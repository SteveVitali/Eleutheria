# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The egress budget check (§38.5, RISK-P21-09, ADR-067): the alarm is a pure function."""

from __future__ import annotations

from pathlib import Path

from ops import egress as E

_CONFIG = Path(__file__).resolve().parents[2] / "ops" / "config.toml"


def _cfg(budget: float = 100.0, ratio: float = 0.8) -> E.EgressConfig:
    return E.EgressConfig(
        monthly_budget_gb=budget, alarm_ratio=ratio, provider="cloudflare-r2", bucket="sig-bulk"
    )


def test_config_loads_from_the_committed_ops_config() -> None:
    cfg = E.EgressConfig.from_toml(_CONFIG)
    assert cfg.provider == "cloudflare-r2"  # ADR-067 primary
    assert cfg.monthly_budget_gb > 0


def test_no_live_usage_is_gate_pending_not_an_alarm() -> None:
    # HG-07 / §3.1: with no store credential there is no measurement — never a false alarm.
    report = E.build_report(_cfg(), usage_gb=None)
    assert report.gate_pending is True
    assert report.level == "gate-pending"
    assert E.exit_code_for(report) == 0


def test_usage_below_budget_is_ok() -> None:
    report = E.build_report(_cfg(budget=100.0, ratio=0.8), usage_gb=50.0)
    assert report.level == "ok"
    assert E.exit_code_for(report) == 0


def test_usage_at_warn_ratio_warns_but_does_not_alarm() -> None:
    report = E.build_report(_cfg(budget=100.0, ratio=0.8), usage_gb=85.0)
    assert report.level == "warn"
    assert E.exit_code_for(report) == 0


def test_usage_over_budget_alarms_nonzero() -> None:
    # RISK-P21-09: a real budget breach exits non-zero so a monitor catches it.
    report = E.build_report(_cfg(budget=100.0), usage_gb=120.0)
    assert report.level == "alarm"
    assert E.exit_code_for(report) == 5


# ── P35.5 / SIG-TRANSP-019: the $50/month hard ceiling on the mirror ──


def test_the_committed_config_carries_the_hard_dollar_ceiling() -> None:
    cfg = E.EgressConfig.from_toml(_CONFIG)
    assert cfg.hard_ceiling_usd == E.DEFAULT_HARD_CEILING_USD


def test_reported_spend_below_the_warn_ratio_is_ok() -> None:
    # $0 is the R2 free-tier expectation — and stays ok.
    report = E.build_report(_cfg(), usage_gb=None, usage_usd=0.0)
    assert report.gate_pending is False  # a reported measurement is not pending
    assert report.level == "ok"
    assert E.exit_code_for(report) == 0


def test_reported_spend_at_warn_ratio_warns_without_alarm() -> None:
    # 80% of $50 = $40 → warn (the operator sees it before the kill switch).
    report = E.build_report(_cfg(), usage_gb=None, usage_usd=41.0)
    assert report.level == "warn"
    assert E.exit_code_for(report) == 0


def test_reported_spend_at_the_ceiling_alarms_nonzero() -> None:
    # $50+ = the hard ceiling: alarm fires the kill-switch path (exit 5).
    report = E.build_report(_cfg(), usage_gb=None, usage_usd=50.0)
    assert report.level == "alarm"
    assert E.exit_code_for(report) == 5


def test_a_dollar_alarm_wins_over_an_ok_gb_report() -> None:
    # The worse bound decides — GB fine but the spend ceiling breached.
    report = E.build_report(_cfg(), usage_gb=10.0, usage_usd=55.0)
    assert report.level == "alarm"
    assert E.exit_code_for(report) == 5
