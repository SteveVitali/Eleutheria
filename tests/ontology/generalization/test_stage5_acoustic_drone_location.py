# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Phase 17 (P17.3): gunshot detection, drones, and commercial location data —
populated with **no schema change**.

This continues the standing proof of §5.2 that P17.1/P17.2 began: the schema
frozen in Phase 2/4 must absorb a further Stage-5 technology span with no change
(SIG-CHART-027/028). Each construct is *populated* as an instance graph over the
committed generated Pydantic model (a real downstream form) and the committed
§13.1/§13.2 vocabularies, proving it is expressible with today's ontology. If a
construct ever required a new capability slug, edge type, technology slug, entity
class, mobility value, or role, ``test_stage5_acoustic_drone_location_required_no_schema_change``
fails — that red result is the Phase-1 defect the acceptance gate demands be
*recorded, not patched here* (the LinkML source is owned by P01.1).

The load-bearing point of this ticket is SIG-ONTO-027: acoustic gunshot sensors
and drones are **non-camera physical sensors** that MUST be representable *without
a camera abstraction*. They are ``PhysicalAsset``\\s whose ``asset_type`` is an
``acoustic`` / ``robotics-aerial`` Technology (never a ``camera-*`` slug) and,
for the drone, whose ``mobility`` is ``airborne``. Commercial location data, by
contrast, has no owned sensor at all: it is a ``data-acquisition`` Deployment (a
subscription) plus a reference ``DataSystem``, with no ``PhysicalAsset``, product,
or vendor — a deployment with no roadside device (SIG-ONTO-026/031).

Constructs proven (ticket deliverables 1–4):

1. **Gunshot detection** — acoustic ``PhysicalAsset``\\s that are **not cameras**
   (``asset_type`` → an ``acoustic`` Technology, ``gunshot-detection-fixed``;
   already in OSM as ``gunshot_detector``), SIG-ONTO-027. A rooftop sensor's
   coordinate sensitivity is evaluated at the **role** level and protects the
   **host** (whose roof it is on), not the operator (§12.4 item 6, §43.3).
2. **Drones / UAS** — airborne ``PhysicalAsset``\\s (``mobility=airborne``,
   ``asset_type`` under ``robotics-aerial``), not a camera abstraction
   (SIG-ONTO-027).
3. **Commercial location data** — a ``data-acquisition`` **Deployment** (a
   subscription) + reference **DataSystem** with **no locally owned sensor**: no
   ``PhysicalAsset``, no product, no vendor (SIG-ONTO-026/031). No ``Person`` row
   is minted for the individuals whose location history the corpus contains
   (§11.3, §43.4).
4. The **no-schema-change proof** is the deterministic Phase-1-defect detector
   (SIG-CHART-027/028); a construct that needed a new schema element fails it, and
   that failure is the recorded Phase-1 defect (owned by P01.1), never patched here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from support import load_generated_pydantic, load_vocab

# `RoleAssignment` inherits the required `edge_type` from `Edge`, but the closed
# §12 catalog has no role-specific member — the role semantics live entirely in
# `role`/`party`/`over` (§12.4). `member_of_network` is used as the neutral,
# structurally-valid carrier for that inherited field; the tests assert on the
# role fields, never on this edge_type. (See RISK-P17-04, established by P17.1.)
_ROLE_EDGE_TYPE = "member_of_network"


@pytest.fixture(scope="module")
def m() -> Any:
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


@dataclass
class Graph:
    """A populated instance graph: the nodes and edges of one pathway."""

    nodes: dict[str, Any] = field(default_factory=dict)
    edges: list[Any] = field(default_factory=list)

    def add_node(self, node: Any) -> Any:
        self.nodes[node.id] = node
        return node

    def add_edge(self, edge: Any) -> Any:
        self.edges.append(edge)
        return edge


# --- Deliverable 1: gunshot detection as acoustic, non-camera PhysicalAssets --


@pytest.fixture(scope="module")
def gunshot_detection(m: Any) -> Graph:
    """Gunshot detection populated as an acoustic ``PhysicalAsset`` that is **not
    a camera**. A city police department operates a rooftop acoustic sensor; the
    sensor sits on a private building. Two independent ``RoleAssignment``\\s make
    the separation first-class: the department is the ``operator``, the building
    owner is the ``host`` — so §43.3 coordinate sensitivity, evaluated at the
    role level, protects the *host* (whose roof it is on), not the operator
    (§12.4 item 6). The department's deployment provides the ``alert.gunshot.own``
    capability."""
    g = Graph()

    g.add_node(m.Organization(id="org:city-pd"))
    g.add_node(m.Organization(id="org:downtown-building-owner"))

    # The acoustic sensor — a PhysicalAsset whose asset_type is an `acoustic`
    # Technology, NOT a camera. Rooftop-mounted, so its mobility is fixed. Its
    # coordinate is sensitive because it reveals the host building (§43.3).
    g.add_node(
        m.PhysicalAsset(
            id="asset:gunshot-sensor-rooftop",
            asset_type="gunshot-detection-fixed",
            mobility=m.Mobility.fixed,
            geometry="POINT(-73.9857 40.7484)",
            sensitivity_tier="2",
            confirmation_status=m.ConfirmationStatus.record_confirmed,
            upstream_id=["osm.node/gunshot_detector"],
        )
    )

    # The capability the deployment provides, in verb.object.scope grammar.
    g.add_node(
        m.Capability(
            id="cap:alert-gunshot-own",
            capability="alert.gunshot.own",
            scope=m.CapabilityScope.own,
        )
    )
    g.add_node(
        m.Deployment(
            id="dep:gunshot-city-pd",
            deploying_organization="org:city-pd",
            technology=["gunshot-detection-fixed"],
            actually_provides_capability=["alert.gunshot.own"],
        )
    )

    # §12.4 role separation over the SAME asset — operator ≠ host, each a separate
    # RoleAssignment so §43.3 can be evaluated per role. The host bears the
    # coordinate risk; the operator does not.
    g.add_edge(
        m.RoleAssignment(
            id="role:gunshot-operator",
            source="org:city-pd",
            target="asset:gunshot-sensor-rooftop",
            edge_type=_ROLE_EDGE_TYPE,
            role=m.Role.operator,
            party="org:city-pd",
            over="asset:gunshot-sensor-rooftop",
        )
    )
    g.add_edge(
        m.RoleAssignment(
            id="role:gunshot-host",
            source="org:downtown-building-owner",
            target="asset:gunshot-sensor-rooftop",
            edge_type=_ROLE_EDGE_TYPE,
            role=m.Role.host,
            party="org:downtown-building-owner",
            over="asset:gunshot-sensor-rooftop",
        )
    )
    return g


def test_gunshot_detection_is_an_acoustic_non_camera_physical_asset(
    gunshot_detection: Graph, tech_by_slug: dict, capability_slugs: set, m: Any
) -> None:
    # Deliverable 1 / SIG-ONTO-027: gunshot detection is a PhysicalAsset whose
    # asset_type is an `acoustic`-domain Technology, never a camera abstraction.
    g = gunshot_detection
    sensor = g.nodes["asset:gunshot-sensor-rooftop"]
    assert isinstance(sensor, m.PhysicalAsset)
    assert sensor.asset_type == "gunshot-detection-fixed"
    # The technology lives under the `acoustic` domain, not a camera domain.
    assert tech_by_slug["gunshot-detection-fixed"]["domain"] == "acoustic"
    assert tech_by_slug["gunshot-detection-fixed"]["family"] == "gunshot-detection"
    # It is emphatically NOT a camera: no camera token anywhere on the asset.
    assert "camera" not in sensor.asset_type
    # The capability follows the committed verb.object.scope grammar.
    cap = g.nodes["cap:alert-gunshot-own"]
    assert cap.capability == "alert.gunshot.own"
    assert cap.capability in capability_slugs
    assert len(cap.capability.split(".")) == 3


def test_gunshot_sensor_coordinate_risk_is_evaluated_at_the_host_role(
    gunshot_detection: Graph, m: Any
) -> None:
    # §12.4 item 6 / §43.3: a rooftop acoustic sensor's coordinate sensitivity is
    # evaluated at the ROLE level and protects the HOST (whose roof it is on), not
    # the operator. Operator and host are separate, independently-modelled roles
    # over the same asset — never collapsed to owner/operator.
    g = gunshot_detection
    roles = {e.id: e for e in g.edges if e.__class__.__name__ == "RoleAssignment"}
    operator = roles["role:gunshot-operator"]
    host = roles["role:gunshot-host"]

    assert operator.role == m.Role.operator
    assert host.role == m.Role.host
    # Both roles are held over the same asset, by different parties.
    assert operator.over == host.over == "asset:gunshot-sensor-rooftop"
    assert operator.party != host.party
    # The sensitive coordinate lives on the asset the HOST hosts — so evaluating
    # coordinate sensitivity at the host role protects the building, not the PD.
    sensor = g.nodes[host.over]
    assert sensor.geometry is not None
    assert sensor.sensitivity_tier is not None
    assert host.party == "org:downtown-building-owner"


# --- Deliverable 2: drones / UAS as airborne, non-camera PhysicalAssets -------


@pytest.fixture(scope="module")
def drones(m: Any) -> Graph:
    """Drones / UAS populated as **airborne** ``PhysicalAsset``\\s
    (``mobility=airborne``), not a camera abstraction (SIG-ONTO-027). A sheriff's
    office runs a drone-as-first-responder programme; the deployment provides the
    ``dispatch.uas.autonomous`` capability."""
    g = Graph()

    g.add_node(m.Organization(id="org:county-sheriff"))

    # A general UAS and a drone-as-first-responder, both airborne PhysicalAssets
    # whose asset_type is a `robotics-aerial` Technology — never a camera.
    g.add_node(
        m.PhysicalAsset(
            id="asset:uas-general",
            asset_type="uas-general",
            mobility=m.Mobility.airborne,
            confirmation_status=m.ConfirmationStatus.record_confirmed,
        )
    )
    g.add_node(
        m.PhysicalAsset(
            id="asset:drone-first-responder",
            asset_type="drone-as-first-responder",
            mobility=m.Mobility.airborne,
            confirmation_status=m.ConfirmationStatus.reported_unverified,
        )
    )

    g.add_node(
        m.Capability(
            id="cap:dispatch-uas-autonomous",
            capability="dispatch.uas.autonomous",
            scope=m.CapabilityScope.subject,
        )
    )
    g.add_node(
        m.Deployment(
            id="dep:dfr-county",
            deploying_organization="org:county-sheriff",
            technology=["uas-general", "drone-as-first-responder"],
            actually_provides_capability=["dispatch.uas.autonomous"],
        )
    )
    return g


def test_drones_are_airborne_non_camera_physical_assets(
    drones: Graph, tech_by_slug: dict, capability_slugs: set, m: Any
) -> None:
    # Deliverable 2 / SIG-ONTO-027: drones are PhysicalAssets with mobility=airborne
    # and a robotics-aerial asset_type — never a camera abstraction.
    g = drones
    assets = [n for n in g.nodes.values() if isinstance(n, m.PhysicalAsset)]
    assert len(assets) == 2
    for asset in assets:
        assert asset.mobility == m.Mobility.airborne
        assert "camera" not in asset.asset_type
        assert tech_by_slug[asset.asset_type]["domain"] == "robotics-aerial"
    # The capability follows the committed verb.object.scope grammar.
    cap = g.nodes["cap:dispatch-uas-autonomous"]
    assert cap.capability == "dispatch.uas.autonomous"
    assert cap.capability in capability_slugs
    assert len(cap.capability.split(".")) == 3


# --- Deliverable 3: commercial location data — a subscription, no owned sensor -


@pytest.fixture(scope="module")
def commercial_location(m: Any) -> Graph:
    """Commercial location data populated as a ``data-acquisition`` **Deployment**
    (a subscription) plus a reference **DataSystem**, with **no locally owned
    sensor** — no ``PhysicalAsset``, no product, no vendor (SIG-ONTO-026/031). A
    police department subscribes to a commercial location-data platform; the
    corpus of device location histories stays with the platform. No ``Person`` row
    is minted for the individuals in that corpus (§11.3, §43.4)."""
    g = Graph()

    g.add_node(m.Organization(id="org:metro-pd"))
    g.add_node(m.Organization(id="org:location-broker"))

    # The commercial dataset is infrastructure even though SIG (and the PD) holds
    # no sensor: a reference DataSystem operated by the broker (SIG-ONTO-031).
    g.add_node(
        m.DataSystem(
            id="sys:commercial-location-platform",
            operator="org:location-broker",
            system_scope=m.SystemScope.commercial,
            data_types=["device_location_history"],
        )
    )

    g.add_node(
        m.Capability(
            id="cap:search-location-history-commercial",
            capability="search.location_history.commercial",
            scope=m.CapabilityScope.commercial,
        )
    )

    # The subscription IS the deployment — a data-acquisition deployment with NO
    # product, NO vendor, and NO PhysicalAsset: a deployment with no roadside
    # device (SIG-ONTO-026).
    g.add_node(
        m.Deployment(
            id="dep:location-subscription-metro-pd",
            deploying_organization="org:metro-pd",
            technology=["location-data-subscription"],
            actually_provides_capability=["search.location_history.commercial"],
        )
    )

    # The access relationship: the PD subscribes to the broker's platform for
    # standing access; the corpus stays with the platform (data does not come to
    # rest at the PD). `subscribes_to` is the closed-catalog member for "B pays
    # for standing access to A's data/service".
    g.add_edge(
        m.AccessRelationship(
            id="edge:pd-subscribes-location",
            source="org:metro-pd",
            target="sys:commercial-location-platform",
            edge_type=m.EdgeType.subscribes_to,
            scope=m.CapabilityScope.commercial,
            direction=m.Direction.a_to_b,
            automaticity=m.Automaticity.manual_approval,
            access_kind=m.AccessKind.configured_access,
        )
    )
    return g


def test_commercial_location_is_a_subscription_with_no_owned_sensor(
    commercial_location: Graph, tech_by_slug: dict, m: Any
) -> None:
    # Deliverable 3 / SIG-ONTO-026/031 / AC2: commercial location data is a
    # data-acquisition Deployment (a subscription) + a reference DataSystem, with
    # NO product, NO vendor, and NO PhysicalAsset — a deployment with no roadside
    # device.
    g = commercial_location
    dep = g.nodes["dep:location-subscription-metro-pd"]
    assert isinstance(dep, m.Deployment)
    assert dep.technology == ["location-data-subscription"]
    assert dep.product is None
    assert dep.vendor is None
    # The subscription owns no sensor at all.
    assert not any(isinstance(n, m.PhysicalAsset) for n in g.nodes.values())
    # The corpus is a reference DataSystem under the data-acquisition domain.
    assert tech_by_slug["location-data-subscription"]["domain"] == "data-acquisition"
    assert tech_by_slug["location-data-subscription"]["family"] == "location-data"
    system = g.nodes["sys:commercial-location-platform"]
    assert isinstance(system, m.DataSystem)
    # The subscription is realised in the closed §12 catalog as `subscribes_to`.
    edge = next(e for e in g.edges if e.id == "edge:pd-subscribes-location")
    assert edge.edge_type == m.EdgeType.subscribes_to
    assert edge.target == system.id


# --- Deliverable 1+2 cross-check: no camera abstraction is forced -------------


def test_no_sensor_is_forced_into_a_camera_abstraction(
    gunshot_detection: Graph, drones: Graph, commercial_location: Graph, m: Any
) -> None:
    # Deliverable 1+2+3 / SIG-ONTO-026/027: none of gunshot detection, drones, or
    # commercial location data is represented as a camera. Physical sensors carry
    # an acoustic / robotics-aerial asset_type (never `camera-*`); the commercial
    # subscription owns no PhysicalAsset at all.
    all_nodes = [
        *gunshot_detection.nodes.values(),
        *drones.nodes.values(),
        *commercial_location.nodes.values(),
    ]
    for n in all_nodes:
        atype = getattr(n, "asset_type", None)
        assert atype is None or "camera" not in atype
    # The physical sensors that DO exist are acoustic or airborne robotics — the
    # non-camera families this ticket is about.
    physical = [n for n in all_nodes if isinstance(n, m.PhysicalAsset)]
    assert physical, "gunshot + drones must populate real PhysicalAssets"
    for asset in physical:
        assert asset.asset_type in {
            "gunshot-detection-fixed",
            "uas-general",
            "drone-as-first-responder",
        }


# --- Person guard (§11.3, §43.4): no Person row for observed individuals -------


def test_no_person_rows_are_minted_for_observed_individuals(
    gunshot_detection: Graph, drones: Graph, commercial_location: Graph, m: Any
) -> None:
    # §11.3 / §43.4: commercial location corpora (and every other construct here)
    # MUST NOT mint Person rows for the individuals they observe.
    all_nodes = [
        *gunshot_detection.nodes.values(),
        *drones.nodes.values(),
        *commercial_location.nodes.values(),
    ]
    assert not any(isinstance(n, m.Person) for n in all_nodes)


# --- Deliverable 4: the no-schema-change proof / Phase-1-defect detector -------


def test_stage5_acoustic_drone_location_required_no_schema_change(
    gunshot_detection: Graph,
    drones: Graph,
    commercial_location: Graph,
    tech_by_slug: dict,
    capability_slugs: set,
    m: Any,
) -> None:
    """SIG-CHART-027/028 (AC1): every capability slug, edge type, entity class,
    technology slug, mobility value, and role the three Stage-5 constructs use
    already exists in the committed ontology. Populating them required NO new
    schema element.

    This is the deterministic Phase-1-defect detector: a construct that needed a
    new element would fail here, and per the Phase-17 acceptance gate that failure
    is recorded as a Phase-1 defect against the ontology (owned by P01.1) — never
    patched silently in this ticket.
    """
    graphs = (gunshot_detection, drones, commercial_location)
    all_edges = [e for g in graphs for e in g.edges]
    all_nodes = [n for g in graphs for n in g.nodes.values()]

    # Every edge type used is a member of the committed closed catalog.
    catalog = {t.value for t in m.EdgeType}
    assert {str(e.edge_type) for e in all_edges} <= catalog

    # Every capability slug used is in the committed §13.2 vocabulary.
    used_caps = {n.capability for n in all_nodes if n.__class__.__name__ == "Capability"}
    assert used_caps == {
        "alert.gunshot.own",
        "dispatch.uas.autonomous",
        "search.location_history.commercial",
    }
    assert used_caps <= capability_slugs

    # Every node is one of the committed entity classes (no new class was needed).
    committed_classes = {
        m.Organization,
        m.Capability,
        m.Deployment,
        m.DataSystem,
        m.PhysicalAsset,
    }
    assert all(type(n) in committed_classes for n in all_nodes)

    # Every technology slug the constructs name is in the committed §13.1 tree, and
    # each lives under the expected non-camera domain.
    expected_domains = {
        "gunshot-detection-fixed": "acoustic",
        "uas-general": "robotics-aerial",
        "drone-as-first-responder": "robotics-aerial",
        "location-data-subscription": "data-acquisition",
    }
    for slug, domain in expected_domains.items():
        assert slug in tech_by_slug
        assert tech_by_slug[slug]["domain"] == domain

    # Every mobility value used by a physical sensor is a committed enum member.
    used_mobility = {
        str(n.mobility) for n in all_nodes if isinstance(n, m.PhysicalAsset) and n.mobility
    }
    assert used_mobility <= {v.value for v in m.Mobility}
    assert "airborne" in used_mobility  # the drone case exercised the airborne value

    # Every role used by a RoleAssignment is a committed member of the §12.4 Role
    # enum (operator and host are both needed for the coordinate-at-role model).
    used_roles = {str(e.role) for e in all_edges if e.__class__.__name__ == "RoleAssignment"}
    assert used_roles == {"operator", "host"}
    assert used_roles <= {r.value for r in m.Role}
