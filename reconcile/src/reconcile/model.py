# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The minimal reconciliation value objects the P06.1 slice needs.

These are lightweight, immutable views aligned with the persisted shapes the full
engine (P08) will use — the ``contradiction`` and ``research_task`` tables of
``db/deploy/graph_annotations.sql`` — without pulling in the database. They are
deliberately thin: the slice proves the *shape* end to end (see ADR-031).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

# --- the count predicates and their bases (§29.1, SIG-RECON-026) --------------

#: The six count predicates that MUST stay distinct and never be conflated.
COUNT_BASES: tuple[str, ...] = (
    "contracted",
    "invoiced",
    "installed",
    "active",
    "mapped",
    "claimed",
)


def predicate_for_basis(basis: str) -> str:
    """The registry predicate id for a count basis (e.g. ``"active"`` ->
    ``"active_device_count"``)."""
    if basis not in COUNT_BASES:
        raise ValueError(f"unknown count basis {basis!r} (§29.1 SIG-RECON-026)")
    return f"{basis}_device_count"


def basis_for_predicate(predicate_id: str) -> str:
    """Inverse of :func:`predicate_for_basis`."""
    basis = predicate_id.removesuffix("_device_count")
    if basis not in COUNT_BASES:
        raise ValueError(f"{predicate_id!r} is not a count predicate (§29.1)")
    return basis


# --- contradiction type vocabulary (§31, docs §4932) --------------------------
# The canonical `contradiction_type` codomain; the slice exercises a subset.
PREDICATE_CONFLATION = "predicate_conflation"
VALUE_DISAGREEMENT = "value_disagreement"
POLICY_CONFIGURATION_DIVERGENCE = "policy_configuration_divergence"
COUNT_BASIS_MISMATCH = "count_basis_mismatch"


@dataclass(frozen=True)
class Evidence:
    """The document-at-a-locator every material claim resolves to (§16, §D.4).

    ``stable_locator`` is the artifact's stable address (the URL/slug recorded on
    ``evidence_artifact``); ``locator`` is the exact anchor within it (selector +
    text span, page, cell, row).
    """

    source_id: str
    source_family: str
    artifact_type: str  # one of the registry artifact_genres, e.g. executed_contract
    stable_locator: str
    capture_digest: str
    locator: dict[str, object]
    excerpt: str = ""

    def resolves_to_document(self) -> bool:
        """Whether this evidence resolves to a document at a specific locator."""
        return bool(self.stable_locator and self.capture_digest and self.locator)


@dataclass(frozen=True)
class CountClaim:
    """One quantity claim about a count predicate, with its epistemics + evidence."""

    count_basis: str
    value: int
    reliability: str  # R1..R6
    integrity: str  # I1..I3
    observed_at: date
    genre: str  # artifact genre -> (genre x predicate) directness lookup
    evidence: Evidence
    structured_exact: bool = False  # machine-readable structured export + EXACT
    field_verified: bool = False
    scope_note: str | None = None  # e.g. "metro" vs "city limits"

    @property
    def predicate_id(self) -> str:
        return predicate_for_basis(self.count_basis)


@dataclass(frozen=True)
class ResearchTask:
    """A typed research task with a testable closing condition (§33.2, SIG-TASK-002)."""

    task_id: str
    task_type: str
    subject_id: str
    closing_condition: str
    detector_version: str
    priority: float = 0.5
    jurisdiction_id: str | None = None
    status: str = "generated"
    note: str = ""


@dataclass(frozen=True)
class Contradiction:
    """A first-class, addressable contradiction (§31, graph_annotations.sql)."""

    contradiction_type: str
    subject_id: str
    predicate_id: str
    claim_values: tuple[object, ...]
    note: str
    severity: str = "notable"
    status: str = "open"
    evidence: tuple[Evidence, ...] = ()
    research_task_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class CountResolution:
    """The resolution of ONE count predicate — its own answer, never merged."""

    count_basis: str
    predicate_id: str
    value: int | None
    weight: int | None
    winning_claim: CountClaim | None
    dissenting: tuple[CountClaim, ...]
    lower_bound: bool
    rationale: str
    resolution_status: str  # RESOLVED | INSUFFICIENT
    contradictions: tuple[Contradiction, ...] = ()


@dataclass(frozen=True)
class UnresolvedDelta:
    """A genuine finding: an unexplained gap between two count predicates (§29.1)."""

    higher_basis: str
    lower_basis: str
    delta: int
    interpretation: str
    task: ResearchTask


@dataclass(frozen=True)
class CountReconciliation:
    """The §29.1 / SIG-RECON-029 output object.

    It carries every count predicate with its own resolution, the unresolved
    deltas with their interpretation, the contradictions, and the generated
    research tasks. It MUST NOT emit a single "true count".
    """

    subject_id: str
    resolutions: dict[str, CountResolution]
    unresolved_deltas: tuple[UnresolvedDelta, ...] = ()
    contradictions: tuple[Contradiction, ...] = ()
    tasks: tuple[ResearchTask, ...] = field(default_factory=tuple)

    def true_count(self) -> int:  # pragma: no cover - the whole point is that there isn't one
        raise NotImplementedError(
            "there is no single true count — reconciliation is not aggregation (SIG-RECON-029)"
        )
