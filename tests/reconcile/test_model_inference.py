# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The shared L4 inference object and the contradiction-type vocabulary (§30, §31)."""

from __future__ import annotations

import pytest
from reconcile.model import (
    CONTRADICTION_TYPES,
    POLICY_CONFIGURATION_DIVERGENCE,
    PREDICATE_CONFLATION,
    SHARING_ASYMMETRY,
    Inference,
)


def test_contradiction_vocabulary_matches_the_spec_codomain() -> None:
    # docs/2_canonical_design_spec.md §4932 — the full contradiction_type codomain.
    assert CONTRADICTION_TYPES == {
        "value_disagreement",
        "predicate_conflation",
        "value_domain_mismatch",
        "sharing_asymmetry",
        "policy_configuration_divergence",
        "temporal_impossibility",
        "count_basis_mismatch",
        "identity_ambiguity",
        "undeclared_copying",
    }
    # the named constants are members
    assert PREDICATE_CONFLATION in CONTRADICTION_TYPES
    assert SHARING_ASYMMETRY in CONTRADICTION_TYPES
    assert POLICY_CONFIGURATION_DIVERGENCE in CONTRADICTION_TYPES


def _inf() -> Inference:
    return Inference(
        subject_id="s",
        predicate_id="attributed_operator",
        value="org:x",
        derivation_rule="rule",
        rule_version="v1",
        input_claim_ids=("c1",),
    )


def test_inference_is_l4_and_never_an_observation() -> None:
    inf = _inf()
    assert inf.layer == "L4"
    assert inf.is_observation is False
    assert inf.confidence == "probable"


def test_inference_is_never_auto_pushable_and_not_observable() -> None:
    inf = _inf()
    assert inf.pushable_to_osm is False
    with pytest.raises(NotImplementedError):
        inf.as_observed_operator()


def test_inference_layer_is_immutable_positional_default() -> None:
    # layer/pushable_to_osm are init=False, so they cannot be spoofed at construction.
    with pytest.raises(TypeError):
        Inference(  # type: ignore[call-arg]
            subject_id="s",
            predicate_id="p",
            value=1,
            derivation_rule="r",
            rule_version="v",
            input_claim_ids=(),
            layer="L1",
        )
