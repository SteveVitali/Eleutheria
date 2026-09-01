# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Deployment-lifecycle reconciliation (§29.4, SIG-RECON-038..042)."""

from __future__ import annotations

import pytest
from reconcile.lifecycle import (
    REMOVAL_RENDER_FORBIDDEN,
    REPLACEMENT_RENDER,
    TRACKS,
    Deployment,
    LifecycleEvent,
    detect_vendor_replacement,
    render_lifecycle_status,
    resolve_lifecycle,
    resolve_track,
)


def _ev(track: str, state: str, edtf: str, **kw: object) -> LifecycleEvent:
    return LifecycleEvent(track=track, state=state, edtf=edtf, **kw)


def test_four_tracks_are_resolved_independently() -> None:
    # SIG-RECON-038: the four orthogonal tracks each get their own timeline.
    events = [
        _ev("procurement", "contracted", "2023-01-01"),
        _ev("physical", "installed", "2023-06-01"),
        _ev("operational", "active", "2023-07-01"),
        _ev("authorization", "authorized", "2023-02-01"),
    ]
    rec = resolve_lifecycle("dep:1", events)
    assert set(rec.tracks) == set(TRACKS)
    assert rec.current_states()["procurement"] == "contracted"
    assert rec.current_states()["physical"] == "installed"
    assert rec.current_states()["operational"] == "active"
    assert rec.current_states()["authorization"] == "authorized"


def test_distinct_dated_events_are_ordered() -> None:
    tl = resolve_track(
        "procurement",
        [_ev("procurement", "canceled", "2026"), _ev("procurement", "contracted", "2024")],
    )
    # 2024 precedes 2026: two ordered slots, none unordered.
    assert [s.events[0].state for s in tl.slots] == ["contracted", "canceled"]
    assert all(not s.unordered_within_window for s in tl.slots)
    assert tl.current_state() == "canceled"


def test_overlapping_fuzzy_envelopes_are_unordered_within_window() -> None:
    # SIG-RECON-040: "2025" (all year) overlaps "2025-06-15"; order is indeterminate.
    tl = resolve_track(
        "physical",
        [_ev("physical", "installed", "2025"), _ev("physical", "removed", "2025-06-15")],
    )
    assert len(tl.slots) == 1
    assert tl.slots[0].unordered_within_window is True
    assert set(tl.slots[0].states) == {"installed", "removed"}
    # an unordered final window has no single current state
    assert tl.current_state() is None


def test_event_log_transition_is_preferred_within_a_window() -> None:
    # SIG-RECON-039: the event-log transition surfaces first within a tie window.
    tl = resolve_track(
        "operational",
        [
            _ev("operational", "inferred_active", "2025", from_event_log=False),
            _ev("operational", "logged_active", "2025", from_event_log=True),
        ],
    )
    assert tl.slots[0].events[0].from_event_log is True
    assert tl.slots[0].events[0].state == "logged_active"


# --- SIG-RECON-041: vendor replacement, never "surveillance removed" ----------


def _prior() -> Deployment:
    return Deployment(
        deployment_id="dep:old",
        org_id="org:city",
        technology_family="alpr",
        procurement_state="canceled",
        procurement_end_edtf="2025-06-01",
    )


def _successor() -> Deployment:
    return Deployment(
        deployment_id="dep:new",
        org_id="org:city",
        technology_family="alpr",
        procurement_state="contracted",
        begin_edtf="2025-08-01",
    )


def test_vendor_replacement_is_rendered_as_replacement() -> None:
    edge = detect_vendor_replacement(_prior(), _successor(), window_days=180)
    assert edge is not None
    assert edge.edge_type == "replaced_by"
    assert edge.rendering == REPLACEMENT_RENDER == "vendor replaced"
    assert edge.rendering != REMOVAL_RENDER_FORBIDDEN
    assert edge.org_id == "org:city"


def test_replacement_outside_window_is_not_detected() -> None:
    assert detect_vendor_replacement(_prior(), _successor(), window_days=30) is None


def test_replacement_requires_same_technology_family() -> None:
    other = Deployment(
        deployment_id="dep:new",
        org_id="org:city",
        technology_family="drone",
        procurement_state="contracted",
        begin_edtf="2025-08-01",
    )
    assert detect_vendor_replacement(_prior(), other, window_days=180) is None


def test_successor_predating_cancellation_is_not_a_replacement() -> None:
    early = Deployment(
        deployment_id="dep:new",
        org_id="org:city",
        technology_family="alpr",
        procurement_state="contracted",
        begin_edtf="2024-01-01",
    )
    assert detect_vendor_replacement(_prior(), early, window_days=800) is None


# --- SIG-RECON-042: canceled contract, hardware still present -----------------


def test_canceled_contract_with_hardware_present_is_stated_plainly() -> None:
    status = render_lifecycle_status(
        "dep:1", procurement_state="canceled", physical_state="installed", as_of_edtf="2026-01-01"
    )
    assert status.hardware_present_despite_cancellation is True
    assert status.rendering == "contract canceled; hardware still present as of 2026-01-01"
    assert "removed" not in status.rendering
    assert status.contradiction is not None
    assert status.task is not None
    assert status.task.task_id in status.contradiction.research_task_ids


def test_ordinary_status_renders_both_tracks_without_a_finding() -> None:
    status = render_lifecycle_status(
        "dep:1", procurement_state="contracted", physical_state="installed", as_of_edtf="2026-01-01"
    )
    assert status.hardware_present_despite_cancellation is False
    assert status.contradiction is None
    assert "procurement:contracted" in status.rendering
    assert "physical:installed" in status.rendering


def test_unknown_track_is_rejected() -> None:
    with pytest.raises(ValueError, match="track"):
        LifecycleEvent(track="budget", state="x", edtf="2025")
