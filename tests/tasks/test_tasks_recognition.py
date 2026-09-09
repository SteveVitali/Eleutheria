# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Anti-abuse: recognition without volume gamification (§33.6).

SIG-TASK-012: no volume leaderboards; recognition is qualitative and tied to verified
contributions.
"""

from __future__ import annotations

import pytest
from tasks.recognition import (
    ProhibitedLeaderboardError,
    VerifiedContribution,
    recognize,
    volume_leaderboard,
)


def test_recognition_ignores_unverified_volume() -> None:
    """SIG-TASK-012: recognition is tied to *verified* contributions, not volume."""
    prolific_unverified = [
        VerifiedContribution(f"c{i}", "spammer", facet="field_mapper", verified=False)
        for i in range(100)
    ]
    one_verified = [VerifiedContribution("c0", "careful", facet="field_mapper", verified=True)]
    spammer = recognize("spammer", prolific_unverified)
    careful = recognize("careful", one_verified)
    # The 100-submission spammer is not recognised at all; the careful contributor is.
    assert spammer.verified_contribution_ids == ()
    assert not spammer.is_recognised
    assert careful.is_recognised
    assert careful.facets == ("field_mapper",)


def test_recognition_is_qualitative_not_a_count() -> None:
    """Recognition exposes distinct facets of verified work, never a score/rank."""
    contribs = [
        VerifiedContribution("a", "u", facet="records_requester", verified=True),
        VerifiedContribution("b", "u", facet="records_requester", verified=True),
        VerifiedContribution("c", "u", facet="field_mapper", verified=True),
    ]
    rec = recognize("u", contribs)
    # Facets are distinct and sorted; there is deliberately no count/score field.
    assert rec.facets == ("field_mapper", "records_requester")
    assert not hasattr(rec, "score")
    assert not hasattr(rec, "rank")


def test_two_contributors_with_same_verified_work_are_recognised_equally() -> None:
    heavy = [
        VerifiedContribution("h1", "heavy", facet="analyst", verified=True),
        *[
            VerifiedContribution(f"hx{i}", "heavy", facet="analyst", verified=False)
            for i in range(50)
        ],
    ]
    light = [VerifiedContribution("l1", "light", facet="analyst", verified=True)]
    assert recognize("heavy", heavy).facets == recognize("light", light).facets


def test_volume_leaderboard_is_an_executable_refusal() -> None:
    """SIG-TASK-012: building a volume leaderboard is prohibited — it always raises."""
    with pytest.raises(ProhibitedLeaderboardError, match="SIG-TASK-012"):
        volume_leaderboard({"alice": 100, "bob": 3})


def test_recognition_filters_to_the_named_contributor() -> None:
    contribs = [
        VerifiedContribution("a", "alice", facet="curator", verified=True),
        VerifiedContribution("b", "bob", facet="curator", verified=True),
    ]
    assert recognize("alice", contribs).verified_contribution_ids == ("a",)
