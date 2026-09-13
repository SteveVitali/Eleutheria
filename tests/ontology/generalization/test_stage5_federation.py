# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Phase 17 (P17.1): private-camera federation, RTCC integration, and the
commercial data-broker chain — populated with **no schema change**.

This is the standing proof of §5.2: the schema frozen in Phase 2/4 must absorb a
Stage-5 technology span with no change (SIG-CHART-027/028). Each Appendix D.5
pathway is *populated* as an instance graph over the generated Pydantic model (a
real downstream form), proving the construct is expressible with today's
ontology. If a construct ever required a new edge type, role, technology slug, or
entity class, ``test_stage5_population_required_no_schema_change`` fails — that
red result is the Phase-1 defect the acceptance gate demands be *recorded, not
patched here* (the LinkML source is owned by P01.1).

Constructs proven (ticket deliverables 1–4):

1. Private-camera federation — Appendix D.5 pathway 1. ``owner`` (a business) is
   independently separable from ``operator`` (a police RTCC) over the *same*
   private camera (SIG-ONTO-047/048 #1). ``enrolls_asset_into`` — whose object is
   a *device* — is kept distinct from a live-feed fact that carries its own
   ``consent_gate`` (SIG-ONTO-045/046). The registry (no live feed) and the
   integration (live feed) are separate vocabulary concepts, so enrolment never
   silently implies streaming.
2. RTCC integration hub — a ``DataSystem`` that *consumes other systems* via
   directional integration edges (``ingests_feed_from`` / ``federates_search_to``
   / ``pushes_alerts_to``), never a stored ``integrates_with`` (SIG-ONTO-045);
   with a reference database as infrastructure (SIG-ONTO-031).
3. The commercial data-broker chain — six layers, not five: the aggregating
   broker and the productizing platform are distinct organizations joined by
   ``resells_data_from`` (SIG-ONTO-046, Appendix D.5 pathway 3; R7 F7.29).
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
# role fields, never on this edge_type. (See RISK-P17-04.)
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


# --- Pathway 1: private camera -> integration platform -> RTCC -> fusion center


@pytest.fixture(scope="module")
def private_camera_federation(m: Any) -> Graph:
    """Appendix D.5 pathway 1, populated. A business owns a private camera that a
    police RTCC operates; the device is enrolled into an integration platform
    (registry), and — as a *separate*, consent-gated fact — a live feed is
    ingested by the RTCC."""
    g = Graph()

    business = g.add_node(m.Organization(id="org:main-street-market"))
    police = g.add_node(m.Organization(id="org:metro-pd"))
    fusion_center = g.add_node(m.Organization(id="org:regional-fusion-center"))

    # The private camera — a field device, not a camera-only abstraction.
    camera = g.add_node(
        m.PhysicalAsset(
            id="asset:market-front-cam",
            asset_type="camera-fixed-cctv",
            mobility=m.Mobility.fixed,
        )
    )
    # The integration platform and the RTCC are data systems, not sensors.
    platform = g.add_node(
        m.DataSystem(
            id="sys:community-connect",
            system_scope=m.SystemScope.vendor_cloud_shared,
            data_types=["video"],
        )
    )
    rtcc = g.add_node(
        m.DataSystem(
            id="sys:metro-rtcc",
            operator="org:metro-pd",
            system_scope=m.SystemScope.agency_local,
            data_types=["video", "alpr"],
        )
    )

    # owner != operator over the SAME asset (SIG-ONTO-047/048 #1), modelled as two
    # independent RoleAssignments so the separation is first-class.
    g.add_edge(
        m.RoleAssignment(
            id="role:cam-owner",
            source="org:main-street-market",
            target="asset:market-front-cam",
            edge_type=_ROLE_EDGE_TYPE,
            role=m.Role.owner,
            party="org:main-street-market",
            over="asset:market-front-cam",
        )
    )
    g.add_edge(
        m.RoleAssignment(
            id="role:cam-operator",
            source="org:metro-pd",
            target="asset:market-front-cam",
            edge_type=_ROLE_EDGE_TYPE,
            role=m.Role.operator,
            party="org:metro-pd",
            over="asset:market-front-cam",
        )
    )

    # Enrolment: the object is a DEVICE (a registry entry), not a live feed. No
    # data comes to rest, and it carries no consent gate of its own — enrolling a
    # camera is not the same act as streaming it (SIG-ONTO-045/046).
    g.add_edge(
        m.IntegrationEdge(
            id="edge:enrol",
            source="asset:market-front-cam",
            target="sys:community-connect",
            edge_type=m.EdgeType.enrolls_asset_into,
            data_kind="device_registration",
            data_comes_to_rest=False,
        )
    )
    # The live feed is a SEPARATE, evidenced fact with its OWN consent gate.
    g.add_edge(
        m.IntegrationEdge(
            id="edge:live-feed",
            source="sys:metro-rtcc",
            target="sys:community-connect",
            edge_type=m.EdgeType.ingests_feed_from,
            data_kind="video",
            data_comes_to_rest=True,
            consent_gate=True,
            initiator="sys:metro-rtcc",
        )
    )
    # The platform federates search to the RTCC — the corpus stays with the
    # platform (data does not come to rest at the far end).
    g.add_edge(
        m.IntegrationEdge(
            id="edge:federate",
            source="sys:community-connect",
            target="sys:metro-rtcc",
            edge_type=m.EdgeType.federates_search_to,
            data_kind="video",
            data_comes_to_rest=False,
        )
    )
    # The RTCC's department participates in a fusion center (structural, not data).
    g.add_edge(
        m.StructuralEdge(
            id="edge:participates",
            source="org:metro-pd",
            target="org:regional-fusion-center",
            edge_type=m.EdgeType.participates_in,
        )
    )

    _ = (business, police, fusion_center, camera, platform, rtcc)
    return g


def test_private_camera_owner_is_independently_separable_from_operator(
    private_camera_federation: Graph,
) -> None:
    # SIG-ONTO-047/048 #1: a private camera owned by a business but effectively
    # operated by a police RTCC — owner != operator, each first-class.
    g = private_camera_federation
    owner = g.nodes["asset:market-front-cam"]
    roles = {e.id: e for e in g.edges if e.__class__.__name__ == "RoleAssignment"}
    owner_role = roles["role:cam-owner"]
    operator_role = roles["role:cam-operator"]

    assert owner_role.role == "owner"
    assert operator_role.role == "operator"
    # Same device, different parties — the separation is not collapsible.
    assert owner_role.over == operator_role.over == owner.id
    assert owner_role.party != operator_role.party


def test_enrolment_is_a_device_edge_distinct_from_the_consent_gated_live_feed(
    private_camera_federation: Graph, tech_by_slug: dict, m: Any
) -> None:
    # Ticket deliverable 1 / SIG-ONTO-045/046: `enrolls_asset_into` (object = a
    # device) is a different edge from the live feed, which carries its own
    # consent gate. The registry and the integration are distinct vocab concepts.
    g = private_camera_federation
    enrol = next(e for e in g.edges if e.id == "edge:enrol")
    feed = next(e for e in g.edges if e.id == "edge:live-feed")

    assert enrol.edge_type == m.EdgeType.enrolls_asset_into
    assert feed.edge_type == m.EdgeType.ingests_feed_from
    assert enrol.id != feed.id

    # Enrolment registers a device; it does not itself stream (no rest, no gate).
    assert enrol.data_comes_to_rest is False
    assert enrol.consent_gate is None
    # The live feed is the fact that carries the consent gate.
    assert feed.consent_gate is True
    assert feed.data_comes_to_rest is True

    # The vocabulary keeps "registry (no live feed)" separate from "integration
    # (live feed)", so enrolment can never silently imply streaming.
    assert tech_by_slug["private-camera-registry"]["domain"] == "surveillance-video"
    assert tech_by_slug["private-camera-integration"]["domain"] == "surveillance-video"


def test_platform_federates_search_to_rtcc_corpus_stays_put(
    private_camera_federation: Graph, m: Any
) -> None:
    # §12.3: federates_search_to means the query moves and the corpus stays with A.
    g = private_camera_federation
    fed = next(e for e in g.edges if e.id == "edge:federate")
    assert fed.edge_type == m.EdgeType.federates_search_to
    assert fed.data_comes_to_rest is False


def test_pathway1_stores_no_integrates_with(private_camera_federation: Graph, m: Any) -> None:
    # SIG-ONTO-045: `integrates_with` is not a stored edge — it is absent from the
    # closed catalog, so no edge in the populated pathway can be one.
    assert not hasattr(m.EdgeType, "integrates_with")
    assert all(e.edge_type != "integrates_with" for e in private_camera_federation.edges)


# --- RTCC integration hub consuming other systems ----------------------------


@pytest.fixture(scope="module")
def rtcc_hub(m: Any) -> Graph:
    """An RTCC / camera-federation hub that *consumes other systems* via
    directional edges, plus a reference database as infrastructure."""
    g = Graph()

    hub = g.add_node(
        m.DataSystem(
            id="sys:citywide-rtcc-hub",
            operator="org:metro-pd",
            system_scope=m.SystemScope.agency_local,
            data_types=["video", "alerts"],
        )
    )
    camera_network = g.add_node(
        m.DataSystem(
            id="sys:downtown-camera-network",
            system_scope=m.SystemScope.vendor_cloud_shared,
            data_types=["video"],
        )
    )
    # A reference database is infrastructure even with no SIG-held sensor.
    reference_db = g.add_node(
        m.DataSystem(
            id="sys:hotlist-reference-db",
            system_scope=m.SystemScope.state,
            data_types=["hotlist"],
        )
    )
    patrol = g.add_node(
        m.DataSystem(
            id="sys:patrol-dispatch",
            system_scope=m.SystemScope.agency_local,
            data_types=["alerts"],
        )
    )

    # The hub pulls a continuous feed (data comes to rest in the hub).
    g.add_edge(
        m.IntegrationEdge(
            id="edge:hub-ingest",
            source="sys:citywide-rtcc-hub",
            target="sys:downtown-camera-network",
            edge_type=m.EdgeType.ingests_feed_from,
            data_kind="video",
            data_comes_to_rest=True,
        )
    )
    # The hub federates a query to a reference database (corpus stays there).
    g.add_edge(
        m.IntegrationEdge(
            id="edge:hub-federate",
            source="sys:citywide-rtcc-hub",
            target="sys:hotlist-reference-db",
            edge_type=m.EdgeType.federates_search_to,
            data_kind="hotlist_match",
            data_comes_to_rest=False,
        )
    )
    # The hub pushes discrete alerts (events, not the corpus) to dispatch.
    g.add_edge(
        m.IntegrationEdge(
            id="edge:hub-alert",
            source="sys:citywide-rtcc-hub",
            target="sys:patrol-dispatch",
            edge_type=m.EdgeType.pushes_alerts_to,
            data_kind="alert",
            granularity="event",
        )
    )

    _ = (hub, camera_network, reference_db, patrol)
    return g


def test_rtcc_hub_consumes_other_systems_via_directional_edges(
    rtcc_hub: Graph, tech_by_slug: dict, m: Any
) -> None:
    # Ticket deliverable 2 / SIG-ONTO-045/046: an integration hub that consumes
    # other systems is a DataSystem plus directional, typed integration edges —
    # never a stored `integrates_with`.
    g = rtcc_hub
    assert "rtcc-platform" in tech_by_slug
    assert "camera-federation-hub" in tech_by_slug

    kinds = {e.edge_type for e in g.edges}
    assert m.EdgeType.ingests_feed_from in kinds
    assert m.EdgeType.federates_search_to in kinds
    assert m.EdgeType.pushes_alerts_to in kinds

    # Every consumption edge originates at the hub (directional, not symmetric).
    assert all(e.source == "sys:citywide-rtcc-hub" for e in g.edges)
    # The three edges are discriminated by where the data ends up.
    ingest = next(e for e in g.edges if e.edge_type == m.EdgeType.ingests_feed_from)
    federate = next(e for e in g.edges if e.edge_type == m.EdgeType.federates_search_to)
    assert ingest.data_comes_to_rest is True
    assert federate.data_comes_to_rest is False


def test_reference_database_is_infrastructure_with_no_sensor(rtcc_hub: Graph, m: Any) -> None:
    # SIG-ONTO-031: a reference database is a DataSystem even where SIG holds no
    # sensor and it has no owned PhysicalAsset.
    refdb = rtcc_hub.nodes["sys:hotlist-reference-db"]
    assert isinstance(refdb, m.DataSystem)
    assert refdb.system_scope == m.SystemScope.state


def test_hub_stores_no_integrates_with(rtcc_hub: Graph, m: Any) -> None:
    assert not hasattr(m.EdgeType, "integrates_with")
    assert all(e.edge_type != "integrates_with" for e in rtcc_hub.edges)


# --- The commercial data-broker chain: six layers, not five ------------------


@pytest.fixture(scope="module")
def broker_chain(m: Any) -> Graph:
    """Appendix D.5 pathway 3 / R7 F7.29, populated as six *distinct*
    organizations. The aggregating broker and the productizing platform are
    different companies joined by `resells_data_from` — the layer the outline's
    five-step diagram collapses."""
    g = Graph()

    # Six institutional layers, each a distinct Organization (six, not five).
    app_publisher = g.add_node(m.Organization(id="org:app-publisher-sdk"))
    ad_exchange = g.add_node(m.Organization(id="org:ad-exchange-bidstream"))
    aggregating_broker = g.add_node(m.Organization(id="org:aggregating-broker"))
    productizer = g.add_node(m.Organization(id="org:productizing-platform"))
    investigative_host = g.add_node(m.Organization(id="org:investigative-platform-host"))
    department = g.add_node(m.Organization(id="org:county-sheriff"))

    def access(edge_id: str, src: str, tgt: str, edge_type: Any) -> Any:
        return m.AccessRelationship(
            id=edge_id,
            source=src,
            target=tgt,
            edge_type=edge_type,
            scope=m.CapabilityScope.commercial,
            direction=m.Direction.a_to_b,
            automaticity=m.Automaticity.automatic,
            access_kind=m.AccessKind.configured_access,
        )

    # The chain, from the agency down (Appendix D.5 pathway 3 edge sequence):
    # subscribes_to -> resells_data_from -> resells_data_from.
    g.add_edge(
        access(
            "edge:subscribes",
            "org:county-sheriff",
            "org:productizing-platform",
            m.EdgeType.subscribes_to,
        )
    )
    g.add_edge(
        access(
            "edge:resell-1",
            "org:productizing-platform",
            "org:aggregating-broker",
            m.EdgeType.resells_data_from,
        )
    )
    g.add_edge(
        access(
            "edge:resell-2",
            "org:aggregating-broker",
            "org:ad-exchange-bidstream",
            m.EdgeType.resells_data_from,
        )
    )
    # The two relationships that make it six layers, not four (R7 F7.29): the
    # productizer supplies the software surface the investigative host operates on.
    g.add_edge(
        access(
            "edge:host",
            "org:productizing-platform",
            "org:investigative-platform-host",
            m.EdgeType.provides_platform_to,
        )
    )
    g.add_edge(
        access(
            "edge:collect",
            "org:ad-exchange-bidstream",
            "org:app-publisher-sdk",
            m.EdgeType.resells_data_from,
        )
    )

    _ = (app_publisher, ad_exchange, aggregating_broker)
    _ = (productizer, investigative_host, department)
    return g


def test_broker_chain_has_six_distinct_layers(broker_chain: Graph) -> None:
    # AC2 / SIG-ONTO-046: six layers, not five.
    assert len(broker_chain.nodes) == 6
    assert len({n.id for n in broker_chain.nodes.values()}) == 6


def test_aggregator_and_productizer_are_distinct_organizations(broker_chain: Graph, m: Any) -> None:
    # AC2 / Appendix D.5 pathway 3: `resells_data_from` runs between the
    # productizing platform and the aggregating broker as SEPARATE organizations —
    # collapsing them would hide the institutional layer that turns an observation
    # into searchable power (§30.2).
    g = broker_chain
    resell = next(e for e in g.edges if e.id == "edge:resell-1")
    assert resell.edge_type == m.EdgeType.resells_data_from
    assert resell.source == "org:productizing-platform"
    assert resell.target == "org:aggregating-broker"
    assert resell.source != resell.target
    assert resell.source in g.nodes and resell.target in g.nodes


def test_broker_chain_edge_sequence_is_subscribes_then_two_resells(
    broker_chain: Graph, m: Any
) -> None:
    # The ticket's required sequence: subscribes_to -> resells_data_from ->
    # resells_data_from, each directional, scoped commercial, configured access.
    g = broker_chain
    sub = next(e for e in g.edges if e.id == "edge:subscribes")
    r1 = next(e for e in g.edges if e.id == "edge:resell-1")
    r2 = next(e for e in g.edges if e.id == "edge:resell-2")

    assert sub.edge_type == m.EdgeType.subscribes_to
    assert r1.edge_type == m.EdgeType.resells_data_from
    assert r2.edge_type == m.EdgeType.resells_data_from
    for e in (sub, r1, r2):
        assert e.direction == m.Direction.a_to_b
        assert e.scope == m.CapabilityScope.commercial
        assert e.access_kind == m.AccessKind.configured_access

    # The chain is transitive but not collapsible: the department subscribes to
    # the productizer, which is a different org from the broker it resells from.
    assert sub.target == r1.source
    assert r1.target == r2.source
    assert sub.target != r1.target


def test_broker_chain_technology_concepts_exist(tech_by_slug: dict) -> None:
    # SIG-CHART-027: the referenced §13.1 vocabulary concepts exist.
    assert "third-party-investigative-platform" in tech_by_slug
    assert "person-records-broker" in tech_by_slug
    assert "adtech-location-purchase" in tech_by_slug


# --- The no-schema-change proof / Phase-1-defect detector --------------------


def test_stage5_population_required_no_schema_change(
    private_camera_federation: Graph,
    rtcc_hub: Graph,
    broker_chain: Graph,
    tech_by_slug: dict,
    m: Any,
) -> None:
    """SIG-CHART-027/028 (AC1): every edge type, role, entity class, and
    technology slug the three Stage-5 pathways use already exists in the committed
    ontology. Populating them required NO new schema element.

    This is the deterministic Phase-1-defect detector: a Stage-5 construct that
    needed a new element would fail here, and per the Phase-17 acceptance gate
    that failure is recorded as a Phase-1 defect against the ontology (owned by
    P01.1) — never patched silently in this ticket.
    """
    all_edges = private_camera_federation.edges + rtcc_hub.edges + broker_chain.edges
    all_nodes = [
        *private_camera_federation.nodes.values(),
        *rtcc_hub.nodes.values(),
        *broker_chain.nodes.values(),
    ]

    # Every edge type used is a member of the committed closed catalog. (Enum
    # fields serialize to their string value under use_enum_values, so compare
    # on values throughout.)
    catalog = {t.value for t in m.EdgeType}
    assert {str(e.edge_type) for e in all_edges} <= catalog

    # Every role used is a member of the committed Role enum.
    role_enum = {r.value for r in m.Role}
    used_roles = {str(e.role) for e in all_edges if e.__class__.__name__ == "RoleAssignment"}
    assert used_roles <= role_enum
    # The load-bearing owner != operator separation is present in the vocabulary.
    assert {"owner", "operator"} <= role_enum

    # Every node is one of the committed entity classes (no new class was needed).
    committed_classes = {m.Organization, m.PhysicalAsset, m.DataSystem, m.Deployment}
    assert all(type(n) in committed_classes for n in all_nodes)

    # Every technology slug the pathways name is in the committed §13.1 tree.
    referenced_slugs = {
        "camera-fixed-cctv",
        "private-camera-registry",
        "private-camera-integration",
        "rtcc-platform",
        "camera-federation-hub",
        "third-party-investigative-platform",
        "person-records-broker",
        "adtech-location-purchase",
    }
    assert referenced_slugs <= set(tech_by_slug)
