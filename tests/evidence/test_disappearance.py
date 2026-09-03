# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Disappearance events + research-task generation (SIG-EVID-013/014/015)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from evidence.disappearance import (
    DISAPPEARANCE_TASK_TYPE,
    disappearance_task,
    record_disappearance,
    sweep_cadence_days,
    wayback_save_url,
)

_WHEN = datetime(2026, 6, 1, tzinfo=UTC)


def test_disappearance_is_an_event_not_a_delete() -> None:
    """SIG-EVID-013: record disappeared_observed_at + failing status; delete nothing."""
    event = record_disappearance("art-1", _WHEN, "link_rotted")
    update = event.artifact_update()
    assert update["disappeared_observed_at"] == _WHEN
    assert update["capture_status"] == "link_rotted"
    # The API only ever produces an UPDATE payload — there is no delete path.
    assert set(update) == {"disappeared_observed_at", "capture_status"}


def test_non_failing_status_is_rejected() -> None:
    with pytest.raises(ValueError):
        record_disappearance("art-1", _WHEN, "captured")


def test_disappearance_generates_a_research_task() -> None:
    """SIG-EVID-014: disappearance generates a §33.2 research task."""
    event = record_disappearance("art-1", _WHEN, "link_rotted")
    task = disappearance_task(event, subject_id="entity-9")
    assert task["task_type"] == DISAPPEARANCE_TASK_TYPE
    assert task["subject_id"] == "entity-9"
    assert task["closing_condition"]  # SIG-TASK-002: testable closing condition
    assert task["detector_version"]


def test_sweep_cadence_is_proportional_to_volatility() -> None:
    """SIG-EVID-015: volatile sources re-checked more often than stable ones."""
    assert sweep_cadence_days("VOLATILE") < sweep_cadence_days("MODERATE")
    assert sweep_cadence_days("MODERATE") < sweep_cadence_days("GLACIAL")


def test_wayback_save_url() -> None:
    assert (
        wayback_save_url("https://x.example/a")
        == "https://web.archive.org/save/https://x.example/a"
    )
