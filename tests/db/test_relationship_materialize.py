# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Materialize the sharing/access relationship network into the real spine (P28.2).

Exercises the ``relationship_materialize`` sqitch change (deploy/verify happen in the
conftest container) and the append-only, idempotent edge materializer over PG18+PostGIS:

* the §29.3 reconciler (P08.2, CONSUMED) runs over real sharing claims and WRITES
  ``relationship`` rows with full provenance (evidence_claim, access_kind, direction);
* directional asymmetry is surfaced as a contradiction (RETURNED, kept visible) and is
  NOT written to ``contradiction`` here (P28.3 owns that) — both directed edges are kept;
* a re-run over unchanged claims inserts **+0** (idempotent on ``input_digest``);
* the write path is insert-only — no UPDATE/DELETE.
"""

from __future__ import annotations

from conftest import seed_claim_prerequisites
from reconcile.materialize import materialize_sharing_edges, read_materialized_edges

PRED = "configured_sharing_partner"


def _seed_sharing_predicate(conn: object) -> None:
    conn.execute(
        "INSERT INTO vocab_predicate"
        "(predicate_id,vocab_version,value_datatype,object_type,definition,"
        " volatility_class,half_life_days,resolution_strategy) "
        "VALUES(%s,'1.0.0','string','entity_ref','fixture','MODERATE',120,"
        "'authoritative_source_wins') ON CONFLICT DO NOTHING",
        (PRED,),
    )


def _org(conn: object) -> object:
    return conn.execute(
        "INSERT INTO entity(entity_type) VALUES('organization') RETURNING entity_id"
    ).fetchone()[0]


def _sharing_claim(conn: object, prereqs: dict, subject: object, partner: object) -> object:
    """A directional configured_access edge claim: subject → partner (entity_ref)."""
    claim_id = conn.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,object_entity,value_kind,"
        "value_text,raw_value,observed_at,source_reliability,claim_directness,"
        "artifact_integrity,asserted_by,assertion_rationale,ingest_run_id,rights_id,"
        "sensitivity_tier) "
        "VALUES(%s,%s,'entity_ref',%s,'value','partner','partner',"
        "'2026-05-01T00:00:00Z','R1','D1','I1',%s,'fixture',%s,%s,0) RETURNING claim_id",
        (
            subject,
            PRED,
            partner,
            prereqs["author_id"],
            prereqs["run_id"],
            prereqs["rights_id"],
        ),
    ).fetchone()[0]
    return claim_id


def test_sqitch_change_deployed_input_digest_column_and_index(conn: object) -> None:
    conn.execute("SELECT input_digest FROM relationship WHERE false")
    row = conn.execute(
        "SELECT 1 FROM pg_indexes WHERE indexname='relationship_input_digest_key'"
    ).fetchone()
    assert row is not None


def test_materialize_writes_a_relationship_edge_with_provenance(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    _seed_sharing_predicate(conn)
    a = prereqs["subject_id"]
    b = _org(conn)
    claim_id = _sharing_claim(conn, prereqs, a, b)

    summary = materialize_sharing_edges(conn, subject=str(a))
    assert summary.inserted == 1
    assert summary.by_access_kind == {"configured_access": 1}

    row = conn.execute(
        "SELECT from_entity, to_entity, edge_type, access_kind, direction, "
        "       valid_from_kind, valid_to_kind, evidence_claim, input_digest "
        "  FROM relationship WHERE from_entity=%s",
        (a,),
    ).fetchone()
    assert row is not None
    assert str(row[0]) == str(a) and str(row[1]) == str(b)
    assert row[2] == "configured_access"  # §12.5: access_kind is the edge_type
    assert row[3] == "configured_access"
    assert row[4] == "a_to_b"
    assert row[5] == "unknown"  # single-snapshot start unknown (SIG-RECON-036)
    assert row[6] == "ongoing"
    assert str(row[7]) == str(claim_id)  # evidenced (§3.1)
    assert row[8] is not None  # idempotency key


def test_asymmetry_surfaced_visible_not_written_to_contradiction(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    _seed_sharing_predicate(conn)
    a = prereqs["subject_id"]
    b = _org(conn)
    _sharing_claim(conn, prereqs, a, b)  # A -> B, no reverse

    contradictions_before = conn.execute("SELECT count(*) FROM contradiction").fetchone()[0]
    summary = materialize_sharing_edges(conn, subject=str(a))
    # The edge is materialized; the asymmetry is a RETURNED contradiction (visible).
    assert summary.inserted == 1
    assert summary.contradictions == 1
    assert summary.asymmetry_tasks == 1
    # P28.3 owns materializing contradiction rows — this ticket writes none.
    contradictions_after = conn.execute("SELECT count(*) FROM contradiction").fetchone()[0]
    assert contradictions_after == contradictions_before


def test_corroborated_pair_keeps_both_directed_edges(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    _seed_sharing_predicate(conn)
    a = prereqs["subject_id"]
    b = _org(conn)
    _sharing_claim(conn, prereqs, a, b)  # A -> B
    _sharing_claim(conn, prereqs, b, a)  # B -> A (reciprocal; corroborates)

    summary = materialize_sharing_edges(conn)
    assert summary.inserted == 2  # both directed edges kept separately (never merged)
    # No asymmetry when both directions are attested by their own side.
    assert summary.contradictions == 0
    corroborated = conn.execute(
        "SELECT bool_and(input_digest IS NOT NULL) FROM relationship"
    ).fetchone()[0]
    assert corroborated is True


def test_re_run_is_idempotent_plus_zero(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    _seed_sharing_predicate(conn)
    a = prereqs["subject_id"]
    b = _org(conn)
    _sharing_claim(conn, prereqs, a, b)

    first = materialize_sharing_edges(conn, subject=str(a))
    assert first.inserted == 1
    before = conn.execute(
        "SELECT count(*) FROM relationship WHERE from_entity=%s", (a,)
    ).fetchone()[0]
    # Re-run over the SAME claims: append-only + idempotent -> +0.
    second = materialize_sharing_edges(conn, subject=str(a))
    assert second.inserted == 0
    assert second.skipped_existing == 1
    after = conn.execute("SELECT count(*) FROM relationship WHERE from_entity=%s", (a,)).fetchone()[
        0
    ]
    assert before == after == 1


def test_read_materialized_edges_round_trips_the_dataset(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    _seed_sharing_predicate(conn)
    a = prereqs["subject_id"]
    b = _org(conn)
    claim_id = _sharing_claim(conn, prereqs, a, b)
    materialize_sharing_edges(conn, subject=str(a))

    edges = read_materialized_edges(conn)
    assert len(edges) == 1
    e = edges[0]
    assert e["from_entity"] == str(a) and e["to_entity"] == str(b)
    assert e["access_kind"] == "configured_access"
    assert e["evidence_claim"] == str(claim_id)
    assert e["valid_from"] is not None
