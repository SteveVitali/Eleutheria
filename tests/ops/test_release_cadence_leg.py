# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.44 — the `ops/gcp/release-cadence.sh` leg driver's offline posture."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "ops/gcp/release-cadence.sh"


def _run(args: list[str], env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.setdefault("SIG_GCP_PROJECT", "test-project")
    env.pop("SIG_CADENCE_AUTHOR", None)
    env.pop("SIG_SCHEDULER_SA_EMAIL", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(SCRIPT), *args], capture_output=True, text=True, env=env, cwd=REPO
    )


def test_check_prints_plan_and_never_mutates() -> None:
    proc = _run(["--check"])
    assert proc.returncode == 0, proc.stderr
    assert "gcloud scheduler jobs create http sig-sched-release-cut" in proc.stdout
    assert "gcloud scheduler jobs create http sig-sched-materialize" in proc.stdout
    assert "0 14 15-17 * *" in proc.stdout  # the three candidate cut days
    assert "0 8 * * 0" in proc.stdout  # the weekly materialize — G1 §3.6 verbatim
    assert "prepared_not_executed" in proc.stdout


def test_check_carries_the_verbatim_rerun() -> None:
    proc = _run(["--check"])
    assert (
        "implement-spec spec=docs/tickets/387_P36.44__release-cadence-automation.md "
        "live_verification=true" in proc.stdout
    )


def test_apply_queues_when_env_absent() -> None:
    env = dict(os.environ)
    env["SIG_GCP_PROJECT"] = "test-project"
    env["SIG_CADENCE_AUTHOR"] = "operator-2026-11-01"
    env["SIG_SCHEDULER_SA_EMAIL"] = "sig-sched@test.iam.gserviceaccount.com"
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply"], capture_output=True, text=True, env=env, cwd=REPO
    )
    # No ADC / hosted env → the leg queues (42) at the first unmet gate —
    # window, ADC or env — never a partial create.
    assert proc.returncode in (42, 2, 3)
    if proc.returncode == 42:
        assert "QUEUED" in proc.stdout
