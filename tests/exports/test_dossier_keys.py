# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.45 — the dossier-key matrix (K4 §5.2, D-K4-3, the unplaced sentinel).

Fixture-level tests of ``exports.dossier_keys``: the canonical slug paths,
the verbatim D-K4-3 page thresholds, ``group_by_key`` membership (placed /
declared / leaf / unplaced), and the parent↔child conservation the keyed
dossiers assert. No database, no secrets, no living values.
"""

from __future__ import annotations

from typing import Any

import pytest

from exports import dossier_keys as dk

# --------------------------------------------------------------------------- #
# Fixture registry — a small canonical world (US county + place, non-US admin1)
# --------------------------------------------------------------------------- #

_JROWS: dict[str, dict[str, Any]] = {
    "iso3166-1:US": {
        "jkey": "iso3166-1:US",
        "name": "United States",
        "level": "country",
        "parent": None,
        "vintage": "pl94-2020",
        "identifiers": [
            {"kind": "canonical", "scheme": "iso3166-1", "value": "US"},
            {"kind": "alternate", "scheme": "iso3166-1-a3", "value": "USA"},
        ],
    },
    "iso3166-1:GB": {
        "jkey": "iso3166-1:GB",
        "name": "United Kingdom",
        "level": "country",
        "parent": None,
        "vintage": "gss-2023",
        "identifiers": [
            {"kind": "canonical", "scheme": "iso3166-1", "value": "GB"},
            {"kind": "alternate", "scheme": "iso3166-1-a3", "value": "GBR"},
        ],
    },
    "iso3166-2:US-CA": {
        "jkey": "iso3166-2:US-CA",
        "name": "California",
        "level": "state_province",
        "parent": "iso3166-1:US",
        "vintage": "pl94-2020",
        "identifiers": [{"kind": "canonical", "scheme": "iso3166-2", "value": "US-CA"}],
    },
    "iso3166-2:US-PR": {
        "jkey": "iso3166-2:US-PR",
        "name": "Puerto Rico",
        "level": "state_province",
        "parent": "iso3166-1:US",
        "vintage": "pl94-2020",
        "identifiers": [{"kind": "canonical", "scheme": "iso3166-2", "value": "US-PR"}],
    },
    "iso3166-2:GB-ENG": {
        "jkey": "iso3166-2:GB-ENG",
        "name": "England",
        "level": "state_province",
        "parent": "iso3166-1:GB",
        "vintage": "gss-2023",
        "identifiers": [{"kind": "canonical", "scheme": "iso3166-2", "value": "GB-ENG"}],
    },
    "us.census.geoid.county:06037": {
        "jkey": "us.census.geoid.county:06037",
        "name": "Los Angeles County",
        "level": "county",
        "parent": "iso3166-2:US-CA",
        "vintage": "pl94-2020",
        "identifiers": [
            {"kind": "canonical", "scheme": "us.census.geoid.county", "value": "06037"}
        ],
    },
    "us.census.geoid.place:0644000": {
        "jkey": "us.census.geoid.place:0644000",
        "name": "Los Angeles",
        "level": "municipality",
        "parent": "iso3166-2:US-CA",
        "vintage": "pl94-2020",
        "identifiers": [
            {"kind": "canonical", "scheme": "us.census.geoid.place", "value": "0644000"}
        ],
    },
}

_CHAINS: dict[str, tuple[str, ...]] = {
    "iso3166-1:US": ("iso3166-1:US",),
    "iso3166-1:GB": ("iso3166-1:GB",),
    "iso3166-2:US-CA": ("iso3166-1:US", "iso3166-2:US-CA"),
    "iso3166-2:US-PR": ("iso3166-1:US", "iso3166-2:US-PR"),
    "iso3166-2:GB-ENG": ("iso3166-1:GB", "iso3166-2:GB-ENG"),
    "us.census.geoid.county:06037": (
        "iso3166-1:US",
        "iso3166-2:US-CA",
        "us.census.geoid.county:06037",
    ),
    "us.census.geoid.place:0644000": (
        "iso3166-1:US",
        "iso3166-2:US-CA",
        "us.census.geoid.place:0644000",
    ),
}


def _reg() -> dk.KeyedRegistry:
    return dk.keyed_registry(list(_JROWS.values()), _CHAINS)


# --------------------------------------------------------------------------- #
# Slug paths — the canonical nested segments (K4 §5.2)
# --------------------------------------------------------------------------- #


def test_slug_paths_are_canonical_and_nested():
    reg = _reg()
    assert reg.slug_path("iso3166-1:US") == "usa"
    assert reg.slug_path("iso3166-1:GB") == "gbr"
    assert reg.slug_path("iso3166-2:US-CA") == "usa/ca"
    assert reg.slug_path("iso3166-2:GB-ENG") == "gbr/eng"
    assert reg.slug_path("us.census.geoid.county:06037") == ("usa/ca/los-angeles-county-06037")
    assert reg.slug_path("us.census.geoid.place:0644000") == "usa/ca/los-angeles-0644000"


def test_slug_path_inverse_is_complete():
    reg = _reg()
    assert set(reg.by_slug_path) == {i.slug_path for i in reg.keys.values()}
    for path, jkey in reg.by_slug_path.items():
        assert reg.keys[jkey].slug_path == path


def test_slug_path_collision_fails_closed():
    # Two registry rows minting one path is a naming bug — never a silent
    # second dossier at the same route.
    rows = [
        dict(_JROWS["iso3166-1:US"]),
        {
            "jkey": "iso3166-1:UK",
            "name": "United States Alt",
            "level": "country",
            "parent": None,
            "identifiers": [{"kind": "alternate", "scheme": "iso3166-1-a3", "value": "USA"}],
        },
    ]
    with pytest.raises(ValueError, match="slug-path collision"):
        dk.keyed_registry(rows)


def test_display_name_carries_ancestors():
    reg = _reg()
    assert reg.display_name("iso3166-2:US-CA") == "California, United States"
    assert reg.display_name("us.census.geoid.county:06037") == (
        "Los Angeles County, California, United States"
    )
    # An unknown key renders as its key — honest, never a fabricated name.
    assert reg.display_name("iso3166-1:XX") == "iso3166-1:XX"


def test_keyed_registry_derives_chain_from_parentage_when_no_chains():
    reg = dk.keyed_registry(list(_JROWS.values()))
    ca = reg.keys["us.census.geoid.county:06037"]
    assert ca.chain == ("iso3166-1:US", "iso3166-2:US-CA", "us.census.geoid.county:06037")
    assert ca.country_jkey == "iso3166-1:US"
    assert ca.country_a2 == "US"


# --------------------------------------------------------------------------- #
# D-K4-3 page thresholds — applied verbatim
# --------------------------------------------------------------------------- #


def test_page_thresholds_verbatim():
    reg = _reg()
    # A US county with ONE record mints a page; so do the US admin-1s and
    # the country. The place with <10 records and no non-site evidence does
    # NOT. The non-US admin-1 with <10 does NOT (its country does).
    pages = dk.page_keys(
        reg,
        {
            "iso3166-1:US": 3,
            "iso3166-2:US-CA": 3,
            "us.census.geoid.county:06037": 1,
            "us.census.geoid.place:0644000": 9,
            "iso3166-1:GB": 2,
            "iso3166-2:GB-ENG": 2,
        },
    )
    assert "us.census.geoid.county:06037" in pages
    assert "iso3166-2:US-CA" in pages
    assert "iso3166-1:US" in pages
    assert "iso3166-1:GB" in pages
    assert "us.census.geoid.place:0644000" not in pages
    assert "iso3166-2:GB-ENG" not in pages
    # US territories sit under iso3166-1:US (D-K4-4) — a US admin-1 with 1
    # record mints.
    pages_pr = dk.page_keys(reg, {"iso3166-2:US-PR": 1})
    assert "iso3166-2:US-PR" in pages_pr
    # Non-US admin-1 at the 10-record bar mints.
    assert "iso3166-2:GB-ENG" in dk.page_keys(reg, {"iso3166-2:GB-ENG": 10})
    assert "iso3166-2:GB-ENG" not in dk.page_keys(reg, {"iso3166-2:GB-ENG": 9})
    # A US place at 10 mints; at 9 it does not.
    assert "us.census.geoid.place:0644000" in dk.page_keys(
        reg, {"us.census.geoid.place:0644000": 10}
    )
    # …but a US place with ANY non-site evidence mints at zero records.
    pages_nonsite = dk.page_keys(reg, {}, non_site_keys={"us.census.geoid.place:0644000"})
    assert "us.census.geoid.place:0644000" in pages_nonsite
    assert pages_nonsite["us.census.geoid.place:0644000"] == dk.THRESHOLD_US_PLACE_NONSITE


def test_page_basis_names_the_rule_verbatim():
    reg = _reg()
    info = reg.keys["us.census.geoid.county:06037"]
    assert dk.page_basis(info, placed_records=1) == dk.THRESHOLD_COUNTY
    us_a1 = reg.keys["iso3166-2:US-CA"]
    assert dk.page_basis(us_a1, placed_records=1) == dk.THRESHOLD_US_ADMIN1
    gb_a1 = reg.keys["iso3166-2:GB-ENG"]
    assert dk.page_basis(gb_a1, placed_records=10) == dk.THRESHOLD_NON_US_ADMIN1
    assert dk.page_basis(gb_a1, placed_records=9) is None
    country = reg.keys["iso3166-1:US"]
    assert dk.page_basis(country, placed_records=1) == dk.THRESHOLD_COUNTRY
    assert dk.page_basis(country, placed_records=0) is None


# --------------------------------------------------------------------------- #
# group_by_key — placed / declared / leaf / unplaced
# --------------------------------------------------------------------------- #


def _site_row(**kw: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "entity_id": "s1",
        "jurisdiction": "iso3166-2:US-CA",
        "jurisdiction_key": None,
        "jurisdiction_chain": [],
    }
    row.update(kw)
    return row


def test_group_by_key_placed_rolls_full_chain():
    placed, declared, leaf = dk.group_by_key(
        _site_row(
            jurisdiction_key="us.census.geoid.county:06037",
            jurisdiction_chain=list(_CHAINS["us.census.geoid.county:06037"]),
        )
    )
    assert placed == frozenset(_CHAINS["us.census.geoid.county:06037"])
    assert leaf == "us.census.geoid.county:06037"
    assert "iso3166-2:US-CA" in declared


def test_group_by_key_chain_less_record_is_unplaced_never_guessed():
    placed, declared, leaf = dk.group_by_key(
        _site_row(jurisdiction=None, jurisdiction_key=None, jurisdiction_chain=[])
    )
    assert placed == frozenset({dk.UNPLACED})
    assert leaf is None
    assert declared == frozenset()
    # A declared key still joins the appearing set — the disagreement keeps
    # both sides visible — but the placed leg stays the honest sentinel.
    placed2, declared2, leaf2 = dk.group_by_key(
        _site_row(jurisdiction="iso3166-2:US-CA", jurisdiction_key=None)
    )
    assert placed2 == frozenset({dk.UNPLACED})
    assert declared2 == frozenset({"iso3166-2:US-CA"})
    assert leaf2 is None


def test_group_by_key_honest_sentinels_mint_no_declared_leg():
    for sentinel in ("unresolved", dk.UNPLACED, "(unasserted)", "(conflicted)", ""):
        _placed, declared, _leaf = dk.group_by_key(_site_row(jurisdiction=sentinel))
        assert declared == frozenset(), sentinel


def test_group_by_key_bare_values_are_not_keys():
    # A bare "California" is never silently promoted to a canonical key —
    # it files as a named declared bucket (its own slug), not CA's dossier.
    _placed, declared, _leaf = dk.group_by_key(_site_row(jurisdiction="California"))
    assert declared == frozenset({"California"})
    assert "iso3166-2:US-CA" not in declared


# --------------------------------------------------------------------------- #
# Roll-up conservation — parent = own leaf + Σ children placed
# --------------------------------------------------------------------------- #


def test_rollup_conservation_arithmetic():
    """The conserved identity the keyed dossier docs assert:

    a dossier's placed count equals its own leaf-placed records plus the
    placed counts of its registry children — the chain is the only ancestry.
    """
    leaf_sets = {
        "iso3166-1:US": {"s-country"},
        "iso3166-2:US-CA": {"s-state"},
        "us.census.geoid.county:06037": {"s-county"},
        "us.census.geoid.place:0644000": {"s-place"},
    }
    placed = {
        "iso3166-1:US": {"s-country", "s-state", "s-county", "s-place"},
        "iso3166-2:US-CA": {"s-state", "s-county", "s-place"},
        "us.census.geoid.county:06037": {"s-county"},
        "us.census.geoid.place:0644000": {"s-place"},
    }
    reg = _reg()
    for jkey in ("iso3166-2:US-CA", "iso3166-1:US"):
        children = [c for c in reg.children.get(jkey, ()) if c in placed]
        assert len(placed[jkey]) == len(leaf_sets[jkey]) + sum(len(placed[c]) for c in children), (
            jkey
        )


# --------------------------------------------------------------------------- #
# The unplaced sentinel — a data-quality state, never a place
# --------------------------------------------------------------------------- #


def test_unplaced_is_not_a_registry_key():
    reg = _reg()
    assert dk.UNPLACED not in reg.keys
    assert dk.UNPLACED not in reg.by_slug_path
    # No registry segment can mint "unplaced" — it collides with nothing.
    assert all(i.slug_path != dk.UNPLACED for i in reg.keys.values())
