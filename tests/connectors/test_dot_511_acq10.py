# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.6 (R11-ACQ-10): the automated-traffic-enforcement layers and the two
aggregate transports — fifteen targets across ten sources.

Drives the REAL ``pipeline.run`` over committed fixtures (no network,
SIG-INGEST-011). Covers: the ``socrata_aggregate`` / ``arcgis_outstatistics``
request shapes and ``enforcement_count`` claim emit (I8 NEW-7 — aggregate
site × period counts only, never a per-violation/citation row), the ATE
technology typing (never the ``traffic_camera`` blanket), the ``line``
route/programme records (MTA ABLE — a shape assertion with NO path geometry
and no ``fixed_asset_location`` claim), the Socrata ``area`` polygon emit
(Howard County school zones), the fail-closed line-geometry and malformed
aggregate-row paths, the Part VIII denied-field exclusions, and the +0
shadow replay determinism.
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
    expand_registry_rows,
    registry_targets,
    target_table,
)
from connectors.field_denylist import FieldDenylistViolation
from connectors.live_targets import live_targets
from connectors.net import PoliteFetcher, RobotsResult
from connectors.pipeline import run
from connectors.registry import get
from connectors.replay import replay, replay_fingerprint, shadow_replay
from connectors.stages import (
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun

_FIX = Path(__file__).resolve().parent / "fixtures" / "dot_511"
REPO_ROOT = Path(__file__).resolve().parents[2]
_RETRIEVED = datetime(2026, 10, 12, tzinfo=UTC)
_ALLOW_ALL = "User-agent: *\nAllow: /\n"

#: The P36.6 (ACQ-10) fifteen-target scope, keyed by the source that carries
#: each target — dot_511_de and camreg_chicago_il are EXISTING sources whose
#: rows widen by target (I8 §5.3); the nine camreg_ sources are new and gated
#: until the operator's OP-26 Wave-B flip under ING-GO-B.
P36_6_TARGET_FIXTURES: dict[str, list[tuple[str, str]]] = {
    "dot_511_de": [("deldot_red_light", "deldot_red_light.json")],
    "camreg_dc_ddot_ate": [
        ("dc_asc_sites", "dc_asc_sites.json"),
        ("dc_asc_violations_by_month", "dc_asc_violations.json"),
    ],
    "camreg_chicago_il": [
        ("chicago_speed_violations_monthly", "chicago_speed_violations.json"),
        ("chicago_redlight_violations_monthly", "chicago_redlight_violations.json"),
    ],
    "camreg_montgomery_md_ate": [
        ("montgomery_speed_violations_quarterly", "montgomery_speed_violations.json"),
        ("montgomery_redlight_violations_quarterly", "montgomery_redlight_violations.json"),
        ("montgomery_speed_cameras_2024", "montgomery_speed_cameras_2024.json"),
    ],
    "camreg_nyc_mta_bus_lane_ate": [("mta_able_enforced_routes", "mta_able_routes.json")],
    "camreg_tacoma_wa_ate": [("tacoma_automated_enforcement", "tacoma_ae.json")],
    "camreg_howard_md_school_zone_ate": [("howard_school_zone_areas", "howard_school_zones.json")],
    "camreg_lakeland_fl_red_light": [("lakeland_red_light_cameras", "lakeland_red_light.json")],
    "camreg_suffolk_ny_red_light": [("suffolk_tpva_red_light_2015", "suffolk_red_light_2015.json")],
    "camreg_medford_or_ate": [("medford_red_light_speed_cameras", "medford_ate.json")],
    "camreg_ctdot_speed_safety": [("ctdot_approximate_speed_safety", "ctdot_speed_safety.json")],
}

ALL_P36_6_TARGETS = [
    (source_id, target_id)
    for source_id, pairs in P36_6_TARGET_FIXTURES.items()
    for target_id, _fixture in pairs
]

#: The nine NEW gated sources — dot_511_de and camreg_chicago_il are existing
#: sources whose rights postures this ticket does not touch.
NEW_GATED_SOURCES = [
    "camreg_dc_ddot_ate",
    "camreg_montgomery_md_ate",
    "camreg_nyc_mta_bus_lane_ate",
    "camreg_tacoma_wa_ate",
    "camreg_howard_md_school_zone_ate",
    "camreg_lakeland_fl_red_light",
    "camreg_suffolk_ny_red_light",
    "camreg_medford_or_ate",
    "camreg_ctdot_speed_safety",
]

#: The ACQ-01 generated ids the P36.6 consolidation retired — they must name
#: no source and no target anywhere in the merged registry.
RETIRED_SOURCE_IDS = [
    "camreg_de_traffic_devices_red",
    "camreg_md_montgomery_county_automated",
    "camreg_md_montgomery_county_speedcameras",
    "camreg_ny_new_york_city_mta_bus",
    "camreg_wa_tacoma_automated_enforcement",
    "camreg_lakeland_fl_red_light_cameras",
    "camreg_suffolk_county_ny_tpva_red_light",
    "camreg_medford_or_red_light_speed",
    "camreg_ct_approximate_speed_safety",
    "camreg_howard_county_md_schzonehighligh",
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


def _empty_page_body(kind: str) -> bytes:
    """The shape an out-of-fixture page returns — a Socrata lane carries a row
    array, an ArcGIS lane a ``features`` document."""
    return b"[]" if kind in ("socrata_rows", "socrata_aggregate") else b'{"features": []}'


def _run_fixture(
    source_id: str,
    fixture: str,
    target_id: str,
    *,
    body: bytes | None = None,
    retrieved_at: datetime = _RETRIEVED,
):
    """Run the connector end-to-end over one committed fixture (no network)."""
    targets = [t for t in live_targets(source_id) if t["id"] == target_id]
    assert targets, f"{source_id}:{target_id} must resolve registry targets"
    payload = _FIX.joinpath(fixture).read_bytes() if body is None else body
    responses = {
        t["url"]: _resp(
            t["url"],
            payload if t.get("page", 0) == 0 else _empty_page_body(str(t["kind"])),
            retrieved_at=retrieved_at,
        )
        for t in targets
    }
    connector, ctx = _ctx(source_id, targets, responses)
    return run(connector, ctx)


def _run_source(source_id: str, *, retrieved_at: datetime = _RETRIEVED):
    """Run the P36.6 live targets of one source, each fed its fixture.

    The deferred ``automated_school_bus_camera_violations`` placeholder row
    (plan AP-T2-049, family ticket ACQ-20 — a per-violation surface the
    P36.6 review explicitly did NOT register) shares the Montgomery source
    and is filtered out here exactly as its deferred status intends.
    """
    fixtures = dict(P36_6_TARGET_FIXTURES[source_id])
    targets = [t for t in live_targets(source_id) if t["id"] in fixtures]
    responses: dict[str, FetchResult] = {}
    for t in targets:
        if int(t.get("page", 0)) == 0:
            body = _FIX.joinpath(fixtures[t["id"]]).read_bytes()
        else:
            body = _empty_page_body(str(t["kind"]))
        responses[t["url"]] = _resp(t["url"], body, retrieved_at=retrieved_at)
    connector, ctx = _ctx(source_id, targets, responses)
    return connector, ctx, run(connector, ctx)


def _claims(report) -> list[Mapping[str, Any]]:
    return [c for c in report.claims if c.get("record_kind") == "claim"]


def _entities(report) -> list[Mapping[str, Any]]:
    return [
        c
        for c in report.claims
        if c.get("predicate_id") == "traffic_camera"
        and c.get("record_kind") != "camera_record_rejected"
    ]


def _rejections(report) -> list[Mapping[str, Any]]:
    return [c for c in report.claims if c.get("record_kind") == "camera_record_rejected"]


def _by_pred(report, predicate: str) -> list[Mapping[str, Any]]:
    return [c for c in _claims(report) if c["predicate_id"] == predicate]


def _qs(target: Mapping[str, Any]) -> dict[str, list[str]]:
    """The expanded target URL's query parameters (SoQL/ArcGIS request shape)."""
    return parse_qs(urlsplit(str(target["url"])).query)


# --- registry expansion -----------------------------------------------------


def test_all_fifteen_targets_resolve() -> None:
    """All fifteen P36.6 targets expand from the merged registry across ten
    sources — the DC pair, the Chicago pair and the Montgomery triple ride
    their consolidated sources in the same run (I8 §5.3)."""
    assert len(ALL_P36_6_TARGETS) == 15
    for source_id, target_id in ALL_P36_6_TARGETS:
        targets = [t for t in registry_targets(source_id) if t["id"] == target_id]
        assert targets, f"{source_id}:{target_id} has no registry target"
        for t in targets:
            assert t["kind"] in (
                "arcgis_query",
                "socrata_rows",
                "socrata_aggregate",
                "arcgis_outstatistics",
            )
            assert t["state"] and t["agency"]
            assert t["jurisdiction_scheme"] == "iso.3166_2"
            if t["kind"] in ("arcgis_query", "arcgis_outstatistics"):
                # The reviewed ArcGIS request budget rides every ArcGIS
                # target (I8 NEW-3), named-host or default 10/min.
                assert int(t.get("rate_limit_per_min") or 0) > 0


def test_every_target_types_ate_never_the_blanket() -> None:
    """Every P36.6 target types an ``ate-*`` member by declaration — the
    legacy ``traffic_camera`` blanket typing is never inferred (PKG-07)."""
    for source_id, target_id in ALL_P36_6_TARGETS:
        for t in registry_targets(source_id):
            if t["id"] != target_id:
                continue
            assert t["technology"].startswith("ate-"), f"{t['id']} declares {t['technology']!r}"
            assert t["record_kind"] == t["technology"]


def test_the_acq01_generated_ids_are_retired() -> None:
    """The P36.6 consolidation renamed/removed the generated source ids —
    none survives as a source_id on any target row."""
    source_ids = {row.get("source_id") for row in target_table().get("targets", [])}
    for retired in RETIRED_SOURCE_IDS:
        assert retired not in source_ids, f"{retired} must be retired"


def test_r11_ate_01_membership_is_the_nine_gated_sources() -> None:
    """ops/cadence.toml r11-ate-01 holds exactly the nine new gated sources —
    the consolidated deldot_red_light rides dot_511_de's r11-layers-01 seat
    and the Chicago aggregates ride camreg_chicago_il's existing seat."""
    import tomllib

    data = tomllib.loads((REPO_ROOT / "ops" / "cadence.toml").read_text())
    batch = next(b for b in data["batches"] if b["id"] == "r11-ate-01")
    assert sorted(batch["members"]) == sorted(NEW_GATED_SOURCES)
    for retired in RETIRED_SOURCE_IDS:
        assert retired not in batch["members"]


def test_all_new_sources_stay_gated() -> None:
    """Every new P36.6 source refuses the live gate — the operator's OP-26
    Wave-B flip under ING-GO-B is the only route to a live fetch."""
    from connectors.runner import live_gate_reasons

    for source_id in NEW_GATED_SOURCES:
        reasons = live_gate_reasons(source_id)
        assert reasons, f"{source_id} must stay gated"
        source = get(source_id)
        assert source.ingestion_permitted is False
        assert live_targets(source_id), f"{source_id} must have live_targets rows"


# --- the aggregate declarations + request shapes (I8 NEW-7) ------------------


def test_aggregate_declaration_is_validated_fail_closed() -> None:
    """A malformed aggregate declaration is a registry defect, never a
    guessed grouping — closed vocabularies, bare identifiers only."""
    assert assert_target_aggregate({"id": "x", "kind": "arcgis_query"}) is None
    with pytest.raises(AggregateSpecNotDeclared):
        assert_target_aggregate(
            {"id": "x", "kind": "socrata_aggregate", "aggregate_period_kind": "quarter"}
        )
    with pytest.raises(AggregateSpecNotDeclared):
        assert_target_aggregate(
            {
                "id": "x",
                "kind": "socrata_aggregate",
                "aggregate_period_kind": "month",
                "aggregate_count_function": "avg",
            }
        )
    with pytest.raises(AggregateSpecNotDeclared):
        # 'verbatim' has no ArcGIS statisticType.
        assert_target_aggregate(
            {
                "id": "x",
                "kind": "arcgis_outstatistics",
                "aggregate_period_kind": "verbatim",
                "aggregate_count_function": "verbatim",
                "aggregate_measure": "violations",
            }
        )
    with pytest.raises(AggregateSpecNotDeclared):
        # ArcGIS groupBy groups verbatim columns only.
        assert_target_aggregate(
            {
                "id": "x",
                "kind": "arcgis_outstatistics",
                "aggregate_period_kind": "month",
                "aggregate_count_function": "sum",
                "aggregate_measure": "violations",
            }
        )
    with pytest.raises(AggregateSpecNotDeclared):
        # A query expression smuggled through a field declaration is refused.
        assert_target_aggregate(
            {
                "id": "x",
                "kind": "socrata_aggregate",
                "aggregate_subject_field": "camera_id,latitude",
                "aggregate_period_field": "violation_date",
                "aggregate_period_kind": "month",
                "aggregate_count_field": "violations",
                "aggregate_count_function": "sum",
                "aggregate_measure": "violations",
            }
        )
    with pytest.raises(AggregateSpecNotDeclared):
        # The count's unit must be declared, never implied.
        assert_target_aggregate(
            {
                "id": "x",
                "kind": "socrata_aggregate",
                "aggregate_subject_field": "camera_id",
                "aggregate_period_field": "violation_date",
                "aggregate_period_kind": "month",
                "aggregate_count_field": "violations",
                "aggregate_count_function": "sum",
            }
        )


def test_chicago_socrata_aggregate_request_shape() -> None:
    """The grouped SoQL: subject camera_id, period date_trunc_ym(violation_date),
    sum(violations) AS count, the committed 2023-10 window, deterministic
    group + order."""
    targets = [
        t
        for t in registry_targets("camreg_chicago_il")
        if t["id"] == "chicago_speed_violations_monthly"
    ]
    params = _qs(targets[0])
    assert params["$select"] == [
        "camera_id AS subject,date_trunc_ym(violation_date) AS period,sum(violations) AS count"
    ]
    assert params["$group"] == ["camera_id,date_trunc_ym(violation_date)"]
    assert params["$where"] == ["violation_date >= '2023-10-01'"]
    assert params["$order"] == ["camera_id,date_trunc_ym(violation_date)"]
    assert params["$limit"] == ["5000"]
    # 5,760 planned group rows ÷ 5,000 → two bounded pages.
    assert len(targets) == 2
    assert params["$offset"] == ["0"]
    assert _qs(targets[1])["$offset"] == ["5000"]


def test_montgomery_verbatim_aggregate_request_shape() -> None:
    """``count_function="verbatim"`` selects the publisher's OWN group row —
    subject/period/total AS the canonical aliases, no ``$group`` emitted."""
    targets = [
        t
        for t in registry_targets("camreg_montgomery_md_ate")
        if t["id"] == "montgomery_speed_violations_quarterly"
    ]
    params = _qs(targets[0])
    assert params["$select"] == ["site_number AS subject,quarter_name AS period,total AS count"]
    assert "$group" not in params, "a publisher-aggregated table emits no $group"
    assert params["$order"] == ["site_number,quarter_name"]
    # The published `address` column is never requested (F-330).
    select = params["$select"][0]
    assert "address" not in select.lower()


def test_dc_outstatistics_request_shape() -> None:
    """The ArcGIS outStatistics query: groupBy subject + period +
    discriminator, sum(NUM_VIOLATIONS) AS count, returnGeometry=false, the
    committed 2023-10 first-window where."""
    targets = [
        t for t in registry_targets("camreg_dc_ddot_ate") if t["id"] == "dc_asc_violations_by_month"
    ]
    params = _qs(targets[0])
    assert params["groupByFieldsForStatistics"] == [
        "ENFORCEMENT_SPACE_CODE,YEAR_MONTH,ENFORCEMENT_TYPE"
    ]
    assert json.loads(params["outStatistics"][0]) == [
        {
            "statisticType": "sum",
            "onStatisticField": "NUM_VIOLATIONS",
            "outStatisticFieldName": "count",
        }
    ]
    assert params["returnGeometry"] == ["false"]
    assert params["where"] == ["YEAR_MONTH >= '2023-10'"]
    assert params["orderByFields"] == ["ENFORCEMENT_SPACE_CODE,YEAR_MONTH,ENFORCEMENT_TYPE"]
    # CAMERA_STATUS/LAST_RECORD stay out of the group — never a per-status row.
    assert "CAMERA_STATUS" not in params["groupByFieldsForStatistics"][0]
    assert "LAST_RECORD" not in params["groupByFieldsForStatistics"][0]


# --- the aggregate emit ------------------------------------------------------


def test_chicago_aggregate_emits_enforcement_count() -> None:
    """The socrata_aggregate run emits subject-keyed entities and
    enforcement_count claims — period + measure, never geometry, never a
    per-violation row."""
    report = _run_fixture(
        "camreg_chicago_il",
        "chicago_speed_violations.json",
        "chicago_speed_violations_monthly",
    )
    entities = _entities(report)
    assert len(entities) == 3
    assert all(e["record_kind"] == "ate-speed" for e in entities)
    assert {e["subject_id"] for e in entities} == {
        "traffic_camera:camreg_chicago_il:chicago_speed_violations_monthly:CHI-S-1141",
        "traffic_camera:camreg_chicago_il:chicago_speed_violations_monthly:CHI-S-2077",
    }
    counts = _by_pred(report, "enforcement_count")
    assert len(counts) == 3
    by_key = {(c["subject_id"], c["period"]): c for c in counts}
    row = by_key[
        (
            "traffic_camera:camreg_chicago_il:chicago_speed_violations_monthly:CHI-S-1141",
            "2023-10",
        )
    ]
    assert row["value"] == 142 and isinstance(row["value"], int)
    assert row["raw_value"] == "142"
    assert row["measure"] == "violations"
    assert "series" not in row
    # An aggregate row mints NO geometry claim and no per-violation predicate.
    assert _by_pred(report, "camera_latitude") == []
    assert _by_pred(report, "camera_longitude") == []
    assert _by_pred(report, "fixed_asset_location") == []


def test_montgomery_verbatim_aggregate_emits() -> None:
    """The publisher-aggregated table: the verbatim period label (the
    quarter_name) rides the claim's period, the published total is the
    count."""
    report = _run_fixture(
        "camreg_montgomery_md_ate",
        "montgomery_speed_violations.json",
        "montgomery_speed_violations_quarterly",
    )
    entities = _entities(report)
    assert len(entities) == 3
    assert all(e["record_kind"] == "ate-speed" for e in entities)
    counts = _by_pred(report, "enforcement_count")
    assert len(counts) == 3
    subject = "traffic_camera:camreg_montgomery_md_ate:montgomery_speed_violations_quarterly:S-003"
    row = next(c for c in counts if c["subject_id"] == subject and c["period"] == "2024-Q1")
    assert row["value"] == 1204
    assert row["measure"] == "violations"


def test_dc_outstatistics_emits_the_type_series() -> None:
    """The DC outStatistics group rows keep the PUBLISHED group-column names;
    the ENFORCEMENT_TYPE discriminator rides the claim's ``series`` field so
    the concurrent red-light + speed series on one space-month never
    collide."""
    report = _run_fixture(
        "camreg_dc_ddot_ate",
        "dc_asc_violations.json",
        "dc_asc_violations_by_month",
    )
    counts = _by_pred(report, "enforcement_count")
    assert len(counts) == 3
    subject = "traffic_camera:camreg_dc_ddot_ate:dc_asc_violations_by_month:ES-0101"
    jan = [c for c in counts if c["subject_id"] == subject and c["period"] == "2024-01"]
    assert len(jan) == 2
    assert {c["series"] for c in jan} == {"Speed", "Red-Light"}
    assert {c["value"] for c in jan} == {142, 38}
    feb = next(c for c in counts if c["period"] == "2024-02")
    assert feb["subject_id"].endswith(":ES-0207")
    assert feb["series"] == "Red-Light"
    assert feb["measure"] == "violations"
    # The group rows carry no geometry and mint none.
    assert _by_pred(report, "camera_latitude") == []


def test_dc_asc_sites_field_coordinates_and_type() -> None:
    """The sites layer: declared coordinate_mode=fields reads the
    CAMERA_LATITUDE/LONGITUDE attribute pair; the seven enforcement types on
    one layer type ate-unspecified (the family evidenced, the subtype
    published per row)."""
    report = _run_fixture("camreg_dc_ddot_ate", "dc_asc_sites.json", "dc_asc_sites")
    entities = _entities(report)
    assert len(entities) == 2
    assert all(e["record_kind"] == "ate-unspecified" for e in entities)
    assert all(
        e["coordinate_source"] == "fields:CAMERA_LATITUDE/CAMERA_LONGITUDE" for e in entities
    )
    assert not _rejections(report)
    names = {c["value"] for c in _by_pred(report, "camera_name")}
    assert "600 block of Eastern Ave NE (EB)" in names
    # The published ENFORCEMENT_TYPE stays captured-but-unclaimed (no
    # registered predicate asserts it).
    assert not any(
        c.get("value") == "Speed" and c.get("predicate_id") != "technology" for c in _claims(report)
    )


def test_aggregate_row_missing_subject_or_count_records_rejection() -> None:
    """A group row with no subject key or a non-numeric count fails closed —
    recorded as camera_record_rejected, never a claim, never a guessed
    window or total."""
    doc = [
        {"subject": "CHI-S-1", "period": "2023-10", "count": "50"},
        {"subject": "", "period": "2023-10", "count": "7"},
        {"subject": "CHI-S-2", "period": "2023-10", "count": "not-a-number"},
        {"subject": "CHI-S-3", "period": "", "count": "9"},
    ]
    report = _run_fixture(
        "camreg_chicago_il",
        "chicago_speed_violations.json",
        "chicago_speed_violations_monthly",
        body=json.dumps(doc).encode(),
    )
    assert len(_entities(report)) == 1
    rejections = _rejections(report)
    assert len(rejections) == 3
    assert all(r["rejection_reason"] in ("missing", "malformed") for r in rejections)
    assert len(_by_pred(report, "enforcement_count")) == 1


# --- the line + area geometry lanes (SIG-GEO-003) ----------------------------


def test_mta_line_records_emit_no_geometry_claims() -> None:
    """The ABLE route register: geometry_kind='line' asserts the route shape
    only — no path, no centroid, no device-point claims; the declared
    deployment-date column emits installation_date verbatim and `route`
    rides camera_roadway."""
    report = _run_fixture(
        "camreg_nyc_mta_bus_lane_ate", "mta_able_routes.json", "mta_able_enforced_routes"
    )
    entities = _entities(report)
    assert len(entities) == 2
    for e in entities:
        assert e["record_kind"] == "ate-bus-lane"
        assert e["geometry_kind"] == "line"
        assert e["geometry_wkt"] is None
        assert e["latitude"] is None and e["longitude"] is None
        assert e["centroid_latitude"] is None and e["centroid_longitude"] is None
        assert e["coordinate_source"] == "none"
        assert e["subject_id"].startswith(
            "traffic_camera:camreg_nyc_mta_bus_lane_ate:mta_able_enforced_routes:"
        )
    kinds = {c["value"] for c in _by_pred(report, "geometry_kind")}
    assert kinds == {"line"}
    assert _by_pred(report, "fixed_asset_location") == []
    assert _by_pred(report, "camera_latitude") == []
    assert _by_pred(report, "camera_longitude") == []
    assert _by_pred(report, "camera_coordinate_source") == []
    roadways = {c["value"] for c in _by_pred(report, "camera_roadway")}
    assert roadways == {"M14 SBS", "Bx12 SBS"}
    dates = {c["value"] for c in _by_pred(report, "installation_date")}
    assert dates == {"2024-05-20", "2019-10-02"}
    # `program` carries NO claim — captured-but-unclaimed (P4).
    assert not any(c.get("value") in ("ABLE", "ACE") for c in _claims(report))


def test_mta_line_row_carrying_path_geometry_fails_closed() -> None:
    """A `line` register row that DOES carry a published path (a Socrata
    LineString under a geo column) fails closed — unsupported_geometry —
    never silently asserting 'no geometry' against published evidence."""
    doc = [
        {
            ":id": "row-ok",
            "program": "ACE",
            "route": "M14 SBS",
            "implementation_date": "2024-05-20",
        },
        {
            ":id": "row-path",
            "program": "ACE",
            "route": "Q44 SBS",
            "implementation_date": "2024-06-01",
            "the_geom": {
                "type": "LineString",
                "coordinates": [[-73.82, 40.70], [-73.80, 40.72]],
            },
        },
    ]
    report = _run_fixture(
        "camreg_nyc_mta_bus_lane_ate",
        "mta_able_routes.json",
        "mta_able_enforced_routes",
        body=json.dumps(doc).encode(),
    )
    assert len(_entities(report)) == 1
    rejections = _rejections(report)
    assert len(rejections) == 1
    assert rejections[0]["rejection_reason"] == "unsupported_geometry"


def test_howard_area_emits_wkt_and_centroid() -> None:
    """The school-zone polygons: geometry_kind='area' converts the GeoJSON
    polygon column to rings → a fixed_asset_location WKT claim + derived
    centroid + ring_count — never a device-point coordinate."""
    report = _run_fixture(
        "camreg_howard_md_school_zone_ate",
        "howard_school_zones.json",
        "howard_school_zone_areas",
    )
    entities = _entities(report)
    assert len(entities) == 2
    for e in entities:
        assert e["record_kind"] == "ate-speed"
        assert e["geometry_kind"] == "area"
        assert e["geometry_wkt"] and e["geometry_wkt"].startswith("POLYGON")
        assert e["centroid_latitude"] is not None
        assert e["centroid_longitude"] is not None
        assert e["ring_count"] == 1
        assert e["latitude"] is None and e["longitude"] is None
    assert {c["value"] for c in _by_pred(report, "geometry_kind")} == {"area"}
    wkts = [c["value"] for c in _by_pred(report, "fixed_asset_location")]
    assert len(wkts) == 2
    assert all(w.startswith("POLYGON") for w in wkts)
    assert _by_pred(report, "camera_latitude") == []
    assert _by_pred(report, "camera_longitude") == []


# --- the point ATE layers -----------------------------------------------------


def test_the_point_ate_layers_emit_typed_records() -> None:
    """Each ArcGIS point layer emits its declared ATE subtype — including the
    consolidated deldot_red_light under dot_511_de and CTDOT's publisher-
    declared approximate precision mark."""
    cases = [
        ("dot_511_de", "deldot_red_light", "deldot_red_light.json", "ate-red-light"),
        (
            "camreg_montgomery_md_ate",
            "montgomery_speed_cameras_2024",
            "montgomery_speed_cameras_2024.json",
            "ate-speed",
        ),
        ("camreg_tacoma_wa_ate", "tacoma_automated_enforcement", "tacoma_ae.json", "ate-speed"),
        (
            "camreg_lakeland_fl_red_light",
            "lakeland_red_light_cameras",
            "lakeland_red_light.json",
            "ate-red-light",
        ),
        (
            "camreg_suffolk_ny_red_light",
            "suffolk_tpva_red_light_2015",
            "suffolk_red_light_2015.json",
            "ate-red-light",
        ),
        (
            "camreg_medford_or_ate",
            "medford_red_light_speed_cameras",
            "medford_ate.json",
            "ate-unspecified",
        ),
        (
            "camreg_ctdot_speed_safety",
            "ctdot_approximate_speed_safety",
            "ctdot_speed_safety.json",
            "ate-work-zone",
        ),
    ]
    for source_id, target_id, fixture, tech in cases:
        report = _run_fixture(source_id, fixture, target_id)
        entities = _entities(report)
        assert len(entities) == 2, f"{source_id}:{target_id}"
        assert all(e["record_kind"] == tech for e in entities), target_id
        assert all(e["technology"] == tech for e in entities)
        assert all(e["latitude"] is not None and e["longitude"] is not None for e in entities)
        assert not _rejections(report), target_id
    # CTDOT's publisher precision caveat rides the entity + coordinate claims.
    report = _run_fixture(
        "camreg_ctdot_speed_safety",
        "ctdot_speed_safety.json",
        "ctdot_approximate_speed_safety",
    )
    assert all(e["coordinate_precision"] == "approximate" for e in _entities(report))
    for pred in ("camera_latitude", "camera_longitude", "camera_coordinate_source"):
        assert all(c["coordinate_precision"] == "approximate" for c in _by_pred(report, pred))
    # Tacoma's declared direction alias emits verbatim.
    report = _run_fixture("camreg_tacoma_wa_ate", "tacoma_ae.json", "tacoma_automated_enforcement")
    assert {c["value"] for c in _by_pred(report, "camera_direction")} == {"EB", "NB"}


# --- Part VIII: the denied-field surface -------------------------------------


def test_declared_surfaces_carry_no_denied_field() -> None:
    """No P36.6 target row declares a Part VIII denied field in
    observed_fields, out_fields or the aggregate bindings — the F-330
    denylist is a registration refusal, not a capture-time filter."""
    for row in target_table().get("targets", []):
        if (row.get("source_id"), row.get("id")) not in {(s, t) for s, t in ALL_P36_6_TARGETS}:
            continue
        # expansion itself is the fail-closed check — a dirty row refuses.
        expand_registry_rows([row], source_id=str(row["source_id"]))


def test_a_dirty_aggregate_row_refuses_at_expansion() -> None:
    """An aggregate target declaring a denied field — plate/address/citation —
    in its observed or select surface refuses at expansion, before any URL
    is minted."""
    dirty = {
        "id": "dirty",
        "source_id": "camreg_test",
        "kind": "socrata_aggregate",
        "layer_url": "https://data.example.gov/resource/xxxx-yyyy.json",
        "state": "US-MD",
        "agency": "Example",
        "observed_count": 10,
        "observed_fields": "site_number,quarter_name,total,plate",
        "aggregate_subject_field": "site_number",
        "aggregate_period_field": "quarter_name",
        "aggregate_period_kind": "verbatim",
        "aggregate_count_field": "total",
        "aggregate_count_function": "verbatim",
        "aggregate_measure": "violations",
        "technology": "ate-speed",
    }
    with pytest.raises(FieldDenylistViolation):
        expand_registry_rows([dirty], source_id="camreg_test")


def test_denied_values_in_a_capture_never_reach_claims() -> None:
    """The Tacoma fixture deliberately carries denied columns (the published
    `address` column, a `plate_number`) inside a feature's attributes — the
    emit path reads ONLY the declared allowlist aliases, so the values stay
    in the capture and never mint a claim."""
    report = _run_fixture("camreg_tacoma_wa_ate", "tacoma_ae.json", "tacoma_automated_enforcement")
    assert len(_entities(report)) == 2
    blob = json.dumps(report.claims)
    assert "BXY4412" not in blob
    assert "1900 S Jackson Ave" not in blob
    # The allowlisted `location` field is what mints camera_name — the denied
    # `address` column is never the claimed name.
    names = {c["value"] for c in _by_pred(report, "camera_name")}
    assert names == {"S 19th St & S Jackson Ave", "S 56th St & S Tyler St"}
    # No plate/citation/person/trip predicate exists in the connector surface —
    # the aggregate entity rows carry only the registry-keyed fields.
    for c in report.claims:
        assert "citation" not in str(c.get("predicate_id", ""))
        assert "trip" not in str(c.get("predicate_id", ""))
        assert "plate" not in str(c.get("predicate_id", ""))


# --- replay / shadow determinism ----------------------------------------------


def test_montgomery_source_replay_and_shadow_are_deterministic() -> None:
    """+0 shadow re-run over the three-target Montgomery source — aggregate
    + point captures replay to byte-identical claim content
    (SIG-INGEST-003/019)."""
    connector, ctx, fixture_report = _run_source("camreg_montgomery_md_ate")
    replay_a = replay(connector, ctx, fixture_report.captures)
    replay_b = replay(connector, ctx, fixture_report.captures)
    assert replay_fingerprint(replay_a) == replay_fingerprint(replay_b)
    diff = shadow_replay(connector, ctx, fixture_report.captures, fixture_report.claims)
    assert diff.changed_count == 0, f"shadow diff must be empty: {diff.summary()}"


def test_dc_aggregate_pair_replay_is_deterministic() -> None:
    """The outStatistics lane replays deterministically — group-row order and
    the series discriminator are stable claim content."""
    connector, ctx, fixture_report = _run_source("camreg_dc_ddot_ate")
    replay_a = replay(connector, ctx, fixture_report.captures)
    replay_b = replay(connector, ctx, fixture_report.captures)
    assert replay_fingerprint(replay_a) == replay_fingerprint(replay_b)
    diff = shadow_replay(connector, ctx, fixture_report.captures, fixture_report.claims)
    assert diff.changed_count == 0, f"shadow diff must be empty: {diff.summary()}"


def test_mta_line_replay_is_deterministic() -> None:
    """The geometry-free line records replay byte-identically — the absent
    geometry claim surface is stable, never re-asserted."""
    connector, ctx, fixture_report = _run_source("camreg_nyc_mta_bus_lane_ate")
    replay_a = replay(connector, ctx, fixture_report.captures)
    replay_b = replay(connector, ctx, fixture_report.captures)
    assert replay_fingerprint(replay_a) == replay_fingerprint(replay_b)
    diff = shadow_replay(connector, ctx, fixture_report.captures, fixture_report.claims)
    assert diff.changed_count == 0, f"shadow diff must be empty: {diff.summary()}"
