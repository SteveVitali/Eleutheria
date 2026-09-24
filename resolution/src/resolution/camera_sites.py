# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Geospatial camera-site entity resolution (P30.2b / GO-LIVE.2b, ADR-105).

**The unit.** An *observation-level camera record* is ONE source's published row for
one camera (a ``traffic_camera:<source>:<target>:<ref>`` subject with coordinate
claims). A **resolved site** is a cluster of observation-level records judged to
describe the *same physical device*. ``M`` = observation-level records considered,
``N`` = post-ER clusters (singletons included), ``N <= M``, dedup ratio ``1 - N/M``.
§28 value resolution (ADR-104) decides *which of one record's own claims* stands for
each attribute; this module decides *which records are one device* — the two are
different things and are never reported as each other.

The pipeline (every stage pure and deterministic; the PG seam is
:mod:`resolution.camera_sites_pg`):

1. **Blocking** — :func:`resolution.blocking.validate_geo_rule`: same/neighbouring grid
   cell, different source, sized against the comparison ceiling. Blocking only
   *proposes* candidates (SIG-IDENT-023/024).
2. **Assessment** — :func:`assess_pairs`: distance, shared upstream reference,
   one-to-one-ness, device-class compatibility and soft conflicts give each candidate a
   §14.6 tier (1g shared upstream ref · 3g coincident point · 4g proximate & unique ·
   5g proximate candidate · else tier 6, discarded) with its ``match_evidence``
   (SIG-IDENT-025).
3. **Measurement** — :func:`measure_tiers` / :func:`decide_auto_write_tiers`: the tiers
   are scored against the committed camera gold set's frozen, agent-verified holdout;
   only a *candidate* auto-write tier whose measured (strict) holdout precision clears
   the published floor auto-writes — a tier with no holdout evidence never does
   (SIG-IDENT-028, ADR-099).
4. **Clustering** — :func:`cluster_decisions`: auto-write edges are applied
   strongest-first under hard constraints (no two records of one source in a cluster,
   bounded span, bounded size); a refused union and every sub-floor tier become
   PROPOSED decisions for human review. Cluster-shape alerts (chaining along a road,
   oversized clusters, single-bridge joins) demote an alerted cluster's edges to
   review (SIG-IDENT-029).

**Hard constraints (test-pinned).** (a) Two records of the *same source* are never
merged — not as a pair and not transitively through a cluster: a source listing two
cameras at one spot lists two devices. (b) Records of incompatible device classes
(the recorded matrix in ``camera_site_rules.toml``) are never candidates, and a soft
conflict (differing resolved jurisdiction or explicit device type) can never
auto-write. (c) A mirror of the same upstream dataset is not independent
corroboration: lineages are inferred from coincident republication, and a cluster's
``independent_lineages`` counts lineages, not sources.

**Coordinates are never mixed.** A cluster publishes at most one point, and that
point's latitude and longitude always come from ONE member record
(:func:`representative_point`) — never latitude from one source and longitude from
another (ADR-104 consequence), and never an average (§19.4 / SIG-GEO-009).
"""

from __future__ import annotations

import hashlib
import json
import math
import tomllib
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import date
from functools import cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from .blocking import BlockingContext, GeoGridRule, load_geo_rules, validate_geo_rule
from .gold_set import Adjudication, GoldLabel, WeightBand, assign_band, cohens_kappa
from .quality_gates import ClusterShapeContext, DemotionDecision, cluster_shape_alerts, pair_key

__all__ = [
    "CAMERA_SITE_RESOLVER_VERSION",
    "CameraRecord",
    "CameraSiteRules",
    "PairAssessment",
    "SiteDecision",
    "SiteAlert",
    "CameraSiteResult",
    "TierMeasurement",
    "CameraGoldPair",
    "CameraGoldSet",
    "haversine_m",
    "normalize_ref",
    "direction_bearing",
    "names_agree",
    "device_class",
    "infer_lineages",
    "assess_pairs",
    "cluster_decisions",
    "site_alerts",
    "representative_point",
    "cluster_summary",
    "resolve_camera_sites",
    "measure_tiers",
    "decide_auto_write_tiers",
    "load_camera_gold",
    "camera_adjudication_rules",
    "decision_digest",
    "run_key",
    "dedup_ratio",
]

#: The resolver version stamped on every decision (bump on a behaviour change).
CAMERA_SITE_RESOLVER_VERSION = "camera-sites/1.0.0"

_EARTH_RADIUS_M = 6_371_008.8


@cache
def _rules_data() -> dict[str, Any]:
    resource = files("resolution").joinpath("data", "camera_site_rules.toml")
    with resource.open("rb") as fh:
        return tomllib.load(fh)


def camera_adjudication_rules() -> str:
    """The written camera-site adjudication rules (versioned prose, SIG-IDENT-027)."""
    return str(_rules_data()["gold"]["adjudication_rules"]).strip()


# --------------------------------------------------------------------------- #
# Records + rules                                                              #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CameraRecord:
    """One observation-level camera record: one source's row for one camera.

    ``claim_ids`` are the establishing claims (coordinates + upstream ref) a decision
    over this record cites as provenance.
    """

    subject_id: str
    source_id: str
    latitude: float | None
    longitude: float | None
    external_ref: str | None = None
    name: str | None = None
    roadway: str | None = None
    direction: str | None = None
    operator: str | None = None
    jurisdiction: str | None = None
    camera_type: str | None = None
    claim_ids: tuple[str, ...] = ()

    def block_record(self) -> dict[str, Any]:
        return {"latitude": self.latitude, "longitude": self.longitude, "source_id": self.source_id}


@dataclass(frozen=True)
class _ClassRule:
    name: str
    source_prefixes: tuple[str, ...] = ()
    source_substrings: tuple[str, ...] = ()
    operator_substrings: tuple[str, ...] = ()
    type_substrings: tuple[str, ...] = ()


@dataclass(frozen=True)
class CameraSiteRules:
    """The versioned camera-site rules (``camera_site_rules.toml``), injectable in tests."""

    version: str = "1"
    coincident_m: float = 1.0
    colocation_m: float = 5.0
    near_max_m: float = 25.0
    candidate_max_m: float = 50.0
    candidate_auto_write: frozenset[int] = frozenset({1, 3})
    tier_labels: Mapping[int, str] = field(
        default_factory=lambda: {
            1: "1g:shared_upstream_ref",
            3: "3g:coincident_point",
            4: "4g:proximate_unique",
            5: "5g:proximate_candidate",
        }
    )
    default_class: str = "unspecified"
    class_rules: tuple[_ClassRule, ...] = ()
    incompatible_classes: frozenset[frozenset[str]] = frozenset()
    soft_conflict_fields: tuple[str, ...] = ("jurisdiction", "camera_type")
    unresolved_jurisdictions: frozenset[str] = frozenset({"unresolved", "", "unknown"})
    direction_conflict_deg: float = 90.0
    shared_ref_requires_mutual_nearest: bool = True
    shared_ref_colocated_requires_name_agreement: bool = True
    lineage_min_pairs: int = 20
    lineage_min_share: float = 0.5
    max_span_m: float = 50.0
    max_size: int = 6
    substantial_component: int = 3
    gold_bands: tuple[WeightBand, ...] = ()
    holdout_fraction: float = 0.3
    gold_seed: int = 30
    strict_precision: bool = True
    min_holdout_pairs: int = 50

    @classmethod
    def from_data(cls) -> CameraSiteRules:
        d = _rules_data()
        dist = d["distance"]
        classes = d["classes"]
        return cls(
            version=str(d["version"]),
            coincident_m=float(dist["coincident_m"]),
            colocation_m=float(dist["colocation_m"]),
            near_max_m=float(dist["near_max_m"]),
            candidate_max_m=float(dist["candidate_max_m"]),
            candidate_auto_write=frozenset(int(t) for t in d["tiers"]["candidate_auto_write"]),
            tier_labels={int(k): str(v) for k, v in d["tiers"]["labels"].items()},
            default_class=str(classes["default"]),
            class_rules=tuple(
                _ClassRule(
                    name=str(r["class"]),
                    source_prefixes=tuple(r.get("source_prefixes", ())),
                    source_substrings=tuple(r.get("source_substrings", ())),
                    operator_substrings=tuple(r.get("operator_substrings", ())),
                    type_substrings=tuple(r.get("type_substrings", ())),
                )
                for r in classes["rule"]
            ),
            incompatible_classes=frozenset(frozenset(p) for p in classes["incompatible"]),
            soft_conflict_fields=tuple(d["soft_conflicts"]["fields"]),
            unresolved_jurisdictions=frozenset(
                str(v).lower() for v in d["soft_conflicts"]["unresolved_jurisdictions"]
            ),
            direction_conflict_deg=float(d["soft_conflicts"]["direction_conflict_deg"]),
            shared_ref_requires_mutual_nearest=bool(
                d["tiers"]["shared_ref_requires_mutual_nearest"]
            ),
            shared_ref_colocated_requires_name_agreement=bool(
                d["tiers"]["shared_ref_colocated_requires_name_agreement"]
            ),
            lineage_min_pairs=int(d["lineage"]["min_pairs"]),
            lineage_min_share=float(d["lineage"]["min_share"]),
            max_span_m=float(d["clusters"]["max_span_m"]),
            max_size=int(d["clusters"]["max_size"]),
            substantial_component=int(d["clusters"]["substantial_component"]),
            gold_bands=tuple(
                WeightBand(name=str(b["name"]), min_weight=float(b["min_weight"]))
                for b in d["gold_band"]
            ),
            holdout_fraction=float(d["gold"]["holdout_fraction"]),
            gold_seed=int(d["gold"]["seed"]),
            strict_precision=bool(d["gold"]["strict_precision"]),
            min_holdout_pairs=int(d["gold"]["min_holdout_pairs"]),
        )

    def label(self, tier: int) -> str:
        return self.tier_labels.get(tier, f"{tier}g")


# --------------------------------------------------------------------------- #
# Primitive features                                                           #
# --------------------------------------------------------------------------- #


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres (mean Earth radius)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def normalize_ref(ref: str | None) -> str | None:
    """Normalise an upstream reference for comparison, or ``None`` when absent.

    Trimmed and lower-cased; a trailing ``.0`` float artefact (a spreadsheet/ArcGIS
    numeric id republished as ``51.0``) is removed so ``51`` and ``51.0`` compare equal.
    """
    if ref is None:
        return None
    text = str(ref).strip().lower()
    if text.endswith(".0") and text[:-2].lstrip("-").isdigit():
        text = text[:-2]
    return text or None


def device_class(record: CameraRecord, rules: CameraSiteRules) -> str:
    """The recorded device class of ``record`` (first matching rule; else the default)."""
    source = record.source_id.lower()
    operator = (record.operator or "").lower()
    camera_type = (record.camera_type or "").lower()
    for rule in rules.class_rules:
        if any(source.startswith(p) for p in rule.source_prefixes):
            return rule.name
        if any(s in source for s in rule.source_substrings):
            return rule.name
        if any(s in operator for s in rule.operator_substrings):
            return rule.name
        if any(s in camera_type for s in rule.type_substrings):
            return rule.name
    return rules.default_class


_COMPASS = {
    "n": 0.0, "north": 0.0, "nb": 0.0, "northbound": 0.0,
    "ne": 45.0, "northeast": 45.0,
    "e": 90.0, "east": 90.0, "eb": 90.0, "eastbound": 90.0,
    "se": 135.0, "southeast": 135.0,
    "s": 180.0, "south": 180.0, "sb": 180.0, "southbound": 180.0,
    "sw": 225.0, "southwest": 225.0,
    "w": 270.0, "west": 270.0, "wb": 270.0, "westbound": 270.0,
    "nw": 315.0, "northwest": 315.0,
}  # fmt: skip


def direction_bearing(value: str | None) -> float | None:
    """A viewing direction as a compass bearing in degrees, or ``None`` if not one.

    Compass words/abbreviations (``N``, ``Southbound``, ``EB`` …) and numeric bearings
    (0–360) parse; anything else (``B`` = both ways, free text) is not a direction.
    """
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in _COMPASS:
        return _COMPASS[text]
    try:
        bearing = float(text)
    except ValueError:
        return None
    return bearing % 360.0 if 0.0 <= bearing <= 360.0 else None


def _angle_between(a: float, b: float) -> float:
    diff = abs(a - b) % 360.0
    return min(diff, 360.0 - diff)


def names_agree(a: str | None, b: str | None) -> bool:
    """Two site descriptions agree when both are present and equal once normalised
    (lower-case, alphanumerics only) — the conservative test; formatting differences
    that a human would accept are left to review."""
    if not a or not b:
        return False
    na = "".join(ch for ch in a.lower() if ch.isalnum())
    nb = "".join(ch for ch in b.lower() if ch.isalnum())
    return bool(na) and na == nb


def _soft_conflicts(a: CameraRecord, b: CameraRecord, rules: CameraSiteRules) -> tuple[str, ...]:
    out: list[str] = []
    if "jurisdiction" in rules.soft_conflict_fields:
        ja = (a.jurisdiction or "").strip().lower()
        jb = (b.jurisdiction or "").strip().lower()
        if (
            ja not in rules.unresolved_jurisdictions
            and jb not in rules.unresolved_jurisdictions
            and ja != jb
        ):
            out.append("jurisdiction")
    if "camera_type" in rules.soft_conflict_fields:
        ta = (a.camera_type or "").strip().lower()
        tb = (b.camera_type or "").strip().lower()
        if ta and tb and ta != tb:
            out.append("camera_type")
    if "direction" in rules.soft_conflict_fields:
        da, db = direction_bearing(a.direction), direction_bearing(b.direction)
        if (
            da is not None
            and db is not None
            and _angle_between(da, db) > rules.direction_conflict_deg
        ):
            out.append("direction")
    return tuple(out)


def _valid_point(r: CameraRecord) -> bool:
    if r.latitude is None or r.longitude is None:
        return False
    return not (r.latitude == 0.0 and r.longitude == 0.0)


# --------------------------------------------------------------------------- #
# Lineage (mirror) inference                                                   #
# --------------------------------------------------------------------------- #


def infer_lineages(
    records: Sequence[CameraRecord],
    coincident_pairs: Iterable[tuple[int, int]],
    rules: CameraSiteRules,
) -> dict[str, str]:
    """Group sources into lineages: republications of one upstream dataset.

    Two sources are one lineage when at least ``lineage_min_pairs`` of their records
    are coincident AND the coincident records cover at least ``lineage_min_share`` of
    the smaller source (data-generated, re-derived every run). Returns
    ``source_id -> lineage_id`` (the lexicographically smallest source of its lineage);
    a source that mirrors nothing is its own lineage.
    """
    size: dict[str, int] = defaultdict(int)
    for r in records:
        size[r.source_id] += 1
    covered: dict[tuple[str, str], tuple[set[int], set[int]]] = {}
    for i, j in coincident_pairs:
        sa, sb = records[i].source_id, records[j].source_id
        if sa == sb:
            continue
        key = (sa, sb) if sa < sb else (sb, sa)
        left, right = covered.setdefault(key, (set(), set()))
        if sa < sb:
            left.add(i)
            right.add(j)
        else:
            left.add(j)
            right.add(i)
    parent: dict[str, str] = {s: s for s in size}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for (sa, sb), (left, right) in sorted(covered.items()):
        pairs = min(len(left), len(right))
        smaller = min(size[sa], size[sb])
        if (
            pairs >= rules.lineage_min_pairs
            and smaller
            and pairs / smaller >= rules.lineage_min_share
        ):
            ra, rb = find(sa), find(sb)
            if ra != rb:
                lo, hi = sorted((ra, rb))
                parent[hi] = lo
    return {s: find(s) for s in sorted(size)}


# --------------------------------------------------------------------------- #
# Pair assessment                                                              #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class PairAssessment:
    """One blocked candidate pair, assessed: its §14.6 tier and ``match_evidence``.

    ``left < right`` (subject ids). ``tier`` is 1/3/4/5 for a recorded candidate; a pair
    that falls to tier 6 is not returned (no per-pair record, SIG-IDENT-020).
    """

    left: str
    right: str
    tier: int
    tier_label: str
    distance_m: float
    soft_conflicts: tuple[str, ...]
    evidence: Mapping[str, Any]
    evidence_claims: tuple[str, ...]

    @property
    def key(self) -> tuple[str, str]:
        return (self.left, self.right)


@dataclass(frozen=True)
class _Assessed:
    assessments: tuple[PairAssessment, ...]
    lineages: dict[str, str]
    blocking_size: int
    unblockable: int
    incompatible_blocked: int
    discarded: int


def _neighbour_index(
    records: Sequence[CameraRecord], pairs: Sequence[tuple[int, int, float]]
) -> dict[int, dict[str, list[tuple[float, int]]]]:
    """record index -> other source -> [(distance, index)] nearest-first (within radius)."""
    by_source: dict[int, dict[str, list[tuple[float, int]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for i, j, d in pairs:
        by_source[i][records[j].source_id].append((d, j))
        by_source[j][records[i].source_id].append((d, i))
    for per in by_source.values():
        for lst in per.values():
            lst.sort()
    return by_source


def _count_within(neigh: list[tuple[float, int]], radius: float) -> int:
    return sum(1 for d, _ in neigh if d <= radius)


def _assess(
    records: Sequence[CameraRecord],
    *,
    rules: CameraSiteRules,
    geo_rule: GeoGridRule,
    blocking_context: BlockingContext | None,
) -> _Assessed:
    block_records = [r.block_record() for r in records]
    index_pairs = validate_geo_rule(block_records, geo_rule, context=blocking_context)
    unblockable = sum(1 for br in block_records if geo_rule.cell(br) is None)

    within: list[tuple[int, int, float]] = []
    for i, j in index_pairs:
        a, b = records[i], records[j]
        if a.source_id == b.source_id or not (_valid_point(a) and _valid_point(b)):
            continue  # hard constraint (a) — defence in depth behind the blocking rule
        d = haversine_m(a.latitude, a.longitude, b.latitude, b.longitude)  # type: ignore[arg-type]
        if d <= rules.candidate_max_m:
            within.append((i, j, d))

    lineages = infer_lineages(
        records, [(i, j) for i, j, d in within if d <= rules.coincident_m], rules
    )
    neigh = _neighbour_index(records, within)
    classes = [device_class(r, rules) for r in records]

    out: list[PairAssessment] = []
    incompatible = discarded = 0
    for i, j, d in within:
        a, b = records[i], records[j]
        if frozenset((classes[i], classes[j])) in rules.incompatible_classes:
            incompatible += 1  # hard constraint (b): never a candidate
            continue
        na = neigh[i][b.source_id]  # a's neighbours in b's source (sorted by distance)
        nb = neigh[j][a.source_id]
        ref_a, ref_b = normalize_ref(a.external_ref), normalize_ref(b.external_ref)
        ref_equal = ref_a is not None and ref_a == ref_b
        unique_colocation = (
            _count_within(na, rules.colocation_m) == 1
            and _count_within(nb, rules.colocation_m) == 1
        )
        # An exact distance tie is not a nearest neighbour: it fails (conservatively).
        mutual_nearest = (
            bool(na)
            and bool(nb)
            and na[0][1] == j
            and nb[0][1] == i
            and (len(na) < 2 or na[1][0] > na[0][0])
            and (len(nb) < 2 or nb[1][0] > nb[0][0])
        )
        unique_near = (
            _count_within(na, rules.near_max_m) == 1 and _count_within(nb, rules.near_max_m) == 1
        )
        # For the shared-ref tier, "mutually nearest" means no record of the other source is
        # STRICTLY nearer on either side: a tie (two devices at one point) is resolved by the
        # shared reference plus the co-location/name rule below, independent of record order.
        none_strictly_nearer = bool(na) and bool(nb) and na[0][0] >= d and nb[0][0] >= d
        shared_ref_tier = ref_equal
        if ref_equal and rules.shared_ref_requires_mutual_nearest and not none_strictly_nearer:
            shared_ref_tier = False  # another record of the other source is the nearer copy
        if (
            shared_ref_tier
            and rules.shared_ref_colocated_requires_name_agreement
            and not unique_colocation
            and not names_agree(a.name, b.name)
        ):
            # Unless the site descriptions agree, the pair must be each other's ONLY
            # counterpart within the co-location radius: a publisher listing several devices
            # at one point cannot say WHICH one a shared row number is.
            shared_ref_tier = False
        if shared_ref_tier:
            tier = 1
        elif d <= rules.coincident_m and unique_colocation:
            tier = 3
        elif d <= rules.near_max_m and mutual_nearest and unique_near:
            tier = 4
        elif d <= rules.near_max_m or mutual_nearest:
            tier = 5
        else:
            discarded += 1  # tier 6: below threshold, no per-pair record
            continue
        left_i, right_i = (i, j) if a.subject_id < b.subject_id else (j, i)
        left, right = records[left_i], records[right_i]
        same_lineage = lineages[a.source_id] == lineages[b.source_id]
        soft = _soft_conflicts(a, b, rules)
        evidence: dict[str, Any] = {
            "rule": rules.label(tier),
            "distance_m": round(d, 2),
            "sources": [left.source_id, right.source_id],
            "device_classes": [classes[left_i], classes[right_i]],
            "shared_upstream_ref": ref_a if ref_equal else None,
            "names_agree": names_agree(a.name, b.name),
            "unique_within_colocation": unique_colocation,
            "mutual_nearest": mutual_nearest,
            "unique_within_near": unique_near,
            "same_lineage": same_lineage,
            "soft_conflicts": list(soft),
            "rules_version": rules.version,
        }
        out.append(
            PairAssessment(
                left=left.subject_id,
                right=right.subject_id,
                tier=tier,
                tier_label=rules.label(tier),
                distance_m=d,
                soft_conflicts=soft,
                evidence=evidence,
                evidence_claims=tuple(sorted(set(left.claim_ids) | set(right.claim_ids))),
            )
        )
    out.sort(key=lambda p: (p.left, p.right))
    return _Assessed(
        assessments=tuple(out),
        lineages=lineages,
        blocking_size=len(index_pairs),
        unblockable=unblockable,
        incompatible_blocked=incompatible,
        discarded=discarded,
    )


def assess_pairs(
    records: Sequence[CameraRecord],
    *,
    rules: CameraSiteRules | None = None,
    geo_rule: GeoGridRule | None = None,
    blocking_context: BlockingContext | None = None,
) -> tuple[PairAssessment, ...]:
    """Block and assess every candidate pair of ``records`` (tiers 1/3/4/5; tier 6 dropped)."""
    rs = rules or CameraSiteRules.from_data()
    gr = geo_rule or load_geo_rules()[0]
    return _assess(records, rules=rs, geo_rule=gr, blocking_context=blocking_context).assessments


# --------------------------------------------------------------------------- #
# Decisions + constrained clustering                                           #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SiteDecision:
    """A recorded same-device decision: ``auto_write`` (clustered) or ``proposed`` (review).

    ``reason`` says why a candidate that could have auto-written was routed to review
    (a demoted/unmeasured tier, a soft conflict, a refused union, a cluster alert).
    """

    assessment: PairAssessment
    disposition: str  # "auto_write" | "proposed"
    reason: str | None = None

    @property
    def left(self) -> str:
        return self.assessment.left

    @property
    def right(self) -> str:
        return self.assessment.right


@dataclass(frozen=True)
class SiteAlert:
    """A cluster-shape alert (SIG-IDENT-029) on a would-be resolved site."""

    cluster_id: str
    kind: str  # elongated_cluster | oversized_cluster | single_bridge_join | same_source_cluster
    detail: Mapping[str, Any]


class _Clusters:
    def __init__(self, records: Mapping[str, CameraRecord]) -> None:
        self.parent: dict[str, str] = {s: s for s in records}
        self.members: dict[str, list[str]] = {s: [s] for s in records}
        self.records = records

    def find(self, x: str) -> str:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def span_if_joined(self, ra: str, rb: str) -> float:
        span = 0.0
        for x in self.members[ra]:
            px = self.records[x]
            for y in self.members[rb]:
                py = self.records[y]
                span = max(
                    span,
                    haversine_m(px.latitude, px.longitude, py.latitude, py.longitude),  # type: ignore[arg-type]
                )
        return span

    def refusal(self, a: str, b: str, rules: CameraSiteRules) -> str | None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return None
        sources_a = {self.records[m].source_id for m in self.members[ra]}
        sources_b = {self.records[m].source_id for m in self.members[rb]}
        if sources_a & sources_b:
            return "cluster_constraint:same_source"
        if len(self.members[ra]) + len(self.members[rb]) > rules.max_size:
            return "cluster_constraint:max_size"
        # Each existing cluster's own span is already bounded, so the joined span is
        # bounded iff every cross-cluster distance is.
        if self.span_if_joined(ra, rb) > rules.max_span_m:
            return "cluster_constraint:max_span"
        return None

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        lo, hi = sorted((ra, rb))
        self.parent[hi] = lo
        self.members[lo].extend(self.members.pop(hi))


def _clusters_from_edges(
    subjects: Iterable[str], edges: Iterable[tuple[str, str]]
) -> dict[str, str]:
    parent: dict[str, str] = {s: s for s in subjects}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            lo, hi = sorted((ra, rb))
            parent[hi] = lo
    return {s: find(s) for s in parent}


def site_alerts(
    clusters: Mapping[str, str],
    edges: Sequence[tuple[str, str]],
    records: Mapping[str, CameraRecord],
    rules: CameraSiteRules,
) -> list[SiteAlert]:
    """Cluster-shape alerts over would-be resolved sites (SIG-IDENT-029).

    * ``elongated_cluster`` — the cluster's span exceeds ``max_span_m``: the signature
      of a chain strung along a road (each hop short, the whole far too long for one
      device);
    * ``oversized_cluster`` — more members than ``max_size``;
    * ``same_source_cluster`` — two members of one source (a hard-constraint breach);
    * ``single_bridge_join`` — one edge joins two components each at least
      ``substantial_component`` large (via :func:`resolution.quality_gates.cluster_shape_alerts`).
    """
    members: dict[str, list[str]] = defaultdict(list)
    for s, c in clusters.items():
        members[c].append(s)
    alerts: list[SiteAlert] = []
    for cid in sorted(members):
        ms = sorted(members[cid])
        if len(ms) < 2:
            continue
        span = 0.0
        for x_i, x in enumerate(ms):
            for y in ms[x_i + 1 :]:
                px, py = records[x], records[y]
                span = max(
                    span,
                    haversine_m(px.latitude, px.longitude, py.latitude, py.longitude),  # type: ignore[arg-type]
                )
        if span > rules.max_span_m:
            alerts.append(
                SiteAlert(
                    cid,
                    "elongated_cluster",
                    {"span_m": round(span, 1), "max_span_m": rules.max_span_m, "size": len(ms)},
                )
            )
        if len(ms) > rules.max_size:
            alerts.append(
                SiteAlert(cid, "oversized_cluster", {"size": len(ms), "max_size": rules.max_size})
            )
        sources = [records[m].source_id for m in ms]
        if len(set(sources)) < len(sources):
            alerts.append(SiteAlert(cid, "same_source_cluster", {"sources": sorted(sources)}))
    ctx = ClusterShapeContext(
        max_le_cluster_size=10**9,  # the law-enforcement rule does not apply to devices
        substantial_component_size=rules.substantial_component,
        le_classes=frozenset(),
    )
    for a in cluster_shape_alerts(clusters, edges, None, context=ctx):
        if a.kind == "single_bridge_join":
            alerts.append(SiteAlert(a.cluster_id, a.kind, dict(a.detail)))
    return alerts


def cluster_decisions(
    assessments: Sequence[PairAssessment],
    records: Sequence[CameraRecord],
    *,
    auto_write_tiers: Iterable[int],
    rules: CameraSiteRules | None = None,
) -> tuple[tuple[SiteDecision, ...], dict[str, str], tuple[SiteAlert, ...]]:
    """Turn assessments into decisions + clusters under the hard constraints.

    Returns ``(decisions, clusters, alerts)`` where ``clusters`` maps every record's
    subject id to its cluster id (the smallest member subject id; a singleton maps to
    itself). Only ``auto_write`` decisions cluster.
    """
    rs = rules or CameraSiteRules.from_data()
    auto = frozenset(auto_write_tiers)
    by_id = {r.subject_id: r for r in records}
    state = _Clusters(by_id)

    initial: dict[tuple[str, str], tuple[str, str | None]] = {}
    ordered = sorted(assessments, key=lambda p: (p.tier, p.distance_m, p.left, p.right))
    for p in ordered:
        if p.tier not in auto:
            initial[p.key] = ("proposed", "tier_not_auto_write")
        elif p.soft_conflicts:
            initial[p.key] = ("proposed", "soft_conflict:" + ",".join(p.soft_conflicts))
        else:
            refusal = state.refusal(p.left, p.right, rs)
            if refusal is None:
                state.union(p.left, p.right)
                initial[p.key] = ("auto_write", None)
            else:
                initial[p.key] = ("proposed", refusal)

    auto_edges = [k for k, (disp, _r) in initial.items() if disp == "auto_write"]
    clusters = _clusters_from_edges(by_id, auto_edges)
    alerts = site_alerts(clusters, auto_edges, by_id, rs)
    alerted = {a.cluster_id for a in alerts}
    if alerted:
        for k in auto_edges:
            if clusters[k[0]] in alerted:
                initial[k] = ("proposed", "cluster_shape_alert")
        auto_edges = [k for k, (disp, _r) in initial.items() if disp == "auto_write"]
        clusters = _clusters_from_edges(by_id, auto_edges)

    decisions = tuple(
        SiteDecision(assessment=p, disposition=initial[p.key][0], reason=initial[p.key][1])
        for p in sorted(assessments, key=lambda p: (p.left, p.right))
    )
    return decisions, clusters, tuple(alerts)


def representative_point(
    members: Sequence[CameraRecord],
) -> tuple[str, float, float] | None:
    """The ONE member record whose coordinate pair stands for a resolved site.

    Both axes always come from the same record (never latitude from one source and
    longitude from another — a point no source reported, ADR-104) and are that record's
    own observed values (never an average, §19.4 / SIG-GEO-009). Deterministic: the
    smallest subject id among members with a valid point. ``None`` if none has one.
    """
    candidates = sorted((m for m in members if _valid_point(m)), key=lambda m: m.subject_id)
    if not candidates:
        return None
    rep = candidates[0]
    return rep.subject_id, float(rep.latitude), float(rep.longitude)  # type: ignore[arg-type]


def cluster_summary(
    cluster_members: Sequence[CameraRecord], lineages: Mapping[str, str]
) -> dict[str, Any]:
    """Summarise one resolved site: members, sources, and INDEPENDENT lineages.

    ``independent_lineages`` counts lineages, not sources, so a mirror of the same
    upstream dataset never counts as a second, independent confirmation
    (hard constraint (c)); ``corroborated`` is true only with two or more lineages.
    """
    sources = sorted({m.source_id for m in cluster_members})
    lineage_ids = sorted({lineages.get(s, s) for s in sources})
    return {
        "size": len(cluster_members),
        "sources": sources,
        "independent_lineages": len(lineage_ids),
        "corroborated": len(lineage_ids) >= 2,
    }


def dedup_ratio(m: int, n: int) -> float:
    """``1 - N/M`` (0.0 when there are no observations)."""
    return 0.0 if m == 0 else 1.0 - n / m


# --------------------------------------------------------------------------- #
# Gold set + measurement (ADR-099 loop, camera flavour)                         #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CameraGoldPair:
    """One adjudicated camera candidate pair of the committed gold set."""

    pair_id: str
    left: str
    right: str
    stratum: str
    weight: float  # -distance_m (nearer = higher), the band score
    band: str
    snapshot: Mapping[str, Any]
    adjudications: tuple[Adjudication, ...]
    frozen: bool

    def label_by(self, adjudicator: str) -> GoldLabel | None:
        for a in self.adjudications:
            if a.adjudicator == adjudicator:
                return a.label
        return None


@dataclass(frozen=True)
class CameraGoldSet:
    """The versioned camera gold set with its frozen, agent/maintainer-verified holdout."""

    version: str
    rules_version: str
    verifier: str
    llm: str
    pairs: tuple[CameraGoldPair, ...]
    digest: str = ""

    def holdout(self) -> tuple[CameraGoldPair, ...]:
        return tuple(p for p in self.pairs if p.frozen)

    def content_digest(self) -> str:
        """The committed file's digest, else a digest of the labels, splits and pairs."""
        if self.digest:
            return self.digest
        body = [
            (
                p.pair_id,
                p.left,
                p.right,
                p.frozen,
                sorted((a.adjudicator, a.label.value) for a in p.adjudications),
            )
            for p in self.pairs
        ]
        return hashlib.sha256(
            json.dumps([self.version, self.verifier, self.llm, body]).encode()
        ).hexdigest()

    def kappa(self) -> float:
        a: list[GoldLabel] = []
        b: list[GoldLabel] = []
        for p in self.pairs:
            la, lb = p.label_by(self.verifier), p.label_by(self.llm)
            if la is not None and lb is not None:
                a.append(la)
                b.append(lb)
        return cohens_kappa(a, b)

    def disputed(self) -> tuple[str, ...]:
        return tuple(
            p.pair_id
            for p in self.pairs
            if p.label_by(self.verifier) is not None
            and p.label_by(self.llm) is not None
            and p.label_by(self.verifier) != p.label_by(self.llm)
        )

    def holdout_label(self, pair: CameraGoldPair) -> GoldLabel | None:
        """The holdout's label is the VERIFIER's (design §2.3 guardrail 2): a disputed
        holdout pair is never dropped from the precision it governs."""
        return pair.label_by(self.verifier)


def _gold_path() -> Any:
    return files("resolution").joinpath("data", "camera_site_gold.json")


def load_camera_gold(path: Path | str | None = None) -> CameraGoldSet | None:
    """Load the committed camera gold set, or ``None`` when none is committed."""
    if path is not None:
        p = Path(path)
        if not p.exists():
            return None
        raw = json.loads(p.read_text(encoding="utf-8"))
    else:
        res = _gold_path()
        if not res.is_file():
            return None
        raw = json.loads(res.read_text(encoding="utf-8"))
    return gold_from_dict(raw)


def gold_from_dict(raw: Mapping[str, Any]) -> CameraGoldSet:
    pairs = []
    for p in raw["pairs"]:
        adjs = tuple(
            Adjudication(
                pair_id=str(p["pair_id"]),
                adjudicator=str(a["adjudicator"]),
                label=GoldLabel(str(a["label"])),
                dated=date.fromisoformat(str(a["dated"])),
                ruleset_version=str(a.get("ruleset_version", raw.get("rules_version", "1"))),
                note=str(a.get("note", "")),
            )
            for a in p["adjudications"]
        )
        pairs.append(
            CameraGoldPair(
                pair_id=str(p["pair_id"]),
                left=str(p["left"]),
                right=str(p["right"]),
                stratum=str(p["stratum"]),
                weight=float(p["weight"]),
                band=str(p["band"]),
                snapshot=dict(p.get("snapshot", {})),
                adjudications=adjs,
                frozen=bool(p["frozen"]),
            )
        )
    return CameraGoldSet(
        digest=hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest(),
        version=str(raw["version"]),
        rules_version=str(raw["rules_version"]),
        verifier=str(raw["verifier"]),
        llm=str(raw["llm"]),
        pairs=tuple(pairs),
    )


def gold_band(distance_m: float, rules: CameraSiteRules) -> str:
    return assign_band(-distance_m, rules.gold_bands)


@dataclass(frozen=True)
class TierMeasurement:
    """A tier's precision on the frozen holdout (strict: NEI counts against)."""

    tier: int
    predicted: int  # holdout pairs the matcher put at this tier
    match: int
    non_match: int
    not_enough_information: int

    @property
    def precision_strict(self) -> float | None:
        return None if self.predicted == 0 else self.match / self.predicted

    @property
    def wilson_lower_95(self) -> float | None:
        """The 95% Wilson lower bound on the strict precision (small-sample honesty)."""
        if self.predicted == 0:
            return None
        n, p, z = self.predicted, self.match / self.predicted, 1.96
        centre = p + z * z / (2 * n)
        margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
        return (centre - margin) / (1 + z * z / n)

    @property
    def precision_decided(self) -> float | None:
        decided = self.match + self.non_match
        return None if decided == 0 else self.match / decided


def measure_tiers(
    gold: CameraGoldSet,
    tier_by_pair: Mapping[tuple[str, str], int],
    *,
    adjudicator: str | None = None,
) -> dict[int, TierMeasurement]:
    """Per-tier precision of the matcher on the frozen holdout (SIG-IDENT-028).

    ``tier_by_pair`` is the run's tier assignment keyed by ``(left, right)`` subject ids
    (order-free). A holdout pair the run did not propose is a tier-6 discard and scores
    no tier. The label is the verifier's (the agent/maintainer-verified holdout) unless
    ``adjudicator`` names another — used only to REPORT the sensitivity of the measurement
    to the (untrusted) LLM's labels, never to gate auto-write.
    """
    counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    normalised = {pair_key(*k): t for k, t in tier_by_pair.items()}
    for p in gold.holdout():
        tier = normalised.get(pair_key(p.left, p.right))
        label = gold.holdout_label(p) if adjudicator is None else p.label_by(adjudicator)
        if tier is None or label is None:
            continue
        counts[tier]["predicted"] += 1
        counts[tier][label.value] += 1
    return {
        t: TierMeasurement(
            tier=t,
            predicted=c["predicted"],
            match=c[GoldLabel.MATCH.value],
            non_match=c[GoldLabel.NON_MATCH.value],
            not_enough_information=c[GoldLabel.NOT_ENOUGH_INFORMATION.value],
        )
        for t, c in sorted(counts.items())
    }


def decide_auto_write_tiers(
    measured: Mapping[int, TierMeasurement],
    *,
    candidate_tiers: Iterable[int],
    threshold: float,
    strict: bool = True,
    min_pairs: int = 1,
) -> tuple[frozenset[int], tuple[DemotionDecision, ...]]:
    """Which candidate tiers auto-write this run, and the demotion record.

    A candidate tier auto-writes only if it has at least ``min_pairs`` holdout pairs AND
    its measured precision (strict by default) is at least ``threshold``; a tier with no
    (or too little) holdout evidence is demoted — silence, or 1-of-1, never auto-writes.
    """
    auto: set[int] = set()
    decisions: list[DemotionDecision] = []
    for tier in sorted(set(candidate_tiers)):
        m = measured.get(tier)
        precision = None
        if m is not None:
            precision = m.precision_strict if strict else m.precision_decided
        value = 0.0 if precision is None else precision
        too_few = m is None or m.predicted < min_pairs
        demoted = precision is None or too_few or precision < threshold
        decisions.append(
            DemotionDecision(tier=tier, precision=value, threshold=threshold, demoted=demoted)
        )
        if not demoted:
            auto.add(tier)
    return frozenset(auto), tuple(decisions)


# --------------------------------------------------------------------------- #
# One ER run                                                                   #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CameraSiteResult:
    """The output of one camera-site ER run (pure; persisted by camera_sites_pg)."""

    rules_version: str
    resolver_version: str
    run_key: str
    observation_count: int  # M
    cluster_count: int  # N
    decisions: tuple[SiteDecision, ...]
    clusters: dict[str, str]
    alerts: tuple[SiteAlert, ...]
    lineages: dict[str, str]
    sources: dict[str, str]  # subject id -> source id
    auto_write_tiers: frozenset[int]
    demotions: tuple[DemotionDecision, ...]
    tier_measurements: dict[int, TierMeasurement]
    tier_measurements_llm_labels: dict[int, TierMeasurement]
    blocking_size: int
    unblockable: int
    incompatible_blocked: int
    discarded: int
    gold_version: str | None
    kappa: float | None
    holdout_size: int
    gold_size: int
    disputed: int

    @property
    def dedup_ratio(self) -> float:
        return dedup_ratio(self.observation_count, self.cluster_count)

    def counts(self) -> dict[str, Any]:
        by_tier: dict[str, dict[str, int]] = {}
        for d in self.decisions:
            slot = by_tier.setdefault(d.assessment.tier_label, {"auto_write": 0, "proposed": 0})
            slot[d.disposition] += 1
        reasons: dict[str, int] = defaultdict(int)
        for d in self.decisions:
            if d.reason:
                reasons[d.reason] += 1
        sizes: dict[int, int] = defaultdict(int)
        members: dict[str, int] = defaultdict(int)
        for c in self.clusters.values():
            members[c] += 1
        for n in members.values():
            sizes[n] += 1
        lineage_groups: dict[str, list[str]] = defaultdict(list)
        for s, lin in self.lineages.items():
            lineage_groups[lin].append(s)
        return {
            **self.corroboration(),
            "by_tier": dict(sorted(by_tier.items())),
            "proposed_reasons": dict(sorted(reasons.items())),
            "cluster_size_histogram": {str(k): v for k, v in sorted(sizes.items())},
            "mirror_lineages": {
                k: sorted(v) for k, v in sorted(lineage_groups.items()) if len(v) > 1
            },
        }

    def corroboration(self) -> dict[str, int]:
        """Multi-record resolved sites split by INDEPENDENT lineages (hard constraint (c)):
        a site whose members all come from one mirror lineage is one observation
        republished, never independently corroborated."""
        members: dict[str, list[str]] = defaultdict(list)
        for subject, cid in self.clusters.items():
            members[cid].append(subject)
        corroborated = mirror_only = 0
        for ms in members.values():
            if len(ms) < 2:
                continue
            lineages = {self.lineages.get(self.sources[m], self.sources[m]) for m in ms}
            if len(lineages) >= 2:
                corroborated += 1
            else:
                mirror_only += 1
        return {
            "multi_record_sites_independently_corroborated": corroborated,
            "multi_record_sites_one_lineage_only": mirror_only,
        }

    def summary(self) -> dict[str, Any]:
        auto = sum(1 for d in self.decisions if d.disposition == "auto_write")
        return {
            "rules_version": self.rules_version,
            "resolver_version": self.resolver_version,
            "run_key": self.run_key,
            "observation_count_M": self.observation_count,
            "resolved_site_count_N": self.cluster_count,
            "dedup_ratio": round(self.dedup_ratio, 6),
            "decisions": len(self.decisions),
            "auto_write_decisions": auto,
            "proposed_decisions": len(self.decisions) - auto,
            "auto_write_tiers": sorted(self.auto_write_tiers),
            "demotions": [
                {
                    "tier": d.tier,
                    "precision": round(d.precision, 4),
                    "threshold": d.threshold,
                    "demoted": d.demoted,
                }
                for d in self.demotions
            ],
            "tier_measurements": {
                str(t): {
                    "predicted": m.predicted,
                    "match": m.match,
                    "non_match": m.non_match,
                    "not_enough_information": m.not_enough_information,
                    "precision_strict": m.precision_strict,
                    "precision_decided": m.precision_decided,
                    "wilson_lower_95": m.wilson_lower_95,
                }
                for t, m in self.tier_measurements.items()
            },
            # Sensitivity only (the LLM adjudicator is not trusted as gold when kappa < bar):
            # the same holdout scored with the LLM's labels. Never used to gate auto-write.
            "tier_measurements_llm_labels": {
                str(t): {
                    "predicted": m.predicted,
                    "match": m.match,
                    "non_match": m.non_match,
                    "not_enough_information": m.not_enough_information,
                    "precision_strict": m.precision_strict,
                }
                for t, m in self.tier_measurements_llm_labels.items()
            },
            "cluster_alerts": [
                {"cluster_id": a.cluster_id, "kind": a.kind, "detail": dict(a.detail)}
                for a in self.alerts
            ],
            "blocking_candidate_pairs": self.blocking_size,
            "unblockable_records": self.unblockable,
            "incompatible_class_pairs_blocked": self.incompatible_blocked,
            "tier6_discarded": self.discarded,
            "gold_set_version": self.gold_version,
            "kappa": self.kappa,
            "gold_pairs": self.gold_size,
            "holdout_pairs": self.holdout_size,
            "disputed_pairs": self.disputed,
            **self.counts(),
        }


def _rules_digest(rules: CameraSiteRules) -> str:
    return hashlib.sha256(repr(rules).encode()).hexdigest()


def run_key(
    *,
    rules: CameraSiteRules,
    auto_write_tiers: Iterable[int],
    gold: CameraGoldSet | None,
    records: Sequence[CameraRecord],
) -> str:
    """The run identity: every input a decision depends on.

    Digests the resolver version, the FULL rules content, the gold set's content, the
    measured auto-write tiers and every field of every record (source, coordinates,
    reference, name, direction, operator, jurisdiction, type, claim ids). Two runs over
    the same inputs share a key (so the re-run is +0); ANY change a decision could depend
    on mints a new key, and readers take the latest COMPLETED run whole — never a union of
    a stale run's edges with a new one's.
    """
    h = hashlib.sha256()
    h.update(
        json.dumps(
            {
                "resolver": CAMERA_SITE_RESOLVER_VERSION,
                "rules": _rules_digest(rules),
                "auto": sorted(auto_write_tiers),
                "gold": None if gold is None else gold.content_digest(),
            },
            sort_keys=True,
        ).encode()
    )
    for r in sorted(records, key=lambda r: r.subject_id):
        fields = asdict(r)
        fields["claim_ids"] = sorted(r.claim_ids)
        h.update(json.dumps(fields, sort_keys=True, default=str).encode())
        h.update(b"\n")
    return "camsite:" + h.hexdigest()[:40]


def decision_digest(key: str, d: SiteDecision) -> str:
    """The idempotency digest of one decision row (re-run over unchanged input = +0)."""
    payload = {
        "run_key": key,
        "left": d.left,
        "right": d.right,
        "tier": d.assessment.tier,
        "disposition": d.disposition,
        "reason": d.reason,
        "claims": list(d.assessment.evidence_claims),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def resolve_camera_sites(
    records: Sequence[CameraRecord],
    *,
    gold: CameraGoldSet | None,
    threshold: float,
    rules: CameraSiteRules | None = None,
    geo_rule: GeoGridRule | None = None,
    blocking_context: BlockingContext | None = None,
) -> CameraSiteResult:
    """One camera-site ER run: block → assess → measure → decide → cluster (pure)."""
    rs = rules or CameraSiteRules.from_data()
    gr = geo_rule or load_geo_rules()[0]
    assessed = _assess(records, rules=rs, geo_rule=gr, blocking_context=blocking_context)
    # The auto-write gate measures exactly what WOULD be auto-written: a candidate-tier pair
    # with a soft conflict is routed to review whatever its tier, so it is not scored as
    # that tier (it cannot be a false auto-merge); every other pair scores at its tier.
    tier_by_pair = {
        p.key: p.tier
        for p in assessed.assessments
        if not (p.tier in rs.candidate_auto_write and p.soft_conflicts)
    }

    measured_llm: dict[int, TierMeasurement] = {}
    if gold is not None:
        measured = measure_tiers(gold, tier_by_pair)
        measured_llm = measure_tiers(gold, tier_by_pair, adjudicator=gold.llm)
        kappa: float | None = gold.kappa()
    else:
        measured, kappa = {}, None
    auto, demotions = decide_auto_write_tiers(
        measured,
        candidate_tiers=rs.candidate_auto_write,
        threshold=threshold,
        strict=rs.strict_precision,
        min_pairs=rs.min_holdout_pairs,
    )
    decisions, clusters, alerts = cluster_decisions(
        assessed.assessments, records, auto_write_tiers=auto, rules=rs
    )
    key = run_key(rules=rs, auto_write_tiers=auto, gold=gold, records=records)
    return CameraSiteResult(
        rules_version=rs.version,
        resolver_version=CAMERA_SITE_RESOLVER_VERSION,
        run_key=key,
        observation_count=len(records),
        cluster_count=len(set(clusters.values())),
        decisions=decisions,
        clusters=clusters,
        alerts=alerts,
        lineages=assessed.lineages,
        sources={r.subject_id: r.source_id for r in records},
        auto_write_tiers=auto,
        demotions=demotions,
        tier_measurements=measured,
        tier_measurements_llm_labels=measured_llm,
        blocking_size=assessed.blocking_size,
        unblockable=assessed.unblockable,
        incompatible_blocked=assessed.incompatible_blocked,
        discarded=assessed.discarded,
        gold_version=None if gold is None else gold.version,
        kappa=kappa,
        holdout_size=0 if gold is None else len(gold.holdout()),
        gold_size=0 if gold is None else len(gold.pairs),
        disputed=0 if gold is None else len(gold.disputed()),
    )
