# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The shared publication-eligibility selector (P32.5 / ADR-124, SIG-TRUST-006).

Pure-layer contract tests — the DB parity tests live in
``tests/db/test_publication_dispositions.py`` (Docker-gated). These pin:

* the deterministic precedence (latest ``decided_at``, then ``disposition_seq``),
* the append-only override semantics (a LATER ``allow`` lifts an earlier deny —
  the "rollback" case — and a later deny overrides an earlier permit),
* the conjunction (disposition ∧ org status ∧ review flag ∧ subject/object
  entity eligibility) — one decision function for every consumer,
* the tombstone carrying ONLY the safe reason category + authority + policy
  version (never the privileged rationale), and
* ``publication-eligibility/1`` stamped on every decision.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from policy.eligibility import (
    POLICY_VERSION,
    Disposition,
    ReasonCategory,
    TargetKind,
    access_decision,
    claim_publication_decision,
    latest_disposition,
    new_disposition,
    organization_publication_decision,
)

T0 = datetime(2026, 6, 1, tzinfo=UTC)


def _rec(
    disposition: Disposition,
    *,
    at: datetime = T0,
    seq: int = 0,
    reason: ReasonCategory = ReasonCategory.SAFETY_WITHDRAWAL,
    authority: str = "reviewer:test",
    target_id: str = "00000000-0000-0000-0000-00000000000e",
) -> object:
    return new_disposition(
        target_kind=TargetKind.ENTITY,
        target_id=target_id,
        disposition=disposition,
        reason_category=reason,
        authority=authority,
        decided_at=at,
        seq=seq,
    )


# --- latest_disposition — precedence ----------------------------------------


def test_latest_disposition_picks_newest_decided_at() -> None:
    older = _rec(Disposition.WITHHOLD, at=T0)
    newer = _rec(Disposition.ALLOW, at=T0 + timedelta(days=1))
    eff = latest_disposition([older, newer])
    assert eff is newer


def test_latest_disposition_seq_breaks_exact_ties() -> None:
    low = _rec(Disposition.ALLOW, seq=1)
    high = _rec(Disposition.WITHDRAW, seq=2)
    eff = latest_disposition([low, high])
    assert eff is high  # recorded second wins the same instant


def test_latest_disposition_respects_the_time_pin() -> None:
    r1 = _rec(Disposition.WITHHOLD, at=T0)
    r2 = _rec(Disposition.ALLOW, at=T0 + timedelta(days=5))
    # As of T0+1d the effective is still the withhold — but CURRENT access
    # (at=None) sees the allow. The pin answers "what did policy say then" for
    # review; public access always evaluates now.
    assert latest_disposition([r1, r2], at=T0 + timedelta(days=1)) is r1
    assert latest_disposition([r1, r2]) is r2


def test_latest_disposition_empty() -> None:
    assert latest_disposition([]) is None


# --- organization_publication_decision — D-P31.5-2's gate --------------------


def test_org_flag_pending_review_denies() -> None:
    dec = organization_publication_decision(
        publication_review_required=True, status="active", effective=None
    )
    assert dec.permitted is False
    assert dec.reason_category is ReasonCategory.REVIEW_PENDING
    assert dec.policy_version == POLICY_VERSION


def test_org_flag_lifted_by_recorded_allow() -> None:
    allow = _rec(Disposition.ALLOW)
    dec = organization_publication_decision(
        publication_review_required=True, status="active", effective=allow
    )
    assert dec.permitted is True


def test_org_deny_disposition_beats_allowing_state() -> None:
    deny = _rec(Disposition.WITHHOLD, reason=ReasonCategory.REVIEW_DENIED)
    dec = organization_publication_decision(
        publication_review_required=False, status="active", effective=deny
    )
    assert dec.permitted is False
    assert dec.reason_category is ReasonCategory.REVIEW_DENIED
    assert dec.authority == "reviewer:test"


@pytest.mark.parametrize(
    "status,reason",
    [("withdrawn", ReasonCategory.SAFETY_WITHDRAWAL), ("suppressed", ReasonCategory.SUPPRESSED)],
)
def test_org_status_denies(status: str, reason: ReasonCategory) -> None:
    dec = organization_publication_decision(
        publication_review_required=False, status=status, effective=None
    )
    assert dec.permitted is False
    assert dec.reason_category is reason


def test_org_deny_disposition_beats_status_checks() -> None:
    # A recorded deny wins over every org-side signal (the row IS the authority).
    deny = _rec(Disposition.WITHDRAW, reason=ReasonCategory.RIGHTS_WITHDRAWAL)
    dec = organization_publication_decision(
        publication_review_required=True, status="active", effective=deny
    )
    assert dec.permitted is False
    assert dec.reason_category is ReasonCategory.RIGHTS_WITHDRAWAL


def test_org_plain_allow() -> None:
    dec = organization_publication_decision(
        publication_review_required=False, status="active", effective=None
    )
    assert dec.permitted is True


# --- claim_publication_decision — the claim conjunction ----------------------


def test_claim_deny_disposition() -> None:
    deny = _rec(Disposition.RESTRICT, reason=ReasonCategory.POLICY_RESTRICTION)
    dec = claim_publication_decision(effective=deny)
    assert dec.permitted is False
    assert dec.reason_category is ReasonCategory.POLICY_RESTRICTION


def test_claim_inherits_subject_denial() -> None:
    subject = organization_publication_decision(
        publication_review_required=True, status="active", effective=None
    )
    dec = claim_publication_decision(effective=None, subject=subject)
    assert dec.permitted is False
    assert dec.reason_category is ReasonCategory.REVIEW_PENDING


def test_claim_inherits_object_entity_denial() -> None:
    # The partner-organisation seam: a claim pointing AT a withheld entity
    # leaks its identity through object_entity — denied the same way.
    obj = organization_publication_decision(
        publication_review_required=False, status="withdrawn", effective=None
    )
    dec = claim_publication_decision(effective=None, object_entity=obj)
    assert dec.permitted is False


def test_claim_allow() -> None:
    assert claim_publication_decision(effective=None).permitted is True


# --- access_decision — the artifact/rollback branch --------------------------


def test_access_deny_on_artifact() -> None:
    deny = _rec(Disposition.WITHDRAW)
    assert access_decision(deny).permitted is False
    assert access_decision(None).permitted is True


# --- tombstone shape — safe fields only --------------------------------------


def test_tombstone_carries_safe_fields_only() -> None:
    deny = _rec(Disposition.WITHHOLD, reason=ReasonCategory.REVIEW_DENIED)
    dec = organization_publication_decision(
        publication_review_required=False, status="active", effective=deny
    )
    ts = dec.tombstone()
    assert ts["permitted"] is False
    assert ts["reason_category"] == "withheld_after_review"
    assert ts["authority"] == "reviewer:test"
    assert ts["policy_version"] == POLICY_VERSION
    # No rationale/decided_by/free-text field may appear on a tombstone.
    assert set(ts) == {"permitted", "reason_category", "authority", "policy_version"}


# --- new_disposition validation ----------------------------------------------


def test_new_disposition_requires_authority_and_target() -> None:
    with pytest.raises(ValueError):
        new_disposition(
            target_kind=TargetKind.CLAIM,
            target_id="",
            disposition=Disposition.WITHHOLD,
            reason_category=ReasonCategory.SAFETY_WITHDRAWAL,
            authority="x",
        )
    with pytest.raises(ValueError):
        new_disposition(
            target_kind=TargetKind.CLAIM,
            target_id="00000000-0000-0000-0000-00000000000c",
            disposition=Disposition.WITHHOLD,
            reason_category=ReasonCategory.SAFETY_WITHDRAWAL,
            authority="",
        )


def test_new_disposition_stamps_policy_version() -> None:
    rec = _rec(Disposition.ALLOW)
    assert rec.policy_version == POLICY_VERSION == "publication-eligibility/1"
