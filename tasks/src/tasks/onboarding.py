# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Onboarding paths and the moderated usability study (§34.2, SIG-CONTRIB-003).

The contributor system is not "declared complete" on code alone: it must clear a
**moderated usability study** — at least five participants with no prior
knowledge of the ontology, timed from the landing page to their first *accepted*
contribution, with the **median at or under ten minutes**, and the protocol and
results published. This module owns the two intended onboarding paths and the
harness that computes the study's outcome from its recorded participants, so the
≤10-minute target is a re-runnable, testable gate rather than a claim.

The study is *agentic* (it needs real humans), so the as-run study lives as
committed data — ``data/usability_study.toml``, published in prose at
``docs/governance/contributor-onboarding-usability-study.md`` — and this harness
validates it. Re-run on any change to the contribution flow: swap the data,
re-evaluate, and the gate re-checks.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from enum import StrEnum

from ._data import load_table

__all__ = [
    "OnboardingPath",
    "Participant",
    "UsabilityStudy",
    "MIN_NAIVE_PARTICIPANTS",
    "MEDIAN_TARGET_MINUTES",
    "available_paths",
    "load_study",
]


class OnboardingPath(StrEnum):
    """The two intended first-contribution paths (§34.2, SIG-CONTRIB-003).

    Either pick a nearby open task, or submit an observation with a photo and a
    location. Both reach an accepted first contribution without the newcomer
    needing to understand the ontology.
    """

    NEARBY_TASK = "nearby_task"
    OBSERVATION_WITH_PHOTO_AND_LOCATION = "observation_with_photo_and_location"


#: The study needs at least this many ontology-naïve participants (SIG-CONTRIB-003).
MIN_NAIVE_PARTICIPANTS: int = 5

#: The median landing→first-accepted-contribution time MUST be at or under this
#: many minutes (SIG-CONTRIB-003).
MEDIAN_TARGET_MINUTES: float = 10.0


def available_paths() -> tuple[OnboardingPath, ...]:
    """The onboarding paths a newcomer may take (§34.2)."""
    return (OnboardingPath.NEARBY_TASK, OnboardingPath.OBSERVATION_WITH_PHOTO_AND_LOCATION)


@dataclass(frozen=True)
class Participant:
    """One usability-study participant and their timed result (§34.2).

    `ontology_naive` records the SIG-CONTRIB-003 eligibility condition (no prior
    knowledge of the ontology); `minutes_to_first_accepted` is the measured time
    from the landing page to their first *accepted* contribution.
    """

    participant_id: str
    ontology_naive: bool
    minutes_to_first_accepted: float

    def __post_init__(self) -> None:
        if self.minutes_to_first_accepted < 0:
            raise ValueError("minutes_to_first_accepted MUST be non-negative")


@dataclass(frozen=True)
class UsabilityStudy:
    """A moderated usability study and its published outcome (SIG-CONTRIB-003).

    Holds the participants and the publication metadata (the study is only valid
    if it is `moderated` and `published`). The gate is :meth:`meets_requirements`:
    at least five ontology-naïve participants and a median at or under ten
    minutes.
    """

    title: str
    moderated: bool
    published_at: str
    protocol_ref: str
    results_ref: str
    participants: tuple[Participant, ...]

    @property
    def is_published(self) -> bool:
        """Whether the protocol and results are published (SIG-CONTRIB-003)."""
        return bool(self.published_at and self.protocol_ref and self.results_ref)

    def naive_participants(self) -> tuple[Participant, ...]:
        """The ontology-naïve cohort the study measures (SIG-CONTRIB-003)."""
        return tuple(p for p in self.participants if p.ontology_naive)

    def naive_count(self) -> int:
        """How many ontology-naïve participants took part."""
        return len(self.naive_participants())

    def median_minutes(self) -> float:
        """The median landing→first-accepted time over the naïve cohort (minutes).

        Raises if there is no naïve cohort — an empty study has no median to gate.
        """
        cohort = self.naive_participants()
        if not cohort:
            raise ValueError("the study has no ontology-naïve participants to measure")
        return statistics.median(p.minutes_to_first_accepted for p in cohort)

    def meets_requirements(self) -> bool:
        """Whether the study clears the SIG-CONTRIB-003 gate.

        Requires the study to be moderated and published, to have at least
        :data:`MIN_NAIVE_PARTICIPANTS` ontology-naïve participants, and a median
        at or under :data:`MEDIAN_TARGET_MINUTES`.
        """
        return (
            self.moderated
            and self.is_published
            and self.naive_count() >= MIN_NAIVE_PARTICIPANTS
            and self.median_minutes() <= MEDIAN_TARGET_MINUTES
        )


def load_study() -> UsabilityStudy:
    """Build the published usability study from ``data/usability_study.toml``."""
    table = load_table("usability_study")
    study = table["study"]
    participants = tuple(
        Participant(
            participant_id=str(p["id"]),
            ontology_naive=bool(p["ontology_naive"]),
            minutes_to_first_accepted=float(p["minutes_to_first_accepted"]),
        )
        for p in table["participants"]
    )
    return UsabilityStudy(
        title=str(study["title"]),
        moderated=bool(study["moderated"]),
        published_at=str(study["published_at"]),
        protocol_ref=str(study["protocol_ref"]),
        results_ref=str(study["results_ref"]),
        participants=participants,
    )
