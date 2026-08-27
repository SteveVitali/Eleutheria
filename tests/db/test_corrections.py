# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Corrections without erasure (§16.6; SIG-STORE-020).

AC3: a query at an `as_of_belief` before the correction still returns the old
value — the property that makes SIG a citable source, not just a database.
"""

from __future__ import annotations

import time

from conftest import insert_claim, seed_claim_prerequisites


def _value_as_of(conn: object, subject_id: object, predicate_id: str, belief: object) -> object:
    row = conn.execute(
        "SELECT value_num FROM claim WHERE subject_id=%s AND predicate_id=%s "
        "AND sys_period @> %s::timestamptz",
        (subject_id, predicate_id, belief),
    ).fetchone()
    return row[0] if row else None


def test_correction_preserves_prior_belief(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)

    # 2026-05-01: the parser read the contract PDF as "25 cameras".
    bad_claim = insert_claim(conn, prereqs, value_text="25", value_num=25)
    time.sleep(0.01)
    belief_before_correction = conn.execute("SELECT clock_timestamp()").fetchone()[0]
    time.sleep(0.01)

    # 2026-08-20: a human notices it actually says "225". Close the prior belief
    # (the world did not change; SIG was wrong) and assert the corrected reading.
    conn.execute(
        "UPDATE claim SET sys_period = tstzrange(lower(sys_period), "
        "clock_timestamp(), '[)') WHERE claim_id=%s AND upper_inf(sys_period)",
        (bad_claim,),
    )
    insert_claim(
        conn,
        prereqs,
        value_text="225",
        value_num=225,
        revises_claim=bad_claim,
        correction_reason="extraction_error",
    )

    # A query at a belief time before the correction still returns 25.
    assert (
        _value_as_of(conn, prereqs["subject_id"], prereqs["predicate_id"], belief_before_correction)
        == 25
    )

    # The current belief (upper_inf transaction time) is the corrected 225.
    current = conn.execute(
        "SELECT value_num FROM claim WHERE subject_id=%s AND predicate_id=%s "
        "AND upper_inf(sys_period)",
        (prereqs["subject_id"], prereqs["predicate_id"]),
    ).fetchall()
    assert [r[0] for r in current] == [225]

    # The original row still exists (append-only): both beliefs are retrievable.
    all_values = conn.execute(
        "SELECT count(*) FROM claim WHERE subject_id=%s AND predicate_id=%s",
        (prereqs["subject_id"], prereqs["predicate_id"]),
    ).fetchone()[0]
    assert all_values == 2


def test_correction_requires_a_reason(conn: object) -> None:
    """SIG-STORE-020 / claim_correction_reasoned: revises_claim needs a reason."""
    import psycopg
    import pytest

    prereqs = seed_claim_prerequisites(conn)
    original = insert_claim(conn, prereqs)
    with pytest.raises(psycopg.Error) as excinfo:
        with conn.transaction():
            insert_claim(
                conn,
                prereqs,
                value_text="30",
                value_num=30,
                revises_claim=original,
                correction_reason=None,
            )
    assert "claim_correction_reasoned" in str(excinfo.value)
