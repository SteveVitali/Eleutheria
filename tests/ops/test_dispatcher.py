# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.1c (ticket 291a; G1-TRIM B-13=a) — the hourly due dispatcher.

Everything here is deterministic: the due set is computed against pinned
instants on a synthetic cadence document, the executor is an injected fake
(no socket), and the live-diff shape tests use fixture ``LiveState`` bodies —
no gcloud, no wall-clock-dependent assertion.
"""

from __future__ import annotations

import json
import tomllib
import urllib.request
from datetime import datetime
from pathlib import Path

import pytest
from ops.cadence_window import CronError
from ops.scheduled import load_cadence, parse_cadence_doc

from ops import dispatcher as D
from ops import live_diff as L

REPO_ROOT = Path(__file__).resolve().parents[2]
CADENCE = REPO_ROOT / "ops" / "cadence.toml"

SYNTHETIC = """\
[probes]
job = "sig-probe"
scheduler = "sig-sched-probe"
schedule = "0 */6 * * *"
gcs_prefix = "ops/probes"

[runs]
gcs_prefix = "ops/runs"

[[sources]]
id = "hourly_src"
cadence = "hourly"
cron = "0 * * * *"
job = "sig-ingest-hourly-src"
scheduler = "sig-sched-hourly-src"

[[sources]]
id = "weekly_src"
cadence = "weekly"
cron = "30 4 * * 2"
job = "sig-ingest-weekly-src"
scheduler = "sig-sched-weekly-src"

[[sources]]
id = "monthly_src"
cadence = "monthly"
cron = "0 5 20 * *"
job = "sig-ingest-monthly-src"
scheduler = "sig-sched-monthly-src"

[[sources]]
id = "edge_src"
cadence = "hourly"
cron = "13 * * * *"
job = "sig-ingest-edge-src"
scheduler = "sig-sched-edge-src"

[[sources]]
id = "paused_src"
cadence = "monthly"
cron = "0 5 20 * *"
job = "sig-ingest-paused-src"
scheduler = "sig-sched-paused-src"
state = "paused"

[[batches]]
id = "pinned_batch"
cadence = "monthly"
cron = "35 3 10 * *"
job = "sig-ingest-pinned-batch"
scheduler = "sig-sched-pinned-batch"
members = ["hourly_src"]

[[manual_jobs]]
job = "sig-export"
sa_class = "export"

[dispatcher]
job = "sig-sched-due"
scheduler = "sig-sched-due"
cron = "13 * * * *"
sa_class = "ingest"
task_timeout = "30m"

[[retire_triggers]]
name = "sig-sched-hourly-src"
disposition = "retired"
reason = "consolidated"

[[retire_triggers]]
name = "sig-sched-weekly-src"
disposition = "retired"
reason = "consolidated"

[[retire_triggers]]
name = "sig-sched-monthly-src"
disposition = "retired"
reason = "consolidated"

[[retire_triggers]]
name = "sig-sched-edge-src"
disposition = "retired"
reason = "consolidated"

[[retire_triggers]]
name = "sig-sched-paused-src"
disposition = "retired"
reason = "consolidated; the row state carries the pause"

[[retire_triggers]]
name = "sig-sched-pinned-batch"
disposition = "kept-declared-pin"
reason = "a declared pin keeps its own trigger"

[[retire_triggers]]
name = "sig-export"
disposition = "kept-manual"
reason = "manual job — never a trigger"
"""


def _config(text: str = SYNTHETIC):
    return parse_cadence_doc(tomllib.loads(text))


def _at(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _due_ids(ds: D.DueSet) -> set[str]:
    return {d.id for d in ds.due}


# --- the due window ------------------------------------------------------------


def test_window_tiles_consecutive_dispatches() -> None:
    open_, close = D.due_window("13 * * * *", _at("2026-10-16T05:13:30Z"))
    assert (open_, close) == (_at("2026-10-16T04:13:00Z"), _at("2026-10-16T05:13:00Z"))
    open2, close2 = D.due_window("13 * * * *", _at("2026-10-16T06:13:00Z"))
    assert (open2, close2) == (close, _at("2026-10-16T06:13:00Z"))


def test_window_late_start_still_covers_its_fire() -> None:
    # A dispatch starting at :45 still closes on its own :13 fire — the due
    # set is the window it stands in for, not the wall clock.
    open_, close = D.due_window("13 * * * *", _at("2026-10-16T05:45:00Z"))
    assert (open_, close) == (_at("2026-10-16T04:13:00Z"), _at("2026-10-16T05:13:00Z"))


def test_window_since_overrides_the_open_edge() -> None:
    open_, close = D.due_window(
        "13 * * * *", _at("2026-10-16T05:13:00Z"), since=_at("2026-10-16T03:00:00Z")
    )
    assert (open_, close) == (_at("2026-10-16T03:00:00Z"), _at("2026-10-16T05:13:00Z"))


def test_window_bad_dispatcher_cron_fails_closed() -> None:
    with pytest.raises(CronError):
        D.due_window("not a cron", _at("2026-10-16T05:13:00Z"))


# --- evaluate_due --------------------------------------------------------------


def test_due_set_at_the_dispatch_minute() -> None:
    ds = D.evaluate_due(_config(), now=_at("2026-10-20T05:13:00Z"))
    # hourly_src fires 05:00 (in window); monthly_src fires day-20 05:00;
    # weekly_src fires Tue 04:30 — 2026-10-20 is a Tuesday, still inside
    # (04:13, 05:13]; edge_src fires 05:13 == close (inclusive edge).
    assert _due_ids(ds) == {"hourly_src", "monthly_src", "weekly_src", "edge_src"}
    assert {s.id for s in ds.skipped} == {"paused_src", "pinned_batch"}
    assert {s.reason for s in ds.skipped} == {"declared-paused", "kept-declared-pin"}
    assert ds.window_open_source == "dispatcher-cron"
    assert ds.evaluated == 6


def test_due_set_next_dispatch_never_redispatches() -> None:
    # The same fires sit on the NEXT window's exclusive open edge — a row is
    # dispatched once per fire, never twice.
    ds = D.evaluate_due(_config(), now=_at("2026-10-20T06:13:00Z"))
    assert _due_ids(ds) == {"hourly_src", "edge_src"}


def test_open_edge_is_exclusive() -> None:
    # A row whose fire lands exactly on the window's open edge was covered by
    # the PREVIOUS dispatch — never redispatched.
    ds = D.evaluate_due(_config(), now=_at("2026-10-20T04:13:00Z"))
    # window (03:13, 04:13]: hourly fires 04:00; edge fires 04:13 (close).
    assert _due_ids(ds) == {"hourly_src", "edge_src"}
    ds2 = D.evaluate_due(_config(), now=_at("2026-10-20T03:13:00Z"))
    # window (02:13, 03:13]: edge fires 03:13; the 04:13 fire is future.
    assert _due_ids(ds2) == {"hourly_src", "edge_src"}


def test_monthly_row_dues_only_on_its_day() -> None:
    ds = D.evaluate_due(_config(), now=_at("2026-10-19T05:13:00Z"))
    assert "monthly_src" not in _due_ids(ds)
    ds = D.evaluate_due(_config(), now=_at("2026-10-20T05:13:00Z"))
    assert "monthly_src" in _due_ids(ds)
    ds = D.evaluate_due(_config(), now=_at("2026-10-21T05:13:00Z"))
    assert "monthly_src" not in _due_ids(ds)


def test_weekly_row_boundary() -> None:
    # 2026-10-21 is a Wednesday — the Tuesday 04:30 fire is a day old.
    ds = D.evaluate_due(_config(), now=_at("2026-10-21T05:13:00Z"))
    assert "weekly_src" not in _due_ids(ds)


def test_dst_weeks_are_plain_utc() -> None:
    # Crons evaluate in UTC — a US DST transition changes nothing about the
    # window or the fires (2026-11-01 is the fallback Sunday).
    ds = D.evaluate_due(_config(), now=_at("2026-11-01T05:13:00Z"))
    assert ds.window_open == "2026-11-01T04:13Z"
    assert ds.window_close == "2026-11-01T05:13Z"
    assert _due_ids(ds) == {"hourly_src", "edge_src"}
    # And the spring-forward week is equally unremarkable in UTC.
    ds = D.evaluate_due(_config(), now=_at("2026-03-08T05:13:00Z"))
    assert ds.window_open == "2026-03-08T04:13Z"


def test_paused_row_is_never_due() -> None:
    # paused_src shares monthly_src's cron — on the 20th it still skips.
    ds = D.evaluate_due(_config(), now=_at("2026-10-20T05:13:00Z"))
    skipped = {s.id: s.reason for s in ds.skipped}
    assert skipped["paused_src"] == "declared-paused"
    assert skipped["pinned_batch"] == "kept-declared-pin"


def test_since_catch_up_picks_up_missed_windows() -> None:
    ds = D.evaluate_due(
        _config(), now=_at("2026-10-16T05:13:00Z"), since=_at("2026-10-16T02:00:00Z")
    )
    # Window (02:00, 05:13]: hourly fires 03:00, 04:00, 05:00 → last fire
    # stands for the row (one dispatch per row per evaluation).
    assert _due_ids(ds) == {"hourly_src", "edge_src"}
    assert ds.window_open_source == "explicit-since"


def test_no_dispatcher_table_refuses() -> None:
    bare = tomllib.loads(SYNTHETIC)
    del bare["dispatcher"]
    with pytest.raises(D.DispatcherError, match=r"no \[dispatcher\]"):
        D.evaluate_due(parse_cadence_doc(bare), now=_at("2026-10-16T05:13:00Z"))


def test_real_cadence_evaluates_all_rows() -> None:
    # The committed file: every row evaluates (or skips) — none errors, and
    # the skipped set is exactly the paused + kept-pin rows.
    cadence = load_cadence(CADENCE)
    ds = D.evaluate_due(cadence, now=_at("2026-10-16T05:13:00Z"))
    assert ds.evaluated == len(cadence.sources) + len(cadence.batches)
    paused = {s.source for s in cadence.sources if s.state == "paused"} | {
        b.id for b in cadence.batches if b.state == "paused"
    }
    kept = {r.name for r in cadence.retire_triggers if r.disposition == "kept-declared-pin"}
    kept_jobs = {s.scheduler for s in cadence.sources if s.scheduler in kept} | {
        b.scheduler for b in cadence.batches if b.scheduler in kept
    }
    skipped_ids = {s.id for s in ds.skipped}
    skipped_scheds = {s.scheduler for s in ds.skipped}
    assert skipped_ids == paused | {r.id for r in ds.skipped if r.reason == "kept-declared-pin"}
    assert kept_jobs == {s for s in skipped_scheds if s in kept}


# --- dispatch_due: the run row + executor -------------------------------------


def _fake_executor(calls: list[str], fail: set[str] | None = None):
    def run(job: str) -> str:
        calls.append(job)
        if fail and job in fail:
            raise D.DispatcherError(f"simulated enqueue failure for {job}")
        return f"execution/{job}-1"

    return run


def test_dispatch_records_would_execute_on_dry_run() -> None:
    calls: list[str] = []
    row, code = D.dispatch_due(
        _config(),
        now=_at("2026-10-20T05:13:00Z"),
        execute=False,
        executor=_fake_executor(calls),
    )
    assert code == 0 and row.outcome == "dry-run" and row.exit_code == 0
    assert calls == []  # a dry-run touches nothing
    rec = row.as_json()
    assert row.kind == "dispatch-due" and row.source == "_dispatcher"
    payload = rec["fetch_record"]
    assert payload["schema"] == "sig.dispatch-due/1"
    assert payload["execute"] is False
    assert all(e.get("would_execute") for e in payload["enqueued"])
    assert {e["id"] for e in payload["enqueued"]} == {
        "hourly_src",
        "monthly_src",
        "weekly_src",
        "edge_src",
    }


def test_dispatch_executes_each_due_job() -> None:
    calls: list[str] = []
    row, code = D.dispatch_due(
        _config(),
        now=_at("2026-10-20T05:13:00Z"),
        executor=_fake_executor(calls),
    )
    assert code == 0
    assert sorted(calls) == [
        "sig-ingest-edge-src",
        "sig-ingest-hourly-src",
        "sig-ingest-monthly-src",
        "sig-ingest-weekly-src",
    ]
    payload = row.as_json()["fetch_record"]
    assert payload["enqueue_failures"] == 0
    assert all(e.get("execution", "").startswith("execution/") for e in payload["enqueued"])


def test_dispatch_enqueue_failure_exits_1_and_records() -> None:
    calls: list[str] = []
    row, code = D.dispatch_due(
        _config(),
        now=_at("2026-10-20T05:13:00Z"),
        executor=_fake_executor(calls, fail={"sig-ingest-weekly-src"}),
    )
    assert code == 1 and row.outcome == "error"
    payload = row.as_json()["fetch_record"]
    assert payload["enqueue_failures"] == 1
    failed = [e for e in payload["enqueued"] if e["job"] == "sig-ingest-weekly-src"]
    assert "error" in failed[0] and "execution" not in failed[0]


def test_dispatch_empty_evaluation_fails_sig_eng_042() -> None:
    bare = tomllib.loads(SYNTHETIC)
    bare["sources"] = []
    bare["batches"] = []
    row, code = D.dispatch_due(
        parse_cadence_doc(bare), now=_at("2026-10-20T05:13:00Z"), execute=False
    )
    assert code == 2 and row.outcome == "error"
    assert "evaluated 0" in row.detail


def test_dispatch_no_due_is_a_recorded_clean_pass() -> None:
    # Evaluated rows with nothing due → a run row, exit 0 — the evaluation IS
    # the record (SIG-ENG-042 only refuses an EMPTY evaluation).
    row, code = D.dispatch_due(_config(), now=_at("2026-10-21T05:13:00Z"), execute=False)
    assert code == 0
    payload = row.as_json()["fetch_record"]
    assert {e["id"] for e in payload["enqueued"]} == {"hourly_src", "edge_src"}
    # Push past the hourly's fire too — an hour where nothing else fires.
    row, code = D.dispatch_due(
        _config(),
        now=_at("2026-10-21T05:13:00Z"),
        executor=_fake_executor([]),
    )
    assert code == 0


def test_dispatch_missing_dispatcher_exits_2() -> None:
    bare = tomllib.loads(SYNTHETIC)
    del bare["dispatcher"]
    row, code = D.dispatch_due(parse_cadence_doc(bare))
    assert code == 2 and row.outcome == "error"


# --- the REST executor ---------------------------------------------------------


def test_rest_executor_posts_the_jobs_run_endpoint() -> None:
    seen: dict[str, object] = {}

    def poster(req: urllib.request.Request):
        seen["url"] = req.full_url
        seen["method"] = req.get_method()
        seen["auth"] = req.get_header("Authorization")
        seen["body"] = req.data
        return {"metadata": {"name": "exec-9"}}

    run_one = D.rest_executor("proj-1", "us-central1", token=lambda: "tok-1", poster=poster)
    assert run_one("sig-ingest-x") == "exec-9"
    assert seen["url"] == (
        "https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/"
        "namespaces/proj-1/jobs/sig-ingest-x:run"
    )
    assert seen["method"] == "POST"
    assert seen["auth"] == "Bearer tok-1"
    assert seen["body"] == b"{}"


def test_rest_executor_without_token_fails() -> None:
    run_one = D.rest_executor("proj-1", "us-central1", token=lambda: None)
    with pytest.raises(D.DispatcherError, match="no GCP access token"):
        run_one("sig-ingest-x")


def test_rest_executor_requires_project() -> None:
    with pytest.raises(D.DispatcherError, match="needs a project"):
        D.rest_executor("", "us-central1")


# --- the declaration-bundle loader ---------------------------------------------


def test_load_dispatcher_cadence_reads_the_bundle(tmp_path: Path) -> None:
    bundle = tmp_path / "declared.json"
    bundle.write_text(json.dumps({"cadence_toml": SYNTHETIC}))
    config = D.load_dispatcher_cadence(declared_source=str(bundle))
    assert config.dispatcher is not None and config.dispatcher.job == "sig-sched-due"


def test_load_dispatcher_cadence_missing_member_refuses(tmp_path: Path) -> None:
    bundle = tmp_path / "declared.json"
    bundle.write_text(json.dumps({"fleet": {}}))
    with pytest.raises(D.DispatcherError, match="cadence_toml"):
        D.load_dispatcher_cadence(declared_source=str(bundle))


# --- retire_trigger_lint: the name-checked set ---------------------------------


def test_real_cadence_retire_lint_is_clean() -> None:
    assert L.retire_trigger_lint(load_cadence(CADENCE)) == []


def test_lint_refuses_an_uncovered_row() -> None:
    doc = tomllib.loads(SYNTHETIC)
    doc["retire_triggers"] = [
        r for r in doc["retire_triggers"] if r["name"] != "sig-sched-weekly-src"
    ]
    problems = L.retire_trigger_lint(parse_cadence_doc(doc))
    assert any("sig-sched-weekly-src" in p and "not listed" in p for p in problems)


def test_lint_refuses_a_bad_disposition() -> None:
    doc = tomllib.loads(SYNTHETIC)
    doc["retire_triggers"][0]["disposition"] = "maybe"
    problems = L.retire_trigger_lint(parse_cadence_doc(doc))
    assert any("disposition" in p for p in problems)


def test_lint_refuses_a_missing_reason() -> None:
    doc = tomllib.loads(SYNTHETIC)
    doc["retire_triggers"][0]["reason"] = ""
    problems = L.retire_trigger_lint(parse_cadence_doc(doc))
    assert any("missing reason" in p for p in problems)


def test_lint_refuses_a_non_cadence_name() -> None:
    doc = tomllib.loads(SYNTHETIC)
    doc["retire_triggers"][-1] = {
        "name": "sig-sched-invented",
        "disposition": "retired",
        "reason": "x",
    }
    problems = L.retire_trigger_lint(parse_cadence_doc(doc))
    assert any("sig-sched-invented" in p and "not a" in p for p in problems)


def test_lint_refuses_a_protected_collision() -> None:
    doc = tomllib.loads(SYNTHETIC)
    doc["retire_triggers"][0]["name"] = "sig-sched-probe"
    problems = L.retire_trigger_lint(parse_cadence_doc(doc))
    assert any("protected" in p for p in problems)


def test_lint_refuses_dispatcher_job_reusing_a_live_name() -> None:
    doc = tomllib.loads(SYNTHETIC)
    doc["dispatcher"]["job"] = "sig-ingest-hourly-src"
    problems = L.retire_trigger_lint(parse_cadence_doc(doc))
    assert any("also declared live" in p for p in problems)


def test_lint_refuses_a_half_declaration() -> None:
    doc = tomllib.loads(SYNTHETIC)
    del doc["dispatcher"]
    problems = L.retire_trigger_lint(parse_cadence_doc(doc))
    assert any("no [dispatcher]" in p for p in problems)


# --- live-diff: the consolidated trigger shape ----------------------------------

PROJECT = "test-proj"
REGION = "us-central1"
FLEET_REF = f"{REGION}-docker.pkg.dev/{PROJECT}/sig/sig-api@sha256:{'a' * 64}"


def _declared_fleet():
    cadence = _config()
    fleet = L.FleetImages(fleet_ref=FLEET_REF)
    return cadence, L.declared_fleet(cadence, fleet, project=PROJECT, region=REGION)


def _sched_body(name: str, schedule: str, job: str, *, state="ENABLED"):
    return {
        "name": f"projects/{PROJECT}/locations/{REGION}/jobs/{name}",
        "schedule": schedule,
        "state": state,
        "httpTarget": {
            "uri": (
                f"https://{REGION}-run.googleapis.com/apis/run.googleapis.com/v1/"
                f"namespaces/{PROJECT}/jobs/{job}:run"
            ),
            "httpMethod": "POST",
            "body": "",
        },
    }


def _live_from(declared: L.DeclaredFleet, *, include_retired=(), extra_sched=()):
    state = L.LiveState()
    for t in declared.triggers:
        state.schedulers[t.name] = _sched_body(
            t.name, t.cron, t.job, state="PAUSED" if t.paused else "ENABLED"
        )
    for j in declared.jobs:
        state.jobs[j.name] = {
            "spec": {
                "template": {
                    "spec": {
                        "template": {
                            "spec": {
                                "serviceAccountName": "sig-ingest-rt@test.iam.gserviceaccount.com",
                                "containers": [{"image": j.image}],
                            }
                        }
                    }
                }
            }
        }
    for name, job in include_retired:
        state.schedulers[name] = _sched_body(name, "0 0 0 0 0", job)
    for name, job in extra_sched:
        state.schedulers[name] = _sched_body(name, "0 0 0 0 0", job)
    return state


def test_declared_fleet_under_the_dispatcher_shape() -> None:
    _cadence, fleet = _declared_fleet()
    trigger_names = {t.name for t in fleet.triggers}
    # The dispatcher joins the declared triggers; retired per-row triggers do
    # not; the kept pin keeps its trigger.
    assert "sig-sched-due" in trigger_names
    assert "sig-sched-hourly-src" not in trigger_names
    assert "sig-sched-pinned-batch" in trigger_names
    assert {t.name for t in fleet.triggers if t.name == "sig-sched-due"}
    due = next(t for t in fleet.triggers if t.name == "sig-sched-due")
    assert due.cron == "13 * * * *" and due.job == "sig-sched-due"
    # The dispatcher job joins the declared jobs with its sa_class.
    job_names = {j.name for j in fleet.jobs}
    assert "sig-sched-due" in job_names
    assert {j.name for j in fleet.jobs if j.sa_class == "ingest"} == {"sig-sched-due"}
    # The name-checked retired set is carried for the report split.
    assert "sig-sched-hourly-src" in fleet.retired_trigger_names
    assert "sig-sched-pinned-batch" not in fleet.retired_trigger_names
    # Jobs that must carry a trigger: probe + dispatcher + the kept pin only.
    assert fleet.cadence_job_names == frozenset(
        {"sig-probe", "sig-sched-due", "sig-ingest-pinned-batch"}
    )


def test_diff_reports_a_still_live_retired_trigger_distinctly() -> None:
    cadence, fleet = _declared_fleet()
    live = _live_from(fleet, include_retired=[("sig-sched-hourly-src", "sig-ingest-hourly-src")])
    report = L.diff(fleet, live)
    retired = [f for f in report.findings if f.name == "sig-sched-hourly-src"]
    assert len(retired) == 1
    assert "declared retired" in retired[0].detail
    assert "not declared" not in retired[0].detail


def test_diff_flags_unlisted_trigger_drift_unchanged() -> None:
    _cadence, fleet = _declared_fleet()
    live = _live_from(fleet, extra_sched=[("sig-sched-stray", "sig-ingest-x")])
    report = L.diff(fleet, live)
    stray = [f for f in report.findings if f.name == "sig-sched-stray"]
    assert len(stray) == 1 and "not declared" in stray[0].detail


def test_diff_checks_the_dispatcher_trigger_shape() -> None:
    _cadence, fleet = _declared_fleet()
    live = _live_from(fleet)
    live.schedulers["sig-sched-due"] = _sched_body(
        "sig-sched-due", "13 * * * *", "sig-ingest-wrong-target"
    )
    report = L.diff(fleet, live)
    due_findings = [f for f in report.findings if f.name == "sig-sched-due"]
    assert any("invokes job" in f.detail for f in due_findings)


def test_diff_reports_a_missing_dispatcher_trigger_and_job() -> None:
    _cadence, fleet = _declared_fleet()
    live = _live_from(fleet)
    del live.schedulers["sig-sched-due"]
    del live.jobs["sig-sched-due"]
    report = L.diff(fleet, live)
    kinds = {(f.cls, f.name) for f in report.findings}
    assert ("schedule", "sig-sched-due") in kinds
    assert ("job_config", "sig-sched-due") in kinds


def test_diff_under_per_source_shape_declares_every_row_trigger() -> None:
    # No [dispatcher] → every per-row trigger is declared (the rollback map).
    doc = tomllib.loads(SYNTHETIC)
    del doc["dispatcher"]
    del doc["retire_triggers"]
    cadence = parse_cadence_doc(doc)
    fleet = L.declared_fleet(
        cadence, L.FleetImages(fleet_ref=FLEET_REF), project=PROJECT, region=REGION
    )
    names = {t.name for t in fleet.triggers}
    assert "sig-sched-hourly-src" in names
    assert "sig-sched-weekly-src" in names
    assert "sig-sched-paused-src" in names  # declared, expected PAUSED
    assert "sig-sched-due" not in names
    assert fleet.retired_trigger_names == frozenset()
    paused = next(t for t in fleet.triggers if t.name == "sig-sched-paused-src")
    assert paused.paused is True


def test_diff_paused_row_enabled_live_is_drift() -> None:
    doc = tomllib.loads(SYNTHETIC)
    del doc["dispatcher"]
    del doc["retire_triggers"]
    cadence = parse_cadence_doc(doc)
    fleet = L.declared_fleet(
        cadence, L.FleetImages(fleet_ref=FLEET_REF), project=PROJECT, region=REGION
    )
    live = _live_from(fleet)  # all declared triggers ENABLED except paused
    live.schedulers["sig-sched-paused-src"] = _sched_body(
        "sig-sched-paused-src", "0 5 20 * *", "sig-ingest-paused-src", state="ENABLED"
    )
    report = L.diff(fleet, live)
    hits = [f for f in report.findings if f.name == "sig-sched-paused-src"]
    assert any("declared paused" in f.detail for f in hits)
