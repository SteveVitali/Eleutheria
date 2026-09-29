# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The anonymous, no-account corrections/dispute intake ops loop (§36/§45; P29.1, ADR-100).

The public ``/dispute`` channel (`web/src/pages/dispute.astro`) is the **anonymous,
no-account** correction path — the first tier of ADR-100's identity-minimization model
(zero identity required). This module is the **operator side** of that channel: it turns
a received dispute into append-only records and, for a factual correction, into an
**append-only correction claim** via the governance primitive
(:class:`policy.governance.BeliefLog`) — the correction is a NEW assertion that
supersedes the old one, never an overwrite, so a citation made before the correction
still resolves (SIG-GOV-005).

Two append-only logs, mirroring the claim spine's shape (P1–P3):

* **Submissions** (:class:`DisputeSubmission`) — one per received report, carrying the
  §45.1 category, the disputed subject, a free-text description, and the reporter label
  (``"anonymous"`` by default). **Identity is never required** except a legal demand that
  needs standing (SIG-GOV-002); the model stores no PII beyond an optional, self-provided
  contact the reporter chose to give for a legal demand.
* **Dispositions** (:class:`DispositionRecord`) — one per operator decision, carrying the
  permitted outcome (correct / annotate / suppress / delete / refuse — **refusal is a
  real, exercisable outcome with published reasoning**, SIG-GOV-004), the reason, the
  operator actor id, and the time.

The category and outcome vocabularies are **read from the policy data**
(`policy.governance.intake_categories` / `permitted_outcomes`), not redefined here, so
this ops loop and the public page and the transparency report stay one source of truth.
:meth:`CorrectionsIntake.transparency_report` counts by category and by outcome
**including refusals** (SIG-GOV-011).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .governance import (
    BeliefLog,
    identity_required_for,
    intake_categories,
    permitted_outcomes,
    transparency_report_shape,
)

__all__ = [
    "IntakeError",
    "DisputeSubmission",
    "DispositionRecord",
    "CorrectionsIntake",
    "known_categories",
    "known_outcomes",
]


class IntakeError(Exception):
    """Raised on an invalid intake action (unknown category/outcome, missing reason)."""


def known_categories() -> frozenset[str]:
    """The §45.1 intake category ids the channel accepts (from policy data, SIG-GOV-001)."""
    return frozenset(c["id"] for c in intake_categories())


def known_outcomes() -> frozenset[str]:
    """The permitted disposition outcome ids, refusal included (from policy data, SIG-GOV-004)."""
    return frozenset(o["id"] for o in permitted_outcomes())


@dataclass(frozen=True)
class DisputeSubmission:
    """One received dispute/correction report (append-only; anonymous by default).

    ``reporter`` defaults to ``"anonymous"`` — no account, no forced identity
    (SIG-GOV-002). ``contact`` is an optional, self-provided channel a reporter chose to
    give (only ever relevant for a legal demand needing standing); it is never required
    and never solicited beyond that. There is no other personal field.
    """

    submission_id: str
    category: str
    subject: str
    description: str
    submitted_at: datetime
    reporter: str = "anonymous"
    contact: str | None = None

    @property
    def is_anonymous(self) -> bool:
        """Whether the report carries no self-identification (the default channel state)."""
        return self.reporter == "anonymous" and not self.contact


@dataclass(frozen=True)
class DispositionRecord:
    """One operator decision on a submission (append-only; carries a reason + actor).

    ``outcome`` is one of the permitted outcomes; ``reason`` is mandatory for **every**
    outcome, including ``refuse`` — a process that can refuse without published
    reasoning is a heckler's veto (SIG-GOV-004). ``actor`` is the operator handle that
    took the decision (the audit trail).
    """

    submission_id: str
    outcome: str
    reason: str
    disposed_at: datetime
    actor: str


class CorrectionsIntake:
    """The append-only corrections/dispute intake ops loop (§36/§45, ADR-100).

    Composes a :class:`~policy.governance.BeliefLog`: a ``correct`` disposition writes
    an **append-only correction claim** through it (history preserved, SIG-GOV-005). The
    intake never mutates a prior record; a change of decision is a new disposition row.
    """

    def __init__(self, belief_log: BeliefLog | None = None) -> None:
        self._submissions: list[DisputeSubmission] = []
        self._dispositions: list[DispositionRecord] = []
        self.belief_log = belief_log if belief_log is not None else BeliefLog()

    # -- intake ---------------------------------------------------------------
    def submit(
        self,
        *,
        submission_id: str,
        category: str,
        subject: str,
        description: str,
        at: datetime,
        reporter: str = "anonymous",
        contact: str | None = None,
    ) -> DisputeSubmission:
        """Record a received dispute (append-only). Identity is never required (SIG-GOV-002).

        The category must be one the channel accepts. Anonymity is the default and is
        always permitted; a legal demand *may* need standing to be acted on, but the
        intake still accepts it without forcing identity — the standing check happens at
        disposition time, not intake.
        """
        if category not in known_categories():
            raise IntakeError(
                f"unknown intake category {category!r}; accepted: {sorted(known_categories())}"
            )
        if not submission_id:
            raise IntakeError("a submission MUST carry an id")
        submission = DisputeSubmission(
            submission_id=submission_id,
            category=category,
            subject=subject,
            description=description,
            submitted_at=at,
            reporter=reporter,
            contact=contact,
        )
        self._submissions.append(submission)
        return submission

    @staticmethod
    def category_requires_identity(category: str) -> bool:
        """Whether acting on ``category`` may require the reporter's standing (SIG-GOV-002)."""
        return identity_required_for(category)

    # -- disposition ----------------------------------------------------------
    def dispose(
        self,
        *,
        submission_id: str,
        outcome: str,
        reason: str,
        at: datetime,
        actor: str,
        subject: str | None = None,
        corrected_value: str | None = None,
    ) -> DispositionRecord:
        """Record an operator decision (append-only). Wires ``correct`` to a claim.

        Every outcome — refusal included — MUST carry a reason (SIG-GOV-004) and an
        operator actor id. A ``correct`` outcome additionally writes an append-only
        correction through the :class:`~policy.governance.BeliefLog`: if SIG already
        holds an open belief about the subject it is *corrected* (the prior value is
        preserved and still resolves at its belief-time, SIG-GOV-005); otherwise the
        corrected value is asserted as the first belief. Never an overwrite.
        """
        if outcome not in known_outcomes():
            raise IntakeError(f"unknown outcome {outcome!r}; permitted: {sorted(known_outcomes())}")
        if not reason:
            raise IntakeError(
                "every disposition MUST carry a reason — refusal included (SIG-GOV-004)"
            )
        if not actor:
            raise IntakeError("a disposition MUST carry an operator actor id (audit trail)")
        if not self._has_submission(submission_id):
            raise IntakeError(f"no such submission {submission_id!r} to dispose")
        record = DispositionRecord(
            submission_id=submission_id,
            outcome=outcome,
            reason=reason,
            disposed_at=at,
            actor=actor,
        )
        self._dispositions.append(record)
        if outcome == "correct":
            if not subject or corrected_value is None:
                raise IntakeError(
                    "a 'correct' disposition MUST name the subject and the corrected value"
                )
            if self.belief_log.has_open_belief(subject):
                self.belief_log.correct(subject, corrected_value, reason=reason, at=at)
            else:
                self.belief_log.assert_value(subject, corrected_value, at=at)
        return record

    # -- reads ----------------------------------------------------------------
    def submissions(self) -> tuple[DisputeSubmission, ...]:
        """Every received submission, in intake order (append-only)."""
        return tuple(self._submissions)

    def dispositions(self, *, submission_id: str | None = None) -> tuple[DispositionRecord, ...]:
        """Every disposition (optionally for one submission), in decision order."""
        return tuple(
            d
            for d in self._dispositions
            if submission_id is None or d.submission_id == submission_id
        )

    def transparency_report(self) -> dict[str, object]:
        """Counts by category and by outcome — refusals included (SIG-GOV-011).

        The grouping/period metadata is the policy-data shape; the counts are over the
        recorded submissions (by category) and dispositions (by outcome), so a refusal
        is counted exactly like every other outcome.
        """
        by_category = {cat: 0 for cat in sorted(known_categories())}
        for s in self._submissions:
            by_category[s.category] = by_category.get(s.category, 0) + 1
        by_outcome = {out: 0 for out in sorted(known_outcomes())}
        for d in self._dispositions:
            by_outcome[d.outcome] = by_outcome.get(d.outcome, 0) + 1
        shape = transparency_report_shape()
        return {
            "grouping": shape,
            "by_category": by_category,
            "by_outcome": by_outcome,
            "submissions_total": len(self._submissions),
            "dispositions_total": len(self._dispositions),
        }

    def _has_submission(self, submission_id: str) -> bool:
        return any(s.submission_id == submission_id for s in self._submissions)
