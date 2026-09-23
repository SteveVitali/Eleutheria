# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Materialize the VISIBLE §31 contradiction object into the real spine (P28.3).

Exercises the ``contradiction_materialize`` sqitch change (deploy/verify happen in the
conftest container) and the append-only, idempotent, lifecycle-aware materializer over
PG18+PostGIS:

* a real 299-vs-190 count disagreement seeded on the spine is DETECTED and WRITTEN with
  BOTH evidence sides in ``claim_ids`` — kept VISIBLE, never reconciled away (§3.1);
* the write path is insert-only — no UPDATE/DELETE;
* a re-run over an unchanged spine inserts **+0** (idempotent on ``input_digest``);
* a clean (uncontested) pair writes 0 contradictions;
* lifecycle-aware — retract one side (append-only ``sys_period`` close) → a re-run
  appends a ``superseded`` state row, the open row RETAINED in history;
* ``read_materialized_contradictions`` round-trips the ``_persisted_contradictions`` shape.
"""

from __future__ import annotations

from conftest import seed_claim_prerequisites
from reconcile.materialize import (
    materialize_contradictions,
    read_materialized_contradictions,
)

PRED = "contracted_device_count"  # resolvable: authoritative_source_wins, in the registry


def _seed_predicate(conn: object) -> None:
    conn.execute(
        "INSERT INTO vocab_resolution_strategy(strategy_id,definition) "
        "VALUES('authoritative_source_wins','fixture') ON CONFLICT DO NOTHING"
    )
    conn.execute(
        "INSERT INTO vocab_predicate"
        "(predicate_id,vocab_version,value_datatype,object_type,definition,"
        " volatility_class,half_life_days,resolution_strategy) "
        "VALUES(%s,'1.0.0','integer','quantity','fixture','IMMUTABLE',365,"
        "'authoritative_source_wins') ON CONFLICT DO NOTHING",
        (PRED,),
    )


def _source_and_capture(conn: object, prereqs: dict, genre: str, key: str) -> object:
    conn.execute(
        "INSERT INTO source_registry(source_id,name,source_kind,default_reliability,"
        "reliability_justification,rights_id,custody_posture,compact_status,"
        "robots_policy,ingestion_permitted) "
        "VALUES(%s,%s,'registry','R1','fixture',%s,'MIRROR','granted','obey',true) "
        "ON CONFLICT DO NOTHING",
        (key, key, prereqs["rights_id"]),
    )
    artifact_id = conn.execute(
        "INSERT INTO evidence_artifact(source_id,stable_locator,artifact_type,"
        "acquisition_method,primary_or_secondary,rights_id,capture_status) "
        "VALUES(%s,%s,%s,'registry_api','primary',%s,'captured') RETURNING artifact_id",
        (key, f"urn:sig:p283:{key}", genre, prereqs["rights_id"]),
    ).fetchone()[0]
    capture_id = conn.execute(
        "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,media_type,"
        "retrieved_at,retrieved_by_run_id,ocfl_object_id,ocfl_version,storage_tier,"
        "capture_method,capture_tool_version,source_uri) "
        "VALUES(%s,%s,10,'application/json','2026-05-01T00:00:00Z',%s,%s,'v1',"
        "'public','registry_api','sig/0',%s) RETURNING capture_id",
        (
            artifact_id,
            f"digest-{key}",
            prereqs["run_id"],
            f"urn:sig:p283:{key}",
            f"urn:sig:p283:{key}",
        ),
    ).fetchone()[0]
    return capture_id


def _claim(
    conn: object, prereqs: dict, value: int, reliability: str, capture_id: object, obs: str
) -> object:
    claim_id = conn.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,value_text,"
        "value_num,unit,raw_value,observed_at,source_reliability,claim_directness,"
        "artifact_integrity,asserted_by,assertion_rationale,ingest_run_id,rights_id,"
        "sensitivity_tier) "
        "VALUES(%s,%s,'quantity','value',%s,%s,'devices',%s,%s,%s,'D1','I1',%s,'fixture',%s,%s,0) "
        "RETURNING claim_id",
        (
            prereqs["subject_id"],
            PRED,
            str(value),
            value,
            str(value),
            obs,
            reliability,
            prereqs["author_id"],
            prereqs["run_id"],
            prereqs["rights_id"],
        ),
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO claim_evidence(claim_id,capture_id,role) VALUES(%s,%s,'establishes')",
        (claim_id, capture_id),
    )
    return claim_id


def _seed_disagreement(conn: object) -> tuple[dict, object, object]:
    """The canonical 299-vs-190 count disagreement on one resolvable subject."""
    prereqs = seed_claim_prerequisites(conn)
    _seed_predicate(conn)
    cap_a = _source_and_capture(conn, prereqs, "executed_contract", "vendor_contract")
    cap_b = _source_and_capture(conn, prereqs, "invoice", "vendor_invoice")
    claim_299 = _claim(conn, prereqs, 299, "R1", cap_a, "2026-05-01T00:00:00Z")
    claim_190 = _claim(conn, prereqs, 190, "R2", cap_b, "2026-04-01T00:00:00Z")
    return prereqs, claim_299, claim_190


def test_sqitch_change_deployed_input_digest_column_and_index(conn: object) -> None:
    conn.execute("SELECT input_digest FROM contradiction WHERE false")
    row = conn.execute(
        "SELECT 1 FROM pg_indexes WHERE indexname='contradiction_input_digest_key'"
    ).fetchone()
    assert row is not None


def test_299_vs_190_is_detected_and_kept_visible_with_both_sides(  # noqa: N802
    conn: object,
) -> None:
    prereqs, claim_299, claim_190 = _seed_disagreement(conn)
    summary = materialize_contradictions(conn, subject=str(prereqs["subject_id"]))
    assert summary.inserted == 1
    assert summary.by_type.get("value_disagreement") == 1

    row = conn.execute(
        "SELECT contradiction_type, status, claim_ids, severity, input_digest "
        "  FROM contradiction WHERE subject_id=%s",
        (prereqs["subject_id"],),
    ).fetchone()
    assert row is not None
    assert row[0] == "value_disagreement"
    assert row[1] == "open"  # kept VISIBLE, never reconciled away (§3.1)
    # BOTH evidence sides present — neither the 299 nor the 190 claim collapsed away.
    claim_ids = {str(x) for x in row[2]}
    assert str(claim_299) in claim_ids
    assert str(claim_190) in claim_ids
    assert row[3] == "notable"
    assert row[4] is not None  # the idempotency key


def test_re_run_is_idempotent_plus_zero(conn: object) -> None:
    prereqs, _, _ = _seed_disagreement(conn)
    first = materialize_contradictions(conn, subject=str(prereqs["subject_id"]))
    assert first.inserted == 1
    before = conn.execute(
        "SELECT count(*) FROM contradiction WHERE subject_id=%s", (prereqs["subject_id"],)
    ).fetchone()[0]
    second = materialize_contradictions(conn, subject=str(prereqs["subject_id"]))
    assert second.inserted == 0
    assert second.skipped_existing == 1
    assert second.superseded == 0
    after = conn.execute(
        "SELECT count(*) FROM contradiction WHERE subject_id=%s", (prereqs["subject_id"],)
    ).fetchone()[0]
    assert before == after == 1


def test_a_clean_pair_writes_no_contradiction(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    _seed_predicate(conn)
    cap_a = _source_and_capture(conn, prereqs, "executed_contract", "vendor_contract")
    cap_b = _source_and_capture(conn, prereqs, "invoice", "vendor_invoice")
    _claim(conn, prereqs, 299, "R1", cap_a, "2026-05-01T00:00:00Z")
    _claim(conn, prereqs, 299, "R2", cap_b, "2026-04-01T00:00:00Z")  # agree — no conflict
    summary = materialize_contradictions(conn, subject=str(prereqs["subject_id"]))
    assert summary.inserted == 0
    count = conn.execute(
        "SELECT count(*) FROM contradiction WHERE subject_id=%s", (prereqs["subject_id"],)
    ).fetchone()[0]
    assert count == 0


def test_lifecycle_supersede_is_a_new_row_never_a_deletion(conn: object) -> None:
    prereqs, _, claim_190 = _seed_disagreement(conn)
    first = materialize_contradictions(conn, subject=str(prereqs["subject_id"]))
    assert first.inserted == 1

    # Later evidence: retract the 190 side by closing its transaction-time interval —
    # the ONE append-only mutation the spine permits (never a DELETE / data edit).
    # clock_timestamp() (not now()) so the upper bound is after the insert's own
    # clock_timestamp() lower bound within this single test transaction.
    conn.execute(
        "UPDATE claim SET sys_period = tstzrange(lower(sys_period), clock_timestamp(), '[)') "
        "WHERE claim_id=%s",
        (claim_190,),
    )
    # Only 299 remains in the current belief → the disagreement resolves.
    second = materialize_contradictions(conn, subject=str(prereqs["subject_id"]))
    assert second.inserted == 0  # no new open contradiction
    assert second.superseded == 1  # a NEW superseded state row appended

    rows = conn.execute(
        "SELECT status, resolved_by FROM contradiction WHERE subject_id=%s ORDER BY status",
        (prereqs["subject_id"],),
    ).fetchall()
    statuses = [r[0] for r in rows]
    assert "open" in statuses  # the open finding is RETAINED (never deleted)
    assert "superseded" in statuses  # resolution is a NEW lifecycle state row
    assert len(rows) == 2

    # Idempotent: re-running does not re-supersede.
    third = materialize_contradictions(conn, subject=str(prereqs["subject_id"]))
    assert third.superseded == 0
    total = conn.execute(
        "SELECT count(*) FROM contradiction WHERE subject_id=%s", (prereqs["subject_id"],)
    ).fetchone()[0]
    assert total == 2


def test_read_materialized_contradictions_round_trips_the_persisted_shape(conn: object) -> None:
    prereqs, claim_299, claim_190 = _seed_disagreement(conn)
    materialize_contradictions(conn, subject=str(prereqs["subject_id"]))
    records = read_materialized_contradictions(conn)
    mine = [r for r in records if r["subject_id"] == str(prereqs["subject_id"])]
    assert len(mine) == 1
    rec = mine[0]
    # Mirrors api.store_pg._persisted_contradictions: id/subject/predicate/type/status/claim_ids.
    assert rec["predicate_id"] == PRED
    assert rec["contradiction_type"] == "value_disagreement"
    assert rec["status"] == "open"
    assert {str(claim_299), str(claim_190)} <= set(rec["claim_ids"])
