# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Temporal kinds, ongoing-rendering, and the as-of contract (§9.3/§9.4).

AC2: `valid_to_kind` distinguishes `ongoing` from `unknown`, and a surface renders
it with the observation date attached (SIG-TIME-004/005).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from db.temporal import (
    AsOf,
    AsOfQuestion,
    ValidBoundKind,
    assert_conformant_rendering,
    render_valid_bound,
)


def test_ongoing_is_rendered_with_the_observation_date() -> None:
    text = render_valid_bound(ValidBoundKind.ONGOING, None, observed_at="2026-07-14")
    assert "2026-07-14" in text
    assert "observed" in text
    assert_conformant_rendering(text, ValidBoundKind.ONGOING)  # does not raise


def test_ongoing_without_an_observation_date_is_refused() -> None:
    with pytest.raises(ValueError, match="SIG-TIME-005"):
        render_valid_bound(ValidBoundKind.ONGOING, None)


def test_currently_phrasing_is_non_conformant() -> None:
    with pytest.raises(ValueError, match="present-tense"):
        assert_conformant_rendering("sharing with 147 orgs currently", ValidBoundKind.ONGOING)


def test_ongoing_and_unknown_are_distinguished() -> None:
    ongoing = render_valid_bound(ValidBoundKind.ONGOING, None, observed_at="2026-07-14")
    unknown = render_valid_bound(ValidBoundKind.UNKNOWN, None)
    assert ongoing != unknown
    assert "observed" in ongoing
    assert unknown == "unknown"


def test_before_and_after_bounds_render_distinctly() -> None:
    assert render_valid_bound(ValidBoundKind.BEFORE, "2025-06-10").startswith("by ")
    assert render_valid_bound(ValidBoundKind.AFTER, "2025-03-14").startswith("from ")
    assert render_valid_bound(ValidBoundKind.EXACT, "2025-03-14") == "2025-03-14"


# --- as-of contract ----------------------------------------------------------


def _utc(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d, tzinfo=UTC)


def test_defaults_are_explicit_world_today_belief_now() -> None:
    now = _utc(2026, 9, 1)
    asof = AsOf.resolve(now=now)
    assert asof.world_defaulted and asof.belief_defaulted
    assert asof.world == _utc(2026, 9, 1)  # today (midnight)
    assert asof.belief == now


def test_where_predicate_filters_both_axes() -> None:
    asof = AsOf.resolve(_utc(2025, 1, 1), _utc(2026, 1, 1))
    where = asof.where()
    assert "valid_period @> %s::timestamptz" in where
    assert "sys_period @> %s::timestamptz" in where
    assert asof.params() == (_utc(2025, 1, 1), _utc(2026, 1, 1))


def test_the_four_questions() -> None:
    now = _utc(2026, 9, 1)
    past_world = _utc(2020, 1, 1)
    past_belief = _utc(2026, 6, 1)
    assert AsOf.resolve(now=now).question(now=now) == AsOfQuestion.CURRENT_BELIEF_NOW
    assert AsOf.resolve(past_world, now=now).question(now=now) == AsOfQuestion.CURRENT_BELIEF_PAST
    assert (
        AsOf.resolve(None, past_belief, now=now).question(now=now) == AsOfQuestion.PAST_BELIEF_NOW
    )
    assert (
        AsOf.resolve(past_world, past_belief, now=now).question(now=now)
        == AsOfQuestion.PAST_BELIEF_PAST
    )
