# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Live-Postgres tests for the connector claim write path (P19.4, LD-F06b).

:class:`db.claim_sink.PgClaimSink` is the first :class:`connectors.stages.ClaimSink`
that writes to the canonical PG spine. These tests drive the real ``atlas``
connector over its committed fixture and assert into a live PG18+PostGIS instance
(the same Docker/sqitch harness the other DB tests use):

* replaying the fixture inserts N>0 append-only ``claim`` rows (L0 evidence + L2
  identity + L1 claim), and
* replaying it again inserts **0** new rows (idempotent on the content digest), and
* the module contains **no** UPDATE/DELETE against any claim table (append-only).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_ATLAS_FIXTURE = REPO_ROOT / "tests" / "connectors" / "fixtures" / "atlas" / "adoption_feed.csv"
_CLAIM_SINK_MODULE = REPO_ROOT / "db" / "src" / "db" / "claim_sink.py"

# The append-only tables the sink writes; truncated for a deterministic count.
_SPINE_TABLES = (
    "claim_evidence",
    "assertion_quarantine",
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


def _run_atlas(dsn: str) -> object:
    """Drive the atlas connector over its fixture, asserting into a PG sink."""
    from connectors.runner import run_connector_over_fixture
    from db.claim_sink import PgClaimSink

    sink = PgClaimSink.from_dsn(
        dsn, connector_name="atlas", connector_version="1.0.0", code_commit="p19.4-test"
    )
    run_connector_over_fixture(
        "atlas",
        "eff_atlas_of_surveillance",
        _ATLAS_FIXTURE,
        media_type="text/csv",
        kind="bulk_csv",
        sink=sink,
    )
    return sink


@pytest.fixture
def clean_dsn(sig_database: dict[str, object]) -> Iterator[str]:
    """A DSN whose spine tables are truncated before AND after the test.

    The sink commits (autocommit), so this test writes to the shared session
    container; truncating on teardown keeps that write from leaking into other
    DB tests (e.g. the RLS visibility counts in test_rls.py)."""
    dsn = _dsn(sig_database)
    truncate = "TRUNCATE " + ", ".join(_SPINE_TABLES) + " CASCADE"
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(truncate)
        # P35.14a closed vocabulary: fixture claims must name a registered
        # vocab_predicate row; the sink never mints one.
        from conftest import register_vocab_predicate

        register_vocab_predicate(conn, "sig.test.chunk_flag")
    yield dsn
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(truncate)


def test_replay_inserts_claims_then_is_idempotent(clean_dsn: str) -> None:
    # First replay: N>0 claim rows land, each carrying a content digest.
    first = _run_atlas(clean_dsn)
    assert first.report.inserted > 0, "the atlas fixture replay must insert claim rows"

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        rows_after_first = conn.execute(
            "SELECT count(*) FROM claim WHERE content_digest IS NOT NULL"
        ).fetchone()[0]
        # recorded_at (sys_period lower bound) is set by the DB, never by the sink.
        assert conn.execute("SELECT bool_and(lower(sys_period) IS NOT NULL) FROM claim").fetchone()[
            0
        ]
        # Every persisted claim resolves to an evidence_capture row (L0 refs).
        linked = conn.execute("SELECT count(*) FROM claim_evidence").fetchone()[0]
        assert linked >= rows_after_first > 0
    assert rows_after_first == first.report.inserted

    # Second replay of the identical run: 0 new rows (idempotent on the digest).
    second = _run_atlas(clean_dsn)
    assert second.report.inserted == 0, "an identical replay must insert no new claims"
    assert second.report.duplicates == first.report.inserted

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        rows_after_second = conn.execute(
            "SELECT count(*) FROM claim WHERE content_digest IS NOT NULL"
        ).fetchone()[0]
    assert rows_after_second == rows_after_first, "replay must not grow the claim table"


def test_claim_sink_module_is_append_only() -> None:
    """The sink module contains no UPDATE/DELETE (append-only, SIG-STORE-011/012)."""
    source = _CLAIM_SINK_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "update " not in lowered, "claim_sink.py must not issue UPDATE (append-only)"
    assert "delete " not in lowered, "claim_sink.py must not issue DELETE (append-only)"


# --- P26.18 / SOURCES.17: chunked commit for very-large sources ----------------
#
# `assert_claims` commits in bounded chunks so a source too large for one
# transaction (OSM's ~1.37M-claim mirror) lands progressively instead of rolling
# back whole. The invariants these tests pin: counters stay exact across chunk
# boundaries; a full re-run is +0; an interrupted run (chunks 1..k committed,
# then a crash) resumes to the SAME final count as an uninterrupted run; and no
# UPDATE/DELETE is issued at runtime (append-only never bent by chunking).


def _synthetic_claims(n: int, *, offset: int = 0) -> list[dict[str, object]]:
    """`n` distinct connector claims (distinct subject + value → distinct digest)."""
    return [
        {
            "subject_id": f"chunk-subj-{i}",
            "predicate_id": "sig.test.chunk_flag",
            "value": f"v-{i}",
            "source_id": "chunk_test_source",
            "license": "CC0-1.0",
            "record_kind": "claim",
        }
        for i in range(offset, offset + n)
    ]


def _claim_count(dsn: str) -> int:
    with psycopg.connect(dsn, autocommit=True) as conn:
        return int(
            conn.execute("SELECT count(*) FROM claim WHERE content_digest IS NOT NULL").fetchone()[
                0
            ]
        )


def test_commit_chunk_size_rejects_non_positive() -> None:
    """The chunk size must span at least one claim (no Docker needed)."""
    from db.claim_sink import PgClaimSink

    for bad in (0, -1):
        with pytest.raises(ValueError, match="commit_chunk_size"):
            # Validation happens before the connection is touched, so a sentinel
            # conn is fine — this stays a pure unit test.
            PgClaimSink(object(), commit_chunk_size=bad)  # type: ignore[arg-type]


def test_chunked_commit_counters_exact_and_idempotent(clean_dsn: str) -> None:
    """Chunked and single-chunk runs agree on every counter and land the same rows."""
    from db.claim_sink import PgClaimSink

    claims = _synthetic_claims(25)

    # Chunked run: chunk_size 10 over 25 claims → 3 transactions (10 + 10 + 5).
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        sink = PgClaimSink(
            conn, connector_name="chunk", code_commit="p26.18-test", commit_chunk_size=10
        )
        sink.assert_claims(claims)
    assert sink.report.considered == 25
    assert sink.report.inserted == 25
    assert sink.report.duplicates == 0
    assert sink.report.non_claim_records == 0
    assert _claim_count(clean_dsn) == 25

    # Identical re-run (still chunked): +0 — every claim dedupes on its digest
    # ACROSS the chunk boundaries, counters stay exact.
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        replay = PgClaimSink(
            conn, connector_name="chunk", code_commit="p26.18-test", commit_chunk_size=10
        )
        replay.assert_claims(claims)
    assert replay.report.considered == 25
    assert replay.report.inserted == 0
    assert replay.report.duplicates == 25
    assert _claim_count(clean_dsn) == 25


def test_chunked_matches_single_chunk_row_for_row(clean_dsn: str) -> None:
    """A tiny chunk size lands byte-for-byte the same claim set as one big chunk."""
    from db.claim_sink import PgClaimSink

    claims = _synthetic_claims(30, offset=100)

    # Single chunk (chunk_size >= N) — the pre-P26.18 all-in-one behaviour.
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        single = PgClaimSink(
            conn, connector_name="chunk", code_commit="p26.18-single", commit_chunk_size=10_000
        )
        single.assert_claims(claims)
        single_digests = {
            r[0]
            for r in conn.execute(
                "SELECT content_digest FROM claim WHERE content_digest IS NOT NULL"
            ).fetchall()
        }
    truncate = "TRUNCATE " + ", ".join(_SPINE_TABLES) + " CASCADE"
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        conn.execute(truncate)

    # Small chunks (chunk_size 3 → many transactions).
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        chunked = PgClaimSink(
            conn, connector_name="chunk", code_commit="p26.18-single", commit_chunk_size=3
        )
        chunked.assert_claims(claims)
        chunked_digests = {
            r[0]
            for r in conn.execute(
                "SELECT content_digest FROM claim WHERE content_digest IS NOT NULL"
            ).fetchall()
        }
    assert single.report.inserted == chunked.report.inserted == 30
    assert single_digests == chunked_digests, "chunking must not change which claims land"


def test_interrupted_run_resumes_to_the_uninterrupted_count(clean_dsn: str) -> None:
    """A crash after k committed chunks leaves them landed; a re-walk tops up to N."""
    from db.claim_sink import PgClaimSink

    claims = _synthetic_claims(25, offset=500)

    # 1) Uninterrupted baseline on a clean DB → final count N.
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        baseline = PgClaimSink(
            conn, connector_name="chunk", code_commit="p26.18-resume", commit_chunk_size=10
        )
        baseline.assert_claims(claims)
    uninterrupted = _claim_count(clean_dsn)
    assert uninterrupted == 25

    # Reset the spine and replay the crash-then-resume sequence.
    truncate = "TRUNCATE " + ", ".join(_SPINE_TABLES) + " CASCADE"
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        conn.execute(truncate)

    # 2) Interrupted run: raise partway through the SECOND chunk. Chunk 1 (10
    #    claims) has already committed; chunk 2's open transaction rolls back.
    class _SimulatedCrash(RuntimeError):
        pass

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        crashing = PgClaimSink(
            conn, connector_name="chunk", code_commit="p26.18-resume", commit_chunk_size=10
        )
        original_insert = crashing._insert_claim
        done = {"n": 0}

        def _insert_then_crash(claim: object) -> None:
            if done["n"] >= 15:  # 10 (chunk 1) + 5 into chunk 2, then crash
                raise _SimulatedCrash("task deadline (simulated)")
            done["n"] += 1
            original_insert(claim)  # type: ignore[arg-type]

        crashing._insert_claim = _insert_then_crash  # type: ignore[assignment]
        with pytest.raises(_SimulatedCrash):
            crashing.assert_claims(claims)

    # Only the first, fully-committed chunk survived the crash.
    partial = _claim_count(clean_dsn)
    assert partial == 10, "committed chunks persist; the rolled-back chunk left nothing"

    # 3) Resume with a fresh sink over the SAME claims → reaches the exact
    #    uninterrupted count (already-committed chunk dedupes to +0).
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        resumed = PgClaimSink(
            conn, connector_name="chunk", code_commit="p26.18-resume", commit_chunk_size=10
        )
        resumed.assert_claims(claims)
    assert resumed.report.inserted == 15
    assert resumed.report.duplicates == 10
    assert _claim_count(clean_dsn) == uninterrupted == 25


def test_chunked_commit_issues_no_update_or_delete(clean_dsn: str) -> None:
    """At RUNTIME every statement is INSERT/SELECT and each chunk is its own tx."""
    from db.claim_sink import PgClaimSink

    class _RecordingConn:
        """Delegates to a real connection while recording SQL + transaction opens."""

        def __init__(self, real: psycopg.Connection[object]) -> None:
            self._real = real
            self.statements: list[str] = []
            self.transactions = 0

        def execute(self, sql: str, params: object = None):  # type: ignore[no-untyped-def]
            self.statements.append(sql)
            return self._real.execute(sql) if params is None else self._real.execute(sql, params)

        def transaction(self):  # type: ignore[no-untyped-def]
            self.transactions += 1
            return self._real.transaction()

    claims = _synthetic_claims(12, offset=900)
    with psycopg.connect(clean_dsn, autocommit=True) as real:
        rec = _RecordingConn(real)
        sink = PgClaimSink(
            rec,  # type: ignore[arg-type]
            connector_name="chunk",
            code_commit="p26.18-noupdate",
            commit_chunk_size=5,
        )
        sink.assert_claims(claims)

    assert sink.report.inserted == 12
    # 12 claims / chunk 5 → 3 transactions (5 + 5 + 2): chunking really happened.
    assert rec.transactions == 3
    for stmt in rec.statements:
        head = stmt.lstrip().upper()
        assert head.startswith(("INSERT", "SELECT")), f"unexpected statement: {stmt!r}"
        assert " UPDATE " not in f" {head} " and not head.startswith("UPDATE")
        assert " DELETE " not in f" {head} " and not head.startswith("DELETE")


# --- P35.14a closed vocabulary at the sink -----------------------------------
#
# These sinks take `autocommit=True` connections like `from_dsn` produces: the
# sink's `conn.transaction()` chunks must really COMMIT for the second
# connection's assertions to see the rows. A non-autocommit conn leaves every
# write inside its implicit transaction — invisible to the read conn AND
# holding row locks that block `clean_dsn`'s teardown TRUNCATE forever (the
# a068ded5 CI stall).


def _closed_vocab_claim(predicate: str, **kw: object) -> dict[str, object]:
    claim: dict[str, object] = {
        "subject_id": "cv-subj",
        "predicate_id": predicate,
        "value": "v",
        "source_id": "cv_source",
        "license": "CC0-1.0",
        "record_kind": "claim",
    }
    claim.update(kw)
    return claim


def test_unknown_predicate_quarantines_and_no_claim_lands(clean_dsn: str) -> None:
    """An unregistered predicate fails closed: assertion_quarantine(unknown_
    predicate), the full record as payload, nothing in claim."""
    from db.claim_sink import PgClaimSink

    sink = PgClaimSink(
        psycopg.connect(clean_dsn, autocommit=True),
        connector_name="cv",
        code_commit="p35.14a-test",
    )
    claim = _closed_vocab_claim("sig.test.never_registered")
    sink.assert_claims([claim])
    assert sink.report.inserted == 0 and sink.report.quarantined == 1
    with psycopg.connect(clean_dsn) as conn:
        (count,) = conn.execute("SELECT count(*) FROM claim").fetchone()
        assert count == 0
        rows = conn.execute("SELECT reason, payload FROM assertion_quarantine").fetchall()
        assert [r[0] for r in rows] == ["unknown_predicate"]
        assert rows[0][1]["record"]["predicate_id"] == "sig.test.never_registered"


def test_unknown_genre_quarantines_and_no_claim_lands(clean_dsn: str) -> None:
    """A registered predicate with an unregistered evidence_genre fails closed:
    assertion_quarantine(unknown_genre) — the genre is never guessed or
    defaulted and no vocab_artifact_genre row is minted."""
    from db.claim_sink import PgClaimSink

    sink = PgClaimSink(
        psycopg.connect(clean_dsn, autocommit=True),
        connector_name="cv",
        code_commit="p35.14a-test",
    )
    claim = _closed_vocab_claim("sig.test.chunk_flag", evidence_genre="sig_test_genre")
    sink.assert_claims([claim])
    assert sink.report.inserted == 0 and sink.report.quarantined == 1
    with psycopg.connect(clean_dsn) as conn:
        (count,) = conn.execute("SELECT count(*) FROM claim").fetchone()
        assert count == 0
        rows = conn.execute("SELECT reason, payload FROM assertion_quarantine").fetchall()
        assert [r[0] for r in rows] == ["unknown_genre"]
        assert rows[0][1]["record"]["evidence_genre"] == "sig_test_genre"
        (genre_count,) = conn.execute(
            "SELECT count(*) FROM vocab_artifact_genre WHERE genre_id = 'sig_test_genre'"
        ).fetchone()
        assert genre_count == 0


def test_quarantine_is_idempotent_by_payload_digest(clean_dsn: str) -> None:
    """Re-asserting the same rejected record does not grow the quarantine —
    the digest-anchored insert stays idempotent across runs."""
    from db.claim_sink import PgClaimSink

    claim = _closed_vocab_claim("sig.test.never_registered")
    sink = PgClaimSink(
        psycopg.connect(clean_dsn, autocommit=True),
        connector_name="cv",
        code_commit="p35.14a-test",
    )
    sink.assert_claims([claim])
    assert sink.report.quarantined == 1 and sink.report.inserted == 0
    # A re-run of the same rejected record appends no second row — the digest
    # dedups, and the report counts what it actually appended (zero).
    sink2 = PgClaimSink(
        psycopg.connect(clean_dsn, autocommit=True),
        connector_name="cv",
        code_commit="p35.14a-test",
    )
    sink2.assert_claims([claim])
    assert sink2.report.quarantined == 0 and sink2.report.inserted == 0
    with psycopg.connect(clean_dsn) as conn:
        (count,) = conn.execute("SELECT count(*) FROM assertion_quarantine").fetchone()
        assert count == 1


def test_register_vocabulary_rejects_unregistered_ids(clean_dsn: str) -> None:
    """register_vocabulary validates against vocab_predicate — it is a known-set
    priming call now, never a mint."""
    from db.claim_sink import PgClaimSink

    sink = PgClaimSink(
        psycopg.connect(clean_dsn, autocommit=True),
        connector_name="cv",
        code_commit="p35.14a-test",
    )
    with pytest.raises(ValueError, match="closed"):
        sink.register_vocabulary((("sig.test.never_registered", "string"),))
    # A registered id validates without error and its claim lands.
    sink.register_vocabulary((("sig.test.chunk_flag", "string"),))
    sink.assert_claims([_closed_vocab_claim("sig.test.chunk_flag")])
    assert sink.report.inserted == 1 and sink.report.quarantined == 0


def test_unknown_qualifier_quarantines_under_closed_vocabulary(clean_dsn: str) -> None:
    """Qualifiers resolve through the same closed registry: the claim lands but
    an unregistered qualifier_id never reaches claim_qualifier — it quarantines
    against the claim's digest instead of minting a vocab row."""
    from db.claim_sink import PgClaimSink

    sink = PgClaimSink(
        psycopg.connect(clean_dsn, autocommit=True),
        connector_name="cv",
        code_commit="p35.14a-test",
    )
    claim = _closed_vocab_claim(
        "sig.test.chunk_flag",
        qualifiers=[{"qualifier_id": "sig.test.qualifier_never_registered", "value": "x"}],
    )
    sink.assert_claims([claim])
    assert sink.report.inserted == 1 and sink.report.quarantined == 1
    with psycopg.connect(clean_dsn) as conn:
        rows = conn.execute("SELECT reason FROM assertion_quarantine").fetchall()
        assert [r[0] for r in rows] == ["unknown_qualifier"]
        (count,) = conn.execute("SELECT count(*) FROM claim_qualifier").fetchone()
        assert count == 0
