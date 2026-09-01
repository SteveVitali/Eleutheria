# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The hardness precondition (P06.1 AC6), as a checkable property of the slice.

The precondition is declared in advance in docs/slice/P06.1_hardness_precondition.md;
these deterministic checks prove the chosen jurisdiction actually satisfies it. A
jurisdiction failing ANY property MUST NOT be used.
"""

from __future__ import annotations

from pathlib import Path

from acceptance import okc_slice as slice_mod

_ROOT = Path(__file__).resolve().parents[2]
_PRECONDITION = _ROOT / "docs" / "slice" / "P06.1_hardness_precondition.md"


def test_precondition_declaration_is_committed() -> None:
    assert _PRECONDITION.exists(), "the hardness precondition MUST be declared before the slice"
    text = _PRECONDITION.read_text()
    assert "Oklahoma City" in text
    assert "pre-registration" in text.lower() or "pre-registered" in text.lower()


def test_at_least_three_independent_source_families() -> None:
    graph = slice_mod.build_slice()
    families = {a.source_family for a in graph.evidence.artifacts.values()}
    assert len(families) >= 3, families


def test_two_claims_on_one_predicate_that_disagree() -> None:
    graph = slice_mod.build_slice()
    claimed = [c for c in graph.count_claims if c.count_basis == "claimed"]
    values = {c.value for c in claimed}
    assert len(values) >= 2, "need >=2 disagreeing claims on one predicate"
    assert 190 in values and 299 in values


def test_at_least_one_asset_with_no_operator() -> None:
    graph = slice_mod.build_slice()
    assert any(a.operator is None for a in graph.assets), "need >=1 asset with no operator"


def test_at_least_one_lifecycle_transition_by_a_dated_document() -> None:
    graph = slice_mod.build_slice()
    timeline = graph.facts.get("timeline", [])
    renewal = next((f for f in timeline if f.key == "renewal"), None)
    assert renewal is not None and renewal.value == "2026-08-18"
    assert renewal.evidence is not None and renewal.evidence.resolves_to_document()
