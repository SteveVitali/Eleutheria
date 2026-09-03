# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The as-of query functions against a live PostgreSQL (§9.4, SIG-TIME-007/008/009).

AC4: the §16.6 correction scenario holds *at query time through the shipped
`claim_as_of` function*: an `as_of_belief` before the correction returns the old
value; the current belief returns the corrected one. This proves the two-axis
query contract on the real engine, not just the Python predicate builder.
"""

from __future__ import annotations

import time

from conftest import insert_claim, seed_claim_prerequisites


def _value_via_as_of(conn: object, subject_id: object, predicate_id: str, belief: object) -> object:
    # clock_timestamp() (not now()) as the world instant: inside this single test
    # transaction the freshly-inserted rows carry sys_period/valid_period bounds set
    # from clock_timestamp(), which is strictly after now() (transaction start).
    row = conn.execute(
        "SELECT value_num FROM claim_as_of(clock_timestamp(), %s::timestamptz) "
        "WHERE subject_id=%s AND predicate_id=%s",
        (belief, subject_id, predicate_id),
    ).fetchone()
    return row[0] if row else None


def test_claim_as_of_belief_returns_prior_belief(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)

    bad_claim = insert_claim(conn, prereqs, value_text="25", value_num=25)
    time.sleep(0.01)
    belief_before = conn.execute("SELECT clock_timestamp()").fetchone()[0]
    time.sleep(0.01)

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

    # The as-of function, pinned to a belief before the correction, returns 25.
    assert (
        _value_via_as_of(conn, prereqs["subject_id"], prereqs["predicate_id"], belief_before) == 25
    )

    # Current belief returns exactly the corrected value.
    current = conn.execute(
        "SELECT value_num FROM claim_as_of() WHERE subject_id=%s AND predicate_id=%s",
        (prereqs["subject_id"], prereqs["predicate_id"]),
    ).fetchall()
    assert [r[0] for r in current] == [225]


def test_claim_as_of_world_filters_valid_time(conn: object) -> None:
    """`as_of_world` selects by T1 valid time: a claim valid only in 2019 is not
    returned for a 2026 world query."""
    prereqs = seed_claim_prerequisites(conn)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,value_text,"
        "value_num,unit,raw_value,valid_period,valid_from_kind,valid_to_kind,observed_at,"
        "source_reliability,claim_directness,artifact_integrity,asserted_by,assertion_rationale,"
        "ingest_run_id,rights_id) "
        "VALUES(%s,%s,'quantity','value','10','10','cameras','10',"
        "tstzrange('2019-01-01','2020-01-01','[)'),'exact','exact','2019-06-01',"
        "'R1','D1','I1',%s,'fixture',%s,%s)",
        (
            prereqs["subject_id"],
            prereqs["predicate_id"],
            prereqs["author_id"],
            prereqs["run_id"],
            prereqs["rights_id"],
        ),
    )
    in_2019 = conn.execute(
        "SELECT count(*) FROM claim_as_of('2019-07-01'::timestamptz, clock_timestamp()) "
        "WHERE subject_id=%s",
        (prereqs["subject_id"],),
    ).fetchone()[0]
    in_2026 = conn.execute(
        "SELECT count(*) FROM claim_as_of('2026-07-01'::timestamptz, clock_timestamp()) "
        "WHERE subject_id=%s",
        (prereqs["subject_id"],),
    ).fetchone()[0]
    assert in_2019 == 1
    assert in_2026 == 0


def test_temporally_unanchored_requires_a_reason(conn: object) -> None:
    """TI-8 support: the temporally_unanchored flag needs a reason (claim_unanchored_reasoned)."""
    import psycopg
    import pytest

    prereqs = seed_claim_prerequisites(conn)
    with pytest.raises(psycopg.Error) as excinfo:
        with conn.transaction():
            conn.execute(
                "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,value_text,"
                "value_num,unit,raw_value,observed_at,source_reliability,claim_directness,"
                "artifact_integrity,asserted_by,assertion_rationale,ingest_run_id,rights_id,"
                "temporally_unanchored) "
                "VALUES(%s,%s,'quantity','value','5','5','cameras','5','2026-01-01',"
                "'R1','D1','I1',%s,'fixture',%s,%s,true)",
                (
                    prereqs["subject_id"],
                    prereqs["predicate_id"],
                    prereqs["author_id"],
                    prereqs["run_id"],
                    prereqs["rights_id"],
                ),
            )
    assert "claim_unanchored_reasoned" in str(excinfo.value)
