# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The layered extraction strategy: cheapest sufficient method (§24.1, SIG-PARSE-001).

Parsing proceeds by the **cheapest method that suffices** for the input, and the method
used is **recorded on the extraction** so provenance always says *how* a value was read.
The layers, cheapest first (§24.1):

======  ==========================  ==========================================
Layer   Method                      Use when
======  ==========================  ==========================================
1       structured import           the source is already structured (CSV/XLSX/JSON)
2       selector/template           stable HTML or a known form layout
3       PDF text extraction         a digital-native PDF
4       PDF table extraction        tabular content in a digital PDF
5       OCR                         scanned documents
6       LLM-assisted extraction     unstructured prose where 1–5 fail (§25)
7       human transcription         everything else, and all adjudication
======  ==========================  ==========================================

This module owns the layer vocabulary and the cost ordering; the *selection* of a layer
for a given file (which depends on classification) lives in :mod:`parsing.classification`,
which reads the verdict and picks the cheapest layer that suffices. The enum values are the
strings recorded in ``extraction.method`` — in particular ``llm_assisted`` matches the DB
``CHECK (method <> 'llm_assisted' OR model_id IS NOT NULL …)`` that ties layer 6 to the §25
model-provenance columns (:mod:`parsing.extraction`).
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import IntEnum

__all__ = [
    "ExtractionLayer",
    "LAYER_ORDER",
    "LLM_LAYER",
    "cheaper_of",
    "cheapest_sufficient",
]


class ExtractionLayer(IntEnum):
    """The seven extraction layers (§24.1), ordered cheapest (1) to most expensive (7).

    An :class:`IntEnum` so the ordering *is* the cost: ``STRUCTURED_IMPORT < OCR`` means
    the structured import is the cheaper method. :attr:`method` is the string recorded on
    the extraction (``extraction.method``); construct from that string with
    :meth:`from_method`.
    """

    STRUCTURED_IMPORT = 1
    SELECTOR_TEMPLATE = 2
    PDF_TEXT = 3
    PDF_TABLE = 4
    OCR = 5
    LLM_ASSISTED = 6
    HUMAN_TRANSCRIPTION = 7

    @property
    def method(self) -> str:
        """The value recorded in ``extraction.method`` for this layer (SIG-PARSE-001)."""
        return _METHODS[self]

    @property
    def cost(self) -> int:
        """The layer's cost rank, 1 (cheapest) … 7 (most expensive)."""
        return int(self.value)

    @classmethod
    def from_method(cls, method: str) -> ExtractionLayer:
        """The layer for an ``extraction.method`` string, or :class:`KeyError`."""
        return _BY_METHOD[method]


_METHODS: dict[ExtractionLayer, str] = {
    ExtractionLayer.STRUCTURED_IMPORT: "structured_import",
    ExtractionLayer.SELECTOR_TEMPLATE: "selector_template",
    ExtractionLayer.PDF_TEXT: "pdf_text",
    ExtractionLayer.PDF_TABLE: "pdf_table",
    ExtractionLayer.OCR: "ocr",
    ExtractionLayer.LLM_ASSISTED: "llm_assisted",
    ExtractionLayer.HUMAN_TRANSCRIPTION: "human_transcription",
}

_BY_METHOD: dict[str, ExtractionLayer] = {method: layer for layer, method in _METHODS.items()}

#: The layers in cost order, cheapest first (§24.1).
LAYER_ORDER: tuple[ExtractionLayer, ...] = tuple(
    sorted(ExtractionLayer, key=lambda layer: layer.value)
)

#: Layer 6 — the seam where the parsing stack hands off to the §25 model-assisted
#: extraction boundary (:mod:`parsing.extraction`). Named so callers wire it explicitly.
LLM_LAYER: ExtractionLayer = ExtractionLayer.LLM_ASSISTED


def cheaper_of(a: ExtractionLayer, b: ExtractionLayer) -> ExtractionLayer:
    """The cheaper of two layers (the lower cost rank)."""
    return a if a.cost <= b.cost else b


def cheapest_sufficient(candidates: Iterable[ExtractionLayer]) -> ExtractionLayer:
    """The cheapest layer among those sufficient for an input (SIG-PARSE-001).

    ``candidates`` is the set of layers that *would* suffice to read the input; this
    returns the least-cost one, which is the method parsing MUST use. Raises
    :class:`ValueError` on an empty set — every input is at minimum sufficient for human
    transcription (layer 7), so a caller that produces no candidate has a bug rather than
    an unparseable input.
    """
    layers = sorted(candidates, key=lambda layer: layer.cost)
    if not layers:
        raise ValueError(
            "no sufficient layer offered; every input is at least human-transcribable "
            "(layer 7) — an empty candidate set is a caller bug (SIG-PARSE-001)"
        )
    return layers[0]
