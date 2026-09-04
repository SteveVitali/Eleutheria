# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ER quality gates (SIG-IDENT-028/029): pairwise P/R/F1 at each tier boundary,
B-cubed cluster precision/recall, auto-write demotion on a holdout-precision breach,
and cluster-shape alerts on the signatures of a bad merge."""

from __future__ import annotations

from resolution.quality_gates import (
    AUTO_WRITE_TIERS,
    ClusterShapeContext,
    bcubed,
    cluster_shape_alerts,
    demote_auto_write_tiers,
    metrics_at_tier_boundaries,
    pair_key,
    pairwise_metrics,
)

# --- Pairwise metrics ---------------------------------------------------------


def test_pairwise_metrics_scores_only_the_gold_universe() -> None:
    gold_pos = [("a", "b"), ("c", "d")]
    gold_neg = [("e", "f")]
    predicted = [("a", "b"), ("e", "f"), ("x", "y")]  # 1 TP, 1 FP, 1 unlabelled
    prf = pairwise_metrics(predicted, gold_pos, gold_neg)
    assert prf.true_positives == 1
    assert prf.predicted_positives == 2  # the unlabelled (x,y) is ignored
    assert prf.actual_positives == 2
    assert prf.precision == 0.5
    assert prf.recall == 0.5


def test_pair_key_is_order_independent() -> None:
    assert pair_key("b", "a") == pair_key("a", "b") == ("a", "b")


def test_perfect_prediction_is_p1_r1() -> None:
    prf = pairwise_metrics([("a", "b")], [("a", "b")], [("c", "d")])
    assert prf.precision == 1.0 and prf.recall == 1.0 and prf.f1 == 1.0


# --- Metrics at each tier boundary (SIG-IDENT-028) ----------------------------


def test_metrics_reported_at_each_tier_boundary() -> None:
    # (a,b) auto-written at tier 2; (c,d) proposed at tier 4; (e,f) proposed at tier 5.
    tier_by_pair = {
        pair_key("a", "b"): 2,
        pair_key("c", "d"): 4,
        pair_key("e", "f"): 5,
    }
    gold_pos = [("a", "b"), ("c", "d")]
    gold_neg = [("e", "f")]
    metrics = metrics_at_tier_boundaries(tier_by_pair, gold_pos, gold_neg)
    assert set(metrics) == {3, 4, 5}
    # boundary 3 (auto-write only): predicts just (a,b) → precision 1, recall 1/2
    assert metrics[3].precision == 1.0
    assert metrics[3].recall == 0.5
    # boundary 4: adds (c,d) → recall 2/2, still precise
    assert metrics[4].recall == 1.0
    assert metrics[4].precision == 1.0
    # boundary 5: adds (e,f) which is a gold NON-match → precision drops
    assert metrics[5].precision < 1.0
    assert metrics[5].recall == 1.0


# --- B-cubed cluster metrics --------------------------------------------------


def test_bcubed_perfect_clustering() -> None:
    predicted = {"a": "1", "b": "1", "c": "2"}
    gold = {"a": "x", "b": "x", "c": "y"}
    prf = bcubed(predicted, gold)
    assert prf.precision == 1.0 and prf.recall == 1.0 and prf.f1 == 1.0


def test_bcubed_penalises_a_bad_merge() -> None:
    # predicted merges a,b,c into one cluster; gold keeps c separate → precision drops
    predicted = {"a": "1", "b": "1", "c": "1"}
    gold = {"a": "x", "b": "x", "c": "y"}
    prf = bcubed(predicted, gold)
    assert prf.precision < 1.0
    assert prf.recall == 1.0  # nothing that should be together was split


def test_bcubed_penalises_a_bad_split() -> None:
    predicted = {"a": "1", "b": "2"}
    gold = {"a": "x", "b": "x"}
    prf = bcubed(predicted, gold)
    assert prf.recall < 1.0
    assert prf.precision == 1.0


# --- Auto-write demotion on a precision breach (SIG-IDENT-028) ----------------


def test_auto_write_tier_demoted_when_precision_below_threshold() -> None:
    decisions = demote_auto_write_tiers({0: 1.0, 2: 0.90, 3: 0.995}, threshold=0.97)
    by_tier = {d.tier: d for d in decisions}
    assert by_tier[0].demoted is False and by_tier[0].disposition == "auto_write"
    assert by_tier[2].demoted is True and by_tier[2].disposition == "review"
    assert by_tier[3].demoted is False


def test_only_auto_write_tiers_are_demotable() -> None:
    # tier 4/5 precisions are ignored — a review tier cannot be "demoted to review".
    decisions = demote_auto_write_tiers({4: 0.1, 5: 0.1}, threshold=0.97)
    assert decisions == []
    assert set(AUTO_WRITE_TIERS) == {0, 1, 2, 3}


def test_tier_without_holdout_evidence_is_not_decided() -> None:
    decisions = demote_auto_write_tiers({0: 0.99}, threshold=0.97)
    assert {d.tier for d in decisions} == {0}


# --- Cluster-shape alerts (SIG-IDENT-029) -------------------------------------


def _ctx() -> ClusterShapeContext:
    return ClusterShapeContext(
        max_le_cluster_size=4,
        substantial_component_size=3,
        le_classes=frozenset({"us.le.municipal_police", "us.le.sheriff"}),
    )


def test_oversized_law_enforcement_cluster_is_flagged() -> None:
    # 5 police agencies in one cluster, ceiling 4 → implausible (SIG-IDENT-029).
    cluster = {f"pd{i}": "c1" for i in range(5)}
    classes = {f"pd{i}": "us.le.municipal_police" for i in range(5)}
    edges = [(f"pd{i}", f"pd{i + 1}") for i in range(4)]
    alerts = cluster_shape_alerts(cluster, edges, classes, context=_ctx())
    assert any(a.kind == "oversized_le_cluster" for a in alerts)


def test_non_law_enforcement_cluster_is_not_size_flagged() -> None:
    cluster = {f"v{i}": "c1" for i in range(5)}
    classes = {f"v{i}": "private.company" for i in range(5)}
    edges = [(f"v{i}", f"v{i + 1}") for i in range(4)]
    alerts = cluster_shape_alerts(cluster, edges, classes, context=_ctx())
    assert not any(a.kind == "oversized_le_cluster" for a in alerts)


def test_single_bridge_join_of_substantial_components_is_flagged() -> None:
    # Two triangles (3 nodes each) joined by ONE bridge edge L2—R0: the bad-merge
    # signature (SIG-IDENT-029).
    left = ["L0", "L1", "L2"]
    right = ["R0", "R1", "R2"]
    cluster = {n: "c1" for n in left + right}
    edges = [
        ("L0", "L1"),
        ("L1", "L2"),
        ("L0", "L2"),  # left triangle
        ("R0", "R1"),
        ("R1", "R2"),
        ("R0", "R2"),  # right triangle
        ("L2", "R0"),  # the single bridge
    ]
    alerts = cluster_shape_alerts(cluster, edges, context=_ctx())
    bridge_alerts = [a for a in alerts if a.kind == "single_bridge_join"]
    assert bridge_alerts
    assert sorted(bridge_alerts[0].detail["component_sizes"]) == [3, 3]


def test_densely_connected_cluster_has_no_bridge_alert() -> None:
    # A fully-connected 4-clique has no bridge → no single-bridge alert.
    nodes = ["a", "b", "c", "d"]
    cluster = {n: "c1" for n in nodes}
    edges = [(x, y) for i, x in enumerate(nodes) for y in nodes[i + 1 :]]
    alerts = cluster_shape_alerts(cluster, edges, context=_ctx())
    assert not any(a.kind == "single_bridge_join" for a in alerts)


def test_bridge_to_a_singleton_is_not_substantial() -> None:
    # A triangle with a single pendant node: the bridge splits into 3 and 1; the
    # size-1 side is not substantial, so no alert (that is a normal shape).
    cluster = {n: "c1" for n in ["a", "b", "c", "d"]}
    edges = [("a", "b"), ("b", "c"), ("a", "c"), ("c", "d")]
    alerts = cluster_shape_alerts(cluster, edges, context=_ctx())
    assert not any(a.kind == "single_bridge_join" for a in alerts)


def test_cluster_shape_context_loads_from_data() -> None:
    ctx = ClusterShapeContext.from_data()
    assert ctx.max_le_cluster_size >= 1
    assert ctx.substantial_component_size >= 1
    assert "us.le.sheriff" in ctx.le_classes
