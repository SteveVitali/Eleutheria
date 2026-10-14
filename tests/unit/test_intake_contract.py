# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `intake-receiver/1` data contract (P32.16 / ADR-135, SIG-FIND-006).

Deterministic acceptance for the pure half of the receiver: the field
allowlist + bounds, the Part VIII pre-persistence screen, the event vocabulary
and fail-closed transitions, the coarse public projection, and the moderation
detail contract. Every behavior here is a refusal-safe rule — a test that
regresses it must go red.
"""

from __future__ import annotations

import pytest

from policy import intake as pint

VALID = {
    "category": "factual_error",
    "description": "The retention-days value on this record is wrong.",
    "idempotency_key": "abc123def456ghi7",
}


def test_fields_allowlist_is_exact() -> None:
    assert pint.allowed_fields() == {
        "form_token",
        "idempotency_key",
        "category",
        "publication_id",
        "record_key",
        "claim_ids",
        "description",
        "evidence_urls",
        "contact_for_legal_demand",
    }


def test_normalize_accepts_minimal_valid() -> None:
    report = pint.normalize_report(dict(VALID))
    assert report.category == "factual_error"
    assert report.publication_id is None
    assert report.claim_ids == ()


def test_unknown_field_rejected() -> None:
    with pytest.raises(pint.IntakeFieldError) as exc:
        pint.normalize_report({**VALID, "email": "x@y.z", "hp": "bot-bait"})
    assert exc.value.fields["email"] == "unknown field"
    assert exc.value.fields["hp"] == "unknown field"


def test_category_required_and_known() -> None:
    with pytest.raises(pint.IntakeFieldError) as exc:
        pint.normalize_report({k: v for k, v in VALID.items() if k != "category"})
    assert "category" in exc.value.fields
    with pytest.raises(pint.IntakeFieldError) as exc2:
        pint.normalize_report({**VALID, "category": "vibes"})
    assert exc2.value.fields["category"] == "unknown category"
    assert pint.category_response_window_hours("factual_error") == 336
    assert pint.category_response_window_hours("privacy_harm") == 72


def test_description_bounds() -> None:
    with pytest.raises(pint.IntakeFieldError):
        pint.normalize_report({**VALID, "description": "too short"})
    with pytest.raises(pint.IntakeFieldError):
        pint.normalize_report({**VALID, "description": "x" * 4001})
    ok = pint.normalize_report({**VALID, "description": "x" * 4000})
    assert len(ok.description) == 4000


def test_publication_id_and_record_key_shapes() -> None:
    with pytest.raises(pint.IntakeFieldError):
        pint.normalize_report({**VALID, "publication_id": "p-nothex"})
    with pytest.raises(pint.IntakeFieldError):
        pint.normalize_report({**VALID, "publication_id": "p-" + "a" * 63})
    ok = pint.normalize_report({**VALID, "publication_id": "p-" + "a" * 64})
    assert ok.publication_id == "p-" + "a" * 64
    with pytest.raises(pint.IntakeFieldError):
        pint.normalize_report({**VALID, "record_key": "free prose about cameras"})
    ok2 = pint.normalize_report({**VALID, "record_key": "portal:entity:org-oklahoma"})
    assert ok2.record_key == "portal:entity:org-oklahoma"


def test_claim_ids_bounded() -> None:
    with pytest.raises(pint.IntakeFieldError):
        pint.normalize_report({**VALID, "claim_ids": [f"{i:032x}" for i in range(11)]})
    ok = pint.normalize_report({**VALID, "claim_ids": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"})
    assert ok.claim_ids == ("a1b2c3d4-e5f6-7890-abcd-ef1234567890",)


def test_evidence_url_rules() -> None:
    # https required
    for bad in (
        "http://example.com/x",
        "ftp://example.com/x",
        "example.com/x",
        "https://user:pass@example.com/x",
        "https://localhost/x",
        "https://127.0.0.1/x",
        "https://10.0.0.4/x",
        "https://[fd00::1]/x",
        "https://169.254.1.1/x",
        "x" * 2100,
    ):
        with pytest.raises(pint.IntakeFieldError):
            pint.normalize_report({**VALID, "evidence_urls": [bad]})
    with pytest.raises(pint.IntakeFieldError):
        pint.normalize_report(
            {**VALID, "evidence_urls": [f"https://e{i}.example.com/x" for i in range(4)]}
        )
    ok = pint.normalize_report(
        {**VALID, "evidence_urls": ["https://example.com/doc.pdf", "https://oklahoma.gov/x"]}
    )
    assert len(ok.evidence_urls) == 2


def test_contact_only_for_legal_demand() -> None:
    with pytest.raises(pint.IntakeFieldError) as exc:
        pint.normalize_report({**VALID, "contact_for_legal_demand": "counsel office"})
    assert "contact_for_legal_demand" in exc.value.fields
    ok = pint.normalize_report(
        {
            **VALID,
            "category": "legal_demand",
            "contact_for_legal_demand": "clerk reference 44-A",
        }
    )
    assert ok.contact_for_legal_demand == "clerk reference 44-A"


def test_idempotency_key_shape() -> None:
    with pytest.raises(pint.IntakeFieldError):
        pint.normalize_report({**VALID, "idempotency_key": "short"})
    with pytest.raises(pint.IntakeFieldError):
        pint.normalize_report({**VALID, "idempotency_key": "bad chars !!xx"})
    ok = pint.normalize_report({**VALID, "idempotency_key": "nonce-" + "x" * 40})
    assert ok.idempotency_key.startswith("nonce-")


def test_part_viii_refusal_fixtures_never_normalize() -> None:
    """Plate/person-shaped payloads are refused BEFORE any persistence path."""
    fixtures = {
        "plate_token": "The camera read the license plate AB-1234.",
        "per_trip": "this shows per-trip travel history of the mayor",
        "hotlist": "a hotlist hit on the vehicle",
        "email": "reach me at jane.doe@example.com",
        "phone": "call 405-555-1212 for the owner",
        "ssn": "their ssn is 123-45-6789",
        "plate_shape": "plate ABC 1234 was seen",
    }
    for _name, description in fixtures.items():
        with pytest.raises(pint.IntakeFieldError):
            pint.normalize_report(
                {**VALID, "description": description},
            )
        # The refusal reason names the rule + remedy, never the content.
    try:
        pint.normalize_report({**VALID, "description": fixtures["plate_token"]})
    except pint.IntakeFieldError as exc:
        assert "license plate" not in str(exc.fields["description"])
        assert "Part VIII" in exc.fields["description"]


def test_screen_on_url_and_record_fields() -> None:
    with pytest.raises(pint.IntakeFieldError):
        pint.normalize_report(
            {**VALID, "evidence_urls": ["https://example.com/license-plate-search"]}
        )
    with pytest.raises(pint.IntakeFieldError):
        pint.normalize_report({**VALID, "record_key": "x:y:license-plate"})


def test_legal_contact_person_shaped_exempt_but_tokens_still_refused() -> None:
    # An email-shaped legal contact is legitimate — the person-shaped screen
    # does not apply — but a Part VIII token still refuses it.
    ok = pint.normalize_report(
        {
            **VALID,
            "category": "legal_demand",
            "contact_for_legal_demand": "clerk@court.example",
        }
    )
    assert ok.contact_for_legal_demand == "clerk@court.example"
    with pytest.raises(pint.IntakeFieldError):
        pint.normalize_report(
            {
                **VALID,
                "category": "legal_demand",
                "contact_for_legal_demand": "the license plate office",
            }
        )


def test_event_vocabulary_and_writer_sets() -> None:
    vocab = pint.event_vocabulary()
    assert set(vocab["lifecycle"]) == {
        "received",
        "triaged",
        "assigned",
        "review_requested",
        "disposition_proposed",
        "disposition_approved",
        "applied",
        "published",
        "closed",
    }
    assert set(vocab["housekeeping"]) == {"redacted", "expunged"}
    assert "applied" not in pint.moderation_events()
    assert "published" not in pint.moderation_events()
    assert "received" not in pint.moderation_events()
    assert "redacted" in pint.moderation_events()


def test_transition_table_fail_closed() -> None:
    assert pint.legal_transition("received", "triaged")
    assert pint.legal_transition("received", "disposition_proposed")
    assert not pint.legal_transition("received", "disposition_approved")
    assert not pint.legal_transition("received", "closed")
    assert pint.legal_transition("triaged", "assigned")
    assert pint.legal_transition("disposition_proposed", "disposition_approved")
    assert pint.legal_transition("disposition_approved", "closed")
    assert not pint.legal_transition("closed", "triaged")
    assert not pint.legal_transition("closed", "disposition_proposed")
    # Housekeeping never blocked, never moves the lifecycle.
    assert pint.legal_transition("closed", "redacted") is True
    # None means only `received` exists.
    assert pint.legal_transition(None, "triaged")


def test_public_state_coarse_projection() -> None:
    assert pint.public_state("received") == "received"
    assert pint.public_state("triaged") == "under_review"
    assert pint.public_state("assigned") == "under_review"
    assert pint.public_state("review_requested") == "under_review"
    assert pint.public_state("disposition_proposed") == "under_review"
    assert pint.public_state("disposition_approved") == "decided"
    assert pint.public_state("applied") == "decided"
    assert pint.public_state("published") == "resolved"
    assert pint.public_state("closed") == "closed"
    assert pint.public_state(None) == "received"


def test_moderation_detail_contract() -> None:
    # A proposal needs outcome + reason.
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_moderation_detail("disposition_proposed", {})
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_moderation_detail(
            "disposition_proposed", {"outcome": "correct", "reason": ""}
        )
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_moderation_detail(
            "disposition_proposed", {"outcome": "nonsense", "reason": "r"}
        )
    ok = pint.validate_moderation_detail(
        "disposition_proposed",
        {"outcome": "refuse", "reason": "duplicate of an earlier report"},
    )
    assert ok["outcome"] == "refuse"
    # Public response requires the explicit publish flag AND the text.
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_moderation_detail(
            "disposition_proposed",
            {"outcome": "correct", "reason": "r", "public_response_publish": True},
        )
    ok2 = pint.validate_moderation_detail(
        "disposition_approved",
        {
            "outcome": "correct",
            "reason": "verified against the cited PDF",
            "public_response": "Corrected per the cited contract.",
            "public_response_publish": True,
            "approves_seq": 7,
        },
    )
    assert ok2["public_response_publish"] is True
    # Approval without the proposal seq fails.
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_moderation_detail(
            "disposition_approved", {"outcome": "correct", "reason": "r"}
        )
    # Unknown detail keys are refused.
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_moderation_detail("triaged", {"note": "ok", "pwn": "no"})
    # Redaction requires a valid field subset.
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_moderation_detail("redacted", {"fields": ["description", "ip"]})
    ok3 = pint.validate_moderation_detail("redacted", {"fields": ["contact"]})
    assert ok3["fields"] == ["contact"]
    # Assigned needs a handle slug.
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_moderation_detail("assigned", {})
    assert pint.validate_moderation_detail("assigned", {"assignee": "rev-7"})["assignee"] == "rev-7"


# --------------------------------------------------------------------------- #
# The P32.16a proposal + publication-linkage contract (SIG-FIND-008)
# --------------------------------------------------------------------------- #
_CLAIM = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


def _correct_proposal() -> dict:
    return {
        "target_kind": "claim",
        "target_id": _CLAIM,
        "claim_digest": "a" * 64,
        "evidence_digest": "b" * 64,
        # P34.37 (C4 NEW-18): the declared object_type binds the value shape —
        # {value_text, value_num, unit} is exactly what 'quantity' admits.
        "object_type": "quantity",
        "value": {"value_text": "225", "value_num": 225, "unit": "cameras"},
    }


def test_proposal_required_per_outcome() -> None:
    # refuse carries NO proposal — denial never mutates the graph.
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_moderation_detail(
            "disposition_proposed",
            {"outcome": "refuse", "reason": "dup", "proposal": {}},
        )
    # An applying outcome REQUIRES the proposal.
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_moderation_detail(
            "disposition_proposed", {"outcome": "correct", "reason": "r"}
        )
    # And the sanitized proposal round-trips on the detail.
    ok = pint.validate_moderation_detail(
        "disposition_proposed",
        {
            "outcome": "correct",
            "reason": "verified",
            "proposal": _correct_proposal(),
        },
    )
    assert ok["proposal"]["target_id"] == _CLAIM


def test_proposal_unknown_and_missing_keys() -> None:
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_proposal("correct", {**_correct_proposal(), "pwn": "x"})
    missing = {k: v for k, v in _correct_proposal().items() if k != "claim_digest"}
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_proposal("correct", missing)


def test_proposal_fingerprint_and_target_shapes() -> None:
    bad = _correct_proposal()
    bad["claim_digest"] = "not-a-digest"
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_proposal("correct", bad)
    bad2 = _correct_proposal()
    bad2["target_id"] = "free prose"
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_proposal("correct", bad2)
    # A release_artifact target is the p-<64 hex> ADR-132 namespace only.
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_proposal(
            "suppress",
            {
                "target_kind": "release_artifact",
                "target_id": "abc123",
                "reason_category": "suppressed",
            },
        )
    ok = pint.validate_proposal(
        "suppress",
        {
            "target_kind": "release_artifact",
            "target_id": "p-" + "c" * 64,
            "reason_category": "rights_withdrawal",
        },
    )
    assert ok["disposition"] == "withhold"  # the safe default


def test_proposal_part_viii_screen() -> None:
    bad = _correct_proposal()
    # Shape-valid for 'quantity' so the refusal is the Part VIII screen, not
    # the NEW-18 shape check.
    bad["value"] = {"value_text": "the license plate ABC-123", "value_num": 225}
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_proposal("correct", bad)
    bad2 = _correct_proposal()
    bad2["correction_reason"] = "per-trip travel history"
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_proposal("correct", bad2)


def test_proposal_value_shape_bound_to_object_type() -> None:
    """C4 NEW-18: a proposal that would be unapplicable at the bridge is
    refused AT PROPOSAL TIME — the declared object_type pins
    required ⊆ present ⊆ required ∪ optional over [proposal.object_value],
    the same table the bridge re-checks at apply."""
    # A required column missing for the declared type.
    missing_col = _correct_proposal()
    del missing_col["value"]["value_num"]
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_proposal("correct", missing_col)
    # A column the declared type does not admit.
    extra_col = _correct_proposal()
    extra_col["value"]["object_entity"] = _CLAIM
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_proposal("correct", extra_col)
    # An out-of-scope type fails closed (geometry is never bridgeable).
    unknown_type = _correct_proposal()
    unknown_type["object_type"] = "geometry"
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_proposal("correct", unknown_type)
    # object_type is required when a value is proposed.
    missing_type = {k: v for k, v in _correct_proposal().items() if k != "object_type"}
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_proposal("correct", missing_type)
    # A correctly-shaped proposal for its declared type still passes.
    literal = _correct_proposal()
    literal["object_type"] = "literal"
    literal["value"] = {"value_text": "updated description"}
    assert pint.validate_proposal("correct", literal)["object_type"] == "literal"
    # One table of record feeds the bridge's apply-side check — no drift.
    rules = pint.object_value_rules()
    assert rules["literal"] == (frozenset({"value_text"}), frozenset({"unit"}))
    assert "value_geom" not in rules and "geometry" not in rules


def test_proposal_outcome_shapes() -> None:
    # correct/annotate target claims only; annotate requires its predicate.
    bad = _correct_proposal()
    bad["target_kind"] = "entity"
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_proposal("correct", bad)
    anno = _correct_proposal()
    anno["predicate_id"] = "camera_count"
    assert pint.validate_proposal("annotate", anno)["predicate_id"] == "camera_count"
    missing_pred = {k: v for k, v in anno.items() if k != "predicate_id"}
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_proposal("annotate", missing_pred)
    # delete always lands withdraw — a narrower disposition is refused.
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_proposal(
            "delete",
            {
                "target_kind": "claim",
                "target_id": _CLAIM,
                "reason_category": "safety_withdrawal",
                "disposition": "withhold",
            },
        )
    ok = pint.validate_proposal(
        "delete",
        {
            "target_kind": "claim",
            "target_id": _CLAIM,
            "reason_category": "safety_withdrawal",
        },
    )
    assert ok["disposition"] == "withdraw"
    # An unknown reason_category is refused.
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_proposal(
            "suppress",
            {"target_kind": "claim", "target_id": _CLAIM, "reason_category": "meh"},
        )


def test_publish_linkage_contract() -> None:
    # At least one of the three linkage forms is required.
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_publish_linkage()
    # The release identity is the ADR-132 namespace, nothing else.
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_publish_linkage(publication_id="release-1")
    ok = pint.validate_publish_linkage(
        publication_id="p-" + "d" * 64, correction_ref="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
    )
    assert ok["publication_id"].startswith("p-") and "correction_ref" in ok
    # A tombstone is screened like every piece of review-authored text.
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_publish_linkage(tombstone="per-person lookup")
    ok2 = pint.validate_publish_linkage(tombstone="withheld pending legal review")
    assert ok2["tombstone"] == "withheld pending legal review"


def test_bridge_transition_paths() -> None:
    # applied/published are bridge-only stages in the lifecycle.
    assert pint.legal_transition("disposition_approved", "applied")
    assert pint.legal_transition("applied", "published")
    assert pint.legal_transition("applied", "closed")
    assert pint.legal_transition("published", "closed")
    # A superseded approval is recoverable: approved → re-proposed → re-approved.
    assert pint.legal_transition("disposition_approved", "disposition_proposed")
    # But the path never skips the approval gate.
    assert not pint.legal_transition("received", "applied")
    assert not pint.legal_transition("triaged", "applied")
    assert not pint.legal_transition("disposition_proposed", "applied")
    assert not pint.legal_transition("published", "applied")
