# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The least-privilege read/materialize role (P30.2, ADR-103) over real PG18+PostGIS.

The ``materialize_role`` sqitch change (deployed + verified by the conftest container)
creates ``sig_materialize``: READ through ``sig_read_public`` (the tier-0 RLS ceiling
binds), WRITE = INSERT only on the Round-6 materialized tables, no UPDATE/DELETE/TRUNCATE
and no write on the claim spine. These tests prove the privilege boundary *and* that every
Round-6 materializer + the P29.2 detector actually runs under it (``--role
sig_materialize``), which is exactly how the hosted run executes.
"""

from __future__ import annotations

import psycopg
import pytest
from conftest import insert_claim, seed_claim_prerequisites
from inference.accountability import materialize_accountability_links
from inference.materialize import materialize_coverage
from reconcile.materialize import (
    materialize_contradictions,
    materialize_resolutions,
    materialize_sharing_edges,
)
from tasks.research_pg import materialize_research_queue

ROLE = "sig_materialize"
MATERIALIZED = (
    "resolution",
    "relationship",
    "contradiction",
    "coverage_record",
    "research_task",
    "inference.derived_fact",
    # P30.2b (ADR-105): the camera-site same_as decision log, its run record, and the
    # review-queue proposals the camera-site materializer enqueues.
    "camera_site_match",
    "camera_site_run",
    "review_item",
)
SPINE = ("claim", "claim_evidence", "evidence_artifact", "evidence_capture", "entity")


def _priv(conn: object, table: str, priv: str) -> bool:
    return bool(
        conn.execute("SELECT has_table_privilege(%s, %s, %s)", (ROLE, table, priv)).fetchone()[0]
    )


def test_role_exists_nologin_nobypassrls_not_superuser(conn: object) -> None:
    row = conn.execute(
        "SELECT rolcanlogin, rolbypassrls, rolsuper, rolcreaterole, rolcreatedb "
        "  FROM pg_roles WHERE rolname = %s",
        (ROLE,),
    ).fetchone()
    assert row is not None, "materialize_role did not create sig_materialize"
    assert row == (False, False, False, False, False)
    # READ is exactly the public read role (tier-0 ceiling).
    assert conn.execute("SELECT pg_has_role(%s, 'sig_read_public', 'USAGE')", (ROLE,)).fetchone()[0]
    assert not conn.execute(
        "SELECT pg_has_role(%s, 'sig_read_restricted', 'USAGE')", (ROLE,)
    ).fetchone()[0]


def test_the_deploying_login_can_set_role(conn: object) -> None:
    assert conn.execute("SELECT pg_has_role(current_user, %s, 'SET')", (ROLE,)).fetchone()[0]


@pytest.mark.parametrize("table", MATERIALIZED)
def test_insert_only_on_the_materialized_tables(conn: object, table: str) -> None:
    assert _priv(conn, table, "INSERT")
    assert _priv(conn, table, "SELECT")  # RETURNING + the idempotency/supersession reads
    for denied in ("UPDATE", "DELETE", "TRUNCATE"):
        assert not _priv(conn, table, denied), f"{ROLE} must not hold {denied} on {table}"


@pytest.mark.parametrize("table", SPINE)
def test_no_write_at_all_on_the_claim_spine(conn: object, table: str) -> None:
    assert _priv(conn, table, "SELECT")
    for denied in ("INSERT", "UPDATE", "DELETE", "TRUNCATE"):
        assert not _priv(conn, table, denied), f"{ROLE} must not hold {denied} on {table}"


def test_rls_tier_ceiling_binds_the_role(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    for tier in (0, 1, 2):
        insert_claim(conn, prereqs, sensitivity_tier=tier)
    conn.execute(f"SET ROLE {ROLE}")
    try:
        tiers = conn.execute(
            "SELECT DISTINCT sensitivity_tier FROM claim WHERE subject_id = %s",
            (prereqs["subject_id"],),
        ).fetchall()
    finally:
        conn.execute("RESET ROLE")
    assert [t[0] for t in tiers] == [0]


def test_update_and_spine_insert_are_refused_under_the_role(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    conn.execute(f"SET ROLE {ROLE}")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("UPDATE resolution SET rationale_text = 'x' WHERE false")
    conn.rollback()
    conn.execute(f"SET ROLE {ROLE}")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("INSERT INTO entity(entity_type) VALUES('deployment') RETURNING entity_id")
    conn.rollback()
    conn.execute(f"SET ROLE {ROLE}")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("DELETE FROM contradiction WHERE subject_id = %s", (prereqs["subject_id"],))
    conn.rollback()


def test_every_round6_materializer_and_the_detector_run_under_the_role(conn: object) -> None:
    """The hosted execution path: each step runs with ``role=sig_materialize`` and hits no
    InsufficientPrivilege (reads + INSERT ... ON CONFLICT DO NOTHING RETURNING)."""
    prereqs = seed_claim_prerequisites(conn)
    insert_claim(conn, prereqs, value_text="25", value_num=25)
    insert_claim(conn, prereqs, value_text="40", value_num=40)

    res = materialize_resolutions(conn, subject=str(prereqs["subject_id"]), role=ROLE)
    assert conn.execute("SELECT current_user").fetchone()[0] == ROLE
    edges = materialize_sharing_edges(conn, role=ROLE)
    con = materialize_contradictions(conn, subject=str(prereqs["subject_id"]), role=ROLE)
    cov = materialize_coverage(conn, role=ROLE, negative_space=True)
    acct = materialize_accountability_links(conn, role=ROLE)
    queue, _ = materialize_research_queue(conn, role=ROLE)

    # Each ran to completion under the role; the coverage metrics always write at least the
    # provenance-completeness row over a non-empty tier-0 spine.
    assert res.considered_pairs >= 1
    assert edges.inserted >= 0 and acct.inserted >= 0 and con.detected >= 0
    assert cov.inserted >= 1
    assert queue.records_requests_sent == 0
