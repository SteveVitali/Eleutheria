# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Organization identity: sets, two axes, surrogate basis, colon-name parsing
(§11.2, SIG-ONTO-012/013, SIG-IDENT-006/010/011/012/018)."""

from __future__ import annotations

import dataclasses

import pytest
from resolution.identity import (
    Identifier,
    IdentityBasis,
    Organization,
    OrgStatus,
    classify,
    identifier_set,
    mint_surrogate,
    parse_agency_name,
    requires_publication_review,
)

# --- SIG-IDENT-006: identifiers are SETS of (scheme, value) ------------------


def test_identifiers_are_a_deduplicating_set() -> None:
    idents = identifier_set(
        [
            ("us.fbi.ori", "CA0194200"),
            ("us.fbi.ori", "CA0194200"),  # the same identifier seen twice
            ("wikidata.qid", "Q61"),
            Identifier("us.census.geoid", "0667000"),
        ]
    )
    assert len(idents) == 3
    assert Identifier("us.fbi.ori", "CA0194200") in idents


def test_identifier_requires_scheme_and_value() -> None:
    with pytest.raises(ValueError, match="scheme and a value"):
        Identifier("us.fbi.ori", "")
    with pytest.raises(ValueError, match="scheme and a value"):
        Identifier("", "CA0194200")


# --- SIG-IDENT-018: the status vocabulary ------------------------------------


def test_status_vocabulary() -> None:
    assert {s.value for s in OrgStatus} == {"active", "inactive", "withdrawn", "suppressed"}


# --- SIG-IDENT-010: the two independent classification axes ------------------


def test_two_axes_are_independent() -> None:
    # A single class holds different relationships in different contexts, and the
    # constructor never rejects a combination because of the other axis.
    university_buys = classify("university", "purchaser")
    university_operates = classify("university", "operator")
    assert university_buys != university_operates
    assert university_buys.organization_class == "university"
    # The axes are orthogonal: the constructor imposes no cross-axis constraint, so
    # every (class, relationship) pairing — including "unusual" ones — is accepted.
    for org_class in ("university", "us.gov.municipality", "private.hoa", "vendor"):
        for relationship in ("purchaser", "operator", "funder", "host"):
            got = classify(org_class, relationship)
            assert got.organization_class == org_class
            assert got.operating_relationship == relationship


def test_two_axes_require_both() -> None:
    with pytest.raises(ValueError):
        classify("", "operator")
    with pytest.raises(ValueError):
        classify("university", "")


# --- SIG-IDENT-012 / SIG-ONTO-013: surrogate identity ------------------------


def _basis(org_class: str = "private.hoa") -> IdentityBasis:
    return IdentityBasis(
        normalized_name="maple grove homeowners association",
        org_class=org_class,
        first_seen_source_ref="flock:portal:maple-grove",
        first_seen_at="2026-05-01",
        place_geoid="0667000",
        address_hash=None,
    )


def test_identity_basis_is_immutable_with_six_fields() -> None:
    basis = _basis()
    assert set(dataclasses.asdict(basis)) == {
        "normalized_name",
        "org_class",
        "first_seen_source_ref",
        "first_seen_at",
        "place_geoid",
        "address_hash",
    }
    with pytest.raises(dataclasses.FrozenInstanceError):
        basis.normalized_name = "something else"  # type: ignore[misc]


def test_identity_basis_requires_the_load_bearing_fields() -> None:
    with pytest.raises(ValueError, match="normalized_name"):
        IdentityBasis(
            normalized_name="",
            org_class="private.hoa",
            first_seen_source_ref="x",
            first_seen_at="2026-01-01",
        )


def test_surrogate_minting_is_deterministic_and_routes_private_bodies_to_review() -> None:
    basis = _basis()
    org_a = mint_surrogate(basis)
    org_b = mint_surrogate(_basis())
    # Idempotent minting: the same immutable basis mints the same surrogate.
    assert org_a.entity_id == org_b.entity_id
    assert org_a.identity_basis == basis
    assert org_a.status is OrgStatus.ACTIVE
    assert not org_a.has_external_identifier
    # SIG-ONTO-013: a small private body with no external id routes through §43.4.
    assert org_a.publication_review_required is True


def test_publication_review_routing_rule() -> None:
    # Surrogate-only private body → review; a public institution (has an ORI) → no.
    assert requires_publication_review("private.hoa", has_external_identifier=False)
    assert not requires_publication_review("private.hoa", has_external_identifier=True)
    assert not requires_publication_review("us.le.sheriff", has_external_identifier=False)


def test_organization_to_row_maps_class_to_type_and_carries_basis() -> None:
    basis = _basis()
    org = mint_surrogate(basis)
    row = org.to_row()
    assert row["organization_type"] == "private.hoa"
    assert row["status"] == "active"
    assert row["publication_review_required"] is True
    assert row["identity_basis"]["normalized_name"] == basis.normalized_name  # type: ignore[index]
    # cached_canonical_name is a resolver output, never written from the registry.
    assert row["cached_canonical_name"] is None


# --- SIG-IDENT-011: colon-delimited agency names -----------------------------


def test_colon_name_splits_into_parent_and_unit() -> None:
    parsed = parse_agency_name("Los Angeles County: Sheriff's Department")
    assert parsed.parent == "Los Angeles County"
    assert parsed.unit == "Sheriff's Department"
    assert parsed.has_parent


def test_name_without_colon_has_no_parent() -> None:
    parsed = parse_agency_name("Berkeley Police Department")
    assert parsed.parent is None
    assert parsed.unit == "Berkeley Police Department"
    assert not parsed.has_parent


def test_dangling_colon_is_not_a_parent_split() -> None:
    parsed = parse_agency_name("Sheriff's Department:")
    assert parsed.parent is None
    assert parsed.unit == "Sheriff's Department:"


def test_leading_colon_has_no_parent() -> None:
    # A leading colon leaves no parent name; treat the whole as a unit, not a split.
    parsed = parse_agency_name(":Sheriff's Department")
    assert parsed.parent is None
    assert parsed.unit == ":Sheriff's Department"


def test_only_the_first_colon_splits() -> None:
    # A unit may itself contain a colon; only the first colon delimits the parent.
    parsed = parse_agency_name("State of X: Dept: Special Unit")
    assert parsed.parent == "State of X"
    assert parsed.unit == "Dept: Special Unit"


def test_external_org_defaults_to_active_no_review() -> None:
    org = Organization(
        organization_class="us.le.municipal_police",
        entity_id="11111111-1111-1111-1111-111111111111",
        identifiers=identifier_set([("us.fbi.ori", "CA0194200")]),
    )
    assert org.has_external_identifier
    assert org.publication_review_required is False
    assert org.status is OrgStatus.ACTIVE
