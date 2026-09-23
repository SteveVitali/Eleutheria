# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The resolution eval loop (P28.1, ADR-099, design §2.4/§2.5)."""

from __future__ import annotations

from datetime import date

from resolution.adjudicator import CandidatePair, PairRecord
from resolution.eval_loop import (
    active_learning_pair_ids,
    read_auto_write_threshold,
    read_kappa_bar,
    render_report_md,
    run_eval,
    tier_precisions_on_holdout,
)
from resolution.gold_set import Adjudication, GoldLabel, build_gold_set


def _rec(eid: str, ids: frozenset[str] = frozenset()) -> PairRecord:
    return PairRecord(entity_id=eid, normalized_name=eid, state="OK", identifiers=ids)


def _pair(pid: str, a: str, b: str, weight: float) -> CandidatePair:
    return CandidatePair(pid, _rec(a), _rec(b), weight)


def test_thresholds_read_from_versioned_data() -> None:
    # P28.1/ADR-099 raised the floor to 0.98 and published a κ bar of 0.7.
    assert read_auto_write_threshold() == 0.98
    assert read_kappa_bar() == 0.7


def _gold(pairs: list[CandidatePair], labels: dict[str, GoldLabel], frozen: set[str]):
    dated = date(2026, 9, 1)
    adjs: list[Adjudication] = []
    for pid, label in labels.items():
        adjs.append(Adjudication(pid, "seed:maintainer@sig", label, dated, "1", "seed"))
        adjs.append(Adjudication(pid, "llm:rulebased@v1", label, dated, "1", "llm"))
    weights = {p.pair_id: p.weight for p in pairs}
    gs = build_gold_set(weights=weights, adjudications=adjs, holdout_fraction=0.0)
    # Force the holdout membership deterministically for the test.
    from dataclasses import replace

    gs = replace(gs, pairs=tuple(replace(p, frozen=p.pair_id in frozen) for p in gs.pairs))
    return gs


def test_demotion_fires_when_holdout_precision_below_floor() -> None:
    pairs = [_pair(f"p{i}", f"a{i}", f"b{i}", 9.0) for i in range(4)]
    # Three holdout pairs at tier 0; one is a false merge -> precision 2/3 < 0.98.
    labels = {
        "p0": GoldLabel.MATCH,
        "p1": GoldLabel.MATCH,
        "p2": GoldLabel.NON_MATCH,  # the model auto-wrote a non-match at tier 0
        "p3": GoldLabel.MATCH,
    }
    gs = _gold(pairs, labels, frozen={"p0", "p1", "p2"})
    tier_by_pair = {"p0": 0, "p1": 0, "p2": 0, "p3": 0}
    prec = tier_precisions_on_holdout(gs, {p.pair_id: p for p in pairs}, tier_by_pair)
    assert prec[0] < 0.98
    report = run_eval(
        gold_set=gs,
        pairs=pairs,
        tier_by_pair_id=tier_by_pair,
        llm_label_by_pair_id={p.pair_id: labels[p.pair_id] for p in pairs},
        seed_adjudicator="seed:maintainer@sig",
        llm_adjudicator="llm:rulebased@v1",
    )
    assert 0 in report.demoted_tiers
    assert report.any_demoted


def test_clean_holdout_keeps_auto_writing() -> None:
    pairs = [_pair(f"p{i}", f"a{i}", f"b{i}", 9.0) for i in range(3)]
    labels = {"p0": GoldLabel.MATCH, "p1": GoldLabel.MATCH, "p2": GoldLabel.MATCH}
    gs = _gold(pairs, labels, frozen={"p0", "p1", "p2"})
    tier_by_pair = {p.pair_id: 0 for p in pairs}
    report = run_eval(
        gold_set=gs,
        pairs=pairs,
        tier_by_pair_id=tier_by_pair,
        llm_label_by_pair_id=labels,
        seed_adjudicator="seed:maintainer@sig",
        llm_adjudicator="llm:rulebased@v1",
    )
    assert not report.any_demoted
    assert report.tier_precisions[0] == 1.0


def test_active_learning_selects_disagreement_and_boundary() -> None:
    pairs = [
        _pair("disagree", "a", "b", 9.0),  # model auto-writes, LLM says non_match
        _pair("boundary", "c", "d", 3.5),  # weight at the review cutoff
        _pair("clear", "e", "f", 12.0),
    ]
    tier_by_pair = {"disagree": 0, "boundary": 4, "clear": 0}
    llm_labels = {
        "disagree": GoldLabel.NON_MATCH,
        "boundary": GoldLabel.MATCH,
        "clear": GoldLabel.MATCH,
    }
    selected = active_learning_pair_ids(
        pairs, tier_by_pair, llm_labels, boundary_low=-3.0, boundary_high=3.5
    )
    assert "disagree" in selected
    assert "boundary" in selected
    assert "clear" not in selected


def test_low_kappa_makes_llm_a_suggester_and_routes_to_review() -> None:
    pairs = [_pair(f"p{i}", f"a{i}", f"b{i}", 9.0) for i in range(4)]
    dated = date(2026, 9, 1)
    # Seed and LLM disagree on most pairs -> low κ.
    adjs: list[Adjudication] = []
    seed_labels = [GoldLabel.MATCH, GoldLabel.NON_MATCH, GoldLabel.MATCH, GoldLabel.NON_MATCH]
    llm_labels_list = [GoldLabel.NON_MATCH, GoldLabel.MATCH, GoldLabel.NON_MATCH, GoldLabel.MATCH]
    for p, sl, ll in zip(pairs, seed_labels, llm_labels_list, strict=True):
        adjs.append(Adjudication(p.pair_id, "seed:maintainer@sig", sl, dated, "1", "s"))
        adjs.append(Adjudication(p.pair_id, "llm:rulebased@v1", ll, dated, "1", "l"))
    gs = build_gold_set(
        weights={p.pair_id: p.weight for p in pairs}, adjudications=adjs, holdout_fraction=0.0
    )
    report = run_eval(
        gold_set=gs,
        pairs=pairs,
        tier_by_pair_id={p.pair_id: 0 for p in pairs},
        llm_label_by_pair_id={p.pair_id: ll for p, ll in zip(pairs, llm_labels_list, strict=True)},
        seed_adjudicator="seed:maintainer@sig",
        llm_adjudicator="llm:rulebased@v1",
    )
    assert report.kappa < 0.7
    assert not report.llm_trusted
    assert report.review_routed >= len(pairs)  # all LLM pairs routed to review
    assert any("SUGGESTER" in n for n in report.notes)


def test_report_renders_markdown_with_provisional_disclosure() -> None:
    pairs = [_pair("p0", "a", "b", 9.0)]
    gs = _gold(pairs, {"p0": GoldLabel.MATCH}, frozen={"p0"})
    report = run_eval(
        gold_set=gs,
        pairs=pairs,
        tier_by_pair_id={"p0": 0},
        llm_label_by_pair_id={"p0": GoldLabel.MATCH},
        seed_adjudicator="seed:maintainer@sig",
        llm_adjudicator="llm:rulebased@v1",
        dedup_ratio=0.5,
        resolved_site_count=10,
        observation_count=20,
        resolutions_materialized=10,
    )
    md = render_report_md(report)
    assert "PROVISIONAL" in md
    assert "Cohen's κ" in md
    assert "auto-write precision floor" in md
    assert "dedup ratio" in md
