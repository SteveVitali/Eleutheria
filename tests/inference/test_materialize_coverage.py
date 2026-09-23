# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Unit tests for the honest §32 coverage materializer's pure functions (P28.4).

The DB-backed materialization is proven over real PG18+PostGIS in
``tests/db/test_coverage_materialize.py``; here we pin the row-building + the hard,
TEST-PINNED **no-total invariant**: the materializer can NEVER emit a population total,
a capture–recapture estimate, or a bare unnamed number (SIG-METRIC-008/009/010). Every
counted-quantity row carries a NAMED, non-reality denominator, and the negative-space
rows carry no denominator by construction.
"""

from __future__ import annotations

import pytest
from inference.completeness import (
    CompletenessMethod,
    ProhibitedEstimateError,
    capture_recapture_population,
    multi_list_log_linear_population,
)
from inference.coverage import CoverageRecord
from inference.denominators import PublishedAggregate
from inference.materialize import (
    absence_row,
    assert_coverage_row_has_named_denominator,
    coverage_input_digest,
    metric_row,
)


def _metric(named_denominator: str = "subjects with a contracted_camera_count claim") -> dict:
    agg = PublishedAggregate(
        label="subjects with a resolved contracted_camera_count value",
        count=1,
        denominator=2,
        not_evaluable=0,
    )
    return metric_row(
        agg,
        method=CompletenessMethod.RECONCILIATION_RATIO,
        named_denominator=named_denominator,
        value=0.5,
        subject_class="subject",
        predicate_id="contracted_camera_count",
    )


def test_metric_row_carries_a_named_denominator_and_reuses_published_aggregate() -> None:
    row = _metric()
    assert row["metric_method"] == "reconciliation_ratio"
    assert row["numerator"] == 1
    assert row["denominator"] == 2
    assert row["not_evaluable"] == 0
    assert row["named_denominator"] == "subjects with a contracted_camera_count claim"
    assert row["metric_value"] == 0.5
    assert row["absence_kind"] == "not_applicable"  # a counted quantity is not an absence
    assert row["input_digest"]  # the idempotency key is set


@pytest.mark.parametrize(
    "reality_denominator",
    ["", "reality", "true population", "all devices", "total", "everything", "the world"],
)
def test_metric_row_refuses_a_denominator_of_reality(reality_denominator: str) -> None:
    """THE no-total pin: a coverage metric can never name a population total (SIG-METRIC-010)."""
    with pytest.raises(ProhibitedEstimateError):
        _metric(named_denominator=reality_denominator)


def test_assert_choke_point_refuses_a_total_metric_row_but_passes_negative_space() -> None:
    # A hand-built metric row implying a total is refused at the choke point.
    total_row = {
        "absence_kind": "not_applicable",
        "metric_method": CompletenessMethod.COUNTED_WITH_DENOMINATOR.value,
        "named_denominator": "total",
        "metric_value": 0.9,
    }
    with pytest.raises(ProhibitedEstimateError):
        assert_coverage_row_has_named_denominator(total_row)

    # A negative-space row (no metric_method) has no denominator by design — allowed.
    absence = absence_row(
        CoverageRecord(
            predicate_id="active_device_count",
            absence_kind="not_researched",
            subject_id="00000000-0000-0000-0000-000000000001",
            subject_class="deployment",
        )
    )
    assert assert_coverage_row_has_named_denominator(absence) is absence
    assert absence["metric_method"] is None
    assert absence["named_denominator"] is None


def test_absence_row_requires_sources_for_searched_not_found() -> None:
    # CoverageRecord itself enforces SIG-METRIC-002 (mirrors the DDL CHECK).
    with pytest.raises(ValueError):
        absence_row(
            CoverageRecord(
                predicate_id="active_device_count",
                absence_kind="searched_not_found",
                subject_id="00000000-0000-0000-0000-000000000001",
                subject_class="deployment",
            )
        )


def test_coverage_input_digest_is_deterministic_and_content_sensitive() -> None:
    a = _metric()
    b = _metric()
    assert coverage_input_digest(a) == coverage_input_digest(b)
    # A changed measurement (a different numerator) → a different digest → a superseding row.
    changed = PublishedAggregate(label=a["metric_label"], count=2, denominator=2)
    c = metric_row(
        changed,
        method=CompletenessMethod.RECONCILIATION_RATIO,
        named_denominator=a["named_denominator"],
        value=1.0,
        subject_class="subject",
        predicate_id="contracted_camera_count",
    )
    assert coverage_input_digest(c) != coverage_input_digest(a)


def test_no_capture_recapture_or_multilist_estimate_is_reachable() -> None:
    """The estimators are always-refusing (SIG-METRIC-008/008a) — no total can leak in."""
    with pytest.raises(ProhibitedEstimateError):
        capture_recapture_population(100, 200, 20)
    with pytest.raises(ProhibitedEstimateError):
        multi_list_log_linear_population([1, 2, 3])
    # And every method the materializer can stamp is one of the four publishable
    # (never-a-total) methods — there is no "population_total" method to select.
    assert set(CompletenessMethod) == {
        CompletenessMethod.COUNTED_WITH_DENOMINATOR,
        CompletenessMethod.RECORDS_DERIVED_BOUNDS,
        CompletenessMethod.RECONCILIATION_RATIO,
        CompletenessMethod.MEASURED_SURVEY_RECALL,
    }
