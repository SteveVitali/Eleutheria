# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.67 (R11-CONF-14 / ADR-154): regenerate the Stream-L acceptance record
``exports/src/exports/data/streaml_acceptance.json`` (``sig.streaml-acceptance/1``)
and its readout ``docs/build/reports/P37.67_streaml_acceptance.md``.

Committed inputs only: the check registry (post-flip), the historical L2
metrics CSV, the landed-row census read off BUILD_INDEX, the committed
``sig.quality-page/1`` fixture artifact, and the deterministic fixture
corpus's real placement-R report (the same harness the release gate
consumes). The live re-measurement leg is declared
``prepared_not_executed`` — this run asserts no release measurement.

Run:  uv run python scripts/eval/run_streaml_acceptance.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "exports" / "src" / "exports" / "data"
OUT_JSON = DATA / "streaml_acceptance.json"
OUT_MD = REPO / "docs" / "build" / "reports" / "P37.67_streaml_acceptance.md"
L2_CSV = REPO / "docs" / "build" / "planning" / "2026-09-30-next-phase" / "data" / "l2_metrics.csv"
BUILD_INDEX = REPO / "docs" / "build" / "BUILD_INDEX.md"

_LANDED_RE = re.compile(r"^\|\s*\d+\s*\|\s*(P\d+[0-9a-z.]*)\s*\|")


def _landed_tickets() -> frozenset[str]:
    """Every ticket id the BUILD_INDEX records as a landed row."""
    out: set[str] = set()
    for line in BUILD_INDEX.read_text(encoding="utf-8").splitlines():
        m = _LANDED_RE.match(line)
        if m:
            out.add(m.group(1))
    return frozenset(out)


def build_doc(generated_at: str | None = None) -> dict:
    """Assemble the record — the same calls the committed bytes came from."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from run_quality_page import build_fixture_page

    from exports import quality as eq
    from exports import streaml_acceptance as sa

    registry = eq.load_registry()
    with L2_CSV.open(encoding="utf-8", newline="") as f:
        l2_rows = list(csv.DictReader(f))
    page = build_fixture_page()
    reports = {"R": page["report"]}
    doc = sa.build_acceptance(
        registry=registry,
        l2_rows=l2_rows,
        landed=_landed_tickets(),
        reports=reports,
        quality_page=page,
        generated_at=generated_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    errors = sa.acceptance_lint_errors(doc)
    if errors:
        raise SystemExit("sig.streaml-acceptance/1 failed its own lint: " + "; ".join(errors))
    return doc


def main() -> int:
    from exports import streaml_acceptance as sa

    doc = build_doc()
    OUT_JSON.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    OUT_MD.write_text(sa.render_readout(doc), encoding="utf-8")
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
