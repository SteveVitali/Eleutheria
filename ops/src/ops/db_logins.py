# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""db_logins — the P34.43 least-privilege database logins (SIG-CONF-013, L3
CP-0, G2 ACT-13).

Two LOGIN roles, provisioned by the windowed leg in ``ops/gcp/db-logins.sh``:

* ``sig_audit`` (L1) — the SELECT-only audit/quality login: member of
  ``sig_read_public`` (the §37 surface, RLS tier-0 ceiling binds),
  ``default_transaction_read_only = on``, ``statement_timeout = 60s`` (the
  L2-documented value), ``CONNECTION LIMIT 4``. Its credential is a Secret
  Manager password (HG-09; ADR-202) whose only accessor is the execution
  host's runtime SA — never a file, never an argv.
  The NEW-16 table grants (``ingest_run_capture``, ``entity_identity_key``)
  ride the ``audit_login`` sqitch change — they reach hosted only inside
  P34.46's deploy slot, so until then they verify as ``not_evaluable``.
* ``sig_recovery_login`` (L2, ``live:P34.46``) — the login granted membership
  in the ``sig_recovery`` group role L52 creates (P34.46 deploys it); the
  apply refuses (exit 42) while the group role is absent — the dependency is
  enforced, not just recorded. For P35.61's bounded apply; the same
  credential shape, CONNECTION LIMIT 2.

Every statement the apply runs is catalog-only (role rows and memberships —
never a table grant, never a table lock; ``lock_timeout`` is set on the
session first). The exact same statements live in ``db/deploy/audit_login.sql``
so the sqitch deploy converges any database the leg ran early on (the deploy
adds the two NEW-16 table grants this leg deliberately omits).
``tests/ops/test_db_logins.py`` pins the two surfaces to identical text.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

#: Exit 42 — the queued/dependency-gated code the leg scripts share.
QUEUED = 42


@dataclass(frozen=True)
class LoginRole:
    """One least-privilege login and its catalog-only provisioning."""

    name: str
    statements: tuple[str, ...]
    secret_name: str
    consumer_sa: str
    password_env: str
    requires_roles: tuple[str, ...] = ()  # absent → the apply queues (exit 42)
    connection_limit: int = 4
    memberships: tuple[str, ...] = ()
    select_tables: tuple[str, ...] = ()
    # Tables whose grants ride the audit_login sqitch change's hosted deploy
    # (P34.46's slot): absent until then — verified as not_evaluable, not fail.
    pending_deploy_tables: tuple[str, ...] = ()
    write_refusal_probes: tuple[str, ...] = ()
    rolconfig: tuple[str, ...] = ()


SIG_AUDIT = LoginRole(
    name="sig_audit",
    statements=(
        "CREATE ROLE sig_audit LOGIN NOBYPASSRLS NOSUPERUSER NOCREATEDB "
        "NOCREATEROLE CONNECTION LIMIT 4",
        "GRANT sig_read_public TO sig_audit",
        "ALTER ROLE sig_audit SET default_transaction_read_only = 'on'",
        "ALTER ROLE sig_audit SET statement_timeout = '60s'",
    ),
    secret_name="sig-audit-password",
    consumer_sa="sig-quality-probe-rt",
    password_env="SIG_AUDIT_PASSWORD",
    requires_roles=("sig_read_public",),
    connection_limit=4,
    memberships=("sig_read_public",),
    # The §37 surface the membership yields (asserted, not enumerated).
    select_tables=("claim", "claim_evidence", "entity", "evidence_capture"),
    pending_deploy_tables=("ingest_run_capture", "entity_identity_key"),
    write_refusal_probes=(
        "INSERT INTO ingest_run_capture DEFAULT VALUES",
        "INSERT INTO entity_identity_key DEFAULT VALUES",
        "UPDATE claim SET claim_id = claim_id WHERE false",
        "DELETE FROM claim WHERE false",
        "CREATE TABLE sig_audit_probe (i int)",
    ),
    rolconfig=("default_transaction_read_only=on", "statement_timeout=60s"),
)

SIG_RECOVERY_LOGIN = LoginRole(
    name="sig_recovery_login",
    statements=(
        "CREATE ROLE sig_recovery_login LOGIN NOBYPASSRLS NOSUPERUSER "
        "NOCREATEDB NOCREATEROLE CONNECTION LIMIT 2",
        "GRANT sig_recovery TO sig_recovery_login",
    ),
    secret_name="sig-recovery-password",
    consumer_sa="sig-quality-probe-rt",
    password_env="SIG_RECOVERY_PASSWORD",
    # The live:P34.46 gate, enforced: the group role exists on hosted only
    # after P34.46's L52 (recovery_apply) deploy lands it.
    requires_roles=("sig_recovery",),
    connection_limit=2,
    memberships=("sig_recovery",),
    # The bounded apply surface is asserted through membership only — this
    # ticket runs no write under the recovery login (P35.61 owns the apply).
    select_tables=(),
    pending_deploy_tables=(),
    write_refusal_probes=(
        "DELETE FROM claim WHERE false",
        "DROP TABLE claim",
    ),
    rolconfig=(),
)

SIG_MATERIALIZE_LOGIN = LoginRole(
    name="sig_materialize_login",
    statements=(
        "CREATE ROLE sig_materialize_login LOGIN NOBYPASSRLS NOSUPERUSER "
        "NOCREATEDB NOCREATEROLE CONNECTION LIMIT 2",
        "GRANT sig_materialize TO sig_materialize_login",
    ),
    secret_name="sig-er-rerun-password",
    consumer_sa="sig-quality-probe-rt",
    password_env="SIG_ER_RERUN_PASSWORD",
    # The group is Round-6's (P30.2-era) — long deployed on hosted, so on the
    # live spine the gate holds trivially; on a cold spine the apply queues
    # (exit 42) rather than mint a credential that cannot write anyway.
    requires_roles=("sig_materialize",),
    connection_limit=2,
    memberships=("sig_materialize",),
    # The append-only camera-site surface + the reads the resolver needs
    # (INSERT ... RETURNING requires SELECT; the queue rows too).
    select_tables=(
        "camera_site_match",
        "camera_site_run",
        "camera_site_execution",
        "review_item",
        "review_decision",
    ),
    # Every grant it needs was deployed by Round-6 + P32.4 — nothing pending.
    pending_deploy_tables=(),
    write_refusal_probes=(
        "UPDATE camera_site_match SET decided_by = 'tampered' WHERE false",
        "DELETE FROM camera_site_match WHERE false",
        "TRUNCATE camera_site_match",
        "DELETE FROM claim WHERE false",
        "INSERT INTO ingest_run (run_id) VALUES (gen_random_uuid())",
    ),
    # Write-capable by design (the one pre-authorised append-only mutation) —
    # deliberately no default_transaction_read_only: the INSERT grants bound
    # it, not a session flag.
    rolconfig=(),
)

ROLES: dict[str, LoginRole] = {
    SIG_AUDIT.name: SIG_AUDIT,
    SIG_RECOVERY_LOGIN.name: SIG_RECOVERY_LOGIN,
    SIG_MATERIALIZE_LOGIN.name: SIG_MATERIALIZE_LOGIN,
}
#: The names the leg script/declarations accept on `--role`.
ROLE_ALIASES: dict[str, str] = {
    "sig_audit": "sig_audit",
    "sig_recovery": "sig_recovery_login",
    "sig_recovery_login": "sig_recovery_login",
    "sig_materialize_login": "sig_materialize_login",
    "sig_er_rerun": "sig_materialize_login",
}


def resolve_role(name: str) -> LoginRole:
    try:
        return ROLES[ROLE_ALIASES[name]]
    except KeyError:
        raise ValueError(
            f"unknown role {name!r} — the declaration admits {sorted(ROLE_ALIASES)} only"
        ) from None


def _connect(dsn: str) -> Any:
    import psycopg

    return psycopg.connect(dsn, connect_timeout=10, autocommit=True)


def _existing_roles(conn: Any) -> set[str]:
    cur = conn.execute("SELECT rolname FROM pg_roles")
    return {str(r[0]) for r in cur.fetchall()}


def missing_prereq_roles(conn: Any, spec: LoginRole) -> list[str]:
    """The group roles the login joins that must already exist (the L2 gate)."""
    have = _existing_roles(conn)
    return [r for r in spec.requires_roles if r not in have]


def apply_role(
    conn: Any,
    spec: LoginRole,
    *,
    password: str | None = None,
    dry_run: bool = True,
    log: Callable[[str], None] = lambda line: None,
) -> int:
    """Run the catalog-only statements. Idempotent (the CREATE is guarded).
    Returns 0 applied / 42 queued on a missing required role."""
    missing = missing_prereq_roles(conn, spec)
    if missing:
        log(
            f"QUEUED: required role(s) {missing} absent on this database — "
            "the dependency deploy has not run"
        )
        return QUEUED
    exists = spec.name in _existing_roles(conn)
    if exists:
        log(
            f"role {spec.name} already exists — apply is idempotent "
            "(memberships + settings re-asserted)"
        )
    for stmt in spec.statements:
        if exists and stmt.startswith(f"CREATE ROLE {spec.name} "):
            # The guarded CREATE (db/deploy/audit_login.sql uses
            # `IF NOT EXISTS`) — re-running never re-asserts creation.
            log(f"  {stmt}   [skipped — role exists]")
            continue
        log(f"  {stmt}")
        if not dry_run:
            conn.execute("BEGIN")
            conn.execute("SET LOCAL lock_timeout = '5s'")
            conn.execute(stmt)
            conn.execute("COMMIT")
    if password is not None:
        from psycopg import sql

        log(f"  ALTER ROLE {spec.name} PASSWORD <from env — never printed>")
        if not dry_run:
            conn.execute("BEGIN")
            conn.execute(
                sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                    sql.Identifier(spec.name), sql.Literal(password)
                )
            )
            conn.execute("COMMIT")
    return 0


def verify_role(conn: Any, spec: LoginRole) -> dict[str, Any]:
    """Catalog assertions + privilege read-back. Every check reports honestly:
    absent pending-deploy grants are ``not_evaluable``, never ``fail``."""
    checks: dict[str, Any] = {}
    cur = conn.execute(
        "SELECT rolcanlogin, rolsuper, rolcreaterole, rolcreatedb, rolbypassrls, "
        "rolconnlimit, rolconfig FROM pg_roles WHERE rolname = %s",
        (spec.name,),
    )
    row = cur.fetchone()
    if row is None:
        return {
            "verdict": "not_evaluable",
            "reason": f"role {spec.name} does not exist on this database",
        }
    can_login, is_super, can_createrole, can_createdb, bypassrls, connlimit, rolconfig = row
    checks["posture"] = {
        "verdict": "pass"
        if (
            can_login and not is_super and not can_createrole and not can_createdb and not bypassrls
        )
        else "fail",
        "rolcanlogin": can_login,
        "rolsuper": is_super,
        "rolcreaterole": can_createrole,
        "rolcreatedb": can_createdb,
        "rolbypassrls": bypassrls,
    }
    checks["connection_limit"] = {
        "verdict": "pass" if connlimit == spec.connection_limit else "fail",
        "expected": spec.connection_limit,
        "actual": connlimit,
    }
    config = set(rolconfig or [])
    missing_cfg = [c for c in spec.rolconfig if c not in config]
    checks["session_defaults"] = {
        "verdict": "pass" if not missing_cfg else "fail",
        "rolconfig": sorted(config),
        "missing": missing_cfg,
    }
    memberships = {}
    for m in spec.memberships:
        cur = conn.execute("SELECT pg_has_role(%s, %s, 'USAGE')", (spec.name, m))
        memberships[m] = bool(cur.fetchone()[0])
    checks["memberships"] = {
        "verdict": "pass" if all(memberships.values()) else "fail",
        "roles": memberships,
    }
    selects = {}
    for t in spec.select_tables:
        cur = conn.execute("SELECT has_table_privilege(%s, %s, 'SELECT')", (spec.name, t))
        selects[t] = bool(cur.fetchone()[0])
    checks["read_surface"] = {
        "verdict": "pass" if all(selects.values()) else "fail",
        "tables": selects,
    }
    pending = {}
    for t in spec.pending_deploy_tables:
        cur = conn.execute("SELECT has_table_privilege(%s, %s, 'SELECT')", (spec.name, t))
        pending[t] = bool(cur.fetchone()[0])
    if pending:
        checks["new16_tables"] = {
            "verdict": "pass" if all(pending.values()) else "not_evaluable",
            "tables": pending,
            "state": "grants ride the audit_login sqitch change — hosted only "
            "inside P34.46's deploy slot",
        }
    refused = []
    for probe in spec.write_refusal_probes:
        verdict = None
        try:
            conn.execute("BEGIN")
            conn.execute(f"SET LOCAL ROLE {spec.name}")
            conn.execute(probe)
            verdict = "fail"  # the write went through — must never happen
            conn.execute("ROLLBACK")
        except Exception:  # noqa: BLE001 - a refusal is the PASS signal
            verdict = "pass"
            conn.execute("ROLLBACK")
        refused.append({"sql": probe, "verdict": verdict})
    checks["write_refusals"] = {
        "verdict": "fail" if any(p["verdict"] == "fail" for p in refused) else "pass",
        "probes": refused,
    }
    verdicts = [c["verdict"] for c in checks.values()]
    overall = (
        "fail"
        if "fail" in verdicts
        else ("not_evaluable" if "not_evaluable" in verdicts else "pass")
    )
    return {"role": spec.name, "overall": overall, "checks": checks}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sig-ops db-login",
        description=(
            "P34.43 (SIG-CONF-013): the least-privilege DB logins — sig_audit "
            "(L1) and sig_recovery_login (L2, gated on live:P34.46). Catalog-"
            "only apply; the windowed leg is ops/gcp/db-logins.sh."
        ),
    )
    parser.add_argument("--role", required=True, help="sig_audit|sig_recovery")
    sub = parser.add_subparsers(dest="db_command", required=True)
    sub.add_parser("plan", help="print the catalog statements + credential plan (offline)")
    p_apply = sub.add_parser(
        "apply",
        help="run the catalog statements over --dsn/$SIG_DB_LOGIN_DSN "
        "(needs the owner conn; exit 42 while a required role is absent)",
    )
    p_apply.add_argument(
        "--dsn",
        default=None,
        help="the owner DSN — prefer $SIG_DB_LOGIN_DSN (env-only, never argv)",
    )
    p_apply.add_argument(
        "--check",
        action="store_true",
        help="print-only dry run (no statement executes)",
    )
    p_verify = sub.add_parser(
        "verify", help="catalog + privilege assertions over --dsn (read-only)"
    )
    p_verify.add_argument(
        "--dsn",
        default=None,
        help="the owner DSN — prefer $SIG_DB_LOGIN_DSN (env-only, never argv)",
    )

    args = parser.parse_args(argv)
    try:
        spec = resolve_role(args.role)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    if args.db_command == "plan":
        doc = {
            "role": spec.name,
            "statements": list(spec.statements),
            "credential": {
                "secret": spec.secret_name,
                "accessor": spec.consumer_sa,
                "password_env": spec.password_env,
                "store": "Secret Manager only — never a file or argv (HG-09, ADR-202)",
            },
            "requires_roles": list(spec.requires_roles),
            "connection_limit": spec.connection_limit,
            "pending_deploy_tables": list(spec.pending_deploy_tables),
        }
        print(json.dumps(doc, indent=2, sort_keys=True))
        return 0

    dsn = args.dsn or os.environ.get("SIG_DB_LOGIN_DSN", "")
    if not dsn:
        print(
            "db-login: no DSN — pass --dsn or set SIG_DB_LOGIN_DSN "
            "(env-only keeps the password off argv)",
            file=sys.stderr,
        )
        return 3
    try:
        conn = _connect(dsn)
    except Exception as exc:  # noqa: BLE001
        print(f"db-login: connect failed: {exc}", file=sys.stderr)
        return 3
    try:
        if args.db_command == "apply":
            password = os.environ.get(spec.password_env) or None
            if password is None:
                print(
                    f"note: ${spec.password_env} unset — the role is applied "
                    "without a password (set the credential separately)",
                    file=sys.stderr,
                )
            return apply_role(
                conn,
                spec,
                password=password,
                dry_run=args.check,
                log=lambda line: print(f"{line}"),
            )
        if args.db_command == "verify":
            report = verify_role(conn, spec)
            print(json.dumps(report, indent=2, sort_keys=True))
            return {"pass": 0, "not_evaluable": 0}.get(report["overall"], 4)
        return 2
    finally:
        conn.close()
