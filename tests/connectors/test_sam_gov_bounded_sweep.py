# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P26.19 (SOURCES.18) — the bounded, quota-aware SAM.gov sweep.

The P26.14 widened sweep over-issued requests against api.data.gov's daily
quota: 429 back-off retries re-burnt the fresh window and the sweep kept issuing
counted requests past the wall until SIGKILL. These deterministic tests pin the
fix (ADR-089):

* a per-run request budget bounds one run and stops it cleanly WITH HEADROOM
  before the wall (``budget_reached``);
* the first 429 stops the sweep and the remaining slices are deferred, never
  re-probed (``quota_reached`` — the recorded rate-limit lesson);
* the SAM.gov live transport never RETRIES a 429 (no re-probe at the transport
  layer either);
* the paged cursor covers the whole prioritised keyword space and pages it when
  the budget is below the keyword count;
* the credential rides the ``X-Api-Key`` header, never the recorded URL.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from typing import Any

import httpx
from connectors.net import PoliteFetcher, RateLimiter, RobotsResult
from connectors.procurement import (
    ProcurementConnector,
    sam_gov_daily_request_budget,
    sam_gov_search_targets,
    sam_gov_sweep_config,
    sam_gov_sweep_plan,
)
from connectors.registry import get
from connectors.stages import FetchResult, InMemoryCaptureStore, InMemoryClaimSink, RunContext
from connectors.transports import HttpxTransport
from evidence.ingest_run import IngestRun

from connectors import pipeline

_SAM_GOV_SEARCH = "https://api.sam.gov/prod/opportunities/v2/search"


def _ctx(*, fetcher: Any = None, **parameters: Any) -> RunContext:
    source = dataclasses.replace(get("sam_gov"), ingestion_permitted=True)
    return RunContext(
        source=source,
        run=IngestRun("procurement", "1.0.0", "deadbeef", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters=parameters,
    )


class _FixedTransport:
    """A transport returning one fixed status for every request; logs each URL."""

    def __init__(self, status: int, body: bytes = b'{"opportunitiesData": []}') -> None:
        self.status = status
        self.body = body
        self.request_log: list[str] = []

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text="User-agent: *\nAllow: /\n")

    def request(
        self,
        url: str,
        *,
        user_agent: str,
        headers: Mapping[str, str] | None = None,
        body: bytes | None = None,
    ) -> FetchResult:
        self.request_log.append(url)
        return FetchResult(
            url=url, status=self.status, body=self.body, media_type="application/json"
        )


def _fetcher(transport: _FixedTransport) -> PoliteFetcher:
    # A no-op sleep keeps the per-host politeness pacing deterministic + instant.
    return PoliteFetcher(
        connector_name="procurement",
        connector_version="1.0.0",
        transport=transport,
        rate_limiter=RateLimiter(sleep=lambda _s: None),
    )


# --- the paged planner (pure) -------------------------------------------------


def test_sweep_plan_covers_whole_space_in_one_run_when_budget_ge_count() -> None:
    kws = ["a", "b", "c", "d"]
    selected, next_cursor = sam_gov_sweep_plan(kws, budget=30, cursor=0)
    assert selected == kws  # full coverage, one run
    assert next_cursor == 0  # nothing left to page — the cursor is inert


def test_sweep_plan_pages_across_windows_when_budget_below_count() -> None:
    kws = ["a", "b", "c", "d", "e"]
    day1, c1 = sam_gov_sweep_plan(kws, budget=2, cursor=0)
    day2, c2 = sam_gov_sweep_plan(kws, budget=2, cursor=c1)
    day3, c3 = sam_gov_sweep_plan(kws, budget=2, cursor=c2)
    assert day1 == ["a", "b"] and c1 == 2
    assert day2 == ["c", "d"] and c2 == 4
    assert day3 == ["e", "a"] and c3 == 1  # wraps — full space covered over days
    # Every keyword is reached within the first ceil(5/2)=3 windows.
    assert set(day1) | set(day2) | set(day3) == set(kws)


def test_sweep_plan_empty_keywords_is_safe() -> None:
    assert sam_gov_sweep_plan([], budget=5, cursor=3) == ([], 0)


def test_configured_budget_is_present_and_ge_keyword_count() -> None:
    budget = sam_gov_daily_request_budget()
    assert budget is not None and budget >= 1
    keywords = list(sam_gov_sweep_config().get("keywords", ()))
    # The shipped budget covers the whole keyword space in one fresh-window run
    # (so D-FEDERAL.1-1 closes with no by-design multi-day tail).
    assert budget >= len(keywords)


# --- generated targets carry the quota flag + no key in the URL ---------------


def test_search_targets_are_quota_governed_and_credential_free() -> None:
    targets = sam_gov_search_targets()
    assert targets
    for t in targets:
        assert t["quota_governed"] is True
        assert t["url"].startswith(_SAM_GOV_SEARCH + "?")
        assert "api_key" not in t["url"] and "X-Api-Key" not in t["url"]


def test_search_targets_cursor_rotates_the_prioritised_order() -> None:
    base = [t["index_keyword"] for t in sam_gov_search_targets(cursor=0)]
    rotated = [t["index_keyword"] for t in sam_gov_search_targets(cursor=1)]
    # At the shipped budget (>= keyword count) both cover the whole space; the
    # cursor only rotates the ORDER, so the sets match and the rotation shows.
    assert set(base) == set(rotated)
    assert rotated[0] == base[1]


def test_discover_marks_supplied_and_generated_slices_quota_governed() -> None:
    supplied = {
        "id": "s1",
        "url": _SAM_GOV_SEARCH + "?limit=25&postedFrom=01/01/2026&postedTo=12/31/2026&title=alpr",
        "kind": "opportunity_search",
    }
    ctx = _ctx(targets=[supplied])
    discovered = ProcurementConnector().discover(ctx)
    opp = [t for t in discovered if t.get("kind") == "opportunity_search"]
    assert opp and all(t.get("quota_governed") for t in opp)
    # The supplied `alpr` search suppresses the generated alpr slice (no double-fetch).
    assert [t for t in discovered if t.get("index_keyword") == "alpr"] == []


# --- the driver stops cleanly before the wall (budget) ------------------------


def test_budget_bounds_one_run_and_defers_the_rest_with_headroom() -> None:
    transport = _FixedTransport(200)
    ctx = _ctx(fetcher=_fetcher(transport), targets=[], request_budget=3)
    report = pipeline.run(ProcurementConnector(), ctx)
    # Exactly the budget was ISSUED — the run stopped with headroom, never
    # approaching the daily wall.
    assert len(transport.request_log) == 3
    assert report.sweep_requests == 3
    assert report.budget_reached is True
    assert report.quota_reached is False
    # The remaining slices are recorded as deferred, not lost.
    assert report.sweep_skipped
    assert all(s["reason"] == "budget_reached" for s in report.sweep_skipped)


# --- the driver stops on the first 429 and NEVER re-probes (quota) ------------


def test_first_429_stops_the_sweep_and_defers_the_rest_never_reprobing() -> None:
    transport = _FixedTransport(429)
    ctx = _ctx(fetcher=_fetcher(transport), targets=[], request_budget=30)
    report = pipeline.run(ProcurementConnector(), ctx)
    # RATE-LIMIT HONESTY: exactly ONE request was issued — the window is
    # exhausted, so the remaining slices are deferred, never re-probed.
    assert len(transport.request_log) == 1
    assert report.sweep_requests == 1
    assert report.quota_reached is True
    assert report.budget_reached is False
    # The 429 is recorded honestly as a disappearance, not a swallowed crash.
    assert report.disappearances
    assert report.sweep_skipped
    assert all(s["reason"] == "quota_reached" for s in report.sweep_skipped)
    # A run must never burn the window into a FAILURE: the report is a clean stop.
    assert report.asserted is True


def test_non_429_challenge_does_not_trip_the_quota_stop() -> None:
    # A 403 auth challenge is NOT a daily-quota wall — the driver classifies it
    # by status and does not set quota_reached (it records disappearances and
    # continues to issue the budgeted slices).
    transport = _FixedTransport(403)
    ctx = _ctx(fetcher=_fetcher(transport), targets=[], request_budget=30)
    report = pipeline.run(ProcurementConnector(), ctx)
    assert report.quota_reached is False
    assert report.sweep_requests == len(transport.request_log)
    assert report.sweep_requests > 1  # not stopped after the first slice


# --- the SAM.gov live transport never RETRIES a 429 (no re-probe) -------------


def _mock_client(handler: Any) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_transport_max_retries_zero_issues_one_request_on_429() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(429, json={})

    transport = HttpxTransport(client=_mock_client(handler), max_retries=0, sleep=lambda _s: None)
    result = transport.request(_SAM_GOV_SEARCH + "?title=x", user_agent="SIG/test")
    assert result.status == 429
    # The whole point (ADR-089): a 429 is surfaced immediately, never retried —
    # a retry against a daily-request quota is a re-probe that re-burns it.
    assert len(calls) == 1
    assert transport.rate_limit_events == []


def test_transport_default_retries_would_reprobe_contrast() -> None:
    # The contrast that motivates the fix: with the default retry policy a 429
    # is re-probed max_retries times (each a counted request against the quota).
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(429, json={})

    transport = HttpxTransport(client=_mock_client(handler), max_retries=3, sleep=lambda _s: None)
    transport.request(_SAM_GOV_SEARCH + "?title=x", user_agent="SIG/test")
    assert len(calls) == 4  # 1 + 3 re-probes — exactly what SAM.gov must NOT do
