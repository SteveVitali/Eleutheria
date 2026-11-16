# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.53 (R11-ACQ-26, I7-S1 `a`) — the S1 programme-level lane.

Twenty gated seats: nine camera-layer sources ride ``dot_511``'s new
``arcgis_s1`` kind (``operator_screen`` — Savannah, East Baton Rouge,
Gastonia, Brookhaven — fetches agency-operator rows only behind a
server-side ``IN`` screen and collapses the private-operator complement to
ONE ``returnCountOnly`` count claim; ``count_only`` — Detroit Project Green
Light, the unresolved-CCSO Flock layer, the Bloomington/Peoria/Medford
police-drone flight logs — serves the published total whole, no row bytes
captured). Ten document seats ride ``dossier_documents`` ``clause_fields``
emitting programme-surface facts only (portal existence, title, technology,
enacting body — never registrant content). The Eye-on-Surveillance New
Orleans seat rides the new ``django_rest_api`` connector's screened count
page. The three FAMILY umbrella rows (the Flock hub-search, the drone-log
hub-search, the FAM-PREG-PAGES registry-page family) stay unmapped recorded
dispositions (D-P37.53-1). Every row stays ``ingestion_permitted=false`` —
the operator's OP-26 Wave-D flip under ING-GO-D is the only route to live.
Replay runs over the committed synthetic fixtures (fixtures/p37_53/
SOURCES.md) with no network.
"""

import dataclasses
import tomllib
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from connectors.django_rest_api import DjangoRestApiConnector
from connectors.dossier_documents import (
    DOSSIER_SOURCES,
    DossierDocumentsConnector,
    adapter_config,
    check_crosswalk,
)
from connectors.dot_511 import (
    Dot511Connector,
    S1SpecNotDeclared,
    assert_target_s1,
    target_aggregate_violations,
)
from connectors.field_denylist import (
    FieldDenylistViolation,
    assert_target_fields_clean,
)
from connectors.live_targets import live_targets
from connectors.net import PoliteFetcher, RateLimiter, RobotsResult
from connectors.pipeline import run
from connectors.registry import CompactStatus, get
from connectors.runner import CONNECTOR_FOR_SOURCE, live_gate_reasons
from connectors.stages import (
    ContentDrift,
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


_FIX = Path(__file__).parent / "fixtures" / "p37_53"

#: The nine camera-layer seats (dot_511 / arcgis_s1).
_LAYER_SOURCES = {
    "camreg_detroit_mi_project_green_light",
    "camreg_ga_savannah_flock_camera",
    "camreg_la_east_baton_rouge_parish_flock",
    "camreg_ga_flock_cameras_asof",
    "camreg_gastonia_nc_flock_condor_cameras",
    "camreg_ga_brookhaven_flock_camera",
    "camreg_bloomington_il_drone_flights",
    "camreg_peoria_il_drone_usage",
    "camreg_medford_or_drone_deployments_fs",
}
#: The ten dossier clause_fields seats.
_DOSSIER_SOURCES = {
    "statrep_vt_vermont_law_enforcement",
    "agenda_us_agency_fusus_real",
    "policy_chicago_il_oemc_link_your",
    "ccops_oh_cincinnati_police_department",
    "policy_lafayette_in_camera_registration",
    "policy_zionsville_in_camera_registry",
    "ccops_ri_narragansett_police_camera",
    "ccops_ca_calistoga_police_department",
    "ccops_ca_pinole_police_department",
    "ccops_mn_dayton_police_department",
}
_DRF_SOURCES = {"camreg_la_new_orleans_eye_on"}
#: The three FAMILY umbrella rows — unmapped recorded dispositions, never
#: fetchable targets (D-P37.53-1).
_FAMILY_SOURCES = {
    "camreg_us_agency_published_flock",
    "camreg_us_agency_drone_flight",
    "policy_us_private_camera_registry",
}
_SOURCES = _LAYER_SOURCES | _DOSSIER_SOURCES | _DRF_SOURCES

#: operator_screen seats carry a features fixture AND a count fixture;
#: count_only seats carry the count fixture only.
_LAYER_FIXTURES = {
    "camreg_ga_savannah_flock_camera": ("savannah_features.json", "savannah_count.json"),
    "camreg_la_east_baton_rouge_parish_flock": ("ebr_features.json", "ebr_count.json"),
    "camreg_gastonia_nc_flock_condor_cameras": (
        "gastonia_features.json",
        "gastonia_count.json",
    ),
    "camreg_ga_brookhaven_flock_camera": (
        "brookhaven_features.json",
        "brookhaven_count.json",
    ),
    "camreg_detroit_mi_project_green_light": (None, "detroit_count.json"),
    "camreg_ga_flock_cameras_asof": (None, "ccso_count.json"),
    "camreg_bloomington_il_drone_flights": (None, "bloomington_count.json"),
    "camreg_peoria_il_drone_usage": (None, "peoria_count.json"),
    "camreg_medford_or_drone_deployments_fs": (None, "medford_count.json"),
}
_DOSSIER_FIXTURES = {
    "statrep_vt_vermont_law_enforcement": "vt_uas_report.html",
    "agenda_us_agency_fusus_real": "elizabeth_fusus.html",
    "policy_chicago_il_oemc_link_your": "chicago_link.html",
    "ccops_oh_cincinnati_police_department": "cincinnati_registry.html",
    "policy_lafayette_in_camera_registration": "lafayette_registration.html",
    "policy_zionsville_in_camera_registry": "zionsville_registry.html",
    "ccops_ri_narragansett_police_camera": "narragansett_registry.html",
    "ccops_ca_calistoga_police_department": "calistoga_registry.html",
    "ccops_ca_pinole_police_department": "pinole_registry.html",
    "ccops_mn_dayton_police_department": "dayton_registry.html",
}
_DRF_FIXTURES = {"camreg_la_new_orleans_eye_on": "eye_on_nola.json"}


def _connect_for(source_id: str) -> Any:
    if source_id in _LAYER_SOURCES:
        return Dot511Connector()
    if source_id in _DRF_SOURCES:
        return DjangoRestApiConnector()
    return DossierDocumentsConnector()


def _run_fixture(source_id: str):
    """Run the source's connector over its committed fixture (no network)."""
    targets = [dict(t) for t in live_targets(source_id)]
    assert targets, f"{source_id} resolves no reviewed targets"
    responses: dict[str, FetchResult] = {}
    if source_id in _LAYER_SOURCES:
        features_name, count_name = _LAYER_FIXTURES[source_id]
        features_body = (_FIX / features_name).read_bytes() if features_name else b""
        count_body = (_FIX / count_name).read_bytes()
        for t in targets:
            role = str(t.get("page_role") or "features")
            body = count_body if role == "count" else features_body
            responses[str(t["url"])] = FetchResult(
                url=str(t["url"]), status=200, body=body, media_type="application/json"
            )
    elif source_id in _DRF_SOURCES:
        body = (_FIX / _DRF_FIXTURES[source_id]).read_bytes()
        for t in targets:
            responses[str(t["url"])] = FetchResult(
                url=str(t["url"]), status=200, body=body, media_type="application/json"
            )
    else:
        body = (_FIX / _DOSSIER_FIXTURES[source_id]).read_bytes()
        for t in targets:
            responses[str(t["url"])] = FetchResult(
                url=str(t["url"]), status=200, body=body, media_type="text/html"
            )
    connector = _connect_for(source_id)
    source = dataclasses.replace(
        get(source_id),
        ingestion_permitted=True,
        compact_status=CompactStatus.PUBLIC_TERMS_ONLY,
    )
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


def test_the_twenty_sources_are_registered_routed_and_gated() -> None:
    for source_id in _LAYER_SOURCES:
        rec = get(source_id)
        assert CONNECTOR_FOR_SOURCE[source_id] == "dot_511", source_id
        assert rec.ingestion_permitted is False, source_id
    for source_id in _DOSSIER_SOURCES:
        rec = get(source_id)
        assert CONNECTOR_FOR_SOURCE[source_id] == "dossier_documents", source_id
        assert rec.ingestion_permitted is False, source_id
    for source_id in _DRF_SOURCES:
        rec = get(source_id)
        assert CONNECTOR_FOR_SOURCE[source_id] == "django_rest_api", source_id
        assert rec.ingestion_permitted is False, source_id


def test_the_family_umbrella_rows_stay_unmapped() -> None:
    for source_id in _FAMILY_SOURCES:
        assert source_id not in CONNECTOR_FOR_SOURCE, source_id
        assert get(source_id).ingestion_permitted is False, source_id
        assert live_targets(source_id) == [], source_id


def test_the_dispositions_table_carries_only_the_family_rows() -> None:
    # P25.6 exactly-once: a connector-mapped source carries NO disposition
    # row — the 20 wired seats' `promote` placeholders resolved when this
    # row wired the connector map; the three family umbrellas keep theirs
    # pending per-member registration (D-P37.53-1).
    disp = tomllib.loads(Path("connectors/src/connectors/data/live_dispositions.toml").read_text())
    seats = disp.get("sources") or {}
    for source_id in _SOURCES:
        assert source_id not in seats, source_id
    for source_id in _FAMILY_SOURCES:
        assert seats[source_id]["disposition"] == "promote", source_id


def test_every_source_is_refused_for_a_live_run() -> None:
    # SIG-INGEST-014/028: a non-green review status refuses at the loader
    # gate BEFORE any transport is constructed — no live verification is
    # claimed.
    for source_id in _SOURCES | _FAMILY_SOURCES:
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


def test_the_crosswalk_resolves_every_configured_field() -> None:
    # The frozen crosswalk is the only field->predicate route — the ten new
    # seats' configured fields (incl. `registration_portal` ->
    # camera_registration_portal) resolve against committed ontology
    # predicates; nothing ad-hoc (SIG-ACQ-003).
    assert check_crosswalk() == []


def test_the_registry_validates_clean() -> None:
    # Every committed target row's aggregate AND s1 declarations validate —
    # a malformed declaration is a registry defect, never a guessed emit.
    assert target_aggregate_violations() == []


# --- the S1 declaration gate ----------------------------------------------------


def test_s1_members_on_a_non_s1_kind_are_a_registry_defect() -> None:
    with pytest.raises(S1SpecNotDeclared):
        assert_target_s1({"id": "t", "kind": "arcgis_query", "s1_mode": "count_only"})


def test_a_missing_mode_is_a_registry_defect() -> None:
    with pytest.raises(S1SpecNotDeclared):
        assert_target_s1({"id": "t", "kind": "arcgis_s1"})


def test_an_operator_screen_needs_its_screen_vocabulary() -> None:
    with pytest.raises(S1SpecNotDeclared):
        assert_target_s1(
            {
                "id": "t",
                "kind": "arcgis_s1",
                "s1_mode": "operator_screen",
                "s1_measure": "rows",
                "s1_period_label": "p",
                "s1_programme_label": "prog",
            }
        )


def test_a_count_only_row_refuses_screen_vocabulary() -> None:
    with pytest.raises(S1SpecNotDeclared):
        assert_target_s1(
            {
                "id": "t",
                "kind": "arcgis_s1",
                "s1_mode": "count_only",
                "s1_operator_field": "Org_Name",
                "s1_measure": "rows",
                "s1_period_label": "p",
                "s1_programme_label": "prog",
            }
        )


def test_a_hand_written_where_is_a_registry_defect() -> None:
    # The lane composes its screen internally — a committed `where` is never
    # legal on an arcgis_s1 row.
    with pytest.raises(S1SpecNotDeclared):
        assert_target_s1(
            {
                "id": "t",
                "kind": "arcgis_s1",
                "where": "1=1",
                "s1_mode": "count_only",
                "s1_measure": "rows",
                "s1_period_label": "p",
                "s1_programme_label": "prog",
            }
        )


def test_the_denylist_refuses_a_denied_screen_column() -> None:
    # F-330: an operator_screen target whose declared screen column is a
    # Part VIII denied field name is refused at registration — never fetched.
    with pytest.raises(FieldDenylistViolation):
        assert_target_fields_clean(
            {
                "id": "t",
                "kind": "arcgis_s1",
                "platform": "arcgis",
                "s1_operator_field": "registrant_name",
            }
        )


def test_the_denylist_refuses_denied_out_fields_on_an_s1_row() -> None:
    with pytest.raises(FieldDenylistViolation):
        assert_target_fields_clean(
            {
                "id": "t",
                "kind": "arcgis_s1",
                "platform": "arcgis",
                "out_fields": ["OBJECTID", "license_plate"],
            }
        )


# --- expansion shapes ------------------------------------------------------------


def _row_by_id(target_id: str) -> dict[str, Any]:
    camreg = tomllib.loads(
        Path("connectors/src/connectors/data/camera_registry_targets.toml").read_text()
    )
    return next(t for t in camreg["targets"] if t["id"] == target_id)


def test_the_nine_s1_rows_are_the_screened_lane() -> None:
    camreg = tomllib.loads(
        Path("connectors/src/connectors/data/camera_registry_targets.toml").read_text()
    )
    s1 = {t["id"]: t for t in camreg["targets"] if t.get("kind") == "arcgis_s1"}
    assert set(s1) == {
        "project_green_light_locations",
        "flock_camera_locations2_savannah_police_department",
        "flock_location_data_view_east_baton_rouge_sheriff_s_office",
        "flock_cameras_asof_20240318_ccso_west_georgia_org_unresolved",
        "city_of_gastonia_nc_flock_layers_condor_cameras_lpr_flock_os_integration_layers",
        "flock_camera_locations_sep_2023_city_of_brookhaven_ga",
        "police_drone_flights",
        "peoria_police_department_drone_usage",
        "drone_deployments_fs",
    }
    screens = [t for t in s1.values() if t["s1_mode"] == "operator_screen"]
    counts = [t for t in s1.values() if t["s1_mode"] == "count_only"]
    assert len(screens) == 4
    assert len(counts) == 5
    # Every screen seat carries the minimal allowlist — OBJECTID + geometry
    # only; the private-operator value list is never declared anywhere.
    for t in screens:
        assert t["out_fields"] == ["OBJECTID"], t["id"]
        assert t["s1_agency_values"], t["id"]
        assert all("private" not in str(v).lower() for v in t["s1_agency_values"])
    for t in counts:
        assert "s1_operator_field" not in t, t["id"]
        assert "out_fields" not in t or t.get("out_fields") == [], t["id"]


def test_the_operator_screen_expands_to_agency_pages_plus_one_count() -> None:
    targets = live_targets("camreg_gastonia_nc_flock_condor_cameras")
    roles = [str(t.get("page_role") or "features") for t in targets]
    assert roles.count("count") == 1
    assert roles.count("features") == len(targets) - 1
    feature_url = next(t["url"] for t in targets if t.get("page_role") != "count")
    count_url = next(t["url"] for t in targets if t.get("page_role") == "count")
    # The feature pages ask the server for the committed agency-operator
    # rows ONLY — the screen is the `IN` clause; the private list never
    # appears.
    assert "Org_Name+IN+%28%27City+of+Gastonia%27%29" in feature_url
    assert "returnCountOnly" not in feature_url
    # The count page asks for the complement — everything the agency screen
    # does not admit — as a count, never a row set.
    assert "returnCountOnly%3Dtrue" in count_url or "returnCountOnly=true" in count_url
    assert "NOT%28" in count_url or "NOT(" in count_url


def test_a_count_only_seat_expands_to_one_count_page() -> None:
    targets = live_targets("camreg_detroit_mi_project_green_light")
    assert len(targets) == 1
    assert targets[0].get("page_role") == "count"
    assert "returnCountOnly" in targets[0]["url"]


# --- fixture-verified replay (the acceptance shape) ----------------------------


def test_every_source_replays_clean_over_its_committed_fixture() -> None:
    for source_id in _SOURCES:
        report = _run_fixture(source_id)
        assert report.claims, f"{source_id} emitted no rows over its fixture"


def test_replay_rerun_is_plus_zero() -> None:
    # The second run emits no new rows and no different assertions — the
    # per-run evidence stamps (retrieved_at, capture digests) vary by design.
    for source_id in _SOURCES:
        key = lambda c: (  # noqa: E731
            c.get("subject_id"),
            c.get("predicate_id"),
            str(c.get("value")),
            str(c.get("raw_value")),
        )
        first = sorted(key(c) for c in _claims(_run_fixture(source_id)))
        second = sorted(key(c) for c in _claims(_run_fixture(source_id)))
        assert first == second, source_id


def test_the_operator_screen_keeps_agency_rows_as_devices() -> None:
    # Agency-operated rows stay device-level camera records; the
    # private-operator complement mints one programme_area subject +
    # programme_count — never a per-private-row claim.
    report = _run_fixture("camreg_gastonia_nc_flock_condor_cameras")
    claims = _claims(report)
    cameras = [c for c in claims if str(c.get("subject_id") or "").startswith("traffic_camera:")]
    assert cameras, "the agency rows mint no device subjects"
    programmes = [c for c in claims if str(c.get("subject_id") or "").startswith("programme_area:")]
    assert programmes, "the complement mints no programme subject"
    predicates = {c["predicate_id"] for c in programmes}
    assert predicates <= {
        "external_id",
        "technology",
        "camera_registry_publisher",
        "programme_area",
        "programme_count",
    }, predicates
    count = next(c for c in programmes if c["predicate_id"] == "programme_count")
    assert count["value"] == 57
    assert count["measure"] == "non_agency_operator_rows"
    assert count["period"] == "all published rows at capture"
    # The technology typing and jurisdiction key ride the claims.
    assert next(c for c in cameras if c["predicate_id"] == "technology")["value"] == "alpr-fixed"
    jurisdictions = [c for c in cameras if c["predicate_id"] == "camera_jurisdiction"]
    assert jurisdictions and jurisdictions[0]["value"] == "US-NC"


def test_a_count_only_seat_emits_programme_facts_only() -> None:
    report = _run_fixture("camreg_bloomington_il_drone_flights")
    claims = _claims(report)
    assert claims, "the count page mints no claims"
    subjects = {str(c["subject_id"]) for c in claims}
    assert all(s.startswith("programme_area:") for s in subjects), subjects
    predicates = {c["predicate_id"] for c in claims}
    assert predicates <= {
        "external_id",
        "technology",
        "camera_registry_publisher",
        "programme_area",
        "programme_count",
    }, predicates
    count = next(c for c in claims if c["predicate_id"] == "programme_count")
    assert count["value"] == 60
    assert count["measure"] == "published_flight_rows"
    tech = next(c for c in claims if c["predicate_id"] == "technology")
    assert tech["value"] == "uas-general"


def test_no_private_operator_row_ever_becomes_a_claim() -> None:
    # The S1 boundary end-to-end: nothing on a private/registrant row —
    # no device subject, no camera_* predicate, no person, no location —
    # lands on the claim surface for ANY S1 seat.
    for source_id in _LAYER_SOURCES:
        report = _run_fixture(source_id)
        for claim in _claims(report):
            assert claim["predicate_id"] not in {
                "camera_latitude",
                "camera_longitude",
            } or str(claim["subject_id"]).startswith("traffic_camera:"), (
                source_id,
                claim["subject_id"],
                claim["predicate_id"],
            )
            assert "plate" not in str(claim.get("raw_value") or "").lower()
            assert "registrant" not in str(claim.get("subject_id") or "").lower()


def test_the_dossier_registry_seats_emit_portal_facts() -> None:
    registry_seats = _DOSSIER_SOURCES - {
        "statrep_vt_vermont_law_enforcement",
        "agenda_us_agency_fusus_real",
    }
    for source_id in registry_seats:
        report = _run_fixture(source_id)
        claims = _claims(report)
        portal = [c for c in claims if c["predicate_id"] == "camera_registration_portal"]
        assert portal, f"{source_id} emitted no portal claim"
        assert portal[0]["value"] is True
        assert str(portal[0]["subject_id"]).startswith("sig:deployment:")
        predicates = {c["predicate_id"] for c in claims}
        allowed = set(adapter_config(source_id)["predicate_allowlist"])
        assert predicates <= allowed, (source_id, predicates - allowed)


def test_the_vermont_report_emits_statutory_facts() -> None:
    report = _run_fixture("statrep_vt_vermont_law_enforcement")
    claims = _claims(report)
    predicates = {c["predicate_id"] for c in claims}
    assert "citation" in predicates
    assert "period" in predicates
    assert "technology" in predicates
    tech = next(c for c in claims if c["predicate_id"] == "technology")
    assert tech["value"] == "unmanned aircraft systems"


# --- the screened count page's failure contract ---------------------------------


def _parse_drf(body: bytes, source_id: str = "camreg_la_new_orleans_eye_on") -> Any:
    connector = DjangoRestApiConnector()
    source = dataclasses.replace(
        get(source_id),
        ingestion_permitted=True,
        compact_status=CompactStatus.PUBLIC_TERMS_ONLY,
    )
    targets = live_targets(source_id)
    responses = {
        str(t["url"]): FetchResult(
            url=str(t["url"]), status=200, body=body, media_type="application/json"
        )
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


def test_the_drf_seat_emits_the_published_count() -> None:
    report = _parse_drf((_FIX / "eye_on_nola.json").read_bytes())
    claims = _claims(report)
    count = next(c for c in claims if c["predicate_id"] == "programme_count")
    assert count["value"] == 842
    assert count["measure"] == "published_camera_rows"
    subjects = {str(c["subject_id"]) for c in claims}
    assert all(s.startswith("programme_area:") for s in subjects)
    tech = next(c for c in claims if c["predicate_id"] == "technology")
    assert tech["value"] == "camera-fixed-cctv"


@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        b"[1,2]",
        b'{"detail": "Not found."}',
        b'{"count": "many", "results": []}',
        b'{"count": 5}',
        b'{"count": 5, "results": [{"id": 1}, {"id": 2}]}',
        b'{"count": 5, "results": [{"id": 1, "owner_name": "x"}]}',
    ],
    ids=[
        "non_json",
        "non_object",
        "error_envelope",
        "non_integer_count",
        "missing_results",
        "two_rows",
        "denied_field_name",
    ],
)
def test_the_drf_lane_fails_closed_on_drift(body: bytes) -> None:
    # A malformed/denied/drifted payload fails the run closed — the lane
    # never emits a guessed count over a drifted envelope.
    with pytest.raises(ContentDrift):
        _parse_drf(body)


def test_the_s1_count_parse_fails_on_a_feature_envelope() -> None:
    # A returnCountOnly page that carries `features` means the service
    # served rows where the lane asked for a count — recorded drift.
    targets = live_targets("camreg_detroit_mi_project_green_light")
    connector = Dot511Connector()
    source = dataclasses.replace(
        get("camreg_detroit_mi_project_green_light"),
        ingestion_permitted=True,
        compact_status=CompactStatus.PUBLIC_TERMS_ONLY,
    )
    body = b'{"count": 5, "features": []}'
    responses = {
        str(t["url"]): FetchResult(
            url=str(t["url"]), status=200, body=body, media_type="application/json"
        )
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
    with pytest.raises(ContentDrift):
        run(connector, ctx)


def test_the_enumerated_register_keeps_the_family_dispositions() -> None:
    camreg = tomllib.loads(
        Path("connectors/src/connectors/data/camera_registry_targets.toml").read_text()
    )
    enumerated = {r["id"]: r for r in camreg["enumerated"]}
    for family_id in (
        "agency_published_flock_lpr_location_layers_on_arcgis_online_family",
        "agency_police_drone_flight_log_usage_feature_services_on_arcgis_online",
    ):
        row = enumerated[family_id]
        assert row["status"] == "family_umbrella_deferred", family_id
        assert "source_id" not in row or not row.get("source_id")
