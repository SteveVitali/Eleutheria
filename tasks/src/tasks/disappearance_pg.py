# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Persist connector-observed disappearances on the spine (§17.6; P37.5b).

:mod:`connectors.disappearance` produces the two first-class rows a
disappearance is — an artifact event (``disappeared_observed_at`` + the failing
``capture_status``) and a ``research_task`` (SIG-INGEST-009/010,
SIG-EVID-013/014). Until this module, those rows lived only in the run's
``FetchRecord`` JSON: ``disappeared_observed_at`` had no writer and the task
half was dropped on the floor of the report serializer. This is the DB glue —
the same posture :mod:`tasks.research_pg` takes for the detector queue.

* **The event lands on the artifact's event columns, never a delete**
  (§17.6/C.3). ``capture_status`` tracks the latest failing status;
  ``disappeared_observed_at`` is **first-observation-wins** — an observation,
  once recorded, is never erased (``COALESCE``), so a re-check confirming the
  same disappearance is a +0 no-op and a later, different failure still updates
  the status. The write is the ONE designed UPDATE surface on
  ``evidence_artifact``: the sqitch ``disappearance_event_grant`` change grants
  ``sig_ingest`` ``UPDATE`` on **those two columns only** — every other column
  and DELETE stay un-granted, so the append-only posture holds inside the grant
  itself.
* **The task is append-only + idempotent** (SIG-TASK-007): an entity-resolved
  subject dedups on ``UNIQUE (task_type, subject_id)`` via
  ``ON CONFLICT DO NOTHING``; a subject that has not resolved to an entity is
  still recorded — ``subject_id`` NULL, ``trigger_kind``/``trigger_ref`` citing
  the artifact + subject string — deduped by a SELECT-first on the trigger pair
  (NULL never fires the unique index). A disappearance whose artifact is not in
  this spine is recorded honestly (``artifact_found: False``), never crashed —
  the sweep's record of "the URL went dark" outlives the row.
* **Queryable** (SIG-INGEST-010): :func:`disappeared_artifacts` is the read
  answering "which sources went dark" — the artifact rows carrying
  ``disappeared_observed_at`` plus their research-task link.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from connectors.disappearance import Disappearance

_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

#: ``trigger_kind`` for a research task a disappearance event generated —
#: ``trigger_ref`` carries the artifact ref (the evidence_artifact PK when
#: resolved, else the raw ref the observer recorded) so the task cites its
#: trigger (P29.2 trigger columns).
DISAPPEARANCE_TRIGGER = "artifact_disappearance"


@dataclass
class DisappearanceWrite:
    """The persistence outcome for one disappearance."""

    artifact_ref: str
    event_status: str = ""
    event_observed_at: Any = None
    artifact_found: bool = False
    artifact_id: str | None = None
    already_marked: bool = False
    event_applied: bool = False
    task_outcome: str = "unattempted"  # written | existing | unattempted

    def as_dict(self) -> dict[str, object]:
        return {
            "artifact_ref": self.artifact_ref,
            "artifact_found": self.artifact_found,
            "artifact_id": self.artifact_id,
            "already_marked": self.already_marked,
            "event_applied": self.event_applied,
            "task_outcome": self.task_outcome,
        }


@dataclass
class PersistSummary:
    """The batch result (the CLI/JSON summary; P29.2's shape)."""

    considered: int = 0
    events_applied: int = 0
    already_marked: int = 0
    unresolved_artifacts: int = 0
    tasks_written: int = 0
    tasks_existing: int = 0
    writes: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "considered": self.considered,
            "events_applied": self.events_applied,
            "already_marked": self.already_marked,
            "unresolved_artifacts": self.unresolved_artifacts,
            "tasks_written": self.tasks_written,
            "tasks_existing": self.tasks_existing,
            "writes": self.writes,
        }


def _resolve_artifact_id(conn: Any, artifact_ref: str) -> str | None:
    """Resolve a recorded artifact ref to an ``evidence_artifact`` PK.

    The connector boundary records whatever it observed — a target id, a
    locator, a URL, or the spine PK itself. A uuid resolves directly; any other
    ref matches ``stable_locator`` or ``url`` (the locators a capture carries).
    ``None`` = not in this spine — an honest miss, never a fabricated link.
    """
    if _UUID.match(artifact_ref):
        row = conn.execute(
            "SELECT artifact_id::text FROM evidence_artifact WHERE artifact_id = %s",
            (artifact_ref,),
        ).fetchone()
        return str(row[0]) if row else None
    row = conn.execute(
        "SELECT artifact_id::text FROM evidence_artifact "
        "WHERE stable_locator = %s OR url = %s "
        "ORDER BY artifact_id LIMIT 1",
        (artifact_ref, artifact_ref),
    ).fetchone()
    return str(row[0]) if row else None


def _resolve_subject(conn: Any, subject: object) -> str | None:
    """Resolve a task ``subject_id`` to an ``entity`` PK, or ``None``.

    A uuid resolves by the entity PK; a connector subject string resolves
    through the ``sig.connector.subject`` identity scheme (the same resolution
    the claim sink performs). Anything unresolved returns ``None`` — the task
    still lands (subjectless, citing its trigger), never dropped.
    """
    if subject is None:
        return None
    text = str(subject).strip()
    if not text:
        return None
    if _UUID.match(text):
        row = conn.execute(
            "SELECT entity_id::text FROM entity WHERE entity_id = %s", (text,)
        ).fetchone()
        return str(row[0]) if row else None
    row = conn.execute(
        "SELECT entity_id::text FROM entity_identifier "
        "WHERE scheme = 'sig.connector.subject' AND value = %s "
        "ORDER BY entity_id LIMIT 1",
        (text,),
    ).fetchone()
    return str(row[0]) if row else None


def insert_task_row(
    conn: Any,
    task: dict[str, Any],
    *,
    trigger_kind: str = DISAPPEARANCE_TRIGGER,
    trigger_ref: str = "",
) -> str:
    """INSERT one connector-emitted task row, append-only + deduped.

    Returns ``"written"`` or ``"existing"``. The task columns come from the row
    itself (``task_type``/``subject_id``/``priority``/``closing_condition``/
    ``detector_version``); ``status`` defaults ``generated``. Dedup is the
    ``UNIQUE (task_type, subject_id)`` contract for a resolved subject, and a
    SELECT-first on ``(task_type, trigger_kind, trigger_ref)`` for a subjectless
    one (NULL never fires the unique index). ``task_type`` and
    ``closing_condition`` are required — a task without a testable closing
    condition does not register (SIG-TASK-002) and this refuses ``ValueError``.
    """
    task_type = str(task.get("task_type", "")).strip()
    if not task_type:
        raise ValueError("a research_task row MUST carry task_type (SIG-TASK-002)")
    closing = str(task.get("closing_condition", "")).strip()
    if not closing:
        raise ValueError(
            f"research_task {task_type!r} has no closing_condition — a task "
            "without a testable close does not register (SIG-TASK-002)"
        )
    subject_entity = _resolve_subject(conn, task.get("subject_id"))
    subject_raw = task.get("subject_id")
    ref = trigger_ref or str(subject_raw or "")
    if subject_entity is not None:
        row = conn.execute(
            "INSERT INTO research_task "
            "(task_type, subject_id, priority, status, closing_condition, "
            " detector_version, trigger_kind, trigger_ref) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (task_type, subject_id) DO NOTHING RETURNING task_id",
            (
                task_type,
                subject_entity,
                task.get("priority", 0.5),
                str(task.get("status", "generated")),
                closing,
                str(task.get("detector_version", "connectors.disappearance/1")),
                trigger_kind,
                ref,
            ),
        ).fetchone()
        return "written" if row else "existing"
    # Subjectless: dedup on the trigger pair (NULL subject_id never fires the
    # unique index) — the SELECT-first is the idempotency seam, matching the
    # sink's own select-then-insert posture.
    seen = conn.execute(
        "SELECT 1 FROM research_task WHERE task_type = %s AND trigger_kind = %s "
        "AND trigger_ref = %s LIMIT 1",
        (task_type, trigger_kind, ref),
    ).fetchone()
    if seen:
        return "existing"
    conn.execute(
        "INSERT INTO research_task "
        "(task_type, subject_id, priority, status, closing_condition, "
        " detector_version, trigger_kind, trigger_ref) "
        "VALUES (%s, NULL, %s, %s, %s, %s, %s, %s)",
        (
            task_type,
            task.get("priority", 0.5),
            str(task.get("status", "generated")),
            closing,
            str(task.get("detector_version", "connectors.disappearance/1")),
            trigger_kind,
            ref,
        ),
    )
    return "written"


def apply_event_columns(conn: Any, write: DisappearanceWrite) -> None:
    """Set the artifact's event columns (§17.6) — first-observation-wins.

    ``capture_status`` tracks the latest failing status;
    ``disappeared_observed_at`` keeps the earliest recorded observation
    (``COALESCE`` — once recorded, never erased). Requires ``artifact_id`` set
    (call :func:`persist_disappearance`, which resolves the ref first).
    """
    assert write.artifact_id is not None
    marked = conn.execute(
        "SELECT disappeared_observed_at IS NOT NULL FROM evidence_artifact WHERE artifact_id = %s",
        (write.artifact_id,),
    ).fetchone()
    write.already_marked = bool(marked and marked[0])
    conn.execute(
        "UPDATE evidence_artifact "
        "SET capture_status = %s, "
        "    disappeared_observed_at = COALESCE(disappeared_observed_at, %s) "
        "WHERE artifact_id = %s",
        (write.event_status, write.event_observed_at, write.artifact_id),
    )
    write.event_applied = True


def persist_disappearance(conn: Any, disappearance: Disappearance) -> DisappearanceWrite:
    """Persist one :class:`connectors.disappearance.Disappearance`.

    Resolves the artifact, applies the event columns (the ONE designed UPDATE
    surface — scoped by the ``disappearance_event_grant`` column grant), and
    lands the research task. Everything runs inside the caller's transaction.
    """
    event = disappearance.event
    write = DisappearanceWrite(
        artifact_ref=event.artifact_id,
        event_status=event.failing_status,
        event_observed_at=event.observed_at,
    )
    resolved = _resolve_artifact_id(conn, event.artifact_id)
    if resolved is not None:
        write.artifact_found = True
        write.artifact_id = resolved
        apply_event_columns(conn, write)
    write.task_outcome = insert_task_row(
        conn,
        dict(disappearance.task),
        trigger_kind=DISAPPEARANCE_TRIGGER,
        trigger_ref=str(resolved or event.artifact_id),
    )
    return write


def persist_disappearances(
    conn: Any, disappearances: list[Disappearance], *, role: str | None = None
) -> PersistSummary:
    """Persist a run's recorded disappearances (the report's ``disappearances``)."""
    if role:
        conn.execute(f"SET ROLE {role}")
    summary = PersistSummary()
    for disappearance in disappearances:
        summary.considered += 1
        write = persist_disappearance(conn, disappearance)
        if write.event_applied:
            summary.events_applied += 1
            if write.already_marked:
                summary.already_marked += 1
        else:
            summary.unresolved_artifacts += 1
        if write.task_outcome == "written":
            summary.tasks_written += 1
        elif write.task_outcome == "existing":
            summary.tasks_existing += 1
        summary.writes.append(write.as_dict())
    return summary


def disappeared_artifacts(conn: Any, *, role: str | None = None) -> list[dict[str, Any]]:
    """The queryable disappearance read (SIG-INGEST-010): which artifacts went dark.

    Every ``evidence_artifact`` carrying ``disappeared_observed_at``, with its
    source + locator + the linked ``source_disappeared`` task when one cites
    the artifact — "which agencies quietly removed their transparency portal"
    is an answerable question only because this read exists.
    """
    if role:
        conn.execute(f"SET ROLE {role}")
    rows = conn.execute(
        "SELECT a.artifact_id::text, a.source_id, a.stable_locator, a.url, "
        "       a.capture_status, a.disappeared_observed_at::text, "
        "       t.task_id::text, t.status "
        "FROM evidence_artifact a "
        "LEFT JOIN research_task t "
        "  ON t.task_type = 'source_disappeared' "
        " AND t.trigger_kind = %s "
        " AND t.trigger_ref = a.artifact_id::text "
        "WHERE a.disappeared_observed_at IS NOT NULL "
        "ORDER BY a.disappeared_observed_at DESC, a.artifact_id",
        (DISAPPEARANCE_TRIGGER,),
    ).fetchall()
    return [
        {
            "artifact_id": r[0],
            "source_id": r[1],
            "stable_locator": r[2],
            "url": r[3],
            "capture_status": r[4],
            "disappeared_observed_at": r[5],
            "task_id": r[6],
            "task_status": r[7],
        }
        for r in rows
    ]


__all__ = [
    "DISAPPEARANCE_TRIGGER",
    "DisappearanceWrite",
    "PersistSummary",
    "apply_event_columns",
    "disappeared_artifacts",
    "insert_task_row",
    "persist_disappearance",
    "persist_disappearances",
]
