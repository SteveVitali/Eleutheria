# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.5 (R11-ACQ-09): the agency ALPR/Flock layers — fifteen sources carrying
sixteen targets, including the consolidated FDOT District-3 inventory +
removal-status pair (I8 §5.2 — one source, same run).

Drives the REAL ``pipeline.run`` over committed ArcGIS fixtures (no network,
SIG-INGEST-011). Covers: the ``status_disposition="removal"`` valid_to bound
(I9a NEW-2 — a removal is a temporal claim, never a deletion, and never a
fabricated date), the declared ``coordinate_precision="approximate"`` mark
(Milford), the proposed-site status verbatim emit (Prince William), the
Hits/plate-read aggregate exclusion (Shelbyville), the media/person-field
name exclusions (Temecula URL, Alabaster SerialNumber, South Fulton editor
columns), the Leon Overwatch Vigilant-LPR typing, and the fail-closed
declaration checks.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from connectors.dot_511 import (
    CoordinatePrecisionNotDeclared,
    Dot511Connector,
    StatusDispositionNotDeclared,
    assert_target_coordinate_precision,
    assert_target_status_disposition,
    expand_registry_rows,
    registry_targets,
)
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

#: The P36.5 (ACQ-09) fifteen-source / sixteen-target scope — every source is
#: gated until the operator's OP-26 Wave-B flip under ING-GO-B.
P36_5_SOURCE_FIXTURES = {
    "camreg_fdot_flock": (
        "fdot_d3_inventory.json",
        "fdot_d3_flock_inventory",
    ),
    "camreg_pueblo_co_flock": ("pueblo_flock.json", "flock_city_of_pueblo_co"),
    "camreg_rocky_mount_nc_lpr_cameras": (
        "rocky_mount_lpr.json",
        "lpr_cameras_city_of_rocky_mount_nc",
    ),
    "camreg_shelbyville_tn_flock_cameras": (
        "shelbyville_flock.json",
        "flock_cameras_public_city_of_shelbyville_tn",
    ),
    "camreg_temecula_ca_flock_wfl1": ("temecula_flock.json", "flock_wfl1_city_of_temecula_ca"),
    "camreg_marble_falls_tx_flock_locations": (
        "marble_falls_flock.json",
        "flock_locations_city_of_marble_falls_tx",
    ),
    "camreg_va_prince_william_county": (
        "prince_william_safety.json",
        "community_safety_cameras_prince_william_county_va",
    ),
    "camreg_milford_ct_flocklprcam": ("milford_flock.json", "flocklprcam_milford_ct"),
    "camreg_elgin_il_lpr_cameras": ("elgin_lpr.json", "lpr_cameras_city_of_elgin_il"),
    "camreg_south_fulton_ga_lpr_cameras": (
        "south_fulton_lpr.json",
        "lpr_cameras_city_of_south_fulton_ga",
    ),
    "camreg_va_pittsylvania_county_stationary": (
        "pittsylvania_lpr.json",
        "stationary_lpr_pittsylvania_county_va",
    ),
    "camreg_alabaster_al_lpr_cameras": (
        "alabaster_lpr.json",
        "lpr_cameras_city_of_alabaster_al_staff_account",
    ),
    "camreg_thomasville_ga_flock_location": (
        "thomasville_flock.json",
        "flock_location_city_of_thomasville_ga",
    ),
    "camreg_leon_county_fl_overwatch_viewer": (
        "leon_overwatch.json",
        "leon_county_sheriff_s_office_overwatch_viewer_vigilant_fixed_lprs_public_access_cameras",
    ),
    "camreg_ga_peachtree_corners_flock_camera": (
        "peachtree_flock.json",
        "flock_camera_location_city_of_peachtree_corners_ga",
    ),
}

ALL_P36_5_SOURCES = list(P36_5_SOURCE_FIXTURES)


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


def _run_fixture(
    source_id: str,
    fixture: str,
    target_id: str | None = None,
    retrieved_at: datetime = _RETRIEVED,
):
    """Run the connector end-to-end over one committed fixture (no network)."""
    if target_id is None:
        target_id = P36_5_SOURCE_FIXTURES[source_id][1]
    targets = [t for t in live_targets(source_id) if t["id"] == target_id]
    assert targets, f"{source_id}:{target_id} must resolve registry targets"
    body = _FIX.joinpath(fixture).read_bytes()
    responses = {
        t["url"]: _resp(
            t["url"],
            body if t.get("page", 0) == 0 else b'{"features": []}',
            retrieved_at=retrieved_at,
        )
        for t in targets
    }
    connector, ctx = _ctx(source_id, targets, responses)
    return run(connector, ctx)


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


# --- registry expansion + the FDOT same-run pairing ------------------------------


def test_every_p36_5_target_resolves() -> None:
    """All sixteen layers expand from the merged registry across fifteen
    sources — camreg_fdot_flock carries its pair in the same run."""
    total = 0
    for source_id, (_fixture, target_id) in P36_5_SOURCE_FIXTURES.items():
        targets = [t for t in registry_targets(source_id) if t["id"] == target_id]
        assert targets, f"{source_id}:{target_id} has no registry target"
        total += len(targets)
        for t in targets:
            assert t["kind"] == "arcgis_query"
            assert t["url"].startswith(t["layer_url"])
            assert "outSR=4326" in t["url"]
            assert t["state"] and t["agency"]
            assert t["technology"]
            assert t["jurisdiction_scheme"] == "iso.3166_2"
    fdot = registry_targets("camreg_fdot_flock")
    assert {t["id"] for t in fdot} == {
        "fdot_d3_flock_inventory",
        "fdot_flock_removal_status",
    }, "camreg_fdot_flock must carry the inventory + removal targets in the same run"
    # no page splits in this batch (all counts < 1000) — 16 targets, 16 pages
    # on FDOT's pair means page ids overlap; assert per-target uniqueness.
    assert len(fdot) == 2


def test_the_acq01_fdot_stub_ids_are_retired() -> None:
    """The generated pair camreg_fl_d3_flock_camera / camreg_fl_flock_removal_status
    consolidated into camreg_fdot_flock — the old ids name no source or target."""
    from connectors.dot_511 import target_table

    source_ids = {row.get("source_id") for row in target_table().get("targets", [])}
    assert "camreg_fdot_flock" in source_ids
    assert "camreg_fl_d3_flock_camera" not in source_ids
    assert "camreg_fl_flock_removal_status" not in source_ids


def test_every_target_declares_alpr_typing_never_a_fallback() -> None:
    """Every P36.5 target types alpr-fixed by declaration — `traffic_camera`
    is never inferred from the source name (PKG-07)."""
    for source_id in ALL_P36_5_SOURCES:
        for t in registry_targets(source_id):
            assert t["technology"] == "alpr-fixed", t["id"]
            assert t["record_kind"] == "alpr-fixed"


def test_out_fields_allowlist_replaces_the_wildcard() -> None:
    """Every P36.5 target carries the reviewed out_fields allowlist — never
    ``outFields=*`` (P8-5); the object id is auto-appended."""
    for source_id in ALL_P36_5_SOURCES:
        for t in registry_targets(source_id):
            assert "outFields=%2A" not in t["url"]
            assert t.get("out_fields"), f"{t['id']} must declare an out_fields allowlist"


def test_p36_5_targets_apply_the_reviewed_arcgis_budget() -> None:
    """The api_allowlist's ArcGIS request budget rides every expanded target."""
    for source_id in ALL_P36_5_SOURCES:
        for t in registry_targets(source_id):
            assert int(t.get("rate_limit_per_min") or 0) > 0


def test_the_batch_membership_is_fifteen() -> None:
    """ops/cadence.toml r11-layers-02 holds exactly the fifteen gated sources —
    the FDOT pair rides one membership (I8 §5.2)."""
    import tomllib

    data = tomllib.loads((REPO_ROOT / "ops" / "cadence.toml").read_text())
    batch = next(b for b in data["batches"] if b["id"] == "r11-layers-02")
    assert sorted(batch["members"]) == sorted(ALL_P36_5_SOURCES)
    assert len(batch["members"]) == 15
    assert "camreg_fl_d3_flock_camera" not in batch["members"]
    assert "camreg_fl_flock_removal_status" not in batch["members"]


# --- the declared status disposition (valid_to, never a deletion) -----------------


def test_status_disposition_membership_is_validated() -> None:
    """Only the closed 'removal' member is accepted; a removal target without
    its declared removal-value vocabulary is a registry defect."""
    assert assert_target_status_disposition({"id": "x"}) is None
    assert (
        assert_target_status_disposition(
            {
                "id": "x",
                "status_disposition": "removal",
                "removal_status_values": ["removed"],
            }
        )
        == "removal"
    )
    with pytest.raises(StatusDispositionNotDeclared):
        assert_target_status_disposition({"id": "x", "status_disposition": "deprecated"})
    with pytest.raises(StatusDispositionNotDeclared):
        # a removal target MUST declare which published values mean removal —
        # no vocabulary, no bound minted anywhere.
        assert_target_status_disposition({"id": "x", "status_disposition": "removal"})
    with pytest.raises(StatusDispositionNotDeclared):
        expand_registry_rows(
            [
                {
                    "id": "bad",
                    "source_id": "s",
                    "kind": "arcgis_query",
                    "layer_url": "https://example.invalid/0",
                    "state": "US-XX",
                    "agency": "x",
                    "observed_count": 1,
                    "technology": "alpr-fixed",
                    "status_disposition": "removal",
                }
            ]
        )


def test_coordinate_precision_membership_is_validated() -> None:
    """Only the closed 'approximate' member is accepted — an invented label is
    a registry defect, never a per-record caveat (P4)."""
    assert assert_target_coordinate_precision({"id": "x"}) is None
    assert assert_target_coordinate_precision(
        {"id": "x", "coordinate_precision": "approximate"}
    ) == ("approximate")
    with pytest.raises(CoordinatePrecisionNotDeclared):
        assert_target_coordinate_precision({"id": "x", "coordinate_precision": "fuzzy"})
    with pytest.raises(CoordinatePrecisionNotDeclared):
        expand_registry_rows(
            [
                {
                    "id": "bad",
                    "source_id": "s",
                    "kind": "arcgis_query",
                    "layer_url": "https://example.invalid/0",
                    "state": "US-XX",
                    "agency": "x",
                    "observed_count": 1,
                    "technology": "alpr-fixed",
                    "coordinate_precision": "fuzzy",
                }
            ]
        )


def test_fdot_removal_target_expands_with_its_declarations() -> None:
    """The removal target's disposition + vocabulary ride the expanded page
    targets; the inventory target carries no disposition."""
    targets = registry_targets("camreg_fdot_flock")
    removal = [t for t in targets if t["id"] == "fdot_flock_removal_status"]
    inventory = [t for t in targets if t["id"] == "fdot_d3_flock_inventory"]
    assert removal and inventory
    for t in removal:
        assert t["status_disposition"] == "removal"
        assert "removed" in t["removal_status_values"]
    for t in inventory:
        assert "status_disposition" not in t


# --- fixture emits: the ordinary ALPR layers --------------------------------------


def test_pueblo_fixture_uses_the_published_lat_long_fields() -> None:
    report = _run_fixture("camreg_pueblo_co_flock", "pueblo_flock.json")
    entities = _entities(report)
    assert len(entities) == 2
    assert all(e["technology"] == "alpr-fixed" for e in entities)
    assert all(e["record_kind"] == "alpr-fixed" for e in entities)
    assert all(e["coordinate_source"] == "fields:Lat/Long" for e in entities)
    assert {c["value"] for c in _by_pred(report, "camera_jurisdiction")} == {"US-CO"}
    # Serial/Company/Pole/Date_installed carry no predicate — never a claim.
    for claim in _claims(report):
        for value in (claim.get("value"), claim.get("raw_value")):
            assert "FS-88214" not in str(value)
            assert "2024-11-02" not in str(value)
    assert len(_by_pred(report, "technology")) == 2


def test_rocky_mount_fixture_emits_deployment_provenance() -> None:
    report = _run_fixture("camreg_rocky_mount_nc_lpr_cameras", "rocky_mount_lpr.json")
    assert len(_entities(report)) == 2
    assert {c["value"] for c in _by_pred(report, "camera_jurisdiction")} == {"US-NC"}


def test_temecula_fixture_uses_caps_fields_and_drops_url() -> None:
    """LAT/LONG attributes are the coordinate source; the feed-content URL is
    excluded by name, its value never emitted."""
    report = _run_fixture("camreg_temecula_ca_flock_wfl1", "temecula_flock.json")
    entities = _entities(report)
    assert len(entities) == 2
    assert all(e["coordinate_source"] == "fields:LAT/LONG" for e in entities)
    assert {c["value"] for c in _by_pred(report, "camera_name")} == {
        "Rancho California Rd & Ynez Rd",
        "Margarita Rd & Winchester Rd",
    }
    assert all("URL" in e["excluded_fields"] for e in entities)
    for claim in report.claims:
        for value in (claim.get("value"), claim.get("raw_value")):
            assert ".m3u8" not in str(value)
            assert "streams.example" not in str(value)


def test_marble_falls_fixture_maps_name_road_and_city() -> None:
    report = _run_fixture("camreg_marble_falls_tx_flock_locations", "marble_falls_flock.json")
    assert len(_entities(report)) == 2
    assert {c["value"] for c in _by_pred(report, "camera_name")} == {
        "US-281 & 2nd St",
        "FM-1431 & Mormon Mill Rd",
    }
    assert {c["value"] for c in _by_pred(report, "camera_roadway")} == {"US-281", "FM-1431"}
    assert {c["value"] for c in _by_pred(report, "camera_county")} == {"Marble Falls"}


def test_elgin_fixture_emits_location_names() -> None:
    report = _run_fixture("camreg_elgin_il_lpr_cameras", "elgin_lpr.json")
    assert len(_entities(report)) == 2
    assert {c["value"] for c in _by_pred(report, "camera_name")} == {
        "Randall Rd & College Green Dr",
        "McLean Blvd & Rt-20",
    }


def test_south_fulton_fixture_drops_the_editor_columns() -> None:
    """created_user/last_edited_user are person-flavoured — name-excluded,
    their values never reach a claim (P8-5)."""
    report = _run_fixture("camreg_south_fulton_ga_lpr_cameras", "south_fulton_lpr.json")
    entities = _entities(report)
    assert len(entities) == 2
    for e in entities:
        assert "created_user" in e["excluded_fields"]
        assert "last_edited_user" in e["excluded_fields"]
    for claim in report.claims:
        for value in (claim.get("value"), claim.get("raw_value")):
            assert "j.doe" not in str(value)
            assert "gis_admin" not in str(value)


def test_pittsylvania_fixture_emits_minimal_surface() -> None:
    report = _run_fixture("camreg_va_pittsylvania_county_stationary", "pittsylvania_lpr.json")
    assert len(_entities(report)) == 2
    assert {c["value"] for c in _by_pred(report, "camera_name")} == {
        "US-29 & SR-685",
        "US-58 & SR-863",
    }
    assert {c["value"] for c in _by_pred(report, "camera_jurisdiction")} == {"US-VA"}


def test_alabaster_fixture_drops_serial_numbers() -> None:
    """SerialNumber is a media-blocklist member — name-excluded, never emitted."""
    report = _run_fixture("camreg_alabaster_al_lpr_cameras", "alabaster_lpr.json")
    entities = _entities(report)
    assert len(entities) == 2
    assert all("SerialNumber" in e["excluded_fields"] for e in entities)
    assert {c["value"] for c in _by_pred(report, "camera_status")} == {"Active"}
    for claim in report.claims:
        for value in (claim.get("value"), claim.get("raw_value")):
            assert "SN-A-88" not in str(value)


def test_thomasville_fixture_emits_site_survey_rows() -> None:
    report = _run_fixture("camreg_thomasville_ga_flock_location", "thomasville_flock.json")
    assert len(_entities(report)) == 2
    assert {c["value"] for c in _by_pred(report, "camera_jurisdiction")} == {"US-GA"}


def test_leon_fixture_types_vigilant_rows_alpr() -> None:
    """The Overwatch layer-2 Vigilant LPR rows type alpr-fixed — the service's
    RTCC/CCTV layers are separate targets (separate typing) and not this row."""
    report = _run_fixture("camreg_leon_county_fl_overwatch_viewer", "leon_overwatch.json")
    entities = _entities(report)
    assert len(entities) == 2
    assert all(e["technology"] == "alpr-fixed" for e in entities)
    assert all(e["record_kind"] == "alpr-fixed" for e in entities)
    assert {c["value"] for c in _by_pred(report, "camera_jurisdiction")} == {"US-FL"}


def test_peachtree_fixture_drops_display_artifacts() -> None:
    """FolderPath/PopupInfo are KML display artifacts — outside the allowlist,
    never emitted."""
    report = _run_fixture("camreg_ga_peachtree_corners_flock_camera", "peachtree_flock.json")
    assert len(_entities(report)) == 2
    assert {c["value"] for c in _by_pred(report, "camera_name")} == {
        "Peachtree Pkwy & Peachtree Corners Cir",
        "Spalding Dr & Holcomb Bridge Rd",
    }
    for claim in _claims(report):
        for value in (claim.get("value"), claim.get("raw_value")):
            assert "Zone A" not in str(value)
            assert "<b>" not in str(value)


# --- row rules: proposed status, approximate coordinates, Hits exclusion ----------


def test_prince_william_proposed_sites_emit_verbatim_status() -> None:
    """Proposed sites emit camera_status='Proposed' — the published programme
    status verbatim (S5 guard), never a synthesized 'active'."""
    report = _run_fixture("camreg_va_prince_william_county", "prince_william_safety.json")
    entities = _entities(report)
    assert len(entities) == 3
    statuses = _by_pred(report, "camera_status")
    assert {c["value"] for c in statuses} == {"Active", "Proposed"}
    proposed = [c for c in statuses if c["value"] == "Proposed"]
    assert len(proposed) == 2


def test_milford_coordinates_carry_the_declared_approximate_mark() -> None:
    """The layer's published 'approximate locations, not GPS data' caveat rides
    the entity + every coordinate claim — never a silently 'exact' point."""
    report = _run_fixture("camreg_milford_ct_flocklprcam", "milford_flock.json")
    entities = _entities(report)
    assert len(entities) == 2
    for e in entities:
        assert e["coordinate_precision"] == "approximate"
    for predicate in ("camera_latitude", "camera_longitude", "camera_coordinate_source"):
        for c in _by_pred(report, predicate):
            assert c["coordinate_precision"] == "approximate"
    # a non-precision target does NOT stamp the mark — contrast check.
    pueblo = _run_fixture("camreg_pueblo_co_flock", "pueblo_flock.json")
    for e in _entities(pueblo):
        assert "coordinate_precision" not in e
    for c in _by_pred(pueblo, "camera_latitude"):
        assert "coordinate_precision" not in c


def test_shelbyville_hits_aggregates_never_emit() -> None:
    """The JanHits..DecHits plate-read aggregates are Part VIII — out of the
    allowlist AND never emitted even when they leak into a capture."""
    report = _run_fixture("camreg_shelbyville_tn_flock_cameras", "shelbyville_flock.json")
    entities = _entities(report)
    assert len(entities) == 2
    assert {c["value"] for c in _by_pred(report, "camera_direction")} == {"NB", "SB"}
    for claim in report.claims:
        blob = json.dumps(claim, default=str)
        assert "Hits" not in blob
        for value in (claim.get("value"), claim.get("raw_value")):
            assert "1473" not in str(value)
            assert "1042" not in str(value)


# --- the FDOT inventory + removal pair (I9a NEW-2) ---------------------------------


def _run_fdot_pair():
    """One run over BOTH FDOT targets — the same-run pairing the ticket
    requires so a removal fact is never asserted against a stale inventory."""
    targets = live_targets("camreg_fdot_flock")
    assert {t["id"] for t in targets} == {
        "fdot_d3_flock_inventory",
        "fdot_flock_removal_status",
    }
    responses: dict[str, FetchResult] = {}
    for t in targets:
        fixture = (
            "fdot_d3_inventory.json"
            if t["id"] == "fdot_d3_flock_inventory"
            else "fdot_removal_status.json"
        )
        body = _FIX.joinpath(fixture).read_bytes()
        responses[t["url"]] = _resp(t["url"], body)
    connector, ctx = _ctx("camreg_fdot_flock", targets, responses)
    return run(connector, ctx)


def test_fdot_inventory_emits_unbounded_registry_rows() -> None:
    """The inventory layer's rows are ordinary registry claims — no valid_to
    bound anywhere on an inventory emit."""
    report = _run_fixture("camreg_fdot_flock", "fdot_d3_inventory.json", "fdot_d3_flock_inventory")
    entities = _entities(report)
    assert len(entities) == 2
    for c in report.claims:
        assert "valid_to" not in c
        assert "valid_to_kind" not in c
    assert all(e["technology"] == "alpr-fixed" for e in entities)


def test_fdot_removal_rows_bound_valid_to_never_delete() -> None:
    """A published 'Removed' status bounds every claim the row emits — exact
    when a date column is present, unknown when not — append-only (the emit
    carries no delete/retract record for the paired inventory rows)."""
    report = _run_fixture(
        "camreg_fdot_flock", "fdot_removal_status.json", "fdot_flock_removal_status"
    )
    entities = _entities(report)
    assert len(entities) == 3

    # row 501 — 'Removed' + a published date column → exact bound.
    exact = [e for e in entities if e["external_id"] == "501"]
    assert len(exact) == 1
    assert exact[0]["valid_to"] == "2026-03-14"
    assert exact[0]["valid_to_kind"] == "exact"

    # row 502 — 'Removed' with no published date → an ended-when-unknown
    # bound, never a fabricated date (P4).
    unknown = [e for e in entities if e["external_id"] == "502"]
    assert len(unknown) == 1
    assert unknown[0]["valid_to"] is None
    assert unknown[0]["valid_to_kind"] == "unknown"

    # row 503 — 'Non-Compliant' is a permit-compliance fact (S5 guard): the
    # verbatim status rides camera_status, no bound mints — even though the
    # capture carries a date column.
    compliant = [e for e in entities if e["external_id"] == "503"]
    assert len(compliant) == 1
    assert "valid_to" not in compliant[0]
    assert "valid_to_kind" not in compliant[0]
    statuses = _by_pred(report, "camera_status")
    assert {c["value"] for c in statuses} == {"Removed", "Non-Compliant"}
    roadways = _by_pred(report, "camera_roadway")
    assert {c["value"] for c in roadways} == {"I-10", "US-90", "US-98"}
    counties = _by_pred(report, "camera_county")
    assert {c["value"] for c in counties} == {"Leon", "Gadsden", "Bay"}

    # the bound stamps EVERY claim the removed rows emit — never a half-removed
    # device; and nothing in the emit deletes or retracts a prior record.
    for c in report.claims:
        subject = str(c.get("subject_id") or "")
        if subject.endswith(":501") or subject.endswith(":502"):
            assert "valid_to_kind" in c, (subject, c.get("predicate_id"))
    for c in report.claims:
        assert c.get("record_kind") in {"claim", "alpr-fixed"}
        blob = json.dumps(c, default=str)
        assert "DELETE" not in blob


def test_fdot_pair_run_keeps_the_layers_distinct() -> None:
    """Same run, two targets: inventory claims stay unbounded while removal
    claims carry their bounds — the pairing never leaks a bound onto the
    inventory rows (same-run consistency, I8 §5.2)."""
    report = _run_fdot_pair()
    entities = _entities(report)
    assert len(entities) == 5
    for e in entities:
        target = e["target_id"]
        if target == "fdot_d3_flock_inventory":
            assert "valid_to" not in e
        elif target == "fdot_flock_removal_status":
            if e["external_id"] in {"501", "502"}:
                assert "valid_to_kind" in e
            else:
                assert "valid_to" not in e
        else:
            pytest.fail(f"unexpected target {target}")


# --- fail-closed paths ------------------------------------------------------------


def test_a_malformed_feature_is_a_recorded_rejection() -> None:
    """A feature with no usable coordinate lands as camera_record_rejected —
    recorded, never a claim (and never a bound)."""
    doc = {
        "features": [
            {
                "attributes": {"OBJECTID": 1, "Status": "Removed"},
                "geometry": {"x": -84.31, "y": 30.40},
            },
            {
                "attributes": {"OBJECTID": 2, "Status": "Removed"},
                # no geometry, no coordinate fields → the point path rejects.
            },
        ]
    }
    targets = [
        t for t in live_targets("camreg_fdot_flock") if t["id"] == "fdot_flock_removal_status"
    ]
    url = targets[0]["url"]
    connector, ctx = _ctx("camreg_fdot_flock", targets, {url: _resp(url, json.dumps(doc).encode())})
    report = run(connector, ctx)
    assert len(_entities(report)) == 1
    rejections = _rejections(report)
    assert len(rejections) == 1
    assert rejections[0]["rejection_reason"] == "missing"


def test_the_removal_bound_never_fires_on_an_undeclared_status() -> None:
    """A status value outside removal_status_values mints NO bound — the
    closed vocabulary is the only route to valid_to (the S5 guard)."""
    doc = {
        "features": [
            {
                "attributes": {
                    "OBJECTID": 9,
                    "Status": "Offline",
                    "Last_Date": "2026-01-01",
                },
                "geometry": {"x": -84.31, "y": 30.40},
            },
        ]
    }
    targets = [
        t for t in live_targets("camreg_fdot_flock") if t["id"] == "fdot_flock_removal_status"
    ]
    url = targets[0]["url"]
    connector, ctx = _ctx("camreg_fdot_flock", targets, {url: _resp(url, json.dumps(doc).encode())})
    report = run(connector, ctx)
    entities = _entities(report)
    assert len(entities) == 1
    assert "valid_to" not in entities[0]
    assert "valid_to_kind" not in entities[0]


# --- the rights gate ------------------------------------------------------------


def test_all_fifteen_sources_stay_gated() -> None:
    """Every P36.5 source row refuses the live gate — the operator's OP-26
    Wave-B flip under ING-GO-B is the only route to a live fetch."""
    from connectors.runner import live_gate_reasons

    for source_id in ALL_P36_5_SOURCES:
        reasons = live_gate_reasons(source_id)
        assert reasons, f"{source_id} must stay gated"
        source = get(source_id)
        assert source.ingestion_permitted is False


def test_the_existing_leon_source_is_untouched() -> None:
    """camreg_leon_fl (the already-permitted traffic-camera org) is a DIFFERENT
    publisher than the Overwatch service — the new source never retypes it."""
    leon = get("camreg_leon_fl")
    assert leon.ingestion_permitted is True
    overwatch = get("camreg_leon_county_fl_overwatch_viewer")
    assert overwatch.ingestion_permitted is False
    leon_targets = registry_targets("camreg_leon_fl")
    assert any("cotinter.leoncountyfl.gov" in t["layer_url"] for t in leon_targets)
    assert "ptvDyBs1KkcwzQNJ" in overwatch.homepage_url


# --- replay / shadow determinism ------------------------------------------------


def test_fdot_pair_replay_and_shadow_are_deterministic() -> None:
    """+0 shadow re-run over the paired FDOT capture — the removal bounds are
    deterministic claim content (SIG-INGEST-003/019)."""
    targets = live_targets("camreg_fdot_flock")
    responses: dict[str, FetchResult] = {}
    for t in targets:
        fixture = (
            "fdot_d3_inventory.json"
            if t["id"] == "fdot_d3_flock_inventory"
            else "fdot_removal_status.json"
        )
        responses[t["url"]] = _resp(t["url"], _FIX.joinpath(fixture).read_bytes())
    connector, ctx = _ctx("camreg_fdot_flock", targets, responses)
    fixture_report = run(connector, ctx)
    replay_a = replay(connector, ctx, fixture_report.captures)
    replay_b = replay(connector, ctx, fixture_report.captures)
    assert replay_fingerprint(replay_a) == replay_fingerprint(replay_b)
    diff = shadow_replay(connector, ctx, fixture_report.captures, fixture_report.claims)
    assert diff.changed_count == 0, f"shadow diff must be empty: {diff.summary()}"


def test_milford_replay_is_deterministic() -> None:
    """The declared precision mark is stable claim content across replays."""
    targets = [
        t
        for t in live_targets("camreg_milford_ct_flocklprcam")
        if t["id"] == "flocklprcam_milford_ct"
    ]
    url = targets[0]["url"]
    body = _FIX.joinpath("milford_flock.json").read_bytes()
    connector, ctx = _ctx("camreg_milford_ct_flocklprcam", targets, {url: _resp(url, body)})
    fixture_report = run(connector, ctx)
    replay_a = replay(connector, ctx, fixture_report.captures)
    replay_b = replay(connector, ctx, fixture_report.captures)
    assert replay_fingerprint(replay_a) == replay_fingerprint(replay_b)
    diff = shadow_replay(connector, ctx, fixture_report.captures, fixture_report.claims)
    assert diff.changed_count == 0, f"shadow diff must be empty: {diff.summary()}"
