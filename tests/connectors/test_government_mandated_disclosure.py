# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `government_mandated_disclosure` connector — CCOPS disclosures
(§22.6 H3, SIG-INGEST-049*, P24.7 / CCOPS.1 / GL-CCOPS-01).

Pins the deliverables: the connector is registered and discoverable through the
registry; the three paying sources (SIG-INGEST-049c — Seattle, NYC POST, SF)
carry the `government_mandated_disclosure` source class and stay
`ingestion_permitted=false`; the committed fixtures ingest to typed, evidenced,
per-agency AGGREGATE claims through the eight stages + loader gate;
`procured≠deployed` is enforced at the genre and predicate level; the
mandated≠populated field states stay distinct; the non-compliance finding lands
as a first-class claim (SIG-INGEST-049e); and a shadow replay over the fixtures
is byte-identical (SIG-INGEST-019). Every test fails if the behaviour is removed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from connectors.registry import SourceKind, get
from connectors.runner import CONNECTOR_FOR_SOURCE, RunMode, run_source
from connectors.stages import registered_connectors

from connectors import government_mandated_disclosure as gmd

_FIX = Path(__file__).parent / "fixtures" / "ccops"
_SOURCES = ("ccops_seattle", "ccops_nyc_post", "ccops_sf")
_FIXTURES = {
    "ccops_seattle": "seattle_sir.json",
    "ccops_nyc_post": "nyc_post_iup.json",
    "ccops_sf": "sf_biannual_inventory.json",
}
_DOSSIER_FIELDS = {
    "retention_period",
    "audit_mechanism",
    "sharing_partner",
    "acquisition_cost",
    "operating_cost",
    "vendor_subsidy",
    "deployment_location",
    "signage_visibility",
    "effectiveness_claim",
    "complaint_count",
    "usage_count",
    "data_access",
    "disparate_impact",
}


def _extract(source_key: str, fixture: str) -> list[dict[str, Any]]:
    payload = gmd.parse_disclosure((_FIX / fixture).read_bytes())
    return [dict(c) for c in gmd.extract_documents(payload)]


def _shadow(source_id: str) -> Any:
    return run_source(
        source_id,
        mode=RunMode.SHADOW,
        fixture=_FIX / _FIXTURES[source_id],
        kind="disclosure",
        media_type="application/json",
    )


# --- registration, source class, and the honest scope (049 / 049a) -------------


def test_connector_is_registered() -> None:
    assert "government_mandated_disclosure" in registered_connectors()


def test_ccops_sources_carry_the_source_class_and_route_to_the_connector() -> None:
    # SIG-INGEST-049: their own source class, distinct from civil_society_dataset
    # and vendor_portal; class posture = public record / pdf / document pipeline.
    sc = gmd.source_class()
    assert sc["licence"] == "public record"
    assert sc["format"] == "pdf"
    assert sc["extraction"] == "document_pipeline"
    assert set(sc["distinct_from"]) == {"civil_society_dataset", "vendor_portal"}
    for source_id in _SOURCES:
        rec = get(source_id)
        assert rec.source_kind is SourceKind.GOVERNMENT_MANDATED_DISCLOSURE
        assert CONNECTOR_FOR_SOURCE[source_id] == "government_mandated_disclosure"


def test_class_level_row_carries_the_class() -> None:
    # The pre-existing class-level registration row is re-kinded to the class.
    assert (
        get("ccops_ordinance_disclosures").source_kind is SourceKind.GOVERNMENT_MANDATED_DISCLOSURE
    )


def test_scope_block_carries_the_honest_depth_not_breadth_numbers() -> None:
    # SIG-INGEST-049a: ~26 jurisdictions, ~5% population, ~0.14% of agencies,
    # ZERO machine-readable, the canonical list is a JPEG — carried, not implied.
    scope = gmd.scope()
    assert scope["jurisdictions"] == 26
    assert scope["us_population_share"] == 0.05
    assert scope["us_agency_share"] == 0.0014
    assert scope["machine_readable_outputs"] == 0
    assert "JPEG" in scope["canonical_list"]
    # Depth, not breadth: the class can never grow past the ~26 jurisdictions.
    assert scope["registry_row_cap"] == 26


def test_sources_are_flipped_on_the_mandated_disclosure_basis() -> None:
    # ADR-085 (operator decision 2026-09-15): all three CCOPS sources flipped on
    # the municipal-mandated-disclosure + derived-facts basis — the connector
    # emits derived facts + citations and never re-hosts the ordinance PDFs.
    # Counsel flag retained (HG-02).
    for source_id in _SOURCES:
        rec = get(source_id)
        assert rec.ingestion_permitted is True, source_id
        assert rec.rights.spdx == "LicenseRef-DerivedFacts-Citations"
        assert rec.review_packet.startswith("docs/build/reports/rights/")


# --- the loader gate is fail-closed (HG-03) ------------------------------------


@pytest.mark.parametrize("source_id", _SOURCES)
def test_every_ccops_source_has_a_document_target(source_id: str) -> None:
    # Flipped under ADR-085 with the document-capture path landed (P25.5): each
    # source carries a real upstream index/document URL, fetched as an
    # EvidenceArtifact (never re-hosted). A live run is not exercised here —
    # unit tests never touch the network.
    from connectors.live_targets import live_targets

    targets = live_targets(source_id)
    assert targets, f"{source_id} has no live target registered"
    assert all(t["kind"] in {"document", "index_page", "disclosure_document"} for t in targets)


def test_document_capture_yields_artifact_not_claims() -> None:
    # A live upstream disclosure document (non-JSON — a POST Act PDF, a Chapter
    # 19B inventory) is captured as an EvidenceArtifact row carrying provenance +
    # the P07.1 verdict; no field claim is fabricated from an unparsed document,
    # and the aggregate schema gate exempts the provenance rows.
    report = run_source(
        "ccops_seattle",
        mode=RunMode.SHADOW,
        fixture=_FIX / "sample_disclosure.pdf",
        kind="disclosure",
        media_type="application/pdf",
    )
    kinds = [row["record_kind"] for row in report.claims]
    assert "evidence_artifact" in kinds
    assert "quality_report" in kinds
    assert "claim" not in kinds
    artifact = next(r for r in report.claims if r["record_kind"] == "evidence_artifact")
    assert artifact["predicate_id"] == "document"
    assert artifact["published_by"] == "ccops_seattle"
    assert artifact["classification"]["file_format"] == "pdf"


# --- fixture → typed, evidenced, per-agency aggregate claims --------------------


@pytest.mark.parametrize("source_id", _SOURCES)
def test_shadow_run_through_the_eight_stages_and_loader_gate(source_id: str) -> None:
    # The real `sig-connectors run --mode shadow` path: loader gate → fixture →
    # capture → parse → extract → normalize → link → load under network
    # isolation; the shadow replay diff is 0 (SIG-INGEST-019).
    report = _shadow(source_id)
    assert report.connector == "government_mandated_disclosure"
    assert report.claims
    assert report.diff is not None and report.diff.changed_count == 0


@pytest.mark.parametrize(
    "source_key,fixture",
    (
        ("seattle", "seattle_sir.json"),
        ("nyc_post", "nyc_post_iup.json"),
        ("sf", "sf_biannual_inventory.json"),
    ),
)
def test_fixture_ingests_to_typed_evidenced_claims(source_key: str, fixture: str) -> None:
    claims = _extract(source_key, fixture)
    assert claims
    for c in claims:
        assert c["claim_type"] in gmd.claim_types()  # typed (§3.1)
        assert c["predicate_id"] in gmd.predicate_allowlist()
        assert c["source_class"] == "government_mandated_disclosure"
        assert c["raw_value"] is not None  # P2 preserved verbatim
        ev = c["evidence"]
        assert ev["source_url"] and ev["retrieved_date"]
        assert ev["locator"] and ev["extraction_method"]


def test_every_claim_is_a_per_agency_aggregate_row() -> None:
    # Part VIII: every claim carries the aggregate schema — agency +
    # reporting_period (+ technology for non-ordinance claims) and the stamped
    # aggregate level; the subject is keyed per agency.
    for key, fixture in (
        ("seattle", "seattle_sir.json"),
        ("nyc_post", "nyc_post_iup.json"),
        ("sf", "sf_biannual_inventory.json"),
    ):
        for c in _extract(key, fixture):
            assert c["agency"] and c["reporting_period"]
            assert c["aggregate_level"] == gmd.aggregate_level()
            assert c["subject_id"].startswith(f"ccops:{c['jurisdiction']}")
            if c["claim_type"] != "ordinance":
                assert c["technology"]
            banned = gmd.forbidden_output_columns()
            assert not any(
                str(k).lower() in banned or any(b in str(k).lower() for b in banned) for k in c
            )


def test_non_aggregate_output_is_refused() -> None:
    # The schema gate: a row missing the agency is not a per-agency aggregate row.
    with pytest.raises(gmd.NonAggregateRow):
        gmd.assert_aggregate_row({"predicate_id": "technology", "reporting_period": "2026"})


def test_forbidden_output_column_is_refused() -> None:
    with pytest.raises(gmd.NonAggregateRow):
        gmd.assert_aggregate_row(
            {
                "predicate_id": "technology",
                "agency": "SFPD",
                "technology": "x",
                "reporting_period": "2026",
                "officer_name": "redacted",
            }
        )


def test_forbidden_token_in_a_value_is_refused() -> None:
    ctx = gmd.DocumentContext(
        source_id="ccops_seattle",
        source_url="https://example/x",
        retrieved_date="2026-08-20",
        genre=gmd.DocumentGenre.POLICY_DOCUMENT,
        jurisdiction="seattle",
        reporting_period="2017",
        agency="SPD",
        technology="ALPR",
    )
    with pytest.raises(gmd.PartVIIIViolation):
        gmd.disclosure_claim(
            ctx,
            claim_type="disclosure",
            predicate="retention_period",
            value="x",
            raw_value="per-person travel history retained",
            extraction_method="structured_import",
            locator={"kind": "row", "row": 0},
        )


def test_person_naming_predicate_is_refused() -> None:
    ctx = gmd.DocumentContext(
        source_id="ccops_seattle",
        source_url="https://example/x",
        retrieved_date="2026-08-20",
        genre=gmd.DocumentGenre.POLICY_DOCUMENT,
        jurisdiction="seattle",
        reporting_period="2017",
        agency="SPD",
    )
    with pytest.raises(gmd.PersonNamingRefused):
        gmd.disclosure_claim(
            ctx,
            claim_type="ordinance",
            predicate="officer_name",
            value="x",
            raw_value="x",
            extraction_method="structured_import",
            locator={"kind": "row", "row": 0},
        )


def test_predicate_allowlist_is_enforced() -> None:
    with pytest.raises(gmd.PredicateNotAllowed):
        gmd.assert_predicate_allowed("per_person_location")


# --- the dossier field surface (049b) ------------------------------------------


def test_dossier_field_predicates_are_emitted() -> None:
    # SIG-INGEST-049b: the fields SIG cannot get anywhere else — named sharing
    # partners, costs incl. freebies, retention, audit, deployment locations,
    # signage, effectiveness, complaint + usage counts — are the predicate
    # surface; the fixtures exercise the fields the documents actually carry.
    emitted = set()
    for key, fixture in (
        ("seattle", "seattle_sir.json"),
        ("nyc_post", "nyc_post_iup.json"),
        ("sf", "sf_biannual_inventory.json"),
    ):
        emitted.update(c["predicate_id"] for c in _extract(key, fixture))
    assert _DOSSIER_FIELDS <= gmd.predicate_allowlist()
    for expected in (
        "retention_period",
        "audit_mechanism",
        "sharing_partner",
        "vendor_subsidy",
        "signage_visibility",
        "data_access",
        "disparate_impact",
        "in_use",
    ):
        assert expected in emitted, expected


def test_the_clause_locator_layer_runs_for_policy_documents() -> None:
    # The ADR-033-deferred layer-3 clause locator (SIG-PARSE-003) actually runs:
    # the NYC POST IUP facts carry the pdf_text extraction method + a byte-range
    # locator into the capture.
    claims = _extract("nyc_post", "nyc_post_iup.json")
    clause_claims = [c for c in claims if c["evidence"]["extraction_method"] == "pdf_text"]
    assert len(clause_claims) == 4
    assert all(c["evidence"]["locator"]["kind"] == "byte_range" for c in clause_claims)


def test_disclosure_claims_are_legally_compelled_calibration_evidence() -> None:
    # SIG-INGEST-049d: claims carry the mandated-disclosure provenance that makes
    # them the calibration corpus — every claim cites its public disclosure URL
    # and retrieval date, and records which field/clause/row it came from.
    for key, fixture in (
        ("seattle", "seattle_sir.json"),
        ("sf", "sf_biannual_inventory.json"),
    ):
        for c in _extract(key, fixture):
            assert c["evidence"]["source_url"].startswith("https://")
            assert c["evidence"]["retrieved_date"] == "2026-08-20"
            assert c["observed_at"] == "2026-08-20"
            assert c["source_attribution"].startswith("ccops_")


# --- mandated != populated (F3.20) ---------------------------------------------


def test_field_state_distinguishes_answered_empty_and_absent() -> None:
    claims = _extract("seattle", "seattle_sir.json")
    answered = {c["predicate_id"] for c in claims if c.get("field_state") == "answered"}
    assert "retention_period" in answered and "vendor_subsidy" in answered
    states = {
        (c["raw_value"], c["value"])
        for c in claims
        if c["predicate_id"] == "disclosure_field_state"
    }
    assert ("SIR Fiscal 1.1 (one-time acquisition cost)", "present_but_empty") in states
    assert ("SIR Fiscal 1.2 (annual operating cost)", "present_but_empty") in states
    assert ("SIR 10.4 (effectiveness metrics)", "absent") in states
    # The blank fiscal fields never fabricate a value.
    assert not any(c["predicate_id"] in {"acquisition_cost", "operating_cost"} for c in claims)


def test_field_state_of_classifies_the_three_states() -> None:
    assert gmd.field_state_of("90 days") == "answered"
    assert gmd.field_state_of("") == "present_but_empty"
    assert gmd.field_state_of(None) == "present_but_empty"
    assert gmd.field_state_of("x", present=False) == "absent"


# --- procured != deployed -------------------------------------------------------


def test_no_use_claim_from_a_commitment_or_policy_document() -> None:
    # The SIR (pre-acquisition commitment) and the POST IUP (capability rules)
    # emit ZERO disclosure_use claims — authorizing is not deploying.
    for key, fixture in (("seattle", "seattle_sir.json"), ("nyc_post", "nyc_post_iup.json")):
        claims = _extract(key, fixture)
        assert not any(c["claim_type"] == "disclosure_use" for c in claims)


def test_sf_inventory_emits_use_only_for_in_use_statuses() -> None:
    # Row-level procured≠deployed: the five "in use without approved policy"
    # rows yield in_use; the approved / seeking-procurement rows yield none.
    claims = _extract("sf", "sf_biannual_inventory.json")
    use = [c for c in claims if c["predicate_id"] == "in_use"]
    assert len(use) == 5
    assert {c["technology"] for c in use} == {
        "Cellebrite Inseyets",
        "Cogent ABIS",
        "DataWorksPlus",
        "CellHawk",
        "Penlink",
    }
    assert not any(
        c["technology"]
        in {
            "Video Analytics with AI",
            "Transit-Only Lane Enforcement (TOLE) cameras",
        }
        for c in use
    )


def _ctx(genre: Any, *, reports_actual_use: bool = False) -> Any:
    return gmd.DocumentContext(
        source_id="ccops_sf",
        source_url="https://example/x",
        retrieved_date="2026-08-20",
        genre=genre,
        jurisdiction="sf",
        reporting_period="2026",
        agency="SFPD",
        technology="ALPR",
        reports_actual_use=reports_actual_use,
    )


def test_use_claim_from_a_non_use_disclosure_is_refused() -> None:
    # A policy_document with reports_actual_use=False cannot evidence use.
    with pytest.raises(gmd.DeploymentInferenceError):
        gmd.disclosure_claim(
            _ctx(gmd.DocumentGenre.POLICY_DOCUMENT),
            claim_type="disclosure_use",
            predicate="in_use",
            value=True,
            raw_value="in use",
            extraction_method="structured_import",
            locator={"kind": "row", "row": 0},
        )


def test_use_claim_from_a_use_reporting_disclosure_is_admitted() -> None:
    # The mandated disclosure's own in-use statement IS the use evidence.
    claim = gmd.disclosure_claim(
        _ctx(gmd.DocumentGenre.POLICY_DOCUMENT, reports_actual_use=True),
        claim_type="disclosure_use",
        predicate="in_use",
        value=True,
        raw_value="in use without an approved policy",
        extraction_method="structured_import",
        locator={"kind": "row", "row": 0},
    )
    assert claim["claim_type"] == "disclosure_use"


def test_use_claim_from_a_deployment_report_is_admitted() -> None:
    claim = gmd.disclosure_claim(
        _ctx(gmd.DocumentGenre.DEPLOYMENT_REPORT),
        claim_type="disclosure_use",
        predicate="usage_count",
        value=12,
        raw_value="12",
        extraction_method="structured_import",
        locator={"kind": "row", "row": 0},
    )
    assert claim["claim_type"] == "disclosure_use"


def test_procurement_genre_never_reports_use_however_labelled() -> None:
    # A procurement record can never evidence use — the flag cannot rescue it.
    with pytest.raises(gmd.DeploymentInferenceError):
        gmd.disclosure_claim(
            _ctx(gmd.DocumentGenre.PROCUREMENT_RECORD, reports_actual_use=True),
            claim_type="disclosure_use",
            predicate="in_use",
            value=True,
            raw_value="in use",
            extraction_method="structured_import",
            locator={"kind": "row", "row": 0},
        )


def test_deployment_predicate_on_a_non_use_claim_is_refused() -> None:
    # The predicate-level guard: a use predicate may ride only on a
    # disclosure_use claim — even in a use-reporting disclosure.
    with pytest.raises(gmd.DeploymentInferenceError):
        gmd.disclosure_claim(
            _ctx(gmd.DocumentGenre.POLICY_DOCUMENT, reports_actual_use=True),
            claim_type="disclosure",
            predicate="in_use",
            value=True,
            raw_value="in use",
            extraction_method="structured_import",
            locator={"kind": "row", "row": 0},
        )


def test_mislabelled_genre_is_rejected_genre_is_re_derived() -> None:
    # The genre the guard keys on is derived from the document text, never
    # trusted from the fixture label.
    doc = {
        "disclosure_source": "sf",
        "documents": [
            {
                "id": "mislabelled",
                "kind": "inventory_table",
                "genre": "deployment_report",
                "jurisdiction": "sf",
                "agency": "SFPD",
                "reporting_period": "2026",
                "source_url": "https://example/x",
                "text": "Purchase Order 999. sole source contract no. vendor bid rfp",
                "rows": [],
            }
        ],
    }
    with pytest.raises(gmd.ClaimTypeNotPermitted):
        gmd.extract_documents(doc)


def test_deployment_genres_stay_in_lockstep_with_parsing() -> None:
    from parsing.genre import DEPLOYMENT_GENRES

    assert gmd.deployment_genres() == DEPLOYMENT_GENRES


# --- the non-compliance finding (049e) -----------------------------------------


def test_sf_inventory_emits_the_compliance_finding() -> None:
    # SIG-INGEST-049e: "in use without an approved policy" is a first-class
    # finding — the disclosure's own metric lands as compliance_finding claims.
    claims = _extract("sf", "sf_biannual_inventory.json")
    findings = {c["predicate_id"]: c for c in claims if c["claim_type"] == "compliance_finding"}
    assert findings["in_use_without_policy_count"]["value"] == 37
    assert findings["policy_compliance_share"]["value"] == 0.66
    assert "26%" in findings["non_compliance_finding"]["raw_value"]


def test_compliance_finding_from_a_commitment_document_is_refused() -> None:
    with pytest.raises(gmd.DeploymentInferenceError):
        gmd.disclosure_claim(
            _ctx(gmd.DocumentGenre.POLICY_DOCUMENT),
            claim_type="compliance_finding",
            predicate="in_use_without_policy_count",
            value=1,
            raw_value="1",
            extraction_method="structured_import",
            locator={"kind": "row", "row": 0},
        )


# --- 049f / 050: the state-statute seed + the future-due registration -----------


def test_state_alpr_statute_seed_is_labelled_with_its_date() -> None:
    # SIG-INGEST-049f: the one national inventory, seeded as committed data and
    # labelled with its frozen date — a one-time seed, never a feed.
    import tomllib

    seed = tomllib.loads(
        (
            Path(__file__).resolve().parents[2]
            / "connectors/src/connectors/data/state_alpr_statute_seed.toml"
        ).read_text()
    )
    assert seed["as_of"] == "2022-02-03"
    assert seed["frozen"] is True and seed["never_a_feed"] is True
    states = {s["state"] for s in seed["statutes"]}
    assert len(states) == 16 == seed["state_count"]
    assert seed["ncsl_table_rows"] == 17  # the NCSL table's own layout (CA twice)
    enactments = sum(len(s["years_enacted"]) for s in seed["statutes"])
    assert enactments == 21  # the enumerated statute-years across the 16 states


def test_ncsl_inventory_source_is_registered_and_not_a_feed() -> None:
    rec = get("state_alpr_statute_inventory")
    assert rec.ingestion_permitted is False
    assert "2022-02-03" in rec.notes


def test_future_statutory_disclosure_is_registered_with_commencement_date() -> None:
    # SIG-INGEST-050: future-due mandated sources are registered NOW with their
    # commencement date; non-compliance after the due date is detectable.
    rec = get("future_statutory_disclosure_2027")
    assert rec.ingestion_permitted is False
    assert "2027-04-01" in rec.notes


# --- fixture provenance ---------------------------------------------------------


def test_fixtures_have_a_sources_md() -> None:
    text = (_FIX / "SOURCES.md").read_text()
    for fixture in _FIXTURES.values():
        assert fixture in text
    for url in ("seattle.gov", "nyc.gov", "sf.gov"):
        assert url in text
