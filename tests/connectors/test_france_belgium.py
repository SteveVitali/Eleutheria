# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The France/Belgium (Technopolice) connectors (§23.5, §23.6, §11.14, §13.8, P18.2).

Covers the deterministic acceptance criteria: the non-US records-request vocabulary
is used, including no_equivalent_available and never foia_request (SIG-ONTO-068);
authorization by published prefectural order maps onto LegalInstrument
(instrument_type=prefectoral_order, §11.14); national open-data procurement maps onto
Contract, with a framework agreement becoming a cooperative_piggyback that MUST set
parent_cooperative_contract (SIG-ONTO-032); plus the predicate allowlist
(SIG-INGEST-033), candidate-identifier-only party keying (SIG-INGEST-034), and the
vocab↔ontology lock-step (drift is a failed test).
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping
from typing import Any

import pytest
from connectors.net import PoliteFetcher, RobotsResult
from connectors.registry import get
from connectors.stages import (
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
    registered_connectors,
)
from evidence.ingest_run import IngestRun
from support import load_schemaview

from connectors import france_belgium as fb

_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"


# --- local fixtures -----------------------------------------------------------


def _ingest_run() -> IngestRun:
    return IngestRun(
        connector_name="france_belgium",
        connector_version="1.0.0",
        code_commit="deadbeef",
        ruleset_version="r1",
        vocab_version="v1",
        input_digests=(),
    )


def _ctx(source_key: str = "prefectural_orders", **kwargs: Any) -> RunContext:
    """A RunContext against a permitted France/Belgium source (loader gate open)."""
    source = dataclasses.replace(get(fb.source_ids()[source_key]), ingestion_permitted=True)
    return RunContext(
        source=source,
        run=_ingest_run(),
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        **kwargs,
    )


class _SequenceTransport:
    """A transport that returns queued responses per URL — no real network."""

    def __init__(self, responses: dict[str, list[tuple[int, bytes, str]]]) -> None:
        self._responses = {k: list(v) for k, v in responses.items()}
        self.request_log: list[str] = []

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ROBOTS_ALLOW_ALL)

    def request(
        self, url: str, *, user_agent: str, headers: Mapping[str, str] | None = None
    ) -> FetchResult:
        self.request_log.append(url)
        status, body, media = self._responses[url].pop(0)
        return FetchResult(url=url, status=status, body=body, media_type=media)


def _fetcher(transport: _SequenceTransport) -> PoliteFetcher:
    return PoliteFetcher(
        connector_name="france_belgium", connector_version="1.0.0", transport=transport
    )


def _raa_arrete() -> dict[str, Any]:
    """A representative arrêté préfectoral record parsed from an RAA gazette (F9.18)."""
    return {
        "external_id": "arrete-01-2026-0451",
        "prefecture": "Préfecture de l'Ain",
        "departement": "01",
        "effective_from": "2026-02-01",
        "operator": "Commune de Gex",
        "constrains_technology": ["fixed_cctv"],
    }


def _decp_marche(**overrides: Any) -> dict[str, Any]:
    """A DECP record in the verbatim structure of F9.16."""
    base: dict[str, Any] = {
        "id": "2025kazvs0000000",
        "acheteur": {"id": "20009020700016"},
        "nature": "Marché",
        "objet": "Fourniture et installation d'un système de vidéoprotection",
        "codeCPV": "35125300",
        "procedure": "Appel d'offres ouvert",
        "dureeMois": 12,
        "dateNotification": "2025-04-01",
        "montant": 50754,
        "titulaires": [{"titulaire": {"typeIdentifiant": "SIRET", "id": "31483054800140"}}],
    }
    base.update(overrides)
    return base


# --- AC: authorization by prefectural order maps onto LegalInstrument (§11.14) ---


def test_prefectoral_order_maps_onto_legal_instrument_prefectoral_order() -> None:
    # AC2: a published arrêté préfectoral parses into a LegalInstrument whose
    # instrument_type is in the prefectoral_order family — the abstract parent the
    # French national child fr.arrete_prefectoral is_a (SIG-ONTO-068, §11.14).
    instrument = fb.prefectoral_order_from_raa(_raa_arrete(), source_id="raa_prefectures")
    assert instrument.instrument_type == "fr.arrete_prefectoral"
    assert instrument.is_prefectoral_order
    assert instrument.abstract_instrument_type == "prefectoral_order"
    # Five-year renewable validity is derived from the effective date (CSI L252).
    assert instrument.sunset_date == "2031-02-01"
    assert instrument.raw["sunset_date_derived"] is True


def test_prefectoral_order_entity_row_records_the_abstract_parent() -> None:
    ctx = _ctx("prefectural_orders")
    rows = fb.FranceBelgiumRecordsConnector().normalize(
        ctx, [{"record_kind": "prefectoral_order", "raw": _raa_arrete()}]
    )
    entity = next(r for r in rows if r.get("record_kind") == "legal_instrument")
    assert entity["instrument_type"] == "fr.arrete_prefectoral"
    assert entity["abstract_instrument_type"] == "prefectoral_order"
    # enacting_body / jurisdiction are candidate identifiers, never resolved (034).
    jurisdiction_rows = [r for r in rows if r.get("predicate_id") == "jurisdiction"]
    assert jurisdiction_rows[0]["candidate_identifier"] == {"scheme": "fr.insee", "value": "01"}


def test_legal_instrument_rejects_an_out_of_vocabulary_type() -> None:
    with pytest.raises(fb.InvalidLegalInstrument):
        fb.LegalInstrument(
            external_id="x", source_id="raa_prefectures", instrument_type="not_a_real_type"
        )


def test_belgian_loi_cameras_is_a_national_instrument_under_a_shared_parent() -> None:
    # AC: Belgium's governing instrument is a be.* national child, not a widened US
    # enum. It is a statute-family instrument (loi caméras, 21 March 2007).
    instrument = fb.LegalInstrument(
        external_id="loi-cameras-2007",
        source_id="declarationcamera_be",
        instrument_type="be.loi_cameras",
        jurisdiction="BE",
    )
    assert instrument.instrument_type == "be.loi_cameras"
    assert not instrument.is_prefectoral_order


# --- AC1: the non-US records-request vocabulary (fr.cada / no_equivalent_available) ---


def test_records_connector_emits_fr_cada_not_foia() -> None:
    # AC1: France uses the internationalized fr.cada regime; no row is foia_request
    # or a us.* records term (SIG-ONTO-068, §13.8).
    ctx = _ctx("records_fr")
    rows = fb.FranceBelgiumRecordsConnector().normalize(
        ctx,
        [
            {
                "record_kind": "records_request",
                "raw": {"jurisdiction": "FR", "subject": "madada:req/42"},
            }
        ],
    )
    acq = next(r for r in rows if r.get("predicate_id") == "acquisition_method")
    assert acq["value"] == "fr.cada"
    values = {r.get("value") for r in rows}
    assert "foia_request" not in values
    assert not any(str(v).startswith("us.") for v in values if isinstance(v, str))


def test_records_connector_emits_no_equivalent_available_for_belgium() -> None:
    # AC1: Belgium's national camera register is behind an eID wall and not public;
    # its records-request regime is the country-neutral no_equivalent_available
    # coverage fact (F9.31), a known-complete-unknown — never discarded.
    ctx = _ctx("records_be")
    rows = fb.FranceBelgiumRecordsConnector().normalize(
        ctx,
        [
            {
                "record_kind": "records_request",
                "raw": {
                    "jurisdiction": "BE",
                    "subject": "jurisdiction:BE",
                    "known_complete_unknown": True,
                },
            }
        ],
    )
    acq = next(r for r in rows if r.get("predicate_id") == "acquisition_method")
    assert acq["value"] == "no_equivalent_available"
    assert acq["known_complete_unknown"] is True


@pytest.mark.parametrize("method", ["foia_request", "us.foia", "us.state_public_records"])
def test_a_us_records_method_is_refused(method: str) -> None:
    # The "not foia_request" guard is real at the seam (§5.3, SIG-ONTO-068).
    with pytest.raises(fb.USRecordsMethodError):
        fb.assert_not_us_records_method(method)


def test_records_request_method_lookup_is_defined_for_fr_and_be() -> None:
    assert fb.records_request_method_for("FR") == "fr.cada"
    assert fb.records_request_method_for("BE") == "no_equivalent_available"


# --- AC2: national open-data procurement maps onto Contract (§23.6, SIG-ONTO-032) ---


def test_decp_record_maps_onto_contract() -> None:
    contract = fb.contract_from_decp(_decp_marche(), source_id="decp_fr")
    assert contract.buyer == "20009020700016"  # acheteur.id (SIRET)
    assert contract.seller == "31483054800140"  # titulaires[].titulaire.id
    assert contract.amount == "50754"
    assert contract.currency == "EUR"
    assert contract.signed_date == "2025-04-01"
    assert contract.acquisition_channel == "competitive_rfp"  # Appel d'offres ouvert
    # end_date is derivable from dureeMois, not stored (F9.16).
    assert contract.end_date is None


def test_decp_framework_agreement_is_a_piggyback_that_links_its_master() -> None:
    # SIG-ONTO-032: a marché riding an accord-cadre is a piggyback on a master award
    # and MUST set parent_cooperative_contract — the same invariant the US
    # cooperative-vehicle case turns on, reached with no US vocabulary.
    contract = fb.contract_from_decp(_decp_marche(idAccordCadre="AC-2024-035"), source_id="decp_fr")
    assert contract.acquisition_channel == "cooperative_piggyback"
    assert contract.parent_cooperative_contract == "AC-2024-035"
    assert contract.is_cooperative_piggyback


def test_decp_contract_claim_rows_pass_the_procurement_allowlist() -> None:
    ctx = _ctx("procurement")
    rows = fb.FranceBelgiumProcurementConnector().normalize(
        ctx, [{"record_kind": "contract", "raw": _decp_marche()}]
    )
    entity = next(r for r in rows if r.get("record_kind") == "contract")
    assert entity["subject_id"] == "contract:decp_fr:2025kazvs0000000"
    # The DECP connector reuses the country-neutral Contract shape, so parties keep
    # the procurement connector's candidate-identifier scheme — still a candidate,
    # never a resolution (SIG-INGEST-034). The SIRET rides through as the value.
    buyer_rows = [r for r in rows if r.get("predicate_id") == "buyer"]
    assert buyer_rows[0]["candidate_identifier"]["value"] == "20009020700016"


@pytest.mark.parametrize(
    ("procedure", "expected"),
    [
        ("Appel d'offres ouvert", "competitive_rfp"),
        ("Marché négocié sans publicité ni mise en concurrence préalable", "sole_source"),
        ("Une procédure inconnue", "direct_award"),
        (None, "direct_award"),
    ],
)
def test_decp_procedure_maps_to_acquisition_channel(procedure: str | None, expected: str) -> None:
    assert fb.decp_acquisition_channel(procedure, has_framework=False) == expected


# --- SIG-INGEST-033: the records connector's predicate allowlist --------------


def test_records_predicate_allowlist_refuses_out_of_scope() -> None:
    # The records connector may not write a procurement Contract value or a device
    # count — refused at the ingest boundary (SIG-INGEST-033).
    for forbidden in ("contract", "device_count", "funding_instrument"):
        with pytest.raises(fb.PredicateNotAllowed):
            fb.assert_legal_predicate_allowed(forbidden)
    for allowed in ("legal_instrument", "instrument_type", "acquisition_method"):
        assert fb.assert_legal_predicate_allowed(allowed) == allowed


# --- vocab ↔ ontology lock-step (drift is a failed test) ----------------------


def test_legal_instrument_and_acquisition_vocab_match_the_ontology() -> None:
    sv = load_schemaview()
    legal = set(sv.get_enum("LegalInstrumentType").permissible_values)
    acq = set(sv.get_enum("AcquisitionMethod").permissible_values)
    assert fb.legal_instrument_types() == legal
    assert fb.acquisition_methods() == acq


def test_both_connectors_are_registered() -> None:
    names = set(registered_connectors())
    assert {"france_belgium_records", "france_belgium_procurement"} <= names


# --- end-to-end: the eight stages, no US-shaped code path ---------------------


def test_records_connector_runs_end_to_end_from_a_capture() -> None:
    url = "https://www.data.gouv.fr/raa/arretes.json"
    payload = {"prefectoral_orders": [_raa_arrete()]}
    transport = _SequenceTransport(
        {url: [(200, json.dumps(payload).encode("utf-8"), "application/json")]}
    )
    ctx = _ctx(
        "prefectural_orders", fetcher=_fetcher(transport), parameters={"targets": [{"url": url}]}
    )
    conn = fb.FranceBelgiumRecordsConnector()
    targets = conn.discover(ctx)
    assert targets == [{"url": url}]  # known lookups only, supplied on the run context
    fetched = conn.fetch(ctx, targets[0])
    capture = conn.capture(ctx, fetched)
    normalized = conn.normalize(ctx, conn.extract(ctx, conn.parse(ctx, capture)))
    loaded = conn.load(ctx, normalized)
    entity = next(r for r in loaded if r.get("record_kind") == "legal_instrument")
    assert entity["instrument_type"] == "fr.arrete_prefectoral"
    assert "claim_id" in entity and "sys_period" in entity  # L1 stamping (SIG-INGEST-003)


def test_records_extract_routes_by_wrapping_key_not_inner_fields() -> None:
    # A combined payload: the wrapping list key is authoritative, so a prefectural
    # order is never misread as a records-request context even if it names a place.
    ctx = _ctx("records_fr")
    conn = fb.FranceBelgiumRecordsConnector()
    payload = {
        "prefectoral_orders": [_raa_arrete()],
        "records_requests": [{"jurisdiction": "FR", "subject": "madada:req/7"}],
    }
    extracted = conn.extract(ctx, {"payload": payload})
    kinds = sorted(r["record_kind"] for r in extracted)
    assert kinds == ["prefectoral_order", "records_request"]
    rows = conn.normalize(ctx, extracted)
    assert any(r.get("record_kind") == "legal_instrument" for r in rows)
    assert any(r.get("predicate_id") == "acquisition_method" for r in rows)


def test_procurement_connector_runs_end_to_end_from_a_decp_payload() -> None:
    ctx = _ctx("procurement")
    url = "https://static.data.gouv.fr/decp/decp.json"
    payload = {"marches": {"marche": [_decp_marche(), _decp_marche(id="2025kazvs0000001")]}}
    transport = _SequenceTransport(
        {url: [(200, json.dumps(payload).encode("utf-8"), "application/json")]}
    )
    ctx = dataclasses.replace(
        ctx, fetcher=_fetcher(transport), parameters={"targets": [{"url": url}]}
    )
    conn = fb.FranceBelgiumProcurementConnector()
    fetched = conn.fetch(ctx, {"url": url})
    capture = conn.capture(ctx, fetched)
    normalized = conn.normalize(ctx, conn.extract(ctx, conn.parse(ctx, capture)))
    contracts = [r for r in normalized if r.get("record_kind") == "contract"]
    assert len(contracts) == 2
    assert {c["subject_id"] for c in contracts} == {
        "contract:decp_fr:2025kazvs0000000",
        "contract:decp_fr:2025kazvs0000001",
    }
