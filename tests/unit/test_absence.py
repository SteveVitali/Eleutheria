# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The four absence states, distinguishably encoded and rendered (§9.5).

AC5: the four absence states render distinguishably; `NOT_RESEARCHED` is not the
same as `NO_EVIDENCE_FOUND` (SIG-TIME-010/012).
"""

from __future__ import annotations

import pytest
from db.absence import (
    UNRESOLVED_CONTRADICTION_STATE,
    AbsenceState,
    coverage_kind_for,
    render_absence,
    state_from_coverage_kind,
)


def test_all_four_states_render_distinguishably() -> None:
    renders = {
        AbsenceState.NOT_RESEARCHED: render_absence(AbsenceState.NOT_RESEARCHED),
        AbsenceState.NO_EVIDENCE_FOUND: render_absence(
            AbsenceState.NO_EVIDENCE_FOUND, sources_searched=["Atlas"]
        ),
        AbsenceState.EVIDENCE_OF_ABSENCE: render_absence(AbsenceState.EVIDENCE_OF_ABSENCE),
        AbsenceState.UNRESOLVED: render_absence(AbsenceState.UNRESOLVED, dissenting_claim_count=3),
    }
    codes = {r.code for r in renders.values()}
    labels = {r.label for r in renders.values()}
    details = {r.detail for r in renders.values()}
    assert len(codes) == 4  # every state has a unique machine token
    assert len(labels) == 4
    assert len(details) == 4


def test_not_researched_differs_from_no_evidence_found() -> None:
    """SIG-TIME-012: the two most-conflated states MUST NOT render identically."""
    a = render_absence(AbsenceState.NOT_RESEARCHED)
    b = render_absence(AbsenceState.NO_EVIDENCE_FOUND, sources_searched=["Atlas", "portal"])
    assert a.code != b.code
    assert a.label != b.label
    assert a.detail != b.detail


def test_no_evidence_found_requires_the_sources_searched() -> None:
    """SIG-TIME-011: 'not in the Atlas' vs 'not in the Atlas, portals, and minutes'."""
    with pytest.raises(ValueError, match="SIG-TIME-011"):
        render_absence(AbsenceState.NO_EVIDENCE_FOUND)
    rendered = render_absence(
        AbsenceState.NO_EVIDENCE_FOUND, sources_searched=["Atlas", "portal", "council minutes"]
    )
    assert "council minutes" in rendered.detail


def test_coverage_kind_round_trip() -> None:
    for state in (
        AbsenceState.NOT_RESEARCHED,
        AbsenceState.NO_EVIDENCE_FOUND,
        AbsenceState.EVIDENCE_OF_ABSENCE,
    ):
        assert state_from_coverage_kind(coverage_kind_for(state)) is state


def test_unresolved_is_not_a_coverage_record() -> None:
    # UNRESOLVED lives on the L3 resolution row, not a coverage record.
    with pytest.raises(ValueError):
        coverage_kind_for(AbsenceState.UNRESOLVED)
    assert UNRESOLVED_CONTRADICTION_STATE == "unresolved_conflict"


def test_coverage_kinds_match_the_schema_vocabulary() -> None:
    # graph_annotations.sql absence_kind: not_researched|searched_not_found|
    # evidence_of_absence|not_applicable.
    assert coverage_kind_for(AbsenceState.NOT_RESEARCHED) == "not_researched"
    assert coverage_kind_for(AbsenceState.NO_EVIDENCE_FOUND) == "searched_not_found"
    assert coverage_kind_for(AbsenceState.EVIDENCE_OF_ABSENCE) == "evidence_of_absence"
