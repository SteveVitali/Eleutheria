# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The table-extraction layer (layer 4, ``pdf_table``) ADR-033 deferred to connectors.

ADR-033 froze the seven-layer vocabulary (:mod:`parsing.layers`) but deferred the
**concrete engines** for layers 3–5 to the connector tickets that need them (LD-F17):
"the concrete layer-3/4/5 engines are owned by the P07.2/P07.3 connector tickets." The
Stage-5 pathway connectors (P21.9) need **layer 4 — table extraction from a procurement
document**: a contract or purchase order lays vendor / product / amount / date out as a
table, and each cell value must be extracted with a **cell locator** so the evidence
viewer can point at exactly where it came from (SIG-PARSE-003).

This is that engine, kept dependency-light and deterministic exactly as ADR-033's
classification is (no third-party PDF library — the heavy binary engines stay out of the
frozen §47 layout). A procurement table reaches this layer as its **extracted text grid**:
pipe/tab-delimited rows, the form a PDF-to-text pass or a records-portal HTML table yields.
The engine parses that grid into addressable cells and emits :class:`ParsedClaim`\\s at
:data:`ExtractionLayer.PDF_TABLE`, each carrying a ``CELL`` locator and the verbatim
``raw_value`` (P2). A cell SIG cannot type is kept as an unparseable value, never dropped.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .claim import ParsedClaim, ParsedValue
from .layers import ExtractionLayer
from .locator import Locator

__all__ = [
    "TABLE_LAYER",
    "Table",
    "parse_table",
    "table_claims",
]

#: The extraction layer every value read by this engine is recorded at (§24.1).
TABLE_LAYER: ExtractionLayer = ExtractionLayer.PDF_TABLE


@dataclass(frozen=True)
class Table:
    """A parsed procurement table: a header row plus data rows of raw cell strings.

    ``header`` is row 0; ``rows`` are the data rows (0-based within :attr:`rows`, so a
    cell's spreadsheet row in the whole table is ``row_index + 1``). Cell strings are the
    verbatim source literals — nothing is typed here (typing happens in
    :meth:`ParsedValue.typed` at the call site, preserving ``raw_value``).
    """

    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]

    def column_index(self, name: str) -> int:
        """The 0-based column index of ``name`` (case-insensitive), or raise ``KeyError``."""
        lowered = name.strip().lower()
        for i, col in enumerate(self.header):
            if col.strip().lower() == lowered:
                return i
        raise KeyError(f"column {name!r} not in table header {list(self.header)}")

    def cell(self, row_index: int, column: str) -> str:
        """The verbatim cell string at ``row_index`` / column ``name``."""
        return self.rows[row_index][self.column_index(column)]

    def locator(self, row_index: int, column: str) -> Locator:
        """A ``CELL`` locator for the cell (row 0 is the header, so data rows are +1)."""
        return Locator.cell(row=row_index + 1, column=self.column_index(column))


def parse_table(data: bytes, *, delimiter: str = "|") -> Table:
    """Parse a delimited procurement-table capture into a :class:`Table` (layer 4).

    Deterministic and dependency-free: it splits on newlines and ``delimiter``, strips
    each cell, and drops fully-blank lines (a table extracted from PDF text routinely
    carries blank separator lines). The first non-blank line is the header. Raises
    :class:`ValueError` for an empty capture — an empty table is a caller/fixture bug.
    """
    text = data.decode("utf-8", errors="strict")
    lines = [ln for ln in (line.strip() for line in text.splitlines()) if ln]
    if not lines:
        raise ValueError("a procurement table capture is empty (no rows to extract)")
    grid = [tuple(cell.strip() for cell in line.split(delimiter)) for line in lines]
    header = grid[0]
    width = len(header)
    rows: list[tuple[str, ...]] = []
    for row in grid[1:]:
        # Pad/truncate a ragged row to the header width so cell locators stay valid;
        # a short row keeps its raw cells and pads with empty strings (never drops).
        if len(row) < width:
            row = (*row, *([""] * (width - len(row))))
        elif len(row) > width:
            row = row[:width]
        rows.append(row)
    return Table(header=tuple(header), rows=tuple(rows))


def table_claims(
    table: Table,
    *,
    subject_of_row: Sequence[str],
    predicate_columns: Mapping[str, str],
    typed_columns: Mapping[str, str] | None = None,
) -> list[ParsedClaim]:
    """Emit one :class:`ParsedClaim` per (row, mapped column) at the ``pdf_table`` layer.

    ``subject_of_row`` gives the subject id for each data row (row *i* → ``subject_of_row[i]``).
    ``predicate_columns`` maps a **column name** to the **predicate** its cell asserts.
    ``typed_columns`` optionally names a ``value_kind`` per column (e.g. ``"amount"`` →
    ``"decimal"``) — a numeric cell that fails to parse is kept as an *unparseable* value
    (P2, SIG-PARSE-004), never dropped. Every emitted claim carries a ``CELL`` locator, so
    a locator-less extraction is impossible (SIG-PARSE-003).
    """
    typed_columns = dict(typed_columns or {})
    claims: list[ParsedClaim] = []
    for row_index in range(len(table.rows)):
        subject = subject_of_row[row_index]
        for column, predicate in predicate_columns.items():
            raw = table.cell(row_index, column)
            value = _typed_cell(raw, typed_columns.get(column))
            claims.append(
                ParsedClaim(
                    subject=subject,
                    predicate=predicate,
                    value=value,
                    locator=table.locator(row_index, column),
                    layer=TABLE_LAYER,
                )
            )
    return claims


def _typed_cell(raw: str, value_kind: str | None) -> ParsedValue:
    """Type a cell per ``value_kind`` while always preserving ``raw`` (SIG-PARSE-004)."""
    if value_kind in (None, "text"):
        return ParsedValue.typed(raw, raw, value_kind="text")
    if value_kind in ("decimal", "amount", "int", "integer"):
        cleaned = raw.replace("$", "").replace(",", "").strip()
        try:
            parsed: object = int(cleaned) if value_kind in ("int", "integer") else float(cleaned)
        except ValueError:
            return ParsedValue.unparseable(raw, note=f"not a {value_kind}: {raw!r}")
        return ParsedValue.typed(raw, parsed, value_kind=value_kind)
    return ParsedValue.typed(raw, raw, value_kind=value_kind)
