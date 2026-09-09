# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The LinkML ontology covers every §11 entity and §12 edge, and obeys the
cross-cutting invariants (§3.1, §0.7 Part VIII, §12.8, SIG-ONTO-*)."""

from __future__ import annotations

import pytest
from support import VENDOR_TOKENS, load_schemaview, slug_tokens

# Every §11 entity (the entity index, incl. the [NEW] and split entities).
EXPECTED_ENTITIES = {
    "Jurisdiction",
    "Organization",
    "Person",
    "Product",
    "Technology",
    "Capability",
    "Deployment",
    "PhysicalAsset",
    "CandidateAsset",
    "DataSystem",
    "Contract",
    "FundingInstrument",
    "Policy",
    "LegalInstrument",
    "ConfigurationState",
    "UsageAggregate",
    "AccountabilityEvent",
    "LegalProceeding",
    "RecordsRequest",
    "Source",
    "EvidenceArtifact",
    "EvidenceCapture",
    "Extraction",
    "Claim",
    "Resolution",
    "Contradiction",
    "ResearchTask",
    "CoverageRecord",
}
NEW_ENTITIES = {
    "Jurisdiction",
    "Person",
    "CandidateAsset",
    "FundingInstrument",
    "LegalInstrument",
    "RecordsRequest",
}
# Every §12 edge type that MUST be in the closed catalog.
EXPECTED_EDGE_TYPES = {
    "ingests_feed_from",
    "pushes_alerts_to",
    "federates_search_to",
    "is_queryable_by",
    "hosts_data_for",
    "resells_data_from",
    "provides_platform_to",
    "subscribes_to",
    "enrolls_asset_into",
    "requests_data_from",
    "distributes_list_to",
    "authorizes",
    "replaced_by",
    "succeeds",
    "parent_of",
    "child_of",
    "merged_into",
    "split_from",
    "renamed_from",
    "absorbed_by",
    "participates_in",
    "has_jurisdiction_over",
    "operates_within",
    "member_of_network",
    "derived_from_claim",
    "supersedes_claim",
    "contradicts_claim",
    "corroborates_claim",
    "extracted_from_capture",
    "captures_artifact",
    "published_by_source",
}
# Prohibited edges (§12.8, SIG-ONTO-050) that MUST NOT be in the catalog.
PROHIBITED_EDGE_TYPES = {"integrates_with", "shares_with"}


@pytest.fixture(scope="module")
def sv() -> object:
    return load_schemaview()


def test_every_section_11_entity_is_a_class(sv: object) -> None:
    classes = set(sv.all_classes())  # type: ignore[attr-defined]
    assert EXPECTED_ENTITIES <= classes, EXPECTED_ENTITIES - classes


def test_new_entities_are_present(sv: object) -> None:
    # SIG-ONTO-010/014/029/033; §11.14; §11.19 — the six [NEW] entities.
    classes = set(sv.all_classes())  # type: ignore[attr-defined]
    assert NEW_ENTITIES <= classes


def test_edge_type_is_a_closed_catalog_with_every_section_12_edge(sv: object) -> None:
    # SIG-ONTO-041: every edge typed from a closed catalog.
    values = set(sv.get_enum("EdgeType").permissible_values)  # type: ignore[attr-defined]
    assert EXPECTED_EDGE_TYPES <= values, EXPECTED_EDGE_TYPES - values


def test_prohibited_edges_are_absent(sv: object) -> None:
    # SIG-ONTO-045/050: no stored integrates_with; no undifferentiated shares_with.
    values = set(sv.get_enum("EdgeType").permissible_values)  # type: ignore[attr-defined]
    assert not (PROHIBITED_EDGE_TYPES & values), PROHIBITED_EDGE_TYPES & values


def test_edges_carry_universal_requirements(sv: object) -> None:
    # SIG-ONTO-041: directed, typed, time-bounded, evidenced, perspectival.
    induced = {s.name for s in sv.class_induced_slots("AccessRelationship")}  # type: ignore[attr-defined]
    required = {
        "source",
        "target",
        "edge_type",
        "valid_from",
        "valid_to",
        "valid_from_kind",
        "valid_to_kind",
        "observed_at",
        "sources",
        "asserted_by",
    }
    assert required <= induced, required - induced


def test_person_is_tightly_constrained(sv: object) -> None:
    # §0.7 / §11.3 / SIG-ONTO-014/015/016: Person carries no surveillance attributes.
    slots = {s.name: s for s in sv.class_induced_slots("Person")}  # type: ignore[attr-defined]
    assert set(slots) <= {
        "id",
        "public_interest_basis",
        "human_review_completed",
        "role_description",
    }
    assert slots["public_interest_basis"].required
    assert slots["human_review_completed"].required


def test_source_class_is_the_six_ol_2e_al_03_classes(sv: object) -> None:
    # SIG-ONTO-039 / §11.17: an incident is linkable to all six source classes.
    values = set(sv.get_enum("SourceClass").permissible_values)  # type: ignore[attr-defined]
    assert values == {
        "primary_record",
        "court_record",
        "agency_statement",
        "vendor_statement",
        "investigative_article",
        "advocacy_analysis",
    }


def test_accountability_event_records_epistemic_status_and_source_class(sv: object) -> None:
    # SIG-ONTO-038: epistemic_status REQUIRED; SIG-ONTO-039: class recorded on the link.
    slots = {s.name: s for s in sv.class_induced_slots("AccountabilityEvent")}  # type: ignore[attr-defined]
    assert slots["epistemic_status"].required
    assert slots["epistemic_status"].range == "EpistemicStatus"
    # The per-source OL-2E-AL-03 class is recorded alongside the sources.
    assert "source_classes" in slots
    assert slots["source_classes"].range == "SourceClass"
    assert slots["source_classes"].multivalued


def test_policy_predicate_surface(sv: object) -> None:
    # §11.13 / SIG-ONTO-034: Policy carries its identity-only predicate surface —
    # a policy type, a polymorphic repeatable applies_to, an adopting body, and an
    # enforcement mechanism.
    slots = {s.name: s for s in sv.class_induced_slots("Policy")}  # type: ignore[attr-defined]
    assert {
        "policy_type",
        "applies_to",
        "adopting_body",
        "enforcement_mechanism",
    } <= set(slots)
    # applies_to is polymorphic (Organization / Deployment / Product) and repeatable.
    assert slots["applies_to"].multivalued
    assert slots["policy_type"].range == "PolicyType"
    assert slots["enforcement_mechanism"].range == "EnforcementMechanism"


def test_legal_instrument_predicate_surface(sv: object) -> None:
    # §11.14 [NEW]: a modelled law/regulation with an instrument type, an enacting
    # body, a jurisdiction, a citation, effective/sunset dates, and the constrains_*
    # / requires_authorization_of edges (CCOPS-style approval requirements).
    slots = {s.name: s for s in sv.class_induced_slots("LegalInstrument")}  # type: ignore[attr-defined]
    assert {
        "instrument_type",
        "enacting_body",
        "jurisdiction",
        "citation",
        "effective_from",
        "effective_to",
        "sunset_date",
        "constrains_technology",
        "constrains_capability",
        "requires_authorization_of",
    } <= set(slots)
    assert slots["instrument_type"].range == "LegalInstrumentType"
    assert slots["constrains_technology"].multivalued
    assert slots["constrains_capability"].multivalued
    assert slots["requires_authorization_of"].multivalued


def test_policy_and_configuration_state_are_never_merged(sv: object) -> None:
    # SIG-ONTO-034 (§11.13, P10): Policy MUST NOT be merged with ConfigurationState —
    # their disagreement is a first-class finding (§29.6), not one collapsed object.
    classes = set(sv.all_classes())  # type: ignore[attr-defined]
    assert {"Policy", "ConfigurationState"} <= classes
    # Two distinct classes; neither is a subtype of the other.
    assert sv.get_class("Policy").is_a != "ConfigurationState"  # type: ignore[attr-defined]
    assert sv.get_class("ConfigurationState").is_a != "Policy"  # type: ignore[attr-defined]
    # Their predicate surfaces are disjoint apart from the universal `id`: no slot
    # belongs to both, so the two objects cannot be silently folded into one.
    policy_slots = {s.name for s in sv.class_induced_slots("Policy")} - {"id"}  # type: ignore[attr-defined]
    config_slots = {s.name for s in sv.class_induced_slots("ConfigurationState")} - {"id"}  # type: ignore[attr-defined]
    assert not (policy_slots & config_slots), policy_slots & config_slots
    # The distinguishing predicates live on exactly one side.
    assert "policy_type" in policy_slots and "policy_type" not in config_slots
    assert "retention_days" in config_slots and "retention_days" not in policy_slots


def test_no_plate_trip_or_per_person_slot_exists(sv: object) -> None:
    # §0.7 Part VIII / N1 / N4 / SIG-ONTO-037: no plate/trip/per-person column anywhere.
    forbidden = {"plate", "trip", "sighting"}
    forbidden_phrases = ("per_person", "per_plate", "per_search", "license_plate")
    for name in sv.all_slots():  # type: ignore[attr-defined]
        toks = slug_tokens(name)
        assert not (forbidden & toks), name
        assert not any(p in name.lower() for p in forbidden_phrases), name


def test_no_vendor_name_in_any_schema_identifier(sv: object) -> None:
    # AC5 / SIG-ONTO-022/053/055 / P7: no vendor token in class/slot/enum/PV/type names.
    identifiers: set[str] = set()
    identifiers |= set(sv.all_classes())  # type: ignore[attr-defined]
    identifiers |= set(sv.all_slots())  # type: ignore[attr-defined]
    identifiers |= set(sv.all_types())  # type: ignore[attr-defined]
    for ename, enum in sv.all_enums().items():  # type: ignore[attr-defined]
        identifiers.add(ename)
        identifiers |= set(enum.permissible_values)
    offenders = {i for i in identifiers if slug_tokens(i) & VENDOR_TOKENS}
    assert not offenders, f"vendor token in schema identifier: {offenders}"
