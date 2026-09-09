#!/usr/bin/env python3
"""Consistency checker for docs/build/COVERAGE_MATRIX.csv (P19.2 deliverable).

Stdlib only. Runs in <1 s. Usage:

    python docs/build/tools/check_coverage_matrix.py docs/build/COVERAGE_MATRIX.csv

Asserts, per the P19.2 ticket contract:
  * exactly 668 data rows (+ header);
  * every ``id`` is a requirement id defined in docs/2_canonical_design_spec.md;
  * no duplicate ids;
  * every enum column (level / class / verdict / routing) holds a valid value;
  * ``routing`` is non-``—`` for every non-MET verdict (MET and N/A-RATIONALE may be ``—``);
  * ``evidence`` is non-blank for every MET / MET-DIFFERENTLY row.

On success prints ``668 rows OK`` and exits 0; on any failure prints each problem
and exits 1.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

EXPECTED_ROWS = 668
HEADER = [
    "id", "level", "spec_section", "class", "verdict", "evidence",
    "owning_tickets", "tests", "adrs", "risk_rows", "routing", "note",
]

LEVELS = {"MUST", "SHOULD", "MAY", "RATIONALE"}
CLASSES = {
    "covered+tested", "covered+untested", "deferred(RISK)", "deviated(ADR)",
    "rationale-only", "process/governance", "unreferenced",
}
VERDICTS = {"MET", "MET-DIFFERENTLY", "PARTIAL", "MISSING", "AT-RISK-INTEGRATION", "N/A-RATIONALE"}
# routing enum owned by P19.2. NOTE: the ticket body lists P21.2..P21.8 but its own
# notes/DECISION_MEMO route two id groups to P21.1 (Stage-0 outreach) and P21.9 (P17
# pathway ingestion); the enum is extended to include them (recorded in
# CAPSTONE_GAP_ANALYSIS.md method). ``P19.4:L`` is intentionally NOT allowed.
ROUTINGS = {
    "—", "P19.3", "P19.4:S", "P19.4:M",
    "P21.1", "P21.2", "P21.3", "P21.4", "P21.5", "P21.6", "P21.7", "P21.8", "P21.9",
    "P20.1:backlog", "P20.2:spec", "accepted",
}
# verdicts that require a non-"—" routing (a gap must be routed somewhere)
NON_MET_VERDICTS = {"MET-DIFFERENTLY", "PARTIAL", "MISSING", "AT-RISK-INTEGRATION"}

ID_DEF_RE = re.compile(r"\*\*(SIG-[A-Z]+-\d+[a-z]?) \((?:MUST|SHOULD|MAY|RATIONALE)")


def spec_ids(spec_path: Path) -> set[str]:
    ids = set()
    for line in spec_path.read_text().splitlines():
        ids.update(ID_DEF_RE.findall(line))
    return ids


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_coverage_matrix.py <COVERAGE_MATRIX.csv>", file=sys.stderr)
        return 2
    csv_path = Path(argv[1]).resolve()
    spec_path = csv_path.parent.parent / "2_canonical_design_spec.md"
    if not spec_path.exists():  # fall back to repo layout docs/build/COVERAGE_MATRIX.csv
        spec_path = csv_path.parents[1] / "2_canonical_design_spec.md"

    errors: list[str] = []
    defined = spec_ids(spec_path)
    if len(defined) != EXPECTED_ROWS:
        errors.append(f"spec defines {len(defined)} ids, expected {EXPECTED_ROWS}")

    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    if header != HEADER:
        errors.append(f"header mismatch:\n  got {header}\n  want {HEADER}")

    if len(rows) != EXPECTED_ROWS:
        errors.append(f"{len(rows)} data rows, expected {EXPECTED_ROWS}")

    seen: set[str] = set()
    for n, row in enumerate(rows, start=2):
        if len(row) != len(HEADER):
            errors.append(f"row {n}: has {len(row)} columns, expected {len(HEADER)}")
            continue
        rid, level, _section, klass, verdict, evidence = row[0], row[1], row[2], row[3], row[4], row[5]
        routing = row[10]
        if rid in seen:
            errors.append(f"row {n}: duplicate id {rid}")
        seen.add(rid)
        if rid not in defined:
            errors.append(f"row {n}: id {rid} is not defined in the spec")
        if level not in LEVELS:
            errors.append(f"row {n} ({rid}): bad level {level!r}")
        if klass not in CLASSES:
            errors.append(f"row {n} ({rid}): bad class {klass!r}")
        if verdict not in VERDICTS:
            errors.append(f"row {n} ({rid}): bad verdict {verdict!r}")
        if routing not in ROUTINGS:
            errors.append(f"row {n} ({rid}): bad routing {routing!r}")
        if verdict in NON_MET_VERDICTS and routing == "—":
            errors.append(f"row {n} ({rid}): verdict {verdict} requires a non-'—' routing")
        if verdict in {"MET", "MET-DIFFERENTLY"} and not evidence.strip():
            errors.append(f"row {n} ({rid}): verdict {verdict} requires non-blank evidence")

    missing = defined - seen
    if missing:
        errors.append(f"{len(missing)} spec ids missing from the matrix: {sorted(missing)[:10]}...")

    # L1 cross-check: every "nowhere-referenced" seed id must be class != covered+tested,
    # OR carry an evidence path proving a test exists (SCOPING_ID_LISTS.md §L1; the list is
    # a seed, not a verdict). Skipped if the lists file is absent.
    lists_path = csv_path.parent / "SCOPING_ID_LISTS.md"
    if lists_path.exists():
        body = lists_path.read_text()
        l1_block = body.split("## L1", 1)[1].split("```", 2)[1]
        l1 = set(re.findall(r"SIG-[A-Z]+-\d+[a-z]?", l1_block))
        by_id = {r[0]: r for r in rows if len(r) == len(HEADER)}
        for rid in sorted(l1):
            r = by_id.get(rid)
            if r is None:
                errors.append(f"L1 id {rid} not in matrix")
                continue
            if r[3] == "covered+tested" and not r[7].strip("—").strip():
                errors.append(f"L1 id {rid} is covered+tested without a test evidence path")
        print(f"L1 cross-check: {len(l1)} seed ids OK")

    if errors:
        print(f"FAIL: {len(errors)} problem(s):")
        for e in errors:
            print("  -", e)
        return 1
    print(f"{EXPECTED_ROWS} rows OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
