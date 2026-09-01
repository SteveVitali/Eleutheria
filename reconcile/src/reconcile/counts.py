# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Camera-count reconciliation (§29.1, SIG-RECON-026/027/028/029).

The count predicates are **distinct and never conflated**. The collapse of
`contracted / invoiced / installed / active / mapped / claimed` into a single
"true count" is the error the whole workflow exists to prevent (SIG-RECON-026).

This module gives the P06.1 slice the two operations §29.1 distinguishes:

* :func:`reconcile_counts` — the RIGHT operation: bin claims by their count basis
  and resolve each predicate on its own, then surface the unexplained deltas
  between predicates as research tasks (never as a disagreement to adjudicate).
* :func:`reconcile_as_single_count` — the WRONG operation §29.1 forbids: asked to
  reduce claims spanning more than one count basis to one number, it refuses and
  emits ``PREDICATE_CONFLATION`` instead (Phase-2.3 guard, SIG-RECON-028).

The full reconciliation engine is P08 (ADR-031); this is the minimal slice.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date

from .model import (
    COUNT_BASIS_MISMATCH,
    PREDICATE_CONFLATION,
    VALUE_DISAGREEMENT,
    Contradiction,
    CountClaim,
    CountReconciliation,
    CountResolution,
    Evidence,
    ResearchTask,
    UnresolvedDelta,
    predicate_for_basis,
)
from .weight import (
    DirectnessExcluded,
    currency,
    directness_for,
    predicate_meta,
    weight_class,
)

DETECTOR_VERSION = "p06.1-slice/1"

#: Ordered pairs of (higher-in-the-pipeline, lower) count bases whose gaps are the
#: genuine findings of §29.1 (the deltas become research tasks, not verdicts).
_DELTA_PAIRS: tuple[tuple[str, str], ...] = (
    ("contracted", "active"),
    ("active", "mapped"),
)


def _task_id() -> str:
    return f"task:{uuid.uuid4()}"


def claim_weight(claim: CountClaim, *, as_of: date) -> int | None:
    """The composed weight ``W`` for a count claim, or ``None`` if excluded (D6)."""
    meta = predicate_meta(claim.predicate_id)
    c = currency(
        volatility_class=meta["volatility_class"],
        half_life=meta["half_life"],
        observed_at=claim.observed_at,
        as_of=as_of,
    )
    try:
        d = directness_for(claim.predicate_id, claim.genre)
    except KeyError:
        return None
    try:
        return weight_class(
            reliability=claim.reliability,
            directness=d,
            integrity=claim.integrity,
            currency=c,
            structured_exact=claim.structured_exact,
            field_verified=claim.field_verified,
        )
    except DirectnessExcluded:
        return None


def _resolve_one_basis(
    subject_id: str,
    basis: str,
    claims: Sequence[CountClaim],
    *,
    as_of: date,
) -> CountResolution:
    """Resolve a single count predicate from claims that all share its basis."""
    predicate_id = predicate_for_basis(basis)
    strategy = predicate_meta(predicate_id)["resolution_strategy"]
    lower_bound = basis == "mapped"  # SIG-RECON-027: mapped is a lower bound only

    weighted = [(c, claim_weight(c, as_of=as_of)) for c in claims]
    admissible = [(c, w) for c, w in weighted if w is not None and w > 0]

    if not admissible:
        return CountResolution(
            count_basis=basis,
            predicate_id=predicate_id,
            value=None,
            weight=None,
            winning_claim=None,
            dissenting=tuple(c for c, _ in weighted),
            lower_bound=lower_bound,
            rationale=f"No admissible evidence for {predicate_id}.",
            resolution_status="INSUFFICIENT",
        )

    winner, wins = _pick_winner(admissible, strategy=strategy, lower_bound=lower_bound)
    dissenting = tuple(c for c, _ in admissible if c is not winner)

    contradictions: list[Contradiction] = []
    tasks: list[ResearchTask] = []
    # A genuine within-predicate disagreement: two admissible claims on the SAME
    # basis with different values (mapped is exempt — a higher figure is a better
    # lower bound, not a disagreement). The disagreement emits a research task and
    # links it (SIG-RECON-057): the detector never states a conflict without work.
    distinct_values = {c.value for c, _ in admissible}
    if len(distinct_values) > 1 and not lower_bound:
        sorted_values = tuple(sorted(distinct_values))
        task = ResearchTask(
            task_id=_task_id(),
            task_type="reconcile_disagreeing_count",
            subject_id=subject_id,
            closing_condition=(
                f"Obtain a dispositive source reconciling {predicate_id} values {sorted_values}."
            ),
            detector_version=DETECTOR_VERSION,
            priority=0.6,
            note=f"{predicate_id} carries disagreeing claims {sorted_values}.",
        )
        tasks.append(task)
        contradictions.append(
            Contradiction(
                contradiction_type=VALUE_DISAGREEMENT,
                subject_id=subject_id,
                predicate_id=predicate_id,
                claim_values=sorted_values,
                note=(
                    f"{predicate_id} carries disagreeing claims "
                    f"({', '.join(str(v) for v in sorted_values)}); "
                    "both retained, neither collapsed."
                ),
                evidence=tuple(c.evidence for c, _ in admissible),
                research_task_ids=(task.task_id,),
            )
        )

    return CountResolution(
        count_basis=basis,
        predicate_id=predicate_id,
        value=winner.value,
        weight=wins,
        winning_claim=winner,
        dissenting=dissenting,
        lower_bound=lower_bound,
        rationale=_rationale(basis, winner, wins, lower_bound),
        resolution_status="RESOLVED",
        contradictions=tuple(contradictions),
        tasks=tuple(tasks),
    )


def _pick_winner(
    admissible: list[tuple[CountClaim, int]],
    *,
    strategy: str,
    lower_bound: bool,
) -> tuple[CountClaim, int]:
    """Choose the resolving claim by weight, breaking ties by the registry strategy."""
    top_w = max(w for _, w in admissible)
    contenders = [(c, w) for c, w in admissible if w == top_w]
    if len(contenders) == 1:
        return contenders[0]
    if lower_bound or strategy == "max_support":
        # A lower bound resolves to the highest supported observation.
        return max(contenders, key=lambda cw: cw[0].value)
    if strategy == "latest_observation_wins":
        return max(contenders, key=lambda cw: cw[0].observed_at)
    # authoritative_source_wins / default: the strongest, then the most recent.
    return max(contenders, key=lambda cw: (cw[1], cw[0].observed_at))


def _rationale(basis: str, winner: CountClaim, weight: int, lower_bound: bool) -> str:
    src = winner.evidence.source_family
    when = winner.observed_at.isoformat()
    if lower_bound:
        return (
            f"{winner.value} devices independently mapped ({src}, {when}); "
            "a LOWER BOUND on the physical population, never an estimate of the true count."
        )
    return (
        f"{winner.value} {basis} devices, from {src} ({when}); "
        f"the most direct available evidence for the {basis} count (W{weight})."
    )


def reconcile_counts(
    subject_id: str,
    claims: Sequence[CountClaim],
    *,
    as_of: date,
) -> CountReconciliation:
    """Resolve every count predicate on its own and surface the deltas (§29.1).

    The output carries every count predicate with its own resolution, the
    unresolved deltas with their interpretation, and the generated research tasks
    (SIG-RECON-029). It does NOT emit a single true count.
    """
    by_basis: dict[str, list[CountClaim]] = {}
    for c in claims:
        by_basis.setdefault(c.count_basis, []).append(c)

    resolutions: dict[str, CountResolution] = {}
    contradictions: list[Contradiction] = []
    tasks: list[ResearchTask] = []
    for basis, group in by_basis.items():
        res = _resolve_one_basis(subject_id, basis, group, as_of=as_of)
        resolutions[basis] = res
        contradictions.extend(res.contradictions)
        # Each within-predicate disagreement already carries its linked research
        # task (the detector→task contract, SIG-RECON-057).
        tasks.extend(res.tasks)

    deltas = _compute_deltas(subject_id, resolutions)
    tasks.extend(d.task for d in deltas)

    return CountReconciliation(
        subject_id=subject_id,
        resolutions=resolutions,
        unresolved_deltas=deltas,
        contradictions=tuple(contradictions),
        tasks=tuple(tasks),
    )


def _compute_deltas(
    subject_id: str,
    resolutions: dict[str, CountResolution],
) -> tuple[UnresolvedDelta, ...]:
    """The deltas between resolved predicates — the genuine findings (§29.1)."""
    out: list[UnresolvedDelta] = []
    for higher, lower in _DELTA_PAIRS:
        hi = resolutions.get(higher)
        lo = resolutions.get(lower)
        if not (hi and lo and hi.value is not None and lo.value is not None):
            continue
        delta = hi.value - lo.value
        if delta == 0:
            continue
        interp, closing = _delta_interpretation(higher, lower, hi.value, lo.value, delta)
        task = ResearchTask(
            task_id=_task_id(),
            task_type=f"count_delta_{higher}_vs_{lower}",
            subject_id=subject_id,
            closing_condition=closing,
            detector_version=DETECTOR_VERSION,
            priority=0.55,
            note=interp,
        )
        out.append(
            UnresolvedDelta(
                higher_basis=higher,
                lower_basis=lower,
                delta=delta,
                interpretation=interp,
                task=task,
            )
        )
    return tuple(out)


def _delta_interpretation(higher: str, lower: str, hv: int, lv: int, delta: int) -> tuple[str, str]:
    if (higher, lower) == ("contracted", "active") and delta > 0:
        return (
            f"{delta} devices contracted ({hv}) but not confirmed active ({lv}) — "
            "were they never installed, or removed?",
            f"Determine the disposition of the {delta} contracted-not-active devices.",
        )
    if (higher, lower) == ("active", "mapped"):
        if delta > 0:
            return (
                f"at least {delta} active devices ({hv}) are not yet mapped ({lv}) — "
                "mapping is a lower bound; locate and map them.",
                f"Locate and map at least {delta} additional devices.",
            )
        return (
            f"mapped ({lv}) exceeds the city's active count ({hv}) by {-delta} — "
            "the surplus is devices with a non-city or unknown operator (§29.2 attribution gap).",
            f"Attribute operators for the {-delta} mapped devices beyond the city's fleet.",
        )
    return (
        f"unexplained delta of {delta} between {higher} ({hv}) and {lower} ({lv}).",
        f"Explain the {delta}-device gap between {higher} and {lower}.",
    )


def reconcile_as_single_count(
    subject_id: str,
    claims: Sequence[CountClaim],
) -> Contradiction | None:
    """The operation §29.1 FORBIDS: reduce a set of count claims to one number.

    Phase-2.3 guard (SIG-RECON-028): if the claims span more than one count basis,
    refuse to compare them and emit ``PREDICATE_CONFLATION`` instead of a verdict.
    Returns the contradiction when conflation is detected, else ``None`` (the
    claims share a basis and could legitimately be resolved together).
    """
    bases = sorted({c.count_basis for c in claims})
    if len(bases) <= 1:
        return None
    predicate_ids = sorted({c.predicate_id for c in claims})
    return Contradiction(
        contradiction_type=PREDICATE_CONFLATION,
        subject_id=subject_id,
        predicate_id=predicate_ids[0],
        claim_values=tuple(c.value for c in claims),
        note=(
            "Refused to compare counts across distinct bases "
            f"({', '.join(bases)}): these are answers to different questions "
            "(§29.1 SIG-RECON-026/028). The mismatched claims are dropped, not adjudicated."
        ),
        severity="blocking",
        evidence=tuple(c.evidence for c in claims),
    )


def count_basis_mismatch(
    subject_id: str, predicate_id: str, claims: Sequence[CountClaim]
) -> Contradiction:
    """A helper contradiction for the deliberate-conflation demonstration."""
    return Contradiction(
        contradiction_type=COUNT_BASIS_MISMATCH,
        subject_id=subject_id,
        predicate_id=predicate_id,
        claim_values=tuple(c.value for c in claims),
        note="Claims tagged to one predicate but carrying different count bases.",
        evidence=tuple(c.evidence for c in claims),
    )


__all__ = [
    "DETECTOR_VERSION",
    "Evidence",
    "claim_weight",
    "count_basis_mismatch",
    "reconcile_as_single_count",
    "reconcile_counts",
]
