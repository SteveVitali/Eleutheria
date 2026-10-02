#!/usr/bin/env python3
"""Read-only local preflight; never switches branches, edits files, or dispatches work.

A ready result is structural eligibility, not proof of worker quiescence, remote
PR closeout, test acceptance, rights, or publication approval. See the runbook.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

BASE = "0e57e6461d6a5db2e8e0042464750ce2ea65db5e"
FOUNDATION = "fdc775837b2808b23a9af690c427deec5ede0a5d"
PACKAGE = "docs/build/planning/2026-09-25-six-streams"
NEXT = {
    "P31.12": "P31.13",
    "P31.13": "P31.14",
    "P31.14": "P31.15",
    "P31.15": "P31.16",
    "P31.16": "P31.19",
    "P31.19": "P32.1",
}
CONTROL = (
    "docs/build/LEDGER.md",
    "docs/build/BUILD_INDEX.md",
    "docs/tickets/00_MANIFEST.md",
    "docs/tickets/DEFERRALS.md",
)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    ).stdout.strip()


def parse_current(text: str) -> dict[str, str]:
    section = re.search(r"^## CURRENT STATE\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    block = re.search(r"^```[^\n]*\n(.*?)^```", section[1] if section else "", re.M | re.S)
    if not block:
        raise ValueError("missing CURRENT STATE fenced block")
    values = {}
    for line in block[1].splitlines():
        match = re.match(r"^([A-Za-z][A-Za-z0-9]*):\s*(.*)$", line)
        if match:
            if match[1] in values:
                raise ValueError(f"duplicate CURRENT STATE key: {match[1]}")
            # Strip actual inline comments, not PR references such as '#147'.
            values[match[1]] = re.split(r"\s+#\s", match[2], maxsplit=1)[0].strip()
    return values


def transition(state: dict[str, str], expected: str | None) -> tuple[dict, list[str]]:
    errors = []
    last = state.get("lastCompleted")
    if last not in NEXT:
        errors.append("lastCompleted is outside supported clean P31.12–P31.19 boundaries")
    if expected != last:
        errors.append("--expect-last must match the operator's completed-ticket boundary")
    if state.get("blockedOn", "MISSING").lower() not in {"", "(nothing)", "none", "(none)"}:
        errors.append(
            "blockedOn needs an evidence-backed disposition; never clear it automatically"
        )
    if state.get("pauseRequested") not in {"true", "false"}:
        errors.append("pauseRequested must be an explicit boolean")
    if state.get("round") != "9":
        errors.append("expected Round 9 before initial import; inspect any existing Round-10 seed")
    if last in NEXT and last != "P31.19":
        if state.get("nextTicket") != NEXT[last] or state.get("projectStatus") != "IN-PROGRESS":
            errors.append(
                "Round-9 next/status differs from expected chain; reconcile fresh manifest first"
            )
    if last == "P31.19" and state.get("projectStatus") not in {"DONE", "IN-PROGRESS", "PAUSED"}:
        errors.append("P31.19 terminal status requires manual review")
    # After P31.19, inspect the old nextTicket manually: it can be a capstone/none
    # sentinel. Never overwrite an independently seeded extension without review.
    return {
        "lastCompleted": last,
        "nextTicket": NEXT.get(last),
        "round": "10" if last == "P31.19" else "9",
        "projectStatus": "IN-PROGRESS",
        "pauseRequested_during_import": "true",
        "canonicalSpec": "docs/2_canonical_design_spec.md",
    }, errors


def manifest_rows(text: str) -> list[tuple[int, str, str]]:
    rows = re.findall(r"^\|\s*(\d+)\s*\|\s*`?([^`| ]+\.md)`?", text, re.M)
    return [(int(n), re.sub(r"^\d+[a-z]?_", "", f).split("__")[0], f) for n, f in rows]


def fingerprint(repo: Path) -> dict:
    return {
        "repo": str(repo),
        "head": git(repo, "rev-parse", "HEAD"),
        "branch": git(repo, "symbolic-ref", "--quiet", "--short", "HEAD"),
        "status": git(repo, "status", "--porcelain=v1", "--untracked-files=all"),
        "control_sha256": {p: hashlib.sha256((repo / p).read_bytes()).hexdigest() for p in CONTROL},
    }


def compare_fingerprint(before: dict, after: dict) -> list[str]:
    return (
        []
        if before == after
        else ["active checkout changed since snapshot; stop and re-read, never overwrite"]
    )


def inspect(
    repo: Path,
    source_ref: str,
    expected: str | None,
    paused: bool,
    base: str = BASE,
    foundation: str = FOUNDATION,
) -> dict:
    repo = repo.resolve()
    before = fingerprint(repo)
    errors = []
    if not paused:
        errors.append(
            "waiting for operator attestation that orchestrator and ticket workers are paused"
        )
    if before["status"]:
        errors.append("active checkout is dirty or has untracked files; no auto-stash/reset/clean")
    if before["branch"] in {"main", "master"}:
        errors.append("expected a feature-stack tip, not main/master")
    for op in (
        "MERGE_HEAD",
        "CHERRY_PICK_HEAD",
        "REVERT_HEAD",
        "rebase-merge",
        "rebase-apply",
        "sequencer",
    ):
        path = Path(git(repo, "rev-parse", "--git-path", op))
        if (path if path.is_absolute() else repo / path).exists():
            errors.append(f"unfinished git operation: {op}")
    state = parse_current((repo / CONTROL[0]).read_text())
    proposal, state_errors = transition(state, expected)
    errors.extend(state_errors)
    if Path(state.get("buildWorktree", "")).resolve() != repo:
        errors.append("ledger buildWorktree does not identify this checkout")
    if state.get("chainTip") != before["branch"]:
        errors.append("ledger chainTip does not match the checked-out branch")
    last = state.get("lastCompleted", "")
    indexed = re.findall(
        r"^\|\s*\d+\s*\|\s*`?" + re.escape(last) + r"`?\s*\|", (repo / CONTROL[1]).read_text(), re.M
    )
    if len(indexed) != 1 or not (repo / f"docs/build/runs/{last}.md").is_file():
        errors.append(
            "completed ticket must have exactly one BUILD_INDEX row and an existing run ledger"
        )
    manifest = (repo / CONTROL[2]).read_text()
    rows = manifest_rows(manifest)
    if last in NEXT and last != "P31.19":
        tail = [tid for _, tid, _ in rows if tid in NEXT]
        if last not in tail or tail[tail.index(last) + 1 :][:1] != [NEXT[last]]:
            errors.append("manifest P31 ordering differs from expected boundary")
    if (repo / PACKAGE / "PLAN.json").exists() or any(tid == "P32.1" for _, tid, _ in rows):
        errors.append(
            "Round-10 already present: recover the existing import instead of duplicating it"
        )
    source = git(repo, "rev-parse", "--verify", "--end-of-options", source_ref + "^{commit}")
    git(repo, "merge-base", "--is-ancestor", base, before["head"])
    git(repo, "merge-base", "--is-ancestor", foundation, source)
    commits = git(repo, "rev-list", "--reverse", f"{base}..{source}").splitlines()
    if not commits or commits[0] != foundation:
        errors.append("source series does not begin with the pinned planning foundation")
    if git(repo, "rev-list", "--merges", f"{base}..{source}"):
        errors.append("planning source contains a merge; inspect provenance before import")
    changed = set()
    for commit in commits:
        changed.update(
            git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", commit).splitlines()
        )
    if any(not p.startswith("docs/") or p in CONTROL[:2] for p in changed):
        errors.append(
            "planning source changes files outside docs or includes active control-state files"
        )
    errors.extend(compare_fingerprint(before, fingerprint(repo)))
    return {
        "schema": "sig.round10_integration_preflight/v1",
        "ready_local": not errors,
        "errors": errors,
        "snapshot": before,
        "proposed_control": proposal,
        "source": {
            "ref": source_ref,
            "tip": source,
            "base": base,
            "foundation": foundation,
            "commits_in_order": commits,
            "changed_file_count": len(changed),
        },
        "allocation_review": {
            "occupied_sequences_161_onward": [r for r in rows if r[0] >= 161],
            "adr_115_files": sorted(p.name for p in (repo / "docs/adr").glob("ADR-115*.md")),
        },
        "still_required": [
            "review completed run/PR/acceptance and exact remote head",
            "inspect fresh manifest for intervening rows, omissions and terminal sentinels",
            "reconcile ADR/BL/requirement/ticket/readout namespaces and P31 progress",
            "follow INTEGRATION_RUNBOOK; this script does not perform integration",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--source-ref", default="codex/sig-six-stream-research")
    parser.add_argument("--expect-last", choices=NEXT)
    parser.add_argument(
        "--paused",
        action="store_true",
        help="operator explicitly confirmed all build workers paused",
    )
    parser.add_argument(
        "--compare", type=Path, help="previous JSON output; require unchanged active snapshot"
    )
    args = parser.parse_args()
    try:
        repo = args.repo.resolve()
        if Path(git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
            raise ValueError("--repo must identify the checkout root")
        report = inspect(repo, args.source_ref, args.expect_last, args.paused)
        if args.compare:
            report["errors"].extend(
                compare_fingerprint(
                    json.loads(args.compare.read_text())["snapshot"], report["snapshot"]
                )
            )
            report["ready_local"] = not report["errors"]
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        # Do not echo command stderr, remote URLs, or environmental credentials.
        report = {
            "ready_local": False,
            "errors": [f"preflight cannot establish required local state ({type(exc).__name__})"],
        }
    print(json.dumps(report, indent=2))
    return 0 if report["ready_local"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
