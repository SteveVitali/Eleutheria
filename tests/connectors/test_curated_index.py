# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""A curated source index is held as an index, never normalized into claims.

Anchored on the P13.2 acceptance criterion for SIG-EPIS-030 (§10.9, OL-2E-AL-02):
SIG MUST be able to hold a curated source index *as an index*, without normalizing
its entries into claims. This is the general form of the behaviour the P13.1
``accountability`` connector's Abuse Library handling relies on.
"""

from __future__ import annotations

import dataclasses
import json

import pytest
from connectors.accountability import AccountabilityConnector, source_ids
from connectors.curated_index import (
    CuratedIndexEntry,
    CuratedSourceIndex,
    IndexNormalizationRefused,
)
from connectors.registry import get
from connectors.stages import InMemoryCaptureStore, InMemoryClaimSink, RunContext
from evidence.ingest_run import IngestRun

# A small curated bibliography of reporting — the shape a real source index takes.
BIBLIOGRAPHY = [
    {"incident": "inc-1", "url": "https://library.example/a", "note": "reporting on A"},
    {"incident": "inc-2", "source": "https://library.example/b"},
    {"incident": "inc-3", "citation": "Doe, 2024, p.4"},
]


def _index() -> CuratedSourceIndex:
    return CuratedSourceIndex.from_raw(
        "src:abuse_library",
        BIBLIOGRAPHY,
        ref_keys=("url", "source", "citation"),
        subject_keys=("incident", "id"),
    )


def test_a_curated_index_retains_its_entries_as_an_index() -> None:
    # SIG-EPIS-030 / OL-2E-AL-02: the entries are held as index references, not
    # materialized into claims about their subjects.
    index = _index()
    assert len(index) == 3
    assert [e.source_ref for e in index] == [
        "https://library.example/a",
        "https://library.example/b",
        "Doe, 2024, p.4",
    ]
    # each entry indexes its subject without asserting anything about it
    assert [e.indexes for e in index] == ["inc-1", "inc-2", "inc-3"]
    assert all(e.source_class == "advocacy_analysis" for e in index)


def test_index_records_are_index_only_never_claim_rows() -> None:
    records = _index().index_records()
    assert len(records) == 3
    for rec in records:
        assert rec["record_kind"] == "index_entry"
        assert rec["index_only"] is True
        # the raw reference is preserved (P2), not normalized into a typed claim value
        assert rec["raw_value"] == rec["source_ref"]
        # an index entry is not a claim: it carries no predicate/value assertion
        assert "predicate_id" not in rec
        assert "value" not in rec


def test_normalizing_a_curated_index_into_claims_is_refused() -> None:
    # The guard makes "held as an index, not normalized into facts" a mechanical
    # property, not a convention (SIG-EPIS-030, §10.9).
    with pytest.raises(IndexNormalizationRefused):
        _index().as_claims()
    assert _index().held_as_index is True


def test_an_entry_requires_a_reference() -> None:
    with pytest.raises(ValueError, match="source_ref"):
        CuratedIndexEntry(source_ref="  ")


def test_entries_without_a_resolvable_reference_are_skipped_not_invented() -> None:
    index = CuratedSourceIndex.from_raw(
        "src:x",
        [{"note": "no url, no citation"}, {"url": "https://library.example/c"}],
        ref_keys=("url", "citation"),
    )
    assert [e.source_ref for e in index] == ["https://library.example/c"]


def test_the_accountability_connector_relies_on_the_general_capability() -> None:
    # The P13.1 Abuse Library path is the canonical consumer: its entries surface as
    # index_only advocacy-analysis links, never event claims (regression guard for
    # the SIG-EPIS-030 general form the connector now depends on).
    source = dataclasses.replace(get(source_ids()["abuse_library"]), ingestion_permitted=True)
    ctx = RunContext(
        source=source,
        run=IngestRun(
            connector_name="accountability",
            connector_version="1.0.0",
            code_commit="deadbeef",
            ruleset_version="r1",
            vocab_version="v1",
            input_digests=(),
        ),
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
    )
    conn = AccountabilityConnector()
    payload = json.dumps({"entries": [{"incident": "inc-1", "url": "https://library.example/a"}]})
    parsed = {"kind": "abuse_library", "payload": json.loads(payload)}
    rows = conn.normalize(ctx, conn.extract(ctx, parsed))
    links = [r for r in rows if r["record_kind"] == "evidence_link"]
    assert len(links) == 1
    assert links[0]["index_only"] is True
    assert links[0]["source_class"] == "advocacy_analysis"
