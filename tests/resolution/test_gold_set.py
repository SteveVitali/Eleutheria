# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The gold-standard label set (SIG-IDENT-027): stratified sampling across weight
bands, a three-value label vocabulary, double adjudication reporting Cohen's kappa,
per-label provenance, and a frozen, immutable holdout."""

from __future__ import annotations

from datetime import date

import pytest
from resolution.gold_set import (
    GOLD_SET_RULES_VERSION,
    Adjudication,
    GoldLabel,
    adjudicated_label,
    adjudication_rules,
    assign_band,
    bands_from_data,
    build_gold_set,
    cohens_kappa,
    stratified_sample,
)

# --- Three-value vocabulary + written rules -----------------------------------


def test_label_vocabulary_is_exactly_three_values() -> None:
    assert {label.value for label in GoldLabel} == {
        "match",
        "non_match",
        "not_enough_information",
    }


def test_written_adjudication_rules_are_present_and_name_every_label() -> None:
    rules = adjudication_rules()
    assert rules
    for label in GoldLabel:
        assert label.value in rules


# --- Stratified sampling across weight bands ----------------------------------


def test_bands_are_ordered_most_confident_first() -> None:
    bands = bands_from_data()
    assert bands
    weights = [b.min_weight for b in bands]
    assert weights == sorted(weights, reverse=True)


def test_assign_band_picks_the_highest_band_met() -> None:
    bands = bands_from_data()
    assert assign_band(100.0, bands) == "very_high"
    assert assign_band(-100.0, bands) == "very_low"


def test_stratified_sample_covers_every_band_and_caps_per_band() -> None:
    # 5 pairs in the very-high band, 1 in the boundary band; per_band=2 caps the
    # crowded band and keeps the sparse one — the point of stratifying.
    scored = {f"vh{i}": 9.0 for i in range(5)}
    scored["b0"] = 0.5
    sample = stratified_sample(scored, per_band=2, seed=1)
    assert len(sample["very_high"]) == 2
    assert sample["boundary"] == ["b0"]


def test_stratified_sample_is_deterministic_under_seed() -> None:
    scored = {f"p{i}": 9.0 for i in range(10)}
    assert stratified_sample(scored, per_band=3, seed=7) == stratified_sample(
        scored, per_band=3, seed=7
    )


# --- Cohen's kappa ------------------------------------------------------------


def test_perfect_agreement_kappa_is_one() -> None:
    a = [GoldLabel.MATCH, GoldLabel.NON_MATCH, GoldLabel.MATCH]
    assert cohens_kappa(a, list(a)) == 1.0


def test_all_identical_single_label_is_perfect_agreement() -> None:
    a = [GoldLabel.MATCH, GoldLabel.MATCH]
    assert cohens_kappa(a, list(a)) == 1.0


def test_kappa_is_below_one_on_disagreement() -> None:
    a = [GoldLabel.MATCH, GoldLabel.MATCH, GoldLabel.NON_MATCH, GoldLabel.NON_MATCH]
    b = [GoldLabel.MATCH, GoldLabel.NON_MATCH, GoldLabel.NON_MATCH, GoldLabel.MATCH]
    kappa = cohens_kappa(a, b)
    assert kappa < 1.0


def test_kappa_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError, match="same pairs"):
        cohens_kappa([GoldLabel.MATCH], [GoldLabel.MATCH, GoldLabel.MATCH])


# --- Double adjudication ------------------------------------------------------


def _adj(pair_id: str, who: str, label: GoldLabel) -> Adjudication:
    return Adjudication(
        pair_id=pair_id,
        adjudicator=who,
        label=label,
        dated=date(2026, 1, 1),
        ruleset_version=GOLD_SET_RULES_VERSION,
    )


def test_consensus_label_requires_two_distinct_adjudicators() -> None:
    with pytest.raises(ValueError, match="two distinct adjudicators"):
        adjudicated_label([_adj("p1", "alice", GoldLabel.MATCH)])


def test_agreeing_adjudicators_yield_the_shared_label() -> None:
    label = adjudicated_label(
        [_adj("p1", "alice", GoldLabel.MATCH), _adj("p1", "bob", GoldLabel.MATCH)]
    )
    assert label is GoldLabel.MATCH


def test_disagreeing_adjudicators_yield_no_label() -> None:
    label = adjudicated_label(
        [_adj("p1", "alice", GoldLabel.MATCH), _adj("p1", "bob", GoldLabel.NON_MATCH)]
    )
    assert label is None


# --- Assembling a versioned gold set with a frozen holdout --------------------


def _gold_set():
    weights = {f"p{i}": float(i) for i in range(10)}
    adjudications = []
    for i in range(10):
        label = GoldLabel.MATCH if i >= 5 else GoldLabel.NON_MATCH
        adjudications.append(_adj(f"p{i}", "alice", label))
        adjudications.append(_adj(f"p{i}", "bob", label))
    return build_gold_set(
        weights=weights, adjudications=adjudications, holdout_fraction=0.3, seed=3
    )


def test_gold_set_is_versioned_and_carries_provenance() -> None:
    gs = _gold_set()
    assert gs.version and gs.rules_version == GOLD_SET_RULES_VERSION
    for pair in gs.pairs:
        assert len(pair.provenance) == 2  # double adjudication
        for adj in pair.provenance:
            assert adj.adjudicator and adj.ruleset_version and adj.dated


def test_holdout_is_a_frozen_fraction() -> None:
    gs = _gold_set()
    assert len(gs.holdout()) == 3  # round(10 * 0.3)
    assert all(p.frozen for p in gs.holdout())
    assert all(not p.frozen for p in gs.training())
    assert len(gs.holdout()) + len(gs.training()) == len(gs.pairs)


def test_frozen_holdout_pair_cannot_be_relabelled() -> None:
    gs = _gold_set()
    frozen_id = gs.holdout()[0].pair_id
    with pytest.raises(ValueError, match="frozen holdout"):
        gs.relabel(frozen_id, GoldLabel.NOT_ENOUGH_INFORMATION)


def test_training_pair_can_be_relabelled() -> None:
    gs = _gold_set()
    train_id = gs.training()[0].pair_id
    updated = gs.relabel(train_id, GoldLabel.NOT_ENOUGH_INFORMATION)
    assert updated.by_id(train_id).label is GoldLabel.NOT_ENOUGH_INFORMATION
    # original is unchanged (immutable value objects)
    assert gs.by_id(train_id).label is not GoldLabel.NOT_ENOUGH_INFORMATION


def test_holdout_split_is_deterministic_under_seed() -> None:
    a = {p.pair_id for p in _gold_set().holdout()}
    b = {p.pair_id for p in _gold_set().holdout()}
    assert a == b


def test_gold_set_kappa_between_named_adjudicators() -> None:
    gs = _gold_set()
    assert gs.kappa("alice", "bob") == 1.0  # they agreed on everything
    assert gs.pairs[0].band  # every pair carries its weight band
