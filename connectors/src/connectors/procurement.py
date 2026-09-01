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

from ._data import load_table
from .stages import CaptureRef, Connector, FetchResult, RunContext, register

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


def tenant_targets(platform: str | None = None) -> list[dict[str, Any]]:
    """The targeted-lookup targets from the tenant registry (the connector reads these).

    One target per registered tenant (optionally filtered to a single ``platform``
    source id), carrying the per-tenant ``api_base`` URL and the jurisdiction as a
    candidate identifier (SIG-INGEST-034). This is "the connector reads tenants from
    the registry" (§23.6 AC).
    """
    out: list[dict[str, Any]] = []
    for tenant_id, row in agenda_tenants().items():
        if platform is not None and row.get("platform") != platform:
            continue
        out.append(
            {
                "tenant_id": tenant_id,
                "platform": row.get("platform"),
                "jurisdiction": row.get("jurisdiction"),
                "url": row.get("api_base"),
                "external_id": tenant_id,
            }
        )
    return out


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
            targets = [*targets, *tenant_targets(platform=ctx.source.id)]
        if ctx.source.id == source_ids().get("usaspending"):
            for target in targets:
                assert_pulls_subawards(target)
        return targets

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """Obtain bytes for one target through the shared politeness layer only (SIG-INGEST-011)."""
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        if ctx.source.id == source_ids().get("usaspending"):
            assert_pulls_subawards(target)
        return ctx.fetcher.fetch(str(target["url"]))

    # -- interpretation (pure functions of the capture) --
    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Structure the captured bytes — a procurement JSON payload, or a document.

        A JSON capture is the contract/sub-award payload; anything else is a captured
        procurement document, classified via the P07.1 parser (never parsed deeply
        here — P07.1 owns the engines).
        """
        data = ctx.captures.get(capture.digest)
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

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """Raw records with locators, preserving raw values (P2)."""
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
            or ""
        )
        return SubAward(
            subaward_id=str(
                raw.get("subaward_id")
                or raw.get(str(cfg["subaward_id_field"]))
                or raw.get("id")
                or ""
            ),
            prime_award_id=prime_id,
            funder=_opt_str(
                raw.get("funder") or raw.get("prime_awardee") or raw.get("awarding_agency")
            )
            or "",
            recipient=_opt_str(
                raw.get("recipient") or raw.get("subawardee") or raw.get("subrecipient_name")
            )
            or "",
            program_name=_opt_str(raw.get("program_name") or raw.get("cfda_title")),
            amount=_opt_str(raw.get("amount") or raw.get("subaward_amount")),
            award_date=_opt_str(raw.get("award_date") or raw.get("action_date")),
            description=_opt_str(raw.get("description") or raw.get("subaward_description")),
            raw=dict(raw),
        )

    # -- link + load --
    # link() is inherited (identity): SIG-INGEST-034 — the connector emits candidate
    # identifiers and NEVER resolves entities itself; resolution is P03.2/P05.1.

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Produce the L1 rows; the driver asserts them (live only, SIG-INGEST-003)."""
        return load_claims_for_l1(linked)


# --- module-private helpers ---------------------------------------------------


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
    stamped_kinds = {"contract", "funding_instrument", "claim"}
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
    "predicate_allowlist",
    "procurement_states",
    "source_ids",
    "tenant_discovery_negatives",
    "tenant_targets",
    "trace_subaward_to_deployment",
    "usaspending_config",
    "vocab",
    "vocab_version",
]
