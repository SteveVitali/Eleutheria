# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Whole-graph TI-6/TI-7 audits over a real spine (P37.57b / R11-DEBT-01b).

ADR-025 deferred this: ``db.invariants`` checks TI-6/TI-7 over the batch a
connector is about to assert, but "a full-graph audit remains a separate
nightly job". :mod:`db.graph_audit` is that job — a read-only pass over the
whole deployed schema. This suite runs it on real PG18+PostGIS
(testcontainers):

* the seeded + materialized spine (``test_projection_rebuild``'s fixture, so
  the audit reads real resolver output, not hand-shaped rows) reports **0
  violations** — the catalog's "audits report 0 violations" acceptance;
* injected TI-6 violations a single-batch check could never see — two
  resolutions inside one §13.4 exclusive group whose ``valid_period``s AND
  ``sys_period``s overlap — are reported with their subjects;
* injected TI-7 violations — a ``revises_claim`` cycle (constructed past the
  append-only trigger, the only way one can exist), a forward-pointer cycle,
  a merge cycle, and a dangling pointer (constructed with the foreign key
  bypassed — the termination failure TI-7 also names) — are reported per
  surface;
* the drift guard proves the declared surface registry covers every
  self-referencing foreign key in the deployed schema, so a new supersedes
  surface can never silently go un-audited.

The negative fixtures are injected with superuser DDL/DML the writer roles
cannot perform — deliberately: the audit exists for exactly the case a
constraint cannot express (ADR-025's revisit trigger).
"""

from __future__ import annotations

import uuid
from typing import Any

import psycopg
import pytest
from conftest import insert_claim, register_vocab_predicate, seed_claim_prerequisites
from db.graph_audit import (
    MUTUALLY_EXCLUSIVE_GROUPS,
    SUPERSEDES_SURFACES,
    audit_graph,
    audit_ti6,
    audit_ti7,
    run,
    self_referencing_fks,
    undeclared_self_fks,
)
from test_projection_rebuild import _materialize_all, _seed_spine, _source_capture

from db import cli as db_cli

#: The four §13.4 tracks, as predicate ids. ``physical_state`` is declared in
#: the ontology and in the audit's exclusive set but is not (yet) a seeded
#: ``vocab_predicate`` row — the fixture registers it like any other.
TRACK_PREDICATES = (
    "procurement_state",
    "physical_state",
    "operational_state",
    "authorization_state",
)


def _seed_resolution_vocab(conn: Any) -> None:
    conn.execute(
        "INSERT INTO vocab_confidence(confidence,definition) VALUES('high','h') "
        "ON CONFLICT DO NOTHING"
    )
    conn.execute(
        "INSERT INTO vocab_rationale(rationale_code,template) VALUES('single','t') "
        "ON CONFLICT DO NOTHING"
    )


def _resolution(
    conn: Any,
    subject: Any,
    predicate: str,
    *,
    valid: tuple[str | None, str | None],
    belief: tuple[str | None, str | None],
) -> Any:
    """One resolution row with an explicit valid AND belief window.

    A bounded ``sys_period`` is the historical record — excluded from the
    ``resolution_no_overlap`` EXCLUDE (``WHERE upper_inf(sys_period)``), which
    is exactly why an *audit* must check coexistence across belief time.
    """
    return conn.execute(
        "INSERT INTO resolution(subject_id,predicate_id,value_kind,value_text,"
        "valid_period,sys_period,considered_claims,contradiction_state,"
        "strategy_id,rationale_code,rationale_text,confidence,evidence_counts,"
        "resolver_version,ruleset_version) "
        "VALUES(%s,%s,'value','installed',tstzrange(%s,%s,'[)'),"
        "tstzrange(%s,%s,'[)'),'{}','uncontested','authoritative_source_wins',"
        "'single','because','high','{}','v1','r1') RETURNING resolution_id",
        (subject, predicate, *valid, *belief),
    ).fetchone()[0]


def _register_tracks(conn: Any) -> None:
    for pid in TRACK_PREDICATES:
        register_vocab_predicate(conn, pid, datatype="lifecycle state")


def _dsn(params: dict[str, object]) -> str:
    return (
        f"postgresql://{params['user']}:{params['password']}"
        f"@{params['host']}:{params['port']}/{params['dbname']}"
    )


# --- the clean whole-graph pass ---------------------------------------------


def test_seeded_materialized_spine_audits_clean(conn: Any) -> None:
    """The catalog acceptance: the audit over the real seeded+materialized
    spine reports 0 violations — and the pass is not vacuous (resolutions were
    scanned, every declared surface was walked)."""
    prereqs = _seed_spine(conn)
    _materialize_all(conn)
    _register_tracks(conn)
    _seed_resolution_vocab(conn)
    subject = prereqs["subject_id"]

    # A legal §13.4 state per track + a sanctioned supersession (closed belief
    # window before the live successor) — the shape TI-6 MUST NOT flag.
    _resolution(conn, subject, "procurement_state", valid=("2020-01-01", None), belief=(None, None))
    _resolution(conn, subject, "physical_state", valid=("2020-01-01", None), belief=(None, None))
    _resolution(conn, subject, "operational_state", valid=("2021-01-01", None), belief=(None, None))
    _resolution(
        conn,
        subject,
        "authorization_state",
        valid=("2020-01-01", None),
        belief=("2020-01-01", "2021-01-01"),
    )
    _resolution(
        conn,
        subject,
        "authorization_state",
        valid=("2020-06-01", None),
        belief=("2021-01-01", None),
    )

    # Succession chains so TI-7's walk is non-vacuous: a §16.6 correction, an
    # entity merge, and a redacted-derivative capture lineage.
    c1 = insert_claim(conn, prereqs)
    insert_claim(conn, prereqs, revises_claim=c1, correction_reason="fixture fix")
    e_new = conn.execute(
        "INSERT INTO entity(entity_type) VALUES('deployment') RETURNING entity_id"
    ).fetchone()[0]
    conn.execute(
        "UPDATE entity SET merged_into=%s WHERE entity_id=%s", (e_new, prereqs["subject_id"])
    )
    parent = _source_capture(conn, prereqs, "audit_parent_src", "camera_registry")
    artifact = conn.execute(
        "SELECT artifact_id FROM evidence_capture WHERE capture_id=%s", (parent,)
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,"
        "media_type,retrieved_at,retrieved_by_run_id,ocfl_object_id,ocfl_version,"
        "storage_tier,capture_method,capture_tool_version,source_uri,"
        "parent_capture_id) VALUES(%s,%s,10,'application/json',"
        "'2026-05-02T00:00:00Z',%s,%s,'v2','public','registry_api','sig/0',%s,%s)",
        (
            artifact,
            "digest-audit-child",
            prereqs["run_id"],
            "urn:sig:p3757b:child",
            "urn:sig:p3757b:child",
            parent,
        ),
    )

    report = audit_graph(conn)
    assert report.ok, report.as_dict()
    assert report.resolutions_scanned > 0
    # every declared surface was walked — none skipped, even the empty ones
    assert set(report.edges_walked) == {f"{s.table}.{s.pointer}" for s in SUPERSEDES_SURFACES}
    assert report.edges_walked["claim.revises_claim"] >= 1
    assert report.edges_walked["entity.merged_into"] >= 1
    assert report.edges_walked["evidence_capture.parent_capture_id"] >= 1
    assert report.unaudited_self_fks == []


# --- TI-6 over the whole graph -----------------------------------------------


def test_ti6_flags_coexisting_overlap_inside_one_track(conn: Any) -> None:
    """Two ``physical_state`` resolutions on one subject whose valid periods
    overlap AND whose belief windows overlap — at some belief instant the L3
    view held two mutually exclusive states. Both rows are closed, so the
    EXCLUDE never saw them: this is the case only a whole-graph audit finds."""
    prereqs = seed_claim_prerequisites(conn)
    _register_tracks(conn)
    _seed_resolution_vocab(conn)
    subject = prereqs["subject_id"]
    r1 = _resolution(
        conn,
        subject,
        "physical_state",
        valid=("2020-01-01", None),
        belief=("2020-01-01", "2022-01-01"),
    )
    r2 = _resolution(
        conn,
        subject,
        "physical_state",
        valid=("2021-01-01", None),
        belief=("2021-01-01", "2023-01-01"),
    )
    violations = audit_ti6(conn)
    assert len(violations) == 1
    v = violations[0]
    assert v.invariant == "TI-6"
    assert v.subject == str(subject)
    assert str(r1) in v.reason and str(r2) in v.reason
    assert "belief" in v.reason


def test_ti6_flags_a_live_overlap(conn: Any) -> None:
    """The live-view case (the EXCLUDE's own guard): two coexisting *live*
    resolutions inside one group — constructible only past the constraint —
    is reported as the current-view violation, not history."""
    prereqs = seed_claim_prerequisites(conn)
    _register_tracks(conn)
    _seed_resolution_vocab(conn)
    subject = prereqs["subject_id"]
    _resolution(
        conn,
        subject,
        "operational_state",
        valid=("2020-01-01", None),
        belief=("2020-01-01", "2028-01-01"),  # future-ok: synthetic: window bound
    )
    live = _resolution(
        conn,
        subject,
        "operational_state",
        valid=("2021-01-01", None),
        belief=(None, None),
    )
    violations = audit_ti6(conn)
    assert len(violations) == 1
    assert str(live) in violations[0].reason
    assert "belief" in violations[0].reason


def test_ti6_orthogonal_tracks_and_belief_succession_are_legal(conn: Any) -> None:
    """SIG-ONTO-061 is the point: four tracks are orthogonal, so a subject may
    hold one resolved state per track at one instant. And belief-time
    succession — the sanctioned close-then-supersede — has disjoint
    ``sys_period``s by construction and is legal."""
    prereqs = seed_claim_prerequisites(conn)
    _register_tracks(conn)
    _seed_resolution_vocab(conn)
    subject = prereqs["subject_id"]
    other = conn.execute(
        "INSERT INTO entity(entity_type) VALUES('deployment') RETURNING entity_id"
    ).fetchone()[0]
    # one state per track, all coexisting — orthogonal, legal
    for pid in TRACK_PREDICATES:
        if pid == "physical_state":
            continue  # its rows are the sanctioned-succession pair below
        _resolution(conn, subject, pid, valid=("2020-01-01", None), belief=(None, None))
    # sanctioned supersession: prior closed before the live successor was believed
    _resolution(
        conn,
        subject,
        "physical_state",
        valid=("2020-01-01", None),
        belief=("2020-01-01", "2021-01-01"),
    )
    _resolution(
        conn,
        subject,
        "physical_state",
        valid=("2020-01-01", None),
        belief=("2021-01-01", None),
    )
    # a different subject's overlapping interval never conflicts
    _resolution(conn, other, "physical_state", valid=("2020-01-01", None), belief=(None, None))
    assert audit_ti6(conn) == []


def test_ti6_declared_groups_widen_the_check(conn: Any) -> None:
    """The group declaration is the contract: declaring the two orthogonal
    tracks as one exclusive group makes their coexistence a violation — the
    default set never does (SIG-ONTO-061)."""
    prereqs = seed_claim_prerequisites(conn)
    _register_tracks(conn)
    _seed_resolution_vocab(conn)
    subject = prereqs["subject_id"]
    _resolution(conn, subject, "physical_state", valid=("2020-01-01", None), belief=(None, None))
    _resolution(conn, subject, "operational_state", valid=("2020-01-01", None), belief=(None, None))
    assert audit_ti6(conn) == []  # orthogonal tracks, default groups
    widened = audit_ti6(conn, groups=[frozenset({"physical_state", "operational_state"})])
    assert len(widened) == 1
    assert widened[0].invariant == "TI-6"


def test_exclusive_groups_name_the_four_lifecycle_tracks() -> None:
    """The declared set IS §13.4's four tracks, each its own group — a fifth
    group or a merged group would mis-declare the spec's model."""
    assert MUTUALLY_EXCLUSIVE_GROUPS == tuple(frozenset({p}) for p in TRACK_PREDICATES)


# --- TI-7 over the whole graph -----------------------------------------------


def test_ti7_revises_claim_cycle_is_flagged(conn: Any) -> None:
    """A revises_claim 2-cycle — only constructible past the append-only
    trigger (revises_claim is a guarded column) — is reported with its
    cycle path. The trigger stays disabled for the injection and is
    re-enabled before the assertion."""
    prereqs = seed_claim_prerequisites(conn)
    c1 = insert_claim(conn, prereqs)
    c2 = insert_claim(conn, prereqs, revises_claim=c1, correction_reason="fixture fix")
    conn.execute("ALTER TABLE claim DISABLE TRIGGER claim_append_only_trg")
    try:
        conn.execute(
            "UPDATE claim SET revises_claim=%s, correction_reason='cycle fixture' "
            "WHERE claim_id=%s",
            (c2, c1),
        )
    finally:
        conn.execute("ALTER TABLE claim ENABLE TRIGGER claim_append_only_trg")
    violations, _ = audit_ti7(conn)
    revises = [v for v in violations if v.subject == "claim.revises_claim"]
    assert len(revises) == 1
    assert "cycles" in revises[0].reason
    assert str(c1) in revises[0].reason and str(c2) in revises[0].reason


def test_ti7_forward_pointer_and_merge_cycles_are_flagged(conn: Any) -> None:
    """Forward ``superseded_by`` links and the ``merged_into`` lineage chain
    are the same acyclic-and-terminating contract, walked in the direction
    stored."""
    prereqs = seed_claim_prerequisites(conn)
    conn.execute(
        "INSERT INTO vocab_predicate(predicate_id,vocab_version,value_datatype,"
        "object_type,definition,volatility_class,half_life_days,"
        "resolution_strategy) "
        "VALUES('sig.test.p_a','1.0.0','string','literal','fixture','MODERATE',"
        "365,'authoritative_source_wins')"
    )
    conn.execute(
        "INSERT INTO vocab_predicate(predicate_id,vocab_version,value_datatype,"
        "object_type,definition,volatility_class,half_life_days,"
        "resolution_strategy) "
        "VALUES('sig.test.p_b','1.0.0','string','literal','fixture','MODERATE',"
        "365,'authoritative_source_wins')"
    )
    conn.execute(
        "UPDATE vocab_predicate SET superseded_by='sig.test.p_b' WHERE predicate_id='sig.test.p_a'"
    )
    conn.execute(
        "UPDATE vocab_predicate SET superseded_by='sig.test.p_a' WHERE predicate_id='sig.test.p_b'"
    )
    e_b = conn.execute(
        "INSERT INTO entity(entity_type) VALUES('deployment') RETURNING entity_id"
    ).fetchone()[0]
    conn.execute(
        "UPDATE entity SET merged_into=%s WHERE entity_id=%s", (e_b, prereqs["subject_id"])
    )
    conn.execute(
        "UPDATE entity SET merged_into=%s WHERE entity_id=%s", (prereqs["subject_id"], e_b)
    )
    violations, walked = audit_ti7(conn)
    surfaces = {v.subject for v in violations}
    assert "vocab_predicate.superseded_by" in surfaces
    assert "entity.merged_into" in surfaces
    assert walked["vocab_predicate.superseded_by"] >= 2
    assert walked["entity.merged_into"] >= 2


def test_ti7_dangling_pointer_is_a_termination_failure(conn: Any) -> None:
    """A pointer whose target is not a row — constructible only with the FK
    bypassed (``session_replication_role=replica`` disables the constraint
    triggers) — is a chain that cannot terminate inside the graph."""
    prereqs = seed_claim_prerequisites(conn)
    ghost = str(uuid.uuid4())
    conn.execute("SET session_replication_role = 'replica'")
    try:
        insert_claim(conn, prereqs, revises_claim=ghost, correction_reason="dangling fixture")
    finally:
        conn.execute("SET session_replication_role = 'origin'")
    violations, _ = audit_ti7(conn)
    dangling = [
        v for v in violations if v.subject == "claim.revises_claim" and "off the graph" in v.reason
    ]
    assert len(dangling) == 1
    assert ghost in dangling[0].reason


# --- the drift guard ---------------------------------------------------------


def test_declared_surfaces_cover_every_schema_self_fk(conn: Any) -> None:
    """Every self-referencing foreign key in the deployed schema is a declared,
    audited surface — a new supersedes pointer added by a later migration
    fails here until it is declared (never silently un-audited)."""
    live = self_referencing_fks(conn)
    declared = {(s.schema, s.table, s.pointer) for s in SUPERSEDES_SURFACES}
    assert live == declared
    assert undeclared_self_fks(conn) == []


def test_unaudited_self_fk_fails_the_report(conn: Any) -> None:
    """A schema drift is loud: an added self-FK the registry does not name
    makes the report red, not quietly skipped."""
    conn.execute("ALTER TABLE entity ADD COLUMN sig_test_selfref uuid REFERENCES entity(entity_id)")
    report = audit_graph(conn)
    assert not report.ok
    assert "public.entity.sig_test_selfref" in report.unaudited_self_fks


# --- the CLI -----------------------------------------------------------------


def test_graph_audit_cli(sig_database: dict[str, object]) -> None:
    """``sig-db graph-audit --dsn …`` is the runnable nightly job: JSON report
    on stdout, exit 0 when clean, exit 3 on violations. Seeds its own
    committed violation (the ``conn`` fixture's writes are never visible to a
    second connection) and cleans it up."""
    dsn = _dsn(sig_database)
    report = run(dsn)
    for key in ("ok", "resolutions_scanned", "edges_walked", "unaudited_self_fks", "violations"):
        assert key in report
    e_a = e_b = None
    with psycopg.connect(dsn, autocommit=True) as conn:
        e_a, e_b = [
            conn.execute(
                "INSERT INTO entity(entity_type) VALUES('deployment') RETURNING entity_id"
            ).fetchone()[0]
            for _ in range(2)
        ]
        conn.execute("UPDATE entity SET merged_into=%s WHERE entity_id=%s", (e_b, e_a))
        conn.execute("UPDATE entity SET merged_into=%s WHERE entity_id=%s", (e_a, e_b))
    try:
        assert db_cli.main(["graph-audit", "--dsn", dsn]) == 3
        assert run(dsn)["ok"] is False
    finally:
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute("DELETE FROM entity WHERE entity_id IN (%s,%s)", (e_a, e_b))


@pytest.mark.parametrize("argv", [["graph-audit"], ["graph-audit", "--help"]])
def test_graph_audit_cli_arg_errors(argv: list[str]) -> None:
    with pytest.raises(SystemExit):
        db_cli.main(argv)
