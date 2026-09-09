# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Unit tests for the layer-3 clause-locator engine (ADR-033-deferred, LD-F17, P21.9)."""

from __future__ import annotations

from parsing.clauses import CLAUSE_LAYER, clause_claim, find_clause, locate_clauses
from parsing.layers import ExtractionLayer
from parsing.locator import LocatorKind

_POLICY = b"""Operations Manual

Section 3 Authorization
A cell-site simulator may be operated only under a court order.

Section 5-118 Retention
Recorded data shall not be retained longer than 30 days.
"""


def test_locate_clauses_splits_into_numbered_clauses() -> None:
    clauses = locate_clauses(_POLICY)
    labels = [c.label for c in clauses]
    assert labels == ["3", "5-118"]


def test_clause_layer_is_layer_3() -> None:
    assert CLAUSE_LAYER is ExtractionLayer.PDF_TEXT
    assert CLAUSE_LAYER.method == "pdf_text"


def test_clause_byte_range_locator_addresses_the_clause() -> None:
    clauses = locate_clauses(_POLICY)
    retention = find_clause(clauses, "5-118")
    assert retention is not None
    loc = retention.locator
    assert loc.kind is LocatorKind.BYTE_RANGE
    # the byte range points back at the exact clause text in the capture
    assert (
        _POLICY[loc.fields["start"] : loc.fields["end"]]
        .decode("utf-8")
        .strip()
        .startswith("Section 5-118")
    )


def test_find_clause_is_case_and_marker_insensitive() -> None:
    clauses = locate_clauses(_POLICY)
    assert find_clause(clauses, "§5-118") is not None
    assert find_clause(clauses, "3") is not None
    assert find_clause(clauses, "999") is None


def test_document_without_headings_yields_one_whole_clause() -> None:
    clauses = locate_clauses(b"A short ordinance with no section markers at all.")
    assert len(clauses) == 1
    assert clauses[0].label == "whole"
    assert clauses[0].locator.kind is LocatorKind.BYTE_RANGE


def test_clause_claim_preserves_raw_and_carries_clause_locator() -> None:
    clauses = locate_clauses(_POLICY)
    retention = find_clause(clauses, "5-118")
    assert retention is not None
    claim = clause_claim(
        retention,
        subject="dep:css-county",
        predicate="retention_period_days",
        value="30 days",
        value_kind="text",
    )
    assert claim.value.raw_value == "30 days"
    assert claim.extraction_method == "pdf_text"
    assert claim.locator.kind is LocatorKind.BYTE_RANGE
