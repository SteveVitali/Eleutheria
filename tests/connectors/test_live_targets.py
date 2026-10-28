# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Live fetch targets (P24.1 live deploy / DEPLOY.1, ADR-082).

The live runner must drive connectors from the declarative ``live_targets.toml``
rows — not a placeholder URL — and must refuse a green source that has no configured
target rather than fetch a bogus one. These tests are network-free.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from connectors.live_targets import DEFAULT_OVERPASS_ENDPOINT, NoLiveTargets, live_targets
from connectors.runner import RunMode, run_source


def test_osm_overpass_has_a_configured_live_target() -> None:
    """The OKC OSM/Overpass live target row exists (guards the config)."""
    targets = live_targets("osm_overpass")
    overpass = [t for t in targets if t["kind"] == "overpass"]
    assert len(overpass) == 1
    assert overpass[0]["id"] == "osm_overpass:overpass"


def test_overpass_target_builds_the_interpreter_url_with_the_okc_query() -> None:
    target = next(t for t in live_targets("osm_overpass") if t["kind"] == "overpass")
    parsed = urlparse(target["url"])
    assert parsed.path.endswith("/interpreter")
    query = parse_qs(parsed.query)["data"][0]
    # the widened P37.1 selection + the OKC metro bbox + body output are present
    assert 'man_made"="surveillance"' in query.replace("[", "").replace("]", "")
    assert 'surveillance:type"' in query
    assert 'highway"="speed_camera"' in query
    assert "35.3,-97.85,35.75,-97.15" in query
    # P37.1 / SIG-INGEST-045e: `out body center qt` — never `out meta`; user/uid
    # are never requested (the capture-side half of F-406).
    assert "out body center qt" in query
    assert "out meta" not in query


def test_overpass_tile_discovery_targets_are_declared() -> None:
    """P37.1 / ACQ-17: the national/global two-pass collection's count targets."""
    counts = [t for t in live_targets("osm_overpass") if t["kind"] == "overpass_tile_count"]
    assert counts, "the tile_discovery flag must emit `out count;` census targets"
    tile_ids = [tile for t in counts for tile in t["tile_ids"]]
    # The declared areas: 51 US-state/DC areas first, then every ISO country.
    assert tile_ids[:2] == ["US-AL", "US-AK"]
    assert "US-DC" in tile_ids and "AU" in tile_ids
    for t in counts:
        parsed = urlparse(t["url"])
        assert parsed.path.endswith("/interpreter")
        query = parse_qs(parsed.query)["data"][0]
        assert "out count;" in query
        # The reviewed ~30s pacing rides the target metadata (rate_limit_per_min=2).
        assert t["rate_limit_per_min"] == 2


def test_overpass_endpoint_is_env_overridable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIG_OVERPASS_ENDPOINT", "https://overpass.example.test/api/interpreter")
    url = live_targets("osm_overpass")[0]["url"]
    assert url.startswith("https://overpass.example.test/api/interpreter?")
    monkeypatch.delenv("SIG_OVERPASS_ENDPOINT", raising=False)
    assert live_targets("osm_overpass")[0]["url"].startswith(DEFAULT_OVERPASS_ENDPOINT)


def test_osm_element_history_has_configured_targets() -> None:
    """The OSM history live rows exist and point at the documented API 0.6 endpoint."""
    targets = live_targets("osm_element_history")
    assert targets, "osm_element_history is flipped — it must have live targets"
    for t in targets:
        assert t["kind"] == "history"
        assert t["url"].startswith("https://api.openstreetmap.org/api/0.6/")
        assert t["url"].endswith("/history.json")


def test_eff_atlas_has_a_configured_live_target() -> None:
    """The Atlas bulk-CSV live row exists and uses the www. host (apex 301s)."""
    targets = live_targets("eff_atlas_of_surveillance")
    assert len(targets) == 1
    assert targets[0]["kind"] == "bulk_csv"
    assert targets[0]["url"] == "https://www.atlasofsurveillance.org/download.csv"


def test_unknown_source_has_no_live_targets() -> None:
    assert live_targets("no_such_source_xyz") == []


def test_live_run_refuses_a_green_source_with_no_target(monkeypatch: pytest.MonkeyPatch) -> None:
    """A green source with no configured target raises NoLiveTargets before any fetch."""
    # osm_overpass is green (flipped in RIGHTS.1); force "no targets" and assert the
    # runner refuses without constructing a transport / opening a socket.
    monkeypatch.setattr("connectors.live_targets.live_targets", lambda _sid: [])
    with pytest.raises(NoLiveTargets):
        run_source("osm_overpass", mode=RunMode.LIVE, sink_kind="memory")
