# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The clause-locator layer (layer 3, ``pdf_text``) ADR-033 deferred to connectors.

The companion to :mod:`parsing.tables`. Where a procurement document is a table, a
**policy document** — an agency operations manual, a surveillance ordinance, a court
authorization — is prose organised into **numbered clauses** (``§ 5-118``, ``Section 3``,
``Article II(a)``). The Stage-5 FR/CSS/forensics pathway extracts *policy* facts (a
retention period, an authorization, a use restriction) from these clauses, and each fact
must cite **which clause** it came from (SIG-PARSE-003) — a policy claim with no clause
locator is not defensible.

This is that layer-3 engine (ADR-033 deferred the concrete layer-3 engine to the
connector tickets, LD-F17): it splits a policy capture into its clauses, addresses each by
a **byte range** into the capture (the locator kind for a raw text span), and emits
:class:`ParsedClaim`\\s at :data:`ExtractionLayer.PDF_TEXT`. Deterministic and
dependency-free — a regexp over clause headings, no NLP model — so the same policy parses
to the same clauses every time (SIG-PARSE-007).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from .claim import ParsedClaim, ParsedValue
from .layers import ExtractionLayer
from .locator import Locator

__all__ = [
    "CLAUSE_LAYER",
    "Clause",
    "locate_clauses",
    "find_clause",
    "clause_claim",
]

#: The extraction layer every clause value is recorded at (§24.1 layer 3).
CLAUSE_LAYER: ExtractionLayer = ExtractionLayer.PDF_TEXT

# A clause heading: a §/Section/Article marker plus its identifier, at line start.
_CLAUSE_HEADING = re.compile(
    r"(?im)^\s*(?:§+\s*|section\s+|article\s+|clause\s+)([0-9]+(?:[.\-][0-9a-z]+)*|[ivxlc]+)"
)


@dataclass(frozen=True)
class Clause:
    """One addressable clause of a policy document (SIG-PARSE-003).

    ``label`` is the clause identifier (``5-118``, ``3``, ``II``); ``text`` is the
    verbatim clause body; ``start``/``end`` are the byte offsets into the capture that a
    :class:`~parsing.locator.Locator` byte-range addresses.
    """

    label: str
    text: str
    start: int
    end: int

    @property
    def locator(self) -> Locator:
        """A byte-range locator addressing this clause in the capture (SIG-PARSE-003)."""
        return Locator.byte_range(start=self.start, end=self.end)


def locate_clauses(data: bytes) -> list[Clause]:
    """Split a policy capture into its numbered clauses, each byte-addressed (layer 3).

    Deterministic: it scans for ``§``/``Section``/``Article``/``Clause`` headings and
    treats the span from one heading to the next as that clause's body. A document with no
    recognisable heading yields a single ``whole`` clause covering the entire capture, so a
    policy fact can still be located (never dropped for want of a heading).
    """
    text = data.decode("utf-8", errors="strict")
    matches = list(_CLAUSE_HEADING.finditer(text))
    if not matches:
        raw = text.encode("utf-8")
        return [Clause(label="whole", text=text, start=0, end=len(raw))]
    clauses: list[Clause] = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        # Byte offsets (the locator addresses bytes, not code points).
        b_start = len(text[:start].encode("utf-8"))
        b_end = len(text[:end].encode("utf-8"))
        clauses.append(Clause(label=match.group(1), text=body, start=b_start, end=b_end))
    return clauses


def find_clause(clauses: list[Clause], label: str) -> Clause | None:
    """The clause whose label matches ``label`` (case-insensitive), or ``None``."""
    wanted = label.strip().lower().lstrip("§").strip()
    for clause in clauses:
        if clause.label.lower() == wanted:
            return clause
    return None


def clause_claim(
    clause: Clause,
    *,
    subject: str,
    predicate: str,
    value: str,
    value_kind: str | None = None,
    typed: object = None,
) -> ParsedClaim:
    """Emit one policy :class:`ParsedClaim` located at ``clause`` (SIG-PARSE-003).

    ``value`` is the verbatim raw literal (preserved, P2); ``typed`` is its typed form
    when SIG could type it (else the raw value stands). The claim is read at the
    ``pdf_text`` layer and carries the clause's byte-range locator.
    """
    parsed = (
        ParsedValue.typed(value, typed if typed is not None else value, value_kind=value_kind)
        if value_kind is not None
        else ParsedValue.typed(value, value, value_kind="text")
    )
    return ParsedClaim(
        subject=subject,
        predicate=predicate,
        value=parsed,
        locator=clause.locator,
        layer=CLAUSE_LAYER,
    )


def clause_map(clauses: list[Clause]) -> Mapping[str, Clause]:
    """A label → clause map for quick lookup by a connector extractor."""
    return {c.label: c for c in clauses}
