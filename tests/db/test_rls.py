# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Row-level security by sensitivity tier (§16.8, §44.4; SIG-STORE-023/024, ADR-012).

AC5: for every role and every tier, RLS shows the permitted rows and hides the
forbidden ones. The public API role holds no BYPASSRLS; an export role running
with row_security=off fails loudly rather than silently returning a subset.
"""

from __future__ import annotations

import psycopg
import pytest
from conftest import insert_claim, seed_claim_prerequisites


def _seed_three_tiers(conn: object) -> dict[str, object]:
    prereqs = seed_claim_prerequisites(conn)
    for tier in (0, 1, 2):
        insert_claim(conn, prereqs, sensitivity_tier=tier)
    return prereqs


def _as_role(conn: object, role: str, sql: str) -> object:
    conn.execute(f"SET ROLE {role}")
    try:
        return conn.execute(sql).fetchone()
    finally:
        conn.execute("RESET ROLE")


@pytest.mark.parametrize(
    ("role", "max_visible_tier", "expected_rows"),
    [
        ("sig_read_public", 0, 1),
        ("sig_read_restricted", 1, 2),
        ("sig_read_sealed", 2, 3),
    ],
)
def test_tier_visibility_per_role(
    conn: object, role: str, max_visible_tier: int, expected_rows: int
) -> None:
    _seed_three_tiers(conn)
    # Visibility: the role sees exactly the tiers up to its ceiling.
    total = _as_role(conn, role, "SELECT count(*) FROM claim")[0]
    assert total == expected_rows
    highest = _as_role(conn, role, "SELECT max(sensitivity_tier) FROM claim")[0]
    assert highest == max_visible_tier
    # Non-visibility: no row above the ceiling is ever returned.
    above = _as_role(
        conn,
        role,
        f"SELECT count(*) FROM claim WHERE sensitivity_tier > {max_visible_tier}",
    )[0]
    assert above == 0


def test_public_role_holds_no_bypassrls(conn: object) -> None:
    row = conn.execute(
        "SELECT rolbypassrls, rolsuper FROM pg_roles WHERE rolname='sig_read_public'"
    ).fetchone()
    assert row == (False, False)


def test_claim_has_rls_enabled_and_forced(conn: object) -> None:
    row = conn.execute(
        "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname='claim'"
    ).fetchone()
    assert row == (True, True)


def test_export_role_fails_loudly_with_row_security_off(conn: object) -> None:
    """SIG-STORE-023: an export role (no BYPASSRLS) running with row_security=off
    must ERROR rather than silently return a filtered subset."""
    _seed_three_tiers(conn)
    with pytest.raises(psycopg.Error) as excinfo:
        with conn.transaction():
            conn.execute("SET LOCAL row_security = off")
            conn.execute("SET LOCAL ROLE sig_export")
            conn.execute("SELECT count(*) FROM claim").fetchone()
    assert "row" in str(excinfo.value).lower() and "security" in str(excinfo.value).lower()


def test_evidence_tables_also_enforce_tiers(conn: object) -> None:
    """The storage-tier ladder on evidence_capture is enforced identically."""
    row = conn.execute(
        "SELECT relrowsecurity FROM pg_class WHERE relname='evidence_capture'"
    ).fetchone()
    assert row == (True,)
