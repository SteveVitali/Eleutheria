# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Freshness relative to predicate volatility, not absolute days (§32.4).

AC4: freshness is computed relative to predicate volatility. The canonical example
(SIG-METRIC-006): a two-year-old contract *signing date* is fresh (IMMUTABLE); a
two-year-old *active device count* is historical (FAST, six-month half-life).
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from inference.freshness import (
    is_stale_for_predicate,
    predicate_currency,
    source_freshness,
)

# Two real registry predicates with opposite volatility (ontology/vocab/predicates.yaml):
_IMMUTABLE = "contract_signed_date"  # IMMUTABLE, half-life infinite
_FAST = "active_device_count"  # FAST, half-life 6mo

_OBSERVED = date(2024, 1, 1)
_TWO_YEARS_LATER = date(2026, 1, 1)


def test_same_age_yields_different_currency_by_volatility() -> None:
    """AC4: identical age, opposite freshness — because volatility differs."""
    immutable = predicate_currency(_IMMUTABLE, observed_at=_OBSERVED, as_of=_TWO_YEARS_LATER)
    fast = predicate_currency(_FAST, observed_at=_OBSERVED, as_of=_TWO_YEARS_LATER)
    assert immutable == "C1"  # a two-year-old contract date is CURRENT
    assert fast == "C4"  # a two-year-old active count is HISTORICAL
    assert immutable != fast  # freshness is not a flat age threshold


def test_immutable_is_never_stale_however_old() -> None:
    assert not is_stale_for_predicate(
        _IMMUTABLE, observed_at=date(2000, 1, 1), as_of=_TWO_YEARS_LATER
    )


def test_fast_predicate_goes_stale_past_its_window() -> None:
    assert is_stale_for_predicate(_FAST, observed_at=_OBSERVED, as_of=_TWO_YEARS_LATER)
    # Freshly observed FAST evidence is not stale.
    assert not is_stale_for_predicate(_FAST, observed_at=date(2025, 12, 20), as_of=_TWO_YEARS_LATER)


def test_source_freshness_surface_counts_stale_by_predicate_class() -> None:
    """SIG-METRIC-007: stale_count is per predicate class, not a flat age."""
    surface = source_freshness(
        "source:flock-portal",
        status="ok",
        last_successful_run=datetime(2026, 1, 1, tzinfo=UTC),
        last_content_change=datetime(2025, 12, 1, tzinfo=UTC),
        observations=[
            (_IMMUTABLE, date(2019, 1, 1)),  # ancient but IMMUTABLE -> fresh
            (_FAST, date(2024, 1, 1)),  # two years old FAST -> stale
            (_FAST, date(2025, 12, 20)),  # recent FAST -> fresh
        ],
        as_of=_TWO_YEARS_LATER,
    )
    assert surface.tracked_count == 3
    assert surface.stale_count == 1  # only the old FAST observation
    assert surface.status == "ok"
    assert surface.as_json()["stale_count"] == 1
    assert surface.as_json()["last_successful_run"] == "2026-01-01T00:00:00+00:00"
