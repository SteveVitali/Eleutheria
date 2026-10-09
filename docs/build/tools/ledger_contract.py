#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Ledger-contract validator — B3 §6 V1–V6, V8, V11 and B4 V12–V13 (P34.9, G5/G11).

The control ledger's contract is *checked*, not trusted. `check` judges the
worktree (or a historical tree with ``--at REV``, read from git, the clock bound
to that commit's committer time); `replay` runs the same checks read-only over
each first-parent commit of a range — the "the known pseudo-id cases are all
allow-listed" audit and the pre-seed/seeded evidence pair.

Checks (each reports candidates/evaluated and a declared parse floor):

  orient-budget      V1  orient region (line 1 → before ``## OPEN FINDINGS``)
                         ≤ 12,288 B, warn > 8,192 B
  current-state      V2  19 keys in order (+ optional ``harness`` in its slot),
                         declared vocabularies, lines ≤ 256 B, no ``| PRIOR``,
                         updatedAt ≤ the clock/commit, nextTicket = the lowest
                         not-landed chain row or DONE, returnPass is an id list,
                         no key-named line outside the section
  named-paths        V3  every backticked repo path in the orient region (and the
                         manifest/canonicalSpec/memoryRoot values) exists
  stale-tokens       V3  no deny-listed token appears (defaults +
                         record_policy/stale_tokens.txt)
  ticket-counts      V3  ``N tickets`` claims in the orient region match the
                         manifest's chain-row count
  phase-log          V4  bullets parse to ``- <date> — <id> <kind> — <payload>``,
                         kinds in record_policy/phase_log_kinds.txt, entries
                         ≤ 2,048 B, lead dates ≤ the bound and non-decreasing in
                         the current region, the last ``## `` heading is the
                         append target
  phase-log-done     V4  landing kinds (``done``/``ticket``) resolve to a
                         BUILD_INDEX row and an evidence file; pseudo-ids
                         SETUP/OPERATOR/ROUND*/CAPSTONE/DONE are allow-listed
                         (parse floor 0.5 — fewer than half of a non-empty
                         candidate set parsing is vacuous)
  build-index        V5  rows parse to their section header's column count (an
                         unescaped ``|`` fails), seq values unique, no ``PR
                         pending`` placeholder after the run ledger closes,
                         live-verification vocabulary, landed ≤ the bound —
                         strict inside ``## Round 11``, warnings in older
                         (unmodifiable) sections
  return-pass        V6  ``returnPass:`` ids equal the ticket cells of
                         ``### RETURN PASS — current``
  gate-decisions     V8  the ``### Round 11`` table parses to 7 columns, kinds in
                         the declared set, answers quoted, dates ≤ the bound and
                         appended in order at the section end
  orient-probe       V11 head + current RETURN PASS + last three PHASE LOG
                         entries + the next row's manifest line and contract
                         head ≤ 48 KiB; nextTicket resolves
  run-harness        V12 run ledgers committed at/after the guards marker carry
                         ``Harness: <harness>/<model-id>/<tier>``
  manifest-rounds    V13 every chain row sits under a ``### Round <n>`` banner
                         (strict for seq ≥ 67, the seeded region; warnings for
                         the pre-banner history) and ticket ids are never reused

V9 (``current_projection.py verify`` in CI) and V14 (planning-ledger freshness,
the vendored ``--planning`` mode over ``docs/build/planning/*/META_PLAN.md``) are
wired in ``make docs-check`` / the CI ``docs`` job, not duplicated here.

G11 no-vacuous-pass: a check that evaluated none of a non-empty candidate set is
vacuous — the tool exits 3, never 0. A check under its declared floor is a
violation. Exit codes match memory_guard.py: 0 green, 1 violations, 2 usage, 3
vacuous, 5 unknown.

Usage::

    python3 docs/build/tools/ledger_contract.py check [--repo DIR] [--at REV]
                                                      [--now ISO] [--json PATH]
    python3 docs/build/tools/ledger_contract.py replay FROM..TO [--repo DIR]
                                                      [--json PATH]
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass, field

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import audit_current_state  # noqa: E402 — EXPECTED_KEYS is the shared key list

ROOT = pathlib.Path(__file__).resolve().parents[3]
SCHEMA = "ledger-contract/1"
EXIT_OK, EXIT_VIOLATIONS, EXIT_USAGE, EXIT_VACUOUS, EXIT_UNKNOWN = 0, 1, 2, 3, 5

LEDGER_REL = "docs/build/LEDGER.md"
BI_REL = "docs/build/BUILD_INDEX.md"
README_REL = "docs/build/README.md"
POLICY_REL = "docs/build/tools/record_policy"
KINDS_REL = f"{POLICY_REL}/phase_log_kinds.txt"
STALE_REL = f"{POLICY_REL}/stale_tokens.txt"

ORIENT_WARN, ORIENT_MAX = 8192, 12288
CS_MAX, LINE_MAX, ENTRY_MAX, PROBE_MAX = 3072, 256, 2048, 49152

EXPECTED_KEYS = audit_current_state.EXPECTED_KEYS
EXPECTED_KEYS_WITH_HARNESS = audit_current_state.EXPECTED_KEYS_WITH_HARNESS
ALL_KEY_NAMES = frozenset(EXPECTED_KEYS_WITH_HARNESS)

# Ticket-id grammar (the vendored script's ID_RE, Python-flavoured).
ID_RE = r"(?:(?:HUMAN-H|GATE-G)[0-9]+|GATE-ACCEPT|[A-Z]+[0-9]*[a-z]?(?:\.[0-9]+[a-z]?)?)"
ID_FULL = re.compile(rf"^{ID_RE}$")
PSEUDO_IDS = ("SETUP", "CAPSTONE", "DONE", "OPERATOR")  # + ROUND* prefix
ENTRY_RE = re.compile(r"^-\s*")
LEAD_RE = re.compile(r"^-\s*(\d{4}-\d{2}-\d{2})")
H2_RE = re.compile(r"^##\s")
KEY_LINE_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9]*):(?=\s|$)")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
GATE_KINDS = frozenset(
    {"decision", "pre-authorization", "confirmation", "waiver", "correction"}
)
LIVE_VERIFY = frozenset(
    {"live-executed", "staging", "fixture-only", "engineered", "n-a", "gate-pending"}
)
VOCAB = {
    "projectStatus": re.compile(r"^(NOT_STARTED|IN_PROGRESS|BLOCKED|PAUSED|DONE)$"),
    "pauseRequested": re.compile(r"^(true|false)$"),
    "mergePolicy": re.compile(r"^(NONE|OPERATOR|AUTO-BOTTOM-UP)$"),
    "autonomy": re.compile(r"^(auto|checkpoint|manual)$"),
    "round": re.compile(r"^[0-9]+$"),
    "updatedAt": re.compile(
        r"^[0-9]{4}-[0-9]{2}-[0-9]{2}([T ][0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]+)?)?"
        r"(Z|[+-][0-9]{2}(:?[0-9]{2})?)?)?$"
    ),
    "harness": re.compile(r"^[a-z0-9._-]+/[a-z0-9._-]+/[a-z0-9._-]+$"),
}
# Round-11 BUILD_INDEX section: strict scope for the V5 row rules.
STRICT_INDEX_SECTION = "Round 11"
# Chain rows with seq ≥ this sit under `### Round <n>` banners (B5 NEW-4 seeded
# the convention; rows 1–66 predate it and stay warnings).
BANNER_STRICT_SEQ = 67


class UsageError(Exception):
    pass


@dataclass
class Finding:
    check: str
    rule: str
    path: str
    line: int
    message: str
    severity: str  # error | warning

    def as_json(self) -> dict:
        return {
            "check": self.check,
            "rule": self.rule,
            "path": self.path,
            "line": self.line,
            "message": self.message,
        }


@dataclass
class Check:
    name: str
    floor: float = 0.0  # evaluated >= ceil(candidates * floor) required


class Report:
    def __init__(self) -> None:
        self.findings: list[Finding] = []
        self.counts: dict[str, list[int]] = {}
        self.extra: dict[str, object] = {}

    def v(self, check: str, rule: str, path: str, line: int, message: str) -> None:
        self.findings.append(Finding(check, rule, path, line, message, "error"))

    def w(self, check: str, rule: str, path: str, line: int, message: str) -> None:
        self.findings.append(Finding(check, rule, path, line, message, "warning"))

    def count(self, check: str, candidates: int, evaluated: int) -> None:
        c = self.counts.setdefault(check, [0, 0])
        c[0] += candidates
        c[1] += evaluated


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def parse_dt(text: str) -> datetime.datetime | None:
    """ISO-8601 date or datetime (Z or offset) → aware datetime; None if not."""
    m = re.match(
        r"^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?"
        r"\s*(Z|[+-]\d{2}:?\d{2})?)?",
        text.strip(),
    )
    if not m:
        return None
    y, mo, d, hh, mm, ss, tz = m.groups()
    try:
        dt = datetime.datetime(
            int(y), int(mo), int(d), int(hh or 0), int(mm or 0), int(ss or 0)
        )
    except ValueError:
        return None
    if tz and tz != "Z":
        sign = 1 if tz[0] == "+" else -1
        td = re.sub(r":", "", tz[1:])
        dt -= datetime.timedelta(
            hours=sign * int(td[:2]), minutes=sign * int(td[2:])
        )
    return dt.replace(tzinfo=datetime.timezone.utc)


def strip_markup(text: str) -> str:
    return re.sub(r"[*_`]", "", text)


# ── input sources: the worktree, or a git tree ────────────────────────────────


class Src:
    def read_text(self, rel: str) -> str | None:  # pragma: no cover - interface
        raise NotImplementedError

    def read_bytes(self, rel: str) -> bytes | None:  # pragma: no cover
        raise NotImplementedError

    def exists(self, rel: str) -> bool:  # pragma: no cover
        raise NotImplementedError

    def files(self) -> set[str]:  # pragma: no cover
        raise NotImplementedError


class TreeSrc(Src):
    def __init__(self, root: pathlib.Path) -> None:
        self.root = root

    def read_text(self, rel: str) -> str | None:
        p = self.root / rel
        if not p.is_file():
            return None
        try:
            return p.read_text()
        except (OSError, UnicodeDecodeError):
            return None

    def read_bytes(self, rel: str) -> bytes | None:
        p = self.root / rel
        return p.read_bytes() if p.is_file() else None

    def exists(self, rel: str) -> bool:
        return (self.root / rel).exists()

    def files(self) -> set[str]:
        return {
            str(p.relative_to(self.root))
            for p in self.root.rglob("*")
            if p.is_file() and ".git" not in p.parts
        }


class RevSrc(Src):
    def __init__(self, git: "Git", rev: str) -> None:
        self.git = git
        self.rev = rev
        self._files = set(
            git.run("ls-tree", "-r", "--name-only", rev).splitlines()
        )

    def read_text(self, rel: str) -> str | None:
        raw = self.read_bytes(rel)
        try:
            return raw.decode() if raw is not None else None
        except UnicodeDecodeError:
            return None

    def read_bytes(self, rel: str) -> bytes | None:
        if rel not in self._files:
            return None
        return self.git.show(self.rev, rel)

    def exists(self, rel: str) -> bool:
        return rel in self._files

    def files(self) -> set[str]:
        return set(self._files)


class Git:
    def __init__(self, root: pathlib.Path) -> None:
        self.root = root

    def run(self, *args: str) -> str:
        out = self._run(*args)
        return out.decode(errors="replace") if isinstance(out, bytes) else out

    def _run(self, *args: str) -> str | bytes:
        cp = subprocess.run(
            ["git", "-C", str(self.root), *args],
            capture_output=True,
        )
        if cp.returncode != 0:
            raise UsageError(
                f"git {' '.join(args)} failed: {cp.stderr.decode(errors='replace')[:200]}"
            )
        return cp.stdout.decode(errors="replace")

    def show(self, rev: str, path: str) -> bytes | None:
        cp = subprocess.run(
            ["git", "-C", str(self.root), "show", f"{rev}:{path}"],
            capture_output=True,
        )
        return cp.stdout if cp.returncode == 0 else None

    def committer_epoch(self, rev: str) -> int:
        return int(self.run("show", "-s", "--format=%ct", rev).strip())

    def marker_commit(self, rev: str) -> str | None:
        out = self.run(
            "log",
            "--format=%H",
            "-S",
            "build-memory-guards: 1",
            rev,
            "--",
            README_REL,
        )
        lines = [ln for ln in out.splitlines() if ln.strip()]
        return lines[-1] if lines else None

    def ancestors(self, rev: str) -> set[str]:
        return set(self.run("rev-list", rev).splitlines())

    def first_added(self, rev: str, *dirs: str) -> dict[str, str]:
        """path → first commit that added it (within `rev`'s history)."""
        out = self.run(
            "log", "--reverse", "--diff-filter=A", "--name-only",
            "--format=@%H", rev, "--", *dirs,
        )
        adds: dict[str, str] = {}
        cur = ""
        for ln in out.splitlines():
            if ln.startswith("@"):
                cur = ln[1:]
            elif ln.strip() and ln not in adds:
                adds[ln] = cur
        return adds

    def first_parents(self, span: str) -> list[str]:
        out = self.run("log", "--format=%H", "--first-parent", span)
        return [ln for ln in out.splitlines() if ln.strip()]


# ── shared parsing ────────────────────────────────────────────────────────────


def lval(ledger: str, key: str) -> str:
    for ln in ledger.splitlines():
        m = KEY_LINE_RE.match(ln)
        if m and m.group(1) == key:
            return re.sub(r"\s*#.*$", "", ln[m.end() :]).strip()
    return ""


def orient_text(ledger: str) -> str:
    out = []
    for ln in ledger.splitlines():
        if re.match(r"^##\s+OPEN FINDINGS", ln):
            break
        out.append(ln)
    return "\n".join(out) + ("\n" if out else "")


def section_text(lines: list[str], head_re: re.Pattern) -> tuple[int, str]:
    """Lines of the `## ` section whose heading matches, as (lineno, text)."""
    start = None
    for i, ln in enumerate(lines):
        if start is None and H2_RE.match(ln) and head_re.match(ln):
            start = i
            continue
        if start is not None and H2_RE.match(ln):
            return start + 1, "\n".join(lines[start : i + 1])
    if start is not None:
        return start + 1, "\n".join(lines[start:])
    return 0, ""


def current_state_block(ledger: str) -> str:
    m = re.search(r"(?ms)^##\s+CURRENT STATE.*?^```\s*$(.*?)^```", ledger)
    return m.group(1) if m else ""


def key_lines(ledger: str) -> list[tuple[int, str]]:
    """(lineno, raw line) of CURRENT-STATE key lines, anywhere in the section."""
    lines = ledger.splitlines()
    inblk = False
    out: list[tuple[int, str]] = []
    for i, ln in enumerate(lines, 1):
        if re.match(r"^##\s+CURRENT STATE", ln):
            inblk = True
            continue
        if inblk and H2_RE.match(ln):
            break
        if inblk and KEY_LINE_RE.match(ln):
            out.append((i, ln))
    return out


def phase_log_entries(ledger: str) -> list[dict]:
    """One record per PHASE LOG bullet: region index, whether it is the last
    region, markup stripped, id, kind, lead date, entry byte size."""
    lines = ledger.splitlines()
    has_pl = any(
        re.match(r"^##\s+PHASE LOG", ln) and "INDEX" not in ln for ln in lines
    )
    records: list[dict] = []
    region = 0
    inlog = not has_pl
    cur: dict | None = None

    def close() -> None:
        nonlocal cur
        if cur is not None:
            records.append(cur)
            cur = None

    for i, ln in enumerate(lines, 1):
        if H2_RE.match(ln):
            close()
            inlog = (
                re.match(r"^##\s+PHASE LOG", ln) is not None and "INDEX" not in ln
            )
            if inlog:
                region += 1
            continue
        if not inlog:
            continue
        if ENTRY_RE.match(ln):
            close()
            cur = {"line": i, "region": region, "size": len(ln.encode()) + 1}
            continue
        if cur is not None:
            if ln.strip() == "":
                close()
            else:
                cur["size"] += len(ln.encode()) + 1
    close()
    last_region = region
    for rec in records:
        rec["last"] = rec["region"] == last_region
        raw = lines[rec["line"] - 1]
        s = strip_markup(raw)
        lm = LEAD_RE.match(s)
        rec["lead"] = lm.group(1) if lm else ""
        rec["id"] = ""
        rec["kind"] = ""
        rec["head_ok"] = False
        rec["markup"] = False
        if lm:
            # the head is the text between the first `—` and the next ` — `;
            # markup is flagged only when it lives inside the head (`**P24.9**
            # done`), not when the payload carries backticks (the vendored
            # script judges the same scope — a payload `…` is fine)
            rp = raw.find("—")
            if rp >= 0:
                rest_raw = raw[rp + 1 :].lstrip()
                rq = rest_raw.find(" — ")
                raw_head = rest_raw[:rq] if rq >= 0 else rest_raw
                rec["markup"] = bool(re.search(r"[*_`]", raw_head))
            p = s.find("—")
            if p >= 0:
                rest = s[p + 1 :].lstrip()
                q = rest.find(" — ")
                head = (rest[:q] if q >= 0 else rest).strip()
                # id = an ID_RE token anchored at the head's start, followed by
                # a delimiter char (the vendored script's IDRE + nx rule). A
                # lowercase/prose head (`agenda content depth done …`) has no
                # id — it is a candidate for done-detection but never
                # evaluated, which is exactly what keeps it out of the
                # done ⇔ BUILD_INDEX check.
                idm = re.match(ID_RE, head) if head else None
                if idm:
                    tail_ch = head[idm.end() : idm.end() + 1]
                    if tail_ch and tail_ch not in (" ", "\t", ":", ",", "("):
                        idm = None
                if idm:
                    rec["id"] = idm.group(0)
                    rec["head_ok"] = True
                    kind = head[idm.end() :].strip()
                    kind = kind.split("(", 1)[0].strip()
                    kind = re.sub(r"\s+\+.*$", "", kind)
                    kind = re.sub(r"\s+#\d+\s*$", "", kind)
                    rec["kind"] = kind
                rec["head_text"] = head
        # A landing entry: the canonical Round-11 `ticket`/`done` kind, or any
        # head carrying `done` as a word (the legacy `- <id> done` shape).
        rec["isdone"] = rec["kind"] in ("done", "ticket") or (
            rec.get("head_text") is not None
            and re.search(
                r"(^|[^A-Za-z-])done([^A-Za-z-]|$)", rec.get("head_text", "")
            )
            is not None
        )
    return records


def split_cells(ln: str) -> list[str]:
    """`|`-separated cells of a table row. An escaped `\\|` inside a cell does
    not split (the vendored checker's `ncells` convention — escaped pipes pass,
    unescaped pipes are extra columns)."""
    u = re.sub(r"\\\|", "\x00", ln.strip())
    u = u.strip("|")
    return [c.strip().replace("\x00", "|") for c in u.split("|")]


def index_sections(bi: str) -> list[dict]:
    """BUILD_INDEX tables: [{section, header_count, rows:[(lineno,cells)]}]."""
    out: list[dict] = []
    sec = ""
    header: list[str] | None = None
    rows: list[tuple[int, list[str]]] = []

    def flush() -> None:
        nonlocal header, rows
        if header is not None or rows:
            out.append(
                {"section": sec, "header": header or [], "rows": rows}
            )
        header, rows = None, []

    for i, ln in enumerate(bi.splitlines(), 1):
        if H2_RE.match(ln):
            flush()
            sec = re.sub(r"^##\s+", "", ln).strip()
            continue
        if not ln.startswith("|"):
            continue
        if re.match(r"^\|[-|: ]+\|\s*$", ln):
            continue
        cells = split_cells(ln)
        if header is None:
            header = cells
        else:
            rows.append((i, cells))
    flush()
    return out


def index_ticket_ids(bi: str) -> set[str]:
    ids: set[str] = set()
    for ln in bi.splitlines():
        m = re.match(r"^\|\s*\d+\s*\|\s*\**([A-Za-z][A-Za-z0-9.-]*)", ln)
        if m:
            ids.add(m.group(1).rstrip("."))
    return ids


def manifest_rows(manifest: str) -> list[dict]:
    """Chain rows under `## The chain`: seq, filename, line, banner."""
    out: list[dict] = []
    in_chain = False
    banner = ""
    for i, ln in enumerate(manifest.splitlines(), 1):
        if re.match(r"^##\s+The chain", ln):
            in_chain = True
            continue
        if in_chain and re.match(r"^## (?!#)", ln):
            in_chain = False
        m = re.match(r"^###\s+(.*)", ln)
        if in_chain and m:
            banner = m.group(1)
        if not in_chain or not ln.startswith("|"):
            continue
        cells = split_cells(ln)
        if not cells or not re.fullmatch(r"\d+[a-z]?", cells[0] or ""):
            continue
        files = re.findall(r"[0-9A-Za-z_.-]+\.md", ln)
        fname = files[0] if files else ""
        tid = ""
        fm = re.match(r"^(\d{2,3}[a-z]?_)?(.+?)__[^_].*\.md$", fname)
        if fm:
            tid = fm.group(2)
        out.append(
            {
                "seq": cells[0],
                "seq_num": int(cells[0].rstrip("a")),
                "file": fname,
                "ticket": tid,
                "line": i,
                "banner": banner,
                "skipped": bool(
                    re.search(
                        r"\b(?:superseded-by|deferred)\(|\bunused\b", ln, re.I
                    )
                ),
            }
        )
    return out


def first_table(lines: list[str], start: int) -> tuple[list[str], list[tuple[int, list[str]]]]:
    """Header cells + data rows of the first `|`-table at/after `start` (0-based
    index into lines); start points at a heading line or -1."""
    header: list[str] | None = None
    rows: list[tuple[int, list[str]]] = []
    if start < 0:
        return [], rows
    for i in range(start, len(lines)):
        ln = lines[i]
        if i > start and re.match(r"^#{1,3}\s", ln):
            break
        if not ln.startswith("|"):
            if header is not None and rows:
                break
            continue
        if re.match(r"^\|[-|: ]+\|\s*$", ln):
            continue
        cells = split_cells(ln)
        if header is None:
            header = cells
        else:
            rows.append((i + 1, cells))
    return header or [], rows


def landed_ids(ledger: str, bi: str, index_ids: set[str]) -> set[str]:
    """BUILD_INDEX ticket cells + PHASE LOG landing-entry ids + returnPass ids
    (the V2 landed set)."""
    out = set(index_ids)
    for rec in phase_log_entries(ledger):
        if rec["isdone"] and rec["id"]:
            out.add(rec["id"])
    for t in lval(ledger, "returnPass").split(","):
        t = t.strip()
        if t:
            out.add(t)
    return out


def created_after_marker(
    rel: str, adds: dict[str, str], before: set[str], marker_state: str
) -> bool:
    """The vendored script's rule: the file's first-add commit is not a strict
    ancestor of the marker commit (uncommitted/unknown → new)."""
    if marker_state == "none":
        return False
    c = adds.get(rel)
    if not c:
        return True
    if marker_state == "uncommitted":
        return False
    return c not in before


# ── the checks ────────────────────────────────────────────────────────────────


def check_orient_budget(rep: Report, src: Src, ctx: dict) -> None:
    name = "orient-budget"
    raw = src.read_bytes(LEDGER_REL)
    if raw is None:
        rep.count(name, 0, 0)
        return
    rep.count(name, 1, 1)
    orient = orient_text(raw.decode(errors="replace"))
    n = len(orient.encode())
    if f"\n## OPEN FINDINGS" not in "\n" + raw.decode(errors="replace"):
        rep.v(name, "orient-shape", LEDGER_REL, 0,
              "no `## OPEN FINDINGS` heading — the orient region has no boundary")
    if n > ORIENT_MAX:
        rep.v(name, "orient-budget", LEDGER_REL, 0,
              f"orient region is {n} B, over the 12 KiB budget (V1)")
    elif n > ORIENT_WARN:
        rep.w(name, "orient-budget", LEDGER_REL, 0,
              f"orient region is {n} B, above the 8 KiB warning level (V1)")
    ctx["orient_bytes"] = n


def check_current_state(rep: Report, src: Src, ctx: dict) -> None:
    name = "current-state"
    ledger = src.read_text(LEDGER_REL)
    if ledger is None:
        rep.count(name, 0, 0)
        return
    bound = ctx["bound_dt"]
    lines = ledger.splitlines()
    kl = key_lines(ledger)
    rep.count(name, len(kl), len(kl))
    got = [re.sub(r":.*$", "", ln).strip() for _i, ln in kl]
    if got and got not in (EXPECTED_KEYS, EXPECTED_KEYS_WITH_HARNESS):
        rep.v(name, "key-order", LEDGER_REL, kl[0][0] if kl else 0,
              "CURRENT STATE keys are missing, extra or out of order "
              "(expected the 19-key list; optional 'harness' only between "
              "round and updatedAt) (V2)")
    _cs_lineno, cs = section_text(lines, re.compile(r"^##\s+CURRENT STATE"))
    if len(cs.encode()) > CS_MAX:
        rep.v(name, "cs-budget", LEDGER_REL, 0,
              f"CURRENT STATE section is {len(cs.encode())} B, over the 3 KiB "
              "budget (values only, V2)")
    for lineno, ln in kl:
        if len(ln.encode()) > LINE_MAX:
            rep.v(name, "line-budget", LEDGER_REL, lineno,
                  f"CURRENT STATE line is {len(ln.encode())} B (> 256 B; values "
                  "only, V2)")
        if re.search(r"\|\s*\**PRIOR", ln):
            rep.v(name, "prior-history", LEDGER_REL, lineno,
                  "CURRENT STATE line carries '| PRIOR' history — values only "
                  "(V2)")
    vals = {k: lval(ledger, k) for k in ALL_KEY_NAMES}
    for key, pat in VOCAB.items():
        tok = (vals.get(key) or "").split(" ")[0] if vals.get(key) else ""
        if tok and not tok.startswith("<") and not tok.startswith("("):
            if not pat.match(tok):
                rep.v(name, "key-vocabulary", LEDGER_REL, 0,
                      f"CURRENT STATE {key} '{tok}' is outside its declared "
                      "vocabulary (V2)")
    upd = (vals.get("updatedAt") or "").split(" ")[0]
    if upd and parse_dt(upd) is not None and bound is not None:
        if parse_dt(upd) > bound:
            rep.v(name, "updatedAt-future", LEDGER_REL, 0,
                  f"updatedAt {upd} is later than the bound "
                  f"{ctx['bound_iso']} (V2)")
    rp = vals.get("returnPass") or ""
    if rp and rp not in ("(none)", "none", "(nothing)"):
        if not re.fullmatch(rf"{ID_RE}(\s*,\s*{ID_RE})*", rp):
            rep.v(name, "returnPass-grammar", LEDGER_REL, 0,
                  "returnPass is not a comma-separated ticket-id list (V2)")
    # no line outside CURRENT STATE begins with a key name
    inblk = False
    for i, ln in enumerate(lines, 1):
        if re.match(r"^##\s+CURRENT STATE", ln):
            inblk = True
            continue
        if inblk and H2_RE.match(ln):
            inblk = False
        if inblk:
            continue
        m = KEY_LINE_RE.match(ln)
        if m and m.group(1) in ALL_KEY_NAMES:
            rep.v(name, "key-shadow", LEDGER_REL, i,
                  f"line begins with CURRENT STATE key '{m.group(1)}' outside "
                  "the section — readers take the first match (V2)")
            break
    # nextTicket names a chain row / DONE / SETUP and is the lowest not-landed
    manifest = src.read_text(ctx["manifest_rel"]) or ""
    mrows = manifest_rows(manifest)
    ids = {r["ticket"] for r in mrows if r["ticket"]}
    ctx["manifest_rows"] = mrows
    nt = (vals.get("nextTicket") or "").split(" ")[0]
    if nt and nt not in ("DONE", "SETUP"):
        if nt not in ids:
            rep.v(name, "next-unknown", LEDGER_REL, 0,
                  f"nextTicket '{nt}' names no chain row, DONE or SETUP (V2)")
        elif mrows:
            bi = src.read_text(BI_REL) or ""
            landed = landed_ids(ledger, bi, index_ticket_ids(bi))
            want = "DONE"
            for r in mrows:
                tid = r["ticket"]
                if (
                    not tid
                    or tid in landed
                    or r["skipped"]
                    or tid.startswith("HUMAN-")
                ):
                    continue
                want = tid
                break
            ctx["want_next"] = want
            if nt != want:
                rep.v(name, "next-not-lowest", LEDGER_REL, 0,
                      f"nextTicket '{nt}' is not the lowest chain row that has "
                      f"not landed ('{want}'; superseded-by/deferred/unused and "
                      "HUMAN rows skipped) (V2)")
    lc = (vals.get("lastCompleted") or "").split(" ")[0]
    if lc and mrows:
        bi = src.read_text(BI_REL) or ""
        if lc in ids and lc not in index_ticket_ids(bi):
            rep.v(name, "lastCompleted-uncovered", LEDGER_REL, 0,
                  f"lastCompleted '{lc}' has no BUILD_INDEX row (V2)")


def check_named_paths(rep: Report, src: Src, ctx: dict) -> None:
    name = "named-paths"
    ledger = src.read_text(LEDGER_REL)
    if ledger is None:
        rep.count(name, 0, 0)
        return
    orient = orient_text(ledger)
    toks = set(re.findall(r"`([^`\s]+)`", orient))
    for key in ("manifest", "canonicalSpec", "memoryRoot"):
        v = lval(ledger, key)
        if v:
            toks.add(v)
    cand = 0
    missing: list[str] = []
    for tok in sorted(toks):
        p = re.sub(r"[#:][^/]*$", "", tok)
        p = re.sub(r"[.,;)]+$", "", p)
        if (
            not p
            or p.startswith(("/", "~", "-"))
            or any(c in p for c in ("://", "<", ">", "{", "}", "*", "$", "=", "…"))
            or "/" not in p
            or not re.search(r"(\.[A-Za-z0-9]{1,5}|/)$", p)
        ):
            continue
        cand += 1
        if not src.exists(p) and not src.exists(f"docs/build/{p}"):
            missing.append(p)
    rep.count(name, cand, cand)
    for p in missing[:10]:
        rep.v(name, "path-missing", LEDGER_REL, 0,
              f"orient region names repo path '{p}' which does not exist — "
              "stale orient text (V3)")
    if len(missing) > 10:
        rep.v(name, "path-missing", LEDGER_REL, 0,
              f"… and {len(missing) - 10} more missing named path(s) (V3)")


def check_stale_tokens(rep: Report, src: Src, ctx: dict) -> None:
    name = "stale-tokens"
    ledger = src.read_text(LEDGER_REL)
    if ledger is None:
        rep.count(name, 0, 0)
        return
    tokens = [".agents/scratch", "gitignored", "Do not resume until"]
    raw = src.read_text(STALE_REL)
    if raw is not None:
        for ln in raw.splitlines():
            ln = re.sub(r"\s+#.*$", "", ln).strip()
            if not ln or ln.startswith("#"):
                continue
            if ln.startswith("!"):
                tokens = [t for t in tokens if t != ln[1:]]
            else:
                tokens.append(ln)
    orient = orient_text(ledger).splitlines()
    rep.count(name, len(tokens), len(tokens))
    for tok in tokens:
        for i, ln in enumerate(orient, 1):
            if tok in ln:
                rep.v(name, "stale-token", LEDGER_REL, i,
                      f"orient region carries the stale token '{tok}' — "
                      "supersede it in OPERATING MODE, archive the old text (V3)")
                break


def check_ticket_counts(rep: Report, src: Src, ctx: dict) -> None:
    name = "ticket-counts"
    ledger = src.read_text(LEDGER_REL)
    if ledger is None:
        rep.count(name, 0, 0)
        return
    mrows = ctx.get("manifest_rows")
    if mrows is None:
        manifest = src.read_text(ctx["manifest_rel"]) or ""
        mrows = manifest_rows(manifest)
    n_rows = len(mrows)
    claims = re.findall(r"(\d+)\s+tickets", orient_text(ledger))
    rep.count(name, len(claims), len(claims))
    for c in claims:
        if int(c) != n_rows:
            rep.v(name, "count-mismatch", LEDGER_REL, 0,
                  f"orient region claims '{c} tickets' but the manifest holds "
                  f"{n_rows} chain rows (V3)")


def check_phase_log(rep: Report, src: Src, ctx: dict, kinds: set[str]) -> None:
    name = "phase-log"
    ledger = src.read_text(LEDGER_REL)
    if ledger is None:
        rep.count(name, 0, 0)
        return
    lines = ledger.splitlines()
    recs = phase_log_entries(ledger)
    rep.count(name, len(recs), sum(1 for r in recs if r["head_ok"]))
    # append target: the last `## ` heading is a PHASE LOG heading
    h2s = [ln for ln in lines if H2_RE.match(ln)]
    if any(re.match(r"^##\s+PHASE LOG", ln) for ln in h2s):
        last = h2s[-1]
        if not re.match(r"^##\s+PHASE LOG", last) or "INDEX" in last:
            rep.v(name, "append-target", LEDGER_REL, 0,
                  f"the last region is '{last.strip()}', not a PHASE LOG "
                  "heading — new entries go only at the end of the file (V4)")
    bound = ctx["bound_dt"]
    prev_lead = ""
    prev_line = 0
    for r in recs:
        strict = r["last"]
        emit = rep.v if strict else rep.w
        if r["size"] > ENTRY_MAX:
            emit(name, "entry-budget", LEDGER_REL, r["line"],
                 f"PHASE LOG entry is {r['size']} B (> 2 KiB, BM-LEDGER-06)"
                 + ("" if strict else " (legacy region)"))
        if r["markup"]:
            emit(name, "markup-id", LEDGER_REL, r["line"],
                 "PHASE LOG entry parses only after stripping markup "
                 "(`*`, `_`, backticks) — write the id bare (BM-LEDGER-06)"
                 + ("" if strict else " (legacy region)"))
        if r["lead"]:
            ldt = parse_dt(r["lead"])
            if bound is not None and ldt is not None and ldt > bound:
                emit(name, "future-date", LEDGER_REL, r["line"],
                     f"PHASE LOG lead date {r['lead']} is later than the bound "
                     f"{ctx['bound_iso']}"
                     + ("" if strict else " (legacy region)"))
            if strict and r["head_ok"]:
                if prev_lead and r["lead"] < prev_lead:
                    rep.w(name, "append-order", LEDGER_REL, r["line"],
                          f"PHASE LOG lead date {r['lead']} is earlier than "
                          f"the previous entry's {prev_lead} (line {prev_line}) "
                          "— entries append newest last (V4)")
                prev_lead, prev_line = r["lead"], r["line"]
        if r["head_ok"] and r["kind"] and r["kind"] not in kinds:
            emit(name, "kind-vocabulary", LEDGER_REL, r["line"],
                 f"PHASE LOG kind '{r['kind']}' is not in "
                 "record_policy/phase_log_kinds.txt (V4)"
                 + ("" if strict else " (legacy region)"))


def check_phase_log_done(rep: Report, src: Src, ctx: dict) -> None:
    name = "phase-log-done"
    ledger = src.read_text(LEDGER_REL)
    if ledger is None:
        rep.count(name, 0, 0)
        return
    recs = [r for r in phase_log_entries(ledger) if r["isdone"]]
    evaluated = [r for r in recs if r["id"]]
    rep.count(name, len(recs), len(evaluated))
    bi = src.read_text(BI_REL) or ""
    idx = index_ticket_ids(bi)
    for r in evaluated:
        tid = r["id"]
        if tid in PSEUDO_IDS or tid.startswith("ROUND"):
            continue
        emit = rep.v if r["last"] else rep.w
        if bi and tid not in idx:
            emit(name, "done-uncovered", BI_REL, r["line"],
                 f"PHASE LOG marks {tid} done (line {r['line']}) but "
                 "BUILD_INDEX.md has no row for it"
                 + ("" if r["last"] else " (legacy region)"))
        if not (
            src.exists(f"docs/build/runs/{tid}.md")
            or src.exists(f"docs/build/pr/{tid}.md")
        ):
            emit(name, "evidence-missing", LEDGER_REL, r["line"],
                 f"PHASE LOG marks {tid} done (line {r['line']}) but neither "
                 f"docs/build/runs/{tid}.md nor pr/{tid}.md exists"
                 + ("" if r["last"] else " (legacy region)"))


def check_build_index(rep: Report, src: Src, ctx: dict) -> None:
    name = "build-index"
    bi = src.read_text(BI_REL)
    if bi is None:
        rep.count(name, 0, 0)
        return
    bound = ctx["bound_dt"]
    sections = index_sections(bi)
    n_cand = n_eval = 0
    for sec in sections:
        strict = sec["section"].startswith(STRICT_INDEX_SECTION)
        emit = rep.v if strict else rep.w
        hcols = len(sec["header"])
        seen_seq: set[str] = set()
        for lineno, cells in sec["rows"]:
            n_cand += 1
            # a row the checker judged — including a column-count failure — was
            # evaluated; `n_eval == 0` means the checker never got to look
            n_eval += 1
            if len(cells) != hcols:
                emit(name, "column-count", BI_REL, lineno,
                     f"row has {len(cells)} cells, the section header has "
                     f"{hcols} — an unescaped '|' in a cell? (V5)"
                     + ("" if strict else " (legacy section)"))
                continue
            seq = cells[0] if cells else ""
            if seq in seen_seq:
                emit(name, "seq-duplicate", BI_REL, lineno,
                     f"duplicate BUILD_INDEX seq '{seq}' (V5)"
                     + ("" if strict else " (legacy section)"))
            seen_seq.add(seq)
            if strict:
                hmap = dict(zip(sec["header"], cells))
                pr = hmap.get("PR", "")
                tid = hmap.get("ticket", "")
                lv = hmap.get(
                    next((h for h in sec["header"] if "live" in h.lower()), ""),
                    "",
                )
                landed = hmap.get("landed", "")
                if re.search(r"pending|TBD", pr, re.I):
                    run = src.read_text(f"docs/build/runs/{tid}.md") or ""
                    if re.search(r"(?mi)^\s*(-\s*)?(\*\*)?Closed:", run):
                        rep.v(name, "placeholder", BI_REL, lineno,
                              f"row {seq} still reads '{pr}' but "
                              f"runs/{tid}.md is Closed: — the PR cell is the "
                              "real #<n> (V5)")
                lv_tok = lv.strip().strip("`*").split(" ")[0] if lv else ""
                if lv_tok and lv_tok not in LIVE_VERIFY:
                    rep.v(name, "live-verification", BI_REL, lineno,
                          f"live-verification cell '{lv_tok}' is outside "
                          f"{' | '.join(sorted(LIVE_VERIFY))} (V5)")
                ldt = parse_dt(landed) if landed else None
                if bound is not None and ldt is not None and ldt > bound:
                    rep.v(name, "future-landed", BI_REL, lineno,
                          f"landed date {landed} is later than the bound "
                          f"{ctx['bound_iso']} (V5)")
    rep.count(name, n_cand, n_eval)


def check_return_pass(rep: Report, src: Src, ctx: dict) -> None:
    name = "return-pass"
    ledger = src.read_text(LEDGER_REL)
    if ledger is None:
        rep.count(name, 0, 0)
        return
    lines = ledger.splitlines()
    start = next(
        (
            i
            for i, ln in enumerate(lines)
            if re.match(r"^###\s+RETURN PASS\s+—\s+current", ln)
        ),
        -1,
    )
    header, rows = first_table(lines, start)
    if not header:
        rep.count(name, 0, 0)
        rep.v(name, "table-missing", LEDGER_REL, 0,
              "`### RETURN PASS — current` has no table (V6)")
        return
    rep.count(name, len(rows), len(rows))
    keys = {
        c[0].strip().strip("*`")
        for _ln, c in rows
        if c and c[0].strip() not in ("—", "")
    }
    rp = lval(ledger, "returnPass")
    value = {t.strip() for t in rp.split(",") if t.strip() and "(" not in t}
    for t in sorted(value - keys):
        rep.v(name, "set-drift", LEDGER_REL, 0,
              f"returnPass: names {t} but the RETURN PASS — current table has "
              "no row keyed by it (V6)")
    for t in sorted(keys - value):
        rep.v(name, "set-drift", LEDGER_REL, 0,
              f"the RETURN PASS — current table keys a row on {t} but "
              "returnPass: does not name it (V6)")


def check_gate_decisions(rep: Report, src: Src, ctx: dict) -> None:
    name = "gate-decisions"
    ledger = src.read_text(LEDGER_REL)
    if ledger is None:
        rep.count(name, 0, 0)
        return
    bound = ctx["bound_dt"]
    gd_lineno, gd = section_text(lines=ledger.splitlines(),
                                 head_re=re.compile(r"^##\s+GATE DECISIONS"))
    if not gd:
        rep.count(name, 0, 0)
        return
    glines = gd.splitlines()
    # the `### Round <n>` subsection holding the strict table (appended last)
    rstart = next(
        (
            i
            for i, ln in enumerate(glines)
            if re.match(r"^###\s+Round\s+11\b", ln)
        ),
        -1,
    )
    if rstart < 0:
        rep.count(name, 0, 0)
        return
    header, rows = first_table(glines, rstart)
    # every row is judged — a column-count failure is an evaluation verdict,
    # not a skipped item
    rep.count(name, len(rows), len(rows))
    prev_date = ""
    prev_line = 0
    for lineno, cells in rows:
        ln = gd_lineno + lineno - 1
        if len(cells) != len(header):
            rep.v(name, "column-count", LEDGER_REL, ln,
                  f"GATE DECISIONS row has {len(cells)} cells, the header has "
                  f"{len(header)} — the 7-column form (V8)")
            continue
        hmap = dict(zip(header, cells))
        date_c = hmap.get("date", "")
        kind = re.sub(r"[\s`*]", "", hmap.get("kind", ""))
        answer = hmap.get(
            next((h for h in header if "answer" in h.lower()), ""), ""
        )
        if kind not in GATE_KINDS:
            rep.v(name, "kind-vocabulary", LEDGER_REL, ln,
                  f"GATE DECISIONS kind '{kind}' is not one of "
                  "decision | pre-authorization | confirmation | waiver | "
                  "correction (V8)")
        if not answer.strip().strip("*"):
            rep.v(name, "answer-empty", LEDGER_REL, ln,
                  "GATE DECISIONS answer cell is empty — the operator's "
                  "verbatim words are the record (V8)")
        elif not answer.strip().lstrip("*").startswith(('"', "“", "'")):
            rep.w(name, "answer-unquoted", LEDGER_REL, ln,
                  "GATE DECISIONS answer cell does not start with a quoted "
                  "verbatim (V8)")
        dt = parse_dt(date_c) if date_c else None
        if dt is None:
            rep.v(name, "date-unparseable", LEDGER_REL, ln,
                  f"GATE DECISIONS date cell '{date_c}' is not an ISO stamp (V8)")
        elif bound is not None and dt > bound:
            rep.v(name, "future-date", LEDGER_REL, ln,
                  f"GATE DECISIONS date {date_c} is later than the bound "
                  f"{ctx['bound_iso']} (V8)")
        if prev_date and dt is not None and parse_dt(prev_date) is not None:
            if dt < parse_dt(prev_date):
                rep.w(name, "append-order", LEDGER_REL, ln,
                      f"GATE DECISIONS date {date_c} is earlier than the "
                      f"previous row's {prev_date} (line {prev_line}) — rows "
                      "append at the end, newest last (V8)")
        if dt is not None:
            prev_date, prev_line = date_c, ln
    # pre-authorization rows must carry expires:/voided-by: (checked on the raw
    # row text, which may span the consequence cell's prose)
    for lineno, cells in rows:
        if len(cells) != len(header):
            continue
        hmap = dict(zip(header, cells))
        kind = re.sub(r"[\s`*]", "", hmap.get("kind", ""))
        if kind == "pre-authorization":
            raw = " ".join(cells)
            if "expires:" not in raw or "voided-by:" not in raw:
                rep.v(name, "preauth-scope", LEDGER_REL,
                      gd_lineno + lineno - 1,
                      "a pre-authorization row lacks expires: and/or voided-by: "
                      "(scoped pre-authorization, V8)")
    # appended at the end: no table follows the Round-11 table inside the
    # GATE DECISIONS section (the table is a contiguous `|` block)
    tail = glines[rstart:]
    tstart = next((i for i, ln in enumerate(tail) if ln.startswith("|")), -1)
    if tstart >= 0:
        tend = tstart
        while tend < len(tail) and tail[tend].startswith("|"):
            tend += 1
        if any(ln.startswith("|") for ln in tail[tend:]):
            rep.v(name, "append-position", LEDGER_REL, 0,
                  "a table follows the Round-11 GATE DECISIONS table inside "
                  "the section — rows append at the section end (V8)")


def check_orient_probe(rep: Report, src: Src, ctx: dict) -> None:
    name = "orient-probe"
    ledger = src.read_text(LEDGER_REL)
    if ledger is None:
        rep.count(name, 0, 0)
        return
    head_b = len(orient_text(ledger).encode())
    lines = ledger.splitlines()
    # current RETURN PASS block (### heading preferred, else the ## section).
    # `### RETURN PASS — current` is a *sub* heading, so `section_text` (which
    # only scans `## ` headings via H2_RE) can never start on it — slice it
    # directly: the heading line through the line before the next `##`-level
    # heading. The `## RETURN PASS` fallback keeps older trees measurable.
    rp_b = 0
    rp_start = next(
        (
            i
            for i, ln in enumerate(lines)
            if re.match(r"^###\s+RETURN PASS\s+—\s+current", ln)
        ),
        None,
    )
    if rp_start is not None:
        rp_end = next(
            (
                i
                for i in range(rp_start + 1, len(lines))
                if re.match(r"^#{2,}\s", lines[i])
            ),
            len(lines),
        )
        rp_b = len("\n".join(lines[rp_start:rp_end]).encode())
    else:
        _ln, block = section_text(lines, re.compile(r"^##\s+RETURN PASS"))
        if block:
            rp_b = len(block.encode())
    # last three PHASE LOG entries (entry = bullet + continuation lines)
    recs = phase_log_entries(ledger)
    last3_b = sum(r["size"] for r in recs[-3:])
    # the next row's manifest line + its contract head
    nt_b = 0
    nt = (lval(ledger, "nextTicket") or "").split(" ")[0]
    nt_resolved = False
    mrows = ctx.get("manifest_rows")
    if mrows is None:
        manifest = src.read_text(ctx["manifest_rel"]) or ""
        mrows = manifest_rows(manifest)
    row = next((r for r in mrows if r["ticket"] == nt), None)
    if row is not None:
        nt_resolved = True
        manifest = src.read_text(ctx["manifest_rel"]) or ""
        mlines = manifest.splitlines()
        if 0 < row["line"] <= len(mlines):
            nt_b += len(mlines[row["line"] - 1].encode()) + 1
        head = src.read_text(f"docs/tickets/{row['file']}")
        if head is not None:
            head_lines: list[str] = []
            for ln in head.splitlines():
                if H2_RE.match(ln):
                    break
                head_lines.append(ln)
            nt_b += len("\n".join(head_lines).encode()) + 1
    elif nt in ("DONE", "SETUP"):
        nt_resolved = True
    rep.count(name, 4, 4 if nt_resolved else 3)
    if not nt_resolved and nt:
        rep.v(name, "next-unresolved", LEDGER_REL, 0,
              f"nextTicket '{nt}' does not resolve to a manifest chain row — "
              "the orient probe cannot read the next row (V11)")
    total = head_b + rp_b + last3_b + nt_b
    if total > PROBE_MAX:
        rep.v(name, "probe-budget", LEDGER_REL, 0,
              f"orient recipe reads {total} B (> 48 KiB: head {head_b} · "
              f"RETURN PASS {rp_b} · last 3 entries {last3_b} · next row "
              f"{nt_b}) (V11)")
    ctx["probe_bytes"] = total


def check_run_harness(rep: Report, src: Src, ctx: dict) -> None:
    name = "run-harness"
    files = sorted(
        f
        for f in src.files()
        if f.startswith("docs/build/runs/") and f.endswith(".md")
    )
    adds = ctx.get("adds", {})
    before = ctx.get("before", set())
    marker_state = ctx.get("marker_state", "none")
    cand = evald = 0
    for rel in files:
        if not created_after_marker(rel, adds, before, marker_state):
            continue
        cand += 1
        text = src.read_text(rel)
        if text is None:
            continue  # offered but unreadable — never evaluated
        # a judged ledger is evaluated; a missing/malformed Harness line is the
        # violation verdict, not a skip
        evald += 1
        ok = bool(
            re.search(
                r"(?m)^\s*(-\s*)?(\*\*)?Harness:\s*[*`]{0,2}\s*"
                r"[a-z0-9._-]+/[a-z0-9._-]+/[a-z0-9._-]+",
                text,
            )
        )
        if not ok:
            rep.v(name, "harness-missing", rel, 0,
                  f"run ledger {rel} has no 'Harness: <harness>/<model-id>/"
                  "<tier>' header line (BM-HARNESS-01, V12)")
    rep.count(name, cand, evald)


def check_manifest_rounds(rep: Report, src: Src, ctx: dict) -> None:
    name = "manifest-rounds"
    mrows = ctx.get("manifest_rows")
    if mrows is None:
        manifest = src.read_text(ctx["manifest_rel"]) or ""
        mrows = manifest_rows(manifest)
    rep.count(name, len(mrows), len(mrows))
    seen: dict[str, dict] = {}
    for r in mrows:
        tid = r["ticket"]
        if not tid:
            continue
        if tid in seen:
            prev = seen[tid]
            # GL-META-00 Lane-B re-run rows share the original contract's id by
            # design (the six documented manifest/duplicate-file pairs in
            # reconciliations.json). The no-reuse rule binds the Round-11 chain
            # (seq ≥ 201); earlier pairs warn.
            strict = prev["seq_num"] >= 201 and r["seq_num"] >= 201
            emit = rep.v if strict else rep.w
            emit(name, "id-reused", ctx["manifest_rel"], r["line"],
                 f"ticket id {tid} appears on chain rows {prev['line']} and "
                 f"{r['line']} — ids are never reused (V13)"
                 + ("" if strict else " (Lane-B re-run row, documented)"))
        else:
            seen[tid] = r
        numbered = re.match(r"Round\s+\d+", r["banner"]) is not None
        if not numbered:
            emit = rep.v if r["seq_num"] >= BANNER_STRICT_SEQ else rep.w
            emit(name, "round-banner", ctx["manifest_rel"], r["line"],
                 f"chain row {r['seq']} ({tid}) sits under banner "
                 f"'{r['banner'][:60] or '(none)'}', not a numbered "
                 "'### Round <n>' banner (V13)"
                 + ("" if r["seq_num"] >= BANNER_STRICT_SEQ else " (pre-banner history)"))


CHECKS: list[Check] = [
    Check("orient-budget"),
    Check("current-state"),
    Check("named-paths"),
    Check("stale-tokens"),
    Check("ticket-counts"),
    Check("phase-log", floor=0.5),
    Check("phase-log-done", floor=0.5),
    Check("build-index"),
    Check("return-pass"),
    Check("gate-decisions"),
    Check("orient-probe"),
    Check("run-harness"),
    Check("manifest-rounds"),
]


# B3 §6's base kind vocabulary plus the Round-11 working kinds — kept identical
# to the committed record_policy/phase_log_kinds.txt so a replay over commits
# that predate the policy file judges with the same vocabulary (the file itself
# only ever extends the set at runtime).
DEFAULT_KINDS = {
    "done", "blocked", "inserted", "split", "gate", "pause", "round",
    "correction", "restored", "ticket", "post-closeout record",
    "post-closeout repair", "orchestrator repair", "interruption",
    "harness-switch",
}


def load_kinds(src: Src) -> set[str]:
    raw = src.read_text(KINDS_REL)
    kinds = set(DEFAULT_KINDS)
    if raw is not None:
        for ln in raw.splitlines():
            ln = re.sub(r"\s+#.*$", "", ln).strip()
            if ln and not ln.startswith("#"):
                kinds.add(ln)
    return kinds


def run_checks(src: Src, ctx: dict) -> Report:
    rep = Report()
    check_orient_budget(rep, src, ctx)
    check_current_state(rep, src, ctx)
    check_named_paths(rep, src, ctx)
    check_stale_tokens(rep, src, ctx)
    check_ticket_counts(rep, src, ctx)
    kinds = load_kinds(src)
    check_phase_log(rep, src, ctx, kinds)
    check_phase_log_done(rep, src, ctx)
    check_build_index(rep, src, ctx)
    check_return_pass(rep, src, ctx)
    check_gate_decisions(rep, src, ctx)
    check_orient_probe(rep, src, ctx)
    check_run_harness(rep, src, ctx)
    check_manifest_rounds(rep, src, ctx)
    return rep


def verdict(rep: Report) -> tuple[int, list[str]]:
    """(exit code, vacuous check names). Vacuous wins over violations: a check
    that evaluated none of a non-empty set could not have run at all (G11)."""
    vacuous = [
        c.name
        for c in CHECKS
        if rep.counts.get(c.name, [0, 0])[0] > 0
        and rep.counts[c.name][1] == 0
    ]
    if vacuous:
        return EXIT_VACUOUS, vacuous
    import math

    underfloor = [
        c.name
        for c in CHECKS
        if rep.counts.get(c.name, [0, 0])[0] > 0
        and rep.counts[c.name][1] < math.ceil(rep.counts[c.name][0] * c.floor)
    ]
    for name in underfloor:
        cand, ev = rep.counts.get(name, [0, 0])
        rep.findings.append(
            Finding(name, "parse-floor", "", 0,
                    f"{name}: only {ev} of {cand} candidates evaluated — below "
                    "the declared parse floor (G11)", "error")
        )
    viol = [f for f in rep.findings if f.severity == "error"]
    return (EXIT_VIOLATIONS if viol else EXIT_OK), []


def emit(rep: Report, meta: dict, json_path: str | None, title: str) -> int:
    code, vacuous = verdict(rep)
    viol = [f for f in rep.findings if f.severity == "error"]
    warn = [f for f in rep.findings if f.severity == "warning"]
    checks = []
    for c in CHECKS:
        cand, ev = rep.counts.get(c.name, [0, 0])
        checks.append(
            {
                "check": c.name,
                "candidates": cand,
                "evaluated": ev,
                "floor": c.floor,
                "violations": [f.as_json() for f in viol if f.check == c.name],
                "warnings": [f.as_json() for f in warn if f.check == c.name],
            }
        )
    doc = {
        "schema": SCHEMA,
        "tool": "docs/build/tools/ledger_contract.py",
        "input": meta,
        "summary": {"violations": len(viol), "warnings": len(warn), "exit": code},
        "checks": checks,
        "extra": rep.extra,
        "exit": code,
    }
    print(title)
    if vacuous:
        print(
            f"  ? vacuous: {', '.join(vacuous)} evaluated none of a non-empty "
            "candidate set (G11) — not green"
        )
    elif viol:
        print(f"  ✗ {len(viol)} violation(s), {len(warn)} warning(s):")
        for f in viol[:20]:
            loc = f"{f.path}:{f.line}" if f.line else f.path
            print(f"    {loc}  [{f.rule}] {f.message}")
        if len(viol) > 20:
            print(f"    … and {len(viol) - 20} more")
    else:
        n = sum(rep.counts.get(c.name, [0, 0])[1] for c in CHECKS)
        print(f"  ✓ no violations ({len(warn)} warning(s); {n} item(s) evaluated)")
    for c in CHECKS:
        cand, ev = rep.counts.get(c.name, [0, 0])
        print(f"    {c.name:18} candidates {cand} evaluated {ev} floor {c.floor}")
    if json_path:
        pathlib.Path(json_path).write_text(json.dumps(doc, indent=2) + "\n")
        print(f"  JSON: {json_path}")
    return code


def build_ctx(repo: pathlib.Path, git: Git | None, at: str | None, now: str | None) -> dict:
    if at:
        if git is None:
            raise UsageError("--at needs a git repository")
        epoch = git.committer_epoch(at)
        bound = datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc)
        bound_iso = bound.strftime("%Y-%m-%dT%H:%M:%SZ")
    elif now:
        bound = parse_dt(now)
        if bound is None:
            raise UsageError(f"--now '{now}' is not an ISO-8601 timestamp")
        bound_iso = now
    else:
        bound = utc_now()
        bound_iso = bound.strftime("%Y-%m-%dT%H:%M:%SZ")
    ctx: dict[str, object] = {
        "bound_dt": bound,
        "bound_iso": bound_iso,
        "manifest_rel": "docs/tickets/00_MANIFEST.md",
    }
    if git is not None:
        marker = git.marker_commit(at or "HEAD")
        if marker:
            ctx["marker_state"] = "committed"
            ctx["before"] = git.ancestors(marker) - {marker}
        else:
            ctx["marker_state"] = "uncommitted"
            ctx["before"] = set()
        ctx["adds"] = git.first_added(
            at or "HEAD", "docs/build/runs", "docs/build/readouts", "docs/adr"
        )
    else:
        ctx["marker_state"] = "none"
        ctx["before"] = set()
        ctx["adds"] = {}
    return ctx


def cmd_check(args: argparse.Namespace) -> int:
    repo = pathlib.Path(args.repo).resolve()
    git = Git(repo)
    try:
        ctx = build_ctx(repo, git, args.at, args.now)
    except UsageError as e:
        print(f"ledger_contract: {e}", file=sys.stderr)
        return EXIT_USAGE
    src: Src = RevSrc(git, args.at) if args.at else TreeSrc(repo)
    if src.read_text(LEDGER_REL) is None:
        print(
            f"ledger_contract: {LEDGER_REL} not found"
            + (f" at {args.at}" if args.at else ""),
            file=sys.stderr,
        )
        return EXIT_USAGE
    rep = run_checks(src, ctx)
    meta = {
        "repo": str(repo),
        "at": args.at or "worktree",
        "bound": ctx["bound_iso"],
        "input_digest": "",
    }
    return emit(rep, meta, args.json,
                f"ledger-contract check ({'@' + args.at if args.at else 'worktree'})")


def cmd_replay(args: argparse.Namespace) -> int:
    repo = pathlib.Path(args.repo).resolve()
    git = Git(repo)
    try:
        commits = git.first_parents(args.span)
    except UsageError as e:
        print(f"ledger_contract: {e}", file=sys.stderr)
        return EXIT_USAGE
    if not commits:
        print(
            f"ledger_contract: replay span '{args.span}' is empty — a vacuous "
            "span is not green (G11)",
            file=sys.stderr,
        )
        return EXIT_VACUOUS
    total = Report()
    per_commit: list[dict] = []
    for rev in commits:
        try:
            ctx = build_ctx(repo, git, rev, None)
        except UsageError as e:
            print(f"ledger_contract: {e}", file=sys.stderr)
            return EXIT_USAGE
        src = RevSrc(git, rev)
        if src.read_text(LEDGER_REL) is None:
            continue
        rep = run_checks(src, ctx)
        code, vacuous = verdict(rep)
        viol = sum(1 for f in rep.findings if f.severity == "error")
        warn = sum(1 for f in rep.findings if f.severity == "warning")
        per_commit.append(
            {
                "commit": rev,
                "exit": code,
                "violations": viol,
                "warnings": warn,
                "vacuous": vacuous,
                "counts": {
                    c.name: rep.counts.get(c.name, [0, 0]) for c in CHECKS
                },
            }
        )
        for f in rep.findings:
            f.message = f"{rev[:8]}: {f.message}"
        total.findings.extend(rep.findings)
        for name, (cand, ev) in rep.counts.items():
            total.count(name, cand, ev)
    if not per_commit:
        print(
            f"ledger_contract: replay span '{args.span}' judged no commits with "
            "a LEDGER — a vacuous span is not green (G11)",
            file=sys.stderr,
        )
        return EXIT_VACUOUS
    total.extra["per_commit"] = per_commit
    meta = {"repo": str(repo), "span": args.span, "commits": len(per_commit)}
    return emit(total, meta, args.json,
                f"ledger-contract replay ({args.span}, {len(per_commit)} commit(s))")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check", help="judge one tree (worktree or --at REV)")
    p.add_argument("--repo", default=str(ROOT))
    p.add_argument("--at", default=None, help="git rev to read instead of the worktree")
    p.add_argument("--now", default=None, help="clock bound (ISO-8601); tree mode only")
    p.add_argument("--json", default=None)
    p.set_defaults(fn=cmd_check)
    p = sub.add_parser("replay", help="judge every first-parent commit of a span")
    p.add_argument("span")
    p.add_argument("--repo", default=str(ROOT))
    p.add_argument("--json", default=None)
    p.set_defaults(fn=cmd_replay)
    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except UsageError as e:
        print(f"ledger_contract: {e}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
