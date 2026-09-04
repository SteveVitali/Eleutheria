# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The parser-interface claim contract every connector extracts through (§24.1).

This is the stable shape every layer of the parsing stack (:mod:`parsing.layers`) — from a
structured CSV import to an LLM-assisted extraction — produces, and every connector's
``extract``/``normalize`` stage (§21.1) emits. It binds the four invariants this ticket
owns into one type so they cannot be forgotten per-source:

* **raw_value is preserved before any typing** (:class:`ParsedValue`, SIG-PARSE-004, P2) —
  including for a value SIG **cannot** parse: the raw literal is kept, ``parsed`` is
  ``None``, and nothing is dropped. A value SIG could not type is data about the source.
* **every claim carries a locator** (:class:`ParsedClaim`, SIG-PARSE-003) — a claim built
  without one is **rejected** (:class:`~parsing.locator.LocatorRequired`).
* **the extraction method is recorded** (the :class:`~parsing.layers.ExtractionLayer` the
  claim was read at — SIG-PARSE-001), so provenance always says *how* the value was read.
* **the normalized reason, if any, travels with the claim**
  (:class:`~parsing.reason_codes.NormalizedReason`, SIG-PARSE-005/006) — with its raw text
  retained and its mapping version stamped.

The type is deliberately dependency-light and deterministic; it produces the row shape the
claim spine stores (``raw_value``, ``claim_evidence.locator``, ``extraction.method``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .layers import ExtractionLayer
from .locator import Locator, LocatorRequired
from .reason_codes import NormalizedReason

__all__ = [
    "ParsedValue",
    "ParsedClaim",
]


@dataclass(frozen=True)
class ParsedValue:
    """A single extracted value with its raw literal always preserved (SIG-PARSE-004, P2).

    ``raw_value`` is the source's verbatim text and is **mandatory** — it is captured before
    any typing or normalization and is retained even when parsing fails. ``parsed`` is the
    typed/normalized value (``None`` when SIG could not parse it), ``value_kind`` names the
    type that was applied, and ``parse_ok`` says whether typing succeeded. Build one through
    :meth:`typed` or :meth:`unparseable` rather than by hand.
    """

    raw_value: str
    parsed: Any | None = None
    value_kind: str | None = None
    parse_ok: bool = True
    note: str | None = None

    def __post_init__(self) -> None:
        if self.raw_value is None:  # type: ignore[comparison-overlap]
            raise ValueError(
                "raw_value MUST be preserved before typing/normalization — it is never "
                "None (SIG-PARSE-004, P2)"
            )
        if not self.parse_ok and self.parsed is not None:
            raise ValueError("an unparseable value MUST NOT carry a parsed value (SIG-PARSE-004)")

    @classmethod
    def typed(cls, raw_value: str, parsed: Any, *, value_kind: str | None = None) -> ParsedValue:
        """A value SIG parsed: the raw literal plus its typed form."""
        return cls(raw_value=raw_value, parsed=parsed, value_kind=value_kind, parse_ok=True)

    @classmethod
    def unparseable(cls, raw_value: str, *, note: str | None = None) -> ParsedValue:
        """A value SIG could NOT parse: the raw literal is kept, ``parsed`` stays ``None``.

        This is the case SIG-PARSE-004 exists for — the value is retained as data about the
        source rather than dropped as an error. ``note`` records why it could not be typed.
        """
        return cls(raw_value=raw_value, parsed=None, value_kind=None, parse_ok=False, note=note)

    @property
    def is_parseable(self) -> bool:
        """Whether SIG produced a typed value (``False`` keeps only the raw literal)."""
        return self.parse_ok

    def to_row(self) -> dict[str, Any]:
        """The value fields recorded on the claim; ``raw_value`` is always present."""
        return {
            "raw_value": self.raw_value,
            "value": self.parsed,
            "value_kind": self.value_kind,
            "parse_ok": self.parse_ok,
            "note": self.note,
        }


@dataclass(frozen=True)
class ParsedClaim:
    """One extracted claim as the parsing stack emits it (SIG-PARSE-001/003/004/005).

    Carries the subject/predicate, the :class:`ParsedValue` (raw literal preserved), the
    mandatory :class:`~parsing.locator.Locator`, the :class:`~parsing.layers.ExtractionLayer`
    it was read at (the recorded method), and an optional normalized reason. Construction
    **rejects** a claim with no locator (SIG-PARSE-003) — the single mechanical guardrail the
    evidence viewer and defensibility guarantee depend on.
    """

    subject: str
    predicate: str
    value: ParsedValue
    locator: Locator
    layer: ExtractionLayer
    reason: NormalizedReason | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.locator, Locator):
            raise LocatorRequired(
                "every extraction MUST emit a locator; a claim without one is rejected "
                "(SIG-PARSE-003)"
            )

    @property
    def extraction_method(self) -> str:
        """The ``extraction.method`` value for the layer this claim was read at."""
        return self.layer.method

    def to_row(self) -> dict[str, Any]:
        """The claim row shape for the spine (raw_value, locator, method, reason)."""
        row: dict[str, Any] = {
            "subject": self.subject,
            "predicate": self.predicate,
            **self.value.to_row(),
            "locator": self.locator.to_row(),
            "extraction_method": self.extraction_method,
        }
        if self.reason is not None:
            row["reason"] = self.reason.to_row()
        return row
