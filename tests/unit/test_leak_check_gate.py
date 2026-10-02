# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The GCP leak check is fail-closed (P34.2 deliverable 7, H2 §5 S-4).

`tests/connectors/test_secrets.py::test_gcp_project_id_is_env_resolved_not_committed`
used to `pytest.skip` when `SIG_GCP_PROJECT` was unset — a check without its
needle passed vacuously. These meta-tests run the real test in a subprocess:
unset → it must FAIL (never skip, never green); armed with a sentinel id → it
must pass and report candidates/evaluated (SIG-ENG-042).
"""

from __future__ import annotations

import os
import subprocess
import sys

from support import REPO_ROOT

NODE = "tests/connectors/test_secrets.py::test_gcp_project_id_is_env_resolved_not_committed"
SENTINEL = "sig-leak-check-sentinel-9e7d"  # a value that is NOT committed anywhere


def _pytest(env_extra: dict[str, str | None]) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    for key, value in env_extra.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-rP", NODE],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_leak_check_fails_closed_when_unarmed() -> None:
    proc = _pytest({"SIG_GCP_PROJECT": None})
    assert proc.returncode != 0, "an unarmed leak check must fail, not skip"
    assert "1 failed" in proc.stdout or "failed" in proc.stdout
    assert "skipped" not in proc.stdout.splitlines()[-1]
    assert "OP-07" in proc.stdout + proc.stderr


def test_leak_check_armed_scans_and_reports_counts() -> None:
    proc = _pytest({"SIG_GCP_PROJECT": SENTINEL})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    # -rP surfaces the check's captured stdout: the non-vacuous report.
    assert "leak-check: candidates=" in proc.stdout and "evaluated=" in proc.stdout
    assert "candidates=0" not in proc.stdout, "a zero-candidate scan is vacuous"


def test_leak_check_scope_resolves_tracked_files() -> None:
    """The needle mechanism is real: `git grep` over the check's scope finds a
    committed literal (the env-var name itself is referenced in scope)."""
    import re

    src = (REPO_ROOT / "tests/connectors/test_secrets.py").read_text()
    scope = re.search(r"_PROJECT_ID_SCOPE\s*=\s*\(([^)]*)\)", src)
    assert scope, "the check's pathspec tuple must be locatable"
    paths = re.findall(r'"([^"]+)"', scope.group(1))
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "grep", "-Il", "-e", "SIG_GCP_PROJECT", "--", *paths],
        capture_output=True,
        text=True,
    )
    assert proc.stdout.split(), (
        "git grep must find in-scope hits for a committed literal — the same "
        "mechanism that flags a leaked project id"
    )
