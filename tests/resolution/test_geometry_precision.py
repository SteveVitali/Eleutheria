# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Agency centroids are barred from point-in-polygon and address use (SIG-IDENT-004)."""

from __future__ import annotations

import pytest
from resolution.geometry_precision import (
    GeometryPrecision,
    GeometryPrecisionError,
    LocatedPoint,
    agency_centroid,
    assert_point_in_polygon_usable,
    assert_usable_as_address,
    is_point_in_polygon_usable,
)


def test_agency_centroid_is_rejected_for_point_in_polygon() -> None:
    with pytest.raises(GeometryPrecisionError, match="point-in-polygon"):
        assert_point_in_polygon_usable(GeometryPrecision.ORGANIZATION_CENTROID_OR_UNKNOWN)
    assert not is_point_in_polygon_usable(GeometryPrecision.ORGANIZATION_CENTROID_OR_UNKNOWN)


def test_agency_centroid_is_rejected_as_an_address() -> None:
    with pytest.raises(GeometryPrecisionError, match="address"):
        assert_usable_as_address(GeometryPrecision.ORGANIZATION_CENTROID_OR_UNKNOWN)


@pytest.mark.parametrize(
    "precision",
    [
        GeometryPrecision.ROOFTOP,
        GeometryPrecision.PARCEL_CENTROID,
        GeometryPrecision.STREET_INTERPOLATED,
        GeometryPrecision.PLACE_CENTROID,
    ],
)
def test_real_precisions_are_usable(precision: GeometryPrecision) -> None:
    assert is_point_in_polygon_usable(precision)
    assert_point_in_polygon_usable(precision)  # does not raise
    assert_usable_as_address(precision)  # does not raise


def test_string_values_are_accepted() -> None:
    # The guard coerces the wire string form too.
    with pytest.raises(GeometryPrecisionError):
        assert_point_in_polygon_usable("organization_centroid_or_unknown")
    assert is_point_in_polygon_usable("rooftop")


def test_geometry_precision_is_stored_with_the_point() -> None:
    # SIG-IDENT-004: the precision is stored alongside the geometry, never lost.
    point = agency_centroid("POINT(-118.24 34.05)")
    assert point.precision is GeometryPrecision.ORGANIZATION_CENTROID_OR_UNKNOWN
    assert not point.usable_for_point_in_polygon
    payload = point.as_claim_value_json()
    assert payload == {
        "geometry": "POINT(-118.24 34.05)",
        "precision": "organization_centroid_or_unknown",
    }
    # A rooftop-precise point travels with its precision and is usable.
    rooftop = LocatedPoint("POINT(-118.24 34.05)", GeometryPrecision.ROOFTOP)
    assert rooftop.usable_for_point_in_polygon
    assert rooftop.as_claim_value_json()["precision"] == "rooftop"
