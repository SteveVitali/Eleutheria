# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.13 / SIG-API-009 — the public read API's enforced per-client rate limits.

The contract (the ticket's SIG-API-009 read + K3 §5.6 / D-K3-6 [B-30]):
30 requests per 60 seconds per client with burst 10; the
``RateLimit-Limit``/``RateLimit-Remaining``/``RateLimit-Reset`` headers ride
**every** response — success, error and the rejection itself; an over-limit
burst is refused with the documented 429 + ``Retry-After`` + the typed
``{detail, code, **extra}`` body (``code: "rate_limited"``), HTML when the
client asked for the no-JS representation (DR-C4-10). The bucket keys on the
edge-appended client address — never the raw peer, never a client-supplied
chain entry (C4 NEW-16). The whole mechanism is in-process: no managed edge
layer (D-K3-6 stays open; SIG-STORE-003's zero-cost posture binds). The
curation app and the intake receiver keep their own postures — the limiter
is the public read app's only.
"""

from __future__ import annotations

import pytest
from api.rate_limit import (
    RATE_LIMIT_BURST,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
    RateLimitConfig,
    TokenBucketLimiter,
    client_key,
)
from api.store import ReadStore
from starlette.testclient import TestClient

from api import create_app

RATE_HEADERS = ("ratelimit-limit", "ratelimit-remaining", "ratelimit-reset")

# The LB-appended tail every fixture request carries: the client's real
# address then the (fake) load-balancer address — Google's external LB shape
# (`<client>, <lb-ip>`; K3 §5.6).
LB_TAIL = ", 34.117.0.1"
CLIENT_A = "203.0.113.10"
CLIENT_B = "198.51.100.20"


def _app(store: ReadStore, posture: str = "enforce", hops: int = 2) -> TestClient:
    return TestClient(
        create_app(
            store,
            rate_limit=RateLimitConfig(posture=posture, trusted_proxy_hops=hops),
        )
    )


@pytest.fixture
def client(store: ReadStore) -> TestClient:
    return _app(store)


def _assert_rate_headers(resp, *, limit: int = RATE_LIMIT_REQUESTS) -> None:
    for name in RATE_HEADERS:
        assert name in resp.headers, f"missing {name} on {resp.status_code} {resp.url.path}"
    assert resp.headers["ratelimit-limit"] == str(limit)
    assert 0 <= int(resp.headers["ratelimit-remaining"]) <= RATE_LIMIT_BURST
    assert int(resp.headers["ratelimit-reset"]) >= 0


# --- the documented surface ------------------------------------------------ #


def test_headers_on_every_response_path(client: TestClient) -> None:
    """Limit/remaining/reset ride every response — a success, a typed 404,
    a validation 422, the dereference surface and the service routes alike."""
    for path in (
        "/health",
        "/",
        "/terms",
        "/v1/contradiction",
        "/v1/dossier/jurisdiction:nowhere",  # typed 404 (scope_not_available)
        "/v1/releases/nope/compartments/x/search?limit=abc",  # 422 validation
        "/no-such-route",  # framework 404
    ):
        resp = client.get(path, headers={"x-forwarded-for": CLIENT_A + LB_TAIL})
        _assert_rate_headers(resp)


def test_unhandled_error_still_carries_headers(store: ReadStore) -> None:
    """A 500 the app never planned for still answers inside the limiter — the
    middleware emits it so the rate headers ride even an unplanned error."""
    app = create_app(store, rate_limit=RateLimitConfig(posture="enforce", trusted_proxy_hops=2))

    @app.get("/v1/__boom__")
    def _boom() -> None:
        raise RuntimeError("planted failure")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/v1/__boom__", headers={"x-forwarded-for": CLIENT_A + LB_TAIL})
    assert resp.status_code == 500
    _assert_rate_headers(resp)


def test_over_limit_burst_returns_the_documented_rejection(client: TestClient) -> None:
    """A client exhausting the burst gets 429 + Retry-After + the headers +
    the typed {detail, code, …} body (``rate_limited``) — the rejection the
    spec documents."""
    headers = {"x-forwarded-for": CLIENT_A + LB_TAIL}
    for _ in range(RATE_LIMIT_BURST):
        resp = client.get("/health", headers=headers)
        assert resp.status_code == 200
        _assert_rate_headers(resp)
    rejected = client.get("/health", headers=headers)
    assert rejected.status_code == 429
    _assert_rate_headers(rejected)
    assert rejected.headers["ratelimit-remaining"] == "0"
    retry_after = int(rejected.headers["retry-after"])
    assert retry_after >= 1
    body = rejected.json()
    assert body["code"] == "rate_limited"
    assert body["limit"] == RATE_LIMIT_REQUESTS
    assert body["window_seconds"] == RATE_LIMIT_WINDOW_SECONDS
    assert body["burst"] == RATE_LIMIT_BURST
    assert body["retry_after_seconds"] == retry_after
    assert "detail" in body
    # The basis label still stamps the rejection (the middleware sits inside
    # the outermost basis wrapper — an over-limit answer still names its
    # authority).
    assert rejected.headers["x-sig-basis"] == "live-spine"
    assert body["basis"]["kind"] == "live-spine"


def test_rejected_burst_is_html_for_html_clients(client: TestClient) -> None:
    """DR-C4-10 / K3 §5.6: a client asking for the no-JS representation gets
    an HTML page on the 429, never a bare JSON body."""
    headers = {"x-forwarded-for": CLIENT_A + LB_TAIL, "accept": "text/html"}
    for _ in range(RATE_LIMIT_BURST + 1):
        resp = client.get("/health", headers=headers)
    assert resp.status_code == 429
    assert resp.headers["content-type"].startswith("text/html")
    assert "Too many requests" in resp.text
    _assert_rate_headers(resp)
    assert "retry-after" in resp.headers


def test_under_limit_traffic_is_unaffected(client: TestClient) -> None:
    """Below the burst the answer is exactly the pre-limiter answer plus the
    three headers — same status, same body."""
    resp = client.get("/health", headers={"x-forwarded-for": CLIENT_A + LB_TAIL})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    _assert_rate_headers(resp)
    resp = client.get("/v1/contradiction", headers={"x-forwarded-for": CLIENT_A + LB_TAIL})
    assert resp.status_code == 200
    _assert_rate_headers(resp)


def test_client_keys_are_independent(client: TestClient) -> None:
    """One exhausted client never starves another — buckets key per the
    edge-reported client address."""
    for _ in range(RATE_LIMIT_BURST + 1):
        resp = client.get("/health", headers={"x-forwarded-for": CLIENT_A + LB_TAIL})
    assert resp.status_code == 429
    other = client.get("/health", headers={"x-forwarded-for": CLIENT_B + LB_TAIL})
    assert other.status_code == 200
    _assert_rate_headers(other)


def test_client_supplied_prefix_never_dodges_the_key(client: TestClient) -> None:
    """C4 NEW-16: entries left of the trusted tail are client-claimed —
    spoofing them must not mint fresh buckets."""
    for i in range(RATE_LIMIT_BURST + 1):
        # Each request claims a DIFFERENT forged left-hand address; the
        # trusted-hop slice still reads the LB-appended client.
        forged = f"10.9.9.{i}, {CLIENT_A}{LB_TAIL}"
        resp = client.get("/health", headers={"x-forwarded-for": forged})
    assert resp.status_code == 429


def test_no_forwarded_chain_falls_back_to_the_peer(store: ReadStore) -> None:
    """Absent any forwarding header the direct peer keys the bucket —
    honest and bounded, never 'unlimited'."""
    client = _app(store, posture="enforce", hops=2)
    last = None
    for _ in range(RATE_LIMIT_BURST + 1):
        last = client.get("/health")  # TestClient peer: "testclient"
    assert last is not None and last.status_code == 429


# --- the posture gate (defined → enforced; code ships dark) ---------------- #


def test_off_posture_mounts_nothing(store: ReadStore) -> None:
    """The pre-flip posture: no limiter middleware, no rate headers — the
    shipped image changes nothing observable until the flip."""
    client = _app(store, posture="off")
    for _ in range(RATE_LIMIT_BURST + 5):
        resp = client.get("/health")
    assert resp.status_code == 200
    for name in RATE_HEADERS:
        assert name not in resp.headers


def test_advise_posture_accounts_but_never_rejects(store: ReadStore) -> None:
    """The staged "defined" half: headers + honest accounting, zero
    rejections — remaining may sit at 0 while answers keep flowing."""
    client = _app(store, posture="advise")
    headers = {"x-forwarded-for": CLIENT_A + LB_TAIL}
    for _ in range(RATE_LIMIT_BURST + 3):
        resp = client.get("/health", headers=headers)
        assert resp.status_code == 200
        _assert_rate_headers(resp)
    assert resp.headers["ratelimit-remaining"] == "0"


def test_env_drives_the_posture(store: ReadStore, monkeypatch: pytest.MonkeyPatch) -> None:
    """A deploy flips via env, not code: ``SIG_API_RATE_LIMIT`` +
    ``SIG_API_TRUSTED_PROXY_HOPS`` are read at app construction (Cloud Run
    sets env, never argv)."""
    monkeypatch.setenv("SIG_API_RATE_LIMIT", "enforce")
    monkeypatch.setenv("SIG_API_TRUSTED_PROXY_HOPS", "2")
    client = TestClient(create_app(store))
    headers = {"x-forwarded-for": CLIENT_A + LB_TAIL}
    for _ in range(RATE_LIMIT_BURST + 1):
        resp = client.get("/health", headers=headers)
    assert resp.status_code == 429

    monkeypatch.setenv("SIG_API_RATE_LIMIT", "advise")
    client = TestClient(create_app(store))
    for _ in range(RATE_LIMIT_BURST + 3):
        resp = client.get("/health", headers=headers)
        assert resp.status_code == 200


def test_unset_env_ships_dark(store: ReadStore, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIG_API_RATE_LIMIT", raising=False)
    monkeypatch.delenv("SIG_API_TRUSTED_PROXY_HOPS", raising=False)
    client = TestClient(create_app(store))
    resp = client.get("/health")
    for name in RATE_HEADERS:
        assert name not in resp.headers


def test_unknown_posture_fails_closed() -> None:
    """A posture typo must never silently un-limit the public surface —
    app construction refuses loud."""
    with pytest.raises(ValueError, match="SIG_API_RATE_LIMIT"):
        RateLimitConfig.from_env({"SIG_API_RATE_LIMIT": "enabled"})
    with pytest.raises(ValueError, match="SIG_API_TRUSTED_PROXY_HOPS"):
        RateLimitConfig.from_env({"SIG_API_TRUSTED_PROXY_HOPS": "lots"})


# --- the limiter mechanics (unit surface) ---------------------------------- #


def test_bucket_refills_over_the_window() -> None:
    """The burst drains instantly but the window refills at 30/min — a client
    that waited the documented reset is served again."""
    limiter = TokenBucketLimiter()
    for i in range(RATE_LIMIT_BURST):
        assert limiter.check("k", now=1000.0 + i * 0.001).allowed
    blocked = limiter.check("k", now=1001.0)
    assert not blocked.allowed
    assert blocked.retry_after_seconds >= 1
    # 60 s later the bucket has refilled the full 30 (capped at burst).
    assert limiter.check("k", now=1062.0).allowed


def test_bucket_never_exceeds_the_burst_cap() -> None:
    limiter = TokenBucketLimiter()
    assert limiter.check("k", now=0.0).allowed
    d = limiter.check("k", now=10_000.0)
    assert d.allowed and d.remaining == RATE_LIMIT_BURST - 1


def test_table_stays_bounded() -> None:
    """Per-client buckets are in-process state — a flood of distinct keys can
    never grow the map without bound (eviction by idle TTL then oldest)."""
    limiter = TokenBucketLimiter()
    for i in range(60_000):
        limiter.check(f"10.0.{i // 256}.{i % 256}", now=float(i))
    from api.rate_limit import _MAX_BUCKETS

    assert len(limiter._buckets) <= _MAX_BUCKETS


def test_client_key_slicing() -> None:
    """The trusted-hop slice of the chain — and only it — is the key."""
    scope = {
        "headers": [(b"x-forwarded-for", f"9.9.9.9, {CLIENT_A}, 34.117.0.1".encode())],
        "client": ("10.0.0.99", 0),
    }
    assert client_key(scope, 2) == CLIENT_A
    assert client_key(scope, 1) == "34.117.0.1"
    # Chain shorter than the declared hops → the direct peer, never a
    # client-claimed entry.
    assert client_key({"headers": [], "client": ("10.0.0.99", 0)}, 2) == "10.0.0.99"
    # RFC 7239 Forwarded is honoured the same way.
    fwd_scope = {
        "headers": [(b"forwarded", f'for="9.9.9.9", for={CLIENT_A}, for=34.117.0.1'.encode())],
        "client": ("10.0.0.99", 0),
    }
    assert client_key(fwd_scope, 2) == CLIENT_A


# --- posture isolation: the other apps are untouched ------------------------ #


def test_curation_and_intake_keep_their_own_postures(
    store: ReadStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Part VIII §0.7: the limiter wraps the public read app ONLY — the
    loopback curation app and the non-operational intake receiver never gain
    the middleware even when the env posture is armed."""
    monkeypatch.setenv("SIG_API_RATE_LIMIT", "enforce")
    from api.curation import create_curation_app
    from api.intake import create_intake_app

    cur = TestClient(create_curation_app())
    resp = cur.get("/nope")
    assert resp.status_code == 404
    for name in RATE_HEADERS:
        assert name not in resp.headers

    intake = TestClient(create_intake_app(enabled=True, operational=False))
    resp = intake.get("/intake/new")
    for name in RATE_HEADERS:
        assert name not in resp.headers
