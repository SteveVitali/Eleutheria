# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""`scripts/bump_version.py` bumps all 15 version files together (SIG-REL-014).

The script runs against a temp copy of the tree — the real pyprojects and
`web/package.json` are never touched by the test. Fails if the script stops
rewriting a member, writes under dry-run, accepts `0.0.0` or malformed input,
or changes any line other than the version field.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

from support import PY_PACKAGES, REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "bump_version.py"


def _copy_tree(tmp: Path) -> Path:
    """A minimal bumpable tree: root pyproject (members list) + the 15 files."""
    root = tmp / "repo"
    root.mkdir(parents=True)
    shutil.copy(REPO_ROOT / "pyproject.toml", root / "pyproject.toml")
    for pkg in PY_PACKAGES:
        (root / pkg).mkdir()
        shutil.copy(REPO_ROOT / pkg / "pyproject.toml", root / pkg / "pyproject.toml")
    (root / "web").mkdir()
    shutil.copy(REPO_ROOT / "web" / "package.json", root / "web" / "package.json")
    return root


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def _py_version(path: Path) -> str:
    with path.open("rb") as fh:
        return str(tomllib.load(fh)["project"]["version"])


def _web_version(path: Path) -> str:
    return str(json.loads(path.read_text(encoding="utf-8"))["version"])


def test_dry_run_changes_nothing(tmp_path: Path) -> None:
    root = _copy_tree(tmp_path)
    proc = _run("0.1.1", "--root", str(root))
    assert proc.returncode == 0, proc.stderr
    for pkg in PY_PACKAGES:
        assert _py_version(root / pkg / "pyproject.toml") == "0.1.0"
    assert _web_version(root / "web" / "package.json") == "0.1.0"
    assert "dry-run" in proc.stdout and "would change" in proc.stdout


def test_apply_bumps_every_file_and_nothing_else(tmp_path: Path) -> None:
    root = _copy_tree(tmp_path)
    before = {
        p: p.read_text(encoding="utf-8")
        for p in [
            *(root / pkg / "pyproject.toml" for pkg in PY_PACKAGES),
            root / "web" / "package.json",
        ]
    }
    proc = _run("0.1.1", "--root", str(root), "--apply")
    assert proc.returncode == 0, proc.stderr

    for pkg in PY_PACKAGES:
        path = root / pkg / "pyproject.toml"
        assert _py_version(path) == "0.1.1", f"{pkg} not bumped"
        # Exactly one line changed — the version line.
        diff = [
            (a, b)
            for a, b in zip(before[path].split("\n"), path.read_text().split("\n"), strict=True)
            if a != b
        ]
        assert len(diff) == 1 and 'version = "0.1.1"' in diff[0][1], diff
    web = root / "web" / "package.json"
    assert _web_version(web) == "0.1.1"
    diff = [
        (a, b)
        for a, b in zip(before[web].split("\n"), web.read_text().split("\n"), strict=True)
        if a != b
    ]
    assert len(diff) == 1 and '"version": "0.1.1"' in diff[0][1], diff
    # The root pyproject (the virtual workspace) is never a bump target.
    assert (root / "pyproject.toml").read_text() == (REPO_ROOT / "pyproject.toml").read_text()


def test_apply_refuses_zero_version(tmp_path: Path) -> None:
    root = _copy_tree(tmp_path)
    proc = _run("0.0.0", "--root", str(root), "--apply")
    assert proc.returncode == 2
    assert _py_version(root / "db" / "pyproject.toml") == "0.1.0"


def test_rejects_non_semver_argument(tmp_path: Path) -> None:
    root = _copy_tree(tmp_path)
    for bad in ("1.2", "v0.1.1", "0.1.1-rc1", "latest"):
        proc = _run(bad, "--root", str(root), "--apply")
        assert proc.returncode == 2, f"{bad!r} must be refused"
    assert _py_version(root / "db" / "pyproject.toml") == "0.1.0"


def test_missing_target_file_fails_closed(tmp_path: Path) -> None:
    root = _copy_tree(tmp_path)
    (root / "db" / "pyproject.toml").unlink()
    proc = _run("0.1.1", "--root", str(root), "--apply")
    assert proc.returncode == 1
    # The other files still report their bump (the failure is per-target),
    # and the run never pretends the missing file was bumped.
    assert "missing" in proc.stderr
