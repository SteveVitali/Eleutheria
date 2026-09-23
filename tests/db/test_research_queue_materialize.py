# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P29.2 — the detector run persists the research queue over real PG18+PostGIS.

The §33.2 catalog is run over the Round-6 MATERIALIZED graph (the ``contradiction`` /
``coverage_record`` tables the P28.3/P28.4 materializers write — SIG-ENG-035, consumed not
re-derived here) and the research queue is written as durable, append-only ``research_task``
rows, each **citing its trigger**. Records requests are DRAFTED, never sent. This proves the
write path + the export read-back over the real schema; the pure routing/drafting is proven
in ``tests/tasks/test_tasks_detect.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from conftest import insert_claim, seed_claim_prerequisites
from tasks.research_pg import materialize_research_queue, read_materialized_inputs

NOW = datetime(2026, 9, 23, 12, 0, 0, tzinfo=UTC)


def _seed_materialized_contradiction(cur, *, subject, predicate, claim_ids, ctype, digest) -> str:
    """Write a materialized ``contradiction`` row directly (what P28.3 materializes)."""
    cur.execute(
        "INSERT INTO contradiction"
        "(subject_id, predicate_id, contradiction_type, claim_ids, severity, status, input_digest) "
        "VALUES(%s,%s,%s,%s,'notable','open',%s) RETURNING contradiction_id",
        (subject, predicate, ctype, claim_ids, digest),
    )
    return str(cur.fetchone()[0])


def _seed_materialized_coverage(
    cur, *, subject, predicate, digest, absence="not_researched"
) -> str:
    """Write a materialized ``coverage_record`` gap row directly (what P28.4 materializes)."""
    cur.execute(
        "INSERT INTO coverage_record"
        "(subject_id, subject_class, predicate_id, absence_kind, input_digest) "
        "VALUES(%s,'deployment',%s,%s,%s) RETURNING coverage_id",
        (subject, predicate, absence, digest),
    )
    return str(cur.fetchone()[0])


def test_research_queue_materialized_from_contradiction_and_coverage(conn) -> None:
    cur = conn.cursor()
    prereqs = seed_claim_prerequisites(conn)
    subject = prereqs["subject_id"]
    predicate = prereqs["predicate_id"]
    claim_a = insert_claim(conn, prereqs, value_text="30", value_num=30)
    claim_b = insert_claim(conn, prereqs, value_text="19", value_num=19)
    # A human agency label so the records-request draft names a target agency.
    cur.execute(
        "INSERT INTO entity_identifier(entity_id, scheme, value) VALUES(%s,'label',%s)",
        (subject, "Oklahoma City PD"),
    )

    con_id = _seed_materialized_contradiction(
        cur,
        subject=subject,
        predicate=predicate,
        claim_ids=[claim_a, claim_b],
        ctype="policy_configuration_divergence",  # → conflicting_retention (records_requester)
        digest="p292-con-1",
    )
    cov_id = _seed_materialized_coverage(
        cur, subject=subject, predicate=predicate, digest="p292-cov-1"
    )

    # The read seam picks up exactly the two materialized rows.
    inputs = read_materialized_inputs(conn)
    assert len(inputs.contradictions) == 1
    assert len(inputs.coverage) == 1

    summary, result = materialize_research_queue(conn, now=NOW, jurisdiction_key="OK")
    assert summary.written == 2
    assert summary.skipped_existing == 0
    assert summary.skipped_no_entity == 0

    rows = cur.execute(
        "SELECT task_type, subject_id::text, trigger_kind, trigger_ref, closing_condition, "
        "       detector_version FROM research_task ORDER BY task_type"
    ).fetchall()
    by_type = {r[0]: r for r in rows}
    # The contradiction routes to conflicting_retention; the coverage gap on a records-obtainable
    # predicate (contracted_camera_count) routes to missing_contract.
    assert set(by_type) == {"conflicting_retention", "missing_contract"}
    # Every persisted task CITES ITS TRIGGER (the materialized row id).
    assert by_type["conflicting_retention"][2] == "contradiction"
    assert by_type["conflicting_retention"][3] == con_id
    assert by_type["missing_contract"][2] == "coverage"
    assert by_type["missing_contract"][3] == cov_id
    # SIG-TASK-002: a testable closing condition is stored, never "research this".
    for r in rows:
        assert r[4] and "research this" not in r[4].lower()
        assert r[5]  # a detector version is stamped

    # Records requests are DRAFTED (the records-requester task), never sent.
    assert summary.records_request_drafts >= 1
    assert summary.records_requests_sent == 0
    draft = next(d for d in result.drafts if d.task_type == "conflicting_retention")
    assert draft.status == "drafted"
    assert draft.records_law_key == "OK"
    assert draft.statutory_citation

    # Idempotent: a re-run over the unchanged materialized spine writes +0 (SIG-TASK-007).
    summary2, _ = materialize_research_queue(conn, now=NOW, jurisdiction_key="OK")
    assert summary2.written == 0
    assert summary2.skipped_existing == 2


def test_export_reads_the_materialized_research_queue_with_its_trigger(conn) -> None:
    import json

    from exports.spine_export import run_spine_export

    cur = conn.cursor()
    prereqs = seed_claim_prerequisites(conn)
    subject = prereqs["subject_id"]
    predicate = prereqs["predicate_id"]
    claim_a = insert_claim(conn, prereqs, value_text="30", value_num=30)
    claim_b = insert_claim(conn, prereqs, value_text="19", value_num=19)
    con_id = _seed_materialized_contradiction(
        cur,
        subject=subject,
        predicate=predicate,
        claim_ids=[claim_a, claim_b],
        ctype="value_disagreement",
        digest="p292-con-2",
    )
    materialize_research_queue(conn, now=NOW)

    export = run_spine_export(conn, as_of="2026-09-23", note="p292", spine_label="seeded")
    queue = json.loads(export.web_artifacts["web/research_queue.json"])
    assert len(queue) == 1
    card = queue[0]
    assert card["closing_condition"]
    # The public surface carries the trigger citation (P29.2).
    assert card["trigger"]["kind"] == "contradiction"
    assert card["trigger"]["ref"] == con_id


def test_empty_materialized_tables_degrade_to_no_tasks(conn) -> None:
    # No materialized rows (input_digest IS NULL everywhere) → an honest empty queue,
    # never a fabricated task (the D-R6.x hosted-materialization live gate).
    seed_claim_prerequisites(conn)
    inputs = read_materialized_inputs(conn)
    assert inputs.contradictions == []
    assert inputs.coverage == []
    assert inputs.edges == []
    summary, _ = materialize_research_queue(conn, now=NOW, jurisdiction_key="OK")
    assert summary.generated == 0
    assert summary.written == 0
    assert summary.records_request_drafts == 0


@pytest.mark.parametrize("absence", ["evidence_of_absence", "not_applicable"])
def test_non_gap_coverage_absence_generates_no_task(conn, absence) -> None:
    cur = conn.cursor()
    prereqs = seed_claim_prerequisites(conn)
    _seed_materialized_coverage(
        cur,
        subject=prereqs["subject_id"],
        predicate=prereqs["predicate_id"],
        digest=f"p292-cov-{absence}",
        absence=absence,
    )
    summary, _ = materialize_research_queue(conn, now=NOW)
    assert summary.written == 0
