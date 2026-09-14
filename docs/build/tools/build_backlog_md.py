#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Render ``docs/build/BACKLOG.md`` from ``docs/build/BACKLOG.csv`` (P24.5).

``BACKLOG.md`` is the committed human-readable mirror of the normalized backlog.
It drifted: later tickets flipped CSV ``status``/``landing`` cells (P21.x closures,
the capstone reconcile, P24.5's triage) without re-rendering the mirror, so the
``.md`` showed stale titles, statuses and groupings. This tool makes the mirror a
pure function of the CSV — run it after any backlog edit:

    python3 docs/build/tools/build_backlog_md.py            # rewrite BACKLOG.md
    python3 docs/build/tools/build_backlog_md.py --check    # exit 1 if stale

Standard library only; deterministic (stable landing order, row order preserved).
``tests/unit/test_backlog_housekeeping.py`` runs ``--check`` so a stale mirror
fails ``make check``.
"""

from __future__ import annotations

import csv
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
BACKLOG = ROOT / "docs/build/BACKLOG.csv"
MIRROR = ROOT / "docs/build/BACKLOG.md"

# Landing groups render in this order: closed-by:<ticket> (numeric), `accepted`,
# P<n>.<m> tickets (numeric), human-gate:HG-<nn> (numeric), then the P<n>+
# unscheduled buckets (numeric). Anything else sorts last, alphabetically.
_P = re.compile(r"P(\d+)\.(\d+)")
_CLOSED = re.compile(r"closed-by:P(\d+)\.(\d+)")
_GATE = re.compile(r"human-gate:HG-(\d+)")
_BUCKET = re.compile(r"P(\d+)\+")


def _landing_key(landing: str) -> tuple[int, int, str]:
    m = _CLOSED.fullmatch(landing)
    if m:
        return (0, int(m.group(1)) * 10 + int(m.group(2)), landing)
    if landing == "accepted":
        return (1, 0, landing)
    m = _P.fullmatch(landing)
    if m:
        return (2, int(m.group(1)) * 10 + int(m.group(2)), landing)
    m = _GATE.fullmatch(landing)
    if m:
        return (3, int(m.group(1)), landing)
    m = _BUCKET.fullmatch(landing)
    if m:
        return (4, int(m.group(1)), landing)
    return (5, 0, landing)


def load_rows() -> list[dict[str, str]]:
    with BACKLOG.open(newline="") as fh:
        return list(csv.DictReader(fh))


def render(rows: list[dict[str, str]]) -> str:
    out = [
        "# BACKLOG — the one normalized post-build backlog (P20.1)",
        "",
        "Grouped by `landing`. Machine-readable form: `BACKLOG.csv`; themes:",
        "`reports/BACKLOG_THEMES.md`; the id space (`BL-nnn`) and the `landing` enum",
        "are owned by P20.1 (extended by P24.5: `closed-by:P<n>.<m>`, `P<n>+` phase",
        "buckets). Every RISK deferred row, every ADR revisit trigger, and every LD",
        "row appears in exactly one item's `sources` (validated by",
        "`docs/build/tools/check_backlog.py`). Later tickets set `status=closed`",
        "when they retire an item. A reviewer resolves any deferred RISK row's fate",
        "in <=2 hops: RISK -> `-> BL-nnn` in `docs/risk_register.md` -> the item's",
        "landing here. Regenerate this file after any backlog edit:",
        "`python3 docs/build/tools/build_backlog_md.py`.",
        "",
    ]
    landings = sorted({r["landing"] for r in rows}, key=_landing_key)
    for land in landings:
        group = [r for r in rows if r["landing"] == land]
        out.append(f"## {land}")
        out.append("")
        for r in group:
            gate = f" · gate {r['gate']}" if r["gate"] else ""
            out.append(
                f"- **{r['bl_id']}** — {r['title']} · _{r['type']}_ · {r['size']}"
                f" · status={r['status']}{gate}"
            )
            out.append(f"  - sources: {r['sources']}")
        out.append("")
    for bucket in (land for land in landings if _BUCKET.fullmatch(land)):
        unscheduled = [r for r in rows if r["landing"] == bucket]
        out.append(
            f"## {bucket} unscheduled (post-Round-4 manifest — the next planning round owns these)"
        )
        out.append("")
        out.append(
            "Triaged by P24.5 (META.1 / GL-META-01, 2026-09-13): each row was"
            " checked against the tree — none is landed, none is owned by a"
            " remaining manifest ticket (rows 84–87 are JURIS.2/CCOPS.1/REC.1/"
            "GATE-ACCEPT). `P25+` = the planning round after this manifest,"
            " replacing the stale `P22+` bucket (the P22 pass closed unscheduled)."
            " Rows conditioned on real post-go-live state are additionally"
            " promoted to `docs/tickets/DEFERRALS.md` (D-META.1-*; the BL row"
            " stays the normalized-debt record)."
        )
        out.append("")
        for r in unscheduled:
            out.append(
                f"- **{r['bl_id']}** — {r['title']} · _{r['type']}_ · {r['size']}"
                f" · sources: {r['sources']}"
            )
        out.append("")
    return "\n".join(out)


def main() -> int:
    rendered = render(load_rows())
    if "--check" in sys.argv[1:]:
        current = MIRROR.read_text() if MIRROR.exists() else ""
        if current != rendered:
            print(
                "check_backlog_md: FAIL — docs/build/BACKLOG.md is stale;"
                " regenerate with `python3 docs/build/tools/build_backlog_md.py`",
                file=sys.stderr,
            )
            return 1
        print("check_backlog_md: BACKLOG.md matches BACKLOG.csv")
        return 0
    MIRROR.write_text(rendered)
    print(f"wrote {MIRROR} ({len(rendered)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
