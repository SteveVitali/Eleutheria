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
   are scored against the committed camera gold set's frozen, agent-labelled holdout;
   only a *candidate* auto-write tier whose measured (strict) holdout precision clears
   the published floor auto-writes — a tier with no holdout evidence never does
   (SIG-IDENT-028, ADR-099). Under ruleset v3-interim (P34.45 / ADR-153 "derivation,
   not identity") an identity-*inference* tier additionally needs an independent
   human (B5) evaluation certifying it — the agent/LLM-labelled gold set can never
   provide one, so every inferential tier is review-only until then; the namespace
   join ``1g:shared_upstream_ref`` is a derivation, not an inference, and stays
   eligible.
4. **Clustering** — :func:`cluster_decisions`: auto-write edges are applied
   strongest-first under hard constraints (no two records of one source in a cluster,
   bounded span, bounded size); a refused union and every sub-floor tier become
   PROPOSED decisions for human review. Cluster-shape alerts (chaining along a road,
   oversized clusters, single-bridge joins) demote an alerted cluster's auto edges to
   review (SIG-IDENT-029).
5. **Human review (P31.11 / ADR-R9-HUMANER)** — the run consumes the append-only
   ``review_decision`` history for ``er_match:camera_site*`` items, folded by
   :func:`fold_human_verdicts` into one :class:`HumanVerdict` per pair. An
   *accept* applies as a ``human_accept`` edge (``decided_by`` = the curator),
   a *reject* is recorded as a hard ``cannot_link`` (``human_reject``), and a
   *conflict* between curators stays proposed and is routed back to review.
   A human verdict outranks the automatic outcome on the same pair, and an
   accepted edge that would violate a hard constraint is recorded ``refused``,
   never silently applied. Zero decisions leave the run byte-identical in
   outcome to the pre-wiring pipeline.
6. **Duplicate targets** — :func:`infer_duplicate_targets` records target-level
   lineage: two records of ONE source whose captured content digests are
   identical (or whose rows are identical) are the same upstream row
   republished under two targets — the *only* exception to constraint (a).

**Hard constraints (test-pinned).** (a) Two records of the *same source* are never
merged — not as a pair and not transitively through a cluster: a source listing two
cameras at one spot lists two devices. The sole exception is evidenced
duplicate-target lineage (:func:`infer_duplicate_targets`): identical capture
digests or row-identical records prove the source republished its own row, so the
pair is the same record, not two devices. (b) Records of incompatible device classes
(the recorded matrix in ``camera_site_rules.toml``) are never candidates, and a soft
conflict (differing resolved jurisdiction or explicit device type) can never
auto-write — a human accept may still apply it, since review exists to decide
exactly those. (c) A mirror of the same upstream dataset is not independent
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
import random
import tomllib
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field, is_dataclass, replace
from dataclasses import fields as dc_fields
from datetime import date, datetime
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
    "HumanItem",
    "HumanVerdict",
    "HumanVote",
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
    "declared_device_class",
    "DeviceClassFinding",
    "device_class_findings",
    "LineageFinding",
    "UNCLASSIFIED",
    "fold_human_verdicts",
    "infer_duplicate_targets",
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
#: 1.1.0 — P31.11: consumes human review verdicts and duplicate-target lineage.
#: 1.2.0 — P35.15a / PKG-07: device class comes from the subject's declared
#:   `technology` slug first; the substring rules are a legacy-only fallback,
#:   and declared-vs-substring disagreements are recorded findings.
#: 1.3.0 — P35.25 / SIG-CONF-014: declared independence classes seed lineage
#:   groups (measured coincidence can only union), undeclared sources share the
#:   `unclassified` voice and can never corroborate, the shared-upstream-ref
#:   tier requires a declared-namespace match, and undeclared copy unions are
#:   disclosed as lineage findings (GQ-11).
CAMERA_SITE_RESOLVER_VERSION = "camera-sites/1.3.0"

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
    #: P35.25 (SIG-CONF-014, NEW-1): the DECLARED identifier namespace
    #: ``external_ref`` lives in (``claim_lineage.id_namespace`` — a shared
    #: upstream id space like ``osm.element``, a source-private ``src:<id>``
    #: space, or ``undeclared``). The shared-upstream-ref tier credits a ref
    #: match ONLY inside one declared namespace: a bare equal string across
    #: namespaces is a coincidence, never shared-upstream evidence.
    id_namespace: str | None = None
    name: str | None = None
    roadway: str | None = None
    direction: str | None = None
    operator: str | None = None
    jurisdiction: str | None = None
    camera_type: str | None = None
    #: P35.15a / PKG-07 (NEW-7 / FM-05): the subject's declared SKOS technology
    #: slug — the latest ``technology`` claim value, the connector's
    #: target-declared classification. ``None`` marks a legacy record that
    #: predates P35.15a's declaration requirement; its class falls back to the
    #: substring rules and the run counts it under
    #: ``records_without_declared_technology``.
    technology: str | None = None
    #: Every DISTINCT current ``technology`` value the subject asserts
    #: (``technology`` is a multi-cardinality predicate). Size > 1 marks a
    #: subject whose declared subtypes MIX — reported by the run, never coerced
    #: to one; ``technology`` still carries the latest claim's value for class
    #: derivation (the shared temporal contract every other field follows).
    declared_technologies: tuple[str, ...] = ()
    claim_ids: tuple[str, ...] = ()
    #: P31.11 target-level lineage (ADR-R9-HUMANER): the connector fetch target
    #: this record's subject was minted under (``traffic_camera:<src>:<target>``
    #: in the ``sig.connector.subject`` identifier) and the ``content_digest``s
    #: of the captures its claims cite — the evidence that proves two targets of
    #: one source republished the same row.
    target_id: str | None = None
    capture_digests: tuple[str, ...] = ()
    #: P32.4 (ADR-123): the *atomic* coordinate pair's own occurrence — the
    #: latest capture that established BOTH selected coordinate claims (the
    #: pair is one source-record occurrence, never lat from capture X and lon
    #: from capture Y). ``None`` when the axes were never asserted together —
    #: such a record keeps no point.
    coordinate_capture_id: str | None = None
    coordinate_retrieved_at: datetime | None = None
    #: P35.16 (R11-DATA-01 / F-322): the defect classes current
    #: ``geometry_defect`` claims mark on this subject (``axis_swap``,
    #: ``null_island``, ``sign_flip``, ``wrong_jurisdiction``). An
    #: ``axis_swap`` flag makes the record never a collapse input — a
    #: suspected transposed point cannot prove a copy — until the P35.16
    #: correction lands (``coordinate_correction == "axis_swap"``).
    geometry_defects: tuple[str, ...] = ()
    #: The ``correction_reason`` the record's current coordinate pair carries
    #: (``axis_swap`` when the P35.16 correction claims are the selected
    #: values); ``None`` for an uncorrected pair.
    coordinate_correction: str | None = None

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
class _TechnologyRule:
    """P35.15a / PKG-07: a declared SKOS technology slug prefix -> device class.

    Ordered like ``class_rules``: first matching prefix wins. A slug equal to a
    prefix, or beginning ``prefix + "-"``, matches (``alpr-fixed`` classes under
    the ``alpr`` rule)."""

    name: str
    slug_prefixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class CameraSiteRules:
    """The versioned camera-site rules (``camera_site_rules.toml``), injectable in tests."""

    version: str = "1"
    coincident_m: float = 1.0
    #: P35.46 (ruleset v3): the measured copy tolerance a derivation collapse
    #: must sit inside (GQ-23) — M-3's empirical value until CONF-09 re-derives
    #: it; the coincident bound stands in.
    copy_tolerance_m: float = 1.0
    colocation_m: float = 5.0
    near_max_m: float = 25.0
    candidate_max_m: float = 50.0
    candidate_auto_write: frozenset[int] = frozenset({1})
    #: P35.46 (ruleset v3, ADR-153/ADR-L3-B): the derivation-collapse tiers —
    #: C0 duplicate target, C1 namespaced copy, C2 position-matched copy. These
    #: are the only tiers that may collapse automatically (the SIG-EVAL-004
    #: waiver scope); the GQ-23 census replaces the eval gate for them.
    collapse_tiers: frozenset[int] = frozenset({0, 1, 2})
    #: Identity-inference tiers (GQ-24's locked set; ADR-153): review-only until
    #: an independent human (B5) evaluation certifies the tier — the agent/LLM
    #: gold set can never certify one. A fail-closed default, never derived from
    #: the auto-write list.
    inferential_tiers: frozenset[int] = frozenset({3, 4, 5})
    #: Q-L3-6 = a: position-matched copies inside documented mirror lineages
    #: may collapse (C2). Flipped false, every C2 pair is a possible duplicate.
    c2_enabled: bool = True
    #: The measured copy overlap a documented lineage must reach before C2
    #: applies (coincident records covering this share of the smaller source,
    #: on at least ``lineage_min_pairs`` evidence).
    c2_min_overlap: float = 0.9
    #: The M-1b quarterly seeded draw per declared namespace (sample frame
    #: emitted each run; the upstream GET leg is CONF-09's named scope).
    m1b_sample_size: int = 200
    tier_labels: Mapping[int, str] = field(
        default_factory=lambda: {
            1: "C1:namespaced_copy",
            2: "C2:position_matched_copy",
            3: "P3:coincident_point",
            4: "P4:proximate_unique",
            5: "P5:proximate_candidate",
        }
    )
    default_class: str = "unspecified"
    class_rules: tuple[_ClassRule, ...] = ()
    #: P35.15a / PKG-07: the declared-technology rules consulted FIRST — a record
    #: carrying a ``technology`` claim classes by its slug prefix; the substring
    #: ``class_rules`` remain only as the legacy fallback for records that carry
    #: no declaration (pre-backfill spine rows).
    technology_rules: tuple[_TechnologyRule, ...] = ()
    incompatible_classes: frozenset[frozenset[str]] = frozenset()
    soft_conflict_fields: tuple[str, ...] = ("jurisdiction", "camera_type")
    unresolved_jurisdictions: frozenset[str] = frozenset({"unresolved", "", "unknown"})
    direction_conflict_deg: float = 90.0
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
            copy_tolerance_m=float(dist.get("copy_tolerance_m", dist["coincident_m"])),
            colocation_m=float(dist["colocation_m"]),
            near_max_m=float(dist["near_max_m"]),
            candidate_max_m=float(dist["candidate_max_m"]),
            candidate_auto_write=frozenset(int(t) for t in d["tiers"]["candidate_auto_write"]),
            inferential_tiers=frozenset(int(t) for t in d["tiers"].get("inferential", (3, 4, 5))),
            c2_enabled=bool(d["tiers"].get("c2_enabled", True)),
            c2_min_overlap=float(d["lineage"].get("c2_min_overlap", 0.9)),
            m1b_sample_size=int(d.get("census", {}).get("m1b_sample_size", 200)),
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
            technology_rules=tuple(
                _TechnologyRule(
                    name=str(r["class"]),
                    slug_prefixes=tuple(str(p).lower() for p in r.get("technology_prefixes", ())),
                )
                for r in classes.get("technology_rule", ())
            ),
            incompatible_classes=frozenset(frozenset(p) for p in classes["incompatible"]),
            soft_conflict_fields=tuple(d["soft_conflicts"]["fields"]),
            unresolved_jurisdictions=frozenset(
                str(v).lower() for v in d["soft_conflicts"]["unresolved_jurisdictions"]
            ),
            direction_conflict_deg=float(d["soft_conflicts"]["direction_conflict_deg"]),
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


def _substring_class(record: CameraRecord, rules: CameraSiteRules) -> str:
    """The pre-P35.15a heuristic class: first matching source/operator/type
    substring rule, else the default. Retained ONLY as the fallback for records
    carrying no declared technology (pre-P35.15b-backfill rows) and as the
    comparison arm of :func:`device_class_findings` — never to classify a
    declared record."""
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


def declared_device_class(record: CameraRecord, rules: CameraSiteRules) -> str | None:
    """The device class the record's DECLARED technology slug implies, or ``None``
    when the record carries no declaration (legacy row — the substring rules
    decide). A declared slug matching no ``technology_rule`` is the default
    class — never ``None``, so a declaration always owns the classification."""
    slug = (record.technology or "").strip().lower()
    if not slug:
        slug = next(
            ((t or "").strip().lower() for t in record.declared_technologies if (t or "").strip()),
            "",
        )
    if not slug:
        return None
    for rule in rules.technology_rules:
        if any(slug == p or slug.startswith(p + "-") for p in rule.slug_prefixes):
            return rule.name
    return rules.default_class


def device_class(record: CameraRecord, rules: CameraSiteRules) -> str:
    """The recorded device class of ``record``.

    P35.15a / PKG-07 (NEW-7 / FM-05): the subject's DECLARED technology slug is
    authoritative — a record carrying a ``technology`` claim classes by the
    ``technology_rule`` table. Only a record with no declaration falls back to
    the legacy substring rules (the spine's pre-backfill rows); the class a
    substring would have produced never overrides a declaration — a
    disagreement is surfaced by :func:`device_class_findings` instead."""
    declared = declared_device_class(record, rules)
    if declared is not None:
        return declared
    return _substring_class(record, rules)


@dataclass(frozen=True)
class DeviceClassFinding:
    """P35.15a: a declared-technology audit finding — recorded, never silently
    coerced.

    ``declared_substring_mismatch`` — the subject's declared class DISAGREES
    with the non-default class the legacy substring rules would have given it
    (the declaration wins classification; the finding keeps the disagreement
    visible).

    ``multiple_declared_technologies`` — the subject asserts more than one
    current ``technology`` claim value (a subject whose declared subtypes mix;
    the multi-cardinality predicate permits it, so it is reported rather than
    reconciled)."""

    kind: str
    subject_id: str
    technologies: tuple[str, ...]
    declared_class: str
    substring_class: str
    matched_by: str  # which legacy signal disagreed: source/operator/camera_type/default


def device_class_findings(
    records: Sequence[CameraRecord], rules: CameraSiteRules
) -> tuple[DeviceClassFinding, ...]:
    """Declared-technology audit findings over the run's records.

    A ``declared_substring_mismatch`` finding is emitted only when a record
    declares a technology AND the substring rules would have classed it as a
    DIFFERENT, non-default class — the substring rules having no opinion
    (``default_class``) on a declared record is the expected NEW-7 coverage
    gap, not a disagreement. A ``multiple_declared_technologies`` finding marks
    a subject asserting more than one current technology slug.
    """
    out: list[DeviceClassFinding] = []
    for r in records:
        declared_values = tuple(
            sorted(
                {(t or "").strip().lower() for t in r.declared_technologies if (t or "").strip()}
            )
        )
        slug = (r.technology or "").strip()
        if not slug and not declared_values:
            continue  # no declaration at all — the legacy/undeclared path
        declared = declared_device_class(r, rules)
        assert declared is not None  # a declaration always resolves a class
        if len(declared_values) > 1:
            out.append(
                DeviceClassFinding(
                    kind="multiple_declared_technologies",
                    subject_id=r.subject_id,
                    technologies=declared_values,
                    declared_class=declared,
                    substring_class="",
                    matched_by="claim",
                )
            )
        heuristic = _substring_class(r, rules)
        if heuristic == rules.default_class or heuristic == declared:
            continue
        # Which legacy signal fired — recorded, so the disagreement is auditable.
        source = r.source_id.lower()
        operator = (r.operator or "").lower()
        camera_type = (r.camera_type or "").lower()
        matched_by = "default"
        for rule in rules.class_rules:
            if rule.name != heuristic:
                continue
            if any(source.startswith(p) for p in rule.source_prefixes) or any(
                s in source for s in rule.source_substrings
            ):
                matched_by = "source_id"
            elif any(s in operator for s in rule.operator_substrings):
                matched_by = "operator"
            elif any(s in camera_type for s in rule.type_substrings):
                matched_by = "camera_type"
            break
        out.append(
            DeviceClassFinding(
                kind="declared_substring_mismatch",
                subject_id=r.subject_id,
                technologies=declared_values or (slug,),
                declared_class=declared,
                substring_class=heuristic,
                matched_by=matched_by,
            )
        )
    return tuple(out)


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
    if "device_kind" in rules.soft_conflict_fields:
        # P35.46 / P35.15b: the declared-technology half of the device-kind
        # conflict — both records declare a technology and their declared
        # classes differ (compatible-but-different kinds; outright
        # incompatible pairs are never candidates). A record without a
        # declaration cannot conflict — the description-parsing half stays
        # D-P30.2b-2.
        ka, kb = declared_device_class(a, rules), declared_device_class(b, rules)
        if ka is not None and kb is not None and ka != kb:
            out.append("device_kind")
    return tuple(out)


def _valid_point(r: CameraRecord) -> bool:
    if r.latitude is None or r.longitude is None:
        return False
    return not (r.latitude == 0.0 and r.longitude == 0.0)


def axis_swap_suspected(r: CameraRecord) -> bool:
    """P35.46: a point flagged ``axis_swap`` (P35.16's ``geometry_defect``
    claim) is never a collapse input — a suspected transposed pair cannot
    prove a copy — until the recorded correction lands: when the record's
    current coordinate pair IS the ``axis_swap`` correction the flag stands
    resolved (the defect claim remains as the immutable marking)."""
    return "axis_swap" in r.geometry_defects and r.coordinate_correction != "axis_swap"


# --------------------------------------------------------------------------- #
# Lineage (mirror) inference                                                   #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class LineageFinding:
    """A lineage fact the data shows but no declaration backs (P35.25 / GQ-11,
    SIG-EPIS-029). ``undeclared_overlap`` = two sources measurably republish one
    upstream with no shared declared class (the copy detector's flag); a
    ``cross_declared_overlap`` = two sources declared to DIFFERENT classes that
    measure as copies — the declarations and the data disagree, disclosed both
    ways (the measured union still stands: one voice, and the contradiction
    stays visible)."""

    kind: str  # undeclared_overlap | cross_declared_overlap
    sources: tuple[str, str]
    coincident_pairs: int
    share: float


@dataclass(frozen=True)
class LineageDeclaration:
    """P35.46 (ruleset v3): one source's declared lineage record, from
    ``source_lineage_current`` — the resolved ``independence_class`` plus the
    declared ``kind`` (``primary`` / ``mirror`` / ``derived`` / ``syndicated``
    / ``undeclared``) and the documentary ``evidence`` of the declaration.
    C1 requires the pair's shared class to be a DECLARED COPY lineage (a
    mirror/derived member); C2 additionally requires that copy declaration to
    carry documentary evidence."""

    independence_class: str = "unclassified"
    kind: str = "undeclared"
    evidence: str = ""


#: The pseudo-class token undeclared sources resolve to under declared mode —
#: shared by every undeclared source, so undeclared material is never counted
#: as independent corroboration (SIG-CONF-014).
UNCLASSIFIED = "unclassified"

#: A ``source_lineage`` ``kind`` that declares this source republishes an
#: upstream — the declaration that makes a shared independence class a
#: *copy* lineage (C1) and, with documentary evidence, a *documented* one (C2).
_COPY_KINDS = frozenset({"mirror", "derived"})


@dataclass(frozen=True)
class CensusFailure:
    """One applied collapse edge whose GQ-23 census re-verification failed."""

    left: str
    right: str
    tier: int
    token: str  # the demoted unit: shared source (C0) or shared lineage (C1/C2)
    reason: str


@dataclass(frozen=True)
class DerivationCensus:
    """The GQ-23 derivation census of one run (P35.46).

    Every applied collapse edge (an ``auto_write`` at a collapse tier) is
    re-checked against the run's record set: C0 re-derives its row identity,
    C1 re-derives ref equality + declared namespace + capture uniqueness +
    copy lineage + tolerance, C2 re-derives the documented lineage + measured
    overlap + within-colocation bijection. A failure DEMOTES that
    ``(lineage-or-source, tier)`` for the NEXT run — the demotion set this run
    consumed (``demoted_collapses`` on the result) is the previous run's
    output, so a stale declaration can only collapse for one run.

    ``origin_distinct_violations`` counts resolved clusters violating GQ-25 —
    two members carrying DIFFERENT normalised ids in ONE declared namespace
    (the origin publisher lists them as distinct). Always a subset; the
    cluster refusal prefers rejecting the union upstream of this count.
    """

    checked: int
    failures: tuple[CensusFailure, ...]
    demote_next_run: tuple[tuple[str, int], ...]
    origin_distinct_violations: int
    origin_distinct_clusters: tuple[str, ...]


def _union_find(
    records: Sequence[CameraRecord],
) -> tuple[dict[str, int], Any, Any]:
    size: dict[str, int] = defaultdict(int)
    for r in records:
        size[r.source_id] += 1
    parent: dict[str, str] = {s: s for s in size}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            lo, hi = sorted((ra, rb))
            parent[hi] = lo

    return size, find, union


def _measured_overlap(
    records: Sequence[CameraRecord],
    coincident_pairs: Iterable[tuple[int, int]],
    size: Mapping[str, int],
) -> dict[tuple[str, str], tuple[int, float]]:
    """The raw measured copy overlap per unordered source pair:
    ``(sa, sb) -> (coincident pair count, share of the smaller source)`` —
    ungated; the lineage rule and the C2 floor apply their own thresholds."""
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
    out: dict[tuple[str, str], tuple[int, float]] = {}
    for (sa, sb), (left, right) in sorted(covered.items()):
        pairs = min(len(left), len(right))
        smaller = min(size[sa], size[sb])
        if smaller:
            out[(sa, sb)] = (pairs, pairs / smaller)
    return out


def _measured_unions(
    records: Sequence[CameraRecord],
    coincident_pairs: Iterable[tuple[int, int]],
    rules: CameraSiteRules,
    size: Mapping[str, int],
) -> dict[tuple[str, str], tuple[int, float]]:
    """Source pairs whose measured coincidence meets the lineage rule:
    ``(sa, sb) -> (coincident pair count, share of the smaller source)``."""
    return {
        key: value
        for key, value in _measured_overlap(records, coincident_pairs, size).items()
        if value[0] >= rules.lineage_min_pairs and value[1] >= rules.lineage_min_share
    }


def _copy_and_documented_lineages(
    lineages: Mapping[str, str],
    declared_details: Mapping[str, LineageDeclaration] | None,
) -> tuple[frozenset[str], frozenset[str]]:
    """The declared-lineage sets the collapse tiers gate on (P35.46).

    ``copy_lineages`` — declared independence classes a ``mirror``/``derived``
    kind declaration names (a declared copy lineage; C1's gate). ``documented``
    — the subset whose copy declaration carries documentary evidence (C2's
    gate; "the mirror's own metadata names its origin"). With a declared-class
    map but no details the kind/documentary tests are unavailable: every
    declared class counts as a copy lineage (the map itself is the
    declaration) and none is documented — C2 then cannot fire. With no
    declared map at all both sets are empty: undeclared material never
    collapses."""
    if declared_details is not None:
        classes: dict[str, list[LineageDeclaration]] = defaultdict(list)
        for source, cls in lineages.items():
            if cls != UNCLASSIFIED:
                details = declared_details.get(source)
                if details is not None:
                    classes[cls].append(details)
        copy = frozenset(
            cls for cls, ds in classes.items() if any(d.kind in _COPY_KINDS for d in ds)
        )
        documented = frozenset(
            cls
            for cls, ds in classes.items()
            if any(d.kind in _COPY_KINDS and d.evidence.strip() for d in ds)
        )
        return copy, documented
    declared = {cls for cls in lineages.values() if cls != UNCLASSIFIED}
    return frozenset(declared), frozenset()


def infer_lineages(
    records: Sequence[CameraRecord],
    coincident_pairs: Iterable[tuple[int, int]],
    rules: CameraSiteRules,
    *,
    declared: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Group sources into lineages: republications of one upstream dataset.

    Two sources are one lineage when at least ``lineage_min_pairs`` of their records
    are coincident AND the coincident records cover at least ``lineage_min_share`` of
    the smaller source (data-generated, re-derived every run). Returns
    ``source_id -> lineage_id`` (the lexicographically smallest source of its lineage);
    a source that mirrors nothing is its own lineage.

    P35.25 (SIG-CONF-014): ``declared`` maps source -> resolved independence
    class (``db.claim_lineage.independence_class`` / ``source_lineage_current``).
    When given, the DECLARED classes are the lineage seeds — sources sharing a
    declared class union even below the measured threshold, and the lineage id
    is the declared class token, so a mirror/derived source can never read as
    its own independent voice. A source with no declared class (absent or
    ``unclassified``) unions into a group only by measured evidence and reports
    the shared ``unclassified`` token when no declared class anchors the group:
    undeclared material is one disclosed voice, never independent corroboration.
    When ``declared`` is ``None`` the legacy measured-only behaviour stands.
    """
    lineages, _findings = _infer_lineages(records, coincident_pairs, rules, declared)
    return lineages


def _infer_lineages(
    records: Sequence[CameraRecord],
    coincident_pairs: Iterable[tuple[int, int]],
    rules: CameraSiteRules,
    declared: Mapping[str, str] | None,
) -> tuple[dict[str, str], tuple[LineageFinding, ...]]:
    size, find, union = _union_find(records)
    measured = _measured_unions(records, coincident_pairs, rules, size)

    findings: list[LineageFinding] = []
    if declared is not None:
        # Declared seeds first: sources sharing a declared independence class
        # are one lineage by declaration, whatever the measured overlap is.
        by_class: dict[str, list[str]] = defaultdict(list)
        for s in size:
            cls = declared.get(s) or UNCLASSIFIED
            if cls != UNCLASSIFIED:
                by_class[cls].append(s)
        for members in by_class.values():
            for m in members[1:]:
                union(members[0], m)
        # GQ-11: a measured copy union with no shared declared class is
        # detected undeclared copying (or a declared-class contradiction).
        for (sa, sb), (pairs, share) in measured.items():
            ca = declared.get(sa) or UNCLASSIFIED
            cb = declared.get(sb) or UNCLASSIFIED
            if ca == cb and ca != UNCLASSIFIED:
                continue  # the declaration already explains this copy
            kind = (
                "cross_declared_overlap"
                if ca != UNCLASSIFIED and cb != UNCLASSIFIED
                else "undeclared_overlap"
            )
            findings.append(
                LineageFinding(
                    kind=kind,
                    sources=(sa, sb),
                    coincident_pairs=pairs,
                    share=round(share, 4),
                )
            )

    for sa, sb in measured:
        union(sa, sb)

    if declared is None:
        return {s: find(s) for s in sorted(size)}, ()

    # Token per group: the shared declared class; conflicting declared classes
    # inside one measured union keep the smallest token (still ONE voice — the
    # contradiction is the finding above); a group with no declared class at
    # all is the shared ``unclassified`` pseudo-lineage.
    groups: dict[str, list[str]] = defaultdict(list)
    for s in size:
        groups[find(s)].append(s)
    out: dict[str, str] = {}
    for members in groups.values():
        classes = sorted(
            {declared[m] for m in members if declared.get(m) and declared[m] != UNCLASSIFIED}
        )
        token = classes[0] if classes else UNCLASSIFIED
        for m in members:
            out[m] = token
    return out, tuple(findings)


# --------------------------------------------------------------------------- #
# Human review verdicts (P31.11 / ADR-R9-HUMANER)                              #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class HumanItem:
    """A camera-site review item bound to a pair (``payload.left``/``right``)."""

    item_id: str
    left: str
    right: str
    tier: int | None = None  # the tier the proposing run recorded (for display)
    tier_label: str | None = None


@dataclass(frozen=True)
class HumanVote:
    """One append-only ``review_decision`` row for a camera-site item."""

    item_id: str
    decision: str  # "accept" | "reject" (the schema's whole vocabulary)
    reviewer: str  # the pseudonymous curator id (SIG-IDENT-026)
    decided_at: str  # the DB-stamped timestamp (ordering only)


@dataclass(frozen=True)
class HumanVerdict:
    """The folded human verdict over one pair of camera records.

    ``verdict`` is ``accept`` / ``reject`` / ``conflict``; ``decided_by`` is the
    governing item's reviewer(s); ``items`` is the per-item audit trail
    (``(item_id, item_verdict)`` in decided order) and ``decided_at`` the
    governing decision's timestamp.
    """

    left: str
    right: str
    verdict: str
    decided_by: str
    items: tuple[tuple[str, str], ...]
    decided_at: str
    tier: int | None = None
    tier_label: str | None = None

    @property
    def key(self) -> tuple[str, str]:
        return (self.left, self.right)


def _item_verdict(votes: Sequence[HumanVote]) -> str:
    """One item's verdict: accept iff every decision accepts, reject iff every
    decision rejects, else ``conflict`` (the append-only history disagrees)."""
    values = {v.decision for v in votes}
    if values == {"accept"}:
        return "accept"
    if values == {"reject"}:
        return "reject"
    return "conflict"


def fold_human_verdicts(
    items: Sequence[HumanItem],
    votes: Sequence[HumanVote],
) -> tuple[HumanVerdict, ...]:
    """Fold the append-only decision history into one verdict per pair.

    Both camera-site item families (``er_match:camera_site:`` proposals and the
    ``er_match:camera_site_disputed:`` routing) bind a pair; the PAIR is what
    clustering judges. A pair's verdict is the verdict of its most recently
    decided item — so a conflicted proposal routed back to a disputed item can
    be resolved by a later clean adjudication there — while a governing item
    whose own history mixes accept and reject stays ``conflict`` (routed back).
    A decision on an item that does not bind a pair is never invented into one.
    """
    votes_by_item: dict[str, list[HumanVote]] = defaultdict(list)
    for v in votes:
        votes_by_item[v.item_id].append(v)
    items_by_pair: dict[tuple[str, str], list[HumanItem]] = defaultdict(list)
    for it in items:
        if it.item_id in votes_by_item:
            key = (it.left, it.right) if it.left < it.right else (it.right, it.left)
            items_by_pair[key].append(it)
    out: list[HumanVerdict] = []
    for (left, right), pair_items in sorted(items_by_pair.items()):
        folded: list[tuple[HumanItem, str, str, tuple[str, ...]]] = []
        for it in sorted(pair_items, key=lambda i: i.item_id):
            iv = sorted(votes_by_item[it.item_id], key=lambda v: v.decided_at)
            folded.append(
                (
                    it,
                    _item_verdict(iv),
                    iv[-1].decided_at,
                    tuple(sorted({v.reviewer for v in iv})),
                )
            )
        # The most recently decided item governs (a routed-back adjudication
        # supersedes an earlier conflicted proposal); a timestamp tie between
        # disagreeing items is itself a conflict (never a coin-flip).
        folded.sort(key=lambda f: (f[2], f[0].item_id))
        latest_at = folded[-1][2]
        top = [f for f in folded if f[2] == latest_at]
        if len({f[1] for f in top}) > 1:
            gov_item, gov = top[-1][0], "conflict"
        else:
            gov_item, gov = top[-1][0], top[-1][1]
        reviewers = sorted({r for f in folded for r in f[3]})
        decided_by = ", ".join(
            next(f[3] for f in folded if f[0] is gov_item) if gov != "conflict" else reviewers
        )
        out.append(
            HumanVerdict(
                left=left,
                right=right,
                verdict=gov,
                decided_by=decided_by,
                items=tuple((f[0].item_id, f[1]) for f in folded),
                decided_at=latest_at,
                tier=gov_item.tier,
                tier_label=gov_item.tier_label,
            )
        )
    return tuple(out)


# --------------------------------------------------------------------------- #
# Duplicate-target lineage (P31.11 / ADR-R9-HUMANER; closes D-P30.2b-3)        #
# --------------------------------------------------------------------------- #


def _norm_text(value: str | None) -> str:
    return str(value).strip().lower() if value else ""


def _row_fingerprint(r: CameraRecord) -> tuple[Any, ...]:
    """The record's row identity: every compared field, normalised."""
    return (
        normalize_ref(r.external_ref),
        r.latitude,
        r.longitude,
        _norm_text(r.name),
        _norm_text(r.roadway),
        _norm_text(r.direction),
        _norm_text(r.operator),
        _norm_text(r.jurisdiction),
        _norm_text(r.camera_type),
    )


def infer_duplicate_targets(records: Sequence[CameraRecord]) -> dict[str, str]:
    """Records that are the SAME upstream row republished under another target.

    Returns ``subject_id -> group root subject_id`` for every member of a
    duplicate group of size >= 2 (the root maps to itself). Two records of one
    source join one group only with evidence (ADR-R9-HUMANER, the sole exception
    to constraint (a)):

    * **row-identical** — the whole projected row is identical (normalised
      reference, coordinate pair, and every compared attribute), and the row
      carries an identifying field (a reference or a name) so two content-free
      coordinate stubs never qualify; or
    * **identical captured content** — the records' targets are PROVEN
      duplicate (their cited captures share a ``content_digest``, i.e. the two
      fetches returned byte-identical content) and the records share the same
      normalised upstream reference — the same row key under byte-identical
      targets, surviving trivial per-run parse differences.

    Genuinely distinct devices at one point — different references or any
    differing field — never group: they stay the separate records constraint
    (a) demands.
    """
    by_source: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(records):
        by_source[r.source_id].append(i)

    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            lo, hi = sorted((ra, rb))
            parent[hi] = lo

    def union_group(idxs: list[int]) -> None:
        for j in idxs[1:]:
            union(records[idxs[0]].subject_id, records[j].subject_id)

    # Evidence path 1 — row-identical: bucket each source's records by their
    # row fingerprint; identical rows (with an identifying field) are the same
    # republished row. Bucketed, never pairwise — a source may carry tens of
    # thousands of records.
    for source in sorted(by_source):
        buckets: dict[tuple[Any, ...], list[int]] = defaultdict(list)
        for i in by_source[source]:
            buckets[_row_fingerprint(records[i])].append(i)
        for fp, grp in buckets.items():
            if len(grp) >= 2 and (fp[0] is not None or bool(fp[3])):
                union_group(sorted(grp))

    # Evidence path 2 — identical captured content across DISTINCT targets:
    # (source, ref) buckets hold the records carrying that normalised upstream
    # reference, keyed by target; two records group only when their targets are
    # proven byte-identical (share a cited content_digest).
    digests_by_target: dict[tuple[str, str], set[str]] = defaultdict(set)
    ref_buckets: dict[tuple[str, str], dict[str, list[int]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for i, r in enumerate(records):
        if r.target_id:
            digests_by_target[(r.source_id, r.target_id)].update(r.capture_digests)
            ref = normalize_ref(r.external_ref)
            if ref is not None:
                ref_buckets[(r.source_id, ref)][r.target_id].append(i)
    for (source, _ref), by_target in sorted(ref_buckets.items()):
        if len(by_target) < 2:
            continue
        # bucket member records by each cited digest of their target
        by_digest: dict[str, list[int]] = defaultdict(list)
        for target, idxs in by_target.items():
            for digest in digests_by_target.get((source, target), ()):
                by_digest[digest].extend(idxs)
        for idxs in by_digest.values():
            # a digest shared across >=2 DISTINCT targets proves the targets
            # byte-identical — members are the same row republished.
            if len({records[i].target_id for i in idxs}) >= 2:
                union_group(sorted(idxs))

    members: dict[str, list[str]] = defaultdict(list)
    for r in records:
        if r.subject_id in parent:
            members[find(r.subject_id)].append(r.subject_id)
    out: dict[str, str] = {}
    for root, ms in members.items():
        if len(ms) >= 2:
            root = min(ms)
            for m in ms:
                out[m] = root
    return out


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
    duplicate_groups: dict[str, str]  # subject -> dup-group root (P31.11)
    blocking_size: int
    unblockable: int
    incompatible_blocked: int
    discarded: int
    lineage_findings: tuple[LineageFinding, ...] = ()  # P35.25 GQ-11 detections
    # P35.46 (ruleset v3): the collapse inputs the census re-verifies.
    ref_counts: dict[tuple[str, str], int] = field(default_factory=dict)
    measured_overlaps: dict[tuple[str, str], tuple[int, float]] = field(default_factory=dict)
    copy_lineages: frozenset[str] = frozenset()
    documented_lineages: frozenset[str] = frozenset()
    colocation_counts: dict[str, dict[str, int]] = field(default_factory=dict)


def _neighbour_index(
    records: Sequence[CameraRecord],
    pairs: Sequence[tuple[int, int, float]],
    eff: Mapping[int, str],
) -> dict[int, dict[str, list[tuple[float, int]]]]:
    """record index -> other source -> [(distance, index)] nearest-first (within radius).

    Duplicate-target members of one source count as ONE record (the nearest
    member stands for the group): a republished row must not count twice
    against the one-to-one rules (ADR-R9-HUMANER).
    """
    by_source: dict[int, dict[str, list[tuple[float, int]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for i, j, d in pairs:
        by_source[i][records[j].source_id].append((d, j))
        by_source[j][records[i].source_id].append((d, i))
    for per in by_source.values():
        for source, lst in per.items():
            lst.sort()
            seen: set[str] = set()
            deduped: list[tuple[float, int]] = []
            for d, j in lst:
                e = eff[j]
                if e in seen:
                    continue  # another member of the same duplicate group
                seen.add(e)
                deduped.append((d, j))
            per[source] = deduped
    return by_source


def _count_within(neigh: list[tuple[float, int]], radius: float) -> int:
    return sum(1 for d, _ in neigh if d <= radius)


def _assess(
    records: Sequence[CameraRecord],
    *,
    rules: CameraSiteRules,
    geo_rule: GeoGridRule,
    blocking_context: BlockingContext | None,
    declared: Mapping[str, str] | None = None,
    declared_details: Mapping[str, LineageDeclaration] | None = None,
) -> _Assessed:
    block_records = [r.block_record() for r in records]
    index_pairs = validate_geo_rule(block_records, geo_rule, context=blocking_context)
    unblockable = sum(1 for br in block_records if geo_rule.cell(br) is None)

    # P31.11: evidence-based within-source duplicate-target lineage first — it
    # defines each record's effective identity (subject, or its dup-group root)
    # for the one-to-one counts and constraint (a) below.
    dup_groups = infer_duplicate_targets(records)
    eff: dict[int, str] = {
        i: dup_groups.get(records[i].subject_id, records[i].subject_id) for i in range(len(records))
    }

    within: list[tuple[int, int, float]] = []
    for i, j in index_pairs:
        a, b = records[i], records[j]
        if a.source_id == b.source_id or not (_valid_point(a) and _valid_point(b)):
            continue  # hard constraint (a) — defence in depth behind the blocking rule
        d = haversine_m(a.latitude, a.longitude, b.latitude, b.longitude)  # type: ignore[arg-type]
        if d <= rules.candidate_max_m:
            within.append((i, j, d))

    coincident = [(i, j) for i, j, d in within if d <= rules.coincident_m]
    lineages, lineage_findings = _infer_lineages(records, coincident, rules, declared)
    neigh = _neighbour_index(records, within, eff)
    classes = [device_class(r, rules) for r in records]

    # P35.46 (ruleset v3): the collapse inputs — the declared copy/documented
    # lineage sets, the measured copy overlap per source pair, the per-source
    # ref-uniqueness counts, and the bijection view the census re-verifies.
    copy_lineages, documented_lineages = _copy_and_documented_lineages(lineages, declared_details)
    source_sizes: dict[str, int] = defaultdict(int)
    ref_counts: dict[tuple[str, str], int] = defaultdict(int)
    for r in records:
        source_sizes[r.source_id] += 1
        ref = normalize_ref(r.external_ref)
        if ref is not None:
            ref_counts[(r.source_id, ref)] += 1
    measured_overlaps = _measured_overlap(records, coincident, source_sizes)
    colocation_counts: dict[str, dict[str, int]] = {
        records[i].subject_id: {s: _count_within(lst, rules.colocation_m) for s, lst in per.items()}
        for i, per in neigh.items()
    }

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
        # P35.25 NEW-1: a shared upstream ref is evidence only inside ONE
        # declared identifier namespace. The same string under two different
        # namespaces — or with no declared namespace at all (``undeclared``)
        # — is a coincidence, never shared-upstream evidence.
        shared_ns = (
            a.id_namespace
            if a.id_namespace
            and a.id_namespace == b.id_namespace
            and a.id_namespace != "undeclared"
            else None
        )
        ref_equal = ref_a is not None and ref_a == ref_b and shared_ns is not None
        ref_match_undeclared = ref_a is not None and ref_a == ref_b and shared_ns is None
        unique_colocation = (
            _count_within(na, rules.colocation_m) == 1
            and _count_within(nb, rules.colocation_m) == 1
        )
        # An exact distance tie is not a nearest neighbour: it fails (conservatively).
        # Compared on EFFECTIVE identity so a duplicate-target twin counts once.
        mutual_nearest = (
            bool(na)
            and bool(nb)
            and eff[na[0][1]] == eff[j]
            and eff[nb[0][1]] == eff[i]
            and (len(na) < 2 or na[1][0] > na[0][0])
            and (len(nb) < 2 or nb[1][0] > nb[0][0])
        )
        unique_near = (
            _count_within(na, rules.near_max_m) == 1 and _count_within(nb, rules.near_max_m) == 1
        )
        # P35.25: an ``unclassified`` lineage on either side means the pair's
        # independence is UNDETERMINED — ``same_lineage`` is then null (unknown),
        # never asserted true or false on undeclared material.
        la, lb = lineages[a.source_id], lineages[b.source_id]
        same_lineage: bool | None = (
            (la == lb) if la != UNCLASSIFIED and lb != UNCLASSIFIED else None
        )
        soft = _soft_conflicts(a, b, rules)
        suspected = axis_swap_suspected(a) or axis_swap_suspected(b)
        source_key = (
            (a.source_id, b.source_id) if a.source_id < b.source_id else (b.source_id, a.source_id)
        )
        overlap_pairs, measured_share = measured_overlaps.get(source_key, (0, 0.0))
        # Ruleset v3 (P35.46, ADR-153/ADR-L3-B): the derivation-collapse checks.
        # C1 — the same value in ONE declared id_namespace inside ONE declared
        # copy lineage, the id unique in each source's record set, within the
        # copy tolerance, and no suspected axis swap on either side.
        unique_in_captures = (
            ref_a is not None
            and ref_equal
            and ref_counts.get((a.source_id, ref_a), 0) == 1
            and ref_counts.get((b.source_id, ref_a), 0) == 1
        )
        copy_checks = {
            "shared_declared_namespace": shared_ns is not None,
            "ref_equal": ref_equal,
            "same_declared_lineage": same_lineage is True,
            "copy_declared_lineage": la == lb and la in copy_lineages,
            "unique_in_captures": unique_in_captures,
            "within_copy_tolerance": d <= rules.copy_tolerance_m,
            "documented_lineage": la == lb and la in documented_lineages,
            "measured_overlap": round(measured_share, 4),
            "overlap_pairs": overlap_pairs,
            "bijective_within_colocation": unique_colocation,
            "attribute_conflict": bool(soft),
            "axis_swap_suspected": suspected,
        }
        c1 = (
            shared_ns is not None
            and ref_equal
            and copy_checks["copy_declared_lineage"]
            and unique_in_captures
            and d <= rules.copy_tolerance_m
            and not suspected
        )
        c2 = (
            not c1
            and rules.c2_enabled
            and d <= rules.copy_tolerance_m
            and unique_colocation
            and copy_checks["documented_lineage"]
            and overlap_pairs >= rules.lineage_min_pairs
            and measured_share >= rules.c2_min_overlap
            and not soft
            and not suspected
        )
        if c1:
            tier = 1
        elif c2:
            tier = 2
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
        # C1 records the attribute differences a republished copy carries
        # (GQ-23: "attribute differences are recorded") — never silently
        # reconciled; the soft-conflict fields among them still route to P.
        attribute_differences = sorted(
            field
            for field, va, vb in (
                ("name", _norm_text(a.name), _norm_text(b.name)),
                ("roadway", _norm_text(a.roadway), _norm_text(b.roadway)),
                ("direction", _norm_text(a.direction), _norm_text(b.direction)),
                ("operator", _norm_text(a.operator), _norm_text(b.operator)),
                ("jurisdiction", _norm_text(a.jurisdiction), _norm_text(b.jurisdiction)),
                ("camera_type", _norm_text(a.camera_type), _norm_text(b.camera_type)),
                (
                    "technology",
                    ",".join(sorted({t for t in a.declared_technologies or (a.technology,) if t})),
                    ",".join(sorted({t for t in b.declared_technologies or (b.technology,) if t})),
                ),
            )
            if va != vb
        )
        # A pair with a copy SHAPE that failed a collapse condition carries the
        # failed conditions as its possible-duplicate reason (P's "1g without a
        # namespace" / undeclared-lineage / non-unique cases, verbatim).
        copy_rejection: list[str] = []
        if tier >= 3 and (
            (shared_ns is not None and ref_equal)
            or (same_lineage is True and d <= rules.copy_tolerance_m)
        ):
            copy_rejection = [
                name
                for name in (
                    "shared_declared_namespace",
                    "ref_equal",
                    "copy_declared_lineage",
                    "unique_in_captures",
                    "within_copy_tolerance",
                    "documented_lineage",
                    "attribute_conflict",
                    "axis_swap_suspected",
                )
                if not copy_checks[name]
            ]
        evidence: dict[str, Any] = {
            "rule": rules.label(tier),
            "distance_m": round(d, 2),
            "sources": [left.source_id, right.source_id],
            "device_classes": [classes[left_i], classes[right_i]],
            # P35.15a / PKG-07: the declared technology slugs behind those
            # classes — auditable per pair, never inferred post-hoc.
            "declared_technologies": [
                sorted({t for t in (left.declared_technologies or (left.technology,)) if t}),
                sorted({t for t in (right.declared_technologies or (right.technology,)) if t}),
            ],
            "shared_upstream_ref": ref_a if ref_equal else None,
            "ref_match_undeclared": ref_match_undeclared or None,
            "id_namespaces": [
                left.id_namespace or "undeclared",
                right.id_namespace or "undeclared",
            ],
            "lineage_ids": [la, lb],
            "names_agree": names_agree(a.name, b.name),
            "unique_within_colocation": unique_colocation,
            "mutual_nearest": mutual_nearest,
            "unique_within_near": unique_near,
            "same_lineage": same_lineage,
            "soft_conflicts": list(soft),
            # P35.46 v3: the collapse-check verdict per pair and the recorded
            # attribute differences a copy carries.
            "copy_checks": copy_checks,
            "copy_rejection": copy_rejection or None,
            "attribute_differences": attribute_differences,
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
    # Duplicate-target edges: each non-root member of a dup group is paired with
    # the group's root (a star is enough to co-cluster the group; the row is
    # pairwise auditable). Tier 0 is outside the measured candidate tiers — the
    # merge is evidence-based (identical captures / identical row), never a
    # statistical call — and carries its lineage proof in match_evidence.
    by_subject = {r.subject_id: r for r in records}
    group_members: dict[str, list[str]] = defaultdict(list)
    for subject, root in dup_groups.items():
        group_members[root].append(subject)
    for root in sorted(group_members):
        for member in sorted(group_members[root]):
            if member == root:
                continue
            a, b = by_subject[root], by_subject[member]
            left, right = (a, b) if a.subject_id < b.subject_id else (b, a)
            d = (
                haversine_m(a.latitude, a.longitude, b.latitude, b.longitude)  # type: ignore[arg-type]
                if _valid_point(a) and _valid_point(b)
                else 0.0
            )
            shared_digests = sorted(set(a.capture_digests) & set(b.capture_digests))
            targets = sorted(t for t in {a.target_id, b.target_id} if t is not None)
            out.append(
                PairAssessment(
                    left=left.subject_id,
                    right=right.subject_id,
                    tier=0,
                    tier_label="C0:duplicate_target",
                    distance_m=d,
                    soft_conflicts=(),
                    evidence={
                        "rule": "C0:duplicate_target",
                        "distance_m": round(d, 2),
                        "sources": [left.source_id, right.source_id],
                        "device_classes": [
                            device_class(left, rules),
                            device_class(right, rules),
                        ],
                        "targets": targets,
                        "identical_capture_digests": shared_digests,
                        "row_identical": _row_fingerprint(a) == _row_fingerprint(b),
                        "duplicate_group_root": root,
                        "group_size": len(group_members[root]),
                        # P35.25: derived from the resolved lineage map, not
                        # hardcoded — same-source twins share whatever lineage
                        # their source resolved to (``unclassified`` included).
                        "same_lineage": lineages[a.source_id] == lineages[b.source_id],
                        "lineage_ids": [lineages[a.source_id]],
                        "rules_version": rules.version,
                    },
                    evidence_claims=tuple(sorted(set(left.claim_ids) | set(right.claim_ids))),
                )
            )
    out.sort(key=lambda p: (p.left, p.right))
    return _Assessed(
        assessments=tuple(out),
        lineages=lineages,
        duplicate_groups=dup_groups,
        blocking_size=len(index_pairs),
        unblockable=unblockable,
        incompatible_blocked=incompatible,
        discarded=discarded,
        lineage_findings=lineage_findings,
        ref_counts=dict(ref_counts),
        measured_overlaps=measured_overlaps,
        copy_lineages=copy_lineages,
        documented_lineages=documented_lineages,
        colocation_counts=colocation_counts,
    )


def assess_pairs(
    records: Sequence[CameraRecord],
    *,
    rules: CameraSiteRules | None = None,
    geo_rule: GeoGridRule | None = None,
    blocking_context: BlockingContext | None = None,
    declared: Mapping[str, str] | None = None,
    declared_details: Mapping[str, LineageDeclaration] | None = None,
) -> tuple[PairAssessment, ...]:
    """Block and assess every candidate pair of ``records`` (tiers 1/2/3/4/5; tier 6 dropped).

    ``declared`` is the P35.25 source -> independence-class map (see
    :func:`infer_lineages`); when given it also gates the shared-upstream-ref
    namespace evidence and makes ``same_lineage`` truthful about
    ``unclassified`` material. ``declared_details`` (P35.46) carries each
    source's ``source_lineage`` kind/evidence — the C1 copy-lineage and C2
    documentary-evidence gates read it; absent it, every declared class
    counts as a copy lineage and none is documented.
    """
    rs = rules or CameraSiteRules.from_data()
    gr = geo_rule or load_geo_rules()[0]
    return _assess(
        records,
        rules=rs,
        geo_rule=gr,
        blocking_context=blocking_context,
        declared=declared,
        declared_details=declared_details,
    ).assessments


# --------------------------------------------------------------------------- #
# Decisions + constrained clustering                                           #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SiteDecision:
    """A recorded same-device decision.

    Dispositions: ``auto_write`` (clustered automatically — measured tiers and
    evidence-based duplicate-target edges), ``human_accept`` (a curator's
    accept, clustered, ``decided_by`` the curator), ``proposed`` (review — also
    a ``human_conflict`` between curators), ``human_reject`` (a curator's
    reject, recorded as a hard ``cannot_link`` relation — never clusters), and
    ``refused`` (a human accept that would violate a hard constraint — recorded
    and refused, never applied). ``reason`` says why a candidate that could have
    clustered was routed to review or refused (a demoted/unmeasured tier, a
    soft conflict, a refused union, a cluster alert, a human conflict/refusal).
    """

    assessment: PairAssessment
    disposition: str  # auto_write | proposed | human_accept | human_reject | refused
    reason: str | None = None
    relation: str = "same_as"  # "cannot_link" for a human reject
    decided_by: str = "auto"  # the curator id on human_* / refused rows
    verdict: HumanVerdict | None = None  # the governing verdict, for audit

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
    def __init__(
        self, records: Mapping[str, CameraRecord], dup: Mapping[str, str] | None = None
    ) -> None:
        self.parent: dict[str, str] = {s: s for s in records}
        self.members: dict[str, list[str]] = {s: [s] for s in records}
        self.records = records
        #: subject -> duplicate-group root: members of one group are the same
        #: upstream row and count as ONE record under constraint (a).
        self.dup = dup or {}

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
                if not (_valid_point(px) and _valid_point(py)):
                    continue  # coord-less members contribute no distance
                span = max(
                    span,
                    haversine_m(px.latitude, px.longitude, py.latitude, py.longitude),  # type: ignore[arg-type]
                )
        return span

    def refusal(self, a: str, b: str, rules: CameraSiteRules) -> str | None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return None
        # Constraint (a): the joined cluster must hold at most one DISTINCT
        # record per source — duplicate-target members share one effective
        # identity (source, dup-root) and so count once (the evidenced exception).
        by_source: dict[str, set[str]] = defaultdict(set)
        for m in self.members[ra] + self.members[rb]:
            by_source[self.records[m].source_id].add(self.dup.get(m, m))
        if any(len(ids) > 1 for ids in by_source.values()):
            return "cluster_constraint:same_source"
        # GQ-25 origin distinctness (P35.46): the joined cluster must never
        # hold two records one origin publisher lists as DISTINCT — two
        # different normalised ids inside ONE declared namespace. Refusing
        # keeps the worst failure in the conservative direction (a possible
        # duplicate over-counts, never under-counts).
        by_ns: dict[str, set[str]] = defaultdict(set)
        for m in self.members[ra] + self.members[rb]:
            r = self.records[m]
            ref = normalize_ref(r.external_ref)
            if r.id_namespace and r.id_namespace != "undeclared" and ref:
                by_ns[r.id_namespace].add(ref)
        if any(len(refs) > 1 for refs in by_ns.values()):
            return "cluster_constraint:origin_distinct"
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
    dup: Mapping[str, str] | None = None,
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
                if not (_valid_point(px) and _valid_point(py)):
                    continue  # coord-less members contribute no distance
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
        # Two members of one source alert only when they are DISTINCT records —
        # duplicate-target members share one effective identity (dup-root) and
        # count once; two different effective ids of one source are the breach.
        dup = dup or {}
        by_source_eff: dict[str, set[str]] = defaultdict(set)
        for m in ms:
            by_source_eff[records[m].source_id].add(dup.get(m, m))
        if any(len(v) > 1 for v in by_source_eff.values()):
            alerts.append(
                SiteAlert(
                    cid,
                    "same_source_cluster",
                    {"sources": sorted(records[m].source_id for m in ms)},
                )
            )
    ctx = ClusterShapeContext(
        max_le_cluster_size=10**9,  # the law-enforcement rule does not apply to devices
        substantial_component_size=rules.substantial_component,
        le_classes=frozenset(),
    )
    for a in cluster_shape_alerts(clusters, edges, None, context=ctx):
        if a.kind == "single_bridge_join":
            alerts.append(SiteAlert(a.cluster_id, a.kind, dict(a.detail)))
    return alerts


def _human_assessment(
    v: HumanVerdict, by_id: Mapping[str, CameraRecord], classes: Mapping[str, str]
) -> PairAssessment:
    """A record-level view for a decided pair that is not a current candidate.

    Carries the pair's recorded tier (from its review item) when known, else
    tier 0; the evidence notes that the decision came from review, not the
    tiered matcher this run.
    """
    a, b = by_id[v.left], by_id[v.right]
    d = (
        haversine_m(a.latitude, a.longitude, b.latitude, b.longitude)  # type: ignore[arg-type]
        if _valid_point(a) and _valid_point(b)
        else 0.0
    )
    return PairAssessment(
        left=v.left,
        right=v.right,
        tier=v.tier if v.tier is not None else 0,
        tier_label=v.tier_label or "0:human_review",
        distance_m=d,
        soft_conflicts=(),
        evidence={
            "rule": "human_review_decision",
            "distance_m": round(d, 2),
            "sources": [a.source_id, b.source_id],
            "device_classes": [classes[v.left], classes[v.right]],
            "human_items": [[iid, iv] for iid, iv in v.items],
            "rules_version": "review",
        },
        evidence_claims=tuple(sorted(set(a.claim_ids) | set(b.claim_ids))),
    )


def _link_stamp(
    d: SiteDecision, clusters: Mapping[str, str], rules: CameraSiteRules
) -> SiteDecision:
    """Stamp the emitted-link vocabulary onto a decision's evidence (P35.46).

    Every recorded decision carries ``link_kind`` + ``basis`` + the site id(s)
    it binds — the spine's honest record of what the link claims:

    * ``derived_from`` — a collapse: C0/C1/C2 copies of one upstream record
      (a derivation link with lineage evidence + the shared ``site_id``,
      never an identity merge — ``merged_into`` stays unwritten, ADR-105 §6);
    * ``possible_duplicate`` — an inferential match, refused union, soft
      conflict, shape alert, demoted or axis-swap-suspected pair: NOT merged;
      the basis says so verbatim;
    * ``same_as`` / ``cannot_link`` — a human review outcome (the curator's
      operational decision, folded under ADR-116)."""
    a = d.assessment
    ev = dict(a.evidence)
    left_site = clusters.get(a.left, a.left)
    right_site = clusters.get(a.right, a.right)
    link_kind = "possible_duplicate"
    if d.disposition == "auto_write" and a.tier in rules.collapse_tiers:
        link_kind = "derived_from"
        ev["site_id"] = left_site  # the shared site id both copies carry
        origin = (a.evidence.get("lineage_ids") or [a.left])[0]
        ref = a.evidence.get("shared_upstream_ref")
        if a.tier == 0:
            basis = "same upstream layer ingested twice"
        elif a.tier == 1:
            basis = f"copy of {origin} record {ref}, checked automatically"
        else:
            basis = f"position-matched copy of {origin} (layer is a republish; matched by location)"
        ev["basis"] = basis
    elif d.disposition == "auto_write" or d.disposition == "human_accept":
        # A B5-certified inferential edge or a curator's accept — one site id.
        link_kind = "same_as"
        ev["site_id"] = left_site
    elif d.disposition == "human_reject":
        link_kind = "cannot_link"
        ev["site_ids"] = [left_site, right_site]
    else:  # proposed | refused — the possible-duplicate link (never merged)
        ev["site_ids"] = [left_site, right_site]
        ev["basis"] = (
            f"possible duplicate of {a.right}, {round(a.distance_m, 2)} m away; "
            "not merged: SIG cannot prove it is the same camera"
        )
        if d.reason:
            ev["possible_duplicate_reason"] = d.reason
    ev["link_kind"] = link_kind
    # The relation the row asserts is the emitted link kind itself — the
    # camera_site_match.relation_type column carries the v3 vocabulary.
    return SiteDecision(
        assessment=replace(a, evidence=ev),
        disposition=d.disposition,
        reason=d.reason,
        relation=link_kind,
        decided_by=d.decided_by,
        verdict=d.verdict,
    )


def cluster_decisions(
    assessments: Sequence[PairAssessment],
    records: Sequence[CameraRecord],
    *,
    auto_write_tiers: Iterable[int],
    rules: CameraSiteRules | None = None,
    human_verdicts: Sequence[HumanVerdict] = (),
    dup_groups: Mapping[str, str] | None = None,
    demoted_collapses: Iterable[tuple[str, int]] = (),
) -> tuple[tuple[SiteDecision, ...], dict[str, str], tuple[SiteAlert, ...]]:
    """Turn assessments + human verdicts into decisions + clusters (constraints hold).

    Returns ``(decisions, clusters, alerts)`` where ``clusters`` maps every record's
    subject id to its cluster id (the smallest member subject id; a singleton maps to
    itself). Applied edges (``auto_write`` and ``human_accept``) cluster; proposed,
    rejected and refused pairs never do.

    **Precedence (ADR-R9-HUMANER).** A pair with a human verdict takes the human
    outcome, whatever the automatic tier would have said — the verdict is applied
    BEFORE the automatic edges. ``accept`` unions under the hard constraints (a
    refusal is recorded ``refused``, never applied); ``reject`` is recorded
    ``human_reject``/``cannot_link`` and the pair never clusters; ``conflict``
    stays ``proposed``. Tier-0 duplicate-target edges are evidence, not a
    measured tier — they apply directly, after human verdicts.

    **Ruleset v3 (P35.46).** Only a ``collapse_tiers`` pair (C0/C1/C2) may
    auto-collapse — and never one carrying a suspected axis swap or sitting in
    a census-demoted ``(lineage, tier)`` (``demoted_collapses``, the prior
    run's GQ-23 failures): those surface as ``possible_duplicate`` links like
    every inferential pair.
    """
    rs = rules or CameraSiteRules.from_data()
    auto = frozenset(auto_write_tiers)
    demoted = frozenset(demoted_collapses)
    by_id = {r.subject_id: r for r in records}
    dup = dict(dup_groups or {})
    state = _Clusters(by_id, dup)
    classes = {s: device_class(r, rs) for s, r in by_id.items()}
    assessed = {p.key: p for p in assessments}

    # key -> (disposition, reason, relation, decided_by, verdict, assessment)
    initial: dict[
        tuple[str, str],
        tuple[str, str | None, str, str, HumanVerdict | None, PairAssessment],
    ] = {}

    # 1) Human verdicts first — precedence over every automatic outcome.
    for v in sorted(human_verdicts, key=lambda v: (v.left, v.right)):
        if v.left not in by_id or v.right not in by_id:
            continue  # decided pair absent from this run's records (counted by caller)
        p = assessed.get(v.key) or _human_assessment(v, by_id, classes)
        if v.verdict == "accept":
            if frozenset((classes[v.left], classes[v.right])) in rs.incompatible_classes:
                initial[v.key] = (
                    "refused",
                    "human_refused:incompatible_class",
                    "same_as",
                    v.decided_by,
                    v,
                    p,
                )
                continue
            refusal = state.refusal(v.left, v.right, rs)
            if refusal is None:
                state.union(v.left, v.right)
                initial[v.key] = ("human_accept", None, "same_as", v.decided_by, v, p)
            else:
                initial[v.key] = (
                    "refused",
                    f"human_refused:{refusal}",
                    "same_as",
                    v.decided_by,
                    v,
                    p,
                )
        elif v.verdict == "reject":
            initial[v.key] = (
                "human_reject",
                "cannot_link",
                "cannot_link",
                v.decided_by,
                v,
                p,
            )
        else:  # conflict — stays proposed, routed back by the writer
            initial[v.key] = ("proposed", "human_conflict", "same_as", "auto", v, p)

    # 2) Automatic edges, strongest first, under the same hard constraints.
    ordered = sorted(assessments, key=lambda p: (p.tier, p.distance_m, p.left, p.right))
    for p in ordered:
        if p.key in initial:
            continue  # a human verdict already owns this pair
        # Ruleset v3 (P35.46): ``auto`` already encodes every gate — a
        # collapse tier is in it by census waiver, an inferential tier ONLY
        # when a B5 certification named it (GQ-24). Anything else is
        # review-only: the possible_duplicate link, never a merge.
        auto_path = p.tier == 0 or p.tier in auto
        if not auto_path:
            reason = (
                "possible_duplicate:inferential"
                if p.tier in rs.inferential_tiers
                else "tier_not_auto_write"
            )
            initial[p.key] = ("proposed", reason, "same_as", "auto", None, p)
            continue
        ra_rec, rb_rec = by_id[p.left], by_id[p.right]
        if axis_swap_suspected(ra_rec) or axis_swap_suspected(rb_rec):
            # GQ-24: a suspected axis swap can never merge mechanically.
            initial[p.key] = (
                "proposed",
                "possible_duplicate:axis_swap_suspected",
                "same_as",
                "auto",
                None,
                p,
            )
            continue
        lids = p.evidence.get("lineage_ids") or []
        demotion_token = ra_rec.source_id if p.tier == 0 else (lids[0] if lids else None)
        if demotion_token is not None and (demotion_token, p.tier) in demoted:
            # GQ-23: a lineage/tier whose last-run census failed does not
            # auto-collapse again — the pair is a possible duplicate.
            initial[p.key] = (
                "proposed",
                "possible_duplicate:census_demoted",
                "same_as",
                "auto",
                None,
                p,
            )
            continue
        if p.soft_conflicts:
            initial[p.key] = (
                "proposed",
                "soft_conflict:" + ",".join(p.soft_conflicts),
                "same_as",
                "auto",
                None,
                p,
            )
            continue
        refusal = state.refusal(p.left, p.right, rs)
        if refusal is None:
            state.union(p.left, p.right)
            initial[p.key] = ("auto_write", None, "same_as", "auto", None, p)
        else:
            initial[p.key] = ("proposed", refusal, "same_as", "auto", None, p)

    applied = [k for k, d in initial.items() if d[0] in ("auto_write", "human_accept")]
    clusters = _clusters_from_edges(by_id, applied)
    alerts = site_alerts(clusters, applied, by_id, rs, dup)
    alerted = {a.cluster_id for a in alerts}
    if alerted:
        for k in applied:
            d = initial[k]
            if d[0] == "auto_write" and d[5].tier != 0 and clusters[k[0]] in alerted:
                initial[k] = ("proposed", "cluster_shape_alert", "same_as", "auto", None, d[5])
        applied = [k for k, d in initial.items() if d[0] in ("auto_write", "human_accept")]
        clusters = _clusters_from_edges(by_id, applied)

    decisions = tuple(
        _link_stamp(
            SiteDecision(
                assessment=d[5],
                disposition=d[0],
                reason=d[1],
                relation=d[2],
                decided_by=d[3],
                verdict=d[4],
            ),
            clusters,
            rs,
        )
        for k, d in sorted(initial.items())
    )
    return decisions, clusters, tuple(alerts)


def derivation_census(
    records: Sequence[CameraRecord],
    decisions: Sequence[SiteDecision],
    clusters: Mapping[str, str],
    rules: CameraSiteRules,
    *,
    lineages: Mapping[str, str],
    copy_lineages: Iterable[str] = (),
    documented_lineages: Iterable[str] = (),
    measured_overlaps: Mapping[tuple[str, str], tuple[int, float]] = {},
    colocation_counts: Mapping[str, dict[str, int]] = {},
) -> DerivationCensus:
    """Re-verify every applied collapse edge of this run — GQ-23 (P35.46).

    Runs AFTER clustering on every run. A collapse edge whose conditions no
    longer verify on the record set is a :class:`CensusFailure`, and its
    ``(lineage-or-source, tier)`` joins ``demote_next_run`` — persisted as an
    append-only demotion row and consumed by the NEXT run's
    ``cluster_decisions`` (a stale declaration collapses for at most one run).

    Also counts the GQ-25 violations that reached clusters anyway (two members
    of one resolved site carrying different normalised ids in one declared
    namespace) — disclosed, never silently reconciled.
    """
    by_id = {r.subject_id: r for r in records}
    # The ref census: (source, normalised ref) -> count, over the full set.
    ref_counts: dict[tuple[str, str], int] = defaultdict(int)
    for r in records:
        ref = normalize_ref(r.external_ref)
        if ref is not None:
            ref_counts[(r.source_id, ref)] += 1
    copy_l = frozenset(copy_lineages)
    documented_l = frozenset(documented_lineages)
    failures: list[CensusFailure] = []
    checked = 0
    for d in decisions:
        if d.disposition != "auto_write" or d.assessment.tier not in rules.collapse_tiers:
            continue
        checked += 1
        a, b = by_id[d.assessment.left], by_id[d.assessment.right]
        tier = d.assessment.tier
        la = lineages.get(a.source_id, UNCLASSIFIED)
        lb = lineages.get(b.source_id, UNCLASSIFIED)
        token = a.source_id if tier == 0 else la
        failed: list[str] = []
        if tier == 0:
            if a.source_id != b.source_id:
                failed.append("cross_source")
            elif not (
                _row_fingerprint(a) == _row_fingerprint(b)
                or set(a.capture_digests) & set(b.capture_digests)
            ):
                failed.append("no_duplicate_target_evidence")
        else:
            if a.source_id == b.source_id:
                failed.append("same_source")
            if axis_swap_suspected(a) or axis_swap_suspected(b):
                failed.append("axis_swap_suspected")
            if d.assessment.distance_m > rules.copy_tolerance_m:
                failed.append("beyond_copy_tolerance")
            if la != lb or la == UNCLASSIFIED:
                failed.append("no_shared_declared_lineage")
            if tier == 1:
                ref_a, ref_b = normalize_ref(a.external_ref), normalize_ref(b.external_ref)
                if (
                    not a.id_namespace
                    or a.id_namespace == "undeclared"
                    or a.id_namespace != b.id_namespace
                ):
                    failed.append("no_shared_declared_namespace")
                if ref_a is None or ref_a != ref_b:
                    failed.append("ref_mismatch")
                elif (
                    ref_counts.get((a.source_id, ref_a), 0) != 1
                    or ref_counts.get((b.source_id, ref_a), 0) != 1
                ):
                    failed.append("ref_not_unique_in_captures")
                if la not in copy_l:
                    failed.append("lineage_not_declared_copy")
            elif tier == 2:
                if la not in documented_l:
                    failed.append("lineage_not_documented_copy")
                key = (
                    (a.source_id, b.source_id)
                    if a.source_id < b.source_id
                    else (b.source_id, a.source_id)
                )
                pairs, share = measured_overlaps.get(key, (0, 0.0))
                if pairs < rules.lineage_min_pairs or share < rules.c2_min_overlap:
                    failed.append("measured_overlap_below_floor")
                ca = colocation_counts.get(a.subject_id, {}).get(b.source_id, 0)
                cb = colocation_counts.get(b.subject_id, {}).get(a.source_id, 0)
                if ca != 1 or cb != 1:
                    failed.append("bijection_broken")
                if _soft_conflicts(a, b, rules):
                    failed.append("attribute_conflict")
        if failed:
            failures.append(
                CensusFailure(
                    left=d.assessment.left,
                    right=d.assessment.right,
                    tier=tier,
                    token=token,
                    reason=",".join(sorted(set(failed))),
                )
            )
    demote = sorted({(f.token, f.tier) for f in failures})
    # GQ-25 on the final clusters: two members, ONE declared namespace,
    # DIFFERENT normalised ids -> the origin publisher lists them as distinct.
    members: dict[str, list[CameraRecord]] = defaultdict(list)
    for r in records:
        members[clusters.get(r.subject_id, r.subject_id)].append(r)
    violating: list[str] = []
    for cid, ms in sorted(members.items()):
        by_ns: dict[str, set[str]] = defaultdict(set)
        for m in ms:
            ref = normalize_ref(m.external_ref)
            if m.id_namespace and m.id_namespace != "undeclared" and ref:
                by_ns[m.id_namespace].add(ref)
        if any(len(refs) > 1 for refs in by_ns.values()):
            violating.append(cid)
    return DerivationCensus(
        checked=checked,
        failures=tuple(failures),
        demote_next_run=tuple(demote),
        origin_distinct_violations=len(violating),
        origin_distinct_clusters=tuple(violating),
    )


def count_intervals(
    records: Sequence[CameraRecord],
    decisions: Sequence[SiteDecision],
    clusters: Mapping[str, str],
    rules: CameraSiteRules,
    *,
    dossier_of: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """The P35.46 honest count intervals (SIG-CONF-D05).

    ``upper`` counts only the applied edges (``auto_write`` + ``human_accept``)
    — the present spine state. ``lower`` additionally collapses every
    possible-duplicate link whose pair lies within the declared distance
    (``near_max_m``) — the count if every inferential match proved to be the
    same camera. Published counts are intervals until CONF-07b closes; a run
    always reports both bounds, per dossier (``jurisdiction`` by default) and
    nationally.
    """
    subjects = [r.subject_id for r in records]
    applied = [
        (d.left, d.right) for d in decisions if d.disposition in ("auto_write", "human_accept")
    ]
    possible = [
        (d.left, d.right)
        for d in decisions
        if d.disposition == "proposed" and d.assessment.distance_m <= rules.near_max_m
    ]
    dossier = dossier_of or {r.subject_id: (r.jurisdiction or "unresolved") for r in records}

    def _bounds(subset: set[str]) -> dict[str, int]:
        sub = [s for s in subjects if s in subset]
        up = len(
            set(
                _clusters_from_edges(
                    sub,
                    [e for e in applied if e[0] in subset and e[1] in subset],
                ).values()
            )
        )
        lo = len(
            set(
                _clusters_from_edges(
                    sub, [e for e in applied + possible if e[0] in subset and e[1] in subset]
                ).values()
            )
        )
        return {"lower": lo, "upper": up}

    all_ids = set(subjects)
    return {
        "declared_distance_m": rules.near_max_m,
        "national": _bounds(all_ids),
        "per_dossier": {
            name: _bounds({s for s in subjects if dossier.get(s, "unresolved") == name})
            for name in sorted({dossier.get(s, "unresolved") for s in subjects})
        },
        "note": (
            "published camera-site counts are intervals until CONF-07b closes; "
            "the upper bound counts only automatic + human-accepted edges and "
            "the lower bound also collapses inferential matches within the "
            "declared distance"
        ),
    }


def m1b_sample_frame(
    decisions: Sequence[SiteDecision],
    *,
    sample_size: int = 200,
    seed_salt: str = "",
) -> dict[str, dict[str, Any]]:
    """The M-1b id-resolution sample frame (P35.46).

    Per declared namespace, a deterministic random sample of up to
    ``sample_size`` applied C1 collapses — the id-resolution verification
    surface a human re-check draws from. Each sample row carries the original
    and republish record ids, the shared upstream ref, and the pair distance.
    The seed is the run key plus the namespace, so the same run always draws
    the same frame (re-runnable, auditable).
    """
    by_ns: dict[str, list[SiteDecision]] = defaultdict(list)
    for d in decisions:
        if d.disposition == "auto_write" and d.assessment.tier == 1:
            nss = d.assessment.evidence.get("id_namespaces") or []
            ns = nss[0] if nss and nss[0] == nss[-1] else None
            if ns and ns != "undeclared":
                by_ns[str(ns)].append(d)
    out: dict[str, dict[str, Any]] = {}
    for ns in sorted(by_ns):
        ds = sorted(by_ns[ns], key=lambda d: (d.left, d.right))
        rng = random.Random(f"m1b:{seed_salt}:{ns}")
        picked = sorted(rng.sample(range(len(ds)), min(sample_size, len(ds))))
        out[ns] = {
            "collapses": len(ds),
            "sample_size": len(picked),
            "sample": [
                {
                    "original_record_id": ds[i].left,
                    "republish_record_id": ds[i].right,
                    "shared_upstream_ref": ds[i].assessment.evidence.get("shared_upstream_ref"),
                    "distance_m": round(ds[i].assessment.distance_m, 2),
                }
                for i in picked
            ],
        }
    return out


def clopper_pearson_lower(k: int, n: int, alpha: float = 0.05) -> float:
    """One-sided exact (Clopper-Pearson) lower confidence bound, binomial.

    The largest ``p`` for which ``P(X >= k | p) = alpha`` — the M-1b
    acceptance bound compares this against the per-namespace floor.
    ``k`` verified out of ``n`` sampled collapses.
    """
    if n <= 0 or k <= 0:
        return 0.0
    k = min(k, n)

    def _sf(p: float) -> float:
        return sum(math.comb(n, i) * p**i * (1.0 - p) ** (n - i) for i in range(k, n + 1))

    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if _sf(mid) < alpha:
            lo = mid  # P(X >= k | p) increases with p — mid sits below the root
        else:
            hi = mid
    return (lo + hi) / 2


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

    P35.25 (SIG-CONF-014): the shared ``unclassified`` pseudo-lineage counts as
    one voice but is not an established independent lineage — ``corroborated``
    needs two or more DECLARED lineage ids and ``unclassified_sources``
    discloses the undeclared membership.
    """
    sources = sorted({m.source_id for m in cluster_members})
    lineage_ids = sorted({lineages.get(s, s) for s in sources})
    declared_ids = [lid for lid in lineage_ids if lid != UNCLASSIFIED]
    return {
        "size": len(cluster_members),
        "sources": sources,
        "independent_lineages": len(declared_ids),
        "unclassified_sources": sum(1 for s in sources if lineages.get(s, s) == UNCLASSIFIED),
        "corroborated": len(declared_ids) >= 2,
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
    """The versioned camera gold set and its provenance.

    ``provenance`` is the reference-label basis class in plain words —
    ``"agent"`` for the committed set (P34.45 / F-512: both labelling runs were
    the same model, an agent seed plus a fresh-context LLM adjudicator, never an
    independent human). The field is fail-closed: a set that does not declare a
    human label source is never read as one. ``labeller_kind``/``labeller_model``
    /``labeller_runs_same_model`` are the additive disclosure fields the ticket
    requires — the old ``verifier``/``llm`` names stay readable unchanged.
    """

    version: str
    rules_version: str
    verifier: str
    llm: str
    pairs: tuple[CameraGoldPair, ...]
    digest: str = ""
    provenance: str = "agent"
    labeller_kind: str | None = None
    labeller_model: str | None = None
    labeller_runs_same_model: bool | None = None

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
            json.dumps([self.version, self.verifier, self.llm, self.provenance, body]).encode()
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
        holdout pair is never dropped from the precision it governs. The verifier
        is an agent — its label is a reference opinion, never a human verdict
        (P34.45 / ADR-152)."""
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
        # P34.45 / F-512: the declared label basis — absent means never human.
        provenance=str(raw.get("provenance", "agent")),
        labeller_kind=(str(raw["labeller_kind"]) if raw.get("labeller_kind") else None),
        labeller_model=(str(raw["labeller_model"]) if raw.get("labeller_model") else None),
        labeller_runs_same_model=(
            bool(raw["labeller_runs_same_model"])
            if raw.get("labeller_runs_same_model") is not None
            else None
        ),
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
    no tier. The label is the verifier's (the agent-labelled holdout) unless
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
    inferential_tiers: Iterable[int] = (),
    certified_tiers: Iterable[int] = (),
    eval_waived_tiers: Iterable[int] = (),
) -> tuple[frozenset[int], tuple[DemotionDecision, ...]]:
    """Which candidate tiers auto-write this run, and the demotion record.

    A candidate tier auto-writes only if it has at least ``min_pairs`` holdout pairs AND
    its measured precision (strict by default) is at least ``threshold``; a tier with no
    (or too little) holdout evidence is demoted — silence, or 1-of-1, never auto-writes.

    P34.45 (ADR-153, GQ-24): a tier in ``inferential_tiers`` is an identity inference —
    it auto-writes only when an independent human (B5) evaluation has certified it
    (``certified_tiers``). The agent/LLM-labelled gold set can never certify one, so
    under v3-interim every inferential tier demotes with reason
    ``no_certifying_evaluation`` however clean its measured precision looks. The
    namespace join (``1g:shared_upstream_ref``) is a derivation, not an inference —
    it follows the measured path like before.

    P35.46 (ADR-153, Q-L3-1 = a): ``eval_waived_tiers`` names the derivation-
    collapse tiers C0–C2 — the SIG-EVAL-004 holdout bound does NOT gate a
    mechanical derivation (the GQ-23 census re-verifies every collapse every
    run instead). The holdout measurement still records — a DemotionDecision
    with ``reason="eval_waived:gq23_census"`` carries the measured precision
    even though the tier auto-collapses.
    """
    inferential = frozenset(inferential_tiers)
    certified = frozenset(certified_tiers)
    waived = frozenset(eval_waived_tiers)
    auto: set[int] = set()
    decisions: list[DemotionDecision] = []
    for tier in sorted(set(candidate_tiers)):
        m = measured.get(tier)
        precision = None
        if m is not None:
            precision = m.precision_strict if strict else m.precision_decided
        value = 0.0 if precision is None else precision
        if tier in waived:
            # The ADR-L3-B scoped waiver: the eval gate does not apply to a
            # derivation-collapse tier — the GQ-23 census gates it instead.
            decisions.append(
                DemotionDecision(
                    tier=tier,
                    precision=value,
                    threshold=threshold,
                    demoted=False,
                    reason="eval_waived:gq23_census",
                )
            )
            auto.add(tier)
            continue
        uncertified = tier in inferential and tier not in certified
        too_few = m is None or m.predicted < min_pairs
        demoted = uncertified or precision is None or too_few or precision < threshold
        if uncertified:
            reason = "no_certifying_evaluation"
        elif m is None or too_few or precision is None:
            reason = "insufficient_holdout"
        elif precision < threshold:
            reason = "below_threshold"
        else:
            reason = ""
        decisions.append(
            DemotionDecision(
                tier=tier,
                precision=value,
                threshold=threshold,
                demoted=demoted,
                reason=reason,
            )
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
    #: The rules' identity-inference tiers (review-only under v3-interim) and the
    #: subset an independent human (B5) evaluation certified this run — empty in
    #: Round 11 (ADR-153; the agent/LLM gold set can never certify).
    inferential_tiers: frozenset[int] = frozenset()
    b5_certified_tiers: frozenset[int] = frozenset()
    tier_measurements: dict[int, TierMeasurement] = field(default_factory=dict)
    tier_measurements_llm_labels: dict[int, TierMeasurement] = field(default_factory=dict)
    blocking_size: int = 0
    unblockable: int = 0
    incompatible_blocked: int = 0
    discarded: int = 0
    gold_version: str | None = None
    kappa: float | None = None
    holdout_size: int = 0
    gold_size: int = 0
    disputed: int = 0
    #: P31.11: subject -> duplicate-group root for every member of an evidenced
    #: same-row republished group (size >= 2); empty when no duplicate target exists.
    duplicate_groups: dict[str, str] = field(default_factory=dict)
    #: P31.11: the folded human verdicts over pairs present in this run's records.
    human_verdicts: tuple[HumanVerdict, ...] = ()
    #: P31.11: decided pairs whose records are absent from this run — recorded
    #: nowhere, counted here so the run admits they were seen and skipped.
    human_verdicts_unmatched: int = 0
    #: P35.15a / PKG-07: the declared-technology classification audit. The
    #: findings are the subjects whose declared class DISAGREES with the class
    #: the legacy substring rules would have given them (the declaration wins;
    #: the disagreement stays visible) plus subjects asserting multiple
    #: declared technology slugs; ``records_without_declared_technology`` marks
    #: the subjects still carrying no ``technology`` claim (the P35.15b
    #: backfill remainder), and ``mixed_technology_subjects`` marks subjects
    #: whose current ``technology`` claims assert more than one slug — never
    #: silently reconciled, counted here.
    device_class_findings: tuple[DeviceClassFinding, ...] = ()
    records_without_declared_technology: int = 0
    mixed_technology_subjects: int = 0
    #: P35.25 / GQ-11 (SIG-EPIS-029): lineage facts the data shows but no
    #: declaration backs — measured copy unions between undeclared sources, and
    #: measured unions CONTRADICTING two declared-independent classes. Empty
    #: when the run had no declared-lineage map.
    lineage_findings: tuple[LineageFinding, ...] = ()
    #: P35.46 (ruleset v3, GQ-23): the derivation census of THIS run — every
    #: applied collapse re-verified, the failures, the demotion set the next
    #: run consumes, and the GQ-25 origin-distinctness cluster count.
    derivation_census: DerivationCensus | None = None
    #: P35.46: the ``(lineage-or-source, tier)`` demotions this run CONSUMED —
    #: the prior run's census failures; pairs under them stayed review-only.
    demoted_collapses: tuple[tuple[str, int], ...] = ()
    #: P35.46 (SIG-CONF-D05): honest count intervals — national + per-dossier.
    count_intervals: dict[str, Any] = field(default_factory=dict)
    #: P35.46 (M-1b): the id-resolution sample frame, keyed by namespace.
    m1b_frame: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def dedup_ratio(self) -> float:
        return dedup_ratio(self.observation_count, self.cluster_count)

    def counts(self) -> dict[str, Any]:
        by_tier: dict[str, dict[str, int]] = {}
        for d in self.decisions:
            slot = by_tier.setdefault(d.assessment.tier_label, {"auto_write": 0, "proposed": 0})
            slot[d.disposition] = slot.get(d.disposition, 0) + 1
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
            # P35.25: how much of the run's lineage is declared vs the shared
            # unclassified voice, and every measured-but-undeclared copy the
            # detector saw (GQ-11 — disclosed, never silently independent).
            "unclassified_lineage_sources": sorted(lineage_groups.get(UNCLASSIFIED, [])),
            "lineage_findings": [
                {
                    "kind": f.kind,
                    "sources": list(f.sources),
                    "coincident_pairs": f.coincident_pairs,
                    "share": f.share,
                }
                for f in self.lineage_findings
            ],
        }

    def corroboration(self) -> dict[str, int]:
        """Multi-record resolved sites split by INDEPENDENT lineages (hard constraint (c)):
        a site whose members all come from one mirror lineage is one observation
        republished, never independently corroborated."""
        members: dict[str, list[str]] = defaultdict(list)
        for subject, cid in self.clusters.items():
            members[cid].append(subject)
        corroborated = mirror_only = unclassified_only = 0
        for ms in members.values():
            if len(ms) < 2:
                continue
            lineages = {self.lineages.get(self.sources[m], self.sources[m]) for m in ms}
            # P35.25: ``unclassified`` is one disclosed voice, never an
            # established independent lineage — corroboration needs two or more
            # DECLARED lineage ids; a site with no declared voice at all is
            # counted apart (its independence is unproven, not disproven).
            declared = lineages - {UNCLASSIFIED}
            if len(declared) >= 2:
                corroborated += 1
            elif not declared:
                unclassified_only += 1
            else:
                mirror_only += 1
        return {
            "multi_record_sites_independently_corroborated": corroborated,
            "multi_record_sites_one_lineage_only": mirror_only,
            "multi_record_sites_unclassified_lineage": unclassified_only,
        }

    def summary(self) -> dict[str, Any]:
        auto = sum(1 for d in self.decisions if d.disposition == "auto_write")
        human_applied = sum(1 for d in self.decisions if d.disposition == "human_accept")
        refused = sum(1 for d in self.decisions if d.disposition == "refused")
        human_rejects = sum(1 for d in self.decisions if d.disposition == "human_reject")
        proposed = sum(1 for d in self.decisions if d.disposition == "proposed")
        # Clusters whose membership a human accept decided (the edge endpoints
        # land in the same cluster — a refused/alerted accept does not count).
        members_of: dict[str, list[str]] = defaultdict(list)
        for subject, cid in self.clusters.items():
            members_of[cid].append(subject)
        human_clusters: set[str] = set()
        for d in self.decisions:
            if d.disposition == "human_accept":
                human_clusters.add(self.clusters[d.left])
        dup_groups = set(self.duplicate_groups.values())
        return {
            "rules_version": self.rules_version,
            "resolver_version": self.resolver_version,
            "run_key": self.run_key,
            "observation_count_M": self.observation_count,
            "resolved_site_count_N": self.cluster_count,
            "dedup_ratio": round(self.dedup_ratio, 6),
            "decisions": len(self.decisions),
            "auto_write_decisions": auto,
            "proposed_decisions": proposed,
            # P35.46 (ruleset v3): the link ledger — derivation links carry the
            # shared site id; every inferential match is a visible
            # possible_duplicate (distance + reason preserved), never merged.
            "derivation_links": sum(
                1
                for d in self.decisions
                if d.assessment.evidence.get("link_kind") == "derived_from"
            ),
            "possible_duplicate_links": sum(
                1
                for d in self.decisions
                if d.assessment.evidence.get("link_kind") == "possible_duplicate"
            ),
            "demoted_collapses": [list(t) for t in self.demoted_collapses],
            "derivation_census": (
                None
                if self.derivation_census is None
                else {
                    "checked": self.derivation_census.checked,
                    "gq23_failures": [
                        {
                            "left": f.left,
                            "right": f.right,
                            "tier": f.tier,
                            "token": f.token,
                            "reason": f.reason,
                        }
                        for f in self.derivation_census.failures
                    ],
                    "demote_next_run": [list(t) for t in self.derivation_census.demote_next_run],
                    "origin_distinct_violations": self.derivation_census.origin_distinct_violations,
                    "origin_distinct_clusters": list(
                        self.derivation_census.origin_distinct_clusters
                    ),
                }
            ),
            "count_intervals": self.count_intervals,
            "m1b_id_resolution_sample": self.m1b_frame,
            # P31.11 human-review accounting (ADR-R9-HUMANER): verdicts folded
            # from review_decision, their outcomes, and what they changed.
            "human_review": {
                "verdict_pairs": len(self.human_verdicts),
                "accepts": sum(1 for v in self.human_verdicts if v.verdict == "accept"),
                "rejects": sum(1 for v in self.human_verdicts if v.verdict == "reject"),
                "conflicts": sum(1 for v in self.human_verdicts if v.verdict == "conflict"),
                "unmatched_pairs": self.human_verdicts_unmatched,
                "accept_edges_applied": human_applied,
                "accept_edges_refused": refused,
                "cannot_link_edges": human_rejects,
                "clusters_with_human_accepts": len(human_clusters),
                "proposed_awaiting_review": proposed,
            },
            "duplicate_target_groups": len(dup_groups),
            "duplicate_target_records": len(self.duplicate_groups),
            "auto_write_tiers": sorted(self.auto_write_tiers),
            # ADR-153 posture: the identity-inference tiers this ruleset locks to
            # review unless an independent human (B5) evaluation certifies them.
            "inferential_tiers": sorted(self.inferential_tiers),
            "b5_certified_tiers": sorted(self.b5_certified_tiers),
            "demotions": [
                {
                    "tier": d.tier,
                    "precision": round(d.precision, 4),
                    "threshold": d.threshold,
                    "demoted": d.demoted,
                    "reason": d.reason,
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
            # P35.15a / PKG-07: the declared-technology classification audit —
            # declared-vs-substring disagreements stay visible, and the run
            # records how many records still lack a declaration (the P35.15b
            # backfill remainder) or assert multiple declared slugs.
            "declared_technology_records": (
                self.observation_count - self.records_without_declared_technology
            ),
            "records_without_declared_technology": self.records_without_declared_technology,
            "mixed_technology_subjects": self.mixed_technology_subjects,
            "device_class_findings": [
                {
                    "kind": f.kind,
                    "subject_id": f.subject_id,
                    "technologies": list(f.technologies),
                    "declared_class": f.declared_class,
                    "substring_class": f.substring_class,
                    "matched_by": f.matched_by,
                }
                for f in self.device_class_findings
            ],
            "tier6_discarded": self.discarded,
            "gold_set_version": self.gold_version,
            "kappa": self.kappa,
            "gold_pairs": self.gold_size,
            "holdout_pairs": self.holdout_size,
            "disputed_pairs": self.disputed,
            **self.counts(),
        }


def _rules_digest(rules: CameraSiteRules) -> str:
    """The content digest of the full rules object.

    Must be process-stable: ``repr`` of a dataclass leaks set/frozenset
    iteration order (PYTHONHASHSEED), which minted a different run_key per
    execution over identical inputs (found by P31.11's +0 re-run verification —
    P30.2b's two 1.0.0 run keys over one input set were the same defect).
    Canonicalise instead: sets sort their frozen elements, dataclasses/dicts
    serialise by sorted field/key name.
    """

    def freeze(v: Any) -> Any:
        if isinstance(v, (set, frozenset)):
            frozen = [freeze(x) for x in v]
            return sorted(frozen, key=lambda e: json.dumps(e, sort_keys=True, default=str))
        if is_dataclass(v) and not isinstance(v, type):
            return {f.name: freeze(getattr(v, f.name)) for f in dc_fields(v)}
        if isinstance(v, dict):
            return {str(k): freeze(v[k]) for k in sorted(v, key=str)}
        if isinstance(v, (list, tuple)):
            return [freeze(x) for x in v]
        return v

    return hashlib.sha256(
        json.dumps(freeze(rules), sort_keys=True, default=str).encode()
    ).hexdigest()


def run_key(
    *,
    rules: CameraSiteRules,
    auto_write_tiers: Iterable[int],
    gold: CameraGoldSet | None,
    records: Sequence[CameraRecord],
    human_verdicts: Sequence[HumanVerdict] = (),
    declared_lineages: Mapping[str, str] | None = None,
    declared_details: Mapping[str, LineageDeclaration] | None = None,
    demoted_collapses: Iterable[tuple[str, int]] = (),
) -> str:
    """The run identity: every input a decision depends on.

    Digests the resolver version, the FULL rules content, the gold set's content, the
    measured auto-write tiers, the folded human verdicts (P31.11 — a new review
    decision changes the outcome, so it must change the key), and every field of
    every record (source, coordinates, reference, name, direction, operator,
    jurisdiction, type, declared technology + the multi-slug set (P35.15a),
    claim ids, target id, capture digests). Two runs over the
    same inputs share a key (so the re-run is +0); ANY change a decision could depend
    on mints a new key, and readers take the latest COMPLETED run whole — never a union of
    a stale run's edges with a new one's.

    P35.46 adds the collapse inputs: each source's lineage-declaration detail
    (kind + documentary evidence gate C1/C2) and the consumed demotion set
    (a census failure mints a NEW key — the demoted run is a different run,
    not a silent re-collapse).
    """
    h = hashlib.sha256()
    h.update(
        json.dumps(
            {
                "resolver": CAMERA_SITE_RESOLVER_VERSION,
                "rules": _rules_digest(rules),
                "auto": sorted(auto_write_tiers),
                "gold": None if gold is None else gold.content_digest(),
                # P35.25 (SIG-CONF-014): the declared independence classes are a
                # decision input — a lineage backfill/declaration change mints a
                # NEW run key instead of silently retaining stale corroboration.
                "declared_lineages": (
                    None
                    if declared_lineages is None
                    else {k: declared_lineages[k] for k in sorted(declared_lineages)}
                ),
                # P35.46 (ruleset v3): the declaration kind/evidence the C1
                # copy-lineage and C2 documentary gates read.
                "declared_lineage_details": (
                    None
                    if declared_details is None
                    else {
                        s: {
                            "independence_class": d.independence_class,
                            "kind": d.kind,
                            "evidence": d.evidence,
                        }
                        for s, d in sorted(declared_details.items())
                    }
                ),
                "demoted_collapses": sorted([token, tier] for token, tier in demoted_collapses),
                "human": [
                    {
                        "left": v.left,
                        "right": v.right,
                        "verdict": v.verdict,
                        "decided_by": v.decided_by,
                        "items": [list(i) for i in v.items],
                        "decided_at": v.decided_at,
                        "tier": v.tier,
                        "tier_label": v.tier_label,
                    }
                    for v in sorted(human_verdicts, key=lambda v: v.key)
                ],
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
        "relation": d.relation,
        "disposition": d.disposition,
        "decided_by": d.decided_by,
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
    human_items: Sequence[HumanItem] = (),
    human_votes: Sequence[HumanVote] = (),
    certified_tiers: Iterable[int] = (),
    declared_lineages: Mapping[str, str] | None = None,
    declared_details: Mapping[str, LineageDeclaration] | None = None,
    demoted_collapses: Iterable[tuple[str, int]] = (),
) -> CameraSiteResult:
    """One camera-site ER run: block → assess → measure → decide → cluster → census (pure).

    ``human_items``/``human_votes`` are the append-only review surface
    (P31.11): items bind decided pairs, votes are ``review_decision`` rows.
    Passing none (or votes only, with no binding items) reproduces the
    pre-wiring run exactly — zero decisions is not a special case.

    ``certified_tiers`` names the inferential tiers an independent human (B5)
    evaluation has certified for auto-write — empty in Round 11 (P34.45,
    ADR-153): every identity-inference tier is review-only no matter what the
    agent/LLM-labelled holdout measures.

    ``declared_lineages`` is the P35.25 source -> independence-class map from
    ``source_lineage_current``; when given, declared classes seed the lineage
    groups (measured coincidence can only UNION, never split them), undeclared
    sources resolve to the shared ``unclassified`` voice, the shared-upstream
    tier requires a declared namespace match, and GQ-11 copy detections are
    reported as :class:`LineageFinding` — none of it silently independent.

    ``declared_details`` (P35.46) is the same table's kind/evidence detail the
    C1 copy-lineage and C2 documentary gates read; ``demoted_collapses`` is
    the prior run's GQ-23 ``(lineage-or-source, tier)`` demotion set — a
    lineage whose census failed does not auto-collapse again.
    """
    verdicts = fold_human_verdicts(human_items, human_votes)
    rs = rules or CameraSiteRules.from_data()
    gr = geo_rule or load_geo_rules()[0]
    demoted = tuple(demoted_collapses)
    assessed = _assess(
        records,
        rules=rs,
        geo_rule=gr,
        blocking_context=blocking_context,
        declared=declared_lineages,
        declared_details=declared_details,
    )
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
        inferential_tiers=rs.inferential_tiers,
        certified_tiers=certified_tiers,
        # Q-L3-1 = a (ADR-153/ADR-L3-B): the holdout bound is waived for the
        # derivation-collapse tiers — the GQ-23 census re-verifies them.
        eval_waived_tiers=rs.collapse_tiers,
    )
    by_id = {r.subject_id for r in records}
    matched = [v for v in verdicts if v.left in by_id and v.right in by_id]
    decisions, clusters, alerts = cluster_decisions(
        assessed.assessments,
        records,
        auto_write_tiers=auto,
        rules=rs,
        human_verdicts=matched,
        dup_groups=assessed.duplicate_groups,
        demoted_collapses=demoted,
    )
    key = run_key(
        rules=rs,
        auto_write_tiers=auto,
        gold=gold,
        records=records,
        human_verdicts=verdicts,
        declared_lineages=declared_lineages,
        declared_details=declared_details,
        demoted_collapses=demoted,
    )
    # GQ-23 (P35.46): the derivation census runs on EVERY run — every applied
    # collapse re-verified against the record set; failures mint the demotion
    # set the next run consumes. Then the honest count intervals (D05) and
    # the M-1b id-resolution sample frame.
    census = derivation_census(
        records,
        decisions,
        clusters,
        rs,
        lineages=assessed.lineages,
        copy_lineages=assessed.copy_lineages,
        documented_lineages=assessed.documented_lineages,
        measured_overlaps=assessed.measured_overlaps,
        colocation_counts=assessed.colocation_counts,
    )
    intervals = count_intervals(records, decisions, clusters, rs)
    m1b = m1b_sample_frame(decisions, sample_size=rs.m1b_sample_size, seed_salt=key)
    # P35.15a / PKG-07: the declared-technology audit — disagreements between a
    # subject's declared slug and the legacy substring class are findings (the
    # declaration wins classification); subjects still lacking a declaration
    # (pre-backfill) or carrying mixed record_kind subtypes are counted, never
    # silently reconciled.
    findings = device_class_findings(records, rs)
    undeclared = sum(
        1 for r in records if not (r.technology or "").strip() and not r.declared_technologies
    )
    mixed = sum(
        1
        for r in records
        if len({(t or "").strip().lower() for t in r.declared_technologies} - {""}) > 1
    )
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
        duplicate_groups=assessed.duplicate_groups,
        human_verdicts=tuple(matched),
        human_verdicts_unmatched=len(verdicts) - len(matched),
        auto_write_tiers=auto,
        demotions=demotions,
        inferential_tiers=rs.inferential_tiers,
        b5_certified_tiers=frozenset(certified_tiers),
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
        device_class_findings=findings,
        records_without_declared_technology=undeclared,
        mixed_technology_subjects=mixed,
        lineage_findings=assessed.lineage_findings,
        derivation_census=census,
        demoted_collapses=demoted,
        count_intervals=intervals,
        m1b_frame=m1b,
    )
