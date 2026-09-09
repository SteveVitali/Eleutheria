# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Opt-in, aggregate-only onboarding timing (P21.7, §34.2, SIG-CONTRIB-003).

Part VIII §0.7: the aggregate keeps ONLY a count + median — no per-user rows, no
identity. These tests pin that guarantee and the median computation.
"""

from __future__ import annotations

import pytest
from tasks.onboarding import MEDIAN_TARGET_MINUTES, OnboardingTimingAggregate


def test_empty_aggregate_has_no_median() -> None:
    agg = OnboardingTimingAggregate()
    assert agg.count == 0
    assert agg.median_minutes() is None


def test_records_only_count_and_histogram_no_per_user_rows() -> None:
    agg = OnboardingTimingAggregate()
    for minutes in (5.0, 6.5, 7.0, 8.5, 9.0):
        agg.record(minutes)
    assert agg.count == 5
    # The only state is a bucket->count histogram; there is no list of samples,
    # no identity, no per-user row anywhere on the object.
    state = vars(agg)
    assert set(state) == {"bucket_minutes", "_counts"}
    assert all(isinstance(v, int) for v in state["_counts"].values())


def test_median_from_histogram_is_reasonable() -> None:
    agg = OnboardingTimingAggregate(bucket_minutes=1.0)
    for minutes in (5.0, 6.0, 7.0, 8.0, 9.0):
        agg.record(minutes)
    # Median sample is 7.x; bucket midpoint for [7,8) is 7.5.
    assert agg.median_minutes() == pytest.approx(7.5)


def test_median_even_count_averages_two_midpoints() -> None:
    agg = OnboardingTimingAggregate(bucket_minutes=1.0)
    for minutes in (2.0, 4.0):
        agg.record(minutes)
    # midpoints 2.5 and 4.5 -> 3.5
    assert agg.median_minutes() == pytest.approx(3.5)


def test_negative_minutes_refused() -> None:
    with pytest.raises(ValueError):
        OnboardingTimingAggregate().record(-1.0)


def test_to_record_is_aggregate_only() -> None:
    agg = OnboardingTimingAggregate()
    agg.record(4.0)
    agg.record(6.0)
    record = agg.to_record()
    assert record["aggregate_only"] is True
    assert record["opt_in"] is True
    assert record["count"] == 2
    assert record["median_target_minutes"] == MEDIAN_TARGET_MINUTES
    # No per-user field of any kind.
    assert "participants" not in record
    assert "handle" not in record
