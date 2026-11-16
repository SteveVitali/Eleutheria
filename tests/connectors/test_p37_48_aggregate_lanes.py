# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.48 (R11-ACQ-20): the aggregate lanes — Socrata ``$group`` payee and
programme-area lanes, ArcGIS ``outStatistics`` declared-period lanes, and the
``state_checkbook_xlsx`` workbook lane, over committed fixtures (no network).

Covers: the ``payee`` subject emit (``payment_total`` + ``vendor``/``buyer``/
``published_by`` claims — the S7 screened lanes), the ``count`` function and
``year``/``declared`` period kinds (P36.6 machinery extended), the
natural-person payee drop gate, the committed ``payee_allowlist`` screen,
programme-area alert counts (S4 — never an alert point), the school-bus ATE
enforcement counts (S3 — never a per-violation row), the fail-closed
declaration checks, the gated-source live refusal, and the +0 shadow replay
determinism.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
from connectors.dot_511 import (
    AggregateSpecNotDeclared,
    Dot511Connector,
    assert_target_aggregate,
    registry_targets,
)
from connectors.live_targets import live_targets
from connectors.net import PoliteFetcher, RobotsResult
from connectors.pipeline import run
from connectors.registry import get
from connectors.stages import FetchResult, InMemoryCaptureStore, InMemoryClaimSink, RunContext
from evidence.ingest_run import IngestRun

_FIX = Path(__file__).resolve().parent / "fixtures" / "p37_48"
_RETRIEVED = datetime(2026, 11, 13, tzinfo=UTC)
_ALLOW_ALL = "User-agent: *\nAllow: /\n"

#: The 36-target P37.48 scope: source → [(target_id, fixture)] — fixture "" for
#: targets exercised by expansion/URL assertions only.
P37_48_TARGET_FIXTURES: dict[str, list[tuple[str, str]]] = {
    "camreg_us_socrata_hosted_vendor": [
        ("vt_vendor_payments_yearly", ""),
        ("ct_open_expenditures_yearly", ""),
        ("or_sos_financial_accounting_biennium", ""),
        ("dallas_vendor_payments_yearly", ""),
        ("cincinnati_vendor_payments_yearly", ""),
        ("la_checkbook_yearly", ""),
        ("cook_county_check_register_yearly", ""),
        ("baton_rouge_checkbook_yearly", ""),
        ("atlanta_checkbook_ledger_yearly", ""),
        ("college_station_checkbook_yearly", ""),
        ("providence_expenditures_yearly", ""),
    ],
    "camreg_us_municipal_contract_expenditure": [("cook_county_awarded_contracts_yearly", "")],
    "procportal_tx_texas_dir_cooperative": [
        ("tx_dir_vsr_fy26_vendor_fy", "tx_dir_fy26.json"),
        ("tx_dir_vsr_archive_vendor_fy", ""),
    ],
    "camreg_az_mesa_city_of_expenditures": [("mesa_expenditures_vendor_fy", "")],
    "camreg_de_delaware_checkbook_expenditure": [("delaware_checkbook_vendor_fy", "")],
    "camreg_nj_new_jersey_yourmoney": [("nj_yourmoney_vendor_fy", "nj_yourmoney.json")],
    "camreg_il_chicago_payments": [("chicago_payments_vendor_year", "")],
    "camreg_wa_washington_state_open": [
        ("wa_checkbook_1315_vendor_fy", ""),
        ("wa_checkbook_1517_vendor_fy", ""),
        ("wa_checkbook_1719_vendor_fy", ""),
        ("wa_checkbook_1921_vendor_fy", ""),
        ("wa_checkbook_2123_vendor_fy", ""),
        ("wa_checkbook_2325_vendor_fy", ""),
        ("wa_checkbook_2527_vendor_fy", "wa_checkbook_2527.xlsx"),
    ],
    "camreg_montgomery_md_ate": [
        ("montgomery_schoolbus_violations_quarterly", "montgomery_schoolbus.json")
    ],
    "camreg_oakland_ca_shotspotter_2013_2015": [
        ("oakland_shotspotter_2013_2014", "oakland_ss.json"),
        ("oakland_shotspotter_2015_09_10", ""),
        ("oakland_shotspotter_2015_07_08a", ""),
        ("oakland_shotspotter_2015_08_09b", ""),
        ("oakland_shotspotter_2015_08_08a", ""),
    ],
    "camreg_il_chicago_violence_reduction": [
        ("chicago_shotspotter_district_month", "chicago_ss.json")
    ],
    "camreg_mi_detroit_dpd_shotspotter": [
        ("detroit_shotspotter_district_2023", ""),
        ("detroit_shotspotter_district_2024", "detroit_ss_2024.json"),
        ("detroit_shotspotter_district_2025", ""),
        ("detroit_shotspotter_district_2026", ""),
    ],
}

ALL_P37_48_TARGETS = [
    (source_id, target_id)
    for source_id, pairs in P37_48_TARGET_FIXTURES.items()
    for target_id, _fixture in pairs
]

NEW_GATED_SOURCES = list(P37_48_TARGET_FIXTURES)

#: The two ACQ-20 seats that stay unmapped — recorded findings, no targets.
UNMAPPED_FINDING_SOURCES = [
    "camreg_us_ate_camera_location_and_per",
    "camreg_us_body_worn_camera",
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


def _empty_body(kind: str) -> bytes:
    return b"[]" if kind in ("socrata_rows", "socrata_aggregate") else b'{"features": []}'


def _run_fixture(
    source_id: str,
    fixture: str,
    target_id: str,
    *,
    body: bytes | None = None,
    retrieved_at: datetime = _RETRIEVED,
):
    targets = [t for t in live_targets(source_id) if t["id"] == target_id]
    assert targets, f"{source_id}:{target_id} must resolve registry targets"
    payload = _FIX.joinpath(fixture).read_bytes() if body is None else body
    responses = {t["url"]: _resp(t["url"], payload, retrieved_at=retrieved_at) for t in targets}
    connector, ctx = _ctx(source_id, targets, responses)
    result = run(connector, ctx)
    return result, ctx


def test_all_36_targets_expand():
    ids = {(s, t) for s, t in ALL_P37_48_TARGETS}
    assert len(ids) == 36
    for source_id, target_id in sorted(ids):
        targets = [t for t in registry_targets(source_id) if t["id"] == target_id]
        assert targets, f"{source_id}:{target_id} missing from expansion"


def test_socrata_payee_soql_shape():
    targets = registry_targets("camreg_nj_new_jersey_yourmoney")
    url = targets[0]["url"]
    qs = parse_qs(urlsplit(url).query)
    sel = qs["$select"][0]
    assert "vendor_name AS subject" in sel
    assert "fiscal_year AS period" in sel
    assert "sum(ytd_amt) AS count" in sel
    assert qs["$group"][0] == "vendor_name,fiscal_year"
    assert "$where" in qs and "upper(vendor_name) like '%FLOCK%'" in qs["$where"][0]


def test_socrata_year_and_count_shapes():
    # year kind -> date_trunc_y (Chicago payments)
    qs = parse_qs(urlsplit(registry_targets("camreg_il_chicago_payments")[0]["url"]).query)
    assert "date_trunc_y(check_date) AS period" in qs["$select"][0]
    # count function -> count(*) (Chicago ShotSpotter)
    qs2 = parse_qs(
        urlsplit(registry_targets("camreg_il_chicago_violence_reduction")[0]["url"]).query
    )
    assert "count(*) AS count" in qs2["$select"][0]
    assert "date_trunc_ym(date) AS period" in qs2["$select"][0]


def test_arcgis_declared_period_shape():
    target = registry_targets("camreg_mi_detroit_dpd_shotspotter")[0]
    qs = parse_qs(urlsplit(target["url"]).query)
    assert qs["groupByFieldsForStatistics"][0] == "council_district"
    stats = json.loads(qs["outStatistics"][0])
    assert stats[0]["statisticType"] == "count"
    assert stats[0]["onStatisticField"] == "incident_id"
    assert "called_at >= DATE '2023-01-01'" in qs["where"][0]
    assert qs["returnGeometry"][0] == "false"


def test_payee_emit_claims():
    result, ctx = _run_fixture(
        "camreg_nj_new_jersey_yourmoney", "nj_yourmoney.json", "nj_yourmoney_vendor_fy"
    )
    claims = result.claims
    totals = [c for c in claims if c["predicate_id"] == "payment_total"]
    assert {c["subject_id"] for c in totals} == {
        "payee:camreg_nj_new_jersey_yourmoney:nj_yourmoney_vendor_fy:CELLEBRITE INC",
        "payee:camreg_nj_new_jersey_yourmoney:nj_yourmoney_vendor_fy:FLOCK SAFETY",
    }
    flock25 = next(
        c for c in totals if c["subject_id"].endswith("FLOCK SAFETY") and c["period"] == "2025"
    )
    assert float(flock25["value"]) == pytest.approx(120000.00)
    assert flock25["currency"] == "USD"
    assert flock25["measure"] == "usd"
    assert "vendor" in {c["predicate_id"] for c in claims}
    assert "published_by" in {c["predicate_id"] for c in claims}
    assert "payee" in {c["predicate_id"] for c in claims}
    assert "technology" not in {c["predicate_id"] for c in claims}  # never on payee


def test_person_shaped_payee_fails_closed():
    body = json.dumps(
        [
            {"subject": "THARINGER  STEPHEN P", "period": "2025", "count": "12000.00"},
            {"subject": "FLOCK SAFETY", "period": "2025", "count": "10.00"},
        ]
    ).encode()
    result, ctx = _run_fixture(
        "camreg_nj_new_jersey_yourmoney",
        "",
        "nj_yourmoney_vendor_fy",
        body=body,
    )
    claims = result.claims
    assert not any("THARINGER" in c.get("subject_id", "") for c in claims)
    assert not any(str(c.get("value", "")).find("THARINGER") >= 0 for c in claims)
    rejected = [c for c in claims if c.get("record_kind") == "camera_record_rejected"]
    assert rejected  # recorded, never emitted


def test_checkbook_xlsx_lane():
    result, ctx = _run_fixture(
        "camreg_wa_washington_state_open",
        "wa_checkbook_2527.xlsx",
        "wa_checkbook_2527_vendor_fy",
    )
    claims = result.claims
    totals = [c for c in claims if c["predicate_id"] == "payment_total"]
    # FLOCK SAFETY only: THARINGER STEPHEN P (person) and US BANK PURCHASING
    # CARD PROGRAM (non-allowlisted) never become group rows.
    subjects = {c["subject_id"] for c in totals}
    assert subjects == {
        "payee:camreg_wa_washington_state_open:wa_checkbook_2527_vendor_fy:FLOCK SAFETY"
    }
    by_period = {c["period"]: float(c["value"]) for c in totals}
    assert by_period["2025"] == pytest.approx(1300.00)
    assert by_period["2026"] == pytest.approx(40.00)


def test_programme_area_alert_emit():
    result, ctx = _run_fixture(
        "camreg_oakland_ca_shotspotter_2013_2015",
        "oakland_ss.json",
        "oakland_shotspotter_2013_2014",
    )
    claims = result.claims
    counts = [c for c in claims if c["predicate_id"] == "programme_count"]
    assert {c["subject_id"] for c in counts} == {
        "programme_area:camreg_oakland_ca_shotspotter_2013_2015:oakland_shotspotter_2013_2014:33X",
        "programme_area:camreg_oakland_ca_shotspotter_2013_2015:oakland_shotspotter_2013_2014:02X",
    }
    assert all(c["measure"] == "alerts" for c in counts)
    assert not any(c["predicate_id"] == "camera_latitude" for c in claims)


def test_declared_period_emit():
    result, ctx = _run_fixture(
        "camreg_mi_detroit_dpd_shotspotter",
        "detroit_ss_2024.json",
        "detroit_shotspotter_district_2024",
    )
    claims = result.claims
    counts = [c for c in claims if c["predicate_id"] == "programme_count"]
    assert len(counts) == 3
    assert all(c["period"] == "2024" for c in counts)
    assert {c["period"] for c in counts} == {"2024"}


def test_schoolbus_enforcement_emit():
    result, ctx = _run_fixture(
        "camreg_montgomery_md_ate",
        "montgomery_schoolbus.json",
        "montgomery_schoolbus_violations_quarterly",
    )
    claims = result.claims
    counts = [c for c in claims if c["predicate_id"] == "enforcement_count"]
    assert len(counts) == 3
    assert {c["period"] for c in counts} == {"2024-Q1", "2024-Q2"}
    tech = [c for c in claims if c["predicate_id"] == "technology"]
    assert tech and all(c["value"] == "ate-school-bus-stop-arm" for c in tech)


def test_declared_requires_label():
    with pytest.raises(AggregateSpecNotDeclared, match="aggregate_period_label"):
        assert_target_aggregate(
            {
                "id": "x",
                "kind": "arcgis_outstatistics",
                "aggregate_period_kind": "declared",
                "aggregate_subject_field": "s",
                "aggregate_count_field": "c",
                "aggregate_count_function": "count",
                "aggregate_measure": "m",
            }
        )


def test_xlsx_requires_allowlist_and_payee():
    base = {
        "id": "x",
        "kind": "state_checkbook_xlsx",
        "aggregate_subject_field": "Vendor",
        "aggregate_period_field": "FY",
        "aggregate_period_kind": "verbatim",
        "aggregate_count_field": "Amount",
        "aggregate_count_function": "sum",
        "aggregate_measure": "usd",
    }
    with pytest.raises(AggregateSpecNotDeclared, match="payee"):
        assert_target_aggregate(base)
    with pytest.raises(AggregateSpecNotDeclared, match="payee_allowlist"):
        assert_target_aggregate(base | {"aggregate_subject_kind": "payee"})


@pytest.mark.parametrize("source_id", sorted(NEW_GATED_SOURCES))
def test_gated_source_refused_live(source_id):
    source = get(source_id)
    assert source.ingestion_permitted is False
    from connectors.loader import IngestionNotPermitted, assert_loadable

    with pytest.raises(IngestionNotPermitted):
        assert_loadable(source)


def test_unmapped_finding_sources():
    from connectors.runner import CONNECTOR_FOR_SOURCE

    for source_id in UNMAPPED_FINDING_SOURCES:
        # The ATE channel's ACQ-01 discovery row (a socrata catalog query, not a
        # fetch lane) and the BWC row carry recorded findings — neither joins
        # the connector map under P37.48.
        assert source_id not in CONNECTOR_FOR_SOURCE
        assert get(source_id).ingestion_permitted is False


def test_second_replay_identical():
    r1, ctx1 = _run_fixture(
        "camreg_nj_new_jersey_yourmoney", "nj_yourmoney.json", "nj_yourmoney_vendor_fy"
    )
    r2, ctx2 = _run_fixture(
        "camreg_nj_new_jersey_yourmoney", "nj_yourmoney.json", "nj_yourmoney_vendor_fy"
    )
    c1 = sorted((c["subject_id"], c["predicate_id"], str(c.get("value", ""))) for c in r1.claims)
    c2 = sorted((c["subject_id"], c["predicate_id"], str(c.get("value", ""))) for c in r2.claims)
    assert c1 == c2
