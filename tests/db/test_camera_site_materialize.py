# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Camera-site entity resolution over the real spine (P30.2b, ADR-105).

Exercises the ``camera_site_resolution`` sqitch change (deployed by the conftest
container) and the append-only materializer over PG18+PostGIS, AS the least-privilege
``sig_materialize`` role:

* the same_as decisions + run record are written with provenance; a re-run over the
  unchanged spine inserts **+0**;
* same-source records at one point are never merged; incompatible device classes are
  never candidates; sub-floor tiers are PROPOSED and enqueued once for review;
* the export's resolved-site metric reads the materialized clusters: N of M, N <= M.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date

import psycopg
import pytest
from exports.spine_export import run_spine_export
from resolution.camera_sites import CameraGoldPair, CameraGoldSet, CameraSiteRules
from resolution.camera_sites_pg import (
    materialize_camera_sites,
    read_camera_records,
    read_resolved_site_runs,
)
from resolution.gold_set import Adjudication, GoldLabel

ROLE = "sig_materialize"
# The fixture gold holds ONE holdout pair; the committed rules require 50 per tier, so the
# tests lower that floor explicitly (the production minimum is pinned in the unit tests).
RULES = replace(CameraSiteRules.from_data(), min_holdout_pairs=1)
PREDICATES = ("camera_latitude", "camera_longitude", "camera_external_ref", "camera_operator")


def _seed_predicates(cur) -> None:
    cur.execute(
        "INSERT INTO vocab_resolution_strategy(strategy_id,definition) "
        "VALUES('latest_observation_wins','fixture') ON CONFLICT DO NOTHING"
    )
    for pid in PREDICATES:
        cur.execute(
            "INSERT INTO vocab_predicate(predicate_id,vocab_version,value_datatype,object_type,"
            " definition,volatility_class,half_life_days,resolution_strategy) "
            "VALUES(%s,'1.0.0','string','literal','fixture','SLOW',730,"
            "'latest_observation_wins') ON CONFLICT DO NOTHING",
            (pid,),
        )


def _source_capture(cur, source_id: str, rights_id, run_id) -> object:
    cur.execute(
        "INSERT INTO source_registry(source_id,name,source_kind,default_reliability,"
        "reliability_justification,rights_id,custody_posture,compact_status,robots_policy,"
        "ingestion_permitted) VALUES(%s,%s,'registry','R2','fixture',%s,'MIRROR','granted',"
        "'obey',true)",
        (source_id, source_id, rights_id),
    )
    cur.execute(
        "INSERT INTO evidence_artifact(source_id,stable_locator,artifact_type,"
        "acquisition_method,primary_or_secondary,rights_id,capture_status) "
        "VALUES(%s,%s,'camera_registry','registry_api','primary',%s,'captured') "
        "RETURNING artifact_id",
        (source_id, f"urn:sig:p302b:{source_id}", rights_id),
    )
    artifact = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,media_type,"
        "retrieved_at,retrieved_by_run_id,ocfl_object_id,ocfl_version,storage_tier,"
        "capture_method,capture_tool_version,source_uri) VALUES(%s,%s,10,'application/json',"
        "'2026-09-01T00:00:00Z',%s,%s,'v1','public','registry_api','sig/0',%s) "
        "RETURNING capture_id",
        (artifact, f"d-{source_id}", run_id, f"urn:{source_id}", f"urn:{source_id}"),
    )
    return cur.fetchone()[0]


@pytest.fixture
def camera_spine(conn) -> dict[str, str]:
    """Seven observation-level camera records over four sources.

    a (DOT) ~ b (mirror) coincident — the same device; c (OSM) 300 m away; d, e: ONE
    source listing two devices at one point; f (ALPR) coincident with g (DOT) —
    incompatible device classes.
    """
    cur = conn.cursor()
    _seed_predicates(cur)
    cur.execute(
        "INSERT INTO rights_record(spdx_expression,redistributable,derivative_permitted,"
        "retrieval_date) VALUES('CC0-1.0','yes','yes','2026-01-01') RETURNING rights_id"
    )
    rights = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO ingest_run(connector_name,connector_version,code_commit,ruleset_version,"
        "vocab_version,parameters,environment,input_digests,status,finished_at) "
        "VALUES('dot_511','0','sha','r1','1.0.0','{}','{}','{}','succeeded',"
        "'2026-09-01T00:00:00Z') RETURNING run_id"
    )
    run = cur.fetchone()[0]
    cur.execute("INSERT INTO entity(entity_type) VALUES('person') RETURNING entity_id")
    author = cur.fetchone()[0]
    caps = {
        s: _source_capture(cur, s, rights, run)
        for s in ("dot_511_zz", "camreg_zz_mirror", "camreg_osm_zz", "camreg_zz_flock")
    }
    ids: dict[str, str] = {}

    def record(key, source, lat, lon, ref, operator):
        cur.execute("INSERT INTO entity(entity_type) VALUES('deployment') RETURNING entity_id")
        subject = cur.fetchone()[0]
        ids[key] = str(subject)
        for pid, value in (
            ("camera_latitude", lat),
            ("camera_longitude", lon),
            ("camera_external_ref", ref),
            ("camera_operator", operator),
        ):
            cur.execute(
                "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,value_text,"
                "raw_value,observed_at,source_reliability,claim_directness,artifact_integrity,"
                "asserted_by,assertion_rationale,ingest_run_id,rights_id,sensitivity_tier) "
                "VALUES(%s,%s,'literal','value',%s,%s,'2026-09-01T00:00:00Z','R2','D2','I1',"
                "%s,'fixture',%s,%s,0) RETURNING claim_id",
                (subject, pid, value, value, author, run, rights),
            )
            claim = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO claim_evidence(claim_id,capture_id,role) VALUES(%s,%s,'establishes')",
                (claim, caps[source]),
            )

    dot = "Zed Department of Transportation"
    record("a", "dot_511_zz", "35.4676000", "-97.5164000", "101", dot)
    record("b", "camreg_zz_mirror", "35.4676030", "-97.5164010", "9001", "community mirror")
    record("c", "camreg_osm_zz", "35.4703000", "-97.5164000", "77", "OpenStreetMap")
    record("d", "dot_511_zz", "35.4800000", "-97.5200000", "102", dot)
    record("e", "dot_511_zz", "35.4800010", "-97.5200000", "103", dot)
    record("f", "camreg_zz_flock", "35.4900000", "-97.5300000", "1", "ALPR camera layer")
    record("g", "dot_511_zz", "35.4900020", "-97.5300000", "104", dot)
    return ids


def _gold(ids: dict[str, str], label: GoldLabel) -> CameraGoldSet:
    left, right = sorted((ids["a"], ids["b"]))
    dated = date(2026, 9, 24)
    adjs = (
        Adjudication("t1", "agent:seed", label, dated, "2"),
        Adjudication("t1", "llm:x", label, dated, "2"),
    )
    pair = CameraGoldPair("t1", left, right, "s", -0.3, "coincident", {}, adjs, True)
    return CameraGoldSet("test-gold", "2", "agent:seed", "llm:x", (pair,))


def test_sqitch_change_deployed(conn) -> None:
    conn.execute("SELECT run_key FROM camera_site_run WHERE false")
    conn.execute("SELECT input_digest, disposition FROM camera_site_match WHERE false")
    assert conn.execute(
        "SELECT 1 FROM pg_indexes WHERE indexname='camera_site_match_input_digest_key'"
    ).fetchone()


def test_records_are_read_one_per_subject(conn, camera_spine) -> None:
    recs = {r.subject_id: r for r in read_camera_records(conn)}
    a = recs[camera_spine["a"]]
    assert a.source_id == "dot_511_zz" and a.external_ref == "101"
    assert a.latitude == pytest.approx(35.4676) and len(a.claim_ids) == 3  # lat, lon, ref


def test_materialize_as_the_least_privilege_role_and_rerun_plus_zero(conn, camera_spine) -> None:
    gold = _gold(camera_spine, GoldLabel.MATCH)
    first = materialize_camera_sites(conn, role=ROLE, gold=gold, threshold=0.98, rules=RULES)
    assert first["auto_write_tiers"] == [3]
    # M = 7 records; one same-device merge (a~b) -> N = 6.
    assert first["observation_count_M"] == 7 and first["resolved_site_count_N"] == 6
    assert first["auto_write_decisions"] == 1 and first["run_record_inserted"] is True
    # hard constraint (a): d/e (one source, one point) are never a decision;
    # hard constraint (b): f (ALPR) / g (traffic) are never a candidate.
    rows = conn.execute(
        "SELECT left_entity::text, right_entity::text, disposition, match_tier, "
        "       match_evidence, cardinality(evidence_claims) FROM camera_site_match"
    ).fetchall()
    pairs = {tuple(sorted((r[0], r[1]))) for r in rows}
    assert tuple(sorted((camera_spine["d"], camera_spine["e"]))) not in pairs
    assert tuple(sorted((camera_spine["f"], camera_spine["g"]))) not in pairs
    auto = [r for r in rows if r[2] == "auto_write"]
    assert len(auto) == 1 and auto[0][3] == 3
    assert auto[0][4]["rule"] == "3g:coincident_point" and auto[0][5] == 6  # cites its claims
    assert first["incompatible_class_pairs_blocked"] == 1

    again = materialize_camera_sites(conn, role=ROLE, gold=gold, threshold=0.98, rules=RULES)
    assert again["inserted"] == 0
    assert again["skipped_existing"] == first["inserted"]
    assert again["run_record_inserted"] is False
    assert again["run_key"] == first["run_key"]


def test_the_role_cannot_update_or_delete_decisions(conn, camera_spine) -> None:
    gold = _gold(camera_spine, GoldLabel.MATCH)
    materialize_camera_sites(conn, role=ROLE, gold=gold, rules=RULES)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("UPDATE camera_site_match SET disposition = 'proposed'")
    conn.rollback()


def test_a_sub_floor_tier_is_proposed_and_enqueued_once(conn, camera_spine) -> None:
    gold = _gold(camera_spine, GoldLabel.NOT_ENOUGH_INFORMATION)
    first = materialize_camera_sites(conn, role=ROLE, gold=gold, threshold=0.98, rules=RULES)
    assert first["auto_write_tiers"] == [] and first["resolved_site_count_N"] == 7  # honest N=M
    assert first["proposed_decisions"] >= 1 and first["review_items_enqueued"] >= 1
    items = conn.execute(
        "SELECT item_id, kind, payload FROM review_item WHERE item_id LIKE 'er_match:camera_site:%'"
    ).fetchall()
    assert items and all(i[1] == "er_match" for i in items)
    again = materialize_camera_sites(conn, role=ROLE, gold=gold, threshold=0.98, rules=RULES)
    assert again["review_items_enqueued"] == 0  # one stable item per pair


def test_the_export_reads_the_clusters_n_of_m(conn, camera_spine) -> None:
    gold = _gold(camera_spine, GoldLabel.MATCH)
    materialize_camera_sites(conn, role=ROLE, gold=gold, rules=RULES)
    conn.execute("RESET ROLE")
    runs = read_resolved_site_runs(conn)
    assert len(runs) == 1 and len(runs[0]["auto_write_edges"]) == 1
    assert (runs[0]["observation_count"], runs[0]["cluster_count"]) == (7, 6)
    export = run_spine_export(conn, as_of="2026-09-24", note="p30.2b", spine_label="seeded")
    coverage = json.loads(export.web_artifacts["web/coverage.json"])
    resolved = next(m for m in coverage if m["id"] == "resolved_sites")
    assert resolved["value"].startswith("6 resolved sites (from 7 observation-level records")
    assert resolved["is_population_total"] is False
