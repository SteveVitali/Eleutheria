# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""A zero-record ingest fails the run; absent is not not-observed (SIG-IDENT-008)."""

from __future__ import annotations

import pytest
from db.absence import AbsenceState
from resolution.registry_ingest import (
    ZeroRecordIngest,
    assert_registry_records_present,
    classify_zero,
)


def test_nonzero_ingest_returns_the_count() -> None:
    assert (
        assert_registry_records_present(42, jurisdiction="06075", sources_searched=["census"]) == 42
    )


def test_zero_record_ingest_fails_the_run() -> None:
    with pytest.raises(ZeroRecordIngest) as excinfo:
        assert_registry_records_present(
            0, jurisdiction="06075", sources_searched=["FBI CDE", "census"]
        )
    # It carries the distinguished absence state, not a silent zero.
    assert excinfo.value.absence_state is AbsenceState.NO_EVIDENCE_FOUND
    assert excinfo.value.jurisdiction == "06075"


def test_absent_is_distinguished_from_not_observed() -> None:
    # not observed: we searched and found nothing.
    assert classify_zero(source_asserts_absent=False) is AbsenceState.NO_EVIDENCE_FOUND
    # absent: the source affirmatively states there are none (a positive finding).
    assert classify_zero(source_asserts_absent=True) is AbsenceState.EVIDENCE_OF_ABSENCE

    with pytest.raises(ZeroRecordIngest) as absent:
        assert_registry_records_present(0, jurisdiction="06075", source_asserts_absent=True)
    assert absent.value.absence_state is AbsenceState.EVIDENCE_OF_ABSENCE


def test_not_observed_zero_must_name_the_sources_searched() -> None:
    # SIG-TIME-011 (via db.absence): a NO_EVIDENCE_FOUND with no sources is rejected.
    with pytest.raises(ValueError, match="SIG-TIME-011"):
        assert_registry_records_present(0, jurisdiction="06075")


def test_negative_count_is_a_programming_error() -> None:
    with pytest.raises(ValueError, match="negative"):
        assert_registry_records_present(-1, jurisdiction="06075")
