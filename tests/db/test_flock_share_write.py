# SPDX-License-Identifier: Apache-2.0
"""P36.75 — the append-only configured_access share-list write.

DB-gated (``SIG_REQUIRE_DB_TESTS`` / ``make test-db``; skips without Docker):

* a unit whose digest matches no stored capture binds nothing — its claims
  count ``unbound_no_evidence`` and are never written;
* a bound unit's claims land as ordinary ``configured_sharing_partner``
  claims bound ``replayed`` to the stored capture;
* a re-run appends +0.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
import pytest

FIXTURES = Path(__file__).parent.parent / "connectors" / "fixtures" / "flock_share_lists"

_SPINE_TABLES = (
    "claim_qualifier",
    "claim_evidence",
    "assertion_quarantine",
    "claim",
    "extraction",
    "ingest_run_capture",
    "evidence_capture",
    "evidence_blob",
    "evidence_artifact",
    "entity_identifier",
    "entity_type_decision",
    "entity_identity_key",
    "ingest_run",
    "source_registry",
    "entity",
)
_TRUNCATE = "TRUNCATE " + ", ".join(_SPINE_TABLES) + " CASCADE"


def _dsn(params: dict[str, object]) -> str:
    return (
        f"postgresql://{params['user']}:{params['password']}"
        f"@{params['host']}:{params['port']}/{params['dbname']}"
    )


@pytest.fixture
def clean_dsn(sig_database: dict[str, object]):
    dsn = _dsn(sig_database)
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(_TRUNCATE)
    yield dsn
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(_TRUNCATE)


def _unit() -> tuple[Any, bytes]:
    from connectors.flock_share_lists import build_share_claims, snapshot_portals
    from db.flock_share_write import ShareUnit
    from evidence.digest import multihash

    blob = (FIXTURES / "snapshot_clean.json").read_bytes()
    build = build_share_claims(snapshot_portals(json.loads(blob)))
    unit = ShareUnit(
        source_id="eyes_on_flock",
        input_digest=multihash(blob),
        byte_size=len(blob),
        media_type="application/json",
        claims=build.claims,
        feed_digest=str(build.feed.get("digest")),
        screened_portals=build.screened_portals,
        refused_portals=len(build.refused),
    )
    return unit, blob


def _seed_capture(dsn: str, blob: bytes) -> None:
    """Land the snapshot's bytes as a real eyes_on_flock capture via the sink."""
    from connectors.stages import CaptureRef
    from db.claim_sink import PgClaimSink
    from evidence.digest import multihash

    sink = PgClaimSink.from_dsn(dsn, connector_name="flock_portal", connector_version="1.0.0")
    capture = CaptureRef(
        digest=multihash(blob),
        source_uri="https://eyesonflock.com/api/v1/data",
        media_type="application/json",
        byte_size=len(blob),
        retrieved_at=datetime(2026, 9, 15, tzinfo=UTC),
    )
    sink.assert_claims(
        [
            {
                "record_kind": "claim",
                "subject_id": "flock_portal:okc-pd",
                "predicate_id": "portal_exists",
                "value": True,
                "raw_value": True,
                "source_id": "eyes_on_flock",
            }
        ],
        capture=capture,
    )


def test_unbound_unit_never_writes(clean_dsn: str) -> None:
    from db.flock_share_write import run_write

    unit, _blob = _unit()
    report = run_write(clean_dsn, units=[unit])
    assert report["claims_unbound_no_evidence"] == len(unit.claims)
    applied = run_write(clean_dsn, units=[unit], apply=True)
    with psycopg.connect(clean_dsn) as conn:
        n = conn.execute("SELECT count(*) FROM claim").fetchone()
        assert n is not None and int(n[0]) == 0
    assert applied["apply"]["bound_units"] == 0


def test_bound_unit_writes_and_reruns_plus_zero(clean_dsn: str) -> None:
    from db.flock_share_write import run_write

    unit, blob = _unit()
    _seed_capture(clean_dsn, blob)
    plan = run_write(clean_dsn, units=[unit])
    assert plan["claims_pending"] == len(unit.claims)
    applied = run_write(clean_dsn, units=[unit], apply=True)
    assert applied["apply"]["claims_added"] == len(unit.claims)
    again = run_write(clean_dsn, units=[unit], apply=True)
    assert again["apply"]["claims_added"] == 0
    assert again["apply"]["claims_duplicate"] == len(unit.claims)
