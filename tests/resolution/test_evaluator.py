# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The design-aware evaluator + shadow confidence gates (P32.10, SIG-EVAL-003/004).

Pure, deterministic tests — the acceptance battery the ticket pins:

* 70/70 agent labels CANNOT certify a human 0.98 lower-bound gate (agent
  labels are not human ground truth — provenance fails AND the bound itself
  cannot reach 0.98 at n=70);
* exact all-success independent-sample calculations and two-tier multiplicity
  examples, cross-checked against an INDEPENDENT implementation (exact
  ``Fraction`` tail probabilities, not the module under test);
* correlated/enriched samples can never select the unjustified iid method;
* missing labels reduce strict performance or leave the evaluation
  inconclusive — they never disappear;
* sealed-test reuse, optional-stopping overrides and zero-sample activation
  all fail; deterministic metric vectors pass.
"""

from __future__ import annotations

import math
from fractions import Fraction

import pytest
from resolution.evaluator import (
    EvalUnit,
    HistoricalMetric,
    HypothesisSpec,
    SamplingDesign,
    StratumSpec,
    activate_policy,
    cell_estimate,
    clopper_pearson_lower,
    design_problems,
    evaluate,
    evaluate_tier_gate,
    hypergeometric_lower_bound,
    load_confidence_policy,
    render_report_md,
    report_digest,
    sampling_design_from_dict,
    weighted_simultaneous_bound,
)


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #
def _unit(
    sample_id: str,
    *,
    outcome: str = "same",
    provenance: str = "human",
    tier: int | None = 1,
    scope: str = "snapshot",
    stratum: str = "s1",
    partition: str = "sealed_final",
    group: str | None = None,
    sealed: bool = False,
    packet_ok: bool = True,
    estimand: str = "auto_positive_precision",
    **kw: object,
) -> EvalUnit:
    return EvalUnit(
        sample_id=sample_id,
        estimand=estimand,
        stratum_id=stratum,
        partition=partition,
        dependency_group_id=group if group is not None else f"dg-{sample_id}",
        outcome=outcome,
        reference_provenance=provenance,
        tier=tier,
        scope=scope,
        weight=1.0,
        selection_probability=1.0,
        sealed=sealed,
        packet_ok=packet_ok,
        **kw,  # type: ignore[arg-type]
    )


def _iid_design(*, alpha: float = 0.05, tier: int = 1, pop: int | None = None) -> SamplingDesign:
    return SamplingDesign(
        design_id="des-iid",
        kind="independent_bernoulli",
        equal_probability=True,
        independent_unit="item",
        independence_basis="declared exchangeable future-run model, preregistered",
        family_alpha=0.05,
        hypotheses=(
            HypothesisSpec(
                tier=tier,
                scope="snapshot",
                alpha=alpha,
                cells=(StratumSpec("s1", pop),),
            ),
        ),
        seed="s",
        target_population="tier-1 auto-positive edges, snapshot scope",
        frame_digest="fd",
        ruleset_digest="rd",
    )


def _srs_design(*, n_cells: int = 1, alpha: float = 0.05, tier: int = 1) -> SamplingDesign:
    cells = tuple(StratumSpec(f"s{i + 1}", 500) for i in range(n_cells))
    return SamplingDesign(
        design_id="des-srs",
        kind="stratified_srs",
        equal_probability=True,
        independent_unit="item",
        independence_basis="",
        family_alpha=0.05,
        hypotheses=(HypothesisSpec(tier=tier, scope="snapshot", alpha=alpha, cells=cells),),
        seed="s",
        target_population="tier-1 auto-positive edges",
    )


def _policy_shadow() -> object:
    return load_confidence_policy()


# --------------------------------------------------------------------------- #
# Exact bounds — pinned vectors + INDEPENDENT numerical cross-checks          #
# --------------------------------------------------------------------------- #
def test_cp_all_success_one_tier_149_passes_148_fails() -> None:
    """EVAL-A6: one prespecified tier at family α=0.05 — 149 all-success
    clears 0.98; 148 does not (the preregistered arithmetic, S3 §8)."""
    assert clopper_pearson_lower(149, 149, 0.05) == pytest.approx(0.9800951837793149)
    assert clopper_pearson_lower(149, 149, 0.05) >= 0.98
    assert clopper_pearson_lower(148, 148, 0.05) == pytest.approx(0.9799620483108958)
    assert clopper_pearson_lower(148, 148, 0.05) < 0.98


def test_cp_two_tier_bonferroni_183_passes_182_fails() -> None:
    """EVAL-A6: a two-tier Bonferroni family splits α to 0.025 each — the
    all-success floor rises to n=183 (182 fails)."""
    assert clopper_pearson_lower(183, 183, 0.025) == pytest.approx(0.9800439991586838)
    assert clopper_pearson_lower(183, 183, 0.025) >= 0.98
    assert clopper_pearson_lower(182, 182, 0.025) == pytest.approx(0.979935458235975)
    assert clopper_pearson_lower(182, 182, 0.025) < 0.98


def test_cp_70_all_success_cannot_reach_the_floor() -> None:
    """n=70 all-success lower bound ≈ 0.9581 < 0.98 — even perfect agent-era
    sample sizes cannot certify the 0.98 gate."""
    assert clopper_pearson_lower(70, 70, 0.05) == pytest.approx(0.9581066559331114)
    assert clopper_pearson_lower(70, 70, 0.05) < 0.98
    assert clopper_pearson_lower(100, 100, 0.05) == pytest.approx(0.9704869503929601)
    assert clopper_pearson_lower(100, 100, 0.05) < 0.98


def test_cp_independent_crosscheck_exact_fraction_tails() -> None:
    """Independent numerical cross-check: the module's bound is re-derived
    with exact rational binomial tails — a DIFFERENT implementation."""

    def exact_tail(k: int, n: int, p: Fraction) -> Fraction:
        return sum(Fraction(math.comb(n, j)) * p**j * (1 - p) ** (n - j) for j in range(k, n + 1))

    def exact_cp(k: int, n: int, alpha: Fraction) -> Fraction:
        lo, hi = Fraction(0), Fraction(1)
        for _ in range(120):
            mid = (lo + hi) / 2
            if exact_tail(k, n, mid) > alpha:
                hi = mid
            else:
                lo = mid
        return lo

    cases = (
        (7, 10, Fraction(5, 100)),
        (9, 10, Fraction(5, 100)),
        (4, 8, Fraction(25, 1000)),
    )
    for k, n, alpha in cases:
        ours = clopper_pearson_lower(k, n, float(alpha))
        theirs = float(exact_cp(k, n, alpha))
        assert ours == pytest.approx(theirs, abs=1e-9)


def test_cp_closed_form_all_success_is_exact_power() -> None:
    """The all-success bound is alpha**(1/n) — verify closed form AND that the
    tail at the bound straddles alpha (independent inequality check)."""
    for n, alpha in ((149, 0.05), (183, 0.025), (217, 0.0125)):
        assert clopper_pearson_lower(n, n, alpha) == pytest.approx(alpha ** (1 / n))
        below = alpha ** (1 / n)
        # monotonic tail: just below the bound the tail must be <= alpha
        p_lo = below - 1e-6
        p_hi = below + 1e-6

        tail = p_lo**n, p_hi**n  # P(X=n) = p**n at each side of the bound
        assert tail[0] < alpha < tail[1]


def test_hg_census_is_exactly_known() -> None:
    """A full census returns x/N exactly — the population rate is then known
    (subject to human reference error), no interval needed."""
    assert hypergeometric_lower_bound(50, 50, 50, 0.05) == pytest.approx(1.0)
    assert hypergeometric_lower_bound(49, 50, 50, 0.05) == pytest.approx(49 / 50)
    assert hypergeometric_lower_bound(0, 50, 50, 0.05) == 0.0


def test_hg_small_population_exact_vectors() -> None:
    """Known finite populations: bound = smallest K with P(X>=x) > alpha,
    recomputed here with an independent direct-combination implementation."""
    from math import comb

    def tail(x: int, n: int, N: int, K: int) -> Fraction:
        denom = comb(N, n)
        lo, hi = max(x, n - (N - K)), min(n, K)
        if lo > hi:
            return Fraction(0)
        return sum(Fraction(comb(K, j) * comb(N - K, n - j), denom) for j in range(lo, hi + 1))

    # N=20, n=10, x=9, alpha=0.05 → independent bound by exact scan.
    N, n, x, alpha = 20, 10, 9, Fraction(5, 100)
    expected_k = min(K for K in range(x, N - (n - x) + 1) if tail(x, n, N, K) > alpha)
    assert hypergeometric_lower_bound(x, n, N, float(alpha)) == pytest.approx(expected_k / N)


def test_hg_all_success_finite_population() -> None:
    """The all-success finite-population bound: N=1000, n=149 → ~0.982.
    And the bound never exceeds the CP iid bound (WOR — sampling without
    replacement can only help)."""
    hg = hypergeometric_lower_bound(149, 149, 1000, 0.05)
    cp = clopper_pearson_lower(149, 149, 0.05)
    assert hg == pytest.approx(0.982)
    assert hg >= cp


def test_hg_monotone_in_alpha_and_x() -> None:
    b = hypergeometric_lower_bound(90, 100, 500, 0.05)
    assert hypergeometric_lower_bound(90, 100, 500, 0.01) <= b
    assert hypergeometric_lower_bound(95, 100, 500, 0.05) >= b


def test_hg_rejects_bad_inputs() -> None:
    with pytest.raises(ValueError):
        hypergeometric_lower_bound(5, 10, 0, 0.05)
    with pytest.raises(ValueError):
        hypergeometric_lower_bound(11, 10, 50, 0.05)
    with pytest.raises(ValueError):
        clopper_pearson_lower(1, 0, 0.05)


# --------------------------------------------------------------------------- #
# Design/method discipline — correlated/enriched can never select iid         #
# --------------------------------------------------------------------------- #
def test_shared_dependency_group_forbids_iid() -> None:
    """Two certifying units in ONE dependency group are correlated — the iid
    frame is refused (SIG-EVAL-003)."""
    units = [
        _unit("a", group="dg-shared"),
        _unit("b", group="dg-shared"),
        _unit("c"),
    ]
    problems = design_problems(_iid_design(), units)
    assert "correlated_units_in_iid_frame" in problems


def test_unequal_probability_forbids_iid() -> None:
    design = SamplingDesign(
        design_id="d",
        kind="independent_bernoulli",
        equal_probability=False,
        independent_unit="item",
        independence_basis="x",
        family_alpha=0.05,
        hypotheses=(HypothesisSpec(1, "snapshot", 0.05, cells=(StratumSpec("s1", None),)),),
    )
    assert "iid_requires_equal_probability" in design_problems(design, [_unit("a")])


def test_iid_requires_a_recorded_basis() -> None:
    design = SamplingDesign(
        design_id="d",
        kind="independent_bernoulli",
        equal_probability=True,
        independent_unit="item",
        independence_basis="   ",
        family_alpha=0.05,
        hypotheses=(HypothesisSpec(1, "snapshot", 0.05, cells=(StratumSpec("s1", None),)),),
    )
    assert "iid_requires_recorded_basis" in design_problems(design, [_unit("a")])


def test_grouped_design_uses_finite_bounds_not_iid() -> None:
    """A grouped/PSU design routes to hypergeometric finite-population bounds
    — never Clopper–Pearson. Within-group hypergeometric is justified because
    the randomness is the sampling design, not the (correlated) content."""
    design = SamplingDesign(
        design_id="des-grouped",
        kind="grouped_psu",
        equal_probability=True,
        independent_unit="dependency_group",
        independence_basis="",
        family_alpha=0.05,
        hypotheses=(
            HypothesisSpec(
                1,
                "snapshot",
                0.05,
                cells=(
                    StratumSpec("g1", 200),
                    StratumSpec("g2", 200),
                ),
            ),
        ),
    )
    units = [
        _unit("a", stratum="g1", group="dg-a"),
        _unit("b", stratum="g1", group="dg-a"),  # same group — legal here
        _unit("c", stratum="g2", group="dg-c"),
    ]
    assert design_problems(design, units) == []
    est = cell_estimate(
        [u for u in units if u.stratum_id == "g1"],
        StratumSpec("g1", 200),
        design,
        alpha=0.025,
        total_population=400,
    )
    assert est.method == "hypergeometric_srs"
    assert est.lower_bound is not None


def test_enriched_strata_are_diagnostic_never_certifying() -> None:
    """An enriched/challenge stratum is reported but excluded from the gate —
    it cannot contribute certification units (SIG-EVAL-003)."""
    design = SamplingDesign(
        design_id="des-enr",
        kind="stratified_srs",
        equal_probability=True,
        independent_unit="item",
        independence_basis="",
        family_alpha=0.05,
        hypotheses=(
            HypothesisSpec(
                1,
                "snapshot",
                0.05,
                cells=(StratumSpec("s1", 500), StratumSpec("enr", 50, enriched=True)),
            ),
        ),
    )
    units = [_unit(f"u{i}") for i in range(149)] + [
        _unit("e1", stratum="enr"),
        _unit("e2", stratum="enr"),
    ]
    gate = evaluate_tier_gate(
        design.hypotheses[0],
        units,
        design,
        problems=[],
        manifest_verified=True,
        contamination=False,
        frozen_digests_match=True,
        analysis_no=1,
        interim_looks=0,
        early_stop=None,
        reused_test_set=False,
    )
    # Enriched units were reported as excluded — never silently pooled in.
    assert "diagnostic_units_excluded" in gate.reasons
    assert gate.drawn == 149
    assert gate.verdict == "certified"


def test_enriched_only_design_is_diagnostic() -> None:
    design = SamplingDesign(
        design_id="des-diag",
        kind="enriched_diagnostic",
        equal_probability=False,
        independent_unit="item",
        independence_basis="",
        family_alpha=0.05,
        hypotheses=(HypothesisSpec(1, "snapshot", 0.05, cells=(StratumSpec("e", None),)),),
    )
    assert "diagnostic_only_design" in design_problems(design, [_unit("a", stratum="e")])


def test_multiplicity_family_alpha_cannot_be_exceeded() -> None:
    design = SamplingDesign(
        design_id="d",
        kind="independent_bernoulli",
        equal_probability=True,
        independent_unit="item",
        independence_basis="x",
        family_alpha=0.05,
        hypotheses=(
            HypothesisSpec(1, "snapshot", 0.03, cells=(StratumSpec("s1", None),)),
            HypothesisSpec(2, "snapshot", 0.03, cells=(StratumSpec("s2", None),)),
        ),
    )
    assert "multiplicity_alpha_exceeded" in design_problems(design, [_unit("a")])


def test_optional_stopping_rule_is_a_design_problem() -> None:
    design = SamplingDesign(
        design_id="d",
        kind="independent_bernoulli",
        equal_probability=True,
        independent_unit="item",
        independence_basis="x",
        family_alpha=0.05,
        hypotheses=(HypothesisSpec(1, "snapshot", 0.05, cells=(StratumSpec("s1", None),)),),
        stopping_rule="sequential_peek",
    )
    assert "optional_stopping_rule" in design_problems(design, [_unit("a")])


def test_multi_look_schedule_is_a_design_problem() -> None:
    design = SamplingDesign(
        design_id="d",
        kind="independent_bernoulli",
        equal_probability=True,
        independent_unit="item",
        independence_basis="x",
        family_alpha=0.05,
        hypotheses=(HypothesisSpec(1, "snapshot", 0.05, cells=(StratumSpec("s1", None),)),),
        scheduled_analyses=2,
    )
    assert "multi_look_schedule" in design_problems(design, [_unit("a")])


# --------------------------------------------------------------------------- #
# Strict unresolved-label handling — nothing disappears                       #
# --------------------------------------------------------------------------- #
def test_missing_label_counts_against_strict_and_incomplete() -> None:
    """One missing label: still in the denominator (strict point drops), the
    campaign is incomplete, certification impossible — never disappeared."""
    design = _iid_design()
    units = [_unit(f"u{i}") for i in range(148)] + [_unit("u_missing", outcome="missing")]
    gate = evaluate_tier_gate(
        design.hypotheses[0],
        units,
        design,
        problems=[],
        manifest_verified=True,
        contamination=False,
        frozen_digests_match=True,
        analysis_no=1,
        interim_looks=0,
        early_stop=None,
        reused_test_set=False,
    )
    assert gate.drawn == 149
    assert gate.missing == 1
    assert gate.successes == 148
    assert gate.point_strict == pytest.approx(148 / 149)
    assert gate.verdict == "incomplete"
    assert "missing_labels" in gate.reasons
    assert "incomplete_labeling" in gate.reasons


def test_insufficient_unresolved_different_are_non_successes() -> None:
    for outcome in ("different", "insufficient_evidence", "unresolved"):
        u = _unit("x", outcome=outcome)
        assert not u.is_success
        assert u.is_terminal  # accounted — not disappeared


def test_missing_is_never_terminal() -> None:
    u = _unit("x", outcome="missing")
    assert not u.is_success
    assert not u.is_terminal


def test_sealed_unit_stays_in_denominator_and_blocks() -> None:
    design = _iid_design()
    units = [_unit(f"u{i}") for i in range(148)] + [
        _unit("u_sealed", outcome="missing", sealed=True)
    ]
    gate = evaluate_tier_gate(
        design.hypotheses[0],
        units,
        design,
        problems=[],
        manifest_verified=True,
        contamination=False,
        frozen_digests_match=True,
        analysis_no=1,
        interim_looks=0,
        early_stop=None,
        reused_test_set=False,
    )
    assert gate.drawn == 149
    assert gate.sealed == 1
    assert gate.verdict == "incomplete"
    assert "sealed_units" in gate.reasons


# --------------------------------------------------------------------------- #
# Eligibility — provenance, integrity, multiplicity, stopping                 #
# --------------------------------------------------------------------------- #
def _gate(
    units: list[EvalUnit],
    design: SamplingDesign,
    **kw: object,
) -> object:
    defaults = {
        "problems": [],
        "manifest_verified": True,
        "contamination": False,
        "frozen_digests_match": True,
        "analysis_no": 1,
        "interim_looks": 0,
        "early_stop": None,
        "reused_test_set": False,
    }
    defaults.update(kw)
    return evaluate_tier_gate(design.hypotheses[0], units, design, **defaults)  # type: ignore[arg-type]


def test_70_agent_labels_cannot_certify_the_human_gate() -> None:
    """THE negative case: 70/70 'same' labels authored by an agent fail twice —
    provenance is not human, and even if it were, n=70 cannot reach the 0.98
    bound (lower ≈ 0.958)."""
    design = _iid_design()
    units = [_unit(f"a{i}", provenance="agent") for i in range(70)]
    gate = _gate(units, design)
    assert gate.verdict == "not_certified"
    assert "non_human_reference" in gate.reasons
    assert "bound_below_floor" in gate.reasons
    assert gate.lower_bound is not None and gate.lower_bound < 0.98
    # Human labels at the same size would ALSO fail the bound — the agent
    # failure is not rescued by swapping provenance.
    gate_h = _gate([_unit(f"h{i}") for i in range(70)], design)
    assert gate_h.verdict == "not_certified"
    assert "non_human_reference" not in gate_h.reasons
    assert "bound_below_floor" in gate_h.reasons


@pytest.mark.parametrize("bad", ["agent", "llm", "synthetic", "unknown"])
def test_no_nonhuman_provenance_can_certify(bad: str) -> None:
    design = _iid_design()
    units = [_unit(f"u{i}", provenance=bad) for i in range(149)]
    gate = _gate(units, design)
    assert "non_human_reference" in gate.reasons
    assert gate.verdict != "certified"


def test_149_human_iid_would_certify_but_shadow_applies_nothing() -> None:
    """The positive path IN SHADOW: 149 human-labeled all-success units on a
    single-tier α=0.05 hypothesis yield bound ≥ 0.98 and verdict 'certified' —
    yet `applied` stays empty because the policy is shadow."""
    design = _iid_design()
    units = [_unit(f"u{i}") for i in range(149)]
    gate = _gate(units, design)
    assert gate.verdict == "certified"
    assert gate.lower_bound == pytest.approx(0.9800951837793149)
    assert gate.recommended_disposition == "certify"
    assert gate.applied is False

    report = evaluate(units=units, design=design)
    assert report.applied == ()
    assert report.policy_mode == "shadow"
    assert report.recommendations["tier1:snapshot"] == "certify"
    assert any("SHADOW MODE" in n for n in report.notes)


def test_two_tier_family_sits_inside_family_alpha() -> None:
    """Two prespecified tiers, Bonferroni 0.025 each — each needs n≥183."""
    design = SamplingDesign(
        design_id="des-2t",
        kind="independent_bernoulli",
        equal_probability=True,
        independent_unit="item",
        independence_basis="x",
        family_alpha=0.05,
        hypotheses=(
            HypothesisSpec(1, "snapshot", 0.025, cells=(StratumSpec("s1", None),)),
            HypothesisSpec(3, "snapshot", 0.025, cells=(StratumSpec("s3", None),)),
        ),
    )
    units = [_unit(f"a{i}", tier=1, stratum="s1") for i in range(183)] + [
        _unit(f"b{i}", tier=3, stratum="s3") for i in range(182)
    ]
    g1 = _gate(units, design)  # hypothesis[0] = tier 1, 183 → passes
    assert g1.verdict == "certified"
    g3 = evaluate_tier_gate(
        design.hypotheses[1],
        units,
        design,
        problems=[],
        manifest_verified=True,
        contamination=False,
        frozen_digests_match=True,
        analysis_no=1,
        interim_looks=0,
        early_stop=None,
        reused_test_set=False,
    )
    assert g3.verdict == "not_certified"
    assert "bound_below_floor" in g3.reasons
    # The failed tier is STILL reported — it cannot be dropped from the family.
    report = evaluate(units=units, design=design)
    assert len(report.gates) == 2
    assert {g.tier for g in report.gates} == {1, 3}


def test_unattempted_hypothesis_reports_zero_not_pass() -> None:
    """A preregistered tier with NO sample cannot pass on silence — it stays
    in the family as incomplete zero-evidence; an EMPTY deployment frame is
    not_applicable."""
    declared_but_unsampled = SamplingDesign(
        design_id="des-empty",
        kind="independent_bernoulli",
        equal_probability=True,
        independent_unit="item",
        independence_basis="x",
        family_alpha=0.05,
        hypotheses=(HypothesisSpec(1, "snapshot", 0.05, cells=(StratumSpec("s1", 500),)),),
    )
    gate = _gate([], declared_but_unsampled)
    assert gate.verdict == "incomplete"
    assert "zero_sample" in gate.reasons
    assert gate.recommended_disposition == "review_only_fail_safe"
    # An empty deployment frame (no declared population, no draws) is
    # not_applicable — never a performance pass.
    gate_na = _gate([], _iid_design())
    assert gate_na.verdict == "not_applicable"
    assert gate_na.recommended_disposition == "retain_provisional"


def test_manifest_unverified_blocks() -> None:
    gate = _gate([_unit(f"u{i}") for i in range(149)], _iid_design(), manifest_verified=False)
    assert "manifest_unverified" in gate.reasons
    assert gate.verdict == "not_certified"


def test_contamination_blocks() -> None:
    gate = _gate([_unit(f"u{i}") for i in range(149)], _iid_design(), contamination=True)
    assert "contamination" in gate.reasons
    assert gate.verdict == "not_certified"


def test_candidate_digest_mismatch_blocks() -> None:
    gate = _gate([_unit(f"u{i}") for i in range(149)], _iid_design(), frozen_digests_match=False)
    assert "candidate_digest_mismatch" in gate.reasons
    assert gate.verdict == "not_certified"


def test_sealed_test_reuse_fails() -> None:
    """A set already exposed (inspected/tuned on) can never re-certify."""
    gate = _gate([_unit(f"u{i}") for i in range(149)], _iid_design(), reused_test_set=True)
    assert "reused_test_set" in gate.reasons
    assert gate.verdict == "not_certified"


def test_optional_stopping_overrides_fail() -> None:
    """An interim look or a second analysis cannot mint eligibility."""
    gate = _gate([_unit(f"u{i}") for i in range(149)], _iid_design(), interim_looks=1)
    assert "optional_stopping" in gate.reasons
    assert gate.verdict == "not_certified"
    gate2 = _gate([_unit(f"u{i}") for i in range(149)], _iid_design(), analysis_no=2)
    assert "optional_stopping" in gate2.reasons
    assert gate2.verdict == "not_certified"


def test_early_stop_records_no_pass() -> None:
    gate = _gate([_unit(f"u{i}") for i in range(149)], _iid_design(), early_stop="futility")
    assert gate.verdict == "incomplete"
    assert "early_stop_no_pass" in gate.reasons


def test_zero_sample_activation_fails() -> None:
    pol = load_confidence_policy()
    with pytest.raises(ValueError, match="zero_sample"):
        activate_policy(
            pol,
            sample_count=0,
            measured_decision_ref="ADR-200",
            release_scopes=("operational",),
        )


def test_activation_refuses_without_measured_decision_or_release() -> None:
    pol = load_confidence_policy()
    with pytest.raises(ValueError, match="no_measured_decision"):
        activate_policy(
            pol,
            sample_count=149,
            measured_decision_ref=None,
            release_scopes=("operational",),
        )
    with pytest.raises(ValueError, match="no_operational_release"):
        activate_policy(
            pol,
            sample_count=149,
            measured_decision_ref="ADR-200",
            release_scopes=("final",),
        )
    # Even with every input satisfied the shadow policy itself refuses.
    with pytest.raises(ValueError, match="policy_shadow_mode"):
        activate_policy(
            pol,
            sample_count=149,
            measured_decision_ref="ADR-200",
            release_scopes=("operational",),
        )


def test_policy_file_is_shadow() -> None:
    pol = load_confidence_policy()
    assert pol.mode == "shadow"
    assert pol.family_alpha == 0.05
    assert pol.threshold == 0.98
    assert pol.stopping_rule == "fixed"
    assert "P32.23" in pol.activation_authority


def test_llm_is_supplementary_never_evidence() -> None:
    """LLM agreement rides the report as a labelled supplement; it enters no
    gate input (SIG-EVAL-004)."""
    design = _iid_design()
    units = [_unit(f"u{i}") for i in range(149)]
    report = evaluate(units=units, design=design, llm_agreement=0.91)
    assert report.llm_agreement == 0.91
    assert any("SUPPLEMENTARY" in n for n in report.notes)
    # And LLM-labelled units cannot certify (already covered) — the report
    # must not silently treat llm_agreement as a pass.
    units_llm = [_unit(f"u{i}", provenance="llm") for i in range(149)]
    gate = _gate(units_llm, design)
    assert gate.verdict != "certified"


# --------------------------------------------------------------------------- #
# Estimands — separate frames, weights, unavailable states                    #
# --------------------------------------------------------------------------- #
def test_stratified_weighted_estimate_is_not_a_raw_pool() -> None:
    """Oversampled strata cannot dominate: the estimate uses Σ W_h p̂_h, not a
    pooled average (SIG-EVAL-003)."""
    design = SamplingDesign(
        design_id="des-strat",
        kind="stratified_srs",
        equal_probability=True,
        independent_unit="item",
        independence_basis="",
        family_alpha=0.05,
        hypotheses=(
            HypothesisSpec(
                1,
                "snapshot",
                0.05,
                cells=(StratumSpec("big", 900), StratumSpec("small", 100)),
            ),
        ),
    )
    # big stratum: 90/100 successes; small stratum: 10/10 — oversampled small.
    units = [
        _unit(f"b{i}", stratum="big", outcome=("same" if i < 90 else "different"))
        for i in range(100)
    ] + [_unit(f"s{i}", stratum="small") for i in range(10)]
    estimates = [
        cell_estimate(
            [u for u in units if u.stratum_id == "big"],
            StratumSpec("big", 900),
            design,
            alpha=0.025,
            total_population=1000,
        ),
        cell_estimate(
            [u for u in units if u.stratum_id == "small"],
            StratumSpec("small", 100),
            design,
            alpha=0.025,
            total_population=1000,
        ),
    ]
    bound = weighted_simultaneous_bound(estimates)
    # Weighted bound = 0.9*L_big + 0.1*L_small — NOT pooled raw precision.
    pooled = 100 / 110
    assert estimates[0].weight == pytest.approx(0.9)
    assert estimates[1].weight == pytest.approx(0.1)
    assert bound is not None and bound < pooled  # bound is honest-conservative
    # and the design-weighted point differs from the raw pool
    wpoint = (estimates[0].weight or 0) * (estimates[0].point_strict or 0) + (
        estimates[1].weight or 0
    ) * (estimates[1].point_strict or 0)
    assert wpoint == pytest.approx(0.9 * 0.9 + 0.1 * 1.0)
    assert wpoint != pytest.approx(pooled)


def test_unmeasured_stratum_contributes_zero_weight_times_zero() -> None:
    """An unobserved nonempty cell contributes L=0 — the bound reflects the
    unmeasured mass instead of pretending it passed."""
    estimates = (
        cell_estimate(
            [_unit(f"a{i}", stratum="s1") for i in range(10)],
            StratumSpec("s1", 500),
            _srs_design(n_cells=2),
            alpha=0.025,
            total_population=1000,
        ),
        cell_estimate(
            [],
            StratumSpec("s2", 500),
            _srs_design(n_cells=2),
            alpha=0.025,
            total_population=1000,
        ),
    )
    bound = weighted_simultaneous_bound(estimates)
    assert bound == pytest.approx(0.5 * estimates[0].lower_bound + 0.5 * 0.0)


def test_estimands_reported_separately_with_named_populations() -> None:
    units = [_unit(f"u{i}") for i in range(10)]
    report = evaluate(units=units, design=_iid_design())
    assert set(report.estimands) == {
        "auto_positive_precision",
        "candidate_recall",
        "cluster_quality",
        "labelability",
    }
    auto = report.estimands["auto_positive_precision"]
    assert auto.state == "measured"
    assert auto.numerator == 10 and auto.denominator == 10
    assert auto.population_note
    recall = report.estimands["candidate_recall"]
    assert recall.state == "unavailable"
    assert recall.unavailable_reason == "no_recall_frame"


def test_candidate_recall_candidate_only_frame_is_unavailable() -> None:
    """A sample of the matcher's own candidates cannot observe blocking false
    negatives — unavailable, never a manufactured recall."""
    units = [
        _unit(f"r{i}", estimand="candidate_recall", offered_to_matcher=None) for i in range(10)
    ]
    report = evaluate(units=units, design=_iid_design())
    recall = report.estimands["candidate_recall"]
    assert recall.state == "unavailable"
    assert recall.unavailable_reason == "candidate_only_frame"


def test_candidate_recall_measured_with_undecided_stay_visible() -> None:
    units = [
        *[
            _unit(f"r{i}", estimand="candidate_recall", offered_to_matcher=(i < 8))
            for i in range(10)
        ],
        _unit(
            "u1",
            estimand="candidate_recall",
            outcome="insufficient_evidence",
            offered_to_matcher=True,
        ),
    ]
    report = evaluate(units=units, design=_iid_design())
    recall = report.estimands["candidate_recall"]
    assert recall.state == "partial"
    assert recall.numerator == 8 and recall.denominator == 10
    row = recall.rows[0]
    assert row["undecided_reference"] == 1
    assert row["recall_lower_strict"] == pytest.approx(8 / 11)


def test_cluster_quality_pair_only_cannot_claim_whole_cluster() -> None:
    """A pair sample alone cannot produce whole-cluster quality (SIG-EVAL-003)
    — without reference-cluster memberships the estimand is unavailable."""
    units = [_unit(f"p{i}", estimand="cluster_quality") for i in range(5)]
    report = evaluate(units=units, design=_iid_design())
    cq = report.estimands["cluster_quality"]
    assert cq.state == "unavailable"
    assert cq.unavailable_reason == "no_reference_clusters"


def test_cluster_quality_bad_bridge_visibly_hurts_cluster_metrics() -> None:
    """EVAL-A9: a synthetic bad bridge that passes an edge-local plausibility
    check still visibly harms the cluster metrics."""
    units = []
    # Two reference clusters {a1,a2,a3} and {b1,b2}; the prediction merges them
    # through one bad bridge — every predicted member is one cluster.
    for i, e in enumerate(("a1", "a2", "a3")):
        units.append(
            _unit(
                f"u{i}",
                estimand="cluster_quality",
                entity_id=e,
                reference_cluster_id="RA",
                predicted_cluster_id="P1",
            )
        )
    for i, e in enumerate(("b1", "b2")):
        units.append(
            _unit(
                f"v{i}",
                estimand="cluster_quality",
                entity_id=e,
                reference_cluster_id="RB",
                predicted_cluster_id="P1",
            )
        )
    report = evaluate(units=units, design=_iid_design())
    cq = report.estimands["cluster_quality"]
    assert cq.state == "measured"
    row = cq.rows[0]
    # The merge is exactly recovered at the entity level but pairwise/B-cubed
    # show the damage: predicted cluster mixes two truth clusters.
    assert row["pairwise_recall"] == pytest.approx(1.0)  # all true pairs found
    assert row["pairwise_precision"] < 1.0  # plus false pairs
    assert row["bcubed_precision"] < 1.0


def test_cluster_quality_unresolved_entities_count_not_invented() -> None:
    units = [
        _unit(
            "a",
            estimand="cluster_quality",
            entity_id="a",
            reference_cluster_id="R1",
            predicted_cluster_id="P1",
        ),
        _unit("b", estimand="cluster_quality", entity_id="b"),  # unlabeled entity
    ]
    report = evaluate(units=units, design=_iid_design())
    cq = report.estimands["cluster_quality"]
    assert cq.state == "partial"
    assert cq.unavailable_reason == "partial_reference_coverage"
    assert cq.rows[0]["unresolved_entities"] == 1


def test_labelability_reports_decisive_fraction() -> None:
    units = [
        _unit("a", outcome="same"),
        _unit("b", outcome="different"),
        _unit("c", outcome="insufficient_evidence"),
        _unit("d", outcome="missing"),
    ]
    report = evaluate(units=units, design=_iid_design())
    lab = report.estimands["labelability"]
    assert lab.state == "measured"
    assert lab.numerator == 2 and lab.denominator == 4
    assert lab.rows[0]["decisive_fraction"] == pytest.approx(0.5)


# --------------------------------------------------------------------------- #
# Determinism, history, rendering                                             #
# --------------------------------------------------------------------------- #
def test_deterministic_metric_vector_and_digest() -> None:
    design = _iid_design()
    units = [_unit(f"u{i}") for i in range(149)]
    r1 = evaluate(units=units, design=design)
    r2 = evaluate(units=list(reversed(units)), design=design)
    assert report_digest(r1) == report_digest(r2)
    # And a changed input changes the digest — tamper-evident.
    r3 = evaluate(units=units[:148], design=design)
    assert report_digest(r3) != report_digest(r1)


def test_historical_metrics_are_labelled_history_not_evidence() -> None:
    hist = (
        HistoricalMetric(
            label="camera_site v2 holdout tier 1g",
            tier=1,
            value=1.0,
            detail="70/70 point estimate (agent/maintainer-verified) — history",
            as_of="ADR-105",
        ),
    )
    report = evaluate(
        units=[_unit(f"u{i}") for i in range(149)],
        design=_iid_design(),
        historical=hist,
    )
    assert report.historical[0].kind == "historical_point_gate"
    md = render_report_md(report)
    assert "NOT eligibility evidence" in md
    assert "SHADOW" in md


def test_render_report_sections() -> None:
    report = evaluate(units=[_unit(f"u{i}") for i in range(5)], design=_iid_design())
    md = render_report_md(report)
    assert "## Estimands" in md
    assert "## Tier gates" in md
    assert "auto_positive_precision" in md
    assert "labelability" in md


def test_sampling_design_from_dict_roundtrip_digest() -> None:
    """The preregistration record rebuilds a byte-identical design — the
    stored JSON and the live object pin the same digest."""
    design = _srs_design(n_cells=2)
    raw = {
        "design_id": design.design_id,
        "kind": design.kind,
        "equal_probability": design.equal_probability,
        "independent_unit": design.independent_unit,
        "independence_basis": design.independence_basis,
        "family_alpha": design.family_alpha,
        "hypotheses": [
            {
                "tier": h.tier,
                "scope": h.scope,
                "alpha": h.alpha,
                "threshold": h.threshold,
                "cells": [
                    {"stratum_id": c.stratum_id, "population": c.population} for c in h.cells
                ],
            }
            for h in design.hypotheses
        ],
        "seed": design.seed,
        "target_population": design.target_population,
    }
    rebuilt = sampling_design_from_dict(raw)
    assert rebuilt.digest() == design.digest()
    with pytest.raises(ValueError):
        sampling_design_from_dict({**raw, "kind": "bogus"})


def test_failing_tier_recommends_fail_safe_review_never_applied() -> None:
    """Fail-safe per-tier demotion: an uncertified tier recommends review-only
    — and even that is a recommendation, applied=False (a pre-campaign safety
    demotion is a separate operational decision)."""
    design = _iid_design()
    units = [_unit(f"u{i}") for i in range(70)]  # can't reach the bound
    report = evaluate(units=units, design=design)
    gate = report.gates[0]
    assert gate.verdict == "not_certified"
    assert gate.recommended_disposition == "review_only_fail_safe"
    assert gate.applied is False
    assert report.applied == ()
