# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""AC2 — both as-of parameters are accepted and echoed (SIG-API-005/006).

Omitting them never means an implicit "latest": the response states the resolved
world/belief instants it used and flags them as defaulted. Cacheability follows
the belief axis (SIG-API-006): belief-pinned → immutable; now-pinned → no-store.
"""

from __future__ import annotations

from starlette.testclient import TestClient

_URL = "/v1/resolution/agency:okcpd/active_device_count"


def test_omitting_both_params_echoes_explicit_defaults_not_latest(client: TestClient) -> None:
    body = client.get(_URL).json()
    asof = body["as_of"]
    # The response states exactly what it used, and flags both as defaulted —
    # there is no "latest" sentinel anywhere.
    assert asof["world_defaulted"] is True
    assert asof["belief_defaulted"] is True
    assert asof["as_of_world"] and asof["as_of_belief"]
    assert "latest" not in str(body).lower()


def test_supplied_params_are_echoed_back_verbatim(client: TestClient) -> None:
    r = client.get(
        _URL,
        params={"as_of_world": "2026-07-01", "as_of_belief": "2026-07-03T00:00:00+00:00"},
    )
    asof = r.json()["as_of"]
    assert asof["world_defaulted"] is False
    assert asof["belief_defaulted"] is False
    assert asof["as_of_world"].startswith("2026-07-01")
    assert asof["as_of_belief"].startswith("2026-07-03")
    # The same pair is echoed inside the resolution envelope too.
    env = r.json()["fact"]["envelope"]
    assert env["as_of_world"] == "2026-07-01"


def test_now_pinned_request_is_not_cacheable(client: TestClient) -> None:
    r = client.get(_URL)
    assert r.headers["cache-control"] == "no-store"
    assert r.json()["as_of"]["belief_pinned"] is False


def test_belief_pinned_request_is_immutable_and_long_cached(client: TestClient) -> None:
    r = client.get(_URL, params={"as_of_belief": "2026-07-03T00:00:00+00:00"})
    cache = r.headers["cache-control"]
    assert "immutable" in cache and "max-age=31536000" in cache
    assert r.json()["as_of"]["belief_pinned"] is True


def test_cache_keys_on_the_full_as_of_pair(client: TestClient) -> None:
    """SIG-API-006: cacheability follows the as-of pair, not just the path.

    The pair is carried in the query string (so the request URI already keys the
    cache on it), and the cache directive differs by belief: the same path yields
    an immutable directive when belief-pinned and no-store when now-pinned.
    """
    now_pinned = client.get(_URL)
    belief_pinned = client.get(_URL, params={"as_of_belief": "2026-07-03T00:00:00+00:00"})
    assert now_pinned.headers["cache-control"] != belief_pinned.headers["cache-control"]
    assert now_pinned.request.url.path == belief_pinned.request.url.path
    assert now_pinned.headers["vary"] == "Accept"


def test_every_read_family_accepts_and_echoes_as_of(client: TestClient) -> None:
    """SIG-API-005 is per-endpoint: every read family echoes the as-of block."""
    urls = [
        "/v1/resolution/agency:okcpd/active_device_count",
        "/v1/entity/agency/agency:okcpd",
        "/v1/claim/portal",
        "/v1/evidence/art:portal/cap:portal:1",
        "/v1/search?q=oklahoma",
        "/v1/dossier/jurisdiction:okc",
        "/v1/crosswalk",
        "/v1/task",
        "/v1/coverage/agency:okcpd:active_device_count",
        "/v1/contradiction",
        "/v1/changes",
        "/v1/export",
    ]
    for url in urls:
        body = client.get(url).json()
        assert "as_of" in body, f"{url} did not echo the as-of block (SIG-API-005)"
        assert body["as_of"]["as_of_world"] and body["as_of"]["as_of_belief"]


def test_only_a_defaulted_belief_is_now_pinned_and_uncacheable(client: TestClient) -> None:
    """SIG-API-006: an explicit belief is a fixed, reproducible cut → immutable;
    only a *defaulted* belief resolves fresh each request and is uncacheable."""
    from datetime import UTC, datetime

    explicit_now = client.get(_URL, params={"as_of_belief": datetime.now(tz=UTC).isoformat()})
    assert "immutable" in explicit_now.headers["cache-control"]
    assert explicit_now.json()["as_of"]["belief_pinned"] is True

    defaulted = client.get(_URL)
    assert defaulted.headers["cache-control"] == "no-store"
    assert defaulted.json()["as_of"]["belief_pinned"] is False


def test_a_malformed_as_of_parameter_is_a_400_not_a_500(client: TestClient) -> None:
    assert client.get(_URL, params={"as_of_belief": "not-a-date"}).status_code == 400
    assert client.get(_URL, params={"as_of_world": "13/25/2026"}).status_code == 400
