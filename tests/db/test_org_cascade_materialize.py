# SPDX-License-Identifier: Apache-2.0
"""P37.46b — the organisation cascade materializer over real PG18+PostGIS
(R11-CONF-13 13b; SIG-CONF-004): append-only organization_match records
(tiers 0-1 same_as auto-link, tier-2 possibly_same surfaced), the run +
execution markers, the +0 re-run contract, and the identity report's
after-links duplicate measure."""

from __future__ import annotations

import uuid

from conftest import seed_claim_prerequisites
from db.crosswalk_intake import org_identity_report
from resolution.org_cascade_pg import (
    materialize_org_cascade,
    read_org_candidates,
    read_org_cascade_runs,
)


def _org_subject(conn, *, org_class: str = "us.le.municipal_police") -> str:
    eid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO entity(entity_id, entity_type) VALUES (%s::uuid, 'organization')",
        (eid,),
    )
    conn.execute(
        "INSERT INTO organization(entity_id, organization_type) VALUES (%s::uuid, %s)",
        (eid, org_class),
    )
    return eid


def _claim(
    conn, prereqs, *, subject: str, predicate: str, value: str, scheme: str | None = None
) -> str:
    value_json = (
        f'{{"scheme": "{scheme}", "value": "{value}"}}' if scheme else f'{{"value": "{value}"}}'
    )
    cid = conn.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,"
        "value_text,value_json,raw_value,observed_at,source_reliability,"
        "claim_directness,artifact_integrity,asserted_by,assertion_rationale,"
        "ingest_run_id,rights_id,sensitivity_tier) "
        "VALUES(%s::uuid,%s,'literal','value',%s,%s::jsonb,%s,"
        "'2026-11-13','R1','D1','I1',%s,'fixture',%s,%s,0) RETURNING claim_id",
        (
            subject,
            predicate,
            value,
            value_json,
            value,
            prereqs["author_id"],
            prereqs["run_id"],
            prereqs["rights_id"],
        ),
    ).fetchone()[0]
    return str(cid)


def _ident(conn, prereqs, entity: str, scheme: str, value: str) -> str:
    """Assert one entity_identifier row with its provenance claim."""
    cid = _claim(conn, prereqs, subject=entity, predicate="external_id", value=value, scheme=scheme)
    conn.execute(
        "INSERT INTO entity_identifier(entity_id, scheme, value, asserted_by_claim) "
        "VALUES (%s::uuid, %s, %s, %s::uuid)",
        (entity, scheme, value, cid),
    )
    return cid


def _crosswalk_entry(conn, prereqs, key: str, ids: list[tuple[str, str]]) -> str:
    """An org_crosswalk_entry entity: the upstream multi-scheme assertion."""
    eid = _org_subject(conn, org_class="us.org")
    conn.execute(
        "INSERT INTO entity_identifier(entity_id, scheme, value, asserted_by_claim) "
        "VALUES (%s::uuid, 'sig.connector.subject', %s, NULL)",
        (eid, f"org_crosswalk_entry:ori_fips:{key}"),
    )
    for scheme, value in ids:
        _ident(conn, prereqs, eid, scheme, value)
    return eid


def _match_rows(conn, run_key: str):
    return conn.execute(
        "SELECT left_entity::text, right_entity::text, relation_type, match_tier, "
        " disposition, match_evidence, evidence_claims::text[] "
        "FROM organization_match WHERE run_key = %s ORDER BY left_entity, right_entity",
        (run_key,),
    ).fetchall()


def _latest_run_key(conn) -> str:
    return str(
        conn.execute(
            "SELECT run_key FROM organization_execution "
            " ORDER BY completed_at DESC, execution_id DESC LIMIT 1"
        ).fetchone()[0]
    )


def test_tier0_materializes_match_records(conn) -> None:
    pre = seed_claim_prerequisites(conn)
    a, b = _org_subject(conn), _org_subject(conn)
    ca = _ident(conn, pre, a, "wikidata.qid", "Q4915")
    cb = _ident(conn, pre, b, "wikidata.qid", "Q4915")
    summary = materialize_org_cascade(conn)
    run_key = summary["run_key"]
    rows = _match_rows(conn, run_key)
    pair = [r for r in rows if {r[0], r[1]} == {a, b}]
    assert len(pair) == 1
    left, right, rel, tier, disp, ev, claims = pair[0]
    assert rel == "same_as" and tier == 0 and disp == "auto_link"
    assert ev["rule"] == "exact_shared_canonical_identifier"
    assert set(claims) == {ca, cb}
    run = conn.execute(
        "SELECT organization_count, link_count, possibly_same_count, auto_link_tiers "
        "FROM organization_run WHERE run_key = %s",
        (run_key,),
    ).fetchone()
    assert run[0] == summary["organizations"]
    assert run[1] == 1 and run[2] == 0 and list(run[3]) == [0, 1]


def test_rerun_is_plus_zero_and_appends_execution(conn) -> None:
    pre = seed_claim_prerequisites(conn)
    a, b = _org_subject(conn), _org_subject(conn)
    _ident(conn, pre, a, "us.sam.uei", "ZK12AB34CD56")
    _ident(conn, pre, b, "us.sam.uei", "ZK12AB34CD56")
    first = materialize_org_cascade(conn)
    second = materialize_org_cascade(conn)
    assert first["run_key"] == second["run_key"]
    assert first["inserted"] >= 1 and second["inserted"] == 0
    assert second["skipped_existing"] == first["inserted"]
    assert second["execution_appended"] is True
    assert second["execution_id"] != first["execution_id"]
    executions = conn.execute(
        "SELECT count(*) FROM organization_execution WHERE run_key = %s",
        (first["run_key"],),
    ).fetchone()[0]
    assert executions == 2


def test_execution_id_retry_is_plus_zero(conn) -> None:
    pre = seed_claim_prerequisites(conn)
    a, b = _org_subject(conn), _org_subject(conn)
    _ident(conn, pre, a, "wikidata.qid", "Q7")
    _ident(conn, pre, b, "wikidata.qid", "Q7")
    exec_id = str(uuid.uuid4())
    first = materialize_org_cascade(conn, execution_id=exec_id)
    second = materialize_org_cascade(conn, execution_id=exec_id)
    assert second["execution_appended"] is False
    assert first["execution_id"] == exec_id == second["execution_id"]


def test_tier1_via_crosswalk_entry(conn) -> None:
    pre = seed_claim_prerequisites(conn)
    c = _crosswalk_entry(
        conn, pre, "OK0261100", [("us.fbi.ori", "OK0261100"), ("us.census.geoid", "4046250000")]
    )
    a, b = _org_subject(conn), _org_subject(conn)
    _ident(conn, pre, a, "us.fbi.ori", "OK0261100")
    _ident(conn, pre, b, "us.census.geoid", "4046250000")
    summary = materialize_org_cascade(conn)
    rows = _match_rows(conn, summary["run_key"])
    by_pair = {(r[0], r[1]): r for r in rows}
    bridged = by_pair.get(tuple(sorted((a, b))))
    assert bridged is not None
    assert bridged[2] == "same_as" and bridged[3] == 1 and bridged[4] == "auto_link"
    assert bridged[5]["crosswalk_entity"] == c
    assert bridged[5]["rule"] == "established_upstream_crosswalk"
    # The entry's own edges are literal shared identifiers — tier 0.
    for entity in (a, b):
        edge = by_pair.get(tuple(sorted((entity, c))))
        assert edge is not None and edge[3] == 0


def test_tier2_surfaced_never_linked(conn) -> None:
    pre = seed_claim_prerequisites(conn)
    a, b = _org_subject(conn), _org_subject(conn)
    for eid in (a, b):
        conn.execute(
            "UPDATE organization SET cached_canonical_name = 'Tulsa Police Department' "
            "WHERE entity_id = %s::uuid",
            (eid,),
        )
        _claim(conn, pre, subject=eid, predicate="organization_jurisdiction", value="OK")
    summary = materialize_org_cascade(conn)
    rows = _match_rows(conn, summary["run_key"])
    pair = [r for r in rows if {r[0], r[1]} == {a, b}]
    assert len(pair) == 1
    assert pair[0][2] == "possibly_same" and pair[0][3] == 2 and pair[0][4] == "surfaced"
    assert summary["possibly_same_pairs"] >= 1
    # Surfaced, never linked: no same_as row for the pair.
    assert not any(r[2] == "same_as" and {r[0], r[1]} == {a, b} for r in rows)


def test_civil_ori_never_links(conn) -> None:
    pre = seed_claim_prerequisites(conn)
    a, b = _org_subject(conn), _org_subject(conn)
    _ident(conn, pre, a, "us.fbi.ori", "OK026110A")
    _ident(conn, pre, b, "us.fbi.ori", "OK026110A")
    summary = materialize_org_cascade(conn)
    rows = _match_rows(conn, summary["run_key"])
    assert not any({r[0], r[1]} == {a, b} and r[2] == "same_as" for r in rows)


def test_read_candidates_assembles_surface(conn) -> None:
    pre = seed_claim_prerequisites(conn)
    a = _org_subject(conn)
    _ident(conn, pre, a, "wikidata.qid", "Q4915")
    conn.execute(
        "UPDATE organization SET cached_canonical_name = 'Enid Police Department' "
        "WHERE entity_id = %s::uuid",
        (a,),
    )
    _claim(conn, pre, subject=a, predicate="organization_jurisdiction", value="OK")
    _crosswalk_entry(conn, pre, "X1", [("us.census.geoid", "4012345")])
    recs = {r.entity_id: r for r in read_org_candidates(conn)}
    rec = recs[a]
    assert rec.name == "Enid Police Department" and rec.state == "OK"
    assert any(i.scheme == "wikidata.qid" and i.value == "Q4915" for i in rec.identifiers)
    assert not rec.is_crosswalk_entry
    assert any(r.is_crosswalk_entry for r in recs.values())


def test_read_seam_latest_completed_run(conn) -> None:
    pre = seed_claim_prerequisites(conn)
    a, b = _org_subject(conn), _org_subject(conn)
    _ident(conn, pre, a, "us.census.geoid", "4046250000")
    _ident(conn, pre, b, "us.census.geoid", "4046250000")
    summary = materialize_org_cascade(conn)
    runs = read_org_cascade_runs(conn)
    assert len(runs) == 1
    run = runs[0]
    assert run["run_key"] == summary["run_key"]
    assert run["link_count"] == 1
    assert any(
        link["relation_type"] == "same_as" and {link["left"], link["right"]} == {a, b}
        for link in run["links"]
    )


def test_report_cascade_block_after_materialize(conn) -> None:
    pre = seed_claim_prerequisites(conn)
    a, b = _org_subject(conn), _org_subject(conn)
    for eid in (a, b):
        conn.execute(
            "UPDATE organization SET cached_canonical_name = 'Enid Police Department' "
            "WHERE entity_id = %s::uuid",
            (eid,),
        )
    # Before the run: no cascade has completed — the report admits it.
    before = org_identity_report(conn)
    assert before["cascade"] is not None and before["cascade"]["run_key"] is None
    _ident(conn, pre, a, "us.fbi.ori", "OK0261100")
    _ident(conn, pre, b, "us.fbi.ori", "OK0261100")
    materialize_org_cascade(conn)
    after = org_identity_report(conn)
    casc = after["cascade"]
    assert casc is not None and casc["run_key"]
    assert casc["same_as_pairs"] >= 1
    assert casc["linked_organizations"] >= 2
    assert casc["resolved_organizations"] < after["organization_entities"]
    # The pair's name group resolves to ONE cluster: the after-links
    # duplicate count falls below the raw name-duplicate count.
    assert casc["name_duplicate_groups_after_links"] <= after["name_duplicate_groups"]
