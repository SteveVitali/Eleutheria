# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Reason-code normalization: a versioned, inspectable, reversible mapping (§24.2).

A "reason" field says *why* a surveillance search or access happened. SIG normalizes those
free-form reasons to a small set of canonical codes — but never by throwing the original
away and never by a hidden code path. The mapping is:

* **stored as data** (``data/reason_codes.toml``) — inspectable, diffable, reviewed on its
  own like the resolution ruleset, not a Python literal (SIG-PARSE-005);
* **reversible** — every canonical code lists the raw variants that map to it, so a reader
  can see exactly what a code means (:meth:`ReasonMapping.raw_variants`);
* **versioned** — the ``version`` is stamped on every normalized reason
  (:attr:`NormalizedReason.mapping_version`); changing the mapping is a **new version**,
  never an edit of history. A bulk re-classification under a newer mapping is performed as
  **new claims** (``extraction_method = 'vocabulary_migration'``), never a rewrite of the
  claims already stamped with the old version (SIG-STORE-038).

Reasons arrive in **two forms** and are *different normalization problems* (SIG-PARSE-006),
so the form is recorded on the result and the two are matched separately:

* :attr:`ReasonKind.CONSTRAINED_DROPDOWN` — a value chosen from a fixed menu; a **strong**
  signal, matched case-insensitively against the menu labels;
* :attr:`ReasonKind.FREE_TEXT` — a typed phrase; a **moderate** signal at best, matched
  after casefolding and folding whitespace/punctuation.

The raw text is **always** retained (P2), including when nothing matches — an unmapped
reason is data about the source, not an error (SIG-PARSE-004).
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from importlib.resources import files
from typing import Any

__all__ = [
    "ReasonKind",
    "SignalStrength",
    "NormalizedReason",
    "ReasonMapping",
    "VOCABULARY_MIGRATION_METHOD",
    "load_reason_mapping",
    "normalize_reason",
]

# The extraction_method recorded when a bulk re-classification re-normalizes historical
# reasons under a newer mapping version — as NEW claims, never a rewrite (SIG-STORE-038).
VOCABULARY_MIGRATION_METHOD = "vocabulary_migration"


class ReasonKind(StrEnum):
    """The form a reason field arrived in (SIG-PARSE-006).

    The two are distinguished on the claim because a dropdown value is a much stronger
    signal than a typed phrase, and they are normalized as separate problems.
    """

    FREE_TEXT = "free_text"
    CONSTRAINED_DROPDOWN = "constrained_dropdown"


class SignalStrength(StrEnum):
    """How strong a normalized reason's signal is, given the form it arrived in."""

    STRONG = "strong"  # a matched constrained-dropdown value
    MODERATE = "moderate"  # a matched free-text phrase
    NONE = "none"  # nothing matched — the raw text is retained regardless


@dataclass(frozen=True)
class NormalizedReason:
    """The result of normalizing one reason field (SIG-PARSE-005/006).

    ``code`` is the canonical reason code, or ``None`` when nothing matched. ``raw_text`` is
    the source's literal text, **always** retained (P2). ``reason_kind`` records which form
    it arrived in, and ``signal_strength`` reflects that form. ``mapping_version`` stamps the
    exact mapping used, so a later mapping change never silently reinterprets this reason.
    """

    raw_text: str
    reason_kind: ReasonKind
    mapping_version: str
    code: str | None = None
    signal_strength: SignalStrength = SignalStrength.NONE

    @property
    def matched(self) -> bool:
        """Whether the raw reason mapped to a canonical code."""
        return self.code is not None

    def to_row(self) -> dict[str, Any]:
        """The normalized-reason fields recorded on the claim (SIG-PARSE-005/006)."""
        return {
            "reason_code": self.code,
            "reason_raw_value": self.raw_text,
            "reason_kind": self.reason_kind.value,
            "reason_signal_strength": self.signal_strength.value,
            "reason_mapping_version": self.mapping_version,
        }


def _fold_free_text(text: str) -> str:
    """Casefold, strip surrounding punctuation, and collapse internal whitespace."""
    folded = re.sub(r"\s+", " ", text.casefold()).strip()
    return folded.strip(".,;:!?/-()[]{}\"' ")


def _fold_dropdown(text: str) -> str:
    """Dropdown labels are constrained: fold case and whitespace, keep them otherwise exact."""
    return re.sub(r"\s+", " ", text.casefold()).strip()


class ReasonMapping:
    """A loaded reason-code mapping: forward normalization and reverse inspection.

    Built from the versioned ``reason_codes.toml`` table. It exposes forward normalization
    (:meth:`normalize`) and the reverse view every reviewer needs (:meth:`raw_variants`,
    :meth:`codes`). Construct via :func:`load_reason_mapping`; the constructor also accepts
    an explicit table so a test can pin a fixture mapping and a migration can hold two
    versions side by side.
    """

    def __init__(self, table: dict[str, Any]) -> None:
        self._version = str(table["version"])
        # Per kind: canonical code -> raw variants (reverse view), and folded variant ->
        # code (forward index). Both are derived from the same data, so they cannot drift.
        self._variants: dict[ReasonKind, dict[str, tuple[str, ...]]] = {}
        self._index: dict[ReasonKind, dict[str, str]] = {}
        for kind, section, fold in (
            (ReasonKind.FREE_TEXT, "free_text", _fold_free_text),
            (ReasonKind.CONSTRAINED_DROPDOWN, "dropdown", _fold_dropdown),
        ):
            variants: dict[str, tuple[str, ...]] = {}
            index: dict[str, str] = {}
            for code, raw_variants in table.get(section, {}).items():
                variants[code] = tuple(raw_variants)
                for raw in raw_variants:
                    folded = fold(raw)
                    if folded in index and index[folded] != code:
                        raise ValueError(
                            f"reason mapping is ambiguous: {raw!r} ({section}) maps to both "
                            f"{index[folded]!r} and {code!r}"
                        )
                    index[folded] = code
            self._variants[kind] = variants
            self._index[kind] = index

    @property
    def version(self) -> str:
        """The mapping version stamped on every normalized reason (SIG-PARSE-005)."""
        return self._version

    def codes(self, kind: ReasonKind | None = None) -> tuple[str, ...]:
        """The canonical reason codes, optionally for one form (sorted, for inspection)."""
        if kind is not None:
            return tuple(sorted(self._variants[kind]))
        both = set(self._variants[ReasonKind.FREE_TEXT]) | set(
            self._variants[ReasonKind.CONSTRAINED_DROPDOWN]
        )
        return tuple(sorted(both))

    def raw_variants(self, code: str, kind: ReasonKind) -> tuple[str, ...]:
        """The raw variants that map to ``code`` for ``kind`` — the reversible view."""
        return self._variants[kind].get(code, ())

    def normalize(self, raw_text: str, kind: ReasonKind) -> NormalizedReason:
        """Normalize one reason field, retaining the raw text (SIG-PARSE-005/006, P2).

        Matches ``raw_text`` against the mapping for its ``kind`` and returns a
        :class:`NormalizedReason` stamped with this mapping's version. An unmatched reason
        still returns a result — ``code=None``, ``signal_strength=NONE`` — with the raw text
        retained, because a reason SIG could not categorize is data about the source, not an
        error to drop.
        """
        folded = (_fold_dropdown if kind is ReasonKind.CONSTRAINED_DROPDOWN else _fold_free_text)(
            raw_text
        )
        code = self._index[kind].get(folded)
        if code is None:
            strength = SignalStrength.NONE
        elif kind is ReasonKind.CONSTRAINED_DROPDOWN:
            strength = SignalStrength.STRONG
        else:
            strength = SignalStrength.MODERATE
        return NormalizedReason(
            raw_text=raw_text,
            reason_kind=kind,
            mapping_version=self._version,
            code=code,
            signal_strength=strength,
        )


@cache
def _table() -> dict[str, Any]:
    resource = files("parsing").joinpath("data", "reason_codes.toml")
    with resource.open("rb") as fh:
        return tomllib.load(fh)


@cache
def load_reason_mapping() -> ReasonMapping:
    """The reason-code mapping from the versioned data table (SIG-PARSE-005)."""
    return ReasonMapping(_table())


def normalize_reason(
    raw_text: str, kind: ReasonKind, *, mapping: ReasonMapping | None = None
) -> NormalizedReason:
    """Normalize one reason field through the shipped (or a supplied) mapping.

    A convenience over :meth:`ReasonMapping.normalize` that defaults to the shipped mapping;
    pass ``mapping`` to normalize under a specific version (e.g. during a migration).
    """
    return (mapping or load_reason_mapping()).normalize(raw_text, kind)
