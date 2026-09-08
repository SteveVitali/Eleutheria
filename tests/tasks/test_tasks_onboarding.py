# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Onboarding paths and the moderated usability study (§34.2, SIG-CONTRIB-003).

AC7: the study runs with ≥5 ontology-naïve participants, the protocol and results
are published, and the median landing→first-accepted time is ≤10 minutes. The
study itself is agentic (real humans); the harness re-checks the recorded result.
"""

from __future__ import annotations

import pytest
from tasks.onboarding import (
    MEDIAN_TARGET_MINUTES,
    MIN_NAIVE_PARTICIPANTS,
    OnboardingPath,
    Participant,
    UsabilityStudy,
    available_paths,
    load_study,
)


def _study(participants: tuple[Participant, ...], *, moderated: bool = True) -> UsabilityStudy:
    return UsabilityStudy(
        title="test",
        moderated=moderated,
        published_at="2026-09-08",
        protocol_ref="docs/governance/contributor-onboarding-usability-study.md",
        results_ref="docs/governance/contributor-onboarding-usability-study.md#results",
        participants=participants,
    )


def _naive(minutes: float, n: int) -> tuple[Participant, ...]:
    return tuple(
        Participant(participant_id=f"P{i}", ontology_naive=True, minutes_to_first_accepted=minutes)
        for i in range(n)
    )


def test_two_onboarding_paths() -> None:
    """SIG-CONTRIB-003: pick a nearby task, or submit an observation with photo+location."""
    assert set(available_paths()) == {
        OnboardingPath.NEARBY_TASK,
        OnboardingPath.OBSERVATION_WITH_PHOTO_AND_LOCATION,
    }


def test_published_study_meets_the_gate() -> None:
    """AC7 / SIG-CONTRIB-003: the as-run study clears every clause of the gate."""
    study = load_study()
    assert study.moderated
    assert study.is_published
    assert study.naive_count() >= MIN_NAIVE_PARTICIPANTS
    assert study.median_minutes() <= MEDIAN_TARGET_MINUTES
    assert study.meets_requirements()


def test_study_measures_only_the_ontology_naive_cohort() -> None:
    """SIG-CONTRIB-003: the SIG-experienced control is excluded from the median."""
    study = load_study()
    assert study.naive_count() == 6
    assert len(study.participants) == 7  # six naïve + one experienced control


def test_gate_fails_without_enough_naive_participants() -> None:
    """SIG-CONTRIB-003: fewer than five ontology-naïve participants fails the gate."""
    study = _study(_naive(5.0, MIN_NAIVE_PARTICIPANTS - 1))
    assert not study.meets_requirements()


def test_gate_fails_when_median_exceeds_target() -> None:
    """SIG-CONTRIB-003: a median above ten minutes fails, even with enough participants."""
    study = _study(_naive(12.0, MIN_NAIVE_PARTICIPANTS + 2))
    assert study.naive_count() >= MIN_NAIVE_PARTICIPANTS
    assert study.median_minutes() > MEDIAN_TARGET_MINUTES
    assert not study.meets_requirements()


def test_gate_requires_moderation_and_publication() -> None:
    """SIG-CONTRIB-003: an un-moderated study cannot pass."""
    study = _study(_naive(5.0, MIN_NAIVE_PARTICIPANTS + 1), moderated=False)
    assert not study.meets_requirements()


def test_empty_cohort_has_no_median() -> None:
    study = _study(())
    with pytest.raises(ValueError, match="no ontology-naïve participants"):
        study.median_minutes()
