# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Temporal identity: reified relations, rename-is-not-succession, and the five
worked succession fixtures (§14.5, SIG-IDENT-016/017/019)."""

from __future__ import annotations

from datetime import date

import pytest
from resolution.identity import Identifier, Organization, identifier_set
from resolution.temporal_identity import (
    OrganizationRelation,
    OrganizationRelationType,
    absorb,
    acquire,
    merge,
    municipality_department_pair,
    rename_organization,
    split,
    transfer_product_vendor,
)

EFFECTIVE = date(2021, 7, 1)


def _org(entity_id: str, org_class: str = "us.le.municipal_police") -> Organization:
    return Organization(organization_class=org_class, entity_id=entity_id)


# --- SIG-IDENT-016: the seven-value reified vocabulary -----------------------


def test_relation_vocabulary_is_exactly_seven_values() -> None:
    assert {r.value for r in OrganizationRelationType} == {
        "same_as",
        "succeeded_by",
        "merged_into",
        "split_into",
        "absorbed",
        "parent_of",
        "acquired",
    }


def test_relation_carries_valid_time_and_serialises() -> None:
    rel = OrganizationRelation(
        from_entity="a",
        to_entity="b",
        relation_type=OrganizationRelationType.MERGED_INTO,
        valid_from=EFFECTIVE,
    )
    row = rel.to_row()
    assert row["relation_type"] == "merged_into"
    assert row["valid_from"] == EFFECTIVE
    assert row["valid_to"] is None
    # sys_period (transaction time) is DB-controlled and not emitted here.
    assert "sys_period" not in row


def test_relation_rejects_a_self_loop_and_coerces_a_string_type() -> None:
    with pytest.raises(ValueError, match="two distinct entities"):
        OrganizationRelation(
            from_entity="a", to_entity="a", relation_type="same_as", valid_from=EFFECTIVE
        )
    rel = OrganizationRelation(
        from_entity="a", to_entity="b", relation_type="acquired", valid_from=EFFECTIVE
    )
    assert rel.relation_type is OrganizationRelationType.ACQUIRED


# --- SIG-IDENT-019 fixture 4 + SIG-IDENT-017: a pure rename -------------------


def test_rename_produces_no_succession_and_no_new_identifier() -> None:
    org = Organization(
        organization_class="us.le.municipal_police",
        entity_id="dept-1",
        identifiers=identifier_set([("us.fbi.ori", "CA0194200")]),
    )
    result = rename_organization(
        org,
        old_name="Clarkstown Police Department",
        new_name="Clarkstown Department of Public Safety",
        effective=EFFECTIVE,
    )
    # The load-bearing assertions of SIG-IDENT-017:
    assert result.relations == ()  # NO succession relation
    assert result.new_identifiers == ()  # NO new identifier
    assert result.former_alias.name == "Clarkstown Police Department"
    assert result.former_alias.alias_type == "former_name"
    assert result.former_alias.valid_to == EFFECTIVE  # the old name is dated out
    assert result.new_canonical_name == "Clarkstown Department of Public Safety"
    # Identity is preserved: same entity, same identifier set (a new *version*).
    assert result.organization.entity_id == "dept-1"
    assert result.organization.identifiers == org.identifiers


# --- SIG-IDENT-019 fixture 1: disbanded PD absorbed by a county sheriff -------


def test_absorb_fixture() -> None:
    outcome = absorb(absorbed="pd-1", into="sheriff-1", effective=EFFECTIVE)
    assert len(outcome.relations) == 1
    rel = outcome.relations[0]
    assert rel.relation_type is OrganizationRelationType.ABSORBED
    assert (rel.from_entity, rel.to_entity) == ("pd-1", "sheriff-1")
    assert outcome.retired == ("pd-1",)


# --- SIG-IDENT-019 fixture 2: two departments merging into a new one ---------


def test_merge_fixture() -> None:
    outcome = merge(sources=("pd-a", "pd-b"), into="metro-pd", effective=EFFECTIVE)
    assert len(outcome.relations) == 2
    assert all(r.relation_type is OrganizationRelationType.MERGED_INTO for r in outcome.relations)
    assert {r.from_entity for r in outcome.relations} == {"pd-a", "pd-b"}
    assert all(r.to_entity == "metro-pd" for r in outcome.relations)
    assert outcome.retired == ("pd-a", "pd-b")


def test_merge_needs_two_sources() -> None:
    with pytest.raises(ValueError, match="at least two source"):
        merge(sources=("pd-a",), into="metro-pd", effective=EFFECTIVE)


# --- SIG-IDENT-019 fixture 3: a department splitting -------------------------


def test_split_fixture() -> None:
    outcome = split(source="county-pd", into=("north-pd", "south-pd"), effective=EFFECTIVE)
    assert len(outcome.relations) == 2
    assert all(r.relation_type is OrganizationRelationType.SPLIT_INTO for r in outcome.relations)
    assert all(r.from_entity == "county-pd" for r in outcome.relations)
    assert {r.to_entity for r in outcome.relations} == {"north-pd", "south-pd"}
    assert outcome.retired == ("county-pd",)


def test_split_needs_two_children() -> None:
    with pytest.raises(ValueError, match="at least two"):
        split(source="county-pd", into=("north-pd",), effective=EFFECTIVE)


# --- SIG-IDENT-019 fixture 5: a vendor acquisition transferring products ------


def test_acquire_fixture_transfers_product_ownership() -> None:
    outcome = acquire(acquirer="vendor-new", acquired="vendor-old", effective=EFFECTIVE)
    assert len(outcome.relations) == 1
    rel = outcome.relations[0]
    assert rel.relation_type is OrganizationRelationType.ACQUIRED
    assert (rel.from_entity, rel.to_entity) == ("vendor-new", "vendor-old")
    # The acquired vendor persists under new ownership — it is not retired.
    assert outcome.retired == ()
    # Product ownership transfer is a new vendor claim, never a mutation.
    transfer = transfer_product_vendor(product_id="product-x", new_vendor="vendor-new")
    assert transfer == {"product_id": "product-x", "vendor": "vendor-new"}


# --- SIG-IDENT-009: municipality and its police department are distinct -------


def test_municipality_and_department_are_distinct_joined_by_parent_of() -> None:
    city = _org("city-1", org_class="us.gov.municipality")
    dept = _org("dept-1", org_class="us.le.municipal_police")
    muni, department, relation = municipality_department_pair(
        municipality=city, department=dept, effective=EFFECTIVE
    )
    assert muni.entity_id != department.entity_id  # distinct organizations
    assert relation.relation_type is OrganizationRelationType.PARENT_OF
    assert (relation.from_entity, relation.to_entity) == ("city-1", "dept-1")


def test_municipality_department_pair_requires_distinct_entities() -> None:
    same = _org("x-1")
    with pytest.raises(ValueError, match="distinct organizations"):
        municipality_department_pair(municipality=same, department=same, effective=EFFECTIVE)


def test_municipality_department_pair_requires_entity_ids() -> None:
    city = Organization(organization_class="us.gov.municipality")  # no entity_id
    dept = _org("dept-1")
    with pytest.raises(ValueError, match="entity ids"):
        municipality_department_pair(municipality=city, department=dept, effective=EFFECTIVE)


def test_identifiers_survive_a_rename_unchanged() -> None:
    org = Organization(
        organization_class="us.le.municipal_police",
        entity_id="dept-1",
        identifiers=frozenset({Identifier("us.fbi.ori", "CA0194200")}),
    )
    result = rename_organization(org, old_name="Old PD", new_name="New PD", effective=EFFECTIVE)
    # SIG-IDENT-017: no identifier is minted, and the set is exactly what it was.
    assert result.new_identifiers == ()
    assert result.organization.identifiers == org.identifiers
    assert len(result.organization.identifiers) == 1
