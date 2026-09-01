# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The detector specification language: tasks as data (§33.1, SIG-TASK-001/002).

Every task type is declared as **data**, not code: a `TaskType` record carrying a
versioned `detector`, a `priority_fn`, a **testable** `closing_condition`, the
`assignee_class` it routes to, an `effort_estimate`, the `dispositions[]` it may
reach, and its `geographic_scope`. This module owns that shape and the registry
that enforces the one load-bearing discipline of §33: a task type whose
`closing_condition` is not testable **cannot be registered** (SIG-TASK-002).
"Research this" is not a task; "obtain a document establishing X, or record that
the agency states no such document exists" is.

The concrete task *catalog* — the 34 detectors of §33.2 — is registered against
this DSL by P10.2. This ticket owns only the language and its registration rules.

A `detector` and a `closing_condition` are both modelled as callables over a
subject's current graph facts (`Facts`): a predicate returning whether the
detector still fires / whether the closing condition is met. Making them callable
rather than free text is exactly what makes SIG-TASK-002 and SIG-TASK-006
testable — the engine can *evaluate* them, not just store them.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from enum import StrEnum

from .vocabulary import AssigneeClass, Disposition, EffortEstimate

__all__ = [
    "Facts",
    "GeographicScope",
    "Detector",
    "TaskType",
    "TaskTypeRegistry",
    "UntestableClosingConditionError",
]

#: The current graph facts about a subject a detector / closing condition reads.
Facts = Mapping[str, object]


class GeographicScope(StrEnum):
    """How a task type is placed for queue assignment (§33.1/§33.5).

    `JURISDICTION`-scoped tasks route to a jurisdiction's geographic queue (where a
    local group may claim priority, §33.5); `GLOBAL` tasks belong to no single
    jurisdiction and are worked from the global pool.
    """

    JURISDICTION = "jurisdiction"
    GLOBAL = "global"


class UntestableClosingConditionError(ValueError):
    """Raised when a task type without a testable `closing_condition` is registered.

    SIG-TASK-002: "Research this" is not a task. A type with no evaluable closing
    condition cannot tell the engine when it is done, so it can never leave the
    queue on any disposition but success — it MUST NOT be registered.
    """


@dataclass(frozen=True)
class Detector:
    """A versioned query over the graph (§33.1, the `detector` field).

    `version` is stamped onto every task the detector generates
    (`research_task.detector_version`), so a task carries the exact detector
    revision that produced it. `query` returns whether the detector *fires* for a
    subject's current facts — the signal the lifecycle re-evaluates to
    auto-invalidate (SIG-TASK-006).
    """

    version: str
    query: Callable[[Facts], bool]

    def __post_init__(self) -> None:
        if not self.version:
            raise ValueError("a Detector MUST carry a version (research_task.detector_version)")
        if not callable(self.query):
            raise TypeError("a Detector's query MUST be callable (a query over the graph)")

    def fires(self, facts: Facts) -> bool:
        """Whether the detector fires for these subject facts."""
        return bool(self.query(facts))


@dataclass(frozen=True)
class TaskType:
    """A research-task type declared as data (§33.1, SIG-TASK-001).

    Carries all eight required fields. `closing_condition` is `Callable | None`:
    `None` models a type that names no testable condition ("research this"), which
    is constructible but which :meth:`TaskTypeRegistry.register` refuses
    (SIG-TASK-002). `dispositions` MUST be non-empty (a task with no permitted
    outcome can never leave the queue) and drawn from the §33.4 vocabulary.
    """

    task_type: str
    detector: Detector
    priority_fn: Callable[[Facts], float]
    closing_condition: Callable[[Facts], bool] | None
    assignee_class: AssigneeClass
    effort_estimate: EffortEstimate
    dispositions: tuple[Disposition, ...]
    geographic_scope: GeographicScope

    def __post_init__(self) -> None:
        if not self.task_type:
            raise ValueError("a TaskType MUST carry a stable task_type slug (§33.1)")
        if not callable(self.priority_fn):
            raise TypeError("priority_fn MUST be callable (§33.1)")
        if not self.dispositions:
            raise ValueError(
                f"task type {self.task_type!r} declares no dispositions; a task with no "
                "permitted outcome can never leave the queue (§33.4)"
            )
        for disposition in self.dispositions:
            if not isinstance(disposition, Disposition):
                raise TypeError(
                    f"task type {self.task_type!r} declares a non-vocabulary disposition "
                    f"{disposition!r}; use the §33.4 Disposition vocabulary"
                )

    @property
    def has_testable_closing_condition(self) -> bool:
        """Whether this type names an evaluable closing condition (SIG-TASK-002)."""
        return callable(self.closing_condition)

    def detector_fires(self, facts: Facts) -> bool:
        """Whether the detector still fires for these subject facts (SIG-TASK-006)."""
        return self.detector.fires(facts)

    def is_closed_by(self, facts: Facts) -> bool:
        """Whether the closing condition is met by these facts (SIG-TASK-002).

        Raises if this type has no testable closing condition — such a type should
        never have been registered, so evaluating it is a programming error.
        """
        if self.closing_condition is None:
            raise UntestableClosingConditionError(
                f"task type {self.task_type!r} has no testable closing_condition (SIG-TASK-002)"
            )
        return bool(self.closing_condition(facts))

    def priority(self, facts: Facts) -> float:
        """Compute this task's urgency for a subject's facts (the `priority_fn`)."""
        return float(self.priority_fn(facts))


class TaskTypeRegistry:
    """The registry of declared task types — the gate SIG-TASK-002 enforces.

    Registration is the single choke point where the "testable closing condition"
    discipline is applied: a type with no evaluable `closing_condition` is refused
    with :class:`UntestableClosingConditionError`, and a duplicate slug is refused
    so a later registration cannot silently shadow an earlier one.
    """

    def __init__(self) -> None:
        self._types: dict[str, TaskType] = {}

    def register(self, task_type: TaskType) -> TaskType:
        """Register a task type, or refuse it (SIG-TASK-001/002).

        Returns the registered type (so registration can be inlined). Refuses a
        type with no testable closing condition (SIG-TASK-002) and a duplicate
        slug.
        """
        if not task_type.has_testable_closing_condition:
            raise UntestableClosingConditionError(
                f"task type {task_type.task_type!r} has no testable closing_condition and "
                "MUST NOT be registered (SIG-TASK-002): 'research this' is not a task"
            )
        if task_type.task_type in self._types:
            raise ValueError(
                f"task type {task_type.task_type!r} is already registered; a change is a new "
                "detector version, not a silent re-registration"
            )
        self._types[task_type.task_type] = task_type
        return task_type

    def get(self, slug: str) -> TaskType:
        """The registered task type for `slug`, or raise `KeyError`."""
        return self._types[slug]

    def __contains__(self, slug: object) -> bool:
        return slug in self._types

    def __iter__(self) -> Iterator[TaskType]:
        return iter(self._types.values())

    def __len__(self) -> int:
        return len(self._types)

    def slugs(self) -> frozenset[str]:
        """The set of registered task-type slugs."""
        return frozenset(self._types)
