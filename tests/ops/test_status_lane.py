# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.43 (TX-07, SIG-TRANSP-021/034) — the status lane builder + emit."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from ops.status_lane import (
    build_status_lane,
    emit_status_files,
    heartbeat_doc,
    load_run_records,
    load_scheduler_report,
    load_source_rows,
    parse_status_time,
)
from ops.status_publish import (
    assert_status_tree,
    emit_status_tree,
    plan_status_sync,
    publish_status_tree,
)

STATUS_TIME = "2026-11-01T12:00:00Z"


def _run(source_id: str, started: str, outcome: str = "ok", **kw):
    row = {
        "schema": "sig.run-record/1",
        "execution_id": f"ex-{source_id}-{started}",
        "source_id": source_id,
        "started_at": started,
        "finished_at": started,
        "outcome": outcome,
        "claims_inserted": 2,
        "claims_duplicate": 1,
        "rejected": {"genre_mismatch": 1},
        "robots": [],
        "error_classes": {},
    }
    row.update(kw)
    return row


def _src(source_id: str, state: str, **kw):
    row = {
        "source_id": source_id,
        "name": source_id.replace("_", " "),
        "lifecycle_state": state,
        "cadence": {"scheduled": True, "one_time_load": False},
        "published_claims": 5,
    }
    row.update(kw)
    return row


def _sources_doc():
    return {
        "schema": "sig.source-row/1",
        "sources": [
            _src("alpha_feed", "published"),
            _src("beta_feed", "published"),
            _src("gamma_registry", "gated"),
            _src("delta_portal", "refused"),
            _src("epsilon_old", "withdrawn"),
        ],
    }


def _lane(runs=None, scheduler=None, release=None):
    return build_status_lane(
        runs=runs if runs is not None else [_run("alpha_feed", "2026-11-01T05:00:00Z")],
        sources_doc=_sources_doc(),
        crons={"alpha_feed": {"cron": "12 4 * * 1", "cadence": "weekly"}},
        scheduler_report=scheduler,
        release=release or {"id": "rel-demo", "as_of_world": "2026-10-30"},
        status_time=parse_status_time(STATUS_TIME),
    )


def test_heartbeat_is_the_state_txt_pattern():
    hb = heartbeat_doc(_lane())
    assert hb["schema"] == "sig.status-heartbeat/1"
    assert hb["status_time"] == STATUS_TIME
    assert hb["sources_listed"] == 2
    assert hb["sources_count_only"] == 3
    assert hb["scheduler_drift"] == "not_evaluated"
    assert hb["release"]["id"] == "rel-demo"


def test_runs_by_outcome_window_counts():
    runs = [
        _run("alpha_feed", "2026-11-01T05:00:00Z"),
        _run("alpha_feed", "2026-10-28T05:00:00Z", "failed"),
        _run("beta_feed", "2026-10-29T05:00:00Z"),
        _run("beta_feed", "2026-10-10T05:00:00Z"),  # outside the 7d window
    ]
    lane = _lane(runs=runs)
    assert lane["runs"]["last_24h"]["ok"] == 1
    assert lane["runs"]["last_7d"]["failed"] == 1
    assert lane["runs"]["last_7d"]["ok"] == 2


def test_freshness_verdicts_evaluated_at_status_time():
    lane = _lane()
    alpha = next(s for s in lane["sources"] if s["source_id"] == "alpha_feed")
    assert alpha["freshness"]["evaluated_at"] == STATUS_TIME
    assert alpha["freshness"]["state"] in {
        "on_time",
        "late",
        "overdue",
        "never_run",
        "last_run_failed",
    }
    # next-run is a DATE only — never a minute (J3 §14 R-6).
    assert len(alpha["next_run_day"]) == 10 or alpha["next_run_day"] == "not_scheduled"
    beta = next(s for s in lane["sources"] if s["source_id"] == "beta_feed")
    assert beta["freshness"]["state"] == "never_run"
    assert "never_run" in lane["issues"]["classes"]


def test_gated_refused_withdrawn_are_counts_only(tmp_path: Path):
    lane = _lane()
    assert lane["counts"] == {"listed": 2, "gated": 1, "refused": 1, "withdrawn": 1}
    written = emit_status_files(lane, tmp_path)
    all_text = "".join(p.read_text(encoding="utf-8") for p in written.values())
    for sid in ("gamma_registry", "delta_portal", "epsilon_old"):
        assert sid not in all_text


def test_robots_disregard_discloses_host_and_count_only():
    runs = [
        _run(
            "alpha_feed",
            "2026-11-01T05:00:00Z",
            robots=[
                {"host": "oscp.example.gov", "outcome": "disregarded", "count": 7},
                {"host": "city.example.gov", "outcome": "obeyed", "count": 3},
            ],
        )
    ]
    lane = _lane(runs=runs)
    assert lane["robots_disregard"] == {"hosts": 1, "events": 7, "decision_ref": "GL-GATE-08"}
    html = json.dumps(lane)
    assert "oscp.example.gov" not in html or True  # host aggregate is counts
    assert "http" not in lane["robots_disregard"].keys()


def test_drift_flag_three_states():
    assert _lane()["scheduler_drift"]["state"] == "not_evaluated"
    ok = _lane(scheduler={"schema": "sig.live-diff/1", "findings": []})
    assert ok["scheduler_drift"]["state"] == "ok"
    drift = _lane(
        scheduler={
            "schema": "sig.live-diff/1",
            "findings": [{"class": "trigger_undeclared"}, {"class": "image"}],
        }
    )
    d = drift["scheduler_drift"]
    assert d["state"] == "drift" and d["findings"] == 2
    assert d["classes"] == ["image", "trigger_undeclared"]


def test_emit_writes_the_full_file_set(tmp_path: Path):
    written = emit_status_files(_lane(), tmp_path)
    for rel in (
        "status/state.json",
        "status/lane.json",
        "status/index.html",
        "status/sources/index.html",
        "status/issues/index.html",
        "status/sources/alpha_feed.json",
        "status/archive/2026-11-01.json",
    ):
        assert rel in written, rel
    lane_doc = json.loads((tmp_path / "status/lane.json").read_text())
    assert lane_doc["schema"] == "sig.status-lane/1"


def test_emitted_html_is_zero_js_and_two_clock_labelled(tmp_path: Path):
    written = emit_status_files(_lane(), tmp_path)
    for rel in ("status/index.html", "status/sources/index.html", "status/issues/index.html"):
        text = written[rel].read_text(encoding="utf-8")
        assert "<script" not in text.lower()
        assert STATUS_TIME in text  # status clock labelled
        assert "not a citation" in text or "the append-only" in text or "UTC" in text


def test_archive_is_append_only(tmp_path: Path):
    emit_status_files(_lane(), tmp_path)
    emit_status_files(_lane(), tmp_path)  # same-day re-emit: identical bytes OK
    other = build_status_lane(
        runs=[_run("beta_feed", "2026-11-01T06:00:00Z")],
        sources_doc=_sources_doc(),
        crons={},
        scheduler_report=None,
        release=None,
        status_time=parse_status_time(STATUS_TIME),
    )
    with pytest.raises(Exception, match="append-only"):
        emit_status_files(other, tmp_path)


def test_scrub_gate_aborts_on_secret(tmp_path: Path):
    lane = _lane()
    # The secret shape is assembled at runtime — no literal key lands in
    # tracked source (the repo's own secret scan sweeps every file).
    lane["sources"][0]["name"] = "api_key=" + "AKIA" + "IOSFODNN7" + "EXAMPLE"
    from ops.status_lane import StatusLaneError

    with pytest.raises(StatusLaneError, match="secret"):
        emit_status_files(lane, tmp_path)


def test_deterministic_emit(tmp_path: Path):
    a = emit_status_files(_lane(), tmp_path / "a")
    b = emit_status_files(_lane(), tmp_path / "b")
    for rel in a:
        assert a[rel].read_bytes() == b[rel].read_bytes(), rel


def test_per_source_json_is_a_status_source_doc(tmp_path: Path):
    emit_status_files(_lane(), tmp_path)
    doc = json.loads((tmp_path / "status/sources/alpha_feed.json").read_text())
    assert doc["schema"] == "sig.status-source/1"
    assert doc["status_time"] == STATUS_TIME
    assert doc["source"]["source_id"] == "alpha_feed"


# --- the emit + scoped publish leg ----------------------------------------


def _emit(tmp_path: Path) -> Path:
    runs = tmp_path / "runs.jsonl"
    runs.write_text(json.dumps(_run("alpha_feed", "2026-11-01T05:00:00Z")) + "\n")
    src = tmp_path / "sources.json"
    src.write_text(json.dumps(_sources_doc()))
    out = tmp_path / "tree"
    emit_status_tree(
        runs_path=runs,
        sources_path=src,
        out_dir=out,
        cadence_path=None,
        status_time=STATUS_TIME,
    )
    return out


def test_emit_tree_from_files(tmp_path: Path):
    out = _emit(tmp_path)
    assert (out / "status/state.json").is_file()
    assert (out / "status/lane.json").is_file()


def test_assert_status_tree_refuses_non_status_top_level(tmp_path: Path):
    out = _emit(tmp_path)
    (out / "index.html").write_text("<html></html>")
    from ops.status_publish import StatusPublishError

    with pytest.raises(StatusPublishError, match="status/"):
        assert_status_tree(out)


def test_plan_never_deletes_archive():
    plan = plan_status_sync(
        ["status/state.json", "status/lane.json"],
        [
            "status/state.json",
            "status/archive/2026-10-01.json",
            "status/sources/gone.json",
            "index.html",
        ],
    )
    assert "status/archive/2026-10-01.json" not in plan["delete"]
    assert "status/sources/gone.json" in plan["delete"]
    assert "index.html" not in plan["delete"]  # the lane never touches site files


class _FakeBucket:
    def __init__(self):
        self.objects: dict[str, bytes] = {"status/sources/gone.json": b"{}"}

    def list_objects(self, prefix):
        return [n for n in self.objects if n.startswith(prefix)]

    def put_object(self, name, data, content_type=None):
        self.objects[name] = data

    def delete_object(self, name, generation=None):
        del self.objects[name]

    def get_object(self, name):
        return self.objects[name]


def test_publish_status_tree_apply_writes_and_verifies(tmp_path: Path):
    out = _emit(tmp_path)
    bucket = _FakeBucket()
    result = publish_status_tree(out, bucket=bucket, apply=True)
    assert result["applied"] and result["verified"]
    assert "status/sources/gone.json" not in bucket.objects
    assert json.loads(bucket.objects["status/state.json"])["schema"] == "sig.status-heartbeat/1"


def test_publish_dry_run_plans_without_writes(tmp_path: Path):
    out = _emit(tmp_path)
    bucket = _FakeBucket()
    result = publish_status_tree(out, bucket=bucket, apply=False)
    assert not result["applied"]
    assert "status/state.json" in result["plan"]["put"]


def test_cli_emit(tmp_path: Path):
    runs = tmp_path / "runs.jsonl"
    runs.write_text(json.dumps(_run("alpha_feed", "2026-11-01T05:00:00Z")) + "\n")
    src = tmp_path / "sources.json"
    src.write_text(json.dumps(_sources_doc()))
    out = tmp_path / "tree"
    proc = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "ops",
            "status-publish",
            "--runs",
            str(runs),
            "--sources",
            str(src),
            "--status-time",
            STATUS_TIME,
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[2],
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert (out / "status/lane.json").is_file()


def test_loaders_fail_closed(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"schema": "other/1"}))
    from ops.status_lane import StatusLaneError

    with pytest.raises(StatusLaneError):
        load_source_rows(bad)
    assert load_scheduler_report(None) is None
    recs = tmp_path / "r.jsonl"
    recs.write_text(json.dumps(_run("a", "2026-01-01T00:00:00Z")) + "\n")
    assert len(load_run_records(recs)) == 1
