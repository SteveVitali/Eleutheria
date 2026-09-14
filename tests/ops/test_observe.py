# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Metrics log, retention, uptime/error budgets, and the readout (OBS.1 / GL-OBS-01)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ops import cli
from ops import observe as O

_CONFIG = Path(__file__).resolve().parents[2] / "ops" / "config.toml"
_NOW = datetime(2026, 9, 13, 12, 0, 0, tzinfo=UTC)


def _probe(service: str, ok: bool, days_ago: float = 0.0, latency: float = 12.0) -> O.ProbeResult:
    ts = (_NOW - timedelta(days=days_ago)).isoformat(timespec="seconds")
    return O.ProbeResult(service=service, ok=ok, latency_ms=latency, ts=ts)


@pytest.fixture()
def state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    probes = tmp_path / "probes.jsonl"
    alerts = tmp_path / "alerts.jsonl"
    monkeypatch.setenv("SIG_PROBE_LOG", str(probes))
    monkeypatch.setenv("SIG_ALERT_LOG", str(alerts))
    return probes, alerts


# --- metrics: the bounded probe log --------------------------------------------


def test_probe_stack_covers_every_stack_service() -> None:
    results = O.probe_stack(
        dsn="postgresql://x",
        api_url="http://a",
        static_url="http://s",
        curation_url="http://c",
        check_http=lambda url, **kw: True,
        check_pg=lambda dsn: False,
    )
    assert [r.service for r in results] == ["pg", "api", "curation", "static"]
    assert results[0].ok is False and results[1].ok is True
    assert results[0].detail == "unreachable"


def test_probe_log_appends_and_reads_back(tmp_path: Path) -> None:
    log = O.ProbeLog(tmp_path / "probes.jsonl")
    log.append(_probe("api", True))
    log.append(_probe("api", False))
    rows = log.read()
    assert [r.ok for r in rows] == [True, False]
    assert rows[0].service == "api"


# --- bounded log retention (zero-cost posture: a file, not a log service) ------


def test_retention_prunes_rows_older_than_the_window(tmp_path: Path) -> None:
    log = O.ProbeLog(tmp_path / "p.jsonl")
    log.append(_probe("api", True, days_ago=45))  # outside a 30d window
    log.append(_probe("api", False, days_ago=1))
    dropped = O.prune_jsonl(log.path, O.RetentionPolicy(max_age_days=30), now=_NOW)
    assert dropped == 1
    assert [r.ok for r in log.read()] == [False]


def test_retention_enforces_the_byte_cap_oldest_first(tmp_path: Path) -> None:
    log = O.ProbeLog(tmp_path / "p.jsonl")
    for _ in range(10):
        log.append(_probe("api", True, latency=1234.5))
    size = len(log.read())
    cap = sum(len(json.dumps(r.as_json())) + 1 for r in log.read()[-3:])
    dropped = O.prune_jsonl(log.path, O.RetentionPolicy(max_age_days=365, max_bytes=cap), now=_NOW)
    assert dropped == size - 3
    assert len(log.read()) == 3  # newest rows kept


def test_prune_on_a_missing_log_is_a_noop(tmp_path: Path) -> None:
    assert O.prune_jsonl(tmp_path / "none.jsonl", O.RetentionPolicy()) == 0


# --- uptime + error budgets (a pure function over the window) -------------------


def test_compute_uptime_within_budget() -> None:
    records = [_probe("api", True) for _ in range(99)] + [_probe("api", False)]
    budgets = {
        b.service: b for b in O.compute_uptime(records, window_days=30, target_pct=99.0, now=_NOW)
    }
    assert budgets["api"].uptime_pct == 99.0
    assert budgets["api"].status == "within-budget"
    assert budgets["api"].budget_consumed_pct == pytest.approx(100.0)


def test_compute_uptime_exhausts_the_error_budget() -> None:
    records = [_probe("api", True) for _ in range(9)] + [_probe("api", False)]
    budgets = {
        b.service: b for b in O.compute_uptime(records, window_days=30, target_pct=99.0, now=_NOW)
    }
    assert budgets["api"].status == "exhausted"
    assert budgets["api"].budget_consumed_pct > 100.0


def test_compute_uptime_ignores_rows_outside_the_window_and_reports_no_data() -> None:
    records = [_probe("api", False, days_ago=90)]
    budgets = {
        b.service: b for b in O.compute_uptime(records, window_days=30, target_pct=99.0, now=_NOW)
    }
    # outside the window => not counted; no in-window data => "no-data", never a
    # fabricated 100% (§3.1).
    assert budgets["api"].status == "no-data"
    assert budgets["pg"].status == "no-data"


def test_observability_config_loads_from_the_committed_ops_config() -> None:
    cfg = O.ObservabilityConfig.from_toml(_CONFIG)
    assert cfg.uptime_target_pct == 99.0
    assert cfg.retention().max_age_days == 30
    assert cfg.retention().max_bytes > 0


# --- the dashboard/readout -------------------------------------------------------


def test_render_dashboard_covers_health_budgets_egress_keepalive_alerts() -> None:
    records = [_probe(s, True) for s in O.STACK_SERVICES]
    budgets = O.compute_uptime(records, window_days=30, target_pct=99.0, now=_NOW)
    latest = {r.service: r for r in records}
    text = O.render_dashboard(
        budgets=budgets,
        latest=latest,
        alerts=[{"ts": "t", "severity": "alarm", "kind": "egress-budget", "message": "breach"}],
        egress={"level": "alarm", "usage_gb": 120.0, "budget_gb": 100.0, "alarm_ratio": 0.8},
        keepalive=O.KeepaliveResult(ok=True, checks={"workflow": "ok"}),
        generated_at="2026-09-13T00:00:00+00:00",
    )
    assert "## Service health" in text and "| api | healthy |" in text
    assert "error budget consumed" in text and "within-budget" in text
    assert "level: **alarm**" in text
    assert "verification: **OK**" in text
    assert "egress-budget" in text and "breach" in text


def test_render_dashboard_is_honest_when_nothing_is_recorded() -> None:
    text = O.render_dashboard(
        budgets=O.compute_uptime([], window_days=30, target_pct=99.0, now=_NOW),
        latest={},
        alerts=[],
        generated_at="2026-09-13T00:00:00+00:00",
    )
    assert "no-data" in text and "- none" in text
    assert "keepalive not verified" in text


# --- CLI wiring -------------------------------------------------------------------


def test_cli_probe_records_metrics_and_alerts_on_down_services(
    state: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    probes, alerts = state
    now = O.utcnow()
    monkeypatch.setattr(
        O,
        "probe_stack",
        lambda **kw: [
            O.ProbeResult("pg", True, 1.0, now),
            O.ProbeResult("api", False, 2.0, now, "unreachable"),
            O.ProbeResult("curation", True, 1.0, now),
            O.ProbeResult("static", True, 1.0, now),
        ],
    )
    rc = cli.main(["probe", "--alert"])
    assert rc == 6
    rows = [json.loads(ln) for ln in probes.read_text().splitlines()]
    assert len(rows) == 4  # every service measured
    fired = [json.loads(ln) for ln in alerts.read_text().splitlines()]
    assert [a["kind"] for a in fired] == ["probe"]
    assert "api" in fired[0]["message"]


def test_cli_probe_healthy_stack_records_metrics_without_alerts(
    state: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    probes, alerts = state
    now = O.utcnow()
    monkeypatch.setattr(
        O,
        "probe_stack",
        lambda **kw: [O.ProbeResult(s, True, 1.0, now) for s in O.STACK_SERVICES],
    )
    assert cli.main(["probe", "--alert"]) == 0
    assert len(probes.read_text().splitlines()) == len(O.STACK_SERVICES)
    assert not alerts.exists()


def test_cli_dashboard_writes_the_readout_file(state: tuple[Path, Path], tmp_path: Path) -> None:
    out = tmp_path / "dashboard.md"
    assert cli.main(["dashboard", "--out", str(out)]) == 0
    text = out.read_text()
    assert text.startswith("# SIG observability readout")
    assert "## Uptime + error budgets" in text and "## Egress budget" in text


def test_cli_keepalive_check_passes_when_the_keepalive_verifies(
    state: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, alerts = state
    monkeypatch.setattr(
        O,
        "verify_keepalive",
        lambda **kw: O.KeepaliveResult(ok=True, checks={"workflow": "ok", "rebuild": "ok"}),
    )
    assert cli.main(["keepalive-check"]) == 0
    assert not alerts.exists()
