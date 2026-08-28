# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The model-assisted-extraction boundary (§25, SIG-LLM-001–007, SIG-PARSE-003):
every extraction records model/prompt/params and is schema-validated; every extracted
claim carries a source span that must appear in the capture or it is rejected; every
extracted claim is R6/`PROPOSED` and never writes to the graph; the pipeline queues
rather than fails when the model is unavailable; and a per-type sampling rate demotes to
human-only on a gold-accuracy breach."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from parsing.extraction import (
    PROPOSED,
    R6,
    ExtractedClaim,
    ExtractionOutcome,
    ExtractionRejected,
    ModelExtraction,
    SourceSpan,
    deterministic_parameters,
    evaluate_demotion,
    extract_claims,
    load_policies,
    measure_accuracy,
    run_extraction,
    should_sample_for_review,
    validate_output,
    validate_span,
)

_CAPTURE = "Acme Police Department operates 12 ALPR cameras on Main Street."


def _span_for(text: str, capture: str = _CAPTURE) -> SourceSpan:
    start = capture.index(text)
    return SourceSpan(
        text=text, start=start, end=start + len(text), locator={"byte_range": [start]}
    )


def _extraction(extraction_type: str = "structured_claim") -> ModelExtraction:
    return ModelExtraction(
        model_id="acme-extract-v2",
        prompt_version="claims-2026-08",
        extraction_type=extraction_type,
        parameters=deterministic_parameters(),
    )


def _raw_item(value: str = "ALPR", text: str = "ALPR cameras") -> dict[str, Any]:
    span = _span_for(text)
    return {
        "subject": "acme_pd",
        "predicate": "operates",
        "value": value,
        "span": {"text": span.text, "start": span.start, "end": span.end, "locator": span.locator},
    }


# --- SIG-LLM-003: provenance + schema validation ----------------------------------


def test_extraction_records_model_prompt_and_deterministic_parameters() -> None:
    extraction = _extraction()
    assert extraction.model_id == "acme-extract-v2"
    assert extraction.prompt_version == "claims-2026-08"
    # The deterministic decoding parameters actually used are recorded (SIG-LLM-003).
    assert extraction.parameters["temperature"] == 0.0
    assert "seed" in extraction.parameters
    assert extraction.to_row()["parameters"] == dict(extraction.parameters)


@pytest.mark.parametrize("missing", ["model_id", "prompt_version", "extraction_type"])
def test_extraction_without_its_provenance_is_rejected(missing: str) -> None:
    kwargs = {
        "model_id": "m",
        "prompt_version": "p",
        "extraction_type": "structured_claim",
        "parameters": {"temperature": 0.0},
    }
    kwargs[missing] = ""
    with pytest.raises(ExtractionRejected):
        ModelExtraction(**kwargs)  # type: ignore[arg-type]


def test_extraction_without_parameters_is_rejected() -> None:
    with pytest.raises(ExtractionRejected):
        ModelExtraction(model_id="m", prompt_version="p", extraction_type="t", parameters={})


def test_schema_validation_rejects_a_missing_claim_field() -> None:
    item = _raw_item()
    del item["value"]
    with pytest.raises(ExtractionRejected, match="value"):
        validate_output([item])


def test_schema_validation_rejects_a_span_missing_its_locator() -> None:
    item = _raw_item()
    del item["span"]["locator"]
    with pytest.raises(ExtractionRejected, match="locator"):
        validate_output([item])


def test_schema_validation_accepts_a_well_formed_item() -> None:
    validate_output([_raw_item()])  # does not raise


# --- SIG-LLM-004 / SIG-PARSE-003: the source-span guardrail ------------------------


def test_span_present_in_the_capture_is_accepted() -> None:
    validate_span(_span_for("ALPR cameras"), _CAPTURE)  # does not raise


def test_span_text_not_in_the_capture_is_rejected() -> None:
    hallucination = SourceSpan(text="facial recognition", start=0, end=18, locator={"p": 1})
    with pytest.raises(ExtractionRejected, match="not present in the capture|does not match"):
        validate_span(hallucination, _CAPTURE)


def test_span_offsets_beyond_the_capture_are_rejected() -> None:
    with pytest.raises(ExtractionRejected):
        validate_span(SourceSpan(text="x", start=999, end=1000, locator={"p": 1}), _CAPTURE)


def test_span_without_text_or_locator_is_rejected() -> None:
    with pytest.raises(ExtractionRejected):
        SourceSpan(text="", start=0, end=0, locator={"p": 1})
    with pytest.raises(ExtractionRejected):
        SourceSpan(text="ALPR", start=0, end=4, locator={})


def test_extract_rejects_the_whole_batch_when_one_span_is_unlocatable() -> None:
    good = _raw_item()
    bad = _raw_item(value="face", text="ALPR cameras")
    bad["span"]["text"] = "facial recognition"  # not in the capture
    with pytest.raises(ExtractionRejected):
        extract_claims([good, bad], capture_text=_CAPTURE, extraction=_extraction())


# --- SIG-LLM-005: R6 + PROPOSED, never to the graph --------------------------------


def test_extracted_claim_is_r6_and_proposed_and_never_writes_to_graph() -> None:
    claims = extract_claims([_raw_item()], capture_text=_CAPTURE, extraction=_extraction())
    assert len(claims) == 1
    claim = claims[0]
    assert claim.source_reliability == R6 == "R6"
    assert claim.claim_status == PROPOSED == "PROPOSED"
    assert claim.writes_to_graph is False
    assert claim.to_row()["source_reliability"] == "R6"


@pytest.mark.parametrize(
    "field,value",
    [("source_reliability", "R1"), ("claim_status", "accepted")],
)
def test_a_claim_at_a_lowered_standard_cannot_be_constructed(field: str, value: str) -> None:
    span = _span_for("ALPR cameras")
    kwargs: dict[str, Any] = {
        "subject": "s",
        "predicate": "p",
        "value": "v",
        "span": span,
        "extraction": _extraction(),
    }
    kwargs[field] = value
    with pytest.raises(ExtractionRejected):
        ExtractedClaim(**kwargs)


# --- SIG-LLM-007: graceful degradation ---------------------------------------------


class _FakeModel:
    def __init__(self, available: bool, items: Sequence[Mapping[str, Any]]) -> None:
        self._available = available
        self._items = items

    @property
    def available(self) -> bool:
        return self._available

    def extract(self, capture_text: str, *, extraction_type: str) -> Sequence[Mapping[str, Any]]:
        if not self._available:
            raise AssertionError("extract must not be called when the model is unavailable")
        return self._items


def test_unavailable_model_queues_the_work_and_emits_no_claim() -> None:
    outcome = run_extraction(_FakeModel(False, []), _CAPTURE, extraction=_extraction())
    assert isinstance(outcome, ExtractionOutcome)
    assert outcome.queued is True
    assert outcome.degraded is True
    assert outcome.claims == ()  # no lowered-standard claim emitted to compensate
    assert outcome.reason == "model_unavailable"


def test_available_model_returns_proposed_claims() -> None:
    outcome = run_extraction(_FakeModel(True, [_raw_item()]), _CAPTURE, extraction=_extraction())
    assert outcome.queued is False
    assert len(outcome.claims) == 1
    assert outcome.claims[0].claim_status == PROPOSED


def test_available_model_with_a_hallucinated_span_still_rejects() -> None:
    bad = _raw_item()
    bad["span"]["text"] = "facial recognition"
    with pytest.raises(ExtractionRejected):
        run_extraction(_FakeModel(True, [bad]), _CAPTURE, extraction=_extraction())


# --- SIG-LLM-006: per-type sampling + gold-accuracy demotion -----------------------


def test_policies_are_loaded_per_extraction_type() -> None:
    policies = load_policies()
    assert "org_alias" in policies
    assert 0.0 <= policies["org_alias"].review_sample_rate <= 1.0


def test_accuracy_below_the_floor_demotes_to_human_only() -> None:
    policy = load_policies()["org_alias"]
    assert policy.human_only is False
    demoted = evaluate_demotion(policy, policy.accuracy_threshold - 0.1)
    assert demoted.human_only is True
    assert demoted.effective_sample_rate == 1.0  # everything routed to a human


def test_accuracy_at_or_above_the_floor_does_not_demote() -> None:
    policy = load_policies()["org_alias"]
    kept = evaluate_demotion(policy, policy.accuracy_threshold)
    assert kept.human_only is False


def test_a_passing_measurement_does_not_repromote_a_demoted_type() -> None:
    policy = load_policies()["org_alias"]
    demoted = evaluate_demotion(policy, 0.0)
    still_demoted = evaluate_demotion(demoted, 1.0)
    assert still_demoted.human_only is True


def test_measure_accuracy_counts_matches_against_gold() -> None:
    assert measure_accuracy([True, True, False], [True, False, False]) == pytest.approx(2 / 3)
    with pytest.raises(ValueError):
        measure_accuracy([True], [True, False])
    with pytest.raises(ValueError):
        measure_accuracy([], [])


def test_sampling_is_deterministic_and_total_when_demoted() -> None:
    policy = load_policies()["structured_claim"]
    claim = extract_claims([_raw_item()], capture_text=_CAPTURE, extraction=_extraction())[0]
    first = should_sample_for_review(policy, claim)
    assert should_sample_for_review(policy, claim) is first  # reproducible
    assert should_sample_for_review(evaluate_demotion(policy, 0.0), claim) is True
