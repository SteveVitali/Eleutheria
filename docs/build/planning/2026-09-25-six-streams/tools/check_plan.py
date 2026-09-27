#!/usr/bin/env python3
"""Strict, read-only validation of the dated Round-10 plan and its integration."""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[3]


def structural_errors(plan: dict, earlier: dict[str, int]) -> list[str]:
    errors = []
    ids = [t["id"] for t in plan["tickets"]]
    seqs = [t["sequence"] for t in plan["tickets"]]
    for label, values in (("ticket", ids), ("sequence", seqs)):
        errors.extend(f"duplicate {label}: {v}" for v, count in Counter(values).items() if count != 1)
    first = plan.get("first_sequence", 161)
    if not isinstance(first, int) or isinstance(first, bool) or first < 1:
        errors.append("first_sequence must be a positive integer")
        first = 161
    if seqs != list(range(first, first + len(seqs))):
        errors.append(f"new chain sequence must be contiguous from {first}")
    if plan.get("last_sequence") != first + len(seqs) - 1:
        errors.append("last_sequence does not match the declared chain")
    for ticket_id, sequence in earlier.items():
        if ticket_id not in ids and sequence in seqs:
            errors.append(f"sequence {sequence} already occupied by {ticket_id}")
    positions = earlier | {t["id"]: t["sequence"] for t in plan["tickets"]}
    owners = Counter(r for t in plan["tickets"] for r in t["requirements"])
    for rid in plan["requirements"]:
        if owners[rid] != 1:
            errors.append(f"{rid}: expected one owner, got {owners[rid]}")
    errors.extend(f"undefined owned requirement: {r}" for r in owners if r not in plan["requirements"])
    for t in plan["tickets"]:
        if t["filename"] != f'{t["sequence"]}_{t["id"]}__{t["slug"]}.md':
            errors.append(f'{t["id"]}: filename/identity mismatch')
        for dep in t["depends"]:
            if dep not in positions or positions[dep] >= t["sequence"]:
                errors.append(f'{t["id"]}: missing/forward dependency {dep}')
        if not t["deliverables"] or not t["acceptance"] or not t["gate"] or not t["live"]:
            errors.append(f'{t["id"]}: incomplete contract')
    tail = [t["kind"] for t in plan["tickets"][-9:]]
    if tail != ["capstone"] * 3 + ["gate"] + ["reconcile"] * 3 + ["docs"] * 2:
        errors.append("full nine-row tail missing or misordered")
    if plan["tickets"][-6]["id"] != "GATE-ACCEPT":
        errors.append("acceptance marker missing from full tail")
    return errors


def main() -> int:
    plan = json.loads((HERE / "PLAN.json").read_text())
    manifest = (ROOT / "docs/tickets/00_MANIFEST.md").read_text()
    rows = re.findall(r"^\|\s*(\d+)\s*\|\s*`?([^`| ]+\.md)`?", manifest, re.M)
    earlier = {}
    for seq, name in rows:
        name = re.sub(r"^\d+[a-z]?_", "", name)
        earlier[name.split("__")[0]] = int(seq)
    errors = structural_errors(plan, earlier)
    spec = (ROOT / "docs/2_canonical_design_spec.md").read_text()
    definitions = re.findall(r"\*\*(SIG-[A-Z]+-\d+[a-z]?) \((?:MUST|SHOULD|MAY|RATIONALE)", spec)
    with (ROOT / "docs/build/COVERAGE_MATRIX.csv").open(newline="") as f:
        coverage = {r["id"]: r for r in csv.DictReader(f)}
    with (HERE / "REQUIREMENTS.csv").open(newline="") as f:
        ownership = list(csv.DictReader(f))
    if len(ownership) != len(plan["requirements"]):
        errors.append("ownership row count mismatch")
    for t in plan["tickets"]:
        path = ROOT / "docs/tickets" / t["filename"]
        if not path.is_file():
            errors.append(f"missing contract {path.name}")
            continue
        body = path.read_text()
        if manifest.count('`' + t["filename"] + '`') != 1:
            errors.append(f'{t["id"]}: manifest needs one contract row')
        if t["kind"] in {"gate", "human"} and "**Run:**" in body:
            errors.append(f'{t["id"]}: marker must not dispatch implement-spec')
        for rid in t["requirements"]:
            if definitions.count(rid) != 1:
                errors.append(f"{rid}: canonical definition count != 1")
            row = coverage.get(rid)
            if not row or row["owning_tickets"] != t["id"]:
                errors.append(f"{rid}: missing/wrong coverage owner")
            if rid not in body.split("## Requirement IDs to satisfy and stamp in the PR\n", 1)[-1].split("## Cross-cutting", 1)[0]:
                errors.append(f"{rid}: not stamped in owner contract")
    for name in ("S1-evidence-integrity", "S2-local-dossiers", "S3-human-evaluation", "S4-public-product", "S5-source-strategy", "S6-build-memory"):
        if not (HERE / "research" / (name + ".md")).is_file():
            errors.append(f"missing research {name}")
    adr_ids = [re.match(r"ADR-\d+", p.name)[0] for p in (ROOT / "docs/adr").glob("ADR-*.md")]
    errors.extend(f"colliding ADR prefix {r}" for r, n in Counter(adr_ids).items() if n > 1)
    for f in ("BRIEF.md", "DESIGN.md", "HANDOFF.md", "VALIDATION.md", "REVIEW_CLOSURE.md"):
        if not (HERE / f).is_file():
            errors.append(f"missing handoff artifact {f}")
    if errors:
        print("check_plan: FAIL\n" + "\n".join("- " + e for e in errors))
        return 1
    print(f'check_plan: OK — {len(plan["tickets"])} ordered rows; {len(plan["requirements"])} singly owned requirements; full9 tail; six research streams')
    return 0


if __name__ == "__main__":
    sys.exit(main())
