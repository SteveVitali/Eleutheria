# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Schema-integrity guards (§16.1, Appendix C.7; SIG-STORE-008/009/026/047).

These are mechanical guards, not review: L2 entity tables must stay identity-only
(AC2), and a set of columns/tables must NEVER exist (AC6 and the §C.7 absences).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# The L2 identity tables (Appendix C.1/C.4). Every attribute of these entities is
# a claim; only identity, typing, bookkeeping, and cached resolver outputs live
# here (SIG-STORE-008/046).
ENTITY_TABLES = (
    "entity",
    "jurisdiction",
    "organization",
    "person",
    "product",
    "technology",
    "capability",
    "deployment",
    "physical_asset",
    "candidate_asset",
    "data_system",
    "contract",
    "funding_instrument",
    "policy",
    "legal_instrument",
    "configuration_state",
    "accountability_event",
    "legal_proceeding",
    "records_request",
)

# SIG-STORE-046: columns that legitimately share a name with a registered
# predicate because they are CACHED RESOLVER OUTPUTS, typing, or crosswalk
# identity — not writable authoritative attributes. Each is reviewed here.
PREDICATE_NAMED_COLUMN_ALLOWLIST = {
    ("deployment", "procurement_state"),  # cached lifecycle track (SIG-ONTO-061)
    ("deployment", "operational_state"),  # cached lifecycle track
    ("deployment", "authorization_state"),  # cached lifecycle track
    ("organization", "organization_type"),  # typing column
    ("product", "product_status"),  # typing/status column
    ("funding_instrument", "federal_award_id"),  # crosswalk identifier
}


def _registered_predicate_ids() -> set[str]:
    path = REPO_ROOT / "ontology" / "generated" / "registry" / "predicate_registry.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {p["predicate_id"] for p in data["predicates"]}


def _columns(conn: object, table: str) -> set[str]:
    return {
        r[0]
        for r in conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=%s",
            (table,),
        ).fetchall()
    }


def _all_public_columns(conn: object) -> list[tuple[str, str]]:
    return [
        (r[0], r[1])
        for r in conn.execute(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema='public'"
        ).fetchall()
    ]


def _all_public_tables(conn: object) -> set[str]:
    return {
        r[0]
        for r in conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_type='BASE TABLE'"
        ).fetchall()
    }


def test_entity_tables_hold_no_duplicate_predicate_columns(conn: object) -> None:
    """AC2 / SIG-STORE-009: no entity-table column duplicates a registered
    predicate id, except the reviewed cached/typing allowlist (SIG-STORE-046)."""
    predicates = _registered_predicate_ids()
    assert predicates, "the generated predicate registry must be non-empty"

    collisions: set[tuple[str, str]] = set()
    for table in ENTITY_TABLES:
        for column in _columns(conn, table):
            if column in predicates:
                collisions.add((table, column))

    violations = collisions - PREDICATE_NAMED_COLUMN_ALLOWLIST
    assert violations == set(), (
        f"entity columns duplicate a predicate id (SIG-STORE-009): {sorted(violations)}"
    )
    # The allowlist must not rot: every exemption must still be a real collision.
    stale = PREDICATE_NAMED_COLUMN_ALLOWLIST - collisions
    assert stale == set(), f"stale predicate-column exemptions: {sorted(stale)}"


def test_no_plate_capable_column_anywhere(conn: object) -> None:
    """AC6 / SIG-STORE-026: no column anywhere can hold a licence plate.

    Token-based, not substring: `template` (contains "plate") is not a plate
    column, but `plate`, `license_plate`, `plate_number`, `vrm` are.
    """
    plate_tokens = {"plate", "vrm"}
    plate_phrases = ("license_plate", "licence_plate", "plate_number", "plate_no")
    offenders = [
        (t, c)
        for t, c in _all_public_columns(conn)
        if (plate_tokens & set(re.split(r"[_.]", c.lower())))
        or any(phrase in c.lower() for phrase in plate_phrases)
    ]
    assert offenders == [], f"plate-capable columns found (SIG-STORE-026): {offenders}"


def test_no_per_search_sighting_or_trip_table(conn: object) -> None:
    """SIG-STORE-047 / §18.1: no per-search, per-sighting, or per-trip table."""
    forbidden_tokens = {"sighting", "sightings", "trip", "trips", "plate", "plates"}
    offenders = [
        t
        for t in _all_public_tables(conn)
        if (forbidden_tokens & set(re.split(r"[_.]", t.lower()))) or "per_search" in t.lower()
    ]
    assert offenders == [], f"forbidden event tables found (§18.1): {offenders}"


def test_person_has_no_address_column(conn: object) -> None:
    """SIG-STORE-047 / SIG-PUB-003: person carries no address, at any tier."""
    offenders = [c for c in _columns(conn, "person") if "address" in c.lower()]
    assert offenders == [], f"person has an address column (SIG-PUB-003): {offenders}"


def test_claim_has_no_stored_currency_column(conn: object) -> None:
    """SIG-STORE-047 / SIG-EPIS-020: currency (C) is derived at query time."""
    assert "currency" not in _columns(conn, "claim")


def test_integrates_with_edge_value_is_forbidden(conn: object) -> None:
    """SIG-STORE-047 / SIG-ONTO-045: no `integrates_with` edge value (CHECK)."""
    defs = [
        r[0]
        for r in conn.execute(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conrelid = 'relationship'::regclass AND contype='c'"
        ).fetchall()
    ]
    assert any("integrates_with" in d for d in defs), (
        "relationship must forbid the integrates_with edge value"
    )
