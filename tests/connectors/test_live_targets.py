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
    assert len(targets) == 1
    assert targets[0]["kind"] == "overpass"


def test_overpass_target_builds_the_interpreter_url_with_the_okc_query() -> None:
    target = live_targets("osm_overpass")[0]
    parsed = urlparse(target["url"])
    assert parsed.path.endswith("/interpreter")
    query = parse_qs(parsed.query)["data"][0]
    # the surveillance selector + the OKC metro bbox + metadata output are present
    assert 'man_made"="surveillance"' in query.replace("[", "").replace("]", "")
    assert "35.30,-97.85,35.75,-97.15" in query
    assert "out meta center" in query


def test_overpass_endpoint_is_env_overridable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIG_OVERPASS_ENDPOINT", "https://overpass.example.test/api/interpreter")
    url = live_targets("osm_overpass")[0]["url"]
    assert url.startswith("https://overpass.example.test/api/interpreter?")
    monkeypatch.delenv("SIG_OVERPASS_ENDPOINT", raising=False)
    assert live_targets("osm_overpass")[0]["url"].startswith(DEFAULT_OVERPASS_ENDPOINT)


def test_unknown_source_has_no_live_targets() -> None:
    assert live_targets("no_such_source_xyz") == []


def test_live_run_refuses_a_green_source_with_no_target(monkeypatch: pytest.MonkeyPatch) -> None:
    """A green source with no configured target raises NoLiveTargets before any fetch."""
    # osm_overpass is green (flipped in RIGHTS.1); force "no targets" and assert the
    # runner refuses without constructing a transport / opening a socket.
    monkeypatch.setattr("connectors.live_targets.live_targets", lambda _sid: [])
    with pytest.raises(NoLiveTargets):
        run_source("osm_overpass", mode=RunMode.LIVE, sink_kind="memory")
