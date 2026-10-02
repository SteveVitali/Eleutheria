# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.6 — `ops.cloudsql_drill` (SIG-OPS-001, ADR-175) deterministic tests.

The parity engine is exercised against an injected fake connection whose rows
are instants, so the at-T predicate semantics are really evaluated: the source
keeps writing after T while the PITR clone is frozen at T, and parity at T must
still hold exactly. Name-check tests pin the delete-safety rule: `sig-pg` and
every nonconforming name are refused. No network, ADC or Docker — `connect` is
injected (ops/backup.py's runner pattern).
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from ops import cloudsql_drill as cd

REPO_ROOT = Path(__file__).resolve().parents[2]
T = datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC)
DRILL = "sig-pg-drill-20261002t1210z"


# --- the fake connection ------------------------------------------------------


class _Cursor:
    def __init__(self, rows: list[tuple]) -> None:
        self._rows = rows

    def fetchone(self) -> tuple | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[tuple]:
        return self._rows


class _FakeConn:
    """Answers exactly the drill's queries from canned per-row instants.

    ``rows`` maps table -> list of commit instants (a row exists at T iff its
    instant <= T); the table DRILL_TABLES marks unbounded gets ``None`` rows
    that only the bare ``count(*)`` counts — mirroring that a real unbounded
    table can't answer a WHERE clause.

    The fake also serves the ``information_schema.columns`` read the engine
    makes to pick the *effective* instant map: every table in ``rows`` is
    present with every column its instant expression needs, minus
    ``missing_columns``/``missing_tables`` (a pre-P32.4 spine drops
    ``claim_evidence.bound_at`` and ``spine_watermark`` — the shape the live
    2026-10-02 drill actually met).
    """

    def __init__(
        self,
        *,
        rows: dict[str, list[datetime | None]],
        watermark: list[tuple] | None = None,
        sqitch: list[tuple] | None = None,
        postgis: str | None = "3.4.0",
        newest: datetime | None = None,
        queried: list[str] | None = None,
        missing_columns: frozenset[str] = frozenset(),
        missing_tables: frozenset[str] = frozenset(),
    ) -> None:
        self.rows = rows
        self.watermark = watermark if watermark is not None else []
        self.watermark_absent = watermark is None
        self.sqitch = sqitch or []
        self.postgis = postgis
        self.newest = newest
        self.queried = queried if queried is not None else []
        self.missing_columns = missing_columns
        self.missing_tables = missing_tables

    def _surface(self) -> list[tuple]:
        out: list[tuple] = []
        for table in self.rows:
            if table in self.missing_tables:
                continue
            out.append((table, "id"))  # a present table always has some column
            for col in cd.DRILL_INSTANT_COLUMNS.get(table, ()):
                if f"{table}.{col}" not in self.missing_columns:
                    out.append((table, col))
        if not self.watermark_absent:
            out.append((cd.WATERMARK_TABLE, "facet"))
        return out

    def execute(self, query: str, params: tuple = ()) -> _Cursor:
        self.queried.append(query)
        if "FROM information_schema.columns" in query:
            return _Cursor(self._surface())
        m = re.match(r"^SELECT count\(\*\) FROM (\w+)(?: WHERE (.+) <= %s)?$", query)
        if m:
            table, pred = m.group(1), m.group(2)
            instants = self.rows.get(table, [])
            if pred is None:
                return _Cursor([(len(instants),)])
            at = params[0]
            return _Cursor([(sum(1 for i in instants if i is not None and i <= at),)])
        if "FROM spine_watermark" in query:
            assert not self.watermark_absent, "watermark table read while absent"
            return _Cursor(list(self.watermark))
        if "FROM sqitch.changes" in query:
            return _Cursor(list(self.sqitch))
        if "FROM pg_extension" in query:
            return _Cursor([(self.postgis,)] if self.postgis else [])
        if "max(lower(sys_period)) FROM claim" in query:
            return _Cursor([(self.newest,)])
        raise AssertionError(f"unexpected query: {query}")

    def __enter__(self) -> _FakeConn:
        return self

    def __exit__(self, *a: Any) -> bool:
        return False


def _base_rows(seed: int = 0) -> dict[str, list[datetime | None]]:
    """Five rows at/before T per bounded table + three rows after T on the
    'still-writing source' tables (the source-side asymmetry the drill must see
    through)."""
    before = [T - timedelta(hours=i + 1) for i in range(5)]
    after = [T + timedelta(hours=i + 1) for i in range(3)]
    return {
        "claim": before + after,
        "claim_evidence": before + after,
        "evidence_capture": before,
        "evidence_artifact": [None] * 7,  # unbounded — total only
        "entity": before + after,
        "ingest_run": before,
        "ingest_run_completion": before,
        "resolution": before,
        "contradiction": before,
        "coverage_record": before + after,
    }


def _wm() -> list[tuple]:
    return [
        ("claim", 5, 5, T - timedelta(hours=1)),
        ("resolution", 5, 5, T - timedelta(hours=1)),
    ]


def _sq() -> list[tuple]:
    return [("baseline", "id-baseline"), ("p34_5", "id-p34_5")]


def _conn_pair(
    *,
    clone_drop: str | None = None,
    source_extra_watermark: bool = False,
    clone_sqitch_extra: bool = False,
    clone_postgis: str | None = "3.4.0",
    clone_newest: datetime | None = None,
    clone_queries: list[str] | None = None,
    pre_contract_schema: bool = False,
    clone_missing_table: str | None = None,
) -> tuple[dict[str, _FakeConn], Any]:
    src_rows = _base_rows()
    cln_rows = {
        # the clone is frozen at T: only the <=T instants exist
        t: [i for i in v if i is None or i <= T]
        for t, v in src_rows.items()
    }
    if clone_drop:
        cln_rows[clone_drop] = cln_rows[clone_drop][:-1]  # one row lost
    # A pre-shared_temporal_contract spine (the 2026-10-02 live drill met one):
    # no claim_evidence.bound_at column, no spine_watermark table at all. And
    # the live spine was quiescent between materialize runs — no claim_evidence
    # row landed after T, which is exactly what an unbounded parity count needs
    # (a post-T write there is indistinguishable from clone drift, by design).
    if pre_contract_schema:
        src_rows["claim_evidence"] = [
            i for i in src_rows["claim_evidence"] if i is not None and i <= T
        ]
        cln_rows["claim_evidence"] = list(src_rows["claim_evidence"])
    missing_cols = frozenset({"claim_evidence.bound_at"}) if pre_contract_schema else frozenset()
    wm = None if pre_contract_schema else _wm()
    wm_src = (
        wm if wm is None else (_wm() + [("new_facet", 1, 1, T)]) if source_extra_watermark else wm
    )
    src = _FakeConn(
        rows=src_rows,
        watermark=wm_src,
        sqitch=_sq(),
        newest=T - timedelta(minutes=4),
        missing_columns=missing_cols,
    )
    cln = _FakeConn(
        rows=cln_rows,
        watermark=wm,
        sqitch=_sq() + ([("drift_change", "id-x")] if clone_sqitch_extra else []),
        postgis=clone_postgis,
        newest=clone_newest if clone_newest is not None else T - timedelta(minutes=4),
        queried=clone_queries,
        missing_columns=missing_cols,
        missing_tables=frozenset({clone_missing_table} if clone_missing_table else ()),
    )
    conns = {"source": src, "clone": cln}
    order = iter([src, cln])

    def connect(_dsn: str) -> _FakeConn:
        return next(order)

    return conns, connect


# --- name checking -------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "sig-pg-drill-20261002t1210z",
        "sig-pg-drill-b-20261002t1210z",
        "sig-pg-drill-19991231t2359z",
    ],
)
def test_assert_drill_name_accepts_only_the_producer_shape(name: str) -> None:
    assert cd.assert_drill_name(name) == name


@pytest.mark.parametrize(
    "name",
    [
        "sig-pg",  # production — never
        "sig-pg-drill",  # no stamp
        "sig-pg-drill-x",  # nonconforming stamp
        "sig-pg-drill-20261002T1210Z",  # uppercase — Cloud SQL names are [a-z0-9-] only
        "sig-pg-drill-20261002t1210",  # missing Z
        "sig-pg-drill-2026100",  # truncated stamp
        "sig-pg-drill-20261002t1210z-extra",  # suffix junk
        "sig-pg-drill-20261002t1210z/sig-pg",  # path-ish injection
        "sig-pg2-drill-20261002t1210z",  # not the sig-pg lineage
        "",
        "SIG-PG",
    ],
)
def test_assert_drill_name_refuses_everything_else(name: str) -> None:
    with pytest.raises(cd.DrillNameError):
        cd.assert_drill_name(name)


def test_sig_pg_refusal_is_a_distinct_greppable_message() -> None:
    with pytest.raises(cd.DrillNameError, match="production instance"):
        cd.assert_drill_name("sig-pg")


# --- parity semantics ------------------------------------------------------------


def test_parity_exact_at_t_while_the_source_keeps_writing() -> None:
    """The source has rows after T; the clone is frozen at T. Parity AT T must
    still be exact — this is the contract's whole point."""
    conns, connect = _conn_pair()
    rec = cd.drill_parity(
        source_dsn="dsn-source",
        clone_dsn="dsn-clone",
        at=T,
        clone_instance=DRILL,
        clone_started_at=T - timedelta(minutes=20),
        verified_at=T + timedelta(minutes=5),
        connect=connect,
    )
    assert rec.reproduced
    for t in rec.tables:
        assert t.equal, t.table
        assert t.clone_at_t == 5 if t.bounded_by_t else t.clone_at_t == 7
    # RTO/RPO are measured, not fabricated.
    assert rec.rto_seconds == pytest.approx(1500.0)  # 25 min clone-submit -> verified
    assert rec.rpo_seconds == pytest.approx(240.0)  # T - newest clone instant


def test_per_table_predicate_is_really_applied() -> None:
    """The clone conn must see `WHERE <instant> <= %s` for every bounded table
    and a bare count for evidence_artifact (no instant column)."""
    queried: list[str] = []
    _, connect = _conn_pair(clone_queries=queried)
    cd.drill_parity(source_dsn="s", clone_dsn="c", at=T, clone_instance=DRILL, connect=connect)
    bounded = sum(1 for q in queried if " <= %s" in q)
    assert bounded == len([e for e in cd.DRILL_TABLES.values() if e is not None])
    assert any(q == "SELECT count(*) FROM evidence_artifact" for q in queried), (
        "evidence_artifact must be counted unbounded"
    )


def test_a_missing_clone_row_fails_closed() -> None:
    _, connect = _conn_pair(clone_drop="claim")
    rec = cd.drill_parity(
        source_dsn="s", clone_dsn="c", at=T, clone_instance=DRILL, connect=connect
    )
    claim = next(t for t in rec.tables if t.table == "claim")
    assert not claim.equal
    assert not rec.reproduced


def test_watermark_drift_fails_closed() -> None:
    _, connect = _conn_pair(source_extra_watermark=True)
    rec = cd.drill_parity(
        source_dsn="s", clone_dsn="c", at=T, clone_instance=DRILL, connect=connect
    )
    assert not rec.watermark_equal
    assert not rec.reproduced
    # the record keeps BOTH sides visible — never reconciled away
    assert "new_facet" in rec.watermark_source
    assert "new_facet" not in rec.watermark_clone


def test_sqitch_tip_drift_fails_closed() -> None:
    _, connect = _conn_pair(clone_sqitch_extra=True)
    rec = cd.drill_parity(
        source_dsn="s", clone_dsn="c", at=T, clone_instance=DRILL, connect=connect
    )
    assert not rec.sqitch_equal
    assert not rec.reproduced


def test_missing_postgis_fails_closed() -> None:
    _, connect = _conn_pair(clone_postgis=None)
    rec = cd.drill_parity(
        source_dsn="s", clone_dsn="c", at=T, clone_instance=DRILL, connect=connect
    )
    assert rec.postgis_clone is None
    assert not rec.postgis_ok
    assert not rec.reproduced


def test_drill_parity_refuses_production_as_clone_target() -> None:
    with pytest.raises(cd.DrillNameError, match="production instance"):
        cd.drill_parity(
            source_dsn="s",
            clone_dsn="c",
            at=T,
            clone_instance="sig-pg",
            connect=lambda _d: _FakeConn(rows={}),
        )


def test_unbounded_table_is_marked_not_bounded_by_t() -> None:
    _, connect = _conn_pair()
    rec = cd.drill_parity(
        source_dsn="s", clone_dsn="c", at=T, clone_instance=DRILL, connect=connect
    )
    artifact = next(t for t in rec.tables if t.table == "evidence_artifact")
    assert artifact.bounded_by_t is False
    assert artifact.equal


def test_pre_contract_spine_parity_is_exact_and_honest() -> None:
    """The deployed schema the 2026-10-02 live drill met: claim_evidence has no
    bound_at and spine_watermark does not exist (prod sat at the P31.11 sqitch
    tip). Parity must still be exact — claim_evidence degrades to an unbounded
    count, the watermark records absent-on-both, and the record says so."""
    _, connect = _conn_pair(pre_contract_schema=True)
    rec = cd.drill_parity(
        source_dsn="s", clone_dsn="c", at=T, clone_instance=DRILL, connect=connect
    )
    assert rec.reproduced
    assert rec.schema_map_equal
    ce = next(t for t in rec.tables if t.table == "claim_evidence")
    assert ce.bounded_by_t is False and ce.instant is None
    assert ce.equal  # the clone holds the pre-T rows only; source total-vs-total
    assert rec.watermark_present is False
    assert rec.watermark_equal is True  # absent on both sides
    payload = rec.as_json()
    assert payload["watermark_present"] is False
    assert payload["schema_map_equal"] is True


def test_a_schema_drifted_clone_is_not_reproduced() -> None:
    """A clone missing a spine table is recorded drift — count is None, equal
    is False, and the effective-map comparison fails too."""
    _, connect = _conn_pair(clone_missing_table="coverage_record")
    rec = cd.drill_parity(
        source_dsn="s", clone_dsn="c", at=T, clone_instance=DRILL, connect=connect
    )
    cov = next(t for t in rec.tables if t.table == "coverage_record")
    assert cov.clone_at_t is None
    assert not cov.equal
    assert not rec.schema_map_equal
    assert not rec.reproduced


def test_record_json_is_deterministic_and_self_describing() -> None:
    _, connect = _conn_pair()
    rec = cd.drill_parity(
        source_dsn="s",
        clone_dsn="c",
        at=T,
        clone_instance=DRILL,
        clone_started_at=T - timedelta(minutes=20),
        verified_at=T + timedelta(minutes=5),
        connect=connect,
    )
    payload = rec.as_json()
    assert payload["schema"] == "sig.restore-drill/1"
    assert payload["reproduced"] is True
    assert payload["at"].endswith("Z")
    assert payload["clone_instance"] == DRILL
    json.dumps(payload, sort_keys=True)  # must be serialisable


# --- the CLI verb ----------------------------------------------------------------


def _cli(
    monkeypatch: pytest.MonkeyPatch,
    *args: str,
    dsns: bool = True,
) -> int:
    """In-process `sig-ops cloudsql-drill …`; returns the exit code."""
    from ops import cli

    if dsns:
        monkeypatch.setenv("SIG_DRILL_DSN_SOURCE", "dsn-source")
        monkeypatch.setenv("SIG_DRILL_DSN_CLONE", "dsn-clone")
    else:
        monkeypatch.delenv("SIG_DRILL_DSN_SOURCE", raising=False)
        monkeypatch.delenv("SIG_DRILL_DSN_CLONE", raising=False)
    return cli.main(["cloudsql-drill", *args])


def test_cli_refuses_sig_pg_as_the_clone_target(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = _cli(monkeypatch, "--at", "2026-10-02T12:00:00Z", "--clone-instance", "sig-pg")
    assert rc == 42
    assert "production instance" in capsys.readouterr().err


def test_cli_refuses_a_nonconforming_name(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = _cli(
        monkeypatch,
        "--at",
        "2026-10-02T12:00:00Z",
        "--clone-instance",
        "sig-pg-drill-x",
    )
    assert rc == 42
    assert "not a drill instance" in capsys.readouterr().err


def test_cli_needs_both_dsns_via_env(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = _cli(
        monkeypatch,
        "--at",
        "2026-10-02T12:00:00Z",
        "--clone-instance",
        DRILL,
        dsns=False,
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "SIG_DRILL_DSN_SOURCE" in err
    assert "argv" in err  # the why: a DSN on argv leaks


def test_cli_bad_timestamp_is_a_usage_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = _cli(
        monkeypatch,
        "--at",
        "not-a-time",
        "--clone-instance",
        DRILL,
    )
    assert rc == 2


def test_cli_writes_the_record_and_fails_on_drift(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A drifted clone exits 1; the record JSON still lands (the drift is the
    evidence)."""
    _, connect = _conn_pair(clone_drop="claim")
    monkeypatch.setattr(cd, "_connect", connect)
    out = tmp_path / "record.json"
    rc = _cli(
        monkeypatch,
        "--at",
        "2026-10-02T12:00:00Z",
        "--clone-instance",
        DRILL,
        "--clone-started-at",
        "2026-10-02T11:50:00Z",
        "--out",
        str(out),
    )
    assert rc == 1
    rec = json.loads(out.read_text())
    assert rec["reproduced"] is False
    assert rec["clone_instance"] == DRILL
    assert any(t["table"] == "claim" and not t["equal"] for t in rec["tables"])


def test_cli_green_path_writes_reproduced_true(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _, connect = _conn_pair()
    monkeypatch.setattr(cd, "_connect", connect)
    out = tmp_path / "record.json"
    rc = _cli(
        monkeypatch,
        "--at",
        "2026-10-02T12:00:00Z",
        "--clone-instance",
        DRILL,
        "--out",
        str(out),
    )
    assert rc == 0
    rec = json.loads(out.read_text())
    assert rec["reproduced"] is True
    assert rec["watermark_equal"] is True
    assert rec["sqitch_equal"] is True
    assert rec["postgis_source"] == "3.4.0"
