#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``memory_guard.py`` (Round 11 Stage B, SEED-02; B4 G1/G2/G4, §3 "Unit fixtures").

Two kinds of test:

- **Oracle replays** judge real commits of this repository read-only (`--first-parent <sha>`), the
  ones B1/B2/B4 name: the guard must flag `c2055d96` (53 GATE DECISIONS rows deleted), its merge
  `e2175c93`, `307161ee` (top insertion), `305f94d5` (ADR date +1 day), `95c8a73f` / `4127dbf3` /
  `0a715fcc` (readout signing rewrites), `7a2ff9fa` (jsonl rewrite + 10-21 anchors), `062306e7`
  (sqitch planned_at ahead of its commit), `e1cedcad` (sources.toml rights dates back-dated with the
  flip) and `b542f236` (DEFERRALS history erased); it must pass the Stage-B seed commits that append
  ADR status lines / trigger evaluations (`850805aa`) and restore the 53 rows (`4a921bb9`). They skip
  when the history is absent (a shallow clone).
- **Synthetic fixtures** build a throw-away git repo per case in ``tmp_path``, commit with
  ``GIT_COMMITTER_DATE`` and run the guard. Every rule has a failing case; every passing case also
  asserts that the guard evaluated something, so each test fails against a no-op guard.

Run::

    uv run pytest docs/build/tools/test_memory_guard.py -q
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
GUARD = HERE / "memory_guard.py"
REAL_POLICY = HERE / "record_policy" / "history.policy"
NOW = "2026-09-30T00:00:00Z"
T_BASE = "2026-09-27T12:00:00Z"
T_CHANGE = "2026-09-28T03:00:00Z"

_spec = importlib.util.spec_from_file_location("memory_guard", GUARD)
assert _spec is not None and _spec.loader is not None
mg = importlib.util.module_from_spec(_spec)
sys.modules["memory_guard"] = mg
_spec.loader.exec_module(mg)


# ── helpers ─────────────────────────────────────────────────────────────────


def run_guard(
    repo: Path, *args: str, now: str = NOW, tmp: Path | None = None
) -> tuple[int, dict, str]:
    out = (tmp or repo.parent) / f"report-{os.getpid()}-{len(args)}.json"
    if out.exists():
        out.unlink()
    proc = subprocess.run(
        [sys.executable, str(GUARD), *args, "--repo", str(repo), "--now", now, "--json", str(out)],
        capture_output=True,
        text=True,
    )
    doc = json.loads(out.read_text()) if out.exists() else {}
    return proc.returncode, doc, proc.stdout + proc.stderr


def rules(doc: dict, severity: str = "violations") -> list[tuple[str, str, str]]:
    return [(f["check"], f["rule"], f["path"]) for c in doc.get("checks", []) for f in c[severity]]


def counts(doc: dict) -> dict[str, tuple[int, int]]:
    return {c["check"]: (c["candidates"], c["evaluated"]) for c in doc.get("checks", [])}


def git(repo: Path, *args: str, date: str | None = None) -> str:
    env = dict(os.environ)
    if date:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    proc = subprocess.run(
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
        env=env,
        check=True,
    )
    return proc.stdout


def commit(repo: Path, date: str = T_CHANGE, msg: str = "change") -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", msg, date=date)
    return git(repo, "rev-parse", "HEAD").strip()


def write(repo: Path, rel: str, text: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def append(repo: Path, rel: str, text: str) -> None:
    with (repo / rel).open("a", encoding="utf-8") as fh:
        fh.write(text)


def replace(repo: Path, rel: str, old: str, new: str) -> None:
    p = repo / rel
    s = p.read_text(encoding="utf-8")
    assert old in s, f"{old!r} not in {rel}"
    p.write_text(s.replace(old, new, 1), encoding="utf-8")


LEDGER = """# demo — build ledger

## CURRENT STATE
```
projectStatus:   IN_PROGRESS
nextTicket:      T2
updatedAt:       2026-09-27T12:00:00Z
```

## OPEN FINDINGS
- **F-1** first finding
- none

## GATE DECISIONS

### Round 1

| date | ticket | gate | item | answer (verbatim) | consequence | kind |
|---|---|---|---|---|---|---|
| 2026-09-26T10:00:00Z | T1 | GATE-G1 | budget | "yes" (chat) | released | decision |
| 2026-09-27T10:00:00Z | T1 | GATE-G1 | scope | "keep it small" (chat) | narrowed | decision |

## RETURN PASS
| ticket | gates | what the operator must do | re-run line |
|---|---|---|---|
| T9 | G9 | wait | rerun |

### RETURN PASS — current
| ticket | gates |
|---|---|
| T9 | G9 |

## PHASE LOG — Round 1
- 2026-09-26 — GATE-G1 pause — waiting for the operator
- 2026-09-27 — T1 done — demo/t1 · PR #1
- 2026-09-27 — T9 planned — demo/t9 · PR pending
"""

DEFERRALS = """# Deferrals

| id | kind | what | blocked by | unblocked by | evidence | status |
|---|---|---|---|---|---|---|
| D-T1-1 | V | live check | budget gated | GATE-G1 | fixture | OPEN |
"""

INDEX = """# Build index

| seq | ticket | kind | branch | PR | base | landed | adr | deferrals | live | evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| 01 | T1 | ticket | demo/t1 | #1 | main | 2026-09-27 | — | — | n-a | runs/T1.md |
| 90 | T9 | ticket | demo/t9 | #TBD | main | 2026-09-27 | — | — | n-a | runs/T9.md |
"""

READOUT = """# GATE-G2 readout
Status: PENDING
Disposition: <pending>

> An operator or authorized human record supplies the decision; an agent must not sign or assume silence is
> approval.

## Criterion (verbatim)
- [ ] the demo is green

## Signature
"""

ADR1 = """# ADR-001: Demo with a section after the trigger

- **Status:** Accepted
- **Date:** 2026-09-01

## Context
Some context.

## Revisit trigger

When X happens.

## References
- a reference
"""

ADR2 = """# ADR-002: Demo with the trigger last

- **Date:** 2026-09-01

## Decision
Decided.

## Revisit trigger

When Y happens."""  # no newline at EOF, as several landed ADRs

ADR3 = "# ADR-003: Successor\n\n- **Date:** 2026-09-20\n\n## Decision\nNew.\n"

MANIFEST = """# Manifest

## The chain

### Round 1
| # | file |
|---|---|
| 01 | `01_T1__demo.md` |

## Plan extensions
- 2026-09-27 — none
"""

SOURCES = """[sources.demo]
name = "demo"
ingestion_permitted = false
last_verified = 2026-09-20
[sources.demo.rights]
retrieval_date = 2026-08-20
"""


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q")
    write(r, "docs/build/README.md", "# build memory\n<!-- build-memory: v2 -->\n")
    write(r, "docs/build/LEDGER.md", LEDGER)
    write(r, "docs/tickets/DEFERRALS.md", DEFERRALS)
    write(r, "docs/build/BUILD_INDEX.md", INDEX)
    write(r, "docs/build/readouts/GATE-G2.md", READOUT)
    write(
        r,
        "docs/build/reports/obligations/events.jsonl",
        '{"id":1,"recorded_at":"2026-09-20T10:00:00Z"}\n{"id":2,"recorded_at":"2026-09-21T10:00:00Z"}\n',
    )
    write(r, "docs/adr/ADR-001-demo.md", ADR1)
    write(r, "docs/adr/ADR-002-two.md", ADR2)
    write(r, "docs/adr/ADR-003-successor.md", ADR3)
    write(
        r,
        "docs/build/runs/T1.md",
        "# Run ledger — T1\n\n- **Started:** 2026-09-27T10:00:00Z\n"
        "- **Closed:** 2026-09-27T11:00:00Z\n- **PR:** #1\n- **ci:** <pending>\n",
    )
    write(r, "docs/tickets/00_MANIFEST.md", MANIFEST)
    write(r, "docs/tickets/01_T1__demo.md", "# T1 — demo\n\n## Acceptance\n- it works\n")
    write(r, "connectors/src/connectors/data/sources.toml", SOURCES)
    (r / "db").mkdir()
    shutil.copy(ROOT / "db" / "sqitch.plan", r / "db" / "sqitch.plan")
    (r / "docs/build/tools/record_policy").mkdir(parents=True)
    shutil.copy(REAL_POLICY, r / "docs/build/tools/record_policy/history.policy")
    commit(r, T_BASE, "base")
    return r


def base_of(repo: Path) -> str:
    return git(repo, "rev-list", "--max-parents=0", "HEAD").strip()


def judge(repo: Path, cmd: str = "all", now: str = NOW) -> tuple[int, dict, str]:
    return run_guard(repo, cmd, "--range", f"{base_of(repo)}..HEAD", now=now)


# ── real-history oracle replays (read-only) ─────────────────────────────────


def _have(sha: str) -> bool:
    shallow = (
        subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--is-shallow-repository"],
            capture_output=True,
            text=True,
        ).stdout.strip()
        == "true"
    )
    ok = subprocess.run(
        ["git", "-C", str(ROOT), "cat-file", "-e", f"{sha}^{{commit}}"], capture_output=True
    )
    return not shallow and ok.returncode == 0


def replay(
    sha: str, tmp_path: Path, now: str = "2026-10-01T08:00:00Z"
) -> tuple[int, dict, str]:
    if not _have(sha):
        pytest.skip(f"{sha} not in this clone (shallow or rewritten history)")
    return run_guard(ROOT, "all", "--first-parent", sha, now=now, tmp=tmp_path)


@pytest.mark.parametrize("sha", ["c2055d96", "e2175c93"])
def test_oracle_c2055d96_gate_decisions_deletion_is_flagged(sha: str, tmp_path: Path) -> None:
    rc, doc, _ = replay(sha, tmp_path)
    hits = [r for r in rules(doc) if r == ("append-only", "append-only", "docs/build/LEDGER.md")]
    assert rc == 1 and len(hits) >= 53, (rc, len(hits))


def test_oracle_307161ee_top_insertion_is_flagged(tmp_path: Path) -> None:
    rc, doc, _ = replay("307161ee", tmp_path)
    assert rc == 1 and ("append-only", "append-position", "docs/build/LEDGER.md") in rules(doc)


def test_oracle_305f94d5_adr_dated_after_its_commit(tmp_path: Path) -> None:
    rc, doc, _ = replay("305f94d5", tmp_path)
    assert rc == 1 and any(
        r[:2] == ("record-dates", "R1") and r[2].startswith("docs/adr/ADR-065") for r in rules(doc)
    )


def test_oracle_95c8a73f_readout_signing_rewrite_and_future_date(tmp_path: Path) -> None:
    rc, doc, _ = replay("95c8a73f", tmp_path)
    got = rules(doc)
    assert rc == 1
    assert ("readouts", "readout", "docs/build/readouts/GATE-G3.md") in got
    assert ("readouts", "G4b-guard", "docs/build/readouts/GATE-G3.md") in got
    assert ("record-dates", "R1", "docs/build/readouts/GATE-G3.md") in got


def test_oracle_7a2ff9fa_jsonl_rewrite_and_anchor_dates(tmp_path: Path) -> None:
    rc, doc, _ = replay("7a2ff9fa", tmp_path)
    got = rules(doc)
    ev = "docs/build/reports/obligations/events.jsonl"
    assert rc == 1 and ("append-only", "prefix", ev) in got and ("record-dates", "R1", ev) in got


def test_oracle_062306e7_sqitch_planned_after_commit(tmp_path: Path) -> None:
    rc, doc, _ = replay("062306e7", tmp_path)
    assert rc == 1 and ("record-dates", "R1", "db/sqitch.plan") in rules(doc)


def test_oracle_e1cedcad_rights_dates_back_dated_with_the_flip(tmp_path: Path) -> None:
    rc, doc, _ = replay("e1cedcad", tmp_path)
    assert rc == 1 and (
        "record-dates",
        "R2",
        "connectors/src/connectors/data/sources.toml",
    ) in rules(doc)


def test_oracle_b542f236_deferrals_history_erased(tmp_path: Path) -> None:
    rc, doc, _ = replay("b542f236", tmp_path)
    assert rc == 1 and ("append-only", "row-annotate", "docs/tickets/DEFERRALS.md") in rules(doc)


@pytest.mark.parametrize(
    "sha,readout", [("4127dbf3", "ACCEPT-R10.md"), ("0a715fcc", "ACCEPT-R8.md")]
)
def test_oracle_signing_rewrites_readouts(sha: str, readout: str, tmp_path: Path) -> None:
    rc, doc, _ = replay(sha, tmp_path)
    assert rc == 1 and ("readouts", "readout", f"docs/build/readouts/{readout}") in rules(doc)


def test_oracle_0a715fcc_quoted_delegation_is_reported(tmp_path: Path) -> None:
    rc, doc, _ = replay("0a715fcc", tmp_path)
    assert ("gate-records", "G4a-delegation", "docs/build/LEDGER.md") in rules(doc, "warnings")


def test_oracle_850805aa_adr_status_lines_and_trigger_evaluations_pass(tmp_path: Path) -> None:
    rc, doc, out = replay("850805aa", tmp_path)
    c = counts(doc)
    assert rc == 0, out
    assert c["append-only"][1] > 500 and c["record-dates"][1] > 50, c


def test_oracle_4a921bb9_restoration_passes_and_blames_r37_r40(tmp_path: Path) -> None:
    rc, doc, out = replay("4a921bb9", tmp_path)
    assert rc == 0, out
    assert counts(doc)["restored-dates"] == (53, 53)
    false_rows = {r["row"] for r in doc["restored"] if r["verdict"] != "ok"}
    assert false_rows == {"R37", "R38", "R39", "R40"}
    assert all(r["annotated"] for r in doc["restored"] if r["verdict"] != "ok")


@pytest.mark.parametrize("sha", ["f68a3c96", "4b346d51"])
def test_oracle_seed_commits_pass(sha: str, tmp_path: Path) -> None:
    """The Stage-B seed commits must pass the full-mode guard — SEED-15 (`f68a3c96`) re-homes
    deferral rows with their text preserved and SEED-12c (`4b346d51`) stamps DRAFT-* placeholders
    with their final SIG-MEM-* ids and appends ADR clarification/status sections; both are the
    sanctioned shapes the modes exist to allow."""
    rc, doc, out = replay(sha, tmp_path, now="2026-10-03T00:00:00Z")
    assert rc == 0, out


def test_blame_mode_on_the_real_c2055d96_rows(tmp_path: Path) -> None:
    """B2 §4.1 restoration of `eb9a23d0` L114–166, judged against `git blame`: exactly the rows dated
    2026-09-10 but written 2026-09-13T19:40Z (`eb72be5f`, R37–R40) are clock-false (R2)."""
    if not _have("eb9a23d0"):
        pytest.skip("eb9a23d0 not in this clone")
    src = subprocess.run(
        ["git", "-C", str(ROOT), "show", "eb9a23d0:docs/build/LEDGER.md"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split("\n")
    rows = src[113:166]
    head = [
        "## GATE DECISIONS",
        "",
        "- 2026-10-01T00:00:00Z **RESTORED from `c2055d96^` (`eb9a23d0`) — test.**",
        "",
        src[111],
        src[112],
        *rows,
        "",
    ]
    r = mg.Report()
    mg.judge_restored_blocks(mg.Git(ROOT), mg.LEDGER_REL, head, None, None, 1790000000, r)
    flagged = sorted({f.message.split()[2] for f in r.findings if f.rule == "blame-R2"})
    assert flagged == ["R37", "R38", "R39", "R40"], flagged
    assert r.counts["restored-dates"] == [53, 53]
    # annotated → clean
    head += ["| row | class | correction |", "|---|---|---|"] + [
        f"| R{n} | clock-false | DATE CORRECTION: recorded 2026-09-10 → true ≤ 2026-09-13T19:40:01Z |"
        for n in range(37, 41)
    ]
    r2 = mg.Report()
    mg.judge_restored_blocks(mg.Git(ROOT), mg.LEDGER_REL, head, None, None, 1790000000, r2)
    assert not [f for f in r2.findings if f.severity == "error"]
    # tampered → not verbatim
    head[6] = head[6].replace("ACCEPTED", "REJECTED", 1)
    r3 = mg.Report()
    mg.judge_restored_blocks(mg.Git(ROOT), mg.LEDGER_REL, head, None, None, 1790000000, r3)
    assert any(f.rule == "verbatim" for f in r3.findings)


# ── synthetic fixtures: G2 append-only ──────────────────────────────────────

PL_OK = "- 2026-09-28 — T2 done — demo/t2 · PR #2\n"


def test_clean_close_passes_and_is_evaluated(repo: Path) -> None:
    append(repo, "docs/build/LEDGER.md", PL_OK)
    replace(
        repo,
        "docs/build/LEDGER.md",
        "updatedAt:       2026-09-27T12:00:00Z",
        "updatedAt:       2026-09-28T03:00:00Z",
    )
    append(
        repo,
        "docs/build/BUILD_INDEX.md",
        "| 02 | T2 | ticket | demo/t2 | #2 | demo/t1 | 2026-09-28 | — | — | n-a | runs/T2.md |\n",
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["record-dates"] == (3, 3)


def test_gate_decisions_rows_deleted_c2055d96_shape(repo: Path) -> None:
    replace(
        repo,
        "docs/build/LEDGER.md",
        '| 2026-09-26T10:00:00Z | T1 | GATE-G1 | budget | "yes" (chat) | released | decision |\n',
        "",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("append-only", "append-only", "docs/build/LEDGER.md") in rules(doc)


def test_gate_decisions_top_insertion_307161ee_shape(repo: Path) -> None:
    replace(
        repo,
        "docs/build/LEDGER.md",
        "|---|---|---|---|---|---|---|\n",
        '|---|---|---|---|---|---|---|\n| 2026-09-28T02:00:00Z | T2 | GATE-G1 | x | "go" | go | confirmation |\n',
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("append-only", "append-position", "docs/build/LEDGER.md") in rules(doc)


def test_phase_log_rewrite_is_flagged(repo: Path) -> None:
    replace(
        repo,
        "docs/build/LEDGER.md",
        "T1 done — demo/t1 · PR #1",
        "T1 done — demo/t1 · PR #1 (merged)",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("append-only", "append-only", "docs/build/LEDGER.md") in rules(doc)


def test_living_head_needs_an_archive_and_a_pointer(repo: Path) -> None:
    replace(
        repo, "docs/build/LEDGER.md", "# demo — build ledger\n", "# demo — build ledger (slim)\n"
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("append-only", "living-archived", "docs/build/LEDGER.md") in rules(doc)


def test_living_head_archived_with_pointer_passes(repo: Path) -> None:
    write(repo, "docs/build/reports/memory-repair/LEDGER_head.txt", "# demo — build ledger\n")
    replace(
        repo,
        "docs/build/LEDGER.md",
        "# demo — build ledger\n",
        "# demo — build ledger (slim)\n<!-- archived: docs/build/reports/memory-repair/LEDGER_head.txt -->\n",
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["append-only"][1] > 0


def test_living_head_archived_without_a_pointer_fails(repo: Path) -> None:
    write(repo, "docs/build/reports/memory-repair/LEDGER_head.txt", "# demo — build ledger\n")
    replace(
        repo, "docs/build/LEDGER.md", "# demo — build ledger\n", "# demo — build ledger (slim)\n"
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("append-only", "pointer", "docs/build/LEDGER.md") in rules(doc)


def test_current_state_value_update_is_living(repo: Path) -> None:
    replace(repo, "docs/build/LEDGER.md", "nextTicket:      T2", "nextTicket:      T3")
    append(repo, "docs/build/LEDGER.md", PL_OK)
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["record-dates"][1] == 1


def test_exempt_return_pass_current_is_not_judged_but_the_old_table_is(repo: Path) -> None:
    replace(
        repo, "docs/build/LEDGER.md", "| T9 | G9 |\n", "| T8 | G8 |\n"
    )  # inside ### RETURN PASS — current
    append(repo, "docs/build/LEDGER.md", PL_OK)
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["append-only"][1] > 0
    replace(
        repo, "docs/build/LEDGER.md", "| T9 | G9 | wait | rerun |", "| T9 | G9 | done | rerun |"
    )
    git(repo, "commit", "-qam", "rewrite old table", date=T_CHANGE)
    rc2, doc2, _ = run_guard(repo, "all", "--first-parent", "HEAD")
    assert rc2 == 1 and ("append-only", "row-annotate", "docs/build/LEDGER.md") in rules(doc2)


def test_deferrals_rewrite_flip_and_dated_flip(repo: Path) -> None:
    replace(repo, "docs/tickets/DEFERRALS.md", "| budget gated |", "| scope gated |")
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("append-only", "row-annotate", "docs/tickets/DEFERRALS.md") in rules(doc)


def test_deferrals_status_flip_needs_a_date(repo: Path) -> None:
    replace(
        repo,
        "docs/tickets/DEFERRALS.md",
        "| fixture | OPEN |",
        "| fixture | DONE (evidence) — was: OPEN |",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("append-only", "status-date", "docs/tickets/DEFERRALS.md") in rules(doc)


def test_deferrals_dated_flip_passes(repo: Path) -> None:
    replace(
        repo,
        "docs/tickets/DEFERRALS.md",
        "| fixture | OPEN |",
        "| fixture | DONE 2026-09-28 (runs/T2.md) — was: OPEN |",
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["record-dates"] == (1, 1)


def test_deferrals_future_dated_flip_fails_r1(repo: Path) -> None:
    replace(
        repo,
        "docs/tickets/DEFERRALS.md",
        "| fixture | OPEN |",
        "| fixture | DONE 2026-10-19 (x) — was: OPEN |",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("record-dates", "R1", "docs/tickets/DEFERRALS.md") in rules(doc)


def test_jsonl_prefix_and_recorded_at(repo: Path) -> None:
    write(
        repo,
        "docs/build/reports/obligations/events.jsonl",
        '{"id":1,"recorded_at":"2026-09-20T10:00:00Z"}\n',
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and (
        "append-only",
        "prefix",
        "docs/build/reports/obligations/events.jsonl",
    ) in rules(doc)


def test_jsonl_future_recorded_at_7a2ff9fa_shape(repo: Path) -> None:
    append(
        repo,
        "docs/build/reports/obligations/events.jsonl",
        '{"id":3,"recorded_at":"2026-10-21T00:00:00Z"}\n',
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and (
        "record-dates",
        "R1",
        "docs/build/reports/obligations/events.jsonl",
    ) in rules(doc)


def test_closed_run_ledger_only_gains_lines(repo: Path) -> None:
    replace(repo, "docs/build/runs/T1.md", "- **PR:** #1\n", "- **PR:** #1 (merged)\n")
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("append-only", "append-only", "docs/build/runs/T1.md") in rules(doc)


def test_body_closed_line_is_not_a_header_stamp_d7cbc68e_shape(repo: Path) -> None:
    write(
        repo,
        "docs/build/runs/T2.md",
        "# Run ledger — T2\n\n- **Started:** 2026-09-28T01:00:00Z\n\n## Deferrals\n\n- **Closed:** none.\n",
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["record-dates"] == (1, 1)
    # not closed (no dated header stamp): the ledger is still append-only — a body
    # `Closed:` line is content, not the header stamp-fill position, so rewriting it
    # in place is a removal the sanctioned modes do not cover (register: 7671b511)
    replace(repo, "docs/build/runs/T2.md", "- **Closed:** none.", "- **Closed:** D-T1-1.")
    git(repo, "commit", "-qam", "edit open run ledger", date=T_CHANGE)
    rc2, doc2, out2 = run_guard(repo, "all", "--first-parent", "HEAD")
    assert rc2 == 1 and ("append-only", "append-only", "docs/build/runs/T2.md") in rules(
        doc2
    ), out2


def test_executed_contract_takes_only_amended_notes(repo: Path) -> None:
    replace(repo, "docs/tickets/01_T1__demo.md", "- it works\n", "- it works well\n")
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("append-only", "frozen", "docs/tickets/01_T1__demo.md") in rules(doc)


def test_executed_contract_amended_note_passes(repo: Path) -> None:
    append(
        repo,
        "docs/tickets/01_T1__demo.md",
        "\n> Amended 2026-09-28: scope clarified (operator, chat).\n",
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["record-dates"] == (1, 1)


# landed ADRs (orchestrator note to SEED-02a: the two shapes SEED-11d appended, nothing else)


def test_adr_status_updates_section_at_eof_passes(repo: Path) -> None:
    append(
        repo,
        "docs/adr/ADR-001-demo.md",
        "\n## Status updates\n\n- **Status:** Superseded by ADR-003 (2026-09-28) — §2 only\n"
        "- **Status note (2026-09-28T02:00:00Z, unit T2):** recorded from the plan;\n"
        "  the body above is unchanged (SIG-ENG-003).\n",
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["record-dates"] == (2, 2)


def test_adr_trigger_evaluation_at_end_of_revisit_trigger_passes(repo: Path) -> None:
    replace(
        repo,
        "docs/adr/ADR-001-demo.md",
        "When X happens.\n",
        "When X happens.\n\n### Trigger evaluation — T2 (Round 1, 2026-09-28): NOT fired\n\n"
        "Evaluated at T2; an agent evaluation, not an operator decision.\n",
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["record-dates"] == (1, 1) and counts(doc)["append-only"][1] > 0


def test_adr_trigger_evaluation_when_the_trigger_is_last_and_eof_lacks_newline(repo: Path) -> None:
    append(
        repo,
        "docs/adr/ADR-002-two.md",
        "\n\n### Trigger evaluation — T2 (Round 1, 2026-09-28): FIRED\n\nThe trigger fired.\n\n"
        "## Status updates\n\n- **Status:** Qualified by ADR-003 (2026-09-28)\n",
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["record-dates"] == (2, 2)


def test_adr_in_place_edit_is_forbidden(repo: Path) -> None:
    replace(repo, "docs/adr/ADR-001-demo.md", "Some context.", "Some better context.")
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("append-only", "frozen", "docs/adr/ADR-001-demo.md") in rules(doc)


def test_adr_insertion_mid_body_and_loose_prose_are_forbidden(repo: Path) -> None:
    replace(
        repo, "docs/adr/ADR-001-demo.md", "Some context.\n", "Some context.\nA new paragraph.\n"
    )
    append(repo, "docs/adr/ADR-002-two.md", "\nAn afterthought appended at EOF.\n")
    commit(repo)
    rc, doc, _ = judge(repo)
    got = rules(doc)
    assert rc == 1
    assert ("append-only", "append-position", "docs/adr/ADR-001-demo.md") in got
    assert ("append-only", "frozen", "docs/adr/ADR-002-two.md") in got


def test_adr_status_line_must_name_an_existing_adr(repo: Path) -> None:
    append(
        repo,
        "docs/adr/ADR-001-demo.md",
        "\n## Status updates\n\n- **Status:** Superseded by ADR-999 (2026-09-28)\n",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("append-only", "superseded-by", "docs/adr/ADR-001-demo.md") in rules(doc)


def test_new_adr_date_header_is_an_act(repo: Path) -> None:
    write(
        repo,
        "docs/adr/ADR-004-new.md",
        "# ADR-004: New\n\n- **Date:** 2026-10-19\n\n## Decision\nx\n",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("record-dates", "R1", "docs/adr/ADR-004-new.md") in rules(doc)


# policy files: db/sqitch.plan (append-only + C-10 allow-list), sources.toml rights dates


def test_sqitch_plan_is_append_only_and_l44_is_never_restamped(repo: Path) -> None:
    replace(
        repo,
        "db/sqitch.plan",
        "claim_assertion_bindings [camera_site_human_decisions claim_evidence "
        "ingest_run_capture access_control] 2026-10-03T12:00:00Z",
        "claim_assertion_bindings [camera_site_human_decisions claim_evidence "
        "ingest_run_capture access_control] 2026-09-27T04:16:00Z",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("append-only", "frozen", "db/sqitch.plan") in rules(doc)


def test_sqitch_new_line_planned_after_its_commit_062306e7_shape(repo: Path) -> None:
    append(
        repo,
        "db/sqitch.plan",
        "demo_change [recovery_apply] 2026-10-05T12:00:00Z t <t@example.invalid> # demo\n",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("record-dates", "R1", "db/sqitch.plan") in rules(doc)


def test_sqitch_new_line_planned_before_its_commit_passes(repo: Path) -> None:
    append(
        repo,
        "db/sqitch.plan",
        "demo_change [recovery_apply] 2026-09-28T02:59:00Z t <t@example.invalid> # demo\n",
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["record-dates"] == (1, 1)


def test_sqitch_c10_allow_list_covers_l44_l52_until_expiry(repo: Path) -> None:
    """C-10-shaped allow entries (one per recorded change: name, dependencies, planned_at) exempt the
    future-dated L44–52 lines (a replay that re-adds them) until 2026-10-19T21:00Z; after expiry the
    same lines fail R1. The fixture writes its own entries, so the test does not pin the living policy."""
    plan = (repo / "db/sqitch.plan").read_text().split("\n")
    head, l44_52 = plan[:43], plan[43:52]
    write(repo, "db/sqitch.plan", "\n".join(head) + "\n")
    prefixes = [ln[: mg.DATE_RE.search(ln).end()] for ln in l44_52]  # type: ignore[union-attr]
    append(
        repo,
        "docs/build/tools/record_policy/history.policy",
        "".join(f"allow db/sqitch.plan 2026-10-19T21:00:00Z {p}\n" for p in prefixes),
    )
    git(repo, "commit", "-qam", "truncate (fixture only)", date=T_BASE)
    start = git(repo, "rev-parse", "HEAD").strip()
    append(repo, "db/sqitch.plan", "\n".join(l44_52) + "\n")
    commit(repo)
    rc, doc, out = run_guard(repo, "dates", "--range", f"{start}..HEAD")
    assert rc == 0, out
    assert counts(doc)["record-dates"] == (9, 9)
    rc2, doc2, _ = run_guard(repo, "dates", "--range", f"{start}..HEAD", now="2026-10-20T00:00:00Z")
    assert rc2 == 1 and len([r for r in rules(doc2) if r[1] == "R1"]) >= 8


def test_sources_toml_rights_dates_back_dated_with_flip_e1cedcad_shape(repo: Path) -> None:
    replace(
        repo,
        "connectors/src/connectors/data/sources.toml",
        "ingestion_permitted = false\n",
        "ingestion_permitted = true\nrights_reviewed_on = 2026-09-10\n",
    )
    commit(repo, "2026-09-13T19:56:51Z")
    rc, doc, _ = judge(repo)
    assert rc == 1 and (
        "record-dates",
        "R2",
        "connectors/src/connectors/data/sources.toml",
    ) in rules(doc)


def test_sources_toml_old_retrieval_date_without_flip_is_an_event(repo: Path) -> None:
    append(
        repo,
        "connectors/src/connectors/data/sources.toml",
        '[sources.other]\nname = "other"\n[sources.other.rights]\nretrieval_date = 2026-08-01\n',
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["record-dates"] == (1, 1)
    append(repo, "connectors/src/connectors/data/sources.toml", "retrieval_date = 2026-10-02\n")
    git(repo, "commit", "-qam", "future", date=T_CHANGE)
    rc2, doc2, _ = run_guard(repo, "all", "--first-parent", "HEAD")
    assert rc2 == 1 and (
        "record-dates",
        "R1",
        "connectors/src/connectors/data/sources.toml",
    ) in rules(doc2)


# ── synthetic fixtures: G1 record dates ─────────────────────────────────────


def test_r1_phase_log_entry_one_day_ahead_305f94d5_shape(repo: Path) -> None:
    append(repo, "docs/build/LEDGER.md", "- 2026-09-29 — T2 done — demo/t2 · PR #2\n")
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("record-dates", "R1", "docs/build/LEDGER.md") in rules(doc)


def test_r1_date_only_uses_the_committer_local_date(repo: Path) -> None:
    # committed 2026-09-27T23:30-04:00 = 2026-09-28T03:30Z: both 09-27 (local) and 09-28 (UTC) pass, 09-29 fails
    append(repo, "docs/build/LEDGER.md", "- 2026-09-28 — T2 done — demo/t2 · PR #2\n")
    commit(repo, "2026-09-27T23:30:00-04:00")
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["record-dates"] == (1, 1)


def test_r2_back_dated_act_and_retro_marker(repo: Path) -> None:
    append(repo, "docs/build/LEDGER.md", "- 2026-09-20 — T2 done — demo/t2 · PR #2\n")
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("record-dates", "R2", "docs/build/LEDGER.md") in rules(doc)
    append(
        repo,
        "docs/build/LEDGER.md",
        "- 2026-09-20 — T3 done — retro: landed 09-20 per git 3f2a1c0 committer time\n",
    )
    git(repo, "commit", "-qam", "retro", date=T_CHANGE)
    rc2, doc2, out2 = run_guard(repo, "all", "--first-parent", "HEAD")
    assert rc2 == 0, out2
    assert counts(doc2)["record-dates"] == (1, 1)


def test_r3_correction_quoting_the_wrong_date_with_the_true_one(repo: Path) -> None:
    write(
        repo,
        "docs/build/runs/T2.md",
        "# T2\n- **Recorded:** DATE CORRECTION — recorded 2026-10-19 → true ≤ 2026-09-28T02:49:00Z\n",
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["record-dates"] == (1, 1)
    write(
        repo,
        "docs/build/runs/T3.md",
        "# T3\n- **Recorded:** DATE CORRECTION — recorded 2026-10-19\n",
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "bare", date=T_CHANGE)
    rc2, doc2, _ = run_guard(repo, "all", "--first-parent", "HEAD")
    assert rc2 == 1 and ("record-dates", "R1", "docs/build/runs/T3.md") in rules(doc2)


def test_r2_a_strict_correction_may_quote_an_old_date(repo: Path) -> None:
    replace(
        repo,
        "docs/tickets/DEFERRALS.md",
        "| fixture | OPEN |",
        "| fixture | OPEN — DATE CORRECTION: DONE 2026-09-10 recorded 2026-09-10 → true 2026-09-13T19:56:51Z |",
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["record-dates"] == (1, 1)
    # the same quoted date without the correction form is a back-dated act
    append(
        repo,
        "docs/tickets/DEFERRALS.md",
        "| D-T1-2 | V | other | gated | GATE-G1 | x | DONE 2026-09-10 (x) |\n",
    )
    git(repo, "commit", "-qam", "back-dated", date=T_CHANGE)
    rc2, doc2, _ = run_guard(repo, "all", "--first-parent", "HEAD")
    assert rc2 == 1 and ("record-dates", "R2", "docs/tickets/DEFERRALS.md") in rules(doc2)


def test_r5_future_ok_and_its_malformed_form(repo: Path) -> None:
    append(
        repo,
        "docs/build/readouts/GATE-G2.md",
        "Date: 2026-10-19 <!-- future-ok: scheduled: the publication window opens -->\n",
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["record-dates"] == (1, 1)
    append(repo, "docs/build/readouts/GATE-G2.md", "Date: 2026-10-20 <!-- future-ok: someday -->\n")
    git(repo, "commit", "-qam", "bad", date=T_CHANGE)
    rc2, doc2, _ = run_guard(repo, "all", "--first-parent", "HEAD")
    got = rules(doc2)
    assert rc2 == 1 and ("record-dates", "R5-malformed", "docs/build/readouts/GATE-G2.md") in got
    assert ("record-dates", "R1", "docs/build/readouts/GATE-G2.md") in got


def test_r5_allow_entry_for_the_10_10_replay_expires(repo: Path) -> None:
    replace(
        repo,
        "docs/tickets/DEFERRALS.md",
        "| fixture | OPEN |",
        "| fixture | OPEN 2026-10-10 — the sig-sched-camreg-batch-05 replay fires at 2026-10-10T03:35Z |",
    )
    append(
        repo,
        "docs/build/tools/record_policy/history.policy",
        "allow docs/tickets/DEFERRALS.md 2026-10-10T04:35:00Z sig-sched-camreg-batch-05\n",
    )
    commit(repo)
    rc, doc, out = judge(repo)  # now = 2026-09-30, before expiry
    assert rc == 0, out
    assert counts(doc)["record-dates"] == (1, 1)
    rc2, doc2, out2 = judge(repo, now="2026-10-10T05:00:00Z")  # after 2026-10-10T04:35Z
    assert rc2 == 1 and "allow entry expired" in out2


def test_malformed_stamp_takes_its_lowest_reading(repo: Path) -> None:
    replace(
        repo,
        "docs/build/LEDGER.md",
        '| 2026-09-27T10:00:00Z | T1 | GATE-G1 | scope | "keep it small" (chat) | narrowed | decision |\n',
        '| 2026-09-27T10:00:00Z | T1 | GATE-G1 | scope | "keep it small" (chat) | narrowed | decision |\n'
        '| 2026-09-28T02:2xZ | T2 | GATE-G1 | x | "yes" | ok | confirmation |\n',
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("record-dates", "R1-malformed", "docs/build/LEDGER.md") in rules(doc)


def test_r6_commit_later_than_the_clock(repo: Path) -> None:
    append(repo, "docs/build/LEDGER.md", "- 2026-10-05 — T2 done — demo/t2 · PR #2\n")
    commit(repo, "2026-10-05T00:00:00Z")
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("record-dates", "R6", "-") in rules(doc)


def test_planning_tree_is_out_of_scope(repo: Path) -> None:
    write(
        repo,
        "docs/build/planning/2026-09-30-next-phase/META_PLAN.md",
        "# plan\n\n## 11. Change log\n- 2026-10-19T00:00Z — forecast text\n",
    )
    append(repo, "docs/build/LEDGER.md", "- 2026-10-19 — T2 done — demo/t2 · PR #2\n")
    commit(repo)
    rc, doc, _ = judge(repo)
    got = rules(doc)
    assert rc == 1 and got == [("record-dates", "R1", "docs/build/LEDGER.md")], got


def test_vacuous_when_no_candidate_could_be_evaluated(repo: Path) -> None:
    append(repo, "docs/build/LEDGER.md", "- T2 done — demo/t2 · PR #2 (no date)\n")
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 3, out
    assert counts(doc)["record-dates"] == (1, 0)


# ── synthetic fixtures: G4a gate records ────────────────────────────────────

ROW_ANCHOR = '| 2026-09-27T10:00:00Z | T1 | GATE-G1 | scope | "keep it small" (chat) | narrowed | decision |\n'


def add_rows(repo: Path, *rows: str) -> None:
    replace(repo, "docs/build/LEDGER.md", ROW_ANCHOR, ROW_ANCHOR + "".join(r + "\n" for r in rows))


def test_g4a_well_formed_row_passes(repo: Path) -> None:
    add_rows(
        repo,
        '| 2026-09-28T02:00:00Z | T2 | GATE-G1 | release | "yes, release it" (chat) | released | decision |',
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["gate-records"] == (1, 1)


@pytest.mark.parametrize(
    "row,rule",
    [
        ('| 2026-09-28T02:00:00Z | T2 | GATE-G1 | x | "yes" | ok | ruling |', "G4a-kind"),
        ("| 2026-09-28T02:00:00Z | T2 | GATE-G1 | x | yes | ok | decision |", "G4a-verbatim"),
        ('| 2026-09-28 | T2 | GATE-G1 | x | "yes" | ok | confirmation |', "G4a-date"),
        (
            '| 2026-09-28T02:00:00Z | T2 | GATE-G1 | all | "go ahead" | ok | pre-authorization |',
            "G4a-preauth",
        ),
        (
            '| 2026-09-28T02:00:00Z | T2 | GATE-G1 | x | "ok please sign it for me or whatever" | ok | decision |',
            "G4a-delegation",
        ),
        (
            '| 2026-09-28T02:00:00Z | T2 | GATE-G1 | x | "I also wonder if we should just ship?" | ok | decision |',
            "G4a-hedge",
        ),
        (
            '| 2026-09-28T02:00:00Z | T2 | GATE-G1 | x | "yes" | ok | decision | extra |',
            "G4a-columns",
        ),
    ],
)
def test_g4a_rule_failures(repo: Path, row: str, rule: str) -> None:
    add_rows(repo, row)
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("gate-records", rule, "docs/build/LEDGER.md") in rules(doc), rules(doc)


def test_g4a_hedge_with_a_later_plain_confirmation_passes(repo: Path) -> None:
    add_rows(
        repo,
        '| 2026-09-28T02:00:00Z | T2 | GATE-G1 | x | "I also wonder if we should just ship?" | asked | decision |',
        '| 2026-09-28T02:30:00Z | T2 | GATE-G1 | x | "Yes — ship it." | shipped | confirmation |',
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["gate-records"] == (2, 2)


def test_g4a_scoped_pre_authorization_passes(repo: Path) -> None:
    add_rows(
        repo,
        '| 2026-09-28T02:00:00Z | T2 | GATE-G3 | HG-03:src_a, HG-03:src_b | "go for those two" (chat) | '
        "pre-authorized; expires: T5; voided-by: any new source | pre-authorization |",
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["gate-records"] == (1, 1)


def test_g4a_decision_for_a_marker_needs_a_pause(repo: Path) -> None:
    add_rows(
        repo,
        '| 2026-09-28T02:00:00Z | GATE-G2 | GATE-G2 | publish | "yes" (chat) | go | decision |',
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("gate-records", "G4a-pause", "docs/build/LEDGER.md") in rules(doc)


def test_g4a_decision_after_its_pause_passes_and_before_it_fails(repo: Path) -> None:
    add_rows(
        repo,
        '| 2026-09-28T02:00:00Z | GATE-G2 | GATE-G2 | publish | "yes" (chat) | go | decision |',
    )
    append(
        repo, "docs/build/LEDGER.md", "- 2026-09-28 — GATE-G2 pause — waiting for the operator\n"
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["gate-records"] == (1, 1)
    add_rows(
        repo, '| 2026-09-25T09:00:00Z | GATE-G1 | GATE-G1 | early | "yes" (chat) | go | decision |'
    )
    git(repo, "commit", "-qam", "early", date="2026-09-25T09:30:00Z")
    rc2, doc2, _ = run_guard(repo, "gates", "--first-parent", "HEAD")
    assert rc2 == 1 and ("gate-records", "G4a-pause", "docs/build/LEDGER.md") in rules(doc2)


# ── synthetic fixtures: G4b readouts ────────────────────────────────────────


def test_g4b_new_readout_needs_the_guard_sentence(repo: Path) -> None:
    write(
        repo,
        "docs/build/readouts/GATE-G3.md",
        "# GATE-G3 readout\nStatus: PENDING\n\n## Criterion\n- x\n",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("readouts", "G4b-guard", "docs/build/readouts/GATE-G3.md") in rules(doc)


def test_g4b_signing_that_rewrites_the_pending_text_95c8a73f_shape(repo: Path) -> None:
    replace(
        repo, "docs/build/readouts/GATE-G2.md", "Status: PENDING", "Status: **SIGNED — approved**"
    )
    replace(
        repo, "docs/build/readouts/GATE-G2.md", "- [ ] the demo is green", "- [x] the demo is green"
    )
    replace(
        repo,
        "docs/build/readouts/GATE-G2.md",
        "> An operator or authorized human record supplies the decision; an agent must not sign or assume silence is\n"
        "> approval.\n",
        "",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    got = rules(doc)
    assert rc == 1
    assert ("readouts", "readout", "docs/build/readouts/GATE-G2.md") in got
    assert ("readouts", "G4b-guard", "docs/build/readouts/GATE-G2.md") in got


SIG_OK = (
    'Operator decision (verbatim, received 2026-09-28T02:10:00Z via chat): "yes, publish"\n'
    "GATE DECISIONS row: 2026-09-28T02:10:00Z | GATE-G2\n"
    "Signed by: the operator. Recorded by claude-code/claude-opus-5-5/subagent, which does not sign.\n"
)


def test_g4b_correct_signature_block_passes(repo: Path) -> None:
    add_rows(
        repo,
        '| 2026-09-28T02:10:00Z | GATE-G2 | GATE-G2 | publish | "yes, publish" (chat) | go | decision |',
    )
    append(
        repo, "docs/build/LEDGER.md", "- 2026-09-28 — GATE-G2 pause — waiting for the operator\n"
    )
    replace(repo, "docs/build/readouts/GATE-G2.md", "Status: PENDING", "Status: SIGNED")
    append(repo, "docs/build/readouts/GATE-G2.md", SIG_OK)
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["readouts"] == (1, 1) and counts(doc)["record-dates"][1] >= 3


def test_g4b_signature_words_must_equal_the_gate_decisions_answer(repo: Path) -> None:
    replace(repo, "docs/build/readouts/GATE-G2.md", "Status: PENDING", "Status: SIGNED")
    append(
        repo,
        "docs/build/readouts/GATE-G2.md",
        SIG_OK + "The operator also agreed to everything else.\n",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    got = rules(doc)
    assert rc == 1
    assert ("readouts", "G4b-verbatim", "docs/build/readouts/GATE-G2.md") in got
    assert ("readouts", "G4b-prose", "docs/build/readouts/GATE-G2.md") in got


def test_g4b_agent_drafted_hash_and_confirmation(repo: Path) -> None:
    import hashlib

    body = "The demo is green on run 42.\n"
    sha = hashlib.sha256(body.encode()).hexdigest()
    append(
        repo,
        "docs/build/readouts/GATE-G2.md",
        f"<!-- agent-drafted:begin sha256={sha} -->\n{body}<!-- agent-drafted:end -->\n",
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["readouts"] == (1, 1)
    replace(repo, "docs/build/readouts/GATE-G2.md", f"sha256={sha}", "sha256=" + "0" * 64)
    git(repo, "commit", "-qam", "bad hash", date=T_CHANGE)
    rc2, doc2, _ = run_guard(repo, "readouts", "--first-parent", "HEAD")
    assert rc2 == 1 and ("readouts", "G4b-drafted-hash", "docs/build/readouts/GATE-G2.md") in rules(
        doc2
    )


def test_g4b_signing_needs_the_operator_confirmation_of_drafted_text(repo: Path) -> None:
    import hashlib

    body = "Summary by the agent.\n"
    sha = hashlib.sha256(body.encode()).hexdigest()
    append(
        repo,
        "docs/build/readouts/GATE-G2.md",
        f"<!-- agent-drafted:begin sha256={sha} -->\n{body}<!-- agent-drafted:end -->\n",
    )
    add_rows(
        repo,
        '| 2026-09-28T02:10:00Z | GATE-G2 | GATE-G2 | publish | "yes, publish" (chat) | go | decision |',
    )
    append(
        repo, "docs/build/LEDGER.md", "- 2026-09-28 — GATE-G2 pause — waiting for the operator\n"
    )
    commit(repo)
    replace(repo, "docs/build/readouts/GATE-G2.md", "Status: PENDING", "Status: SIGNED")
    append(repo, "docs/build/readouts/GATE-G2.md", SIG_OK)
    git(repo, "commit", "-qam", "sign", date=T_CHANGE)
    rc, doc, _ = run_guard(repo, "readouts", "--first-parent", "HEAD")
    assert rc == 1 and ("readouts", "G4b-confirmation", "docs/build/readouts/GATE-G2.md") in rules(
        doc
    )


# ── synthetic fixtures: G1 blame mode on a restored block ───────────────────


def restore_history(repo: Path, annotate: bool, tamper: bool = False) -> str:
    """Rows written at 09-24/09-27 (one dated 09-20: back-dated), deleted at 09-28, restored at 09-29."""
    rows = [
        '| 2026-09-20 | T0 | GATE-G0 | early | "ok" | written late | decision |',
        '| 2026-09-24 | T0 | GATE-G0 | later | "ok" | on time | decision |',
    ]
    replace(repo, "docs/build/LEDGER.md", ROW_ANCHOR, ROW_ANCHOR + rows[0] + "\n")
    commit(repo, "2026-09-24T12:00:00Z", "write rows")
    replace(repo, "docs/build/LEDGER.md", rows[0] + "\n", rows[0] + "\n" + rows[1] + "\n")
    commit(repo, "2026-09-25T12:00:00Z", "write row 2")
    replace(repo, "docs/build/LEDGER.md", rows[0] + "\n" + rows[1] + "\n", "")
    deleting = commit(repo, "2026-09-28T01:00:00Z", "delete rows (c2055d96 shape)")
    pre = git(repo, "rev-parse", "HEAD").strip()
    body = rows[0].replace("written late", "written LATE") if tamper else rows[0]
    block = (
        f"\n- 2026-09-29T10:00:00Z **RESTORED from `{deleting[:8]}^`.** Verbatim, not re-decided.\n\n"
        "| Date | Ticket | Gate | Item | Answer | Notes |\n|---|---|---|---|---|---|\n"
        f"{body}\n{rows[1]}\n"
    )
    if annotate:
        block += (
            "\n- 2026-09-29T10:00:00Z **Annotation of the restored rows.**\n\n| row | class | correction |\n"
            "|---|---|---|\n| R1 | clock-false | DATE CORRECTION: recorded 2026-09-20 → true ≤ 2026-09-24T12:00:00Z |\n"
        )
    replace(repo, "docs/build/LEDGER.md", "\n## RETURN PASS", block + "\n## RETURN PASS")
    commit(repo, "2026-09-29T10:05:00Z", "restore")
    return pre


def test_restored_block_clock_false_row_needs_an_annotation(repo: Path) -> None:
    pre = restore_history(repo, annotate=False)
    rc, doc, _ = run_guard(repo, "all", "--range", f"{pre}..HEAD")
    got = rules(doc)
    assert rc == 1 and ("restored-dates", "blame-R2", "docs/build/LEDGER.md") in got
    assert not [r for r in got if r[0] == "record-dates"], (
        got
    )  # restored rows are judged by blame, not diff mode
    assert counts(doc)["restored-dates"] == (2, 2)


def test_restored_block_annotated_passes(repo: Path) -> None:
    pre = restore_history(repo, annotate=True)
    rc, doc, out = run_guard(repo, "all", "--range", f"{pre}..HEAD")
    assert rc == 0, out
    assert counts(doc)["restored-dates"] == (2, 2)
    assert [r["verdict"] for r in doc["restored"]] == ["R2", "ok"]
    rc2, doc2, out2 = run_guard(repo, "restored", "--rev", "HEAD")
    assert rc2 == 0 and counts(doc2)["restored-dates"] == (2, 2), out2


def test_restored_block_must_be_verbatim(repo: Path) -> None:
    pre = restore_history(repo, annotate=True, tamper=True)
    rc, doc, _ = run_guard(repo, "all", "--range", f"{pre}..HEAD")
    assert rc == 1 and ("restored-dates", "verbatim", "docs/build/LEDGER.md") in rules(doc)


# ── synthetic fixtures: record shape (skill parity) ─────────────────────────


def test_build_index_row_shape(repo: Path) -> None:
    append(
        repo,
        "docs/build/BUILD_INDEX.md",
        "| 01 | T2 | ticket | demo/t2 | PR pending | demo/t1 | 2026-09-28 | — | — | n-a |\n",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    got = {r[1] for r in rules(doc) if r[0] == "record-shape"}
    assert rc == 1 and {"columns", "seq", "pr"} <= got, got


def test_build_index_corrections_table_may_repeat_a_seq(repo: Path) -> None:
    append(
        repo,
        "docs/build/BUILD_INDEX.md",
        "\n## Index repairs\n\n| corr | seq | field | recorded → true |\n|---|---|---|---|\n"
        "| DC-1 | 01 | landed | recorded 2026-09-27 → true 2026-09-27T11:00Z |\n"
        "| DC-2 | 01 | pr | recorded #1 → true #1 |\n| DC-3 | 01 | a | b | c |\n",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    got = rules(doc)
    assert rc == 1 and got == [("record-shape", "columns", "docs/build/BUILD_INDEX.md")], got


def test_build_index_marker_rows_under_a_compact_header_are_counted_and_judged(repo: Path) -> None:
    """SEED-09's shape: late marker rows appended under a new subsection whose header has no spaces
    (`|Seq|Ticket|…|`). record-shape must count them as candidates and evaluate them (it reported 0
    before SEED-02b, so a malformed marker row could not be told from no row at all)."""
    append(
        repo,
        "docs/build/BUILD_INDEX.md",
        "\n### Index repairs (late marker rows)\n\n"
        "|Seq|Ticket|Kind|Branch|PR|Base|Landed|ADRs|Deferrals|Live|Evidence|\n"
        "|---|---|---|---|---|---|---|---|---|---|---|\n"
        "| 02 | GATE-G1 | gate (marker) | — | — (no PR; marker) | demo/t1 | 2026-09-28 | — | — | n-a | "
        "`readouts/GATE-G1.md` |\n"
        "| 03 | GATE-G2 | gate (marker) | — | — (no PR; marker) | demo/t1 | 2026-09-28 | — | — | n-a | "
        "`readouts/GATE-G2.md` |\n",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 0, rules(doc)
    assert counts(doc)["record-shape"] == (2, 2)
    append(
        repo,
        "docs/build/BUILD_INDEX.md",
        "| 04 | GATE-G3 | gate (marker) | — | — | demo/t1 | 2026-09-28 |\n",
    )
    commit(repo)
    rc2, doc2, _ = judge(repo)
    assert rc2 == 1 and counts(doc2)["record-shape"] == (3, 3)
    assert ("record-shape", "columns", "docs/build/BUILD_INDEX.md") in rules(doc2)


def test_build_index_seq_is_unique_across_index_tables(repo: Path) -> None:
    """Every index table (one with a PR or landed column) shares one seq space: a marker row or a
    Round-11 row appended under a new header may not reuse a seq of the main index (SEED-02b; before,
    the seen-set was reset at every header, so a reused seq in a later table went unnoticed)."""
    append(
        repo,
        "docs/build/BUILD_INDEX.md",
        "\n## Round 11\n\n"
        "| seq | ticket | kind | branch | PR | base | landed | adr | deferrals | live | evidence |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|\n"
        "| 01 | T9 | ticket | demo/t9 | #9 | main | 2026-09-27 | — | — | n-a | runs/T9.md |\n",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    got = rules(doc)
    assert rc == 1 and got == [("record-shape", "seq", "docs/build/BUILD_INDEX.md")], got
    assert "reuses seq 01 (first at line 5)" in json.dumps(doc)


def test_build_index_row_under_no_header_is_vacuous(repo: Path) -> None:
    """A row added above every header cannot be judged for shape: a candidate never evaluated is
    not green (G11, exit 3)."""
    replace(
        repo, "docs/build/BUILD_INDEX.md", "# Build index\n", "# Build index\n| 00 | T0 | stray |\n"
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 3 and counts(doc)["record-shape"] == (1, 0)


def test_record_shape_counts_manifest_and_deferrals_rows(repo: Path) -> None:
    replace(
        repo,
        "docs/tickets/00_MANIFEST.md",
        "## Plan extensions",
        "### Round 2\n| # | file |\n|---|---|\n| 02 | `02_T2__next.md` |\n\n## Plan extensions",
    )
    append(
        repo,
        "docs/tickets/DEFERRALS.md",
        "| D-T1-2 | V | another live check | budget gated | GATE-G1 | fixture | OPEN |\n",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 0, rules(doc)
    assert counts(doc)["record-shape"] == (2, 2)


ADR4 = "# ADR-004: Seed ADR\n\n- **Date:** 2026-09-28\n\n## Decision\nFirst draft.\n\n## Revisit trigger\n\nWhen Z.\n"


def _seed_branch(repo: Path, pinned: bool = True) -> str:
    """A branch commit on top of the fixture's base that adds a seed ADR and readout; the LEDGER pins
    the base (`pinnedBaseSha`). Returns the base sha."""
    b0 = base_of(repo)
    if pinned:
        replace(
            repo,
            "docs/build/LEDGER.md",
            "nextTicket:      T2\n",
            f"nextTicket:      T2\npinnedBaseSha:   {b0[:8]}\n",
        )
    write(repo, "docs/adr/ADR-004-seed.md", ADR4)
    write(repo, "docs/build/readouts/GATE-G4.md", READOUT.replace("GATE-G2", "GATE-G4"))
    commit(repo, "2026-09-28T04:00:00Z", "seed: ADR-004 + GATE-G4 readout")
    return b0


def test_staged_edit_of_a_record_added_on_this_branch_is_allowed(repo: Path) -> None:
    """Orchestrator note (SEED-12c): in --staged/--worktree mode a record is landed only if it exists
    at the merge-base of HEAD with the LEDGER's pinnedBaseSha — a seed ADR may be edited until merged."""
    _seed_branch(repo)
    replace(
        repo, "docs/adr/ADR-004-seed.md", "First draft.", "Final wording, final requirement ids."
    )
    git(repo, "add", "-A")
    rc, doc, _ = run_guard(repo, "all", "--staged", now="2026-09-28T05:00:00Z")
    assert rc == 0, rules(doc)
    assert doc["input"]["landed_base"] == base_of(repo)
    assert doc["input"]["landed_from"].startswith("merge-base of HEAD and pinnedBaseSha")
    assert counts(doc)["append-only"][0] > 0  # the change was judged, not skipped
    rc_w, doc_w, _ = run_guard(repo, "all", "--worktree", now="2026-09-28T05:00:00Z")
    assert rc_w == 0, rules(doc_w)


def test_staged_edit_of_an_adr_present_at_the_pinned_base_stays_forbidden(repo: Path) -> None:
    _seed_branch(repo)
    replace(repo, "docs/adr/ADR-001-demo.md", "Some context.", "Rewritten context.")
    git(repo, "add", "-A")
    rc, doc, _ = run_guard(repo, "all", "--staged", now="2026-09-28T05:00:00Z")
    assert rc == 1 and ("append-only", "frozen", "docs/adr/ADR-001-demo.md") in rules(doc)


def test_staged_seed_record_may_be_removed_but_a_landed_one_may_not(repo: Path) -> None:
    _seed_branch(repo)
    (repo / "docs/build/readouts/GATE-G4.md").unlink()
    git(repo, "add", "-A")
    rc, doc, _ = run_guard(repo, "all", "--staged", now="2026-09-28T05:00:00Z")
    assert rc == 0, rules(doc)
    (repo / "docs/build/readouts/GATE-G2.md").unlink()
    git(repo, "add", "-A")
    rc2, doc2, _ = run_guard(repo, "all", "--staged", now="2026-09-28T05:00:00Z")
    assert rc2 == 1 and ("append-only", "deleted", "docs/build/readouts/GATE-G2.md") in rules(doc2)


def test_staged_without_a_pinned_base_falls_back_to_head(repo: Path) -> None:
    _seed_branch(repo, pinned=False)
    replace(repo, "docs/adr/ADR-004-seed.md", "First draft.", "Rewritten.")
    git(repo, "add", "-A")
    rc, doc, _ = run_guard(repo, "all", "--staged", now="2026-09-28T05:00:00Z")
    assert rc == 1 and ("append-only", "frozen", "docs/adr/ADR-004-seed.md") in rules(doc)
    assert doc["input"]["landed_from"].startswith("HEAD")


def test_range_judges_landedness_at_its_own_base(repo: Path) -> None:
    b0 = _seed_branch(repo)
    c1 = git(repo, "rev-parse", "HEAD").strip()
    replace(repo, "docs/adr/ADR-004-seed.md", "First draft.", "Rewritten.")
    commit(repo, "2026-09-28T05:00:00Z", "edit the seed ADR")
    rc, doc, _ = run_guard(repo, "all", "--range", f"{b0}..HEAD", now="2026-09-28T06:00:00Z")
    assert rc == 0, rules(doc)  # new within the range
    rc2, doc2, _ = run_guard(repo, "all", "--range", f"{c1}..HEAD", now="2026-09-28T06:00:00Z")
    assert rc2 == 1 and ("append-only", "frozen", "docs/adr/ADR-004-seed.md") in rules(doc2)


def test_oracle_412cb337_index_repair_rows_are_counted(tmp_path: Path) -> None:
    """SEED-09's index repairs: 2 marker rows + 9 correction rows, all judged and well formed."""
    if not _have("412cb337"):
        pytest.skip("412cb337 not in this clone (shallow or rewritten history)")
    # its own clock: the commit (2026-10-01T13:46:19Z) is later than replay()'s fixed now
    rc, doc, _ = run_guard(
        ROOT, "all", "--first-parent", "412cb337", now="2026-10-01T14:00:00Z", tmp=tmp_path
    )
    cand, ev = counts(doc)["record-shape"]
    assert rc == 0 and cand == ev >= 11, (rc, cand, ev)


def test_manifest_new_chain_row_needs_a_round_banner_and_a_stable_id(repo: Path) -> None:
    replace(
        repo,
        "docs/tickets/00_MANIFEST.md",
        "## Plan extensions",
        "| 02 | `02_T1__other-slug.md` |\n\n## Plan extensions",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("record-shape", "id-registry", "docs/tickets/00_MANIFEST.md") in rules(doc)


# ── modes, usage, policy ────────────────────────────────────────────────────


def test_staged_and_worktree_modes(repo: Path) -> None:
    append(repo, "docs/build/LEDGER.md", "- 2026-10-19 — T2 done — demo/t2 · PR #2\n")
    rc_w, doc_w, _ = run_guard(repo, "all", "--worktree", now="2026-10-01T00:00:00Z")
    assert rc_w == 1 and ("record-dates", "R1", "docs/build/LEDGER.md") in rules(doc_w)
    git(repo, "add", "-A")
    rc_s, doc_s, _ = run_guard(repo, "all", "--staged", now="2026-10-01T00:00:00Z")
    assert rc_s == 1 and ("record-dates", "R1", "docs/build/LEDGER.md") in rules(doc_s)


def test_replay_lists_each_first_parent_commit(repo: Path) -> None:
    append(repo, "docs/build/LEDGER.md", PL_OK)
    commit(repo, msg="ok")
    append(repo, "docs/build/LEDGER.md", "- 2026-10-19 — T3 done — demo/t3 · PR #3\n")
    commit(repo, msg="bad")
    proc = subprocess.run(
        [
            sys.executable,
            str(GUARD),
            "replay",
            f"{base_of(repo)}..HEAD",
            "--repo",
            str(repo),
            "--now",
            NOW,
        ],
        capture_output=True,
        text=True,
    )
    lines = [ln for ln in proc.stdout.splitlines() if " exit=" in ln]
    assert proc.returncode == 1 and len(lines) == 2
    assert "exit=0" in lines[0] and "record-dates[R1]×1" in lines[1]


def test_exit_codes_for_usage_and_unknown(repo: Path, tmp_path: Path) -> None:
    assert (
        subprocess.run(
            [sys.executable, str(GUARD), "all", "--repo", str(repo)], capture_output=True
        ).returncode
        == 2
    )
    plain = tmp_path / "plain"
    plain.mkdir()
    git(plain, "init", "-q")
    write(plain, "x.md", "x\n")
    commit(plain, T_BASE)
    rc, _, out = run_guard(plain, "all", "--first-parent", "HEAD")
    assert rc == 2 and "not a build-memory repo" in out
    rc5, _, out5 = run_guard(repo, "all", "--range", "deadbeef..HEAD")
    assert rc5 == 5 and "never green" in out5


def test_real_policy_invariants() -> None:
    """Invariants only (the policy is a living record: allow entries are added and expire)."""
    pol = mg.Policy.parse(REAL_POLICY.read_bytes())
    assert pol.errors == []
    assert "db/sqitch.plan" in pol.append_only  # C-10: a plan line is never re-stamped
    plan = (ROOT / "db" / "sqitch.plan").read_text().split("\n")
    for a in pol.allow:
        if a.glob == "db/sqitch.plan":  # an allow entry names exactly one recorded change
            assert sum(ln.startswith(a.text) for ln in plan) == 1, a.text


def test_policy_parser_directives_and_comments() -> None:
    raw = (
        "# comment\n"
        "exempt docs/build/LEDGER.md RETURN PASS — current  # generated\n"
        "archive docs/build/reports/memory-repair\n"
        "append-only db/sqitch.plan\n"
        "date connectors/x.toml ^[[:space:]]*(rights_reviewed_on|last_verified)[[:space:]]*=\n"
        "act-when connectors/x.toml ^[[:space:]]*ingestion_permitted[[:space:]]*=\n"
        "allow docs/tickets/DEFERRALS.md 2026-10-10T04:35:00Z sig-sched-camreg-batch-05\n"
        "allow docs/x.md not-a-date text\n"
        "bogus directive\n"
    ).encode()
    pol = mg.Policy.parse(raw)
    assert ("docs/build/LEDGER.md", "RETURN PASS — current") in pol.exempt
    assert pol.archive == ["docs/build/reports/memory-repair"] and pol.append_only == [
        "db/sqitch.plan"
    ]
    assert any(rx.search("  rights_reviewed_on = 2026-09-16") for _, rx in pol.dates)
    assert any(rx.search("ingestion_permitted = true") for _, rx in pol.act_when)
    assert [a.text for a in pol.allow] == ["sig-sched-camreg-batch-05"]
    assert len(pol.errors) == 2  # the bad expiry and the unknown directive
    assert (
        mg.Policy.strip_comment("exempt a ### RETURN PASS — current  # note")
        == "exempt a ### RETURN PASS — current"
    )
    subs = mg.regions(["## RETURN PASS", "x", "### RETURN PASS — current", "| a |"], level=3)
    assert any("RETURN PASS — current" in r.heading for r in subs)


def test_ci_required_names_jobs_of_ci_yml() -> None:
    names = mg.read_ci_required((ROOT / mg.CI_REQUIRED_REL).read_text())
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert names and all(f"\n  {n}:\n" in ci for n in names)
    with pytest.raises(ValueError):
        mg.read_ci_required("# only a comment\n")
    with pytest.raises(ValueError):
        mg.read_ci_required("python\nnot a name\n")


def test_stamp_parser() -> None:
    st = mg.parse_stamp("2026-09-30T18:2xZ")
    assert st is not None and st.malformed and mg.utc_iso(st.epoch) == "2026-09-30T18:20:00Z"
    off = mg.parse_stamp("2026-09-27T23:30:00-04:00")
    assert off is not None and mg.utc_iso(off.epoch) == "2026-09-28T03:30:00Z"
    assert mg.parse_stamp("2026-13-40") is None


# ── P34.7 (M1): remaining-mode fixtures — a passing and a failing diff per mode ──


def test_row_annotate_open_findings_bullet_grown_passes(repo: Path) -> None:
    """`row-annotate` (B2 §7): an OPEN FINDINGS bullet may be rewritten only to grow — the
    id-matched old text stays inside the new line (strike-through is transparent)."""
    replace(
        repo,
        "docs/build/LEDGER.md",
        "- **F-1** first finding\n",
        "- **F-1** ~~first finding~~ first finding — annotated 2026-09-28: cleared by T2\n",
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["append-only"][1] > 0


def test_row_annotate_bullet_without_an_id_cannot_be_rewritten(repo: Path) -> None:
    """A bullet with no `**id**` has no id-matched counterpart — rewriting it is a removal."""
    replace(
        repo,
        "docs/build/LEDGER.md",
        "- none\n",
        "- ~~none~~ none — annotated 2026-09-28: still none\n",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("append-only", "row-annotate", "docs/build/LEDGER.md") in rules(doc)


def test_row_annotate_return_pass_contained_annotation_passes(repo: Path) -> None:
    replace(
        repo,
        "docs/build/LEDGER.md",
        "| T9 | G9 | wait | rerun |",
        "| T9 | G9 | ~~wait~~ done 2026-09-28 (chat) | rerun |",
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["append-only"][1] > 0


def test_placeholder_fill_phase_log_pr_pending_passes(repo: Path) -> None:
    """`placeholder-fill` (B2 §7): a PHASE LOG bullet's `PR pending` field fills with the real PR
    at closeout — every other byte is identical."""
    replace(repo, "docs/build/LEDGER.md", "· PR pending", "· PR #9")
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["append-only"][1] > 0


def test_placeholder_fill_a_real_field_is_not_fillable(repo: Path) -> None:
    replace(repo, "docs/build/LEDGER.md", "· PR #1", "· PR #5")
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("append-only", "append-only", "docs/build/LEDGER.md") in rules(doc)


def test_placeholder_fill_index_pr_cell_passes(repo: Path) -> None:
    replace(repo, "docs/build/BUILD_INDEX.md", "| #TBD |", "| #7 |")
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["append-only"][1] > 0


def test_placeholder_fill_index_other_cell_fails(repo: Path) -> None:
    replace(repo, "docs/build/BUILD_INDEX.md", "| T9 | ticket |", "| T9 | issue |")
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("append-only", "append-only", "docs/build/BUILD_INDEX.md") in rules(doc)


def test_placeholder_fill_readout_disposition_passes(repo: Path) -> None:
    replace(
        repo, "docs/build/readouts/GATE-G2.md", "Disposition: <pending>", "Disposition: signed"
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["readouts"][1] > 0


def test_placeholder_fill_readout_other_line_fails(repo: Path) -> None:
    replace(
        repo,
        "docs/build/readouts/GATE-G2.md",
        "- [ ] the demo is green",
        "- [x] the demo is green",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("readouts", "readout", "docs/build/readouts/GATE-G2.md") in rules(doc)


SWEEP = "# demo report\n\n## P9.9 demo sweep (2026-09-27)\n\n- finding one\n"


def test_frozen_snapshot_late_insert_fails(repo: Path) -> None:
    """`frozen-snapshot` (B2 §7): a `##` heading carrying a date and 'sweep'/'snapshot'/'as of'
    is frozen by the commit that created it — a later insertion inside fails."""
    write(repo, "docs/build/reports/demo-sweep.md", SWEEP)
    commit(repo, "2026-09-27T20:00:00Z", "P9.9 sweep")
    replace(
        repo,
        "docs/build/reports/demo-sweep.md",
        "- finding one\n",
        "- finding one\n- smuggled in later\n",
    )
    commit(repo)
    rc, doc, _ = run_guard(repo, "all", "--first-parent", "HEAD")
    assert rc == 1 and (
        "append-only",
        "frozen-snapshot",
        "docs/build/reports/demo-sweep.md",
    ) in rules(doc)


def test_frozen_snapshot_new_dated_section_appended_after_it_passes(repo: Path) -> None:
    """A new dated section appended after a frozen tail region is a new region, not an edit of
    the snapshot — the sanctioned correction shape (the 412cb337 append)."""
    write(repo, "docs/build/reports/demo-sweep.md", SWEEP)
    commit(repo, "2026-09-27T20:00:00Z", "P9.9 sweep")
    append(
        repo,
        "docs/build/reports/demo-sweep.md",
        "\n## P9.10 follow-up sweep (2026-09-28)\n\n- finding two\n",
    )
    commit(repo)
    rc, doc, out = run_guard(repo, "all", "--first-parent", "HEAD")
    assert rc == 0, out
    assert counts(doc)["append-only"][1] > 0


def test_frozen_snapshot_tail_append_without_a_heading_is_inside(repo: Path) -> None:
    """Bare lines appended at EOF still extend the frozen tail region — only an appended heading
    opens a new section."""
    write(repo, "docs/build/reports/demo-sweep.md", SWEEP)
    commit(repo, "2026-09-27T20:00:00Z", "P9.9 sweep")
    append(repo, "docs/build/reports/demo-sweep.md", "- finding two, sneaked at EOF\n")
    commit(repo)
    rc, doc, _ = run_guard(repo, "all", "--first-parent", "HEAD")
    assert rc == 1 and (
        "append-only",
        "frozen-snapshot",
        "docs/build/reports/demo-sweep.md",
    ) in rules(doc)


def test_frozen_after_close_correction_section_passes(repo: Path) -> None:
    """`frozen-after-close` (B2 §7): a run ledger with a dated Closed: stamp takes only
    placeholder fills and appended `## Correction` sections."""
    append(
        repo,
        "docs/build/runs/T1.md",
        "\n## Correction\n\n- 2026-09-28 — the run's PR cell names #1.\n",
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["append-only"][1] > 0


def test_frozen_after_close_placeholder_fill_passes(repo: Path) -> None:
    replace(repo, "docs/build/runs/T1.md", "- **ci:** <pending>", "- **ci:** green 2026-09-28")
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["append-only"][1] > 0


def test_frozen_after_close_other_section_append_fails(repo: Path) -> None:
    append(repo, "docs/build/runs/T1.md", "\n## Notes\n\n- 2026-09-28 — extra\n")
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and (
        "append-only",
        "frozen-after-close",
        "docs/build/runs/T1.md",
    ) in rules(doc)


def test_frozen_after_close_mid_file_insert_fails(repo: Path) -> None:
    replace(
        repo,
        "docs/build/runs/T1.md",
        "- **PR:** #1\n",
        "- **PR:** #1\n- inserted after close\n",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("append-only", "append-position", "docs/build/runs/T1.md") in rules(doc)


def test_gate_status_fill_in_the_executing_commit_passes(repo: Path) -> None:
    """`frozen-after-execution` (B2 §7): a contract is frozen once execution starts, but the
    commit whose subject begins the ticket may also fill the `Gate status:` line."""
    write(
        repo,
        "docs/tickets/02_T7__gate.md",
        "# T7 — gated demo\n\n- **Gate status:** <pending>\n\n## Acceptance\n- green\n",
    )
    commit(repo, "2026-09-27T20:00:00Z", "add the T7 contract")
    replace(
        repo,
        "docs/tickets/02_T7__gate.md",
        "- **Gate status:** <pending>",
        "- **Gate status:** answered 2026-09-28 (operator, chat)",
    )
    commit(repo, msg="T7 gate — execution starts")
    rc, doc, out = run_guard(repo, "all", "--first-parent", "HEAD")
    assert rc == 0, out
    assert counts(doc)["append-only"][1] > 0


def test_gate_status_fill_after_the_executing_commit_fails(repo: Path) -> None:
    write(
        repo,
        "docs/tickets/02_T7__gate.md",
        "# T7 — gated demo\n\n- **Gate status:** <pending>\n\n## Acceptance\n- green\n",
    )
    commit(repo, "2026-09-27T20:00:00Z", "add the T7 contract")
    append(repo, "docs/build/LEDGER.md", PL_OK)
    commit(repo, msg="T7 gate — execution starts")
    replace(
        repo,
        "docs/tickets/02_T7__gate.md",
        "- **Gate status:** <pending>",
        "- **Gate status:** answered 2026-09-28 (operator, chat)",
    )
    commit(repo, msg="T7 later commit")
    rc, doc, _ = run_guard(repo, "all", "--first-parent", "HEAD")
    assert rc == 1 and ("append-only", "frozen", "docs/tickets/02_T7__gate.md") in rules(doc)


def test_living_head_archive_one_byte_off_fails(repo: Path) -> None:
    """B4 G2 fixture: a `living-archived` archive that differs by one byte does not cover the
    removed head — the bytes must match."""
    write(
        repo,
        "docs/build/reports/memory-repair/LEDGER_head.txt",
        "# demo — build ledger!\n",  # one byte off
    )
    replace(
        repo,
        "docs/build/LEDGER.md",
        "# demo — build ledger\n",
        "# demo — build ledger (slim)\n"
        "<!-- archived: docs/build/reports/memory-repair/LEDGER_head.txt -->\n",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("append-only", "living-archived", "docs/build/LEDGER.md") in rules(doc)


_EV = (
    '{{"schema":"obligation-event/1","event_id":"{eid}","kind":"{kind}","obligation_id":'
    '"{oid}","seq":{seq},"expected_previous_event":{epe},"from_status":"OPEN","to_status":'
    '"{to}","ticket_id":"T9","owner":"—","landing":"—","backlog_home":"—","evidence_refs":[],'
    '"observed_at":"2026-09-28","recorded_at":"2026-09-28","source_commit":"x","reason":"t"}}'
)


def _ev(eid: str, oid: str = "D-T9-1", kind: str = "transition", seq: int = 1, epe: str = '"x"', to: str = "DONE") -> str:
    return _EV.format(eid=eid, oid=oid, kind=kind, seq=seq, epe=epe, to=to) + "\n"


def test_jsonl_chained_transition_passes(repo: Path) -> None:
    """`prefix` (B2 §7): an appended migration anchors a new obligation; a transition chains on
    its event via expected_previous_event."""
    append(
        repo,
        "docs/build/reports/obligations/events.jsonl",
        _ev("D-T9-1:e0", kind="migration", seq=0, epe="null", to="OPEN")
        + _ev("D-T9-1:e1", epe='"D-T9-1:e0"'),
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    assert counts(doc)["record-dates"][1] > 0


def test_jsonl_transition_without_previous_event_fails(repo: Path) -> None:
    append(
        repo,
        "docs/build/reports/obligations/events.jsonl",
        _ev("D-T9-1:e0", kind="migration", seq=0, epe="null", to="OPEN")
        + _ev("D-T9-1:e1", epe="null"),
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and (
        "append-only",
        "chain",
        "docs/build/reports/obligations/events.jsonl",
    ) in rules(doc)


def test_jsonl_transition_chaining_the_wrong_event_fails(repo: Path) -> None:
    append(
        repo,
        "docs/build/reports/obligations/events.jsonl",
        _ev("D-T9-1:e0", kind="migration", seq=0, epe="null", to="OPEN")
        + _ev("D-T9-1:e1", epe='"D-T9-1:e9"'),
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and (
        "append-only",
        "chain",
        "docs/build/reports/obligations/events.jsonl",
    ) in rules(doc)


def test_jsonl_invalid_record_and_unknown_schema_fail(repo: Path) -> None:
    append(
        repo,
        "docs/build/reports/obligations/events.jsonl",
        '{"schema": "mystery/9"}\nnot-json\n',
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    got = [r for r in rules(doc) if r[:2] == ("append-only", "schema")]
    assert rc == 1 and len(got) == 2, got


def test_jsonl_event_missing_a_schema_field_fails(repo: Path) -> None:
    append(
        repo,
        "docs/build/reports/obligations/events.jsonl",
        '{"schema":"obligation-event/1","event_id":"D-T9-1:e0","kind":"migration"}\n',
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and (
        "append-only",
        "schema",
        "docs/build/reports/obligations/events.jsonl",
    ) in rules(doc)


def test_jsonl_migration_re_anchor_fails(repo: Path) -> None:
    append(
        repo,
        "docs/build/reports/obligations/events.jsonl",
        _ev("D-T9-1:e0", kind="migration", seq=0, epe="null", to="OPEN")
        + _ev("D-T9-1:e9", kind="migration", seq=9, epe="null", to="OPEN"),
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and (
        "append-only",
        "chain",
        "docs/build/reports/obligations/events.jsonl",
    ) in rules(doc)


def test_jsonl_placeholder_fill_mid_file_passes(repo: Path) -> None:
    """A `PENDING-COMMIT-SHA` token stamped with the landed sha is a declared placeholder fill,
    not a prefix violation (e.g. the seed writes a record before its sha exists)."""
    write(
        repo,
        "docs/build/reports/demo.jsonl",
        '{"id":1,"recorded_at":"2026-09-28T00:00:00Z","source_commit":"PENDING-COMMIT-SHA"}\n',
    )
    commit(repo)
    replace(
        repo,
        "docs/build/reports/demo.jsonl",
        '"source_commit":"PENDING-COMMIT-SHA"',
        '"source_commit":"0123456789abcdef"',
    )
    commit(repo)
    rc, doc, out = run_guard(repo, "all", "--first-parent", "HEAD")
    assert rc == 0, out


def test_chain_id_rebound_to_another_slug_fails(repo: Path) -> None:
    """Chain-id registry (B4 G2 amendment 4): an id that ever appeared in the manifest chain
    table never re-binds to a different file slug (the 32bea406 / P23.1–P23.7 shape)."""
    replace(
        repo,
        "docs/tickets/00_MANIFEST.md",
        "| 01 | `01_T1__demo.md` |",
        "| 01 | `01_T1__demo.md` |\n| 02 | `02_T1__other-slug.md` |",
    )
    commit(repo)
    rc, doc, _ = judge(repo)
    assert rc == 1 and ("record-shape", "id-registry", "docs/tickets/00_MANIFEST.md") in rules(doc)


def test_chain_registry_is_cached_in_the_report(repo: Path) -> None:
    """The chain-id scan result is recorded in the report (`extra.chain_registry`) so a caller can
    audit what history the registry covered (B4 G2 amendment 4)."""
    replace(
        repo,
        "docs/tickets/00_MANIFEST.md",
        "| 01 | `01_T1__demo.md` |",
        "| 01 | `01_T1__demo.md` |\n| 02 | `02_T2__next.md` |",
    )
    commit(repo)
    rc, doc, out = judge(repo)
    assert rc == 0, out
    reg = doc.get("extra", {}).get("chain_registry")
    assert reg and reg["ids"] >= 2 and reg["rebinds"] == [] and "git log" in reg["scan"]


# ── replay + oracle comparison (B4 §G2) ─────────────────────────────────────


def _oracle_csv(path: Path, rows: list[tuple[str, ...]]) -> str:
    p = path / "oracle.csv"
    with p.open("w", encoding="utf-8", newline="") as fh:
        fh.write("kind,commit,path,check,rule,source,note\n")
        for r in rows:
            fh.write(",".join(r) + "\n")
    return str(p)


def test_replay_oracle_flags_expected_and_passes_clean(repo: Path, tmp_path: Path) -> None:
    """Replay compares every first-parent commit against the expected set: the register-style
    violation row is flagged, the clean row passes, exit 0."""
    # a clean append (PHASE LOG entry) — judged and expected clean
    append(repo, "docs/build/LEDGER.md", "- 2026-09-28 — T2 done — demo/t2 · PR pending\n")
    good = commit(repo, T_CHANGE, "clean append")
    # a violation commit: a DEFERRALS row rewritten in place (post-obligation-ledger era)
    replace(repo, "docs/tickets/DEFERRALS.md", "| D-T1-1 |", "| D-T1-2 |")
    bad = commit(repo, "2026-09-28T05:00:00Z", "row rewritten")
    oracle = _oracle_csv(
        tmp_path,
        [
            ("clean", good[:8], "docs/build/LEDGER.md", "append-only", "*", "test", ""),
            ("violation", bad[:8], "docs/tickets/DEFERRALS.md", "*", "*", "test", ""),
        ],
    )
    rc, doc, out = run_guard(repo, "replay", f"{base_of(repo)}..HEAD", "--oracle", oracle)
    assert rc == 0, out
    assert doc["judged"] == 2 and doc["disagreements"]["missing"] == []


def test_replay_oracle_missed_expectation_fails(repo: Path, tmp_path: Path) -> None:
    """An expected violation the replay does not flag is a miss — never silently re-baselined."""
    append(repo, "docs/build/LEDGER.md", "- 2026-09-28 — T2 done — demo/t2 · PR pending\n")
    head = commit(repo, T_CHANGE, "clean append")
    oracle = _oracle_csv(
        tmp_path,
        [("violation", head[:8], "docs/build/LEDGER.md", "*", "*", "test", "")],
    )
    rc, doc, out = run_guard(repo, "replay", f"{base_of(repo)}..HEAD", "--oracle", oracle)
    assert rc == 1 and doc["disagreements"]["missing"], out


def test_replay_oracle_unexpected_finding_fails(repo: Path, tmp_path: Path) -> None:
    """A flagged cell outside the expected set is a disagreement — benign rows may not flag."""
    append(repo, "docs/build/LEDGER.md", "- 2026-09-28 — T2 done — demo/t2 · PR pending\n")
    commit(repo, T_CHANGE, "clean append")
    replace(repo, "docs/tickets/DEFERRALS.md", "| D-T1-1 |", "| D-T1-2 |")
    bad = commit(repo, "2026-09-28T05:00:00Z", "row rewritten")
    oracle = _oracle_csv(
        tmp_path,
        [("clean", bad[:8], "docs/tickets/DEFERRALS.md", "append-only", "*", "test", "")],
    )
    rc, doc, out = run_guard(repo, "replay", f"{base_of(repo)}..HEAD", "--oracle", oracle)
    assert rc == 1 and doc["disagreements"]["unexpected"], out


def test_replay_oracle_waived_row_withdraws_expectation(repo: Path, tmp_path: Path) -> None:
    """A `source=reviewed` `waived` row withdraws the derived expectation it matches on
    (commit, path, check-or-*): the register's claim and the adjudication sit side by side
    in the file, and the waived expectation is neither missed nor asserted."""
    append(repo, "docs/build/LEDGER.md", "- 2026-09-28 — T2 done — demo/t2 · PR pending\n")
    head = commit(repo, T_CHANGE, "clean append")
    oracle = _oracle_csv(
        tmp_path,
        [
            ("violation", head[:8], "docs/build/LEDGER.md", "*", "*", "test", ""),
            (
                "waived",
                head[:8],
                "docs/build/LEDGER.md",
                "*",
                "*",
                "reviewed",
                "register attribution reviewed — nothing added here to flag",
            ),
        ],
    )
    rc, doc, out = run_guard(repo, "replay", f"{base_of(repo)}..HEAD", "--oracle", oracle)
    assert rc == 0, out
    assert doc["disagreements"]["missing"] == []


def test_replay_oracle_waive_needs_reviewed_source(repo: Path, tmp_path: Path) -> None:
    """A `waived` row without `source=reviewed` cannot withdraw an expectation — the waiver
    is a review artifact, not another derived row."""
    append(repo, "docs/build/LEDGER.md", "- 2026-09-28 — T2 done — demo/t2 · PR pending\n")
    head = commit(repo, T_CHANGE, "clean append")
    oracle = _oracle_csv(
        tmp_path,
        [
            ("violation", head[:8], "docs/build/LEDGER.md", "*", "*", "test", ""),
            ("waived", head[:8], "docs/build/LEDGER.md", "*", "*", "test", ""),
        ],
    )
    rc, doc, out = run_guard(repo, "replay", f"{base_of(repo)}..HEAD", "--oracle", oracle)
    assert rc == 1 and doc["disagreements"]["missing"], out


def test_replay_empty_span_is_vacuous(repo: Path, tmp_path: Path) -> None:
    """A vacuous replay — an empty span judged nothing — exits 3, never green."""
    head = git(repo, "rev-parse", "HEAD").strip()
    rc, _, out = run_guard(repo, "replay", f"{head}..{head}")
    assert rc == 3, out


def test_replay_all_vacuous_span_is_never_green(repo: Path, tmp_path: Path) -> None:
    """A replay over a non-empty span that evaluated nothing at all — the only commit's
    record dates are all unparseable — exits 3: a replay that proves nothing is not green
    (SIG-ENG-042)."""
    append(repo, "docs/build/LEDGER.md", "- T2 done — demo/t2 · PR #2 (no date)\n")
    commit(repo, T_CHANGE, "undated phase-log entry")
    rc, _, out = run_guard(repo, "replay", f"{base_of(repo)}..HEAD")
    assert rc == 3 and "vacuous" in out, out
