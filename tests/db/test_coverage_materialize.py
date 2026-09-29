# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Materialize honest §32 coverage into the real spine (P28.4).

Exercises the ``coverage_materialize`` sqitch change (deploy/verify happen in the
conftest container) and the append-only, idempotent, no-total materializer over
PG18+PostGIS:

* counted quantities are written with NAMED denominators (§32.2/32.3, SIG-METRIC-003/005);
* the honest §32.1 negative space (``not_researched``) is written, distinguished from
  ``searched_not_found``;
* the no-total invariant is pinned at the DB — a metric row that names a population total
  (or omits its denominator) is REJECTED by the ``coverage_metric_named_denominator``
  CHECK (SIG-METRIC-009/010);
* the write path is insert-only — no UPDATE/DELETE;
* a re-run over an unchanged spine inserts **+0** (idempotent on ``input_digest``);
* ``read_materialized_coverage`` round-trips the surface seam.
"""

from __future__ import annotations

import psycopg
import pytest
from conftest import seed_claim_prerequisites
from inference.materialize import materialize_coverage, read_materialized_coverage

PRED_A = "contracted_camera_count"  # seeded by seed_claim_prerequisites
PRED_B = "active_device_count"


def _seed_predicate_b(conn: object) -> None:
    conn.execute(
        "INSERT INTO vocab_predicate"
        "(predicate_id,vocab_version,value_datatype,object_type,definition,"
        " volatility_class,half_life_days,resolution_strategy) "
        "VALUES(%s,'1.0.0','integer','quantity','fixture','FAST',180,"
        "'authoritative_source_wins') ON CONFLICT DO NOTHING",
        (PRED_B,),
    )


def _capture(conn: object, prereqs: dict, key: str) -> object:
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
        "VALUES(%s,%s,'registry','registry_api','primary',%s,'captured') RETURNING artifact_id",
        (key, f"urn:sig:p284:{key}", prereqs["rights_id"]),
    ).fetchone()[0]
    return conn.execute(
        "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,media_type,"
        "retrieved_at,retrieved_by_run_id,ocfl_object_id,ocfl_version,storage_tier,"
        "capture_method,capture_tool_version,source_uri) "
        "VALUES(%s,%s,10,'application/json','2026-05-01T00:00:00Z',%s,%s,'v1',"
        "'public','registry_api','sig/0',%s) RETURNING capture_id",
        (
            artifact_id,
            f"digest-{key}",
            prereqs["run_id"],
            f"urn:sig:p284:{key}",
            f"urn:sig:p284:{key}",
        ),
    ).fetchone()[0]


def _claim(
    conn: object, prereqs: dict, subject_id: object, predicate: str, value: int, capture_id: object
) -> object:
    claim_id = conn.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,value_text,"
        "value_num,unit,raw_value,observed_at,source_reliability,claim_directness,"
        "artifact_integrity,asserted_by,assertion_rationale,ingest_run_id,rights_id,"
        "sensitivity_tier) "
        "VALUES(%s,%s,'quantity','value',%s,%s,'devices',%s,'2026-05-01T00:00:00Z',"
        "'R1','D1','I1',%s,'fixture',%s,%s,0) RETURNING claim_id",
        (
            subject_id,
            predicate,
            str(value),
            value,
            str(value),
            prereqs["author_id"],
            prereqs["run_id"],
            prereqs["rights_id"],
        ),
    ).fetchone()[0]
    if capture_id is not None:
        conn.execute(
            "INSERT INTO claim_evidence(claim_id,capture_id,role) VALUES(%s,%s,'establishes')",
            (claim_id, capture_id),
        )
    return claim_id


def _seed_two_subjects(conn: object) -> dict:
    """S1 (deployment) claims PRED_A with evidence; S2 (deployment) claims PRED_B without.

    Yields: provenance completeness 1-of-2; two per-predicate reconciliation ratios;
    peer-class negative space — S1 lacks PRED_B, S2 lacks PRED_A → two ``not_researched``
    records.
    """
    prereqs = seed_claim_prerequisites(conn)
    _seed_predicate_b(conn)
    s1 = prereqs["subject_id"]
    s2 = conn.execute(
        "INSERT INTO entity(entity_type) VALUES('deployment') RETURNING entity_id"
    ).fetchone()[0]
    cap = _capture(conn, prereqs, "vendor_registry")
    a = _claim(conn, prereqs, s1, PRED_A, 12, cap)  # with evidence
    b = _claim(conn, prereqs, s2, PRED_B, 7, None)  # no evidence (a provenance defect)
    return {"prereqs": prereqs, "s1": str(s1), "s2": str(s2), "claim_a": str(a), "claim_b": str(b)}


def test_sqitch_change_deployed_columns_index_and_no_total_check(conn: object) -> None:
    conn.execute(
        "SELECT input_digest, metric_method, named_denominator, numerator, denominator "
        "FROM coverage_record WHERE false"
    )
    idx = conn.execute(
        "SELECT 1 FROM pg_indexes WHERE indexname='coverage_record_input_digest_key'"
    ).fetchone()
    assert idx is not None
    chk = conn.execute(
        "SELECT 1 FROM pg_constraint WHERE conname='coverage_metric_named_denominator'"
    ).fetchone()
    assert chk is not None


def test_materialize_writes_denominated_metrics_and_negative_space(conn: object) -> None:
    _seed_two_subjects(conn)
    summary = materialize_coverage(conn)
    assert summary.inserted >= 1
    assert summary.absences_inserted >= 1  # negative space retained

    # EVERY counted-quantity row carries a named denominator; NONE is a total.
    metric_rows = conn.execute(
        "SELECT metric_method, named_denominator, numerator, denominator, metric_value "
        "FROM coverage_record WHERE input_digest IS NOT NULL AND metric_method IS NOT NULL"
    ).fetchall()
    assert metric_rows, "at least one denominated coverage metric was written"
    for _method, named_denominator, numerator, denominator, _value in metric_rows:
        assert named_denominator is not None and named_denominator.strip() != ""
        assert named_denominator.strip().lower() not in {
            "reality",
            "true population",
            "all devices",
            "total",
            "everything",
            "the world",
        }
        assert numerator <= denominator  # a numerator can never beat its denominator

    # The §32.3 provenance-completeness counted quantity is present and honest (1 of 2).
    prov = conn.execute(
        "SELECT numerator, denominator FROM coverage_record "
        "WHERE named_denominator = 'published tier-0 claims'"
    ).fetchone()
    assert prov is not None
    assert prov == (1, 2)  # one of the two seeded claims has resolvable evidence

    # Negative space is queryable and distinguished from searched_not_found.
    absences = conn.execute(
        "SELECT count(*) FROM coverage_record "
        "WHERE metric_method IS NULL AND absence_kind = 'not_researched' "
        "AND input_digest IS NOT NULL"
    ).fetchone()[0]
    assert absences >= 1


def test_no_total_row_can_be_inserted_the_db_check_refuses_it(conn: object) -> None:
    """The no-total invariant, pinned at the DB (SIG-METRIC-009/010)."""
    # A metric row that names a population total is refused.
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO coverage_record(absence_kind, metric_method, named_denominator, "
            "numerator, denominator, metric_value, input_digest) "
            "VALUES('not_applicable','counted_with_denominator','total',5,10,0.5,'digest-total')"
        )


def test_a_metric_row_without_a_named_denominator_is_refused(conn: object) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO coverage_record(absence_kind, metric_method, named_denominator, "
            "numerator, denominator, input_digest) "
            "VALUES('not_applicable','counted_with_denominator',NULL,5,10,'digest-nulldenom')"
        )


def test_re_run_is_idempotent_plus_zero(conn: object) -> None:
    _seed_two_subjects(conn)
    first = materialize_coverage(conn)
    assert first.inserted >= 1
    before = conn.execute(
        "SELECT count(*) FROM coverage_record WHERE input_digest IS NOT NULL"
    ).fetchone()[0]
    second = materialize_coverage(conn)
    assert second.inserted == 0
    assert second.skipped_existing == first.inserted
    after = conn.execute(
        "SELECT count(*) FROM coverage_record WHERE input_digest IS NOT NULL"
    ).fetchone()[0]
    assert before == after


def test_read_materialized_coverage_round_trips(conn: object) -> None:
    _seed_two_subjects(conn)
    materialize_coverage(conn)
    records = read_materialized_coverage(conn)
    assert records
    metrics = [r for r in records if r["metric_method"] is not None]
    absences = [r for r in records if r["metric_method"] is None]
    assert metrics and absences
    for m in metrics:
        assert m["named_denominator"]  # every published metric names its denominator
    for a in absences:
        assert a["absence_kind"] == "not_researched"
