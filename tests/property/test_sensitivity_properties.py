# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Property-based tests for the coordinate transforms (§48 taxonomy; ADR-019).

These assert the SIG-GEO-009 invariant — obfuscation offsets are deterministic
per asset and bounded by the published radius — over randomized inputs, the way
the §48 'temporal property tests' row asks pure logic to be checked.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from policy import sensitivity

_coord = st.floats(min_value=-179.0, max_value=179.0, allow_nan=False, allow_infinity=False)


@given(asset_id=st.text(min_size=1, max_size=40), radius=st.floats(min_value=1.0, max_value=5000.0))
def test_offset_is_deterministic_and_bounded(asset_id: str, radius: float) -> None:
    a = sensitivity.deterministic_offset(asset_id, radius)
    b = sensitivity.deterministic_offset(asset_id, radius)
    assert a == b  # no randomness (SIG-GEO-009)
    assert (a[0] ** 2 + a[1] ** 2) ** 0.5 <= radius + 1e-6  # within published radius


@given(lat=_coord, lon=_coord)
def test_truncation_is_idempotent_and_never_increases_precision(lat: float, lon: float) -> None:
    once = sensitivity.apply_tier(lat, lon, 1)
    assert once is not None
    twice = sensitivity.apply_tier(once[0], once[1], 1)
    assert once == twice  # truncation is idempotent
    assert abs(once[0]) <= abs(lat) + 1e-9  # truncation moves toward zero, never away
