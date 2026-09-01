# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `audit_structural` connector: the Flock audit-export layer (§23.7, P11.2).

Every acceptance criterion of P11.2 is pinned here against committed CSV fixtures
(SIG-PARSE-007): an organization audit (with plate/officer columns present, so the
§18.1 no-per-plate discipline is exercised against a realistic export), a
portal-public audit carrying a `Camera Count`, a network audit (a second,
non-interchangeable source type using alias columns), an event log, and a
`SharedNetworks.csv`. The connector is driven through the P04.1 framework and its
pure helpers are tested directly.
"""

from __future__ import annotations

import dataclasses
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest
from connectors.audit_structural import (
    AGENCY_AUDIT_SOURCE_ID,
    CELL_EMPTY,
    CELL_PRESENT,
    CELL_REDACTED,
    AuditStructuralConnector,
    PerRowLeak,
    PredicateNotAllowed,
    UnknownAuditSourceType,
    aggregate_search_events,
    assert_audit_source_type,
    assert_no_per_row_output,
    assert_predicate_allowed,
    audit_source_types,
    camera_count_observation,
    classify_cell,
    deduplicate_events,
    forbidden_output_columns,
    is_redacted,
    parse_csv,
    predicate_allowlist,
    reason_category,
    reconcile_audit_sharing,
    reconcile_camera_counts,
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
from reconcile.model import SHARING_ASYMMETRY, VALUE_DISAGREEMENT, CountClaim, Evidence

_FIX = Path(__file__).parent / "fixtures" / "audit_structural"
_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"


def _fixture_bytes(name: str) -> bytes:
    return (_FIX / name).read_bytes()


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
            media_type="text/csv",
            retrieved_at=datetime(2027, 1, 1),  # noqa: DTZ001 - deterministic test stamp
        )


def _run_over(fixture: str, *, file_kind: str, **target_extra: Any) -> Any:
    """Run the audit_structural connector end-to-end over one committed fixture."""
    transport = _StaticTransport(_fixture_bytes(fixture))
    fetcher = PoliteFetcher(
        connector_name="audit_structural", connector_version="1.0.0", transport=transport
    )
    # The seed row stays ingestion_permitted=false (SIG-INGEST-028); a reviewer
    # flips it to run, exactly as the other connector tests do.
    source = dataclasses.replace(get(AGENCY_AUDIT_SOURCE_ID), ingestion_permitted=True)
    url = f"https://eleutheria.example/records/{fixture}"
    target = {"id": fixture, "url": url, "file_kind": file_kind, **target_extra}
    ctx = RunContext(
        source=source,
        run=IngestRun("audit_structural", "1.0.0", "deadbeef", "r2", vocab_version(), ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": [target]},
    )
    return run(AuditStructuralConnector(), ctx)


def _by_kind(claims: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [c for c in claims if c.get("record_kind") == kind]


# --- registration -------------------------------------------------------------


def test_audit_structural_connector_is_registered() -> None:
    # SIG-INGEST-021: the connector self-registers on import under its name.
    assert "audit_structural" in registered_connectors()
    assert registered_connectors()["audit_structural"] is AuditStructuralConnector


# --- AC1: no per-search or per-plate row is produced anywhere (§18.1) ----------


def test_no_per_search_or_per_plate_row_is_produced() -> None:
    # §18.1 / SIG-STORE-025: the audit export carries Plate + Officer columns; the
    # connector reads the per-search rows transiently and emits ONLY aggregates.
    report = _run_over("organization_audit.csv", file_kind="organization_audit")
    claims = report.claims
    assert claims
    # Only structural record kinds leave — never a per-search / per-plate row.
    kinds = {c.get("record_kind") for c in claims}
    assert kinds <= {"usage_aggregate", "claim"}
    # The bright line is a schema property: no emitted row carries a forbidden column
    # (plate/officer/search_id/timestamp), and no plate value leaks into any value.
    banned = forbidden_output_columns()
    for c in claims:
        for key in c:
            k = str(key).lower()
            assert k not in banned and not any(b in k for b in banned), key
        blob = repr(c)
        for plate in ("ABC123", "XYZ789", "QRS111", "TUV222"):
            assert plate not in blob, plate
        for officer in ("J. Smith", "K. Doe", "L. Roe", "M. Poe"):
            assert officer not in blob, officer


def test_the_per_row_schema_gate_rejects_a_plate_bearing_row() -> None:
    # SIG-STORE-026: a claim capable of holding a plate is rejected at the boundary.
    with pytest.raises(PerRowLeak):
        assert_no_per_row_output([{"record_kind": "claim", "plate": "ABC123"}])
    with pytest.raises(PerRowLeak):
        assert_no_per_row_output([{"record_kind": "claim", "officer_name": "J. Smith"}])
    # An aggregate row (searching_org/count) is clean.
    assert_no_per_row_output([{"record_kind": "usage_aggregate", "searching_org": "X", "count": 3}])


def test_aggregates_count_distinct_searches_and_carry_direction() -> None:
    # §11.16: an aggregate is (searching_org -> source_org, period, count); the two
    # immigration searches in August aggregate to a count of 2, not collapsed to 1.
    report = _run_over("organization_audit.csv", file_kind="organization_audit")
    aggs = _by_kind(report.claims, "usage_aggregate")
    immigration = [
        a
        for a in aggs
        if a["reason_category"] == "immigration_enforcement"
        and a["searching_org"] == "Springfield PD"
    ]
    assert len(immigration) == 1
    agg = immigration[0]
    assert agg["count"] == 2
    assert agg["source_org"] == "Shelby County SO"
    assert agg["period"] == "2026-08"
    assert agg["search_scope"] == "state"


# --- AC2: audit `Camera Count` is an independent count claim (§23.7, §29.1) -----


def test_camera_count_is_an_independent_active_device_count_claim() -> None:
    report = _run_over("portal_public_audit.csv", file_kind="portal_public_audit")
    counts = [c for c in report.claims if c.get("predicate_id") == "active_device_count"]
    assert len(counts) == 1
    claim = counts[0]
    assert claim["value"] == 42
    assert claim["count_basis"] == "active"  # its own basis; reconciled, never merged
    assert claim["audit_source_type"] == "portal_public_audit"
    assert claim["raw_value"] == "42"


def test_redacted_camera_count_yields_no_fabricated_count() -> None:
    # Metro PD's Camera Count is `***` (redacted): a distinct withheld state, never
    # a fabricated count and never conflated with 0 (§3.1 no synthetic certainty).
    report = _run_over("portal_public_audit.csv", file_kind="portal_public_audit")
    counts = [c for c in report.claims if c.get("predicate_id") == "active_device_count"]
    subjects = {c["subject_id"] for c in counts}
    assert subjects == {"audit_org:Shelby County SO"}


def test_camera_count_is_reconciled_against_other_counts_never_merged_via_p08_2() -> None:
    # §29.1 / SIG-RECON-026: the audit Camera Count is one observation of the
    # `active` basis; P08.2 resolves it against a portal observation WITHOUT merging
    # (no summed "true count") — the disagreement is retained as a finding.
    subject = "audit_org:Shelby County SO"
    audit = camera_count_observation(subject, 42, date(2026, 8, 1), reliability="R2")
    portal = CountClaim(
        count_basis="active",
        value=50,
        reliability="R2",
        integrity="I1",
        observed_at=date(2026, 8, 10),
        genre="portal_snapshot",
        evidence=Evidence(
            source_id="eyes_on_flock",
            source_family="flock_portal",
            artifact_type="portal_snapshot",
            stable_locator=subject,
            capture_digest="",
            locator={},
        ),
        structured_exact=True,
    )
    result = reconcile_camera_counts([audit, portal], subject_id=subject, as_of=date(2026, 8, 15))
    active = result.resolutions["active"]
    # Resolved to ONE observation's value (the more direct portal snapshot), never
    # the sum — the two counts are not merged (SIG-RECON-026).
    assert active.value in (42, 50)
    assert active.value != 42 + 50
    assert active.value == 50  # portal_snapshot (D1) outweighs audit_log (D4)
    dissenting_values = {c.value for c in active.dissenting}
    assert 42 in dissenting_values  # the audit count is retained, not discarded
    assert any(c.contradiction_type == VALUE_DISAGREEMENT for c in result.contradictions)


# --- AC3: SharedNetworks edges — configured access, directional, blanks negative -


def test_sharednetworks_edges_are_configured_access_directional_single_snapshot() -> None:
    # SIG-ONTO-042/044, SIG-RECON-034/036: configured access only, directional,
    # single-snapshot edges carry valid_from_kind='unknown'.
    report = _run_over("SharedNetworks.csv", file_kind="shared_networks", observed_at="2026-08-01")
    edges = _by_kind(report.claims, "configured_access_edge")
    assert edges
    for e in edges:
        assert e["access_kind"] == "configured_access"
        assert e["valid_from_kind"] == "unknown"
        assert e["predicate_id"] == "configured_sharing_partner"
    directed = {(e["from_org"], e["to_org"]) for e in edges}
    assert ("Springfield PD", "Shelby County SO") in directed
    assert ("Springfield PD", "Metro PD") in directed


def test_blank_sharing_cells_are_negatives_not_unknown_edges() -> None:
    # §23.7: blank cells are negatives. Metro PD lists no partners in either
    # direction, so it originates NO outbound edge (not an "unknown" edge).
    parsed = parse_csv(_fixture_bytes("SharedNetworks.csv"))
    result = reconcile_audit_sharing(parsed, observed_at=date(2026, 8, 1))
    originators = {e.from_org for e in result.edges}
    assert "Metro PD" not in originators


def test_sharing_asymmetry_is_a_finding_via_the_p08_2_reconciler() -> None:
    # SIG-RECON-035: Springfield lists Metro, but Metro does not reciprocate — an
    # asymmetry finding + research task, emitted by the §29.3 reconciler (P08.2).
    parsed = parse_csv(_fixture_bytes("SharedNetworks.csv"))
    result = reconcile_audit_sharing(parsed, observed_at=date(2026, 8, 1))
    asymmetries = [c for c in result.contradictions if c.contradiction_type == SHARING_ASYMMETRY]
    assert asymmetries
    assert any(t.task_type == "resolve_sharing_asymmetry" for t in result.tasks)


def test_connector_streams_only_deterministic_edges_for_sharing() -> None:
    # The connector's own claim stream carries the reconciled edges (deterministic);
    # asymmetry findings/tasks are the §29.3 reconciler's to emit (owned by P08.2).
    report = _run_over("SharedNetworks.csv", file_kind="shared_networks", observed_at="2026-08-01")
    kinds = {c.get("record_kind") for c in report.claims}
    assert kinds == {"configured_access_edge"}


# --- AC4: `***` redaction is distinguished from empty (SIG-INGEST-046) ---------


def test_classify_cell_distinguishes_redacted_from_empty_and_present() -> None:
    assert classify_cell("***") == CELL_REDACTED
    assert classify_cell("") == CELL_EMPTY
    assert classify_cell("   ") == CELL_EMPTY
    assert classify_cell(None) == CELL_EMPTY
    assert classify_cell("Immigration") == CELL_PRESENT
    assert is_redacted("***") and not is_redacted("")


def test_reason_category_keeps_redacted_distinct_from_unspecified() -> None:
    # A redacted reason and a blank reason are DIFFERENT recorded states.
    assert reason_category("***") == "redacted"
    assert reason_category("") == "unspecified"
    assert reason_category("Immigration") == "immigration_enforcement"
    assert reason_category("something novel") == "other"


def test_redacted_and_empty_reasons_produce_distinct_aggregate_buckets() -> None:
    # SIG-INGEST-046: the `***` search and the blank-reason search land in DIFFERENT
    # aggregate buckets, and a distinct audit_cell_redacted record is emitted.
    report = _run_over("organization_audit.csv", file_kind="organization_audit")
    aggs = _by_kind(report.claims, "usage_aggregate")
    categories = {a["reason_category"] for a in aggs}
    assert "redacted" in categories
    assert "unspecified" in categories
    redaction_rows = [c for c in report.claims if c.get("predicate_id") == "audit_cell_redacted"]
    assert redaction_rows
    assert redaction_rows[0]["redacted_count"] == 1
    assert redaction_rows[0]["cell_state"] == CELL_REDACTED


# --- AC5: the four audit source types are non-interchangeable (§23.7) ----------


def test_the_four_audit_source_types_are_the_closed_set() -> None:
    assert audit_source_types() == (
        "organization_audit",
        "network_audit",
        "portal_public_audit",
        "event_log",
    )
    assert assert_audit_source_type("network_audit") == "network_audit"
    with pytest.raises(UnknownAuditSourceType):
        assert_audit_source_type("some_other_audit")


def test_every_aggregate_records_its_source_type_and_they_are_not_unioned() -> None:
    # §23.7: each aggregate carries its audit_source_type; org and network audits are
    # NOT silently merged — the source type is a distinguishing field on every row.
    org = _run_over("organization_audit.csv", file_kind="organization_audit")
    net = _run_over("network_audit.csv", file_kind="network_audit")
    org_aggs = _by_kind(org.claims, "usage_aggregate")
    net_aggs = _by_kind(net.claims, "usage_aggregate")
    assert org_aggs and net_aggs
    assert all(a["audit_source_type"] == "organization_audit" for a in org_aggs)
    assert all(a["audit_source_type"] == "network_audit" for a in net_aggs)
    # The network audit resolves its alias columns (network/searching_org/search_reason).
    net_agg = net_aggs[0]
    assert net_agg["source_org"] == "Regional ALPR Network"
    assert net_agg["reason_category"] == "amber_alert"
    assert net_agg["count"] == 2


def test_event_log_lands_dated_lifecycle_transitions_tagged_by_source_type() -> None:
    # §23.7 writes: event-log lifecycle transitions, recorded with their source type
    # (the §29.4 reconciliation preferring event-log transitions is owned by P08.2).
    report = _run_over("event_log.csv", file_kind="event_log")
    transitions = [
        c for c in report.claims if c.get("predicate_id") == "deployment_lifecycle_transition"
    ]
    assert len(transitions) == 3
    states = {t["value"]["state"] for t in transitions}
    assert states == {"activated", "firmware_update", "deactivated"}
    for t in transitions:
        assert t["audit_source_type"] == "event_log"
        assert t["subject_id"].startswith("audit_deployment:")


# --- §23.7 duplicate handling: overlapping exports deduped ---------------------


def test_overlapping_exports_are_deduplicated_by_window_block() -> None:
    # §23.7: two exports covering the same (source_org, searching_org, window) are a
    # double-cover — the second export's block is dropped (overlap), distinct
    # within-export searches are NOT.
    events = [
        {"searching_org": "A", "source_org": "B", "month": "2026-08", "export_id": "E1"},
        {"searching_org": "A", "source_org": "B", "month": "2026-08", "export_id": "E1"},
        {"searching_org": "A", "source_org": "B", "month": "2026-08", "export_id": "E2"},
    ]
    kept, overlap = deduplicate_events(events)
    assert len(kept) == 2  # both E1 events kept
    assert overlap == 1  # the E2 double-cover dropped
    aggs = aggregate_search_events(events, audit_source_type="organization_audit")
    assert sum(a.count for a in aggs) == 2


# --- predicate allowlist ------------------------------------------------------


def test_predicate_allowlist_is_enforced() -> None:
    allow = predicate_allowlist()
    assert "usage_search_aggregate" in allow and "active_device_count" in allow
    for forbidden in ("per_search_row", "plate_lookup", "officer_search"):
        with pytest.raises(PredicateNotAllowed):
            assert_predicate_allowed(forbidden)


# --- provenance, append-only, reproducibility ---------------------------------


def test_rows_carry_source_and_are_append_only() -> None:
    report = _run_over("organization_audit.csv", file_kind="organization_audit")
    for c in report.claims:
        assert c["source_id"] == AGENCY_AUDIT_SOURCE_ID
        assert c["vocab_version"] == vocab_version()
        # Append-only (P1-P3): no current-value / authoritative flags.
        assert "is_current" not in c
        assert "authoritative" not in c


def test_source_agency_provenance_travels_on_every_aggregate() -> None:
    # §23.7: every aggregate carries the export it came from and its requesting agency.
    report = _run_over(
        "organization_audit.csv",
        file_kind="organization_audit",
        requesting_agency="Springfield PD",
        export_id="EXP-2026-08",
    )
    aggs = _by_kind(report.claims, "usage_aggregate")
    assert aggs
    for a in aggs:
        assert a["requesting_agency"] == "Springfield PD"
        assert a["audit_export_id"] == "EXP-2026-08"


def test_claim_set_is_reproducible_across_runs() -> None:
    # SIG-INGEST-003: post-capture stages are pure; two runs over the same bytes
    # fingerprint identically (modulo the generated claim_id / transaction time).
    from evidence.ingest_run import claim_set_fingerprint

    first = _run_over("organization_audit.csv", file_kind="organization_audit")
    second = _run_over("organization_audit.csv", file_kind="organization_audit")
    assert claim_set_fingerprint(first.claims) == claim_set_fingerprint(second.claims)


def test_fetch_carries_a_descriptive_user_agent() -> None:
    transport = _StaticTransport(_fixture_bytes("organization_audit.csv"))
    fetcher = PoliteFetcher(
        connector_name="audit_structural", connector_version="1.0.0", transport=transport
    )
    fetcher.fetch("https://eleutheria.example/records/organization_audit.csv")
    assert transport.user_agents
    ua = transport.user_agents[0]
    assert ua.startswith("audit_structural/1.0.0") and "+" in ua


# --- the structural canary ----------------------------------------------------


def test_canary_passes_on_the_committed_fixtures() -> None:
    from connectors.audit_structural import canary_findings

    assert (
        canary_findings(
            parse_csv(_fixture_bytes("organization_audit.csv")), file_kind="organization_audit"
        )
        == []
    )
    assert (
        canary_findings(
            parse_csv(_fixture_bytes("SharedNetworks.csv")), file_kind="shared_networks"
        )
        == []
    )
    assert canary_findings(parse_csv(_fixture_bytes("event_log.csv")), file_kind="event_log") == []


def test_canary_flags_structural_drift() -> None:
    from connectors.audit_structural import canary_findings

    findings = canary_findings({"header": ["Nope"], "rows": []}, file_kind="organization_audit")
    assert findings


# --- vocabulary is versioned data ---------------------------------------------


def test_vocabulary_is_versioned_data() -> None:
    assert vocab_version() == vocab()["vocab_version"]
    assert vocab()["redaction_sentinel"] == "***"
