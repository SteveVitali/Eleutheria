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

``check`` (this unit's scope) verifies the register matches the ADR files: one row per ADR that has a
``## Revisit trigger`` and no row for an ADR that does not, every hash current, the state grammar, refs that
resolve to an ADR file or a manifest chain row, homes that are BACKLOG rows, ``last_evaluated`` a ``date -u``
value, and every waiver line present once. The full G8-3 checker — open homes by state, the round-tail mode,
probe hooks — is P34.32's (R11-MEM-09). Stdlib only; Python 3.9+::

    python3 docs/build/tools/adr_triggers.py check
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


def backlog_ids(root: pathlib.Path) -> set[str]:
    path = root / "docs/build/BACKLOG.csv"
    if not path.is_file():
        return set()
    with path.open(newline="") as fh:
        return {r["bl_id"] for r in csv.DictReader(fh)}


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
    root: pathlib.Path, waiver_lines: tuple[str, ...] = WAIVER_LINES
) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    path = root / REGISTER
    if not path.is_file():
        return [f"{REGISTER} not found"], {}
    header, rows = load(root)
    adrs = adr_files(root)
    chain = chain_ids(root)
    backlog = backlog_ids(root)
    with_trigger = {a: p for a, p in adrs.items() if trigger_text(p.read_text()) is not None}
    stats = {"rows": len(rows), "adr_triggers": len(with_trigger), "evaluated": 0}
    if header != COLUMNS:
        errors.append(f"header {header} != {COLUMNS}")
        return errors, stats
    if not rows:
        errors.append("the register has no rows — nothing evaluated (SIG-ENG-042)")
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
        if not TS_RE.match(r["last_evaluated"]):
            errors.append(
                f"{where}: last_evaluated {r['last_evaluated']!r} is not a date -u timestamp"
            )
        if not r["evidence"].strip():
            errors.append(f"{where}: evidence is empty")
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
    sub.add_parser("check", help="verify the register matches the ADR files")
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
        errors, stats = check(root)
        if stats:
            print(
                f"offered: {stats['adr_triggers']} ADR revisit triggers, {stats['rows']} register rows · "
                f"evaluated: {stats['evaluated']} rows"
            )
        if errors:
            print(f"FAIL: {len(errors)} problem(s):")
            for e in errors:
                print("  -", e)
            return 1
        print(
            f"{stats['rows']} rows OK — one per revisit trigger, hashes current, waivers {', '.join(WAIVER_LINES)} present"
        )
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
