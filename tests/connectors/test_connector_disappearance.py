# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Source disappearance as data at the connector boundary (SIG-INGEST-009/010)."""

from __future__ import annotations

from datetime import UTC, datetime

from connectors.disappearance import (
    failing_status_for_error,
    failing_status_for_http,
    note_disappearance,
)
from connectors.net import ChallengeEncountered

_WHEN = datetime(2026, 6, 1, tzinfo=UTC)


def test_http_status_classification() -> None:
    assert failing_status_for_http(404) == "link_rotted"
    assert failing_status_for_http(410) == "link_rotted"
    assert failing_status_for_http(451) == "access_restricted"
    assert failing_status_for_http(200) is None
    assert failing_status_for_http(302) is None


def test_challenge_classification() -> None:
    assert failing_status_for_error(ChallengeEncountered("blocked")) == "access_restricted"
    assert failing_status_for_error(ValueError("other")) is None


def test_note_disappearance_produces_event_and_task() -> None:
    # SIG-INGEST-009/010: a disappearance is a first-class event AND a research task.
    disappearance = note_disappearance(
        artifact_id="art-1",
        observed_at=_WHEN,
        failing_status="link_rotted",
        subject_id="entity-9",
    )
    rows = disappearance.rows()
    assert rows["event"]["capture_status"] == "link_rotted"
    assert rows["event"]["disappeared_observed_at"] == _WHEN
    assert rows["research_task"]["task_type"] == "source_disappeared"
    assert rows["research_task"]["subject_id"] == "entity-9"
    assert rows["research_task"]["closing_condition"]
