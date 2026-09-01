# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Dispositions and the negative-result→data bridge (§33.4).

AC4 (SIG-TASK-009): `resolved_no_evidence_exists` writes a `CoverageRecord`, so the
queue can shrink. Plus the disposition vocabulary is richer than "done"
(SIG-TASK-008).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from inference.coverage import CoverageRecord
from tasks.dispositions import resolve_no_evidence_exists
from tasks.lifecycle import ResearchTask, TaskPool
from tasks.spec import Detector, GeographicScope, TaskType
from tasks.vocabulary import AssigneeClass, Disposition, EffortEstimate, TaskStatus

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _task_type() -> TaskType:
    return TaskType(
        task_type="missing_contract",
        detector=Detector(version="v1", query=lambda facts: True),
        priority_fn=lambda facts: 1.0,
        closing_condition=lambda facts: bool(facts.get("closed", False)),
        assignee_class=AssigneeClass.RECORDS_REQUESTER,
        effort_estimate=EffortEstimate.MODERATE,
        dispositions=(
            Disposition.RESOLVED_EVIDENCE_FOUND,
            Disposition.RESOLVED_NO_EVIDENCE_EXISTS,
            Disposition.BLOCKED_FEE,
        ),
        geographic_scope=GeographicScope.JURISDICTION,
    )


def _verified_task(subject: str | None = "agency:okcpd") -> ResearchTask:
    pool = TaskPool()
    task = pool.generate(_task_type(), subject, facts={}, now=_NOW)
    assert task is not None
    task.triage()
    task.claim("alice", now=_NOW, timeout=timedelta(days=7))
    task.start()
    task.submit()
    task.verify()
    return task


def test_disposition_vocabulary_is_richer_than_done() -> None:
    """SIG-TASK-008: the eight §33.4 dispositions all exist."""
    assert {d.value for d in Disposition} == {
        "resolved_evidence_found",
        "resolved_no_evidence_exists",
        "blocked_access_denied",
        "blocked_fee",
        "blocked_awaiting_response",
        "not_actionable",
        "superseded",
        "deferred",
    }


def test_resolved_no_evidence_exists_writes_a_coverage_record() -> None:
    """AC4 / SIG-TASK-009: the negative result becomes queryable data."""
    task = _verified_task()
    coverage = resolve_no_evidence_exists(
        task,
        predicate_id="contracted_device_count",
        sources_searched=("MuckRock request #123", "agency portal"),
        searched_at=_NOW,
        searched_by="alice",
        search_method="records_request",
    )
    assert isinstance(coverage, CoverageRecord)
    assert coverage.absence_kind == "searched_not_found"
    assert coverage.subject_id == "agency:okcpd"
    assert coverage.sources_searched == ("MuckRock request #123", "agency portal")
    # And the task is closed with the disposition.
    assert task.status is TaskStatus.CLOSED
    assert task.disposition is Disposition.RESOLVED_NO_EVIDENCE_EXISTS


def test_no_evidence_without_sources_is_refused_before_the_task_closes() -> None:
    """SIG-TASK-009 inherits SIG-METRIC-002: an anonymous negative is rejected."""
    task = _verified_task()
    with pytest.raises(ValueError, match="SIG-METRIC-001/002"):
        resolve_no_evidence_exists(
            task,
            predicate_id="contracted_device_count",
            sources_searched=(),  # named nothing
        )
    # The task did NOT close — the record must exist first, so a failed record
    # leaves the task open (the queue does not shrink on an unrecorded negative).
    assert task.status is TaskStatus.VERIFIED
    assert task.disposition is None


def test_no_evidence_exists_is_unreachable_through_plain_close() -> None:
    """The only path to the coverage-writing disposition is the bridge (SIG-TASK-009)."""
    task = _verified_task()
    with pytest.raises(ValueError, match="MUST write a CoverageRecord"):
        task.close(Disposition.RESOLVED_NO_EVIDENCE_EXISTS)
    assert task.status is TaskStatus.VERIFIED


def test_class_scoped_negative_uses_subject_class() -> None:
    task = _verified_task(subject=None)
    coverage = resolve_no_evidence_exists(
        task,
        predicate_id="portal_exists",
        sources_searched=("statewide portal probe",),
        subject_class="agency",
    )
    assert coverage.subject_id is None
    assert coverage.subject_class == "agency"
