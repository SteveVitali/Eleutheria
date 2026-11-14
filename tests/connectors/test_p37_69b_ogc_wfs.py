# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.69b (R11-ACQ-23b, I7 N1–N21 `a` / RB-06 `a`) — the OGC WFS family.

Four gated seats: Runnymede's GeoServer layer and the Clackmannanshire
Cadcorp layer wire declared ``wfs_capabilities`` + ``wfs_get_feature``
target rows (the records name the feature type); South Kesteven's statmap
INSPIRE seat records no typename, so its capabilities row carries
``feature_type_selector = "sole"`` and the SERVED document resolves the
bounded GetFeature follow-on inside the run (``discover_more`` — never a
guessed name); Ipswich stays ``[[enumerated]]`` — the committed record
evidences WMS only (D-P37.69b-1) and keeps its ``promote`` disposition.
Every seat stays ``ingestion_permitted=false`` — the operator's OP-26
Wave-D flip under ING-GO-D is the only route to live. Replay runs over the
committed synthetic fixtures (fixtures/p37_69b/SOURCES.md) with no network.
"""

import dataclasses
import json
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
from connectors.live_targets import live_targets
from connectors.net import PoliteFetcher, RateLimiter, RobotsResult
from connectors.ogc_wfs import (
    OgcWfsConnector,
    capabilities_url,
    get_feature_url,
)
from connectors.ogc_wfs import (
    enumerated_rows as wfs_enumerated,
)
from connectors.ogc_wfs import (
    expanded_targets as wfs_expanded_targets,
)
from connectors.ogc_wfs import (
    targets_for as wfs_targets_for,
)
from connectors.ogc_wfs import (
    vocab as wfs_vocab,
)
from connectors.pipeline import run
from connectors.registry import CompactStatus, get
from connectors.runner import CONNECTOR_FOR_SOURCE, live_gate_reasons
from connectors.stages import (
    ContentDrift,
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun

_ALLOW_ALL = "User-agent: *\nAllow: /\n"


class MapTransport:
    """Per-URL canned responses + permissive robots — no real network."""

    def __init__(self, responses: Mapping[str, FetchResult]) -> None:
        self._responses = dict(responses)
        self.request_log: list[str] = []

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ALLOW_ALL, status=200)

    def request(
        self,
        url: str,
        *,
        user_agent: str,
        headers: Mapping[str, str] | None = None,
        body: bytes | None = None,
    ) -> FetchResult:
        self.request_log.append(url)
        if url in self._responses:
            return self._responses[url]
        return FetchResult(url=url, status=404, body=b"", media_type="application/octet-stream")


_FIX = Path(__file__).parent / "fixtures" / "p37_69b"

_RUNNY = "camreg_gb_eng_runny_cctv_cameras"
_SKDC = "camreg_gb_eng_south_skdc_cctv"
_CLACK = "camreg_gb_sct_clackmannanshire_cctv"
_IPSWICH = "camreg_gb_eng_ipswich_cctv_camera"

_WIRED = {_RUNNY, _SKDC, _CLACK}
_ENUMERATED = {_IPSWICH}

#: The SKDC seat's sole-served feature type in the committed synthetic
#: capabilities fixture — the resolved GetFeature follows the document.
_SKDC_TYPENAME = "SKDC_INSPIRE_WFS:CCTV"


def _fixture_for_url(url: str) -> tuple[str, str]:
    """(fixture filename, media type) for an expanded target URL."""
    if "maps.runnymede.gov.uk" in url:
        return (
            "capabilities_geoserver.xml" if "GetCapabilities" in url else "getfeature_geoserver.xml"
        ), "application/gml+xml"
    if "southkesteven.statmap.co.uk" in url:
        if "GetCapabilities" in url:
            return "capabilities_statmap.xml", "application/gml+xml"
        return "getfeature_statmap.xml", "application/gml+xml"
    if "clacks.cloud.cadcorp.com" in url:
        if "GetCapabilities" in url:
            return "capabilities_cadcorp.xml", "application/gml+xml"
        return "getfeature_cadcorp.xml", "application/gml+xml"
    raise AssertionError(f"no fixture declared for {url}")


def _responses_for(source_id: str) -> dict[str, FetchResult]:
    responses: dict[str, FetchResult] = {}
    urls = [str(t["url"]) for t in live_targets(source_id)]
    if source_id == _SKDC:
        # The selector-resolved GetFeature target lands inside the run —
        # its URL is deterministic (the served document names the type).
        urls.append(
            get_feature_url(
                {
                    "id": "resolved",
                    "service_url": "https://southkesteven.statmap.co.uk/map/wfs.svc/SKDC_INSPIRE_WFS",
                    "typename": _SKDC_TYPENAME,
                    "count": 500,
                }
            )
        )
    for url in urls:
        fixture, media = _fixture_for_url(url)
        responses[url] = FetchResult(
            url=url, status=200, body=(_FIX / fixture).read_bytes(), media_type=media
        )
    return responses


def _run_fixture(source_id: str, *, bodies: Mapping[str, bytes] | None = None):
    """Run the source's connector over its committed fixtures (no network)."""
    responses = _responses_for(source_id)
    for url, body in (bodies or {}).items():
        media = next(
            (r.media_type for u, r in responses.items() if u == url),
            "application/gml+xml",
        )
        responses[url] = FetchResult(url=url, status=200, body=body, media_type=media)
    targets = [dict(t) for t in live_targets(source_id)]
    assert targets, f"{source_id} resolves no reviewed targets"
    connector = OgcWfsConnector()
    transport = MapTransport(responses)
    source = dataclasses.replace(
        get(source_id),
        ingestion_permitted=True,
        compact_status=CompactStatus.PUBLIC_TERMS_ONLY,
    )
    fetcher = PoliteFetcher(
        connector_name=connector.name,
        connector_version=connector.version,
        transport=transport,
        rate_limiter=RateLimiter(sleep=lambda s: None),
    )
    ctx = RunContext(
        source=source,
        run=IngestRun(connector.name, connector.version, "test", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": targets},
    )
    return run(connector, ctx), transport


def _claims(report: Any) -> list[dict[str, Any]]:
    return [dict(c) for c in report.claims if c.get("record_kind") == "claim"]


def _subjects(report: Any, record_kind: str) -> list[dict[str, Any]]:
    return [dict(r) for r in report.claims if r.get("record_kind") == record_kind]


def _url_for(source_id: str, needle: str) -> str:
    return next(u for u in (str(t["url"]) for t in live_targets(source_id)) if needle in u)


# --- registration, routing, gating (HG-03 / OP-26) ----------------------------


def test_the_four_seats_are_registered_routed_and_gated() -> None:
    for source_id in _WIRED:
        assert CONNECTOR_FOR_SOURCE[source_id] == "ogc_wfs", source_id
        rec = get(source_id)
        assert rec.ingestion_permitted is False, source_id
        assert live_gate_reasons(rec), f"{source_id} reports no live-gate reason"
    for source_id in _ENUMERATED:
        assert source_id not in CONNECTOR_FOR_SOURCE, source_id
        assert get(source_id).ingestion_permitted is False, source_id


def test_the_dispositions_table_carries_only_the_enumerated_promote_row() -> None:
    # P25.6 exactly-once: a connector-mapped source carries NO disposition
    # row; the ONE enumerated seat keeps its `promote` row until
    # D-P37.69b-1's endpoint preflight wires (or retires) its lane.
    disp = tomllib.loads(Path("connectors/src/connectors/data/live_dispositions.toml").read_text())
    seats = disp.get("sources") or {}
    for source_id in _WIRED:
        assert source_id not in seats, source_id
    for source_id in _ENUMERATED:
        assert seats[source_id]["disposition"] == "promote", source_id


def test_the_enumerated_row_records_the_wms_only_seat() -> None:
    enum = {r["source_id"]: r for r in wfs_enumerated()}
    assert _IPSWICH in enum
    assert enum[_IPSWICH]["status"] == "endpoint_preflight_deferred"
    assert live_targets(_IPSWICH) == []


# --- target expansion + the host gate -----------------------------------------


def test_every_expanded_target_sits_on_the_committed_host_set() -> None:
    hosts = set(wfs_vocab()["hosts"])
    for row in (r for s in _WIRED for r in wfs_expanded_targets(s)):
        assert urlsplit(str(row["url"])).netloc.lower() in hosts, row["url"]
        assert row["url"].startswith("https://")


def test_the_target_kinds_match_their_seats() -> None:
    assert {t["kind"] for t in wfs_targets_for(_RUNNY)} == {
        "wfs_capabilities",
        "wfs_get_feature",
    }
    assert {t["kind"] for t in wfs_targets_for(_SKDC)} == {"wfs_capabilities"}
    assert {t["kind"] for t in wfs_targets_for(_CLACK)} == {
        "wfs_capabilities",
        "wfs_get_feature",
    }
    assert wfs_targets_for(_IPSWICH) == []


def test_the_expanded_urls_carry_the_declared_request_shape() -> None:
    caps = _url_for(_RUNNY, "GetCapabilities")
    assert "service=WFS" in caps and "request=GetCapabilities" in caps
    page = _url_for(_RUNNY, "GetFeature")
    assert "typenames=community%3Acctv_cameras" in page
    assert "count=500" in page and "version=2.0.0" in page
    clack_page = _url_for(_CLACK, "GetFeature")
    assert "typenames=ns%3Acctv_cameras" in clack_page
    # SKDC expands only its capabilities row — the feature page resolves in-run
    skdc = [str(t["url"]) for t in wfs_expanded_targets(_SKDC)]
    assert len(skdc) == 1 and "GetCapabilities" in skdc[0]


def test_a_get_feature_row_without_a_typename_fails_at_expansion() -> None:
    with pytest.raises(ValueError, match="no typename"):
        get_feature_url(
            {
                "id": "bad",
                "service_url": "https://maps.runnymede.gov.uk/geoserver/community/cctv_cameras/wfs",
            }
        )


def test_a_target_off_the_committed_host_set_fails_at_expansion() -> None:
    with pytest.raises(ValueError, match="off the committed host set"):
        capabilities_url(
            {
                "id": "bad",
                "service_url": "https://evil.example/geoserver/wfs",
            }
        )


# --- the GetCapabilities lane ---------------------------------------------------


def test_runnymede_capabilities_mints_the_service_record() -> None:
    report, transport = _run_fixture(_RUNNY)
    services = _subjects(report, "ogc_service")
    assert len(services) == 1
    svc = services[0]
    assert svc["external_id"] == "runnymede-geoserver-community"
    assert svc["publisher_label"] == "Runnymede Borough Council"
    assert svc["served_feature_types"] == [
        "community:car_parks",
        "community:cctv_cameras",
    ]
    assert svc["wfs_version"] == "2.0.0" and svc["update_sequence"] == "147"
    assert str(svc["subject_id"]).startswith("ogc_service:")
    claims = _claims(report)
    service_claims = [c for c in claims if str(c["subject_id"]).startswith("ogc_service:")]
    # the service record's own claims stay inside the family allowlist —
    # the camera predicates ride dot_511's shared emit under ITS contract
    assert {c["predicate_id"] for c in service_claims} <= {
        "portal_index",
        "external_id",
        "title",
        "published_by",
        "jurisdiction",
        "technology",
        "as_of",
    }
    as_ofs = [c for c in service_claims if c["predicate_id"] == "as_of"]
    assert as_ofs and as_ofs[0]["value"] == "147"


def test_a_missing_expected_typename_fails_closed() -> None:
    caps_url = _url_for(_CLACK, "GetCapabilities")
    # the clacks fixture serves ns:cctv_cameras; runnymede's row expects
    # community:cctv_cameras — swap bodies so the expectation misses.
    bodies = {caps_url: (_FIX / "capabilities_geoserver.xml").read_bytes()}
    with pytest.raises(ContentDrift, match="expected_typenames"):
        _run_fixture(_CLACK, bodies=bodies)


def test_an_exception_report_fails_closed() -> None:
    page_url = _url_for(_RUNNY, "GetFeature")
    bodies = {page_url: (_FIX / "exception_report.xml").read_bytes()}
    with pytest.raises(ContentDrift, match="ExceptionReport"):
        _run_fixture(_RUNNY, bodies=bodies)


def test_non_xml_payload_fails_closed() -> None:
    caps_url = _url_for(_RUNNY, "GetCapabilities")
    with pytest.raises(ContentDrift, match="does not parse as XML"):
        _run_fixture(_RUNNY, bodies={caps_url: b"not xml at all"})


# --- the GetFeature lane --------------------------------------------------------


def test_runnymede_getfeature_emits_camera_subjects_via_the_shared_emit() -> None:
    report, transport = _run_fixture(_RUNNY)
    claims = _claims(report)
    camera_claims = [c for c in claims if str(c["subject_id"]).startswith("traffic_camera:")]
    assert camera_claims, "expected traffic_camera subjects"
    lats = [c for c in camera_claims if c["predicate_id"] == "camera_latitude"]
    lons = [c for c in camera_claims if c["predicate_id"] == "camera_longitude"]
    # the gml:pos pair reads lat-lon under the served EPSG:4326 srsName
    assert {c["value"] for c in lats} == {51.3910, 51.3690, 51.4321}
    assert {c["value"] for c in lons} == {-0.5401, -0.5023, -0.5178}
    publishers = [c for c in camera_claims if c["predicate_id"] == "camera_registry_publisher"]
    assert publishers and all(c["value"] == "Runnymede Borough Council" for c in publishers)
    assert not any(c["predicate_id"] == "camera_operator" for c in claims)
    techs = [c for c in camera_claims if c["predicate_id"] == "technology"]
    assert techs and all(c["value"] == "fixed-camera-cctv" for c in techs)
    index = _subjects(report, "open_data_index")
    assert len(index) == 1 and index[0]["result_count"] == 3
    assert index[0]["returned_count"] == 3 and index[0]["truncated"] is False
    # exactly two requests — the declared capabilities + the declared page
    assert len(transport.request_log) == 2


def test_skdc_resolves_its_feature_page_from_the_served_document() -> None:
    report, transport = _run_fixture(_SKDC)
    services = _subjects(report, "ogc_service")
    assert len(services) == 1
    assert services[0]["served_feature_types"] == [_SKDC_TYPENAME]
    assert services[0]["resolved_typenames"] == [_SKDC_TYPENAME]
    # two requests: the committed capabilities + the resolved GetFeature —
    # the SERVED document named the type, never a guessed one.
    assert len(transport.request_log) == 2
    assert "GetFeature" in transport.request_log[1]
    assert "SKDC_INSPIRE_WFS%3ACCTV" in transport.request_log[1]
    claims = _claims(report)
    camera_claims = [c for c in claims if str(c["subject_id"]).startswith("traffic_camera:")]
    lats = [c for c in camera_claims if c["predicate_id"] == "camera_latitude"]
    assert {c["value"] for c in lats} == {52.7864, 52.9120}


def test_skdc_sole_selector_refuses_a_multi_type_service() -> None:
    caps_url = _url_for(_SKDC, "GetCapabilities")
    bodies = {caps_url: (_FIX / "capabilities_geoserver.xml").read_bytes()}
    with pytest.raises(ContentDrift, match="sole"):
        _run_fixture(_SKDC, bodies=bodies)


def test_clacks_getfeature_emits_under_the_nonus_rights_line() -> None:
    report, transport = _run_fixture(_CLACK)
    claims = _claims(report)
    camera_claims = [c for c in claims if str(c["subject_id"]).startswith("traffic_camera:")]
    lats = [c for c in camera_claims if c["predicate_id"] == "camera_latitude"]
    assert {c["value"] for c in lats} == {56.1075, 56.0698}
    # the seat's declared non-US DB-right posture rides the emitted rows
    licences = {str(c.get("license")) for c in camera_claims}
    assert licences == {"LicenseRef-OperatorAccepted-DBRight"}
    jurisdictions = [c for c in camera_claims if c["predicate_id"] == "camera_jurisdiction"]
    assert jurisdictions and all(c["value"] == "GB-SCT" for c in jurisdictions)
    assert len(transport.request_log) == 2


def test_a_denied_field_name_fails_the_capture_closed() -> None:
    page_url = _url_for(_RUNNY, "GetFeature")
    body = (_FIX / "getfeature_geoserver.xml").read_text()
    body = body.replace(
        "<community:status>active</community:status>",
        "<community:contact_email>ops@example.gov.uk</community:contact_email>",
        1,
    )
    with pytest.raises(ContentDrift, match="denied field"):
        _run_fixture(_RUNNY, bodies={page_url: body.encode()})


def test_a_missing_point_geometry_fails_closed() -> None:
    page_url = _url_for(_RUNNY, "GetFeature")
    body = (_FIX / "getfeature_geoserver.xml").read_text()
    # drop the geometry property entirely from every member
    import re as _re

    body = _re.sub(r"<community:the_geom>.*?</community:the_geom>", "", body, flags=_re.S)
    with pytest.raises(ContentDrift, match="no gml:Point"):
        _run_fixture(_RUNNY, bodies={page_url: body.encode()})


def test_an_unmapped_srs_fails_closed() -> None:
    page_url = _url_for(_RUNNY, "GetFeature")
    body = (_FIX / "getfeature_geoserver.xml").read_text()
    body = body.replace("urn:ogc:def:crs:EPSG::4326", "urn:ogc:def:crs:EPSG::27700")
    with pytest.raises(ContentDrift, match="off the declared set"):
        _run_fixture(_RUNNY, bodies={page_url: body.encode()})


def test_a_member_count_over_the_declared_bound_fails_closed() -> None:
    # shrink the declared bound via an inline target row: 3 served members
    # over count=2 is a drifted page, never silently truncated.
    targets = [dict(t) for t in live_targets(_RUNNY)]
    for t in targets:
        spec = dict(t.get("target") or {})
        if spec.get("kind") == "wfs_get_feature":
            spec = {**spec, "count": 2}
            t["target"] = spec
            t["url"] = get_feature_url(spec)
    page_url = next(str(t["url"]) for t in targets if "GetFeature" in str(t["url"]))
    responses = _responses_for(_RUNNY)
    body = (_FIX / "getfeature_geoserver.xml").read_bytes()
    responses[page_url] = FetchResult(
        url=page_url, status=200, body=body, media_type="application/gml+xml"
    )
    connector = OgcWfsConnector()
    transport = MapTransport(responses)
    source = dataclasses.replace(
        get(_RUNNY),
        ingestion_permitted=True,
        compact_status=CompactStatus.PUBLIC_TERMS_ONLY,
    )
    fetcher = PoliteFetcher(
        connector_name=connector.name,
        connector_version=connector.version,
        transport=transport,
        rate_limiter=RateLimiter(sleep=lambda s: None),
    )
    ctx = RunContext(
        source=source,
        run=IngestRun(connector.name, connector.version, "test", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": targets},
    )
    with pytest.raises(ContentDrift, match="over the declared bound"):
        run(connector, ctx)


def test_a_number_returned_mismatch_fails_closed() -> None:
    page_url = _url_for(_RUNNY, "GetFeature")
    body = (_FIX / "getfeature_geoserver.xml").read_text()
    body = body.replace('numberReturned="3"', 'numberReturned="9"')
    with pytest.raises(ContentDrift, match="numberReturned"):
        _run_fixture(_RUNNY, bodies={page_url: body.encode()})


def test_the_runs_are_deterministic_over_the_committed_fixtures() -> None:
    def key(r: Mapping[str, Any]) -> tuple[str, str, str]:
        return (
            str(r.get("subject_id")),
            str(r.get("predicate_id")),
            json.dumps(r.get("value"), sort_keys=True, default=str),
        )

    first, _ = _run_fixture(_RUNNY)
    second, _ = _run_fixture(_RUNNY)
    assert sorted(map(key, first.claims)) == sorted(map(key, second.claims))
