#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""CI boundary gate G3a — `ci-boundary/1` (Round 11 Stage B, SEED-02b; B4 G3a, H2 §4, plan App. A T2).

The repo hook of the orchestrate-build skill's `ci-boundary.sh` (BM-CI-01): when this file exists the
skill runs `python3 docs/build/tools/ci_boundary.py --pr <n> --json <path>` from the worktree and passes
the exit code through, so this tool owns the required set, the stack and the wait.

What it reads (read-only `gh` and `git`; it never mutates anything):

- the PR (`gh pr view`): head sha, head and base branch, state, draft flag, mergeable;
- the **head-bound check-runs** of that sha (`gh api repos/{owner}/{repo}/commits/<sha>/check-runs`,
  GitHub Actions only, the highest id per name) — never `gh pr checks`, whose JSON names no sha and can
  attribute a superseded head's result (H2 §4.1, NEW-12);
- the stack: each open PR whose head is the previous PR's base, **only while that base is an `r11/`
  branch**. The Round-10 stack #141–#190 is never read (B-15; plan App. A T2), so its red heads
  #165/#179/#185 cannot block a Round-11 boundary. A requested PR outside that scope — e.g. #190, the PR
  of `lastCompleted: P33.8` at the first boundary — is not read either: the tool reads the open PR of the
  LEDGER's `chainTip` instead when that is an `r11/` branch, and says so in the record;
- the required set, `record_policy/ci_required.txt`, through `memory_guard.read_ci_required()`;
- operator waivers: 7-column GATE DECISIONS rows of kind `waiver` naming `#<n>` and the check
  (BM-GATE-05; the skill's rule — a waiver covers the named PR only).

**Green** — every PR of the stack is OPEN, not a draft, not CONFLICTING, its head did not move during the
read; the current PR's local branch, when the repo has one, is at the PR head; and every required
check-run on every head is `completed` with `success` (or a failure the operator waived). **Pending** — a
required check is queued or running, or not registered yet. **Red** — everything else: `failure`,
`cancelled`, `timed_out`, `action_required`, `startup_failure`, `stale`, `neutral`, a `skipped` required
job, a required check still missing with no workflow run queued for the sha, a moved head, a stack with a
gap, a closed or draft PR, conflicts. "Green locally" is never green (P11).

**Wait.** Poll every `--interval` s (60) up to `--max-wait` s (2,700 = 45 min, H2 §4.3); `--no-wait`
reads once (a missing check is then pending). A required check still missing after `--grace` s (300) of
waiting while no workflow run is registered for the sha is red (`missing`: the workflow did not
trigger). A `gh` error is retried after `--backoff` s (30,60,120) and then exits 5; an authentication
error is not retried.

**Output.** The `ci-boundary/1` JSON at `--json` and, as the last stdout line, the line to record:
`ci: pass #<n>@<sha7> (python <run>; docs <run>; composed <run>; security <run>; web <run>)[ · stack: #a
pass][ · waived: …]`, or `blockedOn: CI <fail|cancel|missing|pending|unavailable|conflict|stack> on
#<n>@<sha7> (<check>): <detail>` (H2 §4.5).

Exit codes (the skill's hook contract, `ci-boundary.sh`): 0 pass · 1 usage · 3 red · 4 still pending
after the wait · 5 unknown — `gh` absent, unauthenticated or offline, checks unreadable, the required set
unreadable, or an out-of-scope PR with no `r11/` chainTip PR. Never treated as green.

Usage::

    ci_boundary.py --pr <n> --json <path> [--repo DIR] [--ledger PATH] [--prefix r11/]
                   [--interval S] [--max-wait S | --no-wait] [--grace S] [--backoff 30,60,120] [--gh PATH]

Python 3.9+ (the skill runs it with whatever `python3` is on PATH — macOS's system Python is 3.9),
stdlib, `git` and `gh` only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NoReturn

SCHEMA = "ci-boundary/1"
EXIT_PASS, EXIT_USAGE, EXIT_RED, EXIT_PENDING, EXIT_UNKNOWN = 0, 1, 3, 4, 5
HERE = Path(__file__).resolve().parent
LEDGER_REL = "docs/build/LEDGER.md"
DEFAULT_PREFIX = "r11/"
# The Round-10 stack (#141–#190): never read by a Round-11 boundary (B-15; plan App. A T2 SEED-02).
ROUND10_PRS = range(141, 191)
GITHUB_ACTIONS = "github-actions"
RED_CONCLUSIONS = {
    "failure",
    "cancelled",
    "timed_out",
    "action_required",
    "startup_failure",
    "stale",
    "neutral",
    "skipped",
}
ACTIVE_STATUSES = {"queued", "in_progress", "waiting", "requested", "pending"}
RUN_ID_RE = re.compile(r"/actions/runs/(\d+)")
AUTH_RE = re.compile(r"gh auth login|authentication|not logged in|HTTP 401|Bad credentials", re.I)
PR_FIELDS = "number,state,isDraft,headRefOid,headRefName,baseRefName,mergeable,url"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: UP017 (3.9)


def load_guard() -> Any:
    """`memory_guard` (same directory) — the single reader of `record_policy/ci_required.txt`."""
    spec = importlib.util.spec_from_file_location("memory_guard", HERE / "memory_guard.py")
    if spec is None or spec.loader is None:
        raise ImportError("docs/build/tools/memory_guard.py not found")
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("memory_guard", mod)
    spec.loader.exec_module(mod)
    return mod


# ── gh (read-only) ───────────────────────────────────────────────────────────


class GhError(Exception):
    pass


class Gh:
    """Runs read-only `gh` commands in the repo; retries transient errors, never an auth error."""

    def __init__(
        self,
        exe: str,
        cwd: Path,
        backoff: list[float],
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.exe, self.cwd, self.backoff, self.sleep = exe, cwd, backoff, sleep
        self.env = dict(os.environ, GH_PROMPT_DISABLED="1", GH_NO_UPDATE_NOTIFIER="1", NO_COLOR="1")
        self.env["GH_PAGER"] = "cat"

    def run(self, *args: str, retry: bool = True) -> str:
        waits = [0.0, *self.backoff] if retry else [0.0]
        last = ""
        for wait in waits:
            if wait:
                self.sleep(wait)
            try:
                proc = subprocess.run(
                    [self.exe, *args],
                    cwd=self.cwd,
                    env=self.env,
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
            except FileNotFoundError as exc:
                raise GhError(f"gh is not installed ({self.exe})") from exc
            except subprocess.TimeoutExpired:
                last = "timed out after 180 s"
                continue
            if proc.returncode == 0:
                return proc.stdout
            err = (proc.stderr or proc.stdout or "").strip()
            last = err.splitlines()[0][:200] if err else f"exit {proc.returncode}"
            if AUTH_RE.search(err):
                raise GhError(f"gh is not authenticated: {last}")
        tries = len(waits)
        raise GhError(f"`gh {' '.join(args[:2])}` failed {tries}× ({last})")

    def json(self, *args: str, retry: bool = True) -> Any:
        out = self.run(*args, retry=retry)
        try:
            return json.loads(out)
        except ValueError as exc:
            raise GhError(f"`gh {' '.join(args[:2])}` returned unparseable JSON") from exc

    def json_pages(self, *args: str) -> list[Any]:
        """`gh api --paginate` prints one JSON document per page, back to back."""
        out = self.run(*args).strip()
        dec = json.JSONDecoder()
        docs: list[Any] = []
        i = 0
        while i < len(out):
            if out[i].isspace():
                i += 1
                continue
            try:
                doc, i = dec.raw_decode(out, i)
            except ValueError as exc:
                raise GhError(f"`gh {' '.join(args[:2])}` returned unparseable JSON") from exc
            docs.append(doc)
        return docs


# ── records ──────────────────────────────────────────────────────────────────


@dataclass
class PR:
    number: int
    head_ref: str
    head_sha: str
    base_ref: str
    state: str
    is_draft: bool
    mergeable: str
    url: str = ""

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> PR:
        return cls(
            number=int(d["number"]),
            head_ref=str(d.get("headRefName") or ""),
            head_sha=str(d.get("headRefOid") or ""),
            base_ref=str(d.get("baseRefName") or ""),
            state=str(d.get("state") or "").upper(),
            is_draft=bool(d.get("isDraft")),
            mergeable=str(d.get("mergeable") or "").upper(),
            url=str(d.get("url") or ""),
        )

    @property
    def sha7(self) -> str:
        return self.head_sha[:7]


@dataclass
class Verdict:
    state: str  # pass | fail | pending
    kind: str = ""  # fail | cancel | missing | pending | conflict | stack
    check: str = "-"
    detail: str = ""


@dataclass
class Ctx:
    required: list[str]
    waivers: list[str]
    final: bool
    waited: float
    grace: float
    single_read: bool
    checks: list[dict[str, Any]] = field(default_factory=list)


def run_id_of(url: str) -> str:
    m = RUN_ID_RE.search(url or "")
    return m.group(1) if m else ""


def read_ledger(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def ledger_value(text: str, key: str) -> str:
    """The value of a CURRENT STATE key (first token; a trailing `# comment` is annotation)."""
    m = re.search(rf"(?m)^\s*{re.escape(key)}:\s*(.*?)\s*$", text)
    if not m:
        return ""
    v = re.sub(r"(?:^|\s)#.*$", "", m.group(1)).strip()
    return v.split()[0] if v else ""


def ledger_waivers(text: str) -> list[str]:
    """Rows of 7-column GATE DECISIONS tables (header's last cell `kind`) whose kind is `waiver`."""
    rows: list[str] = []
    in_gd = header_kind = False
    for line in text.splitlines():
        if re.match(r"^##\s", line):
            in_gd = bool(re.match(r"^##\s+GATE DECISIONS", line))
            header_kind = False
            continue
        if not in_gd or not line.startswith("|"):
            continue
        cells = [re.sub(r"[\s`*]", "", c) for c in line.split("|")]
        last = next((c for c in reversed(cells) if c), "")
        if last == "kind":
            header_kind = True
        elif last == "consequence":
            header_kind = False
        elif header_kind and last == "waiver":
            rows.append(line)
    return rows


def waived(waivers: list[str], pr: int, check: str) -> bool:
    pr_re = re.compile(rf"#{pr}(?![0-9])")
    name_re = re.compile(rf"(?<![A-Za-z0-9_-]){re.escape(check)}(?![A-Za-z0-9_-])")
    return any(pr_re.search(w) and name_re.search(w) for w in waivers)


# ── the gate ─────────────────────────────────────────────────────────────────


class Boundary:
    def __init__(self, gh: Gh, repo: Path, prefix: str) -> None:
        self.gh, self.repo, self.prefix = gh, repo, prefix
        self._runs_cache: dict[str, list[dict[str, Any]]] = {}

    def out_of_scope(self, pr: PR) -> bool:
        return pr.number in ROUND10_PRS or not pr.head_ref.startswith(self.prefix)

    def view(self, number: int) -> PR:
        return PR.from_json(self.gh.json("pr", "view", str(number), "--json", PR_FIELDS))

    def pr_for_head(self, branch: str, state: str) -> PR | None:
        got = self.gh.json(
            "pr", "list", "--head", branch, "--state", state, "--json", PR_FIELDS, "--limit", "20"
        )
        prs = [PR.from_json(d) for d in got or [] if d.get("headRefName") == branch]
        if state == "all":  # a merged PR explains a gap better than a closed one
            prs.sort(key=lambda p: (p.state != "MERGED", -p.number))
        else:
            prs.sort(key=lambda p: -p.number)
        return prs[0] if prs else None

    def local_head(self, branch: str) -> str:
        proc = subprocess.run(
            ["git", "-C", str(self.repo), "rev-parse", "--verify", "-q", f"refs/heads/{branch}"],
            capture_output=True,
            text=True,
        )
        return proc.stdout.strip() if proc.returncode == 0 else ""

    def walk(self, current: PR) -> tuple[list[PR], str, Verdict | None]:
        """The current PR and its open `r11/` ancestors, the reason the walk stopped, and a stack
        verdict when the walk itself found a gap."""
        stack = [current]
        base = current.base_ref
        seen = {current.number}
        for _ in range(200):
            if not base.startswith(self.prefix):
                return (
                    stack,
                    f"base `{base}` is outside the `{self.prefix}` scope — the Round-10 stack "
                    "(#141–#190) is never read (B-15)",
                    None,
                )
            anc = self.pr_for_head(base, "open")
            if anc is None:
                other = self.pr_for_head(base, "all")
                if other is not None and other.state == "MERGED":
                    return stack, f"base `{base}` is #{other.number}, already merged", None
                return (
                    stack,
                    f"base `{base}` has no open PR",
                    Verdict(
                        "fail",
                        "stack",
                        "-",
                        f"stack gap: base `{base}` of #{stack[-1].number} has no open PR",
                    ),
                )
            if anc.number in seen or anc.number in ROUND10_PRS:
                return (
                    stack,
                    f"ancestor #{anc.number} is outside the walk (cycle or Round-10 PR)",
                    None,
                )
            seen.add(anc.number)
            stack.append(anc)
            base = anc.base_ref
        return (
            stack,
            "stopped after 200 hops",
            Verdict("fail", "stack", "-", "stack deeper than 200 PRs"),
        )

    def check_runs(self, sha: str) -> list[dict[str, Any]]:
        pages = self.gh.json_pages(
            "api", f"repos/{{owner}}/{{repo}}/commits/{sha}/check-runs?per_page=100", "--paginate"
        )
        runs: list[dict[str, Any]] = []
        for page in pages:
            runs.extend(page.get("check_runs", []) if isinstance(page, dict) else [])
        return runs

    def workflow_runs(self, sha: str) -> list[dict[str, Any]]:
        if sha not in self._runs_cache:
            self._runs_cache[sha] = (
                self.gh.json(
                    "run",
                    "list",
                    "--commit",
                    sha,
                    "--json",
                    "databaseId,status,conclusion,workflowName,event",
                    "--limit",
                    "50",
                )
                or []
            )
        return self._runs_cache[sha]

    def first_annotation(self, check_run_id: int) -> str:
        try:
            got = self.gh.json(
                "api",
                f"repos/{{owner}}/{{repo}}/check-runs/{check_run_id}/annotations",
                retry=False,
            )
        except GhError:
            return ""
        for a in got or []:
            if isinstance(a, dict) and a.get("annotation_level") in ("failure", None, ""):
                return " ".join(str(a.get("message") or "").split())[:160]
        return ""

    def judge(self, pr: PR, ctx: Ctx) -> Verdict:
        """One PR's verdict on its recorded head; appends its check records to `ctx.checks`."""
        latest: dict[str, dict[str, Any]] = {}
        for cr in self.check_runs(pr.head_sha):
            app = (cr.get("app") or {}).get("slug", GITHUB_ACTIONS)
            if app != GITHUB_ACTIONS or cr.get("head_sha", pr.head_sha) != pr.head_sha:
                continue
            name = str(cr.get("name") or "")
            if name not in latest or int(cr.get("id") or 0) > int(latest[name].get("id") or 0):
                latest[name] = cr
        verdicts: list[Verdict] = []
        if pr.state != "OPEN":
            verdicts.append(Verdict("fail", "stack", "-", f"#{pr.number} is {pr.state.lower()}"))
        elif pr.is_draft:
            verdicts.append(Verdict("fail", "stack", "-", f"#{pr.number} is a draft"))
        elif pr.mergeable == "CONFLICTING":
            verdicts.append(
                Verdict("fail", "conflict", "-", f"#{pr.number} conflicts with `{pr.base_ref}`")
            )
        for name in sorted(set(latest) - set(ctx.required)):
            ctx.checks.append(self.record(pr, name, latest[name], required=False, bucket="info"))
        for name in ctx.required:
            run = latest.get(name)
            if run is None:
                v = self.missing(pr, name, ctx)
                ctx.checks.append(
                    {
                        "pr": pr.number,
                        "name": name,
                        "required": True,
                        "bucket": "missing",
                        "waived": False,
                    }
                )
                verdicts.append(v)
                continue
            status = str(run.get("status") or "").lower()
            concl = str(run.get("conclusion") or "").lower()
            if status != "completed":
                ctx.checks.append(self.record(pr, name, run, required=True, bucket="pending"))
                verdicts.append(Verdict("pending", "pending", name, status or "not completed"))
            elif concl == "success":
                ctx.checks.append(self.record(pr, name, run, required=True, bucket="pass"))
            else:
                w = waived(ctx.waivers, pr.number, name)
                ctx.checks.append(
                    self.record(pr, name, run, required=True, bucket="fail", waived=w)
                )
                if not w:
                    note = self.first_annotation(int(run.get("id") or 0)) if run.get("id") else ""
                    rid = run_id_of(str(run.get("details_url") or ""))
                    detail = (concl or "no conclusion") + (f" — {note}" if note else "")
                    detail += f" (run {rid})" if rid else ""
                    kind = "cancel" if concl == "cancelled" else "fail"
                    verdicts.append(Verdict("fail", kind, name, detail))
        for want in ("fail", "pending"):
            hit = next((v for v in verdicts if v.state == want), None)
            if hit:
                return hit
        return Verdict("pass")

    def missing(self, pr: PR, name: str, ctx: Ctx) -> Verdict:
        if ctx.single_read or (not ctx.final and ctx.waited < ctx.grace):
            return Verdict("pending", "pending", name, "required check not reported yet")
        active = [
            r
            for r in self.workflow_runs(pr.head_sha)
            if str(r.get("status") or "").lower() in ACTIVE_STATUSES
        ]
        if active:
            r = active[0]
            return Verdict(
                "pending",
                "pending",
                name,
                f"required check not registered; workflow run {r.get('databaseId')} is {r.get('status')}",
            )
        return Verdict(
            "fail",
            "missing",
            name,
            f"required check missing — no workflow run queued for {pr.sha7}",
        )

    @staticmethod
    def record(
        pr: PR, name: str, run: dict[str, Any], *, required: bool, bucket: str, waived: bool = False
    ) -> dict[str, Any]:
        link = str(run.get("details_url") or run.get("html_url") or "")
        return {
            "pr": pr.number,
            "name": name,
            "required": required,
            "check_run_id": run.get("id"),
            "run_id": run_id_of(link),
            "status": run.get("status"),
            "conclusion": run.get("conclusion"),
            "bucket": bucket,
            "started_at": run.get("started_at"),
            "completed_at": run.get("completed_at"),
            "link": link,
            "waived": waived,
        }


# ── driver ───────────────────────────────────────────────────────────────────


class UsageParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        print(f"ci_boundary.py: {message}", file=sys.stderr)
        sys.exit(EXIT_USAGE)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = UsageParser(prog="ci_boundary.py", description="CI boundary gate G3a (ci-boundary/1).")
    ap.add_argument("--pr", required=True, help="the PR to read (`123` or `#123`)")
    ap.add_argument(
        "--json", required=True, metavar="PATH", help="where to write the ci-boundary/1 record"
    )
    ap.add_argument(
        "--repo", metavar="DIR", help="the repository (default: the current git toplevel)"
    )
    ap.add_argument(
        "--ledger", metavar="PATH", help=f"the build ledger (default: <repo>/{LEDGER_REL})"
    )
    ap.add_argument(
        "--prefix", default=DEFAULT_PREFIX, help="the round's branch prefix (default r11/)"
    )
    ap.add_argument("--interval", type=float, default=60.0, help="poll interval in seconds (60)")
    ap.add_argument(
        "--max-wait", type=float, default=2700.0, dest="max_wait", help="bounded wait (2700)"
    )
    ap.add_argument("--no-wait", action="store_true", dest="no_wait", help="read once")
    ap.add_argument(
        "--grace", type=float, default=300.0, help="registration grace in seconds (300)"
    )
    ap.add_argument("--backoff", default="30,60,120", help="gh retry waits in seconds (30,60,120)")
    ap.add_argument("--gh", default="gh", help="the gh executable (default: gh on PATH)")
    args = ap.parse_args(argv)
    pr = str(args.pr).lstrip("#")
    if not pr.isdigit():
        ap.error(f"--pr must be a number, got '{args.pr}'")
    args.pr = int(pr)
    try:
        args.backoff = [float(x) for x in str(args.backoff).split(",") if x.strip()]
    except ValueError:
        ap.error("--backoff wants comma-separated seconds")
    if min([args.interval, args.max_wait, args.grace, *args.backoff]) < 0:
        ap.error("times must be >= 0")
    if args.no_wait:
        args.max_wait = 0.0
    return args


def repo_root(arg: str | None) -> Path:
    start = Path(arg).resolve() if arg else Path.cwd()
    top = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    return Path(top.stdout.strip()) if top.returncode == 0 else start


@dataclass
class Out:
    json_path: Path
    doc: dict[str, Any]

    def emit(self, state: str, code: int, line: str, kind: str = "") -> int:
        self.doc.update({"state": state, "kind": kind or None, "line": line, "exit": code})
        try:
            self.json_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.json_path.with_name(self.json_path.name + ".tmp")
            tmp.write_text(
                json.dumps(self.doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            tmp.replace(self.json_path)
        except OSError as exc:
            print(
                f"ci_boundary.py: cannot write the record {self.json_path}: {exc}", file=sys.stderr
            )
            print(
                f"blockedOn: CI unavailable on #{self.doc.get('pr')} (record): the record could not be written"
            )
            return EXIT_UNKNOWN
        print(f"ci-boundary: record → {self.json_path}")
        print(line)
        return code


def stack_digest(stack: list[PR]) -> str:
    body = "".join(f"{p.number} {p.head_sha}\n" for p in stack)
    return hashlib.sha256(body.encode()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo = repo_root(args.repo)
    json_path = Path(args.json)
    if not json_path.is_absolute():
        json_path = Path.cwd() / json_path
    ledger_path = Path(args.ledger) if args.ledger else repo / LEDGER_REL
    out = Out(
        json_path,
        {
            "schema": SCHEMA,
            "tool": "docs/build/tools/ci_boundary.py",
            "requested_pr": args.pr,
            "pr": args.pr,
            "head_sha": None,
            "head_ref": None,
            "base": None,
            "read_at": utc_now(),
            "prefix": args.prefix,
            "scope": f"the current {args.prefix} PR and its open {args.prefix} ancestors; never #141–#190",
            "required": None,
            "stack": [],
            "stack_stop": None,
            "stack_digest": None,
            "local_head": None,
            "checks": [],
            "waivers": 0,
            "polls": 0,
            "waited_s": 0,
        },
    )

    def unknown(where: str, detail: str) -> int:
        return out.emit(
            "unknown",
            EXIT_UNKNOWN,
            f"blockedOn: CI unavailable on {where}: {detail}",
            "unavailable",
        )

    try:
        guard = load_guard()
        required = guard.read_ci_required(
            (repo / guard.CI_REQUIRED_REL).read_text(encoding="utf-8")
        )
    except (OSError, ValueError, ImportError, AttributeError) as exc:
        return unknown(
            f"#{args.pr} (required set)", f"cannot read record_policy/ci_required.txt: {exc}"
        )
    out.doc["required"] = required
    ledger = read_ledger(ledger_path)
    waivers = ledger_waivers(ledger)
    out.doc["waivers"] = len(waivers)
    gh = Gh(args.gh, repo, args.backoff)
    b = Boundary(gh, repo, args.prefix)

    try:
        pr: PR | None = None
        if args.pr not in ROUND10_PRS:  # never even viewed: #141–#190 are out of scope by number
            pr = b.view(args.pr)
        if pr is None or b.out_of_scope(pr):
            tip = ledger_value(ledger, "chainTip")
            cand = b.pr_for_head(tip, "open") if tip.startswith(args.prefix) else None
            if cand is None or b.out_of_scope(cand):
                return unknown(
                    f"#{args.pr} (scope)",
                    f"#{args.pr} is outside the {args.prefix} scope (never #141–#190, B-15) and the LEDGER "
                    f"chainTip `{tip or '(unset)'}` names no open {args.prefix} PR",
                )
            out.doc["redirect"] = (
                f"#{args.pr} is outside the {args.prefix} scope (B-15); read the chainTip `{tip}` PR "
                f"#{cand.number} instead"
            )
            pr = cand
        out.doc.update(
            {"pr": pr.number, "head_sha": pr.head_sha, "head_ref": pr.head_ref, "base": pr.base_ref}
        )

        local = b.local_head(pr.head_ref)
        out.doc["local_head"] = local or None
        stack, stop, gap = b.walk(pr)
        recorded = {p.number: p.head_sha for p in stack}
        out.doc["stack_stop"] = stop
        out.doc["stack_digest"] = stack_digest(stack)
        if local and local != pr.head_sha:
            gap = gap or Verdict(
                "fail",
                "stack",
                "-",
                f"local `{pr.head_ref}` is at {local[:7]}, the PR head is {pr.sha7} — push or re-sync the chain "
                "tip before the boundary",
            )

        start = time.monotonic()
        while True:
            waited = time.monotonic() - start
            final = args.max_wait <= 0 or waited + args.interval >= args.max_wait
            ctx = Ctx(required, waivers, final, waited, args.grace, single_read=args.max_wait <= 0)
            out.doc["polls"] += 1
            out.doc["waited_s"] = round(waited, 1)
            fresh: list[PR] = []
            moved: Verdict | None = None
            for p in stack:
                now = b.view(p.number)
                if now.head_sha != recorded[p.number] and moved is None:
                    moved = Verdict(
                        "fail",
                        "stack",
                        "-",
                        f"#{p.number} head moved {recorded[p.number][:7]} → {now.sha7} during the read",
                    )
                fresh.append(now)
            verdicts = [b.judge(p, ctx) for p in fresh]
            out.doc["stack"] = [
                {
                    "pr": p.number,
                    "head_ref": p.head_ref,
                    "head_sha": p.head_sha,
                    "base": p.base_ref,
                    "pr_state": p.state,
                    "is_draft": p.is_draft,
                    "mergeable": p.mergeable,
                    "state": v.state,
                    "detail": v.detail or None,
                }
                for p, v in zip(fresh, verdicts)  # noqa: B905 (3.9 has no strict=)
            ]
            out.doc["checks"] = ctx.checks
            red = gap or moved
            red_pr = fresh[0]
            if red is None:
                for p, v in zip(fresh, verdicts):  # noqa: B905 (3.9 has no strict=)
                    if v.state == "fail":
                        red, red_pr = v, p
                        break
            if red is not None:
                return out.emit(
                    "fail",
                    EXIT_RED,
                    f"blockedOn: CI {red.kind} on #{red_pr.number}@{red_pr.sha7} ({red.check}): {red.detail}",
                    red.kind,
                )
            pairs = list(zip(fresh, verdicts))  # noqa: B905 (3.9 has no strict=; equal by construction)
            pend = next(((p, v) for p, v in pairs if v.state == "pending"), None)
            if pend is None:
                redirected = args.pr if out.doc.get("redirect") else None
                return out.emit("pass", EXIT_PASS, pass_line(fresh, ctx, redirected))
            if final:
                p, v = pend
                return out.emit(
                    "pending",
                    EXIT_PENDING,
                    f"blockedOn: CI pending on #{p.number}@{p.sha7} ({v.check}): {v.detail} after "
                    f"{round(waited)} s of {round(args.max_wait)} s",
                    "pending",
                )
            print(
                f"ci-boundary: #{pend[0].number} pending ({pend[1].check}: {pend[1].detail}) — re-reading in "
                f"{args.interval:g} s (waited {waited:.0f} s of {args.max_wait:g} s)",
                file=sys.stderr,
            )
            time.sleep(args.interval)
    except GhError as exc:
        return unknown(f"#{out.doc['pr']} (gh)", str(exc))
    except (KeyError, TypeError, ValueError) as exc:  # a gh answer without the fields read above
        return unknown(f"#{out.doc['pr']} (gh)", f"unexpected gh output: {exc!r}"[:200])


def pass_line(stack: list[PR], ctx: Ctx, redirected_from: int | None) -> str:
    cur = stack[0]
    jobs = []
    for c in ctx.checks:
        if c["pr"] != cur.number or not c["required"]:
            continue
        jobs.append(f"{c['name']} waived" if c["waived"] else f"{c['name']} {c['run_id'] or '-'}")
    line = f"ci: pass #{cur.number}@{cur.sha7} ({'; '.join(jobs)})"
    if len(stack) > 1:
        line += " · stack: " + " ".join(f"#{p.number}" for p in stack[1:]) + " pass"
    anc_waived = [
        f"#{c['pr']} {c['name']}" for c in ctx.checks if c["waived"] and c["pr"] != cur.number
    ]
    if anc_waived:
        line += " · waived: " + ", ".join(anc_waived)
    if redirected_from is not None:
        line += f" · requested #{redirected_from} out of scope (B-15)"
    return line


if __name__ == "__main__":
    sys.exit(main())
