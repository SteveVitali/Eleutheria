#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``check_trailers.py`` (OM-01 trailer grammar; Round 11 Stage B, SEED-02b; plan §3.3).

Synthetic cases build a throw-away git repo per test in ``tmp_path``; oracle cases judge real commits of
this repository read-only (the Stage-B planning commits pass; a Round-10 Devin CLI commit with no
trailer fails; a Devin commit as Devin recorded it passes) and skip on a shallow clone. Every test
asserts a classification or an exit code a no-op check cannot produce.

Run::

    uv run pytest docs/build/tools/test_check_trailers.py -q
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TOOL = HERE / "check_trailers.py"
# The interpreter the tool runs under (default: this one). SIG_TOOLS_PYTHON=/usr/bin/python3 checks the
# oldest Python the skill may meet (macOS system Python 3.9).
PYTHON = os.environ.get("SIG_TOOLS_PYTHON") or sys.executable

CLAUDE = "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
DEVIN = "Co-Authored-By: Devin <158243242+devin-ai-integration[bot]@users.noreply.github.com>"


def git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
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
        env={**os.environ, **(env or {})},
    ).stdout


def commit(
    repo: Path,
    message: str,
    pre: tuple[str, ...] = (),
    post: tuple[str, ...] = (),
    env: dict[str, str] | None = None,
) -> str:
    n = len(list(repo.glob("f*.txt")))
    (repo / f"f{n}.txt").write_text(f"{n}\n")
    git(repo, "add", "-A")
    git(repo, *pre, "commit", "-q", *post, "-m", message, env=env)
    return git(repo, "rev-parse", "HEAD").strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    commit(r, f"base\n\n{CLAUDE}")
    git(r, "tag", "base")
    return r


def check(repo: Path, span: str = "base..HEAD", *extra: str) -> tuple[int, dict, str]:
    out = repo.parent / "trailers.json"
    if out.exists():
        out.unlink()
    proc = subprocess.run(
        [
            PYTHON,
            str(TOOL),
            "--range",
            span,
            "--repo",
            str(repo),
            "--json",
            str(out),
            *extra,
        ],
        capture_output=True,
        text=True,
    )
    doc = json.loads(out.read_text()) if out.exists() else {}
    return proc.returncode, doc, proc.stdout + proc.stderr


def classes(doc: dict) -> list[str]:
    return [c["class"] for c in doc.get("commits", [])]


# ── recognised harness trailers ─────────────────────────────────────────────


def test_claude_code_co_author_trailer_passes(repo: Path) -> None:
    commit(
        repo,
        f"SEED-02b: wiring\n\nBody text.\n\nHarness: claude-code/claude-opus-5-5/subagent\n{CLAUDE}",
    )
    commit(
        repo,
        "planning: notes\n\nCo-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>",
    )
    rc, doc, _ = check(repo)
    assert rc == 0 and classes(doc) == ["agent", "agent"]
    first = doc["commits"][0]["trailers"]
    assert {
        "kind": "co-author",
        "harness": "claude-code",
        "model": "claude-opus-5-5",
        "tier": None,
    } in first
    assert {
        "kind": "harness",
        "harness": "claude-code",
        "model": "claude-opus-5-5",
        "tier": "subagent",
    } in first
    assert doc["commits"][1]["trailers"][0]["model"] == "claude-opus-5-5"


def test_harness_line_alone_passes(repo: Path) -> None:
    commit(repo, "P34.1: pin\n\nHarness: devin-desktop/swe-2-high/subagent")
    rc, doc, _ = check(repo)
    assert rc == 0 and classes(doc) == ["agent"] and doc["summary"]["warnings"] == 0
    assert doc["commits"][0]["trailers"][0]["tier"] == "subagent"


def test_devin_trailer_as_devin_writes_it(repo: Path) -> None:
    """No blank line between Devin's `Generated with` line and its co-author trailer: git's own
    trailer parser sees nothing, the grammar still recognises it (and warns: no model named)."""
    sha = commit(
        repo, f"docs(build): record PR #74\n\nGenerated with [Devin](https://devin.ai)\n{DEVIN}\n"
    )
    assert git(repo, "log", "-1", "--format=%(trailers:only)", sha).strip() == ""
    rc, doc, _ = check(repo)
    assert rc == 0 and classes(doc) == ["agent"]
    assert doc["commits"][0]["trailers"][0]["harness"] == "devin"
    assert any("names no model" in w for w in doc["commits"][0]["warnings"])
    commit(
        repo,
        f"P34.2\n\nGenerated with [Devin](https://devin.ai)\nHarness: devin-desktop/swe-2-high/subagent\n{DEVIN}",
    )
    rc2, doc2, _ = check(repo, "HEAD~1..HEAD")
    assert rc2 == 0 and doc2["commits"][0]["warnings"] == []


def test_devin_trailer_naming_its_model(repo: Path) -> None:
    commit(repo, "x\n\nCo-Authored-By: Devin (swe-2-high) <devin@cognition.ai>")
    rc, doc, _ = check(repo)
    assert rc == 0 and doc["commits"][0]["trailers"][0]["model"] == "swe-2-high"


# ── failures ────────────────────────────────────────────────────────────────


def test_untrailered_commit_fails_and_is_named(repo: Path) -> None:
    commit(repo, f"ok\n\n{CLAUDE}")
    bad = commit(repo, "P33.8: close the memory chain\n\nGates: make check green.")
    rc, doc, out = check(repo)
    assert rc == 1 and classes(doc) == ["agent", "untrailered"]
    assert doc["summary"]["violations"] == 1 and bad[:8] in out


def test_trailer_quoted_in_the_body_does_not_count(repo: Path) -> None:
    commit(
        repo,
        f"docs: describe the grammar\n\n{CLAUDE}\n\nThe line above is quoted prose, not a trailer.",
    )
    rc, doc, _ = check(repo)
    assert rc == 1 and classes(doc) == ["untrailered"]


@pytest.mark.parametrize(
    "line",
    [
        "Co-Authored-By: Claude Opus 5.5 <someone@example.invalid>",  # not the harness's address
        "Co-Authored-By: Claude <noreply@anthropic.com>",  # names no model
        "Co-Authored-By: Devin <devin@example.invalid>",
        "Harness: claude-code",  # malformed: no model, no tier
        "Harness: claude code/opus/subagent",
        "Signed-off-by: t <t@example.invalid>",
    ],
)
def test_lookalike_trailers_fail(repo: Path, line: str) -> None:
    commit(repo, f"x\n\n{line}")
    rc, doc, _ = check(repo)
    assert rc == 1 and classes(doc) == ["untrailered"], doc


# ── operator commits ────────────────────────────────────────────────────────


def test_harness_operator_trailer_passes(repo: Path) -> None:
    commit(repo, "HG-03 flips, wave A\n\nHarness: operator")
    rc, doc, _ = check(repo)
    assert rc == 0 and classes(doc) == ["operator"]


def _ssh_key(tmp: Path, name: str) -> Path:
    if shutil.which("ssh-keygen") is None:
        pytest.skip("ssh-keygen not available")
    key = tmp / name
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", name, "-f", str(key)], check=True
    )
    return key


def _sign_opts(key: Path) -> tuple[str, ...]:
    return ("-c", "gpg.format=ssh", "-c", f"user.signingkey={key}")


def _allowed(path: Path, key: Path) -> Path:
    kind, blob = key.with_suffix(".pub").read_text().split()[:2]
    path.write_text(f"t@example.invalid {kind} {blob}\n")
    return path


def test_op25_signature_presence_verified_and_rejected(repo: Path, tmp_path: Path) -> None:
    key = _ssh_key(tmp_path, "op25")
    other = _ssh_key(tmp_path, "other")
    sha = commit(
        repo, "operator: flip wave A (signed, no trailer)", pre=_sign_opts(key), post=("-S",)
    )
    assert "BEGIN SSH SIGNATURE" in git(repo, "cat-file", "commit", sha)
    # no allowed-signers file: a signature nobody can verify identifies no one -> fails (a signing
    # default in an agent session's git config must not turn an untrailered commit green)
    rc, doc, out = check(repo)
    assert rc == 1 and classes(doc) == ["untrailered"], doc
    assert "nothing to verify it against" in doc["commits"][0]["violations"][0]
    assert "Harness: operator" in out
    # the key is an allowed signer -> verified
    allowed = _allowed(tmp_path / "allowed_signers", key)
    rc2, doc2, _ = check(repo, "base..HEAD", "--allowed-signers", str(allowed))
    assert rc2 == 0 and classes(doc2) == ["operator-signed"], doc2
    # only another key is allowed -> the signature does not verify -> fails
    _allowed(allowed, other)
    rc3, doc3, _ = check(repo, "base..HEAD", "--allowed-signers", str(allowed))
    assert (
        rc3 == 1
        and classes(doc3) == ["untrailered"]
        and doc3["commits"][0]["signature_status"] != "G"
    )
    # default: the repo's allowed-signers file as committed at BASE — a change adding its own signer
    # does not verify itself (the file is absent at `base`)
    dest = repo / "docs/build/tools/record_policy/allowed_signers"
    dest.parent.mkdir(parents=True)
    _allowed(dest, other)
    commit(repo, "operator: add my own signer (signed)", pre=_sign_opts(other), post=("-S",))
    rc4, doc4, _ = check(repo)
    assert rc4 == 1 and set(classes(doc4)) == {"untrailered"}
    assert doc4["input"]["allowed_signers"] is None
    # once committed at the base, it is read from there and judges later commits
    _allowed(dest, key)
    commit(repo, f"P34.28: commit the OP-25 allowed signer\n\n{CLAUDE}")
    git(repo, "tag", "base2")
    commit(repo, "operator: signed with the OP-25 key", pre=_sign_opts(key), post=("-S",))
    commit(repo, "operator: signed with another key", pre=_sign_opts(other), post=("-S",))
    rc5, doc5, _ = check(repo, "base2..HEAD")
    assert rc5 == 1 and classes(doc5) == ["operator-signed", "untrailered"]
    assert doc5["input"]["allowed_signers"].startswith("base2:")


def test_github_merge_passes_a_local_untrailered_merge_does_not(repo: Path, tmp_path: Path) -> None:
    key = _ssh_key(tmp_path, "webflow")
    git(repo, "checkout", "-q", "-b", "r11/p34-1")
    commit(repo, f"P34.1 work\n\n{CLAUDE}")
    git(repo, "checkout", "-q", "main")
    git(
        repo,
        *_sign_opts(key),
        "merge",
        "-q",
        "--no-ff",
        "-S",
        "-m",
        "Merge pull request #202 from o/r11/p34-1",
        "r11/p34-1",
        env={"GIT_COMMITTER_NAME": "GitHub", "GIT_COMMITTER_EMAIL": "noreply@github.com"},
    )
    rc, doc, _ = check(repo)
    assert rc == 0 and sorted(classes(doc)) == ["agent", "operator-github-merge"]
    git(repo, "reset", "-q", "--hard", "HEAD~1")
    git(repo, "merge", "-q", "--no-ff", "-m", "Merge branch r11/p34-1", "r11/p34-1")
    rc2, doc2, _ = check(repo)
    assert rc2 == 1 and sorted(classes(doc2)) == ["agent", "untrailered"]


# ── range handling, exits ───────────────────────────────────────────────────


def test_three_dot_range_judges_from_the_merge_base(repo: Path) -> None:
    git(repo, "checkout", "-q", "-b", "feature")
    commit(repo, "no trailer")
    git(repo, "checkout", "-q", "main")
    commit(repo, f"main moves on\n\n{CLAUDE}")
    rc, doc, _ = check(repo, "main...feature")
    assert rc == 1 and classes(doc) == ["untrailered"] and doc["summary"]["commits"] == 1


def test_empty_range_is_vacuous(repo: Path) -> None:
    rc, doc, out = check(repo, "HEAD..HEAD")
    assert rc == 3 and doc["summary"]["commits"] == 0 and "vacuous" in out


def test_unresolvable_revision_and_shallow_clone_are_unknown(repo: Path, tmp_path: Path) -> None:
    rc, doc, _ = check(repo, "deadbeef..HEAD")
    assert rc == 5 and doc["exit"] == 5
    commit(repo, f"two\n\n{CLAUDE}")
    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", f"file://{repo}", str(shallow)],
        check=True,
        capture_output=True,
    )
    rc2, _, out2 = check(shallow, "HEAD~1..HEAD")
    assert rc2 == 5 and "shallow" in out2


@pytest.mark.parametrize("argv", [[], ["--range", "nonsense"]])
def test_usage_errors_exit_2(argv: list[str], repo: Path) -> None:
    proc = subprocess.run([PYTHON, str(TOOL), *argv, "--repo", str(repo)], capture_output=True)
    assert proc.returncode == 2


def test_parser_units() -> None:
    spec = importlib.util.spec_from_file_location("check_trailers", TOOL)
    assert spec is not None and spec.loader is not None
    ct = importlib.util.module_from_spec(spec)
    sys.modules["check_trailers"] = ct
    spec.loader.exec_module(ct)
    t = ct.parse_trailers(
        "s\n\nb\n\nHarness: Operator\nco-authored-by: Claude Sonnet 5 <NOREPLY@anthropic.com>"
    )
    assert t.operator and t.harness[0]["model"] == "claude-sonnet-5"
    folded = ct.final_paragraph("s\n\nHarness: claude-code/\n  claude-opus-5-5/subagent")
    assert folded == ["Harness: claude-code/ claude-opus-5-5/subagent"]
    assert ct.final_paragraph("subject only") == []


# ── real-history oracles (read-only) ────────────────────────────────────────


def _have(*shas: str) -> bool:
    shallow = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--is-shallow-repository"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    ok = all(
        subprocess.run(
            ["git", "-C", str(ROOT), "cat-file", "-e", f"{s}^{{commit}}"], capture_output=True
        ).returncode
        == 0
        for s in shas
    )
    return shallow == "false" and ok


def test_oracle_stage_b_planning_commits_pass(tmp_path: Path) -> None:
    """The seed PR's planning commits (≈ 90 at S6c), all `Co-Authored-By: Claude Opus 5.5`, pass (§3.3)."""
    if not _have("b051732c", "6d988aeb"):
        pytest.skip("history not in this clone")
    rc, doc, _ = check(ROOT, "b051732c..6d988aeb")
    assert rc == 0 and doc["summary"]["commits"] >= 100 and set(classes(doc)) == {"agent"}


def test_oracle_round10_untrailered_devin_cli_commit_fails(tmp_path: Path) -> None:
    if not _have("c77bd45e"):
        pytest.skip("history not in this clone")
    rc, doc, _ = check(ROOT, "c77bd45e^..c77bd45e")
    assert rc == 1 and classes(doc) == ["untrailered"]


def test_oracle_devin_commit_as_recorded_passes(tmp_path: Path) -> None:
    if not _have("fb2ea1c9"):
        pytest.skip("history not in this clone")
    rc, doc, _ = check(ROOT, "fb2ea1c9^..fb2ea1c9")
    assert (
        rc == 0
        and classes(doc) == ["agent"]
        and doc["commits"][0]["trailers"][0]["harness"] == "devin"
    )
