# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.1c — the hourly ``due`` dispatcher (G1-TRIM B-13=a, ticket 291a).

The consolidated trigger shape this module serves: ONE Cloud Scheduler trigger
(``[dispatcher].scheduler``, hourly) fires ONE Cloud Run job
(``[dispatcher].job``) which evaluates every ``[[sources]]``/``[[batches]]``
row in ``ops/cadence.toml`` against the window since the previous dispatch and
enqueues each due row's job through the Cloud Run ``jobs:run`` endpoint — the
same call the retired per-row triggers made. The per-row cadence declarations
stay the scheduler of record's data; consolidation changes the *trigger
shape*, never the declaration.

* **Due window** — between the last two dispatcher fires at-or-before ``now``
  (exclusive/inclusive): a row is due when its own cron's last fire falls in
  ``(window_open, window_close]``. Consecutive windows never overlap, so a row
  is dispatched once per fire; ``--since`` overrides the open edge for a
  recorded manual catch-up.
* **Skipped rows** — a ``state = "paused"`` row (the R6 declared-inert rows)
  is recorded skipped, never dispatched; a ``kept-declared-pin`` retire-list
  name (batch-05's deliberate D-P31.4-1 pin) keeps its own live trigger and is
  never dispatched either. ``kept-manual`` names are jobs, not rows — they
  never enter the due set.
* **The run row** — every evaluation appends one ``sig.dispatch-due/1`` record
  (``ops/runs/_dispatcher/…``, the same per-run timestamped WORM shape as
  every scheduled run): window, evaluated count, due set, enqueued executions
  (or ``would-execute`` markers under ``--dry-run``), skipped rows and any
  enqueue failures. A run that evaluated *no rows at all* fails — SIG-ENG-042:
  an empty evaluation is a defect, never a clean pass.

The executor is injectable — tests pass a fake and no socket opens. The live
path POSTs ``jobs:run`` with the job SA's token (``ops.gcs``'s provider:
metadata server → gcloud ADC → env override), needing no ``gcloud`` in the
image — the same shape ``live_diff.rest_json_opener`` uses for its reads.
"""

from __future__ import annotations

import json
import os
import tomllib
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .cadence_window import CronError, previous_fire
from .gcs import GcsBucket, default_token_provider
from .scheduled import CadenceConfig, RunRow, load_cadence, parse_cadence_doc

SCHEMA = "sig.dispatch-due/1"

#: The run-row ``source`` — under ``ops/runs/_dispatcher/`` like ``_live-diff``.
DISPATCH_SOURCE = "_dispatcher"


class DispatcherError(RuntimeError):
    """The declaration, the evaluation or an enqueue was unusable — exit 2."""


@dataclass(frozen=True)
class DueRow:
    """One cadence row the dispatcher will enqueue this window."""

    kind: str  # "source" | "batch"
    id: str
    job: str
    scheduler: str  # the row's (retired) trigger name — recorded, never fired here
    cron: str
    last_fire: str  # ISO UTC minute — the fire this dispatch stands in for


@dataclass(frozen=True)
class SkippedRow:
    """One cadence row evaluated but deliberately not dispatched."""

    kind: str
    id: str
    job: str
    scheduler: str
    reason: str  # "declared-paused" | "kept-declared-pin"


@dataclass(frozen=True)
class DueSet:
    """The evaluated due set for one dispatch instant."""

    window_open: str  # ISO UTC minute (exclusive)
    window_close: str  # ISO UTC minute (inclusive) — the dispatch's own fire
    window_open_source: str  # "dispatcher-cron" | "explicit-since"
    evaluated: int
    due: tuple[DueRow, ...]
    skipped: tuple[SkippedRow, ...]


def _minute(dt: datetime) -> datetime:
    return dt.astimezone(UTC).replace(second=0, microsecond=0)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%MZ")


def _parse_instant(text: str) -> datetime:
    """An ISO-8601 instant → aware UTC minute. Naive values read as UTC."""
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DispatcherError(f"unparseable instant {text!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return _minute(parsed)


def due_window(
    dispatcher_cron: str, now: datetime, *, since: datetime | None = None
) -> tuple[datetime, datetime]:
    """The ``(open, close]`` interval a dispatch at ``now`` covers.

    ``close`` is the dispatcher cron's last fire at-or-before ``now`` (this
    run stands in for it even when the job started late); ``open`` is the fire
    before that — so consecutive dispatches tile the timeline without overlap.
    ``since`` substitutes an explicit open edge for a recorded catch-up run.
    """
    close = previous_fire(dispatcher_cron, now)  # raises CronError — fail-closed
    if since is not None:
        return _minute(since), close
    open_ = previous_fire(dispatcher_cron, close - timedelta(minutes=1))
    return open_, close


def evaluate_due(
    config: CadenceConfig, *, now: datetime | None = None, since: datetime | None = None
) -> DueSet:
    """Compute the due set against ``now`` (default: the wall clock, UTC).

    Raises :class:`DispatcherError` when no ``[dispatcher]`` is declared, and
    :class:`~ops.cadence_window.CronError` when any evaluated row's cron is
    unparseable — a defect is a refusal, never a partial silent pass.
    """
    spec = config.dispatcher
    if spec is None:
        raise DispatcherError("ops/cadence.toml declares no [dispatcher] table")
    now = _minute(now or datetime.now(UTC))
    window_open, window_close = due_window(spec.cron, now, since=since)
    kept = {r.name for r in config.retire_triggers if r.disposition == "kept-declared-pin"}
    rows: list[tuple[str, str, str, str, str, str]] = [
        ("source", s.source, s.job, s.scheduler, s.cron, s.state) for s in config.sources
    ]
    rows += [("batch", b.id, b.job, b.scheduler, b.cron, b.state) for b in config.batches]
    due: list[DueRow] = []
    skipped: list[SkippedRow] = []
    for kind, rid, job, scheduler, cron, state in rows:
        if state == "paused":
            skipped.append(SkippedRow(kind, rid, job, scheduler, "declared-paused"))
            continue
        if scheduler in kept:
            skipped.append(SkippedRow(kind, rid, job, scheduler, "kept-declared-pin"))
            continue
        fire = previous_fire(cron, now)  # CronError propagates — fail-closed
        if window_open < fire <= window_close:
            due.append(DueRow(kind, rid, job, scheduler, cron, _iso(fire)))
    return DueSet(
        window_open=_iso(window_open),
        window_close=_iso(window_close),
        window_open_source="explicit-since" if since is not None else "dispatcher-cron",
        evaluated=len(rows),
        due=tuple(due),
        skipped=tuple(skipped),
    )


# ---------------------------------------------------------------------------
# The executor — injectable; the default POSTs the Cloud Run jobs:run endpoint
# (the same call a Cloud Scheduler trigger makes), needing no gcloud in-image.

Executor = Callable[[str], str]
Poster = Callable[[urllib.request.Request], Any]


def _default_poster(req: urllib.request.Request) -> Any:
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
        return json.loads(resp.read().decode() or "{}")


def rest_executor(
    project: str,
    region: str,
    *,
    token: Callable[[], str | None] | None = None,
    poster: Poster | None = None,
) -> Executor:
    """A job-name → execution-name executor over the Run v1 ``jobs:run`` API.

    ``token``/``poster`` are injectable (tests); the defaults resolve the job
    SA's token (metadata server → gcloud ADC → env override) and POST through
    urllib. A missing token or a non-2xx response raises — the failure is
    recorded on the run row, never swallowed.
    """
    provider = token or default_token_provider
    post = poster or _default_poster
    if not project:
        raise DispatcherError("rest executor needs a project (--project / SIG_GCP_PROJECT)")

    def execute(job: str) -> str:
        tok = provider()
        if not tok:
            raise DispatcherError(
                "no GCP access token (metadata server + gcloud ADC + "
                "SIG_GCS_ACCESS_TOKEN all absent) — the enqueue cannot run"
            )
        url = (
            f"https://{region}-run.googleapis.com/apis/run.googleapis.com/v1/"
            f"namespaces/{project}/jobs/{job}:run"
        )
        req = urllib.request.Request(
            url,
            data=b"{}",
            headers={
                "Authorization": f"Bearer {tok}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        body = post(req)
        meta = body.get("metadata", {}) if isinstance(body, dict) else {}
        return str(meta.get("name") or body.get("name") or "")

    return execute


# ---------------------------------------------------------------------------
# The declared-side loader — the published bundle first (SIG-OPS-005), the
# packaged/local cadence file otherwise.


def load_dispatcher_cadence(
    *,
    declared_source: str | None = None,
    cadence_file: str | None = None,
    bucket_factory: Callable[[str], GcsBucket] = GcsBucket,
) -> CadenceConfig:
    """Load the cadence the dispatcher evaluates.

    Order: explicit ``--declared`` → ``$SIG_OPS_DECLARED_GCS`` (the bundle the
    reconcile publishes — the in-image path, so a cadence change takes effect
    at the next reconcile without an image roll) → ``--cadence``/the packaged
    file. The bundle's ``cadence_toml`` member is parsed through the same
    ``parse_cadence_doc`` the repo file takes — identical declarations.
    """
    source = declared_source or os.environ.get("SIG_OPS_DECLARED_GCS", "").strip()
    if source:
        try:
            if source.startswith("gs://"):
                bucket, _, name = source[5:].partition("/")
                raw = bucket_factory(bucket).get_object(name)
            else:
                raw = Path(source).read_bytes()
            bundle = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
            if not isinstance(bundle, dict) or "cadence_toml" not in bundle:
                raise DispatcherError(
                    f"declaration bundle at {source} has no `cadence_toml` member"
                )
            return parse_cadence_doc(tomllib.loads(bundle["cadence_toml"]))
        except DispatcherError:
            raise
        except Exception as exc:  # noqa: BLE001 - any read failure fails closed
            raise DispatcherError(f"declaration bundle unreadable ({source}): {exc}") from exc
    try:
        return load_cadence(cadence_file)
    except (OSError, tomllib.TOMLDecodeError, KeyError, TypeError) as exc:
        raise DispatcherError(f"cadence unreadable: {exc}") from exc


# ---------------------------------------------------------------------------
# The dispatch — evaluate, enqueue, record.


def _payload(
    spec: Any,
    due_set: DueSet,
    *,
    execute: bool,
    enqueued: list[dict[str, Any]],
    failures: int,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "dispatcher": {
            "job": spec.job,
            "scheduler": spec.scheduler,
            "cron": spec.cron,
        },
        "window": {
            "open": due_set.window_open,
            "close": due_set.window_close,
            "open_source": due_set.window_open_source,
        },
        "evaluated": due_set.evaluated,
        "execute": execute,
        "due": [
            {
                "kind": d.kind,
                "id": d.id,
                "job": d.job,
                "scheduler": d.scheduler,
                "cron": d.cron,
                "last_fire": d.last_fire,
            }
            for d in due_set.due
        ],
        "enqueued": enqueued,
        "skipped": [
            {
                "kind": s.kind,
                "id": s.id,
                "job": s.job,
                "scheduler": s.scheduler,
                "reason": s.reason,
            }
            for s in due_set.skipped
        ],
        "enqueue_failures": failures,
    }


def dispatch_due(
    config: CadenceConfig,
    *,
    now: datetime | None = None,
    since: datetime | None = None,
    execute: bool = True,
    executor: Executor | None = None,
    project: str | None = None,
    region: str = "us-central1",
    started_at: str | None = None,
) -> tuple[RunRow, int]:
    """Evaluate the due set, enqueue each due job, and shape the run row.

    ``execute=False`` is the staging/operator dry-run: the evaluation and the
    run row are identical, but no job is invoked (each due row is recorded
    ``would-execute``). Enqueue failures are recorded per row and the run
    exits 1; a cadence defect (no dispatcher, unparseable cron, zero rows
    evaluated) exits 2 — SIG-ENG-042: an empty evaluation is never a pass.
    """
    started = started_at or datetime.now(UTC).isoformat()
    t0 = datetime.now(UTC)

    def _row(outcome: str, code: int, detail: str, fetch: dict[str, Any]) -> tuple[RunRow, int]:
        return (
            RunRow(
                kind="dispatch-due",
                source=DISPATCH_SOURCE,
                mode="live" if execute else "dry-run",
                outcome=outcome,
                exit_code=code,
                started_at=started,
                duration_seconds=(datetime.now(UTC) - t0).total_seconds(),
                detail=detail,
                fetch_record=fetch,
            ),
            code,
        )

    try:
        due_set = evaluate_due(config, now=now, since=since)
    except (DispatcherError, CronError) as exc:
        return _row(
            "error", 2, f"{type(exc).__name__}: {exc}", {"schema": SCHEMA, "error": str(exc)}
        )

    if due_set.evaluated == 0:
        # SIG-ENG-042: a dispatcher run that evaluated nothing fails — an empty
        # evaluation is a declaration defect, never a clean pass.
        return _row(
            "error",
            2,
            "evaluated 0 cadence rows — the due-set declaration is empty",
            _payload(config.dispatcher, due_set, execute=execute, enqueued=[], failures=0),
        )

    enqueued: list[dict[str, Any]] = []
    failures = 0
    if execute:
        try:
            run_one = executor or rest_executor(
                project or os.environ.get("SIG_GCP_PROJECT", "").strip(), region
            )
        except DispatcherError as exc:
            return _row(
                "error",
                2,
                f"{type(exc).__name__}: {exc}",
                _payload(config.dispatcher, due_set, execute=execute, enqueued=[], failures=0),
            )
        for d in due_set.due:
            entry: dict[str, Any] = {"kind": d.kind, "id": d.id, "job": d.job}
            try:
                entry["execution"] = run_one(d.job)
            except Exception as exc:  # noqa: BLE001 - the failure IS the record
                failures += 1
                entry["error"] = f"{type(exc).__name__}: {exc}"
            enqueued.append(entry)
    else:
        for d in due_set.due:
            enqueued.append({"kind": d.kind, "id": d.id, "job": d.job, "would_execute": True})

    outcome = "ok"
    code = 0
    if failures:
        outcome, code = "error", 1
    if not execute:
        outcome = "dry-run"
    detail = (
        f"{due_set.evaluated} evaluated, {len(due_set.due)} due, "
        f"{len(due_set.skipped)} skipped"
        + (f", {failures} enqueue failure(s)" if failures else "")
        + ("" if execute else " (dry-run — nothing executed)")
    )
    return _row(
        outcome,
        code,
        detail,
        _payload(
            config.dispatcher,
            due_set,
            execute=execute,
            enqueued=enqueued,
            failures=failures,
        ),
    )


__all__ = [
    "DISPATCH_SOURCE",
    "SCHEMA",
    "DispatcherError",
    "DueRow",
    "DueSet",
    "Executor",
    "SkippedRow",
    "dispatch_due",
    "due_window",
    "evaluate_due",
    "load_dispatcher_cadence",
    "rest_executor",
]
