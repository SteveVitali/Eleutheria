# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Revert a contribution as a unit, over the real claim spine (§34.4, SIG-CONTRIB-009).

AC4: a revert supersedes via a **new append-only assertion** (a claim with
``retraction_of`` set) and **deletes nothing**. This mirrors §16.6's correction
mechanism — the contribution's open claims have their ``sys_period`` closed and a
retraction claim is appended for each, so a belief-time query before the revert
still reproduces the pre-revert values. The in-memory model of the same rule is
``tests/tasks/test_tasks_revert.py``.
"""

from __future__ import annotations

import time

from conftest import insert_claim, seed_claim_prerequisites


def _revert_claim(conn: object, prereqs: dict[str, object], original_id: object) -> object:
    """Close a claim's belief and append a retraction claim pointing back at it.

    The revert is a new assertion: a ``novalue`` claim with ``retraction_of`` set,
    exactly as §16.6 appends a corrected claim with ``revises_claim`` set. The
    original row is never deleted — only its ``sys_period`` is closed.
    """
    conn.execute(
        "UPDATE claim SET sys_period = tstzrange(lower(sys_period), "
        "clock_timestamp(), '[)') WHERE claim_id=%s AND upper_inf(sys_period)",
        (original_id,),
    )
    row = conn.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,"
        "unit,raw_value,observed_at,source_reliability,claim_directness,"
        "artifact_integrity,claim_polarity,asserted_by,assertion_rationale,"
        "ingest_run_id,rights_id,retraction_of,correction_reason) "
        "VALUES(%s,%s,'quantity','novalue','cameras','retracted',"
        "'2026-08-20T00:00:00Z','R1','D1','I1','denies',%s,"
        "'revert of a poisoned contribution',%s,%s,%s,%s) RETURNING claim_id",
        (
            prereqs["subject_id"],
            prereqs["predicate_id"],
            prereqs["author_id"],
            prereqs["run_id"],
            prereqs["rights_id"],
            original_id,
            "contribution_reverted",
        ),
    ).fetchone()
    return row[0]


def _current_value_count(conn: object, prereqs: dict[str, object]) -> int:
    return conn.execute(
        "SELECT count(*) FROM claim WHERE subject_id=%s AND predicate_id=%s "
        "AND value_kind='value' AND upper_inf(sys_period)",
        (prereqs["subject_id"], prereqs["predicate_id"]),
    ).fetchone()[0]


def test_revert_appends_retractions_and_deletes_nothing(conn: object) -> None:
    """AC4 / SIG-CONTRIB-009: the contribution's claims are retracted, not deleted."""
    prereqs = seed_claim_prerequisites(conn)

    # One contribution produced two claims (a unit).
    c1 = insert_claim(conn, prereqs, value_text="25", value_num=25)
    c2 = insert_claim(conn, prereqs, value_text="40", value_num=40)
    assert _current_value_count(conn, prereqs) == 2

    time.sleep(0.01)
    belief_before_revert = conn.execute("SELECT clock_timestamp()").fetchone()[0]
    time.sleep(0.01)

    # Revert the contribution as a unit: retract every open claim it produced.
    r1 = _revert_claim(conn, prereqs, c1)
    r2 = _revert_claim(conn, prereqs, c2)

    # Nothing was deleted: all four rows (two originals + two retractions) exist.
    total = conn.execute(
        "SELECT count(*) FROM claim WHERE subject_id=%s AND predicate_id=%s",
        (prereqs["subject_id"], prereqs["predicate_id"]),
    ).fetchone()[0]
    assert total == 4

    # The two originals still exist and are simply closed (not current).
    originals_still_present = conn.execute(
        "SELECT count(*) FROM claim WHERE claim_id = ANY(%s)",
        ([c1, c2],),
    ).fetchone()[0]
    assert originals_still_present == 2

    # The reverts are new assertions pointing back at what they retract.
    retracted = conn.execute(
        "SELECT retraction_of FROM claim WHERE claim_id = ANY(%s) ORDER BY retraction_of",
        ([r1, r2],),
    ).fetchall()
    assert {row[0] for row in retracted} == {c1, c2}

    # No current value claim remains — the contribution's assertions are withdrawn.
    assert _current_value_count(conn, prereqs) == 0

    # Reproducibility: a belief time before the revert still returns both values.
    values_before = conn.execute(
        "SELECT value_num FROM claim WHERE subject_id=%s AND predicate_id=%s "
        "AND value_kind='value' AND sys_period @> %s::timestamptz ORDER BY value_num",
        (prereqs["subject_id"], prereqs["predicate_id"], belief_before_revert),
    ).fetchall()
    assert [row[0] for row in values_before] == [25, 40]
