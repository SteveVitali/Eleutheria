#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Reproducible generator for the P37.44 mechanical evaluation report
(CONF-09 / SIG-EVAL-003 + SIG-EVAL-006 + SIG-CONF-012).

Emits three committed artifacts deterministically:

1. ``exports/src/exports/data/mech_eval_corpus.json`` — the
   ``sig.mech-eval-corpus/1`` record: the M-4 perturbation and M-5
   hard-negative sections measured over the committed real-data regression
   corpus (``tests/rdc/data``) by the P35.23 harness, with the corpus's own
   estimand headers verbatim.
2. ``exports/src/exports/data/mech_eval.json`` — the canonical
   ``sig.mech-eval/1`` record the web data layer reads in fixtures mode:
   the honest no-completed-run posture (the hosted ruleset-v3 ER run is
   queued — every spine measure reports ``unavailable`` with its named
   reason, never fabricated) plus the measured corpus sections.
3. ``docs/build/reports/P37.44_mechanical_eval.md`` — the EVAL-003-shaped
   Markdown rendering (numerator, denominator, method and population per
   estimand; human estimands ``unavailable`` with their reasons).

Run:  uv run python scripts/eval/run_mech_eval.py
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CORPUS_DATA = REPO / "tests" / "rdc" / "data"
OUT_CORPUS = REPO / "exports" / "src" / "exports" / "data" / "mech_eval_corpus.json"
OUT_RECORD = REPO / "exports" / "src" / "exports" / "data" / "mech_eval.json"
OUT_MD = REPO / "docs" / "build" / "reports" / "P37.44_mechanical_eval.md"


def build_corpus_doc() -> dict:
    """The ``sig.mech-eval-corpus/1`` record — M-4/M-5 measured over the
    committed corpus by the P35.23 harness (deterministic seeds)."""
    from ops import rdc, rdc_harness

    corpus = rdc.load_corpus(CORPUS_DATA)
    report = rdc_harness.run_harness(corpus, with_pipeline=False, generated_at="static")
    sections = report["sections"]
    sources = sorted(
        {
            s.source_id
            for s in corpus.slices
            if s.slice_id not in report["slices_deferred_unmaterialized"]
        }
    )
    captured = sorted({s.captured for s in corpus.slices if s.captured})
    return {
        "schema": "sig.mech-eval-corpus/1",
        "corpus_id": corpus.corpus_id,
        "corpus_version": corpus.version,
        "population": (
            f"the committed real-data regression corpus "
            f"(tests/rdc/data, sig.rdc-corpus/1 v{corpus.version}): "
            f"{report['slices_evaluated']} committed licence-safe slices "
            f"evaluated; {len(report['slices_deferred_unmaterialized'])} "
            "restricted-lane slices deferred-unmaterialized"
        ),
        "sources": sources,
        "time_window": {"slice_captured_dates": captured},
        "harness": "ops.rdc_harness (P35.23; deterministic seeds 7/11/13)",
        "verdict": report["verdict"],
        "estimands": {
            "m4_perturbation": corpus.estimands.get("m4", ""),
            "m5_hard_negatives": corpus.estimands.get("m5", ""),
        },
        "sections": {
            "m4_perturbation": sections["m4"],
            "m5_hard_negatives": sections["m5"],
        },
    }


def build_canonical(corpus_doc: dict, *, as_of: str) -> dict:
    """The canonical no-run ``sig.mech-eval/1`` (the fixtures-mode record)."""
    from exports.mech_eval import build_mech_eval
    from resolution.camera_sites import CameraSiteRules

    rules = CameraSiteRules.from_data()
    return build_mech_eval(
        runs=[],
        dedup_view=None,
        member_records={},
        corpus_doc=corpus_doc,
        source_names={},
        ruleset_version=str(rules.version),
        copy_tolerance_m=float(rules.copy_tolerance_m),
        as_of=as_of,
    )


def render_md(doc: dict) -> str:
    """The EVAL-003-shaped rendering — every estimand with numerator,
    denominator, method and population."""
    lines: list[str] = []
    lines.append("# P37.44 — Mechanical evaluation report (sig.mech-eval/1)")
    lines.append("")
    lines.append(f"> {doc['disclosure']}")
    lines.append("")
    scope = doc["scope"]
    lines.append("## Scope (SIG-EVAL-006 — the figures generalise no further)")
    lines.append("")
    lines.append(
        f"- tiers: auto-collapse derivation {scope['tiers']['auto_collapse_derivation']}; "
        f"review-only inferential {scope['tiers']['review_only_inferential']}"
    )
    lines.append(f"- ruleset: camera_site_rules v{scope['ruleset']['camera_site_rules_version']}")
    lines.append(f"- spine population: {scope['populations']['spine']}")
    lines.append(f"- corpus population: {scope['populations']['corpus']}")
    lines.append(
        f"- source mix: {[s['id'] for s in scope['source_mix']['spine_member_sources']]} "
        f"+ corpus {scope['source_mix']['corpus_sources']}"
    )
    lines.append(
        f"- time window: as_of {scope['time_window']['as_of']}; "
        f"run_completed_at {scope['time_window']['run_completed_at']}; "
        f"corpus captured {scope['time_window'].get('corpus')}"
    )
    lines.append("")
    lines.append("## Human estimands (SIG-EVAL-003 — unavailable, never substituted)")
    lines.append("")
    for name, e in sorted(doc["human_estimands"].items()):
        lines.append(f"### {name} — {e['state']}")
        lines.append("")
        lines.append(f"- population: {e['population']}")
        lines.append(f"- unavailable reason: `{e['unavailable_reason']}`")
        lines.append("")
    lines.append("## Mechanical estimands (basis B1/B2 — never real-world precision/recall)")
    lines.append("")
    for name, e in doc["estimands"].items():
        lines.append(f"### {name} — {e['state']} (basis {e['basis']})")
        lines.append("")
        lines.append(f"- estimand: {e['label']}")
        lines.append(f"- numerator / denominator: {e['numerator']} / {e['denominator']}")
        lines.append(f"- value: {e['value']}")
        lines.append(f"- method: {e['method']}")
        lines.append(f"- population: {e['population']}")
        if e.get("unavailable_reason"):
            lines.append(f"- unavailable reason: `{e['unavailable_reason']}`")
        for row in e.get("rows", []):
            lines.append(f"- `{row}`")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    from exports.mech_eval import corpus_lint_errors, mech_eval_lint_errors

    as_of = datetime.now(UTC).date().isoformat()
    corpus_doc = build_corpus_doc()
    errors = corpus_lint_errors(corpus_doc)
    if errors:
        print("corpus record lint FAILED:", *errors, sep="\n  ", file=sys.stderr)
        return 1
    canonical = build_canonical(corpus_doc, as_of=as_of)
    errors = mech_eval_lint_errors(canonical)
    if errors:
        print("mech-eval lint FAILED:", *errors, sep="\n  ", file=sys.stderr)
        return 1
    OUT_CORPUS.write_text(json.dumps(corpus_doc, indent=2, sort_keys=True, default=str) + "\n")
    OUT_RECORD.write_text(json.dumps(canonical, indent=2, sort_keys=True, default=str) + "\n")
    OUT_MD.write_text(render_md(canonical))
    print(f"wrote {OUT_CORPUS.relative_to(REPO)}")
    print(f"wrote {OUT_RECORD.relative_to(REPO)}")
    print(f"wrote {OUT_MD.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
