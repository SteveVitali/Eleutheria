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


def test_ingestion_permitted_defaults_false_across_the_seed() -> None:
    # Phase 0 seeds the registry; connectors are Phase 4+. No seeded source is
    # permitted until a reviewer resolves its posture and flips the flag.
    assert all(s.ingestion_permitted is False for s in sources())


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
