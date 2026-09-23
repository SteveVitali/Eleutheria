# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P28.6 — the accountability-linkage assembler (pure logic, no DB).

Proves the labelled-inference contract over the deployment→vendor→contract→funding→
policy→oversight chain:
* each derived link is a labelled L4 inference citing its establishing claims (§3.1);
* the procured ≠ deployed guard refuses a deployment-layer predicate as a link type;
* a bare procurement claim never yields a link (an honest gap, not a fabricated edge);
* the idempotency digest is stable and changes with the establishing-claim set.
"""

from __future__ import annotations

import pytest
from inference.accountability import (
    FUNDED_BY,
    GOVERNED_BY_POLICY,
    HAS_VENDOR,
    OVERSEEN_BY,
    PROCURED_UNDER_CONTRACT,
    AcctClaim,
    accountability_link_digest,
    assemble_links,
    assert_not_deployment_link,
    link_inference,
    link_predicate,
)


def _full_chain_claims() -> list[AcctClaim]:
    """A deployment with a complete governance chain through its operator org."""
    return [
        AcctClaim("c-op", "dep1", "deployment", "operator", "org1", "organization"),
        AcctClaim("c-buy", "ct1", "contract", "buyer", "org1", "organization"),
        AcctClaim("c-sell", "ct1", "contract", "seller", "ven1", "organization"),
        AcctClaim("c-fund", "fu1", "funding_instrument", "recipient", "org1", "organization"),
        AcctClaim("c-pol", "pol1", "policy", "applies_to", "dep1", "deployment"),
        AcctClaim("c-evt", "evt1", "accountability_event", "deployments", "dep1", "deployment"),
    ]


def _link_by_type(links, link_type):
    return [i for i in links if i.value["link_type"] == link_type]


def test_full_governance_chain_is_assembled_with_provenance() -> None:
    """A real deployment→vendor→contract→funding→policy→oversight chain, each citing claims."""
    links = assemble_links(["dep1"], _full_chain_claims())
    kinds = {i.value["link_type"] for i in links}
    assert kinds == {
        HAS_VENDOR,
        PROCURED_UNDER_CONTRACT,
        FUNDED_BY,
        GOVERNED_BY_POLICY,
        OVERSEEN_BY,
    }
    # Every link is a labelled L4 inference, never an observation (SIG-ONTO-002/031).
    for inf in links:
        assert inf.layer == "L4"
        assert inf.is_observation is False
        assert inf.pushable_to_osm is False
        assert inf.derivation_rule == "accountability_linkage/§13"
        assert inf.predicate_id == link_predicate(inf.value["link_type"])
        # Each link cites at least one establishing claim (§3.1).
        assert inf.input_claim_ids
        assert set(inf.value["establishing_claims"]) == set(inf.input_claim_ids)

    # The vendor is reached THROUGH the contract (via_contract) and cites all three claims.
    vendor = _link_by_type(links, HAS_VENDOR)[0]
    assert vendor.value["object_id"] == "ven1"
    assert vendor.value["via_contract"] == "ct1"
    assert vendor.value["via_org"] == "org1"
    assert set(vendor.value["establishing_claims"]) == {"c-op", "c-buy", "c-sell"}

    contract = _link_by_type(links, PROCURED_UNDER_CONTRACT)[0]
    assert contract.value["object_id"] == "ct1"
    assert set(contract.value["establishing_claims"]) == {"c-op", "c-buy"}

    funding = _link_by_type(links, FUNDED_BY)[0]
    assert funding.value["object_id"] == "fu1"
    assert set(funding.value["establishing_claims"]) == {"c-op", "c-fund"}

    policy = _link_by_type(links, GOVERNED_BY_POLICY)[0]
    assert policy.value["object_id"] == "pol1"  # applies_to the deployment directly
    assert policy.value["establishing_claims"] == ["c-pol"]

    oversight = _link_by_type(links, OVERSEEN_BY)[0]
    assert oversight.value["object_id"] == "evt1"


def test_direct_vendor_claim_on_the_deployment() -> None:
    """A vendor asserted directly on the deployment (no contract) still links, citing it."""
    links = assemble_links(
        ["dep1"],
        [AcctClaim("c-v", "dep1", "deployment", "vendor", "ven1", "organization")],
    )
    vendors = _link_by_type(links, HAS_VENDOR)
    assert len(vendors) == 1
    assert vendors[0].value["object_id"] == "ven1"
    assert vendors[0].value["via_contract"] is None
    assert vendors[0].value["establishing_claims"] == ["c-v"]


def test_procured_not_deployed_a_bare_procurement_claim_yields_no_link() -> None:
    """procured ≠ deployed: a contract with a buyer but a deployment with NO operator edge
    produces no link (the contract cannot reach the deployment, honest gap), and a
    procurement/count claim is never read as evidence a deployment exists."""
    # A contract names a buyer org, but no operator edge ties dep1 to that org.
    links = assemble_links(
        ["dep1"],
        [
            AcctClaim("c-buy", "ct1", "contract", "buyer", "org1", "organization"),
            AcctClaim("c-sell", "ct1", "contract", "seller", "ven1", "organization"),
        ],
    )
    assert links == []  # the procurement fact does not become a deployment link


def test_guard_refuses_a_deployment_layer_predicate() -> None:
    """The predicate-layer guard: a deployment-layer predicate is never a link type."""
    for bad in ("deployed", "contracted_device_count", "active_device_count", "physical_state"):
        with pytest.raises(ValueError, match="procured ≠ deployed"):
            assert_not_deployment_link(bad)
    # An accountability link type passes.
    assert assert_not_deployment_link(PROCURED_UNDER_CONTRACT) == PROCURED_UNDER_CONTRACT


def test_link_inference_requires_an_establishing_claim() -> None:
    """No unevidenced link (§3.1): a link with no establishing claim is refused."""
    with pytest.raises(ValueError, match="at least one establishing claim"):
        link_inference(
            link_type=HAS_VENDOR,
            deployment_id="dep1",
            object_id="ven1",
            object_type="organization",
            establishing_claims=[],
            chain_role="vendor",
        )


def test_digest_is_stable_and_changes_with_the_claim_set() -> None:
    """The idempotency key: same content → same digest; a changed claim set → a new digest."""
    base = {
        "link_type": HAS_VENDOR,
        "deployment_id": "dep1",
        "object_id": "ven1",
        "object_type": "organization",
        "via_org": "org1",
        "via_contract": "ct1",
        "establishing_claims": ["c-op", "c-buy", "c-sell"],
    }
    d1 = accountability_link_digest(base)
    d2 = accountability_link_digest({**base, "establishing_claims": ["c-sell", "c-op", "c-buy"]})
    assert d1 == d2  # order-independent
    d3 = accountability_link_digest({**base, "establishing_claims": ["c-op", "c-buy"]})
    assert d3 != d1  # a changed evidence set supersedes


def test_only_anchored_deployments_are_linked() -> None:
    """A link is only assembled for a deployment in the anchor set (resolved deployments)."""
    claims = _full_chain_claims()
    # dep1 is not in the anchor set → no links.
    assert assemble_links([], claims) == []
    assert assemble_links(["other"], claims) == []
