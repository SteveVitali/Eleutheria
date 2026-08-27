# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Coordinate sensitivity matrix and tier transforms (§43.3, §19.4)."""

from __future__ import annotations

import pytest
from policy.sensitivity import SensitivityClass as C

from policy import sensitivity


@pytest.mark.parametrize(
    "cls,precision,tier",
    [
        (C.C1, "exact", 0),
        (C.C2, "reduced_precision", 1),
        (C.C3, "no_location", 3),
        (C.C4, "jurisdiction_only", 3),
        (C.C5, "jurisdiction_only", 3),
    ],
)
def test_each_class_produces_specified_precision(cls: C, precision: str, tier: int) -> None:
    assert sensitivity.published_precision(cls) == precision
    assert sensitivity.geo_tier_for(cls) == tier


def test_residential_parcel_demotes_to_c3() -> None:
    assert sensitivity.demote_for_residential_parcel(C.C1, True) is C.C3
    assert sensitivity.demote_for_residential_parcel(C.C1, False) is C.C1


def test_candidate_on_residential_parcel_is_never_published() -> None:
    # SIG-PUB-013: never, at any precision, regardless of corroboration.
    assert sensitivity.candidate_publishable(intersects_residential=True) is False
    assert sensitivity.candidate_publishable(intersects_residential=False) is True


def test_leak_provenance_requires_human_review() -> None:
    assert sensitivity.requires_human_review(True) is True


def test_obfuscation_offset_is_deterministic_not_random() -> None:
    # SIG-GEO-009: no random jitter; the offset is a pure function of the asset.
    a = sensitivity.deterministic_offset("asset-1", 500.0)
    b = sensitivity.deterministic_offset("asset-1", 500.0)
    assert a == b
    assert sensitivity.deterministic_offset("asset-2", 500.0) != a
    # And bounded by the published radius.
    assert (a[0] ** 2 + a[1] ** 2) ** 0.5 <= 500.0 + 1e-6


def test_tier_transforms() -> None:
    assert sensitivity.apply_tier(40.123456, -75.654321, 0) == (40.123456, -75.654321)
    trunc = sensitivity.apply_tier(40.123456, -75.654321, 1)
    assert trunc == (40.12, -75.65)
    assert sensitivity.apply_tier(40.0, -75.0, 3) is None
    binned = sensitivity.apply_tier(40.123456, -75.654321, 2)
    assert binned is not None  # snapped to a deterministic grid cell


def test_grid_bin_is_deterministic() -> None:
    p = (40.123456, -75.654321)
    assert sensitivity.apply_tier(*p, 2) == sensitivity.apply_tier(*p, 2)
