# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.16 — geometry defects at ingest (R11-DATA-01 / F-322 / SIG-GEO-008).

Covers, without the database:

* ``axis_order`` — the declared positional order every target carries; the
  closed vocabulary fails closed, the documented default serves synthetic
  targets only, and the ``lat-lon`` declaration un-transposes a transposed
  positional pair (the F-322 Nottingham/mark43 defect class) while a NAMED
  pair stays name-authoritative;
* the four detectors on the resolved pair — ``null_island`` (near-(0,0)),
  ``axis_swap`` (transposed-rescue), ``sign_flip`` (single-axis negation),
  ``wrong_jurisdiction`` (outside the declared bound, unrescued) — plus the
  recorded skip when no bound resolves;
* emit: a defect-marked point asserts a ``geometry_defect`` claim (class +
  observed pair + failed bound in the claim evidence) and NO device-point
  coordinate claims — the defective pair is marked, never asserted as a
  location (SIG-IDENT-004); the parcel screen records ``unscreened``;
* registry validation: every committed target declares ``axis_order`` and a
  resolvable detector bound; the committed ``sig.geometry-corrections/1``
  artifact resolves all seven F-322 groups;
* parity: ``db.geometry_corrections.classify_defect`` derives the same
  verdicts as the ingest detector on the same inputs.
"""

from __future__ import annotations

from typing import Any

import pytest
from connectors.dot_511 import (
    AxisOrderNotDeclared,
    ExtentNotDeclared,
    GeometryDefect,
    assert_target_axis_order,
    detect_geometry_defect,
    extract_coordinate,
    geometry_correction_scopes,
    scan_extents,
    target_geometry_violations,
)
from db.geometry_corrections import DEFECT_CLASSES, classify_defect

from connectors import dot_511

_RETRIEVED_ISO = "2026-09-17T00:00:00+00:00"


def _target(**over: Any) -> dict[str, Any]:
    target: dict[str, Any] = {
        "id": "t_p3516",
        "kind": "arcgis_query",
        "state": "GA",
        "jurisdiction_scheme": "us.state_abbr",
        "agency": "Test DOT",
        "sensitivity_class": "C1",
        "technology": "fixed-camera-ptz",
        "geometry_kind": "point",
    }
    target.update(over)
    return target


def _raw(
    lat: float,
    lon: float,
    *,
    fields: dict[str, Any] | None = None,
    geometry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "record_kind": "camera_feature",
        "feature_index": 0,
        "fields": (
            {"id": "CAM-1", "latitude": lat, "longitude": lon} if fields is None else fields
        ),
        "excluded_fields": (),
        "geometry": {"x": lon, "y": lat} if geometry is None else geometry,
        "source_uri": "https://example.invalid/p3516",
        "retrieved_at": _RETRIEVED_ISO,
        "target": _target(),
    }


def _entry(raw: dict[str, Any], target: dict[str, Any]):
    return dot_511._entry_from_raw("camreg_city_muni", raw, target)


# --- axis order: the declared positional read ---------------------------------


def test_axis_order_defaults_to_the_declared_lon_lat() -> None:
    """The documented default is the Esri/GeoJSON slot order — synthetic
    targets without the field still read ``x``=longitude."""
    assert assert_target_axis_order({"id": "t"}) == "lon-lat"
    lat, lon, source = extract_coordinate({}, {"x": -84.4, "y": 33.7})
    assert (lat, lon) == (33.7, -84.4)
    assert source == "geometry"


def test_lat_lon_order_untransposes_positional_geometry() -> None:
    """The Nottingham/mark43 class: the feed serves lat in the x slot; the
    declared ``lat-lon`` order reads it correctly and records the applied
    order on the coordinate source."""
    assert assert_target_axis_order({"id": "t", "axis_order": "lat-lon"}) == "lat-lon"
    lat, lon, source = extract_coordinate({}, {"x": 33.7, "y": -84.4}, axis_order="lat-lon")
    assert (lat, lon) == (33.7, -84.4)
    assert source == "geometry:lat-lon"


def test_axis_order_is_closed_vocabulary() -> None:
    """A guessed orientation is a broken declaration — fail closed."""
    with pytest.raises(AxisOrderNotDeclared):
        assert_target_axis_order({"id": "t", "axis_order": "xy"})
    with pytest.raises(AxisOrderNotDeclared):
        extract_coordinate({}, {"x": 1.0, "y": 2.0}, axis_order="north-east")


def test_axis_order_applies_to_geojson_coordinate_slots() -> None:
    """A GeoJSON ``coordinates[]`` pair is positional — ``lat-lon`` reads the
    first slot as latitude."""
    from connectors.dot_511 import socrata_point_geometry

    geometry = socrata_point_geometry({"the_geom": {"type": "Point", "coordinates": [33.7, -84.4]}})
    assert geometry is not None
    lat, lon, _src = extract_coordinate({}, geometry, axis_order="lat-lon")
    assert (lat, lon) == (33.7, -84.4)


def test_named_pair_is_authoritative_under_any_axis_order() -> None:
    """A keyed point object (named latitude/longitude) is never re-ordered —
    a swapped NAMED column is a detector defect, not a silent relabel."""
    from connectors.dot_511 import socrata_point_geometry

    geometry = socrata_point_geometry({"the_geom": {"latitude": 33.7, "longitude": -84.4}})
    assert geometry is not None and geometry.get("named") is True
    lat, lon, source = extract_coordinate({}, geometry, axis_order="lat-lon")
    assert (lat, lon) == (33.7, -84.4)
    assert source == "geometry"


def test_named_field_pairs_are_axis_order_independent() -> None:
    """Aliased ``latitude``/``longitude`` attribute fields win under either
    declared order — a publisher that swapped its named columns surfaces as
    a detector finding on the resolved pair, never a relabel."""
    lat, lon, source = extract_coordinate(
        {"latitude": 33.7, "longitude": -84.4},
        {"x": 1.0, "y": 2.0},
        axis_order="lat-lon",
    )
    assert (lat, lon) == (33.7, -84.4)
    assert source.startswith("fields:")


# --- the detectors on the resolved pair ----------------------------------------

_GA = {"id": "t_ga", "state": "GA", "jurisdiction_scheme": "us.state_abbr"}
_GA_EXTENT = (-85.7, 30.3, -80.7, 35.1)  # the committed us.state_abbr:GA bound


def test_detector_flags_the_axis_swap_class() -> None:
    """F-322's Nottingham/mark43 shape: the published pair sits outside the
    bound and its transposition lands inside."""
    defect = detect_geometry_defect(-84.4, 33.7, _GA)
    assert defect is not None and defect.defect_class == "axis_swap"
    ev = defect.as_evidence()
    assert ev["observed_latitude"] == -84.4 and ev["observed_longitude"] == 33.7
    assert ev["declared_extent"] == list(_GA_EXTENT)
    assert ev["extent_ref"] == "us.state_abbr:GA"


def test_detector_flags_null_island_without_a_bound() -> None:
    """(0,0)-class placeholders need no extent — the oceanic signature is
    defective on its own (dot_511_ga / camreg_fl511_fl)."""
    defect = detect_geometry_defect(0.4, -0.6, {"id": "t", "state": "ZZ"})
    assert defect is not None and defect.defect_class == "null_island"
    assert defect.extent is None and defect.extent_ref == "none"
    # just outside the 1° bound is NOT null-island
    far = detect_geometry_defect(1.5, 1.5, {"id": "t", "state": "ZZ"})
    assert far is None or far.defect_class != "null_island"


def test_detector_flags_a_single_axis_sign_flip() -> None:
    """A hemisphere-impossible sign: negating exactly one axis lands the
    point inside the bound — the defect is recorded, never silently
    corrected."""
    defect = detect_geometry_defect(-33.7, -84.4, _GA)  # lat negated
    assert defect is not None and defect.defect_class == "sign_flip"
    assert "latitude" in defect.detail


def test_detector_flags_wrong_jurisdiction_unrescued() -> None:
    """F-322's gmh_emc/bangla/oosgis/trafficops class: outside the declared
    bound, no transposition or single sign flip rescues the pair."""
    defect = detect_geometry_defect(47.9, 106.9, _GA)  # Mongolia, labeled GA
    assert defect is not None and defect.defect_class == "wrong_jurisdiction"


def test_detector_passes_an_in_extent_point() -> None:
    assert detect_geometry_defect(33.7, -84.4, _GA) is None


def test_detector_records_a_skip_when_no_bound_resolves() -> None:
    """An unresolved jurisdiction carries no declared extent — the check is
    a recorded skip, never a silent pass and never a fabricated defect."""
    target = {"id": "t", "state": "ZZ", "jurisdiction_scheme": "sig.unresolved"}
    assert detect_geometry_defect(50.0, 4.0, target) is None


def test_target_extent_overrides_the_jurisdiction_bound() -> None:
    """The declared target ``extent`` is the bound a record checks against —
    city-tier targets declare tighter bounds than their jurisdiction."""
    defect = detect_geometry_defect(
        53.2,
        -1.2,
        {
            **_GA,
            "state": "GB-NTT",
            "jurisdiction_scheme": "iso.3166_2",
            "extent": [-1.4, 52.8, -0.9, 53.1],
        },
    )
    assert defect is not None and defect.defect_class == "wrong_jurisdiction"
    assert defect.extent_ref == "target:t_ga"
    assert (
        detect_geometry_defect(
            52.95,
            -1.15,
            {
                **_GA,
                "state": "GB-NTT",
                "jurisdiction_scheme": "iso.3166_2",
                "extent": [-1.4, 52.8, -0.9, 53.1],
            },
        )
        is None
    )


def test_extent_declaration_is_validated_fail_closed() -> None:
    from connectors.dot_511 import _extent_tuple

    with pytest.raises(ExtentNotDeclared):
        _extent_tuple([1.0, 2.0, 3.0], owner="t")  # wrong arity
    with pytest.raises(ExtentNotDeclared):
        _extent_tuple([5.0, 90.0, -5.0, 91.0], owner="t")  # inverted/out-of-range
    with pytest.raises(ExtentNotDeclared):
        _extent_tuple(["a", 0.0, 1.0, 1.0], owner="t")


# --- emit: the defect-marked record -------------------------------------------


def test_defect_marked_entry_emits_mark_and_no_point_claims() -> None:
    """A published pair outside its declared bound emits a ``geometry_defect``
    claim and NO ``camera_latitude``/``camera_longitude`` — the defective
    pair is marked in the evidence, never asserted as a location."""
    target = _target()  # us.state_abbr:GA bound
    raw = _raw(47.9, 106.9)  # Mongolia — wrong_jurisdiction on the GA bound
    entry = _entry(raw, target)
    assert entry.geometry_defect is not None
    assert entry.geometry_defect.defect_class == "wrong_jurisdiction"
    assert entry.latitude is None and entry.longitude is None
    # The parcel screen never ran against a point the evidence doesn't
    # support — the recorded verdict is `unscreened`, never `clear`.
    assert entry.parcel_screen == "unscreened"
    assert entry.residential_parcel_flag is False

    rows = entry.claim_rows("https://example.invalid/p3516", _RETRIEVED_ISO, 0)
    predicates = {r["predicate_id"] for r in rows}
    assert "geometry_defect" in predicates
    assert "camera_latitude" not in predicates
    assert "camera_longitude" not in predicates
    # `camera_coordinate_source` survives — it records WHICH read produced
    # the withheld pair.
    assert "camera_coordinate_source" in predicates

    defect_claim = [r for r in rows if r["predicate_id"] == "geometry_defect"][0]
    assert defect_claim["value"] == "wrong_jurisdiction"
    ev = defect_claim["evidence"]["geometry_defect"]
    assert ev["defect_class"] == "wrong_jurisdiction"
    assert ev["observed_latitude"] == 47.9 and ev["observed_longitude"] == 106.9
    assert ev["declared_extent"] == list(_GA_EXTENT)
    assert ev["extent_ref"] == "us.state_abbr:GA"
    assert ev["detector"] == "sig.p35-16-geometry-detector/1"

    entity = [r for r in rows if r["predicate_id"] == "traffic_camera"][0]
    assert entity["geometry_defect"]["defect_class"] == "wrong_jurisdiction"
    assert entity["axis_order"] == "lon-lat"
    assert entity["latitude"] is None and entity["longitude"] is None


def test_null_island_entry_marks_and_withholds() -> None:
    """The (0,0) placeholder is marked ``null_island`` — the F-322
    dot_511_ga / camreg_fl511_fl class."""
    entry = _entry(_raw(0.0, 0.0), _target())
    assert entry.geometry_defect is not None
    assert entry.geometry_defect.defect_class == "null_island"
    rows = entry.claim_rows("https://example.invalid/p3516", _RETRIEVED_ISO, 0)
    defect = [r for r in rows if r["predicate_id"] == "geometry_defect"]
    assert defect and defect[0]["value"] == "null_island"
    assert not [r for r in rows if r["predicate_id"] == "camera_latitude"]


def test_axis_swapped_feed_marks_axis_swap() -> None:
    """A feed serving the pair transposed under a ``lon-lat`` declaration
    flags ``axis_swap`` — the un-corrected reading lands outside the bound
    and its transposition lands inside."""
    target = _target()
    raw = _raw(-84.4, 33.7)  # transposed Atlanta — outside GA, swap rescues
    entry = _entry(raw, target)
    assert entry.geometry_defect is not None
    assert entry.geometry_defect.defect_class == "axis_swap"


def test_lat_lon_declared_target_reads_transposed_feed_clean() -> None:
    """Under a ``lat-lon`` declaration the same transposed feed is read
    correctly at extraction — no defect, the coordinate asserts."""
    target = _target(axis_order="lat-lon")
    # The feed serves the pair transposed (x slot carries latitude); no
    # named lat/lon fields, so the positional read applies the declared
    # order.
    raw = _raw(33.7, -84.4, fields={"id": "CAM-1"}, geometry={"x": 33.7, "y": -84.4})
    entry = _entry(raw, target)
    assert entry.geometry_defect is None
    assert entry.latitude == pytest.approx(33.7)
    assert entry.longitude == pytest.approx(-84.4)
    assert entry.coordinate_source == "geometry:lat-lon"
    rows = entry.claim_rows("https://example.invalid/p3516", _RETRIEVED_ISO, 0)
    assert {r["predicate_id"] for r in rows} >= {
        "camera_latitude",
        "camera_longitude",
    }
    assert not [r for r in rows if r["predicate_id"] == "geometry_defect"]


def test_swapped_named_columns_flag_defect_never_relabel() -> None:
    """A publisher that swapped its NAMED latitude/longitude columns is a
    detector finding — the fields stay name-authoritative (the record marks
    the observed pair, it does not silently swap them)."""
    target = _target()
    # Published fields carry the swapped values verbatim.
    raw = _raw(-84.4, 33.7, fields={"id": "C", "latitude": -84.4, "longitude": 33.7})
    entry = _entry(raw, target)
    assert entry.geometry_defect is not None
    assert entry.geometry_defect.defect_class == "axis_swap"


def test_hand_built_defect_entry_invariants_fail_closed() -> None:
    """The entry's own contract: the defect class is closed vocabulary; a
    defect-marked record never also asserts a device coordinate; the axis
    order is a declared member — a hand-built violation raises, never emits."""
    base: dict[str, Any] = dict(
        camera_ref="CAM-1",
        source_id="camreg_city_muni",
        target_id="t_p3516",
        state="GA",
        agency="Test DOT",
        latitude=None,
        longitude=None,
        coordinate_source="geometry",
        geo_tier=1,
        sensitivity_class="C1",
        technology="fixed-camera-ptz",
        record_kind="fixed-camera-ptz",
        geometry_kind="point",
        license_spdx="CC0-1.0",
        jurisdiction_scheme="us.state_abbr",
    )
    defect = GeometryDefect("axis_swap", -1.2, 53.0, (-1.4, 52.8, -0.9, 53.1), "ref", "d")
    # a defect + a coordinate: the defective pair must never assert
    with pytest.raises(ValueError, match="never asserted as a location"):
        dot_511.CameraRegistryEntry(
            **{**base, "latitude": 53.0, "longitude": -1.2, "geometry_defect": defect}
        )
    # an invented class: closed vocabulary
    with pytest.raises(ValueError, match="closed|member"):
        dot_511.CameraRegistryEntry(
            **{
                **base,
                "geometry_defect": GeometryDefect("teleported", -1.2, 53.0, None, "ref", "d"),
            }
        )
    # an undeclared axis order
    with pytest.raises(ValueError, match="axis_order"):
        dot_511.CameraRegistryEntry(
            **{**base, "axis_order": "xy", "latitude": 1.0, "longitude": 2.0}
        )
    # a defect + parcel flag: the screen never ran on the defective pair
    with pytest.raises(ValueError, match="parcel"):
        dot_511.CameraRegistryEntry(
            **{
                **base,
                "geometry_defect": defect,
                "parcel_screen": "intersects",
                "residential_parcel_flag": True,
                "sensitivity_class": "C3",
                "geo_tier": 3,
            }
        )


# --- registry + artifact declarations ------------------------------------------


def test_committed_registry_passes_the_geometry_self_check() -> None:
    """Every committed target declares ``axis_order`` and a resolvable
    detector bound — ``sig-connectors validate``'s P35.16 surface is clean."""
    assert target_geometry_violations() == []


def test_correction_artifact_resolves_all_seven_f322_groups() -> None:
    """The committed ``sig.geometry-corrections/1`` artifact resolves every
    declared row — ten (source, target) rows covering the seven groups."""
    scopes = geometry_correction_scopes()
    groups = {s.group for s in scopes}
    assert groups == {
        "nottingham_axis_swap",
        "mark43_axis_swap",
        "trafficops_d5_wrong_jurisdiction",
        "gmh_emc_wrong_jurisdiction",
        "bangla_wrong_jurisdiction",
        "oosgis_wrong_jurisdiction",
        "ga_fl511_null_island",
    }
    for scope in scopes:
        assert scope.expected_class in DEFECT_CLASSES
        # every declared group resolves a bound (null_island rows still
        # carry their jurisdiction extent for the recorded evidence)
        assert scope.extent is not None and scope.extent_ref != "unresolved"


def test_scan_extents_cover_keyed_targets() -> None:
    """The out-of-scope scan resolves a bound for every coded target."""
    extents = scan_extents()
    assert ("camreg_nottingham_gb", "nottingham_gb_cctv_cameras") in extents
    assert ("dot_511_ga", "ga_gdot_511_cameras") in extents


# --- detector parity between ingest and the correction pass --------------------


@pytest.mark.parametrize(
    ("lat", "lon", "expected"),
    [
        (33.7, -84.4, None),  # in extent — clean
        (0.2, -0.1, "null_island"),  # near (0,0)
        (-84.4, 33.7, "axis_swap"),  # transposed-rescue
        (-33.7, -84.4, "sign_flip"),  # single-axis negation
        (47.9, 106.9, "wrong_jurisdiction"),  # Mongolia labeled GA
    ],
)
def test_correction_classifier_parity(lat: float, lon: float, expected: str | None) -> None:
    """``db.geometry_corrections.classify_defect`` derives the same verdict as
    the ingest detector on the same pair + bound — the correction pass can
    never disagree with the emit path."""
    defect = detect_geometry_defect(lat, lon, _GA)
    ingest_class = defect.defect_class if defect else None
    assert ingest_class == expected
    assert classify_defect(lat, lon, _GA_EXTENT) == expected
