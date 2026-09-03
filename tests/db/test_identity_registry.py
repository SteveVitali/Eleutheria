# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The identity substrate at the physical layer (App C.4, §14): distinct
organizations joined by parent_of, the reified bitemporal relation, identifiers as
a set, and the temporal jurisdiction boundary (SIG-IDENT-006/009/016, SIG-ONTO-011)."""

from __future__ import annotations

import psycopg
import pytest
from psycopg.types.json import Json

SEVEN_RELATION_TYPES = (
    "same_as",
    "succeeded_by",
    "merged_into",
    "split_into",
    "absorbed",
    "parent_of",
    "acquired",
)


def _new_entity(conn: object, entity_type: str) -> object:
    cur = conn.cursor()
    cur.execute("INSERT INTO entity(entity_type) VALUES(%s) RETURNING entity_id", (entity_type,))
    return cur.fetchone()[0]


def _new_org(
    conn: object,
    org_class: str,
    *,
    status: str = "active",
    identity_basis: dict[str, object] | None = None,
    publication_review_required: bool = False,
) -> object:
    entity_id = _new_entity(conn, "organization")
    conn.cursor().execute(
        "INSERT INTO organization(entity_id,organization_type,status,identity_basis,"
        "publication_review_required) VALUES(%s,%s,%s,%s,%s)",
        (
            entity_id,
            org_class,
            status,
            Json(identity_basis) if identity_basis is not None else None,
            publication_review_required,
        ),
    )
    return entity_id


def _relate(conn: object, frm: object, to: object, relation_type: str, valid_from: str) -> object:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO organization_relation(from_entity,to_entity,relation_type,valid_period) "
        "VALUES(%s,%s,%s,tstzrange(%s,NULL,'[)')) RETURNING relation_id, sys_period",
        (frm, to, relation_type, valid_from),
    )
    return cur.fetchone()


def test_municipality_and_department_are_distinct_joined_by_parent_of(conn: object) -> None:
    # SIG-IDENT-009: the city and its police department are separate rows.
    city = _new_org(conn, "us.gov.municipality")
    dept = _new_org(conn, "us.le.municipal_police")
    assert city != dept
    relation_id, sys_period = _relate(conn, city, dept, "parent_of", "2010-01-01")
    assert relation_id is not None
    # SIG-IDENT-016: the relation is bitemporal — a current row's transaction time
    # is open (upper-unbounded), never a mutable column.
    assert sys_period.upper is None
    row = (
        conn.cursor()
        .execute(
            "SELECT from_entity,to_entity,relation_type FROM organization_relation "
            "WHERE relation_id=%s",
            (relation_id,),
        )
        .fetchone()
    )
    assert row == (city, dept, "parent_of")


def test_all_seven_relation_types_are_storable(conn: object) -> None:
    # SIG-IDENT-016: the seven-value vocabulary round-trips through the reified table.
    a = _new_org(conn, "us.le.municipal_police")
    b = _new_org(conn, "us.le.sheriff")
    for rtype in SEVEN_RELATION_TYPES:
        _relate(conn, a, b, rtype, "2020-01-01")
    stored = (
        conn.cursor()
        .execute("SELECT relation_type FROM organization_relation WHERE from_entity=%s", (a,))
        .fetchall()
    )
    assert {r[0] for r in stored} == set(SEVEN_RELATION_TYPES)


def test_identifiers_are_a_set_per_entity(conn: object) -> None:
    # SIG-IDENT-006: (entity_id, scheme, value) is the primary key — the same pair
    # cannot be inserted twice for one entity.
    org = _new_org(conn, "us.le.municipal_police")
    conn.cursor().execute(
        "INSERT INTO entity_identifier(entity_id,scheme,value) VALUES(%s,'us.fbi.ori','CA0194200')",
        (org,),
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        with conn.transaction():
            conn.cursor().execute(
                "INSERT INTO entity_identifier(entity_id,scheme,value) "
                "VALUES(%s,'us.fbi.ori','CA0194200')",
                (org,),
            )


def test_surrogate_identity_basis_round_trips(conn: object) -> None:
    # SIG-IDENT-012 / SIG-ONTO-013: an immutable basis is stored as jsonb and the
    # publication-review flag persists.
    basis = {
        "normalized_name": "maple grove hoa",
        "org_class": "private.hoa",
        "place_geoid": "0667000",
        "address_hash": None,
        "first_seen_source_ref": "flock:portal:maple-grove",
        "first_seen_at": "2026-05-01",
    }
    org = _new_org(conn, "private.hoa", identity_basis=basis, publication_review_required=True)
    row = (
        conn.cursor()
        .execute(
            "SELECT identity_basis, publication_review_required, status FROM organization "
            "WHERE entity_id=%s",
            (org,),
        )
        .fetchone()
    )
    assert row[0]["normalized_name"] == "maple grove hoa"
    assert row[1] is True
    assert row[2] == "active"


def test_status_vocabulary_values_persist(conn: object) -> None:
    # SIG-IDENT-018: suppressed is distinct from withdrawn (both storable).
    for status in ("active", "inactive", "withdrawn", "suppressed"):
        org = _new_org(conn, "us.le.municipal_police", status=status)
        got = (
            conn.cursor()
            .execute("SELECT status FROM organization WHERE entity_id=%s", (org,))
            .fetchone()[0]
        )
        assert got == status


def test_jurisdiction_requires_an_explicit_level(conn: object) -> None:
    # SIG-IDENT-005: level is NOT NULL on every jurisdiction row.
    entity_id = _new_entity(conn, "jurisdiction")
    with pytest.raises(psycopg.errors.NotNullViolation):
        with conn.transaction():
            conn.cursor().execute(
                "INSERT INTO jurisdiction(entity_id,jurisdiction_type,level) VALUES(%s,%s,NULL)",
                (entity_id, "municipality"),
            )


def test_jurisdiction_boundary_is_temporally_versioned(conn: object) -> None:
    # SIG-ONTO-011: the boundary carries a validity interval, so an as-of query can
    # return a jurisdiction's geometry as it stood on a past date.
    entity_id = _new_entity(conn, "jurisdiction")
    conn.cursor().execute(
        "INSERT INTO jurisdiction(entity_id,jurisdiction_type,level,boundary,boundary_valid) "
        "VALUES(%s,'municipality','place',"
        "ST_Multi(ST_GeomFromText('POLYGON((0 0,0 1,1 1,1 0,0 0))',4326)),"
        "tstzrange('2015-01-01',NULL,'[)'))",
        (entity_id,),
    )
    # In force on a later date...
    in_force = (
        conn.cursor()
        .execute(
            "SELECT boundary_valid @> %s::timestamptz FROM jurisdiction WHERE entity_id=%s",
            ("2020-06-01", entity_id),
        )
        .fetchone()[0]
    )
    assert in_force is True
    # ...but not before the annexation date it became valid.
    before = (
        conn.cursor()
        .execute(
            "SELECT boundary_valid @> %s::timestamptz FROM jurisdiction WHERE entity_id=%s",
            ("2010-06-01", entity_id),
        )
        .fetchone()[0]
    )
    assert before is False
