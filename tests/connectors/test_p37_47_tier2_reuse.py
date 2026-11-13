# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.47 (R11-ACQ-19) — the Tier-2 reuse wave (I8 §6.2).

Thirty gated seats — ten pinned camera-layer target rows over the merged
dot_511 registry (eight new sources plus the WVPA layer-23 and Bellevue
speed-safety lanes riding the existing dot_511_wv / camreg_bellevue_wa
registrations) and twenty dossier_documents rows (seventeen new registrations
plus the three RB-09 flips of existing gated rows: ccops_boston,
ccops_berkeley, dhs_fusion_centers). Every row stays
``ingestion_permitted=false`` — the operator's OP-26 Wave-D flip under
ING-GO-D is the only route to live. Replay runs over the committed synthetic
fixtures (fixtures/p37_47/SOURCES.md) with no network.
"""

import dataclasses
import tomllib
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from connectors.dossier_documents import (
    DOSSIER_SOURCES,
    DossierDocumentsConnector,
    adapter_config,
)
from connectors.dot_511 import Dot511Connector
from connectors.live_targets import live_targets
from connectors.net import PoliteFetcher, RateLimiter, RobotsResult
from connectors.pipeline import run
from connectors.registry import CompactStatus, get
from connectors.runner import CONNECTOR_FOR_SOURCE, live_gate_reasons
from connectors.stages import (
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun

_RETRIEVED = datetime(2026, 10, 1, tzinfo=UTC)
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


_FIX = Path(__file__).parent / "fixtures" / "p37_47"

_LAYER_SOURCES = {
    "dot_511_nm",
    "dot_511_nv",
    "dot_511_id",
    "camreg_jeffersonville_in_flock",
    "camreg_ca_monterey_park_flock_camera",
    "camreg_santa_fe_nm_park_cameras",
    "camreg_fl_broward_county_us_palm_beach",
    "camreg_nv_las_vegas_us_clark_county",
}
_DOSSIER_SOURCES = {
    "legis_vi_legislature_virgin_islands",
    "ccops_mi_wayne_county_commission",
    "ccops_hi_honolulu_police_department",
    "statrep_new_york_ny_nyc_doi_oig",
    "statrep_us_upturn_mass_extraction_2020",
    "ccops_ny_new_york_nyc_comptroller",
    "policy_anaheim_ca_pd_policy_manual",
    "ccops_nc_charlotte_mecklenburg_police",
    "grant_us_doj_cops_technology",
    "grant_ok_safe_oklahoma_grant",
    "statrep_tx_ca_nm_ri_fl_il_eff_red_flag",
    "ccops_nc_elizabeth_city_police",
    "ccops_il_chicago_oig_shotspotter",
    "ccops_san_francisco_bay_ca",
    "ccops_mo_st_louis_fy21_spi_shotspotter",
    "ccops_san_jose_ca",
    "ccops_santa_clara_county_ca",
    "policy_maricopa_county_az_mcso_policies",
    "policy_norman_ok_alpr_policy_amendment",
    "ccops_boston",
    "ccops_berkeley",
    "dhs_fusion_centers",
}
_SOURCES = _LAYER_SOURCES | _DOSSIER_SOURCES

_LAYER_FIXTURES = {
    "dot_511_nm": "statewide_cctv_view.json",
    "dot_511_nv": "its_atm.json",
    "dot_511_id": "cctv_itd.json",
    "camreg_jeffersonville_in_flock": "flock_jeffersonville.json",
    "camreg_ca_monterey_park_flock_camera": "flock_monterey.json",
    "camreg_santa_fe_nm_park_cameras": "park_santa_fe.json",
    "camreg_fl_broward_county_us_palm_beach": "d4_survey.json",
    "camreg_nv_las_vegas_us_clark_county": "metrocams.json",
}
_DOSSIER_FIXTURES = {
    "legis_vi_legislature_virgin_islands": "legvi_bill.html",
    "ccops_mi_wayne_county_commission": "wayne_commission.html",
    "ccops_hi_honolulu_police_department": "hpd_alpr_policy.html",
    "statrep_new_york_ny_nyc_doi_oig": "nyc_doi_reports.html",
    "statrep_us_upturn_mass_extraction_2020": "upturn_index.html",
    "ccops_ny_new_york_nyc_comptroller": "nyc_comptroller_bwc.html",
    "policy_anaheim_ca_pd_policy_manual": "anaheim_manual.html",
    "ccops_nc_charlotte_mecklenburg_police": "cmpd_directives.html",
    "grant_us_doj_cops_technology": "doj_cops.html",
    "grant_ok_safe_oklahoma_grant": "ok_safe_grant.html",
    "statrep_tx_ca_nm_ri_fl_il_eff_red_flag": "eff_red_flag.html",
    "ccops_nc_elizabeth_city_police": "elizabeth_memo.html",
    "ccops_il_chicago_oig_shotspotter": "chicago_oig.html",
    "ccops_san_francisco_bay_ca": "bart_index.html",
    "ccops_mo_st_louis_fy21_spi_shotspotter": "slmpd_eval.html",
    "ccops_san_jose_ca": "san_jose_register.html",
    "ccops_santa_clara_county_ca": "santa_clara_index.html",
    "policy_maricopa_county_az_mcso_policies": "mcso_policies.html",
    "policy_norman_ok_alpr_policy_amendment": "norman_manual.html",
    "ccops_boston": "boston_asr.html",
    "ccops_berkeley": "berkeley_index.html",
    "dhs_fusion_centers": "dhs_fusion_roster.html",
}


def _run_fixture(source_id: str):
    """Run the source's connector over its committed fixture (no network)."""
    fixture = (_LAYER_FIXTURES | _DOSSIER_FIXTURES)[source_id]
    targets = [dict(t) for t in live_targets(source_id)]
    assert targets, f"{source_id} resolves no reviewed targets"
    body = (_FIX / fixture).read_bytes()
    media = "application/json" if fixture.endswith(".json") else "text/html"
    connector: Any = (
        Dot511Connector() if source_id in _LAYER_SOURCES else DossierDocumentsConnector()
    )
    source = dataclasses.replace(
        get(source_id),
        ingestion_permitted=True,
        compact_status=CompactStatus.PUBLIC_TERMS_ONLY,
    )
    responses = {
        str(t["url"]): FetchResult(url=str(t["url"]), status=200, body=body, media_type=media)
        for t in targets
    }
    fetcher = PoliteFetcher(
        connector_name=connector.name,
        connector_version=connector.version,
        transport=MapTransport(responses),
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
    return run(connector, ctx)


def _claims(report: Any) -> list[dict[str, Any]]:
    return [dict(c) for c in report.claims if c.get("record_kind") == "claim"]


# --- registration, routing, gating (HG-03) -------------------------------------


def test_the_thirty_sources_are_registered_routed_and_gated() -> None:
    for source_id in _LAYER_SOURCES:
        rec = get(source_id)
        assert CONNECTOR_FOR_SOURCE[source_id] == "dot_511", source_id
        assert rec.ingestion_permitted is False, source_id
    for source_id in _DOSSIER_SOURCES:
        rec = get(source_id)
        assert CONNECTOR_FOR_SOURCE[source_id] == "dossier_documents", source_id
        assert rec.ingestion_permitted is False, source_id


def test_the_dispositions_table_carries_no_p37_47_rows() -> None:
    # P25.6 exactly-once: a connector-mapped source carries NO disposition row
    # — the 27 `promote` placeholder seats and the three `reference` seats of
    # the RB-09 flip rows resolved when this row wired the connector map.
    disp = tomllib.loads(Path("connectors/src/connectors/data/live_dispositions.toml").read_text())
    seats = disp.get("sources") or {}
    for source_id in _SOURCES:
        assert source_id not in seats, source_id


def test_every_source_is_refused_for_a_live_run() -> None:
    # SIG-INGEST-014/028: a non-green review status refuses at the loader gate
    # BEFORE any transport is constructed — no live verification is claimed.
    for source_id in _SOURCES:
        assert live_gate_reasons(source_id), source_id


def test_the_dossier_sources_join_the_closed_source_set() -> None:
    for source_id in _DOSSIER_SOURCES:
        assert source_id in DOSSIER_SOURCES, source_id
        adapter = adapter_config(source_id)
        assert adapter["source_id"] == source_id


def test_every_source_has_reviewed_live_targets() -> None:
    for source_id in _SOURCES:
        targets = live_targets(source_id)
        assert targets, f"{source_id} has no live target registered"
        for target in targets:
            assert str(target["url"]).startswith("https://"), (source_id, target)


def test_the_sources_ride_tier2_batches() -> None:
    cadence = tomllib.loads(Path("ops/cadence.toml").read_text())
    members = {m for b in cadence["batches"] if "tier2" in b["id"] for m in b["members"]}
    assert _SOURCES <= members


# --- fixture-verified replay (the acceptance shape) -----------------------------


def test_every_source_replays_clean_over_its_committed_fixture() -> None:
    for source_id in _LAYER_SOURCES | _DOSSIER_SOURCES:
        report = _run_fixture(source_id)
        assert report.claims, f"{source_id} emitted no rows over its fixture"


def test_replay_rerun_is_plus_zero() -> None:
    # The second run emits no new rows and no different assertions — the
    # per-run evidence stamps (retrieved_at, capture digests) vary by design.
    for source_id in _LAYER_SOURCES | _DOSSIER_SOURCES:
        key = lambda c: (  # noqa: E731
            c.get("subject_id"),
            c.get("predicate_id"),
            str(c.get("value")),
            str(c.get("raw_value")),
        )
        first = sorted(key(c) for c in _claims(_run_fixture(source_id)))
        second = sorted(key(c) for c in _claims(_run_fixture(source_id)))
        assert first == second, source_id


def test_the_s2_screens_pin_minimal_surfaces() -> None:
    # The three S2-flagged layer rows (Broward D4 survey, Las Vegas
    # metrocams, NDOT ITS_ATM) carry the minimal OBJECTID allowlist — the
    # operator-identifier fields the candidates flagged are never requested.
    camreg = tomllib.loads(
        Path("connectors/src/connectors/data/camera_registry_targets.toml").read_text()
    )
    d511 = tomllib.loads(Path("connectors/src/connectors/data/dot_511_targets.toml").read_text())
    targets = {t["id"]: t for t in camreg["targets"] + d511["targets"]}
    broward = targets["d4_camera_survey_fdot_district_4_row_camera_inventory_form"]
    assert broward["out_fields"] == ["OBJECTID"]
    vegas = targets["shotspotter_and_metrocams_wfl1_layers_metrocams_shotspotter"]
    assert vegas["out_fields"] == ["OBJECTID"]
    ndot = targets["its_atm_existing_devices_ndot_statewide_its_atm_masterplan_layer_3"]
    assert ndot["where"] == "Device_Typ='CCTV'"


def test_the_curated_index_rows_emit_citations_only() -> None:
    # The two curated_index S3 aggregate-only rows emit document-citation
    # claims only — no person-name, registrant, or per-agency row predicates
    # exist in their adapter allowlists by construction.
    for source_id in (
        "statrep_us_upturn_mass_extraction_2020",
        "statrep_tx_ca_nm_ri_fl_il_eff_red_flag",
    ):
        allowed = set(adapter_config(source_id)["predicate_allowlist"])
        assert allowed <= {"title", "document", "posted_date", "disclosure_field_state"}, source_id


def test_verification_first_findings_are_recorded_on_the_layer_rows() -> None:
    # The verification-first rows carry their review findings verbatim in the
    # target notes — an unverified publisher or broken upstream geometry is
    # recorded, never silently resolved.
    d511 = tomllib.loads(Path("connectors/src/connectors/data/dot_511_targets.toml").read_text())
    camreg = tomllib.loads(
        Path("connectors/src/connectors/data/camera_registry_targets.toml").read_text()
    )
    targets = {t["id"]: t for t in camreg["targets"] + d511["targets"]}
    wvpa = targets["cctv_wvpa_wvdot_assets_mapserver_layer_23"]
    assert "geometry" in wvpa["notes"].lower()
    nmdot = targets["statewide_cctv_view"]
    assert "org-identity-verified" in nmdot["notes"].lower()
