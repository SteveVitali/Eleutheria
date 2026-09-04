# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The composed weight ``W`` (§10.6) and currency ``C`` (§28.3).

The load-bearing anchor is Appendix D.2: the same worked reconciliation the spec
publishes MUST reproduce the exact W classes it states — otherwise the ordinal
table is wrong.
"""

from __future__ import annotations

import math
from datetime import date

import pytest
from reconcile.weight import (
    DirectnessExcluded,
    currency,
    directness_for,
    half_life_days,
    predicate_meta,
    weight_class,
)

# --- §10.6 composition -------------------------------------------------------


def test_base_reliability_maps_to_published_classes() -> None:
    # base: R1->W4 R2->W3 R3->W3 R4->W2 R5->W2 R6->W1 (with D1/I1/C1, no change).
    expected = {"R1": 4, "R2": 3, "R3": 3, "R4": 2, "R5": 2, "R6": 1}
    for r, w in expected.items():
        assert weight_class(reliability=r, directness="D1", integrity="I1", currency="C1") == w


def test_appendix_d2_worked_example_reproduces_exact_weight_classes() -> None:
    # docs/2_canonical_design_spec.md §D.2 — the numbers the spec commits to.
    # contracted_device_count: contract, R1 D1 I1 C1 (IMMUTABLE) -> W4.
    assert weight_class(reliability="R1", directness="D1", integrity="I1", currency="C1") == 4
    # active_device_count: portal, R2 D1 I1 C1 -> W3.
    assert weight_class(reliability="R2", directness="D1", integrity="I1", currency="C1") == 3
    # SAME contract as evidence for active: R1 D5 I1 C3 -> W1 (D5 floors at W1).
    assert weight_class(reliability="R1", directness="D5", integrity="I1", currency="C3") == 1
    # mapped_device_count: OSM, R5 D3 I1 C1, structured export + EXACT -> W2.
    assert (
        weight_class(
            reliability="R5",
            directness="D3",
            integrity="I1",
            currency="C1",
            structured_exact=True,
        )
        == 2
    )
    # ...and WITHOUT the structured-export upgrade the same OSM claim is only W1,
    # which is exactly why the upgrade rule is load-bearing for §D.2.
    assert weight_class(reliability="R5", directness="D3", integrity="I1", currency="C1") == 1


def test_d6_is_excluded_not_w0() -> None:
    with pytest.raises(DirectnessExcluded):
        weight_class(reliability="R1", directness="D6", integrity="I1", currency="C1")


def test_d5_and_c4_downgrades_floor_at_w1() -> None:
    # D5 -2 and C4 -2 from R6(W1) would go negative; the floor holds them at W1.
    assert weight_class(reliability="R6", directness="D5", integrity="I1", currency="C1") == 1
    assert weight_class(reliability="R6", directness="D1", integrity="I1", currency="C4") == 1


def test_integrity_downgrade_can_reach_w0() -> None:
    # I3 -2 is NOT floored; R6(W1) - I3(2) clamps to W0 (retained, never resolves).
    assert weight_class(reliability="R6", directness="D1", integrity="I3", currency="C1") == 0


def test_upgrade_is_capped_at_plus_one_and_never_above_w4() -> None:
    # Two upgrade triggers still only add +1.
    assert (
        weight_class(
            reliability="R5",
            directness="D3",
            integrity="I1",
            currency="C1",
            structured_exact=True,
            field_verified=True,
        )
        == 2
    )
    # Never above W4.
    assert (
        weight_class(
            reliability="R1",
            directness="D1",
            integrity="I1",
            currency="C1",
            structured_exact=True,
        )
        == 4
    )


def test_unknown_axis_codes_raise() -> None:
    with pytest.raises(ValueError):
        weight_class(reliability="R9", directness="D1", integrity="I1", currency="C1")


# --- §28.3 currency ----------------------------------------------------------


def test_half_life_parsing() -> None:
    assert math.isinf(half_life_days("infinite"))
    assert half_life_days("6mo") == pytest.approx(182.625)
    assert half_life_days("2y") == pytest.approx(730.5)
    with pytest.raises(ValueError):
        half_life_days("soon")


def test_immutable_predicate_is_always_c1() -> None:
    # An executed contract from years ago is still C1 for an IMMUTABLE predicate.
    assert (
        currency(
            volatility_class="IMMUTABLE",
            half_life="infinite",
            observed_at=date(2020, 1, 1),
            as_of=date(2026, 9, 1),
        )
        == "C1"
    )


def test_currency_bands_track_half_life() -> None:
    # FAST predicate, 6mo half-life (~182.6 days).
    kw = {"volatility_class": "FAST", "half_life": "6mo", "as_of": date(2026, 9, 1)}
    assert currency(observed_at=date(2026, 8, 1), **kw) == "C1"  # ~31d <= 0.5h
    assert currency(observed_at=date(2026, 4, 1), **kw) == "C2"  # ~153d in (0.5h,1.0h]
    assert currency(observed_at=date(2025, 9, 1), **kw) == "C3"  # ~365d in (1.0h,3.0h]
    assert currency(observed_at=date(2023, 1, 1), **kw) == "C4"  # > 3.0h


# --- registry access ---------------------------------------------------------


def test_registry_carries_all_six_count_predicates() -> None:
    for basis in ("contracted", "invoiced", "installed", "active", "mapped", "claimed"):
        meta = predicate_meta(f"{basis}_device_count")
        assert meta["volatility_class"]
        assert meta["half_life"]


def test_directness_matches_appendix_d_for_osm_mapped() -> None:
    # §D.2: OSM is D3 for mapped_device_count (a close proxy / lower bound).
    assert directness_for("mapped_device_count", "osm_node_set") == "D3"
    # An executed contract is D1 for the count it obliges.
    assert directness_for("contracted_device_count", "executed_contract") == "D1"
