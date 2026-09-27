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
from datetime import UTC, datetime, timedelta
from functools import cache
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlencode, urljoin

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


def usaspending_sweep_config() -> Mapping[str, Any]:
    """The bounded federal sweep plan (``[usaspending_sweep]`` in the vocab, P26.14)."""
    return vocab().get("usaspending_sweep", {})


def sam_gov_sweep_config() -> Mapping[str, Any]:
    """The widened SAM.gov keyword plan (``[sam_gov_sweep]`` in the vocab, P26.14)."""
    return vocab().get("sam_gov_sweep", {})


def ted_eu_sweep_config() -> Mapping[str, Any]:
    """The bounded EU tender sweep plan (``[ted_eu_sweep]`` in the vocab, P26.15)."""
    return vocab().get("ted_eu_sweep", {})


def ted_eu_keywords() -> tuple[Mapping[str, Any], ...]:
    """The reviewed TED surveillance-keyword slices (id / query / patterns)."""
    return tuple(ted_eu_sweep_config().get("keywords", ()))


def ted_eu_cpv_codes() -> tuple[Mapping[str, Any], ...]:
    """The verified TED CPV slices (8-digit ``code`` + ``label``, P26.15)."""
    return tuple(ted_eu_sweep_config().get("cpv_codes", ()))


def ted_eu_country_map() -> Mapping[str, str]:
    """The reviewed ISO 3166-1 alpha-3 → alpha-2 map for TED country fields.

    TED returns alpha-3 codes (``POL``); the jurisdiction claim carries the
    alpha-2 (``PL``) under the P26.9 ``iso.3166_1_alpha2`` scheme. An unmapped
    alpha-3 keeps its verbatim raw_value and emits no normalized identifier —
    a code is never fabricated.
    """
    return dict(ted_eu_sweep_config().get("country_map", {}))


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
        # P26.14: an explicitly declared prime-award slice of the reviewed
        # sweep plan is legal — the SIG-ONTO-033 requirement is that the sweep
        # PULLS sub-awards (the generated plan always includes sub slices),
        # not that every single target is a sub-award target.
        if not (
            str(target.get("kind")) == "usaspending_award_search"
            and str(target.get("award_kind")) == "prime"
        ):
            raise ValueError(
                "a USAspending target MUST pull sub-awards (subaward=true), not only prime awards "
                "(§23.6, SIG-ONTO-033); prime-only would miss the federal-grant → local link."
            )
    return target


# --- the bounded federal sweeps (P26.14 / FEDERAL.1) ---------------------------

#: Fragment tag carrying the slice id on generated sweep targets. The fragment
#: is never sent on the wire (RFC 7230) — it exists so the recorded source_uri
#: of each capture names the exact sweep slice (keyword/agency/page) that
#: produced it: the per-slice outcome is recoverable from the fetch record and
#: every claim carries its slice provenance. One POST target per slice, each
#: counted once — a refused request is recorded and NEVER re-probed.
_SLICE_TAG = "#sig-slice="


def usaspending_award_targets() -> list[dict[str, Any]]:
    """The bounded USAspending award-search targets from the reviewed sweep plan (P26.14).

    One POST target per (keyword × page) for sub-award and prime-award slices,
    plus one (agency × page) slice per reviewed awarding agency — the whole
    plan is data in ``[usaspending_sweep]`` (keywords, agencies, page bounds,
    field lists, award-type codes, the time window), never code constants.
    Every target's ``url`` carries ``#sig-slice=<id>`` so its capture's
    recorded source_uri names its slice; ``post_body`` is sent verbatim.
    """
    cfg = usaspending_sweep_config()
    bounds = dict(cfg.get("bounds", {}))
    base = str(usaspending_config()["api_base"]).rstrip("/") + str(
        usaspending_config()["prime_endpoint"]
    )
    keywords = [str(k) for k in cfg.get("keywords", ())]
    agencies = [str(a.get("name")) for a in cfg.get("agencies", ()) if a.get("name")]
    page_size = int(bounds.get("page_size", 100))
    time_period = [dict(t) for t in bounds.get("time_period", ())]
    sub_codes = [str(c) for c in bounds.get("sub_award_type_codes", ())]
    prime_codes = [str(c) for c in bounds.get("prime_award_type_codes", ())]
    sub_fields = [str(f) for f in bounds.get("sub_fields", ())]
    prime_fields = [str(f) for f in bounds.get("prime_fields", ())]
    sub_pages = int(bounds.get("sub_max_pages", 1))
    prime_pages = int(bounds.get("prime_max_pages", 1))
    agency_pages = int(bounds.get("agency_max_pages", 1))

    def _slice(
        tid: str,
        award_kind: str,
        post_body: dict[str, Any],
        extra: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "id": tid,
            "url": f"{base}{_SLICE_TAG}{tid}",
            "kind": "usaspending_award_search",
            "award_kind": award_kind,
            "subaward": award_kind == "sub",
            "post_body": post_body,
            **extra,
        }

    targets: list[dict[str, Any]] = []
    for kw in keywords:
        for page in range(1, sub_pages + 1):
            tid = f"sub_kw:{kw}:p{page}"
            targets.append(
                _slice(
                    tid,
                    "sub",
                    {
                        "subawards": True,
                        "filters": {
                            "time_period": time_period,
                            "award_type_codes": sub_codes,
                            "keywords": [kw],
                        },
                        "fields": sub_fields,
                        "limit": page_size,
                        "page": page,
                        "sort": "Sub-Award Amount",
                        "order": "desc",
                    },
                    {"index_keyword": kw, "slice": "subaward_keyword", "page": page},
                )
            )
        for page in range(1, prime_pages + 1):
            tid = f"prime_kw:{kw}:p{page}"
            targets.append(
                _slice(
                    tid,
                    "prime",
                    {
                        "subawards": False,
                        "filters": {
                            "time_period": time_period,
                            "award_type_codes": prime_codes,
                            "keywords": [kw],
                        },
                        "fields": prime_fields,
                        "limit": page_size,
                        "page": page,
                        "sort": "Award Amount",
                        "order": "desc",
                    },
                    {"index_keyword": kw, "slice": "prime_keyword", "page": page},
                )
            )
    for agency in agencies:
        for page in range(1, agency_pages + 1):
            tid = f"agency:{agency}:p{page}"
            targets.append(
                _slice(
                    tid,
                    "sub",
                    {
                        "subawards": True,
                        "filters": {
                            "time_period": time_period,
                            "award_type_codes": sub_codes,
                            "keywords": keywords,
                            "agencies": [{"type": "awarding", "tier": "toptier", "name": agency}],
                        },
                        "fields": sub_fields,
                        "limit": page_size,
                        "page": page,
                        "sort": "Sub-Award Amount",
                        "order": "desc",
                    },
                    {"agency": agency, "slice": "awarding_agency", "page": page},
                )
            )
    return targets


def sam_gov_search_targets() -> list[dict[str, Any]]:
    """The widened SAM.gov opportunity-search targets from the reviewed plan (P26.14).

    One bounded ``title`` query per reviewed keyword — the API's own search
    field, with ``limit`` + the posted window bounding every slice. The key is
    resolved at fetch time onto ``X-Api-Key`` and never touches the URL.
    """
    cfg = sam_gov_sweep_config()
    base = str(sam_gov_config()["api_base"]).rstrip("/") + str(sam_gov_config()["search_endpoint"])
    keywords = [str(k) for k in cfg.get("keywords", ())]
    limit = int(cfg.get("limit", 25))
    posted_from = str(cfg.get("posted_from", ""))
    posted_to = str(cfg.get("posted_to", ""))
    targets: list[dict[str, Any]] = []
    for kw in keywords:
        query = urlencode(
            {
                "limit": limit,
                "postedFrom": posted_from,
                "postedTo": posted_to,
                "title": kw,
            }
        )
        targets.append(
            {
                "id": f"samgov:kw:{kw}",
                "url": f"{base}?{query}",
                "kind": "opportunity_search",
                "index_keyword": kw,
            }
        )
    return targets


def _sam_gov_title_param(url: str) -> str | None:
    """The decoded ``title`` query param of a SAM.gov search URL (dedupe key)."""
    from urllib.parse import parse_qs, urlsplit

    try:
        values = parse_qs(urlsplit(str(url)).query).get("title")
    except Exception:
        return None
    return values[0].strip().lower() if values else None


def _usaspending_target_for(ctx: RunContext, uri: str) -> Mapping[str, Any] | None:
    """The sweep target whose URL (incl. ``#sig-slice``) produced capture ``uri``.

    Post-capture stages recover slice provenance (keyword/agency/page) from
    the recorded source_uri — the fragment is the bookkeeping annotation that
    survives into the capture, never the wire request.
    """
    resolved = ctx.resolved_targets.get(uri)
    if resolved is not None:
        return resolved
    for target in ctx.parameters.get("targets", ()):
        if str(target.get("url")) == uri:
            return target
    return None


# --- the bounded EU tender sweep (P26.15 / SOURCES.14) -------------------------


def ted_eu_search_targets(*, today: Any = None) -> list[dict[str, Any]]:
    """The bounded TED Search-API targets from the reviewed sweep plan (P26.15).

    One POST target per reviewed keyword slice and per verified CPV slice —
    ``[ted_eu_sweep]`` data, never a code constant. Each target's ``url``
    carries ``#sig-slice=<id>`` (the P26.14 provenance fragment — never sent
    on the wire) and its ``post_body`` is the verbatim
    ``PublicExpertSearchRequestV1`` request: an expert query bounding the
    slice (``FT~"<phrase>"`` or ``classification-cpv=<code>``, AND a rolling
    ``publication-date>=<window>`` bound), the reviewed field list, and the
    PAGE_NUMBER page. ITERATION/scroll mode is never used — the sweep is a
    bounded window of recent notices, each slice independently auditable.
    ``today`` is injectable for deterministic tests.
    """
    cfg = ted_eu_sweep_config()
    endpoint = str(cfg["endpoint"])
    page_size = int(cfg.get("page_size", 250))
    max_pages = int(cfg.get("max_pages_per_slice", 1))
    fields = [str(f) for f in cfg.get("fields", ())]
    window_days = int(cfg.get("search_window_days", 120))
    if today is None:
        today = datetime.now(UTC).date()
    since = (today - timedelta(days=window_days)).strftime("%Y%m%d")
    date_bound = f"publication-date>={since}"

    def _slice(
        tid: str,
        query: str,
        page: int,
        extra: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "id": tid,
            "url": f"{endpoint}{_SLICE_TAG}{tid}",
            "kind": "ted_eu_search",
            "record_kind": "ted_eu_slice",
            "slice": tid,
            "page": page,
            "limit": page_size,
            "query": query,
            "post_body": {
                "query": query,
                "fields": fields,
                "page": page,
                "limit": page_size,
                "scope": str(cfg.get("scope", "ALL")),
                "paginationMode": str(cfg.get("pagination_mode", "PAGE_NUMBER")),
                "onlyLatestVersions": bool(cfg.get("only_latest_versions", True)),
            },
            "plan_version": str(cfg.get("version", "")),
            **extra,
        }

    targets: list[dict[str, Any]] = []
    for kw in ted_eu_keywords():
        kid = str(kw["id"])
        for page in range(1, max_pages + 1):
            phrase = str(kw["query"]).replace('"', "'")
            query = f'FT~"{phrase}" AND {date_bound}'
            targets.append(
                _slice(
                    f"ted_kw:{kid}:p{page}",
                    query,
                    page,
                    {"query_kind": "keyword", "ted_keyword": kid, "keyword_label": kw["query"]},
                )
            )
    for cpv in ted_eu_cpv_codes():
        code = str(cpv["code"])
        for page in range(1, max_pages + 1):
            query = f"classification-cpv={code} AND {date_bound}"
            targets.append(
                _slice(
                    f"ted_cpv:{code}:p{page}",
                    query,
                    page,
                    {"query_kind": "cpv", "cpv_code": code, "cpv_label": cpv.get("label")},
                )
            )
    return targets


@cache
def _compiled_ted_terms() -> tuple[tuple[Mapping[str, Any], tuple[re.Pattern[str], ...]], ...]:
    """The TED keyword set with compiled case-insensitive patterns (deterministic)."""
    return tuple(
        (
            term,
            tuple(re.compile(str(p), re.IGNORECASE) for p in term.get("patterns", ())),
        )
        for term in ted_eu_keywords()
    )


def scan_ted_content(text: str) -> list[dict[str, Any]]:
    """Match ``text`` against the reviewed TED keyword patterns (P26.15).

    Same contract as :func:`scan_agenda_content`: one entry per matched term —
    the FIRST occurrence's verbatim literal slice and its character range into
    ``text``, plus the total match count — sorted by first occurrence then
    term id. ``raw_value`` is verbatim by construction: the literal is always
    a slice of the captured notice text, never the search query.
    """
    matches: list[dict[str, Any]] = []
    for term, patterns in _compiled_ted_terms():
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
                    "term_label": str(term.get("query") or term["id"]),
                    "literal": first.group(0),
                    "start": first.start(),
                    "end": first.end(),
                    "match_count": count,
                }
            )
    matches.sort(key=lambda m: (m["start"], m["term_id"]))
    return matches


def _ted_i18n_values(field: Any) -> list[tuple[str, str]]:
    """The (lang, text) pairs of a TED i18n field ({lang: text | [texts]}).

    A scalar (a non-i18n field or a pre-flattened value) comes back as one
    ``("", value)`` pair. Deterministic language order — ``eng`` first, then
    the notice's own languages in sorted order — so extraction is stable
    across runs and a notice supplying no English text still yields its own
    verbatim literal.
    """
    out: list[tuple[str, str]] = []
    if isinstance(field, Mapping):
        langs = sorted(field.keys(), key=lambda k: (k != "eng", str(k)))
        for lang in langs:
            value = field[lang]
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                out.extend((str(lang), str(v)) for v in value if v is not None)
            elif value is not None:
                out.append((str(lang), str(value)))
    elif isinstance(field, Sequence) and not isinstance(field, (str, bytes)):
        out.extend(("", str(v)) for v in field if v is not None)
    elif field is not None:
        out.append(("", str(field)))
    return out


def _ted_first_text(field: Any) -> str | None:
    """The first text of a TED i18n field (eng preferred, else first sorted lang)."""
    values = _ted_i18n_values(field)
    return values[0][1] if values else None


def _ted_first_seq(field: Any) -> str | None:
    """The first scalar of a TED array-valued field (e.g. ``buyer-country``)."""
    if isinstance(field, Sequence) and not isinstance(field, (str, bytes)):
        return str(field[0]) if field else None
    return str(field) if field is not None else None


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


# --- the procurement-portal tenant registry (P26.10 / SOURCES.9, §22.3-class) --


@cache
def portal_registry() -> Mapping[str, Any]:
    """The published procurement-portal tenant registry (``data/procurement_portal_tenants.toml``).

    Vendor procurement platforms are multi-tenant exactly like the agenda
    platforms: BidNet Direct hosts agency storefronts as paths under one host,
    Bonfire serves per-tenant ``*.bonfirehub.com`` portals, OpenGov Procurement
    serves ``/portal/<agency>`` tenants, and city open-data portals publish
    Socrata contract/award datasets. No municipality→portal directory exists
    upstream; this is it. Every row carries ``enum_source`` enumeration
    provenance, and ``[[platform_census]]`` rows preserve the enumerated hosts
    that are NOT ingest targets (robots walls, WAF challenges, unreachable
    names, vendor infrastructure) — a host found and excluded is recorded, not
    dropped (§3.1, SIG-METRIC-002a).
    """
    return load_table("procurement_portal_tenants")


def portal_tenants() -> dict[str, Mapping[str, Any]]:
    """The registered procurement-portal tenants, keyed by tenant id."""
    return dict(portal_registry().get("tenants", {}))


def procurement_portal_sources() -> frozenset[str]:
    """The registry source ids whose targets are portal tenants (vocab ``procurement_portals``)."""
    return frozenset(str(s) for s in vocab().get("procurement_portals", ()))


def portal_census() -> list[Mapping[str, Any]]:
    """The enumerated-but-not-ingested procurement-portal census rows (P26.10)."""
    return list(portal_registry().get("platform_census", []))


def portal_targets(source_id: str | None = None) -> list[dict[str, Any]]:
    """The bounded index targets the portal tenant registry expands to (P26.10).

    One set of targets per registered tenant (filtered to one ``source_id``
    when given — a live run of ``bidnet_direct`` expands only the BidNet rows,
    a ``procportal_*`` city source expands only its own dataset row). Every
    target is the platform's own bounded index surface:

    * **bidnet** — the tenant storefront's server-rendered solicitation
      indexes: the unfiltered open-bids page-1 plus each reviewed index kind
      under each reviewed recall keyword (the portal's own public
      ``?keywords=`` field — a targeted lookup, never a paginated crawl;
      ``?page=`` is robots-disallowed anyway, verbatim in the packet).
    * **socrata** — one bounded SoQL slice per dataset:
      ``/resource/<id>.json?$limit=N&$order=<date> DESC``, the documented rows
      API on API-mode allow-listed hosts.
    * **bonfire / opengov** — the tenant's portal index URL itself: gated
      surfaces whose fetches record the robots verdict (probed + recorded,
      disregarded per GL-GATE-08 / ADR-088) / WAF challenge as first-class
      outcomes (``record_refusals`` on every portal target).

    All per-tenant/per-run bounds ride the target row as data, from the
    reviewed ``[platform_endpoints.*]`` rows — never code constants.
    """
    out: list[dict[str, Any]] = []
    for tenant_id, row in portal_tenants().items():
        if source_id is not None and str(row.get("source_id")) != source_id:
            continue
        platform = str(row.get("platform") or "")
        cfg = platform_endpoints().get(platform, {})
        base: dict[str, Any] = {
            "tenant_id": tenant_id,
            "tenant": row.get("tenant") or tenant_id,
            "platform": platform,
            "source_id": str(row.get("source_id") or ""),
            "jurisdiction": row.get("jurisdiction"),
            "buyer_name": row.get("buyer_name"),
            "kind": "portal_index",
            # Per-host robots/WAF verdicts are recorded per tenant — a gated
            # tenant's failure never aborts the platform run (P26.3 pattern;
            # post-GL-GATE-08 the robots verdict is recorded + disregarded,
            # and the fetch's honest outcome — capture, access_restricted,
            # or unreachable — lands per tenant).
            "record_refusals": True,
        }
        for bound_key in ("doc_per_tenant", "doc_run_cap"):
            if cfg.get(bound_key) is not None:
                base[bound_key] = int(cfg[bound_key])
        if platform == "bidnet":
            storefront = str(row.get("storefront") or "").rstrip("/")
            host = str(cfg.get("host") or "www.bidnetdirect.com")
            group_id = _opt_str(row.get("purchasing_group_id"))
            unfiltered = {str(k) for k in cfg.get("index_unfiltered_kinds", ())}
            for index_kind in cfg.get("index_kinds", ()):
                for keyword in cfg.get("index_keywords", ()):
                    target = {
                        **base,
                        "id": f"{tenant_id}:{index_kind}:kw:{keyword}",
                        "url": (
                            f"https://{host}{storefront}/solicitations/{index_kind}-bids"
                            f"?{urlencode({'keywords': str(keyword)})}"
                        ),
                        "index_kind": str(index_kind),
                        "index_keyword": str(keyword),
                        "purchasing_group_id": group_id,
                    }
                    out.append(target)
            for index_kind in sorted(unfiltered):
                out.append(
                    {
                        **base,
                        "id": f"{tenant_id}:{index_kind}",
                        "url": f"https://{host}{storefront}/solicitations/{index_kind}-bids",
                        "index_kind": str(index_kind),
                        "index_keyword": None,
                        "purchasing_group_id": group_id,
                    }
                )
        elif platform == "socrata":
            host = str(row.get("host") or "")
            dataset = str(row.get("dataset") or "")
            limit = _opt_int(row.get("limit")) or 500
            date_field = str(row.get("date_field") or "")
            template = str(
                cfg.get("index_path_template") or "https://{host}/resource/{dataset}.json"
            )
            query = urlencode(
                {
                    "$limit": limit,
                    **({"$order": f"{date_field} DESC"} if date_field else {}),
                }
            )
            out.append(
                {
                    **base,
                    "id": f"{tenant_id}:rows",
                    "url": f"{template.format(host=host, dataset=dataset)}?{query}",
                    "index_kind": "rows",
                    "index_keyword": None,
                    "host": host,
                    "dataset": dataset,
                    "limit": limit,
                    # The reviewed per-dataset field aliases ride the target —
                    # extract/normalize read the dataset's own column names
                    # from the registry row, never hardcoded.
                    "id_fields": [str(f) for f in row.get("id_fields", ())],
                    "title_fields": [str(f) for f in row.get("title_fields", ())],
                    "date_field": date_field or None,
                    "vendor_field": _opt_str(row.get("vendor_field")),
                    "amount_field": _opt_str(row.get("amount_field")),
                    "dept_field": _opt_str(row.get("dept_field")),
                    "notice_type_field": _opt_str(row.get("notice_type_field")),
                    "deadline_field": _opt_str(row.get("deadline_field")),
                    "doc_field": _opt_str(row.get("doc_field")),
                }
            )
        else:
            # bonfire / opengov — the gated portal surface itself: the target
            # exists so each run records the host's own verdict (a robots
            # `Disallow: /` refusal, a WAF challenge) as first-class data.
            host = str(row.get("host") or "")
            portal_path = str(row.get("portal_path") or "/portal")
            url = (
                f"https://{host}{portal_path}"
                if platform == "opengov"
                else f"https://{host}/portal"
            )
            out.append(
                {
                    **base,
                    "id": f"{tenant_id}:portal",
                    "url": url,
                    "index_kind": "portal",
                    "index_keyword": None,
                    "host": host,
                }
            )
    return out


def portal_target_for_uri(uri: str) -> Mapping[str, Any] | None:
    """The portal tenant target whose generated index URL ``uri`` fetches (P26.10)."""
    for target in portal_targets():
        if str(target["url"]) == uri:
            return target
    return None


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
        if ctx.source.id in procurement_portal_sources():
            # P26.10: a procurement-portal source's targets ARE its tenant rows
            # (live_targets kind=procurement_portal_tenants); dedupe on the
            # generated index URL so a supplied target never double-fetches.
            seen_urls = {str(t.get("url")) for t in targets}
            targets = [
                *targets,
                *(
                    t
                    for t in portal_targets(source_id=ctx.source.id)
                    if str(t.get("url")) not in seen_urls
                ),
            ]
        if ctx.source.id == source_ids().get("usaspending"):
            # P26.14: append the generated bounded sweep targets (keyword ×
            # page sub/prime slices + awarding-agency slices) — dedupe on id
            # so a supplied/explicit target never double-fetches a slice.
            # `parameters["sweep_expansion"] = False` suppresses generation —
            # the replay/fixture path's opt-out when it drives explicit
            # targets only; live runs always expand.
            if ctx.parameters.get("sweep_expansion", True):
                seen = {str(t.get("id")) for t in targets if t.get("id")}
                generated = [t for t in usaspending_award_targets() if str(t.get("id")) not in seen]
                targets = [*targets, *generated]
                # Register generated slices so post-capture stages recover
                # slice provenance from the capture's source_uri (P26.15 —
                # the same mechanism discover_more continuations use).
                for t in generated:
                    ctx.resolved_targets[str(t["url"])] = t
            for target in targets:
                assert_pulls_subawards(target)
        if ctx.source.id == source_ids().get("sam_gov"):
            # P26.14: append the widened per-keyword search targets; a supplied
            # target whose `title` param already names a keyword suppresses the
            # generated slice for that keyword (no double-fetch).
            supplied = {
                t for t in (_sam_gov_title_param(str(x.get("url", ""))) for x in targets) if t
            }
            generated = [
                t
                for t in sam_gov_search_targets()
                if str(t.get("index_keyword", "")).lower() not in supplied
            ]
            targets = [*targets, *generated]
            for t in generated:
                ctx.resolved_targets[str(t["url"])] = t
        if ctx.source.id == source_ids().get("ted_eu"):
            # P26.15: append the generated bounded TED sweep targets (11
            # keyword + 10 verified CPV slices, one PAGE_NUMBER page each) —
            # dedupe on id so a supplied/explicit target never double-fetches
            # a slice. `parameters["sweep_expansion"] = False` suppresses
            # generation — the replay/fixture path's opt-out when it drives
            # explicit targets only; live runs always expand.
            if ctx.parameters.get("sweep_expansion", True):
                seen = {str(t.get("id")) for t in targets if t.get("id")}
                generated = [t for t in ted_eu_search_targets() if str(t.get("id")) not in seen]
                targets = [*targets, *generated]
                for t in generated:
                    ctx.resolved_targets[str(t["url"])] = t
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
        if ctx.source.id in procurement_portal_sources():
            return self._discover_portal_documents(ctx, captures)
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

    def _discover_portal_documents(
        self, ctx: RunContext, captures: Sequence[CaptureRef]
    ) -> list[Mapping[str, Any]]:
        """Bounded portal detail-document targets from captured tenant indexes (P26.10).

        The portal analogue of the agenda-document continuation: a captured
        **portal index** (a BidNet storefront solicitation list) is the
        discovery surface for its item detail pages — each item's
        ``solicitation-link`` href is the document URL (taken from the item's
        own link, never constructed). Selection is bounded and deterministic:
        tier-0 = items whose title matches the reviewed agenda_content_vocab
        (a surveillance-relevant solicitation title), then canonical order —
        the item's own ``published``/``closing`` date (most recent first) with
        the item id as tie-break, never server ordering — capped at
        ``doc_per_tenant`` per tenant and ``doc_run_cap`` per run, the reviewed
        bounds riding each target row as data. The same solicitation surfacing
        under several keyword windows resolves once (dedupe on its detail URL).
        Socrata datasets resolve nothing — the record IS the document.
        """
        resolved: list[Mapping[str, Any]] = []
        run_cap: int | None = None
        for capture in captures:
            index_target = _portal_index_target_for(ctx, capture.source_uri)
            if index_target is None:
                continue
            platform = str(index_target.get("platform") or "")
            if platform != "bidnet":
                continue  # only BidNet storefronts fan out to detail pages
            cfg = platform_endpoints().get(platform, {})
            if run_cap is None:
                run_cap = _opt_int(index_target.get("doc_run_cap") or cfg.get("doc_run_cap"))
            per_tenant = _opt_int(index_target.get("doc_per_tenant") or cfg.get("doc_per_tenant"))
            if not per_tenant:
                continue
            try:
                items = _bidnet_index_items(
                    ctx.captures.get(capture.digest),
                    source_id=ctx.source.id,
                    source_uri=str(capture.source_uri),
                )
            except ContentDrift:
                continue  # drift is recorded by the index parse, not re-raised here
            for item, tier in _select_portal_document_items(items, index_target, cfg, per_tenant):
                url = str(item.get("detail_url") or "")
                if not url or url in ctx.resolved_targets:
                    continue
                item_id = _portal_item_id(item)
                target: dict[str, Any] = {
                    "id": f"{index_target.get('tenant_id')}:doc:{item_id}",
                    "url": url,
                    "kind": "portal_document",
                    "platform": platform,
                    "tenant_id": index_target.get("tenant_id"),
                    "tenant": index_target.get("tenant"),
                    "source_id": index_target.get("source_id"),
                    "jurisdiction": index_target.get("jurisdiction"),
                    "buyer_name": index_target.get("buyer_name"),
                    "index_url": str(capture.source_uri),
                    "index_kind": index_target.get("index_kind"),
                    "index_keyword": index_target.get("index_keyword"),
                    "item": dict(item),
                    "item_id": item_id,
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
        portal_target = _portal_target_for(ctx, capture.source_uri)
        if portal_target is not None:
            if portal_target.get("kind") == "portal_document":
                return self._parse_portal_document(ctx, capture, data, portal_target)
            return self._parse_portal_index(ctx, capture, data, portal_target)
        if ctx.source.id == source_ids().get("ted_eu"):
            return self._parse_ted_eu_page(ctx, capture, data)
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

    def _parse_portal_index(
        self,
        ctx: RunContext,
        capture: CaptureRef,
        data: bytes,
        target: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Structure a captured portal index by platform contract (P26.10).

        Genre is re-derived from the captured bytes, never trusted from the
        target label. **bidnet** — the storefront's ``mets-table-row`` item
        markup; a page carrying neither a ``solicitation-link`` item nor the
        ``id="solicitationList"`` container (present even on a zero-result
        page) is :class:`ContentDrift`, while a marked-empty list is an honest
        ``empty`` outcome. **socrata** — the SoQL rows payload MUST decode to a
        JSON array; an object (Socrata's error envelope answers HTTP 200 with
        ``{"error": true, ...}``) or an undecodable body is ContentDrift, and
        an empty array is an honest ``empty`` window. **bonfire / opengov**
        carry no reviewed markup contract — a captured body is ContentDrift by
        construction (their live outcomes are the recorded robots verdict —
        disregarded per GL-GATE-08 / ADR-088 — plus the fetch's honest result:
        a WAF challenge or drift, never a fabricated parse).
        """
        platform = str(target.get("platform") or "")
        source_uri = str(capture.source_uri)
        if platform == "bidnet":
            items = _bidnet_index_items(data, source_id=ctx.source.id, source_uri=source_uri)
            return {
                "kind": "portal_index",
                "capture": capture,
                "target": dict(target),
                "platform": platform,
                "items": items,
                "text": html_text(data),
                "byte_size": len(data),
            }
        if platform == "socrata":
            try:
                payload = json.loads(data)
            except (ValueError, UnicodeDecodeError) as exc:
                raise ContentDrift(
                    ctx.source.id,
                    f"portal index {source_uri} is not parseable JSON (the socrata rows-API genre)",
                    details=str(exc)[:200],
                ) from exc
            if not isinstance(payload, list):
                raise ContentDrift(
                    ctx.source.id,
                    f"portal index {source_uri} is a JSON {type(payload).__name__}, "
                    "not the socrata rows array (an error envelope is not an index)",
                    details=str(payload)[:200],
                )
            socrata_items: list[dict[str, Any]] = [
                dict(o) if isinstance(o, Mapping) else {"value": o} for o in payload
            ]
            return {
                "kind": "portal_index",
                "capture": capture,
                "target": dict(target),
                "platform": platform,
                "items": socrata_items,
                "text": utf8_text(data),
                "byte_size": len(data),
            }
        raise ContentDrift(
            ctx.source.id,
            f"portal index {source_uri} has no reviewed markup contract "
            f"(platform {platform!r} is a gated surface — its live outcome is the "
            "recorded refusal/challenge, not a fabricated parse)",
        )

    def _parse_portal_document(
        self,
        ctx: RunContext,
        capture: CaptureRef,
        data: bytes,
        target: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Structure a captured portal detail document by genre (P26.10).

        A BidNet detail page is ``doc_genre = "html"``: a non-HTML body is
        genre drift, and a page without the platform's field markup
        (``mets-field`` / ``descriptionText`` — the reviewed detail-page
        contract) is :class:`ContentDrift`. A marked page with no visible text
        is an honest ``empty`` outcome, never drift.
        """
        platform = str(target.get("platform") or "")
        cfg = platform_endpoints().get(platform, {})
        source_uri = str(capture.source_uri)
        media = str(capture.media_type or "").lower()
        genre = str(cfg.get("doc_genre") or "any")
        if platform == "bidnet" or genre == "html":
            if not (
                "html" in media or "text" in media or media in ("", "application/octet-stream")
            ):
                raise ContentDrift(
                    ctx.source.id,
                    f"portal document {source_uri} is {capture.media_type!r}, "
                    f"not an HTML detail page (the {platform} document genre)",
                )
            raw_text = utf8_text(data)
            if "mets-field" not in raw_text and "descriptionText" not in raw_text:
                raise ContentDrift(
                    ctx.source.id,
                    f"portal document {source_uri} lacks the {platform} detail-page "
                    "field markup (mets-field/descriptionText) — the markup contract "
                    "changed, this is not an empty notice",
                    details=raw_text[:200],
                )
            return {
                "kind": "portal_document",
                "capture": capture,
                "target": dict(target),
                "doc_genre": "html",
                "extraction_method": "selector_template",
                "text": html_text(data),
                "pages": None,
                "byte_size": len(data),
            }
        raise ContentDrift(
            ctx.source.id,
            f"portal document {source_uri} has no reviewed document genre (platform {platform!r})",
        )

    def _parse_ted_eu_page(
        self, ctx: RunContext, capture: CaptureRef, data: bytes
    ) -> dict[str, Any]:
        """Structure a captured TED Search-API page — fail-closed on drift (P26.15).

        The capture must be a ``ExpertSearchResponse`` object:
        ``{"notices": [...], "totalNoticeCount": int|null, "timedOut": bool}``.
        The 400 error envelope (``{"message": …, "error": {…}}`` — verified
        live 2026-09-18), a non-object payload, a missing/non-list ``notices``
        member, or a non-object notice row is content drift, never garbage
        claims — the run fails loud rather than asserting a misread shape.
        An empty ``notices`` list is an honest empty slice.
        """
        source_uri = str(capture.source_uri)
        try:
            payload = json.loads(data)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ContentDrift(
                ctx.source.id,
                f"TED search page {source_uri} is not JSON ({exc}) — the response "
                "shape changed, this is not an empty result",
            ) from exc
        if not isinstance(payload, Mapping):
            raise ContentDrift(
                ctx.source.id,
                f"TED search page {source_uri} is not a JSON object — the response "
                "shape changed, this is not an empty result",
                details=str(payload)[:200],
            )
        notices = payload.get("notices")
        if "error" in payload or ("message" in payload and notices is None):
            raise ContentDrift(
                ctx.source.id,
                f"TED search page {source_uri} is an API error envelope "
                f"({str(payload.get('message'))[:120]!r}) — the request was refused "
                "by the API, not a result page",
                details=str(payload)[:200],
            )
        if not isinstance(notices, list):
            raise ContentDrift(
                ctx.source.id,
                f"TED search page {source_uri} lacks a `notices` list — the "
                "ExpertSearchResponse contract changed",
                details=str(payload)[:200],
            )
        for pos, notice in enumerate(notices):
            if not isinstance(notice, Mapping):
                raise ContentDrift(
                    ctx.source.id,
                    f"TED search page {source_uri} notice[{pos}] is not an object — "
                    "the NoticeResponse contract changed",
                    details=str(notice)[:200],
                )
        return {
            "kind": "ted_eu_search",
            "payload": dict(payload),
            "capture": capture,
            "raw_text": utf8_text(data),
        }

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
        if parsed["kind"] == "portal_index":
            capture = parsed["capture"]
            target = parsed["target"]
            items = parsed["items"]
            out: list[Mapping[str, Any]] = [
                {
                    "record_kind": "portal_index",
                    "source_uri": capture.source_uri,
                    "capture_digest": capture.digest,
                    "media_type": capture.media_type,
                    "retrieved_at": (
                        capture.retrieved_at.isoformat() if capture.retrieved_at else None
                    ),
                    "byte_size": parsed["byte_size"],
                    "text": parsed["text"],
                    "items_count": len(items),
                    "target": target,
                }
            ]
            out.extend(
                {
                    "record_kind": "portal_index_item",
                    "raw": dict(item),
                    "tenant": target,
                    "row_index": pos,
                    "capture_digest": capture.digest,
                    "retrieved_at": (
                        capture.retrieved_at.isoformat() if capture.retrieved_at else None
                    ),
                }
                for pos, item in enumerate(items)
            )
            return out
        if parsed["kind"] == "portal_document":
            capture = parsed["capture"]
            return [
                {
                    "record_kind": "portal_document",
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
        if parsed["kind"] == "ted_eu_search":
            # P26.15: one `procurement_notice` raw record per notice in the
            # captured page, each carrying the sweep-slice provenance recovered
            # from the recorded source_uri's #sig-slice tag; a `ted_eu_slice`
            # outcome row trails them (result counts / page bounds / timed_out).
            capture = parsed["capture"]
            payload = parsed["payload"]
            target = _usaspending_target_for(ctx, str(capture.source_uri))

            def _str_or_none(key: str) -> str | None:
                value = target.get(key) if target else None
                return str(value) if value is not None else None

            prov: dict[str, Any] = {
                "api": "ted_eu",
                "source_uri": str(capture.source_uri),
                "capture_digest": capture.digest,
                "retrieved_at": (
                    capture.retrieved_at.isoformat() if capture.retrieved_at else None
                ),
                "slice": _str_or_none("slice"),
                "query_kind": _str_or_none("query_kind"),
                "query": _str_or_none("query"),
                "ted_keyword": _str_or_none("ted_keyword"),
                "cpv_code": _str_or_none("cpv_code"),
                "page": target.get("page") if target else None,
                "limit": target.get("limit") if target else None,
                "plan_version": _str_or_none("plan_version"),
            }
            timed_out = bool(payload.get("timedOut"))
            notices = list(payload.get("notices") or [])
            total = payload.get("totalNoticeCount")
            page = int(prov["page"] or 1)
            limit = int(prov["limit"] or 0)
            outcome = "timed_out" if timed_out else ("hits" if notices else "empty")
            records: list[Mapping[str, Any]] = []
            if not timed_out:
                # A timed-out page is a partial result set: its outcome is
                # recorded honestly and its notices are NOT asserted — the next
                # run re-finds them; asserting a partial page would overstate
                # the slice's coverage.
                for pos, notice in enumerate(notices):
                    records.append(
                        {
                            "record_kind": "procurement_notice",
                            "raw": dict(notice),
                            "notice_provenance": prov,
                            "row_index": pos,
                        }
                    )
            records.append(
                {
                    "record_kind": "ted_eu_slice",
                    "source_uri": capture.source_uri,
                    "capture_digest": capture.digest,
                    "provenance": prov,
                    "items_count": len(notices),
                    "total_notice_count": total,
                    "timed_out": timed_out,
                    "outcome": outcome,
                    # `truncated` documents the bound itself: the query matched
                    # more notices than the bounded page window retrieved.
                    "truncated": bool(isinstance(total, int) and limit and page * limit < total),
                    "page": page,
                    "limit": limit,
                    "plan_version": prov["plan_version"],
                }
            )
            return records
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
        if ctx.source.id == source_ids().get("usaspending"):
            # P26.14: the bounded award-search payload — `results` is the award
            # list. Each row emits a `procurement_notice` raw record carrying
            # its sweep-slice provenance (recovered from the recorded
            # source_uri's #sig-slice tag) so normalize() can emit the typed
            # award fields; a sub-award-shaped row ALSO emits a `subaward`
            # record so the FundingInstrument traceable link (SIG-ONTO-033)
            # is preserved. A `usaspending_slice` outcome row records the
            # per-slice result count + page metadata for the run record.
            capture = parsed["capture"]
            target = _usaspending_target_for(ctx, str(capture.source_uri)) if capture else None
            provenance = {
                "source_uri": str(capture.source_uri) if capture else None,
                "capture_digest": capture.digest if capture else None,
                "retrieved_at": (
                    capture.retrieved_at.isoformat() if capture and capture.retrieved_at else None
                ),
                "slice": str(target.get("slice")) if target else None,
                "award_kind": str(target.get("award_kind")) if target else None,
                "index_keyword": str(target.get("index_keyword")) if target else None,
                "agency": str(target.get("agency")) if target else None,
                "page": target.get("page") if target else None,
            }
            objects = list(payload.get("results", [])) if isinstance(payload, Mapping) else []
            award_records: list[Mapping[str, Any]] = []
            for pos, obj in enumerate(objects):
                if not isinstance(obj, Mapping):
                    obj = {"value": obj}
                award_records.append(
                    {
                        "record_kind": "procurement_notice",
                        "raw": dict(obj),
                        "notice_provenance": provenance,
                        "row_index": pos,
                    }
                )
                if provenance["award_kind"] == "sub" or _looks_like_subaward(obj):
                    award_records.append({"record_kind": "subaward", "raw": dict(obj)})
            # The per-slice outcome row trails the result records.
            award_records.append(
                {
                    "record_kind": "usaspending_slice",
                    "source_uri": capture.source_uri if capture else None,
                    "capture_digest": capture.digest if capture else None,
                    "provenance": provenance,
                    "items_count": len(objects),
                    "page_metadata": (
                        dict(payload.get("page_metadata", {}))
                        if isinstance(payload, Mapping)
                        else {}
                    ),
                }
            )
            return award_records
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
        extracted: list[Mapping[str, Any]] = []
        for obj in objects:
            kind = "subaward" if _looks_like_subaward(obj) else "contract"
            extracted.append({"record_kind": kind, "raw": dict(obj)})
        return extracted

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
                prov = dict(raw.get("notice_provenance") or {})
                if prov.get("api") == "ted_eu":
                    out.extend(self._normalize_ted_eu_notice(ctx, raw))
                elif raw.get("notice_provenance"):
                    out.extend(self._normalize_usaspending_notice(ctx, raw))
                else:
                    out.extend(self._normalize_notice(ctx, raw))
            elif kind == "usaspending_slice":
                # P26.14 per-slice outcome row — run-record data, not a claim.
                out.append(_stamp(dict(raw), source_id=ctx.source.id))
            elif kind == "ted_eu_slice":
                # P26.15 per-slice outcome row — run-record data, not a claim.
                out.append(_stamp(dict(raw), source_id=ctx.source.id))
            elif kind == "agenda_document":
                out.extend(self._normalize_agenda_document(ctx, raw))
            elif kind == "portal_index":
                out.append(self._normalize_portal_index(ctx, raw))
            elif kind == "portal_index_item":
                out.extend(self._normalize_portal_notice(ctx, raw))
            elif kind == "portal_document":
                out.extend(self._normalize_portal_document(ctx, raw))
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

    # -- portal normalizers (P26.10 / SOURCES.9) --

    def _normalize_portal_index(self, ctx: RunContext, raw: Mapping[str, Any]) -> dict[str, Any]:
        """The per-tenant portal index outcome row — one row per captured index.

        Records the honest window outcome: the tenant, the reviewed index kind
        + keyword (``None`` on the unfiltered window), how many items the page
        carried, the title-level vocab signal (informational — the claims
        themselves always come from verbatim document text), and the bounded
        continuation window it resolved under. An index with zero items is an
        ``empty`` outcome, never drift (drift already failed closed in parse).
        """
        target = raw["target"]
        tenant_id = str(target.get("tenant_id") or "")
        platform = str(target.get("platform") or "")
        index_kind = _opt_str(target.get("index_kind")) or "index"
        keyword = _opt_str(target.get("index_keyword"))
        items_count = int(raw.get("items_count") or 0)
        text = str(raw.get("text") or "")
        matches = scan_agenda_content(text) if text else []
        subject = (
            f"portal_index:{ctx.source.id}:{tenant_id or 'unscoped'}:"
            f"{index_kind}:{keyword or 'all'}"
        )
        jurisdiction = _opt_str(target.get("jurisdiction"))
        row = _stamp(
            {
                "record_kind": "portal_index",
                "subject_id": subject,
                "predicate_id": assert_predicate_allowed("portal_index"),
                "external_id": f"{index_kind}:{keyword or 'all'}",
                "raw_value": str(raw["source_uri"]),
                "platform": platform,
                "tenant_id": tenant_id or None,
                "jurisdiction": jurisdiction,
                "index_kind": index_kind,
                "index_keyword": keyword,
                "items_count": items_count,
                "title_matched_terms": sorted({m["term_id"] for m in matches}),
                "outcome": "empty" if items_count == 0 else "items",
                "capture_digest": raw.get("capture_digest"),
                "doc_window": {
                    "per_tenant": target.get("doc_per_tenant"),
                    "run_cap": target.get("doc_run_cap"),
                },
                "content_vocab_version": content_vocab_version(),
            },
            source_id=ctx.source.id,
        )
        if jurisdiction:
            row["jurisdiction_candidate"] = org_candidate(
                jurisdiction, scheme="portal.jurisdiction_name"
            )
        return row

    def _normalize_portal_notice(
        self, ctx: RunContext, raw: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        """One portal index item → a ``procurement_notice`` subject + claims (P26.10).

        The portal analogue of the SAM ``procurement_notice`` path: a storefront
        line item or a contract-register row is the dated evidence of a
        procurement lifecycle event — a solicitation, an award record — never a
        Contract assertion. Field aliases ride the target (the tenant registry's
        reviewed column names); the lifecycle transition maps through the
        platform's reviewed ``notice_map`` — an unlisted kind/type emits the
        index facts only, never a guessed transition (§3.1).
        """
        item = raw["raw"]
        tenant = raw.get("tenant") or {}
        tenant_id = str(tenant.get("tenant_id") or "")
        platform = str(tenant.get("platform") or "")
        jurisdiction = _opt_str(tenant.get("jurisdiction"))
        index_kind = _opt_str(tenant.get("index_kind"))
        external_id = _portal_external_id(item, tenant)
        subject = f"procurement_notice:{ctx.source.id}:{tenant_id or 'unscoped'}:{external_id}"
        title = _portal_title(item, tenant)
        posted = _portal_posted_date(item, tenant)
        deadline = _first_nonempty(
            item, ("closing", "due_date", str(tenant.get("deadline_field") or ""))
        )
        buyer = _first_nonempty(item, (str(tenant.get("dept_field") or ""),)) or _opt_str(
            tenant.get("buyer_name")
        )
        document = _first_nonempty(
            item,
            ("detail_url", str(tenant.get("doc_field") or "")),
        )
        notice_type = _portal_notice_type(item, tenant, index_kind)
        surface: dict[str, Any] = {
            "external_id": external_id,
            "notice_type": notice_type,
            "posted_date": posted,
            "response_deadline": deadline,
            "buyer": buyer,
            "document": document,
        }
        vendor = _first_nonempty(item, (str(tenant.get("vendor_field") or ""),))
        amount = _first_nonempty(item, (str(tenant.get("amount_field") or ""),))
        rows: list[dict[str, Any]] = [
            _stamp(
                {
                    "record_kind": "procurement_notice",
                    "subject_id": subject,
                    "predicate_id": assert_predicate_allowed("procurement_notice"),
                    "external_id": external_id,
                    "raw_value": title or external_id,
                    "predicate_surface": {k: v for k, v in surface.items() if v is not None},
                    "title": title,
                    "platform": platform,
                    "tenant_id": tenant_id or None,
                    "jurisdiction": jurisdiction,
                    "index_kind": index_kind,
                    "index_keyword": _opt_str(tenant.get("index_keyword")),
                    "row_index": raw.get("row_index"),
                    "raw": dict(item),
                },
                source_id=ctx.source.id,
            )
        ]
        if jurisdiction:
            rows[0]["jurisdiction_candidate"] = org_candidate(
                jurisdiction, scheme="portal.jurisdiction_name"
            )
        for predicate, value in surface.items():
            if value is None:
                continue
            row: dict[str, Any] = {
                "record_kind": "claim",
                "subject_id": subject,
                "predicate_id": assert_predicate_allowed(predicate),
                "raw_value": _raw_value_of(value),
                "value": value,
                "platform": platform,
                "tenant_id": tenant_id or None,
                "jurisdiction": jurisdiction,
            }
            if predicate == "buyer":
                row["candidate_identifier"] = org_candidate(str(value))
            rows.append(_stamp(row, source_id=ctx.source.id))
        if vendor:
            rows.append(
                _stamp(
                    {
                        "record_kind": "claim",
                        "subject_id": subject,
                        "predicate_id": assert_predicate_allowed("seller"),
                        "raw_value": vendor,
                        "value": vendor,
                        "platform": platform,
                        "tenant_id": tenant_id or None,
                        "jurisdiction": jurisdiction,
                        "candidate_identifier": org_candidate(
                            vendor, scheme="procurement.org_name"
                        ),
                    },
                    source_id=ctx.source.id,
                )
            )
        if amount:
            rows.append(
                _stamp(
                    {
                        "record_kind": "claim",
                        "subject_id": subject,
                        "predicate_id": assert_predicate_allowed("amount"),
                        "raw_value": amount,
                        "value": amount,
                        "platform": platform,
                        "tenant_id": tenant_id or None,
                        "jurisdiction": jurisdiction,
                    },
                    source_id=ctx.source.id,
                )
            )
        state = _portal_lifecycle_state(item, tenant, platform, index_kind)
        if state:
            rows.append(
                _stamp(
                    {
                        "record_kind": "claim",
                        "subject_id": subject,
                        "predicate_id": assert_predicate_allowed("lifecycle_transition"),
                        "raw_value": state,
                        "value": {"state": state, "date": posted},
                        "platform": platform,
                        "tenant_id": tenant_id or None,
                        "jurisdiction": jurisdiction,
                    },
                    source_id=ctx.source.id,
                )
            )
        if platform == "socrata":
            # The register row IS the document: emit its portal_document outcome
            # row plus verbatim content_term claims scanned over the reviewed
            # text fields (P26.6 rules — raw_value stays the verbatim literal,
            # the locator is a byte range into the named record field).
            rows.extend(self._socrata_record_rows(ctx, raw, subject=subject))
        return rows

    def _socrata_record_rows(
        self, ctx: RunContext, raw: Mapping[str, Any], *, subject: str
    ) -> list[dict[str, Any]]:
        """The document-level rows for one Socrata register record (P26.10).

        A dataset row carries its own verbatim text — the reviewed
        ``title_fields`` aliases ride the tenant target — so the record doubles
        as its document: a ``portal_document`` outcome row (the row's own scan
        verdict), a ``document`` claim locating the record by ``Locator.row``
        inside the captured array, and ``content_term`` claims whose
        ``evidence.locator`` is a byte range into the NAMED field value
        (``evidence.field``) — every literal verified verbatim by construction.
        """
        item = raw["raw"]
        tenant = raw.get("tenant") or {}
        tenant_id = str(tenant.get("tenant_id") or "")
        platform = str(tenant.get("platform") or "")
        jurisdiction = _opt_str(tenant.get("jurisdiction"))
        external_id = _portal_external_id(item, tenant)
        doc_subject = f"portal_document:{ctx.source.id}:{tenant_id or 'unscoped'}:{external_id}"
        index_url = str(tenant.get("url") or "")
        row_index = raw.get("row_index")
        retrieved_date = _opt_str(raw.get("retrieved_at"))
        retrieved_date = retrieved_date[:10] if retrieved_date else None

        fields = [str(f) for f in tenant.get("title_fields", ()) if str(f)]
        scanned: list[dict[str, Any]] = []
        suppressions: list[dict[str, Any]] = []
        total_len = 0
        for field_name in fields:
            value = _opt_str(item.get(field_name))
            if not value:
                continue
            total_len += len(value)
            for m in scan_agenda_content(value):
                token = content_guard_token(str(m["literal"])) or content_guard_token(
                    str(m["term_label"])
                )
                if token is not None:
                    suppressions.append(
                        {
                            "term_id": m["term_id"],
                            "token": token,
                            "literal": str(m["literal"]),
                            "field": field_name,
                        }
                    )
                else:
                    scanned.append({**m, "field": field_name})
        outcome = "empty" if total_len == 0 else ("matched" if scanned else "no_match")
        doc_row = _stamp(
            {
                "record_kind": "portal_document",
                "subject_id": doc_subject,
                "predicate_id": assert_predicate_allowed("document"),
                "external_id": external_id,
                "raw_value": index_url,
                "platform": platform,
                "tenant_id": tenant_id or None,
                "jurisdiction": jurisdiction,
                "index_url": index_url,
                "index_kind": _opt_str(tenant.get("index_kind")),
                "index_keyword": None,
                "notice_subject": subject,
                "capture_digest": raw.get("capture_digest"),
                "doc_genre": "json",
                "extraction_method": "json_text",
                "row_index": row_index,
                "text_length": total_len,
                "matched_terms": sorted({m["term_id"] for m in scanned}),
                "match_count": sum(int(m["match_count"]) for m in scanned),
                "fields_scanned": [f for f in fields if _opt_str(item.get(f))],
                "outcome": outcome,
                "content_vocab_version": content_vocab_version(),
            },
            source_id=ctx.source.id,
        )
        if jurisdiction:
            doc_row["jurisdiction_candidate"] = org_candidate(
                jurisdiction, scheme="portal.jurisdiction_name"
            )
        if suppressions:
            doc_row["part_viii_suppressions"] = suppressions
        rows: list[dict[str, Any]] = [doc_row]

        # The record locator: this document is row N of the captured SoQL array.
        if row_index is not None:
            rows.append(
                _stamp(
                    {
                        "record_kind": "claim",
                        "subject_id": subject,
                        "predicate_id": assert_predicate_allowed("document"),
                        "value": index_url,
                        "raw_value": index_url,
                        "observed_at": retrieved_date,
                        "platform": platform,
                        "tenant_id": tenant_id or None,
                        "jurisdiction": jurisdiction,
                        "document_subject": doc_subject,
                        "evidence_genre": "portal_document",
                        "evidence": {
                            "source_url": index_url,
                            "retrieved_date": retrieved_date,
                            "extraction_method": "json_text",
                            "locator": Locator.row(int(row_index)).to_row(),
                        },
                    },
                    source_id=ctx.source.id,
                )
            )
        for match in scanned:
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
                        "document": index_url,
                        "document_subject": doc_subject,
                        "evidence_genre": "portal_document",
                        "evidence": {
                            "source_url": index_url,
                            "retrieved_date": retrieved_date,
                            "extraction_method": "json_text",
                            "field": match["field"],
                            "locator": Locator.byte_range(
                                int(match["start"]), int(match["end"])
                            ).to_row(),
                            "record_row": row_index,
                        },
                    },
                    source_id=ctx.source.id,
                )
            )
        return rows

    def _normalize_portal_document(
        self, ctx: RunContext, raw: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        """A captured portal detail page → doc row + verbatim content claims (P26.10).

        Mirrors ``_normalize_agenda_document``: the ``portal_document`` row
        records the honest outcome — ``matched`` / ``no_match`` / ``empty`` —
        and each matched term emits a ``content_term`` claim on the
        ``procurement_notice`` subject whose ``raw_value`` is the VERBATIM
        literal slice of the captured text and whose ``evidence.locator`` is a
        byte range into it (or the PDF page). A literal carrying a Part VIII
        forbidden token is suppressed and recorded, never emitted (§0.7/§43.2).
        """
        target = raw["target"]
        item = target.get("item") if isinstance(target.get("item"), Mapping) else {}
        platform = str(target.get("platform") or "")
        tenant_id = str(target.get("tenant_id") or "")
        jurisdiction = _opt_str(target.get("jurisdiction"))
        external_id = str(target.get("item_id") or _portal_item_id(item))
        notice_subject = (
            f"procurement_notice:{ctx.source.id}:{tenant_id or 'unscoped'}:{external_id}"
        )
        doc_url = str(raw["source_uri"])
        doc_subject = f"portal_document:{ctx.source.id}:{tenant_id or 'unscoped'}:{external_id}"
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
                "record_kind": "portal_document",
                "subject_id": doc_subject,
                "predicate_id": assert_predicate_allowed("document"),
                "external_id": external_id,
                "raw_value": doc_url,
                "platform": platform,
                "tenant_id": tenant_id or None,
                "jurisdiction": jurisdiction,
                "index_url": target.get("index_url"),
                "index_kind": target.get("index_kind"),
                "index_keyword": target.get("index_keyword"),
                "notice_subject": notice_subject,
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
                jurisdiction, scheme="portal.jurisdiction_name"
            )
        if suppressions:
            doc_row["part_viii_suppressions"] = suppressions
        rows: list[dict[str, Any]] = [doc_row]

        # The document-locator claim: the notice's detail page was captured at
        # this URL.
        rows.append(
            _stamp(
                {
                    "record_kind": "claim",
                    "subject_id": notice_subject,
                    "predicate_id": assert_predicate_allowed("document"),
                    "value": doc_url,
                    "raw_value": doc_url,
                    "observed_at": retrieved_date,
                    "platform": platform,
                    "tenant_id": tenant_id or None,
                    "jurisdiction": jurisdiction,
                    "document_subject": doc_subject,
                    "evidence_genre": "portal_document",
                    "evidence": {
                        "source_url": doc_url,
                        "retrieved_date": retrieved_date,
                        "extraction_method": method,
                        "locator": Locator.byte_range(0, len(text)).to_row(),
                    },
                },
                source_id=ctx.source.id,
            )
        )
        for match in clean:
            locator: Mapping[str, Any] | None = (
                page_locator_for(pages, str(match["literal"]))
                if pages
                else Locator.byte_range(int(match["start"]), int(match["end"])).to_row()
            )
            if locator is None:
                continue  # a literal that cannot be located is never emitted (OL-24-18)
            rows.append(
                _stamp(
                    {
                        "record_kind": "claim",
                        "subject_id": notice_subject,
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
                        "evidence_genre": "portal_document",
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

    def _normalize_usaspending_notice(
        self, ctx: RunContext, raw: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        """A USAspending award row → a ``procurement_notice`` subject + typed claims (P26.14).

        The federal-award notice surface: award/notice id, recipient, awarding
        agency, amount, period, description, matched keyword — each claim
        carries the source field name and a locator into the captured
        ``results`` array. **Procured ≠ deployed**: the claims assert only
        what the award record literally says — a purchase signal, never
        deployment, use, or operational status. ``matched_keyword`` claims
        assert that the record's text CONTAINS a reviewed literal (raw_value
        is the verbatim slice), nothing more.
        """
        notice = raw["raw"]
        prov = dict(raw.get("notice_provenance") or {})
        row_index = raw.get("row_index")
        award_kind = str(prov.get("award_kind") or "prime")
        is_sub = award_kind == "sub"

        award_id = (
            _first_nonempty(
                notice,
                (
                    "Sub-Award ID",
                    "subaward_id",
                    "Award ID",
                    "award_id",
                    "internal_id",
                    "generated_internal_id",
                ),
            )
            or _digest_of(notice)[:24]
        )
        subject = f"procurement_notice:{ctx.source.id}:{award_id}"
        source_uri = str(prov.get("source_uri") or "")
        retrieved_date = (str(prov.get("retrieved_at") or "")[:10]) or None

        def _evidence(field: str, locator: Mapping[str, Any]) -> dict[str, Any]:
            return {
                "source_url": source_uri,
                "retrieved_date": retrieved_date,
                "extraction_method": "json_text",
                "field": field,
                "locator": locator,
                "record_row": row_index,
                "slice": prov.get("slice"),
                "index_keyword": prov.get("index_keyword"),
                "agency": prov.get("agency"),
                "capture_digest": prov.get("capture_digest"),
            }

        # --- the typed field surface (source label -> predicate) --------------
        recipient = _first_nonempty(
            notice, ("Sub-Awardee Name", "subawardee", "subrecipient_name", "Recipient Name")
        )
        agency = _first_nonempty(
            notice, ("Awarding Agency", "awarding_agency", "Awarding Sub Agency")
        )
        amount = _first_nonempty(
            notice, ("Sub-Award Amount", "subaward_amount", "Award Amount", "amount")
        )
        start_date = _first_nonempty(
            notice, ("Sub-Award Date", "subaward_date", "Start Date", "start_date")
        )
        end_date = _first_nonempty(notice, ("End Date", "end_date"))
        description = _first_nonempty(
            notice, ("Sub-Award Description", "subaward_description", "Description", "description")
        )
        action_date = _first_nonempty(
            notice, ("Sub-Award Date", "subaward_date", "Start Date", "Action Date")
        )
        federal_id = _first_nonempty(
            notice,
            ("prime_award_generated_internal_id", "prime_award_id", "federal_award_id"),
        )
        notice_type = _first_nonempty(notice, ("Award Type", "award_type")) or (
            "sub_award" if is_sub else "prime_award"
        )

        rows: list[dict[str, Any]] = [
            _stamp(
                {
                    "record_kind": "procurement_notice",
                    "subject_id": subject,
                    "predicate_id": assert_predicate_allowed("procurement_notice"),
                    "external_id": award_id,
                    "raw_value": award_id,
                    "notice_type": notice_type,
                    "award_kind": award_kind,
                    "provenance": prov,
                    "row_index": row_index,
                    "raw": dict(notice),
                },
                source_id=ctx.source.id,
            )
        ]

        field_claims: list[tuple[str, str, str, Any]] = [
            ("external_id", "Sub-Award ID" if is_sub else "Award ID", award_id, award_id),
        ]
        if recipient is not None:
            field_claims.append(
                (
                    "recipient",
                    "Sub-Awardee Name" if is_sub else "Recipient Name",
                    recipient,
                    recipient,
                )
            )
        if agency is not None:
            # Awarding agency: `funder` on assistance/sub-award rows (it pays
            # the program), `buyer` on prime contract awards (it purchases).
            agency_pred = "funder" if is_sub else "buyer"
            field_claims.append((agency_pred, "Awarding Agency", agency, agency))
        if amount is not None:
            field_claims.append(
                ("amount", "Sub-Award Amount" if is_sub else "Award Amount", amount, amount)
            )
        if start_date is not None or end_date is not None:
            period = {"start": start_date, "end": end_date}
            field_claims.append(("period", "Start Date/End Date", json.dumps(period), period))
        if description is not None:
            field_claims.append(
                (
                    "description",
                    "Sub-Award Description" if is_sub else "Description",
                    description,
                    description,
                )
            )
        if federal_id is not None:
            field_claims.append(
                ("federal_award_id", "prime_award_generated_internal_id", federal_id, federal_id)
            )

        for predicate, field_name, raw_literal, value in field_claims:
            # Part VIII guard: a literal carrying a forbidden token is
            # suppressed at the claim surface (the capture keeps the bytes;
            # the claim asserts the field exists without repeating the token).
            raw_out = _raw_value_of(raw_literal)
            suppressed = content_guard_token(raw_out) is not None
            row: dict[str, Any] = {
                "record_kind": "claim",
                "subject_id": subject,
                "predicate_id": assert_predicate_allowed(predicate),
                "raw_value": "[suppressed: part-VIII token]" if suppressed else raw_out,
                "value": None if suppressed else value,
                "observed_at": retrieved_date,
                "evidence": _evidence(field_name, Locator.row(int(row_index or 0)).to_row()),
            }
            if suppressed:
                row["part_viii_suppressed"] = True
            if predicate in ("recipient", "buyer", "funder"):
                row["candidate_identifier"] = org_candidate(str(value))
            rows.append(_stamp(row, source_id=ctx.source.id))

        # --- matched keywords: verbatim literals inside the record text ------
        # Scan the record's own text fields; a match emits `matched_keyword`
        # with the verbatim slice as raw_value and a byte-range locator into
        # the named field. The slice's index_keyword rides as provenance
        # regardless (it named the search, it is not itself a fact claim).
        text_fields = [
            f
            for f in (
                "Sub-Award Description",
                "Description",
                "subaward_description",
                "description",
                "Award Description",
            )
            if _opt_str(notice.get(f))
        ]
        matched: list[dict[str, Any]] = []
        for field_name in text_fields:
            text = str(notice[field_name])
            for match in scan_agenda_content(text):
                matched.append({**match, "field": field_name})
        seen_terms: set[tuple[str, str]] = set()
        for match in matched:
            key = (str(match["term_id"]), str(match["field"]))
            if key in seen_terms:
                continue
            seen_terms.add(key)
            rows.append(
                _stamp(
                    {
                        "record_kind": "claim",
                        "subject_id": subject,
                        "predicate_id": assert_predicate_allowed("matched_keyword"),
                        "value": match["term_id"],
                        "raw_value": match["literal"],
                        "term_label": match["term_label"],
                        "term_kind": match["term_kind"],
                        "observed_at": retrieved_date,
                        "evidence": _evidence(
                            str(match["field"]),
                            Locator.byte_range(int(match["start"]), int(match["end"])).to_row(),
                        ),
                    },
                    source_id=ctx.source.id,
                )
            )

        # --- lifecycle: a published award row asserts `awarded` --------------
        rows.append(
            _stamp(
                {
                    "record_kind": "claim",
                    "subject_id": subject,
                    "predicate_id": assert_predicate_allowed("lifecycle_transition"),
                    "raw_value": "awarded",
                    "value": {"state": "awarded", "date": action_date},
                    "observed_at": retrieved_date,
                    "evidence": _evidence(
                        "Sub-Award Date" if is_sub else "Start Date",
                        Locator.row(int(row_index or 0)).to_row(),
                    ),
                },
                source_id=ctx.source.id,
            )
        )
        return rows

    def _normalize_ted_eu_notice(
        self, ctx: RunContext, raw: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        """A TED OJ S notice → a ``procurement_notice`` subject + typed claims (P26.15).

        The EU notice surface: publication number, buyer, country, value (when
        stated), description, place of performance, matched keyword — each
        claim carries the source field name and a locator into the captured
        ``notices`` array. **Procured ≠ deployed**: a tender notice asserts a
        buyer published procurement text containing a reviewed literal —
        never that equipment was deployed, operates, or exists in a count.
        ``matched_keyword`` asserts that the notice's text CONTAINS a reviewed
        literal (``raw_value`` is the verbatim slice), nothing more.
        Jurisdiction follows the P26.9 convention: the verbatim alpha-3 code
        stays ``raw_value``; the normalized ``iso.3166_1_alpha2`` identifier
        comes from the reviewed country map — never fabricated — and NUTS
        place-of-performance literals are recorded verbatim (a NUTS code is
        NOT an ISO 3166-2 subdivision and is never emitted as one).
        """
        notice = raw["raw"]
        prov = dict(raw.get("notice_provenance") or {})
        row_index = raw.get("row_index")

        pubnum = _opt_str(notice.get("publication-number")) or _digest_of(notice)[:24]
        subject = f"procurement_notice:{ctx.source.id}:{pubnum}"
        source_uri = str(prov.get("source_uri") or "")
        retrieved_date = (str(prov.get("retrieved_at") or "")[:10]) or None

        def _evidence(field: str, locator: Mapping[str, Any]) -> dict[str, Any]:
            return {
                "source_url": source_uri,
                "retrieved_date": retrieved_date,
                "extraction_method": "json_text",
                "field": field,
                "locator": locator,
                "record_row": row_index,
                "slice": prov.get("slice"),
                "query_kind": prov.get("query_kind"),
                "ted_keyword": prov.get("ted_keyword"),
                "cpv_code": prov.get("cpv_code"),
                "capture_digest": prov.get("capture_digest"),
            }

        # --- the verbatim field surface --------------------------------------
        buyer = _ted_first_text(notice.get("buyer-name"))
        buyer_country = _ted_first_seq(notice.get("buyer-country")) or _ted_first_seq(
            notice.get("organisation-country-buyer")
        )
        alpha2 = ted_eu_country_map().get(buyer_country) if buyer_country else None
        title = _ted_first_text(notice.get("notice-title"))
        description = _ted_first_text(notice.get("description-proc"))
        winner = _ted_first_text(notice.get("winner-name"))
        notice_type = _opt_str(notice.get("notice-type"))
        pubdate_raw = _opt_str(notice.get("publication-date"))
        pubdate = pubdate_raw[:10] if pubdate_raw else None
        total = notice.get("total-value")
        currency = _ted_first_seq(notice.get("total-value-cur"))
        deadline = _ted_first_seq(notice.get("deadline-receipt-tender-date-lot"))
        # Verbatim place-of-performance literals: NUTS codes + city names as the
        # notice states them, deduped preserving order.
        place_literals: list[tuple[str, str]] = []
        for field_name in (
            "place-of-performance",
            "place-of-performance-subdiv-lot",
            "place-of-performance-city-lot",
            "place-of-performance-country-lot",
        ):
            values = notice.get(field_name)
            if isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
                place_literals.extend((field_name, str(v)) for v in values if v)
            elif values:
                place_literals.append((field_name, str(values)))

        rows: list[dict[str, Any]] = [
            _stamp(
                {
                    "record_kind": "procurement_notice",
                    "subject_id": subject,
                    "predicate_id": assert_predicate_allowed("procurement_notice"),
                    "external_id": pubnum,
                    "raw_value": pubnum,
                    "notice_type": notice_type,
                    "award_kind": "eu_notice",
                    "provenance": prov,
                    "row_index": row_index,
                    "raw": dict(notice),
                },
                source_id=ctx.source.id,
            )
        ]

        field_claims: list[tuple[str, str, str, Any]] = [
            ("external_id", "publication-number", pubnum, pubnum),
        ]
        if notice_type is not None:
            field_claims.append(("notice_type", "notice-type", notice_type, notice_type))
        if title is not None:
            field_claims.append(("title", "notice-title", title, title))
        if buyer is not None:
            field_claims.append(("buyer", "buyer-name", buyer, buyer))
        if winner is not None:
            # The winner-name literal IS the awarded seller — the §11.11
            # `seller` predicate, emitted only on award notices where TED
            # states a winner (P26.10 vendor precedent).
            field_claims.append(("seller", "winner-name", winner, winner))
        if pubdate_raw is not None:
            field_claims.append(("posted_date", "publication-date", pubdate_raw, pubdate))
        if deadline is not None:
            field_claims.append(
                (
                    "response_deadline",
                    "deadline-receipt-tender-date-lot",
                    deadline,
                    deadline[:10],
                )
            )
        if total is not None:
            raw_amount = f"{total} {currency}" if currency else str(total)
            field_claims.append(("amount", "total-value", raw_amount, raw_amount))
        if description is not None:
            field_claims.append(("description", "description-proc", description, description))

        for predicate, field_name, raw_literal, value in field_claims:
            # Part VIII guard: a literal carrying a forbidden token is
            # suppressed at the claim surface (the capture keeps the bytes).
            raw_out = _raw_value_of(raw_literal)
            suppressed = content_guard_token(raw_out) is not None
            row: dict[str, Any] = {
                "record_kind": "claim",
                "subject_id": subject,
                "predicate_id": assert_predicate_allowed(predicate),
                "raw_value": "[suppressed: part-VIII token]" if suppressed else raw_out,
                "value": None if suppressed else value,
                "observed_at": retrieved_date,
                "evidence": _evidence(field_name, Locator.row(int(row_index or 0)).to_row()),
            }
            if suppressed:
                row["part_viii_suppressed"] = True
            if predicate == "buyer":
                row["candidate_identifier"] = org_candidate(str(value))
            if predicate == "seller":
                row["candidate_identifier"] = org_candidate(
                    str(value), scheme="procurement.org_name"
                )
            rows.append(_stamp(row, source_id=ctx.source.id))

        # classification-cpv — the verbatim CPV codes ARE the notice's product
        # classification (the §11.11 `products` surface); one claim per code,
        # deduped, verbatim literal.
        seen_cpvs: set[str] = set()
        for _, cpv in _ted_i18n_values(notice.get("classification-cpv")):
            code = str(cpv).strip()
            if not code or code in seen_cpvs or content_guard_token(code):
                continue
            seen_cpvs.add(code)
            rows.append(
                _stamp(
                    {
                        "record_kind": "claim",
                        "subject_id": subject,
                        "predicate_id": assert_predicate_allowed("products"),
                        "raw_value": code,
                        "value": code,
                        "observed_at": retrieved_date,
                        "evidence": _evidence(
                            "classification-cpv",
                            Locator.row(int(row_index or 0)).to_row(),
                        ),
                    },
                    source_id=ctx.source.id,
                )
            )

        # Jurisdiction claim — the verbatim alpha-3 is raw_value; the reviewed
        # country map supplies the normalized alpha-2 identifier (P26.9
        # iso.3166_1_alpha2 scheme). An unmapped alpha-3 keeps its verbatim
        # literal as the value and emits NO normalized identifier — a code is
        # never fabricated.
        if buyer_country:
            row = {
                "record_kind": "claim",
                "subject_id": subject,
                "predicate_id": assert_predicate_allowed("country"),
                "raw_value": buyer_country,
                "value": alpha2 or buyer_country,
                "observed_at": retrieved_date,
                "evidence": _evidence("buyer-country", Locator.row(int(row_index or 0)).to_row()),
            }
            if alpha2:
                row["candidate_identifier"] = {
                    "scheme": "iso.3166_1_alpha2",
                    "value": alpha2,
                }
            rows.append(_stamp(row, source_id=ctx.source.id))

        # Verbatim place-of-performance literals (NUTS codes, city names) —
        # deduped; recorded as stated, never emitted as ISO 3166-2 identifiers.
        seen_places: set[tuple[str, str]] = set()
        for field_name, literal in place_literals:
            if (field_name, literal) in seen_places or content_guard_token(literal):
                continue
            seen_places.add((field_name, literal))
            rows.append(
                _stamp(
                    {
                        "record_kind": "claim",
                        "subject_id": subject,
                        "predicate_id": assert_predicate_allowed("place_of_performance"),
                        "raw_value": literal,
                        "value": literal,
                        "observed_at": retrieved_date,
                        "evidence": _evidence(
                            field_name, Locator.row(int(row_index or 0)).to_row()
                        ),
                    },
                    source_id=ctx.source.id,
                )
            )

        # --- matched keywords: verbatim literals inside the notice text -----
        # Scan every i18n value of the notice's text fields; a match emits
        # `matched_keyword` with the verbatim slice as raw_value and a
        # byte-range locator into the named field's text. The slice's query
        # rides as provenance regardless — a query term not found verbatim in
        # the notice is NEVER emitted as a fact claim.
        matched: list[dict[str, Any]] = []
        for field_name in ("notice-title", "description-proc"):
            for lang, text in _ted_i18n_values(notice.get(field_name)):
                for match in scan_ted_content(text):
                    matched.append({**match, "field": f"{field_name}.{lang}"})
        seen_terms: set[tuple[str, str]] = set()
        for match in matched:
            key = (str(match["term_id"]), str(match["field"]))
            if key in seen_terms:
                continue
            seen_terms.add(key)
            literal = str(match["literal"])
            suppressed = content_guard_token(literal) is not None
            rows.append(
                _stamp(
                    {
                        "record_kind": "claim",
                        "subject_id": subject,
                        "predicate_id": assert_predicate_allowed("matched_keyword"),
                        "value": match["term_id"],
                        "raw_value": ("[suppressed: part-VIII token]" if suppressed else literal),
                        "term_label": match["term_label"],
                        "term_kind": match["term_kind"],
                        "observed_at": retrieved_date,
                        "evidence": _evidence(
                            str(match["field"]),
                            Locator.byte_range(int(match["start"]), int(match["end"])).to_row(),
                        ),
                        **({"part_viii_suppressed": True} if suppressed else {}),
                    },
                    source_id=ctx.source.id,
                )
            )

        # --- lifecycle: the notice-type IS the lifecycle signal, verbatim ----
        # cn-* = contract notice (a call for tenders → rfp_issued); can-* =
        # contract-award notice (→ awarded); anything else asserts no
        # transition (a TED type outside the reviewed map says nothing).
        lifecycle_state = (
            "awarded"
            if notice_type and notice_type.startswith("can")
            else ("rfp_issued" if notice_type and notice_type.startswith("cn") else None)
        )
        if lifecycle_state:
            rows.append(
                _stamp(
                    {
                        "record_kind": "claim",
                        "subject_id": subject,
                        "predicate_id": assert_predicate_allowed("lifecycle_transition"),
                        "raw_value": str(notice_type),
                        "value": {"state": lifecycle_state, "date": pubdate},
                        "observed_at": retrieved_date,
                        "evidence": _evidence(
                            "notice-type", Locator.row(int(row_index or 0)).to_row()
                        ),
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


# --- procurement-portal helpers (P26.10 / SOURCES.9) ---------------------------


def _portal_target_for(ctx: RunContext, uri: str) -> Mapping[str, Any] | None:
    """The portal target (index OR resolved document) a capture fetched (P26.10).

    Resolved continuation targets first, then the run's configured targets,
    then the tenant registry row whose generated index URL the capture's
    ``source_uri`` is exactly.
    """
    target = ctx.resolved_targets.get(uri)
    if target is not None and target.get("kind") in ("portal_index", "portal_document"):
        return target
    registry_target = portal_target_for_uri(uri)
    for candidate in ctx.parameters.get("targets", []):
        if str(candidate.get("url")) == uri and candidate.get("kind") in (
            "portal_index",
            "portal_document",
        ):
            # A configured target wins its own fields but inherits the registry
            # row's tenant context (platform, field aliases, bounds) — a bare
            # fixture/live target still parses under the reviewed contract.
            return {**(dict(registry_target) if registry_target else {}), **dict(candidate)}
    return registry_target


def _portal_index_target_for(ctx: RunContext, uri: str) -> Mapping[str, Any] | None:
    """The ``portal_index`` target row a capture fetched (P26.10) — indexes only."""
    target = _portal_target_for(ctx, uri)
    if target is not None and target.get("kind") == "portal_index":
        return target
    return None


def _portal_item_id(item: Mapping[str, Any]) -> str:
    """A portal item's external id — solicitation number, detail-id, or digest."""
    return (
        _first_nonempty(item, ("sol_num", "id", "external_id", "request_id"))
        or _opt_str(str(item.get("detail_url") or "").rstrip("/").rsplit("/", 1)[-1].split("?")[0])
        or _digest_of(item)[:24]
    )


def _portal_external_id(item: Mapping[str, Any], tenant: Mapping[str, Any]) -> str:
    """The notice's external id via the tenant's reviewed ``id_fields`` aliases."""
    for key in tenant.get("id_fields", ()):
        value = _opt_str(item.get(str(key)))
        if value:
            return value
    return _portal_item_id(item)


def _portal_title(item: Mapping[str, Any], tenant: Mapping[str, Any]) -> str | None:
    """The item's title — BidNet ``title`` or the tenant's first title-field alias."""
    if _opt_str(item.get("title")):
        return _opt_str(item.get("title"))
    return _first_nonempty(item, (str(f) for f in tenant.get("title_fields", ())))


def _portal_posted_date(item: Mapping[str, Any], tenant: Mapping[str, Any]) -> str | None:
    """The record's published/posted date — verbatim, never re-formatted (§3.1)."""
    return _first_nonempty(
        item, ("published", str(tenant.get("date_field") or ""), "start_date", "posted_date")
    )


def _portal_notice_type(
    item: Mapping[str, Any], tenant: Mapping[str, Any], index_kind: str | None
) -> str | None:
    """The record's notice type, verbatim: a BidNet index kind or the dataset's own type field."""
    own = _first_nonempty(item, (str(tenant.get("notice_type_field") or ""),))
    if own:
        return own
    if index_kind and index_kind != "rows":
        return index_kind  # the verbatim index window the record surfaced under
    # A register row without its own type field asserts no notice_type — the
    # `contracted` lifecycle transition already records what the register is.
    return None


def _portal_lifecycle_state(
    item: Mapping[str, Any],
    tenant: Mapping[str, Any],
    platform: str,
    index_kind: str | None,
) -> str | None:
    """The reviewed lifecycle state the record's window/type maps to (§13.4).

    Maps through the platform's ``notice_map``: a BidNet ``open`` item is
    ``rfp_issued`` and an ``awarded`` item is ``awarded`` (``closed`` asserts no
    transition — closure alone is not a vocabulary state, §3.1); a Socrata
    register row maps its own notice-type value (normalized) or falls back to
    ``default`` = ``contracted`` — a row in a contract register IS the city's
    recorded contract.
    """
    notice_map = platform_endpoints().get(platform, {}).get("notice_map", {})
    if platform == "bidnet":
        return _opt_str(notice_map.get(str(index_kind or "")))
    if platform == "socrata":
        type_field = str(tenant.get("notice_type_field") or "")
        own = _first_nonempty(item, (type_field,)) if type_field else None
        if own:
            # A register carrying its own notice type maps only through the
            # reviewed vocabulary — an unmapped type (a hearing, a comment
            # period, an intent-to-award) asserts NO transition (§3.1); it is
            # not a contracted record just because it sits in the register.
            return _opt_str(notice_map.get(own.lower().replace(" ", "_")))
        # No type field reviewed on this dataset: every row in a contract
        # register IS the city's recorded contract → the default state.
        return _opt_str(notice_map.get("default"))
    return None


def _mdy_date_key(value: Any) -> str:
    """An ISO sort key for a BidNet ``MM/DD/YYYY`` date (canonical ordering).

    BidNet storefronts render dates ``05/04/2026`` — a string sort is NOT the
    chronological order, so the bounded window orders on the parsed date.
    Unparseable dates sort last (empty key under a descending order).
    """
    text = _opt_str(value)
    if not text:
        return ""
    for fmt, n in (("%m/%d/%Y", 10), ("%Y-%m-%d", 10), ("%Y-%m-%dT%H:%M:%S", 19)):
        try:
            return datetime.strptime(text[:n], fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def _select_portal_document_items(
    items: Sequence[Mapping[str, Any]],
    index_target: Mapping[str, Any],
    cfg: Mapping[str, Any],
    per_tenant: int,
) -> list[tuple[Mapping[str, Any], int]]:
    """The bounded ``(item, tier)`` selection for one portal index (P26.10).

    Mirrors ``_select_document_items``: tier-0 = items whose title matches the
    reviewed agenda_content_vocab, then canonical order — the reviewed
    ``doc_order_fields`` date (most recent first, BidNet ``MM/DD/YYYY`` parsed)
    with the item id as tie-break — never the server's return order. Given the
    same item set the selection is identical; re-runs dedupe.
    """
    if per_tenant <= 0:
        return []
    order_fields = [str(f) for f in (cfg.get("doc_order_fields") or ())]

    def _date_key(item: Mapping[str, Any]) -> str:
        for order_field in order_fields:
            key = _mdy_date_key(item.get(order_field))
            if key:
                return key
        return ""

    ordered = sorted(items, key=_portal_item_id)
    ordered = sorted(ordered, key=_date_key, reverse=True)

    def _relevant(item: Mapping[str, Any]) -> bool:
        title = _opt_str(item.get("title"))
        return bool(title and scan_agenda_content(title))

    scored = [(_relevant(item), pos, item) for pos, item in enumerate(ordered)]
    scored.sort(key=lambda entry: (not entry[0], entry[1]))
    return [(item, 0 if relevant else 1) for relevant, _, item in scored[:per_tenant]]


class _BidnetIndexParser(HTMLParser):
    """The BidNet Direct storefront index markup contract (P26.10).

    Verified markup (2026-09-18): each item is a ``<tr class="mets-table-row">``
    carrying ``div.sol-num`` (the solicitation number), ``a.solicitation-link``
    (title + detail-page href), ``span.sol-publication-date`` and
    ``span.sol-closing-date`` (each ``> span.date-value``), and
    ``span.sol-region-item``. Fields associate by position inside the row —
    the parser is a small state machine over the stdlib HTMLParser, never a
    regex over markup.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.items: list[dict[str, Any]] = []
        self.has_list_container = False
        self._row: dict[str, Any] | None = None
        self._field: str | None = None
        self._buf: list[str] = []
        self._date_ctx: str | None = None  # "pub" | "close"

    @staticmethod
    def _classes(attrs: list[tuple[str, str | None]]) -> set[str]:
        return set((dict(attrs).get("class") or "").split())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        classes = self._classes(attrs)
        if attr.get("id") == "solicitationList":
            self.has_list_container = True
        if tag == "tr" and "mets-table-row" in classes:
            self._row = {
                "sol_num": None,
                "title": None,
                "detail_url": None,
                "published": None,
                "closing": None,
                "region": None,
            }
            self._date_ctx = None
            return
        if self._row is None:
            return
        if "sol-num" in classes:
            self._field, self._buf = "sol_num", []
        elif "sol-publication-date" in classes:
            self._date_ctx = "pub"
        elif "sol-closing-date" in classes:
            self._date_ctx = "close"
        elif "date-value" in classes and self._date_ctx in ("pub", "close"):
            self._field, self._buf = ("published" if self._date_ctx == "pub" else "closing"), []
        elif "sol-region-item" in classes:
            self._field, self._buf = "region", []
        if tag == "a" and "solicitation-link" in classes:
            self._field, self._buf = "title", []
            href = attr.get("href")
            if href:
                self._row["detail_url"] = urljoin("https://www.bidnetdirect.com", href)

    def handle_data(self, data: str) -> None:
        if self._field in ("sol_num", "title", "published", "closing", "region"):
            self._buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "tr" and self._row is not None:
            self.items.append(self._row)
            self._row = None
            self._field = None
            self._date_ctx = None
            return
        if self._row is None or tag not in ("div", "span", "a"):
            return
        if self._field is None:
            return
        text = " ".join("".join(self._buf).split()) or None
        if self._field == "sol_num":
            self._row["sol_num"] = self._row["sol_num"] or text
        elif self._field == "title" and tag == "a":
            self._row["title"] = text
        elif self._field == "published":
            self._row["published"] = self._row["published"] or text
        elif self._field == "closing":
            self._row["closing"] = self._row["closing"] or text
        elif self._field == "region":
            self._row["region"] = self._row["region"] or text
        self._field = None
        self._buf = []


def _bidnet_index_items(data: bytes, *, source_id: str, source_uri: str) -> list[dict[str, Any]]:
    """The solicitation items a captured BidNet storefront index carries (P26.10).

    Fail-closed on the reviewed markup contract: a page with neither a
    ``solicitation-link`` item nor the ``id="solicitationList"`` list container
    is :class:`ContentDrift` — the markup changed; it is never read as a
    silent empty index. A container-present page with zero rows is an honest
    ``empty`` outcome. Items keep only the captured fields — sol_num, title,
    detail_url (the item's own link, never constructed), published, closing,
    region — no inference.
    """
    parser = _BidnetIndexParser()
    raw_text = utf8_text(data)
    try:
        parser.feed(raw_text)
    except Exception:
        pass  # HTMLParser is forgiving; a truncated page yields partial rows
    items = [item for item in parser.items if item.get("detail_url") or item.get("title")]
    if not items and not parser.has_list_container:
        raise ContentDrift(
            source_id,
            f"portal index {source_uri} carries neither a solicitation-link "
            "item nor the solicitationList container — the bidnet index markup "
            "contract changed, this is not an empty index",
            details=raw_text[:200],
        )
    return items


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
