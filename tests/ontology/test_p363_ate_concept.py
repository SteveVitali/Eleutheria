# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.3 (ACQ-03, ADR-207) — the ATE technology family and the declared
geometry kind.

The Round-11 wave-B plan's ACQ-10 rows are automated-traffic-enforcement
layers; they type records with the `ate-*` slugs — never the retired
`traffic_camera` blanket type — and declare zone/area-shaped records with
``geometry_kind="area"``. Both must be registered through the ontology so
the closed claim sink (P35.14a) accepts the emits:

* the ``ate`` family under ``surveillance-vehicle`` with six active leaves,
  each carrying the SIG-ONTO-056 triple (criterion, evidence signature,
  salience) and the SIG-ONTO-020 ``-unspecified`` leaf;
* the ``GeometryKind`` enum (``point`` | ``line`` | ``area``) in the
  generated schema and the ``geometry_kind`` predicate in the generated
  registry.
"""

from __future__ import annotations

import json

from support import generated_dir, load_vocab

from ontology import generate

_ATE_SLUGS = {
    "ate-red-light",
    "ate-speed",
    "ate-bus-lane",
    "ate-school-bus-stop-arm",
    "ate-work-zone",
    "ate-unspecified",
}
_SALIENCE = {"L", "M", "H", "C"}
_TECH_IRI = generate.TECH_SCHEME


def _ate_family(tech: dict) -> dict:
    for dom in tech["domains"]:
        if dom["slug"] == "surveillance-vehicle":
            for fam in dom["families"]:
                if fam["slug"] == "ate":
                    return fam
    raise AssertionError("the `ate` family is absent from surveillance-vehicle")


def test_ate_family_lives_under_surveillance_vehicle() -> None:
    fam = _ate_family(load_vocab("technology"))
    assert fam["label"] == "Automated traffic enforcement"


def test_ate_family_carries_exactly_the_five_subtypes_plus_unspecified() -> None:
    fam = _ate_family(load_vocab("technology"))
    slugs = {t["slug"] for t in fam["technologies"]}
    assert slugs == _ATE_SLUGS


def test_every_ate_leaf_carries_the_sig_onto_056_triple() -> None:
    fam = _ate_family(load_vocab("technology"))
    for t in fam["technologies"]:
        assert t.get("distinguishing_criterion"), t["slug"]
        assert t.get("evidence_signature"), t["slug"]
        assert t.get("salience") in _SALIENCE, t["slug"]


def test_ate_slugs_are_family_prefixed_and_non_vendor() -> None:
    # SIG-ONTO-022: the slug encodes the family discriminator, never a vendor.
    fam = _ate_family(load_vocab("technology"))
    for t in fam["technologies"]:
        assert t["slug"].startswith("ate-"), t["slug"]
        assert t["slug"] == t["slug"].lower()
        assert " " not in t["slug"]


def test_generated_skos_carries_the_ate_hierarchy() -> None:
    # The generated artifact, not the YAML, is what the closed sink and the
    # §13.1 count assertions read (SIG-ONTO-052a).
    from rdflib import Graph, URIRef
    from rdflib.namespace import RDF, SKOS

    g = Graph()
    g.parse(generated_dir() / "skos" / "technology.nt", format="nt")
    family = URIRef(f"{_TECH_IRI}/ate")
    domain = URIRef(f"{_TECH_IRI}/surveillance-vehicle")
    assert (family, RDF.type, SKOS.Concept) in g
    assert (family, SKOS.broader, domain) in g
    for slug in sorted(_ATE_SLUGS):
        leaf = URIRef(f"{_TECH_IRI}/{slug}")
        assert (leaf, RDF.type, SKOS.Concept) in g, slug
        assert (leaf, SKOS.broader, family) in g, slug
        assert list(g.objects(leaf, SKOS.definition)), slug
        assert list(g.objects(leaf, URIRef(f"{generate.SCHEMA_NS}evidenceSignature"))), slug


def test_geometry_kind_predicate_is_registered() -> None:
    # P36.4 emits ``geometry_kind="area"``; an unregistered id quarantines at
    # the closed sink (P35.14a), so registration is asserted, not assumed.
    registry = json.loads((generated_dir() / "registry" / "predicate_registry.json").read_text())
    by_id = {p["predicate_id"]: p for p in registry["predicates"]}
    assert "geometry_kind" in by_id
    row = by_id["geometry_kind"]
    assert row["cardinality"] == "single"
    # The authored assessment (ADR-207): the record's own published shape is
    # the registry's own fact; an unclassified pull stays descriptive.
    assert row["volatility_class"] == "SLOW"
    assert row["half_life"] == "2y"
    assert row["resolution_strategy"] == "authoritative_source_wins"
    assert set(row["directness"]) == set(registry["artifact_genres"])
    assert row["directness"]["camera_registry"] == "D1"
    assert row["directness"]["connector_run"] == "D3"


def test_geometry_kind_enum_membership_in_generated_schema() -> None:
    schema = json.loads((generated_dir() / "jsonschema" / "sig.schema.json").read_text())
    members = set(schema["$defs"]["GeometryKind"]["enum"])
    # `area` is the member a zone/programme-area record declares; `line` and
    # `point` cover the route- and device-shaped cases.
    assert members == {"point", "line", "area"}


def test_ate_never_reuses_the_deprecated_traffic_camera_type() -> None:
    # `traffic_camera` was the deprecated blanket *subject type* P36.3's
    # downstream tickets are forbidden to emit — it was never a technology
    # term and must never enter the scheme; every `ate-*` leaf is active.
    summary = json.loads((generated_dir() / "registry" / "vocab_summary.json").read_text())
    by_slug = {t["slug"]: t for t in summary["technology"]["technologies"]}
    assert "traffic_camera" not in by_slug
    for slug in _ATE_SLUGS:
        assert by_slug[slug]["status"] == "active", slug
