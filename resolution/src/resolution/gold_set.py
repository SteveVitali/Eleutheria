# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The gold-standard label set with a frozen holdout (SIG-IDENT-027).

The gold set is the ground truth the quality gates (:mod:`resolution.quality_gates`)
measure the matcher against. Building it faithfully is what makes the precision/recall
numbers meaningful, so the spec pins its construction and this module enforces it:

* **Stratified sampling across match-weight bands** (:func:`stratified_sample`). A
  uniform sample of blocked pairs is nearly all easy high-weight matches; stratifying
  by weight band forces coverage of the low/ambiguous pairs around the decision
  threshold, where the model actually needs measuring.
* **A three-value label vocabulary** (:class:`GoldLabel`): ``match`` / ``non_match`` /
  ``not_enough_information`` — the third value records honest uncertainty instead of a
  forced guess.
* **Double adjudication with Cohen's κ** (:func:`cohens_kappa`): two adjudicators label
  each pair independently; κ reports their chance-corrected agreement.
* **Per-label provenance**: every label carries who assigned it, when, and against
  which ruleset version (:class:`Adjudication`).
* **A frozen holdout** (:meth:`GoldSet.holdout`): a versioned partition that is
  immutable and never used to tune the model — re-labelling a frozen pair raises.

Everything here is pure and deterministic (sampling and the holdout split take an
explicit seed), so a committed gold set is reproducible and diffable.
"""

from __future__ import annotations

import random
import tomllib
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from enum import StrEnum
from functools import cache
from importlib.resources import files
from typing import Any

__all__ = [
    "GOLD_SET_RULES_VERSION",
    "GoldLabel",
    "WeightBand",
    "Adjudication",
    "GoldPair",
    "GoldSet",
    "bands_from_data",
    "assign_band",
    "stratified_sample",
    "cohens_kappa",
    "adjudicated_label",
    "adjudication_rules",
    "build_gold_set",
]


@cache
def _rules() -> dict[str, Any]:
    resource = files("resolution").joinpath("data", "gold_set_rules.toml")
    with resource.open("rb") as fh:
        return tomllib.load(fh)


GOLD_SET_RULES_VERSION: str = str(_rules()["version"])


class GoldLabel(StrEnum):
    """The three-value adjudication vocabulary (SIG-IDENT-027)."""

    MATCH = "match"
    NON_MATCH = "non_match"
    NOT_ENOUGH_INFORMATION = "not_enough_information"


def adjudication_rules() -> str:
    """The written adjudication rules an adjudicator reads (versioned prose data)."""
    return str(_rules()["adjudication_rules"]).strip()


@dataclass(frozen=True)
class WeightBand:
    """A match-weight band for stratified sampling. ``min_weight`` is inclusive."""

    name: str
    min_weight: float


def bands_from_data() -> tuple[WeightBand, ...]:
    """The committed weight bands, ordered most-confident first."""
    bands = tuple(
        WeightBand(name=str(b["name"]), min_weight=float(b["min_weight"])) for b in _rules()["band"]
    )
    return tuple(sorted(bands, key=lambda b: b.min_weight, reverse=True))


def assign_band(weight: float, bands: Sequence[WeightBand]) -> str:
    """The name of the first (highest) band whose ``min_weight`` ``weight`` meets."""
    for band in sorted(bands, key=lambda b: b.min_weight, reverse=True):
        if weight >= band.min_weight:
            return band.name
    raise ValueError(f"weight {weight} falls below every band floor")


def stratified_sample(
    scored: Mapping[str, float],
    *,
    bands: Sequence[WeightBand] | None = None,
    per_band: int | None = None,
    seed: int = 0,
) -> dict[str, list[str]]:
    """Sample up to ``per_band`` pair ids from each weight band (SIG-IDENT-027).

    ``scored`` maps a candidate-pair id to its match weight. Returns band name → the
    sampled pair ids in that band (a band with fewer than ``per_band`` members
    contributes all of them). Sampling is seeded, so the draw is reproducible.
    """
    band_defs = tuple(bands) if bands is not None else bands_from_data()
    count = per_band if per_band is not None else int(_rules()["sample_per_band"])
    buckets: dict[str, list[str]] = defaultdict(list)
    for pair_id in sorted(scored):
        buckets[assign_band(scored[pair_id], band_defs)].append(pair_id)
    out: dict[str, list[str]] = {}
    for band in band_defs:
        members = buckets.get(band.name, [])
        rng = random.Random(f"{seed}:{band.name}")
        if len(members) <= count:
            out[band.name] = list(members)
        else:
            out[band.name] = sorted(rng.sample(members, count))
    return out


def cohens_kappa(a: Sequence[GoldLabel], b: Sequence[GoldLabel]) -> float:
    """Cohen's κ between two adjudicators' label sequences (SIG-IDENT-027).

    ``κ = (p_o − p_e) / (1 − p_e)`` where ``p_o`` is observed agreement and ``p_e`` is
    the agreement expected by chance from each adjudicator's marginal label rates.
    Returns ``1.0`` for perfect agreement when there is no chance disagreement to
    correct for (both adjudicators used a single label identically).
    """
    if len(a) != len(b):
        raise ValueError("the two adjudicators must label the same pairs")
    n = len(a)
    if n == 0:
        raise ValueError("Cohen's kappa needs at least one labelled pair")
    categories = list(GoldLabel)
    observed = sum(1 for x, y in zip(a, b, strict=True) if x == y) / n
    expected = sum(
        (sum(1 for x in a if x == c) / n) * (sum(1 for y in b if y == c) / n) for c in categories
    )
    if expected == 1.0:
        return 1.0
    return (observed - expected) / (1.0 - expected)


def adjudicated_label(adjudications: Sequence[Adjudication]) -> GoldLabel | None:
    """The consensus label from a pair's adjudications, or ``None`` on disagreement.

    Requires at least two independent adjudications (double adjudication). Returns the
    shared label when every adjudicator agrees; ``None`` when they disagree (the pair
    is then a disputed pair the caller surfaces, never a silent pick).
    """
    if len({a.adjudicator for a in adjudications}) < 2:
        raise ValueError("double adjudication requires two distinct adjudicators")
    labels = {a.label for a in adjudications}
    return next(iter(labels)) if len(labels) == 1 else None


@dataclass(frozen=True)
class Adjudication:
    """One adjudicator's label for one pair, with its provenance (SIG-IDENT-027)."""

    pair_id: str
    adjudicator: str
    label: GoldLabel
    dated: date
    ruleset_version: str
    note: str = ""


@dataclass(frozen=True)
class GoldPair:
    """A gold-set pair: its band, agreed label, adjudication provenance, frozen flag."""

    pair_id: str
    weight: float
    band: str
    label: GoldLabel | None
    provenance: tuple[Adjudication, ...]
    frozen: bool = False

    @property
    def disputed(self) -> bool:
        return self.label is None


@dataclass(frozen=True)
class GoldSet:
    """A versioned gold set with a frozen holdout (SIG-IDENT-027)."""

    version: str
    rules_version: str
    pairs: tuple[GoldPair, ...]
    seed: int = 0

    def by_id(self, pair_id: str) -> GoldPair:
        for pair in self.pairs:
            if pair.pair_id == pair_id:
                return pair
        raise KeyError(pair_id)

    def holdout(self) -> tuple[GoldPair, ...]:
        """The frozen holdout partition — the evaluation set (SIG-IDENT-028)."""
        return tuple(p for p in self.pairs if p.frozen)

    def training(self) -> tuple[GoldPair, ...]:
        """The non-frozen partition, usable for tuning."""
        return tuple(p for p in self.pairs if not p.frozen)

    def labelled(self) -> tuple[GoldPair, ...]:
        """Pairs with an agreed (non-disputed) label."""
        return tuple(p for p in self.pairs if p.label is not None)

    def kappa(self, adjudicator_a: str, adjudicator_b: str) -> float:
        """Cohen's κ between two named adjudicators over the pairs both labelled."""
        seq_a: list[GoldLabel] = []
        seq_b: list[GoldLabel] = []
        for pair in self.pairs:
            la = _label_by(pair, adjudicator_a)
            lb = _label_by(pair, adjudicator_b)
            if la is not None and lb is not None:
                seq_a.append(la)
                seq_b.append(lb)
        return cohens_kappa(seq_a, seq_b)

    def relabel(self, pair_id: str, label: GoldLabel) -> GoldSet:
        """Return a new gold set with ``pair_id`` relabelled — refused if frozen.

        The frozen holdout is immutable (SIG-IDENT-027): relabelling a holdout pair
        raises, so a run can never quietly tune against the evaluation set.
        """
        pair = self.by_id(pair_id)
        if pair.frozen:
            raise ValueError(
                f"gold pair {pair_id!r} is in the frozen holdout and MUST NOT be "
                "relabelled (SIG-IDENT-027)"
            )
        updated = tuple(replace(p, label=label) if p.pair_id == pair_id else p for p in self.pairs)
        return replace(self, pairs=updated)


def _label_by(pair: GoldPair, adjudicator: str) -> GoldLabel | None:
    for adj in pair.provenance:
        if adj.adjudicator == adjudicator:
            return adj.label
    return None


def _freeze_holdout(pair_ids: Sequence[str], *, fraction: float, seed: int) -> frozenset[str]:
    ids = sorted(pair_ids)
    k = int(round(len(ids) * fraction))
    if not ids or k == 0:
        return frozenset()
    rng = random.Random(f"{seed}:holdout")
    return frozenset(rng.sample(ids, k))


def build_gold_set(
    *,
    weights: Mapping[str, float],
    adjudications: Sequence[Adjudication],
    bands: Sequence[WeightBand] | None = None,
    holdout_fraction: float | None = None,
    seed: int = 0,
    version: str = "1",
) -> GoldSet:
    """Assemble a versioned gold set from weights + double adjudications.

    Each pair's agreed label is the consensus of its (≥2) adjudications, or ``None``
    when they disagree. A frozen holdout of ``holdout_fraction`` of the pairs is drawn
    (seeded, reproducible). Every pair carries its band and its full adjudication
    provenance.
    """
    band_defs = tuple(bands) if bands is not None else bands_from_data()
    fraction = (
        holdout_fraction if holdout_fraction is not None else float(_rules()["holdout_fraction"])
    )
    by_pair: dict[str, list[Adjudication]] = defaultdict(list)
    for adj in adjudications:
        by_pair[adj.pair_id].append(adj)

    holdout_ids = _freeze_holdout(list(by_pair), fraction=fraction, seed=seed)
    pairs: list[GoldPair] = []
    for pair_id in sorted(by_pair):
        weight = float(weights[pair_id])
        pairs.append(
            GoldPair(
                pair_id=pair_id,
                weight=weight,
                band=assign_band(weight, band_defs),
                label=adjudicated_label(by_pair[pair_id]),
                provenance=tuple(by_pair[pair_id]),
                frozen=pair_id in holdout_ids,
            )
        )
    return GoldSet(
        version=version,
        rules_version=GOLD_SET_RULES_VERSION,
        pairs=tuple(pairs),
        seed=seed,
    )
