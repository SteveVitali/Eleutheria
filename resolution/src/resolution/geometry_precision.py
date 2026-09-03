# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Geometry precision and the agency-centroid guard (SIG-IDENT-004).

Agency-registry latitude/longitude (FBI CDE, IPEDS, NTD, …) is a point of unknown
precision — often the town hall, a PO box, or a state-capitol placeholder. Stored
as a device location or used for point-in-polygon jurisdiction assignment it would
be a **fabrication**. So every such point is stamped
``organization_centroid_or_unknown`` and this module is the single gate that
refuses to let that precision flow into a point-in-polygon assignment or an
organization address. The value set mirrors the ontology ``GeometryPrecision``
enum (single source of truth, §20.1); ``tests/resolution/test_vocab_conformance``
fails if the two drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GeometryPrecision(StrEnum):
    """How precisely a stored geometry locates its subject (§14.2, SIG-IDENT-004)."""

    ROOFTOP = "rooftop"
    PARCEL_CENTROID = "parcel_centroid"
    STREET_INTERPOLATED = "street_interpolated"
    PLACE_CENTROID = "place_centroid"
    ORGANIZATION_CENTROID_OR_UNKNOWN = "organization_centroid_or_unknown"


# The precisions that MUST NOT be treated as a real point location. An
# agency-registry centroid can be anywhere inside (or outside) the jurisdiction it
# nominally marks, so it is neither point-in-polygon evidence nor an address.
_NOT_A_REAL_POINT: frozenset[GeometryPrecision] = frozenset(
    {GeometryPrecision.ORGANIZATION_CENTROID_OR_UNKNOWN}
)


class GeometryPrecisionError(ValueError):
    """A geometry was used at a precision its provenance does not support (SIG-IDENT-004)."""


def is_point_in_polygon_usable(precision: GeometryPrecision | str) -> bool:
    """Whether a geometry of this precision may drive point-in-polygon assignment."""
    return GeometryPrecision(precision) not in _NOT_A_REAL_POINT


def assert_point_in_polygon_usable(precision: GeometryPrecision | str) -> None:
    """Refuse an agency centroid for point-in-polygon jurisdiction assignment.

    Raises :class:`GeometryPrecisionError` for
    ``organization_centroid_or_unknown`` (SIG-IDENT-004).
    """
    if not is_point_in_polygon_usable(precision):
        raise GeometryPrecisionError(
            f"geometry precision {GeometryPrecision(precision).value!r} MUST NOT be used "
            "for point-in-polygon jurisdiction assignment — an agency centroid is not a "
            "device location (SIG-IDENT-004)"
        )


def assert_usable_as_address(precision: GeometryPrecision | str) -> None:
    """Refuse an agency centroid as an organization address (SIG-IDENT-004)."""
    if GeometryPrecision(precision) in _NOT_A_REAL_POINT:
        raise GeometryPrecisionError(
            f"geometry precision {GeometryPrecision(precision).value!r} MUST NOT be used "
            "as an organization address (SIG-IDENT-004)"
        )


@dataclass(frozen=True)
class LocatedPoint:
    """A stored geometry paired with the precision it was captured at (SIG-IDENT-004).

    The precision travels *with* the geometry — a point is never stored bare — so a
    downstream consumer cannot lose the fact that an agency-registry point is only a
    centroid. :meth:`as_claim_value_json` is the payload the geometry claim carries.
    """

    geometry: str
    precision: GeometryPrecision

    def __post_init__(self) -> None:
        object.__setattr__(self, "precision", GeometryPrecision(self.precision))

    @property
    def usable_for_point_in_polygon(self) -> bool:
        return is_point_in_polygon_usable(self.precision)

    def as_claim_value_json(self) -> dict[str, str]:
        """The stored payload: geometry + its precision (persisted on the geometry claim)."""
        return {"geometry": self.geometry, "precision": self.precision.value}


def agency_centroid(geometry: str) -> LocatedPoint:
    """Stamp an agency-registry lat/long as ``organization_centroid_or_unknown`` (SIG-IDENT-004)."""
    return LocatedPoint(
        geometry=geometry, precision=GeometryPrecision.ORGANIZATION_CENTROID_OR_UNKNOWN
    )
