# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The nine P25.6 `promote` sources made real (P26.2 / SOURCES.2).

Every promoted source named its class ticket at disposition; each is filed into
the existing class connector (no bespoke adapters):

* legistar / primegov / civicclerk — the procurement connector's agenda-platform
  tenant path (§22.3, §23.6): tenants come from the published
  ``data/agenda_tenants.toml`` registry, an item becomes a Contract only through
  the reviewed matter-type patterns;
* sam_gov — the procurement connector's federal-opportunity path
  (``procurement_notice`` records, api_key from ``$SIG_SAM_GOV_KEY``, HG-09);
* courtlistener_recap — the accountability connector's targeted-lookup
  CourtListener path (known dockets only, SIG-INGEST-036/037);
* documentcloud — the records connector's document-index path (targeted document
  lookups, never the search listing);
* eyes_on_flock — the existing flock_portal connector (P11.1);
* openstates — the accountability connector's bill-index path (a pending bill is
  NOT a §11.14 LegalInstrument — index_only evidence links, §3.1);
* fbi_cde_agency_registry — the dedicated ``agency_registry`` connector (the ORI9
  identity substrate, §14.2).

The tests drive each over a committed fixture through the eight-stage framework
and pin the source→connector mapping, the live-target wiring, and the gate
verdict (the five GL-GATE-06 flips are green; documentcloud and
courtlistener_recap stay gated — per-document rights UNDETERMINED and
membership-agreement access respectively).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from connectors.live_targets import live_targets
from connectors.procurement import tenant_targets
from connectors.runner import (
    CONNECTOR_FOR_SOURCE,
    is_review_status_green,
    live_gate_reasons,
    run_connector_over_fixture,
)
from connectors.stages import ContentDrift

_FIX = Path(__file__).parent / "fixtures" / "promoted"

PROMOTED = (
    "civicclerk",
    "courtlistener_recap",
    "documentcloud",
    "eyes_on_flock",
    "fbi_cde_agency_registry",
    "legistar",
    "openstates",
    "primegov",
    "sam_gov",
)


# --- mapping + gate + live-target wiring ---------------------------------------


def test_every_promoted_source_is_connector_mapped() -> None:
    """AC: each of the 9 promoted sources routes through an existing class connector."""
    for source_id in PROMOTED:
        assert source_id in CONNECTOR_FOR_SOURCE, f"{source_id} has no connector mapping"


def test_promoted_gate_verdicts_are_honest() -> None:
    """The GL-GATE-06-resolved rows are green; the unresolved two stay refused."""
    green = {
        "civicclerk",
        "eyes_on_flock",
        "fbi_cde_agency_registry",
        "legistar",
        "openstates",
        "primegov",
        "sam_gov",
    }
    for source_id in green:
        assert is_review_status_green(source_id), (
            f"{source_id} should be green (GL-GATE-06 flip recorded)"
        )
    for source_id in ("documentcloud", "courtlistener_recap"):
        assert not is_review_status_green(source_id)
        reasons = live_gate_reasons(source_id)
        assert any("ingestion_permitted" in r for r in reasons)


def test_every_promoted_source_has_live_targets() -> None:
    """Every promoted source names real reviewed targets — never a homepage."""
    for source_id in PROMOTED:
        targets = live_targets(source_id)
        assert targets, f"{source_id} has no live_targets row"
        for target in targets:
            assert target["url"].startswith("https://")
            assert target.get("kind")


def test_agenda_platform_targets_come_from_the_tenant_registry() -> None:
    """The three agenda platforms resolve their targets from agenda_tenants.toml."""
    for platform in ("legistar", "primegov", "civicclerk"):
        targets = live_targets(platform)
        assert targets == tenant_targets(platform=platform)
        assert targets, f"{platform} has no registered tenants"
        for t in targets:
            assert t["platform"] == platform
            assert t["tenant_id"]


# --- legistar: InSite matters index → agenda_index + reviewed Contract --------


def _tenant_url(platform: str, tenant_id: str) -> str:
    for t in tenant_targets(platform=platform):
        if t["tenant_id"] == tenant_id:
            return str(t["url"])
    raise AssertionError(f"no {platform} tenant {tenant_id!r} registered")


def test_legistar_matters_index_over_fixture() -> None:
    report = run_connector_over_fixture(
        "procurement",
        "legistar",
        _FIX / "legistar_seattle_matters.json",
        media_type="application/json",
        kind="agenda_index",
        target_url=_tenant_url("legistar", "seattle_wa"),
    )
    index_rows = [c for c in report.claims if c.get("record_kind") == "agenda_index"]
    seattle = [r for r in index_rows if r.get("jurisdiction") == "City of Seattle, WA"]
    # All three fixture matters index under the Seattle tenant (the fixture is
    # replayed for the explicit target AND the registry-derived tenant target —
    # discover() reads its tenants from the published registry — so dedupe on
    # external_id).
    assert {r["external_id"] for r in seattle} == {"CB 120512", "C 2501", "Res 32199"}
    # Only the reviewed contract-family type name emits a Contract claim
    # (an ordinance/resolution is legislative business, never a contract — §3.1).
    contract_rows = [c for c in report.claims if c.get("predicate_id") == "contract"]
    assert contract_rows
    assert {c["external_id"] for c in contract_rows} == {"C 2501"}


def test_legistar_tenant_error_envelope_is_recorded_not_silent(tmp_path: Path) -> None:
    """An InSite 'client not provisioned' envelope is a tenant_api_error row (§3.1)."""
    fixture = tmp_path / "chicago_error.json"
    fixture.write_text(
        '{"Message": "LegistarConnectionString setting is not set up in InSite for'
        ' client chicago", "ExceptionMessage": "client not provisioned"}'
    )
    report = run_connector_over_fixture(
        "procurement",
        "legistar",
        fixture,
        media_type="application/json",
        kind="agenda_index",
        target_url=_tenant_url("legistar", "chicago_il"),
    )
    errors = [c for c in report.claims if c.get("record_kind") == "tenant_api_error"]
    assert errors, "a not-provisioned tenant envelope must be recorded loud"


def test_primegov_meeting_index_over_fixture() -> None:
    report = run_connector_over_fixture(
        "procurement",
        "primegov",
        _FIX / "primegov_lacity_search.json",
        media_type="application/json",
        kind="agenda_index",
        target_url=_tenant_url("primegov", "los_angeles_ca"),
    )
    index_rows = [
        c
        for c in report.claims
        if c.get("record_kind") == "agenda_index"
        and c.get("jurisdiction") == "City of Los Angeles, CA"
    ]
    # The fixture is replayed for the explicit target and the registry-derived
    # tenant target — dedupe on the meeting id.
    assert {r["external_id"] for r in index_rows} == {"5512", "5513"}
    assert all(r["platform"] == "primegov" for r in index_rows)


def test_civicclerk_events_index_over_fixture() -> None:
    report = run_connector_over_fixture(
        "procurement",
        "civicclerk",
        _FIX / "civicclerk_events_okc.json",
        media_type="application/json",
        kind="agenda_index",
        target_url=_tenant_url("civicclerk", "oklahoma_city_ok"),
    )
    index_rows = [
        c
        for c in report.claims
        if c.get("record_kind") == "agenda_index"
        and c.get("jurisdiction") == "City of Oklahoma City, OK"
    ]
    assert {r["external_id"] for r in index_rows} == {"8821", "8822"}


# --- sam_gov: opportunities → procurement_notice + reviewed lifecycle ---------


def test_sam_gov_opportunities_over_fixture() -> None:
    report = run_connector_over_fixture(
        "procurement",
        "sam_gov",
        _FIX / "sam_gov_opportunities.json",
        media_type="application/json",
        kind="opportunity_search",
    )
    notices = [c for c in report.claims if c.get("record_kind") == "procurement_notice"]
    assert {n["external_id"] for n in notices} == {"a1b2c3d4e5f60001", "a1b2c3d4e5f60002"}
    transitions = [c for c in report.claims if c.get("predicate_id") == "lifecycle_transition"]
    states = {c["value"]["state"] for c in transitions}
    # Solicitation → rfp_issued; Award Notice → awarded (the reviewed notice_map).
    assert states == {"rfp_issued", "awarded"}


# --- courtlistener_recap: targeted docket lookup → legal_proceeding -----------


def test_courtlistener_docket_lookup_over_fixture() -> None:
    report = run_connector_over_fixture(
        "accountability",
        "courtlistener_recap",
        _FIX / "courtlistener_docket_5.json",
        media_type="application/json",
        kind="docket_lookup",
        target_url="https://www.courtlistener.com/api/rest/v4/dockets/5/",
    )
    proceedings = [c for c in report.claims if c.get("record_kind") == "legal_proceeding"]
    assert len(proceedings) == 1
    assert proceedings[0]["external_id"] == "5"


def test_courtlistener_refuses_collection_and_crawl_targets() -> None:
    """SIG-INGEST-036/037: enumeration/crawl targets are refused at discovery."""
    from connectors.accountability import assert_targeted_lookup

    with pytest.raises(Exception, match="crawl|enumeration|specific"):
        assert_targeted_lookup({"mode": "crawl", "url": "https://x.test/"})
    with pytest.raises(Exception, match="pagination|enumeration"):
        assert_targeted_lookup({"url": "https://x.test/dockets/", "page": 2})
    with pytest.raises(Exception, match="collection|specific"):
        assert_targeted_lookup({"url": "https://www.courtlistener.com/api/rest/v4/dockets/"})
    # A docket-id lookup passes.
    assert_targeted_lookup(
        {
            "url": "https://www.courtlistener.com/api/rest/v4/dockets/5/",
            "docket_id": "5",
        }
    )


# --- documentcloud: targeted document lookup → document_index + artifact ------


def test_documentcloud_document_lookup_over_fixture() -> None:
    report = run_connector_over_fixture(
        "records",
        "documentcloud",
        _FIX / "documentcloud_doc_20504557.json",
        media_type="application/json",
        kind="document_lookup",
        target_url="https://api.www.documentcloud.org/api/documents/20504557/",
    )
    index = [c for c in report.claims if c.get("record_kind") == "document_index"]
    assert len(index) == 1
    assert index[0]["external_id"] == "20504557"
    artifacts = [c for c in report.claims if c.get("record_kind") == "evidence_artifact"]
    assert artifacts, "a document lookup yields a released-document artifact row"


def test_documentcloud_refuses_the_search_listing() -> None:
    """The search/collection endpoint is enumeration — refused (SIG-INGEST-036)."""
    from connectors.records import assert_targeted_lookup

    with pytest.raises(Exception, match="listing|enumeration"):
        assert_targeted_lookup({"url": "https://api.www.documentcloud.org/api/documents/search"})
    # A single-document lookup passes.
    assert_targeted_lookup(
        {
            "url": "https://api.www.documentcloud.org/api/documents/20504557/",
            "external_id": "20504557",
        }
    )


# --- eyes_on_flock: the existing flock_portal connector over its fixture ------


def test_eyes_on_flock_snapshot_over_committed_fixture() -> None:
    report = run_connector_over_fixture(
        "flock_portal",
        "eyes_on_flock",
        Path(__file__).parent / "fixtures" / "flock_portal" / "snapshot_2026_09.json",
        media_type="application/json",
        kind="portal_json",
    )
    assert report.claims, "the portal snapshot fixture yields portal-layer claims"


# --- openstates: bill index → index_only evidence links (never a statute) -----


def test_openstates_bill_index_over_fixture() -> None:
    report = run_connector_over_fixture(
        "accountability",
        "openstates",
        _FIX / "openstates_bills_ok.json",
        media_type="application/json",
        kind="bill_search",
        target_url="https://v3.openstates.org/bills?jurisdiction=ok&q=alpr&per_page=10",
    )
    links = [c for c in report.claims if c.get("record_kind") == "evidence_link"]
    assert len(links) == 2
    assert all(link["index_only"] for link in links)
    # The official legislature page is the primary_record ref; the OpenStates
    # page is the fallback.
    assert all(link["source_class"] == "primary_record" for link in links)
    assert {link["bill_identifier"] for link in links} == {"HB 3101", "SB 2200"}
    # A bill is never normalized into a LegalInstrument claim (§3.1).
    assert not any(c.get("predicate_id") in {"legal_instrument", "statute"} for c in report.claims)


# --- fbi_cde_agency_registry: the ORI9 identity substrate ---------------------


def test_fbi_cde_agency_registry_over_fixture() -> None:
    report = run_connector_over_fixture(
        "agency_registry",
        "fbi_cde_agency_registry",
        _FIX / "fbi_cde_agencies_ok.json",
        media_type="application/json",
        kind="agency_registry",
    )
    entries = [c for c in report.claims if c.get("record_kind") == "agency_registry_entry"]
    assert len(entries) == 3
    oris = {e["external_id"] for e in entries}
    assert oris == {"OK0360400", "OK0360100", "OK0520200"}
    # The ORI is a candidate identifier for the identity layer — never resolved.
    ori_claims = [c for c in report.claims if c.get("predicate_id") == "agency_ori9"]
    assert len(ori_claims) == 3
    assert all(c["candidate_identifier"]["scheme"] == "us.fbi.ori" for c in ori_claims)


def test_fbi_cde_agency_registry_drift_is_loud(tmp_path: Path) -> None:
    """An agency row without an ori is ContentDrift, never silently dropped."""
    fixture = tmp_path / "drift.json"
    fixture.write_text('{"KAY": [{"agency_name": "No ORI Agency"}]}')
    with pytest.raises(ContentDrift):
        run_connector_over_fixture(
            "agency_registry",
            "fbi_cde_agency_registry",
            fixture,
            media_type="application/json",
            kind="agency_registry",
        )
