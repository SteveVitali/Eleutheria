# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The egress budget check (§38.5, RISK-P0-07 / RISK-P21-09, ADR-067).

Egress pricing is the existential cost for a bulk-data project (see
:mod:`exports.distribution`). ADR-015's "revisit if egress climbs" trigger was a promise
with no instrument; this gives it a **measurement**: read the object store's monthly
egress usage (when its usage API is reachable), compare it to the documented budget in
``ops/config.toml``, and **alarm** when the ratio is breached.

P35.5 (SIG-TRANSP-019, D-J3-4/A-3) adds the **hard dollar ceiling**: the R2 mirror
runs under a $50/month cap. When the operator reports the month's Cloudflare spend
(``--usage-usd``), the same ratio logic applies — warn at ``alarm_ratio`` of the
ceiling (default $40), alarm at 100% ($50), and the recorded alert says which
bound fired. A provider-side spend cap cannot be measured without credentials, so
the dollar report, like the GB one, never fabricates a measurement.

No live store is required to *decide* the alarm — the alarm logic is a pure function of
(usage, budget) and is tested as such (HG-07). When usage is unavailable (no
credentials), the report is ``gate pending`` and the threshold is stated for the record.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

#: SIG-TRANSP-019 / D-J3-4 (A-3): the R2 mirror's hard monthly spend ceiling.
#: Exceeding it means the kill switch — the operator disables the CDN route /
#: bucket public access (docs/build/reports/R2_MIRROR_RUNBOOK.md). A config that
#: omits the key still carries the ceiling (fail-closed, not opt-in).
DEFAULT_HARD_CEILING_USD = 50.0


@dataclass(frozen=True)
class EgressConfig:
    """The egress budget from ``ops/config.toml``."""

    monthly_budget_gb: float
    alarm_ratio: float
    provider: str
    bucket: str
    hard_ceiling_usd: float = DEFAULT_HARD_CEILING_USD

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
            hard_ceiling_usd=float(egress.get("hard_ceiling_usd", DEFAULT_HARD_CEILING_USD)),
        )


@dataclass(frozen=True)
class EgressReport:
    """The result of an egress check (GB budget + the $/month hard ceiling)."""

    provider: str
    bucket: str
    budget_gb: float
    usage_gb: float | None  # None => no live usage available (gate pending)
    alarm_ratio: float
    gate_pending: bool
    ceiling_usd: float = 0.0
    usage_usd: float | None = None  # None => no reported spend measurement

    @property
    def ratio(self) -> float | None:
        if self.usage_gb is None or self.budget_gb <= 0:
            return None
        return self.usage_gb / self.budget_gb

    @property
    def usd_ratio(self) -> float | None:
        if self.usage_usd is None or self.ceiling_usd <= 0:
            return None
        return self.usage_usd / self.ceiling_usd

    @staticmethod
    def _band(ratio: float, alarm_ratio: float) -> str:
        if ratio >= 1.0:
            return "alarm"
        if ratio >= alarm_ratio:
            return "warn"
        return "ok"

    @property
    def level(self) -> str:
        """``ok`` / ``warn`` / ``alarm`` / ``gate-pending`` — the worse bound."""
        bands = [
            band
            for band in (
                self._band(self.ratio, self.alarm_ratio) if self.ratio is not None else None,
                self._band(self.usd_ratio, self.alarm_ratio)
                if self.usd_ratio is not None
                else None,
            )
            if band is not None
        ]
        if not bands:
            return "gate-pending"
        if "alarm" in bands:
            return "alarm"
        if "warn" in bands:
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
            "ceiling_usd": self.ceiling_usd,
            "usage_usd": self.usage_usd,
            "usd_ratio": self.usd_ratio,
            "level": self.level,
            "gate_pending": self.gate_pending,
        }


def build_report(
    config: EgressConfig,
    usage_gb: float | None,
    usage_usd: float | None = None,
) -> EgressReport:
    """Decide the egress report from the budget config and (optional) live usage.

    ``usage_gb=None`` / ``usage_usd=None`` (no store credential / no operator-reported
    spend) → a ``gate-pending`` report that states the documented thresholds but raises
    no false alarm (SIG-ENG-001 §3.1: never fabricate a measurement we did not take).
    """
    return EgressReport(
        provider=config.provider,
        bucket=config.bucket,
        budget_gb=config.monthly_budget_gb,
        usage_gb=usage_gb,
        alarm_ratio=config.alarm_ratio,
        gate_pending=usage_gb is None and usage_usd is None,
        ceiling_usd=config.hard_ceiling_usd,
        usage_usd=usage_usd,
    )


def exit_code_for(report: EgressReport) -> int:
    """Process exit code: 0 ok/warn/gate-pending, 5 on a real budget breach (alarm)."""
    return 5 if report.level == "alarm" else 0


__all__ = [
    "DEFAULT_HARD_CEILING_USD",
    "EgressConfig",
    "EgressReport",
    "build_report",
    "exit_code_for",
]
