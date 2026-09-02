# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Corrections/suppression/deletion primitives + the takedown table (§45)."""

from __future__ import annotations

from datetime import datetime

import pytest
from policy.governance import BeliefLog

from policy import governance

MAY = datetime(2026, 5, 1)
JUNE = datetime(2026, 6, 1)
AUG = datetime(2026, 8, 20)


def _corrected_log() -> BeliefLog:
    """The §16.6 worked example: '25 cameras' on 2026-05-01, corrected to '225' on 2026-08-20."""
    log = BeliefLog()
    log.assert_value("device-42.camera_count", "25", at=MAY)
    log.correct("device-42.camera_count", "225", reason="extraction_error", at=AUG)
    return log


def test_correction_preserves_prior_belief() -> None:
    # SIG-GOV-005 / §16.6: a query at a prior as_of_belief still returns the old value,
    # and the current belief is the correction. No deletion, no overwrite.
    log = _corrected_log()
    assert log.value_as_of_belief("device-42.camera_count", JUNE) == "25"
    assert log.value_as_of_belief("device-42.camera_count", AUG) == "225"


def test_correction_is_a_new_assertion_not_a_deletion() -> None:
    # The append-only invariant: correcting appends; the prior row survives with a
    # closed belief interval and the new one points back at what it revises.
    log = _corrected_log()
    assertions = log._assertions  # noqa: SLF001 — asserting the append-only shape
    assert len(assertions) == 2
    prior, correction = assertions
    assert prior.value == "25" and prior.belief_to == AUG  # closed, not deleted
    assert correction.value == "225"
    assert correction.revises == 0
    assert correction.correction_reason == "extraction_error"


def test_correcting_an_unknown_subject_raises() -> None:
    log = BeliefLog()
    with pytest.raises(governance.GovernanceError):
        log.correct("nope", "x", reason="r", at=AUG)


def test_suppression_is_distinct_from_deletion() -> None:
    # SIG-GOV-007: suppression removes material from public surfaces while retaining
    # it internally under the sealed tier — the value survives, the public view does not.
    log = BeliefLog()
    log.assert_value("claim-7", "sensitive value", at=MAY)
    log.suppress("claim-7", author="editor-a", rationale="valid privacy demand")

    assert log.public_value_as_of_belief("claim-7", AUG) is None  # hidden from public
    assert log.value_as_of_belief("claim-7", AUG) == "sensitive value"  # retained internally

    open_row = log._assertions[log._open_id("claim-7")]  # noqa: SLF001
    assert open_row.suppressed is True
    assert open_row.tier == governance.SEALED_TIER
    assert open_row.suppression_author == "editor-a"
    assert open_row.suppression_rationale == "valid privacy demand"


def test_suppression_requires_author_and_rationale() -> None:
    log = BeliefLog()
    log.assert_value("claim-7", "v", at=MAY)
    with pytest.raises(governance.GovernanceError):
        log.suppress("claim-7", author="", rationale="x")
    with pytest.raises(governance.GovernanceError):
        log.suppress("claim-7", author="editor-a", rationale="")


def test_deletion_requires_two_person_auth_and_leaves_tombstone() -> None:
    # SIG-GOV-008: true deletion needs two distinct authorizers and leaves a tombstone
    # recording category + date, never content. Unlike suppression, the value is gone.
    log = BeliefLog()
    log.assert_value("claim-9", "must-not-hold", at=MAY)

    with pytest.raises(governance.DeletionAuthorizationError):
        log.delete("claim-9", category="illegal_content", authorizers=("solo", "solo"), at=AUG)
    with pytest.raises(governance.DeletionAuthorizationError):
        log.delete("claim-9", category="illegal_content", authorizers=("solo", ""), at=AUG)

    log.delete("claim-9", category="illegal_content", authorizers=("editor-a", "editor-b"), at=AUG)
    assert log.value_as_of_belief("claim-9", AUG) is None  # content gone
    tomb = log.tombstone_for("claim-9")
    assert tomb is not None
    assert tomb.category == "illegal_content"
    assert tomb.date == AUG
    assert "must-not-hold" not in (tomb.category,)  # tombstone never records content


def test_sla_prioritises_privacy_and_safety() -> None:
    # SIG-GOV-003: privacy-harm and safety/security rank above all others, including
    # above factual corrections.
    cats = governance.intake_categories()
    priority = {c["id"]: c["priority"] for c in cats}
    assert priority["privacy_harm"] < priority["factual_error"]
    assert priority["security_concern"] < priority["factual_error"]
    assert priority["privacy_harm"] < priority["legal_demand"]
    # every category publishes an SLA (SIG-GOV-003).
    assert all(c["sla_hours"] > 0 for c in cats)


def test_intake_categories_cover_the_required_kinds() -> None:
    # SIG-GOV-001: factual error, privacy harm, legal demand, security concern, copyright.
    ids = {c["id"] for c in governance.intake_categories()}
    assert {
        "factual_error",
        "privacy_harm",
        "legal_demand",
        "security_concern",
        "copyright_claim",
    } <= ids


def test_intake_does_not_require_identity_by_default() -> None:
    # SIG-GOV-002: intake must not require identifying the submitter, except a legal
    # demand that requires standing.
    assert governance.identity_required_for("privacy_harm") is False
    assert governance.identity_required_for("factual_error") is False
    assert governance.identity_required_for("legal_demand") is True


def test_permitted_outcomes_include_refusal() -> None:
    # SIG-GOV-004: refuse-with-published-reasoning is a real, exercisable outcome.
    outcomes = {o["id"]: o for o in governance.permitted_outcomes()}
    assert {"correct", "annotate", "suppress", "delete", "refuse"} <= set(outcomes)
    assert outcomes["refuse"].get("requires_published_reasoning") is True
    # suppression is non-destructive; deletion is the only destructive outcome.
    assert outcomes["suppress"]["destructive"] is False
    assert outcomes["delete"]["destructive"] is True


def test_transparency_report_groups_category_by_outcome_including_refusals() -> None:
    # SIG-GOV-011: periodic counts by category and outcome, refusals included.
    shape = governance.transparency_report_shape()
    assert shape["group_by"] == ["category", "outcome"]
    assert shape["include_refusals"] is True
    assert shape["period"]
