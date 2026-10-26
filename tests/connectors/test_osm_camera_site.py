# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `osm` connector as a camera-site ORIGIN (P37.1 / ACQ-17, I8 §4.3).

Pins the new contract over committed fixtures (SIG-PARSE-007):

* the widened selection — ``surveillance:type`` presence + ``highway=speed_camera``
  join ``man_made=surveillance`` as camera-site elements;
* the camera-site claim family on the element's ``osm:<type>/<id>`` subject —
  ``camera_external_ref`` in the declared ``osm.element`` namespace, coordinates
  (node point or way/relation center), ``camera_coordinate_source=osm``,
  ``camera_jurisdiction=unresolved``, org-only ``camera_operator`` twinned into
  an entity-ref, and P35.15b ``technology`` slugs;
* RF-derived provenance coarsened to 3 decimals everywhere it is derived;
* mapper identity never captured — the capture writer refuses ``user``/``uid``
  on an Overpass response, and a fresh ``out body`` capture stores no such keys;
* the national/global two-pass collection — ``out count;`` discovery resolving
  per-area ``out body center qt;`` fetch tiles, reconciled as ContentDrift;
* edit detection by content digest under version-less ``out body`` output.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import pytest
from connectors.net import FetchResult, PoliteFetcher, RobotsResult
from connectors.osm import (
    ODBL_COMPARTMENT,
    ODBL_LICENSE,
    OSM_SOURCE_ID,
    ElementRef,
    OSMConnector,
    area_tiles,
    build_area_count_query,
    build_overpass_query,
    camera_site_technologies,
    coarsened_geometry,
    declared_areas,
    element_content_digest,
    element_in_scope,
    is_camera_site_element,
    physical_asset_rows,
    rf_derived_source,
    snapshot_content_diff,
    tile_count_drift,
    tile_discovery_targets,
    tile_fetch_target,
    us_state_area_selector,
    vocab_version,
)
from connectors.pipeline import run
from connectors.registry import get
from connectors.stages import (
    ContentDrift,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun

_FIX = Path(__file__).parent / "fixtures" / "osm"
_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"
_ENDPOINT = "https://lz4.overpass-api.de/api/interpreter"


def _fixture_bytes(name: str) -> bytes:
    return (_FIX / name).read_bytes()


def _fixture_json(name: str) -> dict[str, Any]:
    return json.loads((_FIX / name).read_text())


class _DictTransport:
    """Serves per-URL fixture bytes — no real network (SIG-INGEST-011)."""

    def __init__(self, bodies: dict[str, bytes]) -> None:
        self._bodies = bodies
        self.requested: list[str] = []

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ROBOTS_ALLOW_ALL)

    def request(self, url: str, *, user_agent: str) -> FetchResult:
        self.requested.append(url)
        body = self._bodies.get(url)
        if body is None:
            return FetchResult(url=url, status=404, body=b"", media_type="text/plain")
        return FetchResult(
            url=url,
            status=200,
            body=body,
            media_type="application/json",
            retrieved_at=datetime(2026, 10, 26, tzinfo=UTC),
        )


def _ctx(targets: list[dict[str, Any]], transport: _DictTransport) -> RunContext:
    fetcher = PoliteFetcher(connector_name="osm", connector_version="1.0.0", transport=transport)
    source = dataclasses.replace(get(OSM_SOURCE_ID), ingestion_permitted=True)
    return RunContext(
        source=source,
        run=IngestRun("osm", "1.0.0", "deadbeef", "r1", vocab_version(), ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": targets},
    )


def _run_fixture(
    name: str,
    url: str = "https://lz4.overpass-api.de/api/interpreter?data=q",
    *,
    kind: str = "overpass",
    extra_targets: list[dict[str, Any]] | None = None,
) -> tuple[Any, RunContext]:
    targets = [{"id": "t1", "url": url, "kind": kind}] + list(extra_targets or [])
    transport = _DictTransport({url: _fixture_bytes(name)})
    ctx = _ctx(targets, transport)
    return run(OSMConnector(), ctx), ctx


def _claims(report: Any, **kw: Any) -> list[dict[str, Any]]:
    return [
        c
        for c in report.claims
        if c.get("record_kind") == "claim" and all(c.get(k) == v for k, v in kw.items())
    ]


# --- selection + camera-site claim family -------------------------------------


def test_camera_site_selection_is_widened() -> None:
    # surveillance:type presence alone (no man_made) and highway=speed_camera
    # are camera-site elements; a cafe is nothing.
    assert is_camera_site_element({"surveillance:type": "ALPR"})
    assert is_camera_site_element({"highway": "speed_camera"})
    assert not is_camera_site_element({"man_made": "surveillance"})
    assert not is_camera_site_element({"amenity": "cafe"})
    assert element_in_scope({"man_made": "surveillance"})
    assert element_in_scope({"surveillance:type": "camera"})
    assert not element_in_scope({"amenity": "cafe"})


def test_body_snapshot_emits_the_camera_site_family() -> None:
    report, _ = _run_fixture("overpass_body_snapshot.json")
    node = {c["predicate_id"]: c for c in _claims(report, osm_id=5001)}
    # external ref carries the declared osm.element namespace + candidate.
    ref = node["camera_external_ref"]
    assert ref["value"] == "osm:node/5001"
    assert ref["id_namespace"] == "osm.element"
    assert ref["candidate_identifier"] == {"scheme": "osm.element", "value": "node/5001"}
    # Coordinates (the node point), coordinate source, unresolved jurisdiction.
    assert node["camera_latitude"]["value"] == pytest.approx(35.4691)
    assert node["camera_longitude"]["value"] == pytest.approx(-97.5182)
    assert node["camera_coordinate_source"]["value"] == "osm"
    assert node["camera_jurisdiction"]["value"] == "unresolved"
    assert node["camera_jurisdiction"]["candidate_identifier"]["scheme"] == "sig.unresolved"
    # Organisation operator + the declared ALPR technology slug.
    assert node["camera_operator"]["value"] == "Flock Safety"
    assert node["technology"]["value"] == "alpr-fixed"


def test_speed_camera_emits_the_ate_subtype_and_site_claims() -> None:
    report, _ = _run_fixture("overpass_body_snapshot.json")
    node = {c["predicate_id"]: c for c in _claims(report, osm_id=5002)}
    # P36.3: highway=speed_camera declares the ATE speed subtype.
    assert node["technology"]["value"] == "ate-speed"
    assert node["camera_external_ref"]["id_namespace"] == "osm.element"
    assert node["camera_latitude"]["value"] == pytest.approx(35.4821)


def test_way_center_is_the_camera_point() -> None:
    report, _ = _run_fixture("overpass_body_snapshot.json")
    way = {c["predicate_id"]: c for c in _claims(report, osm_id=5003)}
    assert way["camera_latitude"]["value"] == pytest.approx(35.5012)
    assert way["camera_longitude"]["value"] == pytest.approx(-97.5501)
    assert way["camera_coordinate_source"]["value"] == "osm"


def test_out_of_scope_elements_emit_nothing() -> None:
    report, _ = _run_fixture("overpass_body_snapshot.json")
    assert not [c for c in report.claims if c.get("osm_id") == 5006]


def test_operator_is_organisation_only() -> None:
    report, _ = _run_fixture("overpass_body_snapshot.json")
    # A person-shaped `operator` tag mints NO camera_operator claim — the
    # verbatim tag stays only on operator_stated.
    assert not _claims(report, osm_id=5005, predicate_id="camera_operator")
    stated = _claims(report, osm_id=5005, predicate_id="operator_stated")
    assert stated and stated[0]["raw_value"] == "John Smith dba Smith Cams"


def test_camera_operator_twins_an_organisation_ref() -> None:
    report, _ = _run_fixture("overpass_body_snapshot.json")
    ops = [
        c
        for c in _claims(report, predicate_id="camera_operator")
        if c.get("object_ref") is not None
    ]
    assert ops, "link() must twin org-shaped camera_operator claims into entity-refs"
    ref = ops[0]["object_ref"]
    assert ref["entity_type"] == "organization"
    assert ref["role"] == "operator"
    # Scoped to the source — never a bare name mint.
    assert ref["scope"] == "src:osm_overpass"


def test_technology_slugs_follow_mobility_and_kind() -> None:
    assert camera_site_technologies({"surveillance:type": "ALPR"}, "fixed") == ("alpr-fixed",)
    assert camera_site_technologies({"surveillance:type": "ALPR"}, "vehicle_mounted") == (
        "alpr-mobile",
    )
    assert camera_site_technologies({"highway": "speed_camera"}, "unknown") == ("ate-speed",)
    # A kind the table cannot specialise for that mobility emits NOTHING —
    # honest absence, never a guessed slug.
    assert camera_site_technologies({"surveillance:type": "camera"}, "airborne") == ()
    assert camera_site_technologies({"surveillance:type": "guard"}, "fixed") == ()


def test_camera_site_claims_stay_in_the_odbl_compartment() -> None:
    report, _ = _run_fixture("overpass_body_snapshot.json")
    site_claims = [
        c
        for c in report.claims
        if c.get("record_kind") == "claim"
        and str(c.get("predicate_id", "")).startswith(("camera_", "technology", "external"))
    ]
    assert site_claims
    assert all(
        c["license"] == ODBL_LICENSE and c["compartment"] == ODBL_COMPARTMENT for c in site_claims
    )


# --- RF-derived coordinate coarsening ------------------------------------------


def test_rf_provenance_detection() -> None:
    assert rf_derived_source({"source": "wifi survey wardrive"}) == "wifi survey wardrive"
    assert rf_derived_source({"survey": "bluetooth scan"}) == "bluetooth scan"
    assert rf_derived_source({"source:survey": "RFID drive-by"}) is not None
    assert rf_derived_source({"source": "field survey"}) is None
    assert rf_derived_source({}) is None


def test_rf_derived_coordinates_are_coarsened_everywhere() -> None:
    report, _ = _run_fixture("overpass_body_snapshot.json")
    node = {c["predicate_id"]: c for c in _claims(report, osm_id=5004)}
    # The emitted point is 3-decimal coarsened — and the coarse marker rides it.
    assert node["camera_latitude"]["value"] == 35.557
    assert node["camera_longitude"]["value"] == -97.442
    marker = node["camera_latitude"]["coordinate_coarsened"]
    assert marker["basis"] == "rf_derived_source"
    # raw_value is the COARSE value too — the precise point never lands in a claim.
    assert node["camera_latitude"]["raw_value"] in ("35.557", 35.557)
    # The ODbL asset row's geometry is coarsened identically.
    rows = [r for r in report.claims if r.get("record_kind") == "asset" and r.get("osm_id") == 5004]
    (asset_row,) = rows
    assert asset_row["geometry"] == {"kind": "point", "lat": 35.557, "lon": -97.442}
    projected = physical_asset_rows(report.claims)
    (row,) = [r for r in projected if r["osm_element_id"] == 5004]
    assert row["geometry"]["lat"] == 35.557
    # Bounds coarsen too — no precise descriptor of any shape survives.
    coarse = coarsened_geometry(
        {
            "kind": "bounds",
            "bounds": {"minlat": 35.12345, "minlon": -97.5, "maxlat": 35.6, "maxlon": -97.1},
        },
        3,
    )
    assert coarse["bounds"]["minlat"] == 35.123


# --- mapper identity: never requested, refused at capture -----------------------


def test_overpass_query_requests_body_never_meta() -> None:
    q = build_overpass_query(bbox=(35.30, -97.85, 35.75, -97.15))
    assert q.endswith("out body center qt;")
    assert "meta" not in q
    # The widened selection: the three selector classes over n/w/r.
    assert '["man_made"="surveillance"]' in q
    assert '["surveillance:type"]' in q
    assert '["highway"="speed_camera"]' in q


def test_capture_refuses_user_uid_before_the_bytes_land() -> None:
    """A nonconforming Overpass response carrying user/uid is ContentDrift — and
    the screened bytes are never written to the capture store (F-406 /
    D-R11-OSMUID-1 / D-P34.49-2)."""
    transport = _DictTransport(
        {
            "https://lz4.overpass-api.de/api/interpreter?data=q": _fixture_bytes(
                "overpass_meta_leak.json"
            )
        }
    )
    ctx = _ctx(
        [
            {
                "id": "t1",
                "url": "https://lz4.overpass-api.de/api/interpreter?data=q",
                "kind": "overpass",
            }
        ],
        transport,
    )
    with pytest.raises(ContentDrift, match="user/uid"):
        run(OSMConnector(), ctx)
    assert not ctx.captures._blobs, "the capture store must hold zero bytes"


def test_fresh_body_capture_stores_no_mapper_identity_keys() -> None:
    """The SIG-INGEST-045e positive half: under `out body` the request never asks
    for mapper identity and the stored capture bytes contain zero user/uid keys."""
    report, ctx = _run_fixture("overpass_body_snapshot.json")
    assert report.captures
    for cap in report.captures:
        body = ctx.captures.get(cap.digest)
        doc = json.loads(body)
        assert not any({"user", "uid"} & set(el) for el in doc.get("elements", [])), (
            "a fresh capture must contain no user/uid keys"
        )


def test_at_rest_screen_reports_zero_f406_hits_on_a_fresh_capture() -> None:
    """D-P34.49-2's verification half: the committed at-rest screen
    (``ops/at_rest_audit.toml``, P34.49 / ADR-185) re-run over the fresh
    ``out body`` capture reports ZERO ``F406-OSM-USERUID`` hits — and it still
    counts the pre-fix meta-shaped fixture (the audit still catches the old
    shape, so the screen itself is proven live)."""
    from evidence.screen import F406_OSM_USERUID, screen_blob
    from ops.at_rest_audit import load_declaration

    decl = load_declaration()
    report, ctx = _run_fixture("overpass_body_snapshot.json")
    for cap in report.captures:
        hits = screen_blob(
            ctx.captures.get(cap.digest),
            source_id=OSM_SOURCE_ID,
            media_type="application/json",
            decl=decl,
        )
        assert F406_OSM_USERUID not in hits, f"capture {cap.digest} flags {hits}"
    # The pre-fix shape still flags — the screen is proven, not muted.
    legacy = screen_blob(
        _fixture_bytes("overpass_meta_leak.json"),
        source_id=OSM_SOURCE_ID,
        media_type="application/json",
        decl=decl,
    )
    assert legacy.get(F406_OSM_USERUID, 0) > 0


def test_history_channel_keeps_its_meta_shaped_documents() -> None:
    """The refusal is scoped to Overpass responses — the osm_element_history
    channel's meta-shaped documents still process (they are not the leak)."""
    report, _ = _run_fixture(
        "element_history_node_1001.json",
        url="https://api.openstreetmap.org/api/0.6/node/1001/history.json",
        kind="history",
    )
    assert _claims(report, predicate_id="first_observed")


# --- the two-pass national/global collection ------------------------------------


def test_declared_area_tiling_covers_the_us_and_the_world() -> None:
    areas = declared_areas()
    # 51 US-state/DC areas first (ISO3166-2), then every declared country —
    # `us` absent: the state areas ARE the US coverage, no element fetched twice.
    us = [a for a in areas if a["tile"].startswith("US-")]
    assert len(us) == 51 and us[0]["tile"] == "US-AL" and "US-DC" in [a["tile"] for a in us]
    countries = [a for a in areas if not a["tile"].startswith("US-")]
    assert len(countries) >= 240 and not any(a["tile"] == "US" for a in areas)
    assert "AU" in [a["tile"] for a in countries]  # the AP-W-046 global/Australia layer
    params = area_tiles()["params"]
    assert params["pace_seconds"] == 30 and params["fetch_timeout"] == 180


def test_tile_discovery_targets_are_count_queries_at_the_reviewed_pace() -> None:
    targets = tile_discovery_targets(_ENDPOINT)
    assert targets, "the discovery pass must emit count targets"
    tiles = [t for t in targets]
    ids = [tile for t in tiles for tile in t["tile_ids"]]
    assert ids == [a["tile"] for a in declared_areas()]
    for t in tiles:
        assert t["kind"] == "overpass_tile_count"
        assert t["rate_limit_per_min"] == 2  # ~30s pacing → 2 req/min
        q = parse_qs(urlparse(t["url"]).query)["data"][0]
        assert q.count("out count;") == len(t["tile_ids"])
        assert "out body" not in q and "meta" not in q


def test_discover_more_resolves_fetch_tiles_from_captured_counts() -> None:
    """The two-pass collection: a captured `out count;` census resolves one
    fetch tile per NON-EMPTY area, carrying its expected_count — an empty area
    resolves to nothing."""
    count_q = build_area_count_query(
        [us_state_area_selector("US-OK"), us_state_area_selector("US-TX")], timeout=90
    )
    count_url = f"{_ENDPOINT}?{urlencode({'data': count_q})}"
    resolved = tile_fetch_target("US-OK", us_state_area_selector("US-OK"), 200, _ENDPOINT)
    tile_url = str(resolved["url"])
    transport = _DictTransport(
        {
            count_url: _fixture_bytes("overpass_count_response.json"),
            tile_url: _fixture_bytes("overpass_tile_us_ok.json"),
        }
    )
    ctx = _ctx(
        [
            {
                "id": "osm_overpass:tile-count:test",
                "kind": "overpass_tile_count",
                "tile_ids": ["US-OK", "US-TX"],
                "url": count_url,
                "endpoint": _ENDPOINT,
            }
        ],
        transport,
    )
    report = run(OSMConnector(), ctx)
    # The resolved fetch tile was fetched through the shared politeness layer.
    assert tile_url in transport.requested
    assert ctx.resolved_targets[tile_url]["expected_count"] == 200
    # The discovery census rows landed as non-claim audit records.
    census = [r for r in report.claims if r.get("record_kind") == "tile_count"]
    assert {r["tile_id"]: r["count_total"] for r in census} == {"US-OK": 200, "US-TX": 0}
    # 199 in-scope elements emitted claims (the cafe element is out of scope).
    assert len({c["osm_id"] for c in report.claims if c.get("record_kind") == "asset"}) == 199
    assert not report.drifted


def test_tile_fetch_reconciles_against_the_discovery_count() -> None:
    """SIG-ENG-042: a fetch tile whose element count disagrees with its
    discovery census beyond the tolerance is a recorded ContentDrift — the
    count reconciles or the run drifts, never a vacuous success."""
    assert tile_count_drift(200, 200) is None
    assert tile_count_drift(200, 198) is None  # inside the floor
    assert tile_count_drift(200, 150) == 50
    count_q = build_area_count_query([us_state_area_selector("US-OK")], timeout=90)
    count_url = f"{_ENDPOINT}?{urlencode({'data': count_q})}"
    resolved = tile_fetch_target("US-OK", us_state_area_selector("US-OK"), 200, _ENDPOINT)
    tile_url = str(resolved["url"])
    # A count census of 200, but the fetch returns only the 6-element slice.
    transport = _DictTransport(
        {
            count_url: _fixture_bytes("overpass_count_response.json"),
            tile_url: _fixture_bytes("overpass_body_snapshot.json"),
        }
    )
    ctx = _ctx(
        [
            {
                "id": "c",
                "kind": "overpass_tile_count",
                "tile_ids": ["US-OK"],
                "url": count_url,
                "endpoint": _ENDPOINT,
            }
        ],
        transport,
    )
    report = run(OSMConnector(), ctx)
    assert any(
        "US-OK" in str(d.get("detail", "")) or "US-OK" in str(d.get("id", ""))
        for d in report.drifted
    )


# --- version-optional interpretation + content-digest edit detection -------------


def test_body_elements_extract_without_a_version() -> None:
    report, _ = _run_fixture("overpass_body_snapshot.json")
    assets = [r for r in report.claims if r.get("record_kind") == "asset"]
    assert assets
    # `out body` carries no version — the row keeps the honest absent, and
    # every claim still emits (version is never claim identity).
    assert all(r["osm_version"] is None for r in assets)
    assert _claims(report, osm_id=5001, predicate_id="camera_external_ref")


def test_element_content_digest_tracks_edits_not_metadata() -> None:
    el = {"type": "node", "id": 1, "lat": 35.0, "lon": -97.0, "tags": {"man_made": "surveillance"}}
    # A tag edit changes the digest; a fetch-time metadata change does not.
    edited = {**el, "tags": {"man_made": "surveillance", "surveillance:type": "ALPR"}}
    moved = {**el, "lat": 35.1}
    assert element_content_digest(el) != element_content_digest(edited)
    assert element_content_digest(el) != element_content_digest(moved)
    # mapper/acquisition metadata is deliberately outside the content digest.
    meta = {**el, "timestamp": "2027-01-01T00:00:00Z", "changeset": 42}
    assert element_content_digest(el) == element_content_digest(meta)


def test_snapshot_content_diff_surfaces_edits() -> None:
    a, b, c = ElementRef("node", 1), ElementRef("node", 2), ElementRef("node", 3)
    d = snapshot_content_diff({a: "x", b: "y"}, {a: "x", b: "z", c: "w"})
    assert d.added == frozenset({c})
    assert d.edited == frozenset({b})
    assert d.persisted == frozenset({a})
    assert d.deleted_from_osm == frozenset()
    assert d.deletion_events(datetime(2026, 10, 26, tzinfo=UTC)) == []


def test_replay_reproduces_zero_new_claims() -> None:
    """Two runs over the same capture produce identical claims modulo the two
    non-deterministic columns (claim_id, sys_period) — replay is +0."""
    r1, _ = _run_fixture("overpass_body_snapshot.json")
    r2, _ = _run_fixture("overpass_body_snapshot.json")

    def key(c: dict[str, Any]) -> str:
        return json.dumps(
            {k: v for k, v in sorted(c.items()) if k not in {"claim_id", "sys_period"}},
            sort_keys=True,
            default=str,
        )

    assert {key(c) for c in r1.claims} == {key(c) for c in r2.claims}
    assert len(r1.claims) == len(r2.claims)
