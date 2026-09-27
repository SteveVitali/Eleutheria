# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P32.2 / D-P31.1-3 (SIG-TRUST-001): a PG-backed entity carrying BOTH a
resolver-registered and an unregistered predicate must serve its eligible
registered facts — the unknown predicate is surfaced explicitly, never a
whole-entity 404. Restricted (sensitivity > 0) claims stay withheld AND unnamed;
a truly absent entity still 404s.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import psycopg
import pytest

_SUBJECT = "e:mixed-registry"
_UNREGISTERED = "sig.test.unregistered_p32_2"
_RESTRICTED = "sig.test.restricted_p32_2"

_SPINE_TABLES = (
    "claim_qualifier",
    "claim_evidence",
    "claim",
    "assertion_quarantine",
    "extraction",
    "ingest_run_capture",
    "evidence_capture",
    "evidence_blob",
    "evidence_artifact",
    "entity_identifier",
    "ingest_run",
    "source_registry",
    "entity",
)


@pytest.fixture(scope="module")
def seeded(pg_dsn: str) -> dict[str, Any]:
    """One entity: registered + unregistered + restricted-only claims."""
    from connectors.stages import CaptureRef
    from db.claim_sink import PgClaimSink
    from evidence.digest import multihash

    with psycopg.connect(pg_dsn, autocommit=True) as conn:
        conn.execute("TRUNCATE " + ", ".join(_SPINE_TABLES) + " CASCADE")

    body = b"mixed-registry-body"
    cap = CaptureRef(
        digest=multihash(body),
        media_type="text/csv",
        source_uri="https://example/mixed.csv",
        byte_size=len(body),
        retrieved_at=datetime(2026, 7, 1, tzinfo=UTC),
        ocfl_object_id="sig:capture:mixed",
        ocfl_version="v1",
    )
    sink = PgClaimSink.from_dsn(
        pg_dsn, connector_name="p32_2", connector_version="1.0.0", code_commit="p32.2-test"
    )
    sink.assert_claims(
        [
            {
                "subject_id": _SUBJECT,
                "predicate_id": "claimed_device_count",
                "value": 12,
                "source_id": "p32_2_src",
                "license": "CC0-1.0",
                "evidence_genre": "registry_export",
                "locator": {"kind": "byte_range", "start": 0, "end": 12},
            },
            {
                "subject_id": _SUBJECT,
                "predicate_id": _UNREGISTERED,
                "value": "unknown-predicate-value",
                "source_id": "p32_2_src",
                "license": "CC0-1.0",
            },
            {
                "subject_id": _SUBJECT,
                "predicate_id": _RESTRICTED,
                "value": "withheld",
                "sensitivity_tier": 1,
                "source_id": "p32_2_src",
                "license": "CC0-1.0",
            },
        ],
        capture=cap,
    )
    with psycopg.connect(pg_dsn, autocommit=True) as conn:
        (entity_id,) = conn.execute("SELECT subject_id FROM claim LIMIT 1").fetchone()
    return {"dsn": pg_dsn, "entity_id": str(entity_id)}


@pytest.fixture
def client(seeded: dict[str, Any]) -> Any:
    from api.app import create_app
    from api.store_pg import PgReadStore
    from starlette.testclient import TestClient

    store = PgReadStore(seeded["dsn"])
    with TestClient(create_app(store)) as c:
        yield c


def test_the_pg_backed_mixed_entity_serves_registered_facts(
    client: Any, seeded: dict[str, Any]
) -> None:
    r = client.get(f"/v1/entity/deployment/{seeded['entity_id']}")
    assert r.status_code == 200
    body = r.json()
    # The registered predicate produced a fact envelope; the unknown one is
    # named explicitly — no whole-entity 404, no fabricated value.
    assert body["unregistered_predicates"] == [_UNREGISTERED]
    assert len(body["facts"]) >= 1
    for fact in body["facts"]:
        assert fact.get("predicate_id") != _UNREGISTERED


def test_a_restricted_only_predicate_is_withheld_and_unnamed(
    client: Any, seeded: dict[str, Any]
) -> None:
    """The tier-1 claim's predicate never reaches the public surface — not as a
    fact, not even in unregistered_predicates (restricted stays withheld)."""
    body = client.get(f"/v1/entity/deployment/{seeded['entity_id']}").json()
    assert _RESTRICTED not in body["unregistered_predicates"]
    for fact in body["facts"]:
        assert fact.get("predicate_id") != _RESTRICTED


def test_a_truly_absent_entity_still_404s_over_pg(client: Any) -> None:
    r = client.get("/v1/entity/deployment/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
