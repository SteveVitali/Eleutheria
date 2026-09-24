# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P31.1 (HARDEN.1, ADR-108): DB resilience + bounded ``/v1/search`` — no Docker.

The real-PG halves (a terminated backend, the query count, the index plan) live in
``test_store_pg.py``. These pin the pure contract:

* ``PgReadStore._run_read`` retries an idempotent read exactly ONCE after its
  connection died, never retries a statement timeout, a pool timeout, or an error on
  a live connection, and surfaces every give-up as ``StoreUnavailable`` (→ 503),
  never a 500;
* ``/v1/search`` enforces the minimum query length, the page-size cap, and keyset
  pagination (``next_cursor``) — additive fields only, for the demo store too;
* ``GET /health`` answers 200/503 from the store's readiness, outside ``/v1``.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
import pytest
from api.store import (
    SEARCH_DEFAULT_LIMIT,
    SEARCH_MAX_LIMIT,
    SEARCH_MIN_QUERY_LENGTH,
    EntityRecord,
    InMemoryStore,
    StoreHealth,
    StoreQueryTimeout,
    StoreUnavailable,
)
from api.store_pg import PgReadStore, _pooled, like_pattern
from psycopg_pool import PoolTimeout
from starlette.testclient import TestClient

from api import create_app

# --- _run_read: retry-once semantics over a fake pool ---------------------------


class _FakeConn:
    """Stands in for a psycopg connection: only ``closed``/``broken`` matter here."""

    def __init__(self) -> None:
        self.closed = False
        self.broken = False


class _FakePool:
    """Hands out fresh fake connections; counts checkouts."""

    def __init__(self) -> None:
        self.checkouts = 0

    @contextmanager
    def connection(self, timeout: float | None = None) -> Iterator[_FakeConn]:
        self.checkouts += 1
        yield _FakeConn()


def _drop(store: PgReadStore) -> None:
    """Simulate the server dropping the read's connection mid-flight."""
    store._conn.broken = True  # type: ignore[attr-defined]
    raise psycopg.OperationalError("server closed the connection unexpectedly")


def _store_with(pool: object) -> PgReadStore:
    store = PgReadStore.__new__(PgReadStore)
    store._pool = pool  # type: ignore[assignment]
    store._local = threading.local()
    return store


def test_a_dropped_connection_is_retried_exactly_once() -> None:
    pool = _FakePool()
    store = _store_with(pool)
    calls = 0

    def read() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            _drop(store)
        return "ok"

    assert store._run_read(read) == "ok"
    assert calls == 2 and pool.checkouts == 2, "one retry, on a fresh checkout"
    assert getattr(store._local, "conn", None) is None, "the binding is released"


def test_a_second_drop_gives_up_as_store_unavailable() -> None:
    pool = _FakePool()
    store = _store_with(pool)

    def read() -> str:
        _drop(store)
        return "never"

    with pytest.raises(StoreUnavailable):
        store._run_read(read)
    assert pool.checkouts == 2, "retried once, then gave up (no retry storm)"


def test_an_error_on_a_live_connection_is_not_retried() -> None:
    """Only a DEAD connection is retried: e.g. out-of-memory or a lock error on a
    healthy connection is a 503 at once, never a second (possibly heavy) attempt."""
    pool = _FakePool()
    store = _store_with(pool)

    def read() -> str:
        raise psycopg.errors.OutOfMemory("out of memory")

    with pytest.raises(StoreUnavailable):
        store._run_read(read)
    assert pool.checkouts == 1


def test_a_statement_timeout_is_never_retried() -> None:
    pool = _FakePool()
    store = _store_with(pool)

    def read() -> str:
        raise psycopg.errors.QueryCanceled("canceling statement due to statement timeout")

    with pytest.raises(StoreQueryTimeout):
        store._run_read(read)
    assert pool.checkouts == 1


def test_a_pool_timeout_is_never_retried() -> None:
    class _ExhaustedPool(_FakePool):
        @contextmanager
        def connection(self, timeout: float | None = None) -> Iterator[object]:
            self.checkouts += 1
            raise PoolTimeout("couldn't get a connection after 10.00 sec")
            yield object()  # pragma: no cover

    pool = _ExhaustedPool()
    store = _store_with(pool)
    with pytest.raises(StoreUnavailable) as info:
        store._run_read(lambda: "never")
    assert not isinstance(info.value, StoreQueryTimeout)
    assert pool.checkouts == 1


def test_a_non_connection_error_is_not_swallowed() -> None:
    store = _store_with(_FakePool())

    def read() -> str:
        raise psycopg.errors.UndefinedTable("relation does not exist")

    with pytest.raises(psycopg.errors.UndefinedTable):
        store._run_read(read)


def test_pooled_reads_are_reentrant_on_the_held_connection() -> None:
    seen: list[object] = []

    class _Nested(PgReadStore):
        @_pooled
        def outer(self) -> None:
            seen.append(self._conn)
            self.inner()  # a pooled read called from inside a pooled read

        @_pooled
        def inner(self) -> None:
            seen.append(self._conn)

    pool = _FakePool()
    store = _Nested.__new__(_Nested)
    store._pool = pool  # type: ignore[assignment]
    store._local = threading.local()
    store.outer()
    assert pool.checkouts == 1 and seen[0] is seen[1], "re-entered on the held connection"
    with pytest.raises(RuntimeError):
        _ = store._conn  # outside any pooled read there is no connection


def test_like_pattern_escapes_metacharacters() -> None:
    assert like_pattern("flock") == "%flock%"
    assert like_pattern("100%") == "%100\\%%"
    assert like_pattern("a_b") == "%a\\_b%"
    assert like_pattern("c:\\x") == "%c:\\\\x%"


# --- /v1/search bounds over the demo store --------------------------------------


def _paged_store(n: int) -> InMemoryStore:
    store = InMemoryStore()
    for i in range(n):
        store.add_entity(
            EntityRecord(entity_id=f"agency:needle-{i:03d}", entity_type="agency", label=None)
        )
    return store


def test_search_short_query_is_422_and_empty_query_stays_200(client: TestClient) -> None:
    short = "x" * (SEARCH_MIN_QUERY_LENGTH - 1)
    r = client.get("/v1/search", params={"q": short})
    assert r.status_code == 422, r.text
    assert "at least" in r.json()["detail"]
    # Whitespace and punctuation do not count: the index needs a run of 3
    # letters/digits (a trigram), so "a-b" or "a b" is refused like "ab".
    for q in (f"  {short}  ", "a-b", "a b", "a_b", "..."):
        assert client.get("/v1/search", params={"q": q}).status_code == 422, q
    assert client.get("/v1/search", params={"q": "okc"}).status_code == 200
    empty = client.get("/v1/search", params={"q": ""})
    assert empty.status_code == 200 and empty.json()["results"] == []
    assert empty.json()["next_cursor"] is None


def test_search_limit_is_capped(client: TestClient) -> None:
    assert client.get("/v1/search", params={"q": "okc", "limit": 0}).status_code == 422
    over = client.get("/v1/search", params={"q": "okc", "limit": SEARCH_MAX_LIMIT + 1})
    assert over.status_code == 422
    ok = client.get("/v1/search", params={"q": "okc", "limit": SEARCH_MAX_LIMIT})
    assert ok.status_code == 200 and ok.json()["limit"] == SEARCH_MAX_LIMIT
    default = client.get("/v1/search", params={"q": "okc"}).json()
    assert default["limit"] == SEARCH_DEFAULT_LIMIT


def test_search_pages_with_a_keyset_cursor() -> None:
    client = TestClient(create_app(_paged_store(23)))
    seen: list[str] = []
    cursor: str | None = None
    pages = 0
    while True:
        params: dict[str, Any] = {"q": "needle", "limit": 10}
        if cursor:
            params["cursor"] = cursor
        body = client.get("/v1/search", params=params).json()
        ids = [r["entity_id"] for r in body["results"]]
        assert len(ids) <= 10
        seen.extend(ids)
        pages += 1
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert pages == 3
    assert seen == sorted(seen) and len(seen) == len(set(seen)) == 23, "complete, no dupes"


def test_search_exact_page_has_no_next_cursor() -> None:
    client = TestClient(create_app(_paged_store(10)))
    body = client.get("/v1/search", params={"q": "needle", "limit": 10}).json()
    assert len(body["results"]) == 10 and body["next_cursor"] is None


def test_search_response_change_is_additive(client: TestClient) -> None:
    body = client.get("/v1/search", params={"q": "oklahoma"}).json()
    # Every pre-P31.1 field is still present with its old meaning.
    assert {"query", "results", "coverage", "license", "as_of"} <= set(body)
    assert set(body) - {"query", "results", "coverage", "license", "as_of"} == {
        "limit",
        "next_cursor",
    }


# --- 503 mapping + /health -----------------------------------------------------


class _DownStore(InMemoryStore):
    def search(self, query: str, *, limit: int = 50, after: str | None = None) -> list[Any]:
        raise StoreQueryTimeout("statement timeout")

    def crosswalk_rows(self) -> list[Any]:
        raise StoreUnavailable("database connection lost")

    def health(self) -> StoreHealth:
        return StoreHealth(ok=False, backend="postgresql", detail="PoolTimeout", pool={})


def test_store_unavailable_is_a_503_not_a_500() -> None:
    client = TestClient(create_app(_DownStore()), raise_server_exceptions=False)
    r = client.get("/v1/crosswalk")
    assert r.status_code == 503, r.text
    assert r.headers.get("retry-after") == "5"
    s = client.get("/v1/search", params={"q": "flock"})
    assert s.status_code == 503 and "time budget" in s.json()["detail"]


def test_health_reports_store_readiness() -> None:
    up = TestClient(create_app(InMemoryStore())).get("/health")
    assert up.status_code == 200
    assert up.json()["status"] == "ok" and up.json()["backend"] == "in-memory"
    assert up.headers["cache-control"] == "no-store"
    down = TestClient(create_app(_DownStore())).get("/health")
    assert down.status_code == 503
    assert down.json()["status"] == "unavailable" and down.json()["detail"] == "PoolTimeout"


def test_health_is_unversioned_and_not_a_prohibited_surface(client: TestClient) -> None:
    paths = set(client.get("/openapi.json").json()["paths"])
    assert "/health" in paths and "/v1/health" not in paths
    # Cloud Run reserves some paths ending in "z"; the route must not be /healthz.
    assert "/healthz" not in paths
    assert client.get("/").json()["health"] == "/health"
