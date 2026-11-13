# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.52 (R11-ACQ-25): the document-list page family — an index-page ->
PDF/HTML enumerator for public pages with no platform — over committed
fixtures (no network).

Covers: the 8-target committed inventory expansion, the four cooperative
contract-document seats (Florida Buy, WSIPC RFP 24-01, NERIC's service page,
the NASPO portfolio — pointer records, contract mints, RB-07 facts+citations),
the Illinois GATA award table with the person-shaped grantee rejection, the
Massachusetts capital line per-FY allocations, the Ohio OCJS RFP PDF lane, the
Massachusetts EOPSS release recipient lane, the gated-source live refusals,
ContentDrift on a markerless page, and the +0 shadow replay determinism.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from connectors.document_list import (
    DocumentListConnector,
    ForbiddenFieldError,
    PredicateNotAllowed,
    assert_no_forbidden_columns,
    assert_predicate_allowed,
    document_list_targets,
    forbidden_field_tokens,
    forbidden_predicate_genres,
    load_inventory,
    vocab,
)
from connectors.loader import IngestionNotPermitted, assert_loadable
from connectors.net import PoliteFetcher, RobotsResult
from connectors.pipeline import run
from connectors.registry import get
from connectors.stages import (
    ContentDrift,
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun

_FIX = Path(__file__).resolve().parent / "fixtures" / "p37_52"
_RETRIEVED = datetime(2026, 11, 13, tzinfo=UTC)
_ALLOW_ALL = "User-agent: *\nAllow: /\n"

SEATS = [
    "camreg_ma_massachusetts_capital",
    "grant_il_illinois_gata_csfa",
    "grant_ma_massachusetts_law_enforcement",
    "grant_oh_ohio_criminal_justice",
    "procportal_fl_florida_buy_cooperative",
    "procportal_ny_northeastern_regional",
    "procportal_us_naspo_valuepoint_portfolio",
    "procportal_wa_wsipc_rfp_24",
]

FIXTURE_FOR_TARGET = {
    "florida_buy_gaggle_contract": "florida_buy_gaggle.html",
    "wsipc_rfp_24_01_gaggle": "wsipc_rfp_24_01.html",
    "neric_gaggle_service_page": "neric_gaggle_service.html",
    "naspo_portfolio_public_safety_video": "naspo_portfolio.html",
    "ma_capital_line_s027_bwc": "ma_capital_line_s027.html",
    "il_gata_csfa_3496_awardlist": "il_gata_awardlist.html",
    "oh_ocjs_bwc_rfp_fy2026": "oh_ocjs_rfp_fy2026.pdf",
    "ma_eopss_bwc_final_round": "ma_eopss_release.html",
}


class MapTransport:
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


def _resp(url: str, body: bytes, media: str = "text/html") -> FetchResult:
    return FetchResult(url=url, status=200, body=body, media_type=media, retrieved_at=_RETRIEVED)


def _ctx(source_id: str, targets: list[dict[str, Any]], responses: Mapping[str, FetchResult]):
    connector = DocumentListConnector()
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


def _run(source_id: str, fixture: str, target_id: str):
    targets = [t for t in document_list_targets(source_id) if t["id"] == target_id]
    assert targets, f"{source_id}:{target_id} must resolve inventory targets"
    body = _FIX.joinpath(fixture).read_bytes()
    media = "application/pdf" if fixture.endswith(".pdf") else "text/html"
    responses = {t["url"]: _resp(t["url"], body, media) for t in targets}
    connector, ctx = _ctx(source_id, targets, responses)
    return run(connector, ctx), ctx


def test_all_8_targets_expand():
    targets = document_list_targets()
    assert len(targets) == 8
    assert {t["source"] for t in targets} == set(SEATS)
    for seat in SEATS:
        by_source = document_list_targets(seat)
        assert len(by_source) == 1
        assert by_source[0]["kind"] in {"doclist_html", "doclist_pdf"}
    inv = load_inventory()
    assert len(inv.targets) == 8
    assert [t.id for t in inv.targets] == sorted(t.id for t in inv.targets)


def test_vocab_and_allowlist_gates():
    assert vocab()["schema"] == "sig.document-list-vocab/1"
    assert "deployment_exists" in forbidden_predicate_genres()
    assert "officer" in forbidden_field_tokens()
    with pytest.raises(PredicateNotAllowed):
        assert_predicate_allowed("deployment_exists")
    with pytest.raises(ForbiddenFieldError):
        assert_no_forbidden_columns(["Award ID", "Officer Name"], source_id="x")


def test_florida_buy_contract_docs_emit():
    result, _ = _run(
        "procportal_fl_florida_buy_cooperative",
        FIXTURE_FOR_TARGET["florida_buy_gaggle_contract"],
        "florida_buy_gaggle_contract",
    )
    contracts = [c for c in result.claims if c["record_kind"] == "contract"]
    assert len(contracts) == 1
    assert (
        contracts[0]["subject_id"]
        == "contract:procportal_fl_florida_buy_cooperative:florida-buy-gaggle-net-inc"
    )
    vendors = [c for c in result.claims if c.get("predicate_id") == "vendor"]
    assert {c["value"] for c in vendors} == {"Gaggle.Net, Inc."}
    assert all(c["candidate_identifier"]["scheme"] == "procurement.org_name" for c in vendors)
    buyers = [c for c in result.claims if c.get("predicate_id") == "buyer"]
    assert {c["value"] for c in buyers} == {"Panhandle Area Educational Consortium (Florida Buy)"}
    # Seven served contract documents enumerate as pointers — the /about nav
    # link is filtered out by the committed link regex.
    pointers = [c for c in result.claims if c["record_kind"] == "document_list_document"]
    assert len(pointers) == 7
    docs = [c for c in result.claims if c.get("predicate_id") == "document"]
    doc_urls = {c["value"] for c in docs if "value" in c}
    assert "https://floridabuy.paec.org/documents/gaggle-agenda.pdf" in doc_urls
    assert "https://floridabuy.paec.org/documents/gaggle-2025-renewal.pdf" in doc_urls
    assert not any("about" in str(u) for u in doc_urls)
    # Jurisdiction key set on the pointer claims (US state scope).
    jur = [c for c in result.claims if c.get("predicate_id") == "jurisdiction"]
    assert jur and all(c["value"] == "us.state_abbr:FL" for c in jur)


def test_wsipc_facts_citations_only():
    result, _ = _run(
        "procportal_wa_wsipc_rfp_24",
        FIXTURE_FOR_TARGET["wsipc_rfp_24_01_gaggle"],
        "wsipc_rfp_24_01_gaggle",
    )
    contracts = [c for c in result.claims if c["record_kind"] == "contract"]
    assert len(contracts) == 1
    assert contracts[0]["subject_id"] == "contract:procportal_wa_wsipc_rfp_24:wsipc-rfp-24-01"
    pointers = [c for c in result.claims if c["record_kind"] == "document_list_document"]
    assert len(pointers) == 8
    # RB-07 — facts and citations only: no verbatim description claim anywhere.
    assert not any(c.get("predicate_id") == "description" for c in result.claims)


def test_neric_service_page_emit():
    result, _ = _run(
        "procportal_ny_northeastern_regional",
        FIXTURE_FOR_TARGET["neric_gaggle_service_page"],
        "neric_gaggle_service_page",
    )
    # A service OFFERING — never an executed contract.
    assert not any(c["record_kind"] == "contract" for c in result.claims)
    pages = [c for c in result.claims if c["record_kind"] == "document_list_document"]
    assert len(pages) == 3  # the page record + 2 enumerated document pointers
    vendors = [c for c in result.claims if c.get("predicate_id") == "vendor"]
    assert {c["value"] for c in vendors} == {"Gaggle"}
    titles = [c for c in result.claims if c.get("predicate_id") == "title"]
    assert any("NERIC Gaggle service offering" in str(c["value"]) for c in titles)


def test_naspo_portfolio_emit():
    result, _ = _run(
        "procportal_us_naspo_valuepoint_portfolio",
        FIXTURE_FOR_TARGET["naspo_portfolio_public_safety_video"],
        "naspo_portfolio_public_safety_video",
    )
    contracts = [c for c in result.claims if c["record_kind"] == "contract"]
    assert len(contracts) == 1
    pointers = [c for c in result.claims if c["record_kind"] == "document_list_document"]
    assert len(pointers) == 4  # 2 supplier pages + addenda pdf + terms pdf
    docs = [c for c in result.claims if c.get("predicate_id") == "document"]
    assert {
        "https://www.naspovaluepoint.org/suppliers/axon-enterprise-inc",
        "https://www.naspovaluepoint.org/suppliers/motorola-solutions-inc",
    } <= {c["value"] for c in docs if "value" in c}
    # RB-07 — facts and citations only.
    assert not any(c.get("predicate_id") == "description" for c in result.claims)


def test_ma_capital_line_emit():
    result, _ = _run(
        "camreg_ma_massachusetts_capital",
        FIXTURE_FOR_TARGET["ma_capital_line_s027_bwc"],
        "ma_capital_line_s027_bwc",
    )
    programs = [c for c in result.claims if c["record_kind"] == "funding_instrument"]
    assert len(programs) == 1
    assert programs[0]["subject_id"].startswith(
        "funding_instrument:camreg_ma_massachusetts_capital:ma-capital-s027-bwc"
    )
    awards = [c for c in result.claims if c["record_kind"] == "grant_award"]
    assert len(awards) == 5  # one allocation row per served fiscal year
    amounts = [c for c in result.claims if c.get("predicate_id") == "amount"]
    served = {c["value"] for c in amounts}
    assert "3500000" in served or "$3,500,000" in served
    names = [c for c in result.claims if c.get("predicate_id") == "funding_program_name"]
    assert {c["value"] for c in names} == {"Municipal Body-Worn Camera Grant Program"}
    # Plan-level allocations are never recipient rows — the funder rides the
    # recipient field as the allocating body.
    recipients = [c for c in result.claims if c.get("predicate_id") == "recipient"]
    assert {c["value"] for c in recipients} == {
        "Commonwealth of Massachusetts, Executive Office for Administration and Finance"
    }


def test_il_gata_award_table_emit_and_person_drop():
    result, _ = _run(
        "grant_il_illinois_gata_csfa",
        FIXTURE_FOR_TARGET["il_gata_csfa_3496_awardlist"],
        "il_gata_csfa_3496_awardlist",
    )
    awards = [c for c in result.claims if c["record_kind"] == "grant_award"]
    assert len(awards) == 3
    ids = {c["external_id"] for c in awards}
    assert ids == {"26-3496-001", "26-3496-002", "26-3496-003"}
    recipients = [c for c in result.claims if c.get("predicate_id") == "recipient"]
    assert {c["value"] for c in recipients} == {
        "City of Springfield Police Department",
        "County of Madison Sheriff's Office",
        "Village of Riverton Police Department",
    }
    assert all(c["candidate_identifier"]["scheme"] == "procurement.org_name" for c in recipients)
    # The person-shaped grantee mints no subject and lands no claim — the
    # recorded rejection carries the reason + field names, never the name.
    rejected = [c for c in result.claims if c["record_kind"] == "document_list_rejected"]
    assert len(rejected) == 1
    assert rejected[0]["rejection_reason"] == "person_shaped_recipient"
    assert "John Smith" not in json.dumps(result.claims)


def test_oh_ocjs_rfp_pdf_emit():
    result, _ = _run(
        "grant_oh_ohio_criminal_justice",
        FIXTURE_FOR_TARGET["oh_ocjs_bwc_rfp_fy2026"],
        "oh_ocjs_bwc_rfp_fy2026",
    )
    programs = [c for c in result.claims if c["record_kind"] == "funding_instrument"]
    assert len(programs) == 1
    assert programs[0]["subject_id"].startswith(
        "funding_instrument:grant_oh_ohio_criminal_justice:oh-ocjs-bwc-grant"
    )
    # The RFP serves no recipient list — no award rows can mint by construction.
    assert not any(c["record_kind"] == "grant_award" for c in result.claims)
    descs = [c for c in result.claims if c.get("predicate_id") == "description"]
    assert descs and "average award amount for FY2025 was $34,694.52" in str(descs[0]["value"])
    windows = [c for c in result.claims if c.get("predicate_id") == "period"]
    assert {c["value"] for c in windows} == {
        "FY2026",
        "2025-07-01..2027-06-30",  # future-ok: real-world: the RFP's served award window
    }


def test_ma_eopss_release_emit():
    result, _ = _run(
        "grant_ma_massachusetts_law_enforcement",
        FIXTURE_FOR_TARGET["ma_eopss_bwc_final_round"],
        "ma_eopss_bwc_final_round",
    )
    programs = [c for c in result.claims if c["record_kind"] == "funding_instrument"]
    assert len(programs) == 1
    awards = [c for c in result.claims if c["record_kind"] == "grant_award"]
    assert len(awards) == 3
    recipients = [c for c in result.claims if c.get("predicate_id") == "recipient"]
    assert {c["value"] for c in recipients} == {
        "Boston Police Department",
        "Springfield Police Department",
        "Worcester Police Department",
    }
    # The intro <li> carrying the list marker enumerates no award.
    assert not any("32 local police departments" in str(c.get("value", "")) for c in result.claims)


def test_drift_fails_loud():
    targets = [t for t in document_list_targets("procportal_fl_florida_buy_cooperative")]
    url = targets[0]["url"]
    body = _FIX.joinpath("drift.html").read_bytes()
    responses = {url: _resp(url, body)}
    connector, ctx = _ctx("procportal_fl_florida_buy_cooperative", targets, responses)
    with pytest.raises(ContentDrift):
        run(connector, ctx)


def test_off_host_target_refused():
    """A target URL off the committed host set refuses before egress."""
    connector = DocumentListConnector()
    source = dataclasses.replace(
        get("procportal_fl_florida_buy_cooperative"), ingestion_permitted=True
    )
    ctx = RunContext(
        source=source,
        run=IngestRun(connector.name, connector.version, "test", "r1", "v1", ()),
        fetcher=PoliteFetcher(
            connector_name=connector.name,
            connector_version=connector.version,
            transport=MapTransport({}),
        ),
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": [{"id": "x", "url": "https://evil.example.com/x"}]},
    )
    with pytest.raises(ContentDrift):
        connector.fetch(ctx, {"id": "x", "url": "https://evil.example.com/x"})


def test_runner_and_live_targets_wired():
    """Every seat is connector-mapped and its live_targets delegates to the inventory."""
    from connectors.live_targets import live_targets
    from connectors.runner import CONNECTOR_FOR_SOURCE

    for seat in SEATS:
        assert CONNECTOR_FOR_SOURCE[seat] == "document_list"
        targets = live_targets(seat)
        assert targets, f"{seat} must expand live targets from the committed inventory"
        assert all(t["kind"] in {"doclist_html", "doclist_pdf"} for t in targets)


@pytest.mark.parametrize("source_id", sorted(SEATS))
def test_gated_source_refused_live(source_id):
    source = get(source_id)
    assert source.ingestion_permitted is False
    with pytest.raises(IngestionNotPermitted):
        assert_loadable(source)


def test_second_replay_identical():
    r1, _ = _run(
        "grant_il_illinois_gata_csfa",
        FIXTURE_FOR_TARGET["il_gata_csfa_3496_awardlist"],
        "il_gata_csfa_3496_awardlist",
    )
    r2, _ = _run(
        "grant_il_illinois_gata_csfa",
        FIXTURE_FOR_TARGET["il_gata_csfa_3496_awardlist"],
        "il_gata_csfa_3496_awardlist",
    )
    key = lambda c: (c["subject_id"], c.get("predicate_id"), str(c.get("value", "")))  # noqa: E731
    assert sorted(map(key, r1.claims)) == sorted(map(key, r2.claims))
