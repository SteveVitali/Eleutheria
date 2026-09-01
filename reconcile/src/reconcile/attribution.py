# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Device attribution (§29.2, SIG-RECON-030/031/032/033).

The workflow that addresses the ~116,800 mapped ALPRs with no operator (SC-08.1):
given an orphan device and the deployments that might operate it, produce an **L4
`probable` inference** — never an observation, never written to ``operator`` as
though observed, never auto-pushed to OSM (SIG-RECON-031). Candidate generation
weighs the six signals of SIG-RECON-030; the hard cases of SIG-RECON-032 are
**modelled, not defaulted** — where attribution is ambiguous by construction the
workflow *enqueues a research task* rather than picking. Promotion from
``probable`` to asserted requires human confirmation or a ``D1``/``D2`` source
(SIG-RECON-033); a high score never promotes itself.

This module produces the device-attribution inference only; the full L4 inference
layer / access-path closure and its UI labelling are P12.x (§30).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from .model import Inference, ResearchTask

DERIVATION_RULE = "device_attribution/§29.2"
RULE_VERSION = "p08.2/1"

#: Road-network contexts that make containment ambiguous by construction
#: (a device on a county/state road inside a city is not the city's by default).
_CROSS_JURISDICTION_ROADS = frozenset({"county_road", "state_road"})

#: The directness codes that alone can promote an attribution to asserted
#: without a human in the loop (SIG-RECON-033).
_DOCUMENTARY_DIRECTNESS = frozenset({"D1", "D2"})


@dataclass(frozen=True)
class OrphanDevice:
    """A mapped device with no attributed operator (the input to §29.2)."""

    subject_id: str
    technology: str
    #: On a jurisdiction boundary — ambiguous by construction (SIG-RECON-032).
    on_jurisdiction_boundary: bool = False
    inside_jurisdiction_id: str | None = None


@dataclass(frozen=True)
class CandidateOperator:
    """One deployment that might operate the orphan, with its six signals (§29.2).

    The signals are the SIG-RECON-030 candidate-generation inputs. ``role`` is the
    role being attributed (§12.4): attribution names the *role*, it does not assert
    generic ownership. ``on_behalf_of`` records the second party where A operates
    on behalf of B — both roles are kept, never collapsed.
    """

    org_id: str
    role: str = "operator"
    #: Signal 1 — spatial containment in this candidate's jurisdiction.
    contained_in_jurisdiction: bool = False
    #: Signal 2 — distance (m) to this candidate's nearest matching-tech deployment.
    distance_m: float | None = None
    #: Signal 3 — road-network context of the orphan relative to this candidate.
    road_context: str = "unknown"
    #: Signal 4 — this candidate's jurisdiction is adjacent to the orphan's.
    adjacent_jurisdiction: bool = False
    #: Signal 5 — manufacturer/vendor match against the deployment's product.
    vendor_match: bool = False
    #: Signal 6 — unexplained unmapped-device gap at this candidate's deployment.
    unmapped_gap: int = 0
    #: A operates on behalf of B (§12.4): the principal party, if any.
    on_behalf_of: str | None = None
    #: This deployment is a shared multi-agency deployment (multiple operators is
    #: a valid answer, not a conflict — SIG-RECON-032).
    shared: bool = False
    claim_id: str = ""

    #: Distance (m) at or under which proximity counts as a supporting signal.
    proximity_threshold_m: float = 500.0

    def crosses_jurisdiction_road(self) -> bool:
        return self.road_context in _CROSS_JURISDICTION_ROADS

    def score(self) -> int:
        """A deterministic, corroboration-weighted score (no random tie-break).

        Containment is intentionally cheap — *containment is not attribution*
        (SIG-RECON-032): a candidate whose only signal is that it contains the
        device scores 0 on the corroborating axes and cannot carry a `probable`
        inference on its own.
        """
        return self.corroborating_score() + (1 if self.contained_in_jurisdiction else 0)

    def corroborating_score(self) -> int:
        """The signal strength that is *not* mere containment."""
        s = 0
        if self.vendor_match:
            s += 3
        if self.distance_m is not None and self.distance_m <= self.proximity_threshold_m:
            s += 2
        if self.unmapped_gap > 0:
            s += 1
        if self.adjacent_jurisdiction:
            s += 1
        return s


@dataclass(frozen=True)
class AttributionResult:
    """The §29.2 output: either a `probable` L4 inference, or an enqueued task.

    Exactly one of :attr:`inference` / :attr:`task` drives the outcome, but the
    full candidate set is always retained so an ambiguous case stays visibly
    ambiguous (nothing is silently defaulted away).
    """

    subject_id: str
    candidates: tuple[CandidateOperator, ...]
    inference: Inference | None
    task: ResearchTask | None
    hard_case: str | None
    note: str


def _task_id() -> str:
    return f"task:{uuid.uuid4()}"


def _enqueue(
    orphan: OrphanDevice,
    candidates: Sequence[CandidateOperator],
    *,
    hard_case: str,
    note: str,
) -> AttributionResult:
    """Enqueue an attribution research task rather than pick (SIG-RECON-032)."""
    task = ResearchTask(
        task_id=_task_id(),
        task_type="attribute_orphan_device",
        subject_id=orphan.subject_id,
        closing_condition=(
            f"Attribute the operator of {orphan.subject_id} among candidates "
            f"[{', '.join(c.org_id for c in candidates)}] with a D1/D2 source or human review."
        ),
        detector_version=RULE_VERSION,
        jurisdiction_id=orphan.inside_jurisdiction_id,
        priority=0.6,
        note=note,
    )
    return AttributionResult(
        subject_id=orphan.subject_id,
        candidates=tuple(candidates),
        inference=None,
        task=task,
        hard_case=hard_case,
        note=note,
    )


def _infer(
    orphan: OrphanDevice,
    winner: CandidateOperator,
    candidates: Sequence[CandidateOperator],
    *,
    value: object,
    hard_case: str | None,
    note: str,
) -> AttributionResult:
    inf = Inference(
        subject_id=orphan.subject_id,
        predicate_id=f"attributed_{winner.role}",
        value=value,
        derivation_rule=DERIVATION_RULE,
        rule_version=RULE_VERSION,
        input_claim_ids=tuple(c.claim_id for c in candidates if c.claim_id),
        confidence="probable",
        rationale=note,
        alternatives=tuple(c.org_id for c in candidates if c is not winner),
    )
    return AttributionResult(
        subject_id=orphan.subject_id,
        candidates=tuple(candidates),
        inference=inf,
        task=None,
        hard_case=hard_case,
        note=note,
    )


def attribute_operator(
    orphan: OrphanDevice,
    candidates: Sequence[CandidateOperator],
) -> AttributionResult:
    """Attribute an orphan device's operator, or enqueue when ambiguous (§29.2).

    The output is an L4 ``probable`` inference (SIG-RECON-031) only when one
    candidate is corroborated by a non-containment signal and strictly dominates;
    otherwise the hard cases of SIG-RECON-032 are modelled by enqueuing a research
    task rather than defaulting to the containing jurisdiction.
    """
    if not candidates:
        return _enqueue(
            orphan, candidates, hard_case="no_candidate", note="No candidate operator generated."
        )

    # A device on a jurisdiction boundary is ambiguous by construction.
    if orphan.on_jurisdiction_boundary:
        return _enqueue(
            orphan,
            candidates,
            hard_case="jurisdiction_boundary",
            note=(
                "Device on a jurisdiction boundary: ambiguous by construction — "
                "enqueued rather than attributed (SIG-RECON-032)."
            ),
        )

    # Multi-agency shared deployment: multiple operators is a valid answer.
    shared = [c for c in candidates if c.shared]
    if shared:
        value = tuple(c.org_id for c in shared)
        return _infer(
            orphan,
            shared[0],
            candidates,
            value=value,
            hard_case="multi_agency_shared",
            note=(
                "Shared multi-agency deployment: multiple operators recorded as a "
                "valid answer, not a conflict (SIG-RECON-032)."
            ),
        )

    # A device on a county/state road inside a city has >1 plausible operator;
    # do NOT default to the containing jurisdiction.
    if any(c.crosses_jurisdiction_road() for c in candidates) and len(candidates) > 1:
        return _enqueue(
            orphan,
            candidates,
            hard_case="cross_jurisdiction_road",
            note=(
                "Device on a county/state road inside city limits: multiple candidate "
                "operators; not defaulted to the containing jurisdiction (SIG-RECON-032)."
            ),
        )

    ranked = sorted(
        candidates, key=lambda c: (c.corroborating_score(), c.score(), c.org_id), reverse=True
    )
    top = ranked[0]
    runner = ranked[1] if len(ranked) > 1 else None

    # Containment is not attribution: a winner needs a non-containment signal.
    if top.corroborating_score() == 0:
        return _enqueue(
            orphan,
            candidates,
            hard_case="containment_only",
            note=(
                "Only spatial containment supports any candidate; containment is not "
                "attribution (SIG-RECON-032) — enqueued."
            ),
        )

    # An indecisive lead (a tie on the corroborating signal) stays ambiguous.
    if runner is not None and runner.corroborating_score() == top.corroborating_score():
        return _enqueue(
            orphan,
            candidates,
            hard_case="tie",
            note="Two candidates are equally corroborated; enqueued rather than picked.",
        )

    principal = f" on behalf of {top.on_behalf_of}" if top.on_behalf_of else ""
    note = (
        f"Attributed {top.role} of {orphan.subject_id} to {top.org_id}{principal} "
        f"(probable, L4): corroborating signal {top.corroborating_score()} vs "
        f"{runner.corroborating_score() if runner else 0}. Not an observation; "
        "promotion needs human review or a D1/D2 source (SIG-RECON-031/033)."
    )
    return _infer(orphan, top, candidates, value=top.org_id, hard_case=None, note=note)


class PromotionRefused(RuntimeError):
    """Raised when an attribution inference is promoted without authority (SIG-RECON-033)."""


def promote(
    inference: Inference,
    *,
    confirmed_by: str | None = None,
    source_directness: str | None = None,
) -> Inference:
    """Promote a ``probable`` attribution to asserted (SIG-RECON-033).

    A high inference score MUST NOT promote itself: promotion requires either a
    named human confirmer or a ``D1``/``D2`` documentary source. Returns a new,
    asserted inference (the input is never mutated); raises otherwise.
    """
    if confirmed_by:
        rationale = f"{inference.rationale} Promoted to asserted by {confirmed_by} (SIG-RECON-033)."
    elif source_directness in _DOCUMENTARY_DIRECTNESS:
        rationale = (
            f"{inference.rationale} Promoted to asserted on a {source_directness} "
            "documentary source (SIG-RECON-033)."
        )
    else:
        raise PromotionRefused(
            "attribution promotion requires human confirmation or a D1/D2 source; "
            "a high inference score does not promote itself (SIG-RECON-033)"
        )
    from dataclasses import replace

    return replace(inference, confidence="asserted", rationale=rationale)


__all__ = [
    "DERIVATION_RULE",
    "RULE_VERSION",
    "AttributionResult",
    "CandidateOperator",
    "OrphanDevice",
    "PromotionRefused",
    "attribute_operator",
    "promote",
]
