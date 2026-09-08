# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Internationalisation of the ontology (§13.7-13.8, SIG-ONTO-068/069, P18.1).

Two invariants the international data model rests on:

* the four internationalised vocabularies are **country-namespaced under a shared
  abstract parent** and were extended by adding non-US children, not by widening a
  US-shaped enum (SIG-ONTO-068, §5.3); and
* label-bearing entities carry **repeatable BCP-47 language tags** plus a
  ``transliteration_scheme`` qualifier, and those labels round-trip through the
  generated model (SIG-ONTO-069).
"""

from __future__ import annotations

import pytest
from support import load_generated_pydantic, load_schemaview

# The four §13.7 internationalised vocabularies (SIG-ONTO-068).
I18N_ENUMS = ("OrganizationType", "JurisdictionType", "LegalInstrumentType", "AcquisitionMethod")

# The country namespaces the international model uses (§13.7). `private`/`gov` are
# sector namespaces, not country namespaces, and are out of scope for the
# country-child/abstract-parent rules below.
COUNTRY_NAMESPACES = frozenset({"us", "fr", "uk", "de", "eu"})
NON_US_COUNTRY_NAMESPACES = COUNTRY_NAMESPACES - {"us"}

# The us.* permissible values that existed before P18.1, frozen so the "no US enum
# was widened" guard is falsifiable. P18.1 adds only non-US children; if a later
# change adds a us.* value it must update this set deliberately.
FROZEN_US_VALUES: dict[str, frozenset[str]] = {
    "OrganizationType": frozenset(
        {
            "us.le.municipal_police",
            "us.le.sheriff",
            "us.le.state_police",
            "us.le.university_police",
            "us.le.transit_police",
            "us.le.school_district_police",
            "us.le.tribal_police",
            "us.le.federal",
            "us.gov.municipality",
            "us.gov.county",
            "us.gov.special_district",
            "us.fusion_center",
        }
    ),
    "JurisdictionType": frozenset(),  # generic levels only; no us.* values
    "LegalInstrumentType": frozenset(),  # generic parents only; no us.* values
    "AcquisitionMethod": frozenset({"us.foia", "us.state_public_records"}),
}


@pytest.fixture(scope="module")
def sv() -> object:
    return load_schemaview()


def _values(sv: object, enum: str) -> dict[str, object]:
    return dict(sv.get_enum(enum).permissible_values)  # type: ignore[attr-defined]


def _prefix(value: str) -> str | None:
    return value.split(".", 1)[0] if "." in value else None


# --- SIG-ONTO-068: country-namespaced enums under a shared abstract parent ----


@pytest.mark.parametrize("enum", I18N_ENUMS)
def test_enum_carries_non_us_national_children(sv: object, enum: str) -> None:
    # Each internationalised vocabulary carries at least one non-US *country* child,
    # proving the model is not US-only (§5.3).
    values = _values(sv, enum)
    non_us_children = {v for v in values if _prefix(v) in NON_US_COUNTRY_NAMESPACES}
    assert non_us_children, f"{enum} has no non-US national child (SIG-ONTO-068)"


@pytest.mark.parametrize("enum", I18N_ENUMS)
def test_every_non_us_national_child_has_a_shared_abstract_parent(sv: object, enum: str) -> None:
    # SIG-ONTO-068 / AC2: the national children added under a country namespace sit
    # under a shared abstract parent, declared via LinkML `is_a`. The parent is
    # itself an in-enum permissible value and is country-neutral (dotless).
    values = _values(sv, enum)
    national_children = {n for n in values if _prefix(n) in NON_US_COUNTRY_NAMESPACES}
    assert national_children
    for name in national_children:
        parent = getattr(values[name], "is_a", None)
        assert parent, f"{enum}.{name} has no abstract parent (is_a) (SIG-ONTO-068)"
        assert parent in values, f"{enum}.{name} parent {parent!r} is not an in-enum term"
        assert _prefix(parent) is None, f"{enum}.{name} parent {parent!r} must be country-neutral"


def test_us_law_enforcement_types_share_the_international_abstract_parent(sv: object) -> None:
    # The shared-abstract-parent-per-concept claim is cross-country: the US LE types
    # and the FR/UK/DE LE types all hang off the same `law_enforcement` parent, so a
    # rollup query spans jurisdictions (SIG-ONTO-068). US civil-government types share
    # a `government` parent likewise.
    values = _values(sv, "OrganizationType")
    assert "law_enforcement" in values
    assert "government" in values
    for term in ("us.le.municipal_police", "fr.police_municipale", "uk.territorial_police"):
        assert values[term].is_a == "law_enforcement"  # type: ignore[attr-defined]
    for term in ("us.gov.municipality", "us.gov.county", "us.fusion_center"):
        assert values[term].is_a == "government"  # type: ignore[attr-defined]


@pytest.mark.parametrize("enum", I18N_ENUMS)
def test_no_us_enum_was_widened(sv: object, enum: str) -> None:
    # SIG-ONTO-068 / P18.1 AC2: types added under a national namespace, NOT by
    # widening a US enum. The us.* value set must equal the frozen baseline.
    values = _values(sv, enum)
    us_values = {v for v in values if _prefix(v) == "us"}
    assert us_values == FROZEN_US_VALUES[enum], (
        f"{enum} us.* set changed: added={us_values - FROZEN_US_VALUES[enum]}, "
        f"removed={FROZEN_US_VALUES[enum] - us_values} (a US enum must not be widened)"
    )


def test_records_request_vocabulary_is_internationalised(sv: object) -> None:
    # §13.8: the abstract parent `records_request` with national children, plus
    # `no_equivalent_available` for a jurisdiction with no access regime.
    values = _values(sv, "AcquisitionMethod")
    assert "records_request" in values
    assert "no_equivalent_available" in values
    national = {v for v in values if _prefix(v) is not None}
    assert {"fr.cada", "uk.foi"} <= national
    # every national child hangs off the abstract parent
    for v in national:
        assert values[v].is_a == "records_request"  # type: ignore[attr-defined]


def test_legal_instrument_type_carries_a_national_authorization_instrument(sv: object) -> None:
    # §11.14 / §52 Phase 18: the French arrêté préfectoral must have somewhere to
    # land, namespaced under its abstract parent rather than by a US-shaped enum.
    values = _values(sv, "LegalInstrumentType")
    assert "fr.arrete_prefectoral" in values
    assert values["fr.arrete_prefectoral"].is_a == "prefectoral_order"  # type: ignore[attr-defined]


# --- SIG-ONTO-069: BCP-47 multilingual labels + transliteration scheme --------


@pytest.mark.parametrize("entity", ["Jurisdiction", "Organization"])
def test_label_bearing_entity_has_bcp47_and_transliteration_slots(sv: object, entity: str) -> None:
    slots = {s.name: s for s in sv.class_induced_slots(entity)}  # type: ignore[attr-defined]
    assert "name_lang" in slots, f"{entity} missing name_lang (SIG-ONTO-069)"
    assert slots["name_lang"].range == "bcp47"
    assert slots["name_lang"].multivalued
    assert "transliteration_scheme" in slots, f"{entity} missing transliteration_scheme"
    assert slots["transliteration_scheme"].multivalued


def test_multilingual_labels_round_trip_and_render() -> None:
    # A repeatable, language-tagged, transliterated set of names round-trips through
    # the generated Pydantic model (SIG-ONTO-069) — the "render correctly" AC.
    models = load_generated_pydantic()
    org = models.Organization(  # type: ignore[attr-defined]
        id="sig:org:1",
        canonical_name="Préfecture de police de Paris",
        name_lang=["fr-FR", "en-GB", "ja-Latn"],
        transliteration_scheme=["", "", "Hepburn"],
    )
    dumped = org.model_dump()
    assert dumped["name_lang"] == ["fr-FR", "en-GB", "ja-Latn"]
    # The transliteration scheme qualifies the transliterated label positionally:
    # the ja-Latn romanisation carries "Hepburn"; the native-script labels carry none.
    assert dumped["transliteration_scheme"] == ["", "", "Hepburn"]
    assert len(dumped["name_lang"]) == len(dumped["transliteration_scheme"])
    # A jurisdiction's multilingual names round-trip too, positionally paired:
    # name[i] is tagged by name_lang[i] (repeatable, BCP-47 — SIG-ONTO-069).
    juris = models.Jurisdiction(  # type: ignore[attr-defined]
        id="sig:juris:75056",
        name=["Paris", "パリ"],
        name_lang=["fr-FR", "ja-JP"],
    )
    jd = juris.model_dump()
    assert jd["name"] == ["Paris", "パリ"]
    assert jd["name_lang"] == ["fr-FR", "ja-JP"]
    assert len(jd["name"]) == len(jd["name_lang"])
