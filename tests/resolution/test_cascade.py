# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The deterministic cascade, tiers 0–3: auto-write, match_tier + match_evidence
on every match, civil-ORI refusal, and blocking-only keys never as identity
(SIG-IDENT-020/025/003/013)."""

from __future__ import annotations

import pytest
from resolution.address import build_address_keys
from resolution.cascade import Candidate, CascadeContext, MatchResult, resolve
from resolution.identity import identifier_set


def _ctx() -> CascadeContext:
    return CascadeContext.from_data()


# --- SIG-IDENT-025: every match records tier + evidence, disposition auto-write


def _assert_auto_write(result: MatchResult | None, tier: int, label: str) -> MatchResult:
    assert result is not None
    assert result.match_tier == tier
    assert result.tier_label == label
    assert result.disposition == "auto_write"
    assert result.match_evidence and "rule" in result.match_evidence
    return result


# --- Tier 0: exact shared canonical identifier -------------------------------


def test_tier0_exact_shared_ori_auto_writes() -> None:
    a = Candidate(
        "A",
        "us.le.sheriff",
        "Travis County Sheriff Office",
        "TX",
        identifiers=identifier_set([("us.fbi.ori", "TX2270000")]),
    )
    b = Candidate(
        "B",
        "us.le.sheriff",
        "Travis County SO",
        "TX",
        identifiers=identifier_set([("us.fbi.ori", "TX2270000")]),
    )
    result = _assert_auto_write(resolve(a, b), 0, "0")
    assert result.match_evidence["shared_identifiers"] == [
        {"scheme": "us.fbi.ori", "value": "TX2270000"}
    ]


def test_tier0_malformed_shared_ori_does_not_crash_or_auto_link() -> None:
    # A malformed value under the ORI scheme is not a valid canonical identifier;
    # it must neither crash the cascade nor serve as a tier-0 basis.
    a = Candidate(
        "A",
        "us.le.sheriff",
        "Alpha",
        "TX",
        identifiers=identifier_set([("us.fbi.ori", "not-an-ori")]),
    )
    b = Candidate(
        "B",
        "us.le.sheriff",
        "Beta",
        "CA",
        identifiers=identifier_set([("us.fbi.ori", "not-an-ori")]),
    )
    assert resolve(a, b) is None


def test_tier0_different_identifiers_do_not_match_at_tier0() -> None:
    a = Candidate("A", "vendor", "Acme", identifiers=identifier_set([("gleif.lei", "AAAA")]))
    b = Candidate("B", "vendor", "Beta", identifiers=identifier_set([("gleif.lei", "BBBB")]))
    assert resolve(a, b) is None


# --- SIG-IDENT-003: a civil ORI is not a sufficient sole basis ---------------


def test_civil_ori_alone_does_not_auto_link_at_tier0() -> None:
    # Ninth char alphabetic → civil/applicant ORI; identical civil ORIs must NOT
    # auto-link at tier 0 without a second source. With mismatched names/state the
    # pair falls through entirely.
    a = Candidate(
        "A",
        "us.le.sheriff",
        "Alpha County SO",
        "TX",
        identifiers=identifier_set([("us.fbi.ori", "TX22700AA")]),
    )
    b = Candidate(
        "B",
        "us.le.sheriff",
        "Beta County SO",
        "CA",
        identifiers=identifier_set([("us.fbi.ori", "TX22700AA")]),
    )
    assert resolve(a, b) is None


def test_civil_ori_with_a_second_shared_id_still_auto_links() -> None:
    # The civil ORI is dropped as a basis, but a co-present non-civil canonical id
    # (a shared GEOID) is a valid tier-0 basis.
    a = Candidate(
        "A",
        "us.le.sheriff",
        "Alpha",
        "TX",
        identifiers=identifier_set([("us.fbi.ori", "TX22700AA"), ("us.census.geoid", "4835000")]),
    )
    b = Candidate(
        "B",
        "us.le.sheriff",
        "Beta",
        "CA",
        identifiers=identifier_set([("us.fbi.ori", "TX22700AA"), ("us.census.geoid", "4835000")]),
    )
    result = _assert_auto_write(resolve(a, b), 0, "0")
    schemes = {i["scheme"] for i in result.match_evidence["shared_identifiers"]}
    assert schemes == {"us.census.geoid"}  # the civil ORI is excluded from evidence


# --- Tier 1: established upstream crosswalk ----------------------------------


def test_tier1_established_crosswalk_auto_writes() -> None:
    a = Candidate(
        "A",
        "us.le.municipal_police",
        "X PD",
        "CA",
        identifiers=identifier_set([("us.fbi.ori", "CA0194200")]),
    )
    # b has no shared identifier, but an upstream crosswalk established A's ORI as b's.
    b = Candidate(
        "B",
        "us.le.municipal_police",
        "Y PD",
        "CA",
        crosswalk_ids=identifier_set([("us.fbi.ori", "CA0194200")]),
    )
    _assert_auto_write(resolve(a, b), 1, "1")


# --- Tier 2: normalized name + state + class, minus collisions ---------------


def test_tier2_name_state_class_auto_writes() -> None:
    a = Candidate("A", "us.le.sheriff", "Travis County Sheriff's Office", "TX")
    b = Candidate("B", "us.le.sheriff", "Travis County Sheriff's Department", "TX")
    result = _assert_auto_write(resolve(a, b), 2, "2")
    assert result.match_evidence["normalized_name"] == "travis county sheriff office"
    assert "normalize_ruleset_version" in result.match_evidence


def test_tier2_requires_same_state_and_class() -> None:
    a = Candidate("A", "us.le.sheriff", "Travis County Sheriff Office", "TX")
    assert resolve(a, Candidate("B", "us.le.sheriff", "Travis County Sheriff Office", "CA")) is None
    assert resolve(a, Candidate("C", "us.gov.county", "Travis County Sheriff Office", "TX")) is None


def test_tier2_collision_name_is_not_auto_written() -> None:
    # A name on the data-generated collision list routes to review, never merges.
    a = Candidate("A", "us.le.municipal_police", "Springfield Police Department", "IL")
    b = Candidate("B", "us.le.municipal_police", "Springfield Police Department", "IL")
    assert resolve(a, b) is None


def test_tier2_missing_state_never_matches() -> None:
    a = Candidate("A", "us.le.sheriff", "Travis County Sheriff Office")
    b = Candidate("B", "us.le.sheriff", "Travis County Sheriff Office")
    assert resolve(a, b) is None  # a None state is not "the same state"


# --- Tier 3a: shared government domain ---------------------------------------


def test_tier3a_shared_gov_domain_auto_writes() -> None:
    a = Candidate("A", "us.gov.municipality", "City of Berkeley", "CA", gov_domain="berkeley.gov")
    b = Candidate("B", "us.gov.municipality", "Berkeley", "CA", gov_domain="Berkeley.gov")
    result = _assert_auto_write(resolve(a, b), 3, "3a")
    assert result.match_evidence["domain"] == "berkeley.gov"


def test_tier3a_shared_hosting_domain_is_excluded() -> None:
    a = Candidate("A", "private.company", "Alpha", gov_domain="wordpress.com")
    b = Candidate("B", "private.company", "Beta", gov_domain="wordpress.com")
    assert resolve(a, b) is None


# --- Tier 3b: address key K1 + normalized name -------------------------------


def test_tier3b_k1_plus_name_auto_writes() -> None:
    # State is unknown here, so tier 2 (which requires a shared non-null state)
    # cannot fire; K1 + normalized name is what auto-writes at tier 3b.
    keys = build_address_keys(tiger_line_side="edge-99:L", block_geoid="481576789012345")
    a = Candidate("A", "private.company", "Acme Security LLC", address=keys)
    b = Candidate(
        "B",
        "private.company",
        "Acme Security LLC",
        address=build_address_keys(tiger_line_side="edge-99:L"),
    )
    result = _assert_auto_write(resolve(a, b), 3, "3b")
    assert result.match_evidence["address_key"] == {"K1": "edge-99:L"}


def test_tier3b_uses_only_k1_never_a_blocking_key() -> None:
    # Same tract (K3) and place (K4) but different K1 and different names → no
    # match: K3/K4 are never identity evidence (SIG-IDENT-013), and a shared tract
    # alone can never merge two differently-named bodies.
    a = Candidate(
        "A",
        "private.company",
        "Acme Security LLC",
        address=build_address_keys(
            tiger_line_side="edge-1:L", tract_geoid="48157678901", place_geoid="4835000"
        ),
    )
    b = Candidate(
        "B",
        "private.company",
        "Beta Cameras Inc",
        address=build_address_keys(
            tiger_line_side="edge-2:R", tract_geoid="48157678901", place_geoid="4835000"
        ),
    )
    assert resolve(a, b) is None


# --- Ordering + no-match ------------------------------------------------------


def test_tier0_precedes_lower_tiers() -> None:
    # A pair that satisfies both tier 0 and tier 2 reports tier 0 (highest priority).
    a = Candidate(
        "A",
        "us.le.sheriff",
        "Travis County Sheriff's Office",
        "TX",
        identifiers=identifier_set([("us.fbi.ori", "TX2270000")]),
    )
    b = Candidate(
        "B",
        "us.le.sheriff",
        "Travis County Sheriff's Department",
        "TX",
        identifiers=identifier_set([("us.fbi.ori", "TX2270000")]),
    )
    assert resolve(a, b).match_tier == 0


def test_no_deterministic_tier_matches_returns_none() -> None:
    a = Candidate("A", "vendor", "Alpha Systems")
    b = Candidate("B", "vendor", "Beta Corp")
    assert resolve(a, b) is None  # falls through to probabilistic tiers (P05.1)


def test_resolve_rejects_identical_candidates() -> None:
    a = Candidate("A", "vendor", "Alpha")
    with pytest.raises(ValueError, match="distinct"):
        resolve(a, a)


def test_injected_context_overrides_data_defaults() -> None:
    # An empty collision list means Springfield WOULD auto-write; proving the list
    # is data, not hardcoded.
    a = Candidate("A", "us.le.municipal_police", "Springfield Police Department", "IL")
    b = Candidate("B", "us.le.municipal_police", "Springfield Police Department", "IL")
    empty = CascadeContext(
        name_collisions=frozenset(),
        shared_hosting_domains=frozenset(),
        tier0_schemes=frozenset({"us.fbi.ori"}),
    )
    assert resolve(a, b, context=empty).match_tier == 2
