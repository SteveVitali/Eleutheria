# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The camera-site review surface over real PostgreSQL (P31.10, ADR-105/068).

Pins, against the deployed schema (sqitch, the same way production applies it):

* the queue filters — camera-site prefixes vs the P31.3
  ``er_match:identity_duplicate:`` family, tier, and stratum bucket;
* ``decide`` landing as one append-only ``review_decision`` row carrying the
  pseudonymous curator id (and "unsure" writing NOTHING);
* the seeded stratified sampler's reproducibility and append-only campaign
  tagging (+0 re-draw, design-conflict refusal);
* the JSONL export → label → import round trip through the same decide path;
* the least-privilege ``sig_materialize`` role's reach over the new tables.
"""

from __future__ import annotations

import pytest
from resolution.camera_site_review import (
    CAMERA_SITE_DISPUTED_PREFIX,
    CAMERA_SITE_ITEM_PREFIX,
    CAMERA_SITE_PREFIXES,
    IDENTITY_DUPLICATE_PREFIX,
    draw_sample,
    export_rows,
    import_decisions,
    materialize_campaign,
    pair_evidence,
    pending_items,
    read_observation,
)
from resolution.review_pg import PgReviewQueue

ROLE = "sig_materialize"
CAMERA_PREDICATES = (
    "camera_latitude",
    "camera_longitude",
    "camera_external_ref",
    "camera_name",
    "camera_operator",
    "camera_jurisdiction",
    "camera_type",
)


def _seed_prereqs(conn) -> dict:
    """The FK chain one camera claim needs (the camera_spine fixture's shape)."""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO vocab_resolution_strategy(strategy_id,definition) "
        "VALUES('latest_observation_wins','fixture') ON CONFLICT DO NOTHING"
    )
    for pid in CAMERA_PREDICATES:
        cur.execute(
            "INSERT INTO vocab_predicate(predicate_id,vocab_version,value_datatype,object_type,"
            " definition,volatility_class,half_life_days,resolution_strategy) "
            "VALUES(%s,'1.0.0','string','literal','fixture','SLOW',730,"
            "'latest_observation_wins') ON CONFLICT DO NOTHING",
            (pid,),
        )
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
    return {"rights": rights, "run": run, "author": author}


def _camera_subject(conn, p, source_id: str, fields: dict[str, str]) -> str:
    """Insert one observation-level camera subject; return its entity_id."""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO source_registry(source_id,name,source_kind,default_reliability,"
        "reliability_justification,rights_id,custody_posture,compact_status,robots_policy,"
        "ingestion_permitted) VALUES(%s,%s,'registry','R2','fixture',%s,'MIRROR','granted',"
        "'obey',true) ON CONFLICT DO NOTHING",
        (source_id, source_id, p["rights"]),
    )
    cur.execute(
        "INSERT INTO evidence_artifact(source_id,stable_locator,artifact_type,"
        "acquisition_method,primary_or_secondary,rights_id,capture_status) "
        "VALUES(%s,%s,'camera_registry','registry_api','primary',%s,'captured') "
        "RETURNING artifact_id",
        (
            source_id,
            f"urn:sig:p3110:{source_id}:{fields.get('camera_external_ref', 'x')}",
            p["rights"],
        ),
    )
    artifact = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,media_type,"
        "retrieved_at,retrieved_by_run_id,ocfl_object_id,ocfl_version,storage_tier,"
        "capture_method,capture_tool_version,source_uri) VALUES(%s,%s,10,'application/json',"
        "'2026-09-01T00:00:00Z',%s,%s,'v1','public','registry_api','sig/0',%s) "
        "RETURNING capture_id",
        (
            artifact,
            f"d-{source_id}-{fields.get('camera_external_ref', 'x')}",
            p["run"],
            f"urn:{source_id}",
            f"urn:{source_id}",
        ),
    )
    capture = cur.fetchone()[0]
    cur.execute("INSERT INTO entity(entity_type) VALUES('deployment') RETURNING entity_id")
    subject = str(cur.fetchone()[0])
    for pid, value in fields.items():
        cur.execute(
            "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,value_text,"
            "raw_value,observed_at,source_reliability,claim_directness,artifact_integrity,"
            "asserted_by,assertion_rationale,ingest_run_id,rights_id,sensitivity_tier) "
            "VALUES(%s,%s,'literal','value',%s,%s,'2026-09-01T00:00:00Z','R2','D2','I1',"
            "%s,'fixture',%s,%s,0) RETURNING claim_id",
            (subject, pid, value, value, p["author"], p["run"], p["rights"]),
        )
        cur.execute(
            "INSERT INTO claim_evidence(claim_id,capture_id,role) VALUES(%s,%s,'establishes')",
            (cur.fetchone()[0], capture),
        )
    return subject


def _item(conn, item_id: str, payload: dict, summary: str = "fixture") -> None:
    import json

    conn.execute(
        "INSERT INTO review_item(item_id, kind, summary, payload) "
        "VALUES(%s, 'er_match', %s, %s::jsonb) ON CONFLICT DO NOTHING",
        (item_id, summary, json.dumps(payload)),
    )


@pytest.fixture
def review_spine(conn) -> dict[str, object]:
    """Two camera subjects + a spread of review items across every stratum."""
    p = _seed_prereqs(conn)
    left = _camera_subject(
        conn,
        p,
        "dot_511_zz",
        {
            "camera_latitude": "35.4676234",
            "camera_longitude": "-97.5164276",
            "camera_external_ref": "101",
            "camera_name": "I-35 @ Main",
            "camera_operator": "Zed DOT",
            "camera_jurisdiction": "US-OK",
            "camera_type": "traffic",
        },
    )
    right = _camera_subject(
        conn,
        p,
        "camreg_zz_mirror",
        {
            "camera_latitude": "35.4676300",
            "camera_longitude": "-97.5164300",
            "camera_external_ref": "9001",
            "camera_name": "I35/Main St cam",
            "camera_operator": "community mirror",
            "camera_jurisdiction": "US-OK",
            "camera_type": "traffic",
        },
    )
    _item(
        conn,
        f"{CAMERA_SITE_ITEM_PREFIX}{left}:{right}",
        {
            "left": left,
            "right": right,
            "tier": 4,
            "tier_label": "4g:proximate_unique",
            "reason": "tier_not_auto_write",
            "evidence": {"distance_m": 21.5, "soft_conflicts": ["jurisdiction"]},
        },
        "Same camera? dot_511_zz vs camreg_zz_mirror, 21.5 m apart",
    )
    _item(conn, f"{CAMERA_SITE_ITEM_PREFIX}a:b", {"tier": 5, "reason": "tier_not_auto_write"})
    _item(
        conn,
        f"{CAMERA_SITE_ITEM_PREFIX}c:d",
        {"tier": 3, "reason": "soft_conflict:jurisdiction"},
    )
    _item(
        conn,
        f"{CAMERA_SITE_DISPUTED_PREFIX}e:f",
        {"reason": "active_learning:adjudicator_disagreement"},
    )
    _item(conn, f"{IDENTITY_DUPLICATE_PREFIX}g:h", {"scheme": "sig.connector.subject"})
    return {"left": left, "right": right}


def test_pending_items_family_tier_and_bucket_filters(conn, review_spine) -> None:
    items = pending_items(conn, prefixes=CAMERA_SITE_PREFIXES)
    ids = {i.item_id for i in items}
    assert len(ids) == 4
    # The identity-duplicate family is excluded from the camera-site queue.
    assert not any(i.startswith(IDENTITY_DUPLICATE_PREFIX) for i in ids)

    tier4 = pending_items(conn, prefixes=CAMERA_SITE_PREFIXES, tier=4)
    assert [i.item_id for i in tier4] == [
        f"{CAMERA_SITE_ITEM_PREFIX}{review_spine['left']}:{review_spine['right']}"
    ]
    soft = pending_items(conn, prefixes=CAMERA_SITE_PREFIXES, bucket="soft-conflict")
    assert [i.item_id for i in soft] == [f"{CAMERA_SITE_ITEM_PREFIX}c:d"]
    disputed = pending_items(conn, prefixes=CAMERA_SITE_PREFIXES, bucket="disputed")
    assert [i.item_id for i in disputed] == [f"{CAMERA_SITE_DISPUTED_PREFIX}e:f"]


def test_decide_appends_one_review_decision_with_the_curator_id(conn, review_spine) -> None:
    queue = PgReviewQueue(conn)
    item_id = f"{CAMERA_SITE_ITEM_PREFIX}a:b"
    d = queue.decide(item_id, "accept", reviewer="curator-1", rationale="same camera")
    assert d.decision == "accept" and d.reviewer == "curator-1"
    row = conn.execute(
        "SELECT item_id, decision, reviewer, rationale FROM review_decision WHERE item_id = %s",
        (item_id,),
    ).fetchone()
    assert row == (item_id, "accept", "curator-1", "same camera")
    # The decided item drops out of pending.
    assert not any(i.item_id == item_id for i in pending_items(conn))
    # A repeat decision is a NEW append-only row (a history, never an edit).
    queue.decide(item_id, "reject", reviewer="curator-1")
    assert (
        conn.execute(
            "SELECT count(*) FROM review_decision WHERE item_id = %s", (item_id,)
        ).fetchone()[0]
        == 2
    )


def test_sampler_is_reproducible_for_a_seed(conn, review_spine) -> None:
    # Pad 5g so the quota doesn't exhaust the stratum (seed sensitivity needs headroom).
    for i in range(20):
        _item(conn, f"{CAMERA_SITE_ITEM_PREFIX}s{i:02d}:t{i:02d}", {"tier": 5})
    strata = [("4g", None), ("5g", None), ("soft-conflict", None), ("disputed", None)]
    first = draw_sample(conn, strata, n=8, seed="round10")
    second = draw_sample(conn, strata, n=8, seed="round10")
    assert first == second  # reproducible for a fixed seed
    other = draw_sample(conn, strata, n=8, seed="different")
    assert other["5g"] != first["5g"]  # the seed actually steers the draw
    assert first["4g"] == [
        f"{CAMERA_SITE_ITEM_PREFIX}{review_spine['left']}:{review_spine['right']}"
    ]
    assert len(first["soft-conflict"]) == 1 and len(first["disputed"]) == 1
    assert len({i for ids in first.values() for i in ids}) == 8


def test_campaign_tag_is_append_only_and_refuses_a_design_conflict(conn, review_spine) -> None:
    drawn = {"4g": [f"{CAMERA_SITE_ITEM_PREFIX}a:b"], "5g": [f"{CAMERA_SITE_ITEM_PREFIX}s0:t0"]}
    _item(conn, f"{CAMERA_SITE_ITEM_PREFIX}s0:t0", {"tier": 5})
    design = {"seed": "1", "n": 2, "design_digest": "abc"}
    first = materialize_campaign(
        conn,
        campaign_id="test-r10",
        purpose="prepared for Round 10",
        design=design,
        created_by="test",
        drawn=drawn,
    )
    assert first["campaign_inserted"] and first["items_inserted"] == 2
    rows = conn.execute(
        "SELECT item_id, stratum FROM review_campaign_item WHERE campaign_id='test-r10' "
        "ORDER BY item_id"
    ).fetchall()
    assert rows == [
        (f"{CAMERA_SITE_ITEM_PREFIX}a:b", "4g"),
        (f"{CAMERA_SITE_ITEM_PREFIX}s0:t0", "5g"),
    ]
    # Re-drawing the same design under the same id is +0 (append-only idempotent).
    again = materialize_campaign(
        conn,
        campaign_id="test-r10",
        purpose="prepared for Round 10",
        design=design,
        created_by="test",
        drawn=drawn,
    )
    assert again["campaign_inserted"] is False and again["items_inserted"] == 0
    # A different design under a taken id is refused, never silently merged.
    with pytest.raises(Exception, match="different design"):
        materialize_campaign(
            conn,
            campaign_id="test-r10",
            purpose="x",
            design={"design_digest": "different"},
            created_by="test",
            drawn=drawn,
        )


def test_export_import_round_trip_writes_append_only_decisions(conn, review_spine) -> None:
    rows = export_rows(conn, prefixes=CAMERA_SITE_PREFIXES)
    assert {r["item_id"] for r in rows} == {
        i.item_id for i in pending_items(conn, prefixes=CAMERA_SITE_PREFIXES)
    }
    assert all(r["decision"] is None for r in rows)  # a labeller fills this
    for r in rows:
        r["decision"] = "accept" if r["item_id"].endswith("a:b") else "unsure"
        r["rationale"] = "same device" if r["decision"] == "accept" else None
    result = import_decisions(PgReviewQueue(conn), rows, reviewer="sig-curator")
    assert result["appended"] == 1 and result["skipped"] == len(rows) - 1
    row = conn.execute(
        "SELECT reviewer, decision FROM review_decision WHERE item_id = %s",
        (f"{CAMERA_SITE_ITEM_PREFIX}a:b",),
    ).fetchone()
    assert row == ("sig-curator", "accept")


def test_pair_evidence_reads_both_observations(conn, review_spine) -> None:
    item_id = f"{CAMERA_SITE_ITEM_PREFIX}{review_spine['left']}:{review_spine['right']}"
    item = PgReviewQueue(conn).get(item_id)
    assert item is not None
    view = pair_evidence(conn, item)
    assert view is not None and view["distance_m"] == 21.5
    assert view["tier"] == 4 and view["tier_label"] == "4g:proximate_unique"
    assert view["soft_conflicts"] == ["jurisdiction"]
    left, right = view["left_observation"], view["right_observation"]
    assert left["source_id"] == "dot_511_zz" and left["external_ref"] == "101"
    assert left["name"] == "I-35 @ Main" and left["operator"] == "Zed DOT"
    assert left["latitude"] == pytest.approx(35.4676234)
    assert right["source_id"] == "camreg_zz_mirror" and right["external_ref"] == "9001"


def test_read_observation_returns_none_for_a_non_camera_subject(conn, review_spine) -> None:
    cur = conn.cursor()
    cur.execute("INSERT INTO entity(entity_type) VALUES('deployment') RETURNING entity_id")
    plain = str(cur.fetchone()[0])
    assert read_observation(conn, plain) is None


def test_materialize_role_reaches_campaign_tables_and_review_decision(conn, review_spine) -> None:
    from resolution.camera_sites_pg import set_role

    set_role(conn, ROLE)
    drawn = {"5g": [f"{CAMERA_SITE_ITEM_PREFIX}a:b"]}
    out = materialize_campaign(
        conn,
        campaign_id="role-test",
        purpose="prepared for Round 10",
        design={"design_digest": "d"},
        created_by="test",
        drawn=drawn,
    )
    assert out["campaign_inserted"] and out["items_inserted"] == 1
    d = PgReviewQueue(conn).decide(
        f"{CAMERA_SITE_ITEM_PREFIX}a:b", "reject", reviewer="sig-curator"
    )
    assert d.decision == "reject"
    # …but the role still cannot mutate a campaign row (append-only).
    import psycopg.errors

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("UPDATE review_campaign SET purpose='x' WHERE campaign_id='role-test'")
