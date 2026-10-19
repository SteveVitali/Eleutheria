# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.30 — /network/ labels, dates and evidence (export side).

The draft SIG-EXPORT-D21 contract: every emitted edge carries the relation in
words (``predicate``/``relation``), the observed date AND its kind (a 1970
placeholder renders ``undated``, never a synthetic epoch — SIG-TIME-012 class
honesty), the source display names, the derived currency class, and the full
supporting claim ids. Nodes carry the P35.29 ``sig.entity-label/1`` label +
``label_basis`` (never a raw id — L-2/F-106/F-420), a source-stated partner
COUNT is a node ``degree`` attribute — never an edge (SIG-INGEST-043c) — and a
withheld/person-shaped endpoint is never a node (Part VIII, A-10/ADR-159).
"""

from __future__ import annotations

import json
from datetime import date

import jsonschema
from exports.manifest import BuildSpec
from exports.shaping import SharingEdge, build_shaped_dataset
from exports.spine_export import (
    _network,
    _network_evidence,
    _network_from_materialized,
    _NetworkEvidence,
    build_spine_export,
)
from policy.labels import EntityLabel
from test_spine_export import SCHEMA, _rows, _site, _sub

# Real-UUID endpoints — the entity/literal split keys on UUID-shape.
AGENCY = "11111111-1111-4111-8111-111111111111"
PARTNER = "22222222-2222-4222-8222-222222222222"
WITHHELD = "33333333-3333-4333-8333-333333333333"


def _label(
    entity_id: str,
    label: str | None,
    *,
    kind: str = "org",
    basis: str | None = "source_name",
    state: str | None = None,
    descriptor: str | None = None,
) -> EntityLabel:
    return EntityLabel(
        entity_id=entity_id,
        sig_id=None,
        kind=kind,
        url_type=None,
        label=label,
        descriptor=descriptor,
        label_basis=basis if label else None,
        label_source_id=None,
        place_jkey=None,
        slug=None,
        hash=None,
        url=None,
        disambiguator=None,
        component_id=None,
        part8="pass",
        label_state=state,
    )


def _edge(
    subject: str = AGENCY,
    predicate: str = "sharing_partner",
    partner: str | None = PARTNER,
    *,
    access: str = "configured_access",
    claim: str = "c1",
    source: str | None = "src_a",
    observed: str | None = "2026-05-01",
) -> SharingEdge:
    return SharingEdge(
        subject_id=subject,
        predicate_id=predicate,
        partner_ref=partner,
        access_kind=access,
        source_id=source,
        claim_id=claim,
        observed_at=observed,
    )


def _evidence(
    *,
    sources: dict[str, list[str]] | None = None,
    predicates: dict[str, str] | None = None,
    observed: dict[str, str] | None = None,
    lineage: dict[str, str] | None = None,
    as_of: str = "2026-09-22",
) -> _NetworkEvidence:
    raw = {
        "claim_weights": [
            (cid, src, (predicates or {}).get(cid), "W2", "D1", "I1", (observed or {}).get(cid))
            for cid, srcs in (sources or {}).items()
            for src in srcs
        ],
        "claim_lineage": sorted((lineage or {}).items()),
    }
    return _network_evidence(raw, as_of)


def _materialized_edge(**over):
    base = {
        "from_entity": AGENCY,
        "to_entity": PARTNER,
        "edge_type": "configured_access",
        "access_kind": "configured_access",
        "direction": "a_to_b",
        "valid_from_kind": "unknown",
        "valid_to_kind": "unknown",
        "asserted_by": "src_a",
        "valid_from": None,
        "evidence_claim": "c1",
        "relationship_id": "rel1",
        "observed_at": None,
        "valid_to": None,
    }
    base.update(over)
    return base


# --- node labels (L-2, F-106/F-420; ADR-159 typed states) ------------------ #


def test_node_labels_come_from_registry_never_ids() -> None:
    labels = {
        AGENCY: _label(AGENCY, "Oklahoma City PD", kind="agency"),
        PARTNER: _label(PARTNER, "Flock Safety"),
    }
    net = _network_from_materialized([_materialized_edge()], {}, labels)
    by_id = {n["id"]: n for n in net["nodes"]}
    assert by_id[AGENCY]["label"] == "Oklahoma City PD"
    assert by_id[AGENCY]["label_basis"] == "source_name"
    assert by_id[PARTNER]["label"] == "Flock Safety"
    # No node label is the raw entity id / a UUID (L-2 — the F-106 defect).
    for n in net["nodes"]:
        assert n["label"] != n["id"]
        assert len(n["label"]) < len(n["id"]) or not n["label"].startswith(n["id"][:8])


def test_fallback_node_label_is_typed_hash_never_id() -> None:
    net = _network_from_materialized([_materialized_edge()], {}, {})
    for n in net["nodes"]:
        assert n["label"] != n["id"]
        assert n["label"].startswith(("Record #", "Partner #"))
        assert n["label_basis"] == "fallback"


def test_not_yet_reviewed_org_renders_typed_state() -> None:
    labels = {
        PARTNER: _label(
            PARTNER, None, state="not_yet_reviewed", descriptor="Organisation · not yet reviewed"
        )
    }
    net = _network_from_materialized([_materialized_edge()], {}, labels)
    node = next(n for n in net["nodes"] if n["id"] == PARTNER)
    assert node["label"] == "Organisation · not yet reviewed"
    assert node["label_state"] == "not_yet_reviewed"


def test_withheld_endpoint_drops_edge_whole() -> None:
    labels = {PARTNER: _label(PARTNER, None, state="withheld")}
    net = _network_from_materialized([_materialized_edge()], {}, labels)
    assert net["edges"] == []
    assert PARTNER not in {n["id"] for n in net["nodes"]}


# --- edge evidence fields (D21) -------------------------------------------- #


def test_edge_carries_full_evidence_fields() -> None:
    evidence = _evidence(
        sources={"c1": ["src_a"], "c2": ["src_a", "src_b"]},
        predicates={"c1": "sharing_partner", "c2": "sharing_partner"},
        observed={"c1": "2026-05-01", "c2": "2026-06-15"},
        lineage={"c1": "records_audit", "c2": "procurement"},
    )
    sharing = [
        _edge(claim="c1", observed="2026-05-01"),
        _edge(claim="c2", observed="2026-06-15"),
    ]
    sources = {"src_a": "Oklahoma registry", "src_b": "County filings"}
    net = _network_from_materialized(
        [_materialized_edge()], sources, {}, sharing_edges=sharing, evidence=evidence
    )
    (edge,) = net["edges"]
    assert edge["predicate"] == "sharing partner"  # words, never the slot name
    assert edge["relation"] == "sharing partner"
    assert edge["direction"] == "a_to_b"
    assert edge["observed_at"] == "2026-05-01"  # earliest evidenced date
    assert edge["date_kind"] == "observed"
    assert edge["source"] == "County filings; Oklahoma registry"
    assert sorted(edge["sources"]) == ["County filings", "Oklahoma registry"]
    assert "src_a" not in (edge["source"] or "")  # never the raw id
    assert edge["claim_ids"] == ["c1", "c2"]
    assert edge["evidence"] == ["c1", "c2"]
    assert edge["evidence_count"] == 2
    # Two declared-independent classes is genuine corroboration — derived,
    # not the old constant floor.
    assert edge["support"] == "STRONGLY_SUPPORTED"
    assert edge["currency"] in {"CURRENT", "AGING", "STALE", "HISTORICAL"}
    assert edge["historical"] is False


def test_support_floor_when_lineage_undeclared() -> None:
    evidence = _evidence(lineage={"c1": "unclassified"})
    net = _network_from_materialized(
        [_materialized_edge()], {}, {}, sharing_edges=[_edge()], evidence=evidence
    )
    assert net["edges"][0]["support"] == "WEAKLY_SUPPORTED"


def test_undated_edge_is_explicit() -> None:
    net = _network_from_materialized(
        [_materialized_edge()], {}, {}, sharing_edges=[_edge(observed=None)]
    )
    (edge,) = net["edges"]
    assert edge["observed_at"] is None
    assert edge["date_kind"] == "undated"
    assert edge["currency"] == "UNDATED"  # uncomputable — stated, never guessed


def test_epoch_placeholder_renders_undated() -> None:
    """A spine-side 1970 placeholder is folded to `undated` — never a fake date
    (SIG-TIME-012; the backend repair is L3 CONF-06's, not this row's)."""
    net = _network_from_materialized(
        [_materialized_edge()], {}, {}, sharing_edges=[_edge(observed="1970-01-01")]
    )
    (edge,) = net["edges"]
    assert edge["observed_at"] is None
    assert edge["date_kind"] == "undated"
    assert "1970" not in json.dumps(edge)


def test_historical_edge_marked() -> None:
    ended = _materialized_edge(valid_to_kind="exact", valid_to="2025-06-30")
    net = _network_from_materialized([ended], {}, {}, sharing_edges=[_edge(observed="2023-04-11")])
    (edge,) = net["edges"]
    assert edge["valid_to"] == "2025-06-30"
    assert edge["valid_to_kind"] == "exact"
    assert edge["historical"] is True


def test_historical_currency_marks_edge() -> None:
    """A very old observation on a short-half-life predicate is C4 HISTORICAL —
    the edge marks historical even with no end bound."""
    net = _network_from_materialized(
        [_materialized_edge()],
        {},
        {},
        sharing_edges=[_edge(predicate="federal_sharing_enabled", observed="2020-01-01")],
        evidence=_network_evidence(
            {
                "claim_weights": [
                    ("c1", "src_a", "federal_sharing_enabled", "", "", "", "2020-01-01")
                ]
            },
            "2026-09-22",
        ),
    )
    (edge,) = net["edges"]
    assert edge["currency"] == "HISTORICAL"
    assert edge["historical"] is True


def test_currency_unweightable_predicate_is_honest_absence() -> None:
    """An unregistered predicate gives no currency class — `null`, not a guess."""
    net = _network_from_materialized(
        [_materialized_edge()],
        {},
        {},
        sharing_edges=[_edge(predicate="no_such_predicate_x", observed="2026-05-01")],
    )
    (edge,) = net["edges"]
    assert edge["currency"] is None


# --- the literal twin (K2 §2) and degree (H-4) ------------------------------ #


def test_literal_partner_is_person_screened_edge() -> None:
    sharing = [
        _edge(partner="Vigilant Solutions", observed="2026-03-01"),
        # A person-shaped literal: the §3.4 R-8 screen runs before any label or
        # node is made — the edge is withheld whole.
        _edge(partner="Sheriff John Smith", claim="c2", observed="2026-03-01"),
    ]
    net = _network_from_materialized([], {}, {}, sharing_edges=sharing)
    partners = {n["id"] for n in net["nodes"] if n["type"] == "partner"}
    assert partners == {"Vigilant Solutions"}
    assert len(net["edges"]) == 1
    assert net["edges"][0]["to"] == "Vigilant Solutions"
    assert "Sheriff John Smith" not in json.dumps(net)


def test_degree_is_node_attribute_never_edge() -> None:
    sharing = [
        _edge(predicate="sharing_partner_degree", partner="4", claim="d1", observed="2025-09-01"),
        _edge(),  # a real edge beside it
    ]
    net = _network_from_materialized([], {}, {}, sharing_edges=sharing)
    assert len(net["edges"]) == 1
    assert net["edges"][0]["to"] == PARTNER
    node = next(n for n in net["nodes"] if n["id"] == AGENCY)
    assert node["degree"] == 4
    assert node["degree_claim_ids"] == ["d1"]
    assert node["degree_observed_at"] == "2025-09-01"
    # No edge is ever drawn to a bare count.
    assert "4" not in {e["to"] for e in net["edges"]}


def test_untyped_access_kind_never_emitted() -> None:
    net = _network_from_materialized(
        [], {}, {}, sharing_edges=[_edge(partner=PARTNER, access="unclassified")]
    )
    assert net["edges"] == []


# --- path parity + determinism ---------------------------------------------- #


def _dataset(sharing: list[SharingEdge]):
    """A minimal ShapedDataset carrying exactly the sharing rows (fallback path)."""
    raw = {
        "shaping_claims": [],
        "subject_entities": [],
        "source_stats": [],
        "source_runs": [],
        "sharing_edges": [
            (e.claim_id, e.subject_id, e.predicate_id, e.partner_ref, e.source_id, e.observed_at)
            for e in sharing
        ],
        "spine_watermark": "claims=0",
    }
    return build_shaped_dataset(
        raw, as_of="2026-09-22", generated_at="2026-09-22T00:00:00Z", spine_label="unit"
    )


def test_fallback_path_emits_same_additive_fields() -> None:
    """The compute-on-read path and the materialized path emit the same D21
    field set — a claim-level edge just lacks the reconciled bound kinds."""
    sharing = [_edge()]
    evidence = _evidence(
        sources={"c1": ["src_a"]},
        predicates={"c1": "sharing_partner"},
        observed={"c1": "2026-05-01"},
    )
    via_claims = _network(_dataset(sharing), {"src_a": "Registry"}, {}, evidence=evidence)
    via_materialized = _network_from_materialized(
        [_materialized_edge()], {"src_a": "Registry"}, {}, sharing_edges=sharing, evidence=evidence
    )
    (a,) = via_claims["edges"]
    (b,) = via_materialized["edges"]
    for field_name in (
        "predicate",
        "relation",
        "observed_at",
        "date_kind",
        "source",
        "sources",
        "currency",
        "claim_ids",
        "evidence",
        "support",
    ):
        assert a[field_name] == b[field_name], field_name
    # The claim-level edge asserts no reconciled bounds — unknown, never inferred.
    assert a["valid_from_kind"] == "unknown"
    assert a["valid_to_kind"] == "unknown"
    # Same nodes, same additive node fields.
    assert {n["id"]: n["label"] for n in via_claims["nodes"]} == {
        n["id"]: n["label"] for n in via_materialized["nodes"]
    }


def test_output_is_deterministic() -> None:
    sharing = [_edge(claim="c2", observed="2026-06-01"), _edge(claim="c1", observed="2026-05-01")]
    a = json.dumps(_network(_dataset(sharing), {}, {}, evidence=_evidence()), sort_keys=True)
    b = json.dumps(
        _network(_dataset(list(reversed(sharing))), {}, {}, evidence=_evidence()), sort_keys=True
    )
    assert a == b


# --- the emitted artifact validates against the page's consumption contract -- #


def test_network_artifact_matches_public_contract_schema() -> None:
    """`web/network.json` over the shaping fallback validates the frozen P27.1
    surface schema (extended for D21) — the page's consumption contract."""
    sharing_rows = [
        ("c1", AGENCY, "sharing_partner", PARTNER, "src_a", date(2026, 5, 1)),
        ("d1", AGENCY, "sharing_partner_degree", "4", "src_a", date(2025, 9, 1)),
        ("c2", AGENCY, "sharing_partner", "Vigilant Solutions", "src_a", date(2026, 3, 1)),
    ]
    raw = {
        "sharing_edges": sharing_rows,
        "source_names": [("src_a", "Oklahoma registry")],
        "claim_weights": [("c1", "src_a", "sharing_partner", "W2", "D1", "I1", "2026-05-01")],
        "claim_lineage": [("c1", "records_audit")],
        "label_entities": [
            (AGENCY, "agency", "agency:okc", False, "Oklahoma City PD", False, "active"),
            (PARTNER, "org", "org:flock", False, "Flock Safety", False, "active"),
        ],
    }
    claims = _site(AGENCY, "35.46", "-97.51", "Oklahoma")
    ds_raw = dict(raw, shaping_claims=_rows(claims), subject_entities=[(AGENCY, "deployment")])
    dataset = build_shaped_dataset(
        ds_raw, as_of="2026-09-22", generated_at="2026-09-22T00:00:00Z", spine_label="unit"
    )
    export = build_spine_export(
        dataset,
        raw,
        build_spec=BuildSpec(
            as_of_snapshot=date(2026, 9, 22),
            as_of_belief=date(2026, 9, 22),
            ruleset_version="ruleset/1",
            resolver_version="resolver/1",
        ),
        generated_at="2026-09-22T00:00:00Z",
        claims=claims,
        entity_types={AGENCY: "deployment"},
    )
    network = json.loads(export.web_artifacts["web/network.json"].decode("utf-8"))
    jsonschema.validate(network, _sub(SCHEMA["properties"]["network"]))
    # Registry labels landed on the nodes; the degree claim became an attribute.
    labels = {n["id"]: n["label"] for n in network["nodes"]}
    assert labels[AGENCY] == "Oklahoma City PD"
    assert labels[PARTNER] == "Flock Safety"
    assert all(not n["label"].startswith(AGENCY[:8]) for n in network["nodes"])
    node = next(n for n in network["nodes"] if n["id"] == AGENCY)
    assert node["degree"] == 4
    # The literal partner joins the edge set (person-screened, labelled).
    literal = next(e for e in network["edges"] if e["to"] == "Vigilant Solutions")
    assert literal["date_kind"] == "observed"
    assert literal["source"] == "Oklahoma registry"
