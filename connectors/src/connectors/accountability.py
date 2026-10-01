# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `accountability` connector — Atlas, Abuse Library, CourtListener (§23.8, P13.1).

A source adapter on the P04.1 eight-stage framework (:mod:`connectors.stages`)
for the accountability layer: it brings accountability into the graph as
first-class, epistemically-honest records. It writes :class:`AccountabilityEvent`
and :class:`LegalProceeding` entities and **source-class-tagged evidence links**,
preserving a REQUIRED ``epistemic_status`` end to end so an allegation never
renders with a factual verb.

This module owns five things §23.8 / §§11.17–11.18 assign to P13.1, none of which
the framework provides:

* **The ``epistemic_status`` contract** (:class:`AccountabilityEventRecord`,
  SIG-ONTO-038): ``epistemic_status`` is REQUIRED — an event built without one is
  rejected (:class:`MissingEpistemicStatus`) — and preserved **verbatim** from the
  upstream where the upstream provides one. It is emitted under the ontology's
  registered ``event_epistemic_status`` predicate so it flows through the resolver
  (:func:`reconcile.resolve.RESOLVE`) unchanged, and its raw value is preserved
  beside the typed value (P2). The graph never flattens "a plaintiff alleged X in
  a pending lawsuit" to "X happened" (OL-2E-AA-05); the *render* guard lives in
  :mod:`exports.accountability`.
* **Six-source-class evidence links** (:class:`EvidenceLink`, SIG-ONTO-039): an
  incident is linkable to all six OL-2E-AL-03 classes (primary record; court
  record; agency statement; vendor statement; investigative article; advocacy
  analysis) with the class **recorded** on the link, so a claim resting only on
  advocacy analysis is distinguishable from one resting on a court record.
* **The predicate allowlist as a hard schema gate** (SIG-INGEST-033): the
  connector may write only the §11.17–11.18 predicate surface. A Policy, a
  LegalInstrument, a deployment, a device count — the P13.2 / other-ticket
  write-set — is refused at the ingest boundary (the ``D6`` admissibility filter).
* **The crosswalk from the Atlas's own record categories** (data, in
  ``data/accountability_vocab.toml``): the upstream categories (local
  regulation/action, litigation, wrongful stop / false alert, immigration / data
  sharing, security / product issues, stakeholder / company context) are
  **crosswalked**, never adopted wholesale (§23.8), carrying the SKOS mapping
  relation + ``lossy`` flag as provenance. A category outside the crosswalk is
  recorded as unmapped + a research task, never guessed.
* **Targeted-lookup discipline for the court API** (:func:`assert_targeted_lookup`,
  SIG-INGEST-036/037): CourtListener / RECAP is queried as a targeted lookup for
  **known** dockets/opinions only — never crawled (§22.2). This is a legal
  posture; a deviation is an ADR with counsel, not an engineering judgement.

The Atlas publishes **five** artifacts, all of which are consumed (§23.8,
OL-2E-AA-02): the issue-record CSV (the incidents), the source-index CSV (the
reporting behind each incident, typed per OL-2E-AL-03), the GeoJSON (incident
locations, as context — never a device layer), the data dictionary (the crosswalk
authority), and the research archive (recorded provenance). The Abuse Library is a
**curated source index** ingested as an index WITHOUT normalizing its entries into
facts (OL-2E-AL-02): its entries become advocacy-analysis evidence links, not
event claims. Rows are append-only and carry full provenance; the connector emits
**candidate** identifiers and never resolves entities itself (SIG-INGEST-034).
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import cache
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import uuid4

from parsing.document import html_text, pdf_text_pages
from parsing.locator import Locator
from resolution.partner_identity import partner_ref_rows

from ._data import load_table
from .curated_index import CuratedIndexEntry
from .stages import (
    CaptureRef,
    Connector,
    ContentDrift,
    FetchResult,
    RunContext,
    register,
)

_DETECTOR_VERSION = "connectors.accountability/1"

#: Research-task type for an upstream record category outside the versioned
#: crosswalk — mirrors the atlas connector's unmapped-category task (SIG-INGEST-045).
UNMAPPED_CATEGORY_TASK_TYPE = "unmapped_accountability_category"


# --- the versioned vocabulary (data, not code — §20, SIG-ENG-001) -------------


@cache
def vocab() -> dict[str, Any]:
    """The versioned `accountability` connector vocabulary (``data/accountability_vocab.toml``)."""
    return load_table("accountability_vocab")


def vocab_version() -> str:
    """The connector vocabulary version stamped onto every run (§20)."""
    return str(vocab()["vocab_version"])


def source_ids() -> Mapping[str, str]:
    """The registry source ids the connector runs against (§22.6 E)."""
    return dict(vocab()["sources"])


def oversight_report_config() -> Mapping[str, Any]:
    """The reviewed `oversight_report` target-kind contract (``[oversight_report]``, P31.12)."""
    return vocab()["oversight_report"]


def oversight_report_source_ids() -> frozenset[str]:
    """The registry source ids that run the targeted oversight-report path (P31.12)."""
    return frozenset(str(s) for s in oversight_report_config()["sources"])


def epistemic_statuses() -> frozenset[str]:
    """The AccountabilityEvent epistemic-status vocabulary (§11.17, EpistemicStatus)."""
    return frozenset(vocab()["epistemic_statuses"])


def factual_epistemic_statuses() -> frozenset[str]:
    """The statuses that MAY carry a factual verb — only a confirmed/adjudicated event is a fact."""
    return frozenset(vocab()["factual_epistemic_statuses"])


def event_types() -> frozenset[str]:
    """The AccountabilityEvent event-type vocabulary (§11.17, AccountabilityEventType)."""
    return frozenset(vocab()["event_types"])


def postures() -> frozenset[str]:
    """The LegalProceeding posture vocabulary (§11.18, ProceedingPosture)."""
    return frozenset(vocab()["postures"])


def source_classes() -> frozenset[str]:
    """The six OL-2E-AL-03 evidence source classes (§11.17, SourceClass, SIG-ONTO-039)."""
    return frozenset(vocab()["source_classes"])


def atlas_artifacts() -> Mapping[str, str]:
    """The five Accountability Atlas artifacts, all of which are consumed (§23.8, OL-2E-AA-02)."""
    return dict(vocab()["atlas_artifacts"])


# --- the predicate allowlist (SIG-INGEST-033) ---------------------------------


class PredicateNotAllowed(Exception):
    """A schema error: the connector tried to write outside its predicate allowlist."""


def predicate_allowlist() -> frozenset[str]:
    """The predicates this connector may write (§23.8, §§11.17–11.18, SIG-INGEST-033)."""
    return frozenset(vocab()["predicate_allowlist"])


def is_predicate_allowed(predicate: str) -> bool:
    """Whether ``predicate`` is in the connector's allowlist (SIG-INGEST-033)."""
    return predicate in predicate_allowlist()


def forbidden_predicate_genres() -> tuple[str, ...]:
    """The write-set §23.8 / the spec's "Out of scope" places off-limits (documented complement)."""
    return tuple(vocab()["forbidden_predicate_genres"])


def assert_predicate_allowed(predicate: str) -> str:
    """Return ``predicate`` if allowed, else raise :class:`PredicateNotAllowed`.

    The accountability connector may write **only** the AccountabilityEvent
    (§11.17) and LegalProceeding (§11.18) predicate surfaces plus the source-class
    evidence link (§23.8): a Policy, a LegalInstrument, a deployment, or a device
    count is refused here, at the ingestion boundary, rather than only at
    resolution (SIG-INGEST-033, the ``D6`` admissibility filter enforced at ingest).
    Policy / LegalInstrument / policy-configuration divergence is P13.2.
    """
    if not is_predicate_allowed(predicate):
        raise PredicateNotAllowed(
            f"the accountability connector may write only {sorted(predicate_allowlist())} "
            f"(§23.8/§§11.17–11.18, SIG-INGEST-033); {predicate!r} is outside the allowlist — "
            "Policy, LegalInstrument, deployments, device counts are refused (P13.2 owns policy)."
        )
    return predicate


# --- the crosswalk from the Atlas record categories (§23.8) -------------------


def crosswalk() -> Mapping[str, Any]:
    """The upstream record-category → SIG vocabulary crosswalk (data, not code)."""
    return vocab()["crosswalk"]


def category_crosswalk(category: str) -> Mapping[str, Any] | None:
    """The crosswalk entry for one upstream record category, or ``None`` if unmapped.

    The upstream categories are **crosswalked, not adopted wholesale** (§23.8);
    ``None`` means the category is outside the versioned crosswalk and is recorded
    as unmapped + a research task, never guessed.
    """
    return crosswalk().get(_slug(category))


def unmapped_category_task(subject_id: str, category: str) -> dict[str, Any]:
    """A research task for an upstream category outside the versioned crosswalk (§23.8)."""
    return {
        "task_type": UNMAPPED_CATEGORY_TASK_TYPE,
        "subject_id": subject_id,
        "upstream_category": category.strip(),
        "priority": 0.5,
        "closing_condition": (
            "the category is added to the versioned accountability crosswalk (a §20 migration) "
            "OR confirmed out of scope and annotated"
        ),
        "detector_version": _DETECTOR_VERSION,
        "status": "generated",
    }


# --- source-class-tagged evidence links (SIG-ONTO-039) ------------------------


class InvalidSourceClass(Exception):
    """Raised when an evidence link carries a class outside the six OL-2E-AL-03 classes."""


@dataclass(frozen=True)
class EvidenceLink:
    """One source-class-tagged evidence link for an incident (SIG-ONTO-039).

    Records the **class** of the source (one of the six OL-2E-AL-03 classes)
    alongside the source reference, so a claim resting only on advocacy analysis is
    distinguishable from one resting on a court record. ``source_class`` is
    validated against the frozen ``SourceClass`` vocabulary; an out-of-vocabulary
    class is a hard error rather than a silent coercion.
    """

    source_ref: str
    source_class: str
    stable_locator: str = ""
    note: str = ""

    def __post_init__(self) -> None:
        if not str(self.source_ref).strip():
            raise InvalidSourceClass("an evidence link requires a source_ref (§11.17)")
        if self.source_class not in source_classes():
            raise InvalidSourceClass(
                f"source_class {self.source_class!r} is not one of the six OL-2E-AL-03 classes "
                f"{sorted(source_classes())} (SIG-ONTO-039)"
            )

    def as_link(self) -> dict[str, str]:
        """The recorded evidence link — the class is carried on the link (SIG-ONTO-039)."""
        return {
            "source_ref": self.source_ref,
            "source_class": self.source_class,
            "stable_locator": self.stable_locator,
            "note": self.note,
        }


# --- the AccountabilityEvent runtime shape (§11.17) ---------------------------


class MissingEpistemicStatus(Exception):
    """Raised when an event is built without its REQUIRED epistemic_status (SIG-ONTO-038)."""


class InvalidAccountabilityEvent(Exception):
    """Raised when an AccountabilityEvent violates the §11.17 vocabulary contract."""


@dataclass(frozen=True)
class AccountabilityEventRecord:
    """The runtime shape of a §11.17 ``AccountabilityEvent`` — epistemically honest by construction.

    ``epistemic_status`` is **REQUIRED** (SIG-ONTO-038): building an event without
    one raises :class:`MissingEpistemicStatus`, and a value outside the frozen
    ``EpistemicStatus`` vocabulary raises :class:`InvalidAccountabilityEvent`. The
    value is preserved verbatim (``raw_epistemic_status`` keeps exactly what the
    upstream said, P2). ``event_type`` (when present) is validated against
    ``AccountabilityEventType``. ``affected_party_class`` is a class, never a named
    private individual (N4). ``sources`` is a list of :class:`EvidenceLink`, each
    carrying its OL-2E-AL-03 class (SIG-ONTO-039).
    """

    external_id: str
    source_id: str
    epistemic_status: str
    event_type: str | None = None
    date: str | None = None
    organizations: tuple[str, ...] = ()
    deployments: tuple[str, ...] = ()
    technologies: tuple[str, ...] = ()
    affected_party_class: str | None = None
    sources: tuple[EvidenceLink, ...] = ()
    raw_epistemic_status: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.external_id).strip():
            raise InvalidAccountabilityEvent(
                "an AccountabilityEvent requires an external_id (§11.17)"
            )
        if not str(self.epistemic_status).strip():
            raise MissingEpistemicStatus(
                "epistemic_status is REQUIRED on every AccountabilityEvent and MUST NOT be "
                "absent on write (§11.17, SIG-ONTO-038) — an allegation must never be flattened "
                "into an unlabelled fact."
            )
        if self.epistemic_status not in epistemic_statuses():
            raise InvalidAccountabilityEvent(
                f"epistemic_status {self.epistemic_status!r} is not in the EpistemicStatus "
                f"vocabulary {sorted(epistemic_statuses())} (§11.17, SIG-ONTO-038)"
            )
        if self.event_type is not None and self.event_type not in event_types():
            raise InvalidAccountabilityEvent(
                f"event_type {self.event_type!r} is not in the AccountabilityEventType "
                f"vocabulary {sorted(event_types())} (§11.17)"
            )

    @property
    def subject_id(self) -> str:
        """The claim subject id for this event (source + external id scoped)."""
        return f"accountability:{self.source_id}:{self.external_id}"

    @property
    def source_class_set(self) -> frozenset[str]:
        """The distinct OL-2E-AL-03 classes this incident's evidence rests on (SIG-ONTO-039)."""
        return frozenset(link.source_class for link in self.sources)

    def rests_only_on(self, source_class: str) -> bool:
        """Whether every evidence link for this incident is of one class.

        The distinguishing test of SIG-ONTO-039: a claim resting only on
        ``advocacy_analysis`` is distinguishable from one resting on a
        ``court_record`` precisely because the class is recorded on each link.
        """
        return bool(self.sources) and self.source_class_set == {source_class}

    def predicate_values(self) -> dict[str, Any]:
        """The §11.17 predicate → value map for the set predicates (allowlisted keys only)."""
        candidates: dict[str, Any] = {
            "event_type": self.event_type,
            # The ontology's registered predicate id, so the status resolves via
            # RESOLVE() unchanged (SIG-ONTO-038).
            "event_epistemic_status": self.epistemic_status,
            "event_date": self.date,
            "event_organizations": list(self.organizations) or None,
            "event_deployments": list(self.deployments) or None,
            "event_technologies": list(self.technologies) or None,
            "affected_party_class": self.affected_party_class,
        }
        return {k: v for k, v in candidates.items() if v is not None}

    def claim_rows(self) -> list[dict[str, Any]]:
        """The append-only claim rows for this event, confined to the allowlist (P2).

        One ``accountability_event`` entity row (carrying the whole predicate
        surface + the source-class-tagged links for provenance), one row per set
        §11.17 predicate, and one ``event_source`` row per evidence link with the
        OL-2E-AL-03 class recorded (SIG-ONTO-039). ``event_epistemic_status``
        carries the value verbatim beside its raw value (SIG-ONTO-038, P2).
        """
        rows: list[dict[str, Any]] = [
            _stamp(
                {
                    "record_kind": "accountability_event",
                    "subject_id": self.subject_id,
                    "predicate_id": assert_predicate_allowed("accountability_event"),
                    "external_id": self.external_id,
                    "epistemic_status": self.epistemic_status,
                    "raw_value": self.external_id,
                    "predicate_surface": self.predicate_values(),
                    "source_links": [link.as_link() for link in self.sources],
                    "source_classes": sorted(self.source_class_set),
                },
                source_id=self.source_id,
            )
        ]
        for predicate, value in self.predicate_values().items():
            raw_value = (
                self.raw_epistemic_status or self.epistemic_status
                if predicate == "event_epistemic_status"
                else _raw_value_of(value)
            )
            rows.append(
                _stamp(
                    {
                        "record_kind": "claim",
                        "subject_id": self.subject_id,
                        "predicate_id": assert_predicate_allowed(predicate),
                        "value": value,
                        "raw_value": raw_value,
                    },
                    source_id=self.source_id,
                )
            )
        for link in self.sources:
            rows.append(
                _stamp(
                    {
                        "record_kind": "evidence_link",
                        "subject_id": self.subject_id,
                        "predicate_id": assert_predicate_allowed("event_source"),
                        "value": link.source_ref,
                        # SIG-ONTO-039: the class is RECORDED on the evidence link.
                        "source_class": link.source_class,
                        "stable_locator": link.stable_locator,
                        "raw_value": link.source_ref,
                    },
                    source_id=self.source_id,
                )
            )
        return rows


# --- the LegalProceeding runtime shape (§11.18) -------------------------------


class InvalidLegalProceeding(Exception):
    """Raised when a LegalProceeding violates the §11.18 vocabulary contract."""


@dataclass(frozen=True)
class LegalProceedingRecord:
    """The runtime shape of a §11.18 ``LegalProceeding`` — dockets, parties, posture.

    Split from the event because a lawsuit has a docket, parties, and a procedural
    posture a "public hearing" does not (§11.18). ``posture`` (when present) is
    validated against the frozen ``ProceedingPosture`` vocabulary. ``parties`` and
    ``party_role`` are index-aligned. CourtListener / RECAP ids are carried as
    literals so the proceeding links back to the court record it rests on.
    """

    external_id: str
    source_id: str
    court: str | None = None
    docket_number: str | None = None
    case_name: str | None = None
    parties: tuple[str, ...] = ()
    party_role: tuple[str, ...] = ()
    filed_date: str | None = None
    disposition_date: str | None = None
    posture: str | None = None
    courtlistener_id: str | None = None
    recap_id: str | None = None
    sources: tuple[EvidenceLink, ...] = ()
    raw: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.external_id).strip():
            raise InvalidLegalProceeding("a LegalProceeding requires an external_id (§11.18)")
        if self.posture is not None and self.posture not in postures():
            raise InvalidLegalProceeding(
                f"posture {self.posture!r} is not in the ProceedingPosture vocabulary "
                f"{sorted(postures())} (§11.18)"
            )
        if self.parties and self.party_role and len(self.parties) != len(self.party_role):
            raise InvalidLegalProceeding("parties and party_role must be index-aligned (§11.18)")

    @property
    def subject_id(self) -> str:
        return f"legal_proceeding:{self.source_id}:{self.external_id}"

    def predicate_values(self) -> dict[str, Any]:
        """The §11.18 predicate → value map for the set predicates (allowlisted keys only)."""
        candidates: dict[str, Any] = {
            "proceeding_court": self.court,
            "proceeding_docket_number": self.docket_number,
            "proceeding_case_name": self.case_name,
            "proceeding_parties": list(self.parties) or None,
            "proceeding_party_role": list(self.party_role) or None,
            "proceeding_filed_date": self.filed_date,
            "proceeding_disposition_date": self.disposition_date,
            "proceeding_posture": self.posture,
            "proceeding_courtlistener_id": self.courtlistener_id,
            "proceeding_recap_id": self.recap_id,
        }
        return {k: v for k, v in candidates.items() if v is not None}

    def claim_rows(self) -> list[dict[str, Any]]:
        """The append-only claim rows for this proceeding, confined to the allowlist (P2).

        A court record is a ``court_record``-class evidence link by construction
        (SIG-ONTO-039): when no explicit links are supplied, the proceeding stamps
        its own CourtListener/RECAP reference as a court-record link.
        """
        rows: list[dict[str, Any]] = [
            _stamp(
                {
                    "record_kind": "legal_proceeding",
                    "subject_id": self.subject_id,
                    "predicate_id": assert_predicate_allowed("legal_proceeding"),
                    "external_id": self.external_id,
                    "raw_value": self.external_id,
                    "predicate_surface": self.predicate_values(),
                    "source_links": [link.as_link() for link in self._links()],
                },
                source_id=self.source_id,
            )
        ]
        for predicate, value in self.predicate_values().items():
            rows.append(
                _stamp(
                    {
                        "record_kind": "claim",
                        "subject_id": self.subject_id,
                        "predicate_id": assert_predicate_allowed(predicate),
                        "value": value,
                        "raw_value": _raw_value_of(value),
                    },
                    source_id=self.source_id,
                )
            )
        for link in self._links():
            rows.append(
                _stamp(
                    {
                        "record_kind": "evidence_link",
                        "subject_id": self.subject_id,
                        "predicate_id": assert_predicate_allowed("event_source"),
                        "value": link.source_ref,
                        "source_class": link.source_class,
                        "stable_locator": link.stable_locator,
                        "raw_value": link.source_ref,
                    },
                    source_id=self.source_id,
                )
            )
        return rows

    def _links(self) -> tuple[EvidenceLink, ...]:
        if self.sources:
            return self.sources
        ref = self.courtlistener_id or self.recap_id or self.docket_number
        if ref:
            return (EvidenceLink(source_ref=str(ref), source_class="court_record"),)
        return ()


# --- targeted-lookup discipline for CourtListener (SIG-INGEST-036/037) --------


class CrawlAttempted(Exception):
    """Raised when a target would enumerate/crawl the CourtListener API.

    CourtListener / RECAP is used as a targeted lookup for KNOWN dockets/opinions
    only (§22.2, §23.8): at ~5/min a crawl is both prohibited and doomed, and it is
    a **legal** posture (SIG-INGEST-037) — a deviation is an ADR with counsel, not
    an engineering judgement.
    """


def courtlistener_config() -> Mapping[str, Any]:
    """The CourtListener targeted-lookup facts (``[courtlistener]`` in the vocab)."""
    return vocab()["courtlistener"]


def openstates_config() -> Mapping[str, Any]:
    """The OpenStates v3 API facts (``[openstates]`` in the vocab, P26.2)."""
    return vocab()["openstates"]


def congress_gov_config() -> Mapping[str, Any]:
    """The Congress.gov v3 API facts (``[congress_gov]`` in the vocab, P26.12)."""
    return vocab()["congress_gov"]


# --- the surveillance-legislation vocabulary + sweep plan (P26.11 / SOURCES.10)


@cache
def legislation_vocab() -> dict[str, Any]:
    """The reviewed surveillance-legislation vocabulary (``data/legislation_vocab.toml``).

    The keyword set + claim-shape map the bill-index path scans titles against:
    DATA, not code (SIG-ENG-001), versioned like the connector vocabulary.
    """
    return load_table("legislation_vocab")


def legislation_vocab_version() -> str:
    return str(legislation_vocab()["vocab_version"])


def legislation_terms() -> tuple[Mapping[str, Any], ...]:
    """The reviewed [[terms]] rows — id, label, kind, claim_shape, patterns."""
    return tuple(legislation_vocab().get("terms", ()))


def legislation_forbidden() -> tuple[str, ...]:
    """The Part VIII forbidden-token guard for emitted literals (§0.7/§43.2)."""
    return tuple(str(t).lower() for t in legislation_vocab().get("forbidden_tokens", ()))


@cache
def openstates_plan() -> dict[str, Any]:
    """The reviewed 50-state sweep plan (``data/openstates_plan.toml``, P26.11).

    The query plan is data in the target row: which index seeds the
    jurisdiction set, how the current-session window resolves, the per-query
    bounds, and the reviewed query families. Changes are versioned migrations
    (§20), never silent edits.
    """
    return load_table("openstates_plan")


@cache
def congress_gov_plan() -> dict[str, Any]:
    """The reviewed Congress.gov federal sweep plan (``data/congress_gov_plan.toml``, P26.12).

    The query plan is data in the target row: which congresses the bill index
    sweeps, the verified page bound (limit ≤ 250), and the hard
    per-congress page bound that truncates loud rather than crawling. Changes
    are versioned migrations (§20), never silent edits.
    """
    return load_table("congress_gov_plan")


def assert_targeted_lookup(target: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return ``target`` if it is a targeted lookup, else raise :class:`CrawlAttempted`.

    A target is targeted iff it names a **specific** resource: a docket/opinion by
    id, or a concrete document URL. A target that asks to enumerate
    (``mode='crawl'`` / ``'list'`` / ``'search'``), carries a pagination cursor, or
    names a bare collection endpoint with no id is refused (SIG-INGEST-036/037).
    """
    mode = str(target.get("mode", "lookup")).lower()
    if mode in {"crawl", "enumerate", "list", "scrape", "search"}:
        raise CrawlAttempted(
            f"target requests mode={mode!r}; CourtListener is a targeted lookup only, "
            "never crawled (§22.2, SIG-INGEST-036/037)."
        )
    if "page" in target or "cursor" in target or "offset" in target:
        raise CrawlAttempted(
            "target carries a pagination cursor; paging the court API is enumeration, "
            "which the connector never performs (SIG-INGEST-036/037)."
        )
    has_specific = bool(
        target.get("docket_id")
        or target.get("opinion_id")
        or target.get("cluster_id")
        or target.get("recap_id")
        or target.get("document_url")
    )
    url = str(target.get("url", ""))
    if not has_specific and _is_enumeration_url(url):
        raise CrawlAttempted(
            f"target url {url!r} is a bare CourtListener collection endpoint with no specific id; "
            "the connector looks up known dockets/opinions only (§22.2, SIG-INGEST-036/037)."
        )
    return target


# --- targeted report-lookup discipline for the oversight-report sources (P31.12) ----
#
# GAO / DHS OIG / DHS fusion-center assessments / the UK Surveillance Camera
# Commissioner publish individual oversight reports (a landing page or the report
# PDF). The connector looks up ONE reviewed document per target — never an index,
# listing, or search surface (SIG-INGEST-036/037). The reviewed fields ride the
# live-targets row (SIG-INGEST-038 — data, not code): the report's own identifier,
# its title + verbatim literals the capture must carry, and the §11.17 event
# fields. A capture that does not carry every reviewed literal is NOT the reviewed
# document — ContentDrift, fail closed (the P25.8 live-clause precedent).


class UnreviewedReportTarget(ValueError):
    """Raised when an ``oversight_report`` target does not resolve to a reviewed row."""


def assert_oversight_report_target(target: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return ``target`` if it is a reviewed oversight-report row, else raise.

    Enumeration shapes (a crawl/list/search mode, a pagination cursor) are refused
    (SIG-INGEST-036/037). A row missing the reviewed fields — ``external_id``,
    ``title``, non-empty ``literals``, non-empty ``organizations``, an in-vocabulary
    ``epistemic_status`` / ``event_type`` / ``source_class`` — is a data error, never
    a claim (fail closed, §3.1).
    """
    mode = str(target.get("mode", "lookup")).lower()
    if mode in {"crawl", "enumerate", "list", "scrape", "search"}:
        raise CrawlAttempted(
            f"target requests mode={mode!r}; oversight reports are targeted lookups of "
            "specific published documents only, never crawled (§22.2, SIG-INGEST-036/037)."
        )
    if "page" in target or "cursor" in target or "offset" in target:
        raise CrawlAttempted(
            "target carries a pagination cursor; paging a report index is enumeration, "
            "which the connector never performs (SIG-INGEST-036/037)."
        )
    if str(target.get("kind") or "") != str(oversight_report_config()["kind"]):
        raise UnreviewedReportTarget(
            f"target kind {target.get('kind')!r} is not 'oversight_report'"
        )
    url = str(target.get("url") or "").strip()
    if not url.startswith("https://"):
        raise UnreviewedReportTarget(
            f"oversight_report target url {url!r} must be an https document URL"
        )
    if not str(target.get("external_id") or "").strip():
        raise UnreviewedReportTarget(
            "an oversight_report target requires the report's own reviewed `external_id`"
        )
    if not str(target.get("title") or "").strip():
        raise UnreviewedReportTarget("an oversight_report target requires the reviewed `title`")
    literals = target.get("literals")
    if (
        not isinstance(literals, (list, tuple))
        or not literals
        or not all(isinstance(lit, str) and lit.strip() for lit in literals)
    ):
        raise UnreviewedReportTarget(
            "an oversight_report target requires non-empty reviewed `literals` — the "
            "verbatim strings the captured page must still carry"
        )
    organizations = target.get("organizations")
    if not isinstance(organizations, (list, tuple)) or not [
        o for o in organizations if str(o).strip()
    ]:
        raise UnreviewedReportTarget(
            "an oversight_report target requires reviewed `organizations` — the audited "
            "agency or program the event names (§11.17 event_organizations)"
        )
    epistemic = str(target.get("epistemic_status") or "")
    if epistemic not in epistemic_statuses():
        raise UnreviewedReportTarget(
            f"epistemic_status {epistemic!r} is not in the EpistemicStatus vocabulary "
            f"{sorted(epistemic_statuses())} (§11.17, SIG-ONTO-038)"
        )
    event_type = target.get("event_type")
    if event_type is not None and str(event_type) not in event_types():
        raise UnreviewedReportTarget(
            f"event_type {event_type!r} is not in the AccountabilityEventType vocabulary "
            f"{sorted(event_types())} (§11.17)"
        )
    source_class = str(target.get("source_class") or oversight_report_config()["source_class"])
    if source_class not in source_classes():
        raise UnreviewedReportTarget(
            f"source_class {source_class!r} is not one of the six OL-2E-AL-03 classes "
            f"{sorted(source_classes())} (SIG-ONTO-039)"
        )
    return target


def _oversight_report_target_for(ctx: RunContext, uri: str) -> Mapping[str, Any] | None:
    """The reviewed ``oversight_report`` target row for a capture URI, or ``None``.

    A live or hosted asserting-replay run's targets ARE the reviewed
    ``live_targets`` rows; a fixture run names the reviewed URL on a bare
    ``{id,url,kind}`` row — either way the committed live-targets row is
    authoritative for the report's reviewed fields (SIG-INGEST-038): a fixture
    row may name the URL, it may not redefine the review.
    """
    resolved = ctx.resolved_targets.get(uri)
    if resolved is not None and resolved.get("kind") == "oversight_report":
        return resolved
    for candidate in ctx.parameters.get("targets", []):
        if str(candidate.get("url")) == uri and candidate.get("external_id"):
            if candidate.get("kind") == "oversight_report":
                return candidate
    from .live_targets import live_targets

    for candidate in live_targets(ctx.source.id):
        if str(candidate.get("url")) == uri and candidate.get("kind") == "oversight_report":
            return candidate
    return None


def _is_enumeration_url(url: str) -> bool:
    """Whether a URL is a bare CourtListener collection/listing endpoint (no specific resource)."""
    if not url:
        return False
    base, _, query = url.partition("?")
    q = query.lower()
    if any(tok in q for tok in ("id=", "docket=", "cluster=", "q=")):
        # A query filtering to a specific id is a lookup; a free-text `q=` search is not.
        if "q=" in q:
            return True
        return False
    tail = base.rstrip("/")
    cfg = courtlistener_config()
    api_base = str(cfg["api_base"]).rstrip("/")
    for collection in cfg["collections"]:
        endpoint = f"{api_base}{collection}".rstrip("/")
        if tail.endswith(endpoint) or tail.endswith(str(collection).rstrip("/")):
            return True
    return False


# --- CSV parsing --------------------------------------------------------------


def _fold(text: str) -> str:
    """Whitespace-folded text for literal matching across markup/line breaks."""
    return re.sub(r"\s+", " ", str(text))


def _parse_oversight_report(
    ctx: RunContext, capture: CaptureRef, target: Mapping[str, Any], data: bytes
) -> dict[str, Any]:
    """Text + reviewed-literal verification for one report capture (P31.12).

    HTML pages extract through ``parsing.document.html_text``; a ``%PDF`` byte
    stream through ``pdf_text_pages`` (it returns no pages for a malformed or
    text-less PDF — a body that cannot prove its reviewed literals is drift, not
    a claim). Every reviewed ``literals`` string must survive in the extracted
    text (whitespace-folded); a missing one means the captured document is not
    the reviewed report — :class:`ContentDrift`, fail closed, never a claim
    asserted beyond the capture (§3.1; the P25.8 live-clause precedent).
    """
    if data.lstrip()[:4] == b"%PDF":
        pages = pdf_text_pages(data)
        if not pages:
            raise ContentDrift(
                ctx.source.id,
                "the report capture is a PDF with no extractable text layer",
                details=f"{len(data)} bytes",
            )
        text = " ".join(pages)
    else:
        text = html_text(data)
    if not text.strip():
        raise ContentDrift(
            ctx.source.id,
            "the report capture carries no text",
            details=f"{len(data)} bytes",
        )
    folded = _fold(text)
    missing = [
        i
        for i, literal in enumerate(target.get("literals") or ())
        if _fold(str(literal)) not in folded
    ]
    if missing:
        raise ContentDrift(
            ctx.source.id,
            "the capture does not carry the reviewed literal(s) the report row names",
            details=(
                f"external_id={str(target.get('external_id') or '')!r}; "
                f"literal index(es) {missing} absent from {len(text)} chars of text"
            ),
        )
    return {
        "kind": "oversight_report",
        "capture": capture,
        "target": target,
        "byte_size": len(data),
    }


def parse_csv(data: bytes) -> dict[str, Any]:
    """Parse an Accountability Atlas CSV into a header + list of row dicts.

    Kept as a pure function of the captured bytes (SIG-INGEST-002): the connector
    reads the archived capture back and calls this, never the network.
    """
    text = data.decode("utf-8-sig")  # tolerate a UTF-8 BOM on the upstream export
    reader = csv.DictReader(io.StringIO(text))
    header = list(reader.fieldnames or [])
    rows = [dict(row) for row in reader]
    return {"header": header, "rows": rows}


def canary_findings(parsed: Mapping[str, Any]) -> list[str]:
    """Structural-drift findings for an Atlas issue-record CSV (SIG-PARSE-008 canary).

    Committed fixtures pin known inputs and pass forever; the canary is the
    complement that runs against a live response and alerts when the structure
    drifts. This is that check's deterministic core. An **empty** list means no
    drift. Checks: an id column and a category column are present; every row
    carries a non-empty id. It deliberately does NOT assert category *values* — a
    new upstream category is handled as unmapped + a research task, not as drift.
    """
    findings: list[str] = []
    header = parsed.get("header")
    if not isinstance(header, list):
        return ["missing CSV header"]
    if not _first_present(header, _ID_COLUMNS):
        findings.append(f"missing an id column (one of {_ID_COLUMNS})")
    if not _first_present(header, _CATEGORY_COLUMNS):
        findings.append(f"missing a category column (one of {_CATEGORY_COLUMNS})")
    if findings:
        return findings
    id_col = _first_present(header, _ID_COLUMNS)
    for i, row in enumerate(parsed.get("rows", [])):
        if id_col is not None and not str(row.get(id_col, "")).strip():
            findings.append(f"row[{i}] has an empty {id_col!r}")
    return findings


# --- the connector ------------------------------------------------------------


#: The partner predicate whose text claims gain entity-ref claims (P31.5).
_PARTNER_PREDICATES = frozenset({"event_organizations"})


@register
class AccountabilityConnector(Connector):
    """The `accountability` connector: Accountability Atlas, Abuse Library, CourtListener (§23.8).

    Runs on the P04.1 eight-stage framework. ``discover`` returns explicitly
    supplied targets (CourtListener targets are asserted to be targeted lookups,
    never crawls); ``fetch`` egresses through the shared politeness layer;
    ``parse``/``extract``/``normalize`` are pure functions of the capture that build
    :class:`AccountabilityEventRecord` / :class:`LegalProceedingRecord` entities and
    source-class-tagged evidence links, crosswalk the upstream record categories
    (never adopting them wholesale), and preserve ``epistemic_status`` verbatim
    (SIG-ONTO-038). Every claim is confined to the predicate allowlist
    (SIG-INGEST-033).
    """

    name = "accountability"
    version = "1.0.0"

    # -- acquisition --
    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        """Enumerate fetch targets — known lookups only for the court API (SIG-INGEST-036).

        Targets come from ``ctx.parameters['targets']``; a CourtListener target is
        asserted to be a targeted lookup. The connector never enumerates a listing
        endpoint itself.
        """
        targets = list(ctx.parameters.get("targets", []))
        for target in targets:
            if self._is_courtlistener(ctx, target):
                assert_targeted_lookup(target)
        if ctx.source.id in oversight_report_source_ids():
            # P31.12: every target must resolve to a reviewed oversight_report
            # live-targets row (SIG-INGEST-038). The resolved row — not the
            # fetch envelope — is what downstream stages consume.
            resolved_targets: list[Mapping[str, Any]] = []
            for target in targets:
                row = _oversight_report_target_for(ctx, str(target.get("url") or ""))
                if row is None:
                    raise UnreviewedReportTarget(
                        f"target {str(target.get('url') or '')!r} has no reviewed "
                        f"oversight_report row in live_targets.toml for {ctx.source.id!r}"
                    )
                assert_oversight_report_target(row)
                ctx.resolved_targets[str(row["url"])] = row
                resolved_targets.append(row)
            return resolved_targets
        return targets

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """Obtain bytes for one target through the shared politeness layer only (SIG-INGEST-011)."""
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        if self._is_courtlistener(ctx, target):
            assert_targeted_lookup(target)
        url = str(target["url"])
        if ctx.source.id == source_ids().get("openstates"):
            # OpenStates v3 authenticates via the documented X-API-KEY request
            # header — the key resolves from the environment only (HG-09) and
            # never rides in the URL, so no credential lands in the recorded
            # source_uri / run records. Keyless it answers 403, which the shared
            # layer records as a challenge, never defeated. The same header
            # covers the jurisdictions index + the generated bill_search
            # targets of the 50-state sweep (P26.11).
            key = os.environ.get(str(openstates_config()["api_key_env"]), "").strip()
            if key:
                return ctx.fetcher.fetch(
                    url, headers={str(openstates_config()["api_key_header"]): key}
                )
        if ctx.source.id == source_ids().get("congress_gov"):
            # Congress.gov v3 authenticates via the documented api.data.gov
            # X-Api-Key request header (api.data.gov/docs/api-key) — the
            # existing sig-data-gov-key secret resolves from the environment
            # only (HG-09) and NEVER rides an api_key query param, so no
            # credential lands in the recorded source_uri / run records
            # (verified live 2026-09-18: header → 200; keyless → 403
            # API_KEY_MISSING — a recorded challenge, never defeated). The
            # same header covers the seed congress page + the generated
            # bill-index pages of the federal sweep (P26.12).
            key = os.environ.get(str(congress_gov_config()["api_key_env"]), "").strip()
            if key:
                return ctx.fetcher.fetch(
                    url, headers={str(congress_gov_config()["api_key_header"]): key}
                )
        return ctx.fetcher.fetch(url)

    # -- interpretation (pure functions of the capture) --
    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Structure the captured bytes by artifact kind.

        The kind is carried on the capture's ``source_uri`` (the artifact the
        target named): a CSV artifact (issue-record or source-index) is parsed to
        header + rows; a court/abuse JSON payload is parsed as JSON; a GeoJSON /
        data-dictionary / research-archive artifact is consumed as context (§23.8).
        """
        data = ctx.captures.get(capture.digest)
        # P31.12: a reviewed oversight-report target parses its own path — the
        # report's landing page (html_text) or the report PDF (pdf_text_pages),
        # verified against the reviewed literals before anything is read from it.
        target = _oversight_report_target_for(ctx, str(capture.source_uri))
        if target is not None and str(target.get("kind")) == "oversight_report":
            assert_oversight_report_target(target)
            return _parse_oversight_report(ctx, capture, target, data)
        if ctx.source.id in oversight_report_source_ids():
            # Fail closed: a capture for one of these sources whose URL names no
            # reviewed report row is never read as generic rows (SIG-INGEST-038).
            raise ContentDrift(
                ctx.source.id,
                "the capture's URL names no reviewed oversight_report target",
                details=str(capture.source_uri),
            )
        kind = _artifact_kind(capture)
        if kind in {"issue_record_csv", "source_index_csv"}:
            return {"kind": kind, "capture": capture, **parse_csv(data)}
        if kind in {
            "courtlistener",
            "abuse_library",
            "openstates",
            "openstates_jurisdictions",
            "congress_gov_bills",
        }:
            try:
                payload = json.loads(data)
            except json.JSONDecodeError as exc:
                raise ContentDrift(
                    ctx.source.id,
                    f"the {kind} capture is not valid JSON",
                    details=str(exc),
                ) from exc
            parsed: dict[str, Any] = {"kind": kind, "capture": capture, "payload": payload}
            if kind == "openstates":
                # The bill_search target row the capture fetched (a resolved
                # continuation target, or a configured one) — the query plan
                # row (jurisdiction, session window, query family) rides it
                # onto the emitted bill_query outcome row (P26.11).
                parsed["target"] = _bill_search_target_for(ctx, capture.source_uri)
            if kind == "congress_gov_bills":
                # The congress bill-index page target the capture fetched
                # (a resolved continuation target, or the configured seed) —
                # the query plan row (congress, page offset, plan version)
                # rides it onto the emitted bill_query outcome row (P26.12).
                parsed["target"] = _congress_page_target_for(ctx, capture.source_uri)
            return parsed
        # geojson / data_dictionary / research_archive: consumed as context.
        return {"kind": kind, "capture": capture, "byte_size": len(data)}

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """Raw records with locators, preserving raw values (P2)."""
        kind = str(parsed["kind"])
        if kind == "oversight_report":
            # One reviewed report row → one raw record. The reviewed fields ride
            # verbatim (P2 — the row's literals/title are the upstream text the
            # capture proved); the capture's digest + URI carry the locator.
            return [
                {
                    "record_kind": "oversight_report",
                    "raw": dict(parsed["target"]),
                    "source_uri": str(parsed["capture"].source_uri),
                    "capture_digest": str(parsed["capture"].digest),
                    "byte_size": int(parsed.get("byte_size") or 0),
                }
            ]
        if kind == "issue_record_csv":
            return [{"record_kind": "issue_record", "raw": row} for row in parsed.get("rows", [])]
        if kind == "source_index_csv":
            return [{"record_kind": "source_index", "raw": row} for row in parsed.get("rows", [])]
        if kind == "courtlistener":
            payload = parsed["payload"]
            objects = payload["results"] if _has_results(payload) else [payload]
            return [{"record_kind": "court_record", "raw": dict(o)} for o in objects]
        if kind == "abuse_library":
            payload = parsed["payload"]
            # A curated source INDEX ingested without normalizing into facts
            # (OL-2E-AL-02): each entry is an advocacy-analysis source link.
            entries = payload["entries"] if _has_entries(payload) else [payload]
            return [{"record_kind": "abuse_entry", "raw": dict(e)} for e in entries]
        if kind == "openstates":
            # The OpenStates v3 bill search (P26.2, widened P26.11): `results`
            # is the bill index page. An error envelope ({"detail": ...}) or a
            # changed shape is ContentDrift — the connector fails closed rather
            # than treating the envelope as a bill record.
            payload = parsed["payload"]
            if not isinstance(payload, Mapping) or not _has_results(payload):
                detail = (
                    str(payload.get("detail"))
                    if isinstance(payload, Mapping) and payload.get("detail")
                    else type(payload).__name__
                )
                raise ContentDrift(
                    ctx.source.id,
                    "the openstates bill_search payload is not a results page",
                    details=detail,
                )
            objects = payload["results"]
            records: list[Mapping[str, Any]] = [
                {
                    "record_kind": "bill_index",
                    "raw": dict(o),
                    "row_index": i,
                    "source_uri": str(parsed["capture"].source_uri),
                }
                for i, o in enumerate(objects)
            ]
            # The per-QUERY outcome row (P26.11): the sweep's hits/empty
            # outcome for this jurisdiction × query-family fetch, recorded
            # with the reviewed plan row + the page's pagination metadata.
            records.append(
                {
                    "record_kind": "bill_query",
                    "raw": {
                        "target": parsed.get("target"),
                        "pagination": (
                            payload.get("pagination")
                            if isinstance(payload.get("pagination"), Mapping)
                            else {}
                        ),
                        "result_count": len(objects),
                        "source_uri": str(parsed["capture"].source_uri),
                        "capture_digest": str(parsed["capture"].digest),
                    },
                }
            )
            return records
        if kind == "openstates_jurisdictions":
            # The v3 /jurisdictions index that seeds the sweep (P26.11): each
            # row is a jurisdiction record carrying its legislative_sessions —
            # the discovery surface discover_more expands into the bounded
            # bill_search targets. Fail closed on a non-results payload.
            payload = parsed["payload"]
            if not isinstance(payload, Mapping) or not _has_results(payload):
                raise ContentDrift(
                    ctx.source.id,
                    "the openstates jurisdictions payload is not a results page",
                    details=type(payload).__name__,
                )
            return [
                {"record_kind": "jurisdiction_record", "raw": dict(j)} for j in payload["results"]
            ]
        if kind == "congress_gov_bills":
            # The Congress.gov v3 congress-scoped bill index (P26.12):
            # `bills` is the bill index page. An error envelope
            # ({"error": {...}} — the api.data.gov error shape) or a changed
            # shape is ContentDrift — the connector fails closed rather than
            # treating the envelope as a bill record. An empty `bills` list
            # is an honest empty page (e.g. a congress with no bills), not
            # drift.
            payload = parsed["payload"]
            if (
                not isinstance(payload, Mapping)
                or not isinstance(payload.get("bills"), list)
                or "error" in payload
            ):
                detail = (
                    json.dumps(payload.get("error"))
                    if isinstance(payload, Mapping) and payload.get("error")
                    else type(payload).__name__
                )
                raise ContentDrift(
                    ctx.source.id,
                    "the congress_gov bill-index payload is not a bills page",
                    details=detail,
                )
            objects = payload["bills"]
            records = [
                {
                    "record_kind": "congress_bill",
                    "raw": dict(o),
                    "row_index": i,
                    "source_uri": str(parsed["capture"].source_uri),
                }
                for i, o in enumerate(objects)
                if isinstance(o, Mapping)
            ]
            # The per-PAGE outcome row (P26.12): the sweep's honest
            # indexed/matched outcome for this congress bill-index page,
            # recorded with the reviewed plan row + the page's pagination
            # metadata (total_items = pagination.count).
            records.append(
                {
                    "record_kind": "bill_query",
                    "raw": {
                        "target": parsed.get("target"),
                        "pagination": (
                            payload.get("pagination")
                            if isinstance(payload.get("pagination"), Mapping)
                            else {}
                        ),
                        "result_count": len(objects),
                        "source_uri": str(parsed["capture"].source_uri),
                        "capture_digest": str(parsed["capture"].digest),
                    },
                }
            )
            return records
        # A consumed-as-context artifact (geojson / data_dictionary / research_archive).
        return [{"record_kind": "context", "artifact_kind": kind}]

    def discover_more(
        self, ctx: RunContext, captures: Sequence[CaptureRef]
    ) -> list[Mapping[str, Any]]:
        """Expand the captured jurisdictions index into the bounded 50-state
        bill_search sweep (P26.11 / SOURCES.10).

        The captured ``/jurisdictions`` pages ARE the discovery surface: each
        jurisdiction row resolves its current-session window (the reviewed
        regular-class latest-start rule) and expands to one bounded
        ``bill_search`` target per reviewed query family — jurisdiction +
        session + OR-batched keyword phrases + per_page ≤ 20 riding the target
        row as data. The expansion is bounded by the plan's ``max_queries``
        and recorded on ``ctx.resolved_targets`` so each child's post-capture
        stages see its query provenance. Exactly one pass — never a crawl.
        """
        if ctx.source.id == source_ids().get("congress_gov"):
            # The captured seed page(s) ARE the discovery surface for the
            # federal sweep (P26.12 / SOURCES.11): each seed's
            # `pagination.count` names the congress index size, and the
            # remaining bounded pages are expanded — congress + page offset +
            # plan version riding the target row as data. Bounded by the
            # plan's `max_pages_per_congress` and recorded on
            # `ctx.resolved_targets`. Exactly one pass — never a crawl.
            plan = congress_gov_plan()
            page_targets = _congress_page_targets(ctx, captures, plan)
            for target in page_targets:
                ctx.resolved_targets[str(target["url"])] = target
            return page_targets
        if ctx.source.id != source_ids().get("openstates"):
            return []
        plan = openstates_plan()
        jurisdictions = _jurisdictions_from_captures(ctx, captures)
        if not jurisdictions:
            return []
        targets: list[Mapping[str, Any]] = _bill_query_targets(jurisdictions, plan)
        for target in targets:
            ctx.resolved_targets[str(target["url"])] = target
        return targets

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """Typed rows beside preserved raw values (P2), confined to the allowlist."""
        out: list[dict[str, Any]] = []
        # Per-page tally for the bill_query outcome row (P26.11): the batch is
        # one capture's records, so these accumulate within one call.
        page_indexed = 0
        page_matched = 0
        page_terms: set[str] = set()
        page_suppressed: set[str] = set()
        for raw in raw_claims:
            kind = raw["record_kind"]
            if kind == "oversight_report":
                out.extend(self._normalize_oversight_report(ctx, raw))
            elif kind == "issue_record":
                out.extend(self._normalize_issue_record(ctx, raw["raw"]))
            elif kind == "source_index":
                out.append(self._normalize_source_index(ctx, raw["raw"]))
            elif kind == "court_record":
                out.extend(self._normalize_court_record(ctx, raw["raw"]))
            elif kind == "abuse_entry":
                out.append(self._normalize_abuse_entry(ctx, raw["raw"]))
            elif kind == "bill_index":
                page_indexed += 1
                rows, terms, suppressed = self._normalize_bill_row(
                    ctx,
                    raw["raw"],
                    int(raw.get("row_index") or 0),
                    str(raw.get("source_uri") or ""),
                )
                out.extend(rows)
                if terms:
                    page_matched += 1
                    page_terms.update(str(t["term_id"]) for t in terms)
                page_suppressed.update(suppressed)
            elif kind == "congress_bill":
                # The federal layer (P26.12): the same verbatim term scan +
                # claim-shape map, on the Congress.gov record's own title.
                page_indexed += 1
                rows, terms, suppressed = self._normalize_congress_bill_row(
                    ctx,
                    raw["raw"],
                    int(raw.get("row_index") or 0),
                    str(raw.get("source_uri") or ""),
                )
                out.extend(rows)
                if terms:
                    page_matched += 1
                    page_terms.update(str(t["term_id"]) for t in terms)
                page_suppressed.update(suppressed)
            elif kind == "bill_query":
                out.append(
                    self._normalize_bill_query(
                        ctx,
                        raw["raw"],
                        indexed=page_indexed,
                        matched=page_matched,
                        terms=page_terms,
                        suppressed=page_suppressed,
                    )
                )
            elif kind == "jurisdiction_record":
                out.append(self._normalize_jurisdiction(ctx, raw["raw"]))
            # context records carry no claims — they were consumed as authority.
        return out

    # -- normalization helpers --
    def _normalize_issue_record(
        self, ctx: RunContext, raw: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        external_id = _first_value(raw, _ID_COLUMNS)
        category = _first_value(raw, _CATEGORY_COLUMNS)
        subject_id = f"accountability:{ctx.source.id}:{external_id or _slug(str(raw))}"
        mapping = category_crosswalk(category) if category else None
        if category and mapping is None:
            return [
                _stamp(
                    {
                        "record_kind": "unmapped_category",
                        "subject_id": subject_id,
                        "raw_value": category,
                        "research_task": unmapped_category_task(subject_id, category),
                    },
                    source_id=ctx.source.id,
                )
            ]
        # epistemic_status: preserve the upstream verbatim where provided, else the
        # crosswalk default. The RAW upstream string is kept untouched (P2); the
        # TYPED value is the upstream label normalized onto the vocabulary (casing
        # only — "Alleged" -> "alleged"), never a re-interpretation. A label that
        # does not normalize onto a vocabulary term is NOT guessed (SIG-ONTO-038).
        raw_status = _first_value(raw, _EPISTEMIC_COLUMNS)
        status = _normalize_epistemic(raw_status) or (
            str(mapping["epistemic_default"]) if mapping else None
        )
        if raw_status and status is None and not (mapping and mapping.get("epistemic_default")):
            return [
                _stamp(
                    {
                        "record_kind": "unmapped_category",
                        "subject_id": subject_id,
                        "raw_value": raw_status,
                        "research_task": unmapped_category_task(subject_id, category or ""),
                        "note": f"upstream epistemic label {raw_status!r} is off-vocabulary",
                    },
                    source_id=ctx.source.id,
                )
            ]
        if not status:
            return [
                _stamp(
                    {
                        "record_kind": "unmapped_category",
                        "subject_id": subject_id,
                        "raw_value": category or "",
                        "research_task": unmapped_category_task(subject_id, category or ""),
                        "note": "no epistemic_status upstream and no crosswalk default",
                    },
                    source_id=ctx.source.id,
                )
            ]
        event = AccountabilityEventRecord(
            external_id=external_id or _slug(str(raw)),
            source_id=ctx.source.id,
            epistemic_status=str(status).strip().lower(),
            event_type=(
                str(mapping.get("event_type")) if mapping and mapping.get("event_type") else None
            ),
            date=_first_value(raw, _DATE_COLUMNS),
            organizations=_split(_first_value(raw, _ORG_COLUMNS)),
            technologies=_split(_first_value(raw, _TECH_COLUMNS)),
            affected_party_class=_first_value(raw, _PARTY_CLASS_COLUMNS),
            sources=self._issue_record_links(raw),
            raw_epistemic_status=raw_status,
            raw=dict(raw),
        )
        rows = list(event.claim_rows())
        if mapping:
            rows[0]["crosswalk_relation"] = mapping.get("relation")
            rows[0]["crosswalk_lossy"] = bool(mapping.get("lossy", False))
            rows[0]["upstream_category"] = category
        return rows

    @staticmethod
    def _issue_record_links(raw: Mapping[str, Any]) -> tuple[EvidenceLink, ...]:
        """Build source-class-tagged links from an issue-record row (SIG-ONTO-039).

        Where the row names typed sources per class (the source-index join), each
        becomes a link carrying its class; a bare ``source_url`` with no class
        defaults to the ``advocacy_analysis`` class — the Accountability Atlas is
        itself an advocacy compilation, so an untyped Atlas source is advocacy
        analysis until the source index types it more precisely.
        """
        links: list[EvidenceLink] = []
        # sorted() so the emitted link order is deterministic across runs — replay
        # must be byte-identical modulo the excluded columns (SIG-INGEST-003).
        for cls in sorted(source_classes()):
            for ref in _split(raw.get(f"source_{cls}") or raw.get(cls)):
                links.append(EvidenceLink(source_ref=ref, source_class=cls))
        if not links:
            for ref in _split(_first_value(raw, _SOURCE_URL_COLUMNS)):
                links.append(EvidenceLink(source_ref=ref, source_class="advocacy_analysis"))
        return tuple(links)

    def _normalize_source_index(self, ctx: RunContext, raw: Mapping[str, Any]) -> dict[str, Any]:
        """A source-index row: the reporting behind an incident, typed per OL-2E-AL-03.

        The source index is what lets SIG preserve the distinction between an event
        and the reporting about it (§23.8). Each row appends a source-class-tagged
        evidence link to its incident; the class is taken from the row (validated),
        else defaults to advocacy analysis.
        """
        incident = _first_value(raw, _ID_COLUMNS) or ""
        cls = (_first_value(raw, _SOURCE_CLASS_COLUMNS) or "advocacy_analysis").strip()
        ref = (
            _first_value(raw, _SOURCE_URL_COLUMNS)
            or _first_value(raw, ("source", "citation"))
            or ""
        )
        link = EvidenceLink(
            source_ref=ref or f"{ctx.source.id}:{incident}",
            source_class=cls if cls in source_classes() else "advocacy_analysis",
            stable_locator=_first_value(raw, _SOURCE_URL_COLUMNS) or "",
        )
        return _stamp(
            {
                "record_kind": "evidence_link",
                "subject_id": f"accountability:{ctx.source.id}:{incident}",
                "predicate_id": assert_predicate_allowed("event_source"),
                "value": link.source_ref,
                "source_class": link.source_class,
                "raw_value": link.source_ref,
                "raw_source_class": cls,
            },
            source_id=ctx.source.id,
        )

    def _normalize_oversight_report(
        self, ctx: RunContext, raw: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        """One reviewed oversight report → one §11.17 ``AccountabilityEvent`` (P31.12).

        The reviewed live-targets row IS the claim data (SIG-INGEST-038): the report's
        own identifier, its §11.17 event fields, and the organisations it audits. The
        captured page/PDF — already verified to carry the reviewed literals — is the
        ``primary_record`` evidence link the event's claims rest on (SIG-ONTO-039). An
        event is never a deployment, device-count, or operational-state claim (the
        allowlist enforces it; procured/reviewed ≠ deployed).
        """
        data = raw["raw"]  # the reviewed target row (SIG-INGEST-038)
        url = str(raw.get("source_uri") or data.get("url") or "")
        link = EvidenceLink(
            source_ref=url,
            source_class=str(data.get("source_class") or oversight_report_config()["source_class"]),
            stable_locator=url,
            note=str(data.get("title") or ""),
        )
        event = AccountabilityEventRecord(
            external_id=str(data["external_id"]),
            source_id=ctx.source.id,
            epistemic_status=str(data["epistemic_status"]),
            event_type=_opt_str(data.get("event_type")),
            date=_opt_str(data.get("event_date")),
            organizations=tuple(str(o) for o in data.get("organizations") or ()),
            technologies=tuple(str(t) for t in data.get("technologies") or ()),
            affected_party_class=_opt_str(data.get("affected_party_class")),
            sources=(link,),
            raw=dict(data),
        )
        rows = list(event.claim_rows())
        rows[0]["title"] = str(data.get("title") or "")
        return rows

    def _normalize_court_record(
        self, ctx: RunContext, raw: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        external_id = str(raw.get("id") or raw.get("docket_id") or raw.get("docket_number") or "")
        proceeding = LegalProceedingRecord(
            external_id=external_id or _slug(str(raw)),
            source_id=ctx.source.id,
            court=_opt_str(raw.get("court") or raw.get("court_id")),
            docket_number=_opt_str(raw.get("docket_number")),
            case_name=_opt_str(raw.get("case_name") or raw.get("caseName")),
            filed_date=_opt_str(raw.get("date_filed") or raw.get("dateFiled")),
            disposition_date=_opt_str(raw.get("date_terminated") or raw.get("dateTerminated")),
            posture=_opt_str(raw.get("posture")),
            courtlistener_id=_opt_str(raw.get("id") or raw.get("cluster_id")),
            recap_id=_opt_str(raw.get("recap_id") or raw.get("recap_documents")),
            raw=dict(raw),
        )
        return list(proceeding.claim_rows())

    def _normalize_abuse_entry(self, ctx: RunContext, raw: Mapping[str, Any]) -> dict[str, Any]:
        """An Abuse Library entry as an advocacy-analysis source link, NOT a fact (OL-2E-AL-02).

        The Abuse Library is a curated source INDEX held as an index without
        normalizing its entries into facts (§10.9, SIG-EPIS-030): the entry is a
        :class:`~connectors.curated_index.CuratedIndexEntry` (the general form of
        this behaviour), surfaced as an advocacy-analysis ``index_only`` evidence
        link keyed to its incident — never an event claim.
        """
        incident = str(raw.get("incident") or raw.get("id") or "")
        ref = str(raw.get("url") or raw.get("source") or raw.get("citation") or incident)
        entry = CuratedIndexEntry(
            source_ref=ref, source_class="advocacy_analysis", indexes=incident
        )
        return _stamp(
            {
                "record_kind": "evidence_link",
                "subject_id": f"accountability:{ctx.source.id}:{entry.indexes}",
                "predicate_id": assert_predicate_allowed("event_source"),
                "value": entry.source_ref,
                "source_class": entry.source_class,
                "raw_value": entry.source_ref,
                # SIG-EPIS-030 / OL-2E-AL-02: an index entry, never normalized to a fact.
                "index_only": True,
            },
            source_id=ctx.source.id,
        )

    def _normalize_bill_index(self, ctx: RunContext, raw: Mapping[str, Any]) -> dict[str, Any]:
        """An OpenStates bill record as an index-only evidence link (P26.2, §3.1).

        A state bill is **not** a §11.14 LegalInstrument — the frozen
        LegalInstrumentType vocabulary has no ``bill`` value and asserting
        ``statute`` for a pending bill would assert an enactment that never
        happened (no synthetic certainty). The record is what the index *lists*:
        an ``index_only`` evidence link keyed to the bill, ``primary_record``
        class when it points at the official legislature page (OpenStates'
        ``sources``), else the OpenStates page itself. Identifier, title,
        session, jurisdiction, and latest action ride as recorded index
        metadata — claims are never minted from them (P13.2 owns policy).
        """
        bill_id = str(raw.get("id") or raw.get("identifier") or _slug(str(raw)))
        # Prefer the official legislature source URL the record names; the
        # OpenStates page is the fallback locator.
        ref = ""
        for src in raw.get("sources") or []:
            if isinstance(src, Mapping) and src.get("url"):
                ref = str(src["url"])
                break
        ref = ref or str(raw.get("openstates_url") or raw.get("url") or "")
        jurisdiction = raw.get("jurisdiction")
        jurisdiction_name = (
            str(jurisdiction.get("name"))
            if isinstance(jurisdiction, Mapping)
            else _opt_str(jurisdiction) or ""
        )
        return _stamp(
            {
                "record_kind": "evidence_link",
                "subject_id": f"accountability:{ctx.source.id}:{bill_id}",
                "predicate_id": assert_predicate_allowed("event_source"),
                "value": ref or f"openstates:{bill_id}",
                "source_class": "primary_record" if ref else "advocacy_analysis",
                "raw_value": ref or bill_id,
                # SIG-EPIS-030 analogue: an index entry, never normalized to a fact.
                "index_only": True,
                "bill_identifier": _opt_str(raw.get("identifier")),
                "bill_title": _opt_str(raw.get("title")),
                "legislative_session": _opt_str(raw.get("session")),
                "legislative_jurisdiction": jurisdiction_name or None,
                "latest_action": _opt_str(raw.get("latest_action_description")),
                "latest_action_date": _opt_str(raw.get("latest_action_date")),
            },
            source_id=ctx.source.id,
        )

    def _normalize_bill_row(
        self,
        ctx: RunContext,
        raw: Mapping[str, Any],
        row_index: int,
        source_uri: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]:
        """The claim-shape map applied to one bill record (P26.11 / SOURCES.10).

        The bill's own title/other_titles are scanned against the reviewed
        ``legislation_vocab.toml`` term set — the verbatim local match, never
        the API's fuzzy search. A bill matching a ``typed_claim`` term emits
        the bill-surface claim set; any other bill keeps the P26.4
        ``index_only`` evidence link unchanged. Returns ``(rows, matches,
        suppressed_term_ids)`` for the page's bill_query outcome row.
        """
        matches, suppressed = _matched_legislation(raw)
        typed = [m for m in matches if m["claim_shape"] == "typed_claim"]
        if not typed:
            return [self._normalize_bill_index(ctx, raw)], [], suppressed
        return (
            _bill_claim_rows(ctx.source.id, raw, row_index, source_uri, typed, suppressed),
            typed,
            suppressed,
        )

    def _normalize_bill_query(
        self,
        ctx: RunContext,
        raw: Mapping[str, Any],
        *,
        indexed: int,
        matched: int,
        terms: set[str],
        suppressed: set[str],
    ) -> dict[str, Any]:
        """The per-query outcome row — the sweep's honest per-state result (P26.11).

        One row per fetched bill_search capture: the reviewed plan row
        (jurisdiction, resolved session window, query family), the outcome
        (``matched`` = ≥1 bill emitted typed claims; ``empty`` = none), the
        page counts, and ``truncated`` when the API's ``total_items`` exceeds
        the bounded page — recorded, never silently widened. This is a
        non-claim record: it lands on the fetch record's document_outcomes,
        not the claim spine.
        """
        target = raw.get("target")
        if not isinstance(target, Mapping):
            target = {}
        pagination = raw.get("pagination")
        if not isinstance(pagination, Mapping):
            pagination = {}
        # OpenStates names the page total `pagination.total_items`; the
        # Congress.gov index names it `pagination.count` (P26.12).
        total = pagination.get("total_items")
        if not isinstance(total, int):
            total = pagination.get("count")
        returned = raw.get("result_count")
        row: dict[str, Any] = {
            "record_kind": "bill_query",
            "url": str(raw.get("source_uri") or target.get("url") or ""),
            "jurisdiction": _opt_str(target.get("jurisdiction")),
            "jurisdiction_id": _opt_str(target.get("jurisdiction_id")),
            "session": _opt_str(target.get("session")),
            "query_family": _opt_str(target.get("query_family")),
            "outcome": "matched" if matched else "empty",
            "total_items": int(total) if isinstance(total, int) else None,
            "returned_count": int(returned) if isinstance(returned, int) else 0,
            "bills_indexed": indexed,
            "bills_matched": matched,
            "matched_terms": sorted(terms),
            "suppressed_terms": sorted(suppressed),
            "truncated": bool(
                isinstance(total, int) and isinstance(returned, int) and total > returned
            ),
            "plan_version": _opt_str(target.get("plan_version"))
            or (
                str(congress_gov_plan()["plan_version"])
                if ctx.source.id == source_ids().get("congress_gov")
                else str(openstates_plan()["plan_version"])
            ),
            "legislation_vocab_version": legislation_vocab_version(),
            "capture_digest": _opt_str(raw.get("capture_digest")),
        }
        # P26.12 — the federal page's own plan-row fields (absent for the
        # state sweep; only stamped when the target carries them). A target
        # row without `congress` (e.g. a bare fixture run) still names it in
        # the URL's /bill/{congress} path — derived, never guessed.
        for extra in ("congress", "page_offset"):
            if target.get(extra) is not None:
                row[extra] = target[extra]
        if row.get("congress") is None:
            derived = _congress_number(row["url"])
            if derived is not None:
                row["congress"] = derived
        if row.get("page_offset") is None:
            qs = parse_qs(urlsplit(row["url"]).query)
            offset = qs.get("offset", [None])[0]
            if offset is not None and str(offset).isdigit():
                row["page_offset"] = int(offset)
        return _stamp(row, source_id=ctx.source.id)

    def _normalize_jurisdiction(self, ctx: RunContext, raw: Mapping[str, Any]) -> dict[str, Any]:
        """A /jurisdictions index row — recorded, never normalized to a fact (P26.11).

        The row IS the sweep's discovery surface: it records the jurisdiction,
        how many sessions the index carries, and the session the reviewed
        regular-class window rule resolved (or ``None`` when the index has no
        sessions — a query then runs unfiltered, recorded honestly).
        """
        sessions = raw.get("legislative_sessions") or []
        session = _resolve_session(
            sessions if isinstance(sessions, list) else [],
            openstates_plan()["session_window"]["classes"],
        )
        return _stamp(
            {
                "record_kind": "jurisdiction_index",
                "subject_id": f"jurisdiction:{ctx.source.id}:{_jurisdiction_abbr(raw.get('id'))}",
                "jurisdiction_id": _opt_str(raw.get("id")),
                "jurisdiction_name": _opt_str(raw.get("name")),
                "classification": _opt_str(raw.get("classification")),
                "sessions_count": len(sessions) if isinstance(sessions, list) else 0,
                "session_resolved": session,
                "plan_version": str(openstates_plan()["plan_version"]),
            },
            source_id=ctx.source.id,
        )

    def _normalize_congress_bill_row(
        self,
        ctx: RunContext,
        raw: Mapping[str, Any],
        row_index: int,
        source_uri: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]:
        """The claim-shape map applied to one Congress.gov bill record (P26.12).

        The bill's own title is scanned against the reviewed
        ``legislation_vocab.toml`` term set — the verbatim local match (the
        Congress.gov bill list has no server-side keyword query, so LOCAL
        matching is the only match of record). A bill matching a
        ``typed_claim`` term emits the federal bill-surface claim set (the
        P26.11 set + ``bill_chamber``); any other bill keeps the index_only
        evidence link. Returns ``(rows, matches, suppressed_term_ids)`` for
        the page's bill_query outcome row.
        """
        matches, suppressed = _matched_legislation(raw)
        typed = [m for m in matches if m["claim_shape"] == "typed_claim"]
        if not typed:
            return [self._normalize_congress_bill_index(ctx, raw)], [], suppressed
        return (
            _congress_bill_claim_rows(ctx.source.id, raw, row_index, source_uri, typed, suppressed),
            typed,
            suppressed,
        )

    def _normalize_congress_bill_index(
        self, ctx: RunContext, raw: Mapping[str, Any]
    ) -> dict[str, Any]:
        """A Congress.gov bill record as an index-only evidence link (P26.12, §3.1).

        A federal bill/resolution is **not** a §11.14 LegalInstrument — a
        pending bill is proposed law, never an enactment (the frozen
        LegalInstrumentType vocabulary has no ``bill``). The record is what
        the index *lists*: an ``index_only`` evidence link keyed to the bill,
        ``primary_record`` class — Congress.gov IS the primary record (the
        Library of Congress / legislative-clerk record itself, not an
        aggregator). Identifier, title, congress, chamber, and latest action
        ride as recorded index metadata — claims are never minted from them.
        """
        bill_id = _congress_external_id(raw)
        ref = _congress_public_url(raw) or _opt_str(raw.get("url")) or ""
        return _stamp(
            {
                "record_kind": "evidence_link",
                "subject_id": f"accountability:{ctx.source.id}:{bill_id}",
                "predicate_id": assert_predicate_allowed("event_source"),
                "value": ref or f"congress_gov:{bill_id}",
                "source_class": "primary_record",
                "raw_value": ref or bill_id,
                # SIG-EPIS-030 analogue: an index entry, never normalized to a fact.
                "index_only": True,
                "bill_identifier": _congress_identifier(raw)[0],
                "bill_title": _opt_str(raw.get("title")),
                "legislative_session": _opt_str(raw.get("congress")),
                "legislative_jurisdiction": str(congress_gov_config()["jurisdiction_label"]),
                "bill_chamber": _opt_str(raw.get("originChamber")),
                "latest_action": _opt_str(
                    (raw.get("latestAction") or {}).get("text")
                    if isinstance(raw.get("latestAction"), Mapping)
                    else None
                ),
                "latest_action_date": _opt_str(
                    (raw.get("latestAction") or {}).get("actionDate")
                    if isinstance(raw.get("latestAction"), Mapping)
                    else None
                ),
            },
            source_id=ctx.source.id,
        )

    # -- link + load --
    # SIG-INGEST-034: the connector emits candidate identifiers and NEVER resolves
    # entities itself; the identity layer decides which named organisations stand as
    # entities (P31.5 / ADR-112) and the claim sink mints them.

    def link(self, ctx: RunContext, normalized: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Append the ``event_organizations`` entity-ref claims (P31.5 / ADR-112).

        One entity-ref claim per organisation an accountability event names, each
        accepted by :func:`resolution.partner_identity.partner_identity`.
        ``proceeding_parties`` is deliberately excluded: litigants are routinely
        natural persons (Part VIII), and no organisation marker makes a party list
        safe to mint from.
        """
        return partner_ref_rows(normalized, predicates=_PARTNER_PREDICATES)

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Produce the L1 rows; the driver asserts them (live only)."""
        return load_claims_for_l1(linked)

    # -- helpers --
    def _is_courtlistener(self, ctx: RunContext, target: Mapping[str, Any]) -> bool:
        courtlistener_id = source_ids().get("courtlistener")
        if ctx.source.id == courtlistener_id:
            return True
        return _artifact_kind_of_target(target) == "courtlistener"


# --- module-private helpers ---------------------------------------------------


# --- the surveillance-legislation sweep helpers (P26.11 / SOURCES.10) ---------


def _jurisdiction_abbr(ocd_id: Any) -> str:
    """The two-letter jurisdiction code from an OCD jurisdiction id.

    ``ocd-jurisdiction/country:us/state:tx/government`` → ``tx``;
    ``district:dc`` → ``dc``; ``territory:pr`` → ``pr``. The code is the
    ``jurisdiction=<abbr>`` filter the v3 bills endpoint accepts (verified
    live 2026-09-18 incl. territory ``pr``).
    """
    text = str(ocd_id or "")
    for part in text.split("/"):
        if part.startswith(("state:", "district:", "territory:")):
            return part.split(":", 1)[1]
    return text.rsplit("/", 1)[-1].removesuffix("government").strip(":")


def _resolve_session(sessions: Sequence[Mapping[str, Any]], classes: Sequence[str]) -> str | None:
    """The current-session window for one jurisdiction (the reviewed rule).

    The latest-start session among the reviewed regular classes (``primary`` /
    ``regular``) — a called/special session never shadows the legislature's
    main session. With no class match the latest session of ANY class wins; a
    jurisdiction with no sessions returns ``None`` (the query then runs
    unfiltered — recorded, never invented). Ordering is canonical:
    ``(start_date, identifier)`` — a data order, never the server's.
    """
    regular = [s for s in sessions if str(s.get("classification") or "") in classes]
    pool = regular or list(sessions)
    best = max(
        pool,
        key=lambda s: (str(s.get("start_date") or ""), str(s.get("identifier") or "")),
        default=None,
    )
    return _opt_str(best.get("identifier")) if best else None


def _jurisdictions_from_captures(
    ctx: RunContext, captures: Sequence[CaptureRef]
) -> list[Mapping[str, Any]]:
    """The jurisdiction rows from the captured /jurisdictions index pages.

    Reads stored captures only (network-isolated, SIG-INGEST-002). Rows are
    merged + deduped by jurisdiction id and returned in canonical id order —
    the generated target set is deterministic given the same index content
    (SIG-INGEST-003). A page that is not a results payload is ContentDrift —
    fail closed, never a fabricated jurisdiction set.
    """
    index_cfg = openstates_plan()["jurisdiction_index"]
    endpoint = str(index_cfg["endpoint"])
    rows: dict[str, Mapping[str, Any]] = {}
    for capture in captures:
        uri = str(capture.source_uri)
        if _artifact_kind_of_uri(uri) != "openstates_jurisdictions" or endpoint not in uri:
            continue
        try:
            payload = json.loads(ctx.captures.get(capture.digest))
        except json.JSONDecodeError as exc:
            raise ContentDrift(
                ctx.source.id,
                "the captured jurisdictions index is not valid JSON",
                details=str(exc),
            ) from exc
        if not isinstance(payload, Mapping) or not _has_results(payload):
            raise ContentDrift(
                ctx.source.id,
                "the captured jurisdictions index is not a results page",
                details=type(payload).__name__,
            )
        for row in payload["results"]:
            if isinstance(row, Mapping) and row.get("id"):
                rows[str(row["id"])] = row
    return [rows[k] for k in sorted(rows)]


def _bill_query_targets(
    jurisdictions: Sequence[Mapping[str, Any]], plan: Mapping[str, Any]
) -> list[Mapping[str, Any]]:
    """The bounded per-jurisdiction × per-family bill_search targets (P26.11).

    One target per jurisdiction per reviewed query family — ``q`` is the
    family's phrases OR'd into a single bounded search (the API's fuzzy
    recall net; verbatim match attribution is LOCAL on the returned titles).
    The resolved session window rides the target row verbatim; a
    session-less jurisdiction queries unfiltered. Hard-bounded by the plan's
    ``max_queries`` — exceeding it truncates loud, it does not crawl.
    """
    cfg = plan["bills_query"]
    classes = plan["session_window"]["classes"]
    base = str(openstates_config()["api_base"]).rstrip("/")
    per_page = int(cfg["per_page"])
    out: list[Mapping[str, Any]] = []
    for j in jurisdictions:
        abbr = _jurisdiction_abbr(j.get("id"))
        sessions = j.get("legislative_sessions") or []
        session = _resolve_session(sessions if isinstance(sessions, list) else [], classes)
        for family in plan["query_families"]:
            params: dict[str, Any] = {
                "jurisdiction": abbr,
                "q": " OR ".join(str(p) for p in family["phrases"]),
                "per_page": per_page,
                "sort": str(cfg["sort"]),
            }
            if session:
                params["session"] = session
            url = f"{base}{cfg['endpoint']}?{urlencode(params)}"
            out.append(
                {
                    "id": f"openstates-bills-{abbr}-{family['id']}",
                    "url": url,
                    "kind": "bill_search",
                    "jurisdiction_id": str(j.get("id") or ""),
                    "jurisdiction": _opt_str(j.get("name")),
                    "jurisdiction_abbr": abbr,
                    "session": session,
                    "query_family": str(family["id"]),
                    "query_phrases": [str(p) for p in family["phrases"]],
                    "per_page": per_page,
                    "sort": str(cfg["sort"]),
                    "plan_version": str(plan["plan_version"]),
                }
            )
            if len(out) >= int(cfg["max_queries"]):
                return out
    return out


def _bill_search_target_for(ctx: RunContext, uri: str) -> Mapping[str, Any] | None:
    """The bill_search target row a capture fetched (P26.11), or ``None``.

    A resolved continuation target first (the sweep's generated rows carry
    the query-plan fields), then a configured seed target (a fixture run).
    """
    target = ctx.resolved_targets.get(uri)
    if target is not None and target.get("kind") == "bill_search":
        return target
    for candidate in ctx.parameters.get("targets", []):
        if str(candidate.get("url")) == uri and candidate.get("kind") == "bill_search":
            return candidate
    return None


# --- the federal-legislation sweep helpers (P26.12 / SOURCES.11) -------------


def _congress_page_target_for(ctx: RunContext, uri: str) -> Mapping[str, Any] | None:
    """The congress_bill_index target row a capture fetched (P26.12), or ``None``.

    A resolved continuation target first (the sweep's generated page rows
    carry the query-plan fields), then a configured seed target (a fixture
    run).
    """
    target = ctx.resolved_targets.get(uri)
    if target is not None and target.get("kind") == "congress_bill_index":
        return target
    for candidate in ctx.parameters.get("targets", []):
        if str(candidate.get("url")) == uri and candidate.get("kind") == "congress_bill_index":
            return candidate
    return None


def _congress_page_targets(
    ctx: RunContext, captures: Sequence[CaptureRef], plan: Mapping[str, Any]
) -> list[Mapping[str, Any]]:
    """The bounded remaining bill-index pages for the captured seed pages (P26.12).

    Only a capture whose ``source_uri`` is a CONFIGURED seed target
    (``kind='congress_bill_index'`` in ``ctx.parameters['targets']``) expands —
    a generated page never re-expands, so exactly one bounded pass happens.
    Each seed's ``pagination.count`` names its congress index size; the
    remaining pages (``offset`` steps of ``per_page``) are generated up to
    the plan's ``max_pages_per_congress`` bound — a count beyond the bound
    truncates loud on every page's outcome row, it does not crawl. Reads
    stored captures only (SIG-INGEST-002); a seed capture that is not a
    bills page is ContentDrift — fail closed, never a fabricated page set.
    """
    cfg = plan["bill_index"]
    per_page = int(cfg["per_page"])
    max_pages = int(cfg["max_pages_per_congress"])
    base = str(congress_gov_config()["api_base"]).rstrip("/")
    endpoint = str(cfg["endpoint"])
    seeds = {
        str(t.get("url")): t
        for t in ctx.parameters.get("targets", [])
        if t.get("kind") == "congress_bill_index"
    }
    out: dict[str, Mapping[str, Any]] = {}
    for capture in captures:
        uri = str(capture.source_uri)
        seed = seeds.get(uri)
        if seed is None or _artifact_kind_of_uri(uri) != "congress_gov_bills":
            continue
        try:
            payload = json.loads(ctx.captures.get(capture.digest))
        except json.JSONDecodeError as exc:
            raise ContentDrift(
                ctx.source.id,
                "the captured congress bill-index seed page is not valid JSON",
                details=str(exc),
            ) from exc
        if (
            not isinstance(payload, Mapping)
            or not isinstance(payload.get("bills"), list)
            or "error" in payload
        ):
            raise ContentDrift(
                ctx.source.id,
                "the captured congress bill-index seed page is not a bills page",
                details=type(payload).__name__,
            )
        pagination = payload.get("pagination")
        count = (
            int(pagination["count"])
            if isinstance(pagination, Mapping) and isinstance(pagination.get("count"), int)
            else 0
        )
        congress = str(seed.get("congress") or _congress_number(uri) or "")
        if not congress:
            raise ContentDrift(
                ctx.source.id,
                "the congress bill-index seed target names no congress",
                details=uri,
            )
        # The seed IS page 1; generate pages 2..bound (deduped by URL across
        # seeds — two seeds for one congress yield one page set). The bound is
        # PER CONGRESS (the plan's `max_pages_per_congress`).
        bound_items = min(count, max_pages * per_page)
        generated = 0
        for offset in range(per_page, bound_items, per_page):
            url = f"{base}{endpoint}/{congress}?" + urlencode(
                {"limit": per_page, "offset": offset, "format": "json"}
            )
            if url in out or url in seeds:
                continue
            out[url] = {
                "id": f"congress-gov-bill-{congress}-p{offset // per_page + 1}",
                "url": url,
                "kind": "congress_bill_index",
                "congress": congress,
                "page_offset": offset,
                "per_page": per_page,
                "plan_version": str(plan["plan_version"]),
            }
            generated += 1
            if generated >= max_pages - 1:
                break
    # Pages emit in numeric offset order (a URL sort would rank offset=1000
    # before offset=250) — deterministic and semantically paged.
    return sorted(out.values(), key=lambda t: int(t["page_offset"]))


def _congress_number(uri: str) -> str | None:
    """The congress number from a ``/bill/{congress}`` path segment, or ``None``."""
    path = uri.split("?", 1)[0].split("#", 1)[0]
    for part in path.split("/"):
        if part.isdigit() and 1 <= int(part) <= 200:
            return part
    return None


def _congress_external_id(raw: Mapping[str, Any]) -> str:
    """The bill's canonical external id — ``{congress}-{type}-{number}``
    (the API item path ``/bill/119/s/4342`` lowercased)."""
    congress = _opt_str(raw.get("congress"))
    bill_type = _opt_str(raw.get("type"))
    number = _opt_str(raw.get("number"))
    if congress and bill_type and number:
        return f"{congress}-{bill_type.lower()}-{number}"
    return _slug(str(raw))


def _congress_identifier(raw: Mapping[str, Any]) -> tuple[str | None, str | None]:
    """``(typed, raw)`` bill identifier — the conventional citation form as the
    typed value (``S. 4342``), the record's verbatim ``"S 4342"`` as raw. A type
    outside the reviewed prefix map falls back to the verbatim form — never
    guessed."""
    bill_type = _opt_str(raw.get("type"))
    number = _opt_str(raw.get("number"))
    if not bill_type or not number:
        return None, None
    raw_id = f"{bill_type} {number}"
    prefix = congress_gov_config()["type_prefixes"].get(bill_type)
    return (f"{prefix} {number}" if prefix else raw_id), raw_id


def _congress_ordinal(congress: Any) -> str | None:
    """``119`` → ``119th`` — the ordinal the congress.gov public page path uses."""
    try:
        n = int(str(congress))
    except (TypeError, ValueError):
        return None
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _congress_public_url(raw: Mapping[str, Any]) -> str | None:
    """The derived congress.gov public bill page — the official legislature
    record URL (the same precedence the OpenStates path gives the record's own
    source URL). The derivation is the reviewed ``type_slugs`` map +
    ``{ordinal}-congress`` path; a type outside the map yields ``None`` (the
    caller falls back to the record's verbatim API url — never guessed)."""
    bill_type = _opt_str(raw.get("type"))
    number = _opt_str(raw.get("number"))
    ordinal = _congress_ordinal(raw.get("congress"))
    slug = congress_gov_config()["type_slugs"].get(str(bill_type)) if bill_type else None
    if not (slug and number and ordinal):
        return None
    return f"https://www.congress.gov/bill/{ordinal}-congress/{slug}/{number}"


def _congress_latest_action(raw: Mapping[str, Any]) -> tuple[str | None, str | None]:
    """``(text, date)`` of the record's latestAction — verbatim, never inferred."""
    latest = raw.get("latestAction")
    if not isinstance(latest, Mapping):
        return None, None
    return _opt_str(latest.get("text")), _opt_str(latest.get("actionDate"))


def _congress_bill_claim_rows(
    source_id: str,
    raw: Mapping[str, Any],
    row_index: int,
    source_uri: str,
    matches: Sequence[Mapping[str, Any]],
    suppressed: set[str],
) -> list[dict[str, Any]]:
    """The typed claim rows for a Congress.gov bill matching the vocab (P26.12).

    Claims: external id, identifier (conventional citation as typed, verbatim
    as raw), title, session (the congress number — the federal session),
    jurisdiction (the reviewed constant — the source IS the federal
    legislature), chamber (the record's verbatim originChamber), status (the
    record's own latest-action text), status date, and one
    ``bill_matched_keyword`` per typed term carrying the VERBATIM literal as
    raw_value with a byte-range-into-title locator. Every claim carries the
    bill's public record URL + a row locator into the captured page
    (``capture_url`` anchors it). A ``legislative_bill`` entity row records
    the surface — it is PROPOSED law, never a §11.14 LegalInstrument claim.
    No volatile field (no retrieval timestamp, no capture id) touches a claim
    dict — claim identity is the stable bill content (SIG-INGEST-003/017),
    so an unchanged record digests identically on ANY re-run; the observation
    time lives on the capture/evidence (claim_evidence → capture →
    retrieved_at).
    """
    bill_id = _congress_external_id(raw)
    subject_id = f"legislative_bill:{source_id}:{bill_id}"
    cfg = congress_gov_config()
    record_url = _congress_public_url(raw) or _opt_str(raw.get("url")) or ""
    api_url = _opt_str(raw.get("url"))
    latest_action, latest_action_date = _congress_latest_action(raw)
    identifier_typed, identifier_raw = _congress_identifier(raw)
    chamber = _opt_str(raw.get("originChamber"))
    congress = _opt_str(raw.get("congress"))
    bill_type = _opt_str(raw.get("type"))
    number = _opt_str(raw.get("number"))
    introduced = _opt_str(raw.get("introducedDate"))
    jurisdiction = str(cfg["jurisdiction_label"])
    spdx = str(cfg.get("spdx") or "CC0-1.0")

    def _evidence(locator: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
        ev = {
            "source_url": record_url,
            "capture_url": source_uri,
            "extraction_method": "congress_gov_bill_json",
            "locator": dict(locator),
        }
        ev.update(extra)
        return ev

    def _claim(
        predicate: str,
        value: Any,
        raw_value: str,
        evidence: Mapping[str, Any],
        **extra: Any,
    ) -> dict[str, Any]:
        row: dict[str, Any] = {
            "record_kind": "claim",
            "subject_id": subject_id,
            "predicate_id": assert_predicate_allowed(predicate),
            "raw_value": raw_value,
            "value": value,
            "license": spdx,
            "evidence_genre": "bill_index",
            "evidence": dict(evidence),
        }
        row.update({k: v for k, v in extra.items() if v is not None})
        return _stamp(row, source_id=source_id)

    row_evidence = _evidence(Locator.row(row_index).to_row())
    rows: list[dict[str, Any]] = [
        _stamp(
            {
                "record_kind": "legislative_bill",
                "subject_id": subject_id,
                "predicate_id": assert_predicate_allowed("legislative_bill"),
                "external_id": bill_id,
                "bill_identifier": identifier_typed,
                "bill_title": _opt_str(raw.get("title")),
                "legislative_session": congress,
                "legislative_jurisdiction": jurisdiction,
                "bill_chamber": chamber,
                "bill_type": bill_type,
                "congress": int(congress) if congress and congress.isdigit() else None,
                "introduced_date": introduced,
                "latest_action": latest_action,
                "latest_action_date": latest_action_date,
                "record_url": record_url,
                "api_url": api_url,
                "matched_terms": sorted(str(m["term_id"]) for m in matches),
                "suppressed_terms": sorted(suppressed),
                "evidence_genre": "bill_index",
                "evidence": row_evidence,
            },
            source_id=source_id,
        )
    ]
    rows.append(
        _claim(
            "bill_external_id",
            bill_id,
            bill_id,
            row_evidence,
            candidate_identifier=(
                {
                    "scheme": "congress.gov.bill",
                    "value": f"{congress}/{str(bill_type).lower()}/{number}",
                }
                if congress and bill_type and number
                else None
            ),
        )
    )
    if identifier_typed:
        rows.append(
            _claim(
                "bill_identifier",
                identifier_typed,
                identifier_raw or identifier_typed,
                row_evidence,
            )
        )
    title = _opt_str(raw.get("title"))
    if title:
        rows.append(_claim("bill_title", title, title, row_evidence))
    if congress:
        rows.append(_claim("bill_session", congress, congress, row_evidence))
    rows.append(_claim("bill_jurisdiction", jurisdiction, jurisdiction, row_evidence))
    if chamber:
        rows.append(_claim("bill_chamber", chamber, chamber, row_evidence))
    if latest_action:
        rows.append(_claim("bill_status", latest_action, latest_action, row_evidence))
    if latest_action_date:
        rows.append(
            _claim("bill_status_date", latest_action_date, latest_action_date, row_evidence)
        )
    for match in matches:
        rows.append(
            _claim(
                "bill_matched_keyword",
                match["term_id"],
                str(match["literal"]),
                _evidence(
                    Locator.byte_range(int(match["start"]), int(match["end"])).to_row(),
                    field=str(match["field"]),
                    record_row=row_index,
                ),
                term_label=match["term_label"],
                term_kind=match["term_kind"],
            )
        )
    return rows


def _guard_token(text: str) -> str | None:
    """The first Part VIII forbidden token in ``text``, or ``None`` (§0.7/§43.2)."""
    low = text.lower()
    for token in legislation_forbidden():
        if token in low:
            return token
    return None


def _bill_text_fields(raw: Mapping[str, Any]) -> list[tuple[str, str]]:
    """The verbatim text fields the term scan reads — title first, then
    the record's alternate titles (each named for its evidence ``field``)."""
    fields: list[tuple[str, str]] = [("title", str(raw.get("title") or ""))]
    for i, other in enumerate(raw.get("other_titles") or []):
        text = other.get("title") if isinstance(other, Mapping) else other
        if text:
            fields.append((f"other_titles[{i}]", str(text)))
    return fields


def _matched_legislation(
    raw: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], set[str]]:
    """The verbatim legislation-term matches for one bill record (P26.11).

    The LOCAL scan is the match of record — the v3 ``q`` search is fuzzy (it
    returns commemorative resolutions for ``facial recognition``), so a claim
    is minted only where the bill's own title/other_titles literally carries
    a reviewed pattern. One match per term (title wins over alternates — the
    canonical field order). A literal tripping the Part VIII guard is
    suppressed and reported on the second return value, never emitted.
    """
    matches: list[dict[str, Any]] = []
    suppressed: set[str] = set()
    for term in legislation_terms():
        for field_name, text in _bill_text_fields(raw):
            if not text:
                continue
            hit = None
            for pattern in term.get("patterns", ()):
                found = re.search(str(pattern), text, re.IGNORECASE)
                if found:
                    hit = found
                    break
            if hit is None:
                continue
            literal = hit.group(0)
            if _guard_token(literal) is not None:
                suppressed.add(str(term["id"]))
                break
            matches.append(
                {
                    "term_id": str(term["id"]),
                    "term_label": str(term.get("label") or term["id"]),
                    "term_kind": str(term.get("kind") or ""),
                    "claim_shape": str(term.get("claim_shape") or "index_only"),
                    "field": field_name,
                    "literal": literal,
                    "start": hit.start(),
                    "end": hit.end(),
                }
            )
            break
    return matches, suppressed


def _bill_record_url(raw: Mapping[str, Any]) -> str:
    """The bill record URL — the official legislature page first, else the
    OpenStates record (the P26.4 index-link precedence)."""
    for src in raw.get("sources") or []:
        if isinstance(src, Mapping) and src.get("url"):
            return str(src["url"])
    return str(raw.get("openstates_url") or raw.get("url") or "")


def _bill_claim_rows(
    source_id: str,
    raw: Mapping[str, Any],
    row_index: int,
    source_uri: str,
    matches: Sequence[Mapping[str, Any]],
    suppressed: set[str],
) -> list[dict[str, Any]]:
    """The typed claim rows for a bill whose record matched the vocab (P26.11).

    Claims: identifier, title, session, jurisdiction, status (the record's
    own latest-action text — OpenStates' status surface), status date,
    external id, and one ``bill_matched_keyword`` per typed term carrying
    the VERBATIM literal as raw_value with a byte-range-into-field locator.
    Every claim carries the bill record URL + a row locator into the
    captured results array (``capture_url`` anchors it). A ``legislative_bill``
    entity row records the surface — it is PROPOSED law, never a §11.14
    LegalInstrument claim. No volatile field (no retrieval timestamp, no
    capture id) touches a claim dict — claim identity is the stable bill
    content (SIG-INGEST-003/017).
    """
    bill_id = str(raw.get("id") or raw.get("identifier") or _slug(str(raw)))
    subject_id = f"legislative_bill:{source_id}:{bill_id}"
    record_url = _bill_record_url(raw)
    jurisdiction = raw.get("jurisdiction")
    jurisdiction_name = (
        str(jurisdiction.get("name"))
        if isinstance(jurisdiction, Mapping)
        else _opt_str(jurisdiction) or ""
    )
    jurisdiction_id = str(jurisdiction.get("id")) if isinstance(jurisdiction, Mapping) else None
    latest_action = _opt_str(raw.get("latest_action_description"))
    latest_action_date = _opt_str(raw.get("latest_action_date"))
    # Claims carry NO ``observed_at``: the claim asserts "the OpenStates
    # record contains this field" — identity is stable bill content, so an
    # unchanged record digests identically on ANY re-run (SIG-INGEST-003/017;
    # the atlas optional-observed_at pattern). The observation time lives on
    # the capture/evidence (claim_evidence → capture → retrieved_at), and the
    # record's own action date stays verbatim in bill_status_date — never an
    # observed_at (a bill's latest_action_date is routinely future-dated and
    # trips claim_observed_not_future).
    spdx = str(openstates_config().get("spdx") or "CC0-1.0")

    def _evidence(locator: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
        ev = {
            "source_url": record_url,
            "capture_url": source_uri,
            "extraction_method": "openstates_bills_json",
            "locator": dict(locator),
        }
        ev.update(extra)
        return ev

    def _claim(
        predicate: str,
        value: Any,
        raw_value: str,
        evidence: Mapping[str, Any],
        **extra: Any,
    ) -> dict[str, Any]:
        row: dict[str, Any] = {
            "record_kind": "claim",
            "subject_id": subject_id,
            "predicate_id": assert_predicate_allowed(predicate),
            "raw_value": raw_value,
            "value": value,
            "license": spdx,
            "evidence_genre": "bill_index",
            "evidence": dict(evidence),
        }
        row.update({k: v for k, v in extra.items() if v is not None})
        return _stamp(row, source_id=source_id)

    row_evidence = _evidence(Locator.row(row_index).to_row())
    rows: list[dict[str, Any]] = [
        _stamp(
            {
                "record_kind": "legislative_bill",
                "subject_id": subject_id,
                "predicate_id": assert_predicate_allowed("legislative_bill"),
                "external_id": bill_id,
                "bill_identifier": _opt_str(raw.get("identifier")),
                "bill_title": _opt_str(raw.get("title")),
                "legislative_session": _opt_str(raw.get("session")),
                "legislative_jurisdiction": jurisdiction_name or None,
                "latest_action": latest_action,
                "latest_action_date": latest_action_date,
                "record_url": record_url,
                "source_urls": [
                    str(s["url"])
                    for s in raw.get("sources") or []
                    if isinstance(s, Mapping) and s.get("url")
                ],
                "matched_terms": sorted(str(m["term_id"]) for m in matches),
                "suppressed_terms": sorted(suppressed),
                "evidence_genre": "bill_index",
                "evidence": row_evidence,
            },
            source_id=source_id,
        )
    ]
    rows.append(
        _claim(
            "bill_external_id",
            bill_id,
            bill_id,
            row_evidence,
            candidate_identifier={"scheme": "ocd-bill", "value": bill_id},
        )
    )
    identifier = _opt_str(raw.get("identifier"))
    if identifier:
        rows.append(_claim("bill_identifier", identifier, identifier, row_evidence))
    title = _opt_str(raw.get("title"))
    if title:
        rows.append(_claim("bill_title", title, title, row_evidence))
    session = _opt_str(raw.get("session"))
    if session:
        rows.append(_claim("bill_session", session, session, row_evidence))
    if jurisdiction_name:
        rows.append(
            _claim(
                "bill_jurisdiction",
                jurisdiction_name,
                jurisdiction_name,
                row_evidence,
                candidate_identifier=(
                    {"scheme": "openstates.jurisdiction", "value": jurisdiction_id}
                    if jurisdiction_id
                    else None
                ),
            )
        )
    if latest_action:
        rows.append(_claim("bill_status", latest_action, latest_action, row_evidence))
    if latest_action_date:
        rows.append(
            _claim("bill_status_date", latest_action_date, latest_action_date, row_evidence)
        )
    for match in matches:
        rows.append(
            _claim(
                "bill_matched_keyword",
                match["term_id"],
                str(match["literal"]),
                _evidence(
                    Locator.byte_range(int(match["start"]), int(match["end"])).to_row(),
                    field=str(match["field"]),
                    record_row=row_index,
                ),
                term_label=match["term_label"],
                term_kind=match["term_kind"],
            )
        )
    return rows


def _stamp(row: dict[str, Any], *, source_id: str) -> dict[str, Any]:
    """Stamp a row with its source id and the connector vocabulary version (§20).

    The accountability sources are REFERENCE-posture with per-source rights that
    the lead research pass left UNDETERMINED (sources.toml); the export compartment
    is decided per source by the licence gate (SIG-LIC-009a), so — like records —
    the connector does not pin a single compartment here. It records the source id
    and the vocabulary version every row is interpretable against.
    """
    row.setdefault("source_id", source_id)
    row.setdefault("vocab_version", vocab_version())
    return row


def load_claims_for_l1(claims: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Add the generated ``claim_id`` + transaction time each L1 claim/entity row needs.

    Mirrors the framework's load contract: ``claim_id`` and ``sys_period`` are the
    two non-deterministic columns the reproducibility fingerprint excludes
    (SIG-INGEST-003), so replay is byte-identical modulo exactly these. Only the
    claim/entity/evidence-link rows get an identity + transaction time; unmapped and
    context rows keep their own keys.
    """
    stamped_kinds = {
        "accountability_event",
        "legal_proceeding",
        "legislative_bill",
        "claim",
        "evidence_link",
    }
    out: list[dict[str, Any]] = []
    for claim in claims:
        if claim.get("record_kind") in stamped_kinds:
            out.append(
                {
                    **claim,
                    "claim_id": str(uuid4()),
                    "sys_period": f"[{datetime.now(UTC).isoformat()},)",
                }
            )
        else:
            out.append(dict(claim))
    return out


def _artifact_kind(capture: CaptureRef) -> str:
    """Infer the Atlas artifact kind from a capture's source URI (§23.8)."""
    return _artifact_kind_of_uri(capture.source_uri)


def _artifact_kind_of_target(target: Mapping[str, Any]) -> str:
    kind = target.get("artifact_kind")
    if kind:
        return str(kind)
    return _artifact_kind_of_uri(str(target.get("url", "")))


def _artifact_kind_of_uri(uri: str) -> str:
    low = uri.lower()
    if "courtlistener" in low or "/recap" in low:
        return "courtlistener"
    # The Congress.gov congress-scoped bill index that seeds + fills the
    # federal sweep (P26.12) — checked before the generic kinds; both the
    # /v3/bill/{congress} list pages and any /bill item url carry
    # "congress.gov".
    if "congress.gov" in low:
        return "congress_gov_bills"
    # The jurisdictions index that seeds the 50-state sweep (P26.11) — checked
    # before the generic bill-search kind since both carry "openstates".
    if "openstates" in low and "/jurisdictions" in low:
        return "openstates_jurisdictions"
    if "openstates" in low:
        return "openstates"
    if "abuse" in low or "kansas.watch" in low:
        return "abuse_library"
    if "source_index" in low or "source-index" in low:
        return "source_index_csv"
    if low.endswith(".geojson") or "geojson" in low:
        return "geojson"
    if "data_dictionary" in low or "dictionary" in low:
        return "data_dictionary"
    if "archive" in low:
        return "research_archive"
    if low.endswith(".csv") or "issue" in low:
        return "issue_record_csv"
    return "issue_record_csv"


def _normalize_epistemic(raw: str | None) -> str | None:
    """Map an upstream epistemic label onto the vocabulary term, or ``None``.

    Casing/whitespace only ("Alleged" / " alleged " -> "alleged"): the typed value
    must be a vocabulary term, but the connector never re-interprets one status as
    another. A label that does not land on a term returns ``None`` (recorded as
    unmapped, never guessed — SIG-ONTO-038, §3.1).
    """
    if raw is None:
        return None
    candidate = raw.strip().lower()
    return candidate if candidate in epistemic_statuses() else None


def _raw_value_of(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return ";".join(str(v) for v in value)
    return str(value)


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _slug(text: str) -> str:
    return "_".join(str(text).strip().lower().split())


def _split(value: Any) -> tuple[str, ...]:
    """Split a repeatable cell (``;``/``|``/``,`` separated) into non-empty refs (P2-safe)."""
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(str(v).strip() for v in value if str(v).strip())
    text = str(value).strip()
    if not text:
        return ()
    for sep in (";", "|"):
        if sep in text:
            return tuple(p.strip() for p in text.split(sep) if p.strip())
    if "," in text and ("http" not in text):
        return tuple(p.strip() for p in text.split(",") if p.strip())
    return (text,)


def _first_present(header: Sequence[str], candidates: Sequence[str]) -> str | None:
    present = set(header)
    for c in candidates:
        if c in present:
            return c
    return None


def _first_value(raw: Mapping[str, Any], candidates: Sequence[str]) -> str | None:
    for c in candidates:
        if c in raw and str(raw[c]).strip():
            return str(raw[c]).strip()
    return None


def _has_results(payload: Any) -> bool:
    return isinstance(payload, Mapping) and "results" in payload


def _has_entries(payload: Any) -> bool:
    return isinstance(payload, Mapping) and "entries" in payload


# Column-name aliases tolerated across the upstream exports (the Atlas keys on its
# own column names; these are the common shapes). Kept here as the connector's
# tolerant read layer, not in the vocabulary (they are parser detail, not a
# reviewed value set).
_ID_COLUMNS = ("id", "incident_id", "issue_id", "record_id", "slug")
_CATEGORY_COLUMNS = ("category", "record_category", "issue_type", "type")
_EPISTEMIC_COLUMNS = ("epistemic_status", "status", "epistemic", "verdict")
_DATE_COLUMNS = ("date", "incident_date", "event_date")
_ORG_COLUMNS = ("organizations", "agency", "agencies", "org")
_TECH_COLUMNS = ("technologies", "technology", "tech")
_PARTY_CLASS_COLUMNS = ("affected_party_class", "affected_class", "affected")
_SOURCE_URL_COLUMNS = ("source_url", "url", "source", "link")
_SOURCE_CLASS_COLUMNS = ("source_class", "class", "source_type")


__all__ = [
    "UNMAPPED_CATEGORY_TASK_TYPE",
    "AccountabilityConnector",
    "AccountabilityEventRecord",
    "CrawlAttempted",
    "EvidenceLink",
    "InvalidAccountabilityEvent",
    "InvalidLegalProceeding",
    "InvalidSourceClass",
    "LegalProceedingRecord",
    "MissingEpistemicStatus",
    "PredicateNotAllowed",
    "UnreviewedReportTarget",
    "assert_oversight_report_target",
    "assert_predicate_allowed",
    "assert_targeted_lookup",
    "atlas_artifacts",
    "canary_findings",
    "category_crosswalk",
    "congress_gov_config",
    "congress_gov_plan",
    "courtlistener_config",
    "crosswalk",
    "epistemic_statuses",
    "event_types",
    "factual_epistemic_statuses",
    "forbidden_predicate_genres",
    "is_predicate_allowed",
    "legislation_terms",
    "legislation_vocab",
    "legislation_vocab_version",
    "load_claims_for_l1",
    "openstates_config",
    "openstates_plan",
    "oversight_report_config",
    "oversight_report_source_ids",
    "parse_csv",
    "postures",
    "predicate_allowlist",
    "source_classes",
    "source_ids",
    "unmapped_category_task",
    "vocab",
    "vocab_version",
]
