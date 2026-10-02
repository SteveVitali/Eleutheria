# SPDX-License-Identifier: Apache-2.0
"""The DB loader half of ``evidence-audit/1`` (P32.6, SIG-TRUST-007).

Docker-gated: seeds the spine exactly as the P32.2 sink would (artifact →
capture occurrence → claim → typed binding → run mark), then asserts
``db.evidence_audit.load_audit_input`` emits the ``audit-rows/1`` shape —
and writes NOTHING.
"""

from __future__ import annotations

import pytest
from conftest import insert_claim, seed_claim_prerequisites

pytestmark = pytest.mark.usefixtures("sig_database")

DIGEST = "CIabcdefghijklmnop"  # a well-formed recorded digest (multihash shape)


def _seed_evidence_chain(conn, prereqs) -> dict[str, object]:
    """artifact → blob → capture occurrence → typed claim_evidence binding."""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO source_registry(source_id,name,source_kind,default_reliability,"
        " reliability_justification,rights_id,custody_posture,compact_status,"
        " robots_policy) VALUES('audit_src','Audit Source','registry','R1','fixture',"
        " %s,'MIRROR','active','allow') ON CONFLICT DO NOTHING",
        (prereqs["rights_id"],),
    )
    cur.execute(
        "INSERT INTO evidence_artifact(source_id,stable_locator,artifact_type,"
        " acquisition_method,primary_or_secondary,rights_id,capture_status) "
        "VALUES('audit_src','https://example.test/doc','document','http','primary',"
        " %s,'captured') RETURNING artifact_id",
        (prereqs["rights_id"],),
    )
    artifact_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO evidence_blob(blob_digest,source_uri,byte_size,ocfl_object_id,"
        " ocfl_version) VALUES(%s,'https://example.test/doc',4,%s,'v1') "
        "ON CONFLICT DO NOTHING",
        (DIGEST, f"sig:capture:{DIGEST}"),
    )
    cur.execute(
        "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,media_type,"
        " retrieved_at,retrieved_by_run_id,ocfl_object_id,ocfl_version,storage_tier,"
        " capture_method,capture_tool_version,source_uri,blob_digest,"
        " capture_classification) "
        "VALUES(%s,%s,4,'text/plain','2026-10-01T00:00:00Z',%s,%s,'v1','public',"
        " 'httpx','1.0','https://example.test/doc',%s,'actual') RETURNING capture_id",
        (artifact_id, DIGEST, prereqs["run_id"], f"sig:capture:{DIGEST}", DIGEST),
    )
    capture_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO claim_evidence(claim_id,capture_id,role,locator,"
        " extraction_config_digest,extractor_version,binding_status) "
        'VALUES(%s,%s,\'establishes\',\'{"kind":"byte_range","start":0,"end":4}\','
        " 'cfg-1','parser/1.0','actual_capture')",
        (prereqs["claim_id"], capture_id),
    )
    cur.execute(
        "INSERT INTO ingest_run_capture(run_id,target_key,state,capture_digest,"
        " source_uri,media_type,byte_size,retrieved_at,records,ocfl_object_id,"
        " ocfl_version) VALUES(%s,'https://example.test/doc','flushed',%s,"
        " 'https://example.test/doc','text/plain',4,'2026-10-01T00:00:00Z',1,%s,'v1')",
        (prereqs["run_id"], DIGEST, f"sig:capture:{DIGEST}"),
    )
    return {"artifact_id": artifact_id, "capture_id": capture_id}


def test_load_audit_input_emits_the_row_contract(conn):
    from db.evidence_audit import load_audit_input

    prereqs = seed_claim_prerequisites(conn)
    prereqs["claim_id"] = insert_claim(conn, prereqs, value_text="25")
    chain = _seed_evidence_chain(conn, prereqs)

    load = load_audit_input(conn, claim_ids=[str(prereqs["claim_id"])])
    assert load.row_version == "evidence-audit-rows/1"
    assert len(load.rows) == 1
    row = load.rows[0]
    assert row["claim_id"] == str(prereqs["claim_id"])
    assert row["capture_id"] == str(chain["capture_id"])
    assert row["capture_digest"] == DIGEST
    assert row["capture_classification"] == "actual"
    assert row["binding_status"] == "actual_capture"
    assert row["role"] == "establishes"
    assert row["locator"] == {"kind": "byte_range", "start": 0, "end": 4}
    assert row["extractor_version"] == "parser/1.0"
    assert row["ocfl_object_id"] == f"sig:capture:{DIGEST}"
    assert row["source_id"] == "audit_src"
    # marks keyed by the capture digest attest the occurrence
    assert DIGEST in load.marks
    assert load.marks[DIGEST][0]["run_id"] == str(prereqs["run_id"])
    # the watermark records the audited spine
    assert load.watermark["claims"]["count"] >= 1
    assert load.watermark["evidence_capture"]["actual"] >= 1
    # eligibility comes through the shared fragment (no dispositions → eligible)
    assert str(prereqs["claim_id"]) in load.eligible_claim_ids


def test_loader_is_read_only(conn):
    """load_audit_input performs SELECTs only — asserted against row counts."""
    from db.evidence_audit import load_audit_input

    prereqs = seed_claim_prerequisites(conn)
    prereqs["claim_id"] = insert_claim(conn, prereqs)
    before = conn.execute(
        "SELECT (SELECT count(*) FROM claim),(SELECT count(*) FROM claim_evidence),"
        "(SELECT count(*) FROM publication_disposition)"
    ).fetchone()
    load_audit_input(conn)
    after = conn.execute(
        "SELECT (SELECT count(*) FROM claim),(SELECT count(*) FROM claim_evidence),"
        "(SELECT count(*) FROM publication_disposition)"
    ).fetchone()
    assert before == after


def test_units_from_rows_round_trips_loader_output(conn):
    """The ops classifier consumes exactly what the loader emits."""
    from db.evidence_audit import load_audit_input
    from ops.evidence_audit import units_from_rows

    prereqs = seed_claim_prerequisites(conn)
    prereqs["claim_id"] = insert_claim(conn, prereqs, value_text="25")
    chain = _seed_evidence_chain(conn, prereqs)
    load = load_audit_input(conn, claim_ids=[str(prereqs["claim_id"])])
    units = units_from_rows(load.rows, load.marks, load.eligible_claim_ids)
    assert len(units) == 1
    unit = units[0]
    assert unit.bindings[0].capture is not None
    assert unit.bindings[0].capture.capture_id == str(chain["capture_id"])
    assert unit.bindings[0].capture.marks
    assert unit.compartment  # resolved through policy.licensing
