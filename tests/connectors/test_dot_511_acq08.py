# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.4 (R11-ACQ-08): the ten official camera layers — five DOT/511
(DE/VT/WV/MI/NC) and five municipal (Lincoln/Omaha/Hyattsville/Denver/Seattle).

Drives the REAL ``pipeline.run`` over committed ArcGIS fixtures (no network,
SIG-INGEST-011). Covers: per-target ``out_fields`` capture allowlists, the
reviewed server-side ``where`` filter (Vermont's CCTV-only DeviceList), the
``geometry_kind="area"`` programme-area emit (SIG-GEO-003 — Seattle's polygon
records never mint device-point claims), the media/denied-field exclusions
(values never reach a claim even if they leak into a capture), and the
fail-closed geometry paths.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from connectors.dot_511 import (
    CoordinateRejected,
    Dot511Connector,
    GeometryKindNotDeclared,
    area_geometry,
    assert_target_geometry_kind,
    canary_findings,
    expand_registry_rows,
    registry_targets,
)
from connectors.live_targets import live_targets
from connectors.net import PoliteFetcher, RobotsResult
from connectors.pipeline import run
from connectors.registry import get
from connectors.replay import replay, replay_fingerprint, shadow_replay
from connectors.stages import (
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun

_FIX = Path(__file__).resolve().parent / "fixtures" / "dot_511"
_RETRIEVED = datetime(2026, 10, 12, tzinfo=UTC)
_ALLOW_ALL = "User-agent: *\nAllow: /\n"

#: The P36.4 (ACQ-08) ten-layer scope — eight gated sources plus the two
#: already-permitted sources (P26.16) carrying a new target each.
P36_4_SOURCE_FIXTURES = {
    "dot_511_de": ("de_firstmap.json", "traffic_devices_camera_de_boundary_and_point_layer_26"),
    "dot_511_vt": ("vt_its.json", "its_devicelist_devicelocdetail"),
    "dot_511_wv": ("wv_cctv.json", "cctv_wvdoh_wvdot_assets_mapserver_layer_22"),
    "dot_511_mi": ("mi_midrive.json", "midrive_cameras"),
    "dot_511_nc": ("nc_ncdot.json", "ncdot_cameras"),
    "camreg_ne_lincoln_traffic_cameras": (
        "lincoln_traffic.json",
        "traffic_cameras_traffic_operations_public_monitoring_cameras_city_of_lincoln",
    ),
    "camreg_omaha_ne_parks_cameras": (
        "omaha_parks.json",
        "parks_cameras_city_of_omaha_maintained_cameras_college_world_series",
    ),
    "camreg_hyattsville_md_cctv_camera_2024": (
        "hyattsville_cctv.json",
        "hyattsville_cctv_camera_program_2024",
    ),
    "camreg_denver_co": ("denver_halo.json", "police_halo_cameras_denver_police_department"),
    "camreg_seattle_wa": (
        "seattle_cctv_areas.json",
        "seattle_police_department_cctv_pilot_areas",
    ),
}

#: The eight NEW P36.4 source rows — gated until the operator's OP-26 Wave-B
#: flip under ING-GO-B (Denver/Seattle were already permitted by P26.16).
GATED_P36_4_SOURCES = [
    "dot_511_de",
    "dot_511_vt",
    "dot_511_wv",
    "dot_511_mi",
    "dot_511_nc",
    "camreg_ne_lincoln_traffic_cameras",
    "camreg_omaha_ne_parks_cameras",
    "camreg_hyattsville_md_cctv_camera_2024",
]


class MapTransport:
    """Per-URL canned responses + permissive robots — no real network."""

    def __init__(self, responses: Mapping[str, FetchResult]) -> None:
        self._responses = dict(responses)
        self.request_log: list[str] = []

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ALLOW_ALL)

    def request(
        self,
        url: str,
        *,
        user_agent: str,
        headers: Mapping[str, str] | None = None,
        body: bytes | None = None,
    ) -> FetchResult:
        self.request_log.append(url)
        result = self._responses[url]
        return dataclasses.replace(result, url=url)


def _resp(
    url: str, body: bytes, status: int = 200, retrieved_at: datetime = _RETRIEVED
) -> FetchResult:
    return FetchResult(
        url=url, status=status, body=body, media_type="application/json", retrieved_at=retrieved_at
    )


def _ctx(source_id: str, targets: list[dict[str, Any]], responses: Mapping[str, FetchResult]):
    connector = Dot511Connector()
    source = dataclasses.replace(get(source_id), ingestion_permitted=True)
    fetcher = PoliteFetcher(
        connector_name=connector.name,
        connector_version=connector.version,
        transport=MapTransport(responses),
    )
    return connector, RunContext(
        source=source,
        run=IngestRun(connector.name, connector.version, "test", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": targets},
    )


def _run_fixture(
    source_id: str,
    fixture: str,
    target_id: str | None = None,
    retrieved_at: datetime = _RETRIEVED,
):
    """Run the connector end-to-end over one committed fixture (no network)."""
    if target_id is None:
        target_id = P36_4_SOURCE_FIXTURES[source_id][1]
    targets = [t for t in live_targets(source_id) if t["id"] == target_id]
    assert targets, f"{source_id}:{target_id} must resolve registry targets"
    body = _FIX.joinpath(fixture).read_bytes()
    responses = {
        t["url"]: _resp(
            t["url"],
            body if t.get("page", 0) == 0 else b'{"features": []}',
            retrieved_at=retrieved_at,
        )
        for t in targets
    }
    connector, ctx = _ctx(source_id, targets, responses)
    return run(connector, ctx)


def _claims(report) -> list[Mapping[str, Any]]:
    return [c for c in report.claims if c.get("record_kind") == "claim"]


def _entities(report) -> list[Mapping[str, Any]]:
    return [
        c
        for c in report.claims
        if c.get("predicate_id") == "traffic_camera"
        and c.get("record_kind") != "camera_record_rejected"
    ]


def _rejections(report) -> list[Mapping[str, Any]]:
    return [c for c in report.claims if c.get("record_kind") == "camera_record_rejected"]


def _by_pred(report, predicate: str) -> list[Mapping[str, Any]]:
    return [c for c in _claims(report) if c["predicate_id"] == predicate]


# --- registry expansion --------------------------------------------------------


def test_every_p36_4_target_resolves() -> None:
    """All ten layers expand from the merged registry."""
    for source_id, (_fixture, target_id) in P36_4_SOURCE_FIXTURES.items():
        targets = [t for t in registry_targets(source_id) if t["id"] == target_id]
        assert targets, f"{source_id}:{target_id} has no registry target"
        for t in targets:
            assert t["kind"] == "arcgis_query"
            assert t["url"].startswith(t["layer_url"])
            assert "outSR=4326" in t["url"]
            assert t["state"] and t["agency"]
            assert t["technology"]
            assert t["jurisdiction_scheme"] == "iso.3166_2"


def test_vt_target_filters_to_cctv_devices() -> None:
    """Vermont's ITS DeviceList is narrowed server-side to CCTV rows only."""
    targets = registry_targets("dot_511_vt")
    assert targets
    for t in targets:
        assert t.get("where") == "DeviceType='CCTV'"
        assert "DeviceType%3D%27CCTV%27" in t["url"]


def test_out_fields_allowlist_replaces_the_wildcard() -> None:
    """Every P36.4 target carries the reviewed out_fields allowlist — never
    ``outFields=*`` (P8-5): the raw capture holds only allowlisted columns."""
    for source_id, (_fixture, target_id) in P36_4_SOURCE_FIXTURES.items():
        targets = [t for t in registry_targets(source_id) if t["id"] == target_id]
        assert targets
        for t in targets:
            assert "outFields=%2A" not in t["url"]
            assert t.get("out_fields"), f"{target_id} must declare an out_fields allowlist"


def test_p36_4_targets_apply_the_reviewed_arcgis_budget() -> None:
    """The api_allowlist's ArcGIS request budget rides every expanded target."""
    for source_id, (_fixture, target_id) in P36_4_SOURCE_FIXTURES.items():
        targets = [t for t in registry_targets(source_id) if t["id"] == target_id]
        for t in targets:
            assert int(t.get("rate_limit_per_min") or 0) > 0


def test_nc_target_paginates_over_two_pages() -> None:
    """NCDOT's 1,157 cameras exceed one 1,000-row page → deterministic paging."""
    targets = [t for t in registry_targets("dot_511_nc") if t["id"] == "ncdot_cameras"]
    assert len(targets) == 2
    assert {t["page"] for t in targets} == {0, 1}
    assert all(t["id"] == "ncdot_cameras" for t in targets)


def test_nc_mirror_lineage_row_is_preserved() -> None:
    """The RunNeals mirror stays an append-only [[enumerated]] lineage record —
    never deleted, never a live target."""
    rows = registry_targets("dot_511_nc")
    ids = {t["id"] for t in rows}
    assert "ncdot_cameras" in ids
    assert "ncdot_runneals_mirror" not in ids


# --- fixture emits (point registries) ------------------------------------------


def test_de_fixture_emits_registry_claims() -> None:
    report = _run_fixture("dot_511_de", "de_firstmap.json")
    entities = _entities(report)
    assert len(entities) == 2
    assert all(e["technology"] == "fixed-camera-ptz" for e in entities)
    assert all(e["record_kind"] == "fixed-camera-ptz" for e in entities)
    assert all(e["coordinate_source"] == "geometry" for e in entities)
    assert {c["value"] for c in _by_pred(report, "camera_jurisdiction")} == {"US-DE"}
    # the publishing agency is publisher provenance; the target's operator
    # field mints the operator claim (P32.3 / SIG-TRUST-003).
    operators = {c["value"] for c in _by_pred(report, "camera_operator")}
    assert operators == {"Delaware Department of Transportation"}
    publishers = {c["value"] for c in _by_pred(report, "camera_registry_publisher")}
    assert len(publishers) == 1
    # PERMITNUM/DEVICE_TYPE/MODEL/OWNER are registry fields that carry no
    # camera predicate — none of their values reach a claim.
    for claim in _claims(report):
        for value in (claim.get("value"), claim.get("raw_value")):
            assert "CAM-001" not in str(value)
            assert "PTZ-DOME" not in str(value)
    # technology claims ride every subject (P35.15a).
    assert len(_by_pred(report, "technology")) == 2


def test_vt_fixture_emits_only_cctv_rows() -> None:
    """The capture carries only CCTV rows; every claim's evidence anchors the
    filtered query URL."""
    report = _run_fixture("dot_511_vt", "vt_its.json")
    entities = _entities(report)
    assert len(entities) == 2
    for claim in _claims(report):
        assert "DeviceType%3D%27CCTV%27" in claim["evidence"]["source_url"]
    # the layer's NETWORK_ADDRESS infrastructure field must never emit — not
    # even when it leaks into a capture (defence-in-depth over out_fields).
    for claim in report.claims:
        for value in (claim.get("value"), claim.get("raw_value")):
            assert "10.255.0." not in str(value)


def test_wv_fixture_emits_location_names() -> None:
    report = _run_fixture("dot_511_wv", "wv_cctv.json")
    assert len(_entities(report)) == 2
    names = {c["value"] for c in _by_pred(report, "camera_name")}
    assert names == {"I-79 MM 155 near Morgantown", "I-64 MM 58 near Charleston"}


def test_mi_fixture_uses_the_published_lat_lon_fields() -> None:
    """MiDrive's title-case Lat/Lon attribute pair is the coordinate source;
    the feed-content `Image` field is excluded by name, never emitted."""
    report = _run_fixture("dot_511_mi", "mi_midrive.json")
    entities = _entities(report)
    assert len(entities) == 2
    assert all(e["coordinate_source"] == "fields:Lat/Lon" for e in entities)
    assert all("Image" in e["excluded_fields"] for e in entities)
    for claim in report.claims:
        for value in (claim.get("value"), claim.get("raw_value")):
            assert ".jpg" not in str(value) and "snap/" not in str(value)
    assert {c["value"] for c in _by_pred(report, "camera_roadway")} == {"I-75", "I-94"}
    assert {c["value"] for c in _by_pred(report, "camera_county")} == {"Wayne"}
    assert {c["value"] for c in _by_pred(report, "camera_direction")} == {"NB", "EB"}


def test_nc_fixture_emits_geometry_only_records() -> None:
    report = _run_fixture("dot_511_nc", "nc_ncdot.json")
    assert len(_entities(report)) == 2
    assert not _rejections(report)


def test_municipal_fixtures_emit() -> None:
    """Lincoln + Omaha emit minimal-surface registry records."""
    for source_id, fixture in (
        ("camreg_ne_lincoln_traffic_cameras", "lincoln_traffic.json"),
        ("camreg_omaha_ne_parks_cameras", "omaha_parks.json"),
    ):
        report = _run_fixture(source_id, fixture)
        assert len(_entities(report)) == 2, source_id
        assert {c["value"] for c in _by_pred(report, "camera_jurisdiction")} == {"US-NE"}


def test_hyattsville_fixture_maps_the_programme_fields() -> None:
    report = _run_fixture("camreg_hyattsville_md_cctv_camera_2024", "hyattsville_cctv.json")
    entities = _entities(report)
    assert len(entities) == 2
    assert all(e["technology"] == "fixed-camera-cctv" for e in entities)
    assert {c["value"] for c in _by_pred(report, "camera_name")} == {
        "Jefferson St & 42nd Ave",
        "Rhode Island Ave & 38th St",
    }
    assert {c["value"] for c in _by_pred(report, "camera_county")} == {"Ward 2", "Ward 1"}
    assert {c["value"] for c in _by_pred(report, "camera_status")} == {"Active"}
    assert {c["value"] for c in _by_pred(report, "camera_jurisdiction")} == {"US-MD"}


def test_denver_halo_fixture_rides_the_existing_source() -> None:
    """The HALO layer targets the already-permitted camreg_denver_co source —
    the ticket's licence-match check means no separate source row."""
    report = _run_fixture("camreg_denver_co", "denver_halo.json")
    entities = _entities(report)
    assert len(entities) == 2
    assert all(e["license"] == "LicenseRef-PublicRecord-FactualCompilation" for e in entities)
    assert {c["value"] for c in _by_pred(report, "camera_operator")} == {"Denver Police Department"}
    assert all(e["technology"] == "fixed-camera-ptz" for e in entities)


# --- the area emit (SIG-GEO-003) ------------------------------------------------


def test_seattle_areas_emit_as_polygons_never_points() -> None:
    """SPD pilot-area rows emit ``geometry_kind="area"`` + a WKT location
    claim; no ``camera_latitude``/``camera_longitude`` claims exist."""
    report = _run_fixture("camreg_seattle_wa", "seattle_cctv_areas.json")
    entities = _entities(report)
    assert len(entities) == 2
    for entity in entities:
        assert entity["geometry_kind"] == "area"
        assert entity["latitude"] is None and entity["longitude"] is None
        assert entity["geometry_wkt"].startswith(("POLYGON(", "MULTIPOLYGON("))
        assert entity["ring_count"] >= 1
        # the derived centroid is recorded for positioning — post-tier.
        assert entity["centroid_latitude"] is not None
        assert entity["centroid_longitude"] is not None
    # claim surface: geometry_kind + fixed_asset_location per area; the
    # device-point predicates are absent entirely.
    kinds = _by_pred(report, "geometry_kind")
    assert {c["value"] for c in kinds} == {"area"}
    assert len(kinds) == 2
    locations = _by_pred(report, "fixed_asset_location")
    assert len(locations) == 2
    assert all(str(c["value"]).startswith(("POLYGON(", "MULTIPOLYGON(")) for c in locations)
    assert _by_pred(report, "camera_latitude") == []
    assert _by_pred(report, "camera_longitude") == []
    assert _by_pred(report, "camera_coordinate_source") == []
    assert not _rejections(report)


def test_seattle_area_wkt_and_centroid_are_deterministic() -> None:
    """Replay over the same capture reproduces identical WKT + centroid."""
    first = _run_fixture("camreg_seattle_wa", "seattle_cctv_areas.json")
    second = _run_fixture("camreg_seattle_wa", "seattle_cctv_areas.json")
    wkt_a = sorted(e["geometry_wkt"] for e in _entities(first))
    wkt_b = sorted(e["geometry_wkt"] for e in _entities(second))
    assert wkt_a == wkt_b
    centroids_a = sorted(
        (e["centroid_latitude"], e["centroid_longitude"]) for e in _entities(first)
    )
    centroids_b = sorted(
        (e["centroid_latitude"], e["centroid_longitude"]) for e in _entities(second)
    )
    assert centroids_a == centroids_b


def test_area_geometry_multipolygon_and_holes() -> None:
    """Unit-level: two exterior rings → MULTIPOLYGON; a counter-clockwise
    interior ring groups as a hole under its exterior."""
    exterior_a = [[0, 0], [0, 4], [4, 4], [4, 0], [0, 0]]  # clockwise
    exterior_b = [[10, 10], [10, 12], [12, 12], [12, 10], [10, 10]]  # clockwise
    wkt, clat, clon, ring_count = area_geometry({"rings": [exterior_a, exterior_b]})
    assert wkt.startswith("MULTIPOLYGON(")
    assert ring_count == 2
    # centroid of the larger exterior (the 4x4 square) ≈ its centre
    assert (round(clon, 6), round(clat, 6)) == (2.0, 2.0)
    hole = [[1, 1], [3, 1], [3, 3], [1, 3], [1, 1]]  # counter-clockwise → hole
    wkt2, _, _, ring_count2 = area_geometry({"rings": [exterior_a, hole]})
    assert wkt2.startswith("POLYGON(")
    # `POLYGON((exterior), (hole))` — one polygon, two ring groups.
    assert wkt2.count("(") == 3 and wkt2.count("), (") == 1
    assert ring_count2 == 2


@pytest.mark.parametrize(
    "geometry,reason",
    [
        (None, "missing"),
        ({}, "missing"),
        ({"x": -122.3, "y": 47.6}, "unsupported_geometry"),  # point on an area target
        ({"rings": []}, "missing"),
        ({"rings": [[0, 0], [1, 0], [0, 0]]}, "malformed"),  # <4 positions
        ({"rings": [[[0, 0], [4, 0], [4, 4], [0, 4]]]}, "malformed"),  # unclosed
        ({"rings": [[[0, 0], [0, 4], [4, 4], [4, 95], [0, 0]]]}, "out_of_range"),
        (
            {"rings": [[[0, 0], [0, 4], [4, 4], [4, 0], [0, 0]], [[0, 0], [1, 0], [0, 0]]]},
            "malformed",
        ),  # a degenerate trailing ring fails the whole record
    ],
)
def test_area_geometry_fails_closed(geometry, reason) -> None:
    with pytest.raises(CoordinateRejected) as exc:
        area_geometry(geometry)
    assert exc.value.reason == reason


def test_malformed_area_is_a_recorded_rejection() -> None:
    """A bad polygon row lands as camera_record_rejected — never a claim."""
    doc = {
        "features": [
            {
                "attributes": {"OBJECTID": 9, "Name": "good area"},
                "geometry": {
                    "rings": [
                        [
                            [-122.35, 47.59],
                            [-122.35, 47.60],
                            [-122.31, 47.60],
                            [-122.31, 47.59],
                            [-122.35, 47.59],
                        ]
                    ]
                },
            },
            {
                "attributes": {"OBJECTID": 10, "Name": "unclosed area"},
                "geometry": {
                    "rings": [
                        [
                            [-122.35, 47.59],
                            [-122.35, 47.60],
                            [-122.31, 47.60],
                            [-122.31, 47.59],
                        ]
                    ]
                },
            },
        ]
    }
    targets = [
        t
        for t in live_targets("camreg_seattle_wa")
        if t["id"] == "seattle_police_department_cctv_pilot_areas"
    ]
    url = targets[0]["url"]
    connector, ctx = _ctx("camreg_seattle_wa", targets, {url: _resp(url, json.dumps(doc).encode())})
    report = run(connector, ctx)
    assert len(_entities(report)) == 1
    rejections = _rejections(report)
    assert len(rejections) == 1
    assert rejections[0]["rejection_reason"] == "malformed"
    assert "field_names_present" in rejections[0]


def test_point_feature_on_an_area_target_is_recorded_drift() -> None:
    """A point geometry on the area target is ``unsupported_geometry`` —
    recorded, never silently flattened into a device point."""
    doc = {
        "features": [
            {
                "attributes": {"OBJECTID": 9, "Name": "good area"},
                "geometry": {
                    "rings": [
                        [
                            [-122.35, 47.59],
                            [-122.35, 47.60],
                            [-122.31, 47.60],
                            [-122.31, 47.59],
                            [-122.35, 47.59],
                        ]
                    ]
                },
            },
            {
                "attributes": {"OBJECTID": 10, "Name": "drifted point"},
                "geometry": {"x": -122.33, "y": 47.60},
            },
        ]
    }
    targets = [
        t
        for t in live_targets("camreg_seattle_wa")
        if t["id"] == "seattle_police_department_cctv_pilot_areas"
    ]
    url = targets[0]["url"]
    connector, ctx = _ctx("camreg_seattle_wa", targets, {url: _resp(url, json.dumps(doc).encode())})
    report = run(connector, ctx)
    assert len(_entities(report)) == 1
    reasons = {r["rejection_reason"] for r in _rejections(report)}
    assert reasons == {"unsupported_geometry"}


def test_geometry_kind_membership_is_validated() -> None:
    """A target naming a non-member geometry kind is a registry defect —
    refused at declaration, expansion and emit."""
    assert assert_target_geometry_kind({"id": "x"}) == "point"
    assert assert_target_geometry_kind({"id": "x", "geometry_kind": "area"}) == "area"
    with pytest.raises(GeometryKindNotDeclared):
        assert_target_geometry_kind({"id": "x", "geometry_kind": "sphere"})
    with pytest.raises(GeometryKindNotDeclared):
        expand_registry_rows(
            [
                {
                    "id": "bad",
                    "source_id": "s",
                    "kind": "arcgis_query",
                    "layer_url": "https://example.invalid/0",
                    "state": "US-XX",
                    "agency": "x",
                    "observed_count": 1,
                    "technology": "fixed-camera-cctv",
                    "geometry_kind": "sphere",
                }
            ]
        )


def test_canary_accepts_polygon_geometry() -> None:
    """The structural canary treats `rings` as a valid shape — not x/y drift."""
    good = {"payload": json.loads(_FIX.joinpath("seattle_cctv_areas.json").read_text())}
    assert canary_findings(good) == []
    bad = {"payload": {"features": [{"attributes": {}, "geometry": {"rings": "not-a-list"}}]}}
    assert canary_findings(bad)


# --- the rights gate ------------------------------------------------------------


def test_new_sources_stay_gated() -> None:
    """The eight NEW P36.4 source rows refuse the live gate — the operator's
    OP-26 Wave-B flip under ING-GO-B is the only route to a live fetch."""
    from connectors.runner import live_gate_reasons

    for source_id in GATED_P36_4_SOURCES:
        reasons = live_gate_reasons(source_id)
        assert reasons, f"{source_id} must stay gated"
    # Denver/Seattle remain green under their P26.16 flips — unchanged here.
    assert live_gate_reasons("camreg_denver_co") == []
    assert live_gate_reasons("camreg_seattle_wa") == []


# --- replay / shadow determinism ------------------------------------------------


def test_fixture_replay_and_shadow_are_deterministic() -> None:
    """+0 shadow re-run: replay over the Seattle area capture reproduces an
    identical claim fingerprint (SIG-INGEST-003/019)."""
    targets = [
        t
        for t in live_targets("camreg_seattle_wa")
        if t["id"] == "seattle_police_department_cctv_pilot_areas"
    ]
    url = targets[0]["url"]
    body = _FIX.joinpath("seattle_cctv_areas.json").read_bytes()
    connector, ctx = _ctx("camreg_seattle_wa", targets, {url: _resp(url, body)})
    fixture_report = run(connector, ctx)
    replay_a = replay(connector, ctx, fixture_report.captures)
    replay_b = replay(connector, ctx, fixture_report.captures)
    assert replay_fingerprint(replay_a) == replay_fingerprint(replay_b)
    diff = shadow_replay(connector, ctx, fixture_report.captures, fixture_report.claims)
    assert diff.changed_count == 0, f"shadow diff must be empty: {diff.summary()}"
