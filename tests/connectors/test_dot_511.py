# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P26.7 `dot_511` connector — state DOT/511 traffic-camera registries.

Drives the REAL ``pipeline.run`` over a per-URL canned transport (no network,
SIG-INGEST-011): committed ArcGIS-query fixtures stand in for the captured
upstream bytes. Covers: the sourced enumeration registry, per-schema field
aliases, the media blocklist (feed content is never ingested — Part VIII),
coordinate fail-closed + §43.3 sensitivity-tier application, evidence+locator
on every claim, per-source live-gate granularity, drift fail-loud, and
replay/shadow determinism.
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
    PredicateNotAllowed,
    assert_predicate_allowed,
    canary_findings,
    enumerated_outcomes,
    extract_coordinate,
    is_media_field,
    partition_fields,
    predicate_allowlist,
    publishable_coordinate,
    registry_targets,
)
from connectors.live_targets import live_targets
from connectors.net import PoliteFetcher, RobotsResult
from connectors.pipeline import run
from connectors.registry import get
from connectors.replay import replay, replay_fingerprint, shadow_replay
from connectors.runner import live_gate_reasons
from connectors.stages import (
    ContentDrift,
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun

from connectors import dot_511

_FIX = Path(__file__).resolve().parent / "fixtures" / "dot_511"
_RETRIEVED = datetime(2026, 9, 17, tzinfo=UTC)
_ALLOW_ALL = "User-agent: *\nAllow: /\n"

SOURCE_IDS = [
    "dot_511_ky",
    "dot_511_il",
    "dot_511_ut",
    "dot_511_or",
    "dot_511_la",
    "dot_511_ia",
    "dot_511_wa",
    "dot_511_dc",
    "dot_511_ga",
    "dot_511_al",
    "dot_511_mo",
    "dot_511_tx",
    "dot_511_md",
]

#: P26.9 (SOURCES.8) — municipal/transit/non-US camera-registry sources; the
#: first nine are the GL-GATE-06-resolved (flipped) rows, the rest stay gated.
CAMREG_SOURCE_IDS = [
    "camreg_austin_tx",
    "camreg_nola_la",
    "camreg_batonrouge_la",
    "camreg_winnipeg_mb",
    "camreg_act_au",
    "camreg_siouxfalls_sd",
    "camreg_baltimore_md",
    "camreg_ottawa_on",
    "camreg_sheffield_gb",
    "camreg_chicago_il",
    "camreg_calgary_ab",
    "camreg_edmonton_ab",
    "camreg_honolulu_hi",
    "camreg_md_opendata",
    "camreg_york_on",
    "camreg_arlington_va",
    "camreg_seattle_wa",
    "camreg_bellevue_wa",
    "camreg_lexington_ky",
    "camreg_nzta_nz",
    "camreg_qldc_au",
    "camreg_donegal_ie",
    "camreg_hk_hk",
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
    """Run the connector end-to-end over one committed fixture (no network).

    The fixture body answers the target's page-0 query; any further planned
    pages answer an empty ``features`` list (a registry shorter than its planned
    pages is a normal, non-drift outcome).
    """
    targets = live_targets(source_id)
    assert targets, f"{source_id} must resolve registry targets"
    if target_id is not None:
        targets = [t for t in targets if t["id"] == target_id]
    body = _FIX.joinpath(fixture).read_bytes()
    responses = {
        t["url"]: _resp(
            t["url"],
            body
            if t.get("page", 0) == 0
            else (b"[]" if t.get("kind") == "socrata_rows" else b'{"features": []}'),
            retrieved_at=retrieved_at,
        )
        for t in targets
    }
    connector, ctx = _ctx(source_id, targets, responses)
    return run(connector, ctx)


def _claims(report) -> list[Mapping[str, Any]]:
    return [c for c in report.claims if c.get("record_kind") == "claim"]


def _entities(report) -> list[Mapping[str, Any]]:
    return [c for c in report.claims if c.get("record_kind") == "traffic_camera"]


def _rejections(report) -> list[Mapping[str, Any]]:
    return [c for c in report.claims if c.get("record_kind") == "camera_record_rejected"]


# --- the enumeration registry -------------------------------------------------


def test_every_dot_511_source_resolves_a_registry_target() -> None:
    """All 13 state sources have ≥1 verified target row (≥10 states attempted)."""
    for source_id in SOURCE_IDS:
        targets = registry_targets(source_id)
        assert targets, f"{source_id} has no registry target"
        for t in targets:
            assert t["kind"] == "arcgis_query"
            assert t["url"].startswith(t["layer_url"])
            assert "where=1%3D1" in t["url"]
            assert "outSR=4326" in t["url"]
            assert t["state"] and t["agency"]


def test_live_targets_expand_from_the_registry() -> None:
    targets = live_targets("dot_511_wa")
    # the WSDOT-hosted layer (1,705 observed → 2 pages) + the King County layer
    # (125 → 1 page) = 3 page targets over 2 registry rows
    assert len(targets) == 3
    assert {t["state"] for t in targets} == {"WA"}
    assert {t["id"] for t in targets} == {
        "wa_wsdot_travel_cameras",
        "wa_kingcounty_traffic_cameras",
    }


def test_registry_targets_paginate_over_the_transfer_limit() -> None:
    """A >1,000-camera layer expands into ordered page targets (ArcGIS caps a
    query response at maxRecordCount=1,000 on the hosted layers — a single
    unpaged query silently truncates the registry)."""
    targets = live_targets("dot_511_il")  # 2,937 observed → 3 pages
    assert len(targets) == 3
    assert {t["id"] for t in targets} == {"il_idot_gateway_cameras"}
    assert [t["page"] for t in targets] == [0, 1, 2]
    for i, t in enumerate(targets):
        assert f"resultOffset={i * 1000}" in t["url"]
        assert "resultRecordCount=1000" in t["url"]
        assert "orderByFields=OBJECTID" in t["url"]
    # a ≤1,000-row layer stays a single page target
    ky = live_targets("dot_511_ky")
    assert len(ky) == 1 and ky[0]["page"] == 0 and ky[0]["page_count"] == 1


def test_exceeded_transfer_limit_is_content_drift() -> None:
    """A page answering exceededTransferLimit=true means the registry outgrew
    its planned pages — fail loud, never emit a silently truncated registry."""
    doc = {"features": [], "exceededTransferLimit": True}
    targets = live_targets("dot_511_ky")
    url = targets[0]["url"]
    connector, ctx = _ctx("dot_511_ky", targets, {url: _resp(url, json.dumps(doc).encode())})
    with pytest.raises(ContentDrift, match="transfer limit"):
        run(connector, ctx)


def test_transfer_limit_on_a_middle_page_is_not_drift() -> None:
    """exceededTransferLimit on a page BEFORE the last planned one is expected —
    more planned pages follow. Only the last page's flag is drift."""
    page0 = {
        "features": [
            {
                "attributes": {"CAMERAID": "IL-P0", "y": 41.8, "x": -87.6},
                "geometry": {"x": -87.6, "y": 41.8},
            }
        ],
        "exceededTransferLimit": True,
    }
    targets = live_targets("dot_511_il")  # 3 planned pages
    responses = {
        t["url"]: _resp(
            t["url"],
            json.dumps(page0 if t["page"] == 0 else {"features": []}).encode(),
        )
        for t in targets
    }
    connector, ctx = _ctx("dot_511_il", targets, responses)
    report = run(connector, ctx)
    assert len(_entities(report)) == 1
    assert _entities(report)[0]["subject_id"].endswith(":IL-P0")


def test_enumerated_negative_outcomes_are_preserved() -> None:
    """Keyed/refused/unreachable hosts stay recorded — never silently dropped."""
    rows = enumerated_outcomes()
    assert len(rows) >= 20
    statuses = {r["status"] for r in rows}
    assert {
        "keyed_api",
        "access_restricted",
        "robots_unretrievable",
        "spa_shell",
        "not_found",
        "unreachable",
        "unresolved_rights",
    } <= statuses
    # No enumerated row ever resolves to a fetchable target.
    for row in rows:
        assert "source_id" not in row or not row.get("source_id")


def test_enumeration_covers_at_least_ten_states() -> None:
    states = {t["state"] for t in dot_511.target_table()["targets"]}
    assert len(states) >= 10


# --- the media blocklist (Part VIII: registry only, never feed content) -------


def test_media_field_names_and_patterns() -> None:
    for name in (
        "snapshot",
        "SnapShot",
        "ImageURL",
        "VideoUrl",
        "hlsurl",
        "CCTVPublicURL",
        "ImgPath",
        "URL1",
        "attributes_videoId",
        "ThumbFileLoc",
        "ImageFileLoc",
        "STREAM_ERROR",
        "url",
    ):
        assert is_media_field(name), name
    for name in ("latitude", "Route", "name", "OBJECTID", "CameraTitle", "county"):
        assert not is_media_field(name), name


def test_partition_fields_drops_media_values() -> None:
    fields, excluded = partition_fields(
        {"id": "cam1", "latitude": 1.0, "snapshot": "https://x/y.jpg", "ImageURL": "z"}
    )
    assert fields == {"id": "cam1", "latitude": 1.0}
    assert excluded == ["ImageURL", "snapshot"]


def test_no_claim_carries_a_media_field_value() -> None:
    """The strongest Part VIII check: no emitted value is a feed-content URL."""
    report = _run_fixture("dot_511_ky", "ky_kytc.json")
    assert _entities(report)
    for claim in report.claims:
        for value in (claim.get("value"), claim.get("raw_value")):
            text = str(value)
            assert ".jpg" not in text and "snap/" not in text
    # The excluded media field NAMES are recorded on the entity, never values.
    entity = _entities(report)[0]
    assert "snapshot" in entity["excluded_fields"]


# --- coordinates + sensitivity policy (fail closed) ---------------------------


def test_extract_coordinate_prefers_explicit_fields() -> None:
    lat, lon, source = extract_coordinate(
        {"latitude": "36.5", "longitude": -86.4}, {"x": -99.0, "y": 1.0}
    )
    assert (lat, lon) == (36.5, -86.4)
    assert source == "fields:latitude/longitude"


def test_extract_coordinate_geometry_fallback() -> None:
    lat, lon, source = extract_coordinate({}, {"x": -122.33, "y": 47.62})
    assert (lat, lon, source) == (47.62, -122.33, "geometry")


@pytest.mark.parametrize(
    "fields,geometry,reason",
    [
        ({}, None, "missing"),
        ({"latitude": "abc", "longitude": "1"}, None, "malformed"),
        ({"latitude": 95.0, "longitude": 0.0}, None, "out_of_range"),
        ({"latitude": 0.0, "longitude": 190.0}, None, "out_of_range"),
    ],
)
def test_extract_coordinate_fails_closed(fields, geometry, reason) -> None:
    with pytest.raises(CoordinateRejected) as exc:
        extract_coordinate(fields, geometry)
    assert exc.value.reason == reason


def test_publishable_coordinate_applies_the_sensitivity_tier() -> None:
    """C1 (public hardware on public ROW, operator-published) → tier 0 exact."""
    lat, lon, tier = publishable_coordinate(36.123456, -86.654321, "C1")
    assert (lat, lon) == (36.123456, -86.654321)
    assert tier == 0


def test_publishable_coordinate_tier3_refuses_geometry() -> None:
    """A class publishing jurisdiction-only yields NO coordinate claim."""
    with pytest.raises(CoordinateRejected) as exc:
        publishable_coordinate(36.1, -86.4, "C3")
    assert exc.value.reason == "tier_forbids_geometry"


def test_emitted_coordinates_pass_the_policy_check() -> None:
    """Every emitted coordinate is inside valid ranges at its published tier."""
    report = _run_fixture("dot_511_il", "il_idot.json")
    lats = {c["value"] for c in _claims(report) if c["predicate_id"] == "camera_latitude"}
    lons = {c["value"] for c in _claims(report) if c["predicate_id"] == "camera_longitude"}
    assert lats and lons
    assert all(-90.0 <= lat <= 90.0 for lat in lats)
    assert all(-180.0 <= lon <= 180.0 for lon in lons)
    entities = _entities(report)
    assert all(e["sensitivity_class"] == "C1" and e["geo_tier"] == 0 for e in entities)


# --- end-to-end over the real pipeline -----------------------------------------


def test_ky_fixture_emits_camera_claims_with_evidence_and_locators() -> None:
    report = _run_fixture("dot_511_ky", "ky_kytc.json")
    entities = _entities(report)
    assert len(entities) == 3
    claims = _claims(report)
    by_pred: dict[str, list[Mapping[str, Any]]] = {}
    for c in claims:
        by_pred.setdefault(c["predicate_id"], []).append(c)
    # location + roadway + jurisdiction + operator + identity, per camera
    assert len(by_pred["camera_latitude"]) == 3
    assert len(by_pred["camera_longitude"]) == 3
    assert len(by_pred["camera_roadway"]) == 3
    assert len(by_pred["camera_jurisdiction"]) == 3
    assert len(by_pred["camera_operator"]) == 3
    assert len(by_pred["camera_external_ref"]) == 3
    assert {c["value"] for c in by_pred["camera_roadway"]} == {"I-65", "I-64", "US-27"}
    assert {c["value"] for c in by_pred["camera_jurisdiction"]} == {"KY"}
    # candidate identifiers, never resolutions (SIG-INGEST-034)
    assert by_pred["camera_jurisdiction"][0]["candidate_identifier"] == {
        "scheme": "us.state_abbr",
        "value": "KY",
    }
    assert by_pred["camera_external_ref"][0]["candidate_identifier"]["scheme"] == (
        "dot511.camera_ref"
    )
    # every claim carries evidence + a row locator (SIG-PARSE-003)
    for claim in claims:
        evidence = claim["evidence"]
        assert evidence["extraction_method"] == "arcgis_feature_json"
        assert evidence["locator"]["kind"] == "row"
        assert evidence["locator"]["row"] in (0, 1, 2)
        assert evidence["source_url"].startswith("https://services2.arcgis.com/CcI36Pduqd0OR4W9/")
    # subject ids are source+target+ref scoped and stable
    assert entities[0]["subject_id"] == (
        "traffic_camera:dot_511_ky:ky_kytc_traffic_cameras:KYTC-0001"
    )


def test_claim_digests_stable_across_retrieval_times() -> None:
    """P26.8 regression (found live on the hosted re-run): the claim evidence
    dict carried the capture's ``retrieved_at`` — a volatile per-run timestamp
    — so ``content_digest`` churned and a re-run over an unchanged registry
    minted a duplicate claim set. The retrieval timestamp is durable on
    ``evidence_capture.retrieved_at`` + the run row's fetch record; it must
    never reach claim identity (the P26.6 ``capture_digest`` precedent)."""
    from db.claim_sink import content_digest

    first = _run_fixture("dot_511_ky", "ky_kytc.json")
    second = _run_fixture(
        "dot_511_ky", "ky_kytc.json", retrieved_at=datetime(2026, 10, 24, tzinfo=UTC)
    )
    digests_a = sorted(content_digest(c) for c in _claims(first))
    digests_b = sorted(content_digest(c) for c in _claims(second))
    assert digests_a == digests_b and digests_a
    for claim in _claims(first):
        assert "retrieved_date" not in claim["evidence"]


def test_il_fixture_xy_field_aliases() -> None:
    """IL's x/y attribute fields resolve as coordinates; CC-BY-SA-2.0 stamps."""
    report = _run_fixture("dot_511_il", "il_idot.json")
    entities = _entities(report)
    assert len(entities) == 2
    assert all(e["license"] == "CC-BY-SA-2.0" for e in entities)
    assert all(e["coordinate_source"] == "fields:y/x" for e in entities)


def test_wa_fixture_geometry_only_coordinates() -> None:
    """WSDOT's geometry-only layer resolves coordinates from point geometry."""
    report = _run_fixture("dot_511_wa", "wa_wsdot.json", target_id="wa_wsdot_travel_cameras")
    entities = _entities(report)
    assert len(entities) == 2
    assert all(e["coordinate_source"] == "geometry" for e in entities)
    claims = _claims(report)
    assert {c["value"] for c in claims if c["predicate_id"] == "camera_direction"} == {"N", "E"}


def test_or_fixture_attributes_prefixed_aliases() -> None:
    report = _run_fixture("dot_511_or", "or_tripcheck.json")
    entities = _entities(report)
    assert len(entities) == 1
    entity = entities[0]
    assert entity["subject_id"].endswith(":CAM-OR-7001")
    assert entity["coordinate_source"] == "fields:attributes_latitude/attributes_longitude"
    assert set(entity["excluded_fields"]) >= {
        "attributes_filename",
        "attributes_videoId",
        "attributes_publishedImageId",
    }


def test_partial_rejections_are_recorded_not_dropped() -> None:
    """A mixed capture: the good camera emits; the bad ones are recorded rows."""
    report = _run_fixture("dot_511_ky", "mixed_rejections.json")
    assert len(_entities(report)) == 1
    rejections = _rejections(report)
    reasons = {r["rejection_reason"] for r in rejections}
    assert reasons == {"missing", "out_of_range", "malformed"}
    assert len(rejections) == 4
    assert all("field_names_present" in r for r in rejections)


# --- drift: fail loud ----------------------------------------------------------


def test_arcgis_error_envelope_is_content_drift() -> None:
    targets = live_targets("dot_511_ky")
    url = targets[0]["url"]
    body = _FIX.joinpath("error_envelope.json").read_bytes()
    connector, ctx = _ctx("dot_511_ky", targets, {url: _resp(url, body)})
    with pytest.raises(ContentDrift, match="error envelope"):
        run(connector, ctx)


def test_non_json_capture_is_content_drift() -> None:
    targets = live_targets("dot_511_ky")
    url = targets[0]["url"]
    connector, ctx = _ctx("dot_511_ky", targets, {url: _resp(url, b"<html>502 Bad Gateway</html>")})
    with pytest.raises(ContentDrift, match="non-JSON"):
        run(connector, ctx)


def test_missing_features_list_is_content_drift() -> None:
    targets = live_targets("dot_511_ky")
    url = targets[0]["url"]
    connector, ctx = _ctx("dot_511_ky", targets, {url: _resp(url, b'{"results": []}')})
    with pytest.raises(ContentDrift, match="no 'features'"):
        run(connector, ctx)


def test_all_rejected_records_is_content_drift() -> None:
    """A 100%-rejection feed is a schema change, not an empty registry."""
    doc = {"features": [{"attributes": {"name": "no id, no coords"}, "geometry": None}]}
    targets = live_targets("dot_511_ky")
    url = targets[0]["url"]
    connector, ctx = _ctx("dot_511_ky", targets, {url: _resp(url, json.dumps(doc).encode())})
    with pytest.raises(ContentDrift, match="every camera record failed"):
        run(connector, ctx)


def test_canary_findings_clean_and_drifted() -> None:
    good = {"payload": json.loads(_FIX.joinpath("ky_kytc.json").read_text())}
    assert canary_findings(good) == []
    bad = {"payload": {"features": [{"attributes": None}, {"attributes": {}, "geometry": "x"}]}}
    findings = canary_findings(bad)
    assert len(findings) >= 2


# --- predicate allowlist (SIG-INGEST-033) --------------------------------------


def test_predicate_allowlist_refuses_feed_content() -> None:
    for pred in ("camera_image", "camera_video", "feed_url", "deployment_exists"):
        with pytest.raises(PredicateNotAllowed):
            assert_predicate_allowed(pred)
    assert "traffic_camera" in predicate_allowlist()


def test_allowlisted_predicates_are_the_whole_writeset() -> None:
    report = _run_fixture("dot_511_ky", "ky_kytc.json")
    for claim in report.claims:
        assert claim["predicate_id"] in predicate_allowlist()


# --- rights granularity + the live gate ----------------------------------------


def test_resolved_sources_are_green_gated_sources_refuse() -> None:
    green = {
        "dot_511_ky",
        "dot_511_il",
        "dot_511_ut",
        "dot_511_or",
        "dot_511_ia",
        "dot_511_wa",
        "dot_511_dc",
        "dot_511_mo",
    }
    gated = set(SOURCE_IDS) - green
    for source_id in green:
        assert live_gate_reasons(source_id) == [], f"{source_id} should be green"
    for source_id in sorted(gated):
        assert live_gate_reasons(source_id), f"{source_id} must stay gated"


# --- replay / shadow determinism (SIG-INGEST-003/019) ---------------------------


def test_replay_and_shadow_are_deterministic() -> None:
    targets = live_targets("dot_511_ky")
    url = targets[0]["url"]
    body = _FIX.joinpath("ky_kytc.json").read_bytes()
    connector, ctx = _ctx("dot_511_ky", targets, {url: _resp(url, body)})
    fixture_report = run(connector, ctx)
    replay_a = replay(connector, ctx, fixture_report.captures)
    replay_b = replay(connector, ctx, fixture_report.captures)
    assert replay_fingerprint(replay_a) == replay_fingerprint(replay_b)
    diff = shadow_replay(connector, ctx, fixture_report.captures, fixture_report.claims)
    assert diff.changed_count == 0, f"shadow diff must be empty: {diff.summary()}"


# ============================================================================
# P26.9 (SOURCES.8) — municipal / transit / non-US camera registries
# ============================================================================


def test_every_camreg_source_resolves_a_registry_target() -> None:
    """All 23 municipal/transit/non-US sources have ≥1 verified target row —
    ArcGIS layers AND Socrata datasets, gated rows included (the endpoint is
    real; the gate is what stops the fetch)."""
    for source_id in CAMREG_SOURCE_IDS:
        targets = registry_targets(source_id)
        assert targets, f"{source_id} has no registry target"
        for t in targets:
            assert t["kind"] in ("arcgis_query", "socrata_rows")
            assert t["url"].startswith(t["layer_url"])
            assert t["state"] and t["agency"]
            assert t["jurisdiction_scheme"]


def test_socrata_targets_expand_to_paged_resource_urls() -> None:
    targets = live_targets("camreg_austin_tx")
    assert len(targets) == 1  # 1,005 observed < 5,000-page
    t = targets[0]
    assert t["kind"] == "socrata_rows"
    assert t["url"].startswith("https://datahub.austintexas.gov/resource/b4k4-adkb.json?")
    assert "%24select=%2A%2C%3Aid" in t["url"]  # $select=*,:id
    assert "%24order=%3Aid" in t["url"]  # $order=:id
    assert "%24limit=5000" in t["url"]
    assert "%24offset=0" in t["url"]
    assert t["jurisdiction_scheme"] == "us.state_abbr"


def test_iso_jurisdiction_schemes_are_carried() -> None:
    """Non-US registries carry ISO-3166 candidate schemes, never us.state_abbr."""
    assert registry_targets("camreg_winnipeg_mb")[0]["jurisdiction_scheme"] == "iso.3166_2"
    assert registry_targets("camreg_act_au")[0]["jurisdiction_scheme"] == "iso.3166_2"
    assert registry_targets("camreg_ottawa_on")[0]["jurisdiction_scheme"] == "iso.3166_2"
    assert registry_targets("camreg_sheffield_gb")[0]["jurisdiction_scheme"] == "iso.3166_2"
    assert registry_targets("camreg_nzta_nz")[0]["jurisdiction_scheme"] == "iso.3166_1_alpha2"


def test_socrata_error_envelope_is_content_drift() -> None:
    targets = live_targets("camreg_austin_tx")
    url = targets[0]["url"]
    body = json.dumps({"code": "dataset.missing", "error": True, "message": "Not found"}).encode()
    connector, ctx = _ctx("camreg_austin_tx", targets, {url: _resp(url, body)})
    with pytest.raises(ContentDrift, match="error envelope"):
        run(connector, ctx)


def test_socrata_non_json_is_content_drift() -> None:
    targets = live_targets("camreg_austin_tx")
    url = targets[0]["url"]
    connector, ctx = _ctx("camreg_austin_tx", targets, {url: _resp(url, b"<html>403</html>")})
    with pytest.raises(ContentDrift, match="non-JSON"):
        run(connector, ctx)


def test_socrata_non_array_payload_is_content_drift() -> None:
    targets = live_targets("camreg_austin_tx")
    url = targets[0]["url"]
    connector, ctx = _ctx("camreg_austin_tx", targets, {url: _resp(url, b'{"results": []}')})
    with pytest.raises(ContentDrift, match="error envelope"):
        run(connector, ctx)


def test_socrata_full_last_page_is_content_drift() -> None:
    """A page returning exactly $limit rows on the last planned page is the
    Socrata analogue of exceededTransferLimit — fail loud, never truncate."""
    rows = [{"id": str(i), "latitude": 30.2, "longitude": -97.7} for i in range(5000)]
    targets = live_targets("camreg_austin_tx")  # 1 planned page
    url = targets[0]["url"]
    connector, ctx = _ctx("camreg_austin_tx", targets, {url: _resp(url, json.dumps(rows).encode())})
    with pytest.raises(ContentDrift, match="outgrown its planned pages"):
        run(connector, ctx)


def test_socrata_media_fields_are_dropped() -> None:
    """image_view / camera_url / iframe values never reach a claim or record."""
    doc = [
        {
            "id": "9",
            "latitude": 30.1,
            "longitude": -90.8,
            "image_view": "https://511la.org/map/Cctv/x",
            "camera_url": "https://cam.example/9.jpg",
            "iframe": "<iframe src='https://cam.example/e'></iframe>",
        }
    ]
    targets = live_targets("camreg_batonrouge_la")
    url = targets[0]["url"]
    connector, ctx = _ctx(
        "camreg_batonrouge_la", targets, {url: _resp(url, json.dumps(doc).encode())}
    )
    report = run(connector, ctx)
    entity = _entities(report)[0]
    assert set(entity["excluded_fields"]) == {"camera_url", "iframe", "image_view"}
    for claim in report.claims:
        text = str(claim.get("value")) + str(claim.get("raw_value"))
        assert "511la.org" not in text and "cam.example" not in text


def test_austin_socrata_fixture_emits_camera_claims() -> None:
    report = _run_fixture("camreg_austin_tx", "austin_socrata.json")
    entities = _entities(report)
    assert len(entities) == 2
    claims = _claims(report)
    by_pred: dict[str, list[Mapping[str, Any]]] = {}
    for c in claims:
        by_pred.setdefault(c["predicate_id"], []).append(c)
    assert len(by_pred["camera_latitude"]) == 2
    assert len(by_pred["camera_longitude"]) == 2
    assert len(by_pred["camera_jurisdiction"]) == 2
    assert {c["value"] for c in by_pred["camera_jurisdiction"]} == {"TX"}
    assert by_pred["camera_jurisdiction"][0]["candidate_identifier"] == {
        "scheme": "us.state_abbr",
        "value": "TX",
    }
    # GeoJSON point under `location` resolves as geometry-source coordinates
    entity = entities[0]
    assert entity["coordinate_source"] == "geometry"
    assert entity["sensitivity_class"] == "C1" and entity["geo_tier"] == 0
    assert "screenshot_address" in entity["excluded_fields"]
    for claim in claims:
        assert claim["evidence"]["extraction_method"] == "socrata_rows_json"
        assert claim["evidence"]["locator"]["kind"] == "row"
    assert entity["subject_id"].startswith(
        "traffic_camera:camreg_austin_tx:austin_tx_traffic_cameras:"
    )


def test_nola_socrata_fixture_field_aliases() -> None:
    """NOLA's lowercase/other-named fields resolve through the P26.9 aliases."""
    report = _run_fixture("camreg_nola_la", "nola_socrata.json")
    entities = _entities(report)
    assert len(entities) == 2
    claims = _claims(report)
    assert {c["value"] for c in claims if c["predicate_id"] == "camera_external_ref"} == {
        "NO179",
        "NO173",
    }
    names = {c["value"] for c in claims if c["predicate_id"] == "camera_name"}
    assert names == {"5200 Bullard Ave", "2400 Orleans Ave"}
    dirs = {c["value"] for c in claims if c["predicate_id"] == "camera_direction"}
    assert dirs == {"SB", "WB"}
    lats = {c["value"] for c in claims if c["predicate_id"] == "camera_latitude"}
    assert lats == {30.031396000519, 29.968552731539}


def test_iso3166_jurisdiction_scheme_reaches_the_claim() -> None:
    """A CA-MB target stamps iso.3166_2 on the camera_jurisdiction candidate."""
    doc = [
        {
            "inventory_item_id": "2242",
            "camera_description": "Fort & York",
            "latitude": "49.88996219",
            "longitude": "-97.13725258",
            "location": {"type": "Point", "coordinates": [-97.13725258, 49.88996219]},
            ":id": "row-5krg.u358.f8tv",
        }
    ]
    targets = live_targets("camreg_winnipeg_mb")
    url = targets[0]["url"]
    connector, ctx = _ctx(
        "camreg_winnipeg_mb", targets, {url: _resp(url, json.dumps(doc).encode())}
    )
    report = run(connector, ctx)
    jx = [c for c in _claims(report) if c["predicate_id"] == "camera_jurisdiction"][0]
    assert jx["candidate_identifier"] == {"scheme": "iso.3166_2", "value": "CA-MB"}
    assert jx["value"] == "CA-MB"
    name = [c for c in _claims(report) if c["predicate_id"] == "camera_name"][0]
    assert name["value"] == "Fort & York"


def test_camreg_green_sources_pass_gated_ones_refuse() -> None:
    green = {
        "camreg_austin_tx",
        "camreg_nola_la",
        "camreg_batonrouge_la",
        "camreg_winnipeg_mb",
        "camreg_act_au",
        "camreg_siouxfalls_sd",
        "camreg_baltimore_md",
        "camreg_ottawa_on",
        "camreg_sheffield_gb",
    }
    gated = set(CAMREG_SOURCE_IDS) - green
    for source_id in green:
        assert live_gate_reasons(source_id) == [], f"{source_id} should be green"
    for source_id in sorted(gated):
        assert live_gate_reasons(source_id), f"{source_id} must stay gated"


def test_enumerated_p26_9_negative_outcomes_are_preserved() -> None:
    rows = {r["id"]: r for r in enumerated_outcomes()}
    assert "nyc_tmc_cameras" in rows
    assert "tfl_jamcams" in rows
    assert "nsw_live_traffic_cameras" in rows
    assert "qld_qldtraffic_api" in rows
    statuses = {r["status"] for r in rows.values()}
    assert {"keyed_api", "unresolved_rights", "access_restricted", "not_found"} <= statuses


def test_socrata_replay_and_shadow_are_deterministic() -> None:
    targets = live_targets("camreg_austin_tx")
    url = targets[0]["url"]
    body = _FIX.joinpath("austin_socrata.json").read_bytes()
    connector, ctx = _ctx("camreg_austin_tx", targets, {url: _resp(url, body)})
    fixture_report = run(connector, ctx)
    replay_a = replay(connector, ctx, fixture_report.captures)
    replay_b = replay(connector, ctx, fixture_report.captures)
    assert replay_fingerprint(replay_a) == replay_fingerprint(replay_b)
    diff = shadow_replay(connector, ctx, fixture_report.captures, fixture_report.claims)
    assert diff.changed_count == 0, f"shadow diff must be empty: {diff.summary()}"
