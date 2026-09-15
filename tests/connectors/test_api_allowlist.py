# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ADR-083 API-vs-crawl carve-out allow-list.

robots.txt governs crawling; a host on the allow-list is API mode (documented,
ToS-governed, rate-limited). A host off the list — or a path outside its endpoint
prefix — stays CRAWL and robots binds (no blanket bypass, SIG-INGEST-037).
"""

from __future__ import annotations

import pytest
from connectors.api_allowlist import api_allow_reason
from connectors.net import PoliteFetcher, RobotsDisallowed


def test_allow_listed_api_endpoint_returns_a_tos_basis() -> None:
    reason = api_allow_reason("https://overpass-api.de/api/interpreter?data=...")
    assert reason and "Overpass" in reason


def test_non_allow_listed_host_is_not_api_mode() -> None:
    assert api_allow_reason("https://example.test/api/x") is None


def test_allow_listed_host_but_path_outside_prefix_is_not_api_mode() -> None:
    # overpass-api.de is allow-listed only for /api/interpreter, not its web pages.
    assert api_allow_reason("https://overpass-api.de/index.html") is None


def test_api_mode_bypasses_robots_for_the_allow_listed_endpoint(  # type: ignore[no-untyped-def]
    transport_factory, json_response
) -> None:
    """An allow-listed API URL fetches even when robots.txt would disallow it."""
    url = "https://overpass-api.de/api/interpreter?data=x"
    transport = transport_factory(
        {url: json_response(url, {"elements": []})},
        robots_text="User-agent: *\nDisallow: /api\n",  # would block CRAWL mode
    )
    fetcher = PoliteFetcher(connector_name="osm", connector_version="1", transport=transport)
    result = fetcher.fetch(url)  # must NOT raise RobotsDisallowed (API mode)
    assert result.status == 200
    assert fetcher.conduct_decisions[-1]["mode"] == "api"


def test_off_allow_list_host_still_honours_robots(transport_factory, json_response) -> None:  # type: ignore[no-untyped-def]
    url = "https://portal.example/api/x"
    transport = transport_factory(
        {url: json_response(url, {})},
        robots_text="User-agent: *\nDisallow: /api\n",
    )
    fetcher = PoliteFetcher(connector_name="toy", connector_version="1", transport=transport)
    with pytest.raises(RobotsDisallowed):
        fetcher.fetch(url)
    assert fetcher.conduct_decisions[-1]["mode"] == "crawl"
