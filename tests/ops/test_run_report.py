# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Unit proof of the ingest-run report field derivation (P35.32 / J3 §3.3
item 1, K10 §18 C-13/C-14) — no DB needed:

* robots outcomes fold to the closed S-13 vocabulary across all three
  recorded decision shapes;
* refusal classes count refusals + politeness markers + quarantine
  count-by-reason (payload never enters);
* ``per_fetch`` stays unwritten — the PKG-12 column lands in this change
  but its writer is row 312's (P35.34), J3's "when present" clause;
* every P31.2 unmatched reason maps to a ``unmatched:<slug>`` basis;
* the repo live-run records mint 'repo_record'/'git_only' rows;
* unevidenced values stay None (not_recorded), never fabricated zeros.
"""

from __future__ import annotations

from pathlib import Path

from ops.run_report import (
    REPO_RECORD_DIR,
    document_outcome_map,
    error_class_for,
    fetch_fields,
    fields_for_repo_record,
    fields_for_run_row,
    fields_for_scheduled_row,
    read_repo_records,
    refusal_class_map,
    robots_outcome_map,
    unmatched_link_basis,
)
from ops.scheduled import RunRow

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_robots_outcomes_fold_all_recorded_shapes() -> None:
    fr = {
        "robots_decisions": [
            {"example.org": "allowed"},  # connector {host: verdict}
            {"host": "probe.test", "decision": "unretrievable"},  # egress probe
            {"host": "cc.test", "outcome": "no_policy_4xx"},  # civicclerk era
            {"cc2.test": "disallowed"},
            {"unknown.test": "a_future_verdict"},  # unmapped: dropped
        ],
        "robots_disregarded": [
            {"url": "https://rogue.test/x", "host": "rogue.test", "verdict": "disallowed"}
        ],
    }
    assert robots_outcome_map(fr) == {
        "example.org": {"obeyed": 1},
        "probe.test": {"unavailable": 1},
        "cc.test": {"unavailable": 1},
        "cc2.test": {"disallowed": 1},
        "rogue.test": {"disregarded": 1},
    }
    assert robots_outcome_map({}) is None
    assert robots_outcome_map({"robots_decisions": []}) is None


def test_refusal_classes_count_and_never_copy_payload() -> None:
    fr = {
        "refusals": [
            {"detail": "robots.txt disallows 'c/1.0' from fetching 'https://x/y'"},
            {"detail": "robots.txt for 'h' is unretrievable; crawl refused"},
            {"detail": "some other refusal"},
        ],
        "politeness_refusal": "RobotsDisallowed: robots.txt disallows 'x'",
        "content_drift": "content drift for source 's': shape changed",
    }
    classes = refusal_class_map(fr, quarantine={"unknown_predicate": 2})
    assert classes == {
        "robots_disallow": 2,
        "robots_unavailable": 1,
        "politeness_refusal": 1,
        "content_drift": 1,
        "unknown_predicate": 2,
    }
    # Quarantine contributes count-by-reason only — the reason string, never
    # a payload field.
    assert "payload" not in repr(classes)
    assert refusal_class_map({}) is None


def test_gate_and_no_live_targets_reasons_land_as_classes() -> None:
    assert refusal_class_map({}, refusal_reason="gate_refused") == {"gate_refused": 1}
    fr = {"politeness_refusal": "NoLiveTargets: source 'x' has no live targets"}
    assert refusal_class_map(fr) == {"no_live_targets": 1}


def test_per_fetch_absent_records_write_null() -> None:
    """P35.34's writer is live: a fetch record that carries no per-fetch
    telemetry (pre-P35.34 rows, and any record where the layer recorded
    nothing) writes NULL — not_recorded, never a fabricated []."""
    fields = fetch_fields({"urls": ["https://h.test/x"], "status_codes": [200]})
    assert fields["per_fetch"] is None
    doc = {
        "kind": "scheduled-ingest",
        "source": "s",
        "outcome": "ok",
        "started_at": "2026-09-01T00:00:00+00:00",
        "duration_seconds": 1.0,
        "fetch_record": {"urls": ["https://h.test/x"], "status_codes": [200]},
    }
    assert fields_for_run_row(doc, link_basis="backfill:sole-candidate")["per_fetch"] is None


def test_unmatched_reasons_map_to_closed_slugs() -> None:
    assert (
        unmatched_link_basis(
            "outcome 'gate_refused' is not an ingest execution (nothing was written)"
        )
        == "unmatched:not_an_execution"
    )
    assert unmatched_link_basis("no connector is known for this source") == "unmatched:no_connector"
    assert (
        unmatched_link_basis("its window overlaps another run row of the same source (ambiguous)")
        == "unmatched:overlapping_window"
    )
    assert (
        unmatched_link_basis("no ingest_run of connector 'x' had started by the row's finish")
        == "unmatched:no_candidate_run"
    )
    assert (
        unmatched_link_basis("3 candidate runs hold claims in the window (ambiguous)")
        == "unmatched:ambiguous_claims_in_window"
    )
    assert (
        unmatched_link_basis(
            "failed with no claim recorded in its window: no proof it touched a run"
        )
        == "unmatched:failed_no_proof"
    )
    assert (
        unmatched_link_basis("no claim recorded in its window and no claim handed to the sink")
        == "unmatched:no_claims_recorded"
    )
    assert (
        unmatched_link_basis("2 candidate runs and no claim in the window (ambiguous)")
        == "unmatched:ambiguous_candidates"
    )
    assert unmatched_link_basis("something new") == "unmatched:unresolved"


def test_error_class_for_outcomes() -> None:
    assert error_class_for("error", "psycopg.OperationalError: connection lost") == (
        "db_connection_lost"
    )
    assert error_class_for("error", "unknown") == "unclassified_error"
    assert error_class_for("error", "HTTP 503 from upstream") == "upstream_http_503"
    assert error_class_for("content_drift", "", fetch_record={"content_drift": "d"}) == (
        "content_drift"
    )
    assert (
        error_class_for(
            "politeness_refusal",
            "",
            fetch_record={"politeness_refusal": "RobotsDisallowed: x"},
        )
        == "robots_disallow"
    )
    assert error_class_for("ok", "") is None
    assert error_class_for("gate_refused", "", refusal_reason="gate_refused") is None


def test_fields_for_run_row_carries_own_clock_and_emitted_count() -> None:
    doc = {
        "kind": "scheduled-ingest",
        "source": "s",
        "outcome": "ok",
        "started_at": "2026-09-01T00:00:00+00:00",
        "duration_seconds": 10.0,
        "claims_added": 9,
        "fetch_record": {"urls": ["https://h.test/x"], "status_codes": [200], "byte_counts": [3]},
    }
    fields = fields_for_run_row(doc, link_basis="backfill:sole-candidate", run_id="r1")
    assert fields["link_basis"] == "backfill:sole-candidate"
    assert fields["clock_basis"] == "run_row"  # the WORM row's clock, never 'db'
    assert fields["records_emitted"] == 9
    assert fields["fetches"] == 1
    # An empty doc leaves everything typed-not_recorded, never zero-shaped.
    empty = fields_for_run_row({}, link_basis="unmatched:no_candidate_run")
    assert empty["started_at"] is None
    assert empty["fetches"] is None
    assert empty["records_emitted"] is None
    assert empty["error_class"] is None


def test_fields_for_scheduled_row_live_basis() -> None:
    row = RunRow(
        kind="scheduled-ingest",
        source="s1",
        mode="live",
        outcome="ok",
        exit_code=0,
        started_at="2026-10-19T00:00:00+00:00",
        duration_seconds=5.0,
        claims_added=2,
        fetch_record={
            "urls": ["https://h.test/x"],
            "status_codes": [200],
            "byte_counts": [3],
            "fetches": 1,
        },
        ingest_run_id="run-1",
    )
    fields = fields_for_scheduled_row(row)
    assert fields["link_basis"] == "live"
    assert fields["clock_basis"] == "db"
    assert fields["run_id"] == "run-1"
    assert fields["fetches"] == 1 and fields["records_emitted"] == 2
    # A refused row (no ingest_run) keeps run_id None + run_row clock.
    refused = RunRow(
        kind="scheduled-ingest",
        source="s2",
        mode="live",
        outcome="gate_refused",
        exit_code=3,
        started_at="2026-10-19T00:01:00+00:00",
        duration_seconds=0.1,
        refusal_reason="gate_refused",
    )
    f2 = fields_for_scheduled_row(refused)
    assert f2["run_id"] is None and f2["clock_basis"] == "run_row"
    assert f2["refusal_classes"] == {"gate_refused": 1}
    assert f2["error_class"] is None  # a gate refusal is not an upstream error


def test_repo_records_link_repo_record_git_only() -> None:
    records = read_repo_records(REPO_ROOT / REPO_RECORD_DIR)
    assert records, "the pinned live-run records exist"
    for rec in records:
        fields = fields_for_repo_record(rec.doc)
        assert fields["link_basis"] == "repo_record"
        assert fields["clock_basis"] == "git_only"
        assert fields["run_id"] is None
    # A FetchRecord-shaped record carries its fetch fields.
    fr_record = next(
        r for r in records if r.doc.get("urls") or r.doc.get("claim_count") is not None
    )
    fields = fields_for_repo_record(fr_record.doc)
    assert fields["records_emitted"] == fr_record.doc.get(
        "claims_added", fr_record.doc.get("claim_count")
    )


def test_repo_record_quota_probe_records_quota_class() -> None:
    doc = {
        "code": "900804",
        "message": "Message throttled out",
        "description": "You have exceeded your quota",
    }
    fields = fields_for_repo_record(doc)
    assert fields["link_basis"] == "repo_record" and fields["clock_basis"] == "git_only"
    assert fields["error_class"] == "quota_reached"
    assert fields["source_id"] is None  # not evidenced in the artifact


def test_fetch_fields_typed_not_recorded() -> None:
    fields = fetch_fields({})
    assert fields == {
        "fetches": None,
        "rate_limit_events": None,
        "disappearances": None,
        "robots_outcomes": None,
        "document_outcomes": None,
        "quota_reached": None,
        "budget_reached": None,
        "per_fetch": None,
        "upstream_reconciliation": None,
    }
    # An explicit fetch count wins; else the URL list's length; else NULL.
    assert fetch_fields({"fetches": 7})["fetches"] == 7
    assert fetch_fields({"urls": ["a", "b"]})["fetches"] == 2


def test_document_outcome_map_counts_outcomes_and_drift() -> None:
    fr = {
        "document_outcomes": [{"outcome": "matched"}, {"outcome": "matched"}, {"outcome": "empty"}],
        "document_drift": [{"url": "u"}],
    }
    assert document_outcome_map(fr) == {"matched": 2, "empty": 1, "drifted": 1}
    assert document_outcome_map({}) is None


def test_read_repo_records_reads_every_json_only(tmp_path: Path) -> None:
    (tmp_path / "x.json").write_text('{"a": 1}', encoding="utf-8")
    (tmp_path / "README.md").write_text("# not a record", encoding="utf-8")
    records = read_repo_records(tmp_path)
    assert len(records) == 1
    assert records[0].path.endswith("x.json") and records[0].doc == {"a": 1}
    # An unparseable record still yields a RepoRecord (empty doc →
    # not_recorded fields, never a crash).
    (tmp_path / "broken.json").write_text("{nope", encoding="utf-8")
    records = read_repo_records(tmp_path)
    assert len(records) == 2


# --- P35.34 / PKG-12 + SIG-CONF-009 ---------------------------------------------
#
# The per-fetch telemetry writer and the upstream-reconciliation pair: every
# URL passes the S-6 lane rules (host always; the full URL only where the lane
# + gate allow, else a path hash), the count pair records ``not_exposed`` /
# ``not_recorded`` honestly, the reason vocabulary is closed, and an
# unexplained >1 % difference lands ``unexplained`` — never explained-away.


def test_per_fetch_rows_carry_the_scrubbed_s6_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import ops.run_report as rr

    # An unregistered/unreadable source → ("unknown", False): host + path
    # hash, never the full URL.
    monkeypatch.setattr(rr, "_lane_for_source", lambda _s: ("unknown", False))
    fields = fetch_fields(
        {
            "per_fetch": [
                {
                    "url": "https://portal.example/list?page=3&key=secret-token",
                    "kind": "content",
                    "status": 200,
                    "bytes": 1024,
                    "fetched_at": "2026-10-01T00:00:00+00:00",
                    "duration_ms": 41,
                }
            ]
        },
        source_id="not_a_registered_source",
    )
    entry = fields["per_fetch"][0]
    assert entry["host"] == "portal.example"
    assert "url" not in entry and entry["path_sha256"]
    assert entry["status"] == 200 and entry["bytes"] == 1024
    assert entry["duration_ms"] == 41
    assert entry["fetched_at"] == "2026-10-01T00:00:00+00:00"
    assert entry["kind"] == "content"


def test_per_fetch_full_url_only_where_the_lane_allows(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import ops.run_report as rr

    entries = [
        {"url": "https://portal.example/list?key=tok", "kind": "content", "status": 200, "bytes": 9}
    ]
    monkeypatch.setattr(rr, "_lane_for_source", lambda _s: ("raw-ok", True))
    row = fetch_fields({"per_fetch": entries}, source_id="s")["per_fetch"][0]
    assert row["url"] == "https://portal.example/list"  # credentials stripped (S-1)
    monkeypatch.setattr(rr, "_lane_for_source", lambda _s: ("link-only", True))
    row = fetch_fields({"per_fetch": entries}, source_id="s")["per_fetch"][0]
    assert "url" not in row and row["path_sha256"]
    # A refusal outcome row keeps its outcome token.
    entries[0]["outcome"] = "rights_reservation"
    row = fetch_fields({"per_fetch": entries}, source_id="s")["per_fetch"][0]
    assert row["outcome"] == "rights_reservation"


def test_per_fetch_absent_stays_null_a_recorded_empty_stays_empty() -> None:
    assert fetch_fields({"fetches": 0})["per_fetch"] is None
    assert fetch_fields({"per_fetch": []})["per_fetch"] == []


def test_upstream_reconciliation_exact_match_is_in_range() -> None:
    fr = {
        "document_outcomes": [
            {"url": "https://portal.example/t1", "total_items": 100, "returned_count": 100}
        ]
    }
    rec = fetch_fields(fr, records_emitted=100)["upstream_reconciliation"]
    assert rec["schema"] == "sig.upstream-reconciliation/1"
    pair = [p for p in rec["pairs"] if p["target"] != "run"][0]
    assert pair["upstream_count"] == 100 and pair["subjects_held"] == 100
    assert pair["difference_pct"] == 0.0 and pair["classification"] == "in_range"
    run_pair = [p for p in rec["pairs"] if p["target"] == "run"][0]
    assert run_pair["classification"] == "in_range"


def test_upstream_reconciliation_explained_difference_carries_a_reason() -> None:
    fr = {
        "document_outcomes": [
            {
                "url": "https://api.example/bills",
                "total_items": 1500,
                "returned_count": 25,
                "truncated": True,
            }
        ]
    }
    rec = fetch_fields(fr, records_emitted=25)["upstream_reconciliation"]
    pair = rec["pairs"][0]
    assert pair["difference_pct"] > 1.0
    assert pair["classification"] == "explained"
    assert pair["reason"] == "pagination_cap"


def test_upstream_reconciliation_unexplained_above_one_pct() -> None:
    fr = {
        "document_outcomes": [
            {"url": "https://portal.example/t1", "total_items": 100, "returned_count": 85}
        ]
    }
    rec = fetch_fields(fr, records_emitted=100)["upstream_reconciliation"]
    pair = rec["pairs"][0]
    assert pair["difference_pct"] == 15.0
    assert pair["classification"] == "unexplained"
    assert pair["reason"] is None


def test_upstream_reconciliation_at_one_pct_is_in_range() -> None:
    fr = {
        "document_outcomes": [
            {"url": "https://portal.example/t1", "total_items": 100, "returned_count": 99}
        ]
    }
    pair = fetch_fields(fr)["upstream_reconciliation"]["pairs"][0]
    assert pair["difference_pct"] == 1.0 and pair["classification"] == "in_range"


def test_upstream_reconciliation_not_exposed_is_a_recorded_value() -> None:
    # A run with fetch evidence but no upstream-declared count records the
    # not_exposed token on the run-level pair — never a guess.
    rec = fetch_fields(
        {"urls": ["https://a.example/x", "https://a.example/y"], "fetches": 2},
        records_emitted=7,
    )["upstream_reconciliation"]
    run_pair = [p for p in rec["pairs"] if p["target"] == "run"][0]
    assert run_pair["upstream_count"] == "not_exposed"
    assert run_pair["subjects_held"] == 7
    assert run_pair["classification"] == "not_evaluable"


def test_upstream_reconciliation_missing_held_count_is_not_evaluable() -> None:
    fr = {
        "document_outcomes": [{"url": "https://portal.example/t1", "total_items": 42}],
        "fetches": 1,
    }
    rec = fetch_fields(fr)["upstream_reconciliation"]
    pair = rec["pairs"][0]
    assert pair["upstream_count"] == 42
    assert pair["subjects_held"] == "not_recorded"
    assert pair["classification"] == "not_evaluable"
    # Part VIII: the pair target passes the same S-6 scrub as per_fetch —
    # host + path hash for an unresolved lane, never the raw path.
    assert pair["target"] == "portal.example"
    assert "url" not in pair and pair["path_sha256"]


def test_upstream_reconciliation_none_without_run_evidence() -> None:
    # A non-run artifact (the sam.gov quota probe shape) records no run —
    # the column stays NULL (not_recorded), never a fabricated empty object.
    assert fetch_fields({"message": "Message throttled out"})["upstream_reconciliation"] is None


def test_recon_reason_vocabulary_is_closed() -> None:
    import ops.run_report as rr

    for reason in rr.RECON_REASONS:
        assert rr.valid_recon_reason(reason)
    assert rr.valid_recon_reason("other:timed_out")
    assert not rr.valid_recon_reason("probably_dedup")
    assert not rr.valid_recon_reason("")


def test_recon_explicit_recorded_reason_wins() -> None:
    fr = {
        "document_outcomes": [
            {
                "url": "https://portal.example/t1",
                "total_items": 100,
                "returned_count": 60,
                "difference_reason": "withheld_rows",
            }
        ]
    }
    pair = fetch_fields(fr)["upstream_reconciliation"]["pairs"][0]
    assert pair["classification"] == "explained"
    assert pair["reason"] == "withheld_rows"


def test_run_level_pair_explains_via_run_quota() -> None:
    fr = {
        "document_outcomes": [
            {"url": "https://api.example/s1", "total_notice_count": 500, "items_count": 100}
        ],
        "quota_reached": True,
    }
    rec = fetch_fields(fr, records_emitted=100)["upstream_reconciliation"]
    run_pair = [p for p in rec["pairs"] if p["target"] == "run"][0]
    assert run_pair["classification"] == "explained"
    assert run_pair["reason"] == "other:quota_reached"


def test_fields_for_run_row_carries_per_fetch_and_reconciliation(
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    import ops.run_report as rr

    monkeypatch.setattr(rr, "_lane_for_source", lambda _s: ("unknown", False))
    doc = {
        "source": "fixture_source",
        "outcome": "ok",
        "claims_added": 3,
        "fetch_record": {
            "urls": ["https://fixture.example/a"],
            "per_fetch": [
                {
                    "url": "https://fixture.example/a",
                    "kind": "content",
                    "status": 200,
                    "bytes": 11,
                }
            ],
        },
    }
    fields = fields_for_run_row(doc, link_basis="backfill:sole-candidate")
    assert fields["per_fetch"] == [
        {
            "host": "fixture.example",
            "path_sha256": fields["per_fetch"][0]["path_sha256"],
            "kind": "content",
            "status": 200,
            "bytes": 11,
        }
    ]
    rec = fields["upstream_reconciliation"]
    run_pair = [p for p in rec["pairs"] if p["target"] == "run"][0]
    assert run_pair["upstream_count"] == "not_exposed"
    assert run_pair["subjects_held"] == 3


def test_fetch_record_to_dict_round_trips_per_fetch() -> None:
    from connectors.runner import FetchRecord

    rec = FetchRecord(
        source_id="s",
        connector="toy",
        mode="live",
        started_at="2026-10-19T00:00:00+00:00",
        duration_seconds=1.0,
        per_fetch=[{"url": "https://h.example/x", "kind": "content", "status": 200, "bytes": 5}],
    )
    doc = rec.to_dict()
    assert doc["per_fetch"] == [
        {"url": "https://h.example/x", "kind": "content", "status": 200, "bytes": 5}
    ]
    # Back-compat: the aggregate arrays still serialise beside it.
    assert "urls" in doc and "status_codes" in doc and "byte_counts" in doc
