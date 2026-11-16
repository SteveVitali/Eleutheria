# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.45 (CONF-12, SIG-CONF-011 + SIG-CONF-001/010): regenerate the canonical
fixtures-mode quality artifact ``exports/src/exports/data/quality_page.json``
(``sig.quality-page/1``).

The committed record is GENERATED, never hand-written: the script assembles
a small deterministic scan dir from committed bytes (a few declared
``sites.jsonl`` fixture rows, a dossier doc whose inflation block derives
from the same counts, and the committed ``sig.mech-eval/1`` /
``sig.resolution-eval/1`` records), runs the REAL placement-R harness
(``ops.quality.run_quality_probe`` — the same code the release gate
consumes) over it, then wraps the measured ``sig.quality-report/1`` in the
page artifact with the full registry declaration.

Every check the placement cannot measure on this corpus reports
``not_evaluable`` with the named reason — honest states, never fabricated
outcomes. ``generated_at`` is the fixture corpus's fixed stamp (the same
constant the status-lane fixture carries), so the committed bytes are
byte-stable across regenerations.

Run:  uv run python scripts/eval/run_quality_page.py
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "exports" / "src" / "exports" / "data" / "quality_page.json"
DATA = REPO / "exports" / "src" / "exports" / "data"

#: The fixture corpus's fixed clock (the status-lane fixture's stamp).
FIXED_AT = "2026-10-15T12:00:00Z"
TARGET = "fixture quality-page corpus"

#: A few declared site rows — the fixture corpus's dedup field set (the
#: CONF-07b wire shape: copies nested, possible duplicates listed,
#: multi-view same-layer co-located records).
SITE_ROWS = [
    {
        "entity_id": "cam-okc-001",
        "label": "OKC traffic camera — Broadway & 23rd",
        "jurisdiction": "Oklahoma",
        "tier": 0,
        "lat": 35.493,
        "lon": -97.514,
        "precision": "exact",
        "site_id": "cam-okc-001",
        "copies": [{"record": "cam-okc-001b"}],
        "possible_duplicates": [],
        "multi_view": [],
        "n_independent_lineages": 1,
    },
    {
        "entity_id": "cam-okc-002",
        "label": "OKC ALPR pole — I-235 frontage",
        "jurisdiction": "Oklahoma",
        "tier": 0,
        "lat": 35.512,
        "lon": -97.501,
        "precision": "exact",
        "site_id": "cam-okc-002",
        "copies": [],
        "possible_duplicates": [{"record": "cam-okc-003", "distance_m": 18.0}],
        "multi_view": [{"record": "cam-okc-002b"}],
        "n_independent_lineages": 1,
    },
]


def _dossier_doc(published: int, roots: int) -> dict:
    return {
        "schema": "sig.dossier/2",
        "rollup": {
            "records": published,
            "count_interval": {"records": published, "lower": roots, "upper": published},
            "dossier_inflation_vs_lineage_roots": {
                "published_rows": published,
                "lineage_roots": roots,
                "measured": published / roots if roots else None,
                "ratchet_target": "<= 1.02",
            },
        },
    }


def build_fixture_page() -> dict:
    """Assemble the scan dir, run the real placement-R harness, wrap the
    page artifact — the same calls the committed record came from."""
    from ops.quality import EvalContext, run_quality_probe

    from exports import quality as eq

    registry = eq.load_registry()
    # A FIXED relative scan dir — the recorded violation paths embed the
    # scan-dir prefix verbatim, so a temp dir would make the committed
    # record non-deterministic across machines.
    tmp = Path("scan-quality-page-corpus")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    try:
        (tmp / "sig_graph").mkdir(parents=True)
        (tmp / "sig_graph" / "sites.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in SITE_ROWS), encoding="utf-8"
        )
        dossier_dir = tmp / "web" / "dossiers"
        dossier_dir.mkdir(parents=True)
        (dossier_dir / "oklahoma-city-ok.json").write_text(
            json.dumps(_dossier_doc(published=3, roots=3), indent=2), encoding="utf-8"
        )
        # The committed release artifacts — real bytes the GQ-27 wording scan
        # measures (the same files the page's figures point at).
        for name in ("mech_eval.json", "resolution_eval.json"):
            if (DATA / name).is_file():
                dest = tmp / "web" / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(DATA / name, dest)
        report = run_quality_probe(
            EvalContext(scan_dir=tmp),
            placement="R",
            target=TARGET,
            generated_at=datetime.fromisoformat(FIXED_AT),
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    doc = eq.build_quality_page(registry, report, generated_at=FIXED_AT, target=TARGET)
    errors = eq.quality_page_lint_errors(doc)
    if errors:
        raise SystemExit("sig.quality-page/1 failed its own lint: " + "; ".join(errors))
    return doc


def main() -> int:
    doc = build_fixture_page()
    OUT.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
