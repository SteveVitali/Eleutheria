# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Docker-gated seeded-spine run of the quality harness (P34.44a, SIG-CONF-006/
007/008/013 — the fixture-verified acceptance criterion).

Seeds a small, fully-controlled spine on a real PG18+PostGIS testcontainer and
runs ``ops.quality.run_quality_probe`` (placement M) against it: every
implemented M check measures real rows, both record kinds are emitted with
evaluated counts, the seeded GQ-24 violation fails the run (enforce), and a
check whose population was never seeded fails rather than passing vacuously
(SIG-ENG-042). Read-only throughout: every evaluator is SELECT-only and the
fixture's writes are rolled back by the ``conn`` fixture.
"""

from __future__ import annotations

import pytest
from ops.quality import EvalContext, probe_run_record, run_quality_probe


def _pred(cur, predicate_id: str, object_type: str = "literal") -> None:
    cur.execute(
        "INSERT INTO vocab_resolution_strategy(strategy_id,definition) "
        "VALUES('authoritative_source_wins','fixture') ON CONFLICT DO NOTHING"
    )
    cur.execute(
        "INSERT INTO vocab_predicate"
        "(predicate_id,vocab_version,value_datatype,object_type,definition,"
        " volatility_class,half_life_days,resolution_strategy) "
        "VALUES(%s,'1.0.0','string',%s,'fixture','MODERATE',365,"
        "'authoritative_source_wins') ON CONFLICT DO NOTHING",
        (predicate_id, object_type),
    )


def _entity(cur, entity_type: str = "physical_asset") -> str:
    cur.execute(
        "INSERT INTO entity(entity_type) VALUES(%s) RETURNING entity_id",
        (entity_type,),
    )
    return str(cur.fetchone()[0])


def _rights(cur) -> str:
    cur.execute(
        "INSERT INTO rights_record(spdx_expression,redistributable,"
        "derivative_permitted,retrieval_date) VALUES('CC0-1.0','yes','yes','2026-01-01') "
        "RETURNING rights_id"
    )
    return str(cur.fetchone()[0])


def _run(cur, connector: str, finished: str) -> str:
    cur.execute(
        "INSERT INTO ingest_run(connector_name,connector_version,code_commit,"
        "ruleset_version,vocab_version,parameters,environment,input_digests,"
        "finished_at) VALUES(%s,'0','sha','r1','1.0.0','{}','{}','{}',%s) "
        "RETURNING run_id",
        (connector, finished),
    )
    return str(cur.fetchone()[0])


def _source(cur, source_id: str, rights_id: str) -> None:
    cur.execute(
        "INSERT INTO source_registry(source_id,name,source_kind,default_reliability,"
        "reliability_justification,rights_id,custody_posture,compact_status,"
        "robots_policy) VALUES(%s,%s,'scraper','R2','fixture',%s,'MIRROR','ok','respect')",
        (source_id, source_id, rights_id),
    )


def _capture(cur, artifact_id: str, run_id: str) -> str:
    cur.execute(
        "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,media_type,"
        "retrieved_at,retrieved_by_run_id,ocfl_object_id,ocfl_version,capture_method,"
        "capture_tool_version) VALUES(%s,'digest-x',100,'text/html','2026-01-01',%s,"
        "'ocfl:x','v1','GET','t1') RETURNING capture_id",
        (artifact_id, run_id),
    )
    return str(cur.fetchone()[0])


def _artifact(cur, source_id: str, locator: str, rights_id: str) -> str:
    cur.execute(
        "INSERT INTO evidence_artifact(source_id,stable_locator,artifact_type,"
        "acquisition_method,primary_or_secondary,rights_id,capture_status) "
        "VALUES(%s,%s,'html','GET','primary',%s,'captured') RETURNING artifact_id",
        (source_id, locator, rights_id),
    )
    return str(cur.fetchone()[0])


def _claim(
    cur,
    *,
    subject: str,
    predicate: str,
    run_id: str,
    rights_id: str,
    author: str,
    capture_id: str | None = None,
    value_text: str | None = None,
    value_num: float | None = None,
    value_geom: str | None = None,
    object_entity: str | None = None,
) -> str:
    cur.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,value_text,"
        "value_num,value_geom,object_entity,raw_value,observed_at,source_reliability,"
        "claim_directness,artifact_integrity,asserted_by,assertion_rationale,"
        "ingest_run_id,rights_id,sensitivity_tier) "
        "VALUES(%s,%s,%s,'value',%s,%s,%s,%s,%s,'2026-05-01','R1','D1','I1',"
        "%s,'fixture',%s,%s,0) RETURNING claim_id",
        (
            subject,
            predicate,
            "geometry" if value_geom else "literal",
            value_text or (value_geom or "v"),
            value_num,
            value_geom,
            object_entity,
            value_text or "raw",
            author,
            run_id,
            rights_id,
        ),
    )
    claim_id = str(cur.fetchone()[0])
    if capture_id:
        cur.execute(
            "INSERT INTO claim_evidence(claim_id,capture_id,role) VALUES(%s,%s,'establishes')",
            (claim_id, capture_id),
        )
    return claim_id


def _seed_spine(cur) -> dict[str, str]:
    for pred, ot in (
        ("camera_latitude", "quantity"),
        ("camera_longitude", "quantity"),
        ("camera_operator", "literal"),
        ("camera_status", "literal"),
        ("camera_geom", "geometry"),
    ):
        _pred(cur, pred, ot)
    cur.execute(
        "INSERT INTO vocab_confidence(confidence,definition) VALUES('high','h') "
        "ON CONFLICT DO NOTHING"
    )
    cur.execute(
        "INSERT INTO vocab_rationale(rationale_code,template) VALUES('single','t') "
        "ON CONFLICT DO NOTHING"
    )

    rights = _rights(cur)
    run1 = _run(cur, "fixture-a", "2026-01-01")
    run2 = _run(cur, "fixture-a", "2026-02-01")
    _source(cur, "src-a", rights)
    _source(cur, "src-b", rights)
    art_a = _artifact(cur, "src-a", "cap://a", rights)
    art_b = _artifact(cur, "src-b", "cap://b", rights)
    cap_a = _capture(cur, art_a, run1)
    cap_b = _capture(cur, art_b, run1)
    author = _entity(cur, "person")

    # GQ-05: one subject moving between run1 and run2 (> 0.0005°)
    subj = _entity(cur)
    for run, lat in ((run1, 1.0), (run2, 1.001)):
        _claim(
            cur,
            subject=subj,
            predicate="camera_latitude",
            run_id=run,
            rights_id=rights,
            author=author,
            capture_id=cap_a,
            value_text=str(lat),
            value_num=lat,
        )
        _claim(
            cur,
            subject=subj,
            predicate="camera_longitude",
            run_id=run,
            rights_id=rights,
            author=author,
            capture_id=cap_a,
            value_text="1.0",
            value_num=1.0,
        )

    # GQ-07 + GQ-21: a deployment with a publisher-literal operator
    deploy = _entity(cur, "deployment")
    op_claim = _claim(
        cur,
        subject=deploy,
        predicate="camera_operator",
        run_id=run1,
        rights_id=rights,
        author=author,
        capture_id=cap_a,
        value_text="Flock Safety",
    )

    # GQ-03: an exact repeat of (subject, predicate, value, source)
    dup_subj = _entity(cur)
    for _ in range(2):
        _claim(
            cur,
            subject=dup_subj,
            predicate="camera_status",
            run_id=run1,
            rights_id=rights,
            author=author,
            capture_id=cap_a,
            value_text="active",
        )

    # GQ-11: two source layers whose distinct points overlap within 1 m
    for src_cap, i in ((cap_a, 1), (cap_a, 2), (cap_b, 1), (cap_b, 2)):
        _claim(
            cur,
            subject=_entity(cur),
            predicate="camera_geom",
            run_id=run1,
            rights_id=rights,
            author=author,
            capture_id=src_cap,
            value_geom=f"SRID=4326;POINT(0 {i * 0.0000001})",
        )

    # GQ-15: one undated edge, one epoch-start edge, one live duplicate
    a, b, c, d = (_entity(cur) for _ in range(4))
    for _ in range(2):  # duplicate (a→b operates) — undated, counted twice
        cur.execute(
            "INSERT INTO relationship(from_entity,to_entity,edge_type,direction,"
            "valid_period,evidence_claim) VALUES(%s,%s,'operates','forward',"
            "tstzrange(NULL,NULL), %s)",
            (a, b, op_claim),
        )
    cur.execute(
        "INSERT INTO relationship(from_entity,to_entity,edge_type,direction,"
        "valid_period,valid_from_kind,evidence_claim) VALUES(%s,%s,'operates','forward',"
        "tstzrange('1970-01-01',NULL),'exact',%s)",
        (c, d, op_claim),
    )

    # GQ-13: one resolution over two disagreeing claims, uncontested, no dissent
    res_subj = _entity(cur)
    c1 = _claim(
        cur,
        subject=res_subj,
        predicate="camera_status",
        run_id=run1,
        rights_id=rights,
        author=author,
        capture_id=cap_a,
        value_text="active",
    )
    c2 = _claim(
        cur,
        subject=res_subj,
        predicate="camera_status",
        run_id=run1,
        rights_id=rights,
        author=author,
        capture_id=cap_b,
        value_text="inactive",
    )
    cur.execute(
        "INSERT INTO resolution(subject_id,predicate_id,value_kind,value_text,"
        "valid_period,considered_claims,contradiction_state,strategy_id,"
        "rationale_code,rationale_text,confidence,evidence_counts,resolver_version,"
        "ruleset_version) "
        "VALUES(%s,'camera_status','value','active',tstzrange('2026-01-01',NULL),"
        "ARRAY[%s,%s]::uuid[],'uncontested','authoritative_source_wins','single',"
        "'because','high','{}','v1','r1')",
        (res_subj, c1, c2),
    )

    # GQ-24: one inferential auto-write (tier 3g) in the LATEST completed run —
    # the lock's violation. A second, older run's inferential auto-write stays
    # on the append-only spine as detected history, never re-judged (P34.45).
    left, right = _entity(cur), _entity(cur)
    if right < left:
        left, right = right, left
    for rk, completed in (("rk0", "2026-09-01T00:00:00Z"), ("rk", "2026-10-01T00:00:00Z")):
        cur.execute(
            "INSERT INTO camera_site_run(run_key,ruleset_version,resolver_version,"
            "auto_write_tiers,observation_count,cluster_count,summary,completed_at) "
            "VALUES(%s,'v1','r1',ARRAY[3]::smallint[],2,1,'{}',%s)",
            (rk, completed),
        )
        cur.execute(
            "INSERT INTO camera_site_execution(execution_id,run_key,completed_at,"
            "input_count,summary) VALUES(gen_random_uuid(),%s,%s,2,'{}')",
            (rk, completed),
        )
    for rk in ("rk0", "rk"):
        cur.execute(
            "INSERT INTO camera_site_match(run_key,left_entity,right_entity,match_tier,"
            "tier_label,disposition,match_evidence,evidence_claims,ruleset_version,"
            "resolver_version,input_digest) VALUES(%s,%s,%s,3,'3g:coincident_point',"
            "'auto_write','{}',ARRAY[%s]::uuid[],'r1','v1',%s)",
            (rk, left, right, c1, f"digest-{rk}"),
        )
    return {"cap_a": cap_a, "run1": run1}


def test_m_run_over_seeded_spine(conn) -> None:
    cur = conn.cursor()
    _seed_spine(cur)
    report = run_quality_probe(EvalContext(conn=conn), placement="M", target="seeded-test-spine")
    rows = {c["id"]: c for c in report["checks"]}

    # Both record kinds, with evaluated counts (SIG-CONF-013)
    assert report["version"] == "sig.quality-report/1"
    probe = probe_run_record(report)
    assert probe["version"] == "sig.probe-run/1"
    assert all("evaluated" in c for c in probe["checks"])

    # The implemented M checks measured the seed
    assert rows["GQ-03"]["evaluated"] > 0 and rows["GQ-03"]["measured"] > 0
    assert rows["GQ-05"]["measured"] == 1.0  # the one comparable subject moved
    assert rows["GQ-07"]["measured"] == 1  # "Flock Safety" literal
    assert rows["GQ-11"]["measured"] == 1  # one violating layer pair
    assert rows["GQ-13"]["measured"] == 1  # one uncontested disagreement
    assert rows["GQ-15"]["measured"] == 4  # 2 undated + 1 epoch + 1 duplicate
    assert rows["GQ-18"]["measured"] == 1.0  # every claim is capture-bound
    assert rows["GQ-21"]["measured"] == 1.0  # the one deployment has an operator
    assert rows["GQ-24"]["measured"] == 1  # the seeded inferential auto-write
    # P34.45: the superseded run's inferential auto-write is detected and
    # disclosed, never deleted or re-judged
    assert rows["GQ-24"]["detail"]["latest_run_key"] == "rk"
    assert rows["GQ-24"]["detail"]["historical_inferential_auto_writes"] == 1

    # Enforce fails the run; ratchet improvements are recorded, not gated
    assert rows["GQ-24"]["outcome"] == "fail"
    assert report["summary"]["enforce_failures"] == ["GQ-24"]
    assert report["summary"]["overall"] == "fail"
    assert probe["overall"] == "fail"
    assert rows["GQ-07"]["improvement"] and rows["GQ-07"]["outcome"] == "pass"

    # Seam-deferred checks are honest not_evaluable, never silent skips
    for cid in ("GQ-02", "GQ-12", "GQ-23", "GQ-25", "GQ-26"):
        assert rows[cid]["outcome"] == "not_evaluable", cid
        assert rows[cid]["reason"]


def test_zero_evaluated_population_fails(conn) -> None:
    """SIG-ENG-042: an empty spine fails every check rather than reporting a
    vacuous pass — a scheduled job that measured nothing is not a success."""
    report = run_quality_probe(EvalContext(conn=conn), placement="M")
    rows = {c["id"]: c for c in report["checks"]}
    assert rows["GQ-24"]["outcome"] == "fail"
    assert "no vacuous pass" in rows["GQ-24"]["reason"]
    assert rows["GQ-21"]["outcome"] == "fail"


def test_readonly_session_posture(sig_database) -> None:
    """connect_readonly opens the audit-posture session (SIG-CONF-008)."""
    from ops.quality import connect_readonly

    dsn = (
        f"host={sig_database['host']} port={sig_database['port']} "
        f"user={sig_database['user']} password={sig_database['password']} "
        f"dbname={sig_database['dbname']}"
    )
    with connect_readonly(dsn) as c:
        ro = c.execute("SHOW default_transaction_read_only").fetchone()[0]
        timeout = c.execute("SHOW statement_timeout").fetchone()[0]
        import psycopg

        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            c.execute("CREATE TABLE should_not_exist(x int)")
    assert ro == "on"
    assert timeout == "1min"
