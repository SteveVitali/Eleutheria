# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Vandalism and poisoning resistance (§34.4, SIG-CONTRIB-010/011/011a/011b/011c).

AC5: anomaly detection routes bursts / coordinated-similar / contested-resolving
submissions to review (never auto-reject), and guards false absence equally.
AC6: the vendor operating-territory check holds an unsupported claim at the lowest
confidence and raises a verification task. Plus the no-mass-revert and
visual-weight disciplines.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from tasks.poisoning import (
    AnomalyDetector,
    ClaimSource,
    ContributionSignal,
    MassRevertRefusedError,
    ReviewReason,
    RoutingDecision,
    apply_reverts_automatically,
    assert_distinct_visual_weight,
    check_operating_territory,
    renders_with_same_weight,
    suggest_reverts_for_review,
    visual_weight,
)

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _signal(
    handle: str,
    *,
    fp: str = "fp",
    polarity: str = "affirms",
    at: datetime = _NOW,
    contested: bool = False,
) -> ContributionSignal:
    return ContributionSignal(
        handle=handle,
        subject_id="deployment:x",
        predicate_id="has_device",
        content_fingerprint=fp,
        submitted_at=at,
        polarity=polarity,
        resolves_contested=contested,
    )


# --- anomaly detection (SIG-CONTRIB-010/011) ------------------------------- #
def test_no_auto_reject_outcome_exists() -> None:
    """SIG-CONTRIB-010: auto-rejection is unrepresentable — only accept / route-to-review."""
    assert {d.value for d in RoutingDecision} == {"accept", "route_to_review"}
    assert "reject" not in {d.value for d in RoutingDecision}


def test_benign_submission_is_accepted() -> None:
    detector = AnomalyDetector()
    [verdict] = detector.assess([_signal("alice")])
    assert verdict.decision is RoutingDecision.ACCEPT
    assert verdict.reasons == ()


def test_burst_routes_to_review() -> None:
    """SIG-CONTRIB-010: a burst from one handle is held for review, not rejected."""
    detector = AnomalyDetector()
    signals = [_signal("floods", at=_NOW + timedelta(minutes=i)) for i in range(6)]
    verdicts = detector.assess(signals)
    assert all(v.decision is RoutingDecision.ROUTE_TO_REVIEW for v in verdicts)
    assert all(ReviewReason.BURST in v.reasons for v in verdicts)


def test_coordinated_similar_routes_to_review() -> None:
    """SIG-CONTRIB-010: identical submissions across handles route to review."""
    detector = AnomalyDetector()
    signals = [_signal(h, fp="same-node") for h in ("a", "b", "c")]
    verdicts = detector.assess(signals)
    assert all(v.decision is RoutingDecision.ROUTE_TO_REVIEW for v in verdicts)
    assert all(ReviewReason.COORDINATED_SIMILAR in v.reasons for v in verdicts)


def test_contested_resolving_routes_to_review() -> None:
    """SIG-CONTRIB-010: a submission that conveniently resolves a contested claim."""
    detector = AnomalyDetector()
    [verdict] = detector.assess([_signal("alice", contested=True)])
    assert verdict.decision is RoutingDecision.ROUTE_TO_REVIEW
    assert ReviewReason.CONTESTED_RESOLVING in verdict.reasons


def test_false_absence_is_guarded_equally() -> None:
    """SIG-CONTRIB-011: a false-absence burst routes exactly like a false-presence one."""
    detector = AnomalyDetector()
    affirms = detector.assess(
        [_signal("f", polarity="affirms", at=_NOW + timedelta(minutes=i)) for i in range(6)]
    )
    denies = detector.assess(
        [_signal("f", polarity="denies", at=_NOW + timedelta(minutes=i)) for i in range(6)]
    )
    # The detector never branches on polarity: identical decisions and reasons.
    assert [v.decision for v in affirms] == [v.decision for v in denies]
    assert [v.reasons for v in affirms] == [v.reasons for v in denies]
    assert all(v.routed_to_review for v in denies)


# --- vendor operating-territory (SIG-CONTRIB-011a) ------------------------- #
def test_unsupported_territory_held_at_lowest_confidence_with_task() -> None:
    """AC6 / SIG-CONTRIB-011a: no independent V-in-C evidence → lowest confidence + task."""
    verdict = check_operating_territory(
        vendor_id="vendor:acme",
        region_id="region:pl",
        known_operating_regions={"region:us", "region:ca"},
    )
    assert verdict.plausible is False
    assert verdict.confidence == "lowest"
    assert verdict.enters_graph_as_observation is False
    assert verdict.verification_task is not None
    assert verdict.verification_task.region_id == "region:pl"
    assert verdict.verification_task.task_type == "verify_vendor_operating_territory"


def test_supported_territory_enters_normally() -> None:
    """SIG-CONTRIB-011a: independent evidence that V operates in C → normal entry."""
    verdict = check_operating_territory(
        vendor_id="vendor:acme",
        region_id="region:us",
        known_operating_regions={"region:us", "region:ca"},
    )
    assert verdict.plausible is True
    assert verdict.confidence == "normal"
    assert verdict.enters_graph_as_observation is True
    assert verdict.verification_task is None


# --- no SIG-caused mass revert (SIG-CONTRIB-011b) -------------------------- #
def test_sig_never_auto_applies_a_mass_revert() -> None:
    """SIG-CONTRIB-011b: SIG must not be the proximate cause of a mass revert."""
    with pytest.raises(MassRevertRefusedError):
        apply_reverts_automatically([("deployment:a", "implausible", "ev:1")])


def test_reverts_are_suggestions_not_writes() -> None:
    """SIG-CONTRIB-011b: implausible-node handling produces suggestions, never applications."""
    suggestions = suggest_reverts_for_review(
        [("deployment:a", "implausible node", "ev:1"), ("deployment:b", "fabricated", "ev:2")]
    )
    assert len(suggestions) == 2
    assert all(not s.applied_by_sig for s in suggestions)


# --- visual weight (SIG-CONTRIB-011c) -------------------------------------- #
def test_unverified_renders_below_records_derived() -> None:
    """SIG-CONTRIB-011c: an unverified observation never shares records-derived weight."""
    assert visual_weight(ClaimSource.UNVERIFIED_COMMUNITY) < visual_weight(
        ClaimSource.RECORDS_DERIVED
    )
    assert not renders_with_same_weight(
        ClaimSource.UNVERIFIED_COMMUNITY, ClaimSource.RECORDS_DERIVED
    )
    # The assertion helper does not raise on the correct configuration.
    assert_distinct_visual_weight()
