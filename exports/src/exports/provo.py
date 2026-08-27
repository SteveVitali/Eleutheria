# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""PROV-O export over the ingest-run lineage (§21.6, SIG-INGEST-015/016).

Every claim is traceable to its `ingest_run` (SIG-INGEST-015). SIG-INGEST-016
requires that lineage map onto **PROV-O** for interoperable export, with a fixed
correspondence:

* captures and claims        -> `prov:Entity`
* runs and extractions       -> `prov:Activity`
* connectors, curators, and
  sources                    -> `prov:Agent`
* `revises_claim`            -> `prov:wasRevisionOf`

The wiring between them follows PROV's own vocabulary: a claim
`prov:wasGeneratedBy` its extraction, which `prov:used` the capture it parsed and
was `prov:wasAssociatedWith` the connector; a capture `prov:wasAttributedTo` its
source and `prov:wasGeneratedBy` the run; a human-asserted claim
`prov:wasAttributedTo` the curator. The export is built with rdflib (already a
project dependency via `ontology`) and serialises deterministically so a release
artifact is byte-stable and diffable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from rdflib import PROV, RDF, XSD, Graph, Literal, Namespace, URIRef

# The base namespace SIG mints lineage URIs under. Stable and dereferenceable-shaped.
SIG = Namespace("https://sig-project.org/prov/")


# --- lineage input (a thin, DB-agnostic projection of the lineage rows) -------


@dataclass(frozen=True)
class Source:
    source_id: str
    name: str | None = None


@dataclass(frozen=True)
class Connector:
    name: str
    version: str | None = None


@dataclass(frozen=True)
class Curator:
    curator_id: str
    name: str | None = None


@dataclass(frozen=True)
class IngestRun:
    run_id: str
    connector_name: str
    connector_version: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass(frozen=True)
class Extraction:
    extraction_id: str
    run_id: str
    capture_id: str | None = None
    connector_name: str | None = None


@dataclass(frozen=True)
class Capture:
    capture_id: str
    source_id: str | None = None
    run_id: str | None = None
    retrieved_at: datetime | None = None


@dataclass(frozen=True)
class Claim:
    claim_id: str
    extraction_id: str | None = None
    run_id: str | None = None
    revises_claim_id: str | None = None
    asserted_by_curator_id: str | None = None
    recorded_at: datetime | None = None


@dataclass
class Lineage:
    """A batch of lineage rows to export as one PROV-O document."""

    sources: list[Source] = field(default_factory=list)
    connectors: list[Connector] = field(default_factory=list)
    curators: list[Curator] = field(default_factory=list)
    runs: list[IngestRun] = field(default_factory=list)
    extractions: list[Extraction] = field(default_factory=list)
    captures: list[Capture] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)


# --- URI minting --------------------------------------------------------------


def _uri(kind: str, ident: str) -> URIRef:
    return SIG[f"{kind}/{ident}"]


def claim_uri(claim_id: str) -> URIRef:
    return _uri("claim", claim_id)


def capture_uri(capture_id: str) -> URIRef:
    return _uri("capture", capture_id)


def run_uri(run_id: str) -> URIRef:
    return _uri("run", run_id)


def extraction_uri(extraction_id: str) -> URIRef:
    return _uri("extraction", extraction_id)


def source_uri(source_id: str) -> URIRef:
    return _uri("source", source_id)


def connector_uri(name: str) -> URIRef:
    return _uri("connector", name)


def curator_uri(curator_id: str) -> URIRef:
    return _uri("curator", curator_id)


def _instant(g: Graph, subject: URIRef, predicate: URIRef, value: datetime | None) -> None:
    if value is not None:
        g.add((subject, predicate, Literal(value.isoformat(), datatype=XSD.dateTime)))


# --- graph construction -------------------------------------------------------


def build_prov_graph(lineage: Lineage) -> Graph:
    """Build the PROV-O graph for a lineage batch (SIG-INGEST-016 mapping)."""
    g = Graph()
    g.bind("prov", PROV)
    g.bind("sig", SIG)

    # Agents: connectors, curators, sources.
    for connector in lineage.connectors:
        node = connector_uri(connector.name)
        g.add((node, RDF.type, PROV.Agent))
        g.add((node, RDF.type, PROV.SoftwareAgent))
        if connector.version is not None:
            g.add((node, SIG.version, Literal(connector.version)))
    for curator in lineage.curators:
        node = curator_uri(curator.curator_id)
        g.add((node, RDF.type, PROV.Agent))
        g.add((node, RDF.type, PROV.Person))
        if curator.name is not None:
            g.add((node, SIG.name, Literal(curator.name)))
    for source in lineage.sources:
        node = source_uri(source.source_id)
        g.add((node, RDF.type, PROV.Agent))
        if source.name is not None:
            g.add((node, SIG.name, Literal(source.name)))

    # Activities: runs and extractions.
    for run in lineage.runs:
        node = run_uri(run.run_id)
        g.add((node, RDF.type, PROV.Activity))
        g.add((node, PROV.wasAssociatedWith, connector_uri(run.connector_name)))
        _instant(g, node, PROV.startedAtTime, run.started_at)
        _instant(g, node, PROV.endedAtTime, run.finished_at)
    for extraction in lineage.extractions:
        node = extraction_uri(extraction.extraction_id)
        g.add((node, RDF.type, PROV.Activity))
        g.add((node, SIG.partOfRun, run_uri(extraction.run_id)))
        if extraction.capture_id is not None:
            g.add((node, PROV.used, capture_uri(extraction.capture_id)))
        if extraction.connector_name is not None:
            g.add((node, PROV.wasAssociatedWith, connector_uri(extraction.connector_name)))

    # Entities: captures and claims.
    for capture in lineage.captures:
        node = capture_uri(capture.capture_id)
        g.add((node, RDF.type, PROV.Entity))
        if capture.source_id is not None:
            g.add((node, PROV.wasAttributedTo, source_uri(capture.source_id)))
        if capture.run_id is not None:
            g.add((node, PROV.wasGeneratedBy, run_uri(capture.run_id)))
        _instant(g, node, PROV.generatedAtTime, capture.retrieved_at)
    for claim in lineage.claims:
        node = claim_uri(claim.claim_id)
        g.add((node, RDF.type, PROV.Entity))
        if claim.extraction_id is not None:
            g.add((node, PROV.wasGeneratedBy, extraction_uri(claim.extraction_id)))
        elif claim.run_id is not None:
            g.add((node, PROV.wasGeneratedBy, run_uri(claim.run_id)))
        if claim.asserted_by_curator_id is not None:
            g.add((node, PROV.wasAttributedTo, curator_uri(claim.asserted_by_curator_id)))
        if claim.revises_claim_id is not None:
            # The canonical SIG-INGEST-016 edge: revises_claim -> prov:wasRevisionOf.
            revised = claim_uri(claim.revises_claim_id)
            g.add((node, PROV.wasRevisionOf, revised))
            # The revised claim is itself an Entity even when it belongs to an
            # earlier batch not otherwise described here, so an incremental export
            # stays self-consistent (and validates).
            g.add((revised, RDF.type, PROV.Entity))
        _instant(g, node, PROV.generatedAtTime, claim.recorded_at)

    return g


# --- validation ---------------------------------------------------------------

# The three disjoint PROV top classes an exported node may carry.
_PROV_TOP = {PROV.Entity: "Entity", PROV.Activity: "Activity", PROV.Agent: "Agent"}


class ProvValidationError(ValueError):
    """The exported graph does not conform to the SIG-INGEST-016 PROV-O mapping."""


def validate_prov_graph(graph: Graph) -> None:
    """Validate the PROV-O mapping (SIG-INGEST-016).

    Asserts every typed node carries exactly one of the disjoint PROV top classes,
    that `prov:wasRevisionOf` relates two Entities, and that generation/attribution
    edges connect the right PROV kinds. Raises :class:`ProvValidationError` on any
    breach so a malformed export fails the build.
    """
    top_class: dict[URIRef, set[str]] = {}
    for cls_uri, label in _PROV_TOP.items():
        for node in graph.subjects(RDF.type, cls_uri):
            if isinstance(node, URIRef):
                top_class.setdefault(node, set()).add(label)

    for node, kinds in top_class.items():
        if len(kinds) > 1:
            raise ProvValidationError(
                f"{node} is typed as multiple disjoint PROV classes: {sorted(kinds)}"
            )

    def _kind(node: object) -> str | None:
        if isinstance(node, URIRef) and node in top_class:
            return next(iter(top_class[node]))
        return None

    # wasRevisionOf relates Entity -> Entity (SIG-INGEST-016).
    for s, _p, o in graph.triples((None, PROV.wasRevisionOf, None)):
        if _kind(s) != "Entity" or _kind(o) != "Entity":
            raise ProvValidationError(f"prov:wasRevisionOf must relate two Entities: {s} -> {o}")
    # wasGeneratedBy relates Entity -> Activity.
    for s, _p, o in graph.triples((None, PROV.wasGeneratedBy, None)):
        if _kind(s) != "Entity" or _kind(o) != "Activity":
            raise ProvValidationError(
                f"prov:wasGeneratedBy must relate an Entity to an Activity: {s} -> {o}"
            )
    # wasAssociatedWith relates Activity -> Agent.
    for s, _p, o in graph.triples((None, PROV.wasAssociatedWith, None)):
        if _kind(s) != "Activity" or _kind(o) != "Agent":
            raise ProvValidationError(
                f"prov:wasAssociatedWith must relate an Activity to an Agent: {s} -> {o}"
            )
    # wasAttributedTo relates Entity -> Agent.
    for s, _p, o in graph.triples((None, PROV.wasAttributedTo, None)):
        if _kind(s) != "Entity" or _kind(o) != "Agent":
            raise ProvValidationError(
                f"prov:wasAttributedTo must relate an Entity to an Agent: {s} -> {o}"
            )


# --- serialisation ------------------------------------------------------------


def canonical_ntriples(graph: Graph) -> str:
    """Deterministic N-Triples: sorted lines, so a release artifact is byte-stable."""
    lines = sorted(line for line in graph.serialize(format="nt").splitlines() if line.strip())
    return "\n".join(lines) + "\n"


def export_lineage(lineage: Lineage, *, fmt: str = "turtle") -> str:
    """Build, validate, and serialise a lineage batch as PROV-O.

    `fmt="nt"` yields the deterministic canonical form; other rdflib formats
    (turtle, json-ld) are offered for interoperability.
    """
    graph = build_prov_graph(lineage)
    validate_prov_graph(graph)
    if fmt == "nt":
        return canonical_ntriples(graph)
    return graph.serialize(format=fmt)
