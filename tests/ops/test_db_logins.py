# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.43 / SIG-CONF-013 (ADR-202) — the least-privilege DB login legs.

Offline layer: the ``LoginRole`` declarations pin the contract posture
(``sig_audit`` SELECT-only with a 60 s statement timeout + read-only session
default + connection cap; ``sig_recovery_login`` as a distinct LOGIN member
of L52's ``sig_recovery`` NOLOGIN group); ``resolve_role`` is a closed map;
``apply_role`` queues (exit 42) while a required group role is absent — the
``live:P34.46`` gate — and runs catalog-only statements otherwise; the shell
leg's ``--check`` is green with no ADC and no network. Refused-write probes
under ``SET ROLE`` live in ``tests/db/test_audit_login.py``.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from ops.db_logins import (
    QUEUED,
    ROLES,
    SIG_AUDIT,
    SIG_RECOVERY_LOGIN,
    apply_role,
    resolve_role,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_LOGINS_SH = REPO_ROOT / "ops" / "gcp" / "db-logins.sh"


class _FakeConn:
    """A catalog stub: ``SELECT rolname FROM pg_roles`` answers `existing`;
    everything else records the statement. No real DB is touched."""

    def __init__(self, existing: set[str]):
        self.existing = existing
        self.ran: list[str] = []

    def execute(self, sql, params=None):
        self.ran.append(str(sql))
        if "FROM pg_roles" in str(sql):
            roles = sorted(self.existing)

            class _Cur:
                def fetchall(self):
                    return [(r,) for r in roles]

            return _Cur()

        class _Cur:
            def fetchone(self):
                return None

        return _Cur()


def test_sig_audit_is_the_select_only_login() -> None:
    stmts = "\n".join(SIG_AUDIT.statements)
    assert "CREATE ROLE sig_audit LOGIN" in stmts
    for flag in ("NOBYPASSRLS", "NOSUPERUSER", "NOCREATEDB", "NOCREATEROLE"):
        assert flag in stmts
    assert "CONNECTION LIMIT 4" in stmts
    assert "GRANT sig_read_public TO sig_audit" in stmts
    assert "default_transaction_read_only = 'on'" in stmts
    assert "statement_timeout = '60s'" in stmts
    # Catalog-only: no statement names a table grant — table grants ride the
    # audit_login sqitch change inside P34.46's hosted deploy slot.
    assert not any(
        "GRANT SELECT ON" in s or " ON " in s.split("TO sig_audit")[0]
        for s in SIG_AUDIT.statements
        if s.startswith("GRANT")
    )
    assert SIG_AUDIT.secret_name == "sig-audit-password"
    assert SIG_AUDIT.consumer_sa == "sig-quality-probe-rt"
    assert SIG_AUDIT.password_env == "SIG_AUDIT_PASSWORD"
    # Every probe is a write that must be refused — never a tolerated read.
    for probe in SIG_AUDIT.write_refusal_probes:
        assert probe.lstrip().split()[0] in {"INSERT", "UPDATE", "DELETE", "CREATE", "DROP"}


def test_sig_recovery_login_is_a_member_of_the_group_never_the_group() -> None:
    """L52 creates ``sig_recovery`` as NOLOGIN; the credential is a DISTINCT
    LOGIN role holding membership — never a second role of the same name."""
    assert SIG_RECOVERY_LOGIN.name == "sig_recovery_login"
    assert SIG_RECOVERY_LOGIN.name != "sig_recovery"
    stmts = "\n".join(SIG_RECOVERY_LOGIN.statements)
    assert "CREATE ROLE sig_recovery_login LOGIN" in stmts
    assert "GRANT sig_recovery TO sig_recovery_login" in stmts
    assert "CREATE ROLE sig_recovery " not in stmts
    assert SIG_RECOVERY_LOGIN.requires_roles == ("sig_recovery",)
    assert SIG_RECOVERY_LOGIN.connection_limit == 2
    assert SIG_RECOVERY_LOGIN.select_tables == ()  # no read surface of its own
    assert SIG_RECOVERY_LOGIN.secret_name == "sig-recovery-password"


def test_resolve_role_is_a_closed_map() -> None:
    assert resolve_role("sig_audit") is SIG_AUDIT
    assert resolve_role("sig_recovery") is SIG_RECOVERY_LOGIN
    assert resolve_role("sig_recovery_login") is SIG_RECOVERY_LOGIN
    for bad in ("postgres", "sig_materialize", "sig_read_public", ""):
        with pytest.raises(ValueError):
            resolve_role(bad)


def test_apply_queues_when_the_group_role_is_absent() -> None:
    conn = _FakeConn(existing={"sig_read_public"})  # no sig_recovery yet
    rc = apply_role(conn, SIG_RECOVERY_LOGIN, dry_run=False)
    assert rc == QUEUED
    # Nothing ran against the catalog — queueing is not a partial apply.
    assert not any(s.startswith("CREATE ROLE") for s in conn.ran)


def test_apply_runs_catalog_only_statements_and_is_idempotent() -> None:
    conn = _FakeConn(existing={"sig_read_public", "pg_monitor"})
    rc = apply_role(conn, SIG_AUDIT, password=None, dry_run=False)
    assert rc == 0
    ran = [s for s in conn.ran if not s.startswith("SELECT")]
    assert any(s.startswith("CREATE ROLE sig_audit") for s in ran)
    # A second apply skips the CREATE — guarded idempotence.
    conn2 = _FakeConn(existing={"sig_read_public", "sig_audit"})
    rc2 = apply_role(conn2, SIG_AUDIT, dry_run=False)
    assert rc2 == 0
    assert not any(s.startswith("CREATE ROLE") for s in conn2.ran)
    assert any(s.startswith("GRANT sig_read_public") for s in conn2.ran)


def test_apply_never_puts_a_password_in_argv_or_a_statement_literal() -> None:
    conn = _FakeConn(existing={"sig_read_public"})
    apply_role(conn, SIG_AUDIT, password="s3cr3t-å", dry_run=True)
    joined = "\n".join(conn.ran)
    assert "s3cr3t" not in joined
    # dry_run: only the roles read ran.
    assert all("FROM pg_roles" in s for s in conn.ran)


def test_every_declared_role_has_a_secret_and_consumer() -> None:
    for spec in ROLES.values():
        assert spec.secret_name and spec.consumer_sa and spec.password_env
        assert spec.memberships  # least privilege rides a group, never bare grants


def test_db_logins_sh_check_is_green_without_adc() -> None:
    env = {k: v for k, v in os.environ.items() if k != "SIG_GCP_PROJECT"}
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    env["CLOUDSDK_CONFIG"] = "/nonexistent-sig-adc"
    proc = subprocess.run(
        ["bash", str(DB_LOGINS_SH), "--check"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "PLAN:" in proc.stdout and "check OK" in proc.stdout
    # The contract posture is rendered, a password never is.
    assert "statement_timeout" in proc.stdout
    assert "sig_recovery_login" not in proc.stdout or "QUEUED" not in proc.stdout
