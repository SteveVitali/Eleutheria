# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The mandatory-locator schema (§24.1, SIG-PARSE-003): the six addressable locator kinds,
their validation, and the ``jsonb`` row shape the evidence viewer resolves. The
locator-*less* rejection is asserted on the claim contract (test_claim.py)."""

from __future__ import annotations

import pytest
from parsing.locator import InvalidLocator, Locator, LocatorKind


def test_every_locator_kind_constructs_and_renders_a_tagged_row() -> None:
    cases = {
        LocatorKind.PAGE: Locator.page(3),
        LocatorKind.BBOX: Locator.bbox(2, (10.0, 20.0, 110.0, 40.0)),
        LocatorKind.CELL: Locator.cell(4, 1, sheet="Sheet1"),
        LocatorKind.ROW: Locator.row(7),
        LocatorKind.BYTE_RANGE: Locator.byte_range(100, 128),
        LocatorKind.DOM_PATH: Locator.dom_path("table#roster tr:nth-child(2) td.count"),
    }
    for kind, loc in cases.items():
        assert loc.kind is kind
        row = loc.to_row()
        assert row["kind"] == kind.value
        # The tag plus the kind-specific fields, nothing else.
        assert set(row) - {"kind"} == set(loc.fields)


def test_page_and_bbox_pages_are_one_based() -> None:
    with pytest.raises(InvalidLocator, match="page"):
        Locator.page(0)
    with pytest.raises(InvalidLocator, match="page"):
        Locator.bbox(0, (0.0, 0.0, 1.0, 1.0))


def test_bbox_rejects_a_malformed_box() -> None:
    with pytest.raises(InvalidLocator, match="x1>=x0"):
        Locator.bbox(1, (10.0, 10.0, 5.0, 20.0))
    with pytest.raises(InvalidLocator, match="x0, y0, x1, y1"):
        Locator.bbox(1, (1.0, 2.0, 3.0))  # type: ignore[arg-type]


def test_byte_range_must_be_non_negative_and_ordered() -> None:
    assert Locator.byte_range(0, 0).fields == {"start": 0, "end": 0}
    with pytest.raises(InvalidLocator, match="end>=start"):
        Locator.byte_range(10, 5)
    with pytest.raises(InvalidLocator, match="start"):
        Locator.byte_range(-1, 5)


def test_cell_omits_optional_sheet_when_absent() -> None:
    assert Locator.cell(0, 0).fields == {"row": 0, "column": 0}
    assert Locator.cell(0, 0, sheet="S").fields == {"row": 0, "column": 0, "sheet": "S"}


def test_dom_path_requires_a_non_empty_selector() -> None:
    with pytest.raises(InvalidLocator, match="non-empty selector"):
        Locator.dom_path("")


def test_constructing_directly_rejects_missing_and_unknown_fields() -> None:
    with pytest.raises(InvalidLocator, match="MUST carry"):
        Locator(LocatorKind.PAGE, {})
    with pytest.raises(InvalidLocator, match="unexpected"):
        Locator(LocatorKind.PAGE, {"page": 1, "colour": "red"})


def test_bool_is_not_accepted_as_an_int_field() -> None:
    # bool is an int subclass; a page of `True` would silently pass a naive check.
    with pytest.raises(InvalidLocator):
        Locator.page(True)  # type: ignore[arg-type]


def test_locators_are_frozen_and_value_equal() -> None:
    import dataclasses

    assert Locator.page(1) == Locator.page(1)
    assert Locator.page(1) != Locator.page(2)
    with pytest.raises(dataclasses.FrozenInstanceError):
        Locator.page(1).kind = LocatorKind.ROW  # type: ignore[misc]
