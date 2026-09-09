# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `flock_portal` connector: portal layer via the aggregator API (§23.4, P11.1).

Every acceptance criterion of P11.1 is pinned here against committed fixtures
(SIG-PARSE-007): two consecutive live snapshots of the Eyes on Flock
`GET /api/v1/data` response (so the snapshot diff and portal appearance /
disappearance are exercised end to end) and one archived Wayback capture (so
historical back-fill is exercised). The connector is driven through the P04.1
framework and its pure helpers are tested directly.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest
from connectors.flock_portal import (
    CC_BY_SA_LICENSE,
    EYES_ON_FLOCK_SOURCE_ID,
    PORTAL_APPEARED_TASK,
    PORTAL_COMPARTMENT,
    PORTAL_DISAPPEARED_TASK,
    FlockPortalConnector,
    PredicateNotAllowed,
    assert_predicate_allowed,
    canary_findings,
    detect_portal_changes,
    diff_portal_snapshots,
    fallback_routes,
    fallback_tasks_for_gaps,
    forbidden_predicate_genres,
    is_poll_due,
    is_predicate_allowed,
    parse_json,
    portal_capture,
    portal_id,
    portal_slugs,
    portal_snapshot_date,
    predicate_allowlist,
    reconcile_portal_sharing,
    sharing_observations,
    snapshot_field_name,
    vocab,
    vocab_version,
)
from connectors.loader import LicenseIncompatibilityError, assert_export_compatible
from connectors.net import ChallengeEncountered, FetchResult, PoliteFetcher, RobotsResult
from connectors.pipeline import run
from connectors.registry import get
from connectors.stages import (
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
    registered_connectors,
)
from evidence.ingest_run import IngestRun
from policy.licensing import TrainingNotPermitted, assert_training_allowed
from reconcile.model import SHARING_ASYMMETRY
from reconcile.snapshot_diff import FieldChangeEvent

_FIX = Path(__file__).parent / "fixtures" / "flock_portal"
_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"
_ATLAS_SOURCE_ID = "eff_atlas_of_surveillance"


def _fixture_bytes(name: str) -> bytes:
    return (_FIX / name).read_bytes()


def _fixture_json(name: str) -> dict[str, Any]:
    return json.loads(_fixture_bytes(name).decode("utf-8"))


class _StaticTransport:
    """Serves one document's bytes for any URL — no real network (SIG-INGEST-011)."""

    def __init__(self, body: bytes, *, status: int = 200) -> None:
        self._body = body
        self._status = status
        self.user_agents: list[str] = []

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ROBOTS_ALLOW_ALL)

    def request(self, url: str, *, user_agent: str, headers: Any = None) -> FetchResult:
        self.user_agents.append(user_agent)
        return FetchResult(
            url=url,
            status=self._status,
            body=self._body,
            media_type="application/json",
            # A LATER wall-clock retrieval time than any snapshot in the fixtures,
            # so a test can prove observed_at is keyed on the upstream snapshot,
            # not on fetch time (SIG-INGEST-030c).
            retrieved_at=datetime(2027, 1, 1),  # noqa: DTZ001 - deterministic test stamp
        )


def _run_over(fixture: str, *, status: int = 200) -> tuple[_StaticTransport, Any]:
    """Run the flock_portal connector end-to-end over a committed fixture."""
    transport = _StaticTransport(_fixture_bytes(fixture), status=status)
    fetcher = PoliteFetcher(
        connector_name="flock_portal", connector_version="1.0.0", transport=transport
    )
    # The seed row stays ingestion_permitted=false (SIG-INGEST-028); a reviewer
    # flips it to run, exactly as the atlas/osm connector tests do.
    source = dataclasses.replace(get(EYES_ON_FLOCK_SOURCE_ID), ingestion_permitted=True)
    ctx = RunContext(
        source=source,
        run=IngestRun("flock_portal", "1.0.0", "deadbeef", "r1", vocab_version(), ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": [{"id": "live", "url": "https://eyesonflock.com/api/v1/data"}]},
    )
    report = run(FlockPortalConnector(), ctx)
    return transport, report


def _claims(report: Any) -> list[dict[str, Any]]:
    return report.claims


def _by_kind(claims: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [c for c in claims if c.get("record_kind") == kind]


# --- registration -------------------------------------------------------------


def test_flock_portal_connector_is_registered() -> None:
    # SIG-INGEST-021: the connector self-registers on import under its name.
    assert "flock_portal" in registered_connectors()
    assert registered_connectors()["flock_portal"] is FlockPortalConnector


# --- AC: no challenge-defeating code; a challenge is honoured as a refusal -----


def test_challenge_response_is_honoured_as_a_refusal() -> None:
    # §26 Rule 4 / SIG-INGEST-036/037: a bot-management challenge (403) is recorded
    # as a disappearance, NEVER retried, proxied, or solved. The run yields no
    # claims and a first-class disappearance datum instead.
    transport, report = _run_over("snapshot_2026_08.json", status=403)
    assert report.claims == []
    assert report.disappearances, "a challenge must be recorded as a disappearance"
    disappearance = report.disappearances[0]
    assert disappearance.event.failing_status == "access_restricted"
    assert disappearance.task["task_type"] == "source_disappeared"


def test_the_fetcher_never_defeats_a_challenge() -> None:
    # The shared politeness layer raises rather than working around a challenge; the
    # connector holds no HTTP client of its own and adds no circumvention (Rule 4).
    transport = _StaticTransport(_fixture_bytes("snapshot_2026_08.json"), status=429)
    fetcher = PoliteFetcher(
        connector_name="flock_portal", connector_version="1.0.0", transport=transport
    )
    with pytest.raises(ChallengeEncountered):
        fetcher.fetch("https://eyesonflock.com/api/v1/data")


# --- AC: separate CC BY-SA compartment; merging with the CC-BY graph fails ----


def test_rows_land_in_the_cc_by_sa_portal_compartment() -> None:
    # SIG-INGEST-035 / SIG-LIC-004a: every row lands in the CC-BY-SA-4.0 portal
    # compartment, never the CC-BY sig_graph.
    _, report = _run_over("snapshot_2026_08.json")
    claims = _claims(report)
    assert claims
    for c in claims:
        assert c["license"] == CC_BY_SA_LICENSE
        assert c["compartment"] == PORTAL_COMPARTMENT
        assert c["source_id"] == EYES_ON_FLOCK_SOURCE_ID


def test_export_merging_portal_with_the_cc_by_graph_fails_the_build() -> None:
    # SIG-LIC-004a / SIG-LIC-010: CC-BY-SA-4.0 (portal) and CC-BY-4.0 (Atlas / SIG
    # graph) are mutually incompatible — merging them into one export fails.
    with pytest.raises(LicenseIncompatibilityError):
        assert_export_compatible([EYES_ON_FLOCK_SOURCE_ID, _ATLAS_SOURCE_ID])


def test_portal_compartment_alone_exports_under_cc_by_sa() -> None:
    assert assert_export_compatible([EYES_ON_FLOCK_SOURCE_ID]) == CC_BY_SA_LICENSE


# --- AC: change detection keys on the snapshot field, not fetch time ----------


def test_observed_at_is_the_upstream_snapshot_date_not_fetch_time() -> None:
    # SIG-INGEST-030c: observed_at is the upstream data_last_updated (2026-08-15),
    # NOT the transport's retrieved_at (2027-01-01).
    _, report = _run_over("snapshot_2026_08.json")
    dated = [c for c in _claims(report) if "observed_at" in c]
    assert dated
    for c in dated:
        assert c["observed_at"] == date(2026, 8, 15)


def test_declared_freshness_is_recorded_but_not_used_as_observed_at() -> None:
    # §23.4: portal_last_updated_declared is the portal's own claim about freshness;
    # it is recorded, but never trusted as observed_at.
    _, report = _run_over("snapshot_2026_08.json")
    declared = [
        c for c in _claims(report) if c.get("predicate_id") == "portal_last_updated_declared"
    ]
    assert declared
    for c in declared:
        assert c["raw_value"] == "2026-08-15"
        # The declared-freshness claim itself carries no observed_at (it is not an
        # observation time — it is a claim about the upstream's own freshness).
        assert "observed_at" not in c


def test_is_poll_due_keys_on_the_snapshot_and_respects_the_refresh_cadence() -> None:
    # SIG-INGEST-030c: SIG must not poll faster than the upstream refreshes, and the
    # decision keys on the snapshot field, not the wall clock.
    # First poll (nothing observed yet): due.
    assert is_poll_due(date(2026, 8, 15), date(2026, 8, 15), None) is True
    # Upstream snapshot has NOT advanced and the refresh window has NOT elapsed: no.
    assert is_poll_due(date(2026, 8, 15), date(2026, 8, 15), date(2026, 8, 15)) is False
    # Upstream snapshot advanced: due (there is new information).
    assert is_poll_due(date(2026, 9, 15), date(2026, 8, 20), date(2026, 8, 15)) is True
    # Snapshot unchanged but the refresh window (1 day) has elapsed: due to re-check.
    assert is_poll_due(date(2026, 8, 15), date(2026, 8, 17), date(2026, 8, 15)) is True


# --- AC: historical back-fill from archived captures --------------------------


def test_backfill_from_an_archived_capture_keys_observed_at_on_the_snapshot() -> None:
    # SIG-INGEST-030b: an archived (Wayback) capture is a first-class target, and its
    # observed_at is the archived snapshot's own date (2025-11-02), not fetch time.
    _, report = _run_over("wayback_2025_11.json")
    dated = [c for c in _claims(report) if "observed_at" in c]
    assert dated
    for c in dated:
        assert c["observed_at"] == date(2025, 11, 2)
    # The back-fill produced real portal claims (it is not treated differently).
    cameras = [c for c in _claims(report) if c.get("predicate_id") == "active_device_count"]
    assert cameras and cameras[0]["value"] == 60


# --- AC: ai_training_permitted = false, recorded and enforced -----------------


def test_ai_training_is_recorded_false_on_every_row() -> None:
    # SIG-LIC-004b: the grant is stamped explicitly on every row and is False.
    _, report = _run_over("snapshot_2026_08.json")
    claims = _claims(report)
    assert claims
    for c in claims:
        assert c["ai_training_permitted"] is False


def test_ai_training_gate_refuses_this_source() -> None:
    # SIG-LIC-004b/004c: the source's rights do not grant AI training, so the
    # training gate refuses to route it to a training pipeline.
    rights = get(EYES_ON_FLOCK_SOURCE_ID).rights
    assert rights.ai_training_permitted is False
    with pytest.raises(TrainingNotPermitted):
        assert_training_allowed(rights)


# --- AC: portal disappearance produces an event and a task --------------------


def test_portal_disappearance_produces_an_event_and_a_task() -> None:
    # SIG-INGEST-035: a portal present before and absent now yields a
    # portal_exists=False event and a source_disappeared task.
    prev = portal_slugs(_fixture_json("snapshot_2026_08.json"))
    cur = portal_slugs(_fixture_json("snapshot_2026_09.json"))
    rows = detect_portal_changes(
        prev, cur, current_snapshot_date=date(2026, 9, 15), previous_snapshot_date=date(2026, 8, 15)
    )
    disappearance_events = [
        c for c in rows if c.get("predicate_id") == "portal_exists" and c["value"] is False
    ]
    assert len(disappearance_events) == 1
    gone = disappearance_events[0]
    assert gone["subject_id"] == portal_id("tulsa-pd")
    assert gone["event_class"] == "artifact_event"
    assert gone["compartment"] == PORTAL_COMPARTMENT
    tasks = [c for c in rows if c.get("task_type") == PORTAL_DISAPPEARED_TASK]
    assert len(tasks) == 1
    assert tasks[0]["subject_id"] == portal_id("tulsa-pd")


def test_portal_appearance_produces_an_event_and_a_no_known_deployment_task() -> None:
    # SIG-INGEST-035: portal appeared / no known deployment handled.
    prev = portal_slugs(_fixture_json("snapshot_2026_08.json"))
    cur = portal_slugs(_fixture_json("snapshot_2026_09.json"))
    rows = detect_portal_changes(prev, cur, current_snapshot_date=date(2026, 9, 15))
    appeared = [c for c in rows if c.get("predicate_id") == "portal_exists" and c["value"] is True]
    assert [c["subject_id"] for c in appeared] == [portal_id("newcity-pd")]
    tasks = [c for c in rows if c.get("task_type") == PORTAL_APPEARED_TASK]
    assert len(tasks) == 1 and tasks[0]["subject_id"] == portal_id("newcity-pd")


def test_a_fetched_portal_emits_a_portal_exists_true_claim() -> None:
    _, report = _run_over("snapshot_2026_08.json")
    exists = [
        c
        for c in _claims(report)
        if c.get("predicate_id") == "portal_exists" and c["value"] is True
    ]
    subjects = {c["subject_id"] for c in exists}
    assert subjects == {portal_id("okc-pd"), portal_id("tulsa-pd"), portal_id("smallville-pd")}


# --- AC: snapshot diffing produces per-field change events (via P08.2) ---------


def test_snapshot_diff_produces_per_field_change_events_via_p08_2() -> None:
    # SIG-RECON-045: consecutive captures diffed at the extracted-field level, each
    # event carrying BOTH values and BOTH dates, using P08.2's reconciler.
    aug = _fixture_json("snapshot_2026_08.json")
    sep = _fixture_json("snapshot_2026_09.json")
    okc_aug = next(p for p in aug["portals"] if p["slug"] == "okc-pd")
    okc_sep = next(p for p in sep["portals"] if p["slug"] == "okc-pd")
    events = diff_portal_snapshots(
        [
            portal_capture(okc_aug, capture_digest="digest-aug"),
            portal_capture(okc_sep, capture_digest="digest-sep"),
        ]
    )
    assert events
    assert all(isinstance(e, FieldChangeEvent) for e in events)
    by_field = {e.field: e for e in events}
    # total_cameras 100 -> 120, with both dates on the event.
    cams = by_field["total_cameras"]
    assert cams.old_value == 100 and cams.new_value == 120
    assert cams.old_date == date(2026, 8, 15) and cams.new_date == date(2026, 9, 15)
    assert cams.artifact_id == portal_id("okc-pd")
    # data_retention 30 -> 45 also detected.
    assert by_field["data_retention"].old_value == 30
    assert by_field["data_retention"].new_value == 45


# --- AC: sharing edges — configured access only, directional, blanks negative --


def test_sharing_edges_are_configured_access_directional_single_snapshot() -> None:
    # SIG-ONTO-042/044, SIG-RECON-034/036: configured access only, directional,
    # single-snapshot edges carry valid_from_kind='unknown'.
    portals = _fixture_json("snapshot_2026_08.json")["portals"]
    result = reconcile_portal_sharing(portals)
    assert result.edges
    for edge in result.edges:
        assert edge.access_kind == "configured_access"
        assert edge.valid_from_kind == "unknown"
    # okc-pd -> tulsa-pd is a directional configured-access edge.
    okc_to_tulsa = [e for e in result.edges if e.from_org == "okc-pd" and e.to_org == "tulsa-pd"]
    assert okc_to_tulsa


def test_blank_sharing_cells_are_negatives_not_unknown_edges() -> None:
    # §23.4: blank cells are negatives. tulsa-pd and smallville-pd list no partners,
    # so they originate NO sharing edges (not an "unknown" edge).
    portals = _fixture_json("snapshot_2026_08.json")["portals"]
    obs = sharing_observations(portals)
    originators = {o.from_org for o in obs}
    assert "tulsa-pd" not in originators
    assert "smallville-pd" not in originators


def test_sharing_asymmetry_is_a_finding_via_the_p08_2_reconciler() -> None:
    # SIG-RECON-035: okc-pd lists tulsa-pd, but tulsa-pd does not reciprocate — an
    # asymmetry finding + research task, emitted by the §29.3 reconciler.
    portals = _fixture_json("snapshot_2026_08.json")["portals"]
    result = reconcile_portal_sharing(portals)
    asymmetries = [c for c in result.contradictions if c.contradiction_type == SHARING_ASYMMETRY]
    assert asymmetries
    assert result.tasks
    assert any(t.task_type == "resolve_sharing_asymmetry" for t in result.tasks)


def test_connector_streams_only_deterministic_edges_for_sharing() -> None:
    # The connector's own claim stream carries the reconciled edges (deterministic);
    # asymmetry findings/tasks are the §29.3 reconciler's to emit (owned by P08.2),
    # so they are not folded into the connector's non-reproducible L1 output.
    _, report = _run_over("snapshot_2026_08.json")
    edges = _by_kind(_claims(report), "configured_access_edge")
    assert edges
    for e in edges:
        assert e["access_kind"] == "configured_access"
        assert e["valid_from_kind"] == "unknown"
        assert e["predicate_id"] == "configured_sharing_partner"


# --- predicate allowlist + forbidden write-set --------------------------------


def test_predicate_allowlist_and_forbidden_genres() -> None:
    allow = predicate_allowlist()
    assert "portal_exists" in allow and "active_device_count" in allow
    assert is_predicate_allowed("configured_retention_days")
    for forbidden in ("executed_contract", "fixed_asset_location", "per_search_row"):
        assert not is_predicate_allowed(forbidden)
        with pytest.raises(PredicateNotAllowed):
            assert_predicate_allowed(forbidden)
    genres = set(forbidden_predicate_genres())
    assert genres == {"contract_fact", "device_geometry", "per_search_row", "per_plate_row"}


def test_no_row_writes_a_predicate_outside_the_allowlist() -> None:
    # §23.4 / §18.1: MUST NOT write contract facts, device geometry, or any
    # per-search / per-plate row. Every claim/edge predicate is in the allowlist.
    _, report = _run_over("snapshot_2026_08.json")
    allow = predicate_allowlist()
    for c in _claims(report):
        if "predicate_id" in c:
            assert c["predicate_id"] in allow, c["predicate_id"]
    # No per-search / per-plate columns leak into any row.
    for c in _claims(report):
        for banned in ("plate", "search_id", "trip", "vehicle_id"):
            assert banned not in c


# --- SIG-INGEST-031 fallbacks -------------------------------------------------


def test_the_three_fallback_routes_are_retained_and_named() -> None:
    routes = fallback_routes()
    assert set(routes) == {"records_acquisition", "contributor_capture", "partner_archive"}
    # A challenge-defeating crawler is explicitly NOT a fallback route.
    for spec in routes.values():
        assert "challenge" not in spec["description"].lower()
        assert "circumvent" not in spec["description"].lower()


def test_missing_aggregator_fields_route_to_the_fallbacks() -> None:
    # SIG-INGEST-031: smallville-pd has no retention, no prohibited_uses, and no
    # sharing data, so all three fallback channels are routed to.
    smallville = next(
        p for p in _fixture_json("snapshot_2026_08.json")["portals"] if p["slug"] == "smallville-pd"
    )
    tasks = fallback_tasks_for_gaps(smallville, "smallville-pd")
    types = {t["task_type"] for t in tasks}
    assert types == {"records_acquisition", "contributor_capture", "partner_archive"}


def test_a_complete_portal_routes_to_no_fallback() -> None:
    portals = _fixture_json("snapshot_2026_08.json")["portals"]
    okc = next(p for p in portals if p["slug"] == "okc-pd")
    assert fallback_tasks_for_gaps(okc, "okc-pd") == []


# --- field mapping, provenance, append-only -----------------------------------


def test_windowed_usage_counters_carry_their_window() -> None:
    # SIG-RECON-011: the rolling usage statistics are windowed, not cumulative.
    _, report = _run_over("snapshot_2026_08.json")
    windowed = {
        "vehicles_detected_windowed_count",
        "hotlist_hit_windowed_count",
        "usage_search_windowed_count",
    }
    hits = [c for c in _claims(report) if c.get("predicate_id") in windowed]
    assert hits
    for c in hits:
        assert c["windowed"] is True
        assert c["window_months"] == 1


def test_rows_preserve_attribution_and_are_append_only() -> None:
    _, report = _run_over("snapshot_2026_08.json")
    attribution = get(EYES_ON_FLOCK_SOURCE_ID).rights.attribution
    for c in _claims(report):
        assert c["source_attribution"] == attribution
        # Append-only (P1-P3): no current-value / authoritative flags.
        assert "is_current" not in c
        assert "authoritative" not in c


def test_raw_values_are_preserved_beside_typed_values() -> None:
    _, report = _run_over("snapshot_2026_08.json")
    cams = next(c for c in _claims(report) if c.get("predicate_id") == "active_device_count")
    assert cams["value"] == 100
    assert cams["raw_value"] == 100
    assert cams["extracted_field"] == "total_cameras"


def test_claim_set_is_reproducible_across_runs() -> None:
    # SIG-INGEST-003: the post-capture stages are pure functions of the capture, so
    # two runs over the same bytes fingerprint identically (modulo the generated
    # claim_id / transaction time the fingerprint excludes).
    from evidence.ingest_run import claim_set_fingerprint

    _, first = _run_over("snapshot_2026_08.json")
    _, second = _run_over("snapshot_2026_08.json")
    assert claim_set_fingerprint(first.claims) == claim_set_fingerprint(second.claims)


def test_fetch_carries_a_descriptive_user_agent() -> None:
    transport, _ = _run_over("snapshot_2026_08.json")
    assert transport.user_agents
    ua = transport.user_agents[0]
    assert ua.startswith("flock_portal/1.0.0") and "+" in ua


# --- the structural canary ----------------------------------------------------


def test_canary_passes_on_the_committed_fixtures() -> None:
    for name in ("snapshot_2026_08.json", "snapshot_2026_09.json", "wayback_2025_11.json"):
        assert canary_findings(parse_json(_fixture_bytes(name))) == []


def test_canary_flags_structural_drift() -> None:
    assert canary_findings({"summary": {}}) == ["missing top-level 'portals' array"]
    assert "not an array" in " ".join(canary_findings({"summary": {}, "portals": {}}))
    empty_slug = {"summary": {}, "portals": [{"slug": ""}]}
    assert any("empty" in f for f in canary_findings(empty_slug))


# --- vocabulary is versioned data ---------------------------------------------


def test_vocabulary_is_versioned_data() -> None:
    assert vocab_version() == vocab()["vocab_version"]
    assert snapshot_field_name() == "data_last_updated"
    assert portal_snapshot_date({"data_last_updated": "2026-08-15"}) == date(2026, 8, 15)
    assert portal_snapshot_date({"data_last_updated": ""}) is None
