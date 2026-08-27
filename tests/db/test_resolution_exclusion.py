# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Resolution non-overlap (§16.4; SIG-STORE-014/016).

AC4: at most one resolved value per (subject, predicate) may be current for any
instant of valid time — enforced by the GiST exclusion constraint IN THE
DATABASE, not by application code.
"""

from __future__ import annotations

import psycopg
import pytest
from conftest import seed_claim_prerequisites


def _seed_resolution_vocab(conn: object) -> None:
    conn.execute(
        "INSERT INTO vocab_confidence(confidence,definition) VALUES('high','h') "
        "ON CONFLICT DO NOTHING"
    )
    conn.execute(
        "INSERT INTO vocab_rationale(rationale_code,template) VALUES('single','t') "
        "ON CONFLICT DO NOTHING"
    )


def _insert_resolution(
    conn: object, subject_id: object, predicate_id: str, lower: str, upper: str
) -> None:
    conn.execute(
        "INSERT INTO resolution(subject_id,predicate_id,value_kind,value_text,"
        "valid_period,considered_claims,contradiction_state,strategy_id,"
        "rationale_code,rationale_text,confidence,evidence_counts,"
        "resolver_version,ruleset_version) "
        "VALUES(%s,%s,'value','25',tstzrange(%s,%s,'[)'),'{}','uncontested',"
        "'authoritative_source_wins','single','because','high','{}','v1','r1')",
        (subject_id, predicate_id, lower, upper),
    )


def test_overlapping_current_resolutions_are_rejected(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    _seed_resolution_vocab(conn)
    subject, predicate = prereqs["subject_id"], prereqs["predicate_id"]

    _insert_resolution(conn, subject, predicate, "2026-01-01", "2026-12-31")
    with pytest.raises(psycopg.errors.ExclusionViolation) as excinfo:
        with conn.transaction():
            _insert_resolution(conn, subject, predicate, "2026-06-01", "2027-06-01")
    assert "resolution_no_overlap" in str(excinfo.value)


def test_non_overlapping_resolutions_are_allowed(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    _seed_resolution_vocab(conn)
    subject, predicate = prereqs["subject_id"], prereqs["predicate_id"]

    _insert_resolution(conn, subject, predicate, "2026-01-01", "2026-06-01")
    _insert_resolution(conn, subject, predicate, "2026-06-01", "2027-01-01")
    count = conn.execute(
        "SELECT count(*) FROM resolution WHERE subject_id=%s", (subject,)
    ).fetchone()[0]
    assert count == 2


def test_superseded_resolution_frees_the_valid_window(conn: object) -> None:
    """The exclusion applies only WHERE upper_inf(sys_period): once a resolution
    is superseded (its transaction-time closed), a new decision may reuse the
    same valid window (§16.4)."""
    prereqs = seed_claim_prerequisites(conn)
    _seed_resolution_vocab(conn)
    subject, predicate = prereqs["subject_id"], prereqs["predicate_id"]

    _insert_resolution(conn, subject, predicate, "2026-01-01", "2026-12-31")
    conn.execute(
        "UPDATE resolution SET sys_period = tstzrange(lower(sys_period), "
        "clock_timestamp(), '[)') WHERE subject_id=%s",
        (subject,),
    )
    # Same valid window is now free because the prior decision is not current.
    _insert_resolution(conn, subject, predicate, "2026-01-01", "2026-12-31")
    current = conn.execute(
        "SELECT count(*) FROM resolution WHERE subject_id=%s AND upper_inf(sys_period)",
        (subject,),
    ).fetchone()[0]
    assert current == 1


def test_exclusion_is_a_database_constraint(conn: object) -> None:
    """The non-overlap guarantee is a real exclusion constraint (contype 'x'),
    not application logic (SIG-STORE-016)."""
    row = conn.execute(
        "SELECT contype FROM pg_constraint WHERE conname='resolution_no_overlap'"
    ).fetchone()
    assert row is not None and row[0] == "x"
