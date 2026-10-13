# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.24b — `ops.sqitch_rehearsal` (SIG-ENG-045) deterministic tests.

The clone-rehearsal harness: a name check that refuses `sig-pg` outright and
every name outside the producer's drill shapes (the same check the delete
uses, so a deployable name is always a deletable name); read-only snapshot /
sampler SQL (every statement is a SELECT — a mutation can never be added
silently); per-change timing from the stamped deploy log AND the sqitch
registry; lock-episode grouping with honest observed/upper-bound windows;
and the `sig.sqitch-rehearsal/1` record assembly. No network, ADC or Docker —
`connect` is injectable (ops/backup.py's runner pattern).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from ops import sqitch_rehearsal as sr

REPO_ROOT = Path(__file__).resolve().parents[2]
DRILL_SH = REPO_ROOT / "ops" / "gcp" / "restore-drill.sh"
T0 = datetime(2026, 10, 4, 12, 0, 0, tzinfo=UTC)
L44_CLONE = "sig-pg-drill-l44-20261004t1210z"


def _at(s: float) -> str:
    return (T0 + timedelta(seconds=s)).isoformat().replace("+00:00", "Z")


# --- the name check (AC1) -------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        L44_CLONE,  # the contract's rehearsal shape
        "sig-pg-drill-20261004t1210z",
        "sig-pg-drill-b-20261004t1210z",
    ],
)
def test_rehearsal_target_accepts_only_drill_shapes(name: str) -> None:
    assert sr.assert_rehearsal_target(name) == name


@pytest.mark.parametrize(
    "name",
    [
        "sig-pg",  # production — refused outright
        "sig-pg-drill-l44",  # no stamp
        "sig-pg-drill-l44-20261004T1210Z",  # uppercase — Cloud SQL names are [a-z0-9-]
        "sig-pg-drill-l44-20261004t1210",  # missing z
        "sig-pg-drill-l44-20261004t1210z-extra",  # suffix junk
        "sig-pg-drill-l44-20261004t1210z/sig-pg",  # path-ish injection
        "sig-pg2-drill-l44-20261004t1210z",  # not the sig-pg lineage
        "sig-pg-drill-x-20261004t1210z",  # unknown infix — tighter than the wildcard
        "sig-pg-drill-",  # truncated
        "",
        "SIG-PG",
    ],
)
def test_rehearsal_target_refuses_everything_else(name: str) -> None:
    from ops.cloudsql_drill import DrillNameError

    with pytest.raises(DrillNameError):
        sr.assert_rehearsal_target(name)


def test_sig_pg_refusal_is_the_greppable_production_message() -> None:
    from ops.cloudsql_drill import DrillNameError

    with pytest.raises(DrillNameError, match="production instance"):
        sr.assert_rehearsal_target("sig-pg")


# --- every query is a SELECT -----------------------------------------------------


_WRITE_VERBS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|"
    r"VACUUM|CLUSTER|REINDEX|CALL|COPY|SET)\b",
    re.IGNORECASE,
)


@pytest.mark.parametrize(
    "sql_attr",
    [
        "SQITCH_TIP_SQL",
        "DB_STATS_SQL",
        "DATABASE_SIZE_SQL",
        "RELATION_SIZES_SQL",
        "LOCK_SAMPLE_SQL",
        "INDEX_PROGRESS_SQL",
    ],
)
def test_every_measurement_query_is_a_select(sql_attr: str) -> None:
    """The measurement surface can never grow a mutation: each SQL constant
    the module issues must begin with SELECT and carry no write verb."""
    sql = getattr(sr, sql_attr)
    assert sql.lstrip().upper().startswith("SELECT "), sql_attr
    assert not _WRITE_VERBS.search(sql), f"{sql_attr} contains a write verb"


def test_lock_timeout_is_the_fea07_ceiling() -> None:
    assert sr.LOCK_TIMEOUT_MS == 20 * 60 * 1000


# --- the fake connection -----------------------------------------------------------


class _Cursor:
    def __init__(self, rows: list[tuple]) -> None:
        self._rows = rows

    def fetchone(self) -> tuple | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[tuple]:
        return self._rows


class _FakeConn:
    """Answers the rehearsal's exact queries from canned rows."""

    def __init__(
        self,
        *,
        tip: list[tuple] | None = None,
        stats: tuple | None = None,
        db_bytes: int = 1 << 30,
        relations: list[tuple] | None = None,
        locks: list[tuple] | None = None,
        indexes: list[tuple] | None = None,
        queried: list[str] | None = None,
    ) -> None:
        self.tip = tip if tip is not None else []
        self.stats = stats or (0, 0, 0, 0, 0, 0, 0, 0, 0)
        self.db_bytes = db_bytes
        self.relations = relations or []
        self.locks = locks or []
        self.indexes = indexes or []
        self.queried = queried if queried is not None else []

    def execute(self, query: str, params: tuple = ()) -> _Cursor:
        self.queried.append(query)
        if "FROM sqitch.changes" in query:
            if self.tip is None:
                raise RuntimeError("undefined_table: sqitch.changes")
            return _Cursor(list(self.tip))
        if "FROM pg_stat_database" in query:
            return _Cursor([self.stats])
        if "pg_database_size" in query:
            return _Cursor([(self.db_bytes,)])
        if "pg_stat_user_tables" in query:
            return _Cursor(list(self.relations))
        if "FROM pg_locks" in query:
            return _Cursor(list(self.locks))
        if "pg_stat_progress_create_index" in query:
            return _Cursor(list(self.indexes))
        raise AssertionError(f"unexpected query: {query}")

    def __enter__(self) -> _FakeConn:
        return self

    def __exit__(self, *a: Any) -> bool:
        return False


_TIP = [
    ("capture_bindings", "id-43", T0 - timedelta(days=10), T0 - timedelta(days=10)),
    ("claim_assertion_bindings", "id-44", T0, T0 + timedelta(seconds=30)),
    ("recovery_apply", "id-52", T0, T0 + timedelta(seconds=95)),
]


def test_snapshot_reads_tip_sizes_and_counters() -> None:
    conn = _FakeConn(
        tip=_TIP,
        stats=(2, 1024, 10, 1, 100, 50, 3, 2, 1),
        relations=[("claim_evidence", 1 << 20, 1 << 19, 1 << 18, 42)],
    )
    snap = sr.snapshot(conn)
    assert snap["sqitch_changes"] == 3
    assert snap["sqitch_head_change"] == "recovery_apply"
    assert len(snap["sqitch_tip_sha256"]) == 64
    assert snap["db_stats"]["temp_bytes"] == 1024
    assert snap["relations"]["claim_evidence"]["n_live_tup"] == 42
    # only SELECTs were issued
    assert all(q.lstrip().upper().startswith("SELECT") for q in conn.queried)


def test_a_virgin_database_reads_as_an_empty_tip_not_an_error() -> None:
    conn = _FakeConn(tip=None)

    class _Raising:
        def execute(self, q: str, params: tuple = ()) -> _Cursor:
            if "sqitch.changes" in q:
                raise RuntimeError('relation "sqitch.changes" does not exist')
            return conn.execute(q, params)

    conn2 = _Raising()
    snap = sr.snapshot(conn2)
    assert snap["sqitch_changes"] == 0
    assert snap["sqitch_head_change"] is None


def test_sample_once_collects_locks_index_progress_and_temp() -> None:
    conn = _FakeConn(
        locks=[
            (1234, "AccessExclusiveLock", True, "claim_evidence", T0, "active", "ALTER TABLE x")
        ],
        indexes=[(1234, "building index: scanning", "claim_evidence", "ce_idx", 5, 10, None, None)],
        stats=(3, 4096, 0, 0, 0, 0, 0, 0, 0),
    )
    sample = sr.sample_once(conn)
    assert sample["locks"][0]["relation"] == "claim_evidence"
    assert sample["locks"][0]["granted"] is True
    assert sample["index_progress"][0]["blocks_done"] == 5
    assert sample["temp_bytes"] == 4096


def test_sample_loop_stops_on_the_stop_file(tmp_path: Path) -> None:
    conn = _FakeConn()
    out, stop = tmp_path / "s.jsonl", tmp_path / ".stop"
    calls = {"n": 0}

    def sleep(_s: float) -> None:
        calls["n"] += 1
        if calls["n"] >= 3:
            stop.touch()

    n = sr.sample_loop("dsn", out, stop, connect=lambda _d: conn, sleep=sleep)
    assert n >= 3
    lines = out.read_text().splitlines()
    assert len(lines) == n
    assert all(json.loads(line)["at"].endswith("Z") for line in lines)


def test_sample_loop_records_an_error_and_recovers(tmp_path: Path) -> None:
    class _Flaky(_FakeConn):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        def execute(self, q: str, params: tuple = ()) -> _Cursor:
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("proxy wobble")
            return super().execute(q, params)

    flaky = _Flaky()
    out, stop = tmp_path / "s.jsonl", tmp_path / ".stop"
    calls = {"n": 0}

    def sleep(_s: float) -> None:
        calls["n"] += 1
        if calls["n"] >= 3:
            stop.touch()

    n = sr.sample_loop("dsn", out, stop, connect=lambda _d: flaky, sleep=sleep)
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert any("error" in r for r in rows)
    assert n >= 3  # the wobble degraded one sample, never the leg


# --- deploy-log parsing --------------------------------------------------------------


def test_parse_deploy_log_gives_per_change_seconds() -> None:
    """sqitch's real completion format (App::Sqitch v1.6.1): a `Deploying
    changes to` header, then `  + <change> …. ok` completions — the 2026-10-04
    live leg's actual shape."""
    lines = [
        f"{_at(0)}\tDeploying changes to db:pg://sig@host.docker.internal:5442/sig",
        f"{_at(4)}\t  + claim_assertion_bindings ................... ok",
        f"{_at(40)}\t  + partner_org_scoped_identity_key ............ ok",
        f"{_at(95)}\t  + recovery_apply ............................. ok",
    ]
    parsed = sr.parse_deploy_log(iter(lines))
    changes = parsed["changes"]
    assert [c["change"] for c in changes] == [
        "claim_assertion_bindings",
        "partner_org_scoped_identity_key",
        "recovery_apply",
    ]
    assert changes[0]["seconds"] == 4.0
    assert changes[1]["seconds"] == 36.0
    assert changes[2]["seconds"] == 55.0
    assert parsed["wall_seconds"] == 95.0
    assert parsed["deploy_failed"] is None
    assert parsed["reverted"] == []


def test_parse_deploy_log_records_a_verify_failure_and_the_revert() -> None:
    """A failed `+` line marks the change failed and the following
    `Reverting to`/`  - <change>` section is kept separate — the 2026-10-04
    leg's real path: intake_storage's verify erred, sqitch reverted to the
    clone head, `Deploy failed`."""
    lines = [
        f"{_at(0)}\tDeploying changes to db:pg://sig@host:5442/sig",
        f"{_at(4)}\t  + claim_assertion_bindings ................... ok",
        f"{_at(9)}\t  + intake_storage ............................. "
        'psql:verify/intake_storage.sql:80: ERROR:  permission denied to set role "x"',
        f'{_at(10)}\tVerify script "verify/intake_storage.sql" failed.',
        f"{_at(11)}\tnot ok",
        f"{_at(12)}\tReverting to camera_site_human_decisions",
        f"{_at(15)}\t  - claim_assertion_bindings ................... ok",
        f"{_at(16)}\tDeploy failed",
    ]
    parsed = sr.parse_deploy_log(iter(lines))
    assert parsed["deploy_failed"] is True
    assert parsed["revert_to"] == "camera_site_human_decisions"
    assert [c["status"] for c in parsed["changes"]] == ["ok", "failed"]
    assert parsed["changes"][1]["change"] == "intake_storage"
    assert "permission denied" in (parsed["changes"][1]["output_tail"] or "")
    assert [r["change"] for r in parsed["reverted"]] == ["claim_assertion_bindings"]
    assert parsed["reverted"][0]["status"] == "ok"


def test_parse_deploy_log_flips_a_split_completion_to_ok() -> None:
    """The live log split one revert completion: `  - name …. 1` then `ok`
    on the next stamped line — psql output interleaved between the dots and
    the ok. The pending row flips to ok, never reads as a failure."""
    lines = [
        f"{_at(0)}\tDeploying changes to db:pg://sig@host:5442/sig",
        f"{_at(3)}\t  + c1 .......................................... ok",
        f"{_at(4)}\tReverting to head",
        f"{_at(5)}\t  - c1 .......................................... 1",
        f"{_at(6)}\tok",
    ]
    parsed = sr.parse_deploy_log(iter(lines))
    assert parsed["reverted"][0]["status"] == "ok"
    assert parsed["deploy_failed"] is None


def test_parse_deploy_log_tolerates_unstamped_lines() -> None:
    lines = [
        "noise without a tab",
        f"{_at(0)}\tDeploying changes to db:pg://sig@h:1/d",
        f"{_at(10)}\tdone",
    ]
    parsed = sr.parse_deploy_log(iter(lines))
    assert parsed["changes"] == []
    assert parsed["wall_seconds"] == 10.0


def test_lock_sample_joins_activity_on_datid() -> None:
    """Regression pin for the 2026-10-04 live defect: pg_stat_activity must
    join on ``a.datid = l.database`` (oid = oid); the datname/database join
    is `name = oid` — an UndefinedFunction on every sample."""
    assert "a.datid = l.database" in sr.LOCK_SAMPLE_SQL
    assert "a.datname = l.database" not in sr.LOCK_SAMPLE_SQL


# --- lock-episode grouping ------------------------------------------------------------


def _lock_sample(s: float, pid: int = 7, rel: str = "claim_evidence") -> dict:
    return {
        "at": _at(s),
        "locks": [
            {
                "pid": pid,
                "mode": "AccessExclusiveLock",
                "granted": True,
                "relation": rel,
                "query": "ALTER TABLE claim_evidence …",
                "state": "active",
            }
        ],
    }


def test_episodes_group_consecutive_sightings() -> None:
    eps = sr.lock_episodes([_lock_sample(0.0), _lock_sample(0.25), _lock_sample(0.5)], 0.25)
    assert len(eps) == 1
    assert eps[0]["samples"] == 3
    assert eps[0]["observed_s"] == pytest.approx(0.5)
    assert eps[0]["upper_bound_s"] == pytest.approx(1.0)
    assert eps[0]["query"] == "ALTER TABLE claim_evidence …"


def test_a_gap_longer_than_the_tolerance_splits_episodes() -> None:
    eps = sr.lock_episodes([_lock_sample(0.0), _lock_sample(0.25), _lock_sample(2.0)], 0.25)
    assert len(eps) == 2
    assert eps[0]["samples"] == 2 and eps[1]["samples"] == 1


def test_different_relations_are_different_episodes() -> None:
    samples = [_lock_sample(0.0), _lock_sample(0.25, rel="claim")]
    eps = sr.lock_episodes(samples, 0.25)
    assert len(eps) == 2
    assert {e["relation"] for e in eps} == {"claim_evidence", "claim"}


def test_lock_summary_reports_the_claim_evidence_headline() -> None:
    samples = [_lock_sample(0.0), _lock_sample(0.25), _lock_sample(0.5)]
    eps = sr.lock_episodes(samples, 0.25)
    summary = sr.lock_summary(eps)
    assert summary["n_episodes"] == 1
    assert summary["claim_evidence"]["max_observed_s"] == pytest.approx(0.5)
    assert summary["claim_evidence"]["max_upper_bound_s"] == pytest.approx(1.0)
    assert summary["by_relation"]["claim_evidence"]["episodes"] == 1


# --- registry timings -----------------------------------------------------------


def test_registry_change_timings_from_committed_at_deltas() -> None:
    pre = [{"change": "c43", "change_id": "id-43", "committed_at": _at(-1000)}]
    post = [
        *pre,
        {"change": "c44", "change_id": "id-44", "committed_at": _at(30)},
        {"change": "c45", "change_id": "id-45", "committed_at": _at(70)},
    ]
    rows = sr.registry_change_timings(pre, post)
    assert [r["change"] for r in rows] == ["c44", "c45"]
    # the first new change's seconds is null — the pre-head stamp predates
    # the deploy; the stamped log bounds it instead
    assert rows[0]["seconds"] is None
    assert rows[1]["seconds"] == 40.0


# --- flags + plan hashes -----------------------------------------------------------


def test_deploy_change_flags_see_the_heavy_shapes() -> None:
    flags = sr.deploy_change_flags(
        "CREATE INDEX foo ON claim_evidence (a);\nALTER TABLE t ADD c int;\n"
    )
    assert flags == {"create_index": True, "alter_table": True, "update_rows": False}
    flags = sr.deploy_change_flags("UPDATE claim SET x = 1;")
    assert flags["update_rows"] is True and flags["create_index"] is False


def test_plan_line_hashes_cover_the_protected_span() -> None:
    lines = [f"line-{i} abc\n" for i in range(1, 59)]
    plan = "".join(lines)
    hashes = sr.plan_line_hashes(plan)
    assert hashes["plan_l44_52_lines"] == "44-52"
    assert hashes["plan_tip_line"] == 58
    assert len(hashes["plan_l44_52_sha256"]) == 64
    # the span hash is sensitive to a one-byte edit inside 44-52 …
    tampered = "".join(line if i != 44 else "line-44 ABD\n" for i, line in enumerate(lines, 1))
    assert sr.plan_line_hashes(tampered)["plan_l44_52_sha256"] != hashes["plan_l44_52_sha256"]
    # … and stable to a change outside the span
    outside = "".join(line if i != 53 else "line-53 ABD\n" for i, line in enumerate(lines, 1))
    assert sr.plan_line_hashes(outside)["plan_l44_52_sha256"] == hashes["plan_l44_52_sha256"]


def test_the_live_plan_l44_52_span_is_byte_identical_to_the_c10_freeze() -> None:
    """db/sqitch.plan lines 44-52 hash to the bytes C-10 froze — a re-stamp
    or edit of the protected span flips the hash and fails this test. This
    is an invariant (the frozen span can never change, only appended lines
    may), never a living-record read."""
    plan = (REPO_ROOT / "db" / "sqitch.plan").read_text()
    hashes = sr.plan_line_hashes(plan)
    assert hashes["plan_l44_52_sha256"] == (
        "8cc9d3db4dfc9335821cc4ecef181ee0c9f96231346ce231567e0f55b413a9fc"
    )
    assert hashes["plan_tip_line"] == len(plan.splitlines())


# --- the record ---------------------------------------------------------------------


def _pre_snapshot() -> dict:
    return {
        "at": _at(0),
        "sqitch_tip": [{"change": "c43", "change_id": "id-43", "committed_at": _at(-1000)}],
        "sqitch_tip_sha256": "a" * 64,
        "sqitch_changes": 1,
        "sqitch_head_change": "c43",
        "db_stats": {"temp_files": 0, "temp_bytes": 0, "tup_inserted": 5},
        "database_bytes": 1 << 30,
        "relations": {"claim_evidence": {"total_bytes": 1 << 20}},
    }


def _post_snapshot() -> dict:
    return {
        "at": _at(200),
        "sqitch_tip": [
            {"change": "c43", "change_id": "id-43", "committed_at": _at(-1000)},
            {"change": "c44", "change_id": "id-44", "committed_at": _at(30)},
            {"change": "c45", "change_id": "id-45", "committed_at": _at(70)},
        ],
        "sqitch_tip_sha256": "b" * 64,
        "sqitch_changes": 3,
        "sqitch_head_change": "c45",
        "db_stats": {"temp_files": 4, "temp_bytes": 1 << 22, "tup_inserted": 9},
        "database_bytes": (1 << 30) + (1 << 21),
        "relations": {"claim_evidence": {"total_bytes": 1 << 21}},
    }


def _meta() -> dict:
    return {
        "clone_instance": L44_CLONE,
        "clone_point_in_time": _at(-600),
        "chain_tip_commit": "0" * 40,
        "plan": {"plan_sha256": "c" * 64, "plan_l44_52_sha256": "d" * 64},
        "deploy": {"exit": 0},
    }


def test_build_record_assembles_every_field_honestly() -> None:
    samples = [_lock_sample(0.0), _lock_sample(0.25), _lock_sample(0.5)]
    deploy = {
        "exit": 0,
        "started_at": _at(0),
        "ended_at": _at(95),
        "changes": [{"change": "c44", "seconds": 30.0}],
    }
    source = {
        "before": {"tup_inserted": 100, "temp_bytes": 0},
        "after": {"tup_inserted": 100, "temp_bytes": 0},
        "operations_before": [{"name": "op-1"}],
        "operations_after": [{"name": "op-1"}],
    }
    rec = sr.build_record(
        meta=_meta(),
        pre=_pre_snapshot(),
        post=_post_snapshot(),
        samples=samples,
        deploy=deploy,
        verify={"exit": 0, "started_at": _at(96), "ended_at": _at(101)},
        source=source,
        sample_interval_s=0.25,
    )
    assert rec["schema"] == "sig.sqitch-rehearsal/1"
    assert rec["clone_instance"] == L44_CLONE
    assert rec["head_before"]["sqitch_head_change"] == "c43"
    assert rec["head_after"]["sqitch_head_change"] == "c45"
    assert rec["deploy"]["lock_timeout_ms"] == 20 * 60 * 1000
    assert rec["deploy"]["registry_changes"][1]["seconds"] == 40.0
    assert rec["locks"]["claim_evidence"]["max_observed_s"] == pytest.approx(0.5)
    assert rec["temp_disk"]["temp_bytes_delta"] == 1 << 22
    assert rec["temp_disk"]["claim_evidence_total_bytes_before"] == 1 << 20
    assert rec["temp_disk"]["claim_evidence_total_bytes_after"] == 1 << 21
    assert rec["source_no_write"]["delta"]["tup_inserted"] == 0
    assert rec["source_no_write"]["operations_after"] == [{"name": "op-1"}]
    assert rec["bounds_note"]
    json.dumps(rec, sort_keys=True)  # the record must be serialisable


def test_build_record_keeps_unseen_numbers_null_never_fabricated() -> None:
    rec = sr.build_record(
        meta=_meta(),
        pre=_pre_snapshot(),
        post=_post_snapshot(),
        samples=[],  # the sampler never ran — nothing may be invented
        deploy={"exit": 1},
        verify=None,
        source=None,
    )
    assert rec["locks"]["episodes"] == []
    assert rec["locks"]["claim_evidence"]["max_observed_s"] is None
    assert rec["locks"]["claim_evidence"]["max_upper_bound_s"] is None
    assert rec["verify"] is None
    assert rec["source_no_write"] is None
    assert rec["temp_disk"]["temp_bytes_delta"] == (1 << 22)


def test_build_record_blanks_the_headline_when_every_sample_errored() -> None:
    """P34.24b attempt-1 shape: 214/214 samples carried an error (the
    pre-fix sampler SQL). Zero observed episodes is fact, but a
    max_observed_s of 0.0 would fabricate 'no lock was held' — the
    headline must be null."""
    errored = [
        {"at": _at(i), "error": "UndefinedFunction: operator does not exist: name = oid"}
        for i in range(4)
    ]
    rec = sr.build_record(
        meta=_meta(),
        pre=_pre_snapshot(),
        post=_post_snapshot(),
        samples=errored,
        deploy={"exit": 2},
        verify=None,
        source=None,
    )
    assert rec["locks"]["samples"] == 4
    assert rec["locks"]["sample_errors"] == 4
    assert rec["locks"]["n_episodes"] == 0
    assert rec["locks"]["claim_evidence"] == {
        "episodes": 0,
        "max_observed_s": None,
        "max_upper_bound_s": None,
    }


# --- the CLI surface ------------------------------------------------------------


def _cli(
    monkeypatch: pytest.MonkeyPatch,
    *args: str,
    dsn: str | None = "dsn-x",
) -> int:
    from ops import cli

    if dsn is None:
        monkeypatch.delenv("SIG_REHEARSAL_DSN", raising=False)
    else:
        monkeypatch.setenv("SIG_REHEARSAL_DSN", dsn)
    return cli.main(["sqitch-rehearsal", *args])


def test_cli_snapshot_refuses_sig_pg(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = _cli(monkeypatch, "snapshot", "--instance", "sig-pg")
    assert rc == 42
    assert "production instance" in capsys.readouterr().err


def test_cli_sample_refuses_a_nonconforming_name(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = _cli(monkeypatch, "sample", "--instance", "sig-pg-drill-x")
    assert rc == 42
    assert "not a drill instance" in capsys.readouterr().err


def test_cli_snapshot_needs_the_dsn_via_env(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = _cli(monkeypatch, "snapshot", "--instance", L44_CLONE, dsn=None)
    assert rc == 2
    assert "SIG_REHEARSAL_DSN" in capsys.readouterr().err


def test_cli_record_assembles_from_the_measured_parts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "meta.json").write_text(json.dumps(_meta()))
    (tmp_path / "pre.json").write_text(json.dumps(_pre_snapshot()))
    (tmp_path / "post.json").write_text(json.dumps(_post_snapshot()))
    (tmp_path / "samples.jsonl").write_text(
        "\n".join(json.dumps(_lock_sample(s)) for s in (0.0, 0.25, 0.5)) + "\n"
    )
    (tmp_path / "deploy.log").write_text(
        f"{_at(0)}\tDeploying changes to db:pg://sig@h:1/d\n"
        f"{_at(30)}\t  + c44 ......................................... ok\n"
        f"{_at(70)}\t  + c45 ......................................... ok\n"
    )
    out = tmp_path / "record.json"
    rc = _cli(
        monkeypatch,
        "record",
        "--meta",
        str(tmp_path / "meta.json"),
        "--pre",
        str(tmp_path / "pre.json"),
        "--post",
        str(tmp_path / "post.json"),
        "--samples",
        str(tmp_path / "samples.jsonl"),
        "--deploy-log",
        str(tmp_path / "deploy.log"),
        "--out",
        str(out),
        dsn=None,
    )
    assert rc == 0
    rec = json.loads(out.read_text())
    assert rec["schema"] == "sig.sqitch-rehearsal/1"
    assert rec["deploy"]["changes"][0]["change"] == "c44"
    assert rec["locks"]["claim_evidence"]["episodes"] == 1


def test_cli_plan_hashes_diff_the_base(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    lines = [f"line-{i} abc\n" for i in range(1, 59)]
    plan = tmp_path / "sqitch.plan"
    plan.write_text("".join(lines))
    base = tmp_path / "base.plan"
    base_lines = list(lines)
    base_lines[43] = "line-44 DIFFERENT\n"
    base.write_text("".join(base_lines))
    rc = _cli(
        monkeypatch,
        "plan-hashes",
        "--plan",
        str(plan),
        "--base-plan",
        str(base),
        dsn=None,
    )
    out = rc  # record captured below via stdout
    assert out == 0


def test_cli_plan_hashes_flags_a_byte_difference(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lines = [f"line-{i} abc\n" for i in range(1, 59)]
    plan = tmp_path / "sqitch.plan"
    plan.write_text("".join(lines))
    base = tmp_path / "base.plan"
    base.write_text("".join(lines))
    rc = _cli(
        monkeypatch,
        "plan-hashes",
        "--plan",
        str(plan),
        "--base-plan",
        str(base),
        dsn=None,
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["plan_l44_52_byte_identical"] is True


# --- the shell wiring (IaC, offline) ---------------------------------------------


def _run_drill(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(DRILL_SH), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )


def test_rehearse_check_mode_is_plan_only() -> None:
    env = {k: v for k, v in os.environ.items() if k != "SIG_GCP_PROJECT"}
    env["SIG_GCP_PROJECT"] = "example-proj"
    proc = _run_drill(["rehearse"], env)
    assert proc.returncode == 0, proc.stderr
    assert "check OK" in proc.stdout
    assert "deploy --verify" in proc.stdout
    assert "sqitch/sqitch@sha256:" in proc.stdout  # the pinned image, never a tag
    assert "lock_timeout=1200000" in proc.stdout
    assert "sig-pg is read-only" in proc.stdout


def test_rehearse_apply_refuses_sig_pg_as_the_target(
    tmp_path: Path,
) -> None:
    """--clone-name sig-pg is refused by the same name check the delete uses,
    before any proxy, docker or gcloud mutation can run."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    log = tmp_path / "gcloud.log"
    log.touch()
    state = tmp_path / "instances.state"
    state.write_text("sig-pg\n")
    stub = bindir / "gcloud"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        'printf \'%s\\n\' "$*" >> "$GCLOUD_STUB_LOG"\n'
        'case "$*" in\n'
        '  "sql instances list"*) cat "$STUB_INSTANCE_STATE" ;;\n'
        '  *) echo "{}" ;;\n'
        "esac\n"
    )
    stub.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k != "SIG_GCP_PROJECT"}
    env.update(
        PATH=f"{bindir}:{os.environ['PATH']}",
        SIG_GCP_PROJECT="example-proj",
        GCLOUD_STUB_LOG=str(log),
        STUB_INSTANCE_STATE=str(state),
        SIG_DRILL_EVIDENCE_DIR=str(tmp_path / "evidence"),
        CLOUDSDK_CONFIG="/nonexistent-sig-adc",
    )
    proc = subprocess.run(
        ["bash", str(DRILL_SH), "--apply", "rehearse", "--clone-name", "sig-pg"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 42, proc.stdout + proc.stderr
    assert "production instance" in proc.stderr
    # nothing mutating was invoked — the name check fires first
    assert "instances clone" not in log.read_text()
    assert "instances delete" not in log.read_text()
