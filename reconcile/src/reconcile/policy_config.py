# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Policy-versus-configuration reconciliation (§29.6, SIG-RECON-044).

Policy is not configuration (invariant P10). SIG MUST detect and surface
policy/configuration divergence as a **first-class finding**, carrying **both
sides' evidence**, and MUST NOT editorially collapse it. The canonical instance —
a written policy prohibiting immigration-related use alongside an *enabled*
immigration hotlist — MUST be expressible and renderable (OL-8.12-02).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from .model import POLICY_CONFIGURATION_DIVERGENCE, Contradiction, Evidence, ResearchTask

RULE_VERSION = "p08.2/1"

#: Policy stances toward a capability (§11.13–11.14).
PROHIBITED = "prohibited"
PERMITTED = "permitted"
REQUIRED = "required"


def _task_id() -> str:
    return f"task:{uuid.uuid4()}"


@dataclass(frozen=True)
class PolicyStatement:
    """A written-policy stance toward a capability (the ``declared_policy`` side)."""

    subject_id: str
    capability: str
    stance: str  # PROHIBITED | PERMITTED | REQUIRED
    evidence: Evidence | None = None
    claim_id: str = ""


@dataclass(frozen=True)
class ConfigurationState:
    """The observed configured reality for a capability (the ``configured`` side)."""

    subject_id: str
    capability: str
    enabled: bool
    detail: str = ""
    evidence: Evidence | None = None
    claim_id: str = ""


@dataclass(frozen=True)
class PolicyConfigResult:
    """The §29.6 finding — both sides retained, never collapsed."""

    subject_id: str
    capability: str
    policy: PolicyStatement
    configuration: ConfigurationState
    divergent: bool
    contradiction: Contradiction | None
    task: ResearchTask | None

    def collapse(self) -> str:  # pragma: no cover - the point is that it raises
        raise NotImplementedError(
            "policy/configuration divergence MUST NOT be editorially collapsed; both "
            "sides are shown with their evidence (SIG-RECON-044)"
        )


def _is_divergent(policy: PolicyStatement, configuration: ConfigurationState) -> bool:
    if policy.stance == PROHIBITED and configuration.enabled:
        return True
    if policy.stance == REQUIRED and not configuration.enabled:
        return True
    return False


def reconcile_policy_configuration(
    policy: PolicyStatement,
    configuration: ConfigurationState,
) -> PolicyConfigResult:
    """Surface policy/configuration divergence as a first-class finding (§29.6).

    When the written policy and the configured reality disagree (the canonical case:
    a policy prohibiting immigration-related use with the immigration hotlist
    enabled), emit a ``policy_configuration_divergence`` contradiction carrying both
    sides' evidence and a research task. The two sides are never merged.
    """
    if policy.capability != configuration.capability:
        raise ValueError(
            f"policy capability {policy.capability!r} != configuration capability "
            f"{configuration.capability!r}; reconcile the same capability"
        )
    if not _is_divergent(policy, configuration):
        return PolicyConfigResult(
            subject_id=policy.subject_id,
            capability=policy.capability,
            policy=policy,
            configuration=configuration,
            divergent=False,
            contradiction=None,
            task=None,
        )

    note = (
        f"Written policy {policy.stance} {policy.capability!r}, but the configured state is "
        f"{'enabled' if configuration.enabled else 'disabled'}"
        f"{f' ({configuration.detail})' if configuration.detail else ''}. "
        "Both sides retained with their evidence; not collapsed (SIG-RECON-044)."
    )
    task = ResearchTask(
        task_id=_task_id(),
        task_type="reconcile_policy_configuration_divergence",
        subject_id=policy.subject_id,
        closing_condition=(
            f"Resolve why the written policy and the configured state of "
            f"{policy.capability!r} disagree (policy stale? config unauthorized? "
            "enforcement gap?)."
        ),
        detector_version=RULE_VERSION,
        priority=0.75,
        note=note,
    )
    contradiction = Contradiction(
        contradiction_type=POLICY_CONFIGURATION_DIVERGENCE,
        subject_id=policy.subject_id,
        predicate_id=f"policy_vs_config:{policy.capability}",
        claim_values=(f"policy:{policy.stance}", f"configured:{configuration.enabled}"),
        note=note,
        severity="notable",
        evidence=tuple(e for e in (policy.evidence, configuration.evidence) if e is not None),
        research_task_ids=(task.task_id,),
    )
    return PolicyConfigResult(
        subject_id=policy.subject_id,
        capability=policy.capability,
        policy=policy,
        configuration=configuration,
        divergent=True,
        contradiction=contradiction,
        task=task,
    )


__all__ = [
    "PERMITTED",
    "PROHIBITED",
    "REQUIRED",
    "RULE_VERSION",
    "ConfigurationState",
    "PolicyConfigResult",
    "PolicyStatement",
    "reconcile_policy_configuration",
]
