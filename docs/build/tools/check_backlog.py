#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Validate ``docs/build/BACKLOG.csv`` against its four sources of truth (P20.1).

The backlog replaces four overlapping backlogs (the risk-register deferred-class
tables, the ADR ``## Revisit trigger`` sections, ``LEDGER_DEFERRALS.md``, and the
``CHECKLIST_ITEMS→None`` pattern) with **one** normalized file where every source
id lands in exactly one row's ``sources`` cell (defining standard §3.1: no orphan
items, no double-owned sources).

This is a **docs tool invoked in the PR**, not a ``make check`` step — the
compensating control for RISK-P20-01 (backlog drift). Standard library only; run
from anywhere:

    python docs/build/tools/check_backlog.py

Exits 0 and prints the count lines when the backlog is consistent; exits 1
with the first failing invariant otherwise.

Round 11 (SEED-15, Stage B T4; SEED-14b's checker list; B4 G8-3/G9; ADR-150 D3):

* **landings** accept letter-suffixed chain tickets and multi-digit row numbers
  (``P34.48``, ``P37.16a``, ``closed-by:P31.16``);
* **open-home rule** — an owed (OPEN/PARTIAL) DEFERRALS row cites at least one
  *open* BACKLOG row (a ``(cites BL-nnn)`` re-homing annotation appended to the
  row counts); an ADR revisit trigger homes on an open row, or on an
  ``accepted`` monitor row (BL-002, U-0260) unless the trigger is
  ``fired-unanswered``, or on a closed row only while it is ``quiet`` or
  ``superseded`` — the state read from ``ADR_TRIGGERS.csv``, whose ``home``
  must equal the BACKLOG row that owns the ADR;
* **RISK ids are unique** across the register's tables, except an id whose
  second definition a dated rename record (``Renamed RISK-…a by this record``)
  resolves; correction tables restating an id are not definitions.
"""

from __future__ import annotations

import csv
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
BACKLOG = ROOT / "docs/build/BACKLOG.csv"
# P22.3 (build-memory v2 migration) moved the root report files into
# docs/build/reports/; the two backlog sources of truth live there now.
THEMES = ROOT / "docs/build/reports/BACKLOG_THEMES.md"
RISK = ROOT / "docs/risk_register.md"
LD = ROOT / "docs/build/reports/LEDGER_DEFERRALS.md"
ADR_DIR = ROOT / "docs/adr"
# P24.8 / REC.1 — the fifth source of truth: every OPEN/PARTIAL DEFERRALS row must
# name its single backlog home (`(cites BL-nnn)` in the row). A `D-*` id cannot
# live in a `sources` cell (it would be an orphan — only RISK-*/ADR-*/LD-*/LH-*
# are in the universe), so the cite is how a deferral "appears in exactly one
# BACKLOG source cell".
DEFERRALS = ROOT / "docs/tickets/DEFERRALS.md"

# Risk-register subsection headings whose RISK rows are the deferred/unclosed
# backlog inputs (Load list of the P20.1 ticket).
DEFERRED_HEADING = re.compile(
    r"Deferred|Out of scope|Scaffolded|Unverifiable|not-fully-closed|Bounded", re.I
)

VALID_TYPE = {
    "defect",
    "deferred-feature",
    "operational-prereq",
    "rights/legal",
    "docs-drift",
    "schema-refinement",
    "external-dep",
    "process",
}
VALID_SIZE = {"S", "M", "L"}
VALID_STATUS = {"open", "closed", "accepted"}
# landing enum: closed-by:P<n>.<m>, a P<n>.<m> chain ticket, a P<n>+ phase bucket
# (P22+ was the post-build unscheduled bucket; P25+ = post-Round-4 manifest,
# P24.5/META.1), accepted, human-gate:HG-nn. (P21.9 = Stage-5 pathway connectors,
# per the phase plan; the ticket's "P21.1…P21.8" shorthand is inclusive of the
# ninth P21 ticket. Generalised by P24.5 so future tickets land rows without
# editing this enum.)
# Round 11 (SEED-15): the row part takes any number of digits and an optional letter suffix
# (P34.48, P37.16a); before, `P\d{2}\.\d` matched only the first digit of a ticket id.
LANDING_RE = re.compile(
    r"^(closed-by:P\d{2}\.\d+[a-z]?|P\d{2}\.\d+[a-z]?|P\d{2}\+|accepted|human-gate:HG-\d{2})$"
)
# The revisit-trigger register (B4 G8-3; SEED-15) — trigger states for the open-home rule.
ADR_TRIGGERS = ROOT / "docs/build/reports/adr_triggers/ADR_TRIGGERS.csv"
# open-home rule: an owed deferral homes on an open row; an ADR trigger may also home on an
# accepted monitor row (BL-002) unless it fired unanswered, and on a closed row only while
# quiet or superseded (B4 G8-3; SEED-14b's list).
OPEN_HOME = frozenset({"open"})
MONITOR_HOME = frozenset({"accepted"})
CLOSED_HOME_STATES = frozenset({"quiet", "superseded"})


def _fail(msg: str) -> None:
    print(f"check_backlog: FAIL — {msg}", file=sys.stderr)
    sys.exit(1)


def risk_deferred_ids() -> list[str]:
    """RISK ids under a deferred-class ``### `` heading (id cell may carry a
    ``→ BL-nnn`` cross-ref suffix, which is stripped)."""
    ids: list[str] = []
    in_deferred = False
    for line in RISK.read_text().splitlines():
        if line.startswith("### "):
            in_deferred = DEFERRED_HEADING.search(line) is not None
            continue
        if line.startswith("## "):
            in_deferred = False
            continue
        if in_deferred and line.startswith("|"):
            m = re.match(r"\|\s*(RISK-[A-Za-z0-9-]+)", line)
            if m:
                ids.append(m.group(1))
    return ids


def ld_ids() -> list[str]:
    """LD-/LH- ids that head a table row in LEDGER_DEFERRALS.md."""
    ids: list[str] = []
    for line in LD.read_text().splitlines():
        m = re.match(r"\|\s*(L[DH]-[A-Za-z0-9]+)\s*\|", line)
        if m:
            ids.append(m.group(1))
    return ids


def adr_revisit_ids() -> list[str]:
    """ADR ids whose file carries a ``## Revisit trigger`` section."""
    ids: list[str] = []
    for path in sorted(ADR_DIR.glob("ADR-*.md")):
        if "## Revisit trigger" in path.read_text():
            m = re.match(r"(ADR-\d+)", path.name)
            if m:
                ids.append(m.group(1))
    return ids


# DEFERRALS statuses that still owe work — the same owed set as audit_current_state.OWED_STATUSES
# and the vendored check-build-memory.sh rule-5 scan (OPEN, PARTIAL).
DEFERRAL_OWED_STATUSES = frozenset({"OPEN", "PARTIAL"})
_DEFERRAL_ROW = re.compile(r"^\|\s*(D-[A-Z0-9][A-Za-z0-9._-]*)\s*\|")
_BL_HOME = re.compile(r"BL-\d{3}")


def deferral_homes(path: pathlib.Path) -> tuple[list[str], list[str]]:
    """Return ``(citing, missing)`` — OPEN/PARTIAL DEFERRALS row ids that name at
    least one ``BL-nnn`` backlog home, and those that name none.

    DONE / WONTFIX / ACCEPTED-SKELETON rows are owed nothing and skipped. The
    status is the first word of the row's last cell — the row's leading status
    token, the convention ``audit_current_state.py`` and ``obligation_events.py``
    use (ADR-126: never "last token wins"). The vendored
    ``scripts/docs/check-build-memory.sh`` (build-memory 0.5.0, since SEED-02c)
    no longer parses it this way: it takes the first of OPEN, PARTIAL, DONE,
    WONTFIX, ACCEPTED-SKELETON (in that priority order) that appears as a word
    anywhere in the last cell, and uses it only to reject an orphan status.
    """
    citing: list[str] = []
    missing: list[str] = []
    if not path.is_file():
        return citing, missing
    for line in path.read_text().splitlines():
        m = _DEFERRAL_ROW.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.split("|")]
        words = cells[-2].split() if len(cells) >= 2 else []
        status = words[0].upper() if words else ""
        if status not in DEFERRAL_OWED_STATUSES:
            continue
        (citing if _BL_HOME.search(line) else missing).append(m.group(1))
    return citing, missing


def deferral_open_homes(
    path: pathlib.Path, bl_status: dict[str, str]
) -> tuple[list[str], list[str]]:
    """Return ``(homed, unhomed)`` — OPEN/PARTIAL DEFERRALS rows that cite at least one *open*
    BACKLOG row, and those whose cited rows are all closed, accepted or unknown (open-home rule).

    The cites are every ``BL-nnn`` in the row, so an appended ``(cites BL-nnn)`` re-homing annotation
    homes a row whose original cite has since closed (rows are append-only)."""
    homed: list[str] = []
    unhomed: list[str] = []
    if not path.is_file():
        return homed, unhomed
    for line in path.read_text().splitlines():
        m = _DEFERRAL_ROW.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.split("|")]
        words = cells[-2].split() if len(cells) >= 2 else []
        if not words or words[0].upper() not in DEFERRAL_OWED_STATUSES:
            continue
        cites = _BL_HOME.findall(line)
        if any(bl_status.get(bl) in OPEN_HOME for bl in cites):
            homed.append(m.group(1))
        else:
            unhomed.append(m.group(1))
    return homed, unhomed


def trigger_register(path: pathlib.Path) -> list[dict[str, str]]:
    """Rows of ``ADR_TRIGGERS.csv`` (empty when the register is absent)."""
    if not path.is_file():
        return []
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def state_word(state: str) -> str:
    """``fired-answered(P35.1a)`` → ``fired-answered``."""
    return state.split("(", 1)[0].strip()


def adr_home_problems(
    adr_ids: list[str],
    owner: dict[str, str],
    bl_status: dict[str, str],
    register: list[dict[str, str]],
) -> list[str]:
    """Open-home rule for ADR revisit triggers, plus register ``home`` == BACKLOG owner."""
    problems: list[str] = []
    states = {
        r.get("adr", ""): state_word(r.get("state", ""))
        for r in register
        if r.get("adr", "").startswith("ADR-")
    }
    homes = {
        r.get("adr", ""): r.get("home", "") for r in register if r.get("adr", "").startswith("ADR-")
    }
    for adr in adr_ids:
        bl = owner.get(adr)
        if bl is None:
            continue  # reported as unmapped
        status = bl_status.get(bl, "")
        state = states.get(adr)
        if state is None:
            problems.append(f"{adr}: no ADR_TRIGGERS.csv row")
            continue
        if homes.get(adr) != bl:
            problems.append(
                f"{adr}: ADR_TRIGGERS.csv home {homes.get(adr)!r} != BACKLOG owner {bl}"
            )
        if status in OPEN_HOME:
            continue
        if status in MONITOR_HOME and state != "fired-unanswered":
            continue
        if status == "closed" and state in CLOSED_HOME_STATES:
            continue
        problems.append(f"{adr}: home {bl} is {status!r} while the trigger is {state!r}")
    return problems


_RISK_DEF_RE = re.compile(r"^\|\s*(RISK-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+)\b")
_RENAME_RE = re.compile(r"Renamed (RISK-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+) by this record")


def risk_id_duplicates(path: pathlib.Path) -> list[str]:
    """RISK ids that head more than one definition row and are not resolved by rename records.

    A definition row is a table row whose first cell starts with the id, outside a section headed
    "Corrections" (correction tables restate ids on purpose). A rename record ``Renamed RISK-X-NNa
    by this record`` resolves one extra definition of ``RISK-X-NN`` (B4 G9; F3 §7.1)."""
    defs: dict[str, int] = {}
    renames: dict[str, int] = {}
    in_corrections = False
    if not path.is_file():
        return []
    for line in path.read_text().splitlines():
        if line.startswith("#"):
            in_corrections = "orrection" in line
            continue
        rm = _RENAME_RE.search(line)
        if rm:
            base = re.sub(r"[a-z]$", "", rm.group(1))
            renames[base] = renames.get(base, 0) + 1
            continue
        m = _RISK_DEF_RE.match(line)
        if m and not in_corrections:
            defs[m.group(1)] = defs.get(m.group(1), 0) + 1
    return sorted(rid for rid, n in defs.items() if n - renames.get(rid, 0) > 1)


def load_rows() -> list[dict[str, str]]:
    with BACKLOG.open(newline="") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    if not BACKLOG.exists():
        _fail(f"{BACKLOG} not found")
    rows = load_rows()

    expected_cols = [
        "bl_id",
        "title",
        "type",
        "sources",
        "req_ids",
        "package",
        "blocks",
        "landing",
        "gate",
        "size",
        "status",
    ]
    if rows and list(rows[0].keys()) != expected_cols:
        _fail(f"unexpected columns {list(rows[0].keys())}")

    # enum validity + non-empty landing + bl_id uniqueness
    seen_bl: set[str] = set()
    for r in rows:
        bl = r["bl_id"]
        if not re.match(r"^BL-\d{3}$", bl):
            _fail(f"bad bl_id {bl!r}")
        if bl in seen_bl:
            _fail(f"duplicate bl_id {bl}")
        seen_bl.add(bl)
        if r["type"] not in VALID_TYPE:
            _fail(f"{bl}: bad type {r['type']!r}")
        if r["size"] not in VALID_SIZE:
            _fail(f"{bl}: bad size {r['size']!r}")
        if r["status"] not in VALID_STATUS:
            _fail(f"{bl}: bad status {r['status']!r}")
        if not r["landing"].strip():
            _fail(f"{bl}: empty landing")
        if not LANDING_RE.match(r["landing"]):
            _fail(f"{bl}: bad landing {r['landing']!r}")
        if r["landing"] == "P22+" and (r["type"] not in VALID_TYPE or r["size"] not in VALID_SIZE):
            _fail(f"{bl}: P22+ row needs type+size")
        if not r["sources"].strip():
            _fail(f"{bl}: empty sources")

    # each source appears in exactly one sources cell (no double-owned sources)
    owner: dict[str, str] = {}
    dupes: list[str] = []
    for r in rows:
        for src in r["sources"].split():
            if src in owner:
                dupes.append(f"{src} ({owner[src]} & {r['bl_id']})")
            else:
                owner[src] = r["bl_id"]

    risk_ids = risk_deferred_ids()
    ld = ld_ids()
    adr = adr_revisit_ids()

    if len(set(risk_ids)) != len(risk_ids):
        _fail("duplicate RISK id under a deferred-class heading")

    risk_mapped = sum(1 for i in risk_ids if i in owner)
    adr_mapped = sum(1 for i in adr if i in owner)
    ld_mapped = sum(1 for i in ld if i in owner)

    unmapped_risk = [i for i in risk_ids if i not in owner]
    unmapped_adr = [i for i in adr if i not in owner]
    unmapped_ld = [i for i in ld if i not in owner]

    # sources that reference ids outside the three universes (orphan cite)
    universe = set(risk_ids) | set(ld) | set(adr)
    orphan_sources = sorted(s for s in owner if s not in universe)

    # themes: <=10, every bl_id in exactly one theme
    theme_owner: dict[str, str] = {}
    theme_dupes: list[str] = []
    theme_headings = 0
    if THEMES.exists():
        cur = ""
        for line in THEMES.read_text().splitlines():
            hm = re.match(r"##\s+(T\d+)\b", line)
            if hm:
                cur = hm.group(1)
                theme_headings += 1
                continue
            bm = re.match(r"-\s+\*\*bl_ids:\*\*\s+(.+)$", line)
            if bm:
                for bl in re.findall(r"BL-\d{3}", bm.group(1)):
                    if bl in theme_owner:
                        theme_dupes.append(f"{bl} ({theme_owner[bl]} & {cur})")
                    else:
                        theme_owner[bl] = cur

    citing, missing_homes = deferral_homes(DEFERRALS)
    bl_status = {r["bl_id"]: r["status"] for r in rows}
    homed, unhomed = deferral_open_homes(DEFERRALS, bl_status)
    register = trigger_register(ADR_TRIGGERS)
    trigger_problems = adr_home_problems(adr, owner, bl_status, register)
    risk_dupes = risk_id_duplicates(RISK)
    print(f"risk deferred rows: {risk_mapped}/{len(risk_ids)}")
    print(f"ADR revisit triggers: {adr_mapped}/{len(adr)}")
    print(f"LD rows: {ld_mapped}/{len(ld)}")
    print(f"deferral homes: {len(citing)}/{len(citing) + len(missing_homes)}")
    print(f"deferral open homes: {len(homed)}/{len(homed) + len(unhomed)}")
    print(
        f"ADR trigger homes (open-home rule, {len(register)} register rows): {len(adr) - len(trigger_problems)}/{len(adr)}"
    )
    print(f"duplicate RISK ids (after rename records): {len(risk_dupes)}")
    print(f"duplicate sources: {len(dupes)}")

    ok = True
    if THEMES.exists():
        if theme_headings > 10:
            print(f"  too many themes: {theme_headings} > 10", file=sys.stderr)
            ok = False
        missing_theme = [r["bl_id"] for r in rows if r["bl_id"] not in theme_owner]
        if missing_theme:
            print(f"  bl_ids in no theme: {' '.join(missing_theme)}", file=sys.stderr)
            ok = False
        if theme_dupes:
            print(f"  bl_ids in >1 theme: {'; '.join(theme_dupes)}", file=sys.stderr)
            ok = False
    if unmapped_risk:
        print(f"  unmapped RISK: {' '.join(unmapped_risk)}", file=sys.stderr)
        ok = False
    if unmapped_adr:
        print(f"  unmapped ADR: {' '.join(unmapped_adr)}", file=sys.stderr)
        ok = False
    if unmapped_ld:
        print(f"  unmapped LD: {' '.join(unmapped_ld)}", file=sys.stderr)
        ok = False
    if orphan_sources:
        print(
            f"  orphan sources (not a RISK/ADR/LD id): {' '.join(orphan_sources)}", file=sys.stderr
        )
        ok = False
    if dupes:
        print(f"  double-owned sources: {'; '.join(dupes)}", file=sys.stderr)
        ok = False
    if missing_homes:
        print(
            f"  OPEN/PARTIAL DEFERRALS rows with no BL home: {' '.join(missing_homes)}",
            file=sys.stderr,
        )
        ok = False
    if unhomed:
        print(
            "  OPEN/PARTIAL DEFERRALS rows citing no open BL row (append a `(cites BL-nnn)` "
            f"re-homing annotation): {' '.join(unhomed)}",
            file=sys.stderr,
        )
        ok = False
    if not register:
        print(f"  ADR trigger register missing or empty: {ADR_TRIGGERS}", file=sys.stderr)
        ok = False
    if trigger_problems:
        print(f"  ADR trigger homes: {'; '.join(trigger_problems)}", file=sys.stderr)
        ok = False
    if risk_dupes:
        print(
            f"  RISK ids defined twice with no rename record: {' '.join(risk_dupes)}",
            file=sys.stderr,
        )
        ok = False

    if not ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
