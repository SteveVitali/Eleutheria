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
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import cache
from typing import Any
from uuid import uuid4

from ._data import load_table
from .curated_index import CuratedIndexEntry
from .stages import CaptureRef, Connector, FetchResult, RunContext, register

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
        return targets

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """Obtain bytes for one target through the shared politeness layer only (SIG-INGEST-011)."""
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        if self._is_courtlistener(ctx, target):
            assert_targeted_lookup(target)
        return ctx.fetcher.fetch(str(target["url"]))

    # -- interpretation (pure functions of the capture) --
    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Structure the captured bytes by artifact kind.

        The kind is carried on the capture's ``source_uri`` (the artifact the
        target named): a CSV artifact (issue-record or source-index) is parsed to
        header + rows; a court/abuse JSON payload is parsed as JSON; a GeoJSON /
        data-dictionary / research-archive artifact is consumed as context (§23.8).
        """
        data = ctx.captures.get(capture.digest)
        kind = _artifact_kind(capture)
        if kind in {"issue_record_csv", "source_index_csv"}:
            return {"kind": kind, "capture": capture, **parse_csv(data)}
        if kind in {"courtlistener", "abuse_library"}:
            return {"kind": kind, "capture": capture, "payload": json.loads(data)}
        # geojson / data_dictionary / research_archive: consumed as context.
        return {"kind": kind, "capture": capture, "byte_size": len(data)}

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """Raw records with locators, preserving raw values (P2)."""
        kind = str(parsed["kind"])
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
        # A consumed-as-context artifact (geojson / data_dictionary / research_archive).
        return [{"record_kind": "context", "artifact_kind": kind}]

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """Typed rows beside preserved raw values (P2), confined to the allowlist."""
        out: list[dict[str, Any]] = []
        for raw in raw_claims:
            kind = raw["record_kind"]
            if kind == "issue_record":
                out.extend(self._normalize_issue_record(ctx, raw["raw"]))
            elif kind == "source_index":
                out.append(self._normalize_source_index(ctx, raw["raw"]))
            elif kind == "court_record":
                out.extend(self._normalize_court_record(ctx, raw["raw"]))
            elif kind == "abuse_entry":
                out.append(self._normalize_abuse_entry(ctx, raw["raw"]))
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

    # -- link + load --
    # link() is inherited (identity): SIG-INGEST-034 — the connector emits candidate
    # identifiers and NEVER resolves entities itself; resolution is P03.2/P05.1.

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
    stamped_kinds = {"accountability_event", "legal_proceeding", "claim", "evidence_link"}
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
    "assert_predicate_allowed",
    "assert_targeted_lookup",
    "atlas_artifacts",
    "canary_findings",
    "category_crosswalk",
    "courtlistener_config",
    "crosswalk",
    "epistemic_statuses",
    "event_types",
    "factual_epistemic_statuses",
    "forbidden_predicate_genres",
    "is_predicate_allowed",
    "load_claims_for_l1",
    "parse_csv",
    "postures",
    "predicate_allowlist",
    "source_classes",
    "source_ids",
    "unmapped_category_task",
    "vocab",
    "vocab_version",
]
