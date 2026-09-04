# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The composed epistemic weight ``W`` (§10.6, SIG-EPIS-021) and derived currency
``C`` (§28.3, SIG-RECON-008).

This is the minimal, spec-faithful implementation the P06.1 vertical slice needs
to reconcile competing quantity claims; the full reconciliation engine is P08,
which supersedes and extends it (see ADR-031). The composition is a **published
ordinal table**, never arithmetic on invented numbers (SIG-EPIS-021):

    base:        R1->W4  R2->W3  R3->W3  R4->W2  R5->W2  R6->W1
    directness:  D1 0  D2 0  D3 -1  D4 -2  D5 -2 (floor W1)  D6 EXCLUDE
    integrity:   I1 0  I2 -1  I3 -2
    currency:    C1 0  C2 -1  C3 -2  C4 -2 (floor W1)
    upgrade (at most +1 total, never above W4):
      +1  machine-readable structured export AND extraction confidence EXACT
      +1  independently field-verified by a SIG curator with a logged event
    W = clamp(W0..W4)

``C`` is **not stored** on a claim (SIG-EPIS-020); it is recomputed at query time
from the predicate's volatility half-life and the claim's ``observed_at``.
"""

from __future__ import annotations

import json
import math
from datetime import date, datetime
from functools import cache
from typing import Any

# --- §10.6 ordinal composition table -----------------------------------------

#: Base weight from source reliability R (§10.4, §10.6).
BASE_WEIGHT: dict[str, int] = {"R1": 4, "R2": 3, "R3": 3, "R4": 2, "R5": 2, "R6": 1}

#: Directness downgrade (§10.5, §10.6). ``D6`` is EXCLUDE, handled separately.
DIRECTNESS_DELTA: dict[str, int] = {"D1": 0, "D2": 0, "D3": -1, "D4": -2, "D5": -2}

#: Integrity downgrade (§10.6).
INTEGRITY_DELTA: dict[str, int] = {"I1": 0, "I2": -1, "I3": -2}

#: Currency downgrade (§10.6).
CURRENCY_DELTA: dict[str, int] = {"C1": 0, "C2": -1, "C3": -2, "C4": -2}

#: Directness code that excludes a claim from the admissible set entirely (§10.5).
EXCLUDED_DIRECTNESS = "D6"

#: The lowest and highest weight classes; W0 is retained for display, never resolves.
W_MIN, W_MAX = 0, 4

#: D5 and C4 downgrade "to a floor of W1" — they never push a claim to W0 (§10.6).
_FLOOR_TRIGGERS_D = {"D5"}
_FLOOR_TRIGGERS_C = {"C4"}


class DirectnessExcluded(ValueError):
    """Raised when a claim's directness is ``D6`` — non-probative, not admissible."""


def weight_class(
    *,
    reliability: str,
    directness: str,
    integrity: str,
    currency: str,
    structured_exact: bool = False,
    field_verified: bool = False,
) -> int:
    """Compose the weight class ``W`` (0..4) from the four axes (§10.6).

    Raises :class:`DirectnessExcluded` for ``D6`` (excluded from the admissible
    set — the caller must not treat it as W0). The two upgrades sum to at most
    ``+1`` and never lift ``W`` above ``W4``.
    """
    if directness == EXCLUDED_DIRECTNESS:
        raise DirectnessExcluded(
            f"directness {directness!r} is non-probative for this predicate (§10.5)"
        )
    for code, table, name in (
        (reliability, BASE_WEIGHT, "reliability"),
        (directness, DIRECTNESS_DELTA, "directness"),
        (integrity, INTEGRITY_DELTA, "integrity"),
        (currency, CURRENCY_DELTA, "currency"),
    ):
        if code not in table:
            raise ValueError(f"unknown {name} code {code!r} (§10.4-§10.6)")

    raw = (
        BASE_WEIGHT[reliability]
        + DIRECTNESS_DELTA[directness]
        + INTEGRITY_DELTA[integrity]
        + CURRENCY_DELTA[currency]
    )
    # D5 / C4 downgrades floor at W1 (they never reach W0); other downgrades may.
    if directness in _FLOOR_TRIGGERS_D or currency in _FLOOR_TRIGGERS_C:
        raw = max(raw, 1)
    base = _clamp(raw)

    upgrade = 1 if (structured_exact or field_verified) else 0
    return _clamp(base + upgrade)


def _clamp(w: int) -> int:
    return max(W_MIN, min(W_MAX, w))


#: Human labels for the weight classes (§10.6).
WEIGHT_LABEL: dict[int, str] = {
    4: "dispositive",
    3: "strong",
    2: "moderate",
    1: "weak",
    0: "non-probative",
}


# --- §28.3 currency derivation -----------------------------------------------

#: Days per month / year used to turn a half-life string ("6mo", "2y") into days.
_DAYS_PER_MONTH = 30.4375
_DAYS_PER_YEAR = 365.25


def half_life_days(half_life: str) -> float:
    """Parse a predicate registry half-life string to days.

    Accepts ``"infinite"``, ``"<n>mo"`` and ``"<n>y"`` (the forms used in
    ``ontology/vocab/predicates.yaml``); ``"infinite"`` maps to ``inf``.
    """
    hl = half_life.strip().lower()
    if hl in {"infinite", "inf"}:
        return math.inf
    if hl.endswith("mo"):
        return float(hl[:-2]) * _DAYS_PER_MONTH
    if hl.endswith("y"):
        return float(hl[:-1]) * _DAYS_PER_YEAR
    raise ValueError(f"unrecognised half-life {half_life!r} (expected 'infinite', '<n>mo', '<n>y')")


def currency(
    *,
    volatility_class: str,
    half_life: str,
    observed_at: date,
    as_of: date,
) -> str:
    """Derive currency ``C`` (C1..C4) at query time (§28.3, SIG-RECON-008).

        age = as_of - observed_at
        C1 CURRENT     age <= 0.5h      C2 AGING       0.5h < age <= 1.0h
        C3 STALE       1.0h < age <= 3.0h                C4 HISTORICAL  age > 3.0h

    IMMUTABLE predicates have an infinite half-life and are ALWAYS ``C1``.
    """
    h = half_life_days(half_life)
    if volatility_class == "IMMUTABLE" or math.isinf(h):
        return "C1"
    age = (_as_date(as_of) - _as_date(observed_at)).days
    if age <= 0.5 * h:
        return "C1"
    if age <= 1.0 * h:
        return "C2"
    if age <= 3.0 * h:
        return "C3"
    return "C4"


def _as_date(value: date) -> date:
    return value.date() if isinstance(value, datetime) else value


# --- predicate registry access -----------------------------------------------


@cache
def predicate_registry() -> dict[str, dict[str, Any]]:
    """Load the generated predicate registry, keyed by ``predicate_id``.

    The registry is the ontology's generated source of truth for volatility,
    half-life, resolution strategy, and the (genre x predicate) directness matrix
    (§13.6, SIG-ONTO-066/067); the reconciler consumes it rather than hard-coding
    epistemics (§28.3, SIG-RECON-009).
    """
    from ontology.generate import generated_dir

    path = generated_dir() / "registry" / "predicate_registry.json"
    data = json.loads(path.read_text())
    return {p["predicate_id"]: p for p in data["predicates"]}


def predicate_meta(predicate_id: str) -> dict[str, Any]:
    """Return the registry row for ``predicate_id`` (raises ``KeyError`` if absent)."""
    return predicate_registry()[predicate_id]


def directness_for(predicate_id: str, genre: str) -> str:
    """The directness ``D`` for a ``(genre x predicate)`` pair (§10.5)."""
    return predicate_meta(predicate_id)["directness"][genre]
