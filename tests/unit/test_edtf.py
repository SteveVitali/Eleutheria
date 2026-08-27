# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""EDTF Level 1 encoding + the deterministic envelope (§16.7, SIG-STORE-021/022).

AC3: EDTF round-trips and the derived envelope is deterministic; "early 2025"
does NOT become 2025-01-01.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from db.edtf import (
    ENVELOPE_RULESET_VERSION,
    EdtfError,
    canonical,
    derive_envelope,
    infer_kinds,
)


def _utc(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d, tzinfo=UTC)


# The normative §16.7 table: (source EDTF, lower, upper, (from_kind, to_kind)).
SPEC_TABLE = [
    ("2025-03-14", _utc(2025, 3, 14), _utc(2025, 3, 15), ("exact", "exact")),
    ("2019", _utc(2019, 1, 1), _utc(2020, 1, 1), ("exact", "exact")),
    ("2025-03~", _utc(2025, 1, 1), _utc(2025, 6, 1), ("approximate", "approximate")),
    ("../2025-06-10", None, _utc(2025, 6, 11), ("unknown", "before")),
    ("2026-07-14/..", _utc(2026, 7, 14), None, ("exact", "ongoing")),
    ("..", None, None, ("unknown", "unknown")),
]


@pytest.mark.parametrize("edtf,lower,upper,kinds", SPEC_TABLE)
def test_spec_16_7_table_envelopes(
    edtf: str, lower: datetime | None, upper: datetime | None, kinds: tuple[str, str]
) -> None:
    env = derive_envelope(edtf)
    assert env.lower == lower
    assert env.upper == upper
    assert infer_kinds(edtf) == kinds


def test_early_2025_is_not_sharpened_to_jan_1() -> None:
    """SIG-STORE-022: 'in early 2025' (2025-03~) MUST NOT become 2025-01-01 exact."""
    env = derive_envelope("2025-03~")
    # It spans a real window (H1 2025), it is not the single instant 2025-01-01.
    assert env.lower == _utc(2025, 1, 1)
    assert env.upper == _utc(2025, 6, 1)
    assert env.lower != env.upper  # not a false-precise point
    # And the year-only exact form is a different, sharper envelope.
    assert derive_envelope("2025-03~") != derive_envelope("2025-01-01")


def test_envelope_is_deterministic() -> None:
    for edtf, *_ in SPEC_TABLE:
        first = derive_envelope(edtf)
        for _ in range(5):
            assert derive_envelope(edtf) == first


@pytest.mark.parametrize(
    "edtf",
    [
        "2025-03-14",
        "2019",
        "2025-03~",
        "2025-03?",
        "2025-03%",
        "../2025-06-10",
        "2026-07-14/..",
        "..",
        "2019/2020",
        "2019-03/2019-05",
        "201X",
        "19XX",
        "2019-22",  # summer season
        "/2020-06",  # unknown start
        "2020-06/",  # unknown end
    ],
)
def test_round_trip_canonical(edtf: str) -> None:
    once = canonical(edtf)
    assert canonical(once) == once  # canonical is idempotent (a stable round-trip)


def test_infer_kinds_for_closed_intervals_and_open_ends() -> None:
    # A closed interval reports each known bound's natural kind, not "before".
    assert infer_kinds("2019/2020") == ("exact", "exact")
    assert infer_kinds("2019~/2020") == ("approximate", "exact")
    # Open/unknown ends follow the §16.7 semantics.
    assert infer_kinds("2019/..") == ("exact", "ongoing")
    assert infer_kinds("2019/") == ("exact", "unknown")
    # Unknown start + known end reads as bounded-above-only ("before").
    assert infer_kinds("/2020") == ("unknown", "before")


def test_seasons_widen_to_the_season_window() -> None:
    # 2019-22 = summer 2019 = Jun-Aug.
    env = derive_envelope("2019-22")
    assert env.lower == _utc(2019, 6, 1)
    assert env.upper == _utc(2019, 9, 1)


def test_masked_year_expands_to_the_decade() -> None:
    env = derive_envelope("201X")
    assert env.lower == _utc(2010, 1, 1)
    assert env.upper == _utc(2020, 1, 1)


def test_uncertain_does_not_widen_but_approximate_does() -> None:
    # `?` is a flag on the value, not a nearby-ness claim: same window as exact.
    assert derive_envelope("2025-03?") == derive_envelope("2025-03")
    # `~` widens; `%` (both) widens like `~`.
    assert derive_envelope("2025-03~") == derive_envelope("2025-03%")
    assert derive_envelope("2025-03~") != derive_envelope("2025-03")


def test_tstzrange_literal_uses_null_for_infinity() -> None:
    assert "NULL" in derive_envelope("2026-07-14/..").to_tstzrange_literal()
    assert derive_envelope("2019").to_tstzrange_literal().startswith("tstzrange('2019-01-01")


def test_unknown_ruleset_is_refused() -> None:
    with pytest.raises(EdtfError):
        derive_envelope("2019", ruleset_version="something-else")


def test_ruleset_version_is_pinned() -> None:
    assert ENVELOPE_RULESET_VERSION == "edtf-envelope-1"


@pytest.mark.parametrize(
    "bad",
    ["", "   ", "2019-13", "2019-00", "2019-02-30", "not-a-date", "2019-1", "20", "/", "2019-15"],
)
def test_invalid_edtf_is_rejected(bad: str) -> None:
    with pytest.raises(EdtfError):
        derive_envelope(bad)
