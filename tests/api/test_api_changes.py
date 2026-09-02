# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG-API-009 — the /changes feed, driven by the §29.7 snapshot-diff layer."""

from __future__ import annotations

from starlette.testclient import TestClient


def test_changes_feed_emits_field_level_events_from_the_snapshot_diff(
    client: TestClient,
) -> None:
    events = client.get("/v1/changes").json()["events"]
    assert events, "the demo has two snapshots of one artifact → one field change"
    event = events[0]
    assert event["artifact_id"] == "art:portal"
    assert event["field"] == "active_device_count"
    assert event["change_type"] == "modified"
    assert event["old_value"] == 35 and event["new_value"] == 38


def test_changes_feed_can_be_followed_incrementally_with_since(client: TestClient) -> None:
    # A cursor after the only change yields nothing — consumers follow, not re-download.
    empty = client.get("/v1/changes", params={"since": "2026-08-01"}).json()["events"]
    assert empty == []
    # A cursor before it still includes it.
    got = client.get("/v1/changes", params={"since": "2026-01-01"}).json()["events"]
    assert len(got) == 1


def test_a_malformed_since_cursor_is_a_400(client: TestClient) -> None:
    assert client.get("/v1/changes", params={"since": "not-a-date"}).status_code == 400
