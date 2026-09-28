#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Strict, read-only parser + discrepancy report for build-memory control files
(P32.1 / SIG-MEM-001).

Parses the current-obligation surfaces — the manifest chain table, ``LEDGER.md``
CURRENT STATE + PHASE LOG, ``DEFERRALS.md``, ``COVERAGE_MATRIX.csv`` and the ADR
set/index/spec supersession references — and emits structured diagnostics:
``{check, severity, file, obligation, evidence, message}``. Severities are
``error`` (structural violation) and ``conflict`` (ambiguous or unreconciled
state that needs a recorded reconciliation — ambiguity stays open, never
silently resolved).

This tool is **read-only**: it never writes or mutates any repo file. Report
destinations are caller-provided (``--json-out`` / ``--md-out``) — there is no
shared default output path, so two worktrees can validate concurrently without
clobbering each other's report. The report records the SHA-256 of every input
file so a stale report cannot masquerade as fresh.

This is a docs tool invoked in the PR, not a ``make check`` step. Standard
library only; run from anywhere:

    python3 docs/build/tools/audit_current_state.py
    python3 docs/build/tools/audit_current_state.py --json-out report.json --md-out report.md

Exit codes: 0 clean · 1 errors or conflicts present · 2 usage error / not a
build-memory repo (no ``docs/build/README.md`` ``build-memory: v2`` marker).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

# Single source of truth for the coverage enums/spec-id grammar (P19.2).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_coverage_matrix  # noqa: E402

EXPECTED_KEYS = (
    "projectStatus nextTicket lastCompleted blockedOn pauseRequested returnPass "
    "manifest canonicalSpec memoryRoot dispatchTarget buildWorktree buildBranchBase "
    "pinnedBaseSha chainTip benchmarkSet autonomy mergePolicy round updatedAt"
).split()

MARKER = "<!-- build-memory: v2 -->"
OWED_STATUSES = frozenset({"OPEN", "PARTIAL"})
TERMINAL_STATUSES = frozenset({"DONE", "WONTFIX", "ACCEPTED-SKELETON"})
VALID_STATUSES = OWED_STATUSES | TERMINAL_STATUSES

# An obligation id heads a `| D-… |` row: `D-` + dotted segments + `-` + suffix.
# `D-P31.1-1`, `D-R10-HUMAN-1`, `D-P27-SPEC-1`, `D-R6.1-EVAL` are all valid.
DEFERRAL_ID_RE = re.compile(r"^D-[A-Z0-9][A-Za-z0-9]*(\.[A-Za-z0-9]+)*(-[A-Za-z0-9]+)+$")
# A first cell that *intends* an obligation id (case-insensitive D- token) — the
# strict anchor, so a malformed id is flagged rather than silently skipped.
DEFERRAL_CELL_RE = re.compile(r"^\|\s*([Dd]-[^|\s]*)\s*\|")
# A first cell that *references* an obligation id (backticked) — a cross-ref
# table row, not a new obligation; the referenced id must exist.
DEFERRAL_XREF_RE = re.compile(r"^\|\s*`(D-[A-Za-z0-9._-]+)`\s*\|")
BL_HOME_RE = re.compile(r"BL-\d{3}")
DATED_TERMINAL_RE = re.compile(
    r"\b(DONE|WONTFIX|ACCEPTED-SKELETON)\s+20\d\d-"
    # P33.1: the same dated-terminal class written as `P31.x (2026-09-25): DONE` —
    # eight Round-9 rows recorded verified DONEs inside an owed-leading cell and
    # sailed through both this audit and obligation_events.parse_obligation_rows
    # as clean OPEN (the parenthesised date precedes the status word). Match the
    # `(YYYY-MM-DD): TERMINAL` shape too so the word order cannot hide the
    # disagreement. obligation_events.py reuses this compiled pattern.
    r"|\(20\d\d-\d\d-\d\d\)\s*:\s*\*{0,2}\s*(DONE|WONTFIX|ACCEPTED-SKELETON)\b"
)

# Ticket ids that can appear in a `Depends on:` line. `D-*`/`BL-*`/`HG-*`/`GL-*`/
# `ADR-*`/`SIG-*`/`RISK-*` tokens are stripped first so `D-FEDERAL.1-1` cannot be
# misread as a dependency on `FEDERAL.1`.
NON_DEP_TOKEN_RE = re.compile(r"\b(?:D|BL|HG|GL|LD|ADR|RISK|SIG|LLM|OCI|URL|TLA)-[A-Za-z0-9._-]+")
DEP_ID_RE = re.compile(
    r"P\d+\.\d+[a-z]?"
    r"|HUMAN-H\d+"
    r"|GATE-G\d+"
    r"|GATE-ACCEPT"
    r"|[A-Z]{2,}[0-9]*\.[0-9]+[a-z]?"
)
SEMANTIC_ID_RE = re.compile(r"\*\*Semantic id:\*\*\s*`?([A-Z][A-Za-z0-9.]*)\b")
FILENAME_ID_RE = re.compile(r"^(\d{2,3}[a-z]?_)?(.+?)__[^_].*\.md$")
# Admissible routing sentinels that are not chain-ticket ids.
ROUTING_SENTINELS = frozenset({"—", "accepted"})
SCOPED_ROUTING_RE = re.compile(r"^P\d+\.\d+:.+$")
PHASE_LOG_DONE_RE = re.compile(r"^-\s*\d{4}-\d{2}-\d{2}\s*—\s*(?:\*\*)?([A-Za-z][A-Za-z0-9.-]*)")


def diag(
    check: str,
    severity: str,
    file: str,
    obligation: str,
    evidence: str,
    message: str,
) -> dict:
    return {
        "check": check,
        "severity": severity,
        "file": file,
        "obligation": obligation,
        "evidence": evidence,
        "message": message,
    }


def _rel(root: pathlib.Path, path: pathlib.Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── manifest ─────────────────────────────────────────────────────────────────


def parse_manifest(root: pathlib.Path, diags: list[dict]) -> dict:
    """Parse the chain table. Returns rows (seq, filename), companions and the
    id→seq map derived from **manifest order** — not the filename prefix, so a
    legacy-named ticket keeps its true chain position."""
    manifest = root / "docs/tickets/00_MANIFEST.md"
    rows: list[tuple[str, str]] = []
    companions: set[str] = {"_TEMPLATE.md", "DEFERRALS.md", "00_MANIFEST.md"}
    if not manifest.is_file():
        diags.append(
            diag(
                "manifest/missing",
                "error",
                "docs/tickets/00_MANIFEST.md",
                "",
                "",
                "manifest file not found",
            )
        )
        return {"rows": rows, "companions": companions, "id_to_seq": {}, "file_to_seq": {}}
    text = manifest.read_text()
    m = re.search(r"(?im)^\s*companions:\s*(.+)$", text)
    if m:
        companions.update(
            t.strip("` ") for t in m.group(1).split(",") if t.strip("` ").endswith(".md")
        )
    in_chain = False
    seen_seq: dict[str, str] = {}
    seen_file: dict[str, str] = {}
    for lineno, line in enumerate(text.splitlines(), 1):
        if re.match(r"^##\s+The chain", line):
            in_chain = True
            continue
        # subsections (`### …`) inside the chain table do not end it
        if in_chain and re.match(r"^## (?!#)", line):
            in_chain = False
        if not in_chain or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        first = cells[0] if cells else ""
        if first in ("#", "---", "") or set(first) <= {"-"}:
            continue
        if not re.fullmatch(r"\d+[a-z]?", first):
            diags.append(
                diag(
                    "manifest/malformed-row",
                    "error",
                    "docs/tickets/00_MANIFEST.md",
                    "",
                    f"line {lineno}",
                    f"chain row {lineno} has a non-numeric sequence cell {first!r}",
                )
            )
            continue
        files = re.findall(r"[0-9A-Za-z_.-]+\.md", line)
        if not files:
            diags.append(
                diag(
                    "manifest/malformed-row",
                    "error",
                    "docs/tickets/00_MANIFEST.md",
                    first,
                    f"line {lineno}",
                    f"chain row {first} names no *.md ticket file",
                )
            )
            continue
        fname = files[0]
        if first in seen_seq:
            diags.append(
                diag(
                    "manifest/duplicate-sequence",
                    "error",
                    "docs/tickets/00_MANIFEST.md",
                    first,
                    f"lines {seen_seq[first]} & {lineno}",
                    f"sequence {first} appears twice in the chain table",
                )
            )
        else:
            seen_seq[first] = str(lineno)
        if fname in seen_file:
            diags.append(
                diag(
                    "manifest/duplicate-file",
                    "conflict",
                    "docs/tickets/00_MANIFEST.md",
                    fname,
                    f"lines {seen_file[fname]} & {lineno}",
                    f"ticket file {fname} appears at two chain positions — verify a documented "
                    f"pointer row (e.g. a Lane-B re-run row) vs an authoring error",
                )
            )
        else:
            seen_file[fname] = str(lineno)
        rows.append((first, fname))
    # Chain order is the *physical* row order in the table, not the `#` cell —
    # inserted tickets (P30.2a/P30.2b) keep stable row numbers while sitting
    # physically earlier (manifest RENUMBER/Plan-extensions notes).
    id_to_seq: dict[str, int] = {}
    file_to_seq: dict[str, int] = {}
    id_to_num: dict[str, int] = {}
    for pos, (seq, fname) in enumerate(rows, 1):
        file_to_seq.setdefault(fname, pos)
        m2 = FILENAME_ID_RE.match(fname)
        if m2:
            tid = m2.group(2)
            id_to_seq.setdefault(tid, pos)
            id_to_num.setdefault(tid, int(seq.rstrip("abcdefghijklmnopqrstuvwxyz")))
    return {
        "rows": rows,
        "companions": companions,
        "id_to_seq": id_to_seq,
        "id_to_num": id_to_num,
        "file_to_seq": file_to_seq,
    }


# ── ticket files + Depends on ────────────────────────────────────────────────


def parse_tickets(root: pathlib.Path, manifest: dict, diags: list[dict]) -> dict:
    tickets = root / "docs/tickets"
    companions = manifest["companions"]
    id_to_seq = dict(manifest["id_to_seq"])
    file_to_seq = manifest["file_to_seq"]
    # semantic-id aliases (e.g. `CI.1`, `DEPLOY.1`) → the same chain position.
    for fname, seq in file_to_seq.items():
        path = tickets / fname
        if path.is_file():
            sm = SEMANTIC_ID_RE.search(path.read_text())
            if sm:
                id_to_seq.setdefault(sm.group(1), seq)
    chain_files = {fname for _, fname in manifest["rows"]}
    for fname in chain_files:
        if not (tickets / fname).is_file():
            diags.append(
                diag(
                    "manifest/missing-file",
                    "error",
                    "docs/tickets/00_MANIFEST.md",
                    fname,
                    f"chain row for {fname}",
                    f"manifest names {fname} but no such file exists in docs/tickets/",
                )
            )
    if tickets.is_dir():
        for path in sorted(tickets.glob("*.md")):
            if path.name in companions or path.name == "00_MANIFEST.md":
                continue
            if path.name not in chain_files:
                diags.append(
                    diag(
                        "tickets/orphan-file",
                        "error",
                        _rel(root, path),
                        path.name,
                        "",
                        f"ticket file {path.name} has no row in the manifest chain table",
                    )
                )
    # Depends on — resolved against manifest order (legacy filenames cannot hide
    # a forward dependency behind sequence 0).
    for fname in sorted(chain_files):
        path = tickets / fname
        if not path.is_file():
            continue
        my_seq = file_to_seq[fname]
        dep_line = ""
        for line in path.read_text().splitlines():
            if re.search(r"Depends on:", line):
                dep_line = line.split("Depends on:", 1)[1]
                break
        cleaned = NON_DEP_TOKEN_RE.sub(" ", dep_line)
        candidates = DEP_ID_RE.findall(cleaned)
        for dep in sorted(set(candidates)):
            dep_seq = id_to_seq.get(dep)
            if dep_seq is None:
                if re.fullmatch(r"P\d+\.\d+[a-z]?", dep):
                    diags.append(
                        diag(
                            "tickets/dependency-not-in-chain",
                            "conflict",
                            _rel(root, path),
                            dep,
                            dep_line.strip()[:120],
                            f"{fname} names {dep} in 'Depends on:' but {dep} has no chain row "
                            f"(prose context or a stale reference — needs recorded reconciliation)",
                        )
                    )
                continue
            if dep_seq > my_seq:
                diags.append(
                    diag(
                        "tickets/forward-dependency",
                        "error",
                        _rel(root, path),
                        dep,
                        dep_line.strip()[:120],
                        f"{fname} (chain row {my_seq}) depends on {dep} (chain row {dep_seq}) "
                        f"which lands later",
                    )
                )
    return {"id_to_seq": id_to_seq}


# ── DEFERRALS.md ─────────────────────────────────────────────────────────────


def parse_deferrals(root: pathlib.Path, diags: list[dict]) -> list[dict]:
    path = root / "docs/tickets/DEFERRALS.md"
    obligations: list[dict] = []
    if not path.is_file():
        return obligations
    seen: dict[str, int] = {}
    readouts = root / "docs/build/readouts"
    passed_gates: set[str] = set()
    if readouts.is_dir():
        for ro in readouts.glob("GATE-*.md"):
            if re.search(r"(?im)verdict:?\s*PASSED|^PASSED|\bPASSED\b", ro.read_text()):
                passed_gates.add(ro.stem)
    xrefs: list[tuple[str, int]] = []
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        xm = DEFERRAL_XREF_RE.match(line)
        if xm:
            xrefs.append((xm.group(1), lineno))
            continue
        m = DEFERRAL_CELL_RE.match(line)
        if not m:
            continue
        oid = m.group(1).rstrip("`*.,;:)")
        if not DEFERRAL_ID_RE.match(oid):
            diags.append(
                diag(
                    "deferrals/malformed-id",
                    "error",
                    "docs/tickets/DEFERRALS.md",
                    m.group(1),
                    f"line {lineno}",
                    f"row {lineno} first cell {m.group(1)!r} is not a well-formed obligation id",
                )
            )
            continue
        cells = [c.strip() for c in line.split("|")]
        last = cells[-2] if len(cells) >= 2 else ""
        words = last.split()
        status = words[0].upper() if words else ""
        if status not in VALID_STATUSES:
            diags.append(
                diag(
                    "deferrals/malformed-status",
                    "error",
                    "docs/tickets/DEFERRALS.md",
                    oid,
                    f"line {lineno}: {last[:80]!r}",
                    f"row {oid} status cell begins {status!r} — not a valid status",
                )
            )
        if oid in seen:
            diags.append(
                diag(
                    "deferrals/duplicate-id",
                    "error",
                    "docs/tickets/DEFERRALS.md",
                    oid,
                    f"lines {seen[oid]} & {lineno}",
                    f"obligation id {oid} heads two rows",
                )
            )
        else:
            seen[oid] = lineno
        if status in OWED_STATUSES:
            hit = DATED_TERMINAL_RE.search(last)
            if hit:
                diags.append(
                    diag(
                        "deferrals/status-conflict",
                        "conflict",
                        "docs/tickets/DEFERRALS.md",
                        oid,
                        f"line {lineno}: leading {status!r} vs {hit.group(0)!r}",
                        f"{oid} leads {status} but its status cell later records {hit.group(0)} — "
                        f"mechanical readers and the prose disagree; ambiguity stays open until a "
                        f"recorded reconciliation (no silent last-token-wins)",
                    )
                )
            if not BL_HOME_RE.search(line):
                diags.append(
                    diag(
                        "deferrals/no-backlog-home",
                        "error",
                        "docs/tickets/DEFERRALS.md",
                        oid,
                        f"line {lineno}",
                        f"owed row {oid} cites no BL-nnn backlog home",
                    )
                )
            for g in passed_gates:
                if g in line:
                    diags.append(
                        diag(
                            "deferrals/open-vs-passed-gate",
                            "error",
                            "docs/tickets/DEFERRALS.md",
                            oid,
                            f"line {lineno}",
                            f"owed row {oid} references {g} whose readout says PASSED",
                        )
                    )
        obligations.append({"id": oid, "status": status, "line": lineno})
    ids = {o["id"] for o in obligations}
    for oid, lineno in xrefs:
        if oid not in ids:
            diags.append(
                diag(
                    "deferrals/crossref-unresolvable",
                    "conflict",
                    "docs/tickets/DEFERRALS.md",
                    oid,
                    f"line {lineno}",
                    f"cross-reference row names `{oid}` but no obligation row carries that id",
                )
            )
    return obligations


# ── LEDGER.md ────────────────────────────────────────────────────────────────


def _lval(text: str, key: str) -> str:
    m = re.search(rf"(?m)^\s*{re.escape(key)}:\s*(.*?)\s*$", text)
    if not m:
        return ""
    return re.sub(r"\s*#.*$", "", m.group(1)).strip()


def parse_ledger(root: pathlib.Path, manifest: dict, diags: list[dict]) -> dict:
    path = root / "docs/build/LEDGER.md"
    if not path.is_file():
        return {}
    text = path.read_text()
    blk = re.search(r"(?ms)^##\s+CURRENT STATE.*?^```\s*$(.*?)^```", text)
    body = blk.group(1) if blk else text
    got = [
        re.sub(r":.*$", "", ln).strip()
        for ln in body.splitlines()
        if re.match(r"^\s*[A-Za-z][A-Za-z0-9]*:(\s|$)", ln)
    ]
    if got != EXPECTED_KEYS:
        diags.append(
            diag(
                "ledger/key-order",
                "error",
                "docs/build/LEDGER.md",
                "",
                " ".join(got)[:200],
                "CURRENT STATE keys are missing, extra or out of order",
            )
        )
    ids = manifest["id_to_seq"]
    num_of = manifest.get("id_to_num", {})
    index = _build_index_rows(root)
    nt = _lval(text, "nextTicket")
    if nt and nt not in ("DONE", "SETUP") and nt not in ids:
        diags.append(
            diag(
                "ledger/next-ticket",
                "error",
                "docs/build/LEDGER.md",
                nt,
                f"nextTicket: {nt}",
                f"nextTicket {nt!r} names no chain row, DONE or SETUP",
            )
        )
    lc = _lval(text, "lastCompleted")
    if lc:
        if lc not in ids:
            diags.append(
                diag(
                    "ledger/last-completed",
                    "conflict",
                    "docs/build/LEDGER.md",
                    lc,
                    f"lastCompleted: {lc}",
                    f"lastCompleted {lc!r} is not a chain row id",
                )
            )
        elif (lc_row := next((r for r in index if r["ticket"] == lc), None)) is None:
            diags.append(
                diag(
                    "ledger/last-completed",
                    "conflict",
                    "docs/build/LEDGER.md",
                    lc,
                    f"lastCompleted: {lc}",
                    f"lastCompleted {lc!r} has no BUILD_INDEX row",
                )
            )
        else:
            refs = [
                t.split("#", 1)[0].rstrip(".,;:")
                for t in re.findall(r"[\w./-]+\.md", lc_row.get("evidence", ""))
            ]
            if not refs or not any(
                (root / "docs/build" / t).is_file() or (root / t).is_file() for t in refs
            ):
                diags.append(
                    diag(
                        "ledger/last-completed",
                        "conflict",
                        "docs/build/LEDGER.md",
                        lc,
                        f"lastCompleted: {lc}",
                        f"lastCompleted {lc!r}'s BUILD_INDEX row names no existing evidence file",
                    )
                )
        if nt and nt not in ("DONE", "SETUP") and any(r["ticket"] == nt for r in index):
            diags.append(
                diag(
                    "ledger/next-landed",
                    "conflict",
                    "docs/build/LEDGER.md",
                    nt,
                    f"nextTicket {nt} already has a BUILD_INDEX row",
                    "the index runs ahead of CURRENT STATE — landed work recorded for a ticket the "
                    "ledger still calls next",
                )
            )
        if lc in num_of:
            ahead = [r for r in index if r["seq"] > num_of[lc]]
            for r in ahead:
                diags.append(
                    diag(
                        "ledger/index-ahead",
                        "conflict",
                        "docs/build/BUILD_INDEX.md",
                        r["ticket"],
                        f"index row {r['seq']} > lastCompleted seq {num_of[lc]}",
                        f"BUILD_INDEX row {r['seq']} ({r['ticket']}) lands after the ledger's "
                        f"lastCompleted {lc} — index and control state disagree",
                    )
                )
    # PHASE LOG "done" entries must have an index row whose evidence cell names
    # at least one file that exists (runs/, pr/, readouts/, reports/…). A gate
    # marker's evidence is its readout, not a runs/ file.
    for lineno, line in enumerate(text.splitlines(), 1):
        dm = PHASE_LOG_DONE_RE.match(line)
        if not dm or "done" not in line:
            continue
        tid = dm.group(1)
        if tid not in ids:
            continue
        row = next((r for r in index if r["ticket"] == tid), None)
        if row is None:
            diags.append(
                diag(
                    "ledger/done-uncovered",
                    "error",
                    "docs/build/LEDGER.md",
                    tid,
                    f"line {lineno}",
                    f"PHASE LOG marks {tid} done but BUILD_INDEX.md has no row for it",
                )
            )
            continue
        refs = [t.rstrip(".,;:") for t in re.findall(r"[\w./-]+\.md", row.get("evidence", ""))]
        refs = [t.split("#", 1)[0] for t in refs]
        if not refs or not any(
            (root / "docs/build" / t).is_file() or (root / t).is_file() for t in refs
        ):
            diags.append(
                diag(
                    "ledger/done-uncovered",
                    "error",
                    "docs/build/LEDGER.md",
                    tid,
                    f"line {lineno}",
                    f"PHASE LOG marks {tid} done but its BUILD_INDEX row names no "
                    f"existing evidence file ({row.get('evidence', '')[:80]!r})",
                )
            )
    return {"nextTicket": nt, "lastCompleted": lc}


def _build_index_rows(root: pathlib.Path) -> list[dict]:
    path = root / "docs/build/BUILD_INDEX.md"
    rows: list[dict] = []
    if not path.is_file():
        return rows
    for line in path.read_text().splitlines():
        m = re.match(r"^\|\s*(\d+)\s*\|\s*([A-Za-z][A-Za-z0-9.-]*)\s*\|", line)
        if m:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            rows.append({"seq": int(m.group(1)), "ticket": m.group(2), "evidence": cells[-1]})
    return rows


# ── COVERAGE_MATRIX.csv ──────────────────────────────────────────────────────


def parse_coverage(root: pathlib.Path, manifest: dict, diags: list[dict]) -> None:
    path = root / "docs/build/COVERAGE_MATRIX.csv"
    spec = root / "docs/2_canonical_design_spec.md"
    if not path.is_file() or not spec.is_file():
        return
    defined = check_coverage_matrix.spec_ids(spec)
    with path.open(newline="") as fh:
        rows = list(csv.reader(fh))
    if not rows:
        return
    if rows[0] != check_coverage_matrix.HEADER:
        diags.append(
            diag(
                "coverage/header",
                "error",
                "docs/build/COVERAGE_MATRIX.csv",
                "",
                ",".join(rows[0])[:160],
                "COVERAGE_MATRIX.csv header does not match the expected column set",
            )
        )
    data = rows[1:]
    seen: set[str] = set()
    ids: set[str] = set()
    chain_ids = set(manifest["id_to_seq"])
    for i, r in enumerate(data, 2):
        if len(r) < len(check_coverage_matrix.HEADER):
            diags.append(
                diag(
                    "coverage/malformed-row",
                    "error",
                    "docs/build/COVERAGE_MATRIX.csv",
                    "",
                    f"line {i}: {len(r)} cells",
                    f"coverage row {i} has {len(r)} cells",
                )
            )
            continue
        rid, level, _section, cls, verdict, _ev, _own, _tests, _adrs, _risk, routing, _note = r[:12]
        if not re.fullmatch(r"SIG-[A-Z]+-\d+[a-z]?", rid):
            diags.append(
                diag(
                    "coverage/malformed-id",
                    "error",
                    "docs/build/COVERAGE_MATRIX.csv",
                    rid,
                    f"line {i}",
                    f"coverage row {i} id {rid!r} is not a well-formed requirement id",
                )
            )
            continue
        if rid in seen:
            diags.append(
                diag(
                    "coverage/duplicate-id",
                    "error",
                    "docs/build/COVERAGE_MATRIX.csv",
                    rid,
                    f"line {i}",
                    f"requirement id {rid} has two coverage rows",
                )
            )
        seen.add(rid)
        ids.add(rid)
        if level not in check_coverage_matrix.LEVELS:
            diags.append(
                diag(
                    "coverage/enum",
                    "error",
                    "docs/build/COVERAGE_MATRIX.csv",
                    rid,
                    f"line {i}",
                    f"{rid}: level {level!r} not in the enum",
                )
            )
        if cls not in check_coverage_matrix.CLASSES:
            diags.append(
                diag(
                    "coverage/enum",
                    "error",
                    "docs/build/COVERAGE_MATRIX.csv",
                    rid,
                    f"line {i}",
                    f"{rid}: class {cls!r} not in the enum",
                )
            )
        if verdict not in check_coverage_matrix.VERDICTS:
            diags.append(
                diag(
                    "coverage/enum",
                    "error",
                    "docs/build/COVERAGE_MATRIX.csv",
                    rid,
                    f"line {i}",
                    f"{rid}: verdict {verdict!r} not in the enum",
                )
            )
        if (
            routing not in ROUTING_SENTINELS
            and routing not in chain_ids
            and not SCOPED_ROUTING_RE.match(routing)
        ):
            diags.append(
                diag(
                    "coverage/routing-unknown",
                    "error",
                    "docs/build/COVERAGE_MATRIX.csv",
                    rid,
                    f"line {i}: routing {routing!r}",
                    f"{rid}: routing {routing!r} is not a chain ticket, sentinel or scoped route",
                )
            )
        if verdict in check_coverage_matrix.NON_MET_VERDICTS and routing == "—":
            diags.append(
                diag(
                    "coverage/nonmet-unrouted",
                    "error",
                    "docs/build/COVERAGE_MATRIX.csv",
                    rid,
                    f"line {i}",
                    f"{rid}: non-MET verdict {verdict} but routing is '—'",
                )
            )
        if rid not in defined:
            diags.append(
                diag(
                    "coverage/undefined-id",
                    "error",
                    "docs/build/COVERAGE_MATRIX.csv",
                    rid,
                    f"line {i}",
                    f"{rid} is not defined in the canonical spec",
                )
            )
    missing = sorted(defined - ids)
    for rid in missing:
        diags.append(
            diag(
                "coverage/missing-id",
                "error",
                "docs/build/COVERAGE_MATRIX.csv",
                rid,
                "",
                f"spec-defined requirement {rid} has no coverage row",
            )
        )
    if len(defined) != len(ids):
        diags.append(
            diag(
                "coverage/count-mismatch",
                "conflict",
                "docs/build/COVERAGE_MATRIX.csv",
                "",
                f"spec defines {len(defined)} ids; CSV holds {len(ids)}",
                "coverage matrix and canonical spec disagree on the requirement universe — "
                "the dated assessment has not caught up with the spec (or vice versa)",
            )
        )


# ── ADRs ─────────────────────────────────────────────────────────────────────


def parse_adrs(root: pathlib.Path, diags: list[dict]) -> None:
    adr_dir = root / "docs/adr"
    spec = root / "docs/2_canonical_design_spec.md"
    if not adr_dir.is_dir():
        return
    files: dict[str, pathlib.Path] = {}
    for p in sorted(adr_dir.glob("ADR-*.md")):
        m = re.match(r"(ADR-\d{3})", p.name)
        if not m:
            continue
        num = m.group(1)
        if num in files:
            diags.append(
                diag(
                    "adr/duplicate-number",
                    "error",
                    _rel(root, p),
                    num,
                    p.name,
                    f"{num} has two files ({files[num].name} and {p.name})",
                )
            )
        files[num] = p
        if "## Revisit trigger" not in p.read_text():
            diags.append(
                diag(
                    "adr/missing-revisit",
                    "error",
                    _rel(root, p),
                    num,
                    "",
                    f"{p.name} has no '## Revisit trigger' section",
                )
            )
    # index ↔ file set
    readme = adr_dir / "README.md"
    if readme.is_file():
        indexed: dict[str, str] = {}
        for line in readme.read_text().splitlines():
            m = re.search(r"\[ADR-(\d{3})\]\(([^)]+)\)", line)
            if m:
                indexed[f"ADR-{m.group(1)}"] = m.group(2)
        for num, p in files.items():
            if num not in indexed:
                diags.append(
                    diag(
                        "adr/index-mismatch",
                        "error",
                        "docs/adr/README.md",
                        num,
                        p.name,
                        f"{num} ({p.name}) has no index row",
                    )
                )
            elif indexed[num] != p.name:
                diags.append(
                    diag(
                        "adr/index-mismatch",
                        "error",
                        "docs/adr/README.md",
                        num,
                        f"index → {indexed[num]}",
                        f"index row for {num} links {indexed[num]}, expected {p.name}",
                    )
                )
        for num in indexed:
            if num not in files:
                diags.append(
                    diag(
                        "adr/index-mismatch",
                        "error",
                        "docs/adr/README.md",
                        num,
                        indexed[num],
                        f"index row for {num} names {indexed[num]} but no such file exists",
                    )
                )
    # spec appendix / body references ↔ file set
    if spec.is_file():
        spec_ids = set(re.findall(r"ADR-\d{3}", spec.read_text()))
        for num in sorted(spec_ids - set(files)):
            diags.append(
                diag(
                    "adr/spec-appendix-mismatch",
                    "error",
                    "docs/2_canonical_design_spec.md",
                    num,
                    "",
                    f"the canonical spec names {num} but docs/adr/ has no such file",
                )
            )
        for num in sorted(set(files) - spec_ids):
            diags.append(
                diag(
                    "adr/spec-appendix-mismatch",
                    "error",
                    "docs/adr",
                    num,
                    files[num].name,
                    f"{num} exists but is not named anywhere in the canonical spec "
                    f"(Appendix F drift)",
                )
            )
    # dangling cross-references inside ADR bodies (supersession/citation chains
    # must resolve to real files).
    for num, p in files.items():
        for ref in sorted(set(re.findall(r"ADR-\d{3}", p.read_text())) - {num}):
            if ref not in files:
                diags.append(
                    diag(
                        "adr/dangling-reference",
                        "error",
                        _rel(root, p),
                        ref,
                        f"{num} cites {ref}",
                        f"{p.name} cites {ref} which has no file in docs/adr/",
                    )
                )


# ── report ───────────────────────────────────────────────────────────────────

INPUTS = (
    "docs/tickets/00_MANIFEST.md",
    "docs/tickets/DEFERRALS.md",
    "docs/build/LEDGER.md",
    "docs/build/BUILD_INDEX.md",
    "docs/build/COVERAGE_MATRIX.csv",
    "docs/2_canonical_design_spec.md",
)


def audit(root: pathlib.Path) -> tuple[list[dict], dict]:
    diags: list[dict] = []
    manifest = parse_manifest(root, diags)
    parse_tickets(root, manifest, diags)
    parse_deferrals(root, diags)
    parse_ledger(root, manifest, diags)
    parse_coverage(root, manifest, diags)
    parse_adrs(root, diags)
    inputs = {}
    for rel in INPUTS:
        p = root / rel
        if p.is_file():
            inputs[rel] = sha256(p)
    adr_dir = root / "docs/adr"
    if adr_dir.is_dir():
        for p in sorted(adr_dir.glob("ADR-*.md")):
            inputs[_rel(root, p)] = sha256(p)
    meta = {
        "tool": "audit_current_state.py",
        "schema": "build-memory-audit/1",
        "root": str(root),
        "input_digests": inputs,
    }
    return diags, meta


def render_markdown(diags: list[dict], meta: dict) -> str:
    errors = [d for d in diags if d["severity"] == "error"]
    conflicts = [d for d in diags if d["severity"] == "conflict"]
    lines = [
        "# Build-memory current-state audit (P32.1 / SIG-MEM-001)",
        "",
        f"- root: `{meta['root']}`",
        f"- inputs: {len(meta['input_digests'])} files, SHA-256 recorded in the JSON report",
        f"- result: **{len(errors)} error(s), {len(conflicts)} conflict(s)**",
        "",
    ]
    if not diags:
        lines.append("No discrepancies detected.")
        return "\n".join(lines) + "\n"
    lines.append("| check | severity | file | obligation | message |")
    lines.append("|---|---|---|---|---|")
    for d in diags:
        lines.append(
            f"| {d['check']} | {d['severity']} | {d['file']} | {d['obligation']} | {d['message']} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=pathlib.Path, default=ROOT, help="repo/worktree root")
    ap.add_argument(
        "--json-out", type=pathlib.Path, default=None, help="write the JSON report here"
    )
    ap.add_argument(
        "--md-out", type=pathlib.Path, default=None, help="write the Markdown report here"
    )
    args = ap.parse_args(argv)
    root = args.root.resolve()
    readme = root / "docs/build/README.md"
    if not readme.is_file() or MARKER not in readme.read_text():
        print(
            f"audit_current_state: {root} is not a build-memory repo (no marker)", file=sys.stderr
        )
        return 2
    diags, meta = audit(root)
    errors = sum(1 for d in diags if d["severity"] == "error")
    conflicts = sum(1 for d in diags if d["severity"] == "conflict")
    payload = {**meta, "summary": {"errors": errors, "conflicts": conflicts}, "diagnostics": diags}
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=1) + "\n")
    md = render_markdown(diags, meta)
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(md)
    sys.stdout.write(md)
    return 1 if diags else 0


if __name__ == "__main__":
    raise SystemExit(main())
