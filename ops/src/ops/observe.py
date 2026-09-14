# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Metrics, bounded logs, uptime/error budgets, and the readout (OBS.1 / GL-OBS-01, ADR-077).

Within the zero-cost posture (SIG-STORE-003) there is no hosted metrics stack:
**metrics** are a bounded JSONL probe log (``sig-ops probe`` appends one row per
service check: ok / latency / timestamp), **logs** are those JSONL files held to a
**retention policy** (age + byte caps — a file, not a paid log service), **uptime +
error budgets** are a pure function over the probe log inside a rolling window, and
the **dashboard** is a markdown readout rendered from the same records.

The health probes here (``http_ok`` / ``pg_ready``) are the single implementation
the CLI's ``status``/``up`` paths reuse — one probe definition, no drift between
what the operator sees and what the monitor records.
"""

from __future__ import annotations

import json
import time
import tomllib
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from .degraded import Runner

from .alerts import utcnow


def http_ok(url: str, *, timeout: float = 3.0) -> bool:
    """True when ``url`` answers with any non-5xx status within ``timeout``."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 - local staging
            return 200 <= resp.status < 500
    except (urllib.error.URLError, ConnectionError, OSError, ValueError):
        return False


def pg_ready(dsn: str) -> bool:
    """True when the claim-spine PostgreSQL answers a trivial query."""
    try:
        import psycopg

        with psycopg.connect(dsn, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:  # noqa: BLE001 - any failure means "not ready"
        return False


#: The services a probe sweep covers (name → the endpoint reader the CLI passes).
STACK_SERVICES = ("pg", "api", "curation", "static")


@dataclass(frozen=True)
class ProbeResult:
    """One row of the metrics log: a single service health measurement."""

    service: str
    ok: bool
    latency_ms: float
    ts: str
    detail: str = ""

    def as_json(self) -> dict[str, object]:
        return {
            "service": self.service,
            "ok": self.ok,
            "latency_ms": round(self.latency_ms, 1),
            "ts": self.ts,
            "detail": self.detail,
        }


def _timed(check: Callable[[], bool]) -> tuple[bool, float]:
    start = time.monotonic()
    ok = check()
    return ok, (time.monotonic() - start) * 1000.0


def probe_stack(
    *,
    dsn: str,
    api_url: str,
    static_url: str,
    curation_url: str,
    now: str | None = None,
    check_http: Callable[..., bool] | None = None,
    check_pg: Callable[[str], bool] | None = None,
) -> list[ProbeResult]:
    """Probe the live stack (PG spine, read API, curation, static) once.

    ``check_http``/``check_pg`` are injectable so the sweep is deterministic in
    tests (the default is the real network/PG probe). Returns one
    :class:`ProbeResult` per service, in ``STACK_SERVICES`` order.
    """
    check_http = check_http or http_ok
    check_pg = check_pg or pg_ready
    ts = now or utcnow()
    results: list[ProbeResult] = []
    for service, check in (
        ("pg", lambda: check_pg(dsn)),
        ("api", lambda: check_http(api_url + "/")),
        ("curation", lambda: check_http(curation_url + "/")),
        ("static", lambda: check_http(static_url)),
    ):
        ok, latency = _timed(check)
        results.append(
            ProbeResult(
                service=service,
                ok=ok,
                latency_ms=latency,
                ts=ts,
                detail="" if ok else "unreachable",
            )
        )
    return results


class ProbeLog:
    """The bounded metrics log: one JSONL row per probe (append-only between prunes)."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, result: ProbeResult) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(result.as_json(), sort_keys=True) + "\n")
        return self.path

    def read(self) -> list[ProbeResult]:
        if not self.path.exists():
            return []
        rows: list[ProbeResult] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            rows.append(
                ProbeResult(
                    service=str(raw["service"]),
                    ok=bool(raw["ok"]),
                    latency_ms=float(raw["latency_ms"]),
                    ts=str(raw["ts"]),
                    detail=str(raw.get("detail", "")),
                )
            )
        return rows


@dataclass(frozen=True)
class RetentionPolicy:
    """Bounded log retention within the zero-cost posture: age + byte caps.

    Both bounds apply: rows older than ``max_age_days`` drop, and the file is then
    truncated (oldest-first) to ``max_bytes`` so the log can never grow without
    bound — bounded retention on a *file* instead of a paid log service.
    """

    max_age_days: int = 30
    max_bytes: int = 1_048_576


def _parse_ts(ts: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def prune_jsonl(path: str | Path, policy: RetentionPolicy, *, now: datetime | None = None) -> int:
    """Apply ``policy`` to a JSONL log in place; return the number of rows dropped.

    Keeps the newest rows within the age window and the byte cap (oldest rows drop
    first). A row whose ``ts`` does not parse is kept only inside the byte cap —
    it cannot be proven in-window.
    """
    path = Path(path)
    if not path.exists():
        return 0
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=policy.max_age_days)
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    kept: list[str] = []
    dropped = 0
    for line in lines:
        try:
            raw = json.loads(line)
            ts = _parse_ts(str(raw.get("ts", ""))) if isinstance(raw, dict) else None
        except ValueError:
            ts = None
        if ts is None or ts >= cutoff:
            kept.append(line)
        else:
            dropped += 1
    # Byte cap: drop oldest-first until the file fits.
    while kept and sum(len(ln) + 1 for ln in kept) > policy.max_bytes:
        kept.pop(0)
        dropped += 1
    if dropped:
        path.write_text("".join(ln + "\n" for ln in kept), encoding="utf-8")
    return dropped


@dataclass(frozen=True)
class ObservabilityConfig:
    """The ``[observability]`` block of ``ops/config.toml``."""

    uptime_target_pct: float = 99.0
    window_days: int = 30
    retention_days: int = 30
    probe_log_max_bytes: int = 1_048_576

    @classmethod
    def from_toml(cls, path: str | Path) -> ObservabilityConfig:
        with open(path, "rb") as fh:
            doc = tomllib.load(fh)
        obs = doc.get("observability", {})
        return cls(
            uptime_target_pct=float(obs.get("uptime_target_pct", 99.0)),
            window_days=int(obs.get("window_days", 30)),
            retention_days=int(obs.get("retention_days", 30)),
            probe_log_max_bytes=int(obs.get("probe_log_max_bytes", 1_048_576)),
        )

    def retention(self) -> RetentionPolicy:
        return RetentionPolicy(max_age_days=self.retention_days, max_bytes=self.probe_log_max_bytes)


@dataclass(frozen=True)
class ServiceBudget:
    """Uptime + error-budget readout for one service over the rolling window."""

    service: str
    probes: int
    ok: int
    uptime_pct: float | None  # None => no probes in the window
    budget_consumed_pct: float | None  # 0..100+ of the error budget burned
    status: str  # "within-budget" | "exhausted" | "no-data"

    def as_json(self) -> dict[str, object]:
        return {
            "service": self.service,
            "probes": self.probes,
            "ok": self.ok,
            "uptime_pct": self.uptime_pct,
            "budget_consumed_pct": self.budget_consumed_pct,
            "status": self.status,
        }


def compute_uptime(
    records: Sequence[ProbeResult],
    *,
    window_days: int,
    target_pct: float,
    now: datetime | None = None,
) -> list[ServiceBudget]:
    """Uptime % and error-budget burn per service over the rolling window (pure).

    Error budget = ``100 - target_pct`` percentage points of allowed downtime in the
    window; ``budget_consumed_pct`` is how much of it the observed failures burned.
    A service with no probes in the window reports ``no-data`` — never a fabricated
    100% (§3.1: assert only what was measured).
    """
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=window_days)
    allowed = 100.0 - target_pct
    budgets: list[ServiceBudget] = []
    for service in STACK_SERVICES:
        window = [r for r in records if r.service == service and (_parse_ts(r.ts) or now) >= cutoff]
        if not window:
            budgets.append(ServiceBudget(service, 0, 0, None, None, "no-data"))
            continue
        ok = sum(1 for r in window if r.ok)
        uptime = ok / len(window) * 100.0
        consumed = None if allowed <= 0 else (100.0 - uptime) / allowed * 100.0
        status = "within-budget" if uptime >= target_pct else "exhausted"
        budgets.append(ServiceBudget(service, len(window), ok, uptime, consumed, status))
    return budgets


@dataclass(frozen=True)
class KeepaliveResult:
    """The keepalive verification outcome (SIG-GOV-021, RISK-P0-12)."""

    ok: bool
    checks: dict[str, str] = field(default_factory=dict)

    def as_json(self) -> dict[str, object]:
        return {"ok": self.ok, "checks": self.checks}


def verify_keepalive(
    *,
    repo_root: Path,
    data_source: str = "fixtures",
    export_dir: str | None = None,
    runner: Runner | None = None,
) -> KeepaliveResult:
    """Verify the dormant-scheduler keepalive end to end.

    Two checks, each recorded in the result: (1) the keepalive *machinery* is intact —
    ``.github/workflows/keepalive.yml`` exists, still carries a ``cron:`` schedule and
    still runs ``sig-ops degraded``; (2) the keepalive *function* works — the degraded
    static site rebuilds from committed bytes (``degraded.build_static_site``, runner
    injectable for tests). Any failure is returned, never raised past the caller —
    the caller turns it into a recorded alert.
    """
    import subprocess

    from .degraded import DegradedBuildError, build_static_site

    checks: dict[str, str] = {}
    workflow = repo_root / ".github" / "workflows" / "keepalive.yml"
    if not workflow.exists():
        checks["workflow"] = "FAIL: .github/workflows/keepalive.yml is missing"
    else:
        text = workflow.read_text(encoding="utf-8")
        missing = [needle for needle in ("cron:", "sig-ops degraded") if needle not in text]
        checks["workflow"] = (
            "ok" if not missing else f"FAIL: keepalive.yml no longer carries {missing}"
        )
    try:
        dist = build_static_site(
            repo_root=repo_root,
            data_source=data_source,
            export_dir=export_dir,
            runner=runner if runner is not None else subprocess.run,
        )
        checks["rebuild"] = f"ok ({dist})"
    except DegradedBuildError as exc:
        checks["rebuild"] = f"FAIL: {exc}"
    return KeepaliveResult(ok=all(v.startswith("ok") for v in checks.values()), checks=checks)


def render_dashboard(
    *,
    budgets: Sequence[ServiceBudget],
    latest: dict[str, ProbeResult],
    alerts: Sequence[dict[str, object]],
    egress: dict[str, object] | None = None,
    keepalive: KeepaliveResult | None = None,
    window_days: int = 30,
    target_pct: float = 99.0,
    generated_at: str | None = None,
) -> str:
    """Render the observability readout (markdown) from the recorded state.

    This is the dashboard: a deterministic function of the probe log, the alert
    ledger, and the last egress/keepalive outcomes — no client JS, no hosted
    dashboard service (zero-cost).
    """
    generated_at = generated_at or utcnow()
    lines: list[str] = [
        "# SIG observability readout (OBS.1 / GL-OBS-01)",
        "",
        f"Generated: {generated_at} · window: {window_days}d · uptime target: {target_pct}%",
        "",
        "## Service health (latest probe)",
        "",
        "| service | state | latency_ms | at |",
        "|---|---|---|---|",
    ]
    for service in STACK_SERVICES:
        probe = latest.get(service)
        if probe is None:
            lines.append(f"| {service} | no-data | — | — |")
        else:
            state = "healthy" if probe.ok else "DOWN"
            lines.append(f"| {service} | {state} | {probe.latency_ms:.0f} | {probe.ts} |")
    lines += [
        "",
        f"## Uptime + error budgets (last {window_days}d; budget = {100.0 - target_pct}% downtime)",
        "",
        "| service | probes | uptime % | error budget consumed | status |",
        "|---|---|---|---|---|",
    ]
    for budget in budgets:
        uptime = "—" if budget.uptime_pct is None else f"{budget.uptime_pct:.2f}"
        consumed = (
            "—" if budget.budget_consumed_pct is None else f"{budget.budget_consumed_pct:.1f}%"
        )
        lines.append(
            f"| {budget.service} | {budget.probes} | {uptime} | {consumed} | {budget.status} |"
        )
    lines += ["", "## Egress budget (§38.5, RISK-P21-09)", ""]
    if egress is None:
        lines.append("- no egress report recorded in this window")
    else:
        lines.append(
            "- level: **{level}** — usage {usage} of {budget} GB (alarm ratio {ratio})".format(
                level=egress.get("level"),
                usage=(
                    f"{egress.get('usage_gb')} GB"
                    if egress.get("usage_gb") is not None
                    else "unmeasured (gate pending: HG-07)"
                ),
                budget=egress.get("budget_gb"),
                ratio=egress.get("alarm_ratio"),
            )
        )
    lines += ["", "## Keepalive (SIG-GOV-021)", ""]
    if keepalive is None:
        lines.append("- keepalive not verified this run")
    else:
        state = "OK" if keepalive.ok else "FAIL"
        lines.append(f"- verification: **{state}**")
        for name, outcome in keepalive.checks.items():
            lines.append(f"  - {name}: {outcome}")
    lines += ["", f"## Alerts recorded ({len(alerts)} in the ledger)", ""]
    if not alerts:
        lines.append("- none")
    else:
        lines += ["| ts | severity | kind | message |", "|---|---|---|---|"]
        for alert in alerts:
            lines.append(
                "| {ts} | {sev} | {kind} | {msg} |".format(
                    ts=alert.get("ts"),
                    sev=alert.get("severity"),
                    kind=alert.get("kind"),
                    msg=str(alert.get("message", "")).replace("|", "\\|"),
                )
            )
    lines.append("")
    return "\n".join(lines)


__all__ = [
    "STACK_SERVICES",
    "KeepaliveResult",
    "ObservabilityConfig",
    "ProbeLog",
    "ProbeResult",
    "RetentionPolicy",
    "ServiceBudget",
    "compute_uptime",
    "http_ok",
    "pg_ready",
    "probe_stack",
    "prune_jsonl",
    "render_dashboard",
    "verify_keepalive",
]
