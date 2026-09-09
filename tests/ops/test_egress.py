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
