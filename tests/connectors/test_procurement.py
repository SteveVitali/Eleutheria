# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for the `procurement` connector (§23.6, §11.11, §11.12, P07.3).

Cover the four Phase-7 ACs sub-set to this ticket plus the cross-cutting
invariants: cooperative piggyback contracts set parent_cooperative_contract
(SIG-ONTO-032); federal sub-awards traced to a local deployment via federal_award_id
with FundingInstrument distinguishing funder from recipient (SIG-ONTO-033); the
agenda-platform tenant registry exists, is published, and the connector reads its
targets from it, retaining discovery negatives as coverage records
(SIG-METRIC-002a); the artifact_type additions (SIG-INGEST-047); the predicate
allowlist (SIG-INGEST-033); and candidate-identifier-only party keying
(SIG-INGEST-034).
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping
from typing import Any

import pytest
from connectors.net import PoliteFetcher, RobotsResult
from connectors.procurement import (
    Contract,
    EvidenceArtifactRow,
    FundingInstrument,
    InvalidContract,
    InvalidFundingInstrument,
    LifecycleTransition,
    PredicateNotAllowed,
    ProcurementConnector,
    SubAward,
    acquisition_channels,
    agenda_tenants,
    artifact_types,
    assert_predicate_allowed,
    assert_pulls_subawards,
    cooperative_channel,
    evidence_artifact_id,
    forbidden_predicate_genres,
    funding_instrument_from_subaward,
    funding_instrument_types,
    is_cooperative_vehicle,
    is_predicate_allowed,
    load_claims_for_l1,
    org_candidate,
    procurement_states,
    source_ids,
    tenant_discovery_negatives,
    tenant_targets,
    trace_subaward_to_deployment,
)
from connectors.registry import get
from connectors.stages import FetchResult, InMemoryCaptureStore, InMemoryClaimSink, RunContext
from evidence.ingest_run import IngestRun
from support import load_schemaview

_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"


# --- local fixtures -----------------------------------------------------------


def _ingest_run() -> IngestRun:
    return IngestRun(
        connector_name="procurement",
        connector_version="1.0.0",
        code_commit="deadbeef",
        ruleset_version="r1",
        vocab_version="v1",
        input_digests=(),
    )


def _ctx(source_key: str = "sourcewell", **kwargs: Any) -> RunContext:
    """A RunContext against a permitted procurement source (loader gate open)."""
    source = dataclasses.replace(get(source_ids()[source_key]), ingestion_permitted=True)
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
        connector_name="procurement", connector_version="1.0.0", transport=transport
    )


# --- AC1: cooperative piggyback sets parent_cooperative_contract (SIG-ONTO-032) ---


def test_cooperative_piggyback_contract_requires_parent() -> None:
    # SIG-ONTO-032: a cooperative_piggyback contract MUST link the ridden master
    # award; a missing local RFP is NOT evidence that no procurement exists.
    with pytest.raises(InvalidContract):
        Contract(
            external_id="c1",
            source_id="sourcewell",
            acquisition_channel="cooperative_piggyback",
        )


def test_cooperative_piggyback_with_parent_is_valid() -> None:
    contract = Contract(
        external_id="c1",
        source_id="sourcewell",
        acquisition_channel="cooperative_piggyback",
        parent_cooperative_contract="sourcewell:020617-FSI",
    )
    assert contract.is_cooperative_piggyback
    rows = contract.claim_rows()
    parent_rows = [r for r in rows if r.get("predicate_id") == "parent_cooperative_contract"]
    assert len(parent_rows) == 1
    assert parent_rows[0]["value"] == "sourcewell:020617-FSI"


def test_cooperative_vehicle_source_defaults_to_piggyback_and_links_master() -> None:
    # A contract sourced from a cooperative vehicle (Sourcewell) is a piggyback:
    # the connector defaults acquisition_channel and requires the master award.
    ctx = _ctx("sourcewell")
    raw = {
        "record_kind": "contract",
        "raw": {
            "id": "OKCPD-FLOCK-2024",
            "agency": "Oklahoma City Police Department",
            "vendor": "Flock Group Inc.",
            "master_contract": "sourcewell:020617-FSI",
            "amount": "250000",
        },
    }
    rows = ProcurementConnector().normalize(ctx, [raw])
    entity = next(r for r in rows if r.get("record_kind") == "contract")
    assert entity["acquisition_channel"] == "cooperative_piggyback"
    assert entity["parent_cooperative_contract"] == "sourcewell:020617-FSI"


def test_cooperative_vehicle_without_master_award_is_a_hard_error() -> None:
    # The connector must not silently drop the SIG-ONTO-032 requirement.
    ctx = _ctx("sourcewell")
    raw = {"record_kind": "contract", "raw": {"id": "x", "agency": "PD", "vendor": "V"}}
    with pytest.raises(InvalidContract):
        ProcurementConnector().normalize(ctx, [raw])


def test_all_named_cooperative_vehicles_are_registered() -> None:
    # §22.3 / SIG-ONTO-032 names eight vehicles; each is a seeded registry source.
    for vehicle in (
        "sourcewell",
        "omnia_partners",
        "naspo_valuepoint",
        "buyboard",
        "tips_usa",
        "hgacbuy",
        "equalis_group",
        "gsa",
    ):
        assert is_cooperative_vehicle(vehicle), vehicle
        assert get(vehicle) is not None


# --- AC2 & AC4: federal sub-awards; funder != recipient (SIG-ONTO-033) --------


def _byrne_jag_subaward() -> SubAward:
    # A real-world-shaped case: a Byrne JAG sub-award to a sheriff for LPR cameras.
    return SubAward(
        subaward_id="SUB-2023-JAG-0099",
        prime_award_id="15PBJA-23-GG-01234-JAGX",
        funder="U.S. Department of Justice, Bureau of Justice Assistance",
        recipient="Jefferson County Sheriff's Office",
        program_name="Byrne JAG",
        amount="82000",
        award_date="2023-09-30",
        description="License plate reader cameras and installation",
    )


def test_subaward_becomes_funding_instrument_distinguishing_funder_from_recipient() -> None:
    # AC4: FundingInstrument distinguishes funder (federal program) from
    # recipient/purchaser (the local agency).
    instrument = funding_instrument_from_subaward(_byrne_jag_subaward(), source_id="usaspending")
    assert instrument.funder != instrument.recipient
    assert instrument.instrument_type == "federal_grant"
    assert instrument.federal_award_id == "15PBJA-23-GG-01234-JAGX"
    assert instrument.program_name == "Byrne JAG"


def test_funder_and_recipient_must_differ() -> None:
    # The whole point of the entity: the party paying is not the party operating.
    with pytest.raises(InvalidFundingInstrument):
        FundingInstrument(
            external_id="x",
            source_id="usaspending",
            funder="Same Org",
            recipient="Same Org",
            instrument_type="federal_grant",
        )


def test_funding_instrument_requires_both_parties() -> None:
    with pytest.raises(InvalidFundingInstrument):
        FundingInstrument(
            external_id="x",
            source_id="usaspending",
            funder="Funder",
            recipient="",
            instrument_type="federal_grant",
        )


def test_subaward_traces_to_deployment_via_federal_award_id() -> None:
    # AC2: USAspending sub-award → federal_award_id → local deployment.
    instrument = funding_instrument_from_subaward(_byrne_jag_subaward(), source_id="usaspending")
    trace = trace_subaward_to_deployment(instrument, deployment_id="deploy:jeffco:alpr:2023")
    assert trace["predicate_id"] == "federal_award_id"
    assert trace["value"] == "15PBJA-23-GG-01234-JAGX"
    assert trace["traces_to_deployment"]["value"] == "deploy:jeffco:alpr:2023"


def test_trace_requires_a_federal_award_id() -> None:
    instrument = FundingInstrument(
        external_id="x",
        source_id="usaspending",
        funder="DOJ",
        recipient="Sheriff",
        instrument_type="federal_grant",
    )
    with pytest.raises(InvalidFundingInstrument):
        trace_subaward_to_deployment(instrument, deployment_id="d1")


def test_usaspending_target_must_pull_subawards() -> None:
    # SIG-ONTO-033: sub-awards MUST be pulled, not only prime awards.
    assert_pulls_subawards(
        {"url": "https://api.usaspending.gov/api/v2/subawards/", "subaward": True}
    )
    with pytest.raises(ValueError):
        assert_pulls_subawards(
            {"url": "https://api.usaspending.gov/api/v2/search/", "subaward": False}
        )
    with pytest.raises(ValueError):
        assert_pulls_subawards({"url": "https://api.usaspending.gov/api/v2/search/"})


def test_discover_asserts_usaspending_targets_pull_subawards() -> None:
    conn = ProcurementConnector()
    prime_only = _ctx("usaspending", parameters={"targets": [{"url": "u", "subaward": False}]})
    with pytest.raises(ValueError):
        conn.discover(prime_only)


def test_subaward_flows_through_normalize_and_traces() -> None:
    ctx = _ctx("usaspending")
    raw = {
        "record_kind": "subaward",
        "raw": {
            "subaward_id": "SUB-2023-JAG-0099",
            "prime_award_id": "15PBJA-23-GG-01234-JAGX",
            "prime_awardee": "U.S. DOJ, Bureau of Justice Assistance",
            "subawardee": "Jefferson County Sheriff's Office",
            "program_name": "Byrne JAG",
            "subaward_amount": "82000",
            "deployment_id": "deploy:jeffco:alpr:2023",
        },
    }
    rows = ProcurementConnector().normalize(ctx, [raw])
    fi = next(r for r in rows if r.get("record_kind") == "funding_instrument")
    assert fi["federal_award_id"] == "15PBJA-23-GG-01234-JAGX"
    traces = [r for r in rows if r.get("traces_to_deployment")]
    assert traces and traces[0]["traces_to_deployment"]["value"] == "deploy:jeffco:alpr:2023"


def test_subaward_is_detected_apart_from_a_prime_contract() -> None:
    # extract() routes a sub-award-shaped object to the FundingInstrument path.
    ctx = _ctx("usaspending")
    parsed = {
        "kind": "procurement_payload",
        "payload": {"results": [{"subaward_id": "s1", "prime_award_id": "p1"}]},
        "capture": None,
    }
    extracted = ProcurementConnector().extract(ctx, parsed)
    assert extracted[0]["record_kind"] == "subaward"


# --- AC3: agenda-platform tenant registry (§22.3, SIG-METRIC-002a) ------------


def test_agenda_tenant_registry_is_published_and_seeded() -> None:
    # The municipality→platform directory exists (§22.3 "SIG should build one").
    tenants = agenda_tenants()
    assert tenants  # non-empty
    for row in tenants.values():
        assert row.get("platform")
        assert row.get("jurisdiction")
        assert row.get("api_base")


def test_connector_reads_tenants_from_the_registry() -> None:
    # AC3: discover() over an agenda-platform source reads its targets from the
    # published registry.
    conn = ProcurementConnector()
    targets = conn.discover(_ctx("legistar"))
    assert targets  # tenants for the legistar platform
    assert all(t["platform"] == "legistar" for t in targets)
    assert any("legistar.com" in str(t["url"]) for t in targets)


def test_tenant_targets_filter_by_platform() -> None:
    legistar = tenant_targets("legistar")
    primegov = tenant_targets("primegov")
    assert {t["platform"] for t in legistar} == {"legistar"}
    assert {t["platform"] for t in primegov} == {"primegov"}


def test_tenant_discovery_negatives_are_retained_as_coverage() -> None:
    # SIG-METRIC-002a: a jurisdiction probed with no platform is a NO_EVIDENCE_FOUND
    # coverage record naming the platforms probed — retained, not discarded.
    negatives = tenant_discovery_negatives()
    assert negatives
    neg = negatives[0]
    assert neg["record_kind"] == "coverage_record"
    assert neg["absence_state"] == "NO_EVIDENCE_FOUND"
    assert neg["absence_kind"] == "searched_not_found"
    assert neg["sources_searched"]  # SIG-TIME-011: names what was searched


# --- SIG-INGEST-047: artifact_type additions ---------------------------------


def test_new_artifact_types_are_members_of_the_ontology_enum() -> None:
    sv = load_schemaview()
    enum = set(sv.get_enum("ArtifactType").permissible_values)
    for value in ("state_auditor_survey", "warrant", "procurement_aggregator_record"):
        assert value in enum, value


def test_connector_artifact_types_are_a_subset_of_the_ontology_enum() -> None:
    sv = load_schemaview()
    enum = set(sv.get_enum("ArtifactType").permissible_values)
    assert artifact_types() <= enum


def test_evidence_artifact_stamps_artifact_type() -> None:
    artifact = EvidenceArtifactRow(
        artifact_id=evidence_artifact_id("https://cdn/contract.pdf"),
        source_id="sourcewell",
        source_uri="https://cdn/contract.pdf",
        capture_digest="deadbeef",
        media_type="application/pdf",
        byte_size=10,
        artifact_type="contract",
        classification={"file_format": "pdf"},
    )
    row = artifact.to_row()
    assert row["artifact_type"] == "contract"
    assert row["published_by"] == "sourcewell"


def test_govspend_documents_carry_the_aggregator_artifact_type() -> None:
    # SIG-INGEST-047: the paywalled aggregator's records carry procurement_aggregator_record.
    ctx = _ctx("govspend")
    pdf = b"%PDF-1.4\n1 0 obj<< >>endobj\n%%EOF"
    capture = ctx.captures.put(
        pdf, media_type="application/pdf", source_uri="https://govspend/doc.pdf"
    )
    conn = ProcurementConnector()
    rows = conn.normalize(ctx, conn.extract(ctx, conn.parse(ctx, capture)))
    artifact = next(r for r in rows if r.get("record_kind") == "evidence_artifact")
    assert artifact["artifact_type"] == "procurement_aggregator_record"
    assert artifact["classification"]["file_format"] == "pdf"


def test_govspend_is_registered_under_a_link_custody_posture() -> None:
    # SIG-INGEST-047: the paywalled aggregator is carried under LINK.
    from connectors.registry import CustodyPosture

    assert get("govspend").custody_posture is CustodyPosture.LINK


# --- vocabulary lock-step with the frozen ontology enums ----------------------


def test_acquisition_channel_vocab_matches_the_ontology_enum() -> None:
    sv = load_schemaview()
    enum = set(sv.get_enum("AcquisitionChannel").permissible_values)
    assert acquisition_channels() == enum
    assert cooperative_channel() in enum


def test_funding_instrument_type_vocab_matches_the_ontology_enum() -> None:
    sv = load_schemaview()
    enum = set(sv.get_enum("FundingInstrumentType").permissible_values)
    assert funding_instrument_types() == enum


def test_procurement_state_vocab_matches_the_ontology_enum() -> None:
    sv = load_schemaview()
    enum = set(sv.get_enum("ProcurementState").permissible_values)
    assert procurement_states() == enum


# --- predicate allowlist (SIG-INGEST-033) -------------------------------------


def test_predicate_allowlist_is_the_contract_and_funding_surface() -> None:
    for predicate in (
        "contract",
        "acquisition_channel",
        "parent_cooperative_contract",
        "funding_instrument",
        "funder",
        "recipient",
        "federal_award_id",
        "lifecycle_transition",
    ):
        assert is_predicate_allowed(predicate), predicate


def test_writing_outside_the_allowlist_is_a_schema_error() -> None:
    with pytest.raises(PredicateNotAllowed):
        assert_predicate_allowed("device_count")
    with pytest.raises(PredicateNotAllowed):
        assert_predicate_allowed("response_status")


def test_forbidden_genres_are_outside_the_allowlist() -> None:
    for genre in forbidden_predicate_genres():
        assert not is_predicate_allowed(genre), genre


# --- candidate identifiers only, never resolution (SIG-INGEST-034) ------------


def test_party_predicates_carry_a_candidate_identifier_not_a_resolution() -> None:
    contract = Contract(
        external_id="c1",
        source_id="legistar",
        buyer="Oklahoma City Police Department",
        seller="Flock Group Inc.",
    )
    rows = contract.claim_rows()
    buyer_rows = [r for r in rows if r.get("predicate_id") == "buyer"]
    assert buyer_rows[0]["candidate_identifier"]["scheme"] == "procurement.org_name"
    assert "resolved_entity_id" not in buyer_rows[0]


def test_funding_parties_carry_candidate_identifiers() -> None:
    instrument = funding_instrument_from_subaward(_byrne_jag_subaward(), source_id="usaspending")
    rows = instrument.claim_rows()
    funder_rows = [r for r in rows if r.get("predicate_id") == "funder"]
    assert funder_rows[0]["candidate_identifier"] == org_candidate(instrument.funder)


# --- validation ---------------------------------------------------------------


def test_invalid_acquisition_channel_is_rejected() -> None:
    with pytest.raises(InvalidContract):
        Contract(external_id="c1", source_id="legistar", acquisition_channel="handshake")


def test_invalid_instrument_type_is_rejected() -> None:
    with pytest.raises(InvalidFundingInstrument):
        FundingInstrument(
            external_id="x",
            source_id="usaspending",
            funder="DOJ",
            recipient="Sheriff",
            instrument_type="bake_sale",
        )


def test_contract_external_id_is_required() -> None:
    with pytest.raises(InvalidContract):
        Contract(external_id="", source_id="legistar")


def test_invalid_lifecycle_state_is_rejected() -> None:
    with pytest.raises(InvalidContract):
        LifecycleTransition(state="teleported", date="2024-01-01")


def test_dated_lifecycle_transition_is_written() -> None:
    contract = Contract(
        external_id="c1",
        source_id="legistar",
        lifecycle=(LifecycleTransition(state="awarded", date="2024-03-01"),),
    )
    rows = contract.claim_rows()
    transitions = [r for r in rows if r.get("predicate_id") == "lifecycle_transition"]
    assert transitions[0]["value"] == {"state": "awarded", "date": "2024-03-01"}


# --- append-only load contract (SIG-INGEST-003) -------------------------------


def test_load_adds_identity_only_to_claim_and_entity_rows() -> None:
    rows = [
        {"record_kind": "contract", "subject_id": "contract:sourcewell:1"},
        {"record_kind": "funding_instrument", "subject_id": "funding_instrument:usaspending:1"},
        {"record_kind": "claim", "subject_id": "contract:sourcewell:1", "predicate_id": "amount"},
        {"record_kind": "coverage_record", "subject_id": "jurisdiction:x"},
        {"record_kind": "evidence_artifact", "subject_id": "procurement:artifact:z"},
        {"record_kind": "quality_report", "capture_digest": "d"},
    ]
    loaded = load_claims_for_l1(rows)
    by_kind = {r["record_kind"]: r for r in loaded}
    assert "claim_id" in by_kind["contract"] and "sys_period" in by_kind["contract"]
    assert "claim_id" in by_kind["funding_instrument"]
    assert "claim_id" in by_kind["claim"]
    assert "claim_id" not in by_kind["coverage_record"]
    assert "claim_id" not in by_kind["evidence_artifact"]
    assert "claim_id" not in by_kind["quality_report"]


# --- integration: the full pipeline (SIG-INGEST-001) --------------------------


def test_pipeline_ingests_a_cooperative_contract_end_to_end() -> None:
    from connectors import pipeline

    url = "https://www.sourcewell-mn.gov/contracts/020617-FSI/OKCPD"
    payload = {
        "id": "MAT-42",
        "agency": "Chicago Police Department",
        "vendor": "Flock Group Inc.",
        "master_contract": "sourcewell:020617-FSI",
        "amount": "500000",
        "lifecycle": [{"state": "awarded", "date": "2024-05-01"}],
    }
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    transport = _SequenceTransport({url: [(200, body, "application/json")]})
    ctx = _ctx("sourcewell", fetcher=_fetcher(transport), parameters={"targets": [{"url": url}]})
    report = pipeline.run(ProcurementConnector(), ctx)
    assert report.asserted
    kinds = {c.get("record_kind") for c in report.claims}
    assert "contract" in kinds
    assert "quality_report" in kinds
    entity = next(c for c in report.claims if c.get("record_kind") == "contract")
    assert entity["parent_cooperative_contract"] == "sourcewell:020617-FSI"


def test_pipeline_ingests_usaspending_subawards_end_to_end() -> None:
    from connectors import pipeline

    url = "https://api.usaspending.gov/api/v2/subawards/"
    payload = {
        "results": [
            {
                "subaward_id": "SUB-2023-JAG-0099",
                "prime_award_id": "15PBJA-23-GG-01234-JAGX",
                "prime_awardee": "U.S. DOJ, Bureau of Justice Assistance",
                "subawardee": "Jefferson County Sheriff's Office",
                "program_name": "Byrne JAG",
                "subaward_amount": "82000",
            }
        ]
    }
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    transport = _SequenceTransport({url: [(200, body, "application/json")]})
    ctx = _ctx(
        "usaspending",
        fetcher=_fetcher(transport),
        parameters={"targets": [{"url": url, "subaward": True}]},
    )
    report = pipeline.run(ProcurementConnector(), ctx)
    assert report.asserted
    fi = next(c for c in report.claims if c.get("record_kind") == "funding_instrument")
    assert fi["federal_award_id"] == "15PBJA-23-GG-01234-JAGX"
