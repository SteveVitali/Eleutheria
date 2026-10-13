#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``changelog_gate.py`` (SIG-REL-014, P34.23; G3 §9.4).

Each case builds a throw-away git repo in ``tmp_path``: a range touching
``web/src/pages/`` without a CHANGELOG change fails, and the same range
passes when CHANGELOG.md changes too or a commit carries a
``Changelog: none (<reason>)`` trailer. Remove the gate or gut a rule and a
test here fails.

Run::

    uv run pytest docs/build/tools/test_changelog_gate.py -q
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TOOL = HERE / "changelog_gate.py"
PYTHON = os.environ.get("SIG_TOOLS_PYTHON") or sys.executable

TRAILER = "Harness: devin-desktop/swe-2-high/subagent"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.email=t@example.invalid",
            "-c",
            "user.name=t",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            *args,
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def commit(repo: Path, path: str, message: str) -> str:
    f = repo / path
    f.parent.mkdir(parents=True, exist_ok=True)
    prior = f.read_text() if f.exists() else ""
    f.write_text(f"{prior}{path} {len(prior)}\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD").strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    commit(r, "CHANGELOG.md", f"base\n\n{TRAILER}")
    git(r, "tag", "base")
    return r


def check(repo: Path, span: str = "base..HEAD") -> tuple[int, dict, str]:
    out = repo.parent / "gate.json"
    if out.exists():
        out.unlink()
    proc = subprocess.run(
        [PYTHON, str(TOOL), "--range", span, "--repo", str(repo), "--json", str(out)],
        capture_output=True,
        text=True,
    )
    doc = json.loads(out.read_text()) if out.exists() else {}
    return proc.returncode, doc, proc.stdout + proc.stderr


def test_public_page_without_changelog_fails(repo: Path) -> None:
    commit(repo, "web/src/pages/index.astro", f"page change\n\n{TRAILER}")
    rc, doc, out = check(repo)
    assert rc == 1, out
    assert doc["verdict"] == "fail"
    assert doc["public_paths"] == ["web/src/pages/index.astro"]


def test_public_page_with_changelog_passes(repo: Path) -> None:
    commit(repo, "web/src/pages/index.astro", f"page change\n\n{TRAILER}")
    commit(repo, "CHANGELOG.md", f"entry\n\n{TRAILER}")
    rc, doc, out = check(repo)
    assert rc == 0, out
    assert doc["changelog_changed"] is True


def test_public_page_with_trailer_passes(repo: Path) -> None:
    commit(
        repo,
        "web/src/pages/index.astro",
        f"page change\n\nChangelog: none (copy-only fix, no behaviour)\n{TRAILER}",
    )
    rc, doc, out = check(repo)
    assert rc == 0, out
    assert doc["changelog_trailer"]["reason"].startswith("copy-only fix")


def test_empty_reason_trailer_does_not_pass(repo: Path) -> None:
    commit(
        repo,
        "web/src/pages/index.astro",
        f"page change\n\nChangelog: none ()\n{TRAILER}",
    )
    rc, doc, out = check(repo)
    assert rc == 1, out


def test_trailer_in_body_not_final_paragraph_does_not_count(repo: Path) -> None:
    commit(
        repo,
        "web/src/pages/index.astro",
        f"page change\n\nmentions Changelog: none (x) in prose\n\n{TRAILER}",
    )
    rc, doc, out = check(repo)
    assert rc == 1, out


def test_no_public_path_passes(repo: Path) -> None:
    commit(repo, "docs/some/doc.md", f"docs\n\n{TRAILER}")
    rc, doc, out = check(repo)
    assert rc == 0, out
    assert doc["public_paths"] == []


@pytest.mark.parametrize(
    "path",
    [
        "web/src/pages/dossiers/index.astro",
        "web/src/layouts/Base.astro",
        "api/src/api/routes.py",
        "api/src/api/app.py",
        "api/src/api/models.py",
        "exports/src/exports/release.py",
        "exports/src/exports/release_publish.py",
        "exports/src/exports/spine_export.py",
        "exports/src/exports/manifest.py",
        "ops/public_routes.toml",
        "ops/disclosures.toml",
        "policy/src/policy/licensing.py",
        "policy/data/rights.toml",
        "ontology/src/ontology/generate.py",
    ],
)
def test_each_public_path_fails(repo: Path, path: str) -> None:
    commit(repo, path, f"change\n\n{TRAILER}")
    rc, doc, out = check(repo)
    assert rc == 1, f"{path} must be in the public set: {out}"
    assert doc["public_paths"] == [path]


@pytest.mark.parametrize(
    "path",
    [
        "web/src/lib/data.ts",
        "api/src/api/store_pg.py",
        "exports/src/exports/bundle.py",
        "exports/src/exports/releases/manifest_helper.py",  # a directory, not release*.py
        "ops/config.toml",
        "db/src/db/claim_sink.py",
        "ontology/generated/pydantic/sig_models.py",
        "tests/unit/test_x.py",
    ],
)
def test_non_public_paths_pass(repo: Path, path: str) -> None:
    commit(repo, path, f"change\n\n{TRAILER}")
    rc, doc, out = check(repo)
    assert rc == 0, f"{path} must NOT be in the public set: {out}"


def test_vacuous_range_is_not_green(repo: Path) -> None:
    rc, doc, out = check(repo, "base..base")
    assert rc == 3, out
    assert doc["verdict"] == "vacuous"


def test_unresolvable_range_is_unknown(repo: Path) -> None:
    proc = subprocess.run(
        [PYTHON, str(TOOL), "--range", "nonexistent..HEAD", "--repo", str(repo)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 5


def test_three_dot_uses_merge_base(repo: Path) -> None:
    """`base...HEAD` judges the same file set as the PR diff (merge base)."""
    git(repo, "checkout", "-q", "-b", "feature")
    commit(repo, "web/src/pages/x.astro", f"page\n\n{TRAILER}")
    git(repo, "checkout", "-q", "main")
    commit(repo, "docs/other.md", f"other\n\n{TRAILER}")
    rc, doc, out = check(repo, "main...feature")
    assert rc == 1, out
    assert doc["public_paths"] == ["web/src/pages/x.astro"]
