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


def test_per_fetch_stays_unwritten_for_row_312() -> None:
    """J3's 'when present' clause: the ``per_fetch`` column lands in this
    change but its PKG-12 telemetry writer is row 312's (P35.34) — these
    writers leave the field absent (NULL → not_recorded), never guessed."""
    fields = fetch_fields({"urls": ["https://h.test/x"], "status_codes": [200]})
    assert "per_fetch" not in fields
    doc = {
        "kind": "scheduled-ingest",
        "source": "s",
        "outcome": "ok",
        "started_at": "2026-09-01T00:00:00+00:00",
        "duration_seconds": 1.0,
        "fetch_record": {"urls": ["https://h.test/x"], "status_codes": [200]},
    }
    assert "per_fetch" not in fields_for_run_row(doc, link_basis="backfill:sole-candidate")


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
