# SPDX-License-Identifier: Apache-2.0
"""P36.75 — the flock-share-lists leg script's offline posture."""

from __future__ import annotations

import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "ops" / "gcp" / "flock-share-lists.sh"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_check_prints_plan_and_never_mutates():
    out = _run("--check")
    assert out.returncode == 0
    assert "PLAN: sig-connectors flock-share-lists --snapshot" in out.stdout
    assert "--apply" in out.stdout
    assert "prepared_not_executed" in out.stdout


def test_check_carries_the_verbatim_rerun():
    out = _run("--check")
    rerun = (
        "implement-spec spec=docs/tickets/"
        "385_P36.75__flock-share-lists-configured-access.md"
        " live_verification=true"
    )
    assert rerun in out.stdout


def test_apply_queues_when_env_absent(monkeypatch):
    import os

    env = {k: v for k, v in os.environ.items() if not k.startswith("SIG_SHARE")}
    env["SIG_GCP_MODE"] = "apply"
    env["SIG_GCP_PROJECT"] = "test-proj"
    out = subprocess.run(
        ["bash", str(SCRIPT), "--apply"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert out.returncode in (42, 3)
