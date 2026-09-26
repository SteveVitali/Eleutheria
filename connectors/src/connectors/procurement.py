# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `procurement` connector — cooperative vehicles, USAspending, agenda platforms (§23.6, P07.3).

A source adapter on the P04.1 eight-stage framework (:mod:`connectors.stages`) for
the procurement channel: it writes :class:`Contract` and :class:`FundingInstrument`
entities, ``acquisition_channel``, quantities, renewal terms, and dated lifecycle
transitions. Like ``records`` it is a **targeted-lookup** client against rate-limited
government APIs, never a crawler.

This module owns five things §23.6 / §11.11 / §11.12 assign to P07.3, none of which
the framework or the ontology (which defines the *shape* — P01.1) provides:

* **The ``Contract`` runtime shape** (:class:`Contract`): the §11.11 predicate
  surface, with ``acquisition_channel`` validated against the frozen
  ``AcquisitionChannel`` enum. ``acquisition_channel`` and
  ``parent_cooperative_contract`` are **required model elements, not conveniences**
  (SIG-ONTO-032): a ``cooperative_piggyback`` contract MUST set
  ``parent_cooperative_contract`` (the ridden master award), because an agency
  riding a Sourcewell/OMNIA/NASPO/BuyBoard/TIPS/HGACBuy/Equalis/GSA master award
  often files **no local RFP at all**, and a model assuming a local competition
  would wrongly conclude no procurement evidence exists.
* **The ``FundingInstrument`` runtime shape** (:class:`FundingInstrument`):
  funder ≠ recipient ≠ purchaser (§11.12, SIG-ONTO-033). A BID, HOA, foundation, or
  federal grant program can fund surveillance an agency operates — a pattern CCOPS
  ordinances (which regulate *agency acquisition*) miss. ``funder`` and ``recipient``
  are distinct, required, and validated to differ.
* **Federal sub-award tracing** (:func:`funding_instrument_from_subaward`,
  :func:`trace_subaward_to_deployment`): USAspending **sub-awards** — not only prime
  awards — name LPR purchases by sheriffs under Byrne JAG and UASI, identifying
  deployments that appear in **no local procurement record** (SIG-ONTO-033). Every
  USAspending target asserts it pulls sub-awards (:func:`assert_pulls_subawards`),
  and the ``federal_award_id`` is the traceable link to the local deployment.
* **The agenda-platform tenant registry** (:func:`agenda_tenants`,
  :func:`tenant_targets`, :func:`tenant_discovery_negatives`): agenda platforms are
  per-tenant APIs and no municipality→platform directory exists upstream, so SIG
  builds and publishes one (``data/agenda_tenants.toml``, §22.3). ``discover()``
  reads its targets from that registry, and a jurisdiction probed with **no**
  discoverable platform is retained as a ``NO_EVIDENCE_FOUND`` coverage record
  (SIG-METRIC-002a / SIG-TIME-011), never discarded.
* **The predicate allowlist as a hard schema gate** (SIG-INGEST-033): the connector
  may write only the Contract/FundingInstrument predicate surface; a device count, a
  deployment, or a records-request claim is refused at the ingest boundary.

The layered parsing of a captured contract document is **not** done here: P07.1 owns
the parser, and this connector only *calls* it — :func:`parsing.classification.classify`
records the verdict and routes the document to a layer; the engines run in P07.1. Rows
are append-only and carry full provenance; the connector emits **candidate**
identifiers for the parties and never resolves entities itself (SIG-INGEST-034).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import cache
from typing import Any

from db.absence import AbsenceState, coverage_kind_for, render_absence
from evidence.digest import multihash
from parsing.classification import (
    ArchiveClassification,
    ClassificationVerdict,
    FileFormat,
    classify,
    classify_archive,
)
from parsing.document import html_text, page_locator_for, pdf_text_pages, utf8_text
from parsing.locator import Locator

from ._data import load_table
from .stages import (
    CaptureRef,
    Connector,
    ContentDrift,
    FetchResult,
    RunContext,
    register,
)

# --- the versioned vocabulary (data, not code — §20, SIG-ENG-001) -------------


@cache
def vocab() -> dict[str, Any]:
    """The versioned `procurement` connector vocabulary (``data/procurement_vocab.toml``)."""
    return load_table("procurement_vocab")


def vocab_version() -> str:
    """The connector vocabulary version stamped onto every run (§20)."""
    return str(vocab()["vocab_version"])


def source_ids() -> Mapping[str, str]:
    """The registry source ids the connector runs against, by role key (§22.6)."""
    return dict(vocab()["sources"])


def acquisition_channels() -> frozenset[str]:
    """The Contract acquisition-channel vocabulary (§11.11, AcquisitionChannel)."""
    return frozenset(vocab()["acquisition_channels"])


def cooperative_channel() -> str:
    """The channel whose contracts MUST set parent_cooperative_contract (SIG-ONTO-032)."""
    return str(vocab()["cooperative_channel"])


def funding_instrument_types() -> frozenset[str]:
    """The FundingInstrument instrument-type vocabulary (§11.12, FundingInstrumentType)."""
    return frozenset(vocab()["funding_instrument_types"])


def procurement_states() -> frozenset[str]:
    """The procurement lifecycle-track states (§13.4, ProcurementState)."""
    return frozenset(vocab()["procurement_states"])


def cooperative_vehicles() -> frozenset[str]:
    """The cooperative purchasing vehicle source ids (§22.3, SIG-ONTO-032)."""
    return frozenset(vocab()["cooperative_vehicles"])


def agenda_platform_sources() -> frozenset[str]:
    """The agenda-platform registry source ids (§22.3)."""
    return frozenset(vocab()["agenda_platforms"])


def artifact_types() -> frozenset[str]:
    """The artifact_type genres this connector may stamp (§10.3.2, SIG-INGEST-047)."""
    return frozenset(vocab()["artifact_types"])


def usaspending_config() -> Mapping[str, Any]:
    """The USAspending sub-award endpoint/field facts (``[usaspending]`` in the vocab)."""
    return vocab()["usaspending"]


def sam_gov_config() -> Mapping[str, Any]:
    """The SAM.gov opportunity-search facts (``[sam_gov]`` in the vocab, P26.2)."""
    return vocab()["sam_gov"]


# --- the predicate allowlist (SIG-INGEST-033) ---------------------------------


class PredicateNotAllowed(Exception):
    """A schema error: the connector tried to write outside its predicate allowlist."""


def predicate_allowlist() -> frozenset[str]:
    """The predicates this connector may write (§23.6, §11.11/§11.12, SIG-INGEST-033)."""
    return frozenset(vocab()["predicate_allowlist"])


def is_predicate_allowed(predicate: str) -> bool:
    """Whether ``predicate`` is in the connector's allowlist (SIG-INGEST-033)."""
    return predicate in predicate_allowlist()


def forbidden_predicate_genres() -> tuple[str, ...]:
    """The write-set §23.6 places out of scope for this connector (documented complement)."""
    return tuple(vocab()["forbidden_predicate_genres"])


def assert_predicate_allowed(predicate: str) -> str:
    """Return ``predicate`` if allowed, else raise :class:`PredicateNotAllowed`.

    The procurement connector may write **only** the Contract (§11.11) and
    FundingInstrument (§11.12) predicate surfaces plus the dated lifecycle
    transition: a device count, a deployment, a records-request claim, or a
    parsed-document claim is refused here, at the ingestion boundary, rather than
    only at resolution (SIG-INGEST-033, the ``D6`` admissibility filter at ingest).
    """
    if not is_predicate_allowed(predicate):
        raise PredicateNotAllowed(
            f"the procurement connector may write only {sorted(predicate_allowlist())} "
            f"(§23.6/§11.11/§11.12, SIG-INGEST-033); {predicate!r} is outside the allowlist — "
            "device counts, deployments, records requests, and parsed-document claims are refused."
        )
    return predicate


# --- candidate identifiers for the parties (SIG-INGEST-034) -------------------


def org_candidate(raw_org: str, *, scheme: str = "procurement.org_name") -> dict[str, str]:
    """A **candidate** identifier for a procurement party — never a resolution.

    The connector emits ``(scheme, value)`` and the identity layer (§14.6) resolves
    it (SIG-INGEST-034). A numeric id (e.g. a SAM UEI/DUNS) routes to a scheme-scoped
    path; a free-text organization name routes to the surrogate
    ``procurement.org_name`` path that feeds P03.2's crosswalk.
    """
    value = raw_org.strip()
    return {"scheme": scheme, "value": value}


# --- the Contract runtime shape (§11.11) --------------------------------------


class InvalidContract(Exception):
    """Raised when a Contract violates the §11.11 vocabulary contract or SIG-ONTO-032."""


@dataclass(frozen=True)
class LifecycleTransition:
    """A dated procurement lifecycle transition (§13.4): a (state, date) pair."""

    state: str
    date: str | None = None

    def __post_init__(self) -> None:
        if self.state not in procurement_states():
            raise InvalidContract(
                f"lifecycle state {self.state!r} is not in the ProcurementState vocabulary "
                f"{sorted(procurement_states())} (§13.4)"
            )


@dataclass(frozen=True)
class Contract:
    """The runtime shape of a §11.11 ``Contract``.

    Carries the §11.11 predicate surface. ``acquisition_channel`` is validated
    against the frozen ``AcquisitionChannel`` vocabulary; an out-of-vocabulary value
    is a hard error rather than a silent coercion. **SIG-ONTO-032**: a
    ``cooperative_piggyback`` contract MUST set ``parent_cooperative_contract`` (the
    master award being ridden) — the invariant is enforced in :meth:`__post_init__`,
    not left to the caller, because a missing local RFP must NOT be read as "no
    procurement evidence". The connector emits **candidate** party identifiers, never
    resolutions (SIG-INGEST-034).
    """

    external_id: str
    source_id: str
    buyer: str | None = None
    seller: str | None = None
    amount: str | None = None
    currency: str | None = None
    signed_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    renewal_options: str | None = None
    products: tuple[str, ...] = ()
    quantities: tuple[int, ...] = ()
    document: str | None = None
    acquisition_channel: str | None = None
    parent_cooperative_contract: str | None = None
    amends_contract: str | None = None
    lifecycle: tuple[LifecycleTransition, ...] = ()
    raw: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.external_id).strip():
            raise InvalidContract("a Contract requires an external_id (§11.11)")
        if (
            self.acquisition_channel is not None
            and self.acquisition_channel not in acquisition_channels()
        ):
            raise InvalidContract(
                f"acquisition_channel {self.acquisition_channel!r} is not in the "
                f"AcquisitionChannel vocabulary {sorted(acquisition_channels())} (§11.11)"
            )
        if (
            self.acquisition_channel == cooperative_channel()
            and not self.parent_cooperative_contract
        ):
            raise InvalidContract(
                "a cooperative_piggyback contract MUST set parent_cooperative_contract — the "
                "ridden master award (§11.11, SIG-ONTO-032); a missing local RFP is NOT evidence "
                "that no procurement exists."
            )

    @property
    def subject_id(self) -> str:
        """The claim subject id for this contract (source + external id scoped)."""
        return f"contract:{self.source_id}:{self.external_id}"

    @property
    def is_cooperative_piggyback(self) -> bool:
        """Whether this is a cooperative piggyback riding a master award (SIG-ONTO-032)."""
        return self.acquisition_channel == cooperative_channel()

    def predicate_values(self) -> dict[str, Any]:
        """The §11.11 predicate → value map for the set predicates (allowlisted keys only)."""
        candidates: dict[str, Any] = {
            "buyer": self.buyer,
            "seller": self.seller,
            "amount": self.amount,
            "currency": self.currency,
            "signed_date": self.signed_date,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "renewal_options": self.renewal_options,
            "document": self.document,
            "acquisition_channel": self.acquisition_channel,
            "parent_cooperative_contract": self.parent_cooperative_contract,
            "amends_contract": self.amends_contract,
            "external_id": self.external_id,
        }
        values = {k: v for k, v in candidates.items() if v is not None}
        if self.products:
            values["products"] = list(self.products)
        if self.quantities:
            values["quantities"] = list(self.quantities)
        return values

    def claim_rows(self) -> list[dict[str, Any]]:
        """The append-only claim rows for this contract, confined to the allowlist (P2).

        One ``contract`` entity row (carrying the whole predicate surface for
        provenance) plus one row per set §11.11 predicate and one per dated lifecycle
        transition. Every predicate id passes :func:`assert_predicate_allowed`
        (SIG-INGEST-033); ``raw_value`` is preserved beside every typed value (P2).
        Party predicates carry a **candidate** identifier, never a resolution
        (SIG-INGEST-034).
        """
        rows: list[dict[str, Any]] = [
            _stamp(
                {
                    "record_kind": "contract",
                    "subject_id": self.subject_id,
                    "predicate_id": assert_predicate_allowed("contract"),
                    "external_id": self.external_id,
                    "raw_value": self.external_id,
                    "predicate_surface": self.predicate_values(),
                    "acquisition_channel": self.acquisition_channel,
                    "parent_cooperative_contract": self.parent_cooperative_contract,
                },
                source_id=self.source_id,
            )
        ]
        party_predicates = ("buyer", "seller", "parent_cooperative_contract", "amends_contract")
        for predicate, value in self.predicate_values().items():
            row: dict[str, Any] = {
                "record_kind": "claim",
                "subject_id": self.subject_id,
                "predicate_id": assert_predicate_allowed(predicate),
                "raw_value": _raw_value_of(value),
                "value": value,
            }
            if predicate in party_predicates and isinstance(value, str):
                # SIG-INGEST-034: emit a candidate identifier, never resolve.
                row["candidate_identifier"] = org_candidate(value)
            rows.append(_stamp(row, source_id=self.source_id))
        for transition in self.lifecycle:
            rows.append(
                _stamp(
                    {
                        "record_kind": "claim",
                        "subject_id": self.subject_id,
                        "predicate_id": assert_predicate_allowed("lifecycle_transition"),
                        "raw_value": transition.state,
                        "value": {"state": transition.state, "date": transition.date},
                    },
                    source_id=self.source_id,
                )
            )
        return rows


# --- the FundingInstrument runtime shape (§11.12) -----------------------------


class InvalidFundingInstrument(Exception):
    """Raised when a FundingInstrument violates the §11.12 vocabulary contract."""


@dataclass(frozen=True)
class FundingInstrument:
    """The runtime shape of a §11.12 ``FundingInstrument`` — funder ≠ recipient ≠ purchaser.

    Business improvement districts, HOAs, foundations, and federal grant programs
    routinely buy surveillance for agencies to operate (SIG-ONTO-033); a model with
    no funder is blind to it. ``funder`` and ``recipient`` are distinct and required,
    and validated to differ — the whole point of the entity is that the party paying
    is not the party operating. ``instrument_type`` is validated against the frozen
    ``FundingInstrumentType`` vocabulary; ``federal_award_id`` is the USAspending
    award/sub-award id that is the traceable link (SIG-ONTO-033).
    """

    external_id: str
    source_id: str
    funder: str
    recipient: str
    instrument_type: str
    program_name: str | None = None
    amount: str | None = None
    award_date: str | None = None
    period: str | None = None
    conditions: str | None = None
    federal_award_id: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.external_id).strip():
            raise InvalidFundingInstrument("a FundingInstrument requires an external_id (§11.12)")
        if not str(self.funder).strip() or not str(self.recipient).strip():
            raise InvalidFundingInstrument(
                "a FundingInstrument requires both a funder and a recipient — funder ≠ recipient "
                "≠ purchaser is the reason the entity exists (§11.12, SIG-ONTO-033)"
            )
        if self.funder.strip() == self.recipient.strip():
            raise InvalidFundingInstrument(
                f"funder and recipient must differ (funder ≠ operator ≠ purchaser, §11.12); "
                f"both are {self.funder.strip()!r}"
            )
        if self.instrument_type not in funding_instrument_types():
            raise InvalidFundingInstrument(
                f"instrument_type {self.instrument_type!r} is not in the FundingInstrumentType "
                f"vocabulary {sorted(funding_instrument_types())} (§11.12)"
            )

    @property
    def subject_id(self) -> str:
        """The claim subject id for this funding instrument."""
        return f"funding_instrument:{self.source_id}:{self.external_id}"

    def predicate_values(self) -> dict[str, Any]:
        """The §11.12 predicate → value map for the set predicates (allowlisted keys only)."""
        candidates: dict[str, Any] = {
            "funder": self.funder,
            "recipient": self.recipient,
            "instrument_type": self.instrument_type,
            "program_name": self.program_name,
            "amount": self.amount,
            "award_date": self.award_date,
            "period": self.period,
            "conditions": self.conditions,
            "federal_award_id": self.federal_award_id,
            "external_id": self.external_id,
        }
        return {k: v for k, v in candidates.items() if v is not None}

    def claim_rows(self) -> list[dict[str, Any]]:
        """The append-only claim rows for this instrument, confined to the allowlist (P2)."""
        rows: list[dict[str, Any]] = [
            _stamp(
                {
                    "record_kind": "funding_instrument",
                    "subject_id": self.subject_id,
                    "predicate_id": assert_predicate_allowed("funding_instrument"),
                    "external_id": self.external_id,
                    "raw_value": self.external_id,
                    "predicate_surface": self.predicate_values(),
                    "federal_award_id": self.federal_award_id,
                },
                source_id=self.source_id,
            )
        ]
        for predicate, value in self.predicate_values().items():
            row: dict[str, Any] = {
                "record_kind": "claim",
                "subject_id": self.subject_id,
                "predicate_id": assert_predicate_allowed(predicate),
                "raw_value": _raw_value_of(value),
                "value": value,
            }
            if predicate in ("funder", "recipient") and isinstance(value, str):
                # SIG-INGEST-034: candidate identifiers, never a resolution.
                row["candidate_identifier"] = org_candidate(value)
            rows.append(_stamp(row, source_id=self.source_id))
        return rows


# --- federal sub-award tracing (§23.6, SIG-ONTO-033) --------------------------


@dataclass(frozen=True)
class SubAward:
    """A USAspending **sub-award** — not a prime award (§23.6, SIG-ONTO-033).

    Sub-awards name the LOCAL purchase a federal grant funded (Byrne JAG, UASI): the
    prime awardee is the funder (the federal program/agency), the sub-awardee is the
    recipient (the local agency), and ``prime_award_id`` is the ``federal_award_id``
    that is the traceable link. Pulling only prime awards would miss exactly the
    deployments that appear in no local procurement record.
    """

    subaward_id: str
    prime_award_id: str
    funder: str
    recipient: str
    program_name: str | None = None
    amount: str | None = None
    award_date: str | None = None
    description: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict)


def funding_instrument_from_subaward(subaward: SubAward, *, source_id: str) -> FundingInstrument:
    """Build the §11.12 FundingInstrument a USAspending sub-award traces to (SIG-ONTO-033).

    The federal program/agency is the ``funder``, the local agency is the
    ``recipient`` (funder ≠ recipient), and ``federal_award_id`` carries the prime
    award id so the grant → local-surveillance link is queryable. ``instrument_type``
    is ``federal_grant`` — the sub-award is a slice of a federal grant.
    """
    return FundingInstrument(
        external_id=subaward.subaward_id,
        source_id=source_id,
        funder=subaward.funder,
        recipient=subaward.recipient,
        instrument_type="federal_grant",
        program_name=subaward.program_name,
        amount=subaward.amount,
        award_date=subaward.award_date,
        conditions=subaward.description,
        federal_award_id=subaward.prime_award_id,
        raw=dict(subaward.raw),
    )


def trace_subaward_to_deployment(
    instrument: FundingInstrument, *, deployment_id: str
) -> dict[str, Any]:
    """Link a sub-award-derived FundingInstrument to a local deployment (SIG-ONTO-033).

    The trace is a ``federal_award_id`` → deployment edge: it records that the
    federal grant identified by ``instrument.federal_award_id`` funded the deployment
    ``deployment_id``, the path that identifies deployments appearing in no local
    procurement record. It is a **candidate** link (the identity layer resolves the
    deployment, SIG-INGEST-034); ``federal_award_id`` is required for the trace.
    """
    if not instrument.federal_award_id:
        raise InvalidFundingInstrument(
            "a federal sub-award trace requires a federal_award_id (§11.12, SIG-ONTO-033)"
        )
    return _stamp(
        {
            "record_kind": "claim",
            "subject_id": instrument.subject_id,
            "predicate_id": assert_predicate_allowed("federal_award_id"),
            "raw_value": instrument.federal_award_id,
            "value": instrument.federal_award_id,
            "traces_to_deployment": {"scheme": "deployment", "value": deployment_id},
            "funder": instrument.funder,
            "recipient": instrument.recipient,
        },
        source_id=instrument.source_id,
    )


def assert_pulls_subawards(target: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return ``target`` if it pulls USAspending sub-awards, else raise (SIG-ONTO-033).

    Sub-awards MUST be pulled, not only prime awards (§23.6). A USAspending target
    that does not set ``subaward`` truthy would fetch only prime awards and miss the
    federal-grant → local-surveillance link, so it is refused.
    """
    if not target.get("subaward"):
        raise ValueError(
            "a USAspending target MUST pull sub-awards (subaward=true), not only prime awards "
            "(§23.6, SIG-ONTO-033); prime-only would miss the federal-grant → local link."
        )
    return target


# --- the agenda-platform tenant registry (§22.3, this ticket OWNS it) ---------


@cache
def agenda_registry() -> Mapping[str, Any]:
    """The published agenda-platform tenant registry (``data/agenda_tenants.toml``)."""
    return load_table("agenda_tenants")


def agenda_tenants() -> dict[str, Mapping[str, Any]]:
    """The registered agenda-platform tenants, keyed by tenant id (§22.3).

    Each maps a jurisdiction to the platform serving it and the per-tenant API key —
    the municipality→platform directory upstream does not publish, which SIG builds
    and publishes here so the connector has targets (§22.3 SIG-INGEST-026).
    """
    return dict(agenda_registry().get("tenants", {}))


def platform_endpoints() -> Mapping[str, Any]:
    """The per-platform index-endpoint facts (``[platform_endpoints.*]``, P26.2)."""
    return vocab().get("platform_endpoints", {})


# --- the agenda-content vocabulary (P26.6 / SOURCES.6) -------------------------


@cache
def content_vocab() -> Mapping[str, Any]:
    """The reviewed agenda-content term set (``data/agenda_content_vocab.toml``)."""
    return load_table("agenda_content_vocab")


def content_vocab_version() -> str:
    """The agenda-content vocabulary version stamped on emitted rows (§20)."""
    return str(content_vocab()["vocab_version"])


def content_terms() -> tuple[Mapping[str, Any], ...]:
    """The reviewed surveillance-relevance terms (id / kind / label / patterns)."""
    return tuple(content_vocab().get("terms", ()))


def content_forbidden_tokens() -> tuple[str, ...]:
    """Part VIII content tokens refused in an emitted literal or row field (§0.7/§43.2)."""
    return tuple(str(t).lower() for t in content_vocab()["forbidden_tokens"])


def content_person_naming_predicates() -> frozenset[str]:
    """Predicates naming a natural person — never emitted (§43.4)."""
    return frozenset(str(p) for p in content_vocab()["person_naming_predicates"])


@cache
def _compiled_terms() -> tuple[tuple[Mapping[str, Any], tuple[re.Pattern[str], ...]], ...]:
    """The term set with compiled case-insensitive patterns (deterministic order)."""
    return tuple(
        (
            term,
            tuple(re.compile(str(p), re.IGNORECASE) for p in term.get("patterns", ())),
        )
        for term in content_terms()
    )


def scan_agenda_content(text: str) -> list[dict[str, Any]]:
    """Match ``text`` against the reviewed agenda-content vocabulary (P26.6).

    Returns one entry per matched term — the FIRST occurrence's verbatim
    literal slice and its character range into ``text``, plus the total match
    count — sorted by first occurrence then term id (deterministic). The
    literal is always a slice of the captured text: ``raw_value`` is verbatim
    by construction, exactly the OKC document-path rule (the literal is
    verified against captured text, never normalized or inferred).
    """
    matches: list[dict[str, Any]] = []
    for term, patterns in _compiled_terms():
        first: re.Match[str] | None = None
        count = 0
        for pattern in patterns:
            for m in pattern.finditer(text):
                count += 1
                if first is None or m.start() < first.start():
                    first = m
        if first is not None:
            matches.append(
                {
                    "term_id": str(term["id"]),
                    "term_kind": str(term.get("kind") or ""),
                    "term_label": str(term.get("label") or term["id"]),
                    "literal": first.group(0),
                    "start": first.start(),
                    "end": first.end(),
                    "match_count": count,
                }
            )
    matches.sort(key=lambda m: (m["start"], m["term_id"]))
    return matches


def content_guard_token(text: str) -> str | None:
    """The first Part VIII forbidden token in ``text``, or ``None`` (§0.7/§43.2)."""
    lowered = str(text).lower()
    for token in content_forbidden_tokens():
        if token in lowered:
            return token
    return None


def tenant_targets(platform: str | None = None) -> list[dict[str, Any]]:
    """The targeted-lookup targets from the tenant registry (the connector reads these).

    One target per registered tenant (optionally filtered to a single ``platform``
    source id). The ``url`` is the tenant's **index endpoint** — ``api_base`` plus
    the platform's reviewed ``index_path``/``index_query``/``index_method`` from
    ``[platform_endpoints.*]`` (P26.2): the public meetings/matters listing the
    portal itself reads, bounded, never a crawl. The jurisdiction rides as a
    candidate identifier (SIG-INGEST-034).
    """
    out: list[dict[str, Any]] = []
    for tenant_id, row in agenda_tenants().items():
        if platform is not None and row.get("platform") != platform:
            continue
        platform_id = str(row.get("platform") or "")
        endpoint = platform_endpoints().get(platform_id, {})
        api_base = str(row.get("api_base") or "").rstrip("/")
        index_path = str(endpoint.get("index_path", ""))
        index_query = str(endpoint.get("index_query", "")).strip()
        url = f"{api_base}{index_path}" + (f"?{index_query}" if index_query else "")
        target: dict[str, Any] = {
            "id": tenant_id,
            "tenant_id": tenant_id,
            # The per-tenant slug the platform keys its host/path on (the
            # matter_link_template's {tenant} slot) — distinct from tenant_id,
            # which is the registry row key (jurisdiction-shaped).
            "tenant": row.get("tenant") or tenant_id,
            "platform": platform_id,
            "jurisdiction": row.get("jurisdiction"),
            "url": url,
            "api_base": api_base,
            "external_id": tenant_id,
            "kind": "agenda_index",
            # P26.3: each tenant host's own robots.txt decides, and the verdict
            # is recorded per host (claims / refused / unretrievable) rather
            # than the first refused tenant aborting the whole platform run.
            "record_refusals": True,
        }
        # P26.6 (SOURCES.6): the bounded document window rides the target row as
        # data — the per-tenant cap (most-relevant items) and the per-run
        # platform cap come from the reviewed [platform_endpoints.*] row, never
        # a code constant.
        for bound_key in ("doc_per_tenant", "doc_run_cap"):
            if endpoint.get(bound_key) is not None:
                target[bound_key] = int(endpoint[bound_key])
        if str(endpoint.get("index_method", "")).lower() == "post":
            # e.g. PrimeGov PublicPortal /search — the bounded POST body rides the
            # shared fetch seam exactly like a USAspending sub-award search does.
            target["post_body"] = dict(endpoint.get("index_body", {}))
        patterns = endpoint.get("contract_matter_patterns")
        if patterns:
            target["contract_matter_patterns"] = list(patterns)
        out.append(target)
    return out


def tenant_for_uri(uri: str) -> Mapping[str, Any] | None:
    """The tenant-registry row whose index URL ``uri`` fetches (P26.2).

    ``extract``/``normalize`` are pure functions of the capture — the tenant
    context (jurisdiction, contract-type patterns) is recovered by matching the
    capture's source URI back to the registry row whose generated URL it is.
    """
    for target in tenant_targets():
        if str(target["url"]) == uri:
            return target
    # A tenant's bare api_base (or a per-item detail URL under it) still maps.
    for target in tenant_targets():
        api_base = str(target["url"]).split("?", 1)[0].rstrip("/")
        if uri.rstrip("/") == api_base or uri.startswith(f"{api_base}/"):
            return target
    return None


def tenant_discovery_negatives() -> list[dict[str, Any]]:
    """Coverage records for jurisdictions probed with NO agenda platform (SIG-METRIC-002a).

    A discovery negative is **retained, not discarded** (§22.3): a jurisdiction that
    was probed and found to have no discoverable agenda-platform API is a positive
    coverage finding, stored as a ``NO_EVIDENCE_FOUND`` coverage record naming the
    platforms probed (SIG-TIME-011), so the negative space is queryable once P09.1's
    coverage surfaces land. Wired now so the negatives are never dropped.
    """
    rows: list[dict[str, Any]] = []
    for negative_id, row in agenda_registry().get("negatives", {}).items():
        probed = [str(p) for p in row.get("probed_platforms", [])]
        rendering = render_absence(AbsenceState.NO_EVIDENCE_FOUND, sources_searched=probed)
        rows.append(
            _stamp(
                {
                    "record_kind": "coverage_record",
                    "subject_id": f"jurisdiction:{row.get('jurisdiction', negative_id)}",
                    "predicate_id": assert_predicate_allowed("contract"),
                    "absence_kind": coverage_kind_for(AbsenceState.NO_EVIDENCE_FOUND),
                    "absence_state": AbsenceState.NO_EVIDENCE_FOUND.value,
                    "absence_label": rendering.label,
                    "absence_detail": rendering.detail,
                    "sources_searched": probed,
                    "denominator_published": False,
                    "raw_value": "agenda_platform_not_found",
                    "tenant_discovery_id": negative_id,
                },
                source_id="agenda_tenant_registry",
            )
        )
    return rows


def platform_census() -> list[Mapping[str, Any]]:
    """The enumerated-but-not-ingested platform tenant census (P26.5).

    ``[[platform_census]]`` rows record vendor-tenant hosts the P26.5 enumeration
    *found* but which are NOT live targets — a platform-wide robots ``Disallow: /``
    (Granicus, PrimeGov-class walls), a platform with no bounded API surface
    (NovusAGENDA's WebForms postback portal, CivicPlus Agenda Center, IQM2,
    BoardDocs), or an unreachable host. They are registry data, never targets:
    :func:`tenant_targets` reads only ``[tenants.*]``. The census keeps the
    enumeration honest — a host found and excluded is recorded with its
    ``outcome`` and ``enum_source``, not dropped (§3.1, SIG-METRIC-002a).
    """
    return list(agenda_registry().get("platform_census", []))


# --- cooperative-vehicle helpers (SIG-ONTO-032) -------------------------------


def is_cooperative_vehicle(source_id: str) -> bool:
    """Whether a registry source id is a cooperative purchasing vehicle (§22.3)."""
    return source_id in cooperative_vehicles()


# --- captured procurement documents as EvidenceArtifact rows (§10.2, §23.6) ---


def evidence_artifact_id(source_uri: str) -> str:
    """The stable EvidenceArtifact id for a captured procurement document at ``source_uri``."""
    return f"procurement:artifact:{multihash(source_uri.encode('utf-8'))}"


def assert_artifact_type(artifact_type: str) -> str:
    """Return ``artifact_type`` if this connector may stamp it, else raise (SIG-INGEST-047)."""
    if artifact_type not in artifact_types():
        raise ValueError(
            f"artifact_type {artifact_type!r} is not one the procurement connector stamps "
            f"{sorted(artifact_types())} (§10.3.2, SIG-INGEST-047)"
        )
    return artifact_type


@dataclass(frozen=True)
class EvidenceArtifactRow:
    """A captured procurement document as an EvidenceArtifact row (§10.2, SIG-INGEST-047).

    Carries the ``artifact_type`` genre (§10.3.2) — for procurement that is a
    ``contract``, ``grant_award``, ``state_auditor_survey``, ``warrant``, or
    ``procurement_aggregator_record`` — plus the P07.1 classification verdict (the
    parser is *called*, not run here — the layer engines are P07.1).
    """

    artifact_id: str
    source_id: str
    source_uri: str
    capture_digest: str
    media_type: str
    byte_size: int
    artifact_type: str
    classification: Mapping[str, Any]
    integrity: str = "captured"

    def to_row(self) -> dict[str, Any]:
        return _stamp(
            {
                "record_kind": "evidence_artifact",
                "subject_id": self.artifact_id,
                "predicate_id": assert_predicate_allowed("document"),
                "published_by": self.source_id,
                "source_uri": self.source_uri,
                "capture_digest": self.capture_digest,
                "media_type": self.media_type,
                "byte_size": self.byte_size,
                "artifact_type": assert_artifact_type(self.artifact_type),
                "integrity": self.integrity,
                "classification": dict(self.classification),
                "raw_value": self.source_uri,
            },
            source_id=self.source_id,
        )


def classify_procurement_document(
    filename: str, data: bytes
) -> ClassificationVerdict | ArchiveClassification:
    """Call the P07.1 parser to classify one captured procurement document (§23.6).

    A procurement document (a signed PDF contract, a mixed-format ZIP of award
    packets) is classified via :func:`parsing.classification.classify` /
    ``classify_archive`` — this connector records the verdict and the routed layer;
    it does NOT run the layer engine (P07.1 owns that, SIG-PARSE-001/002).
    """
    verdict = classify(filename, data)
    if verdict.file_format is FileFormat.ZIP:
        return classify_archive(filename, data)
    return verdict


# --- the run record + per-capture quality report (§23.1) ----------------------


@dataclass(frozen=True)
class CaptureQualityReport:
    """The quality report produced **per capture** (§23.6 AC / phase-gate DQ)."""

    source_id: str
    capture_digest: str
    media_type: str
    byte_size: int
    capture_kind: str  # "contract" | "funding_instrument" | "procurement_document"
    connector_name: str
    connector_version: str
    vocab_version: str
    contract_count: int = 0
    funding_instrument_count: int = 0
    document_count: int = 0
    claim_count: int = 0
    classification: Mapping[str, Any] | None = None

    def to_row(self) -> dict[str, Any]:
        return {
            "record_kind": "quality_report",
            "source_id": self.source_id,
            "capture_digest": self.capture_digest,
            "media_type": self.media_type,
            "byte_size": self.byte_size,
            "capture_kind": self.capture_kind,
            "connector_name": self.connector_name,
            "connector_version": self.connector_version,
            "vocab_version": self.vocab_version,
            "contract_count": self.contract_count,
            "funding_instrument_count": self.funding_instrument_count,
            "document_count": self.document_count,
            "claim_count": self.claim_count,
            "classification": dict(self.classification) if self.classification else None,
        }


# --- the connector ------------------------------------------------------------


@register
class ProcurementConnector(Connector):
    """The `procurement` connector: cooperative vehicles, USAspending, agenda platforms (§23.6).

    Runs on the P04.1 eight-stage framework as a **targeted-lookup** client.
    ``discover`` returns supplied targets and — for an agenda-platform source —
    reads its tenants from the published tenant registry (§22.3); ``fetch`` egresses
    through the shared politeness layer, asserting that a USAspending target pulls
    sub-awards (SIG-ONTO-033); ``parse``/``extract``/``normalize`` are pure functions
    of the capture that build :class:`Contract` and :class:`FundingInstrument`
    entities (setting ``parent_cooperative_contract`` on cooperative piggybacks,
    SIG-ONTO-032), capture procurement documents as :class:`EvidenceArtifactRow`
    (calling the P07.1 parser to classify them), and emit a per-capture
    :class:`CaptureQualityReport`. Every claim is confined to the predicate allowlist
    (SIG-INGEST-033).
    """

    name = "procurement"
    version = "1.0.0"

    # -- acquisition --
    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        """Enumerate fetch targets — supplied targets plus agenda-registry tenants (§22.3).

        Targets come from ``ctx.parameters['targets']``; for an agenda-platform
        source the connector additionally reads its targets from the published
        tenant registry (:func:`tenant_targets`) — "the connector reads tenants from
        it" (§23.6 AC). A USAspending target is asserted to pull sub-awards.
        """
        targets: list[Mapping[str, Any]] = list(ctx.parameters.get("targets", []))
        if ctx.source.id in agenda_platform_sources():
            # The live path passes the registry-derived targets in already
            # (live_targets kind=agenda_tenants); dedupe on tenant_id so a tenant
            # is never fetched twice in one run.
            seen = {str(t.get("tenant_id")) for t in targets if t.get("tenant_id")}
            targets = [
                *targets,
                *(
                    t
                    for t in tenant_targets(platform=ctx.source.id)
                    if str(t.get("tenant_id")) not in seen
                ),
            ]
        if ctx.source.id == source_ids().get("usaspending"):
            for target in targets:
                assert_pulls_subawards(target)
        return targets

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """Obtain bytes for one target through the shared politeness layer only (SIG-INGEST-011)."""
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        if ctx.source.id == source_ids().get("usaspending"):
            assert_pulls_subawards(target)
        url = str(target["url"])
        headers: dict[str, str] = {}
        if ctx.source.id == source_ids().get("sam_gov"):
            # SAM.gov's public API requires an api_key credential — resolved
            # from the environment and carried on the reviewed X-Api-Key request
            # header (HG-09: the key is auth, never stored in a file, and never
            # appended to the request URL — a keyed query would land in the
            # capture's recorded source_uri and run records). Keyless, SAM.gov
            # answers 404 — a recorded disappearance, not something to defeat.
            import os

            key = os.environ.get(str(sam_gov_config()["api_key_env"]), "").strip()
            if key:
                headers[str(sam_gov_config()["api_key_header"])] = key
        post_body = target.get("post_body")
        if post_body is not None:
            # POST-targeted searches (USAspending sub-awards §23.6; PrimeGov's
            # PublicPortal /search index, P26.2) ride the shared seam like an
            # auth header — the body is reviewed target/vocab data, not content.
            headers["Content-Type"] = "application/json"
            return ctx.fetcher.fetch(
                url,
                headers=headers,
                body=json.dumps(post_body, sort_keys=True).encode("utf-8"),
            )
        return ctx.fetcher.fetch(url, headers=headers or None)

    def discover_more(
        self, ctx: RunContext, captures: Sequence[CaptureRef]
    ) -> list[Mapping[str, Any]]:
        """Bounded agenda/matter document targets resolved from captured indexes (P26.6).

        Each agenda-platform tenant **index** capture is the discovery surface
        for its linked matter/meeting documents: the connector reads the stored
        capture bytes (network-isolated, a pure function of the capture —
        SIG-INGEST-002), takes each item's document URL from the item's own
        link field (``doc_link_keys`` — e.g. PrimeGov's portal link) or the
        platform's reviewed ``doc_url_template`` (e.g. InSite ``/matters/{id}``,
        CivicClerk ``/v1/Meetings/{agendaId}``, eScribe ``Meeting.aspx``), and
        returns at most ``doc_per_tenant`` most-relevant documents per tenant
        (vocab-/contract-matching items first, then index order = recency) and
        ``doc_run_cap`` documents per run — the reviewed window bounds that ride
        each tenant target row as data, so a sweep stays finite and idempotent.
        Resolved targets land on ``ctx.resolved_targets`` so the document's
        post-capture stages see the tenant + item provenance.
        """
        if ctx.source.id not in agenda_platform_sources():
            return []
        cfg = platform_endpoints().get(ctx.source.id, {})
        if not cfg.get("doc_url_template") and not cfg.get("doc_link_keys"):
            return []
        resolved: list[Mapping[str, Any]] = []
        run_cap: int | None = None
        for capture in captures:
            index_target = _agenda_index_target_for(ctx, capture.source_uri)
            if index_target is None:
                continue
            if run_cap is None:
                run_cap = _opt_int(index_target.get("doc_run_cap") or cfg.get("doc_run_cap"))
            per_tenant = _opt_int(index_target.get("doc_per_tenant") or cfg.get("doc_per_tenant"))
            if not per_tenant:
                continue
            try:
                payload = json.loads(ctx.captures.get(capture.digest))
            except Exception:
                continue  # a non-JSON index capture resolves no documents
            items = _agenda_index_items(payload, ctx.source.id)
            for item, tier in _select_document_items(items, index_target, cfg, per_tenant):
                url = _document_url(item, index_target, cfg)
                if not url or url in ctx.resolved_targets:
                    continue
                target: dict[str, Any] = {
                    "id": f"{index_target.get('tenant_id')}:doc:{_agenda_item_id(item)}",
                    "url": url,
                    "kind": "agenda_document",
                    "platform": ctx.source.id,
                    "tenant_id": index_target.get("tenant_id"),
                    "tenant": index_target.get("tenant"),
                    "jurisdiction": index_target.get("jurisdiction"),
                    "index_url": str(capture.source_uri),
                    "item": dict(item),
                    "item_id": _agenda_item_id(item),
                    "selection_tier": tier,
                    "doc_per_tenant": per_tenant,
                    "doc_run_cap": run_cap,
                }
                ctx.resolved_targets[url] = target
                resolved.append(target)
                if run_cap is not None and len(resolved) >= run_cap:
                    return resolved
        return resolved

    # -- interpretation (pure functions of the capture) --
    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Structure the captured bytes — a procurement JSON payload, or a document.

        A JSON capture is the contract/sub-award payload; anything else is a captured
        procurement document, classified via the P07.1 parser (never parsed deeply
        here — P07.1 owns the engines). A resolved ``agenda_document`` continuation
        target (P26.6) parses as the platform's document genre — fail-closed.
        """
        data = ctx.captures.get(capture.digest)
        doc_target = _agenda_doc_target(ctx, capture.source_uri)
        if doc_target is not None:
            return self._parse_agenda_document(ctx, capture, data, doc_target)
        if _is_json_media(capture.media_type):
            return {"kind": "procurement_payload", "payload": json.loads(data), "capture": capture}
        filename = _filename_from_uri(capture.source_uri)
        verdict = classify_procurement_document(filename, data)
        return {
            "kind": "procurement_document",
            "capture": capture,
            "verdict": verdict.to_row(),
            "byte_size": len(data),
        }

    def _parse_agenda_document(
        self,
        ctx: RunContext,
        capture: CaptureRef,
        data: bytes,
        target: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Structure a captured agenda/minutes/matter document by genre (P26.6).

        Genre is re-derived from the captured bytes, never trusted from the
        target label: a JSON-genre endpoint answering a non-JSON body, an
        InSite-style error envelope, or an object missing every reviewed
        ``doc_required_fields`` key is :class:`ContentDrift` — fail closed,
        recorded per-document by the driver. An empty document (no text layer,
        an empty agenda shell) is an honest ``empty`` outcome, never drift.
        """
        platform = str(target.get("platform") or ctx.source.id)
        cfg = platform_endpoints().get(platform, {})
        genre = str(cfg.get("doc_genre") or "any")
        source_uri = str(capture.source_uri)
        media = str(capture.media_type or "").lower()

        def _doc(kind: str, method: str, text: str, pages: list[str] | None) -> dict[str, Any]:
            return {
                "kind": "agenda_document",
                "capture": capture,
                "target": dict(target),
                "doc_genre": kind,
                "extraction_method": method,
                "text": text,
                "pages": pages,
                "byte_size": len(data),
            }

        # A captured agenda PDF is in-genre for every platform (agendas publish
        # as PDF too); the pdf_text engine is fail-closed (no text → ()).
        if data.lstrip().startswith(b"%PDF"):
            pages = pdf_text_pages(data)
            return _doc("pdf", "pdf_text", "\n\n".join(pages), list(pages))

        if genre == "json":
            try:
                payload = json.loads(data)
            except (ValueError, UnicodeDecodeError) as exc:
                raise ContentDrift(
                    ctx.source.id,
                    f"agenda document {source_uri} is not parseable JSON "
                    f"(the {platform} document endpoint's expected genre)",
                    details=str(exc)[:200],
                ) from exc
            if _is_tenant_error_envelope(payload):
                raise ContentDrift(
                    ctx.source.id,
                    f"agenda document {source_uri} answered an API error envelope, not a document",
                    details=str(payload.get("Message"))[:200],
                )
            if isinstance(payload, Mapping):
                required = [str(k) for k in cfg.get("doc_required_fields", ())]
                if required and not any(k in payload for k in required):
                    raise ContentDrift(
                        ctx.source.id,
                        f"agenda document {source_uri} JSON lacks every required "
                        f"{platform} field {required}",
                        details=f"keys: {sorted(payload)[:20]}",
                    )
            elif not isinstance(payload, Sequence) or isinstance(payload, (str, bytes)):
                raise ContentDrift(
                    ctx.source.id,
                    f"agenda document {source_uri} is neither a {platform} document "
                    "object nor a list",
                )
            # The decoded payload IS the document text — the literal scan runs
            # over verbatim captured text, byte-range locators into it.
            return _doc("json", "json_text", utf8_text(data), None)

        if genre == "html":
            if not (
                "html" in media or "text" in media or media in ("", "application/octet-stream")
            ):
                raise ContentDrift(
                    ctx.source.id,
                    f"agenda document {source_uri} is {capture.media_type!r}, "
                    f"not an HTML agenda page (the {platform} document genre)",
                )
            return _doc("html", "selector_template", html_text(data), None)

        # doc_genre "any" (e.g. a PrimeGov portal link): sniff the capture.
        try:
            json.loads(data)
            return _doc("json", "json_text", utf8_text(data), None)
        except (ValueError, UnicodeDecodeError):
            pass
        if "html" in media or "text" in media or media in ("", "application/octet-stream"):
            return _doc("html", "selector_template", html_text(data), None)
        raise ContentDrift(
            ctx.source.id,
            f"agenda document {source_uri} is {capture.media_type!r} — "
            "no reviewed genre (json/html/pdf) fits",
        )

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """Raw records with locators, preserving raw values (P2)."""
        if parsed["kind"] == "agenda_document":
            capture = parsed["capture"]
            return [
                {
                    "record_kind": "agenda_document",
                    "source_uri": capture.source_uri,
                    "capture_digest": capture.digest,
                    "media_type": capture.media_type,
                    "retrieved_at": (
                        capture.retrieved_at.isoformat() if capture.retrieved_at else None
                    ),
                    "byte_size": parsed["byte_size"],
                    "doc_genre": parsed["doc_genre"],
                    "extraction_method": parsed["extraction_method"],
                    "text": parsed["text"],
                    "pages": parsed.get("pages"),
                    "target": parsed["target"],
                }
            ]
        if parsed["kind"] == "procurement_document":
            capture = parsed["capture"]
            return [
                {
                    "record_kind": "procurement_document",
                    "source_uri": capture.source_uri,
                    "capture_digest": capture.digest,
                    "media_type": capture.media_type,
                    "byte_size": parsed["byte_size"],
                    "verdict": parsed["verdict"],
                }
            ]
        payload = parsed["payload"]
        if ctx.source.id in agenda_platform_sources():
            # An agenda-platform tenant index (P26.2): one `agenda_item` raw
            # record per matter/event/meeting, carrying the tenant context
            # recovered from the registry so normalize() knows the jurisdiction
            # + reviewed contract-type patterns. An InSite error envelope (a
            # tenant whose client id is not provisioned — recorded, §3.1) is a
            # `tenant_api_error` record, never a silent empty result.
            tenant = tenant_for_uri(str(parsed["capture"].source_uri))
            if _is_tenant_error_envelope(payload):
                raw_payload = (
                    dict(payload) if isinstance(payload, Mapping) else {"payload": payload}
                )
                return [
                    {
                        "record_kind": "tenant_api_error",
                        "raw": raw_payload,
                        "tenant": dict(tenant) if tenant else None,
                    }
                ]
            objects = _agenda_index_items(payload, ctx.source.id)
            return [
                {
                    "record_kind": "agenda_item",
                    "raw": dict(o),
                    "tenant": dict(tenant) if tenant else None,
                }
                for o in objects
            ]
        if ctx.source.id == source_ids().get("sam_gov"):
            # SAM.gov opportunities search — `opportunitiesData` is the notice
            # list (P26.2); a notice is a dated procurement event, not a contract.
            objects = (
                list(payload.get("opportunitiesData", [])) if isinstance(payload, Mapping) else []
            )
            return [{"record_kind": "procurement_notice", "raw": dict(o)} for o in objects]
        if isinstance(payload, Mapping) and "results" in payload:
            objects = list(payload["results"])
        elif isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
            objects = list(payload)
        else:
            objects = [payload]
        out: list[Mapping[str, Any]] = []
        for obj in objects:
            kind = "subaward" if _looks_like_subaward(obj) else "contract"
            out.append({"record_kind": kind, "raw": dict(obj)})
        return out

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """Typed rows beside preserved raw values (P2), confined to the allowlist."""
        out: list[dict[str, Any]] = []
        for raw in raw_claims:
            kind = raw["record_kind"]
            if kind == "procurement_document":
                out.extend(self._normalize_document(ctx, raw))
            elif kind == "subaward":
                out.extend(self._normalize_subaward(ctx, raw))
            elif kind == "agenda_item":
                out.extend(self._normalize_agenda_item(ctx, raw))
            elif kind == "tenant_api_error":
                out.append(self._normalize_tenant_error(ctx, raw))
            elif kind == "procurement_notice":
                out.extend(self._normalize_notice(ctx, raw))
            elif kind == "agenda_document":
                out.extend(self._normalize_agenda_document(ctx, raw))
            else:
                out.extend(self._normalize_contract(ctx, raw))
        return out

    # -- normalization helpers --
    def _normalize_contract(self, ctx: RunContext, raw: Mapping[str, Any]) -> list[dict[str, Any]]:
        contract = self._build_contract(ctx, raw["raw"])
        rows: list[dict[str, Any]] = list(contract.claim_rows())
        claim_count = sum(1 for r in rows if r.get("record_kind") == "claim")
        rows.append(
            _stamp(
                CaptureQualityReport(
                    source_id=ctx.source.id,
                    capture_digest=_digest_of(raw["raw"]),
                    media_type="application/json",
                    byte_size=len(json.dumps(raw["raw"], sort_keys=True, default=str)),
                    capture_kind="contract",
                    connector_name=self.name,
                    connector_version=self.version,
                    vocab_version=vocab_version(),
                    contract_count=1,
                    claim_count=claim_count,
                ).to_row(),
                source_id=ctx.source.id,
            )
        )
        return rows

    def _normalize_subaward(self, ctx: RunContext, raw: Mapping[str, Any]) -> list[dict[str, Any]]:
        subaward = self._build_subaward(ctx, raw["raw"])
        instrument = funding_instrument_from_subaward(subaward, source_id=ctx.source.id)
        rows: list[dict[str, Any]] = list(instrument.claim_rows())
        deployment_id = _opt_str(raw["raw"].get("deployment_id"))
        if deployment_id:
            rows.append(trace_subaward_to_deployment(instrument, deployment_id=deployment_id))
        claim_count = sum(1 for r in rows if r.get("record_kind") == "claim")
        rows.append(
            _stamp(
                CaptureQualityReport(
                    source_id=ctx.source.id,
                    capture_digest=_digest_of(raw["raw"]),
                    media_type="application/json",
                    byte_size=len(json.dumps(raw["raw"], sort_keys=True, default=str)),
                    capture_kind="funding_instrument",
                    connector_name=self.name,
                    connector_version=self.version,
                    vocab_version=vocab_version(),
                    funding_instrument_count=1,
                    claim_count=claim_count,
                ).to_row(),
                source_id=ctx.source.id,
            )
        )
        return rows

    def _normalize_document(self, ctx: RunContext, raw: Mapping[str, Any]) -> list[dict[str, Any]]:
        artifact = EvidenceArtifactRow(
            artifact_id=evidence_artifact_id(str(raw["source_uri"])),
            source_id=ctx.source.id,
            source_uri=str(raw["source_uri"]),
            capture_digest=str(raw["capture_digest"]),
            media_type=str(raw["media_type"]),
            byte_size=int(raw["byte_size"]),
            artifact_type=_artifact_type_for_source(ctx.source.id),
            classification=dict(raw["verdict"]),
        )
        report = CaptureQualityReport(
            source_id=ctx.source.id,
            capture_digest=str(raw["capture_digest"]),
            media_type=str(raw["media_type"]),
            byte_size=int(raw["byte_size"]),
            capture_kind="procurement_document",
            connector_name=self.name,
            connector_version=self.version,
            vocab_version=vocab_version(),
            document_count=1,
            classification=dict(raw["verdict"]),
        )
        return [artifact.to_row(), _stamp(report.to_row(), source_id=ctx.source.id)]

    def _normalize_agenda_document(
        self, ctx: RunContext, raw: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        """A captured agenda/matter document → doc row + verbatim content claims (P26.6).

        The ``agenda_document`` row records the honest per-document outcome —
        ``matched`` / ``no_match`` / ``empty`` — with the capture digest, genre,
        extraction method, text length, matched term ids, and the reviewed
        window bounds it resolved under. Each matched term emits a
        ``content_term`` claim on the agenda item subject (and on the contract
        subject when the item is a reviewed contract-type matter): the typed
        ``value`` is the term id, ``raw_value`` is the VERBATIM literal slice of
        the captured text, and ``evidence.locator`` is the document locator —
        a byte range into the document text, or the PDF page. Nothing is
        asserted beyond the captured bytes (§3.1); a literal carrying a Part
        VIII forbidden token is suppressed and recorded on the document row,
        never emitted (§0.7/§43.2).
        """
        target = raw["target"]
        item = target.get("item") if isinstance(target.get("item"), Mapping) else {}
        platform = str(target.get("platform") or ctx.source.id)
        tenant_id = str(target.get("tenant_id") or "")
        jurisdiction = _opt_str(target.get("jurisdiction"))
        external_id = str(target.get("item_id") or _agenda_item_id(item))
        item_subject = f"agenda_item:{ctx.source.id}:{tenant_id or 'unscoped'}:{external_id}"
        doc_url = str(raw["source_uri"])
        doc_subject = f"agenda_document:{ctx.source.id}:{tenant_id or 'unscoped'}:{external_id}"
        text = str(raw.get("text") or "")
        pages = tuple(str(p) for p in (raw.get("pages") or ()))
        method = str(raw.get("extraction_method") or "")
        retrieved = _opt_str(raw.get("retrieved_at"))
        retrieved_date = retrieved[:10] if retrieved else None

        matches = scan_agenda_content(text) if text else []
        suppressions: list[dict[str, Any]] = []
        clean: list[Mapping[str, Any]] = []
        for m in matches:
            token = content_guard_token(str(m["literal"])) or content_guard_token(
                str(m["term_label"])
            )
            if token is not None:
                suppressions.append(
                    {"term_id": m["term_id"], "token": token, "literal": str(m["literal"])}
                )
            else:
                clean.append(m)
        outcome = "empty" if not text.strip() else ("matched" if clean else "no_match")

        doc_row = _stamp(
            {
                "record_kind": "agenda_document",
                "subject_id": doc_subject,
                "predicate_id": assert_predicate_allowed("document"),
                "external_id": external_id,
                "raw_value": doc_url,
                "platform": platform,
                "tenant_id": tenant_id or None,
                "jurisdiction": jurisdiction,
                "index_url": target.get("index_url"),
                "item_subject": item_subject,
                "capture_digest": raw.get("capture_digest"),
                "media_type": raw.get("media_type"),
                "byte_size": raw.get("byte_size"),
                "doc_genre": raw.get("doc_genre"),
                "extraction_method": method,
                "text_length": len(text),
                "matched_terms": [m["term_id"] for m in clean],
                "match_count": sum(int(m["match_count"]) for m in clean),
                "outcome": outcome,
                "selection_tier": target.get("selection_tier"),
                "doc_window": {
                    "per_tenant": target.get("doc_per_tenant"),
                    "run_cap": target.get("doc_run_cap"),
                },
                "content_vocab_version": content_vocab_version(),
            },
            source_id=ctx.source.id,
        )
        if jurisdiction:
            doc_row["jurisdiction_candidate"] = org_candidate(
                jurisdiction, scheme="agenda.jurisdiction_name"
            )
        if suppressions:
            doc_row["part_viii_suppressions"] = suppressions
        rows: list[dict[str, Any]] = [doc_row]

        # The document-locator claim: the item's document was captured at this
        # URL (the fetched document, distinct from the human-readable link the
        # index row already carries).
        rows.append(
            _stamp(
                {
                    "record_kind": "claim",
                    "subject_id": item_subject,
                    "predicate_id": assert_predicate_allowed("document"),
                    "value": doc_url,
                    "raw_value": doc_url,
                    "observed_at": retrieved_date,
                    "platform": platform,
                    "tenant_id": tenant_id or None,
                    "jurisdiction": jurisdiction,
                    "document_subject": doc_subject,
                    "evidence_genre": "agenda_document",
                    "evidence": {
                        "source_url": doc_url,
                        "retrieved_date": retrieved_date,
                        "extraction_method": method,
                        "locator": Locator.byte_range(0, len(text)).to_row(),
                        # No capture_digest inside the claim: the digest keys the
                        # claim's content_digest, and a byte-volatile page (a
                        # CSRF token churning between fetches) would mint a new
                        # claim per run — the capture↔document map lives on the
                        # agenda_document row + the fetch record instead (the
                        # OKC convention carries no capture id either).
                    },
                },
                source_id=ctx.source.id,
            )
        )

        # Contract-kind matters (the reviewed contract_matter_patterns) get the
        # same content_term claims on the contract subject too — the document's
        # verbatim literals then evidence the contract entity itself.
        type_name = _first_nonempty(
            item,
            ("MatterTypeName", "type_name", "category", "categoryName", "info", "MeetingType"),
        )
        patterns = [
            str(p).lower()
            for p in (
                target.get("contract_matter_patterns")
                or platform_endpoints().get(platform, {}).get("contract_matter_patterns", [])
            )
        ]
        contract_subject = (
            f"contract:{ctx.source.id}:{external_id}"
            if type_name and any(p in type_name.lower() for p in patterns)
            else None
        )
        for match in clean:
            locator: Mapping[str, Any] | None = (
                page_locator_for(pages, str(match["literal"]))
                if pages
                else Locator.byte_range(int(match["start"]), int(match["end"])).to_row()
            )
            if locator is None:
                # A literal that cannot be located is never emitted (OL-24-18,
                # SIG-PARSE-003) — impossible by construction, kept explicit.
                continue
            subjects = (item_subject, contract_subject) if contract_subject else (item_subject,)
            for subject in subjects:
                rows.append(
                    _stamp(
                        {
                            "record_kind": "claim",
                            "subject_id": subject,
                            "predicate_id": assert_predicate_allowed("content_term"),
                            "value": match["term_id"],
                            "raw_value": match["literal"],
                            "term_label": match["term_label"],
                            "term_kind": match["term_kind"],
                            "match_count": match["match_count"],
                            "observed_at": retrieved_date,
                            "platform": platform,
                            "tenant_id": tenant_id or None,
                            "jurisdiction": jurisdiction,
                            "document": doc_url,
                            "document_subject": doc_subject,
                            "evidence_genre": "agenda_document",
                            "evidence": {
                                "source_url": doc_url,
                                "retrieved_date": retrieved_date,
                                "extraction_method": method,
                                "locator": locator,
                            },
                        },
                        source_id=ctx.source.id,
                    )
                )
        return rows

    def _normalize_agenda_item(
        self, ctx: RunContext, raw: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        """One agenda-platform index record → an ``agenda_index`` row (+ maybe a Contract).

        Every matter/event/meeting is retained as an index row carrying its
        locators (item id, title, dates, document link) and the tenant's
        jurisdiction as a candidate identifier (SIG-INGEST-034). A Contract is
        emitted **only** when the item's type name matches the tenant's reviewed
        ``contract_matter_patterns`` (P26.2) — an ordinance or appointment is
        legislative business, never a contract (§3.1, no synthetic certainty).
        """
        item = raw["raw"]
        tenant = raw.get("tenant") or {}
        tenant_id = str(tenant.get("tenant_id") or "")
        platform = str(tenant.get("platform") or ctx.source.id)
        jurisdiction = _opt_str(tenant.get("jurisdiction"))
        external_id = _agenda_item_id(item)
        type_name = _first_nonempty(
            item,
            ("MatterTypeName", "type_name", "category", "categoryName", "info", "MeetingType"),
        )
        title = _first_nonempty(
            item,
            ("MatterTitle", "MatterName", "meetingTitle", "name", "title", "MeetingName"),
        )
        doc_link = self._agenda_item_link(item, tenant, platform)
        subject = f"agenda_item:{ctx.source.id}:{tenant_id or 'unscoped'}:{external_id}"
        index_row = _stamp(
            {
                "record_kind": "agenda_index",
                "subject_id": subject,
                "predicate_id": assert_predicate_allowed("agenda_item"),
                "external_id": external_id,
                "raw_value": title or external_id,
                "platform": platform,
                "tenant_id": tenant_id or None,
                "title": title,
                "type_name": type_name,
                "status": _first_nonempty(item, ("MatterStatusName", "status", "meetingStatus")),
                "introduced": _first_nonempty(
                    item,
                    ("MatterIntroDate", "startDateTime", "meetingDate", "StartDate"),
                ),
                "enactment_number": _first_nonempty(item, ("MatterEnactmentNumber",)),
                "document": doc_link,
                "jurisdiction": jurisdiction,
                "raw": dict(item),
            },
            source_id=ctx.source.id,
        )
        if jurisdiction:
            index_row["jurisdiction_candidate"] = org_candidate(
                jurisdiction, scheme="agenda.jurisdiction_name"
            )
        rows: list[dict[str, Any]] = [index_row]

        patterns = [
            str(p).lower()
            for p in (
                tenant.get("contract_matter_patterns")
                or platform_endpoints().get(platform, {}).get("contract_matter_patterns", [])
            )
        ]
        if type_name and any(p in type_name.lower() for p in patterns):
            contract = Contract(
                external_id=external_id,
                source_id=ctx.source.id,
                buyer=jurisdiction,
                document=doc_link,
                lifecycle=tuple(
                    LifecycleTransition(state=state, date=date)
                    for state, date in (
                        (
                            "proposed",
                            _first_nonempty(item, ("MatterIntroDate", "created_at")),
                        ),
                        (
                            "awarded",
                            _first_nonempty(item, ("MatterPassedDate", "MatterEnactmentDate")),
                        ),
                    )
                    if date
                ),
                raw=dict(item),
            )
            rows.extend(contract.claim_rows())
        return rows

    def _agenda_item_link(
        self, item: Mapping[str, Any], tenant: Mapping[str, Any], platform: str
    ) -> str | None:
        """The human-readable item link an agenda index row records (never fetched here)."""
        template = platform_endpoints().get(platform, {}).get("matter_link_template")
        matter_id = item.get("MatterId") or item.get("ID")
        if template and matter_id:
            return str(template).format(
                tenant=tenant.get("tenant") or tenant.get("tenant_id") or "",
                matter_id=matter_id,
                matter_guid=item.get("MatterGuid") or item.get("Guid") or "",
            )
        for key in ("url", "link", "document_url", "itemsSearchResultsDefaultLinkOnMeetingPortal"):
            if item.get(key):
                return str(item[key])
        return None

    def _normalize_tenant_error(self, ctx: RunContext, raw: Mapping[str, Any]) -> dict[str, Any]:
        """A tenant whose index answered an API error envelope — recorded, not silent (§3.1)."""
        tenant = raw.get("tenant") or {}
        tenant_id = tenant.get("tenant_id") or "unknown"
        envelope = raw["raw"] if isinstance(raw.get("raw"), Mapping) else {}
        return _stamp(
            {
                "record_kind": "tenant_api_error",
                "subject_id": f"agenda_tenant:{ctx.source.id}:{tenant_id}",
                "predicate_id": assert_predicate_allowed("agenda_item"),
                "raw_value": _opt_str(envelope.get("Message")) or "tenant index error envelope",
                "tenant_id": tenant.get("tenant_id"),
                "jurisdiction": tenant.get("jurisdiction"),
                "raw": dict(envelope),
            },
            source_id=ctx.source.id,
        )

    def _normalize_notice(self, ctx: RunContext, raw: Mapping[str, Any]) -> list[dict[str, Any]]:
        """A SAM.gov opportunity → a ``procurement_notice`` subject + its claims (P26.2).

        A notice is the dated evidence of a procurement lifecycle event — a
        solicitation, an award announcement — not a Contract (the award may never
        have executed). The reviewed ``[sam_gov.notice_map]`` maps the notice type
        to a lifecycle state; an unlisted type emits the index facts only, never
        a guessed transition (§3.1).
        """
        notice = raw["raw"]
        notice_id = (
            _first_nonempty(notice, ("noticeId", "notice_id", "id")) or _digest_of(notice)[:24]
        )
        notice_type = _first_nonempty(notice, ("type", "notice_type"))
        subject = f"procurement_notice:{ctx.source.id}:{notice_id}"
        agency = _opt_str(
            " / ".join(
                p
                for p in (
                    _opt_str(notice.get("fullParentPathName") or notice.get("department")),
                    _opt_str(notice.get("subTier") or notice.get("agency")),
                    _opt_str(notice.get("office")),
                )
                if p
            )
        )
        surface: dict[str, Any] = {
            "external_id": notice_id,
            "notice_type": notice_type,
            "posted_date": _opt_str(notice.get("postedDate")),
            "response_deadline": _opt_str(
                notice.get("responseDeadLine") or notice.get("response_deadline")
            ),
            "buyer": agency,
            "document": _opt_str(notice.get("uiLink") or notice.get("url")),
        }
        rows: list[dict[str, Any]] = [
            _stamp(
                {
                    "record_kind": "procurement_notice",
                    "subject_id": subject,
                    "predicate_id": assert_predicate_allowed("procurement_notice"),
                    "external_id": notice_id,
                    "raw_value": notice_id,
                    "predicate_surface": {k: v for k, v in surface.items() if v is not None},
                    "title": _opt_str(notice.get("title")),
                    "raw": dict(notice),
                },
                source_id=ctx.source.id,
            )
        ]
        for predicate, value in surface.items():
            if value is None:
                continue
            row: dict[str, Any] = {
                "record_kind": "claim",
                "subject_id": subject,
                "predicate_id": assert_predicate_allowed(predicate),
                "raw_value": _raw_value_of(value),
                "value": value,
            }
            if predicate == "buyer":
                row["candidate_identifier"] = org_candidate(str(value))
            rows.append(_stamp(row, source_id=ctx.source.id))
        mapping = sam_gov_config().get("notice_map", {}).get(str(notice_type or ""))
        if mapping:
            rows.append(
                _stamp(
                    {
                        "record_kind": "claim",
                        "subject_id": subject,
                        "predicate_id": assert_predicate_allowed("lifecycle_transition"),
                        "raw_value": str(mapping["state"]),
                        "value": {
                            "state": str(mapping["state"]),
                            "date": _opt_str(notice.get("postedDate")),
                        },
                    },
                    source_id=ctx.source.id,
                )
            )
            if mapping.get("channel"):
                rows.append(
                    _stamp(
                        {
                            "record_kind": "claim",
                            "subject_id": subject,
                            "predicate_id": assert_predicate_allowed("acquisition_channel"),
                            "raw_value": str(mapping["channel"]),
                            "value": str(mapping["channel"]),
                        },
                        source_id=ctx.source.id,
                    )
                )
        return rows

    def _build_contract(self, ctx: RunContext, raw: Mapping[str, Any]) -> Contract:
        """Map a raw contract object onto the §11.11 runtime shape.

        A contract sourced from a cooperative purchasing vehicle is a piggyback:
        ``acquisition_channel`` defaults to ``cooperative_piggyback`` and its
        ``parent_cooperative_contract`` (the ridden master award) MUST be present —
        SIG-ONTO-032. Otherwise the raw ``acquisition_channel`` is used verbatim.
        """
        channel = _opt_str(raw.get("acquisition_channel"))
        parent = _opt_str(raw.get("parent_cooperative_contract") or raw.get("master_contract"))
        if is_cooperative_vehicle(ctx.source.id):
            channel = channel or cooperative_channel()
        lifecycle = tuple(
            LifecycleTransition(state=str(t["state"]), date=_opt_str(t.get("date")))
            for t in raw.get("lifecycle", [])
            if t.get("state")
        )
        return Contract(
            external_id=str(
                raw.get("external_id") or raw.get("id") or raw.get("contract_id") or ""
            ),
            source_id=ctx.source.id,
            buyer=_opt_str(raw.get("buyer") or raw.get("agency")),
            seller=_opt_str(raw.get("seller") or raw.get("vendor")),
            amount=_opt_str(raw.get("amount") or raw.get("value")),
            currency=_opt_str(raw.get("currency")),
            signed_date=_opt_str(raw.get("signed_date")),
            start_date=_opt_str(raw.get("start_date")),
            end_date=_opt_str(raw.get("end_date")),
            renewal_options=_opt_str(raw.get("renewal_options")),
            products=tuple(str(p) for p in raw.get("products", []) if p),
            quantities=tuple(int(q) for q in raw.get("quantities", []) if q is not None),
            document=_opt_str(raw.get("document")),
            acquisition_channel=channel,
            parent_cooperative_contract=parent,
            amends_contract=_opt_str(raw.get("amends_contract")),
            lifecycle=lifecycle,
            raw=dict(raw),
        )

    def _build_subaward(self, ctx: RunContext, raw: Mapping[str, Any]) -> SubAward:
        """Map a raw USAspending sub-award object onto :class:`SubAward` (SIG-ONTO-033)."""
        cfg = usaspending_config()
        prime_id = str(
            raw.get("prime_award_id")
            or raw.get(str(cfg["federal_award_id_field"]))
            or raw.get("prime_award_generated_internal_id")
            or raw.get("prime_award_internal_id")
            or ""
        )
        return SubAward(
            subaward_id=str(
                raw.get("subaward_id")
                or raw.get(str(cfg["subaward_id_field"]))
                or raw.get("id")
                # The live API returns display labels for requested fields.
                or raw.get("Sub-Award ID")
                or ""
            ),
            prime_award_id=prime_id,
            funder=_opt_str(
                raw.get("funder")
                or raw.get("prime_awardee")
                or raw.get("awarding_agency")
                or raw.get("Awarding Agency")
            )
            or "",
            recipient=_opt_str(
                raw.get("recipient")
                or raw.get("subawardee")
                or raw.get("subrecipient_name")
                or raw.get("Sub-Awardee Name")
            )
            or "",
            program_name=_opt_str(raw.get("program_name") or raw.get("cfda_title")),
            amount=_opt_str(
                raw.get("amount") or raw.get("subaward_amount") or raw.get("Sub-Award Amount")
            ),
            award_date=_opt_str(
                raw.get("award_date") or raw.get("action_date") or raw.get("Sub-Award Date")
            ),
            description=_opt_str(
                raw.get("description")
                or raw.get("subaward_description")
                or raw.get("Sub-Award Description")
            ),
            raw=dict(raw),
        )

    # -- link + load --
    # link() is inherited (identity): SIG-INGEST-034 — the connector emits candidate
    # identifiers and NEVER resolves entities itself; resolution is P03.2/P05.1.

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Produce the L1 rows; the driver asserts them (live only, SIG-INGEST-003)."""
        return load_claims_for_l1(linked)


# --- module-private helpers ---------------------------------------------------


def _opt_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _agenda_index_items(payload: Any, platform: str) -> list[Mapping[str, Any]]:
    """The item objects an agenda-platform index payload carries (P26.2/P26.6).

    The item list lives under a platform-named envelope key — ``items_key`` on
    the reviewed ``[platform_endpoints.*]`` row (e.g. eScribe's ASP.NET
    webmethod answers ``{"d": [...]}``, P26.5); the generic ``value``/``results``
    keys cover the OData platforms; a bare list is the list itself. An InSite
    error envelope resolves to no items — it is an error, not an empty index.
    """
    if _is_tenant_error_envelope(payload):
        return []
    if isinstance(payload, Mapping):
        items_key = str(platform_endpoints().get(platform, {}).get("items_key", ""))
        if (
            items_key
            and isinstance(payload.get(items_key), Sequence)
            and not isinstance(payload.get(items_key), (str, bytes))
        ):
            objects = list(payload[items_key])
        else:
            objects = list(payload.get("value") or payload.get("results") or [])
    elif isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        objects = list(payload)
    else:
        objects = [payload]
    return [o if isinstance(o, Mapping) else {"value": o} for o in objects]


def _agenda_item_id(item: Mapping[str, Any]) -> str:
    """The item's external id — the same derivation the index row uses (P26.2/P26.6)."""
    return (
        _first_nonempty(
            item,
            (
                "MatterFile",
                "MatterId",
                "id",
                "ID",
                "meetingId",
                "meeting_id",
                "event_id",
                "systemItemId",
            ),
        )
        or _digest_of(item)[:24]
    )


def _agenda_index_target_for(ctx: RunContext, uri: str) -> Mapping[str, Any] | None:
    """The ``agenda_index`` target row a capture fetched (P26.6).

    Resolved continuation targets first, then the run's configured targets,
    then the tenant registry row whose generated index URL the capture's
    ``source_uri`` is exactly — the prefix fallback in :func:`tenant_for_uri`
    is deliberately NOT used here: a document URL under a tenant's api_base is
    not the index capture.
    """
    for candidate in ctx.resolved_targets.values():
        if str(candidate.get("url")) == uri and candidate.get("kind") == "agenda_index":
            return candidate
    for candidate in ctx.parameters.get("targets", []):
        if str(candidate.get("url")) == uri and candidate.get("kind") == "agenda_index":
            return candidate
    for target in tenant_targets(platform=ctx.source.id):
        if str(target["url"]) == uri:
            return target
    return None


def _agenda_doc_target(ctx: RunContext, uri: str) -> Mapping[str, Any] | None:
    """The ``agenda_document`` target a capture fetched (P26.6), or ``None``.

    Resolved continuation targets carry the tenant/item provenance; a
    configured seed target of kind ``agenda_document`` (a fixture run) is
    honoured the same way.
    """
    target = ctx.resolved_targets.get(uri)
    if target is None:
        for candidate in ctx.parameters.get("targets", []):
            if str(candidate.get("url")) == uri:
                target = candidate
                break
    if target is None or target.get("kind") != "agenda_document":
        return None
    return target


def _item_relevant(item: Mapping[str, Any], contract_patterns: Sequence[str]) -> bool:
    """Whether an index item is a priority document target (P26.6).

    Tier-0 relevance: the item's own text fields match the reviewed
    agenda-content vocabulary (a surveillance-relevant title/type) OR the
    item's type matches the reviewed contract-matter patterns (a contract-type
    matter is where surveillance procurement hides). Items with no signal are
    tier 1 — still fetched within the per-tenant cap, in index (recency) order,
    because a title that doesn't hint can still carry relevant document text.
    """
    text = " ".join(str(v) for v in item.values() if isinstance(v, str))
    if not text.strip():
        return False
    if scan_agenda_content(text):
        return True
    lowered = text.lower()
    return any(p in lowered for p in contract_patterns)


def _select_document_items(
    items: list[Mapping[str, Any]],
    index_target: Mapping[str, Any],
    cfg: Mapping[str, Any],
    per_tenant: int,
) -> list[tuple[Mapping[str, Any], int]]:
    """The bounded ``(item, tier)`` selection for one tenant index (P26.6).

    At most ``per_tenant`` items: tier-0 (vocab-/contract-matching) first, then
    tier-1 in **canonical order** — the reviewed ``doc_order_fields`` date (most
    recent first) with the item id as tie-break. The order comes from item DATA,
    never the server's return order: eScribe's ``GetCalendarMeetings`` returns
    the same meeting set in a different order per call, so position-in-payload
    would make the bounded window non-idempotent. Given the same item set the
    selection is identical — re-runs dedupe.
    """
    if per_tenant <= 0:
        return []
    patterns = [
        str(p).lower()
        for p in (
            index_target.get("contract_matter_patterns") or cfg.get("contract_matter_patterns", [])
        )
    ]
    order_fields = [
        str(f) for f in (index_target.get("doc_order_fields") or cfg.get("doc_order_fields") or ())
    ]

    def _date_key(item: Mapping[str, Any]) -> str:
        for order_field in order_fields:
            value = _opt_str(item.get(order_field))
            if value:
                return value
        return ""  # no reviewed date — sorts last under the descending order

    # Two stable sorts build the canonical order: id ascending, then date
    # descending (an empty date key is smallest, so undated items fall last).
    ordered = sorted(items, key=_agenda_item_id)
    ordered = sorted(ordered, key=_date_key, reverse=True)
    scored = [(_item_relevant(item, patterns), pos, item) for pos, item in enumerate(ordered)]
    scored.sort(key=lambda entry: (not entry[0], entry[1]))
    return [(item, 0 if relevant else 1) for relevant, _, item in scored[:per_tenant]]


def _document_url(
    item: Mapping[str, Any], index_target: Mapping[str, Any], cfg: Mapping[str, Any]
) -> str | None:
    """The document URL for one index item — the item's own link field first (P26.6).

    ``doc_link_keys`` names item fields that carry the document URL directly
    (the payload names its own documents — nothing is constructed); the
    reviewed ``doc_url_template`` + ``doc_id_keys`` is the fallback. A missing
    or placeholder id (``0``/empty) resolves no document — never a guessed URL.
    """
    for key in cfg.get("doc_link_keys", ()):
        value = _opt_str(item.get(str(key)))
        if value and value.startswith(("http://", "https://")):
            return value
    template = cfg.get("doc_url_template")
    if template:
        for key in cfg.get("doc_id_keys", ()):
            value = _opt_str(item.get(str(key)))
            if value is None or value == "0":
                continue
            return str(template).format(
                api_base=str(index_target.get("api_base") or "").rstrip("/"),
                tenant=str(index_target.get("tenant") or index_target.get("tenant_id") or ""),
                item_id=value,
            )
    return None


def _stamp(row: dict[str, Any], *, source_id: str) -> dict[str, Any]:
    """Stamp a row with its source id and the connector vocabulary version (§20)."""
    row.setdefault("source_id", source_id)
    row.setdefault("vocab_version", vocab_version())
    return row


def load_claims_for_l1(claims: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Add the generated ``claim_id`` + transaction time each L1 claim/entity row needs.

    Mirrors the framework's load contract: ``claim_id`` and ``sys_period`` are the
    two non-deterministic columns the reproducibility fingerprint excludes
    (SIG-INGEST-003). Only the claim/entity rows get an identity + transaction time;
    coverage records, evidence artifacts, and quality reports keep their own keys.
    """
    stamped_kinds = {"contract", "funding_instrument", "procurement_notice", "claim"}
    out: list[dict[str, Any]] = []
    for claim in claims:
        if claim.get("record_kind") in stamped_kinds:
            out.append(
                {
                    **claim,
                    "claim_id": str(_uuid4()),
                    "sys_period": f"[{datetime.now(UTC).isoformat()},)",
                }
            )
        else:
            out.append(dict(claim))
    return out


def _uuid4() -> Any:
    from uuid import uuid4

    return uuid4()


def _raw_value_of(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return ";".join(str(v) for v in value)
    return str(value)


def _is_tenant_error_envelope(payload: Any) -> bool:
    """Whether an agenda-platform payload is an InSite-style API error envelope.

    A tenant whose client id is not provisioned answers HTTP 200 with
    ``{"Message": ..., "ExceptionMessage"/"messageDetail": ...}`` — an error
    envelope, not an index page (observed 2026-09-16 on the shared
    webapi.legistar.com host). Recorded as a tenant_api_error row, never read as
    an empty index (§3.1).
    """
    return (
        isinstance(payload, Mapping)
        and "Message" in payload
        and ("ExceptionMessage" in payload or "messageDetail" in payload)
    )


def _first_nonempty(raw: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    """The first present non-empty string value among ``keys`` (alias-tolerant read)."""
    for key in keys:
        value = _opt_str(raw.get(key))
        if value is not None:
            return value
    return None


def _looks_like_subaward(obj: Mapping[str, Any]) -> bool:
    """Whether a raw object is a USAspending sub-award rather than a contract."""
    if not isinstance(obj, Mapping):
        return False
    keys = set(obj)
    subaward_markers = {
        "subaward_id",
        "prime_award_id",
        "prime_award_generated_internal_id",
        "subawardee",
        "subrecipient_name",
        "subaward_amount",
    }
    return bool(keys & subaward_markers) or str(obj.get("record_type", "")).startswith("sub")


def _artifact_type_for_source(source_id: str) -> str:
    """The artifact_type genre a captured document from ``source_id`` carries (§10.3.2)."""
    if source_id == source_ids().get("govspend"):
        return "procurement_aggregator_record"
    return "contract"


def _digest_of(payload: Any) -> str:
    return multihash(json.dumps(payload, sort_keys=True, default=str).encode("utf-8"))


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _is_json_media(media_type: str) -> bool:
    return "json" in media_type.lower()


def _filename_from_uri(uri: str) -> str:
    tail = uri.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
    return tail or "document"


__all__ = [
    "CaptureQualityReport",
    "Contract",
    "EvidenceArtifactRow",
    "FundingInstrument",
    "InvalidContract",
    "InvalidFundingInstrument",
    "LifecycleTransition",
    "PredicateNotAllowed",
    "ProcurementConnector",
    "SubAward",
    "acquisition_channels",
    "agenda_platform_sources",
    "agenda_tenants",
    "artifact_types",
    "assert_artifact_type",
    "assert_predicate_allowed",
    "assert_pulls_subawards",
    "classify_procurement_document",
    "cooperative_channel",
    "cooperative_vehicles",
    "evidence_artifact_id",
    "forbidden_predicate_genres",
    "funding_instrument_from_subaward",
    "funding_instrument_types",
    "is_cooperative_vehicle",
    "is_predicate_allowed",
    "load_claims_for_l1",
    "org_candidate",
    "platform_endpoints",
    "predicate_allowlist",
    "procurement_states",
    "sam_gov_config",
    "source_ids",
    "tenant_discovery_negatives",
    "tenant_for_uri",
    "tenant_targets",
    "trace_subaward_to_deployment",
    "usaspending_config",
    "vocab",
    "vocab_version",
]
