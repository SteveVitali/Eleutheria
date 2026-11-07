# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The flock_portal change feed (P37.5b; SIG-INGEST-035, §17.6).

The driver wires the connector's change-detection halves into one deterministic
feed: appearance/disappearance event rows + research tasks over the two
committed snapshots (``tulsa-pd`` disappears and ``newcity-pd`` appears between
2026-08 and 2026-09), the per-field diff on shared portals (SIG-RECON-045), and
the poll-due decision keyed on the upstream's own snapshot date — never
wall-clock in a claim value (SIG-INGEST-018).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from connectors.portal_changes import (
    SCHEMA,
    canonical_json,
    load_snapshot,
    portal_change_feed,
)

FIXTURES = Path(__file__).parent / "fixtures" / "flock_portal"
NOW = date(2026, 9, 20)


def _feed():
    return portal_change_feed(
        load_snapshot(FIXTURES / "snapshot_2026_08.json"),
        load_snapshot(FIXTURES / "snapshot_2026_09.json"),
        previous_capture_digest="dig08",
        current_capture_digest="dig09",
        now=NOW,
        last_observed_snapshot=date(2026, 8, 15),
    )


def test_disappearance_produces_event_and_task() -> None:
    feed = _feed()
    assert feed.disappeared == ("tulsa-pd",)
    assert feed.appeared == ("newcity-pd",)
    gone = [
        r
        for r in feed.claim_rows()
        if r.get("subject_id") == "flock_portal:tulsa-pd" and r["value"] is False
    ]
    assert len(gone) == 1
    assert gone[0]["observed_at"] == date(2026, 9, 15)
    tasks = feed.task_rows()
    dis = [t for t in tasks if t["task_type"] == "source_disappeared"]
    assert len(dis) == 1 and dis[0]["subject_id"] == "flock_portal:tulsa-pd"
    app = [t for t in tasks if t["task_type"] == "flock_portal_appeared"]
    assert len(app) == 1 and app[0]["subject_id"] == "flock_portal:newcity-pd"


def test_field_events_carry_both_values_and_dates() -> None:
    feed = _feed()
    assert feed.field_events  # the shared portals changed between snapshots
    for e in feed.field_events:
        assert e.change_type in ("added", "removed", "modified")
        assert e.old_date <= e.new_date
    okc = [e for e in feed.field_events if e.artifact_id == "flock_portal:okc-pd"]
    assert okc  # at least one field moved on a shared portal


def test_poll_due_uses_upstream_dates_not_the_clock() -> None:
    feed = _feed()
    assert feed.poll_due  # the snapshot advanced past the last observed
    not_due = portal_change_feed(
        load_snapshot(FIXTURES / "snapshot_2026_08.json"),
        load_snapshot(FIXTURES / "snapshot_2026_08.json"),
        now=date(2026, 8, 15),
        last_observed_snapshot=date(2026, 8, 15),
    )
    assert not not_due.poll_due  # same snapshot, same day — nothing due


def test_first_observation_marks_everything_appeared() -> None:
    feed = portal_change_feed(None, load_snapshot(FIXTURES / "snapshot_2026_09.json"), now=NOW)
    assert set(feed.appeared) == {"okc-pd", "smallville-pd", "newcity-pd"}
    assert feed.disappeared == ()
    assert feed.field_events == ()


def test_report_is_json_serialisable_and_stamped() -> None:
    report = _feed().as_dict()
    assert report["schema"] == SCHEMA
    json.dumps(report)  # raises on a non-serialisable value
    assert (
        report["rows"][0].get("observed_at")
        in (
            "2026-09-15",
            None,
        )
        or "observed_at" not in report["rows"][0]
    )
    out = canonical_json(report)
    assert out.endswith("\n")
    assert json.loads(out) == report


def test_no_wall_clock_when_snapshot_undated() -> None:
    """SIG-INGEST-018: an undated snapshot leaves observed_at absent, never now."""
    parsed = {"summary": {}, "portals": [{"slug": "a"}, {"slug": "b"}]}
    current = {"summary": {}, "portals": [{"slug": "b"}]}
    feed = portal_change_feed(parsed, current, now=NOW)
    gone = [r for r in feed.claim_rows() if r["subject_id"] == "flock_portal:a"]
    assert len(gone) == 1
    assert "observed_at" not in gone[0]  # never the run's clock
