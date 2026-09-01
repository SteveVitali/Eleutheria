# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Dispositions and the negative-result→data bridge (§33.4, SIG-TASK-008/009).

The disposition vocabulary (:class:`~tasks.vocabulary.Disposition`) is what lets
the queue *shrink*: a task can conclude as "searched, the record does not exist" or
"blocked by a fee", not only as "done". The load-bearing one is
`resolved_no_evidence_exists`: it MUST write a `CoverageRecord` with
`absence_kind = searched_not_found` and the sources searched (SIG-TASK-009). That is
the mechanism by which a negative result becomes *data* — an entry the coverage
layer (§32) can render — instead of nothing, and without it the queue can only grow.

This module reuses `inference.coverage.CoverageRecord` (P09.1) rather than
re-encoding the coverage shape: the `searched_not_found`-requires-`sources_searched`
invariant (SIG-METRIC-001/002) is enforced there and inherited here, so a
no-evidence disposition with no named sources is refused at the point of closing.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from inference.coverage import CoverageRecord

from .lifecycle import ResearchTask
from .vocabulary import Disposition

__all__ = [
    "BLOCKED_DISPOSITIONS",
    "RESOLVED_DISPOSITIONS",
    "COVERAGE_WRITING_DISPOSITION",
    "resolve_no_evidence_exists",
]

#: Dispositions that record a *resolution* of the task (the work concluded).
RESOLVED_DISPOSITIONS: frozenset[Disposition] = frozenset(
    {Disposition.RESOLVED_EVIDENCE_FOUND, Disposition.RESOLVED_NO_EVIDENCE_EXISTS}
)

#: Dispositions that record a *block* (the work is stopped by an external cause).
BLOCKED_DISPOSITIONS: frozenset[Disposition] = frozenset(
    {
        Disposition.BLOCKED_ACCESS_DENIED,
        Disposition.BLOCKED_FEE,
        Disposition.BLOCKED_AWAITING_RESPONSE,
    }
)

#: The one disposition that MUST write a `CoverageRecord` (SIG-TASK-009).
COVERAGE_WRITING_DISPOSITION: Disposition = Disposition.RESOLVED_NO_EVIDENCE_EXISTS


def resolve_no_evidence_exists(
    task: ResearchTask,
    *,
    predicate_id: str,
    sources_searched: Sequence[str],
    subject_class: str | None = None,
    searched_at: datetime | None = None,
    searched_by: str | None = None,
    search_method: str | None = None,
) -> CoverageRecord:
    """Close `task` as `resolved_no_evidence_exists`, writing a `CoverageRecord`.

    This is the *only* path to the `resolved_no_evidence_exists` disposition
    (:meth:`ResearchTask.close` refuses it), which guarantees SIG-TASK-009: recording
    "searched, found nothing" always produces a queryable `searched_not_found`
    coverage record naming the sources searched. The record is built first — so its
    `sources_searched`-required invariant (SIG-METRIC-002, enforced in
    `inference.coverage.CoverageRecord`) can reject an anonymous negative *before*
    the task is closed — then the task is closed with the disposition. Returns the
    record so the caller can persist it (persistence is downstream).

    `subject_class` supplies the coverage record's subject when the task has no
    concrete `subject_id` (a class-scoped negative); the record still requires *some*
    subject identity.
    """
    coverage = CoverageRecord(
        predicate_id=predicate_id,
        absence_kind="searched_not_found",
        subject_id=task.subject_id,
        subject_class=subject_class,
        jurisdiction_id=task.jurisdiction_id,
        sources_searched=tuple(sources_searched),
        searched_at=searched_at,
        searched_by=searched_by,
        search_method=search_method,
    )
    task._close_with(COVERAGE_WRITING_DISPOSITION)
    return coverage
