# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The layered extraction strategy (§24.1, SIG-PARSE-001): seven layers ordered cheapest
to most expensive, the method string recorded on the extraction, and the cheapest-
sufficient selection over a candidate set."""

from __future__ import annotations

import pytest
from parsing.layers import (
    LAYER_ORDER,
    LLM_LAYER,
    ExtractionLayer,
    cheaper_of,
    cheapest_sufficient,
)


def test_layers_are_ordered_cheapest_to_most_expensive() -> None:
    assert LAYER_ORDER == (
        ExtractionLayer.STRUCTURED_IMPORT,
        ExtractionLayer.SELECTOR_TEMPLATE,
        ExtractionLayer.PDF_TEXT,
        ExtractionLayer.PDF_TABLE,
        ExtractionLayer.OCR,
        ExtractionLayer.LLM_ASSISTED,
        ExtractionLayer.HUMAN_TRANSCRIPTION,
    )
    # The IntEnum value IS the cost rank, so cheaper compares as smaller.
    assert ExtractionLayer.STRUCTURED_IMPORT < ExtractionLayer.OCR
    assert [layer.cost for layer in LAYER_ORDER] == [1, 2, 3, 4, 5, 6, 7]


def test_method_strings_match_the_extraction_method_vocabulary() -> None:
    # These strings are recorded in extraction.method; llm_assisted MUST match the DB
    # CHECK that ties layer 6 to the §25 model-provenance columns.
    assert ExtractionLayer.LLM_ASSISTED.method == "llm_assisted"
    assert LLM_LAYER is ExtractionLayer.LLM_ASSISTED
    assert {layer.method for layer in ExtractionLayer} == {
        "structured_import",
        "selector_template",
        "pdf_text",
        "pdf_table",
        "ocr",
        "llm_assisted",
        "human_transcription",
    }


def test_from_method_round_trips() -> None:
    for layer in ExtractionLayer:
        assert ExtractionLayer.from_method(layer.method) is layer
    with pytest.raises(KeyError):
        ExtractionLayer.from_method("no_such_method")


def test_cheapest_sufficient_picks_the_least_cost_candidate() -> None:
    assert (
        cheapest_sufficient(
            [ExtractionLayer.OCR, ExtractionLayer.STRUCTURED_IMPORT, ExtractionLayer.PDF_TEXT]
        )
        is ExtractionLayer.STRUCTURED_IMPORT
    )
    assert cheapest_sufficient([ExtractionLayer.HUMAN_TRANSCRIPTION]) is (
        ExtractionLayer.HUMAN_TRANSCRIPTION
    )


def test_cheapest_sufficient_rejects_an_empty_candidate_set() -> None:
    # Every input is at least human-transcribable, so no candidate is a caller bug.
    with pytest.raises(ValueError, match="no sufficient layer"):
        cheapest_sufficient([])


def test_cheaper_of() -> None:
    assert cheaper_of(ExtractionLayer.PDF_TEXT, ExtractionLayer.OCR) is ExtractionLayer.PDF_TEXT
    assert cheaper_of(ExtractionLayer.OCR, ExtractionLayer.PDF_TEXT) is ExtractionLayer.PDF_TEXT
