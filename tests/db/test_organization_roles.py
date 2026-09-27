# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P32.3 canonical organisation-role taxonomy (SIG-TRUST-003, ADR-122).

One mapping — consumed by the ``dot_511`` adapter, ``resolution.partner_identity``
and the P28.6 accountability join — keeps a publisher label from ever becoming
an operator relationship (the OSM-contributor case) while an authoritative
operator field still mints one.
"""

from __future__ import annotations

from db.organization_roles import (
    ENTITY_REF_ROLES,
    ORGANIZATION_ROLES,
    PROVENANCE_ROLES,
    ROLE_OF_PREDICATE,
    OrganizationRole,
    mints_entity_ref,
    predicates_for_role,
    role_for_predicate,
)


def test_the_taxonomy_covers_every_required_role() -> None:
    # The ticket's roles: publisher, operator, owner, vendor, prime contractor
    # and access — plus the procurement/funding/oversight roles the joins use.
    for role in (
        OrganizationRole.PUBLISHER,
        OrganizationRole.OPERATOR,
        OrganizationRole.OWNER,
        OrganizationRole.VENDOR,
        OrganizationRole.PRIME,
        OrganizationRole.ACCESS,
        OrganizationRole.BUYER,
        OrganizationRole.RECIPIENT,
        OrganizationRole.FUNDER,
    ):
        assert role in ORGANIZATION_ROLES


def test_provenance_roles_never_mint_entity_refs() -> None:
    assert PROVENANCE_ROLES == {OrganizationRole.PUBLISHER, OrganizationRole.HOST}
    assert not PROVENANCE_ROLES & ENTITY_REF_ROLES
    # The canonical case: the OSM-contributor-style registry publisher label.
    assert mints_entity_ref("camera_registry_publisher") is False
    # …but the claim still has a role — the taxonomy records WHY nothing mints.
    assert role_for_predicate("camera_registry_publisher") is OrganizationRole.PUBLISHER


def test_operational_roles_mint_candidates_with_the_role_attached() -> None:
    for predicate, role in (
        ("camera_operator", OrganizationRole.OPERATOR),
        ("operator", OrganizationRole.OPERATOR),
        ("owned_by", OrganizationRole.OWNER),
        ("vendor", OrganizationRole.VENDOR),
        ("buyer", OrganizationRole.BUYER),
        ("seller", OrganizationRole.VENDOR),
        ("recipient", OrganizationRole.RECIPIENT),
        ("funder", OrganizationRole.FUNDER),
        ("configured_sharing_partner", OrganizationRole.ACCESS),
        ("event_organizations", OrganizationRole.PARTICIPANT),
    ):
        assert role_for_predicate(predicate) is role
        assert mints_entity_ref(predicate) is True


def test_unmapped_predicates_mint_nothing() -> None:
    assert role_for_predicate("deployed_camera_count") is None
    assert mints_entity_ref("deployed_camera_count") is False
    assert mints_entity_ref("made_up_predicate") is False


def test_predicates_for_role_is_the_exact_inverse() -> None:
    assert predicates_for_role(OrganizationRole.PUBLISHER) == frozenset(
        {"camera_registry_publisher"}
    )
    rebuilt = frozenset(p for role in ORGANIZATION_ROLES for p in predicates_for_role(role))
    assert rebuilt == frozenset(ROLE_OF_PREDICATE)


def test_the_accountability_join_uses_the_same_taxonomy() -> None:
    # The inference layer derives its legs from this module — the import must
    # exist and exclude every provenance-role predicate (SIG-TRUST-003).
    from inference.accountability import ACCOUNTABILITY_PREDICATES

    provenance_predicates = frozenset(
        p for role in PROVENANCE_ROLES for p in predicates_for_role(role)
    )
    assert not provenance_predicates & ACCOUNTABILITY_PREDICATES
    # The operator leg still carries the authoritative-operator predicates.
    assert "camera_operator" in ACCOUNTABILITY_PREDICATES
    assert "operator" in ACCOUNTABILITY_PREDICATES
