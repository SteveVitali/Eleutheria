# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The real HTTP transport over a local stub — NO network (P21.3, §26, LD-F03).

Every case runs against an in-process :class:`httpx.MockTransport`, so no socket
is ever opened: the transport's retry/backoff, Retry-After honouring, Overpass
back-off semantics, conditional GET, robots retrieval and no-circumvention posture
are all asserted deterministically (SIG-INGEST-037).
"""

from __future__ import annotations

import httpx
import pytest
from connectors.net import PoliteFetcher, RobotsDisallowed
from connectors.transports import HttpxTransport, default_user_agent
from policy.crawler import CircumventionError, circumvention_techniques

_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"


def _client(handler) -> httpx.Client:  # type: ignore[no-untyped-def]
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_a_200_is_returned_with_media_type_and_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True}, headers={"Content-Type": "application/json"})

    transport = HttpxTransport(client=_client(handler))
    result = transport.request("https://x.test/d", user_agent="SIG/0 (+u)")
    assert result.status == 200
    assert result.media_type == "application/json"
    assert b"ok" in result.body
    assert result.retrieved_at is not None  # every fetch records its retrieval time


def test_429_with_retry_after_yields_exactly_one_retry_after_the_delay() -> None:
    # AC: a 429 with Retry-After: 2 yields exactly one retry after >= 2 s.
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "2"})
        return httpx.Response(200, text="ok")

    slept: list[float] = []
    transport = HttpxTransport(client=_client(handler), sleep=slept.append)
    result = transport.request("https://x.test/d", user_agent="SIG/0 (+u)")

    assert result.status == 200
    assert calls["n"] == 2, "exactly one retry (two total requests)"
    assert slept == [2.0], "backoff waited the Retry-After delay exactly once"
    assert transport.rate_limit_events == [
        {
            "url": "https://x.test/d",
            "status": 429,
            "action": "back_off",
            "wait_seconds": 2.0,
            "attempt": 1,
        }
    ]


def test_overpass_504_is_backed_off_and_retried_not_treated_as_a_challenge() -> None:
    # LD-F03 / SIG-INGEST-045h: a 504 is back-off-and-retry, not a bot challenge.
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(504)
        return httpx.Response(200, text="ok")

    slept: list[float] = []
    transport = HttpxTransport(client=_client(handler), sleep=slept.append)
    result = transport.request("https://overpass-api.de/api/interpreter", user_agent="SIG/0 (+u)")
    assert result.status == 200
    assert calls["n"] == 2 and len(slept) == 1


def test_persistent_429_is_returned_after_exhausting_retries() -> None:
    # After max_retries the 429 is returned (the fetcher then surfaces it as a
    # challenge/disappearance) — the transport never rotates identity to defeat it.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "1"})

    slept: list[float] = []
    transport = HttpxTransport(client=_client(handler), max_retries=2, sleep=slept.append)
    result = transport.request("https://x.test/d", user_agent="SIG/0 (+u)")
    assert result.status == 429
    assert len(slept) == 2, "backed off exactly max_retries times, then gave up"


def test_a_403_challenge_is_never_retried() -> None:
    # A 401/403 is a challenge, not a rate-limit: the transport returns it
    # unretried for the fetcher to surface (SIG-INGEST-013) — never defeated.
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(403)

    slept: list[float] = []
    transport = HttpxTransport(client=_client(handler), sleep=slept.append)
    result = transport.request("https://x.test/d", user_agent="SIG/0 (+u)")
    assert result.status == 403
    assert calls["n"] == 1 and slept == []


def test_conditional_get_replays_the_validators_and_serves_304_body() -> None:
    # SIG-INGEST-017: the ETag is remembered and replayed as If-None-Match; a 304
    # serves the previously-captured bytes back rather than re-downloading.
    seen_headers: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(dict(request.headers))
        if request.headers.get("if-none-match") == '"v1"':
            return httpx.Response(304)
        return httpx.Response(
            200, text="body-v1", headers={"ETag": '"v1"', "Content-Type": "text/plain"}
        )

    transport = HttpxTransport(client=_client(handler))
    first = transport.request("https://x.test/page", user_agent="SIG/0 (+u)")
    second = transport.request("https://x.test/page", user_agent="SIG/0 (+u)")
    assert first.status == 200 and first.body == b"body-v1"
    assert second.status == 304
    assert second.body == b"body-v1", "the 304 serves the cached body back"
    assert seen_headers[1].get("if-none-match") == '"v1"'


def test_robots_unretrievable_returns_none_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    transport = HttpxTransport(client=_client(handler))
    assert transport.robots("https://x.test/robots.txt").text is None


def test_robots_disallowed_path_is_never_requested() -> None:
    # AC: a robots-disallowed path is never requested. The PoliteFetcher checks
    # robots before egress, so the transport's request handler never sees it.
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private\n")
        return httpx.Response(200, text="should-not-happen")

    transport = HttpxTransport(client=_client(handler))
    fetcher = PoliteFetcher(connector_name="test", connector_version="1", transport=transport)
    with pytest.raises(RobotsDisallowed):
        fetcher.fetch("https://x.test/private/secret")
    assert "/private/secret" not in requested_paths
    assert requested_paths == ["/robots.txt"], (
        "only robots.txt was fetched, never the disallowed URL"
    )


def test_transport_refuses_a_configured_circumvention_technique() -> None:
    # Rule 4 (SIG-INGEST-037): a circumvention technique on the transport is a
    # hard error — the live path never defeats access controls.
    technique = next(iter(circumvention_techniques()))
    with pytest.raises(CircumventionError):
        HttpxTransport(circumvention_techniques=[technique])


def test_default_user_agent_carries_a_contact_url() -> None:
    ua = default_user_agent()
    assert ua.startswith("SIG/") and "+https://" in ua
