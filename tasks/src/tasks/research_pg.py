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
  run degrades to an empty queue (no fabricated task, D-R6.x live gate). The contract inputs
  (:func:`read_contract_expiry_inputs`, P37.32 / K7 WX-06 — catalog #10's
  ``contract_expiring`` detector) are not a materialization: they are the spine's own
  current claims on ``contract:*`` subjects, the same subject family + predicate set the
  P35.43 watch producer's ``watch_claims`` read carries, minus the publication gates a
  public emission needs (a task is minted internally and gated at export by
  ``{PUB_TASK_GATE}``).
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

from collections.abc import Iterable
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
    "read_contract_expiry_inputs",
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
    # P36.58 (SIG-RQ-005 / K11 RC-6): subject-grain wording — a coverage_hole
    # task's subject is one record (a camera, an agency row), so the closing
    # condition names the subject, never "the jurisdiction" the older text did.
    "coverage_hole": (
        "evidence for the subject is obtained, OR a CoverageRecord records the searched absence"
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
    # P37.32 (K7 WX-06, catalog #10): the "renewal terms unknown" task — the
    # wording mirrors the catalog's own closes (renewal evidence recorded, OR
    # the recorded end date moves past the firing window).
    "contract_expiring": (
        "the contract's renewal terms are on record (auto_renews and its notice "
        "window, or a recorded non-renewal), or the recorded end date passes the "
        "firing window"
    ),
    # P37.35 (K11 RQ-02, SIG-RQ-005): the routing table's two new types name
    # the subject's own gap — subject-grain wording (RC-6), never "the
    # jurisdiction".
    "retention_unknown": (
        "the subject's retention period or retention policy is evidenced on the "
        "record, OR a CoverageRecord records the searched absence"
    ),
    "sharing_unknown": (
        "the subject's data-sharing record (partners, degree or restrictions) is "
        "evidenced on the record, OR a CoverageRecord records the searched absence"
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
    #: P37.35 (K11 RQ-02): persisted rows superseded by disposition — the
    #: per-camera ``coverage_hole`` rows the campaign/metric lanes replace,
    #: plus mis-routed rows the new predicate table re-mints (append-only,
    #: never a delete).
    superseded: int = 0
    records_request_drafts: int = 0
    records_requests_sent: int = 0  # always 0 — sending is operator-gated (never auto)

    def as_dict(self) -> dict[str, object]:
        return {
            "generated": self.generated,
            "written": self.written,
            "skipped_existing": self.skipped_existing,
            "skipped_no_entity": self.skipped_no_entity,
            "superseded": self.superseded,
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

    inputs = MaterializedInputs(
        contradictions=_read("contradiction", read_materialized_contradictions),
        coverage=_read("coverage_record", read_materialized_coverage),
        edges=_read("relationship", read_materialized_edges),
        contracts=read_contract_expiry_inputs(conn),
    )
    # P37.35 (K11 RC-4): the subject → attributed-jurisdiction map — the
    # materialized rows carry none, so the task layer resolves the subject's
    # evidenced jurisdiction link (a `jurisdiction:`-keyed object entity).
    subjects = {
        str(r[k])
        for rows, k in (
            (inputs.contradictions, "subject_id"),
            (inputs.coverage, "subject_id"),
            (inputs.edges, "from_entity"),
            (inputs.contracts, "subject_id"),
        )
        for r in rows
        if r.get(k)
    }
    return MaterializedInputs(
        contradictions=inputs.contradictions,
        coverage=inputs.coverage,
        edges=inputs.edges,
        contracts=inputs.contracts,
        jurisdictions=_subject_jurisdictions(conn, subjects),
    )


def _subject_jurisdictions(conn: Any, subject_ids: Iterable[str]) -> dict[str, str]:
    """subject_id → the attributed jurisdiction entity (P37.35 / K11 §4.3).

    The evidenced link: a currently-valid claim on the subject whose
    ``object_entity`` is a ``jurisdiction:``-keyed entity — the newest such
    claim wins (``lower(sys_period) DESC``). A subject with no evidenced link
    yields no entry — the task mints unplaced (K4), never a guessed place.
    A schema mismatch degrades to ``{}`` — honest absence.
    """
    ids = sorted(s for s in subject_ids if s)
    if not ids:
        return {}
    try:
        rows = conn.execute(
            "SELECT DISTINCT ON (c.subject_id) c.subject_id::text, c.object_entity::text"
            "  FROM claim c"
            "  JOIN entity_identifier ei ON ei.entity_id = c.object_entity"
            "   AND ei.scheme = 'sig.connector.subject' AND ei.value LIKE 'jurisdiction:%'"
            " WHERE c.subject_id = ANY(%s::uuid[]) AND c.object_entity IS NOT NULL"
            "   AND upper_inf(c.sys_period)"
            " ORDER BY c.subject_id, lower(c.sys_period) DESC, c.claim_id DESC",
            (ids,),
        ).fetchall()
    except Exception:  # noqa: BLE001 - a schema-shape mismatch is honest absence
        return {}
    return {str(s): str(j) for s, j in rows}


#: The contract predicates catalog #10 reads — the WX-01 contract surface:
#: ``end_date`` fires; the renewal-term claims settle ``renewal_evidence``
#: (P37.32 / K7 WX-06).
_CONTRACT_EXPIRY_PREDICATES: tuple[str, ...] = (
    "end_date",
    "auto_renews",
    "notice_window_days",
    "renewal_term_months",
    "renewal_options",
)


def read_contract_expiry_inputs(conn: Any) -> list[dict[str, Any]]:
    """Read the current contract claims the catalog #10 detector runs over.

    One row per ``contract:*`` subject: the latest recorded (never superseded)
    claim of each firing/renewal predicate — ``end_date`` + its claim id (the
    trigger the task cites) and the ``auto_renews``/``notice_window_days``/
    ``renewal_term_months``/``renewal_options`` values ``renewal_evidence``
    turns on. A claim another claim revises is dropped (the newest recording
    wins, append-only). A schema mismatch or an absent subject-key surface
    degrades to ``[]`` — honest absence, never a fabricated contract.
    """
    try:
        rows = conn.execute(
            "SELECT c.subject_id::text, skey.subject_key, c.predicate_id,"
            "       c.claim_id::text, COALESCE(c.value_text, c.raw_value),"
            "       c.value_num, c.value_bool"
            "  FROM claim c"
            "  JOIN LATERAL (SELECT ei.value AS subject_key"
            "                FROM entity_identifier ei"
            "               WHERE ei.entity_id = c.subject_id"
            "                 AND ei.scheme = 'sig.connector.subject'"
            "               ORDER BY ei.value LIMIT 1) skey ON true"
            " WHERE skey.subject_key LIKE 'contract:%'"
            "   AND upper_inf(c.sys_period)"
            "   AND NOT EXISTS (SELECT 1 FROM claim c2"
            "                   WHERE c2.revises_claim = c.claim_id)"
            f"   AND c.predicate_id IN ({','.join(repr(p) for p in _CONTRACT_EXPIRY_PREDICATES)})"
            " ORDER BY c.subject_id, c.predicate_id,"
            "          lower(c.sys_period), c.claim_id",
        ).fetchall()
    except Exception:  # noqa: BLE001 - a schema-shape mismatch is honest absence
        return []
    by_subject: dict[str, dict[str, Any]] = {}
    for subject_id, subject_key, predicate, claim_id, value, num, boolean in rows:
        entry = by_subject.setdefault(
            str(subject_id),
            {
                "subject_id": str(subject_id),
                "subject_key": str(subject_key),
                "jurisdiction_id": None,
            },
        )
        if predicate == "end_date":
            entry["end_date"] = str(value) if value else None
            entry["end_date_claim_id"] = str(claim_id)
        elif predicate == "auto_renews":
            entry["auto_renews"] = bool(boolean) if boolean is not None else None
        elif predicate == "notice_window_days":
            entry["notice_window_days"] = int(num) if num is not None else None
        elif predicate == "renewal_term_months":
            entry["renewal_term_months"] = int(num) if num is not None else None
        elif predicate == "renewal_options":
            entry["renewal_options"] = str(value) if value else None
    # A contract with no current end_date claim cannot fire — the undated case
    # is a coverage question, never this detector's.
    return [r for r in by_subject.values() if r.get("end_date_claim_id") and r.get("end_date")]


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


def _has_column(conn: Any, table: str, column: str) -> bool:
    """True iff ``table.column`` exists (the additive RQ-02 change may not be
    deployed on an older spine — honest degrade, never a crash)."""
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        " WHERE table_name = %s AND column_name = %s LIMIT 1",
        (table, column),
    ).fetchone()
    return bool(row)


def _insert_task(conn: Any, task: ResearchTask, *, with_predicates: bool) -> bool:
    """INSERT one queued task, append-only + deduped. Returns True iff a row was written.

    ``predicate_ids`` (the additive RQ-02 column) records the predicate(s) the
    task seeks (SIG-RQ-005); on a spine without the column the insert falls
    back to the pre-change column set — the task still lands.
    """
    closing = CLOSING_CONDITION_TEXT.get(task.task_type, _GENERIC_CLOSING_CONDITION)
    cols = (
        "  (task_type, subject_id, jurisdiction_id, priority, status, closing_condition, "
        "   detector_version, trigger_kind, trigger_ref"
        + (", predicate_ids" if with_predicates else "")
        + ")"
    )
    placeholders = "%s, %s, %s, %s, 'generated', %s, %s, %s, %s" + (
        ", %s" if with_predicates else ""
    )
    params: list[Any] = [
        task.task_type,
        task.subject_id,
        task.jurisdiction_id,
        task.priority,
        closing,
        task.detector_version,
        task.trigger_kind,
        task.trigger_ref,
    ]
    if with_predicates:
        params.append(list(task.predicate_ids) or None)
    row = conn.execute(
        "INSERT INTO research_task " + cols + " VALUES (" + placeholders + ") "
        "ON CONFLICT (task_type, subject_id) DO NOTHING "
        "RETURNING task_id",
        params,
    ).fetchone()
    return bool(row)


#: The supersession reason stamped on legacy rows the RQ-02 routing replaces
#: (K11 §4.1: append-only — a `superseded` disposition with a reason, never a
#: delete).
_FIELD_GAP_REASON = (
    "per-object field gap now routed by the predicate routing table "
    "(gap_routing.toml / D-K11-1): campaign-lane gaps present as mapping "
    "campaigns, registry-only gaps as coverage metrics — never individual "
    "coverage_hole research tasks"
)
_REROUTED_REASON = (
    "coverage gap re-minted under the explicit predicate routing table "
    "(gap_routing.toml / SIG-RQ-005) — this row's task type was the retired "
    "substring router's answer, the new task mints under the asserted type"
)

#: The `research_task` statuses a persisted row may still be superseded from —
#: an already-closed/invalidated row is terminal and never rewritten.
_OPEN_TASK_STATUSES = (
    "generated",
    "triaged",
    "claimed",
    "in_progress",
    "submitted",
    "verified",
    "reopened",
)


def _supersede_rerouted_tasks(
    conn: Any,
    *,
    field_gap_refs: Iterable[str],
    rerouted_refs: dict[str, str],
) -> int:
    """Supersede persisted per-camera rows the RQ-02 routing replaces.

    Two append-only dispositions (the `research_task_predicates` change's
    column-scoped ``UPDATE`` grant — an EVENT surface, never a delete):
    every open ``coverage_hole`` row citing a campaign/metric-routed
    coverage record, and every open row citing a research-lane coverage
    record whose recorded ``task_type`` is not the table's asserted route.
    A row already superseded/closed is never touched twice (+0 idempotent).
    Returns the count superseded; 0 on an older spine lacking the columns.
    """
    if not (_has_column(conn, "research_task", "disposition_reason")):
        return 0
    refs = sorted(set(field_gap_refs))
    superseded = 0
    if refs:
        rows = conn.execute(
            "UPDATE research_task"
            "   SET status = 'closed', disposition = 'superseded', disposition_reason = %s"
            " WHERE task_type = 'coverage_hole' AND trigger_kind = 'coverage'"
            "   AND trigger_ref = ANY(%s) AND status = ANY(%s)"
            "   AND disposition IS NULL"
            " RETURNING task_id",
            (_FIELD_GAP_REASON, refs, list(_OPEN_TASK_STATUSES)),
        ).fetchall()
        superseded += len(rows)
    for ref, slug in sorted(rerouted_refs.items()):
        rows = conn.execute(
            "UPDATE research_task"
            "   SET status = 'closed', disposition = 'superseded', disposition_reason = %s"
            " WHERE trigger_kind = 'coverage' AND trigger_ref = %s"
            "   AND task_type <> %s AND status = ANY(%s) AND disposition IS NULL"
            " RETURNING task_id",
            (_REROUTED_REASON, ref, slug, list(_OPEN_TASK_STATUSES)),
        ).fetchall()
        superseded += len(rows)
    return superseded


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
    summary.superseded = _supersede_rerouted_tasks(
        conn,
        field_gap_refs=result.field_gap_refs,
        rerouted_refs=result.rerouted_refs,
    )
    with_predicates = _has_column(conn, "research_task", "predicate_ids")
    for task in result.queue:
        if not _entity_exists(conn, task.subject_id):
            summary.skipped_no_entity += 1
            continue
        if _insert_task(conn, task, with_predicates=with_predicates):
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
