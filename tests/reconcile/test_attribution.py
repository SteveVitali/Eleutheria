# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Device attribution (§29.2, SIG-RECON-030/031/032/033)."""

from __future__ import annotations

import pytest
from reconcile.attribution import (
    CandidateOperator,
    OrphanDevice,
    PromotionRefused,
    attribute_operator,
    promote,
)

ORPHAN = OrphanDevice(
    subject_id="asset:orphan-1", technology="alpr", inside_jurisdiction_id="juris:city"
)


def test_corroborated_candidate_yields_probable_l4_inference() -> None:
    # SIG-RECON-031: output is an L4 `probable` inference, never an observation.
    res = attribute_operator(
        ORPHAN,
        [
            CandidateOperator(org_id="org:pd", vendor_match=True, distance_m=120.0, claim_id="c1"),
            CandidateOperator(org_id="org:sheriff", contained_in_jurisdiction=True, claim_id="c2"),
        ],
    )
    assert res.inference is not None
    assert res.task is None
    inf = res.inference
    assert inf.confidence == "probable"
    assert inf.layer == "L4"
    assert inf.is_observation is False
    assert inf.value == "org:pd"
    assert inf.predicate_id == "attributed_operator"
    assert "org:sheriff" in inf.alternatives


def test_inference_is_not_writable_as_observed_operator() -> None:
    # SIG-RECON-031: MUST NOT be written into operator as observed.
    res = attribute_operator(ORPHAN, [CandidateOperator(org_id="org:pd", vendor_match=True)])
    assert res.inference is not None
    with pytest.raises(NotImplementedError):
        res.inference.as_observed_operator()


def test_inference_is_never_auto_pushable_to_osm() -> None:
    # SIG-RECON-031: MUST NOT be pushed to OSM automatically (§35.2).
    res = attribute_operator(ORPHAN, [CandidateOperator(org_id="org:pd", vendor_match=True)])
    assert res.inference is not None
    assert res.inference.pushable_to_osm is False


def test_containment_alone_is_not_attribution() -> None:
    # SIG-RECON-032: state-police device inside a city — containment is not attribution.
    res = attribute_operator(
        ORPHAN,
        [CandidateOperator(org_id="org:city", contained_in_jurisdiction=True, claim_id="c1")],
    )
    assert res.inference is None
    assert res.hard_case == "containment_only"
    assert res.task is not None


def test_boundary_device_is_enqueued_not_picked() -> None:
    # SIG-RECON-032: device on a jurisdiction boundary — ambiguous by construction.
    orphan = OrphanDevice(subject_id="asset:edge", technology="alpr", on_jurisdiction_boundary=True)
    res = attribute_operator(
        orphan,
        [
            CandidateOperator(org_id="org:a", vendor_match=True),
            CandidateOperator(org_id="org:b", vendor_match=True),
        ],
    )
    assert res.inference is None
    assert res.hard_case == "jurisdiction_boundary"
    assert res.task is not None


def test_county_road_inside_city_does_not_default_to_containing_jurisdiction() -> None:
    # SIG-RECON-032: device on a county road inside city limits — multiple candidates.
    res = attribute_operator(
        ORPHAN,
        [
            CandidateOperator(
                org_id="org:city", contained_in_jurisdiction=True, road_context="county_road"
            ),
            CandidateOperator(
                org_id="org:county", adjacent_jurisdiction=True, road_context="county_road"
            ),
        ],
    )
    assert res.inference is None
    assert res.hard_case == "cross_jurisdiction_road"


def test_multi_agency_shared_deployment_is_multiple_operators_not_a_conflict() -> None:
    # SIG-RECON-032: multi-agency shared deployment — multiple operators is a valid answer.
    res = attribute_operator(
        ORPHAN,
        [
            CandidateOperator(org_id="org:a", shared=True, vendor_match=True, claim_id="c1"),
            CandidateOperator(org_id="org:b", shared=True, vendor_match=True, claim_id="c2"),
        ],
    )
    assert res.hard_case == "multi_agency_shared"
    assert res.inference is not None
    assert set(res.inference.value) == {"org:a", "org:b"}  # type: ignore[arg-type]


def test_operator_on_behalf_of_names_the_role() -> None:
    # SIG-RECON-032: A operates on behalf of B — both roles recorded; attribution names the role.
    res = attribute_operator(
        ORPHAN,
        [
            CandidateOperator(
                org_id="org:vendor", vendor_match=True, on_behalf_of="org:city", claim_id="c1"
            )
        ],
    )
    assert res.inference is not None
    assert res.inference.predicate_id == "attributed_operator"
    assert "on behalf of org:city" in res.inference.rationale


def test_equally_corroborated_candidates_are_enqueued() -> None:
    res = attribute_operator(
        ORPHAN,
        [
            CandidateOperator(org_id="org:a", vendor_match=True),
            CandidateOperator(org_id="org:b", vendor_match=True),
        ],
    )
    assert res.inference is None
    assert res.hard_case == "tie"


def test_no_candidates_enqueues() -> None:
    res = attribute_operator(ORPHAN, [])
    assert res.inference is None
    assert res.hard_case == "no_candidate"


# --- SIG-RECON-033: promotion requires human confirmation or a D1/D2 source ---


def _an_inference():
    res = attribute_operator(ORPHAN, [CandidateOperator(org_id="org:pd", vendor_match=True)])
    assert res.inference is not None
    return res.inference


def test_high_score_does_not_promote_itself() -> None:
    with pytest.raises(PromotionRefused):
        promote(_an_inference())


def test_human_confirmation_promotes() -> None:
    promoted = promote(_an_inference(), confirmed_by="curator:jane")
    assert promoted.confidence == "asserted"
    assert "curator:jane" in promoted.rationale


def test_documentary_source_promotes() -> None:
    promoted = promote(_an_inference(), source_directness="D1")
    assert promoted.confidence == "asserted"


def test_weak_directness_does_not_promote() -> None:
    with pytest.raises(PromotionRefused):
        promote(_an_inference(), source_directness="D4")
