# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The parser-interface claim contract (§24.1): raw_value preserved before typing INCLUDING
for values SIG cannot parse (SIG-PARSE-004, P2); the mandatory locator, with a locator-less
claim rejected (SIG-PARSE-003); and the extraction method + normalized reason travelling
with the claim (SIG-PARSE-001/005)."""

from __future__ import annotations

import pytest
from parsing.claim import ParsedClaim, ParsedValue
from parsing.layers import ExtractionLayer
from parsing.locator import Locator, LocatorRequired
from parsing.reason_codes import ReasonKind, normalize_reason


def _claim(value: ParsedValue) -> ParsedClaim:
    return ParsedClaim(
        subject="okc_pd",
        predicate="reason_for_search",
        value=value,
        locator=Locator.cell(2, 4, sheet="log"),
        layer=ExtractionLayer.STRUCTURED_IMPORT,
    )


def test_raw_value_is_preserved_for_a_parsed_value() -> None:
    v = ParsedValue.typed("12", 12, value_kind="integer")
    assert v.raw_value == "12"
    assert v.parsed == 12
    assert v.is_parseable


def test_raw_value_is_preserved_for_an_unparseable_value_round_trip() -> None:
    # AC2: a value SIG cannot type keeps its raw literal; nothing is dropped.
    raw = "twelve-ish (see note)"
    v = ParsedValue.unparseable(raw, note="not a number")
    assert v.parsed is None
    assert v.parse_ok is False
    assert v.raw_value == raw
    # Round-trip through the recorded row: the raw literal survives.
    row = v.to_row()
    assert row["raw_value"] == raw
    assert row["value"] is None
    assert row["parse_ok"] is False
    assert ParsedValue(**{k: row[k] for k in ("raw_value", "parse_ok")}).raw_value == raw


def test_raw_value_may_not_be_none() -> None:
    with pytest.raises(ValueError, match="raw_value MUST be preserved"):
        ParsedValue(raw_value=None)  # type: ignore[arg-type]


def test_unparseable_value_may_not_carry_a_parsed_value() -> None:
    with pytest.raises(ValueError, match="MUST NOT carry a parsed value"):
        ParsedValue(raw_value="x", parsed=1, parse_ok=False)


def test_a_claim_without_a_locator_is_rejected() -> None:
    # AC1 / SIG-PARSE-003: a locator-less extraction is rejected, not admitted.
    with pytest.raises(LocatorRequired, match="every extraction MUST emit a locator"):
        ParsedClaim(
            subject="okc_pd",
            predicate="reason_for_search",
            value=ParsedValue.typed("12", 12),
            locator=None,  # type: ignore[arg-type]
            layer=ExtractionLayer.STRUCTURED_IMPORT,
        )
    with pytest.raises(LocatorRequired):
        ParsedClaim(
            subject="s",
            predicate="p",
            value=ParsedValue.typed("v", "v"),
            locator="page 1",  # type: ignore[arg-type]
            layer=ExtractionLayer.PDF_TEXT,
        )


def test_claim_records_method_and_carries_raw_value_and_locator() -> None:
    claim = _claim(ParsedValue.unparseable("n/a"))
    assert claim.extraction_method == "structured_import"
    row = claim.to_row()
    assert row["raw_value"] == "n/a"
    assert row["extraction_method"] == "structured_import"
    assert row["locator"]["kind"] == "cell"
    assert "reason" not in row  # no reason attached


def test_normalized_reason_travels_with_the_claim() -> None:
    reason = normalize_reason("Criminal Investigation", ReasonKind.CONSTRAINED_DROPDOWN)
    claim = ParsedClaim(
        subject="okc_pd",
        predicate="reason_for_search",
        value=ParsedValue.typed("Criminal Investigation", "criminal_investigation"),
        locator=Locator.cell(2, 4),
        layer=ExtractionLayer.STRUCTURED_IMPORT,
        reason=reason,
    )
    row = claim.to_row()
    assert row["reason"]["reason_code"] == "criminal_investigation"
    assert row["reason"]["reason_kind"] == "constrained_dropdown"
    assert row["reason"]["reason_raw_value"] == "Criminal Investigation"
