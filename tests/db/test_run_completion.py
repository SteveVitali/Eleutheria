# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Real-PG proof of append-only ingest-run completion (P31.2 / ADR-109, D-P30.3-1).

* Two executions of one connector version are two ``ingest_run`` rows, each with
  exactly one appended ``ingest_run_completion``; ``ingest_run`` is never rewritten.
* A completion row is immutable (UPDATE/DELETE refused by trigger), and a second
  live completion for the same run is +0.
* The WORM backfill appends completions for the rows it can prove, reports the rest
  unmatched with a reason, re-runs +0, and runs as the least-privilege
  ``sig_materialize`` role.
* The export shaping then reads real ISO dates for the completed source and keeps
  ``not-recorded`` for a source with no completion.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_ATLAS_FIXTURE = REPO_ROOT / "tests" / "connectors" / "fixtures" / "atlas" / "adoption_feed.csv"

_SPINE_TABLES = (
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
    dsn = _dsn(sig_database)
    truncate = "TRUNCATE " + ", ".join(_SPINE_TABLES) + " CASCADE"
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(truncate)
    yield dsn
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(truncate)


def _run_atlas(dsn: str) -> Any:
    from connectors.runner import run_connector_over_fixture

    return run_connector_over_fixture(
        "atlas",
        "eff_atlas_of_surveillance",
        _ATLAS_FIXTURE,
        media_type="text/csv",
        kind="bulk_csv",
        sink_kind="pg",
        dsn=dsn,
        code_commit="p31.2-test",
    )


def test_two_executions_are_two_runs_each_with_one_appended_completion(clean_dsn: str) -> None:
    _run_atlas(clean_dsn)
    _run_atlas(clean_dsn)
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        runs = conn.execute(
            "SELECT run_id, parameters ->> 'execution_id', status, finished_at"
            "  FROM ingest_run ORDER BY started_at"
        ).fetchall()
        assert len(runs) == 2, "one ingest_run per execution (never folded together)"
        assert runs[0][1] and runs[1][1] and runs[0][1] != runs[1][1]
        # ingest_run is never rewritten: its legacy lifecycle columns stay as inserted.
        assert [(r[2], r[3]) for r in runs] == [("running", None), ("running", None)]
        comps = conn.execute(
            "SELECT c.run_id, c.status, c.source_id, c.claims_inserted, c.claims_duplicate,"
            "       c.backfilled_from, c.finished_at >= r.started_at"
            "  FROM ingest_run_completion c JOIN ingest_run r USING (run_id)"
            " ORDER BY r.started_at"
        ).fetchall()
    assert [c[0] for c in comps] == [r[0] for r in runs], "exactly one completion per run"
    first, second = comps
    assert first[1] == second[1] == "ok"
    assert first[2] == second[2] == "eff_atlas_of_surveillance"
    assert first[3] > 0 and first[4] == 0  # the first execution inserted claims
    assert second[3] == 0 and second[4] == first[3]  # the re-run was +0 (all duplicates)
    assert first[5] is None and second[5] is None  # live, not backfilled
    assert first[6] and second[6]


def test_completion_rows_are_immutable_and_one_live_completion_per_run(clean_dsn: str) -> None:
    from db.claim_sink import PgClaimSink

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        sink = PgClaimSink(conn, connector_name="immut", code_commit="p31.2")
        assert sink.record_completion("ok", source_id="s") is not None
        assert sink.record_completion("failed", source_id="s") is None  # +0, not a 2nd row
        assert conn.execute("SELECT count(*) FROM ingest_run_completion").fetchone()[0] == 1
        for stmt in (
            "UPDATE ingest_run_completion SET status = 'failed'",
            "DELETE FROM ingest_run_completion",
        ):
            with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
                conn.execute(stmt)
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                "INSERT INTO ingest_run_completion(run_id, status, claims_inserted)"
                " VALUES (%s, 'running', 0)",
                (sink.run_id,),
            )


def test_an_explicit_execution_id_resumes_the_same_run(clean_dsn: str) -> None:
    from db.claim_sink import PgClaimSink

    claims = [
        {"subject_id": "r-1", "predicate_id": "sig.test.resume", "value": "v", "source_id": "s"}
    ]
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        a = PgClaimSink(conn, connector_name="resume", execution_id="exec-1")
        a.assert_claims(claims)
        b = PgClaimSink(conn, connector_name="resume", execution_id="exec-1")
        b.assert_claims(claims)
        fresh = PgClaimSink(conn, connector_name="resume")
        fresh.record_completion("ok")
        assert a.run_id == b.run_id != fresh.run_id
        assert conn.execute("SELECT count(*) FROM ingest_run").fetchone()[0] == 2


def test_a_failed_first_chunk_still_records_an_honest_failed_completion(clean_dsn: str) -> None:
    """Review finding (P31.2): a chunk that raises rolls back the run row it created.

    The sink must forget that run id and the counts of the rolled-back chunk, so the
    pipeline's ``failed`` completion lands on a real run and says 0 claims inserted,
    never the claims that were rolled back.
    """
    from db.claim_sink import PgClaimSink

    claims = [
        {"subject_id": f"f-{i}", "predicate_id": "sig.test.fail", "value": i, "source_id": "s"}
        for i in range(5)
    ]
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        sink = PgClaimSink(conn, connector_name="failfirst", commit_chunk_size=10)
        real_insert = sink._insert_claim
        seen = {"n": 0}

        def crash_on_third(claim: object) -> None:
            if seen["n"] == 2:
                raise RuntimeError("statement timeout (simulated)")
            seen["n"] += 1
            real_insert(claim)  # type: ignore[arg-type]

        sink._insert_claim = crash_on_third  # type: ignore[method-assign]
        with pytest.raises(RuntimeError):
            sink.assert_claims(claims)
        assert sink.run_id is None, "the rolled-back run id is forgotten"
        assert sink.report.inserted == 0, "rolled-back claims are not counted"
        assert sink.record_completion("failed", source_id="s", detail="RuntimeError")
        row = conn.execute(
            "SELECT c.status, c.claims_inserted, (SELECT count(*) FROM claim)"
            "  FROM ingest_run_completion c JOIN ingest_run r USING (run_id)"
        ).fetchone()
    assert row == ("failed", 0, 0)


# --- the WORM backfill ----------------------------------------------------------


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


def _doc(source: str, start: datetime, duration: float, *, outcome: str = "ok", added: int = 4):
    return {
        "kind": "scheduled-ingest",
        "source": source,
        "mode": "live",
        "outcome": outcome,
        "started_at": start.isoformat(timespec="seconds"),
        "duration_seconds": duration,
        "claims_added": added,
        "fetch_record": {"connector": "dot_511"} if outcome == "ok" else {},
    }


def test_worm_backfill_appends_proven_rows_reruns_plus_zero_and_feeds_freshness(
    clean_dsn: str,
) -> None:
    from connectors.runner import CONNECTOR_FOR_SOURCE
    from db.claim_sink import PgClaimSink
    from exports.shaping import NOT_RECORDED, run_shaping
    from ops.run_completion import backfill_run_completions, read_worm_rows

    # A pre-P31.2 history: two sources ingested through one dot_511 run, no completion.
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        t_start = conn.execute("SELECT clock_timestamp()").fetchone()[0]
        legacy = PgClaimSink(conn, connector_name="dot_511", code_commit="unknown")
        legacy.assert_claims(_geo_claims("camreg_t", 2, "t"))
        legacy.assert_claims(_geo_claims("camreg_u", 1, "u"))
        t_end = conn.execute("SELECT clock_timestamp()").fetchone()[0]
    start = t_start.replace(microsecond=0)
    span = (t_end - start).total_seconds() + 1
    later = start + timedelta(hours=6)
    docs = {
        # camreg_t: the execution that wrote 4 claims, then a +0 re-run six hours later.
        "ops/runs/camreg_t/a.json": _doc("camreg_t", start, span),
        "ops/runs/camreg_t/b.json": _doc("camreg_t", later, 30.0),
        # camreg_u: only a gate refusal and a failure that wrote nothing — unprovable.
        "ops/runs/camreg_u/c.json": _doc("camreg_u", later, 1.0, outcome="gate_refused"),
        "ops/runs/camreg_u/d.json": _doc(
            "camreg_u", later + timedelta(hours=1), 5.0, outcome="error"
        ),
    }
    rows = read_worm_rows(
        _FakeBucket(docs), "ops/runs", connector_for_source={**CONNECTOR_FOR_SOURCE}
    )
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        conn.execute("SET ROLE sig_materialize")  # the hosted least-privilege role
        first = backfill_run_completions(conn, rows)
        again = backfill_run_completions(conn, rows)
        dry = backfill_run_completions(conn, rows, dry_run=True)
    assert (first.rows_read, first.matched, first.appended) == (4, 2, 2)
    assert {u["uri"].rsplit("/", 1)[1] for u in first.unmatched} == {"c.json", "d.json"}
    assert first.matched_by_basis == {"claims-in-window": 1, "sole-candidate": 1}
    assert (again.appended, again.already_present) == (0, 2), "a re-run is +0"
    assert dry.appended == 0 and dry.dry_run is True

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        got = conn.execute(
            "SELECT backfilled_from, run_id, status, finished_at, claims_inserted"
            "  FROM ingest_run_completion ORDER BY finished_at"
        ).fetchall()
        assert [g[0] for g in got] == [
            "gs://proj-sig-restricted/ops/runs/camreg_t/a.json",
            "gs://proj-sig-restricted/ops/runs/camreg_t/b.json",
        ]
        assert {str(g[1]) for g in got} == {legacy.run_id}
        # finished_at is the row's own started_at + duration — never invented.
        assert got[0][3] == start + timedelta(seconds=span)
        assert got[1][3] == later + timedelta(seconds=30)
        assert [g[4] for g in got] == [4, 0]
        # ingest_run untouched.
        assert conn.execute("SELECT status, finished_at FROM ingest_run").fetchall() == [
            ("running", None)
        ]

        ds = run_shaping(conn, as_of="2026-09-24")
    rows_by_source = {s.freshness.source_id: s.freshness_row() for s in ds.sources}
    t_row = rows_by_source["camreg_t"]
    assert t_row["last_successful_run"] == (later + timedelta(seconds=30)).isoformat()
    # The +0 re-run is the latest success but NOT the latest content change.
    assert t_row["last_content_change"] == (start + timedelta(seconds=span)).isoformat()
    assert t_row["status"] == "ok"
    u_row = rows_by_source["camreg_u"]
    assert u_row["last_successful_run"] == NOT_RECORDED
    assert u_row["status"] == "degraded"  # still only the open legacy run


def test_no_code_path_updates_or_deletes_ingest_run() -> None:
    """AC: completion is appended; nothing anywhere rewrites ingest_run (no Docker)."""
    pattern = re.compile(r"\b(update|delete\s+from)\s+ingest_run\b", re.IGNORECASE)
    offenders: list[str] = []
    for root in [REPO_ROOT / p for p in ("db", "connectors", "ops", "exports", "api")]:
        for path in root.rglob("*"):
            if path.suffix in {".py", ".sql"} and "revert" not in path.parts:
                if pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
                    offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == []
