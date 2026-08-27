# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""ORI validation by pattern, the UCR↔USPS table, and the civil-ORI flag
(SIG-IDENT-002/003)."""

from __future__ import annotations

import pytest
from resolution.ori import (
    OriValidationError,
    is_civil_ori,
    is_valid_ori,
    ucr_to_usps,
    ucr_usps_divergences,
    usps_to_ucr,
    validate_ori,
)

# --- SIG-IDENT-002: validated by pattern, never by positional state ----------


def test_valid_ori_is_nine_alnum() -> None:
    assert validate_ori("TX0570000") == "TX0570000"
    assert is_valid_ori("CA0194200")
    # An "impossible" USPS prefix is still a valid ORI — validity is pattern-only,
    # so a positional state assumption never rejects a well-formed ORI.
    assert is_valid_ori("ZZ1234567")


@pytest.mark.parametrize("bad", ["TX057000", "TX05700000", "tx0570000", "TX05700 0", "TX-570000"])
def test_malformed_ori_is_rejected(bad: str) -> None:
    assert not is_valid_ori(bad)
    with pytest.raises(OriValidationError):
        validate_ori(bad)


def test_validation_does_not_consult_the_state_prefix() -> None:
    # A right-shaped token with a nonsense prefix passes; a wrong-shaped token with
    # a real state prefix fails. Validity depends on shape, not the prefix.
    assert is_valid_ori("QX0000001")
    assert not is_valid_ori("CA057")


# --- SIG-IDENT-002: the UCR↔USPS table exists incl NB→NE, GM→GU --------------


def test_ucr_usps_divergences_include_the_mandated_pairs() -> None:
    div = ucr_usps_divergences()
    assert div["NB"] == "NE"  # Nebraska
    assert div["GM"] == "GU"  # Guam


def test_ucr_to_usps_translates_divergent_and_passes_through_identical() -> None:
    assert ucr_to_usps("NB") == "NE"
    assert ucr_to_usps("GM") == "GU"
    assert ucr_to_usps("CA") == "CA"  # UCR and USPS agree for most states
    assert ucr_to_usps("tx") == "TX"  # case-insensitive


def test_usps_to_ucr_is_the_inverse() -> None:
    assert usps_to_ucr("NE") == "NB"
    assert usps_to_ucr("GU") == "GM"
    assert usps_to_ucr("CA") == "CA"


# --- SIG-IDENT-003: the civil/applicant ORI flag -----------------------------


def test_alphabetic_ninth_char_is_flagged_civil() -> None:
    # A trailing letter marks a probable civil/applicant ORI (SIG-IDENT-003).
    assert is_civil_ori("MA013013Y") is True
    assert is_civil_ori("CA01942AA") is True


def test_numeric_ninth_char_is_not_civil() -> None:
    assert is_civil_ori("TX0570000") is False
    assert is_civil_ori("CA0194200") is False


def test_civil_flag_requires_a_valid_ori() -> None:
    with pytest.raises(OriValidationError):
        is_civil_ori("not-an-ori")
