# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The CoverageRecord: negative space queryable, and probe negatives retained (§32.1).

AC1: a `searched_not_found` record missing `sources_searched[]` is rejected.
AC3 (API): the four absence kinds render distinguishably; `not_researched` is not
`searched_not_found`. SIG-METRIC-002a: discovery-probe negatives are retained.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from inference.coverage import CoverageRecord, probe_coverage_records


def test_searched_not_found_requires_sources_searched() -> None:
    """AC1 / SIG-METRIC-001/002: a record missing sources_searched is rejected."""
    with pytest.raises(ValueError, match="SIG-METRIC-001/002"):
        CoverageRecord(
            predicate_id="active_device_count",
            absence_kind="searched_not_found",
            subject_id="agency:okcpd",
        )
    # With the sources named, it is accepted.
    rec = CoverageRecord(
        predicate_id="active_device_count",
        absence_kind="searched_not_found",
        subject_id="agency:okcpd",
        sources_searched=("Atlas", "portal", "council minutes"),
    )
    assert rec.sources_searched == ("Atlas", "portal", "council minutes")


def test_other_kinds_do_not_require_sources() -> None:
    for kind in ("not_researched", "evidence_of_absence", "not_applicable"):
        rec = CoverageRecord(
            predicate_id="active_device_count",
            absence_kind=kind,
            subject_class="agency",
            jurisdiction_id="jurisdiction:ok",
        )
        assert rec.absence_kind == kind


def test_coverage_record_requires_a_subject_identity() -> None:
    with pytest.raises(ValueError, match="identify a subject"):
        CoverageRecord(predicate_id="active_device_count", absence_kind="not_researched")


def test_unknown_absence_kind_is_rejected() -> None:
    with pytest.raises(ValueError, match="not one of"):
        CoverageRecord(
            predicate_id="active_device_count",
            absence_kind="made_up",
            subject_id="agency:okcpd",
        )


def test_epistemic_state_maps_kinds_and_not_applicable_is_stateless() -> None:
    """SIG-TIME-010: kinds map to §9.5 states; `not_applicable` has none."""
    states = {
        "not_researched": "NOT_RESEARCHED",
        "searched_not_found": "NO_EVIDENCE_FOUND",
        "evidence_of_absence": "EVIDENCE_OF_ABSENCE",
    }
    for kind, expected in states.items():
        rec = CoverageRecord(
            predicate_id="active_device_count",
            absence_kind=kind,
            subject_id="agency:okcpd",
            sources_searched=("Atlas",) if kind == "searched_not_found" else (),
        )
        assert rec.epistemic_state is not None
        assert rec.epistemic_state.value == expected
    na = CoverageRecord(
        predicate_id="active_device_count", absence_kind="not_applicable", subject_id="x"
    )
    assert na.epistemic_state is None


def test_four_kinds_render_distinguishably_in_the_api_view() -> None:
    """AC3 (API contract): the four absence kinds do not render identically."""

    def _view(kind: str) -> dict[str, object]:
        rec = CoverageRecord(
            predicate_id="active_device_count",
            absence_kind=kind,
            subject_id="agency:okcpd",
            sources_searched=("Atlas",) if kind == "searched_not_found" else (),
        )
        return rec.public_view()

    views = [
        _view(k)
        for k in ("not_researched", "searched_not_found", "evidence_of_absence", "not_applicable")
    ]
    codes = {v["absence_code"] for v in views}
    labels = {v["absence_label"] for v in views}
    assert len(codes) == 4
    assert len(labels) == 4
    # The two most-conflated states are explicitly distinct in the wire view.
    assert _view("not_researched")["absence_code"] != _view("searched_not_found")["absence_code"]


def test_public_view_carries_the_full_shape() -> None:
    rec = CoverageRecord(
        predicate_id="active_device_count",
        absence_kind="searched_not_found",
        subject_id="agency:okcpd",
        jurisdiction_id="jurisdiction:ok",
        sources_searched=("Atlas", "portal"),
        searched_at=datetime(2026, 1, 2, tzinfo=UTC),
        searched_by="pipeline:records",
        search_method="portal_probe",
    )
    view = rec.public_view()
    assert view["epistemic_state"] == "NO_EVIDENCE_FOUND"
    assert view["sources_searched"] == ["Atlas", "portal"]
    assert view["searched_at"] == "2026-01-02T00:00:00+00:00"
    assert view["search_method"] == "portal_probe"


# --- discovery-probe negatives retained (SIG-METRIC-002a) --------------------


def test_probe_retains_only_the_confirmed_absent_candidates() -> None:
    """SIG-METRIC-002a: the 5,011 confirmed-absent slugs are kept, not discarded."""
    records = probe_coverage_records(
        predicate_id="portal_exists",
        candidates=["okc", "tulsa", "norman", "edmond"],
        present=["okc", "tulsa"],
        sources_searched=["flock-slug-probe"],
        subject_class="portal",
        jurisdiction_id="jurisdiction:ok",
    )
    subjects = {r.subject_id for r in records}
    assert subjects == {"norman", "edmond"}  # only the absent candidates
    assert all(r.absence_kind == "searched_not_found" for r in records)
    assert all(r.sources_searched == ("flock-slug-probe",) for r in records)


def test_probe_is_a_denominator_present_plus_absent_equals_candidates() -> None:
    candidates = [f"slug{i}" for i in range(10)]
    present = ["slug1", "slug7"]
    records = probe_coverage_records(
        predicate_id="portal_exists",
        candidates=candidates,
        present=present,
        sources_searched=["probe"],
    )
    # The behavioral property: the records are *exactly* the candidates not present —
    # every negative retained, no positive retained (SIG-METRIC-002a).
    assert {r.subject_id for r in records} == set(candidates) - set(present)
    # tested = present + absent; the negatives are what make it a denominator.
    assert len(records) + len(present) == len(candidates)


def test_probe_rejects_a_present_id_outside_the_candidate_space() -> None:
    with pytest.raises(ValueError, match="not in the probed candidate"):
        probe_coverage_records(
            predicate_id="portal_exists",
            candidates=["a", "b"],
            present=["a", "z"],
            sources_searched=["probe"],
        )


def test_probe_requires_named_sources() -> None:
    with pytest.raises(ValueError, match="SIG-METRIC-002"):
        probe_coverage_records(
            predicate_id="portal_exists",
            candidates=["a", "b"],
            present=["a"],
            sources_searched=[],
        )
