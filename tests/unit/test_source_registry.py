# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The seeded source registry (§22, SIG-INGEST-023/024/026/027/038)."""

from __future__ import annotations

import pytest
from connectors.registry import (
    RELIABILITY_TIERS,
    CompactStatus,
    CustodyPosture,
    RobotsPolicy,
    SourceKind,
    get,
    registry,
    sources,
)
from policy.rights import is_undetermined


def _by_url() -> dict[str, object]:
    return {s.homepage_url: s for s in sources()}


# --- SIG-INGEST-023: every row carries the minimum fields ---------------------


def test_every_source_carries_the_minimum_fields() -> None:
    for s in sources():
        assert s.id and s.name  # identity
        assert isinstance(s.source_kind, SourceKind)
        assert isinstance(s.custody_posture, CustodyPosture)  # custody_posture
        assert isinstance(s.compact_status, CompactStatus)  # compact_status
        assert isinstance(s.robots_policy, RobotsPolicy)
        assert s.default_tier in RELIABILITY_TIERS  # default_tier + reliability R
        assert isinstance(s.ingestion_permitted, bool)  # ingestion_permitted
        assert s.rights.source_id == s.id  # rights record present
        assert s.rights.spdx  # SPDX expression (or UNDETERMINED)


def test_registry_is_non_trivially_seeded() -> None:
    # SIG-INGEST-038: this is a seeded registry, not a stub. Every §22.6 subsection
    # plus the §22.3 additions land here.
    assert len(sources()) >= 90


def test_source_ids_are_unique() -> None:
    ids = [s.id for s in sources()]
    assert len(ids) == len(set(ids))


# --- SIG-INGEST-028: ingestion_permitted defaults to false --------------------


#: The OKC critical subset flipped by the RIGHTS.1 re-run (GL-GATE-03, 2026-09-10),
#: plus the resolved-licence live-ops flips (GL-GATE-03, 2026-09-15): eff_atlas
#: (CC-BY-4.0) and osm_element_history (ODbL-1.0), and the four B-pass
#: operator-approved flips: usaspending (CC0-1.0), fbi_cde_agency_registry (CC0-1.0),
#: eff_data_driven (CC-BY-4.0), muckrock (LicenseRef-MuckRock-API-ToS, REFERENCE —
#: non-redistributable until per-document posture resolves). raa_prefectures
#: (ODbL-1.0) and decp_fr (LicenceOuverte-2.0, ADR-084) flipped once the France
#: cohort gate went per-source (operator decision 2026-09-15); ccops_seattle/
#: nyc_post/sf and pathways_rtcc/css/acoustic flipped on the municipal-mandated-
#: disclosure basis (ADR-085); and the five held sources flipped 2026-09-15 on
#: counsel's approval (HG-02): madada, declarationcamera_be, aspi, carnegie_ai_gsi,
#: facial_recognition_world_map — all LicenseRef-DerivedFacts-Citations, DERIVE
#: custody; counsel resolved HG-02 on 2026-09-16 (ADR-086) — the derived facts
#: publish in the dedicated `derived_facts` compartment, so those records are
#: redistributable (upstream bytes are never re-hosted regardless — no connector
#: emits them into the spine). GL-GATE-06 (2026-09-16, blanket rights disposition)
#: then flipped the 13 remaining flip-ready OSM-ecosystem + civic sources
#: (osm_copyright, osm_taginfo, osmf_licence_guidelines, osm_surveillance_tagging,
#: osm_replication, osm_automated_edits_coc, sous_surveillance_osm_import,
#: wikidata_sparql, eyes_on_flock, flock_finder, deflock_app_repo, gleif,
#: agency_audit_export). P26.2 (2026-09-17) then flipped the five promoted
#: sources whose rights resolve clear under GL-GATE-06 (legistar, primegov,
#: civicclerk, sam_gov, openstates). The two promoted-but-unresolved sources
#: (documentcloud, courtlistener_recap) are connector-mapped yet stay
#: un-permitted, and the unmapped remainder stays un-permitted.
_FLIPPED_SUBSET = frozenset(
    {
        "okc_procurement",
        "okc_council",
        "okcpd_policy",
        "ok_statute",
        "osm_overpass",
        "deflock_repo",
        "eff_atlas_of_surveillance",
        "osm_element_history",
        "usaspending",
        "fbi_cde_agency_registry",
        "eff_data_driven",
        "muckrock",
        "raa_prefectures",
        "decp_fr",
        "ccops_seattle",
        "ccops_nyc_post",
        "ccops_sf",
        "pathways_rtcc_federation",
        "pathways_fr_css_forensics",
        "pathways_acoustic_drone_location",
        "madada",
        "declarationcamera_be",
        "aspi_mapping_chinas_tech_giants",
        "carnegie_ai_gsi",
        "facial_recognition_world_map",
        # GL-GATE-06 (2026-09-16): the 13 flip-ready OSM-ecosystem + civic sources.
        "osm_copyright",
        "osm_taginfo",
        "osmf_licence_guidelines",
        "osm_surveillance_tagging",
        "osm_replication",
        "osm_automated_edits_coc",
        "sous_surveillance_osm_import",
        "wikidata_sparql",
        "eyes_on_flock",
        "flock_finder",
        "deflock_app_repo",
        "gleif",
        "agency_audit_export",
        # P26.2 (2026-09-17): the promoted sources whose rights resolve to a
        # resolved-clear licence under GL-GATE-06 — the three agenda platforms
        # (LicenseRef-PublicAgenda-MeetingRecord), sam_gov (CC0-1.0) and
        # openstates (CC-BY-4.0). documentcloud + courtlistener_recap stay
        # gated (per-document licence ambiguity / the FLP membership agreement
        # is an operator acceptance, not a blanket-clear licence).
        "legistar",
        "primegov",
        "civicclerk",
        "sam_gov",
        "openstates",
        # P26.5 (2026-09-17): eScribe — the fourth enumerated agenda platform —
        # flipped on the same GL-GATE-06 municipal-public-record basis
        # (CC0-1.0; packet docs/build/reports/rights/escribe.md).
        "escribe",
        # P26.7 (2026-09-17): the eight resolved-clear state DOT/511 camera
        # registries — KY/UT/OR/DC on the public-record/CC0 dedication basis,
        # IA explicit CC-BY-4.0, IL explicit CC-BY-SA-2.0 (own compartment),
        # WA/MO conditional public grants evaluated under public terms.
        # Packets: docs/build/reports/rights/dot_511_<st>.md. LA/GA/AL/TX/MD
        # stay gated (empty licenseInfo / non-authority publisher / no SPDX
        # expression for the conditioned terms).
        "dot_511_ky",
        "dot_511_il",
        "dot_511_ut",
        "dot_511_or",
        "dot_511_ia",
        "dot_511_wa",
        "dot_511_dc",
        "dot_511_mo",
    }
)


def test_ingestion_permitted_defaults_false_across_the_seed() -> None:
    # Phase 0 seeds the registry; connectors are Phase 4+. A source is permitted
    # only after a reviewer resolves its posture and flips the flag — as of the
    # RIGHTS.1 re-run, the 2026-09-15 live-ops flips, the GL-GATE-06 blanket
    # disposition (2026-09-16), the P26.2 promoted-source flips (2026-09-17),
    # and the P26.5 eScribe flip that is exactly this set (44 sources), plus the
    # P26.7 dot_511 flips (52 sources).
    permitted = {s.id for s in sources() if s.ingestion_permitted}
    assert permitted == set(_FLIPPED_SUBSET)


# --- SIG-INGEST-027: compact_status is a closed vocabulary incl. no_response --


def test_compact_status_is_the_closed_vocabulary_including_no_response() -> None:
    assert {c.value for c in CompactStatus} == {
        "not_contacted",
        "contacted_awaiting_response",
        "no_response",
        "permission_granted",
        "permission_granted_conditional",
        "permission_declined",
        "public_terms_only",
        "partnership_active",
    }
    # no_response is a real, recorded state — FlockReporter carries it.
    assert CompactStatus.NO_RESPONSE.value == "no_response"
    assert get("flockreporter").compact_status is CompactStatus.NO_RESPONSE


# --- SIG-INGEST-024 / SIG-LIC-003: redistributable separately reviewed --------


def test_redistributable_is_never_derived_from_the_licence_string() -> None:
    # Every resolved (non-UNDETERMINED) row shows evidence of a rights review:
    # attribution and a terms_url. Unresolved rows fail closed (redistributable
    # false) rather than inferring permission.
    for s in sources():
        if is_undetermined(s.rights):
            assert s.rights.redistributable is False
        else:
            assert s.rights.attribution, f"{s.id}: resolved rights need attribution"
            assert s.rights.terms_url, f"{s.id}: resolved rights need a terms_url"


def test_rights_are_populated_or_explicitly_undetermined() -> None:
    # SIG-LIC-001: no source is left without a rights posture.
    for s in sources():
        assert is_undetermined(s.rights) or s.rights.spdx


# --- SIG-INGEST-038: the §22.6 rows are present -------------------------------


@pytest.mark.parametrize(
    "url",
    [
        # A. physical
        "https://www.openstreetmap.org/copyright",
        "https://taginfo.openstreetmap.org/api/4/",
        "https://deflock.org/",
        "https://github.com/FoggedLens/deflock",
        "https://github.com/FoggedLens/deflock-app",
        "https://sunders.uber.space/",
        "https://panopticity.fr/",
        "https://driversagainstflock.org/",
        # B. vendor / portal
        "https://transparency.flocksafety.com/",
        "https://eyesonflock.com/",
        "https://axoncommunityconnect.com/communities/",
        # C. usage / audit
        "https://haveibeenflocked.com/",
        "https://alprwatch.org/",
        "https://gitlab.com/alprwatch-org",
        # D. adoption
        "https://www.atlasofsurveillance.org/",
        "https://www.eff.org/copyright",
        # E. accountability
        "https://alpratlas.org/",
        "https://library.kansas.watch/",
        "https://www.courtlistener.com/api/rest/v4/",
        # F. records / procurement
        "https://www.muckrock.com/",
        "https://api.usaspending.gov/",
        "https://www.sourcewell-mn.gov/",
        "https://api.sam.gov/",
        "https://webapi.legistar.com/v1/<client>/",
        "https://api.usa.gov/crime/fbi/cde/agency/byStateAbbr/{ST}",
        "https://www.gleif.org/en/lei-data/gleif-golden-copy",
        # G. lead generation
        "https://github.com/simeononsecurity/flock-finder",
        "https://wigle.net/",
        # H. community
        "https://flockreporter.org/",
        "https://eyesoffcr.org/",
        # H2. projects
        "https://github.com/none-below/sm-alpr",
        "https://panopti.ca/",
        # I. international
        "https://technopolice.fr/",
        "https://ted.europa.eu/",
    ],
)
def test_named_seed_row_is_registered(url: str) -> None:
    assert url in _by_url(), f"§22.6 source missing from the seed: {url}"


# --- §22.3 SIG-INGEST-026: named additions incl. the cooperative vehicles -----


@pytest.mark.parametrize(
    "source_id",
    [
        "sourcewell",
        "omnia_partners",
        "naspo_valuepoint",
        "buyboard",
        "tips_usa",
        "hgacbuy",
        "equalis_group",
        "gsa",  # cooperative vehicles
        "legistar",
        "primegov",
        "civicclerk",
        "civicplus",
        "novusagenda",
        "boarddocs",
        "iqm2",
        "escribe",  # agenda platforms
        "nextrequest",
        "govqa",
        "justfoia",
        "foiaxpress",  # records portals
        "dhs_fusion_centers",
        "faa_drone_waivers",
        "footnote4a",
        "eyes_off_cedar_rapids",
        "courtlistener_recap",
    ],
)
def test_section_22_3_addition_is_registered(source_id: str) -> None:
    assert source_id in registry(), f"§22.3 addition missing: {source_id}"


# --- REQ-R1-14 / SIG-TASK-014: DeFlock canonical host resolved ----------------


def test_deflock_canonical_host_is_org_not_me() -> None:
    deflock = get("deflock")
    assert "deflock.org" in deflock.homepage_url
    # No registered source may point its canonical host at the 403 deflock.me.
    for s in sources():
        assert not s.homepage_url.startswith("https://deflock.me"), (
            f"{s.id} points at deflock.me; the canonical host is deflock.org (REQ-R1-14)"
        )


def test_deflock_canonical_repos_are_registered_with_their_licences() -> None:
    assert get("deflock_repo").rights.spdx == "MIT"
    assert get("deflock_app_repo").rights.spdx == "AGPL-3.0"


# --- SIG-INGEST-030: Eyes on Flock outreach outcome recorded ------------------


def test_eyes_on_flock_outreach_outcome_is_recorded() -> None:
    eof = get("eyes_on_flock")
    # A recorded compact state (not the absence of one) and the Stage-0 outcome
    # captured in the row — the Phase 11 blocker (SIG-INGEST-030) is recorded.
    assert eof.compact_status is CompactStatus.PUBLIC_TERMS_ONLY
    assert "SIG-INGEST-030" in eof.notes
    # Access resolved under CC-BY-SA-4.0 (§22.5).
    assert eof.rights.spdx == "CC-BY-SA-4.0"
    assert eof.contact == "contact@eyesonflock.com"


# --- SIG-INGEST-048b: licence hazards handled ---------------------------------


def test_agpl_projects_are_marked_non_derivative_licence_hazards() -> None:
    # AGPL-3.0 code MUST NOT be linked into SIG's Apache-2.0 codebase.
    for sid in ("sm_alpr", "deflock_app_repo"):
        assert get(sid).rights.spdx == "AGPL-3.0"
        assert get(sid).rights.derivative_permitted is False


def test_unlicensed_projects_are_undetermined_not_assumed_permitted() -> None:
    # "no licence" means UNDETERMINED under SIG-LIC-004, not implied permission.
    for sid in ("ringmast4r_flock", "flock_ajith_fyi"):
        assert is_undetermined(get(sid).rights)
