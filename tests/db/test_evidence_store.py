# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The evidence-store schema against a real PG18 (P02.2; SIG-EVID-004/011/012/013).

These extend the P02.1 live-Postgres harness (see conftest.py): the sqitch plan
now includes the `evidence_store` change, so a deployed database has the dedup
blob registry, the source_uri uniqueness, the redaction guard, and the audited
access log. Every write here is rolled back by the `conn` fixture.
"""

from __future__ import annotations

import psycopg
import pytest


def _seed_capture(conn: object) -> dict[str, object]:
    """Insert the minimum FK chain for an evidence_capture; return the ids."""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO rights_record(spdx_expression,redistributable,"
        "derivative_permitted,retrieval_date) "
        "VALUES('Apache-2.0','yes','yes','2026-01-01') RETURNING rights_id"
    )
    rights_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO source_registry(source_id,name,source_kind,default_reliability,"
        "reliability_justification,rights_id,custody_posture,compact_status,robots_policy) "
        "VALUES('portal','Portal','portal','R2','fixture',%s,'MIRROR','no_response','obey') ",
        (rights_id,),
    )
    cur.execute(
        "INSERT INTO ingest_run(connector_name,connector_version,code_commit,"
        "ruleset_version,vocab_version,parameters,environment,input_digests) "
        "VALUES('fixture','0','sha','r1','1.0.0','{}','{}','{}') RETURNING run_id"
    )
    run_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO evidence_artifact(source_id,stable_locator,artifact_type,"
        "acquisition_method,primary_or_secondary,rights_id,capture_status) "
        "VALUES('portal','urn:sig:source:portal:x','webpage','crawl','primary',%s,'captured') "
        "RETURNING artifact_id",
        (rights_id,),
    )
    artifact_id = cur.fetchone()[0]
    return {
        "rights_id": rights_id,
        "run_id": run_id,
        "artifact_id": artifact_id,
        "source_uri": "urn:sig:source:portal:x",
    }


def _insert_blob(conn: object, seed: dict[str, object], digest: str) -> None:
    conn.cursor().execute(
        "INSERT INTO evidence_blob(blob_digest,source_uri,byte_size,ocfl_object_id,ocfl_version) "
        "VALUES(%s,%s,10,%s,'v1')",
        (digest, seed["source_uri"], seed["source_uri"]),
    )


def _insert_capture(conn: object, seed: dict[str, object], digest: str, **over: object) -> object:
    cur = conn.cursor()
    cols = {
        "artifact_id": seed["artifact_id"],
        "content_digest": digest,
        "byte_size": 10,
        "media_type": "text/html",
        "retrieved_at": "2026-05-01T00:00:00Z",
        "retrieved_by_run_id": seed["run_id"],
        "ocfl_object_id": seed["source_uri"],
        "ocfl_version": "v1",
        "storage_tier": "public",
        "capture_method": "wacz",
        "capture_tool_version": "sig-evidence/0",
        "source_uri": seed["source_uri"],
        "blob_digest": digest,
    }
    cols.update(over)
    names = ",".join(cols)
    placeholders = ",".join(["%s"] * len(cols))
    cur.execute(
        f"INSERT INTO evidence_capture({names}) VALUES({placeholders}) RETURNING capture_id",
        list(cols.values()),
    )
    return cur.fetchone()[0]


def test_source_uri_dedup_key_is_unique(conn: object) -> None:
    """SIG-EVID-004: (blob_digest, source_uri) is unique."""
    seed = _seed_capture(conn)
    _insert_blob(conn, seed, "bdigest1")
    with pytest.raises(psycopg.errors.UniqueViolation):
        _insert_blob(conn, seed, "bdigest1")


def test_unchanged_page_yields_one_blob_but_many_capture_rows(conn: object) -> None:
    """SIG-EVID-004: dedup does NOT block N capture rows for one digest/artifact."""
    seed = _seed_capture(conn)
    _insert_blob(conn, seed, "bdigest1")
    _insert_capture(conn, seed, "bdigest1")
    # The P02.1 (content_digest, artifact_id) unique would have blocked this; the
    # evidence_store change dropped it so a daily re-fetch records another row.
    _insert_capture(conn, seed, "bdigest1", retrieved_at="2026-05-02T00:00:00Z")
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM evidence_capture WHERE content_digest='bdigest1'")
    assert cur.fetchone()[0] == 2
    cur.execute("SELECT count(*) FROM evidence_blob WHERE blob_digest='bdigest1'")
    assert cur.fetchone()[0] == 1


def test_redaction_is_a_new_capture_with_parent_and_version(conn: object) -> None:
    """SIG-EVID-011: redaction = new capture with parent_capture_id + version."""
    seed = _seed_capture(conn)
    _insert_blob(conn, seed, "bdigest1")
    original = _insert_capture(conn, seed, "bdigest1")
    _insert_blob(conn, seed, "bredacted")
    redacted = _insert_capture(
        conn,
        seed,
        "bredacted",
        parent_capture_id=original,
        redaction_applied=True,
        redaction_method="blackbox",
        redaction_version="2.1",
    )
    assert redacted != original


def test_redaction_without_version_is_rejected(conn: object) -> None:
    """SIG-EVID-011: a redaction must record its version (identifiable/re-doable)."""
    seed = _seed_capture(conn)
    _insert_blob(conn, seed, "bdigest1")
    original = _insert_capture(conn, seed, "bdigest1")
    _insert_blob(conn, seed, "bredacted")
    with pytest.raises(psycopg.errors.CheckViolation):
        _insert_capture(
            conn,
            seed,
            "bredacted",
            parent_capture_id=original,
            redaction_applied=True,
            redaction_method="blackbox",  # no redaction_version
        )


def test_disappearance_is_an_update_not_a_delete(conn: object) -> None:
    """SIG-EVID-013/014: record the event + generate a task; delete nothing."""
    seed = _seed_capture(conn)
    cur = conn.cursor()
    cur.execute(
        "UPDATE evidence_artifact SET disappeared_observed_at='2026-06-01T00:00:00Z',"
        "capture_status='link_rotted' WHERE artifact_id=%s",
        (seed["artifact_id"],),
    )
    cur.execute("INSERT INTO entity(entity_type) VALUES('deployment') RETURNING entity_id")
    subject = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO research_task"
        "(task_type,subject_id,priority,closing_condition,detector_version) "
        "VALUES('source_disappeared',%s,0.8,'retrievable again OR replacement',"
        "'evidence.disappearance/1')",
        (subject,),
    )
    # The artifact still exists — its captures and claims are untouched.
    cur.execute(
        "SELECT capture_status, disappeared_observed_at IS NOT NULL "
        "FROM evidence_artifact WHERE artifact_id=%s",
        (seed["artifact_id"],),
    )
    status, disappeared = cur.fetchone()
    assert status == "link_rotted" and disappeared


def test_access_log_only_records_restricted_and_sealed(conn: object) -> None:
    """SIG-EVID-012: public access is not audited; restricted/sealed is."""
    seed = _seed_capture(conn)
    _insert_blob(conn, seed, "bdigest1")
    capture = _insert_capture(conn, seed, "bdigest1", storage_tier="sealed")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO evidence_access_log(capture_id,requester,purpose,storage_tier,"
        "retention_expires_at) VALUES(%s,'researcher','takedown review','sealed',"
        "'2026-12-01T00:00:00Z')",
        (capture,),
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        cur.execute(
            "INSERT INTO evidence_access_log(capture_id,requester,purpose,storage_tier,"
            "retention_expires_at) VALUES(%s,'researcher','browsing','public',"
            "'2026-12-01T00:00:00Z')",
            (capture,),
        )


def test_ingest_run_grant_forbids_delete_on_evidence(conn: object) -> None:
    """SIG-EVID-013: no application role may DELETE evidence (append-only)."""
    cur = conn.cursor()
    cur.execute(
        "SELECT has_table_privilege('sig_ingest','evidence_artifact','DELETE'),"
        "has_table_privilege('sig_ingest','evidence_capture','DELETE')"
    )
    artifact_del, capture_del = cur.fetchone()
    assert not artifact_del and not capture_del
