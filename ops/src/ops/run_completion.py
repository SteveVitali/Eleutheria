# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The one-shot WORM backfill of ingest-run completions (P31.2 / ADR-109).

Before P31.2 nothing recorded how an ingest execution ended: every hosted
``ingest_run`` row is still ``running`` with ``finished_at`` NULL, so the public
freshness page says ``not-recorded`` for every source (D-P30.3-1). The executions
did finish, and each scheduled one left a write-once run row under
``gs://<project>-sig-restricted/ops/runs/<source>/<date>/<ts>.json``. This module
reads those rows and appends one ``ingest_run_completion`` per row it can **prove**,
labelled ``backfilled_from=<gs URI>``. It never rewrites ``ingest_run``.

Matching rules (deterministic; a row that fails any rule is recorded as unmatched
with its reason and is never guessed):

1. The row must describe an ingest execution. ``gate_refused`` and
   ``no_live_targets`` were refused before any write, so they are unmatched.
2. The connector is the run row's ``fetch_record.connector``, else the registry
   map (``connectors.runner.CONNECTOR_FOR_SOURCE``). No connector means unmatched.
3. Candidate runs are the non-replay ``ingest_run`` rows of that connector that
   had started by the row's finish. None means unmatched.
4. ``claims_inserted`` is counted from the spine: the claims that the candidate
   run established for that source, recorded inside the row's window
   ``[started_at, started_at + duration_seconds + 1 s]``. The 1 s allows for the
   row's whole-second ``started_at``.
5. A run is matched when exactly one candidate holds claims in the window. With
   no claims in the window, a ``scheduled-ingest`` execution that ended normally
   and handed claims to the sink (``claims_added > 0``) is matched only when
   exactly one candidate exists. Under the pre-P31.2 reuse-by-key that single
   run is the one it wrote through. Anything else is ambiguous, so unmatched.
   A ``failed`` execution with no claims in the window has no proof it touched a
   run, so it is unmatched.
6. Two rows of the same source whose windows overlap cannot be told apart, so
   both are unmatched.

``finished_at`` is the row's own ``started_at + duration_seconds``, never a
guess (§3.1). A row that an execution already completed *live* (its URI is a
live completion's ``run_record_uri``) is skipped. Every append is
``ON CONFLICT DO NOTHING`` on ``backfilled_from``, so a re-run is +0.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

#: Run-row outcomes that were refused before any spine write (not an execution).
NOT_EXECUTED_OUTCOMES = frozenset({"gate_refused", "no_live_targets"})

#: Run-row outcomes that mean the execution failed (the process survived to say so).
FAILED_OUTCOMES = frozenset({"error", "content_drift", "politeness_refusal"})

#: Tolerance on the window's end: ``started_at`` is whole seconds, the duration is not.
WINDOW_TOLERANCE = timedelta(seconds=1)


@dataclass(frozen=True)
class WormRunRow:
    """One ``ops/runs`` object, reduced to what the backfill needs."""

    uri: str
    source: str
    kind: str
    outcome: str
    started_at: datetime
    duration_seconds: float
    claims_added: int
    connector: str | None
    status: str | None  # the completion status, None when not an execution

    @property
    def finished_at(self) -> datetime:
        """The row's recorded finish: ``started_at + duration_seconds``."""
        return self.started_at + timedelta(seconds=self.duration_seconds)

    @property
    def window_end(self) -> datetime:
        return self.finished_at + WINDOW_TOLERANCE


@dataclass(frozen=True)
class RunCandidate:
    """One ``ingest_run`` row a WORM row might belong to."""

    run_id: str
    connector_name: str
    started_at: datetime
    is_replay: bool = False


@dataclass(frozen=True)
class Match:
    row: WormRunRow
    run_id: str
    claims_inserted: int
    basis: str  # why this run: "claims-in-window" | "sole-candidate"


@dataclass(frozen=True)
class Unmatched:
    uri: str
    source: str
    outcome: str
    reason: str


@dataclass
class BackfillPlan:
    matched: list[Match] = field(default_factory=list)
    unmatched: list[Unmatched] = field(default_factory=list)
    skipped_live: list[str] = field(default_factory=list)


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def completion_status_for(doc: Mapping[str, Any]) -> str | None:
    """Map a run row's outcome onto the completion vocabulary (None = not an execution).

    It mirrors ``connectors.pipeline.completion_status``: an ``ok`` run that
    recorded disappearances, refusals or drift, or whose budget deferred a tail,
    is ``partial``.
    """
    outcome = str(doc.get("outcome", ""))
    if outcome in NOT_EXECUTED_OUTCOMES:
        return None
    if outcome in FAILED_OUTCOMES:
        return "failed"
    if outcome == "quota_reached":
        return "quota_reached"
    if outcome == "ok":
        fr = doc.get("fetch_record") or {}
        if (
            fr.get("disappearances")
            or fr.get("refusals")
            or fr.get("document_drift")
            or fr.get("budget_reached")
        ):
            return "partial"
        return "ok"
    return None  # an outcome this code does not know: never guessed


def parse_run_row(
    uri: str, doc: Mapping[str, Any], *, connector_for_source: Mapping[str, str]
) -> WormRunRow:
    """Reduce one WORM run row to a :class:`WormRunRow`."""
    source = str(doc["source"])
    fr = doc.get("fetch_record") or {}
    connector = fr.get("connector") or connector_for_source.get(source)
    return WormRunRow(
        uri=uri,
        source=source,
        kind=str(doc.get("kind", "")),
        outcome=str(doc.get("outcome", "")),
        started_at=_parse_ts(str(doc["started_at"])),
        duration_seconds=float(doc.get("duration_seconds") or 0.0),
        claims_added=int(doc.get("claims_added") or 0),
        connector=str(connector) if connector else None,
        status=completion_status_for(doc),
    )


def candidate_runs(row: WormRunRow, runs: Sequence[RunCandidate]) -> list[RunCandidate]:
    """The non-replay runs of the row's connector that had started by its finish."""
    return [
        r
        for r in runs
        if row.connector is not None
        and r.connector_name == row.connector
        and not r.is_replay
        and r.started_at <= row.window_end
    ]


def _overlapping(rows: Sequence[WormRunRow]) -> set[str]:
    """URIs of rows whose same-source windows overlap (indistinguishable)."""
    by_source: dict[str, list[WormRunRow]] = {}
    for r in rows:
        by_source.setdefault(r.source, []).append(r)
    bad: set[str] = set()
    for group in by_source.values():
        group = sorted(group, key=lambda r: r.started_at)
        # Compare each row with the widest window seen so far, not only its
        # neighbour: a short row nested inside a long one is still ambiguous.
        widest: WormRunRow | None = None
        for row in group:
            if widest is not None and row.started_at <= widest.window_end:
                bad.update({widest.uri, row.uri})
            if widest is None or row.window_end > widest.window_end:
                widest = row
    return bad


def plan_backfill(
    rows: Sequence[WormRunRow],
    runs: Sequence[RunCandidate],
    inserted: Mapping[tuple[str, str], int],
    *,
    live_uris: Iterable[str] = (),
) -> BackfillPlan:
    """Decide, per row, the run it completes or why it cannot be matched (pure).

    ``inserted`` maps ``(row uri, run_id)`` to the claims that run established for
    the row's source inside the row's window (see :func:`count_inserted_in_windows`).
    """
    plan = BackfillPlan()
    live = set(live_uris)
    overlapping = _overlapping([r for r in rows if r.status is not None])
    for row in sorted(rows, key=lambda r: (r.source, r.started_at, r.uri)):
        if row.uri in live:
            plan.skipped_live.append(row.uri)
            continue

        def miss(reason: str, row: WormRunRow = row) -> None:
            plan.unmatched.append(Unmatched(row.uri, row.source, row.outcome, reason))

        if row.status is None:
            miss(f"outcome {row.outcome!r} is not an ingest execution (nothing was written)")
            continue
        if row.connector is None:
            miss("no connector is known for this source")
            continue
        if row.uri in overlapping:
            miss("its window overlaps another run row of the same source (ambiguous)")
            continue
        cands = candidate_runs(row, runs)
        if not cands:
            miss(f"no ingest_run of connector {row.connector!r} had started by the row's finish")
            continue
        with_claims = [(c, inserted.get((row.uri, c.run_id), 0)) for c in cands]
        proven = [(c, n) for c, n in with_claims if n > 0]
        if len(proven) == 1:
            run, n = proven[0]
            plan.matched.append(Match(row, run.run_id, n, "claims-in-window"))
            continue
        if len(proven) > 1:
            miss(f"{len(proven)} candidate runs hold claims in the window (ambiguous)")
            continue
        # No claim of this source was recorded in the window.
        if row.status == "failed":
            miss("failed with no claim recorded in its window: no proof it touched a run")
            continue
        if row.kind != "scheduled-ingest" or row.claims_added <= 0:
            miss("no claim recorded in its window and no claim handed to the sink")
            continue
        if len(cands) != 1:
            miss(f"{len(cands)} candidate runs and no claim in the window (ambiguous)")
            continue
        plan.matched.append(Match(row, cands[0].run_id, 0, "sole-candidate"))
    return plan


# --- the spine side (psycopg; read + append) -------------------------------------

_RUNS_SQL = "SELECT run_id::text, connector_name, started_at, is_replay FROM ingest_run"

_LIVE_URIS_SQL = (
    "SELECT run_record_uri FROM ingest_run_completion"
    " WHERE backfilled_from IS NULL AND run_record_uri IS NOT NULL"
)

#: Claims each (row, candidate run) pair established for the row's source inside the
#: row's window, in ONE set-based statement (hash joins over the spine, no per-row scan).
_INSERTED_SQL = (
    "WITH w AS ("
    "  SELECT * FROM unnest(%s::text[], %s::text[], %s::uuid[],"
    "                       %s::timestamptz[], %s::timestamptz[])"
    "         AS w(uri, source_id, run_id, s, f)"
    "), pairs AS (SELECT DISTINCT source_id, run_id FROM w"
    "), caps AS ("
    "  SELECT ec.capture_id, p.source_id, p.run_id"
    "    FROM pairs p"
    "    JOIN evidence_artifact ea ON ea.source_id = p.source_id"
    "    JOIN evidence_capture ec"
    "      ON ec.artifact_id = ea.artifact_id AND ec.retrieved_by_run_id = p.run_id"
    "), t AS ("
    "  SELECT caps.source_id, caps.run_id, c.claim_id, lower(c.sys_period) AS rec"
    "    FROM caps"
    "    JOIN claim_evidence ce ON ce.capture_id = caps.capture_id AND ce.role = 'establishes'"
    "    JOIN claim c ON c.claim_id = ce.claim_id AND c.ingest_run_id = caps.run_id"
    ") "
    "SELECT w.uri, w.run_id::text, count(DISTINCT t.claim_id)"
    "  FROM w LEFT JOIN t"
    "    ON t.source_id = w.source_id AND t.run_id = w.run_id AND t.rec BETWEEN w.s AND w.f"
    " GROUP BY w.uri, w.run_id"
)


def load_runs(conn: Any) -> list[RunCandidate]:
    return [
        RunCandidate(str(r[0]), str(r[1]), r[2], bool(r[3]))
        for r in conn.execute(_RUNS_SQL).fetchall()
    ]


def load_live_uris(conn: Any) -> set[str]:
    """WORM URIs an execution already completed live (empty before the table exists,
    so a ``--dry-run`` can measure the plan ahead of the schema deploy)."""
    present = conn.execute("SELECT to_regclass('ingest_run_completion') IS NOT NULL").fetchone()
    if not (present and present[0]):
        return set()
    return {str(r[0]) for r in conn.execute(_LIVE_URIS_SQL).fetchall()}


def count_inserted_in_windows(
    conn: Any, rows: Sequence[WormRunRow], runs: Sequence[RunCandidate]
) -> dict[tuple[str, str], int]:
    """Count, for every (row, candidate run) pair, the claims established in the window."""
    uris: list[str] = []
    sources: list[str] = []
    run_ids: list[str] = []
    starts: list[datetime] = []
    ends: list[datetime] = []
    for row in rows:
        if row.status is None:
            continue
        for cand in candidate_runs(row, runs):
            uris.append(row.uri)
            sources.append(row.source)
            run_ids.append(cand.run_id)
            starts.append(row.started_at)
            ends.append(row.window_end)
    if not uris:
        return {}
    out: dict[tuple[str, str], int] = {}
    for uri, run_id, n in conn.execute(
        _INSERTED_SQL, (uris, sources, run_ids, starts, ends)
    ).fetchall():
        out[(str(uri), str(run_id))] = int(n)
    return out


@dataclass
class BackfillReport:
    """What one backfill invocation did (printed as JSON; the run's evidence)."""

    rows_read: int = 0
    matched: int = 0
    appended: int = 0
    already_present: int = 0
    skipped_live: int = 0
    unmatched: list[dict[str, str]] = field(default_factory=list)
    matched_by_status: dict[str, int] = field(default_factory=dict)
    matched_by_basis: dict[str, int] = field(default_factory=dict)
    dry_run: bool = False

    def as_json(self) -> dict[str, Any]:
        return {
            "rows_read": self.rows_read,
            "matched": self.matched,
            "appended": self.appended,
            "already_present": self.already_present,
            "skipped_live": self.skipped_live,
            "unmatched_count": len(self.unmatched),
            "unmatched": self.unmatched,
            "matched_by_status": dict(sorted(self.matched_by_status.items())),
            "matched_by_basis": dict(sorted(self.matched_by_basis.items())),
            "dry_run": self.dry_run,
        }


def read_worm_rows(
    bucket: Any, prefix: str, *, connector_for_source: Mapping[str, str]
) -> list[WormRunRow]:
    """Read every ``<prefix>/**.json`` run row from the bucket (``ops.gcs.GcsBucket``)."""
    rows: list[WormRunRow] = []
    for name in sorted(bucket.list_objects(prefix.rstrip("/") + "/")):
        if not name.endswith(".json"):
            continue
        doc = json.loads(bucket.get_object(name).decode("utf-8"))
        rows.append(
            parse_run_row(
                f"gs://{bucket.bucket}/{name}", doc, connector_for_source=connector_for_source
            )
        )
    return rows


def backfill_run_completions(
    conn: Any, rows: Sequence[WormRunRow], *, dry_run: bool = False
) -> BackfillReport:
    """Plan against the spine, then append the matched completions (unless ``dry_run``).

    ``conn`` is an autocommit psycopg connection (the role it runs as needs SELECT on
    the spine and INSERT on ``ingest_run_completion``, nothing more).
    """
    from db.run_completion import append_completion

    runs = load_runs(conn)
    plan = plan_backfill(
        rows,
        runs,
        count_inserted_in_windows(conn, rows, runs),
        live_uris=load_live_uris(conn),
    )
    report = BackfillReport(
        rows_read=len(rows),
        matched=len(plan.matched),
        skipped_live=len(plan.skipped_live),
        dry_run=dry_run,
        unmatched=[
            {"uri": u.uri, "source": u.source, "outcome": u.outcome, "reason": u.reason}
            for u in plan.unmatched
        ],
    )
    for m in plan.matched:
        status = m.row.status or "failed"
        report.matched_by_status[status] = report.matched_by_status.get(status, 0) + 1
        report.matched_by_basis[m.basis] = report.matched_by_basis.get(m.basis, 0) + 1
        if dry_run:
            continue
        new_id = append_completion(
            conn,
            run_id=m.run_id,
            source_id=m.row.source,
            status=status,
            finished_at=m.row.finished_at,
            claims_inserted=m.claims_inserted,
            run_record_uri=m.row.uri,
            backfilled_from=m.row.uri,
            detail=f"backfilled from WORM run row ({m.basis}; outcome {m.row.outcome})",
        )
        if new_id is None:
            report.already_present += 1
        else:
            report.appended += 1
    return report


__all__ = [
    "FAILED_OUTCOMES",
    "NOT_EXECUTED_OUTCOMES",
    "BackfillPlan",
    "BackfillReport",
    "Match",
    "RunCandidate",
    "Unmatched",
    "WormRunRow",
    "backfill_run_completions",
    "candidate_runs",
    "completion_status_for",
    "count_inserted_in_windows",
    "load_live_uris",
    "load_runs",
    "parse_run_row",
    "plan_backfill",
    "read_worm_rows",
]
