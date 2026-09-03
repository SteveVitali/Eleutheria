# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Per-run lineage mapped to PROV-O (SIG-INGEST-015/016)."""

from __future__ import annotations

from datetime import UTC, datetime

from connectors.lineage import build_lineage
from connectors.stages import CaptureRef
from evidence.ingest_run import IngestRun
from exports.provo import build_prov_graph as build_graph
from exports.provo import export_lineage, validate_prov_graph
from rdflib import PROV, RDF


def _run() -> IngestRun:
    return IngestRun(
        connector_name="toy",
        connector_version="1",
        code_commit="deadbeef",
        ruleset_version="r1",
        vocab_version="v1",
        input_digests=("digest-1",),
    )


def _capture() -> CaptureRef:
    return CaptureRef(
        digest="cap-digest-1",
        media_type="application/json",
        source_uri="https://portal.example/p1",
        byte_size=10,
        retrieved_at=datetime(2026, 6, 1, tzinfo=UTC),
    )


def test_build_lineage_assembles_the_run() -> None:
    # SIG-INGEST-015: the run's captures and claims are traceable to the ingest_run.
    lineage = build_lineage(
        _run(),
        run_id="run-1",
        source_id="eyes_on_flock",
        captures=[_capture()],
        claim_ids=["claim-1", "claim-2"],
    )
    assert len(lineage.captures) == 1
    assert len(lineage.claims) == 2
    assert lineage.runs[0].run_id == "run-1"
    assert lineage.connectors[0].name == "toy"
    assert lineage.sources[0].source_id == "eyes_on_flock"


def test_lineage_maps_onto_prov_o() -> None:
    # SIG-INGEST-016: captures/claims are prov:Entity, runs prov:Activity, etc.
    lineage = build_lineage(
        _run(),
        run_id="run-1",
        source_id="eyes_on_flock",
        captures=[_capture()],
        claim_ids=["claim-1"],
    )
    graph = build_graph(lineage)
    validate_prov_graph(graph)  # raises if the mapping is wrong
    entities = set(graph.subjects(RDF.type, PROV.Entity))
    activities = set(graph.subjects(RDF.type, PROV.Activity))
    agents = set(graph.subjects(RDF.type, PROV.Agent))
    assert entities and activities and agents

    turtle = export_lineage(lineage, fmt="turtle")
    assert "prov:" in turtle
