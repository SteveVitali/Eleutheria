#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Recorded-CI verifier (G3b; P34.2, SIG-MEM-007, H2 §4.6).

A recorded `ci:` line is a *claim* about GitHub state. This tool verifies every
such claim against the live records so "green" stays auditable after the fact:

- **PR scope** (`--diff-base <ref>`): every `ci:` line the diff `<ref>...HEAD`
  adds — wherever it lands — plus the rule that a Round-11 PHASE LOG `done`
  entry added without a `ci:` field fails.
- **Nightly scope** (`--all`): every `## PHASE LOG — Round 11` entry (a `done`
  entry without a `ci:` field fails; entries that are pause/blocked records are
  exempt by their own markers) and every `ci:` line in the run ledgers the
  entries name (`docs/build/runs/<ticket>.md`).

A full line `ci: pass #<n>@<sha7> (python <run>; …)` is verified per run id:
`gh api repos/{owner}/{repo}/actions/runs/<id>` must return a run whose
`head_sha` carries the recorded sha and whose `conclusion` is `success`
(`pass-after-rerun` lines record the same final state; attempt 1 lives in
`docs/build/reports/ci/flake_log.csv`). A bare field `ci: pass #<n>@<sha>`
carries no run ids — it is verified against the sha's head-bound check-runs:
every required check (record_policy/ci_required.txt) must be `success`.

Read-only: `git diff`/`gh api` GETs only — it never re-runs anything (the one
re-run per head is `ci_boundary.py`'s, H2 §4.4). Exit codes: 0 verified ·
1 usage · 3 a recorded line failed verification (or a `done` entry lacks `ci:`)
· 5 unknown (gh absent/unauthenticated, unreadable records). Never treated as
green on doubt (SIG-ENG-042: it reports `candidates`/`evaluated`).

Usage::

    verify_recorded_ci.py --diff-base origin/r11/x | --all
                          [--repo DIR] [--ledger PATH] [--gh PATH] [--json PATH]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
LEDGER_REL = "docs/build/LEDGER.md"
RUNS_REL = "docs/build/runs"
EXIT_OK, EXIT_USAGE, EXIT_FAIL, EXIT_UNKNOWN = 0, 1, 3, 5

#: `ci: pass|pass-after-rerun #<pr>@<sha7>` optionally followed by `(job runs; …)`.
CI_RE = re.compile(r"ci:\s*(pass-after-rerun|pass)\s+#(\d+)@([0-9a-fA-F]{7,40})\s*(?:\(([^)]*)\))?")
#: One job's segment inside the parens: `web 36938225132`, `docs waived`, or the
#: re-run pair `web a1 fail LH-PERF-1 run 36938225132` + `a2 pass`.
RUN_ID_RE = re.compile(r"\brun\s+(\d+)|^[A-Za-z][\w-]*\s+(\d{6,})\s*$")
SECTION_RE = re.compile(r"(?ms)^##\s+PHASE LOG — Round 11\s*$(.*?)(?=^#{2,3}\s|\Z)")
BULLET_RE = re.compile(r"(?m)^\s*-\s+(.+)$")
TICKET_RE = re.compile(r"\b(P\d+\.\d+[a-z]?)\b")
#: A PHASE LOG *entry* (vs a note bullet): `- <date> — …`.
ENTRY_RE = re.compile(r"^\s*\d{4}-\d{2}-\d{2}\s*—")
#: Markers that make a PHASE LOG entry a non-`done` record (no `ci:` owed).
NON_DONE = ("blockedon", "pause", "paused", "held", "gate", "abandoned", "reverted")


class UsageParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        print(f"verify_recorded_ci.py: {message}", file=sys.stderr)
        sys.exit(EXIT_USAGE)


class GhError(Exception):
    pass


def gh_json(gh: str, repo: Path, *args: str) -> Any:
    env = dict(
        os.environ,
        GH_PROMPT_DISABLED="1",
        GH_NO_UPDATE_NOTIFIER="1",
        GH_PAGER="cat",
        NO_COLOR="1",
    )
    try:
        proc = subprocess.run(
            [gh, *args],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except FileNotFoundError as exc:
        raise GhError(f"gh is not installed ({gh})") from exc
    except subprocess.TimeoutExpired as exc:
        raise GhError(f"`gh {' '.join(args[:2])}` timed out") from exc
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip().splitlines()
        raise GhError(f"`gh {' '.join(args[:2])}` failed: {(err or ['?'])[0][:200]}")
    try:
        return json.loads(proc.stdout)
    except ValueError as exc:
        raise GhError(f"`gh {' '.join(args[:2])}` returned unparseable JSON") from exc


@dataclass
class Claim:
    """One recorded `ci:` field: where it was found and what it claims."""

    where: str
    state: str  # pass | pass-after-rerun
    pr: int
    sha: str
    run_ids: list[str] = field(default_factory=list)


def parse_ci_line(text: str, where: str) -> list[Claim]:
    """Every full `ci:` field on a line. A `ci:` fragment that does not parse is
    a malformed claim — collected as an empty-runs claim only when it matches the
    `ci: <state> #<n>@<sha>` head, else it is returned by `stray_ci`."""
    out: list[Claim] = []
    for m in CI_RE.finditer(text):
        run_ids: list[str] = []
        for seg in (m.group(4) or "").split(";"):
            seg = seg.strip()
            rid = RUN_ID_RE.search(seg)
            if rid:
                run_ids.append(rid.group(1) or rid.group(2))
        out.append(
            Claim(
                where=where,
                state=m.group(1),
                pr=int(m.group(2)),
                sha=m.group(3).lower(),
                run_ids=run_ids,
            )
        )
    return out


#: The surfaces where a `ci:` field is a *claim* — every other file (code,
#: comments, tickets, PR-body prose) only *mentions* the token, and a
#: backticked or string-literal `ci: pass #<n>@<sha>` template there is
#: documentation, not a recorded result.
CLAIM_FILE_RE = re.compile(
    r"(?:^|/)docs/build/(?:LEDGER\.md|BUILD_INDEX\.md|runs/[^/]+\.md)$"
)
#: `ci:` asserting an outcome in claim context.
CI_TOKEN_RE = re.compile(r"(?<![\w/-])ci:\s*(?:pass-after-rerun|pass|blockedOn|fail)")
#: … occupying a field position: the line opens with the `ci:` field (modulo a
#: list/quote marker). A mid-line `ci:` in a record file — e.g. a documented
#: example `` `ci: pass #202@…` `` — is a mention, not a recorded result.
CI_FIELD_RE = re.compile(r"^\s*[-*>|]?\s*ci:\s*(?:pass-after-rerun|pass|blockedOn|fail)")


def has_stray_ci(line: str, *, bullet: bool = False, claim_file: bool = False) -> bool:
    """A `ci:`-shaped fragment that is not a parseable field — a claim we cannot
    audit. Checked only where `ci:` fields are records: PHASE LOG bullets (every
    `ci:` there is claim text) and the build-memory claim files at a field
    position. Anywhere else a `ci:` token is prose or code, not a result."""
    if CI_RE.search(line):
        return False
    if bullet:
        return bool(CI_TOKEN_RE.search(line))
    return bool(claim_file and CI_FIELD_RE.match(line))


def load_guard() -> Any:
    spec = importlib.util.spec_from_file_location("memory_guard", HERE / "memory_guard.py")
    if spec is None or spec.loader is None:
        raise ImportError("docs/build/tools/memory_guard.py not found")
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("memory_guard", mod)
    spec.loader.exec_module(mod)
    return mod


def git_diff_added(repo: Path, base: str) -> list[tuple[str, str]]:
    """`(path, added-line)` pairs of the `<base>...HEAD` diff."""
    proc = subprocess.run(
        ["git", "-C", str(repo), "diff", f"{base}...HEAD", "--unified=0"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise GhError(f"`git diff {base}...HEAD` failed: {(proc.stderr or '').strip()[:200]}")
    out: list[tuple[str, str]] = []
    path = ""
    for line in proc.stdout.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            out.append((path, line[1:]))
    return out


def phase_log_bullets(ledger: str) -> list[str]:
    m = SECTION_RE.search(ledger)
    if not m:
        return []
    return BULLET_RE.findall(m.group(1))


def collect_all(repo: Path, ledger_text: str) -> tuple[list[Claim], list[str]]:
    """Nightly scope: every Round-11 PHASE LOG claim + the run ledgers they name."""
    claims: list[Claim] = []
    missing: list[str] = []
    tickets: set[str] = set()
    for bullet in phase_log_bullets(ledger_text):
        found = parse_ci_line(bullet, "LEDGER PHASE LOG (Round 11)")
        claims.extend(found)
        if ENTRY_RE.match(bullet) and not found and not any(k in bullet.lower() for k in NON_DONE):
            missing.append(f"PHASE LOG entry with no ci: field: {bullet.strip()[:100]}")
        if has_stray_ci(bullet, bullet=True):
            missing.append(f"unparseable ci: fragment: {bullet.strip()[:100]}")
        tickets.update(TICKET_RE.findall(bullet))
    for ticket in sorted(tickets):
        ledger_path = repo / RUNS_REL / f"{ticket}.md"
        try:
            text = ledger_path.read_text(encoding="utf-8")
        except OSError:
            continue  # a named ticket without a run ledger is not a ci: claim
        for lineno, line in enumerate(text.splitlines(), 1):
            claims.extend(parse_ci_line(line, f"{RUNS_REL}/{ticket}.md:{lineno}"))
            if has_stray_ci(line, claim_file=True):
                missing.append(
                    f"unparseable ci: fragment in {RUNS_REL}/{ticket}.md:{lineno}: "
                    f"{line[:100]}"
                )
    return claims, missing


def collect_diff(repo: Path, base: str) -> tuple[list[Claim], list[str]]:
    """PR scope: `ci:` fields the change adds, and added done-entries without one."""
    claims: list[Claim] = []
    missing: list[str] = []
    for path, line in git_diff_added(repo, base):
        found = parse_ci_line(line, f"{path} (added)")
        claims.extend(found)
        body = re.sub(r"^\s*-\s+", "", line)
        entry = path.endswith("LEDGER.md") and bool(ENTRY_RE.match(body))
        if entry:
            if not found and not any(k in line.lower() for k in NON_DONE):
                missing.append(f"added PHASE LOG entry with no ci: field: {line[:100]}")
        if has_stray_ci(
            line, bullet=entry, claim_file=bool(CLAIM_FILE_RE.search(path))
        ):
            missing.append(f"unparseable ci: fragment added in {path}: {line[:100]}")
    return claims, missing


def verify(gh: str, repo: Path, claims: list[Claim], required: list[str]) -> list[str]:
    """Verify every claim against GitHub; returns the failure list."""
    failures: list[str] = []
    run_cache: dict[str, dict[str, Any]] = {}
    for c in claims:
        if c.run_ids:
            for rid in c.run_ids:
                if rid not in run_cache:
                    run_cache[rid] = gh_json(
                        gh, repo, "api", f"repos/{{owner}}/{{repo}}/actions/runs/{rid}"
                    )
                run = run_cache[rid]
                head = str(run.get("head_sha") or "")
                concl = str(run.get("conclusion") or "")
                if not head.lower().startswith(c.sha):
                    failures.append(
                        f"{c.where}: run {rid} is head {head[:7]}, not {c.sha} — the "
                        "recorded line names a run that did not run on that sha"
                    )
                elif concl != "success":
                    failures.append(
                        f"{c.where}: run {rid} concluded `{concl}` — the line records `{c.state}`"
                    )
        else:
            # A bare `ci: pass #N@sha` (the PHASE LOG form): verify the sha's
            # head-bound check-runs — every required check must be success.
            latest: dict[str, dict[str, Any]] = {}
            page = gh_json(
                gh,
                repo,
                "api",
                f"repos/{{owner}}/{{repo}}/commits/{c.sha}/check-runs?per_page=100",
            )
            for cr in (page or {}).get("check_runs", []):
                if not str(cr.get("head_sha") or "").lower().startswith(c.sha):
                    continue
                name = str(cr.get("name") or "")
                if name not in latest or int(cr.get("id") or 0) > int(latest[name].get("id") or 0):
                    latest[name] = cr
            for name in required:
                run = latest.get(name)
                if run is None:
                    failures.append(
                        f"{c.where}: `ci: {c.state} #{c.pr}@{c.sha}` but no `{name}` "
                        "check-run on that sha"
                    )
                elif (
                    str(run.get("status")) != "completed" or str(run.get("conclusion")) != "success"
                ):
                    failures.append(
                        f"{c.where}: `{name}` on {c.sha} is "
                        f"{run.get('status')}/{run.get('conclusion')} — the line records "
                        f"`{c.state}`"
                    )
    return failures


def main(argv: list[str] | None = None) -> int:
    ap = UsageParser(
        prog="verify_recorded_ci.py",
        description="Verify every recorded `ci:` line against GitHub (G3b).",
    )
    scope = ap.add_mutually_exclusive_group(required=True)
    scope.add_argument("--diff-base", metavar="REF", help="verify ci: lines added by <ref>...HEAD")
    scope.add_argument("--all", action="store_true", help="verify every Round-11 record")
    ap.add_argument("--repo", metavar="DIR", help="repository (default: git toplevel)")
    ap.add_argument("--ledger", metavar="PATH", help=f"default <repo>/{LEDGER_REL}")
    ap.add_argument("--gh", default="gh")
    ap.add_argument("--json", metavar="PATH", help="optional JSON result record")
    args = ap.parse_args(argv)

    repo = (
        Path(args.repo).resolve()
        if args.repo
        else Path(
            subprocess.run(
                ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
            ).stdout.strip()
            or "."
        )
    )
    try:
        guard = load_guard()
        required = guard.read_ci_required(
            (repo / guard.CI_REQUIRED_REL).read_text(encoding="utf-8")
        )
        ledger_text = (Path(args.ledger) if args.ledger else repo / LEDGER_REL).read_text(
            encoding="utf-8"
        )
        if args.diff_base:
            claims, missing = collect_diff(repo, args.diff_base)
        else:
            claims, missing = collect_all(repo, ledger_text)
    except (OSError, ValueError, ImportError, AttributeError) as exc:
        print(f"verify-recorded-ci: unreadable inputs: {exc}", file=sys.stderr)
        return EXIT_UNKNOWN

    failures = list(missing)
    if args.all and not claims and not missing:
        failures.append("no Round-11 PHASE LOG entries found — a vacuous verification")
    if claims:
        try:
            failures.extend(verify(args.gh, repo, claims, required))
        except GhError as exc:
            print(f"verify-recorded-ci: {exc}", file=sys.stderr)
            return EXIT_UNKNOWN

    report = {
        "schema": "recorded-ci-verify/1",
        "scope": f"diff-base:{args.diff_base}" if args.diff_base else "all",
        "candidates": len(claims),
        "evaluated": len(claims),
        "failures": failures,
        "claims": [
            {"where": c.where, "state": c.state, "pr": c.pr, "sha": c.sha, "runs": c.run_ids}
            for c in claims
        ],
    }
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for f in failures:
        print(f"verify-recorded-ci: FAIL {f}", file=sys.stderr)
    print(
        f"verify-recorded-ci: candidates={len(claims)} evaluated={len(claims)} "
        f"failures={len(failures)}"
    )
    return EXIT_FAIL if failures else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
