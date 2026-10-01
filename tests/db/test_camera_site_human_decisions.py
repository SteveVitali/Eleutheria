# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Human review decisions into camera-site clustering over the real spine (P31.11).

Exercises the ``camera_site_human_decisions`` sqitch change and the P31.11 wiring
(ADR-R9-HUMANER) over PG18+PostGIS, as the least-privilege ``sig_materialize``
role:

* ``accept`` verdicts land as ``human_accept`` same_as edges (``decided_by`` the
  curator) and cluster; ``reject`` lands as ``human_reject``/``cannot_link`` and
  never does; conflicting curators stay ``proposed`` and are routed back under a
  ``camera_site_conflict:`` item whose later clean adjudication governs;
* an accept that would violate a hard constraint is recorded ``refused`` and
  never applied; a verdict on a pair absent from the run is counted, not invented;
* duplicate-target lineage (identical captured content digests / row-identical
  records) merges the republished row — the narrow constraint-(a) exception —
  while genuinely distinct same-source devices stay separate;
* a zero-decision run is identical to the pre-wiring pipeline and re-runs +0.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date

import pytest
from resolution.camera_sites import CameraGoldPair, CameraGoldSet, CameraSiteRules
from resolution.camera_sites_pg import (
    materialize_camera_sites,
    read_camera_records,
    read_resolved_site_runs,
)
from resolution.gold_set import Adjudication, GoldLabel

ROLE = "sig_materialize"
RULES = replace(CameraSiteRules.from_data(), min_holdout_pairs=1)
PREDICATES = (
    "camera_latitude",
    "camera_longitude",
    "camera_external_ref",
    "camera_name",
    "camera_operator",
)


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


@pytest.fixture
def spine_ctx(conn) -> dict[str, object]:
    """The fixture spine: two coincident records a(s1)/b(s2), two same-source
    records d/e at one point, plus the plumbing (rights, run, captures) to mint
    records with chosen target ids / capture digests."""
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
    ctx: dict[str, object] = {
        "rights": rights,
        "run": run,
        "author": author,
        "ids": {},
        "sources": set(),
    }

    caps: dict[tuple[str, str], object] = {}

    def source(source_id: str, digest: str) -> object:
        """One artifact+capture per (source, content digest); cached so two records
        citing the same fetched bytes cite the same capture."""
        key = (source_id, digest)
        if key in caps:
            return caps[key]
        cur.execute(
            "INSERT INTO source_registry(source_id,name,source_kind,default_reliability,"
            "reliability_justification,rights_id,custody_posture,compact_status,"
            "robots_policy,ingestion_permitted) VALUES(%s,%s,'registry','R2','fixture',%s,"
            "'MIRROR','granted','obey',true) ON CONFLICT DO NOTHING",
            (source_id, source_id, rights),
        )
        cur.execute(
            "INSERT INTO evidence_artifact(source_id,stable_locator,artifact_type,"
            "acquisition_method,primary_or_secondary,rights_id,capture_status) "
            "VALUES(%s,%s,'camera_registry','registry_api','primary',%s,'captured') "
            "RETURNING artifact_id",
            (source_id, f"urn:sig:p3111:{source_id}:{len(caps)}", rights),
        )
        artifact = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,media_type,"
            "retrieved_at,retrieved_by_run_id,ocfl_object_id,ocfl_version,storage_tier,"
            "capture_method,capture_tool_version,source_uri) VALUES(%s,%s,10,"
            "'application/json','2026-09-01T00:00:00Z',%s,%s,'v1','public','registry_api',"
            "'sig/0',%s) RETURNING capture_id",
            (artifact, digest, run, f"urn:{source_id}:{len(caps)}", f"urn:{source_id}"),
        )
        caps[key] = cur.fetchone()[0]
        return caps[key]

    def record(
        key: str,
        source_id: str,
        lat: str,
        lon: str,
        ref: str,
        name: str,
        *,
        digest: str | None = None,
        target: str | None = None,
    ) -> str:
        cap = source(source_id, digest or f"d-{source_id}-{ref}")
        cur.execute("INSERT INTO entity(entity_type) VALUES('deployment') RETURNING entity_id")
        subject = str(cur.fetchone()[0])
        ctx["ids"][key] = subject  # type: ignore[index]
        if target is not None:
            cur.execute(
                "INSERT INTO entity_identifier(entity_id,scheme,value) "
                "VALUES(%s,'sig.connector.subject',%s)",
                (subject, f"traffic_camera:{source_id}:{target}:{ref}"),
            )
        for pid, value in (
            ("camera_latitude", lat),
            ("camera_longitude", lon),
            ("camera_external_ref", ref),
            ("camera_name", name),
            ("camera_operator", f"operator-{source_id}"),
            # a per-source distinguishing operator so a shared-ref pair stays honest
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
                (claim, cap),
            )
        return subject

    # a (s1) ~ b (s2) coincident, shared upstream ref; d/e: one source, two
    # DISTINCT devices at one point (different refs).
    record("a", "camreg_zz_a", "35.4676000", "-97.5164000", "101", "I-5 / Gilman")
    record("b", "camreg_zz_b", "35.4676030", "-97.5164010", "101", "I-5 / Gilman")
    record("d", "camreg_zz_a", "35.4800000", "-97.5200000", "7", "Gilman NB")
    record("e", "camreg_zz_a", "35.4800010", "-97.5200000", "8", "Gilman SB")
    ctx["record"] = record
    ctx["source"] = source
    return ctx


def _ids(ctx) -> dict[str, str]:
    return ctx["ids"]  # type: ignore[return-value]


def _gold_pair(left: str, right: str, label: GoldLabel) -> CameraGoldSet:
    dated = date(2026, 9, 24)
    adjs = (
        Adjudication("t1", "agent:seed", label, dated, "2"),
        Adjudication("t1", "llm:x", label, dated, "2"),
    )
    pair = CameraGoldPair("t1", *sorted((left, right)), "s", -0.3, "coincident", {}, adjs, True)
    return CameraGoldSet("test-gold", "2", "agent:seed", "llm:x", (pair,))


def _item_id(left: str, right: str, prefix: str = "er_match:camera_site") -> str:
    a, b = sorted((left, right))
    return f"{prefix}:{a}:{b}"


def _insert_item(cur, left: str, right: str, *, prefix="er_match:camera_site", tier=3) -> str:
    item_id = _item_id(left, right, prefix)
    cur.execute(
        "INSERT INTO review_item(item_id, kind, summary, payload) "
        "VALUES(%s, 'er_match', 'fixture', %s::jsonb) ON CONFLICT (item_id) DO NOTHING",
        (
            item_id,
            json.dumps(
                {
                    "left": left,
                    "right": right,
                    "tier": tier,
                    "tier_label": f"{tier}g:fixture",
                },
                sort_keys=True,
            ),
        ),
    )
    return item_id


def _decide(cur, item_id: str, decision: str, reviewer: str, at: str) -> None:
    cur.execute(
        "INSERT INTO review_decision(item_id, decision, reviewer, decided_at) "
        "VALUES(%s, %s, %s, %s::timestamptz)",
        (item_id, decision, reviewer, at),
    )


def _matches(conn, run_key: str) -> list[tuple]:
    return conn.execute(
        "SELECT left_entity::text, right_entity::text, relation_type, disposition, "
        "       decided_by, disposition_reason, match_tier, match_evidence "
        "  FROM camera_site_match WHERE run_key = %s ORDER BY left_entity",
        (run_key,),
    ).fetchall()


def test_widened_dispositions_and_materialize_grant(conn) -> None:
    # The CHECKs admit the new vocabulary; the materialize role reads+appends
    # review_decision and still may not UPDATE/DELETE it (append-only both ways).
    assert conn.execute(
        "SELECT has_table_privilege('sig_materialize','review_decision','SELECT') "
        " AND has_table_privilege('sig_materialize','review_decision','INSERT') "
        " AND NOT has_table_privilege('sig_materialize','review_decision','UPDATE') "
        " AND NOT has_table_privilege('sig_materialize','review_decision','DELETE')"
    ).fetchone()[0]


def test_a_human_accept_clusters_the_pair_and_names_the_curator(conn, spine_ctx) -> None:
    ids = _ids(spine_ctx)
    gold = _gold_pair(ids["a"], ids["b"], GoldLabel.NOT_ENOUGH_INFORMATION)
    first = materialize_camera_sites(conn, role=ROLE, gold=gold, threshold=0.98, rules=RULES)
    assert first["resolved_site_count_N"] == 4  # a/b proposed, not merged (NEI holdout)

    item = _insert_item(conn.cursor(), ids["a"], ids["b"])
    _decide(conn.cursor(), item, "accept", "curator:kim", "2026-10-01T00:00:00Z")
    second = materialize_camera_sites(conn, role=ROLE, gold=gold, threshold=0.98, rules=RULES)
    assert second["run_key"] != first["run_key"]  # the verdict is a run input
    assert second["resolved_site_count_N"] == 3
    rows = _matches(conn, second["run_key"])
    human = [r for r in rows if r[3] == "human_accept"]
    assert len(human) == 1
    assert human[0][2] == "same_as" and human[0][4] == "curator:kim"
    ev = human[0][7]
    ev = ev if isinstance(ev, dict) else json.loads(ev)
    assert ev["human_items"] == [[item, "accept"]]
    hr = second["human_review"]
    assert hr["accepts"] == 1 and hr["accept_edges_applied"] == 1

    # Re-run over the unchanged spine + decision history is +0.
    again = materialize_camera_sites(conn, role=ROLE, gold=gold, threshold=0.98, rules=RULES)
    assert again["inserted"] == 0 and again["run_record_inserted"] is False
    assert again["run_key"] == second["run_key"]

    conn.execute("RESET ROLE")
    runs = read_resolved_site_runs(conn)
    assert len(runs[0]["human_accept_edges"]) == 1
    assert len(runs[0]["resolved_edges"]) == 1 and runs[0]["auto_write_edges"] == []


def test_a_human_reject_is_a_cannot_link_that_never_clusters(conn, spine_ctx) -> None:
    ids = _ids(spine_ctx)
    # The automatic run WOULD merge a~b (clean holdout) — the curator's reject wins.
    gold = _gold_pair(ids["a"], ids["b"], GoldLabel.MATCH)
    first = materialize_camera_sites(conn, role=ROLE, gold=gold, threshold=0.98, rules=RULES)
    assert first["resolved_site_count_N"] == 3 and first["auto_write_decisions"] == 1

    item = _insert_item(conn.cursor(), ids["a"], ids["b"])
    _decide(conn.cursor(), item, "reject", "curator:lee", "2026-10-01T00:00:00Z")
    second = materialize_camera_sites(conn, role=ROLE, gold=gold, threshold=0.98, rules=RULES)
    assert second["resolved_site_count_N"] == 4  # the auto merge is gone
    rows = _matches(conn, second["run_key"])
    reject = [r for r in rows if r[3] == "human_reject"]
    assert len(reject) == 1
    assert reject[0][2] == "cannot_link" and reject[0][4] == "curator:lee"
    hr = second["human_review"]
    assert hr["rejects"] == 1 and hr["cannot_link_edges"] == 1

    conn.execute("RESET ROLE")
    runs = read_resolved_site_runs(conn)
    assert runs[0]["resolved_edges"] == [] and runs[0]["cannot_link_count"] == 1


def test_conflicting_votes_stay_proposed_and_the_routed_back_item_governs(conn, spine_ctx) -> None:
    ids = _ids(spine_ctx)
    gold = _gold_pair(ids["a"], ids["b"], GoldLabel.NOT_ENOUGH_INFORMATION)
    item = _insert_item(conn.cursor(), ids["a"], ids["b"])
    _decide(conn.cursor(), item, "accept", "curator:kim", "2026-10-01T00:00:00Z")
    _decide(conn.cursor(), item, "reject", "curator:lee", "2026-10-02T00:00:00Z")

    run = materialize_camera_sites(conn, role=ROLE, gold=gold, threshold=0.98, rules=RULES)
    rows = _matches(conn, run["run_key"])
    (row,) = [r for r in rows if r[3] == "proposed"]
    assert row[5] == "human_conflict"
    assert run["human_review"]["conflicts"] == 1
    # routed back under its own item id (the proposal id is the decided item)
    conflict_item = _item_id(ids["a"], ids["b"], "er_match:camera_site_conflict")
    assert conn.execute(
        "SELECT payload->>'reason' FROM review_item WHERE item_id = %s", (conflict_item,)
    ).fetchone() == ("human_conflict",)

    # A clean adjudication on the routed-back item is the LATEST decided item —
    # it governs over the conflicted proposal.
    _decide(conn.cursor(), conflict_item, "accept", "curator:arbiter", "2026-10-03T00:00:00Z")
    third = materialize_camera_sites(conn, role=ROLE, gold=gold, threshold=0.98, rules=RULES)
    assert third["resolved_site_count_N"] == 3
    human = [r for r in _matches(conn, third["run_key"]) if r[3] == "human_accept"]
    assert len(human) == 1 and human[0][4] == "curator:arbiter"


def test_an_accept_violating_a_hard_constraint_is_recorded_refused(conn, spine_ctx) -> None:
    ids = _ids(spine_ctx)
    # d/e are two DISTINCT devices of one source: a curator accept is recorded,
    # named and refused — constraint (a) still binds humans.
    item = _insert_item(conn.cursor(), ids["d"], ids["e"])
    _decide(conn.cursor(), item, "accept", "curator:kim", "2026-10-01T00:00:00Z")
    run = materialize_camera_sites(conn, role=ROLE, threshold=0.98, rules=RULES)
    rows = _matches(conn, run["run_key"])
    refused = [r for r in rows if r[3] == "refused"]
    assert len(refused) == 1
    assert refused[0][4] == "curator:kim"
    assert refused[0][5] == "human_refused:cluster_constraint:same_source"
    hr = run["human_review"]
    assert hr["accepts"] == 1 and hr["accept_edges_refused"] == 1
    conn.execute("RESET ROLE")
    runs = read_resolved_site_runs(conn)
    assert runs[0]["refused_count"] == 1


def test_a_verdict_on_an_absent_pair_is_counted_not_invented(conn, spine_ctx) -> None:
    ghost_item = _insert_item(conn.cursor(), "0" * 36, "1" * 36)  # no such entities
    _decide(conn.cursor(), ghost_item, "accept", "curator:kim", "2026-10-01T00:00:00Z")
    run = materialize_camera_sites(conn, role=ROLE, threshold=0.98, rules=RULES)
    assert run["human_review"]["unmatched_pairs"] == 1
    assert not any(r[3] == "human_accept" for r in _matches(conn, run["run_key"]))


def test_zero_decisions_run_is_unchanged_and_reruns_plus_zero(conn, spine_ctx) -> None:
    # Items exist (enqueued proposals) but NOTHING was ever decided: the run is
    # the pre-wiring outcome and a re-run is +0.
    gold = _gold_pair(_ids(spine_ctx)["a"], _ids(spine_ctx)["b"], GoldLabel.MATCH)
    first = materialize_camera_sites(conn, role=ROLE, gold=gold, threshold=0.98, rules=RULES)
    hr = first["human_review"]
    assert hr["verdict_pairs"] == 0 and hr["accept_edges_applied"] == 0
    again = materialize_camera_sites(conn, role=ROLE, gold=gold, threshold=0.98, rules=RULES)
    assert again["run_key"] == first["run_key"]
    assert again["inserted"] == 0 and again["run_record_inserted"] is False


def test_duplicate_targets_merge_on_identical_captured_content(conn, spine_ctx) -> None:
    # Two subjects of ONE source under two targets whose captures are byte-
    # identical, with the same row key: the source republished its own row.
    record = spine_ctx["record"]
    x = record(
        "x",
        "camreg_zz_dup",
        "35.5000000",
        "-97.5400000",
        "cam-7",
        "Gilman",
        digest="dup:shared-bytes",
        target="t1",
    )
    y = record(
        "y",
        "camreg_zz_dup",
        "35.5000000",
        "-97.5400000",
        "cam-7",
        "Gilman",
        digest="dup:shared-bytes",
        target="t2",
    )
    recs = {r.subject_id: r for r in read_camera_records(conn)}
    assert recs[x].target_id == "t1" and recs[y].target_id == "t2"
    assert "dup:shared-bytes" in recs[x].capture_digests

    run = materialize_camera_sites(conn, role=ROLE, threshold=0.98, rules=RULES)
    rows = _matches(conn, run["run_key"])
    dup = [r for r in rows if tuple(sorted((r[0], r[1]))) == tuple(sorted((x, y)))]
    assert len(dup) == 1
    assert dup[0][3] == "auto_write" and dup[0][6] == 0  # tier 0: evidence, not a measured tier
    ev = dup[0][7]
    ev = ev if isinstance(ev, dict) else json.loads(ev)
    assert ev["rule"] == "0:duplicate_target_of" and ev["identical_capture_digests"]
    assert run["duplicate_target_groups"] == 1


def test_distinct_same_source_devices_stay_separate(conn, spine_ctx) -> None:
    ids = _ids(spine_ctx)
    # d/e share a point and a source but are genuinely different rows (refs 7/8):
    # no dup lineage, no merge, no decision row at all.
    run = materialize_camera_sites(conn, role=ROLE, threshold=0.98, rules=RULES)
    assert run["resolved_site_count_N"] == run["observation_count_M"] == 4
    rows = _matches(conn, run["run_key"])
    assert not any(tuple(sorted((r[0], r[1]))) == tuple(sorted((ids["d"], ids["e"]))) for r in rows)
    assert run["duplicate_target_groups"] == 0


def test_the_role_cannot_update_or_delete_human_rows(conn, spine_ctx) -> None:
    import psycopg

    materialize_camera_sites(conn, role=ROLE, threshold=0.98, rules=RULES)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("UPDATE camera_site_match SET disposition = 'proposed'")
    conn.rollback()  # SET ROLE rolls back with the aborted transaction — re-set it
    from resolution.camera_sites_pg import set_role

    set_role(conn, ROLE)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("UPDATE review_decision SET decision = 'accept'")
    conn.rollback()
