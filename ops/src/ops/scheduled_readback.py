# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

"""P34.39a — read-only read-back of a scheduled-ingest execution (D-P31.4-1).

``sig-ops scheduled-readback`` gathers, after the fact, the evidence that a
scheduled ingest ran and what it did, and compares it with D-P31.4-1's success
criteria plus G1 §3.7's additions:

- the Cloud Run execution result and the Cloud Scheduler trigger state,
- the ``ops/runs`` WORM run rows for every batch member on the run date,
- the ``ingest_run_completion`` row for the run,
- ``pg_stat_user_tables`` ``n_tup_upd``/``n_tup_del`` on the ingest write set,
- the ``ops/probes`` ``sig-api-health`` rows on the run date, and
- Cloud Monitoring timeseries for Cloud SQL memory / disk / uptime.

AR-4 clock guard: before the fire the command refuses (exit
``READBACK_QUEUED`` — the protect.sh "queued, not failed" convention) and
prints the leg-rerun prompt. AR-5: every gather is a read; this command never
re-executes, never cancels, never mutates production.
"""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from .cadence_window import previous_fire
from .gcs import GcsBucket, GcsError, default_token_provider

# ---------------------------------------------------------------------------
# Exit codes.  42 is the protect.sh "queued, not failed" convention (P35.20):
# the leg did not run because the clock guard does not yet hold — not an error.
READBACK_QUEUED = 42
READBACK_ERROR = 1

RERUN_PROMPT = (
    "implement-spec spec=docs/tickets/247_P34.39a__osm-replay-read-back.md live_verification=true"
)

# D-P31.4-1 / G1 §3.7 constants for the 2026-10-10 batch-05 OSM replay.
EXPECTED_OSM_FETCHES = 158
EXPECTED_OSM_CLAIMS = 1_369_210  # the recorded 09-23 replay (G1 §3.7 "≈1.37M")
CLAIMS_TOLERANCE = 0.15  # ±15% band around the recorded ≈1.37M
MEMBER_WELL_UNDER_HOUR_S = 3600  # G1 §3.7 "well under 1 h"
BATCH_TIMEOUT_S = 36 * 3600  # ADR-107 36h ceiling; contract AR-4 timeout route
ANOMALY_DISK_JUMP_BYTES = 3 << 30  # G1 §3.7 anomaly: "disk jump over 3 GB"
HEALTH_MAX_TRANSIENT_NOT_OK = 1  # "at most one transient 503"
MEM_UTIL_LIMIT = 0.90  # Cloud SQL memory < 90%
DISK_GROWTH_LIMIT_BYTES = 1 << 30  # "< 1 GB" read as 1 GiB

M_MEM_UTIL = "cloudsql.googleapis.com/database/memory/utilization"
M_DISK_BYTES = "cloudsql.googleapis.com/database/disk/bytes_used"
M_UPTIME = "cloudsql.googleapis.com/database/uptime"
MONITORING_METRICS = (M_MEM_UTIL, M_DISK_BYTES, M_UPTIME)

# The append-only ingest write set (everything PgClaimSink / the completion
# append write to).  UPDATE/DELETE counters on these must stay zero.
SPINE_TABLES = (
    "assertion_quarantine",
    "claim",
    "claim_evidence",
    "claim_qualifier",
    "entity",
    "entity_identifier",
    "entity_identity_key",
    "evidence_artifact",
    "evidence_blob",
    "evidence_capture",
    "extraction",
    "ingest_run",
    "ingest_run_capture",
    "ingest_run_completion",
    "organization",
    "rights_record",
    "source_registry",
)

OSM_MEMBER = "camreg_osm_surveillance"

# The pinned batch-05 image predates P31.7's re-sighting bookkeeping; the
# contract requires the read-back to say so rather than imply support.
RESIGHTING_DISCLOSURE = (
    "the pinned batch-05 image sig-api@sha256:feff986cf66f551ed12031d6627ac"
    "defd3217192a9e20d452c3d4fe0376833f2 predates P31.7 and does not record "
    "P31.7 re-sightings; the OSM re-fetch therefore refreshes the +0 claims "
    "without emitting re-sighting records"
)


# ---------------------------------------------------------------------------
# Injectable dependencies

GcloudRunner = Callable[[Sequence[str]], str]
QueryFn = Callable[[str, tuple], list[tuple]]
SeriesFn = Callable[[str, datetime, datetime], list[dict]]  # metric -> points
HealthFn = Callable[[str], dict]  # url -> {"status": int, ...}


def gcloud_cli(args: Sequence[str]) -> str:
    """Run a read-only ``gcloud`` call, returning stdout (raise on failure)."""
    p = subprocess.run(["gcloud", *args], capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise RuntimeError(f"gcloud {' '.join(args)} failed ({p.returncode}): {p.stderr.strip()}")
    return p.stdout


def monitoring_series_factory(
    *, project: str, token_provider: Callable[[], str | None] | None = None
) -> SeriesFn:
    """Return a read-only Cloud Monitoring ``timeSeries.list`` fetcher."""
    tp = token_provider or default_token_provider

    def _series(metric_type: str, start: datetime, end: datetime) -> list[dict]:
        token = tp()
        if not token:
            raise GcsError(
                "no access token (metadata server + gcloud ADC both absent) — "
                "monitoring reads skipped"
            )
        flt = f'metric.type = "{metric_type}" AND resource.type = "cloudsql_database"'
        url = (
            f"https://monitoring.googleapis.com/v3/projects/{project}"
            "/timeSeries?"
            + urllib.parse.urlencode(
                {
                    "filter": flt,
                    "interval.startTime": start.isoformat().replace("+00:00", "Z"),
                    "interval.endTime": end.isoformat().replace("+00:00", "Z"),
                    "view": "FULL",
                    "pageSize": "500",
                }
            )
        )
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        body = urllib.request.urlopen(req, timeout=60).read()  # noqa: S310
        doc = json.loads(body.decode("utf-8"))
        points: list[dict] = []
        for ts in doc.get("timeSeries", []):
            for pt in ts.get("points", []):
                val = pt.get("value", {})
                num = val.get("doubleValue") if "doubleValue" in val else val.get("int64Value")
                points.append(
                    {
                        "time": pt.get("interval", {}).get("endTime"),
                        "value": float(num) if num is not None else None,
                    }
                )
        points.sort(key=lambda p: p.get("time") or "")
        return points

    return _series


def api_health_factory(*, token_provider: Callable[[], str | None] | None = None) -> HealthFn:
    """Return an authenticated GET /health probe (read-only)."""
    tp = token_provider or default_token_provider

    def _health(api_url: str) -> dict:
        token = tp()
        if not token:
            raise GcsError(
                "no access token (metadata server + gcloud ADC both absent) — "
                "the /health read is skipped"
            )
        url = api_url.rstrip("/") + "/health"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            resp = urllib.request.urlopen(req, timeout=30)  # noqa: S310
            return {
                "status": resp.status,
                "body": json.loads(resp.read().decode("utf-8") or "{}"),
            }
        except urllib.error.HTTPError as e:  # still an answer, record it
            return {"status": e.code, "error": e.read().decode("utf-8")[:400]}
        except Exception as e:
            return {"status": None, "error": str(e)}

    return _health


def pg_query_factory(dsn: str) -> QueryFn:
    """Return a read-only-session query function over a psycopg DSN.

    Autocommit + ``SET SESSION CHARACTERISTICS … READ ONLY`` so every statement
    is its own read-only transaction (a failed read cannot abort the rest) and
    a 300 s statement_timeout bounds every one (per-source claim counts walk
    the run index over millions of rows).
    """
    import psycopg

    conn = psycopg.connect(dsn, connect_timeout=20, autocommit=True)
    conn.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY")
    conn.execute("SET statement_timeout = '300s'")

    def _q(sql: str, params: tuple = ()) -> list[tuple]:
        return conn.execute(sql, params).fetchall()

    return _q


# ---------------------------------------------------------------------------
# Pure helpers


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _utc(dt: datetime) -> datetime:
    return dt.astimezone(UTC)


def fire_time_for(cron: str, run_date: date) -> datetime:
    """The UTC time ``cron`` last fires on ``run_date`` (raise if it doesn't)."""
    end = datetime.combine(run_date, datetime.max.time(), tzinfo=UTC)
    fire = previous_fire(cron, end)
    if fire.date() != run_date:
        raise ValueError(f"cron {cron!r} does not fire on {run_date.isoformat()}")
    return fire


def pick_execution(
    executions: Sequence[Mapping[str, Any]],
    job: str,
    fire: datetime,
    *,
    skew: timedelta = timedelta(minutes=2),
) -> Mapping[str, Any] | None:
    """The newest execution of ``job`` created at/after ``fire`` (±skew)."""
    out: Mapping[str, Any] | None = None
    for ex in executions:
        name = str(ex.get("metadata", {}).get("name", ""))
        if not name.startswith(job):
            continue
        created = _parse_ts(ex.get("metadata", {}).get("creationTimestamp"))
        if created is None or _utc(created) < fire - skew:
            continue
        prev = (
            _parse_ts(out.get("metadata", {}).get("creationTimestamp")) if out is not None else None
        )
        if prev is None or _utc(created) > _utc(prev):
            out = ex
    return out


def execution_summary(ex: Mapping[str, Any] | None) -> dict:
    if not ex:
        return {"found": False}
    st = ex.get("status", {})
    start = _parse_ts(st.get("startTime"))
    done = _parse_ts(st.get("completionTime"))
    dur = (done - start).total_seconds() if start and done else None
    cond = {c.get("type"): c.get("state", c.get("status")) for c in st.get("conditions", [])}
    succeeded = st.get("succeededCount") or 0
    failed = st.get("failedCount") or 0
    cancelled = st.get("cancelledCount") or 0
    return {
        "found": True,
        "name": ex.get("metadata", {}).get("name"),
        "created": ex.get("metadata", {}).get("creationTimestamp"),
        "start": st.get("startTime"),
        "completion": st.get("completionTime"),
        "duration_seconds": dur,
        "finished": done is not None,
        "succeeded": succeeded,
        "failed": failed,
        "cancelled": cancelled,
        "completed_ok": done is not None and failed == 0 and cancelled == 0,
        "conditions": cond,
        "observed_generation": st.get("observedGeneration"),
    }


def guard_failures(
    *,
    fire: datetime,
    now: datetime,
    scheduler: Mapping[str, Any] | None,
    execution: Mapping[str, Any] | None,
    executions_error: str | None = None,
    scheduler_error: str | None = None,
    skew: timedelta = timedelta(minutes=2),
) -> list[str]:
    """The AR-4 conditions that must all hold before the leg runs."""
    out: list[str] = []
    if _utc(now) < _utc(fire):
        out.append(
            f"scheduled fire {fire.isoformat()} is in the future (now {_utc(now).isoformat()})"
        )
    if scheduler is None:
        out.append("scheduler trigger describe unavailable")
        if scheduler_error:
            out.append(f"scheduler describe failed: {scheduler_error}")
    else:
        if scheduler.get("state") == "DISABLED":
            out.append("scheduler trigger is DISABLED")
        last_attempt = _parse_ts(scheduler.get("lastAttemptTime"))
        if last_attempt is None:
            out.append("scheduler trigger has not fired (no lastAttemptTime)")
        elif _utc(last_attempt) < _utc(fire) - skew:
            out.append(
                "scheduler trigger's lastAttemptTime "
                f"{scheduler.get('lastAttemptTime')} predates this run's "
                f"fire {fire.isoformat()}"
            )
    if executions_error:
        out.append(f"executions list failed: {executions_error}")
    elif execution is None:
        out.append("no Cloud Run execution exists at/after the fire")
    elif not execution_summary(execution).get("finished"):
        out.append("the Cloud Run execution has not finished")
    return out


# ---------------------------------------------------------------------------
# Gathers (each returns (value, error) — errors degrade criteria honestly)


@dataclass
class Gathered:
    scheduler: Mapping[str, Any] | None = None
    job: Mapping[str, Any] | None = None
    executions: list[Mapping[str, Any]] = field(default_factory=list)
    run_rows: dict[str, list[dict]] = field(default_factory=dict)
    completions: list[dict] = field(default_factory=list)
    counters: dict[str, dict[str, int]] = field(default_factory=dict)
    claim_counts: dict[str, int] = field(default_factory=dict)
    counters_queried: bool = False
    completions_queried: bool = False
    probes: list[dict] = field(default_factory=list)
    monitoring: dict[str, list[dict]] = field(default_factory=dict)
    api_health: dict | None = None
    baseline: dict | None = None
    errors: list[str] = field(default_factory=list)


def _run_row_dates(rows: Sequence[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: str(r.get("started_at", "")))


def gather_run_rows_gcs(
    bucket: GcsBucket, members: Sequence[str], run_date: date
) -> tuple[dict[str, list[dict]], list[str]]:
    rows: dict[str, list[dict]] = {}
    errs: list[str] = []
    for src in members:
        prefix = f"ops/runs/{src}/{run_date.isoformat()}/"
        found: list[dict] = []
        try:
            for name in bucket.list_objects(prefix):
                try:
                    doc = json.loads(bucket.get_object(name).decode("utf-8"))
                except ValueError:
                    continue
                if isinstance(doc, dict):
                    doc["_object"] = f"gs://{bucket.bucket}/{name}"
                    found.append(doc)
        except Exception as e:  # noqa: BLE001 — recorded, never swallowed
            errs.append(f"run rows {src}: {e}")
        rows[src] = _run_row_dates(found)
    return rows, errs


def gather_probes_gcs(
    bucket: GcsBucket, run_date: date, target: str = "sig-api-health"
) -> tuple[list[dict], list[str]]:
    out: list[dict] = []
    errs: list[str] = []
    prefix = f"ops/probes/{run_date.isoformat()}/"
    try:
        names = bucket.list_objects(prefix)
    except Exception as e:  # noqa: BLE001 — recorded, never swallowed
        return out, [f"probes list {prefix}: {e}"]
    for name in names:
        try:
            text = bucket.get_object(name).decode("utf-8")
        except Exception as e:  # noqa: BLE001 — recorded, never swallowed
            errs.append(f"probe {name}: {e}")
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                doc = json.loads(line)
            except ValueError:
                continue
            if doc.get("service") == target:
                out.append(doc)
    out.sort(key=lambda d: str(d.get("ts", "")))
    return out, errs


def db_counters(query: QueryFn) -> dict[str, dict[str, int]]:
    rows = query(
        "SELECT relname, n_tup_upd, n_tup_del FROM pg_stat_user_tables WHERE relname = ANY(%s)",
        (list(SPINE_TABLES),),
    )
    return {str(r[0]): {"n_tup_upd": int(r[1]), "n_tup_del": int(r[2])} for r in rows}


def db_completions(query: QueryFn, since: datetime) -> list[dict]:
    rows = query(
        "SELECT completion_id, run_id, source_id, status, finished_at, "
        "claims_considered, claims_inserted, claims_duplicate, "
        "run_record_uri, backfilled_from, detail, recorded_at "
        "FROM ingest_run_completion "
        "WHERE finished_at >= %s OR recorded_at >= %s "
        "ORDER BY finished_at",
        (since, since),
    )
    cols = [
        "completion_id",
        "run_id",
        "source_id",
        "status",
        "finished_at",
        "claims_considered",
        "claims_inserted",
        "claims_duplicate",
        "run_record_uri",
        "backfilled_from",
        "detail",
        "recorded_at",
    ]
    return [
        {c: (v.isoformat() if isinstance(v, datetime) else v) for c, v in zip(cols, r, strict=True)}
        for r in rows
    ]


def db_claim_counts(query: QueryFn, members: Sequence[str]) -> dict[str, int]:
    """Per-source claim counts through the evidence chain.

    ``claim`` carries no ``source_id``, and the pre-P31.2 reuse-by-key runs
    folded several sources' executions into one ``ingest_run`` — so a
    run→completion→source map mis-attributes the folded runs' claims (a live
    check 2026-10-07 showed the shared run's 2,058,714 claims all credited to
    the alphabetically-first member).  The honest attribution walks
    ``claim → claim_evidence → evidence_capture → evidence_artifact.source_id``
    (the same chain ``run_completion.py`` uses), counting each claim once.
    """
    rows = query(
        "SELECT ea.source_id, count(DISTINCT c.claim_id) "
        "FROM claim c "
        "JOIN claim_evidence ce ON ce.claim_id = c.claim_id "
        "JOIN evidence_capture ec ON ec.capture_id = ce.capture_id "
        "JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id "
        "WHERE ea.source_id = ANY(%s) "
        "GROUP BY ea.source_id",
        (list(members),),
    )
    return {str(r[0]): int(r[1]) for r in rows}


def db_claim_total(query: QueryFn) -> int:
    return int(query("SELECT count(*) FROM claim", ())[0][0])


# ---------------------------------------------------------------------------
# Fixture replay: identical report shape, every gather read from a directory.


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def gather_from_fixtures(fixtures: Path, members: Sequence[str], run_date: date) -> Gathered:
    g = Gathered()
    g.scheduler = _load_json(fixtures / "scheduler.json")
    g.job = _load_json(fixtures / "job.json")
    ex = _load_json(fixtures / "executions.json")
    g.executions = list(ex) if isinstance(ex, list) else []
    g.baseline = _load_json(fixtures / "baseline.json")
    g.api_health = _load_json(fixtures / "api_health.json")

    for src in members:
        d = fixtures / "run_rows" / src / run_date.isoformat()
        rows = []
        if d.is_dir():
            for f in sorted(d.glob("*.json")):
                doc = _load_json(f)
                if isinstance(doc, dict):
                    doc["_object"] = str(f.relative_to(fixtures))
                    rows.append(doc)
        g.run_rows[src] = _run_row_dates(rows)

    probes: list[dict] = []
    pd = fixtures / "probes" / run_date.isoformat()
    if pd.is_dir():
        for f in sorted(pd.glob("*.jsonl")):
            for line in f.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    doc = json.loads(line)
                except ValueError:
                    continue
                if doc.get("service") == "sig-api-health":
                    probes.append(doc)
    g.probes = sorted(probes, key=lambda d: str(d.get("ts", "")))

    db = _load_json(fixtures / "db.json")
    if isinstance(db, dict):
        g.completions = list(db.get("completions") or [])
        g.counters = dict(db.get("counters") or {})
        g.claim_counts = dict(db.get("claim_counts") or {})
        g.completions_queried = "completions" in db
        g.counters_queried = "counters" in db

    mon = _load_json(fixtures / "monitoring.json") or {}
    g.monitoring = {m: list((mon.get(m) or {}).get("points") or []) for m in MONITORING_METRICS}
    return g


# ---------------------------------------------------------------------------
# Criterion evaluation


def _points_in(
    points: Sequence[dict], start: datetime, end: datetime
) -> list[tuple[datetime, float]]:
    out = []
    for p in points:
        t = _parse_ts(p.get("time"))
        v = p.get("value")
        if t is None or v is None:
            continue
        if start - timedelta(minutes=5) <= _utc(t) <= end + timedelta(minutes=5):
            out.append((_utc(t), float(v)))
    return out


def evaluate(g: Gathered, ctx: dict) -> list[dict]:
    """The D-P31.4-1 + G1 §3.7 criteria over the gathered evidence."""
    members: list[str] = ctx["members"]
    fire: datetime = ctx["fire"]
    exec_sum: dict = ctx["execution"]
    osm_rows = g.run_rows.get(OSM_MEMBER, [])
    osm = osm_rows[-1] if osm_rows else None
    end = _parse_ts(exec_sum.get("completion")) or ctx.get("now") or fire
    start = _parse_ts(exec_sum.get("start")) or fire
    out: list[dict] = []

    def crit(cid: str, text: str, result: str, evidence: dict) -> None:
        out.append({"id": cid, "criterion": text, "result": result, "evidence": evidence})

    # 1. execution completed (the job-level verdict)
    if exec_sum.get("found"):
        ok = bool(exec_sum.get("completed_ok"))
        crit(
            "execution-completed",
            "the sig-ingest-camreg-batch-05 execution completes",
            "pass" if ok else "fail",
            exec_sum,
        )
    else:
        crit(
            "execution-completed",
            "the sig-ingest-camreg-batch-05 execution completes",
            "not_evaluable",
            {"reason": "no execution record at/after the fire"},
        )

    # 2. OSM run row exists
    if osm is None:
        crit(
            "osm-run-row",
            f"an ops/runs/{OSM_MEMBER} row exists on the run date",
            "fail",
            {"rows_found": 0},
        )
    else:
        crit(
            "osm-run-row",
            f"an ops/runs/{OSM_MEMBER} row exists on the run date",
            "pass",
            {"object": osm.get("_object"), "rows_found": len(osm_rows)},
        )

    # 3. outcome ok|partial
    if osm is None:
        crit("osm-outcome", "OSM run-row outcome is ok or partial", "not_evaluable", {})
    else:
        oc = osm.get("outcome")
        crit(
            "osm-outcome",
            "OSM run-row outcome is ok or partial",
            "pass" if oc in ("ok", "partial") else "fail",
            {
                "outcome": oc,
                "exit_code": osm.get("exit_code"),
                "refusal_reason": osm.get("refusal_reason"),
                "detail": osm.get("detail"),
            },
        )

    # 4. fetches 158 or fewer only with resumed entries
    if osm is None:
        crit(
            "osm-fetches", "fetches = 158, or fewer only with resumed entries", "not_evaluable", {}
        )
    else:
        fr = osm.get("fetch_record") or {}
        fetches = fr.get("fetches")
        if fetches is None:
            urls = fr.get("urls") or []
            fetches = len(urls) if urls else None
        resumed = list(fr.get("resumed") or [])
        resumed_n = len(resumed)
        if fetches == EXPECTED_OSM_FETCHES:
            res = "pass"
        elif fetches is not None and 0 <= int(fetches) < EXPECTED_OSM_FETCHES and resumed_n > 0:
            res = "pass"
        else:
            res = "fail"
        crit(
            "osm-fetches",
            "fetches = 158, or fewer only with resumed entries",
            res,
            {
                "fetches": fetches,
                "expected": EXPECTED_OSM_FETCHES,
                "resumed_entries": resumed_n,
                "resumed": resumed[:5],
                "logical_run": fr.get("logical_run"),
            },
        )

    # 5. claims_added ≈ 1.37M
    if osm is None:
        crit("osm-claims-added", "claims_added ≈ 1.37M", "not_evaluable", {})
    else:
        ca = osm.get("claims_added")
        lo = int(EXPECTED_OSM_CLAIMS * (1 - CLAIMS_TOLERANCE))
        hi = int(EXPECTED_OSM_CLAIMS * (1 + CLAIMS_TOLERANCE))
        res = "pass" if isinstance(ca, int) and lo <= ca <= hi else "fail"
        ev = {
            "claims_added": ca,
            "expected": EXPECTED_OSM_CLAIMS,
            "band": [lo, hi],
            "tolerance": CLAIMS_TOLERANCE,
        }
        if isinstance(ca, int) and ca > hi:
            ev["direction"] = "far_above"
        elif isinstance(ca, int) and ca < lo:
            ev["direction"] = "far_below"
        crit("osm-claims-added", "claims_added ≈ 1.37M", res, ev)

    # 6. ingest_run_completion for the run
    if not g.completions_queried:
        crit(
            "osm-completion",
            "an ingest_run_completion row exists for the run",
            "not_evaluable",
            {"reason": "the completion table was not read (DSN absent or query failed)"},
        )
    else:
        uri = osm.get("_object") if osm else None  # gs://… of the WORM row
        uri_base = uri.rsplit("/", 1)[-1] if uri else None
        run_id = osm.get("ingest_run_id") if osm else None

        def _uri_match(c: Mapping[str, Any]) -> bool:
            if not uri:
                return False
            for key in ("run_record_uri", "backfilled_from"):
                v = str(c.get(key) or "")
                # exact match, or the recorded fixture replay where the
                # completion names the same object basename under gs://…
                if v == uri or (uri_base and v.endswith("/" + uri_base)):
                    return True
            return False

        matches = [
            c for c in g.completions if (run_id and c.get("run_id") == run_id) or _uri_match(c)
        ]
        res = "pass" if matches else ("not_evaluable" if not osm else "fail")
        crit(
            "osm-completion",
            "an ingest_run_completion row exists for the run",
            res,
            {
                "matched": matches[:3],
                "completions_found": len(g.completions),
                "run_record_uri": uri,
                "ingest_run_id": run_id,
            },
        )

    # 7. duration well under 1h (G1 §3.7 / ADR-111 projection 12–15 min)
    if osm is None:
        crit("osm-duration", "the OSM member finishes well under 1 h", "not_evaluable", {})
    else:
        dur = osm.get("duration_seconds")
        res = (
            "pass" if (isinstance(dur, (int, float)) and dur < MEMBER_WELL_UNDER_HOUR_S) else "fail"
        )
        crit(
            "osm-duration",
            "the OSM member finishes well under 1 h (ADR-111 projected 12–15 min)",
            res,
            {
                "duration_seconds": dur,
                "budget_seconds": MEMBER_WELL_UNDER_HOUR_S,
                "execution_duration_seconds": exec_sum.get("duration_seconds"),
            },
        )

    # 8. every member has a run row
    missing = [m for m in members if not g.run_rows.get(m)]
    crit(
        "member-run-rows",
        f"all {len(members)} member run rows exist on the run date",
        "pass" if not missing else "fail",
        {
            "members": len(members),
            "missing": missing,
            "rows_per_member": {m: len(g.run_rows.get(m, [])) for m in members},
        },
    )

    # 9. append-only counters stay zero
    if not g.counters_queried:
        crit(
            "append-only-counters",
            "claim-table n_tup_upd / n_tup_del stay zero",
            "not_evaluable",
            {"reason": "the counter tables were not read (DSN absent or query failed)"},
        )
    else:
        bad = {t: c for t, c in g.counters.items() if c.get("n_tup_upd") or c.get("n_tup_del")}
        base_bad = {}
        if g.baseline and g.baseline.get("counters"):
            for t, c in g.counters.items():
                b = g.baseline["counters"].get(t) or {}
                du = int(c.get("n_tup_upd", 0)) - int(b.get("n_tup_upd", 0))
                dd = int(c.get("n_tup_del", 0)) - int(b.get("n_tup_del", 0))
                if du or dd:
                    base_bad[t] = {"upd_delta": du, "del_delta": dd}
        res = "pass" if not bad and not base_bad else "fail"
        crit(
            "append-only-counters",
            "claim-table n_tup_upd / n_tup_del stay zero",
            res,
            {"nonzero": bad, "baseline_deltas": base_bad, "counters": g.counters},
        )

    # 10. /health stays up — at most one transient not-ok probe row
    if not g.probes:
        crit(
            "api-health",
            "/health stays up — at most one transient 503",
            "not_evaluable",
            {
                "reason": "no sig-api-health probe rows on the run date",
                "note": "the probe sweeps every 6h; coverage between sweeps is unobserved",
            },
        )
    else:
        not_ok = [p for p in g.probes if not p.get("ok")]
        res = "pass" if len(not_ok) <= HEALTH_MAX_TRANSIENT_NOT_OK else "fail"
        crit(
            "api-health",
            "/health stays up — at most one transient 503",
            res,
            {
                "probe_rows": len(g.probes),
                "not_ok": len(not_ok),
                "not_ok_rows": not_ok[:3],
                "note": "probe cadence is 6h; the window between sweeps is unobserved",
            },
        )

    # 11. Cloud SQL memory < 90%
    mem = _points_in(g.monitoring.get(M_MEM_UTIL, []), start, end)
    if not mem:
        crit(
            "sql-memory",
            "Cloud SQL memory < 90% during the run",
            "not_evaluable",
            {"reason": f"no {M_MEM_UTIL} points in window"},
        )
    else:
        peak = max(v for _t, v in mem)
        crit(
            "sql-memory",
            "Cloud SQL memory < 90% during the run",
            "pass" if peak < MEM_UTIL_LIMIT else "fail",
            {"peak_utilization": peak, "points": len(mem)},
        )

    # 12. disk growth < 1 GiB
    disk = _points_in(g.monitoring.get(M_DISK_BYTES, []), start, end)
    base_disk = (g.baseline or {}).get("sql", {}).get("disk_bytes_used")
    if not disk and base_disk is None:
        crit(
            "sql-disk-growth",
            "disk grows < 1 GiB",
            "not_evaluable",
            {"reason": f"no {M_DISK_BYTES} points and no baseline"},
        )
    else:
        disk_hi: float | None = max((v for _t, v in disk), default=None)
        disk_lo: float | None = (
            float(base_disk)
            if base_disk is not None
            else (min(v for _t, v in disk) if disk else None)
        )
        growth = (disk_hi - disk_lo) if (disk_hi is not None and disk_lo is not None) else None
        crit(
            "sql-disk-growth",
            "disk grows < 1 GiB",
            "pass" if growth is not None and growth < DISK_GROWTH_LIMIT_BYTES else "fail",
            {
                "growth_bytes": growth,
                "baseline_bytes": base_disk,
                "window_high": disk_hi,
                "limit_bytes": DISK_GROWTH_LIMIT_BYTES,
            },
        )

    # 13. no Cloud SQL restart during the run (uptime monotonic within window)
    up = _points_in(g.monitoring.get(M_UPTIME, []), start, end)
    if not up:
        crit(
            "sql-no-restart",
            "no Cloud SQL restart during the run",
            "not_evaluable",
            {"reason": f"no {M_UPTIME} points in window"},
        )
    else:
        restarted = any(
            v < (t - fire).total_seconds() - 120 for t, v in up if (t - fire).total_seconds() > 0
        )
        crit(
            "sql-no-restart",
            "no Cloud SQL restart during the run",
            "fail" if restarted else "pass",
            {"uptime_points": len(up), "min_uptime_s": min(v for _t, v in up)},
        )

    return out


def overall_and_routing(
    criteria: Sequence[dict],
    *,
    exec_sum: dict,
    fire: datetime,
    now: datetime,
) -> tuple[str, str, list[str]]:
    """verdict, routing, triggers — the contract's AR-4 routing rules."""
    by_id = {c["id"]: c for c in criteria}
    triggers: list[str] = []

    # Execution-level timeout: finished but took >=36h, or still not finished
    # 36h after the fire.
    exec_dur = exec_sum.get("duration_seconds")
    if exec_dur is not None and exec_dur >= BATCH_TIMEOUT_S:
        triggers.append("execution ran to the 36h ceiling")
        return "fail", "deferral-row:execution-timeout", triggers
    if (
        exec_sum.get("found")
        and not exec_sum.get("finished")
        and (_utc(now) - _utc(fire)).total_seconds() >= BATCH_TIMEOUT_S
    ):
        triggers.append("execution still unfinished 36h after the fire")
        return "fail", "deferral-row:execution-timeout", triggers

    fails = [c["id"] for c in criteria if c["result"] == "fail"]
    if not fails:
        verdict = "pass" if all(c["result"] == "pass" for c in criteria) else "not_evaluable"
        return verdict, "none" if verdict == "pass" else "deferral-row", triggers

    # G1 §3.7 anomaly → "stop and preserve": clone PITR to T0 for comparison,
    # never UPDATE/DELETE the spine.  Triggered by non-zero update/delete
    # counters, claims_added far above ~1.37M, or a disk jump over 3 GB; the
    # deferral row names the operator decision (re-execute/cancel needs a go).
    if "append-only-counters" in fails:
        triggers.append("claim-table update/delete counters non-zero")
    ca = by_id.get("osm-claims-added", {})
    if ca.get("result") == "fail" and ca.get("evidence", {}).get("direction") == "far_above":
        triggers.append("claims_added far above ~1.37M")
    dg = by_id.get("sql-disk-growth", {})
    growth = dg.get("evidence", {}).get("growth_bytes")
    if dg.get("result") == "fail" and growth is not None and growth > ANOMALY_DISK_JUMP_BYTES:
        triggers.append("disk jump over 3 GB")
    if triggers:
        return "fail", "anomaly-stop-and-preserve", triggers

    # Over-1h-but-finished → record the ADR-107/ADR-111 revisit trigger (a).
    if fails == ["osm-duration"]:
        triggers.append("OSM member exceeded the 1h projection")
        return "fail", "adr-107-111-revisit", triggers

    return "fail", "deferral-row", [f"criteria failed: {', '.join(fails)}"]


# ---------------------------------------------------------------------------
# Report assembly


def build_report(
    *,
    batch: dict,
    run_date: date,
    now: datetime,
    gathered: Gathered,
    project: str | None,
    region: str | None,
) -> dict:
    cron = str(batch.get("cron"))
    fire = fire_time_for(cron, run_date)
    members = list(batch.get("members") or [])
    job = str(batch.get("job"))
    scheduler_name = str(batch.get("scheduler"))

    ex = pick_execution(gathered.executions, job, fire)
    exec_sum = execution_summary(ex)

    ctx = {"members": members, "fire": fire, "execution": exec_sum, "now": now}
    criteria = evaluate(gathered, ctx)
    verdict, routing, triggers = overall_and_routing(
        criteria, exec_sum=exec_sum, fire=fire, now=now
    )

    image = None
    job_doc: Mapping[str, Any] = gathered.job or {}
    try:
        image = job_doc["spec"]["template"]["spec"]["template"]["spec"]["containers"][0]["image"]
    except Exception:
        tpl = job_doc.get("template") or {}
        for c in tpl.get("template", {}).get("spec", {}).get("containers") or []:
            image = c.get("image")

    osm_rows = gathered.run_rows.get(OSM_MEMBER) or []
    osm: dict | None = osm_rows[-1] if osm_rows else None
    return {
        "kind": "sig.scheduled-readback/1",
        "generated_at": now.isoformat(),
        "obligation": "D-P31.4-1",
        "ticket": "P34.39a",
        "batch": batch.get("id"),
        "run_date": run_date.isoformat(),
        "fire_time": fire.isoformat(),
        "project": project,
        "region": region,
        "scheduler": {
            "name": scheduler_name,
            "state": (gathered.scheduler or {}).get("state"),
            "schedule": (gathered.scheduler or {}).get("schedule"),
            "scheduleTime": (gathered.scheduler or {}).get("scheduleTime"),
            "lastAttemptTime": (gathered.scheduler or {}).get("lastAttemptTime"),
        },
        "execution": exec_sum,
        "osm_run_row": {
            "object": (osm or {}).get("_object"),
            "outcome": (osm or {}).get("outcome"),
            "started_at": (osm or {}).get("started_at"),
            "duration_seconds": (osm or {}).get("duration_seconds"),
            "claims_added": (osm or {}).get("claims_added"),
            "fetch_record": (osm or {}).get("fetch_record"),
            "ingest_run_id": (osm or {}).get("ingest_run_id"),
            "capture_digests": len((osm or {}).get("capture_digests") or []),
        },
        "run_rows_per_member": {m: len(gathered.run_rows.get(m, [])) for m in members},
        "api_health": gathered.api_health,
        "claim_counts": gathered.claim_counts,
        "claim_counts_baseline": ((gathered.baseline or {}).get("claim_counts")),
        "completions_found": len(gathered.completions),
        "probes_found": len(gathered.probes),
        "image": image,
        "criteria": criteria,
        "verdict": verdict,
        "routing": routing,
        "triggers": triggers,
        "gather_errors": gathered.errors,
        "disclosures": [RESIGHTING_DISCLOSURE],
        "layer": "live",
        "read_only": True,
    }


def queued_report(
    *,
    batch: dict,
    run_date: date,
    now: datetime,
    scheduler: Mapping[str, Any] | None,
    execution: Mapping[str, Any] | None,
    failures: Sequence[str],
) -> dict:
    cron = str(batch.get("cron"))
    fire = fire_time_for(cron, run_date)
    return {
        "kind": "sig.scheduled-readback/1",
        "generated_at": now.isoformat(),
        "obligation": "D-P31.4-1",
        "ticket": "P34.39a",
        "batch": batch.get("id"),
        "run_date": run_date.isoformat(),
        "fire_time": fire.isoformat(),
        "guard": {
            "holds": False,
            "failures": list(failures),
            "fire": fire.isoformat(),
            "now": now.isoformat(),
        },
        "leg": {
            "status": "queued",
            "rerun_prompt": RERUN_PROMPT,
        },
        "scheduler": {
            "state": (scheduler or {}).get("state"),
            "scheduleTime": (scheduler or {}).get("scheduleTime"),
            "lastAttemptTime": (scheduler or {}).get("lastAttemptTime"),
        },
        "execution": execution_summary(execution),
        "read_only": True,
    }


# ---------------------------------------------------------------------------
# Live orchestration.  Every gather is a permitted READ (AR-5): gcloud
# describe/list, GCS list/download, monitoring timeseries, a read-only SQL
# transaction, one authenticated GET.  Nothing here executes, cancels, or
# writes.


def _batch_dict(batch: Any) -> dict:
    """Accept a ``BatchCadence`` or a plain mapping; return a plain dict."""
    if isinstance(batch, Mapping):
        return dict(batch)
    return {
        "id": batch.id,
        "cadence": getattr(batch, "cadence", None),
        "cron": batch.cron,
        "job": batch.job,
        "scheduler": batch.scheduler,
        "members": list(batch.members),
    }


def gather_live(
    *,
    batch: Any,
    run_date: date,
    fire: datetime,
    now: datetime,
    project: str,
    region: str,
    bucket_name: str | None,
    dsn: str | None,
    api_url: str | None,
    scheduler: Mapping[str, Any] | None = None,
    executions: Sequence[Mapping[str, Any]] | None = None,
    baseline_path: Path | None = None,
    gcloud: GcloudRunner = gcloud_cli,
    series: SeriesFn | None = None,
    health: HealthFn | None = None,
    query_factory: Callable[[str], QueryFn] | None = None,
    bucket_factory: Callable[[str], GcsBucket] | None = None,
) -> Gathered:
    """The live, read-only gather. Per-source failures are recorded, not hidden.

    ``scheduler``/``executions`` come pre-fetched by the guard — the same reads
    are reused rather than re-described, so the report and the guard judge the
    identical live records.
    """
    b = _batch_dict(batch)
    g = Gathered()
    g.scheduler = scheduler
    g.executions = list(executions or [])
    members = list(b["members"])
    job = str(b["job"])

    try:
        g.job = json.loads(
            gcloud(
                [
                    "run",
                    "jobs",
                    "describe",
                    job,
                    "--region",
                    region,
                    "--project",
                    project,
                    "--format",
                    "json",
                ]
            )
        )
    except Exception as e:  # noqa: BLE001 — recorded
        g.errors.append(f"job describe: {e}")

    ex = pick_execution(g.executions, job, fire)
    exec_sum = execution_summary(ex)
    start = _parse_ts(exec_sum.get("start")) or fire
    end = _parse_ts(exec_sum.get("completion")) or now
    end = min(_utc(end), _utc(now))
    win_start = _utc(start) - timedelta(minutes=30)
    win_end = end + timedelta(minutes=30)

    if baseline_path is not None and baseline_path.is_file():
        try:
            g.baseline = json.loads(baseline_path.read_text())
        except Exception as e:  # noqa: BLE001 — recorded
            g.errors.append(f"baseline read {baseline_path}: {e}")

    if bucket_name:
        bf = bucket_factory or GcsBucket
        try:
            bucket = bf(bucket_name)
        except Exception as e:  # noqa: BLE001 — recorded
            g.errors.append(f"gcs bucket: {e}")
        else:
            rows, errs = gather_run_rows_gcs(bucket, members, run_date)
            g.run_rows = rows
            g.errors.extend(errs)
            probes, errs = gather_probes_gcs(bucket, run_date)
            g.probes = probes
            g.errors.extend(errs)
    else:
        g.errors.append("no restricted bucket resolved — run rows / probes unread")

    if dsn:
        qf = query_factory or pg_query_factory
        try:
            query = qf(dsn)
        except Exception as e:  # noqa: BLE001 — recorded
            g.errors.append(f"db connect: {e}")
        else:
            try:
                g.counters = db_counters(query)
                g.counters_queried = True
            except Exception as e:  # noqa: BLE001 — recorded
                g.errors.append(f"pg_stat counters: {e}")
            try:
                g.completions = db_completions(query, fire - timedelta(days=1))
                g.completions_queried = True
            except Exception as e:  # noqa: BLE001 — recorded
                g.errors.append(f"ingest_run_completion: {e}")
            try:
                g.claim_counts = db_claim_counts(query, members)
            except Exception as e:  # noqa: BLE001 — recorded
                g.errors.append(f"claim counts: {e}")
    else:
        g.errors.append(
            "no read-only DSN provided — completion rows / claim-table "
            "counters / claim counts unread"
        )

    sf = series or monitoring_series_factory(project=project)
    for metric in MONITORING_METRICS:
        try:
            g.monitoring[metric] = sf(metric, win_start, win_end)
        except Exception as e:  # noqa: BLE001 — recorded
            g.errors.append(f"monitoring {metric}: {e}")

    if api_url:
        hf = health or api_health_factory()
        try:
            g.api_health = hf(api_url)
        except Exception as e:  # noqa: BLE001 — recorded
            g.errors.append(f"api health {api_url}: {e}")
    return g


def run_readback(
    *,
    batch: Any,
    run_date: date,
    now: datetime,
    project: str,
    region: str,
    bucket_name: str | None,
    dsn: str | None,
    api_url: str | None,
    baseline_path: Path | None = None,
    fixtures_dir: Path | None = None,
    gcloud: GcloudRunner = gcloud_cli,
    series: SeriesFn | None = None,
    health: HealthFn | None = None,
    query_factory: Callable[[str], QueryFn] | None = None,
    bucket_factory: Callable[[str], GcsBucket] | None = None,
) -> tuple[dict, int]:
    """Run the read-back; return ``(report, exit_code)``.

    The AR-4 clock guard runs first: before the fire, or before the trigger's
    ``lastAttemptTime`` and a finished execution exist, the leg is *queued*
    (exit ``READBACK_QUEUED``) with the verbatim re-run prompt — never a green
    verdict fabricated ahead of the fact.
    """
    b = _batch_dict(batch)
    fire = fire_time_for(str(b["cron"]), run_date)

    executions: list[Mapping[str, Any]] = []
    sched_err = exec_err = None
    if fixtures_dir is not None:
        gathered = gather_from_fixtures(fixtures_dir, list(b["members"]), run_date)
        scheduler = gathered.scheduler
        executions = gathered.executions
    else:
        gathered = Gathered()
        scheduler = None
        try:
            scheduler = json.loads(
                gcloud(
                    [
                        "scheduler",
                        "jobs",
                        "describe",
                        str(b["scheduler"]),
                        "--location",
                        region,
                        "--project",
                        project,
                        "--format",
                        "json",
                    ]
                )
            )
        except Exception as e:  # noqa: BLE001 — recorded
            sched_err = str(e)
        try:
            doc = json.loads(
                gcloud(
                    [
                        "run",
                        "jobs",
                        "executions",
                        "list",
                        "--job",
                        str(b["job"]),
                        "--region",
                        region,
                        "--project",
                        project,
                        "--format",
                        "json",
                        "--limit",
                        "30",
                    ]
                )
            )
            executions = list(doc) if isinstance(doc, list) else []
        except Exception as e:  # noqa: BLE001 — recorded
            exec_err = str(e)

    execution = pick_execution(executions, str(b["job"]), fire)
    failures = guard_failures(
        fire=fire,
        now=now,
        scheduler=scheduler,
        execution=execution,
        executions_error=exec_err,
        scheduler_error=sched_err,
    )
    if failures:
        return (
            queued_report(
                batch=b,
                run_date=run_date,
                now=now,
                scheduler=scheduler,
                execution=execution,
                failures=failures,
            ),
            READBACK_QUEUED,
        )

    if fixtures_dir is None:
        gathered = gather_live(
            batch=b,
            run_date=run_date,
            fire=fire,
            now=now,
            project=project,
            region=region,
            bucket_name=bucket_name,
            dsn=dsn,
            api_url=api_url,
            scheduler=scheduler,
            executions=executions,
            baseline_path=baseline_path,
            gcloud=gcloud,
            series=series,
            health=health,
            query_factory=query_factory,
            bucket_factory=bucket_factory,
        )
    report = build_report(
        batch=b,
        run_date=run_date,
        now=now,
        gathered=gathered,
        project=project,
        region=region,
    )
    # A fixture replay is never a live record (SIG-OPS honest layers).
    report["layer"] = "fixture" if fixtures_dir is not None else "live"
    return report, 0


def capture_baseline(
    *,
    batch: Any,
    run_date: date | None,
    now: datetime,
    project: str,
    region: str,
    dsn: str | None,
    api_url: str | None,
    gcloud: GcloudRunner = gcloud_cli,
    series: SeriesFn | None = None,
    health: HealthFn | None = None,
    query_factory: Callable[[str], QueryFn] | None = None,
) -> dict:
    """The pre-run baseline (D-P31.4-1's second bullet): the counters, the
    per-source claim counts, the disk/memory point, and a /health answer —
    taken while the replay has not yet run, so the read-back can say "grew"
    instead of only "is".  Read-only, like everything else here.
    """
    b = _batch_dict(batch)
    members = list(b["members"])
    doc: dict[str, Any] = {
        "kind": "sig.scheduled-readback-baseline/1",
        "taken_at": now.isoformat(),
        "ticket": "P34.39a",
        "obligation": "D-P31.4-1",
        "batch": b["id"],
        "run_date": run_date.isoformat() if run_date else None,
        "project": project,
        "region": region,
        "counters": {},
        "claim_counts": {},
        "claim_counts_method": (
            "claims credited to each member source through the evidence "
            "chain claim -> claim_evidence -> evidence_capture -> "
            "evidence_artifact.source_id (claim carries no source_id; the "
            "pre-P31.2 reuse-by-key runs fold several sources' executions "
            "into one ingest_run, so a run-level map mis-attributes them)"
        ),
        "claim_total": None,
        "sql": {},
        "api_health": None,
        "errors": [],
        "read_only": True,
    }
    try:
        sched = json.loads(
            gcloud(
                [
                    "scheduler",
                    "jobs",
                    "describe",
                    str(b["scheduler"]),
                    "--location",
                    region,
                    "--project",
                    project,
                    "--format",
                    "json",
                ]
            )
        )
        doc["scheduler"] = {
            "state": sched.get("state"),
            "schedule": sched.get("schedule"),
            "scheduleTime": sched.get("scheduleTime"),
            "lastAttemptTime": sched.get("lastAttemptTime"),
            "target_uri": (sched.get("httpTarget") or {}).get("uri"),
        }
    except Exception as e:  # noqa: BLE001 — recorded
        doc["errors"].append(f"scheduler describe: {e}")
    try:
        inst = json.loads(
            gcloud(
                [
                    "sql",
                    "instances",
                    "describe",
                    "sig-pg",
                    "--project",
                    project,
                    "--format",
                    "json",
                ]
            )
        )
        st = inst.get("settings", {})
        doc["sql_instance"] = {
            "state": inst.get("state"),
            "tier": st.get("tier"),
            "dataDiskSizeGb": st.get("dataDiskSizeGb"),
            "storageAutoResize": st.get("storageAutoResize"),
        }
    except Exception as e:  # noqa: BLE001 — recorded
        doc["errors"].append(f"sql instance describe: {e}")

    if dsn:
        qf = query_factory or pg_query_factory
        try:
            query = qf(dsn)
        except Exception as e:  # noqa: BLE001 — recorded
            doc["errors"].append(f"db connect: {e}")
        else:
            try:
                doc["counters"] = db_counters(query)
            except Exception as e:  # noqa: BLE001 — recorded
                doc["errors"].append(f"pg_stat counters: {e}")
            try:
                doc["claim_counts"] = db_claim_counts(query, members)
            except Exception as e:  # noqa: BLE001 — recorded
                doc["errors"].append(f"claim counts: {e}")
            try:
                doc["claim_total"] = db_claim_total(query)
            except Exception as e:  # noqa: BLE001 — recorded
                doc["errors"].append(f"claim total: {e}")
    else:
        doc["errors"].append("no read-only DSN provided — SQL baseline skipped")

    sf = series or monitoring_series_factory(project=project)
    win = timedelta(minutes=30)
    sql_stats: dict[str, Any] = {}
    for metric, key in (
        (M_DISK_BYTES, "disk_bytes_used"),
        (M_MEM_UTIL, "memory_utilization"),
    ):
        try:
            pts = sf(metric, now - win, now)
        except Exception as e:  # noqa: BLE001 — recorded
            doc["errors"].append(f"monitoring {metric}: {e}")
            continue
        vals = [p.get("value") for p in pts if p.get("value") is not None]
        if vals:
            sql_stats[key] = vals[-1]
            sql_stats[f"{key}_points"] = len(pts)
    doc["sql"] = sql_stats

    if api_url:
        hf = health or api_health_factory()
        try:
            doc["api_health"] = hf(api_url)
        except Exception as e:  # noqa: BLE001 — recorded
            doc["errors"].append(f"api health {api_url}: {e}")
    return doc
