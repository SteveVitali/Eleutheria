# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The mandatory-locator contract every extraction obeys (§24.1, SIG-PARSE-003).

Every value SIG extracts MUST be able to say **where it came from**. A locator is that
answer: a page, a bounding box, a spreadsheet cell, a row, a byte range, or a DOM path —
whichever addresses the value in its capture. The evidence viewer (§39.6) and the
defensibility guarantee (OL-24-18) both depend on it, so an extraction that cannot cite a
locator is **rejected** (:class:`LocatorRequired`) rather than admitted without provenance.

This module owns that contract for the whole parsing stack — every layer
(:mod:`parsing.layers`), from a structured CSV import to an LLM-assisted extraction,
produces claims addressed by the *same* :class:`Locator` type, so the evidence viewer and
every connector resolve one shape. It is deliberately small and dependency-free: the layer
enum, the classification verdict, and the claim contract all build on it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

__all__ = [
    "LocatorKind",
    "Locator",
    "InvalidLocator",
    "LocatorRequired",
]


class InvalidLocator(ValueError):
    """A locator whose kind-specific fields are missing or malformed.

    Raised while *constructing* a locator — an offending page number, an ill-formed bbox,
    a byte range with ``end < start``. Distinct from :class:`LocatorRequired`, which is
    raised when a claim carries **no** locator at all.
    """


class LocatorRequired(ValueError):
    """A claim that carries no locator — rejected (SIG-PARSE-003).

    An extraction that cannot say where a value came from MUST be rejected, because the
    evidence viewer (§39.6) and the defensibility guarantee (OL-24-18) both depend on the
    locator. This is the mechanical enforcement of that MUST.
    """


class LocatorKind(StrEnum):
    """The six addressable locator kinds the parsing stack emits (SIG-PARSE-003).

    Each names a *way* of pointing into a capture; which one applies depends on the
    layer that produced the value (§24.1): a spreadsheet import emits ``CELL``, a PDF text
    layer ``PAGE``/``BBOX``, a stable-HTML selector ``DOM_PATH``, a raw structured feed
    ``BYTE_RANGE``. The evidence viewer resolves all six.
    """

    PAGE = "page"
    BBOX = "bbox"
    CELL = "cell"
    ROW = "row"
    BYTE_RANGE = "byte_range"
    DOM_PATH = "dom_path"


# The required fields each locator kind carries. A locator MUST supply exactly the fields
# its kind names — no more (unknown fields are rejected so a typo cannot silently produce a
# locator the evidence viewer can't resolve), no fewer.
_REQUIRED_FIELDS: dict[LocatorKind, tuple[str, ...]] = {
    LocatorKind.PAGE: ("page",),
    LocatorKind.BBOX: ("page", "bbox"),
    LocatorKind.CELL: ("row", "column"),
    LocatorKind.ROW: ("row",),
    LocatorKind.BYTE_RANGE: ("start", "end"),
    LocatorKind.DOM_PATH: ("selector",),
}

# Fields a kind MAY carry in addition to its required set (all else is rejected).
_OPTIONAL_FIELDS: dict[LocatorKind, tuple[str, ...]] = {
    LocatorKind.CELL: ("sheet",),
}


@dataclass(frozen=True)
class Locator:
    """The addressable pointer to where an extracted value came from (SIG-PARSE-003).

    A locator is a :class:`LocatorKind` plus the kind-specific ``fields`` that address the
    value in its capture. Construct one through the classmethods (:meth:`page`,
    :meth:`bbox`, :meth:`cell`, :meth:`row`, :meth:`byte_range`, :meth:`dom_path`) rather
    than by hand — they validate the fields and are the readable call sites a connector
    uses. :meth:`to_row` renders the ``jsonb`` shape stored on ``claim_evidence.locator``.
    """

    kind: LocatorKind
    fields: Mapping[str, Any]

    def __post_init__(self) -> None:
        required = _REQUIRED_FIELDS[self.kind]
        allowed = set(required) | set(_OPTIONAL_FIELDS.get(self.kind, ()))
        missing = [name for name in required if self.fields.get(name) is None]
        if missing:
            raise InvalidLocator(
                f"a {self.kind.value} locator MUST carry {list(required)}; missing {missing} "
                "(SIG-PARSE-003)"
            )
        unknown = [name for name in self.fields if name not in allowed]
        if unknown:
            raise InvalidLocator(
                f"a {self.kind.value} locator accepts {sorted(allowed)}; got unexpected "
                f"{unknown} (SIG-PARSE-003)"
            )
        # Freeze the mapping to a plain dict so equality/hash are stable and the stored
        # jsonb is deterministic.
        object.__setattr__(self, "fields", dict(self.fields))

    # -- constructors, one per kind (the readable call sites) --

    @classmethod
    def page(cls, page: int) -> Locator:
        """A whole-page locator (digital-native or OCR'd PDF text) — 1-based page."""
        _require_non_negative_int("page", page, one_based=True)
        return cls(LocatorKind.PAGE, {"page": page})

    @classmethod
    def bbox(cls, page: int, box: tuple[float, float, float, float]) -> Locator:
        """A bounding box ``(x0, y0, x1, y1)`` on a 1-based ``page`` (PDF table cell)."""
        _require_non_negative_int("page", page, one_based=True)
        if len(box) != 4:
            raise InvalidLocator(f"bbox MUST be (x0, y0, x1, y1); got {box!r} (SIG-PARSE-003)")
        x0, y0, x1, y1 = box
        if x1 < x0 or y1 < y0:
            raise InvalidLocator(f"bbox MUST have x1>=x0 and y1>=y0; got {box!r}")
        return cls(LocatorKind.BBOX, {"page": page, "bbox": [x0, y0, x1, y1]})

    @classmethod
    def cell(cls, row: int, column: int, *, sheet: str | None = None) -> Locator:
        """A spreadsheet cell — 0-based ``row``/``column``, optional ``sheet`` name."""
        _require_non_negative_int("row", row)
        _require_non_negative_int("column", column)
        fields: dict[str, Any] = {"row": row, "column": column}
        if sheet is not None:
            fields["sheet"] = sheet
        return cls(LocatorKind.CELL, fields)

    @classmethod
    def row(cls, row: int) -> Locator:
        """A record/row locator — 0-based ``row`` (a CSV/JSON-array member)."""
        _require_non_negative_int("row", row)
        return cls(LocatorKind.ROW, {"row": row})

    @classmethod
    def byte_range(cls, start: int, end: int) -> Locator:
        """A byte range ``[start, end)`` into the capture bytes (a raw structured feed)."""
        _require_non_negative_int("start", start)
        _require_non_negative_int("end", end)
        if end < start:
            raise InvalidLocator(
                f"a byte-range locator MUST have end>=start; got [{start}, {end}) (SIG-PARSE-003)"
            )
        return cls(LocatorKind.BYTE_RANGE, {"start": start, "end": end})

    @classmethod
    def dom_path(cls, selector: str) -> Locator:
        """A DOM path / CSS selector into stable HTML (a selector/template extraction)."""
        if not selector:
            raise InvalidLocator("a dom_path locator MUST carry a non-empty selector")
        return cls(LocatorKind.DOM_PATH, {"selector": selector})

    def to_row(self) -> dict[str, Any]:
        """The ``jsonb`` shape stored on ``claim_evidence.locator`` (a tagged object)."""
        return {"kind": self.kind.value, **self.fields}


def _require_non_negative_int(name: str, value: Any, *, one_based: bool = False) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidLocator(f"{name} MUST be an int; got {value!r}")
    floor = 1 if one_based else 0
    if value < floor:
        raise InvalidLocator(f"{name} MUST be >= {floor}; got {value}")
