# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The officer-naming test (§43.4, SIG-PUB-007..010)."""

from __future__ import annotations

from policy.officer import (
    OfficerNamingProngs,
    ReviewerConcurrence,
    evaluate_officer_naming,
)


def _all_prongs() -> OfficerNamingProngs:
    return OfficerNamingProngs(True, True, True, True, True)


def _two_reviewers() -> tuple[ReviewerConcurrence, ...]:
    return (
        ReviewerConcurrence("reviewer-a", agrees=True, rationale="conduct is official"),
        ReviewerConcurrence("reviewer-b", agrees=True, rationale="name on the record"),
    )


def test_all_five_prongs_plus_two_reviewers_permits() -> None:
    d = evaluate_officer_naming(_all_prongs(), _two_reviewers())
    assert d.permitted is True
    assert len(d.reviewers) == 2  # recorded


def test_a_single_failed_prong_rejects() -> None:
    prongs = OfficerNamingProngs(True, False, True, True, True)  # not on face of record
    d = evaluate_officer_naming(prongs, _two_reviewers())
    assert d.permitted is False
    assert "name_on_face_of_record" in d.reason


def test_missing_second_reviewer_rejects() -> None:
    d = evaluate_officer_naming(_all_prongs(), _two_reviewers()[:1])
    assert d.permitted is False


def test_reviewer_disagreement_defaults_to_no_publish() -> None:
    reviewers = (
        ReviewerConcurrence("reviewer-a", agrees=True, rationale="ok"),
        ReviewerConcurrence("reviewer-b", agrees=False, rationale="not proportionate"),
    )
    d = evaluate_officer_naming(_all_prongs(), reviewers)
    assert d.permitted is False


def test_concurrence_requires_written_rationale() -> None:
    reviewers = (
        ReviewerConcurrence("reviewer-a", agrees=True, rationale=""),
        ReviewerConcurrence("reviewer-b", agrees=True, rationale=""),
    )
    d = evaluate_officer_naming(_all_prongs(), reviewers)
    assert d.permitted is False


def test_reviewers_must_be_independent() -> None:
    reviewers = (
        ReviewerConcurrence("reviewer-a", agrees=True, rationale="ok", independent=True),
        ReviewerConcurrence("reviewer-b", agrees=True, rationale="ok", independent=False),
    )
    d = evaluate_officer_naming(_all_prongs(), reviewers)
    assert d.permitted is False


def test_home_address_is_outside_the_test_entirely() -> None:
    d = evaluate_officer_naming(_all_prongs(), _two_reviewers(), is_home_address=True)
    assert d.permitted is False
    assert "SIG-PUB-009" in d.reason


def test_routine_audit_row_does_not_trigger_the_test() -> None:
    d = evaluate_officer_naming(_all_prongs(), _two_reviewers(), is_routine_audit_row=True)
    assert d.permitted is False
    assert "SIG-PUB-010" in d.reason
