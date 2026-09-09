# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Unit tests for the layer-4 table-extraction engine (ADR-033-deferred, LD-F17, P21.9)."""

from __future__ import annotations

import pytest
from parsing.layers import ExtractionLayer
from parsing.locator import LocatorKind
from parsing.tables import TABLE_LAYER, parse_table, table_claims

_PROCUREMENT = b"""
Vendor | Product | Amount | Date
Fusus | RTCC integration platform | $250,000 | 2024-02-01
Axon | Fusus enterprise | 90,000 | 2024-03-15
"""


def test_parse_table_reads_header_and_rows() -> None:
    table = parse_table(_PROCUREMENT)
    assert table.header == ("Vendor", "Product", "Amount", "Date")
    assert len(table.rows) == 2
    assert table.cell(0, "Vendor") == "Fusus"
    assert table.cell(1, "Product") == "Fusus enterprise"


def test_parse_table_is_layer_4() -> None:
    assert TABLE_LAYER is ExtractionLayer.PDF_TABLE
    assert TABLE_LAYER.method == "pdf_table"


def test_cell_locator_points_at_the_right_cell() -> None:
    table = parse_table(_PROCUREMENT)
    loc = table.locator(0, "Amount")
    assert loc.kind is LocatorKind.CELL
    # data row 0 is spreadsheet row 1 (row 0 is the header); Amount is column index 2
    assert loc.fields == {"row": 1, "column": 2}


def test_table_claims_preserve_raw_value_and_carry_locators() -> None:
    table = parse_table(_PROCUREMENT)
    claims = table_claims(
        table,
        subject_of_row=["contract:1", "contract:2"],
        predicate_columns={"Vendor": "vendor_name", "Amount": "contract_amount"},
        typed_columns={"Amount": "amount"},
    )
    assert len(claims) == 4  # 2 rows x 2 mapped columns
    by = {(c.subject, c.predicate): c for c in claims}
    amount = by[("contract:1", "contract_amount")]
    # raw literal preserved verbatim (P2, SIG-PARSE-004), typed value parsed alongside
    assert amount.value.raw_value == "$250,000"
    assert amount.value.parsed == 250000.0
    assert amount.extraction_method == "pdf_table"
    assert amount.locator.kind is LocatorKind.CELL


def test_unparseable_amount_is_kept_never_dropped() -> None:
    table = parse_table(b"Vendor | Amount\nFusus | see attachment")
    claims = table_claims(
        table,
        subject_of_row=["contract:1"],
        predicate_columns={"Amount": "contract_amount"},
        typed_columns={"Amount": "amount"},
    )
    (claim,) = claims
    assert claim.value.raw_value == "see attachment"
    assert claim.value.parsed is None
    assert claim.value.parse_ok is False


def test_ragged_row_is_padded_never_dropped() -> None:
    table = parse_table(b"A | B | C\nx | y")
    assert table.rows == (("x", "y", ""),)


def test_empty_capture_raises() -> None:
    with pytest.raises(ValueError):
        parse_table(b"   \n  \n")
