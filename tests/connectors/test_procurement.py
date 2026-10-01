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
from pathlib import Path
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
        self.bodies: list[bytes | None] = []

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ROBOTS_ALLOW_ALL)

    def request(
        self,
        url: str,
        *,
        user_agent: str,
        headers: Mapping[str, str] | None = None,
        body: bytes | None = None,
    ) -> FetchResult:
        self.request_log.append(url)
        self.bodies.append(body)
        status, body_, media = self._responses[url].pop(0)
        return FetchResult(url=url, status=status, body=body_, media_type=media)


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
    # P26.14: sub-award-shaped rows route to BOTH the notice record (typed
    # federal-award claims) and the FundingInstrument path.
    assert any(r["record_kind"] == "subaward" for r in extracted)
    assert any(r["record_kind"] == "procurement_notice" for r in extracted)


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
        parameters={
            "targets": [{"url": url, "subaward": True}],
            "sweep_expansion": False,
        },
    )
    report = pipeline.run(ProcurementConnector(), ctx)
    assert report.asserted
    fi = next(c for c in report.claims if c.get("record_kind") == "funding_instrument")
    assert fi["federal_award_id"] == "15PBJA-23-GG-01234-JAGX"


def test_usaspending_post_body_target_posts_and_parses_display_labels() -> None:
    # The live USAspending shape: a POST to /search/spending_by_award/ whose
    # results carry the API's display labels (verified against the real API
    # 2026-09-15) rather than snake_case keys.
    from connectors import pipeline

    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    payload = {
        "results": [
            {
                "internal_id": "SUB-OKC-001",
                "Sub-Award ID": "SUB-OKC-001",
                "Sub-Awardee Name": "Oklahoma City Police Department",
                "Sub-Award Date": "2023-06-01",
                "Sub-Award Amount": 82000.0,
                "Sub-Award Description": "ALPR cameras",
                "Awarding Agency": "U.S. DOJ",
                "prime_award_generated_internal_id": "ASST_NON_15PBJA-23-GG-01234-JAGX_180",
            }
        ]
    }
    transport = _SequenceTransport(
        {url: [(200, json.dumps(payload).encode("utf-8"), "application/json")]}
    )
    post_body = {"subawards": True, "filters": {"keywords": ["license plate reader"]}}
    ctx = _ctx(
        "usaspending",
        fetcher=_fetcher(transport),
        parameters={
            "targets": [{"url": url, "subaward": True, "post_body": post_body}],
            "sweep_expansion": False,
        },
    )
    report = pipeline.run(ProcurementConnector(), ctx)
    assert report.asserted
    # The target's post_body was sent verbatim as the request body (JSON).
    assert transport.bodies == [json.dumps(post_body, sort_keys=True).encode("utf-8")]
    fi = next(c for c in report.claims if c.get("record_kind") == "funding_instrument")
    assert fi["federal_award_id"] == "ASST_NON_15PBJA-23-GG-01234-JAGX_180"
    recipient = next(c for c in report.claims if c.get("predicate_id") == "recipient")
    assert recipient["value"] == "Oklahoma City Police Department"


# --- P26.14 (FEDERAL.1): bounded federal award sweeps --------------------------


def test_usaspending_sweep_generates_bounded_slice_targets() -> None:
    from connectors.procurement import usaspending_award_targets

    targets = usaspending_award_targets()
    assert targets
    # Every slice is a POST to the documented search endpoint with the slice
    # id riding the (never-transmitted) #sig-slice fragment.
    for t in targets:
        assert t["kind"] == "usaspending_award_search"
        assert t["url"].startswith("https://api.usaspending.gov/api/v2/search/spending_by_award/")
        assert f"#sig-slice={t['id']}" in t["url"]
        assert t["post_body"]["limit"] <= 100
        assert t["post_body"]["page"] >= 1
    kinds = {(t["award_kind"], t.get("slice")) for t in targets}
    assert ("sub", "subaward_keyword") in kinds
    assert ("prime", "prime_keyword") in kinds
    assert ("sub", "awarding_agency") in kinds
    # Page bounds are enforced: sub keyword slices stop at the reviewed max.
    sub_pages = {t["page"] for t in targets if t["award_kind"] == "sub" and t.get("index_keyword")}
    assert max(sub_pages) <= 2


def test_prime_slice_is_legal_but_undeclared_prime_is_still_refused() -> None:
    # SIG-ONTO-033: the sweep MUST pull sub-awards — a declared prime slice of
    # the reviewed plan is fine; an undeclared prime-only target is refused.
    from connectors.procurement import usaspending_award_targets

    prime = next(t for t in usaspending_award_targets() if t["award_kind"] == "prime")
    assert_pulls_subawards(prime)  # declared prime slice: OK
    with pytest.raises(ValueError):
        assert_pulls_subawards(
            {"url": "https://api.usaspending.gov/api/v2/search/", "subaward": False}
        )


def test_discover_expands_usaspending_sweep_and_dedupes() -> None:
    conn = ProcurementConnector()
    supplied = {
        "id": "sub_kw:drone:p1",  # collides with a generated slice id
        "url": "https://api.usaspending.gov/api/v2/search/spending_by_award/#sig-slice=sub_kw:drone:p1",
        "kind": "usaspending_award_search",
        "award_kind": "sub",
        "subaward": True,
        "post_body": {"subawards": True, "filters": {"keywords": ["drone"]}},
    }
    ctx = _ctx("usaspending", parameters={"targets": [supplied]})
    targets = conn.discover(ctx)
    ids = [t.get("id") for t in targets]
    assert ids.count("sub_kw:drone:p1") == 1  # deduped, not double-fetched
    assert len(ids) == len(set(ids))
    # Generated slices present alongside the supplied one.
    assert any(i.startswith("prime_kw:") for i in ids)
    assert any(i.startswith("agency:") for i in ids)


def test_usaspending_slice_emits_typed_notice_claims_end_to_end() -> None:
    """A captured award-search slice → typed procurement_notice claims.

    The claim surface must carry award id, recipient, awarding agency,
    amount, period, description, and the verbatim matched keyword — each with
    an evidence locator — and must assert NOTHING about deployment.
    """
    from connectors import pipeline

    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/#sig-slice=sub_kw:drone:p1"
    payload = {
        "results": [
            {
                "internal_id": "SUB-OKC-001",
                "Sub-Award ID": "SUB-OKC-001",
                "Sub-Awardee Name": "Oklahoma City Police Department",
                "Sub-Award Date": "2023-06-01",
                "Sub-Award Amount": 82000.0,
                "Sub-Award Description": "ALPR cameras for the patrol division",
                "Awarding Agency": "Department of Justice",
                "prime_award_generated_internal_id": "ASST_NON_15PBJA-23-GG-01234-JAGX_180",
            }
        ],
        "page_metadata": {"page": 1, "total": 1, "hasNext": False},
    }
    transport = _SequenceTransport(
        {url: [(200, json.dumps(payload).encode("utf-8"), "application/json")]}
    )
    post_body = {
        "subawards": True,
        "filters": {"keywords": ["drone"], "award_type_codes": ["02"]},
        "fields": ["Sub-Award ID"],
        "limit": 100,
        "page": 1,
    }
    ctx = _ctx(
        "usaspending",
        fetcher=_fetcher(transport),
        parameters={
            "targets": [
                {
                    "id": "sub_kw:drone:p1",
                    "url": url,
                    "kind": "usaspending_award_search",
                    "award_kind": "sub",
                    "subaward": True,
                    "index_keyword": "drone",
                    "slice": "subaward_keyword",
                    "page": 1,
                    "post_body": post_body,
                }
            ],
            "sweep_expansion": False,
        },
    )
    report = pipeline.run(ProcurementConnector(), ctx)
    assert report.asserted
    claims = report.claims

    # The per-slice outcome row is recorded.
    slice_row = next(c for c in claims if c.get("record_kind") == "usaspending_slice")
    assert slice_row["items_count"] == 1
    assert slice_row["provenance"]["index_keyword"] == "drone"

    # The notice subject + typed field claims exist with evidence locators.
    notice = next(c for c in claims if c.get("record_kind") == "procurement_notice")
    subject = notice["subject_id"]
    by_pred = {}
    for c in claims:
        if c.get("record_kind") == "claim" and c.get("subject_id") == subject:
            by_pred.setdefault(c["predicate_id"], []).append(c)
    assert by_pred["external_id"][0]["value"] == "SUB-OKC-001"
    assert by_pred["recipient"][0]["value"] == "Oklahoma City Police Department"
    assert by_pred["funder"][0]["value"] == "Department of Justice"
    assert by_pred["amount"][0]["value"] == "82000.0"
    assert by_pred["period"][0]["value"]["start"] == "2023-06-01"
    assert "ALPR" in by_pred["description"][0]["raw_value"]
    assert by_pred["federal_award_id"][0]["value"] == "ASST_NON_15PBJA-23-GG-01234-JAGX_180"
    # Every field claim carries a locator into the captured results array.
    for pred in ("recipient", "funder", "amount", "description"):
        assert by_pred[pred][0]["evidence"]["locator"]

    # matched_keyword: raw_value is a VERBATIM literal slice of the record
    # text — the claim asserts a text match, never a deployment.
    mk = by_pred["matched_keyword"]
    assert mk and mk[0]["raw_value"] == "ALPR"
    assert mk[0]["evidence"]["locator"]
    assert mk[0]["evidence"]["field"] == "Sub-Award Description"

    # FundingInstrument still flows for sub-award rows (SIG-ONTO-033).
    fi = next(c for c in claims if c.get("record_kind") == "funding_instrument")
    assert fi["federal_award_id"] == "ASST_NON_15PBJA-23-GG-01234-JAGX_180"

    # Procured ≠ deployed: no deployment/person/plate predicate anywhere.
    predicates = {c.get("predicate_id") for c in claims}
    assert "deployment_exists" not in predicates
    assert "device_count" not in predicates
    forbidden = {"deployment_exists", "device_count", "camera_count", "configuration_state"}
    assert not (predicates & forbidden)


def test_prime_slice_normalizes_buyer_not_funder() -> None:
    """Prime contract-award rows: the awarding agency is the buyer, not funder."""
    ctx = _ctx("usaspending")
    raw = {
        "record_kind": "procurement_notice",
        "notice_provenance": {
            "source_uri": "https://api.usaspending.gov/api/v2/search/spending_by_award/#sig-slice=prime_kw:drone:p1",
            "award_kind": "prime",
            "slice": "prime_keyword",
            "index_keyword": "drone",
        },
        "row_index": 0,
        "raw": {
            "Award ID": "CONT_AWD_123",
            "Recipient Name": "AeroVironment Inc",
            "Award Amount": 4500000.0,
            "Start Date": "2023-01-15",
            "End Date": "2025-01-14",
            "Awarding Agency": "Department of Defense",
            "Description": "Unmanned aerial systems",
        },
    }
    rows = ProcurementConnector().normalize(ctx, [raw])
    by_pred = {}
    for r in rows:
        if r.get("record_kind") == "claim":
            by_pred.setdefault(r["predicate_id"], []).append(r)
    assert by_pred["buyer"][0]["value"] == "Department of Defense"
    assert "funder" not in by_pred
    assert by_pred["period"][0]["value"]["end"] == "2025-01-14"
    assert by_pred["external_id"][0]["value"] == "CONT_AWD_123"
    # The drone literal matches verbatim.
    assert any(m["raw_value"].lower().startswith("unmanned") for m in by_pred["matched_keyword"])


def test_sam_gov_widened_keyword_targets_and_dedupe() -> None:
    from connectors.procurement import sam_gov_search_targets

    targets = sam_gov_search_targets()
    assert len(targets) >= 15
    for t in targets:
        assert t["url"].startswith("https://api.sam.gov/prod/opportunities/v2/search?")
        assert "api_key" not in t["url"] and "X-Api-Key" not in t["url"]
        assert "title=" in t["url"]
    # discover() dedupes a supplied target that already searches a keyword.
    supplied_url = (
        "https://api.sam.gov/prod/opportunities/v2/search?"
        "limit=25&postedFrom=01%2F01%2F2026&postedTo=12%2F31%2F2026&title=license%20plate%20reader"
    )
    ctx = _ctx(
        "sam_gov",
        parameters={"targets": [{"id": "s1", "url": supplied_url, "kind": "opportunity_search"}]},
    )
    discovered = ProcurementConnector().discover(ctx)
    lpr = [t for t in discovered if t.get("index_keyword") == "license plate reader"]
    assert lpr == []  # generated LPR slice suppressed by the supplied search
    assert any(t.get("index_keyword") == "drone" for t in discovered)


# --- P31.13 (BREADTH.2): FEMA HSGP assistance allocations ----------------------

_FIXTURES = Path(__file__).parent / "fixtures"


def _fema_ctx(**kwargs: Any) -> RunContext:
    """A RunContext for the fema_hsgp_allocations source (loader gate open in tests)."""
    return _ctx("fema_hsgp", **kwargs)


def _fema_target(page: int = 1) -> dict[str, Any]:
    """The reviewed assistance-slice target shape (live_targets.toml [fema_hsgp_allocations])."""
    return {
        "id": f"fema-hsgp-allocations:p{page}",
        "url": f"https://api.usaspending.gov/api/v2/search/spending_by_award/#sig-slice=fema_hsgp_allocations:p{page}",
        "kind": "usaspending_award_search",
        "award_kind": "prime",
        "award_class": "assistance",
        "slice": "hsgp_allocations",
        "page": page,
        "post_body": {
            "subawards": False,
            "filters": {
                "award_type_codes": ["02", "03", "04", "05"],
                "agencies": [
                    {
                        "type": "awarding",
                        "tier": "subtier",
                        "name": "Federal Emergency Management Agency",
                    }
                ],
                "program_numbers": ["97.067"],
            },
            "fields": [
                "Award ID",
                "Recipient Name",
                "Start Date",
                "End Date",
                "Award Amount",
                "Awarding Agency",
                "Awarding Sub Agency",
                "Award Type",
                "Assistance Listings",
                "Description",
            ],
            "limit": 100,
            "page": page,
        },
    }


def test_fema_source_is_registered_routed_and_reviewed() -> None:
    # The registry row rides the procurement connector; its live targets are
    # the two reviewed assistance slices (award_class="assistance" admits them
    # under SIG-ONTO-033 as declared prime/assistance targets).
    from connectors.live_targets import live_targets
    from connectors.runner import CONNECTOR_FOR_SOURCE

    assert source_ids()["fema_hsgp"] == "fema_hsgp_allocations"
    assert CONNECTOR_FOR_SOURCE["fema_hsgp_allocations"] == "procurement"
    targets = live_targets("fema_hsgp_allocations")
    assert len(targets) == 2
    for t in targets:
        assert t["award_class"] == "assistance"
        assert t["post_body"]["filters"]["program_numbers"] == ["97.067"]
        # Declared prime/assistance slices satisfy the sub-award mandate as
        # reviewed bounded slices (the sweep still pulls sub-awards elsewhere).
        assert_pulls_subawards(t)


def test_fema_assistance_row_normalizes_funder_not_buyer() -> None:
    """Assistance rows: the awarding sub-agency is the FUNDER, never a buyer."""
    ctx = _fema_ctx()
    raw = {
        "record_kind": "procurement_notice",
        "notice_provenance": {
            "source_uri": _fema_target()["url"],
            "award_kind": "prime",
            "award_class": "assistance",
            "slice": "hsgp_allocations",
        },
        "row_index": 0,
        "raw": {
            "Award ID": "SIG-EMW-2024-SS-00001",
            "Recipient Name": "STATE OF EXAMPLE EMERGENCY MANAGEMENT AGENCY",
            "Awarding Agency": "Department of Homeland Security",
            "Awarding Sub Agency": "Federal Emergency Management Agency",
            "Award Amount": 15250000.0,
            "Start Date": "2024-10-01",
            "End Date": "2027-09-30",
            "Award Type": "02 - BLOCK GRANT",
            "Assistance Listings": [
                {
                    "cfda_number": "97.067",
                    "cfda_program_title": "HOMELAND SECURITY GRANT PROGRAM",
                }
            ],
            "Description": "HOMELAND SECURITY GRANT PROGRAM ALLOCATION",
        },
    }
    rows = ProcurementConnector().normalize(ctx, [raw])
    claims = [r for r in rows if r.get("record_kind") == "claim"]
    by_pred: dict[str, list[dict[str, Any]]] = {}
    for c in claims:
        by_pred.setdefault(c["predicate_id"], []).append(c)
    # The administering sub-agency (FEMA under DHS) is the funder-of-record —
    # verbatim; a buyer claim would assert a purchase that never happened.
    assert by_pred["funder"][0]["value"] == "Federal Emergency Management Agency"
    assert by_pred["funder"][0]["raw_value"] == "Federal Emergency Management Agency"
    assert "buyer" not in by_pred
    assert by_pred["recipient"][0]["value"] == "STATE OF EXAMPLE EMERGENCY MANAGEMENT AGENCY"
    # Party claims carry candidate identifiers, never a resolution (SIG-INGEST-034).
    assert by_pred["funder"][0]["candidate_identifier"]["scheme"] == "procurement.org_name"
    assert by_pred["recipient"][0]["candidate_identifier"]["scheme"] == "procurement.org_name"
    # The §11.12 FundingInstrument lands under its own subject, tracing the
    # assistance award id as federal_award_id (SIG-ONTO-033).
    fi = next(r for r in rows if r.get("record_kind") == "funding_instrument")
    assert fi["subject_id"] == "funding_instrument:fema_hsgp_allocations:SIG-EMW-2024-SS-00001"
    assert fi["federal_award_id"] == "SIG-EMW-2024-SS-00001"
    surface = fi["predicate_surface"]
    assert surface["instrument_type"] == "federal_grant"
    assert surface["funder"] == "Federal Emergency Management Agency"
    assert surface["recipient"] == "STATE OF EXAMPLE EMERGENCY MANAGEMENT AGENCY"
    assert surface["program_name"] == "HOMELAND SECURITY GRANT PROGRAM"
    # Funding ≠ deployment: no deployment/operational predicate is ever emitted.
    assert not {
        "is_deployed",
        "deployment_status",
        "device_count",
        "operates",
        "technology",
    } & {c["predicate_id"] for c in claims}


def test_fema_row_without_recipient_lands_claims_but_no_instrument() -> None:
    """A row missing the recipient literal still emits its field claims; the
    FundingInstrument is emitted only when funder AND recipient are evidenced
    (§11.12 requires both parties)."""
    ctx = _fema_ctx()
    raw = {
        "record_kind": "procurement_notice",
        "notice_provenance": {
            "source_uri": _fema_target()["url"],
            "award_kind": "prime",
            "award_class": "assistance",
            "slice": "hsgp_allocations",
        },
        "row_index": 2,
        "raw": {
            "Award ID": "SIG-EMW-2022-SS-00003",
            "Awarding Agency": "Department of Homeland Security",
            "Awarding Sub Agency": "Federal Emergency Management Agency",
            "Award Amount": 975000.0,
            "Start Date": "2022-10-01",
            "End Date": "2025-09-30",
            "Award Type": "02 - BLOCK GRANT",
        },
    }
    rows = ProcurementConnector().normalize(ctx, [raw])
    predicates = {r["predicate_id"] for r in rows if r.get("record_kind") == "claim"}
    assert "funder" in predicates and "recipient" not in predicates
    assert not any(r.get("record_kind") == "funding_instrument" for r in rows)


def test_fema_hsgp_slice_ingests_end_to_end() -> None:
    """Fixture page → pipeline → funding instruments + field claims, zero deployment."""
    from connectors import pipeline

    target = _fema_target()
    body = _FIXTURES.joinpath("fema_hsgp_page1.json").read_bytes()
    transport = _SequenceTransport({target["url"]: [(200, body, "application/json")]})
    ctx = _fema_ctx(
        fetcher=_fetcher(transport),
        parameters={"targets": [target], "sweep_expansion": False},
    )
    report = pipeline.run(ProcurementConnector(), ctx)
    assert report.asserted
    # The reviewed post_body went out verbatim as the request body.
    assert transport.bodies == [json.dumps(target["post_body"], sort_keys=True).encode("utf-8")]
    instruments = [r for r in report.claims if r.get("record_kind") == "funding_instrument"]
    # Rows 1-2 carry funder + recipient literals; row 3 lacks a recipient → no
    # instrument (its field claims still land — see the unit test above).
    assert len(instruments) == 2
    by_ext = {i["external_id"]: i for i in instruments}
    one = by_ext["SIG-EMW-2024-SS-00001"]
    assert one["predicate_surface"]["funder"] == "Federal Emergency Management Agency"
    assert one["predicate_surface"]["recipient"] == "STATE OF EXAMPLE EMERGENCY MANAGEMENT AGENCY"
    two = by_ext["SIG-EMW-2023-SS-00002"]
    # No sub-agency field → the awarding agency is the funder literal verbatim.
    assert two["predicate_surface"]["funder"] == "Department of Homeland Security"
    assert two["predicate_surface"]["recipient"] == "EXAMPLE METROPOLITAN URBAN AREA WORKING GROUP"
    assert two["federal_award_id"] == "SIG-EMW-2023-SS-00002"
    # The per-slice outcome row records the bounded window (SIG-METRIC-002a).
    slices = [r for r in report.claims if r.get("record_kind") == "usaspending_slice"]
    assert slices and slices[0]["items_count"] == 3
    # Procurement/funding ≠ deployment: nothing in the run asserts a deployment.
    claims = [r for r in report.claims if r.get("record_kind") == "claim"]
    assert not {
        "is_deployed",
        "deployment_status",
        "device_count",
        "operates",
        "technology",
        "buyer",
    } & {c["predicate_id"] for c in claims}
    # Every emitted predicate is inside the allowlist (the allowlist itself is
    # the contract+funding surface — nothing else can be written).
    assert all(is_predicate_allowed(c["predicate_id"]) for c in claims)


def test_fema_hsgp_shadow_replay_over_the_fixture_diffs_zero() -> None:
    # `sig-connectors run --mode shadow` over the committed assistance fixture:
    # the runner resolves the reviewed live_targets slices (the synthetic
    # fixture row would fail the SIG-ONTO-033 assertion), the static transport
    # serves the fixture bytes, and the replay diff is 0 (SIG-INGEST-019).
    from connectors.runner import RunMode, run_source

    report = run_source(
        "fema_hsgp_allocations",
        mode=RunMode.SHADOW,
        fixture=_FIXTURES / "fema_hsgp_page1.json",
        kind="usaspending_award_search",
        media_type="application/json",
    )
    assert report.connector == "procurement"
    assert report.diff is not None and report.diff.changed_count == 0
