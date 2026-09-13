# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Phase 17 (P17.2): facial recognition, cell-site simulators, and mobile-device
forensics — populated with **no schema change**.

This continues the standing proof of §5.2 that P17.1 began: the schema frozen in
Phase 2/4 must absorb a Stage-5 technology span with no change
(SIG-CHART-027/028). Each construct is *populated* as an instance graph over the
committed generated Pydantic model (a real downstream form) and the committed
§13.1/§13.2 vocabularies, proving it is expressible with today's ontology. If a
construct ever required a new capability slug, edge type, technology slug, entity
class, or lifecycle state, ``test_stage5_forensics_required_no_schema_change``
fails — that red result is the Phase-1 defect the acceptance gate demands be
*recorded, not patched here* (the LinkML source is owned by P01.1).

Constructs proven (ticket deliverables 1–5):

1. **Facial recognition** — a ``Capability`` (``search.face.*``, SIG-ONTO-023)
   that searches against a reference **DataSystem** (an image/reference gallery)
   with no locally owned sensor (SIG-ONTO-031). The §11.10 illustration
   ``… facial recognition system --searches_against--> image/reference database``
   is realised in the closed §12 catalog as ``federates_search_to`` — the query
   moves, the gallery corpus stays put. No ``Person`` row is minted for the faces
   in the gallery (§11.3, §43.4).
2. **Cell-site simulators** and **mobile-device forensics** — ``Deployment``\\s
   with **no product, no vendor, and no physical asset** (SIG-ONTO-026): a
   capability with no roadside device. Capability slugs ``locate.handset.rf``,
   ``extract.device.logical/physical``, ``extract.cloud.account`` (SIG-ONTO-023).
   No ``Person`` row is minted for extracted individuals.
3. **Non-camera / no-physical-asset representation** — none of the three is
   forced into a camera or generic-asset abstraction (SIG-ONTO-026/027/031): the
   sensing systems are ``DataSystem``\\s, not ``PhysicalAsset``\\s, and no node
   carries a ``camera-*`` ``asset_type``.
4. **Federal authorization datasets** — an ingested authorization populates
   ``authorization_state`` (§13.4 track 4) and carries its **native validity
   interval** encoded as EDTF (on the Deployment and on a linked
   ``LegalInstrument``), never coerced to a fabricated point value.
5. The **no-schema-change proof** is the deterministic Phase-1-defect detector.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from db.edtf import EdtfInterval, derive_envelope, parse_edtf
from support import load_generated_pydantic, load_vocab


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


# --- Deliverable 1: facial recognition against a reference gallery ------------


@pytest.fixture(scope="module")
def face_recognition(m: Any) -> Graph:
    """FR populated as a ``Capability`` searching a reference ``DataSystem`` with
    no locally owned sensor. The agency runs an FR system (a DataSystem, not a
    camera); that system ``federates_search_to`` a state DMV image gallery — the
    query moves, the gallery corpus stays put. No ``Person`` row is created for
    the faces enrolled in the gallery."""
    g = Graph()

    g.add_node(m.Organization(id="org:state-police"))

    # The capability itself, in verb.object.scope grammar (SIG-ONTO-023).
    g.add_node(
        m.Capability(
            id="cap:search-face-state",
            capability="search.face.state",
            scope=m.CapabilityScope.state,
        )
    )

    # The FR matching system — a DataSystem, NOT a PhysicalAsset/camera. The
    # agency holds no sensor of its own here (SIG-ONTO-031).
    g.add_node(
        m.DataSystem(
            id="sys:fr-matcher",
            operator="org:state-police",
            system_scope=m.SystemScope.agency_local,
            data_types=["face_probe"],
        )
    )
    # The reference gallery is infrastructure even though SIG holds no sensor and
    # it owns no PhysicalAsset (SIG-ONTO-031). It is a DMV image corpus.
    g.add_node(
        m.DataSystem(
            id="sys:dmv-image-gallery",
            system_scope=m.SystemScope.state,
            data_types=["face_gallery"],
        )
    )

    # The deployment: FR adopted by the agency, evidenced by the capability it
    # provides, with NO product, NO vendor, and NO physical asset (SIG-ONTO-026).
    g.add_node(
        m.Deployment(
            id="dep:fr-state-police",
            deploying_organization="org:state-police",
            technology=["face-identification-1ton"],
            actually_provides_capability=["search.face.state"],
        )
    )

    # §11.10's `searches_against` is realised in the closed §12 catalog as
    # `federates_search_to`: the FR system queries the gallery, the corpus stays
    # with the gallery (data does not come to rest at the matcher).
    g.add_edge(
        m.IntegrationEdge(
            id="edge:fr-search-gallery",
            source="sys:fr-matcher",
            target="sys:dmv-image-gallery",
            edge_type=m.EdgeType.federates_search_to,
            data_kind="face_template_match",
            data_comes_to_rest=False,
        )
    )
    return g


def test_face_recognition_is_a_capability_searching_a_reference_datasystem(
    face_recognition: Graph, capability_slugs: set, tech_by_slug: dict, m: Any
) -> None:
    # Deliverable 1 / SIG-ONTO-023/031 / AC2: FR is a verb.object.scope Capability
    # that resolves to a reference DataSystem gallery via federates_search_to.
    g = face_recognition
    cap = g.nodes["cap:search-face-state"]
    assert cap.capability == "search.face.state"
    assert cap.capability in capability_slugs
    # verb.object.scope grammar (SIG-ONTO-023): exactly three dotted parts.
    assert len(cap.capability.split(".")) == 3

    # The FR family lives under the biometric-id domain, not a camera domain.
    assert tech_by_slug["face-identification-1ton"]["domain"] == "biometric-id"

    # The search resolves to a reference DataSystem; the corpus stays with it.
    gallery = g.nodes["sys:dmv-image-gallery"]
    assert isinstance(gallery, m.DataSystem)
    search = next(e for e in g.edges if e.id == "edge:fr-search-gallery")
    assert search.edge_type == m.EdgeType.federates_search_to
    assert search.target == gallery.id
    assert search.data_comes_to_rest is False


def test_face_recognition_has_no_locally_owned_sensor(face_recognition: Graph, m: Any) -> None:
    # SIG-ONTO-026/031 / AC2: FR is a Deployment + DataSystems with NO product, NO
    # vendor, and NO PhysicalAsset — the agency owns no sensor for this capability.
    g = face_recognition
    dep = g.nodes["dep:fr-state-police"]
    assert dep.product is None
    assert dep.vendor is None
    # No PhysicalAsset was needed to express FR at all.
    assert not any(isinstance(n, m.PhysicalAsset) for n in g.nodes.values())


# --- Deliverable 2: cell-site simulators + mobile-device forensics ------------


@pytest.fixture(scope="module")
def css_and_forensics(m: Any) -> Graph:
    """Cell-site simulation and mobile-device extraction populated as Deployments
    with **no product, no vendor, and no physical asset** — a capability with no
    roadside device (SIG-ONTO-026). No Person row is minted for the individuals
    whose handsets are located or whose devices are extracted (§11.3, §43.4)."""
    g = Graph()

    g.add_node(m.Organization(id="org:county-sheriff"))

    # Cell-site simulator: a comms-intercept capability with no owned roadside
    # device. It locates handsets by RF (locate.handset.rf).
    g.add_node(
        m.Capability(
            id="cap:locate-handset-rf",
            capability="locate.handset.rf",
            scope=m.CapabilityScope.subject,
        )
    )
    g.add_node(
        m.Deployment(
            id="dep:css-county",
            deploying_organization="org:county-sheriff",
            technology=["cell-site-simulator-general"],
            actually_provides_capability=["locate.handset.rf"],
        )
    )

    # Mobile-device forensics: logical + physical + cloud-account extraction.
    for cap_slug, node_id in (
        ("extract.device.logical", "cap:extract-device-logical"),
        ("extract.device.physical", "cap:extract-device-physical"),
        ("extract.cloud.account", "cap:extract-cloud-account"),
    ):
        g.add_node(
            m.Capability(
                id=node_id,
                capability=cap_slug,
                scope=m.CapabilityScope.subject,
            )
        )
    g.add_node(
        m.Deployment(
            id="dep:forensics-county",
            deploying_organization="org:county-sheriff",
            technology=["extraction-logical", "extraction-physical", "cloud-account-extraction"],
            actually_provides_capability=[
                "extract.device.logical",
                "extract.device.physical",
                "extract.cloud.account",
            ],
        )
    )
    return g


def test_css_and_forensics_are_deployments_with_no_product_vendor_or_asset(
    css_and_forensics: Graph, m: Any
) -> None:
    # Deliverable 2 / SIG-ONTO-026 / AC2: both are Deployments with NO product, NO
    # vendor, and NO PhysicalAsset — a capability with no roadside device.
    g = css_and_forensics
    for dep_id in ("dep:css-county", "dep:forensics-county"):
        dep = g.nodes[dep_id]
        assert isinstance(dep, m.Deployment)
        assert dep.product is None
        assert dep.vendor is None
    # Not a single PhysicalAsset was needed for either.
    assert not any(isinstance(n, m.PhysicalAsset) for n in g.nodes.values())


def test_css_and_forensics_capability_slugs_follow_the_grammar(
    css_and_forensics: Graph, capability_slugs: set, tech_by_slug: dict
) -> None:
    # SIG-ONTO-023: every capability slug used is a committed verb.object.scope
    # slug; the technologies live under comms-intercept / device-forensics, never
    # a camera domain.
    g = css_and_forensics
    used = {n.capability for n in g.nodes.values() if n.__class__.__name__ == "Capability"}
    assert used == {
        "locate.handset.rf",
        "extract.device.logical",
        "extract.device.physical",
        "extract.cloud.account",
    }
    assert used <= capability_slugs
    for slug in used:
        assert len(slug.split(".")) == 3

    assert tech_by_slug["cell-site-simulator-general"]["domain"] == "comms-intercept"
    for slug in ("extraction-logical", "extraction-physical", "cloud-account-extraction"):
        assert tech_by_slug[slug]["domain"] == "device-forensics"


# --- Deliverable 3: no camera / no generic-asset abstraction is forced --------


def test_no_construct_is_forced_into_a_camera_abstraction(
    face_recognition: Graph, css_and_forensics: Graph, m: Any
) -> None:
    # Deliverable 3 / SIG-ONTO-026/027/031 / AC2: none of FR, CSS, or forensics is
    # represented as a camera. The sensing systems are DataSystems (or nothing),
    # never a PhysicalAsset, and no node carries a camera asset_type.
    all_nodes = [*face_recognition.nodes.values(), *css_and_forensics.nodes.values()]
    assets = [n for n in all_nodes if isinstance(n, m.PhysicalAsset)]
    assert assets == []  # no physical asset at all — nothing to coerce
    for n in all_nodes:
        atype = getattr(n, "asset_type", None)
        assert atype is None or "camera" not in atype


# --- Deliverable 4: federal authorization → authorization_state + EDTF interval


@pytest.fixture(scope="module")
def federal_authorization(m: Any) -> Graph:
    """A federal authorization dataset populates the Deployment's track-4
    ``authorization_state`` and carries its **native validity interval** as EDTF —
    on the Deployment (``authorizes`` edge bounds) and on a linked
    ``LegalInstrument`` (``effective_from``/``effective_to``). A federal court
    order authorises a county cell-site simulator for a fixed window; the window
    is preserved verbatim, never collapsed to a single date."""
    g = Graph()

    # The authorization's native validity interval, exactly as the source states
    # it (a 60-day federal order). Two distinct EDTF endpoints — never one point.
    valid_from = "2024-03-01"
    valid_to = "2024-04-30"

    g.add_node(m.Organization(id="org:us-district-court"))
    g.add_node(
        m.Deployment(
            id="dep:css-authorized",
            deploying_organization="org:county-sheriff",
            technology=["cell-site-simulator-general"],
            authorization_state=m.AuthorizationState.authorized,
        )
    )
    g.add_node(
        m.LegalInstrument(
            id="law:css-court-order-2024",
            instrument_type=m.LegalInstrumentType.court_order,
            enacting_body="org:us-district-court",
            citation="No. 1:24-mj-00123",
            effective_from=valid_from,
            effective_to=valid_to,
            constrains_capability=["locate.handset.rf"],
        )
    )
    # `authorizes`: A grants B legal permission to operate a capability; no data
    # moves (a StructuralEdge). The edge carries the same native validity window.
    g.add_edge(
        m.StructuralEdge(
            id="edge:authorizes-css",
            source="law:css-court-order-2024",
            target="dep:css-authorized",
            edge_type=m.EdgeType.authorizes,
            valid_from=valid_from,
            valid_to=valid_to,
            valid_from_kind=m.TemporalBoundKind.known,
            valid_to_kind=m.TemporalBoundKind.known,
        )
    )
    return g


def test_federal_authorization_populates_track4_authorization_state(
    federal_authorization: Graph, m: Any
) -> None:
    # Deliverable 4 / §13.4 track 4 / AC3: the ingested authorization sets the
    # Deployment's authorization_state to a valid track-4 value.
    dep = federal_authorization.nodes["dep:css-authorized"]
    assert dep.authorization_state == m.AuthorizationState.authorized
    assert dep.authorization_state in {s.value for s in m.AuthorizationState}


def test_authorization_carries_native_validity_interval_not_a_point(
    federal_authorization: Graph, m: Any
) -> None:
    # Deliverable 4 / AC3: the validity interval is preserved as a genuine EDTF
    # interval with two distinct bounds — never coerced to a fabricated point.
    g = federal_authorization
    law = g.nodes["law:css-court-order-2024"]
    edge = next(e for e in g.edges if e.id == "edge:authorizes-css")

    # The edge authorises the deployment (permission, not a data flow).
    assert edge.edge_type == m.EdgeType.authorizes
    assert edge.target == "dep:css-authorized"

    # The interval, spelled as EDTF, parses as an INTERVAL (two ends), not a
    # single date. A coerced point would parse as an EdtfDate and fail here.
    for lo, hi in ((law.effective_from, law.effective_to), (edge.valid_from, edge.valid_to)):
        interval = parse_edtf(f"{lo}/{hi}")
        assert isinstance(interval, EdtfInterval)
        assert interval.start is not None and interval.end is not None
        # The two bounds are genuinely distinct — the window was not flattened.
        env = derive_envelope(f"{lo}/{hi}")
        assert env.lower is not None and env.upper is not None
        assert env.lower < env.upper

    # A single endpoint, on its own, is only a point — proof the interval carries
    # strictly more information than any coercion to a date would retain.
    assert not isinstance(parse_edtf(law.effective_from), EdtfInterval)


# --- Person guard (§11.3, §43.4): no Person row for observed individuals -------


def test_no_person_rows_are_minted_for_observed_individuals(
    face_recognition: Graph, css_and_forensics: Graph, federal_authorization: Graph, m: Any
) -> None:
    # §11.3 / §43.4: FR reference galleries and forensic extractions MUST NOT mint
    # Person rows for the individuals they observe. None of the graphs contain one.
    all_nodes = [
        *face_recognition.nodes.values(),
        *css_and_forensics.nodes.values(),
        *federal_authorization.nodes.values(),
    ]
    assert not any(isinstance(n, m.Person) for n in all_nodes)


# --- Deliverable 5: the no-schema-change proof / Phase-1-defect detector -------


def test_stage5_forensics_required_no_schema_change(
    face_recognition: Graph,
    css_and_forensics: Graph,
    federal_authorization: Graph,
    tech_by_slug: dict,
    capability_slugs: set,
    m: Any,
) -> None:
    """SIG-CHART-027/028 (AC1): every capability slug, edge type, entity class,
    technology slug, and lifecycle state the three Stage-5 constructs use already
    exists in the committed ontology. Populating them required NO new schema
    element.

    This is the deterministic Phase-1-defect detector: a construct that needed a
    new element would fail here, and per the Phase-17 acceptance gate that failure
    is recorded as a Phase-1 defect against the ontology (owned by P01.1) — never
    patched silently in this ticket.
    """
    graphs = (face_recognition, css_and_forensics, federal_authorization)
    all_edges = [e for g in graphs for e in g.edges]
    all_nodes = [n for g in graphs for n in g.nodes.values()]

    # Every edge type used is a member of the committed closed catalog. (Enum
    # fields serialize to their string value under use_enum_values.)
    catalog = {t.value for t in m.EdgeType}
    assert {str(e.edge_type) for e in all_edges} <= catalog

    # Every capability slug used is in the committed §13.2 vocabulary.
    used_caps = {n.capability for n in all_nodes if n.__class__.__name__ == "Capability"}
    assert used_caps <= capability_slugs

    # Every node is one of the committed entity classes (no new class was needed).
    committed_classes = {
        m.Organization,
        m.Capability,
        m.Deployment,
        m.DataSystem,
        m.LegalInstrument,
    }
    assert all(type(n) in committed_classes for n in all_nodes)

    # Every technology slug the constructs name is in the committed §13.1 tree.
    referenced_slugs = {
        "face-identification-1ton",
        "cell-site-simulator-general",
        "extraction-logical",
        "extraction-physical",
        "cloud-account-extraction",
    }
    assert referenced_slugs <= set(tech_by_slug)

    # Every lifecycle / legal-instrument value used is a committed enum member.
    assert {"authorized"} <= {s.value for s in m.AuthorizationState}
    assert m.LegalInstrumentType.court_order.value in {t.value for t in m.LegalInstrumentType}
