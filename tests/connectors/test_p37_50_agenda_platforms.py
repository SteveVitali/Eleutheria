# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.50 (R11-ACQ-22, I8 §6.2): agenda platforms v2 — the four reviewed HTML
index contracts (CivicPlus AgendaCenter, iCompass CivicWeb, Hyland OnBase
Agenda Online, and the Fargo-style year archive) over committed fixtures
trimmed from the verified 2026-11-13 registration captures.

Covers: per-city source → tenant expansion (platform/source_id split), the
markup parses + emitted agenda_index/meeting_date rows (jurisdiction + doc
link), the Savannah AgendaPlus→AgendaCenter binding finding, minutes/
attachments never minted (P8-3), ContentDrift on contract violation, the
honest empty outcome, gated-source live refusals, and a +0 shadow replay.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from connectors.live_targets import live_targets
from connectors.procurement import tenant_targets
from connectors.runner import CONNECTOR_FOR_SOURCE, live_gate_reasons, run_connector_over_fixture
from connectors.stages import ContentDrift

_FIX = Path(__file__).parent / "fixtures" / "p37_50"

SEATS = {
    "agenda_durham_nc_agenda_center": ("civicplus_agendacenter", "durham_nc", "Durham, NC"),
    "agenda_hialeah_fl_agenda_center": ("civicplus_agendacenter", "hialeah_fl", "Hialeah, FL"),
    "agenda_bexar_county_tx_agenda_center": (
        "civicplus_agendacenter",
        "bexar_county_tx",
        "Bexar County, TX",
    ),
    "agenda_savannah_ga_2023_05_25": ("civicplus_agendacenter", "savannah_ga", "Savannah, GA"),
    "agenda_jersey_city_nj_digital_agenda": ("civicweb", "jersey_city_nj", "Jersey City, NJ"),
    "agenda_tx_dallas_county_commissioners": ("civicweb", "dallas_county_tx", "Dallas County, TX"),
    "agenda_frisco_tx_onbase_agenda_online": (
        "onbase_agendaonline",
        "frisco_tx",
        "Frisco, TX",
    ),
    "agenda_tampa_fl_onbase_agenda_online": ("onbase_agendaonline", "tampa_fl", "Tampa, FL"),
    "agenda_az_maricopa_county_board_of": (
        "onbase_agendaonline",
        "maricopa_county_az",
        "Maricopa County, AZ",
    ),
    "agenda_nd_fargo_city_commission_agendas": ("html_agenda_archive", "fargo_nd", "Fargo, ND"),
}


def _url(source_id: str) -> str:
    targets = tenant_targets(platform=source_id)
    assert len(targets) == 1, f"{source_id}: expected exactly one tenant target"
    return str(targets[0]["url"])


def test_all_ten_seats_map_to_the_procurement_connector() -> None:
    for source_id in SEATS:
        assert CONNECTOR_FOR_SOURCE[source_id] == "procurement", source_id


def test_every_seat_expands_to_its_bound_tenant() -> None:
    for source_id, (platform, tenant_id, jurisdiction) in SEATS.items():
        targets = tenant_targets(platform=source_id)
        assert len(targets) == 1, source_id
        target = targets[0]
        assert target["platform"] == platform
        assert target["source_id"] == source_id
        assert target["tenant_id"] == tenant_id
        assert target["jurisdiction"] == jurisdiction
        assert target["kind"] == "agenda_index"
        assert target["record_refusals"] is True
        # The index URL is reviewed row data, never a constructed crawl.
        assert target["url"].startswith("https://")


def test_live_targets_expand_through_the_registry() -> None:
    for source_id in SEATS:
        assert live_targets(source_id) == tenant_targets(platform=source_id)


def test_all_ten_seats_stay_gated_and_refuse_live() -> None:
    for source_id in SEATS:
        assert live_gate_reasons(source_id), (
            f"{source_id}: the seat must stay ingestion_permitted=false "
            "pending the operator's OP-26 Wave-D flip"
        )


def test_savannah_binds_the_serving_agendacenter_not_the_walled_host() -> None:
    target = tenant_targets(platform="agenda_savannah_ga_2023_05_25")[0]
    # agenda.savannahga.gov is login-walled (censused access_restricted); the
    # seat binds the same jurisdiction's serving CivicPlus AgendaCenter.
    assert target["url"] == "https://www.savannahga.gov/AgendaCenter"
    assert "agenda.savannahga.gov" not in target["url"]


def test_civicplus_index_over_fixture() -> None:
    report = run_connector_over_fixture(
        "procurement",
        "agenda_hialeah_fl_agenda_center",
        _FIX / "civicplus_hialeah.html",
        media_type="text/html",
        kind="agenda_index",
        target_url=_url("agenda_hialeah_fl_agenda_center"),
    )
    rows = [c for c in report.claims if c.get("record_kind") == "agenda_index"]
    hialeah = [r for r in rows if r.get("jurisdiction") == "Hialeah, FL"]
    ids = {r["external_id"] for r in hialeah}
    # The fixture's City Council panel items index — the replay doubles rows
    # (explicit + registry target), dedupe on external_id.
    assert ids >= {"11102026-1423", "10272026-1416"}
    assert all(r["platform"] == "civicplus_agendacenter" for r in hialeah)
    # The agenda ViewFile link is recorded, never fetched (P8-3).
    assert all(r["document"] and "ViewFile/Agenda/" in r["document"] for r in hialeah)
    assert not any("ViewFile/Minutes/" in str(r.get("document")) for r in rows)
    dates = {r["value"] for r in report.claims if r.get("predicate_id") == "meeting_date"}
    assert "2026-11-10" in dates
    titles = [r["raw_value"] for r in hialeah]
    assert any("Agenda" in str(t) for t in titles)


def test_civicweb_index_over_fixture() -> None:
    report = run_connector_over_fixture(
        "procurement",
        "agenda_jersey_city_nj_digital_agenda",
        _FIX / "civicweb_jersey.html",
        media_type="text/html",
        kind="agenda_index",
        target_url=_url("agenda_jersey_city_nj_digital_agenda"),
    )
    rows = [
        c
        for c in report.claims
        if c.get("record_kind") == "agenda_index" and c.get("jurisdiction") == "Jersey City, NJ"
    ]
    ids = {r["external_id"] for r in rows}
    assert {"375", "374", "373", "384", "382", "337"} <= ids
    assert all(r["platform"] == "civicweb" for r in rows)
    assert all("MeetingInformation.aspx?Id=" in str(r["document"]) for r in rows)
    assert {r["type_name"] for r in rows} >= {
        "Regular Meeting of Municipal Council",
        "Special Meeting of Municipal Council",
    }
    dates = {r["value"] for r in report.claims if r.get("predicate_id") == "meeting_date"}
    assert "2026-11-12" in dates


def test_onbase_meeting_row_index_over_fixture() -> None:
    report = run_connector_over_fixture(
        "procurement",
        "agenda_frisco_tx_onbase_agenda_online",
        _FIX / "onbase_frisco.html",
        media_type="text/html",
        kind="agenda_index",
        target_url=_url("agenda_frisco_tx_onbase_agenda_online"),
    )
    rows = [
        c
        for c in report.claims
        if c.get("record_kind") == "agenda_index" and c.get("jurisdiction") == "Frisco, TX"
    ]
    ids = {r["external_id"] for r in rows}
    assert {"5821", "5822"} <= ids
    assert all(r["platform"] == "onbase_agendaonline" for r in rows)
    assert all("Meetings/ViewMeeting" in str(r["document"]) for r in rows)
    # Minutes (doctype=2) + DownloadFile PDFs never ride the row (P8-3).
    assert not any("doctype=2" in str(r.get("document")) for r in rows)
    assert not any("DownloadFile" in str(r.get("document")) for r in rows)
    dates = {r["value"] for r in report.claims if r.get("predicate_id") == "meeting_date"}
    assert "2026-11-17" in dates
    assert {r["type_name"] for r in rows} >= {"Legislative Committee", "City Council Work Session"}


def test_onbase_embedded_search_results_over_fixture() -> None:
    report = run_connector_over_fixture(
        "procurement",
        "agenda_tampa_fl_onbase_agenda_online",
        _FIX / "onbase_tampa.html",
        media_type="text/html",
        kind="agenda_index",
        target_url=_url("agenda_tampa_fl_onbase_agenda_online"),
    )
    rows = [
        c
        for c in report.claims
        if c.get("record_kind") == "agenda_index" and c.get("jurisdiction") == "Tampa, FL"
    ]
    ids = {r["external_id"] for r in rows}
    assert {"2838", "2945"} <= ids
    assert any(r["title"] == "City Council Regular - January 7, 2027" for r in rows)
    assert all(
        "Meetings/ViewMeeting" in str(r["document"]) and "doctype=1" in str(r["document"])
        for r in rows
    )
    dates = {r["value"] for r in report.claims if r.get("predicate_id") == "meeting_date"}
    assert "2027-01-07" in dates


def test_fargo_year_archive_over_fixture() -> None:
    report = run_connector_over_fixture(
        "procurement",
        "agenda_nd_fargo_city_commission_agendas",
        _FIX / "archive_fargo.html",
        media_type="text/html",
        kind="agenda_index",
        target_url=_url("agenda_nd_fargo_city_commission_agendas"),
    )
    rows = [
        c
        for c in report.claims
        if c.get("record_kind") == "agenda_index" and c.get("jurisdiction") == "Fargo, ND"
    ]
    ids = {r["external_id"] for r in rows}
    assert "ag26jan5" in ids
    # Consent + Regular background links are attachments, never items (P8-3).
    assert "jan4consentagenda" not in ids
    assert "jan5regularagenda" not in ids
    assert all(r["platform"] == "html_agenda_archive" for r in rows)
    assert all(r["type_name"] == "City Commission" for r in rows)
    assert all("download.fargond.gov" in str(r["document"]) for r in rows)
    dates = {r["value"] for r in report.claims if r.get("predicate_id") == "meeting_date"}
    assert "2026-01-05" in dates


def test_no_document_fanout_targets_resolve() -> None:
    # P8-3: matter metadata only — no doc_url_template/doc_link_keys on the
    # HTML contracts, so discover_more resolves no agenda_document targets.
    from connectors.procurement import platform_endpoints

    for platform in (
        "civicplus_agendacenter",
        "civicweb",
        "onbase_agendaonline",
        "html_agenda_archive",
    ):
        cfg = platform_endpoints()[platform]
        assert not cfg.get("doc_url_template") and not cfg.get("doc_link_keys"), platform


def test_markup_contract_violation_is_drift_not_empty(tmp_path: Path) -> None:
    fixture = tmp_path / "drift.html"
    fixture.write_text((_FIX / "drift.html").read_text())
    with pytest.raises(ContentDrift):
        run_connector_over_fixture(
            "procurement",
            "agenda_hialeah_fl_agenda_center",
            fixture,
            media_type="text/html",
            kind="agenda_index",
            target_url=_url("agenda_hialeah_fl_agenda_center"),
        )


def test_marked_empty_index_is_an_honest_empty() -> None:
    report = run_connector_over_fixture(
        "procurement",
        "agenda_hialeah_fl_agenda_center",
        _FIX / "empty_civicplus.html",
        media_type="text/html",
        kind="agenda_index",
        target_url=_url("agenda_hialeah_fl_agenda_center"),
    )
    assert not [
        c
        for c in report.claims
        if c.get("record_kind") == "agenda_index" and c.get("jurisdiction") == "Hialeah, FL"
    ]


def test_shadow_replay_is_plus_zero() -> None:
    first = run_connector_over_fixture(
        "procurement",
        "agenda_hialeah_fl_agenda_center",
        _FIX / "civicplus_hialeah.html",
        media_type="text/html",
        kind="agenda_index",
        target_url=_url("agenda_hialeah_fl_agenda_center"),
    )
    second = run_connector_over_fixture(
        "procurement",
        "agenda_hialeah_fl_agenda_center",
        _FIX / "civicplus_hialeah.html",
        media_type="text/html",
        kind="agenda_index",
        target_url=_url("agenda_hialeah_fl_agenda_center"),
    )
    mine = [
        c
        for c in first.claims
        if c.get("record_kind") == "agenda_index" and c.get("jurisdiction") == "Hialeah, FL"
    ]
    again = [
        c
        for c in second.claims
        if c.get("record_kind") == "agenda_index" and c.get("jurisdiction") == "Hialeah, FL"
    ]
    assert {r["external_id"] for r in mine} == {r["external_id"] for r in again}
