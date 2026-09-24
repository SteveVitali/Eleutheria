# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Append-only ingest-run completion (P31.2 / ADR-109, D-P30.3-1).

``ingest_run`` has a nullable ``finished_at`` and a ``status`` that defaults to
``running``. Nothing ever closed a run, and closing one would be an ``UPDATE``,
which the spine forbids. So a finished execution is recorded as a **new**
``ingest_run_completion`` row (sqitch change ``ingest_run_completion``). This
module is the single INSERT for that table. Two writers use it: the live pipeline
(through :meth:`db.claim_sink.PgClaimSink.record_completion`) and the one-shot
WORM backfill (``ops.run_completion``).

Every write is ``INSERT … ON CONFLICT DO NOTHING``:

* a live completion is unique per ``run_id``, so a second call for the same run is +0;
* a backfilled completion is unique per ``backfilled_from`` (the gs:// run row), so
  re-running the backfill is +0.

``finished_at`` defaults to the **database clock**. Only the backfill passes it
explicitly, and then it is the WORM row's own ``started_at + duration_seconds``,
never a guess (§3.1).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

#: The completion status vocabulary (the table's CHECK constraint).
#: * ``ok``: the execution ran to the end, and every target yielded.
#: * ``partial``: it ran to the end, but some targets were recorded as
#:   disappearances, refusals or drift, or the request budget deferred a tail.
#: * ``quota_reached``: it stopped cleanly at a 429 quota wall (never re-probed).
#: * ``failed``: an exception ended it, and the process survived to record that.
COMPLETION_STATUSES = ("ok", "partial", "quota_reached", "failed")

#: Statuses that count as a *successful* run for freshness (SIG-METRIC-007). The
#: execution ended normally. ``failed`` never counts.
SUCCESSFUL_STATUSES = ("ok", "partial", "quota_reached")

_INSERT = (
    "INSERT INTO ingest_run_completion"
    "(run_id, source_id, status, finished_at, claims_considered, claims_inserted,"
    " claims_duplicate, run_record_uri, backfilled_from, detail) "
    "VALUES (%s, %s, %s, COALESCE(%s::timestamptz, clock_timestamp()), %s, %s, %s, %s, %s, %s) "
    "ON CONFLICT DO NOTHING RETURNING completion_id"
)


def append_completion(
    conn: Any,
    *,
    run_id: str,
    status: str,
    claims_inserted: int,
    source_id: str | None = None,
    finished_at: datetime | None = None,
    claims_considered: int | None = None,
    claims_duplicate: int | None = None,
    run_record_uri: str | None = None,
    backfilled_from: str | None = None,
    detail: str | None = None,
) -> str | None:
    """Append one completion row. Returns its id, or ``None`` if it already existed.

    ``conn`` is any psycopg connection or cursor with ``execute``. Validation runs
    before any SQL, so a bad status fails here with a clear message and never
    reaches the CHECK constraint.
    """
    if status not in COMPLETION_STATUSES:
        raise ValueError(f"completion status {status!r} is not one of {COMPLETION_STATUSES}")
    if claims_inserted < 0:
        raise ValueError(f"claims_inserted must be >= 0 (got {claims_inserted!r})")
    if backfilled_from is not None and not backfilled_from.startswith("gs://"):
        raise ValueError(f"backfilled_from must be a gs:// URI (got {backfilled_from!r})")
    row = conn.execute(
        _INSERT,
        (
            run_id,
            source_id,
            status,
            finished_at,
            claims_considered,
            claims_inserted,
            claims_duplicate,
            run_record_uri,
            backfilled_from,
            detail,
        ),
    ).fetchone()
    return None if row is None else str(row[0])


__all__ = ["COMPLETION_STATUSES", "SUCCESSFUL_STATUSES", "append_completion"]
