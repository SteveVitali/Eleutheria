# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Geospatial camera-site entity resolution (P30.2b, ADR-105).

Pins the contract's hard constraints — (a) never merge two records of the same source
(pairwise AND transitively), (b) no merge across the recorded device-class conflicts and
no auto-write through a soft conflict, (c) a mirror of the same upstream is not
independent corroboration — plus the unit/metric (N <= M), the tiering, the measured
auto-write gate (silence never auto-writes; strict precision), cluster-shape alerts for
chaining, and the joint-coordinate rule (never lat from one record and lon from another).
"""

from __future__ import annotations

import json
import math
from dataclasses import replace
from datetime import date
from importlib.resources import files

import pytest
from resolution.blocking import (
    BlockingContext,
    BlockingRuleRejected,
    GeoGridRule,
    geo_grid_pairs,
    load_geo_rules,
    validate_geo_rule,
)
from resolution.camera_sites import (
    CameraGoldPair,
    CameraGoldSet,
    CameraRecord,
    CameraSiteRules,
    HumanItem,
    HumanVote,
    PairAssessment,
    TierMeasurement,
    assess_pairs,
    cluster_decisions,
    cluster_summary,
    decide_auto_write_tiers,
    device_class,
    direction_bearing,
    fold_human_verdicts,
    infer_duplicate_targets,
    infer_lineages,
    load_camera_gold,
    measure_tiers,
    names_agree,
    normalize_ref,
    representative_point,
    resolve_camera_sites,
    run_key,
    site_alerts,
)
from resolution.gold_set import Adjudication, GoldLabel

RULES = CameraSiteRules.from_data()
DATED = date(2026, 9, 24)
LAT0, LON0 = 35.4676, -97.5164
M_PER_DEG_LAT = 111_195.0


def _at(north_m: float = 0.0, east_m: float = 0.0) -> tuple[float, float]:
    lat = LAT0 + north_m / M_PER_DEG_LAT
    lon = LON0 + east_m / (M_PER_DEG_LAT * math.cos(math.radians(LAT0)))
    return lat, lon


def _rec(sid: str, source: str, north_m: float = 0.0, east_m: float = 0.0, **kw) -> CameraRecord:
    lat, lon = _at(north_m, east_m)
    return CameraRecord(subject_id=sid, source_id=source, latitude=lat, longitude=lon, **kw)


def _by_key(assessments):
    return {(p.left, p.right): p for p in assessments}


# --- blocking -----------------------------------------------------------------------


def test_committed_geo_rule_covers_the_candidate_radius() -> None:
    (rule,) = load_geo_rules()
    assert rule.covers_radius_m >= RULES.candidate_max_m
    # the cell is at least the radius in both axes up to the declared latitude bound
    assert rule.cell_lat_deg * 110_574 >= rule.covers_radius_m
    lon_m = rule.cell_lon_deg * 111_320 * math.cos(math.radians(rule.max_abs_latitude))
    assert lon_m >= rule.covers_radius_m


def test_an_undersized_cell_is_refused() -> None:
    with pytest.raises(BlockingRuleRejected, match="does not cover"):
        GeoGridRule(rule_id="tiny", cell_lat_deg=0.0001, cell_lon_deg=0.0001)


def test_geo_blocking_proposes_neighbours_from_other_sources_only() -> None:
    (rule,) = load_geo_rules()
    recs = [
        _rec("a", "s1").block_record(),
        _rec("b", "s1", 3).block_record(),  # same source: never a candidate
        _rec("c", "s2", 40).block_record(),  # other source, neighbouring cell
        _rec("d", "s2", 2000).block_record(),  # far away: not blocked with a
    ]
    pairs = geo_grid_pairs(recs, rule)
    assert (0, 1) not in pairs
    assert (0, 2) in pairs and (1, 2) in pairs
    assert all(3 not in p for p in pairs)


def test_unblockable_points_are_never_candidates() -> None:
    (rule,) = load_geo_rules()
    null_island = {"latitude": 0.0, "longitude": 0.0, "source_id": "s1"}
    polar = {"latitude": 80.0, "longitude": 10.0, "source_id": "s1"}
    missing = {"latitude": None, "longitude": 10.0, "source_id": "s1"}
    for rec in (null_island, polar, missing):
        assert rule.cell(rec) is None


def test_geo_blocking_is_sized_against_the_ceiling() -> None:
    (rule,) = load_geo_rules()
    recs = [_rec(f"x{i}", f"s{i}", i * 0.1).block_record() for i in range(10)]
    assert len(validate_geo_rule(recs, rule)) == 45
    with pytest.raises(BlockingRuleRejected, match="ceiling"):
        validate_geo_rule(recs, rule, context=BlockingContext(comparison_ceiling=10))


# --- hard constraint (a): never merge two records of the same source ----------------


def test_same_source_records_at_one_point_are_never_a_candidate() -> None:
    # One source listing two cameras at one spot lists two devices.
    recs = [_rec("a", "osm"), _rec("b", "osm", 0.2)]
    assert assess_pairs(recs) == ()
    result = resolve_camera_sites(recs, gold=None, threshold=0.98)
    assert result.cluster_count == result.observation_count == 2


def _pa(left: str, right: str, tier: int, d: float = 0.5) -> PairAssessment:
    return PairAssessment(
        left=left,
        right=right,
        tier=tier,
        tier_label=RULES.label(tier),
        distance_m=d,
        soft_conflicts=(),
        evidence={"distance_m": d},
        evidence_claims=(),
    )


def test_same_source_is_never_merged_transitively_through_a_cluster() -> None:
    # a(s1) ~ b(s2) and b(s2) ~ c(s1) would put two s1 records into one site.
    recs = [_rec("a", "s1"), _rec("b", "s2", 0.3), _rec("c", "s1", 0.6)]
    decisions, clusters, _ = cluster_decisions(
        [_pa("a", "b", 3, 0.3), _pa("b", "c", 3, 0.3)], recs, auto_write_tiers={3}, rules=RULES
    )
    by = {(d.left, d.right): d for d in decisions}
    assert [d.disposition for d in decisions].count("auto_write") == 1
    refused = [d for d in by.values() if d.disposition == "proposed"]
    assert refused and refused[0].reason == "cluster_constraint:same_source"
    assert clusters["a"] != clusters["c"]


# --- hard constraint (b): recorded device-class conflicts + soft conflicts -----------


def test_incompatible_device_classes_are_never_candidates() -> None:
    alpr = _rec("a", "camreg_lpd_flock", operator="ArcGIS community-published ALPR camera")
    traffic = _rec("b", "dot_511_ok", 0.2, operator="Oklahoma Department of Transportation")
    assert assess_pairs([alpr, traffic]) == ()
    result = resolve_camera_sites([alpr, traffic], gold=None, threshold=0.98)
    assert result.incompatible_blocked == 1
    assert result.decisions == ()


@pytest.mark.parametrize(
    ("left_kw", "right_kw", "conflict"),
    [
        ({"jurisdiction": "WA"}, {"jurisdiction": "OR"}, "jurisdiction"),
        ({"camera_type": "dome"}, {"camera_type": "fixed"}, "camera_type"),
        ({"direction": "S"}, {"direction": "49"}, "direction"),
    ],
)
def test_a_soft_conflict_can_never_auto_write(left_kw, right_kw, conflict) -> None:
    recs = [_rec("a", "s1", **left_kw), _rec("b", "s2", 0.3, **right_kw)]
    (p,) = assess_pairs(recs)
    assert p.tier == 3 and conflict in p.soft_conflicts
    decisions, clusters, _ = cluster_decisions([p], recs, auto_write_tiers={1, 3}, rules=RULES)
    assert decisions[0].disposition == "proposed"
    assert decisions[0].reason == f"soft_conflict:{conflict}"
    assert clusters["a"] != clusters["b"]


def test_unresolved_jurisdiction_and_both_way_direction_are_not_conflicts() -> None:
    recs = [
        _rec("a", "s1", jurisdiction="unresolved", direction="B"),
        _rec("b", "s2", 0.3, jurisdiction="MD", direction="North"),
    ]
    (p,) = assess_pairs(recs)
    assert p.soft_conflicts == ()


# --- hard constraint (c): a mirror is not independent corroboration -----------------


def test_mirror_lineage_is_inferred_and_counts_once() -> None:
    upstream = [_rec(f"u{i}", "dot_511_md", i * 200.0) for i in range(25)]
    mirror = [_rec(f"m{i}", "camreg_md_mirror", i * 200.0) for i in range(25)]
    independent = [_rec("osm1", "camreg_osm_surveillance", 0.4)]
    recs = upstream + mirror + independent
    coincident = [(i, 25 + i) for i in range(25)]
    lineages = infer_lineages(recs, coincident, RULES)
    assert lineages["dot_511_md"] == lineages["camreg_md_mirror"]
    assert lineages["camreg_osm_surveillance"] == "camreg_osm_surveillance"
    mirror_site = cluster_summary([upstream[0], mirror[0]], lineages)
    assert mirror_site["sources"] == ["camreg_md_mirror", "dot_511_md"]
    assert mirror_site["independent_lineages"] == 1
    assert mirror_site["corroborated"] is False
    corroborated = cluster_summary([upstream[0], independent[0]], lineages)
    assert corroborated["independent_lineages"] == 2 and corroborated["corroborated"] is True


def test_a_few_coincidences_do_not_make_a_lineage() -> None:
    recs = [_rec("a", "s1"), _rec("b", "s2", 0.1)]
    lineages = infer_lineages(recs, [(0, 1)], RULES)
    assert lineages["s1"] != lineages["s2"]


# --- tiers --------------------------------------------------------------------------


def test_tiers_shared_ref_coincident_proximate_and_discard() -> None:
    recs = [
        _rec("a1", "s1", external_ref="51"),
        _rec("a2", "s2", 3, external_ref="51.0"),  # shared upstream id, one-to-one within 5 m
        _rec("b1", "s1", 1000),
        _rec("b2", "s2", 1000.4),  # coincident, one-to-one
        _rec("c1", "s1", 2000),
        _rec("c2", "s2", 2012),  # 12 m, mutual nearest, unique
        _rec("d1", "s1", 3000),
        _rec("d2", "s2", 3045),  # 45 m, no ref: mutual nearest -> tier 5 (review)
        _rec("e1", "s1", 4000),
        _rec("e2", "s3", 4400),  # 400 m apart: not a candidate
    ]
    got = {k: p.tier for k, p in _by_key(assess_pairs(recs)).items()}
    assert got == {("a1", "a2"): 1, ("b1", "b2"): 3, ("c1", "c2"): 4, ("d1", "d2"): 5}


def test_a_distant_shared_ref_needs_agreeing_descriptions() -> None:
    # 30 m apart with a shared row number: not one-to-one within 5 m, so only an agreeing
    # site description makes it the deterministic tier.
    unnamed = [_rec("f1", "s1", external_ref="9"), _rec("f2", "s2", 30, external_ref="9")]
    assert {p.tier for p in assess_pairs(unnamed)} == {5}
    named = [
        _rec("g1", "s1", external_ref="9", name="I-84 at 28th"),
        _rec("g2", "s2", 30, external_ref="9", name="I-84 AT 28TH"),
    ]
    assert {p.tier for p in assess_pairs(named)} == {1}


def test_colocated_devices_are_never_coincident_tier() -> None:
    # s2 lists TWO devices at the point (a pole with two cameras): which one is s1's?
    recs = [_rec("a", "s1"), _rec("b", "s2", 0.2), _rec("c", "s2", 0.4)]
    tiers = {k: p.tier for k, p in _by_key(assess_pairs(recs)).items()}
    assert tiers[("a", "b")] == 5 and tiers[("a", "c")] == 5


def test_shared_ref_needs_mutual_nearest_and_disambiguation_when_colocated() -> None:
    # s1 lists three devices at one point; s2's row shares a number with one of them.
    base = [_rec("x", "s1", external_ref="273", name="SH20B Puhinui Rd West")]
    others = [_rec("y", "s1", 0.1, external_ref="274"), _rec("z", "s1", 0.2, external_ref="275")]
    mirror = _rec("w", "s2", 0.05, external_ref="273", name="SH20B Waokauri Creek")
    tiers = {k: p.tier for k, p in _by_key(assess_pairs([*base, *others, mirror])).items()}
    assert tiers[("w", "x")] != 1  # names disagree and the point is ambiguous
    agreeing = replace(mirror, name="SH20B Puhinui Rd West")
    tiers2 = {k: p.tier for k, p in _by_key(assess_pairs([*base, *others, agreeing])).items()}
    assert tiers2[("w", "x")] == 1


def test_primitive_features() -> None:
    assert normalize_ref(" 51.0 ") == "51" and normalize_ref("") is None
    assert normalize_ref("LADOTD--76.C3") == "ladotd--76.c3"
    assert direction_bearing("Southbound") == 180.0 and direction_bearing("49") == 49.0
    assert direction_bearing("B") is None and direction_bearing("East-West") is None
    assert names_agree("I-95 AT MD 216", "i 95 at md216")
    assert not names_agree("SH2 Petone", "Petone") and not names_agree(None, "x")


# --- the measured auto-write gate ---------------------------------------------------


def _gold(labels: dict[tuple[str, str], GoldLabel], *, frozen: bool = True) -> CameraGoldSet:
    pairs = []
    for i, ((left, right), label) in enumerate(sorted(labels.items())):
        adjs = (
            Adjudication(f"p{i}", "agent:seed", label, DATED, "2"),
            Adjudication(f"p{i}", "llm:x", GoldLabel.NOT_ENOUGH_INFORMATION, DATED, "2"),
        )
        pairs.append(
            CameraGoldPair(f"p{i}", left, right, "s", -0.3, "coincident", {}, adjs, frozen)
        )
    return CameraGoldSet("t", "2", "agent:seed", "llm:x", tuple(pairs))


def test_silence_never_auto_writes() -> None:
    auto, demotions = decide_auto_write_tiers({}, candidate_tiers={1, 3}, threshold=0.98)
    assert auto == frozenset()
    assert all(d.demoted for d in demotions)


def test_too_small_a_holdout_never_auto_writes() -> None:
    # 1 of 1 "= 1.000" is not evidence: the committed rules need 50 holdout pairs per tier.
    assert RULES.min_holdout_pairs == 50
    one = TierMeasurement(tier=3, predicted=1, match=1, non_match=0, not_enough_information=0)
    auto, (d,) = decide_auto_write_tiers(
        {3: one}, candidate_tiers={3}, threshold=0.98, min_pairs=RULES.min_holdout_pairs
    )
    assert auto == frozenset() and d.demoted
    enough = TierMeasurement(tier=3, predicted=50, match=50, non_match=0, not_enough_information=0)
    auto2, _ = decide_auto_write_tiers(
        {3: enough}, candidate_tiers={3}, threshold=0.98, min_pairs=RULES.min_holdout_pairs
    )
    assert auto2 == {3}


def test_strict_precision_counts_unverifiable_merges_against_the_tier() -> None:
    m = TierMeasurement(tier=3, predicted=50, match=49, non_match=0, not_enough_information=1)
    assert m.precision_strict == pytest.approx(0.98)
    assert m.precision_decided == 1.0
    auto, _ = decide_auto_write_tiers({3: m}, candidate_tiers={3}, threshold=0.98)
    assert auto == {3}
    worse = replace(m, match=48, not_enough_information=2)
    auto2, _ = decide_auto_write_tiers({3: worse}, candidate_tiers={3}, threshold=0.98)
    assert auto2 == frozenset()


def test_the_holdout_label_is_the_verifiers_even_when_disputed() -> None:
    gold = _gold({("a", "b"): GoldLabel.NON_MATCH})
    assert gold.disputed() == ("p0",)
    measured = measure_tiers(gold, {("b", "a"): 3})  # order-free key
    assert measured[3].non_match == 1 and measured[3].precision_strict == 0.0


def test_training_pairs_never_score_a_tier() -> None:
    gold = _gold({("a", "b"): GoldLabel.MATCH}, frozen=False)
    assert measure_tiers(gold, {("a", "b"): 3}) == {}


ONE_PAIR = replace(RULES, min_holdout_pairs=1)  # fixture golds hold a single holdout pair


def test_a_tier_auto_writes_only_when_its_measured_holdout_clears_the_floor() -> None:
    recs = [_rec("a", "s1"), _rec("b", "s2", 0.3), _rec("c", "s1", 500), _rec("d", "s2", 500.2)]
    good = _gold({("a", "b"): GoldLabel.MATCH})
    r = resolve_camera_sites(recs, gold=good, threshold=0.98, rules=ONE_PAIR)
    assert r.auto_write_tiers == {3}
    assert r.observation_count == 4 and r.cluster_count == 2
    assert r.dedup_ratio == pytest.approx(0.5)
    bad = _gold({("a", "b"): GoldLabel.NOT_ENOUGH_INFORMATION})
    r2 = resolve_camera_sites(recs, gold=bad, threshold=0.98, rules=ONE_PAIR)
    assert r2.auto_write_tiers == frozenset()
    assert r2.cluster_count == r2.observation_count == 4  # an honest N = M
    assert {d.disposition for d in r2.decisions} == {"proposed"}


def test_run_key_is_stable_for_unchanged_input_and_moves_with_every_decision_input() -> None:
    recs = [_rec("a", "s1"), _rec("b", "s2", 0.3)]
    gold = _gold({("a", "b"): GoldLabel.MATCH})

    def key(records=recs, rules=RULES, tiers=(3,), g=gold):
        return run_key(rules=rules, auto_write_tiers=tiers, gold=g, records=records)

    k1 = key()
    assert k1 == key(records=list(reversed(recs)))  # order-free
    # a change to ANY field a decision can depend on mints a new run (never a stale union)
    for changed in (
        replace(recs[1], claim_ids=("c-new",)),
        replace(recs[1], direction="S"),
        replace(recs[1], jurisdiction="OR"),
        replace(recs[1], name="x"),
        replace(recs[1], operator="ALPR layer"),
        replace(recs[1], source_id="s3"),
    ):
        assert key(records=[recs[0], changed]) != k1
    assert key(tiers=()) != k1
    assert key(rules=replace(RULES, near_max_m=20.0)) != k1
    assert key(g=_gold({("a", "b"): GoldLabel.NON_MATCH})) != k1


def test_a_direction_change_moves_the_run_and_its_decision() -> None:
    # The reviewer's reproduction: the same pair flips from auto_write to a soft conflict,
    # and it must be a NEW run (the old run's auto_write edge can never be unioned in).
    recs = [_rec("a", "s1", direction="N"), _rec("b", "s2", 0.3, direction="N")]
    gold = _gold({("a", "b"): GoldLabel.MATCH})
    r1 = resolve_camera_sites(recs, gold=gold, threshold=0.98, rules=ONE_PAIR)
    flipped = [recs[0], replace(recs[1], direction="S")]
    r2 = resolve_camera_sites(flipped, gold=gold, threshold=0.98, rules=ONE_PAIR)
    assert r1.decisions[0].disposition == "auto_write"
    # the flipped pair can no longer auto-write (a soft conflict; and with its gold pair now
    # soft-conflicted, tier 3 has no scorable evidence either — silence never auto-writes)
    assert r2.decisions[0].disposition == "proposed"
    assert "direction" in r2.decisions[0].assessment.soft_conflicts
    assert r1.run_key != r2.run_key
    assert (r1.cluster_count, r2.cluster_count) == (1, 2)


# --- cluster-shape alerts: chaining along a road -------------------------------------


def test_a_chain_strung_along_a_road_is_refused_and_alerted() -> None:
    # Five records 20 m apart along a road, each hop a plausible same-device edge.
    recs = [_rec(f"r{i}", f"s{i}", i * 20.0) for i in range(5)]
    chain = [_pa(f"r{i}", f"r{i + 1}", 3, 20.0) for i in range(4)]
    decisions, clusters, _ = cluster_decisions(chain, recs, auto_write_tiers={3}, rules=RULES)
    # the span constraint stops the chain growing past one device's footprint
    assert any(d.reason == "cluster_constraint:max_span" for d in decisions)
    members: dict[str, list[str]] = {}
    for sid, cid in clusters.items():
        members.setdefault(cid, []).append(sid)
    assert max(len(m) for m in members.values()) <= 3
    # and the alert fires on a chain that would be published unconstrained
    by_id = {r.subject_id: r for r in recs}
    whole = {r.subject_id: "r0" for r in recs}
    edges = [(p.left, p.right) for p in chain]
    kinds = {a.kind for a in site_alerts(whole, edges, by_id, RULES)}
    assert "elongated_cluster" in kinds


def test_an_alerted_cluster_is_demoted_to_review() -> None:
    loose = replace(RULES, max_span_m=10_000.0, max_size=100)
    recs = [_rec(f"r{i}", f"s{i}", i * 30.0) for i in range(4)]
    chain = [_pa(f"r{i}", f"r{i + 1}", 3, 30.0) for i in range(3)]
    strict = replace(loose, max_span_m=50.0)
    # clustering under the loose constraint, alerting under the strict one
    decisions, clusters, alerts = cluster_decisions(
        chain, recs, auto_write_tiers={3}, rules=replace(strict, max_span_m=10_000.0)
    )
    assert all(d.disposition == "auto_write" for d in decisions)
    by_id = {r.subject_id: r for r in recs}
    edges = [(d.left, d.right) for d in decisions]
    assert any(a.kind == "elongated_cluster" for a in site_alerts(clusters, edges, by_id, strict))


def test_a_single_bridge_join_is_demoted_inside_clustering() -> None:
    # Two 3-record trees (all six sources distinct, all within a few metres) joined by ONE
    # edge: the classic bad-merge shape. The clustering must demote EVERY edge of that
    # cluster to review and return its members to singletons.
    recs = [_rec(k, f"s-{k}", i * 1.5) for i, k in enumerate("abcdef")]
    edges = [
        _pa("a", "b", 3, 1.5),
        _pa("a", "c", 3, 3.0),
        _pa("d", "e", 3, 1.5),
        _pa("d", "f", 3, 3.0),
        _pa("a", "d", 3, 4.5),  # the bridge
    ]
    decisions, clusters, alerts = cluster_decisions(edges, recs, auto_write_tiers={3}, rules=RULES)
    assert any(a.kind == "single_bridge_join" for a in alerts)
    assert {d.disposition for d in decisions} == {"proposed"}
    assert {d.reason for d in decisions} == {"cluster_shape_alert"}
    assert len(set(clusters.values())) == 6


def test_the_run_summary_splits_corroborated_from_one_lineage_sites() -> None:
    # 25 upstream/mirror copies (one lineage) + one independent source coincident with one.
    upstream = [_rec(f"u{i:02d}", "dot_511_md", i * 200.0) for i in range(25)]
    mirror = [_rec(f"m{i:02d}", "camreg_md_mirror", i * 200.0 + 0.2) for i in range(25)]
    osm = [_rec("zz-osm", "camreg_osm_surveillance", 4000.0 + 0.3)]  # near u20 / m20
    gold = _gold({("m00", "u00"): GoldLabel.MATCH})
    r = resolve_camera_sites(upstream + mirror + osm, gold=gold, threshold=0.98, rules=ONE_PAIR)
    summary = r.summary()
    assert summary["multi_record_sites_one_lineage_only"] >= 1  # mirror pairs: one observation
    assert r.lineages["dot_511_md"] == r.lineages["camreg_md_mirror"]
    assert summary["multi_record_sites_independently_corroborated"] + summary[
        "multi_record_sites_one_lineage_only"
    ] == sum(1 for c in set(r.clusters.values()) if list(r.clusters.values()).count(c) >= 2)


def test_an_explicit_plate_reader_type_classes_the_record_as_alpr() -> None:
    osm_alpr = _rec("a", "camreg_osm_surveillance", camera_type="ALPR", operator="OpenStreetMap")
    traffic = _rec("b", "dot_511_ok", 0.2, operator="Oklahoma Department of Transportation")
    assert device_class(osm_alpr, RULES) == "alpr"
    assert assess_pairs([osm_alpr, traffic]) == ()


def test_an_exact_distance_tie_is_not_a_nearest_neighbour() -> None:
    # s2 lists two records at the SAME distance from a: neither is a's nearest.
    recs = [_rec("a", "s1"), _rec("b", "s2", 10), _rec("c", "s2", -10)]
    tiers = {k: p.tier for k, p in _by_key(assess_pairs(recs)).items()}
    assert tiers[("a", "b")] == 5 and tiers[("a", "c")] == 5  # never 4g on a tie


def test_same_source_cluster_alert() -> None:
    recs = [_rec("a", "s1"), _rec("b", "s1", 1)]
    by_id = {r.subject_id: r for r in recs}
    kinds = {a.kind for a in site_alerts({"a": "a", "b": "a"}, [("a", "b")], by_id, RULES)}
    assert "same_source_cluster" in kinds


# --- coordinates are never mixed ----------------------------------------------------


def test_a_resolved_site_point_takes_both_axes_from_one_record() -> None:
    a = CameraRecord("b-subject", "s1", 35.0000, -97.0000)
    b = CameraRecord("a-subject", "s2", 35.0003, -97.0004)
    subject, lat, lon = representative_point([a, b])  # type: ignore[misc]
    rep = {r.subject_id: r for r in (a, b)}[subject]
    assert (lat, lon) == (rep.latitude, rep.longitude)  # never lat of one, lon of another
    assert lat not in ((a.latitude + b.latitude) / 2,)  # never an average
    assert representative_point([CameraRecord("x", "s", None, None)]) is None


# --- the committed gold set ---------------------------------------------------------


def test_the_committed_gold_set_is_double_adjudicated_and_coordinate_free() -> None:
    gold = load_camera_gold()
    assert gold is not None
    assert gold.verifier.startswith("agent:") and gold.llm.startswith("llm:")
    assert gold.holdout(), "a frozen holdout must exist"
    for p in gold.pairs:
        assert {a.adjudicator for a in p.adjudications} == {gold.verifier, gold.llm}
        text = json.dumps(dict(p.snapshot))
        assert "latitude" not in text and "longitude" not in text  # §19.4: no coordinates
    raw = json.loads(
        files("resolution").joinpath("data", "camera_site_gold.json").read_text(encoding="utf-8")
    )
    assert raw["rules_version"] == RULES.version


def test_the_wilson_bound_states_small_sample_uncertainty() -> None:
    perfect = TierMeasurement(tier=1, predicted=70, match=70, non_match=0, not_enough_information=0)
    assert perfect.precision_strict == 1.0
    assert perfect.wilson_lower_95 == pytest.approx(0.948, abs=1e-3)
    assert TierMeasurement(1, 0, 0, 0, 0).wilson_lower_95 is None


def test_llm_labels_are_reported_as_sensitivity_but_never_gate() -> None:
    # verifier: match; the (untrusted) LLM: not_enough_information.
    recs = [_rec("a", "s1"), _rec("b", "s2", 0.3)]
    r = resolve_camera_sites(
        recs, gold=_gold({("a", "b"): GoldLabel.MATCH}), threshold=0.98, rules=ONE_PAIR
    )
    assert r.auto_write_tiers == {3}
    assert r.tier_measurements_llm_labels[3].precision_strict == 0.0
    s = r.summary()
    assert s["tier_measurements"]["3"]["precision_strict"] == 1.0
    assert s["tier_measurements_llm_labels"]["3"]["not_enough_information"] == 1


def test_the_cli_exposes_the_camera_sites_stage() -> None:
    from resolution.cli import build_parser

    args = build_parser().parse_args(
        ["camera-sites", "--dsn", "postgresql://x", "--role", "r", "--dry-run"]
    )
    assert (args.command, args.role, args.dry_run) == ("camera-sites", "r", True)


# --- P31.11: human review decisions into clustering (ADR-R9-HUMANER) ---------------


def _item(item_id: str, left: str, right: str, tier: int | None = None) -> HumanItem:
    return HumanItem(
        item_id=item_id,
        left=left,
        right=right,
        tier=tier,
        tier_label=RULES.label(tier) if tier is not None else None,
    )


def _vote(
    item_id: str, decision: str, reviewer: str = "curator:one", at: str = "2026-10-01T00:00:00"
) -> HumanVote:
    return HumanVote(item_id=item_id, decision=decision, reviewer=reviewer, decided_at=at)


def _proposal_id(left: str, right: str) -> str:
    a, b = sorted((left, right))
    return f"er_match:camera_site:{a}:{b}"


def test_a_human_accept_clusters_a_proposed_pair_and_names_the_curator() -> None:
    # No gold -> silence never auto-writes, so the pair is proposed; the curator's
    # accept then applies it as a human edge under the same constraints.
    recs = [_rec("a", "s1"), _rec("b", "s2", 0.3)]
    items = [_item(_proposal_id("a", "b"), "a", "b", tier=3)]
    votes = [_vote(_proposal_id("a", "b"), "accept", reviewer="curator:kim")]
    r = resolve_camera_sites(recs, gold=None, threshold=0.98, human_items=items, human_votes=votes)
    (d,) = r.decisions
    assert d.disposition == "human_accept" and d.relation == "same_as"
    assert d.decided_by == "curator:kim"
    assert r.clusters["a"] == r.clusters["b"] and r.cluster_count == 1
    hr = r.summary()["human_review"]
    assert hr["accepts"] == 1 and hr["accept_edges_applied"] == 1
    assert hr["clusters_with_human_accepts"] == 1
    assert r.run_key != run_key(
        rules=RULES, auto_write_tiers=frozenset(), gold=None, records=recs
    )  # the verdict is a run input


def test_a_human_reject_is_a_recorded_cannot_link_that_never_clusters() -> None:
    recs = [_rec("a", "s1"), _rec("b", "s2", 0.3)]
    iid = _proposal_id("a", "b")
    r = resolve_camera_sites(
        recs,
        gold=None,
        threshold=0.98,
        human_items=[_item(iid, "a", "b")],
        human_votes=[_vote(iid, "reject", reviewer="curator:kim")],
    )
    (d,) = r.decisions
    assert d.disposition == "human_reject" and d.relation == "cannot_link"
    assert d.decided_by == "curator:kim"
    assert r.clusters["a"] != r.clusters["b"] and r.cluster_count == 2
    hr = r.summary()["human_review"]
    assert hr["rejects"] == 1 and hr["cannot_link_edges"] == 1


def test_a_reject_beats_an_automatic_tier_that_would_have_auto_written() -> None:
    # Tier 3 measured clean on the holdout, but the curator rejected the pair:
    # the human verdict outranks the automatic outcome on the same pair.
    recs = [_rec("a", "s1"), _rec("b", "s2", 0.3)]
    gold = _gold({("a", "b"): GoldLabel.MATCH})
    auto_only = resolve_camera_sites(recs, gold=gold, threshold=0.98, rules=ONE_PAIR)
    assert auto_only.decisions[0].disposition == "auto_write"
    iid = _proposal_id("a", "b")
    r = resolve_camera_sites(
        recs,
        gold=gold,
        threshold=0.98,
        rules=ONE_PAIR,
        human_items=[_item(iid, "a", "b", tier=3)],
        human_votes=[_vote(iid, "reject")],
    )
    assert r.decisions[0].disposition == "human_reject"
    assert r.cluster_count == 2


def test_an_accept_beats_a_soft_conflict_that_would_have_stayed_proposed() -> None:
    recs = [_rec("a", "s1", jurisdiction="WA"), _rec("b", "s2", 0.3, jurisdiction="OR")]
    iid = _proposal_id("a", "b")
    gold = _gold({("a", "b"): GoldLabel.MATCH})
    r = resolve_camera_sites(
        recs,
        gold=gold,
        threshold=0.98,
        rules=ONE_PAIR,
        human_items=[_item(iid, "a", "b", tier=3)],
        human_votes=[_vote(iid, "accept")],
    )
    # review exists to decide exactly the soft-conflicted pairs — accept applies.
    assert r.decisions[0].disposition == "human_accept"
    assert r.clusters["a"] == r.clusters["b"]


def test_no_decision_leaves_the_proposal_proposed() -> None:
    recs = [_rec("a", "s1"), _rec("b", "s2", 0.3)]
    r = resolve_camera_sites(
        recs,
        gold=None,
        threshold=0.98,
        human_items=[_item(_proposal_id("a", "b"), "a", "b")],  # item, no vote
        human_votes=[],
    )
    (d,) = r.decisions
    assert d.disposition == "proposed" and r.human_verdicts == ()
    assert r.summary()["human_review"]["proposed_awaiting_review"] == 1


def test_zero_decisions_reproduce_the_pre_wiring_run() -> None:
    # With no votes anywhere, the whole run is identical to the pre-wiring
    # pipeline: same decisions, same clusters, same key.
    recs = [_rec("a", "s1"), _rec("b", "s2", 0.3), _rec("c", "s1", 500), _rec("d", "s2", 500.2)]
    gold = _gold({("a", "b"): GoldLabel.MATCH})
    plain = resolve_camera_sites(recs, gold=gold, threshold=0.98, rules=ONE_PAIR)
    wired = resolve_camera_sites(
        recs,
        gold=gold,
        threshold=0.98,
        rules=ONE_PAIR,
        # items exist (they were enqueued) but nothing was ever decided
        human_items=[_item("er_match:camera_site:a:b", "a", "b", tier=3)],
        human_votes=[],
    )
    assert wired.run_key == plain.run_key
    assert wired.decisions == plain.decisions
    assert wired.clusters == plain.clusters
    assert wired.summary()["human_review"]["verdict_pairs"] == 0


def test_conflicting_human_decisions_stay_proposed_for_adjudication() -> None:
    recs = [_rec("a", "s1"), _rec("b", "s2", 0.3)]
    iid = _proposal_id("a", "b")
    votes = [
        _vote(iid, "accept", reviewer="curator:kim", at="2026-10-01T00:00:00"),
        _vote(iid, "reject", reviewer="curator:lee", at="2026-10-02T00:00:00"),
    ]
    r = resolve_camera_sites(
        recs, gold=None, threshold=0.98, human_items=[_item(iid, "a", "b")], human_votes=votes
    )
    (d,) = r.decisions
    assert d.disposition == "proposed" and d.reason == "human_conflict"
    assert r.clusters["a"] != r.clusters["b"]
    hr = r.summary()["human_review"]
    assert hr["conflicts"] == 1 and hr["accept_edges_applied"] == 0


def test_an_accept_violating_constraint_a_is_recorded_refused_never_applied() -> None:
    # A curator may accept, but constraint (a) still binds: two DISTINCT same-source
    # records never merge — the attempt is recorded 'refused' with the constraint named.
    recs = [_rec("a", "s1", external_ref="7"), _rec("b", "s1", 0.3, external_ref="8")]
    iid = _proposal_id("a", "b")
    r = resolve_camera_sites(
        recs,
        gold=None,
        threshold=0.98,
        human_items=[_item(iid, "a", "b")],
        human_votes=[_vote(iid, "accept", reviewer="curator:kim")],
    )
    (d,) = r.decisions
    assert d.disposition == "refused"
    assert d.reason == "human_refused:cluster_constraint:same_source"
    assert d.decided_by == "curator:kim" and d.relation == "same_as"
    assert r.clusters["a"] != r.clusters["b"]
    hr = r.summary()["human_review"]
    assert hr["accepts"] == 1 and hr["accept_edges_refused"] == 1
    assert hr["accept_edges_applied"] == 0


def test_an_accept_across_incompatible_classes_is_refused() -> None:
    alpr = _rec("a", "camreg_lpd_flock", operator="community ALPR layer")
    traffic = _rec("b", "dot_511_ok", 0.2, operator="Oklahoma Department of Transportation")
    iid = _proposal_id("a", "b")
    r = resolve_camera_sites(
        [alpr, traffic],
        gold=None,
        threshold=0.98,
        human_items=[_item(iid, "a", "b")],
        human_votes=[_vote(iid, "accept")],
    )
    (d,) = r.decisions
    assert d.disposition == "refused" and d.reason == "human_refused:incompatible_class"


def test_a_decided_pair_absent_from_the_run_is_counted_not_invented() -> None:
    recs = [_rec("a", "s1"), _rec("b", "s2", 0.3)]
    ghost = _item("er_match:camera_site:x:y", "x", "y")  # records not in this run
    r = resolve_camera_sites(
        recs,
        gold=None,
        threshold=0.98,
        human_items=[ghost],
        human_votes=[_vote("er_match:camera_site:x:y", "accept")],
    )
    assert r.human_verdicts == () and r.human_verdicts_unmatched == 1
    assert r.summary()["human_review"]["unmatched_pairs"] == 1


def test_the_latest_decided_item_governs_a_routed_back_conflict() -> None:
    # accept on the proposal, reject on the routed-back conflict item decided
    # later -> the later adjudication governs (reject).
    recs = [_rec("a", "s1"), _rec("b", "s2", 0.3)]
    prop = _proposal_id("a", "b")
    conf = "er_match:camera_site_conflict:a:b"
    items = [_item(prop, "a", "b"), _item(conf, "a", "b")]
    votes = [
        _vote(prop, "accept", at="2026-10-01T00:00:00"),
        _vote(conf, "reject", reviewer="curator:arbiter", at="2026-10-03T00:00:00"),
    ]
    r = resolve_camera_sites(recs, gold=None, threshold=0.98, human_items=items, human_votes=votes)
    (d,) = r.decisions
    assert d.disposition == "human_reject" and d.decided_by == "curator:arbiter"
    assert d.verdict is not None and len(d.verdict.items) == 2


def test_fold_human_verdicts_item_and_pair_rules() -> None:
    it = "er_match:camera_site:a:b"
    # accept iff every vote accepts; reject iff every vote rejects; else conflict.
    (v,) = fold_human_verdicts(
        [_item(it, "b", "a")],
        [_vote(it, "accept"), _vote(it, "accept", "curator:two", "2026-10-02")],
    )
    assert v.verdict == "accept" and v.left == "a" and v.right == "b"
    assert v.decided_by == "curator:one, curator:two"
    (v,) = fold_human_verdicts(
        [_item(it, "a", "b")],
        [_vote(it, "reject"), _vote(it, "accept", at="2026-10-02T00:00:00")],
    )
    assert v.verdict == "conflict"
    # a vote on an item that binds no pair is never invented into one
    assert fold_human_verdicts([], [_vote(it, "accept")]) == ()
    # a timestamp tie between disagreeing items is itself a conflict, never a coin-flip
    it2 = "er_match:camera_site_disputed:a:b"
    (v,) = fold_human_verdicts(
        [_item(it, "a", "b"), _item(it2, "a", "b")],
        [_vote(it, "accept"), _vote(it2, "reject")],
    )
    assert v.verdict == "conflict"


def test_human_decisions_do_not_break_cluster_id_stability() -> None:
    # Cluster ids are the smallest member subject id — adding a human accept must
    # not churn the public identity of a site between identical re-runs.
    recs = [_rec("a", "s1"), _rec("b", "s2", 0.3), _rec("c", "s3", 1000)]
    iid = _proposal_id("a", "b")
    kwargs = dict(
        gold=None,
        threshold=0.98,
        human_items=[_item(iid, "a", "b")],
        human_votes=[_vote(iid, "accept")],
    )
    r1 = resolve_camera_sites(recs, **kwargs)
    r2 = resolve_camera_sites(recs, **kwargs)
    assert r1.run_key == r2.run_key and r1.clusters == r2.clusters
    assert r1.clusters["a"] == "a" == r1.clusters["b"]
    assert r1.clusters["c"] == "c"


# --- P31.11: duplicate-target lineage (closes D-P30.2b-3) --------------------------


def _dup_pair(**kw) -> list[CameraRecord]:
    """Two records of ONE source republished under two targets."""
    a = _rec("a", "camreg_ucsd", external_ref="cam-7", name="I-5 / Gilman", **kw)
    b = _rec("b", "camreg_ucsd", 0.0, external_ref="cam-7", name="I-5 / Gilman", **kw)
    return [a, b]


def test_identical_captured_content_makes_the_same_row_one_record() -> None:
    a, b = _dup_pair()
    a = replace(a, target_id="ucsd_traffic_camera", capture_digests=("h1", "h2"))
    b = replace(b, target_id="ucsd_traffic_camera_wfl", capture_digests=("h2", "h3"))
    assert infer_duplicate_targets([a, b]) == {"a": "a", "b": "a"}
    r = resolve_camera_sites([a, b], gold=None, threshold=0.98)
    assert r.cluster_count == 1 and r.clusters["a"] == r.clusters["b"]
    (d,) = r.decisions
    assert d.disposition == "auto_write" and d.assessment.tier == 0
    assert d.assessment.tier_label == "0:duplicate_target_of"
    ev = d.assessment.evidence
    assert ev["identical_capture_digests"] == ["h2"]
    s = r.summary()
    assert s["duplicate_target_groups"] == 1 and s["duplicate_target_records"] == 2


def test_row_identical_same_source_records_are_one_lineage() -> None:
    # No capture digests needed: the whole projected row is identical.
    a, b = _dup_pair()
    assert infer_duplicate_targets([a, b]) == {"a": "a", "b": "a"}
    r = resolve_camera_sites([a, b], gold=None, threshold=0.98)
    assert r.cluster_count == 1
    (d,) = r.decisions
    assert d.assessment.evidence["row_identical"] is True


def test_distinct_same_source_devices_never_group() -> None:
    # Same source, same point, DIFFERENT rows: genuinely two devices — the
    # exception is evidence-narrow and these stay separate (constraint (a)).
    a = _rec("a", "camreg_ucsd", external_ref="cam-7", name="I-5 / Gilman")
    b = _rec("b", "camreg_ucsd", 0.2, external_ref="cam-8", name="I-5 / Gilman NB")
    assert infer_duplicate_targets([a, b]) == {}
    r = resolve_camera_sites([a, b], gold=None, threshold=0.98)
    assert r.cluster_count == 2 and r.decisions == ()
    # Content-free stubs with no identifying field also never group.
    s1, s2 = _rec("x", "s", north_m=1000), _rec("y", "s", north_m=1000)
    assert infer_duplicate_targets([s1, s2]) == {}
    # And identical bytes under DIFFERENT refs are two rows, not one.
    c = replace(a, target_id="t1", capture_digests=("h",))
    d = replace(b, target_id="t2", capture_digests=("h",))
    assert infer_duplicate_targets([c, d]) == {}


def test_a_duplicate_group_counts_once_under_constraint_a() -> None:
    # a,b are one republished row of s1; c is s2's coincident record. The group
    # counts as ONE s1 record, so c may cluster with it — and both a and b end
    # up in the site (they are the same row, not two s1 devices).
    a, b = _dup_pair()
    c = _rec("c", "s2", 0.3)
    r = resolve_camera_sites(
        [a, b, c],
        gold=_gold({("a", "c"): GoldLabel.MATCH}),
        threshold=0.98,
        rules=ONE_PAIR,
    )
    assert r.cluster_count == 1
    assert r.clusters["a"] == r.clusters["b"] == r.clusters["c"]
    assert not any(x.kind == "same_source_cluster" for x in r.alerts)


def test_a_human_reject_overrides_even_duplicate_target_evidence() -> None:
    # The fold precedes the dup edge for the SAME pair: a curator's reject is
    # recorded cannot-link and the pair is not merged by its own dup edge.
    a, b = _dup_pair()
    iid = _proposal_id("a", "b")
    r = resolve_camera_sites(
        [a, b],
        gold=None,
        threshold=0.98,
        human_items=[_item(iid, "a", "b")],
        human_votes=[_vote(iid, "reject")],
    )
    (d,) = r.decisions
    assert d.disposition == "human_reject" and d.relation == "cannot_link"
    assert r.clusters["a"] != r.clusters["b"]
