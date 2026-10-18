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
        # P35.20b (ED-43): staleness evaluates only under a DECLARED class —
        # the caller names the source's registered §28.3 class, never a guess.
        declared_volatility_class="FAST",
    )
    assert surface.tracked_count == 3
    assert surface.stale_count == 1  # only the old FAST observation
    assert surface.status == "ok"
    assert surface.staleness_evaluable is True
    assert surface.as_json()["stale_count"] == 1
    assert surface.as_json()["last_successful_run"] == "2026-01-01T00:00:00+00:00"


def test_undeclared_source_is_not_evaluable_never_stale_zero() -> None:
    """P35.20b (ED-43, GQ-15): no declared class → not evaluable, even with
    observations that *would* measure stale — a fabricated stale-0 would claim
    an evaluation that never ran."""
    surface = source_freshness(
        "source:council-minutes",
        status="ok",
        last_successful_run=datetime(2026, 1, 1, tzinfo=UTC),
        last_content_change=None,
        observations=[
            (_FAST, date(2024, 1, 1)),  # old FAST — would be stale if evaluable
            (_FAST, date(2025, 12, 20)),
        ],
        as_of=_TWO_YEARS_LATER,
        declared_volatility_class=None,
        not_evaluable_count=2,
    )
    assert surface.staleness_evaluable is False
    assert surface.stale_count == 0  # never a fabricated figure — and the
    assert surface.not_evaluable_count == 2  # row discloses what went unmeasured
    assert surface.as_json()["staleness_evaluable"] is False


def test_declared_class_with_no_evaluable_observations_is_not_evaluable() -> None:
    """P35.20b: a declared class but zero dated observations → staleness was
    never evaluated; the row cannot claim 'ok'."""
    surface = source_freshness(
        "source:empty-feed",
        status="degraded",
        last_successful_run=None,
        last_content_change=None,
        observations=[],
        as_of=_TWO_YEARS_LATER,
        declared_volatility_class="MODERATE",
    )
    assert surface.staleness_evaluable is False


def test_non_evaluable_surface_refuses_a_nonzero_stale_count() -> None:
    """A non-evaluable staleness carrying a stale figure is self-contradictory."""
    import pytest

    with pytest.raises(ValueError, match="never faked"):
        from inference.freshness import SourceFreshness

        SourceFreshness(
            source_id="source:x",
            last_successful_run=None,
            last_content_change=None,
            status="ok",
            stale_count=1,
            tracked_count=1,
            staleness_evaluable=False,
        )
