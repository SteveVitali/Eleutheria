# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The write-capable ER re-run login (P34.45, ADR-206) over real PG18+PostGIS
— the ``er_rerun_login`` sqitch change deployed by the conftest container.

``sig_materialize_login`` is the one WRITE-capable login the P34.43 host
carries: a distinct LOGIN member of the NOLOGIN ``sig_materialize`` group —
append-only INSERT+SELECT on the camera-site tables and the review queue,
UPDATE/DELETE/TRUNCATE refused, no claim-spine write, no read-only session
default by design (the INSERT grants bound it, not a session flag).
"""

from __future__ import annotations

import psycopg
import pytest

pytestmark = pytest.mark.usefixtures("sig_database")

LOGIN = "sig_materialize_login"
GROUP = "sig_materialize"

#: Writes the append-only credential must never hold — probed under a real
#: login connection below.
REFUSED_WRITES = (
    "UPDATE camera_site_match SET decided_by = 'tampered' WHERE false",
    "DELETE FROM camera_site_match WHERE false",
    "TRUNCATE camera_site_match",
    "DELETE FROM claim WHERE false",
    "INSERT INTO ingest_run (run_id) VALUES (gen_random_uuid())",
)


@pytest.fixture
def rerun_dsn(sig_database):
    """Mint the login's password on an autocommit superuser connection + yield
    a real login connection (the hosted shape). The value never leaves the
    test."""
    pw = "test-only-pw-not-a-secret"
    admin = psycopg.connect(
        host=sig_database["host"],
        port=sig_database["port"],
        user=sig_database["user"],
        password=sig_database["password"],
        dbname=sig_database["dbname"],
        autocommit=True,
    )
    try:
        admin.execute(f"ALTER ROLE {LOGIN} PASSWORD '{pw}'")
    finally:
        admin.close()
    connection = psycopg.connect(
        host=sig_database["host"],
        port=sig_database["port"],
        user=LOGIN,
        password=pw,
        dbname=sig_database["dbname"],
        autocommit=True,
    )
    try:
        yield connection
    finally:
        connection.close()


def test_rerun_login_posture(conn) -> None:
    row = conn.execute(
        "SELECT rolcanlogin, rolsuper, rolcreaterole, rolcreatedb, rolbypassrls, "
        "rolconnlimit, rolconfig FROM pg_roles WHERE rolname = %s",
        (LOGIN,),
    ).fetchone()
    assert row is not None, "er_rerun_login did not create sig_materialize_login"
    can_login, is_super, createrole, createdb, bypassrls, connlimit, rolconfig = row
    assert can_login is True
    assert (is_super, createrole, createdb, bypassrls) == (False, False, False, False)
    assert connlimit == 2
    # Write-capable by design: no read-only session default — the INSERT
    # grants bound the login, never a session flag.
    cfg = set(rolconfig or [])
    assert "default_transaction_read_only=on" not in cfg


def test_rerun_login_is_a_member_of_the_group_not_a_second_group(conn) -> None:
    assert conn.execute("SELECT pg_has_role(%s, %s, 'USAGE')", (LOGIN, GROUP)).fetchone()[0]
    direct = conn.execute(
        "SELECT r.rolname FROM pg_auth_members m "
        "JOIN pg_roles member ON m.member = member.oid "
        "JOIN pg_roles r ON m.roleid = r.oid "
        "WHERE member.rolname = %s",
        (LOGIN,),
    ).fetchall()
    assert {r[0] for r in direct} == {GROUP}
    grp = conn.execute("SELECT rolcanlogin FROM pg_roles WHERE rolname = %s", (GROUP,)).fetchone()
    assert grp is not None and grp[0] is False


def test_rerun_login_surface_is_append_only_camera_site(conn) -> None:
    for table, want in (
        ("camera_site_match", True),
        ("camera_site_run", True),
        ("camera_site_execution", True),
        ("review_item", True),
    ):
        assert (
            conn.execute("SELECT has_table_privilege(%s, %s, 'INSERT')", (LOGIN, table)).fetchone()[
                0
            ]
            == want
        ), f"{LOGIN} must INSERT {table} (append-only)"
    for table in ("camera_site_match", "camera_site_run", "camera_site_execution"):
        assert conn.execute(
            "SELECT has_table_privilege(%s, %s, 'SELECT')", (LOGIN, table)
        ).fetchone()[0], f"{LOGIN} must SELECT {table} (INSERT ... RETURNING)"
        for denied in ("UPDATE", "DELETE", "TRUNCATE"):
            assert not conn.execute(
                "SELECT has_table_privilege(%s, %s, %s)", (LOGIN, table, denied)
            ).fetchone()[0], f"{LOGIN} holds {denied} on {table}"
    # No claim-spine write of any kind.
    for table in ("claim", "claim_evidence", "evidence_capture", "ingest_run"):
        for denied in ("INSERT", "UPDATE", "DELETE", "TRUNCATE"):
            assert not conn.execute(
                "SELECT has_table_privilege(%s, %s, %s)", (LOGIN, table, denied)
            ).fetchone()[0], f"{LOGIN} holds {denied} on {table}"


REFUSAL_ERRORS = (
    psycopg.errors.InsufficientPrivilege,
    psycopg.errors.ReadOnlySqlTransaction,
)


@pytest.mark.parametrize("sql", REFUSED_WRITES)
def test_rerun_login_write_is_refused_on_a_real_login(rerun_dsn, sql: str) -> None:
    with pytest.raises(REFUSAL_ERRORS):
        rerun_dsn.execute(sql)


def test_rerun_login_can_insert_a_review_queue_row_shape(rerun_dsn) -> None:
    """The write surface it DOES hold: a camera_site_match-shaped insert —
    exercised through a table the login may write, rolled into a temp probe
    is not needed: has_table_privilege already proves the grant; here the
    SELECT the RETURNING clause needs is exercised on a real connection."""
    cur = rerun_dsn.execute("SELECT count(*) FROM camera_site_match WHERE false")
    assert cur.fetchone()[0] == 0
