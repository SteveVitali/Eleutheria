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
    PairAssessment,
    TierMeasurement,
    assess_pairs,
    cluster_decisions,
    cluster_summary,
    decide_auto_write_tiers,
    direction_bearing,
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


def test_a_tier_auto_writes_only_when_its_measured_holdout_clears_the_floor() -> None:
    recs = [_rec("a", "s1"), _rec("b", "s2", 0.3), _rec("c", "s1", 500), _rec("d", "s2", 500.2)]
    good = _gold({("a", "b"): GoldLabel.MATCH})
    r = resolve_camera_sites(recs, gold=good, threshold=0.98)
    assert r.auto_write_tiers == {3}
    assert r.observation_count == 4 and r.cluster_count == 2
    assert r.dedup_ratio == pytest.approx(0.5)
    bad = _gold({("a", "b"): GoldLabel.NOT_ENOUGH_INFORMATION})
    r2 = resolve_camera_sites(recs, gold=bad, threshold=0.98)
    assert r2.auto_write_tiers == frozenset()
    assert r2.cluster_count == r2.observation_count == 4  # an honest N = M
    assert {d.disposition for d in r2.decisions} == {"proposed"}


def test_run_key_is_stable_for_unchanged_input_and_moves_with_it() -> None:
    recs = [_rec("a", "s1"), _rec("b", "s2", 0.3)]
    k1 = run_key(rules_version="2", auto_write_tiers={3}, gold_version="g", records=recs)
    assert k1 == run_key(
        rules_version="2", auto_write_tiers={3}, gold_version="g", records=list(reversed(recs))
    )
    changed = [recs[0], replace(recs[1], claim_ids=("c-new",))]
    assert k1 != run_key(rules_version="2", auto_write_tiers={3}, gold_version="g", records=changed)
    assert k1 != run_key(rules_version="2", auto_write_tiers=(), gold_version="g", records=recs)


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
