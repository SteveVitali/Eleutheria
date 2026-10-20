# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P32.2 (SIG-TRUST-001/002): the sig.assertion/1 adapter + capture binding.

Pure unit tests — no database. Every default the adapter applies carries a
named basis; every unknown type fails closed into a Rejection; absent fields
never silently strengthen evidence or lower sensitivity.
"""

from __future__ import annotations

from datetime import UTC, datetime

from db.assertion import (
    ASSERTION_MAP_ID,
    BINDING_ACTUAL,
    BINDING_DOCUMENT_ONLY,
    BINDING_LEGACY,
    BINDING_REPLAYED,
    CaptureBinding,
    QuarantineReason,
    Rejection,
    TypedAssertion,
    assertion_from_record,
    binding_of,
    quarantine_payload,
)
from evidence.digest import multihash

_OBS = datetime(2026, 9, 25, tzinfo=UTC)


def _binding(**kw) -> CaptureBinding:
    args = dict(
        digest=multihash(b"capture-bytes"),
        source_uri="https://example/page.html",
        media_type="text/html",
        byte_size=42,
        retrieved_at=_OBS,
        ocfl_object_id="sig:capture:x",
        ocfl_version="v3",
    )
    args.update(kw)
    return CaptureBinding(**args)


def _record(**kw) -> dict:
    rec = {"subject_id": "subj:1", "predicate_id": "sig.test.p"}
    rec.update(kw)
    return rec


# --- binding_of ---------------------------------------------------------------


def test_binding_of_rejects_a_missing_digest() -> None:
    r = binding_of({"source_uri": "https://x", "retrieved_at": _OBS})
    assert isinstance(r, Rejection) and r.reason is QuarantineReason.MISSING_CAPTURE_BINDING


def test_binding_of_rejects_an_undecodable_digest() -> None:
    r = binding_of({"digest": "not-a-multihash", "source_uri": "https://x", "retrieved_at": _OBS})
    assert isinstance(r, Rejection) and r.reason is QuarantineReason.BAD_DIGEST


def test_binding_of_rejects_a_missing_retrieved_at() -> None:
    """evidence_capture.retrieved_at is NOT NULL — the observation time is never
    fabricated (SIG-TRUST-002)."""
    r = binding_of({"digest": multihash(b"x"), "source_uri": "https://x"})
    assert isinstance(r, Rejection) and r.reason is QuarantineReason.MISSING_CAPTURE_BINDING


def test_binding_of_normalizes_a_naive_datetime() -> None:
    b = binding_of(
        {
            "digest": multihash(b"x"),
            "source_uri": "https://x",
            "retrieved_at": datetime(2026, 9, 25),  # naive
            "ocfl_version": "v2",
        }
    )
    assert isinstance(b, CaptureBinding)
    assert b.retrieved_at.tzinfo is not None and b.ocfl_version == "v2"


# --- typed fields preserved ---------------------------------------------------


def test_all_typed_fields_are_preserved() -> None:
    a = assertion_from_record(
        _record(
            value=3.5,
            object_type="quantity",
            unit="m",
            raw_value="3.5 m",
            valid_from="2026-01-01",
            valid_to="2026-12-31",
            source_reliability="R2",
            claim_directness="D3",
            artifact_integrity="I2",
            sensitivity_tier=1,
            claim_polarity="denies",
            rank="preferred",
            review_status="human_verified",
            legacy_source_tier="B",
            assertion_rationale="direct statement",
            unit_kind=None,
        ),
        binding=_binding(),
    )
    assert isinstance(a, TypedAssertion)
    assert a.object_type == "quantity" and a.unit == "m"
    assert a.value_float == repr(3.5) and a.raw_value == "3.5 m"
    assert a.valid_from == "2026-01-01T00:00:00+00:00" and a.valid_to == "2026-12-31T00:00:00+00:00"
    assert (a.source_reliability, a.claim_directness, a.artifact_integrity) == ("R2", "D3", "I2")
    assert a.sensitivity_tier == 1 and a.claim_polarity == "denies"
    assert a.rank == "preferred" and a.review_status == "human_verified"
    assert a.legacy_source_tier == "B" and a.assertion_rationale == "direct statement"


def test_observed_at_defaults_from_the_binding_retrieval_time() -> None:
    """The capture's retrieved_at is the honest basis for observation time —
    recorded as such, never silent (SIG-TRUST-002)."""
    a = assertion_from_record(_record(value="x"), binding=_binding())
    assert isinstance(a, TypedAssertion)
    assert a.observed_at == _OBS.isoformat()
    assert a.defaulted["observed_at"] == "capture_retrieved_at"


def test_an_explicit_observed_at_beats_the_binding() -> None:
    a = assertion_from_record(
        _record(value="x", observed_at="2026-01-05T00:00:00Z"), binding=_binding()
    )
    assert isinstance(a, TypedAssertion)
    assert a.observed_at == "2026-01-05T00:00:00+00:00"
    assert "observed_at" not in a.defaulted


def test_absent_time_stays_unknown_with_a_recorded_basis() -> None:
    a = assertion_from_record(_record(value="x"))
    assert isinstance(a, TypedAssertion)
    assert a.valid_from_kind == "unknown" and a.valid_to_kind == "unknown"
    assert a.observed_at is None and a.observed_unknown_reason is not None
    assert a.defaulted["valid_from_kind"] == "absent_is_unknown"


# --- fail-closed rejections ---------------------------------------------------


def test_missing_subject_or_predicate_rejects() -> None:
    r = assertion_from_record({"predicate_id": "p"}, binding=_binding())
    assert isinstance(r, Rejection) and r.reason is QuarantineReason.MISSING_REQUIRED_FIELD


def test_unknown_object_type_rejects() -> None:
    r = assertion_from_record(_record(object_type="widget"), binding=_binding())
    assert isinstance(r, Rejection) and r.reason is QuarantineReason.UNKNOWN_OBJECT_TYPE


def test_unknown_value_kind_rejects() -> None:
    r = assertion_from_record(_record(value="x", value_kind="kinda"), binding=_binding())
    assert isinstance(r, Rejection) and r.reason is QuarantineReason.UNKNOWN_VALUE_KIND


def test_quantity_without_a_unit_rejects() -> None:
    r = assertion_from_record(_record(value=1, object_type="quantity"), binding=_binding())
    assert isinstance(r, Rejection) and r.reason is QuarantineReason.MISSING_REQUIRED_FIELD


def test_unsupported_locator_kind_rejects() -> None:
    r = assertion_from_record(
        _record(value="x", locator={"kind": "warp_drive", "n": 1}), binding=_binding()
    )
    assert isinstance(r, Rejection) and r.reason is QuarantineReason.UNSUPPORTED_LOCATOR


def test_llm_assisted_without_model_identity_rejects() -> None:
    """The extraction CHECK needs model+prompt for llm_assisted; a model identity
    is never fabricated."""
    r = assertion_from_record(
        _record(value="x", extraction_method="llm_assisted"), binding=_binding()
    )
    assert isinstance(r, Rejection) and r.reason is QuarantineReason.MISSING_REQUIRED_FIELD


def test_a_revises_claim_without_reason_rejects_at_db_not_silently() -> None:
    """correction_reason stays whatever the record carried — the DB CHECK is the
    gate; the adapter preserves rather than fabricates one."""
    a = assertion_from_record(
        _record(value="x", revises_claim="00000000-0000-7000-8000-000000000001"),
        binding=_binding(),
    )
    assert isinstance(a, TypedAssertion) and a.correction_reason is None


# --- binding status / locators ------------------------------------------------


def test_a_typed_locator_marks_actual_capture() -> None:
    a = assertion_from_record(
        _record(value="x", locator={"kind": "page", "page": 3}), binding=_binding()
    )
    assert isinstance(a, TypedAssertion)
    assert a.binding_status == BINDING_ACTUAL and a.locator_row is not None


def test_no_locator_is_the_honest_document_only_limitation() -> None:
    a = assertion_from_record(_record(value="x"), binding=_binding())
    assert isinstance(a, TypedAssertion)
    assert a.binding_status == BINDING_DOCUMENT_ONLY
    assert a.locator_row == {"kind": "byte_range", "start": 0, "end": 42}


def test_no_binding_is_honestly_legacy() -> None:
    a = assertion_from_record(_record(value="x"))
    assert isinstance(a, TypedAssertion)
    assert a.binding_status == BINDING_LEGACY and a.locator_row is None


def test_a_replayed_binding_marks_replayed() -> None:
    a = assertion_from_record(_record(value="x"), binding=_binding(replayed=True), replayed=True)
    assert isinstance(a, TypedAssertion) and a.binding_status == BINDING_REPLAYED


# --- qualifiers ---------------------------------------------------------------


def test_qualifiers_preserve_typed_values() -> None:
    a = assertion_from_record(
        _record(
            value="x",
            qualifiers=[
                {"qualifier_id": "qual.money.amount", "value": 1200.0, "unit": "USD"},
                {"qualifier_id": "qual.applicability.jurisdiction", "value": "US-OK"},
                {
                    "qualifier_id": "qual.instrument.effective_date",
                    "value": "x",
                    "valid_from": "2026-01-01",
                    "valid_to": "2026-06-30",
                },
            ],
        ),
        binding=_binding(),
    )
    assert isinstance(a, TypedAssertion)
    assert [q.qualifier_id for q in a.qualifiers] == [
        "qual.money.amount",
        "qual.applicability.jurisdiction",
        "qual.instrument.effective_date",
    ]
    assert a.qualifiers[0].value_num == "1200.0" and a.qualifiers[0].unit == "USD"
    assert a.qualifiers[2].valid_from is not None and a.qualifiers[2].valid_to is not None


def test_a_qualifier_without_an_id_rejects() -> None:
    r = assertion_from_record(_record(value="x", qualifiers=[{"value": 1}]), binding=_binding())
    assert isinstance(r, Rejection) and r.reason is QuarantineReason.UNKNOWN_QUALIFIER


# --- map id / basis -----------------------------------------------------------


def test_the_named_versioned_map_and_basis() -> None:
    a = assertion_from_record(_record(value="x"), binding=_binding())
    assert isinstance(a, TypedAssertion)
    assert ASSERTION_MAP_ID == "sig.assertion.map.v1"
    basis = a.map_basis()
    assert "object_type" not in basis or "object_type=inferred_from_value_shape" in basis
    assert "observed_at=capture_retrieved_at" in basis


def test_the_legacy_map_basis_labels_itself() -> None:
    a = assertion_from_record(_record(value="x"))
    assert isinstance(a, TypedAssertion)
    assert a.map_basis(synthetic=True) == "legacy_synthetic"


# --- quarantine payload --------------------------------------------------------


def test_quarantine_payload_is_content_keyed() -> None:
    p = quarantine_payload(_record(value="x"), connector_name="atlas", source_id="src")
    assert p["schema"] == "sig.assertion/1" and p["connector_name"] == "atlas"
    assert p["record"]["subject_id"] == "subj:1"


# --- P35.18 (JUR-02a / K4 §3.2): candidate_identifier -> value_json -----------


def test_candidate_identifier_persists_as_scheme_value_in_value_json() -> None:
    """A record's ``candidate_identifier`` lands in ``value_json`` as the
    ``{scheme, value}`` pair — the declared scheme survives to the spine."""
    import json

    a = assertion_from_record(
        _record(
            value="OK",
            candidate_identifier={"scheme": "us.state_abbr", "value": "OK"},
        ),
        binding=_binding(),
    )
    assert isinstance(a, TypedAssertion)
    assert json.loads(a.value_json) == {"scheme": "us.state_abbr", "value": "OK"}


def test_candidate_identifier_leaves_the_text_value_and_digest_inputs_alone() -> None:
    """The claim's text value is byte-identical and the digest is over the
    RECORD (never the derived jsonb) — persisting the pair changes neither."""
    import json

    from db.claim_sink import content_digest

    rec = _record(
        value="US-DE",
        candidate_identifier={"scheme": "iso.3166_2", "value": "US-DE"},
    )
    digest_before = content_digest(rec)
    a = assertion_from_record(rec, binding=_binding())
    assert isinstance(a, TypedAssertion)
    assert a.value_text == "US-DE" and a.raw_value == "US-DE"
    assert "value_json" not in rec  # the adapter never mutates the record
    assert content_digest(rec) == digest_before
    assert json.loads(a.value_json)["scheme"] == "iso.3166_2"


def test_candidate_identifier_merges_into_existing_value_json() -> None:
    """An existing ``value_json`` object keeps its fields; the pair is additive."""
    import json

    a = assertion_from_record(
        _record(
            value="x",
            value_json={"note": "kept"},
            candidate_identifier={"scheme": "openstates.jurisdiction", "value": "ocd"},
        ),
        binding=_binding(),
    )
    assert isinstance(a, TypedAssertion)
    doc = json.loads(a.value_json)
    assert doc == {
        "note": "kept",
        "scheme": "openstates.jurisdiction",
        "value": "ocd",
    }


def test_candidate_identifier_conflict_with_value_json_rejects() -> None:
    """A record whose ``value_json`` already declares a *different* pair fails
    closed — an ambiguous identifier never lands on the spine."""
    r = assertion_from_record(
        _record(
            value="x",
            value_json={"scheme": "us.state_abbr", "value": "OK"},
            candidate_identifier={"scheme": "iso.3166_2", "value": "US-OK"},
        ),
        binding=_binding(),
    )
    assert isinstance(r, Rejection)
    assert r.reason is QuarantineReason.MISSING_REQUIRED_FIELD


def test_candidate_identifier_non_mapping_value_json_rejects() -> None:
    r = assertion_from_record(
        _record(
            value="x",
            value_json="not-an-object",
            candidate_identifier={"scheme": "us.state_abbr", "value": "OK"},
        ),
        binding=_binding(),
    )
    assert isinstance(r, Rejection)
    assert r.reason is QuarantineReason.MISSING_REQUIRED_FIELD


def test_a_malformed_candidate_identifier_rejects() -> None:
    """Missing scheme/value keys fail closed (fail-closed, quarantine upstream)."""
    for bad in (
        "us.state_abbr:OK",  # a string, not a pair
        {"scheme": "us.state_abbr"},  # no value
        {"value": "OK"},  # no scheme
        {"scheme": "", "value": "OK"},  # empty scheme
        {"scheme": "us.state_abbr", "value": ""},  # empty value
    ):
        r = assertion_from_record(_record(value="x", candidate_identifier=bad), binding=_binding())
        assert isinstance(r, Rejection), bad
        assert r.reason is QuarantineReason.MISSING_REQUIRED_FIELD


def test_no_candidate_identifier_keeps_value_json_unchanged() -> None:
    """Back-compat: a record with no candidate_identifier shapes exactly as
    before — including an absent ``value_json`` staying ``None``."""
    a = assertion_from_record(_record(value="x"), binding=_binding())
    assert isinstance(a, TypedAssertion)
    assert a.value_json is None
    b = assertion_from_record(_record(value="x", value_json={"only": "this"}), binding=_binding())
    assert isinstance(b, TypedAssertion)
    import json

    assert json.loads(b.value_json) == {"only": "this"}
