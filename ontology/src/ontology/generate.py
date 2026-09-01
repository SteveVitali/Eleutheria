# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Generate every downstream artifact from the single ontology source (§20.1).

One LinkML source (``schema/sig.yaml``) plus the versioned vocabulary term lists
(``vocab/*.yaml``) generate: SQL DDL, JSON Schema, OWL, SHACL, Pydantic, and docs
(via the LinkML toolchain, ADR-007), and the SKOS concept schemes, the predicate
registry, and the external crosswalks (SIG-STORE-034/035, §13.6, §20.3).

The generation is **byte-deterministic** so the CI gate (SIG-ENG-016) can assert
committed artifacts equal a fresh generation:

* RDF (OWL/SHACL/SKOS) is emitted as **canonically-labelled, sorted N-Triples**
  (rdflib RDF-dataset canonicalization) — turtle/blank-node ordering is not
  stable, canonical sorted N-Triples is.
* LinkML metadata that embeds the source file's mtime/size is disabled
  (``metadata=False``) so a fresh checkout regenerates identical bytes.
"""

from __future__ import annotations

import json
import logging
import shutil
import tempfile
from importlib.resources import files
from pathlib import Path
from typing import Any

# --- Stable IRIs (per-version; SIG-STORE-035) --------------------------------
BASE = "https://ontology.sig-project.org/"
SCHEMA_NS = BASE + "schema/"
VOCAB_VERSION = "1.0.0"
TECH_SCHEME = f"{BASE}vocab/technology/{VOCAB_VERSION}"
CAP_SCHEME = f"{BASE}vocab/capability/{VOCAB_VERSION}"
PRED_SCHEME = f"{BASE}vocab/predicate/{VOCAB_VERSION}"
XWALK_NS = f"{BASE}vocab/crosswalk/{VOCAB_VERSION}/"

# Artifact tree, relative to the generated/ root.
ARTIFACTS = {
    "jsonschema": "jsonschema/sig.schema.json",
    "pydantic": "pydantic/sig_models.py",
    "sql": "sql/sig.sql",
    "owl": "owl/sig.owl.nt",
    "shacl": "shacl/sig.shacl.nt",
    "skos_technology": "skos/technology.nt",
    "skos_capability": "skos/capability.nt",
    "skos_predicate": "skos/predicate.nt",
    "skos_structural": "skos/structural.nt",
    "skos_crosswalks": "skos/crosswalks.nt",
    "predicate_registry": "registry/predicate_registry.json",
    "vocab_summary": "registry/vocab_summary.json",
    "docs_dir": "docs",
}


def _pkg_dir() -> Path:
    """The ontology package root (``ontology/``), sibling of ``src/``."""
    return Path(str(files("ontology"))).parents[1]


def schema_path() -> Path:
    return Path(str(files("ontology").joinpath("schema/sig.yaml")))


def vocab_dir() -> Path:
    return _pkg_dir() / "vocab"


def generated_dir() -> Path:
    return _pkg_dir() / "generated"


def _load_vocab(name: str) -> dict[str, Any]:
    import yaml

    with (vocab_dir() / f"{name}.yaml").open("rb") as fh:
        return yaml.safe_load(fh)


# --- RDF canonicalization -----------------------------------------------------
def _canonical_nt(graph: Any) -> str:
    """Canonically-labelled, sorted N-Triples — the deterministic RDF form."""
    from rdflib.compare import to_canonical_graph

    canonical = to_canonical_graph(graph)
    lines = sorted(ln for ln in canonical.serialize(format="nt").splitlines() if ln.strip())
    return "\n".join(lines) + "\n"


def _rdf_from_turtle(turtle: str) -> str:
    from rdflib import Graph

    g = Graph()
    g.parse(data=turtle, format="turtle")
    return _canonical_nt(g)


# --- LinkML generators (ADR-007) ---------------------------------------------
def _gen_jsonschema(schema: str) -> str:
    from linkml.generators.jsonschemagen import JsonSchemaGenerator

    return JsonSchemaGenerator(schema).serialize()


def _gen_pydantic(schema: str) -> str:
    from linkml.generators.pydanticgen import PydanticGenerator

    return _relativize_repo_paths(PydanticGenerator(schema).serialize())


def _relativize_repo_paths(text: str) -> str:
    """Rewrite the absolute schema path LinkML embeds as ``source_file`` metadata.

    ``PydanticGenerator`` records the schema's absolute ``source_file`` in the
    module's ``linkml_meta`` block, so the output otherwise carries the machine
    it was generated on (``/Users/...`` vs. the CI runner's ``/home/runner/...``)
    and the byte-for-byte generation gate (SIG-ENG-016) fails. Rewriting it to the
    stable repo-relative path makes the artifact byte-deterministic everywhere.
    """
    abs_schema = str(schema_path())
    rel_schema = schema_path().relative_to(_pkg_dir().parent).as_posix()
    return text.replace(abs_schema, rel_schema)


def _gen_sql(schema: str) -> str:
    from linkml.generators.sqltablegen import SQLTableGenerator

    return _sort_index_runs(SQLTableGenerator(schema).generate_ddl())


def _sort_index_runs(sql: str) -> str:
    """Sort each maximal run of consecutive ``CREATE INDEX`` statements.

    SQLAlchemy stores a table's indexes in an identity-hashed ``set``, so their
    emission order varies across processes regardless of ``PYTHONHASHSEED``. Index
    creation order is semantically irrelevant, so sorting each consecutive block
    of index statements makes the DDL byte-deterministic without touching table
    or column order.
    """
    lines = sql.splitlines()
    out: list[str] = []
    run: list[str] = []

    def flush() -> None:
        out.extend(sorted(run))
        run.clear()

    for line in lines:
        if line.startswith("CREATE INDEX "):
            run.append(line)
        else:
            if run:
                flush()
            out.append(line)
    if run:
        flush()
    return "\n".join(out) + ("\n" if sql.endswith("\n") else "")


def _gen_owl(schema: str) -> str:
    from linkml.generators.owlgen import OwlSchemaGenerator

    ttl = OwlSchemaGenerator(
        schema,
        format="ttl",
        metadata=False,
        mergeimports=True,
        skip_vacuous_min_zero_cardinality_axioms=True,
        skip_vacuous_local_range_axioms=True,
        consolidate_cardinality_axioms=True,
    ).serialize()
    return _rdf_from_turtle(ttl)


def _merged_schema_yaml(schema: str) -> str:
    """A single self-contained schema with imports inlined.

    ``ShaclGenerator``'s own ``mergeimports`` does not resolve cross-file slot
    references (it raises ``KeyError`` on the imported schema name), so we inline
    the imports first and hand it a flat schema.
    """
    from linkml.generators.linkmlgen import LinkmlGenerator

    return LinkmlGenerator(schema, format="yaml", mergeimports=True).serialize()


def _gen_shacl(schema: str) -> str:
    import tempfile as _tempfile

    from linkml.generators.shaclgen import ShaclGenerator

    with _tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=True) as fh:
        fh.write(_merged_schema_yaml(schema))
        fh.flush()
        ttl = ShaclGenerator(fh.name, metadata=False, mergeimports=False).serialize()
    return _rdf_from_turtle(ttl)


def _gen_docs(schema: str, out: Path) -> None:
    from linkml.generators.docgen import DocGenerator

    out.mkdir(parents=True, exist_ok=True)
    # subfolder_type_separation writes classes/, slots/, enums/, types/ into their
    # own subfolders. Without it, a class and an eponymous slot (e.g. Capability /
    # capability) both write docs/<name>.md — distinct paths only on a
    # case-sensitive filesystem. A dev on case-insensitive macOS then silently
    # commits one file per pair, and the case-sensitive CI runner regenerates both,
    # breaking the generation gate (SIG-ENG-016). Separate subfolders make the tree
    # identical on every filesystem.
    DocGenerator(
        schema,
        mergeimports=True,
        metadata=False,
        directory=str(out),
        subfolder_type_separation=True,
    ).serialize(directory=str(out))


# --- SKOS concept schemes (§13, §20.2) ---------------------------------------
def _skos_graph() -> Any:
    from rdflib import Graph, Namespace
    from rdflib.namespace import DCTERMS, OWL, RDF, SKOS

    g = Graph()
    g.bind("skos", SKOS)
    g.bind("dcterms", DCTERMS)
    g.bind("owl", OWL)
    g.bind("sig", Namespace(SCHEMA_NS))
    return g, RDF, SKOS, DCTERMS, OWL


def _add_scheme(g: Any, RDF: Any, SKOS: Any, DCTERMS: Any, OWL: Any, iri: str, title: str) -> Any:
    from rdflib import Literal, URIRef

    ref = URIRef(iri)
    g.add((ref, RDF.type, SKOS.ConceptScheme))
    g.add((ref, DCTERMS.title, Literal(title)))
    g.add((ref, OWL.versionInfo, Literal(VOCAB_VERSION)))
    g.add((ref, OWL.versionIRI, ref))  # stable per-version IRI (SIG-STORE-035)
    g.add((ref, DCTERMS.description, Literal("Immutable once published (SIG-STORE-036).")))
    return ref


def _sig(term: str) -> Any:
    from rdflib import URIRef

    return URIRef(SCHEMA_NS + term)


def build_technology_skos() -> str:
    from rdflib import Literal, URIRef

    g, RDF, SKOS, DCTERMS, OWL = _skos_graph()
    scheme = _add_scheme(g, RDF, SKOS, DCTERMS, OWL, TECH_SCHEME, "SIG technology vocabulary")
    data = _load_vocab("technology")

    def concept(slug: str, label: str, level: str) -> URIRef:
        ref = URIRef(f"{TECH_SCHEME}/{slug}")
        g.add((ref, RDF.type, SKOS.Concept))
        g.add((ref, SKOS.inScheme, scheme))
        g.add((ref, SKOS.prefLabel, Literal(label, lang="en")))
        g.add((ref, SKOS.notation, Literal(slug)))
        g.add((ref, _sig("hierarchyLevel"), Literal(level)))
        return ref

    for dom in data["domains"]:
        dref = concept(dom["slug"], dom["label"], "domain")
        g.add((dref, SKOS.topConceptOf, scheme))
        g.add((scheme, SKOS.hasTopConcept, dref))
        for fam in dom["families"]:
            fref = concept(fam["slug"], fam["label"], "family")
            g.add((fref, SKOS.broader, dref))
            for tech in fam["technologies"]:
                tref = concept(tech["slug"], tech["label"], "technology")
                g.add((tref, SKOS.broader, fref))
                g.add((tref, SKOS.definition, Literal(tech["distinguishing_criterion"])))
                g.add((tref, _sig("salience"), Literal(tech["salience"])))
                for sig_str in tech["evidence_signature"]:
                    g.add((tref, _sig("evidenceSignature"), Literal(sig_str)))
    return _canonical_nt(g)


def build_capability_skos() -> str:
    from rdflib import Literal, URIRef

    g, RDF, SKOS, DCTERMS, OWL = _skos_graph()
    scheme = _add_scheme(g, RDF, SKOS, DCTERMS, OWL, CAP_SCHEME, "SIG capability vocabulary")
    for cap in _load_vocab("capability")["capabilities"]:
        ref = URIRef(f"{CAP_SCHEME}/{cap['slug']}")
        g.add((ref, RDF.type, SKOS.Concept))
        g.add((ref, SKOS.inScheme, scheme))
        g.add((ref, SKOS.prefLabel, Literal(cap["label"], lang="en")))
        g.add((ref, SKOS.notation, Literal(cap["slug"])))
        g.add((ref, _sig("capabilityClass"), Literal(cap["class"])))
        g.add((ref, _sig("verb"), Literal(cap["verb"])))
        g.add((ref, _sig("object"), Literal(cap["object"])))
        g.add((ref, _sig("scope"), Literal(cap["scope"])))
        g.add((ref, _sig("salience"), Literal(cap["salience"])))
        if cap.get("negative"):
            g.add((ref, _sig("negative"), Literal(True)))
    return _canonical_nt(g)


def build_predicate_skos() -> str:
    from rdflib import Literal, URIRef

    g, RDF, SKOS, DCTERMS, OWL = _skos_graph()
    scheme = _add_scheme(g, RDF, SKOS, DCTERMS, OWL, PRED_SCHEME, "SIG predicate registry")
    for p in _load_vocab("predicates")["predicates"]:
        ref = URIRef(p["skos_concept_iri"])
        g.add((ref, RDF.type, SKOS.Concept))
        g.add((ref, SKOS.inScheme, scheme))
        g.add((ref, SKOS.prefLabel, Literal(p["predicate_id"], lang="en")))
        g.add((ref, SKOS.definition, Literal(p["definition"])))
        g.add((ref, _sig("volatilityClass"), Literal(p["volatility_class"])))
        g.add((ref, _sig("halfLife"), Literal(p["half_life"])))
        g.add((ref, _sig("resolutionStrategy"), Literal(p["resolution_strategy"])))
        g.add((ref, _sig("valueDatatype"), Literal(p["value_datatype"])))
        g.add((ref, _sig("cardinality"), Literal(p["cardinality"])))
    return _canonical_nt(g)


# The §13 structural vocabularies that MUST also publish as SKOS concept schemes
# (the §13 intro: "all vocabularies here are published as versioned SKOS concept
# schemes"). Each is authored once as a LinkML enum and generated to SKOS here.
STRUCTURAL_ENUMS: dict[str, tuple[str, ...]] = {
    # §13.3 evidence and epistemics
    "evidence_epistemics": (
        "SourceReliability",
        "ClaimDirectness",
        "ArtifactIntegrity",
        "ArtifactType",
        "Currency",
        "WeightClass",
        "EvidenceRole",
        "EpistemicStatus",
        "AbsenceKind",
        "ContradictionState",
        "ValueKind",
        "PredicateVolatility",
    ),
    # §13.4 the four orthogonal lifecycle tracks
    "lifecycle": (
        "ProcurementState",
        "PhysicalState",
        "OperationalState",
        "AuthorizationState",
    ),
    # §13.5 organization type, acquisition method, and the fourteen roles
    "org_acquisition_role": (
        "OrganizationType",
        "AcquisitionMethod",
        "AcquisitionChannel",
        "Role",
        "AccessKind",
        "JurisdictionType",
        "LegalInstrumentType",
    ),
}


def build_structural_skos() -> str:
    """SKOS concept schemes for the §13.3/§13.4/§13.5 structural vocabularies.

    One scheme per LinkML enum (its single source), at a stable per-version IRI.
    """
    from linkml_runtime import SchemaView
    from rdflib import Literal, URIRef

    g, RDF, SKOS, DCTERMS, OWL = _skos_graph()
    sv = SchemaView(str(schema_path()), merge_imports=True)
    for group, enum_names in STRUCTURAL_ENUMS.items():
        for enum_name in enum_names:
            enum = sv.get_enum(enum_name)
            scheme_iri = f"{BASE}vocab/{enum_name}/{VOCAB_VERSION}"
            scheme = _add_scheme(
                g, RDF, SKOS, DCTERMS, OWL, scheme_iri, f"SIG {enum_name} ({group})"
            )
            for pv_name, pv in enum.permissible_values.items():
                ref = URIRef(f"{scheme_iri}/{pv_name}")
                g.add((ref, RDF.type, SKOS.Concept))
                g.add((ref, SKOS.inScheme, scheme))
                g.add((ref, SKOS.topConceptOf, scheme))
                g.add((scheme, SKOS.hasTopConcept, ref))
                g.add((ref, SKOS.prefLabel, Literal(pv_name, lang="en")))
                g.add((ref, SKOS.notation, Literal(pv_name)))
                if pv.description:
                    g.add((ref, SKOS.definition, Literal(pv.description)))
    return _canonical_nt(g)


def build_crosswalks_skos() -> str:
    import hashlib

    from rdflib import Literal, URIRef

    g, RDF, SKOS, DCTERMS, OWL = _skos_graph()
    data = _load_vocab("crosswalks")
    for row in data["crosswalks"]:
        sig_ref = URIRef(f"{TECH_SCHEME}/{row['sig_concept']}")
        digest = hashlib.sha256(row["external_concept"].encode()).hexdigest()[:12]
        ext_ref = URIRef(f"{XWALK_NS}{row['taxonomy']}/{digest}")
        g.add((ext_ref, RDF.type, SKOS.Concept))
        g.add((ext_ref, SKOS.prefLabel, Literal(row["external_concept"])))
        g.add((ext_ref, _sig("taxonomy"), Literal(row["taxonomy"])))
        g.add((sig_ref, SKOS[row["relation"]], ext_ref))
        g.add((ext_ref, _sig("lossy"), Literal(bool(row["lossy"]))))
    return _canonical_nt(g)


# --- Predicate registry + vocab summary (deterministic JSON) -----------------
def build_predicate_registry() -> str:
    data = _load_vocab("predicates")
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _vocab_summary_dict() -> dict[str, Any]:
    """The falsifiable count/field artifact the acceptance suite asserts against.

    (SIG-ONTO-052a: counts asserted in prose but not checked against an artifact
    are unfalsifiable.)
    """
    tech = _load_vocab("technology")
    cap = _load_vocab("capability")
    pred = _load_vocab("predicates")
    families = [f for d in tech["domains"] for f in d["families"]]
    technologies = [t for f in families for t in f["technologies"]]
    return {
        "version": VOCAB_VERSION,
        "technology": {
            "scheme_iri": TECH_SCHEME,
            "counts": {
                "domains": len(tech["domains"]),
                "families": len(families),
                "technologies": len(technologies),
            },
            "families_without_unspecified_leaf": sorted(
                f["slug"]
                for f in families
                if not any(t["slug"].endswith("-unspecified") for t in f["technologies"])
            ),
            "technologies": sorted(
                (
                    {
                        "slug": t["slug"],
                        "salience": t["salience"],
                        "has_distinguishing_criterion": bool(t.get("distinguishing_criterion")),
                        "has_evidence_signature": bool(t.get("evidence_signature")),
                    }
                    for t in technologies
                ),
                key=lambda r: r["slug"],
            ),
        },
        "capability": {
            "scheme_iri": CAP_SCHEME,
            "count": len(cap["capabilities"]),
            "classes": sorted({c["class"] for c in cap["capabilities"]}),
            "slugs": sorted(c["slug"] for c in cap["capabilities"]),
        },
        "predicate": {
            "scheme_iri": PRED_SCHEME,
            "count": len(pred["predicates"]),
            "artifact_genres": pred["artifact_genres"],
            "ids": sorted(p["predicate_id"] for p in pred["predicates"]),
        },
    }


def build_vocab_summary_json() -> str:
    return json.dumps(_vocab_summary_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


# --- Orchestration ------------------------------------------------------------
def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def generate_into(root: Path) -> None:
    """Write the full generated-artifact tree under ``root``."""
    logging.getLogger("linkml").setLevel(logging.ERROR)
    schema = str(schema_path())
    _write(root / ARTIFACTS["jsonschema"], _gen_jsonschema(schema))
    _write(root / ARTIFACTS["pydantic"], _gen_pydantic(schema))
    _write(root / ARTIFACTS["sql"], _gen_sql(schema))
    _write(root / ARTIFACTS["owl"], _gen_owl(schema))
    _write(root / ARTIFACTS["shacl"], _gen_shacl(schema))
    _write(root / ARTIFACTS["skos_technology"], build_technology_skos())
    _write(root / ARTIFACTS["skos_capability"], build_capability_skos())
    _write(root / ARTIFACTS["skos_predicate"], build_predicate_skos())
    _write(root / ARTIFACTS["skos_structural"], build_structural_skos())
    _write(root / ARTIFACTS["skos_crosswalks"], build_crosswalks_skos())
    _write(root / ARTIFACTS["predicate_registry"], build_predicate_registry())
    _write(root / ARTIFACTS["vocab_summary"], build_vocab_summary_json())
    docs = root / ARTIFACTS["docs_dir"]
    if docs.exists():
        shutil.rmtree(docs)
    _gen_docs(schema, docs)


def generate(check: bool = False) -> int:
    """Regenerate artifacts (``check=False``) or verify they are up to date.

    Returns a process exit code. ``check`` generates into a temp tree and diffs it
    against the committed ``generated/`` tree without touching the working copy.
    """
    target = generated_dir()
    if not check:
        if target.exists():
            shutil.rmtree(target)
        generate_into(target)
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / "generated"
        generate_into(fresh)
        drift = _diff_trees(target, fresh)
    if drift:
        for line in drift:
            print(line)
        return 1
    return 0


def _diff_trees(committed: Path, fresh: Path) -> list[str]:
    def rel_files(base: Path) -> set[str]:
        return {
            str(p.relative_to(base))
            for p in base.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        }

    drift: list[str] = []
    committed_files = rel_files(committed) if committed.exists() else set()
    fresh_files = rel_files(fresh)
    for missing in sorted(fresh_files - committed_files):
        drift.append(f"missing committed artifact: {missing}")
    for extra in sorted(committed_files - fresh_files):
        drift.append(f"stale committed artifact: {extra}")
    for shared in sorted(committed_files & fresh_files):
        if (committed / shared).read_bytes() != (fresh / shared).read_bytes():
            drift.append(f"artifact differs from a fresh generation: {shared}")
    return drift
