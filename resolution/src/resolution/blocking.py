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
