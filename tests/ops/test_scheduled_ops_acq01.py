# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.6 / ACQ-01 — first-run-safe scheduling machinery (I8 R6, NEW-4).

* ``scheduled-ops.sh --paused``: every trigger a run *creates* is created
  then immediately paused — a new source's first execution is a manually
  observed `gcloud scheduler jobs run`, never an unobserved cron fire.
  ``--paused`` never *pauses* a live trigger — an existing trigger's state is
  untouched.
* per-row ``task_timeout``: a ``[[sources]]``/``[[batches]]`` row may carry a
  reviewed duration (legistar's widened keyword pass, the Round-11 6h
  batches); rows without one keep the 60m/36h defaults.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "ops/gcp/scheduled-ops.sh"


def _env() -> dict[str, str]:
    """No-ADC env — same contract as test_gcp_iac's ``_no_adc_env``."""
    import os

    env = {k: v for k, v in os.environ.items() if k != "SIG_GCP_PROJECT"}
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    env["CLOUDSDK_CONFIG"] = "/nonexistent-sig-adc"
    return env


def _plan(*extra: str) -> str:
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--check", *extra],
        capture_output=True,
        text=True,
        check=False,
        env=_env(),
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    return proc.stdout


def test_paused_marks_every_new_trigger_paused() -> None:
    """--check surfaces the R6 contract: every create plan carries the annotation."""
    out = _plan("--paused")
    assert "R6 create-paused" in out
    creates = [ln for ln in out.splitlines() if "scheduler jobs create" in ln]
    assert creates
    assert all("NEW triggers paused on create (R6)" in ln for ln in creates)


def test_unpaused_run_plans_no_ingest_pause() -> None:
    """Without --paused, only declared-paused maintenance rows plan a pause —
    no ingest/batch trigger is ever held, and no create plan carries the R6
    annotation."""
    out = _plan()
    assert "R6 create-paused" not in out
    creates = [ln for ln in out.splitlines() if "scheduler jobs create" in ln]
    assert not any("NEW triggers paused on create" in ln for ln in creates)
    pause_lines = [ln for ln in out.splitlines() if "scheduler jobs pause" in ln]
    ingest_pauses = [ln for ln in pause_lines if "sig-sched-r11-" in ln or "sig-sched-camreg" in ln]
    assert not ingest_pauses, ingest_pauses


def test_legistar_row_carries_its_reviewed_timeout() -> None:
    out = _plan()
    legistar = [
        ln for ln in out.splitlines() if "sig-ingest-legistar" in ln and "jobs deploy" in ln
    ]
    assert legistar and all("--task-timeout 3h" in ln for ln in legistar)


def test_default_timeouts_still_apply() -> None:
    out = _plan()
    batch_lines = [ln for ln in out.splitlines() if "--batch" in ln and "jobs deploy" in ln]
    assert batch_lines
    # every batch deploy carries an explicit bound — the script substitutes
    # 36h for rows with no declared task_timeout (the camreg monthly rows);
    # rows that carry a reviewed bound (the R11 6h batches) keep it instead.
    assert all(re.search(r"--task-timeout \S+", ln) for ln in batch_lines)
    assert any("--task-timeout 36h" in ln for ln in batch_lines)
    assert any("--task-timeout 6h" in ln for ln in batch_lines)
    assert "--max-retries 0" in out


def test_cadence_model_carries_task_timeout() -> None:
    from ops.scheduled import load_cadence

    config = load_cadence(REPO_ROOT / "ops/cadence.toml")
    by_id = {s.source: s for s in config.sources}
    assert by_id["legistar"].task_timeout == "3h"
    # rows without the field keep the empty (default) value — the script
    # substitutes 60m/36h at deploy time
    assert any(not s.task_timeout for s in config.sources)


def test_unscheduled_live_sources_guard_unchanged() -> None:
    """R6 drift guard: the canonical schedule check still parses the file."""
    from ops.scheduled import load_cadence, unscheduled_live_sources

    config = load_cadence(REPO_ROOT / "ops/cadence.toml")
    assert unscheduled_live_sources(config) == []
