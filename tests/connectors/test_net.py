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
    user_agent,
)
from policy.crawler import CircumventionError


def test_user_agent_carries_a_contact_url() -> None:
    # SIG-INGEST-011 / Rule 1: a documented UA carrying a contact URL.
    ua = user_agent("toy", "1")
    assert ua.startswith("toy/1")
    assert DEFAULT_CONTACT_URL in ua


def test_unretrievable_robots_is_recorded_and_fetched(transport_factory, json_response) -> None:  # type: ignore[no-untyped-def]
    # GL-GATE-08 / ADR-088: robots.txt unretrievable => the RFC-assumed disallow
    # is RECORDED (outcome "unretrievable") but never enforced — the fetch
    # proceeds and is marked robots_disregarded so provenance stays honest.
    url = "https://portal.example/api"
    transport = transport_factory({url: json_response(url, {"ok": True})}, robots_text=None)
    fetcher = PoliteFetcher(connector_name="toy", connector_version="1", transport=transport)
    result = fetcher.fetch(url)
    assert result.status == 200
    outcome = fetcher.robots_outcomes["portal.example"]
    assert outcome["outcome"] == "unretrievable"
    assert fetcher.robots_disregarded == [
        {"url": url, "host": "portal.example", "verdict": "unretrievable"}
    ]
    assert fetcher.conduct_decisions[-1]["outcome"] == "robots_disregarded"
    assert not fetcher.can_fetch(url)  # the recorded verdict is still "no"


def test_4xx_robots_means_no_policy_permits_the_fetch(transport_factory, json_response) -> None:  # type: ignore[no-untyped-def]
    # ADR-087 / RFC 9309 §2.3.1.4: a 404 robots answer = "no policy exists" →
    # unrestricted — the fetch proceeds. This is the *.api.civicclerk.com case
    # (P26.3): the tenant API answers robots.txt with 404, which under the old
    # reading was refused as "unretrievable".
    url = "https://tenant.api.example/v1/Events"
    transport = transport_factory(
        {url: json_response(url, {"id": "e1", "cameras": 0})},
        robots_text=None,
        robots_status=404,
    )
    fetcher = PoliteFetcher(connector_name="toy", connector_version="1", transport=transport)
    result = fetcher.fetch(url)
    assert result.status == 200
    # The decision is auditable per host (ADR-087).
    outcome = fetcher.robots_outcomes["tenant.api.example"]
    assert outcome["outcome"] == "no_policy_4xx"
    assert outcome["status"] == 404


@pytest.mark.parametrize("status", [429, 500, 503])
def test_5xx_and_429_robots_are_unavailable_recorded_not_refused(  # type: ignore[no-untyped-def]
    transport_factory, json_response, status: int
) -> None:
    # 429/5xx robots answers are "unavailable", not "no policy" (the RFC
    # reserves the permit for 4xx) — recorded as such; under GL-GATE-08 /
    # ADR-088 the fetch still proceeds and is marked robots_disregarded.
    url = "https://portal.example/api"
    transport = transport_factory(
        {url: json_response(url, {"ok": True})}, robots_text=None, robots_status=status
    )
    fetcher = PoliteFetcher(connector_name="toy", connector_version="1", transport=transport)
    result = fetcher.fetch(url)
    assert result.status == 200
    outcome = fetcher.robots_outcomes["portal.example"]
    assert outcome["outcome"] == "unretrievable"
    assert outcome["status"] == status
    assert fetcher.robots_disregarded == [
        {"url": url, "host": "portal.example", "verdict": "unretrievable"}
    ]


def test_robots_disallow_is_recorded_and_disregarded(transport_factory, json_response) -> None:  # type: ignore[no-untyped-def]
    # GL-GATE-08 / ADR-088: a retrieved `Disallow` verdict no longer refuses —
    # the URL is fetched and the record marks the ignored refusal.
    url = "https://portal.example/secret"
    transport = transport_factory(
        {url: json_response(url, {})},
        robots_text="User-agent: *\nDisallow: /secret\n",
    )
    fetcher = PoliteFetcher(connector_name="toy", connector_version="1", transport=transport)
    result = fetcher.fetch(url)
    assert result.status == 200
    assert fetcher.robots_outcomes["portal.example"]["outcome"] == "retrieved"
    assert fetcher.robots_disregarded == [
        {"url": url, "host": "portal.example", "verdict": "disallowed"}
    ]
    decision = fetcher.conduct_decisions[-1]
    assert decision["robots_verdict"] == "disallowed"
    assert decision["outcome"] == "robots_disregarded"
    assert not fetcher.can_fetch(url)  # verdict semantics preserved


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


def test_pinned_api_budget_survives_a_shorter_robots_delay(
    transport_factory, json_response
) -> None:  # type: ignore[no-untyped-def]
    """P26.11: a reviewed rate_limit_per_min pin ratchets UP only — robots can
    demand slower, never lower the declared API budget."""
    url = "https://api.example/bills"
    transport = transport_factory(
        {url: json_response(url, {"results": []})},
        robots_text="User-agent: *\nAllow: /\nCrawl-delay: 1\n",
    )
    clock = {"t": 100.0}
    limiter = RateLimiter(now=lambda: clock["t"], sleep=lambda s: None)
    fetcher = PoliteFetcher(
        connector_name="toy",
        connector_version="1",
        transport=transport,
        rate_limiter=limiter,
    )
    fetcher.set_host_delay("api.example", 12.0)  # the reviewed 5/min budget
    fetcher.fetch(url)
    assert limiter.delay_for("api.example") == pytest.approx(12.0)


def test_a_slower_robots_delay_still_demands_slower(transport_factory, json_response) -> None:  # type: ignore[no-untyped-def]
    url = "https://api.example/bills"
    transport = transport_factory(
        {url: json_response(url, {"results": []})},
        robots_text="User-agent: *\nAllow: /\nCrawl-delay: 30\n",
    )
    clock = {"t": 100.0}
    limiter = RateLimiter(now=lambda: clock["t"], sleep=lambda s: None)
    fetcher = PoliteFetcher(
        connector_name="toy",
        connector_version="1",
        transport=transport,
        rate_limiter=limiter,
    )
    fetcher.set_host_delay("api.example", 12.0)
    fetcher.fetch(url)
    assert limiter.delay_for("api.example") == pytest.approx(30.0)
