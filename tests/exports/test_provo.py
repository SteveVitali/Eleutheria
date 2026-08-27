# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""PROV-O export over the ingest-run lineage (§21.6, SIG-INGEST-016).

AC6: the PROV-O export validates and maps captures/claims/runs/agents per the
fixed SIG-INGEST-016 correspondence.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from exports.provo import (
    Capture,
    Claim,
    Connector,
    Curator,
    Extraction,
    IngestRun,
    Lineage,
    ProvValidationError,
    Source,
    build_prov_graph,
    canonical_ntriples,
    capture_uri,
    claim_uri,
    connector_uri,
    curator_uri,
    export_lineage,
    extraction_uri,
    run_uri,
    source_uri,
    validate_prov_graph,
)
from exports.provo_io import lineage_from_json
from rdflib import PROV, RDF


def _lineage() -> Lineage:
    ts = datetime(2026, 8, 20, 14, 3, tzinfo=UTC)
    return Lineage(
        sources=[Source("flock-portal", "Flock Portal")],
        connectors=[Connector("flock", "1.2.0")],
        curators=[Curator("curator-1", "A. Curator")],
        runs=[IngestRun("run-1", "flock", "1.2.0", started_at=ts)],
        extractions=[Extraction("ext-1", "run-1", capture_id="cap-1", connector_name="flock")],
        captures=[Capture("cap-1", source_id="flock-portal", run_id="run-1", retrieved_at=ts)],
        claims=[
            Claim("claim-old", extraction_id="ext-1", run_id="run-1"),
            Claim(
                "claim-new",
                extraction_id="ext-1",
                run_id="run-1",
                revises_claim_id="claim-old",
                asserted_by_curator_id="curator-1",
            ),
        ],
    )


def test_captures_and_claims_are_entities() -> None:
    g = build_prov_graph(_lineage())
    assert (capture_uri("cap-1"), RDF.type, PROV.Entity) in g
    assert (claim_uri("claim-old"), RDF.type, PROV.Entity) in g
    assert (claim_uri("claim-new"), RDF.type, PROV.Entity) in g


def test_runs_and_extractions_are_activities() -> None:
    g = build_prov_graph(_lineage())
    assert (run_uri("run-1"), RDF.type, PROV.Activity) in g
    assert (extraction_uri("ext-1"), RDF.type, PROV.Activity) in g


def test_connectors_curators_sources_are_agents() -> None:
    g = build_prov_graph(_lineage())
    assert (connector_uri("flock"), RDF.type, PROV.Agent) in g
    assert (curator_uri("curator-1"), RDF.type, PROV.Agent) in g
    assert (source_uri("flock-portal"), RDF.type, PROV.Agent) in g


def test_revises_claim_maps_to_was_revision_of() -> None:
    g = build_prov_graph(_lineage())
    assert (claim_uri("claim-new"), PROV.wasRevisionOf, claim_uri("claim-old")) in g


def test_wiring_edges_use_prov_vocabulary() -> None:
    g = build_prov_graph(_lineage())
    assert (claim_uri("claim-new"), PROV.wasGeneratedBy, extraction_uri("ext-1")) in g
    assert (claim_uri("claim-new"), PROV.wasAttributedTo, curator_uri("curator-1")) in g
    assert (extraction_uri("ext-1"), PROV.used, capture_uri("cap-1")) in g
    assert (capture_uri("cap-1"), PROV.wasAttributedTo, source_uri("flock-portal")) in g
    assert (run_uri("run-1"), PROV.wasAssociatedWith, connector_uri("flock")) in g


def test_export_validates() -> None:
    # export_lineage validates internally; it must not raise on a well-formed graph.
    turtle = export_lineage(_lineage(), fmt="turtle")
    assert "prov:wasRevisionOf" in turtle or "wasRevisionOf" in turtle


def test_validation_rejects_a_disjoint_class_conflict() -> None:
    g = build_prov_graph(_lineage())
    # Force a claim (Entity) to also be typed as an Activity — disjoint in PROV.
    g.add((claim_uri("claim-old"), RDF.type, PROV.Activity))
    with pytest.raises(ProvValidationError):
        validate_prov_graph(g)


def test_serialisation_is_deterministic() -> None:
    a = canonical_ntriples(build_prov_graph(_lineage()))
    b = canonical_ntriples(build_prov_graph(_lineage()))
    assert a == b
    assert export_lineage(_lineage(), fmt="nt") == a


def test_incremental_export_of_a_correction_still_validates() -> None:
    """A correction batch may reference a prior claim from an earlier run; the
    revised claim is still an Entity, so the export validates."""
    lineage = Lineage(
        connectors=[Connector("flock", "1.0")],
        runs=[IngestRun("run-2", "flock", "1.0")],
        claims=[
            Claim("claim-new", run_id="run-2", revises_claim_id="claim-from-earlier-run"),
        ],
    )
    g = build_prov_graph(lineage)
    validate_prov_graph(g)  # must not raise
    assert (claim_uri("claim-from-earlier-run"), RDF.type, PROV.Entity) in g
    assert (claim_uri("claim-new"), PROV.wasRevisionOf, claim_uri("claim-from-earlier-run")) in g


def test_round_trips_through_json_loader() -> None:
    doc = {
        "sources": [{"source_id": "s1"}],
        "connectors": [{"name": "flock", "version": "1.0"}],
        "runs": [{"run_id": "r1", "connector_name": "flock"}],
        "captures": [{"capture_id": "cap1", "source_id": "s1", "run_id": "r1"}],
        "claims": [
            {"claim_id": "c1", "run_id": "r1"},
            {"claim_id": "c2", "run_id": "r1", "revises_claim_id": "c1"},
        ],
    }
    lineage = lineage_from_json(doc)
    g = build_prov_graph(lineage)
    validate_prov_graph(g)
    assert (claim_uri("c2"), PROV.wasRevisionOf, claim_uri("c1")) in g
