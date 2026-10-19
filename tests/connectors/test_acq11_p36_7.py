# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.7 (R11-ACQ-11): the Wave-B procurement and programme registers.

Drives the REAL ``pipeline.run`` over committed fixtures (no network,
SIG-INGEST-011) for the three gated surfaces:

* ``procportal_cook_il_awards`` — Cook County awarded contracts; the
  reviewed ``cook_county`` where slices only (``rows_window = false``),
  vendor_name + description ``%TERM%`` recall with the verbatim precision
  pass; the reseller-attribution case (Insight Public Sector carrying a
  Flock award in ``description``).
* ``procportal_wa_des_contract_sales`` — Washington DES contract sales;
  ``wa_des`` where slices with ``exact_fields`` contract-number equality
  (the seven reviewed master contracts), the ``customer_type``
  public-entity allowlist failing closed server-side AND client-side, and
  the composite ``contract|customer|vendor`` row key.
* ``camreg_dc_ovsjg_camera_rebate`` — the DC OVSJG rebate register's
  layer-33 ``arcgis_outstatistics`` PSA × MONTH_YEAR aggregate — a
  multi-measure ``programme_area``/``programme_count`` emit (ADR-208):
  programme-level rows only, never a camera, a geometry, or a registrant.

P8-6 runs on both lanes: a natural-person vendor emits NO ``seller``
claim (recorded ``seller_dropped`` on the notice row); the rebate lane
selects no registrant-level column and records denied-field names on
``excluded_fields``. Every row stays ``ingestion_permitted=false`` — the
loader gate refuses before any fetch (SIG-INGEST-014/028).
"""

from __future__ import annotations

import dataclasses
import json
import tomllib
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from connectors.dot_511 import (
    AggregateSpecNotDeclared,
    Dot511Connector,
    assert_target_aggregate,
    target_table,
)
from connectors.live_targets import live_targets
from connectors.net import PoliteFetcher, RobotsResult
from connectors.procurement import (
    ProcurementConnector,
    acq_keyword_term_set,
    portal_targets,
)
from connectors.registry import CompactStatus, CustodyPosture, get
from connectors.replay import replay, replay_fingerprint, shadow_replay
from connectors.stages import (
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun

from connectors import pipeline

_FIX_PORTAL = Path(__file__).resolve().parent / "fixtures" / "procportal"
_FIX_511 = Path(__file__).resolve().parent / "fixtures" / "dot_511"
REPO_ROOT = Path(__file__).resolve().parents[2]
_RETRIEVED = datetime(2026, 10, 12, tzinfo=UTC)
_ALLOW_ALL = "User-agent: *\nAllow: /\n"

COOK = "procportal_cook_il_awards"
WA_DES = "procportal_wa_des_contract_sales"
DC_REBATE = "camreg_dc_ovsjg_camera_rebate"

#: The three ACQ-11 surfaces — every row lands gated (HG-03 flips are the
#: operator's OP-26 Wave-B execution under ING-GO-B, never this ticket).
NEW_GATED_SOURCES = [COOK, WA_DES, DC_REBATE]

#: The ACQ-01 generated ids this ticket replaced — they must name no
#: source, tenant, target, cadence member or disposition row anywhere.
RETIRED_SOURCE_IDS = [
    "procportal_il_cook_county_procurement",
    "procportal_wa_washington_des_statewide",
    "camreg_dc_private_security_camera",
]

#: The reviewed WA DES public-entity customer_type allowlist (the verbatim
#: published values — the tenant row carries them, the $where folds them,
#: and extract fails closed on anything else).
WA_PUBLIC_CUSTOMER_TYPES = [
    "Cities Including Towns",
    "State Agency",
    "School Districts",
    "Districts, Other",
    "County",
    "Higher Ed (State Agency)",
    "Port Districts",
    "Other Govt",
    "US States/Territories",
    "Tribes",
    "Libraries",
    "Enterprise Services",
    "Federal Government",
    "Component Units",
]


# --- shared transport plumbing -------------------------------------------------


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


def _resp(url: str, body: bytes, status: int = 200) -> FetchResult:
    return FetchResult(
        url=url,
        status=status,
        body=body,
        media_type="application/json",
        retrieved_at=_RETRIEVED,
    )


def _ingest_run(connector_name: str) -> IngestRun:
    return IngestRun(
        connector_name=connector_name,
        connector_version="1.0.0",
        code_commit="deadbeef",
        ruleset_version="r1",
        vocab_version="v1",
        input_digests=(),
    )


def _ctx(
    source_id: str,
    connector: Any,
    targets: list[Mapping[str, Any]],
    responses: Mapping[str, FetchResult],
) -> RunContext:
    """The fixture gate posture — the source record is flipped the way a
    reviewer's flip would, never by bypassing the gate."""
    source = dataclasses.replace(
        get(source_id),
        ingestion_permitted=True,
        compact_status=CompactStatus.PUBLIC_TERMS_ONLY,
        custody_posture=CustodyPosture.MIRROR,
    )
    fetcher = PoliteFetcher(
        connector_name=connector.name,
        connector_version=connector.version,
        transport=MapTransport(responses),
    )
    return RunContext(
        source=source,
        run=_ingest_run(connector.name),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": list(targets)},
    )


def _claims(report) -> list[Mapping[str, Any]]:
    return [c for c in report.claims if c.get("record_kind") == "claim"]


# --- Cook County: bounded where slices only ------------------------------------


def test_cook_targets_are_where_slices_only_no_rows_window() -> None:
    """``rows_window = false``: the reviewed surface IS the where filter —
    no generic recency slice expands beside it."""
    targets = portal_targets(source_id=COOK)
    assert targets
    assert all(t["index_kind"] == "where" for t in targets)
    assert all(t["portal_where"] == "cook_county" for t in targets)
    terms = acq_keyword_term_set("cook_county")
    assert [t for w in targets for t in w["where_terms"]] == terms
    for t in targets:
        q = parse_qs(urlparse(str(t["url"])).query)
        assert "qh8j-6k63" in str(t["url"])
        clause = q["$where"][0]
        # vendor_name + description LIKE groups; no equality or required clause.
        assert "upper(vendor_name) like" in clause
        assert "upper(description) like" in clause
        assert "customer_type" not in clause
        assert " = '" not in clause
        for term in t["where_terms"]:
            assert f"'%{term.upper()}%'" in clause
        assert q["$order"] == ["start_date DESC"]


def _run_portal_source(
    source_id: str,
    fixture_by_group: Mapping[int, str],
    *,
    extra_fixtures: Mapping[int, str] | None = None,
):
    """Run the procurement connector over the source's own expanded targets,
    each where group fed its fixture (a group with no fixture sees an empty
    register page — the honest ``empty`` outcome)."""
    targets = portal_targets(source_id=source_id)
    bodies: dict[str, bytes] = {}
    for group, fixture in dict(fixture_by_group).items():
        bodies[group] = _FIX_PORTAL.joinpath(fixture).read_bytes()
    responses: dict[str, FetchResult] = {}
    for t in targets:
        body = bodies.get(t.get("where_group"), b"[]")
        responses[str(t["url"])] = _resp(str(t["url"]), body)
    connector = ProcurementConnector()
    ctx = _ctx(source_id, connector, targets, responses)
    return connector, ctx, pipeline.run(connector, ctx)


def test_cook_flock_reseller_and_person_rows() -> None:
    """The reviewed fixture surface: the Insight reseller row emits with its
    Flock evidence found in ``description`` (vendor_name alone never carries
    it — I3-Q069); Flock Safety + Axon emit beside it; the office-supplies
    row drops as recall noise; the natural-person vendor's seller claim is
    dropped (P8-6) and recorded on its notice row."""
    _connector, _ctx_obj, report = _run_portal_source(
        COOK,
        {0: "socrata_cook_awards.json", 3: "socrata_cook_awards_person.json"},
    )
    notices = [c for c in report.claims if c.get("record_kind") == "procurement_notice"]
    by_id = {n["external_id"]: n for n in notices}
    assert set(by_id) == {"2055-18411", "2055-17874", "2055-17001", "2055-16999"}
    assert {n["index_kind"] for n in notices} == {"where"}

    # The reseller row: seller is Insight, but the Flock evidence lands as a
    # verbatim content_term located in the description field.
    insight_subject = by_id["2055-18411"]["subject_id"]
    sellers = [
        c
        for c in report.claims
        if c.get("record_kind") == "claim" and c.get("predicate_id") == "seller"
    ]
    seller_names = {c["subject_id"]: c["value"] for c in sellers}
    assert seller_names[insight_subject] == "INSIGHT PUBLIC SECTOR LLC"
    terms = [
        c
        for c in report.claims
        if c.get("record_kind") == "claim" and c.get("predicate_id") == "content_term"
    ]
    insight_terms = [t for t in terms if t["subject_id"] == insight_subject]
    assert any(
        t["evidence"]["field"] == "description" and "flock" in t["value"].lower()
        for t in insight_terms
    ), f"no verbatim Flock term located in description: {insight_terms}"
    # The literal is verbatim — a byte range into the named field.
    flock_term = next(t for t in insight_terms if t["evidence"]["field"] == "description")
    row = json.loads(_FIX_PORTAL.joinpath("socrata_cook_awards.json").read_bytes())[
        flock_term["evidence"]["record_row"]
    ]
    field_text = row[flock_term["evidence"]["field"]]
    loc = flock_term["evidence"]["locator"]
    assert field_text[loc["start"] : loc["end"]] == flock_term["raw_value"]

    # P8-6: the natural-person payee emits no seller claim — the drop is
    # recorded on the notice row, never silent.
    person_notice = by_id["2055-16999"]
    assert person_notice["seller_dropped"] == "person_shaped"
    assert person_notice["subject_id"] not in seller_names
    # The person never mints an identity claim — the verbatim row stays on
    # the notice's `raw` (the award stays; the seller claim drops, P8-6).
    assert not any(
        c.get("predicate_id") == "seller" and "JOHN SMITH" in str(c.get("value") or "")
        for c in _claims(report)
    )

    # The g0 index row records the honest outcome: 3 kept, 1 recall-noise drop
    # (office supplies); g3 keeps the natural-person row.
    index = {
        r.get("index_keyword"): r for r in report.claims if r.get("record_kind") == "portal_index"
    }
    assert index["g0"]["items_count"] == 4
    assert index["g0"]["precise_count"] == 3
    assert index["g0"]["dropped_count"] == 1
    assert index["g3"]["items_count"] == 1
    assert index["g3"]["precise_count"] == 1

    # Buyer = the published department field; amount rides the award value.
    buyers = {
        c["subject_id"]: c["value"] for c in _claims(report) if c.get("predicate_id") == "buyer"
    }
    assert buyers[insight_subject] == "Sheriff's Office - Information Technology"


# --- WA DES: contract-number exact slices + public-entity customers ------------


def test_wa_des_targets_carry_exact_and_required_clauses() -> None:
    """Every WA slice folds the public-entity ``customer_type`` allowlist into
    ``$where`` AND adds per-term ``upper(contract_number) = '<TERM>'``
    equality for the seven reviewed contract ids; no rows window expands."""
    targets = portal_targets(source_id=WA_DES)
    assert targets
    assert all(t["index_kind"] == "where" for t in targets)
    assert all(t["portal_where"] == "wa_des" for t in targets)
    assert all(t["where_exact_fields"] == ["contract_number"] for t in targets)
    assert all(t["required_field"] == "customer_type" for t in targets)
    assert all(t["required_values"] == WA_PUBLIC_CUSTOMER_TYPES for t in targets)
    terms = acq_keyword_term_set("wa_des")
    assert [t for w in targets for t in w["where_terms"]] == terms
    # The seven reviewed contract ids sit inside the reviewed term set.
    for contract in ("05720", "02315", "06316", "04220", "06913", "00318", "02702"):
        assert contract in terms
    for t in targets:
        q = parse_qs(urlparse(str(t["url"])).query)
        clause = q["$where"][0]
        assert "upper(customer_type) in (" in clause
        for value in WA_PUBLIC_CUSTOMER_TYPES:
            assert f"'{value.upper()}'" in clause
        assert "upper(vendor_name) like" in clause
        for term in t["where_terms"]:
            assert f"upper(contract_number) = '{term.upper()}'" in clause


def test_wa_des_public_customers_emit_and_private_fail_closed() -> None:
    """g0 (vendor terms): the Axon and Motorola public-entity sales emit with
    ``buyer`` = the published customer; the private-school Axon sale and the
    office-supplies row never surface — one excluded, one recall-noise drop."""
    _connector, _ctx_obj, report = _run_portal_source(WA_DES, {0: "socrata_wa_des_sales.json"})
    index = {
        r.get("index_keyword"): r for r in report.claims if r.get("record_kind") == "portal_index"
    }
    assert index["g0"]["items_count"] == 4
    assert index["g0"]["precise_count"] == 2
    assert index["g0"]["dropped_count"] == 1
    assert index["g0"]["excluded_count"] == 1
    assert index["g0"]["required_field"] == "customer_type"
    assert index["g0"]["required_values"] == WA_PUBLIC_CUSTOMER_TYPES

    notices = [c for c in report.claims if c.get("record_kind") == "procurement_notice"]
    # The composite key: contract|customer|vendor — a bare contract number
    # can never collapse distinct sales onto one subject.
    ext_ids = {n["external_id"] for n in notices}
    assert ext_ids == {
        "05720|CITY OF SEATTLE|AXON ENTERPRISE INC",
        "06913|KING COUNTY|MOTOROLA SOLUTIONS INC",
    }
    subjects = {n["subject_id"] for n in notices}
    assert all("procurement_notice:" in s for s in subjects)

    buyers = {
        c["subject_id"]: c["value"] for c in _claims(report) if c.get("predicate_id") == "buyer"
    }
    subject_by_ext = {n["external_id"]: n["subject_id"] for n in notices}
    assert buyers[subject_by_ext["05720|CITY OF SEATTLE|AXON ENTERPRISE INC"]] == (
        "CITY OF SEATTLE"
    )
    assert buyers[subject_by_ext["06913|KING COUNTY|MOTOROLA SOLUTIONS INC"]] == ("KING COUNTY")
    sellers = {
        c["subject_id"]: c["value"] for c in _claims(report) if c.get("predicate_id") == "seller"
    }
    assert sellers[subject_by_ext["05720|CITY OF SEATTLE|AXON ENTERPRISE INC"]] == (
        "AXON ENTERPRISE INC"
    )
    # The private-school sale never reaches any claim surface.
    assert all(
        "EVERGREEN" not in str(c.get("value") or "")
        and "EVERGREEN" not in str(c.get("raw_value") or "")
        for c in _claims(report)
    )


def test_wa_des_contract_number_surfaces_reseller_rows() -> None:
    """g4 (the contract-id terms): the CDW Government sale on contract 05720
    emits — the exact contract-number match is the reviewed evidence, so a
    reseller whose vendor literal matches nothing still surfaces; the
    'Miscellaneous' and missing-type rows fail closed as excluded; the
    natural-person vendor's seller claim drops (P8-6)."""
    _connector, _ctx_obj, report = _run_portal_source(
        WA_DES, {4: "socrata_wa_des_sales_contracts.json"}
    )
    index = {
        r.get("index_keyword"): r for r in report.claims if r.get("record_kind") == "portal_index"
    }
    assert index["g4"]["items_count"] == 4
    assert index["g4"]["precise_count"] == 2
    assert index["g4"]["excluded_count"] == 2  # Miscellaneous + missing customer_type

    notices = [c for c in report.claims if c.get("record_kind") == "procurement_notice"]
    by_id = {n["external_id"]: n for n in notices}
    assert set(by_id) == {
        "05720|CITY OF SPOKANE|CDW GOVERNMENT LLC",
        "02315|PORT OF SEATTLE|JOHN SMITH",
    }
    reseller = by_id["05720|CITY OF SPOKANE|CDW GOVERNMENT LLC"]
    sellers = {
        c["subject_id"]: c["value"] for c in _claims(report) if c.get("predicate_id") == "seller"
    }
    assert sellers[reseller["subject_id"]] == "CDW GOVERNMENT LLC"
    # The contract number rides verbatim title evidence — never a fabricated
    # vendor literal.
    assert reseller["title"] == "05720"
    # P8-6 on the natural-person vendor.
    person = by_id["02315|PORT OF SEATTLE|JOHN SMITH"]
    assert person["seller_dropped"] == "person_shaped"
    assert person["subject_id"] not in sellers
    assert not any(
        c.get("predicate_id") == "seller" and "JOHN SMITH" in str(c.get("value") or "")
        for c in _claims(report)
    )


# --- DC OVSJG rebate: the programme-area aggregate -------------------------------


def _dc_targets() -> list[dict[str, Any]]:
    targets = [t for t in live_targets(DC_REBATE)]
    assert len(targets) == 1  # observed_count 171 < the 1000-row page
    return targets


def _run_dc(fixture: str):
    targets = _dc_targets()
    body = _FIX_511.joinpath(fixture).read_bytes()
    responses = {t["url"]: _resp(t["url"], body) for t in targets}
    connector = Dot511Connector()
    ctx = _ctx(DC_REBATE, connector, targets, responses)
    return connector, ctx, pipeline.run(connector, ctx)


def test_dc_rebate_target_is_multi_measure_arcgis_outstatistics() -> None:
    """Layer 33 expands to ONE ``arcgis_outstatistics`` page grouping
    ``PSA,MONTH_YEAR`` with six ``count_<field>`` statistics and
    ``returnGeometry=false`` — never ward/year columns the schema does not
    publish (ADR-208), never a geometry."""
    targets = _dc_targets()
    t = targets[0]
    assert t["id"] == "dc_ovsjg_camera_rebate_by_month"
    assert t["kind"] == "arcgis_outstatistics"
    aggregate = t["aggregate"]
    assert aggregate["subject_field"] == "PSA"
    assert aggregate["subject_kind"] == "programme_area"
    assert aggregate["period_field"] == "MONTH_YEAR"
    assert aggregate["count_fields"] == [
        "RECEIVED",
        "UNDERREVIEW",
        "APPROVED",
        "DECLINED",
        "REBATEFUND",
        "CAMERAFOUNDED",
    ]
    q = parse_qs(urlparse(t["url"]).query)
    assert q["groupByFieldsForStatistics"] == ["PSA,MONTH_YEAR"]
    assert q["returnGeometry"] == ["false"]
    statistics = json.loads(q["outStatistics"][0])
    assert len(statistics) == 6
    aliases = {s["outStatisticFieldName"] for s in statistics}
    assert aliases == {
        "count_RECEIVED",
        "count_UNDERREVIEW",
        "count_APPROVED",
        "count_DECLINED",
        "count_REBATEFUND",
        "count_CAMERAFOUNDED",
    }
    assert all(s["statisticType"] == "sum" for s in statistics)
    assert {s["onStatisticField"] for s in statistics} == set(aggregate["count_fields"])
    # Layer 33 only — the voucher programme's layer 34 is never a target.
    assert "/MapServer/33/query" in t["url"]
    assert "/MapServer/34" not in t["url"]


def test_dc_rebate_emits_programme_area_counts_only() -> None:
    """The fixture's three PSA × month group rows mint ``programme_area``
    subjects and fan out into six ``programme_count`` claims each — the
    published status series named verbatim — and NEVER a camera, geometry,
    enforcement or registrant surface."""
    _connector, _ctx_obj, report = _run_dc("arcgis_dc_ovsjg_rebate.json")
    assert report.asserted

    entities = [c for c in report.claims if c.get("predicate_id") == "programme_area"]
    subjects = {e["subject_id"] for e in entities}
    assert subjects == {
        f"programme_area:{DC_REBATE}:dc_ovsjg_camera_rebate_by_month:605",
        f"programme_area:{DC_REBATE}:dc_ovsjg_camera_rebate_by_month:301",
    }
    # Never a camera/geometry/registrant surface.
    assert not any(c.get("predicate_id") == "traffic_camera" for c in report.claims)
    assert not any(
        str(c.get("subject_id") or "").startswith("traffic_camera:") for c in report.claims
    )
    for e in entities:
        assert "REGISTRANT_PHOTO_URL" not in str(e.get("raw_value") or "")
    # The denied media field's NAME is recorded on excluded_fields; its
    # value never reaches the row (P8-5/F-330).
    photo_row = next(
        e for e in entities if "REGISTRANT_PHOTO_URL" in (e.get("excluded_fields") or ())
    )
    assert "example.invalid" not in json.dumps(photo_row)

    counts = [c for c in _claims(report) if c.get("predicate_id") == "programme_count"]
    # 3 group rows × 6 measures = 18 claims.
    assert len(counts) == 18
    by_series: dict[str, dict[tuple[str, str], int]] = {}
    for c in counts:
        assert c["measure"] == "programme_outcomes"
        assert c["period"] == "05-2026" or c["period"] == "06-2026"
        assert c["aggregate_subject_field"] == "PSA"
        assert c["aggregate_count_field"] == c["series"]
        by_series.setdefault(c["series"], {})[(c["subject_id"].rsplit(":", 1)[-1], c["period"])] = (
            c["value"]
        )
    assert set(by_series) == {
        "RECEIVED",
        "UNDERREVIEW",
        "APPROVED",
        "DECLINED",
        "REBATEFUND",
        "CAMERAFOUNDED",
    }
    assert by_series["RECEIVED"][("605", "05-2026")] == 12
    assert by_series["APPROVED"][("605", "05-2026")] == 8
    assert by_series["CAMERAFOUNDED"][("605", "06-2026")] == 6
    assert by_series["REBATEFUND"][("301", "05-2026")] == 2
    # No enforcement_count ever lands on a programme subject.
    assert not any(c.get("predicate_id") == "enforcement_count" for c in report.claims)


def test_dc_rebate_malformed_rows_fail_closed() -> None:
    """A group row missing its subject or carrying a non-numeric count
    rejects recorded — never a silently-absent or fabricated series."""
    _connector, _ctx_obj, report = _run_dc("arcgis_dc_ovsjg_rebate_bad.json")
    rejections = [c for c in report.claims if c.get("record_kind") == "camera_record_rejected"]
    assert len(rejections) == 2
    reasons = {r["rejection_reason"] for r in rejections}
    assert reasons == {"missing", "malformed"}
    # A rejected programme row records a programme_area subject — never a
    # camera subject id.
    assert all(str(r["subject_id"]).startswith("programme_area:") for r in rejections)
    # The one clean row still emits its programme subject + six counts.
    entities = [
        c
        for c in report.claims
        if c.get("record_kind") == "programme_area" and c.get("predicate_id") == "programme_area"
    ]
    assert len(entities) == 1
    counts = [c for c in _claims(report) if c.get("predicate_id") == "programme_count"]
    assert len(counts) == 6


def test_dc_rebate_replay_is_deterministic() -> None:
    """+0 shadow re-run — the multi-measure fan-out is pure and order-stable
    (SIG-INGEST-003/019)."""
    connector, ctx, report = _run_dc("arcgis_dc_ovsjg_rebate.json")
    replay_a = replay(connector, ctx, report.captures)
    replay_b = replay(connector, ctx, report.captures)
    assert replay_fingerprint(replay_a) == replay_fingerprint(replay_b)
    diff = shadow_replay(connector, ctx, report.captures, report.claims)
    assert diff.changed_count == 0, f"shadow diff must be empty: {diff.summary()}"


# --- registry / gate / cadence invariants --------------------------------------


def test_all_three_sources_stay_gated() -> None:
    """``ingestion_permitted=false`` on every row; the loader gate refuses
    before any fetch (SIG-INGEST-014/028)."""
    from connectors.loader import IngestionNotPermitted, assert_loadable

    for source_id in NEW_GATED_SOURCES:
        record = get(source_id)
        assert record.ingestion_permitted is False
        with pytest.raises(IngestionNotPermitted):
            assert_loadable(record)


def test_retired_generated_ids_name_nothing() -> None:
    """The ACQ-01 generated ids are gone from every registry surface —
    sources, tenants, targets, cadence members, dispositions."""
    sources_text = (REPO_ROOT / "connectors/src/connectors/data/sources.toml").read_text()
    for retired in RETIRED_SOURCE_IDS:
        assert f"[sources.{retired}]" not in sources_text
    tenants = tomllib.loads(
        (REPO_ROOT / "connectors/src/connectors/data/procurement_portal_tenants.toml").read_text()
    )["tenants"]
    for retired in RETIRED_SOURCE_IDS:
        assert retired not in {str(r.get("source_id")) for r in tenants.values()}
    targets = tomllib.loads(
        (REPO_ROOT / "connectors/src/connectors/data/camera_registry_targets.toml").read_text()
    )["targets"]
    for retired in RETIRED_SOURCE_IDS:
        assert retired not in {str(r.get("source_id")) for r in targets}
    dispositions = tomllib.loads(
        (REPO_ROOT / "connectors/src/connectors/data/live_dispositions.toml").read_text()
    )["sources"]
    for retired in RETIRED_SOURCE_IDS:
        assert retired not in dispositions


def test_cadence_batch_carries_the_final_ids() -> None:
    """``r11-procurement-01`` (``17 7 19 * *``, create-paused) names the three
    final source ids — never the generated ones."""
    cadence = tomllib.loads((REPO_ROOT / "ops/cadence.toml").read_text())
    batch = next(b for b in cadence["batches"] if b["id"] == "r11-procurement-01")
    assert batch["cron"] == "17 7 19 * *"
    assert set(batch["members"]) == set(NEW_GATED_SOURCES)
    assert batch["task_timeout"] == "6h"
    for retired in RETIRED_SOURCE_IDS:
        assert retired not in batch["members"]


def test_runner_maps_each_source_to_its_connector() -> None:
    from connectors.runner import CONNECTOR_FOR_SOURCE

    assert CONNECTOR_FOR_SOURCE[COOK] == "procurement"
    assert CONNECTOR_FOR_SOURCE[WA_DES] == "procurement"
    assert CONNECTOR_FOR_SOURCE[DC_REBATE] == "dot_511"


def test_live_targets_resolve_for_each_gated_source() -> None:
    """The live-target rows expand to the same reviewed surfaces (the gate
    refuses before they are ever fetched)."""
    cook = live_targets(COOK)
    assert cook and all(t["index_kind"] == "where" for t in cook)
    wa = live_targets(WA_DES)
    assert wa and all(t["index_kind"] == "where" for t in wa)
    dc = live_targets(DC_REBATE)
    assert len(dc) == 1 and dc[0]["kind"] == "arcgis_outstatistics"


def test_api_allowlist_covers_the_new_hosts() -> None:
    from connectors.registry import load_table

    allowlist = load_table("api_allowlist")
    hosts = {(row["host"], row["endpoint_prefix"]) for row in allowlist.get("api_host", [])}
    assert ("datacatalog.cookcountyil.gov", "/resource/") in hosts
    assert ("data.wa.gov", "/resource/") in hosts


def test_aggregate_declaration_closes_on_bad_specs() -> None:
    """``assert_target_aggregate`` fails closed on the malformed multi-measure
    declarations — ambiguous pair, empty list, verbatim-multi, multi +
    discriminator, unknown subject kind."""
    base = {
        "id": "test_target",
        "kind": "socrata_aggregate",
        "aggregate_subject_field": "PSA",
        "aggregate_period_field": "MONTH_YEAR",
        "aggregate_period_kind": "verbatim",
        "aggregate_count_function": "sum",
        "aggregate_measure": "programme_outcomes",
        "aggregate_subject_kind": "programme_area",
    }
    with pytest.raises(AggregateSpecNotDeclared, match="BOTH"):
        assert_target_aggregate(
            {
                **base,
                "aggregate_count_field": "RECEIVED",
                "aggregate_count_fields": ["RECEIVED"],
            }
        )
    with pytest.raises(AggregateSpecNotDeclared, match="non-empty list"):
        assert_target_aggregate({**base, "aggregate_count_fields": []})
    with pytest.raises(AggregateSpecNotDeclared, match="ONE published"):
        assert_target_aggregate(
            {
                **base,
                "aggregate_count_function": "verbatim",
                "aggregate_count_fields": ["RECEIVED", "APPROVED"],
            }
        )
    with pytest.raises(AggregateSpecNotDeclared, match="discriminator"):
        assert_target_aggregate(
            {
                **base,
                "aggregate_count_fields": ["RECEIVED", "APPROVED"],
                "aggregate_discriminator_field": "TYPE",
            }
        )
    with pytest.raises(AggregateSpecNotDeclared, match="aggregate_subject_kind"):
        assert_target_aggregate(
            {
                **base,
                "aggregate_subject_kind": "ward",
                "aggregate_count_fields": ["RECEIVED"],
            }
        )
    # The committed DC row validates.
    row = next(r for r in target_table()["targets"] if r["id"] == "dc_ovsjg_camera_rebate_by_month")
    spec = assert_target_aggregate(row)
    assert spec is not None
    assert spec.subject_kind == "programme_area"
    assert len(spec.count_fields) == 6


def test_no_procurement_claim_asserts_deployment() -> None:
    """Procured ≠ deployed — a procurement emit never carries a deployment
    predicate (§3.1 / the ticket's cited guard)."""
    _connector, _ctx_obj, report = _run_portal_source(WA_DES, {0: "socrata_wa_des_sales.json"})
    assert not any("deploy" in str(c.get("predicate_id") or "").lower() for c in report.claims)


def test_cook_replay_is_deterministic() -> None:
    """+0 shadow re-run over the Cook where slices (SIG-INGEST-017/019)."""
    connector, ctx, report = _run_portal_source(COOK, {0: "socrata_cook_awards.json"})
    replay_a = replay(connector, ctx, report.captures)
    replay_b = replay(connector, ctx, report.captures)
    assert replay_fingerprint(replay_a) == replay_fingerprint(replay_b)
    diff = shadow_replay(connector, ctx, report.captures, report.claims)
    assert diff.changed_count == 0, f"shadow diff must be empty: {diff.summary()}"
