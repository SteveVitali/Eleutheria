# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Real-PG proof of restart = resume (P31.4 / ADR-111, D-P30.1-2).

An execution is killed at page *k* (a ``BaseException`` escapes the pipeline the
way a SIGKILL does: no completion is recorded). A second execution of the same
logical run, through a fresh ``PgClaimSink``:

* issues **no fetch** for the pages the first one flushed;
* re-processes the page it had captured but not flushed from the stored capture;
* inserts only the tail, and the spine ends with exactly the claim set an
  uninterrupted run lands (same count, same content digests);
* records one ``ok`` completion whose counts cover only its own inserts.

A third execution of the now-completed logical run is a fresh run: it re-fetches
every page and inserts +0. A new cadence window never resumes. The marks table is
append-only (UPDATE/DELETE refused by trigger).
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Iterator, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

import psycopg
import pytest

PAGES = 6
ROWS = 40

_SPINE_TABLES = (
    "ingest_run_capture",
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


class Killed(BaseException):  # noqa: N818 - models a SIGKILL
    pass


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


def _connector() -> Any:
    from connectors.stages import CaptureRef, Connector, FetchResult, RunContext

    class Paged(Connector):
        name = "p31-4-paged"
        version = "1"

        def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
            return list(ctx.parameters["targets"])

        def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
            assert ctx.fetcher is not None
            return ctx.fetcher.fetch(str(target["url"]))

        def parse(self, ctx: RunContext, capture: CaptureRef) -> Any:
            return json.loads(ctx.captures.get(capture.digest))

        def extract(self, ctx: RunContext, parsed: Any) -> list[Mapping[str, Any]]:
            return list(parsed["features"])

        def normalize(
            self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
        ) -> list[dict[str, Any]]:
            out: list[dict[str, Any]] = []
            for row in raw_claims:
                subject = f"traffic_camera:p31_4:{row['FID']}"
                base = {"subject_id": subject, "source_id": "p31_4_paged", "spdx": "ODbL-1.0"}
                out.append({**base, "predicate_id": "sig.test.name", "value": row["name"]})
                out.append({**base, "predicate_id": "sig.test.fid", "value": row["FID"]})
                out.append({"record_kind": "traffic_camera", "subject_id": subject})
            return out

    return Paged()


class Fetcher:
    def __init__(self, *, kill_at: int | None = None) -> None:
        self.pages: list[int] = []
        self._kill_at = kill_at

    def fetch(
        self, url: str, *, headers: Mapping[str, str] | None = None, body: bytes | None = None
    ) -> Any:
        from connectors.stages import FetchResult

        page = int(url.rsplit("=", 1)[1])
        if page == self._kill_at:
            raise Killed(url)
        self.pages.append(page)
        rows = [{"FID": page * ROWS + i, "name": f"cam {page}-{i}"} for i in range(ROWS)]
        return FetchResult(
            url=url,
            status=200,
            body=json.dumps({"features": rows}, sort_keys=True).encode(),
            media_type="application/json",
            retrieved_at=datetime(2026, 9, 25, tzinfo=UTC),
        )


def _execute(
    dsn: str,
    logical_run: str | None,
    fetcher: Fetcher,
    captures: Any,
    *,
    sink_cls: Any = None,
) -> tuple[Any, Any]:
    from connectors.pipeline import run
    from connectors.registry import get
    from connectors.stages import ArtifactStore, RunContext
    from db.claim_sink import PgClaimSink
    from evidence.ingest_run import IngestRun

    cls = sink_cls or PgClaimSink
    sink = cls.from_dsn(
        dsn,
        connector_name="p31-4-paged",
        connector_version="1",
        code_commit="p31.4-test",
        logical_run=logical_run,
        commit_chunk_size=50,  # a page spans two chunks: a flush is many commits
    )
    ctx = RunContext(
        source=dataclasses.replace(get("eyes_on_flock"), ingestion_permitted=True),
        run=IngestRun("p31-4-paged", "1", "t", "r1", "v1", ()),
        fetcher=fetcher,
        captures=captures,
        claim_sink=sink,
        parameters={
            "targets": [
                {"id": "layer", "url": f"https://arcgis.example/q?resultOffset={p}"}
                for p in range(PAGES)
            ]
        },
        artifacts=ArtifactStore(keep_history=False),
        retain_record=lambda _r: False,
    )
    try:
        return run(_connector(), ctx), sink
    except BaseException:
        sink._conn.close()
        raise


def _spine(dsn: str) -> tuple[int, set[str]]:
    with psycopg.connect(dsn) as conn:
        digests = {r[0] for r in conn.execute("SELECT content_digest FROM claim").fetchall()}
    return len(digests), digests


def _uninterrupted(dsn: str) -> tuple[int, set[str], Any]:
    from connectors.stages import InMemoryCaptureStore

    report, sink = _execute(dsn, "src@w0", Fetcher(), InMemoryCaptureStore())
    sink._conn.close()
    count, digests = _spine(dsn)
    return count, digests, report


def test_a_killed_run_resumes_to_the_uninterrupted_final_state(clean_dsn: str) -> None:
    from connectors.stages import InMemoryCaptureStore
    from db.claim_sink import PgClaimSink

    baseline_count, baseline_digests, baseline = _uninterrupted(clean_dsn)
    assert baseline_count == PAGES * ROWS * 2
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        conn.execute("TRUNCATE " + ", ".join(_SPINE_TABLES) + " CASCADE")

    class DiesFlushingPage3(PgClaimSink):
        """Page 3 is captured, then the process dies inside its flush."""

        calls = 0

        def assert_claims(self, claims: Sequence[Mapping[str, Any]]) -> None:
            type(self).calls += 1
            if type(self).calls == 4:
                raise Killed("mid-flush")
            super().assert_claims(claims)

    captures = InMemoryCaptureStore()  # persistent across executions (the GCS mount)
    with pytest.raises(Killed):
        _execute(clean_dsn, "src@w1", Fetcher(), captures, sink_cls=DiesFlushingPage3)
    landed, _ = _spine(clean_dsn)
    assert landed == 3 * ROWS * 2  # pages 0-2 committed; page 3 rolled back

    second = Fetcher()
    report, sink = _execute(clean_dsn, "src@w1", second, captures)
    run_id = sink.run_id
    sink._conn.close()
    assert second.pages == [4, 5]  # no fetch for pages 0-3
    assert [r["action"] for r in report.resumed] == ["skipped"] * 3 + ["reprocessed"]
    count, digests = _spine(clean_dsn)
    assert count == baseline_count and digests == baseline_digests
    assert report.claim_count == baseline.claim_count
    assert [c.digest for c in report.captures] == [c.digest for c in baseline.captures]

    with psycopg.connect(clean_dsn) as conn:
        comps = conn.execute(
            "SELECT r.parameters ->> 'logical_run', c.status, c.claims_inserted"
            "  FROM ingest_run r LEFT JOIN ingest_run_completion c USING (run_id)"
            " ORDER BY r.started_at"
        ).fetchall()
        marks = conn.execute(
            "SELECT state, count(*) FROM ingest_run_capture WHERE run_id = %s GROUP BY 1",
            (run_id,),
        ).fetchall()
    # The killed execution has no completion; the resumed one completed ok, and its
    # inserts are the tail only (page 3 re-derived from the capture + pages 4-5).
    assert comps == [("src@w1", None, None), ("src@w1", "ok", 3 * ROWS * 2)]
    assert dict(marks) == {"captured": 2, "flushed": 3}

    # The logical run is complete: a further execution is a fresh run — every page
    # re-fetched, +0 inserted.
    third = Fetcher()
    report3, sink3 = _execute(clean_dsn, "src@w1", third, InMemoryCaptureStore())
    inserted3 = sink3.report.inserted
    sink3._conn.close()
    assert third.pages == list(range(PAGES)) and report3.resumed == [] and inserted3 == 0
    assert _spine(clean_dsn)[0] == baseline_count


def test_a_new_cadence_window_never_resumes(clean_dsn: str) -> None:
    from connectors.stages import InMemoryCaptureStore

    captures = InMemoryCaptureStore()
    with pytest.raises(Killed):
        _execute(clean_dsn, "src@w1", Fetcher(kill_at=2), captures)
    fresh = Fetcher()
    report, sink = _execute(clean_dsn, "src@w2", fresh, captures)
    sink._conn.close()
    assert fresh.pages == list(range(PAGES)) and report.resumed == []
    none = Fetcher()
    report, sink = _execute(clean_dsn, None, none, captures)  # no logical run at all
    sink._conn.close()
    assert none.pages == list(range(PAGES))


def test_capture_marks_are_append_only(clean_dsn: str) -> None:
    from connectors.stages import InMemoryCaptureStore

    report, sink = _execute(clean_dsn, "src@w1", Fetcher(), InMemoryCaptureStore())
    sink._conn.close()
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        assert conn.execute("SELECT count(*) FROM ingest_run_capture").fetchone()[0] == 2 * PAGES
        for stmt in ("UPDATE ingest_run_capture SET records = 0", "DELETE FROM ingest_run_capture"):
            with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
                conn.execute(stmt)
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                "INSERT INTO ingest_run_capture(run_id, target_key, state, capture_digest,"
                " source_uri, media_type, byte_size) SELECT run_id, 'x', 'flushed', 'd', 'u',"
                " 'm', 0 FROM ingest_run LIMIT 1"
            )


def _sink(dsn: str, logical_run: str, **kw: Any) -> Any:
    from db.claim_sink import PgClaimSink

    base = {"connector_name": "rules", "connector_version": "1", "code_commit": "c1"}
    return PgClaimSink.from_dsn(dsn, logical_run=logical_run, **{**base, **kw})


def _mark(sink: Any, key: str, state: str) -> None:
    sink.record_capture(
        key,
        state=state,
        capture_digest=f"d-{key}",
        source_uri=f"u-{key}",
        media_type="application/json",
        byte_size=1,
        records=1 if state == "flushed" else None,
    )


def test_the_resume_rule_on_real_pg(clean_dsn: str) -> None:
    """failed stays resumable; ok/partial close; backfilled completions and other code
    never count; a flushed mark from an older execution beats a newer captured one."""
    a = _sink(clean_dsn, "L")
    _mark(a, "p1", "flushed")
    _mark(a, "p2", "captured")
    a.record_completion("failed", detail="OperationalError")  # a surviving failure
    b = _sink(clean_dsn, "L")
    marks = {m["target_key"]: m["state"] for m in b.resume_marks()}
    assert marks == {"p1": "flushed", "p2": "captured"}
    _mark(b, "p1", "captured")  # newer, but p1 was already flushed by `a`
    c = _sink(clean_dsn, "L")
    assert {m["target_key"]: m["state"] for m in c.resume_marks()} == marks
    # Another code commit, connector version, logical run or a replay never resumes.
    for other in (
        _sink(clean_dsn, "L", code_commit="c2"),
        _sink(clean_dsn, "L", connector_version="2"),
        _sink(clean_dsn, "L2"),
        _sink(clean_dsn, "L", is_replay=True),
    ):
        assert other.resume_marks() == []
    # A backfilled completion never closes a logical run.
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO ingest_run_completion(run_id, status, claims_inserted, backfilled_from)"
            " VALUES (%s, 'ok', 0, 'gs://b/ops/runs/x.json')",
            (b.run_id,),
        )
    assert _sink(clean_dsn, "L").resume_marks() != []
    # A live `partial` completion closes it: the next execution is a fresh run.
    b.record_completion("partial")
    assert _sink(clean_dsn, "L").resume_marks() == []
    for s in (a, b, c):
        s._conn.close()


def test_a_spine_without_the_marks_table_runs_without_resume() -> None:
    from db.claim_sink import PgClaimSink

    class NoTable:
        def execute(self, *_: Any, **__: Any) -> Any:
            raise psycopg.errors.UndefinedTable("relation ingest_run_capture does not exist")

    sink = PgClaimSink(NoTable(), connector_name="x", logical_run="L")  # type: ignore[arg-type]
    assert sink.resume_marks() == [] and sink.logical_run is None
    _mark(sink, "p", "captured")  # a no-op now: never touches the missing table
