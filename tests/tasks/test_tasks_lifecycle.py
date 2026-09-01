# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The task lifecycle and pool (§33.3).

AC2 (SIG-TASK-006): a task auto-invalidates when its detector stops firing — evidence
arriving by another route silently closes it. Plus the lifecycle state machine
(SIG-TASK-005), duplicate suppression + claim timeout (SIG-TASK-007), and per-subject
rate limiting (SIG-TASK-013).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from tasks.lifecycle import IllegalTransitionError, RateLimiter, ResearchTask, TaskPool
from tasks.spec import Detector, GeographicScope, TaskType
from tasks.vocabulary import AssigneeClass, Disposition, EffortEstimate, TaskStatus

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _task_type(*, fires_key: str = "fires", slug: str = "missing_contract") -> TaskType:
    return TaskType(
        task_type=slug,
        detector=Detector(version="v1", query=lambda facts: bool(facts.get(fires_key, True))),
        priority_fn=lambda facts: float(facts.get("priority", 1.0)),
        closing_condition=lambda facts: bool(facts.get("closed", False)),
        assignee_class=AssigneeClass.RECORDS_REQUESTER,
        effort_estimate=EffortEstimate.MODERATE,
        dispositions=(Disposition.RESOLVED_EVIDENCE_FOUND, Disposition.NOT_ACTIONABLE),
        geographic_scope=GeographicScope.JURISDICTION,
    )


def _generated(pool: TaskPool, subject: str = "agency:okcpd") -> ResearchTask:
    task = pool.generate(_task_type(), subject, facts={"priority": 3.0}, now=_NOW)
    assert task is not None
    return task


# --- lifecycle state machine (SIG-TASK-005) ----------------------------------


def test_happy_path_traversal() -> None:
    task = _generated(TaskPool())
    task.triage()
    task.claim("alice", now=_NOW, timeout=timedelta(days=7))
    task.start()
    task.submit()
    task.verify()
    task.close(Disposition.RESOLVED_EVIDENCE_FOUND)
    assert task.status is TaskStatus.CLOSED
    assert task.disposition is Disposition.RESOLVED_EVIDENCE_FOUND


def test_illegal_transition_is_refused() -> None:
    task = _generated(TaskPool())
    with pytest.raises(IllegalTransitionError, match="→"):
        task.submit()  # generated → submitted is not a legal edge


def test_a_task_may_close_early_with_a_non_verification_disposition() -> None:
    """§33.4: not_actionable/superseded/deferred conclude before full verification."""
    pool = TaskPool()
    task = _generated(pool)
    task.triage()
    task.claim("a", now=_NOW, timeout=timedelta(days=1))
    task.close(Disposition.NOT_ACTIONABLE)  # detector fired on a modelling artifact
    assert task.status is TaskStatus.CLOSED
    assert task.disposition is Disposition.NOT_ACTIONABLE


def test_an_invalidated_task_can_be_reopened_when_evidence_changes() -> None:
    """SIG-TASK-006/007: invalidation is not a dead-end under (task_type, subject)."""
    pool = TaskPool()
    task = _generated(pool)
    task.triage()
    pool.sweep_invalidations({"agency:okcpd": {"fires": False}})
    assert task.status is TaskStatus.INVALIDATED
    # The evidence later changes; the same task row is reopened rather than dead-ended.
    task.reopen()
    assert task.status is TaskStatus.REOPENED
    task.triage()
    assert task.status is TaskStatus.TRIAGED


def test_close_requires_a_permitted_disposition() -> None:
    task = _generated(TaskPool())
    task.triage()
    task.claim("a", now=_NOW, timeout=timedelta(days=1))
    task.start()
    task.submit()
    task.verify()
    with pytest.raises(ValueError, match="not permitted"):
        task.close(Disposition.SUPERSEDED)  # not in this type's dispositions[]


# --- auto-invalidation (AC2 / SIG-TASK-006) ----------------------------------


def test_auto_invalidate_when_detector_stops_firing() -> None:
    """AC2: evidence arriving by another route silently closes the task."""
    pool = TaskPool()
    task = _generated(pool)
    task.triage()
    # The detector no longer fires for this subject (evidence arrived elsewhere).
    invalidated = pool.sweep_invalidations({"agency:okcpd": {"fires": False}})
    assert invalidated == [task]
    assert task.status is TaskStatus.INVALIDATED
    assert not task.is_open


def test_a_task_whose_detector_still_fires_is_not_swept() -> None:
    pool = TaskPool()
    task = _generated(pool)
    task.triage()
    kept = pool.sweep_invalidations({"agency:okcpd": {"fires": True}})
    assert kept == []
    assert task.status is TaskStatus.TRIAGED


def test_a_subject_absent_from_the_facts_is_left_unchanged() -> None:
    pool = TaskPool()
    task = _generated(pool)
    task.triage()
    kept = pool.sweep_invalidations({})  # no fact for this subject
    assert kept == []
    assert task.is_open


def test_a_closed_task_is_not_reinvalidated() -> None:
    pool = TaskPool()
    task = _generated(pool)
    task.triage()
    task.claim("a", now=_NOW, timeout=timedelta(days=1))
    task.start()
    task.submit()
    task.verify()
    task.close(Disposition.RESOLVED_EVIDENCE_FOUND)
    swept = pool.sweep_invalidations({"agency:okcpd": {"fires": False}})
    assert swept == []  # terminal tasks are not swept
    assert task.status is TaskStatus.CLOSED


# --- duplicate suppression (SIG-TASK-007) ------------------------------------


def test_duplicate_suppression_by_task_type_and_subject() -> None:
    pool = TaskPool()
    first = _generated(pool)
    second = pool.generate(_task_type(), "agency:okcpd", facts={}, now=_NOW)
    assert second is first  # same (task_type, subject) → same task
    assert len(pool) == 1


def test_different_subjects_are_distinct_tasks() -> None:
    pool = TaskPool()
    a = _generated(pool, "agency:a")
    b = _generated(pool, "agency:b")
    assert a is not b
    assert len(pool) == 2


# --- claim timeout (SIG-TASK-007) --------------------------------------------


def test_expired_claim_returns_to_the_pool() -> None:
    pool = TaskPool()
    task = _generated(pool)
    task.triage()
    task.claim("alice", now=_NOW, timeout=timedelta(hours=48))
    assert task.status is TaskStatus.CLAIMED
    # Before the deadline: nothing reclaimed.
    assert pool.reclaim_expired(_NOW + timedelta(hours=1)) == []
    # After the deadline: released back to triaged, claim cleared.
    reclaimed = pool.reclaim_expired(_NOW + timedelta(hours=49))
    assert reclaimed == [task]
    assert task.status is TaskStatus.TRIAGED
    assert task.claimed_by is None
    assert task.claim_expires_at is None


# --- per-subject rate limiting (SIG-TASK-013) --------------------------------


def test_rate_limiter_caps_generation_per_subject() -> None:
    limiter = RateLimiter(max_per_window=3, window=timedelta(hours=1))
    for _ in range(3):
        assert limiter.allow("agency:bad", _NOW) is True
    assert limiter.allow("agency:bad", _NOW) is False  # 4th within window refused
    # A different subject is unaffected — the limit is per subject.
    assert limiter.allow("agency:other", _NOW) is True


def test_rate_limiter_is_a_rate_not_a_ban() -> None:
    limiter = RateLimiter(max_per_window=1, window=timedelta(hours=1))
    assert limiter.allow("s", _NOW) is True
    assert limiter.allow("s", _NOW) is False
    # Once the window passes, generation is allowed again.
    assert limiter.allow("s", _NOW + timedelta(hours=2)) is True


def test_pool_refuses_to_flood_one_subject_with_task_types() -> None:
    """SIG-TASK-013: one badly-modelled subject cannot flood the queue."""
    pool = TaskPool(rate_limiter=RateLimiter(max_per_window=2, window=timedelta(hours=1)))
    subject = "agency:badly_modelled"
    made = [
        pool.generate(_task_type(slug=f"type_{i}"), subject, facts={}, now=_NOW) for i in range(4)
    ]
    created = [t for t in made if t is not None]
    assert len(created) == 2  # two admitted, two refused (None)
    assert made[2] is None and made[3] is None


def test_deduplicated_generation_does_not_consume_rate_budget() -> None:
    pool = TaskPool(rate_limiter=RateLimiter(max_per_window=2, window=timedelta(hours=1)))
    first = pool.generate(_task_type(), "agency:x", facts={}, now=_NOW)
    # Re-generating the same (task_type, subject) returns the existing task without
    # charging the budget — proven because two *distinct* types still both succeed
    # under a cap of two despite the duplicate call in between.
    again = pool.generate(_task_type(), "agency:x", facts={}, now=_NOW)
    assert again is first
    other = pool.generate(_task_type(slug="other"), "agency:x", facts={}, now=_NOW)
    assert other is not None
    # The third distinct type is refused: the budget of two is now spent.
    third = pool.generate(_task_type(slug="third"), "agency:x", facts={}, now=_NOW)
    assert third is None
