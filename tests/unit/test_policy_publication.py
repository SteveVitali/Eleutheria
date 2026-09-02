# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Publication policy: exclusions, de-pseudonymisation, jurisdiction (§43)."""

from __future__ import annotations

import pytest

from policy import publication


@pytest.mark.parametrize(
    "kind",
    ["license_plate_number", "travel_history", "home_address", "incidental_private_name"],
)
def test_categorically_excluded_data_cannot_be_stored(kind: str) -> None:
    assert publication.is_categorically_excluded(kind)
    with pytest.raises(publication.CategoricallyExcluded):
        publication.assert_storable(kind)


def test_institutional_data_is_storable() -> None:
    assert not publication.is_categorically_excluded("device_operator_agency")
    publication.assert_storable("device_operator_agency")  # does not raise


def test_operator_identifier_is_hashed_with_held_back_salt() -> None:
    a = publication.hash_operator_identifier("operator-uuid", salt="held-back")
    b = publication.hash_operator_identifier("operator-uuid", salt="held-back")
    assert a == b
    assert a != "operator-uuid"  # raw value never surfaces
    # A different salt yields a different digest (salt is genuinely mixed in).
    assert publication.hash_operator_identifier("operator-uuid", salt="other") != a


def test_hashing_requires_a_salt() -> None:
    with pytest.raises(ValueError):
        publication.hash_operator_identifier("x", salt="")


def test_operator_joinable_surface_is_forbidden() -> None:
    with pytest.raises(publication.DePseudonymisationError):
        publication.assert_no_operator_join(
            joinable_on_operator_id=True, per_operator_aggregation=False
        )
    with pytest.raises(publication.DePseudonymisationError):
        publication.assert_no_operator_join(
            joinable_on_operator_id=False, per_operator_aggregation=True
        )
    # A surface that does neither is allowed.
    publication.assert_no_operator_join(
        joinable_on_operator_id=False, per_operator_aggregation=False
    )


def test_jurisdiction_conditional_publication() -> None:
    # US permits public-employee names; EU (default posture) does not.
    assert publication.publication_permitted("US", "US", is_public_employee_name=True)
    assert not publication.publication_permitted("EU", "US", is_public_employee_name=True)
    assert not publication.publication_permitted("US", "EU", is_public_employee_name=True)
    # Unknown jurisdiction defaults conservative (no-publish).
    assert not publication.publication_permitted("ZZ", "US", is_public_employee_name=True)
    # Non-employee-name material is not gated by this rule.
    assert publication.publication_permitted("EU", "EU", is_public_employee_name=False)
