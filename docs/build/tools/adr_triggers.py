#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""adr_triggers.py — the ADR revisit-trigger register and its file-match check (SEED-15, Round 11 T4).

``docs/build/reports/adr_triggers/ADR_TRIGGERS.csv`` (B4 G8-3; F3's ADR-TRIGGER-REGISTER; plan §7 and
Appendix A T4) holds one row per revisit trigger: every ADR's ``## Revisit trigger`` section, plus revisit
triggers the operator accepted outside an ADR (Q-29's operator-accepted-risk revisit). Rows that record an
operator waiver carry its line id (A-6; WV-01…WV-12). Columns — B4 G8-3's seven, then three of SEED-15's:

``adr, trigger_sha256, state, evidence, probe_id, home, last_evaluated, kind, waiver, trigger_text``

* ``trigger_sha256`` — sha256 of the ``## Revisit trigger`` section text **up to the first ``### Trigger
  evaluation``** heading (or the next ``## `` heading, or the end of the file), surrounding blank lines
  stripped (CARRY: SEED-11d → SEED-15). An appended evaluation therefore never changes the hash; an edited
  trigger does. A non-ADR row hashes its ``trigger_text`` cell.
* ``state`` ∈ quiet · fired-unanswered · fired-answered(ref) · superseded(ref) · dormant(reason).
* ``home`` — the BACKLOG row that owns the trigger (``check_backlog.py`` applies the open-home rule).
* ``kind`` ∈ adr · waiver · accepted-risk; ``waiver`` names the operator's waiver line.

``check`` (SEED-15's base + P34.32's full G8-3) verifies the register matches the ADR files: one row
per ADR that has a ``## Revisit trigger`` and no row for an ADR that does not, every hash current, the
state grammar, refs that resolve to an ADR file or a manifest chain row, homes that are BACKLOG rows
— and the **open-home rule**: a home sits on an *open* BACKLOG row, on an *accepted* monitor row
(BL-002) unless the trigger is ``fired-unanswered``, or on a *closed* row only while the trigger is
``quiet`` or ``superseded`` — the same rule ``check_backlog.py`` applies from the BACKLOG side
(F3 NEW-3). ``last_evaluated`` is a ``date -u`` value, evidence is present, every waiver line is
present once, and a ``probe_id`` is honoured when present (the G10 hook: validated as a token, not
required). ``--round-tail <round-start>`` (the closing-rows mode P34.33 calls and the P38 tail uses)
fails when any row's ``last_evaluated`` predates the round start, or a ``fired-unanswered`` row
carries no ``S1… disposition:`` record in its evidence — the stage-1 sweep's routing of the
unanswered trigger. Stdlib only; Python 3.9+::

    python3 docs/build/tools/adr_triggers.py check [--round-tail YYYY-MM-DD]
    python3 docs/build/tools/adr_triggers.py hash docs/adr/ADR-150-coverage-verdict-vocabulary.md
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
REGISTER = "docs/build/reports/adr_triggers/ADR_TRIGGERS.csv"
COLUMNS = [
    "adr",
    "trigger_sha256",
    "state",
    "evidence",
    "probe_id",
    "home",
    "last_evaluated",
    "kind",
    "waiver",
    "trigger_text",
]
KINDS = ("adr", "waiver", "accepted-risk")
# The operator's waiver lines a register row must carry (plan §6.5; ADR-150 D10; round 27 adds WV-12).
WAIVER_LINES = ("A-6",) + tuple(f"WV-{n:02d}" for n in range(1, 13))
STATE_RE = re.compile(
    r"^(?:quiet|fired-unanswered|fired-answered\((?P<answer>[^()]+)\)|superseded\((?P<by>[^()]+)\)"
    r"|dormant\((?P<reason>[^()]+)\))$"
)
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
ROUND_TAIL_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PROBE_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
# A fired-unanswered row's round-tail evidence must record the stage-1 sweep's routing of the
# unanswered trigger — written `S1 disposition: …` (or `S1b`/`S1d` for the naming-the-unit form).
S1_DISPOSITION_RE = re.compile(r"\bS1[a-z]?\s+disposition\b", re.I)
BACKLOG = "docs/build/BACKLOG.csv"
# The open-home rule (F3 NEW-3; the same split check_backlog.py applies from the BACKLOG side).
OPEN_HOME = frozenset({"open"})
MONITOR_HOME = frozenset({"accepted"})
CLOSED_HOME_STATES = frozenset({"quiet", "superseded"})
_EVAL_RE = re.compile(r"^###\s+Trigger evaluation\b")
_FILE_ID_RE = re.compile(r"(?:\d{2,3}[a-z]?_)?([A-Za-z][A-Za-z0-9.-]*)__[^`|\s]*\.md")


def trigger_text(adr_text: str) -> str | None:
    """The ``## Revisit trigger`` section up to the first ``### Trigger evaluation`` (or the next H2)."""
    lines = adr_text.splitlines()
    start = next(
        (i for i, ln in enumerate(lines) if re.match(r"^## Revisit trigger\s*$", ln)), None
    )
    if start is None:
        return None
    body: list[str] = []
    for ln in lines[start + 1 :]:
        if _EVAL_RE.match(ln) or re.match(r"^## (?!#)", ln):
            break
        body.append(ln)
    return "\n".join(body).strip()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def trigger_sha256(adr_text: str) -> str | None:
    text = trigger_text(adr_text)
    return None if text is None else sha256_text(text)


def adr_files(root: pathlib.Path) -> dict[str, pathlib.Path]:
    out: dict[str, pathlib.Path] = {}
    for p in sorted((root / "docs/adr").glob("ADR-*.md")):
        m = re.match(r"(ADR-\d{3})\b", p.name)
        if m:
            out.setdefault(m.group(1), p)
    return out


def chain_ids(root: pathlib.Path) -> set[str]:
    ids: set[str] = set()
    manifest = root / "docs/tickets/00_MANIFEST.md"
    if manifest.is_file():
        for line in manifest.read_text().splitlines():
            if re.match(r"^\|\s*\d+[a-z]?\s*\|", line):
                m = _FILE_ID_RE.search(line)
                if m:
                    ids.add(m.group(1))
    return ids


def backlog_rows(root: pathlib.Path) -> list[dict[str, str]]:
    path = root / BACKLOG
    if not path.is_file():
        return []
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def backlog_ids(root: pathlib.Path) -> set[str]:
    return {r["bl_id"] for r in backlog_rows(root)}


def backlog_status(root: pathlib.Path) -> dict[str, str]:
    return {r["bl_id"]: r.get("status", "") for r in backlog_rows(root)}


def backlog_owner(root: pathlib.Path) -> dict[str, str]:
    """``source-token → bl_id`` — the BACKLOG row whose ``sources`` cell names it (first wins; a
    duplicate-owner source is check_backlog.py's finding, not this one's)."""
    owner: dict[str, str] = {}
    for r in backlog_rows(root):
        for src in r.get("sources", "").split():
            owner.setdefault(src, r["bl_id"])
    return owner


def load(root: pathlib.Path) -> tuple[list[str], list[dict[str, str]]]:
    path = root / REGISTER
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def _ref_ok(ref: str, adrs: dict[str, pathlib.Path], chain: set[str]) -> bool:
    ref = ref.strip()
    if re.fullmatch(r"ADR-\d{3}", ref):
        return ref in adrs
    return ref in chain


def check(
    root: pathlib.Path,
    waiver_lines: tuple[str, ...] = WAIVER_LINES,
    round_tail: str | None = None,
) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    path = root / REGISTER
    if not path.is_file():
        return [f"{REGISTER} not found"], {}
    header, rows = load(root)
    adrs = adr_files(root)
    chain = chain_ids(root)
    backlog = backlog_ids(root)
    bl_status = backlog_status(root)
    bl_owner = backlog_owner(root)
    with_trigger = {a: p for a, p in adrs.items() if trigger_text(p.read_text()) is not None}
    stats = {"rows": len(rows), "adr_triggers": len(with_trigger), "evaluated": 0, "probes": 0}
    if header != COLUMNS:
        errors.append(f"header {header} != {COLUMNS}")
        return errors, stats
    if not rows:
        errors.append("the register has no rows — nothing evaluated (SIG-ENG-042)")
    if round_tail is not None and not ROUND_TAIL_RE.match(round_tail):
        errors.append(f"--round-tail {round_tail!r} is not a YYYY-MM-DD round-start date")
    seen: dict[str, int] = {}
    waivers: dict[str, int] = {}
    for n, r in enumerate(rows, start=2):
        stats["evaluated"] += 1
        key = r["adr"]
        where = f"line {n} ({key})"
        seen[key] = seen.get(key, 0) + 1
        if r["kind"] not in KINDS:
            errors.append(f"{where}: kind {r['kind']!r} not in {KINDS}")
        if r["waiver"]:
            for w in r["waiver"].split(";"):
                waivers[w.strip()] = waivers.get(w.strip(), 0) + 1
            if r["kind"] != "waiver":
                errors.append(f"{where}: a row naming waiver {r['waiver']} must be kind 'waiver'")
        elif r["kind"] == "waiver":
            errors.append(f"{where}: kind 'waiver' without a waiver line id")
        if r["kind"] == "accepted-risk":
            if not r["trigger_text"].strip():
                errors.append(f"{where}: an accepted-risk row records its trigger_text")
            elif r["trigger_sha256"] != sha256_text(r["trigger_text"].strip()):
                errors.append(f"{where}: trigger_sha256 does not match its trigger_text")
        else:
            if key not in adrs:
                errors.append(f"{where}: {key} has no file in docs/adr/")
            elif key not in with_trigger:
                errors.append(f"{where}: {key} has no '## Revisit trigger' section")
            else:
                current = trigger_sha256(with_trigger[key].read_text())
                if r["trigger_sha256"] != current:
                    errors.append(
                        f"{where}: trigger_sha256 is stale — the revisit trigger changed (current {current}); "
                        "re-evaluate the trigger and record the new hash"
                    )
            if r["trigger_text"]:
                errors.append(
                    f"{where}: an ADR row keeps its trigger text in the ADR, not in trigger_text"
                )
        m = STATE_RE.match(r["state"])
        state_kind = r["state"].split("(", 1)[0].strip()
        if not m:
            errors.append(f"{where}: state {r['state']!r} is off the G8-3 grammar")
        else:
            for ref in filter(None, [m.group("answer"), m.group("by")]):
                if not _ref_ok(ref, adrs, chain):
                    errors.append(
                        f"{where}: state ref {ref!r} is neither an ADR file nor a manifest chain row"
                    )
        if not re.fullmatch(r"BL-\d{3}", r["home"]) or r["home"] not in backlog:
            errors.append(f"{where}: home {r['home']!r} is not a BACKLOG row")
        else:
            # register home == the BACKLOG row whose sources name the ADR (check_backlog.py
            # verifies the same edge from the BACKLOG side; the register checker judges it too)
            owner_bl = bl_owner.get(key)
            if key.startswith("ADR-") and owner_bl and r["home"] != owner_bl:
                errors.append(
                    f"{where}: home {r['home']!r} != BACKLOG owner {owner_bl} "
                    "(the BL row whose sources name the ADR)"
                )
            home_status = bl_status.get(r["home"], "")
            if home_status in OPEN_HOME:
                pass
            elif home_status in MONITOR_HOME:
                if state_kind == "fired-unanswered":
                    errors.append(
                        f"{where}: home {r['home']} is an accepted monitor row while the trigger "
                        "is fired-unanswered — an unanswered trigger needs an open home (F3 NEW-3)"
                    )
            elif home_status == "closed":
                if state_kind not in CLOSED_HOME_STATES:
                    errors.append(
                        f"{where}: home {r['home']} is closed while the trigger is {r['state']!r} "
                        "— a closed home only for quiet/superseded (F3 NEW-3)"
                    )
            elif home_status:
                errors.append(
                    f"{where}: home {r['home']} has BACKLOG status {home_status!r} "
                    "(open/accepted/closed expected)"
                )
        if r["probe_id"]:
            if not PROBE_ID_RE.fullmatch(r["probe_id"]):
                errors.append(f"{where}: probe_id {r['probe_id']!r} is not a probe id token")
            else:
                stats["probes"] += 1
        if not TS_RE.match(r["last_evaluated"]):
            errors.append(
                f"{where}: last_evaluated {r['last_evaluated']!r} is not a date -u timestamp"
            )
        if not r["evidence"].strip():
            errors.append(f"{where}: evidence is empty")
        if round_tail is not None:
            if TS_RE.match(r["last_evaluated"]) and r["last_evaluated"][:10] < round_tail:
                errors.append(
                    f"{where}: last_evaluated {r['last_evaluated']!r} predates the round start "
                    f"{round_tail} (--round-tail: every row is re-evaluated inside the round)"
                )
            if state_kind == "fired-unanswered" and not S1_DISPOSITION_RE.search(r["evidence"]):
                errors.append(
                    f"{where}: fired-unanswered with no 'S1… disposition:' record in evidence "
                    "(--round-tail: an unanswered trigger must show its stage-1 routing)"
                )
    for key, count in sorted(seen.items()):
        if count > 1:
            errors.append(f"{key}: {count} register rows — one row per revisit trigger")
    for adr in sorted(set(with_trigger) - set(seen)):
        errors.append(f"{adr}: has a '## Revisit trigger' but no register row")
    for line in waiver_lines:
        if waivers.get(line, 0) != 1:
            errors.append(
                f"waiver line {line}: {waivers.get(line, 0)} register rows (expected exactly 1)"
            )
    return errors, stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--root", default=str(ROOT))
    sub = ap.add_subparsers(dest="cmd")
    cp = sub.add_parser("check", help="verify the register matches the ADR files")
    cp.add_argument(
        "--round-tail",
        metavar="YYYY-MM-DD",
        default=None,
        help="round-tail mode: every row's last_evaluated must fall inside the round and every "
        "fired-unanswered row must carry an 'S1… disposition:' record in evidence",
    )
    hp = sub.add_parser("hash", help="print an ADR's trigger_sha256")
    hp.add_argument("adr_file")
    args = ap.parse_args(argv)
    root = pathlib.Path(args.root).resolve()
    if args.cmd == "hash":
        digest = trigger_sha256(pathlib.Path(args.adr_file).read_text())
        if digest is None:
            print("no '## Revisit trigger' section", file=sys.stderr)
            return 1
        print(digest)
        return 0
    if args.cmd == "check":
        errors, stats = check(root, round_tail=args.round_tail)
        if stats:
            print(
                f"offered: {stats['adr_triggers']} ADR revisit triggers, {stats['rows']} register rows · "
                f"evaluated: {stats['evaluated']} rows"
                + (f", {stats['probes']} carrying probe_id" if stats.get("probes") else "")
            )
        if errors:
            print(f"FAIL: {len(errors)} problem(s):")
            for e in errors:
                print("  -", e)
            return 1
        tail = f" · round-tail from {args.round_tail} OK" if args.round_tail else ""
        print(
            f"{stats['rows']} rows OK — one per revisit trigger, hashes current, waivers {', '.join(WAIVER_LINES)} present{tail}"
        )
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
