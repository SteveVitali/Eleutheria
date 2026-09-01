# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Completeness-estimation guardrails and the capture–recapture ban (§32.5).

AC5: any completeness estimate publishes its violated assumptions or is omitted; a
test asserts no capture–recapture / multi-list population estimate is ever published
(SIG-METRIC-008/008a). The one legitimate exception is records-derived survey recall
(SIG-METRIC-008b), and SIG publishes named-denominator figures, never a total
(SIG-METRIC-009/010).
"""

from __future__ import annotations

import pytest
from inference.completeness import (
    CompletenessMethod,
    CompletenessStatement,
    ProhibitedEstimateError,
    RecordsDerivedRecall,
    assert_no_population_total,
    capture_recapture_population,
    multi_list_log_linear_population,
)


def test_capture_recapture_is_never_published() -> None:
    """AC5 / SIG-METRIC-008: capture–recapture always refuses — not with a caveat."""
    with pytest.raises(ProhibitedEstimateError, match="SIG-METRIC-008"):
        capture_recapture_population(n1=100, n2=80, m2=20)


def test_multi_list_log_linear_is_never_published() -> None:
    """SIG-METRIC-008a: multi-list log-linear rescue also refuses."""
    with pytest.raises(ProhibitedEstimateError, match="SIG-METRIC-008a"):
        multi_list_log_linear_population(lists=[[1], [2], [3]])


def test_completeness_statement_rejects_a_denominator_of_reality() -> None:
    """SIG-METRIC-010: no figure may imply it knows the denominator of reality."""
    for bad in ("reality", "true population", "all devices", "total", ""):
        with pytest.raises(ProhibitedEstimateError, match="SIG-METRIC-010"):
            CompletenessStatement(
                method=CompletenessMethod.COUNTED_WITH_DENOMINATOR,
                named_denominator=bad,
                value=0.4,
            )


def test_completeness_statement_with_a_named_denominator_is_publishable() -> None:
    stmt = CompletenessStatement(
        method=CompletenessMethod.COUNTED_WITH_DENOMINATOR,
        named_denominator="agencies known in Oklahoma",
        value=0.4,
        violated_assumptions=("portal opt-in is self-selected",),
    )
    assert stmt.as_json()["named_denominator"] == "agencies known in Oklahoma"
    assert stmt.as_json()["violated_assumptions"] == ["portal opt-in is self-selected"]
    assert assert_no_population_total(stmt) is stmt


def test_completeness_statement_always_publishes_its_assumptions_field() -> None:
    """AC5: a published estimate publishes its violated assumptions; the only way to
    *not* publish is to omit the statement (there is no defensible-total path)."""
    # A counted quantity legitimately has no violated population assumptions.
    counted = CompletenessStatement(
        method=CompletenessMethod.COUNTED_WITH_DENOMINATOR,
        named_denominator="agencies known in Oklahoma",
        value=0.4,
    )
    assert "violated_assumptions" in counted.as_json()
    # An estimate that must disclose its assumptions can carry them explicitly.
    disclosed = CompletenessStatement(
        method=CompletenessMethod.RECONCILIATION_RATIO,
        named_denominator="OKCPD records vs portal count",
        value=1.2,
        violated_assumptions=("portal counts lag the records channel",),
    )
    assert disclosed.as_json()["violated_assumptions"] == ["portal counts lag the records channel"]


def test_a_bare_number_is_not_a_publishable_completeness_figure() -> None:
    """SIG-METRIC-009: only a named-denominator statement may publish."""
    with pytest.raises(ProhibitedEstimateError, match="SIG-METRIC-009/010"):
        assert_no_population_total(0.42)


# --- the one legitimate exception: records-derived recall (SIG-METRIC-008b) --


def test_records_derived_recall_measures_the_survey_not_the_population() -> None:
    recall = RecordsDerivedRecall(
        jurisdiction_id="jurisdiction:ok",
        predicate_id="active_device_count",
        inventory_size=50,
        survey_found_in_inventory=40,
        pre_registered=True,
        window_days=30,
        predicate_half_life_days=182.0,
    )
    assert recall.recall == pytest.approx(0.8)
    stmt = recall.statement()
    # It is published as SIG's method-recall, denominated by the records inventory,
    # never a population total and never extrapolated beyond the named jurisdiction.
    assert stmt.method is CompletenessMethod.MEASURED_SURVEY_RECALL
    assert "jurisdiction:ok" in stmt.named_denominator
    assert stmt.value == pytest.approx(0.8)


def test_records_derived_recall_must_be_pre_registered() -> None:
    with pytest.raises(ProhibitedEstimateError, match="pre-registered"):
        RecordsDerivedRecall(
            jurisdiction_id="j",
            predicate_id="active_device_count",
            inventory_size=50,
            survey_found_in_inventory=40,
            pre_registered=False,
            window_days=30,
            predicate_half_life_days=182.0,
        )


def test_records_derived_recall_requires_a_located_inventory() -> None:
    """SIG-METRIC-008b: a bare count cannot support device-level linkage."""
    with pytest.raises(ProhibitedEstimateError, match="with locations"):
        RecordsDerivedRecall(
            jurisdiction_id="j",
            predicate_id="active_device_count",
            inventory_size=50,
            survey_found_in_inventory=40,
            pre_registered=True,
            window_days=30,
            predicate_half_life_days=182.0,
            inventory_has_locations=False,
        )


def test_records_derived_recall_requires_a_blind_survey() -> None:
    """SIG-METRIC-008b: a sighted survey is not independent of the inventory."""
    with pytest.raises(ProhibitedEstimateError, match="blind"):
        RecordsDerivedRecall(
            jurisdiction_id="j",
            predicate_id="active_device_count",
            inventory_size=50,
            survey_found_in_inventory=40,
            pre_registered=True,
            window_days=30,
            predicate_half_life_days=182.0,
            survey_blind=False,
        )


def test_records_derived_recall_window_must_beat_the_half_life() -> None:
    with pytest.raises(ProhibitedEstimateError, match="SIG-METRIC-008b"):
        RecordsDerivedRecall(
            jurisdiction_id="j",
            predicate_id="active_device_count",
            inventory_size=50,
            survey_found_in_inventory=40,
            pre_registered=True,
            window_days=200,
            predicate_half_life_days=182.0,
        )
