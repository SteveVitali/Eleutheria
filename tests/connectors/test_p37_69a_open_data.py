# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.69a (R11-ACQ-23a, I7 N1–N21 `a`) — the international open-data portal
family.

Thirty-six gated seats: seventeen ride the CKAN lane (two bounded
``package_search`` rows, fourteen ``package_show`` rows + one enumerated
Tasmania seat whose slug truncates in the committed record), two ride the
OpenDataSoft v2 records lane, one the data.europa.eu hub-search POST lane,
three the committed-file lane (Barnet's two CSV registers + Trafford's
GeoJSON), twelve the reused ``dossier_documents`` ``clause_fields`` lane
(dataset pages, regulator guidance, oversight PDFs, the ICO register's
register-level read) and one the ``accountability`` targeted
``oversight_report`` lane (the CNIL BriefCam decision). Every seat stays
``ingestion_permitted=false`` — the operator's OP-26 Wave-D flip under
ING-GO-D is the only route to live. Replay runs over the committed synthetic
fixtures (fixtures/p37_69a/SOURCES.md) with no network.
"""

import dataclasses
import io
import json
import tomllib
import zipfile
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import pytest
from connectors.accountability import AccountabilityConnector
from connectors.dossier_documents import DOSSIER_SOURCES, DossierDocumentsConnector
from connectors.live_targets import live_targets
from connectors.net import PoliteFetcher, RateLimiter, RobotsResult
from connectors.open_data_files import (
    CONNECTOR_NAMES as FILE_CONNECTORS,
)
from connectors.open_data_files import (
    CsvFileConnector,
    GeojsonFileConnector,
)
from connectors.open_data_files import enumerated_rows as file_enumerated
from connectors.open_data_files import (
    expanded_targets as file_expanded_targets,
)
from connectors.open_data_files import (
    vocab as files_vocab,
)
from connectors.open_data_portals import (
    CONNECTOR_NAMES as PORTAL_CONNECTORS,
)
from connectors.open_data_portals import (
    CkanPackageSearchConnector,
    DataeuropaHubSearchConnector,
    OpendatasoftExploreConnector,
    portal_targets,
)
from connectors.open_data_portals import (
    enumerated_rows as portal_enumerated,
)
from connectors.open_data_portals import (
    targets_for as portal_targets_for,
)
from connectors.open_data_portals import (
    vocab as portals_vocab,
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

_RETRIEVED = datetime(2026, 11, 14, tzinfo=UTC)
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


_FIX = Path(__file__).parent / "fixtures" / "p37_69a"

#: The seventeen CKAN seats (16 live-target rows + 1 enumerated).
_SEARCH_SOURCES = {"dot_511_gb", "camreg_au_ckan_package_search"}
_PKGSHOW_SOURCES = {
    "camreg_gb_eng_mansf_cctv_cameras",
    "camreg_gb_eng_brist_cctv_cameras",
    "camreg_gb_sct_edinburgh_public_cctv",
    "camreg_au_nsw_sydney_street_safety",
    "camreg_au_tas_hobar_security_camera",
    "camreg_au_wa_perth_security_cameras",
    "camreg_au_qld_towns_cctv_camera_register",
    "camreg_au_vic_ballarat_cctv_cameras",
    "camreg_au_vic_geelong_closed_circuit",
    "camreg_ie_d_dublin_traffic_poles_with",
    "camreg_it_me_messina_videosorveglianza",
    "camreg_si_048_ko_evje_videonadzor_na",
    "ccops_si_085_novo_mesto_evidenca_o",
    "camreg_ua_18_korosten",
}
_CKAN_SOURCES = _SEARCH_SOURCES | _PKGSHOW_SOURCES
_ODS_SOURCES = {
    "camreg_gb_eng_leice_cctv_cameras",
    "camreg_fr_92_grand_paris_seine_ouest_vid",
}
_HUB_SOURCES = {"camreg_eu_eea_data_europa_search_api"}
_PORTAL_SOURCES = _CKAN_SOURCES | _ODS_SOURCES | _HUB_SOURCES

_CSV_SOURCES = {"camreg_gb_eng_barnet_cctv_camera", "camreg_gb_eng_barnet_cctv_traffic"}
_GEOJSON_SOURCES = {"camreg_gb_eng_traff_trafford_cctv"}
_FILE_SOURCES = _CSV_SOURCES | _GEOJSON_SOURCES

_DOSSIER_SOURCES = {
    "ccops_gb_eng_barnet_traffic_cctv",
    "camreg_gb_eng_north_cctv_cameras",
    "ccops_iso_au_privacy_commissioner",
    "statrep_ca_special_parliament_use",
    "ccops_it_tn_trento_provvedimento_dell_11",
    "statrep_gb_eng_seven_cctv_june_2026",
    "statrep_gb_sct_joint_assurance_review",
    "legis_ie_rs_general_scheme",
    "statrep_gb_uk_algorithmic_transparency",
    "statrep_gb_enforcement_action",
    "camreg_pt_11_lisboa_sistema_de",
    "camreg_es_md_madrid_c_maras_de",
}
_ACCOUNTABILITY_SOURCES = {"statrep_fr_cnil_utilisation_de"}

#: The enumerated seats — registered, gated, never fetchable (D-P37.69a-1).
_ENUMERATED_SOURCES = {"camreg_au_tas_emergency_closed_circuit"}

_WIRED = _PORTAL_SOURCES | _FILE_SOURCES | _DOSSIER_SOURCES | _ACCOUNTABILITY_SOURCES

_DOSSIER_FIXTURES = {
    "ccops_gb_eng_barnet_traffic_cctv": "barnet_contract.html",
    "camreg_gb_eng_north_cctv_cameras": "north_somerset.html",
    "ccops_iso_au_privacy_commissioner": "oaic.html",
    "statrep_ca_special_parliament_use": "opc_ca.html",
    "ccops_it_tn_trento_provvedimento_dell_11": "trento.html",
    "statrep_gb_eng_seven_cctv_june_2026": "sevenoaks.html",
    "statrep_gb_sct_joint_assurance_review": "scottish_review.html",
    "legis_ie_rs_general_scheme": "oireachtas.html",
    "statrep_gb_uk_algorithmic_transparency": "atrs.html",
    "statrep_gb_enforcement_action": "ico.html",
    "camreg_pt_11_lisboa_sistema_de": "lisboa.html",
    "camreg_es_md_madrid_c_maras_de": "madrid.html",
}
_CSV_FIXTURES = {
    "camreg_gb_eng_barnet_cctv_camera": "barnet_cctv.csv",
    "camreg_gb_eng_barnet_cctv_traffic": "barnet_mtc.csv",
}


def _connect_for(source_id: str) -> Any:
    if source_id in _ODS_SOURCES:
        return OpendatasoftExploreConnector()
    if source_id in _HUB_SOURCES:
        return DataeuropaHubSearchConnector()
    if source_id in _CKAN_SOURCES:
        return CkanPackageSearchConnector()
    if source_id in _CSV_SOURCES:
        return CsvFileConnector()
    if source_id in _GEOJSON_SOURCES:
        return GeojsonFileConnector()
    if source_id in _ACCOUNTABILITY_SOURCES:
        return AccountabilityConnector()
    return DossierDocumentsConnector()


def _fixture_for(source_id: str) -> tuple[str, str]:
    """(fixture filename, media type) for the seat's committed fixture."""
    if source_id == "dot_511_gb" or source_id == "camreg_au_ckan_package_search":
        return "ckan_package_search_uk.json", "application/json"
    if source_id in _PKGSHOW_SOURCES:
        return "ckan_package_show.json", "application/json"
    if source_id == "camreg_gb_eng_leice_cctv_cameras":
        return "ods_records_leicester.json", "application/json"
    if source_id == "camreg_fr_92_grand_paris_seine_ouest_vid":
        return "ods_records_seine.json", "application/json"
    if source_id in _HUB_SOURCES:
        return "hub_search.json", "application/json"
    if source_id in _CSV_SOURCES:
        return _CSV_FIXTURES[source_id], "text/csv"
    if source_id in _GEOJSON_SOURCES:
        return "trafford_cctv.geojson", "application/geo+json"
    if source_id in _ACCOUNTABILITY_SOURCES:
        return "cnil_briefcam.html", "text/html"
    return _DOSSIER_FIXTURES[source_id], "text/html"


def _run_fixture(source_id: str, *, body: bytes | None = None):
    """Run the source's connector over its committed fixture (no network)."""
    targets = [dict(t) for t in live_targets(source_id)]
    assert targets, f"{source_id} resolves no reviewed targets"
    fixture, media = _fixture_for(source_id)
    responses: dict[str, FetchResult] = {
        str(t["url"]): FetchResult(
            url=str(t["url"]),
            status=200,
            body=body if body is not None else (_FIX / fixture).read_bytes(),
            media_type=media,
        )
        for t in targets
    }
    connector = _connect_for(source_id)
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


# --- registration, routing, gating (HG-03 / OP-26) ----------------------------


def test_the_36_seats_are_registered_routed_and_gated() -> None:
    assert len(_WIRED) == 35 and len(_ENUMERATED_SOURCES) == 1
    expected: dict[str, str] = {}
    for s in _CKAN_SOURCES:
        expected[s] = "ckan_package_search"
    for s in _ODS_SOURCES:
        expected[s] = "opendatasoft_explore"
    for s in _HUB_SOURCES:
        expected[s] = "dataeuropa_hub_search"
    for s in _CSV_SOURCES:
        expected[s] = "csv_file"
    for s in _GEOJSON_SOURCES:
        expected[s] = "geojson_file"
    for s in _DOSSIER_SOURCES:
        expected[s] = "dossier_documents"
    for s in _ACCOUNTABILITY_SOURCES:
        expected[s] = "accountability"
    for source_id, connector in expected.items():
        assert CONNECTOR_FOR_SOURCE[source_id] == connector, source_id
        rec = get(source_id)
        assert rec.ingestion_permitted is False, source_id
        assert live_gate_reasons(rec), f"{source_id} reports no live-gate reason"
    for source_id in _ENUMERATED_SOURCES:
        assert source_id not in CONNECTOR_FOR_SOURCE, source_id
        assert get(source_id).ingestion_permitted is False, source_id


def test_the_dossier_sources_tuple_carries_the_twelve_document_seats() -> None:
    for source_id in _DOSSIER_SOURCES:
        assert source_id in DOSSIER_SOURCES, source_id


def test_the_dispositions_table_carries_no_p37_69a_promote_row() -> None:
    # P25.6 exactly-once: a connector-mapped source carries NO disposition
    # row — the 35 wired seats' `promote` placeholders resolved when this
    # row wired the connector map. The ONE enumerated seat is NOT
    # connector-mapped, so the shared live-disposition invariant requires
    # it to carry exactly one `promote` row until D-P37.69a-1's endpoint
    # preflight wires (or retires) its lane.
    disp = tomllib.loads(Path("connectors/src/connectors/data/live_dispositions.toml").read_text())
    seats = disp.get("sources") or {}
    for source_id in _WIRED:
        assert source_id not in seats, source_id
    for source_id in _ENUMERATED_SOURCES:
        assert seats[source_id]["disposition"] == "promote", source_id


def test_the_enumerated_rows_record_the_uncommitted_endpoints() -> None:
    portal_enum = {r["source_id"] for r in portal_enumerated()}
    file_enum = {r["source_id"] for r in file_enumerated()}
    assert "camreg_au_tas_emergency_closed_circuit" in portal_enum
    assert "camreg_au_vic_geelong_closed_circuit" in portal_enum
    assert {
        "camreg_es_md_madrid_c_maras_de",
        "camreg_au_vic_ballarat_cctv_cameras",
        "camreg_pt_11_lisboa_sistema_de",
        "camreg_au_qld_towns_cctv_camera_register",
    } <= file_enum
    # the enumerated seat resolves no live target — never a fetch surface
    assert live_targets("camreg_au_tas_emergency_closed_circuit") == []


# --- the portal lane: expansion + host gate ------------------------------------


def test_every_portal_target_expands_onto_the_committed_host_set() -> None:
    hosts = set(portals_vocab()["hosts"])
    from urllib.parse import urlsplit

    for row in (r for s in _PORTAL_SOURCES for r in portal_targets(s)):
        assert urlsplit(str(row["url"])).netloc.lower() in hosts, row["url"]
        if row["kind"] in {"package_search", "package_show"}:
            assert "/api/action/" in row["url"] or "/api/3/action/" in row["url"]
        if row["kind"] == "ods_records":
            assert "/api/explore/v2.1/catalog/datasets/" in row["url"]
    for row in (r for s in _FILE_SOURCES for r in file_expanded_targets(s)):
        assert urlsplit(str(row["url"])).netloc.lower() in set(files_vocab()["hosts"])


def test_the_target_table_kinds_match_their_source_lanes() -> None:
    for source_id in _SEARCH_SOURCES:
        assert {t["kind"] for t in portal_targets_for(source_id)} == {"package_search"}
    for source_id in _PKGSHOW_SOURCES:
        assert {t["kind"] for t in portal_targets_for(source_id)} == {"package_show"}
    for source_id in _ODS_SOURCES:
        assert {t["kind"] for t in portal_targets_for(source_id)} == {"ods_records"}
    for source_id in _HUB_SOURCES:
        assert {t["kind"] for t in portal_targets_for(source_id)} == {"hub_search"}


# --- CKAN package_search --------------------------------------------------------


def test_ckan_package_search_emits_index_datasets_and_pointers() -> None:
    report, transport = _run_fixture("dot_511_gb")
    datasets = _subjects(report, "open_data_dataset")
    index = _subjects(report, "open_data_index")
    resources = _subjects(report, "open_data_resource")
    assert len(index) == 1 and index[0]["result_count"] == 3
    assert index[0]["returned_count"] == 3 and index[0]["truncated"] is False
    assert len(datasets) == 3
    assert {d["external_id"] for d in datasets} == {
        "example-town-cctv-locations",
        "example-shire-public-space-cameras",
        "example-borough-cctv-policy",
    }
    # the person-shaped CKAN keys ride as NAMES ONLY (excluded_fields),
    # never values — the Part VIII drop is legible on the entity row.
    town = next(d for d in datasets if d["external_id"] == "example-town-cctv-locations")
    assert town["excluded_fields"] == ["author", "maintainer_email"]
    assert len(resources) == 3  # r1, r2, r3 — pointers, never fetched
    assert transport.request_log == [
        "https://data.gov.uk/api/action/package_search?q=CCTV&rows=10"
    ]  # exactly one request — resources are pointers
    claims = _claims(report)
    assert {c["predicate_id"] for c in claims} <= {
        "portal_index",
        "external_id",
        "title",
        "document",
        "published_by",
        "jurisdiction",
        "technology",
        "as_of",
    }
    # no person value anywhere in the emitted surface
    blob = json.dumps(report.claims)
    assert "data@example-town.gov.uk" not in blob and "J. Bloggs" not in blob


def test_ckan_package_show_emits_the_dataset_and_its_resource_pointers() -> None:
    report, transport = _run_fixture("camreg_gb_eng_mansf_cctv_cameras")
    datasets = _subjects(report, "open_data_dataset")
    resources = _subjects(report, "open_data_resource")
    assert len(datasets) == 1
    assert datasets[0]["external_id"] == "example-city-cctv-cameras"
    assert datasets[0]["publisher_label"] == "Example City Council"
    assert datasets[0]["excluded_fields"] == ["author_email"]
    assert {r["external_id"] for r in resources} == {"res-1", "res-2"}
    assert all("open_data_dataset:" in str(d["subject_id"]) for d in datasets)
    assert len(transport.request_log) == 1
    claims = _claims(report)
    published = [c for c in claims if c["predicate_id"] == "published_by"]
    assert published and published[0]["value"] == "Example City Council"
    assert not any(str(c.get("value")) == "ops@example-city.example" for c in claims)


def test_ckan_error_envelope_and_non_json_fail_closed() -> None:
    bad_envelope = json.dumps({"success": False, "error": {"message": "not found"}}).encode()
    with pytest.raises(ContentDrift, match="success flag"):
        _run_fixture("camreg_gb_eng_mansf_cctv_cameras", body=bad_envelope)
    with pytest.raises(ContentDrift, match="non-JSON"):
        _run_fixture("camreg_gb_eng_mansf_cctv_cameras", body=b"<html>nope</html>")


def test_ckan_result_missing_count_is_drift_not_a_guess() -> None:
    payload = json.dumps({"success": True, "result": {"results": []}}).encode()
    with pytest.raises(ContentDrift, match="integer 'count'"):
        _run_fixture("dot_511_gb", body=payload)


# --- the hub-search seat ---------------------------------------------------------


def test_hub_search_posts_the_reviewed_body_and_enumerates_datasets() -> None:
    report, transport = _run_fixture("camreg_eu_eea_data_europa_search_api")
    index = _subjects(report, "open_data_index")
    datasets = _subjects(report, "open_data_dataset")
    assert len(index) == 1 and index[0]["result_count"] == 2
    assert len(datasets) == 2
    titles = {d["title"] for d in datasets}
    assert "Example commune camera register" in titles  # localised title resolves
    assert transport.request_log == ["https://data.europa.eu/api/hub/search/search"]


# --- the ODS records lane ---------------------------------------------------------


def test_ods_records_emit_camera_subjects_via_the_shared_emit() -> None:
    report, _ = _run_fixture("camreg_gb_eng_leice_cctv_cameras")
    datasets = _subjects(report, "open_data_dataset")
    assert len(datasets) == 1 and datasets[0]["external_id"] == "cctv-cameras"
    claims = _claims(report)
    camera_claims = [c for c in claims if str(c["subject_id"]).startswith("traffic_camera:")]
    assert camera_claims, "expected traffic_camera subjects"
    lats = [c for c in camera_claims if c["predicate_id"] == "camera_latitude"]
    lons = [c for c in camera_claims if c["predicate_id"] == "camera_longitude"]
    assert len(lats) == 2 and len(lons) == 2
    assert {c["value"] for c in lats} == {52.63, 52.64}
    publishers = [c for c in camera_claims if c["predicate_id"] == "camera_registry_publisher"]
    assert publishers and all(c["value"] == "Leicester City Council" for c in publishers)
    # publisher label is provenance only — never a camera_operator claim
    assert not any(c["predicate_id"] == "camera_operator" for c in claims)
    techs = [c for c in camera_claims if c["predicate_id"] == "technology"]
    assert techs and all(c["value"] == "fixed-camera-cctv" for c in techs)


def test_ods_denied_field_name_fails_the_capture_closed() -> None:
    payload = json.dumps(
        {
            "total_count": 1,
            "results": [
                {
                    "id": "VP-02",
                    "adresse": "2 Rue Example",
                    "geo_point_2d": {"lon": 2.24, "lat": 48.83},
                    "operator_email": "ops@example.fr",
                }
            ],
        }
    ).encode()
    with pytest.raises(ContentDrift, match="denied field"):
        _run_fixture("camreg_fr_92_grand_paris_seine_ouest_vid", body=payload)


def test_ods_missing_coordinate_is_drift_never_a_guessed_point() -> None:
    payload = json.dumps(
        {"total_count": 1, "results": [{"id": "VP-03", "adresse": "3 Rue Example"}]}
    ).encode()
    with pytest.raises(ContentDrift, match="no valid published coordinate"):
        _run_fixture("camreg_fr_92_grand_paris_seine_ouest_vid", body=payload)


# --- the committed-file lanes ----------------------------------------------------


def test_csv_lane_emits_camera_rows_and_the_dataset_anchor() -> None:
    report, transport = _run_fixture("camreg_gb_eng_barnet_cctv_camera")
    datasets = _subjects(report, "open_data_dataset")
    assert len(datasets) == 1
    claims = _claims(report)
    refs = [c for c in claims if c["predicate_id"] == "camera_external_ref"]
    assert {c["value"] for c in refs} == {"EX-001", "EX-002"}
    lats = [c for c in claims if c["predicate_id"] == "camera_latitude"]
    assert {c["value"] for c in lats} == {51.65, 51.64}
    assert len(transport.request_log) == 1
    names = [c for c in claims if c["predicate_id"] == "camera_name"]
    assert {c["value"] for c in names} == {"Example Parade", "Example High Road"}


def test_csv_denied_header_column_fails_closed_never_partial() -> None:
    with pytest.raises(ContentDrift, match="denied field"):
        _run_fixture(
            "camreg_gb_eng_barnet_cctv_camera",
            body=(_FIX / "barnet_denied.csv").read_bytes(),
        )


def test_csv_missing_declared_column_is_drift_not_a_guess() -> None:
    bad = b"Camera Ref,Location,Latitude\nEX-001,Example Parade,51.65\n"
    # The marker screen fires first (the absent column is also a declared
    # marker) — either way the capture refuses, never a guessed position.
    with pytest.raises(ContentDrift, match="Longitude"):
        _run_fixture("camreg_gb_eng_barnet_cctv_camera", body=bad)


def test_geojson_lane_emits_point_devices() -> None:
    report, _ = _run_fixture("camreg_gb_eng_traff_trafford_cctv")
    claims = _claims(report)
    refs = [c for c in claims if c["predicate_id"] == "camera_external_ref"]
    assert {c["value"] for c in refs} == {"TR-001", "TR-002"}
    lons = [c for c in claims if c["predicate_id"] == "camera_longitude"]
    assert {c["value"] for c in lons} == {-2.35, -2.36}


def test_geojson_non_point_member_and_non_collection_fail_closed() -> None:
    bad_member = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
                    },
                    "properties": {"id": "TR-009"},
                }
            ],
        }
    ).encode()
    with pytest.raises(ContentDrift, match="not a Point"):
        _run_fixture("camreg_gb_eng_traff_trafford_cctv", body=bad_member)
    with pytest.raises(ContentDrift, match="FeatureCollection"):
        _run_fixture(
            "camreg_gb_eng_traff_trafford_cctv",
            body=json.dumps({"type": "Feature", "geometry": None}).encode(),
        )


def _make_xlsx(rows: list[list[str]], *, sheet_name: str = "Sheet1") -> bytes:
    """A minimal valid xlsx (sharedStrings + one worksheet) — synthetic."""
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    shared = [c for r in rows for c in r]
    idx = {v: i for i, v in enumerate(shared)}
    sheet = ElementTree.fromstring(f'<worksheet xmlns="{ns}"><sheetData/></worksheet>')
    data = sheet.find(f"{{{ns}}}sheetData")
    for r_i, r in enumerate(rows):
        row_el = ElementTree.SubElement(data, f"{{{ns}}}row")
        for c_i, v in enumerate(r):
            c = ElementTree.SubElement(row_el, f"{{{ns}}}c")
            c.set("r", f"{chr(65 + c_i)}{r_i + 1}")
            c.set("t", "s")
            v_el = ElementTree.SubElement(c, f"{{{ns}}}v")
            v_el.text = str(idx[v])
    ss = ElementTree.fromstring(f'<sst xmlns="{ns}"/>')
    for s in shared:
        si = ElementTree.SubElement(ss, f"{{{ns}}}si")
        t = ElementTree.SubElement(si, f"{{{ns}}}t")
        t.text = s
    rels_root = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="t" Target="worksheets/sheet1.xml"/></Relationships>'
    )
    workbook = (
        f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{sheet_name}" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", rels_root)
        zf.writestr("xl/sharedStrings.xml", ElementTree.tostring(ss))
        zf.writestr("xl/worksheets/sheet1.xml", ElementTree.tostring(sheet))
    return buf.getvalue()


def test_xlsx_reader_parses_the_declared_sheet_and_screens_the_header() -> None:
    from connectors.open_data_files import _xlsx_rows

    body = _make_xlsx(
        [["Ref", "Location", "Latitud", "Longitud"], ["M-1", "Plaza Example", "40.42", "-3.70"]]
    )
    rows = _xlsx_rows("camreg_es_md_madrid_c_maras_de", body, {"sheet_name": "Sheet1"})
    assert rows[0] == ["Ref", "Location", "Latitud", "Longitud"]
    assert rows[1][0] == "M-1"
    with pytest.raises(ContentDrift, match="declared sheet"):
        _xlsx_rows(
            "camreg_es_md_madrid_c_maras_de",
            _make_xlsx([["a"]], sheet_name="Other"),
            {"sheet_name": "Sheet1"},
        )
    with pytest.raises(ContentDrift, match="not a readable xlsx"):
        _xlsx_rows("camreg_es_md_madrid_c_maras_de", b"not a zip", {"sheet_name": "Sheet1"})


# --- the reused dossier / accountability seats -----------------------------------


@pytest.mark.parametrize("source_id", sorted(_DOSSIER_SOURCES))
def test_dossier_seats_emit_their_reviewed_clause_facts(source_id: str) -> None:
    report, transport = _run_fixture(source_id)
    claims = _claims(report)
    assert claims, f"{source_id} emitted no claims"
    titles = [c for c in claims if c["predicate_id"] == "title"]
    assert titles, f"{source_id} emitted no title claim"
    # institutional facts only — no device-shaped claim off a document lane
    assert not any(c["predicate_id"].startswith("camera_") for c in claims)
    assert len(transport.request_log) == len(live_targets(source_id))


def test_the_cnil_seat_emits_one_oversight_event() -> None:
    report, transport = _run_fixture("statrep_fr_cnil_utilisation_de")
    assert report.claims, "the CNIL seat emitted no records"
    claims = _claims(report)
    assert not any(c["predicate_id"].startswith("camera_") for c in claims)
    assert transport.request_log == [
        "https://cnil.fr/fr/utilisation-briefcam-logiciels-analyse-video-par-etat-communes-la-cnil-prononce-plusieurs-mises-en-demeure"
    ]


# --- vocabulary + determinism -----------------------------------------------------


def test_the_vocabularies_version_and_allowlists_are_committed() -> None:
    assert portals_vocab()["vocab_version"] == "2026.11.14"
    assert files_vocab()["vocab_version"] == "2026.11.14"
    assert PORTAL_CONNECTORS == {
        "ckan_package_search",
        "opendatasoft_explore",
        "dataeuropa_hub_search",
    }
    assert FILE_CONNECTORS == {"csv_file", "geojson_file", "xlsx_file"}


def test_replay_is_deterministic_for_the_camera_lanes() -> None:
    """Two replay runs over the same fixture mint the same claim surface."""
    for source_id in (
        "camreg_gb_eng_leice_cctv_cameras",
        "camreg_gb_eng_barnet_cctv_camera",
        "camreg_gb_eng_traff_trafford_cctv",
        "camreg_gb_eng_mansf_cctv_cameras",
        "dot_511_gb",
    ):
        first, _ = _run_fixture(source_id)
        second, _ = _run_fixture(source_id)

        def fingerprint(report: Any) -> list[tuple[str, str, str]]:
            return sorted(
                (
                    str(r.get("record_kind")),
                    str(r.get("subject_id")),
                    str(r.get("predicate_id")),
                )
                for r in report.claims
            )

        assert fingerprint(first) == fingerprint(second), source_id
