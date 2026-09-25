# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Materialize §28 resolution envelopes into the real spine (P28.1, ADR-099).

Exercises the ``resolution_materialize`` sqitch change (deploy/verify happen in the
conftest container) and the append-only, idempotent materializer over PG18+PostGIS:

* the resolver runs over real claims and WRITES a ``resolution`` row with full
  provenance (§16.4);
* a re-run over unchanged claims inserts **+0** (idempotent on ``input_digest``);
* the write path is insert-only — no UPDATE/DELETE of the claim spine.
"""

from __future__ import annotations

from datetime import date

from conftest import seed_claim_prerequisites
from reconcile.materialize import materialize_resolutions

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
        (key, f"urn:sig:p281:{key}", genre, prereqs["rights_id"]),
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
            f"urn:sig:p281:{key}",
            f"urn:sig:p281:{key}",
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


def _seed_resolvable_subject(conn: object) -> dict:
    prereqs = seed_claim_prerequisites(conn)
    _seed_predicate(conn)
    cap_contract = _source_and_capture(conn, prereqs, "executed_contract", "vendor_contract")
    cap_invoice = _source_and_capture(conn, prereqs, "invoice", "vendor_invoice")
    _claim(conn, prereqs, 299, "R1", cap_contract, "2026-05-01T00:00:00Z")
    _claim(conn, prereqs, 299, "R2", cap_invoice, "2026-04-01T00:00:00Z")
    return prereqs


def test_sqitch_change_deployed_input_digest_column_and_index(conn: object) -> None:
    # The column exists (selectable) and the partial unique index is present.
    conn.execute("SELECT input_digest FROM resolution WHERE false")
    row = conn.execute(
        "SELECT 1 FROM pg_indexes WHERE indexname='resolution_input_digest_key'"
    ).fetchone()
    assert row is not None


def test_materialize_writes_a_resolution_row_with_provenance(conn: object) -> None:
    prereqs = _seed_resolvable_subject(conn)
    summary = materialize_resolutions(conn, subject=str(prereqs["subject_id"]))
    assert summary.inserted == 1
    assert summary.resolved == 1
    row = conn.execute(
        "SELECT value_num, confidence, contradiction_state, strategy_id, decided_by, "
        "       input_digest, resolver_version FROM resolution WHERE subject_id=%s",
        (prereqs["subject_id"],),
    ).fetchone()
    assert row is not None
    assert int(row[0]) == 299
    assert row[1] == "confirmed"
    assert row[2] in ("uncontested", "resolved_conflict")
    assert row[3] == "authoritative_source_wins"
    assert row[4] == "auto"
    assert row[5] is not None  # the input_digest idempotency key
    assert row[6]  # resolver_version stamped


def test_re_run_is_idempotent_plus_zero(conn: object) -> None:
    prereqs = _seed_resolvable_subject(conn)
    first = materialize_resolutions(conn, subject=str(prereqs["subject_id"]))
    assert first.inserted == 1
    before = conn.execute(
        "SELECT count(*) FROM resolution WHERE subject_id=%s", (prereqs["subject_id"],)
    ).fetchone()[0]
    # Re-run over the SAME claims: append-only + idempotent -> +0.
    second = materialize_resolutions(conn, subject=str(prereqs["subject_id"]))
    assert second.inserted == 0
    assert second.skipped_existing == 1
    after = conn.execute(
        "SELECT count(*) FROM resolution WHERE subject_id=%s", (prereqs["subject_id"],)
    ).fetchone()[0]
    assert before == after == 1


def test_unresolvable_predicate_is_skipped_not_guessed(conn: object) -> None:
    # A claim on a predicate the resolver ruleset does not know is skipped, not written.
    prereqs = seed_claim_prerequisites(
        conn
    )  # seeds predicate 'contracted_camera_count' (not in registry)
    _source_and_capture(conn, prereqs, "portal_snapshot", "portal")
    conn.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,value_text,"
        "value_num,unit,raw_value,observed_at,source_reliability,claim_directness,"
        "artifact_integrity,asserted_by,assertion_rationale,ingest_run_id,rights_id,"
        "sensitivity_tier) VALUES(%s,%s,'quantity','value','7',7,'cameras','7',"
        "'2026-05-01T00:00:00Z','R1','D1','I1',%s,'fixture',%s,%s,0)",
        (
            prereqs["subject_id"],
            prereqs["predicate_id"],
            prereqs["author_id"],
            prereqs["run_id"],
            prereqs["rights_id"],
        ),
    )
    summary = materialize_resolutions(conn, subject=str(prereqs["subject_id"]))
    assert summary.inserted == 0
    assert summary.skipped_unresolvable >= 1
    count = conn.execute(
        "SELECT count(*) FROM resolution WHERE subject_id=%s", (prereqs["subject_id"],)
    ).fetchone()[0]
    assert count == 0


# --- P30.2a (ADR-104): camera-registry predicates over real PG18+PostGIS -------------


def _seed_camera_predicate(conn: object, predicate_id: str) -> None:
    # The FK row PgClaimSink auto-registers for a connector predicate (a placeholder in
    # the DB; the resolver's epistemics come from the generated registry, ADR-104).
    conn.execute(
        "INSERT INTO vocab_resolution_strategy(strategy_id,definition) "
        "VALUES('authoritative_source_wins','fixture') ON CONFLICT DO NOTHING"
    )
    conn.execute(
        "INSERT INTO vocab_predicate"
        "(predicate_id,vocab_version,value_datatype,object_type,definition,"
        " volatility_class,half_life_days,resolution_strategy) "
        "VALUES(%s,'1.0.0','decimal','literal','fixture','MODERATE',365,"
        "'authoritative_source_wins') ON CONFLICT DO NOTHING",
        (predicate_id,),
    )


def _undated_camera_claim(
    conn: object, prereqs: dict, subject: object, value: float, capture_id: object
) -> object:
    """A registry-shaped claim: observed_at NULL (the connector keeps retrieval time out
    of the claim), evidenced by a camera_registry capture retrieved 2026-05-01."""
    claim_id = conn.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,value_text,"
        "value_num,raw_value,observed_at,observed_unknown_reason,source_reliability,"
        "claim_directness,artifact_integrity,asserted_by,assertion_rationale,ingest_run_id,"
        "rights_id,sensitivity_tier) "
        "VALUES(%s,'camera_latitude','literal','value',%s,%s,%s,NULL,"
        "'connector run did not record an observation time','R3','D2','I1',"
        "%s,'fixture',%s,%s,0) RETURNING claim_id",
        (
            subject,
            str(value),
            value,
            str(value),
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


def test_camera_coordinate_resolves_from_its_capture_time_and_reruns_plus_zero(
    conn: object,
) -> None:
    prereqs = seed_claim_prerequisites(conn)
    _seed_camera_predicate(conn, "camera_latitude")
    capture = _source_and_capture(conn, prereqs, "camera_registry", "camreg_fixture")
    subject = prereqs["subject_id"]
    _undated_camera_claim(conn, prereqs, subject, 35.4676, capture)

    first = materialize_resolutions(conn, subject=str(subject), as_of=date(2026, 9, 24))
    assert first.inserted == 1 and first.resolved == 1 and first.skipped_unresolvable == 0
    row = conn.execute(
        "SELECT value_num, strategy_id, contradiction_state, evidence_counts "
        "  FROM resolution WHERE subject_id=%s AND predicate_id='camera_latitude'",
        (subject,),
    ).fetchone()
    assert float(row[0]) == 35.4676
    assert row[1] == "latest_observation_wins"
    assert row[2] == "uncontested"
    # the capture-time dating is an inference and is labelled on the stored decision
    # (P31.7 / ADR-R9-RESIGHT: the LATEST sighting, now that re-sightings are linked).
    assert "SIG-RECON-008:observed_at=capture_retrieved_at_latest" in row[3]["rules_fired"]

    again = materialize_resolutions(conn, subject=str(subject), as_of=date(2026, 9, 24))
    assert again.inserted == 0 and again.skipped_existing == 1


def test_camera_coordinates_beyond_tolerance_are_materialized_unresolved(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    _seed_camera_predicate(conn, "camera_latitude")
    subject = prereqs["subject_id"]
    cap_a = _source_and_capture(conn, prereqs, "camera_registry", "camreg_a")
    cap_b = _source_and_capture(conn, prereqs, "camera_registry", "camreg_b")
    a = _undated_camera_claim(conn, prereqs, subject, 35.4676, cap_a)
    b = _undated_camera_claim(conn, prereqs, subject, 35.4776, cap_b)  # ~1.1 km apart

    summary = materialize_resolutions(conn, subject=str(subject), as_of=date(2026, 9, 24))
    assert summary.inserted == 1 and summary.unresolved == 1
    row = conn.execute(
        "SELECT winning_claim, contradiction_state, considered_claims "
        "  FROM resolution WHERE subject_id=%s AND predicate_id='camera_latitude'",
        (subject,),
    ).fetchone()
    assert row[0] is None  # no fabricated winner
    assert row[1] == "unresolved_conflict"  # the disagreement stays visible
    assert {str(x) for x in row[2]} == {str(a), str(b)}
