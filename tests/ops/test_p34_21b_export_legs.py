# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.21b leg L2 — the re-export's append-only prefix invariant.

``ops/gcp/export.sh run`` writes a NEW ``exports/national/<as-of>/`` prefix
under sig-restricted (the as-of stamp names the snapshot; colons are stripped
for object-name safety) — a republish never overwrites or deletes a prior
export prefix (SIG-OPS-004 / ADR-132 immutability). These tests pin the
invariant statically + through the dry-run plan: no delete verb, no
``--delete-unmatched-destination-objects`` on any sync, and the fetch sync's
direction is bucket → local.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "ops" / "gcp" / "export.sh"


def _env(**overrides: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k != "SIG_GCP_PROJECT"}
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    env["CLOUDSDK_CONFIG"] = "/nonexistent-sig-adc"
    env.update(overrides)
    return env


def _code_lines() -> str:
    return "\n".join(
        line for line in SCRIPT.read_text().splitlines() if not line.lstrip().startswith("#")
    )


def test_no_delete_path_in_the_export_script() -> None:
    code = _code_lines()
    for forbidden in (
        "delete-unmatched-destination-objects",
        "objects delete",
        "storage rm",
        "storage mv",
        "buckets delete",
        "rsync --delete",
    ):
        assert forbidden not in code, f"export.sh carries a delete path: {forbidden}"


def test_run_writes_a_fresh_as_of_prefix() -> None:
    env = _env(
        SIG_GCP_PROJECT="example-proj",
        SIG_EXPORT_AS_OF="2026-10-05T12:34:56Z",  # future-ok: synthetic: leg fixture
    )
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--check", "run"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    # the output prefix names the as-of stamp (colons stripped) under national/
    assert (
        "exports/national/2026-10-05T123456Z"  # future-ok: synthetic: stamp
        in proc.stdout
    )
    # a second as-of stamps a DIFFERENT prefix — never an overwrite
    env["SIG_EXPORT_AS_OF"] = (
        "2026-10-06T00:00:00Z"  # future-ok: synthetic: export-leg fixture timestamp
    )
    proc2 = subprocess.run(
        ["bash", str(SCRIPT), "--check", "run"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc2.returncode == 0, proc2.stderr
    m1 = re.findall(r"exports/national/\S+", proc.stdout)
    m2 = re.findall(r"exports/national/\S+", proc2.stdout)
    assert m1 and m2 and set(m1) != set(m2)


def test_p35_12_belief_environment_replay_emergency_propagate() -> None:
    """P35.12 / SIG-REL-001+003: the wrapper forwards the belief instant, the
    declared environment and the clock-guard flags into the job's export
    command — a plan run must show them verbatim (NEW-2's fix)."""
    env = _env(
        SIG_GCP_PROJECT="example-proj",
        SIG_EXPORT_AS_OF="2026-10-05T12:34:56Z",  # future-ok: synthetic: leg fixture
        SIG_EXPORT_BELIEF="2026-10-05T12:00:00Z",  # future-ok: synthetic: fixture
        SIG_EXPORT_ENVIRONMENT="staging",
        SIG_EXPORT_REPLAY="restore-drill replay",
        SIG_EXPORT_EMERGENCY="takedown re-cut",
    )
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--check", "run"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    assert '--as-of "2026-10-05T12:34:56Z"' in proc.stdout
    assert '--environment "staging"' in proc.stdout
    assert '--belief "2026-10-05T12:00:00Z"' in proc.stdout
    assert '--replay "restore-drill replay"' in proc.stdout
    assert '--emergency "takedown re-cut"' in proc.stdout


def test_p35_12_optional_flags_absent_when_unset() -> None:
    """Unset SIG_EXPORT_BELIEF/REPLAY/EMERGENCY add no flags — the command
    stays exactly the live-cut shape."""
    env = _env(
        SIG_GCP_PROJECT="example-proj",
        SIG_EXPORT_AS_OF="2026-10-05T12:34:56Z",  # future-ok: synthetic: leg fixture
    )
    env.pop("SIG_EXPORT_BELIEF", None)
    env.pop("SIG_EXPORT_REPLAY", None)
    env.pop("SIG_EXPORT_EMERGENCY", None)
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--check", "run"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    assert '--environment "production"' in proc.stdout  # the declared default
    assert "--belief" not in proc.stdout
    assert "--replay" not in proc.stdout
    assert "--emergency" not in proc.stdout


def test_fetch_syncs_bucket_to_local_without_delete() -> None:
    env = _env(
        SIG_GCP_PROJECT="example-proj",
        SIG_EXPORT_AS_OF="2026-10-05T00:00:00Z",  # future-ok: synthetic: fixture
    )
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--check", "fetch"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    rsync = [ln for ln in proc.stdout.splitlines() if "rsync" in ln]
    assert rsync, "fetch plans no rsync"
    for line in rsync:
        assert "gs://example-proj-sig-restricted" in line
        assert "delete" not in line
