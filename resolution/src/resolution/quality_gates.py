# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ER quality gates (SIG-IDENT-028/029) — the §14.7 gates everything downstream
depends on.

Three families of check, all pure functions over an ER run's predictions and the
gold set (:mod:`resolution.gold_set`):

* **Pairwise precision/recall/F1 at each tier boundary** (:func:`metrics_at_tier_boundaries`).
  A tier boundary is a candidate cut point of the cascade (after the auto-write tiers,
  after tier 4, after tier 5); the metric treats every pair at or above the boundary
  as a predicted match and scores it against the gold labels.
* **B-cubed cluster precision/recall on the holdout** (:func:`bcubed`). Pairwise metrics
  miss cluster-level damage (one bad edge can merge two clusters); B-cubed measures per
  element how pure and complete its predicted cluster is.
* **Auto-write demotion** (:func:`demote_auto_write_tiers`). If a *deterministic*
  auto-write tier's measured holdout precision falls below the published floor, that
  tier is demoted to review — the gate that stops a decaying rule from silently
  writing (SIG-IDENT-028).

plus **cluster-shape alerts** (:func:`cluster_shape_alerts`, SIG-IDENT-029): the
signatures of a bad merge — an oversized law-enforcement cluster, or two substantial
components joined by a single bridge edge.
"""

from __future__ import annotations

import tomllib
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import cache
from importlib.resources import files
from typing import Any

__all__ = [
    "QUALITY_GATES_VERSION",
    "PRF",
    "DemotionDecision",
    "ClusterShapeAlert",
    "ClusterShapeContext",
    "pair_key",
    "pairwise_metrics",
    "metrics_at_tier_boundaries",
    "bcubed",
    "demote_auto_write_tiers",
    "cluster_shape_alerts",
    "AUTO_WRITE_TIERS",
]

AUTO_WRITE_TIERS = (0, 1, 2, 3)

PairKey = tuple[str, str]


@cache
def _rules() -> dict[str, Any]:
    resource = files("resolution").joinpath("data", "quality_gates.toml")
    with resource.open("rb") as fh:
        return tomllib.load(fh)


QUALITY_GATES_VERSION: str = str(_rules()["version"])


def pair_key(a: str, b: str) -> PairKey:
    """A canonical, order-independent key for the pair ``{a, b}``."""
    return (a, b) if a <= b else (b, a)


@dataclass(frozen=True)
class PRF:
    """Precision / recall / F1 with the counts they were computed from."""

    precision: float
    recall: float
    f1: float
    true_positives: int
    predicted_positives: int
    actual_positives: int


def _prf(true_positives: int, predicted_positives: int, actual_positives: int) -> PRF:
    precision = true_positives / predicted_positives if predicted_positives else 0.0
    recall = true_positives / actual_positives if actual_positives else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return PRF(precision, recall, f1, true_positives, predicted_positives, actual_positives)


def pairwise_metrics(
    predicted_positive: Iterable[PairKey],
    gold_positive: Iterable[PairKey],
    gold_negative: Iterable[PairKey],
) -> PRF:
    """Pairwise P/R/F1 of ``predicted_positive`` against the gold labels.

    Only pairs in the gold universe (``gold_positive ∪ gold_negative``) are scored, so
    a prediction on an unlabelled pair neither helps nor hurts — precision and recall
    are measured only where ground truth exists.
    """
    pos = {pair_key(*p) for p in gold_positive}
    neg = {pair_key(*p) for p in gold_negative}
    universe = pos | neg
    predicted = {pair_key(*p) for p in predicted_positive} & universe
    true_positives = len(predicted & pos)
    return _prf(true_positives, len(predicted), len(pos))


def metrics_at_tier_boundaries(
    tier_by_pair: Mapping[PairKey, int],
    gold_positive: Iterable[PairKey],
    gold_negative: Iterable[PairKey],
    *,
    boundaries: Sequence[int] = (3, 4, 5),
) -> dict[int, PRF]:
    """Pairwise metrics at each cascade tier boundary (SIG-IDENT-028).

    At boundary ``b`` every pair assigned a tier ``<= b`` counts as a predicted match.
    Returns boundary tier → :class:`PRF`.
    """
    normalised = {pair_key(*p): t for p, t in tier_by_pair.items()}
    out: dict[int, PRF] = {}
    for boundary in boundaries:
        predicted = [p for p, tier in normalised.items() if tier <= boundary]
        out[boundary] = pairwise_metrics(predicted, gold_positive, gold_negative)
    return out


def bcubed(
    predicted_cluster: Mapping[str, str],
    gold_cluster: Mapping[str, str],
) -> PRF:
    """B-cubed cluster precision/recall/F1 over the elements both mappings share.

    For each element, precision is the fraction of its predicted-cluster co-members
    that share its gold cluster, and recall the fraction of its gold-cluster co-members
    that share its predicted cluster; the reported values are the element averages.
    The counts on the returned :class:`PRF` are the number of shared elements.
    """
    elements = sorted(set(predicted_cluster) & set(gold_cluster))
    if not elements:
        return _prf(0, 0, 0)
    pred_members: dict[str, set[str]] = defaultdict(set)
    gold_members: dict[str, set[str]] = defaultdict(set)
    for element in elements:
        pred_members[predicted_cluster[element]].add(element)
        gold_members[gold_cluster[element]].add(element)

    precision_sum = 0.0
    recall_sum = 0.0
    for element in elements:
        same_pred = pred_members[predicted_cluster[element]] & set(elements)
        same_gold = gold_members[gold_cluster[element]] & set(elements)
        correct = same_pred & same_gold
        precision_sum += len(correct) / len(same_pred)
        recall_sum += len(correct) / len(same_gold)

    n = len(elements)
    precision = precision_sum / n
    recall = recall_sum / n
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return PRF(precision, recall, f1, len(elements), n, n)


@dataclass(frozen=True)
class DemotionDecision:
    """Whether an auto-write tier keeps auto-writing or is demoted to review."""

    tier: int
    precision: float
    threshold: float
    demoted: bool

    @property
    def disposition(self) -> str:
        return "review" if self.demoted else "auto_write"


def demote_auto_write_tiers(
    tier_precisions: Mapping[int, float],
    *,
    threshold: float,
) -> list[DemotionDecision]:
    """Demote each auto-write tier whose holdout precision is below ``threshold``.

    Only the deterministic auto-write tiers (0–3) are demotable — a review tier is
    already at review. A tier absent from ``tier_precisions`` (no holdout evidence) is
    not decided and is omitted (SIG-IDENT-028).
    """
    decisions: list[DemotionDecision] = []
    for tier in AUTO_WRITE_TIERS:
        if tier not in tier_precisions:
            continue
        precision = tier_precisions[tier]
        decisions.append(
            DemotionDecision(
                tier=tier,
                precision=precision,
                threshold=threshold,
                demoted=precision < threshold,
            )
        )
    return decisions


# --- Cluster-shape alerts (SIG-IDENT-029) -------------------------------------


@dataclass(frozen=True)
class ClusterShapeAlert:
    """One implausible-cluster finding: a signature of a bad merge (SIG-IDENT-029)."""

    cluster_id: str
    kind: str  # "oversized_le_cluster" | "single_bridge_join"
    detail: dict[str, Any]


@dataclass(frozen=True)
class ClusterShapeContext:
    """Cluster-shape thresholds (data-driven, injectable for tests)."""

    max_le_cluster_size: int = 6
    substantial_component_size: int = 3
    le_classes: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_data(cls) -> ClusterShapeContext:
        cfg = _rules()["cluster_shape"]
        return cls(
            max_le_cluster_size=int(cfg["max_le_cluster_size"]),
            substantial_component_size=int(cfg["substantial_component_size"]),
            le_classes=frozenset(cfg["le_classes"]),
        )


def _bridges(nodes: set[str], adjacency: Mapping[str, set[str]]) -> list[tuple[str, str]]:
    """Every bridge (cut edge) of the undirected graph, via a Tarjan DFS."""
    disc: dict[str, int] = {}
    low: dict[str, int] = {}
    bridges: list[tuple[str, str]] = []
    timer = [0]

    def dfs(u: str, parent: str | None) -> None:
        disc[u] = low[u] = timer[0]
        timer[0] += 1
        skipped_parent = False
        for v in adjacency[u]:
            if v == parent and not skipped_parent:
                skipped_parent = True  # skip the edge back to parent once
                continue
            if v not in disc:
                dfs(v, u)
                low[u] = min(low[u], low[v])
                if low[v] > disc[u]:
                    bridges.append((u, v))
            else:
                low[u] = min(low[u], disc[v])

    for node in sorted(nodes):
        if node not in disc:
            dfs(node, None)
    return bridges


def _component_sizes_without(
    nodes: set[str], adjacency: Mapping[str, set[str]], drop: tuple[str, str]
) -> list[int]:
    a, b = drop
    seen: set[str] = set()
    sizes: list[int] = []
    for start in sorted(nodes):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        size = 0
        while stack:
            u = stack.pop()
            size += 1
            for v in adjacency[u]:
                if (u, v) == (a, b) or (u, v) == (b, a):
                    continue  # the dropped edge
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        sizes.append(size)
    return sizes


def cluster_shape_alerts(
    cluster_by_element: Mapping[str, str],
    edges: Iterable[tuple[str, str]],
    org_class_by_element: Mapping[str, str] | None = None,
    *,
    context: ClusterShapeContext | None = None,
) -> list[ClusterShapeAlert]:
    """Flag implausible clusters — the bad-merge signatures (SIG-IDENT-029).

    ``cluster_by_element`` maps each element to its predicted cluster id; ``edges`` are
    the predicted within-cluster links; ``org_class_by_element`` supplies the class for
    the oversized-law-enforcement check. Returns one alert per finding.
    """
    ctx = context if context is not None else ClusterShapeContext.from_data()
    classes = org_class_by_element or {}
    members: dict[str, list[str]] = defaultdict(list)
    for element, cluster_id in cluster_by_element.items():
        members[cluster_id].append(element)

    adjacency: dict[str, set[str]] = defaultdict(set)
    cluster_edges: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for a, b in edges:
        cid = cluster_by_element.get(a)
        if cid is None or cid != cluster_by_element.get(b):
            continue
        adjacency[a].add(b)
        adjacency[b].add(a)
        cluster_edges[cid].append((a, b))

    alerts: list[ClusterShapeAlert] = []
    for cluster_id in sorted(members):
        elements = sorted(members[cluster_id])
        size = len(elements)

        # (1) oversized law-enforcement cluster
        if (
            size > ctx.max_le_cluster_size
            and elements
            and all(classes.get(e) in ctx.le_classes for e in elements)
        ):
            alerts.append(
                ClusterShapeAlert(
                    cluster_id=cluster_id,
                    kind="oversized_le_cluster",
                    detail={"size": size, "max": ctx.max_le_cluster_size},
                )
            )

        # (2) single bridge joining two substantial components
        node_set = set(elements)
        local_adjacency = {e: adjacency.get(e, set()) & node_set for e in elements}
        for bridge in _bridges(node_set, local_adjacency):
            sizes = sorted(_component_sizes_without(node_set, local_adjacency, bridge))
            if len(sizes) == 2 and sizes[0] >= ctx.substantial_component_size:
                alerts.append(
                    ClusterShapeAlert(
                        cluster_id=cluster_id,
                        kind="single_bridge_join",
                        detail={
                            "bridge": list(bridge),
                            "component_sizes": sizes,
                            "substantial": ctx.substantial_component_size,
                        },
                    )
                )
    return alerts
