# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tiered address keys K1–K4: K1/K2 may match, K3/K4 blocking-only (SIG-IDENT-013)."""

from __future__ import annotations

import pytest
from resolution.address import (
    BLOCKING_ONLY_KEYS,
    IDENTITY_KEYS,
    BlockingOnlyKeyError,
    assert_identity_usable,
    build_address_keys,
)
from resolution.geoid import GeoidValidationError


def test_the_two_key_classes_are_disjoint_and_complete() -> None:
    assert IDENTITY_KEYS == {"K1", "K2"}
    assert BLOCKING_ONLY_KEYS == {"K3", "K4"}
    assert IDENTITY_KEYS.isdisjoint(BLOCKING_ONLY_KEYS)


def test_k1_k2_are_identity_usable() -> None:
    assert assert_identity_usable("K1") == "K1"
    assert assert_identity_usable("K2") == "K2"


@pytest.mark.parametrize("blocking", ["K3", "K4"])
def test_blocking_only_keys_are_refused_as_identity_evidence(blocking: str) -> None:
    with pytest.raises(BlockingOnlyKeyError):
        assert_identity_usable(blocking)


def test_unknown_key_kind_is_rejected() -> None:
    with pytest.raises(ValueError):
        assert_identity_usable("K9")


def test_build_partitions_keys_into_identity_and_blocking() -> None:
    keys = build_address_keys(
        tiger_line_side="edge-7:L",
        block_geoid="481576789012345",
        tract_geoid="48157678901",
        place_geoid="4835000",
    )
    assert keys.identity_keys() == {"K1": "edge-7:L", "K2": "481576789012345"}
    assert keys.blocking_keys() == {"K3": "48157678901", "K4": "4835000"}


def test_build_validates_geoid_widths() -> None:
    # A place GEOID must be 7 chars; a wrong width fails at build time.
    with pytest.raises(GeoidValidationError):
        build_address_keys(place_geoid="48")
    with pytest.raises(GeoidValidationError):
        build_address_keys(block_geoid="123")  # block is 15-wide


def test_coarse_address_has_only_a_place_key() -> None:
    keys = build_address_keys(place_geoid="4835000")
    assert keys.identity_keys() == {}
    assert keys.blocking_keys() == {"K4": "4835000"}
