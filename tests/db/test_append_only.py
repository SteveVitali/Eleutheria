# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Append-only enforcement on the claim table (§16.3; SIG-STORE-011/012/013).

AC1: UPDATE/DELETE on `claim` are rejected except closing `sys_period`.
"""

from __future__ import annotations

import psycopg
import pytest
from conftest import insert_claim, seed_claim_prerequisites


def test_update_of_a_value_column_is_rejected(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    insert_claim(conn, prereqs)
    with pytest.raises(psycopg.Error) as excinfo:
        with conn.transaction():
            conn.execute("UPDATE claim SET value_text = '999'")
    assert "immutable" in str(excinfo.value)


def test_delete_is_rejected(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    insert_claim(conn, prereqs)
    with pytest.raises(psycopg.Error) as excinfo:
        with conn.transaction():
            conn.execute("DELETE FROM claim")
    assert "DELETE forbidden" in str(excinfo.value)


def test_closing_sys_period_is_permitted(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    insert_claim(conn, prereqs)
    cur = conn.execute(
        "UPDATE claim SET sys_period = tstzrange(lower(sys_period), "
        "clock_timestamp(), '[)') WHERE upper_inf(sys_period)"
    )
    assert cur.rowcount == 1
    # And a claim already closed cannot be closed again.
    with pytest.raises(psycopg.Error) as excinfo:
        with conn.transaction():
            conn.execute(
                "UPDATE claim SET sys_period = tstzrange(lower(sys_period), "
                "clock_timestamp(), '[)')"
            )
    assert "already closed" in str(excinfo.value)


def test_sys_period_lower_bound_is_immutable(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    insert_claim(conn, prereqs)
    with pytest.raises(psycopg.Error) as excinfo:
        with conn.transaction():
            conn.execute(
                "UPDATE claim SET sys_period = tstzrange("
                "lower(sys_period) - interval '1 day', NULL, '[)')"
            )
    assert "lower bound is immutable" in str(excinfo.value)


def test_application_roles_lack_delete_on_append_only_tables(conn: object) -> None:
    """SIG-STORE-012: application roles hold no DELETE on the append-only tables
    (defence in depth, alongside the trigger)."""
    tables = ("claim", "extraction", "evidence_artifact", "evidence_capture")
    for role in ("sig_ingest", "sig_read_public"):
        for table in tables:
            has_delete = conn.execute(
                "SELECT has_table_privilege(%s, %s, 'DELETE')", (role, table)
            ).fetchone()[0]
            assert has_delete is False, f"{role} unexpectedly holds DELETE on {table}"


def test_guard_column_list_matches_the_live_schema(conn: object) -> None:
    """SIG-STORE-011: the mutable-guard list is the live claim columns minus
    sys_period, so adding a column cannot silently widen what is mutable."""
    live = {
        r[0]
        for r in conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='claim'"
        ).fetchall()
    }
    guarded = {
        r[0]
        for r in conn.execute(
            "SELECT column_name FROM append_only_guard WHERE table_name='claim'"
        ).fetchall()
    }
    assert guarded == live - {"sys_period"}
    assert "sys_period" not in guarded
