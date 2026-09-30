# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P31.2 / ADR-109: the WORM run-row → completion matching rules (pure, no DB).

The real-PG backfill (append + +0 re-run + shaping read-back) is
``tests/db/test_run_completion.py``; here every matching rule in
``ops.run_completion`` is pinned deterministically, including each reason a row is
left unmatched rather than guessed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from ops.run_completion import (
    RunCandidate,
    completion_status_for,
    parse_run_row,
    plan_backfill,
    read_worm_rows,
)

T0 = datetime(2026, 9, 19, 6, 0, tzinfo=UTC)
CONNECTORS = {"camreg_a": "dot_511", "camreg_b": "dot_511", "ccops_x": "gmd"}


def _doc(
    source: str = "camreg_a",
    *,
    outcome: str = "ok",
    start: datetime = T0,
    duration: float = 60.0,
    claims_added: int = 5,
    kind: str = "scheduled-ingest",
    fetch_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "source": source,
        "mode": "live",
        "outcome": outcome,
        "started_at": start.isoformat(timespec="seconds"),
        "duration_seconds": duration,
        "claims_added": claims_added,
        "fetch_record": fetch_record if fetch_record is not None else {},
    }


def _row(uri: str = "gs://b/ops/runs/camreg_a/1.json", **kw: Any):  # type: ignore[no-untyped-def]
    return parse_run_row(uri, _doc(**kw), connector_for_source=CONNECTORS)


RUN_A = RunCandidate("run-a", "dot_511", T0 - timedelta(days=1))


def test_status_mapping_mirrors_the_pipeline() -> None:
    assert completion_status_for(_doc()) == "ok"
    assert completion_status_for(_doc(fetch_record={"disappearances": [{"x": 1}]})) == "partial"
    assert completion_status_for(_doc(fetch_record={"budget_reached": True})) == "partial"
    assert completion_status_for(_doc(outcome="quota_reached")) == "quota_reached"
    for failed in ("error", "content_drift", "politeness_refusal"):
        assert completion_status_for(_doc(outcome=failed)) == "failed"
    for refused in ("gate_refused", "no_live_targets"):
        assert completion_status_for(_doc(outcome=refused)) is None
    assert completion_status_for(_doc(outcome="something_new")) is None  # never guessed


def test_finished_at_is_the_rows_own_start_plus_duration() -> None:
    row = _row(duration=90.5)
    assert row.finished_at == T0 + timedelta(seconds=90.5)


def test_connector_prefers_the_fetch_record_then_the_registry_map() -> None:
    assert _row(fetch_record={"connector": "procurement"}).connector == "procurement"
    assert _row().connector == "dot_511"
    assert _row(source="unknown_src").connector is None


def test_claims_in_window_match_carries_the_counted_claims() -> None:
    row = _row()
    plan = plan_backfill([row], [RUN_A], {(row.uri, "run-a"): 42})
    assert [(m.run_id, m.claims_inserted, m.basis) for m in plan.matched] == [
        ("run-a", 42, "claims-in-window")
    ]
    assert plan.unmatched == []


def test_sole_candidate_match_for_a_clean_run_with_no_new_claims() -> None:
    row = _row(claims_added=5)
    plan = plan_backfill([row], [RUN_A], {})
    assert [(m.run_id, m.claims_inserted, m.basis) for m in plan.matched] == [
        ("run-a", 0, "sole-candidate")
    ]


def test_every_unprovable_row_is_unmatched_with_a_reason() -> None:
    later_run = RunCandidate("run-late", "gmd", T0 + timedelta(days=2))
    rows = [
        _row("gs://b/1", outcome="gate_refused"),
        _row("gs://b/2", source="unknown_src"),
        _row("gs://b/3", source="ccops_x"),  # its connector's only run started later
        _row("gs://b/4", source="camreg_b", outcome="error", claims_added=0),
        _row("gs://b/5", source="camreg_b", start=T0 + timedelta(hours=2), claims_added=0),
        _row("gs://b/6", source="camreg_b", start=T0 + timedelta(hours=4), kind="p265-sweep"),
    ]
    plan = plan_backfill(rows, [RUN_A, later_run], {})
    reasons = {u.uri: u.reason for u in plan.unmatched}
    assert plan.matched == []
    assert "not an ingest execution" in reasons["gs://b/1"]
    assert "no connector" in reasons["gs://b/2"]
    assert "had started by the row's finish" in reasons["gs://b/3"]
    assert "no proof it touched a run" in reasons["gs://b/4"]
    assert "no claim handed to the sink" in reasons["gs://b/5"]
    assert "no claim handed to the sink" in reasons["gs://b/6"]


def test_a_failed_run_that_wrote_claims_is_matched_as_failed() -> None:
    row = _row(outcome="error", claims_added=0)
    plan = plan_backfill([row], [RUN_A], {(row.uri, "run-a"): 7})
    assert [(m.row.status, m.claims_inserted) for m in plan.matched] == [("failed", 7)]


def test_ambiguity_is_never_resolved_by_guessing() -> None:
    run_b = RunCandidate("run-b", "dot_511", T0 - timedelta(hours=1))
    row = _row()
    both = plan_backfill([row], [RUN_A, run_b], {(row.uri, "run-a"): 1, (row.uri, "run-b"): 1})
    assert both.matched == [] and "ambiguous" in both.unmatched[0].reason
    neither = plan_backfill([row], [RUN_A, run_b], {})
    assert neither.matched == [] and "2 candidate runs" in neither.unmatched[0].reason
    # Claims isolate one of the two candidates: that run is proven.
    one = plan_backfill([row], [RUN_A, run_b], {(row.uri, "run-b"): 3})
    assert [m.run_id for m in one.matched] == ["run-b"]


def test_overlapping_windows_of_one_source_are_both_unmatched() -> None:
    a = _row("gs://b/a", duration=600)
    b = _row("gs://b/b", start=T0 + timedelta(seconds=300))
    plan = plan_backfill([a, b], [RUN_A], {("gs://b/a", "run-a"): 1, ("gs://b/b", "run-a"): 1})
    assert plan.matched == []
    assert {u.uri for u in plan.unmatched} == {"gs://b/a", "gs://b/b"}


def test_a_row_completed_live_is_skipped() -> None:
    row = _row()
    plan = plan_backfill([row], [RUN_A], {}, live_uris=[row.uri])
    assert plan.skipped_live == [row.uri] and plan.matched == [] and plan.unmatched == []


def test_replay_runs_are_never_candidates() -> None:
    row = _row()
    replay = RunCandidate("run-r", "dot_511", T0 - timedelta(days=1), is_replay=True)
    plan = plan_backfill([row], [replay], {(row.uri, "run-r"): 5})
    assert plan.matched == [] and "had started" in plan.unmatched[0].reason


def test_read_worm_rows_names_each_row_by_its_gs_uri() -> None:
    import json

    class _Bucket:
        bucket = "proj-sig-restricted"
        objects = {
            "ops/runs/camreg_a/2026-09-19/a.json": json.dumps(_doc()).encode(),
            "ops/runs/camreg_a/2026-09-19/notes.txt": b"ignored",
        }

        def list_objects(self, prefix: str) -> list[str]:
            assert prefix == "ops/runs/"
            return list(self.objects)

        def get_object(self, name: str) -> bytes:
            return self.objects[name]

    rows = read_worm_rows(_Bucket(), "ops/runs", connector_for_source=CONNECTORS)
    assert [r.uri for r in rows] == ["gs://proj-sig-restricted/ops/runs/camreg_a/2026-09-19/a.json"]


def test_cli_refuses_without_a_dsn_or_a_bucket(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    from ops import cli

    for var in ("SIG_STAGING_DSN", "SIG_PG_USER", "SIG_OPS_GCS_BUCKET"):
        monkeypatch.delenv(var, raising=False)
    assert cli.main(["backfill-run-completions", "--dry-run"]) == 2
    assert "needs --dsn" in capsys.readouterr().out
    assert cli.main(["backfill-run-completions", "--dsn", "postgresql://x", "--dry-run"]) == 2
    assert "needs --gcs-bucket" in capsys.readouterr().out


def test_a_row_nested_inside_a_long_window_is_ambiguous_too() -> None:
    # A spans 0-100 s; B (10-20 s) and C (50-60 s) both sit inside it. C does not
    # overlap its neighbour B, but it overlaps A — all three are unmatched.
    a = _row("gs://b/a", duration=100)
    b = _row("gs://b/b", start=T0 + timedelta(seconds=10), duration=10)
    c = _row("gs://b/c", start=T0 + timedelta(seconds=50), duration=10)
    counts = {(u, "run-a"): 1 for u in ("gs://b/a", "gs://b/b", "gs://b/c")}
    plan = plan_backfill([a, b, c], [RUN_A], counts)
    assert plan.matched == []
    assert {u.uri for u in plan.unmatched} == {"gs://b/a", "gs://b/b", "gs://b/c"}
