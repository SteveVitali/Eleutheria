#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``verify_recorded_ci.py`` (G3b; P34.2, SIG-MEM-007).

Every test runs the real CLI against a stubbed ``gh``: the stub answers
``gh api repos/{owner}/{repo}/actions/runs/<id>`` and
``gh api …/commits/<sha>/check-runs`` from a JSON fixture. No network. Each test
asserts a verdict a no-op verifier cannot produce — a forged or vacuous record
must fail.

Run::

    uv run pytest docs/build/tools/test_verify_recorded_ci.py -q
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TOOL = HERE / "verify_recorded_ci.py"
PYTHON = os.environ.get("SIG_TOOLS_PYTHON") or sys.executable

STUB = r"""
import json, os, re, sys
fx = json.load(open(os.environ["GH_STUB"]))
with open(os.environ["GH_STUB"] + ".log", "a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\n")

def fail(msg, code=1):
    sys.stderr.write(msg + "\n")
    sys.exit(code)

args = sys.argv[1:]
if fx.get("auth_error"):
    fail("gh auth login", 4)
if args[:1] == ["api"] and "/actions/runs/" in args[1]:
    rid = args[1].rsplit("/", 1)[1]
    if rid not in fx.get("runs", {}):
        fail("gh: Not Found (HTTP 404)")
    print(json.dumps(fx["runs"][rid]))
elif args[:1] == ["api"] and "/commits/" in args[1] and "/check-runs" in args[1]:
    sha = re.search(r"commits/([0-9a-fA-F]+)/check-runs", args[1]).group(1)
    page = {"total_count": len(fx.get("check_runs", {}).get(sha, [])),
            "check_runs": fx.get("check_runs", {}).get(sha, [])}
    print(json.dumps(page))
else:
    fail("stub: unexpected gh call " + " ".join(args), 2)
"""

SHA_HEAD = "abc1234" + "0" * 33
SHA_OTHER = "def5678" + "0" * 33

LEDGER = """# ledger

## PHASE LOG — Round 11

- 2026-10-01 — P34.1 ticket — PR #193 · 5/5 green (`ci: pass #193@{sha7}`) · tip r11/x
- 2026-10-01 — GATE-P pause — a pause entry, exempt from ci:

## PHASE LOG — Round 10
"""

RUN_LEDGER = """# run ledger
some prose
ci: pass #193@{sha7} (python 36000001; docs 36000002; composed 36000003; security 36000004; \
web 36000005) · stack: #192 pass
"""


def _check_runs(sha: str, conclusion: str = "success") -> list[dict]:
    return [
        {
            "id": 9000 + k,
            "name": name,
            "head_sha": sha,
            "status": "completed",
            "conclusion": conclusion,
            "app": {"slug": "github-actions"},
        }
        for k, name in enumerate(["python", "docs", "composed", "security", "web"])
    ]


def _all_green_runs() -> dict[str, dict]:
    return {
        str(rid): {"id": rid, "head_sha": SHA_HEAD, "status": "completed", "conclusion": "success"}
        for rid in (36000001, 36000002, 36000003, 36000004, 36000005, 36000006)
    }


@pytest.fixture
def env(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "docs/build/tools/record_policy").mkdir(parents=True)
    (repo / "docs/build/runs").mkdir(parents=True)
    (repo / "docs/build/reports/ci").mkdir(parents=True)

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo), "-c", "user.email=t@e", "-c", "user.name=t", *args],
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    git("init", "-q")
    shutil.copy(
        HERE / "record_policy" / "ci_required.txt",
        repo / "docs/build/tools/record_policy/",
    )
    (repo / "docs/build/LEDGER.md").write_text(LEDGER.format(sha7=SHA_HEAD[:7]), encoding="utf-8")
    (repo / "docs/build/runs/P34.1.md").write_text(
        RUN_LEDGER.format(sha7=SHA_HEAD[:7]), encoding="utf-8"
    )
    git("add", "-A")
    git("commit", "-q", "-m", "base")
    stub = tmp_path / "gh"
    stub.write_text(f"#!{sys.executable}\n{STUB}", encoding="utf-8")
    stub.chmod(0o755)
    fixture = tmp_path / "fixture.json"

    class Env:
        root = repo

        def git(self, *a: str) -> str:
            return git(*a)

        def add_file(self, rel: str, text: str) -> None:
            p = repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
            git("add", "-A")
            git("commit", "-q", "-m", "add " + rel)

        def set(self, fx: dict) -> None:
            fixture.write_text(json.dumps(fx), encoding="utf-8")

        def run(self, *args: str) -> tuple[int, str, list[list[str]]]:
            proc = subprocess.run(
                [PYTHON, str(TOOL), "--repo", str(repo), "--gh", str(stub), *args],
                capture_output=True,
                text=True,
                env=dict(os.environ, GH_STUB=str(fixture)),
            )
            log = Path(str(fixture) + ".log")
            calls = [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
            if log.exists():
                log.unlink()
            return proc.returncode, proc.stdout + proc.stderr, calls

    return Env()


def fx(**kw: object) -> dict:
    d: dict = {"runs": _all_green_runs(), "check_runs": {SHA_HEAD[:7]: _check_runs(SHA_HEAD)}}
    d.update(kw)
    return d


# ── full-line verification (run ids bound to head + conclusion) ──────────────


def test_full_line_verified_green(env) -> None:
    env.add_file(
        "x.md",
        f"ci: pass #1@{SHA_HEAD[:7]} "
        "(python 36000001; docs 36000002; composed 36000003; "
        "security 36000004; web 36000005) · stack: #192 pass\n",
    )
    env.set(fx())
    base = env.git("rev-parse", "HEAD~1").strip()
    rc, out, calls = env.run("--diff-base", base)
    assert rc == 0 and "failures=0" in out
    assert ["api", "repos/{owner}/{repo}/actions/runs/36000001"] in calls


def test_run_head_sha_mismatch_fails(env) -> None:
    env.add_file("x.md", f"ci: pass #1@{SHA_HEAD[:7]} (python 36000001)\n")
    f = fx()
    f["runs"]["36000001"] = {"id": 36000001, "head_sha": SHA_OTHER, "conclusion": "success"}
    env.set(f)
    rc, out, _ = env.run("--diff-base", "HEAD~1")
    assert rc == 3 and "did not run on that sha" in out


def test_run_conclusion_mismatch_fails(env) -> None:
    env.add_file("x.md", f"ci: pass #1@{SHA_HEAD[:7]} (python 36000001)\n")
    f = fx()
    f["runs"]["36000001"] = {"id": 36000001, "head_sha": SHA_HEAD, "conclusion": "failure"}
    env.set(f)
    rc, out, _ = env.run("--diff-base", "HEAD~1")
    assert rc == 3 and "concluded `failure`" in out


def test_pass_after_rerun_line_verified(env) -> None:
    env.add_file(
        "x.md",
        f"ci: pass-after-rerun #1@{SHA_HEAD[:7]} "
        "(web a1 fail LH-PERF-1 run 36000006; a2 pass; docs 36000001)\n",
    )
    env.set(fx())
    rc, out, calls = env.run("--diff-base", "HEAD~1")
    assert rc == 0 and ["api", "repos/{owner}/{repo}/actions/runs/36000006"] in calls


# ── the done-entry rule and bare `ci:` fields ────────────────────────────────


def test_added_done_entry_without_ci_fails(env) -> None:
    env.add_file(
        "docs/build/LEDGER.md",
        LEDGER.format(sha7=SHA_HEAD[:7])
        + "\n- 2026-10-02 — P34.9 ticket — r11/y · PR #200 · landed\n",
    )
    env.set(fx())
    rc, out, _ = env.run("--diff-base", "HEAD~1")
    assert rc == 3 and "no ci: field" in out


def test_bare_field_verified_via_check_runs(env) -> None:
    """`ci: pass #N@sha` (no run ids) is verified against the sha's check-runs."""
    env.add_file("x.md", f"result: ci: pass #1@{SHA_HEAD[:7]}\n")
    env.set(fx())
    rc, out, _ = env.run("--diff-base", "HEAD~1")
    assert rc == 0, out


def test_bare_field_with_a_red_check_run_fails(env) -> None:
    env.add_file("x.md", f"ci: pass #1@{SHA_HEAD[:7]}\n")
    f = fx(check_runs={SHA_HEAD[:7]: _check_runs(SHA_HEAD, "failure")})
    env.set(f)
    rc, out, _ = env.run("--diff-base", "HEAD~1")
    assert rc == 3 and "completed/failure" in out


def test_unparseable_ci_fragment_fails(env) -> None:
    """On a record surface, a `ci:`-shaped fragment that is not a parseable
    field is a claim we cannot audit — red."""
    env.add_file("docs/build/runs/x.md", "ci: pass oops-not-a-record\n")
    env.set(fx())
    rc, out, _ = env.run("--diff-base", "HEAD~1")
    assert rc == 3 and "unparseable ci: fragment" in out


def test_ci_token_in_a_non_record_file_is_a_mention(env) -> None:
    """Outside the record surfaces (LEDGER, BUILD_INDEX, runs/) a `ci:` token is
    prose or code — a doc comment, a test literal, a template `#<n>@<sha>` —
    not a recorded claim."""
    env.add_file("notes.md", "docs: a bare `ci: pass #N@sha` re-reads check-runs\n")
    env.add_file("mod.py", 'S = "ci: pass #1@{SHA_HEAD[:7]}\\n"\n')
    env.set(fx())
    rc, out, _ = env.run("--diff-base", "HEAD~1")
    assert rc == 0, out


def test_non_done_entry_is_exempt(env) -> None:
    env.add_file(
        "docs/build/LEDGER.md",
        LEDGER.format(sha7=SHA_HEAD[:7])
        + "\n- 2026-10-02 — GATE-B pause — waiting on the operator\n",
    )
    env.set(fx())
    rc, out, _ = env.run("--diff-base", "HEAD~1")
    assert rc == 0, out


def test_correction_kind_entry_is_exempt(env) -> None:
    """A declared `correction` entry records a record event, not a head-bound
    CI read — no `ci:` field is owed even when the payload carries no
    pause/blocked marker (P34.27: the restoration corrections were flagged
    before the kind slot was consulted)."""
    env.add_file(
        "docs/build/LEDGER.md",
        LEDGER.format(sha7=SHA_HEAD[:7])
        + "\n- 2026-10-02 — P34.27 correction — restored the removed wording "
        "verbatim from 7671b511^; nothing is re-decided\n",
    )
    env.set(fx())
    rc, out, _ = env.run("--diff-base", "HEAD~1")
    assert rc == 0, out


def test_ticket_kind_mentioning_correction_still_owes_ci(env) -> None:
    """Kind, not vocabulary: a landing entry whose payload happens to contain
    the word 'correction' is still a `done`/`ticket` record and fails without
    a `ci:` field."""
    env.add_file(
        "docs/build/LEDGER.md",
        LEDGER.format(sha7=SHA_HEAD[:7])
        + "\n- 2026-10-02 — P34.9 ticket — r11/y · PR #200 · landed the "
        "append-only correction\n",
    )
    env.set(fx())
    rc, out, _ = env.run("--diff-base", "HEAD~1")
    assert rc == 3 and "no ci: field" in out


def test_post_closeout_record_still_owes_ci(env) -> None:
    """`post-closeout record` exists to record a head-bound read — exempting
    it would let a vacuous record pass."""
    env.add_file(
        "docs/build/LEDGER.md",
        LEDGER.format(sha7=SHA_HEAD[:7])
        + "\n- 2026-10-02 — P34.9 post-closeout record — closeout head "
        "deadbee 5/5 green\n",
    )
    env.set(fx())
    rc, out, _ = env.run("--diff-base", "HEAD~1")
    assert rc == 3 and "no ci: field" in out


# ── --all scope (nightly) ────────────────────────────────────────────────────


def test_all_scope_finds_the_section_under_its_real_heading(env) -> None:
    """The live heading carries a parenthetical (`## PHASE LOG — Round 11
    (append-only, newest last; the only append target)`); a section regex
    pinned to the bare text finds nothing and `--all` can only report
    vacuous — never a verification."""
    (env.root / "docs/build/LEDGER.md").write_text(
        LEDGER.format(sha7=SHA_HEAD[:7]).replace(
            "## PHASE LOG — Round 11\n",
            "## PHASE LOG — Round 11 (append-only, newest last; the only append target)\n",
        ),
        encoding="utf-8",
    )
    env.git("add", "-A")
    env.git("commit", "-q", "-m", "heading")
    env.set(fx())
    rc, out, _ = env.run("--all")
    assert rc == 0 and "candidates=2" in out, out


def test_all_scope_verifies_phase_log_and_run_ledger(env) -> None:
    env.set(fx())
    rc, out, calls = env.run("--all")
    assert rc == 0 and "candidates=2" in out, out
    # the run-ledger line's five runs AND the bare field's check-runs read
    assert any("/actions/runs/36000005" in " ".join(c) for c in calls)
    assert any("/check-runs" in " ".join(c) for c in calls)


def test_all_scope_fails_when_the_ledger_is_missing_entries(env) -> None:
    (env.root / "docs/build/LEDGER.md").write_text("# ledger\n", encoding="utf-8")
    env.git("add", "-A")
    env.git("commit", "-q", "-m", "x")
    env.set(fx())
    rc, out, _ = env.run("--all")
    assert rc == 3 and "vacuous" in out


def test_all_scope_flags_a_done_entry_without_ci(env) -> None:
    env.add_file(
        "docs/build/LEDGER.md",
        LEDGER.format(sha7=SHA_HEAD[:7]).replace(
            "- 2026-10-01 — GATE-P pause",
            "- 2026-10-02 — P34.3 ticket — claimed green with no record\n"
            "- 2026-10-01 — GATE-P pause",
        ),
    )
    env.set(fx())
    rc, out, _ = env.run("--all")
    assert rc == 3 and "no ci: field" in out


# ── unknown / gh errors ──────────────────────────────────────────────────────


def test_gh_missing_is_unknown(env, tmp_path: Path) -> None:
    env.set(fx())
    proc = subprocess.run(
        [
            PYTHON,
            str(TOOL),
            "--repo",
            str(env.root),
            "--gh",
            str(tmp_path / "no-gh"),
            "--all",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 5 and "not installed" in proc.stderr


def test_gh_api_error_is_unknown(env) -> None:
    env.add_file("x.md", f"ci: pass #1@{SHA_HEAD[:7]} (python 36000999)\n")
    env.set(fx())
    rc, out, _ = env.run("--diff-base", "HEAD~1")
    assert rc == 5 and "failed" in out


def test_json_record_written(env, tmp_path: Path) -> None:
    env.set(fx())
    out_json = tmp_path / "r.json"
    rc, out, _ = env.run("--all", "--json", str(out_json))
    assert rc == 0
    doc = json.loads(out_json.read_text())
    assert doc["schema"] == "recorded-ci-verify/1" and doc["candidates"] >= 1
