# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.39a / D-P31.4-1: the read-only ``scheduled-readback`` verb.

Every test runs on recorded fixtures or injected fakes — the clock guard, the
criterion verdicts, and the failure routing are pure; no socket, no gcloud, no
PG is touched (the live paths are the thin ``*_factory`` gatherers).
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from ops.scheduled_readback import (
    READBACK_QUEUED,
    RERUN_PROMPT,
    Gathered,
    build_report,
    capture_baseline,
    evaluate,
    execution_summary,
    fire_time_for,
    guard_failures,
    overall_and_routing,
    pick_execution,
    run_readback,
)

from ops import cli

FIRE = datetime(2026, 10, 10, 3, 35, tzinfo=UTC)
RUN_DATE = date(2026, 10, 10)
AFTER = datetime(2026, 10, 10, 5, 0, tzinfo=UTC)
MEMBERS = ["camreg_osm_surveillance", "camreg_nitro", "camreg_nola_safety_la"]
BATCH = {
    "id": "camreg-batch-05",
    "cadence": "monthly",
    "cron": "35 3 10 * *",
    "job": "sig-ingest-camreg-batch-05",
    "scheduler": "sig-sched-camreg-batch-05",
    "members": MEMBERS,
}
FIXTURES = Path(__file__).parent / "fixtures" / "scheduled_readback" / "pass"
# The committed pass fixture mirrors the real 17-member batch-05.
FIXTURE_BATCH = {
    **BATCH,
    "members": [
        "camreg_monmap_mn",
        "camreg_mueller_de",
        "camreg_nashville_tn",
        "camreg_nitro",
        "camreg_nola_safety_la",
        "camreg_und_018",
        "camreg_us_ny_001",
        "camreg_us_ny_002",
        "camreg_nzta_nz",
        "camreg_oem_camera",
        "camreg_und_019",
        "camreg_oosgis_nl",
        "camreg_osm_surveillance",
        "camreg_palmdesert_ca",
        "camreg_penndot_pa",
        "camreg_pgcounty_md",
        "camreg_pipeline_sec",
    ],
}

SCHEDULER_FIRED = {
    "state": "ENABLED",
    "schedule": "35 3 10 * *",
    "scheduleTime": "2026-10-10T03:35:00Z",
    "lastAttemptTime": "2026-10-10T03:35:00.1Z",
}
EXECUTION_DONE = {
    "metadata": {
        "name": "sig-ingest-camreg-batch-05-ab12c",
        "creationTimestamp": "2026-10-10T03:35:02Z",
    },
    "status": {
        "startTime": "2026-10-10T03:35:40Z",
        "completionTime": "2026-10-10T03:55:12Z",
        "succeededCount": 1,
        "cancelledCount": 0,
        "failedCount": 0,
    },
}


def _osm_row(**kw: Any) -> dict:
    row = {
        "kind": "scheduled-ingest",
        "source": "camreg_osm_surveillance",
        "mode": "live",
        "outcome": "ok",
        "exit_code": 0,
        "started_at": "2026-10-10T03:36:20Z",
        "duration_seconds": 812.4,
        "claims_added": 1_369_210,
        "capture_digests": ["sha256:aa"],
        "fetch_record": {
            "fetches": 158,
            "resumed": [],
            "logical_run": "camreg_osm_surveillance@2026-10-10T03:35Z",
        },
        "ingest_run_id": "11111111-2222-3333-4444-555566667777",
        "_object": "gs://b/ops/runs/camreg_osm_surveillance/2026-10-10/r.json",
    }
    row.update(kw)
    return row


def _gathered(**kw: Any) -> Gathered:
    g = Gathered()
    g.scheduler = dict(SCHEDULER_FIRED)
    g.executions = [dict(EXECUTION_DONE)]
    g.run_rows = {
        "camreg_osm_surveillance": [_osm_row()],
        "camreg_nitro": [{"started_at": "2026-10-10T03:40:00Z", "outcome": "ok"}],
        "camreg_nola_safety_la": [{"started_at": "2026-10-10T03:41:00Z", "outcome": "ok"}],
    }
    g.completions = [
        {
            "run_id": "11111111-2222-3333-4444-555566667777",
            "source_id": "camreg_osm_surveillance",
            "status": "ok",
            "run_record_uri": "gs://b/ops/runs/camreg_osm_surveillance/2026-10-10/r.json",
            "finished_at": "2026-10-10T03:50:01Z",
        }
    ]
    g.counters = {"claim": {"n_tup_upd": 0, "n_tup_del": 0}}
    g.counters_queried = True
    g.completions_queried = True
    g.probes = [
        {"service": "sig-api-health", "ok": True, "ts": "2026-10-10T00:00:05Z"},
        {"service": "sig-api-health", "ok": True, "ts": "2026-10-10T06:00:05Z"},
    ]
    g.monitoring = {
        "cloudsql.googleapis.com/database/memory/utilization": [
            {"time": "2026-10-10T03:50:00Z", "value": 0.72}
        ],
        "cloudsql.googleapis.com/database/disk/bytes_used": [
            {"time": "2026-10-10T03:35:00Z", "value": 6_549_311_488},
            {"time": "2026-10-10T03:55:00Z", "value": 6_553_000_000},
        ],
        "cloudsql.googleapis.com/database/uptime": [
            {"time": "2026-10-10T03:35:00Z", "value": 1_900_000},
            {"time": "2026-10-10T03:55:00Z", "value": 1_901_200},
        ],
    }
    for k, v in kw.items():
        setattr(g, k, v)
    return g


def _ctx(exec_sum: dict | None = None) -> dict:
    return {
        "members": MEMBERS,
        "fire": FIRE,
        "execution": exec_sum or execution_summary(EXECUTION_DONE),
    }


def _results(criteria: list[dict]) -> dict[str, str]:
    return {c["id"]: c["result"] for c in criteria}


# --- clock guard -------------------------------------------------------------


def test_fire_time_from_cron() -> None:
    assert fire_time_for("35 3 10 * *", RUN_DATE) == FIRE
    with pytest.raises(ValueError):
        fire_time_for("35 3 10 * *", date(2026, 10, 11))


def test_guard_refuses_before_the_fire() -> None:
    failures = guard_failures(
        fire=FIRE,
        now=FIRE - timedelta(days=1),
        scheduler={"state": "ENABLED"},
        execution=None,
    )
    assert any("in the future" in f for f in failures)
    assert any("lastAttemptTime" in f for f in failures)
    assert any("no Cloud Run execution" in f for f in failures)


def test_guard_refuses_until_trigger_fired_and_execution_done() -> None:
    base = dict(fire=FIRE, now=AFTER)
    # Trigger not yet fired
    assert guard_failures(**base, scheduler={"state": "ENABLED"}, execution=EXECUTION_DONE)
    # Trigger fired, execution still running
    running = {
        "metadata": {
            "name": "sig-ingest-camreg-batch-05-x",
            "creationTimestamp": "2026-10-10T03:35:02Z",
        },
        "status": {"startTime": "2026-10-10T03:35:40Z"},
    }
    assert guard_failures(**base, scheduler=SCHEDULER_FIRED, execution=running)
    # Everything in place
    assert not guard_failures(**base, scheduler=SCHEDULER_FIRED, execution=EXECUTION_DONE)
    # A disabled trigger is a failure even after the fire time
    assert guard_failures(
        **base,
        scheduler={**SCHEDULER_FIRED, "state": "DISABLED"},
        execution=EXECUTION_DONE,
    )
    # A lastAttemptTime from a PREVIOUS month's fire does not satisfy the guard
    assert guard_failures(
        **base,
        scheduler={**SCHEDULER_FIRED, "lastAttemptTime": "2026-09-10T03:35:00Z"},
        execution=EXECUTION_DONE,
    )
    # Executions list unreadable is a failure, not an implicit pass
    assert guard_failures(
        **base,
        scheduler=SCHEDULER_FIRED,
        execution=EXECUTION_DONE,
        executions_error="API unreachable",
    )
    # Scheduler describe unreadable is a failure too
    assert guard_failures(
        **base,
        scheduler=None,
        execution=EXECUTION_DONE,
        scheduler_error="API unreachable",
    )


def test_pick_execution_scopes_to_post_fire_executions() -> None:
    old = {
        "metadata": {
            "name": "sig-ingest-camreg-batch-05-old",
            "creationTimestamp": "2026-09-10T03:35:02Z",
        },
        "status": {"completionTime": "2026-09-10T04:00:00Z"},
    }
    other_job = {
        "metadata": {
            "name": "sig-ingest-camreg-batch-04-ab",
            "creationTimestamp": "2026-10-10T03:36:00Z",
        },
        "status": {"completionTime": "2026-10-10T04:00:00Z"},
    }
    picked = pick_execution([old, other_job, EXECUTION_DONE], "sig-ingest-camreg-batch-05", FIRE)
    assert picked is EXECUTION_DONE


# --- criterion evaluation -----------------------------------------------------


def test_evaluate_all_pass() -> None:
    criteria = evaluate(_gathered(), _ctx())
    results = _results(criteria)
    assert all(r == "pass" for r in results.values()), results
    verdict, routing, _ = overall_and_routing(
        criteria, exec_sum=_ctx()["execution"], fire=FIRE, now=AFTER
    )
    assert verdict == "pass"
    assert routing == "none"


def test_fetches_fewer_only_with_resumed() -> None:
    ok_row = _osm_row(
        fetch_record={
            "fetches": 144,
            "resumed": [{"target_key": "t1", "state": "skipped"}] * 14,
        }
    )
    g = _gathered(
        run_rows={
            "camreg_osm_surveillance": [ok_row],
            "camreg_nitro": [{}],
            "camreg_nola_safety_la": [{}],
        }
    )
    r = _results(evaluate(g, _ctx()))
    assert r["osm-fetches"] == "pass"
    bad_row = _osm_row(fetch_record={"fetches": 144, "resumed": []})
    g2 = _gathered(
        run_rows={
            "camreg_osm_surveillance": [bad_row],
            "camreg_nitro": [{}],
            "camreg_nola_safety_la": [{}],
        }
    )
    assert _results(evaluate(g2, _ctx()))["osm-fetches"] == "fail"


def test_claims_added_band() -> None:
    in_band = _osm_row(claims_added=1_400_000)
    g = _gathered(
        run_rows={
            "camreg_osm_surveillance": [in_band],
            "camreg_nitro": [{}],
            "camreg_nola_safety_la": [{}],
        }
    )
    assert _results(evaluate(g, _ctx()))["osm-claims-added"] == "pass"
    far_above = _osm_row(claims_added=3_000_000)
    g2 = _gathered(
        run_rows={
            "camreg_osm_surveillance": [far_above],
            "camreg_nitro": [{}],
            "camreg_nola_safety_la": [{}],
        }
    )
    criteria = evaluate(g2, _ctx())
    assert _results(criteria)["osm-claims-added"] == "fail"
    verdict, routing, triggers = overall_and_routing(
        criteria, exec_sum=_ctx()["execution"], fire=FIRE, now=AFTER
    )
    assert verdict == "fail"
    assert routing == "anomaly-stop-and-preserve"
    assert any("far above" in t for t in triggers)


def test_counter_drift_routes_to_anomaly_stop_and_preserve() -> None:
    g = _gathered(counters={"claim": {"n_tup_upd": 3, "n_tup_del": 0}})
    criteria = evaluate(g, _ctx())
    assert _results(criteria)["append-only-counters"] == "fail"
    _, routing, triggers = overall_and_routing(
        criteria, exec_sum=_ctx()["execution"], fire=FIRE, now=AFTER
    )
    assert routing == "anomaly-stop-and-preserve"
    assert any("counters" in t for t in triggers)


def test_disk_jump_over_3gb_is_anomaly_not_deferral() -> None:
    # G1 §3.7's anomaly row names a >3 GB disk jump; a 1–3 GiB growth fail is a
    # plain deferral-row, but a >3 GiB jump routes to stop-and-preserve.
    g = _gathered()
    g.monitoring["cloudsql.googleapis.com/database/disk/bytes_used"] = [
        {"time": "2026-10-10T03:35:00Z", "value": 6_549_311_488},
        {"time": "2026-10-10T03:55:00Z", "value": 6_549_311_488 + (4 << 30)},
    ]
    criteria = evaluate(g, _ctx())
    assert _results(criteria)["sql-disk-growth"] == "fail"
    _, routing, triggers = overall_and_routing(
        criteria, exec_sum=_ctx()["execution"], fire=FIRE, now=AFTER
    )
    assert routing == "anomaly-stop-and-preserve"
    assert any("disk" in t for t in triggers)


def test_over_hour_routes_to_adr_revisit() -> None:
    slow = _osm_row(duration_seconds=4200.0)
    g = _gathered(
        run_rows={
            "camreg_osm_surveillance": [slow],
            "camreg_nitro": [{}],
            "camreg_nola_safety_la": [{}],
        }
    )
    criteria = evaluate(g, _ctx())
    assert _results(criteria)["osm-duration"] == "fail"
    _, routing, _ = overall_and_routing(
        criteria, exec_sum=_ctx()["execution"], fire=FIRE, now=AFTER
    )
    assert routing == "adr-107-111-revisit"


def test_missing_member_rows_fail() -> None:
    g = _gathered(
        run_rows={
            "camreg_osm_surveillance": [_osm_row()],
            "camreg_nitro": [],
            "camreg_nola_safety_la": [],
        }
    )
    criteria = evaluate(g, _ctx())
    assert _results(criteria)["member-run-rows"] == "fail"
    _, routing, _ = overall_and_routing(
        criteria, exec_sum=_ctx()["execution"], fire=FIRE, now=AFTER
    )
    assert routing == "deferral-row"


def test_36h_timeout_routes_to_deferral_row() -> None:
    long_ex = {
        "metadata": {
            "name": "sig-ingest-camreg-batch-05-x",
            "creationTimestamp": "2026-10-10T03:35:02Z",
        },
        "status": {
            "startTime": "2026-10-10T03:35:40Z",
            "completionTime": "2026-10-11T15:36:00Z",
            "succeededCount": 1,
        },
    }
    es = execution_summary(long_ex)
    criteria = evaluate(_gathered(), _ctx(es))
    _, routing, _ = overall_and_routing(
        criteria,
        exec_sum=es,
        fire=FIRE,
        now=FIRE + timedelta(hours=40),
    )
    assert routing == "deferral-row:execution-timeout"


def test_health_memory_disk_restart_criteria() -> None:
    # two not-ok probe rows → fail (more than one transient allowed)
    g = _gathered(
        probes=[
            {"service": "sig-api-health", "ok": True, "ts": "2026-10-10T00:00:05Z"},
            {"service": "sig-api-health", "ok": False, "ts": "2026-10-10T03:45:05Z"},
            {"service": "sig-api-health", "ok": False, "ts": "2026-10-10T06:00:05Z"},
        ]
    )
    assert _results(evaluate(g, _ctx()))["api-health"] == "fail"
    # no probe rows at all → honestly not_evaluable
    g = _gathered(probes=[])
    assert _results(evaluate(g, _ctx()))["api-health"] == "not_evaluable"
    # memory over 90%
    g = _gathered()
    g.monitoring["cloudsql.googleapis.com/database/memory/utilization"] = [
        {"time": "2026-10-10T03:50:00Z", "value": 0.93}
    ]
    assert _results(evaluate(g, _ctx()))["sql-memory"] == "fail"
    # disk grew >1 GiB
    g = _gathered()
    g.monitoring["cloudsql.googleapis.com/database/disk/bytes_used"] = [
        {"time": "2026-10-10T03:35:00Z", "value": 6_549_311_488},
        {"time": "2026-10-10T03:55:00Z", "value": 8_000_000_000},
    ]
    assert _results(evaluate(g, _ctx()))["sql-disk-growth"] == "fail"
    # uptime smaller than the point's distance from the fire → restart
    g = _gathered()
    g.monitoring["cloudsql.googleapis.com/database/uptime"] = [
        {"time": "2026-10-10T03:50:00Z", "value": 300.0}
    ]
    assert _results(evaluate(g, _ctx()))["sql-no-restart"] == "fail"


def test_missing_evidence_is_not_evaluable_never_green() -> None:
    g = _gathered(
        counters={},
        counters_queried=False,
        completions=[],
        completions_queried=False,
        probes=[],
        monitoring={},
    )
    criteria = evaluate(g, _ctx())
    results = _results(criteria)
    assert results["append-only-counters"] == "not_evaluable"
    assert results["api-health"] == "not_evaluable"
    assert results["sql-memory"] == "not_evaluable"
    assert results["sql-disk-growth"] == "not_evaluable"
    assert results["sql-no-restart"] == "not_evaluable"
    verdict, routing, _ = overall_and_routing(
        criteria, exec_sum=_ctx()["execution"], fire=FIRE, now=AFTER
    )
    assert verdict == "not_evaluable"
    assert routing == "deferral-row"


def test_completion_missing_fails() -> None:
    g = _gathered(completions=[])
    assert _results(evaluate(g, _ctx()))["osm-completion"] in ("fail", "not_evaluable")


# --- fixture replay / report shape --------------------------------------------


def test_fixture_replay_all_pass(tmp_path: Path) -> None:
    report, code = run_readback(
        batch=FIXTURE_BATCH,
        run_date=RUN_DATE,
        now=AFTER,
        project="proj",
        region="us-central1",
        bucket_name=None,
        dsn=None,
        api_url=None,
        fixtures_dir=FIXTURES,
    )
    assert code == 0
    assert report["kind"] == "sig.scheduled-readback/1"
    assert report["verdict"] == "pass"
    assert report["routing"] == "none"
    assert report["obligation"] == "D-P31.4-1"
    assert report["read_only"] is True
    assert any("re-sightings" in d for d in report["disclosures"])
    assert report["image"].endswith(
        "feff986cf66f551ed12031d6627acdefd3217192a9e20d452c3d4fe0376833f2"
    )
    assert {c["id"] for c in report["criteria"]} == {
        "execution-completed",
        "osm-run-row",
        "osm-outcome",
        "osm-fetches",
        "osm-claims-added",
        "osm-completion",
        "osm-duration",
        "member-run-rows",
        "append-only-counters",
        "api-health",
        "sql-memory",
        "sql-disk-growth",
        "sql-no-restart",
    }


def test_cli_fixture_replay(capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(
        [
            "scheduled-readback",
            "--batch",
            "camreg-batch-05",
            "--date",
            "2026-10-10",
            "--now",
            "2026-10-10T05:00:00Z",
            "--fixtures-dir",
            str(FIXTURES),
        ]
    )
    assert code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["verdict"] == "pass"


def test_cli_guard_refusal_is_queued_42(capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(
        [
            "scheduled-readback",
            "--batch",
            "camreg-batch-05",
            "--date",
            "2026-10-10",
            "--now",
            "2026-10-07T12:00:00Z",
            "--fixtures-dir",
            str(FIXTURES),
        ]
    )
    assert code == READBACK_QUEUED == 42
    report = json.loads(capsys.readouterr().out)
    assert report["leg"]["status"] == "queued"
    assert report["leg"]["rerun_prompt"] == RERUN_PROMPT
    assert report["guard"]["holds"] is False
    assert report["guard"]["failures"]


def test_cli_out_writes_report(tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    code = cli.main(
        [
            "scheduled-readback",
            "--fixtures-dir",
            str(FIXTURES),
            "--now",
            "2026-10-10T05:00:00Z",
            "--out",
            str(out),
        ]
    )
    assert code == 0
    assert json.loads(out.read_text())["verdict"] == "pass"


def test_cli_rejects_unknown_batch(capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(
        [
            "scheduled-readback",
            "--batch",
            "no-such-batch",
            "--fixtures-dir",
            str(FIXTURES),
        ]
    )
    assert code == 2


# --- the baseline capture ------------------------------------------------------


def test_capture_baseline_with_fakes(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_gcloud(args: Any) -> str:
        calls.append(list(args))
        if "scheduler" in args:
            return json.dumps(SCHEDULER_FIRED)
        return json.dumps({"state": "RUNNABLE", "settings": {"tier": "db-custom-1-3840"}})

    def fake_query(sql: str, params: tuple = ()) -> list[tuple]:
        if "pg_stat_user_tables" in sql:
            return [("claim", 0, 0)]
        if "evidence_artifact" in sql:
            return [("camreg_osm_surveillance", 100)]
        return [(2640429,)]

    def fake_series(metric: str, start: datetime, end: datetime) -> list[dict]:
        return [{"time": "2026-10-07T16:00:00Z", "value": 6549311488.0}]

    def fake_health(url: str) -> dict:
        return {"status": 200, "body": {"status": "ok"}}

    doc = capture_baseline(
        batch=BATCH,
        run_date=RUN_DATE,
        now=datetime(2026, 10, 7, 16, 6, tzinfo=UTC),
        project="proj",
        region="us-central1",
        dsn="postgresql://fake",
        api_url="https://api.example",
        gcloud=fake_gcloud,
        series=fake_series,
        health=fake_health,
        query_factory=lambda dsn: fake_query,
    )
    assert doc["kind"] == "sig.scheduled-readback-baseline/1"
    assert doc["errors"] == []
    assert doc["counters"] == {"claim": {"n_tup_upd": 0, "n_tup_del": 0}}
    assert doc["claim_counts"] == {"camreg_osm_surveillance": 100}
    assert doc["claim_total"] == 2640429
    assert doc["sql"]["disk_bytes_used"] == 6549311488.0
    assert doc["api_health"]["status"] == 200
    assert doc["sql_instance"]["tier"] == "db-custom-1-3840"
    assert doc["read_only"] is True
    # every gcloud call is a describe — never execute/cancel/update
    for call in calls:
        assert "execute" not in call and "cancel" not in call
        assert "update" not in call and "delete" not in call


def test_capture_baseline_without_dsn_records_the_gap() -> None:
    doc = capture_baseline(
        batch=BATCH,
        run_date=RUN_DATE,
        now=datetime(2026, 10, 7, tzinfo=UTC),
        project="proj",
        region="us-central1",
        dsn=None,
        api_url=None,
        gcloud=lambda a: json.dumps(SCHEDULER_FIRED),
        series=lambda m, s, e: [],
        health=None,
        query_factory=None,
    )
    assert doc["counters"] == {}
    assert any("DSN" in e for e in doc["errors"])


def test_build_report_carries_disclosure_and_layer() -> None:
    report = build_report(
        batch=BATCH,
        run_date=RUN_DATE,
        now=AFTER,
        gathered=_gathered(),
        project="proj",
        region="us-central1",
    )
    assert report["layer"] == "live"
    assert report["read_only"] is True
    assert "feff986c" in report["disclosures"][0]
    assert report["scheduler"]["lastAttemptTime"] == "2026-10-10T03:35:00.1Z"
