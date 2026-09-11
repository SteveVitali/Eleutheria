# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Vandalism and poisoning resistance (§34.4, SIG-CONTRIB-010/011/011a/011b/011c).

The dominant live failure mode in this domain is **inflationary** — panic-driven
or adversarial over-reporting (R12-F12.28), not honest error — so none of these
rules assume good faith. Five disciplines are made executable here:

* **Anomaly detection routes, never rejects (SIG-CONTRIB-010).** Bursts,
  coordinated-similar submissions, and submissions that conveniently resolve a
  contested claim are routed to human review. :class:`RoutingDecision` has *no*
  ``reject`` value — auto-rejection is unrepresentable, which is the guarantee.
* **False absence is guarded equally (SIG-CONTRIB-011).** The detector never
  branches on polarity: a coordinated campaign asserting a deployment does *not*
  exist trips the same rules as one asserting it does. This threat hides as
  helpfulness, so equal guarding is deliberate.
* **Vendor operating-territory (SIG-CONTRIB-011a).** A claim that vendor V runs a
  device in region C, where SIG holds no independent evidence V operates in C at
  all, is held at the lowest confidence and generates a verification task rather
  than entering the graph as an observation.
* **No SIG-caused mass revert (SIG-CONTRIB-011b).** SIG never auto-applies a bulk
  revert; implausible-node handling produces human-reviewed *suggestions*, never
  writes. :func:`apply_reverts_automatically` is a hard refusal.
* **Visual weight (SIG-CONTRIB-011c).** An unverified community observation MUST
  NOT render with the same visual weight as a records-derived claim.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

__all__ = [
    "RoutingDecision",
    "ReviewReason",
    "ContributionSignal",
    "AnomalyConfig",
    "AnomalyVerdict",
    "AnomalyDetector",
    "TerritoryVerdict",
    "VerificationTask",
    "check_operating_territory",
    "ClaimSource",
    "PRESENTATION_WEIGHT",
    "visual_weight",
    "renders_with_same_weight",
    "assert_distinct_visual_weight",
    "RevertSuggestion",
    "MassRevertRefusedError",
    "suggest_reverts_for_review",
    "apply_reverts_automatically",
]


# --------------------------------------------------------------------------- #
# Anomaly detection (SIG-CONTRIB-010/011)                                     #
# --------------------------------------------------------------------------- #
class RoutingDecision(StrEnum):
    """What the anomaly detector does with a submission (SIG-CONTRIB-010).

    There are exactly two outcomes — accept, or route to human review. There is
    deliberately **no ``reject``**: the spec forbids auto-rejection, so the
    vocabulary cannot express it.
    """

    ACCEPT = "accept"
    ROUTE_TO_REVIEW = "route_to_review"


class ReviewReason(StrEnum):
    """Why a submission was routed to review (§34.4)."""

    BURST = "burst"
    COORDINATED_SIMILAR = "coordinated_similar"
    CONTESTED_RESOLVING = "contested_resolving"


@dataclass(frozen=True)
class ContributionSignal:
    """The anomaly-relevant facets of one submission.

    `polarity` is ``"affirms"`` (a deployment exists) or ``"denies"`` (a false-
    absence claim). The detector never branches on it — that is SIG-CONTRIB-011's
    equal-guarding made structural. `content_fingerprint` is a normalized hash of
    the assertion used to spot coordinated-similar submissions across handles.
    """

    handle: str
    subject_id: str
    predicate_id: str
    content_fingerprint: str
    submitted_at: datetime
    polarity: str = "affirms"
    resolves_contested: bool = False


@dataclass(frozen=True)
class AnomalyConfig:
    """Thresholds for the §34.4 pattern rules (data, tunable per deployment)."""

    #: More than this many submissions from one handle inside `burst_window`.
    burst_threshold: int = 5
    burst_window: timedelta = timedelta(hours=1)
    #: At least this many identical fingerprints (any handles) inside the window.
    coordination_threshold: int = 3
    coordination_window: timedelta = timedelta(hours=24)


@dataclass(frozen=True)
class AnomalyVerdict:
    """The routing decision for one signal, with the reasons that drove it."""

    decision: RoutingDecision
    reasons: tuple[ReviewReason, ...]

    @property
    def routed_to_review(self) -> bool:
        """Whether the submission was held for review rather than accepted."""
        return self.decision is RoutingDecision.ROUTE_TO_REVIEW


class AnomalyDetector:
    """Routes anomalous contribution patterns to review, never to rejection.

    Stateless beyond its :class:`AnomalyConfig`: :meth:`assess` takes the whole
    batch (bursts and coordination are batch properties) and returns one
    :class:`AnomalyVerdict` per signal, in input order.
    """

    def __init__(self, config: AnomalyConfig | None = None) -> None:
        self._config = config or AnomalyConfig()

    def assess(self, signals: Sequence[ContributionSignal]) -> list[AnomalyVerdict]:
        """Classify each signal as accept or route-to-review (SIG-CONTRIB-010/011)."""
        return [self._verdict(signal, signals) for signal in signals]

    def _verdict(
        self, signal: ContributionSignal, batch: Sequence[ContributionSignal]
    ) -> AnomalyVerdict:
        reasons: list[ReviewReason] = []
        if self._is_burst(signal, batch):
            reasons.append(ReviewReason.BURST)
        if self._is_coordinated(signal, batch):
            reasons.append(ReviewReason.COORDINATED_SIMILAR)
        if signal.resolves_contested:
            reasons.append(ReviewReason.CONTESTED_RESOLVING)
        decision = RoutingDecision.ROUTE_TO_REVIEW if reasons else RoutingDecision.ACCEPT
        return AnomalyVerdict(decision=decision, reasons=tuple(reasons))

    def _is_burst(self, signal: ContributionSignal, batch: Sequence[ContributionSignal]) -> bool:
        window = self._config.burst_window
        same_handle = [
            other
            for other in batch
            if other.handle == signal.handle
            and abs(other.submitted_at - signal.submitted_at) <= window
        ]
        return len(same_handle) > self._config.burst_threshold

    def _is_coordinated(
        self, signal: ContributionSignal, batch: Sequence[ContributionSignal]
    ) -> bool:
        window = self._config.coordination_window
        # NOTE: polarity is intentionally NOT part of this predicate — a false-
        # absence campaign is coordinated the same way a false-presence one is
        # (SIG-CONTRIB-011).
        similar = [
            other
            for other in batch
            if other.content_fingerprint == signal.content_fingerprint
            and abs(other.submitted_at - signal.submitted_at) <= window
        ]
        return len(similar) >= self._config.coordination_threshold


# --------------------------------------------------------------------------- #
# Vendor operating-territory check (SIG-CONTRIB-011a)                          #
# --------------------------------------------------------------------------- #
#: The confidence a territory-implausible claim is held at (§10.7 lowest band).
LOWEST_CONFIDENCE = "lowest"
#: The confidence a territory-plausible claim keeps (unchanged by this rule).
NORMAL_CONFIDENCE = "normal"


@dataclass(frozen=True)
class VerificationTask:
    """A task to verify a territory-implausible claim before it can be believed.

    Generated *instead of* letting the claim enter the graph as an observation
    (SIG-CONTRIB-011a). It routes to research, not to auto-rejection.
    """

    task_type: str
    vendor_id: str
    region_id: str
    reason: str


@dataclass(frozen=True)
class TerritoryVerdict:
    """The outcome of the vendor operating-territory plausibility check."""

    plausible: bool
    confidence: str
    enters_graph_as_observation: bool
    verification_task: VerificationTask | None


def check_operating_territory(
    *,
    vendor_id: str,
    region_id: str,
    known_operating_regions: frozenset[str] | set[str] | Sequence[str],
) -> TerritoryVerdict:
    """Plausibility-check that vendor V operating in region C is supported (SIG-CONTRIB-011a).

    If SIG holds independent evidence that V operates in C (``region_id`` is in
    `known_operating_regions`), the claim is plausible and enters normally. If it
    holds no such evidence, the claim is held at the lowest confidence and a
    verification task is generated **instead of** letting it enter the graph as an
    observation — the fabricated-node failure mode is inflationary, so an
    unsupported territory claim is never trusted by default.
    """
    known = set(known_operating_regions)
    if region_id in known:
        return TerritoryVerdict(
            plausible=True,
            confidence=NORMAL_CONFIDENCE,
            enters_graph_as_observation=True,
            verification_task=None,
        )
    return TerritoryVerdict(
        plausible=False,
        confidence=LOWEST_CONFIDENCE,
        enters_graph_as_observation=False,
        verification_task=VerificationTask(
            task_type="verify_vendor_operating_territory",
            vendor_id=vendor_id,
            region_id=region_id,
            reason=(
                f"no independent evidence that vendor {vendor_id!r} operates in region "
                f"{region_id!r}; held at lowest confidence pending verification (SIG-CONTRIB-011a)"
            ),
        ),
    )


# --------------------------------------------------------------------------- #
# Visual weight (SIG-CONTRIB-011c)                                            #
# --------------------------------------------------------------------------- #
class ClaimSource(StrEnum):
    """Where a rendered claim came from, for presentation weighting (§34.4/§10.7)."""

    UNVERIFIED_COMMUNITY = "unverified_community"
    RECORDS_DERIVED = "records_derived"


#: Relative visual prominence by source — higher renders more prominently. An
#: unverified community observation is strictly below a records-derived claim
#: (SIG-CONTRIB-011c); they can never share a weight.
PRESENTATION_WEIGHT: dict[ClaimSource, int] = {
    ClaimSource.UNVERIFIED_COMMUNITY: 1,
    ClaimSource.RECORDS_DERIVED: 3,
}


class VisualWeightViolation(ValueError):
    """Raised when an unverified observation is given records-derived weight (011c)."""


def visual_weight(source: ClaimSource) -> int:
    """The relative visual prominence of a claim from `source` (SIG-CONTRIB-011c)."""
    return PRESENTATION_WEIGHT[source]


def renders_with_same_weight(a: ClaimSource, b: ClaimSource) -> bool:
    """Whether two sources would render with the same visual weight."""
    return visual_weight(a) == visual_weight(b)


def assert_distinct_visual_weight() -> None:
    """Assert unverified community obs never share records-derived weight (011c)."""
    if renders_with_same_weight(ClaimSource.UNVERIFIED_COMMUNITY, ClaimSource.RECORDS_DERIVED):
        raise VisualWeightViolation(
            "an unverified community observation MUST NOT render with the same visual weight "
            "as a records-derived claim (SIG-CONTRIB-011c)"
        )
    unverified = visual_weight(ClaimSource.UNVERIFIED_COMMUNITY)
    records = visual_weight(ClaimSource.RECORDS_DERIVED)
    if unverified >= records:
        raise VisualWeightViolation(
            "an unverified community observation MUST render below a records-derived claim "
            "(SIG-CONTRIB-011c)"
        )


# --------------------------------------------------------------------------- #
# No SIG-caused mass revert (SIG-CONTRIB-011b)                                #
# --------------------------------------------------------------------------- #
class MassRevertRefusedError(RuntimeError):
    """Raised on any attempt to auto-apply reverts — SIG is never the proximate cause."""


@dataclass(frozen=True)
class RevertSuggestion:
    """A human-reviewed suggestion to revert an implausible node — never a write.

    SIG supplies the candidate and its evidence; a human decides and, if they
    agree, applies it in their own account (the suggestion-not-write posture of
    SIG-CONTRIB-015, invoked here for the operational reason of SIG-CONTRIB-011b).
    """

    subject_id: str
    rationale: str
    evidence_ref: str
    applied_by_sig: bool = False

    def __post_init__(self) -> None:
        if self.applied_by_sig:
            raise MassRevertRefusedError(
                "SIG MUST NOT apply a revert itself (SIG-CONTRIB-011b); it may only suggest"
            )


def suggest_reverts_for_review(
    candidates: Sequence[tuple[str, str, str]],
) -> list[RevertSuggestion]:
    """Turn `(subject_id, rationale, evidence_ref)` candidates into review suggestions.

    Produces suggestions only — nothing is applied. This is the sole SIG-side
    output for implausible nodes (SIG-CONTRIB-011b).
    """
    return [
        RevertSuggestion(subject_id=subject_id, rationale=rationale, evidence_ref=evidence_ref)
        for subject_id, rationale, evidence_ref in candidates
    ]


def apply_reverts_automatically(_candidates: Sequence[object]) -> None:
    """Always refuse: SIG never auto-applies a mass revert (SIG-CONTRIB-011b)."""
    raise MassRevertRefusedError(
        "SIG MUST NOT be the proximate cause of a mass revert (SIG-CONTRIB-011b); "
        "route candidates through suggest_reverts_for_review for human application"
    )
