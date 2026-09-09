# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The controlled vocabularies of the research-task engine (§33).

The task engine is "tasks as data" (§33.1). That only works if the *values* those
data carry — who a task is for, what outcomes it may reach, what state it is in —
are a fixed, testable vocabulary rather than free text. This module owns those
enums and the one piece of logic that is pure vocabulary: the legal lifecycle
transitions (§33.3). Everything else (the DSL, the pool, the queues) builds on
these.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "AssigneeClass",
    "Disposition",
    "EffortEstimate",
    "TaskStatus",
    "TERMINAL_STATUSES",
    "OPEN_STATUSES",
    "is_legal_transition",
    "legal_transitions_from",
]


class AssigneeClass(StrEnum):
    """Who a task type is routed to (§33.1, the `assignee_class` field).

    The exact seven classes the spec table enumerates — no more, no fewer.
    """

    FIELD_MAPPER = "field_mapper"
    RECORDS_REQUESTER = "records_requester"
    DOCUMENT_REVIEWER = "document_reviewer"
    ANALYST = "analyst"
    LOCAL_GROUP = "local_group"
    CURATOR = "curator"
    DEVELOPER = "developer"


class Disposition(StrEnum):
    """The disposition vocabulary richer than "done" (§33.4, SIG-TASK-008).

    The queue must be able to *shrink*: without a way to record "searched, found
    nothing" or "blocked by a fee", a task can only ever be closed by success, so
    the backlog only grows — which is how contributor systems die (§33.4).
    """

    RESOLVED_EVIDENCE_FOUND = "resolved_evidence_found"
    #: Searched; the record does not exist. Writes a CoverageRecord (SIG-TASK-009).
    RESOLVED_NO_EVIDENCE_EXISTS = "resolved_no_evidence_exists"
    BLOCKED_ACCESS_DENIED = "blocked_access_denied"
    BLOCKED_FEE = "blocked_fee"
    BLOCKED_AWAITING_RESPONSE = "blocked_awaiting_response"
    NOT_ACTIONABLE = "not_actionable"
    SUPERSEDED = "superseded"
    DEFERRED = "deferred"


class EffortEstimate(StrEnum):
    """A coarse effort band (§33.1, the `effort_estimate` field).

    The spec leaves the units open; a small ordered band keeps the field typed and
    testable without pretending to a precision (minutes) the detector cannot know.
    """

    QUICK = "quick"
    MODERATE = "moderate"
    SUBSTANTIAL = "substantial"


class TaskStatus(StrEnum):
    """The lifecycle states of a task (§33.3, SIG-TASK-005).

    The happy path is the linear `generated → triaged → claimed → in_progress →
    submitted → verified → closed`; `reopened` and `invalidated` are the two
    off-path transitions the spec names.
    """

    GENERATED = "generated"
    TRIAGED = "triaged"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    CLOSED = "closed"
    REOPENED = "reopened"
    INVALIDATED = "invalidated"


#: States from which no further work happens (the task has left the queue).
TERMINAL_STATUSES: frozenset[TaskStatus] = frozenset({TaskStatus.CLOSED, TaskStatus.INVALIDATED})

#: The linear happy path, in order — the spine of the transition table.
_HAPPY_PATH: tuple[TaskStatus, ...] = (
    TaskStatus.GENERATED,
    TaskStatus.TRIAGED,
    TaskStatus.CLAIMED,
    TaskStatus.IN_PROGRESS,
    TaskStatus.SUBMITTED,
    TaskStatus.VERIFIED,
    TaskStatus.CLOSED,
)

# The legal transitions (§33.3). The happy-path spine (`_HAPPY_PATH`), plus:
#  * invalidated: reachable from any non-terminal state (auto-invalidation,
#    SIG-TASK-006, can fire whenever the detector stops firing);
#  * closed: reachable from any worked state (triaged onward), because the §33.4
#    disposition vocabulary concludes tasks in many ways — `not_actionable`,
#    `superseded`, and `deferred` legitimately close a task *before* full
#    verification, so closure is not tied to the happy path alone;
#  * → triaged: an abandoned claim / in-progress task returns to the pool
#    (SIG-TASK-007, SIG-TASK-011);
#  * reopened: a submitted/verified/closed/invalidated task can be reopened — an
#    invalidated task whose evidence later changes re-enters the queue rather than
#    dead-ending under the `(task_type, subject)` uniqueness (SIG-TASK-007);
#  * reopened → triaged: a reopened task re-enters the workable queue.
_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.GENERATED: frozenset({TaskStatus.TRIAGED, TaskStatus.INVALIDATED}),
    TaskStatus.TRIAGED: frozenset({TaskStatus.CLAIMED, TaskStatus.CLOSED, TaskStatus.INVALIDATED}),
    TaskStatus.CLAIMED: frozenset(
        {TaskStatus.IN_PROGRESS, TaskStatus.TRIAGED, TaskStatus.CLOSED, TaskStatus.INVALIDATED}
    ),
    TaskStatus.IN_PROGRESS: frozenset(
        {TaskStatus.SUBMITTED, TaskStatus.TRIAGED, TaskStatus.CLOSED, TaskStatus.INVALIDATED}
    ),
    TaskStatus.SUBMITTED: frozenset(
        {TaskStatus.VERIFIED, TaskStatus.REOPENED, TaskStatus.CLOSED, TaskStatus.INVALIDATED}
    ),
    TaskStatus.VERIFIED: frozenset(
        {TaskStatus.CLOSED, TaskStatus.REOPENED, TaskStatus.INVALIDATED}
    ),
    TaskStatus.CLOSED: frozenset({TaskStatus.REOPENED}),
    TaskStatus.REOPENED: frozenset({TaskStatus.TRIAGED, TaskStatus.INVALIDATED}),
    TaskStatus.INVALIDATED: frozenset({TaskStatus.REOPENED}),
}

#: States a task can still be worked from (not terminal). Derived, not hand-listed.
OPEN_STATUSES: frozenset[TaskStatus] = frozenset(
    s for s in TaskStatus if s not in TERMINAL_STATUSES
)


def legal_transitions_from(status: TaskStatus) -> frozenset[TaskStatus]:
    """The states reachable in one step from `status` (§33.3)."""
    return _TRANSITIONS[status]


def is_legal_transition(src: TaskStatus, dst: TaskStatus) -> bool:
    """Whether `src → dst` is a permitted lifecycle transition (SIG-TASK-005)."""
    return dst in _TRANSITIONS[src]
