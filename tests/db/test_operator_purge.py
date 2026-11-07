# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The operator-only purge function (P37.71; ADR-181/WV-06 + ADR-189/WV-11).

The acceptance shape: a fixture purge leaves a tombstone + audit record;
UPDATE/DELETE on `claim` from every other role and path still raises; no
path can invoke the function without holding ``sig_purge_operator``.
"""

from __future__ import annotations

import uuid

import psycopg
import pytest
from conftest import insert_claim, seed_claim_prerequisites


def _call_purge(conn: object, ids: list[str], category: str = "categorically_excluded") -> object:
    return conn.execute(
        "SELECT sig_purge_claims(%s::uuid[], %s, %s, %s)",
        (ids, category, "TICKET-GO-ref", None),
    ).fetchone()[0]


def test_purge_function_exists_security_definer(conn: object) -> None:
    row = conn.execute("SELECT prosecdef FROM pg_proc WHERE proname='sig_purge_claims'").fetchone()
    assert row and row[0] is True


def test_operator_role_is_nologin_and_holds_no_other_surface(conn: object) -> None:
    row = conn.execute(
        "SELECT rolcanlogin, rolsuper, rolbypassrls FROM pg_roles "
        "WHERE rolname='sig_purge_operator'"
    ).fetchone()
    assert row == (False, False, False)
    for table in ("claim", "claim_evidence", "purge_tombstone", "purge_audit"):
        for priv in ("INSERT", "UPDATE", "DELETE"):
            assert (
                conn.execute(
                    "SELECT has_table_privilege('sig_purge_operator', %s, %s)", (table, priv)
                ).fetchone()[0]
                is False
            )


def test_execute_is_operator_only(conn: object) -> None:
    sig = "sig_purge_claims(uuid[],text,text,text)"
    assert (
        conn.execute(
            "SELECT has_function_privilege('sig_purge_operator', %s, 'EXECUTE')", (sig,)
        ).fetchone()[0]
        is True
    )
    for role in (
        "sig_ingest",
        "sig_materialize",
        "sig_read_public",
        "sig_export",
        "sig_read_restricted",
        "sig_read_sealed",
        "sig_seal_writer",
    ):
        assert (
            conn.execute(
                "SELECT has_function_privilege(%s, %s, 'EXECUTE')", (role, sig)
            ).fetchone()[0]
            is False
        ), role


def test_fixture_purge_leaves_tombstone_and_audit(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    claim_id = insert_claim(conn, prereqs)
    # the bundle: evidence + qualifier + lineage rows belong to the claim
    conn.execute(
        "INSERT INTO source_registry(source_id,name,source_kind,default_reliability,"
        "reliability_justification,rights_id,custody_posture,compact_status,robots_policy) "
        "VALUES('sig.test.purge','Fixture','portal','R2','fixture',%s,'MIRROR',"
        "'no_response','obey')",
        (prereqs["rights_id"],),
    )
    artifact_id = conn.execute(
        "INSERT INTO evidence_artifact(source_id,stable_locator,artifact_type,"
        "acquisition_method,primary_or_secondary,rights_id,capture_status) "
        "VALUES('sig.test.purge','urn:sig:test:purge','webpage','crawl','primary',%s,"
        "'captured') RETURNING artifact_id",
        (prereqs["rights_id"],),
    ).fetchone()[0]
    capture_id = conn.execute(
        "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,media_type,"
        "retrieved_at,retrieved_by_run_id,ocfl_object_id,ocfl_version,capture_method,"
        "capture_tool_version) VALUES(%s,'d-purge',10,'text/html',now(),%s,'o','v1',"
        "'x','v') RETURNING capture_id",
        (artifact_id, prereqs["run_id"]),
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO claim_evidence(claim_id,capture_id,role) VALUES(%s,%s,'establishes')",
        (claim_id, capture_id),
    )
    conn.execute(
        "INSERT INTO claim_qualifier(claim_id,qualifier_id,value_text) "
        "VALUES(%s,'contracted_camera_count','x')",
        (claim_id,),
    )
    conn.execute(
        "INSERT INTO claim_lineage(claim_id,source_id,basis) VALUES(%s,'s','undeclared')",
        (claim_id,),
    )
    conn.execute("SET LOCAL ROLE sig_purge_operator")
    tomb = _call_purge(conn, [str(claim_id)])
    # the operator role holds no read surface — assertions run as the owner
    conn.execute("RESET ROLE")
    # the claim and its bundle are gone
    for table, col in (
        ("claim", "claim_id"),
        ("claim_evidence", "claim_id"),
        ("claim_qualifier", "claim_id"),
        ("claim_lineage", "claim_id"),
    ):
        assert (
            conn.execute(f"SELECT count(*) FROM {table} WHERE {col}=%s", (claim_id,)).fetchone()[0]
            == 0
        )
    t = conn.execute(
        "SELECT operation,target_kind,category,rows_removed FROM purge_tombstone "
        "WHERE tombstone_id=%s",
        (tomb,),
    ).fetchone()
    assert t == ("purge", "claim", "categorically_excluded", 1)
    a = conn.execute(
        "SELECT executed_role, detail FROM purge_audit WHERE tombstone_id=%s", (tomb,)
    ).fetchone()
    assert a[0] == "sig_purge_operator"
    assert a[1]["claim"] == 1 and a[1]["claim_evidence"] == 1
    # the append-only trigger is armed again: a plain delete still raises
    insert_claim(conn, prereqs)
    with pytest.raises(psycopg.Error, match="immutable"):
        with conn.transaction():
            conn.execute("DELETE FROM claim")


def test_every_other_role_and_path_still_raises(conn: object) -> None:
    """SIG-STORE-011 stands for every role but the one function: UPDATE/DELETE
    on `claim` from any other path still fails."""
    prereqs = seed_claim_prerequisites(conn)
    insert_claim(conn, prereqs)
    for role in ("sig_ingest", "sig_materialize", "sig_read_public", "sig_export"):
        conn.execute(f"SET LOCAL ROLE {role}")
        with pytest.raises(psycopg.Error):
            with conn.transaction():
                conn.execute("DELETE FROM claim")
        with pytest.raises(psycopg.Error):
            with conn.transaction():
                conn.execute("UPDATE claim SET value_text='x'")
        conn.execute("RESET ROLE")


def test_a_non_member_can_never_call_the_function(conn: object) -> None:
    """'No agent path can invoke it without the go': the deploy login, the
    ingest role — none is a member, all are refused."""
    prereqs = seed_claim_prerequisites(conn)
    claim_id = insert_claim(conn, prereqs)
    # as the plain session role (not a member) — the in-function check refuses
    with pytest.raises(psycopg.Error, match="sig_purge_operator"):
        with conn.transaction():
            _call_purge(conn, [str(claim_id)])
    # a non-member role is refused at the grant layer
    conn.execute("SET LOCAL ROLE sig_ingest")
    with pytest.raises(psycopg.Error):
        with conn.transaction():
            _call_purge(conn, [str(claim_id)])
    conn.execute("RESET ROLE")
    # the claim survived both refusals
    assert (
        conn.execute("SELECT count(*) FROM claim WHERE claim_id=%s", (claim_id,)).fetchone()[0] == 1
    )


def test_inputs_are_required_and_scoped(conn: object) -> None:
    conn.execute("SET LOCAL ROLE sig_purge_operator")
    with pytest.raises(psycopg.Error, match="no claim ids"):
        with conn.transaction():
            _call_purge(conn, [])
    with pytest.raises(psycopg.Error, match="closed vocabulary"):
        with conn.transaction():
            conn.execute(
                "SELECT sig_purge_claims(%s::uuid[], %s, %s, %s)",
                ([str(uuid.uuid4())], "not-a-category", "go", None),
            )
    with pytest.raises(psycopg.Error, match="go must be named"):
        with conn.transaction():
            conn.execute(
                "SELECT sig_purge_claims(%s::uuid[], %s, %s, %s)",
                ([str(uuid.uuid4())], "categorically_excluded", "", None),
            )
    conn.execute("RESET ROLE")


def test_a_recorded_decision_blocks_the_purge(conn: object) -> None:
    """A claim a decision references is refused — suppression, not purge."""
    prereqs = seed_claim_prerequisites(conn)
    claim_id = insert_claim(conn, prereqs)
    conn.execute(
        "INSERT INTO entity_identifier(entity_id,scheme,value,asserted_by_claim) "
        "VALUES(%s,'us.fbi.ori','OK0090000',%s)",
        (prereqs["subject_id"], claim_id),
    )
    conn.execute("SET LOCAL ROLE sig_purge_operator")
    with pytest.raises(psycopg.Error, match="entity_identifier.asserted_by_claim"):
        with conn.transaction():
            _call_purge(conn, [str(claim_id)])
    conn.execute("RESET ROLE")
    assert (
        conn.execute("SELECT count(*) FROM claim WHERE claim_id=%s", (claim_id,)).fetchone()[0] == 1
    )


def test_a_set_purges_intra_references_together(conn: object) -> None:
    """A claim + its correction purge together under one go; a claim still
    referenced by an outside claim's revises_claim is refused alone."""
    prereqs = seed_claim_prerequisites(conn)
    old = insert_claim(conn, prereqs)
    new = insert_claim(
        conn, prereqs, value_text="26", value_num=26, revises_claim=old, correction_reason="fixture"
    )
    conn.execute("SET LOCAL ROLE sig_purge_operator")
    # alone: the correction's revises_claim still points at the old claim
    with pytest.raises(psycopg.Error, match="claim.revises_claim"):
        with conn.transaction():
            _call_purge(conn, [str(old)])
    # together: intra-set references purge as one set
    _call_purge(conn, [str(old), str(new)])
    conn.execute("RESET ROLE")
    assert conn.execute("SELECT count(*) FROM claim").fetchone()[0] == 0


def test_tombstone_and_audit_are_immutable(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    claim_id = insert_claim(conn, prereqs)
    conn.execute("SET LOCAL ROLE sig_purge_operator")
    tomb = _call_purge(conn, [str(claim_id)])
    conn.execute("RESET ROLE")
    for table in ("purge_tombstone", "purge_audit"):
        with pytest.raises(psycopg.Error, match="immutable"):
            with conn.transaction():
                conn.execute(f"UPDATE {table} SET authority_ref='x' WHERE TRUE")
        with pytest.raises(psycopg.Error, match="immutable"):
            with conn.transaction():
                conn.execute(f"DELETE FROM {table}")
    assert tomb is not None
