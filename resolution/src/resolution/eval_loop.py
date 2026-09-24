# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The resolution eval loop (P28.1, ADR-099, design §2.4/§2.5) — SIG measuring its
own method.

This module composes the built-but-dormant eval machinery
(:mod:`resolution.gold_set`, :mod:`resolution.quality_gates`,
:mod:`resolution.adjudicator`) into one measured pass over an ER run and renders the
eval report the operator reads at the P28.5 pause:

* **Calibrate** the LLM adjudicator against the maintainer seed — Cohen's κ
  (:meth:`resolution.gold_set.GoldSet.kappa`). LLM gold is trusted only when
  ``κ ≥ kappa_bar`` (default ``0.7``); otherwise the LLM is a suggester and its pairs
  route to review.
* **Measure** pairwise P/R/F1 at the tier boundaries + B-cubed on the frozen holdout +
  per-auto-write-tier precision, and **demote** any auto-write tier whose measured
  holdout precision falls below the published floor (``auto_write_precision_threshold``,
  default ``0.98``) — a decaying rule can never silently keep writing.
* **Surface** cluster-shape alerts (the bad-merge signatures) and route disputed pairs
  + model↔LLM disagreements + near-boundary pairs to the review queue (active learning).

Every threshold is read from versioned data (``splink_model.toml`` /
``gold_set_rules.toml``), never hard-coded, and is **provisional** by construction
(``D-R6.1-EVAL``).
"""

from __future__ import annotations

import tomllib
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from typing import Any

from .adjudicator import CandidatePair
from .gold_set import GoldLabel, GoldSet
from .quality_gates import (
    AUTO_WRITE_TIERS,
    PRF,
    ClusterShapeAlert,
    DemotionDecision,
    bcubed,
    demote_auto_write_tiers,
    metrics_at_tier_boundaries,
    pair_key,
    pairwise_metrics,
)

__all__ = [
    "DEFAULT_KAPPA_BAR",
    "EvalReport",
    "read_auto_write_threshold",
    "read_kappa_bar",
    "tier_precisions_on_holdout",
    "active_learning_pair_ids",
    "run_eval",
    "render_report_md",
]

DEFAULT_KAPPA_BAR = 0.7


@cache
def _splink_thresholds() -> dict[str, Any]:
    resource = files("resolution").joinpath("data", "splink_model.toml")
    with resource.open("rb") as fh:
        return dict(tomllib.load(fh).get("thresholds", {}))


@cache
def _gold_rules() -> dict[str, Any]:
    resource = files("resolution").joinpath("data", "gold_set_rules.toml")
    with resource.open("rb") as fh:
        return dict(tomllib.load(fh))


def read_auto_write_threshold() -> float:
    """The published auto-write holdout-precision floor (``splink_model.toml``).

    This is the reader ``demote_auto_write_tiers`` needs; the threshold lives with the
    model so gate and model version together (SIG-IDENT-028).
    """
    return float(_splink_thresholds()["auto_write_precision_threshold"])


def read_kappa_bar() -> float:
    """The published LLM-vs-seed agreement bar (``gold_set_rules.toml``)."""
    return float(_gold_rules().get("kappa_bar", DEFAULT_KAPPA_BAR))


@dataclass(frozen=True)
class EvalReport:
    """The committed eval report: everything the operator reads at the P28.5 pause."""

    gold_set_version: str
    seed_adjudicator: str
    llm_adjudicator: str
    kappa: float
    kappa_bar: float
    llm_trusted: bool
    auto_write_threshold: float
    holdout_size: int
    labelled_size: int
    tier_metrics: dict[int, PRF]
    holdout_bcubed: PRF | None
    tier_precisions: dict[int, float]
    demotions: tuple[DemotionDecision, ...]
    cluster_alerts: tuple[ClusterShapeAlert, ...]
    disputed_pair_ids: tuple[str, ...]
    active_learning_pair_ids: tuple[str, ...]
    review_routed: int
    dedup_ratio: float | None = None
    resolved_site_count: int | None = None
    observation_count: int | None = None
    resolutions_materialized: int | None = None
    #: P30.2a (ADR-104): observation-level sites whose coordinates carry a §28 VALUE
    #: decision within their own record — NOT deduplication; and the entity-level merges
    #: (the cross-source dedup that P30.2b measures). ``None`` = not measured.
    value_resolved_site_count: int | None = None
    entity_merges: int | None = None
    provisional: bool = True
    notes: tuple[str, ...] = ()

    @property
    def demoted_tiers(self) -> tuple[int, ...]:
        return tuple(d.tier for d in self.demotions if d.demoted)

    @property
    def any_demoted(self) -> bool:
        return bool(self.demoted_tiers)


def _key_of(pair: CandidatePair) -> tuple[str, str]:
    return pair_key(pair.left.entity_id, pair.right.entity_id)


def _gold_partitions(
    gold_set: GoldSet,
    pairs_by_id: Mapping[str, CandidatePair],
    *,
    holdout_only: bool,
) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    """Return (gold_positive_keys, gold_negative_keys) over labelled, non-disputed pairs."""
    positive: set[tuple[str, str]] = set()
    negative: set[tuple[str, str]] = set()
    for gp in gold_set.pairs:
        if holdout_only and not gp.frozen:
            continue
        if gp.label is None or gp.pair_id not in pairs_by_id:
            continue
        key = _key_of(pairs_by_id[gp.pair_id])
        if gp.label == GoldLabel.MATCH:
            positive.add(key)
        elif gp.label == GoldLabel.NON_MATCH:
            negative.add(key)
    return positive, negative


def tier_precisions_on_holdout(
    gold_set: GoldSet,
    pairs_by_id: Mapping[str, CandidatePair],
    tier_by_pair_id: Mapping[str, int],
) -> dict[int, float]:
    """Per-auto-write-tier pairwise precision on the frozen holdout (SIG-IDENT-028).

    For each auto-write tier, precision = (holdout pairs assigned that tier that are gold
    ``match``) / (holdout pairs assigned that tier that carry a match/non_match label).
    A tier with no holdout evidence is omitted, so it is not decided (never demoted on
    silence).
    """
    positive, negative = _gold_partitions(gold_set, pairs_by_id, holdout_only=True)
    universe = positive | negative
    predicted_at: dict[int, list[tuple[str, str]]] = defaultdict(list)
    for pair_id, tier in tier_by_pair_id.items():
        if tier in AUTO_WRITE_TIERS and pair_id in pairs_by_id:
            key = _key_of(pairs_by_id[pair_id])
            if key in universe:
                predicted_at[tier].append(key)
    out: dict[int, float] = {}
    for tier, keys in predicted_at.items():
        prf = pairwise_metrics(keys, positive, negative)
        out[tier] = prf.precision
    return out


def active_learning_pair_ids(
    pairs: Sequence[CandidatePair],
    tier_by_pair_id: Mapping[str, int],
    llm_label_by_pair_id: Mapping[str, GoldLabel],
    *,
    boundary_low: float,
    boundary_high: float,
) -> tuple[str, ...]:
    """Pairs worth a human label first (design §2.4): maximise information per label.

    Selects (a) **model↔LLM disagreements** — the model predicts a match tier (≤5) but
    the LLM says ``non_match``, or the model discards (tier 6 / absent) but the LLM says
    ``match`` — and (b) **near-boundary** pairs whose match weight sits in
    ``[boundary_low, boundary_high]`` around the review cutoff.
    """
    selected: set[str] = set()
    for p in pairs:
        tier = tier_by_pair_id.get(p.pair_id)
        llm = llm_label_by_pair_id.get(p.pair_id)
        model_says_match = tier is not None and tier <= 5
        if llm is not None:
            if model_says_match and llm == GoldLabel.NON_MATCH:
                selected.add(p.pair_id)
            if not model_says_match and llm == GoldLabel.MATCH:
                selected.add(p.pair_id)
        if boundary_low <= p.weight <= boundary_high:
            selected.add(p.pair_id)
    return tuple(sorted(selected))


def run_eval(
    *,
    gold_set: GoldSet,
    pairs: Sequence[CandidatePair],
    tier_by_pair_id: Mapping[str, int],
    llm_label_by_pair_id: Mapping[str, GoldLabel],
    seed_adjudicator: str,
    llm_adjudicator: str,
    predicted_clusters: Mapping[str, str] | None = None,
    gold_clusters: Mapping[str, str] | None = None,
    cluster_alerts: Sequence[ClusterShapeAlert] = (),
    auto_write_threshold: float | None = None,
    kappa_bar: float | None = None,
    dedup_ratio: float | None = None,
    resolved_site_count: int | None = None,
    observation_count: int | None = None,
    resolutions_materialized: int | None = None,
    value_resolved_site_count: int | None = None,
    entity_merges: int | None = None,
    provisional: bool = True,
    notes: Sequence[str] = (),
) -> EvalReport:
    """Run the measured eval pass and assemble the :class:`EvalReport` (design §2.4)."""
    threshold = (
        auto_write_threshold if auto_write_threshold is not None else read_auto_write_threshold()
    )
    bar = kappa_bar if kappa_bar is not None else read_kappa_bar()

    kappa = gold_set.kappa(seed_adjudicator, llm_adjudicator)
    llm_trusted = kappa >= bar

    pairs_by_id = {p.pair_id: p for p in pairs}

    # Tier-boundary metrics on the frozen holdout (the honest eval set).
    pos_holdout, neg_holdout = _gold_partitions(gold_set, pairs_by_id, holdout_only=True)
    tier_by_key: dict[tuple[str, str], int] = {}
    for pair_id, tier in tier_by_pair_id.items():
        if pair_id in pairs_by_id:
            tier_by_key[_key_of(pairs_by_id[pair_id])] = tier
    tier_metrics = metrics_at_tier_boundaries(tier_by_key, pos_holdout, neg_holdout)

    tier_prec = tier_precisions_on_holdout(gold_set, pairs_by_id, tier_by_pair_id)
    demotions = tuple(demote_auto_write_tiers(tier_prec, threshold=threshold))

    holdout_bcubed = None
    if predicted_clusters is not None and gold_clusters is not None:
        holdout_bcubed = bcubed(predicted_clusters, gold_clusters)

    thresholds = _splink_thresholds()
    boundary_low = float(thresholds.get("tier5_weak", -3.0))
    boundary_high = float(thresholds.get("tier4_review", 3.5))
    active = active_learning_pair_ids(
        pairs,
        tier_by_pair_id,
        llm_label_by_pair_id,
        boundary_low=boundary_low,
        boundary_high=boundary_high,
    )

    disputed = tuple(sorted(gp.pair_id for gp in gold_set.pairs if gp.disputed))
    # Everything that goes to review: tier 4/5 proposals + disputed + active-learning +
    # (if the LLM is not trusted) all LLM-suggested pairs.
    review: set[str] = set(disputed) | set(active)
    for pair_id, tier in tier_by_pair_id.items():
        if tier in (4, 5):
            review.add(pair_id)
    if not llm_trusted:
        review |= set(llm_label_by_pair_id)

    extra_notes = list(notes)
    if not llm_trusted:
        extra_notes.append(
            f"LLM κ={kappa:.3f} below bar {bar:.2f}: LLM is a SUGGESTER, "
            "all its pairs route to review."
        )
    if any(d.demoted for d in demotions):
        demoted = ", ".join(str(d.tier) for d in demotions if d.demoted)
        extra_notes.append(
            f"auto-write tier(s) {demoted} DEMOTED to review (holdout precision < floor)."
        )

    return EvalReport(
        gold_set_version=gold_set.version,
        seed_adjudicator=seed_adjudicator,
        llm_adjudicator=llm_adjudicator,
        kappa=kappa,
        kappa_bar=bar,
        llm_trusted=llm_trusted,
        auto_write_threshold=threshold,
        holdout_size=len(gold_set.holdout()),
        labelled_size=len(gold_set.labelled()),
        tier_metrics=tier_metrics,
        holdout_bcubed=holdout_bcubed,
        tier_precisions=tier_prec,
        demotions=demotions,
        cluster_alerts=tuple(cluster_alerts),
        disputed_pair_ids=disputed,
        active_learning_pair_ids=active,
        review_routed=len(review),
        dedup_ratio=dedup_ratio,
        resolved_site_count=resolved_site_count,
        observation_count=observation_count,
        resolutions_materialized=resolutions_materialized,
        value_resolved_site_count=value_resolved_site_count,
        entity_merges=entity_merges,
        provisional=provisional,
        notes=tuple(extra_notes),
    )


def _fmt_prf(prf: PRF | None) -> str:
    if prf is None:
        return "n/a"
    counts = f"(tp={prf.true_positives}, pp={prf.predicted_positives}, ap={prf.actual_positives})"
    return f"P={prf.precision:.3f} R={prf.recall:.3f} F1={prf.f1:.3f} {counts}"


def _na(value: object, *, fmt: str = "") -> str:
    if value is None:
        return "n/a"
    return format(value, fmt) if fmt else str(value)


def render_report_md(report: EvalReport, *, title: str = "Resolution eval report") -> str:
    """Render the eval report as Markdown (committed to build memory + the coverage page)."""
    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    if report.provisional:
        lines.append(
            "> **PROVISIONAL** — the gold set is LLM-bootstrapped with a small maintainer seed "
            "and the auto-write floor is set against provisional labels (D-R6.1-EVAL, OPEN). "
            'A launch claim of "resolved sites" discloses this until the deferral closes.'
        )
        lines.append("")
    lines.append("## Calibration (LLM adjudicator vs maintainer seed)")
    lines.append("")
    lines.append(f"- gold set version: `{report.gold_set_version}`")
    lines.append(f"- seed adjudicator: `{report.seed_adjudicator}`")
    lines.append(f"- LLM adjudicator: `{report.llm_adjudicator}`")
    lines.append(
        f"- Cohen's κ (LLM vs seed): **{report.kappa:.3f}** (bar ≥ {report.kappa_bar:.2f})"
    )
    lines.append(
        f"- LLM trusted as gold: **{'yes' if report.llm_trusted else 'no — suggester only'}**"
    )
    lines.append(f"- labelled pairs: {report.labelled_size}; frozen holdout: {report.holdout_size}")
    lines.append(f"- disputed (adjudicators disagree) → review: {len(report.disputed_pair_ids)}")
    lines.append("")
    lines.append("## Quality gates (frozen holdout)")
    lines.append("")
    lines.append(f"- auto-write precision floor: **{report.auto_write_threshold:.3f}**")
    for boundary in sorted(report.tier_metrics):
        lines.append(f"- pairwise @ tier ≤ {boundary}: {_fmt_prf(report.tier_metrics[boundary])}")
    lines.append(f"- B-cubed cluster (holdout): {_fmt_prf(report.holdout_bcubed)}")
    if report.tier_precisions:
        for tier in sorted(report.tier_precisions):
            lines.append(
                f"- auto-write tier {tier} holdout precision: {report.tier_precisions[tier]:.3f}"
            )
    lines.append("")
    lines.append("### Auto-write demotion")
    lines.append("")
    if report.demotions:
        for d in sorted(report.demotions, key=lambda x: x.tier):
            verdict = "DEMOTED → review" if d.demoted else "keeps auto-writing"
            lines.append(
                f"- tier {d.tier}: precision {d.precision:.3f} "
                f"vs floor {d.threshold:.3f} → {verdict}"
            )
    else:
        lines.append("- (no auto-write tier had holdout evidence this pass)")
    lines.append("")
    lines.append("### Cluster-shape alerts (bad-merge signatures)")
    lines.append("")
    if report.cluster_alerts:
        for a in report.cluster_alerts:
            lines.append(f"- `{a.kind}` on cluster `{a.cluster_id}`: {a.detail}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Review routing (active learning)")
    lines.append("")
    lines.append(f"- pairs routed to review: **{report.review_routed}**")
    n_active = len(report.active_learning_pair_ids)
    lines.append(f"- active-learning-selected (disagreement + near-boundary): {n_active}")
    lines.append("")
    lines.append("## Scale (materialization over the spine)")
    lines.append("")
    lines.append(f"- observations considered: {_na(report.observation_count)}")
    lines.append(f"- resolved sites / decisions: {_na(report.resolved_site_count)}")
    lines.append(f"- resolution envelopes materialized: {_na(report.resolutions_materialized)}")
    if report.value_resolved_site_count is not None:
        lines.append(
            "- sites whose coordinates carry a §28 value decision (within each source's own "
            f"record — NOT deduplication): {report.value_resolved_site_count}"
        )
    if report.entity_merges is not None:
        lines.append(f"- entity-level merges (cross-source dedup): {report.entity_merges}")
    lines.append(f"- dedup ratio: {_na(report.dedup_ratio, fmt='.3f')}")
    lines.append("")
    if report.notes:
        lines.append("## Notes")
        lines.append("")
        for n in report.notes:
            lines.append(f"- {n}")
        lines.append("")
    return "\n".join(lines)
