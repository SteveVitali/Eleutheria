# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Run the §33.2 detector catalog over the materialized graph → the research queue (P29.2).

This is the *self-feeding accountability loop*: the Round-6 materialized graph
(contradictions §31, honest coverage §32, the sharing/relationship network §29.3) is the
output of running SIG's detectors over the real spine, and this module turns each of those
materialized detector outputs into a **research task** — the next round of evidence to
gather. It is pure orchestration: it **reuses** the built engine and does not re-implement
any of it.

* **Contradictions → tasks (SIG-TASK-004).** Every §31 ``contradiction_type`` already routes
  to the catalog task that resolves it (:data:`tasks.catalog.CONTRADICTION_TASK_MAP`);
  detection without a route to resolution is just an alarm. Each OPEN materialized
  contradiction generates its mapped catalog task, citing the contradiction as its trigger.
* **Coverage gaps → tasks (§32).** A materialized ``coverage_record`` whose absence is
  ``not_researched``/``searched_not_found`` is an honest gap; a records-obtainable predicate
  (contract/procurement/retention/policy/funding) routes to ``missing_contract`` (a
  records-requester task), else to ``coverage_hole``.
* **Stale sharing edges → renewals (§29.7).** A ``configured_access`` relationship whose newest
  observation exceeds the FAST volatility threshold generates ``sharing_snapshot_stale`` — the
  renewal signal.

The queue is minted through the real :class:`~tasks.lifecycle.TaskPool`, so the §33
anti-abuse disciplines apply unchanged: **per-subject rate limiting** (a
:class:`~tasks.lifecycle.RateLimiter`, SIG-TASK-013) and **``(task_type, subject)`` dedup**
(SIG-TASK-007). Every generated task **cites its trigger** (the materialized row id). The
:class:`~tasks.geographic.GeographicQueue` orders the queue for a claiming group without ever
gatekeeping it (SIG-TASK-010/011).

Records-request generation (§36) is here too, and it is **DRAFT, NEVER SEND**: for each
records-requester/document-reviewer task this emits the *ready-to-file materials* — the correct
statute + citation for the jurisdiction (:func:`~tasks.records_request.records_law_for`) and the
current proven template (:func:`~tasks.records_request.template_library`) — with the **filer left
for the contributor who files it** (SIG-TASK-018: SIG files nothing without an explicit consenting
filer). **No transmit path exists or is invoked** — sending a records request is an external side
effect reserved to an explicit operator gate (never auto-fired). A residency-restricted
jurisdiction (SIG-TASK-016a/b) carries a routing note to local filers rather than presenting an
invalid non-resident request.

Reading the materialized rows from Postgres and persisting the queue as ``research_task`` rows
is :mod:`tasks.research_pg`; this module is pure (dicts in, dataclasses out) and DB-free.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from .catalog import CONTRADICTION_TASK_MAP, build_catalog
from .geographic import GeographicQueue
from .lifecycle import RateLimiter, ResearchTask, TaskPool
from .records_request import (
    RESIDENCY_RESTRICTED_JURISDICTIONS,
    UnknownJurisdictionError,
    records_law_for,
    table_version,
    template_library,
)
from .spec import TaskTypeRegistry
from .vocabulary import AssigneeClass

__all__ = [
    "MaterializedInputs",
    "JurisdictionInfo",
    "RecordsRequestDraft",
    "DetectorRunSummary",
    "DetectorRunResult",
    "run_detectors",
    "records_request_drafts",
    "RECORDS_REQUEST_RECORD_TYPE",
]

# --- routing constants (documented, honest — the materialized row IS the detection) ---

#: Only an OPEN contradiction is queued; a settled/superseded finding is no longer work.
_CONTRADICTION_OPEN_STATUS = "open"

#: Priority band by §31 severity (blocking findings are worked first).
_SEVERITY_PRIORITY: dict[str, float] = {
    "blocking": 0.9,
    "notable": 0.6,
    "informational": 0.3,
}

#: The coverage absences that are a research gap (an evidenced negative — not an
#: ``evidence_of_absence`` / ``not_applicable`` conclusion — is work to be done).
_COVERAGE_GAP_ABSENCE: frozenset[str] = frozenset({"not_researched", "searched_not_found"})

#: A coverage gap whose predicate is obtainable by a public-records request routes to the
#: records-requester ``missing_contract`` task; any other gap is field/local ``coverage_hole``.
_RECORDS_OBTAINABLE_MARKERS: tuple[str, ...] = (
    "contract",
    "procurement",
    "retention",
    "policy",
    "funding",
    "grant",
    "sharing",
)

#: The relationship access kind whose snapshots go stale (§29.7 configured access).
_STALE_ACCESS_KIND = "configured_access"

#: The FAST-volatility threshold (§29.7): a configured-access snapshot older than this is stale.
_FAST_THRESHOLD_DAYS = 180

#: Catalog task type → the records-request record type (a ``request_templates.toml`` key) whose
#: proven template + statute the draft uses. Any records-requester/document-reviewer task not
#: listed falls back to the surveillance-policy template.
RECORDS_REQUEST_RECORD_TYPE: dict[str, str] = {
    "conflicting_retention": "surveillance_policy",
    "retention_changed_without_policy": "surveillance_policy",
    "incident_only_secondary_sources": "surveillance_policy",
    "missing_contract": "alpr_contract",
    "adoption_without_corroboration": "alpr_contract",
    "cooperative_contract_unexplored": "alpr_contract",
    "contract_amendment_chain_incomplete": "alpr_contract",
    "free_trial_capability": "alpr_contract",
    "missing_physical_devices": "camera_deployment",
    "sharing_snapshot_stale": "data_sharing_agreement",
}
_DEFAULT_RECORD_TYPE = "surveillance_policy"

#: The assignee classes whose tasks a records request can serve (§36).
_RECORDS_ASSIGNEES: frozenset[AssigneeClass] = frozenset(
    {AssigneeClass.RECORDS_REQUESTER, AssigneeClass.DOCUMENT_REVIEWER}
)


@dataclass(frozen=True)
class MaterializedInputs:
    """The Round-6 materialized detector outputs the detector run consumes (P28.1–P28.4).

    Each is the exact ``list[dict]`` shape the materialized read seams return
    (``reconcile.materialize.read_materialized_{contradictions,edges}`` and
    ``inference.materialize.read_materialized_coverage``). Absent/empty inputs are honest
    (an unmaterialized spine degrades to an empty queue, never a fabricated task).
    """

    contradictions: Sequence[dict[str, object]] = ()
    coverage: Sequence[dict[str, object]] = ()
    edges: Sequence[dict[str, object]] = ()


@dataclass(frozen=True)
class JurisdictionInfo:
    """Where a records request would be filed (the §36 routing a resolver supplies).

    ``records_law_key`` is a :func:`~tasks.records_request.records_law_table` key (a US
    jurisdiction code, e.g. ``"OK"``). ``target_agency`` is the agency the request names;
    ``records_contact`` defaults to a placeholder completed at filing time.
    """

    records_law_key: str
    target_agency: str
    records_contact: str = "(records contact to be determined at filing time)"


#: A resolver mapping a task's ``(subject_id, jurisdiction_id)`` to its §36 routing, or
#: ``None`` when the jurisdiction cannot be resolved (the task is queued, no draft is made).
JurisdictionResolver = Callable[[str | None, str | None], JurisdictionInfo | None]


@dataclass(frozen=True)
class RecordsRequestDraft:
    """A statute-templated public-records request **DRAFT** — generated, NEVER sent (§36).

    Sending a records request is an external side effect reserved to an explicit **operator
    gate** (never auto-fired). This carries the ready-to-file *materials* — the correct
    statute + citation for the jurisdiction and the current proven template body — with the
    **filer left for the contributor who files it** (SIG-TASK-018: SIG files nothing without
    an explicit consenting filer, so no filer/consent is fabricated here). ``status`` is
    always ``"drafted"``; there is no transmit path. A residency-restricted jurisdiction
    (SIG-TASK-016a/b) carries ``routing_note`` to the local filers rather than presenting an
    invalid non-resident request.
    """

    task_type: str
    subject_id: str | None
    jurisdiction_id: str | None
    trigger_kind: str | None
    trigger_ref: str | None
    records_law_key: str
    jurisdiction_name: str
    target_agency: str
    records_contact: str
    record_type: str
    statute_name: str
    statutory_citation: str
    records_sought: str
    draft_body: str
    response_deadline: str
    appeal_path: str
    residency_restricted: bool
    routing_note: str
    template_version: str
    template_set_version: str
    table_version: str
    #: NEVER "sent" — sending is operator-gated (drafted-not-sent, BL-057).
    status: str = "drafted"

    def as_dict(self) -> dict[str, object]:
        """A JSON-serialisable view (the ``records_requests.json`` artifact shape)."""
        return {
            "status": self.status,
            "task_type": self.task_type,
            "subject_id": self.subject_id,
            "jurisdiction_id": self.jurisdiction_id,
            "trigger_kind": self.trigger_kind,
            "trigger_ref": self.trigger_ref,
            "records_law_key": self.records_law_key,
            "jurisdiction_name": self.jurisdiction_name,
            "target_agency": self.target_agency,
            "records_contact": self.records_contact,
            "record_type": self.record_type,
            "statute_name": self.statute_name,
            "statutory_citation": self.statutory_citation,
            "records_sought": self.records_sought,
            "draft_body": self.draft_body,
            "response_deadline": self.response_deadline,
            "appeal_path": self.appeal_path,
            "residency_restricted": self.residency_restricted,
            "routing_note": self.routing_note,
            "template_version": self.template_version,
            "template_set_version": self.template_set_version,
            "table_version": self.table_version,
        }


@dataclass
class DetectorRunSummary:
    """Counters describing one detector run (the CLI/JSON summary)."""

    contradictions_read: int = 0
    coverage_read: int = 0
    edges_read: int = 0
    generated: int = 0
    deduplicated: int = 0
    rate_limited: int = 0
    unroutable: int = 0
    by_task_type: dict[str, int] = field(default_factory=dict)
    by_trigger_kind: dict[str, int] = field(default_factory=dict)
    records_request_drafts: int = 0
    residency_routed_drafts: int = 0

    def as_dict(self) -> dict[str, object]:
        """A JSON-serialisable, deterministically-ordered view."""
        return {
            "contradictions_read": self.contradictions_read,
            "coverage_read": self.coverage_read,
            "edges_read": self.edges_read,
            "generated": self.generated,
            "deduplicated": self.deduplicated,
            "rate_limited": self.rate_limited,
            "unroutable": self.unroutable,
            "by_task_type": dict(sorted(self.by_task_type.items())),
            "by_trigger_kind": dict(sorted(self.by_trigger_kind.items())),
            "records_request_drafts": self.records_request_drafts,
            "residency_routed_drafts": self.residency_routed_drafts,
            "records_requests_sent": 0,  # always 0 — sending is operator-gated (never auto)
        }


@dataclass
class DetectorRunResult:
    """The outcome of a detector run: the deduped queue, the drafts, and the summary."""

    pool: TaskPool
    queue: list[ResearchTask]
    drafts: list[RecordsRequestDraft]
    summary: DetectorRunSummary


# --- candidate routing (materialized row → a catalog task) --------------------


def _parse_dt(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _contradiction_candidates(
    rows: Iterable[dict[str, object]],
) -> list[tuple[str, str | None, str | None, str, str, float]]:
    out: list[tuple[str, str | None, str | None, str, str, float]] = []
    for r in rows:
        if str(r.get("status") or "") != _CONTRADICTION_OPEN_STATUS:
            continue
        ctype = str(r.get("contradiction_type") or "")
        slug = CONTRADICTION_TASK_MAP.get(ctype)
        if not slug:
            continue
        subject = r.get("subject_id")
        cid = r.get("contradiction_id")
        if subject is None or cid is None:
            continue
        priority = _SEVERITY_PRIORITY.get(str(r.get("severity") or ""), 0.3)
        out.append((slug, str(subject), None, "contradiction", str(cid), priority))
    return out


def _coverage_candidates(
    rows: Iterable[dict[str, object]],
) -> list[tuple[str, str | None, str | None, str, str, float]]:
    out: list[tuple[str, str | None, str | None, str, str, float]] = []
    for r in rows:
        if str(r.get("absence_kind") or "") not in _COVERAGE_GAP_ABSENCE:
            continue
        cid = r.get("coverage_id")
        subject = r.get("subject_id")
        jurisdiction = r.get("jurisdiction_id")
        subj = subject if subject is not None else jurisdiction
        if subj is None or cid is None:
            continue  # a gap with no subject/jurisdiction cannot be scoped to a queue
        predicate = str(r.get("predicate_id") or "")
        records_obtainable = any(m in predicate for m in _RECORDS_OBTAINABLE_MARKERS)
        slug = "missing_contract" if records_obtainable else "coverage_hole"
        out.append(
            (
                slug,
                str(subj),
                str(jurisdiction) if jurisdiction is not None else None,
                "coverage",
                str(cid),
                0.5,
            )
        )
    return out


def _edge_candidates(
    rows: Iterable[dict[str, object]], *, now: datetime
) -> list[tuple[str, str | None, str | None, str, str, float]]:
    out: list[tuple[str, str | None, str | None, str, str, float]] = []
    for r in rows:
        if str(r.get("access_kind") or "") != _STALE_ACCESS_KIND:
            continue
        valid_from = _parse_dt(r.get("valid_from"))
        rid = r.get("relationship_id")
        subject = r.get("from_entity")
        if valid_from is None or rid is None or subject is None:
            continue
        age_days = (now - valid_from).days
        if age_days <= _FAST_THRESHOLD_DAYS:
            continue  # snapshot still fresh — not yet a renewal task
        priority = min(1.0, age_days / 365.0)
        out.append(
            ("sharing_snapshot_stale", str(subject), None, "relationship", str(rid), priority)
        )
    return out


# --- the run ------------------------------------------------------------------


def run_detectors(
    inputs: MaterializedInputs,
    *,
    now: datetime,
    registry: TaskTypeRegistry | None = None,
    rate_limiter: RateLimiter | None = None,
    jurisdiction_resolver: JurisdictionResolver | None = None,
) -> DetectorRunResult:
    """Run the §33.2 catalog over the materialized inputs → the research queue.

    Routes each materialized detector output to its catalog task (SIG-TASK-004 for
    contradictions), mints it through the real :class:`~tasks.lifecycle.TaskPool` (so
    ``(task_type, subject)`` dedup + the optional per-subject rate limiter apply), and stamps
    each task with its trigger. Then drafts records requests for the records-oriented tasks
    (DRAFT, NEVER SEND). Empty inputs yield an empty queue (honest degrade).
    """
    registry = registry if registry is not None else build_catalog()
    pool = TaskPool(rate_limiter=rate_limiter)
    summary = DetectorRunSummary(
        contradictions_read=len(inputs.contradictions),
        coverage_read=len(inputs.coverage),
        edges_read=len(inputs.edges),
    )

    candidates = (
        _contradiction_candidates(inputs.contradictions)
        + _coverage_candidates(inputs.coverage)
        + _edge_candidates(inputs.edges, now=now)
    )

    seen: set[str] = set()
    for slug, subject_id, jurisdiction_id, trigger_kind, trigger_ref, priority in candidates:
        if slug not in registry:
            summary.unroutable += 1
            continue
        spec = registry.get(slug)
        task = pool.generate(
            spec,
            subject_id,
            facts={"priority": priority},
            now=now,
            jurisdiction_id=jurisdiction_id,
            trigger_kind=trigger_kind,
            trigger_ref=trigger_ref,
        )
        if task is None:
            summary.rate_limited += 1
            continue
        if task.task_id in seen:
            summary.deduplicated += 1
            continue
        seen.add(task.task_id)
        summary.by_task_type[slug] = summary.by_task_type.get(slug, 0) + 1
        summary.by_trigger_kind[trigger_kind] = summary.by_trigger_kind.get(trigger_kind, 0) + 1

    queue = sorted(pool.open_tasks(), key=lambda t: (-t.priority, t.task_type, t.subject_id or ""))
    summary.generated = len(queue)

    drafts = records_request_drafts(queue, jurisdiction_resolver=jurisdiction_resolver)
    summary.records_request_drafts = len(drafts)
    summary.residency_routed_drafts = sum(1 for d in drafts if d.residency_restricted)

    return DetectorRunResult(pool=pool, queue=queue, drafts=drafts, summary=summary)


def records_request_drafts(
    tasks: Iterable[ResearchTask],
    *,
    jurisdiction_resolver: JurisdictionResolver | None,
) -> list[RecordsRequestDraft]:
    """Draft statute-templated records requests for the records-oriented tasks (§36).

    DRAFT, NEVER SEND: this fills the current proven template with the correct statute for
    each jurisdiction, leaving the **filer for the contributor who files it** (no consent is
    fabricated, SIG-TASK-018) and inventing no transmit path. A task whose jurisdiction the
    resolver cannot map yields no draft (it stays a queued task). A residency-restricted
    jurisdiction carries a routing note to local filers (SIG-TASK-016a/b).
    """
    if jurisdiction_resolver is None:
        return []
    lib = template_library()
    tv = table_version()
    drafts: list[RecordsRequestDraft] = []
    for task in tasks:
        if task.spec.assignee_class not in _RECORDS_ASSIGNEES:
            continue
        info = jurisdiction_resolver(task.subject_id, task.jurisdiction_id)
        if info is None:
            continue
        try:
            law = records_law_for(info.records_law_key)
        except UnknownJurisdictionError:
            continue
        record_type = RECORDS_REQUEST_RECORD_TYPE.get(task.task_type, _DEFAULT_RECORD_TYPE)
        template = lib.current(record_type)
        records_sought = template.records_sought.format(
            agency=info.target_agency, start_date="the earliest available date"
        )
        restricted = info.records_law_key in RESIDENCY_RESTRICTED_JURISDICTIONS
        routing_note = (
            (
                f"{law.name} restricts public-records requests to residents ({law.citation}); "
                "this draft must be filed by a resident of the jurisdiction — route to the local "
                "filers (§33.5, SIG-TASK-016a/016b)."
            )
            if restricted
            else ""
        )
        draft_body = template.body.format(
            agency=info.target_agency,
            records_contact=info.records_contact,
            statute=law.statute,
            citation=law.citation,
            records_sought=records_sought,
            response_deadline=law.response_deadline,
            filer="[the contributor who files this request — completed at filing time]",
            public_act_notice=(
                "[Filing is a public act attributable to the filer; the acknowledgement is "
                "completed at filing time (SIG-TASK-018).]"
            ),
        )
        drafts.append(
            RecordsRequestDraft(
                task_type=task.task_type,
                subject_id=task.subject_id,
                jurisdiction_id=task.jurisdiction_id,
                trigger_kind=task.trigger_kind,
                trigger_ref=task.trigger_ref,
                records_law_key=info.records_law_key,
                jurisdiction_name=law.name,
                target_agency=info.target_agency,
                records_contact=info.records_contact,
                record_type=record_type,
                statute_name=law.statute,
                statutory_citation=law.citation,
                records_sought=records_sought,
                draft_body=draft_body,
                response_deadline=law.response_deadline,
                appeal_path=law.appeal_path,
                residency_restricted=restricted,
                routing_note=routing_note,
                template_version=template.version,
                template_set_version=lib.set_version,
                table_version=tv,
            )
        )
    return drafts


def order_for_group(
    queue: Iterable[ResearchTask], *, group_id: str, queue_view: GeographicQueue, now: datetime
) -> list[ResearchTask]:
    """Order the queue for a claiming group (§33.5) — a convenience over the real queue.

    Delegates to :meth:`tasks.geographic.GeographicQueue.order_for_group`: a group's claimed
    jurisdictions sort first, then by priority — priority, never exclusivity (SIG-TASK-010/011).
    """
    return queue_view.order_for_group(queue, group_id=group_id, now=now)
