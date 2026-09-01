# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Reason-code normalization (§24.2, SIG-PARSE-005/006): a versioned, inspectable,
reversible mapping stored as data; the raw text always retained; the mapping version
stamped on every result; free-text vs constrained-dropdown reasons normalized separately
and distinguished by signal strength; and changing the mapping never rewrites history."""

from __future__ import annotations

import pytest
from parsing.reason_codes import (
    VOCABULARY_MIGRATION_METHOD,
    NormalizedReason,
    ReasonKind,
    ReasonMapping,
    SignalStrength,
    load_reason_mapping,
    normalize_reason,
)


def test_free_text_and_dropdown_are_distinguished_by_signal_strength() -> None:
    # SIG-PARSE-006: the same reason from a dropdown is a stronger signal than typed text.
    free = normalize_reason("crim inv", ReasonKind.FREE_TEXT)
    drop = normalize_reason("Criminal Investigation", ReasonKind.CONSTRAINED_DROPDOWN)
    assert free.code == drop.code == "criminal_investigation"
    assert free.reason_kind is ReasonKind.FREE_TEXT
    assert free.signal_strength is SignalStrength.MODERATE
    assert drop.reason_kind is ReasonKind.CONSTRAINED_DROPDOWN
    assert drop.signal_strength is SignalStrength.STRONG


def test_free_text_matching_folds_case_whitespace_and_punctuation() -> None:
    for raw in ("Criminal Investigation", "  criminal   investigation ", "criminal investigation."):
        assert normalize_reason(raw, ReasonKind.FREE_TEXT).code == "criminal_investigation"


def test_an_unmapped_reason_retains_its_raw_text_and_does_not_match() -> None:
    # A reason SIG cannot categorize is data about the source, not an error to drop.
    result = normalize_reason("because I said so", ReasonKind.FREE_TEXT)
    assert result.matched is False
    assert result.code is None
    assert result.signal_strength is SignalStrength.NONE
    assert result.raw_text == "because I said so"


def test_every_canonical_code_is_reversible() -> None:
    # SIG-PARSE-005: the mapping is reversible — each code lists the raw variants it maps
    # from, and each such variant normalizes back to that code.
    mapping = load_reason_mapping()
    for kind in ReasonKind:
        for code in mapping.codes(kind):
            variants = mapping.raw_variants(code, kind)
            assert variants, f"{code} ({kind}) has no reverse variants"
            for raw in variants:
                assert mapping.normalize(raw, kind).code == code


def test_the_mapping_version_is_stamped_on_every_result() -> None:
    mapping = load_reason_mapping()
    result = normalize_reason("traffic stop", ReasonKind.FREE_TEXT)
    assert result.mapping_version == mapping.version
    # ...even when nothing matched.
    assert normalize_reason("???", ReasonKind.FREE_TEXT).mapping_version == mapping.version


def test_changing_the_mapping_does_not_rewrite_history() -> None:
    # SIG-STORE-038 / AC4: a v1 claim keeps its v1 stamp; a re-classification under v2 is a
    # NEW result, never an edit of the v1 one (the results are immutable and independent).
    v1 = ReasonMapping({"version": "1", "free_text": {"criminal_investigation": ["crim inv"]}})
    v2 = ReasonMapping(
        {"version": "2", "free_text": {"criminal_investigation": ["crim inv", "ci case"]}}
    )
    old = v1.normalize("crim inv", ReasonKind.FREE_TEXT)
    new = v2.normalize("crim inv", ReasonKind.FREE_TEXT)
    assert old.mapping_version == "1"
    assert new.mapping_version == "2"
    assert old.code == new.code == "criminal_investigation"
    # The old result is untouched by the existence of the new mapping.
    assert old == NormalizedReason(
        raw_text="crim inv",
        reason_kind=ReasonKind.FREE_TEXT,
        mapping_version="1",
        code="criminal_investigation",
        signal_strength=SignalStrength.MODERATE,
    )
    # A term v1 didn't know only resolves under v2 — v1 history is never retro-mapped.
    assert v1.normalize("ci case", ReasonKind.FREE_TEXT).code is None
    assert v2.normalize("ci case", ReasonKind.FREE_TEXT).code == "criminal_investigation"


def test_migration_method_constant_is_the_store_038_marker() -> None:
    assert VOCABULARY_MIGRATION_METHOD == "vocabulary_migration"


def test_an_ambiguous_mapping_is_rejected_at_load() -> None:
    with pytest.raises(ValueError, match="ambiguous"):
        ReasonMapping(
            {
                "version": "x",
                "free_text": {"a": ["same phrase"], "b": ["Same Phrase"]},
            }
        )
