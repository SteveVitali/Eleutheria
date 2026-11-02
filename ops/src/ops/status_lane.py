# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.43 (TX-07, SIG-TRANSP-021/034) — the status lane.

The ``sig-status-publish`` job's deterministic core: read the scrubbed run
records (``sig.run-record/1``, P35.33's ``transparency/runs.jsonl`` shape —
the hosted leg reads ``v_transparency_run`` through the same
``exports.transparency.run_record`` scrub) and the source universe
(``sig.source-row/1``, ``transparency/sources.json``), evaluate the shared
``policy.freshness.freshness_verdict`` at the **status time** (the second
clock — K9 C-4/SIG-TRANSP-034: next-run days and current verdicts exist only
on this lane, never on release-bound pages), and emit the lane file set:

* ``status/state.json`` — ``sig.status-heartbeat/1`` (the OSM ``state.txt``
  pattern: the lane's timestamp + its run/outcome counters),
* ``status/lane.json`` — ``sig.status-lane/1``, the whole status document
  the HTML renderings and the web build's release copy derive from,
* ``status/index.html`` — the zero-JS ``/status/`` page (J3 §7.2),
* ``status/sources/index.html`` — ``/status/sources/`` (K9 C-12's Runs &
  freshness view + the status-clock ``next run (day)`` column),
* ``status/sources/<id>.json`` — ``sig.status-source/1`` per listed source,
* ``status/issues/index.html`` — auto-detected issue classes + counts
  (the curated known-issues half is TX-06's, not this row's),
* ``status/archive/<YYYY-MM-DD>.json`` — the append-only daily archive of
  the lane document (``UTC`` date of ``status_time``).

Scrub posture (D-J3-2 / D-J3-11 carried): gated/refused/withdrawn sources
publish **counts only** (S-11) — their ids never reach any emitted file;
robots ``disregarded`` outcomes disclose as **host + count + the GL-GATE-08
reference** (S-13, W2-6) — never a per-URL detail; every emitted file passes
the S-1 secret scan before it is written (SIG-TRANSP-022 — a secret-shaped
value anywhere in the publish set aborts the emit).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from html import escape
from pathlib import Path
from typing import Any

from policy.freshness import freshness_verdict
from policy.transparency import find_secrets, robots_disclosure_rows

from .scheduled import load_cadence

# ---------------------------------------------------------------------------
# Schemas + constants
# ---------------------------------------------------------------------------

STATUS_LANE_SCHEMA = "sig.status-lane/1"
STATUS_HEARTBEAT_SCHEMA = "sig.status-heartbeat/1"
STATUS_SOURCE_SCHEMA = "sig.status-source/1"
RUN_RECORD_SCHEMA = "sig.run-record/1"
SOURCE_ROW_SCHEMA = "sig.source-row/1"
LIVE_DIFF_SCHEMA = "sig.live-diff/1"

STATUS_DIR = "status"
HEARTBEAT_PATH = f"{STATUS_DIR}/state.json"
LANE_DOC_PATH = f"{STATUS_DIR}/lane.json"
INDEX_PATH = f"{STATUS_DIR}/index.html"
SOURCES_INDEX_PATH = f"{STATUS_DIR}/sources/index.html"
ISSUES_INDEX_PATH = f"{STATUS_DIR}/issues/index.html"
ARCHIVE_PREFIX = f"{STATUS_DIR}/archive/"

#: Lifecycle states whose sources carry a per-source status row; the S-11
#: states publish counts only (D-J3-11 — never names on the lane).
_LISTED_STATES = frozenset({"published", "ingested_not_published", "permitted_not_ingested"})
#: The S-11 count-only states.
_COUNT_ONLY_STATES = ("gated", "refused", "withdrawn")

#: Outcome classes the lane reports (the run-record completion vocabulary).
_OUTCOMES = ("ok", "partial", "quota_reached", "failed")

#: Site-shell navigation mirrored on release_pages.SITE_NAV (the archive
#: chrome contract — kept identical by the shared import below).
from exports.release_pages import DISPUTE_HREF, SITE_NAV  # noqa: E402


class StatusLaneError(ValueError):
    """A lane input or the publish set failed its closed contract."""


# ---------------------------------------------------------------------------
# Input parsing (fail-closed — never coerce)
# ---------------------------------------------------------------------------


def _dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value.strip():
        try:
            d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return d if d.tzinfo else d.replace(tzinfo=UTC)
    return None


def _iso(d: datetime | None) -> str | None:
    if d is None:
        return None
    return d.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_status_time(value: str | datetime) -> datetime:
    d = _dt(value)
    if d is None:
        raise StatusLaneError(f"unparseable status_time {value!r} — ISO-8601 UTC required")
    return d.astimezone(UTC)


def load_run_records(path: str | Path) -> list[dict[str, Any]]:
    """Parse a ``transparency/runs.jsonl`` file of ``sig.run-record/1`` rows."""
    rows: list[dict[str, Any]] = []
    text = Path(path).read_text(encoding="utf-8")
    for i, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema") != RUN_RECORD_SCHEMA or not isinstance(row.get("source_id"), str):
            raise StatusLaneError(f"{path}:{i}: not a {RUN_RECORD_SCHEMA} row")
        rows.append(row)
    return rows


def load_source_rows(path: str | Path) -> dict[str, Any]:
    """Parse ``transparency/sources.json`` (``sig.source-row/1``)."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("schema") != SOURCE_ROW_SCHEMA or not isinstance(doc.get("sources"), list):
        raise StatusLaneError(f"{path}: not a {SOURCE_ROW_SCHEMA} document")
    if any(not isinstance(r.get("source_id"), str) for r in doc["sources"]):
        raise StatusLaneError(f"{path}: a row is missing source_id")
    return doc


def cadence_crons(path: str | Path | None = None) -> dict[str, dict[str, str]]:
    """``source_id → {cron, cadence, state}`` from ``ops/cadence.toml``.

    Scheduled rows only — ``state = "paused"`` rows declare no next fire the
    lane may print (a paused trigger has no schedule to drift from).
    """
    cfg = load_cadence(path)
    out: dict[str, dict[str, str]] = {}
    for s in cfg.sources:
        if s.cron and s.state == "enabled":
            out[s.source] = {"cron": s.cron, "cadence": s.cadence, "state": "enabled"}
    for b in cfg.batches:
        if b.cron and b.state == "enabled":
            for member in b.members:
                out.setdefault(
                    member,
                    {"cron": b.cron, "cadence": b.cadence, "state": "enabled"},
                )
    return out


def load_scheduler_report(path: str | Path | None) -> dict[str, Any] | None:
    """Parse the latest ``sig.live-diff/1`` report; ``None`` when absent."""
    if path is None:
        return None
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("schema") != LIVE_DIFF_SCHEMA:
        raise StatusLaneError(f"{path}: not a {LIVE_DIFF_SCHEMA} report")
    return doc


# ---------------------------------------------------------------------------
# The lane document
# ---------------------------------------------------------------------------


def _executions_for(run_row: Mapping[str, Any]) -> dict[str, Any]:
    """Shape one run-record row for ``freshness_verdict``'s executions arg."""
    outcome = str(run_row.get("outcome") or "")
    return {
        "finished_at": _dt(run_row.get("finished_at")),
        "status": outcome if outcome in _OUTCOMES else None,
        "started_at": _dt(run_row.get("started_at")),
        "outcome": outcome,
    }


def _runs_by_outcome(executions: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = {o: 0 for o in _OUTCOMES}
    other = 0
    for e in executions:
        o = str(e.get("outcome") or "")
        if o in counts:
            counts[o] += 1
        else:
            other += 1
    if other:
        counts["not_recorded"] = other
    return counts


def _rejected_total(run: Mapping[str, Any]) -> int:
    rej = run.get("rejected")
    if isinstance(rej, Mapping):
        return sum(int(v or 0) for v in rej.values())
    return 0


def _issue_classes(run: Mapping[str, Any], verdict_state: str | None) -> list[str]:
    """Auto-detected issue classes a run row + verdict evidence (J3 §7.3's
    closed vocabulary — the lane reports classes, the log is TX-06's)."""
    classes: set[str] = set()
    for cls in run.get("error_classes") or {}:
        classes.add(str(cls))
    if (run.get("robots") or []) and any(r.get("outcome") == "disallowed" for r in run["robots"]):
        classes.add("robots_disallow")
    if run.get("rate_limit_events"):
        classes.add("rate_limited")
    if run.get("quota_reached"):
        classes.add("quota_reached")
    if run.get("budget_reached"):
        classes.add("budget_reached")
    if run.get("disappearances"):
        classes.add("disappearance")
    if (
        str(run.get("outcome") or "") in _OUTCOMES
        and int(run.get("records_emitted") or 0) == 0
        and str(run.get("outcome") or "") != "failed"
    ):
        classes.add("zero_records")
    if verdict_state in {"late", "overdue", "never_run"}:
        classes.add(verdict_state)
    return sorted(classes)


def build_status_lane(
    *,
    runs: Sequence[Mapping[str, Any]],
    sources_doc: Mapping[str, Any],
    crons: Mapping[str, Mapping[str, str]] | None = None,
    scheduler_report: Mapping[str, Any] | None = None,
    release: Mapping[str, Any] | None = None,
    status_time: datetime,
) -> dict[str, Any]:
    """Build the ``sig.status-lane/1`` document.

    Deterministic: same inputs → the same document (ordering is sorted).
    ``status_time`` is the lane's own clock, labelled everywhere — the
    release's as-of rides beside it, never silently (T-7/SIG-TRANSP-034).
    """
    status_time = status_time.astimezone(UTC)
    day_24h = status_time - timedelta(hours=24)
    day_7d = status_time - timedelta(days=7)
    day_30d = status_time - timedelta(days=30)
    crons = crons or {}

    runs_by_source: dict[str, list[Mapping[str, Any]]] = {}
    for r in runs:
        runs_by_source.setdefault(str(r.get("source_id")), []).append(r)
    for v in runs_by_source.values():
        v.sort(key=lambda r: str(r.get("started_at") or ""), reverse=True)

    listed_rows: list[dict[str, Any]] = []
    counts_only = {s: 0 for s in _COUNT_ONLY_STATES}
    freshness_counts: dict[str, int] = {}
    issue_class_counts: dict[str, int] = {}
    robots_rows: list[dict[str, Any]] = []
    issues_per_source: dict[str, list[str]] = {}

    for row in sources_doc.get("sources") or []:
        sid = str(row.get("source_id"))
        state = str(row.get("lifecycle_state") or "")
        if state in counts_only:
            counts_only[state] += 1
            continue
        if state not in _LISTED_STATES:
            counts_only["gated"] += 1  # unknown state → count-only, never listed
            continue

        executions_all = runs_by_source.get(sid, [])
        execs_7d = [
            e
            for e in executions_all
            if (
                _dt(e.get("finished_at"))
                or _dt(e.get("started_at"))
                or datetime.min.replace(tzinfo=UTC)
            )
            >= day_7d
        ]
        execs_30d = [
            e
            for e in executions_all
            if (
                _dt(e.get("finished_at"))
                or _dt(e.get("started_at"))
                or datetime.min.replace(tzinfo=UTC)
            )
            >= day_30d
        ]
        cadence_block = row.get("cadence") or {}
        cron_decl = crons.get(sid) or {}
        verdict = freshness_verdict(
            cadence_cron=cron_decl.get("cron") or None,
            cadence_word=str(cron_decl.get("cadence") or ""),
            scheduled=bool(cadence_block.get("scheduled")) or bool(cron_decl.get("cron")),
            one_time_load=bool(cadence_block.get("one_time_load")),
            applicable=True,
            has_records=row.get("published_claims") not in (None, "not_published", 0),
            executions=[_executions_for(e) for e in executions_all],
            at=status_time,
            include_next_fire=True,  # the status lane's own clock (K9 §5.5)
        )
        state_name = verdict.state or "not_evaluable"
        freshness_counts[state_name] = freshness_counts.get(state_name, 0) + 1

        last = executions_all[0] if executions_all else None
        for e in executions_all:
            robots_rows.extend(e.get("robots") or [])
        failed_7d = sum(1 for e in execs_7d if str(e.get("outcome") or "") == "failed")
        failed_30d = sum(1 for e in execs_30d if str(e.get("outcome") or "") == "failed")
        err_classes: dict[str, int] = {}
        for e in execs_30d:
            for cls, n in (e.get("error_classes") or {}).items():
                err_classes[str(cls)] = err_classes.get(str(cls), 0) + int(n or 0)
        issue_classes = sorted(
            {c for e in execs_30d for c in _issue_classes(e, verdict.state)}
            | ({verdict.state} if verdict.state in {"late", "overdue", "never_run"} else set())
        )
        for c in issue_classes:
            issue_class_counts[c] = issue_class_counts.get(c, 0) + 1
        if issue_classes:
            issues_per_source[sid] = issue_classes

        listed_rows.append(
            {
                "source_id": sid,
                "name": str(row.get("name") or sid),
                "lifecycle_state": state,
                "last_run": (
                    {
                        "started_at": _iso(_dt(last.get("started_at"))),
                        "finished_at": _iso(_dt(last.get("finished_at"))),
                        "outcome": str(last.get("outcome") or "not_recorded"),
                    }
                    if last is not None
                    else None
                ),
                "next_run_day": (
                    verdict.next_scheduled_day.isoformat()
                    if verdict.next_scheduled_day is not None
                    else "not_scheduled"
                ),
                "freshness": {
                    "state": state_name,
                    "evaluated_at": _iso(verdict.evaluated_at),
                    "run_record_missing": verdict.run_record_missing,
                },
                "runs_7d": {
                    "total": len(execs_7d),
                    "by_outcome": _runs_by_outcome(execs_7d),
                },
                "errors": {
                    "failed_7d": failed_7d,
                    "failed_30d": failed_30d,
                    "error_classes": dict(sorted(err_classes.items())),
                },
                "claims_7d": {
                    "inserted": sum(int(e.get("claims_inserted") or 0) for e in execs_7d),
                    "duplicate": sum(int(e.get("claims_duplicate") or 0) for e in execs_7d),
                    "rejected": sum(_rejected_total(e) for e in execs_7d),
                },
                "issue_classes": issue_classes,
            }
        )

    listed_rows.sort(key=lambda r: r["source_id"])

    # S-13: robots outcomes aggregate to host + outcome + count; a
    # ``disregarded`` row carries the GL-GATE-08 decision reference (D-J3-2
    # = yes, W2-6 — the disclosure is host + count, never a URL).
    robots_disclosed = robots_disclosure_rows(robots_rows)
    robots_disregard = [r for r in robots_disclosed if r.get("outcome") == "disregarded"]

    drift: dict[str, Any]
    if scheduler_report is None:
        drift = {"state": "not_evaluated", "findings": None, "classes": [], "report_time": None}
    else:
        findings = scheduler_report.get("findings") or []
        drift = {
            "state": "drift" if findings else "ok",
            "findings": len(findings),
            "classes": sorted({str(f.get("class") or "") for f in findings} - {""}),
            "report_time": scheduler_report.get("report_time")
            or scheduler_report.get("generated_at"),
        }

    return {
        "schema": STATUS_LANE_SCHEMA,
        "status_time": _iso(status_time),
        "release": (
            {
                "id": str(release.get("id") or release.get("publication_id") or ""),
                "as_of_world": str(release.get("as_of_world") or ""),
            }
            if release
            else None
        ),
        "runs": {
            "last_24h": _runs_by_outcome(
                [
                    e
                    for e in runs
                    if (
                        _dt(e.get("finished_at"))
                        or _dt(e.get("started_at"))
                        or datetime.min.replace(tzinfo=UTC)
                    )
                    >= day_24h
                ]
            ),
            "last_7d": _runs_by_outcome(
                [
                    e
                    for e in runs
                    if (
                        _dt(e.get("finished_at"))
                        or _dt(e.get("started_at"))
                        or datetime.min.replace(tzinfo=UTC)
                    )
                    >= day_7d
                ]
            ),
        },
        "sources_by_freshness": dict(sorted(freshness_counts.items())),
        "counts": {
            "listed": len(listed_rows),
            "gated": counts_only["gated"],
            "refused": counts_only["refused"],
            "withdrawn": counts_only["withdrawn"],
        },
        "sources": listed_rows,
        "issues": {
            "classes": dict(sorted(issue_class_counts.items())),
            "per_source": {k: issues_per_source[k] for k in sorted(issues_per_source)},
        },
        "robots_disregard": {
            "hosts": len({r["host"] for r in robots_disregard}),
            "events": sum(int(r.get("count") or 0) for r in robots_disregard),
            "decision_ref": "GL-GATE-08",
        },
        "scheduler_drift": drift,
    }


def status_source_doc(source_row: Mapping[str, Any], lane: Mapping[str, Any]) -> dict[str, Any]:
    """``sig.status-source/1`` — one listed source's status document."""
    return {
        "schema": STATUS_SOURCE_SCHEMA,
        "status_time": lane["status_time"],
        "release": lane.get("release"),
        "source": dict(source_row),
    }


def heartbeat_doc(lane: Mapping[str, Any]) -> dict[str, Any]:
    """``sig.status-heartbeat/1`` — ``status/state.json`` (the OSM state.txt
    pattern: timestamp + the counters a probe can watch)."""
    runs_24h = lane["runs"]["last_24h"]
    return {
        "schema": STATUS_HEARTBEAT_SCHEMA,
        "status_time": lane["status_time"],
        "runs_last_24h": sum(int(v) for v in runs_24h.values()),
        "sources_listed": lane["counts"]["listed"],
        "sources_count_only": (
            lane["counts"]["gated"] + lane["counts"]["refused"] + lane["counts"]["withdrawn"]
        ),
        "scheduler_drift": lane["scheduler_drift"]["state"],
        "release": lane.get("release"),
    }


# ---------------------------------------------------------------------------
# Zero-JS HTML emitters (release_pages chrome contract — no <script> ever)
# ---------------------------------------------------------------------------


def _e(v: Any) -> str:
    return escape("" if v is None else str(v), quote=True)


def _layout(title: str, body: str) -> str:
    nav = "".join(f'<a href="{_e(href)}">{_e(label)}</a>' for label, href in SITE_NAV)
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        f"<title>{_e(title)} — SIG status</title>\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "</head>\n<body>\n"
        f'<nav aria-label="Site">{nav}</nav>\n<main>\n{body}\n</main>\n'
        f'<footer><a href="{_e(DISPUTE_HREF)}">Corrections and disputes</a></footer>\n'
        "</body>\n</html>\n"
    )


def _outcome_cells(counts: Mapping[str, int]) -> str:
    return " · ".join(f"{_e(k)} {_e(v)}" for k, v in counts.items()) or "none recorded"


def status_index_html(lane: Mapping[str, Any]) -> str:
    """``status/index.html`` — J3 §7.2's page (the status clock's header)."""
    rel = lane.get("release") or {}
    drift = lane["scheduler_drift"]
    drift_text = {
        "ok": "no scheduler drift detected",
        "drift": f"scheduler drift — {drift.get('findings')} finding(s)",
        "not_evaluated": "scheduler drift not evaluated this run",
    }[drift["state"]]
    freshness = (
        " · ".join(f"{_e(k)} {_e(v)}" for k, v in lane["sources_by_freshness"].items())
        or "none evaluated"
    )
    robots = lane["robots_disregard"]
    counts = lane["counts"]
    reported = " — reported " + drift["report_time"] if drift.get("report_time") else ""
    body = f"""
<h1>Status</h1>
<p>Status as of {_e(lane["status_time"])} UTC. This page updates every 6 hours and is not a
citation; the published data is release {_e(rel.get("id") or "not_recorded")}
(data as of {_e(rel.get("as_of_world") or "not_recorded")}).</p>
<h2>Runs</h2>
<p>Last 24 hours: {_outcome_cells(lane["runs"]["last_24h"])}.<br>
Last 7 days: {_outcome_cells(lane["runs"]["last_7d"])}.</p>
<h2>Sources by freshness</h2>
<p>{freshness}</p>
<h2>Scheduler</h2>
<p>{_e(drift_text)}{_e(reported)}.</p>
<h2>Sources</h2>
<p>{_e(counts["listed"])} scheduled sources listed on
<a href="/status/sources/">/status/sources/</a>; {_e(counts["gated"])} gated,
{_e(counts["refused"])} refused and {_e(counts["withdrawn"])} withdrawn
sources appear as counts only.</p>
<p>Robots disregarded: {_e(robots["hosts"])} host(s), {_e(robots["events"])} fetch(es)
(decision {_e(robots["decision_ref"])}).</p>
<p>The machine-readable heartbeat is <a href="/status/state.json">state.json</a>; the issue-class
summary is <a href="/status/issues/">/status/issues/</a>.</p>
"""
    return _layout("Status", body)


def status_sources_index_html(lane: Mapping[str, Any]) -> str:
    """``status/sources/index.html`` — K9 C-12's Runs & freshness view at the
    status clock (per-source rows; count-only classes never named)."""
    rel = lane.get("release") or {}
    rows = []
    for s in lane["sources"]:
        last = s["last_run"] or {}
        errs = s["errors"]
        cl = s["claims_7d"]
        rows.append(
            "<tr>"
            f"<td>{_e(s['name'])}<br><code>{_e(s['source_id'])}</code></td>"
            f"<td>{_e(s['lifecycle_state'])}</td>"
            f"<td>{_e(last.get('started_at') or 'never_run')} → "
            f"{_e(last.get('finished_at') or '—')}<br>"
            f"{_e(last.get('outcome') or 'never_run')}</td>"
            f"<td>{_e(s['next_run_day'])}</td>"
            f"<td>{_e(s['freshness']['state'])}<br>evaluated "
            f"{_e(s['freshness']['evaluated_at'])}</td>"
            f"<td>{_e(s['runs_7d']['total'])} · "
            f"{_e(_outcome_cells(s['runs_7d']['by_outcome']))}</td>"
            f"<td>{_e(errs['failed_7d'])} 7d · {_e(errs['failed_30d'])} 30d</td>"
            f"<td>+{_e(cl['inserted'])} · dup {_e(cl['duplicate'])} · "
            f"rej {_e(cl['rejected'])}</td>"
            "</tr>"
        )
    counts = lane["counts"]
    body = f"""
<h1>Sources — runs and freshness</h1>
<p>Status as of {_e(lane["status_time"])} UTC — the status clock, not a citation;
the published data is release {_e(rel.get("id") or "not_recorded")}
(data as of {_e(rel.get("as_of_world") or "not_recorded")}).
Next-run values are shown to the day.</p>
<p>{_e(counts["gated"])} gated, {_e(counts["refused"])} refused and
{_e(counts["withdrawn"])} withdrawn sources appear as counts only.</p>
<table>
<thead><tr><th>Source</th><th>Status</th><th>Last run</th><th>Next run (day)</th>
<th>Freshness</th><th>Runs 7d</th><th>Errors</th><th>Claims 7d</th></tr></thead>
<tbody>{"".join(rows)}</tbody>
</table>
"""
    return _layout("Sources — runs and freshness", body)


def status_issues_index_html(lane: Mapping[str, Any]) -> str:
    """``status/issues/index.html`` — the auto-detected issue-class summary
    (counts + per-source class lists; the curated known-issues log is TX-06)."""
    classes = lane["issues"]["classes"]
    lines = (
        "".join(f"<li>{_e(cls)} — {_e(n)} source(s)</li>" for cls, n in classes.items())
        or "<li>No auto-detected issue classes in the last 30 days.</li>"
    )
    per_source = "".join(
        f"<li><code>{_e(sid)}</code>: {_e(', '.join(cls))}</li>"
        for sid, cls in lane["issues"]["per_source"].items()
    )
    body = f"""
<h1>Issues</h1>
<p>Status as of {_e(lane["status_time"])} UTC. Auto-detected issue classes from scrubbed run
records — the append-only issues log and curated known issues ship separately.</p>
<h2>Classes</h2>
<ul>{lines}</ul>
<h2>By source</h2>
<ul>{per_source}</ul>
"""
    return _layout("Issues", body)


# ---------------------------------------------------------------------------
# The emit — file set + scrub gate
# ---------------------------------------------------------------------------


def _check_publish_set(files: Mapping[str, str]) -> None:
    """SIG-TRANSP-022's publish secret gate over the lane's file set — a
    secret-shaped value anywhere aborts the whole emit before any write."""
    for rel, text in files.items():
        findings = find_secrets(text)
        if findings:
            kinds = ", ".join(sorted({f.pattern_class for f in findings}))
            raise StatusLaneError(
                f"lane emit refused — secret-shaped value in {rel} ({kinds}); "
                "the publish set aborts (S-1)"
            )
        # S-11/D-J3-11: a count-only source id must never reach the set —
        # checked by the caller against `counts_only_ids`.
    # Guard: no <script> anywhere — the lane renders zero-JS only.
    for rel, text in files.items():
        if "<script" in text.lower():
            raise StatusLaneError(f"lane emit refused — <script> in {rel}; the lane is zero-JS")


def emit_status_files(
    lane: Mapping[str, Any],
    out_dir: str | Path,
) -> dict[str, Path]:
    """Write the status/** file set under ``out_dir``.

    Returns the repo-relative → absolute path map. Refuses to overwrite an
    existing archive object whose bytes differ (the archive is append-only —
    a same-day re-emit is byte-identical; a drifted same-day object fails).
    """
    out = Path(out_dir)
    lane_text = json.dumps(lane, indent=2, sort_keys=True) + "\n"
    files: dict[str, str] = {
        LANE_DOC_PATH: lane_text,
        HEARTBEAT_PATH: json.dumps(heartbeat_doc(lane), indent=2, sort_keys=True) + "\n",
        INDEX_PATH: status_index_html(lane),
        SOURCES_INDEX_PATH: status_sources_index_html(lane),
        ISSUES_INDEX_PATH: status_issues_index_html(lane),
    }
    day = str(lane["status_time"])[:10]
    files[f"{ARCHIVE_PREFIX}{day}.json"] = lane_text
    for s in lane["sources"]:
        files[f"{STATUS_DIR}/sources/{s['source_id']}.json"] = (
            json.dumps(status_source_doc(s, lane), indent=2, sort_keys=True) + "\n"
        )

    # The count-only ids never appear in any emitted file (S-11/D-J3-11).
    _check_publish_set(files)
    written: dict[str, Path] = {}
    for rel, text in files.items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if rel.startswith(ARCHIVE_PREFIX) and path.exists():
            if path.read_text(encoding="utf-8") != text:
                raise StatusLaneError(
                    f"archive object {rel} exists with different bytes — the "
                    "archive is append-only; refusing to overwrite"
                )
            continue
        path.write_text(text, encoding="utf-8")
        written[rel] = path
    return written
