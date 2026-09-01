# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The generalization conformance suite (SIG-CHART-028, AC2).

Each of the five non-ALPR constructs the schema MUST support from day one
(SIG-CHART-027, §5.2) is proven *expressible* by instantiating the generated
Pydantic model (a real downstream form) and confirming the referenced vocabulary
concept exists. The suite fails the phase gate if the schema regresses to
ALPR-specific assumptions.
"""

from __future__ import annotations

import pytest
from support import load_generated_pydantic, load_vocab


@pytest.fixture(scope="module")
def m() -> object:
    return load_generated_pydantic()


@pytest.fixture(scope="module")
def tech_by_slug() -> dict:
    tech = load_vocab("technology")
    return {
        t["slug"]: {"family": fam["slug"], "domain": dom["slug"]}
        for dom in tech["domains"]
        for fam in dom["families"]
        for t in fam["technologies"]
    }


@pytest.fixture(scope="module")
def capability_slugs() -> set:
    return {c["slug"] for c in load_vocab("capability")["capabilities"]}


def test_acoustic_sensor_is_a_non_camera_physical_asset(m: object, tech_by_slug: dict) -> None:
    # OL-4.5-02 / SIG-ONTO-027: sensors are not forced into a camera abstraction.
    assert "gunshot-detection-fixed" in tech_by_slug
    assert tech_by_slug["gunshot-detection-fixed"]["domain"] == "acoustic"
    asset = m.PhysicalAsset(  # type: ignore[attr-defined]
        id="asset:1",
        asset_type="gunshot-detection-fixed",
        mobility=m.Mobility.fixed,  # type: ignore[attr-defined]
    )
    assert asset.asset_type == "gunshot-detection-fixed"


def test_capability_with_no_physical_asset(m: object, capability_slugs: set) -> None:
    # OL-4.6-01 / OL-4.8-01 / SIG-ONTO-026: a deployment needs no product, vendor, or asset.
    assert "extract.device.physical" in capability_slugs
    assert "locate.handset.rf" in capability_slugs
    deployment = m.Deployment(  # type: ignore[attr-defined]
        id="dep:css",
        technology=["cell-site-simulator-general"],
    )
    assert deployment.product is None and deployment.vendor is None
    cap = m.Capability(id="cap:1", capability="extract.device.physical")  # type: ignore[attr-defined]
    assert cap.capability == "extract.device.physical"


def test_reference_database_as_infrastructure(m: object) -> None:
    # OL-4.7-02 / SIG-ONTO-031: a reference database is a DataSystem even with no sensor.
    system = m.DataSystem(  # type: ignore[attr-defined]
        id="sys:refdb",
        system_scope=m.SystemScope.commercial,  # type: ignore[attr-defined]
        data_types=["face_gallery"],
    )
    assert system.system_scope == m.SystemScope.commercial  # type: ignore[attr-defined]


def test_commercial_data_access_relationship_with_no_local_sensor(m: object) -> None:
    # OL-4.9-01 / SIG-ONTO-049: a commercial data-access relationship with no owned sensor.
    subscription = m.Deployment(id="dep:fogreveal")  # type: ignore[attr-defined]
    assert subscription.product is None
    rel = m.AccessRelationship(  # type: ignore[attr-defined]
        id="edge:1",
        source="org:agency",
        target="org:broker",
        edge_type=m.EdgeType.resells_data_from,  # type: ignore[attr-defined]
        scope=m.CapabilityScope.commercial,  # type: ignore[attr-defined]
        direction=m.Direction.a_to_b,  # type: ignore[attr-defined]
        automaticity=m.Automaticity.automatic,  # type: ignore[attr-defined]
        access_kind=m.AccessKind.configured_access,  # type: ignore[attr-defined]
    )
    assert rel.access_kind == m.AccessKind.configured_access  # type: ignore[attr-defined]


def test_integration_hub_consuming_other_systems(m: object, tech_by_slug: dict) -> None:
    # OL-4.10-02 / §12.3: an integration hub that ingests from other systems.
    assert "camera-federation-hub" in tech_by_slug
    assert "rtcc-platform" in tech_by_slug
    edge = m.IntegrationEdge(  # type: ignore[attr-defined]
        id="edge:hub",
        source="sys:hub",
        target="sys:camera_network",
        edge_type=m.EdgeType.ingests_feed_from,  # type: ignore[attr-defined]
        data_kind="video",
        data_comes_to_rest=True,
    )
    assert edge.edge_type == m.EdgeType.ingests_feed_from  # type: ignore[attr-defined]


def test_access_relationship_requires_direction_scope_and_kind(m: object) -> None:
    # SIG-ONTO-049: never reduce a sharing relationship to an undifferentiated edge.
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        m.AccessRelationship(  # type: ignore[attr-defined]
            id="edge:bad",
            source="a",
            target="b",
            edge_type=m.EdgeType.subscribes_to,  # type: ignore[attr-defined]
        )


def test_access_relationship_requires_automaticity(m: object) -> None:
    # SIG-ONTO-049: direction, scope, automaticity, AND kind are all required — an
    # AccessRelationship missing automaticity is a reduction the spec forbids.
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        m.AccessRelationship(  # type: ignore[attr-defined]
            id="edge:no-automaticity",
            source="a",
            target="b",
            edge_type=m.EdgeType.subscribes_to,  # type: ignore[attr-defined]
            scope=m.CapabilityScope.partner,  # type: ignore[attr-defined]
            direction=m.Direction.a_to_b,  # type: ignore[attr-defined]
            access_kind=m.AccessKind.configured_access,  # type: ignore[attr-defined]
        )
