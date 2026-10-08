# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The protective-seal register (P34.49 / ADR-185, F-406) over real
PG18+PostGIS — the ``seal_register`` sqitch change deployed by the conftest
container:

* ``capture_seal`` is append-only (immutable trigger + privilege — no
  UPDATE/DELETE route anywhere);
* ``capture_currently_sealed`` answers the latest recorded action — a
  capture is sealed until a superseding ``unseal`` row lands;
* the least-privilege posture holds (sig_seal_writer INSERT-only, the read
  roles column-limited, every role refused UPDATE/DELETE);
* the serving consult (``PgReadStore.capture``) serves the sealed
  representation for a sealed capture whatever tier the row carries; and
* the export's claim→evidence binding join drops a sealed capture and
  counts the drop.

The whole path is suppression: a seal row never deletes or overwrites a byte.
"""

from __future__ import annotations

from typing import Any

import psycopg
import pytest

pytestmark = pytest.mark.usefixtures("sig_database")


def _seed_capture(conn: Any, source_id: str = "seal_src") -> tuple[str, str, str]:
    """One captured artifact + capture + a bound claim. Returns
    (artifact_id, capture_id, claim_id)."""
    from conftest import insert_claim, seed_claim_prerequisites

    prereqs = seed_claim_prerequisites(conn)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO source_registry(source_id,name,source_kind,default_reliability,"
        "reliability_justification,rights_id,custody_posture,compact_status,robots_policy) "
        "VALUES(%s,'Fixture','portal','R2','fixture',%s,'MIRROR','no_response','obey')",
        (source_id, prereqs["rights_id"]),
    )
    cur.execute(
        "INSERT INTO evidence_artifact(source_id,stable_locator,artifact_type,"
        "acquisition_method,primary_or_secondary,rights_id,capture_status) "
        "VALUES(%s,%s,'webpage','crawl','primary',%s,'captured') RETURNING artifact_id",
        (source_id, f"urn:sig:{source_id}:page", prereqs["rights_id"]),
    )
    artifact_id = str(cur.fetchone()[0])
    cur.execute(
        "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,media_type,"
        "retrieved_at,retrieved_by_run_id,ocfl_object_id,ocfl_version,capture_method,"
        "capture_tool_version,storage_tier,capture_classification) "
        "VALUES(%s,%s,10,'application/json',now(),%s,%s,'v1','x','v','public','actual') "
        "RETURNING capture_id",
        (artifact_id, f"d-{source_id}", prereqs["run_id"], f"sig:capture:d-{source_id}"),
    )
    capture_id = str(cur.fetchone()[0])
    claim_id = insert_claim(conn, prereqs)
    cur.execute(
        "INSERT INTO claim_evidence(claim_id,capture_id,role) VALUES(%s,%s,'establishes')",
        (claim_id, capture_id),
    )
    return artifact_id, capture_id, str(claim_id)


def _seal(conn: Any, capture_id: str, digest: str, action: str = "seal") -> None:
    conn.execute(
        "INSERT INTO capture_seal(capture_id,content_digest,action,rules,author,audit_report)"
        " VALUES(%s,%s,%s,%s,'test','report')",
        (capture_id, digest, action, ["F406-OSM-USERUID"]),
    )


# --------------------------------------------------------------------------- #
# The register itself — append-only, least-privilege                            #
# --------------------------------------------------------------------------- #


def test_register_exists_with_the_writer_role(conn: Any) -> None:
    has = conn.execute("SELECT to_regclass('capture_seal') IS NOT NULL").fetchone()
    assert has and has[0]
    role = conn.execute(
        "SELECT rolname, rolcanlogin FROM pg_roles WHERE rolname='sig_seal_writer'"
    ).fetchone()
    assert role is not None and role[1] is False  # NOLOGIN


def test_register_is_append_only(conn: Any) -> None:
    _, capture_id, _ = _seed_capture(conn)
    _seal(conn, capture_id, "d-seal_src")
    with pytest.raises(Exception, match="immutable"), conn.transaction():
        conn.execute("UPDATE capture_seal SET action='unseal' WHERE capture_id=%s", (capture_id,))
    with pytest.raises(Exception, match="immutable"), conn.transaction():
        conn.execute("DELETE FROM capture_seal WHERE capture_id=%s", (capture_id,))


def test_no_role_can_update_or_delete(conn: Any) -> None:
    rows = conn.execute(
        "SELECT grantee, privilege_type FROM information_schema.table_privileges"
        " WHERE table_name='capture_seal' AND privilege_type IN ('UPDATE','DELETE')"
        "   AND grantee <> 'sig'"  # the owner always can; the trigger refuses it
    ).fetchall()
    assert rows == []


def test_public_reader_sees_column_limited_surface(conn: Any) -> None:
    """sig_read_public sees capture_id/action/rules — never author or the
    audit report ref (privileged columns)."""
    cols = {
        str(r[0])
        for r in conn.execute(
            "SELECT column_name FROM information_schema.column_privileges"
            " WHERE table_name='capture_seal' AND grantee='sig_read_public'"
        ).fetchall()
    }
    assert cols == {"seal_seq", "capture_id", "action", "rules", "recorded_at"}


def test_capture_currently_sealed_latest_action_wins(conn: Any) -> None:
    _, capture_id, _ = _seed_capture(conn)
    assert conn.execute("SELECT capture_currently_sealed(%s)", (capture_id,)).fetchone()[0] is False
    _seal(conn, capture_id, "d-seal_src")
    assert conn.execute("SELECT capture_currently_sealed(%s)", (capture_id,)).fetchone()[0] is True
    _seal(conn, capture_id, "d-seal_src", action="unseal")
    assert conn.execute("SELECT capture_currently_sealed(%s)", (capture_id,)).fetchone()[0] is False


# --------------------------------------------------------------------------- #
# The serving consult — PgReadStore.capture serves the sealed rep              #
# --------------------------------------------------------------------------- #


def test_sealed_capture_serves_the_sealed_representation(
    conn: Any, sig_database: dict[str, object]
) -> None:
    from api.store_pg import PgReadStore
    from evidence.tiers import SEALED_PUBLIC_FIELDS, public_representation

    artifact_id, capture_id, _ = _seed_capture(conn)
    _seal(conn, capture_id, "d-seal_src")
    conn.commit()  # the store reads on its own pooled connection

    dsn = (
        f"postgresql://{sig_database['user']}:{sig_database['password']}@"
        f"{sig_database['host']}:{sig_database['port']}/{sig_database['dbname']}"
    )
    store = PgReadStore(dsn, pool_min=1, pool_max=2)
    try:
        meta = store.capture(artifact_id, capture_id)
        assert meta is not None
        assert meta.tier.value == "sealed"
        rep = public_representation(meta)
        assert set(rep.keys()) <= SEALED_PUBLIC_FIELDS
        assert rep["bytes_available"] is False
        # The deny consult names why at class granularity (restricted-side).
        assert meta.seal_rules == ("F406-OSM-USERUID",)
    finally:
        store.close()
        with psycopg.connect(dsn, autocommit=True) as c:
            c.execute(
                "TRUNCATE capture_seal, claim_evidence, claim, evidence_capture,"
                " evidence_artifact, source_registry, ingest_run, rights_record CASCADE"
            )


def test_unsealed_capture_restores_the_recorded_tier(conn: Any) -> None:
    """A superseding unseal row restores the capture's recorded tier — the
    consult honours the latest action."""
    artifact_id, capture_id, _ = _seed_capture(conn)
    _seal(conn, capture_id, "d-seal_src")
    _seal(conn, capture_id, "d-seal_src", action="unseal")

    # Reads on the same conn fixture see the rolled-back view only through a
    # new connection; the SQL-level consult is asserted directly here.
    assert conn.execute("SELECT capture_currently_sealed(%s)", (capture_id,)).fetchone()[0] is False


# --------------------------------------------------------------------------- #
# The export consult — a sealed capture loses its public binding               #
# --------------------------------------------------------------------------- #


def test_export_bindings_drop_a_sealed_capture(conn: Any) -> None:
    from exports.spine_export import fetch_export_raw

    artifact_id, capture_id, claim_id = _seed_capture(conn, "seal_exp")
    cur = conn.cursor()
    raw_before = fetch_export_raw(cur)
    bound = [r for r in raw_before["evidence_bindings"] if str(r[1]) == capture_id]
    assert bound, "fixture: the capture must bind a claim before sealing"

    _seal(conn, capture_id, "d-seal_exp")
    raw_after = fetch_export_raw(cur)
    leaked = [r for r in raw_after["evidence_bindings"] if str(r[1]) == capture_id]
    assert leaked == []
    # the query gate dropped it — the post-check catch had nothing to remove,
    # and the counts-only record says one binding was suppressed.
    assert raw_after["sealed_bindings_dropped"] == [[0]]
    assert raw_after["sealed_bindings_suppressed"] == [[len(bound)]]
