# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Deployment-lifecycle reconciliation (§29.4, SIG-RECON-038..042)."""

from __future__ import annotations

import pytest
from reconcile.lifecycle import (
    REMOVAL_RENDER_FORBIDDEN,
    REPLACEMENT_RENDER,
    SOFT_PHYSICAL_REMOVED_OPERATIONAL_ACTIVE,
    SOFT_PROCUREMENT_CANCELED_OPERATIONAL_ACTIVE,
    TRACKS,
    Deployment,
    LifecycleEvent,
    detect_soft_constraints,
    detect_vendor_replacement,
    lifecycle_events_from_claims,
    render_lifecycle_status,
    resolve_lifecycle,
    resolve_track,
    track_for_state,
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


def test_event_log_decides_the_state_in_a_mixed_window() -> None:
    # P37.9 / SIG-RECON-039: one event-log transition in a window of inferred
    # evidence DECIDES the state — the window stays recorded as unordered
    # (SIG-RECON-040) but the log's transition is the resolved current state.
    tl = resolve_track(
        "operational",
        [
            _ev("operational", "active", "2025", from_event_log=True),
            _ev("operational", "suspended", "2025-06", from_event_log=False),
        ],
    )
    assert tl.slots[0].unordered_within_window is True
    assert tl.current_state() == "active"


def test_two_event_log_transitions_in_one_window_decide_nothing() -> None:
    # Two competing event-log transitions are BOTH top-quality evidence; where
    # their envelopes overlap the order is genuinely indeterminate — RECON-040
    # keeps the window unordered and no state is invented.
    tl = resolve_track(
        "physical",
        [
            _ev("physical", "installed", "2025", from_event_log=True),
            _ev("physical", "removed", "2025-06", from_event_log=True),
        ],
    )
    assert tl.slots[0].unordered_within_window is True
    assert tl.current_state() is None


# --- from claims: the event-log / inferred split (SIG-RECON-039) ---------------


def test_lifecycle_events_from_claims_split_event_log_and_inferred() -> None:
    rows = [
        (
            "dep:1",
            "deployment_lifecycle_transition",
            '{"state": "active", "date": "2025-06"}',
            "c1",
        ),
        ("dep:1", "lifecycle_transition", '{"state": "contracted", "date": "2025-01-15"}', "c2"),
    ]
    by_subject = lifecycle_events_from_claims(rows)
    events = by_subject["dep:1"]
    logged = next(e for e in events if e.claim_id == "c1")
    assert logged.from_event_log is True
    assert logged.track == "operational"  # state's own vocabulary routes it
    assert logged.edtf == "2025-06"
    inferred = next(e for e in events if e.claim_id == "c2")
    assert inferred.from_event_log is False
    assert inferred.track == "procurement"  # the predicate's declared track
    rec = resolve_lifecycle("dep:1", events)
    assert rec.current_states()["operational"] == "active"
    assert rec.current_states()["procurement"] == "contracted"


def test_lifecycle_events_from_claims_handles_edtf_fallbacks_and_undated() -> None:
    rows = [
        # observed_edtf fallback at position 4
        ("dep:1", "lifecycle_transition", {"state": "awarded", "date": None}, "c1", "2024-11"),
        # no date anywhere → the explicitly-undated event (never ordered)
        ("dep:1", "lifecycle_transition", {"state": "contracted"}, "c2"),
        # garbage date → undated, not an invented instant
        ("dep:1", "lifecycle_transition", {"state": "canceled", "date": "not-a-date"}, "c3"),
    ]
    events = lifecycle_events_from_claims(rows)["dep:1"]
    assert len(events) == 3
    dated = [e for e in events if e.edtf != ".."]
    undated = [e for e in events if e.edtf == ".."]
    assert [e.edtf for e in dated] == ["2024-11"]
    assert len(undated) == 2


def test_lifecycle_events_from_claims_skips_unroutable_and_unknown_states() -> None:
    rows = [
        ("dep:1", "deployment_lifecycle_transition", {"state": "unknown", "date": "2025"}, "c1"),
        (
            "dep:1",
            "deployment_lifecycle_transition",
            {"state": "not_a_state", "date": "2025"},
            "c2",
        ),
        ("dep:1", "lifecycle_transition", "not json", "c3"),
        ("dep:1", "camera_latitude", {"state": "installed", "date": "2025"}, "c4"),
    ]
    assert lifecycle_events_from_claims(rows) == {}


def test_track_for_state_routes_and_refuses() -> None:
    assert track_for_state("canceled") == "procurement"
    assert track_for_state("removed") == "physical"
    assert track_for_state("active") == "operational"
    assert track_for_state("authorized") == "authorization"
    assert track_for_state("unknown") is None  # admissible on all four — no signal
    assert track_for_state("bogus") is None


# --- SIG-ONTO-064: the free_trial path is legal --------------------------------


def test_free_trial_to_active_is_a_legal_path() -> None:
    # ONTO-064: `free_trial → operational:active` with NO procurement
    # transition is the discovery-mission edge — legal, never flagged.
    events = [
        _ev("procurement", "free_trial", "2025-01"),
        _ev("operational", "active", "2025-02"),
    ]
    rec = resolve_lifecycle("dep:ft", events)
    assert rec.current_states()["procurement"] == "free_trial"
    assert rec.current_states()["operational"] == "active"
    report = detect_soft_constraints(rec, as_of_edtf="2026-01-01")
    assert report.findings == ()
    assert report.fired(SOFT_PHYSICAL_REMOVED_OPERATIONAL_ACTIVE) is False
    assert report.fired(SOFT_PROCUREMENT_CANCELED_OPERATIONAL_ACTIVE) is False


# --- SIG-ONTO-065: the two owned soft-constraint detectors ----------------------


def test_removed_and_active_flags_a_data_error() -> None:
    rec = resolve_lifecycle(
        "dep:1",
        [
            _ev("physical", "installed", "2024"),
            _ev("physical", "removed", "2025"),
            _ev("operational", "active", "2025-03"),
        ],
    )
    report = detect_soft_constraints(rec, as_of_edtf="2026-01-01")
    assert report.fired(SOFT_PHYSICAL_REMOVED_OPERATIONAL_ACTIVE)
    finding = next(f for f in report.findings if f.disposition == "data_error")
    assert finding.contradiction is not None
    assert finding.contradiction.contradiction_type == "temporal_impossibility"
    assert finding.task is not None
    assert finding.task.task_id in finding.contradiction.research_task_ids
    assert "flagged, never rejected" in finding.rendering


def test_canceled_and_active_flags_a_wind_down_task_not_a_contradiction() -> None:
    # Legal during wind-down: a research task, never a contradiction.
    rec = resolve_lifecycle(
        "dep:1",
        [
            _ev("procurement", "contracted", "2023"),
            _ev("procurement", "canceled", "2025-09"),
            _ev("operational", "active", "2025-10"),
        ],
    )
    report = detect_soft_constraints(rec, as_of_edtf="2026-01-01")
    assert report.fired(SOFT_PROCUREMENT_CANCELED_OPERATIONAL_ACTIVE)
    assert report.contradictions == ()
    (task,) = report.tasks
    assert task.task_type == "canceled_contract_still_active"
    assert "wind-down" in task.closing_condition


def test_soft_constraints_do_not_fire_on_undecided_or_clean_states() -> None:
    # An unordered-inferred final window decides no state → nothing fires.
    rec = resolve_lifecycle(
        "dep:1",
        [
            _ev("physical", "removed", "2025"),
            _ev("physical", "installed", "2025-06"),
            _ev("operational", "active", "2025-03"),
        ],
    )
    assert rec.current_states()["physical"] is None
    assert detect_soft_constraints(rec, as_of_edtf="2026-01-01").findings == ()
    # procured-and-installed: the ordinary state flags nothing either.
    clean = resolve_lifecycle(
        "dep:2", [_ev("procurement", "contracted", "2024"), _ev("physical", "installed", "2024-06")]
    )
    assert detect_soft_constraints(clean, as_of_edtf="2026-01-01").findings == ()


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
