# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.9a (R11-ACQ-13a, I8 §5.6): the UAV + FRT half of statutory disclosures II.

Five `statrep_*` registry ids land on the `government_mandated_disclosure`
connector P36.8 generalized (batch `r11-disclosures-02`, `27 7 22 * *`), plus
two consolidated targets — the I4-C005 Minn. Stat. 626.19 UAV reports under
`statrep_mn_bca` (P36.8's source row) and the Arvada I4-C103 page as the first
target of `statrep_co_frt_accountability`. This file pins the ticket's
contract:

* the five I8 §5.6 source ids are registered, routed to the connector, carry
  live targets, sit in cadence batch ``r11-disclosures-02``, and stay
  ``ingestion_permitted=false`` (HG-03 — the OP-26 Wave-B flip under ING-GO-B
  is the operator's, never a code change);
* the ACQ-01 generated ids this row reconciles are gone — the consolidated
  candidates (Arvada I4-C103, MN UAV I4-C005) are targets, not source rows;
* the Detroit weekly index enumerates and emits per-week ``usage_count``
  claims in ``disclosure_use`` ONLY — never per-incident rows or officer
  names (Part VIII / §43.4);
* ``ordinance_literal_required`` keeps the source-level § 13.824 citation off
  the BCA's 626.19 UAV filings (the filing's own authority lands as
  ``legal_authority`` verbatim);
* an unmapped technology literal mints NO technology claim and is recorded on
  the artifact row (SIG-ONTO-021 — WaTech's biometric NOI exercises it);
* a shadow replay over every committed fixture is byte-identical
  (SIG-INGEST-019) and the P36.8 surfaces are unchanged (diff 0 — pinned by
  test_statrep_p36_8.py, test_government_mandated_disclosure.py and
  test_live_extraction.py).

Every test fails if the behaviour is removed.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import pytest
from connectors.live_targets import live_targets
from connectors.registry import SourceKind, get, sources
from connectors.runner import CONNECTOR_FOR_SOURCE, RunMode, run_source

from connectors import government_mandated_disclosure as gmd

_FIX = Path(__file__).parent / "fixtures" / "statrep"

# The five I8 §5.6 ACQ-13a registry ids -> (committed fixture, kind, media).
# `statrep_me_dps_uav`'s reviewed surface IS a single filing (no index); the
# consolidated MN UAV and Arvada surfaces are exercised via their own cases
# below.
_INDEX_SOURCES = {
    "statrep_co_frt_accountability": ("co_frt_index.html", "index_page", "text/html"),
    "statrep_wa_watech_frt": ("wa_watech_index.html", "index_page", "text/html"),
    "statrep_detroit_mi_frt_weekly": ("detroit_frt_index.html", "index_page", "text/html"),
    "statrep_il_icjia_drone": ("il_icjia_index.html", "index_page", "text/html"),
}
_DOC_SOURCES = {
    "statrep_me_dps_uav": ("me_dps_uav_report.txt", "disclosure_document", "text/plain"),
}
_SOURCES = {**_INDEX_SOURCES, **_DOC_SOURCES}

# The committed document fixtures exercised directly (index fixture runs serve
# the index bytes to resolved links; the filing's own claim shape is proven on
# the dedicated document fixture — the P36.8 `ne_crime_report.txt` pattern).
_DOCUMENT_FIXTURES = {
    "statrep_co_frt_accountability": "co_frt_arvada_report.txt",
    "statrep_wa_watech_frt": "wa_watech_fr_accountability.txt",
    "statrep_detroit_mi_frt_weekly": "detroit_frt_weekly.txt",
    "statrep_me_dps_uav": "me_dps_uav_report.txt",
    "statrep_il_icjia_drone": "il_icjia_report.txt",
}

# The ACQ-01 generated ids this row reconciled — the two consolidated
# candidates became targets, the five family rows took their design ids.
_RETIRED_IDS = {
    "statrep_co_arvada_facial_recognition",
    "statrep_co_colorado_agency_facial",
    "statrep_il_illinois_freedom_from",
    "statrep_me_safety_maine_law",
    "statrep_mi_detroit_police_department",
    "statrep_mn_unmanned_aerial_vehicle",
    "statrep_wa_facial_recognition_watech",
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


def test_the_five_statrep_sources_are_registered_routed_and_gated() -> None:
    # I8 §5.6: the five ACQ-13a ids — the reconciled design names, not the
    # generated ACQ-01 placeholders. Every row rides the GOVERNMENT_MANDATED_
    # DISCLOSURE source class + connector map and stays
    # ingestion_permitted=false (the operator's OP-26 Wave-B flip under
    # ING-GO-B is the only route to live).
    for source_id in _SOURCES:
        rec = get(source_id)
        assert rec.source_kind is SourceKind.GOVERNMENT_MANDATED_DISCLOSURE, source_id
        assert CONNECTOR_FOR_SOURCE[source_id] == "government_mandated_disclosure", source_id
        assert rec.ingestion_permitted is False, source_id
        assert rec.custody_posture == "DERIVE", source_id
        assert rec.compact_status == "public_terms_only", source_id
        # RB-03/RB-04: rights stay UNDETERMINED pending the operator's flip —
        # a licence lead is seed evidence, never a resolved record.
        assert rec.rights.spdx == "UNDETERMINED", source_id
        assert rec.rights.redistributable is False, source_id


def test_the_reconciled_generated_ids_are_retired() -> None:
    # Plan R1 consolidation: the Arvada page (I4-C103) and the MN UAV series
    # (I4-C005) are targets under consolidated rows, never source rows of
    # their own; the five generated ids are renamed, not duplicated.
    registered = {s.id for s in sources()}
    assert _RETIRED_IDS.isdisjoint(registered)
    for source_id in _RETIRED_IDS:
        assert source_id not in CONNECTOR_FOR_SOURCE
        assert not live_targets(source_id)


def test_the_five_statrep_sources_have_reviewed_live_targets() -> None:
    for source_id, (_, kind, _) in _SOURCES.items():
        targets = live_targets(source_id)
        assert targets, f"{source_id} has no live target registered"
        assert all(t["kind"] == kind for t in targets), (source_id, targets)
        for target in targets:
            assert target["url"].startswith("https://"), (source_id, target)


def test_the_consolidated_targets_land_on_their_reviewed_urls() -> None:
    # I4-C103 rides `statrep_co_frt_accountability` as its first target; the
    # I4-C005 UAV series is `statrep_mn_bca`'s second index target under the
    # plan's R1 one-row-per-publisher consolidation.
    co_targets = live_targets("statrep_co_frt_accountability")
    assert co_targets[0]["url"] == ("https://www.arvadaco.gov/917/Facial-Recognition-Technology")
    mn_targets = live_targets("statrep_mn_bca")
    assert len(mn_targets) == 2
    uav = mn_targets[1]
    assert uav["id"] == "uav_annual_reports"
    assert uav["url"] == (
        "https://dps.mn.gov/divisions/bca/data-and-reports/uav-uav-annual-reports"
    )
    # The per-target document filter narrows the shared BCA tree to the UAV
    # filings only.
    assert uav.get("doc_url_contains") == "uav"


def test_the_five_sources_ride_the_disclosures_02_cadence_batch() -> None:
    cadence = tomllib.loads(Path("ops/cadence.toml").read_text())
    batch = next(b for b in cadence["batches"] if b["id"] == "r11-disclosures-02")
    assert set(_SOURCES) <= set(batch["members"])
    assert batch["cron"] == "27 7 22 * *"
    # The consolidated candidates hold no batch seat of their own — the MN UAV
    # family rides `statrep_mn_bca`'s existing disclosures-01 seat (a source
    # holds one batch seat).
    assert "statrep_mn_bca" not in set(batch["members"])
    b01 = next(b for b in cadence["batches"] if b["id"] == "r11-disclosures-01")
    assert "statrep_mn_bca" in set(b01["members"])
    for retired in _RETIRED_IDS:
        assert retired not in set(batch["members"])


def test_adapter_specs_resolve_for_all_five_sources() -> None:
    for source_id in _SOURCES:
        adapter = gmd.source_adapter(source_id)
        assert adapter is not None, source_id
        assert adapter.get("document_genre") == "statutory_report", source_id
        assert adapter.get("ordinance_citation"), source_id
        assert adapter.get("ordinance_literals"), source_id
        assert adapter.get("technology_mapped") is True, source_id


def test_the_new_uav_frt_literals_map_to_active_slugs() -> None:
    slugs = gmd.technology_slugs()
    mapping = gmd.technology_map()
    for literal in (
        "facial rec",
        "frs",
        "facial recognition system",
        "facial recognition technology",
    ):
        assert mapping[literal] == "face-recognition-unspecified", literal
    for literal in (
        "drone surveillance",
        "unmanned aerial systems",
        "unmanned aerial vehicles",
        "unmanned aircraft system",
        "unmanned aircraft systems",
        "uavs",
    ):
        assert mapping[literal] == "uas-unspecified", literal
    for slug in ("face-recognition-unspecified", "uas-unspecified"):
        assert slug in slugs


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


def test_co_frt_derives_the_filing_agency_from_the_anchor() -> None:
    # The Arvada page (I4-C103, consolidated first target) names the filing
    # agency in the link's own anchor — never the publisher string; the page's
    # own yearly use-statistics literal rides as a usage_count use claim.
    report = _shadow_index("statrep_co_frt_accountability")
    artifacts = _artifacts(report)
    assert len(artifacts) == 2  # the index + the DocumentCenter filing
    claims = _claims(report)
    use = [c for c in claims if c["predicate_id"] == "usage_count"]
    assert [c["value"] for c in use] == ["97"]
    assert use[0]["agency"] == "Arvada Police Department"
    assert use[0]["technology"] == "face-recognition-unspecified"
    vendors = {c["value"] for c in claims if c["predicate_id"] == "vendor_name"}
    assert {"Lumen", "Colorado Information Sharing Consortium"} <= vendors


def test_co_frt_document_fixture_emits_typed_claims() -> None:
    # The accountability-report filing's own fields: the Technology: literal
    # types it face-recognition (the map literal), the statutory citation and
    # enacting body land verbatim, and the filing's own use statement carries
    # the usage_count claim.
    report = _shadow_doc("statrep_co_frt_accountability")
    predicates = set(_predicates(report))
    assert {"technology", "legal_authority", "vendor_name", "usage_count"} <= predicates
    claims = _claims(report)
    tech = [c for c in claims if c["predicate_id"] == "technology"]
    assert tech and tech[0]["value"] == "face-recognition-unspecified"
    assert tech[0]["raw_value"] == "facial recognition system"
    use = [c for c in claims if c["predicate_id"] == "usage_count"]
    assert [c["value"] for c in use] == ["97"]
    assert all(c["claim_type"] == "disclosure_use" for c in use)


def test_wa_watech_scopes_to_fr_filings_and_records_the_unmapped() -> None:
    # The TSB posting page admits the NOI + accountability-report links via
    # the scope screen; the off-host RCW link and the plain page links are
    # skipped. The biometric NOI's literal maps to nothing — NO technology
    # claim mints and the literal is recorded on the artifact (SIG-ONTO-021).
    report = _shadow_index("statrep_wa_watech_frt")
    artifacts = _artifacts(report)
    assert len(artifacts) == 4  # index + NOI + accountability + biometric NOI
    biometric = [a for a in artifacts if "biometric" in str(a.get("source_uri", ""))]
    assert len(biometric) == 1
    assert biometric[0]["unmapped_technology_literals"] == ["biometric"]
    claims = _claims(report)
    assert not any(
        c["predicate_id"] == "technology" and "biometric" in str(c.get("raw_value", ""))
        for c in claims
    )
    # The filing agency rides each link's anchor, never the publisher string.
    agencies = {c["agency"] for c in claims if c["predicate_id"] == "technology"}
    assert agencies == {"WaTech"}


def test_detroit_weekly_emits_per_week_use_counts_only() -> None:
    # DPD Directive 307.5-5.1 makes the weekly filing BY DIRECTIVE a use
    # report — the per-week + year-to-date counts are disclosure_use/
    # usage_count claims ONLY. No per-incident row, no case id, no officer
    # name is emitted (Part VIII / §43.4).
    report = _shadow_doc("statrep_detroit_mi_frt_weekly")
    claims = _claims(report)
    use = [c for c in claims if c["predicate_id"] == "usage_count"]
    assert {c["value"] for c in use} == {"12", "468"}
    assert all(c["claim_type"] == "disclosure_use" for c in use)
    assert all(c["technology"] == "face-recognition-unspecified" for c in use)
    assert {c["claim_type"] for c in claims} <= {
        "ordinance",
        "disclosure",
        "disclosure_use",
    }


def test_detroit_index_resolves_only_the_weekly_report_links() -> None:
    # The weekly-report PDFs under /files/events/ resolve; the BOPC meeting
    # agenda fails the `facial` path filter and the plain boards link fails
    # the suffix filter.
    report = _shadow_index("statrep_detroit_mi_frt_weekly")
    artifacts = _artifacts(report)
    assert len(artifacts) == 3  # the index + two weekly filings
    assert not any("Agenda" in str(a.get("source_uri")) for a in artifacts)


def test_me_dps_uav_emits_the_filings_own_zero_use_literal() -> None:
    # The 25 M.R.S. § 4501 annual report is BY STATUTE the use report — the
    # filing's own "UAV uses reported statewide: 0" literal lands as the
    # usage_count claim, verbatim.
    report = _shadow_doc("statrep_me_dps_uav")
    claims = _claims(report)
    use = [c for c in claims if c["predicate_id"] == "usage_count"]
    assert [c["value"] for c in use] == ["0"]
    assert use[0]["technology"] == "uas-unspecified"
    assert "25 MRSA 4501" in {c["value"] for c in claims if c["predicate_id"] == "legal_authority"}


def test_il_icjia_ownership_rows_are_inventory_never_use() -> None:
    # The Freedom From Drone Surveillance Act report lists agencies that OWN
    # a drone — inventory_entry assertions (ownership is not deployment):
    # `reported_owned` approval_status + the row's own mapped literal, and NO
    # use claim (the filing asserts no deployment).
    report = _shadow_doc("statrep_il_icjia_drone")
    claims = _claims(report)
    owned = [c for c in claims if c["predicate_id"] == "approval_status"]
    assert {c["agency"] for c in owned} == {
        "Springfield Police Department",
        "Illinois State Police",
        "Champaign County Sheriff's Office",
    }
    assert all(c["value"] == "reported_owned" for c in owned)
    assert all(c["claim_type"] == "inventory_entry" for c in owned)
    assert all(c["technology"] == "uas-unspecified" for c in owned)
    assert not any(c["claim_type"] == "disclosure_use" for c in claims)


def test_il_icjia_index_respects_the_path_and_host_filters() -> None:
    # The firearms publication fails the `/drone` path filter and the legacy
    # icjia.state.il.us mirror fails the same-host rule — the two on-host SFY
    # filings resolve.
    report = _shadow_index("statrep_il_icjia_drone")
    artifacts = _artifacts(report)
    assert len(artifacts) == 3  # the index + the two SFY filings
    uris = [str(a["source_uri"]) for a in artifacts]
    assert not any("firearms" in u for u in uris)
    assert not any("icjia.state.il.us" in u for u in uris)


def test_mn_bca_uav_index_resolves_the_626_19_series() -> None:
    # The second target's page links the annual-report series; the off-host
    # Legislative Reference Library mirror is skipped.
    report = _shadow("statrep_mn_bca", "mn_bca_uav_index.html", "index_page", "text/html")
    artifacts = _artifacts(report)
    assert len(artifacts) == 4  # the index + three UAV filings
    uris = [str(a["source_uri"]) for a in artifacts]
    assert not any("lrl.mn.gov" in u for u in uris)
    # The resolved filings type uas-unspecified from the anchor literal —
    # never the source's LPR default.
    techs = [c for c in _claims(report) if c["predicate_id"] == "technology"]
    assert techs and all(c["value"] == "uas-unspecified" for c in techs)


def test_mn_bca_uav_filing_carries_its_own_authority_and_use() -> None:
    # Minn. Stat. 626.19 lands as the filing's verbatim legal_authority; the
    # source-level § 13.824 citation NEVER stamps a filing that does not name
    # it (ordinance_literal_required) — no ordinance_citation claim. The
    # filing's own Technology: field types it uas-unspecified; the statewide
    # total is a use claim; the per-agency rows are reported_uav_use entries.
    report = _shadow("statrep_mn_bca", "mn_bca_uav_report.txt", "disclosure_document", "text/plain")
    claims = _claims(report)
    assert not any(c["predicate_id"] == "ordinance_citation" for c in claims)
    assert "Minn. Stat. 626.19" in {
        c["value"] for c in claims if c["predicate_id"] == "legal_authority"
    }
    use = [c for c in claims if c["predicate_id"] == "usage_count"]
    assert [c["value"] for c in use] == ["9,080"]
    assert use[0]["technology"] == "uas-unspecified"
    entries = [c for c in claims if c["predicate_id"] == "approval_status"]
    assert {c["agency"] for c in entries} == {
        "Hennepin County Sheriff's Office",
        "Minnesota State Patrol",
        "Duluth Police Department",
    }
    assert all(c["value"] == "reported_uav_use" for c in entries)
    assert all(c["technology"] == "uas-unspecified" for c in entries)
    # The statutory list's own per-agency use statements mint in_use claims.
    in_use = {c["agency"] for c in claims if c["predicate_id"] == "in_use"}
    assert in_use == {c["agency"] for c in entries}


def test_mn_bca_lpr_surface_is_unchanged() -> None:
    # The P36.8 LPR list still types alpr-* and emits its verbatim location
    # literals — the second target's additions (technology_field_pattern,
    # document_entries, use_fields, ordinance_literal_required) are no-ops on
    # the LPR page (its resolved form carries no derivable reporting period
    # and no Technology:/bullet literals).
    report = _shadow("statrep_mn_bca", "mn_bca_index.html", "index_page", "text/html")
    claims = _claims(report)
    assert {str(c.get("technology")) for c in claims if c.get("technology")} <= {
        "alpr-unspecified",
        "alpr-fixed",
    }
    assert "uas-unspecified" not in {str(c.get("technology")) for c in claims}
    assert {c["value"] for c in claims if c["predicate_id"] == "ordinance_citation"}
    locations = [c for c in claims if c["predicate_id"] == "deployment_location"]
    assert len(locations) == 4


# --- fixture provenance ---------------------------------------------------------


def test_every_new_fixture_is_named_in_sources_md_with_its_upstream() -> None:
    text = (_FIX / "SOURCES.md").read_text()
    fixtures = [fx for fx, _, _ in _SOURCES.values()]
    fixtures += list(_DOCUMENT_FIXTURES.values())
    fixtures += ["mn_bca_uav_index.html", "mn_bca_uav_report.txt"]
    for fixture in fixtures:
        assert fixture in text, fixture
    for url in (
        "arvadaco.gov",
        "watech.wa.gov",
        "detroitmi.gov",
        "lldc.mainelegislature.org",
        "icjia.illinois.gov",
        "dps.mn.gov",
    ):
        assert url in text, url
    # No re-hosted capture — the manifest states the synthetic-reconstruction
    # rule itself (P8-2).
    assert "synthetic reconstruction" in text
