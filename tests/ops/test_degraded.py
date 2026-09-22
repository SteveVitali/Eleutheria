# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Degraded-but-alive mode + the keepalive workflow (SIG-GOV-021, RISK-P0-12, LD-P07).

The governance doc promises a *dormant-scheduler keepalive test*: the degraded rebuild
MUST fail loudly if it cannot rebuild. These tests hold that contract, and assert the
monthly keepalive workflow runs exactly the same command an operator would.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from ops import degraded as D

_REPO_ROOT = Path(__file__).resolve().parents[2]
_KEEPALIVE = _REPO_ROOT / ".github" / "workflows" / "keepalive.yml"


def _completed(rc: int, out: str = "", err: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["npm"], returncode=rc, stdout=out, stderr=err)


def test_successful_build_returns_the_dist_dir(tmp_path) -> None:
    web = tmp_path / "web"
    web.mkdir()

    def runner(cmd, **kw):
        # Simulate a successful `npm run build` that writes web/dist.
        dist = web / "dist"
        dist.mkdir(exist_ok=True)
        (dist / "index.html").write_text("<html></html>")
        return _completed(0)

    dist = D.build_static_site(repo_root=tmp_path, runner=runner)
    assert dist == web / "dist" and dist.exists()


def test_build_uses_the_chosen_data_source_and_no_api(tmp_path) -> None:
    web = tmp_path / "web"
    web.mkdir()
    seen_env = {}

    def runner(cmd, *, env, **kw):
        seen_env.update(env)
        (web / "dist").mkdir(exist_ok=True)
        (web / "dist" / "i.html").write_text("x")
        return _completed(0)

    D.build_static_site(repo_root=tmp_path, data_source="export", export_dir="/exp", runner=runner)
    # The static build's data source is build-time env only — never a live API.
    assert seen_env["SIG_DATA_SOURCE"] == "export"
    assert seen_env["SIG_EXPORT_DIR"] == "/exp"


def test_failed_build_fails_loudly(tmp_path) -> None:
    # RISK-P0-12: a keepalive that cannot rebuild must FAIL, not silently pass.
    (tmp_path / "web").mkdir()

    def runner(cmd, **kw):
        return _completed(1, err="astro build blew up")

    with pytest.raises(D.DegradedBuildError, match="FAILED"):
        D.build_static_site(repo_root=tmp_path, runner=runner)


def test_build_that_produces_no_dist_fails_loudly(tmp_path) -> None:
    (tmp_path / "web").mkdir()

    def runner(cmd, **kw):
        return _completed(0)  # exits 0 but writes no dist

    with pytest.raises(D.DegradedBuildError, match="no static site"):
        D.build_static_site(repo_root=tmp_path, runner=runner)


def test_missing_npm_fails_loudly(tmp_path) -> None:
    (tmp_path / "web").mkdir()

    def runner(cmd, **kw):
        raise FileNotFoundError("npm")

    with pytest.raises(D.DegradedBuildError):
        D.build_static_site(repo_root=tmp_path, runner=runner)


# --- the keepalive workflow itself -------------------------------------------


def test_keepalive_workflow_exists_and_is_monthly() -> None:
    assert _KEEPALIVE.exists()
    doc = yaml.safe_load(_KEEPALIVE.read_text())
    # PyYAML parses the bare `on:` key as the boolean True.
    triggers = doc.get("on") or doc.get(True)
    schedules = triggers["schedule"]
    assert any("1 * *" in s["cron"] for s in schedules)  # monthly (day-of-month 1)


def test_keepalive_runs_the_same_degraded_command() -> None:
    # The workflow and `sig-ops degraded` cannot drift: the job runs the CLI verbatim.
    doc = yaml.safe_load(_KEEPALIVE.read_text())
    steps = doc["jobs"]["degraded-rebuild"]["steps"]
    runs = [s.get("run", "") for s in steps]
    assert any("sig-ops degraded" in r for r in runs)
