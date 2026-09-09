# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The public read API served over PostgreSQL (P19.4, LD-F06).

These tests build :class:`api.store_pg.PgReadStore` over a live PG spine seeded with
the OKC ``claimed_device_count`` slice (299 vs 190), mount it with the unchanged
``create_app(store)``, and drive every §37.3 resource family over HTTP (Starlette
``TestClient``). They assert that:

* all 12 ``/v1/*`` families + ``/id/{type}/{uuid}`` answer 200 with the envelope
  shape over ``PgReadStore`` (the API reads the PG spine for the first time),
* a within-predicate disagreement stays **visible** through the API (§3.1), and
* a belief-pinned (as-of) read returns the historical value for ≥1 claim.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import psycopg
import pytest

_SUBJECT_IDENT = "okc:deployment:okcpd-flock"
_PREDICATE = "claimed_device_count"
_ID_SCHEME = "sig.connector.subject"

_SPINE_TABLES = (
    "claim_evidence",
    "claim",
    "extraction",
    "evidence_capture",
    "evidence_blob",
    "evidence_artifact",
    "entity_identifier",
    "coverage_record",
    "ingest_run",
    "source_registry",
    "entity",
)


@pytest.fixture(scope="module")
def seeded(pg_dsn: str) -> dict[str, Any]:
    """Seed the OKC slice + one historical (past-belief) correction; return handles."""
    from db.claim_sink import PgClaimSink

    with psycopg.connect(pg_dsn, autocommit=True) as conn:
        conn.execute("TRUNCATE " + ", ".join(_SPINE_TABLES) + " CASCADE")

    # Two current, belief-now claims for the same (subject, predicate): a visible
    # within-predicate contradiction (299 vs 190), both news_article genre.
    sink = PgClaimSink.from_dsn(
        pg_dsn, connector_name="okc", connector_version="1.0.0", code_commit="p19.4"
    )
    sink.assert_claims(
        [
            {
                "record_kind": "claim",
                "subject_id": _SUBJECT_IDENT,
                "predicate_id": _PREDICATE,
                "value": 299,
                "raw_value": "299",
                "source_id": "deflock",
                "license": "CC-BY-4.0",
                "source_attribution": "DeFlock",
                "evidence_genre": "news_article",
                "observed_at": "2026-08-20",
                "claim_id": "c1",
                "sys_period": "[x,)",
            },
            {
                "record_kind": "claim",
                "subject_id": _SUBJECT_IDENT,
                "predicate_id": _PREDICATE,
                "value": 190,
                "raw_value": "190",
                "source_id": "bacy",
                "license": "CC-BY-4.0",
                "source_attribution": "Chief Bacy",
                "evidence_genre": "news_article",
                "observed_at": "2026-08-18",
                "claim_id": "c2",
                "sys_period": "[x,)",
            },
        ]
    )

    handles: dict[str, Any] = {"dsn": pg_dsn}
    with psycopg.connect(pg_dsn, autocommit=True) as conn:
        entity_id, extraction_id, run_id, rights_id = conn.execute(
            "SELECT subject_id, extraction_id, ingest_run_id, rights_id FROM claim LIMIT 1"
        ).fetchone()
        handles["entity_id"] = str(entity_id)
        claim_id, cap_id = conn.execute(
            "SELECT c.claim_id, ce.capture_id FROM claim c "
            "JOIN claim_evidence ce ON ce.claim_id = c.claim_id LIMIT 1"
        ).fetchone()
        handles["claim_id"] = str(claim_id)
        handles["capture_id"] = str(cap_id)
        handles["artifact_id"] = str(
            conn.execute(
                "SELECT artifact_id FROM evidence_capture WHERE capture_id = %s", (cap_id,)
            ).fetchone()[0]
        )
        # A HISTORICAL claim: value 150, asserted (sys_period lower) back on
        # 2026-01-01, so a belief pinned before "now" sees it but not the 299/190
        # claims asserted at test time. INSERT with an explicit sys_period is a
        # legitimate history fixture; the append-only trigger fires only on mutation.
        conn.execute(
            "INSERT INTO claim"
            "(subject_id, predicate_id, object_type, value_kind, value_text, value_num,"
            " raw_value, observed_at, source_reliability, claim_directness, artifact_integrity,"
            " extraction_id, ingest_run_id, rights_id, sensitivity_tier, content_digest,"
            " sys_period) "
            "VALUES (%s, %s, 'literal', 'value', '150', 150, '150', '2026-01-01', 'R3','D2','I1',"
            " %s, %s, %s, 0, 'hist-okc-150', tstzrange('2026-01-01'::timestamptz, NULL, '[)'))"
            " RETURNING claim_id",
            (entity_id, _PREDICATE, extraction_id, run_id, rights_id),
        )
        # A sealed (tier-2) claim that the publication boundary must NOT publish.
        conn.execute(
            "INSERT INTO claim"
            "(subject_id, predicate_id, object_type, value_kind, value_text, value_num,"
            " raw_value, observed_at, source_reliability, claim_directness, artifact_integrity,"
            " extraction_id, ingest_run_id, rights_id, sensitivity_tier, content_digest) "
            "VALUES (%s, %s, 'literal', 'value', '999', 999, '999', '2026-08-01', 'R3','D2','I1',"
            " %s, %s, %s, 2, 'sealed-okc-999')",
            (entity_id, _PREDICATE, extraction_id, run_id, rights_id),
        )
    return handles


@pytest.fixture
def client(seeded: dict[str, Any]) -> Any:
    from api.app import create_app
    from api.store_pg import PgReadStore
    from starlette.testclient import TestClient

    store = PgReadStore(seeded["dsn"])
    with TestClient(create_app(store)) as c:
        yield c


def test_all_v1_routes_and_id_return_200_over_pg(client: Any, seeded: dict[str, Any]) -> None:
    ent = seeded["entity_id"]
    paths = {
        "resolution": f"/v1/resolution/{ent}/{_PREDICATE}",
        "entity": f"/v1/entity/deployment/{ent}",
        "claim": f"/v1/claim/{seeded['claim_id']}",
        "evidence": f"/v1/evidence/{seeded['artifact_id']}/{seeded['capture_id']}",
        "search": "/v1/search?q=okc",
        "dossier": "/v1/dossier/jurisdiction:okc",
        "coverage": f"/v1/coverage/{ent}",
        "contradiction": "/v1/contradiction",
        "task": "/v1/task",
        "crosswalk": "/v1/crosswalk",
        "export": "/v1/export",
        "changes": "/v1/changes",
    }
    assert len(paths) == 12, "every §37.3 /v1 family is exercised"
    for name, path in paths.items():
        resp = client.get(path)
        assert resp.status_code == 200, f"{name} ({path}): {resp.status_code} {resp.text[:200]}"
        # Every envelope echoes the as-of pair it used (SIG-API-005).
        assert "as_of" in resp.json(), f"{name}: response is not an as-of envelope"

    # /id/{type}/{uuid} dereferences an identifier (SIG-API-008).
    r = client.get(f"/id/{_ID_SCHEME}/{_SUBJECT_IDENT}")
    assert r.status_code == 200, r.text


def test_contradiction_stays_visible_over_pg(client: Any, seeded: dict[str, Any]) -> None:
    ent = seeded["entity_id"]
    # The material fact is NOT collapsed to one value: 299 vs 190 is contested (§3.1).
    body = client.get(f"/v1/resolution/{ent}/{_PREDICATE}").json()
    fact = body["fact"]
    assert fact.get("value") is None, f"a contested value must not be collapsed: {fact}"

    # The compute-on-read contradiction surface reflects the disagreement.
    contradictions = client.get("/v1/contradiction").json()["contradictions"]
    assert any(
        c["subject_id"] == ent and c["predicate_id"] == _PREDICATE for c in contradictions
    ), f"the 299-vs-190 disagreement must be a visible contradiction: {contradictions}"


def test_as_of_belief_returns_historical_value(seeded: dict[str, Any]) -> None:
    from api.store_pg import PgReadStore

    store = PgReadStore(seeded["dsn"])
    ent = seeded["entity_id"]

    # Belief pinned before the 299/190 claims were asserted: only the historical
    # value=150 claim (sys_period lower = 2026-01-01) is visible.
    historical = store.claims_for(ent, _PREDICATE, as_of_belief=datetime(2026, 6, 1, tzinfo=UTC))
    hist_values = {c.value for c in historical}
    assert hist_values == {150}, f"a past-belief read must see only history, got {hist_values}"

    # Belief pinned to now: the current claims are visible too.
    current = store.claims_for(ent, _PREDICATE, as_of_belief=datetime.now(tz=UTC))
    now_values = {c.value for c in current}
    assert {299, 190} <= now_values, f"a now-belief read must see the current claims: {now_values}"
    assert 999 not in now_values, "the sealed (tier-2) claim must never be published (§0.7)"
    store.close()
