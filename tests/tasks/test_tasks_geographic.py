# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Geographic queues: coordination without gatekeeping (§33.5).

AC3 (SIG-TASK-010/011): geographic claims expire without renewal and never grant
exclusivity — any contributor can still work any open task.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from tasks.geographic import GeographicClaim, GeographicQueue, any_contributor_may_work
from tasks.lifecycle import ResearchTask, TaskPool
from tasks.spec import Detector, GeographicScope, TaskType
from tasks.vocabulary import AssigneeClass, Disposition, EffortEstimate

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _task_type(slug: str = "coverage_hole") -> TaskType:
    return TaskType(
        task_type=slug,
        detector=Detector(version="v1", query=lambda facts: True),
        priority_fn=lambda facts: float(facts.get("priority", 1.0)),
        closing_condition=lambda facts: bool(facts.get("closed", False)),
        assignee_class=AssigneeClass.LOCAL_GROUP,
        effort_estimate=EffortEstimate.MODERATE,
        dispositions=(Disposition.RESOLVED_EVIDENCE_FOUND,),
        geographic_scope=GeographicScope.JURISDICTION,
    )


def _task(subject: str, jurisdiction: str, priority: float = 1.0) -> ResearchTask:
    pool = TaskPool()
    task = pool.generate(
        _task_type(slug=f"t_{subject}"),
        subject,
        facts={"priority": priority},
        now=_NOW,
        jurisdiction_id=jurisdiction,
    )
    assert task is not None
    return task


def test_claim_grants_priority_and_visibility() -> None:
    """SIG-TASK-010: a claim grants visibility, notification, and priority."""
    queue = GeographicQueue()
    queue.claim(jurisdiction_id="jur:ok", group_id="deflock:okc", now=_NOW, ttl=timedelta(days=90))
    assert queue.has_priority(group_id="deflock:okc", jurisdiction_id="jur:ok", now=_NOW)
    assert queue.visible_jurisdictions("deflock:okc", _NOW) == frozenset({"jur:ok"})
    assert queue.claimant_groups("jur:ok", _NOW) == frozenset({"deflock:okc"})


def test_claims_expire_without_renewal() -> None:
    """AC3 / SIG-TASK-011: a claim past its deadline confers nothing."""
    queue = GeographicQueue()
    queue.claim(jurisdiction_id="jur:ok", group_id="g", now=_NOW, ttl=timedelta(days=30))
    later = _NOW + timedelta(days=31)
    assert queue.active_claims(later) == []
    assert not queue.has_priority(group_id="g", jurisdiction_id="jur:ok", now=later)
    assert queue.visible_jurisdictions("g", later) == frozenset()


def test_a_claim_never_grants_exclusivity() -> None:
    """AC3 / SIG-TASK-011: any contributor may work any open task, claim or not."""
    queue = GeographicQueue()
    queue.claim(jurisdiction_id="jur:ok", group_id="deflock:okc", now=_NOW, ttl=timedelta(days=90))
    task = _task("agency:okcpd", "jur:ok")
    # The workability check takes no contributor and no claim — a non-claiming
    # contributor is not blocked, because exclusivity does not exist.
    assert any_contributor_may_work(task) is True


def test_claim_priority_orders_but_does_not_filter() -> None:
    """SIG-TASK-010/011: claimed jurisdiction sorts first, but nothing is excluded."""
    queue = GeographicQueue()
    queue.claim(jurisdiction_id="jur:ok", group_id="g", now=_NOW, ttl=timedelta(days=90))
    ok_low = _task("agency:ok", "jur:ok", priority=1.0)
    tx_high = _task("agency:tx", "jur:tx", priority=9.0)
    ordered = queue.order_for_group([tx_high, ok_low], group_id="g", now=_NOW)
    # The claimed-jurisdiction task sorts ahead despite its lower own-priority...
    assert ordered[0] is ok_low
    # ...but the unclaimed task is still present and workable (not filtered out).
    assert tx_high in ordered
    assert all(any_contributor_may_work(t) for t in ordered)


def test_expired_claim_stops_boosting_order() -> None:
    queue = GeographicQueue()
    queue.claim(jurisdiction_id="jur:ok", group_id="g", now=_NOW, ttl=timedelta(days=10))
    ok_low = _task("agency:ok", "jur:ok", priority=1.0)
    tx_high = _task("agency:tx", "jur:tx", priority=9.0)
    later = _NOW + timedelta(days=11)
    ordered = queue.order_for_group([tx_high, ok_low], group_id="g", now=later)
    # With the claim lapsed, ordering falls back to own priority.
    assert ordered[0] is tx_high


def test_closed_task_is_not_workable() -> None:
    task = _task("agency:okcpd", "jur:ok")
    task.triage()
    task.claim("a", now=_NOW, timeout=timedelta(days=1))
    task.start()
    task.submit()
    task.verify()
    task.close(Disposition.RESOLVED_EVIDENCE_FOUND)
    assert any_contributor_may_work(task) is False  # left the queue, not owned


def test_a_claim_must_expire_after_it_is_made() -> None:
    with pytest.raises(ValueError, match="expire"):
        GeographicClaim(jurisdiction_id="j", group_id="g", claimed_at=_NOW, expires_at=_NOW)


def test_multiple_groups_may_claim_the_same_jurisdiction() -> None:
    """Non-exclusivity: a second claimant does not displace the first."""
    queue = GeographicQueue()
    queue.claim(jurisdiction_id="jur:ok", group_id="g1", now=_NOW, ttl=timedelta(days=90))
    queue.claim(jurisdiction_id="jur:ok", group_id="g2", now=_NOW, ttl=timedelta(days=90))
    assert queue.claimant_groups("jur:ok", _NOW) == frozenset({"g1", "g2"})
