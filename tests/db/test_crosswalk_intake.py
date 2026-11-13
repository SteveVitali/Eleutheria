# SPDX-License-Identifier: Apache-2.0
"""P37.46a — the crosswalk-intake apply: entity_identifier assertions with
asserted_by_claim provenance (R11-CONF-13 13a; insert-only, +0 re-run)."""

from __future__ import annotations

import uuid

from db.crosswalk_intake import (
    L2_DUPLICATE_BASELINE,
    REPORT_SCHEMA,
    assert_lane_identifiers,
    intake_plan,
    lane_schemes,
    org_identity_report,
)
from conftest import seed_claim_prerequisites


def _org_subject(conn) -> str:
    eid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO entity(entity_id, entity_type) VALUES (%s::uuid, 'organization')",
        (eid,),
    )
    conn.execute(
        "INSERT INTO organization(entity_id, organization_type)"
        " VALUES (%s::uuid, 'us.org')",
        (eid,),
    )
    return eid


def _claim(conn, prereqs, *, subject: str, scheme: str, value: str) -> str:
    cid = conn.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,"
        "value_text,value_json,raw_value,observed_at,source_reliability,"
        "claim_directness,artifact_integrity,asserted_by,assertion_rationale,"
        "ingest_run_id,rights_id,sensitivity_tier) "
        "VALUES(%s::uuid,'external_id','literal','value',%s,%s::jsonb,%s,"
        "'2026-11-13','R1','D1','I1',%s,'fixture',%s,%s,0) RETURNING claim_id",
        (
            subject,
            value,
            f'{{"scheme": "{scheme}", "value": "{value}"}}',
            value,
            prereqs["author_id"],
            prereqs["run_id"],
            prereqs["rights_id"],
        ),
    ).fetchone()[0]
    return str(cid)


def test_lane_vocabulary() -> None:
    lanes = lane_schemes()
    assert lanes["sam_uei"] == "us.sam.uei"
    assert lanes["census_geoid"] == "us.census.geoid"
    assert lanes["wikidata_qid"] == "wikidata.qid"
    assert lanes["ori"] == "us.fbi.ori"


def test_assert_writes_entity_identifier_with_provenance(conn) -> None:
    pre = seed_claim_prerequisites(conn)
    eid = _org_subject(conn)
    cid = _claim(conn, pre, subject=eid, scheme="wikidata.qid", value="Q4915")
    report = assert_lane_identifiers(conn, schemes=["wikidata.qid"], apply=True)
    assert report.asserted == 1
    row = conn.execute(
        "SELECT entity_id::text, scheme, value, asserted_by_claim::text "
        "FROM entity_identifier WHERE entity_id = %s::uuid",
        (eid,),
    ).fetchone()
    assert row == (eid, "wikidata.qid", "Q4915", cid)


def test_rerun_is_plus_zero(conn) -> None:
    pre = seed_claim_prerequisites(conn)
    eid = _org_subject(conn)
    _claim(conn, pre, subject=eid, scheme="us.census.geoid", value="4046250000")
    first = assert_lane_identifiers(conn, schemes=["us.census.geoid"], apply=True)
    second = assert_lane_identifiers(conn, schemes=["us.census.geoid"], apply=True)
    assert first.asserted == 1 and second.asserted == 0


def test_non_org_subject_is_skipped(conn) -> None:
    pre = seed_claim_prerequisites(conn)
    eid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO entity(entity_id, entity_type) VALUES (%s::uuid, 'deployment')",
        (eid,),
    )
    _claim(conn, pre, subject=eid, scheme="wikidata.qid", value="Q9999")
    report = assert_lane_identifiers(conn, schemes=["wikidata.qid"], apply=True)
    assert report.scanned == 0


def test_dry_run_writes_nothing(conn) -> None:
    pre = seed_claim_prerequisites(conn)
    eid = _org_subject(conn)
    _claim(conn, pre, subject=eid, scheme="us.sam.uei", value="ZK12AB34CD56")
    report = assert_lane_identifiers(conn, schemes=["us.sam.uei"], apply=False)
    assert report.scanned == 1
    assert (
        conn.execute(
            "SELECT count(*) FROM entity_identifier WHERE entity_id = %s::uuid", (eid,)
        ).fetchone()[0]
        == 0
    )


def test_report_measures_fall_vs_l2(conn) -> None:
    pre = seed_claim_prerequisites(conn)
    e1, e2 = _org_subject(conn), _org_subject(conn)
    conn.execute(
        "UPDATE organization SET cached_canonical_name='X PD'"
        " WHERE entity_id IN (%s::uuid, %s::uuid)",
        (e1, e2),
    )
    _claim(conn, pre, subject=e1, scheme="us.fbi.ori", value="OK0261100")
    _claim(conn, pre, subject=e2, scheme="us.fbi.ori", value="OK0261100")
    assert_lane_identifiers(conn, schemes=["us.fbi.ori"], apply=True)
    rep = org_identity_report(conn)
    assert rep["record_type"] == REPORT_SCHEMA
    assert rep["identifier_shared_entity_pairs"] >= 1
    assert rep["baseline_l2"] == L2_DUPLICATE_BASELINE
    assert rep["rate_fell_vs_l2"] in (True, False, None)


def test_plan_counts_pending(conn) -> None:
    pre = seed_claim_prerequisites(conn)
    eid = _org_subject(conn)
    _claim(conn, pre, subject=eid, scheme="wikidata.qid", value="Q1")
    plan = intake_plan(conn, schemes=["wikidata.qid"])
    assert plan["pending"].get("wikidata.qid", 0) >= 1
