# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The egress budget check (§38.5, RISK-P0-07 / RISK-P21-09, ADR-067).

Egress pricing is the existential cost for a bulk-data project (see
:mod:`exports.distribution`). ADR-015's "revisit if egress climbs" trigger was a promise
with no instrument; this gives it a **measurement**: read the object store's monthly
egress usage (when its usage API is reachable), compare it to the documented budget in
``ops/config.toml``, and **alarm** when the ratio is breached.

No live store is required to *decide* the alarm — the alarm logic is a pure function of
(usage, budget) and is tested as such (HG-07). When usage is unavailable (no
credentials), the report is ``gate pending`` and the threshold is stated for the record.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EgressConfig:
    """The egress budget from ``ops/config.toml``."""

    monthly_budget_gb: float
    alarm_ratio: float
    provider: str
    bucket: str

    @classmethod
    def from_toml(cls, path: str | Path) -> EgressConfig:
        with open(path, "rb") as fh:
            doc = tomllib.load(fh)
        egress = doc.get("egress", {})
        store = doc.get("object_store", {})
        return cls(
            monthly_budget_gb=float(egress.get("monthly_budget_gb", 100.0)),
            alarm_ratio=float(egress.get("alarm_ratio", 0.8)),
            provider=str(store.get("provider", "")),
            bucket=str(store.get("bucket", "")),
        )


@dataclass(frozen=True)
class EgressReport:
    """The result of an egress check."""

    provider: str
    bucket: str
    budget_gb: float
    usage_gb: float | None  # None => no live usage available (gate pending)
    alarm_ratio: float
    gate_pending: bool

    @property
    def ratio(self) -> float | None:
        if self.usage_gb is None or self.budget_gb <= 0:
            return None
        return self.usage_gb / self.budget_gb

    @property
    def level(self) -> str:
        """``ok`` / ``warn`` / ``alarm`` / ``gate-pending``."""
        r = self.ratio
        if r is None:
            return "gate-pending"
        if r >= 1.0:
            return "alarm"
        if r >= self.alarm_ratio:
            return "warn"
        return "ok"

    def as_json(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "bucket": self.bucket,
            "budget_gb": self.budget_gb,
            "usage_gb": self.usage_gb,
            "alarm_ratio": self.alarm_ratio,
            "ratio": self.ratio,
            "level": self.level,
            "gate_pending": self.gate_pending,
        }


def build_report(config: EgressConfig, usage_gb: float | None) -> EgressReport:
    """Decide the egress report from the budget config and (optional) live usage.

    ``usage_gb=None`` (no store credential / usage API) → a ``gate-pending`` report that
    states the documented threshold but raises no false alarm (SIG-ENG-001 §3.1: never
    fabricate a measurement we did not take).
    """
    return EgressReport(
        provider=config.provider,
        bucket=config.bucket,
        budget_gb=config.monthly_budget_gb,
        usage_gb=usage_gb,
        alarm_ratio=config.alarm_ratio,
        gate_pending=usage_gb is None,
    )


def exit_code_for(report: EgressReport) -> int:
    """Process exit code: 0 ok/warn/gate-pending, 5 on a real budget breach (alarm)."""
    return 5 if report.level == "alarm" else 0


__all__ = [
    "EgressConfig",
    "EgressReport",
    "build_report",
    "exit_code_for",
]
