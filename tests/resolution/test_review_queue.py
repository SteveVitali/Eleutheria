# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The internal review queue and curation contract (§14.6/§25/§27): a human
accepts/rejects tier-4/5 PROPOSED matches with the per-comparison confidence explanation
surfaced inline (SIG-IDENT-025); the queue adjudicates model-assisted extractions and
logs model/prompt with every decision (SIG-IDENT-026); nothing here writes to the graph
and LLM output reaches only the queue (SIG-LLM-002)."""

from __future__ import annotations

import pytest
from parsing.extraction import ExtractedClaim, ModelExtraction, SourceSpan, deterministic_parameters
from resolution.probabilistic import ComparisonContribution, ProbabilisticMatch
from resolution.review_queue import (
    ER_MATCH,
    MODEL_EXTRACTION,
    ReviewDecision,
    ReviewItem,
    ReviewQueue,
    review_item_from_extraction,
    review_item_from_match,
    surface_confidence_explanation,
)

_FIXED = "2026-08-27T00:00:00+00:00"


def _match() -> ProbabilisticMatch:
    return ProbabilisticMatch(
        left="org:100",
        right="org:200",
        match_tier=4,
        tier_label="4",
        match_weight=9.3,
        match_probability=0.9986,
        decomposition=(
            ComparisonContribution("normalized_name", 3, 128.0, "exact"),
            ComparisonContribution("state", 1, 4.0, "equal"),
        ),
        match_evidence={"rule": "splink_probabilistic", "claim_status": "PROPOSED"},
    )


def _extracted_claim() -> ExtractedClaim:
    capture = "Acme PD operates ALPR cameras."
    text = "ALPR cameras"
    start = capture.index(text)
    span = SourceSpan(
        text=text, start=start, end=start + len(text), locator={"byte_range": [start]}
    )
    extraction = ModelExtraction(
        model_id="acme-extract-v2",
        prompt_version="claims-2026-08",
        extraction_type="structured_claim",
        parameters=deterministic_parameters(),
    )
    return ExtractedClaim("acme_pd", "operates", "ALPR", span, extraction)


# --- SIG-IDENT-025: confidence explanation surfaced inline -------------------------


def test_match_item_carries_the_per_comparison_decomposition() -> None:
    item = review_item_from_match(_match())
    assert item.kind == ER_MATCH
    assert item.overall_weight == pytest.approx(9.3)
    names = [factor.name for factor in item.confidence]
    assert names == ["normalized_name", "state"]
    assert item.confidence[0].weight == pytest.approx(128.0)


def test_surface_confidence_explanation_shows_the_decomposition() -> None:
    text = surface_confidence_explanation(review_item_from_match(_match()))
    assert "org:100 ~ org:200" in text
    assert "overall match weight: +9.30" in text
    assert "normalized_name" in text and "exact" in text


def test_reviewer_can_accept_a_proposed_match() -> None:
    queue = ReviewQueue()
    item = review_item_from_match(_match())
    queue.enqueue(item)
    assert [i.item_id for i in queue.pending()] == [item.item_id]
    decision = queue.decide(item.item_id, "accept", reviewer="alice", decided_at=_FIXED)
    assert decision.accepted is True
    assert queue.pending() == ()


def test_reviewer_can_reject_a_proposed_match() -> None:
    queue = ReviewQueue()
    item = review_item_from_match(_match())
    queue.enqueue(item)
    decision = queue.decide(item.item_id, "reject", reviewer="bob", decided_at=_FIXED)
    assert decision.decision == "reject"
    assert decision.accepted is False


# --- SIG-IDENT-026 / SIG-LLM-002: model/prompt logged; only the queue --------------


def test_model_extraction_item_is_model_assisted_and_logs_provenance_on_decision() -> None:
    queue = ReviewQueue()
    item = review_item_from_extraction(_extracted_claim())
    assert item.kind == MODEL_EXTRACTION
    assert item.model_assisted is True
    queue.enqueue(item)
    decision = queue.decide(item.item_id, "accept", reviewer="carol", decided_at=_FIXED)
    # model_id and prompt_version are logged with the human decision (SIG-IDENT-026).
    assert decision.model_id == "acme-extract-v2"
    assert decision.prompt_version == "claims-2026-08"


def test_a_deterministic_er_match_decision_is_not_model_assisted() -> None:
    item = review_item_from_match(_match())
    assert item.model_assisted is False
    queue = ReviewQueue()
    queue.enqueue(item)
    decision = queue.decide(item.item_id, "accept", reviewer="dave", decided_at=_FIXED)
    assert decision.model_id is None
    assert decision.prompt_version is None


def test_a_model_assisted_item_missing_provenance_cannot_be_decided() -> None:
    # An item that claims to be model-assisted but drops its provenance is refused
    # (defensive: the queue never records a model decision without model/prompt).
    broken = ReviewItem(
        item_id="model_extraction:x:0:1",
        kind=MODEL_EXTRACTION,
        summary="broken",
        model_id="m",
        prompt_version=None,
    )
    assert broken.model_assisted is True
    queue = ReviewQueue()
    queue.enqueue(broken)
    with pytest.raises(ValueError, match="SIG-IDENT-026"):
        queue.decide("model_extraction:x:0:1", "accept", reviewer="e", decided_at=_FIXED)


def test_queue_has_no_graph_write_path() -> None:
    # The queue records decisions only; it exposes no method that writes to the graph.
    queue = ReviewQueue()
    public = {name for name in dir(queue) if not name.startswith("_")}
    assert not (public & {"write", "load_graph", "commit", "persist_claim", "to_graph"})
    item = review_item_from_extraction(_extracted_claim())
    queue.enqueue(item)
    decision = queue.decide(item.item_id, "accept", reviewer="f", decided_at=_FIXED)
    # Accepting records a decision; it does not itself produce a graph write.
    assert isinstance(decision, ReviewDecision)
    assert queue.decisions() == (decision,)


# --- queue mechanics: append-only, deterministic, serialisable ---------------------


def test_decisions_are_append_only_an_item_is_not_re_decided() -> None:
    queue = ReviewQueue()
    item = review_item_from_match(_match())
    queue.enqueue(item)
    queue.decide(item.item_id, "accept", reviewer="alice", decided_at=_FIXED)
    with pytest.raises(ValueError, match="already been decided"):
        queue.decide(item.item_id, "reject", reviewer="mallory", decided_at=_FIXED)


def test_deciding_an_unknown_item_raises() -> None:
    with pytest.raises(ValueError, match="no pending review item"):
        ReviewQueue().decide("nope", "accept", reviewer="x", decided_at=_FIXED)


def test_enqueue_rejects_a_duplicate_id() -> None:
    queue = ReviewQueue()
    item = review_item_from_match(_match())
    queue.enqueue(item)
    with pytest.raises(ValueError, match="already in the queue"):
        queue.enqueue(item)


def test_decision_requires_a_reviewer_and_a_known_verb() -> None:
    with pytest.raises(ValueError):
        ReviewDecision(item_id="i", decision="accept", reviewer="", decided_at=_FIXED)
    with pytest.raises(ValueError):
        ReviewDecision(item_id="i", decision="maybe", reviewer="r", decided_at=_FIXED)


def test_queue_round_trips_through_json_dict() -> None:
    queue = ReviewQueue()
    match_item = review_item_from_match(_match())
    extraction_item = review_item_from_extraction(_extracted_claim())
    queue.enqueue(match_item)
    queue.enqueue(extraction_item)
    queue.decide(extraction_item.item_id, "reject", reviewer="alice", decided_at=_FIXED)

    restored = ReviewQueue.from_dict(queue.to_dict())
    assert [i.item_id for i in restored.pending()] == [match_item.item_id]
    assert len(restored.decisions()) == 1
    restored_decision = restored.decisions()[0]
    assert restored_decision.model_id == "acme-extract-v2"
    assert restored.get(extraction_item.item_id) is not None  # decided item retained
    # the surviving pending match still carries its decomposition after a round-trip
    assert restored.pending()[0].confidence[0].name == "normalized_name"
