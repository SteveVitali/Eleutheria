# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Retention reconciliation (§29.5, SIG-RECON-043).

``policy_written_retention_days``, ``configured_retention_days``, and
``vendor_default_retention_days`` are **three predicates**, not one. Their
disagreement is a finding (routed to P10), never a value to average. Two guards
this workflow enforces:

* **Vendor defaults MUST NOT populate configuration** (SIG-ONTO-036): the "what the
  box ships with" value is never silently written into "what this deployment is set
  to."
* **A vendor's default change is not retroactive**: changing
  ``vendor_default_retention_days`` does not change any existing deployment's
  configured retention — a distinction with real-world instances.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from .model import Contradiction, Evidence, ResearchTask

#: The three retention predicates that MUST stay distinct (§29.5).
POLICY_WRITTEN = "policy_written_retention_days"
CONFIGURED = "configured_retention_days"
VENDOR_DEFAULT = "vendor_default_retention_days"
RETENTION_PREDICATES: tuple[str, ...] = (POLICY_WRITTEN, CONFIGURED, VENDOR_DEFAULT)

RULE_VERSION = "p08.2/1"


def _task_id() -> str:
    return f"task:{uuid.uuid4()}"


@dataclass(frozen=True)
class RetentionClaim:
    """One retention claim, tagged to exactly one of the three predicates."""

    predicate: str
    days: int
    observed_at: date
    evidence: Evidence | None = None
    claim_id: str = ""

    def __post_init__(self) -> None:
        if self.predicate not in RETENTION_PREDICATES:
            raise ValueError(
                f"unknown retention predicate {self.predicate!r} "
                f"(§29.5 expects one of {RETENTION_PREDICATES})"
            )


@dataclass(frozen=True)
class RetentionReconciliation:
    """The §29.5 output: the three predicates, each with its own value, plus the
    disagreements surfaced as findings."""

    subject_id: str
    values: dict[str, int | None]
    contradictions: tuple[Contradiction, ...]
    tasks: tuple[ResearchTask, ...]


def _latest(claims: Sequence[RetentionClaim]) -> RetentionClaim | None:
    return max(claims, default=None, key=lambda c: (c.observed_at, c.claim_id))


def reconcile_retention(
    subject_id: str, claims: Sequence[RetentionClaim]
) -> RetentionReconciliation:
    """Resolve each retention predicate on its own and surface disagreements (§29.5).

    The three predicates are kept distinct; where the *policy* and *configured*
    values disagree — or where the *configured* value diverges from the *vendor
    default* — the divergence is emitted as a finding with a research task, never
    collapsed to one number.
    """
    by_pred: dict[str, list[RetentionClaim]] = {p: [] for p in RETENTION_PREDICATES}
    for c in claims:
        by_pred[c.predicate].append(c)
    latest = {p: _latest(cs) for p, cs in by_pred.items()}
    values: dict[str, int | None] = {
        p: (c.days if c is not None else None) for p, c in latest.items()
    }

    contradictions: list[Contradiction] = []
    tasks: list[ResearchTask] = []

    def _finding(pred_a: str, pred_b: str, note: str) -> None:
        task = ResearchTask(
            task_id=_task_id(),
            task_type="reconcile_retention_divergence",
            subject_id=subject_id,
            closing_condition=(
                f"Explain the divergence between {pred_a} ({values[pred_a]}d) and "
                f"{pred_b} ({values[pred_b]}d)."
            ),
            detector_version=RULE_VERSION,
            priority=0.6,
            note=note,
        )
        tasks.append(task)
        contradictions.append(
            Contradiction(
                contradiction_type="value_disagreement",
                subject_id=subject_id,
                predicate_id=f"{pred_a}__vs__{pred_b}",
                claim_values=(values[pred_a], values[pred_b]),
                note=note,
                severity="notable",
                evidence=tuple(
                    c.evidence
                    for c in (latest[pred_a], latest[pred_b])
                    if c is not None and c.evidence is not None
                ),
                research_task_ids=(task.task_id,),
            )
        )

    # Policy vs configured: the compliance-relevant disagreement.
    if values[POLICY_WRITTEN] is not None and values[CONFIGURED] is not None:
        if values[POLICY_WRITTEN] != values[CONFIGURED]:
            _finding(
                POLICY_WRITTEN,
                CONFIGURED,
                "Written retention policy disagrees with the configured retention; "
                "both retained, neither collapsed (§29.5).",
            )
    # Configured vs vendor default: informative, but the vendor default is never
    # allowed to *become* the configured value (see populate_configured_from_vendor_default).
    if values[CONFIGURED] is not None and values[VENDOR_DEFAULT] is not None:
        if values[CONFIGURED] != values[VENDOR_DEFAULT]:
            _finding(
                CONFIGURED,
                VENDOR_DEFAULT,
                "Configured retention diverges from the vendor default; the default does "
                "not populate configuration (SIG-ONTO-036).",
            )

    return RetentionReconciliation(
        subject_id=subject_id,
        values=values,
        contradictions=tuple(contradictions),
        tasks=tuple(tasks),
    )


class VendorDefaultLeak(RuntimeError):
    """Raised on an attempt to populate configuration from a vendor default (SIG-ONTO-036)."""


def populate_configured_from_vendor_default(vendor_default_days: int) -> int:
    """Refuse to populate configuration from a vendor default (SIG-ONTO-036, §29.5)."""
    raise VendorDefaultLeak(
        f"vendor default ({vendor_default_days}d) MUST NOT populate configured_retention_days; "
        "the two are distinct predicates and the default is never assumed to be the setting "
        "(SIG-ONTO-036, SIG-RECON-043)"
    )


def apply_vendor_default_change(
    *, configured_days: int | None, new_vendor_default_days: int
) -> int | None:
    """A vendor default change is not retroactive (SIG-RECON-043).

    Returns the deployment's ``configured_days`` **unchanged** — a vendor changing
    its shipped default does not retroactively change an existing deployment's
    configured retention.
    """
    return configured_days


__all__ = [
    "CONFIGURED",
    "POLICY_WRITTEN",
    "RETENTION_PREDICATES",
    "RULE_VERSION",
    "VENDOR_DEFAULT",
    "RetentionClaim",
    "RetentionReconciliation",
    "VendorDefaultLeak",
    "apply_vendor_default_change",
    "populate_configured_from_vendor_default",
    "reconcile_retention",
]
