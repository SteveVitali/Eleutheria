#!/usr/bin/env python3
"""A3 — deterministic, read-only extractor + checker for the Round-11 obligation universe.

    python3 extract_universe.py            (re)write universe/UNIVERSE.csv; print the reconciliation
    python3 extract_universe.py --check    regenerate in memory; verify UNIVERSE.csv is
                                           byte-identical, every source item appears exactly
                                           once, counts reconcile to the A1 baseline (or the
                                           difference is explained); exit 1 on any error
    python3 extract_universe.py --stdout   print the CSV; write nothing

One row per SOURCE ITEM (META_PLAN §8.1 columns + a trailing `links` column). Ids `U-nnnn` are
positional over a deterministic sort (source_kind in KIND_ORDER, then a natural sort of
source_ref), so they are stable for a fixed set of source bytes. disposition / disposition_ref /
rationale / priority are left empty (S1 assigns them). Cross-source duplicates are LINKED
(symmetric, space-separated source refs), never collapsed.

Reads only: docs/tickets/{DEFERRALS.md,00_MANIFEST.md}, docs/build/reports/obligations/*,
docs/build/{COVERAGE_MATRIX.csv,BACKLOG.csv,BUILD_INDEX.md,OPERATIONAL_READINESS.md},
docs/2_canonical_design_spec.md, docs/risk_register.md, two slices + the `returnPass:` key of
docs/build/LEDGER.md, docs/adr/ADR-*.md, docs/build/readouts/*.md and the A1 baseline.json.
Writes only universe/UNIVERSE.csv (default mode). Stdlib only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parents[1]  # the planning directory (PD)
ROOT = HERE.parents[3]  # repository root
OUT = HERE / "universe" / "UNIVERSE.csv"
BASELINE = HERE / "baseline" / "baseline.json"

DEFERRALS = "docs/tickets/DEFERRALS.md"
EVENTS = "docs/build/reports/obligations/events.jsonl"
ASSESSMENTS = "docs/build/reports/obligations/coverage_assessments.jsonl"
RECONCILIATIONS = "docs/build/reports/obligations/reconciliations.json"
COVERAGE = "docs/build/COVERAGE_MATRIX.csv"
SPEC = "docs/2_canonical_design_spec.md"
BACKLOG = "docs/build/BACKLOG.csv"
RISKS = "docs/risk_register.md"
LEDGER = "docs/build/LEDGER.md"
READINESS = "docs/build/OPERATIONAL_READINESS.md"
ADR_DIR = "docs/adr"
READOUTS = "docs/build/readouts"
MANIFEST = "docs/tickets/00_MANIFEST.md"
BUILD_INDEX = "docs/build/BUILD_INDEX.md"

COLUMNS = [
    "u_id",
    "source_kind",
    "source_ref",
    "title",
    "source_status",
    "effective_status",
    "blocker_class",
    "evidence",
    "disposition",
    "disposition_ref",
    "rationale",
    "stream",
    "priority",
    "links",  # A3 extension, appended after the §8.1 columns
]
S1_COLUMNS = ("disposition", "disposition_ref", "rationale", "priority")
# §8.1 enum order; `ledger_finding` / `return_pass` are A3 extensions (the §8.1 `finding` kind is
# reserved for FINDINGS.csv F-ids and `feedback` for U-ids, both merged by S1).
KIND_ORDER = (
    "deferral",
    "requirement",
    "backlog",
    "risk",
    "ledger_finding",
    "return_pass",
    "adr_trigger",
    "readout",
    "manifest_row",
)
BLOCKER_CLASSES = (
    "engineering",
    "live-execution",
    "operator",
    "human",
    "rights",
    "external",
    "scheduled",
)
# META_PLAN row that should adjudicate each kind.
STREAM = {
    "deferral": "F1",
    "requirement": "F2",
    "backlog": "F3",
    "risk": "F3",
    "ledger_finding": "B4",
    "return_pass": "B3",
    "adr_trigger": "S1",
    "readout": "F4",
    "manifest_row": "F4",
}
OWED = frozenset({"OPEN", "PARTIAL"})
TERMINAL = frozenset({"DONE", "WONTFIX", "ACCEPTED-SKELETON"})
# Round-10 ids the matrix calls MET although the evidence records a reduced scope (F-16).
REDUCED_SCOPE_MET = (
    "SIG-TRUST-009",
    "SIG-TRUST-010",
    "SIG-FIND-006",
    "SIG-DOS-002",
    "SIG-DOS-003",
    "SIG-DOS-004",
    "SIG-DOS-005",
    "SIG-ACQ-004",
)
EXPECTED_READOUTS = 2  # HUMAN-H4, HUMAN-H5 (row prompt)
EXPECTED_MANIFEST_ROWS = 6  # 158, 159 unused; 184-187 deferred (row prompt)
TITLE_MAX = 200

# --- id grammar (same conventions as docs/build/tools/audit_current_state.py) -------------------
DEFERRAL_ID_RE = re.compile(r"^D-[A-Z0-9][A-Za-z0-9]*(\.[A-Za-z0-9]+)*(-[A-Za-z0-9]+)+$")
DEFERRAL_CELL_RE = re.compile(r"^\|\s*([Dd]-[^|\s]*)\s*\|")
DEFERRAL_XREF_RE = re.compile(r"^\|\s*`(D-[A-Za-z0-9._-]+)`\s*\|")
DATED_TERMINAL_RE = re.compile(
    r"\b(DONE|WONTFIX|ACCEPTED-SKELETON)\s+20\d\d-"
    r"|\(20\d\d-\d\d-\d\d\)\s*:\s*\*{0,2}\s*(DONE|WONTFIX|ACCEPTED-SKELETON)\b"
)
D_MENTION_RE = re.compile(
    r"(?<![A-Za-z0-9])(?P<base>D-[A-Z0-9][A-Za-z0-9]*(?:\.[A-Za-z0-9]+)*(?:-[A-Za-z0-9]+)+)"
    r"(?P<more>(?:/-?[0-9]+(?![A-Za-z0-9-]))*)"
)
SIG_MENTION_RE = re.compile(
    r"(?<![A-Za-z0-9])(?P<base>SIG-[A-Z]+-)(?P<num>\d+)(?P<suf>[a-z]?)"
    r"(?P<more>(?:/(?:\d+[a-z]?|[a-z])(?![A-Za-z0-9]))*)"
    r"(?:(?:…|\.\.\.|–)(?P<to>\d+)(?![A-Za-z0-9]))?"
)
BL_MENTION_RE = re.compile(r"(?<![A-Za-z0-9])BL-\d{3}(?![0-9])")
RISK_MENTION_RE = re.compile(r"(?<![A-Za-z0-9])RISK-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")
HUMAN_MENTION_RE = re.compile(r"(?<![A-Za-z0-9])HUMAN-H\d+(?![0-9])")
ADR_MENTION_RE = re.compile(r"(?<![A-Za-z0-9])ADR-(\d{3})(?![0-9])")
RISK_ROUTED_RE = re.compile(
    r"^\|\s*(RISK-[A-Za-z0-9-]+?)\s*(?:→|->)\s*(BL-\d{3})(?![0-9])([^|]*)\|"
)
LEDGER_FINDING_RE = re.compile(r"^- \*\*([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)")
CLOSURE_RE = re.compile(r"\b(RESOLVED|CLOSED|RETIRED)\b")
SEMANTIC_ID_RE = re.compile(r"(?<![A-Za-z0-9.])([A-Z][A-Z0-9-]*\.\d+[a-z]?)(?![A-Za-z0-9])")


@dataclass
class Item:
    kind: str
    ref: str
    title: str
    source_status: str
    effective_status: str
    evidence: str
    blocker_class: str = ""
    mentions: set[str] = field(default_factory=set)  # alias tokens this item's own text names
    aliases: set[str] = field(default_factory=set)  # tokens by which other items name this one
    extra_links: set[str] = field(default_factory=set)  # refs linked by an explicit rule
    links: list[str] = field(default_factory=list)


# --- small helpers ------------------------------------------------------------------------------


def read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def clip(text: str, limit: int = TITLE_MAX) -> str:
    text = " ".join(text.replace("**", "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def natural_key(ref: str) -> tuple[tuple[int, int, str], ...]:
    return tuple(
        (0, int(p), "") if p.isdigit() else (1, 0, p) for p in re.split(r"(\d+)", ref) if p
    )


def split_row(line: str) -> list[str]:
    """Split a markdown table row on unescaped pipes (`\\|` is a literal pipe)."""
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    cells = re.split(r"(?<!\\)\|", body)
    return [c.replace("\\|", "|").strip() for c in cells]


def row_layout(line: str, cells: list[str]) -> str:
    """Name a DEFERRALS row shape: 8-col, legacy-7-col, or an overflow from literal pipes."""
    names = {8: "8-col", 7: "legacy-7-col"}
    if len(cells) in names:
        return names[len(cells)]
    inner = sum(span.count("|") for span in re.findall(r"`[^`\n]*`", line))
    base = len(cells) - inner
    if inner and base in names:
        return f"{names[base]} (+{inner} literal pipe(s) inside code spans)"
    return f"overflow-{len(cells)}-cells (literal pipes outside code spans)"


def expand_d(text: str) -> set[str]:
    out: set[str] = set()
    for m in D_MENTION_RE.finditer(text):
        base = m.group("base").rstrip("`*.,;:)")
        out.add(base)
        if m.group("more"):
            stem = base.rsplit("-", 1)[0]
            for part in m.group("more").split("/")[1:]:
                out.add(f"{stem}-{part.lstrip('-')}")
    return out


def expand_sig(text: str) -> set[str]:
    out: set[str] = set()
    for m in SIG_MENTION_RE.finditer(text):
        base, num, suf = m.group("base"), m.group("num"), m.group("suf")
        out.add(f"{base}{num}{suf}")
        for part in (m.group("more") or "").split("/")[1:]:
            out.add(f"{base}{num}{part}" if part.isalpha() else f"{base}{part}")
        if m.group("to") and not suf:
            lo, hi = int(num), int(m.group("to"))
            if lo < hi <= lo + 50:
                out.update(f"{base}{n:0{len(num)}d}" for n in range(lo, hi + 1))
    return out


def mentions(text: str, manifest_aliases: dict[str, str]) -> set[str]:
    """Alias tokens named in `text` (deferral, requirement, backlog, risk, readout, manifest)."""
    toks = expand_d(text) | expand_sig(text)
    toks |= set(BL_MENTION_RE.findall(text)) | set(HUMAN_MENTION_RE.findall(text))
    toks |= {r.rstrip("-") for r in RISK_MENTION_RE.findall(text)}
    for alias in manifest_aliases:
        if alias.startswith("P") and re.search(
            rf"(?<![A-Za-z0-9.]){re.escape(alias)}(?![A-Za-z0-9])(?!\.\d)", text
        ):
            toks.add(alias)
    return toks


def section(lines: list[str], header_re: str, stop_re: str = r"^#{1,3} ") -> list[tuple[int, str]]:
    """(lineno, line) pairs of every section whose header matches, up to the next header."""
    out: list[tuple[int, str]] = []
    inside = False
    for n, line in enumerate(lines, 1):
        if re.match(header_re, line):
            inside = True
            continue
        if inside and re.match(stop_re, line):
            inside = False
        if inside:
            out.append((n, line))
    return out


def blocker_from_domain(domain: str) -> str:
    """Map an OPERATIONAL_READINESS §(f3) 'blocking domain' cell onto the §8.1 blocker enum."""
    d = domain.lower().strip()
    if d.startswith("external"):
        return "external"
    if "rights" in d:
        return "rights"
    if "credentials" in d or "accounts" in d:
        return "operator"
    if "scheduled" in d or "date-bound" in d:
        return "scheduled"
    if "maintainer" in d:
        return "engineering"
    if "operator" in d:
        return "operator"
    if d.startswith("human"):
        return "human"
    if d.startswith("hosted"):
        return "live-execution"
    if d.startswith("public"):
        return "operator"
    if d.startswith("engineering"):
        return "engineering"
    return ""


# --- manifest aliases (needed by every source's mention scan) -----------------------------------


def manifest_rows(root: Path) -> dict[str, tuple[int, list[str]]]:
    rows: dict[str, tuple[int, list[str]]] = {}
    for n, line in enumerate(read(root, MANIFEST).splitlines(), 1):
        m = re.match(r"^\|\s*(\d+[a-z]?)\s*\|\s*`?[^|]+\.md`?\s*\|", line)
        if m:
            rows[m.group(1)] = (n, split_row(line))
    return rows


def build_index_seqs(root: Path) -> Counter[str]:
    seqs: Counter[str] = Counter()
    for line in read(root, BUILD_INDEX).splitlines():
        m = re.match(r"^\|\s*(\d+[a-z]?)\s*\|\s*[A-Z][^|]*\|", line)
        if m:
            seqs[m.group(1)] += 1
    return seqs


def manifest_items(root: Path) -> tuple[list[Item], dict[str, Any]]:
    text = read(root, MANIFEST)
    lines = text.splitlines()
    rows = manifest_rows(root)
    landed = build_index_seqs(root)
    items: list[Item] = []
    info: dict[str, Any] = {}
    # deferred rows: the S3 dispatch amendment ("rows 184–187 ... are recorded OPEN obligations")
    for n, line in enumerate(lines, 1):
        if "Dispatch amendment" in line and "deferral" in line:
            m = re.search(r"rows (\d+)[–-](\d+)", line)
            if not m:
                continue
            for seq in range(int(m.group(1)), int(m.group(2)) + 1):
                ln, cells = rows[str(seq)]
                ticket = re.sub(r"^\d+[a-z]?_", "", cells[1].strip("`")).split("__")[0]
                items.append(
                    Item(
                        kind="manifest_row",
                        ref=f"MANIFEST-{seq}",
                        title=clip(f"{ticket} — {cells[5]}"),
                        source_status="deferred",
                        effective_status="landed" if str(seq) in landed else "not-landed",
                        evidence=clip(
                            f"{MANIFEST}:{ln} (kind={cells[3]}; gate: {cells[6]}); deferred by the "
                            f"S3 dispatch amendment {MANIFEST}:{n}; BUILD_INDEX row: "
                            f"{'yes' if str(seq) in landed else 'none'}",
                            400,
                        ),
                        mentions=expand_d(line) | expand_d(" ".join(cells)),
                        aliases={ticket},
                    )
                )
            break
    # unused rows: "Rows 158 and 159 are unused: row 158 was P31.17 (...) — **DROPPED** ..."
    flat = " ".join(re.sub(r"^>\s?", "", ln) for ln in lines)
    note_line = next(
        (n for n, ln in enumerate(lines, 1) if re.search(r"Rows \d+ and \d+ are unused", ln)), 0
    )
    recon = json.loads(read(root, RECONCILIATIONS)) if (root / RECONCILIATIONS).is_file() else {}
    documented = {d["obligation"]: d for d in recon.get("documented", [])}
    m = re.search(r"Rows (\d+) and (\d+) are unused", flat)
    unused = [m.group(1), m.group(2)] if m else []
    for useq in unused:
        um = re.search(rf"row {useq} was (\S+) \(([^)]*)\) — \*\*([^*]+)\*\*", flat)
        ticket, what, fate = (um.group(1), um.group(2), um.group(3)) if um else ("?", "?", "?")
        rec = documented.get(ticket)
        items.append(
            Item(
                kind="manifest_row",
                ref=f"MANIFEST-{useq}",
                title=clip(f"{ticket} ({what}) — unused row: {fate}"),
                source_status=f"unused({fate})",
                effective_status="landed" if useq in landed else "not-landed",
                evidence=clip(
                    f"{MANIFEST}:{note_line} (unused-row note; no table row, no BUILD_INDEX row)"
                    + (
                        f"; {RECONCILIATIONS} {rec['check']} {ticket} → {rec['pointer']}"
                        if rec
                        else ""
                    ),
                    400,
                ),
                aliases={ticket},
            )
        )
    not_in_index = sorted((s for s in rows if s not in landed), key=natural_key)
    info["manifest_table_rows"] = len(rows)
    info["manifest_rows_without_build_index_row"] = not_in_index
    info["build_index_duplicate_seqs"] = sorted(s for s, c in landed.items() if c > 1)
    info["unused_rows"] = unused
    return items, info


# --- 1. deferrals ---------------------------------------------------------------------------------


def load_event_heads(root: Path) -> dict[str, dict]:
    heads: dict[str, dict] = {}
    path = root / EVENTS
    if not path.is_file():
        return heads
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ev = json.loads(line)
        oid = ev["obligation_id"]
        if oid not in heads or ev["seq"] > heads[oid]["seq"]:
            heads[oid] = ev
    return heads


def f3_domains(root: Path) -> dict[str, str]:
    lines = read(root, READINESS).splitlines()
    out: dict[str, str] = {}
    for _, line in section(lines, r"^### \(f3\)", r"^#{2,3} "):
        m = re.match(r"^\|\s*`(D-[^`]+)`\s*\|", line)
        if m:
            out[m.group(1)] = split_row(line)[1]
    return out


def deferral_items(root: Path, aliases: dict[str, str]) -> tuple[list[Item], dict[str, Any]]:
    heads = load_event_heads(root)
    f3 = f3_domains(root)
    items: list[Item] = []
    layouts: Counter[str] = Counter()
    conflicts: list[str] = []
    for n, line in enumerate(read(root, DEFERRALS).splitlines(), 1):
        if DEFERRAL_XREF_RE.match(line):
            continue
        m = DEFERRAL_CELL_RE.match(line)
        if not m:
            continue
        oid = m.group(1).rstrip("`*.,;:)")
        if not DEFERRAL_ID_RE.match(oid):
            raise ValueError(f"{DEFERRALS}:{n}: malformed obligation id {m.group(1)!r}")
        cells = split_row(line)
        layout = row_layout(line, cells)
        layouts[layout] += 1
        status_cell = cells[-1]
        lead = status_cell.split()[0].upper() if status_cell.split() else ""
        head = heads.get(oid)
        effective = head["to_status"] if head else lead
        ev = [f"{DEFERRALS}:{n}", f"kind={cells[1]}"]
        if layout != "8-col":
            ev.append(layout)
        if head:
            interp = head.get("anchor", {}).get("interpretation", "")
            ev.append(
                f"{EVENTS} head {head['event_id']} ({head['kind']}{'/' + interp if interp else ''})"
            )
            if head.get("backlog_home") not in (None, "", "—"):
                ev.append(f"backlog_home={head['backlog_home']}")
        else:
            ev.append("no obligation event (leading token used)")
        if lead in OWED and DATED_TERMINAL_RE.search(status_cell):
            conflicts.append(oid)
            ev.append("owed-leading cell also records a dated terminal token")
        if lead != effective:
            ev.append(f"cell leads {lead} but event head says {effective}")
        blocker = ""
        if oid in f3:
            ev.append(f"§(f3) domain: {f3[oid]}")
            if effective in OWED:
                blocker = blocker_from_domain(f3[oid])
        toks = mentions(line, aliases)
        if head and head.get("backlog_home") not in (None, "", "—"):
            toks.add(head["backlog_home"])
        items.append(
            Item(
                kind="deferral",
                ref=oid,
                title=clip(cells[2]),
                source_status=lead,
                effective_status=effective,
                evidence="; ".join(ev),
                blocker_class=blocker,
                mentions=toks,
                aliases={oid},
            )
        )
    info = {
        "layouts": dict(layouts),
        "owed_leading_with_dated_terminal": conflicts,
        "reconciled_events": sorted(
            oid
            for oid, h in heads.items()
            if h.get("anchor", {}).get("interpretation") == "reconciled"
        ),
        "f3_ids": sorted(f3),
        "events_present": bool(heads),
    }
    return items, info


# --- 2. requirements ------------------------------------------------------------------------------


def spec_definitions(root: Path) -> dict[str, tuple[int, str, str]]:
    text = read(root, SPEC)
    out: dict[str, tuple[int, str, str]] = {}
    for m in re.finditer(r"\*\*(SIG-[A-Z]+-\d+[a-z]?) \(([A-Z ]+)\)[^*\n]*\*\*", text):
        rest = text[m.end() :]
        para = re.split(r"\n\s*\n", rest, maxsplit=1)[0]
        line = text.count("\n", 0, m.start()) + 1
        out.setdefault(m.group(1), (line, m.group(2), para))
    return out


def latest_assessments(root: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    path = root / ASSESSMENTS
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            a = json.loads(line)
            rid = a["requirement_id"]
            if rid not in out or a.get("seq", 0) >= out[rid].get("seq", 0):
                out[rid] = a
    return out


def requirement_items(root: Path, aliases: dict[str, str]) -> tuple[list[Item], dict[str, Any]]:
    defs = spec_definitions(root)
    assessed = latest_assessments(root)
    items: list[Item] = []
    verdicts: Counter[str] = Counter()
    with (root / COVERAGE).open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        prev = reader.line_num
        for row in reader:
            start, prev = prev + 1, reader.line_num
            verdicts[row["verdict"]] += 1
            rid = row["id"]
            reduced = row["verdict"] == "MET" and rid in REDUCED_SCOPE_MET
            if row["verdict"] == "MET" and not reduced:
                continue
            spec_line, level, para = defs.get(rid, (0, row["level"], ""))
            status = "MET(reduced-scope?)" if reduced else row["verdict"]
            effective = assessed[rid]["verdict"] if rid in assessed else row["verdict"]
            ev = [
                f"{COVERAGE}:{start}",
                f"{SPEC}:{spec_line}" if spec_line else "spec definition not found",
                f"level={row['level']}",
                f"§{row['spec_section'].lstrip('§')}",
                f"class={row['class']}",
                f"owning={row['owning_tickets'] or '—'}",
                f"routing={row['routing'] or '—'}",
            ]
            if row["adrs"] not in ("", "—"):
                ev.append(f"adrs={row['adrs']}")
            if rid in assessed:
                ev.append(f"{ASSESSMENTS} {assessed[rid]['assessment_id']}")
            items.append(
                Item(
                    kind="requirement",
                    ref=rid,
                    title=clip(para or row["spec_section"]),
                    source_status=status,
                    effective_status=effective,
                    evidence="; ".join(ev),
                    mentions=mentions(" ".join(row.values()), aliases) - {rid},
                    aliases={rid},
                )
            )
    return items, {"verdicts": dict(verdicts), "rows": sum(verdicts.values())}


# --- 3. backlog + 4. risk register ----------------------------------------------------------------


def backlog_rows(root: Path) -> list[tuple[int, dict[str, str]]]:
    out = []
    with (root / BACKLOG).open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        prev = reader.line_num
        for row in reader:
            out.append((prev + 1, row))
            prev = reader.line_num
    return out


def backlog_items(root: Path, aliases: dict[str, str]) -> tuple[list[Item], dict[str, Any]]:
    items: list[Item] = []
    rows = backlog_rows(root)
    for line, row in rows:
        if row["status"] not in ("open", "accepted"):
            continue
        toks = mentions(" ".join(row.values()), aliases) - {row["bl_id"]}
        toks |= {f"ADR-{n}" for n in ADR_MENTION_RE.findall(row["sources"])}
        items.append(
            Item(
                kind="backlog",
                ref=row["bl_id"],
                title=clip(row["title"]),
                source_status=row["status"],
                effective_status=row["status"],
                evidence=clip(
                    f"{BACKLOG}:{line}; type={row['type']}; package={row['package'] or '—'}; "
                    f"landing={row['landing'] or '—'}; gate={row['gate'] or '—'}; "
                    f"size={row['size']}",
                    400,
                ),
                mentions=toks,
                aliases={row["bl_id"]},
            )
        )
    return items, {"status": dict(Counter(r["status"] for _, r in rows)), "rows": len(rows)}


def risk_items(root: Path, aliases: dict[str, str]) -> tuple[list[Item], dict[str, Any]]:
    bl_status = {r["bl_id"]: r["status"] for _, r in backlog_rows(root)}
    items: list[Item] = []
    routed: Counter[str] = Counter()
    all_ids: Counter[str] = Counter()
    for n, line in enumerate(read(root, RISKS).splitlines(), 1):
        base = re.match(r"^\|\s*(RISK-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)", line)
        if base:
            all_ids[base.group(1)] += 1
        m = RISK_ROUTED_RE.match(line)
        if not m:
            continue
        rid, bl = m.group(1), m.group(2)
        status = bl_status.get(bl, "missing")
        routed[status] += 1
        if status not in ("open", "accepted"):
            continue
        cells = split_row(line)
        items.append(
            Item(
                kind="risk",
                ref=rid,
                title=clip(cells[1] if len(cells) > 1 else rid),
                source_status=f"routed→{bl}",
                effective_status=status,
                evidence=(
                    f"{RISKS}:{n}; routed to {bl}{m.group(3).rstrip()} (BACKLOG status {status})"
                ),
                mentions=mentions(line, aliases) - {rid},
                aliases={rid},
            )
        )
    info = {
        "routed_by_bl_status": dict(routed),
        "risk_rows": sum(all_ids.values()),
        "duplicate_risk_ids": sorted(k for k, v in all_ids.items() if v > 1),
    }
    return items, info


# --- 5. LEDGER slices -----------------------------------------------------------------------------


def ledger_finding_items(root: Path, aliases: dict[str, str]) -> tuple[list[Item], dict[str, Any]]:
    lines = read(root, LEDGER).splitlines()
    items: list[Item] = []
    seen: list[tuple[str, bool]] = []
    for n, line in section(lines, r"^## OPEN FINDINGS", r"^## "):
        m = LEDGER_FINDING_RE.match(line)
        if not m:
            continue
        fid = m.group(1)
        rest = line[m.end() :]
        closed = bool(CLOSURE_RE.search(rest))
        seen.append((fid, closed))
        if closed:
            continue
        items.append(
            Item(
                kind="ledger_finding",
                ref=fid,
                title=clip(rest.lstrip(":*— ").replace("**", "")),
                source_status="open",
                effective_status="open",
                evidence=f"{LEDGER}:{n} (OPEN FINDINGS; no RESOLVED/CLOSED/RETIRED marker)",
                mentions=mentions(rest, aliases),
            )
        )
    return items, {"entries": len(seen), "closed": sorted(f for f, c in seen if c)}


def split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth == 0 and text.startswith(", ", i):
            parts.append("".join(buf).strip())
            buf = []
            i += 2
            continue
        buf.append(ch)
        i += 1
    if "".join(buf).strip():
        parts.append("".join(buf).strip())
    return parts


def done_marker(text: str) -> str:
    done = bool(re.search(r"\b(DONE|CLEARED)\b", text))
    owed = bool(re.search(r"\bowed\b", text, re.I))
    if done and owed:
        return "partly-done-marked"
    return "done-marked" if done else "listed"


def return_pass_items(
    root: Path, aliases: dict[str, str], deferral_refs: dict[str, str]
) -> tuple[list[Item], dict[str, Any]]:
    lines = read(root, LEDGER).splitlines()
    table: dict[str, tuple[int, list[str], str]] = {}
    for n, line in section(lines, r"^## RETURN PASS", r"^## "):
        if not line.startswith("|") or re.match(r"^\|\s*(Ticket|-{3})", line):
            continue
        cells = split_row(line)
        tid = cells[0].split()[0]
        table[tid] = (n, cells, line)
    key: dict[str, tuple[int, str]] = {}
    for n, line in enumerate(lines, 1):
        if line.startswith("returnPass:"):
            body = re.sub(r"\s{2,}#\s.*$", "", line[len("returnPass:") :]).strip()
            for entry in split_top_level(body):
                tm = re.match(r"[A-Z][A-Za-z0-9.-]*", entry)
                if tm:
                    key[tm.group(0)] = (n, entry)
            break
    items: list[Item] = []
    for tid in sorted(set(table) | set(key), key=natural_key):
        texts, ev = [], []
        if tid in table:
            n, cells, line = table[tid]
            texts.append(line)
            ev.append(f"{LEDGER}:{n} (RETURN PASS table)")
            title = f"{cells[0]} — {cells[1]}"
        if tid in key:
            n, entry = key[tid]
            texts.append(entry)
            ev.append(f"{LEDGER}:{n} (returnPass key)")
            if tid not in table:
                title = entry
        text = " ".join(texts)
        status = (
            f"table={done_marker(table[tid][1][1]) if tid in table else '-'} "
            f"key={done_marker(key[tid][1]) if tid in key else '-'}"
        )
        prefixes = {tid} | set(
            SEMANTIC_ID_RE.findall(table[tid][1][0] if tid in table else key[tid][1][:40])
        )
        linked = {d for d in expand_d(text) if d in deferral_refs}
        linked |= {d for d in deferral_refs if any(d.startswith(f"D-{p}-") for p in prefixes)}
        owed = sorted(d for d in linked if deferral_refs[d] in OWED)
        effective = "owed" if owed else ("terminal" if linked else "unlinked")
        ev.append(
            f"linked deferrals: {len(linked)} ({len(owed)} owed"
            + (": " + " ".join(owed) if owed else "")
            + ")"
        )
        items.append(
            Item(
                kind="return_pass",
                ref=f"RETURN-PASS:{tid}",
                title=clip(title),
                source_status=status,
                effective_status=effective,
                evidence="; ".join(ev),
                mentions=mentions(text, aliases),
                extra_links=linked,
            )
        )
    info = {
        "table_rows": len(table),
        "key_entries": len(key),
        "key_only": sorted(set(key) - set(table), key=natural_key),
        "table_only": sorted(set(table) - set(key), key=natural_key),
    }
    return items, info


# --- 6. ADR revisit triggers ----------------------------------------------------------------------


def adr_items(root: Path, aliases: dict[str, str]) -> tuple[list[Item], dict[str, Any]]:
    items: list[Item] = []
    missing: list[str] = []
    statuses: Counter[str] = Counter()
    files = sorted((root / ADR_DIR).glob("ADR-*.md"))
    for path in files:
        num = re.match(r"ADR-(\d+)", path.name)
        if not num:
            continue
        ref = f"ADR-{num.group(1)}"
        lines = path.read_text(encoding="utf-8").splitlines()
        title = next((ln.lstrip("# ").strip() for ln in lines if ln.startswith("# ")), ref)
        title = re.sub(rf"^{ref}\s*[:—-]\s*", "", title)
        status = ""
        for ln in lines[:20]:
            sm = re.match(r"^\s*-\s*(?:\*\*)?Status:?(?:\*\*)?:?\s*(.*)$", ln)
            if sm:
                status = sm.group(1).strip()
                break
        statuses[(status.split() or ["?"])[0].strip(".;,").lower()] += 1
        trig = section(lines, r"^## Revisit trigger", r"^## ")
        head = next((n for n, ln in enumerate(lines, 1) if ln.startswith("## Revisit trigger")), 0)
        body = " ".join(ln for _, ln in trig).strip()
        if not head:
            missing.append(ref)
        rel = path.relative_to(root).as_posix()
        items.append(
            Item(
                kind="adr_trigger",
                ref=ref,
                title=clip(title, 160),
                source_status="monitor",
                effective_status="superseded?" if "supersed" in status.lower() else "monitor",
                evidence=clip(
                    f"{rel}:{head or '?'}; status={clip(status, 60) or '?'}; "
                    f"trigger: {body or '(none)'}",
                    400,
                ),
                mentions=mentions(body, aliases),
                aliases={ref},
            )
        )
    return items, {"files": len(files), "missing_trigger": missing, "statuses": dict(statuses)}


# --- 7. readouts ----------------------------------------------------------------------------------


def readout_items(root: Path, aliases: dict[str, str]) -> tuple[list[Item], dict[str, Any]]:
    items: list[Item] = []
    statuses: dict[str, str] = {}
    for path in sorted((root / READOUTS).glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        status, line = "", 0
        for n, ln in enumerate(lines, 1):
            sm = re.match(r"^(?:Status:|## Verdict:)\s*(.*)$", ln)
            if sm:
                status, line = sm.group(1).replace("**", "").strip(), n
                break
        h1 = next((ln.lstrip("# ").strip() for ln in lines if ln.startswith("# ")), "")
        h1_status = re.search(r"\b(PENDING|SIGNED|PASSED)\b.*", h1)
        if not status and h1_status:
            status, line = f"(H1) {h1_status.group(0)}", 1
        statuses[path.stem] = clip(status, 60) or "(no Status/Verdict line)"
        if not status.upper().startswith("PENDING"):
            continue
        rel = path.relative_to(root).as_posix()
        title = next((ln.lstrip("# ").strip() for ln in lines if ln.startswith("# ")), path.stem)
        items.append(
            Item(
                kind="readout",
                ref=path.stem,
                title=clip(title),
                source_status="PENDING",
                effective_status="PENDING",
                evidence=clip(f"{rel}:{line}: {status}", 300),
                mentions=mentions("\n".join(lines), aliases),
                aliases={path.stem},
            )
        )
    return items, {"statuses": statuses}


# --- assembly -------------------------------------------------------------------------------------


def build(root: Path = ROOT) -> tuple[list[Item], dict[str, dict[str, Any]]]:
    mitems, minfo = manifest_items(root)
    manifest_alias = {a: i.ref for i in mitems for a in i.aliases}
    ditems, dinfo = deferral_items(root, manifest_alias)
    deferral_status = {i.ref: i.effective_status for i in ditems}
    groups = {
        "deferral": (ditems, dinfo),
        "requirement": requirement_items(root, manifest_alias),
        "backlog": backlog_items(root, manifest_alias),
        "risk": risk_items(root, manifest_alias),
        "ledger_finding": ledger_finding_items(root, manifest_alias),
        "return_pass": return_pass_items(root, manifest_alias, deferral_status),
        "adr_trigger": adr_items(root, manifest_alias),
        "readout": readout_items(root, manifest_alias),
        "manifest_row": (mitems, minfo),
    }
    items = [it for kind in KIND_ORDER for it in groups[kind][0]]
    infos = {kind: groups[kind][1] for kind in KIND_ORDER}
    infos["_section55"] = section55(root)
    link(items)
    items.sort(key=lambda it: (KIND_ORDER.index(it.kind), natural_key(it.ref)))
    return items, infos


def link(items: list[Item]) -> None:
    """Symmetric cross-kind links from explicit id mentions (never same-kind, never self)."""
    by_ref = {it.ref: it for it in items}
    index: dict[str, set[str]] = {}
    for it in items:
        for alias in it.aliases:
            index.setdefault(alias, set()).add(it.ref)
    edges: set[tuple[str, str]] = set()
    for it in items:
        targets = set(it.extra_links)
        for tok in it.mentions:
            targets |= index.get(tok, set())
        for ref in targets:
            other = by_ref.get(ref)
            if other is not None and other.kind != it.kind:
                edges.add((it.ref, ref))
                edges.add((ref, it.ref))
    for it in items:
        it.links = sorted((b for a, b in edges if a == it.ref), key=natural_key)


def section55(root: Path) -> dict[str, Any]:
    text = read(root, SPEC)
    m = re.search(r"^## 55\. .*?(?=^# )", text, re.S | re.M)
    body = m.group(0) if m else ""
    return {"d_ids": sorted(expand_d(body), key=natural_key), "found": bool(body)}


def to_rows(items: list[Item]) -> list[dict[str, str]]:
    rows = []
    for n, it in enumerate(items, 1):
        rows.append(
            {
                "u_id": f"U-{n:04d}",
                "source_kind": it.kind,
                "source_ref": it.ref,
                "title": it.title,
                "source_status": it.source_status,
                "effective_status": it.effective_status,
                "blocker_class": it.blocker_class,
                "evidence": it.evidence,
                "disposition": "",
                "disposition_ref": "",
                "rationale": "",
                "stream": STREAM[it.kind],
                "priority": "",
                "links": " ".join(it.links),
            }
        )
    return rows


def render(rows: list[dict[str, str]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


# --- checker --------------------------------------------------------------------------------------


def load_baseline() -> dict:
    return json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.is_file() else {}


def reconciliation(
    rows: list[dict[str, str]], infos: dict[str, dict[str, Any]], baseline: dict
) -> tuple[list[tuple[str, str, int, str, bool]], list[str]]:
    """(kind, expected, actual, explanation, ok) per source + errors for unexplained differences."""
    counts = Counter(r["source_kind"] for r in rows)
    by_status = {
        k: Counter(r["effective_status"] for r in rows if r["source_kind"] == k) for k in KIND_ORDER
    }
    src = Counter((r["source_kind"], r["source_status"]) for r in rows)
    out: list[tuple[str, str, int, str, bool]] = []
    errors: list[str] = []

    def add(kind: str, expected: int | None, why: str, explained_diff: int = 0) -> None:
        actual = counts.get(kind, 0)
        ok = expected is None or actual - expected == explained_diff
        if not ok:
            errors.append(f"{kind}: expected {expected}, got {actual} — difference not explained")
        out.append((kind, "—" if expected is None else str(expected), actual, why, ok))

    d = infos["deferral"]
    owed = sum(by_status["deferral"][s] for s in OWED)
    exp_owed = baseline.get("mem.current.owed", 36)
    if owed != exp_owed:
        errors.append(f"deferral: owed {owed} != baseline {exp_owed}")
    add(
        "deferral",
        baseline.get("mem.deferrals.rows", 97),
        f"every obligation row; effective status from {EVENTS} heads "
        f"({dict(sorted(by_status['deferral'].items()))}); owed={owed} (baseline {exp_owed}); "
        f"layouts {d['layouts']}",
    )
    verdicts = baseline.get("mem.coverage.verdicts", {})
    not_met = baseline.get("mem.coverage.not_met", 69)
    na = int(verdicts.get("N/A-RATIONALE", 0))
    exp_req = not_met + int(verdicts.get("MET-DIFFERENTLY", 77)) + len(REDUCED_SCOPE_MET)
    add(
        "requirement",
        exp_req,
        f"{not_met} not-MET + {verdicts.get('MET-DIFFERENTLY', 77)} MET-DIFFERENTLY + "
        f"{len(REDUCED_SCOPE_MET)} MET(reduced-scope?) expected; +{na} N/A-RATIONALE rows are also "
        f"verdict != MET (included, explained); by source_status "
        f"{dict(sorted((s, c) for (k, s), c in src.items() if k == 'requirement'))}",
        explained_diff=na,
    )
    bls = baseline.get("mem.backlog.status", {})
    add(
        "backlog",
        int(bls.get("open", 32)) + int(bls.get("accepted", 4)),
        f"open + accepted ({dict(sorted(by_status['backlog'].items()))}); closed excluded",
    )
    r = infos["risk"]
    add(
        "risk",
        None,
        f"register rows routed `RISK → BL` whose BL is open/accepted; routed by BL status "
        f"{r['routed_by_bl_status']} (closed-BL routes excluded); {r['risk_rows']} RISK rows in "
        f"the "
        f"register; duplicate ids {r['duplicate_risk_ids']}",
    )
    lf = infos["ledger_finding"]
    add(
        "ledger_finding",
        None,
        f"{lf['entries']} entries under the two `## OPEN FINDINGS` headings; "
        f"closed: {lf['closed']}",
    )
    rp = infos["return_pass"]
    add(
        "return_pass",
        None,
        f"union of {rp['table_rows']} RETURN PASS table rows and {rp['key_entries']} `returnPass:` "
        f"key entries; key-only {rp['key_only']}; table-only {rp['table_only']}",
    )
    a = infos["adr_trigger"]
    add(
        "adr_trigger",
        baseline.get("mem.adr.files", 144),
        f"one per ADR file ({a['files']} files; "
        f"missing trigger section: {a['missing_trigger'] or 'none'}; "
        f"status words {a['statuses']})",
    )
    ro = infos["readout"]
    add(
        "readout",
        EXPECTED_READOUTS,
        "PENDING readouts only; others: "
        + ", ".join(
            f"{k}={v if v.startswith('(') else v.split(' ')[0]}"
            for k, v in ro["statuses"].items()
            if not v.upper().startswith("PENDING")
        ),
    )
    m = infos["manifest_row"]
    add(
        "manifest_row",
        EXPECTED_MANIFEST_ROWS,
        f"unused {m['unused_rows']} + the S3-deferred rows; manifest rows without a "
        f"BUILD_INDEX row: {m['manifest_rows_without_build_index_row']} (190/195 are gate "
        f"markers with signed readouts, "
        f"170a is recorded as a duplicate seq {m['build_index_duplicate_seqs']} — excluded)",
    )
    return out, errors


def independent_counts(root: Path) -> dict[str, int]:
    """Deliberately naive re-counts that do not share the extractor's parsers."""
    raw = read(root, DEFERRALS)
    cov = list(csv.DictReader((root / COVERAGE).open(newline="", encoding="utf-8")))
    bl = list(csv.DictReader((root / BACKLOG).open(newline="", encoding="utf-8")))
    return {
        "deferral": len(re.findall(r"^\| D-", raw, re.M)),
        "requirement": sum(1 for r in cov if r["verdict"] != "MET" or r["id"] in REDUCED_SCOPE_MET),
        "backlog": sum(1 for r in bl if r["status"] in ("open", "accepted")),
        "adr_trigger": sum(
            1
            for p in (root / ADR_DIR).glob("ADR-*.md")
            if "\n## Revisit trigger" in p.read_text(encoding="utf-8")
        ),
    }


def check_rows(
    rows: list[dict[str, str]],
    items: list[Item],
    infos: dict[str, dict[str, Any]],
    root: Path = ROOT,
) -> list[str]:
    errors: list[str] = []
    expected_keys = Counter((it.kind, it.ref) for it in items)
    seen_keys = Counter((r["source_kind"], r["source_ref"]) for r in rows)
    for key, n in sorted(seen_keys.items()):
        if n != 1:
            errors.append(f"{key[0]} {key[1]}: appears {n} times (must be exactly once)")
    for key in sorted(expected_keys):
        if key not in seen_keys:
            errors.append(f"{key[0]} {key[1]}: source item missing from the universe")
    for key in sorted(seen_keys):
        if key not in expected_keys:
            errors.append(f"{key[0]} {key[1]}: universe row has no source item")
    refs = Counter(r["source_ref"] for r in rows)
    errors.extend(f"source_ref {k} is not globally unique" for k, v in refs.items() if v > 1)
    order = [
        (KIND_ORDER.index(r["source_kind"]), natural_key(r["source_ref"]))
        for r in rows
        if r["source_kind"] in KIND_ORDER
    ]
    if order != sorted(order):
        errors.append("rows are not in (source_kind, natural source_ref) order")
    for n, r in enumerate(rows, 1):
        if r["u_id"] != f"U-{n:04d}":
            errors.append(f"row {n}: u_id {r['u_id']} is not U-{n:04d}")
        if r["source_kind"] not in KIND_ORDER:
            errors.append(f"{r['u_id']}: unknown source_kind {r['source_kind']!r}")
        if r["blocker_class"] and r["blocker_class"] not in BLOCKER_CLASSES:
            errors.append(f"{r['u_id']}: blocker_class {r['blocker_class']!r} not in the §8.1 enum")
        for col in S1_COLUMNS:
            if r[col]:
                errors.append(f"{r['u_id']}: {col} must stay empty until S1")
        if (
            not r["stream"]
            or not r["source_status"]
            or not r["effective_status"]
            or not r["evidence"]
        ):
            errors.append(
                f"{r['u_id']}: stream/source_status/effective_status/evidence must be set"
            )
    kind_of = {r["source_ref"]: r["source_kind"] for r in rows}
    linkset = {r["source_ref"]: set(r["links"].split()) for r in rows}
    for ref, targets in linkset.items():
        for t in targets:
            if t not in kind_of:
                errors.append(f"{ref}: link {t} does not resolve to a universe row")
            elif kind_of[t] == kind_of[ref]:
                errors.append(f"{ref}: link {t} is same-kind (links are cross-source only)")
            elif ref not in linkset.get(t, set()):
                errors.append(f"{ref}: link {t} is not symmetric")
    owed = {
        r["source_ref"]
        for r in rows
        if r["source_kind"] == "deferral" and r["effective_status"] in OWED
    }
    f3 = set(infos["deferral"]["f3_ids"])
    if owed != f3:
        errors.append(
            f"owed deferrals != OPERATIONAL_READINESS §(f3): only-owed {sorted(owed - f3)}, "
            f"only-f3 {sorted(f3 - owed)}"
        )
    for row in rows:
        if (
            row["source_kind"] == "deferral"
            and row["effective_status"] in OWED
            and not row["blocker_class"]
        ):
            errors.append(
                f"{row['source_ref']}: owed deferral without a §(f3)-derived blocker_class"
            )
    s55 = infos["_section55"]
    missing55 = [d for d in s55["d_ids"] if kind_of.get(d) != "deferral"]
    if not s55["found"]:
        errors.append("spec §55 not found")
    if missing55:
        errors.append(f"§55 names obligations absent from the universe: {missing55}")
    counts = Counter(r["source_kind"] for r in rows)
    for kind, n in independent_counts(root).items():
        if counts.get(kind, 0) != n:
            errors.append(f"{kind}: extractor count {counts.get(kind, 0)} != naive re-count {n}")
    return errors


def baseline_drift(root: Path, baseline: dict) -> list[str]:
    notes = []
    for key, value in sorted(baseline.items()):
        if key.startswith("mem.sha256."):
            rel = key[len("mem.sha256.") :]
            path = root / rel
            now = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "absent"
            if now != value:
                notes.append(f"{rel}: sha256 differs from the A1 baseline")
    return notes


def report(rows: list[dict[str, str]], infos: dict[str, dict[str, Any]], root: Path) -> list[str]:
    baseline = load_baseline()
    table, errors = reconciliation(rows, infos, baseline)
    print("| source_kind | expected | actual | diff | ok | derivation / explanation |")
    print("|---|---|---|---|---|---|")
    for kind, exp, act, why, ok in table:
        diff = "—" if exp == "—" else f"{act - int(exp):+d}"
        print(f"| {kind} | {exp} | {act} | {diff} | {'yes' if ok else 'NO'} | {why} |")
    print(f"| **total** | | {len(rows)} | | | |")
    drift = baseline_drift(root, baseline)
    print(
        "baseline digests: "
        + ("all tracked control files match A1" if not drift else "; ".join(drift))
    )
    s55 = infos["_section55"]
    print(f"§55 cross-check: {len(s55['d_ids'])} D-ids named, all present as deferral rows")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="verify UNIVERSE.csv; write nothing")
    ap.add_argument("--stdout", action="store_true", help="print the CSV; write nothing")
    args = ap.parse_args(argv)
    items, infos = build(ROOT)
    rows = to_rows(items)
    text = render(rows)
    if args.stdout:
        sys.stdout.write(text)
        return 0
    errors = check_rows(rows, items, infos, ROOT)
    if args.check:
        on_disk = OUT.read_text(encoding="utf-8") if OUT.is_file() else ""
        if on_disk != text:
            errors.append(f"{OUT.relative_to(ROOT)} is stale — regenerate with extract_universe.py")
        else:
            disk_rows = list(csv.DictReader(io.StringIO(on_disk)))
            errors.extend(check_rows(disk_rows, items, infos, ROOT))
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(text, encoding="utf-8")
    errors += report(rows, infos, ROOT)
    errors = sorted(set(errors), key=errors.index)
    if errors:
        print("extract_universe: FAIL\n" + "\n".join("- " + e for e in errors))
        return 1
    print(f"extract_universe: OK — {len(rows)} universe rows; each source item exactly once")
    return 0


if __name__ == "__main__":
    sys.exit(main())
