# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Independent blinded human-evaluation campaign tooling (P32.9, ADR-128).

The pure half of the SIG-EVAL-001/002 campaign protocol. Everything here is
deterministic and dependency-free so the same campaign design reproduces
byte-identically under any caller (CLI, tests, the later HUMAN-H4/H5 staging
steps); the PG writes live in :mod:`resolution.human_eval_pg` and the schema in
``db/deploy/human_eval_campaign.sql``.

Vocabulary (kept strictly separate from the P31.10 *operational* review path —
``review_item``/``review_decision`` carry model proposals and accept/reject
verdicts that steer clustering; this module answers a different question,
"do two records describe the same defined object", and none of its labels can
ever become an operational decision automatically):

* **frame** — the candidate pair universe, described by caller-supplied
  ``FrameItem`` rows carrying the lineage attributes a disjoint split needs
  (entity neighbourhood, upstream source-lineage ids, republisher family,
  mirror/copy group).
* **dependency group** — the transitive closure of pairs sharing any one of
  those keys. Partitions are assigned at *group* granularity so no entity,
  component, copied/mirrored observation or republisher lineage can cross a
  train/test boundary (SIG-EVAL-001).
* **partition** — ``training`` / ``development`` / ``calibration`` / ``pilot`` /
  ``sealed_final``. Whole republisher families named by the design's
  ``holdout_families`` are forced into ``sealed_final`` (the unseen-family
  generalization posture of §55.4).
* **sample** — the drawn labeling set. Each row carries its stratum's
  ``selection_probability`` (= drawn/universe of the partition×stratum cell),
  its inverse ``weight``, a stable ``draw_order`` and an opaque
  ``hev-…`` ``sample_id`` that encodes nothing about stratum, tier or score.
* **packet** — the only thing a reviewer ever sees: a two-sided evidence view
  with randomized orientation and every model/score/tier/label/stratum field
  stripped (:func:`build_blinded_packet` + :func:`assert_blinded`).
* **label** — a human's ``same`` / ``different`` / ``insufficient_evidence``
  verdict. ``insufficient`` is a real, persisted outcome — it never collapses
  to ``same`` and never auto-accepts a pair (:func:`consensus`,
  :func:`to_gold_label`).
* **manifest / watermark** — the campaign's tamper-evident digests:
  :func:`manifest_digest` over the campaign design + the whole sample
  membership (verify against the stored manifest row to detect tampering) and
  :func:`label_watermark`, the chained digest over ordered label payloads.

Nothing in this module recruits a human, authors a label, or marks a campaign
as run — :func:`campaign_state` reports ``prepared``/``provisional`` while
zero human labels exist, which is exactly the engineering-readiness posture
this ticket is allowed to reach (HUMAN-H4/H5 remain separate, later stages).
"""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "PARTITIONS",
    "SEALED_PARTITION",
    "REFERENCE_LABELS",
    "ADJUDICATION_LABELS",
    "ESTIMANDS",
    "REFERENCE_BASES",
    "PACKET_VERSION",
    "FORBIDDEN_PACKET_TOKENS",
    "FrameItem",
    "GroupSpec",
    "SampleSpec",
    "canonical_json",
    "sha256_hex",
    "sample_id_for",
    "dependency_key_parts",
    "build_dependency_groups",
    "homogenize_group_strata",
    "assign_partitions",
    "draw_eval_sample",
    "campaign_design",
    "membership_digest",
    "manifest_digest",
    "build_blinded_packet",
    "assert_blinded",
    "packet_digest",
    "label_digest",
    "label_watermark",
    "consensus",
    "to_gold_label",
    "campaign_state",
]

#: The leakage-safe partitions a frame item may land in. ``sealed_final`` is
#: the confirmatory holdout drawn at P32.22a; its labels stay sealed until an
#: authorized ``human_eval_release`` row unseals them.
PARTITIONS: tuple[str, ...] = (
    "training",
    "development",
    "calibration",
    "pilot",
    "sealed_final",
)
SEALED_PARTITION = "sealed_final"

#: The reference-label vocabulary — deliberately NOT the operational
#: accept/reject vocabulary (SIG-EVAL-002). ``insufficient_evidence`` is a
#: first-class persisted outcome, never an implicit accept.
REFERENCE_LABELS: tuple[str, ...] = ("same", "different", "insufficient_evidence")
#: Adjudications may additionally record ``unresolved`` — a disagreement the
#: adjudicator could not settle stays unresolved rather than being forced.
ADJUDICATION_LABELS: tuple[str, ...] = (*REFERENCE_LABELS, "unresolved")

#: The estimands a drawn item may serve. Each keeps its own frame and
#: denominator (the S3 design: auto-positive precision, candidate recall and
#: final-cluster quality are separate estimands, never pooled).
ESTIMANDS: tuple[str, ...] = (
    "auto_positive_precision",
    "candidate_recall",
    "cluster_quality",
)

#: What "the same" means for a labeled pair. The rubric fixes which question
#: the campaign asks; the basis is recorded per item so a downstream reader
#: never conflates record-deduplication truth with physical-site truth.
REFERENCE_BASES: tuple[str, ...] = (
    "source_record_identity",
    "physical_identity",
    "site_identity",
)

PACKET_VERSION = "eval-packet/1"

#: Key-name tokens a reviewer-visible payload must never contain, at any
#: nesting level (``_``/``-`` separated). Their presence un-blinds: a match
#: tier or model score invites anchoring; a prior label invites agreement;
#: stratum/partition/draw fields leak the sampling design.
FORBIDDEN_PACKET_TOKENS: frozenset[str] = frozenset(
    {
        "tier",
        "score",
        "weight",
        "label",
        "labels",
        "cluster",
        "stratum",
        "probability",
        "prediction",
        "predicted",
        "confidence",
        "model",
        "adjudication",
        "adjudicator",
        "verdict",
        "decision",
        "partition",
        "draw",
        "estimand",
        "match",
        "rule",
        "distance",
        "rank",
        "threshold",
        "proposal",
        "review",
        "prompt",
    }
)

_BLINDED_SIDE_KEYS: frozenset[str] = frozenset(
    {
        "latitude",
        "longitude",
        "external_ref",
        "name",
        "roadway",
        "direction",
        "operator",
        "jurisdiction",
        "camera_type",
        "source_id",
        "capture_refs",
        "observed_at",
    }
)


def canonical_json(obj: Any) -> str:
    """The deterministic serialization every digest in this module shares."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sample_id_for(campaign_id: str, pair_id: str) -> str:
    """The opaque sample id — a bare digest that encodes no stratum/tier."""
    return "hev-" + sha256_hex(f"{campaign_id}|{pair_id}")[:16]


@dataclass(frozen=True)
class FrameItem:
    """One candidate pair in the evaluation frame.

    ``pair_id`` is the caller's stable identity for the pair (e.g. a
    ``{left}:{right}`` join or an upstream proposal id — it is internal
    metadata, never shown to reviewers). The four lineage attributes are the
    disjointness inputs: any shared value lands both pairs in one dependency
    group, so related pairs can never cross a partition boundary.
    """

    pair_id: str
    left_ref: str
    right_ref: str
    stratum_id: str
    estimand: str = "auto_positive_precision"
    reference_basis: str = "physical_identity"
    #: A shared entity/component neighbourhood (e.g. the resolved site or the
    #: blocking cell) — two pairs whose unions touch the same neighbourhood
    #: are dependent.
    entity_neighborhood: str = ""
    #: Upstream source-record lineage of EITHER side (source ids, upstream
    #: feed ids). Any shared element makes the pairs dependent.
    source_lineage_ids: tuple[str, ...] = ()
    #: The republisher/mirror family a source belongs to ("" = its own family).
    republisher_family: str = ""
    #: An explicit copied/mirrored-observation group id ("" = none).
    mirror_group_id: str = ""

    def validate(self) -> None:
        if not self.pair_id:
            raise ValueError("frame item needs a pair_id")
        if self.estimand not in ESTIMANDS:
            raise ValueError(f"unknown estimand {self.estimand!r} (known: {ESTIMANDS})")
        if self.reference_basis not in REFERENCE_BASES:
            raise ValueError(
                f"unknown reference_basis {self.reference_basis!r} (known: {REFERENCE_BASES})"
            )


def dependency_key_parts(item: FrameItem) -> tuple[str, ...]:
    """The group-merge keys one frame item contributes.

    A pair joins a dependency group when it shares ANY key with another pair:
    same subject entity (either side), same entity/component neighbourhood,
    any shared upstream lineage id, same republisher family, or same explicit
    mirror group. The empty optional values emit nothing.
    """
    keys: list[str] = []
    if item.entity_neighborhood:
        keys.append(f"nbr:{item.entity_neighborhood}")
    keys.extend(f"lineage:{lid}" for lid in item.source_lineage_ids if lid)
    if item.republisher_family:
        keys.append(f"repub:{item.republisher_family}")
    if item.mirror_group_id:
        keys.append(f"mirror:{item.mirror_group_id}")
    return tuple(keys)


def _ordered_keys(item: FrameItem) -> tuple[str, ...]:
    """All group keys plus subject + pair anchors.

    ``sub:`` keys are the entity-disjointness rule: two pairs that share a
    subject entity (either side) can never cross a partition boundary. The
    ``pair:`` anchor gives singleton groups a stable existence.
    """
    return (
        f"sub:{item.left_ref}",
        f"sub:{item.right_ref}",
        *dependency_key_parts(item),
        f"pair:{item.pair_id}",
    )


def build_dependency_groups(items: Sequence[FrameItem]) -> dict[str, list[str]]:
    """Union-find transitive closure of pairs over the dependency keys.

    Returns ``{group_id: [pair_id, ...]}`` — ``group_id`` is a digest of the
    member pair ids, so it is stable for identical input and meaningless for
    anything else. Any two pairs sharing an entity neighbourhood, an upstream
    lineage id, a republisher family or a mirror group land in the same group
    (transitively — A~B and B~C groups A with C).
    """
    parent: dict[str, str] = {}
    key_anchor: dict[str, str] = {}

    def find(p: str) -> str:
        while parent[p] != p:
            parent[p] = parent[parent[p]]  # path halving
            p = parent[p]
        return p

    for item in sorted(items, key=lambda i: i.pair_id):
        item.validate()
        parent.setdefault(item.pair_id, item.pair_id)
        for key in _ordered_keys(item):
            anchor = key_anchor.setdefault(key, item.pair_id)
            if anchor != item.pair_id:
                ra, rb = find(anchor), find(item.pair_id)
                if ra != rb:
                    # Union by deterministic order — smaller root wins.
                    keep, drop = (ra, rb) if ra < rb else (rb, ra)
                    parent[drop] = keep

    members: dict[str, list[str]] = {}
    for item in sorted(items, key=lambda i: i.pair_id):
        members.setdefault(find(item.pair_id), []).append(item.pair_id)

    groups: dict[str, list[str]] = {}
    for pair_ids in members.values():
        ordered = sorted(pair_ids)
        gid = "dg-" + sha256_hex("|".join(ordered))[:16]
        groups[gid] = ordered
    return dict(sorted(groups.items()))


def homogenize_group_strata(items: Sequence[FrameItem]) -> list[FrameItem]:
    """Rewrite every group's members to the group's minimum stratum id.

    Partitions are assigned at group granularity, so a group that legitimately
    spans strata (e.g. two pairs sharing a subject but drawn under different
    proposal strata) needs ONE stratum before :func:`assign_partitions` and
    the per-(partition,stratum) denominators can treat it consistently. The
    group's stratum becomes ``min(members' strata)`` — deterministic, and the
    rewrite is part of the recorded design, never a silent re-stratification.
    """
    groups = build_dependency_groups(items)
    by_pair = {i.pair_id: i for i in items}
    group_stratum = {
        gid: min(by_pair[p].stratum_id for p in pairs) for gid, pairs in groups.items()
    }
    pair_group = {p: gid for gid, pairs in groups.items() for p in pairs}
    return [
        FrameItem(
            pair_id=i.pair_id,
            left_ref=i.left_ref,
            right_ref=i.right_ref,
            stratum_id=group_stratum[pair_group[i.pair_id]],
            estimand=i.estimand,
            reference_basis=i.reference_basis,
            entity_neighborhood=i.entity_neighborhood,
            source_lineage_ids=i.source_lineage_ids,
            republisher_family=i.republisher_family,
            mirror_group_id=i.mirror_group_id,
        )
        for i in items
    ]


@dataclass(frozen=True)
class GroupSpec:
    """The partition-allocation design the campaign preregisters.

    ``fractions`` maps partition → share of each stratum's groups. Leftover
    share lands in ``training``. ``holdout_families`` forces every group
    touching a named republisher family into ``sealed_final`` — the
    unseen-family generalization holdout (SIG-EVAL-001). ``per_stratum`` may
    override fractions for named strata.
    """

    fractions: Mapping[str, float] = field(
        default_factory=lambda: {
            "training": 0.5,
            "development": 0.2,
            "calibration": 0.1,
            "pilot": 0.05,
            "sealed_final": 0.15,
        }
    )
    holdout_families: tuple[str, ...] = ()
    per_stratum: Mapping[str, Mapping[str, float]] = field(default_factory=dict)

    def validate(self) -> None:
        for name, frac in self.fractions.items():
            if name not in PARTITIONS:
                raise ValueError(f"unknown partition {name!r} (known: {PARTITIONS})")
            if not 0.0 <= frac <= 1.0:
                raise ValueError(f"partition {name!r} fraction {frac} outside [0,1]")
        if sum(self.fractions.values()) > 1.0 + 1e-9:
            raise ValueError("partition fractions sum above 1.0")


@dataclass(frozen=True)
class SampleSpec:
    """The preregistered sample design.

    ``quotas`` maps partition → items-per-stratum target (None = census of the
    partition's stratum members). ``denominators`` are recomputed from the
    frame and persisted with the manifest — the population each
    ``selection_probability`` is drawn against must survive the campaign.
    """

    quotas: Mapping[str, int | None] = field(default_factory=dict)


def assign_partitions(
    items: Sequence[FrameItem],
    *,
    seed: str,
    spec: GroupSpec,
) -> dict[str, str]:
    """Assign every pair to a partition at dependency-group granularity.

    Whole groups move together (transitively disjoint by construction).
    Within each stratum the groups are ordered by ``sha256(seed|stratum|gid)``
    and allocated to partitions to meet the spec's per-stratum fraction
    targets (largest-unmet-deficit first, fixed partition order on ties), so
    each partition keeps a proportional stratum mix and a repeated draw over
    the same frame+seed is identical. Groups touching a ``holdout_families``
    family are forced into ``sealed_final`` before any fraction bookkeeping.
    """
    spec.validate()
    groups = build_dependency_groups(items)
    by_pair = {i.pair_id: i for i in items}
    group_stratum: dict[str, str] = {}
    forced: dict[str, str] = {}
    for gid, pair_ids in groups.items():
        strata = {by_pair[p].stratum_id for p in pair_ids}
        if len(strata) != 1:
            raise ValueError(
                f"dependency group {gid} spans strata {sorted(strata)} — run "
                "homogenize_group_strata() first (a group must be homogeneous "
                "for the split to be whole-group and stratum-proportional)"
            )
        group_stratum[gid] = next(iter(strata))
        families = {by_pair[p].republisher_family for p in pair_ids}
        if families & set(spec.holdout_families):
            forced[gid] = SEALED_PARTITION

    assignment: dict[str, str] = dict(forced)
    by_stratum: dict[str, list[str]] = {}
    for gid, stratum in group_stratum.items():
        if gid in forced:
            continue
        by_stratum.setdefault(stratum, []).append(gid)

    # Deterministic fill order: largest deficit first, fixed partition order.
    partition_order = [p for p in PARTITIONS if p != "training"]
    for stratum, gids in sorted(by_stratum.items()):
        fractions = dict(spec.fractions)
        fractions.update(spec.per_stratum.get(stratum, {}))
        ordered = sorted(gids, key=lambda g: sha256_hex(f"{seed}|{stratum}|{g}"))
        n = len(ordered)
        targets: dict[str, int] = {}
        remainder = n
        for name in partition_order:
            targets[name] = min(remainder, int(round(n * fractions.get(name, 0.0))))
            remainder -= targets[name]
        assigned: dict[str, int] = {p: 0 for p in PARTITIONS}

        def deficit(
            part: str,
            targets: dict[str, int] = targets,
            assigned: dict[str, int] = assigned,
        ) -> int:
            return targets.get(part, 0) - assigned[part]

        for gid in ordered:
            part = max(
                partition_order,
                key=lambda p: (deficit(p), -partition_order.index(p)),
            )
            if deficit(part) <= 0:
                part = "training"
            assignment[gid] = part
            assigned[part] += 1

    return {pair_id: assignment[gid] for gid, pair_ids in groups.items() for pair_id in pair_ids}


def draw_eval_sample(
    items: Sequence[FrameItem],
    partitions: Mapping[str, str],
    *,
    campaign_id: str,
    seed: str,
    spec: SampleSpec,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Draw the labeled-sample rows + the persisted denominators.

    For every (partition, stratum) cell the candidates are the frame items
    assigned to that cell; the draw is a seeded shuffle of the sorted pair ids
    truncated to the spec's per-partition quota (None quota = the whole cell —
    a census still records p=1.0 honestly). Each drawn item records
    ``selection_probability`` = cell drawn ÷ cell universe and ``weight`` =
    its inverse, plus a deterministic global ``draw_order``. Returns
    ``(sample_rows, denominators)`` — the rows are ready for
    ``human_eval_sample`` and the denominators ride the manifest row.
    """
    cells: dict[tuple[str, str], list[FrameItem]] = {}
    for item in sorted(items, key=lambda i: i.pair_id):
        item.validate()
        part = partitions.get(item.pair_id)
        if part is None:
            raise ValueError(f"frame pair {item.pair_id!r} has no partition assignment")
        cells.setdefault((part, item.stratum_id), []).append(item)

    # Pair → dependency-group id, computed once over the same frame.
    groups = build_dependency_groups(items)
    pair_group = {p: g for g, pairs in groups.items() for p in pairs}

    rows: list[dict[str, Any]] = []
    denominators: dict[str, Any] = {}
    for (part, stratum), cell in sorted(cells.items()):
        quota = spec.quotas.get(part)
        universe = len(cell)
        ids = [i.pair_id for i in cell]
        rng = random.Random(f"{seed}|{part}|{stratum}")
        shuffled = list(ids)
        rng.shuffle(shuffled)
        drawn = shuffled if quota is None else shuffled[: min(quota, universe)]
        drawn_set = set(drawn)
        p = (len(drawn) / universe) if universe else 0.0
        denominators.setdefault(part, {})[stratum] = {
            "universe": universe,
            "drawn": len(drawn),
        }
        for item in cell:
            if item.pair_id not in drawn_set:
                continue
            rows.append(
                {
                    "campaign_id": campaign_id,
                    "sample_id": sample_id_for(campaign_id, item.pair_id),
                    "pair_id": item.pair_id,
                    "left_ref": item.left_ref,
                    "right_ref": item.right_ref,
                    "partition": part,
                    "estimand": item.estimand,
                    "stratum_id": item.stratum_id,
                    "dependency_group_id": pair_group[item.pair_id],
                    "source_lineage_ids": sorted(set(item.source_lineage_ids)),
                    "selection_probability": p,
                    "weight": (universe / len(drawn)) if drawn else None,
                    "draw_order": None,  # filled below, deterministic global order
                    "reference_basis": item.reference_basis,
                }
            )

    # Global draw order: stable over (partition, stratum, seeded order index).
    rows.sort(key=lambda r: (r["partition"], r["stratum_id"], r["pair_id"]))
    order_rng = random.Random(f"{seed}|order")
    order_rng.shuffle(rows)
    for i, row in enumerate(rows):
        row["draw_order"] = i
    rows.sort(key=lambda r: r["draw_order"])
    return rows, denominators


def campaign_design(
    *,
    purpose: str,
    protocol_digest: str,
    frame_snapshot: str,
    ruleset_digest: str,
    seed: str,
    group_spec: GroupSpec,
    sample_spec: SampleSpec,
    target_population: str,
    rubric_version: str,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The preregistered design document stored on ``human_eval_campaign``.

    Frozen before any label exists: the snapshot identity, the population the
    sample speaks for, the strata, the grouping/split rules, the seed and the
    ruleset/protocol digests. A changed ruleset or an unblinded test set means
    a NEW campaign + design — never an edit (SIG-EVAL-001).
    """
    design = {
        "purpose": purpose,
        "protocol_digest": protocol_digest,
        "frame_snapshot": frame_snapshot,
        "ruleset_digest": ruleset_digest,
        "seed": seed,
        "target_population": target_population,
        "rubric_version": rubric_version,
        "group_spec": {
            "fractions": dict(group_spec.fractions),
            "holdout_families": sorted(group_spec.holdout_families),
            "per_stratum": {k: dict(v) for k, v in group_spec.per_stratum.items()},
        },
        "sample_spec": {"quotas": dict(sample_spec.quotas)},
        "estimands": list(ESTIMANDS),
        "reference_bases": list(REFERENCE_BASES),
        "partitions": list(PARTITIONS),
    }
    if extra:
        design["extra"] = dict(extra)
    return design


def _sample_digestable(row: Mapping[str, Any]) -> dict[str, Any]:
    """The canonical sample-row projection the manifest digest covers."""
    return {
        "sample_id": row["sample_id"],
        "pair_id": row.get("pair_id"),
        "left_ref": row.get("left_ref"),
        "right_ref": row.get("right_ref"),
        "partition": row["partition"],
        "estimand": row["estimand"],
        "stratum_id": row["stratum_id"],
        "dependency_group_id": row["dependency_group_id"],
        "source_lineage_ids": sorted(row.get("source_lineage_ids") or []),
        "selection_probability": row["selection_probability"],
        "weight": row.get("weight"),
        "draw_order": row["draw_order"],
        "reference_basis": row["reference_basis"],
        "packet_digest": row.get("packet_digest"),
    }


def membership_digest(sample_rows: Sequence[Mapping[str, Any]]) -> str:
    """Digest over the drawn membership (draw_order-sorted canonical rows)."""
    ordered = sorted(sample_rows, key=lambda r: r["draw_order"])
    return sha256_hex(canonical_json([_sample_digestable(r) for r in ordered]))


def manifest_digest(
    campaign: Mapping[str, Any],
    sample_rows: Sequence[Mapping[str, Any]],
) -> str:
    """The campaign's tamper-evident digest: design + full membership.

    Covers the campaign's identifying fields and every sample row's
    digestable projection. Recomputed over live rows it must equal the stored
    ``human_eval_manifest.manifest_digest`` — any edit to the design, a sample
    row's partition/stratum/probability, or the membership itself is detected
    (SIG-EVAL-001 "manifest tampering is detected").
    """
    payload = {
        "campaign_id": campaign["campaign_id"],
        "purpose": campaign.get("purpose"),
        "design": campaign.get("design"),
        "membership_digest": membership_digest(sample_rows),
        "sample_count": len(sample_rows),
    }
    return sha256_hex(canonical_json(payload))


# --------------------------------------------------------------------------- #
# Blinded packets — the only artifact a reviewer ever sees                      #
# --------------------------------------------------------------------------- #
def _key_forbidden(key: str) -> bool:
    tokens = {t for t in key.lower().replace("-", "_").split("_") if t}
    return bool(tokens & FORBIDDEN_PACKET_TOKENS)


def _sanitize(value: Any, path: str) -> Any:
    """Recursively drop forbidden keys; raise-free, silently omitting."""
    if isinstance(value, Mapping):
        out = {}
        for k, v in value.items():
            ks = str(k)
            if _key_forbidden(ks):
                continue
            out[ks] = _sanitize(v, f"{path}.{ks}")
        return out
    if isinstance(value, (list, tuple)):
        return [_sanitize(v, f"{path}[]") for v in value]
    return value


def _scan_forbidden(value: Any, path: str = "") -> list[str]:
    """The verifier's scan: list every forbidden key found (for assertion)."""
    hits: list[str] = []
    if isinstance(value, Mapping):
        for k, v in value.items():
            ks = str(k)
            if _key_forbidden(ks):
                hits.append(f"{path}.{ks}" if path else ks)
            hits.extend(_scan_forbidden(v, f"{path}.{ks}" if path else ks))
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            hits.extend(_scan_forbidden(v, f"{path}[{i}]"))
    return hits


def build_blinded_packet(
    *,
    sample_id: str,
    seed: str,
    left_evidence: Mapping[str, Any],
    right_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """The reviewer-facing two-sided evidence packet.

    Randomizes which side is "A" vs "B" from the campaign seed + sample id
    (reproducible for the same campaign, different across seeds/samples) and
    sanitizes both sides recursively — model tier/score/weight, prior labels,
    strata, probabilities, predictions and adjudication fields can never
    reach the payload. Only observation evidence survives (coordinates, name,
    roadway, operator, jurisdiction, type, external ref, source identity,
    capture refs). Internal pair/subject refs stay OUT — the reviewer weighs
    evidence, never ids.
    """
    flip = int(sha256_hex(f"{seed}|{sample_id}|orient")[:8], 16) % 2 == 1
    a_raw, b_raw = (right_evidence, left_evidence) if flip else (left_evidence, right_evidence)
    side_a = _sanitize(dict(a_raw), "side_a")
    side_b = _sanitize(dict(b_raw), "side_b")
    payload: dict[str, Any] = {
        "packet_version": PACKET_VERSION,
        "side_a": side_a,
        "side_b": side_b,
    }
    assert_blinded(payload)
    return payload


def assert_blinded(payload: Mapping[str, Any]) -> None:
    """Raise ``ValueError`` if a reviewer payload carries any forbidden key."""
    hits = _scan_forbidden(payload)
    if hits:
        raise ValueError("unblinded packet field(s) present: " + ", ".join(sorted(hits)))


def packet_digest(payload: Mapping[str, Any]) -> str:
    """The digest of a blinded packet — recorded on the sample + every label."""
    assert_blinded(payload)
    return "sha256:" + sha256_hex(canonical_json(payload))


# --------------------------------------------------------------------------- #
# Labels, adjudication, watermark                                              #
# --------------------------------------------------------------------------- #
def label_digest(
    *,
    campaign_id: str,
    sample_id: str,
    reviewer_id: str,
    round: str,
    label: str,
    reason_codes: Sequence[str],
    evidence_refs: Sequence[Mapping[str, Any]],
    rubric_version: str,
    packet_digest: str,
) -> str:
    """Per-label content digest — the watermark chain's unit."""
    if label not in REFERENCE_LABELS:
        raise ValueError(f"unknown reference label {label!r} (known: {REFERENCE_LABELS})")
    return sha256_hex(
        canonical_json(
            {
                "campaign_id": campaign_id,
                "sample_id": sample_id,
                "reviewer_id": reviewer_id,
                "round": round,
                "label": label,
                "reason_codes": sorted(reason_codes),
                "evidence_refs": list(evidence_refs),
                "rubric_version": rubric_version,
                "packet_digest": packet_digest,
            }
        )
    )


def label_watermark(labels: Sequence[Mapping[str, Any]]) -> str:
    """The chained watermark over a campaign's ordered label digests.

    Order is the append order (label seq/recorded order the caller supplies —
    callers pass rows ordered by the identity seq). Tampering with, dropping
    or reordering any label changes the chain.
    """
    state = sha256_hex("human-eval-label-watermark/1")
    for row in labels:
        state = sha256_hex(f"{state}|{row['label_digest']}")
    return "sha256:" + state


def consensus(labels: Sequence[str]) -> str:
    """The two-independent-label outcome per the S3 adjudication design.

    Two equal definite judgments yield the reference label. ANY disagreement
    or ANY ``insufficient_evidence`` proceeds to adjudication — abstention is
    preserved, never collapsed into agreement, and ``insufficient`` can never
    produce ``same`` (the "cannot auto-accept a pair" invariant).
    """
    vals = [lab for lab in labels if lab]
    for lab in vals:
        if lab not in REFERENCE_LABELS:
            raise ValueError(f"unknown label {lab!r}")
    if len(vals) < 2:
        return "awaiting_labels"
    first_two = vals[:2]
    if first_two[0] == first_two[1] and first_two[0] in ("same", "different"):
        return first_two[0]
    return "needs_adjudication"


def to_gold_label(label: str) -> str | None:
    """Map a reference label onto the evaluator's gold-set vocabulary.

    ``same`` → ``match``, ``different`` → ``non_match``. ``insufficient`` is
    deliberately EXCLUDED (``None``) — an abstention is not evidence either
    way and must never silently count as a match or a miss.
    """
    if label == "same":
        return "match"
    if label == "different":
        return "non_match"
    if label == "insufficient_evidence":
        return None
    raise ValueError(f"unknown reference label {label!r}")


def campaign_state(
    *,
    label_count: int,
    adjudication_count: int = 0,
    released: bool = False,
) -> str:
    """The honest lifecycle state a campaign may report.

    ``prepared`` — tooling complete, zero human labels (this ticket's end
    state). ``provisional`` — some labels exist but no authorized release.
    ``unsealed`` — an authorized release row exists (labels may feed the
    readout). A campaign never reports "done" without a release; engineering
    artifacts alone can never move it past ``provisional``.
    """
    if released:
        return "unsealed"
    if label_count == 0:
        return "prepared"
    return "provisional"
