# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.46 — the `ops/gcp/ingestion-history.sh` leg driver's offline posture."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "ops/gcp/ingestion-history.sh"


def _run(args: list[str], env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.setdefault("SIG_GCP_PROJECT", "test-project")
    env.pop("SIG_BACKFILL_AUTHOR", None)
    env.pop("SIG_BACKFILL_DSN", None)
    env.pop("SIG_OPS_GCS_BUCKET", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(SCRIPT), *args], capture_output=True, text=True, env=env, cwd=REPO
    )


def test_check_prints_plan_and_never_mutates() -> None:
    proc = _run(["--check"])
    assert proc.returncode == 0, proc.stderr
    assert "sig-ops backfill-run-reports" in proc.stdout
    assert "--role sig_materialize" in proc.stdout
    assert "--dry-run" in proc.stdout
    assert "--repo-records docs/build/reports/live_runs" in proc.stdout
    assert "prepared_not_executed" in proc.stdout
    # The writer DSN rides the env, never argv (HG-09).
    assert "SIG_STAGING_DSN=$SIG_BACKFILL_DSN" in proc.stdout


def test_check_carries_the_verbatim_rerun() -> None:
    proc = _run(["--check"])
    assert (
        "implement-spec spec=docs/tickets/389_P36.46__execution-keyed-ingestion-history.md "
        "live_verification=true" in proc.stdout
    )


def test_apply_queues_when_env_absent() -> None:
    env = dict(os.environ)
    env["SIG_GCP_PROJECT"] = "test-project"
    env["SIG_BACKFILL_AUTHOR"] = "operator-2026-11-01"
    env["SIG_BACKFILL_DSN"] = "postgresql://x@127.0.0.1:5433/sig"
    env["SIG_OPS_GCS_BUCKET"] = "sig-test-bucket"
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply"], capture_output=True, text=True, env=env, cwd=REPO
    )
    # Without the hosted env the leg refuses — queued (42) at the first
    # unmet gate, or a hard refusal where an ADC happens to exist (the
    # fake bucket/DSN then fail the real command before any write).
    assert proc.returncode != 0
    if proc.returncode == 42:
        assert "QUEUED" in proc.stdout
