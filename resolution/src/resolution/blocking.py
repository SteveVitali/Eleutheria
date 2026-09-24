# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Sized blocking for the probabilistic matcher (SIG-IDENT-023/024).

Blocking is candidate *generation*: it narrows the O(n²) all-pairs comparison to
the pairs worth scoring. Two rules from the spec govern it, and both are enforced
here rather than left to convention:

* **SIG-IDENT-023 — blocking rules are sized before use.** A rule that generates
  more candidate comparisons than a documented ceiling is *rejected*, not run: an
  unsized blocking rule is how an ER run silently turns into an all-pairs scan.
  Blocking on **suffix alone or state alone is prohibited** — those keys are so
  low-cardinality that they block almost nothing (a state-alone rule pairs every
  agency in the state with every other).
* **SIG-IDENT-024 — trigram similarity MAY power candidate search but MUST NOT be
  a decision score.** A trigram blocking rule is allowed *here* (it only decides
  which pairs to look at); the guard against trigram reaching the decision score
  lives with the model (:func:`resolution.probabilistic.assert_no_trigram_decision`).

The sizer counts the deduplication candidate pairs a rule yields over a record
set — ``sum(C(n, 2))`` across blocks — which is the exact number of comparisons
Splink would materialise, so the ceiling is a real bound on work, not an estimate.
"""

from __future__ import annotations

import math
import tomllib
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import cache
from importlib.resources import files
from itertools import combinations
from typing import Any

__all__ = [
    "BlockingRule",
    "BlockingContext",
    "GeoGridRule",
    "geo_grid_pairs",
    "load_geo_rules",
    "validate_geo_rule",
    "BlockingRuleRejected",
    "block_key",
    "size_blocking_rule",
    "candidate_pairs",
    "validate_blocking_rule",
    "blocked_pairs",
    "load_rules",
    "trigrams",
]

Record = Mapping[str, Any]


@cache
def _rules() -> dict[str, Any]:
    resource = files("resolution").joinpath("data", "blocking_rules.toml")
    with resource.open("rb") as fh:
        return tomllib.load(fh)


class BlockingRuleRejected(ValueError):
    """A blocking rule failed sizing or is a prohibited low-cardinality rule."""


@dataclass(frozen=True)
class BlockingRule:
    """One blocking rule: the keys whose shared value defines a candidate block.

    ``method`` is ``"equijoin"`` (records share the exact value of every key) or
    ``"trigram"`` (records share at least one character trigram of the single
    ``keys`` column — a candidate-search path only, never a decision score,
    SIG-IDENT-024). ``rule_id`` names it for the run record and evidence.
    """

    rule_id: str
    keys: tuple[str, ...]
    method: str = "equijoin"
    description: str = ""

    def __post_init__(self) -> None:
        if not self.keys:
            raise BlockingRuleRejected(f"blocking rule {self.rule_id!r} names no keys")
        if self.method not in ("equijoin", "trigram"):
            raise BlockingRuleRejected(
                f"blocking rule {self.rule_id!r}: unknown method {self.method!r}"
            )
        if self.method == "trigram" and len(self.keys) != 1:
            raise BlockingRuleRejected(
                f"trigram blocking rule {self.rule_id!r} takes exactly one key"
            )


@dataclass(frozen=True)
class BlockingContext:
    """The documented sizing ceiling and the prohibited sole-key list (data).

    Injectable so tests can supply their own without touching code, mirroring
    :class:`resolution.cascade.CascadeContext`.
    """

    comparison_ceiling: int = 1_000_000
    prohibited_sole_keys: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_data(cls) -> BlockingContext:
        rules = _rules()
        return cls(
            comparison_ceiling=int(rules["comparison_ceiling"]),
            prohibited_sole_keys=frozenset(rules["prohibited_sole_keys"]),
        )


def trigrams(value: str) -> frozenset[str]:
    """The set of 3-character trigrams of ``value`` (blank-padded), lower-cased.

    Used only to generate candidate blocks (SIG-IDENT-024): a shared trigram makes
    two records *candidates*, never scores them.
    """
    text = f"  {value.strip().lower()}  "
    if len(text) < 3:
        return frozenset()
    return frozenset(text[i : i + 3] for i in range(len(text) - 2))


def block_key(record: Record, rule: BlockingRule) -> tuple[Any, ...] | None:
    """The equijoin block key for ``record`` under ``rule``, or ``None`` to skip.

    A record with a null/empty value in any keyed column produces ``None`` — a
    missing value is never a shared block (that is how nulls silently co-block).
    """
    values: list[Any] = []
    for key in rule.keys:
        value = record.get(key)
        if value is None or value == "":
            return None
        values.append(value)
    return tuple(values)


def _equijoin_pairs(records: Sequence[Record], rule: BlockingRule) -> list[tuple[int, int]]:
    buckets: dict[tuple[Any, ...], list[int]] = defaultdict(list)
    for idx, record in enumerate(records):
        key = block_key(record, rule)
        if key is not None:
            buckets[key].append(idx)
    pairs: list[tuple[int, int]] = []
    for members in buckets.values():
        pairs.extend(combinations(members, 2))
    return pairs


def _trigram_pairs(records: Sequence[Record], rule: BlockingRule) -> list[tuple[int, int]]:
    (column,) = rule.keys
    buckets: dict[str, list[int]] = defaultdict(list)
    for idx, record in enumerate(records):
        value = record.get(column)
        if not value:
            continue
        for gram in trigrams(str(value)):
            buckets[gram].append(idx)
    seen: set[tuple[int, int]] = set()
    for members in buckets.values():
        for pair in combinations(sorted(set(members)), 2):
            seen.add(pair)
    return sorted(seen)


def _pairs(records: Sequence[Record], rule: BlockingRule) -> list[tuple[int, int]]:
    if rule.method == "trigram":
        return _trigram_pairs(records, rule)
    return _equijoin_pairs(records, rule)


def candidate_pairs(records: Sequence[Record], rule: BlockingRule) -> list[tuple[int, int]]:
    """The distinct candidate index-pairs ``rule`` generates over ``records``.

    Deduplicated and order-normalised (``i < j``). This is the set the matcher
    would score; the sizer counts it (:func:`size_blocking_rule`).
    """
    return sorted(set(_pairs(records, rule)))


def size_blocking_rule(records: Sequence[Record], rule: BlockingRule) -> int:
    """Count the candidate comparison pairs ``rule`` yields (SIG-IDENT-023).

    This is the exact comparison count, not a heuristic — it is what the ceiling
    in :meth:`validate_blocking_rule` is checked against.
    """
    return len(candidate_pairs(records, rule))


def validate_blocking_rule(
    records: Sequence[Record],
    rule: BlockingRule,
    *,
    context: BlockingContext | None = None,
) -> int:
    """Size ``rule`` and accept it, or raise :class:`BlockingRuleRejected`.

    Rejects (a) a rule that blocks on a single prohibited low-cardinality key
    (suffix alone / state alone, SIG-IDENT-023) and (b) a rule whose sized
    comparison count exceeds the documented ceiling. Returns the accepted rule's
    comparison count so a caller can record it in the run's quality report.
    """
    ctx = context if context is not None else BlockingContext.from_data()
    if len(rule.keys) == 1 and rule.keys[0] in ctx.prohibited_sole_keys:
        raise BlockingRuleRejected(
            f"blocking rule {rule.rule_id!r} blocks on {rule.keys[0]!r} alone — "
            "suffix-alone / state-alone blocking is prohibited (SIG-IDENT-023)"
        )
    size = size_blocking_rule(records, rule)
    if size > ctx.comparison_ceiling:
        raise BlockingRuleRejected(
            f"blocking rule {rule.rule_id!r} sizes to {size} candidate comparisons, "
            f"above the ceiling of {ctx.comparison_ceiling} (SIG-IDENT-023)"
        )
    return size


def load_rules() -> tuple[BlockingRule, ...]:
    """The committed default blocking rules (versioned data)."""
    return tuple(
        BlockingRule(
            rule_id=str(entry["rule_id"]),
            keys=tuple(entry["keys"]),
            method=str(entry.get("method", "equijoin")),
            description=str(entry.get("description", "")),
        )
        for entry in _rules()["rule"]
    )


# --- Geospatial grid blocking (P30.2b, ADR-105) ------------------------------------

#: Metres per degree used for the coverage check — the conservative lower bounds
#: (a degree of latitude is shortest at the equator; a degree of longitude is
#: 111,320 m x cos(latitude) on the WGS84 equatorial radius).
_M_PER_DEG_LAT_MIN = 110_574.0
_M_PER_DEG_LON_EQUATOR = 111_320.0


@dataclass(frozen=True)
class GeoGridRule:
    """A coordinate-grid blocking rule: same or neighbouring cell, different group.

    A record's block is its ``(floor(lat / cell_lat_deg), floor(lon / cell_lon_deg))``
    cell; its candidates are the records in that cell and the 8 neighbouring cells whose
    ``exclude_same`` value differs (two rows of one source are two devices, never a
    candidate). The rule only PROPOSES pairs (SIG-IDENT-024) and is sized against the
    comparison ceiling before use (SIG-IDENT-023) exactly like the equijoin rules.

    ``covers_radius_m`` is the matcher's outer candidate radius the 3x3 neighbourhood
    must cover up to ``max_abs_latitude``; :meth:`__post_init__` refuses a cell that
    does not (an undersized cell would silently miss true candidates).
    """

    rule_id: str
    lat_key: str = "latitude"
    lon_key: str = "longitude"
    exclude_same: str = "source_id"
    cell_lat_deg: float = 0.0005
    cell_lon_deg: float = 0.0016
    max_abs_latitude: float = 73.0
    covers_radius_m: float = 50.0
    description: str = ""

    def __post_init__(self) -> None:
        if self.cell_lat_deg <= 0 or self.cell_lon_deg <= 0:
            raise BlockingRuleRejected(f"geo rule {self.rule_id!r}: cell sizes must be positive")
        if not 0 < self.max_abs_latitude < 90:
            raise BlockingRuleRejected(
                f"geo rule {self.rule_id!r}: max_abs_latitude must be in (0, 90)"
            )
        lat_m = self.cell_lat_deg * _M_PER_DEG_LAT_MIN
        lon_m = (
            self.cell_lon_deg
            * _M_PER_DEG_LON_EQUATOR
            * math.cos(math.radians(self.max_abs_latitude))
        )
        if min(lat_m, lon_m) < self.covers_radius_m:
            raise BlockingRuleRejected(
                f"geo rule {self.rule_id!r}: a {lat_m:.1f} m x {lon_m:.1f} m cell (at "
                f"{self.max_abs_latitude} deg) does not cover the {self.covers_radius_m} m "
                "candidate radius — the 3x3 neighbourhood would miss true candidates"
            )

    def cell(self, record: Record) -> tuple[int, int] | None:
        """The grid cell of ``record``, or ``None`` when it is not blockable.

        Not blockable: a missing/non-numeric coordinate, an out-of-range one, the
        null-island placeholder (0, 0), or a latitude beyond ``max_abs_latitude`` (where
        the cell would no longer cover the candidate radius). Such a record stays a
        singleton — counted by the caller, never silently mis-blocked.
        """
        try:
            lat = float(record.get(self.lat_key))  # type: ignore[arg-type]
            lon = float(record.get(self.lon_key))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        if not (math.isfinite(lat) and math.isfinite(lon)):
            return None
        if abs(lat) > self.max_abs_latitude or abs(lon) > 180.0:
            return None
        if lat == 0.0 and lon == 0.0:
            return None
        return (math.floor(lat / self.cell_lat_deg), math.floor(lon / self.cell_lon_deg))


def load_geo_rules() -> tuple[GeoGridRule, ...]:
    """The committed geospatial blocking rules (``[[geo_rule]]`` in blocking_rules.toml)."""
    return tuple(
        GeoGridRule(
            rule_id=str(entry["rule_id"]),
            lat_key=str(entry.get("lat_key", "latitude")),
            lon_key=str(entry.get("lon_key", "longitude")),
            exclude_same=str(entry.get("exclude_same", "source_id")),
            cell_lat_deg=float(entry["cell_lat_deg"]),
            cell_lon_deg=float(entry["cell_lon_deg"]),
            max_abs_latitude=float(entry["max_abs_latitude"]),
            covers_radius_m=float(entry["covers_radius_m"]),
            description=str(entry.get("description", "")),
        )
        for entry in _rules().get("geo_rule", [])
    )


def geo_grid_pairs(records: Sequence[Record], rule: GeoGridRule) -> list[tuple[int, int]]:
    """The distinct candidate index-pairs (``i < j``) ``rule`` proposes over ``records``.

    Same or neighbouring grid cell AND a different ``exclude_same`` value (a record with
    no value in that key is never paired — a missing source is not a different source).
    """
    cells: dict[tuple[int, int], list[int]] = defaultdict(list)
    for idx, record in enumerate(records):
        c = rule.cell(record)
        if c is not None and record.get(rule.exclude_same) not in (None, ""):
            cells[c].append(idx)
    pairs: set[tuple[int, int]] = set()
    for (cx, cy), members in cells.items():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                other = cells.get((cx + dx, cy + dy))
                if not other:
                    continue
                for i in members:
                    group_i = records[i].get(rule.exclude_same)
                    for j in other:
                        if j <= i or records[j].get(rule.exclude_same) == group_i:
                            continue
                        pairs.add((i, j))
    return sorted(pairs)


def validate_geo_rule(
    records: Sequence[Record],
    rule: GeoGridRule,
    *,
    context: BlockingContext | None = None,
) -> list[tuple[int, int]]:
    """Size ``rule`` over ``records`` and return its pairs, or raise if above the ceiling.

    The comparison count is exact (the distinct candidate pairs the matcher would
    score), checked against the same documented ceiling as every other rule
    (SIG-IDENT-023) — an oversized geo rule aborts the run rather than quietly running.
    """
    ctx = context if context is not None else BlockingContext.from_data()
    pairs = geo_grid_pairs(records, rule)
    if len(pairs) > ctx.comparison_ceiling:
        raise BlockingRuleRejected(
            f"blocking rule {rule.rule_id!r} sizes to {len(pairs)} candidate comparisons, "
            f"above the ceiling of {ctx.comparison_ceiling} (SIG-IDENT-023)"
        )
    return pairs


def blocked_pairs(
    records: Sequence[Record],
    rules: Iterable[BlockingRule],
    *,
    context: BlockingContext | None = None,
) -> list[tuple[int, int]]:
    """The union of candidate pairs across ``rules``, each sized-and-accepted first.

    Every rule is validated (SIG-IDENT-023) before its pairs are admitted, so an
    oversized or prohibited rule aborts the whole set rather than quietly running.
    """
    ctx = context if context is not None else BlockingContext.from_data()
    union: set[tuple[int, int]] = set()
    for rule in rules:
        validate_blocking_rule(records, rule, context=ctx)
        union.update(candidate_pairs(records, rule))
    return sorted(union)
