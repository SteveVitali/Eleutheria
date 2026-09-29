#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Reproducible generator for the P28.1 resolution eval report (ADR-099, design §2).

Runs the eval loop over a committed bootstrap gold set: a maintainer/agent stratified
seed (oversampling the ambiguous weight bands) adjudicated by a human role AND the
LLM (rules-encoded) adjudicator, calibrated by Cohen's κ, then measured by the quality
gates on the frozen holdout. Writes the Markdown report to
``docs/build/reports/P28.1_resolution_eval.md``.

Deterministic — re-run to regenerate the exact report. The SCALE numbers (dedup ratio /
resolved-site count over the ~75k hosted observations) require the ``resolution_materialize``
sqitch change deployed to the hosted spine + an operator-held read/materialize role; that
live-over-hosted pass is the OPEN deferral D-R6.1-EVAL (see the report + DEFERRALS.md).

Run:  uv run python scripts/eval/run_resolution_eval.py
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from resolution.adjudicator import (
    CandidatePair,
    PairRecord,
    RuleBasedLLMAdjudicator,
    adjudicate_pairs,
    weights_of,
)
from resolution.eval_loop import render_report_md, run_eval
from resolution.gold_set import Adjudication, GoldLabel, build_gold_set

DATED = date(2026, 9, 23)
SEED_ADJ = "seed:maintainer@sig"
LLM = RuleBasedLLMAdjudicator()

# --- the committed bootstrap fixture -----------------------------------------
# A stratified seed of realistic org-dedup candidate pairs, oversampling the
# ambiguous boundary band. Each entry: (pair_id, left, right, weight, tier,
# seed_label). The LLM label is computed by the rules-encoded adjudicator.
# left/right = (entity_id, normalized_name, state, org_class, identifiers).
LE = "us.le.municipal_police"
SO = "us.le.sheriff"


def _rec(eid, name, state, cls, ids=()):
    return PairRecord(eid, name, state, cls, frozenset(ids))


# fmt: off
_FIXTURE = [
    # --- tier 0 (shared canonical identifier): unambiguous matches ---
    ("t0-okc", _rec("e1", "oklahoma city police department", "OK", LE, ["ori:OK05501"]),
     _rec("e2", "okc pd", "OK", LE, ["ori:OK05501"]), 11.0, 0, GoldLabel.MATCH),
    ("t0-tulsa", _rec("e3", "tulsa police department", "OK", LE, ["ori:OK07201"]),
     _rec("e4", "tulsa pd", "OK", LE, ["ori:OK07201"]), 10.5, 0, GoldLabel.MATCH),
    ("t0-dallas", _rec("e5", "dallas police department", "TX", LE, ["ori:TX05719"]),
     _rec("e6", "dallas pd", "TX", LE, ["ori:TX05719"]), 10.8, 0, GoldLabel.MATCH),
    ("t0-sheriff", _rec("e7", "oklahoma county sheriff", "OK", SO, ["ori:OK05500"]),
     _rec("e8", "oklahoma co so", "OK", SO, ["ori:OK05500"]), 9.9, 0, GoldLabel.MATCH),
    ("t0-geoid", _rec("e9", "city of norman", "OK", "us.municipality", ["geoid:4052500"]),
     _rec("e10", "norman city", "OK", "us.municipality", ["geoid:4052500"]), 9.6, 0, GoldLabel.MATCH),
    ("t0-vendorlei", _rec("e11", "flock safety", "GA", "vendor", ["lei:FLOCK00001"]),
     _rec("e12", "flock group inc", "GA", "vendor", ["lei:FLOCK00001"]), 9.2, 0, GoldLabel.MATCH),
    # --- tier 2 (name+state+class, no shared id but corroborated by seed) ---
    ("t2-edmond", _rec("e13", "edmond police department", "OK", LE),
     _rec("e14", "edmond police dept", "OK", LE), 6.2, 2, GoldLabel.MATCH),
    ("t2-moore", _rec("e15", "moore police department", "OK", LE),
     _rec("e16", "moore pd", "OK", LE), 5.8, 2, GoldLabel.MATCH),
    # --- different state (non-matches even on name near-duplicate) ---
    ("neg-springfield", _rec("e17", "springfield police department", "IL", LE),
     _rec("e18", "springfield police department", "MO", LE), 6.5, 4, GoldLabel.NON_MATCH),
    ("neg-columbus", _rec("e19", "columbus police department", "OH", LE),
     _rec("e20", "columbus police department", "GA", LE), 6.4, 4, GoldLabel.NON_MATCH),
    ("neg-franklin", _rec("e21", "franklin county sheriff", "OH", SO),
     _rec("e22", "franklin county sheriff", "KY", SO), 6.0, 4, GoldLabel.NON_MATCH),
    ("neg-muni-vs-pd", _rec("e23", "city of aurora", "CO", "us.municipality"),
     _rec("e24", "aurora police department", "CO", LE), 3.9, 5, GoldLabel.NON_MATCH),
    # --- boundary band (ambiguous: name dup, same state, no shared id) ---
    # The LLM (rules) returns NEI here; the maintainer sometimes matches on
    # off-catalog knowledge (a genuine disagreement -> disputed), sometimes agrees.
    ("bnd-metro", _rec("e25", "metro police", "TX", LE),
     _rec("e26", "metro police", "TX", LE), 3.6, 4, GoldLabel.MATCH),        # maintainer: match
    ("bnd-univ", _rec("e27", "university police", "CA", "us.le.campus_police"),
     _rec("e28", "university police", "CA", "us.le.campus_police"), 3.2, 4, GoldLabel.NOT_ENOUGH_INFORMATION),
    ("bnd-transit", _rec("e29", "transit police", "NY", "us.le.transit_police"),
     _rec("e30", "transit police", "NY", "us.le.transit_police"), 2.9, 5, GoldLabel.NOT_ENOUGH_INFORMATION),
    ("bnd-park", _rec("e31", "park police", "DC", LE),
     _rec("e32", "park police", "DC", LE), 1.5, 5, GoldLabel.MATCH),          # maintainer: match
    ("bnd-harbor", _rec("e33", "harbor police", "CA", LE),
     _rec("e34", "harbor police", "CA", LE), 0.8, 5, GoldLabel.NOT_ENOUGH_INFORMATION),
    ("bnd-airport", _rec("e35", "airport police", "IL", LE),
     _rec("e36", "airport police", "IL", LE), 0.3, 5, GoldLabel.NOT_ENOUGH_INFORMATION),
    # --- low / very-low band (weak signal, non-matches) ---
    ("low-acme", _rec("e37", "acme cameras", "CA", "vendor"),
     _rec("e38", "beta surveillance", "CA", "vendor"), -1.2, 5, GoldLabel.NON_MATCH),
    ("low-genesys", _rec("e39", "genesys security", "TX", "vendor"),
     _rec("e40", "genworth systems", "TX", "vendor"), -2.1, 5, GoldLabel.NON_MATCH),
    ("vlow-x", _rec("e41", "riverside water district", "CA", "us.special_district"),
     _rec("e42", "riverside police department", "CA", LE), -4.0, 6, GoldLabel.NON_MATCH),
]
# fmt: on


def build() -> tuple:
    pairs = [CandidatePair(pid, left, right, w) for pid, left, right, w, _t, _lab in _FIXTURE]
    tier_by_pair_id = {pid: t for pid, _l, _r, _w, t, _lab in _FIXTURE}
    seed_labels = {pid: lab for pid, _l, _r, _w, _t, lab in _FIXTURE}

    llm_adjs = adjudicate_pairs(pairs, LLM, dated=DATED)
    llm_label_by_pair_id = {a.pair_id: a.label for a in llm_adjs}
    seed_adjs = [
        Adjudication(pid, SEED_ADJ, seed_labels[pid], DATED, "1", "maintainer seed judgment")
        for pid in seed_labels
    ]

    gold_set = build_gold_set(
        weights=weights_of(pairs),
        adjudications=[*llm_adjs, *seed_adjs],
        holdout_fraction=0.3,
        seed=7,
    )

    # Clusters (auto-write tier 0/2 edges only) for B-cubed on the shared elements.
    predicted_clusters: dict[str, str] = {}
    gold_clusters: dict[str, str] = {}
    next_g = 0
    for _pid, left, right, _w, tier, lab in _FIXTURE:
        # predicted: auto-write tiers merge; else singletons
        if tier in (0, 1, 2, 3):
            predicted_clusters.setdefault(left.entity_id, left.entity_id)
            predicted_clusters[right.entity_id] = predicted_clusters[left.entity_id]
        else:
            predicted_clusters.setdefault(left.entity_id, left.entity_id)
            predicted_clusters.setdefault(right.entity_id, right.entity_id)
        # gold: match -> same cluster, else distinct
        if lab == GoldLabel.MATCH:
            gold_clusters.setdefault(left.entity_id, f"g{next_g}")
            gold_clusters[right.entity_id] = gold_clusters[left.entity_id]
        else:
            gold_clusters.setdefault(left.entity_id, f"g{next_g}")
            next_g += 1
            gold_clusters[right.entity_id] = f"g{next_g}"
            next_g += 1
        next_g += 1

    return pairs, tier_by_pair_id, llm_label_by_pair_id, gold_set, predicted_clusters, gold_clusters


def main() -> int:
    pairs, tier_by_pair_id, llm_label_by_pair_id, gold_set, pred_c, gold_c = build()
    report = run_eval(
        gold_set=gold_set,
        pairs=pairs,
        tier_by_pair_id=tier_by_pair_id,
        llm_label_by_pair_id=llm_label_by_pair_id,
        seed_adjudicator=SEED_ADJ,
        llm_adjudicator=LLM.adjudicator_id,
        predicted_clusters=pred_c,
        gold_clusters=gold_c,
        # Scale numbers over the hosted spine are DEFERRED (D-R6.1-EVAL): the
        # migration must land on hosted + an operator role must run the materializer.
        observation_count=None,
        resolved_site_count=None,
        dedup_ratio=None,
        resolutions_materialized=None,
        notes=[
            "Methodology numbers below are reproducible from this committed bootstrap gold set "
            "(scripts/eval/run_resolution_eval.py). The write path is proven over real PG18+PostGIS "
            "in tests/db/test_resolution_materialize.py (append-only, idempotent +0).",
            "SCALE over the ~75k hosted observations (dedup ratio / resolved-site count) is DEFERRED "
            "to D-R6.1-EVAL: it needs the resolution_materialize sqitch change deployed to the hosted "
            "spine + an operator-held read/materialize role. Re-run: `sig-reconcile materialize --dsn "
            "$SIG_PG_DSN` after the migration is deployed. OSM land (D-SOURCES.17-1) still in flight.",
        ],
    )
    md = render_report_md(report, title="P28.1 — Resolution eval report (Round 6 keystone)")
    out = Path("docs/build/reports/P28.1_resolution_eval.md")
    out.write_text(md + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(
        f"κ={report.kappa:.3f} (bar {report.kappa_bar}) trusted={report.llm_trusted} "
        f"floor={report.auto_write_threshold} demoted={report.demoted_tiers} "
        f"disputed={len(report.disputed_pair_ids)} review_routed={report.review_routed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
