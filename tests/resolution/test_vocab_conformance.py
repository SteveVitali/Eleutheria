# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The resolution enums are the ontology's vocabularies, not a private copy.

The ontology is the single source of truth (§20.1, ADR-007). These tests fail if
the Python StrEnums drift from the generated LinkML enums, and if the two-axis
classification (SIG-IDENT-010) stops grounding its axes in the real vocabularies:
``organization_class`` in ``OrganizationType`` and ``operating_relationship`` in
the fourteen-role ``Role`` enum.
"""

from __future__ import annotations

import pytest
from resolution.geometry_precision import GeometryPrecision
from resolution.temporal_identity import OrganizationRelationType
from support import load_schemaview


@pytest.fixture(scope="module")
def sv() -> object:
    return load_schemaview()


def _enum_values(sv: object, name: str) -> set[str]:
    return set(sv.get_enum(name).permissible_values)  # type: ignore[attr-defined]


def test_organization_relation_type_matches_the_ontology(sv: object) -> None:
    assert {r.value for r in OrganizationRelationType} == _enum_values(
        sv, "OrganizationRelationType"
    )


def test_geometry_precision_matches_the_ontology(sv: object) -> None:
    assert {p.value for p in GeometryPrecision} == _enum_values(sv, "GeometryPrecision")


def test_two_axes_are_grounded_in_the_ontology_vocabularies(sv: object) -> None:
    org_types = _enum_values(sv, "OrganizationType")
    roles = _enum_values(sv, "Role")
    # The class axis draws from OrganizationType; the relationship axis from Role.
    for org_class in ("university", "us.le.sheriff", "us.gov.municipality", "private.hoa"):
        assert org_class in org_types
    for relationship in ("purchaser", "operator", "funder", "host"):
        assert relationship in roles
