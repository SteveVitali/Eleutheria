# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The materialized :class:`~reconcile.model.Contradiction` entity + lifecycle (§31).

The entity and its append-only lifecycle transitions live on the dataclass in
:mod:`reconcile.model`; this module owns the orchestration around it — the three
things §31 requires the surrounding system to do with a materialized contradiction:

* **Materialize** a detected contradiction into an addressable entity with its own
  stable identity and its ``claim_ids`` (:func:`materialize`, SIG-RECON-053).
* **The manual brake** (:func:`forces_unresolved`, SIG-RECON-054): an *open*
  ``severity = blocking`` contradiction on a ``(subject, predicate)`` pair forces
  the resolver to ``UNRESOLVED`` (``U7``). A curator can stop publication of a
  value without deleting anything.
* **Publish, never hide** (:func:`publishable_view`, SIG-RECON-055): an open
  contradiction surfaces as an ``unresolved_conflict``; a resolved one stays
  visible in history. Resolution sets status; it never deletes.

It also defines the **detector→task contract** (SIG-RECON-057): every detector
that emits a contradiction MUST also emit a research task with a defined closing
condition. :func:`detector_task_violations` is the mechanical check the workflows'
conformance tests run over their outputs.

The materialized ``contradiction_id`` is **content-derived** (a hash of the
identity-bearing fields), not random, so materializing the same detected
contradiction twice yields the same id — the reproducibility contract of §28.7
(SIG-RECON-020) extends to the entity, not just the resolution.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from dataclasses import replace

from .model import Contradiction, ResearchTask

__all__ = [
    "derive_contradiction_id",
    "materialize",
    "forces_unresolved",
    "open_blocking_contradictions",
    "publishable_view",
    "DetectorTaskViolation",
    "detector_task_violations",
    "assert_detector_task_contract",
]


def derive_contradiction_id(contradiction: Contradiction) -> str:
    """A stable, content-derived identity for a contradiction (SIG-RECON-020).

    Derived from the identity-bearing fields (subject, predicate, type, and the
    disagreeing claim ids — falling back to the claim values when the contradiction
    has not been linked to claim rows). Deterministic: the same disagreement
    always materializes to the same ``contradiction_id``, so a recomputation
    supersedes the prior record rather than minting an unrelated one.
    """
    claim_key = (
        "|".join(sorted(contradiction.claim_ids))
        if contradiction.claim_ids
        else "|".join(sorted(repr(v) for v in contradiction.claim_values))
    )
    payload = "|".join(
        (
            contradiction.subject_id,
            contradiction.predicate_id,
            contradiction.contradiction_type,
            claim_key,
        )
    )
    return f"contradiction:{hashlib.sha256(payload.encode()).hexdigest()}"


def materialize(
    detected: Contradiction,
    *,
    claim_ids: Sequence[str] = (),
    contradiction_id: str | None = None,
) -> Contradiction:
    """Materialize a detected contradiction into an addressable entity (SIG-RECON-053).

    Assigns the disagreeing ``claim_ids`` (if the detector supplies them) and a
    stable identity. ``contradiction_id`` may be pinned (e.g. to a persisted uuid);
    otherwise it is content-derived so the operation is idempotent. The lifecycle
    ``status`` is left as-is (``open`` by default) — a freshly materialized
    contradiction is open and publishable.
    """
    entity = detected
    if claim_ids and not entity.claim_ids:
        entity = replace(entity, claim_ids=tuple(claim_ids))
    cid = contradiction_id or derive_contradiction_id(entity)
    return entity.with_identity(cid)


# --- SIG-RECON-054: the manual brake (severity=blocking forces U7) ------------


def open_blocking_contradictions(
    contradictions: Iterable[Contradiction],
    *,
    subject_id: str,
    predicate_id: str,
) -> tuple[Contradiction, ...]:
    """The open, blocking contradictions filed against one ``(subject, predicate)``."""
    return tuple(
        c
        for c in contradictions
        if c.subject_id == subject_id
        and c.predicate_id == predicate_id
        and c.is_open
        and c.is_blocking
    )


def forces_unresolved(
    contradictions: Iterable[Contradiction],
    *,
    subject_id: str,
    predicate_id: str,
) -> bool:
    """Whether an open blocking contradiction forces ``UNRESOLVED`` (``U7``).

    This is the value the resolver's ``blocking_contradiction`` argument takes
    (SIG-RECON-054): a curator who marks a contradiction ``severity = blocking``
    stops the value from publishing — without deleting anything — until they
    resolve or accept it. A resolved/accepted (non-open) blocking contradiction no
    longer brakes.
    """
    return bool(
        open_blocking_contradictions(
            contradictions, subject_id=subject_id, predicate_id=predicate_id
        )
    )


# --- SIG-RECON-055: publish, never hide ---------------------------------------


def publishable_view(contradictions: Iterable[Contradiction]) -> list[dict[str, object]]:
    """The publish/API projection of a set of contradictions (SIG-RECON-055).

    Every contradiction is included — open ones as ``unresolved_conflict``,
    settled ones with their own status so they stay visible in history. Nothing is
    suppressed; this is what a read surface (P14.1) renders and what proves an
    ``unresolved_conflict`` is publishable, not hidden.
    """
    return [c.public_view() for c in contradictions]


# --- SIG-RECON-057: the detector→task contract --------------------------------


class DetectorTaskViolation(ValueError):
    """A contradiction that breaks the detector→task contract (SIG-RECON-057)."""


def detector_task_violations(
    contradictions: Iterable[Contradiction],
    tasks: Iterable[ResearchTask],
) -> list[str]:
    """Check the detector→task contract over one detector's output (SIG-RECON-057).

    Every emitted contradiction MUST reference at least one research task
    (``research_task_ids``) that is present in ``tasks`` and carries a non-empty
    ``closing_condition``. Returns a human-readable list of violations (empty when
    the contract holds), so a conformance test can assert emptiness and report the
    offenders.
    """
    by_id = {t.task_id: t for t in tasks}
    violations: list[str] = []
    for c in contradictions:
        label = f"{c.contradiction_type} on {c.subject_id}/{c.predicate_id}"
        if not c.research_task_ids:
            violations.append(f"{label}: emits no research task (SIG-RECON-057)")
            continue
        for tid in c.research_task_ids:
            task = by_id.get(tid)
            if task is None:
                violations.append(f"{label}: research_task_id {tid!r} is not among emitted tasks")
            elif not task.closing_condition:
                violations.append(f"{label}: task {tid!r} has an empty closing_condition")
    return violations


def assert_detector_task_contract(
    contradictions: Iterable[Contradiction],
    tasks: Iterable[ResearchTask],
) -> None:
    """Raise :class:`DetectorTaskViolation` if the detector→task contract is broken."""
    violations = detector_task_violations(contradictions, tasks)
    if violations:
        raise DetectorTaskViolation("; ".join(violations))
