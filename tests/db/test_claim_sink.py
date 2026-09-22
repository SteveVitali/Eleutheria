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
