# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The France/Belgium (Technopolice) connectors — the first non-US adapter (§52 Phase 18, P18.2).

The France/Belgium evidence base **stress-tests** the international data model the
P18.1 adapter framework opened (§5.3): authorization is carried by **published
prefectural orders** rather than by contracts, and procurement by a **national
open-data dataset** rather than by thousands of municipal systems. Both must map
onto the existing entities — a :class:`LegalInstrument` and a
:class:`connectors.procurement.Contract` — or the failure to map is a §5.3 defect to
be found here, not in production. This module is the two connectors that make that
mapping concrete, and it exercises the framework with **no US-shaped assumption**:
it never reaches for a ``us.*`` term (the ``foia_request`` / ``us.foia`` / cooperative
US-vehicle vocabulary of the ``records``/``procurement`` connectors is refused).

Two source adapters on the P04.1 eight-stage framework (:mod:`connectors.stages`),
plus the runtime shapes they need:

* **The ``LegalInstrument`` runtime shape** (:class:`LegalInstrument`, §11.14): this
  ticket is its first consumer. A published **arrêté préfectoral** — the legally
  authoritative, dated, five-year-renewable authorization the US has no equivalent
  of (F9.18) — parses into a ``LegalInstrument`` whose ``instrument_type`` is in the
  ``prefectoral_order`` family (``fr.arrete_prefectoral is_a prefectoral_order``,
  SIG-ONTO-068). A US-shaped enum could not hold it; a national-namespace child under
  a shared abstract parent can.
* **The internationalized records-request vocabulary** (§13.8, SIG-ONTO-068): the
  ``france_belgium_records`` connector emits the ``AcquisitionMethod`` regime for the
  jurisdiction — ``fr.cada`` for France (Ma Dada / CADA), ``no_equivalent_available``
  for Belgium (whose national camera register sits behind a Belgian-eID wall and is
  not public — a *known-complete-unknown*, F9.31). It NEVER emits ``foia_request`` or
  a ``us.*`` records term (:func:`assert_not_us_records_method`).
* **National open-data procurement → ``Contract``** (§23.6, SIG-ONTO-032): the
  ``france_belgium_procurement`` connector maps a DECP (Données Essentielles de la
  Commande Publique) record 1:1 onto the country-neutral :class:`Contract` (F9.16).
  A marché riding an accord-cadre (framework agreement) is a piggyback and MUST set
  ``parent_cooperative_contract`` — the same SIG-ONTO-032 invariant the US
  cooperative-vehicle case turns on, reached here with no US vocabulary.

The layered parsing of a captured arrêté PDF is **not** done here: P07.1 owns the
parser. Rows are append-only and carry full provenance; the connectors emit
**candidate** identifiers for the parties and jurisdictions and never resolve
entities themselves (SIG-INGEST-034). The study of the already-executed
~12,000-camera OSM import — a precondition of any SIG-originated contribution at
scale (SIG-CONTRIB-016) — lives in :mod:`connectors.osm_import_study`.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import cache
from typing import Any

from evidence.digest import multihash

from ._data import load_table
from .procurement import Contract, LifecycleTransition
from .stages import CaptureRef, Connector, FetchResult, RunContext, register

# --- the versioned vocabulary (data, not code — §20, SIG-ENG-001) -------------


@cache
def vocab() -> dict[str, Any]:
    """The versioned `france_belgium` connector vocabulary (``data/france_belgium_vocab.toml``)."""
    return load_table("france_belgium_vocab")


def vocab_version() -> str:
    """The connector vocabulary version stamped onto every run (§20)."""
    return str(vocab()["vocab_version"])


def source_ids() -> Mapping[str, str]:
    """The registry source ids the connectors run against, by role key (§22.6 I)."""
    return dict(vocab()["sources"])


def legal_instrument_types() -> frozenset[str]:
    """The LegalInstrumentType vocabulary (§11.14), mirrored from the ontology enum."""
    return frozenset(vocab()["legal_instrument_types"])


def acquisition_methods() -> frozenset[str]:
    """The AcquisitionMethod vocabulary (§13.8), mirrored from the ontology enum."""
    return frozenset(vocab()["acquisition_methods"])


def prefectoral_order_family() -> frozenset[str]:
    """The prefectoral-order family: the abstract parent + its national children (§11.14)."""
    return frozenset(vocab()["prefectoral_order_family"])


def prefectoral_order_parent() -> str:
    """The shared abstract parent every prefectural order maps onto (``prefectoral_order``)."""
    return str(vocab()["prefectoral_order_parent"])


def forbidden_us_acquisition_methods() -> frozenset[str]:
    """The US records-request terms a non-US connector MUST NOT emit (§5.3, SIG-ONTO-068)."""
    return frozenset(vocab()["forbidden_us_acquisition_methods"])


def records_request_method_for(jurisdiction: str) -> str:
    """The internationalized records-request regime for a jurisdiction (§13.8).

    ``FR`` → ``fr.cada``; ``BE`` → ``no_equivalent_available`` (the national camera
    register is behind a Belgian-eID wall and not public, F9.31). Raises
    :class:`KeyError` for an unknown jurisdiction rather than guessing a regime.
    """
    return str(vocab()["records_request_methods"][jurisdiction])


# --- the internationalized records-request vocabulary (§13.8, SIG-ONTO-068) ---


class USRecordsMethodError(Exception):
    """Raised when the France/Belgium connector reaches for a US records-request term.

    The mechanical form of §5.3 / SIG-ONTO-068 for this connector: ``foia_request``
    is US-specific, and ``us.foia`` / ``us.state_public_records`` are the US children
    of the abstract ``records_request`` parent. A non-US connector emitting one of
    them is exactly the US-shaped assumption the international model prohibits.
    """


class InvalidAcquisitionMethod(Exception):
    """Raised when an acquisition method is not in the AcquisitionMethod vocabulary (§13.8)."""


def assert_not_us_records_method(method: str) -> str:
    """Return ``method`` unless it is a US records-request term, else raise (§5.3).

    Guards the "not ``foia_request``" acceptance criterion at the seam: the France
    (``fr.cada``) and Belgium (``no_equivalent_available``) regimes pass; the
    outline's ``foia_request`` and the ``us.*`` children are refused here.
    """
    if method in forbidden_us_acquisition_methods():
        raise USRecordsMethodError(
            f"the France/Belgium records connector may not emit {method!r}: it is a "
            "US-specific records-request term (§5.3, SIG-ONTO-068). France uses "
            "'fr.cada' and Belgium 'no_equivalent_available'."
        )
    return method


def assert_acquisition_method(method: str) -> str:
    """Return ``method`` if it is a valid, non-US AcquisitionMethod, else raise (§13.8)."""
    assert_not_us_records_method(method)
    if method not in acquisition_methods():
        raise InvalidAcquisitionMethod(
            f"acquisition method {method!r} is not in the AcquisitionMethod vocabulary "
            f"{sorted(acquisition_methods())} (§13.8)"
        )
    return method


def acquisition_method_claim(
    *,
    jurisdiction: str,
    subject_id: str,
    source_id: str,
    raw_value: str | None = None,
    known_complete_unknown: bool = False,
) -> dict[str, Any]:
    """Build one internationalized ``acquisition_method`` claim (§13.8, SIG-ONTO-068).

    The value is the jurisdiction's records-request regime — ``fr.cada`` or
    ``no_equivalent_available`` — validated to be a non-US AcquisitionMethod term.
    ``known_complete_unknown`` flags the Belgian case (F9.31): a complete
    authoritative register exists, is held by the police, and is not accessible — a
    state distinct from "no data" and from "no such data exists", which
    ``no_equivalent_available`` records rather than discards.
    """
    method = assert_acquisition_method(records_request_method_for(jurisdiction))
    return _stamp(
        {
            "record_kind": "claim",
            "subject_id": subject_id,
            "predicate_id": assert_legal_predicate_allowed("acquisition_method"),
            "value": method,
            "raw_value": raw_value if raw_value is not None else method,
            "jurisdiction": jurisdiction,
            "known_complete_unknown": known_complete_unknown,
        },
        source_id=source_id,
    )


# --- the predicate allowlist for the records connector (SIG-INGEST-033) -------


class PredicateNotAllowed(Exception):
    """A schema error: the connector tried to write outside its predicate allowlist."""


def legal_instrument_predicate_allowlist() -> frozenset[str]:
    """The predicates the records connector may write (§11.14, §13.8, SIG-INGEST-033)."""
    return frozenset(vocab()["legal_instrument_predicate_allowlist"])


def legal_instrument_forbidden_predicate_genres() -> tuple[str, ...]:
    """The write-set the records connector places out of scope (documented complement)."""
    return tuple(vocab()["legal_instrument_forbidden_predicate_genres"])


def assert_legal_predicate_allowed(predicate: str) -> str:
    """Return ``predicate`` if allowed, else raise :class:`PredicateNotAllowed`.

    The ``france_belgium_records`` connector may write **only** the §11.14
    ``LegalInstrument`` predicate surface plus the ``acquisition_method`` coverage
    fact: a procurement value, a device count, or a deployment claim is refused here,
    at the ingest boundary (SIG-INGEST-033, the ``D6`` filter at ingest).
    """
    if predicate not in legal_instrument_predicate_allowlist():
        raise PredicateNotAllowed(
            f"the france_belgium records connector may write only "
            f"{sorted(legal_instrument_predicate_allowlist())} (§11.14/§13.8, "
            f"SIG-INGEST-033); {predicate!r} is outside the allowlist — procurement, "
            "device, and deployment claims are refused."
        )
    return predicate


# --- candidate identifiers for the parties (SIG-INGEST-034) -------------------


def org_candidate(raw_org: str, *, scheme: str = "fr.org_name") -> dict[str, str]:
    """A **candidate** identifier for a France/Belgium organization — never a resolution.

    A numeric id (a French SIREN/SIRET) routes to a scheme-scoped path; a free-text
    name routes to a surrogate ``<ns>.org_name`` path the identity layer (§14.6)
    resolves (SIG-INGEST-034).
    """
    value = raw_org.strip()
    if value.isdigit():
        return {"scheme": "fr.siret", "value": value}
    return {"scheme": scheme, "value": value}


def jurisdiction_candidate(raw_code: str, *, scheme: str = "fr.insee") -> dict[str, str]:
    """A **candidate** identifier for a France/Belgium jurisdiction (SIG-INGEST-034)."""
    return {"scheme": scheme, "value": str(raw_code).strip()}


# --- the LegalInstrument runtime shape (§11.14) -------------------------------


class InvalidLegalInstrument(Exception):
    """Raised when a LegalInstrument violates the §11.14 vocabulary contract."""


@dataclass(frozen=True)
class LegalInstrument:
    """The runtime shape of a §11.14 ``LegalInstrument`` — this ticket is its first consumer.

    Gives the international requirement somewhere to put an arrêté préfectoral, a CNIL
    decision, or a Belgian loi caméras. ``instrument_type`` is validated against the
    frozen ``LegalInstrumentType`` vocabulary; an out-of-vocabulary value is a hard
    error rather than a silent coercion (SIG-ONTO). A published prefectural order maps
    onto an instrument in the ``prefectoral_order`` family (:attr:`is_prefectoral_order`).
    The connector emits **candidate** party/jurisdiction identifiers, never resolutions
    (SIG-INGEST-034).
    """

    external_id: str
    source_id: str
    instrument_type: str
    enacting_body: str | None = None
    jurisdiction: str | None = None
    citation: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    sunset_date: str | None = None
    constrains_technology: tuple[str, ...] = ()
    constrains_capability: tuple[str, ...] = ()
    requires_authorization_of: tuple[str, ...] = ()
    raw: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.external_id).strip():
            raise InvalidLegalInstrument("a LegalInstrument requires an external_id (§11.14)")
        if self.instrument_type not in legal_instrument_types():
            raise InvalidLegalInstrument(
                f"instrument_type {self.instrument_type!r} is not in the LegalInstrumentType "
                f"vocabulary {sorted(legal_instrument_types())} (§11.14)"
            )

    @property
    def subject_id(self) -> str:
        """The claim subject id for this instrument (source + external id scoped)."""
        return f"legal_instrument:{self.source_id}:{self.external_id}"

    @property
    def is_prefectoral_order(self) -> bool:
        """Whether this instrument is a prefectural order (abstract parent or a child)."""
        return self.instrument_type in prefectoral_order_family()

    @property
    def abstract_instrument_type(self) -> str:
        """The shared abstract instrument type (``prefectoral_order`` for the family).

        Maps the concrete national child (``fr.arrete_prefectoral``) up to the shared
        abstract parent, so a cross-country query can ask for every prefectural order
        regardless of national namespace (SIG-ONTO-068). AC2's "maps onto
        ``instrument_type=prefectoral_order``" is exactly this.
        """
        if self.is_prefectoral_order:
            return prefectoral_order_parent()
        return self.instrument_type

    def predicate_values(self) -> dict[str, Any]:
        """The §11.14 predicate → value map for the set predicates (allowlisted keys only)."""
        candidates: dict[str, Any] = {
            "instrument_type": self.instrument_type,
            "enacting_body": self.enacting_body,
            "jurisdiction": self.jurisdiction,
            "citation": self.citation,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "sunset_date": self.sunset_date,
            "external_id": self.external_id,
        }
        values = {k: v for k, v in candidates.items() if v is not None}
        if self.constrains_technology:
            values["constrains_technology"] = list(self.constrains_technology)
        if self.constrains_capability:
            values["constrains_capability"] = list(self.constrains_capability)
        if self.requires_authorization_of:
            values["requires_authorization_of"] = list(self.requires_authorization_of)
        return values

    def claim_rows(self) -> list[dict[str, Any]]:
        """The append-only claim rows for this instrument, confined to the allowlist (P2).

        One ``legal_instrument`` entity row (carrying the whole predicate surface for
        provenance) plus one row per set §11.14 predicate. Every predicate id passes
        :func:`assert_legal_predicate_allowed` (SIG-INGEST-033); ``raw_value`` is
        preserved beside every typed value (P2). ``enacting_body`` and ``jurisdiction``
        carry a **candidate** identifier, never a resolution (SIG-INGEST-034).
        """
        rows: list[dict[str, Any]] = [
            _stamp(
                {
                    "record_kind": "legal_instrument",
                    "subject_id": self.subject_id,
                    "predicate_id": assert_legal_predicate_allowed("legal_instrument"),
                    "external_id": self.external_id,
                    "raw_value": self.external_id,
                    "predicate_surface": self.predicate_values(),
                    "instrument_type": self.instrument_type,
                    "abstract_instrument_type": self.abstract_instrument_type,
                },
                source_id=self.source_id,
            )
        ]
        for predicate, value in self.predicate_values().items():
            row: dict[str, Any] = {
                "record_kind": "claim",
                "subject_id": self.subject_id,
                "predicate_id": assert_legal_predicate_allowed(predicate),
                "raw_value": _raw_value_of(value),
                "value": value,
            }
            if predicate == "enacting_body" and isinstance(value, str):
                row["candidate_identifier"] = org_candidate(value)
            elif predicate == "jurisdiction" and isinstance(value, str):
                row["candidate_identifier"] = jurisdiction_candidate(value)
            rows.append(_stamp(row, source_id=self.source_id))
        return rows


def prefectoral_order_from_raa(raw: Mapping[str, Any], *, source_id: str) -> LegalInstrument:
    """Build the arrêté préfectoral a RAA record parses into (§11.14, F9.18).

    A French prefectural authorization is granted for **five years and is renewable**
    (Code de la sécurité intérieure L252); when the arrêté carries an
    ``effective_from`` and no explicit expiry, the five-year ``sunset_date`` is
    derived and flagged as derived in ``raw`` so the §12 renewal-watch task can fire
    ("this authorization lapses in N years; is there a renewal?"). ``instrument_type``
    is ``fr.arrete_prefectoral`` — a national child of the abstract ``prefectoral_order``
    parent (SIG-ONTO-068), never a widened US enum.
    """
    v = vocab()
    effective_from = _opt_str(raw.get("effective_from") or raw.get("date"))
    sunset = _opt_str(raw.get("sunset_date") or raw.get("effective_to"))
    if sunset is None and effective_from is not None:
        sunset = _plus_years(effective_from, int(v["fr_prefectoral_order_validity_years"]))
    departement = _opt_str(raw.get("departement") or raw.get("commune") or raw.get("jurisdiction"))
    return LegalInstrument(
        external_id=str(raw.get("external_id") or raw.get("id") or raw.get("titre") or ""),
        source_id=source_id,
        instrument_type=str(v["fr_prefectoral_order_instrument_type"]),
        enacting_body=_opt_str(raw.get("enacting_body") or raw.get("prefecture")),
        jurisdiction=departement,
        citation=_opt_str(raw.get("citation")) or str(v["fr_prefectoral_order_citation"]),
        effective_from=effective_from,
        sunset_date=sunset,
        constrains_technology=tuple(str(t) for t in raw.get("constrains_technology", [])),
        requires_authorization_of=tuple(str(a) for a in raw.get("requires_authorization_of", [])),
        raw={**dict(raw), "sunset_date_derived": sunset is not None and not raw.get("sunset_date")},
    )


# --- national open-data procurement → Contract (§23.6, SIG-ONTO-032, F9.16) ---


def decp_procedure_channels() -> Mapping[str, str]:
    """The DECP ``procedure`` → AcquisitionChannel map (§11.11)."""
    return dict(vocab()["decp"]["procedure_channels"])


def decp_default_channel() -> str:
    """The AcquisitionChannel assumed when a DECP procedure maps to nothing specific."""
    return str(vocab()["decp_default_channel"])


def decp_framework_channel() -> str:
    """The channel a marché riding an accord-cadre carries (``cooperative_piggyback``)."""
    return str(vocab()["decp_framework_channel"])


def decp_currency() -> str:
    """The DECP currency (montant is in EUR)."""
    return str(vocab()["decp_currency"])


def decp_acquisition_channel(procedure: str | None, *, has_framework: bool) -> str:
    """The AcquisitionChannel for a DECP record (§11.11, SIG-ONTO-032).

    A marché with an ``idAccordCadre`` (framework agreement) is a piggyback on a
    master award and takes the framework channel regardless of ``procedure`` — the
    same shape as a US cooperative-vehicle piggyback, reached here through French
    open data with no US vocabulary. Otherwise the free-text French ``procedure``
    maps through :func:`decp_procedure_channels`, falling back to the default.
    """
    if has_framework:
        return decp_framework_channel()
    if procedure is None:
        return decp_default_channel()
    return decp_procedure_channels().get(procedure, decp_default_channel())


def contract_from_decp(raw: Mapping[str, Any], *, source_id: str) -> Contract:
    """Map one DECP record 1:1 onto the country-neutral §11.11 ``Contract`` (F9.16).

    Proves national open-data procurement maps onto ``Contract`` without loss (AC2):
    ``acheteur.id`` (SIRET) → buyer, ``titulaires[].titulaire.id`` → seller,
    ``montant`` → amount (EUR), ``dateNotification`` → signed/start date. ``end_date``
    is deliberately left unset — DECP gives ``dureeMois``, from which the end is
    **derivable, not stored** (F9.16). A marché carrying an ``idAccordCadre`` is a
    piggyback and MUST set ``parent_cooperative_contract`` (SIG-ONTO-032); the
    Contract's own ``__post_init__`` enforces that invariant.
    """
    acheteur = raw.get("acheteur") or {}
    buyer = _opt_str(acheteur.get("id") if isinstance(acheteur, Mapping) else acheteur)
    seller = _first_titulaire(raw.get("titulaires"))
    framework = _opt_str(raw.get("idAccordCadre"))
    procedure = _opt_str(raw.get("procedure"))
    channel = decp_acquisition_channel(procedure, has_framework=framework is not None)
    signed = _opt_str(raw.get("dateNotification"))
    products = tuple(p for p in (_opt_str(raw.get("objet")), _opt_str(raw.get("codeCPV"))) if p)
    lifecycle = (LifecycleTransition(state="contracted", date=signed),) if signed else ()
    return Contract(
        external_id=str(raw.get("id") or ""),
        source_id=source_id,
        buyer=buyer,
        seller=seller,
        amount=_opt_str(raw.get("montant")),
        currency=decp_currency() if raw.get("montant") is not None else None,
        signed_date=signed,
        start_date=signed,
        renewal_options=framework,
        products=products,
        acquisition_channel=channel,
        parent_cooperative_contract=framework if channel == decp_framework_channel() else None,
        lifecycle=lifecycle,
        raw=dict(raw),
    )


def _first_titulaire(titulaires: Any) -> str | None:
    """The first titulaire's SIRET/name from a DECP ``titulaires[]`` array (F9.16)."""
    if not isinstance(titulaires, Sequence) or isinstance(titulaires, (str, bytes)):
        return None
    for item in titulaires:
        holder = item.get("titulaire") if isinstance(item, Mapping) else None
        if isinstance(holder, Mapping):
            value = _opt_str(holder.get("id") or holder.get("denomination"))
            if value:
                return value
        elif isinstance(item, Mapping):
            value = _opt_str(item.get("id"))
            if value:
                return value
    return None


# --- the per-capture quality report (§23.1 universal rule) --------------------


@dataclass(frozen=True)
class CaptureQualityReport:
    """The quality report produced **per capture** (§23.1, phase-gate data quality)."""

    source_id: str
    capture_digest: str
    media_type: str
    byte_size: int
    capture_kind: str  # "prefectoral_order" | "records_request" | "contract"
    connector_name: str
    connector_version: str
    vocab_version: str
    legal_instrument_count: int = 0
    contract_count: int = 0
    acquisition_method_count: int = 0
    claim_count: int = 0

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
            "legal_instrument_count": self.legal_instrument_count,
            "contract_count": self.contract_count,
            "acquisition_method_count": self.acquisition_method_count,
            "claim_count": self.claim_count,
        }


# --- the records connector ----------------------------------------------------


@register
class FranceBelgiumRecordsConnector(Connector):
    """The `france_belgium_records` connector: prefectural orders + the CADA/no-regime vocabulary.

    Runs on the P04.1 eight-stage framework. ``discover``/``fetch`` acquire known
    targets through the shared politeness layer (SIG-INGEST-011); ``parse``/
    ``extract``/``normalize`` are pure functions of the capture that build
    :class:`LegalInstrument` entities from published arrêtés préfectoraux
    (``instrument_type`` in the ``prefectoral_order`` family) and emit the
    internationalized ``acquisition_method`` regime for the jurisdiction — ``fr.cada``
    for France, ``no_equivalent_available`` for Belgium — never ``foia_request``
    (SIG-ONTO-068). Every claim is confined to the predicate allowlist (SIG-INGEST-033);
    the connector emits candidate identifiers and never resolves entities (SIG-INGEST-034).
    """

    name = "france_belgium_records"
    version = "1.0.0"

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        """Enumerate fetch targets — known lookups supplied on the run context."""
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """Obtain bytes for one target through the shared politeness layer only (SIG-INGEST-011)."""
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Structure the captured bytes — a JSON payload of arrêtés / records-request contexts."""
        data = ctx.captures.get(capture.digest)
        return {"payload": json.loads(data), "capture": capture}

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """Raw records with their kind, preserving raw values (P2).

        The wrapping list key is authoritative — ``prefectoral_orders`` records are
        prefectural orders and ``records_requests`` records are records-request
        contexts, regardless of their inner fields. Only for a bare object/list is
        the kind inferred (an explicit ``record_kind``/``kind``, else a
        ``jurisdiction`` field marks a records-request context).
        """
        payload = parsed["payload"]
        out: list[Mapping[str, Any]] = []
        if isinstance(payload, Mapping) and (
            "prefectoral_orders" in payload or "records_requests" in payload
        ):
            for obj in payload.get("prefectoral_orders", []) or []:
                out.append({"record_kind": "prefectoral_order", "raw": dict(obj)})
            for obj in payload.get("records_requests", []) or []:
                out.append({"record_kind": "records_request", "raw": dict(obj)})
            return out
        for obj in _decp_or_list(payload, keys=()):
            kind = obj.get("record_kind") or obj.get("kind")
            if kind is None:
                kind = "records_request" if obj.get("jurisdiction") else "prefectoral_order"
            out.append({"record_kind": str(kind), "raw": dict(obj)})
        return out

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """Typed rows beside preserved raw values (P2), confined to the allowlist."""
        out: list[dict[str, Any]] = []
        for raw in raw_claims:
            if raw["record_kind"] == "records_request":
                out.extend(self._normalize_records_request(ctx, raw["raw"]))
            else:
                out.extend(self._normalize_prefectoral_order(ctx, raw["raw"]))
        return out

    def _normalize_prefectoral_order(
        self, ctx: RunContext, raw: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        instrument = prefectoral_order_from_raa(raw, source_id=ctx.source.id)
        rows: list[dict[str, Any]] = list(instrument.claim_rows())
        claim_count = sum(1 for r in rows if r.get("record_kind") == "claim")
        report = CaptureQualityReport(
            source_id=ctx.source.id,
            capture_digest=_digest_of(raw),
            media_type="application/json",
            byte_size=len(json.dumps(raw, sort_keys=True, default=str)),
            capture_kind="prefectoral_order",
            connector_name=self.name,
            connector_version=self.version,
            vocab_version=vocab_version(),
            legal_instrument_count=1,
            claim_count=claim_count,
        )
        rows.append(_stamp(report.to_row(), source_id=ctx.source.id))
        return rows

    def _normalize_records_request(
        self, ctx: RunContext, raw: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        jurisdiction = str(raw["jurisdiction"])
        subject_id = str(
            raw.get("subject_id") or raw.get("subject") or f"jurisdiction:{jurisdiction}"
        )
        row = acquisition_method_claim(
            jurisdiction=jurisdiction,
            subject_id=subject_id,
            source_id=ctx.source.id,
            raw_value=_opt_str(raw.get("raw_value")),
            known_complete_unknown=bool(raw.get("known_complete_unknown")),
        )
        report = CaptureQualityReport(
            source_id=ctx.source.id,
            capture_digest=_digest_of(raw),
            media_type="application/json",
            byte_size=len(json.dumps(raw, sort_keys=True, default=str)),
            capture_kind="records_request",
            connector_name=self.name,
            connector_version=self.version,
            vocab_version=vocab_version(),
            acquisition_method_count=1,
            claim_count=1,
        )
        return [row, _stamp(report.to_row(), source_id=ctx.source.id)]

    # link() inherited (identity): SIG-INGEST-034 — candidate identifiers only.

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Produce the L1 rows; the driver asserts them (live only)."""
        return load_claims_for_l1(linked)


# --- the procurement connector ------------------------------------------------


@register
class FranceBelgiumProcurementConnector(Connector):
    """The `france_belgium_procurement` connector: DECP national open-data → Contract (§23.6).

    Runs on the P04.1 eight-stage framework. ``parse``/``extract``/``normalize`` are
    pure functions of the capture that map each DECP marché onto the country-neutral
    :class:`Contract` (F9.16), setting ``parent_cooperative_contract`` on a marché
    riding an accord-cadre (SIG-ONTO-032). Every claim is confined to the Contract
    predicate allowlist (enforced by :class:`Contract`); the connector emits candidate
    identifiers and never resolves entities (SIG-INGEST-034).
    """

    name = "france_belgium_procurement"
    version = "1.0.0"

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Structure the captured DECP JSON payload."""
        data = ctx.captures.get(capture.digest)
        return {"payload": json.loads(data), "capture": capture}

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """Pull the DECP marché records, preserving raw values (P2)."""
        payload = parsed["payload"]
        return [{"record_kind": "contract", "raw": dict(obj)} for obj in _decp_marches(payload)]

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for raw in raw_claims:
            contract = contract_from_decp(raw["raw"], source_id=ctx.source.id)
            rows = list(contract.claim_rows())
            claim_count = sum(1 for r in rows if r.get("record_kind") == "claim")
            report = CaptureQualityReport(
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
            )
            out.extend(rows)
            out.append(_stamp(report.to_row(), source_id=ctx.source.id))
        return out

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return load_claims_for_l1(linked)


# --- module-private helpers ---------------------------------------------------


def _stamp(row: dict[str, Any], *, source_id: str) -> dict[str, Any]:
    """Stamp a row with its source id and the connector vocabulary version (§20)."""
    row.setdefault("source_id", source_id)
    row.setdefault("vocab_version", vocab_version())
    return row


def load_claims_for_l1(claims: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Add the generated ``claim_id`` + transaction time each L1 entity/claim row needs.

    Mirrors the framework's load contract: ``claim_id`` and ``sys_period`` are the two
    non-deterministic columns the reproducibility fingerprint excludes (SIG-INGEST-003).
    Entity, claim, and contract rows get an identity + transaction time; quality
    reports keep their own keys.
    """
    stamped_kinds = {"legal_instrument", "contract", "funding_instrument", "claim"}
    out: list[dict[str, Any]] = []
    for claim in claims:
        if claim.get("record_kind") in stamped_kinds:
            out.append(
                {
                    **claim,
                    "claim_id": _new_claim_id(),
                    "sys_period": f"[{datetime.now(UTC).isoformat()},)",
                }
            )
        else:
            out.append(dict(claim))
    return out


def _new_claim_id() -> str:
    from uuid import uuid4

    return str(uuid4())


def _decp_or_list(payload: Any, *, keys: Sequence[str]) -> list[Mapping[str, Any]]:
    """Flatten a payload into records: named-list keys, a ``results`` list, or a bare list/obj."""
    out: list[Mapping[str, Any]] = []
    if isinstance(payload, Mapping):
        matched = False
        for key in keys:
            value = payload.get(key)
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                out.extend(dict(o) for o in value)
                matched = True
        if matched:
            return out
        if isinstance(payload.get("results"), Sequence):
            return [dict(o) for o in payload["results"]]
        return [dict(payload)]
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        return [dict(o) for o in payload]
    return out


def _decp_marches(payload: Any) -> list[Mapping[str, Any]]:
    """The marché records from a DECP payload (``{"marches": {"marche": [...]}}``, F9.16)."""
    if isinstance(payload, Mapping) and "marches" in payload:
        marches = payload["marches"]
        if isinstance(marches, Mapping):
            marche = marches.get("marche", [])
            return [dict(o) for o in marche] if isinstance(marche, Sequence) else []
        if isinstance(marches, Sequence) and not isinstance(marches, (str, bytes)):
            return [dict(o) for o in marches]
    return _decp_or_list(payload, keys=("marche",))


def _raw_value_of(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return ";".join(str(v) for v in value)
    return str(value)


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _digest_of(payload: Any) -> str:
    return multihash(json.dumps(payload, sort_keys=True, default=str).encode("utf-8"))


def _plus_years(edtf_date: str, years: int) -> str:
    """Add ``years`` to an ISO/EDTF ``YYYY[-MM-DD]`` date, preserving month/day when present."""
    head = edtf_date.strip()[:10]
    parts = head.split("-")
    try:
        year = int(parts[0])
    except (ValueError, IndexError):
        return edtf_date
    new_year = year + years
    if len(parts) >= 3:
        return f"{new_year:04d}-{parts[1]}-{parts[2]}"
    if len(parts) == 2:
        return f"{new_year:04d}-{parts[1]}"
    return f"{new_year:04d}"


__all__ = [
    "CaptureQualityReport",
    "Contract",
    "FranceBelgiumProcurementConnector",
    "FranceBelgiumRecordsConnector",
    "InvalidAcquisitionMethod",
    "InvalidLegalInstrument",
    "LegalInstrument",
    "PredicateNotAllowed",
    "USRecordsMethodError",
    "acquisition_method_claim",
    "acquisition_methods",
    "assert_acquisition_method",
    "assert_legal_predicate_allowed",
    "assert_not_us_records_method",
    "contract_from_decp",
    "decp_acquisition_channel",
    "legal_instrument_predicate_allowlist",
    "legal_instrument_types",
    "load_claims_for_l1",
    "prefectoral_order_family",
    "prefectoral_order_from_raa",
    "records_request_method_for",
    "source_ids",
    "vocab_version",
]
