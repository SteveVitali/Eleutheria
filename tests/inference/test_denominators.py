# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Published denominators and per-jurisdiction coverage (§32.2, §32.3, §32.4).

AC2: every published aggregate carries a denominator (and its not-evaluable count);
a bare count fails the build. SIG-METRIC-004: per-jurisdiction coverage is computed.
SIG-METRIC-005: provenance completeness is measured and a shortfall is a defect list.
"""

from __future__ import annotations

import pytest
from inference.denominators import (
    AgencyCoverageInput,
    PublishedAggregate,
    assert_denominated,
    jurisdiction_coverage,
    provenance_completeness,
)


def test_published_aggregate_phrase_is_conformant() -> None:
    """The §32.2 conformant phrasing carries denominator and not-evaluable inline."""
    agg = PublishedAggregate(label="agencies", count=37, denominator=214, not_evaluable=1109)
    assert "37 of 214 evaluable agencies" in agg.phrase()
    assert "1109 not evaluable" in agg.phrase()
    assert agg.as_json()["denominator"] == 214


def test_a_numerator_cannot_exceed_its_denominator() -> None:
    with pytest.raises(ValueError, match="exceeds evaluable denominator"):
        PublishedAggregate(label="agencies", count=5, denominator=3)


def test_bare_count_is_not_publishable() -> None:
    """AC2: a bare count fails the build; only a PublishedAggregate may publish."""
    with pytest.raises(TypeError, match="MUST be a PublishedAggregate"):
        assert_denominated(37)
    agg = PublishedAggregate(label="agencies", count=37, denominator=214)
    assert assert_denominated(agg) is agg


def _agencies() -> list[AgencyCoverageInput]:
    return [
        AgencyCoverageInput(
            "a1",
            has_deployment_evidence=True,
            has_contract_evidence=True,
            has_portal_evidence=True,
            has_mapped_devices=True,
            evidence_age_days=100,
            open_contradictions=1,
            weight_class="W3",
        ),
        AgencyCoverageInput(
            "a2",
            has_deployment_evidence=True,
            evidence_age_days=300,
            open_contradictions=2,
            weight_class="W1",
        ),
        AgencyCoverageInput("a3", weight_class="W1"),  # known, no evidence, no age
    ]


def test_jurisdiction_coverage_denominates_every_count() -> None:
    """SIG-METRIC-004: each per-jurisdiction count is denominated by agencies known."""
    cov = jurisdiction_coverage("jurisdiction:ok", _agencies())
    assert cov.agencies_known == 3
    assert (cov.with_deployment_evidence.count, cov.with_deployment_evidence.denominator) == (2, 3)
    assert (cov.with_contract_evidence.count, cov.with_contract_evidence.denominator) == (1, 3)
    assert (cov.with_portal_evidence.count, cov.with_portal_evidence.denominator) == (1, 3)
    assert (cov.with_mapped_devices.count, cov.with_mapped_devices.denominator) == (1, 3)


def test_jurisdiction_coverage_mean_age_and_distribution() -> None:
    cov = jurisdiction_coverage("jurisdiction:ok", _agencies())
    # mean over the two agencies with dated evidence only (never a silent zero for a3).
    assert cov.mean_evidence_age_days == pytest.approx((100 + 300) / 2)
    assert cov.open_contradiction_count == 3
    assert cov.weight_class_distribution == {"W3": 1, "W1": 2}


def test_jurisdiction_coverage_mean_age_is_none_when_no_dated_evidence() -> None:
    cov = jurisdiction_coverage("j", [AgencyCoverageInput("a1"), AgencyCoverageInput("a2")])
    assert cov.mean_evidence_age_days is None


def test_jurisdiction_coverage_rejects_duplicate_agency() -> None:
    with pytest.raises(ValueError, match="duplicate agency id"):
        jurisdiction_coverage("j", [AgencyCoverageInput("a1"), AgencyCoverageInput("a1")])


def test_every_known_agency_is_evaluable_so_not_evaluable_is_zero() -> None:
    """§32.2: a 'no' to 'has any deployment evidence' is a negative answer, not a
    missing-data exclusion — so every known agency is evaluable (not_evaluable == 0)."""
    cov = jurisdiction_coverage("j", _agencies())
    assert cov.with_deployment_evidence.not_evaluable == 0
    assert cov.with_deployment_evidence.denominator == cov.agencies_known


def test_agency_input_rejects_negative_inputs() -> None:
    with pytest.raises(ValueError, match="evidence_age_days cannot be negative"):
        AgencyCoverageInput("a1", evidence_age_days=-1)
    with pytest.raises(ValueError, match="open_contradictions cannot be negative"):
        AgencyCoverageInput("a1", open_contradictions=-1)


# --- provenance completeness (SIG-METRIC-005) --------------------------------


def test_provenance_shortfall_is_a_defect_list_not_a_statistic() -> None:
    """SIG-METRIC-005: a shortfall names the offending claims; it is actionable."""
    pc = provenance_completeness(
        ["c1", "c2", "c3", "c4"],
        claims_with_resolvable_evidence=["c1", "c3"],
    )
    assert pc.published_claims == 4
    assert pc.with_resolvable_evidence == 2
    assert set(pc.defects) == {"c2", "c4"}  # the defect list, not just "50%"
    assert pc.share == pytest.approx(0.5)
    assert pc.is_complete is False


def test_provenance_complete_when_all_resolvable() -> None:
    pc = provenance_completeness(["c1", "c2"], claims_with_resolvable_evidence=["c1", "c2"])
    assert pc.is_complete is True
    assert pc.share == 1.0
    assert pc.defects == ()


def test_provenance_empty_is_trivially_complete() -> None:
    pc = provenance_completeness([], claims_with_resolvable_evidence=[])
    assert pc.share == 1.0
    assert pc.is_complete is True
