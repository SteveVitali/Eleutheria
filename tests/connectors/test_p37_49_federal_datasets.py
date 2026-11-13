# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.49 (R11-ACQ-21): the federal datasets family — the fetch-and-parse
helper's four lanes (``federal_index`` link enumeration, ``federal_json``
Federal Register documents, ``federal_csv`` OMB AI inventory, and the
resolved ``federal_xlsx`` ICE 287(g) roster) over committed fixtures (no
network).

Covers: the 13-target committed inventory expansion, the Federal Register
document emit, the index-pointer emits (wiretap / DHS / NCES / ICE monthly —
pointers only, contents never read), the landing-page → dated-workbook
``discover_more`` resolve + roster emit, the person-level column refusal,
the person-shaped agency drop, the gated-source live refusals, and the +0
shadow replay determinism.
"""

from __future__ import annotations

import dataclasses
import io
import zipfile
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from connectors.federal_datasets import (
    FederalDatasetsConnector,
    ForbiddenFieldError,
    assert_no_forbidden_columns,
    federal_dataset_targets,
    load_inventory,
)
from connectors.loader import IngestionNotPermitted, assert_loadable
from connectors.net import PoliteFetcher, RobotsResult
from connectors.pipeline import run
from connectors.registry import get
from connectors.stages import (
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun

_FIX = Path(__file__).resolve().parent / "fixtures" / "p37_49"
_RETRIEVED = datetime(2026, 11, 13, tzinfo=UTC)
_ALLOW_ALL = "User-agent: *\nAllow: /\n"

SEATS = [
    "camreg_us_nces_school_survey_on_crime",
    "legis_us_federal_register_api",
    "statrep_tx_south_padre_island_faa",
    "statrep_us_2024_federal_agency",
    "statrep_us_dhs_ai_use",
    "statrep_us_ice_287_monthly",
    "statrep_us_ice_287_participating",
    "statrep_us_wiretap_summary_tables",
]


def _xlsx(rows: list[list[str]]) -> bytes:
    """Build a minimal shared-strings XLSX (stdlib — same lane as P37.48)."""
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    shared: list[str] = []
    idx: dict[str, int] = {}

    def si(v: str) -> int:
        if v not in idx:
            idx[v] = len(shared)
            shared.append(v)
        return idx[v]

    col_names = "ABCDEFGHIJ"
    sheet_rows = []
    for r, row in enumerate(rows, 1):
        cells = "".join(
            f'<c r="{col_names[i]}{r}" t="s"><v>{si(str(v))}</v></c>' for i, v in enumerate(row)
        )
        sheet_rows.append(f'<row r="{r}">{cells}</row>')
    sheet = (
        f'<?xml version="1.0"?><worksheet xmlns="{ns}">'
        f"<sheetData>{''.join(sheet_rows)}</sheetData></worksheet>"
    )
    strings = (
        f'<?xml version="1.0"?><sst xmlns="{ns}" count="{len(shared)}">'
        + "".join(f"<si><t>{s}</t></si>" for s in shared)
        + "</sst>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("xl/workbook.xml", '<?xml version="1.0"?><workbook/>')
        zf.writestr("xl/worksheets/sheet1.xml", sheet)
        zf.writestr("xl/sharedStrings.xml", strings)
    return buf.getvalue()


_ROSTER = _xlsx(
    [
        [
            "STATE",
            "LAW ENFORCEMENT AGENCY",
            "TYPE",
            "COUNTY",
            "SUPPORT TYPE",
            "SIGNED",
            "MOA",
            "ADDENDUM",
        ],
        [
            "TX",
            "CAMERON COUNTY SHERIFF'S OFFICE",
            "County ",
            "Cameron",
            "Jail Enforcement Model ",
            "6/1/2025",
            "",
            "",
        ],
        [
            "FL",
            "CITY OF JACKSONVILLE",
            "City",
            "Duval",
            "Warrant Service Officer ",
            "3/15/2025",
            "",
            "",
        ],
    ]
)


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


def _resp(url: str, body: bytes, media: str = "application/json") -> FetchResult:
    return FetchResult(url=url, status=200, body=body, media_type=media, retrieved_at=_RETRIEVED)


def _ctx(source_id: str, targets: list[dict[str, Any]], responses: Mapping[str, FetchResult]):
    connector = FederalDatasetsConnector()
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


def _run(source_id: str, fixture: str, target_id: str, **kw):
    targets = [t for t in federal_dataset_targets(source_id) if t["id"] == target_id]
    assert targets, f"{source_id}:{target_id} must resolve inventory targets"
    body = kw.pop("body", None)
    media = "text/html" if targets[0]["kind"] == "federal_index" else "application/json"
    payload = _FIX.joinpath(fixture).read_bytes() if body is None else body
    responses = {t["url"]: _resp(t["url"], payload, media=media) for t in targets}
    responses.update(kw.pop("extra_responses", {}))
    connector, ctx = _ctx(source_id, targets, responses)
    return run(connector, ctx), ctx


def test_all_13_targets_expand():
    targets = federal_dataset_targets()
    assert len(targets) == 13
    assert {t["source"] for t in targets} == set(SEATS)
    by_source = {s: [t["id"] for t in federal_dataset_targets(s)] for s in SEATS}
    assert len(by_source["legis_us_federal_register_api"]) == 6
    assert len(by_source["statrep_tx_south_padre_island_faa"]) == 1
    inv = load_inventory()
    assert len(inv.targets) == 13


def test_fr_document_emit():
    result, _ = _run("statrep_tx_south_padre_island_faa", "fr_documents.json", "fr_term_aerostat")
    claims = result.claims
    subjects = {c["subject_id"] for c in claims if c["record_kind"] == "federal_register_document"}
    assert subjects == {
        "federal_register_document:statrep_tx_south_padre_island_faa:2025-16236",
        "federal_register_document:statrep_tx_south_padre_island_faa:2024-28716",
    }
    titles = [c for c in claims if c["predicate_id"] == "title"]
    assert any("South Padre Island" in str(c["value"]) for c in titles)
    cites = [c for c in claims if c["predicate_id"] == "citation"]
    assert {c["value"] for c in cites} == {"90 FR 41111", "89 FR 96984"}
    pubs = [c for c in claims if c["predicate_id"] == "published_by"]
    assert any("Federal Aviation Administration" in str(c["value"]) for c in pubs)
    assert all(
        c["evidence_genre"] == "connector_run" for c in claims if c["record_kind"] == "claim"
    )


def test_wiretap_index_pointer_emit():
    result, _ = _run(
        "statrep_us_wiretap_summary_tables",
        "wiretap_report.html",
        "uscourts_wiretap_report_index",
    )
    docs = [c for c in result.claims if c["record_kind"] == "federal_document"]
    assert len(docs) == 4  # wire-1, wire-2, wire-7, wire-a1
    urls = {c.get("external_id") for c in docs}
    assert {"wire-1", "wire-2", "wire-7", "wire-a1"} <= urls
    # Pointers only — the Wire-2 judge table is enumerated, never extracted.
    assert not any(c["predicate_id"] == "usage_count" for c in result.claims)


def test_dhs_index_pointer_emit():
    result, _ = _run("statrep_us_dhs_ai_use", "dhs_inventory.html", "dhs_ai_inventory_index")
    docs = [c for c in result.claims if c["record_kind"] == "federal_document"]
    assert len(docs) == 3


def test_nces_index_pointer_emit():
    result, _ = _run(
        "camreg_us_nces_school_survey_on_crime",
        "nces_dataset.html",
        "nces_ssocs_dataset_index",
    )
    docs = [c for c in result.claims if c["record_kind"] == "federal_document"]
    assert len(docs) == 2


def test_ice_monthly_pointer_only():
    result, _ = _run(
        "statrep_us_ice_287_monthly", "ice_287g_landing.html", "ice_287g_monthly_index"
    )
    docs = [c for c in result.claims if c["record_kind"] == "federal_document"]
    assert {c.get("external_id") for c in docs} == {
        "monthlyEncounterSep2026.pdf",
        "monthlyEncounterAug2026.pdf",
    }
    # S3: no per-encounter or person-level row can exist — pointers only.
    assert not any(c["predicate_id"] in ("usage_count", "enforcement_count") for c in result.claims)


def test_ice_287g_resolve_and_roster_emit():
    """The landing page resolves the dated workbook; the roster emits agencies."""
    source_id = "statrep_us_ice_287_participating"
    targets = federal_dataset_targets(source_id)
    landing_url = targets[0]["url"]
    xlsx_url = (
        "https://www.ice.gov/doclib/about/offices/ero/287g/participatingAgencies09282026.xlsx"
    )
    responses = {
        landing_url: _resp(
            landing_url, _FIX.joinpath("ice_287g_landing.html").read_bytes(), media="text/html"
        ),
        xlsx_url: _resp(xlsx_url, _ROSTER, media="application/vnd.ms-excel"),
    }
    connector, ctx = _ctx(source_id, targets, responses)
    result = run(connector, ctx)
    assert xlsx_url in ctx.resolved_targets  # the dated file was resolved, not pinned
    entries = [c for c in result.claims if c["record_kind"] == "agency_registry_entry"]
    assert len(entries) == 2
    names = [c for c in result.claims if c["predicate_id"] == "agency_name"]
    assert any("CAMERON COUNTY" in str(c["value"]) for c in names)
    states = [c for c in result.claims if c["predicate_id"] == "agency_state"]
    assert {c["value"] for c in states} == {"TX", "FL"}
    cands = [c for c in states if c.get("candidate_identifier")]
    assert all(c["candidate_identifier"]["scheme"] == "us.state_abbr" for c in cands)


def test_ai_inventory_csv_emit():
    result, _ = _run(
        "statrep_us_2024_federal_agency", "omb_ai_inventory.csv", "omb_ai_inventory_2024_csv"
    )
    cases = [c for c in result.claims if c["record_kind"] == "ai_use_case"]
    assert len(cases) == 3
    assert all("ai_use_case:statrep_us_2024_federal_agency:" in c["subject_id"] for c in cases)
    topics = [c for c in result.claims if c["predicate_id"] == "technology_category"]
    assert {c["value"] for c in topics} == {"Law & Justice", "Mission-Enabling"}
    stages = [c for c in result.claims if c["predicate_id"] == "in_use"]
    assert {c["value"] for c in stages} == {
        "Implementation and Assessment",
        "Initiated",
    }


def test_forbidden_column_refusal():
    with pytest.raises(ForbiddenFieldError):
        assert_no_forbidden_columns(["AGENCY", "JUDGE NAME", "COUNT"], source_id="x")


def test_person_shaped_agency_dropped():
    """A person-shaped roster agency name mints no subject — recorded rejection."""
    roster = _xlsx(
        [
            [
                "STATE",
                "LAW ENFORCEMENT AGENCY",
                "TYPE",
                "COUNTY",
                "SUPPORT TYPE",
                "SIGNED",
                "MOA",
                "ADDENDUM",
            ],
            ["TX", "SMITH  JOHN", "County", "Travis", "Jail Enforcement Model", "1/1/2025", "", ""],
            [
                "TX",
                "TRAVIS COUNTY SHERIFF'S OFFICE",
                "County",
                "Travis",
                "Jail Enforcement Model",
                "1/1/2025",
                "",
                "",
            ],
        ]
    )
    source_id = "statrep_us_ice_287_participating"
    targets = federal_dataset_targets(source_id)
    landing_url = targets[0]["url"]
    xlsx_url = (
        "https://www.ice.gov/doclib/about/offices/ero/287g/participatingAgencies09282026.xlsx"
    )
    responses = {
        landing_url: _resp(
            landing_url, _FIX.joinpath("ice_287g_landing.html").read_bytes(), media="text/html"
        ),
        xlsx_url: _resp(xlsx_url, roster, media="application/vnd.ms-excel"),
    }
    connector, ctx = _ctx(source_id, targets, responses)
    result = run(connector, ctx)
    entries = [c for c in result.claims if c["record_kind"] == "agency_registry_entry"]
    assert len(entries) == 1
    assert not any("SMITH" in c.get("subject_id", "") for c in result.claims)
    rejected = [c for c in result.claims if c.get("record_kind") == "federal_record_rejected"]
    assert rejected


@pytest.mark.parametrize("source_id", sorted(SEATS))
def test_gated_source_refused_live(source_id):
    source = get(source_id)
    assert source.ingestion_permitted is False
    with pytest.raises(IngestionNotPermitted):
        assert_loadable(source)


def test_second_replay_identical():
    r1, _ = _run("statrep_tx_south_padre_island_faa", "fr_documents.json", "fr_term_aerostat")
    r2, _ = _run("statrep_tx_south_padre_island_faa", "fr_documents.json", "fr_term_aerostat")
    c1 = sorted((c["subject_id"], c["predicate_id"], str(c.get("value", ""))) for c in r1.claims)
    c2 = sorted((c["subject_id"], c["predicate_id"], str(c.get("value", ""))) for c in r2.claims)
    assert c1 == c2
