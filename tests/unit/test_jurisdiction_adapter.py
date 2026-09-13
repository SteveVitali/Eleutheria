# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The jurisdiction adapter framework (§5.3, §13.7-13.8, SIG-CHART-029/030, P18.1).

Proves the framework onboards a non-US jurisdiction with **no us.*-only code path**
(SIG-CHART-029/030), that a seeded adapter's vocabulary terms are real ontology
enum values (so the checklist gates against the actual schema, not a private
string list), and that the non-US records-request vocabulary — including
``no_equivalent_available`` — is usable.
"""

from __future__ import annotations

import pytest
from support import load_schemaview

from policy import jurisdiction as jur

NON_US_CODES = ("FR", "UK")


@pytest.fixture(scope="module")
def sv() -> object:
    return load_schemaview()


def _enum_values(sv: object, enum: str) -> set[str]:
    return set(sv.get_enum(enum).permissible_values)  # type: ignore[attr-defined]


# --- SIG-CHART-029: the checklist is satisfiable, no US-shaped assumption ------


def test_every_seeded_adapter_validates() -> None:
    all_adapters = jur.adapters()
    assert set(all_adapters) >= {"US", "FR", "UK"}
    for adapter in all_adapters.values():
        checklist = jur.validate_adapter(adapter)  # raises if incomplete / US-shaped
        assert all(checklist.values())


@pytest.mark.parametrize("code", NON_US_CODES)
def test_non_us_adapter_has_no_us_shaped_code_path(code: str) -> None:
    # SIG-CHART-030 / AC1: onboarding a non-US jurisdiction touches no us.* term.
    adapter = jur.get(code)
    assert not adapter.is_us
    jur.assert_no_us_shaped_assumption(adapter)  # does not raise
    for term in adapter.all_vocab():  # every slot, incl. national_code_schemes
        assert not term.startswith("us."), f"{code} adapter reaches for {term!r}"


def test_a_us_term_in_a_non_us_adapter_is_rejected() -> None:
    # The guard is real: inject a us.* term into a non-US adapter and it raises.
    fr = jur.get("FR")
    poisoned = jur.JurisdictionAdapter(
        code=fr.code,
        namespace=fr.namespace,
        jurisdiction_levels=fr.jurisdiction_levels,
        national_code_schemes=fr.national_code_schemes,
        organization_types=("us.le.municipal_police",),  # US-shaped assumption
        legal_instrument_types=fr.legal_instrument_types,
        records_request_methods=fr.records_request_methods,
        default_languages=fr.default_languages,
        publication_profile=fr.publication_profile,
        local_partner=fr.local_partner,
    )
    with pytest.raises(jur.USShapedAssumptionError):
        jur.assert_no_us_shaped_assumption(poisoned)


def test_a_us_code_scheme_in_a_non_us_adapter_is_rejected() -> None:
    # The us.* ban covers national_code_schemes too — a non-US adapter reaching for
    # a us.* code system is a US-shaped code path just as much as a us.* org type.
    fr = jur.get("FR")
    poisoned = jur.JurisdictionAdapter(
        code=fr.code,
        namespace=fr.namespace,
        jurisdiction_levels=fr.jurisdiction_levels,
        national_code_schemes=("us.census.geoid",),  # US-shaped assumption
        organization_types=fr.organization_types,
        legal_instrument_types=fr.legal_instrument_types,
        records_request_methods=fr.records_request_methods,
        default_languages=fr.default_languages,
        publication_profile=fr.publication_profile,
        local_partner=fr.local_partner,
    )
    with pytest.raises(jur.USShapedAssumptionError):
        jur.assert_no_us_shaped_assumption(poisoned)


def test_a_foreign_non_us_namespace_in_a_country_scoped_slot_is_rejected() -> None:
    # Rule 2: a country onboards under its OWN namespace — a FR adapter reaching for
    # a de.* org type is rejected even though it is not us.*.
    fr = jur.get("FR")
    poisoned = jur.JurisdictionAdapter(
        code=fr.code,
        namespace=fr.namespace,
        jurisdiction_levels=fr.jurisdiction_levels,
        national_code_schemes=fr.national_code_schemes,
        organization_types=("de.landespolizei",),  # foreign (non-own) namespace
        legal_instrument_types=fr.legal_instrument_types,
        records_request_methods=fr.records_request_methods,
        default_languages=fr.default_languages,
        publication_profile=fr.publication_profile,
        local_partner=fr.local_partner,
    )
    with pytest.raises(jur.USShapedAssumptionError):
        jur.assert_no_us_shaped_assumption(poisoned)


def test_global_code_schemes_are_allowed_in_a_non_us_adapter() -> None:
    # iso.* / wikidata.* are global scheme namespaces, not a foreign country's — a
    # non-US adapter may use them for code systems (rule 2 exempts code schemes).
    fr = jur.get("FR")
    assert "iso.3166-2" in fr.national_code_schemes
    assert "wikidata.qid" in fr.national_code_schemes
    jur.assert_no_us_shaped_assumption(fr)  # does not raise


def test_an_incomplete_adapter_fails_the_checklist() -> None:
    bare = jur.JurisdictionAdapter(code="ZZ", namespace="zz")
    with pytest.raises(jur.AdapterIncomplete):
        jur.validate_adapter(bare)


# --- The adapter vocabulary is grounded in the real ontology enums ------------


def test_adapter_vocab_terms_are_real_ontology_enum_values(sv: object) -> None:
    org = _enum_values(sv, "OrganizationType")
    juris = _enum_values(sv, "JurisdictionType")
    legal = _enum_values(sv, "LegalInstrumentType")
    acq = _enum_values(sv, "AcquisitionMethod")
    for adapter in jur.adapters().values():
        assert set(adapter.organization_types) <= org, adapter.code
        assert set(adapter.jurisdiction_levels) <= juris, adapter.code
        assert set(adapter.legal_instrument_types) <= legal, adapter.code
        assert set(adapter.records_request_methods) <= acq, adapter.code


# --- SIG-ONTO-068 realised: national namespaces, not a widened US enum ---------


def test_non_us_adapters_use_their_own_namespace_for_org_and_legal_types() -> None:
    for code in NON_US_CODES:
        adapter = jur.get(code)
        for term in (*adapter.organization_types, *adapter.legal_instrument_types):
            prefix = term.split(".", 1)[0] if "." in term else None
            # A namespaced term must carry the adapter's own namespace.
            if prefix is not None:
                assert prefix == adapter.namespace, f"{code}: {term!r}"


# --- §13.8: the non-US records-request vocabulary, incl. no_equivalent_available


def test_non_us_records_request_vocabulary_is_used() -> None:
    assert jur.get("FR").records_request_methods == ("fr.cada",)
    assert jur.get("UK").records_request_methods == ("uk.foi",)


def test_no_equivalent_available_is_a_valid_records_regime_declaration(sv: object) -> None:
    # A jurisdiction with no access regime records that fact explicitly (§13.8);
    # `no_equivalent_available` is a country-neutral term the framework accepts
    # without it counting as a foreign-namespace borrow.
    assert "no_equivalent_available" in _enum_values(sv, "AcquisitionMethod")
    no_regime = jur.JurisdictionAdapter(
        code="XX",
        namespace="xx",
        jurisdiction_levels=("country",),
        national_code_schemes=("iso.3166-2",),
        organization_types=("law_enforcement",),
        legal_instrument_types=("statute",),
        records_request_methods=("no_equivalent_available",),
        default_languages=("en",),
        publication_profile="UNKNOWN",
        local_partner="read-only",
    )
    checklist = jur.validate_adapter(no_regime)  # does not raise
    assert checklist["records_request_methods"]


# --- SIG-PUB-017: jurisdiction-conditional publication via the adapter ---------


def test_publication_is_jurisdiction_conditional_across_adapters() -> None:
    us = jur.get("US")
    fr = jur.get("FR")
    # US-DEFAULT: public-official names presumptively publishable, same-jurisdiction.
    assert jur.adapter_publication_permitted(us, "US", is_public_employee_name=True)
    # FR-GDPR: redact by default — the same fact is NOT publishable for a FR subject
    # even when the record also originates in FR (in-regime negative case)...
    assert not jur.adapter_publication_permitted(fr, "FR", is_public_employee_name=True)
    # ...nor across regimes in either direction.
    assert not jur.adapter_publication_permitted(fr, "US", is_public_employee_name=True)
    assert not jur.adapter_publication_permitted(us, "FR", is_public_employee_name=True)
    # Non-name institutional material is not gated by this rule.
    assert jur.adapter_publication_permitted(fr, "FR", is_public_employee_name=False)
