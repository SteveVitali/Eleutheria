# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The SIG-ONTO-001/002 layer-direction contract, mechanically enforced (P37.57a).

§8.1: data flows upward only — no layer may write to a layer below it. The
boundary is enforced by GRANTs (who may write where) and by the
``append_only_guard`` trigger (L1 stays append-only even where a write grant
exists). This file audits both, over the real PG18+PostGIS spine:

* the WHOLE-SCHEMA write matrix — for each pipeline role, the exact set of
  (table, privilege) writes it may hold across ``public``/``inference``/
  ``intake``, asserted against ``role_table_grants`` so a new grant lands as a
  named diff, never silently;
* functional direction probes under ``SET ROLE`` — the materializer cannot
  reach the spine, readers/export cannot write anywhere, ingest cannot reach
  L4, and the append-only trigger refuses a claim rewrite even for the role
  holding the UPDATE grant;
* L4 is a separate labelled namespace — every ``inference.*`` table carries
  ``input_claim_ids`` + ``derived_at``, and the namespace set itself is
  audited;
* L4 drops and rebuilds — ``inference.derived_fact`` is deleted wholesale and
  re-materialized from the unchanged spine to identical stable content.
"""

from __future__ import annotations

import json
from typing import Any

import psycopg
import pytest
from conftest import insert_claim, seed_claim_prerequisites
from inference.accountability import materialize_accountability_links

ROLES = (
    "sig_ingest",
    "sig_materialize",
    "sig_read_public",
    "sig_read_restricted",
    "sig_read_sealed",
    "sig_export",
)

#: The audited write surface each pipeline role may hold, per §8.1/SIG-ONTO-002:
#: role -> {table -> privileges}. ``role_table_grants`` is swept over the whole
#: public+inference+intake namespaces and must equal this map EXACTLY — a grant
#: added or lost lands as a named diff here, which is the layer-direction test.
EXPECTED_WRITES: dict[str, dict[str, set[str]]] = {
    # L0–L2 writer: evidence, claims, entities, run/decision records. Holds the
    # legacy `resolution` INSERT (access_control, pre-materializer) and the
    # COLUMN-scoped evidence_artifact UPDATE (disappearance event only — see
    # test_ingest_artifact_update_is_column_scoped). Nothing at L4; nothing in
    # the post-Round-6 L3 projection set.
    "sig_ingest": {
        "claim": {"INSERT", "UPDATE"},
        "claim_evidence": {"INSERT"},
        "claim_qualifier": {"INSERT"},
        "claim_lineage": {"INSERT"},
        "assertion_quarantine": {"INSERT"},
        "entity": {"INSERT"},
        "resolution": {"INSERT"},
        # UPDATE on evidence_artifact is COLUMN-scoped (the two disappearance
        # event columns only) — role_table_grants reports table-level grants,
        # so it does not appear here; test_ingest_artifact_update_is_column_scoped
        # pins the column set exactly.
        "evidence_artifact": {"INSERT"},
        "evidence_capture": {"INSERT"},
        "extraction": {"INSERT"},
        "evidence_blob": {"INSERT"},
        "evidence_access_log": {"INSERT"},
        "rights_decision": {"INSERT"},
        "ingest_run_capture": {"INSERT"},
        "ingest_run_completion": {"INSERT"},
        "ingest_run_report": {"INSERT"},
        "entity_identity_key": {"INSERT"},
        "entity_type_decision": {"INSERT"},
        "source_redistribution": {"INSERT"},
        "subject_key_pin": {"INSERT"},
        "subject_rekey_decision": {"INSERT"},
    },
    # L3+L4 writer — INSERT only (UPDATE/DELETE/TRUNCATE revoked schema-wide by
    # materialize_role.sql); lineage + disposition + vocab provenance writes are
    # its declared provenance side-outputs.
    "sig_materialize": {
        "resolution": {"INSERT"},
        "relationship": {"INSERT"},
        "contradiction": {"INSERT"},
        "coverage_record": {"INSERT"},
        "research_task": {"INSERT"},
        "entity_role": {"INSERT"},
        "review_item": {"INSERT"},
        "review_decision": {"INSERT"},
        "review_campaign": {"INSERT"},
        "review_campaign_item": {"INSERT"},
        "camera_site_run": {"INSERT"},
        "camera_site_match": {"INSERT"},
        "camera_site_execution": {"INSERT"},
        "camera_site_census": {"INSERT"},
        "camera_site_demotion": {"INSERT"},
        "organization_run": {"INSERT"},
        "organization_match": {"INSERT"},
        "organization_execution": {"INSERT"},
        "inference.derived_fact": {"INSERT"},
        "ingest_run_completion": {"INSERT"},
        "ingest_run_report": {"INSERT"},
        "vocab_resolution_strategy": {"INSERT"},
        "vocab_rationale": {"INSERT"},
        "vocab_confidence": {"INSERT"},
        "source_redistribution": {"INSERT"},
        "source_lineage": {"INSERT"},
        "claim_lineage": {"INSERT"},
        "publication_disposition": {"INSERT"},
    },
    # L5-facing readers: SELECT only, nothing writes back — "L5 stores nothing".
    "sig_read_public": {},
    # The one audited reader-write: restricted/sealed reads append to the
    # access-audit log (evidence_store.sql) — an L0-side audit append, never a
    # spine write.
    "sig_read_restricted": {"evidence_access_log": {"INSERT"}},
    "sig_read_sealed": {"evidence_access_log": {"INSERT"}},
    # The exporter's one write: retention pruning of that same access log.
    "sig_export": {"evidence_access_log": {"DELETE"}},
}

WRITE_PRIVS = ("INSERT", "UPDATE", "DELETE", "TRUNCATE")


def _actual_writes(conn: Any) -> dict[tuple[str, str], set[str]]:
    """``(role, table) -> {write privileges}`` from role_table_grants, swept over
    the whole public+inference+intake namespaces — column-scoped grants appear
    here too (the evidence_artifact UPDATE), matching EXPECTED_WRITES' grain."""
    rows = conn.execute(
        "SELECT grantee, table_schema, table_name, privilege_type "
        "FROM information_schema.role_table_grants "
        "WHERE grantee = ANY(%s) AND table_schema = ANY(%s) "
        "AND privilege_type = ANY(%s)",
        (list(ROLES), ["public", "inference", "intake"], list(WRITE_PRIVS)),
    ).fetchall()
    actual: dict[tuple[str, str], set[str]] = {}
    for grantee, schema, table, priv in rows:
        name = f"{schema}.{table}" if schema != "public" else table
        actual.setdefault((grantee, name), set()).add(priv)
    return actual


def test_the_whole_schema_write_matrix_matches_the_layer_contract(conn: Any) -> None:
    """THE layer-direction check: no role writes below its layer, ever —
    asserted as exact equality between the deployed grant surface and the
    audited EXPECTED_WRITES map. A grant added or lost is a named diff."""
    actual = _actual_writes(conn)
    expected: dict[tuple[str, str], set[str]] = {}
    for role, tables in EXPECTED_WRITES.items():
        for table, privs in tables.items():
            expected[(role, table)] = privs
    keys = actual.keys() | expected.keys()
    diffs = [
        f"{role} on {table}: deployed={sorted(actual.get((role, table), ()))} "
        f"expected={sorted(expected.get((role, table), ()))}"
        for role, table in sorted(keys)
        if actual.get((role, table), set()) != expected.get((role, table), set())
    ]
    assert not diffs, "grant surface drifted from the §8.1 layer contract:\n" + "\n".join(diffs)


def test_public_holds_no_write_privileges(conn: Any) -> None:
    rows = conn.execute(
        "SELECT table_schema, table_name, privilege_type "
        "FROM information_schema.role_table_grants "
        "WHERE grantee = 'PUBLIC' AND table_schema = ANY(%s) "
        "AND privilege_type = ANY(%s)",
        (["public", "inference", "intake"], list(WRITE_PRIVS)),
    ).fetchall()
    assert rows == [], f"PUBLIC holds write privileges: {rows}"


def test_no_role_writes_to_a_layer_below_its_own(conn: Any) -> None:
    """Directional summary of the matrix (the headline, in words): the ingest
    role never reaches L3/L4 derived tables, the materialize role never
    reaches the L0–L2 spine, and no read/export role writes a spine row."""
    l34 = (
        "resolution",
        "relationship",
        "contradiction",
        "coverage_record",
        "research_task",
        "review_item",
        "review_decision",
        "entity_role",
        "camera_site_run",
        "camera_site_match",
        "camera_site_execution",
        "camera_site_census",
        "camera_site_demotion",
        "organization_run",
        "organization_match",
        "organization_execution",
        "inference.derived_fact",
        "inference.derived_geometry",
    )
    for table in l34:
        if table == "resolution":
            continue  # the audited legacy exception in EXPECTED_WRITES
        for priv in WRITE_PRIVS:
            assert not conn.execute(
                "SELECT has_table_privilege('sig_ingest', %s, %s)", (table, priv)
            ).fetchone()[0], f"sig_ingest must not write {table} ({priv})"
    l012 = (
        "evidence_artifact",
        "evidence_capture",
        "evidence_blob",
        "claim",
        "claim_evidence",
        "claim_qualifier",
        "entity",
        "entity_identifier",
        "organization",
        "deployment",
        "physical_asset",
    )
    for table in l012:
        for priv in WRITE_PRIVS:
            assert not conn.execute(
                "SELECT has_table_privilege('sig_materialize', %s, %s)", (table, priv)
            ).fetchone()[0], f"sig_materialize must not write {table} ({priv})"


def test_l5_never_writes_below(conn: Any) -> None:
    """ "L5 stores nothing" (SIG-ONTO-002): the presentation/export roles hold
    no write on any spine table — the only audited exception is the access-
    audit log, which is an audit append/prune, never a spine fact."""
    swept = _actual_writes(conn)
    for role in ("sig_read_public", "sig_read_restricted", "sig_read_sealed", "sig_export"):
        writes = {
            table: privs
            for (r, table), privs in swept.items()
            if r == role and table != "evidence_access_log"
        }
        assert writes == {}, f"{role} writes below L5: {writes}"


def test_the_schema_namespaces_are_exactly_the_layered_set(conn: Any) -> None:
    """Physical separation (SIG-ONTO-002): the only application namespaces are
    the canonical spine (public), the L4 inference namespace, and the intake
    quarantine — extension namespaces (postgis) and the sqitch migration
    registry are not application layers."""
    schemas = {
        str(r[0])
        for r in conn.execute(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name NOT LIKE 'pg_%' AND schema_name <> 'information_schema'"
        ).fetchall()
    }
    app = schemas - {"topology", "tiger", "extensions", "sqitch"}
    assert app == {"public", "inference", "intake"}, app


def test_l4_tables_carry_the_inference_labels(conn: Any) -> None:
    """ "Every inference says it is an inference": each table in the inference
    namespace carries the citation columns (input_claim_ids + derived_at), NOT
    NULL — and the check sweeps every inference table, so a future L4 table
    without the labels fails here."""
    tables = [
        str(r[0])
        for r in conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'inference' AND table_type = 'BASE TABLE'"
        ).fetchall()
    ]
    assert tables, "the inference namespace holds no tables"
    for table in tables:
        cols = {
            str(r[0]): bool(r[1])
            for r in conn.execute(
                "SELECT column_name, is_nullable = 'NO' "
                "FROM information_schema.columns "
                "WHERE table_schema = 'inference' AND table_name = %s",
                (table,),
            ).fetchall()
        }
        for label in ("input_claim_ids", "derived_at"):
            assert cols.get(label) is True, f"inference.{table} lacks the L4 label {label} NOT NULL"


def test_l2_entity_table_is_identity_only(conn: Any) -> None:
    """SIG-ONTO-003: the L2 `entity` table holds identity + lifecycle
    bookkeeping only — every attribute of every entity is a claim, never a
    column. A new entity column lands as a named diff here."""
    cols = {
        str(r[0])
        for r in conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'entity'"
        ).fetchall()
    }
    assert cols == {"entity_id", "entity_type", "created_at", "merged_into"}


def test_ingest_artifact_update_is_column_scoped(conn: Any) -> None:
    """L0 write-once (SIG-ONTO-002): the disappearance writer's UPDATE on
    evidence_artifact reaches exactly the two event columns — every content
    column stays un-writable."""
    allowed = ("capture_status", "disappeared_observed_at")
    for col in allowed:
        assert conn.execute(
            "SELECT has_column_privilege('sig_ingest', 'evidence_artifact', %s, 'UPDATE')",
            (col,),
        ).fetchone()[0], f"sig_ingest should UPDATE evidence_artifact.{col}"
    for col in ("stable_locator", "artifact_type", "rights_id", "source_id"):
        assert not conn.execute(
            "SELECT has_column_privilege('sig_ingest', 'evidence_artifact', %s, 'UPDATE')",
            (col,),
        ).fetchone()[0], f"sig_ingest must not UPDATE evidence_artifact.{col}"


def test_direction_probes_under_set_role(conn: Any) -> None:
    """Behaviour, not just grants: the refusals fire under SET ROLE, and the
    append-only trigger refuses a claim rewrite even for the role whose grant
    would otherwise permit it (SIG-ONTO-002 'L1 is append-only')."""
    conn.execute("SET ROLE sig_materialize")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("INSERT INTO entity(entity_type) VALUES('deployment')")
    conn.rollback()
    conn.execute("SET ROLE sig_materialize")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("DELETE FROM resolution WHERE true")
    conn.rollback()
    conn.execute("SET ROLE sig_read_public")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("DELETE FROM claim WHERE true")
    conn.rollback()
    conn.execute("SET ROLE sig_export")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("INSERT INTO entity(entity_type) VALUES('deployment')")
    conn.rollback()
    conn.execute("SET ROLE sig_ingest")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute(
            "INSERT INTO inference.derived_fact"
            "(subject_id, predicate_id, value_json, derivation_rule, rule_version,"
            " input_claim_ids, confidence) "
            "VALUES (gen_random_uuid(), 'x', '{}'::jsonb, 'x', 'x', '{}', 'x')"
        )
    conn.rollback()
    # ingest CAN write at its own layer — the positive control.
    conn.execute("SET ROLE sig_ingest")
    conn.execute("INSERT INTO entity(entity_type) VALUES('deployment')")
    conn.rollback()
    # …and the strongest append-only fact of all: the writer is READ-BLIND.
    # sig_ingest holds INSERT+UPDATE on claim, yet the restrictive tier-ceiling
    # policy (it belongs to no read role → max tier -1) hides every claim row —
    # it can append a row it can then never see, update or delete. The
    # append_only_guard trigger's own refusal (UPDATE/DELETE raise
    # restrict_violation) is proven on the superuser path in test_append_only.
    prereqs = seed_claim_prerequisites(conn)
    claim_id = insert_claim(conn, prereqs)
    conn.execute("SET ROLE sig_ingest")
    visible = conn.execute(
        "SELECT count(*) FROM claim WHERE claim_id = %s", (claim_id,)
    ).fetchone()[0]
    assert visible == 0, "sig_ingest should be read-blind to the spine it appends"
    cur = conn.execute("UPDATE claim SET raw_value = 'rewritten' WHERE claim_id = %s", (claim_id,))
    assert cur.rowcount == 0, "a blind UPDATE can never reach a claim row"
    conn.rollback()


# --- L4 drop/rebuild (SIG-ONTO-002 'L4 is separate, labelled, droppable') ----


def _ref_claim(conn: Any, prereqs: dict, subject: Any, predicate: str, target: Any) -> None:
    conn.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,object_entity,value_kind,"
        "value_text,raw_value,observed_at,source_reliability,claim_directness,"
        "artifact_integrity,asserted_by,assertion_rationale,ingest_run_id,rights_id,"
        "sensitivity_tier) "
        "VALUES(%s,%s,'entity_ref',%s,'value',%s,%s,'2026-05-01T00:00:00Z','R1','D1','I1',"
        "%s,'fixture',%s,%s,0)",
        (
            subject,
            predicate,
            target,
            str(target),
            str(target),
            prereqs["author_id"],
            prereqs["run_id"],
            prereqs["rights_id"],
        ),
    )


def _seed_accountability_chain(conn: Any) -> None:
    prereqs = seed_claim_prerequisites(conn)
    conn.execute(
        "INSERT INTO vocab_resolution_strategy(strategy_id,definition) "
        "VALUES('never_resolve','fixture: recorded, not adjudicated') ON CONFLICT DO NOTHING"
    )
    for pid in ("operator", "buyer", "seller", "recipient", "applies_to"):
        conn.execute(
            "INSERT INTO vocab_predicate"
            "(predicate_id,vocab_version,value_datatype,object_type,definition,"
            " volatility_class,half_life_days,resolution_strategy) "
            "VALUES(%s,'1.0.0','entity_ref','entity_ref','fixture','IMMUTABLE',NULL,"
            "'never_resolve') ON CONFLICT DO NOTHING",
            (pid,),
        )

    def entity(etype: str) -> Any:
        return conn.execute(
            "INSERT INTO entity(entity_type) VALUES(%s) RETURNING entity_id", (etype,)
        ).fetchone()[0]

    dep, org = prereqs["subject_id"], entity("organization")
    vendor, contract = entity("organization"), entity("contract")
    funding, policy = entity("funding_instrument"), entity("policy")
    _ref_claim(conn, prereqs, dep, "operator", org)
    _ref_claim(conn, prereqs, contract, "buyer", org)
    _ref_claim(conn, prereqs, contract, "seller", vendor)
    _ref_claim(conn, prereqs, funding, "recipient", org)
    _ref_claim(conn, prereqs, policy, "applies_to", dep)


def _l4_snapshot(conn: Any) -> list[tuple[Any, ...]]:
    """Stable ``inference.derived_fact`` content — the minted surrogate key and
    ``derived_at`` stamp excluded, everything else (incl. the citation list,
    whose target claim rows are canonical and untouched) compared exactly."""
    rows = conn.execute(
        "SELECT subject_id, predicate_id, value_json, derivation_rule, rule_version,"
        " input_claim_ids, confidence FROM inference.derived_fact"
    ).fetchall()
    canon = [
        (
            str(r[0]),
            str(r[1]),
            json.dumps(r[2], sort_keys=True),
            str(r[3]),
            str(r[4]),
            tuple(str(v) for v in sorted(r[5], key=str)),
            str(r[6]),
        )
        for r in rows
    ]
    return sorted(canon, key=repr)


def test_l4_drops_and_rebuilds_from_the_unchanged_spine(conn: Any) -> None:
    """The droppable-layer proof: materialize the L4 accountability facts,
    snapshot, DELETE the whole inference namespace, re-run the documented
    rebuild command — the stable content returns identical, and every row
    still carries its L4 labels."""
    _seed_accountability_chain(conn)
    materialize_accountability_links(conn, role="sig_materialize")
    conn.execute("RESET ROLE")
    before = _l4_snapshot(conn)
    assert before, "the seeded chain produced no derived facts"
    conn.execute("DELETE FROM inference.derived_fact")
    conn.execute("DELETE FROM inference.derived_geometry")
    materialize_accountability_links(conn, role="sig_materialize")
    conn.execute("RESET ROLE")
    assert _l4_snapshot(conn) == before
    # …and every rebuilt row still says it is an inference (§30.2 labels).
    unlabeled = conn.execute(
        "SELECT count(*) FROM inference.derived_fact "
        "WHERE derivation_rule = '' OR rule_version = '' "
        "OR cardinality(input_claim_ids) = 0 OR derived_at IS NULL"
    ).fetchone()[0]
    assert unlabeled == 0
