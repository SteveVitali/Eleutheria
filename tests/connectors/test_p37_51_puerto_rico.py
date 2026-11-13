# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.51 (R11-ACQ-24): the Puerto Rico territorial family — the SUTRA
title-phrase search lane, the SUTRA measure detail pages and the OCPR
contract-registry index (with the S7 natural-person contractor screen)
over committed fixtures (no network).

Covers: the 11-target committed inventory expansion, the SUTRA index emit
(measure records + the truncated page outcome), the SUTRA detail emit
(events + document pointers), the OCPR fiscal-year pointer lane, the
results-table contract emit with the person-shaped contractor drop, the
gated-source live refusals, ContentDrift on a markerless page, and the +0
shadow replay determinism.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from connectors.loader import IngestionNotPermitted, assert_loadable
from connectors.net import PoliteFetcher, RobotsResult
from connectors.pipeline import run
from connectors.puerto_rico import (
    ForbiddenFieldError,
    PuertoRicoConnector,
    assert_no_forbidden_columns,
    load_inventory,
    puerto_rico_targets,
)
from connectors.registry import get
from connectors.stages import (
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun

_FIX = Path(__file__).resolve().parent / "fixtures" / "p37_51"
_RETRIEVED = datetime(2026, 11, 13, tzinfo=UTC)
_ALLOW_ALL = "User-agent: *\nAllow: /\n"

SEATS = [
    "legis_pr_pc0489_ley_del",
    "legis_pr_pc0560_plan_de",
    "legis_pr_rc0740_investigaci_sobre",
    "legis_pr_rc0787_resoluci_de",
    "legis_pr_rcs0198_resoluci_conjunta",
    "legis_pr_rs0604_resoluci_del",
    "legis_pr_sistema_nico_de",
    "procportal_pr_consulta_del_registro",
]


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
    connector = PuertoRicoConnector()
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
    targets = [t for t in puerto_rico_targets(source_id) if t["id"] == target_id]
    assert targets, f"{source_id}:{target_id} must resolve inventory targets"
    body = _FIX.joinpath(fixture).read_bytes()
    responses = {t["url"]: _resp(t["url"], body) for t in targets}
    connector, ctx = _ctx(source_id, targets, responses)
    return run(connector, ctx), ctx


def test_all_11_targets_expand():
    targets = puerto_rico_targets()
    assert len(targets) == 11
    assert {t["source"] for t in targets} == set(SEATS)
    by_source = {s: [t["id"] for t in puerto_rico_targets(s)] for s in SEATS}
    assert len(by_source["legis_pr_sistema_nico_de"]) == 4
    assert len(by_source["procportal_pr_consulta_del_registro"]) == 1
    for seat in SEATS[0:6]:
        assert len(by_source[seat]) == 1
    inv = load_inventory()
    assert len(inv.targets) == 11


def test_sutra_search_emit():
    result, _ = _run(
        "legis_pr_sistema_nico_de", "sutra_search_vigilancia.html", "sutra_search_vigilancia"
    )
    measures = [c for c in result.claims if c["record_kind"] == "sutra_measure"]
    assert len(measures) == 5
    subjects = {c["subject_id"] for c in measures}
    assert "sutra_measure:154899" in subjects  # PC0489
    assert "sutra_measure:155376" in subjects  # PC0560
    ids = {c.get("external_id") for c in measures}
    assert {"152507", "152720", "153031", "154899", "155376"} == ids
    titles = [c for c in result.claims if c.get("predicate_id") == "bill_title"]
    assert any("Vigilancia" in str(c["value"]) for c in titles)
    # The committed phrase is asserted verbatim as the matched literal.
    kw = [c for c in result.claims if c.get("predicate_id") == "bill_matched_keyword"]
    assert kw and all(c["raw_value"] == "vigilancia" for c in kw)
    # Jurisdiction key set on every measure claim (US-PR territorial).
    jur = [c for c in result.claims if c.get("predicate_id") == "bill_jurisdiction"]
    assert jur and all(c["value"] == "US-PR" for c in jur)
    # The search outcome row records the served totals honestly.
    page = [c for c in result.claims if c["record_kind"] == "sutra_search_page"]
    assert len(page) == 1
    assert page[0]["total_records"] == 24
    assert page[0]["returned_count"] == 5
    assert page[0]["truncated"] is True
    # Author names never mint a claim — the count rides the entity row.
    assert not any(c.get("predicate_id") in ("author", "person_name") for c in result.claims)
    assert all(c["authors_redacted"] is True for c in measures)


def test_sutra_search_empty_is_honest():
    result, _ = _run(
        "legis_pr_sistema_nico_de", "sutra_search_empty.html", "sutra_search_tablillas"
    )
    measures = [c for c in result.claims if c["record_kind"] == "sutra_measure"]
    assert measures == []
    page = [c for c in result.claims if c["record_kind"] == "sutra_search_page"]
    assert len(page) == 1
    assert page[0]["outcome"] == "empty"
    assert page[0]["total_records"] == 0


def test_sutra_detail_emit():
    result, _ = _run(
        "legis_pr_rc0787_resoluci_de", "sutra_detail_rc0787.html", "sutra_medida_rc0787"
    )
    measures = [c for c in result.claims if c["record_kind"] == "sutra_measure"]
    assert len(measures) == 1
    m = measures[0]
    assert m["subject_id"] == "sutra_measure:162075"
    assert m["measure_number"] == "RC0787"
    assert m["measure_type"] == "Resolución de la Cámara"
    assert m["legislative_session"] == "2025-2028"
    assert m["filed_date"] == "2026-09-01"
    assert m["filed_date_raw"] == "09/01/2026"
    assert m["author_count"] == 3
    assert len(m["events"]) == 3
    assert m["events"][-1]["name"] == "Referido a Comisión(es)"
    assert m["events"][-1]["date"] == "09/03/2026"
    assert m["events"][-1]["detail"] == "Comisión de Asuntos Internos"
    filed = [c for c in result.claims if c.get("predicate_id") == "filed_date"]
    assert filed and filed[0]["value"] == "2026-09-01"
    status = [c for c in result.claims if c.get("predicate_id") == "bill_status"]
    assert status and status[0]["value"] == "Referido a Comisión(es)"
    docs = [c for c in result.claims if c.get("predicate_id") == "document"]
    assert {c["value"] for c in docs} == {
        "https://sutra.oslpr.org/SutraFilesGen/162075/RC0787.docx"
    }


def test_sutra_detail_second_measure():
    result, _ = _run("legis_pr_pc0560_plan_de", "sutra_detail_pc0560.html", "sutra_medida_pc0560")
    measures = [c for c in result.claims if c["record_kind"] == "sutra_measure"]
    assert len(measures) == 1
    m = measures[0]
    assert m["measure_number"] == "PC0560"
    assert m["measure_type"] == "Proyecto de la Cámara"
    assert m["filed_date"] == "2025-04-28"
    assert m["author_count"] == 1
    docs = [c for c in result.claims if c.get("predicate_id") == "document"]
    assert {c["value"] for c in docs} == {"https://sutra.oslpr.org/SutraFilesGen/155376/PC0560.doc"}


def test_ocpr_index_pointer_emit():
    result, _ = _run(
        "procportal_pr_consulta_del_registro", "ocpr_index.html", "ocpr_consulta_index"
    )
    docs = [c for c in result.claims if c["record_kind"] == "ocpr_document"]
    assert len(docs) == 14
    years = {c.get("external_id") for c in docs}
    assert "2023-2024" in years and "2010-2011" in years
    # Pointers only — the FY file contents are never fetched.
    assert not any(c.get("predicate_id") == "contract" for c in result.claims)
    meta = [c for c in result.claims if c["record_kind"] == "ocpr_index"]
    assert len(meta) == 1
    assert meta[0]["fy_links"] == 14
    assert meta[0]["results_rows"] == 0
    assert meta[0]["search_form_post"] is True
    assert meta[0]["search_form_submitted"] is False
    assert meta[0]["last_updated_literal"]


def test_ocpr_results_s7_screen():
    """A populated results table emits contracts; a person-shaped contractor drops."""
    result, _ = _run(
        "procportal_pr_consulta_del_registro", "ocpr_results.html", "ocpr_consulta_index"
    )
    contracts = [c for c in result.claims if c["record_kind"] == "contract"]
    assert len(contracts) == 3
    subjects = {c["subject_id"] for c in contracts}
    assert subjects == {
        "contract:procportal_pr_consulta_del_registro:2023-000412",
        "contract:procportal_pr_consulta_del_registro:2022-001877",
        "contract:procportal_pr_consulta_del_registro:2021-002330",
    }
    sellers = [c for c in result.claims if c.get("predicate_id") == "seller"]
    assert {c["value"] for c in sellers} == {
        "VIGILANT SOLUTIONS LLC",
        "ABC SEGURIDAD INTEGRADA INC",
    }
    assert all(c["candidate_identifier"]["scheme"] == "procurement.org_name" for c in sellers)
    buyers = [c for c in result.claims if c.get("predicate_id") == "buyer"]
    assert {c["value"] for c in buyers} == {
        "Negociado de la Policia de Puerto Rico",
        "Departamento de Seguridad Publica",
        "Administracion de Transito Terrestre",
    }
    amounts = [c for c in result.claims if c.get("predicate_id") == "amount"]
    assert {c["value"] for c in amounts} == {"187500.00", "48000.00", "92340.00"}
    signed = [c for c in result.claims if c.get("predicate_id") == "signed_date"]
    assert {c["value"] for c in signed} == {"2023-03-15", "2022-11-02", "2021-08-20"}
    # The S7 drop: the contract still mints; the person name lands nowhere —
    # no seller claim, no label on the entity row, recorded screen outcome.
    person_contract = next(c for c in contracts if c["subject_id"].endswith("2022-001877"))
    assert person_contract["contractor_screen"] == "dropped"
    assert person_contract["seller_label"] == ""
    assert all(c["contractor_screen"] == "org" for c in contracts if c is not person_contract)
    assert "PEREZ" not in json.dumps(result.claims)
    meta = [c for c in result.claims if c["record_kind"] == "ocpr_index"]
    assert meta[0]["contracts_emitted"] == 3
    assert meta[0]["contractor_names_dropped"] == 1


def test_forbidden_column_refusal():
    with pytest.raises(ForbiddenFieldError):
        assert_no_forbidden_columns(["Contratista", "Seguro Social", "Entidad"], source_id="x")


def test_drift_fails_loud():
    targets = [t for t in puerto_rico_targets("legis_pr_sistema_nico_de")]
    url = targets[0]["url"]
    body = _FIX.joinpath("drift.html").read_bytes()
    responses = {url: _resp(url, body)}
    connector, ctx = _ctx("legis_pr_sistema_nico_de", targets[:1], responses)
    from connectors.stages import ContentDrift

    with pytest.raises(ContentDrift):
        run(connector, ctx)


def test_runner_and_live_targets_wired():
    """Every seat is connector-mapped and its live_targets delegates to the inventory."""
    from connectors.live_targets import live_targets
    from connectors.runner import CONNECTOR_FOR_SOURCE

    for seat in SEATS:
        assert CONNECTOR_FOR_SOURCE[seat] == "puerto_rico"
        targets = live_targets(seat)
        assert targets, f"{seat} must expand live targets from the committed inventory"
        assert all(t["kind"] in {"sutra_index", "sutra_detail", "ocpr_index"} for t in targets)


@pytest.mark.parametrize("source_id", sorted(SEATS))
def test_gated_source_refused_live(source_id):
    source = get(source_id)
    assert source.ingestion_permitted is False
    with pytest.raises(IngestionNotPermitted):
        assert_loadable(source)


def test_second_replay_identical():
    r1, _ = _run("legis_pr_rc0787_resoluci_de", "sutra_detail_rc0787.html", "sutra_medida_rc0787")
    r2, _ = _run("legis_pr_rc0787_resoluci_de", "sutra_detail_rc0787.html", "sutra_medida_rc0787")
    key = lambda c: (c["subject_id"], c.get("predicate_id"), str(c.get("value", "")))  # noqa: E731
    c1 = sorted(map(key, r1.claims))
    c2 = sorted(map(key, r2.claims))
    assert c1 == c2
