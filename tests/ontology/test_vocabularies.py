# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The §13 controlled vocabularies as SKOS: counts, -unspecified leaves, the
capability grammar, stable per-version IRIs, and no vendor slugs."""

from __future__ import annotations

import json

import pytest
from support import VENDOR_TOKENS, generated_dir, load_vocab, slug_tokens

SALIENCE = {"L", "M", "H", "C"}


@pytest.fixture(scope="module")
def summary() -> dict:
    # SIG-ONTO-052a: counts are asserted against the generated artifact, not prose.
    return json.loads((generated_dir() / "registry" / "vocab_summary.json").read_text())


def test_technology_counts_are_14_36_104(summary: dict) -> None:
    # SIG-ONTO-052.
    assert summary["technology"]["counts"] == {"domains": 14, "families": 36, "technologies": 104}


def test_every_family_has_an_unspecified_leaf(summary: dict) -> None:
    # AC4 / SIG-ONTO-020/054.
    assert summary["technology"]["families_without_unspecified_leaf"] == []


def test_every_technology_carries_criterion_signature_and_salience() -> None:
    # SIG-ONTO-056.
    tech = load_vocab("technology")
    for dom in tech["domains"]:
        for fam in dom["families"]:
            for t in fam["technologies"]:
                assert t.get("distinguishing_criterion"), t["slug"]
                assert t.get("evidence_signature"), t["slug"]
                assert t.get("salience") in SALIENCE, t["slug"]


def test_capability_vocabulary_shape() -> None:
    # SIG-ONTO-023/024/060: ~45 verb.object.scope terms, six classes incl export/disclosure.
    cap = load_vocab("capability")
    caps = cap["capabilities"]
    assert len(caps) == 45
    slugs = [c["slug"] for c in caps]
    assert len(set(slugs)) == len(slugs)
    assert all(s.count(".") == 2 for s in slugs)  # verb.object.scope
    classes = {c["class"] for c in caps}
    assert "export_disclosure" in classes  # SIG-ONTO-024
    assert "governance" in classes
    assert any(c.get("negative") for c in caps)  # SIG-ONTO-025


def test_technology_slugs_are_stable_lowercase_hyphenated() -> None:
    # SIG-ONTO-053.
    tech = load_vocab("technology")
    for dom in tech["domains"]:
        for fam in dom["families"]:
            for t in fam["technologies"]:
                assert t["slug"] == t["slug"].lower()
                assert " " not in t["slug"]


def test_no_vendor_name_in_any_vocab_slug() -> None:
    # AC5 / SIG-ONTO-022/055: slugs encode family-discriminator, never a vendor.
    slugs: set[str] = set()
    tech = load_vocab("technology")
    for dom in tech["domains"]:
        slugs.add(dom["slug"])
        for fam in dom["families"]:
            slugs.add(fam["slug"])
            slugs.update(t["slug"] for t in fam["technologies"])
    slugs.update(c["slug"] for c in load_vocab("capability")["capabilities"])
    slugs.update(p["predicate_id"] for p in load_vocab("predicates")["predicates"])
    offenders = {s for s in slugs if slug_tokens(s) & VENDOR_TOKENS}
    assert not offenders, f"vendor token in vocab slug: {offenders}"


@pytest.mark.parametrize(
    "artifact,scheme_fragment",
    [
        ("technology.nt", "vocab/technology/1.0.0"),
        ("capability.nt", "vocab/capability/1.0.0"),
        ("predicate.nt", "vocab/predicate/1.0.0"),
    ],
)
def test_vocabularies_publish_at_stable_per_version_iris(
    artifact: str, scheme_fragment: str
) -> None:
    # AC6 / SIG-STORE-035: versioned SKOS concept schemes at stable per-version IRIs.
    from rdflib import Graph
    from rdflib.namespace import OWL, RDF, SKOS

    g = Graph()
    g.parse(generated_dir() / "skos" / artifact, format="nt")
    schemes = list(g.subjects(RDF.type, SKOS.ConceptScheme))
    assert schemes, artifact
    scheme = schemes[0]
    assert scheme_fragment in str(scheme)
    version_iris = list(g.objects(scheme, OWL.versionIRI))
    assert version_iris, f"no owl:versionIRI on {artifact}"
    assert scheme_fragment in str(version_iris[0])


def test_structural_vocabularies_are_published_as_skos() -> None:
    # §13 intro: ALL §13 vocabularies publish as versioned SKOS concept schemes —
    # incl. evidence/epistemics (§13.3), the four lifecycle tracks (§13.4), and
    # org/acquisition/role enums (§13.5), not just technology/capability/predicate.
    from rdflib import Graph, URIRef
    from rdflib.namespace import OWL, RDF, SKOS

    g = Graph()
    g.parse(generated_dir() / "skos" / "structural.nt", format="nt")
    schemes = {str(s) for s in g.subjects(RDF.type, SKOS.ConceptScheme)}
    for enum_name in (
        "EpistemicStatus",
        "ClaimDirectness",
        "PredicateVolatility",  # §13.3
        "ProcurementState",
        "PhysicalState",
        "OperationalState",
        "AuthorizationState",  # §13.4
        "OrganizationType",
        "AcquisitionMethod",
        "Role",  # §13.5
    ):
        iri = f"https://ontology.sig-project.org/vocab/{enum_name}/1.0.0"
        assert iri in schemes, enum_name
        assert list(g.objects(URIRef(iri), OWL.versionIRI)), enum_name
