#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``ci_boundary.py`` (G3a; Round 11 Stage B, SEED-02b; B4 G3a, H2 §4).

Every test runs the real CLI against a **stubbed ``gh``**: a small script (written per test into
``tmp_path``) that answers ``gh pr view`` / ``gh pr list`` / ``gh api …/check-runs`` / ``gh run list``
from a JSON fixture and logs every call. No network is touched. Each test asserts a verdict, a recorded
line or a call-log fact that a no-op hook (exit 0, no record) cannot produce, so every test fails
against a no-op.

Run::

    uv run pytest docs/build/tools/test_ci_boundary.py -q
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
TOOL = HERE / "ci_boundary.py"
# The interpreter the tool runs under (default: this one). SIG_TOOLS_PYTHON=/usr/bin/python3 checks the
# oldest Python the skill may meet (macOS system Python 3.9).
PYTHON = os.environ.get("SIG_TOOLS_PYTHON") or sys.executable
REQUIRED = ["python", "docs", "composed", "security", "web"]

STUB = r'''
import json, os, re, sys
fx = json.load(open(os.environ["GH_STUB"]))
state_path = os.environ["GH_STUB"] + ".state"
state = json.load(open(state_path)) if os.path.exists(state_path) else {}
args = sys.argv[1:]
with open(os.environ["GH_STUB"] + ".log", "a") as log:
    log.write(json.dumps(args) + "\n")

def nth(key, seq):
    n = state.get(key, 0)
    state[key] = n + 1
    json.dump(state, open(state_path, "w"))
    return seq[min(n, len(seq) - 1)] if isinstance(seq, list) and seq and isinstance(seq[0], list) else seq

def fail(msg, code=1):
    sys.stderr.write(msg + "\n")
    sys.exit(code)

if fx.get("auth_error"):
    fail("To get started with GitHub CLI, please run:  gh auth login", 4)
flaky = fx.get("flaky", 0)
if flaky:
    n = state.get("flaky", 0)
    state["flaky"] = n + 1
    json.dump(state, open(state_path, "w"))
    if flaky < 0 or n < flaky:
        fail("HTTP 502: Bad Gateway (https://api.github.com/graphql)")

def pr_state(num, advance):
    """A PR fixture may be a list of successive states; every read (view or list) takes the next."""
    v = fx["prs"][num]
    if not isinstance(v, list):
        return v
    n = state.get("pr" + num, 0)
    if advance:
        state["pr" + num] = n + 1
        json.dump(state, open(state_path, "w"))
    return v[min(n, len(v) - 1)]

if args[:2] == ["pr", "view"]:
    if args[2] not in fx["prs"]:
        fail(f"GraphQL: Could not resolve to a PullRequest with the number of {args[2]}.")
    print(json.dumps(pr_state(args[2], True)))
elif args[:2] == ["pr", "list"]:
    head = args[args.index("--head") + 1]
    st = args[args.index("--state") + 1]
    out = []
    for num in fx["prs"]:
        p = pr_state(num, False)
        if p["headRefName"] == head and (st == "all" or p["state"] == st.upper()):
            out.append(pr_state(num, True))
    print(json.dumps(out))
elif args[:1] == ["api"] and "/check-runs/" in args[1] and args[1].endswith("/annotations"):
    cid = re.search(r"check-runs/(\d+)/", args[1]).group(1)
    print(json.dumps(fx.get("annotations", {}).get(cid, [])))
elif args[:1] == ["api"] and "/commits/" in args[1] and "/check-runs" in args[1]:
    assert "--paginate" in args, args
    assert args[1].startswith("repos/{owner}/{repo}/"), args
    sha = re.search(r"commits/([0-9a-f]+)/check-runs", args[1]).group(1)
    runs = nth("cr" + sha, fx.get("check_runs", {}).get(sha, []))
    half = len(runs) // 2  # two pages, printed back to back as `gh api --paginate` does
    print(json.dumps({"total_count": len(runs), "check_runs": runs[:half]}), end="")
    print(json.dumps({"total_count": len(runs), "check_runs": runs[half:]}))
elif args[:2] == ["run", "list"]:
    sha = args[args.index("--commit") + 1]
    print(json.dumps(fx.get("runs", {}).get(sha, [])))
else:
    fail("stub: unexpected gh call " + " ".join(args), 2)
'''

SHA_SEED = "a" * 40
SHA_T1 = "b" * 40
SHA_190 = "c" * 40
SHA_185 = "d" * 40


def pr(number: int, head: str, sha: str, base: str, **kw: object) -> dict[str, object]:
    d: dict[str, object] = {
        "number": number,
        "state": "OPEN",
        "isDraft": False,
        "headRefOid": sha,
        "headRefName": head,
        "baseRefName": base,
        "mergeable": "MERGEABLE",
        "url": f"https://github.com/o/r/pull/{number}",
    }
    d.update(kw)
    return d


def runs(sha: str, base_id: int, **override: tuple[str, str | None]) -> list[dict[str, object]]:
    """Five required check-runs (all green unless overridden: name -> (status, conclusion))."""
    out = []
    for k, name in enumerate(REQUIRED):
        status, concl = override.get(name, ("completed", "success"))
        out.append(
            {
                "id": base_id + k,
                "name": name,
                "head_sha": sha,
                "status": status,
                "conclusion": concl,
                "started_at": "2026-10-01T10:00:00Z",
                "completed_at": "2026-10-01T10:08:00Z" if status == "completed" else None,
                "details_url": f"https://github.com/o/r/actions/runs/{9000 + base_id}/job/{base_id + k}",
                "app": {"slug": "github-actions"},
            }
        )
    return out


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.email=t@example.invalid", "-c", "user.name=t", *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


LEDGER = """# ledger

## CURRENT STATE

```
nextTicket:      P34.2
lastCompleted:   P34.1
chainTip:        r11/p34-1   # the Round-11 chain tip
```

## GATE DECISIONS

| date | gate | question | answer | decided by | consequence | kind |
|---|---|---|---|---|---|---|
{waivers}
## PHASE LOG — Round 11

- 2026-10-01 — P34.1 done — PR #202
"""


@pytest.fixture
def env(tmp_path: Path):
    """A throw-away repo with the hook's inputs, the stub gh, and a runner."""
    repo = tmp_path / "repo"
    (repo / "docs/build/tools/record_policy").mkdir(parents=True)
    git(repo, "init", "-q")
    shutil.copy(
        HERE / "record_policy" / "ci_required.txt", repo / "docs/build/tools/record_policy/"
    )
    (repo / "docs/build/LEDGER.md").write_text(LEDGER.format(waivers=""), encoding="utf-8")
    (repo / "README").write_text("x\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    head = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "branch", "r11/p34-1", head)
    git(repo, "branch", "r11/seed", head)
    stub = tmp_path / "gh"
    stub.write_text(f"#!{sys.executable}\n{STUB}", encoding="utf-8")
    stub.chmod(0o755)
    fixture = tmp_path / "fixture.json"

    class Env:
        root = repo
        local = head
        fx = fixture

        def set(self, fx: dict[str, object]) -> None:
            fixture.write_text(json.dumps(fx), encoding="utf-8")

        def ledger(self, waiver_rows: str = "", tip: str = "r11/p34-1") -> None:
            text = LEDGER.format(waivers=waiver_rows).replace("r11/p34-1   #", f"{tip}   #")
            (repo / "docs/build/LEDGER.md").write_text(text, encoding="utf-8")

        def run(self, *args: str, gh: str | None = None) -> tuple[int, dict, str, list[list[str]]]:
            out = tmp_path / "ci.json"
            if out.exists():
                out.unlink()
            proc = subprocess.run(
                [
                    PYTHON,
                    str(TOOL),
                    "--json",
                    str(out),
                    "--repo",
                    str(repo),
                    "--gh",
                    gh or str(stub),
                    "--backoff",
                    "0,0,0",
                    *args,
                ],
                capture_output=True,
                text=True,
                env=dict(os.environ, GH_STUB=str(fixture)),
            )
            log = tmp_path / "fixture.json.log"
            calls = [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
            doc = json.loads(out.read_text()) if out.exists() else {}
            last = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
            return proc.returncode, doc, last, calls

    return Env()


def standard(local: str, **t1_override: tuple[str, str | None]) -> dict[str, object]:
    """#202 (r11/p34-1, at the local branch head) on #201 (r11/seed) on #190 (Round 10, red at #185)."""
    return {
        "prs": {
            "202": pr(202, "r11/p34-1", local, "r11/seed"),
            "201": pr(201, "r11/seed", SHA_SEED, "devin/p33-8-agent-docs-refresh"),
            "190": pr(
                190, "devin/p33-8-agent-docs-refresh", SHA_190, "devin/p33-7-repo-docs-refresh"
            ),
            "185": pr(185, "devin/p33-3-capstone-closure", SHA_185, "devin/p33-2-x"),
        },
        "check_runs": {
            local: runs(local, 100, **t1_override),
            SHA_SEED: runs(SHA_SEED, 200),
            SHA_190: runs(SHA_190, 300),
            SHA_185: runs(SHA_185, 400, python=("completed", "failure")),
        },
        "annotations": {
            "104": [{"annotation_level": "failure", "message": "Performance budgets: score 0.81"}]
        },
    }


def named_prs(calls: list[list[str]]) -> set[str]:
    """Every PR number or branch a gh call named."""
    seen: set[str] = set()
    for c in calls:
        if c[:2] == ["pr", "view"]:
            seen.add(c[2])
        if c[:2] == ["pr", "list"]:
            seen.add(c[c.index("--head") + 1])
    return seen


# ── pass, scope, head binding ───────────────────────────────────────────────


def test_green_stack_passes_and_never_reads_the_round10_stack(env) -> None:
    env.set(standard(env.local))
    rc, doc, line, calls = env.run("--pr", "202", "--no-wait")
    assert rc == 0, line
    assert line == (
        f"ci: pass #202@{env.local[:7]} (python 9100; docs 9100; composed 9100; security 9100; web 9100)"
        " · stack: #201 pass"
    )
    assert doc["schema"] == "ci-boundary/1" and doc["state"] == "pass" and doc["exit"] == 0
    assert [s["pr"] for s in doc["stack"]] == [202, 201]
    assert "outside the `r11/` scope" in doc["stack_stop"]
    assert doc["local_head"] == env.local and len(doc["stack_digest"]) == 64
    assert {c["name"] for c in doc["checks"] if c["pr"] == 202 and c["bucket"] == "pass"} == set(
        REQUIRED
    )
    # head-bound reads only; #190 / #185 (and their branches) are never named in any gh call
    shas = {
        c[1].split("/commits/")[1].split("/")[0]
        for c in calls
        if c[:1] == ["api"] and "/commits/" in c[1]
    }
    assert shas == {env.local, SHA_SEED}
    assert not named_prs(calls) & {"190", "185", "devin/p33-7-repo-docs-refresh", "devin/p33-2-x"}
    assert not any(c[:2] == ["pr", "checks"] for c in calls)


def test_out_of_scope_pr_reads_the_chain_tip_pr_instead(env) -> None:
    """At the first boundary `lastCompleted` is P33.8 → #190: never read; the chainTip PR is."""
    env.ledger(tip="r11/seed")
    fx = standard(env.local)
    fx["prs"]["201"] = pr(201, "r11/seed", env.local, "devin/p33-8-agent-docs-refresh")
    fx["check_runs"][env.local] = runs(env.local, 500)
    env.set(fx)
    rc, doc, line, calls = env.run("--pr", "190", "--no-wait")
    assert rc == 0 and doc["pr"] == 201 and doc["requested_pr"] == 190, line
    assert line.endswith("· requested #190 out of scope (B-15)") and line.startswith(
        "ci: pass #201@"
    )
    assert "190" not in named_prs(calls)


def test_out_of_scope_pr_without_an_r11_chain_tip_is_unknown(env) -> None:
    env.ledger(tip="devin/p33-8-agent-docs-refresh")
    env.set(standard(env.local))
    rc, doc, line, _ = env.run("--pr", "190", "--no-wait")
    assert rc == 5 and doc["state"] == "unknown" and "outside the r11/ scope" in line


def test_a_non_r11_head_is_out_of_scope_even_outside_141_190(env) -> None:
    env.ledger(tip="devin/p33-8-agent-docs-refresh")
    fx = standard(env.local)
    fx["prs"]["300"] = pr(300, "feature/x", env.local, "main")
    env.set(fx)
    rc, _, line, _ = env.run("--pr", "300", "--no-wait")
    assert rc == 5 and "#300 is outside the r11/ scope" in line


def test_checks_of_a_superseded_head_never_count(env) -> None:
    """Green check-runs exist only for an older sha; the PR head has none → never green."""
    fx = standard(env.local)
    fx["check_runs"] = {"e" * 40: runs("e" * 40, 100), SHA_SEED: runs(SHA_SEED, 200)}
    env.set(fx)
    rc, doc, line, _ = env.run("--pr", "202", "--no-wait")
    assert (
        rc == 4
        and doc["state"] == "pending"
        and "(python): required check not reported yet" in line
    )


def test_local_branch_behind_or_ahead_of_the_pr_head_is_red(env) -> None:
    fx = standard(env.local)
    fx["prs"]["202"] = pr(202, "r11/p34-1", SHA_T1, "r11/seed")
    fx["check_runs"][SHA_T1] = runs(SHA_T1, 100)
    env.set(fx)
    rc, doc, line, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 3 and doc["kind"] == "stack" and f"local `r11/p34-1` is at {env.local[:7]}" in line


def test_head_moving_during_the_read_is_red(env) -> None:
    fx = standard(env.local)
    fx["prs"]["201"] = [
        pr(201, "r11/seed", SHA_SEED, "devin/p33-8-agent-docs-refresh"),
        pr(201, "r11/seed", "f" * 40, "devin/p33-8-agent-docs-refresh"),
    ]
    env.set(fx)
    rc, _, line, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 3 and "#201 head moved aaaaaaa → fffffff during the read" in line


def test_only_github_actions_runs_and_the_latest_attempt_count(env) -> None:
    fx = standard(env.local)
    rs = runs(env.local, 100)
    # an older failed attempt of `docs` (lower id) is superseded by the green re-run
    rs.append({**rs[1], "id": 50, "conclusion": "failure"})
    # a third-party app reporting a check named `web` does not satisfy the required job
    rs[4] = {**rs[4], "app": {"slug": "some-other-app"}}
    fx["check_runs"][env.local] = rs
    env.set(fx)
    rc, doc, line, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 4 and "(web): required check not reported yet" in line
    docs = [c for c in doc["checks"] if c["name"] == "docs" and c["pr"] == 202]
    assert docs[0]["check_run_id"] == 101 and docs[0]["bucket"] == "pass"


def test_newer_failed_attempt_wins_over_an_older_success(env) -> None:
    fx = standard(env.local)
    rs = runs(env.local, 100)
    rs.append({**rs[0], "id": 999, "conclusion": "failure"})
    fx["check_runs"][env.local] = rs
    env.set(fx)
    rc, _, line, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 3 and "(python): failure" in line


# ── red, pending, missing ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "concl,kind",
    [
        ("failure", "fail"),
        ("cancelled", "cancel"),
        ("skipped", "fail"),
        ("timed_out", "fail"),
        ("neutral", "fail"),
        ("startup_failure", "fail"),
        ("action_required", "fail"),
    ],
)
def test_every_non_success_conclusion_is_red(env, concl: str, kind: str) -> None:
    env.set(standard(env.local, web=("completed", concl)))
    rc, doc, line, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 3 and doc["kind"] == kind
    assert line.startswith(f"blockedOn: CI {kind} on #202@{env.local[:7]} (web): {concl}")


def test_failure_line_carries_the_annotation_and_run_id(env) -> None:
    env.set(standard(env.local, web=("completed", "failure")))
    rc, _, line, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 3
    assert line == (
        f"blockedOn: CI fail on #202@{env.local[:7]} (web): failure — Performance budgets: score 0.81 (run 9100)"
    )


def test_red_ancestor_blocks_and_is_named(env) -> None:
    fx = standard(env.local)
    fx["check_runs"][SHA_SEED] = runs(SHA_SEED, 200, docs=("completed", "failure"))
    env.set(fx)
    rc, doc, line, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 3 and line.startswith(f"blockedOn: CI fail on #201@{SHA_SEED[:7]} (docs): failure")
    assert [s["state"] for s in doc["stack"]] == ["pass", "fail"]


@pytest.mark.parametrize(
    "override,kind,text",
    [
        ({"isDraft": True}, "stack", "#202 is a draft"),
        ({"mergeable": "CONFLICTING"}, "conflict", "#202 conflicts with `r11/seed`"),
        ({"state": "CLOSED"}, "stack", "#202 is closed"),
    ],
)
def test_draft_conflicting_or_closed_pr_is_red(env, override: dict, kind: str, text: str) -> None:
    fx = standard(env.local)
    fx["prs"]["202"] = pr(202, "r11/p34-1", env.local, "r11/seed", **override)
    env.set(fx)
    rc, doc, line, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 3 and doc["kind"] == kind and text in line


def test_stack_gap_is_red(env) -> None:
    fx = standard(env.local)
    del fx["prs"]["201"]
    env.set(fx)
    rc, _, line, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 3 and "stack gap: base `r11/seed` of #202 has no open PR" in line


def test_merged_ancestor_ends_the_walk(env) -> None:
    fx = standard(env.local)
    fx["prs"]["201"] = pr(
        201, "r11/seed", SHA_SEED, "devin/p33-8-agent-docs-refresh", state="MERGED"
    )
    env.set(fx)
    rc, doc, _, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 0 and doc["stack_stop"] == "base `r11/seed` is #201, already merged"
    assert [s["pr"] for s in doc["stack"]] == [202]


def test_in_progress_is_pending_on_a_single_read(env) -> None:
    env.set(standard(env.local, composed=("in_progress", None)))
    rc, doc, line, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 4 and doc["state"] == "pending" and "(composed): in_progress" in line


def test_pending_then_green_on_the_next_poll(env) -> None:
    fx = standard(env.local)
    fx["check_runs"][env.local] = [runs(env.local, 100, web=("queued", None)), runs(env.local, 100)]
    env.set(fx)
    rc, doc, line, _ = env.run("--pr", "202", "--interval", "0.05", "--max-wait", "30")
    assert rc == 0 and doc["polls"] == 2 and line.startswith("ci: pass #202@")


def test_still_pending_at_the_deadline_exits_4(env) -> None:
    env.set(standard(env.local, web=("queued", None)))
    rc, doc, line, _ = env.run("--pr", "202", "--interval", "0.1", "--max-wait", "0.3")
    assert rc == 4 and doc["polls"] >= 2 and "(web): queued after" in line


def test_missing_required_check_after_the_wait_is_red_unless_a_run_is_queued(env) -> None:
    fx = standard(env.local)
    fx["check_runs"][env.local] = runs(env.local, 100)[:4]  # `web` never reported
    env.set(fx)
    rc, doc, line, _ = env.run("--pr", "202", "--interval", "0.05", "--max-wait", "0.1")
    assert rc == 3 and doc["kind"] == "missing" and "(web): required check missing" in line
    fx["runs"] = {env.local: [{"databaseId": 77, "status": "queued", "workflowName": "CI"}]}
    env.set(fx)
    rc2, _, line2, _ = env.run("--pr", "202", "--interval", "0.05", "--max-wait", "0.1")
    assert rc2 == 4 and "workflow run 77 is queued" in line2


def test_missing_after_the_grace_with_no_workflow_run_is_red_before_the_deadline(env) -> None:
    fx = standard(env.local)
    fx["check_runs"][env.local] = runs(env.local, 100)[:4]
    env.set(fx)
    rc, doc, _, _ = env.run("--pr", "202", "--interval", "0.05", "--max-wait", "60", "--grace", "0")
    assert rc == 3 and doc["kind"] == "missing" and doc["polls"] == 1


# ── required set and waivers ────────────────────────────────────────────────


def test_required_set_comes_from_ci_required_txt(env) -> None:
    (env.root / "docs/build/tools/record_policy/ci_required.txt").write_text(
        "# two only\npython\ndocs\n"
    )
    env.set(standard(env.local, web=("completed", "failure")))
    rc, doc, line, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 0 and doc["required"] == ["python", "docs"]
    assert "(python 9100; docs 9100)" in line
    web = [c for c in doc["checks"] if c["name"] == "web" and c["pr"] == 202]
    assert web[0]["required"] is False


def test_unreadable_required_set_is_unknown(env) -> None:
    (env.root / "docs/build/tools/record_policy/ci_required.txt").write_text("# none\n")
    env.set(standard(env.local))
    rc, doc, line, calls = env.run("--pr", "202", "--no-wait")
    assert rc == 5 and doc["state"] == "unknown" and "ci_required.txt" in line and calls == []


def test_operator_waiver_names_the_pr_and_the_check(env) -> None:
    row = (
        '| 2026-10-01T12:00:00Z | P34.1 | web red on #202 | "waive web on #202 for this boundary" '
        "| operator | carry | waiver |\n"
    )
    env.ledger(waiver_rows=row)
    env.set(standard(env.local, web=("completed", "failure")))
    rc, doc, line, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 0 and "web waived" in line and doc["waivers"] == 1
    env.ledger(waiver_rows=row.replace("#202", "#203"))
    rc2, _, line2, _ = env.run("--pr", "202", "--no-wait")
    assert rc2 == 3 and "(web): failure" in line2


# ── gh failures, usage ──────────────────────────────────────────────────────


def test_gh_not_installed_is_unknown(env, tmp_path: Path) -> None:
    env.set(standard(env.local))
    rc, doc, line, _ = env.run("--pr", "202", "--no-wait", gh=str(tmp_path / "no-such-gh"))
    assert rc == 5 and doc["kind"] == "unavailable" and "gh is not installed" in line


def test_gh_unauthenticated_is_unknown_without_retries(env) -> None:
    fx = standard(env.local)
    fx["auth_error"] = True
    env.set(fx)
    rc, _, line, calls = env.run("--pr", "202", "--no-wait")
    assert rc == 5 and "not authenticated" in line and len(calls) == 1


def test_transient_gh_errors_are_retried_then_unknown(env) -> None:
    fx = standard(env.local)
    fx["flaky"] = 2
    env.set(fx)
    rc, _, line, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 0 and line.startswith("ci: pass")
    fx["flaky"] = -1  # always failing
    env.set(fx)
    (env.fx.parent / "fixture.json.state").unlink()
    (env.fx.parent / "fixture.json.log").unlink()
    rc2, _, line2, calls2 = env.run("--pr", "202", "--no-wait")
    assert rc2 == 5 and "failed 4×" in line2 and len(calls2) == 4


@pytest.mark.parametrize("argv", [[], ["--pr", "abc"], ["--pr", "202", "--interval", "-1"]])
def test_usage_errors_exit_1(argv: list[str], tmp_path: Path) -> None:
    proc = subprocess.run(
        [PYTHON, str(TOOL), "--json", str(tmp_path / "x.json"), *argv],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1 and not (tmp_path / "x.json").exists()


def test_ledger_parsers() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("ci_boundary", TOOL)
    assert spec is not None and spec.loader is not None
    cb = importlib.util.module_from_spec(spec)
    sys.modules["ci_boundary"] = cb
    spec.loader.exec_module(cb)
    text = (
        LEDGER.format(
            waivers='| 2026-10-01T12:00:00Z | g | q | "waive docs" | operator | c | waiver |\n'
        )
        + "\n## GATE DECISIONS (legacy)\n\n| date | gate | q | a | by | consequence |\n|---|---|---|---|---|---|\n"
        + ("| 2026-09-01 | g | q | a waiver | op | waiver |\n")
    )
    assert cb.ledger_value(text, "chainTip") == "r11/p34-1"
    assert len(cb.ledger_waivers(text)) == 1  # the legacy 6-column table is not a waiver source
    assert cb.waived(["| … #202 … web … | waiver |"], 202, "web")
    assert not cb.waived(["| … #2021 … web … | waiver |"], 202, "web")
    assert not cb.waived(["| … #202 … web-perf … | waiver |"], 202, "web")
