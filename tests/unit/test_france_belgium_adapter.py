# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""France & Belgium onboarded under national namespaces (§5.3, §13.7, SIG-ONTO-068, P18.2).

Deliverable 4: France/Belgium jurisdictions, org types, and legal-instrument types
are instantiated under a national namespace (fr.* / be.*) with a shared abstract
parent — NOT by widening a US enum — and the adapters validate through the P18.1
framework with no US-shaped code path. Belgium is added here; France was seeded by
P18.1 and its connectors land in this ticket.
"""

from __future__ import annotations

import pytest
from support import load_schemaview

from policy import jurisdiction as jur

FR_BE = ("FR", "BE")


@pytest.fixture(scope="module")
def sv() -> object:
    return load_schemaview()


def _enum_values(sv: object, enum: str) -> set[str]:
    return set(sv.get_enum(enum).permissible_values)  # type: ignore[attr-defined]


def test_belgium_adapter_is_seeded_and_validates() -> None:
    # SIG-CHART-029/030: Belgium onboards with no us.* code path anywhere.
    be = jur.get("BE")
    assert be.namespace == "be"
    checklist = jur.validate_adapter(be)  # raises if incomplete or US-shaped
    assert all(checklist.values())
    for term in be.all_vocab():
        assert not term.startswith("us."), term


@pytest.mark.parametrize("code", FR_BE)
def test_org_and_legal_types_use_the_national_namespace(code: str) -> None:
    # SIG-ONTO-068: a namespaced org/legal-instrument term carries the country's OWN
    # namespace — a national child under a shared abstract parent, not a widened US enum.
    adapter = jur.get(code)
    for term in (*adapter.organization_types, *adapter.legal_instrument_types):
        prefix = term.split(".", 1)[0] if "." in term else None
        if prefix is not None:
            assert prefix == adapter.namespace, f"{code}: {term!r}"


def test_belgium_terms_are_real_namespaced_ontology_values(sv: object) -> None:
    be = jur.get("BE")
    assert set(be.jurisdiction_levels) <= _enum_values(sv, "JurisdictionType")
    assert set(be.organization_types) <= _enum_values(sv, "OrganizationType")
    assert set(be.legal_instrument_types) <= _enum_values(sv, "LegalInstrumentType")
    # be.* children exist under shared abstract parents (SIG-ONTO-068).
    assert {"be.region", "be.province", "be.commune", "be.police_zone"} <= _enum_values(
        sv, "JurisdictionType"
    )
    assert {"be.police_locale", "be.police_federale"} <= _enum_values(sv, "OrganizationType")
    assert "be.loi_cameras" in _enum_values(sv, "LegalInstrumentType")


def test_no_us_enum_was_widened_for_france_or_belgium(sv: object) -> None:
    # SIG-ONTO-068 / §5.3: the frozen us.* org-type set is unchanged; France and
    # Belgium added NO us.* term. (The P18.1 baseline froze this set.)
    us_org = {v for v in _enum_values(sv, "OrganizationType") if v.startswith("us.")}
    assert us_org == {
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


def test_belgium_records_regime_is_no_equivalent_available() -> None:
    # §13.8: Belgium's national camera register is not public (eID wall, F9.31), so
    # its records-request regime is the country-neutral no_equivalent_available.
    assert jur.get("BE").records_request_methods == ("no_equivalent_available",)


def test_belgium_publication_is_jurisdiction_conditional_redact_by_default() -> None:
    # §43.8 / SIG-PUB-017: BE-GDPR redacts public-official names by default, like FR.
    be = jur.get("BE")
    assert not jur.adapter_publication_permitted(be, "BE", is_public_employee_name=True)
    assert jur.adapter_publication_permitted(be, "BE", is_public_employee_name=False)
