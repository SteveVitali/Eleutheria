# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `atlas` connector: agency adoption, family granularity, keying, retirement (§23.3, P04.3).

Every acceptance criterion of P04.3 is pinned here against committed fixtures
(SIG-PARSE-007): a bulk Atlas adoption CSV with no per-row methodology component
(the real upstream shape → granularity loss), and a second feed that DOES record
the producing component (→ carried). The connector is driven end-to-end through
the P04.1 framework and its pure helpers are tested directly.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from connectors.atlas import (
    ATLAS_AGENCY_SCHEME,
    CATEGORY_RETIRED_PREDICATE,
    CC_BY_LICENSE,
    DEPLOYMENT_ENDED_PREDICATE,
    DEPLOYMENT_EXISTS_PREDICATE,
    ORI_SCHEME,
    SIG_GRAPH_COMPARTMENT,
    AtlasConnector,
    PredicateNotAllowed,
    agency_identity,
    assert_predicate_allowed,
    atlas_version,
    canary_findings,
    category_mapping,
    category_retirement_record,
    evidence_genres,
    forbidden_predicate_genres,
    is_predicate_allowed,
    is_retired_category,
    normalize_evidence_genre,
    parse_csv,
    predicate_allowlist,
    retired_categories,
    unmapped_category_task,
    vocab,
    vocab_version,
)
from connectors.net import FetchResult, PoliteFetcher, RobotsResult
from connectors.pipeline import run
from connectors.registry import get
from connectors.stages import (
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
    registered_connectors,
)
from evidence.ingest_run import IngestRun

_FIX = Path(__file__).parent / "fixtures" / "atlas"
_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"
_ATLAS_SOURCE_ID = "eff_atlas_of_surveillance"


def _fixture_bytes(name: str) -> bytes:
    return (_FIX / name).read_bytes()


class _StaticTransport:
    """Serves one document's bytes for any URL — no real network (SIG-INGEST-011)."""

    def __init__(self, body: bytes) -> None:
        self._body = body
        self.user_agents: list[str] = []

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ROBOTS_ALLOW_ALL)

    def request(self, url: str, *, user_agent: str) -> FetchResult:
        self.user_agents.append(user_agent)
        return FetchResult(
            url=url,
            status=200,
            body=self._body,
            media_type="text/csv",
            retrieved_at=datetime(2026, 8, 20, tzinfo=UTC),
        )


def _run_over(fixture: str) -> tuple[Any, list[dict[str, Any]]]:
    """Run the atlas connector end-to-end over a committed fixture; return (transport, claims)."""
    transport = _StaticTransport(_fixture_bytes(fixture))
    fetcher = PoliteFetcher(connector_name="atlas", connector_version="1.0.0", transport=transport)
    # The seed row stays ingestion_permitted=false (SIG-INGEST-028); a reviewer
    # flips it to run, exactly as the osm connector tests do.
    source = dataclasses.replace(get(_ATLAS_SOURCE_ID), ingestion_permitted=True)
    ctx = RunContext(
        source=source,
        run=IngestRun("atlas", "1.0.0", "deadbeef", "r1", vocab_version(), ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={
            "targets": [
                {"id": "t1", "url": "https://atlasofsurveillance.org/x", "kind": "bulk_csv"}
            ]
        },
    )
    report = run(AtlasConnector(), ctx)
    return transport, report.claims


def _deployments(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [c for c in claims if c.get("record_kind") == "claim"]


# --- registration -------------------------------------------------------------


def test_atlas_connector_is_registered() -> None:
    # SIG-INGEST-021: the connector self-registers on import under its name.
    assert "atlas" in registered_connectors()
    assert registered_connectors()["atlas"] is AtlasConnector


# --- AC4: writes confined to deployment_exists at family granularity ----------


def test_only_deployment_exists_is_written_at_family_granularity() -> None:
    _, claims = _run_over("adoption_feed.csv")
    deployments = _deployments(claims)
    assert deployments, "expected deployment_exists claims"
    for c in deployments:
        # §23.3: the ONLY claim predicate, at FAMILY-level technology granularity.
        assert c["predicate_id"] == DEPLOYMENT_EXISTS_PREDICATE
        assert c["value"] is True
        assert c["granularity"] == "family"
        assert c["technology_family"] and "-unspecified" not in c["technology_family"]


def test_category_maps_to_a_sig_family() -> None:
    # §23.3: Atlas categories roll to SIG technology FAMILIES (seeded from the
    # eff_atlas crosswalk), carrying the SKOS relation + lossy provenance.
    _, claims = _run_over("adoption_feed.csv")
    by_family = {c["technology_family"] for c in _deployments(claims)}
    assert {"alpr", "face-recognition", "gunshot-detection", "uas", "federation-hub"} <= by_family
    alpr = next(c for c in _deployments(claims) if c["technology_family"] == "alpr")
    assert alpr["crosswalk_relation"] == "broadMatch"
    assert alpr["crosswalk_lossy"] is True
    assert alpr["sig_technology_concept"] == "alpr-unspecified"


def test_predicate_allowlist_refuses_counts_coordinates_config_status() -> None:
    # SIG-INGEST-033: writing outside the allowlist is a schema error. Device
    # counts, coordinates, configuration and current status are refused.
    assert is_predicate_allowed(DEPLOYMENT_EXISTS_PREDICATE)
    assert assert_predicate_allowed(DEPLOYMENT_EXISTS_PREDICATE) == DEPLOYMENT_EXISTS_PREDICATE
    assert predicate_allowlist() == frozenset({DEPLOYMENT_EXISTS_PREDICATE})
    for forbidden in (
        "active_device_count",
        "fixed_asset_location",
        "configured_retention_days",
        "current_status",
    ):
        assert not is_predicate_allowed(forbidden)
        with pytest.raises(PredicateNotAllowed):
            assert_predicate_allowed(forbidden)
    # The spec's explicit out-of-scope write-set is named as data and is disjoint
    # from the allowlist (§23.3): counts, coordinates, configuration, status.
    genres = forbidden_predicate_genres()
    assert set(genres) == {"device_count", "coordinates", "configuration", "current_status"}
    assert not (set(genres) & predicate_allowlist())


def test_no_claim_row_writes_any_other_predicate() -> None:
    for fixture in ("adoption_feed.csv", "adoption_feed_with_method.csv"):
        _, claims = _run_over(fixture)
        for c in _deployments(claims):
            assert c["predicate_id"] == DEPLOYMENT_EXISTS_PREDICATE


# --- AC3: agency-id keying; non-ORI-shaped -> surrogate path ------------------


def test_ori_shaped_agency_routes_to_the_canonical_path() -> None:
    ident = agency_identity("TX0570000")
    assert ident.scheme == ORI_SCHEME
    assert ident.route == "canonical"
    assert ident.value == "TX0570000"


def test_non_ori_shaped_agency_routes_to_the_surrogate_path() -> None:
    # SIG-INGEST-034: the connector keys on the Atlas agency identifier and routes
    # non-ORI-shaped values (the common case: agency names) to the surrogate path.
    ident = agency_identity("Fresno Police Department")
    assert ident.scheme == ATLAS_AGENCY_SCHEME
    assert ident.route == "surrogate"


def test_agency_routing_flows_through_the_pipeline() -> None:
    _, claims = _run_over("adoption_feed.csv")
    deployments = _deployments(claims)
    fresno = next(c for c in deployments if c["raw_agency"] == "Fresno Police Department")
    assert fresno["agency_identifier"] == {
        "scheme": ATLAS_AGENCY_SCHEME,
        "value": "Fresno Police Department",
    }
    assert fresno["identity_route"] == "surrogate"
    ori_row = next(c for c in deployments if c["raw_agency"] == "TX0570000")
    assert ori_row["agency_identifier"] == {"scheme": ORI_SCHEME, "value": "TX0570000"}
    assert ori_row["identity_route"] == "canonical"


def test_connector_does_not_resolve_entities_itself() -> None:
    # SIG-INGEST-034: link() is identity — the connector emits candidate
    # identifiers and never resolves. No output row carries a resolved entity_id.
    _, claims = _run_over("adoption_feed.csv")
    for c in claims:
        assert "entity_id" not in c
        assert "match_tier" not in c


# --- AC1: attribution + Atlas vocabulary version preserved --------------------


def test_rows_preserve_atlas_source_attribution_and_vocabulary_version() -> None:
    _, claims = _run_over("adoption_feed.csv")
    assert claims
    for c in claims:
        # AC1: the Atlas's own source attribution preserved on each row.
        assert c["source_attribution"] == get(_ATLAS_SOURCE_ID).rights.attribution
        assert c["source_id"] == _ATLAS_SOURCE_ID
        # AC1 / SIG-ONTO-059: the recorded Atlas vocabulary version on every row.
        assert c["atlas_version"] == atlas_version() == "2024-03"
    # The row's own upstream links (its provenance) are carried too.
    fresno = next(c for c in _deployments(claims) if c["raw_agency"] == "Fresno Police Department")
    assert any(
        link["value"] == "https://example.gov/fresno-alpr" for link in fresno["attribution_links"]
    )


def test_rows_land_in_the_cc_by_sig_graph_compartment() -> None:
    _, claims = _run_over("adoption_feed.csv")
    for c in claims:
        assert c["license"] == CC_BY_LICENSE
        assert c["compartment"] == SIG_GRAPH_COMPARTMENT


def test_rows_are_append_only_with_no_current_value_flag() -> None:
    # AC5 (connector side): later evidence supersedes via the resolver, never by
    # overwrite — so the connector marks nothing authoritative/current (P1-P3).
    _, claims = _run_over("adoption_feed.csv")
    for c in claims:
        assert "is_current" not in c
        assert "authoritative" not in c
        assert c["raw_value"]  # raw_value preserved on every row (P2)


# --- AC2: a retired Atlas category is a retirement, not a world change ---------


def test_retired_category_is_recorded_as_a_category_retirement() -> None:
    _, claims = _run_over("adoption_feed.csv")
    retirements = [c for c in claims if c.get("record_kind") == "vocabulary_event"]
    assert len(retirements) == 1
    ring = retirements[0]
    # SIG-ONTO-059: a vocabulary event, NOT a deployment and NOT a world change.
    assert ring["predicate_id"] == CATEGORY_RETIRED_PREDICATE
    assert ring["event_class"] == "vocabulary_event"
    assert ring["predicate_id"] != DEPLOYMENT_EXISTS_PREDICATE
    assert ring["predicate_id"] != DEPLOYMENT_ENDED_PREDICATE
    assert ring["retired_category"] == "Ring/Neighbors"
    assert ring["retired_at_atlas_version"] == "2024-03"
    # The retired row does NOT produce a deployment_exists claim.
    assert all(c["raw_value"] != "Ring/Neighbors" for c in _deployments(claims))


def test_retired_category_helpers() -> None:
    assert is_retired_category("Ring/Neighbors")
    assert not is_retired_category("Automated License Plate Readers")
    assert "Ring/Neighbors" in retired_categories()
    rec = category_retirement_record("Ring/Neighbors", datetime(2026, 8, 20, tzinfo=UTC))
    assert rec["removed_data_points"] == 2530
    assert rec["predicate_id"] == CATEGORY_RETIRED_PREDICATE


# --- AC5: evidence-genre carried when recorded, else granularity loss ----------


def test_genre_is_a_granularity_loss_when_the_feed_records_no_component() -> None:
    # The real Atlas CSV has no per-row methodology component (§23.3): the
    # connector records the loss rather than guessing a tier.
    _, claims = _run_over("adoption_feed.csv")
    for c in _deployments(claims):
        assert c["evidence_genre"] is None
        assert c["evidence_genre_granularity_loss"] is True


def test_genre_is_carried_when_the_feed_records_the_component() -> None:
    _, claims = _run_over("adoption_feed_with_method.csv")
    deployments = _deployments(claims)
    reno = next(c for c in deployments if c["raw_agency"] == "Reno Police Department")
    assert reno["evidence_genre"] == "news_reporting"
    assert reno["evidence_genre_granularity_loss"] is False
    miami = next(c for c in deployments if c["raw_agency"] == "Miami Police Department")
    assert miami["evidence_genre"] == "procurement_leads"
    # Blank component -> loss; unrecognised component -> loss (never guessed).
    boise = next(c for c in deployments if c["raw_agency"] == "Boise Police Department")
    assert boise["evidence_genre"] is None and boise["evidence_genre_granularity_loss"] is True
    salem = next(c for c in deployments if c["raw_agency"] == "Salem Police Department")
    assert salem["evidence_genre"] is None and salem["evidence_genre_granularity_loss"] is True
    # An unrecognised-but-recorded component is preserved for provenance.
    assert salem["raw_evidence_component"] == "Vibes"


def test_the_nine_methodology_genres_are_named() -> None:
    # §23.3 / OL-2D-AT-02: the Atlas methodology is nine distinct evidence genres.
    assert len(evidence_genres()) == 9
    assert normalize_evidence_genre("gov docs") == "government_documents"
    assert normalize_evidence_genre("Press Release") == "press_releases"
    assert normalize_evidence_genre("staff and intern review") == "staff_review"
    assert normalize_evidence_genre("nonsense") is None  # never guessed


# --- unmapped category -> research task, never guessed -------------------------


def test_unmapped_category_files_a_research_task_and_writes_no_deployment() -> None:
    _, claims = _run_over("adoption_feed.csv")
    unmapped = [c for c in claims if c.get("record_kind") == "unmapped_category"]
    assert len(unmapped) == 1
    pp = unmapped[0]
    assert pp["raw_value"] == "Predictive Policing"
    assert pp["research_task"]["task_type"] == "unmapped_atlas_category"
    # No family was guessed for it.
    assert "technology_family" not in pp
    assert category_mapping("Predictive Policing") is None


def test_unmapped_category_task_shape() -> None:
    task = unmapped_category_task("atlas:Some Agency", "Predictive Policing")
    assert task["status"] == "generated"
    assert task["atlas_category"] == "Predictive Policing"


# --- AC6: committed fixtures + canary -----------------------------------------


def test_canary_passes_on_the_committed_fixture() -> None:
    # SIG-PARSE-008: no structural drift on a known-good response.
    assert canary_findings(parse_csv(_fixture_bytes("adoption_feed.csv"))) == []


def test_canary_flags_structural_drift() -> None:
    # An upstream that drops the Agency column (the key we route on) is drift.
    drifted = {"header": ["City", "Type"], "rows": [{"City": "X", "Type": "ALPR"}]}
    findings = canary_findings(drifted)
    assert any("Agency" in f for f in findings)
    # A response with no header at all is drift.
    assert canary_findings({}) == ["missing CSV header"]
    # A present-but-empty required cell is drift.
    empty = {"header": ["Agency", "Type"], "rows": [{"Agency": "", "Type": "ALPR"}]}
    assert any("empty" in f for f in canary_findings(empty))


# --- vocabulary is versioned data ---------------------------------------------


def test_vocabulary_is_versioned() -> None:
    # §20: the category→claim mapping is versioned data, not code.
    assert vocab_version() == vocab()["vocab_version"]
    assert atlas_version() == vocab()["atlas_version"]


def test_fetch_carries_a_descriptive_user_agent() -> None:
    # The connector fetches only through the shared politeness layer (SIG-INGEST-011).
    transport, _ = _run_over("adoption_feed.csv")
    assert transport.user_agents
    ua = transport.user_agents[0]
    assert ua.startswith("atlas/1.0.0") and "+" in ua


def test_claim_set_is_reproducible_across_runs() -> None:
    # SIG-INGEST-003: the post-capture stages are pure functions of the capture, so
    # two runs over the same bytes fingerprint identically (modulo the generated
    # claim_id / transaction time the fingerprint excludes). This is what guards the
    # replay/shadow harness — a wall-clock stamp in normalize would break it.
    from evidence.ingest_run import claim_set_fingerprint

    _, first = _run_over("adoption_feed.csv")
    _, second = _run_over("adoption_feed.csv")
    assert claim_set_fingerprint(first) == claim_set_fingerprint(second)
