# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The anonymous corrections/dispute intake ops loop (P29.1, §36/§45, ADR-100)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from policy.corrections_intake import (
    CorrectionsIntake,
    DisputeSubmission,
    IntakeError,
    known_categories,
    known_outcomes,
)

_T0 = datetime(2026, 1, 1, tzinfo=UTC)
_T1 = datetime(2026, 6, 1, tzinfo=UTC)
_T2 = datetime(2026, 9, 1, tzinfo=UTC)


def test_intake_accepts_anonymous_no_account_submission() -> None:
    intake = CorrectionsIntake()
    sub = intake.submit(
        submission_id="d1",
        category="factual_error",
        subject="agency:okcpd",
        description="operator is wrong",
        at=_T1,
    )
    assert sub.reporter == "anonymous"
    assert sub.is_anonymous
    assert intake.submissions() == (sub,)


def test_submission_model_has_no_forced_identity_field() -> None:
    # No personal field beyond an optional self-provided contact (SIG-GOV-002).
    import dataclasses

    fields = {f.name for f in dataclasses.fields(DisputeSubmission)}
    assert not fields & {"name", "real_name", "legal_name", "email", "ip"}


def test_unknown_category_is_refused() -> None:
    intake = CorrectionsIntake()
    with pytest.raises(IntakeError):
        intake.submit(
            submission_id="d1", category="not_a_category", subject="s", description="", at=_T1
        )


def test_only_legal_demand_may_require_identity() -> None:
    assert CorrectionsIntake.category_requires_identity("legal_demand") is True
    assert CorrectionsIntake.category_requires_identity("privacy_harm") is False
    assert CorrectionsIntake.category_requires_identity("factual_error") is False


def test_correct_disposition_writes_append_only_correction_preserving_history() -> None:
    intake = CorrectionsIntake()
    # SIG already believes something about the subject as of _T0.
    intake.belief_log.assert_value("agency:okcpd", "Flock", at=_T0)
    intake.submit(
        submission_id="d1",
        category="factual_error",
        subject="agency:okcpd",
        description="it's Motorola, not Flock",
        at=_T1,
    )
    rec = intake.dispose(
        submission_id="d1",
        outcome="correct",
        reason="records show Motorola",
        at=_T2,
        actor="operator-1",
        subject="agency:okcpd",
        corrected_value="Motorola",
    )
    assert rec.outcome == "correct"
    assert rec.actor == "operator-1"
    # Append-only: the prior value still resolves at its belief-time (SIG-GOV-005).
    assert intake.belief_log.value_as_of_belief("agency:okcpd", _T0) == "Flock"
    assert intake.belief_log.value_as_of_belief("agency:okcpd", _T2) == "Motorola"


def test_correct_without_subject_and_value_is_refused() -> None:
    intake = CorrectionsIntake()
    intake.submit(submission_id="d1", category="factual_error", subject="s", description="", at=_T1)
    with pytest.raises(IntakeError):
        intake.dispose(submission_id="d1", outcome="correct", reason="r", at=_T2, actor="op")


def test_refusal_is_a_real_outcome_but_still_needs_a_reason() -> None:
    intake = CorrectionsIntake()
    intake.submit(submission_id="d1", category="factual_error", subject="s", description="", at=_T1)
    # Refusal is permitted...
    assert "refuse" in known_outcomes()
    rec = intake.dispose(
        submission_id="d1",
        outcome="refuse",
        reason="the claim is accurate and evidenced; declined with reasoning",
        at=_T2,
        actor="operator-1",
    )
    assert rec.outcome == "refuse"
    # ...but a reasonless disposition (even a refusal) is refused (SIG-GOV-004).
    with pytest.raises(IntakeError):
        intake.dispose(submission_id="d1", outcome="refuse", reason="", at=_T2, actor="operator-1")


def test_disposition_requires_actor_and_an_existing_submission() -> None:
    intake = CorrectionsIntake()
    intake.submit(submission_id="d1", category="factual_error", subject="s", description="", at=_T1)
    with pytest.raises(IntakeError):
        intake.dispose(submission_id="d1", outcome="annotate", reason="r", at=_T2, actor="")
    with pytest.raises(IntakeError):
        intake.dispose(submission_id="nope", outcome="annotate", reason="r", at=_T2, actor="op")


def test_transparency_report_counts_including_refusals() -> None:
    intake = CorrectionsIntake()
    intake.submit(submission_id="d1", category="privacy_harm", subject="s1", description="", at=_T1)
    intake.submit(
        submission_id="d2", category="factual_error", subject="s2", description="", at=_T1
    )
    intake.dispose(submission_id="d1", outcome="suppress", reason="harm", at=_T2, actor="op")
    intake.dispose(submission_id="d2", outcome="refuse", reason="accurate", at=_T2, actor="op")
    report = intake.transparency_report()
    assert report["by_category"]["privacy_harm"] == 1
    assert report["by_category"]["factual_error"] == 1
    assert report["by_outcome"]["suppress"] == 1
    assert report["by_outcome"]["refuse"] == 1  # refusals ARE counted (SIG-GOV-011)
    assert report["submissions_total"] == 2
    assert report["dispositions_total"] == 2
    # Every category/outcome the policy data names has a bucket.
    assert set(report["by_category"]) == set(known_categories())
    assert set(report["by_outcome"]) == set(known_outcomes())


def test_records_are_append_only_no_mutation_path() -> None:
    intake = CorrectionsIntake()
    # A change of decision is a NEW disposition row, never a mutation.
    intake.submit(submission_id="d1", category="factual_error", subject="s", description="", at=_T1)
    intake.dispose(submission_id="d1", outcome="annotate", reason="first", at=_T1, actor="op")
    intake.dispose(submission_id="d1", outcome="refuse", reason="reconsidered", at=_T2, actor="op")
    history = intake.dispositions(submission_id="d1")
    assert [d.outcome for d in history] == ["annotate", "refuse"]
