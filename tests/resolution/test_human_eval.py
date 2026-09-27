# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Pure-side tests for the P32.9 human-evaluation protocol (SIG-EVAL-001/002).

Covers the deterministic contract without Postgres: dependency-disjoint
partitions, seeded sample reproducibility, explicit inclusion probabilities,
opaque ids, blinded packets, manifest tamper evidence, the watermark chain,
the consensus/adjudication rules and the honest zero-label campaign state.
The PG/RLS half lives in ``tests/db/test_human_eval.py``.
"""

from __future__ import annotations

import pytest
from resolution.human_eval import (
    FrameItem,
    GroupSpec,
    SampleSpec,
    assert_blinded,
    assign_partitions,
    build_blinded_packet,
    build_dependency_groups,
    campaign_design,
    campaign_state,
    consensus,
    draw_eval_sample,
    homogenize_group_strata,
    label_digest,
    label_watermark,
    manifest_digest,
    packet_digest,
    sample_id_for,
    to_gold_label,
)


def _frame(n: int, **per_i: dict[int, dict[str, object]]) -> list[FrameItem]:
    """A synthetic frame: pair p{i} ~ subject a{i} vs b{i}, in cycling strata."""
    strata = ["t1", "t2", "t3"]
    items = []
    for i in range(n):
        kw = dict(
            pair_id=f"p{i:03d}",
            left_ref=f"e{i * 2}",
            right_ref=f"e{i * 2 + 1}",
            stratum_id=strata[i % 3],
            source_lineage_ids=(f"src-{i % 5}",),
        )
        kw.update(per_i.get(i, {}))
        items.append(FrameItem(**kw))
    return items


# --------------------------------------------------------------------------- #
# Dependency groups — the disjointness contract                                 #
# --------------------------------------------------------------------------- #
def test_pairs_sharing_a_subject_group_together() -> None:
    items = _frame(4)
    # p0 (e0~e1) and p1 (e2~e3) share nothing; force e1 == e2 via a new item.
    items[1] = FrameItem(
        pair_id="p001", left_ref="e1", right_ref="e3", stratum_id="t2",
        source_lineage_ids=("src-1",),
    )
    groups = build_dependency_groups(items)
    same_group = [g for g, ps in groups.items() if {"p000", "p001"} <= set(ps)]
    assert same_group, "pairs sharing subject e1 must be one dependency group"
    # The untouched pairs still group only with themselves.
    assert all("p002" not in groups[same_group[0]] for _ in [0])


def test_shared_lineage_or_family_groups_transitively() -> None:
    items = [
        FrameItem(pair_id="p1", left_ref="a1", right_ref="b1", stratum_id="s",
                  source_lineage_ids=("up-1",)),
        FrameItem(pair_id="p2", left_ref="a2", right_ref="b2", stratum_id="s",
                  source_lineage_ids=("up-1",)),
        FrameItem(pair_id="p3", left_ref="a3", right_ref="b3", stratum_id="s",
                  republisher_family="fam-x"),
        FrameItem(pair_id="p4", left_ref="a4", right_ref="b4", stratum_id="s",
                  republisher_family="fam-x"),
        FrameItem(pair_id="p5", left_ref="a5", right_ref="b5", stratum_id="s",
                  source_lineage_ids=("up-2",), republisher_family="fam-x"),
        FrameItem(pair_id="p6", left_ref="a6", right_ref="b6", stratum_id="s",
                  mirror_group_id="mir-1"),
        FrameItem(pair_id="p7", left_ref="a7", right_ref="b7", stratum_id="s",
                  mirror_group_id="mir-1"),
    ]
    groups = build_dependency_groups(items)
    by_pair = {p: g for g, ps in groups.items() for p in ps}
    assert by_pair["p1"] == by_pair["p2"], "shared upstream lineage must group"
    assert by_pair["p3"] == by_pair["p4"], "same republisher family must group"
    assert by_pair["p3"] == by_pair["p5"], "lineage+family members group too"
    assert by_pair["p6"] == by_pair["p7"], "same mirror group must group"
    assert by_pair["p1"] != by_pair["p6"], "unrelated pairs stay apart"


def test_groups_are_deterministic_for_identical_input() -> None:
    items = _frame(30)
    a = build_dependency_groups(items)
    b = build_dependency_groups(list(reversed(items)))
    assert a == b


# --------------------------------------------------------------------------- #
# Partitions — whole-group, lineage-disjoint, holdout-forced                   #
# --------------------------------------------------------------------------- #
def test_partitions_never_split_a_dependency_group() -> None:
    items = _frame(60)
    # Make p005 mirror p006 — they must share a partition whatever the draw.
    items[6] = FrameItem(
        pair_id="p006", left_ref="e100", right_ref="e101", stratum_id="t1",
        mirror_group_id="shared-copy",
    )
    items[5] = FrameItem(
        pair_id="p005", left_ref="e98", right_ref="e99", stratum_id="t1",
        mirror_group_id="shared-copy",
    )
    items = homogenize_group_strata(items)
    parts = assign_partitions(items, seed="s1", spec=GroupSpec())
    groups = build_dependency_groups(items)
    for gid, pairs in groups.items():
        assert len({parts[p] for p in pairs}) == 1, f"group {gid} crossed partitions"


def test_no_lineage_crosses_the_sealed_boundary() -> None:
    items = _frame(80)
    items = homogenize_group_strata(items)
    parts = assign_partitions(items, seed="s2", spec=GroupSpec())
    by_pair = {i.pair_id: i for i in items}
    sealed = [p for p, v in parts.items() if v == "sealed_final"]
    non_sealed = [p for p, v in parts.items() if v != "sealed_final"]

    def keys(p: str) -> set[str]:
        i = by_pair[p]
        out = {i.left_ref, i.right_ref, i.republisher_family, i.mirror_group_id}
        out |= set(i.source_lineage_ids)
        return {k for k in out if k}

    sealed_keys = set().union(*(keys(p) for p in sealed)) if sealed else set()
    for p in non_sealed:
        assert not (keys(p) & sealed_keys), (
            f"{p} shares entity/lineage/family with a sealed pair"
        )


def test_holdout_families_are_forced_sealed() -> None:
    items = _frame(40)
    items[0] = FrameItem(
        pair_id="p000", left_ref="e0", right_ref="e1", stratum_id="t1",
        republisher_family="fam-held-out",
    )
    spec = GroupSpec(holdout_families=("fam-held-out",))
    parts = assign_partitions(homogenize_group_strata(items), seed="s3", spec=spec)
    assert parts["p000"] == "sealed_final"


def test_partition_assignment_is_seed_deterministic() -> None:
    items = homogenize_group_strata(_frame(50))
    spec = GroupSpec()
    a = assign_partitions(items, seed="abc", spec=spec)
    b = assign_partitions(items, seed="abc", spec=spec)
    c = assign_partitions(items, seed="xyz", spec=spec)
    assert a == b
    assert set(a) == set(c)  # every pair is assigned either way
    assert set(a.values()) <= set(
        ("training", "development", "calibration", "pilot", "sealed_final")
    )


def test_cross_strata_group_raises_without_homogenize() -> None:
    items = [
        FrameItem(pair_id="p1", left_ref="e1", right_ref="e2", stratum_id="t1"),
        FrameItem(pair_id="p2", left_ref="e2", right_ref="e3", stratum_id="t2"),
    ]
    with pytest.raises(ValueError, match="spans strata"):
        assign_partitions(items, seed="s", spec=GroupSpec())
    fixed = homogenize_group_strata(items)
    assert {i.stratum_id for i in fixed} == {"t1"}
    assign_partitions(fixed, seed="s", spec=GroupSpec())  # no raise


# --------------------------------------------------------------------------- #
# The draw — seeded identity, probabilities, denominators, opaque ids          #
# --------------------------------------------------------------------------- #
def _draw(n: int = 60, seed: str = "draw-1"):
    items = homogenize_group_strata(_frame(n))
    parts = assign_partitions(items, seed=seed, spec=GroupSpec())
    spec = SampleSpec(quotas={"training": None, "sealed_final": None})
    return draw_eval_sample(items, parts, campaign_id="camp-1", seed=seed, spec=spec)


def test_seeded_draw_is_identical_on_repeat() -> None:
    rows1, den1 = _draw()
    rows2, den2 = _draw()
    assert rows1 == rows2 and den1 == den2


def test_inclusion_probabilities_and_weights_are_explicit() -> None:
    rows, den = _draw()
    assert rows, "expected a non-empty sample"
    for r in rows:
        cell = den[r["partition"]][r["stratum_id"]]
        assert cell["universe"] >= cell["drawn"] > 0
        assert 0 < r["selection_probability"] <= 1.0
        assert r["weight"] == pytest.approx(
            cell["universe"] / cell["drawn"]
        )
        assert abs(r["selection_probability"] * r["weight"] - 1.0) < 1e-9
    # Census cells (quota None → everything drawn) honestly report p = 1.
    assert any(r["selection_probability"] == 1.0 for r in rows)


def test_draw_orders_are_a_dense_permutation() -> None:
    rows, _ = _draw()
    orders = sorted(r["draw_order"] for r in rows)
    assert orders == list(range(len(rows)))


def test_sample_ids_are_opaque() -> None:
    rows, _ = _draw()
    for r in rows:
        assert r["sample_id"].startswith("hev-")
        for token in (r["stratum_id"], r["partition"], r["pair_id"]):
            assert token not in r["sample_id"]
    assert sample_id_for("camp-1", "p001") == sample_id_for("camp-1", "p001")
    assert sample_id_for("camp-1", "p001") != sample_id_for("camp-2", "p001")


def test_quota_bounded_draw_records_honest_probability() -> None:
    items = homogenize_group_strata(_frame(90))
    parts = assign_partitions(items, seed="q", spec=GroupSpec())
    spec = SampleSpec(quotas={"training": 2})
    rows, den = draw_eval_sample(items, parts, campaign_id="c", seed="q", spec=spec)
    training = [r for r in rows if r["partition"] == "training"]
    assert training, "expected training draws"
    for r in training:
        cell = den["training"][r["stratum_id"]]
        assert cell["drawn"] <= 2
        if cell["universe"] > cell["drawn"]:
            assert r["selection_probability"] < 1.0
            assert r["weight"] > 1.0


# --------------------------------------------------------------------------- #
# Manifest digests — tamper evidence                                           #
# --------------------------------------------------------------------------- #
def _campaign_and_rows():
    items = homogenize_group_strata(_frame(40))
    parts = assign_partitions(items, seed="m", spec=GroupSpec())
    rows, den = draw_eval_sample(
        items, parts, campaign_id="camp-m", seed="m", spec=SampleSpec()
    )
    design = campaign_design(
        purpose="t",
        protocol_digest="pd",
        frame_snapshot="snap-1",
        ruleset_digest="rs-1",
        seed="m",
        group_spec=GroupSpec(),
        sample_spec=SampleSpec(),
        target_population="all pending camera pairs",
        rubric_version="eval-rubric/1",
    )
    campaign = {"campaign_id": "camp-m", "purpose": "t", "design": design}
    return campaign, rows, den


def test_manifest_digest_stable_and_tamper_evident() -> None:
    campaign, rows, _ = _campaign_and_rows()
    d = manifest_digest(campaign, rows)
    assert d == manifest_digest(campaign, rows)
    # Any membership change is detected (pick a value guaranteed different).
    tampered = [dict(r) for r in rows]
    other = "sealed_final" if tampered[0]["partition"] != "sealed_final" else "training"
    tampered[0] = dict(tampered[0], partition=other)
    assert manifest_digest(campaign, tampered) != d
    # Any design change is detected.
    c2 = dict(campaign, design=dict(campaign["design"], seed="other"))
    assert manifest_digest(c2, rows) != d
    # A dropped row changes it too.
    assert manifest_digest(campaign, rows[:-1]) != d


def test_design_carries_the_preregistered_contract() -> None:
    design = campaign_design(
        purpose="p",
        protocol_digest="pd",
        frame_snapshot="snap",
        ruleset_digest="rs",
        seed="s",
        group_spec=GroupSpec(holdout_families=("fam-a",)),
        sample_spec=SampleSpec(quotas={"training": 3}),
        target_population="pop",
        rubric_version="r/1",
    )
    for key in (
        "protocol_digest",
        "frame_snapshot",
        "ruleset_digest",
        "seed",
        "target_population",
        "rubric_version",
        "group_spec",
        "sample_spec",
        "estimands",
        "partitions",
    ):
        assert key in design
    assert design["group_spec"]["holdout_families"] == ["fam-a"]


# --------------------------------------------------------------------------- #
# Blinded packets                                                               #
# --------------------------------------------------------------------------- #
def _dirty_evidence() -> dict:
    return {
        "latitude": 35.47,
        "longitude": -97.51,
        "name": "I-40 @ Western",
        "operator": "ODOT",
        "source_id": "src-okc",
        "tier": 3,
        "score": 0.91,
        "overall_weight": 4.2,
        "model_id": "cam-rules-v2",
        "stratum": "3g",
        "labels": {"r1": "same"},
        "predicted_cluster": "cl-9",
        "distance_m": 12.4,
        "match_evidence": {"rule": "geo_name"},
        "nested": {"confidence": 0.7, "threshold_pass": True, "keep": "x"},
    }


def test_packet_strips_every_model_and_label_field() -> None:
    payload = build_blinded_packet(
        sample_id="hev-x",
        seed="s",
        left_evidence=_dirty_evidence(),
        right_evidence=_dirty_evidence(),
    )
    assert_blinded(payload)
    side = payload["side_a"]
    assert side["latitude"] == 35.47
    assert side["operator"] == "ODOT"
    for forbidden in ("tier", "score", "overall_weight", "model_id", "stratum",
                      "labels", "predicted_cluster", "distance_m", "match_evidence"):
        assert forbidden not in side
    # Nested forbidden keys are gone too.
    assert side["nested"] == {"keep": "x"}


def test_assert_blinded_rejects_leaky_payloads() -> None:
    with pytest.raises(ValueError, match="unblinded"):
        assert_blinded({"side_a": {"match_tier": 3}})
    with pytest.raises(ValueError, match="unblinded"):
        packet_digest({"a": [{"prior_label": "same"}]})


def test_orientation_is_reproducible_and_seed_varied() -> None:
    left = {"name": "left-side", "latitude": 1.0}
    right = {"name": "right-side", "latitude": 2.0}
    p1 = build_blinded_packet(
        sample_id="hev-1", seed="s", left_evidence=left, right_evidence=right
    )
    p2 = build_blinded_packet(
        sample_id="hev-1", seed="s", left_evidence=left, right_evidence=right
    )
    assert p1 == p2  # same seed + sample → same packet (reproducible audit)
    flips = {
        build_blinded_packet(
            sample_id=f"hev-{i}", seed="s", left_evidence=left, right_evidence=right
        )["side_a"]["name"]
        for i in range(10)
    }
    assert flips == {"left-side", "right-side"}, "orientation must vary across samples"


def test_packet_digest_covers_payload() -> None:
    p = build_blinded_packet(
        sample_id="hev-1", seed="s",
        left_evidence={"name": "a"}, right_evidence={"name": "b"},
    )
    assert packet_digest(p).startswith("sha256:")
    changed = dict(p, side_a=dict(p["side_a"], name="a2"))
    assert packet_digest(changed) != packet_digest(p)


# --------------------------------------------------------------------------- #
# Labels, consensus, watermark, campaign state                                  #
# --------------------------------------------------------------------------- #
def _label_row(**kw) -> dict:
    d = dict(
        campaign_id="c",
        sample_id="hev-1",
        reviewer_id="rev-a",
        round="independent_1",
        label="same",
        reason_codes=["geo_exact"],
        evidence_refs=[],
        rubric_version="eval-rubric/1",
        packet_digest="sha256:abc",
    )
    d.update(kw)
    return {"label_digest": label_digest(**d), **d}


def test_label_digest_rejects_unknown_labels() -> None:
    with pytest.raises(ValueError):
        label_digest(
            campaign_id="c", sample_id="s", reviewer_id="r", round="independent_1",
            label="accept",  # the operational vocabulary is not a reference label
            reason_codes=[], evidence_refs=[], rubric_version="r/1",
            packet_digest="p",
        )


def test_watermark_is_chained_and_order_sensitive() -> None:
    a = _label_row(reviewer_id="r1")
    b = _label_row(reviewer_id="r2", label="different")
    w1 = label_watermark([a, b])
    assert w1.startswith("sha256:")
    assert label_watermark([a, b]) == w1
    assert label_watermark([b, a]) != w1
    assert label_watermark([a]) != w1


def test_consensus_rules_preserve_abstention_and_disagreement() -> None:
    assert consensus(["same", "same"]) == "same"
    assert consensus(["different", "different"]) == "different"
    assert consensus(["same", "different"]) == "needs_adjudication"
    # insufficient never produces a reference label — it goes to adjudication.
    assert consensus(["same", "insufficient_evidence"]) == "needs_adjudication"
    assert consensus(["insufficient_evidence", "insufficient_evidence"]) == (
        "needs_adjudication"
    )
    assert consensus(["same"]) == "awaiting_labels"
    assert consensus([]) == "awaiting_labels"


def test_insufficient_can_never_become_a_gold_match() -> None:
    assert to_gold_label("same") == "match"
    assert to_gold_label("different") == "non_match"
    assert to_gold_label("insufficient_evidence") is None
    with pytest.raises(ValueError):
        to_gold_label("accept")


def test_zero_labels_leave_the_campaign_prepared() -> None:
    assert campaign_state(label_count=0) == "prepared"
    assert campaign_state(label_count=3) == "provisional"
    assert campaign_state(label_count=3, released=True) == "unsealed"
    # No combination of engineering artifacts reports a finished human campaign.
    assert campaign_state(label_count=0, adjudication_count=0) == "prepared"
