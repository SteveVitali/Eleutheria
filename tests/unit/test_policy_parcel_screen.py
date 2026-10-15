# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.66 — the declared residential-parcel screen (SIG-PUB-004/005/013).

Exercises the *declared signal* machinery over the committed synthetic fixture
layer (``tests/unit/fixtures/parcels/residential_parcels.toml`` — a stand-in,
not real geography): the three-valued verdict (``intersects`` | ``clear`` |
``unscreened``), the fail-closed integrity checks, and the publish-path
refusal (:func:`policy.sensitivity.assert_public_layer_subject` /
``CandidateAssetPublishRefused``).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from policy.parcel_screen import (
    PARCEL_SCREEN_VERDICTS,
    ParcelScreenVerdict,
    ParcelSignalError,
    ResidentialParcelSignal,
    declared_parcel_signal,
    parcel_fields,
    screen_geometry_descriptor,
    screen_point,
    signal_doc_violations,
)
from policy.sensitivity import (
    CandidateAssetPublishRefused,
    assert_public_layer_subject,
)

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "parcels" / "residential_parcels.toml"

#: Verdict-pinning points against the synthetic fixture geography.
ON_PARCEL = (35.46, -97.52)  # (lat, lon) inside parcel-1
IN_COVERAGE_OFF_PARCEL = (35.50, -97.40)  # inside coverage, outside every parcel
OUTSIDE_COVERAGE = (36.00, -98.00)  # beyond every coverage region


@pytest.fixture(scope="module")
def signal() -> ResidentialParcelSignal:
    return ResidentialParcelSignal.load(_FIXTURE)


# --- the declared signal ------------------------------------------------------


def test_fixture_signal_loads_and_stamps(signal: ResidentialParcelSignal) -> None:
    assert signal.signal_id == "sig.residential_parcels.fixture"
    assert signal.version == "fixture-v1"
    assert signal.stamp == "sig.residential_parcels.fixture@fixture-v1"
    assert len(signal.coverage) == 1
    assert len(signal.parcels) == 1


def test_committed_signal_loads_with_empty_coverage() -> None:
    """The committed declared signal is honest: no geography held yet, so every
    point screens ``unscreened`` — a recorded coverage gap, never a fabricated
    ``clear``."""
    sig = declared_parcel_signal()
    assert sig.signal_id and sig.version and sig.provenance
    assert sig.coverage == () and sig.parcels == ()
    assert screen_point(*ON_PARCEL) is ParcelScreenVerdict.UNSCREENED
    # Even the fixture parcel's centre is unscreened against the committed
    # signal — empty coverage is the recorded boundary.
    assert screen_point(*IN_COVERAGE_OFF_PARCEL) is ParcelScreenVerdict.UNSCREENED


# --- the three-valued verdict -------------------------------------------------


def test_screen_point_verdicts(signal: ResidentialParcelSignal) -> None:
    assert screen_point(*ON_PARCEL, signal=signal) is ParcelScreenVerdict.INTERSECTS
    assert screen_point(*IN_COVERAGE_OFF_PARCEL, signal=signal) is ParcelScreenVerdict.CLEAR
    assert screen_point(*OUTSIDE_COVERAGE, signal=signal) is ParcelScreenVerdict.UNSCREENED


def test_screen_geometry_descriptor(signal: ResidentialParcelSignal) -> None:
    """``point``/``center`` descriptors screen on their coordinate; ``bounds``
    and absent/malformed geometry record ``unscreened`` — never a clearance a
    point-in-parcel check could not have produced."""
    assert (
        screen_geometry_descriptor(
            {"kind": "point", "lat": ON_PARCEL[0], "lon": ON_PARCEL[1]}, signal=signal
        )
        is ParcelScreenVerdict.INTERSECTS
    )
    assert (
        screen_geometry_descriptor(
            {"kind": "center", "lat": IN_COVERAGE_OFF_PARCEL[0], "lon": IN_COVERAGE_OFF_PARCEL[1]},
            signal=signal,
        )
        is ParcelScreenVerdict.CLEAR
    )
    assert (
        screen_geometry_descriptor(
            {"kind": "bounds", "bounds": {"minlat": 35.45, "maxlat": 35.47}},
            signal=signal,
        )
        is ParcelScreenVerdict.UNSCREENED
    )
    assert screen_geometry_descriptor(None, signal=signal) is ParcelScreenVerdict.UNSCREENED
    assert (
        screen_geometry_descriptor({"kind": "point", "lat": "x"}, signal=signal)
        is ParcelScreenVerdict.UNSCREENED
    )


def test_verdict_vocabulary_is_closed() -> None:
    assert PARCEL_SCREEN_VERDICTS == {"intersects", "clear", "unscreened"}


def test_parcel_fields_stamp(signal: ResidentialParcelSignal) -> None:
    flagged = parcel_fields(ParcelScreenVerdict.INTERSECTS, signal=signal)
    assert flagged == {
        "residential_parcel_flag": True,
        "parcel_screen": "intersects",
        "parcel_screen_signal": signal.stamp,
    }
    clear = parcel_fields(ParcelScreenVerdict.CLEAR, signal=signal)
    assert clear["residential_parcel_flag"] is False
    assert clear["parcel_screen"] == "clear"
    # ``unscreened`` is a distinct recorded state — flag stays false but the
    # verdict is never ``clear``.
    unscreened = parcel_fields(ParcelScreenVerdict.UNSCREENED, signal=signal)
    assert unscreened["parcel_screen"] == "unscreened"


# --- integrity: a malformed signal is a config defect, never a verdict --------


def test_signal_doc_violations_missing_keys() -> None:
    problems = signal_doc_violations({})
    assert any("signal_id" in p for p in problems)
    assert any("version" in p for p in problems)
    assert any("provenance" in p for p in problems)


def test_signal_doc_violations_open_ring() -> None:
    problems = signal_doc_violations(
        {
            "signal_id": "s",
            "version": "v",
            "provenance": "p",
            "coverage": [[[0, 0], [1, 0], [1, 1], [0, 1]]],  # never closes
        }
    )
    assert any("not closed" in p for p in problems)


def test_signal_doc_violations_out_of_range_position() -> None:
    problems = signal_doc_violations(
        {
            "signal_id": "s",
            "version": "v",
            "provenance": "p",
            "coverage": [[[0, 0], [200, 0], [200, 95], [0, 0]]],
        }
    )
    assert any("in-range" in p for p in problems)


def test_signal_doc_violations_parcel_outside_coverage() -> None:
    """A parcel whose centroid sits outside every declared coverage region is
    a contradiction — the signal claims a parcel in geography it does not
    cover."""
    problems = signal_doc_violations(
        {
            "signal_id": "s",
            "version": "v",
            "provenance": "p",
            "coverage": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
            "parcels": [{"id": "p1", "ring": [[5, 5], [6, 5], [6, 6], [5, 6], [5, 5]]}],
        }
    )
    assert any("outside every declared coverage" in p for p in problems)


def test_from_doc_raises_on_violations() -> None:
    with pytest.raises(ParcelSignalError):
        ResidentialParcelSignal.from_doc({"signal_id": "s"})
    # A clean document loads.
    assert (
        ResidentialParcelSignal.from_doc(
            {"signal_id": "s", "version": "v", "provenance": "p"}
        ).stamp
        == "s@v"
    )


# --- the publish-path refusal (SIG-PUB-011/013) -------------------------------


def test_assert_public_layer_subject_refuses_flagged() -> None:
    with pytest.raises(CandidateAssetPublishRefused):
        assert_public_layer_subject("physical_asset", residential_parcel_flag=True, surface="test")


def test_assert_public_layer_subject_refuses_candidate_asset() -> None:
    # Flagged or not, a candidate asset never reaches a public device layer.
    with pytest.raises(CandidateAssetPublishRefused):
        assert_public_layer_subject("candidate_asset", surface="test")
    with pytest.raises(CandidateAssetPublishRefused):
        assert_public_layer_subject("candidate_asset", residential_parcel_flag=True, surface="test")


def test_assert_public_layer_subject_passes_ordinary_subjects() -> None:
    assert_public_layer_subject("deployment", surface="test")
    assert_public_layer_subject("physical_asset", residential_parcel_flag=False)
