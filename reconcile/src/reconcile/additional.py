# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Additional reconciliation workflows (§29.8, SIG-RECON-046).

Four further workflows the spec requires, each following the same discipline as
§29.1: keep the distinct bases distinct, and surface disagreement as a finding
rather than a collapsed number.

* **Cost / contract-value** — contract value vs invoiced total vs budget line vs
  cooperative SKU price are distinct bases; their deltas are findings.
* **Organization-existence** — an organization named in a network list that no
  registry knows (§14.4) is a finding (phantom, alias, or genuinely unregistered),
  never silently created or silently dropped.
* **Capability** — does org X have capability Y, across disagreeing sources,
  respecting the **marketed-vs-configured** distinction (SIG-ONTO-018): a marketed
  capability never implies a configured one.
* **Geographic-coverage** — coverage claims at different scopes are distinct; a
  disagreement within one scope is a finding.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from .model import IDENTITY_AMBIGUITY, VALUE_DISAGREEMENT, Contradiction, Evidence, ResearchTask

RULE_VERSION = "p08.2/1"


def _task_id() -> str:
    return f"task:{uuid.uuid4()}"


# --- cost / contract-value reconciliation -------------------------------------

#: The distinct cost bases (§29.8). Never conflated into one "cost".
COST_BASES: tuple[str, ...] = (
    "contract_value",
    "invoiced_total",
    "budget_line",
    "cooperative_sku_price",
)


@dataclass(frozen=True)
class CostClaim:
    """A monetary claim, tagged to exactly one cost basis (amounts in cents)."""

    basis: str
    amount_cents: int
    observed_at: date
    currency: str = "USD"
    evidence: Evidence | None = None
    claim_id: str = ""

    def __post_init__(self) -> None:
        if self.basis not in COST_BASES:
            raise ValueError(f"unknown cost basis {self.basis!r} (§29.8 expects {COST_BASES})")


@dataclass(frozen=True)
class CostReconciliation:
    subject_id: str
    values: dict[str, int | None]
    contradictions: tuple[Contradiction, ...]
    tasks: tuple[ResearchTask, ...]


def reconcile_cost(subject_id: str, claims: Sequence[CostClaim]) -> CostReconciliation:
    """Resolve each cost basis on its own and surface the deltas (§29.8)."""
    currencies = {c.currency for c in claims}
    if len(currencies) > 1:
        raise ValueError(
            f"mixed currencies {sorted(currencies)}; normalize upstream before diffing"
        )
    by_basis: dict[str, list[CostClaim]] = {b: [] for b in COST_BASES}
    for c in claims:
        by_basis[c.basis].append(c)
    values: dict[str, int | None] = {
        b: (max(cs, key=lambda c: (c.observed_at, c.claim_id)).amount_cents if cs else None)
        for b, cs in by_basis.items()
    }
    contradictions: list[Contradiction] = []
    tasks: list[ResearchTask] = []
    present = [(b, v) for b, v in values.items() if v is not None]
    for (ba, va), (bb, vb) in zip(present, present[1:], strict=False):
        if va == vb:
            continue
        task = ResearchTask(
            task_id=_task_id(),
            task_type="reconcile_cost_delta",
            subject_id=subject_id,
            closing_condition=f"Explain the {abs(va - vb)}c gap between {ba} and {bb}.",
            detector_version=RULE_VERSION,
            priority=0.5,
            note=f"{ba} ({va}c) != {bb} ({vb}c).",
        )
        tasks.append(task)
        contradictions.append(
            Contradiction(
                contradiction_type=VALUE_DISAGREEMENT,
                subject_id=subject_id,
                predicate_id=f"{ba}__vs__{bb}",
                claim_values=(va, vb),
                note=f"Cost bases disagree: {ba} ({va}c) vs {bb} ({vb}c); both retained (§29.8).",
                severity="notable",
                research_task_ids=(task.task_id,),
            )
        )
    return CostReconciliation(subject_id, values, tuple(contradictions), tuple(tasks))


# --- organization-existence reconciliation (§14.4) ----------------------------


@dataclass(frozen=True)
class OrgExistenceFinding:
    org_name: str
    known: bool
    contradiction: Contradiction | None
    task: ResearchTask | None


def reconcile_organization_existence(
    named_orgs: Sequence[str],
    known_registry_ids: set[str],
    *,
    named_in: str = "a network list",
) -> tuple[OrgExistenceFinding, ...]:
    """Flag organizations named in a list that no registry knows (§14.4, §29.8).

    Such an organization is neither silently created nor silently dropped: it is a
    finding (a phantom, an alias, or a genuinely unregistered body) with a research
    task to establish its identity.
    """
    findings: list[OrgExistenceFinding] = []
    for name in named_orgs:
        if name in known_registry_ids:
            findings.append(OrgExistenceFinding(name, True, None, None))
            continue
        task = ResearchTask(
            task_id=_task_id(),
            task_type="establish_organization_existence",
            subject_id=name,
            closing_condition=(
                f"Establish whether {name!r} (named in {named_in}) is a phantom, an alias of "
                "a known organization, or a genuinely unregistered body."
            ),
            detector_version=RULE_VERSION,
            priority=0.55,
            note=f"{name!r} named in {named_in} but unknown to any registry (§14.4).",
        )
        contradiction = Contradiction(
            contradiction_type=IDENTITY_AMBIGUITY,
            subject_id=name,
            predicate_id="organization_exists",
            claim_values=(name,),
            note=f"{name!r} is named in {named_in} but no registry knows it (§14.4).",
            severity="notable",
            research_task_ids=(task.task_id,),
        )
        findings.append(OrgExistenceFinding(name, False, contradiction, task))
    return tuple(findings)


# --- capability reconciliation (SIG-ONTO-018) ---------------------------------

#: Capability assertion kinds (SIG-ONTO-018). Marketed != configured != observed.
CAPABILITY_KINDS: tuple[str, ...] = ("marketed", "configured", "observed")


@dataclass(frozen=True)
class CapabilityClaim:
    org_id: str
    capability: str
    kind: str  # marketed | configured | observed
    present: bool
    observed_at: date
    evidence: Evidence | None = None
    claim_id: str = ""

    def __post_init__(self) -> None:
        if self.kind not in CAPABILITY_KINDS:
            raise ValueError(f"unknown capability kind {self.kind!r} (expects {CAPABILITY_KINDS})")


@dataclass(frozen=True)
class CapabilityReconciliation:
    org_id: str
    capability: str
    by_kind: dict[str, bool | None]
    contradictions: tuple[Contradiction, ...]
    tasks: tuple[ResearchTask, ...]


def reconcile_capability(
    org_id: str, capability: str, claims: Sequence[CapabilityClaim]
) -> CapabilityReconciliation:
    """Reconcile whether org X has capability Y across kinds (§29.8, SIG-ONTO-018).

    Each kind (marketed / configured / observed) is resolved on its own — a
    *marketed* capability never implies a *configured* one. Within-kind
    disagreement across sources is surfaced as a finding.
    """
    by_kind: dict[str, bool | None] = {k: None for k in CAPABILITY_KINDS}
    contradictions: list[Contradiction] = []
    tasks: list[ResearchTask] = []
    for kind in CAPABILITY_KINDS:
        kind_claims = [c for c in claims if c.kind == kind and c.capability == capability]
        if not kind_claims:
            continue
        votes = {c.present for c in kind_claims}
        if len(votes) > 1:
            task = ResearchTask(
                task_id=_task_id(),
                task_type="reconcile_capability_disagreement",
                subject_id=org_id,
                closing_condition=(
                    f"Resolve whether {org_id} has {capability!r} ({kind}); sources disagree."
                ),
                detector_version=RULE_VERSION,
                priority=0.6,
                note=f"{kind} claims for {capability!r} disagree.",
            )
            tasks.append(task)
            contradictions.append(
                Contradiction(
                    contradiction_type=VALUE_DISAGREEMENT,
                    subject_id=org_id,
                    predicate_id=f"capability:{capability}:{kind}",
                    claim_values=tuple(sorted(str(v) for v in votes)),
                    note=f"{kind} sources disagree on {capability!r}; both retained (§29.8).",
                    severity="notable",
                    research_task_ids=(task.task_id,),
                )
            )
            # Disagreement leaves the kind unresolved rather than picking a side.
            by_kind[kind] = None
        else:
            # Prefer the latest observation within the kind.
            latest = max(kind_claims, key=lambda c: (c.observed_at, c.claim_id))
            by_kind[kind] = latest.present
    return CapabilityReconciliation(
        org_id, capability, by_kind, tuple(contradictions), tuple(tasks)
    )


# --- geographic-coverage reconciliation ---------------------------------------


@dataclass(frozen=True)
class CoverageClaim:
    subject_id: str
    scope: str  # e.g. "city_limits", "metro", "county"
    area_label: str
    observed_at: date
    evidence: Evidence | None = None
    claim_id: str = ""


@dataclass(frozen=True)
class CoverageReconciliation:
    subject_id: str
    by_scope: dict[str, str | None]
    contradictions: tuple[Contradiction, ...]
    tasks: tuple[ResearchTask, ...]


def reconcile_geographic_coverage(
    subject_id: str, claims: Sequence[CoverageClaim]
) -> CoverageReconciliation:
    """Reconcile coverage claims, keeping distinct scopes distinct (§29.8).

    Coverage at different scopes (city limits vs metro vs county) are distinct
    answers, never conflated; a within-scope disagreement is a finding.
    """
    by_scope_claims: dict[str, list[CoverageClaim]] = {}
    for c in claims:
        by_scope_claims.setdefault(c.scope, []).append(c)
    by_scope: dict[str, str | None] = {}
    contradictions: list[Contradiction] = []
    tasks: list[ResearchTask] = []
    for scope, cs in sorted(by_scope_claims.items()):
        labels = {c.area_label for c in cs}
        if len(labels) > 1:
            task = ResearchTask(
                task_id=_task_id(),
                task_type="reconcile_coverage_disagreement",
                subject_id=subject_id,
                closing_condition=f"Resolve the disagreeing {scope} coverage claims.",
                detector_version=RULE_VERSION,
                priority=0.5,
                note=f"{scope} coverage claims disagree: {sorted(labels)}.",
            )
            tasks.append(task)
            contradictions.append(
                Contradiction(
                    contradiction_type=VALUE_DISAGREEMENT,
                    subject_id=subject_id,
                    predicate_id=f"coverage:{scope}",
                    claim_values=tuple(sorted(labels)),
                    note=f"Disagreeing {scope} coverage; both retained (§29.8).",
                    severity="notable",
                    research_task_ids=(task.task_id,),
                )
            )
            by_scope[scope] = None
        else:
            by_scope[scope] = labels.pop()
    return CoverageReconciliation(subject_id, by_scope, tuple(contradictions), tuple(tasks))


__all__ = [
    "CAPABILITY_KINDS",
    "COST_BASES",
    "RULE_VERSION",
    "CapabilityClaim",
    "CapabilityReconciliation",
    "CostClaim",
    "CostReconciliation",
    "CoverageClaim",
    "CoverageReconciliation",
    "OrgExistenceFinding",
    "reconcile_capability",
    "reconcile_cost",
    "reconcile_geographic_coverage",
    "reconcile_organization_existence",
]
