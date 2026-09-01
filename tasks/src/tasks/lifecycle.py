# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The task lifecycle and the pool that governs it (§33.3, SIG-TASK-005/006/007).

A `ResearchTask` is a live instance of a `TaskType` (:mod:`tasks.spec`) about one
subject. It moves through the §33.3 lifecycle under a validated state machine, and
three disciplines the spec makes MUSTs are enforced by the :class:`TaskPool`:

* **auto-invalidation** — when the detector no longer fires (evidence arrived by
  another route), the task is *silently closed* rather than left stale
  (SIG-TASK-006);
* **duplicate suppression** — at most one task per `(task_type, subject)`, mirroring
  the `research_task` UNIQUE constraint (SIG-TASK-007);
* **claim timeout** — a claim that is not progressed by its deadline returns to the
  pool, so an abandoned claim does not park a task forever (SIG-TASK-007);
* **per-subject rate limiting** — a badly-modelled subject cannot flood the queue
  with generated tasks (SIG-TASK-013).

The fields track `db/deploy/graph_annotations.sql`'s `research_task` row; persisting
them to Postgres and serving them is a downstream ticket (this module owns the
in-memory shape and the transition rules).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .spec import Facts, TaskType
from .vocabulary import (
    OPEN_STATUSES,
    TERMINAL_STATUSES,
    Disposition,
    TaskStatus,
    is_legal_transition,
)

__all__ = [
    "ResearchTask",
    "RateLimiter",
    "TaskPool",
    "IllegalTransitionError",
]


class IllegalTransitionError(ValueError):
    """Raised on a lifecycle transition the §33.3 state machine forbids."""


@dataclass
class ResearchTask:
    """A live research task about one subject (§33.3, the `research_task` row).

    Holds a reference to its declaring :class:`~tasks.spec.TaskType` (`spec`) so it
    can re-evaluate the detector and the closing condition, plus the instance state
    that changes over the lifecycle. `subject_id` is the subject the task is *about*
    and, with the task type, is the duplicate-suppression key (SIG-TASK-007).
    """

    spec: TaskType
    subject_id: str | None
    jurisdiction_id: str | None = None
    priority: float = 0.0
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.GENERATED
    disposition: Disposition | None = None
    claimed_by: str | None = None
    claimed_at: datetime | None = None
    claim_expires_at: datetime | None = None
    generated_at: datetime | None = None

    @property
    def task_type(self) -> str:
        """The declaring type's stable slug (`research_task.task_type`)."""
        return self.spec.task_type

    @property
    def detector_version(self) -> str:
        """The detector revision that produced this task (`detector_version`)."""
        return self.spec.detector.version

    @property
    def is_open(self) -> bool:
        """Whether the task is still workable (not closed/invalidated)."""
        return self.status in OPEN_STATUSES

    @property
    def dedup_key(self) -> tuple[str, str | None]:
        """The `(task_type, subject)` duplicate-suppression key (SIG-TASK-007)."""
        return (self.task_type, self.subject_id)

    def transition_to(self, dst: TaskStatus) -> None:
        """Move to `dst`, or raise if the transition is illegal (SIG-TASK-005)."""
        if not is_legal_transition(self.status, dst):
            raise IllegalTransitionError(
                f"illegal transition {self.status.value} → {dst.value} for task {self.task_id} "
                "(§33.3)"
            )
        self.status = dst

    # --- happy-path helpers ---------------------------------------------------

    def triage(self) -> None:
        """`generated → triaged` (or `reopened → triaged` back into the queue)."""
        self.transition_to(TaskStatus.TRIAGED)

    def claim(self, contributor: str, *, now: datetime, timeout: timedelta) -> None:
        """Claim a triaged task with a timeout (SIG-TASK-007).

        A claim is a soft lease, not exclusivity (§33.5): it records who is working
        and until when, so an abandoned claim can be reclaimed. It grants no right to
        block another contributor from an open task.
        """
        self.transition_to(TaskStatus.CLAIMED)
        self.claimed_by = contributor
        self.claimed_at = now
        self.claim_expires_at = now + timeout

    def start(self) -> None:
        """`claimed → in_progress`."""
        self.transition_to(TaskStatus.IN_PROGRESS)

    def submit(self) -> None:
        """`in_progress → submitted`."""
        self.transition_to(TaskStatus.SUBMITTED)

    def verify(self) -> None:
        """`submitted → verified`."""
        self.transition_to(TaskStatus.VERIFIED)

    def release(self) -> None:
        """Return a claimed/in-progress task to the queue (`→ triaged`).

        Clears the claim so the task is workable by anyone again (SIG-TASK-011).
        """
        self.transition_to(TaskStatus.TRIAGED)
        self._clear_claim()

    def reopen(self) -> None:
        """Reopen a submitted/verified/closed task (`→ reopened`)."""
        self.transition_to(TaskStatus.REOPENED)
        self.disposition = None

    def close(self, disposition: Disposition) -> None:
        """Close a verified task with a disposition (§33.4).

        The disposition MUST be one the task type permits (`dispositions[]`).
        `resolved_no_evidence_exists` is refused here on purpose: it MUST write a
        `CoverageRecord` (SIG-TASK-009), so it is only reachable through
        :func:`tasks.dispositions.resolve_no_evidence_exists`, which cannot close the
        task without producing that record.
        """
        if disposition is Disposition.RESOLVED_NO_EVIDENCE_EXISTS:
            raise ValueError(
                "resolved_no_evidence_exists MUST write a CoverageRecord (SIG-TASK-009); "
                "close it through tasks.dispositions.resolve_no_evidence_exists, not close()"
            )
        self._close_with(disposition)

    def _close_with(self, disposition: Disposition) -> None:
        if disposition not in self.spec.dispositions:
            raise ValueError(
                f"disposition {disposition.value!r} is not permitted for task type "
                f"{self.task_type!r} (§33.1 dispositions[])"
            )
        self.transition_to(TaskStatus.CLOSED)
        self.disposition = disposition

    def invalidate(self) -> None:
        """Silently retire a task whose detector no longer fires (SIG-TASK-006)."""
        self.transition_to(TaskStatus.INVALIDATED)
        self._clear_claim()

    # --- the two re-evaluation checks the pool drives -------------------------

    def claim_is_expired(self, now: datetime) -> bool:
        """Whether a claim has passed its deadline (SIG-TASK-007)."""
        return (
            self.status is TaskStatus.CLAIMED
            and self.claim_expires_at is not None
            and now >= self.claim_expires_at
        )

    def detector_still_fires(self, facts: Facts) -> bool:
        """Whether the generating detector still fires for the subject."""
        return self.spec.detector_fires(facts)

    def is_closable_by(self, facts: Facts) -> bool:
        """Whether the closing condition is met by these facts (SIG-TASK-002)."""
        return self.spec.is_closed_by(facts)

    def _clear_claim(self) -> None:
        self.claimed_by = None
        self.claimed_at = None
        self.claim_expires_at = None


class RateLimiter:
    """A per-subject sliding-window generation limit (SIG-TASK-013).

    Task generation MUST be rate-limited per subject so one badly-modelled entity
    cannot flood the queue. This records generation events per subject and refuses
    once `max_per_window` have occurred within `window`.
    """

    def __init__(self, *, max_per_window: int, window: timedelta) -> None:
        if max_per_window < 1:
            raise ValueError("max_per_window MUST be at least 1")
        if window <= timedelta(0):
            raise ValueError("window MUST be positive")
        self._max = max_per_window
        self._window = window
        self._events: dict[str, list[datetime]] = {}

    def allow(self, subject_id: str, now: datetime) -> bool:
        """Whether a generation for `subject_id` is allowed at `now`.

        Prunes events older than the window, then admits (and records) the event iff
        the subject is under its cap. A denied event is *not* recorded, so the limit
        is a true rate, not a permanent ban.
        """
        recent = [t for t in self._events.get(subject_id, ()) if now - t < self._window]
        if len(recent) >= self._max:
            self._events[subject_id] = recent
            return False
        recent.append(now)
        self._events[subject_id] = recent
        return True


class TaskPool:
    """The set of live tasks, enforcing the §33.3/§33.6 pool disciplines.

    Owns duplicate suppression (SIG-TASK-007), claim reclamation (SIG-TASK-007), and
    per-subject rate limiting (SIG-TASK-013). Auto-invalidation (SIG-TASK-006) is
    driven through :meth:`sweep_invalidations` from the current graph facts.
    """

    def __init__(self, *, rate_limiter: RateLimiter | None = None) -> None:
        self._tasks: dict[str, ResearchTask] = {}
        self._by_key: dict[tuple[str, str | None], str] = {}
        self._rate_limiter = rate_limiter

    def generate(
        self,
        spec: TaskType,
        subject_id: str | None,
        *,
        facts: Facts,
        now: datetime,
        jurisdiction_id: str | None = None,
    ) -> ResearchTask | None:
        """Generate a task for `(spec, subject_id)`, honoring dedup + rate limit.

        Returns the existing task if one already exists for the key (duplicate
        suppression, SIG-TASK-007) — no new task, no rate-limit charge. Returns
        `None` if generation is refused by the per-subject rate limiter
        (SIG-TASK-013). Otherwise mints a task at `generated`, priced by the type's
        `priority_fn`, and records it.
        """
        key = (spec.task_type, subject_id)
        existing_id = self._by_key.get(key)
        if existing_id is not None:
            return self._tasks[existing_id]
        if (
            self._rate_limiter is not None
            and subject_id is not None
            and not self._rate_limiter.allow(subject_id, now)
        ):
            return None
        task = ResearchTask(
            spec=spec,
            subject_id=subject_id,
            jurisdiction_id=jurisdiction_id,
            priority=spec.priority(facts),
            status=TaskStatus.GENERATED,
            generated_at=now,
        )
        self._tasks[task.task_id] = task
        self._by_key[key] = task.task_id
        return task

    def reclaim_expired(self, now: datetime) -> list[ResearchTask]:
        """Return every task whose claim has expired to the pool (SIG-TASK-007).

        An abandoned claim (claimed, past its deadline, never progressed) is released
        back to `triaged` so anyone can pick it up. Returns the reclaimed tasks.
        """
        reclaimed = [t for t in self._tasks.values() if t.claim_is_expired(now)]
        for task in reclaimed:
            task.release()
        return reclaimed

    def sweep_invalidations(self, facts_by_subject: dict[str | None, Facts]) -> list[ResearchTask]:
        """Auto-invalidate open tasks whose detector no longer fires (SIG-TASK-006).

        For each open task, look up its subject's current facts; if the detector no
        longer fires, the evidence has arrived by another route, so the task is
        silently invalidated rather than left in the queue. A subject absent from
        `facts_by_subject` is treated as unchanged (not swept). Returns the tasks
        invalidated.
        """
        invalidated: list[ResearchTask] = []
        for task in self._tasks.values():
            if not task.is_open or task.subject_id not in facts_by_subject:
                continue
            if not task.detector_still_fires(facts_by_subject[task.subject_id]):
                task.invalidate()
                invalidated.append(task)
        return invalidated

    def get(self, task_id: str) -> ResearchTask:
        """The task with `task_id`, or raise `KeyError`."""
        return self._tasks[task_id]

    def open_tasks(self) -> list[ResearchTask]:
        """Every task still workable (not closed/invalidated)."""
        return [t for t in self._tasks.values() if t.is_open]

    def tasks_for_subject(self, subject_id: str | None) -> list[ResearchTask]:
        """Every task about `subject_id`."""
        return [t for t in self._tasks.values() if t.subject_id == subject_id]

    def __iter__(self) -> Iterator[ResearchTask]:
        return iter(self._tasks.values())

    def __len__(self) -> int:
        return len(self._tasks)


def terminal_statuses() -> Iterable[TaskStatus]:
    """The lifecycle's terminal states (re-exported for callers)."""
    return TERMINAL_STATUSES
