# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The Jurisdiction registry: overlapping hierarchy, GEOID validation, and
temporally-versioned geometry (§11.1, SIG-ONTO-010/011, SIG-IDENT-005)."""

from __future__ import annotations

from datetime import date

import pytest
from resolution.geoid import GeoidValidationError
from resolution.identity import Identifier
from resolution.jurisdiction import BoundaryVersion, build_jurisdiction


def test_overlapping_parents_are_permitted() -> None:
    # SIG-ONTO-010: hierarchies overlap — a city may span two counties.
    city = build_jurisdiction(
        jurisdiction_type="municipality",
        level="place",
        parents=("county-a", "county-b"),
        identifiers=[("us.census.geoid", "0667000")],
    )
    assert city.parents == ("county-a", "county-b")


def test_geoid_identifiers_are_validated_against_the_level() -> None:
    # SIG-IDENT-005: a GEOID whose width does not match the declared level is refused.
    with pytest.raises(GeoidValidationError):
        build_jurisdiction(
            jurisdiction_type="county",
            level="county",  # expects width 5
            identifiers=[("us.census.geoid", "0667000")],  # width 7 (a place)
        )
    ok = build_jurisdiction(
        jurisdiction_type="county",
        level="county",
        identifiers=[("us.census.geoid", "06075")],
    )
    assert Identifier("us.census.geoid", "06075") in ok.identifiers


def test_missing_level_and_type_are_refused() -> None:
    with pytest.raises(ValueError, match="explicit level"):
        build_jurisdiction(jurisdiction_type="municipality", level="")
    with pytest.raises(ValueError, match="jurisdiction_type"):
        build_jurisdiction(jurisdiction_type="", level="place")


def test_boundary_as_of_returns_the_version_in_force() -> None:
    # SIG-ONTO-011: an annexation means the containing polygon on the observation
    # date differs from today's. Two disjoint versions; as-of picks the right one.
    old = BoundaryVersion(
        geometry="MULTIPOLYGON(((0 0,0 1,1 1,1 0,0 0)))",
        valid_from=date(2000, 1, 1),
        valid_to=date(2015, 1, 1),
    )
    new = BoundaryVersion(
        geometry="MULTIPOLYGON(((0 0,0 2,2 2,2 0,0 0)))",
        valid_from=date(2015, 1, 1),
        valid_to=None,
    )
    juris = build_jurisdiction(
        jurisdiction_type="municipality", level="place", boundaries=[old, new]
    )
    assert juris.boundary_as_of(date(2010, 6, 1)) is old
    assert juris.boundary_as_of(date(2020, 6, 1)) is new
    # The observation-date geometry differs from today's — the whole point.
    assert juris.boundary_as_of(date(2010, 6, 1)) != juris.boundary_as_of(date(2020, 6, 1))


def test_boundary_as_of_before_any_version_is_none() -> None:
    v = BoundaryVersion(
        geometry="MULTIPOLYGON(((0 0,0 1,1 1,1 0,0 0)))", valid_from=date(2015, 1, 1)
    )
    juris = build_jurisdiction(jurisdiction_type="municipality", level="place", boundaries=[v])
    assert juris.boundary_as_of(date(2000, 1, 1)) is None


def test_pluggable_national_code_systems_are_accepted() -> None:
    # SIG-ONTO-010: the code system is pluggable — a non-US scheme (INSEE) is stored
    # and is not subjected to the Census GEOID width rule.
    commune = build_jurisdiction(
        jurisdiction_type="municipality",
        level="municipality",
        identifiers=[("fr.insee", "75056"), ("iso.3166-2", "FR-75")],
    )
    assert Identifier("fr.insee", "75056") in commune.identifiers
    assert Identifier("iso.3166-2", "FR-75") in commune.identifiers


def test_build_jurisdiction_coerces_identifier_pairs_to_a_set() -> None:
    juris = build_jurisdiction(
        jurisdiction_type="state",
        level="state",
        identifiers=[("us.census.geoid", "06"), Identifier("wikidata.qid", "Q99")],
        boundary_source="capture:tiger:2020",
    )
    assert len(juris.identifiers) == 2
    assert juris.boundary_source == "capture:tiger:2020"
