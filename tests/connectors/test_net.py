# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The shared rate-limiter + robots layer (SIG-INGEST-011/012/013)."""

from __future__ import annotations

import pytest
from connectors.net import (
    DEFAULT_CONTACT_URL,
    ChallengeEncountered,
    PoliteFetcher,
    RateLimiter,
    RobotsDisallowed,
    RobotsUnretrievable,
    user_agent,
)
from policy.crawler import CircumventionError


def test_user_agent_carries_a_contact_url() -> None:
    # SIG-INGEST-011 / Rule 1: a documented UA carrying a contact URL.
    ua = user_agent("toy", "1")
    assert ua.startswith("toy/1")
    assert DEFAULT_CONTACT_URL in ua


def test_unretrievable_robots_refuses_to_run(transport_factory) -> None:  # type: ignore[no-untyped-def]
    # SIG-INGEST-012: robots.txt unretrievable => permission NOT granted => refuse.
    transport = transport_factory({}, robots_text=None)
    fetcher = PoliteFetcher(connector_name="toy", connector_version="1", transport=transport)
    with pytest.raises(RobotsUnretrievable):
        fetcher.fetch("https://portal.example/api")


def test_robots_disallow_is_honored(transport_factory, json_response) -> None:  # type: ignore[no-untyped-def]
    transport = transport_factory(
        {"https://portal.example/secret": json_response("https://portal.example/secret", {})},
        robots_text="User-agent: *\nDisallow: /secret\n",
    )
    fetcher = PoliteFetcher(connector_name="toy", connector_version="1", transport=transport)
    with pytest.raises(RobotsDisallowed):
        fetcher.fetch("https://portal.example/secret")


def test_a_permitted_fetch_returns_the_bytes(transport_factory, json_response) -> None:  # type: ignore[no-untyped-def]
    url = "https://portal.example/api"
    transport = transport_factory({url: json_response(url, {"id": "p1", "cameras": 3})})
    fetcher = PoliteFetcher(connector_name="toy", connector_version="1", transport=transport)
    result = fetcher.fetch(url)
    assert result.status == 200
    assert b'"cameras"' in result.body
    assert transport.robots_log  # robots was retrieved before the first fetch


def test_bot_challenge_is_surfaced_never_defeated(transport_factory, json_response) -> None:  # type: ignore[no-untyped-def]
    # SIG-INGEST-013: SIG does not defeat challenges; a 403 is surfaced, not retried.
    url = "https://portal.example/api"
    transport = transport_factory({url: json_response(url, {}, status=403)})
    fetcher = PoliteFetcher(connector_name="toy", connector_version="1", transport=transport)
    with pytest.raises(ChallengeEncountered):
        fetcher.fetch(url)


def test_circumvention_technique_is_rejected_at_construction(transport_factory) -> None:  # type: ignore[no-untyped-def]
    # SIG-INGEST-013 / Rule 4: a challenge-defeating configuration is a hard error.
    transport = transport_factory({})
    with pytest.raises(CircumventionError):
        PoliteFetcher(
            connector_name="toy",
            connector_version="1",
            transport=transport,
            circumvention_techniques=["challenge_solving"],
        )


def test_rate_limiter_enforces_a_per_host_minimum_interval() -> None:
    # SIG-INGEST-011 / Rule 3: per-host budget with a minimum interval.
    clock = {"t": 0.0}
    slept: list[float] = []

    def now() -> float:
        return clock["t"]

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        clock["t"] += seconds

    limiter = RateLimiter(default_delay=2.0, now=now, sleep=sleep)
    assert limiter.acquire("h") == 0.0  # first request: no wait
    assert limiter.acquire("h") == pytest.approx(2.0)  # immediate re-request waits the delay
    assert slept == [pytest.approx(2.0)]


def test_robots_crawl_delay_pins_the_host_budget(transport_factory, json_response) -> None:  # type: ignore[no-untyped-def]
    url = "https://portal.example/api"
    transport = transport_factory(
        {url: json_response(url, {"id": "p1", "cameras": 1})},
        robots_text="User-agent: *\nAllow: /\nCrawl-delay: 5\n",
    )
    clock = {"t": 100.0}
    limiter = RateLimiter(now=lambda: clock["t"], sleep=lambda s: None)
    fetcher = PoliteFetcher(
        connector_name="toy",
        connector_version="1",
        transport=transport,
        rate_limiter=limiter,
    )
    fetcher.fetch(url)
    assert limiter.delay_for("portal.example") == pytest.approx(5.0)
