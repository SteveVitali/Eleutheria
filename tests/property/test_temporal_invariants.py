# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Property tests over the eight temporal invariants TI-1..TI-8 (§9.6).

AC1: property tests over temporal invariants TI-1..TI-8 pass (SIG-TIME-013). These
exercise the pipeline data-quality checks (`db.invariants`): each invariant holds
on well-formed data and fires on a deliberately-malformed case (SIG-TIME-014).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from db.invariants import (
    ClaimTiming,
    ResolvedInterval,
    check_all,
    check_ti1,
    check_ti2,
    check_ti3,
    check_ti4,
    check_ti5,
    check_ti6,
    check_ti7,
    check_ti8,
)
from hypothesis import given
from hypothesis import strategies as st

_EPOCH = datetime(2000, 1, 1, tzinfo=UTC)


@st.composite
def _instants(draw: st.DrawFn) -> datetime:
    seconds = draw(st.integers(min_value=0, max_value=60 * 60 * 24 * 365 * 60))
    return _EPOCH + timedelta(seconds=seconds)


def _claim(**kw: object) -> ClaimTiming:
    base = {"claim_id": "c", "recorded_at": _EPOCH}
    base.update(kw)
    return ClaimTiming(**base)  # type: ignore[arg-type]


# --- TI-1: valid_from <= valid_to when both exact -----------------------------


@given(a=_instants(), b=_instants())
def test_ti1_holds_and_fires(a: datetime, b: datetime) -> None:
    lo, hi = sorted((a, b))
    ok = _claim(valid_from=lo, valid_to=hi, valid_from_kind="exact", valid_to_kind="exact")
    assert check_ti1(ok) is None
    if lo != hi:
        bad = _claim(valid_from=hi, valid_to=lo, valid_from_kind="exact", valid_to_kind="exact")
        assert check_ti1(bad) is not None
    # Non-exact kinds are exempt (imprecise bounds are legal in any order).
    assert check_ti1(_claim(valid_from=hi, valid_to=lo, valid_from_kind="unknown")) is None


# --- TI-2: recorded_at <= superseded_at when superseded -----------------------


@given(a=_instants(), b=_instants())
def test_ti2_holds_and_fires(a: datetime, b: datetime) -> None:
    lo, hi = sorted((a, b))
    assert check_ti2(_claim(recorded_at=lo, superseded_at=hi)) is None
    assert check_ti2(_claim(recorded_at=lo, superseded_at=None)) is None
    if lo != hi:
        assert check_ti2(_claim(recorded_at=hi, superseded_at=lo)) is not None


# --- TI-3: observed_at <= published_at (± tolerance) --------------------------


@given(a=_instants(), b=_instants())
def test_ti3_holds_and_fires(a: datetime, b: datetime) -> None:
    lo, hi = sorted((a, b))
    assert check_ti3(_claim(observed_at=lo, published_at=hi)) is None
    if hi - lo > timedelta(days=1):
        assert check_ti3(_claim(observed_at=hi, published_at=lo)) is not None
    # Within tolerance is fine even if slightly out of order.
    assert check_ti3(_claim(observed_at=lo + timedelta(hours=1), published_at=lo)) is None


# --- TI-4: published_at <= retrieved_at (± tolerance) -------------------------


@given(a=_instants(), b=_instants())
def test_ti4_holds_and_fires(a: datetime, b: datetime) -> None:
    lo, hi = sorted((a, b))
    assert check_ti4(lo, hi) is None
    if hi - lo > timedelta(days=1):
        assert check_ti4(hi, lo) is not None


# --- TI-5: observed_at not in the future relative to recorded_at --------------


@given(a=_instants(), b=_instants())
def test_ti5_holds_and_fires(a: datetime, b: datetime) -> None:
    lo, hi = sorted((a, b))
    assert check_ti5(_claim(recorded_at=hi, observed_at=lo)) is None
    if lo != hi:
        assert check_ti5(_claim(recorded_at=lo, observed_at=hi)) is not None


# --- TI-6: mutually-exclusive resolved intervals do not overlap ---------------


@given(offset=st.integers(min_value=-500, max_value=500))
def test_ti6_detects_overlap_of_exclusive_predicates(offset: int) -> None:
    a = ResolvedInterval("r1", "subj", "status", _EPOCH, _EPOCH + timedelta(days=100))
    b = ResolvedInterval(
        "r2",
        "subj",
        "status",
        _EPOCH + timedelta(days=offset),
        _EPOCH + timedelta(days=offset + 100),
    )
    violations = check_ti6([a, b], ["status"])
    overlaps = -100 < offset < 100
    assert bool(violations) == overlaps
    # Different subjects never conflict.
    b_other = ResolvedInterval("r3", "other", "status", a.valid_from, a.valid_to)
    assert check_ti6([a, b_other], ["status"]) == []


# --- TI-7: supersedes chain acyclic and terminating ---------------------------


def test_ti7_accepts_a_terminating_chain_and_rejects_a_cycle() -> None:
    chain = [
        _claim(claim_id="c3", supersedes_claim_id="c2"),
        _claim(claim_id="c2", supersedes_claim_id="c1"),
        _claim(claim_id="c1"),
    ]
    assert check_ti7(chain) == []
    cycle = [
        _claim(claim_id="a", supersedes_claim_id="b"),
        _claim(claim_id="b", supersedes_claim_id="a"),
    ]
    assert check_ti7(cycle)


# --- TI-8: every claim is anchored in time ------------------------------------


def test_ti8_requires_an_anchor() -> None:
    assert check_ti8(_claim(observed_at=_EPOCH)) is None
    assert check_ti8(_claim(published_at=_EPOCH)) is None
    assert (
        check_ti8(
            _claim(temporally_unanchored=True, temporally_unanchored_reason="atemporal event")
        )
        is None
    )
    # No anchor and no reasoned flag = data-quality failure.
    assert check_ti8(_claim()) is not None
    # The flag without a reason does not satisfy TI-8.
    assert check_ti8(_claim(temporally_unanchored=True)) is not None


# --- the batch gate -----------------------------------------------------------


def test_check_all_fails_the_run_on_any_violation() -> None:
    good = _claim(claim_id="ok", observed_at=_EPOCH)
    bad = _claim(claim_id="floating")  # violates TI-8
    report = check_all([good, bad])
    assert not report.ok
    assert any(v.invariant == "TI-8" for v in report.violations)
    try:
        report.raise_if_failed()
    except Exception as exc:  # noqa: BLE001 - asserting the failure surfaces
        assert "TI-8" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected raise_if_failed to raise")
    assert check_all([good]).ok
