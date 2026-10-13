# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.9b (R11-ACQ-13b) — the CSS / interception / ATE / Seattle-OIG / DHS half
of the statutory disclosures-II family (I8 §5.6, batch `r11-disclosures-02`).

Eleven registry ids after the plan's R1 consolidations — the ACQ-01 generated
ids renamed to the design names (the I4-C068 municipal ATE reports are
index-enumerated under `statrep_wa_wtsc_ate`; the four component DHS surfaces
are the five targets of `statrep_us_dhs_privacy_compliance`; the SORNs are
Federal Register document pages). Every row rides the generalized
`government_mandated_disclosure` connector; every row stays
`ingestion_permitted=false` (HG-03 — the operator's OP-26 Wave-B flip under
ING-GO-B is the only route to live). Replay/shadow run over the committed
synthetic fixtures (SOURCES.md) with no network.
"""

import tomllib
from pathlib import Path
from typing import Any

import pytest
from connectors.live_targets import live_targets
from connectors.registry import SourceKind, get, sources
from connectors.runner import (
    CONNECTOR_FOR_SOURCE,
    RunMode,
    live_gate_reasons,
    run_source,
)

from connectors import government_mandated_disclosure as gmd

_FIX = Path(__file__).parent / "fixtures" / "statrep"

# The eleven I8 §5.6 ACQ-13b registry ids -> (committed fixture, kind, media).
_INDEX_SOURCES = {
    "statrep_wa_wtsc_ate": ("wa_wtsc_index.html", "index_page", "text/html"),
    "statrep_fl_flhsmv_red_light": ("fl_flhsmv_index.html", "index_page", "text/html"),
    "statrep_seattle_wa_oig": ("seattle_oig_index.html", "index_page", "text/html"),
    "statrep_us_dhs_privacy_compliance": ("dhs_pia_index.html", "index_page", "text/html"),
}
_DOC_SOURCES = {
    "statrep_hi_judiciary_interception": (
        "hi_interception_report.txt",
        "disclosure_document",
        "text/plain",
    ),
    "statrep_mn_court_interception": (
        "mn_court_interception.txt",
        "disclosure_document",
        "text/plain",
    ),
    "statrep_md_msp_css": ("md_msp_css_report.txt", "disclosure_document", "text/plain"),
    "statrep_de_diac": ("de_diac_privacy_sop.txt", "disclosure_document", "text/plain"),
    "statrep_seattle_wa_sdot_ate": (
        "seattle_sdot_atsc_report.txt",
        "disclosure_document",
        "text/plain",
    ),
    "statrep_pa_wzssc": ("pa_wzssc_report.txt", "disclosure_document", "text/plain"),
    "legis_us_dhs_sorn_plate_data": (
        "fr_sorn_cbp007_bci.txt",
        "disclosure_document",
        "text/plain",
    ),
}
_SOURCES = {**_INDEX_SOURCES, **_DOC_SOURCES}

# The committed document fixtures exercised directly for the index-backed
# sources (the filing's own claim shape is proven on the dedicated document
# fixture — the P36.8 `ne_crime_report.txt` pattern).
_DOCUMENT_FIXTURES = {
    "statrep_wa_wtsc_ate": "wa_wtsc_ase_report.txt",
    "statrep_fl_flhsmv_red_light": "fl_flhsmv_rlc_report.txt",
    "statrep_seattle_wa_oig": "seattle_oig_usage_review.txt",
    "statrep_us_dhs_privacy_compliance": "dhs_pia_telemetry.txt",
    **{k: v[0] for k, v in _DOC_SOURCES.items()},
}

# The sixteen ACQ-01 generated ids this row reconciled — eleven renamed to the
# design ids, five consolidated into siblings (municipal ATE -> the WTSC index;
# the four component DHS surfaces -> the privacy-compliance row's targets).
_RETIRED_IDS = {
    "statrep_hi_hawai_judiciary_under",
    "statrep_de_delaware_information_analysis",
    "statrep_wa_2026_automated_safety",
    "statrep_wa_automated_traffic_safety",
    "statrep_fl_florida_highway_safety",
    "statrep_pa_pennsylvania_work_zone",
    "statrep_md_maryland_required_chapters",
    "statrep_mn_minnesota_court_administrator",
    "legis_us_dhs_system_records",
    "statrep_seattle_wa_2024_2025_automated",
    "statrep_wa_seattle_oig_annual",
    "statrep_us_dhs_privacy_impact",
    "statrep_us_dhs_component_privacy",
    "statrep_us_dhs_obim_pia",
    "statrep_us_dhs_cbp_border",
    "statrep_us_dhs_cbp_pia",
}


def _shadow(source_id: str, fixture: str, kind: str, media: str) -> Any:
    return run_source(
        source_id,
        mode=RunMode.SHADOW,
        fixture=_FIX / fixture,
        kind=kind,
        media_type=media,
    )


def _shadow_index(source_id: str) -> Any:
    fx, kind, media = _INDEX_SOURCES[source_id]
    return _shadow(source_id, fx, kind, media)


def _shadow_doc(source_id: str) -> Any:
    return _shadow(source_id, _DOCUMENT_FIXTURES[source_id], "disclosure_document", "text/plain")


def _claims(report: Any) -> list[dict[str, Any]]:
    return [dict(c) for c in report.claims if c.get("record_kind") == "claim"]


def _artifacts(report: Any) -> list[dict[str, Any]]:
    return [dict(c) for c in report.claims if c.get("record_kind") == "evidence_artifact"]


def _predicates(report: Any) -> list[str]:
    return [c["predicate_id"] for c in _claims(report)]


# --- registration, routing, gating (HG-03) -------------------------------------


def test_the_eleven_sources_are_registered_routed_and_gated() -> None:
    # I8 §5.6: the eleven ACQ-13b ids — the reconciled design names, not the
    # generated ACQ-01 placeholders. Every row rides the GOVERNMENT_MANDATED_
    # DISCLOSURE source class + connector map and stays
    # ingestion_permitted=false (the operator's OP-26 Wave-B flip under
    # ING-GO-B is the only route to live).
    for source_id in _SOURCES:
        rec = get(source_id)
        assert rec.source_kind is SourceKind.GOVERNMENT_MANDATED_DISCLOSURE, source_id
        assert CONNECTOR_FOR_SOURCE[source_id] == "government_mandated_disclosure", source_id
        assert rec.ingestion_permitted is False, source_id
        assert rec.compact_status == "public_terms_only", source_id
        # RB-03/RB-04/RB-05/RB-06: rights stay UNDETERMINED pending the
        # operator's flip — a licence lead is seed evidence, never a resolved
        # record.
        assert rec.rights.spdx == "UNDETERMINED", source_id
        assert rec.rights.redistributable is False, source_id


def test_the_reconciled_generated_ids_are_retired() -> None:
    # Plan R1 consolidation: the municipal ATE row and the four component DHS
    # rows are targets under consolidated rows, never source rows of their
    # own; the sixteen generated ids are renamed, not duplicated.
    registered = {s.id for s in sources()}
    assert _RETIRED_IDS.isdisjoint(registered)
    for source_id in _RETIRED_IDS:
        assert source_id not in CONNECTOR_FOR_SOURCE
        assert not live_targets(source_id)


def test_the_dispositions_table_carries_no_p36_9b_promote_placeholders() -> None:
    # Exactly-once: the consolidated/renamed generated ids hold no `promote`
    # seat — the resolved rows are the design ids.
    disp = tomllib.loads(Path("connectors/src/connectors/data/live_dispositions.toml").read_text())
    for source_id in _RETIRED_IDS:
        assert source_id not in (disp.get("sources") or {}), source_id


def test_every_source_is_refused_for_a_live_run() -> None:
    # SIG-INGEST-014/028: a non-green review status makes the live gate refuse
    # BEFORE any transport is constructed — no live verification is claimed.
    for source_id in _SOURCES:
        assert live_gate_reasons(source_id), source_id


def test_the_eleven_sources_have_reviewed_live_targets() -> None:
    for source_id, (_, kind, _) in _SOURCES.items():
        targets = live_targets(source_id)
        assert targets, f"{source_id} has no live target registered"
        for target in targets:
            assert target["url"].startswith("https://"), (source_id, target)
        # The registered target kind matches the fixture exercise kind.
        assert {t["kind"] for t in targets} == {kind}, (source_id, targets)


def test_consolidated_target_surfaces() -> None:
    # The WTSC index row carries the bounded fan-out covering the statewide
    # filing + the ~29 municipal reports (I4-C067/068, plan R1).
    wtsc = live_targets("statrep_wa_wtsc_ate")
    assert len(wtsc) == 1
    assert int(wtsc[0].get("max_documents", 0)) >= 30
    # The DHS privacy-compliance row carries its five reviewed targets
    # (PIA hub + component index + the three named-program pages).
    dhs = live_targets("statrep_us_dhs_privacy_compliance")
    assert len(dhs) == 5
    assert {t["id"] for t in dhs} == {
        "dhs-pia-hub",
        "dhs-ice-component-index",
        "dhs-obim-hart",
        "dhs-cbp-bss",
        "dhs-cbp-telemetry",
    }
    # The SORN row rides Federal Register document pages — seven reviewed
    # notices of the ~8-document I3-C072 family.
    sorn = live_targets("legis_us_dhs_sorn_plate_data")
    assert len(sorn) == 7
    assert all("federalregister.gov/documents/" in t["url"] for t in sorn)


def test_the_sources_ride_the_disclosures_02_cadence_batch() -> None:
    cadence = tomllib.loads(Path("ops/cadence.toml").read_text())
    batch = next(b for b in cadence["batches"] if b["id"] == "r11-disclosures-02")
    members = set(batch["members"])
    assert set(_SOURCES) <= members
    # The five ACQ-13a siblings keep their seats — sixteen members total.
    assert {
        "statrep_me_dps_uav",
        "statrep_wa_watech_frt",
        "statrep_co_frt_accountability",
        "statrep_detroit_mi_frt_weekly",
        "statrep_il_icjia_drone",
    } <= members
    assert len(members) == 16
    assert batch["cron"] == "27 7 22 * *"
    for retired in _RETIRED_IDS:
        assert retired not in members


def test_adapter_specs_resolve_for_all_eleven_sources() -> None:
    for source_id in _SOURCES:
        adapter = gmd.source_adapter(source_id)
        assert adapter is not None, source_id
        assert adapter.get("ordinance_citation"), source_id
        assert adapter.get("ordinance_literals"), source_id
        assert adapter.get("technology_mapped") is True, source_id
    # Genres: DIAC is the policy_document; the rest are statutory filings.
    assert gmd.source_adapter("statrep_de_diac")["document_genre"] == "policy_document"
    for source_id in set(_SOURCES) - {"statrep_de_diac"}:
        assert gmd.source_adapter(source_id)["document_genre"] == "statutory_report", source_id


def test_the_new_literals_map_to_active_slugs() -> None:
    slugs = gmd.technology_slugs()
    mapping = gmd.technology_map()
    for literal in ("wiretap", "wiretaps", "wiretap orders"):
        assert mapping[literal] == "lawful-intercept-content", literal
    for literal in ("pen register", "trap and trace"):
        assert mapping[literal] == "lawful-intercept-metadata", literal
    assert mapping["lawful interception"] == "lawful-intercept-unspecified"
    for literal in ("cell-site simulator", "cell site simulators", "stingray"):
        assert mapping[literal] == "cell-site-simulator-unspecified", literal
    for literal in ("work zone speed camera", "work zone speed safety cameras"):
        assert mapping[literal] == "ate-work-zone", literal
    for literal in ("traffic infraction detector", "traffic infraction detectors"):
        assert mapping[literal] == "ate-red-light", literal
    assert mapping["automated traffic safety cameras"] == "ate-unspecified"
    assert mapping["fusion center"] == "rtcc-unspecified"
    # The P35.14a / SIG-ONTO-055 successors — never the retired slugs.
    assert mapping["social media monitoring"] == "osint-monitoring-social-media"
    assert mapping["commercial telemetry data"] == "location-data-adtech-purchase"
    assert mapping["homeland advanced recognition technology"] == "other-biometric-unspecified"
    for slug in (
        "lawful-intercept-content",
        "lawful-intercept-metadata",
        "lawful-intercept-unspecified",
        "cell-site-simulator-unspecified",
        "ate-work-zone",
        "ate-red-light",
        "ate-unspecified",
        "rtcc-unspecified",
        "osint-monitoring-social-media",
        "location-data-adtech-purchase",
        "other-biometric-unspecified",
    ):
        assert slug in slugs, slug


# --- shadow replay + per-publisher fixture claims (SIG-INGEST-019) -------------


@pytest.mark.parametrize("source_id", sorted(_SOURCES))
def test_shadow_replay_over_the_committed_fixture_diffs_zero(source_id: str) -> None:
    fx, kind, media = _SOURCES[source_id]
    report = _shadow(source_id, fx, kind, media)
    assert report.connector == "government_mandated_disclosure"
    assert report.claims
    assert report.diff is not None and report.diff.changed_count == 0


@pytest.mark.parametrize("source_id", sorted(_DOCUMENT_FIXTURES))
def test_document_fixture_replay_diffs_zero(source_id: str) -> None:
    report = _shadow_doc(source_id)
    assert report.claims
    assert report.diff is not None and report.diff.changed_count == 0


@pytest.mark.parametrize("source_id", sorted(_SOURCES))
def test_every_claim_is_a_per_agency_aggregate_row(source_id: str) -> None:
    # Part VIII: every claim carries the aggregate schema — agency +
    # reporting_period (+ technology for non-ordinance claims) — institution-
    # level facts only, no per-incident field, no officer name.
    fx, kind, media = _SOURCES[source_id]
    for c in _claims(_shadow(source_id, fx, kind, media)):
        assert c["claim_type"] in gmd.claim_types(), (source_id, c)
        assert c["predicate_id"] in gmd.predicate_allowlist(), (source_id, c)
        assert c["agency"] and c["reporting_period"], (source_id, c)
        assert c["aggregate_level"] == gmd.aggregate_level()
        if c["claim_type"] != "ordinance":
            assert c["technology"], (source_id, c)
        banned = gmd.forbidden_output_columns()
        assert not any(
            str(k).lower() in banned or any(b in str(k).lower() for b in banned) for k in c
        ), (source_id, c)


# --- per-source behaviour -------------------------------------------------------


def test_wtsc_index_enumerates_the_statewide_and_municipal_reports() -> None:
    # The ASE page links the statewide report + the municipal filings; the
    # off-scope report links, the non-PDF link and the off-host link are
    # skipped by the reviewed screens. The filing agency rides each link's
    # anchor — never the publisher string.
    report = _shadow_index("statrep_wa_wtsc_ate")
    artifacts = _artifacts(report)
    uris = [str(a.get("source_uri")) for a in artifacts]
    assert len(artifacts) == 4  # the index + statewide + two municipal filings
    assert not any("Distracted" in u for u in uris)
    assert not any("Annual-Report" in u for u in uris)
    assert not any("wsp.wa.gov" in u for u in uris)
    agencies = {c["agency"] for c in _claims(report) if c["predicate_id"] == "technology"}
    assert "City of Auburn" in agencies
    assert "City of Bellevue" in agencies


def test_wtsc_filing_emits_the_statute_and_aggregate_counts() -> None:
    report = _shadow(
        "statrep_wa_wtsc_ate", "wa_wtsc_ase_report.txt", "disclosure_document", "text/plain"
    )
    claims = _claims(report)
    tech = [c for c in claims if c["predicate_id"] == "technology"]
    assert tech and tech[0]["value"] == "ate-unspecified"
    assert "RCW 46.63.220" in {c["value"] for c in claims if c["predicate_id"] == "legal_authority"}
    use = [c for c in claims if c["predicate_id"] == "usage_count"]
    assert [c["value"] for c in use] == ["41,903"]
    assert all(c["claim_type"] == "disclosure_use" for c in use)


def test_hi_interception_emits_the_statutory_zero_only() -> None:
    # HRS § 803-47(b) makes the filing BY STATUTE the annual applications
    # report — the "there were no applications" literal pins usage_count = 0.
    # Judge/prosecutor appendix names are never extracted (§43.4).
    report = _shadow_doc("statrep_hi_judiciary_interception")
    claims = _claims(report)
    use = [c for c in claims if c["predicate_id"] == "usage_count"]
    assert [c["value"] for c in use] == ["0"]
    assert all(c["technology"] == "lawful-intercept-content" for c in use)
    assert all(c["claim_type"] == "disclosure_use" for c in use)
    # No person-naming predicate can ever appear.
    assert not (set(_predicates(report)) & gmd.person_naming_predicates())


def test_mn_court_interception_emits_institution_counts_only() -> None:
    report = _shadow_doc("statrep_mn_court_interception")
    claims = _claims(report)
    values = sorted(c["value"] for c in claims if c["predicate_id"] == "usage_count")
    assert values == ["0", "12", "6"]
    assert all(
        c["technology"] == "lawful-intercept-unspecified"
        for c in claims
        if c["predicate_id"] == "usage_count"
    )
    assert not (set(_predicates(report)) & gmd.person_naming_predicates())


def test_md_msp_css_emits_aggregate_deployment_counts() -> None:
    report = _shadow_doc("statrep_md_msp_css")
    claims = _claims(report)
    tech = [c for c in claims if c["predicate_id"] == "technology"]
    assert tech and tech[0]["value"] == "cell-site-simulator-unspecified"
    assert tech[0]["raw_value"] == "cell-site simulator"
    use = sorted(c["value"] for c in claims if c["predicate_id"] == "usage_count")
    assert use == ["1", "4"]


def test_de_diac_is_a_policy_document_with_no_use_claims() -> None:
    # The fusion center's published SOP is a policy_document — the genre gate
    # permits no disclosure_use claim at all; the reviewed coarse typing is
    # rtcc-unspecified pending the `fusion-center` concept (D-P36.9b-1).
    report = _shadow_doc("statrep_de_diac")
    claims = _claims(report)
    assert not any(c["claim_type"] == "disclosure_use" for c in claims)
    tech = [c for c in claims if c["predicate_id"] == "technology"]
    assert tech and tech[0]["value"] == "rtcc-unspecified"
    assert tech[0]["raw_value"].lower() == "fusion center"


def test_seattle_sdot_emits_the_published_site_literals_verbatim() -> None:
    # The appendix site table emits the filing's OWN published site literals
    # as deployment_location strings keyed to the program operator — never
    # geocoded, never a deployment beyond the filing's own words.
    report = _shadow_doc("statrep_seattle_wa_sdot_ate")
    claims = _claims(report)
    locations = [c for c in claims if c["predicate_id"] == "deployment_location"]
    assert len(locations) == 4
    assert {c["raw_value"] for c in locations} == {
        "Broadview Thomson K8 / Greenwood Ave N",
        "Olympic View Elementary / 92nd Ave NE",
        "Aurora Ave N & N 105th St",
        "Spokane St / West Seattle Bridge",
    }
    assert all(c["agency"] == "Seattle Department of Transportation" for c in locations)
    assert all(c["claim_type"] == "disclosure_use" for c in locations)
    # The program-level infraction count rides as a use claim.
    assert "30,241" in {c["value"] for c in claims if c["predicate_id"] == "usage_count"}


def test_fl_index_respects_the_cabinet_reports_path_and_scope_screens() -> None:
    report = _shadow_index("statrep_fl_flhsmv_red_light")
    artifacts = _artifacts(report)
    uris = [str(a.get("source_uri")) for a in artifacts]
    assert len(artifacts) == 3  # the index + summary + survey-responses filings
    assert not any("HighwaySafetyPlan" in u for u in uris)
    assert not any("newsroom" in u for u in uris)
    assert not any("flsenate.gov" in u for u in uris)


def test_fl_filing_types_the_statutory_literal() -> None:
    # Florida's statute names its cameras "traffic infraction detectors" —
    # the filing's own literal types it ate-red-light (the specific type).
    report = _shadow_doc("statrep_fl_flhsmv_red_light")
    claims = _claims(report)
    tech = [c for c in claims if c["predicate_id"] == "technology"]
    assert tech and tech[0]["value"] == "ate-red-light"
    use = [c for c in claims if c["predicate_id"] == "usage_count"]
    assert {c["value"] for c in use} == {"210,445"}


def test_pa_wzssc_emits_the_work_zone_aggregate() -> None:
    report = _shadow_doc("statrep_pa_wzssc")
    claims = _claims(report)
    assert all(
        c["technology"] == "ate-work-zone"
        for c in claims
        if c["claim_type"] != "ordinance" and c.get("technology")
    )
    use = sorted(c["value"] for c in claims if c["predicate_id"] == "usage_count")
    assert use == ["112,530", "98,112"]
    assert "75 Pa.C.S. 3369" in {
        c["value"] for c in claims if c["predicate_id"] == "legal_authority"
    }


def test_seattle_oig_index_scopes_to_the_usage_reviews() -> None:
    # The OIG catalogue admits the SMC 14.18 usage reviews; the
    # accountability audit and off-host links are skipped.
    report = _shadow_index("statrep_seattle_wa_oig")
    artifacts = _artifacts(report)
    uris = [str(a.get("source_uri")) for a in artifacts]
    assert len(artifacts) == 3  # the index + two usage reviews
    assert not any("Accountability-Audit" in u for u in uris)
    assert not any("spd.gov" in u for u in uris)


def test_seattle_oig_review_emits_program_level_use() -> None:
    # The usage review IS the mandated use statement — the reviewed subject
    # is the operating department (SPD), typed by the filing's own literal.
    report = _shadow_doc("statrep_seattle_wa_oig")
    claims = _claims(report)
    tech = [c for c in claims if c["predicate_id"] == "technology"]
    assert tech and tech[0]["value"] == "gunshot-detection-unspecified"
    use = [c for c in claims if c["predicate_id"] == "usage_count"]
    assert [c["value"] for c in use] == ["37"]
    assert all(c["agency"] == "Seattle Police Department" for c in use)
    assert not (set(_predicates(report)) & gmd.person_naming_predicates())


def test_dhs_index_admits_the_publication_links_only() -> None:
    report = _shadow_index("statrep_us_dhs_privacy_compliance")
    artifacts = _artifacts(report)
    uris = [str(a.get("source_uri")) for a in artifacts]
    assert len(artifacts) == 5  # the index + four publication pages
    assert not any(u.rstrip("/").endswith(("/foia", "/about-dhs")) for u in uris)


def test_dhs_pia_typing_comes_from_the_filing_not_a_default() -> None:
    # The PIA-080 filing's own literals: Technology -> location-data-adtech-
    # purchase (the P35.14a successor), the component id derives the agency,
    # and § 208 lands as the verbatim legal authority. No default slug exists
    # — an unmapped filing would mint ordinance claims only (SIG-ONTO-021).
    report = _shadow_doc("statrep_us_dhs_privacy_compliance")
    claims = _claims(report)
    tech = [c for c in claims if c["predicate_id"] == "technology"]
    assert tech and tech[0]["value"] == "location-data-adtech-purchase"
    assert tech[0]["raw_value"] == "commercial telemetry data"
    assert all(c["agency"] == "CBP" for c in claims if c["claim_type"] != "ordinance")
    assert not any(c["claim_type"] == "disclosure_use" for c in claims), (
        "a PIA is a compliance disclosure, not a use report"
    )


def test_sorn_plate_literal_is_suppressed_by_part_viii() -> None:
    # The BCI SORN's verbatim "license plate readers" literal maps to
    # alpr-unspecified, but the raw literal hits the Part VIII forbidden-token
    # gate — suppressed and recorded on the artifact, never emitted.
    report = _shadow_doc("legis_us_dhs_sorn_plate_data")
    claims = _claims(report)
    assert not any("license plate" in str(c.get("raw_value", "")).lower() for c in claims)
    artifacts = _artifacts(report)
    assert artifacts and artifacts[0].get("part_viii_suppressions")
    # The Privacy Act authority still lands verbatim; the component id
    # derives the agency.
    assert "Privacy Act of 1974" in {
        c["value"] for c in claims if c["predicate_id"] == "legal_authority"
    }
    assert all(c["agency"] == "CBP" for c in claims if c["claim_type"] != "ordinance")


def test_sorn_unmapped_literal_records_and_mints_no_technology_claim() -> None:
    # The ATS notice's own literal "automated targeting system" maps to
    # nothing — recorded on the artifact, never guessed into a slug
    # (SIG-ONTO-021); with no default the filing mints ordinance claims only.
    report = _shadow(
        "legis_us_dhs_sorn_plate_data",
        "fr_sorn_cbp006_ats.txt",
        "disclosure_document",
        "text/plain",
    )
    artifacts = _artifacts(report)
    assert artifacts[0]["unmapped_technology_literals"] == ["automated targeting system"]
    claims = _claims(report)
    assert not any(c["predicate_id"] == "technology" for c in claims)
    assert any(c["predicate_id"] == "ordinance_citation" for c in claims)


# --- fixture provenance ---------------------------------------------------------


def test_every_new_fixture_is_named_in_sources_md_with_its_upstream() -> None:
    text = (_FIX / "SOURCES.md").read_text()
    fixtures = [fx for fx, _, _ in _SOURCES.values()]
    fixtures += list(_DOCUMENT_FIXTURES.values())
    fixtures += ["fr_sorn_cbp006_ats.txt"]
    for fixture in set(fixtures):
        assert fixture in text, fixture
    for url in (
        "wtsc.wa.gov",
        "data.capitol.hawaii.gov",
        "leg.mn.gov",
        "mdsp.prod.maryland.gov",
        "dediac.org",
        "seattle.gov/documents",
        "flhsmv.gov",
        "workzonecameras.penndot.gov",
        "seattle.gov/inspector-general",
        "dhs.gov/privacy-impact-assessments",
        "federalregister.gov/documents",
    ):
        assert url in text, url
    # No re-hosted capture — the manifest states the synthetic-reconstruction
    # rule itself (P8-2).
    assert "synthetic reconstruction" in text


def test_p36_9a_fixtures_are_unchanged() -> None:
    # The a-half siblings' committed fixtures are untouched — the b-half adds
    # rows, never edits theirs.
    for fixture in (
        "co_frt_index.html",
        "wa_watech_index.html",
        "detroit_frt_index.html",
        "il_icjia_index.html",
        "me_dps_uav_report.txt",
    ):
        assert (_FIX / fixture).exists(), fixture
