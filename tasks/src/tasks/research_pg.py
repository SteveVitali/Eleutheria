# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Persist the detector-run research queue over the spine (P29.2, the DB glue).

:mod:`tasks.detect` is pure; this module is the Postgres edge. It **reads** the Round-6
materialized graph through the built read seams (never re-querying the spine itself) and
**writes** the research queue as durable ``research_task`` rows:

* **Read (reuse, degrade honestly).** :func:`read_materialized_inputs` consumes
  ``reconcile.materialize.read_materialized_{contradictions,edges}`` and
  ``inference.materialize.read_materialized_coverage`` inside the caller's transaction. Each
  is guarded by the materializer's ``input_digest`` column exactly as
  ``exports.spine_export`` guards its reads — a spine whose Round-6 materializations have not
  run degrades to an empty queue (no fabricated task, D-R6.x live gate).
* **Write (append-only, idempotent).** :func:`materialize_research_queue` runs the detector
  catalog (:func:`tasks.detect.run_detectors`) and INSERTs each queued task into
  ``research_task`` with ``ON CONFLICT (task_type, subject_id) DO NOTHING`` — the SIG-TASK-007
  dedup index is the idempotency contract, so a re-run over an unchanged spine is +0. Every
  written row **cites its trigger** (``trigger_kind``/``trigger_ref``). A subject that is not a
  resolved entity is skipped honestly (the ``research_task.subject_id`` foreign key binds).

Records requests are **DRAFT, NEVER SENT** (see :mod:`tasks.detect`): the drafts ride along in
the summary/artifact; nothing here transmits one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from inference.materialize import read_materialized_coverage
from reconcile.materialize import (
    read_materialized_contradictions,
    read_materialized_edges,
)

from .detect import (
    DetectorRunResult,
    JurisdictionInfo,
    MaterializedInputs,
    RecordsRequestDraft,
    run_detectors,
)
from .lifecycle import RateLimiter, ResearchTask

__all__ = [
    "CLOSING_CONDITION_TEXT",
    "ResearchQueueSummary",
    "read_materialized_inputs",
    "materialize_research_queue",
    "materialize_research_queue_from_dsn",
]

#: The testable closing-condition text stamped onto each persisted ``research_task`` row
#: (``research_task.closing_condition`` NOT NULL, SIG-TASK-002). Keyed by the catalog slug the
#: detector run generates; a slug not listed falls back to the generic auto-invalidation text
#: (SIG-TASK-006: the closing condition and auto-invalidation are two views of one fact).
CLOSING_CONDITION_TEXT: dict[str, str] = {
    "conflicting_retention": (
        "the authoritative record establishes the retention period and the policy/configuration "
        "divergence is reconciled"
    ),
    "missing_physical_devices": (
        "the mapped device count reconciles with the evidenced active count"
    ),
    "missing_contract": (
        "the procurement record (contract/purchase order) for the deployment is on file"
    ),
    "coverage_hole": (
        "evidence for the jurisdiction is obtained, OR a CoverageRecord records the searched "
        "absence"
    ),
    "unmapped_vocabulary_value": "the source value is mapped into the controlled vocabulary",
    "sharing_asymmetry": (
        "the one-sided sharing edge is corroborated by the other party, or retracted"
    ),
    "canceled_but_installed": "the canceled-yet-installed lifecycle contradiction is resolved",
    "candidate_duplicate_entities": (
        "the ER tier-4/5 candidate pair is adjudicated (merged or split)"
    ),
    "sole_source_tier_f_support": (
        "independent higher-reliability support for the claim is established"
    ),
    "sharing_snapshot_stale": (
        "a fresh configured-access observation (within the FAST volatility window) is captured"
    ),
}
_GENERIC_CLOSING_CONDITION = (
    "the generating detector no longer fires for the subject — the evidence resolving the gap "
    "has landed (auto-invalidation, SIG-TASK-006)"
)


@dataclass
class ResearchQueueSummary:
    """The result of materializing the research queue (the CLI/JSON summary)."""

    detector: dict[str, object] = field(default_factory=dict)
    generated: int = 0
    written: int = 0
    skipped_existing: int = 0
    skipped_no_entity: int = 0
    records_request_drafts: int = 0
    records_requests_sent: int = 0  # always 0 — sending is operator-gated (never auto)

    def as_dict(self) -> dict[str, object]:
        return {
            "generated": self.generated,
            "written": self.written,
            "skipped_existing": self.skipped_existing,
            "skipped_no_entity": self.skipped_no_entity,
            "records_request_drafts": self.records_request_drafts,
            "records_requests_sent": self.records_requests_sent,
            "detector": self.detector,
        }


def _has_input_digest(conn: Any, table: str) -> bool:
    """True iff ``table`` exists and carries the materializer's ``input_digest`` column.

    The same guard ``exports.spine_export`` uses: a pre-Round-6 spine lacks the column, so the
    read is skipped and the input degrades to empty (honest absence, never a crash).
    """
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        " WHERE table_name = %s AND column_name = 'input_digest' LIMIT 1",
        (table,),
    ).fetchone()
    return bool(row)


def read_materialized_inputs(conn: Any, *, role: str | None = None) -> MaterializedInputs:
    """Read the Round-6 materialized detector outputs (contradictions/coverage/edges).

    Reuses the built read seams, each guarded by its ``input_digest`` column and wrapped so a
    schema mismatch is honest absence (``[]``). Read-only.
    """
    if role:
        conn.execute(f"SET ROLE {role}")

    def _read(table: str, seam: Any) -> list[dict[str, Any]]:
        if not _has_input_digest(conn, table):
            return []
        try:
            return list(seam(conn))
        except Exception:  # noqa: BLE001 - a schema-shape mismatch is honest absence
            return []

    return MaterializedInputs(
        contradictions=_read("contradiction", read_materialized_contradictions),
        coverage=_read("coverage_record", read_materialized_coverage),
        edges=_read("relationship", read_materialized_edges),
    )


def _entity_label(conn: Any, entity_id: str | None) -> str | None:
    """A human label for an entity (its identifier value), or ``None``."""
    if not entity_id:
        return None
    try:
        row = conn.execute(
            "SELECT value FROM entity_identifier WHERE entity_id = %s ORDER BY scheme LIMIT 1",
            (entity_id,),
        ).fetchone()
    except Exception:  # noqa: BLE001
        return None
    return str(row[0]) if row and row[0] else None


def _entity_exists(conn: Any, entity_id: str | None) -> bool:
    if not entity_id:
        return False
    try:
        row = conn.execute("SELECT 1 FROM entity WHERE entity_id = %s", (entity_id,)).fetchone()
    except Exception:  # noqa: BLE001 - a non-uuid subject cannot be an entity
        return False
    return bool(row)


def _make_resolver(conn: Any, *, jurisdiction_key: str | None) -> Any:
    """A §36 jurisdiction resolver for records-request drafts (see :mod:`tasks.detect`).

    When ``jurisdiction_key`` is given (the CLI ``--jurisdiction`` state code), every
    records-oriented task in that spine routes to that jurisdiction's statute, naming the
    subject entity as the target agency. Without it, no draft is made (honest: the loop cannot
    guess a jurisdiction's records law).
    """
    if not jurisdiction_key:
        return None

    def resolver(subject_id: str | None, task_jurisdiction: str | None) -> JurisdictionInfo | None:
        agency = (
            _entity_label(conn, task_jurisdiction)
            or _entity_label(conn, subject_id)
            or "the responsive agency"
        )
        return JurisdictionInfo(records_law_key=jurisdiction_key, target_agency=agency)

    return resolver


def _insert_task(conn: Any, task: ResearchTask) -> bool:
    """INSERT one queued task, append-only + deduped. Returns True iff a row was written."""
    closing = CLOSING_CONDITION_TEXT.get(task.task_type, _GENERIC_CLOSING_CONDITION)
    row = conn.execute(
        "INSERT INTO research_task "
        "  (task_type, subject_id, jurisdiction_id, priority, status, closing_condition, "
        "   detector_version, trigger_kind, trigger_ref) "
        "VALUES (%s, %s, %s, %s, 'generated', %s, %s, %s, %s) "
        "ON CONFLICT (task_type, subject_id) DO NOTHING "
        "RETURNING task_id",
        (
            task.task_type,
            task.subject_id,
            task.jurisdiction_id,
            task.priority,
            closing,
            task.detector_version,
            task.trigger_kind,
            task.trigger_ref,
        ),
    ).fetchone()
    return bool(row)


def materialize_research_queue(
    conn: Any,
    *,
    now: datetime | None = None,
    role: str | None = None,
    jurisdiction_key: str | None = None,
    rate_limiter: RateLimiter | None = None,
) -> tuple[ResearchQueueSummary, DetectorRunResult]:
    """Run the detector catalog over the materialized spine and persist the research queue.

    Reads the materialized graph, runs :func:`tasks.detect.run_detectors`, and INSERTs each
    queued task into ``research_task`` (append-only; ``ON CONFLICT (task_type, subject_id) DO
    NOTHING`` → idempotent +0). A subject that is not a resolved entity is skipped (the FK
    binds). Records requests are drafted, never sent. Returns the summary and the full run
    result (whose ``.drafts`` the CLI writes as an artifact).
    """
    if role:
        conn.execute(f"SET ROLE {role}")
    now = now or datetime.now(UTC)
    inputs = read_materialized_inputs(conn)
    resolver = _make_resolver(conn, jurisdiction_key=jurisdiction_key)
    result = run_detectors(
        inputs, now=now, rate_limiter=rate_limiter, jurisdiction_resolver=resolver
    )

    summary = ResearchQueueSummary(
        detector=result.summary.as_dict(),
        generated=result.summary.generated,
        records_request_drafts=len(result.drafts),
    )
    for task in result.queue:
        if not _entity_exists(conn, task.subject_id):
            summary.skipped_no_entity += 1
            continue
        if _insert_task(conn, task):
            summary.written += 1
        else:
            summary.skipped_existing += 1
    return summary, result


def materialize_research_queue_from_dsn(
    dsn: str, **kwargs: Any
) -> tuple[ResearchQueueSummary, list[RecordsRequestDraft]]:
    """Open an autocommit connection from ``dsn`` and materialize the research queue (CLI)."""
    import psycopg  # available via the sig-db dependency (driver stays in `db`)

    conn = psycopg.connect(dsn, autocommit=True)
    try:
        summary, result = materialize_research_queue(conn, **kwargs)
        return summary, result.drafts
    finally:
        conn.close()
