# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ratchet engine + record contracts (P34.44a, SIG-CONF-007, ADR-154 d.2/4):
regressions past baseline fail, improvements are recorded, baselines move only
toward thresholds, loosening needs a new ADR, enforce flips only in the fixing
row, B3/B4 never gate, and a zero-evaluated check fails (SIG-ENG-042)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from exports.quality import (
    PROBE_RUN_VERSION,
    REPORT_VERSION,
    CheckRegistry,
    Measurement,
    QualityCheck,
    RegistryError,
    Threshold,
    build_probe_run,
    build_quality_report,
    diff_registry,
    evaluate_check,
    load_registry,
    run_release_gate,
    summarize,
)


def _check(**kw: object) -> QualityCheck:
    """A minimal synthetic check — a fixture row, not a living record."""
    defaults: dict[str, object] = dict(
        check_id="GQ-99",
        statement="synthetic check",
        population="things",
        placement=frozenset({"M"}),
        mode="ratchet",
        direction="lower_is_better",
        threshold=Threshold.parse("<= 0"),
        baseline=10.0,
        baseline_pending=False,
        unit="count",
        basis_class="B1",
        fixing=("P35.1",),
        source_ids="TEST",
        note="",
    )
    defaults.update(kw)
    return QualityCheck(**defaults)  # type: ignore[arg-type]


def _measure(check_id: str = "GQ-99", **kw: object) -> Measurement:
    defaults: dict[str, object] = dict(check_id=check_id, offered=100, evaluated=100, measured=0.0)
    defaults.update(kw)
    return Measurement(**defaults)  # type: ignore[arg-type]


# --- evaluate_check ---------------------------------------------------------


def test_enforce_pass_and_fail_on_threshold() -> None:
    check = _check(mode="enforce")
    assert evaluate_check(check, _measure(measured=0)).outcome == "pass"
    out = evaluate_check(check, _measure(measured=3))
    assert out.outcome == "fail"
    assert "threshold" in out.reason


def test_ratchet_regression_fails_past_baseline() -> None:
    check = _check(baseline=10.0)
    out = evaluate_check(check, _measure(measured=11))
    assert out.outcome == "fail" and out.regression
    assert "regresses past baseline" in out.reason


def test_ratchet_improvement_is_recorded_not_gated() -> None:
    check = _check(baseline=10.0)
    out = evaluate_check(check, _measure(measured=4))
    assert out.outcome == "pass" and out.improvement


def test_ratchet_at_baseline_passes() -> None:
    check = _check(baseline=10.0)
    out = evaluate_check(check, _measure(measured=10))
    assert out.outcome == "pass" and not out.improvement and not out.regression


def test_ratchet_pending_baseline_is_unbaselined_not_a_pass() -> None:
    check = _check(baseline=None, baseline_pending=True)
    out = evaluate_check(check, _measure(measured=42))
    assert out.outcome == "unbaselined"


def test_higher_is_better_direction() -> None:
    check = _check(direction="higher_is_better", baseline=0.5)
    regressed = evaluate_check(check, _measure(measured=0.4))
    improved = evaluate_check(check, _measure(measured=0.9))
    assert regressed.regression and regressed.outcome == "fail"
    assert improved.improvement and improved.outcome == "pass"


def test_report_mode_never_gates() -> None:
    check = _check(mode="report", baseline=None)
    assert evaluate_check(check, _measure(measured=99999)).outcome == "pass"


def test_report_wrong_way_is_class_s_signal() -> None:
    check = _check(mode="report", baseline=0.2, direction="lower_is_better")
    out = evaluate_check(check, _measure(measured=0.9))
    assert out.outcome == "pass" and out.alert_band_breach


def test_zero_evaluated_fails_even_with_empty_population() -> None:
    """SIG-ENG-042: a check that examined nothing cannot pass — even when the
    offered population was empty (the honest-vacuum rule)."""
    for mode in ("enforce", "ratchet", "report"):
        out = evaluate_check(_check(mode=mode), _measure(offered=0, evaluated=0))
        assert out.outcome == "fail", mode
        assert "no vacuous pass" in out.reason


def test_not_evaluable_is_never_a_pass() -> None:
    out = evaluate_check(
        _check(mode="enforce"),
        _measure(offered=0, evaluated=0, not_evaluable_reason="seam absent"),
    )
    assert out.outcome == "not_evaluable" and out.reason == "seam absent"


def test_missing_measured_value_is_not_evaluable() -> None:
    out = evaluate_check(_check(), _measure(measured=None))
    assert out.outcome == "not_evaluable"


def test_outcome_carries_counts_and_basis() -> None:
    out = evaluate_check(_check(), _measure(offered=10, evaluated=4, measured=1))
    assert out.offered == 10 and out.evaluated == 4 and out.measured == 1.0
    assert out.basis_class == "B1" and out.mode == "ratchet"


# --- summarize + records ----------------------------------------------------


def _run(outcomes: list, **kw: object) -> dict:
    defaults = dict(placement="M", target="test", generated_at=datetime(2026, 10, 8, tzinfo=UTC))
    defaults.update(kw)
    return build_quality_report(load_registry(), outcomes, **defaults)  # type: ignore[arg-type]


def test_summarize_overall_pass() -> None:
    s = summarize([evaluate_check(_check(mode="enforce"), _measure(measured=0))])
    assert s.overall == "pass"


def test_summarize_partial_when_unbaselined() -> None:
    check = _check(baseline=None, baseline_pending=True)
    s = summarize([evaluate_check(check, _measure(measured=1))])
    assert s.overall == "partial" and s.unbaselined == ("GQ-99",)


def test_report_shape_is_sig_quality_report_1() -> None:
    out = evaluate_check(_check(), _measure(measured=7, offered=50, evaluated=50))
    report = _run([out])
    assert report["version"] == REPORT_VERSION
    assert report["placement"] == "M"
    assert report["registry"]["schema"] == "sig.quality-checks/1"
    row = report["checks"][0]
    for key in (
        "id",
        "mode",
        "basis_class",
        "outcome",
        "offered",
        "evaluated",
        "measured",
        "baseline",
        "baseline_pending",
        "threshold",
        "direction",
        "regression",
        "improvement",
        "reason",
    ):
        assert key in row
    assert report["totals"] == {"offered": 50, "evaluated": 50}
    assert report["summary"]["overall"] == "pass"


def test_probe_run_envelope_is_sig_probe_run_1() -> None:
    out = evaluate_check(_check(), _measure(measured=7))
    probe = build_probe_run(_run([out]))
    assert probe["version"] == PROBE_RUN_VERSION
    assert probe["probe"] == "sig-quality"
    assert probe["overall"] == report_overall(probe)
    assert probe["checks"][0]["name"] == "GQ-99"
    assert probe["checks"][0]["evaluated"] == 100


def report_overall(probe: dict) -> str:
    return probe["report"]["summary"]["overall"]


def test_report_is_deterministic() -> None:
    out = evaluate_check(_check(), _measure(measured=7))
    a = _run([out])
    b = _run([out])
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


# --- the release gate (V15 hook) -------------------------------------------


def test_release_gate_passes_clean_report() -> None:
    out = evaluate_check(_check(mode="enforce"), _measure(measured=0))
    gate = run_release_gate(_run([out]))
    assert gate["verdict"] == "pass"


def test_release_gate_fails_on_enforce_failure() -> None:
    out = evaluate_check(_check(mode="enforce"), _measure(measured=2))
    gate = run_release_gate(_run([out]))
    assert gate["verdict"] == "fail" and gate["enforce_failures"] == ["GQ-99"]


def test_release_gate_fails_on_ratchet_regression() -> None:
    out = evaluate_check(_check(baseline=1.0), _measure(measured=9))
    gate = run_release_gate(_run([out]))
    assert gate["verdict"] == "fail" and gate["ratchet_regressions"] == ["GQ-99"]


def test_release_gate_fails_closed_on_not_evaluable_enforce() -> None:
    out = evaluate_check(
        _check(mode="enforce"),
        _measure(evaluated=0, not_evaluable_reason="artifact absent"),
    )
    gate = run_release_gate(_run([out]))
    assert gate["verdict"] == "fail"
    assert gate["not_evaluable_enforce"] == ["GQ-99"]


def test_release_gate_ignores_report_and_unbaselined() -> None:
    report_out = evaluate_check(_check(mode="report", baseline=None), _measure())
    unbaselined = evaluate_check(_check(baseline=None, baseline_pending=True), _measure(measured=9))
    gate = run_release_gate(_run([report_out, unbaselined]))
    assert gate["verdict"] == "pass"


def test_release_gate_rejects_non_report() -> None:
    with pytest.raises(RegistryError):
        run_release_gate({"version": "something/else"})


# --- the registry diff (the rules on the ruleset) ----------------------------


def _reg(*checks: QualityCheck) -> CheckRegistry:
    """A CheckRegistry built directly — lets the diff see states load_registry
    would refuse (e.g. a B3 gating flip), so the diff's own guard is tested."""
    return CheckRegistry(version="1", checks=tuple(checks), digest="test")


def test_diff_allows_baseline_move_toward_threshold() -> None:
    old, new = _reg(_check()), _reg(_check(baseline=5.0))
    assert diff_registry(old, new, ticket="P35.1") == []


def test_diff_rejects_baseline_move_away_from_threshold() -> None:
    old, new = _reg(_check()), _reg(_check(baseline=15.0))
    violations = diff_registry(old, new, ticket="P35.1")
    assert [v.field for v in violations] == ["baseline"]
    assert "requires a new ADR" in violations[0].message


def test_diff_allows_loosening_with_adr() -> None:
    old, new = _reg(_check()), _reg(_check(baseline=15.0))
    assert diff_registry(old, new, ticket="P35.1", adr_ids=("ADR-999",)) == []


def test_diff_rejects_erasing_a_baseline() -> None:
    old = _reg(_check())
    new = _reg(_check(baseline=None, baseline_pending=True))
    assert [v.field for v in diff_registry(old, new, ticket="P35.1")] == ["baseline"]


def test_diff_allows_establishing_a_pending_baseline() -> None:
    old = _reg(_check(baseline=None, baseline_pending=True))
    new = _reg(_check(baseline=3.0))
    assert diff_registry(old, new, ticket="P35.1") == []


def test_diff_higher_is_better_direction() -> None:
    old = _reg(_check(direction="higher_is_better", baseline=0.5))
    better = _reg(_check(direction="higher_is_better", baseline=0.7))
    worse = _reg(_check(direction="higher_is_better", baseline=0.3))
    assert diff_registry(old, better, ticket="P35.1") == []
    assert [v.field for v in diff_registry(old, worse, ticket="P35.1")] == ["baseline"]


def test_diff_rejects_threshold_loosening() -> None:
    old = _reg(_check())
    new = _reg(_check(threshold=Threshold.parse("<= 5")))
    v = diff_registry(old, new, ticket="P35.1")
    assert [x.field for x in v] == ["threshold"]
    assert diff_registry(old, new, ticket="P35.1", adr_ids=("ADR-1",)) == []


def test_diff_allows_threshold_tightening() -> None:
    old = _reg(_check(threshold=Threshold.parse("<= 5")))
    new = _reg(_check(threshold=Threshold.parse("<= 2")))
    assert diff_registry(old, new, ticket="P35.1") == []


def test_diff_enforce_flip_only_in_fixing_row() -> None:
    """SIG-CONF-007: a ratchet check flips to enforce only in its fixing row."""
    old = _reg(_check(fixing=("P35.46",)))
    new = _reg(_check(mode="enforce", fixing=("P35.46",)))
    assert diff_registry(old, new, ticket="P35.46") == []
    v = diff_registry(old, new, ticket="P35.99")
    assert [x.field for x in v] == ["mode"]
    assert "fixing" in v[0].message


def test_diff_enforce_flip_rejects_non_gating_basis() -> None:
    """SIG-CONF-003 at the diff layer too: even in the fixing row, a B3 check
    may not flip to enforce."""
    old = _reg(_check(fixing=("P35.46",), basis_class="B3", mode="report"))
    new = _reg(_check(mode="enforce", fixing=("P35.46",), basis_class="B3"))
    v = diff_registry(old, new, ticket="P35.46")
    assert any(x.field == "basis_class" for x in v)


def test_diff_rejects_mode_weakening_without_adr() -> None:
    old = _reg(_check(mode="enforce"))
    new = _reg(_check(mode="ratchet"))
    assert [v.field for v in diff_registry(old, new, ticket="P35.1")] == ["mode"]
    assert diff_registry(old, new, ticket="P35.1", adr_ids=("ADR-2",)) == []


def test_diff_rejects_check_removal_without_adr() -> None:
    old = _reg(_check(), _check(check_id="GQ-98"))
    new = _reg(_check())
    v = diff_registry(old, new, ticket="P35.1")
    assert [x.check_id for x in v] == ["GQ-98"]
    assert diff_registry(old, new, ticket="P35.1", adr_ids=("ADR-3",)) == []


def test_diff_allows_new_check_and_report_to_ratchet() -> None:
    old = _reg(_check(mode="report", baseline=None))
    new = _reg(
        _check(mode="ratchet"),
        _check(check_id="GQ-98", mode="report", baseline=None),
    )
    assert diff_registry(old, new, ticket="P35.1") == []
