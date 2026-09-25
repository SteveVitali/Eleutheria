# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Materialize honest §32 coverage into the real spine (P28.4).

Exercises the ``coverage_materialize`` sqitch change (deploy/verify happen in the
conftest container) and the append-only, idempotent, no-total materializer over
PG18+PostGIS:

* counted quantities are written with NAMED denominators (§32.2/32.3, SIG-METRIC-003/005);
* the honest §32.1 negative space (``not_researched``) is written, distinguished from
  ``searched_not_found`` — scoped by the **declared peer classes** (P31.9 / ADR-115:
  ``(entity_type, connector)`` membership + a declared tracked-predicate set per class,
  never the union over the whole spine);
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
from inference.peer_classes import PeerClass

PRED_A = "contracted_camera_count"  # seeded by seed_claim_prerequisites
PRED_B = "active_device_count"
PRED_C = "retention_period"
PRED_X = "portal_exists"  # claimed by a class-A member but NEVER declared → never emitted

#: The declared §32.1 peer classes this suite materializes against (ADR-115). Class A
#: covers the ``fixture`` connector, class B ``fixture_b``; claims written by any other
#: connector (e.g. ``fixture_undeclared``) have no declared coverage surface.
FIXTURE_PEER_CLASSES = (
    PeerClass(entity_type="deployment", connectors=("fixture",), tracked=(PRED_A, PRED_B)),
    PeerClass(entity_type="deployment", connectors=("fixture_b",), tracked=(PRED_B, PRED_C)),
)


def _seed_predicates(conn: object) -> None:
    for pred in (PRED_B, PRED_C, PRED_X):
        conn.execute(
            "INSERT INTO vocab_predicate"
            "(predicate_id,vocab_version,value_datatype,object_type,definition,"
            " volatility_class,half_life_days,resolution_strategy) "
            "VALUES(%s,'1.0.0','integer','quantity','fixture','FAST',180,"
            "'authoritative_source_wins') ON CONFLICT DO NOTHING",
            (pred,),
        )


def _ingest_run(conn: object, connector: str) -> object:
    """A second/third ingest run stamped with a different ``connector_name`` — the
    peer-class membership signal (ADR-115)."""
    return conn.execute(
        "INSERT INTO ingest_run(connector_name,connector_version,code_commit,"
        "ruleset_version,vocab_version,parameters,environment,input_digests) "
        "VALUES(%s,'0','sha','r1','1.0.0','{}','{}','{}') RETURNING run_id",
        (connector,),
    ).fetchone()[0]


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
    conn: object,
    prereqs: dict,
    subject_id: object,
    predicate: str,
    value: int,
    capture_id: object,
    run_id: object = None,
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
            run_id or prereqs["run_id"],
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
    """S1 claims PRED_A via the ``fixture`` connector (class A) with evidence;
    S2 claims PRED_B via ``fixture_b`` (class B) without.

    Yields: provenance completeness 1-of-2; two per-predicate reconciliation ratios;
    class-scoped negative space — S1 lacks class-A's PRED_B, S2 lacks class-B's
    PRED_C → exactly two ``not_researched`` records, and NEVER a cross-class row
    (S1 is never "not researched" for PRED_C, S2 never for PRED_A).
    """
    prereqs = seed_claim_prerequisites(conn)
    _seed_predicates(conn)
    s1 = prereqs["subject_id"]
    s2 = conn.execute(
        "INSERT INTO entity(entity_type) VALUES('deployment') RETURNING entity_id"
    ).fetchone()[0]
    cap = _capture(conn, prereqs, "vendor_registry")
    a = _claim(conn, prereqs, s1, PRED_A, 12, cap)  # with evidence
    b = _claim(
        conn, prereqs, s2, PRED_B, 7, None, run_id=_ingest_run(conn, "fixture_b")
    )  # no evidence (a provenance defect)
    return {"prereqs": prereqs, "s1": str(s1), "s2": str(s2), "claim_a": str(a), "claim_b": str(b)}


def _absences(conn: object) -> dict[tuple[str, str], None]:
    rows = conn.execute(
        "SELECT subject_id::text, predicate_id FROM coverage_record "
        "WHERE metric_method IS NULL AND absence_kind = 'not_researched' "
        "AND input_digest IS NOT NULL"
    ).fetchall()
    return {(str(r[0]), str(r[1])): None for r in rows}


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
    seeded = _seed_two_subjects(conn)
    summary = materialize_coverage(conn, peer_classes=FIXTURE_PEER_CLASSES)
    assert summary.inserted >= 1
    assert summary.absences_inserted == 2  # S1 lacks PRED_B; S2 lacks PRED_C — nothing else

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

    # Negative space is queryable, class-scoped, and distinguished from
    # searched_not_found: exactly (S1, PRED_B) and (S2, PRED_C).
    assert set(_absences(conn)) == {
        (seeded["s1"], PRED_B),
        (seeded["s2"], PRED_C),
    }


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
    first = materialize_coverage(conn, peer_classes=FIXTURE_PEER_CLASSES)
    assert first.inserted >= 1
    before = conn.execute(
        "SELECT count(*) FROM coverage_record WHERE input_digest IS NOT NULL"
    ).fetchone()[0]
    second = materialize_coverage(conn, peer_classes=FIXTURE_PEER_CLASSES)
    assert second.inserted == 0
    assert second.skipped_existing == first.inserted
    after = conn.execute(
        "SELECT count(*) FROM coverage_record WHERE input_digest IS NOT NULL"
    ).fetchone()[0]
    assert before == after


def test_no_cross_class_negative_space(conn: object) -> None:
    """A subject is compared only with peers of its declared class (ADR-115)."""
    seeded = _seed_two_subjects(conn)
    materialize_coverage(conn, peer_classes=FIXTURE_PEER_CLASSES)
    absences = _absences(conn)
    # S1 (class A) is never "not researched" for class-B's PRED_C, and S2 (class B)
    # is never "not researched" for class-A's PRED_A — cross-class rows cannot exist.
    assert (seeded["s1"], PRED_C) not in absences
    assert (seeded["s2"], PRED_A) not in absences
    assert absences == {(seeded["s1"], PRED_B): None, (seeded["s2"], PRED_C): None}


def test_an_undeclared_predicate_never_appears(conn: object) -> None:
    """PRED_X is claimed by a class-A member but is not declared: no subject can be
    'not researched' for it — an undeclared predicate is never negative space."""
    seeded = _seed_two_subjects(conn)
    prereqs = seeded["prereqs"]
    s4 = conn.execute(
        "INSERT INTO entity(entity_type) VALUES('deployment') RETURNING entity_id"
    ).fetchone()[0]
    _claim(conn, prereqs, s4, PRED_X, 1, None)  # class-A member via the 'fixture' run
    materialize_coverage(conn, peer_classes=FIXTURE_PEER_CLASSES)
    absences = _absences(conn)
    assert all(pred != PRED_X for _, pred in absences)
    # S4's negative space is the rest of class A's declared surface, no more.
    assert (str(s4), PRED_A) in absences and (str(s4), PRED_B) in absences
    assert all(subj != str(s4) or pred in {PRED_A, PRED_B} for subj, pred in absences)


def test_a_subject_with_only_undeclared_connectors_has_no_negative_space(
    conn: object,
) -> None:
    """No declared class ⇒ no coverage surface ⇒ no rows (never a guess)."""
    prereqs = seed_claim_prerequisites(conn)
    _seed_predicates(conn)
    s3 = conn.execute(
        "INSERT INTO entity(entity_type) VALUES('deployment') RETURNING entity_id"
    ).fetchone()[0]
    _claim(conn, prereqs, s3, PRED_A, 3, None, run_id=_ingest_run(conn, "fixture_undeclared"))
    materialize_coverage(conn, peer_classes=FIXTURE_PEER_CLASSES)
    assert not _absences(conn)


def test_the_shipped_declaration_does_not_cover_fixture_connectors(conn: object) -> None:
    """The default declaration (inference/data/peer_classes.toml) is what the hosted
    run uses; fixture connectors are deliberately undeclared → no negative space."""
    _seed_two_subjects(conn)
    summary = materialize_coverage(conn)  # peer_classes=None → shipped file
    assert summary.absences_inserted == 0
    # …while the denominated metrics are unchanged (the peer-class rule touches ONLY
    # the negative space).
    prov = conn.execute(
        "SELECT numerator, denominator FROM coverage_record "
        "WHERE named_denominator = 'published tier-0 claims'"
    ).fetchone()
    assert prov == (1, 2)


def test_read_materialized_coverage_round_trips(conn: object) -> None:
    _seed_two_subjects(conn)
    materialize_coverage(conn, peer_classes=FIXTURE_PEER_CLASSES)
    records = read_materialized_coverage(conn)
    assert records
    metrics = [r for r in records if r["metric_method"] is not None]
    absences = [r for r in records if r["metric_method"] is None]
    assert metrics and absences
    for m in metrics:
        assert m["named_denominator"]  # every published metric names its denominator
    for a in absences:
        assert a["absence_kind"] == "not_researched"


def _resolution(conn: object, subject_id: str, predicate: str, winning_claim: object) -> None:
    """A materialized §16.4 decision; ``winning_claim=None`` is an unresolved_conflict."""
    conn.execute(
        "INSERT INTO vocab_resolution_strategy(strategy_id,definition) "
        "VALUES('authoritative_source_wins','fixture') ON CONFLICT DO NOTHING"
    )
    conn.execute(
        "INSERT INTO vocab_rationale(rationale_code,template) VALUES('FIXTURE','t') "
        "ON CONFLICT DO NOTHING"
    )
    conn.execute(
        "INSERT INTO vocab_confidence(confidence,definition) VALUES('probable','d') "
        "ON CONFLICT DO NOTHING"
    )
    conn.execute(
        "INSERT INTO resolution(subject_id,predicate_id,value_kind,valid_period,winning_claim,"
        " considered_claims,contradiction_state,strategy_id,rationale_code,rationale_text,"
        " confidence,evidence_counts,resolver_version,ruleset_version,input_digest) "
        "VALUES(%s,%s,'value',tstzrange('2026-05-01',NULL,'[)'),%s,'{}',%s,"
        " 'authoritative_source_wins','FIXTURE','fixture','probable','{}','r','r',%s)",
        (
            subject_id,
            predicate,
            winning_claim,
            "uncontested" if winning_claim else "unresolved_conflict",
            f"fixture-{subject_id}-{predicate}",
        ),
    )


def _ratio(conn: object, predicate: str) -> tuple[int, int]:
    row = conn.execute(
        "SELECT numerator, denominator FROM coverage_record "
        "WHERE metric_method = 'reconciliation_ratio' AND predicate_id = %s",
        (predicate,),
    ).fetchone()
    assert row is not None
    return int(row[0]), int(row[1])


def test_an_unresolved_conflict_is_never_counted_as_a_resolved_value(conn: object) -> None:
    """P30.2 finding COVERAGE-RESOLVED-01: the hosted 299-vs-190 ``unresolved_conflict``
    envelope was counted in the "subjects with a resolved <predicate> value" numerator.
    Only a decision that picked a winning claim resolves anything (§3.1)."""
    seeded = _seed_two_subjects(conn)
    _resolution(conn, seeded["s1"], PRED_A, None)  # unresolved_conflict — no winner
    _resolution(conn, seeded["s2"], PRED_B, seeded["claim_b"])  # a genuine resolved value
    materialize_coverage(conn, negative_space=False)
    assert _ratio(conn, PRED_A) == (0, 1)
    assert _ratio(conn, PRED_B) == (1, 1)


def test_the_read_seam_returns_the_latest_measurement_superseded_rows_stay(conn: object) -> None:
    """A re-measured quantity is a NEW row (append-only); the seam returns only the latest,
    and the superseded measurement stays in the table as history."""
    seeded = _seed_two_subjects(conn)
    materialize_coverage(conn, negative_space=False)
    assert _ratio(conn, PRED_B) == (0, 1)
    # The spine changes: PRED_B is now resolved → a new, superseding measurement row.
    _resolution(conn, seeded["s2"], PRED_B, seeded["claim_b"])
    second = materialize_coverage(conn, negative_space=False)
    assert second.inserted == 1  # only the changed quantity; the rest +0
    history = conn.execute(
        "SELECT numerator FROM coverage_record WHERE metric_method = 'reconciliation_ratio' "
        "AND predicate_id = %s ORDER BY coverage_id",
        (PRED_B,),
    ).fetchall()
    assert [int(r[0]) for r in history] == [0, 1]  # both measurements retained, never updated
    current = [
        r
        for r in read_materialized_coverage(conn)
        if r["metric_method"] == "reconciliation_ratio" and r["predicate_id"] == PRED_B
    ]
    assert len(current) == 1
    assert current[0]["numerator"] == 1.0
