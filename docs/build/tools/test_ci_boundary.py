#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``ci_boundary.py`` (G3a; Round 11 Stage B, SEED-02b; B4 G3a, H2 §4).

Every test runs the real CLI against a **stubbed ``gh``**: a small script (written per test into
``tmp_path``) that answers ``gh pr view`` / ``gh pr list`` / ``gh api …/check-runs`` /
``gh run list`` from a JSON fixture and logs every call. No network is touched. Each test
asserts a verdict, a recorded
line or a call-log fact that a no-op hook (exit 0, no record) cannot produce, so every test fails
against a no-op.

Run::

    uv run pytest docs/build/tools/test_ci_boundary.py -q
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TOOL = HERE / "ci_boundary.py"
# The interpreter the tool runs under (default: this one). SIG_TOOLS_PYTHON=/usr/bin/python3
# checks the oldest Python the skill may meet (macOS system Python 3.9).
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
    if isinstance(seq, list) and seq and isinstance(seq[0], list):
        return seq[min(n, len(seq) - 1)]
    return seq

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
    st = args[args.index("--state") + 1]
    if "--head" in args:
        head = args[args.index("--head") + 1]
        out = []
        for num in fx["prs"]:
            p = pr_state(num, False)
            if p["headRefName"] == head and (st == "all" or p["state"] == st.upper()):
                out.append(pr_state(num, True))
    elif st == "merged":
        out = fx.get("merged_prs", [])
    else:
        out = fx.get("open_prs", [
            pr_state(num, False) for num in fx["prs"] if pr_state(num, False)["state"] == "OPEN"
        ])
    print(json.dumps(out))
elif args[:2] == ["run", "rerun"]:
    # The one permitted GitHub write (B-15): record it; a fixture's `post_rerun`
    # map gives the check-runs a sha reports after its failed jobs re-ran.
    rid = args[-1]
    state.setdefault("reruns", []).append(rid)
    json.dump(state, open(state_path, "w"))
    print("{}")
elif args[:1] == ["api"] and "/check-runs/" in args[1] and args[1].endswith("/annotations"):
    cid = re.search(r"check-runs/(\d+)/", args[1]).group(1)
    print(json.dumps(fx.get("annotations", {}).get(cid, [])))
elif args[:1] == ["api"] and "/commits/" in args[1] and "/check-runs" in args[1]:
    assert "--paginate" in args, args
    assert args[1].startswith("repos/{owner}/{repo}/"), args
    sha = re.search(r"commits/([0-9a-f]+)/check-runs", args[1]).group(1)
    if state.get("reruns") and sha in fx.get("post_rerun", {}):
        runs = nth("cr" + sha, fx["post_rerun"][sha])
    else:
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
                "details_url": (
                    f"https://github.com/o/r/actions/runs/{9000 + base_id}/job/{base_id + k}"
                ),
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
## PHASE LOG — Round 11 (append-only, newest last; the only append target)

- 2026-10-01 — P34.1 done — PR #202
{phase_entry}"""


@pytest.fixture
def env(tmp_path: Path):
    """A throw-away repo with the hook's inputs, the stub gh, and a runner."""
    repo = tmp_path / "repo"
    (repo / "docs/build/tools/record_policy").mkdir(parents=True)
    git(repo, "init", "-q")
    shutil.copy(
        HERE / "record_policy" / "ci_required.txt", repo / "docs/build/tools/record_policy/"
    )
    # An empty allow-list: no failure is a flake unless a test writes one (the real
    # policy is exercised by the flake tests, which write their own entries).
    (repo / "docs/build/tools/record_policy/ci_flakes.toml").write_text(
        "# test fixture allow-list — empty\n", encoding="utf-8"
    )
    (repo / "docs/build/LEDGER.md").write_text(
        LEDGER.format(waivers="", phase_entry=""), encoding="utf-8"
    )
    (repo / "README").write_text("x\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    head = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "branch", "r11/p34-1", head)
    git(repo, "branch", "r11/seed", head)
    # G3c: the chain must descend from origin/main — the worktree's remote-tracking ref.
    git(repo, "update-ref", "refs/remotes/origin/main", head)
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

        def ledger(
            self,
            waiver_rows: str = "",
            tip: str = "r11/p34-1",
            phase_entry: str = "",
        ) -> None:
            text = LEDGER.format(waivers=waiver_rows, phase_entry=phase_entry).replace(
                "r11/p34-1   #", f"{tip}   #"
            )
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
    """#202 (r11/p34-1, at the local branch head) on #201 (r11/seed) on #190
    (Round 10, red at #185)."""
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
        if c[:2] == ["pr", "list"] and "--head" in c:
            seen.add(c[c.index("--head") + 1])
    return seen


# ── pass, scope, head binding ───────────────────────────────────────────────


def test_green_stack_passes_and_never_reads_the_round10_stack(env) -> None:
    env.set(standard(env.local))
    rc, doc, line, calls = env.run("--pr", "202", "--no-wait")
    assert rc == 0, line
    assert line == (
        f"ci: pass #202@{env.local[:7]} (python 9100; docs 9100; composed 9100; "
        "security 9100; web 9100)"
        " · stack: #201 pass"
        f" · main: {env.local[:7]} descends:yes merges:0 open-other:2"
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
    assert "· requested #190 out of scope (B-15) · main: " in line and line.startswith(
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
        f"blockedOn: CI fail on #202@{env.local[:7]} (web): failure — "
        "Performance budgets: score 0.81 (run 9100)"
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


# ── P34.2: flake allow-list + one re-run per head (CI-5, B-15) ──────────────

FLAKE_WEB = """[[flake]]
id = "LH-PERF-1"
job = "web"
step = "Performance budgets (build fails on regression)"
pattern = "Performance budgets.*score"
evidence_runs = ["35051006427"]
reason = "single-run perf noise"
tracking = "P34.2"
expires = "2099-01-01"
"""


def _flakes(env, text: str) -> None:
    (env.root / "docs/build/tools/record_policy/ci_flakes.toml").write_text(text, encoding="utf-8")


def _rerun_calls(calls: list[list[str]]) -> list[list[str]]:
    return [c for c in calls if c[:2] == ["run", "rerun"]]


def test_allow_listed_flake_gets_exactly_one_rerun_and_both_attempts_logged(env) -> None:
    """CI-5: the failing `web` run matches LH-PERF-1 → one `gh run rerun --failed`,
    both attempts in flake_log.csv, and the line reads pass-after-rerun."""
    _flakes(env, FLAKE_WEB)
    fx = standard(env.local, web=("completed", "failure"))
    fx["post_rerun"] = {env.local: [runs(env.local, 100)]}
    env.set(fx)
    rc, doc, line, calls = env.run("--pr", "202", "--interval", "0.05", "--max-wait", "30")
    assert rc == 0 and line.startswith("ci: pass-after-rerun #202@"), line
    assert f"web a1 fail LH-PERF-1 run {100 + 9000}" in line and "a2 pass" in line
    assert _rerun_calls(calls) == [["run", "rerun", "--failed", "9100"]]
    assert doc["reruns"] == [
        {
            "pr": 202,
            "check": "web",
            "flake_id": "LH-PERF-1",
            "run_id": "9100",
            "at": doc["reruns"][0]["at"],
        }
    ]
    log = (env.root / "docs/build/reports/ci/flake_log.csv").read_text()
    rows = log.strip().splitlines()
    assert rows[0].startswith("date,pr,head_sha") and len(rows) == 3
    assert f"202,{env.local},web,LH-PERF-1,9100,1,failure" in rows[1]
    assert rows[2].endswith(",2,rerun-requested")


def test_a_second_flake_failure_on_the_head_is_red_not_rerun(env) -> None:
    """One re-run per head: a head that already used it gets flake-exhausted red."""
    _flakes(env, FLAKE_WEB)
    fx = standard(env.local, web=("completed", "failure"))
    # The durable log already holds this head's re-run (an earlier boundary took it).
    env.run  # noqa: B018
    log_path = env.root / "docs/build/reports/ci/flake_log.csv"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "date,pr,head_sha,check,flake_id,run_id,attempt,outcome\n"
        f"2026-10-01T00:00:00Z,202,{env.local},web,LH-PERF-1,9000,1,failure\n"
        f"2026-10-01T00:01:00Z,202,{env.local},web,LH-PERF-1,9000,2,rerun-requested\n"
    )
    env.set(fx)
    rc, doc, line, calls = env.run("--pr", "202", "--no-wait")
    assert rc == 3 and "flake-exhausted" in line and "LH-PERF-1" in line
    assert _rerun_calls(calls) == []


def test_a_failure_off_the_allow_list_is_never_rerun(env) -> None:
    """A planted failure that matches no unexpired entry stays red — no gh write."""
    _flakes(env, FLAKE_WEB)
    env.set(standard(env.local, python=("completed", "failure")))
    rc, _, line, calls = env.run("--pr", "202", "--no-wait")
    assert rc == 3 and "(python): failure" in line and _rerun_calls(calls) == []


def test_an_expired_flake_entry_matches_nothing(env) -> None:
    _flakes(env, FLAKE_WEB.replace("2099-01-01", "2020-01-01"))
    env.set(standard(env.local, web=("completed", "failure")))
    rc, _, line, calls = env.run("--pr", "202", "--no-wait")
    assert rc == 3 and "(web): failure" in line and _rerun_calls(calls) == []


def test_a_flake_red_alongside_a_real_red_is_not_rerun(env) -> None:
    """The one re-run covers allow-listed flakes only: a real failure on the same
    head means no re-run is taken and the real failure is the reported one."""
    _flakes(env, FLAKE_WEB)
    fx = standard(env.local, web=("completed", "failure"), docs=("completed", "failure"))
    env.set(fx)
    rc, _, line, calls = env.run("--pr", "202", "--no-wait")
    assert rc == 3 and "(docs): failure" in line and _rerun_calls(calls) == []


def test_no_rerun_flag_disables_the_one_rerun(env) -> None:
    _flakes(env, FLAKE_WEB)
    env.set(standard(env.local, web=("completed", "failure")))
    rc, _, line, calls = env.run("--pr", "202", "--no-wait", "--no-rerun")
    assert rc == 3 and "(web): failure" in line and _rerun_calls(calls) == []


def test_malformed_flake_policy_is_unknown_not_vacuous(env) -> None:
    (env.root / "docs/build/tools/record_policy/ci_flakes.toml").write_text(
        '[[flake]]\njob = "web"\n',
        encoding="utf-8",  # missing id/pattern/expires
    )
    env.set(standard(env.local, web=("completed", "failure")))
    rc, doc, line, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 5 and doc["state"] == "unknown" and "ci_flakes.toml" in line


def test_committed_ci_flakes_toml_parses(env) -> None:
    """The shipped allow-list parses under the tool's own minimal reader (3.9-safe)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("ci_boundary", TOOL)
    assert spec is not None and spec.loader is not None
    cb = importlib.util.module_from_spec(spec)
    sys.modules["ci_boundary"] = cb
    spec.loader.exec_module(cb)
    flakes = cb.parse_flakes((HERE / "record_policy/ci_flakes.toml").read_text(encoding="utf-8"))
    by_id = {f.id: f for f in flakes}
    assert {"LH-PERF-1", "PY-SUBSTR-1"} <= set(by_id), "the two known flakes are listed"
    assert by_id["LH-PERF-1"].job == "web" and by_id["PY-SUBSTR-1"].job == "python"
    assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", f.expires) for f in flakes)


# ── P34.2: G3c external delta (OM-03/OM-17) ──────────────────────────────────


def test_external_delta_fields_are_recorded_and_in_the_line(env) -> None:
    env.set(standard(env.local))
    rc, doc, line, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 0, line
    ext = doc["external"]
    assert ext["main_sha"] == env.local and ext["chain_descends"] is True
    assert ext["merged_since"] == [] and ext["since"] == "2026-10-01"
    assert {p["number"] for p in ext["open_off_chain"]} == {190, 185}
    # SHA_SEED is a fixture sha, not a local object — honestly "unverifiable", never claimed.
    assert ext["ancestry"] == [
        {
            "child": 202,
            "parent": 201,
            "ancestor": None,
            "note": "parent head not resolvable locally",
        }
    ]
    assert f" · main: {env.local[:7]} descends:yes merges:0 open-other:2" in line


def test_off_stack_merge_since_the_last_boundary_is_red(env) -> None:
    fx = standard(env.local)
    fx["merged_prs"] = [
        {
            "number": 555,
            "headRefName": "someone/hotfix",
            "headRefOid": "e" * 40,
            "baseRefName": "main",
            "mergedAt": "2026-10-01T12:00:00Z",
        }
    ]
    env.set(fx)
    rc, doc, line, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 3 and doc["kind"] == "stack" and "off-stack merge #555" in line
    assert doc["external"]["merged_since"][0]["on_stack"] is False


def test_a_chain_merge_is_recorded_not_blocked(env) -> None:
    """An `r11/` PR merged since the last boundary is a chain row — recorded, not red."""
    fx = standard(env.local)
    fx["merged_prs"] = [
        {
            "number": 199,
            "headRefName": "r11/p34-0",
            "headRefOid": "f" * 40,
            "baseRefName": "main",
            "mergedAt": "2026-10-01T12:00:00Z",
        }
    ]
    env.set(fx)
    rc, doc, line, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 0 and doc["external"]["merged_since"][0]["on_stack"] is True
    assert "merges:1" in line


def test_a_tip_not_descending_from_main_is_recorded(env) -> None:
    """chain_descends: false is *recorded* (`descends:no`), not a red — the
    operator merges the chain late, so the tip normally trails main's head.
    The red conditions are an off-stack merge in the window and a broken stack
    link (OM-03/OM-17)."""
    env.set(standard(env.local))
    # Move origin/main to a commit the tip does not contain.
    git(env.root, "checkout", "-q", "--orphan", "other-root")
    git(env.root, "commit", "-q", "-m", "foreign root")
    other = git(env.root, "rev-parse", "HEAD").strip()
    git(env.root, "update-ref", "refs/remotes/origin/main", other)
    git(env.root, "checkout", "-q", "r11/p34-1")
    rc, doc, line, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 0, line
    assert doc["external"]["chain_descends"] is False
    assert "descends:no" in line and "blockedOn" not in line


def test_a_merge_before_the_boundary_timestamp_is_not_since_it(env) -> None:
    """The merge window is a timestamp, not a date: when the last PHASE LOG
    entry names its boundary time, a merge earlier that day predates it and is
    not part of the delta (the contract's 'since the last boundary')."""
    env.ledger(
        phase_entry="- 2026-10-01 — P34.1 done — PR #201 green "
        # `ci: pass #201@SHA7X`: SHA7X is deliberately not hex — a parseable
        # `ci:` field anywhere in the diff is verified against GitHub, and a
        # sha-shaped placeholder would be taken for a real claim.
        "(`ci: pass #201@SHA7X`; ci_boundary 22:18:48Z)\n"
    )
    fx = standard(env.local)
    fx["merged_prs"] = [
        {
            "number": 154,
            "headRefName": "devin/p31-19-round9-closeout",
            "headRefOid": "e" * 40,
            "baseRefName": "main",
            # Earlier the same calendar day as the boundary — before it.
            "mergedAt": "2026-10-01T04:26:00Z",
        },
        {
            "number": 200,
            "headRefName": "r11/p34-0",
            "headRefOid": "f" * 40,
            "baseRefName": "main",
            "mergedAt": "2026-10-01T23:00:00Z",  # after the boundary — in the window
        },
    ]
    env.set(fx)
    rc, doc, line, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 0, line
    ext = doc["external"]
    assert ext["since"] == "2026-10-01T22:18:48Z"
    assert [m["number"] for m in ext["merged_since"]] == [200], (
        "the pre-boundary merge is outside the window; the chain merge is recorded"
    )
    assert "merges:1" in line


def test_a_stack_link_broken_by_rebase_is_red(env) -> None:
    """The parent head is not an ancestor of the child's — a rebase/retarget."""
    fx = standard(env.local)
    # #201's recorded head is a commit the tip does not contain.
    git(env.root, "checkout", "-q", "--orphan", "rebased")
    git(env.root, "commit", "-q", "-m", "foreign parent")
    foreign = git(env.root, "rev-parse", "HEAD").strip()
    git(env.root, "checkout", "-q", "r11/p34-1")
    fx["prs"]["201"] = pr(201, "r11/seed", foreign, "devin/p33-8-agent-docs-refresh")
    fx["check_runs"][foreign] = runs(foreign, 200)
    env.set(fx)
    rc, doc, line, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 3 and doc["kind"] == "stack" and "does not contain its base" in line
    assert doc["external"]["ancestry"][0]["ancestor"] is False


def test_unreadable_origin_main_is_unavailable_not_green(env) -> None:
    git(env.root, "update-ref", "-d", "refs/remotes/origin/main")
    env.set(standard(env.local))
    rc, doc, line, _ = env.run("--pr", "202", "--no-wait")
    assert rc == 3 and doc["kind"] == "unavailable" and "origin/main is not readable" in line


def test_ledger_parsers() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("ci_boundary", TOOL)
    assert spec is not None and spec.loader is not None
    cb = importlib.util.module_from_spec(spec)
    sys.modules["ci_boundary"] = cb
    spec.loader.exec_module(cb)
    text = (
        LEDGER.format(
            waivers='| 2026-10-01T12:00:00Z | g | q | "waive docs" | operator | c | waiver |\n',
            phase_entry="",
        )
        + "\n## GATE DECISIONS (legacy)\n\n| date | gate | q | a | by | consequence |\n"
        + "|---|---|---|---|---|---|\n"
        + ("| 2026-09-01 | g | q | a waiver | op | waiver |\n")
    )
    assert cb.ledger_value(text, "chainTip") == "r11/p34-1"
    assert len(cb.ledger_waivers(text)) == 1  # the legacy 6-column table is not a waiver source
    assert cb.waived(["| … #202 … web … | waiver |"], 202, "web")
    assert not cb.waived(["| … #2021 … web … | waiver |"], 202, "web")
    assert not cb.waived(["| … #202 … web-perf … | waiver |"], 202, "web")
