# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Rights-review status + the flip-metadata rule (P21.1, SIG-INGEST-028/038, SIG-LIC-001/009)."""

from __future__ import annotations

import contextlib
import io
from datetime import date

import pytest
from connectors.cli import main
from connectors.registry import (
    CompactStatus,
    CustodyPosture,
    RobotsPolicy,
    SourceKind,
    SourceRecord,
    sources,
)
from connectors.review import (
    flip_ready,
    gate_breakdown,
    is_flip_ready,
    review_metadata_violations,
)
from policy.rights import UNDETERMINED, RightsRecord


def _record(
    source_id: str,
    *,
    permitted: bool,
    spdx: str = "CC0-1.0",
    reviewed_by: str = "licensing reviewer",
    reviewed_on: date | None = date(2026, 9, 10),
    last_verified: date | None = date(2026, 9, 10),
    custody: CustodyPosture = CustodyPosture.REFERENCE,
    compact: CompactStatus = CompactStatus.PUBLIC_TERMS_ONLY,
    redistributable: bool = True,
) -> SourceRecord:
    rights = RightsRecord(
        source_id=source_id,
        spdx=spdx,
        attribution="test" if spdx != UNDETERMINED else "",
        redistributable=redistributable,
        derivative_permitted=True,
        terms_url="https://example.test/terms" if spdx != UNDETERMINED else "",
        retrieval_date=date(2026, 9, 10),
    )
    return SourceRecord(
        id=source_id,
        name=f"test {source_id}",
        source_kind=SourceKind.GOVERNMENT_PORTAL,
        homepage_url="https://example.test/",
        default_tier="R1",
        custody_posture=custody,
        compact_status=compact,
        robots_policy=RobotsPolicy.HONOR,
        rights=rights,
        ingestion_permitted=permitted,
        rights_reviewed_by=reviewed_by,
        rights_reviewed_on=reviewed_on,
        last_verified=last_verified,
    )


# --- The flip-metadata rule (SIG-INGEST-028/038, SIG-LIC-001) -----------------


def test_flip_without_reviewed_by_is_a_validation_violation_naming_the_id() -> None:
    bad = _record("test_flip_no_reviewer", permitted=True, reviewed_by="")
    violations = review_metadata_violations([bad])
    assert len(violations) == 1
    assert "test_flip_no_reviewer" in violations[0]
    assert "rights_reviewed_by" in violations[0]


def test_flip_without_rights_block_is_a_violation() -> None:
    bad = _record(
        "test_flip_undetermined", permitted=True, spdx=UNDETERMINED, redistributable=False
    )
    (msg,) = review_metadata_violations([bad])
    assert "test_flip_undetermined" in msg
    assert "resolved rights block" in msg


def test_flip_without_reviewed_on_or_last_verified_is_a_violation() -> None:
    bad = _record("test_flip_no_dates", permitted=True, reviewed_on=None, last_verified=None)
    (msg,) = review_metadata_violations([bad])
    assert "rights_reviewed_on" in msg
    assert "last_verified" in msg


def test_a_fully_reviewed_flip_is_not_a_violation() -> None:
    good = _record("test_flip_ok", permitted=True)
    assert review_metadata_violations([good]) == []


def test_unpermitted_rows_are_never_violations_even_without_metadata() -> None:
    # A source that is not flipped needs no review metadata (additive/back-compat).
    row = _record("test_unpermitted", permitted=False, reviewed_by="", reviewed_on=None)
    assert review_metadata_violations([row]) == []


def test_the_seeded_registry_has_no_flip_metadata_violations() -> None:
    # Nothing is flipped in the seed, so the rule holds registry-wide.
    assert review_metadata_violations(sources()) == []


# --- validate wires the rule (AC: validate fails naming the id) ---------------


def test_validate_passes_on_the_seeded_registry(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate"]) == 0
    out = capsys.readouterr().out
    assert "registered sources: 339" in out
    assert "self-checks OK" in out


def test_validate_fails_naming_the_offending_id(monkeypatch: pytest.MonkeyPatch) -> None:
    # A row flipped to ingestion_permitted=true but lacking rights_reviewed_by
    # makes `sig-connectors validate` fail, naming the id (SIG-INGEST-028/038).
    bad = _record("okc_procurement_test_flip", permitted=True, reviewed_by="")
    monkeypatch.setattr(
        "connectors.cli.review_metadata_violations",
        lambda srcs: [
            f"source {bad.id!r} has ingestion_permitted=true but is missing rights_reviewed_by"
        ],
    )
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = main(["validate"])
    assert code == 1
    assert "VALIDATION FAILED" in buf.getvalue()
    assert "okc_procurement_test_flip" in buf.getvalue()


# --- flip-ready + loadable counts (post RIGHTS.1 + P25 flips, GL-GATE-03) ------
# The OKC critical subset was flipped 2026-09-10 (okc_procurement/okc_council/
# okcpd_policy/ok_statute + osm_overpass/deflock_repo) = 6 loadable. Then 2026-09-15:
# two resolved-licence sources (P25.3: eff_atlas_of_surveillance CC-BY-4.0,
# osm_element_history ODbL) and four B-pass operator-approved flips (usaspending
# CC0-1.0, fbi_cde_agency_registry CC0-1.0, eff_data_driven CC-BY-4.0, muckrock
# LicenseRef at REFERENCE) = 12 loadable. The same-day unblock pass (operator
# determination, ADR-085) flipped the rights-resolved France pair (raa_prefectures
# ODbL-1.0, decp_fr LicenceOuverte-2.0 — the cohort gate went per-source) plus
# ccops_seattle/nyc_post/sf and pathways_rtcc/css/acoustic on the derived-facts +
# mandated-disclosure basis = 20 loadable, 13 flip-ready. Counsel (HG-02) then
# approved the five held sources (madada, declarationcamera_be, aspi,
# carnegie_ai_gsi, facial_recognition_world_map — LicenseRef-DerivedFacts-Citations,
# DERIVE custody) = 25 loadable; flip-ready unchanged at 13 (those five had no
# rights blocks before counsel, so they were never in the flip-ready set). The
# GL-GATE-06 blanket rights disposition (2026-09-16) then flipped all 13
# flip-ready sources = 38 loadable, 0 flip-ready. P26.2 (SOURCES.2, same-day)
# then flipped five promoted sources whose rights resolved clear under
# GL-GATE-06 — legistar/primegov/civicclerk (municipal public records →
# CC0-1.0, same basis as okc_council), sam_gov (federal public domain,
# 17 U.S.C. §105), openstates (documented public-domain dedication,
# open.pluralpolicy.com/data/) — while documentcloud (per-document rights
# UNDETERMINED) and courtlistener_recap (membership-agreement access, HG-09
# class) stay gated = 43 loadable, 0 flip-ready. P26.3 (SOURCES.3, 2026-09-17)
# added one gated discovery row (la_city_clerk_cfms — the real LA City
# legislative surface found during the PrimeGov robots-wall pivot) = 143
# registered, 43 loadable, 0 flip-ready.


def test_review_status_prints_flip_ready_0_and_loadable_65(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # GL-GATE-06 (2026-09-16) drained flip-ready to 0; the same-day P26.2 pass
    # flipped the five resolved promoted sources (38 → 43 loadable). P26.3's
    # gated discovery row moved registered 142 → 143; P26.5 added granicus as a
    # gated/link-only census source (143 → 144) and flipped eScribe on the
    # municipal-public-record basis (43 → 44 loadable). P26.7 (SOURCES.7) added
    # 13 state DOT/511 camera-registry rows (144 → 157) and flipped the 8
    # resolved-clear states (KY/IL/UT/OR/IA/WA/DC/MO; LA/GA/AL/TX/MD stay gated)
    # under the GL-GATE-06 delegated basis (44 → 52 loadable). P26.9 (SOURCES.8)
    # added 23 municipal/transit/non-US camera-registry rows (157 → 180) and
    # flipped the 9 resolved-clear publishers (Austin/NOLA/Baton Rouge/Winnipeg/
    # ACT/Sioux Falls/Baltimore/Ottawa/Sheffield; Chicago/Calgary/Edmonton/
    # Honolulu/MD-mirror/York/Arlington/Seattle/Bellevue/Lexington/NZTA/QLDC/
    # Donegal/HK stay gated) under the same delegated basis (52 → 61 loadable).
    # P26.10 (SOURCES.9) added 6 procurement-portal rows (180 → 186: bonfire +
    # five per-city Socrata contract datasets) and flipped the four
    # licence-reviewed cities (Austin PUBLIC_DOMAIN, SF PDDL, KCMO CC0-1.0,
    # NYC PUBLIC_DOMAIN — verbatim basis in each rights packet) under the same
    # GL-GATE-06 delegated pattern (61 → 65 loadable); bidnet_direct (vendor
    # terms not yet captured verbatim), bonfire (robots Disallow:/), opengov
    # (WAF challenge) and procportal_chicago_il (no licence metadata) stay gated.
    # P26.12 (SOURCES.11) added congress_gov (186 → 187) — the federal
    # legislation sweep, flipped under the same GL-GATE-06 delegated pattern
    # (US federal public domain, 17 U.S.C. §105 → CC0-1.0; 65 → 66 loadable).
    # P26.13 (SOURCES.12) added the 11 catalog-sweep camreg rows (187 → 198)
    # and flipped the 10 resolved-clear registries (DC/Nottingham/York/
    # Glasgow/North Ayrshire/Lambeth/Peel/Rochester/Gold Coast/Puerto Gaitán;
    # St. Albert stays gated — D-SOURCES.12-1) under the same delegated
    # pattern (66 → 76 loadable). P26.15 (SOURCES.14) expanded the pre-registered
    # ted_eu census stub (registered stays 198) — the EU OJ S procurement
    # surface — flipped under the same GL-GATE-06 delegated pattern
    # (Commission Decision 2011/833/EU free-reuse grant + CC-BY-4.0 editorial +
    # CC0-1.0 metadata → CC-BY-4.0; 76 → 77 loadable).
    # P26.16 (SOURCES.15) — the GL-GATE-07 rights batch: +136 new registry
    # rows (198 → 334 registered) and +151 flips (15 pre-registered gated
    # sources + 136 new rows all permitted; 77 → 228 loadable).
    # P27.2 (LAUNCH.2) — `state_alpr_statute_inventory` rights-reviewed under
    # GL-GATE-07/HG-03 (LicenseRef-DerivedFacts-Citations; the landed seed
    # claims resolve via rights_decision, ADR-095). The registry flag stays
    # false by design: the source is a one-time frozen seed that never
    # re-fetches (SIG-INGEST-049f) and its terms page Cloudflare-challenges
    # non-browser fetches — so it sits flip-ready-but-deliberately-unflipped,
    # the registry's one standing exception.
    # P29.3 (ACTIVATE.3) — targeted accountability/governance breadth under
    # GL-GATE-07 (HG-03, LEDGER GATE DECISIONS 2026-09-23): +5 new registry rows
    # (334 → 339: gao_surveillance_reports, dhs_oig_reports,
    # dhs_fusion_center_assessments, fema_hsgp_allocations — US federal PD /
    # CC0-1.0; uk_surveillance_camera_commissioner — non-US /
    # LicenseRef-OperatorAccepted-DBRight) and +8 flips (the 5 new rows + the 3
    # pre-registered gated CCOPS discovery rows ccops_oakland/ccops_cambridge/
    # ccops_somerville, US municipal → LicenseRef-PublicRecord-FactualCompilation;
    # 228 → 236 loadable). flip-ready stays 1 (the new rows land already flipped).
    assert main(["review-status"]) == 0
    out = capsys.readouterr().out
    assert "registered sources: 339" in out
    assert "flip-ready: 1" in out
    assert "flip-ready: state_alpr_statute_inventory" in out
    assert "loadable now: 236" in out


def test_review_status_loadable_equals_validate() -> None:
    # review-status' loadable-now count must equal validate's (both = is_loadable).
    from connectors.loader import is_loadable

    loadable = [s for s in sources() if is_loadable(s)]
    assert len(loadable) == 236
    # state_alpr_statute_inventory is the single flip-ready row: its rights
    # resolved for the landed seed claims (P27.2/ADR-095) while the live gate
    # stays closed by design — one-time seed, never a feed (SIG-INGEST-049f).
    assert {s.id for s in flip_ready()} == {"state_alpr_statute_inventory"}


def test_flip_ready_excludes_permitted_and_undetermined_and_link() -> None:
    permitted = _record("t_perm", permitted=True)
    undetermined = _record("t_und", permitted=False, spdx=UNDETERMINED, redistributable=False)
    link = _record("t_link", permitted=False, custody=CustodyPosture.LINK)
    ready = _record("t_ready", permitted=False)
    assert is_flip_ready(ready) is True
    assert is_flip_ready(permitted) is False  # flag already true
    assert is_flip_ready(undetermined) is False  # no rights block
    assert is_flip_ready(link) is False  # link-only custody


def test_review_status_single_source_shows_five_gate_fields(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["review-status", "--source", "osm_overpass"]) == 0
    out = capsys.readouterr().out
    for field in ("ingestion_permitted=", "compact=", "custody=", "rights=", "reviewed-by="):
        assert field in out
    # osm_overpass was flipped 2026-09-10 (GL-GATE-03): now loadable, no longer
    # flip-ready (the flag is true), all five gate fields green.
    assert "ingestion_permitted=True" in out
    assert "flip-ready: False" in out
    assert "loadable now: True" in out


def test_review_status_unknown_source_is_an_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["review-status", "--source", "no_such_source"]) == 2


def test_gate_breakdown_reports_all_five_fields() -> None:
    bd = gate_breakdown(_record("t", permitted=False))
    assert bd.compact_ok and bd.custody_ok and bd.rights_present and bd.reviewed_by
    assert bd.ingestion_permitted is False
    assert bd.flip_ready is True
    assert bd.loadable is False
