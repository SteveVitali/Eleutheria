#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Worktree-safety fixtures for ``scripts/docs/check-build-memory.sh`` (P32.8,
SIG-MEM-003): two concurrent validations must never overwrite each other's
report, the JSON report must name the checked input revision (commit + input
digest), diagnostics carry the uniform {check,severity,file,obligation,
evidence,message} shape, and the report's recorded exit code must agree with the
process exit status. The fixtures are minimal build-memory trees — the checks
exercise the report contract, not repo-specific content.
"""

from __future__ import annotations

import json
import pathlib
import subprocess

from support import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "docs" / "check-build-memory.sh"

MINIMAL_TREE = {
    "docs/build/README.md": "# build\n\n<!-- build-memory: v2 -->\n",
    "docs/build/logs/.gitignore": "*\n!.gitignore\n",
    "docs/build/LEDGER.md": "# ledger\n",
    "docs/tickets/00_MANIFEST.md": "# manifest\n\n## The chain\n\n| # | Ticket |\n|---|---|\n",
    "docs/tickets/DEFERRALS.md": "# deferrals\n",
}


def _tree(root: pathlib.Path) -> pathlib.Path:
    for rel, text in MINIMAL_TREE.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return root


def _run(repo: pathlib.Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), str(repo), *extra],
        capture_output=True,
        text=True,
        timeout=300,
    )


def _report_path(stdout: str) -> pathlib.Path:
    line = [ln for ln in stdout.splitlines() if "JSON:" in ln]
    assert line, f"no JSON path printed in stdout:\n{stdout}"
    return pathlib.Path(line[-1].split("JSON:", 1)[1].strip())


def test_caller_selected_json_path_honored(tmp_path: pathlib.Path) -> None:
    repo = _tree(tmp_path / "repo")
    out = tmp_path / "chosen.json"
    r = _run(repo, "--json", str(out))
    assert out.is_file()
    report = json.loads(out.read_text())
    assert report["schema"] == "build-memory-check/2"
    # exit severity and the recorded exit agree
    assert report["summary"]["exit"] == r.returncode


def test_default_output_is_unique_per_run(tmp_path: pathlib.Path) -> None:
    repo = _tree(tmp_path / "repo")
    r1, r2 = _run(repo), _run(repo)
    p1, p2 = _report_path(r1.stdout), _report_path(r2.stdout)
    # two validations get two distinct report paths — no shared /tmp filename
    assert p1 != p2
    assert p1.name != "build-memory-check.json" and p2.name != "build-memory-check.json"
    assert p1.is_file() and p2.is_file()
    p1.unlink()
    p2.unlink()


def test_concurrent_validations_never_overwrite(tmp_path: pathlib.Path) -> None:
    """Two worktrees validating at once keep two distinct reports — the shared
    /tmp write-collision defect this patch exists to fix."""
    repo_a = _tree(tmp_path / "a")
    repo_b = _tree(tmp_path / "b")
    ra, rb = _run(repo_a), _run(repo_b)
    pa, pb = _report_path(ra.stdout), _report_path(rb.stdout)
    assert pa != pb
    ra_report = json.loads(pa.read_text())
    rb_report = json.loads(pb.read_text())
    assert ra_report["input"]["repo"] == str(repo_a)
    assert rb_report["input"]["repo"] == str(repo_b)
    pa.unlink()
    pb.unlink()


def test_report_records_checked_input_identity(tmp_path: pathlib.Path) -> None:
    repo = _tree(tmp_path / "repo")
    out = tmp_path / "r.json"
    _run(repo, "--json", str(out))
    report = json.loads(out.read_text())
    identity = report["input"]
    assert identity["repo"] == str(repo)
    # non-git fixture: commit may be empty, but the input digest is mandatory —
    # a report is valid only for the exact input revision it names
    assert len(identity["input_digest"]) == 64
    assert "dirty" in identity


def test_input_digest_tracks_input_revision(tmp_path: pathlib.Path) -> None:
    repo = _tree(tmp_path / "repo")
    out1, out2 = tmp_path / "r1.json", tmp_path / "r2.json"
    _run(repo, "--json", str(out1))
    (repo / "docs/tickets/DEFERRALS.md").write_text("# deferrals v2\n")
    _run(repo, "--json", str(out2))
    d1 = json.loads(out1.read_text())["input"]["input_digest"]
    d2 = json.loads(out2.read_text())["input"]["input_digest"]
    assert d1 != d2  # a stale report cannot masquerade as fresh


def test_diagnostics_carry_uniform_record_shape(tmp_path: pathlib.Path) -> None:
    repo = _tree(tmp_path / "repo")
    # inject a real violation: an unallowed docs/build root entry
    (repo / "docs/build/stray.md").write_text("not allowed\n")
    out = tmp_path / "r.json"
    r = _run(repo, "--json", str(out))
    report = json.loads(out.read_text())
    assert r.returncode == 1
    assert report["summary"]["exit"] == 1
    assert report["summary"]["violations"] >= 1
    rec = report["violations"][0]
    for key in ("check", "severity", "file", "obligation", "evidence", "message"):
        assert key in rec, rec
    assert rec["severity"] == "error"
    assert rec["check"] == "layout"
    assert rec["file"].endswith("stray.md")


def test_non_repo_exit_2_report_agrees(tmp_path: pathlib.Path) -> None:
    out = tmp_path / "r.json"
    r = _run(tmp_path / "empty", "--json", str(out))
    assert r.returncode == 2
    report = json.loads(out.read_text())
    assert report["buildMemory"] is False
    assert report["summary"]["exit"] == 2


def test_no_unmodified_vendoring_claim(tmp_path: pathlib.Path) -> None:
    """Truthful provenance: the patched script must NOT claim to be a
    byte-for-byte / unmodified copy of upstream (SIG-MEM-003)."""
    text = SCRIPT.read_text()
    assert "LOCAL PATCH" in text
    # no surviving claim that the file is still an unmodified/unaltered copy
    header = text.split("check-build-memory.sh — validate", 1)[0]
    assert "UNALTERED copy" not in header
    assert "unaltered copy" not in header
    assert "unmodified" not in header.replace("NO LONGER", "")
