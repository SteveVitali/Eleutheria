# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Scheduled live operations (P26.1 / OPS.2): probes, run-log, cadence.

What runs by hand today runs on a timer after this ticket: a Cloud Scheduler
trigger drives a ``sig-probe`` Cloud Run job every six hours, and a per-source
scheduler trigger drives each ``sig-ingest-<source>`` job on its recorded
cadence. Everything a scheduled run leaves is **WORM-shaped** — a per-run
timestamped object under ``gs://…-sig-restricted/ops/`` (the private bucket),
never a read-modify-write of a shared log:

* ``ops/probes/<YYYY-MM-DD>/<ts>.jsonl`` — one hosted-stack probe sweep
  (``probe-hosted``): the read API (root + ``/v1/coverage/okc``), the public
  ``sig-web`` service, the public export objects, and Cloud SQL reachability.
* ``ops/runs/<source>/<YYYY-MM-DD>/<ts>.json`` — one run row per scheduled
  reingestion (``scheduled-ingest``): source, mode, outcome, claims added,
  capture digests, refusal/disappearance records — the same honest record a
  manual ``sig-connectors run`` leaves, embedded as ``fetch_record``.

A DOWN/degraded probe target fires a recorded alert through the existing
``sig-alerts`` receiver seam (``ops.alerts`` — record-first, notify-second,
ADR-077); a refused reingestion is *recorded*, never retried into silence
(SIG-INGEST-012/013). The cadence choices themselves are data —
``ops/cadence.toml`` — operator-revisable config, not gates.

No host-specific value is baked into code: target URLs resolve from the
environment first (``SIG_PROBE_*`` / ``SIG_GCP_PROJECT``) and fall back to the
recorded deployment values in ``ops/cadence.toml`` (HG-12; the run.app URLs are
already committed in ``docs/build/reports/GCP_DEPLOYMENT.md``).
"""

from __future__ import annotations

import json
import os
import tomllib
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .alerts import scrub_secrets, utcnow
from .gcs import GcsBucket
from .observe import ProbeResult, _timed, http_ok, pg_ready

#: ``ops/cadence.toml`` next to ``src/`` — found in the repo checkout. In the
#: image the package lives in site-packages, so ``load_cadence`` also tries
#: ``./ops/cadence.toml`` relative to the CWD (the image's ``WORKDIR /app``
#: layout, ``COPY ops ./ops``). ``SIG_OPS_CADENCE`` overrides both.
DEFAULT_CADENCE_PATH = Path(__file__).resolve().parents[2] / "cadence.toml"

#: Prefixes under the PRIVATE restricted bucket (WORM per-run objects).
PROBE_PREFIX = "ops/probes"
RUN_PREFIX = "ops/runs"


# --- cadence config (ops/cadence.toml — data, not code) ------------------------


@dataclass(frozen=True)
class TargetSpec:
    """One hosted probe target as recorded in ``ops/cadence.toml``.

    ``url_env`` names an environment variable carrying the deployed base URL
    (run.app hostnames move with redeploys); ``path`` is appended to it.
    ``url`` is a recorded literal that may carry a ``{project}`` placeholder
    filled from ``SIG_GCP_PROJECT``. A target whose URL cannot be resolved is
    skipped — reported, never probed against a placeholder.
    """

    name: str
    kind: str  # "http" | "cloudsql"
    url: str = ""
    url_env: str = ""
    path: str = ""


@dataclass(frozen=True)
class SourceCadence:
    """One source's recorded reingestion cadence (``[[sources]]`` row).

    ``existing`` marks a scheduler trigger that already exists (muckrock,
    P25.7): the trigger is VERIFIED, never recreated — the run job itself is
    still upserted onto the ``scheduled-ingest`` wrapper so its executions
    append run rows like every other source. ``secrets`` carries extra
    Secret-Manager env bindings the job needs beyond ``sig-pg-password``
    (``ENV=secret-name`` pairs — names only, never values, HG-09).
    """

    source: str
    cadence: str  # "weekly" | "monthly" | ...
    cron: str
    job: str
    scheduler: str
    existing: bool = False  # scheduler trigger already applied — verify only
    secrets: tuple[str, ...] = ()
    note: str = ""


@dataclass(frozen=True)
class BatchCadence:
    """One grouped reingestion batch (``[[batches]]`` row, P26.16 / SOURCES.15).

    The GL-GATE-07 rights batch lands ~150 newly-green camera-registry
    sources; one Cloud Run job + scheduler per source would be unmanageable,
    so members run under a single ``sig-ingest-<batch>`` job —
    ``sig-ops scheduled-ingest --batch <id>`` iterates ``members`` in order
    and appends one ops/runs row PER MEMBER SOURCE (the per-source audit
    record is unchanged; batching only groups the job/scheduler count).
    """

    id: str
    cadence: str
    cron: str
    job: str
    scheduler: str
    members: tuple[str, ...]
    note: str = ""


@dataclass(frozen=True)
class CadenceConfig:
    """The parsed ``ops/cadence.toml``."""

    probe_job: str
    probe_scheduler: str
    probe_schedule: str
    probe_gcs_prefix: str
    probe_targets: tuple[TargetSpec, ...]
    runs_gcs_prefix: str
    sources: tuple[SourceCadence, ...]
    batches: tuple[BatchCadence, ...] = ()


def load_cadence(path: str | Path | None = None) -> CadenceConfig:
    """Parse ``ops/cadence.toml``.

    Resolution order: explicit ``path`` → ``$SIG_OPS_CADENCE`` → the file next
    to ``src/`` (repo checkout) → ``./ops/cadence.toml`` under the CWD (the
    image's ``WORKDIR /app`` layout). The first candidate that exists wins.
    """
    candidates: list[Path] = []
    if path:
        candidates.append(Path(path))
    env_path = os.environ.get("SIG_OPS_CADENCE", "").strip()
    if env_path:
        candidates.append(Path(env_path))
    candidates += [DEFAULT_CADENCE_PATH, Path.cwd() / "ops" / "cadence.toml"]
    resolved = next((c for c in candidates if c.is_file()), candidates[0])
    with resolved.open("rb") as fh:
        doc = tomllib.load(fh)
    probes = doc.get("probes", {})
    targets = tuple(
        TargetSpec(
            name=str(t["name"]),
            kind=str(t.get("kind", "http")),
            url=str(t.get("url", "")),
            url_env=str(t.get("url_env", "")),
            path=str(t.get("path", "")),
        )
        for t in probes.get("targets", [])
    )
    runs = doc.get("runs", {})
    sources = tuple(
        SourceCadence(
            source=str(s["id"]),
            cadence=str(s["cadence"]),
            cron=str(s["cron"]),
            job=str(s["job"]),
            scheduler=str(s["scheduler"]),
            existing=bool(s.get("existing", False)),
            secrets=tuple(f"{k}={v}" for k, v in dict(s.get("secrets", {})).items()),
            note=str(s.get("note", "")),
        )
        for s in doc.get("sources", [])
    )
    batches = tuple(
        BatchCadence(
            id=str(b["id"]),
            cadence=str(b["cadence"]),
            cron=str(b["cron"]),
            job=str(b["job"]),
            scheduler=str(b["scheduler"]),
            members=tuple(str(m) for m in b.get("members", [])),
            note=str(b.get("note", "")),
        )
        for b in doc.get("batches", [])
    )
    return CadenceConfig(
        probe_job=str(probes.get("job", "sig-probe")),
        probe_scheduler=str(probes.get("scheduler", "sig-sched-probe")),
        probe_schedule=str(probes.get("schedule", "0 */6 * * *")),
        probe_gcs_prefix=str(probes.get("gcs_prefix", PROBE_PREFIX)),
        probe_targets=targets,
        runs_gcs_prefix=str(runs.get("gcs_prefix", RUN_PREFIX)),
        sources=sources,
        batches=batches,
    )


def unscheduled_live_sources(config: CadenceConfig) -> list[str]:
    """Loadable sources WITH live targets missing from the cadence table.

    The drift check: a source that turns green and gains live targets but never
    gets a cadence row is a silent gap — surfaced here and pinned by tests.
    Batch membership counts as scheduled (P26.16): a ``[[batches]]`` member
    runs under its batch's ``sig-ingest-<id>`` job.
    """
    from connectors.live_targets import live_targets
    from connectors.loader import is_loadable
    from connectors.registry import sources as registry_sources

    scheduled = {s.source for s in config.sources}
    scheduled.update(m for b in config.batches for m in b.members)
    missing: list[str] = []
    for record in registry_sources():
        if is_loadable(record) and live_targets(record.id) and record.id not in scheduled:
            missing.append(record.id)
    return sorted(missing)


# --- hosted probe sweep --------------------------------------------------------


def hosted_pg_dsn(env: dict[str, str] | None = None) -> str | None:
    """The Cloud SQL reachability DSN, assembled from env parts (HG-09).

    ``SIG_PROBE_DSN`` wins; else the job's standard ``SIG_PG_*`` +
    ``SIG_CLOUDSQL_CONNECTION`` parts assemble the unix-socket DSN the ingest
    jobs use. ``None`` when no parts exist (a local run without credentials —
    the target is skipped, not probed against a default).
    """
    resolved = dict(os.environ) if env is None else env
    direct = resolved.get("SIG_PROBE_DSN", "").strip()
    if direct:
        return direct
    user = resolved.get("SIG_PG_USER", "").strip()
    db = resolved.get("SIG_PG_DB", "").strip()
    conn = resolved.get("SIG_CLOUDSQL_CONNECTION", "").strip()
    if not (user and db and conn):
        return None
    password = resolved.get("SIG_PG_PASSWORD", "").strip()
    return f"postgresql://{user}:{password}@/{db}?host=/cloudsql/{conn}"


def resolve_targets(
    config: CadenceConfig, env: dict[str, str] | None = None
) -> tuple[list[tuple[str, str]], list[str]]:
    """Resolve target specs to ``(name, url_or_dsn)`` pairs.

    Returns ``(resolved, skipped)`` — ``skipped`` names the specs whose URL
    could not be resolved (env unset), so the caller reports them rather than
    probing a placeholder.
    """
    resolved_env = dict(os.environ) if env is None else env
    project = resolved_env.get("SIG_GCP_PROJECT", "").strip()
    out: list[tuple[str, str]] = []
    skipped: list[str] = []
    for spec in config.probe_targets:
        if spec.kind == "cloudsql":
            dsn = hosted_pg_dsn(resolved_env)
            if dsn:
                out.append((spec.name, dsn))
            else:
                skipped.append(spec.name)
            continue
        url = ""
        if spec.url_env and resolved_env.get(spec.url_env, "").strip():
            url = resolved_env[spec.url_env].strip().rstrip("/") + spec.path
        elif spec.url:
            url = spec.url.replace("{project}", project) if project else spec.url
            if "{project}" in url:
                skipped.append(spec.name)
                continue
        if url:
            out.append((spec.name, url))
        else:
            skipped.append(spec.name)
    return out, skipped


def probe_hosted(
    targets: Sequence[tuple[str, str, str]],
    *,
    now: str | None = None,
    check_http: Callable[..., bool] | None = None,
    check_pg: Callable[[str], bool] | None = None,
    http_timeout: float | None = None,
) -> list[ProbeResult]:
    """Probe the hosted stack once — one :class:`ProbeResult` per target.

    ``targets`` are ``(name, kind, url_or_dsn)`` triples. The check callables are
    injectable so the sweep is deterministic in tests; the defaults are the same
    ``http_ok``/``pg_ready`` the local ``probe`` verb uses — one probe
    implementation, no drift between the local and hosted sweeps.

    ``http_timeout`` (default ``$SIG_PROBE_HTTP_TIMEOUT`` or 15s) applies only
    to the default ``http_ok`` check: the hosted surfaces scale to zero, so a
    sweep can legitimately hit a multi-second cold start — the local 3s budget
    would record a false DOWN on every first probe after idle (observed live
    2026-09-16: 3.03s/3.01s timeouts on a healthy API).
    """
    if check_http is None:
        timeout = http_timeout
        if timeout is None:
            timeout = float(os.environ.get("SIG_PROBE_HTTP_TIMEOUT", "15"))
        check_http = lambda u, _t=timeout: http_ok(u, timeout=_t)  # noqa: E731
    check_pg = check_pg or pg_ready
    ts = now or utcnow()
    results: list[ProbeResult] = []
    for name, kind, url in targets:
        check = (lambda u=url: check_pg(u)) if kind == "cloudsql" else (lambda u=url: check_http(u))
        ok, latency = _timed(check)
        results.append(
            ProbeResult(
                service=name,
                ok=ok,
                latency_ms=latency,
                ts=ts,
                detail="" if ok else "unreachable",
            )
        )
    return results


def sweep_object_name(prefix: str, ts: str) -> str:
    """The per-run WORM object name for a sweep: ``<prefix>/<date>/<ts>.jsonl``."""
    safe_ts = ts.replace(":", "-")
    return f"{prefix.rstrip('/')}/{ts[:10]}/{safe_ts}.jsonl"


def upload_sweep(bucket: GcsBucket, prefix: str, results: Sequence[ProbeResult], ts: str) -> str:
    """Write one sweep as a new timestamped JSONL object; return its name."""
    body = "".join(json.dumps(r.as_json(), sort_keys=True) + "\n" for r in results)
    return bucket.put_object(
        sweep_object_name(prefix, ts), body.encode("utf-8"), content_type="application/jsonl"
    )


# --- probe history -------------------------------------------------------------


@dataclass(frozen=True)
class TargetHistory:
    """The folded uptime summary for one probe target (``probe-history``)."""

    target: str
    probes: int
    ok: int
    uptime_pct: float | None  # None => no rows
    latest_ts: str
    latest_ok: bool | None
    p95_ms: float | None  # p95 latency over the last-N probes

    def as_json(self) -> dict[str, object]:
        return {
            "target": self.target,
            "probes": self.probes,
            "ok": self.ok,
            "uptime_pct": None if self.uptime_pct is None else round(self.uptime_pct, 2),
            "latest_ts": self.latest_ts,
            "latest_ok": self.latest_ok,
            "p95_ms": self.p95_ms,
        }


def percentile(values: Sequence[float], pct: float) -> float | None:
    """Nearest-rank percentile over ``values`` (None when empty)."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, round(pct / 100.0 * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def fold_probe_history(rows: Iterable[ProbeResult], *, last: int = 20) -> list[TargetHistory]:
    """Fold every stored sweep's rows into a per-target uptime summary.

    ``last`` bounds the latency window for the p95 — the most recent ``last``
    probes per target. No rows ⇒ ``uptime_pct=None`` / ``no-data`` honesty (§3.1:
    assert only what was measured).
    """
    by_target: dict[str, list[ProbeResult]] = {}
    for row in rows:
        by_target.setdefault(row.service, []).append(row)
    summaries: list[TargetHistory] = []
    for target in sorted(by_target):
        records = sorted(by_target[target], key=lambda r: r.ts)
        ok = sum(1 for r in records if r.ok)
        window = records[-last:] if last > 0 else records
        latest = records[-1]
        summaries.append(
            TargetHistory(
                target=target,
                probes=len(records),
                ok=ok,
                uptime_pct=ok / len(records) * 100.0,
                latest_ts=latest.ts,
                latest_ok=latest.ok,
                p95_ms=percentile([r.latency_ms for r in window], 95.0),
            )
        )
    return summaries


def read_sweep_rows(bucket: GcsBucket, prefix: str) -> list[ProbeResult]:
    """Download every stored sweep under ``prefix`` and flatten to probe rows."""
    rows: list[ProbeResult] = []
    for name in sorted(bucket.list_objects(prefix)):
        for line in bucket.get_object(name).decode("utf-8").splitlines():
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


# --- scheduled reingestion (the run-log) ---------------------------------------

#: Outcome vocabulary for a run row — mirrors the ``sig-connectors run`` exit
#: codes so a scheduled run's row says exactly what a manual run's output says.
RUN_OUTCOMES = (
    "ok",
    "gate_refused",
    "no_live_targets",
    "content_drift",
    "politeness_refusal",
    "error",
)


@dataclass(frozen=True)
class RunRow:
    """One scheduled-ingest outcome row — the audit record under ``ops/runs/``."""

    kind: str
    source: str
    mode: str
    outcome: str
    exit_code: int
    started_at: str
    duration_seconds: float
    claims_added: int = 0
    capture_digests: tuple[str, ...] = ()
    refusal_reason: str = ""
    detail: str = ""
    fetch_record: dict[str, Any] = field(default_factory=dict)

    def as_json(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "source": self.source,
            "mode": self.mode,
            "outcome": self.outcome,
            "exit_code": self.exit_code,
            "started_at": self.started_at,
            "duration_seconds": round(self.duration_seconds, 3),
            "claims_added": self.claims_added,
            "capture_digests": list(self.capture_digests),
            "refusal_reason": self.refusal_reason,
            "detail": self.detail,
            "fetch_record": self.fetch_record,
        }


def run_object_name(prefix: str, source: str, ts: str) -> str:
    """``<prefix>/<source>/<date>/<ts>.json`` — a new object per scheduled run."""
    safe_ts = ts.replace(":", "-")
    return f"{prefix.rstrip('/')}/{source}/{ts[:10]}/{safe_ts}.json"


def scheduled_ingest(
    source_id: str,
    *,
    sink_kind: str = "pg",
    dsn: str | None = None,
    capture_dir: Path | None = None,
    commit_chunk_size: int | None = None,
    runner: Callable[..., Any] | None = None,
    now: str | None = None,
) -> RunRow:
    """Run one source live through the gated connector and shape the run row.

    The wrapper NEVER bypasses the ingestion gate: it calls the same
    ``connectors.runner.run_source`` the manual CLI calls, so a non-green source
    is refused (``gate_refused``) before any socket is opened, and every refusal
    / drift / disappearance the runner records lands verbatim in the run row —
    scheduled runs record refusals exactly like manual ones.

    ``commit_chunk_size`` (PG sink) bounds the per-transaction claim count so a
    very-large source commits progressively (P26.18 / SOURCES.17); ``None`` uses
    the sink default (small sources commit in one chunk, unchanged behaviour).
    """
    if runner is None:
        from connectors.runner import RunMode, run_source

        def runner(source: str, **kw: Any) -> Any:  # type: ignore[misc]
            return run_source(source, mode=RunMode.LIVE, **kw)

    started = now or utcnow()
    t0 = datetime.now(UTC)
    outcome = "ok"
    exit_code = 0
    claims = 0
    digests: tuple[str, ...] = ()
    refusal = ""
    detail = ""
    fetch_record: dict[str, Any] = {}
    try:
        report = runner(
            source_id,
            sink_kind=sink_kind,
            dsn=dsn,
            capture_dir=capture_dir,
            commit_chunk_size=commit_chunk_size,
        )
        claims = len(report.claims)
        digests = tuple(str(c.digest) for c in report.captures if hasattr(c, "digest"))
        if report.fetch_record is not None:
            fetch_record = dict(report.fetch_record.to_dict())
        parts: list[str] = []
        # GL-GATE-08 / ADR-088: robots verdicts are recorded, never enforced —
        # a run that proceeded despite non-grant verdicts says so in detail.
        fr = report.fetch_record
        disregarded = list(getattr(fr, "robots_disregarded", None) or [])
        if disregarded:
            parts.append(
                f"{len(disregarded)} robots verdict(s) disregarded (recorded robots_disregarded)"
            )
        if report.refusals:
            parts.append(f"{len(report.refusals)} politeness refusal(s)")
        if report.disappearances:
            parts.append(f"{len(report.disappearances)} disappearance(s)")
        if getattr(report, "drifted", None):
            parts.append(f"{len(report.drifted)} document drift(s)")
        detail = "; ".join(parts)
    except Exception as exc:  # noqa: BLE001 - the outcome IS the exception class
        name = type(exc).__name__
        if name == "LiveGateRefused":
            outcome, exit_code = "gate_refused", 3
            refusal = "; ".join(str(r) for r in getattr(exc, "reasons", [str(exc)]))
        elif name == "NoLiveTargets":
            outcome, exit_code = "no_live_targets", 4
        elif name == "ContentDrift":
            outcome, exit_code = "content_drift", 5
            refusal = str(exc)
        elif name in ("RobotsUnretrievable", "RobotsDisallowed"):
            outcome, exit_code = "politeness_refusal", 6
            refusal = f"{name}: {exc}"
        else:
            outcome, exit_code = "error", 1
            detail = f"{name}: {exc}"
    duration = (datetime.now(UTC) - t0).total_seconds()
    return RunRow(
        kind="scheduled-ingest",
        source=source_id,
        mode="live",
        outcome=outcome,
        exit_code=exit_code,
        started_at=started,
        duration_seconds=duration,
        claims_added=claims,
        capture_digests=digests,
        refusal_reason=scrub_secrets(refusal),
        detail=scrub_secrets(detail),
        fetch_record=fetch_record,
    )


def store_run_row(
    row: RunRow,
    *,
    prefix: str = RUN_PREFIX,
    gcs: GcsBucket | None = None,
    local_dir: Path | None = None,
) -> dict[str, str]:
    """Persist a run row: local mirror + (when configured) the GCS object.

    Both destinations are per-run timestamped names — append-only. A GCS failure
    raises :class:`~ops.gcs.GcsError` to the caller (the job fails loud rather
    than losing the audit row), while the local mirror has already landed.
    Returns the written locations for the log line.
    """
    body = json.dumps(row.as_json(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    written: dict[str, str] = {}
    if local_dir is not None:
        safe_ts = row.started_at.replace(":", "-")
        path = local_dir / row.source / f"{safe_ts}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        written["local"] = str(path)
    if gcs is not None:
        name = run_object_name(prefix, row.source, row.started_at)
        gcs.put_object(name, body.encode("utf-8"), content_type="application/json")
        written["gcs"] = f"gs://{gcs.bucket}/{name}"
    return written


__all__ = [
    "DEFAULT_CADENCE_PATH",
    "PROBE_PREFIX",
    "RUN_OUTCOMES",
    "RUN_PREFIX",
    "BatchCadence",
    "CadenceConfig",
    "RunRow",
    "SourceCadence",
    "TargetHistory",
    "TargetSpec",
    "fold_probe_history",
    "hosted_pg_dsn",
    "load_cadence",
    "percentile",
    "probe_hosted",
    "read_sweep_rows",
    "resolve_targets",
    "run_object_name",
    "scheduled_ingest",
    "store_run_row",
    "sweep_object_name",
    "unscheduled_live_sources",
    "upload_sweep",
]
