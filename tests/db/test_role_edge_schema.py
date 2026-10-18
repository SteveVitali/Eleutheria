# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.26 role/time backend over real PG18+PostGIS (R11-L3-CP7, CONF-06).

Exercises the ``role_edges`` + ``vocab_published_by`` sqitch changes (deployed
+ verified by the conftest container) and the
``reconcile.materialize.materialize_role_edges`` pass:

* a publishing-only source mints NO operator edge — provenance-role claims
  (``camera_registry_publisher``, ``published_by``) are literal provenance and
  never reach the ``entity_role`` surface (SIG-TRUST-003);
* ``operator_absent`` materializes the explicit ``operator_unknown`` marker
  row — actor NULL, evidenced by the absence claim (SIG-ONTO-028);
* role edges carry honest valid time — a claim's evidenced bound becomes the
  edge's ``valid_period`` lower; an undated claim produces an UNBOUNDED period
  + ``valid_from_kind='undated'`` + NULL ``observed_at`` — never 1970-01-01
  (SIG-ONTO-030/032);
* supersession is recorded edge succession — a later same-lineage state closes
  the prior episode's valid upper bound and names the closing claim
  (SIG-EPIS-029); the sys_period close runs through the SECURITY DEFINER
  function, never an in-place edit;
* append-only idempotency — a re-run over unchanged claims is +0;
* epoch-zero is rejected AT WRITE on both edge tables (the CHECK);
* ``operator_state`` reads operator / operator_unknown / not_asserted.
"""

from __future__ import annotations

import re

import psycopg
from conftest import seed_claim_prerequisites
from db.organization_roles import EDGE_ROLE_VOCABULARY
from reconcile.materialize import (
    materialize_role_edges,
    materialize_sharing_edges,
    operator_state,
    read_materialized_edges,
    read_materialized_role_edges,
)


def _entity(conn: object, entity_type: str = "organization") -> object:
    return conn.execute(
        "INSERT INTO entity(entity_type) VALUES(%s) RETURNING entity_id", (entity_type,)
    ).fetchone()[0]


def _claim(
    conn: object,
    prereqs: dict[str, object],
    *,
    subject: object,
    predicate: str,
    object_type: str = "literal",
    object_entity: object = None,
    value_text: str | None = "v",
    value_bool: object = None,
    observed_at: str | None = "2026-05-01T00:00:00Z",
    valid_lower: str | None = None,
    valid_upper: str | None = None,
    revises_claim: object = None,
    retraction_of: object = None,
    correction_reason: object = None,
) -> object:
    """One role-bearing claim through the asserted_by origin path."""
    cur = conn.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,object_entity,value_kind,"
        "value_text,value_bool,raw_value,observed_at,observed_unknown_reason,valid_period,"
        "source_reliability,claim_directness,artifact_integrity,asserted_by,"
        "assertion_rationale,ingest_run_id,rights_id,sensitivity_tier,revises_claim,"
        "retraction_of,correction_reason) "
        "VALUES(%s,%s,%s,%s,'value',%s,%s,'raw',%s,%s,"
        " tstzrange(%s::timestamptz,%s::timestamptz,'[)'),"
        " 'R1','D1','I1',%s,'fixture',%s,%s,0,%s,%s,%s) RETURNING claim_id",
        (
            subject,
            predicate,
            object_type,
            object_entity,
            value_text,
            value_bool,
            observed_at,
            None if observed_at else "fixture-undated",
            valid_lower,
            valid_upper,
            prereqs["author_id"],
            prereqs["run_id"],
            prereqs["rights_id"],
            revises_claim,
            retraction_of,
            correction_reason,
        ),
    ).fetchone()
    return cur[0]


def _lineage(conn: object, claim_id: object, source_id: str) -> None:
    conn.execute(
        "INSERT INTO claim_lineage(claim_id,source_id,id_namespace,lineage_kind,"
        "independence_class,basis) VALUES(%s,%s,'fixture','primary','fixture','fixture')",
        (claim_id, source_id),
    )


def _live_roles(conn: object, subject: object) -> list[tuple]:
    return conn.execute(
        "SELECT entity_role_id, actor_id, role, lower(valid_period), upper(valid_period),"
        "       valid_from_kind, valid_to_kind, observed_at, evidence_claim,"
        "       supersedes, superseded_by_claim, input_digest"
        "  FROM entity_role WHERE entity_id = %s AND upper_inf(sys_period)"
        " ORDER BY role, lower(valid_period) NULLS FIRST",
        (subject,),
    ).fetchall()


def _all_roles(conn: object, subject: object) -> list[tuple]:
    return conn.execute(
        "SELECT entity_role_id, actor_id, role, upper_inf(sys_period)"
        "  FROM entity_role WHERE entity_id = %s ORDER BY role, entity_role_id",
        (subject,),
    ).fetchall()


# --- the schema landed ------------------------------------------------------ #


def test_entity_role_reshape_and_relationship_supersedes_deployed(conn: object) -> None:
    # The surrogate PK + the temporal/succession columns exist.
    conn.execute(
        "SELECT entity_role_id, valid_from_kind, valid_to_kind, observed_at,"
        "       asserted_by, supersedes, superseded_by_claim, input_digest, sys_period"
        "  FROM entity_role WHERE false"
    )
    conn.execute("SELECT supersedes FROM relationship WHERE false")
    row = conn.execute(
        "SELECT 1 FROM pg_indexes WHERE indexname='entity_role_input_digest_key'"
    ).fetchone()
    assert row is not None


def test_the_closure_functions_are_materializer_only(conn: object) -> None:
    """`sig_materialize` EXECUTEs the sanctioned sys_period closures — and
    nothing else does (the caller keeps its INSERT-only posture, never UPDATE)."""
    for fn in ("close_superseded_entity_roles", "close_superseded_relationships"):
        assert conn.execute(
            "SELECT has_function_privilege('sig_materialize', %s, 'EXECUTE')",
            (f"{fn}(uuid[])",),
        ).fetchone()[0], fn
    # The materializer itself holds no UPDATE on either edge table.
    for table in ("entity_role", "relationship"):
        assert not conn.execute(
            "SELECT has_table_privilege('sig_materialize', %s, 'UPDATE')", (table,)
        ).fetchone()[0], table


def test_closed_role_vocabulary_matches_the_python_taxonomy(conn: object) -> None:
    """The CHECK's IN list is exactly ``EDGE_ROLE_VOCABULARY`` (parity of truth)."""
    cdef = conn.execute(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint"
        " WHERE conrelid='entity_role'::regclass"
        "   AND conname='entity_role_closed_vocabulary'"
    ).fetchone()[0]
    # The planner may render the list as `IN (...)` or `= ANY (ARRAY[...])`;
    # the single-quoted literals are the vocabulary either way.
    listed = set(re.findall(r"'([a-z_]+)'", cdef))
    assert listed == set(EDGE_ROLE_VOCABULARY), f"CHECK drifted: {cdef}"


def test_epoch_zero_is_rejected_at_write(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    a, b = _entity(conn), _entity(conn)
    claim = _claim(conn, prereqs, subject=a, predicate="camera_operator")
    conn.execute("SAVEPOINT sp0")
    try:
        conn.execute(
            "INSERT INTO relationship(from_entity,to_entity,edge_type,direction,"
            "valid_period,evidence_claim) VALUES(%s,%s,'operates','forward',"
            "tstzrange('1970-01-01',NULL),%s)",
            (a, b, claim),
        )
        raise AssertionError("epoch-zero relationship bound accepted")
    except psycopg.errors.CheckViolation:
        conn.execute("ROLLBACK TO SAVEPOINT sp0")
    conn.execute("SAVEPOINT sp1")
    try:
        conn.execute(
            "INSERT INTO entity_role(entity_id,actor_id,role,valid_period,evidence_claim)"
            " VALUES(%s,%s,'operator',tstzrange('1970-01-01',NULL),%s)",
            (a, b, claim),
        )
        raise AssertionError("epoch-zero entity_role bound accepted")
    except psycopg.errors.CheckViolation:
        conn.execute("ROLLBACK TO SAVEPOINT sp1")
    conn.execute("SAVEPOINT sp2")
    try:
        conn.execute(
            "INSERT INTO entity_role(entity_id,actor_id,role,valid_period,observed_at,"
            "evidence_claim) VALUES(%s,%s,'operator',tstzrange(NULL,NULL),"
            "'1970-01-01'::timestamptz,%s)",
            (a, b, claim),
        )
        raise AssertionError("epoch-zero entity_role observed_at accepted")
    except psycopg.errors.CheckViolation:
        conn.execute("ROLLBACK TO SAVEPOINT sp2")


def test_actor_null_only_for_the_unknown_marker(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    a = prereqs["subject_id"]
    claim = _claim(conn, prereqs, subject=a, predicate="operator_absent", value_bool=True)
    conn.execute("SAVEPOINT sp1")
    try:
        conn.execute(
            "INSERT INTO entity_role(entity_id,actor_id,role,valid_period,evidence_claim)"
            " VALUES(%s,NULL,'operator',tstzrange(NULL,NULL),%s)",
            (a, claim),
        )
        raise AssertionError("NULL actor on an actor role accepted")
    except psycopg.errors.CheckViolation:
        conn.execute("ROLLBACK TO SAVEPOINT sp1")
    conn.execute("SAVEPOINT sp2")
    try:
        conn.execute(
            "INSERT INTO entity_role(entity_id,actor_id,role,valid_period,evidence_claim)"
            " VALUES(%s,NULL,'not_a_role',tstzrange(NULL,NULL),%s)",
            (a, claim),
        )
        raise AssertionError("a role outside the closed vocabulary accepted")
    except psycopg.errors.CheckViolation:
        conn.execute("ROLLBACK TO SAVEPOINT sp2")
    # The marker row itself is writable.
    conn.execute(
        "INSERT INTO entity_role(entity_id,actor_id,role,valid_period,evidence_claim)"
        " VALUES(%s,NULL,'operator_unknown',tstzrange(NULL,NULL),%s)",
        (a, claim),
    )


# --- role distinction (SIG-TRUST-003) ---------------------------------------- #


def test_publisher_only_source_mints_no_operator_edge(conn: object) -> None:
    """A publishing-only source produces NO role edge — the recorded defect."""
    prereqs = seed_claim_prerequisites(conn)
    subject = prereqs["subject_id"]
    org = _entity(conn)
    # The strongest form: even a provenance-role claim carrying an entity ref
    # (a misshapen upstream) still mints nothing — the taxonomy, not the claim
    # shape, decides.
    _claim(
        conn,
        prereqs,
        subject=subject,
        predicate="camera_registry_publisher",
        object_type="entity_ref",
        object_entity=org,
        value_text="City Registry",
    )
    _claim(
        conn,
        prereqs,
        subject=subject,
        predicate="published_by",
        value_text="OpenStreetMap contributors",
    )

    summary = materialize_role_edges(conn, subject=str(subject))
    assert summary.inserted == 0
    assert summary.slots == 0
    assert _live_roles(conn, subject) == []
    # Explicit honest reading: the slot was never asked, not "absent".
    assert operator_state(conn, str(subject))["state"] == "not_asserted"


def test_operator_claim_materializes_a_dated_operator_edge(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    subject = prereqs["subject_id"]
    org = _entity(conn)
    claim = _claim(
        conn,
        prereqs,
        subject=subject,
        predicate="camera_operator",
        object_type="entity_ref",
        object_entity=org,
        value_text="Flock Safety",
        observed_at="2026-05-01T00:00:00Z",
    )

    summary = materialize_role_edges(conn, subject=str(subject))
    assert summary.inserted == 1
    assert summary.by_role == {"operator": 1}

    rows = _live_roles(conn, subject)
    assert len(rows) == 1
    (_rid, actor, role, lower, upper, from_kind, to_kind, observed, evidence, *_rest) = rows[0]
    assert str(actor) == str(org)
    assert role == "operator"
    assert from_kind == "exact"  # the claim's observed_at evidences the bound
    assert to_kind == "ongoing"
    assert str(evidence) == str(claim)
    assert observed is not None
    # operator_state reads the evidenced operator.
    state = operator_state(conn, str(subject))
    assert state["state"] == "operator"
    assert state["actors"] == [str(org)]


def test_undated_claim_produces_an_undated_edge_never_epoch(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    subject = prereqs["subject_id"]
    org = _entity(conn)
    _claim(
        conn,
        prereqs,
        subject=subject,
        predicate="camera_operator",
        object_type="entity_ref",
        object_entity=org,
        observed_at=None,  # no evidenced date anywhere on the claim
    )

    summary = materialize_role_edges(conn, subject=str(subject))
    assert summary.inserted == 1
    (_rid, _actor, _role, lower, _upper, from_kind, _to, observed, *_rest) = _live_roles(
        conn, subject
    )[0]
    assert lower is None  # UNBOUNDED valid_period — not 1970-01-01
    assert from_kind == "undated"  # the explicit marker, not a fabricated bound
    assert observed is None
    # And the structural guard: no epoch bound anywhere in the edge tables.
    epoch = conn.execute(
        "SELECT count(*) FROM entity_role"
        " WHERE lower(valid_period) = '1970-01-01'::timestamptz"
        "    OR observed_at = '1970-01-01'::timestamptz"
    ).fetchone()[0]
    assert epoch == 0


def test_operator_absent_materializes_the_unknown_state(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    subject = prereqs["subject_id"]
    claim = _claim(
        conn,
        prereqs,
        subject=subject,
        predicate="operator_absent",
        value_bool=True,
        observed_at="2026-05-01T00:00:00Z",
    )

    summary = materialize_role_edges(conn, subject=str(subject))
    assert summary.inserted == 1
    assert summary.unknown_states == 1

    rows = _live_roles(conn, subject)
    assert len(rows) == 1
    (_rid, actor, role, _lower, _upper, _fk, _tk, _obs, evidence, *_rest) = rows[0]
    assert actor is None  # no fabricated actor
    assert role == "operator_unknown"
    assert str(evidence) == str(claim)

    state = operator_state(conn, str(subject))
    assert state["state"] == "operator_unknown"
    assert state["actors"] == []


def test_unknown_state_yields_to_a_later_operator_claim(conn: object) -> None:
    """The unknown marker and an operator edge occupy the SAME slot (SIG-ONTO-028)."""
    prereqs = seed_claim_prerequisites(conn)
    subject = prereqs["subject_id"]
    org = _entity(conn)
    absent = _claim(
        conn,
        prereqs,
        subject=subject,
        predicate="operator_absent",
        value_bool=True,
        observed_at="2026-01-01T00:00:00Z",
    )
    operated = _claim(
        conn,
        prereqs,
        subject=subject,
        predicate="camera_operator",
        object_type="entity_ref",
        object_entity=org,
        observed_at="2026-06-01T00:00:00Z",
    )
    _lineage(conn, absent, "src-osm")
    _lineage(conn, operated, "src-osm")

    summary = materialize_role_edges(conn, subject=str(subject))
    assert summary.inserted == 2
    rows = _live_roles(conn, subject)
    assert len(rows) == 2
    unknown = next(r for r in rows if r[2] == "operator_unknown")
    operated_row = next(r for r in rows if r[2] == "operator")
    # The marker is closed by the later operator claim — recorded succession,
    # both rows live as belief-truth (the timeline is in valid_period).
    assert unknown[10] is not None and str(unknown[10]) == str(operated)  # superseded_by_claim
    assert str(operated_row[9]) == str(unknown[0])  # supersedes link
    assert operator_state(conn, str(subject))["state"] == "operator"


# --- supersession + idempotency ---------------------------------------------- #


def test_same_lineage_role_change_is_a_recorded_succession(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    subject = prereqs["subject_id"]
    org_a, org_b = _entity(conn), _entity(conn)
    c1 = _claim(
        conn,
        prereqs,
        subject=subject,
        predicate="camera_operator",
        object_type="entity_ref",
        object_entity=org_a,
        observed_at="2026-01-01T00:00:00Z",
    )
    c2 = _claim(
        conn,
        prereqs,
        subject=subject,
        predicate="camera_operator",
        object_type="entity_ref",
        object_entity=org_b,
        observed_at="2026-06-01T00:00:00Z",
    )
    _lineage(conn, c1, "src-registry")
    _lineage(conn, c2, "src-registry")

    summary = materialize_role_edges(conn, subject=str(subject))
    assert summary.inserted == 2

    rows = _live_roles(conn, subject)
    assert len(rows) == 2
    old = next(r for r in rows if str(r[1]) == str(org_a))
    new = next(r for r in rows if str(r[1]) == str(org_b))
    # The earlier episode's valid upper bound is set BY the succeeding claim —
    # a recorded edge succession (SIG-EPIS-029), never an in-place edit.
    assert old[4] is not None  # valid upper
    assert str(old[10]) == str(c2)  # superseded_by_claim names the corrector
    assert str(new[9]) == str(old[0])  # supersedes links the predecessor row
    # Re-run over the same claims: +0 (append-only idempotent).
    again = materialize_role_edges(conn, subject=str(subject))
    assert again.inserted == 0
    assert again.skipped_existing == 2
    assert len(_all_roles(conn, subject)) == 2


def test_cross_lineage_correction_closes_the_revised_state(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    subject = prereqs["subject_id"]
    org_a, org_b = _entity(conn), _entity(conn)
    c1 = _claim(
        conn,
        prereqs,
        subject=subject,
        predicate="camera_operator",
        object_type="entity_ref",
        object_entity=org_a,
        observed_at="2026-01-01T00:00:00Z",
    )
    # A DIFFERENT lineage corrects the first claim — revises_claim is an
    # explicit correction, not a timeline move.
    c2 = _claim(
        conn,
        prereqs,
        subject=subject,
        predicate="camera_operator",
        object_type="entity_ref",
        object_entity=org_b,
        observed_at="2026-06-01T00:00:00Z",
        revises_claim=c1,
        correction_reason="registry correction",
    )
    _lineage(conn, c1, "src-a")
    _lineage(conn, c2, "src-b")

    materialize_role_edges(conn, subject=str(subject))
    rows = _live_roles(conn, subject)
    assert len(rows) == 2
    old = next(r for r in rows if str(r[1]) == str(org_a))
    new = next(r for r in rows if str(r[1]) == str(org_b))
    assert str(old[10]) == str(c2)
    assert old[4] is not None
    # Cross-lineage: B's edge does not claim A's chain link (distinct voices).
    assert new[9] is None


def test_cross_lineage_concurrent_states_coexist(conn: object) -> None:
    """Two sources disagreeing NOW keep both edges live — never silently reconciled."""
    prereqs = seed_claim_prerequisites(conn)
    subject = prereqs["subject_id"]
    org_a, org_b = _entity(conn), _entity(conn)
    c1 = _claim(
        conn,
        prereqs,
        subject=subject,
        predicate="camera_operator",
        object_type="entity_ref",
        object_entity=org_a,
        observed_at="2026-01-01T00:00:00Z",
    )
    c2 = _claim(
        conn,
        prereqs,
        subject=subject,
        predicate="camera_operator",
        object_type="entity_ref",
        object_entity=org_b,
        observed_at="2026-06-01T00:00:00Z",
    )
    _lineage(conn, c1, "src-a")
    _lineage(conn, c2, "src-b")

    materialize_role_edges(conn, subject=str(subject))
    rows = _live_roles(conn, subject)
    # Distinct live states under distinct lineages: two open edges.
    assert len(rows) == 2
    assert all(r[4] is None for r in rows)  # neither closed
    state = operator_state(conn, str(subject))
    assert state["state"] == "operator"
    assert set(state["actors"]) == {str(org_a), str(org_b)}


def test_belief_supersession_closes_the_prior_version(conn: object) -> None:
    """A changed evidence/digest supersedes the live row — sys_period close,
    never an UPDATE (append-only)."""
    prereqs = seed_claim_prerequisites(conn)
    subject = prereqs["subject_id"]
    org = _entity(conn)
    c1 = _claim(
        conn,
        prereqs,
        subject=subject,
        predicate="camera_operator",
        object_type="entity_ref",
        object_entity=org,
        observed_at="2026-01-01T00:00:00Z",
    )
    _lineage(conn, c1, "src-registry")
    first = materialize_role_edges(conn, subject=str(subject))
    assert first.inserted == 1
    live_before = _live_roles(conn, subject)
    assert len(live_before) == 1

    # A second same-state claim in the same lineage corroborates — the open
    # state's EVIDENCE SET changes → a new digest → belief supersession.
    c2 = _claim(
        conn,
        prereqs,
        subject=subject,
        predicate="camera_operator",
        object_type="entity_ref",
        object_entity=org,
        observed_at="2026-02-01T00:00:00Z",
    )
    _lineage(conn, c2, "src-registry")
    second = materialize_role_edges(conn, subject=str(subject))
    assert second.superseded >= 1

    live_after = _live_roles(conn, subject)
    assert len(live_after) == 1
    new_row = live_after[0]
    # The new live version links the closed one; the old row stays as history.
    assert str(new_row[9]) == str(live_before[0][0])
    all_rows = _all_roles(conn, subject)
    assert len(all_rows) == 2
    closed = next(r for r in all_rows if not r[3])
    assert str(closed[0]) == str(live_before[0][0])
    # The corroborated version still points at an evidence claim (min id).
    assert new_row[8] is not None


def test_dry_run_writes_nothing(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    subject = prereqs["subject_id"]
    org = _entity(conn)
    _claim(
        conn,
        prereqs,
        subject=subject,
        predicate="camera_operator",
        object_type="entity_ref",
        object_entity=org,
    )
    summary = materialize_role_edges(conn, subject=str(subject), dry_run=True)
    assert summary.dry_run is True
    assert summary.inserted == 1  # computed, not written
    assert _live_roles(conn, subject) == []


def test_read_materialized_role_edges_returns_live_only(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    subject = prereqs["subject_id"]
    org = _entity(conn)
    claim = _claim(
        conn,
        prereqs,
        subject=subject,
        predicate="camera_operator",
        object_type="entity_ref",
        object_entity=org,
        observed_at="2026-05-01T00:00:00Z",
    )
    materialize_role_edges(conn, subject=str(subject))
    edges = read_materialized_role_edges(conn)
    ours = [e for e in edges if e["entity_id"] == str(subject)]
    assert len(ours) == 1
    e = ours[0]
    assert e["actor_id"] == str(org)
    assert e["role"] == "operator"
    assert e["evidence_claim"] == str(claim)
    assert e["valid_from"] is not None


# --- relationship edges: the same guarantees --------------------------------- #


def test_sharing_edge_supersession_closes_the_prior_live_row(conn: object) -> None:
    """P35.26 on the `relationship` table: changed evidence supersedes."""
    prereqs = seed_claim_prerequisites(conn)
    a, b = prereqs["subject_id"], _entity(conn)
    conn.execute(
        "INSERT INTO vocab_predicate"
        "(predicate_id,vocab_version,value_datatype,object_type,definition,"
        " volatility_class,half_life_days,resolution_strategy) "
        "VALUES('configured_sharing_partner','1.0.0','string','entity_ref','fixture',"
        "'MODERATE',120,'authoritative_source_wins') ON CONFLICT DO NOTHING"
    )
    _claim(
        conn,
        prereqs,
        subject=a,
        predicate="configured_sharing_partner",
        object_type="entity_ref",
        object_entity=b,
        value_text="partner",
        observed_at="2026-05-01T00:00:00Z",
    )
    first = materialize_sharing_edges(conn, subject=str(a))
    assert first.inserted == 1
    # A corroborating claim changes the evidence set → new digest → supersede.
    _claim(
        conn,
        prereqs,
        subject=a,
        predicate="configured_sharing_partner",
        object_type="entity_ref",
        object_entity=b,
        value_text="partner",
        observed_at="2026-06-01T00:00:00Z",
    )
    second = materialize_sharing_edges(conn, subject=str(a))
    assert second.inserted == 1
    assert second.superseded == 1
    live = read_materialized_edges(conn)
    ours = [e for e in live if e["from_entity"] == str(a)]
    assert len(ours) == 1  # 0 live duplicates (GQ-15)
    # The closed row stays queryable as history.
    total = conn.execute("SELECT count(*) FROM relationship WHERE from_entity=%s", (a,)).fetchone()[
        0
    ]
    closed = conn.execute(
        "SELECT count(*) FROM relationship WHERE from_entity=%s AND NOT upper_inf(sys_period)",
        (a,),
    ).fetchone()[0]
    assert total == 2 and closed == 1
    # The succession link lands on the live row.
    sup = conn.execute(
        "SELECT supersedes::text FROM relationship WHERE from_entity=%s AND upper_inf(sys_period)",
        (a,),
    ).fetchone()[0]
    assert sup is not None


def test_undated_sharing_claim_produces_an_undated_edge(conn: object) -> None:
    """The pre-fix path wrote 1970-01-01; the edge now reads undated honestly."""
    prereqs = seed_claim_prerequisites(conn)
    a, b = prereqs["subject_id"], _entity(conn)
    conn.execute(
        "INSERT INTO vocab_predicate"
        "(predicate_id,vocab_version,value_datatype,object_type,definition,"
        " volatility_class,half_life_days,resolution_strategy) "
        "VALUES('configured_sharing_partner','1.0.0','string','entity_ref','fixture',"
        "'MODERATE',120,'authoritative_source_wins') ON CONFLICT DO NOTHING"
    )
    _claim(
        conn,
        prereqs,
        subject=a,
        predicate="configured_sharing_partner",
        object_type="entity_ref",
        object_entity=b,
        value_text="partner",
        observed_at=None,
    )
    summary = materialize_sharing_edges(conn, subject=str(a))
    assert summary.inserted == 1
    row = conn.execute(
        "SELECT lower(valid_period), observed_at, valid_from_kind FROM relationship"
        " WHERE from_entity=%s",
        (a,),
    ).fetchone()
    assert row[0] is None  # unbounded — never the epoch placeholder
    assert row[1] is None
    assert row[2] == "undated"
