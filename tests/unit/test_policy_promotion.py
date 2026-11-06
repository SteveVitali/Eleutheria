# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.10 — the §43.5 asset-promotion gate (SIG-PUB-012).

The acceptance shape (ticket catalog R11-DATA-06): **a corroboration-only
candidate is refused**. ``promotion_permitted()`` is the single decision
function and :func:`policy.promotion.promotion_claims` the only
candidate→``PhysicalAsset`` writer — a ``PromotionWrite`` cannot be
fabricated without the gate, and every refusal is named, never a silent drop.

No Docker needed — the composed-spine twin is
``tests/db/test_asset_promotion.py``.
"""

from __future__ import annotations

import pytest
from policy.promotion import (
    PROMOTION_RULE_VERSION,
    CandidateForPromotion,
    Confirmation,
    ConfirmationKind,
    PromotionRefusal,
    PromotionRefused,
    PromotionWrite,
    promotion_claims,
    promotion_permitted,
)


def _candidate(**kw: object) -> CandidateForPromotion:
    base = {
        "subject": "candidate:rf:okc-1",
        "detection_method": "rf_oui_match",
        "observation_count": 4,
        "promotion_status": "corroborated",
    }
    base.update(kw)
    return CandidateForPromotion(**base)


def _field() -> Confirmation:
    return Confirmation(ConfirmationKind.FIELD, "mapper.alice", ("claim:field-obs-1",))


# --- the acceptance shape: corroboration-only is refused ----------------------


def test_a_corroboration_only_candidate_is_refused() -> None:
    # The catalog acceptance shape: corroborated status + nonzero
    # observation_count and no recorded confirmation → refused, never minted.
    candidate = _candidate()
    decision = promotion_permitted(candidate)
    assert not decision.permitted
    assert decision.refusals == (PromotionRefusal.CORROBORATION_ONLY,)
    assert decision.confirmation_status is None
    # A refusal records no status change — the candidate stays corroborated.
    assert decision.resulting_status == "corroborated"
    with pytest.raises(PromotionRefused):
        promotion_claims(candidate, source_id="t", license="CC0-1.0")


def test_no_observation_count_ever_promotes_without_confirmation() -> None:
    candidate = _candidate(observation_count=10_000)
    decision = promotion_permitted(candidate)
    assert not decision.permitted
    assert PromotionRefusal.CORROBORATION_ONLY in decision.refusals


def test_an_unreviewed_candidate_also_needs_confirmation() -> None:
    decision = promotion_permitted(_candidate(promotion_status="unreviewed"))
    assert not decision.permitted
    assert PromotionRefusal.CORROBORATION_ONLY in decision.refusals


def test_detection_method_is_never_a_confirmation() -> None:
    # `imagery_detection` is how the lead was *found* — an automated
    # detection, not a recorded imagery confirmation (SIG-PUB-012).
    decision = promotion_permitted(_candidate(detection_method="imagery_detection"))
    assert not decision.permitted
    assert PromotionRefusal.CORROBORATION_ONLY in decision.refusals


# --- permitted paths ----------------------------------------------------------


def test_field_confirmation_promotes() -> None:
    candidate = _candidate(confirmations=(_field(),))
    decision = promotion_permitted(candidate)
    assert decision.permitted
    assert decision.refusals == ()
    assert decision.confirmation_status == "field_confirmed"
    assert decision.resulting_status == "promoted"

    write = promotion_claims(candidate, source_id="t", license="CC0-1.0")
    assert write.asset_subject == "promoted:candidate:rf:okc-1"
    assert write.confirmation_status == "field_confirmed"
    by_pred = {c["predicate_id"]: c for c in write.claims}
    assert set(by_pred) == {"asset_exists_at_location", "candidate_promotion_status"}
    assert by_pred["asset_exists_at_location"]["subject_id"] == write.asset_subject
    assert by_pred["candidate_promotion_status"]["subject_id"] == candidate.subject
    assert by_pred["candidate_promotion_status"]["value"] == "promoted"
    # The promotion keeps its evidence chain (§3.1).
    assert by_pred["asset_exists_at_location"]["derived_from_claim_ids"] == ["claim:field-obs-1"]
    assert PROMOTION_RULE_VERSION in by_pred["asset_exists_at_location"]["assertion_rationale"]


def test_imagery_and_documentary_confirmations_promote() -> None:
    imagery = Confirmation(ConfirmationKind.IMAGERY, "mapper.bob")
    documentary = Confirmation(ConfirmationKind.DOCUMENTARY, "records:resp:okc-114")
    assert (
        promotion_permitted(_candidate(confirmations=(imagery,))).confirmation_status
        == "imagery_confirmed"
    )
    assert (
        promotion_permitted(_candidate(confirmations=(documentary,))).confirmation_status
        == "record_confirmed"
    )
    # Several kinds → deterministic precedence (field > imagery > documentary).
    assert (
        promotion_permitted(
            _candidate(confirmations=(documentary, _field(), imagery))
        ).confirmation_status
        == "field_confirmed"
    )


def test_a_location_estimate_rides_the_promotion() -> None:
    write = promotion_claims(
        _candidate(
            confirmations=(_field(),),
            location_estimate_wkt="POINT(-97.52 35.46)",
        ),
        source_id="t",
        license="CC0-1.0",
    )
    preds = {c["predicate_id"] for c in write.claims}
    assert "fixed_asset_location" in preds


# --- the remaining refusals ---------------------------------------------------


def test_residential_parcel_refuses_even_with_confirmation() -> None:
    # SIG-PUB-013: barred at every precision, regardless of confirmation.
    candidate = _candidate(confirmations=(_field(),), residential_parcel_flag=True)
    decision = promotion_permitted(candidate)
    assert not decision.permitted
    assert PromotionRefusal.RESIDENTIAL_PARCEL in decision.refusals
    assert decision.resulting_status == "suppressed_by_policy"
    with pytest.raises(PromotionRefused):
        promotion_claims(candidate, source_id="t", license="CC0-1.0")


def test_a_confirmation_without_its_reference_is_refused() -> None:
    # §3.1: a claim carries the evidence behind it — a confirmation with no
    # actor/document reference is unprovenanced, never a weaker permit.
    decision = promotion_permitted(
        _candidate(confirmations=(Confirmation(ConfirmationKind.FIELD, ""),))
    )
    assert not decision.permitted
    assert decision.refusals == (PromotionRefusal.UNPROVENANCED_CONFIRMATION,)


def test_decided_statuses_refuse() -> None:
    for status in ("rejected", "suppressed_by_policy"):
        decision = promotion_permitted(
            _candidate(promotion_status=status, confirmations=(_field(),))
        )
        assert not decision.permitted
        assert PromotionRefusal.DECIDED in decision.refusals


def test_already_promoted_refuses_the_second_write() -> None:
    # Append-only: the promotion record is written once.
    decision = promotion_permitted(
        _candidate(promotion_status="promoted", confirmations=(_field(),))
    )
    assert not decision.permitted
    assert PromotionRefusal.ALREADY_PROMOTED in decision.refusals


def test_unknown_status_fails_closed() -> None:
    decision = promotion_permitted(
        _candidate(promotion_status="confirmed", confirmations=(_field(),))
    )
    assert not decision.permitted
    assert PromotionRefusal.UNKNOWN_STATUS in decision.refusals


def test_missing_subject_fails_closed() -> None:
    decision = promotion_permitted(_candidate(subject="", confirmations=(_field(),)))
    assert not decision.permitted
    assert PromotionRefusal.MISSING_SUBJECT in decision.refusals


# --- the only-writer property ---------------------------------------------------


def test_a_promotion_write_cannot_be_fabricated_without_the_gate() -> None:
    # The private gate token means the frozen PromotionWrite exists only as
    # promotion_claims()' output — no second candidate→PhysicalAsset writer.
    with pytest.raises(TypeError, match="only.*writer"):
        PromotionWrite(
            _gate_token=object(),
            decision=promotion_permitted(_candidate(confirmations=(_field(),))),
            asset_subject="promoted:candidate:x",
            confirmation_status="field_confirmed",
            claims=(),
        )


def test_refusals_accumulate_in_a_stable_order() -> None:
    # A parcel-flagged, already-decided candidate with no confirmation names
    # every refusal — an audit can see all of them at once.
    decision = promotion_permitted(
        _candidate(
            promotion_status="rejected",
            residential_parcel_flag=True,
        )
    )
    assert not decision.permitted
    assert set(decision.refusals) == {
        PromotionRefusal.RESIDENTIAL_PARCEL,
        PromotionRefusal.DECIDED,
        PromotionRefusal.CORROBORATION_ONLY,
    }
    assert decision.resulting_status == "suppressed_by_policy"
