# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.10 (R11-ACQ-14) — the CCOPS-reports, agency-policy and district
self-disclosure lanes of batch `r11-documents-01` (I8 §5.7).

Sixteen registry ids — the ACQ-01 generated ids renamed to the design names
(five further CCOPS municipalities on the generalized
`government_mandated_disclosure` index→document / document adapters; seven
agency-policy rows as the reviewed seats of the new `agency_policy` connector —
ONE connector serving a closed `source_ids` set; four district self-disclosure
pages whose vendor/product literals mint `inventory_entry` claims — never
student data, never a deployment). The I9b-C040 family list is the discovery
channel and carries NO registry row. Every row stays
`ingestion_permitted=false` (HG-03 — RB-03 `a`; the two CSS-policy rows RB-07
`a`, facts and citations only; the operator's OP-26 Wave-B flip under ING-GO-B
is the only route to live). Replay/shadow run over the committed synthetic
fixtures (fixtures/p36_10/SOURCES.md) with no network.
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
from connectors import okc_documents

_FIX = Path(__file__).parent / "fixtures" / "p36_10"

# The five CCOPS rows + four district self-disclosure rows ride the
# generalized disclosure connector; the seven agency-policy rows ride the
# new `agency_policy` connector.
_CCOPS_INDEX = {
    "ccops_st_louis_mo": ("st_louis_mo_index.html", "index_page", "text/html"),
    "ccops_dayton_oh": ("dayton_oh_index.html", "index_page", "text/html"),
}
_CCOPS_DOCS = {
    "ccops_columbia_mo": ("columbia_mo_report.txt", "text/plain"),
    "ccops_anchorage_ak": ("anchorage_ao_2023_78.txt", "text/plain"),
    "ccops_austin_tx": ("austin_trust_resolution.txt", "text/plain"),
}
_DISTRICT_PAGES = {
    "policy_st_cloud_mn_isd742": ("st_cloud_securly.html", "text/html"),
    "policy_onslow_nc_schools": ("onslow_gaggle.html", "text/html"),
    "policy_pflugerville_tx_isd": ("pflugerville_gaggle.html", "text/html"),
    "policy_whitesboro_ny_csd": ("whitesboro_lightspeed.html", "text/html"),
}
_GMD_SOURCES = {
    **_CCOPS_INDEX,
    **{k: (f, "disclosure_document", m) for k, (f, m) in _CCOPS_DOCS.items()},
    **{k: (f, "disclosure_document", m) for k, (f, m) in _DISTRICT_PAGES.items()},
}
_POLICY_SOURCES = {
    "policy_houston_tx_hpd": "agency_policy_houston.json",
    "policy_albuquerque_nm_apd": "agency_policy_albuquerque.json",
    "policy_bangor_me_pd": "agency_policy_bangor.json",
    "policy_little_rock_ar_pd": "agency_policy_little_rock.json",
    "policy_orange_county_ca_sheriff": "agency_policy_orange_county.json",
    "policy_pasadena_ca_pd": "agency_policy_pasadena.json",
    "legis_ca_gov_code_53166": "agency_policy_ca_53166.json",
}
_SOURCES = {
    **_GMD_SOURCES,
    **{k: (f, "document_page", "application/json") for k, f in _POLICY_SOURCES.items()},
}

# The dedicated document fixtures for the two index-backed CCOPS rows — the
# filing's own claim shape is proven on the committed report extracts (the
# P36.8 ne_crime_report.txt pattern).
_DOCUMENT_FIXTURES = {
    "ccops_st_louis_mo": "st_louis_mo_report.txt",
    "ccops_dayton_oh": "dayton_oh_report.txt",
}

# The eleven ACQ-01 generated ids this row renamed to the I8 §5.7 design ids —
# retired, never duplicated.
_RETIRED_IDS = {
    "policy_ca_orange_county_policy_610",
    "agenda_pasadena_ca_policy_620_cellular",
    "legis_ca_california_code_53166",
    "policy_bangor_me_general_order_59",
    "policy_houston_tx_general_orders",
    "policy_nm_albuquerque_apd_standard",
    "policy_little_rock_ar_general_order_332",
    "policy_st_cloud_mn_area_school_district",
    "statrep_nc_onslow_county_schools_gaggle",
    "policy_pflugerville_tx_isd_gaggle_page",
    "statrep_ny_whitesboro_central_school",
}

# The six already-registered-not-permitted CCOPS rows BL-054 names on the
# Wave-B flip list — registered under P24.x, routed to no connector yet, and
# NEVER touched by this row.
_EXISTING_CCOPS_ROWS = {
    "ccops_berkeley",
    "ccops_davis",
    "ccops_boston",
    "ccops_baltimore",
    "ccops_nashville",
    "ccops_grand_rapids",
}


def _shadow(source_id: str, fixture: str, kind: str, media: str) -> Any:
    return run_source(
        source_id,
        mode=RunMode.SHADOW,
        fixture=_FIX / fixture,
        kind=kind,
        media_type=media,
    )


def _claims(report: Any) -> list[dict[str, Any]]:
    return [dict(c) for c in report.claims if c.get("record_kind") == "claim"]


def _artifacts(report: Any) -> list[dict[str, Any]]:
    return [dict(c) for c in report.claims if c.get("record_kind") == "evidence_artifact"]


# --- registration, routing, gating (HG-03) -------------------------------------


def test_the_sixteen_sources_are_registered_routed_and_gated() -> None:
    # I8 §5.7: the sixteen ACQ-14 ids — the reconciled design names, not the
    # generated ACQ-01 placeholders. The nine disclosure-lane rows ride
    # GOVERNMENT_MANDATED_DISCLOSURE; the seven policy seats are
    # GOVERNMENT_PORTAL rows on the `agency_policy` connector. Every row
    # stays ingestion_permitted=false (HG-03) — the operator's OP-26 Wave-B
    # flip under ING-GO-B is the only route to live.
    for source_id in _GMD_SOURCES:
        rec = get(source_id)
        assert rec.source_kind is SourceKind.GOVERNMENT_MANDATED_DISCLOSURE, source_id
        assert CONNECTOR_FOR_SOURCE[source_id] == "government_mandated_disclosure", source_id
        assert rec.ingestion_permitted is False, source_id
        assert rec.compact_status == "public_terms_only", source_id
        assert rec.rights.spdx == "UNDETERMINED", source_id
        assert rec.rights.redistributable is False, source_id
    for source_id in _POLICY_SOURCES:
        rec = get(source_id)
        assert rec.source_kind is SourceKind.GOVERNMENT_PORTAL, source_id
        assert CONNECTOR_FOR_SOURCE[source_id] == "agency_policy", source_id
        assert rec.ingestion_permitted is False, source_id
        assert rec.compact_status == "public_terms_only", source_id
        assert rec.rights.spdx == "UNDETERMINED", source_id
        assert rec.rights.redistributable is False, source_id


def test_the_reconciled_generated_ids_are_retired() -> None:
    # The eleven generated placeholder keys are renamed to the design ids —
    # no stale registry row, routing entry or live target survives.
    registered = {s.id for s in sources()}
    assert _RETIRED_IDS.isdisjoint(registered)
    for source_id in _RETIRED_IDS:
        assert source_id not in CONNECTOR_FOR_SOURCE
        assert not live_targets(source_id)


def test_the_dispositions_table_carries_no_p36_10_rows() -> None:
    # P25.6 exactly-once: a connector-mapped source carries NO disposition
    # row (its disposition is "live via <connector>"); the sixteen `promote`
    # placeholder seats — under the generated ids and the design ids alike —
    # resolved when this row wired the connector map.
    disp = tomllib.loads(Path("connectors/src/connectors/data/live_dispositions.toml").read_text())
    seats = disp.get("sources") or {}
    for source_id in _RETIRED_IDS | set(_SOURCES):
        assert source_id not in seats, source_id


def test_the_discovery_channel_carries_no_registry_row() -> None:
    # The I9b-C040 district self-disclosure family list is a discovery
    # channel — its four reviewed members hold the rows; the channel itself
    # is a recorded non-row.
    registered = {s.id for s in sources()}
    assert not any("i9b_c040" in sid or "self_disclosure" in sid for sid in registered)


def test_the_six_existing_ccops_rows_are_untouched() -> None:
    # BL-054: the six already-registered-not-permitted CCOPS rows are named
    # on the Wave-B flip list — never edited, never routed, never flipped.
    for source_id in _EXISTING_CCOPS_ROWS:
        rec = get(source_id)
        assert rec.source_kind is SourceKind.GOVERNMENT_MANDATED_DISCLOSURE, source_id
        assert rec.ingestion_permitted is False, source_id
        assert source_id not in CONNECTOR_FOR_SOURCE, source_id


def test_every_source_is_refused_for_a_live_run() -> None:
    # SIG-INGEST-014/028: a non-green review status makes the live gate refuse
    # BEFORE any transport is constructed — no live verification is claimed.
    for source_id in _SOURCES:
        assert live_gate_reasons(source_id), source_id


def test_the_sixteen_sources_have_reviewed_live_targets() -> None:
    for source_id, (_, kind, _) in _SOURCES.items():
        targets = live_targets(source_id)
        assert targets, f"{source_id} has no live target registered"
        for target in targets:
            assert target["url"].startswith("https://"), (source_id, target)
            assert target["kind"] == kind, (source_id, target)
    # The two CSS-policy seats carry a second document_page target each — the
    # reporting-section clause sits in a different section than the policy
    # clause (Pasadena §620.8, Orange County §610.7).
    assert len(live_targets("policy_pasadena_ca_pd")) == 2
    assert len(live_targets("policy_orange_county_ca_sheriff")) == 2


def test_the_sources_ride_the_documents_01_cadence_batch() -> None:
    cadence = tomllib.loads(Path("ops/cadence.toml").read_text())
    batch = next(b for b in cadence["batches"] if b["id"] == "r11-documents-01")
    members = set(batch["members"])
    assert set(_SOURCES) <= members
    assert len(members) == 28  # sixteen ACQ-14 seats + P36.11's twelve
    assert batch["cron"] == "27 7 23 * *"
    for retired in _RETIRED_IDS:
        assert retired not in members


# --- vocabulary + adapter declarations -----------------------------------------


def test_gmd_adapter_specs_resolve_for_the_nine_disclosure_rows() -> None:
    for source_id in _GMD_SOURCES:
        adapter = gmd.source_adapter(source_id)
        assert adapter is not None, source_id
        assert adapter.get("agency"), source_id
    # The CCOPS filings carry a reviewed citation; Dayton's is unknown (the
    # adapter declares `ordinance_literal_required` and NO citation — a
    # guessed instrument never stamps).
    for source_id in (
        "ccops_columbia_mo",
        "ccops_st_louis_mo",
        "ccops_anchorage_ak",
        "ccops_austin_tx",
    ):
        adapter = gmd.source_adapter(source_id)
        assert adapter.get("ordinance_citation"), source_id
        assert adapter.get("ordinance_literals"), source_id
    dayton = gmd.source_adapter("ccops_dayton_oh")
    assert dayton.get("ordinance_literal_required") is True
    assert not dayton.get("ordinance_citation")
    # The district pages mint inventory claims off the page literals and take
    # their honest as-of-capture period.
    for source_id in _DISTRICT_PAGES:
        adapter = gmd.source_adapter(source_id)
        assert adapter.get("document_genre") == "policy_document", source_id
        assert adapter.get("period_from_capture") is True, source_id
        assert adapter.get("default_technology") == "school-surveillance-unspecified", source_id
        kinds = {f.get("claim_type") for f in adapter.get("field_patterns") or ()}
        assert kinds == {"inventory_entry"}, source_id


def test_the_agency_policy_connector_declares_its_closed_seat_set() -> None:
    cfg = dict(okc_documents.connector_config("agency_policy"))
    assert cfg["genre"] == "policy_document"
    assert cfg["extractor"] == "policy_clauses"
    assert set(cfg["source_ids"]) == set(_POLICY_SOURCES)
    # No deployment predicate on the policy surface — procured != authorized
    # != deployed (the epistemic guard).
    allowlist = okc_documents.predicate_allowlist("agency_policy")
    assert not ({"deployment", "deployed", "usage_count"} & allowlist)


def test_the_new_literals_map_to_active_slugs() -> None:
    slugs = gmd.technology_slugs()
    assert "school-surveillance-unspecified" in slugs
    mapping = gmd.technology_map()
    # Every literal the new adapters' field patterns may capture maps.
    for literal in ("cctv", "drones", "body-worn cameras", "video surveillance"):
        assert mapping[literal] in slugs, literal


def test_vocabulary_self_check_is_clean() -> None:
    # The P36.10 adapter blocks pass the connector's own validation sweep —
    # including the new field_patterns[].claim_type / value declarations.
    assert gmd.technology_map_violations() == []


# --- shadow replay + per-publisher fixture claims (SIG-INGEST-019) -------------


@pytest.mark.parametrize("source_id", sorted(_SOURCES))
def test_shadow_replay_over_the_committed_fixture_diffs_zero(source_id: str) -> None:
    fx, kind, media = _SOURCES[source_id]
    report = _shadow(source_id, fx, kind, media)
    assert report.connector == _expected_connector(source_id)
    assert report.claims
    assert report.diff is not None and report.diff.changed_count == 0


def _expected_connector(source_id: str) -> str:
    return "agency_policy" if source_id in _POLICY_SOURCES else "government_mandated_disclosure"


@pytest.mark.parametrize("source_id", sorted(_DOCUMENT_FIXTURES))
def test_ccops_document_fixture_replay_diffs_zero(source_id: str) -> None:
    report = _shadow(source_id, _DOCUMENT_FIXTURES[source_id], "disclosure_document", "text/plain")
    assert report.claims
    assert report.diff is not None and report.diff.changed_count == 0


@pytest.mark.parametrize("source_id", sorted(_GMD_SOURCES))
def test_every_gmd_claim_is_a_per_agency_aggregate_row(source_id: str) -> None:
    # Part VIII: every claim carries the aggregate schema — agency +
    # reporting_period (+ technology for non-ordinance claims) — institution-
    # level facts only, no per-incident field, no officer name, no student
    # data.
    fx, kind, media = _GMD_SOURCES[source_id]
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
        assert not ({"officer", "operator", "agent_name"} & set(c)), (source_id, c)


# --- per-source behaviour -------------------------------------------------------


def test_columbia_filing_emits_ordinance_and_mapped_technology() -> None:
    # The 2025 annual surveillance technology report names its systems in its
    # own "Surveillance Technology:" fields — the multi-field read captures
    # both; the plate literal is refused by the Part VIII sweep (recorded on
    # the artifact, never emitted).
    report = _shadow(
        "ccops_columbia_mo", "columbia_mo_report.txt", "disclosure_document", "text/plain"
    )
    claims = _claims(report)
    assert "City of Columbia Law Enforcement Surveillance Oversight Ordinance" in {
        c["value"] for c in claims if c["predicate_id"] == "ordinance_citation"
    }
    assert "Columbia City Council" in {
        c["value"] for c in claims if c["predicate_id"] == "enacting_body"
    }
    tech = [c for c in claims if c["predicate_id"] == "technology"]
    assert tech and tech[0]["value"] == "fixed-camera-unspecified"
    assert tech[0]["raw_value"] == "CCTV"
    artifact = _artifacts(report)[0]
    assert artifact["part_viii_suppressions"]


def test_st_louis_index_enumerates_the_annual_reports_only() -> None:
    # The anchor/scope screen admits the two annual-report links; the staff
    # directory and the off-host partner link never resolve.
    report = _shadow("ccops_st_louis_mo", "st_louis_mo_index.html", "index_page", "text/html")
    uris = [str(a.get("source_uri")) for a in _artifacts(report)]
    assert any("annual-report-stu-2025" in u for u in uris)
    assert any("annual-report-stu-2024" in u for u in uris)
    assert not any("staff-directory" in u for u in uris)
    assert not any("otheragency" in u for u in uris)


def test_st_louis_filing_emits_the_ordinance_and_technology() -> None:
    report = _shadow(
        "ccops_st_louis_mo", "st_louis_mo_report.txt", "disclosure_document", "text/plain"
    )
    claims = _claims(report)
    citations = {c["value"] for c in claims if c["predicate_id"] == "ordinance_citation"}
    assert any("71842" in v for v in citations)
    assert "St. Louis Board of Aldermen" in {
        c["value"] for c in claims if c["predicate_id"] == "enacting_body"
    }
    assert "Executive Order 78" in {
        c["value"] for c in claims if c["predicate_id"] == "legal_authority"
    }


def test_dayton_index_resolves_only_archive_document_links() -> None:
    report = _shadow("ccops_dayton_oh", "dayton_oh_index.html", "index_page", "text/html")
    uris = [str(a.get("source_uri")) for a in _artifacts(report)]
    doc_uris = [u for u in uris if "archive.aspx" in u.lower()]
    # The two annual reports + the reviewed use-policy link; the commission
    # minutes carry no scope term and never resolve.
    assert len(doc_uris) == 3
    assert not any("8710" in u for u in doc_uris)


def test_dayton_filing_emits_no_unverified_citation() -> None:
    # No ordinance number is on record (I6-C017) — `ordinance_literal_required`
    # refuses the fallback citation; the filing's mapped technology stands.
    report = _shadow("ccops_dayton_oh", "dayton_oh_report.txt", "disclosure_document", "text/plain")
    claims = _claims(report)
    assert not [c for c in claims if c["predicate_id"] in {"ordinance_citation", "enacting_body"}]
    tech = [c for c in claims if c["predicate_id"] == "technology"]
    assert tech and tech[0]["value"] == "uas-unspecified"
    assert _artifacts(report)[0]["part_viii_suppressions"]


def test_anchorage_ordinance_is_a_governance_document() -> None:
    # AO 2023-78 is the ordinance text itself — ordinance claims only; the
    # filing's coarse typing rides the reviewed default slug, and the title's
    # unmapped literal is recorded on the artifact, never guessed.
    report = _shadow(
        "ccops_anchorage_ak", "anchorage_ao_2023_78.txt", "disclosure_document", "text/plain"
    )
    claims = _claims(report)
    assert {c["claim_type"] for c in claims} <= {"ordinance", "disclosure"}
    assert not any(c["claim_type"] == "disclosure_use" for c in claims)
    assert any(
        "3.102" in str(c["value"]) for c in claims if c["predicate_id"] == "ordinance_citation"
    )
    assert "AO 2023-78" in {c["value"] for c in claims if c["predicate_id"] == "legal_authority"}
    assert _artifacts(report)[0].get("unmapped_technology_literals")


def test_austin_resolution_emits_governance_claims_only() -> None:
    # The TRUST resolution directs an ordinance — it reports no deployment:
    # no technology literal maps (the class name is recorded unmapped), no
    # use claim exists, and the resolution's File ID is the citation literal.
    report = _shadow(
        "ccops_austin_tx", "austin_trust_resolution.txt", "disclosure_document", "text/plain"
    )
    claims = _claims(report)
    assert {c["claim_type"] for c in claims} == {"ordinance"}
    assert any(
        "26-1072" in str(c["value"]) for c in claims if c["predicate_id"] == "ordinance_citation"
    )
    assert "Austin City Council" in {
        c["value"] for c in claims if c["predicate_id"] == "enacting_body"
    }
    assert _artifacts(report)[0].get("unmapped_technology_literals")


@pytest.mark.parametrize(
    "source_id,vendor,product",
    [
        ("policy_st_cloud_mn_isd742", "Securly", "Securly Home"),
        ("policy_onslow_nc_schools", "Gaggle", "Gaggle Safety Management"),
        ("policy_pflugerville_tx_isd", "Gaggle", None),
        ("policy_whitesboro_ny_csd", "Lightspeed Systems", "Lightspeed Alert"),
    ],
)
def test_district_pages_emit_vendor_inventory_only(
    source_id: str, vendor: str, product: str | None
) -> None:
    fx, media = _DISTRICT_PAGES[source_id]
    report = _shadow(source_id, fx, "disclosure_document", media)
    claims = _claims(report)
    # inventory_entry claims only — never student data, never a deployment
    # or use claim (the page discloses vendor use, nothing more).
    assert claims
    assert {c["claim_type"] for c in claims} == {"inventory_entry"}
    assert {c["predicate_id"] for c in claims} <= {"vendor_name", "product_name"}
    vendors = {c["value"] for c in claims if c["predicate_id"] == "vendor_name"}
    assert vendor in vendors
    if product is not None:
        assert product in {c["value"] for c in claims if c["predicate_id"] == "product_name"}
    # The honest covered period is the capture date (period_from_capture).
    assert all(c["reporting_period"] == "2026-08-20" for c in claims)
    assert all(c["technology"] == "school-surveillance-unspecified" for c in claims)
    assert not any("student" in str(c.get("raw_value", "")).lower() for c in claims)


# --- the agency_policy seats ----------------------------------------------------


@pytest.mark.parametrize("source_id", sorted(_POLICY_SOURCES))
def test_agency_policy_seats_stamp_their_own_source_id(source_id: str) -> None:
    report = _shadow(source_id, _POLICY_SOURCES[source_id], "document_page", "application/json")
    claims = _claims(report)
    assert claims
    # The multi-source seat: every claim carries the run's source id under
    # the shared connector name (never a config-level single source_id).
    assert all(c["connector"] == "agency_policy" for c in claims)
    assert all(c["source_id"] == source_id for c in claims)
    assert all(c["source_attribution"] == source_id for c in claims)
    # Clause-surface predicates only — no deployment predicate, no
    # person-naming predicate (the §43.4 officer gate is inherited).
    allowlist = okc_documents.predicate_allowlist("agency_policy")
    assert all(c["predicate_id"] in allowlist for c in claims)
    assert all(c["document_genre"] == "policy_document" for c in claims)


def test_a_seatless_source_id_fails_closed() -> None:
    # A run stamped with a source outside the declared `source_ids` set is a
    # registry/config error — extraction refuses rather than mint a claim
    # under an undeclared seat.
    parsed = {
        "documents": [
            {
                "id": "d1",
                "genre": "policy_document",
                "kind": "policy_clauses",
                "source_url": "https://example.invalid/x",
                "subject_id": "sig:policy:x",
                "text": "§ 1. Clause.\nBody.",
                "clauses": [],
            }
        ]
    }
    with pytest.raises(ValueError, match="source_ids"):
        okc_documents.extract_documents("agency_policy", parsed, source_id="ccops_seattle")


def test_the_clause_facts_emit_with_verbatim_raw_values() -> None:
    report = _shadow(
        "legis_ca_gov_code_53166",
        "agency_policy_ca_53166.json",
        "document_page",
        "application/json",
    )
    claims = _claims(report)
    by_pred = {c["predicate_id"]: c for c in claims}
    assert by_pred["statutory_citation"]["value"] == "California Government Code § 53166"
    assert by_pred["use_restriction"]["predicate_id"] == "use_restriction"
    assert all(c["evidence"]["locator"]["kind"] == "byte_range" for c in claims)


# --- back-compat: the OKC path is byte-identical --------------------------------


def test_okc_fixtures_are_unchanged() -> None:
    # The `source_id` kwarg is additive: the per-name OKC config path stands
    # and the committed OKC fixtures diff 0 (covered exhaustively by
    # test_okc_documents; this run double-checks the shared extract function).
    okc_fix = Path(__file__).parent / "fixtures" / "okc"
    for source_id, fixture in (
        ("ok_statute", "ok_statute.json"),
        ("okc_procurement", "okc_procurement.json"),
        ("okcpd_policy", "okcpd_policy.json"),
    ):
        report = run_source(
            source_id,
            mode=RunMode.SHADOW,
            fixture=okc_fix / fixture,
            kind="document_page",
            media_type="application/json",
        )
        assert report.diff is not None and report.diff.changed_count == 0, source_id
