# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Fixed-width Census GEOID validation with an explicit level (SIG-IDENT-005).

GEOIDs MUST be stored as **fixed-width strings** with a length check, and every
jurisdiction row MUST carry an explicit ``level``. A bare GEOID is ambiguous:
``0644000`` is seven characters, and seven-character GEOIDs collide across place,
elementary / secondary / unified school district, and other levels — so the level
is not derivable from the value and MUST be supplied. Storing GEOIDs as integers
(the classic bug) silently drops the leading zeros that carry the state prefix, so
they are strings here, always.

This module owns the deterministic width table and the validator the jurisdiction
registry-ingest calls before it persists any jurisdiction identifier.
"""

from __future__ import annotations

from types import MappingProxyType

# Census hierarchy GEOID widths, in characters (Census Bureau GEOID structure).
# Several distinct levels share width 7 (place / the three school-district levels)
# and width 5 (county / cbsa / zcta) — which is exactly why a bare width cannot
# name a level and the level MUST be carried explicitly (SIG-IDENT-005).
GEOID_WIDTHS: MappingProxyType[str, int] = MappingProxyType(
    {
        "state": 2,
        "congressional_district": 4,
        "county": 5,
        "cbsa": 5,
        "zcta": 5,
        "place": 7,
        "elementary_school_district": 7,
        "secondary_school_district": 7,
        "unified_school_district": 7,
        "county_subdivision": 10,
        "census_tract": 11,
        "block_group": 12,
        "block": 15,
    }
)


class GeoidValidationError(ValueError):
    """A GEOID failed the fixed-width / explicit-level contract (SIG-IDENT-005)."""


def geoid_levels_for_width(width: int) -> frozenset[str]:
    """The Census levels that share a GEOID ``width`` — the ambiguity set.

    Used to justify why the level is required: for width 7 this returns
    ``{place, elementary_school_district, secondary_school_district,
    unified_school_district}`` — four levels one value cannot disambiguate.
    """
    return frozenset(level for level, w in GEOID_WIDTHS.items() if w == width)


def validate_geoid(code: str, level: str) -> str:
    """Validate a Census GEOID against its declared ``level`` (SIG-IDENT-005).

    Returns the GEOID unchanged when it is a fixed-width, all-digit string of the
    exact width the level requires. Raises :class:`GeoidValidationError` otherwise
    — including when ``level`` is missing or unknown, because a GEOID with no level
    cannot be stored at all.
    """
    if not level:
        raise GeoidValidationError(
            "a GEOID MUST carry an explicit level (SIG-IDENT-005): a bare value is "
            f"ambiguous across {sorted(geoid_levels_for_width(len(code)))}"
        )
    if level not in GEOID_WIDTHS:
        raise GeoidValidationError(f"unknown GEOID level {level!r} (SIG-IDENT-005)")
    if not isinstance(code, str):  # a stored int would have dropped leading zeros
        raise GeoidValidationError("a GEOID MUST be a string, not an integer (SIG-IDENT-005)")
    if not code.isascii() or not code.isdigit():
        raise GeoidValidationError(
            f"GEOID {code!r} for level {level!r} MUST be all digits (SIG-IDENT-005)"
        )
    expected = GEOID_WIDTHS[level]
    if len(code) != expected:
        raise GeoidValidationError(
            f"GEOID {code!r} is {len(code)} chars but level {level!r} is fixed-width "
            f"{expected} (SIG-IDENT-005)"
        )
    return code
