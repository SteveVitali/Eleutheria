#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Consistency checker for the spec source tree (P20.2 deliverable, SIG-ENG-039).

The canonical spec ``docs/2_canonical_design_spec.md`` is a build artifact assembled
from ``docs/research/_meta/spec_src/*.md`` by ``BUILD.sh`` (SIG-ENG-003). This tool
asserts, with the standard library only and in well under a second:

  * **byte-identical reproduction** — concatenating the ordered ``spec_src`` section
    files (exactly as ``BUILD.sh`` does) reproduces the committed spec byte for byte;
  * **Appendix F completeness** — every ``docs/adr/ADR-*.md`` file appears as a row in
    Appendix F, and Appendix F names no ADR that lacks a file (SIG-ENG-039);
  * **requirement-id integrity** — the requirement-definition count equals
    ``668 + N`` fold-backs (N = ids added after the 46-ticket build), there are no
    duplicate or malformed ids, and none of the RESERVED ids (§0.3) is defined;
  * **reference closure** — every ``SIG-*`` id *referenced* in the spec is either
    defined or listed as reserved (§0.3).

Usage (from anywhere)::

    python docs/build/tools/check_spec_src.py

Exits 0 and prints a short summary when everything holds; exits 1 and prints each
problem otherwise.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SPEC = ROOT / "docs/2_canonical_design_spec.md"
SPEC_SRC = ROOT / "docs/research/_meta/spec_src"
ADR_DIR = ROOT / "docs/adr"

# The requirement-definition count after the 46-ticket build (P19.2 froze this at 668),
# plus the fold-back ids this ticket (P20.2) appended to the spec via spec_src.
BASELINE_IDS = 668
FOLD_BACK_IDS = ["SIG-UI-047", "SIG-EVID-020", "SIG-ENG-039"]
EXPECTED_IDS = BASELINE_IDS + len(FOLD_BACK_IDS)

# RESERVED-but-unassigned ids (§0.3): allocated in drafting, merged before publication,
# and MUST NOT be assigned to a new requirement so external references fail loudly.
RESERVED = {
    "SIG-ENG-006", "SIG-ENG-007", "SIG-ENG-008", "SIG-ENG-009",
    "SIG-ENG-028", "SIG-ENG-029",
}

# A requirement *definition*: a bolded id followed by a level keyword. Matches the
# regex the sibling checker (check_coverage_matrix.py) already relies on.
DEF_RE = re.compile(r"\*\*(SIG-[A-Z]+-\d+[a-z]?) \((?:MUST|SHOULD|MAY|RATIONALE)")
# Any id token anywhere (references included).
REF_RE = re.compile(r"SIG-[A-Z]+-\d+[a-z]?")
# A well-formed id: AREA is 3-6 uppercase letters, ordinal zero-padded, optional suffix.
GRAMMAR_RE = re.compile(r"^SIG-[A-Z]{2,8}-\d{3}[a-z]?$")
ADR_FILE_RE = re.compile(r"^(ADR-\d+)")
ADR_ROW_RE = re.compile(r"^\| (ADR-\d+) \|")


def assembled() -> str:
    """Reproduce BUILD.sh: cat each ordered ``[0-9]*.md`` then a newline."""
    parts = []
    for f in sorted(SPEC_SRC.glob("[0-9]*.md")):
        parts.append(f.read_text())
        parts.append("\n")
    return "".join(parts)


def appendix_f_ids(spec_text: str) -> set[str]:
    """ADR ids named in the Appendix F index table."""
    ids: set[str] = set()
    in_appf = False
    for line in spec_text.splitlines():
        if line.startswith("# Appendix F"):
            in_appf = True
            continue
        if in_appf and line.startswith("# Appendix G"):
            break
        if in_appf:
            m = ADR_ROW_RE.match(line)
            if m:
                ids.add(m.group(1))
    return ids


def main() -> int:
    errors: list[str] = []

    if not SPEC.exists():
        print(f"check_spec_src: FAIL — {SPEC} not found", file=sys.stderr)
        return 1
    committed = SPEC.read_text()

    # 1) byte-identical reproduction
    if assembled() != committed:
        errors.append(
            "BUILD.sh reproduction is NOT byte-identical: re-run "
            "`sh docs/research/_meta/spec_src/BUILD.sh` and commit the result"
        )

    # 2) Appendix F <-> docs/adr file set
    adr_files = {ADR_FILE_RE.match(p.name).group(1) for p in ADR_DIR.glob("ADR-*.md")}
    appf = appendix_f_ids(committed)
    missing_from_appf = sorted(adr_files - appf)
    ghost_in_appf = sorted(appf - adr_files)
    if missing_from_appf:
        errors.append(f"ADR files absent from Appendix F: {missing_from_appf}")
    if ghost_in_appf:
        errors.append(f"Appendix F names ADRs with no file: {ghost_in_appf}")

    # 3) requirement-id integrity
    defs = DEF_RE.findall(committed)
    seen: dict[str, int] = {}
    for d in defs:
        seen[d] = seen.get(d, 0) + 1
    dupes = sorted(k for k, v in seen.items() if v > 1)
    if dupes:
        errors.append(f"duplicate requirement definitions: {dupes}")

    unique_defs = set(seen)
    if len(unique_defs) != EXPECTED_IDS:
        errors.append(
            f"requirement-id count is {len(unique_defs)}, expected {EXPECTED_IDS} "
            f"(= {BASELINE_IDS} baseline + {len(FOLD_BACK_IDS)} fold-backs)"
        )

    malformed = sorted(i for i in unique_defs if not GRAMMAR_RE.match(i))
    if malformed:
        errors.append(f"malformed ids (violate the §0.3 grammar): {malformed}")

    reserved_used = sorted(unique_defs & RESERVED)
    if reserved_used:
        errors.append(f"RESERVED ids assigned to a definition (§0.3 forbids): {reserved_used}")

    for fb in FOLD_BACK_IDS:
        if fb not in unique_defs:
            errors.append(f"declared fold-back id {fb} is not defined in the spec")

    # 4) reference closure: every referenced id is defined or reserved
    referenced = set(REF_RE.findall(committed))
    dangling = sorted(referenced - unique_defs - RESERVED)
    if dangling:
        errors.append(f"referenced but neither defined nor reserved (§0.3): {dangling}")

    if errors:
        print(f"check_spec_src: FAIL — {len(errors)} problem(s):")
        for e in errors:
            print("  -", e)
        return 1

    print("check_spec_src: OK")
    print(f"  BUILD.sh reproduction: byte-identical ({len(committed)} bytes)")
    print(f"  Appendix F: {len(appf)} ADRs, equal to the docs/adr/ file set")
    print(f"  requirement ids: {len(unique_defs)} (= {BASELINE_IDS} + {len(FOLD_BACK_IDS)} fold-backs)")
    print(f"  no duplicate / malformed / reserved ids; reference closure holds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
