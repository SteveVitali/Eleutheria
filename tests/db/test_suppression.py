# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Small-cell disclosure control for the analytics boundary (§18.4).

These are the SIG-STORE-030/031/032/033 guards: the k=5 threshold, the
rationale-driven publish/suppress decision (institutional conduct publishes even
when small; a private-individual small cell is suppressed to null — never zero),
complementary suppression so a lone suppressed cell is not invertible, and the
one-month granularity floor.
"""

from __future__ import annotations

import pytest
from db.suppression import (
    DEFAULT_K_THRESHOLD,
    Cell,
    SuppressionRationale,
    assert_month_granularity,
    effective_k_threshold,
    is_month_period,
    is_small_cell,
    suppress_group,
)

INST = SuppressionRationale.INSTITUTIONAL_CONDUCT
INDIV = SuppressionRationale.PROTECTS_INDIVIDUAL
CONTRACT = SuppressionRationale.CONTRACTUAL
AMBIG = SuppressionRationale.AMBIGUOUS


def _by_label(result: object) -> dict[str, object]:
    return {d.label: d for d in result.decisions}  # type: ignore[attr-defined]


# --- the k=5 threshold (SIG-STORE-030/033) ------------------------------------


def test_default_threshold_is_sigs_own_policy() -> None:
    # SIG-STORE-033: k=5 is SIG's own documented policy, not a claimed standard.
    assert DEFAULT_K_THRESHOLD == 5


@pytest.mark.parametrize("count,small", [(1, True), (4, True), (5, False), (9, False)])
def test_small_cell_is_one_to_k_minus_one(count: int, small: bool) -> None:
    assert is_small_cell(count) is small


def test_zero_is_not_a_small_cell() -> None:
    # A zero is the absence of activity (coverage model), not a small cell.
    assert is_small_cell(0) is False


def test_negative_count_is_a_data_error() -> None:
    with pytest.raises(ValueError):
        is_small_cell(-1)


def test_stricter_partner_threshold_wins() -> None:
    # SIG-STORE-033: where a partner licence imposes a different threshold, the
    # stricter (larger — suppresses more) applies; SIG's own k is the floor.
    assert effective_k_threshold(5, 10) == 10
    assert effective_k_threshold(5, 3) == 5
    assert effective_k_threshold(5, None) == 5


# --- one-month granularity floor (SIG-STORE-030 / §18.4) ----------------------


@pytest.mark.parametrize(
    "period,ok",
    [
        ("2026-07", True),
        ("2026-12", True),
        ("2026-07-15", False),
        ("2026-13", False),
        ("2026", False),
    ],
)
def test_month_granularity(period: str, ok: bool) -> None:
    assert is_month_period(period) is ok
    if ok:
        assert assert_month_granularity(period) == period
    else:
        with pytest.raises(ValueError):
            assert_month_granularity(period)


# --- the rationale-driven decision (SIG-STORE-031/032) ------------------------


def test_institutional_small_count_is_published_not_suppressed() -> None:
    # SIG-STORE-032: "three searches by an agency" is accountability information
    # and MUST publish, even though 3 < k.
    result = suppress_group([Cell("agency", 3, INST)], margin_published=False)
    decision = result.decisions[0]
    assert decision.published_count == 3
    assert decision.suppressed_flag is False
    assert decision.rationale is INST


def test_individual_small_count_is_suppressed_to_null_never_zero() -> None:
    # SIG-STORE-030: suppressed cell is null + flag + k_threshold, NEVER zero.
    result = suppress_group([Cell("person", 2, INDIV)], margin_published=False)
    decision = result.decisions[0]
    assert decision.published_count is None
    assert decision.published_count != 0
    assert decision.suppressed_flag is True
    assert decision.k_threshold == DEFAULT_K_THRESHOLD
    assert decision.rationale is INDIV


def test_individual_large_count_is_published() -> None:
    result = suppress_group([Cell("person", 40, INDIV)], margin_published=False)
    assert result.decisions[0].published_count == 40
    assert result.decisions[0].suppressed_flag is False


def test_contractual_is_suppressed_and_must_cite_a_rights_record() -> None:
    # SIG-STORE-031 table: contractual → suppress, cite the rights record.
    result = suppress_group(
        [Cell("licensed", 99, CONTRACT, rights_record="rights:xyz")], margin_published=False
    )
    decision = result.decisions[0]
    assert decision.suppressed_flag is True
    assert decision.published_count is None
    assert decision.rights_record == "rights:xyz"


def test_contractual_without_a_rights_record_is_an_error() -> None:
    with pytest.raises(ValueError):
        suppress_group([Cell("licensed", 99, CONTRACT)], margin_published=False)


def test_ambiguous_small_cell_is_suppressed_and_raises_a_review_task() -> None:
    # SIG-STORE-032: the default when the two readings cannot be separated is to
    # suppress AND raise a review task, never to publish.
    result = suppress_group([Cell("mixed", 2, AMBIG)], margin_published=False)
    decision = result.decisions[0]
    assert decision.suppressed_flag is True
    assert decision.review_task_required is True
    assert any("mixed" in t for t in result.review_tasks)


def test_ambiguous_large_cell_is_published_without_a_task() -> None:
    result = suppress_group([Cell("mixed", 50, AMBIG)], margin_published=False)
    assert result.decisions[0].suppressed_flag is False
    assert result.review_tasks == ()


# --- complementary (secondary) suppression (SIG-STORE-030) --------------------


def test_a_lone_suppressed_cell_triggers_complementary_suppression() -> None:
    # One primary suppression + a published margin → the cell is recoverable by
    # subtraction, so a second cell MUST be suppressed.
    cells = [
        Cell("small", 2, INDIV),  # primary suppression
        Cell("mid", 8, INDIV),
        Cell("big", 30, INDIV),
    ]
    decisions = _by_label(suppress_group(cells, margin_published=True))
    assert decisions["small"].suppressed_flag is True
    # The smallest publishable cell absorbs the complementary suppression.
    assert decisions["mid"].suppressed_flag is True
    assert decisions["mid"].complementary is True
    # A complementary cell is stamped COMPLEMENTARY, never its own (publish) rationale.
    assert decisions["mid"].rationale is SuppressionRationale.COMPLEMENTARY
    assert decisions["big"].suppressed_flag is False


def test_complementary_prefers_a_non_institutional_cell() -> None:
    # Accountability (institutional) data is preserved when another cell can absorb
    # the secondary suppression.
    cells = [
        Cell("person", 2, INDIV),  # primary suppression
        Cell("agency", 4, INST),  # institutional small — must stay published
        Cell("other", 12, INDIV),
    ]
    decisions = _by_label(suppress_group(cells, margin_published=True))
    assert decisions["person"].suppressed_flag is True
    assert decisions["agency"].suppressed_flag is False  # institutional preserved
    assert decisions["other"].complementary is True


def test_complementary_falls_on_institutional_only_when_forced_and_flags_review() -> None:
    cells = [
        Cell("person", 2, INDIV),  # primary suppression
        Cell("agency", 20, INST),  # the only other cell — forced to absorb it
    ]
    result = suppress_group(cells, margin_published=True)
    decisions = _by_label(result)
    assert decisions["agency"].suppressed_flag is True
    assert decisions["agency"].complementary is True
    # The suppressed institutional cell no longer claims a "publish" rationale.
    assert decisions["agency"].rationale is SuppressionRationale.COMPLEMENTARY
    assert any("accountability tradeoff" in t for t in result.review_tasks)


def test_two_primary_suppressions_need_no_complementary() -> None:
    cells = [Cell("a", 2, INDIV), Cell("b", 3, INDIV), Cell("c", 40, INDIV)]
    decisions = _by_label(suppress_group(cells, margin_published=True))
    assert decisions["a"].suppressed_flag and decisions["b"].suppressed_flag
    assert decisions["c"].suppressed_flag is False
    assert decisions["c"].complementary is False


def test_single_cell_margin_withholds_the_total_when_it_would_be_invertible() -> None:
    # A one-cell group whose only cell is suppressed: the margin total equals that
    # cell, so it must be withheld — no second cell exists to protect it.
    result = suppress_group([Cell("solo", 1, INDIV)], margin_published=True)
    assert result.decisions[0].suppressed_flag is True
    assert result.margin_publishable is False
    assert any("solo" in t for t in result.review_tasks)


def test_a_published_margin_with_no_suppression_is_untouched() -> None:
    cells = [Cell("a", 10, INDIV), Cell("b", 20, INST)]
    result = suppress_group(cells, margin_published=True)
    assert result.margin_publishable is True
    assert all(not d.suppressed_flag for d in result.decisions)
