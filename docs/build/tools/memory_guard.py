#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Build-memory record guard — `memory-guard/1` (Round 11 Stage B, SEED-02; design B4 G1/G2/G4).

The structural validators read the *shape of the current tree*; this guard reads a **change** (a PR
range, one first-parent commit, the index, or the working tree) and judges only the lines that change
adds or removes, with each added line carrying the committer time of the commit that added it. It is
the repo hook the build-memory skill's history mode delegates to (`check-history.sh` runs
`memory_guard.py all <mode args> [--json PATH] [--now ISO]` and passes the exit code through), so it
implements every history-mode rule of the skill (BM-HIST-01) plus SIG's own:

- **G1 record-dates (diff mode).** A record date the change adds in a build-memory record position is
  not later than its commit (+5 min) nor the clock (R1); an act is not back-dated more than 48 h unless
  the line says `≤`, `retro:` or `as-of` (R2); a correction line may quote a wrong date when it also
  carries the true one (R3); `future-ok: <scheduled|real-world|synthetic|illustrative>: <reason>` or an
  unexpired `allow` entry exempts R1 (R5); no commit is later than the clock (R6). An unparseable stamp
  such as `18:2xZ` takes its lowest reading and is reported as malformed. Scope: build-memory records
  only — `docs/build/LEDGER.md`, `BUILD_INDEX.md`, `runs/`, `pr/`, `readouts/`, `reports/`,
  `docs/tickets/`, `docs/adr/` — plus the policy's `date` paths; **never `docs/build/planning/**`**.
- **G1 restored-dates (blame mode).** For a GATE DECISIONS block appended under a caption
  `RESTORED from `<sha>^``, every restored row must exist verbatim at `<sha>^`, and its date is judged
  (R1/R2) against `git blame` of that source line — the commit that originally wrote it. A clock-false
  row must be annotated: a row `| R<n> | … clock-false | DATE CORRECTION … |` in a table after the
  block, or a `date_corrections.csv` row whose `line_or_field` names `restored R<n>`.
- **G2 append-only (core).** LEDGER `GATE DECISIONS` / `PHASE LOG*` / `OPEN FINDINGS*` / `RETURN PASS*`
  lose no line and grow only after their last line; other LEDGER regions lose no line; the living head
  is replaced only when the removed text is archived byte-for-byte in the same change with a pointer
  (living-archived); DEFERRALS rows only grow (row-annotate); readouts change only their `Status:`
  line; closed run ledgers only gain lines; executed contracts take only `> Amended <date>:` notes;
  landed ADRs take only an appended `## Status updates` section (`- **Status:** <Superseded|Qualified|
  Amended|Extended|Revisited> by ADR-NNN (<date>)` bullets + notes) or `### Trigger evaluation …`
  subsections at the end of `## Revisit trigger`; `*.jsonl` keep their byte prefix; policy
  `append-only` files (e.g. `db/sqitch.plan`) only append at EOF; BUILD_INDEX and the manifest's
  append-only sections lose no line.
- **Record shape (skill parity).** Added BUILD_INDEX rows have the header's column count, a fresh seq
  and a real PR; new chain rows sit under a numbered `### Round <n>` banner and never re-bind an id;
  owed kind-P DEFERRALS rows carry `owner:`/`trigger:` (a violation under the guards marker).
- **G4a gate records.** Rows added to a 7-column GATE DECISIONS table: `date` is ISO-8601 Z; `kind` ∈
  decision | pre-authorization | confirmation | waiver | correction | date-correction; the answer holds
  the operator's words in quotes or `provided: yes/no`; a pre-authorization names its items,
  `expires:` and `voided-by:`; hedged words (`?`, "I wonder", "perhaps", "maybe", "should just",
  "I think … but") need a later plain `confirmation` row; delegation ("sign … for me", "on my behalf",
  "<x>'s judgement", "delegate") fails; a `decision` for a gate is dated at or after that gate's
  PHASE LOG pause in the same round (a chain marker with no recorded pause fails).
- **G4b readouts.** A new readout carries the guard sentence; a readout changes only its single
  `Status:` line (PENDING → SIGNED | PASSED | SKIPPED-BY-OPERATOR | NOT-PASSABLE) and appends; a signing
  diff adds only the Signature block (operator words that equal a GATE DECISIONS answer, the row
  pointer, a confirmation quoting the agent-drafted hash prefix, `Signed by:`), agent-drafted blocks
  whose sha256 matches their body, and no checkbox ticks or unlabelled prose.
- **G11 no-vacuous-pass.** Every check reports `candidates` and `evaluated`; a check that was offered
  candidates and evaluated none exits 3.

Usage::

    memory_guard.py {all|dates|append-only|gates|readouts}
                    (--range BASE..HEAD | --range BASE...HEAD | --staged | --first-parent SHA | --worktree)
                    [--json PATH] [--now ISO] [--repo DIR]
    memory_guard.py restored [--rev REV | --worktree] [--json PATH] [--now ISO] [--repo DIR]
    memory_guard.py replay FROM..TO [--json PATH] [--now ISO] [--repo DIR]

`--worktree` (this tool only) judges uncommitted working-tree changes against HEAD, untracked files
included, with commit time = now; `replay` judges every first-parent commit of FROM..TO on its own
(read-only backtest). Python 3.11+, stdlib and `git` only.

**Landed records (SEED-02b).** A protected record is *landed* — its frozen/append-only rules apply —
only if it exists at the landed base: the range's base (`A`, or the merge-base for `A...B`), the parent
for `--first-parent`, and for `--staged`/`--worktree` the merge-base of HEAD with the LEDGER's
`pinnedBaseSha` (else `buildBranchBase`; else HEAD). A record the branch added after that base (a seed
ADR) may still be edited or removed until it is merged; its edits are judged as a new file's. The four
control files (LEDGER, DEFERRALS, BUILD_INDEX, manifest) keep their region rules.

Policy: `docs/build/tools/record_policy/history.policy` (also read by the skill's `check-history.sh`):
`append-only <glob>`, `date <glob> <ERE>`, `allow <glob> <expires ISO> <fixed text>`,
`exempt <path> <heading text>`, `archive <dir>`, and (this tool only) `act-when <glob> <ERE>`.
`record_policy/ci_required.txt` (the G3a required check names) is read with `read_ci_required()`.

Report: `memory-guard/1` JSON at `--json PATH`:
`{schema, tool, input:{repo, mode, base, head, landed_base, landed_from, ci_now, policy_sha256, guards}, summary:{violations,
warnings, exit}, checks:[{check, candidates, evaluated, violations:[…], warnings:[…]}], restored:[…],
exit}`; each finding is `{check, rule, path, line, commit, message}`.

Exit codes: 0 clean · 1 violations · 2 usage error or not a build-memory repo · 3 vacuous pass (a
check evaluated none of its candidates) · 5 unknown (shallow clone, unresolvable revision, git
failure) — never treated as green.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import fnmatch
import hashlib
import io
import json
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

SCHEMA = "memory-guard/1"
EXIT_OK, EXIT_VIOLATIONS, EXIT_USAGE, EXIT_VACUOUS, EXIT_UNKNOWN = 0, 1, 2, 3, 5
TOLERANCE_S = 300  # R1/R6: +5 min
ACT_WINDOW_S = 48 * 3600  # R2: 48 h

POLICY_REL = "docs/build/tools/record_policy/history.policy"
README_REL = "docs/build/README.md"
LEDGER_REL = "docs/build/LEDGER.md"
DEFERRALS_REL = "docs/tickets/DEFERRALS.md"
INDEX_REL = "docs/build/BUILD_INDEX.md"
MANIFEST_REL = "docs/tickets/00_MANIFEST.md"
DATE_CORRECTIONS_REL = "docs/build/reports/memory-repair/date_corrections.csv"
ARCHIVE_DEFAULT = "docs/build/reports/ledger-archive"
BM_MARKER = "<!-- build-memory: v2 -->"
GUARDS_RE = re.compile(r"^\s*<!-- build-memory-guards: 1 -->\s*$", re.M)

# G1 scope: build-memory records only. The planning tree is never judged (S6R-10); logs are gitignored.
SCOPE = ("docs/build", "docs/tickets", "docs/adr")
EXCLUDED = ("docs/build/planning/", "docs/build/logs/")

STATE_KEYS = (
    "projectStatus nextTicket lastCompleted blockedOn pauseRequested returnPass manifest canonicalSpec "
    "memoryRoot dispatchTarget buildWorktree buildBranchBase pinnedBaseSha chainTip benchmarkSet "
    "autonomy mergePolicy round harness updatedAt"
).split()
STATE_KEY_RE = re.compile(r"^\s*(" + "|".join(STATE_KEYS) + r"):")

GUARD_SENTENCE = (
    "An operator or authorized human record supplies the decision; an agent must not sign or assume "
    "silence is approval."
)
READOUT_STATUSES = ("SIGNED", "PASSED", "SKIPPED-BY-OPERATOR", "NOT-PASSABLE")
GATE_KINDS = (
    "decision",
    "pre-authorization",
    "confirmation",
    "waiver",
    "correction",
    "date-correction",
)
FUTURE_OK_CLASSES = ("scheduled", "real-world", "synthetic", "illustrative")

_TIME = r"[T ]\d{2}:[0-9x]{2}(?::[0-9x]{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?"
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}(?:" + _TIME + r")?")
DATE_FULL_RE = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):([0-9x]{2})(?::([0-9x]{2})(?:\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?"
)
ISO_Z_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?Z$")
FUTURE_OK_RE = re.compile(r"future-ok:\s*([A-Za-z-]+)\s*:\s*\S")
CORRECTION_RE = re.compile(r"correct|date correction|→\s*true|recorded .* → ", re.I)
R2_MARKERS = ("≤", "<=", "retro:", "as-of")
# A correction record quoting an old wrong date is not a back-dated act (R2) when it says so plainly
# and carries another date (the true one); the looser CORRECTION_RE above is the skill's R3 test.
STRICT_CORRECTION_RE = re.compile(
    r"DATE CORRECTION|\brecorded\b.{0,80}?→\s*true|\bcorrected from\b", re.I
)
RESTORED_RE = re.compile(r"RESTORED from\s+`?([0-9a-f]{7,40})\^`?")
HEDGE_RE = re.compile(
    r"\?|\bI wonder\b|\bperhaps\b|\bmaybe\b|\bshould just\b|\bI think\b.*\bbut\b", re.I
)
DELEGATION_RES = (
    re.compile(r"\bsign\w*\b.{0,80}?\bfor me\b", re.I),
    re.compile(r"\bon my behalf\b", re.I),
    re.compile(
        r"\b(?:your|devin'?s|claude'?s|the agent'?s|agent'?s)\s+(?:own\s+)?judge?ment\b", re.I
    ),
    re.compile(r"\bdelegat\w*", re.I),
    re.compile(r"\b(?:sign|accept|attest)\w*\b[^.;]{0,60}\bor whatever\b", re.I),
)
PLAIN_ANSWER_RE = re.compile(r"^\W*(yes|no|confirm(?:ed)?|i confirm|approved?|rejected?)\b", re.I)
BLANKET_ITEMS = ("", "all", "any", "everything", "*", "—", "-")
ADR_STATUS_RE = re.compile(
    r"\b(Superseded|Qualified|Amended|Extended|Revisited)\s+by\s+(ADR-\d+)", re.I
)
ADR_STATUS_BULLET_RE = re.compile(r"^\s*-\s*\*\*Status:\*\*")
GATE_MARKER_RE = re.compile(r"\b(GATE-G\d+[a-z]?|HUMAN-H\d+[a-z]?|GATE-ACCEPT)\b")
GATE_ID_RE = re.compile(
    r"\b(GATE-[A-Z0-9]+|HUMAN-H\d+[a-z]?|HG-\d+|GL-GATE-\d+|[A-Z]{1,6}\d*\.\d+[a-z]?)\b"
)


# ── small helpers ────────────────────────────────────────────────────────────


def norm(text: str) -> str:
    """Whitespace/escaping-equivalence used for 'moved, not rewritten' (check-history `norm`)."""
    text = re.sub(r"\\(.)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def strip_markup(text: str) -> str:
    return re.sub(r"[*_`]", "", text)


def utc_iso(epoch: int) -> str:
    return dt.datetime.fromtimestamp(epoch, dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_date(epoch: int) -> str:
    return dt.datetime.fromtimestamp(epoch, dt.UTC).strftime("%Y-%m-%d")


@dataclass(frozen=True)
class Stamp:
    text: str
    epoch: int
    has_time: bool
    date: str  # the literal YYYY-MM-DD (for date-only comparisons)
    malformed: bool


def parse_stamp(text: str) -> Stamp | None:
    """Parse an ISO-8601 date or timestamp; `x` digits take their lowest reading (malformed)."""
    m = DATE_FULL_RE.fullmatch(text.strip())
    if not m:
        return None
    malformed = "x" in text
    y, mo, d = int(m[1]), int(m[2]), int(m[3])
    hh = int(m[4]) if m[4] else 0
    mi = int(m[5].replace("x", "0")) if m[5] else 0
    ss = int(m[6].replace("x", "0")) if m[6] else 0
    try:
        base = dt.datetime(y, mo, d, hh, mi, ss, tzinfo=dt.UTC)
    except ValueError:
        return None
    epoch = int(base.timestamp())
    tz = m[7]
    if tz and tz != "Z":
        sign = -1 if tz[0] == "-" else 1
        digits = tz[1:].replace(":", "")
        epoch -= sign * (int(digits[:2]) * 3600 + int(digits[2:4] or 0) * 60)
    return Stamp(text, epoch, m[4] is not None, f"{y:04d}-{mo:02d}-{d:02d}", malformed)


def parse_now(text: str | None) -> int:
    if not text:
        return int(dt.datetime.now(dt.UTC).timestamp())
    st = parse_stamp(text)
    if st is None or st.malformed:
        raise UsageError(f"--now '{text}' is not an ISO-8601 time")
    return st.epoch


def ere_to_py(ere: str) -> re.Pattern[str]:
    """POSIX ERE (as written for check-history.sh) → Python regex."""
    classes = {
        "[:space:]": r"\s",
        "[:digit:]": "0-9",
        "[:alpha:]": "A-Za-z",
        "[:alnum:]": "A-Za-z0-9",
        "[:upper:]": "A-Z",
        "[:lower:]": "a-z",
        "[:blank:]": r" \t",
    }
    for k, v in classes.items():
        ere = ere.replace(k, v)
    return re.compile(ere)


def table_cells(row: str) -> list[str]:
    """Cells of a markdown table row; an escaped `\\|` stays inside its cell."""
    u = row.strip().replace("\\|", "\x00")
    if u.startswith("|"):
        u = u[1:]
    if u.endswith("|"):
        u = u[:-1]
    return [c.replace("\x00", "\\|").strip() for c in u.split("|")]


def is_separator(row: str) -> bool:
    return bool(re.match(r"^\|[-|: ]+\|\s*$", row))


def quotes(text: str) -> list[str]:
    out = []
    for a, b in re.findall(r'"([^"]+)"|“([^”]+)”', text):
        q = (a or b).strip()
        if q:
            out.append(q)
    return out


def qnorm(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("“", '"').replace("”", '"')).strip().strip('"').strip()


class UsageError(Exception):
    pass


class UnknownError(Exception):
    pass


# ── git ──────────────────────────────────────────────────────────────────────


class Git:
    def __init__(self, root: Path) -> None:
        self.root = root

    def run(self, *args: str, ok: tuple[int, ...] = (0,), binary: bool = False) -> str | bytes:
        proc = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True)
        if proc.returncode not in ok:
            err = proc.stderr.decode("utf-8", "replace").strip()
            raise UnknownError(f"git {' '.join(args[:3])} failed: {err[:200]}")
        return proc.stdout if binary else proc.stdout.decode("utf-8", "replace")

    def text(self, *args: str) -> str:
        out = self.run(*args)
        assert isinstance(out, str)
        return out

    def resolve(self, rev: str) -> str | None:
        proc = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "--verify", "-q", f"{rev}^{{commit}}"],
            capture_output=True,
            text=True,
        )
        return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else None

    def show(self, rev: str, path: str) -> bytes | None:
        proc = subprocess.run(
            ["git", "-C", str(self.root), "show", f"{rev}:{path}"], capture_output=True
        )
        return proc.stdout if proc.returncode == 0 else None

    def is_shallow(self) -> bool:
        proc = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "--is-shallow-repository"],
            capture_output=True,
            text=True,
        )
        return proc.stdout.strip() == "true"


@dataclass(frozen=True)
class CommitInfo:
    sha: str
    ct: int  # committer time, epoch
    ci: str  # committer time, ISO with the committer's offset

    @property
    def short(self) -> str:
        return self.sha[:8] if len(self.sha) >= 8 else self.sha

    @property
    def local_date(self) -> str:
        return self.ci[:10]


# ── policy ───────────────────────────────────────────────────────────────────


@dataclass
class AllowEntry:
    glob: str
    expires: int
    expires_iso: str
    text: str


@dataclass
class Policy:
    sha256: str = ""
    append_only: list[str] = field(default_factory=list)
    dates: list[tuple[str, re.Pattern[str]]] = field(default_factory=list)
    act_when: list[tuple[str, re.Pattern[str]]] = field(default_factory=list)
    allow: list[AllowEntry] = field(default_factory=list)
    exempt: list[tuple[str, str]] = field(default_factory=list)
    archive: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @staticmethod
    def strip_comment(line: str) -> str:
        # `#` starts a comment at line start or after whitespace, unless part of a `##…` heading run.
        m = re.search(r"(?:^|\s)#(?!#)(?:\s|$)", line)
        return (line[: m.start()] if m else line).strip()

    @classmethod
    def parse(cls, raw: bytes | None) -> Policy:
        pol = cls()
        if raw is None:
            return pol
        pol.sha256 = hashlib.sha256(raw).hexdigest()
        for n, line in enumerate(raw.decode("utf-8", "replace").splitlines(), 1):
            s = cls.strip_comment(line)
            if not s:
                continue
            parts = s.split(None, 1)
            key, rest = parts[0], (parts[1] if len(parts) > 1 else "")
            try:
                if key == "append-only":
                    pol.append_only.append(rest.split()[0])
                elif key in ("date", "act-when"):
                    glob, ere = rest.split(None, 1)
                    (pol.dates if key == "date" else pol.act_when).append((glob, ere_to_py(ere)))
                elif key == "allow":
                    glob, exp, text = rest.split(None, 2)
                    st = parse_stamp(exp)
                    if st is None:
                        raise ValueError(f"bad expiry '{exp}'")
                    pol.allow.append(AllowEntry(glob, st.epoch, exp, " ".join(text.split())))
                elif key == "exempt":
                    path, heading = rest.split(None, 1)
                    pol.exempt.append((path, heading.strip()))
                elif key == "archive":
                    pol.archive.append(rest.split()[0].rstrip("/"))
                else:
                    pol.errors.append(f"line {n}: unknown directive '{key}'")
            except (ValueError, IndexError, re.error) as exc:
                pol.errors.append(f"line {n}: {exc}")
        return pol


# ── findings and report ──────────────────────────────────────────────────────

FAMILIES = {
    "all": (
        "record-dates",
        "restored-dates",
        "append-only",
        "record-shape",
        "gate-records",
        "readouts",
    ),
    "dates": ("record-dates", "restored-dates"),
    "append-only": ("append-only", "record-shape"),
    "gates": ("gate-records",),
    "readouts": ("readouts",),
    "restored": ("restored-dates",),
}


@dataclass
class Finding:
    check: str
    rule: str
    path: str
    line: int
    commit: str
    message: str
    severity: str  # error | warning

    def as_json(self) -> dict[str, object]:
        return {
            "check": self.check,
            "rule": self.rule,
            "path": self.path,
            "line": self.line,
            "commit": self.commit,
            "message": self.message,
        }


class Report:
    def __init__(self) -> None:
        self.findings: list[Finding] = []
        self.counts: dict[str, list[int]] = {}
        self.restored: list[dict[str, object]] = []

    def v(
        self, check: str, rule: str, path: str, line: int, message: str, commit: str = ""
    ) -> None:
        self.findings.append(Finding(check, rule, path, line, commit, message, "error"))

    def w(
        self, check: str, rule: str, path: str, line: int, message: str, commit: str = ""
    ) -> None:
        self.findings.append(Finding(check, rule, path, line, commit, message, "warning"))

    def count(self, check: str, candidates: int, evaluated: int) -> None:
        c = self.counts.setdefault(check, [0, 0])
        c[0] += candidates
        c[1] += evaluated


# ── the change under judgement ───────────────────────────────────────────────

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


@dataclass
class DiffRecs:
    removed: list[tuple[int, str]]  # (base line, text)
    added: list[tuple[int, int, str]]  # (head line, insert-after base line, text)


def parse_u0(diff: str) -> DiffRecs:
    removed: list[tuple[int, str]] = []
    added: list[tuple[int, int, str]] = []
    order: list[tuple[str, int]] = []
    rl = al = ins = 0
    in_hunk = False
    noeol_removed: int | None = None
    drop: set[tuple[str, int]] = set()
    for line in diff.split("\n"):
        m = HUNK_RE.match(line)
        if m:
            a = int(m[1])
            b = 1 if m[2] is None else int(m[2])
            c = int(m[3])
            ins = a if b == 0 else a + b - 1
            rl, al, in_hunk = a, c, True
            continue
        if not in_hunk or not line:
            if line.startswith("diff --git"):
                in_hunk = False
            continue
        if line.startswith("\\"):
            if order and order[-1][0] == "R":
                noeol_removed = order[-1][1]
            continue
        if line.startswith("-"):
            removed.append((rl, line[1:]))
            order.append(("R", len(removed) - 1))
            rl += 1
        elif line.startswith("+"):
            added.append((al, ins, line[1:]))
            order.append(("A", len(added) - 1))
            if noeol_removed is not None and removed[noeol_removed][1] == line[1:]:
                drop.add(("R", noeol_removed))
                drop.add(("A", len(added) - 1))
                noeol_removed = None
            al += 1
    return DiffRecs(
        [r for i, r in enumerate(removed) if ("R", i) not in drop],
        [a for i, a in enumerate(added) if ("A", i) not in drop],
    )


class Change:
    """BASE..HEAD under one of the modes; HEAD may be the index or the working tree."""

    def __init__(self, git: Git, mode: str, arg: str, now: int) -> None:
        self.git, self.mode, self.arg, self.now = git, mode, arg, now
        self.base: str | None = None  # None = the empty tree
        self.head: str = ""
        if mode in ("range", "first-parent") and git.is_shallow():
            raise UnknownError(
                "shallow clone — history mode needs the full history (set fetch-depth: 0)"
            )
        if mode == "range":
            if "..." in arg:
                a, b = arg.split("...", 1)
                ra, rb = git.resolve(a), git.resolve(b)
                if not ra or not rb:
                    raise UnknownError(f"cannot resolve the range '{arg}'")
                self.base = git.text("merge-base", ra, rb).strip()
                self.head = rb
            elif ".." in arg:
                a, b = arg.split("..", 1)
                ra, rb = git.resolve(a), git.resolve(b or "HEAD")
                if not ra or not rb:
                    raise UnknownError(f"cannot resolve the range '{arg}'")
                self.base, self.head = ra, rb
            else:
                raise UsageError("--range wants BASE..HEAD or BASE...HEAD")
        elif mode == "first-parent":
            h = git.resolve(arg)
            if not h:
                raise UnknownError(f"cannot resolve '{arg}'")
            self.head = h
            self.base = git.resolve(f"{h}^1")
        elif mode in ("staged", "worktree"):
            self.base = git.resolve("HEAD")
            self.head = ":index" if mode == "staged" else ":worktree"
        else:
            raise UsageError(f"unknown mode {mode}")
        # The landed base: a protected record is *landed* (frozen/append-only rules apply) only if it
        # exists there; one added after it is new and may be edited until merged. A range or a
        # first-parent commit judges against its own base. The index and the working tree judge against
        # HEAD, but HEAD holds the branch's own unmerged records, so their landed base is the merge-base
        # of HEAD with the LEDGER's `pinnedBaseSha` (else `buildBranchBase`), falling back to HEAD.
        self.landed_base: str | None = self.base
        self.landed_from = "base"
        if mode in ("staged", "worktree") and self.base:
            self.landed_base, self.landed_from = self._branch_base(git, self.base)
        self._landed_cache: dict[str, bool] = {}
        self._head_cache: dict[str, str | None] = {}
        self._base_cache: dict[str, str | None] = {}
        self.added_by: dict[tuple[str, str], CommitInfo] = {}
        self.removed_by: dict[tuple[str, str], CommitInfo] = {}
        if self.committed:
            hc = git.text("log", "-1", "--format=%H %ct %cI", self.head).split()
            self.head_commit = CommitInfo(hc[0], int(hc[1]), hc[2])
        else:
            self.head_commit = CommitInfo(
                "staged" if mode == "staged" else "worktree", now, utc_iso(now)
            )

    @property
    def committed(self) -> bool:
        return self.mode in ("range", "first-parent")

    @staticmethod
    def _branch_base(git: Git, head: str) -> tuple[str, str]:
        raw = git.show(head, LEDGER_REL)
        text = raw.decode("utf-8", "replace") if raw is not None else ""
        for key in ("pinnedBaseSha", "buildBranchBase"):
            m = re.search(rf"(?m)^\s*{key}:[ \t]*(\S+)", text)
            if not m or m.group(1).startswith(("(", "#")):
                continue
            for cand in (m.group(1), f"origin/{m.group(1)}"):
                rev = git.resolve(cand)
                if not rev:
                    continue
                mb = subprocess.run(
                    ["git", "-C", str(git.root), "merge-base", head, rev],
                    capture_output=True,
                    text=True,
                )
                if mb.returncode == 0 and mb.stdout.strip():
                    return mb.stdout.strip(), f"merge-base of HEAD and {key} {m.group(1)}"
        return head, "HEAD (no resolvable pinnedBaseSha/buildBranchBase)"

    def landed(self, path: str) -> bool:
        """The record exists at the landed base (it is merged history, not this branch's own work)."""
        if path not in self._landed_cache:
            if self.landed_base == self.base:
                self._landed_cache[path] = self.base_bytes(path) is not None
            else:
                self._landed_cache[path] = (
                    self.landed_base is not None
                    and self.git.show(self.landed_base, path) is not None
                )
        return self._landed_cache[path]

    # content
    def at_base(self, path: str) -> str | None:
        if path not in self._base_cache:
            raw = self.git.show(self.base, path) if self.base else None
            self._base_cache[path] = raw.decode("utf-8", "replace") if raw is not None else None
        return self._base_cache[path]

    def at_head(self, path: str) -> str | None:
        if path not in self._head_cache:
            raw = self.head_bytes(path)
            self._head_cache[path] = raw.decode("utf-8", "replace") if raw is not None else None
        return self._head_cache[path]

    def base_bytes(self, path: str) -> bytes | None:
        return self.git.show(self.base, path) if self.base else None

    def head_bytes(self, path: str) -> bytes | None:
        if self.mode == "staged":
            return self.git.show("", path)
        if self.mode == "worktree":
            p = self.git.root / path
            return p.read_bytes() if p.is_file() else None
        return self.git.show(self.head, path)

    def head_has(self, path_prefix: str, pattern: str) -> bool:
        return any(fnmatch.fnmatchcase(p, pattern) for p in self.head_files(path_prefix))

    def head_files(self, prefix: str) -> list[str]:
        if self.mode == "worktree":
            base = self.git.root / prefix
            return sorted(str(p.relative_to(self.git.root)) for p in base.rglob("*") if p.is_file())
        if self.mode == "staged":
            return self.git.text("ls-files", "--", prefix).splitlines()
        return self.git.text("ls-tree", "-r", "--name-only", self.head, "--", prefix).splitlines()

    def _diff_args(self) -> list[str]:
        if self.mode == "staged":
            return ["diff", "--cached", "--no-renames", "--no-color"] + (
                [self.base] if self.base else []
            )
        if self.mode == "worktree":
            return ["diff", "--no-renames", "--no-color"] + ([self.base] if self.base else [])
        empty = self.git.text("hash-object", "-t", "tree", "/dev/null").strip()
        return ["diff", "--no-renames", "--no-color", self.base or empty, self.head]

    def pathspecs(self, policy: Policy) -> list[str]:
        specs = list(SCOPE)
        for g in policy.append_only + [g for g, _ in policy.dates]:
            specs.append(f":(glob){g}" if any(ch in g for ch in "*?[") else g)
        specs += [f":(exclude){e.rstrip('/')}" for e in EXCLUDED]
        return specs

    def changed(self, policy: Policy) -> list[tuple[str, str]]:
        out = self.git.text(*self._diff_args(), "--name-status", "--", *self.pathspecs(policy))
        rows: dict[str, str] = {}
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                rows[parts[-1]] = parts[0][0]
        if self.mode == "worktree":
            extra = self.git.text(
                "ls-files", "--others", "--exclude-standard", "--", *self.pathspecs(policy)
            )
            for p in extra.splitlines():
                rows.setdefault(p, "A")
        return sorted(
            ((st, p) for p, st in rows.items() if not p.startswith(EXCLUDED)), key=lambda x: x[1]
        )

    def diff(self, path: str, status: str) -> DiffRecs:
        if self.mode == "worktree" and status == "A" and self.at_base(path) is None:
            text = self.at_head(path) or ""
            lines = text.split("\n")
            if lines and lines[-1] == "":
                lines.pop()
            return DiffRecs([], [(i, 0, t) for i, t in enumerate(lines, 1)])
        return parse_u0(self.git.text(*self._diff_args(), "-U0", "--", path))

    # attribution
    def attribute(self, policy: Policy) -> None:
        if not self.committed:
            return
        rng = f"{self.base}..{self.head}" if self.base else self.head
        out = self.git.text(
            "log",
            "--reverse",
            "-p",
            "--no-renames",
            "--no-color",
            "-U0",
            "--format=@@C %H %ct %cI",
            rng,
            "--",
            *self.pathspecs(policy),
        )
        cur: CommitInfo | None = None
        new_f = old_f = None
        in_header = False
        for line in out.split("\n"):
            if line.startswith("@@C "):
                _, sha, ct, ci = line.split(" ", 3)
                cur = CommitInfo(sha, int(ct), ci.strip())
                continue
            if line.startswith("diff --git "):
                in_header, new_f, old_f = True, None, None
                continue
            if in_header:
                if line.startswith("--- "):
                    old_f = line[6:] if line.startswith("--- a/") else None
                elif line.startswith("+++ "):
                    new_f = line[6:] if line.startswith("+++ b/") else None
                elif line.startswith("@@"):
                    in_header = False
                continue
            if cur is None or line.startswith("@@"):
                continue
            if line.startswith("+") and new_f:
                self.added_by[(new_f, line[1:])] = cur
            elif line.startswith("-") and old_f:
                self.removed_by[(old_f, line[1:])] = cur

    def commit_of_added(self, path: str, text: str) -> CommitInfo:
        return self.added_by.get((path, text), self.head_commit)

    def commit_of_removed(self, path: str, text: str) -> str:
        c = self.removed_by.get((path, text))
        return c.short if c else (self.head_commit.short if self.mode == "first-parent" else "")

    def commits(self) -> list[CommitInfo]:
        if not self.committed:
            return []
        rng = f"{self.base}..{self.head}" if self.base else self.head
        out = self.git.text("log", "--format=%H %ct %cI", rng)
        return [
            CommitInfo(s, int(t), c)
            for s, t, c in (ln.split() for ln in out.splitlines() if ln.strip())
        ]


# ── markdown structure ───────────────────────────────────────────────────────


@dataclass
class Region:
    start: int
    end: int
    lnb: int  # last non-blank line
    heading: str


def regions(lines: list[str], level: int = 2) -> list[Region]:
    """`##` regions (level 2), or every `##`/`###` heading as a boundary (level 3)."""
    regs: list[Region] = []
    pat = re.compile(r"^##\s") if level == 2 else re.compile(r"^#{2,3}\s")
    for i, line in enumerate(lines, 1):
        if pat.match(line):
            if regs:
                regs[-1].end = i - 1
            regs.append(Region(i, len(lines), i, line))
        elif regs and line.strip():
            regs[-1].lnb = i
    return regs


def region_at(regs: list[Region], line: int) -> Region | None:
    for r in reversed(regs):
        if r.start <= line:
            return r
    return None


POSITIONAL = re.compile(r"^##\s+(GATE DECISIONS|PHASE LOG|OPEN FINDINGS|RETURN PASS)")
PHASE_LOG_RE = re.compile(r"^##\s+PHASE LOG(?!\s+INDEX)")
GATE_DECISIONS_RE = re.compile(r"^##\s+GATE DECISIONS")
ROUND_RE = re.compile(r"\bRound\s+(\d+)\b")


@dataclass
class Table:
    header_line: int
    header: list[str]
    rows: list[tuple[int, str]]
    caption: str
    round: str | None
    region: Region

    @property
    def restored_from(self) -> str | None:
        """The `<sha>` of a `RESTORED from `<sha>^`` caption: the last bullet (with its continuation
        lines) before the table must carry it."""
        lines = self.caption.split("\n")
        start = max((i for i, ln in enumerate(lines) if ln.startswith("- ")), default=-1)
        if start < 0:
            return None
        m = RESTORED_RE.search(" ".join(lines[start:]))
        return m[1] if m else None


def gd_tables(lines: list[str]) -> list[Table]:
    """Tables inside `## GATE DECISIONS` regions, with their caption text and round context."""
    out: list[Table] = []
    for reg in regions(lines):
        if not GATE_DECISIONS_RE.match(reg.heading):
            continue
        caption: list[str] = []
        rnd: str | None = None
        i = reg.start + 1
        while i <= reg.end:
            line = lines[i - 1]
            if line.startswith("###"):
                m = ROUND_RE.search(line)
                rnd = m[1] if m else rnd
                caption = [line]
                i += 1
                continue
            if line.startswith("|") and i + 1 <= reg.end and is_separator(lines[i]):
                hdr = table_cells(line)
                rows: list[tuple[int, str]] = []
                j = i + 2
                while j <= reg.end and lines[j - 1].startswith("|"):
                    rows.append((j, lines[j - 1]))
                    j += 1
                out.append(Table(i, hdr, rows, "\n".join(caption), rnd, reg))
                caption = []
                i = j
                continue
            if line.strip():
                caption.append(line)
            i += 1
    return out


@dataclass
class PhaseEntry:
    line: int
    stamp: Stamp
    text: str
    round: str | None


def phase_entries(lines: list[str]) -> list[PhaseEntry]:
    out: list[PhaseEntry] = []
    for reg in regions(lines):
        if not PHASE_LOG_RE.match(reg.heading):
            continue
        m = ROUND_RE.search(reg.heading)
        rnd = m[1] if m else None
        for i in range(reg.start + 1, reg.end + 1):
            s = strip_markup(lines[i - 1])
            mm = re.match(r"^-\s*(" + DATE_RE.pattern + ")", s)
            if mm:
                st = parse_stamp(mm[1])
                if st:
                    out.append(PhaseEntry(i, st, s, rnd))
    return out


# ── the judge ────────────────────────────────────────────────────────────────


@dataclass
class DateRec:
    path: str
    line: int
    cls: str  # act | event
    stamp_text: str
    text: str
    check: str = "record-dates"


class Judge:
    def __init__(self, change: Change, policy: Policy, report: Report, guards: bool) -> None:
        self.c, self.pol, self.r, self.guards = change, policy, report, guards
        self.dates: list[DateRec] = []
        self.date_candidates = 0
        self.date_unparsed = 0
        self.changed: list[tuple[str, str]] = []
        self._executed: set[str] | None = None

    # -- entry point
    def run(self) -> None:
        self.changed = self.c.changed(self.pol)
        self.c.attribute(self.pol)
        changed_paths = {p for _, p in self.changed}
        cand = 0
        for status, path in self.changed:
            recs = self.c.diff(path, status)
            cand += len(recs.removed) + len(recs.added)
            self.judge_file(status, path, recs, changed_paths)
        self.r.count("append-only", cand, cand)
        self.judge_dates()
        self.judge_commit_clock()

    def add_date(self, path: str, line: int, cls: str, stamp_text: str, text: str) -> None:
        self.date_candidates += 1
        self.dates.append(DateRec(path, line, cls, stamp_text, text))

    def undated(self, path: str, line: int, what: str) -> None:
        self.date_candidates += 1
        self.date_unparsed += 1
        self.r.w("record-dates", "undated", path, line, f"{what} carries no parseable record date")

    def classify(self, path: str) -> str:
        if path == LEDGER_REL:
            return "ledger"
        if path == DEFERRALS_REL:
            return "deferrals"
        if path.startswith("docs/build/readouts/"):
            return (
                ""
                if path.endswith("/_TEMPLATE.md")
                else ("readout" if path.endswith(".md") else "")
            )
        if path == INDEX_REL:
            return "index"
        if path == MANIFEST_REL:
            return "manifest"
        if path.startswith("docs/build/reports/digests/") and path.endswith(".md"):
            return "digest"
        if path.startswith("docs/build/") and path.endswith(".jsonl"):
            return "jsonl"
        if re.match(r"^docs/build/(runs|pr)/[^/]+\.md$", path):
            return "runpr"
        if re.match(r"^docs/adr/ADR-[^/]+\.md$", path):
            return "adr"
        if re.match(r"^docs/tickets/[^/]+\.md$", path):
            return "contract"
        return ""

    def judge_file(self, status: str, path: str, recs: DiffRecs, changed_paths: set[str]) -> None:
        cls = self.classify(path)
        if any(fnmatch.fnmatchcase(path, g) for g in self.pol.append_only):
            cls = "policy-ao"
        if cls == "contract" and not self.executed(path):
            cls = ""
        # A record added after the landed base (e.g. a seed ADR in the index/worktree modes) is not
        # landed: it may be edited or removed until merged. Its edits are judged as a new file's ("N");
        # the control files (LEDGER, DEFERRALS, BUILD_INDEX, manifest) keep their region rules.
        fresh = status != "A" and bool(cls) and not self.c.landed(path)
        if fresh and status == "D":
            return
        if fresh and cls not in ("ledger", "deferrals", "index", "manifest"):
            status = "N"
        if status == "D":
            base = self.c.at_base(path) or ""
            closed_run = cls == "runpr" and "/runs/" in path and run_ledger_closed(base)
            if (
                cls
                in (
                    "ledger",
                    "deferrals",
                    "readout",
                    "index",
                    "manifest",
                    "digest",
                    "jsonl",
                    "adr",
                    "contract",
                    "policy-ao",
                )
                or closed_run
            ):
                self.r.v(
                    "append-only",
                    "deleted",
                    path,
                    0,
                    "a protected build record was deleted — records are corrected by appending, never "
                    "removed (BM-HIST-01)",
                    self.c.commit_of_removed(path, ""),
                )
            return
        handler = {
            "ledger": self.judge_ledger,
            "deferrals": self.judge_deferrals,
            "readout": self.judge_readout,
            "index": self.judge_index,
            "manifest": self.judge_manifest,
            "contract": self.judge_contract,
            "adr": self.judge_adr,
            "policy-ao": self.judge_policy_ao,
            "jsonl": self.judge_jsonl,
            "digest": self.judge_digest,
            "runpr": self.judge_runpr,
        }.get(cls)
        if handler:
            handler(status, path, recs)
        self.judge_policy_dates(path, recs)

    def executed(self, path: str) -> bool:
        tid = re.sub(r"^[0-9]{2,3}[a-z]?_", "", Path(path).name)
        tid = re.sub(r"__.*$", "", tid)
        tid = re.sub(r"\.md$", "", tid)
        if self._executed is None:
            ids: set[str] = set()
            for line in (self.c.at_base(INDEX_REL) or "").splitlines():
                if line.startswith("|"):
                    for cell in table_cells(line):
                        c = re.sub(r"[*`]", "", cell).strip().split(" ")[0] if cell.strip() else ""
                        if re.match(r"^[A-Z][A-Z0-9.a-z-]*$", c):
                            ids.add(c)
            self._executed = ids
        return tid in self._executed

    # -- generic append-only
    def no_removals(self, path: str, recs: DiffRecs, check: str, rule: str, what: str) -> None:
        added = {norm(t) for _, _, t in recs.added}
        for ln, text in recs.removed:
            t = norm(text)
            if not t or t in added:
                continue
            self.r.v(
                check,
                rule,
                path,
                ln,
                f"line {ln} removed or rewritten: '{text[:80]}' — {what}",
                self.c.commit_of_removed(path, text),
            )

    # -- LEDGER
    def judge_ledger(self, status: str, path: str, recs: DiffRecs) -> None:
        base_text = self.c.at_base(path)
        head_text = self.c.at_head(path) or ""
        head = head_text.split("\n")
        base = base_text.split("\n") if base_text is not None else []
        regs = regions(base)
        head_end = 0
        for r in regs:
            if re.match(r"^##\s+OPEN FINDINGS", r.heading):
                head_end = r.start - 1
                break
        else:
            for r in regs:
                if not re.match(r"^##\s+CURRENT STATE", r.heading):
                    head_end = r.start - 1
                    break
        exempt_spans = self.exempt_spans(path, base)
        added_norm = {norm(t) for _, _, t in recs.added}
        removed_norm = {norm(t) for _, t in recs.removed}
        head_removed: list[tuple[int, str]] = []
        for ln, text in recs.removed:
            if any(a <= ln <= b for a, b in exempt_spans):
                continue
            if ln <= head_end:
                head_removed.append((ln, text))
                continue
            t = norm(text)
            if not t or t in added_norm:
                continue
            reg = region_at(regs, ln)
            hd = reg.heading[:40] if reg else "?"
            self.r.v(
                "append-only",
                "append-only",
                path,
                ln,
                f"line {ln} in '{hd}' removed or rewritten: '{text[:80]}' — this region only appends; a "
                "correction is a new dated entry (BM-HIST-01)",
                self.c.commit_of_removed(path, text),
            )
        for hl, ins, text in recs.added:
            if any(a <= ins <= b for a, b in exempt_spans) or ins <= head_end:
                continue
            reg = region_at(regs, ins)
            if (
                reg
                and POSITIONAL.match(reg.heading)
                and ins < reg.lnb
                and norm(text) not in removed_norm
            ):
                self.r.v(
                    "append-only",
                    "append-position",
                    path,
                    hl,
                    f"line {hl} was inserted inside '{reg.heading[:40]}' (before its last entry at base line "
                    f"{reg.lnb}) — new entries go only after the region's last line (BM-LEDGER-06, BM-HIST-01)",
                    self.c.commit_of_added(path, text).short,
                )
        self.living_archived(path, head_removed, head_text)
        added_lines = {hl for hl, _, _ in recs.added}
        self.ledger_dates(path, head, added_lines)
        self.judge_gate_records(path, head, added_lines)
        self.judge_restored(path, head, added_lines)

    def exempt_spans(self, path: str, lines: list[str]) -> list[tuple[int, int]]:
        spans = []
        subs = regions(lines, level=3)
        for p, heading in self.pol.exempt:
            if p != path:
                continue
            for r in subs:
                if heading in r.heading:
                    spans.append((r.start, r.end))
        return spans

    def living_archived(
        self, path: str, head_removed: list[tuple[int, str]], head_text: str
    ) -> None:
        if not head_removed:
            return
        dirs = [ARCHIVE_DEFAULT] + self.pol.archive
        archive_files = [
            p for st, p in self.changed if st != "D" and any(p.startswith(d + "/") for d in dirs)
        ]
        archived: set[str] = set()
        for af in archive_files:
            archived.update((self.c.at_head(af) or "").split("\n"))
        missing = [
            (ln, t)
            for ln, t in head_removed
            if t.strip() and not STATE_KEY_RE.match(t) and t not in archived
        ]
        narch = sum(
            1 for _, t in head_removed if t.strip() and not STATE_KEY_RE.match(t) and t in archived
        )
        if missing:
            self.r.v(
                "append-only",
                "living-archived",
                path,
                missing[0][0],
                f"{len(missing)} removed LEDGER head line(s) (first: base line {missing[0][0]}) are not archived "
                f"byte-for-byte under {' or '.join(dirs)}/ in this change — archive the replaced text with a "
                "sha256 pointer comment (BM-LEDGER-08)",
            )
        elif narch and not any(Path(af).name in head_text for af in archive_files):
            self.r.v(
                "append-only",
                "pointer",
                path,
                1,
                "the LEDGER head was archived but no pointer comment names the archive file (BM-LEDGER-08)",
            )

    def ledger_dates(self, path: str, head: list[str], added: set[int]) -> None:
        restored_rows = {ln for t in gd_tables(head) if t.restored_from for ln, _ in t.rows}
        tables = {row_ln: t for t in gd_tables(head) for row_ln, _ in t.rows}
        cur = ""
        for i, line in enumerate(head, 1):
            if re.match(r"^##\s", line):
                cur = line
                continue
            if i not in added:
                continue
            m_upd = re.match(r"^\s*updatedAt:\s*(" + DATE_RE.pattern + ")", line)
            if m_upd:
                self.add_date(path, i, "act", m_upd[1], line)
                continue
            if re.match(r"^\s*updatedAt:", line):
                self.undated(path, i, "`updatedAt:`")
                continue
            if PHASE_LOG_RE.match(cur) and line.startswith("- "):
                m = re.match(r"^-\s*(" + DATE_RE.pattern + ")", strip_markup(line))
                if m:
                    self.add_date(path, i, "act", m[1], line)
                else:
                    self.undated(path, i, "PHASE LOG entry")
            elif GATE_DECISIONS_RE.match(cur):
                if line.startswith("- "):
                    m = re.match(r"^-\s*(" + DATE_RE.pattern + ")", strip_markup(line))
                    if m:
                        self.add_date(path, i, "act", m[1], line)
                elif line.startswith("|") and i in tables and i not in restored_rows:
                    t = tables[i]
                    if not t.header or not re.match(
                        r"^date\b", strip_markup(t.header[0]).strip().lower()
                    ):
                        continue
                    cells = table_cells(line)
                    m = DATE_RE.search(cells[0]) if cells else None
                    if m:
                        self.add_date(path, i, "act", m[0], line)
                    else:
                        self.undated(path, i, "GATE DECISIONS row")

    # -- G1 blame mode: restored GATE DECISIONS rows
    def judge_restored(self, path: str, head: list[str], added: set[int] | None) -> None:
        judge_restored_blocks(
            self.c.git, path, head, added, self.c.at_head(DATE_CORRECTIONS_REL), self.c.now, self.r
        )

    # -- G4a
    def judge_gate_records(self, path: str, head: list[str], added: set[int]) -> None:
        tables = gd_tables(head)
        pauses = [e for e in phase_entries(head) if re.search(r"\bpause[ds]?\b", e.text, re.I)]
        cand = ev = 0
        for t in tables:
            low = [strip_markup(h).strip().lower() for h in t.header]
            if (
                "kind" not in low or t.restored_from
            ):  # restored rows are history, judged by blame mode
                continue
            kc = low.index("kind")
            ac = next((i for i, h in enumerate(low) if h.startswith("answer")), 4)
            gc = next((i for i, h in enumerate(low) if h.startswith("gate")), 2)
            ic = next((i for i, h in enumerate(low) if h.startswith("item")), 3)
            tc = next((i for i, h in enumerate(low) if h.startswith("ticket")), 1)
            parsed = [(ln, row, table_cells(row)) for ln, row in t.rows]
            for idx, (ln, row, cells) in enumerate(parsed):
                if ln not in added:
                    continue
                cand += 1
                if len(cells) != len(t.header):
                    self.r.v(
                        "gate-records",
                        "G4a-columns",
                        path,
                        ln,
                        f"GATE DECISIONS row has {len(cells)} cells, the header has {len(t.header)} — escape a | "
                        "inside a cell as \\| (BM-LEDGER-04)",
                        self.c.commit_of_added(path, row).short,
                    )
                    continue
                ev += 1
                commit = self.c.commit_of_added(path, row).short
                date_cell = strip_markup(cells[0]).strip()
                if not ISO_Z_RE.match(date_cell):
                    self.r.v(
                        "gate-records",
                        "G4a-date",
                        path,
                        ln,
                        f"date '{date_cell[:40]}' is not an ISO-8601 Z time from `date -u` (BM-GATE-05)",
                        commit,
                    )
                kind = strip_markup(cells[kc]).strip().lower()
                if kind not in GATE_KINDS:
                    self.r.v(
                        "gate-records",
                        "G4a-kind",
                        path,
                        ln,
                        f"kind '{kind or '<empty>'}' is not one of {' | '.join(GATE_KINDS)} (BM-GATE-05)",
                        commit,
                    )
                answer = cells[ac]
                qs = quotes(answer)
                if not qs and not re.search(r"\bprovided:\s*(yes|no)\b", answer, re.I):
                    self.r.v(
                        "gate-records",
                        "G4a-verbatim",
                        path,
                        ln,
                        "the answer holds no quoted operator words and no `provided: yes/no` (BM-GATE-05)",
                        commit,
                    )
                words = " ".join(qs)
                if kind == "pre-authorization":
                    item = strip_markup(cells[ic]).strip().lower()
                    if "expires:" not in row or "voided-by:" not in row or item in BLANKET_ITEMS:
                        self.r.v(
                            "gate-records",
                            "G4a-preauth",
                            path,
                            ln,
                            "a pre-authorization names exact item ids, `expires:` and `voided-by:` "
                            "(BM-GATE-09, OM-10)",
                            commit,
                        )
                for rx in DELEGATION_RES:
                    if words and rx.search(words):
                        self.r.v(
                            "gate-records",
                            "G4a-delegation",
                            path,
                            ln,
                            f"the answer delegates a decision or signature ('{rx.search(words)[0]}') — an "
                            "agent never signs or decides for the operator (BM-GATE-07, OM-08)",
                            commit,
                        )
                        break
                if words and HEDGE_RE.search(words):
                    gate = norm(strip_markup(cells[gc])).lower()
                    later = [
                        c
                        for _, _, c in parsed[idx + 1 :]
                        if len(c) == len(t.header)
                        and strip_markup(c[kc]).strip().lower() == "confirmation"
                        and norm(strip_markup(c[gc])).lower() == gate
                        and any(
                            PLAIN_ANSWER_RE.match(q) and not HEDGE_RE.search(q)
                            for q in quotes(c[ac])
                        )
                    ]
                    if kind == "confirmation" or not later:
                        self.r.v(
                            "gate-records",
                            "G4a-hedge",
                            path,
                            ln,
                            "the answer is interrogative, conditional or hedged — it is not a decision until a "
                            "later `confirmation` row records a plain yes/no (BM-GATE-06, OM-09)",
                            commit,
                        )
                if kind == "decision":
                    self.answer_after_pause(
                        path, ln, commit, cells[0], cells[gc] + " " + cells[tc], t.round, pauses
                    )
        # Legacy bullet entries: a quoted delegation is reported (a warning — a bullet may quote it as a fact).
        for reg in regions(head):
            if not GATE_DECISIONS_RE.match(reg.heading):
                continue
            for i in range(reg.start + 1, reg.end + 1):
                line = head[i - 1]
                if i not in added or not line.startswith("- "):
                    continue
                words = " ".join(quotes(line))
                hit = next(
                    (rx.search(words) for rx in DELEGATION_RES if words and rx.search(words)), None
                )
                if hit:
                    self.r.w(
                        "gate-records",
                        "G4a-delegation",
                        path,
                        i,
                        f"a GATE DECISIONS entry quotes a delegated signature or decision ('{hit[0]}') — an agent "
                        "never signs or decides for the operator (BM-GATE-07, OM-08)",
                        self.c.commit_of_added(path, line).short,
                    )
        self.r.count("gate-records", cand, ev)

    def answer_after_pause(
        self,
        path: str,
        ln: int,
        commit: str,
        date_cell: str,
        ids_text: str,
        rnd: str | None,
        pauses: list[PhaseEntry],
    ) -> None:
        st = parse_stamp(strip_markup(date_cell).strip())
        ids = set(GATE_ID_RE.findall(strip_markup(ids_text)))
        if st is None or not ids:
            return
        same = [
            p
            for p in pauses
            if (rnd is None or p.round == rnd)
            and any(re.search(r"(?<![\w.-])" + re.escape(i) + r"(?![\w-])", p.text) for i in ids)
        ]
        marker = bool(GATE_MARKER_RE.search(ids_text))
        if same:
            ok = any(
                (st.epoch >= p.stamp.epoch) if p.stamp.has_time else (st.date >= p.stamp.date)
                for p in same
            )
            if not ok:
                self.r.v(
                    "gate-records",
                    "G4a-pause",
                    path,
                    ln,
                    f"decision dated {st.text} precedes every recorded PHASE LOG pause for {', '.join(sorted(ids))} "
                    "— an earlier answer is a `pre-authorization` with items, expires: and voided-by: "
                    "(BM-GATE-05, OM-10)",
                    commit,
                )
        elif marker:
            self.r.v(
                "gate-records",
                "G4a-pause",
                path,
                ln,
                f"decision for gate marker {GATE_MARKER_RE.search(ids_text)[0]} has no PHASE LOG pause entry "
                f"{'in Round ' + rnd + ' ' if rnd else ''}— record the pause, or type the row "
                "`pre-authorization` (BM-GATE-05, OM-10)",
                commit,
            )
        else:
            self.r.w(
                "gate-records",
                "G4a-pause",
                path,
                ln,
                f"no PHASE LOG pause entry found for {', '.join(sorted(ids))}; a decision answered before its "
                "pause is a pre-authorization (BM-GATE-05)",
                commit,
            )

    # -- DEFERRALS (row-annotate)
    def judge_deferrals(self, status: str, path: str, recs: DiffRecs) -> None:
        head_text = self.c.at_head(path) or ""
        head = head_text.split("\n")
        added_rows = [(hl, t) for hl, _, t in recs.added]

        def row_id(text: str) -> str:
            return table_cells(text)[0] if text.startswith("|") else ""

        added_by_id = {}
        for hl, t in added_rows:
            if re.match(r"^\|\s*D-", t):
                added_by_id.setdefault(row_id(t), (hl, t))
        added_norm = {norm(t) for _, t in added_rows}
        changed_ids: set[str] = set()
        for ln, old in recs.removed:
            if re.match(r"^\|\s*D-", old):
                rid = row_id(old)
                if rid not in added_by_id:
                    self.r.v(
                        "append-only",
                        "row-annotate",
                        path,
                        ln,
                        f"DEFERRALS row {rid} was removed — never delete a row (BM-DEFER-01)",
                        self.c.commit_of_removed(path, old),
                    )
                    continue
                hl, new = added_by_id[rid]
                verdict = deferral_verdict(old, new)
                commit = self.c.commit_of_added(path, new).short
                if verdict == "rewritten":
                    self.r.v(
                        "append-only",
                        "row-annotate",
                        path,
                        ln,
                        f"DEFERRALS row {rid} was rewritten, not grown — keep every cell's text and add the note "
                        "(BM-DEFER-01, BM-HIST-01)",
                        commit,
                    )
                    continue
                if verdict == "flip-undated":
                    self.r.v(
                        "append-only",
                        "status-date",
                        path,
                        ln,
                        f"DEFERRALS row {rid} changed status without a dated note (`date -u +%F` + evidence) "
                        "(BM-DEFER-01)",
                        commit,
                    )
                for d in status_dates(new):
                    if d not in old:
                        self.add_date(path, hl, "act", d, new)
                changed_ids.add(rid)
            else:
                t = norm(old)
                if t and t not in added_norm:
                    self.r.v(
                        "append-only",
                        "append-only",
                        path,
                        ln,
                        f"DEFERRALS line {ln} removed or rewritten — the header and rules only gain lines "
                        "(BM-DEFER-01)",
                        self.c.commit_of_removed(path, old),
                    )
        # rows added under new ids: status dates; rule 5 (owed kind-P rows are scheduled)
        added_lines = {hl for hl, _ in added_rows}
        kc = uc = 0
        for i, line in enumerate(head, 1):
            if re.match(r"^\|\s*id\s*\|", line):
                hdr = [c.lower() for c in table_cells(line)]
                kc = hdr.index("kind") + 1 if "kind" in hdr else 0
                uc = hdr.index("unblocked by") + 1 if "unblocked by" in hdr else 0
                continue
            if i not in added_lines or not re.match(r"^\|\s*D-", line):
                continue
            cells = table_cells(line)
            if cells[0] in changed_ids:
                continue
            for d in status_dates(line):
                self.add_date(path, i, "act", d, line)
            if kc:
                self.r.count("record-shape", 1, 1)
            if kc and len(cells) >= kc and re.sub(r"[\s*`_]", "", cells[kc - 1]) == "P":
                last = next((c for c in reversed(cells) if c.strip()), "")
                if re.search(r"OPEN|PARTIAL", last.upper()):
                    cell = cells[uc - 1] if uc and len(cells) >= uc else line
                    if "owner:" not in cell or "trigger:" not in cell:
                        msg = (
                            f"DEFERRALS row {cells[0]} (kind P, owed) was added without owner:/trigger: in "
                            "'unblocked by' — human work is scheduled (rule 5)"
                        )
                        (self.r.v if self.guards else self.r.w)(
                            "record-shape", "rule-5", path, i, msg
                        )

    # -- readouts (G2 + G4b)
    def judge_readout(self, status: str, path: str, recs: DiffRecs) -> None:
        head_text = self.c.at_head(path) or ""
        head = head_text.split("\n")
        base_text = self.c.at_base(path) or ""
        self.r.count("readouts", 1, 1)
        has_guard_head = guard_sentence_in(head_text)
        commit = self.c.commit_of_added(path, recs.added[0][2]).short if recs.added else ""
        if status in ("A", "N") or not base_text:
            if not has_guard_head:
                self.r.v(
                    "readouts",
                    "G4b-guard",
                    path,
                    1,
                    f'a new readout lacks the guard sentence ("{GUARD_SENTENCE}") (BM-INDEX-03, DRAFT-MEM-5)',
                    commit,
                )
            st = readout_status(head)
            if st and not st.upper().startswith("PENDING"):
                self.r.w(
                    "readouts",
                    "G4b-status",
                    path,
                    1,
                    f"a new readout was created with Status '{st[:40]}' — signing is a later, separate diff "
                    "(BM-INDEX-03)",
                    commit,
                )
        else:
            rm_status = [(ln, t) for ln, t in recs.removed if re.match(r"^\s*Status:", t)]
            add_status = [(hl, t) for hl, _, t in recs.added if re.match(r"^\s*Status:", t)]
            for ln, t in recs.removed:
                if re.match(r"^\s*Status:", t) or not norm(t):
                    continue
                self.r.v(
                    "readouts",
                    "readout",
                    path,
                    ln,
                    f"readout line {ln} removed or rewritten ('{t[:60]}') — a readout is append-only except its "
                    "single Status: line; signing appends a Signature block (BM-INDEX-03, BM-GATE-08)",
                    self.c.commit_of_removed(path, t),
                )
            if len(rm_status) > 1 or len(add_status) > 1:
                self.r.v(
                    "readouts",
                    "readout",
                    path,
                    0,
                    "readout changed more than one Status: line (BM-INDEX-03)",
                )
            new_status = ""
            if add_status:
                new_status = strip_markup(
                    re.sub(r"<!--.*?-->", "", add_status[0][1].split(":", 1)[1])
                ).strip()
                tok = new_status.split()[0].upper().rstrip(".,;") if new_status.split() else ""
                old = strip_markup(rm_status[0][1].split(":", 1)[1]).strip() if rm_status else ""
                if not tok.startswith("PENDING") and tok not in READOUT_STATUSES:
                    self.r.v(
                        "readouts",
                        "G4b-status",
                        path,
                        add_status[0][0],
                        f"Status '{new_status[:40]}' is not PENDING or one of {' | '.join(READOUT_STATUSES)} "
                        "(BM-INDEX-03)",
                        commit,
                    )
                if old and not old.upper().startswith("PENDING") and tok != old.split()[0].upper():
                    self.r.v(
                        "readouts",
                        "G4b-status",
                        path,
                        add_status[0][0],
                        f"Status moved from '{old[:30]}' — only a PENDING readout changes its Status (BM-INDEX-03)",
                        commit,
                    )
            if guard_sentence_in(base_text) and not has_guard_head:
                self.r.v(
                    "readouts",
                    "G4b-guard",
                    path,
                    0,
                    "the guard sentence was removed (BM-INDEX-03, BM-GATE-08)",
                    commit,
                )
            elif not has_guard_head:
                self.r.w(
                    "readouts",
                    "G4b-guard",
                    path,
                    0,
                    "a grandfathered readout lacks the guard sentence; it is added with its restored history "
                    "(M4) (BM-INDEX-03)",
                )
            signing = (
                new_status.split()[0].upper().rstrip(".,;") in READOUT_STATUSES
                if new_status.split()
                else False
            ) or any(re.match(r"^\s*Operator decision \(verbatim", t) for _, _, t in recs.added)
            if signing:
                self.signing_diff(path, head, recs, commit)
        self.agent_drafted(path, head, {hl for hl, _, _ in recs.added}, commit)
        # readout record dates
        added = {hl for hl, _, _ in recs.added}
        for i, line in enumerate(head, 1):
            if i in added and re.search(
                r"(^|[^A-Za-z])(Date|[Rr]eceived|[Ss]igned|[Cc]onfirm[a-z]*|GATE DECISIONS row)",
                line,
            ):
                for m in DATE_RE.finditer(line):
                    self.add_date(path, i, "act", m[0], line)

    def signing_diff(self, path: str, head: list[str], recs: DiffRecs, commit: str) -> None:
        added = {hl for hl, _, _ in recs.added}
        in_block = drafted_lines(head)
        decision_quotes: list[str] = []
        allowed = re.compile(
            r"^\s*(#{2,}\s*Signature\b|Operator decision \(verbatim|GATE DECISIONS row:|Operator confirmation\b|"
            r"Signed by:|Recorded by\b|Status:|<!--.*-->\s*$|>\s*[\"“])"
        )
        for i, line in enumerate(head, 1):
            if i not in added or not line.strip():
                continue
            if re.search(r"\[[xX]\]", line):
                self.r.v(
                    "readouts",
                    "G4b-tick",
                    path,
                    i,
                    "a checkbox was ticked in a signing diff — the Signature block quotes what the operator "
                    "declares met (BM-GATE-07)",
                    commit,
                )
                continue
            if i in in_block:
                continue
            if not allowed.match(line):
                self.r.v(
                    "readouts",
                    "G4b-prose",
                    path,
                    i,
                    f"unlabelled prose added in a signing diff ('{line[:60]}') — agent text sits in an "
                    "agent-drafted block confirmed by the operator (BM-GATE-08, DRAFT-MEM-5)",
                    commit,
                )
            if re.match(r"^\s*Operator decision \(verbatim", line):
                decision_quotes += quotes(line)
        status_signed = any(
            re.match(r"^\s*Status:\s*(" + "|".join(READOUT_STATUSES) + r")\b", strip_markup(t))
            for _, _, t in recs.added
        )
        if status_signed and not decision_quotes:
            self.r.v(
                "readouts",
                "G4b-verbatim",
                path,
                0,
                'Status moved out of PENDING without an appended `Operator decision (verbatim …): "…"` line '
                "(BM-INDEX-03)",
                commit,
            )
        gd_quotes, conf_quotes = gate_decision_quotes(self.c.at_head(LEDGER_REL) or "")
        for q in decision_quotes:
            if qnorm(q) not in gd_quotes:
                self.r.v(
                    "readouts",
                    "G4b-verbatim",
                    path,
                    0,
                    f'the operator decision "{q[:60]}" does not equal any GATE DECISIONS answer (DRAFT-MEM-5)',
                    commit,
                )
            for rx in DELEGATION_RES:
                if rx.search(q):
                    self.r.v(
                        "readouts",
                        "G4b-delegation",
                        path,
                        0,
                        f"the signature delegates ('{rx.search(q)[0]}') — an agent never signs (BM-GATE-07)",
                        commit,
                    )
                    break
        # every agent-drafted block needs the operator's confirmation quoting its hash prefix
        for sha, _, _ in drafted_blocks(head):
            conf = [
                ln for ln in head if re.match(r"^\s*Operator confirmation", ln) and sha[:12] in ln
            ]
            if not conf:
                self.r.v(
                    "readouts",
                    "G4b-confirmation",
                    path,
                    0,
                    f"agent-drafted block sha256:{sha[:12]} has no operator confirmation quoting its hash prefix "
                    "(BM-GATE-08)",
                    commit,
                )
                continue
            words = [q for ln in conf for q in quotes(ln)]
            if not words or not all(qnorm(w) in conf_quotes for w in words):
                self.r.v(
                    "readouts",
                    "G4b-confirmation",
                    path,
                    0,
                    f"the confirmation of sha256:{sha[:12]} is not recorded verbatim as a GATE DECISIONS "
                    "`confirmation` row (BM-GATE-08)",
                    commit,
                )

    def agent_drafted(self, path: str, head: list[str], added: set[int], commit: str) -> None:
        for sha, begin, end in drafted_blocks(head):
            if not any(begin <= i <= end for i in added):
                continue
            body = head[begin : end - 1]
            got = {
                hashlib.sha256(("\n".join(body) + "\n").encode()).hexdigest(),
                hashlib.sha256("\n".join(body).encode()).hexdigest(),
            }
            if sha.lower() not in got:
                self.r.v(
                    "readouts",
                    "G4b-drafted-hash",
                    path,
                    begin,
                    f"agent-drafted block sha256={sha[:12]}… does not match its body "
                    f"({sorted(got)[0][:12]}…) (BM-GATE-08)",
                    commit,
                )

    # -- BUILD_INDEX
    def judge_index(self, status: str, path: str, recs: DiffRecs) -> None:
        self.no_removals(
            path,
            recs,
            "append-only",
            "append-only",
            "BUILD_INDEX is append-only; a correction is an appended row (BM-INDEX-01)",
        )
        head = (self.c.at_head(path) or "").split("\n")
        added = {hl for hl, _, _ in recs.added}
        hn = sc = pc = dc = 0
        have = False
        seen: dict[str, int] = {}
        cand = ev = 0  # record-shape (G11): added rows offered / judged against a header
        for i, line in enumerate(head, 1):
            if not line.startswith("|") or is_separator(line):
                continue
            if i < len(head) and is_separator(head[i]):
                hdr = [strip_markup(c).strip().lower() for c in table_cells(line)]
                hn = len(hdr)
                sc = next((k + 1 for k, c in enumerate(hdr) if c in ("seq", "#")), 0)
                pc = next((k + 1 for k, c in enumerate(hdr) if c == "pr"), 0)
                dc = next((k + 1 for k, c in enumerate(hdr) if c == "landed"), 0)
                # seq is unique only in an index table (it has a PR or landed column); a corrections
                # table may name one seq once per corrected field.
                if not (pc or dc):
                    sc = 0
                # Every index table shares one seq space (the main index, SEED-09's late marker rows,
                # the `## Round 11` table): `seen` is not reset per table (SEED-02b).
                have = True
                continue
            if not have:
                cand += i in added  # an added row under no header cannot be judged (G11)
                continue
            cells = table_cells(line)
            seq = strip_markup(cells[sc - 1]).strip() if sc and len(cells) >= sc else ""
            if i not in added:
                if seq:
                    seen[seq] = i
                continue
            cand += 1
            ev += 1
            commit = self.c.commit_of_added(path, line).short
            if len(cells) != hn:
                self.r.v(
                    "record-shape",
                    "columns",
                    path,
                    i,
                    f"added BUILD_INDEX row has {len(cells)} cells, the header has {hn} — escape a | inside a cell "
                    "as \\| (BM-INDEX-01)",
                    commit,
                )
            if seq and seq in seen:
                self.r.v(
                    "record-shape",
                    "seq",
                    path,
                    i,
                    f"added BUILD_INDEX row reuses seq {seq} (first at line {seen[seq]}) (BM-INDEX-01)",
                    commit,
                )
            if seq:
                seen[seq] = i
            if (
                pc
                and len(cells) >= pc
                and re.search(r"[Pp]ending|TBD", strip_markup(cells[pc - 1]))
            ):
                self.r.v(
                    "record-shape",
                    "pr",
                    path,
                    i,
                    f"added BUILD_INDEX row has no real PR ('{cells[pc - 1][:20]}') — the worker closes after the "
                    "PR exists (BM-INDEX-01)",
                    commit,
                )
            if dc and len(cells) >= dc:
                m = DATE_RE.search(cells[dc - 1])
                if m:
                    self.add_date(path, i, "act", m[0], line)
                else:
                    self.undated(path, i, "BUILD_INDEX `landed` cell")
        self.r.count("record-shape", cand, ev)

    # -- manifest
    def judge_manifest(self, status: str, path: str, recs: DiffRecs) -> None:
        base = (self.c.at_base(path) or "").split("\n")
        head = (self.c.at_head(path) or "").split("\n")
        sec_of: dict[int, str] = {}
        cur = ""
        for i, line in enumerate(base, 1):
            if re.match(r"^##\s", line):
                cur = (
                    line
                    if re.match(r"^##\s+(Spec amendments applied|Plan extensions)", line)
                    else ""
                )
            sec_of[i] = cur
        added_norm = {norm(t) for _, _, t in recs.added}
        for ln, text in recs.removed:
            if sec_of.get(ln) and text.strip() and norm(text) not in added_norm:
                self.r.v(
                    "append-only",
                    "append-only",
                    path,
                    ln,
                    f"manifest line {ln} in '{sec_of[ln][:40]}' removed or rewritten — that section only appends "
                    "(BM-MANIFEST-01)",
                    self.c.commit_of_removed(path, text),
                )

        def chain(lines: list[str]) -> list[tuple[int, str, str]]:
            out, on, banner = [], False, ""
            for i, line in enumerate(lines, 1):
                if re.match(r"^##\s+The chain", line):
                    on, banner = True, ""
                    continue
                if on and re.match(r"^##\s", line):
                    on = False
                if on and line.startswith("###"):
                    banner = line
                    continue
                if on and line.startswith("|"):
                    m = re.search(r"[0-9A-Za-z_.-]+\.md", line)
                    if m:
                        out.append((i, m[0], banner))
            return out

        def idof(f: str) -> tuple[str, str]:
            x = re.sub(r"^[0-9]+[a-z]?_", "", f)
            x = re.sub(r"\.md$", "", x)
            if "__" in x:
                a, b = x.split("__", 1)
                return a, b
            return x, ""

        base_files = {f for _, f, _ in chain(base)}
        slug_of = {idof(f)[0]: idof(f)[1] for f in base_files}
        added = {hl for hl, _, _ in recs.added}
        for i, f, banner in chain(head):
            if i not in added or f in base_files:
                continue
            self.r.count("record-shape", 1, 1)
            tid, slug = idof(f)
            if tid in slug_of and slug_of[tid] != slug:
                self.r.v(
                    "record-shape",
                    "id-registry",
                    path,
                    i,
                    f"chain id {tid} re-bound from slug '{slug_of[tid]}' to '{slug}' — an id never binds to another "
                    "file (BM-MANIFEST-03)",
                )
            if not re.match(r"^###\s+Round\s+[0-9]+", banner):
                self.r.v(
                    "record-shape",
                    "round-banner",
                    path,
                    i,
                    f"new chain row {f} is not under a numbered '### Round <n>' banner (BM-MANIFEST-01, V13)",
                )
        cur = ""
        for i, line in enumerate(head, 1):
            if re.match(r"^##\s", line):
                cur = (
                    line
                    if re.match(r"^##\s+(Spec amendments applied|Plan extensions)", line)
                    else ""
                )
                continue
            if cur and i in added:
                m = re.match(r"^[-|][\s|*]*(\d{4}-\d{2}-\d{2})", line)
                if m:
                    self.add_date(path, i, "act", m[1], line)

    # -- frozen files
    def judge_contract(self, status: str, path: str, recs: DiffRecs) -> None:
        if status in ("A", "N"):
            return
        self.frozen_common(
            path,
            recs,
            "an executed contract is frozen; amend it with an appended "
            "'> Amended <date -u +%F>:' note (BM-TICKET-04)",
        )
        lastnb = last_nonblank(self.c.at_base(path) or "")
        for hl, ins, text in recs.added:
            if ins < lastnb or not text.strip():
                continue
            if not text.startswith(">"):
                self.r.v(
                    "append-only",
                    "amendment",
                    path,
                    hl,
                    f"added line {hl} is not part of a '> Amended <date -u +%F>:' note (BM-TICKET-04)",
                    self.c.commit_of_added(path, text).short,
                )
            elif re.match(r"^>\s*Amended", text):
                m = re.search(r"\d{4}-\d{2}-\d{2}", text)
                if m:
                    self.add_date(path, hl, "act", m[0], text)

    def frozen_common(self, path: str, recs: DiffRecs, what: str) -> None:
        lastnb = last_nonblank(self.c.at_base(path) or "")
        for ln, text in recs.removed:
            self.r.v(
                "append-only",
                "frozen",
                path,
                ln,
                f"line {ln} removed or rewritten — {what}",
                self.c.commit_of_removed(path, text),
            )
        for hl, ins, text in recs.added:
            if ins < lastnb:
                self.r.v(
                    "append-only",
                    "append-position",
                    path,
                    hl,
                    f"line {hl} inserted before the end of a frozen/append-only file — append at EOF (BM-HIST-01)",
                    self.c.commit_of_added(path, text).short,
                )

    def judge_policy_ao(self, status: str, path: str, recs: DiffRecs) -> None:
        if status in ("A", "N"):
            return
        self.frozen_common(
            path,
            recs,
            "this file only appends at EOF (record_policy/history.policy); a "
            "correction is an appended amendment, never a re-stamp (C-10)",
        )

    def judge_adr(self, status: str, path: str, recs: DiffRecs) -> None:
        """A new ADR: its `Date:` header is an act (G1). A landed ADR (present at BASE) is frozen: no line
        is removed or changed, and additions are allowed only (a) at EOF as a `## Status updates` section
        (or a bare status line, the skill's form) and (b) as `### Trigger evaluation …` subsections at the
        end of `## Revisit trigger` (or at EOF when that section is last)."""
        head = (self.c.at_head(path) or "").split("\n")
        if status in ("A", "N") or self.c.at_base(path) is None:
            # "N": an ADR added after the landed base and edited again — still new, not frozen; its
            # `Date:` header is judged only when this change writes it.
            added = {hl for hl, _, _ in recs.added}
            for i, line in enumerate(head, 1):
                if re.match(r"^##\s", line):
                    break
                if re.match(r"^\s*(-\s*)?(\*\*)?Date:", line):
                    if status == "N" and i not in added:
                        break
                    m = DATE_RE.search(line)
                    if m:
                        self.add_date(path, i, "act", m[0], line)
                    else:
                        self.undated(path, i, "ADR `Date:` header")
                    break
            return
        base = (self.c.at_base(path) or "").split("\n")
        for ln, text in recs.removed:
            self.r.v(
                "append-only",
                "frozen",
                path,
                ln,
                f"line {ln} removed or rewritten ('{text[:60]}') — a landed ADR is frozen; only an appended "
                "`## Status updates` section or a `### Trigger evaluation` subsection at the end of "
                "`## Revisit trigger` is allowed (BM-ADR-01, SIG-ENG-003)",
                self.c.commit_of_removed(path, text),
            )
        lastnb = last_nonblank("\n".join(base))
        rt = next(
            (r for r in regions(base) if re.match(r"^##\s+Revisit trigger", r.heading, re.I)), None
        )
        hregs = regions(head)
        subs = regions(head, level=3)
        adr_ids = {
            m[1] for p in self.c.head_files("docs/adr") if (m := re.search(r"/(ADR-\d+)-", p))
        }
        prev_ok_status = False
        for hl, ins, text in recs.added:
            commit = self.c.commit_of_added(path, text).short
            at_eof = ins >= lastnb
            if not (at_eof or (rt is not None and rt.lnb <= ins <= rt.end)):
                self.r.v(
                    "append-only",
                    "append-position",
                    path,
                    hl,
                    f"line {hl} inserted inside a landed ADR — additions go only at the end of the file or at the "
                    "end of `## Revisit trigger` (BM-ADR-01)",
                    commit,
                )
                continue
            if not text.strip():
                continue
            sec = region_at(hregs, hl)
            near = region_at(subs, hl)
            sec_h = sec.heading if sec else ""
            sub_h = near.heading if near and near.heading.startswith("###") else ""
            in_status = bool(re.match(r"^##\s+Status updates\b", sec_h, re.I))
            in_eval = bool(re.match(r"^##\s+Revisit trigger", sec_h, re.I)) and bool(
                re.match(r"^###\s+Trigger evaluation\b", sub_h, re.I)
            )
            status_line = bool(ADR_STATUS_RE.search(text)) and bool(
                ADR_STATUS_BULLET_RE.match(text) or re.match(r"^\s*(-\s*)?Superseded by", text)
            )
            continuation = prev_ok_status and re.match(r"^\s{2,}\S", text) is not None
            if not (in_status or in_eval or (status_line and at_eof) or continuation):
                self.r.v(
                    "append-only",
                    "frozen",
                    path,
                    hl,
                    f"added line {hl} ('{text[:50]}') is outside a `## Status updates` section or a "
                    "`### Trigger evaluation` subsection of `## Revisit trigger` — a landed ADR body is frozen "
                    "(BM-ADR-01, SIG-ENG-003)",
                    commit,
                )
                prev_ok_status = False
                continue
            if "**Status:**" in text or status_line:
                problems = []
                if not ADR_STATUS_RE.search(text):
                    problems.append(
                        "it does not read `<Superseded|Qualified|Amended|Extended|Revisited> by ADR-NNN`"
                    )
                missing = [
                    f"ADR-{n}" for n in re.findall(r"ADR-(\d+)", text) if f"ADR-{n}" not in adr_ids
                ]
                if missing:
                    problems.append(f"{', '.join(missing)} does not exist at the head")
                if not DATE_RE.search(text):
                    problems.append("it carries no `date -u`")
                for p in problems:
                    self.r.v(
                        "append-only",
                        "superseded-by",
                        path,
                        hl,
                        f"appended status line: {p} (BM-ADR-01, plan §7)",
                        commit,
                    )
            if not continuation:
                prev_ok_status = bool(
                    ADR_STATUS_BULLET_RE.match(text) or status_line or re.match(r"^\s*-\s", text)
                )
            if ("**Status" in text and re.match(r"^\s*-\s", text)) or re.match(
                r"^###\s+Trigger evaluation", text, re.I
            ):
                m = DATE_RE.search(text)
                if m:
                    self.add_date(path, hl, "act", m[0], text)

    def judge_jsonl(self, status: str, path: str, recs: DiffRecs) -> None:
        base = self.c.base_bytes(path) or b""
        head = self.c.head_bytes(path) or b""
        if status != "N" and base and not head.startswith(base):
            self.r.v(
                "append-only",
                "prefix",
                path,
                0,
                f"{path} no longer starts with its previous {len(base)} bytes — a .jsonl record file only appends "
                "(BM-HIST-01)",
                self.c.head_commit.short if self.c.mode == "first-parent" else "",
            )
        for hl, _, text in recs.added:
            for key, cls in (
                ("recorded_at", "act"),
                ("observed_at", "event"),
                ("assessed_at", "event"),
            ):
                m = re.search(r'"' + key + r'"\s*:\s*"([^"]+)"', text)
                if m:
                    self.add_date(path, hl, cls, m[1], text)

    def judge_digest(self, status: str, path: str, recs: DiffRecs) -> None:
        if status != "N":
            self.no_removals(
                path, recs, "append-only", "append-only", "a digest is append-only (BM-DIGEST-01)"
            )
        for hl, _, text in recs.added:
            if re.match(r"^##\s+\d", text):
                m = DATE_RE.search(text)
                if m:
                    self.add_date(path, hl, "act", m[0], text)

    def judge_runpr(self, status: str, path: str, recs: DiffRecs) -> None:
        if status != "N" and "/runs/" in path and run_ledger_closed(self.c.at_base(path) or ""):
            self.no_removals(
                path,
                recs,
                "append-only",
                "append-only",
                "a closed run ledger only gains lines; a later fact is an appended dated note "
                "(BM-INDEX-02)",
            )
        header_end = header_end_line((self.c.at_head(path) or "").split("\n"))
        for hl, _, text in recs.added:
            if STAMP_RE.match(text):
                m = DATE_RE.search(text)
                if m:
                    self.add_date(path, hl, "act", m[0], text)
                elif (
                    hl < header_end
                ):  # an undated header stamp; "- **Closed:** none." in a body is not one
                    self.undated(path, hl, "run/PR ledger header stamp")

    def judge_policy_dates(self, path: str, recs: DiffRecs) -> None:
        rules = [rx for g, rx in self.pol.dates if fnmatch.fnmatchcase(path, g)]
        if not rules:
            return
        conds = [rx for g, rx in self.pol.act_when if fnmatch.fnmatchcase(path, g)]
        head = (self.c.at_head(path) or "").split("\n")
        base = (self.c.at_base(path) or "").split("\n")
        group_head = toml_groups(head)
        group_base = toml_groups(base)
        flipped: set[str] = set()
        for hl, _, text in recs.added:
            if any(rx.search(text) for rx in conds):
                flipped.add(group_head.get(hl, ""))
        for ln, text in recs.removed:
            if any(rx.search(text) for rx in conds):
                flipped.add(group_base.get(ln, ""))
        for hl, _, text in recs.added:
            if not any(rx.search(text) for rx in rules):
                continue
            m = DATE_RE.search(text)
            if not m:
                self.undated(path, hl, "policy `date` position")
                continue
            cls = "act" if not conds or group_head.get(hl, "") in flipped else "event"
            self.add_date(path, hl, cls, m[0], text)

    # -- G1: judge every collected record date
    def judge_dates(self) -> None:
        evaluated = 0
        now = self.c.now
        for d in self.dates:
            st = parse_stamp(d.stamp_text)
            commit = self.c.commit_of_added(d.path, d.text)
            if st is None:
                self.r.v(
                    d.check,
                    "R1",
                    d.path,
                    d.line,
                    f"unparseable record date '{d.stamp_text}'",
                    commit.short,
                )
                continue
            evaluated += 1
            if st.malformed:
                self.r.v(
                    d.check,
                    "R1-malformed",
                    d.path,
                    d.line,
                    f"record stamp '{d.stamp_text}' is malformed; judged at its lowest reading — write the time "
                    "from `date -u` (BM-CLOCK-01)",
                    commit.short,
                )
            exempt, why = r1_exempt(self.pol, d.path, d.text, st, now)
            if why:
                self.r.v(d.check, "R5-malformed", d.path, d.line, why, commit.short)
            if not exempt and not r1_ok(st, commit, now):
                if not correction_context(d.text, st, commit, now):
                    expired = expired_allow(self.pol, d.path, d.text, now)
                    self.r.v(
                        d.check,
                        "R1",
                        d.path,
                        d.line,
                        f"(added in {commit.short}, committed {utc_iso(commit.ct)}): record date {d.stamp_text} is later "
                        f"than its commit{'; its allow entry expired ' + expired if expired else ''} — write the time "
                        "from `date -u` at recording; a scheduled or real-world value is marked `future-ok: <class>: "
                        "<reason>` (record_policy/history.policy; BM-CLOCK-01, DRAFT-MEM-1)",
                        commit.short,
                    )
            if (
                d.cls == "act"
                and not any(mk in d.text for mk in R2_MARKERS)
                and not strict_correction(d.text, st)
                and not r2_ok(st, commit)
            ):
                self.r.v(
                    d.check,
                    "R2",
                    d.path,
                    d.line,
                    f"(added in {commit.short}, committed {utc_iso(commit.ct)}): act date {d.stamp_text} is more than "
                    "48 h before its commit — a late recording says `retro: <evidence>` or `as-of <sha|#PR>` "
                    "(BM-CLOCK-01)",
                    commit.short,
                )
        self.r.count("record-dates", self.date_candidates, evaluated)

    def judge_commit_clock(self) -> None:
        for c in self.c.commits():
            if c.ct > self.c.now + TOLERANCE_S:
                self.r.v(
                    "record-dates",
                    "R6",
                    "-",
                    0,
                    f"commit {c.short} is dated {c.ci}, later than the clock {utc_iso(self.c.now)} + 5 min — fix "
                    "the committer clock (BM-CLOCK-01)",
                    c.short,
                )


# ── shared rule helpers ──────────────────────────────────────────────────────


def r1_ok(st: Stamp, c: CommitInfo, now: int) -> bool:
    if st.has_time:
        return st.epoch <= min(c.ct, now) + TOLERANCE_S
    return st.date <= max(utc_date(c.ct), c.local_date)


def r2_ok(st: Stamp, c: CommitInfo) -> bool:
    if st.has_time:
        return st.epoch >= c.ct - ACT_WINDOW_S
    return st.date >= utc_date(c.ct - ACT_WINDOW_S)


def r1_exempt(pol: Policy, path: str, text: str, st: Stamp, now: int) -> tuple[bool, str]:
    if "future-ok:" in text:
        m = FUTURE_OK_RE.search(text)
        if m and m[1].lower() in FUTURE_OK_CLASSES:
            return True, ""
        return False, (
            "`future-ok:` needs a class and a reason: `future-ok: <scheduled|real-world|synthetic|"
            "illustrative>: <reason>` (R5)"
        )
    for a in pol.allow:
        if fnmatch.fnmatchcase(path, a.glob) and a.text in " ".join(text.split()):
            within = st.epoch <= a.expires if st.has_time else st.date <= utc_date(a.expires)
            if now <= a.expires and within:
                return True, ""
    return False, ""


def expired_allow(pol: Policy, path: str, text: str, now: int) -> str:
    for a in pol.allow:
        if (
            fnmatch.fnmatchcase(path, a.glob)
            and a.text in " ".join(text.split())
            and now > a.expires
        ):
            return a.expires_iso
    return ""


def correction_context(text: str, st: Stamp, c: CommitInfo, now: int) -> bool:
    if not CORRECTION_RE.search(text):
        return False
    for m in DATE_RE.finditer(text):
        o = parse_stamp(m[0])
        if o and m[0] != st.text and r1_ok(o, c, now):
            return True
    return False


STAMP_RE = re.compile(r"^\s*(-\s*)?(\*\*)?(Date|Started|Closed|Landed|Recorded)(\*\*)?:")


def header_end_line(lines: list[str]) -> int:
    """The first `##` heading's line number (the header block lies before it)."""
    return next((i for i, ln in enumerate(lines, 1) if re.match(r"^##\s", ln)), len(lines) + 1)


def run_ledger_closed(text: str) -> bool:
    """A run ledger is closed when its header carries a dated `Closed:` stamp."""
    lines = text.split("\n")
    end = header_end_line(lines)
    return any(
        re.match(r"^\s*(-\s*)?(\*\*)?Closed(\*\*)?:", ln) and DATE_RE.search(ln)
        for ln in lines[: end - 1]
    )


def strict_correction(text: str, st: Stamp) -> bool:
    if not STRICT_CORRECTION_RE.search(text):
        return False
    return any(m[0] != st.text for m in DATE_RE.finditer(text))


def last_nonblank(text: str) -> int:
    n = 0
    for i, line in enumerate(text.split("\n"), 1):
        if line.strip():
            n = i
    return n


def status_dates(row: str) -> list[str]:
    return re.findall(
        r"(?:OPEN|PARTIAL|DONE|WONTFIX|ACCEPTED-SKELETON|DEFERRED-AGAIN)[^0-9|]{0,12}(\d{4}-\d{2}-\d{2})",
        row,
    )


def deferral_verdict(old: str, new: str) -> str:
    def nz(x: str) -> str:
        x = re.sub(r"[*`]|~~", "", x)
        return re.sub(r"\s+", " ", x).strip()

    status = r"^(OPEN|PARTIAL|DONE|WONTFIX|ACCEPTED-SKELETON)"

    def lead(c: str) -> str:
        m = re.match(status, nz(c).upper())
        return m[1] if m else ""

    def rest(c: str) -> str:
        return re.sub(status + r"\s*", "", nz(c), flags=re.I)

    o, n = table_cells(old), table_cells(new)
    for i in range(len(o) - 1):
        if i >= len(n) or nz(o[i]) not in nz(n[i]):
            return "rewritten"
    if rest(o[-1]) not in nz(n[-1]):
        return "rewritten"
    if lead(o[-1]) != lead(n[-1]):
        new_dates = [d for d in re.findall(r"\d{4}-\d{2}-\d{2}", new) if d not in old]
        return "flip" if new_dates else "flip-undated"
    return "grown"


def toml_groups(lines: list[str]) -> dict[int, str]:
    """Line → TOML record group (the first two components of the nearest `[table]` header)."""
    out, cur = {}, ""
    for i, line in enumerate(lines, 1):
        m = re.match(r"^\s*\[+\s*([^\]]+?)\s*\]+", line)
        if m:
            cur = ".".join(m[1].split(".")[:2])
        out[i] = cur
    return out


def guard_sentence_in(text: str) -> bool:
    flat = re.sub(r"[\s>]+", " ", text).lower()
    return GUARD_SENTENCE.lower() in flat


def readout_status(lines: list[str]) -> str:
    for line in lines:
        m = re.match(r"^\s*Status:\s*(.*)$", line)
        if m:
            return strip_markup(re.sub(r"<!--.*?-->", "", m[1])).strip()
    return ""


def drafted_blocks(lines: list[str]) -> list[tuple[str, int, int]]:
    out = []
    begin: tuple[str, int] | None = None
    for i, line in enumerate(lines, 1):
        m = re.search(r"<!--\s*agent-drafted:begin\s+sha256=([0-9a-fA-F]{64})\s*-->", line)
        if m:
            begin = (m[1], i)
            continue
        if begin and re.search(r"<!--\s*agent-drafted:end\s*-->", line):
            out.append((begin[0], begin[1], i))
            begin = None
    return out


def drafted_lines(lines: list[str]) -> set[int]:
    return {i for _, b, e in drafted_blocks(lines) for i in range(b, e + 1)}


def gate_decision_quotes(ledger: str) -> tuple[set[str], set[str]]:
    lines = ledger.split("\n")
    allq: set[str] = set()
    conf: set[str] = set()
    for reg in regions(lines):
        if GATE_DECISIONS_RE.match(reg.heading):
            for i in range(reg.start, reg.end + 1):
                allq.update(qnorm(q) for q in quotes(lines[i - 1]))
    for t in gd_tables(lines):
        low = [strip_markup(h).strip().lower() for h in t.header]
        if "kind" in low:
            kc = low.index("kind")
            for _, row in t.rows:
                c = table_cells(row)
                if len(c) > kc and strip_markup(c[kc]).strip().lower() == "confirmation":
                    conf.update(qnorm(q) for q in quotes(row))
    return allq, conf


def date_correction_rows(csv_text: str | None) -> set[int]:
    """Restored-row numbers named by `date_corrections.csv` (`line_or_field` … `restored R<n>`)."""
    out: set[int] = set()
    if not csv_text:
        return out
    try:
        for row in csv.DictReader(io.StringIO(csv_text)):
            m = re.search(r"\brestored\s+R0*(\d+)\b", row.get("line_or_field") or "")
            if m:
                out.add(int(m[1]))
    except csv.Error:
        return out
    return out


def blame_lines(git: Git, rev: str, path: str) -> dict[int, CommitInfo]:
    out = git.text("blame", "--line-porcelain", "-w", rev, "--", path)
    res: dict[int, CommitInfo] = {}
    sha, final, ct, tz = "", 0, 0, "+0000"
    for line in out.split("\n"):
        m = re.match(r"^([0-9a-f]{40}) \d+ (\d+)", line)
        if m:
            sha, final = m[1], int(m[2])
            continue
        if line.startswith("committer-time "):
            ct = int(line.split()[1])
        elif line.startswith("committer-tz "):
            tz = line.split()[1]
        elif line.startswith("\t"):
            sign = -1 if tz.startswith("-") else 1
            off = sign * (int(tz[1:3]) * 3600 + int(tz[3:5]) * 60)
            local = dt.datetime.fromtimestamp(ct, dt.timezone(dt.timedelta(seconds=off)))
            res[final] = CommitInfo(sha, ct, local.isoformat())
    return res


def judge_restored_blocks(
    git: Git,
    path: str,
    head: list[str],
    added: set[int] | None,
    corrections_csv: str | None,
    now: int,
    r: Report,
) -> None:
    """G1 blame mode: restored rows exist verbatim at `<sha>^`; their dates are judged against `git blame`."""
    tables = gd_tables(head)
    csv_rows = date_correction_rows(corrections_csv)
    cand = ev = 0
    for ti, t in enumerate(tables):
        sha = t.restored_from
        if not sha:
            continue
        if added is not None and not any(ln in added for ln, _ in t.rows):
            continue
        src_rev = f"{sha}^"
        rows = t.rows
        cand += len(rows)
        src_sha = git.resolve(src_rev)
        if not src_sha:
            r.v(
                "restored-dates",
                "source",
                path,
                t.header_line,
                f"the RESTORED caption names {src_rev}, which does not resolve — restore from a real commit (B2 §4.1)",
            )
            continue
        raw = git.show(src_sha, path)
        if raw is None:
            r.v(
                "restored-dates",
                "source",
                path,
                t.header_line,
                f"{path} does not exist at {src_rev}",
            )
            continue
        src = raw.decode("utf-8", "replace").split("\n")
        blame = blame_lines(git, src_sha, path)
        # annotation rows: tables after this one in the same region whose first cell is R<n>
        notes: dict[int, str] = {}
        for later in tables[ti + 1 :]:
            if later.region.start != t.region.start or later.restored_from:
                break
            for _, row in later.rows:
                c = table_cells(row)
                mm = re.match(r"^R0*(\d+)$", strip_markup(c[0]).strip()) if c else None
                if mm:
                    notes[int(mm[1])] = notes.get(int(mm[1]), "") + " " + row
        used = 0
        for n, (ln, row) in enumerate(rows, 1):
            src_ln = next(
                (k for k in range(used + 1, len(src) + 1) if src[k - 1] == row), 0
            ) or next((k for k in range(1, len(src) + 1) if norm(src[k - 1]) == norm(row)), 0)
            if not src_ln:
                r.v(
                    "restored-dates",
                    "verbatim",
                    path,
                    ln,
                    f"restored row R{n:02d} is not a verbatim line of {path} at {src_rev} — a restoration quotes the "
                    "removed text byte-for-byte (B2 §4.1)",
                )
                continue
            used = max(used, src_ln)
            info = blame.get(src_ln)
            cells = table_cells(row)
            dm = DATE_RE.search(cells[0]) if cells else None
            st = parse_stamp(dm[0]) if dm else None
            if info is None or st is None:
                continue
            ev += 1
            verdict = []
            if not r1_ok(st, info, now):
                verdict.append("R1")
            if not any(mk in row for mk in R2_MARKERS) and not r2_ok(st, info):
                verdict.append("R2")
            note = notes.get(n, "")
            annotated = bool(re.search(r"clock-false|date correction", note, re.I)) or n in csv_rows
            r.restored.append(
                {
                    "row": f"R{n:02d}",
                    "line": ln,
                    "source_line": src_ln,
                    "date": st.text,
                    "blame_commit": info.short,
                    "blame_time": utc_iso(info.ct),
                    "verdict": "+".join(verdict) or "ok",
                    "annotated": annotated,
                }
            )
            if verdict and not annotated:
                for rule in verdict:
                    what = (
                        "later than the commit that first wrote it"
                        if rule == "R1"
                        else "more than 48 h before the commit that first wrote it"
                    )
                    r.v(
                        "restored-dates",
                        f"blame-{rule}",
                        path,
                        ln,
                        f"restored row R{n:02d} is dated {st.text}, {what} ({info.short}, {utc_iso(info.ct)}, by "
                        f"`git blame {src_rev}` line {src_ln}) and no annotation marks it clock-false — append an "
                        "annotation row `| R<n> | … clock-false | DATE CORRECTION: recorded → true … |` or a "
                        "date_corrections.csv row naming `restored R<n>` (TS-08, ADR-146)",
                        info.short,
                    )
    r.count("restored-dates", cand, ev)


# ── shared policy readers ────────────────────────────────────────────────────

CI_REQUIRED_REL = "docs/build/tools/record_policy/ci_required.txt"


def read_ci_required(text: str) -> list[str]:
    """The required check names of `record_policy/ci_required.txt` (one per line, `#` comments), for
    `ci_boundary.py` (G3a). Raises ValueError on a malformed name or an empty list — never vacuous."""
    names = []
    for n, line in enumerate(text.splitlines(), 1):
        s = Policy.strip_comment(line)
        if not s:
            continue
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", s):
            raise ValueError(f"ci_required.txt line {n}: '{s}' is not a check name")
        names.append(s)
    if not names:
        raise ValueError("ci_required.txt names no check")
    return names


# ── driver ───────────────────────────────────────────────────────────────────


def repo_root(arg: str | None) -> Path:
    if arg:
        p = Path(arg).resolve()
        if not p.is_dir():
            raise UsageError(f"no such repo: {arg}")
        top = subprocess.run(
            ["git", "-C", str(p), "rev-parse", "--show-toplevel"], capture_output=True, text=True
        )
        return Path(top.stdout.strip()) if top.returncode == 0 else p
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if top.returncode != 0:
        raise UsageError("not inside a git repository (use --repo)")
    return Path(top.stdout.strip())


def finish(
    report: Report,
    families: Iterable[str],
    meta: dict[str, object],
    json_path: str | None,
    title: str,
) -> int:
    fams = tuple(families)
    kept = [f for f in report.findings if f.check in fams]
    viol = [f for f in kept if f.severity == "error"]
    warn = [f for f in kept if f.severity == "warning"]
    vacuous = [c for c in fams if report.counts.get(c, [0, 0])[0] > 0 and report.counts[c][1] == 0]
    code = EXIT_VIOLATIONS if viol else (EXIT_VACUOUS if vacuous else EXIT_OK)
    checks = []
    for c in fams:
        cand, ev = report.counts.get(c, [0, 0])
        checks.append(
            {
                "check": c,
                "candidates": cand,
                "evaluated": ev,
                "violations": [f.as_json() for f in viol if f.check == c],
                "warnings": [f.as_json() for f in warn if f.check == c],
            }
        )
    doc = {
        "schema": SCHEMA,
        "tool": "docs/build/tools/memory_guard.py",
        "input": meta,
        "summary": {"violations": len(viol), "warnings": len(warn), "exit": code},
        "checks": checks,
        "restored": report.restored,
        "exit": code,
    }
    print(title)
    if viol:
        print(f"  ✗ {len(viol)} violation(s), {len(warn)} warning(s):")
    elif vacuous:
        print(
            f"  ? vacuous: {', '.join(vacuous)} evaluated none of its candidates (G11) — not green"
        )
    else:
        n = sum(report.counts.get(c, [0, 0])[1] for c in fams)
        print(f"  ✓ no violations ({len(warn)} warning(s); {n} item(s) evaluated)")
    for f in viol:
        at = f" @{f.commit}" if f.commit else ""
        print(f"    - {f.check} [{f.rule}] {f.path}:{f.line}{at}: {f.message}")
    for f in warn:
        print(f"    ~ {f.check} [{f.rule}] {f.path}:{f.line}: {f.message}")
    if json_path:
        p = Path(json_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  JSON: {json_path}")
    return code


def preflight(root: Path, git: Git, rev_for_readme: str | None) -> tuple[bool, Policy]:
    """Applicable when the checkout (as the skill reads it) or the judged revision is a build-memory repo;
    the guards marker and the policy come from the judged revision when it has them (a replay of a
    pre-v2 commit is judged under today's marker and policy, as check-history.sh does)."""
    readme = (
        (root / README_REL).read_text(encoding="utf-8", errors="replace")
        if (root / README_REL).is_file()
        else ""
    )
    if rev_for_readme:
        raw = git.show(rev_for_readme, README_REL)
        if raw is not None and BM_MARKER in raw.decode("utf-8", "replace"):
            readme = raw.decode("utf-8", "replace")
    if BM_MARKER not in readme:
        raise UsageError(
            f"{root} is not a build-memory repo (no `{BM_MARKER}` in {README_REL}) — not applicable"
        )
    # The policy in force is the one at the head being judged (a change may add or amend it).
    raw_pol = (root / POLICY_REL).read_bytes() if (root / POLICY_REL).is_file() else None
    if rev_for_readme:
        at_rev = git.show(rev_for_readme, POLICY_REL)
        raw_pol = at_rev if at_rev is not None else raw_pol
    return bool(GUARDS_RE.search(readme)), Policy.parse(raw_pol)


def cmd_change(args: argparse.Namespace) -> int:
    root = repo_root(args.repo)
    git = Git(root)
    now = parse_now(args.now)
    modes = [m for m in ("range", "first_parent", "staged", "worktree") if getattr(args, m)]
    if len(modes) != 1:
        raise UsageError("give exactly one of --range, --first-parent, --staged, --worktree")
    mode = modes[0].replace("_", "-")
    arg = getattr(args, modes[0])
    change = Change(git, mode, arg if isinstance(arg, str) else "", now)
    guards, policy = preflight(root, git, change.head if change.committed else None)
    report = Report()
    for e in policy.errors:
        report.v("append-only", "policy", POLICY_REL, 0, f"policy error: {e}")
    Judge(change, policy, report, guards).run()
    meta = {
        "repo": str(root),
        "mode": mode,
        "base": change.base or "(empty tree)",
        "head": change.head,
        "landed_base": change.landed_base or "(empty tree)",
        "landed_from": change.landed_from,
        "ci_now": utc_iso(now),
        "policy_sha256": policy.sha256 or None,
        "guards": guards,
    }
    families = FAMILIES[args.cmd] + (
        ("append-only",) if policy.errors and args.cmd != "all" else ()
    )
    title = (
        f"memory-guard {args.cmd}: {mode} {arg if isinstance(arg, str) else ''} "
        f"({(change.base or 'empty')[:12]}..{change.head[:12]}) in {root}"
    )
    return finish(report, families, meta, args.json, title)


def cmd_restored(args: argparse.Namespace) -> int:
    root = repo_root(args.repo)
    git = Git(root)
    now = parse_now(args.now)
    if args.worktree:
        head_text = (root / LEDGER_REL).read_text(encoding="utf-8", errors="replace")
        csv_text = (
            (root / DATE_CORRECTIONS_REL).read_text(encoding="utf-8")
            if (root / DATE_CORRECTIONS_REL).is_file()
            else None
        )
        rev = "worktree"
    else:
        rev = git.resolve(args.rev or "HEAD") or ""
        if not rev:
            raise UnknownError(f"cannot resolve '{args.rev}'")
        raw = git.show(rev, LEDGER_REL)
        if raw is None:
            raise UnknownError(f"{LEDGER_REL} does not exist at {rev}")
        head_text = raw.decode("utf-8", "replace")
        cr = git.show(rev, DATE_CORRECTIONS_REL)
        csv_text = cr.decode("utf-8", "replace") if cr is not None else None
    if git.is_shallow():
        raise UnknownError("shallow clone — blame mode needs the full history (set fetch-depth: 0)")
    preflight(root, git, None if args.worktree else rev)
    report = Report()
    judge_restored_blocks(git, LEDGER_REL, head_text.split("\n"), None, csv_text, now, report)
    meta = {
        "repo": str(root),
        "mode": "restored",
        "base": None,
        "head": rev,
        "ci_now": utc_iso(now),
        "policy_sha256": None,
        "guards": None,
    }
    return finish(
        report,
        FAMILIES["restored"],
        meta,
        args.json,
        f"memory-guard restored: {LEDGER_REL} at {rev[:12]}",
    )


def cmd_replay(args: argparse.Namespace) -> int:
    root = repo_root(args.repo)
    git = Git(root)
    if ".." not in args.span:
        raise UsageError("replay wants FROM..TO")
    if git.is_shallow():
        raise UnknownError("shallow clone — replay needs the full history (set fetch-depth: 0)")
    commits = git.text("rev-list", "--reverse", "--first-parent", args.span).split()
    results = []
    bad = 0
    for c in commits:
        sub = argparse.Namespace(
            cmd="all",
            repo=str(root),
            now=args.now,
            json=None,
            range=None,
            first_parent=c,
            staged=False,
            worktree=False,
        )
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            rc = cmd_change(sub)
        except UnknownError:
            rc = EXIT_UNKNOWN
        except UsageError:
            rc = EXIT_USAGE
        finally:
            sys.stdout = old
        rules: dict[str, int] = {}
        for line in buf.getvalue().splitlines():
            m = re.match(r"^    - ([a-z-]+) \[([A-Za-z0-9-]+)\]", line)
            if m:
                rules[f"{m[1]}[{m[2]}]"] = rules.get(f"{m[1]}[{m[2]}]", 0) + 1
        bad += rc == EXIT_VIOLATIONS
        info = git.text("log", "-1", "--format=%h %cI", c).strip()
        tag = " ".join(f"{k}×{v}" for k, v in sorted(rules.items()))
        print(f"{info} exit={rc} {tag}".rstrip())
        results.append({"commit": c, "exit": rc, "rules": rules})
    print(
        f"memory-guard replay {args.span}: {len(commits)} commit(s) judged, {bad} with violations"
    )
    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "schema": "memory-guard-replay/1",
                    "range": args.span,
                    "commits": results,
                    "judged": len(commits),
                    "violating": bad,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return EXIT_VIOLATIONS if bad else EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="memory_guard.py",
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("all", "dates", "append-only", "gates", "readouts"):
        sp = sub.add_parser(name, help=f"judge a change ({', '.join(FAMILIES[name])})")
        g = sp.add_mutually_exclusive_group()
        g.add_argument("--range", metavar="BASE..HEAD")
        g.add_argument("--first-parent", metavar="SHA", dest="first_parent")
        g.add_argument("--staged", action="store_true")
        g.add_argument("--worktree", action="store_true")
        sp.add_argument("--json", metavar="PATH")
        sp.add_argument("--now", metavar="ISO")
        sp.add_argument("--repo", metavar="DIR")
    sp = sub.add_parser(
        "restored", help="judge every RESTORED GATE DECISIONS block against git blame"
    )
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--rev", metavar="REV")
    g.add_argument("--worktree", action="store_true")
    sp.add_argument("--json", metavar="PATH")
    sp.add_argument("--now", metavar="ISO")
    sp.add_argument("--repo", metavar="DIR")
    sp = sub.add_parser(
        "replay", help="judge every first-parent commit of FROM..TO on its own (read-only)"
    )
    sp.add_argument("span", metavar="FROM..TO")
    sp.add_argument("--json", metavar="PATH")
    sp.add_argument("--now", metavar="ISO")
    sp.add_argument("--repo", metavar="DIR")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return EXIT_USAGE if exc.code not in (0, None) else EXIT_OK
    try:
        if args.cmd == "restored":
            return cmd_restored(args)
        if args.cmd == "replay":
            return cmd_replay(args)
        if (
            args.staged is False
            and args.worktree is False
            and not args.range
            and not args.first_parent
        ):
            raise UsageError("one of --range, --first-parent, --staged, --worktree is required")
        return cmd_change(args)
    except UsageError as exc:
        print(f"memory-guard: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except UnknownError as exc:
        print(f"memory-guard: {exc} — unknown, never green", file=sys.stderr)
        return EXIT_UNKNOWN


if __name__ == "__main__":
    sys.exit(main())
