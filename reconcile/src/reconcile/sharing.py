# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Sharing-edge reconciliation (§29.3, SIG-RECON-034/035/036/037).

The three edge types of §12.2 (:data:`ACCESS_KINDS`) are reconciled **separately**
— there is no operation that merges them (SIG-RECON-034). The signal this workflow
protects is **asymmetry**: where A's export lists B but B's export does not list A,
SIG records both observations, emits a ``SHARING_ASYMMETRY`` contradiction, and
generates a research task — it never silently picks an explanation, because doing
so destroys the signal (SIG-RECON-035).

Two more invariants:

* A sharing edge from a single snapshot carries ``valid_from_kind = 'unknown'``
  (SIG-RECON-036); SIG never infers a start date from first observation.
* An ``observed_use`` edge MUST NOT create or imply a ``configured_access`` edge at
  L1, and vice versa (SIG-RECON-037). The inference (use implies access existed at
  the time of use) is available at L4, clearly labelled — never at L1.

This module owns the sharing-edge reconciliation logic (SIG-RECON-034/035/036/037);
downstream tickets (P11.1 portal, P12.2 access edges + closure) land edges *through*
this reconciler and MUST NOT fork it.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from .model import SHARING_ASYMMETRY, Contradiction, Evidence, Inference, ResearchTask

#: The three sharing edge types (§12.2, common.yaml AccessKind). Reconciled
#: separately; never merged.
ACCESS_KINDS: tuple[str, ...] = ("configured_access", "observed_use", "declared_policy")

DERIVATION_RULE = "use_implies_access/§29.3"
RULE_VERSION = "p08.2/1"


def _task_id() -> str:
    return f"task:{uuid.uuid4()}"


@dataclass(frozen=True)
class SharingObservation:
    """One directed sharing edge as attested by a single party's export/snapshot.

    ``asserted_by`` is the organization whose evidence produced this edge (so the
    reconciler can tell "A says A→B" from "B says A→B"); ``from_org`` / ``to_org``
    are the directed endpoints (A→B = *A shares with B*).
    """

    asserted_by: str
    from_org: str
    to_org: str
    access_kind: str
    observed_at: date
    from_single_snapshot: bool = True
    evidence: Evidence | None = None
    claim_id: str = ""

    def __post_init__(self) -> None:
        if self.access_kind not in ACCESS_KINDS:
            raise ValueError(
                f"unknown access_kind {self.access_kind!r} (§12.2 expects one of {ACCESS_KINDS})"
            )

    @property
    def valid_from_kind(self) -> str:
        """A single-snapshot edge's start is UNKNOWN, never inferred (SIG-RECON-036)."""
        return "unknown" if self.from_single_snapshot else "known"

    @property
    def direction(self) -> str:
        return "a_to_b"


@dataclass(frozen=True)
class ReconciledEdge:
    """A reconciled directed sharing edge, within a single access kind."""

    from_org: str
    to_org: str
    access_kind: str
    valid_from_kind: str
    corroborated: bool
    observations: tuple[SharingObservation, ...]
    direction: str = "a_to_b"


@dataclass(frozen=True)
class SharingReconciliation:
    """The §29.3 output — per access kind, kept strictly separate."""

    edges: tuple[ReconciledEdge, ...]
    contradictions: tuple[Contradiction, ...]
    tasks: tuple[ResearchTask, ...]


def _pair_key(from_org: str, to_org: str) -> tuple[str, str]:
    return (from_org, to_org)


def reconcile_sharing(
    observations: Sequence[SharingObservation],
) -> SharingReconciliation:
    """Reconcile sharing edges within each access kind (§29.3).

    Edges of different access kinds are never merged (SIG-RECON-034). Within one
    kind, a directed edge A→B attested by A is checked for its reverse B→A attested
    by B; a missing reverse is a ``SHARING_ASYMMETRY`` finding plus a research task
    (SIG-RECON-035), not a silently-chosen explanation.
    """
    edges: list[ReconciledEdge] = []
    contradictions: list[Contradiction] = []
    tasks: list[ResearchTask] = []

    for kind in ACCESS_KINDS:
        kind_obs = [o for o in observations if o.access_kind == kind]
        if not kind_obs:
            continue
        by_dir: dict[tuple[str, str], list[SharingObservation]] = {}
        for o in kind_obs:
            by_dir.setdefault(_pair_key(o.from_org, o.to_org), []).append(o)

        for (frm, to), obs in sorted(by_dir.items()):
            reverse = by_dir.get(_pair_key(to, frm), [])
            # Corroborated when the counterparty's own evidence attests the reverse.
            corroborated = any(r.asserted_by == to for r in reverse)
            asserted_by_from = any(o.asserted_by == frm for o in obs)
            edges.append(
                ReconciledEdge(
                    from_org=frm,
                    to_org=to,
                    access_kind=kind,
                    valid_from_kind=(
                        "unknown" if any(o.from_single_snapshot for o in obs) else "known"
                    ),
                    corroborated=corroborated,
                    observations=tuple(obs),
                )
            )
            if asserted_by_from and not corroborated:
                task = ResearchTask(
                    task_id=_task_id(),
                    task_type="resolve_sharing_asymmetry",
                    subject_id=frm,
                    closing_condition=(
                        f"Determine why {frm}'s {kind} export lists {to} but {to}'s "
                        "export does not reciprocate (stale export? one direction disabled? "
                        "different semantics? misidentification?)."
                    ),
                    detector_version=RULE_VERSION,
                    priority=0.65,
                    note=f"{kind} asymmetry {frm} -> {to}.",
                )
                tasks.append(task)
                contradictions.append(
                    Contradiction(
                        contradiction_type=SHARING_ASYMMETRY,
                        subject_id=frm,
                        predicate_id=f"{kind}_edge",
                        claim_values=(f"{frm}->{to}",),
                        note=(
                            f"{frm}'s {kind} export lists {to}, but {to}'s export does not "
                            f"list {frm}. Both observations retained; the explanation is a "
                            "finding, not a merge (SIG-RECON-035)."
                        ),
                        severity="notable",
                        evidence=tuple(o.evidence for o in obs if o.evidence is not None),
                        research_task_ids=(task.task_id,),
                    )
                )

    return SharingReconciliation(
        edges=tuple(edges),
        contradictions=tuple(contradictions),
        tasks=tuple(tasks),
    )


class L1InferenceForbidden(RuntimeError):
    """Raised on an attempt to derive one edge kind from another at L1 (SIG-RECON-037)."""


def infer_access_from_use(edge: ReconciledEdge) -> Inference:
    """Infer a ``configured_access`` edge from an ``observed_use`` edge — at **L4**.

    Use logically implies access existed at the time of use, but that inference is
    permitted only at L4, clearly labelled — never as an L1 edge (SIG-RECON-037).
    Returns a labelled :class:`Inference`; the caller MUST NOT write it as an
    observed L1 ``configured_access`` edge.
    """
    if edge.access_kind != "observed_use":
        raise L1InferenceForbidden(
            f"use->access inference applies to observed_use edges, not {edge.access_kind!r}"
        )
    return Inference(
        subject_id=edge.from_org,
        predicate_id="configured_access_edge",
        value={
            "from_org": edge.from_org,
            "to_org": edge.to_org,
            "access_kind": "configured_access",
        },
        derivation_rule=DERIVATION_RULE,
        rule_version=RULE_VERSION,
        input_claim_ids=tuple(o.claim_id for o in edge.observations if o.claim_id),
        confidence="probable",
        rationale=(
            f"{edge.from_org} was observed using {edge.to_org} on "
            f"{edge.from_org}->{edge.to_org}, so configured access existed at the time of "
            "use — an L4 inference, never an L1 configured_access edge (SIG-RECON-037)."
        ),
    )


__all__ = [
    "ACCESS_KINDS",
    "DERIVATION_RULE",
    "RULE_VERSION",
    "L1InferenceForbidden",
    "ReconciledEdge",
    "SharingObservation",
    "SharingReconciliation",
    "infer_access_from_use",
    "reconcile_sharing",
]
