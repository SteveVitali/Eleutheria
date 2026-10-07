# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.39b: the read-only ``scheduled-firstfire`` legs (l1 wave / l2 peel / l3 final).

Every test runs on recorded fixtures or injected fakes — the first-fire
classification, the per-leg clock guards, the verdicts and the routing rows
are pure; no socket, no gcloud, no PG is touched (the live paths are the thin
``gather_*_live`` readers).  Fixture clocks derive from ``BASE`` so the
scheduled fire dates are written once, as ``date()`` arithmetic.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from ops.cadence_window import next_fire
from ops.scheduled import load_cadence
from ops.scheduled_firstfire import (
    FIRSTFIRE_QUEUED,
    L1_WINDOW_END,
    LEGS,
    NAMED_READS,
    PEEL_ON_AFTER,
    PEEL_ON_SOURCE,
    RERUN_PROMPT,
    FleetGathered,
    FleetTrigger,
    assess_first_fire,
    evaluate_fire_row,
    fleet_from_cadence,
    gather_from_fixtures,
    leg_fleet,
    run_firstfire,
)

from ops import cli

BASE = date(2026, 10, 7)  # the P34.39b engineering day — every clock derives from it
FIXTURES = Path(__file__).parent / "fixtures" / "scheduled_firstfire"


def _at(days: int, hms: str = "00:00:00") -> datetime:
    d = BASE + timedelta(days=days)
    return datetime.fromisoformat(f"{d.isoformat()}T{hms}+00:00")


def _fleet(path: Path = FIXTURES / "cadence.toml"):
    return fleet_from_cadence(load_cadence(path))


def _gathered(name: str, fleet=None) -> FleetGathered:
    return gather_from_fixtures(
        FIXTURES / name, fleet or _fleet(), known_extra=["sig-sched-api-probe"]
    )


def _run(leg: str, fixture: str, now: datetime):
    return run_firstfire(
        leg=leg,
        fleet=_fleet(),
        now=now,
        project="sig-p",
        region="us-central1",
        bucket_name="b",
        dsn="postgresql://r/o",
        fixtures_dir=FIXTURES / fixture,
        known_schedulers=["sig-sched-api-probe"],
    )


# ---------------------------------------------------------------------------
# cron helpers


def test_next_fire_same_day():
    assert next_fire("0 12 29 * *", _at(0)) == _at(22, "12:00:00")


def test_next_fire_or_semantics():
    # sam_gov's live-shape OR cron (day-of-month 1 OR Monday): the first fire
    # at/after a mid-September deploy is the following Monday.
    assert next_fire("0 5 1 * 1", _at(-20, "07:16:33")) == _at(-16, "05:00:00")


def test_next_fire_wraps_month():
    assert next_fire("35 3 10 * *", _at(4)) == _at(34, "03:35:00")


# ---------------------------------------------------------------------------
# first-fire classification


def _describe(**kw):
    return kw


def test_assess_first_fire_from_deploy():
    t = FleetTrigger("muckrock", "source", "0 6 1 * *", "j", "s")
    a = assess_first_fire(
        t,
        _describe(userUpdateTime="2026-09-16T04:08:09Z", lastAttemptTime="2026-10-01T06:00:00.7Z"),
    )
    assert a["first_fire"] == datetime(2026, 10, 1, 6, 0, tzinfo=UTC)
    assert a["basis"] in ("deployed", "attempted")


def test_assess_first_fire_attempted_earlier():
    # A trigger deployed earlier then re-pointed: the attempt maps to the
    # earlier fire — it stays the true first fire.
    t = FleetTrigger("sam_gov", "source", "0 5 1 * 1", "j", "s")
    a = assess_first_fire(
        t, _describe(userUpdateTime="2026-09-17T07:16:33Z", lastAttemptTime="2026-09-21T05:00:01Z")
    )
    assert a["first_fire"] == datetime(2026, 9, 21, 5, 0, tzinfo=UTC)


def test_assess_first_fire_absent():
    t = FleetTrigger("ghost", "source", "0 5 1 * *", "j", "s")
    assert assess_first_fire(t, None)["first_fire"] is None


# ---------------------------------------------------------------------------
# leg membership


def test_leg_l1_membership_matches_wave():
    fleet = _fleet()
    rows = leg_fleet("l1", fleet, _gathered("l1_pass"))
    ids = {t.id for t, _a in rows}
    assert ids == {
        "fbi_cde_agency_registry",
        "muckrock",
        "usaspending",
        "camreg-batch-05",
    }
    # the repeat trigger and the peel-on source stay out of the wave
    assert "sam_gov" not in ids and PEEL_ON_SOURCE not in ids


def test_leg_l2_is_the_peel_fire():
    fleet = _fleet()
    rows = leg_fleet("l2", fleet, _gathered("l2_pass"))
    assert [t.id for t, _a in rows] == [PEEL_ON_SOURCE]
    assert (
        rows[0][1]["first_fire"].isoformat()
        == "2026-10-29T12:00:00+00:00"  # future-ok: scheduled: contract bound
    )


def test_leg_l3_adds_peel_to_the_wave():
    fleet = _fleet()
    rows = leg_fleet("l3", fleet, _gathered("l3_pass"))
    ids = [t.id for t, _a in rows]
    assert PEEL_ON_SOURCE in ids
    assert len(ids) == 5
    # rows sorted by first_fire
    fires = [a["first_fire"] for _t, a in rows]
    assert fires == sorted(fires)


# ---------------------------------------------------------------------------
# clock guards


def test_l1_queued_before_window_end():
    report, code = _run("l1", "l1_pass", _at(1))
    assert code == FIRSTFIRE_QUEUED
    assert report["leg_status"]["status"] == "queued"
    assert report["leg_status"]["rerun_prompt"] == RERUN_PROMPT
    assert L1_WINDOW_END in report["guard"]["failures"][0]
    assert {f["fleet_id"] for f in report["queued_fires"]} == {
        "fbi_cde_agency_registry",
        "muckrock",
        "usaspending",
        "camreg-batch-05",
    }


def test_l2_queued_before_the_peel_fire():
    report, code = _run("l2", "l2_queued", _at(15))
    assert code == FIRSTFIRE_QUEUED
    assert report["leg_status"]["status"] == "queued"
    assert any("in the future" in f for f in report["guard"]["failures"])
    assert any("no lastAttemptTime" in f for f in report["guard"]["failures"])
    assert report["queued_fires"][0]["fleet_id"] == PEEL_ON_SOURCE


def test_l3_queued_until_the_peel_fire_finishes():
    # l1's window has closed but peel-on has not fired — l3 stays queued.
    report, code = _run("l3", "l3_pass", _at(15))
    assert code == FIRSTFIRE_QUEUED
    assert report["leg"] == "l3"


# ---------------------------------------------------------------------------
# fleet table verdicts


def test_l1_pass_table():
    report, code = _run("l1", "l1_pass", _at(16))
    assert code == 0
    assert report["kind"] == "sig.scheduled-firstfire/1"
    assert report["leg"] == "l1"
    assert report["layer"] == "fixture"
    assert report["read_only"] and report["non_blocking"]
    assert report["verdict"] == "ok"
    assert report["fires_read"] == 4
    by_id = {f["fleet_id"]: f for f in report["fires"]}
    assert set(by_id) == {
        "fbi_cde_agency_registry",
        "muckrock",
        "usaspending",
        "camreg-batch-05",
    }
    assert all(f["verdict"] == "ok" for f in by_id.values())
    # the batch row carries every member's WORM row
    assert by_id["camreg-batch-05"]["run_row_count"] == 3
    assert set(by_id["camreg-batch-05"]["run_rows"]) == {
        "camreg_osm_surveillance",
        "camreg_nitro",
        "camreg_nola_safety_la",
    }
    assert report["routing_rows"] == []
    # the two named reads are recorded (sam_gov's quota_reached row included)
    reads = {r["trigger"]: r for r in report["named_reads"]}
    assert reads["sam_gov"]["recorded"] and reads["sam_gov"]["evidence_for"] == "D-FEDERAL.1-1"
    assert reads["sam_gov"]["run_rows"][0]["outcome"] == "quota_reached"
    assert reads["muckrock"]["recorded"] and reads["muckrock"]["evidence_for"] == "F1 NEW-7"
    assert report["out_of_scope"] == 1  # sam_gov (peel-on is excluded separately)
    assert report["untracked_schedulers"] == []


def test_l1_anomaly_table_routes_every_row():
    report, code = _run("l1", "l1_anomaly", _at(16))
    assert code == 0
    assert report["verdict"] == "failed"
    by_id = {f["fleet_id"]: f for f in report["fires"]}
    # a missed fire — no attempt — routes to scheduler/fleet hygiene
    assert by_id["muckrock"]["verdict"] == "failed"
    assert by_id["muckrock"]["routing"]["owner"].startswith("P35.1a/P35.1b")
    # a failed execution routes to the source's connector owner
    assert by_id["usaspending"]["verdict"] == "failed"
    assert "usaspending connector owner" in by_id["usaspending"]["routing"]["owner"]
    # a missing member WORM row is an anomaly routed to completion evidence
    assert by_id["camreg-batch-05"]["verdict"] == "anomaly"
    assert "completion evidence" in by_id["camreg-batch-05"]["routing"]["owner"]
    assert by_id["fbi_cde_agency_registry"]["verdict"] == "ok"
    # the non-zero spine counter lands a stop-and-preserve routing row
    spine = [r for r in report["routing_rows"] if r["fleet_id"] == "(claim spine)"]
    assert spine and "stop and preserve" in spine[0]["trigger"]
    assert len(report["routing_rows"]) == 4


def test_l2_pass_table():
    report, code = _run("l2", "l2_pass", _at(23, "13:00:00"))
    assert code == 0
    assert report["verdict"] == "ok"
    assert [f["fleet_id"] for f in report["fires"]] == [PEEL_ON_SOURCE]
    row = report["fires"][0]
    assert row["execution"]["completed_ok"]
    assert row["completion"]["found"]
    assert report["named_reads"] == []  # named reads belong to the wave legs


def test_l3_pass_table_covers_wave_plus_peel():
    report, code = _run("l3", "l3_pass", _at(23, "13:00:00"))
    assert code == 0
    assert report["verdict"] == "ok"
    ids = [f["fleet_id"] for f in report["fires"]]
    assert PEEL_ON_SOURCE in ids and len(ids) == 5
    assert len(report["named_reads"]) == 2


# ---------------------------------------------------------------------------
# per-fire evaluation edge cases (injected fakes — no fixtures)


def _trigger() -> FleetTrigger:
    return FleetTrigger("x_src", "source", "0 5 1 * *", "j-x", "s-x")


def _assess(fire: datetime) -> dict:
    return {"cron": "0 5 1 * *", "first_fire": fire, "basis": "deployed"}


def test_evaluate_pending_execution():
    fire = _at(0)
    g = FleetGathered()
    g.schedulers = {"s-x": {"state": "ENABLED", "lastAttemptTime": fire.isoformat()}}
    g.executions = {
        "j-x": [
            {
                "metadata": {"name": "j-x-1", "creationTimestamp": fire.isoformat()},
                "status": {"startTime": fire.isoformat()},
            }
        ]
    }
    row = evaluate_fire_row(_trigger(), _assess(fire), g, _at(0, "12:00:00"))
    assert row["verdict"] == "pending"


def test_evaluate_execution_timeout_routes_to_deferral_row():
    fire = _at(-40)
    g = FleetGathered()
    g.schedulers = {"s-x": {"state": "ENABLED", "lastAttemptTime": fire.isoformat()}}
    g.executions = {
        "j-x": [
            {
                "metadata": {"name": "j-x-1", "creationTimestamp": fire.isoformat()},
                "status": {"startTime": fire.isoformat()},
            }
        ]
    }
    row = evaluate_fire_row(_trigger(), _assess(fire), g, _at(0))
    assert row["verdict"] == "failed"
    assert "execution-timeout" in row["routing"]["trigger"]


def test_evaluate_credential_failure_routes_to_operator():
    fire = _at(0)
    g = FleetGathered()
    g.schedulers = {"s-x": {"state": "ENABLED", "lastAttemptTime": fire.isoformat()}}
    g.executions = {
        "j-x": [
            {
                "metadata": {"name": "j-x-1", "creationTimestamp": fire.isoformat()},
                "status": {
                    "completionTime": _at(0, "06:00:00").isoformat(),
                    "failedCount": 1,
                    "cancelledCount": 0,
                },
            }
        ]
    }
    g.run_rows = {
        f"x_src@{fire.date().isoformat()}": [
            {"outcome": "error", "detail": "HTTP 429 quota exceeded", "ingest_run_id": "r"}
        ]
    }
    row = evaluate_fire_row(_trigger(), _assess(fire), g, _at(0, "12:00:00"))
    assert row["verdict"] == "failed"
    assert "operator" in row["routing"]["owner"]


def test_evaluate_missing_completion_is_anomaly():
    fire = _at(0)
    g = FleetGathered()
    g.completions_queried = True
    g.completions = []
    g.schedulers = {"s-x": {"state": "ENABLED", "lastAttemptTime": fire.isoformat()}}
    g.executions = {
        "j-x": [
            {
                "metadata": {"name": "j-x-1", "creationTimestamp": fire.isoformat()},
                "status": {
                    "completionTime": _at(0, "06:00:00").isoformat(),
                    "succeededCount": 1,
                    "failedCount": 0,
                    "cancelledCount": 0,
                },
            }
        ]
    }
    g.run_rows = {f"x_src@{fire.date().isoformat()}": [{"outcome": "ok", "ingest_run_id": "r9"}]}
    row = evaluate_fire_row(_trigger(), _assess(fire), g, _at(0, "12:00:00"))
    assert row["verdict"] == "anomaly"
    assert "completion evidence" in row["routing"]["owner"]


def test_evaluate_disabled_trigger_is_failed():
    fire = _at(0)
    g = FleetGathered()
    g.schedulers = {"s-x": {"state": "DISABLED"}}
    row = evaluate_fire_row(_trigger(), _assess(fire), g, _at(0, "12:00:00"))
    assert row["verdict"] == "failed"
    assert "P35.1a/P35.1b" in row["routing"]["owner"]


def test_evaluate_absent_describe_is_not_evaluable():
    g = FleetGathered()
    g.schedulers = {"s-x": None}
    row = evaluate_fire_row(_trigger(), _assess(_at(0)), g, _at(0, "12:00:00"))
    assert row["verdict"] == "not_evaluable"


# ---------------------------------------------------------------------------
# CLI wiring


def test_cli_requires_project_or_fixtures(capsys, monkeypatch):
    # env can arm the live path (make check sets SIG_GCP_PROJECT) — the
    # "needs project" check must be tested with a bare environment.
    for var in ("SIG_GCP_PROJECT", "SIG_GCP_REGION", "SIG_OPS_GCS_BUCKET", "SIG_STAGING_DSN"):
        monkeypatch.delenv(var, raising=False)
    code = cli.main(
        ["scheduled-firstfire", "--leg", "l1", "--cadence", str(FIXTURES / "cadence.toml")]
    )
    assert code == 2
    assert "SIG_GCP_PROJECT" in capsys.readouterr().err


def test_cli_l1_pass(capsys):
    code = cli.main(
        [
            "scheduled-firstfire",
            "--leg",
            "l1",
            "--fixtures-dir",
            str(FIXTURES / "l1_pass"),
            "--cadence",
            str(FIXTURES / "cadence.toml"),
            "--now",
            _at(16).isoformat(),
        ]
    )
    assert code == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["verdict"] == "ok" and doc["layer"] == "fixture"


def test_cli_l2_queued(capsys):
    code = cli.main(
        [
            "scheduled-firstfire",
            "--leg",
            "l2",
            "--fixtures-dir",
            str(FIXTURES / "l2_queued"),
            "--cadence",
            str(FIXTURES / "cadence.toml"),
            "--now",
            _at(23).isoformat(),
        ]
    )
    assert code == FIRSTFIRE_QUEUED
    doc = json.loads(capsys.readouterr().out)
    assert doc["leg_status"]["rerun_prompt"] == RERUN_PROMPT


def test_cli_bad_leg(capsys):
    with pytest.raises(SystemExit):
        cli.main(
            ["scheduled-firstfire", "--leg", "l9", "--fixtures-dir", str(FIXTURES / "l1_pass")]
        )


# ---------------------------------------------------------------------------
# constants


def test_contract_constants():
    assert L1_WINDOW_END == "2026-10-21T06:09Z"  # future-ok: scheduled: contract constant
    assert PEEL_ON_AFTER == "2026-10-29T12:00Z"  # future-ok: scheduled: contract bound
    assert LEGS == ("l1", "l2", "l3")
    assert {e["trigger"] for e in NAMED_READS} == {"sam_gov", "muckrock"}
    assert RERUN_PROMPT.endswith("live_verification=true")
    assert "248_P34.39b" in RERUN_PROMPT
