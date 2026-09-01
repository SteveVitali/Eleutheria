# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The detector specification language: tasks as data, testably (§33.1).

AC1 (SIG-TASK-002): a task type with no testable `closing_condition` cannot register.
SIG-TASK-001: a task type carries all eight declared-as-data fields.
"""

from __future__ import annotations

import pytest
from tasks.spec import (
    Detector,
    Facts,
    GeographicScope,
    TaskType,
    TaskTypeRegistry,
    UntestableClosingConditionError,
)
from tasks.vocabulary import AssigneeClass, Disposition, EffortEstimate


def _detector(version: str = "v1") -> Detector:
    return Detector(version=version, query=lambda facts: bool(facts.get("fires", False)))


def _task_type(
    *,
    slug: str = "missing_contract",
    closing_condition=lambda facts: bool(facts.get("closed", False)),
) -> TaskType:
    return TaskType(
        task_type=slug,
        detector=_detector(),
        priority_fn=lambda facts: float(facts.get("priority", 1.0)),
        closing_condition=closing_condition,
        assignee_class=AssigneeClass.RECORDS_REQUESTER,
        effort_estimate=EffortEstimate.MODERATE,
        dispositions=(Disposition.RESOLVED_EVIDENCE_FOUND, Disposition.BLOCKED_FEE),
        geographic_scope=GeographicScope.JURISDICTION,
    )


def test_task_type_declares_all_eight_fields() -> None:
    """SIG-TASK-001: every §33.1 field is present and typed."""
    tt = _task_type()
    assert tt.task_type == "missing_contract"
    assert tt.detector.version == "v1"
    assert callable(tt.priority_fn)
    assert callable(tt.closing_condition)
    assert tt.assignee_class is AssigneeClass.RECORDS_REQUESTER
    assert tt.effort_estimate is EffortEstimate.MODERATE
    assert tt.dispositions == (Disposition.RESOLVED_EVIDENCE_FOUND, Disposition.BLOCKED_FEE)
    assert tt.geographic_scope is GeographicScope.JURISDICTION


def test_untestable_closing_condition_cannot_register() -> None:
    """AC1 / SIG-TASK-002: 'research this' (no testable condition) is refused."""
    registry = TaskTypeRegistry()
    research_this = _task_type(slug="research_this", closing_condition=None)
    assert not research_this.has_testable_closing_condition
    with pytest.raises(UntestableClosingConditionError, match="SIG-TASK-002"):
        registry.register(research_this)
    assert "research_this" not in registry
    assert len(registry) == 0


def test_a_testable_closing_condition_registers_and_is_evaluable() -> None:
    registry = TaskTypeRegistry()
    tt = registry.register(_task_type())
    assert "missing_contract" in registry
    assert registry.get("missing_contract") is tt
    # The closing condition is genuinely evaluable, not decorative.
    assert tt.is_closed_by({"closed": True}) is True
    assert tt.is_closed_by({"closed": False}) is False


def test_evaluating_an_untestable_condition_is_a_programming_error() -> None:
    tt = _task_type(closing_condition=None)
    with pytest.raises(UntestableClosingConditionError):
        tt.is_closed_by({})


def test_duplicate_slug_is_refused() -> None:
    registry = TaskTypeRegistry()
    registry.register(_task_type())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(_task_type())


def test_a_task_type_with_no_dispositions_is_rejected() -> None:
    with pytest.raises(ValueError, match="no dispositions"):
        _task_type_no_dispositions()


def _task_type_no_dispositions() -> TaskType:
    return TaskType(
        task_type="x",
        detector=_detector(),
        priority_fn=lambda facts: 1.0,
        closing_condition=lambda facts: True,
        assignee_class=AssigneeClass.ANALYST,
        effort_estimate=EffortEstimate.QUICK,
        dispositions=(),
        geographic_scope=GeographicScope.GLOBAL,
    )


def test_detector_requires_a_version() -> None:
    with pytest.raises(ValueError, match="version"):
        Detector(version="", query=lambda facts: True)


def test_detector_and_priority_are_evaluable() -> None:
    tt = _task_type()
    facts: Facts = {"fires": True, "priority": 7.5}
    assert tt.detector_fires(facts) is True
    assert tt.detector_fires({"fires": False}) is False
    assert tt.priority(facts) == 7.5
