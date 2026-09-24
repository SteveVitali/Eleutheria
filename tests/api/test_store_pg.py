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


def test_watermark_keyed_serve_path_discloses_and_invalidates(
    pg_dsn: str, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """P25.10: same set as compute-on-read, watermark disclosed, never stale.

    The spine is append-only, so the compute-on-read annotation set is memoised
    against the spine watermark: repeated reads at one watermark never recompute;
    a new contradiction-producing claim bumps the watermark and the endpoint
    reflects it on the next read; the cache can never serve a stale set.
    """
    from api.app import create_app
    from api.store_pg import PgReadStore
    from db.claim_sink import PgClaimSink
    from starlette.testclient import TestClient

    store = PgReadStore(pg_dsn)
    compute_calls = 0
    original = store._compute_on_read

    def _counting_compute(conn: Any) -> Any:
        nonlocal compute_calls
        compute_calls += 1
        return original(conn)

    monkeypatch.setattr(store, "_compute_on_read", _counting_compute)

    with TestClient(create_app(store)) as client:
        first = client.get("/v1/contradiction").json()
        wm1 = first["spine_watermark"]
        assert wm1 and "claims=" in wm1, f"freshness must be disclosed: {wm1}"
        ids1 = {c["contradiction_id"] for c in first["contradictions"]}
        ent = seeded["entity_id"]
        assert f"contradiction:{ent}:{_PREDICATE}" in ids1
        assert all(c["spine_watermark"] == wm1 for c in first["contradictions"]), (
            "every served item states the watermark it was computed at"
        )

        # A second read at the same watermark is the memoised set, no recompute.
        second = client.get("/v1/contradiction").json()
        assert second["spine_watermark"] == wm1
        assert {c["contradiction_id"] for c in second["contradictions"]} == ids1
        assert compute_calls == 1, "a same-watermark read must never recompute"

        # /v1/task is the same shape: the shared cached view, same disclosure.
        tasks = client.get("/v1/task").json()
        assert tasks["spine_watermark"] == wm1
        assert compute_calls == 1

        # --- invalidation: a new contradiction-producing claim lands ---------
        sink = PgClaimSink.from_dsn(
            pg_dsn, connector_name="okc", connector_version="1.0.0", code_commit="p25.10"
        )
        new_subject = "okc:deployment:p25-10-watermark"
        sink.assert_claims(
            [
                {
                    "record_kind": "claim",
                    "subject_id": new_subject,
                    "predicate_id": _PREDICATE,
                    "value": 11,
                    "raw_value": "11",
                    "source_id": "p25-10-src-a",
                    "license": "CC-BY-4.0",
                    "source_attribution": "P25.10 test source A",
                    "evidence_genre": "news_article",
                    "observed_at": "2026-09-16",
                    "claim_id": "p25-10-a",
                    "sys_period": "[x,)",
                },
                {
                    "record_kind": "claim",
                    "subject_id": new_subject,
                    "predicate_id": _PREDICATE,
                    "value": 22,
                    "raw_value": "22",
                    "source_id": "p25-10-src-b",
                    "license": "CC-BY-4.0",
                    "source_attribution": "P25.10 test source B",
                    "evidence_genre": "news_article",
                    "observed_at": "2026-09-16",
                    "claim_id": "p25-10-b",
                    "sys_period": "[x,)",
                },
            ]
        )

        # The bumped watermark recomputes exactly once and serves BOTH the old
        # and the new contradiction; a stale set can never be served.
        third = client.get("/v1/contradiction").json()
        assert third["spine_watermark"] != wm1
        ids3 = {c["contradiction_id"] for c in third["contradictions"]}
        new_ids = ids3 - ids1
        assert len(new_ids) == 1, f"exactly one new contradiction appears: {new_ids}"
        assert new_ids.pop().endswith(f":{_PREDICATE}")
        assert f"contradiction:{ent}:{_PREDICATE}" in ids3, "the old set is retained"
        assert compute_calls == 2, "a bumped watermark recomputes exactly once"

        # The single-item route discloses the same watermark.
        item = client.get(f"/v1/contradiction/{sorted(ids3)[0]}").json()
        assert item["spine_watermark"] == third["spine_watermark"]
    store.close()


# =============================================================================
# P31.1 (HARDEN.1, ADR-108): DB resilience + bounded search over real PG
# =============================================================================

_NEEDLE = "p31needle"


class _CountingConn:
    """Proxy that counts every statement a pooled read executes."""

    def __init__(self, conn: Any, counter: _CountingPool) -> None:
        self._conn = conn
        self._counter = counter

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        self._counter.statements += 1
        return self._conn.execute(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)


class _CountingPool:
    """Wraps the store's real pool: counts checkouts and statements."""

    def __init__(self, pool: Any) -> None:
        self._pool = pool
        self.statements = 0
        self.checkouts = 0

    def connection(self, timeout: float | None = None) -> Any:
        from contextlib import contextmanager

        @contextmanager
        def _cm() -> Any:
            self.checkouts += 1
            with self._pool.connection() as conn:
                yield _CountingConn(conn, self)

        return _cm()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._pool, name)


def _terminate(dsn: str, application_name: str) -> list[int]:
    """Kill every backend carrying ``application_name``; wait until they are gone."""
    import time

    with psycopg.connect(dsn, autocommit=True) as admin:
        pids = [
            int(r[0])
            for r in admin.execute(
                "SELECT pid FROM pg_stat_activity WHERE application_name = %s", (application_name,)
            ).fetchall()
        ]
        for pid in pids:
            admin.execute("SELECT pg_terminate_backend(%s)", (pid,))
        deadline = time.time() + 10
        while time.time() < deadline:
            left = admin.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE pid = ANY(%s)", (pids,)
            ).fetchone()[0]
            if left == 0:
                break
            time.sleep(0.05)
    return pids


def test_a_terminated_backend_does_not_500_the_next_request(seeded: dict[str, Any]) -> None:
    """D-P30.4-1: kill the store's backend between two requests; the second is 200.

    The pre-P31.1 store held ONE long-lived connection and answered every later
    request with 500 (``server closed the connection unexpectedly``) until the
    process was recycled. Now the next checkout finds the connection dead, the
    pool replaces it, and ``SET ROLE`` is re-applied on the replacement.
    """
    import uuid

    from api.app import create_app
    from api.store_pg import PgReadStore
    from starlette.testclient import TestClient

    app_name = f"sig-api-p31-{uuid.uuid4().hex[:8]}"
    store = PgReadStore(
        seeded["dsn"], role="sig_read_public", application_name=app_name, pool_max=2
    )
    ent = seeded["entity_id"]
    try:
        with TestClient(create_app(store)) as client:
            before = client.get(f"/v1/entity/deployment/{ent}")
            assert before.status_code == 200, before.text

            killed = _terminate(seeded["dsn"], app_name)
            assert killed, "the store must have held at least one backend to kill"

            after = client.get(f"/v1/entity/deployment/{ent}")
            assert after.status_code == 200, f"reconnect failed: {after.status_code} {after.text}"
            assert after.json()["entity_id"] == before.json()["entity_id"]
            assert client.get("/health").json()["status"] == "ok"

            # A NEW backend serves, still under the read role (configure re-ran).
            with psycopg.connect(seeded["dsn"], autocommit=True) as admin:
                live = {
                    int(r[0])
                    for r in admin.execute(
                        "SELECT pid FROM pg_stat_activity WHERE application_name = %s",
                        (app_name,),
                    ).fetchall()
                }
            assert live and not (live & set(killed)), "the killed backends were replaced"
            role = store._run_read(lambda: store._conn.execute("SELECT current_user").fetchone()[0])
            assert role == "sig_read_public", "SET ROLE must be re-applied on reconnect"
    finally:
        store.close()


def test_a_connection_dropped_mid_read_is_retried_once(seeded: dict[str, Any]) -> None:
    """The dead connection IS handed out (no checkout check); the read still
    succeeds because ``_run_read`` purges the dead idle connections and retries
    once on a fresh one."""
    import uuid

    from api.store_pg import PgReadStore

    app_name = f"sig-api-p31-{uuid.uuid4().hex[:8]}"
    store = PgReadStore(seeded["dsn"], application_name=app_name, pool_min=1, pool_max=1)
    counting = _CountingPool(store._pool)
    store._pool = counting  # type: ignore[assignment]
    try:
        assert store.stored_claim(seeded["claim_id"]) is not None
        _terminate(seeded["dsn"], app_name)
        counting.checkouts = 0
        claim = store.stored_claim(seeded["claim_id"])
        assert claim is not None, "the read answered after the drop"
        assert counting.checkouts == 2, "exactly one retry on a fresh connection"
    finally:
        counting._pool.close()


def test_a_restart_that_kills_every_pooled_connection_costs_one_fast_retry(
    seeded: dict[str, Any],
) -> None:
    """The hosted roll found this: with the pool's own checkout check, a request
    after ALL pooled connections died walked the dead ones with a 1 s, 2 s, 4 s
    backoff and got a 503 after the 10 s timeout. Now the first read purges them
    all at once and is served on a fresh connection, well inside a second."""
    import time
    import uuid

    from api.app import create_app
    from api.store_pg import PgReadStore
    from starlette.testclient import TestClient

    app_name = f"sig-api-p31-{uuid.uuid4().hex[:8]}"
    store = PgReadStore(seeded["dsn"], application_name=app_name, pool_min=5, pool_max=5)
    store._pool.wait(timeout=20)
    try:
        with TestClient(create_app(store)) as client:
            assert client.get("/v1/crosswalk").status_code == 200
            killed = _terminate(seeded["dsn"], app_name)
            assert len(killed) == 5, killed
            t0 = time.perf_counter()
            r = client.get("/v1/crosswalk")
            elapsed = time.perf_counter() - t0
            assert r.status_code == 200, r.text
            assert elapsed < 2.0, f"the first request after the restart took {elapsed:.1f}s"
            assert client.get("/health").json()["status"] == "ok"
    finally:
        store.close()


@pytest.fixture(scope="module")
def needles(seeded: dict[str, Any]) -> list[str]:
    """30 entities whose identifier contains the needle, over 3 sources."""
    from db.claim_sink import PgClaimSink

    sink = PgClaimSink.from_dsn(
        seeded["dsn"], connector_name="p31", connector_version="1.0.0", code_commit="p31.1"
    )
    sink.assert_claims(
        [
            {
                "record_kind": "claim",
                "subject_id": f"{_NEEDLE}:deployment:{i:02d}",
                "predicate_id": _PREDICATE,
                "value": i,
                "raw_value": str(i),
                "source_id": f"p31-src-{i % 3}",
                "license": "CC-BY-4.0",
                "source_attribution": f"P31.1 test source {i % 3}",
                "evidence_genre": "news_article",
                "observed_at": "2026-09-24",
                "claim_id": f"p31-needle-{i:02d}",
                "sys_period": "[x,)",
            }
            for i in range(30)
        ]
    )
    with psycopg.connect(seeded["dsn"], autocommit=True) as conn:
        return sorted(
            str(r[0])
            for r in conn.execute(
                "SELECT DISTINCT entity_id FROM entity_identifier WHERE value LIKE %s",
                (f"{_NEEDLE}:%",),
            ).fetchall()
        )


def test_search_is_capped_paginated_and_consistent(
    seeded: dict[str, Any], needles: list[str]
) -> None:
    """D-P30.4-2: the page is capped, the cursor walks every match exactly once, and
    each hit's label/sources equal the per-entity reads the old N+1 loop issued."""
    from api.app import create_app
    from api.store_pg import PgReadStore
    from starlette.testclient import TestClient

    assert len(needles) == 30
    store = PgReadStore(seeded["dsn"])
    try:
        with TestClient(create_app(store)) as client:
            seen: list[str] = []
            cursor = None
            while True:
                params: dict[str, Any] = {"q": _NEEDLE, "limit": 7}
                if cursor:
                    params["cursor"] = cursor
                r = client.get("/v1/search", params=params)
                assert r.status_code == 200, r.text
                body = r.json()
                assert len(body["results"]) <= 7 and body["limit"] == 7
                seen.extend(x["entity_id"] for x in body["results"])
                cursor = body["next_cursor"]
                if cursor is None:
                    break
            assert seen == needles, "keyset pages cover every match once, in order"

            bad = client.get("/v1/search", params={"q": _NEEDLE, "cursor": "not-a-cursor"})
            assert bad.status_code == 422

        page = store.search(_NEEDLE, limit=30)
        for rec in page:
            label, sources = store._run_read(
                lambda rec=rec: (
                    store._label_for(rec.entity_id),
                    store._source_ids_for_entity(rec.entity_id),
                )
            )
            assert rec.label == label, "set-based label == the per-entity rule"
            assert list(rec.source_ids) == sources, "set-based sources == per-entity sources"
        assert {s for rec in page for s in rec.source_ids} == {
            "p31-src-0",
            "p31-src-1",
            "p31-src-2",
        }
    finally:
        store.close()


def test_search_statement_count_does_not_grow_with_the_page(
    seeded: dict[str, Any], needles: list[str]
) -> None:
    """No N+1: a 3-row page and a 30-row page cost the same number of statements."""
    from api.store_pg import PgReadStore

    store = PgReadStore(seeded["dsn"])
    counting = _CountingPool(store._pool)
    store._pool = counting  # type: ignore[assignment]
    try:
        counts = {}
        for limit in (3, 30):
            counting.statements = 0
            hits = store.search(_NEEDLE, limit=limit)
            assert len(hits) == limit
            counts[limit] = counting.statements
        assert counts[3] == counts[30] == 4, f"timeout + match + labels + sources: {counts}"
    finally:
        counting._pool.close()


def test_search_statement_timeout_is_a_503_and_does_not_leak(
    seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A search past its statement timeout is a 503 (never retried), and the
    transaction-local timeout does not leak onto the pooled connection."""
    import api.store_pg as store_pg
    from api.app import create_app
    from starlette.testclient import TestClient

    slow = (
        "SELECT NULL::uuid, NULL::text FROM pg_sleep(2) "
        "WHERE %(pattern)s::text IS NOT NULL AND %(limit)s::int > 0"
    )
    monkeypatch.setattr(store_pg, "SEARCH_SQL", slow)
    store = store_pg.PgReadStore(seeded["dsn"], search_timeout_ms=100, pool_max=1)
    try:
        with TestClient(create_app(store)) as client:
            r = client.get("/v1/search", params={"q": _NEEDLE})
            assert r.status_code == 503, r.text
            # Same (only) pooled connection afterwards: no statement timeout leaked.
            timeout = store._run_read(
                lambda: store._conn.execute("SHOW statement_timeout").fetchone()[0]
            )
            assert timeout == "0"
            assert client.get("/v1/crosswalk").status_code == 200
    finally:
        store.close()


def test_search_plan_uses_the_trigram_index_at_scale(seeded: dict[str, Any]) -> None:
    """The planner picks ``entity_identifier_value_trgm_idx`` for a selective term.

    The seeded test spine is a handful of rows, where a scan is rightly cheapest.
    So this loads 20,000 identifiers shaped like the hosted camera-registry ones
    INSIDE a transaction, ANALYZEs, EXPLAINs the store's exact search statement
    (planner settings untouched), and rolls everything back. The hosted plan over
    247k identifiers is recorded in docs/build/runs/P31.1.md.
    """
    from api.store_pg import SEARCH_SQL, like_pattern

    with psycopg.connect(seeded["dsn"]) as conn:  # a transaction, rolled back below
        try:
            conn.execute(
                "WITH e AS (INSERT INTO entity(entity_type) "
                "           SELECT 'deployment' FROM generate_series(1, 20000) "
                "           RETURNING entity_id) "
                "INSERT INTO entity_identifier(entity_id, scheme, value) "
                "SELECT entity_id, 'sig.connector.subject', "
                "       'traffic_camera:camreg_bulk:' || md5(entity_id::text) FROM e"
            )
            # A bulk insert lands in GIN's pending list (costed as a scan of that
            # list) until VACUUM merges it; the hosted index is freshly BUILT, so
            # merge it here to plan against the same shape.
            conn.execute("SELECT gin_clean_pending_list('entity_identifier_value_trgm_idx')")
            conn.execute("ANALYZE entity_identifier")
            conn.execute("ANALYZE entity")
            cur = psycopg.ClientCursor(conn)
            cur.execute(
                "EXPLAIN " + SEARCH_SQL,
                {"pattern": like_pattern(_NEEDLE), "limit": 51},
            )
            plan = "\n".join(r[0] for r in cur.fetchall())
        finally:
            conn.rollback()
    assert "entity_identifier_value_trgm_idx" in plan, plan
    assert "Seq Scan on entity_identifier" not in plan, plan


def test_the_compute_path_reconnects_too(seeded: dict[str, Any]) -> None:
    """The annotation surface (pooled watermark read + dedicated compute
    connection) answers 200 after the store's backends are killed."""
    import uuid

    from api.app import create_app
    from api.store_pg import PgReadStore
    from starlette.testclient import TestClient

    app_name = f"sig-api-p31-{uuid.uuid4().hex[:8]}"
    store = PgReadStore(seeded["dsn"], application_name=app_name, pool_max=2)
    try:
        with TestClient(create_app(store)) as client:
            assert client.get("/v1/contradiction").status_code == 200
            assert _terminate(seeded["dsn"], app_name), "a pooled backend existed"
            store._annotation_cache = None  # force the dedicated-connection compute
            r = client.get("/v1/contradiction")
            assert r.status_code == 200, r.text
            assert r.json()["contradictions"], "the served set is intact after reconnect"
    finally:
        store.close()


def test_queued_annotation_requests_hold_no_pooled_connection(
    seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """While one request computes the annotation set (under the lock), others queue
    on the lock WITHOUT a pooled connection, so plain reads keep being served."""
    import threading
    import time

    from api.app import create_app
    from api.store_pg import PgReadStore
    from starlette.testclient import TestClient

    store = PgReadStore(seeded["dsn"], pool_max=2, pool_timeout=3)
    original = store._compute_on_read
    started = threading.Event()

    def _slow_compute(conn: Any) -> Any:
        started.set()
        time.sleep(3)
        return original(conn)

    monkeypatch.setattr(store, "_compute_on_read", _slow_compute)
    try:
        with TestClient(create_app(store)) as client:
            results: list[int] = []
            workers = [
                threading.Thread(
                    target=lambda: results.append(client.get("/v1/contradiction").status_code)
                )
                for _ in range(4)
            ]
            for w in workers:
                w.start()
            assert started.wait(10), "the compute started"
            t0 = time.perf_counter()
            plain = client.get("/v1/crosswalk")
            elapsed = time.perf_counter() - t0
            assert plain.status_code == 200, plain.text
            assert elapsed < 2.5, f"a plain read waited {elapsed:.1f}s behind the lock queue"
            for w in workers:
                w.join(30)
            assert results == [200, 200, 200, 200]
            assert store.health().pool["requests_waiting"] == 0  # type: ignore[index]
    finally:
        store.close()


def test_concurrent_mixed_reads_share_a_small_pool(seeded: dict[str, Any]) -> None:
    """24 threads of mixed reads over a 2-connection pool: all succeed, and every
    read ran on the connection its own thread checked out."""
    from concurrent.futures import ThreadPoolExecutor

    from api.store_pg import PgReadStore

    store = PgReadStore(seeded["dsn"], pool_max=2, pool_timeout=20)
    ent = seeded["entity_id"]

    def work(i: int) -> bool:
        kind = i % 4
        if kind == 0:
            return store.entity("deployment", ent) is not None
        if kind == 1:
            return store.stored_claim(seeded["claim_id"]) is not None
        if kind == 2:
            return len(store.search("okc", limit=5)) >= 1
        return store._run_read(lambda: store._conn is store._local.conn)

    try:
        with ThreadPoolExecutor(max_workers=24) as pool:
            outcomes = list(pool.map(work, range(96)))
        assert all(outcomes), outcomes
        stats = store.health().pool
        assert stats is not None and stats["pool_size"] <= 2
    finally:
        store.close()


def test_search_after_cursor_plan_uses_the_trigram_index(seeded: dict[str, Any]) -> None:
    """The cursor (page 2+) statement also plans on the trigram index for a
    selective term, at a hosted-like scale (loaded and rolled back)."""
    from api.store_pg import SEARCH_AFTER_SQL, like_pattern

    with psycopg.connect(seeded["dsn"]) as conn:
        try:
            conn.execute(
                "WITH e AS (INSERT INTO entity(entity_type) "
                "           SELECT 'deployment' FROM generate_series(1, 20000) "
                "           RETURNING entity_id) "
                "INSERT INTO entity_identifier(entity_id, scheme, value) "
                "SELECT entity_id, 'sig.connector.subject', "
                "       'traffic_camera:camreg_bulk:' || md5(entity_id::text) FROM e"
            )
            conn.execute("SELECT gin_clean_pending_list('entity_identifier_value_trgm_idx')")
            conn.execute("ANALYZE entity_identifier")
            conn.execute("ANALYZE entity")
            after = conn.execute(
                "SELECT entity_id FROM entity ORDER BY entity_id LIMIT 1"
            ).fetchone()[0]
            cur = psycopg.ClientCursor(conn)
            cur.execute(
                "EXPLAIN " + SEARCH_AFTER_SQL,
                {"pattern": like_pattern(_NEEDLE), "limit": 51, "after": str(after)},
            )
            plan = "\n".join(r[0] for r in cur.fetchall())
        finally:
            conn.rollback()
    assert "entity_identifier_value_trgm_idx" in plan, plan
