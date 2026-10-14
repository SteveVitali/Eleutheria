# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The least-privilege DB logins (P34.43, SIG-CONF-013, ADR-202) over real
PG18+PostGIS — the ``audit_login`` sqitch change deployed by the conftest
container.

``sig_audit`` is the L1 SELECT-only audit/quality login: LOGIN, no
superuser/createrole/createdb/bypass-RLS attributes, ``CONNECTION LIMIT 4``,
``default_transaction_read_only = on`` + ``statement_timeout = '60s'`` as
session defaults, SELECT through ``sig_read_public`` plus the two NEW-16
capture-store tables — and every write refused. ``sig_recovery_login`` is
the L2 credential: a distinct LOGIN role whose only power is membership in
L52's ``sig_recovery`` NOLOGIN group (a role of that name can never be a
second LOGIN — the group's grants are the bounded-apply surface, P35.61).

The tests connect AS ``sig_audit`` (a real login — the hosted shape), never
merely ``SET ROLE``, so the session defaults and the timeout are the ones the
execution host's connections get.
"""

from __future__ import annotations

import psycopg
import pytest

pytestmark = pytest.mark.usefixtures("sig_database")

AUDIT = "sig_audit"
RECOVERY_LOGIN = "sig_recovery_login"

# The spine surfaces the audit login must never write — probed under
# `SET ROLE` and under a real `sig_audit` connection.
REFUSED_WRITES = (
    "UPDATE claim SET claim_id = claim_id WHERE false",
    "DELETE FROM claim WHERE false",
    "INSERT INTO claim_evidence DEFAULT VALUES",
    "INSERT INTO publication_disposition DEFAULT VALUES",
    "INSERT INTO recovery_application DEFAULT VALUES",
)


@pytest.fixture
def audit_dsn(sig_database):
    """Mint sig_audit's password on an autocommit superuser connection (the
    password must COMMIT — the conn fixture rolls back) + yield a real login
    connection (the hosted shape). The value never leaves this test."""
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
        admin.execute(f"ALTER ROLE {AUDIT} PASSWORD '{pw}'")
    finally:
        admin.close()
    connection = psycopg.connect(
        host=sig_database["host"],
        port=sig_database["port"],
        user=AUDIT,
        password=pw,
        dbname=sig_database["dbname"],
        autocommit=True,
    )
    try:
        yield connection
    finally:
        connection.close()


def test_audit_login_posture(conn) -> None:
    row = conn.execute(
        "SELECT rolcanlogin, rolsuper, rolcreaterole, rolcreatedb, rolbypassrls, "
        "rolconnlimit, rolconfig FROM pg_roles WHERE rolname = %s",
        (AUDIT,),
    ).fetchone()
    assert row is not None, "audit_login did not create sig_audit"
    can_login, is_super, createrole, createdb, bypassrls, connlimit, rolconfig = row
    assert can_login is True
    assert (is_super, createrole, createdb, bypassrls) == (False, False, False, False)
    assert connlimit == 4
    cfg = set(rolconfig or [])
    assert "default_transaction_read_only=on" in cfg
    assert "statement_timeout=60s" in cfg


def test_audit_read_surface_is_exactly_the_read_role_plus_new16(conn) -> None:
    assert conn.execute("SELECT pg_has_role(%s, 'sig_read_public', 'USAGE')", (AUDIT,)).fetchone()[
        0
    ]
    for table in ("ingest_run_capture", "entity_identity_key"):
        assert conn.execute(
            "SELECT has_table_privilege(%s, %s, 'SELECT')", (AUDIT, table)
        ).fetchone()[0], f"sig_audit must SELECT {table}"
        for denied in ("INSERT", "UPDATE", "DELETE", "TRUNCATE"):
            assert not conn.execute(
                "SELECT has_table_privilege(%s, %s, %s)", (AUDIT, table, denied)
            ).fetchone()[0]
    # No write anywhere on the claim spine, via privilege or membership.
    for table in ("claim", "claim_evidence", "evidence_capture"):
        for denied in ("INSERT", "UPDATE", "DELETE", "TRUNCATE"):
            assert not conn.execute(
                "SELECT has_table_privilege(%s, %s, %s)", (AUDIT, table, denied)
            ).fetchone()[0], f"sig_audit holds {denied} on {table}"
    for role in ("sig_recovery", "sig_materialize", "sig_intake_bridge"):
        assert not conn.execute("SELECT pg_has_role(%s, %s, 'USAGE')", (AUDIT, role)).fetchone()[
            0
        ], f"sig_audit is a member of write role {role}"


def test_audit_session_is_read_only_and_timed(audit_dsn) -> None:
    cur = audit_dsn.execute("SHOW transaction_read_only")
    assert cur.fetchone()[0] == "on"
    cur = audit_dsn.execute("SHOW statement_timeout")
    assert cur.fetchone()[0] in {"1min", "60s", "60000"}


def test_audit_statement_timeout_is_enforced(audit_dsn) -> None:
    """The role-level default applies; a tightened per-session bound aborts a
    runaway statement (the enforcement mechanism the 60 s default rides)."""
    audit_dsn.execute("SET statement_timeout = '50ms'")
    with pytest.raises(psycopg.errors.QueryCanceled):
        audit_dsn.execute("SELECT pg_sleep(5)")


# A refused write raises the read-only-transaction error or the privilege
# error — whichever wall the planner hits first; either proves the refusal.
REFUSAL_ERRORS = (
    psycopg.errors.InsufficientPrivilege,
    psycopg.errors.ReadOnlySqlTransaction,
)


@pytest.mark.parametrize("sql", REFUSED_WRITES)
def test_audit_write_is_refused_on_a_real_login(audit_dsn, sql: str) -> None:
    with pytest.raises(REFUSAL_ERRORS):
        audit_dsn.execute(sql)


def test_audit_cannot_create_objects(audit_dsn) -> None:
    with pytest.raises(REFUSAL_ERRORS):
        audit_dsn.execute("CREATE TABLE sig_audit_probe (i int)")


def test_recovery_login_is_a_member_of_the_group_not_a_second_group(conn) -> None:
    row = conn.execute(
        "SELECT rolcanlogin, rolsuper, rolcreaterole, rolcreatedb, rolbypassrls, "
        "rolconnlimit FROM pg_roles WHERE rolname = %s",
        (RECOVERY_LOGIN,),
    ).fetchone()
    assert row is not None, "audit_login did not create sig_recovery_login"
    can_login, is_super, createrole, createdb, bypassrls, connlimit = row
    assert can_login is True
    assert (is_super, createrole, createdb, bypassrls) == (False, False, False, False)
    assert connlimit == 2
    # Membership in L52's group role is the credential's ONLY direct grant —
    # the read surface it reaches transitively is the group's own L52 scope
    # (sig_recovery's sealed-read membership), never duplicated on the login.
    assert conn.execute(
        "SELECT pg_has_role(%s, 'sig_recovery', 'USAGE')", (RECOVERY_LOGIN,)
    ).fetchone()[0]
    direct = conn.execute(
        "SELECT r.rolname FROM pg_auth_members m "
        "JOIN pg_roles member ON m.member = member.oid "
        "JOIN pg_roles r ON m.roleid = r.oid "
        "WHERE member.rolname = %s",
        (RECOVERY_LOGIN,),
    ).fetchall()
    assert {r[0] for r in direct} == {"sig_recovery"}
    # The group stays NOLOGIN — the credential is a member, never the group.
    grp = conn.execute("SELECT rolcanlogin FROM pg_roles WHERE rolname = 'sig_recovery'").fetchone()
    assert grp is not None and grp[0] is False


def test_recovery_login_holds_no_direct_spine_write(conn) -> None:
    """Its apply surface is entirely the group's — nothing duplicated on the
    login itself (the catalog grants no direct privilege)."""
    # The login's effective privileges all route through sig_recovery; a
    # spine DELETE is refused through the group too (sig_recovery's grants
    # are INSERT/UPDATE(sys_period)-only). The conftest user is a superuser —
    # SET ROLE works without a membership grant.
    conn.execute(f"SET ROLE {RECOVERY_LOGIN}")
    try:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("DELETE FROM claim WHERE false")
    finally:
        conn.rollback()
