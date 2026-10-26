# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""alerting — the P35.2 alerting-as-code machinery (SIG-OPS-006/007).

P34.4 codified the Track-0.5 alert set into ``ops/monitoring/*.json`` and wired
the apply path for its five named mutations. This module carries what this row
adds on top of that substrate (G1 §3.5, the design table verbatim):

* **escalation hygiene** — :func:`renotify_due`, the once-daily re-notify rule
  for a condition red more than 24 h. Cloud Monitoring expresses the same rule
  as ``alertStrategy.notificationRateLimit {period: "86400s"}``, which the
  committed policy defs now carry on every policy; this function is the
  executable statement of the rule the monthly drill and the roll packet cite.
* **uptime-check apply render** — :func:`uptime_update_args` /
  :func:`uptime_create_args` turn a committed ``uptime-check.*.json`` def into
  the ``gcloud monitoring uptime`` flag set the roll applies (create or
  update by id; the channel itself is never re-created — P34.4's mechanism).
* **SLO readout** — :func:`slo_report` + :func:`render_slo_readout` compute the
  99.5 % monthly availability objectives (SIG-OPS-007) over stored probe sweep
  rows and render the monthly error-budget readout into
  ``docs/build/reports/``. A month with no rows for a declared target reports
  ``no-data`` — never a fabricated 100 % (SIG-ENG-042).
* **measured-nothing gate** — :func:`measured_gate` is the SIG-ENG-042 rule
  ``observability.yml`` takes: a scheduled check that measured nothing fails.
  The workflow writes ``offered``/``evaluated`` counts per leg; the gate fails
  when a non-empty candidate set evaluated zero — or when nothing was offered
  at all.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

#: The re-notification period: a condition red more than 24 h re-notifies once
#: daily (SIG-OPS-006 verbatim; ``notificationRateLimit.period`` = "86400s").
RENOTIFY_PERIOD = timedelta(days=1)

#: The monthly availability objective (SIG-OPS-007): 99.5 % over the calendar
#: month, measured by external checks at intervals of 5 minutes or less.
SLO_OBJECTIVE_PCT = 99.5

#: Declared SLO targets — objective name → the probe-target names whose rows
#: measure it. ``sig-web-root``/``sig-api-health`` are the ``[[probes.targets]]``
#: names in ops/cadence.toml; the Monitoring uptime checks on the same surfaces
#: contribute their own rows under their check ids when the readout runs
#: against a Monitoring export (the same surfaces, the same verdict math).
SLO_TARGETS: dict[str, tuple[str, ...]] = {
    "site-root": ("sig-web-root",),
    "api-health": ("sig-api-health",),
}

#: REST region enum → ``gcloud monitoring uptime --set-regions`` value.
_REGION_CLI = {
    "USA_IOWA": "usa-iowa",
    "USA_OREGON": "usa-oregon",
    "EUROPE": "europe",
    "SOUTH_AMERICA": "south-america",
    "ASIA_PACIFIC": "asia-pacific",
}

#: REST contentMatcher ``matcher`` enum → ``--matcher-type`` value.
_MATCHER_CLI = {
    "CONTAINS_STRING": "contains-string",
    "NOT_CONTAINS_STRING": "not-contains-string",
    "MATCHES_REGEX": "matches-regex",
    "NOT_MATCHES_REGEX": "not-matches-regex",
    "MATCHES_JSON_PATH": "matches-json-path",
    "NOT_MATCHES_JSON_PATH": "not-matches-json-path",
}


def _parse_ts(ts: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


# --- escalation hygiene -------------------------------------------------------


def renotify_due(
    opened_at: datetime,
    last_notified_at: datetime | None,
    now: datetime,
    *,
    period: timedelta = RENOTIFY_PERIOD,
) -> bool:
    """The once-daily re-notify rule (SIG-OPS-006, G1 §3.5 hygiene row).

    A condition red for more than 24 h re-notifies **once daily** — never
    every sweep. ``opened_at`` is when the condition first went red;
    ``last_notified_at`` is the last notification (``None`` = never). The rule:

    * younger than ``period`` → no re-notify (the opening notification stands),
    * never notified at all → due,
    * otherwise due only when the last notification is ``period`` or older.
    """
    if (now - opened_at) < period:
        return False
    if last_notified_at is None:
        return True
    return (now - last_notified_at) >= period


# --- uptime-check apply render -------------------------------------------------


class DefRenderError(ValueError):
    """A committed def cannot render to gcloud flags (missing required field)."""


def _http_check(body: Mapping[str, Any]) -> Mapping[str, Any]:
    hc = body.get("httpCheck")
    if not isinstance(hc, dict):
        raise DefRenderError("uptime def has no httpCheck object")
    return hc


def _host(body: Mapping[str, Any]) -> str:
    res = body.get("monitoredResource") or {}
    return str((res.get("labels") or {}).get("host", ""))


def _common_args(body: Mapping[str, Any], project: str) -> list[str]:
    """The flag set shared by update and create (times, matcher, http shape)."""
    hc = _http_check(body)
    args: list[str] = []
    args += ["--display-name", str(body["displayName"])]
    args += ["--period", str(int(str(body["period"]).rstrip("s")))]
    args += ["--timeout", str(int(str(body["timeout"]).rstrip("s")))]
    args += ["--path", str(hc.get("path", "/"))]
    args += ["--port", str(hc.get("port", 443 if hc.get("useSsl") else 80))]
    args += ["--request-method", str(hc.get("requestMethod", "GET")).lower()]
    if hc.get("validateSsl"):
        args += ["--validate-ssl", "true"]
    regions = [
        _REGION_CLI.get(str(r).upper(), str(r).lower()) for r in body.get("selectedRegions", [])
    ]
    if regions:
        args += ["--set-regions", ",".join(regions)]
    matchers = body.get("contentMatchers") or hc.get("contentMatchers") or []
    if matchers:
        m = matchers[0]
        matcher = _MATCHER_CLI.get(str(m.get("matcher", "CONTAINS_STRING")).upper())
        if matcher is None:
            raise DefRenderError(f"unknown matcher enum {m.get('matcher')!r}")
        args += ["--matcher-type", matcher, "--matcher-content", str(m["content"])]
    return args


def uptime_update_args(body: Mapping[str, Any], check_id: str, project: str) -> list[str]:
    """``gcloud monitoring uptime update <check_id> …`` argv from a committed def.

    The def is the REST shape minus volatile fields (``ops/monitoring/``);
    the check id resolves at apply time from the live config matched on
    ``displayName``. Regions arrive via ``--set-regions`` (a reconcile, not an
    add) and the content matcher via ``--matcher-type``/``--matcher-content``.
    """
    return ["update", check_id, *(_common_args(body, project))]


def uptime_create_args(body: Mapping[str, Any], project: str) -> list[str]:
    """``gcloud monitoring uptime create <display> --resource-type=uptime-url …``."""
    host = _host(body)
    if not host:
        raise DefRenderError("uptime def has no monitoredResource.labels.host")
    hc = _http_check(body)
    args = ["create", str(body["displayName"])]
    args += ["--resource-type", "uptime-url"]
    args += ["--resource-labels", f"host={host},project_id={project}"]
    args += ["--protocol", "https" if hc.get("useSsl") else "http"]
    args += _common_args(body, project)
    return args


# --- the measured-nothing gate (SIG-ENG-042) -----------------------------------

_COUNT_LINE = re.compile(r"^([A-Za-z0-9_-]+)=(\d+)$")


def parse_measured_counts(text: str) -> dict[str, int]:
    """Parse the ``key=N`` lines a workflow leg appends to its counts file.

    Lines that do not parse are ignored — a malformed count line is reported by
    the caller as an offered/evaluated of what did parse, never by guessing.
    """
    counts: dict[str, int] = {}
    for line in text.splitlines():
        m = _COUNT_LINE.match(line.strip())
        if m:
            counts[m.group(1)] = int(m.group(2))
    return counts


def measured_gate(counts: Mapping[str, int]) -> tuple[bool, str]:
    """SIG-ENG-042: a scheduled check that measured nothing fails.

    ``counts`` carries ``*_offered``/``*_evaluated`` legs (plus any total). The
    gate fails when the evaluated total is zero — a non-empty candidate set
    that evaluated nothing, or a job that offered nothing at all; both are
    vacuous-success shapes. Returns ``(ok, report)`` where the report always
    names offered and evaluated counts (the rule's own accounting sentence).
    """
    offered = sum(v for k, v in counts.items() if k.endswith("_offered"))
    evaluated = sum(v for k, v in counts.items() if k.endswith("_evaluated"))
    offered += counts.get("offered", 0)
    evaluated += counts.get("evaluated", 0)
    report = f"measured: offered={offered} evaluated={evaluated}"
    if evaluated == 0:
        return False, (
            f"{report} — FAIL: a scheduled check that measured nothing must not "
            "report success (SIG-ENG-042)"
        )
    return True, f"{report} — OK"


# --- the monthly SLO readout (SIG-OPS-007) --------------------------------------


@dataclass(frozen=True)
class SloTargetResult:
    """One declared objective's monthly outcome."""

    name: str
    probes: int
    ok: int
    uptime_pct: float | None  # None => no rows in the month (no-data)
    budget_consumed_pct: float | None
    status: str  # "met" | "missed" | "no-data"

    def as_json(self) -> dict[str, object]:
        return {
            "name": self.name,
            "probes": self.probes,
            "ok": self.ok,
            "uptime_pct": None if self.uptime_pct is None else round(self.uptime_pct, 3),
            "budget_consumed_pct": (
                None if self.budget_consumed_pct is None else round(self.budget_consumed_pct, 1)
            ),
            "status": self.status,
        }


@dataclass(frozen=True)
class SloReport:
    """The monthly readout: per-target outcomes + the gate verdict."""

    month: str  # "YYYY-MM"
    objective_pct: float
    results: tuple[SloTargetResult, ...]
    offered: int
    evaluated: int
    gate_ok: bool  # SIG-ENG-042: False when nothing was evaluated
    notes: tuple[str, ...] = field(default_factory=tuple)

    def as_json(self) -> dict[str, object]:
        return {
            "version": "sig.slo-readout/1",
            "month": self.month,
            "objective_pct": self.objective_pct,
            "results": [r.as_json() for r in self.results],
            "offered": self.offered,
            "evaluated": self.evaluated,
            "gate_ok": self.gate_ok,
            "notes": list(self.notes),
        }


def month_bounds(month: str) -> tuple[datetime, datetime]:
    """``YYYY-MM`` → [first instant, first instant of next month) UTC."""
    start = datetime.strptime(month + "-01", "%Y-%m-%d").replace(tzinfo=UTC)
    year, mon = start.year, start.month
    end = start.replace(year=year + 1, month=1) if mon == 12 else start.replace(month=mon + 1)
    return start, end


def slo_report(
    rows: Sequence[Mapping[str, Any]],
    *,
    month: str,
    objective_pct: float = SLO_OBJECTIVE_PCT,
    targets: Mapping[str, Sequence[str]] | None = None,
) -> SloReport:
    """Compute the monthly 99.5 % objectives over stored probe rows.

    ``rows`` are sweep rows — dicts carrying ``service``/``ok``/``ts`` (the
    ``ProbeResult.as_json`` shape; Monitoring uptime-check rows map onto the
    same fields when the readout is fed a Monitoring export). A declared
    target with no in-window rows reports ``no-data`` — never a fabricated
    100 %. ``gate_ok`` is False when no declared target evaluated anything
    (SIG-ENG-042: measured nothing → the readout run fails, it does not print
    a green).
    """
    target_map = dict(targets or SLO_TARGETS)
    start, end = month_bounds(month)
    results: list[SloTargetResult] = []
    evaluated = 0
    for name, services in sorted(target_map.items()):
        window = [
            r
            for r in rows
            if str(r.get("service", r.get("target", ""))) in services
            and (dt := _parse_ts(str(r.get("ts", "")))) is not None
            and start <= dt < end
        ]
        if not window:
            results.append(SloTargetResult(name, 0, 0, None, None, "no-data"))
            continue
        evaluated += 1
        ok = sum(1 for r in window if bool(r.get("ok")))
        uptime = ok / len(window) * 100.0
        allowed = 100.0 - objective_pct
        consumed = None if allowed <= 0 else (100.0 - uptime) / allowed * 100.0
        results.append(
            SloTargetResult(
                name,
                len(window),
                ok,
                uptime,
                consumed,
                "met" if uptime >= objective_pct else "missed",
            )
        )
    return SloReport(
        month=month,
        objective_pct=objective_pct,
        results=tuple(results),
        offered=len(target_map),
        evaluated=evaluated,
        gate_ok=evaluated > 0,
    )


def render_slo_readout(report: SloReport, *, generated_at: str | None = None) -> str:
    """The monthly error-budget readout (SIG-OPS-007) — markdown, deterministic."""
    generated_at = generated_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    allowed = 100.0 - report.objective_pct
    lines: list[str] = [
        f"# SIG availability readout — {report.month} (SIG-OPS-007, P35.2)",
        "",
        f"Generated: {generated_at} · objective: {report.objective_pct}% monthly "
        f"(error budget {allowed}% downtime) · source: ops/probes sweeps + "
        "Monitoring uptime-check rows",
        "",
        "| target | probes | uptime % | error budget consumed | status |",
        "|---|---|---|---|---|",
    ]
    for r in report.results:
        uptime = "—" if r.uptime_pct is None else f"{r.uptime_pct:.3f}"
        consumed = "—" if r.budget_consumed_pct is None else f"{r.budget_consumed_pct:.1f}%"
        lines.append(f"| {r.name} | {r.probes} | {uptime} | {consumed} | {r.status} |")
    lines += [
        "",
        f"Measured: offered={report.offered} evaluated={report.evaluated}"
        + ("" if report.gate_ok else " — measured nothing (SIG-ENG-042: this run fails)"),
        "",
    ]
    if report.notes:
        lines += ["## Notes", ""]
        lines += [f"- {n}" for n in report.notes]
        lines.append("")
    return "\n".join(lines)


def load_probe_rows_jsonl(text: str) -> list[dict[str, Any]]:
    """Decode a sweep JSONL body (ops/probes objects or a local probe log)."""
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        if isinstance(raw, dict):
            rows.append(raw)
    return rows


__all__ = [
    "RENOTIFY_PERIOD",
    "SLO_OBJECTIVE_PCT",
    "SLO_TARGETS",
    "DefRenderError",
    "SloReport",
    "SloTargetResult",
    "load_probe_rows_jsonl",
    "measured_gate",
    "month_bounds",
    "parse_measured_counts",
    "render_slo_readout",
    "renotify_due",
    "slo_report",
    "uptime_create_args",
    "uptime_update_args",
]
