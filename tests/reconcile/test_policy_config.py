# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Policy-versus-configuration reconciliation (§29.6, SIG-RECON-044)."""

from __future__ import annotations

import pytest
from reconcile.model import POLICY_CONFIGURATION_DIVERGENCE, Evidence
from reconcile.policy_config import (
    PROHIBITED,
    REQUIRED,
    ConfigurationState,
    PolicyStatement,
    reconcile_policy_configuration,
)

CAP = "immigration_related_use"


def _ev(tag: str) -> Evidence:
    return Evidence(
        source_id=f"src:{tag}",
        source_family=tag,
        artifact_type="policy_document",
        stable_locator=f"https://example/{tag}",
        capture_digest="c" + "0" * 40,
        locator={"page": 1},
    )


def test_canonical_immigration_divergence_is_a_first_class_finding() -> None:
    # SIG-RECON-044 / OL-8.12-02: written policy prohibits immigration-related use
    # while the immigration hotlist is enabled.
    policy = PolicyStatement(
        subject_id="org:pd", capability=CAP, stance=PROHIBITED, evidence=_ev("policy")
    )
    config = ConfigurationState(
        subject_id="org:pd",
        capability=CAP,
        enabled=True,
        detail="immigration hotlist enabled",
        evidence=_ev("config"),
    )
    res = reconcile_policy_configuration(policy, config)
    assert res.divergent is True
    assert res.contradiction is not None
    assert res.contradiction.contradiction_type == POLICY_CONFIGURATION_DIVERGENCE
    # both sides' evidence retained
    assert len(res.contradiction.evidence) == 2
    assert res.task is not None
    assert res.task.task_id in res.contradiction.research_task_ids


def test_divergence_must_not_be_collapsed() -> None:
    policy = PolicyStatement(subject_id="org:pd", capability=CAP, stance=PROHIBITED)
    config = ConfigurationState(subject_id="org:pd", capability=CAP, enabled=True)
    res = reconcile_policy_configuration(policy, config)
    with pytest.raises(NotImplementedError):
        res.collapse()
    # both sides remain individually inspectable
    assert res.policy.stance == PROHIBITED
    assert res.configuration.enabled is True


def test_agreement_is_not_a_finding() -> None:
    policy = PolicyStatement(subject_id="org:pd", capability=CAP, stance=PROHIBITED)
    config = ConfigurationState(subject_id="org:pd", capability=CAP, enabled=False)
    res = reconcile_policy_configuration(policy, config)
    assert res.divergent is False
    assert res.contradiction is None


def test_required_but_disabled_is_a_finding() -> None:
    policy = PolicyStatement(subject_id="org:pd", capability="audit_logging", stance=REQUIRED)
    config = ConfigurationState(subject_id="org:pd", capability="audit_logging", enabled=False)
    res = reconcile_policy_configuration(policy, config)
    assert res.divergent is True


def test_mismatched_capability_is_rejected() -> None:
    policy = PolicyStatement(subject_id="org:pd", capability="a", stance=PROHIBITED)
    config = ConfigurationState(subject_id="org:pd", capability="b", enabled=True)
    with pytest.raises(ValueError, match="capability"):
        reconcile_policy_configuration(policy, config)
