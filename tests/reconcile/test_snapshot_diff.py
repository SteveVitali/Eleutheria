# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Snapshot-diff reconciliation (§29.7, SIG-RECON-045)."""

from __future__ import annotations

from datetime import date

import pytest
from reconcile.snapshot_diff import (
    ADDED,
    MODIFIED,
    REMOVED,
    Capture,
    diff_captures,
    diff_series,
)

D1 = date(2026, 1, 1)
D2 = date(2026, 2, 1)
D3 = date(2026, 3, 1)


def _cap(digest: str, when: date, **fields: object) -> Capture:
    return Capture(
        artifact_id="art:1", capture_digest=digest, captured_at=when, fields=dict(fields)
    )


def test_modified_field_carries_both_values_and_both_dates() -> None:
    # SIG-RECON-045: per-field change events with both values and both dates.
    prev = _cap("d1", D1, retention_days=30, active_count=38)
    cur = _cap("d2", D2, retention_days=90, active_count=38)
    events = diff_captures(prev, cur)
    assert len(events) == 1
    e = events[0]
    assert e.field == "retention_days"
    assert e.change_type == MODIFIED
    assert e.old_value == 30 and e.new_value == 90
    assert e.old_date == D1 and e.new_date == D2
    assert e.old_capture_digest == "d1" and e.new_capture_digest == "d2"


def test_added_and_removed_fields() -> None:
    prev = _cap("d1", D1, a=1)
    cur = _cap("d2", D2, b=2)
    events = {e.field: e for e in diff_captures(prev, cur)}
    assert events["a"].change_type == REMOVED
    assert events["a"].old_value == 1 and events["a"].new_value is None
    assert events["b"].change_type == ADDED
    assert events["b"].old_value is None and events["b"].new_value == 2


def test_present_but_none_is_distinct_from_absent() -> None:
    # A field present and set to None is not the same as an absent field.
    prev = _cap("d1", D1, x=None)
    cur = _cap("d2", D2, x=5)
    events = diff_captures(prev, cur)
    assert len(events) == 1 and events[0].change_type == MODIFIED
    assert events[0].old_value is None and events[0].new_value == 5


def test_unchanged_fields_produce_no_event() -> None:
    prev = _cap("d1", D1, a=1, b=2)
    cur = _cap("d2", D2, a=1, b=2)
    assert diff_captures(prev, cur) == ()


def test_events_are_sorted_by_field_for_a_deterministic_feed() -> None:
    prev = _cap("d1", D1, z=1, a=1)
    cur = _cap("d2", D2, z=2, a=2)
    fields = [e.field for e in diff_captures(prev, cur)]
    assert fields == sorted(fields) == ["a", "z"]


def test_series_diffs_consecutively_in_chronological_order() -> None:
    caps = [
        _cap("d3", D3, v=3),
        _cap("d1", D1, v=1),
        _cap("d2", D2, v=2),
    ]
    events = diff_series(caps)
    # ordered by date: 1->2 then 2->3
    assert [(e.old_value, e.new_value) for e in events] == [(1, 2), (2, 3)]


def test_diffing_different_artifacts_is_rejected() -> None:
    a = Capture(artifact_id="art:1", capture_digest="d1", captured_at=D1, fields={})
    b = Capture(artifact_id="art:2", capture_digest="d2", captured_at=D2, fields={})
    with pytest.raises(ValueError, match="different artifacts"):
        diff_captures(a, b)
