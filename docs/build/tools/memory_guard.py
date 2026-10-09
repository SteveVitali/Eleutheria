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
OBLIGATIONS_REL = "docs/build/reports/obligations/events.jsonl"
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

# `placeholder-fill` (B2 §7): a removed line may be replaced only by the same line with declared
# placeholder tokens filled. The token set is declared in the policy (`placeholder <token>`); the
# blank `______` generalises to any underscore run, incl. labelled blanks like `__CLOSED__`.
BLANK_PLACEHOLDER = "______"
BLANK_PH_RE = re.compile(r"_{3,}|_{2,}[\w-]*_{2,}")

# `row-annotate` regions of the LEDGER (B2 §7): OPEN FINDINGS and RETURN PASS rows are annotated
# in place — the id-matched old text stays contained in the new text (strike-through allowed).
ANNOTATE_REGION_RE = re.compile(r"^##\s+(OPEN FINDINGS|RETURN PASS)\b")

# `frozen-snapshot` (B2 §7): a heading carrying a `(YYYY-MM-DD)` date and one of "sweep",
# "snapshot", "as of" names a frozen snapshot region — no removals and no additions inside it.
SNAPSHOT_HEADING_RE = re.compile(r"^#{2,3}\s+.*\(\d{4}-\d{2}-\d{2}\)")
SNAPSHOT_WORD_RE = re.compile(r"\b(sweep|snapshot|as of)\b", re.I)

# `frozen-after-close` (B2 §7): a closed run ledger takes only placeholder fills and appended
# `## Correction` sections.
CORRECTION_HEADING_RE = re.compile(r"^##\s+Correction\b", re.I)

# `frozen-after-execution` (B2 §7): an executed contract is frozen except appended
# `> Amended YYYY-MM-DD:` blocks — plus a `Gate status:` fill in the executing ticket's first
# commit (the sanctioned shape of b4bd0068's transition-justified row).
GATE_STATUS_RE = re.compile(r"^\s*-?\s*(?:\*\*)?Gate status:(?:\*\*)?", re.I)

# `prefix` (B2 §7): obligation ledgers keep their byte prefix; each appended record is a valid
# `obligation-event/1` or `coverage-assessment/1` object and an event chains to the obligation's
# last event via `expected_previous_event`.
OBLIGATIONS_PREFIX = "docs/build/reports/obligations/"
EVENT_SCHEMA = "obligation-event/1"
ASSESSMENT_SCHEMA = "coverage-assessment/1"
EVENT_KINDS = {"migration", "transition", "correction"}
EVENT_FIELDS = (
    "schema",
    "event_id",
    "kind",
    "obligation_id",
    "seq",
    "expected_previous_event",
    "from_status",
    "to_status",
    "ticket_id",
    "owner",
    "landing",
    "backlog_home",
    "evidence_refs",
    "observed_at",
    "recorded_at",
    "source_commit",
    "reason",
)
ASSESSMENT_FIELDS = (
    "schema",
    "assessment_id",
    "requirement_id",
    "verdict",
    "domain",
    "code_revision",
    "evidence_refs",
    "limitations",
    "assessor",
    "assessed_at",
    "supersedes",
    "seq",
)
OBLIGATION_STATUSES = {"OPEN", "PARTIAL", "DONE", "WONTFIX", "ACCEPTED-SKELETON"}


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
    placeholders: list[str] = field(default_factory=list)
    seed_commits: set[str] = field(default_factory=set)
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
                elif key == "placeholder":
                    if not rest.strip():
                        raise ValueError("placeholder wants a token")
                    pol.placeholders.append(rest.strip())
                elif key == "seed-commit":
                    sha8 = rest.split()[0].lower()
                    if not re.fullmatch(r"[0-9a-f]{7,40}", sha8):
                        raise ValueError(f"seed-commit wants a commit prefix, got '{sha8}'")
                    pol.seed_commits.add(sha8)
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
        self.extra: dict[str, object] = {}  # cached scans (e.g. the chain-id registry)

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
        self._hist_subjects: list[str] | None = None
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

    def range_subjects(self) -> list[tuple[str, str]]:
        """(sha, subject) of each in-range commit, oldest first (committed modes only)."""
        if not self.committed:
            return []
        rng = f"{self.base}..{self.head}" if self.base else self.head
        out = self.git.text("log", "--reverse", "--format=%H%x09%s", rng)
        return [(h, s) for h, s in (ln.split("\t", 1) for ln in out.splitlines() if ln.strip())]

    def history_subjects(self) -> list[str]:
        """Subjects of every first-parent commit at or below the judged base — B2 §7 defines
        execution start as 'the first commit whose subject starts with the ticket id'."""
        if self._hist_subjects is None:
            rev = self.base or self.head
            if not rev:
                self._hist_subjects = []
            else:
                self._hist_subjects = self.git.text(
                    "log", "--first-parent", "--format=%s", rev
                ).splitlines()
        return self._hist_subjects

    _obligation_epoch: int | None = None

    def obligation_epoch(self) -> int:
        """Committer time of the commit that introduced the obligation-event ledger
        (`docs/build/reports/obligations/events.jsonl`, ADR-126). Before it, DEFERRALS' leading
        status token was itself the transition mechanism — rewrites of it are the sanctioned
        legacy shape; from that commit on, a token change without an obligation event is
        `transition-unjustified` (B2 register class)."""
        if self._obligation_epoch is None:
            rev = self.head if self.committed else "HEAD"
            out = self.git.text(
                "log", "--diff-filter=A", "--format=%ct", "-1", rev, "--", OBLIGATIONS_REL
            ).strip()
            self._obligation_epoch = int(out) if out else 0
        return self._obligation_epoch


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


def table_spans(lines: list[str]) -> list[tuple[int, int]]:
    """`(first, last)` line numbers of each maximal run of `|`-lines (header, separator, rows)."""
    spans: list[tuple[int, int]] = []
    start: int | None = None
    for i, line in enumerate(lines, 1):
        if line.startswith("|"):
            if start is None:
                start = i
        elif start is not None:
            spans.append((start, i - 1))
            start = None
    if start is not None:
        spans.append((start, len(lines)))
    return spans


POSITIONAL = re.compile(r"^##\s+(GATE DECISIONS|PHASE LOG|OPEN FINDINGS|RETURN PASS)")
PHASE_LOG_RE = re.compile(r"^##\s+PHASE LOG(?!\s+INDEX)")
GATE_DECISIONS_RE = re.compile(r"^##\s+GATE DECISIONS")
ROUND_RE = re.compile(r"\bRound\s+(\d+)\b")


def chain_rows(lines: list[str]) -> list[tuple[int, str]]:
    """`(line, filename)` pairs of the chain-table rows inside `## The chain` of a manifest."""
    out: list[tuple[int, str]] = []
    on = False
    for i, line in enumerate(lines, 1):
        if re.match(r"^##\s+The chain", line):
            on = True
            continue
        if on and re.match(r"^##\s", line):
            on = False
        if on and line.startswith("|"):
            m = re.search(r"[0-9A-Za-z_.-]+\.md", line)
            if m:
                out.append((i, m[0]))
    return out


def chain_idof(f: str) -> tuple[str, str]:
    """A chain filename's (ticket id, slug): `209_P34.7__x.md` → (`P34.7`, `x`)."""
    x = re.sub(r"^[0-9]+[a-z]?_", "", f)
    x = re.sub(r"\.md$", "", x)
    if "__" in x:
        a, b = x.split("__", 1)
        return a, b
    return x, ""


_CHAIN_CACHE: dict[str, dict] = {}


def scan_chain_history(git: "Git", tip: str) -> dict:
    """B4 G2 amendment 4 — the chain-id registry: every `id → slug` binding the manifest's
    `## The chain` table ever held on the first-parent history of `tip`, plus each re-bind event
    `(seq, sha, id, first_slug, new_slug)` (a commit whose version binds an id to a slug different
    from that id's first-ever binding — B2 NEW-9, the P23.1–P23.7 reuse). Versions are read
    commit-by-commit (the `git log -p` scan resolved to file state per commit). Cached per
    (repo, tip)."""
    key = f"{git.root}:{tip}"
    if key in _CHAIN_CACHE:
        return _CHAIN_CACHE[key]
    seq = {
        s: i
        for i, s in enumerate(git.text("rev-list", "--first-parent", tip).split())
    }
    commits = git.text(
        "log", "--first-parent", "--reverse", "--format=%H", tip, "--", MANIFEST_REL
    ).split()
    versions: list[tuple[str, dict[str, str]]] = []
    for sha in commits:
        raw = git.show(sha, MANIFEST_REL)
        if raw is None:
            continue
        binds: dict[str, str] = {}
        for _, f in chain_rows(raw.decode("utf-8", "replace").split("\n")):
            tid, slug = chain_idof(f)
            binds.setdefault(tid, slug)
        versions.append((sha, binds))
    first: dict[str, str] = {}
    prev: dict[str, str] = {}
    events: list[tuple[int, str, str, str, str]] = []
    for sha, binds in versions:
        for tid, slug in binds.items():
            if tid not in first:
                first[tid] = slug
            elif first[tid] != slug and prev.get(tid) != slug:
                events.append((seq.get(sha, -1), sha, tid, first[tid], slug))
        prev = binds
    out = {
        "tip": tip,
        "seq": seq,
        "versions": versions,
        "first": first,
        "events": events,
    }
    _CHAIN_CACHE[key] = out
    return out


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
        self._exec_cache: dict[str, tuple[bool, str | None]] = {}
        self._chain_scan: dict | None = None

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
        if self.c.committed:
            # a declared Stage-B seed commit (policy `seed-commit`): the seed round wrote
            # corrections, re-homes and id stamps under its own verifier before the
            # completed modes existed (B4 §6.1) — its append-only findings are sanctioned.
            # The same mechanism covers a later verifier-backed bulk correction commit
            # (P34.18 / ADR-178): the exemption is keyed by the commit each finding is
            # attributed to, so a finding can borrow the exemption only by belonging to a
            # declared commit — never by sitting later in the judged range. The head-commit
            # rule stays for modes where findings carry no attribution.
            head_seed = self.c.head_commit.sha[:8].lower() in self.pol.seed_commits
            self.r.findings = [
                f
                for f in self.r.findings
                if not (
                    f.check == "append-only"
                    and f.severity == "error"
                    and (
                        head_seed
                        or (f.commit and f.commit[:8].lower() in self.pol.seed_commits)
                    )
                )
            ]

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
        if cls == "contract" and not self.executed(path)[0]:
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
                or cls == "runpr"
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
        self.frozen_snapshot(status, path, recs)
        self.judge_policy_dates(path, recs)

    def executed(self, path: str) -> tuple[bool, str | None]:
        """`frozen-after-execution` (B2 §7): a ticket contract is frozen once execution has
        started — when a `runs/<id>.md` ledger or a BUILD_INDEX row already exists at the judged
        base, or a first-parent commit whose subject starts with the ticket id does. Returns
        (executed, start_sha): `start_sha` is the in-range commit whose subject begins execution
        (the one commit that may also fill the contract's `Gate status:` line), None when the
        ticket was already executing at the base."""
        tid = re.sub(r"^[0-9]{2,3}[a-z]?_", "", Path(path).name)
        tid = re.sub(r"__.*$", "", tid)
        tid = re.sub(r"\.md$", "", tid)
        if tid in self._exec_cache:
            return self._exec_cache[tid]
        if self._executed is None:
            ids: set[str] = set()
            for line in (self.c.at_base(INDEX_REL) or "").splitlines():
                if line.startswith("|"):
                    for cell in table_cells(line):
                        c = re.sub(r"[*`]", "", cell).strip().split(" ")[0] if cell.strip() else ""
                        if re.match(r"^[A-Z][A-Z0-9.a-z-]*$", c):
                            ids.add(c)
            self._executed = ids
        begins = re.compile(r"^" + re.escape(tid) + r"(?![\w.])")
        # the start commit is also the one whose subject names the ticket mid-line
        # ("…: P25.4/P25.5 amendments" — b87c279c) — execution subjects are not always prefixed
        mentions = re.compile(r"(?<![\w.])" + re.escape(tid) + r"(?![\w.])")
        at_base = tid in self._executed or self.c.at_base(f"docs/build/runs/{tid}.md") is not None
        if not at_base:
            at_base = any(begins.match(s) for s in self.c.history_subjects())
        start = None
        if not at_base:
            for sha, subj in self.c.range_subjects():
                if begins.match(subj) or mentions.search(subj):
                    start = sha
                    break
            # a ticket whose own first commit is in this range executes from that commit on
            res = (True, start) if start else (False, None)
        else:
            res = (True, None)
        self._exec_cache[tid] = res
        return res

    # -- generic append-only
    def frozen_snapshot(self, status: str, path: str, recs: DiffRecs) -> None:
        """`frozen-snapshot` (B2 §7): a `##`/`###` heading that carries a `(YYYY-MM-DD)` date and
        the word "sweep", "snapshot" or "as of" names a region frozen by the commit that created
        it — no removals and no later additions inside it."""
        if status in ("A", "N", "D") or not (recs.removed or recs.added):
            return
        base_text = self.c.at_base(path)
        if base_text is None:
            return
        snaps = [
            r
            for r in regions(base_text.split("\n"), level=3)
            if SNAPSHOT_HEADING_RE.match(r.heading) and SNAPSHOT_WORD_RE.search(r.heading)
        ]
        if not snaps:
            return
        # a file-scope relocation — the identical line removed and re-added elsewhere in the same
        # diff, or an id-matched row whose old text survives inside the new row (the sanctioned
        # re-homing shape: SEED-15 moved deferral rows to their BL home with an appended
        # annotation) — preserves the row's bytes; it is not a loss or an insertion into the record
        added_norm = {norm(t) for _, _, t in recs.added}
        removed_norm = {norm(t) for _, t in recs.removed}
        added_by_id: dict[str, list[str]] = {}
        for _, _, t in recs.added:
            rid = annotate_id(t)
            if rid:
                added_by_id.setdefault(rid, []).append(t)
        for ln, text in recs.removed:
            reg = next((r for r in snaps if r.start <= ln <= r.end), None)
            if not (reg and text.strip()):
                continue
            if norm(text) in added_norm:
                continue  # verbatim relocation
            rid = annotate_id(text)
            if rid and any(row_contained(text, n) for n in added_by_id.get(rid, [])):
                continue  # row re-homed with an annotation (its text is preserved)
            self.r.v(
                "append-only",
                "frozen-snapshot",
                path,
                ln,
                f"line {ln} removed from frozen snapshot '{reg.heading[:50]}' — a dated "
                "sweep/snapshot never changes after its commit; corrections are appended "
                "(BM-HIST-01, B2 NEW-4)",
                self.c.commit_of_removed(path, text),
            )
        # An append after the tail region's last non-blank base line opens a new section only
        # once the appended block carries its own heading — bare lines added there extend the
        # frozen region and are judged. `ins` is the base line the addition follows; every line
        # in a hunk shares it, so track where the first added heading lands in each group.
        new_section_at: dict[int, int] = {}
        for idx, (hl, ins, text) in enumerate(recs.added):
            if ins not in new_section_at and re.match(r"^#{1,6}\s", text):
                new_section_at[ins] = idx
        for idx, (hl, ins, text) in enumerate(recs.added):
            tail = snaps[-1]
            reg = next(
                (
                    r
                    for r in snaps
                    # the tail snapshot reaches to EOF only when it is the file's last region;
                    # when other sections follow it an EOF append is outside it entirely
                    if (r.start <= ins <= r.lnb if r is not tail else r.start <= ins <= r.end)
                    and not (
                        ins >= r.lnb
                        and r is tail
                        and idx >= new_section_at.get(ins, len(recs.added) + 1)
                    )
                ),
                None,
            )
            if reg and text.strip() and norm(text) not in removed_norm:
                rid = annotate_id(text)
                if rid and any(
                    annotate_id(t2) == rid and row_contained(t2, text)
                    for _, t2 in recs.removed
                ):
                    continue  # a re-homed/annotated row lands inside the region, text preserved
                self.r.v(
                    "append-only",
                    "frozen-snapshot",
                    path,
                    hl,
                    f"line {hl} added inside frozen snapshot '{reg.heading[:50]}' — a dated "
                    "sweep/snapshot never changes after its commit (BM-HIST-01, B2 NEW-4)",
                    self.c.commit_of_added(path, text).short,
                )

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
        added_by_id: dict[str, list[str]] = {}
        for _, _, t in recs.added:
            rid = annotate_id(t)
            if rid:
                added_by_id.setdefault(rid, []).append(t)
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
            if reg and ANNOTATE_REGION_RE.match(reg.heading):
                # `row-annotate` (B2 §7): the id-matched old row's text must survive in the new
                # row; strike-through is transparent. A removed row with no added counterpart is
                # a deletion.
                rid = annotate_id(text)
                if rid and any(row_contained(text, n) for n in added_by_id.get(rid, [])):
                    continue
                self.r.v(
                    "append-only",
                    "row-annotate",
                    path,
                    ln,
                    f"'{hd}' row {rid or '#' + str(ln)} was removed or rewritten — an annotation keeps "
                    "the row's text (strike-through allowed) (BM-HIST-01)",
                    self.c.commit_of_removed(path, text),
                )
                continue
            if (
                reg
                and PHASE_LOG_RE.match(reg.heading)
                and any(
                    fills_placeholder(text, t2, self.pol.placeholders)
                    for _, _, t2 in recs.added
                )
            ):
                continue  # placeholder-fill: a declared token stamped at closeout (B2 §7)
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
                # A contained row-annotation or a declared placeholder fill lands mid-region at
                # the line it annotates — that is the region's own mode, not an insertion.
                span_removed = [
                    t2 for l2, t2 in recs.removed if reg.start <= l2 <= reg.end
                ]
                if ANNOTATE_REGION_RE.match(reg.heading):
                    rid = annotate_id(text)
                    if rid and any(
                        annotate_id(t2) == rid and row_contained(t2, text)
                        for t2 in span_removed
                    ):
                        continue
                if PHASE_LOG_RE.match(reg.heading) and any(
                    fills_placeholder(t2, text, self.pol.placeholders)
                    for t2 in span_removed
                ):
                    continue
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
        # Pre-obligation-ledger commits (before ADR-126's events.jsonl existed): the row's own
        # leading token was the transition mechanism, so a rewrite is the sanctioned legacy
        # shape — the register's four `transition-unjustified` rows are all at/after that
        # commit. A row that disappears entirely is never sanctioned, in any era.
        legacy = self.c.committed and self.c.head_commit.ct < self.c.obligation_epoch()
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
                if legacy and verdict in ("rewritten", "flip-undated"):
                    verdict = "grown"
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
                if t and t not in added_norm and not legacy:
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
                # `placeholder-fill` (B2 §7): a readout's `Disposition:` / `Signed by:` line may
                # trade declared placeholder tokens for real text.
                if re.match(
                    r"^\s*-?\s*(?:\*\*)?\s*(Disposition|Signed by)\s*:", strip_markup(t)
                ) and any(
                    fills_placeholder(t, t2, self.pol.placeholders)
                    for _, _, t2 in recs.added
                ):
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
    def index_fill(
        self, base_lines: list[str], ln: int, old: str, added: list[tuple[int, int, str]]
    ) -> bool:
        """`placeholder-fill` on a BUILD_INDEX row (B2 §7): only the `PR` and `branch` cells of
        the row's table may trade declared placeholder tokens for real text."""
        if not old.startswith("|"):
            return False
        hdr: list[str] | None = None
        for j in range(ln - 1, 0, -1):
            line = base_lines[j - 1]
            if not line.startswith("|"):
                break
            if j < len(base_lines) and is_separator(base_lines[j]):
                hdr = [strip_markup(c).strip().lower() for c in table_cells(line)]
                break
        if not hdr:
            return False
        fill_cols = {k for k, c in enumerate(hdr) if c in ("pr", "branch")}
        if not fill_cols:
            return False
        oc = table_cells(old)
        for _, _, new in added:
            if not new.startswith("|"):
                continue
            nc = table_cells(new)
            if len(oc) != len(nc) or len(oc) != len(hdr):
                continue
            diff = [k for k in range(len(oc)) if oc[k] != nc[k]]
            if diff and all(
                k in fill_cols and fills_placeholder(oc[k], nc[k], self.pol.placeholders)
                for k in diff
            ):
                return True
        return False

    def judge_index(self, status: str, path: str, recs: DiffRecs) -> None:
        base_lines = (self.c.at_base(path) or "").split("\n")
        added_norm = {norm(t) for _, _, t in recs.added}
        for ln, text in recs.removed:
            t = norm(text)
            if not t or t in added_norm:
                continue
            if self.index_fill(base_lines, ln, text, recs.added):
                continue  # placeholder-fill in a pr/branch cell (B2 §7)
            self.r.v(
                "append-only",
                "append-only",
                path,
                ln,
                f"line {ln} removed or rewritten: '{text[:80]}' — BUILD_INDEX is append-only; a "
                "correction is an appended row (BM-INDEX-01)",
                self.c.commit_of_removed(path, text),
            )
        # `append-position`: an index row may land only after its table's last row at base
        # (inserting among existing rows — or growing an existing row — is a rewrite). A line
        # that replaces a removed row by a declared placeholder fill is not an insertion.
        spans = table_spans(base_lines)
        moved = {norm(t) for _, t in recs.removed}
        for hl, ins, text in recs.added:
            if not norm(text) or norm(text) in moved:
                continue
            sp = next((s for s in spans if s[0] <= ins <= s[1]), None)
            if sp and ins < sp[1]:
                span_removed = [t for l2, t in recs.removed if sp[0] <= l2 <= sp[1]]
                if any(fills_placeholder(t2, text, self.pol.placeholders) for t2 in span_removed):
                    continue
                self.r.v(
                    "append-only",
                    "append-position",
                    path,
                    hl,
                    f"line {hl} inserted inside a BUILD_INDEX table (before its last row at base "
                    f"line {sp[1]}) — new rows append at the table end (BM-INDEX-01, BM-HIST-01)",
                    self.c.commit_of_added(path, text).short,
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

    # -- manifest chain-id registry (B4 G2 amendment 4)
    def _chain_data(self) -> dict:
        if self._chain_scan is not None:
            return self._chain_scan
        head = self.c.head if self.c.committed else self.c.base
        # Judging an ancestor of HEAD: scan HEAD once — every version below the head is in it —
        # then bound by first-parent sequence. A head off HEAD's first-parent chain rescans to it.
        real_head = self.c.git.resolve("HEAD") or head
        scan = scan_chain_history(self.c.git, real_head) if real_head else scan_chain_history(
            self.c.git, head
        )
        if self.c.committed and self.c.head not in scan["seq"]:
            scan = scan_chain_history(self.c.git, self.c.head)
        self._chain_scan = scan
        ids = {i for _, b in scan["versions"] for i in b}
        self.r.extra["chain_registry"] = {
            "tip": scan["tip"],
            "ids": len(ids),
            "rebinds": [
                {"commit": e[1][:12], "id": e[2], "first": e[3], "rebound": e[4]}
                for e in scan["events"]
            ],
            "scan": f"git log --first-parent -p {scan['tip'][:12]} -- {MANIFEST_REL}",
        }
        return scan

    def chain_asof(self, rev: str | None) -> dict[str, str]:
        """First-seen `id → slug` bindings among chain versions at or below `rev`'s first-parent
        sequence position (the whole registry when `rev` is off the chain)."""
        scan = self._chain_data()
        limit = scan["seq"].get(rev, 10**9) if rev else 10**9
        first: dict[str, str] = {}
        for sha, binds in scan["versions"]:
            if scan["seq"].get(sha, -1) > limit:
                continue
            for tid, slug in binds.items():
                first.setdefault(tid, slug)
        return first

    def chain_rebind_events(self) -> list[tuple[int, str, str, str, str]]:
        """Re-bind events whose commit is inside the judged range (empty for staged/worktree)."""
        scan = self._chain_data()
        if not self.c.committed:
            return []
        lo = scan["seq"].get(self.c.base or "", -1)
        hi = scan["seq"].get(self.c.head, 10**9)
        return [e for e in scan["events"] if lo < e[0] <= hi]

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

        base_files = {f for _, f, _ in chain(base)}
        # B4 G2 amendment 4 — the chain-id registry covers the whole first-parent history at or
        # below the judged tip, not just the base: an id that ever bound to a slug never re-binds
        # to another (the as-of-head set already contains this diff's own first-time bindings, so
        # they compare equal and pass).
        registry = self.chain_asof(self.c.head if self.c.committed else self.c.base)
        events = self.chain_rebind_events()
        flagged = {(e[2], e[4]) for e in events}
        added = {hl for hl, _, _ in recs.added}
        for i, f, banner in chain(head):
            if i not in added or f in base_files:
                continue
            self.r.count("record-shape", 1, 1)
            tid, slug = chain_idof(f)
            if tid in registry and registry[tid] != slug and (tid, slug) not in flagged:
                self.r.v(
                    "record-shape",
                    "id-registry",
                    path,
                    i,
                    f"chain id {tid} re-bound from slug '{registry[tid]}' to '{slug}' — an id never binds to another "
                    "file (BM-MANIFEST-03, B2 NEW-9)",
                )
            if not re.match(r"^###\s+Round\s+[0-9]+", banner):
                self.r.v(
                    "record-shape",
                    "round-banner",
                    path,
                    i,
                    f"new chain row {f} is not under a numbered '### Round <n>' banner (BM-MANIFEST-01, V13)",
                )
        for _seq, sha, tid, first, slug in events:
            self.r.v(
                "record-shape",
                "id-registry",
                path,
                0,
                f"chain id {tid} re-bound from slug '{first}' to '{slug}' in {sha[:12]} — an id "
                "that ever appeared in the chain table never binds to another file "
                "(BM-MANIFEST-03, B2 NEW-9)",
                sha[:12],
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
        _, start = self.executed(path)
        # In the executing ticket's first commit the `Gate status:` block may be filled with the
        # operator's answers (B2 §7 — the contract itself instructs: "copy them into this block in
        # your first commit"). The block is the `Gate status:` bullet plus its indented
        # continuation; edits inside it, attributed to the start commit, are the transition.
        base_lines = (self.c.at_base(path) or "").split("\n")
        gs = gate_status_span(base_lines)

        def at_start(commit_sha: str) -> bool:
            return bool(start) and commit_sha == start

        added_norm = {norm(t) for _, _, t in recs.added}
        for ln, text in recs.removed:
            t = norm(text)
            if not t or t in added_norm:
                continue
            if (
                gs
                and gs[0] <= ln <= gs[1]
                and at_start(
                    self.c.removed_by.get((path, text), self.c.head_commit).sha
                )
            ):
                continue
            self.r.v(
                "append-only",
                "frozen",
                path,
                ln,
                f"line {ln} removed or rewritten — an executed contract is frozen; amend it with an "
                "appended '> Amended <date -u +%F>:' note (BM-TICKET-04)",
                self.c.commit_of_removed(path, text),
            )
        lastnb = last_nonblank(self.c.at_base(path) or "")
        for hl, ins, text in recs.added:
            if ins < lastnb and not (
                gs
                and gs[0] <= ins <= gs[1]
                and at_start(self.c.added_by.get((path, text), self.c.head_commit).sha)
            ):
                self.r.v(
                    "append-only",
                    "append-position",
                    path,
                    hl,
                    f"line {hl} inserted before the end of a frozen/append-only file — append at EOF "
                    "(BM-HIST-01)",
                    self.c.commit_of_added(path, text).short,
                )
                continue
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
        is removed or changed, and additions are allowed only (a) at EOF as a `## Status updates` or
        `## Clarification` section (appended record, never a rewrite — BM-ADR-01), and (b) as
        `### Trigger evaluation …` subsections at the end of `## Revisit trigger` (or at EOF when that
        section is last). A removal is allowed only when the new line differs by declared placeholder
        tokens alone (`placeholder-fill`; the Stage-B `DRAFT-*` id-map fills land this way)."""
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
            if any(
                fills_placeholder(text, t2, self.pol.placeholders)
                for _, _, t2 in recs.added
            ):
                continue  # placeholder-fill: a declared token stamped with its real value (B2 §7)
            self.r.v(
                "append-only",
                "frozen",
                path,
                ln,
                f"line {ln} removed or rewritten ('{text[:60]}') — a landed ADR is frozen; only an appended "
                "`## Status updates`/`## Clarification` section or a `### Trigger evaluation` subsection at "
                "the end of `## Revisit trigger` is allowed (BM-ADR-01, SIG-ENG-003)",
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
            in_status = bool(
                re.match(r"^##\s+(Status updates|Clarification)\b", sec_h, re.I)
            )
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
            # The byte prefix may change only where every removed line is a declared placeholder
            # fill (e.g. `PENDING-COMMIT-SHA` stamped with the landed sha at closeout).
            unfilled = [
                (ln, t)
                for ln, t in recs.removed
                if norm(t)
                and not any(
                    fills_placeholder(t, n, self.pol.placeholders) for _, _, n in recs.added
                )
            ]
            if unfilled:
                self.r.v(
                    "append-only",
                    "prefix",
                    path,
                    unfilled[0][0],
                    f"{path} no longer starts with its previous {len(base)} bytes (first un-filled "
                    f"line {unfilled[0][0]}: '{unfilled[0][1][:60]}') — a .jsonl record file only "
                    "appends; a mid-file line may change only to fill a declared placeholder "
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
            if path.startswith(OBLIGATIONS_PREFIX):
                continue
            if text.strip():
                try:
                    json.loads(text)
                except (json.JSONDecodeError, ValueError) as exc:
                    self.r.v(
                        "append-only",
                        "schema",
                        path,
                        hl,
                        f"appended .jsonl line is not valid JSON ({exc}) (BM-HIST-01)",
                        self.c.commit_of_added(path, text).short,
                    )
        if path.startswith(OBLIGATIONS_PREFIX):
            self.judge_obligations(path, status, recs)

    def judge_obligations(self, path: str, status: str, recs: DiffRecs) -> None:
        """`prefix` obligations-ledger checks on appended lines (B2 §7): valid schema
        (`obligation-event/1` or `coverage-assessment/1`) and an event chains to the
        obligation's last event via `expected_previous_event`."""
        last: dict[str, str] = {}
        known: set[str] = set()
        old_event_at_line: list[str | None] = []  # 1-indexed file line → event/record id
        for ln in (self.c.at_base(path) or "").splitlines():
            old_event_at_line.append(None)
            if not ln.strip():
                continue
            try:
                obj = json.loads(ln)
            except (json.JSONDecodeError, ValueError):
                continue  # pre-schema history is opaque; only appended lines are judged
            if isinstance(obj.get("event_id") or obj.get("assessment_id"), str):
                old_event_at_line[-1] = obj.get("event_id") or obj.get("assessment_id")
            if (
                obj.get("schema") == EVENT_SCHEMA
                and isinstance(obj.get("obligation_id"), str)
                and isinstance(obj.get("event_id"), str)
            ):
                known.add(obj["event_id"])
                if obj.get("kind") != "correction":
                    # a correction is an annotation, never a chain link (P34.8)
                    last[obj["obligation_id"]] = obj["event_id"]
        seen_oids = set(last)
        for hl, _, text in recs.added:
            if not text.strip():
                continue
            commit = self.c.commit_of_added(path, text).short
            try:
                obj = json.loads(text)
            except (json.JSONDecodeError, ValueError) as exc:
                self.r.v(
                    "append-only",
                    "schema",
                    path,
                    hl,
                    f"appended obligation-ledger line is not valid JSON ({exc}) (BM-HIST-01)",
                    commit,
                )
                continue
            schema = obj.get("schema")
            if schema == EVENT_SCHEMA:
                missing = [k for k in EVENT_FIELDS if k not in obj]
                if missing:
                    self.r.v(
                        "append-only",
                        "schema",
                        path,
                        hl,
                        f"appended obligation-event is missing field(s) {', '.join(missing)} "
                        f"({EVENT_SCHEMA})",
                        commit,
                    )
                    continue
                kind = obj["kind"]
                if kind not in EVENT_KINDS:
                    self.r.v(
                        "append-only",
                        "schema",
                        path,
                        hl,
                        f"obligation-event kind {kind!r} not in {sorted(EVENT_KINDS)}",
                        commit,
                    )
                for s in ("from_status", "to_status"):
                    # a correction moves no status — `—` is the honest pair
                    if obj[s] not in OBLIGATION_STATUSES and not (
                        kind == "correction" and obj[s] == "—"
                    ):
                        self.r.v(
                            "append-only",
                            "schema",
                            path,
                            hl,
                            f"obligation-event {s} {obj[s]!r} is not a valid status "
                            f"({'|'.join(sorted(OBLIGATION_STATUSES))})",
                            commit,
                        )
                if not isinstance(obj["seq"], int) or obj["seq"] < 0:
                    self.r.v(
                        "append-only",
                        "schema",
                        path,
                        hl,
                        "obligation-event seq must be a non-negative integer",
                        commit,
                    )
                oid, eid = obj["obligation_id"], obj["event_id"]
                epe = obj["expected_previous_event"]
                if kind == "correction":
                    # a correction is an annotation — it repairs a named record and
                    # never becomes a chain link (P34.8)
                    corr = obj.get("correction")
                    if not isinstance(corr, dict) or not isinstance(
                        corr.get("file"), str
                    ):
                        self.r.v(
                            "append-only",
                            "schema",
                            path,
                            hl,
                            f"correction {eid!r} carries no correction block naming the "
                            "file/record it repairs",
                            commit,
                        )
                    elif corr.get("file") == path:
                        tgt_line = corr.get("line")
                        tgt_eid = corr.get("event_id")
                        if epe != tgt_eid:
                            self.r.v(
                                "append-only",
                                "chain",
                                path,
                                hl,
                                f"correction {eid!r} of a {path} record must carry "
                                f"expected_previous_event == the corrected event "
                                f"{tgt_eid!r}, got {epe!r}",
                                commit,
                            )
                        if isinstance(tgt_line, int) and tgt_eid in known:
                            idx = tgt_line - 1
                            if not (
                                0 <= idx < len(old_event_at_line)
                                and old_event_at_line[idx] == tgt_eid
                            ):
                                self.r.v(
                                    "append-only",
                                    "chain",
                                    path,
                                    hl,
                                    f"correction {eid!r} names {path} line {tgt_line} but "
                                    f"that line is not {tgt_eid!r}",
                                    commit,
                                )
                    elif not str(corr.get("file")).startswith(OBLIGATIONS_PREFIX):
                        self.r.v(
                            "append-only",
                            "schema",
                            path,
                            hl,
                            f"correction {eid!r} names file {corr.get('file')!r} which is "
                            f"not an obligations-ledger record ({OBLIGATIONS_PREFIX}*)",
                            commit,
                        )
                elif kind == "migration":
                    if epe is not None:
                        self.r.v(
                            "append-only",
                            "chain",
                            path,
                            hl,
                            "a migration anchor must have expected_previous_event=null",
                            commit,
                        )
                    elif oid in seen_oids:
                        self.r.v(
                            "append-only",
                            "chain",
                            path,
                            hl,
                            f"migration {eid!r} re-anchors {oid}, which already has events — a "
                            "status change is a `transition` chained on the last event",
                            commit,
                        )
                elif kind == "transition":
                    if epe is None:
                        self.r.v(
                            "append-only",
                            "chain",
                            path,
                            hl,
                            f"transition {eid!r} must name expected_previous_event — it chains "
                            "on the obligation's last event",
                            commit,
                        )
                    elif oid in last and epe != last[oid]:
                        self.r.v(
                            "append-only",
                            "chain",
                            path,
                            hl,
                            f"transition {eid!r} expects {epe!r} but {oid}'s last event is "
                            f"{last[oid]!r} — the chain must point at the obligation's last event",
                            commit,
                        )
                    elif oid not in last and epe not in known:
                        self.r.v(
                            "append-only",
                            "chain",
                            path,
                            hl,
                            f"transition {eid!r} names expected_previous_event {epe!r}, which is "
                            "not an event in this ledger",
                            commit,
                        )
                if isinstance(eid, str):
                    known.add(eid)
                    if kind != "correction":
                        # corrections annotate, they do not move the chain head
                        last[oid] = eid
                        seen_oids.add(oid)
            elif schema == ASSESSMENT_SCHEMA:
                missing = [k for k in ASSESSMENT_FIELDS if k not in obj]
                if missing:
                    self.r.v(
                        "append-only",
                        "schema",
                        path,
                        hl,
                        f"appended coverage-assessment is missing field(s) {', '.join(missing)} "
                        f"({ASSESSMENT_SCHEMA})",
                        commit,
                    )
            else:
                self.r.v(
                    "append-only",
                    "schema",
                    path,
                    hl,
                    f"appended obligation-ledger record has schema {schema!r} — expected "
                    f"{EVENT_SCHEMA!r} or {ASSESSMENT_SCHEMA!r}",
                    commit,
                )

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
        # `frozen-after-close` (B2 §7): a run ledger whose header carries a dated `Closed:` stamp
        # takes only declared placeholder fills and appended `## Correction` sections.
        closed = (
            status != "N" and "/runs/" in path and run_ledger_closed(self.c.at_base(path) or "")
        )
        if status not in ("A", "N", "D") and not closed:
            # an OPEN run/pr ledger is already an append-only record (B2 §7): removals pass only
            # through the sanctioned modes — a placeholder fill, a verbatim relocation, or a row
            # rewrite that keeps every old cell's text (row-annotate) — and additions go at EOF.
            # The stricter `frozen-after-close` rule below binds once `Closed:` is stamped.
            base_text = self.c.at_base(path) or ""
            hdr_end = header_end_line(base_text.split("\n"))
            added_norm = {norm(t) for _, _, t in recs.added}
            for ln, text in recs.removed:
                t = norm(text)
                if not t or t in added_norm:
                    continue
                if any(
                    fills_placeholder(text, t2, self.pol.placeholders)
                    for _, _, t2 in recs.added
                ):
                    continue
                # the sanctioned close/stamp fill: a header stamp line (`- **Closed:** none.`)
                # is rewritten only to stamp its own label with a date — the stamp itself is
                # date-checked by the G1 rules
                label = stamp_label(text)
                if ln <= hdr_end and label and any(
                    stamp_label(t2) == label and DATE_RE.search(t2)
                    for _, _, t2 in recs.added
                ):
                    continue
                if any(row_contained(text, t2) for _, _, t2 in recs.added):
                    continue
                self.r.v(
                    "append-only",
                    "append-only",
                    path,
                    ln,
                    f"line {ln} removed or rewritten: '{text[:80]}' — a run ledger is append-only "
                    "from its first commit; the gate-status/placeholder fills are the sanctioned "
                    "in-place edits, later facts are appended (BM-HIST-01, BM-INDEX-02)",
                    self.c.commit_of_removed(path, text),
                )
            # additions in an open ledger are not position-judged: a live run fills its sections
            # (the "## …" results the next leg produces) wherever they sit — the strict
            # EOF-position rule belongs to the frozen/closed modes (register: every runs/ loss
            # row is a removal; B4's position scan covers LEDGER only).
        if closed:
            base_text = self.c.at_base(path) or ""
            head_lines = (self.c.at_head(path) or "").split("\n")
            hregs = regions(head_lines)
            added_norm = {norm(t) for _, _, t in recs.added}
            for ln, text in recs.removed:
                t = norm(text)
                if not t or t in added_norm:
                    continue
                if any(
                    fills_placeholder(text, t2, self.pol.placeholders)
                    for _, _, t2 in recs.added
                ):
                    continue
                self.r.v(
                    "append-only",
                    "append-only",
                    path,
                    ln,
                    f"line {ln} removed or rewritten: '{text[:80]}' — a closed run ledger takes "
                    "only placeholder fills and appended '## Correction' sections; a later fact "
                    "is an appended dated note (BM-INDEX-02)",
                    self.c.commit_of_removed(path, text),
                )
            lastnb = last_nonblank(base_text)
            for hl, ins, text in recs.added:
                # a declared placeholder fill lands at the removed line's position — that is the
                # fill itself, wherever it sits in the file (including the last line)
                if text.strip() and any(
                    fills_placeholder(t, text, self.pol.placeholders)
                    for _, t in recs.removed
                ):
                    continue
                if ins < lastnb:
                    self.r.v(
                        "append-only",
                        "append-position",
                        path,
                        hl,
                        f"line {hl} inserted inside a closed run ledger — appends go at EOF "
                        "(BM-INDEX-02, BM-HIST-01)",
                        self.c.commit_of_added(path, text).short,
                    )
                    continue
                if not text.strip():
                    continue
                sec = region_at(hregs, hl)
                if not (sec and CORRECTION_HEADING_RE.match(sec.heading)):
                    self.r.v(
                        "append-only",
                        "frozen-after-close",
                        path,
                        hl,
                        f"appended line {hl} is not under a '## Correction' heading — a closed "
                        "run ledger grows only by correction sections (BM-INDEX-02)",
                        self.c.commit_of_added(path, text).short,
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


def stamp_label(text: str) -> str:
    """The stamp field a `STAMP_RE` line carries ('closed', 'landed', …) — '' for non-stamps.
    A header stamp line may be rewritten only to stamp the same field with a date (the
    sanctioned close/land fill); a same-label check keeps `Closed:` from passing for `Landed:`."""
    m = STAMP_RE.match(text)
    return m[3].lower() if m else ""


def header_end_line(lines: list[str]) -> int:
    """The first `##` heading's line number (the header block lies before it)."""
    return next((i for i, ln in enumerate(lines, 1) if re.match(r"^##\s", ln)), len(lines) + 1)


def run_ledger_closed(text: str) -> bool:
    """A run ledger is closed when its header carries a dated `Closed:` stamp. A `Closed:` line
    still holding a declared blank (`Closed: 2026-10-02T__CLOSED__`) is mid-close, not closed —
    the closeout commit itself may fill it without tripping `frozen-after-close`."""
    lines = text.split("\n")
    end = header_end_line(lines)
    return any(
        re.match(r"^\s*(-\s*)?(\*\*)?Closed(\*\*)?:", ln)
        and DATE_RE.search(ln)
        and not BLANK_PH_RE.search(ln)
        for ln in lines[: end - 1]
    )


def gate_status_span(lines: list[str]) -> tuple[int, int] | None:
    """1-based [first, last] span of a ticket's `Gate status:` block — the bullet line plus its
    indented continuation lines (answers copied into the block fill it whole, sub-bullets and
    all). None when the ticket has no `Gate status:` line."""
    for i, line in enumerate(lines):
        if not GATE_STATUS_RE.match(line):
            continue
        ind = len(line) - len(line.lstrip())
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if nxt.strip() and len(nxt) - len(nxt.lstrip()) <= ind:
                break
            j += 1
        return (i + 1, j)
    return None


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


def _ph_pattern(token: str) -> str:
    """The regex a declared placeholder token compiles to; `______` is the blank convention —
    any run of ≥ 3 underscores, or a labelled blank like `__CLOSED__`. A token written
    `re:<ERE>` is a declared token family (e.g. the Stage-B `DRAFT-MEM-1` ids that SEED-12
    stamped with their final SIG-MEM-* ids — a fill, not a rewrite)."""
    if token == BLANK_PLACEHOLDER:
        return BLANK_PH_RE.pattern
    if token.startswith("re:"):
        return "(?:" + token[3:] + ")"
    return re.escape(token)


def fills_placeholder(old: str, new: str, tokens: list[str]) -> bool:
    """`new` is `old` with only declared placeholder tokens replaced by real (non-empty) text —
    B2 §7 `placeholder-fill`. Every other byte must match exactly."""
    if not tokens or not old.strip() or old == new:
        return False
    rx = re.compile("|".join(_ph_pattern(t) for t in tokens))
    pat: list[str] = []
    pos = 0
    seen = False
    for m in rx.finditer(old):
        seen = True
        pat.append(re.escape(old[pos : m.start()]))
        pat.append(r".+")
        pos = m.end()
    if not seen:
        return False
    pat.append(re.escape(old[pos:]))
    return re.fullmatch("".join(pat), new) is not None


def annotate_id(text: str) -> str:
    """The row id an annotation must preserve: the first cell of a table row, or the first bold
    token of an OPEN FINDINGS-style bullet; "" when the line is not an addressable row."""
    if text.startswith("|"):
        cells = table_cells(text)
        return strip_markup(cells[0]).strip() if cells else ""
    m = re.match(r"^\s*-\s*\*\*([A-Za-z0-9_.-]+)", text)
    return m[1] if m else ""


def row_contained(old: str, new: str) -> bool:
    """`row-annotate` containment: every cell's text of a table row survives in the matching
    cell of the new row; a bullet's whole text survives in the new bullet. Strike-through
    (`~~…~~`) and emphasis markup are transparent."""

    def nz(x: str) -> str:
        x = re.sub(r"~~", "", x)
        x = re.sub(r"[*`]", "", x)
        return re.sub(r"\s+", " ", x).strip()

    if old.startswith("|"):
        oc, nc = table_cells(old), table_cells(new)
        if len(oc) > len(nc):
            return False
        return all(nz(oc[i]) in nz(nc[i]) for i in range(len(oc)))
    return nz(old) in nz(new)


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
        "extra": report.extra,
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


def judge_change(
    root: Path, git: "Git", mode: str, arg: str, now: int
) -> tuple["Change", "Policy", bool, Report]:
    """Judge one diff (`mode` ∈ range|first-parent|staged|worktree) and return the report —
    `cmd_change` and `cmd_replay` share this so a replayed commit is judged exactly like a live one."""
    change = Change(git, mode, arg, now)
    guards, policy = preflight(root, git, change.head if change.committed else None)
    if change.committed:
        # `seed-commit` lines declare *past* commits: they exist only in the checkout's
        # policy, so a replay judged under the historical policy must still see them
        # (the policy in force otherwise governs — a change may amend it).
        raw_wt = (root / POLICY_REL).read_bytes() if (root / POLICY_REL).is_file() else None
        if raw_wt is not None:
            policy.seed_commits |= Policy.parse(raw_wt).seed_commits
    report = Report()
    for e in policy.errors:
        report.v("append-only", "policy", POLICY_REL, 0, f"policy error: {e}")
    Judge(change, policy, report, guards).run()
    return change, policy, guards, report


def cmd_change(args: argparse.Namespace) -> int:
    root = repo_root(args.repo)
    git = Git(root)
    now = parse_now(args.now)
    modes = [m for m in ("range", "first_parent", "staged", "worktree") if getattr(args, m)]
    if len(modes) != 1:
        raise UsageError("give exactly one of --range, --first-parent, --staged, --worktree")
    mode = modes[0].replace("_", "-")
    arg = getattr(args, modes[0])
    change, policy, guards, report = judge_change(
        root, git, mode, arg if isinstance(arg, str) else "", now
    )
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


# ── replay oracle (B4 §G2; P34.7) ─────────────────────────────────────────────
#
# `tests/unit/fixtures/memory_guard/replay_expected.csv` is the committed expected set for the
# nightly whole-history replay: one row per expected `(commit, path, check)` cell, derived from
# the B1/B2 registers and B4's position scan by `memory_guard.py oracle-gen` — never hand-copied
# counts (OM-15). `source` says where a row came from; `reviewed` rows are the hand-review channel
# for disagreements (B4: a disagreement is reviewed before the oracle changes — adding a reviewed
# row is the recorded act of review, never a silent re-baseline).

ORACLE_REL = "tests/unit/fixtures/memory_guard/replay_expected.csv"
APPEND_REGISTER_REL = "docs/build/reports/memory-repair/append_only_register.csv"
# `waived` is the review artifact (B4: "a disagreement is reviewed by hand before the oracle
# changes, never silently re-baselined"): it withdraws the derived row matching it on
# (commit, path, check-or-*), and its note records who adjudicated what and why. The derived
# row stays in the file beside it — the register's claim and the review are both visible.
ORACLE_KINDS = ("violation", "clean", "waived")


@dataclass(frozen=True)
class OracleRow:
    kind: str  # violation | clean
    commit: str  # 8-char prefix
    path: str
    check: str
    rule: str  # subrule, or '*' for any rule of the check
    source: str
    note: str


def load_oracle(path: str | Path) -> list[OracleRow]:
    rows: list[OracleRow] = []
    for i, rec in enumerate(csv.DictReader(open(path, newline="", encoding="utf-8")), 2):
        kind = (rec.get("kind") or "").strip()
        if kind not in ORACLE_KINDS:
            raise UsageError(f"{path}:{i}: kind must be one of {ORACLE_KINDS}")
        rows.append(
            OracleRow(
                kind,
                (rec.get("commit") or "").strip(),
                (rec.get("path") or "").strip(),
                (rec.get("check") or "").strip(),
                (rec.get("rule") or "*").strip() or "*",
                (rec.get("source") or "").strip(),
                (rec.get("note") or "").strip(),
            )
        )
    if not rows:
        raise UsageError(f"{path}: oracle holds no rows — a vacuous oracle is not a check")
    return rows


def _oracle_hit(row: OracleRow, commit8: str, path: str, check: str, rule: str) -> bool:
    return (
        row.commit == commit8
        and row.path == path
        and (row.check == "*" or row.check == check)
        and (row.rule == "*" or row.rule == rule)
    )


def oracle_compare(
    git: "Git",
    span: str,
    commits: list[str],
    oracle: list[OracleRow],
    findings: list[Finding],
) -> tuple[int, dict[str, list]]:
    """Set-equality between the replay's error findings and the committed oracle.

    - every `violation` row must be matched by a finding (a register positive may not be missed);
    - every finding must be covered by a `violation` row (a benign row or an uncovered commit may
      not be flagged);
    - every `clean` row forbids findings of that check on that (commit, path) cell.

    Returns (exit_code, {missing, unexpected, clean-breached}).
    """
    span8 = {c[:8] for c in commits}
    actual = {(f.commit[:8], f.path, f.check, f.rule) for f in findings}
    waivers = [
        r
        for r in oracle
        if r.kind == "waived" and r.commit in span8 and r.source == "reviewed"
    ]

    def waived(row: OracleRow) -> bool:
        # a waiver withdraws *derived* rows only — a reviewed row is itself the adjudication
        return row.source != "reviewed" and any(
            w.commit == row.commit
            and w.path == row.path
            and (w.check == "*" or w.check == row.check)
            for w in waivers
        )

    missing, unexpected, breached = [], [], []
    n_waived = 0
    for row in oracle:
        if row.commit not in span8 or row.kind == "waived":
            continue  # the row names a commit outside this replay's span — not owed here
        if waived(row):
            # a hand-reviewed withdrawal — the register's claim and the adjudication are
            # both on file; it is neither expected nor asserted clean
            n_waived += 1
            continue
        if row.kind == "violation":
            if not any(_oracle_hit(row, *a) for a in actual):
                missing.append(row)
        elif row.kind == "clean":
            if any(a[0] == row.commit and a[1] == row.path and a[2] == row.check for a in actual):
                breached.append(row)
    for a in sorted(actual):
        if not any(
            r.kind == "violation" and not waived(r) and _oracle_hit(r, *a) for r in oracle
        ):
            unexpected.append(a)
    for row in missing:
        print(
            f"  oracle-miss: {row.commit} {row.path} {row.check}[{row.rule}] expected "
            f"({row.source}{': ' + row.note[:80] if row.note else ''}) but not flagged"
        )
    for row in breached:
        print(
            f"  oracle-breach: {row.commit} {row.path} {row.check} expected clean "
            f"({row.source}{': ' + row.note[:80] if row.note else ''}) but flagged"
        )
    for c8, path, check, rule in unexpected:
        print(f"  oracle-unexpected: {c8} {path} {check}[{rule}] flagged but not expected")
    print(
        f"oracle: {sum(1 for r in oracle if r.kind == 'violation')} expected violation cell(s), "
        f"{sum(1 for r in oracle if r.kind == 'clean')} clean cell(s); {len(actual)} actual "
        f"finding cell(s); {len(missing)} missed, {len(breached)} breached, "
        f"{len(unexpected)} unexpected, {n_waived} reviewed-waived"
    )
    rc = EXIT_VIOLATIONS if (missing or breached or unexpected) else EXIT_OK
    return rc, {
        "missing": [
            {"commit": r.commit, "path": r.path, "check": r.check, "rule": r.rule, "source": r.source}
            for r in missing
        ],
        "unexpected": [
            {"commit": c8, "path": p, "check": ch, "rule": ru} for c8, p, ch, ru in unexpected
        ],
        "clean-breached": [
            {"commit": r.commit, "path": r.path, "check": r.check, "source": r.source}
            for r in breached
        ],
    }


def register_commit_map(git: "Git", wanted: set[str], commits: list[str]) -> dict[str, str]:
    """Map each wanted register commit (8-char prefix) to the first-parent commit of `commits`
    that carries it: itself, or the earliest merge on the first-parent path that contains it."""
    in_span = {c[:8] for c in commits}
    out: dict[str, str] = {}
    tip = commits[-1] if commits else "HEAD"
    for w in wanted:
        if w in in_span:
            out[w] = w
            continue
        merges = git.text(
            "rev-list", "--first-parent", "--merges", "--ancestry-path", f"{w}..{tip}"
        ).split()
        if merges:
            out[w] = merges[-1][:8]  # rev-list is newest-first; the earliest merge is last
        else:
            out[w] = w  # no carrier — the row stays at its own commit and reports as missed
    return out


# class-b note kinds naming a position no record-dates rule can ever judge — release-identity
# strings inside release artifacts, generated artifacts, code constants, fixture pins, and
# planning notes. (Event dates, anchor dates and chain-stale dates are *position* dependent —
# they are decided by the line simulation in `date_row_visible`, not by kind.)
DATE_INVISIBLE_KINDS = re.compile(
    r"[ab]:(planning-stamp|anchor-date|scheduled-date|unsigned-slot"
    r"|release-identity|generated-artifact|code-constant|fixture-pin"
    # sqitch planned_at rows are the C-10 allow-listed future stamps — the keyed `allow`
    # entries are how they pass, so they are not expected violations
    r"|sqitch-planned)"
)


def _collected_stamps(
    line: str, path: str, region: str | None, pol: "Policy"
) -> set[tuple[str, str]]:
    """The (stamp, class) pairs the judge would collect from `line` on `path` — the position
    test a register row must pass to be an expected violation. Mirrors the add_date
    collectors: header/status stamps (`STAMP_RE`), `updatedAt:` scalars, list bullets led by
    a date inside LEDGER's PHASE LOG / GATE DECISIONS regions, first-cell dates of LEDGER
    tables, pure-date cells of BUILD_INDEX rows, DEFERRALS status dates, readout
    Date/Signed/Confirm lines, manifest date-led items, policy `date` positions, and dated
    fields of `.jsonl` records."""
    out: set[tuple[str, str]] = set()

    def first(pat: str, s: str, cls: str) -> None:
        m = re.match(pat, s)
        if m:
            out.add((m[1], cls))

    if STAMP_RE.match(line):
        m = DATE_RE.search(line)
        if m:
            out.add((m[0], "act"))
    first(r"^\s*updatedAt:\s*(" + DATE_RE.pattern + r")", line, "act")
    if line.lstrip().startswith("- "):
        if region and re.search(r"PHASE LOG|GATE DECISIONS", region):
            first(r"^-\s*(" + DATE_RE.pattern + r")", strip_markup(line), "act")
    if line.startswith("|"):
        cells = table_cells(line)
        if cells:
            if path == LEDGER_REL:
                # GATE DECISIONS-style tables: the first cell is the row's stamp
                m = DATE_RE.search(cells[0])
                if m:
                    out.add((m[0], "act"))
            elif path == INDEX_REL:
                # the `landed` cell is a bare date — a cell that is only a date is a stamp
                for c in cells[1:]:
                    if re.fullmatch(DATE_RE.pattern + r"\s*", c.strip()):
                        out.add((c.strip(), "act"))
    if path.endswith("DEFERRALS.md"):
        out.update((d, "act") for d in status_dates(line))
    if path.startswith("docs/build/readouts/") and re.search(
        r"(^|[^A-Za-z])(Date|[Rr]eceived|[Ss]igned|[Cc]onfirm)", line
    ):
        out.update((m[0], "act") for m in DATE_RE.finditer(line))
    if path.endswith("00_MANIFEST.md"):
        first(r"^[-|][\s|*]*(" + DATE_RE.pattern + r")", line, "act")
    for g, rx in pol.dates:
        if fnmatch.fnmatchcase(path, g) and rx.search(line):
            m = DATE_RE.search(line)
            if m:
                # act-when records are acts only when the same diff flips them — the
                # simulator cannot see the flip, so treat the position as act-capable
                out.add((m[0], "act"))
    if path.endswith(".jsonl") and line.strip().startswith("{"):
        for k, v in re.findall(r'"([^"]+)"\s*:\s*"([^"]*)"', line):
            if re.search(r"date|stamp|recorded|_at|time", k, re.I):
                for m in DATE_RE.finditer(v):
                    out.add((m[0], "act"))
    return out


def date_row_visible(
    row: dict[str, str],
    pol: "Policy",
    added: dict[tuple[str, str], tuple[list[tuple[int, str]], str | None]],
    git: "Git",
) -> bool:
    """Whether a class-b `date_corrections.csv` row names a stamp the replay can flag: the
    recorded value must appear as a *collected* stamp on a line the introducing commit added
    to that path, and it must actually violate under the judge's own rules — R1 (later than
    its commit, barring `future-ok:`/`allow`/correction-context), or on an act position R2
    (back-dated >48 h without a retro/as-of/strict-correction marker). A wrong-but-plausible
    event date, a stamp on an unjudged position, or one the judge's suppression rules
    legitimately absorb is invisible to a diff-scoped checker — expecting it would be a
    manufactured miss."""
    if row.get("class") != "b":
        return False
    if DATE_INVISIBLE_KINDS.match(row.get("note", "")):
        return False
    path = row.get("path", "")
    if not _in_scope_path(path):
        return False
    m = DATE_RE.search(row.get("recorded_value", ""))
    if not m:
        return False
    want = m[0][:10]
    c8 = row.get("introducing_commit", "")[:8]
    info = _commit_info(git, c8)
    if info is None:
        return False
    key = (c8, path)
    if key not in added:
        added[key] = _commit_diff(git, c8, path)
    pairs, base_text = added[key]
    regs = regions(base_text.split("\n")) if base_text is not None else []
    # the policy in force where the line was written governs its collection and its
    # `allow`/`future-ok:` exemptions (fall back to the checkout's policy)
    raw_pol = git.show(c8, POLICY_REL)
    pol_c = Policy.parse(raw_pol) if raw_pol is not None else pol
    now = int(dt.datetime.now(dt.UTC).timestamp())
    for ins, line in pairs:
        reg = next((r for r in regs if r.start <= ins <= r.end), None)
        for st_text, cls in _collected_stamps(
            line, path, reg.heading if reg else None, pol_c
        ):
            if st_text[:10] != want:
                continue
            st = parse_stamp(st_text)
            if st is None or st.malformed:
                return True  # an unparseable collected stamp is an R1 finding by itself
            exempt, _ = r1_exempt(pol_c, path, line, st, now)
            if (
                not exempt
                and not r1_ok(st, info, now)
                and not correction_context(line, st, info, now)
            ):
                return True
            if (
                cls == "act"
                and not any(mk in line for mk in R2_MARKERS)
                and not strict_correction(line, st)
                and not r2_ok(st, info)
            ):
                return True
    return False


def _commit_info(git: "Git", c8: str) -> "CommitInfo | None":
    """The introducing commit's CommitInfo (sha/committer time) for the visibility test —
    the register's `commit_date_utc` column is UTC-only, and R1/R2 need the committer's
    local date too."""
    try:
        out = git.text("show", "-s", "--format=%H%n%ct%n%cI", c8).split("\n")
        return CommitInfo(out[0].strip(), int(out[1]), out[2].strip())
    except Exception:
        return None


def _commit_diff(
    git: "Git", c8: str, path: str
) -> tuple[list[tuple[int, str]], str | None]:
    """((ins, text) of each `+` line, base file text) for `path` at commit `c8`. `ins` is the
    base line the addition follows — the region anchor. The introducing commit may live off
    first-parent (a landed branch), so its own diff — not the merge carrier's — is the
    position evidence."""
    try:
        full = git.text("rev-parse", "--verify", "-q", c8 + "^{commit}").strip()
        if not full:
            return [], None
        parent = git.text("rev-parse", "--verify", "-q", full + "^").strip()
        base = git.show(parent, path) if parent else None
        base_text = base.decode("utf-8", "replace") if base is not None else None
        if parent:
            diff = git.text("diff", "-U0", parent, full, "--", path)
        else:
            diff = git.text("show", "--format=", full, "--", path)
    except Exception:
        return [], None
    pairs: list[tuple[int, str]] = []
    consumed = 0
    for ln in diff.splitlines():
        if ln.startswith("@@"):
            m = HUNK_RE.match(ln)
            if m:
                consumed = int(m[1]) - 1
                if m[2] == "0":
                    consumed = int(m[1])
        elif ln.startswith("-") and not ln.startswith("---"):
            consumed += 1
        elif ln.startswith("+") and not ln.startswith("+++"):
            pairs.append((consumed, ln[1:]))
    return pairs, base_text


def _in_scope_path(path: str) -> bool:
    """The build-memory scope the date judge sees: docs/build, docs/tickets, docs/adr plus the
    out-of-tree policy `date` records (sqitch.plan, sources.toml, flake_log)."""
    if path.startswith(("docs/build/", "docs/tickets/", "docs/adr/")):
        return True
    return path in (
        "db/sqitch.plan",
        "connectors/src/connectors/data/sources.toml",
        "docs/build/reports/ci/flake_log.csv",
    )


def derive_oracle_rows(root: Path, git: "Git", span: str) -> list[OracleRow]:
    """The register-derived expected set (B4 §G2; OM-15 — generated, never hand-copied):

    - append_only_register: `loss`/`transition-unjustified` rows expect a violation on that
      (commit, file) cell under any check — the register names the cell, not which of the
      guard's checks catches it; `benign`/`transition-justified` rows expect the cell clean
      of `append-only` findings (the 405 + 88).
    - date_corrections: each in-scope class-b row the guard can see expects a `record-dates`
      violation on its (introducing commit, path) cell.
    - position scan (B4 G2 amendment 1): a commit that inserts lines inside LEDGER's
      `## GATE DECISIONS` region instead of appending at its end expects an `append-only`
      violation on its (commit, LEDGER) cell.
    """
    rows: list[OracleRow] = []
    span_commits = git.text("rev-list", "--reverse", "--first-parent", span).split()
    reg = list(
        csv.DictReader(open(root / APPEND_REGISTER_REL, newline="", encoding="utf-8"))
    )
    wanted = {r["commit"][:8] for r in reg}
    dc = list(
        csv.DictReader(open(root / DATE_CORRECTIONS_REL, newline="", encoding="utf-8"))
    )
    pol = Policy.parse(
        (root / POLICY_REL).read_bytes() if (root / POLICY_REL).is_file() else None
    )
    added: dict[tuple[str, str], list[str]] = {}
    dc_visible = [
        r for r in dc if date_row_visible(r, pol, added, git)
    ]
    wanted |= {r["introducing_commit"][:8] for r in dc_visible}
    mapping = register_commit_map(git, wanted, span_commits)
    seen: set[tuple] = set()
    # the register is per-row: a cell may hold benign rows *and* a loss row. The cell-level
    # `clean` expectation only holds where no positive row shares the cell.
    positive_cells = {
        (mapping.get(r["commit"][:8], r["commit"][:8]), r["file"])
        for r in reg
        if r["classification"] in ("loss", "transition-unjustified")
    }
    for r in reg:
        c8 = mapping.get(r["commit"][:8], r["commit"][:8])
        cls = r["classification"]
        if cls in ("loss", "transition-unjustified"):
            # the register asserts the cell carries a violation — not which check catches it:
            # a signing rewrite lands under readouts, a lead-token rewrite may land under
            # record-dates (6bade66e). Any error finding on the cell satisfies the row.
            key = ("violation", c8, r["file"], "*", "*")
            note = f"{cls}: {r['summary'][:80]}"
        else:
            if (c8, r["file"]) in positive_cells:
                continue
            key = ("clean", c8, r["file"], "append-only", "*")
            note = cls
        if key not in seen:
            seen.add(key)
            rows.append(OracleRow(*key, "append-register", note))
    for r in dc_visible:
        c8 = mapping.get(r["introducing_commit"][:8], r["introducing_commit"][:8])
        key = ("violation", c8, r["path"], "record-dates", "*")
        if key not in seen:
            seen.add(key)
            rows.append(OracleRow(*key, "date-register", r["note"][:80]))
    rows += _derive_position_rows(git, span_commits)
    return rows


def _derive_position_rows(git: "Git", commits: list[str]) -> list[OracleRow]:
    """B4 G2 amendment 1's scan, redone by code: for each first-parent commit, a `+` line whose
    insert point falls inside the base `## GATE DECISIONS` region (before its last entry) is a
    position violation — 18 top-insertions from `307161ee` plus the two mid-list inserts."""
    rows: list[OracleRow] = []
    for c in commits:
        parent = git.text("rev-parse", f"{c}^").strip()
        base_raw = git.show(c + "^", LEDGER_REL)
        if base_raw is None:
            continue
        base_lines = base_raw.decode("utf-8", "replace").split("\n")
        gd = next(
            (
                r
                for r in regions(base_lines)
                if re.match(r"^##\s+GATE DECISIONS\b", r.heading)
            ),
            None,
        )
        if gd is None:
            continue
        diff = git.text("diff", "-U0", parent, c, "--", LEDGER_REL)
        consumed = 0
        for line in diff.splitlines():
            if line.startswith("@@"):
                m = HUNK_RE.match(line)
                if m:
                    # `-a,b`: base lines a..a+b-1 are consumed; `+` lines insert after the
                    # last consumed base line — the insert position `ins` is `consumed`
                    consumed = int(m[1]) - 1
                    if m[2] == "0":
                        consumed = int(m[1])
                continue
            if line.startswith("-") and not line.startswith("---"):
                consumed += 1
            elif (
                line.startswith("+")
                and not line.startswith("+++")
                and gd.start <= consumed < gd.lnb
            ):
                rows.append(
                    OracleRow(
                        "violation",
                        c[:8],
                        LEDGER_REL,
                        "append-only",
                        "*",
                        "position-scan",
                        "inserted inside GATE DECISIONS (B4 G2 amendment 1)",
                    )
                )
                break
    return rows


def cmd_oracle(args: argparse.Namespace) -> int:
    """`oracle-gen FROM..TO --out FILE`: regenerate the register-derived rows of the replay
    oracle, preserving the file's `reviewed` rows — the recorded disagreements. A derived row
    that disappears or changes is drift: the file and the derivation are re-verified together."""
    root = repo_root(args.repo)
    git = Git(root)
    if ".." not in args.span:
        raise UsageError("oracle-gen wants FROM..TO")
    if git.is_shallow():
        raise UnknownError("shallow clone — oracle derivation needs the full history")
    derived = derive_oracle_rows(root, git, args.span)
    reviewed: list[OracleRow] = []
    out = Path(args.out or (root / ORACLE_REL))
    if out.is_file():
        reviewed = [r for r in load_oracle(out) if r.source == "reviewed"]
    rows = sorted(
        derived + reviewed,
        key=lambda r: (r.commit, r.path, r.check, r.rule, r.kind),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["kind", "commit", "path", "check", "rule", "source", "note"])
        for r in rows:
            w.writerow([r.kind, r.commit, r.path, r.check, r.rule, r.source, r.note])
    print(
        f"oracle-gen: wrote {len(rows)} row(s) to {out} "
        f"({len(derived)} derived, {len(reviewed)} reviewed preserved)"
    )
    return EXIT_OK


def cmd_replay(args: argparse.Namespace) -> int:
    root = repo_root(args.repo)
    git = Git(root)
    if ".." not in args.span:
        raise UsageError("replay wants FROM..TO")
    if git.is_shallow():
        raise UnknownError("shallow clone — replay needs the full history (set fetch-depth: 0)")
    oracle = load_oracle(args.oracle) if args.oracle else None
    commits = git.text("rev-list", "--reverse", "--first-parent", args.span).split()
    if not commits:
        # a replay over an empty span evaluated nothing — vacuous is never green
        print(f"memory-guard replay {args.span}: empty span — nothing judged")
        return EXIT_VACUOUS
    results = []
    findings: list[Finding] = []  # every error finding, tagged with the judged commit
    bad = 0
    vacuous = 0
    for c in commits:
        try:
            change, _policy, _guards, report = judge_change(
                root, git, "first-parent", c, parse_now(args.now)
            )
            in_scope = [f for f in report.findings if f.check in FAMILIES["all"]]
            vac = any(
                report.counts.get(ch, [0, 0])[0] > 0 and report.counts[ch][1] == 0
                for ch in FAMILIES["all"]
            )
            rc = (
                EXIT_VIOLATIONS
                if any(f.severity == "error" for f in in_scope)
                else (EXIT_VACUOUS if vac else EXIT_OK)
            )
        except UnknownError:
            in_scope, rc = [], EXIT_UNKNOWN
        except UsageError:
            in_scope, rc = [], EXIT_USAGE
        rules: dict[str, int] = {}
        for f in in_scope:
            if f.severity != "error":
                continue
            findings.append(
                Finding(f.check, f.rule, f.path, f.line, c[:12], f.message, "error")
            )
            rules[f"{f.check}[{f.rule}]"] = rules.get(f"{f.check}[{f.rule}]", 0) + 1
        bad += rc == EXIT_VIOLATIONS
        vacuous += rc == EXIT_VACUOUS
        info = git.text("log", "-1", "--format=%h %cI", c).strip()
        tag = " ".join(f"{k}×{v}" for k, v in sorted(rules.items()))
        print(f"{info} exit={rc} {tag}".rstrip())
        results.append({"commit": c, "exit": rc, "rules": rules})
    print(
        f"memory-guard replay {args.span}: {len(commits)} commit(s) judged, {bad} with violations"
        + (f", {vacuous} vacuous" if vacuous else "")
    )
    all_vacuous = bool(commits) and vacuous == len(commits)
    if all_vacuous:
        # a replay that judged a non-empty span and evaluated nothing proves nothing —
        # vacuous is never green (EXIT_VACUOUS)
        print("memory-guard replay: every commit judged vacuous — nothing was evaluated")
    disagree_rc = 0
    disagreements: dict[str, list] = {"missing": [], "unexpected": [], "clean-breached": []}
    if oracle is not None:
        disagree_rc, disagreements = oracle_compare(git, args.span, commits, oracle, findings)
    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "schema": "memory-guard-replay/1",
                    "range": args.span,
                    "commits": results,
                    "judged": len(commits),
                    "violating": bad,
                    "vacuous": vacuous,
                    "oracle": args.oracle,
                    "disagreements": disagreements if oracle is not None else None,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    if all_vacuous:
        return EXIT_VACUOUS
    if oracle is not None:
        # the oracle is the verdict: a finding it expects is sanctioned history, a
        # disagreement (missed, unexpected or breached) is the failure
        return disagree_rc
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
    sp.add_argument(
        "--oracle",
        metavar="CSV",
        help="compare the replay's findings against the committed expected set "
        "(default the oracle at %s)" % ORACLE_REL,
    )
    sp = sub.add_parser(
        "oracle-gen",
        help="regenerate the register-derived rows of the replay oracle "
        "(preserves source=reviewed rows; read-only for the repo)",
    )
    sp.add_argument("span", metavar="FROM..TO")
    sp.add_argument("--out", metavar="CSV")
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
        if args.cmd == "oracle-gen":
            return cmd_oracle(args)
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
