# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Real-PG proof of the append-only ingest-run report (P35.32 / J3 §3.3 item 1,
K10 §18 C-13/C-14 — SIG-TRANSP-036's engine field; owner stays P36.46).

* One ``ingest_run_report`` row per execution; rows are immutable (UPDATE/DELETE
  refused by trigger), a second live row for the same run is +0, and a second
  backfilled row for the same source URI is +0 (``backfilled_from`` unique key).
* ``link_basis`` is the closed C-14 vocabulary ('live', 'backfill:*',
  'unmatched:<reason>', 'repo_record'), ``clock_basis`` is db|run_row|git_only,
  ``error_class`` reuses the P35.31 S-4 closed vocabulary — off-vocabulary
  inserts fail the CHECK.
* The WORM+repo backfill mints every execution exactly once — matched rows
  carry their run, unmatched executions carry ``run_id NULL`` with the P31.2
  reason class, repo records carry 'repo_record'/'git_only' — and a re-run
  appends nothing (+0). The reconcile read-back proves no execution is
  double-counted.
* assertion_quarantine contributes COUNT-BY-REASON only — the private payload
  never lands in the report (K10 §18).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

_SPINE_TABLES = (
    "ingest_run_report",
    "assertion_quarantine",
    "ingest_run_completion",
    "claim_evidence",
    "claim",
    "extraction",
    "evidence_capture",
    "evidence_blob",
    "evidence_artifact",
    "entity_identifier",
    "ingest_run",
    "source_registry",
    "entity",
)


def _dsn(params: dict[str, object]) -> str:
    return (
        f"postgresql://{params['user']}:{params['password']}"
        f"@{params['host']}:{params['port']}/{params['dbname']}"
    )


@pytest.fixture
def clean_dsn(sig_database: dict[str, object]) -> Iterator[str]:
    from conftest import register_vocab_predicate

    dsn = _dsn(sig_database)
    truncate = "TRUNCATE " + ", ".join(_SPINE_TABLES) + " CASCADE"
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(truncate)
        register_vocab_predicate(conn, "sig.test.report")
    yield dsn
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(truncate)


def test_report_rows_are_immutable(clean_dsn: str) -> None:
    from db.run_report import append_report

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        report_id = append_report(
            conn,
            link_basis="live",
            clock_basis="run_row",
            source_id="s",
            fetches=3,
            records_emitted=42,
            error_class="upstream_http_503",
            per_fetch=[{"host": "example.org", "status": 200, "bytes": 1234}],
        )
        assert report_id
        # The column round-trips the PKG-12 host/status/bytes shape (the
        # telemetry writer lands in row 312 — the contract holds already).
        got = conn.execute(
            "SELECT per_fetch FROM ingest_run_report WHERE report_id = %s",
            (report_id,),
        ).fetchone()[0]
        assert got == [{"host": "example.org", "status": 200, "bytes": 1234}]
        for stmt in (
            "UPDATE ingest_run_report SET fetches = 0",
            "DELETE FROM ingest_run_report",
        ):
            with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
                conn.execute(stmt)
        assert conn.execute("SELECT count(*) FROM ingest_run_report").fetchone()[0] == 1


def test_vocabulary_checks_reject_off_vocabulary_values(clean_dsn: str) -> None:
    from db.run_report import append_report

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        # In-code validation mirrors the CHECKs.
        for bad in (
            {"link_basis": "guessed", "clock_basis": "run_row"},
            {"link_basis": "live", "clock_basis": "wallclock"},
            {"link_basis": "live", "clock_basis": "db", "error_class": "made_up"},
        ):
            with pytest.raises(ValueError, match="off-vocabulary"):
                append_report(conn, **bad)
        # And the DDL CHECKs hold the same boundary on a raw insert.
        for sql, params in (
            ("INSERT INTO ingest_run_report(link_basis, clock_basis) VALUES('guessed','db')", ()),
            ("INSERT INTO ingest_run_report(link_basis, clock_basis) VALUES('live','wall')", ()),
            (
                "INSERT INTO ingest_run_report(link_basis, clock_basis, error_class)"
                " VALUES('live','db','made_up')",
                (),
            ),
        ):
            with pytest.raises(psycopg.errors.CheckViolation):
                conn.execute(sql, params)
        # The open-suffix members land.
        assert append_report(conn, link_basis="unmatched:no_candidate_run", clock_basis="run_row")
        assert append_report(
            conn,
            link_basis="repo_record",
            clock_basis="git_only",
            backfilled_from="repo:docs/build/reports/live_runs/x.json",
        )


def test_live_row_per_run_and_backfill_uri_are_plus_zero(clean_dsn: str) -> None:
    from db.claim_sink import PgClaimSink
    from db.run_report import append_report

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        sink = PgClaimSink(conn, connector_name="rep", code_commit="p35.32")
        sink.assert_claims(
            [
                {
                    "subject_id": "r-1",
                    "predicate_id": "sig.test.report",
                    "value": "v",
                    "source_id": "s",
                    "license": "CC0-1.0",
                }
            ]
        )
        assert sink.run_id
        uri = "gs://b/ops/runs/s/2026-10-19/t.json"
        first = append_report(conn, link_basis="live", clock_basis="db", run_id=sink.run_id)
        again = append_report(conn, link_basis="live", clock_basis="db", run_id=sink.run_id)
        assert first and again is None, "one live report per run (+0)"
        b1 = append_report(
            conn,
            link_basis="backfill:sole-candidate",
            clock_basis="run_row",
            run_id=sink.run_id,
            backfilled_from=uri,
        )
        b2 = append_report(
            conn,
            link_basis="backfill:sole-candidate",
            clock_basis="run_row",
            run_id=sink.run_id,
            backfilled_from=uri,
        )
        assert b1 and b2 is None, "one report per backfilled_from URI (+0)"
        # NULL run_id rows (unmatched executions, refusals) do not contend on
        # the live key — several exist side by side.
        for i in range(3):
            assert append_report(conn, link_basis=f"unmatched:reason_{i}", clock_basis="run_row")


def test_grants_are_select_insert_only(clean_dsn: str) -> None:
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        granted = {
            (r[0], r[1])
            for r in conn.execute(
                "SELECT grantee, privilege_type FROM information_schema.role_table_grants"
                " WHERE table_name='ingest_run_report'"
                " AND grantee IN ('sig_ingest','sig_materialize','sig_read_public',"
                " 'sig_read_restricted','sig_read_sealed','sig_export')"
            ).fetchall()
        }
    assert ("sig_ingest", "INSERT") in granted
    assert ("sig_materialize", "INSERT") in granted
    assert ("sig_read_restricted", "SELECT") in granted
    # The table is NOT on the §37 public surface — execution-keyed public
    # history is P36.46's (row 389), published through rows 311/313 views.
    assert ("sig_read_public", "SELECT") not in granted
    assert not any(p in ("UPDATE", "DELETE") for _g, p in granted)


# --- the WORM + repo backfill -------------------------------------------------


class _FakeBucket:
    bucket = "proj-sig-restricted"

    def __init__(self, docs: dict[str, dict[str, Any]]) -> None:
        import json

        self._objects = {k: json.dumps(v).encode() for k, v in docs.items()}

    def list_objects(self, prefix: str) -> list[str]:
        return [k for k in self._objects if k.startswith(prefix)]

    def get_object(self, name: str) -> bytes:
        return self._objects[name]


def _geo_claims(source: str, n: int, tag: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i in range(n):
        for pred, val in (("camera_latitude", 35.4 + i / 100), ("camera_longitude", -97.5)):
            out.append(
                {
                    "subject_id": f"{tag}-{i}",
                    "predicate_id": pred,
                    "value": val,
                    "source_id": source,
                    "license": "CC0-1.0",
                }
            )
    return out


_LANE = {
    "custody_posture": "MIRROR",
    "spdx": "CC0-1.0",
    "redistributable": "yes",
    "reviewed": True,
    "part_viii_class": "clear",
}


def _doc(
    source: str,
    start: datetime,
    duration: float,
    *,
    outcome: str = "ok",
    added: int = 4,
    fetch_record: dict | None = None,
) -> dict[str, Any]:
    return {
        "kind": "scheduled-ingest",
        "source": source,
        "mode": "live",
        "outcome": outcome,
        "started_at": start.isoformat(timespec="seconds"),
        "duration_seconds": duration,
        "claims_added": added,
        "fetch_record": (
            fetch_record
            if fetch_record is not None
            else ({"connector": "dot_511"} if outcome == "ok" else {})
        ),
    }


def test_backfill_reports_each_execution_once_then_plus_zero(clean_dsn: str) -> None:
    """The union: two executions folded through one shared run get one report
    row each (own run-row clock, never the shared run's), an unprovable row
    stays unmatched with run_id NULL, a repo record links 'repo_record'."""
    from connectors.runner import CONNECTOR_FOR_SOURCE
    from db.claim_sink import PgClaimSink
    from ops.run_report import (
        RepoRecord,
        backfill_run_reports,
        read_worm_docs,
        reconcile_run_reports,
    )

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        t_start = conn.execute("SELECT clock_timestamp()").fetchone()[0]
        legacy = PgClaimSink(
            conn,
            connector_name="dot_511",
            code_commit="unknown",
            lane_resolver=lambda _sid: _LANE,
        )
        legacy.assert_claims(_geo_claims("camreg_t", 2, "t"))
        t_end = conn.execute("SELECT clock_timestamp()").fetchone()[0]
        # A quarantine row on the shared run: the report must carry the
        # reason COUNT and never the payload (K10 §18).
        conn.execute(
            "INSERT INTO assertion_quarantine"
            " (run_id, reason, connector_name, source_id, payload, payload_digest)"
            " VALUES (%s,'unknown_predicate','dot_511','camreg_t',"
            " %s::jsonb,'digest-q1')",
            (legacy.run_id, '{"secret": "PAYLOAD-MARKER-9f2"}'),
        )
    start = t_start.replace(microsecond=0)
    span = (t_end - start).total_seconds() + 1
    later = start + timedelta(hours=6)
    fetch = {
        "connector": "dot_511",
        "urls": ["https://example.org/a", "http://10.0.0.9/b"],
        "status_codes": [200, 404],
        "byte_counts": [100, 0],
        "robots_decisions": [
            {"example.org": "allowed"},
            {"host": "other.org", "decision": "unretrievable"},
        ],
        "robots_disregarded": [
            {"url": "https://rogue.test/x", "host": "rogue.test", "verdict": "disallowed"}
        ],
        "refusals": [{"detail": "robots.txt disallows fetch of 'x'"}],
        "disappearances": [{"url": "https://gone.test/d"}],
        "document_outcomes": [{"outcome": "matched"}, {"outcome": "no_match"}],
        "rate_limit_events": [{"status": 429}],
        "quota_reached": True,
        "budget_reached": False,
    }
    docs = {
        # camreg_t: the execution that wrote claims — claims-in-window link.
        "ops/runs/camreg_t/a.json": _doc("camreg_t", start, span, fetch_record=fetch),
        # camreg_t again: a sole-candidate +0 re-run (it emitted 4 claims, all
        # duplicates of the first execution's — no claim lands in its window).
        "ops/runs/camreg_t/b.json": _doc(
            "camreg_t", later, 30.0, added=4, fetch_record={"connector": "dot_511"}
        ),
        # camreg_u: a gate refusal — not an execution → unmatched.
        "ops/runs/camreg_u/c.json": _doc("camreg_u", later, 1.0, outcome="gate_refused", added=0),
        # camreg_u: a failure that wrote nothing → unmatched.
        "ops/runs/camreg_u/d.json": _doc(
            "camreg_u",
            later + timedelta(hours=1),
            5.0,
            outcome="error",
            added=0,
            fetch_record={"connector": "dot_511"},
        ),
    }
    worm_docs = read_worm_docs(_FakeBucket(docs), "ops/runs")
    records = [
        RepoRecord(
            path="docs/build/reports/live_runs/2026-09-16_probe.json",
            doc={
                "source_id": "probe_src",
                "started_at": "2026-09-16T01:00:00+00:00",
                "duration_seconds": 12.5,
                "claim_count": 7,
                "urls": ["https://probe.test/i"],
                "status_codes": [200],
                "byte_counts": [10],
            },
        )
    ]
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        first = backfill_run_reports(
            conn, worm_docs, records, connector_for_source={**CONNECTOR_FOR_SOURCE}
        )
        second = backfill_run_reports(
            conn, worm_docs, records, connector_for_source={**CONNECTOR_FOR_SOURCE}
        )
        reconcile = reconcile_run_reports(conn)

    assert first.errors == []
    # 5 executions: 2 matched + 2 unmatched + 1 repo record.
    assert (first.appended, first.matched, first.unmatched) == (5, 2, 2)
    assert (second.appended, second.already_present) == (0, 5), "a re-run is +0"
    basis = first.link_basis_counts
    assert basis["backfill:claims-in-window"] == 1
    assert basis["backfill:sole-candidate"] == 1
    assert basis["unmatched:not_an_execution"] == 1
    assert basis["unmatched:failed_no_proof"] == 1
    assert basis["repo_record"] == 1

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        rows = conn.execute(
            "SELECT link_basis, clock_basis, run_id::text, source_id, started_at,"
            "       fetches, records_emitted, robots_outcomes, refusal_classes,"
            "       rate_limit_events, disappearances, document_outcomes,"
            "       quota_reached, budget_reached, error_class, per_fetch"
            "  FROM ingest_run_report ORDER BY backfilled_from"
        ).fetchall()
    # The a.json row carries the full typed fetch evidence.
    a = rows[0]
    assert a[0] == "backfill:claims-in-window" and a[1] == "run_row"
    assert a[2] == str(legacy.run_id)
    assert a[4] == start  # the execution's OWN clock — never the shared run's
    assert a[5] == 2 and a[6] == 4  # fetches, records_emitted (emitted, not inserted)
    assert a[7] == {
        "example.org": {"obeyed": 1},
        "other.org": {"unavailable": 1},
        "rogue.test": {"disregarded": 1},
    }
    refusal = a[8]
    assert refusal["robots_disallow"] == 1
    assert refusal["unknown_predicate"] == 1, "quarantine reason counted"
    assert "PAYLOAD-MARKER" not in json.dumps(refusal), "payload never lands"
    assert a[9] == 1 and a[10] == 1  # rate_limit_events, disappearances
    assert a[11] == {"matched": 1, "no_match": 1}
    assert a[12] is True and a[13] is False
    # per_fetch stays NULL — the column + PKG-12 contract land in this
    # change; the telemetry writer is row 312's (P35.34), J3 'when present'.
    assert a[15] is None

    unmatched = [r for r in rows if r[0].startswith("unmatched:")]
    assert all(r[2] is None for r in unmatched), "unmatched → run_id NULL (C-14)"
    err_row = next(r for r in rows if r[0] == "unmatched:failed_no_proof")
    assert err_row[14] == "unclassified_error", "S-4 class for a bare 'error'"

    repo_row = rows[-1]
    assert repo_row[0] == "repo_record" and repo_row[1] == "git_only"
    assert repo_row[2] is None and repo_row[3] == "probe_src"
    assert repo_row[6] == 7  # records_emitted from claim_count

    assert reconcile["total"] == 5
    assert reconcile["double_counted"] == 0
    # The shared legacy run links two report rows — each keeps its own clock.
    assert reconcile["shared_run_rows"]["runs"] == 1
    assert reconcile["shared_run_rows"]["missing_own_start"] == 0


def test_quarantine_counts_require_read_privilege(clean_dsn: str) -> None:
    """Under the hosted least-privilege role (sig_materialize, ADR-103) the
    private quarantine table is sealed: ``load_quarantine_counts`` degrades
    to {} rather than surfacing payload — the report still lands, the count
    simply isn't claimed."""
    from ops.run_report import load_quarantine_counts

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        sink_run = conn.execute(
            "INSERT INTO ingest_run"
            " (connector_name, connector_version, code_commit, ruleset_version,"
            "  vocab_version, parameters, environment, input_digests)"
            " VALUES ('q','1.0','x','1.0.0','1.0','{}'::jsonb,'{}'::jsonb,'{}')"
            " RETURNING run_id"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO assertion_quarantine"
            " (run_id, reason, connector_name, payload, payload_digest)"
            " VALUES (%s,'unknown_predicate','q','{}'::jsonb,'dq1')",
            (sink_run,),
        )
        assert load_quarantine_counts(conn) == {str(sink_run): {"unknown_predicate": 1}}
        conn.execute("SET ROLE sig_materialize")
        assert load_quarantine_counts(conn) == {}, "sealed under least privilege"


def test_live_writer_appends_one_report_per_execution(clean_dsn: str) -> None:
    """The scheduled-ingest writer: store_run_report appends a 'live' row per
    execution; a repeat for the same run is +0 under the live key."""
    from db.claim_sink import PgClaimSink
    from ops.scheduled import RunRow, store_run_report

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        sink = PgClaimSink(conn, connector_name="rep_live", code_commit="p35.32")
        sink.assert_claims(
            [
                {
                    "subject_id": "r-2",
                    "predicate_id": "sig.test.report",
                    "value": "v",
                    "source_id": "camreg_t",
                    "license": "CC0-1.0",
                }
            ]
        )
        assert sink.run_id
        row = RunRow(
            kind="scheduled-ingest",
            source="camreg_t",
            mode="live",
            outcome="ok",
            exit_code=0,
            started_at="2026-10-18T06:00:00+00:00",
            duration_seconds=30.0,
            claims_added=3,
            fetch_record={
                "connector": "dot_511",
                "urls": ["https://example.org/x"],
                "status_codes": [200],
                "byte_counts": [50],
            },
            ingest_run_id=sink.run_id,
        )
        first = store_run_report(row, conn=conn)
        again = store_run_report(row, conn=conn)
        got = conn.execute(
            "SELECT link_basis, clock_basis, run_id::text, source_id,"
            "       fetches, records_emitted, per_fetch"
            " FROM ingest_run_report"
        ).fetchall()
    assert first and again is None, "one live report per execution (+0)"
    assert len(got) == 1
    link_basis, clock_basis, run_id, source_id, fetches, emitted, per_fetch = got[0]
    assert (link_basis, clock_basis) == ("live", "db")
    assert run_id == str(sink.run_id) and source_id == "camreg_t"
    assert (fetches, emitted) == (1, 3)
    assert per_fetch is None, "the PKG-12 writer is row 312's (P35.34)"

    # A refused run writes no ingest_run: the report row still lands (one row
    # per execution, C-14) with run_id NULL and the refusal class recorded.
    refused = RunRow(
        kind="scheduled-ingest",
        source="camreg_u",
        mode="live",
        outcome="gate_refused",
        exit_code=3,
        started_at="2026-10-18T06:05:00+00:00",
        duration_seconds=0.2,
        refusal_reason="gate_refused",
    )
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        assert store_run_report(refused, conn=conn)
        got = conn.execute(
            "SELECT run_id, link_basis, clock_basis, refusal_classes"
            " FROM ingest_run_report WHERE source_id='camreg_u'"
        ).fetchone()
    assert got[0] is None
    assert got[1:] == ("live", "run_row", {"gate_refused": 1})


def test_no_code_path_updates_or_deletes_ingest_run_report() -> None:
    """AC: reports are appended; nothing anywhere rewrites them (no Docker)."""
    pattern = re.compile(r"\b(update|delete\s+from)\s+ingest_run_report\b", re.IGNORECASE)
    offenders: list[str] = []
    for root in [REPO_ROOT / p for p in ("db", "connectors", "ops", "exports", "api")]:
        for path in root.rglob("*"):
            if path.suffix in {".py", ".sql"} and "revert" not in path.parts:
                if pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
                    offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == []
