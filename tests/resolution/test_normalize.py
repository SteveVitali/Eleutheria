# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""normalize_org_name(): pure, deterministic, versioned; committed vectors in CI;
sheriff collapse; acronyms by exact lookup only, never fuzzy (SIG-IDENT-022)."""

from __future__ import annotations

import tomllib
from importlib.resources import files

import pytest
from resolution.normalize import (
    NORMALIZE_RULESET_VERSION,
    normalize_org_name,
    resolve_acronym,
    ruleset_version,
)


def _vectors() -> list[dict[str, str]]:
    resource = files("resolution").joinpath("data", "normalize_vectors.toml")
    with resource.open("rb") as fh:
        return tomllib.load(fh)["vector"]


# --- The committed test-vector suite (SIG-IDENT-022) -------------------------


@pytest.mark.parametrize("vector", _vectors(), ids=lambda v: v["input"])
def test_every_committed_vector_holds(vector: dict[str, str]) -> None:
    assert normalize_org_name(vector["input"]) == vector["expected"]


def test_there_are_committed_vectors() -> None:
    assert _vectors()  # a normaliser with no committed vectors is unguarded


# --- Purity / determinism ----------------------------------------------------


def test_is_deterministic_and_idempotent() -> None:
    name = "Los Angeles County Sheriff's Department"
    once = normalize_org_name(name)
    assert normalize_org_name(name) == once  # deterministic across calls
    assert normalize_org_name(once) == once  # idempotent on its own output


# --- Sheriff's Office / Department collapse ----------------------------------


def test_sheriff_office_and_department_collapse_to_one_suffix() -> None:
    office = normalize_org_name("Travis County Sheriff's Office")
    department = normalize_org_name("Travis County Sheriff's Department")
    assert office == department == "travis county sheriff office"


# --- Acronyms: exact lookup only, NEVER fuzzy --------------------------------


def test_known_acronym_resolves_by_exact_lookup() -> None:
    assert resolve_acronym("LAPD") == "Los Angeles Police Department"
    assert resolve_acronym("  lapd  ") == "Los Angeles Police Department"  # trimmed, ci
    assert normalize_org_name("NYPD") == "new york city police department"


def test_similar_initials_are_not_fuzzy_merged() -> None:
    # LASD and LAPD share three letters; exact lookup keeps them distinct and a
    # typo resolves to NOTHING rather than the nearest acronym (SIG-IDENT-022).
    assert normalize_org_name("LAPD") != normalize_org_name("LASD")
    assert resolve_acronym("LAPDX") is None
    assert resolve_acronym("LAP") is None
    assert resolve_acronym("LASO") is None  # near-miss of LASD; not merged
    assert normalize_org_name("LAPDX") == "lapdx"


def test_acronym_lookup_is_whole_string_not_substring() -> None:
    # An acronym embedded in a longer name is NOT expanded — only a whole-string
    # match counts, so "LAPD Foothill Division" is not silently rewritten.
    assert resolve_acronym("LAPD Foothill Division") is None
    assert normalize_org_name("LAPD Foothill Division") == "lapd foothill division"


# --- Versioning --------------------------------------------------------------


def test_ruleset_is_versioned() -> None:
    assert ruleset_version() == NORMALIZE_RULESET_VERSION
    assert NORMALIZE_RULESET_VERSION  # a non-empty version string


# --- Edge cases --------------------------------------------------------------


def test_empty_and_punctuation_only_normalise_to_empty() -> None:
    assert normalize_org_name("") == ""
    assert normalize_org_name("   ") == ""
    assert normalize_org_name("!!!---") == ""
