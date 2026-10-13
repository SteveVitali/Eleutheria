# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.25 (S0 RI-02): ``sig_read_public`` reads ONLY the published §37 surface.

Until this change, ``read_surface_grants`` (P24.1) gave the public read role
``SELECT ON ALL TABLES`` in ``public`` + ``inference`` — so "public" could read
``person``, every domain projection (``contract``, ``legal_proceeding``,
``records_request``…), the resolution/relationship internals, ``extraction``,
``ingest_run*``, the review queue, the camera-site machinery, every vocab
registry, ``append_only_guard``, the byte store (``evidence_blob``,
``evidence_access_log``) and both ``inference`` tables. None of those reach the
public API. ``public_read_allowlist`` revokes the blanket and re-grants exactly
``PgReadStore``'s read set; these tests prove the boundary on the complete
sqitch-deployed schema — the allowed set is exact (not merely a spot-check),
the forbidden set fails a real ``SET ROLE`` SELECT, and the column-limited
disposition tombstone keeps its shape.
"""

from __future__ import annotations

import psycopg
import pytest

ROLE = "sig_read_public"

#: The exact §37 read surface PgReadStore queries (P34.25). Table-level SELECT
#: on this set and NOTHING else — publication_disposition is separate because
#: its grant is column-limited, never table-level.
ALLOWED_TABLES: frozenset[str] = frozenset(
    {
        "claim",
        "claim_evidence",
        "claim_qualifier",
        "entity",
        "entity_identifier",
        "organization",
        "evidence_artifact",
        "evidence_capture",
        "source_registry",
        "rights_record",
        "rights_decision",
        "contradiction",
        "coverage_record",
        "research_task",
        "spine_watermark",
    }
)

#: Spot-checks across every category the blanket wrongly opened — domain
#: projections, graph internals, operational/ingest state, the byte store,
#: review + camera-site machinery, vocab registries, internal guards and the
#: whole inference schema. A real SELECT under the role must be REFUSED.
FORBIDDEN_SAMPLES: tuple[str, ...] = (
    "person",  # Part VIII — never public
    "jurisdiction",
    "deployment",
    "contract",
    "legal_proceeding",
    "records_request",
    "organization_relation",
    "entity_role",
    "resolution",
    "relationship",
    "extraction",
    "ingest_run",
    "ingest_run_completion",
    "ingest_run_capture",
    "entity_identity_key",
    "evidence_blob",  # the bytes themselves — never a public table read
    "evidence_access_log",
    "review_item",
    "review_decision",
    "review_campaign",
    "review_campaign_item",
    "camera_site_run",
    "camera_site_match",
    "camera_site_execution",
    "vocab_predicate",
    "vocab_evidence_role",
    "directness_matrix",
    "append_only_guard",
    "assertion_quarantine",
    "recovery_application",
    "human_eval_sample",
    "inference.derived_fact",
    "inference.derived_geometry",
)


def _all_read_surface_relations(conn: object) -> list[str]:
    rows = conn.execute(
        "SELECT n.nspname, c.relname FROM pg_class c"
        "  JOIN pg_namespace n ON n.oid = c.relnamespace"
        " WHERE n.nspname IN ('public', 'inference')"
        "   AND c.relkind IN ('r', 'v', 'm', 'p', 'f')"
        " ORDER BY 1, 2"
    ).fetchall()
    return [f"{s}.{t}" if s != "public" else t for s, t in rows]


def _has_select(conn: object, relation: str) -> bool:
    return bool(
        conn.execute("SELECT has_table_privilege(%s, %s, 'SELECT')", (ROLE, relation)).fetchone()[0]
    )


def test_the_granted_set_is_exactly_the_published_surface(conn: object) -> None:
    """The allow-list is EXACT — every relation public can SELECT is named,
    and every other public/inference relation is denied."""
    relations = _all_read_surface_relations(conn)
    assert "publication_disposition" in relations  # schema sanity: it exists
    granted = {r for r in relations if _has_select(conn, r)}
    # publication_disposition's grant is column-limited: whether or not
    # has_table_privilege counts a partial column grant, it must not appear as
    # a TABLE-level grant — check relacl directly.
    table_level = {
        r[0] if r[1] == "public" else f"{r[1]}.{r[0]}"
        for r in conn.execute(
            "SELECT c.relname, n.nspname FROM pg_class c"
            "  JOIN pg_namespace n ON n.oid = c.relnamespace"
            "  JOIN aclexplode(c.relacl) a ON true"
            "  JOIN pg_roles g ON g.oid = a.grantee"
            " WHERE n.nspname IN ('public', 'inference')"
            "   AND c.relkind IN ('r', 'v', 'm', 'p', 'f')"
            "   AND g.rolname = %s AND a.privilege_type = 'SELECT'",
            (ROLE,),
        ).fetchall()
    }
    assert table_level == ALLOWED_TABLES, (
        f"table-level granted-not-allowed: {sorted(table_level - ALLOWED_TABLES)}; "
        f"allowed-not-granted: {sorted(ALLOWED_TABLES - table_level)}"
    )
    # And effective access (direct + inherited + PUBLIC) agrees — nothing else
    # is reachable through any grant path. The three PostGIS catalog objects
    # are engine metadata that MUST stay PUBLIC-readable (spatial_ref_sys is
    # read by every PostGIS function); they are not spine relations.
    postgis_catalog = {"geography_columns", "geometry_columns", "spatial_ref_sys"}
    effective = granted - {"publication_disposition"} - postgis_catalog
    assert effective == ALLOWED_TABLES, (
        f"effective grants beyond the surface: {sorted(effective - ALLOWED_TABLES)}"
    )


def test_disposition_stays_column_limited(conn: object) -> None:
    for col in ("rationale", "decided_by"):
        assert not conn.execute(
            "SELECT has_column_privilege(%s, 'publication_disposition', %s, 'SELECT')",
            (ROLE, col),
        ).fetchone()[0], f"{ROLE} unexpectedly reads publication_disposition.{col}"
    for col in ("disposition", "reason_category", "authority", "policy_version"):
        assert conn.execute(
            "SELECT has_column_privilege(%s, 'publication_disposition', %s, 'SELECT')",
            (ROLE, col),
        ).fetchone()[0], f"{ROLE} cannot read tombstone column {col}"


@pytest.mark.parametrize("table", sorted(ALLOWED_TABLES))
def test_every_allowed_relation_really_selects(conn: object, table: str) -> None:
    """Privilege metadata is one thing; a real SELECT under the role is proof."""
    conn.execute(f"SET ROLE {ROLE}")
    try:
        conn.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchall()
    finally:
        conn.execute("RESET ROLE")


@pytest.mark.parametrize("table", FORBIDDEN_SAMPLES)
def test_forbidden_relations_refuse_a_real_select(conn: object, table: str) -> None:
    conn.execute(f"SET ROLE {ROLE}")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchall()
    # SET ROLE rolls back with the aborted transaction — restore cleanly.
    conn.rollback()


def test_inference_schema_usage_is_gone(conn: object) -> None:
    assert not conn.execute(
        "SELECT has_schema_privilege(%s, 'inference', 'USAGE')", (ROLE,)
    ).fetchone()[0]


def test_no_sequence_privileges_either(conn: object) -> None:
    """Least privilege covers sequences too — the public role names none."""
    rows = conn.execute(
        "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace,"
        "      aclexplode(c.relacl) a LEFT JOIN pg_roles g ON g.oid = a.grantee"
        " WHERE c.relkind = 'S' AND n.nspname IN ('public', 'inference')"
        "   AND a.privilege_type = 'USAGE'"
        "   AND (a.grantee = 0 OR g.rolname = %s)",  # PUBLIC or the role itself
        (ROLE,),
    ).fetchall()
    assert rows == [], f"{ROLE} unexpectedly holds sequence USAGE: {rows}"


def test_materialize_keeps_its_own_read_scope(conn: object) -> None:
    """Narrowing public must not break the materializer/curation read set —
    it is now granted directly (was: inheritance through public)."""
    for table in (
        "resolution",
        "relationship",
        "ingest_run",
        "ingest_run_completion",
        "camera_site_run",
        "camera_site_match",
        "camera_site_execution",
        "review_campaign",
        "review_campaign_item",
        "vocab_resolution_strategy",
        "vocab_rationale",
        "vocab_confidence",
        "inference.derived_fact",
    ):
        assert conn.execute(
            "SELECT has_table_privilege('sig_materialize', %s, 'SELECT')", (table,)
        ).fetchone()[0], f"sig_materialize lost its read on {table}"
