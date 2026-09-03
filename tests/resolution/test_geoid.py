# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""GEOIDs are fixed-width strings with an explicit level (SIG-IDENT-005)."""

from __future__ import annotations

import pytest
from resolution.geoid import (
    GeoidValidationError,
    geoid_levels_for_width,
    validate_geoid,
)


@pytest.mark.parametrize(
    ("code", "level"),
    [
        ("06", "state"),
        ("06075", "county"),
        ("0667000", "place"),
        ("06075", "cbsa"),
        ("06075010100", "census_tract"),
    ],
)
def test_valid_fixed_width_geoids_pass(code: str, level: str) -> None:
    assert validate_geoid(code, level) == code


def test_seven_char_geoid_is_ambiguous_without_a_level() -> None:
    # The crux of SIG-IDENT-005: width 7 is shared by four levels, so the value
    # alone cannot name the level — it must be supplied.
    ambiguous = geoid_levels_for_width(7)
    assert ambiguous == {
        "place",
        "elementary_school_district",
        "secondary_school_district",
        "unified_school_district",
    }
    # The very same string validates as either a place or a school district; only
    # the level disambiguates.
    assert validate_geoid("0667000", "place") == "0667000"
    assert validate_geoid("0667000", "unified_school_district") == "0667000"


def test_missing_level_is_rejected() -> None:
    with pytest.raises(GeoidValidationError, match="explicit level"):
        validate_geoid("0667000", "")


def test_unknown_level_is_rejected() -> None:
    with pytest.raises(GeoidValidationError, match="unknown GEOID level"):
        validate_geoid("06", "galaxy")


def test_wrong_width_for_level_is_rejected() -> None:
    # A state GEOID is two chars; a county is five. Feeding one as the other fails.
    with pytest.raises(GeoidValidationError, match="fixed-width"):
        validate_geoid("06", "county")


def test_non_digit_geoid_is_rejected() -> None:
    with pytest.raises(GeoidValidationError, match="all digits"):
        validate_geoid("CA075", "county")


def test_leading_zero_is_preserved_as_a_string() -> None:
    # "06" (California) must survive; an int 6 would have dropped the leading zero.
    assert validate_geoid("06", "state") == "06"
    assert validate_geoid("06", "state").startswith("0")
