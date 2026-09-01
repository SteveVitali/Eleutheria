# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Anti-abuse: recognition without volume gamification (§33.6, SIG-TASK-012).

Tasks MUST NOT be gamified with public leaderboards ranking contributors by volume:
volume incentives in an evidence system produce low-quality submissions at scale.
Recognition SHOULD instead be qualitative and tied to **verified** contributions.

This module makes both halves executable. Recognition is derived only from a
contributor's *verified* contributions and expressed as qualitative facets (the
kinds of work verified), never a count-based score — so two contributors with wildly
different raw submission volume but the same verified work are recognised
identically. And the prohibited artifact is an executable refusal: building a
volume leaderboard raises, mirroring the P09.1 precedent of encoding a MUST NOT as a
function that always raises rather than a comment nobody runs.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

__all__ = [
    "VerifiedContribution",
    "Recognition",
    "ProhibitedLeaderboardError",
    "recognize",
    "volume_leaderboard",
]


class ProhibitedLeaderboardError(RuntimeError):
    """Raised by any attempt to rank contributors by volume (SIG-TASK-012).

    A public volume leaderboard is prohibited outright, so the "build one" entry
    point is an executable refusal, not a convention: the ban is a test.
    """


@dataclass(frozen=True)
class VerifiedContribution:
    """One contribution by a contributor, with its verification state (§34.1).

    Recognition keys off `verified`: an unreviewed submission confers nothing until a
    reviewer verifies it (SIG-TASK-012 — recognition is tied to *verified*
    contributions). `facet` names the *kind* of work (e.g. a task type or assignee
    class), which is what recognition surfaces qualitatively — not a point value.
    """

    contribution_id: str
    contributor: str
    facet: str
    verified: bool


@dataclass(frozen=True)
class Recognition:
    """A contributor's qualitative recognition (§33.6).

    Carries the verified contribution ids that back it and the distinct facets of
    verified work — deliberately *no* score, rank, or count field, because there is
    no ordering by volume to expose (SIG-TASK-012).
    """

    contributor: str
    verified_contribution_ids: tuple[str, ...]
    facets: tuple[str, ...]

    @property
    def is_recognised(self) -> bool:
        """Whether the contributor has any verified work to be recognised for."""
        return bool(self.verified_contribution_ids)


def recognize(contributor: str, contributions: Iterable[VerifiedContribution]) -> Recognition:
    """Compute a contributor's qualitative recognition (SIG-TASK-012).

    Uses only that contributor's **verified** contributions; unverified submissions
    are ignored, so raw volume cannot inflate recognition. The result is the set of
    distinct verified facets (sorted for determinism) and the backing ids — a
    qualitative summary, never a count-ranked score.
    """
    verified = [c for c in contributions if c.contributor == contributor and c.verified]
    return Recognition(
        contributor=contributor,
        verified_contribution_ids=tuple(c.contribution_id for c in verified),
        facets=tuple(sorted({c.facet for c in verified})),
    )


def volume_leaderboard(*_args: object, **_kwargs: object) -> None:
    """Refuse to build a volume leaderboard (SIG-TASK-012) — always raises.

    There is intentionally no implementation: ranking contributors by volume is
    prohibited, and encoding that as a raising function means the prohibition is
    enforced by CI rather than trusted to reviewers.
    """
    raise ProhibitedLeaderboardError(
        "ranking contributors by volume is prohibited (SIG-TASK-012); recognition is "
        "qualitative and tied to verified contributions — use recognize()"
    )
