# SPDX-License-Identifier: Apache-2.0
"""tests/ops/test_wacz_capture_iac.py — the P37.56 WACZ-capture leg script
(BL-026). The offline plan, the AR-3 window guard, the author gate, and the
declared-shape invariant: every `wacz = true` cadence row's job plans a
`jobs update --args … --wacz`, the `run` leg is plan-only (the capture run
itself executes ONLY under live_verification=true), and an apply that meets
a surprise live arg shape stops (OM-18) rather than clobbering.
"""

from __future__ import annotations

import os
import subprocess
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "ops" / "gcp" / "wacz-capture.sh"
CADENCE = REPO_ROOT / "ops" / "cadence.toml"


def _env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    for k in ("SIG_GCP_PROJECT", "SIG_WACZ_AUTHOR", "SIG_WACZ_NOW"):
        env.pop(k, None)
    env.update(extra or {})
    return env


def _run(args: list[str], extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        env=_env(extra),
        cwd=str(REPO_ROOT),
    )


def _declared() -> list[tuple[str, str, str]]:
    """Every (job, source, batch) the script must name — straight off the
    declaration, never a pinned count: the rows change, the invariant does not."""
    doc = tomllib.loads(CADENCE.read_text())
    out = [(s["job"], s["id"], "") for s in doc.get("sources", []) if s.get("wacz")]
    out += [(b["job"], "", b["id"]) for b in doc.get("batches", []) if b.get("wacz")]
    return out


def test_check_plans_every_declared_wacz_job_update_offline() -> None:
    proc = _run(["--check", "jobs"])
    assert proc.returncode == 0, proc.stderr
    plan = proc.stdout
    declared = _declared()
    assert declared, "the declaration must carry at least one wacz row"
    for job, src, bid in declared:
        key = src or bid
        kind = "source" if src else "batch"
        want = (
            f'jobs update {job} --args "-c,exec sig-ops scheduled-ingest '
            f'--{kind} {key} --sink pg --wacz"'
        )
        assert want in plan, f"declared {kind} {key} ({job}) missing its --wacz update plan"


def test_check_never_executes_the_capture_run() -> None:
    # The `run` leg is the named mutation — in check mode it is a PLAN line,
    # and the plan itself records that it belongs to the live rerun only.
    proc = _run(["--check", "run"])
    assert proc.returncode == 0, proc.stderr
    assert "jobs execute" in proc.stdout
    assert "live_verification=true only" in proc.stdout


def test_apply_refuses_inside_the_window_band_and_without_author() -> None:
    # inside the daily 03:00–10:00Z band → exit 42 QUEUED (the AR-3 + AR-2 guard)
    proc = _run(
        ["--apply", "jobs"],
        {
            "SIG_WACZ_NOW": "2026-11-14T05:30:00Z",
            "SIG_WACZ_AUTHOR": "steve",
            "SIG_GCP_PROJECT": "p",
        },
    )
    assert proc.returncode == 42
    assert "QUEUED" in proc.stdout
    # outside the band but no recorded author → refuses (OM-20 scope discipline)
    proc = _run(
        ["--apply", "jobs"],
        {
            "SIG_WACZ_NOW": "2026-11-14T15:30:00Z",  # future-ok: synthetic: fixed test clock
            "SIG_GCP_PROJECT": "p",
        },
    )
    assert proc.returncode == 2
    assert "SIG_WACZ_AUTHOR" in (proc.stdout + proc.stderr)


def test_apply_meeting_a_surprise_arg_shape_stops_om18(tmp_path: Path) -> None:
    # armed on paper (author + window); a gcloud stub whose `describe` answers
    # nothing parseable → the jobs leg meets an arg shape that is neither the
    # declared nor the wacz form and STOPS (OM-18), never a blind update.
    stub = tmp_path / "gcloud"
    stub.write_text("#!/usr/bin/env bash\nexit 1\n")
    stub.chmod(0o755)
    proc = _run(
        ["--apply", "jobs"],
        {
            "SIG_WACZ_NOW": "2026-11-14T15:30:00Z",  # future-ok: synthetic: fixed test clock
            "SIG_WACZ_AUTHOR": "steve",
            "SIG_GCP_PROJECT": "p",
            "PATH": f"{tmp_path}:{os.environ.get('PATH', '')}",
        },
    )
    assert proc.returncode == 4
    assert "match neither the declared nor the wacz shape" in (proc.stdout + proc.stderr)


def test_rollback_plans_the_exact_prestate_args() -> None:
    proc = _run(["--check", "rollback"])
    assert proc.returncode == 0, proc.stderr
    # a rollback restores the declared non-wacz shape — never touches evidence
    assert "jobs update sig-ingest-" in proc.stdout
    assert " --wacz" not in "\n".join(ln for ln in proc.stdout.splitlines() if "jobs update" in ln)
