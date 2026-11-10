# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The deterministic renewal-clause reader (P37.31 / K7 WX-02, P07.1 layer 3).

A captured contract document's renewal clause carries the three values the
decision-calendar watch needs and the spine never modelled (K7 §2 NEW-2):
``auto_renews``, ``notice_window_days`` and ``renewal_term_months``. This module
reads them the way the layer-3 clause locator reads policy facts — a deterministic
regexp pass over the captured text against the **reviewed, versioned** pattern set
(``data/renewal_clauses.toml``, §20), returning each value with the verbatim
literal slice it was read from so the claim's ``raw_value`` and locator are
defensible (SIG-PARSE-003/004).

Honesty rules it encodes:

* **a value the document does not state is absent, never inferred** — no
  renewal clause, no claims (§3.1);
* **every value is a verbatim slice** — ``literal``/``start``/``end`` locate the
  clause text the value was read from; the typed value is only ever what the
  literal itself states (a year-stated term converts at exactly 12 months, a
  month-stated notice window stays unstated — months are not days);
* **affirmative and negative signals both record** — a document whose clauses
  genuinely disagree emits both; the spine keeps the disagreement visible,
  never silently reconciled;
* **deterministic** — the same capture text reads to the same terms every time
  (SIG-PARSE-007); a pattern change is a new ``version`` in the TOML, and a bulk
  re-read rides new claims (SIG-STORE-038), never a rewrite.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from typing import Any

__all__ = [
    "RENEWAL_CLAUSES_VERSION",
    "RenewalTerm",
    "extract_renewal_terms",
    "renewal_clause_rules",
]

#: The emitted predicate ids — the Contract renewal triple (K7 WX-02).
RENEWAL_PREDICATES: tuple[str, ...] = (
    "auto_renews",
    "notice_window_days",
    "renewal_term_months",
)

_MONTHS_PER_YEAR = 12


@cache
def _data() -> dict[str, Any]:
    resource = files("parsing").joinpath("data", "renewal_clauses.toml")
    with resource.open("rb") as fh:
        return tomllib.load(fh)


RENEWAL_CLAUSES_VERSION: str = str(_data()["version"])


def _number_words() -> dict[str, int]:
    return {str(k): int(v) for k, v in _data()["number_words"].items()}


def _number_alternation() -> str:
    """The ``NUMBER`` token a TOML pattern embeds: a digit run or a reviewed
    number word (single-token or ``<tens> <units>`` / ``<units>-<units>``)."""
    words = sorted(_number_words(), key=len, reverse=True)
    word_re = "|".join(re.escape(w) for w in words)
    return rf"(?:\d+|(?:{word_re})(?:[-\s](?:{word_re}))?)"


def _parse_number(text: str) -> int | None:
    """Parse a captured ``NUMBER`` — digits, a number word, or a two-word phrase."""
    token = text.strip().lower().replace("-", " ")
    if token.isdigit():
        return int(token)
    parts = token.split()
    if len(parts) == 1 and parts[0] in _number_words():
        return _number_words()[parts[0]]
    if len(parts) == 2 and all(p in _number_words() for p in parts):
        return _number_words()[parts[0]] + _number_words()[parts[1]]
    return None


def _convert(value: int, *, from_unit: str, to_unit: str) -> int | None:
    """Convert a stated duration to the predicate's unit — exact only, never a guess."""
    if from_unit == to_unit:
        return value
    if from_unit == "years" and to_unit == "months":
        return value * _MONTHS_PER_YEAR
    return None  # e.g. months→days is never a 30-day guess


@dataclass(frozen=True)
class RenewalTerm:
    """One dated-decision value read from a captured contract's renewal clause.

    ``predicate`` is the emitted predicate id; ``value`` is the typed value the
    literal states; ``literal``/``start``/``end`` are the verbatim slice of the
    captured text the value was read from (the claim's ``raw_value`` +
    ``byte_range`` locator); ``rule_id`` names the reviewed pattern that fired.
    """

    predicate: str
    value: bool | int
    literal: str
    start: int
    end: int
    rule_id: str


@cache
def renewal_clause_rules() -> tuple[tuple[str, str, str, str, re.Pattern[str]], ...]:
    """The compiled reviewed rules — ``(rule_id, predicate, value_spec, unit, pattern)``.

    ``value_spec`` is a literal value (``"true"``/``"false"``) or ``"capture"`` —
    the latter reads the pattern's first capture group as the stated number.
    """
    out: list[tuple[str, str, str, str, re.Pattern[str]]] = []
    for rule in _data()["rule"]:
        for pattern in rule["patterns"]:
            compiled = re.compile(pattern.replace("NUMBER", _number_alternation()), re.IGNORECASE)
            out.append(
                (
                    str(rule["id"]),
                    str(rule["predicate"]),
                    str(rule["value"]),
                    str(rule["unit"]),
                    compiled,
                )
            )
    return tuple(out)


_TARGET_UNIT = {"notice_window_days": "days", "renewal_term_months": "months"}


def extract_renewal_terms(text: str) -> list[RenewalTerm]:
    """Read the dated-decision renewal values a captured contract text states.

    Deterministic: every reviewed rule fires at every match; a value whose
    capture cannot be parsed or converted exactly is dropped (the literal never
    becomes a guessed number); identical ``(predicate, value, literal)`` matches
    from overlapping patterns emit once, in text order.
    """
    out: list[RenewalTerm] = []
    seen: set[tuple[str, str, str]] = set()
    for rule_id, predicate, value_spec, unit, pattern in renewal_clause_rules():
        for match in pattern.finditer(text):
            if value_spec == "capture":
                if match.lastindex is None or not match.lastindex:
                    continue  # the reviewed pattern must carry the number group
                number = _parse_number(match.group(1))
                if number is None:
                    continue  # an unreadable number word stands unread (§3.1)
                converted = _convert(
                    number, from_unit=unit, to_unit=_TARGET_UNIT.get(predicate, unit)
                )
                if converted is None:
                    continue
                value: bool | int = converted
            else:
                value = value_spec.strip().lower() == "true"
            literal = match.group(0)
            key = (predicate, str(value), literal.lower())
            if key in seen:
                continue
            seen.add(key)
            out.append(
                RenewalTerm(
                    predicate=predicate,
                    value=value,
                    literal=literal,
                    start=match.start(),
                    end=match.end(),
                    rule_id=rule_id,
                )
            )
    out.sort(key=lambda t: (t.start, t.predicate))
    return out
