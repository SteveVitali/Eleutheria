# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The design-aware resolution evaluator and shadow confidence gates (P32.10,
ADR-129 — SIG-EVAL-003, SIG-EVAL-004, §55.4).

This module is the *measurement* half of the S3 design: given a preregistered
sampling design (from the P32.9 campaign machinery, :mod:`resolution.human_eval`)
and the labels an authorized release exposed, it computes the estimands the spec
distinguishes and applies the preregistered confidence/multiplicity/stopping
rules — deterministically and stdlib-only so the same input reproduces
byte-identically under any caller.

Boundaries this module keeps (the ticket's "safe eligibility" half):

* **Separate estimands, never pooled.** ``auto_positive_precision`` (fraction of
  proposed automatic edges verified ``same``), ``candidate_recall`` (fraction of
  independently-referenced ``same`` pairs the matcher was offered) and
  ``cluster_quality`` (pairwise + B-cubed over reference clusters) have
  different frames and denominators. ``labelability`` — the share of the frame a
  human can decide at all — is reported alongside, per SIG-EVAL-003's four-way
  distinction. Each estimate carries numerator, denominator, weights, the
  uncertainty method used and the population it speaks for; an estimand whose
  frame cannot support it reports an explicit ``unavailable``/``partial``
  state, never a silent zero or a pooled proxy.

* **Interval method follows the sampling design, never convenience.** The exact
  one-sided Clopper–Pearson (independent-Bernoulli) bound is available ONLY for
  a declared ``independent_bernoulli`` frame — equal selection probability,
  item-level independence, and no shared dependency groups among certifying
  units (a shared group means the draws are correlated, so the iid method is
  refused). Finite frames sampled without replacement use exact hypergeometric
  inversion — whose randomness comes from the sampling design, so correlated
  *content* does not invalidate it (S3 W7/§8). Stratified and grouped designs
  use the conservative simultaneous route: an exact lower bound ``L_c`` per
  declared cell, Bonferroni alpha across the hypothesis's sampled cells, and
  ``Σ_c W_c L_c`` with ``W_c`` the declared population weight; an unmeasured
  nonempty cell contributes exactly ``0``. Enriched/diagnostic strata are never
  certification evidence — they are reported as diagnostics and excluded from
  gate denominators. A heuristic "effective sample size" is never substituted
  for an exact interval, and a zero-error design-based interval can never pass.

* **Strict unresolved-label handling.** Only an adjudicated human ``same`` on
  an intact packet is a success. ``different``, ``insufficient_evidence``,
  ``unresolved`` adjudications and — critically — *missing* final labels are
  all non-successes that stay in the strict denominator. Nothing is dropped to
  improve a gate; a campaign with unlabeled sampled units is ``incomplete``
  and cannot certify even if a favourable bound could be manufactured.

* **Preregistered gate, fixed stopping.** ``eligible_for_auto_write`` requires
  every condition: human reference provenance (agent/LLM/synthetic labels can
  never certify — LLM agreement is supplementary reporting, never ground
  truth), a verified manifest, no train/test contamination, the frozen
  candidate/ruleset digests matching, sealed partitions unsealed by an
  authorized release, every sampled unit accounted for, a fixed single-analysis
  stopping rule (optional stopping or interim peeks can only produce
  ``not_certified``/``incomplete``), a computable design-matched simultaneous
  lower bound, and that bound ≥ the preregistered floor (0.98). A tier with an
  empty deployment frame is ``not_applicable``, never a performance pass.

* **Shadow/inactive until the measured P32.23 decision.** The
  :class:`ConfidencePolicy` ships ``mode='shadow'``: the evaluator computes
  what the preregistered gate *would* decide and reports per-tier
  recommendations, but ``applied`` is empty — nothing is promoted, nothing is
  demoted, and the existing explicitly PROVISIONAL production policy
  (:func:`resolution.camera_sites.decide_auto_write_tiers` et al.) is
  untouched. :func:`activate_policy` refuses every activation path in this
  build — zero-sample, unsealed, or missing the measured post-HUMAN-H5
  decision reference. Historical point-gate metrics are carried in the report
  labelled ``history`` — they are never new eligibility evidence.
"""

from __future__ import annotations

import math
import tomllib
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import cache
from importlib.resources import files
from typing import Any

from .human_eval import ESTIMANDS, PARTITIONS, SEALED_PARTITION, canonical_json, sha256_hex
from .quality_gates import bcubed

__all__ = [
    "EVALUATOR_VERSION",
    "OUTCOMES",
    "TERMINAL_OUTCOMES",
    "PROVENANCES",
    "CERTIFYING_PROVENANCE",
    "DESIGN_KINDS",
    "INDEPENDENT_UNITS",
    "GATE_VERDICTS",
    "ESTIMAND_STATES",
    "EvalUnit",
    "StratumSpec",
    "HypothesisSpec",
    "SamplingDesign",
    "sampling_design_from_dict",
    "ConfidencePolicy",
    "HistoricalMetric",
    "CellEstimate",
    "EstimandReport",
    "TierGate",
    "EvaluationReport",
    "load_confidence_policy",
    "clopper_pearson_lower",
    "hypergeometric_lower_bound",
    "design_problems",
    "cell_estimate",
    "weighted_simultaneous_bound",
    "evaluate_tier_gate",
    "evaluate",
    "activate_policy",
    "report_digest",
    "render_report_md",
]

EVALUATOR_VERSION = "evaluator/1"

#: The outcome vocabulary an evaluation unit may carry. ``missing`` is the
#: honest state for a drawn unit with no final label — it is a persisted,
#: counted outcome, never a dropped row.
OUTCOMES: tuple[str, ...] = (
    "same",
    "different",
    "insufficient_evidence",
    "unresolved",
    "missing",
)
#: Outcomes that close a unit's labeling. ``missing`` is the only non-terminal.
TERMINAL_OUTCOMES: tuple[str, ...] = tuple(o for o in OUTCOMES if o != "missing")

#: Where a reference label came from. Only ``human`` can ever certify
#: (SIG-EVAL-004 — agent/LLM labels are not human ground truth; synthetic
#: labels exist for tests and diagnostics and are excluded from production
#: reference truth by construction).
PROVENANCES: tuple[str, ...] = ("human", "agent", "llm", "synthetic", "unknown")
CERTIFYING_PROVENANCE = "human"

#: The sampling designs the preregistered inference engine understands.
#: ``enriched_diagnostic`` is a real frame kind — targeted/challenge cases —
#: that is *reported* but can never certify (SIG-EVAL-003: enriched samples
#: are not independent representative Bernoulli trials).
DESIGN_KINDS: tuple[str, ...] = (
    "independent_bernoulli",
    "finite_srs",
    "stratified_srs",
    "grouped_psu",
    "enriched_diagnostic",
)

#: The unit independence is claimed over. ``item`` = each sampled pair/record;
#: ``dependency_group`` = the P32.9 dependency group is the PSU.
INDEPENDENT_UNITS: tuple[str, ...] = (
    "item",
    "dependency_group",
    "record",
    "neighborhood",
)

#: The only stopping rule this evaluator accepts for certification: a fixed
#: preregistered sample size and one scheduled analysis (S3 §8 — a sequential
#: alpha-spending/confidence-sequence method needs its own justified protocol).
FIXED_STOPPING_RULE = "fixed"

#: Per-tier gate verdicts. ``certified`` is evidence-side only — under the
#: shadow policy nothing is *applied* regardless of verdict.
GATE_VERDICTS: tuple[str, ...] = (
    "certified",
    "not_certified",
    "incomplete",
    "not_applicable",
    "invalid",
)

#: Estimand report states — an unavailable frame is a first-class answer.
ESTIMAND_STATES: tuple[str, ...] = ("measured", "partial", "unavailable")

_POLICY_RESOURCE = ("data", "eval_confidence.toml")


# --------------------------------------------------------------------------- #
# Inputs — units, strata, hypotheses, design, policy                          #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class EvalUnit:
    """One sampled unit presented for evaluation.

    The caller (CLI / PG reader / test) materializes these from the campaign
    sample rows joined to the *released* label surface — never the sealed
    tables. ``outcome`` is the final resolved outcome: the current
    adjudication when one exists, else the two-independent-label consensus,
    else ``missing``. ``sealed=True`` marks a unit whose partition is
    ``sealed_final`` and whose labels are still sealed — it stays in every
    denominator and blocks certification.
    """

    sample_id: str
    estimand: str
    stratum_id: str
    partition: str
    dependency_group_id: str
    outcome: str
    reference_provenance: str
    tier: int | None = None
    scope: str = "snapshot"
    weight: float | None = None
    selection_probability: float | None = None
    sealed: bool = False
    packet_ok: bool = True
    #: Recall/cluster fields (only for those estimands).
    entity_id: str | None = None
    reference_cluster_id: str | None = None
    predicted_cluster_id: str | None = None
    offered_to_matcher: bool | None = None

    def validate(self) -> None:
        if not self.sample_id:
            raise ValueError("eval unit needs a sample_id")
        if self.estimand not in ESTIMANDS:
            raise ValueError(f"unknown estimand {self.estimand!r} (known: {ESTIMANDS})")
        if self.partition not in PARTITIONS:
            raise ValueError(f"unknown partition {self.partition!r} (known: {PARTITIONS})")
        if self.outcome not in OUTCOMES:
            raise ValueError(f"unknown outcome {self.outcome!r} (known: {OUTCOMES})")
        if self.reference_provenance not in PROVENANCES:
            raise ValueError(
                f"unknown provenance {self.reference_provenance!r} (known: {PROVENANCES})"
            )
        if self.sealed and self.partition != SEALED_PARTITION:
            raise ValueError("only a sealed_final unit may carry sealed=True")

    @property
    def is_success(self) -> bool:
        """The strict certification success test: adjudicated human ``same``
        on an intact packet. Everything else — different, insufficient,
        unresolved, missing, non-human provenance, a failed packet — is a
        non-success that stays in the denominator."""
        return (
            self.outcome == "same"
            and self.reference_provenance == CERTIFYING_PROVENANCE
            and self.packet_ok
            and not self.sealed
        )

    @property
    def is_terminal(self) -> bool:
        """A unit is accounted for once it has any terminal outcome."""
        return self.outcome in TERMINAL_OUTCOMES and not self.sealed


@dataclass(frozen=True)
class StratumSpec:
    """One declared cell of a hypothesis's frame.

    ``population`` is the finite cell size ``N_c`` (required for every finite
    design — the N_h the design must store); ``None`` declares an
    exchangeable/infinite-model cell, legal only under
    ``independent_bernoulli``. ``enriched=True`` marks a diagnostic stratum:
    its units are reported, never certification evidence.
    """

    stratum_id: str
    population: int | None
    enriched: bool = False

    def validate(self) -> None:
        if not self.stratum_id:
            raise ValueError("stratum needs an id")
        if self.population is not None and self.population < 0:
            raise ValueError("stratum population must be >= 0")


@dataclass(frozen=True)
class HypothesisSpec:
    """One preregistered gate hypothesis: "tier ``tier`` auto-positive edges
    in scope ``scope`` are at least ``threshold`` strict precision", tested at
    allocated family alpha ``alpha`` over the declared ``cells``."""

    tier: int
    scope: str
    alpha: float
    threshold: float = 0.98
    cells: tuple[StratumSpec, ...] = ()

    def validate(self) -> None:
        if not 0.0 < self.alpha <= 1.0:
            raise ValueError("hypothesis alpha must be in (0,1]")
        if not 0.0 < self.threshold < 1.0:
            raise ValueError("hypothesis threshold must be in (0,1)")
        for c in self.cells:
            c.validate()


@dataclass(frozen=True)
class SamplingDesign:
    """The preregistered inference design the evaluator refuses to deviate from.

    Frozen before labels are exposed — the design object has no mutable fields;
    a changed frame/ruleset/manifest means a new design (and a new campaign
    under P32.9's machinery). ``independence_basis`` is the *written
    justification* an ``independent_bernoulli`` claim must carry; it is
    required, recorded and reported, never inferred.
    """

    design_id: str
    kind: str
    equal_probability: bool
    independent_unit: str
    independence_basis: str
    family_alpha: float
    hypotheses: tuple[HypothesisSpec, ...]
    stopping_rule: str = FIXED_STOPPING_RULE
    scheduled_analyses: int = 1
    seed: str = ""
    target_population: str = ""
    frame_digest: str = ""
    ruleset_digest: str = ""
    manifest_digest: str = ""
    #: True when every cell declares its finite population (finite designs).
    min_independent_units: int = 2

    def validate(self) -> None:
        if not self.design_id:
            raise ValueError("design needs an id")
        if self.kind not in DESIGN_KINDS:
            raise ValueError(f"unknown design kind {self.kind!r} (known: {DESIGN_KINDS})")
        if self.independent_unit not in INDEPENDENT_UNITS:
            raise ValueError(
                f"unknown independent_unit {self.independent_unit!r} (known: {INDEPENDENT_UNITS})"
            )
        for h in self.hypotheses:
            h.validate()

    def digest(self) -> str:
        """The preregistration digest — pins every field that matters."""
        payload = {
            "design_id": self.design_id,
            "kind": self.kind,
            "equal_probability": self.equal_probability,
            "independent_unit": self.independent_unit,
            "independence_basis": self.independence_basis,
            "family_alpha": self.family_alpha,
            "hypotheses": [
                {
                    "tier": h.tier,
                    "scope": h.scope,
                    "alpha": h.alpha,
                    "threshold": h.threshold,
                    "cells": [
                        {
                            "stratum_id": c.stratum_id,
                            "population": c.population,
                            "enriched": c.enriched,
                        }
                        for c in h.cells
                    ],
                }
                for h in self.hypotheses
            ],
            "stopping_rule": self.stopping_rule,
            "scheduled_analyses": self.scheduled_analyses,
            "seed": self.seed,
            "target_population": self.target_population,
            "frame_digest": self.frame_digest,
            "ruleset_digest": self.ruleset_digest,
            "manifest_digest": self.manifest_digest,
            "min_independent_units": self.min_independent_units,
        }
        return "sha256:" + sha256_hex(canonical_json(payload))


def sampling_design_from_dict(raw: Mapping[str, Any]) -> SamplingDesign:
    """Build a :class:`SamplingDesign` from its preregistration record (JSON).

    The design record is frozen at campaign preregistration; rebuilding it
    here from the stored JSON keeps the evaluator's digest byte-comparable to
    what was registered (``design.digest()`` covers every field).
    """
    hypotheses = tuple(
        HypothesisSpec(
            tier=int(h["tier"]),
            scope=str(h["scope"]),
            alpha=float(h["alpha"]),
            threshold=float(h.get("threshold", 0.98)),
            cells=tuple(
                StratumSpec(
                    stratum_id=str(c["stratum_id"]),
                    population=int(c["population"]) if c.get("population") is not None else None,
                    enriched=bool(c.get("enriched", False)),
                )
                for c in h.get("cells", ())
            ),
        )
        for h in raw.get("hypotheses", ())
    )
    design = SamplingDesign(
        design_id=str(raw["design_id"]),
        kind=str(raw["kind"]),
        equal_probability=bool(raw["equal_probability"]),
        independent_unit=str(raw["independent_unit"]),
        independence_basis=str(raw.get("independence_basis", "")),
        family_alpha=float(raw["family_alpha"]),
        hypotheses=hypotheses,
        stopping_rule=str(raw.get("stopping_rule", FIXED_STOPPING_RULE)),
        scheduled_analyses=int(raw.get("scheduled_analyses", 1)),
        seed=str(raw.get("seed", "")),
        target_population=str(raw.get("target_population", "")),
        frame_digest=str(raw.get("frame_digest", "")),
        ruleset_digest=str(raw.get("ruleset_digest", "")),
        manifest_digest=str(raw.get("manifest_digest", "")),
        min_independent_units=int(raw.get("min_independent_units", 2)),
    )
    design.validate()
    return design


@dataclass(frozen=True)
class ConfidencePolicy:
    """The versioned confidence policy (``data/eval_confidence.toml``).

    Ships ``mode='shadow'``: the evaluator reports what the gate would decide
    and applies nothing. Only the measured post-HUMAN-H5 decision recorded at
    P32.23 (a new ADR + an authorized operational release) may arm it — this
    build never activates.
    """

    version: str
    mode: str  # "shadow" | "active"
    family_alpha: float
    threshold: float
    alpha_allocation: str  # "bonferroni"
    stopping_rule: str
    activation_authority: str

    @property
    def shadow(self) -> bool:
        return self.mode != "active"


@cache
def load_confidence_policy() -> ConfidencePolicy:
    """The committed confidence policy, read as versioned data."""
    resource = files("resolution").joinpath(*_POLICY_RESOURCE)
    with resource.open("rb") as fh:
        raw = tomllib.load(fh)
    return ConfidencePolicy(
        version=str(raw["version"]),
        mode=str(raw.get("mode", "shadow")),
        family_alpha=float(raw["family_alpha"]),
        threshold=float(raw["threshold"]),
        alpha_allocation=str(raw.get("alpha_allocation", "bonferroni")),
        stopping_rule=str(raw.get("stopping_rule", FIXED_STOPPING_RULE)),
        activation_authority=str(raw.get("activation_authority", "P32.23")),
    )


@dataclass(frozen=True)
class HistoricalMetric:
    """A legacy point-gate number carried as HISTORY — never eligibility
    evidence (the 70/70, 69/70-era measurements stay visible, labelled)."""

    label: str
    tier: int | None
    value: float | None
    detail: str = ""
    as_of: str = ""
    kind: str = "historical_point_gate"


# --------------------------------------------------------------------------- #
# Exact one-sided bounds (stdlib only — no scipy)                              #
# --------------------------------------------------------------------------- #
def _log_choose(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def _binom_tail(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p), computed in log space."""
    if p <= 0.0:
        return 0.0 if k > 0 else 1.0
    if p >= 1.0:
        return 1.0 if k <= n else 0.0
    terms = [
        math.exp(_log_choose(n, j) + j * math.log(p) + (n - j) * math.log1p(-p))
        for j in range(k, n + 1)
    ]
    return min(1.0, sum(terms))


def clopper_pearson_lower(k: int, n: int, alpha: float) -> float:
    """The exact one-sided Clopper–Pearson lower confidence bound.

    The smallest p such that observing ``k`` or more successes in ``n``
    independent Bernoulli(p) trials remains plausible at level ``alpha`` —
    i.e. ``L`` solves ``P(X >= k; n, L) = alpha``. Valid ONLY where the
    design justifies independent equal-probability trials; the caller
    (:func:`cell_estimate`) is responsible for refusing it elsewhere.
    """
    if n <= 0:
        raise ValueError("Clopper–Pearson needs n >= 1")
    if not 0 < k <= n:
        return 0.0
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0,1)")
    if k == n:
        return alpha ** (1.0 / n)
    # P(X >= k) is nondecreasing in p: L is the unique crossing of alpha, i.e.
    # the supremum of {p : tail(p) <= alpha}.
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if _binom_tail(k, n, mid) > alpha:
            hi = mid
        else:
            lo = mid
        if hi - lo < 1e-15:
            break
    return lo


def _hyper_tail(x: int, n: int, N: int, K: int) -> float:
    """P(X >= x) drawing n without replacement from N holding K successes."""
    lo = max(x, n - (N - K))
    hi = min(n, K)
    if lo > hi:
        return 0.0
    denom = _log_choose(N, n)
    return min(
        1.0,
        sum(
            math.exp(_log_choose(K, j) + _log_choose(N - K, n - j) - denom)
            for j in range(lo, hi + 1)
        ),
    )


def hypergeometric_lower_bound(x: int, n: int, N: int, alpha: float) -> float:
    """The exact lower confidence bound on the finite-population rate K/N.

    ``K_L`` = the smallest ``K`` such that ``P(X >= x; N, K, n) > alpha``;
    returned as a proportion ``K_L / N``. Sampling without replacement means
    the randomness lives in the *design*, so no Bernoulli-independence
    assumption is needed — the correct inference for finite frames holding
    correlated content (S3 §8/W7). A full census (``n == N``) returns ``x/N``
    exactly: the population count is then known, subject to reference error.
    """
    if N <= 0:
        raise ValueError("hypergeometric bound needs a nonempty population N")
    if not 0 <= n <= N:
        raise ValueError("sample size n must satisfy 0 <= n <= N")
    if not 0 <= x <= n:
        raise ValueError("observed successes x must satisfy 0 <= x <= n")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0,1)")
    if x == 0:
        return 0.0
    if n == N:
        return x / N
    # P_K(X >= x) is nondecreasing in K → smallest K with tail > alpha.
    lo_k, hi_k = x, N - (n - x)
    best = hi_k
    while lo_k <= hi_k:
        mid = (lo_k + hi_k) // 2
        if _hyper_tail(x, n, N, mid) > alpha:
            best = mid
            hi_k = mid - 1
        else:
            lo_k = mid + 1
    return best / N


# --------------------------------------------------------------------------- #
# Design validation — the method can never outrun the frame                    #
# --------------------------------------------------------------------------- #
def design_problems(design: SamplingDesign, units: Sequence[EvalUnit]) -> list[str]:
    """Every reason this design cannot legitimately drive inference.

    Returns structured problem codes; an empty list means the design is
    internally consistent AND consistent with the units presented. This is
    where "correlated/enriched samples cannot select an unjustified iid
    method" is enforced.
    """
    problems: list[str] = []
    design.validate()

    if design.stopping_rule != FIXED_STOPPING_RULE:
        problems.append("optional_stopping_rule")
    if design.scheduled_analyses != 1:
        problems.append("multi_look_schedule")
    total_alpha = sum(h.alpha for h in design.hypotheses)
    if total_alpha > design.family_alpha + 1e-9:
        problems.append("multiplicity_alpha_exceeded")
    if not design.hypotheses:
        problems.append("no_hypotheses")

    certifying = [u for u in units if not _is_diagnostic(design, u)]
    if not certifying:
        problems.append("zero_sample")

    if design.kind == "enriched_diagnostic":
        problems.append("diagnostic_only_design")

    if design.kind == "independent_bernoulli":
        if not design.equal_probability:
            problems.append("iid_requires_equal_probability")
        if design.independent_unit != "item":
            problems.append("iid_requires_item_independence")
        if not design.independence_basis.strip():
            problems.append("iid_requires_recorded_basis")
        # Correlated content kills the iid claim outright: two certifying
        # units sharing a dependency group are not independent trials.
        seen_groups: set[str] = set()
        for u in certifying:
            if u.dependency_group_id in seen_groups:
                problems.append("correlated_units_in_iid_frame")
                break
            seen_groups.add(u.dependency_group_id)
        for h in design.hypotheses:
            if any(c.enriched for c in h.cells):
                problems.append("enriched_stratum_in_iid_design")
                break

    if design.kind == "grouped_psu":
        if design.independent_unit != "dependency_group":
            problems.append("grouped_design_requires_group_psu")
        for h in design.hypotheses:
            for c in h.cells:
                if c.population is None:
                    problems.append("grouped_cell_missing_population")
                    break
    if design.kind in ("finite_srs", "stratified_srs"):
        for h in design.hypotheses:
            for c in h.cells:
                if c.population is None:
                    problems.append("finite_cell_missing_population")
                    break
    return sorted(set(problems))


def _is_diagnostic(design: SamplingDesign, unit: EvalUnit) -> bool:
    """A unit is diagnostic-only when its stratum is enriched or the whole
    design is the enriched/diagnostic frame."""
    if design.kind == "enriched_diagnostic":
        return True
    for h in design.hypotheses:
        for c in h.cells:
            if c.stratum_id == unit.stratum_id and c.enriched:
                return True
    return False


def _certification_method(design: SamplingDesign, cell: StratumSpec) -> str | None:
    """The interval method a cell may legitimately use, or ``None``.

    ``clopper_pearson_iid`` exists only under a validated iid frame;
    ``hypergeometric_srs`` wherever a finite population is declared — the
    design-matched method, never a convenience pick.
    """
    if design.kind == "independent_bernoulli":
        return "clopper_pearson_iid"
    if design.kind in ("finite_srs", "stratified_srs", "grouped_psu"):
        return "hypergeometric_srs" if cell.population is not None else None
    return None


# --------------------------------------------------------------------------- #
# Estimates — per-cell bounds and the simultaneous weighted bound              #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CellEstimate:
    """One declared cell's measured outcome — strict counts never drop a row."""

    stratum_id: str
    population: int | None
    drawn: int
    successes: int
    different: int
    insufficient: int
    unresolved: int
    missing: int
    sealed: int
    non_human: int
    point_strict: float | None
    lower_bound: float | None
    method: str | None
    alpha: float | None
    weight: float | None
    enriched: bool = False

    @property
    def accounted(self) -> bool:
        """Every drawn unit reached a terminal, visible outcome."""
        return self.missing == 0 and self.sealed == 0


def cell_estimate(
    units: Sequence[EvalUnit],
    cell: StratumSpec,
    design: SamplingDesign,
    *,
    alpha: float,
    total_population: int,
) -> CellEstimate:
    """Measure one declared cell: strict counts + the design-matched bound.

    ``n`` is every unit the campaign presented for the cell — missing labels,
    sealed units and non-human provenance all stay in the denominator.
    """
    drawn = len(units)
    successes = sum(1 for u in units if u.is_success)
    counts = {
        "different": sum(1 for u in units if u.outcome == "different"),
        "insufficient": sum(1 for u in units if u.outcome == "insufficient_evidence"),
        "unresolved": sum(1 for u in units if u.outcome == "unresolved"),
        "missing": sum(1 for u in units if u.outcome == "missing"),
        "sealed": sum(1 for u in units if u.sealed),
        "non_human": sum(1 for u in units if u.reference_provenance != CERTIFYING_PROVENANCE),
    }
    point = (successes / drawn) if drawn else None
    method = _certification_method(design, cell)
    bound: float | None = None
    if drawn and method == "clopper_pearson_iid":
        bound = clopper_pearson_lower(successes, drawn, alpha)
    elif drawn and method == "hypergeometric_srs":
        bound = hypergeometric_lower_bound(successes, drawn, int(cell.population or 0), alpha)
    elif drawn:
        # A cell with drawn units but no legitimate method is measured-but-
        # unbounded: point estimate reported, bound stays None.
        bound = None
    weight = None
    if cell.population is not None and total_population > 0:
        weight = cell.population / total_population
    return CellEstimate(
        stratum_id=cell.stratum_id,
        population=cell.population,
        drawn=drawn,
        successes=successes,
        different=counts["different"],
        insufficient=counts["insufficient"],
        unresolved=counts["unresolved"],
        missing=counts["missing"],
        sealed=counts["sealed"],
        non_human=counts["non_human"],
        point_strict=point,
        lower_bound=bound,
        method=method,
        alpha=alpha,
        weight=weight,
        enriched=cell.enriched,
    )


def weighted_simultaneous_bound(cells: Sequence[CellEstimate]) -> float | None:
    """The conservative simultaneous lower bound ``Σ_c W_c L_c``.

    Bonferroni across the hypothesis's sampled cells is already inside each
    ``L_c``; an unmeasured or unboundable cell contributes ``L_c = 0`` (its
    true precision could be zero). ``None`` when no cell carries a declared
    weight — the bound is then undefined, never silently pooled.
    """
    if not cells or all(c.weight is None for c in cells):
        return None
    total = 0.0
    for c in cells:
        w = c.weight if c.weight is not None else 0.0
        bound = c.lower_bound if c.lower_bound is not None else 0.0
        total += w * bound
    return total


# --------------------------------------------------------------------------- #
# Tier gates — the preregistered eligibility decision (evidence side)          #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class TierGate:
    """The per-hypothesis gate record: evidence verdict + shadow recommendation."""

    tier: int
    scope: str
    alpha: float
    threshold: float
    drawn: int
    successes: int
    different: int
    insufficient: int
    unresolved: int
    missing: int
    sealed: int
    non_human: int
    point_strict: float | None
    lower_bound: float | None
    method: str | None
    complete: bool
    verdict: str
    reasons: tuple[str, ...]
    cells: tuple[CellEstimate, ...]
    recommended_disposition: str
    applied: bool = False

    def to_row(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "scope": self.scope,
            "alpha": self.alpha,
            "threshold": self.threshold,
            "drawn": self.drawn,
            "successes": self.successes,
            "different": self.different,
            "insufficient": self.insufficient,
            "unresolved": self.unresolved,
            "missing": self.missing,
            "sealed": self.sealed,
            "non_human": self.non_human,
            "point_strict": self.point_strict,
            "lower_bound": self.lower_bound,
            "method": self.method,
            "complete": self.complete,
            "verdict": self.verdict,
            "reasons": list(self.reasons),
            "recommended_disposition": self.recommended_disposition,
            "applied": self.applied,
            "cells": [
                {
                    "stratum_id": c.stratum_id,
                    "population": c.population,
                    "drawn": c.drawn,
                    "successes": c.successes,
                    "point_strict": c.point_strict,
                    "lower_bound": c.lower_bound,
                    "method": c.method,
                    "alpha": c.alpha,
                    "weight": c.weight,
                    "enriched": c.enriched,
                }
                for c in self.cells
            ],
        }


def evaluate_tier_gate(
    hypothesis: HypothesisSpec,
    units: Sequence[EvalUnit],
    design: SamplingDesign,
    *,
    problems: Sequence[str],
    manifest_verified: bool,
    contamination: bool,
    frozen_digests_match: bool,
    analysis_no: int,
    interim_looks: int,
    early_stop: str | None,
    reused_test_set: bool,
) -> TierGate:
    """Apply the preregistered gate to one (tier, scope) hypothesis.

    The verdict is pure evidence: ``certified`` requires the strict
    simultaneous bound ≥ threshold AND every integrity precondition. Shadow
    application is decided by the caller — ``applied`` stays False here.
    """
    reasons: list[str] = list(problems)

    hyp_units = [u for u in units if u.tier == hypothesis.tier and u.scope == hypothesis.scope]
    cert_units = [u for u in hyp_units if not _is_diagnostic(design, u)]
    diag_units = [u for u in hyp_units if _is_diagnostic(design, u)]

    # The certifying population is the NON-enriched frame: enriched/challenge
    # strata are a different population, reported as diagnostics — their mass
    # never enters the hypothesis's weight denominator.
    cells = [c for c in hypothesis.cells if not c.enriched]
    declared_population = sum(c.population or 0 for c in cells)
    sampled_cell_ids = {u.stratum_id for u in cert_units}
    sampled_cells = [c for c in cells if c.stratum_id in sampled_cell_ids]
    # Bonferroni within the hypothesis: its alpha is divided across the cells
    # it actually sampled (unmeasured cells contribute an exact 0 — no alpha
    # is spent on them).
    n_sampled = max(1, len(sampled_cells))
    cell_alpha = hypothesis.alpha / n_sampled

    by_stratum: dict[str, list[EvalUnit]] = defaultdict(list)
    for u in cert_units:
        by_stratum[u.stratum_id].append(u)
    estimates = [
        cell_estimate(
            by_stratum.get(c.stratum_id, []),
            c,
            design,
            alpha=cell_alpha,
            total_population=declared_population,
        )
        for c in cells
    ]

    drawn = len(cert_units)
    successes = sum(e.successes for e in estimates)
    counts = {
        "different": sum(e.different for e in estimates),
        "insufficient": sum(e.insufficient for e in estimates),
        "unresolved": sum(e.unresolved for e in estimates),
        "missing": sum(e.missing for e in estimates),
        "sealed": sum(e.sealed for e in estimates),
        "non_human": sum(e.non_human for e in estimates),
    }
    point = (successes / drawn) if drawn else None
    if design.kind == "independent_bernoulli":
        # An exchangeable Bernoulli frame has no finite cells to weight —
        # pooling the iid draws IS the design's own estimate; the Bonferroni
        # within-hypothesis allocation is the hypothesis alpha itself.
        bound = clopper_pearson_lower(successes, drawn, hypothesis.alpha) if drawn else None
    else:
        bound = weighted_simultaneous_bound(estimates)
    complete = drawn > 0 and all(e.accounted for e in estimates)

    # ---- structured reasons ------------------------------------------------
    if drawn == 0:
        reasons.append("zero_sample")
    # A unit is sealed exactly when its sealed_final labels were absent from
    # the released surface — that materialized flag is the gate input, not a
    # caller claim about release scopes.
    if counts["sealed"]:
        reasons.append("sealed_units")
    if counts["missing"]:
        reasons.append("missing_labels")
    if counts["non_human"]:
        reasons.append("non_human_reference")
    if diag_units:
        reasons.append("diagnostic_units_excluded")
    if not complete:
        reasons.append("incomplete_labeling")
    if not manifest_verified:
        reasons.append("manifest_unverified")
    if contamination:
        reasons.append("contamination")
    if not frozen_digests_match:
        reasons.append("candidate_digest_mismatch")
    if reused_test_set:
        reasons.append("reused_test_set")
    if analysis_no > 1 or interim_looks > 0:
        reasons.append("optional_stopping")
    if early_stop is not None:
        reasons.append("early_stop_no_pass")
    methods = {e.method for e in estimates if e.drawn}
    method = next(iter(methods)) if len(methods) == 1 else ("mixed" if methods else None)
    if drawn and bound is None:
        reasons.append("bound_not_computable")
    if bound is not None and bound < hypothesis.threshold:
        reasons.append("bound_below_floor")

    # ---- verdict -------------------------------------------------------------
    declared_empty = declared_population == 0 and drawn == 0
    if problems:
        verdict = "invalid"
    elif declared_empty:
        verdict = "not_applicable"
    elif not complete or early_stop is not None:
        verdict = "incomplete"
    elif (
        bound is not None
        and bound >= hypothesis.threshold
        and not any(
            r
            for r in reasons
            if r
            in (
                "non_human_reference",
                "manifest_unverified",
                "contamination",
                "candidate_digest_mismatch",
                "reused_test_set",
                "optional_stopping",
                "bound_not_computable",
                "sealed_units",
            )
        )
    ):
        verdict = "certified"
    else:
        verdict = "not_certified"

    if verdict == "certified":
        recommendation = "certify"
    elif verdict == "not_applicable":
        recommendation = "retain_provisional"
    else:
        # Fail-safe: insufficient evidence demotes or retains review-only
        # status (SIG-EVAL-004). Adopting the demotion is a *separate*
        # operational decision — this report only recommends.
        recommendation = "review_only_fail_safe"

    return TierGate(
        tier=hypothesis.tier,
        scope=hypothesis.scope,
        alpha=hypothesis.alpha,
        threshold=hypothesis.threshold,
        drawn=drawn,
        successes=successes,
        different=counts["different"],
        insufficient=counts["insufficient"],
        unresolved=counts["unresolved"],
        missing=counts["missing"],
        sealed=counts["sealed"],
        non_human=counts["non_human"],
        point_strict=point,
        lower_bound=bound,
        method=method,
        complete=complete,
        verdict=verdict,
        reasons=tuple(sorted(set(reasons))),
        cells=tuple(estimates),
        recommended_disposition=recommendation,
        applied=False,
    )


# --------------------------------------------------------------------------- #
# The four estimands                                                           #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class EstimandReport:
    """One estimand's measured state: rows + the named frame/population."""

    estimand: str
    state: str  # ESTIMAND_STATES
    rows: tuple[Mapping[str, Any], ...]
    numerator: int | None
    denominator: int | None
    population_note: str
    method: str | None
    unavailable_reason: str | None = None
    extras: Mapping[str, Any] = field(default_factory=dict)


def _auto_positive_rows(
    units: Sequence[EvalUnit],
) -> tuple[Mapping[str, Any], ...]:
    """The auto-positive precision accounting rows per (tier, scope) cell.

    Every drawn unit stays visible: successes beside the non-success
    categories, never a pooled count.
    """
    groups: dict[tuple[int | None, str, str], list[EvalUnit]] = defaultdict(list)
    for u in units:
        groups[(u.tier, u.scope, u.stratum_id)].append(u)
    rows: list[Mapping[str, Any]] = []
    for (tier, scope, stratum), us in sorted(groups.items(), key=lambda kv: str(kv[0])):
        rows.append(
            {
                "tier": tier,
                "scope": scope,
                "stratum_id": stratum,
                "drawn": len(us),
                "same": sum(1 for u in us if u.is_success),
                "different": sum(1 for u in us if u.outcome == "different"),
                "insufficient_evidence": sum(1 for u in us if u.outcome == "insufficient_evidence"),
                "unresolved": sum(1 for u in us if u.outcome == "unresolved"),
                "missing": sum(1 for u in us if u.outcome == "missing"),
                "sealed": sum(1 for u in us if u.sealed),
            }
        )
    return tuple(rows)


def _candidate_recall(
    units: Sequence[EvalUnit],
) -> EstimandReport:
    """Candidate-generation recall over the reference frame.

    The denominator is the INDEPENDENTLY referenced same-pair population —
    pairs found by searching the authorized corpus, not by the matcher under
    test. A sample drawn only from the matcher's own candidates can never
    observe blocking false negatives, so it reports ``unavailable`` rather
    than a manufactured recall.
    """
    frame = [u for u in units if u.estimand == "candidate_recall"]
    if not frame:
        return EstimandReport(
            estimand="candidate_recall",
            state="unavailable",
            rows=(),
            numerator=None,
            denominator=None,
            population_note="no recall frame was drawn",
            method=None,
            unavailable_reason="no_recall_frame",
        )
    if all(u.offered_to_matcher is None for u in frame):
        return EstimandReport(
            estimand="candidate_recall",
            state="unavailable",
            rows=(),
            numerator=None,
            denominator=None,
            population_note=(
                "the frame is candidate-only — a sample of the matcher's own "
                "output cannot observe blocking false negatives (SIG-EVAL-003)"
            ),
            method=None,
            unavailable_reason="candidate_only_frame",
        )
    decided_same = [u for u in frame if u.outcome == "same"]
    undecided = [u for u in frame if u.outcome != "same"]
    offered = sum(1 for u in decided_same if u.offered_to_matcher)
    n_decided = len(decided_same)
    point = (offered / n_decided) if n_decided else None
    worst = offered / (n_decided + len(undecided)) if (n_decided + len(undecided)) else None
    rows = (
        {
            "offered_same": offered,
            "decided_reference_same": n_decided,
            "undecided_reference": len(undecided),
            "recall_point": point,
            "recall_lower_strict": worst,
        },
    )
    state = "measured" if not undecided else "partial"
    return EstimandReport(
        estimand="candidate_recall",
        state=state,
        rows=rows,
        numerator=offered,
        denominator=n_decided,
        population_note=(
            "fraction of independently referenced same pairs the candidate "
            "generator offered; undecided reference units are counted, never "
            "dropped"
        ),
        method="design_weighted" if any(u.weight for u in frame) else "unweighted",
        unavailable_reason=None if state == "measured" else "reference_undecided",
    )


def _cluster_quality(
    units: Sequence[EvalUnit],
) -> EstimandReport:
    """Whole-cluster quality over independently resolved reference clusters.

    Pairwise + B-cubed over entities whose reference membership is known.
    Unlabeled entities are counted as unresolved coverage — assigning them to
    truth singletons would invent recall (S3 §9). A pair-only sample cannot
    produce whole-cluster quality.
    """
    frame = [u for u in units if u.estimand == "cluster_quality"]
    if not frame:
        return EstimandReport(
            estimand="cluster_quality",
            state="unavailable",
            rows=(),
            numerator=None,
            denominator=None,
            population_note="no cluster-quality frame was drawn",
            method=None,
            unavailable_reason="no_cluster_frame",
        )
    labeled = [
        u
        for u in frame
        if u.entity_id is not None and u.reference_cluster_id is not None and u.packet_ok
    ]
    unresolved = len(frame) - len(labeled)
    if not labeled:
        return EstimandReport(
            estimand="cluster_quality",
            state="unavailable",
            rows=({"declared_entities": len(frame), "unresolved_entities": unresolved},),
            numerator=None,
            denominator=len(frame),
            population_note=(
                "no entity in the frame carries a reference-cluster membership — "
                "a pair sample alone cannot establish whole-cluster quality "
                "(SIG-EVAL-003)"
            ),
            method=None,
            unavailable_reason="no_reference_clusters",
        )
    pred = {str(u.entity_id): str(u.predicted_cluster_id) for u in labeled}
    gold = {str(u.entity_id): str(u.reference_cluster_id) for u in labeled}
    # Pairwise over within-cluster pairs + B-cubed per element. Scored over the
    # whole cluster pair space (not a labeled-pair universe): every predicted
    # co-membership counts, so a bad merge is visibly penalised.
    pred_pairs = _cluster_pairs(pred)
    gold_pairs = _cluster_pairs(gold)
    tp = len(pred_pairs & gold_pairs)
    pair_precision = tp / len(pred_pairs) if pred_pairs else None
    pair_recall = tp / len(gold_pairs) if gold_pairs else None
    b3 = bcubed(pred, gold)
    rows = (
        {
            "entities": len(labeled),
            "unresolved_entities": unresolved,
            "pairwise_precision": pair_precision,
            "pairwise_recall": pair_recall,
            "predicted_pairs": len(pred_pairs),
            "reference_pairs": len(gold_pairs),
            "bcubed_precision": b3.precision,
            "bcubed_recall": b3.recall,
            "coverage": len(labeled) / len(frame) if frame else None,
        },
    )
    return EstimandReport(
        estimand="cluster_quality",
        state="measured" if unresolved == 0 else "partial",
        rows=rows,
        numerator=len(labeled),
        denominator=len(frame),
        population_note=(
            "pairwise + B-cubed over entities with independent reference-"
            "cluster membership; unresolved entities stay in the coverage "
            "denominator, never become invented truth singletons"
        ),
        method="bcubed+pairwise",
        unavailable_reason=None if unresolved == 0 else "partial_reference_coverage",
    )


def _cluster_pairs(cluster_of: Mapping[str, str]) -> set[tuple[str, str]]:
    members: dict[str, list[str]] = defaultdict(list)
    for e, c in cluster_of.items():
        members[c].append(e)
    pairs: set[tuple[str, str]] = set()
    for es in members.values():
        es = sorted(es)
        for i in range(len(es)):
            for j in range(i + 1, len(es)):
                pairs.add((es[i], es[j]))
    return pairs


def _labelability(units: Sequence[EvalUnit]) -> EstimandReport:
    """How much of the frame a human could decide at all (SIG-EVAL-003).

    decisive = same/different (a real answer); insufficient/unresolved/
    missing/sealed are non-decisive and stay visible — labelability is a
    report, never a gate shortcut.
    """
    groups: dict[str, list[EvalUnit]] = defaultdict(list)
    for u in units:
        groups[u.stratum_id].append(u)
    rows: list[Mapping[str, Any]] = []
    decisive = total = 0
    for stratum, us in sorted(groups.items()):
        d = sum(1 for u in us if u.outcome in ("same", "different"))
        decisive += d
        total += len(us)
        rows.append(
            {
                "stratum_id": stratum,
                "units": len(us),
                "decisive": d,
                "insufficient_evidence": sum(1 for u in us if u.outcome == "insufficient_evidence"),
                "unresolved": sum(1 for u in us if u.outcome == "unresolved"),
                "missing": sum(1 for u in us if u.outcome == "missing"),
                "sealed": sum(1 for u in us if u.sealed),
                "decisive_fraction": (d / len(us)) if us else None,
            }
        )
    return EstimandReport(
        estimand="labelability",
        state="measured" if total else "unavailable",
        rows=tuple(rows),
        numerator=decisive,
        denominator=total,
        population_note="fraction of drawn units carrying a decisive same/different label",
        method="stratified_counts",
        unavailable_reason=None if total else "no_units",
    )


# --------------------------------------------------------------------------- #
# The whole evaluation                                                         #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class EvaluationReport:
    """The deterministic evaluation output — digest-stable for identical input."""

    evaluator_version: str
    design_id: str
    design_digest: str
    manifest_verified: bool
    estimands: Mapping[str, EstimandReport]
    gates: tuple[TierGate, ...]
    design_problems: tuple[str, ...]
    policy_mode: str
    policy_version: str
    applied: tuple[str, ...]
    recommendations: Mapping[str, str]
    historical: tuple[HistoricalMetric, ...]
    llm_agreement: float | None
    release_scopes: tuple[str, ...] | None
    analysis_no: int
    notes: tuple[str, ...]

    def payload(self) -> dict[str, Any]:
        return {
            "evaluator_version": self.evaluator_version,
            "design_id": self.design_id,
            "design_digest": self.design_digest,
            "manifest_verified": self.manifest_verified,
            "estimands": {
                k: {
                    "state": r.state,
                    "rows": [dict(row) for row in r.rows],
                    "numerator": r.numerator,
                    "denominator": r.denominator,
                    "population_note": r.population_note,
                    "method": r.method,
                    "unavailable_reason": r.unavailable_reason,
                    "extras": dict(r.extras),
                }
                for k, r in sorted(self.estimands.items())
            },
            "gates": [g.to_row() for g in self.gates],
            "design_problems": list(self.design_problems),
            "policy_mode": self.policy_mode,
            "policy_version": self.policy_version,
            "applied": list(self.applied),
            "recommendations": dict(self.recommendations),
            "historical": [
                {
                    "label": h.label,
                    "tier": h.tier,
                    "value": h.value,
                    "detail": h.detail,
                    "as_of": h.as_of,
                    "kind": h.kind,
                }
                for h in self.historical
            ],
            "llm_agreement": self.llm_agreement,
            "release_scopes": list(self.release_scopes) if self.release_scopes else None,
            "analysis_no": self.analysis_no,
            "notes": list(self.notes),
        }


def report_digest(report: EvaluationReport) -> str:
    """Tamper-evident digest over the whole report payload."""
    return "sha256:" + sha256_hex(canonical_json(report.payload()))


def evaluate(
    *,
    units: Sequence[EvalUnit],
    design: SamplingDesign,
    policy: ConfidencePolicy | None = None,
    manifest_verified: bool = True,
    contamination: bool = False,
    frozen_digests_match: bool = True,
    release_scopes: Sequence[str] | None = ("final",),
    analysis_no: int = 1,
    interim_looks: int = 0,
    early_stop: str | None = None,
    reused_test_set: bool = False,
    llm_agreement: float | None = None,
    historical: Sequence[HistoricalMetric] = (),
    notes: Sequence[str] = (),
) -> EvaluationReport:
    """Run the design-aware evaluation and produce the shadow report.

    Every input the gate consumes is explicit in this signature — the
    evaluator reads only unsealed/authorized units (the caller must never
    materialize a sealed label), validates the preregistered design against
    them, computes the estimands and the per-hypothesis gate, and reports.
    Under the shadow policy ``applied`` is always empty.
    """
    policy = policy if policy is not None else load_confidence_policy()
    for u in units:
        u.validate()

    problems = design_problems(design, units)

    gates = tuple(
        evaluate_tier_gate(
            h,
            units,
            design,
            problems=problems,
            manifest_verified=manifest_verified,
            contamination=contamination,
            frozen_digests_match=frozen_digests_match,
            analysis_no=analysis_no,
            interim_looks=interim_looks,
            early_stop=early_stop,
            reused_test_set=reused_test_set,
        )
        for h in sorted(design.hypotheses, key=lambda x: (x.tier, x.scope))
    )

    auto_units = [u for u in units if u.estimand == "auto_positive_precision"]
    auto_report = EstimandReport(
        estimand="auto_positive_precision",
        state="measured" if auto_units else "unavailable",
        rows=_auto_positive_rows(auto_units),
        numerator=sum(1 for u in auto_units if u.is_success),
        denominator=len(auto_units) if auto_units else None,
        population_note=(
            "strict share of sampled auto-positive edges verified same; "
            "missing/sealed/insufficient stay in the denominator"
        ),
        method=next(
            (g.method for g in gates if g.method),
            None,
        ),
        unavailable_reason=None if auto_units else "no_auto_positive_frame",
    )

    estimands: dict[str, EstimandReport] = {
        "auto_positive_precision": auto_report,
        "candidate_recall": _candidate_recall(units),
        "cluster_quality": _cluster_quality(units),
        "labelability": _labelability(units),
    }

    recommendations = {f"tier{g.tier}:{g.scope}": g.recommended_disposition for g in gates}
    all_notes = list(notes)
    if policy.shadow:
        all_notes.append(
            "SHADOW MODE (eval-confidence policy): the preregistered gate is "
            "computed and reported but NOTHING is applied — no promotion, no "
            "demotion. The explicitly PROVISIONAL production policy is "
            "unchanged; activation requires the measured post-HUMAN-H5 "
            "P32.23 decision."
        )
    if llm_agreement is not None:
        all_notes.append(
            f"LLM agreement {llm_agreement:.3f} is SUPPLEMENTARY reporting — "
            "never a substitute for human ground truth (SIG-EVAL-004)."
        )

    return EvaluationReport(
        evaluator_version=EVALUATOR_VERSION,
        design_id=design.design_id,
        design_digest=design.digest(),
        manifest_verified=manifest_verified,
        estimands=estimands,
        gates=gates,
        design_problems=tuple(problems),
        policy_mode=policy.mode,
        policy_version=policy.version,
        applied=(),
        recommendations=recommendations,
        historical=tuple(historical),
        llm_agreement=llm_agreement,
        release_scopes=tuple(sorted(release_scopes)) if release_scopes else None,
        analysis_no=analysis_no,
        notes=tuple(all_notes),
    )


def activate_policy(
    policy: ConfidencePolicy,
    *,
    sample_count: int,
    measured_decision_ref: str | None,
    release_scopes: Sequence[str],
) -> ConfidencePolicy:
    """Attempt to arm the confidence policy — refuses every unsafe path.

    Activation requires ALL of: a nonzero sample, an authorized
    ``operational`` release scope, and a reference to the measured
    post-HUMAN-H5 P32.23 decision (the ADR that records the actual result).
    In this build the policy ships ``mode='shadow'`` and this function always
    raises — ``applied`` never becomes non-empty by deploying the evaluator.
    """
    missing: list[str] = []
    if sample_count <= 0:
        missing.append("zero_sample")
    if "operational" not in release_scopes:
        missing.append("no_operational_release")
    if not measured_decision_ref:
        missing.append("no_measured_decision")
    if policy.shadow:
        missing.append("policy_shadow_mode")
    if missing:
        raise ValueError("confidence policy activation refused — " + ", ".join(sorted(missing)))
    return policy


# --------------------------------------------------------------------------- #
# Rendering                                                                    #
# --------------------------------------------------------------------------- #
def _fmt(value: object, *, fmt: str = ".4f") -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return format(value, fmt)
    return str(value)


def render_report_md(report: EvaluationReport) -> str:
    """Render the evaluation report as Markdown — every estimand with its
    numerator, denominator, weights, method and population (SIG-EVAL-003)."""
    lines: list[str] = []
    lines.append(f"# Design-aware resolution evaluation — {report.design_id}")
    lines.append("")
    lines.append(
        f"> evaluator `{report.evaluator_version}` · design digest "
        f"`{report.design_digest}` · policy `{report.policy_version}` "
        f"mode **{report.policy_mode}** (applied: {len(report.applied)})"
    )
    lines.append("")
    if report.policy_mode != "active":
        lines.append(
            "> **SHADOW / INACTIVE** — this report computes the preregistered "
            "gate but applies nothing. The PROVISIONAL production policy is "
            "unchanged; certification requires the measured post-HUMAN-H5 "
            "P32.23 decision."
        )
        lines.append("")
    lines.append("## Estimands (separate frames, never pooled)")
    lines.append("")
    for name, est in sorted(report.estimands.items()):
        lines.append(f"### {name} — {est.state}")
        lines.append("")
        lines.append(f"- numerator / denominator: {_fmt(est.numerator)} / {_fmt(est.denominator)}")
        lines.append(f"- population: {est.population_note}")
        lines.append(f"- uncertainty method: {_fmt(est.method)}")
        if est.unavailable_reason:
            lines.append(f"- unavailable reason: `{est.unavailable_reason}`")
        for row in est.rows:
            lines.append(f"- `{dict(row)}`")
        lines.append("")
    lines.append("## Tier gates (preregistered hypotheses)")
    lines.append("")
    lines.append(
        "| tier | scope | α | drawn | same | diff | insuff | unres | missing | "
        "sealed | non-human | strict point | lower bound | method | verdict |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for g in report.gates:
        lines.append(
            f"| {g.tier} | {g.scope} | {g.alpha} | {g.drawn} | {g.successes} | "
            f"{g.different} | {g.insufficient} | {g.unresolved} | {g.missing} | "
            f"{g.sealed} | {g.non_human} | {_fmt(g.point_strict)} | "
            f"{_fmt(g.lower_bound)} | {_fmt(g.method)} | **{g.verdict}** |"
        )
    lines.append("")
    for g in report.gates:
        lines.append(
            f"- tier {g.tier} ({g.scope}): verdict `{g.verdict}`; reasons "
            f"{list(g.reasons)}; recommended `{g.recommended_disposition}` "
            f"(applied: {g.applied})"
        )
    if report.design_problems:
        lines.append("")
        lines.append("## Design problems")
        lines.append("")
        for p in report.design_problems:
            lines.append(f"- `{p}`")
    if report.historical:
        lines.append("")
        lines.append("## Historical point-gate metrics (history — NOT eligibility evidence)")
        lines.append("")
        for h in report.historical:
            lines.append(
                f"- {h.label} (tier {h.tier}): {_fmt(h.value)} as of {h.as_of} — {h.detail}"
            )
    if report.llm_agreement is not None:
        lines.append("")
        lines.append(
            f"LLM agreement (supplementary): {report.llm_agreement:.3f} — never "
            "a substitute for human ground truth."
        )
    if report.notes:
        lines.append("")
        lines.append("## Notes")
        lines.append("")
        for n in report.notes:
            lines.append(f"- {n}")
        lines.append("")
    return "\n".join(lines)
