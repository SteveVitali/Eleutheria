# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Dereferenceable identifiers with content negotiation (§37.3, SIG-API-008).

Every SIG identifier is dereferenceable at ``/id/{type}/{uuid}``. The same
identifier resolves to HTML (for a browser), JSON-LD, or RDF (Turtle) depending
on the ``Accept`` header (SIG-IDENT-031) — a cool-URI, follow-your-nose contract
that lets the graph be crawled as linked data. The RDF/JSON-LD share one base
IRI namespace so a dereferenced id is a stable subject across representations.
"""

from __future__ import annotations

import html

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS

from .store import IdDescriptor

#: The base IRI namespace SIG identifiers dereference under.
SIG = Namespace("https://sig.example/id/")

#: The media types the dereference endpoint content-negotiates over, in the
#: order they are offered (SIG-API-008).
JSONLD_MEDIA_TYPE = "application/ld+json"
TURTLE_MEDIA_TYPE = "text/turtle"
HTML_MEDIA_TYPE = "text/html"


def subject_iri(descriptor: IdDescriptor) -> str:
    """The stable subject IRI for a dereferenced identifier."""
    return f"{SIG}{descriptor.id_type}/{descriptor.uuid}"


def select_media_type(accept: str | None) -> str:
    """Pick a representation from an ``Accept`` header (SIG-API-008).

    JSON-LD and Turtle are honoured when explicitly requested; everything else —
    including a browser's ``text/html`` and the ``*/*`` default — resolves to the
    human HTML view, the follow-your-nose landing page.
    """
    header = (accept or "").lower()
    if JSONLD_MEDIA_TYPE in header:
        return JSONLD_MEDIA_TYPE
    if TURTLE_MEDIA_TYPE in header or "application/rdf+xml" in header:
        return TURTLE_MEDIA_TYPE
    return HTML_MEDIA_TYPE


def _graph(descriptor: IdDescriptor) -> Graph:
    graph = Graph()
    graph.bind("sig", SIG)
    subject = URIRef(subject_iri(descriptor))
    graph.add((subject, RDF.type, URIRef(f"{SIG}type/{descriptor.id_type}")))
    graph.add((subject, RDFS.label, Literal(descriptor.label)))
    for predicate, value in sorted(descriptor.predicates.items()):
        graph.add((subject, URIRef(f"{SIG}prop/{predicate}"), Literal(value)))
    return graph


def render_jsonld(descriptor: IdDescriptor) -> str:
    """A JSON-LD representation of the identifier (SIG-API-008)."""
    return _graph(descriptor).serialize(format="json-ld")


def render_turtle(descriptor: IdDescriptor) -> str:
    """A Turtle (RDF) representation of the identifier (SIG-API-008)."""
    return _graph(descriptor).serialize(format="turtle")


def render_html(descriptor: IdDescriptor) -> str:
    """A minimal human landing page for the identifier (SIG-API-008)."""
    rows = "\n".join(
        f"    <tr><th>{html.escape(k)}</th><td>{html.escape(str(v))}</td></tr>"
        for k, v in sorted(descriptor.predicates.items())
    )
    label = html.escape(descriptor.label)
    iri = html.escape(subject_iri(descriptor))
    canonical = html.escape(descriptor.canonical_path)
    return (
        "<!doctype html>\n"
        f'<html lang="en"><head><meta charset="utf-8"><title>{label}</title></head>\n'
        "<body>\n"
        f"  <h1>{label}</h1>\n"
        f"  <p>Identifier: <code>{iri}</code></p>\n"
        f'  <p>Canonical resource: <a href="{canonical}">{canonical}</a></p>\n'
        f"  <table>\n{rows}\n  </table>\n"
        "</body></html>\n"
    )
