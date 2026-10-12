# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.8 (R11-ACQ-12, I8 §5.5): the statutory ALPR-regime disclosures.

The `government_mandated_disclosure` connector generalizes beyond the CCOPS
municipal ordinances to ten state/federal statutory publishers. This file pins
the ticket's contract:

* the ten I8 §5.5 source ids are registered, routed to the connector, carry
  live targets, sit in cadence batch ``r11-disclosures-01``, and stay
  ``ingestion_permitted=false`` (HG-03 — the OP-26 Wave-B flip is the
  operator's, never a code change);
* ``[technology_map]`` literals ride to ACTIVE ontology slugs only — an
  unmapped literal mints NO technology claim and is recorded on the artifact,
  never a guessed slug (SIG-ONTO-021);
* the reviewed ``document_genre`` fallback applies ONLY where the capture's
  own text classifies to no genre — a text-derived genre always stands;
* registration rows are ``inventory_entry`` assertions (the publisher did not
  verify them), fixed-location literals are verbatim ``deployment_location``
  use claims (never geocoded), and use claims ride only filings that report
  actual use (``reports_use`` / ``reports_use_pattern``);
* the scope screen keeps broad mandated-report catalogues (MD DLS, VA RGA) to
  surveillance-relevant entries only;
* a shadow replay over every committed fixture is byte-identical
  (SIG-INGEST-019) and the CCOPS fixtures' behaviour is unchanged (diff 0 —
  pinned by test_government_mandated_disclosure.py and test_live_extraction.py).

Every test fails if the behaviour is removed.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import pytest
from connectors.live_targets import live_targets
from connectors.registry import SourceKind, get
from connectors.runner import CONNECTOR_FOR_SOURCE, RunMode, run_source
from parsing.genre import DocumentGenre

from connectors import government_mandated_disclosure as gmd

_FIX = Path(__file__).parent / "fixtures" / "statrep"

# The ten I8 §5.5 ACQ-12 source ids -> (committed fixture, capture kind, media).
_INDEX_SOURCES = {
    "statrep_wa_ago_alpr_registry": ("wa_ago_index.html", "index_page", "text/html"),
    "statrep_mn_bca": ("mn_bca_index.html", "index_page", "text/html"),
    "statrep_ne_crime_commission_alpr": (
        "ne_crime_index.html",
        "index_page",
        "text/html",
    ),
    "statrep_il_isp_alpr": ("il_isp_index.html", "index_page", "text/html"),
    "statrep_md_dls_mandated_reports": ("md_dls_index.html", "index_page", "text/html"),
    "statrep_va_rga": ("va_rga_index.html", "index_page", "text/html"),
}
_DOC_SOURCES = {
    "statrep_va_vsp_alpr": ("va_vsp_spec.txt", "disclosure_document", "text/plain"),
    "statrep_va_vscc_alpr": ("va_vscc_report.txt", "disclosure_document", "text/plain"),
    "statrep_vt_dps_alpr": ("vt_dps_report.txt", "disclosure_document", "text/plain"),
    "statrep_austin_tx_auditor": (
        "austin_auditor_report.txt",
        "disclosure_document",
        "text/plain",
    ),
}
_SOURCES = {**_INDEX_SOURCES, **_DOC_SOURCES}


def _shadow(source_id: str, fixture: str | None = None) -> Any:
    fx, kind, media = _SOURCES[source_id]
    return run_source(
        source_id,
        mode=RunMode.SHADOW,
        fixture=_FIX / (fixture or fx),
        kind=kind,
        media_type=media,
    )


def _claims(report: Any) -> list[dict[str, Any]]:
    return [dict(c) for c in report.claims if c.get("record_kind") == "claim"]


def _artifacts(report: Any) -> list[dict[str, Any]]:
    return [dict(c) for c in report.claims if c.get("record_kind") == "evidence_artifact"]


def _predicates(report: Any) -> list[str]:
    return [c["predicate_id"] for c in _claims(report)]


# --- registration, routing, gating (HG-03) -------------------------------------


def test_the_ten_statrep_sources_are_registered_routed_and_gated() -> None:
    # I8 §5.5: the ten ACQ-12 ids — the reconciled names, not the generated
    # ACQ-01 placeholders. Every row rides the GOVERNMENT_MANDATED_DISCLOSURE
    # source class + connector map and stays ingestion_permitted=false (the
    # operator's OP-26 Wave-B flip under ING-GO-B is the only route to live).
    for source_id in _SOURCES:
        rec = get(source_id)
        assert rec.source_kind is SourceKind.GOVERNMENT_MANDATED_DISCLOSURE, source_id
        assert CONNECTOR_FOR_SOURCE[source_id] == "government_mandated_disclosure", source_id
        assert rec.ingestion_permitted is False, source_id
        # RB-03: rights stay UNDETERMINED pending the family ticket's review —
        # a licence lead is seed evidence, never a resolved record.
        assert rec.rights.spdx == "UNDETERMINED", source_id


def test_the_ten_statrep_sources_have_reviewed_live_targets() -> None:
    for source_id, (_, kind, _) in _SOURCES.items():
        targets = live_targets(source_id)
        assert targets, f"{source_id} has no live target registered"
        assert all(t["kind"] == kind for t in targets), (source_id, targets)
        for target in targets:
            assert target["url"].startswith("https://"), (source_id, target)


def test_the_ten_statrep_sources_ride_the_disclosures_01_cadence_batch() -> None:
    cadence = tomllib.loads(Path("ops/cadence.toml").read_text())
    batch = next(b for b in cadence["batches"] if b["id"] == "r11-disclosures-01")
    # Exactly the ten P36.8 members — P36.9a/b ride r11-disclosures-02.
    assert set(batch["members"]) == set(_SOURCES)
    assert batch["cron"] == "27 7 21 * *"


def test_adapter_specs_resolve_for_all_ten_sources() -> None:
    for source_id in _SOURCES:
        adapter = gmd.source_adapter(source_id)
        assert adapter is not None, source_id
        assert adapter.get("document_genre") == "statutory_report", source_id
        # Every statutory adapter carries its reviewed mandate literals.
        assert adapter.get("ordinance_citation"), source_id
        assert adapter.get("ordinance_literals"), source_id


def test_statrep_source_ids_stay_distinct_from_the_ccops_adapter_keys() -> None:
    # The [sources] map is the registry-id lookup for both families; a statrep
    # row resolving to a CCOPS adapter (or vice versa) is a wiring bug.
    ccops = {
        "ccops_seattle",
        "ccops_nyc_post",
        "ccops_sf",
        "ccops_oakland",
        "ccops_cambridge",
        "ccops_somerville",
    }
    assert ccops.isdisjoint(_SOURCES)
    for source_id in set(_SOURCES) | ccops:
        assert gmd.adapter_key_for(source_id) is not None


# --- the reviewed genre fallback -----------------------------------------------


def test_statutory_report_is_a_document_genre_but_not_a_marker_derived_one() -> None:
    # STATUTORY_REPORT exists so the adapter's reviewed declaration can type a
    # capture whose own text matches no marker set — the classifier never
    # guesses statutory status from overlapping policy/deployment language.
    assert DocumentGenre.STATUTORY_REPORT == "statutory_report"
    from parsing.genre import _MARKERS, classify_genre

    # The genre is deliberately ABSENT from the marker table: no text can
    # classify AS statutory_report — only the reviewed adapter declaration can.
    assert all(genre is not DocumentGenre.STATUTORY_REPORT for genre, _ in _MARKERS)
    assert classify_genre("x.txt", b"").genre is DocumentGenre.UNKNOWN
    assert (
        classify_genre("x.txt", b"a quarterly filing library index page").genre
        is DocumentGenre.UNKNOWN
    )


def test_declared_genre_is_a_fallback_never_an_override() -> None:
    # The WA AGO index's own text carries ordinance/policy markers, so the
    # text-derived genre stands over the adapter's statutory_report fallback;
    # the IL ISP index text matches no marker set, so the declared fallback
    # applies. Genre is derived from the document, never trusted from a label.
    wa_artifact = _artifacts(_shadow("statrep_wa_ago_alpr_registry"))[0]
    il_artifact = _artifacts(_shadow("statrep_il_isp_alpr"))[0]
    assert wa_artifact["document_genre"] == "policy_document"
    assert il_artifact["document_genre"] == "statutory_report"


def test_an_invalid_declared_genre_fails_closed() -> None:
    with pytest.raises(ValueError, match="document_genre"):
        gmd._declared_genre({"document_genre": "not_a_genre"})


# --- the technology literal -> slug map (SIG-ONTO-021) --------------------------


def test_every_technology_map_value_is_an_active_ontology_slug() -> None:
    assert gmd.technology_map_violations() == []
    slugs = gmd.technology_slugs()
    for literal, slug in gmd.technology_map().items():
        assert slug in slugs, (literal, slug)


def test_adapter_declared_slugs_are_active_ontology_members() -> None:
    slugs = gmd.technology_slugs()
    for source_id in _SOURCES:
        adapter = gmd.source_adapter(source_id)
        assert adapter is not None
        default = adapter.get("default_technology")
        if default:
            assert default in slugs, (source_id, default)
        for entry in adapter.get("entries") or ():
            if entry.get("technology"):
                assert entry["technology"] in slugs, (source_id, entry)


def test_unmapped_literals_mint_no_claim_and_are_recorded() -> None:
    # SIG-ONTO-021: a literal with no map key produces NO technology claim —
    # the unmapped literal is returned for recording on the artifact, never a
    # guessed slug. (WA AGO's "trail camera" registration exercises the same
    # rule at the fixture level: no ALPR literal, no typed claim.)
    adapter = gmd.source_adapter("statrep_wa_ago_alpr_registry")
    assert adapter is not None and adapter.get("technology_mapped") is True
    mapped, unmapped = gmd._mapped_technologies(
        [("Thermal drone swarm", "Thermal drone swarm"), ("ALPR", "ALPR")], adapter
    )
    assert mapped == [("alpr-unspecified", "ALPR")]
    assert unmapped == ["Thermal drone swarm"]


def test_ccops_adapters_keep_verbatim_technology_behaviour() -> None:
    # Back-compat (shadow diff 0): adapters without `technology_mapped` keep
    # the historical verbatim pass-through — no mapping, no unmapped list.
    adapter = gmd.source_adapter("ccops_oakland")
    assert adapter is not None and not adapter.get("technology_mapped")
    mapped, unmapped = gmd._mapped_technologies([("ShotSpotter", "ShotSpotter")], adapter)
    assert mapped == [("ShotSpotter", "ShotSpotter")] and unmapped == []


def test_a_declared_slug_outside_the_registry_fails_closed() -> None:
    with pytest.raises(gmd.TechnologySlugNotDeclared):
        gmd._assert_declared_slug("not-a-real-slug", where="test")


# --- shadow replay + per-publisher fixture claims (SIG-INGEST-019) -------------


@pytest.mark.parametrize("source_id", sorted(_SOURCES))
def test_shadow_replay_over_the_committed_fixture_diffs_zero(source_id: str) -> None:
    # The real `sig-connectors run --mode shadow` path: loader → static
    # transport (no socket) → capture → parse → extract → normalize → link →
    # load; replay over the same captures is byte-identical.
    report = _shadow(source_id)
    assert report.connector == "government_mandated_disclosure"
    assert report.claims
    assert report.diff is not None and report.diff.changed_count == 0


@pytest.mark.parametrize("source_id", sorted(_SOURCES))
def test_every_claim_is_a_per_agency_aggregate_row(source_id: str) -> None:
    # Part VIII: every claim carries the aggregate schema — agency +
    # reporting_period (+ technology for non-ordinance claims).
    for c in _claims(_shadow(source_id)):
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


def test_wa_ago_emits_registration_assertions_not_deployments() -> None:
    # I9a-C036: RCW 10.130 registers agencies that "operate or intend to
    # operate" — the AGO states it does NOT verify the entries, so rows are
    # inventory_entry assertions; the filing reports no use (no reports_use).
    report = _shadow("statrep_wa_ago_alpr_registry")
    claims = _claims(report)
    statuses = [c for c in claims if c["predicate_id"] == "approval_status"]
    assert {c["agency"] for c in statuses} == {
        "Bellevue Police Department",
        "Redmond Police Department",
        "Olympia Police Department",
        "Forks Wildlife Office",
    }
    assert all(c["claim_type"] == "inventory_entry" for c in statuses)
    assert all(c["value"] == "registered" for c in statuses)
    # A registration is never a use claim — the filing reports none.
    assert not any(c["claim_type"] == "disclosure_use" for c in claims)
    # The trail-camera registration names no mappable technology literal —
    # typed claims ride only the two rows that name an ALPR literal.
    techs = {c["agency"] for c in claims if c["predicate_id"] == "technology"}
    assert techs == {"Bellevue Police Department", "Redmond Police Department"}


def test_wa_ago_index_resolves_only_the_alpr_pdf_links() -> None:
    # /alpr + .pdf: the newsletter and the off-host RCW link are skipped; the
    # registration form and model policy resolve (bounded fan-out).
    artifacts = _artifacts(_shadow("statrep_wa_ago_alpr_registry"))
    assert len(artifacts) == 3  # the index + two resolved documents


def test_mn_bca_emits_statutory_use_and_verbatim_locations() -> None:
    # Minn. Stat. 13.824 subd. 8(b): the list is BY STATUTE a use list —
    # "agencies that use" (reports_use = true); the published fixed-location
    # strings are deployment_location use claims, verbatim, never geocoded.
    claims = _claims(_shadow("statrep_mn_bca"))
    use = {c["agency"] for c in claims if c["predicate_id"] == "in_use"}
    assert use == {
        "Bloomington Police Department",
        "Minnesota State Patrol",
        "Rochester Police Department",
    }
    assert all(c["claim_type"] == "disclosure_use" for c in claims if c["predicate_id"] == "in_use")
    locations = [c for c in claims if c["predicate_id"] == "deployment_location"]
    assert len(locations) == 4
    assert all(c["technology"] == "alpr-fixed" for c in locations)
    values = {c["value"] for c in locations}
    assert "84th Avenue and Lyndale Avenue S" in values
    assert "I-494 and Nicollet Avenue" in values
    # Location rows key to the agency heading that precedes them on the page.
    assert {c["agency"] for c in locations} <= use


def test_ne_index_derives_the_agency_from_each_link_anchor() -> None:
    # The per-agency 60-3206 filings name their agency in the anchor text —
    # never the publisher name; the non-ALPR link is skipped by the path rule.
    claims = _claims(_shadow("statrep_ne_crime_commission_alpr"))
    agencies = {c["agency"] for c in claims if c["predicate_id"] == "technology"}
    assert agencies == {
        "Bellevue Police Department",
        "Lincoln Police Department",
        "Nebraska State Patrol",
    }
    # The victim-services link (outside /alpr-reports/) is not a document.
    assert len(_artifacts(_shadow("statrep_ne_crime_commission_alpr"))) == 4


def test_ne_report_form_emits_its_own_fields() -> None:
    # The committed per-agency filing shape: agency + technology from the
    # form's own literals; retention + sharing as disclosures; the statutory
    # count literals as use claims (the 60-3206 form is a use report).
    report = run_source(
        "statrep_ne_crime_commission_alpr",
        mode=RunMode.SHADOW,
        fixture=_FIX / "ne_crime_report.txt",
        kind="disclosure_document",
        media_type="text/plain",
    )
    claims = _claims(report)
    # The filing's own "Agency:" literal keys every non-ordinance claim — the
    # ordinance claim keys to the enacting legislature.
    assert all(
        c["agency"] == "Bellevue Police Department"
        for c in claims
        if c["claim_type"] != "ordinance"
    )
    assert "technology" in _predicates(report)
    assert "legal_authority" in _predicates(report)
    counts = [c["value"] for c in claims if c["predicate_id"] == "usage_count"]
    assert counts == ["3", "12"]
    assert {c["predicate_id"] for c in claims} >= {
        "retention_period",
        "sharing_partner",
    }


def test_vt_dps_document_carries_its_agency_rows_inside_the_filing() -> None:
    # document_entries: the DPS report's own bullet list names the operating
    # agencies — the `entries` mechanism runs over the DOCUMENT bytes here
    # (index adapters leave it off so resolved filings never re-fire rows).
    claims = _claims(_shadow("statrep_vt_dps_alpr"))
    operating = {
        c["agency"]
        for c in claims
        if c["claim_type"] == "inventory_entry" and c["predicate_id"] == "approval_status"
    }
    assert operating == {
        "Burlington Police Department",
        "Vermont State Police",
        "Williston Police Department",
    }
    assert all(
        c["value"] == "reported_operating" for c in claims if c["predicate_id"] == "approval_status"
    )
    use_agencies = {c["agency"] for c in claims if c["predicate_id"] == "in_use"}
    assert use_agencies == operating
    counts = [c["value"] for c in claims if c["predicate_id"] == "usage_count"]
    assert counts == ["14,230"]


def test_va_vsp_spec_records_the_mandated_field_states() -> None:
    # The § 2.2-5517(J) reporting spec's required metrics are recorded as
    # mandated-field states (answered / present_but_empty / absent) — the
    # spec mandates the fields; a populated value is never fabricated.
    claims = _claims(_shadow("statrep_va_vsp_alpr"))
    states = [c for c in claims if c["predicate_id"] == "disclosure_field_state"]
    assert len(states) == 3
    assert all(c["value"] == "answered" for c in states)
    # The spec mandates metrics; it does NOT itself report use.
    assert not any(c["claim_type"] == "disclosure_use" for c in claims)


def test_va_vscc_emits_use_only_where_the_report_carries_the_literal() -> None:
    # The VSCC update reports surveyed query counts — the usage_count claim
    # rides the report's own literal via reports_use_pattern.
    claims = _claims(_shadow("statrep_va_vscc_alpr"))
    use = [c for c in claims if c["claim_type"] == "disclosure_use"]
    assert [c["value"] for c in use] == ["1,842"]
    predicates = set(_predicates(_shadow("statrep_va_vscc_alpr")))
    assert {"technology", "legal_authority", "vendor_name", "retention_period"} <= predicates
    retention = [c["value"] for c in claims if c["predicate_id"] == "retention_period"]
    assert retention == ["24 hours"]


def test_austin_audit_emits_the_use_claim_on_the_audit_s_own_words() -> None:
    # The auditor's report IS the use statement (in_use pinned value=true with
    # the verbatim literal retained as raw_value).
    claims = _claims(_shadow("statrep_austin_tx_auditor"))
    use = [c for c in claims if c["predicate_id"] == "in_use"]
    assert len(use) == 1
    assert use[0]["value"] is True
    assert "ALPR" in str(use[0]["raw_value"])
    assert "audit_mechanism" in _predicates(_shadow("statrep_austin_tx_auditor"))


def test_il_isp_resolves_annual_reports_with_anchor_named_technology() -> None:
    # The transparency page's filings name their technology in the link's own
    # anchor ("FY2024 ALPR Annual Report"); the non-ALPR traffic-safety link
    # is skipped (outside /content/dam/).
    report = _shadow("statrep_il_isp_alpr")
    claims = _claims(report)
    techs = [c for c in claims if c["predicate_id"] == "technology"]
    assert len(techs) == 3
    assert all(c["value"] == "alpr-unspecified" for c in techs)
    assert all(c["agency"] == "Illinois State Police" for c in techs)
    assert len(_artifacts(report)) == 4  # index + three resolved filings


@pytest.mark.parametrize("source_id", ["statrep_md_dls_mandated_reports", "statrep_va_rga"])
def test_the_scope_screen_admits_only_surveillance_relevant_deposits(source_id: str) -> None:
    # MD DLS / VA RGA deposit EVERY mandated report — the scope_terms screen
    # admits surveillance-relevant entries only (an index-wide ingest is scope
    # creep); the off-host link is skipped by same-host too.
    report = _shadow(source_id)
    artifacts = _artifacts(report)
    assert len(artifacts) == 2  # the index + the one surveillance deposit
    claims = _claims(report)
    filing_agency = {
        "statrep_md_dls_mandated_reports": "Maryland State Police",
        "statrep_va_rga": "Virginia State Crime Commission",
    }[source_id]
    techs = [c for c in claims if c["predicate_id"] == "technology"]
    assert {c["agency"] for c in techs} == {filing_agency}
    # The non-surveillance deposits (transportation, water quality, ...) mint
    # no claims at all — the scope screen is admission, not labelling.
    assert all("Transportation" not in str(c.get("agency")) for c in claims)


# --- the use-claim guard on statutory filings ------------------------------------


def _statctx(reports_use: bool = False) -> Any:
    return gmd.DocumentContext(
        source_id="statrep_mn_bca",
        source_url="https://example/x",
        retrieved_date="2026-10-12",
        genre=DocumentGenre.STATUTORY_REPORT,
        jurisdiction="us-mn",
        reporting_period="2026",
        agency="Minnesota Bureau of Criminal Apprehension",
        technology="alpr-unspecified",
        reports_actual_use=reports_use,
    )


def test_use_claim_from_a_statutory_report_needs_the_filing_s_own_use() -> None:
    # A statutory filing that does not itself report use cannot evidence it —
    # even as an aggregate claim.
    with pytest.raises(gmd.DeploymentInferenceError):
        gmd.disclosure_claim(
            _statctx(reports_use=False),
            claim_type="disclosure_use",
            predicate="in_use",
            value=True,
            raw_value="in use",
            extraction_method="pdf_text",
            locator={"kind": "byte_range", "start": 0, "end": 6},
        )
    claim = gmd.disclosure_claim(
        _statctx(reports_use=True),
        claim_type="disclosure_use",
        predicate="in_use",
        value=True,
        raw_value="in use",
        extraction_method="pdf_text",
        locator={"kind": "byte_range", "start": 0, "end": 6},
    )
    assert claim["claim_type"] == "disclosure_use"


def test_procurement_and_vendor_genres_never_evidence_use() -> None:
    for genre in (DocumentGenre.PROCUREMENT_RECORD, DocumentGenre.VENDOR_DISCLOSURE):
        with pytest.raises(gmd.DeploymentInferenceError):
            gmd.assert_claim_type_supported("disclosure_use", genre, reports_actual_use=True)


def test_statutory_report_permits_the_statutory_claim_types() -> None:
    permitted = gmd.genre_claim_types()[DocumentGenre.STATUTORY_REPORT]
    assert {
        "ordinance",
        "inventory_entry",
        "disclosure",
        "disclosure_use",
    } <= permitted
    # A statutory report may not assert a compliance_finding — the genre's
    # permitted set is the contract.
    assert "compliance_finding" not in permitted


# --- fixture provenance ----------------------------------------------------------


def test_every_fixture_is_named_in_sources_md_with_its_upstream() -> None:
    text = (_FIX / "SOURCES.md").read_text()
    for fixture, _, _ in _SOURCES.values():
        assert fixture in text, fixture
    assert (_FIX / "ne_crime_report.txt").name in text
    for url in (
        "atg.wa.gov",
        "dps.mn.gov",
        "ncc.nebraska.gov",
        "isp.illinois.gov",
        "dls.maryland.gov",
        "rga.lis.virginia.gov",
        "vsp.es.virginia.gov",
        "vscc.virginia.gov",
        "legislature.vermont.gov",
        "austintexas.gov",
    ):
        assert url in text, url
    # No re-hosted capture — the manifest states the synthetic-reconstruction
    # rule itself (P8-2).
    assert "synthetic reconstruction" in text
