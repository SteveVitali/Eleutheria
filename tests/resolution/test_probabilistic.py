# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The probabilistic tiers 4–6 (SIG-IDENT-020/021/024/025): a Splink 4 / DuckDB
matcher whose scored pairs become PROPOSED review proposals (never auto-writes),
each carrying its match weight and per-comparison Bayes-factor decomposition; tier 6
persists no per-pair record; trigram similarity is never a decision score."""

from __future__ import annotations

import copy

import pytest
from resolution.blocking import BlockingContext, BlockingRuleRejected
from resolution.probabilistic import (
    PROPOSED,
    SPLINK_MODEL_VERSION,
    ProbabilisticMatch,
    ProbabilisticMatcher,
    assert_no_trigram_decision,
)

_RECORDS = [
    {
        "unique_id": "a1",
        "normalized_name": "travis county sheriff office",
        "name_first_token": "travis",
        "state": "TX",
        "organization_class": "us.le.sheriff",
    },
    {
        "unique_id": "a2",
        "normalized_name": "travis county so",
        "name_first_token": "travis",
        "state": "TX",
        "organization_class": "us.le.sheriff",
    },
    {
        "unique_id": "b1",
        "normalized_name": "los angeles police department",
        "name_first_token": "los",
        "state": "CA",
        "organization_class": "us.le.municipal_police",
    },
    {
        "unique_id": "b2",
        "normalized_name": "los angeles police dept",
        "name_first_token": "los",
        "state": "CA",
        "organization_class": "us.le.municipal_police",
    },
    {
        "unique_id": "c1",
        "normalized_name": "harris county sheriff office",
        "name_first_token": "harris",
        "state": "TX",
        "organization_class": "us.le.sheriff",
    },
]


def _matches() -> list[ProbabilisticMatch]:
    return ProbabilisticMatcher.from_data().match(_RECORDS)


# --- SIG-IDENT-020 / AC1: tiers 4 and 5 produce PROPOSED claims only ----------


def test_matcher_returns_some_proposals() -> None:
    matches = _matches()
    assert matches, "the near-duplicate pairs should be scored"
    assert all(m.match_tier in (4, 5) for m in matches)


def test_every_probabilistic_match_is_proposed_never_auto_write() -> None:
    for m in _matches():
        assert m.disposition == "review"
        assert m.disposition != "auto_write"
        assert m.proposed is True
        assert m.match_evidence["claim_status"] == PROPOSED


def test_tier6_below_threshold_persists_no_record() -> None:
    # Raise tier5_weak above every achievable weight → every pair is tier 6 and
    # nothing is returned (SIG-IDENT-020: tier 6 has no per-pair record).
    model = copy.deepcopy(ProbabilisticMatcher.from_data().model)
    model["thresholds"]["tier5_weak"] = 100.0
    model["thresholds"]["tier4_review"] = 200.0
    matcher = ProbabilisticMatcher(model=model, blocking_context=BlockingContext.from_data())
    assert matcher.match(_RECORDS) == []


def test_tier_boundaries_are_data_driven() -> None:
    # Lowering tier4_review promotes the weak pair from tier 5 to tier 4 without any
    # code change — the tier boundary is data (thresholds in splink_model.toml).
    model = copy.deepcopy(ProbabilisticMatcher.from_data().model)
    model["thresholds"]["tier4_review"] = -10.0
    matcher = ProbabilisticMatcher(model=model, blocking_context=BlockingContext.from_data())
    assert {m.match_tier for m in matcher.match(_RECORDS)} == {4}


# --- SIG-IDENT-025 / AC2: weight + per-comparison decomposition on every match


def test_every_match_records_tier_evidence_weight_and_decomposition() -> None:
    for m in _matches():
        assert m.match_tier in (4, 5)
        assert m.tier_label in ("4", "5")
        assert m.match_evidence["rule"] == "splink_probabilistic"
        assert m.match_evidence["model_version"] == SPLINK_MODEL_VERSION
        assert isinstance(m.match_weight, float)
        assert 0.0 <= m.match_probability <= 1.0
        # per-comparison decomposition: one contribution per compared column, each
        # with its Bayes factor and the level that fired.
        columns = {c.column for c in m.decomposition}
        assert columns == {"normalized_name", "state", "organization_class"}
        for c in m.decomposition:
            assert c.bayes_factor > 0.0
            assert c.label


def test_decomposition_is_mirrored_in_evidence_json() -> None:
    m = next(m for m in _matches() if m.match_tier == 4)
    evidence_cols = {d["column"] for d in m.match_evidence["decomposition"]}
    assert evidence_cols == {"normalized_name", "state", "organization_class"}
    for d in m.match_evidence["decomposition"]:
        assert set(d) == {"column", "gamma", "bayes_factor", "label"}


def test_strong_name_match_reaches_tier4_with_explainable_weight() -> None:
    # The two "Los Angeles Police Department/Dept" spellings: same state + class, a
    # Jaro-Winkler name match → a confident probabilistic match (tier 4).
    m = next(m for m in _matches() if {m.left, m.right} == {"b1", "b2"})
    assert m.match_tier == 4
    name = next(c for c in m.decomposition if c.column == "normalized_name")
    assert "jaro-winkler" in name.label
    assert name.bayes_factor > 1.0  # the name pushed the weight UP


# --- SIG-IDENT-021: the matcher is Splink 4 on DuckDB -------------------------


def test_evidence_names_the_splink_duckdb_matcher() -> None:
    assert all(m.match_evidence["matcher"] == "splink4-duckdb" for m in _matches())


def test_matching_is_deterministic() -> None:
    first = _matches()
    second = _matches()
    assert [(m.left, m.right, round(m.match_weight, 6)) for m in first] == [
        (m.left, m.right, round(m.match_weight, 6)) for m in second
    ]


# --- SIG-IDENT-024: trigram similarity is never a decision score --------------


def test_shipped_model_uses_no_trigram_decision_score() -> None:
    assert_no_trigram_decision()  # does not raise on the committed model


@pytest.mark.parametrize(
    "bad_condition",
    [
        'jaccard_similarity("normalized_name_l", "normalized_name_r") > 0.8',
        'trigram_similarity("normalized_name_l", "normalized_name_r") > 0.7',
        '"normalized_name_l" % "normalized_name_r"',
    ],
)
def test_trigram_decision_score_is_rejected(bad_condition: str) -> None:
    model = copy.deepcopy(ProbabilisticMatcher.from_data().model)
    model["comparison"][0]["level"].insert(
        1, {"sql_condition": bad_condition, "label": "bad trigram", "m": 0.5, "u": 0.01}
    )
    with pytest.raises(ValueError, match="SIG-IDENT-024"):
        assert_no_trigram_decision(model)
    with pytest.raises(ValueError, match="SIG-IDENT-024"):
        ProbabilisticMatcher(model=model, blocking_context=BlockingContext.from_data())


def test_jaro_winkler_is_allowed_as_a_decision_score() -> None:
    # Edit-distance similarity IS permitted as a decision score; only trigram/q-gram
    # set-similarity is banned. The shipped model relies on Jaro-Winkler.
    conditions = [
        level["sql_condition"]
        for comparison in ProbabilisticMatcher.from_data().model["comparison"]
        for level in comparison["level"]
    ]
    assert any("jaro_winkler_similarity" in c for c in conditions)


# --- SIG-IDENT-023: the matcher sizes blocking before running -----------------


def test_matcher_sizes_blocking_and_reports_counts() -> None:
    sizes = ProbabilisticMatcher.from_data().size_blocking(_RECORDS)
    assert sizes  # one entry per model blocking rule
    assert all(count >= 0 for count in sizes.values())


def test_oversized_blocking_aborts_the_match() -> None:
    matcher = ProbabilisticMatcher(
        model=ProbabilisticMatcher.from_data().model,
        blocking_context=BlockingContext(comparison_ceiling=0, prohibited_sole_keys=frozenset()),
    )
    with pytest.raises(BlockingRuleRejected):
        matcher.match(_RECORDS)
