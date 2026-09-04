# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The probabilistic top of the resolution cascade — tiers 4–6 (§14.6, SIG-IDENT-020).

Where :mod:`resolution.cascade` owns the deterministic, auto-writing tiers 0–3, this
module owns the **probabilistic** ones: a Splink 4 matcher on a DuckDB backend
(SIG-IDENT-021) whose scored pairs land on one of three tiers by match weight:

| Tier | Band | Disposition |
|------|------|-------------|
| 4 | weight ≥ ``tier4_review`` | **PROPOSED → review** (probabilistic match above threshold) |
| 5 | ``tier5_weak`` ≤ weight < ``tier4_review`` | **PROPOSED → review** (weak-signal candidate) |
| 6 | weight < ``tier5_weak`` | discard — **no per-pair record** |

The two load-bearing invariants, both pinned by tests:

* **Tiers 4 and 5 NEVER auto-write** (SIG-IDENT-020). Every :class:`ProbabilisticMatch`
  carries ``disposition == "review"`` and an evidence block stamped
  ``claim_status == "PROPOSED"``; a probabilistic tier can only *propose*.
* **Every match records its weight and per-comparison decomposition**
  (SIG-IDENT-025). The model is fully specified (each comparison level carries its
  own m/u in :mod:`splink_model.toml <resolution.data>`), so the Fellegi–Sunter
  match weight and the per-column Bayes factors are deterministic and explainable —
  the confidence explanation surfaced in the review UI (P05.2).

Trigram similarity is confined to candidate search (:mod:`resolution.blocking`); it
never appears in a comparison's decision ``sql_condition`` — enforced by
:func:`assert_no_trigram_decision` (SIG-IDENT-024).

The Splink import is lazy (it pulls DuckDB, pandas, and numpy): importing this module
is cheap, and only :meth:`ProbabilisticMatcher.match` pays the cost.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import cache
from importlib.resources import files
from typing import Any

from .blocking import BlockingContext, BlockingRule, validate_blocking_rule

__all__ = [
    "SPLINK_MODEL_VERSION",
    "ComparisonContribution",
    "ProbabilisticMatch",
    "ProbabilisticMatcher",
    "assert_no_trigram_decision",
    "PROPOSED",
    "REVIEW",
]

# The disposition a probabilistic tier assigns: a PROPOSED claim enqueued for review,
# never an auto-write (SIG-IDENT-020). Kept as named constants so callers and tests
# refer to the contract, not a bare string.
REVIEW = "review"
PROPOSED = "PROPOSED"

# Trigram-similarity function tokens that may never appear in a decision sql_condition
# (SIG-IDENT-024). Jaro/Jaro-Winkler and Levenshtein are edit-distance measures and are
# allowed as decision scores (so the bare word "similarity" is NOT banned — Jaro-Winkler's
# DuckDB function is `jaro_winkler_similarity`); trigram/q-gram *set* similarity, and the
# pg_trgm `%` operator, are not.
_TRIGRAM_DECISION_TOKENS = re.compile(
    r"jaccard|trigram|q_?gram|n_?gram|%",
    re.IGNORECASE,
)


@cache
def _model() -> dict[str, Any]:
    resource = files("resolution").joinpath("data", "splink_model.toml")
    with resource.open("rb") as fh:
        return tomllib.load(fh)


SPLINK_MODEL_VERSION: str = str(_model()["version"])


@dataclass(frozen=True)
class ComparisonContribution:
    """One column's contribution to a pair's match weight (SIG-IDENT-025).

    ``gamma`` is the index of the comparison level that fired (Splink's per-column
    level id; ``-1`` for a null level); ``bayes_factor`` is that level's Bayes
    factor ``m/u`` — the multiplicative evidence the column contributed. ``label`` is
    the human-readable level name from the model, for the confidence explanation.
    """

    column: str
    gamma: int
    bayes_factor: float
    label: str


@dataclass(frozen=True)
class ProbabilisticMatch:
    """A scored candidate pair proposed for review (tier 4 or 5).

    Mirrors :class:`resolution.cascade.MatchResult` but for the probabilistic tiers:
    it carries the ``match_weight`` and the per-comparison decomposition, and its
    ``disposition`` is always ``"review"`` — a probabilistic tier proposes, it never
    auto-writes (SIG-IDENT-020).
    """

    left: str
    right: str
    match_tier: int
    tier_label: str
    match_weight: float
    match_probability: float
    decomposition: tuple[ComparisonContribution, ...]
    match_evidence: dict[str, Any]
    disposition: str = REVIEW

    @property
    def proposed(self) -> bool:
        """True — a probabilistic-tier match is always a PROPOSED claim, never auto-written."""
        return self.disposition == REVIEW


def assert_no_trigram_decision(model: dict[str, Any] | None = None) -> None:
    """Reject a model that uses trigram similarity as a decision score (SIG-IDENT-024).

    Scans every comparison level's ``sql_condition`` for trigram/q-gram set-similarity
    tokens. Edit-distance functions (Jaro-Winkler, Levenshtein) are allowed; trigram
    similarity is not — it may only power candidate search (blocking).
    """
    m = model if model is not None else _model()
    for comparison in m.get("comparison", []):
        for level in comparison.get("level", []):
            condition = str(level.get("sql_condition", ""))
            if _TRIGRAM_DECISION_TOKENS.search(condition):
                raise ValueError(
                    "trigram similarity may not be a decision score (SIG-IDENT-024): "
                    f"comparison {comparison.get('output_column_name')!r} level "
                    f"{level.get('label')!r} uses {condition!r}"
                )


def _build_settings(model: dict[str, Any]) -> dict[str, Any]:
    """Translate the versioned model data into a Splink settings dict."""
    comparisons: list[dict[str, Any]] = []
    for comparison in model["comparison"]:
        levels: list[dict[str, Any]] = []
        for level in comparison["level"]:
            spec: dict[str, Any] = {
                "sql_condition": level["sql_condition"],
                "label_for_charts": level.get("label", level["sql_condition"]),
            }
            if level.get("is_null_level"):
                spec["is_null_level"] = True
            else:
                spec["m_probability"] = float(level["m"])
                spec["u_probability"] = float(level["u"])
            levels.append(spec)
        comparisons.append(
            {"output_column_name": comparison["output_column_name"], "comparison_levels": levels}
        )
    blocking = [
        {"blocking_rule": " AND ".join(f'l."{c}" = r."{c}"' for c in rule["columns"])}
        for rule in model["blocking_rule"]
    ]
    return {
        "link_type": "dedupe_only",
        "unique_id_column_name": "unique_id",
        "probability_two_random_records_match": float(
            model["probability_two_random_records_match"]
        ),
        "retain_intermediate_calculation_columns": True,
        "blocking_rules_to_generate_predictions": blocking,
        "comparisons": comparisons,
    }


def _level_labels(model: dict[str, Any]) -> dict[str, list[str]]:
    """column → the non-null level labels ordered as Splink numbers gamma (0-based).

    Splink assigns ``gamma = 0`` to the last (``ELSE``) level and increasing values to
    the more-specific levels above it; the null level is ``gamma = -1``. Reversing the
    model's most-specific-first level order (minus the null level) yields that mapping.
    """
    out: dict[str, list[str]] = {}
    for comparison in model["comparison"]:
        labels = [
            str(level.get("label", level["sql_condition"]))
            for level in comparison["level"]
            if not level.get("is_null_level")
        ]
        out[comparison["output_column_name"]] = list(reversed(labels))
    return out


@dataclass(frozen=True)
class ProbabilisticMatcher:
    """Splink 4 / DuckDB probabilistic matcher for cascade tiers 4–6 (SIG-IDENT-021).

    Constructed from the versioned model + blocking data (:meth:`from_data`) or with
    an injected model dict (tests). ``match`` scores blocked candidate pairs and
    returns the tier-4/5 :class:`ProbabilisticMatch` proposals; tier-6 pairs (below
    ``tier5_weak``) are dropped with no record.
    """

    model: dict[str, Any]
    blocking_context: BlockingContext = field(default_factory=BlockingContext.from_data)

    @classmethod
    def from_data(cls) -> ProbabilisticMatcher:
        model = _model()
        assert_no_trigram_decision(model)
        return cls(model=model, blocking_context=BlockingContext.from_data())

    def __post_init__(self) -> None:
        # A matcher is never constructed with a trigram decision score (SIG-IDENT-024).
        assert_no_trigram_decision(self.model)

    @property
    def version(self) -> str:
        return str(self.model["version"])

    def _tier_for(self, match_weight: float) -> tuple[int, str] | None:
        thresholds = self.model["thresholds"]
        if match_weight >= float(thresholds["tier4_review"]):
            return 4, "4"
        if match_weight >= float(thresholds["tier5_weak"]):
            return 5, "5"
        return None  # tier 6: below threshold, discarded with no per-pair record

    def _blocking_rules(self) -> list[BlockingRule]:
        return [
            BlockingRule(
                rule_id="+".join(rule["columns"]),
                keys=tuple(rule["columns"]),
                method="equijoin",
            )
            for rule in self.model["blocking_rule"]
        ]

    def size_blocking(self, records: Sequence[dict[str, Any]]) -> dict[str, int]:
        """Size every model blocking rule against ``records`` before matching.

        Raises :class:`resolution.blocking.BlockingRuleRejected` if any rule is
        oversized or prohibited (SIG-IDENT-023). Returns rule_id → comparison count
        for the run's quality report.
        """
        sizes: dict[str, int] = {}
        for rule in self._blocking_rules():
            sizes[rule.rule_id] = validate_blocking_rule(
                records, rule, context=self.blocking_context
            )
        return sizes

    def match(self, records: Sequence[dict[str, Any]]) -> list[ProbabilisticMatch]:
        """Score blocked candidate pairs; return tier-4/5 PROPOSED proposals.

        ``records`` are mappings carrying at least ``unique_id`` and every column the
        model compares/blocks on (``normalized_name``, ``name_first_token``,
        ``state``, ``organization_class``). Blocking is sized first (SIG-IDENT-023);
        tier-6 pairs are discarded with no record (SIG-IDENT-020).
        """
        # Sizing gate runs first — an oversized blocking rule aborts the match.
        blocking_sizes = self.size_blocking(records)

        # Lazy import: Splink pulls DuckDB/pandas/numpy; only matching pays for it.
        import pandas as pd
        from splink import DuckDBAPI, Linker

        settings = _build_settings(self.model)
        labels = _level_labels(self.model)
        compared = [c["output_column_name"] for c in self.model["comparison"]]

        frame = pd.DataFrame(list(records))
        linker = Linker(frame, settings, DuckDBAPI())
        predictions = linker.inference.predict(
            threshold_match_weight=float(self.model["thresholds"]["tier5_weak"])
        )
        scored = predictions.as_pandas_dataframe()

        results: list[ProbabilisticMatch] = []
        for row in scored.to_dict(orient="records"):
            weight = float(row["match_weight"])
            tier = self._tier_for(weight)
            if tier is None:
                continue  # tier 6 — no per-pair record
            match_tier, tier_label = tier
            decomposition = tuple(_contribution(column, row, labels) for column in compared)
            evidence = {
                "rule": "splink_probabilistic",
                "matcher": "splink4-duckdb",
                "model_version": self.version,
                "claim_status": PROPOSED,
                "match_weight": weight,
                "match_probability": float(row["match_probability"]),
                "blocking_sizes": blocking_sizes,
                "decomposition": [
                    {
                        "column": c.column,
                        "gamma": c.gamma,
                        "bayes_factor": c.bayes_factor,
                        "label": c.label,
                    }
                    for c in decomposition
                ],
            }
            results.append(
                ProbabilisticMatch(
                    left=str(row["unique_id_l"]),
                    right=str(row["unique_id_r"]),
                    match_tier=match_tier,
                    tier_label=tier_label,
                    match_weight=weight,
                    match_probability=float(row["match_probability"]),
                    decomposition=decomposition,
                    match_evidence=evidence,
                )
            )
        results.sort(key=lambda m: (-m.match_weight, m.left, m.right))
        return results


def _contribution(
    column: str, row: dict[str, Any], labels: dict[str, list[str]]
) -> ComparisonContribution:
    gamma = int(row[f"gamma_{column}"])
    bf_key = f"bf_{column}"
    bayes_factor = float(row[bf_key]) if bf_key in row and row[bf_key] is not None else 1.0
    column_labels = labels.get(column, [])
    if gamma < 0:
        label = "null"
    elif gamma < len(column_labels):
        label = column_labels[gamma]
    else:
        label = f"level {gamma}"
    return ComparisonContribution(
        column=column, gamma=gamma, bayes_factor=bayes_factor, label=label
    )
