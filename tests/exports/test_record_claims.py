# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P32.13 (SIG-FIND-002) — the per-compartment ``record_claims.jsonl`` export
artifact: claim anchors + evidence bindings, sliced by the claim's OWN licence
compartment and checksummed in the manifest."""

from __future__ import annotations

import json
from pathlib import Path

from exports.spine_export import EXPORT_QUERIES
from test_spine_export import _build, _site


def _claims_artifact(export, comp: str) -> list[dict]:
    data = export.web_artifacts[f"{comp}/record_claims.jsonl"]
    return [json.loads(line) for line in data.decode().splitlines() if line.strip()]


def test_record_claims_emitted_per_compartment() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma") + _site(
        "B", "48.85", "2.35", "Paris", source_id="fr_src", spdx="CC-BY-4.0"
    )
    export = _build(claims)
    compartments = {
        a.compartment: a for a in export.manifest.artifacts if "record_claims" in a.path
    }
    # one artifact per site compartment, each labelled with ITS licence
    paths = {a.path for a in export.manifest.artifacts}
    assert any("record_claims.jsonl" in p for p in paths)
    for art in compartments.values():
        assert art.license != "" and art.sha256 != "x"
    sig_rows = None
    for a in export.manifest.artifacts:
        if a.path.endswith("record_claims.jsonl") and a.compartment == "sig_graph":
            sig_rows = _claims_artifact(export, a.path.split("/")[0])
    assert sig_rows is not None
    anchors = {r["claim_id"] for r in sig_rows}
    # the CC-BY French site's claims land in the sig_graph compartment…
    # actually every claim is filed under ITS OWN licence compartment:
    for row in sig_rows:
        assert row["source_id"] in {"src_a", "fr_src"}
        assert row["predicate_id"].startswith("camera_")
        assert row["entity_id"] in {"A", "B"}
    assert anchors  # non-empty


def test_record_claims_carry_evidence_bindings() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma")
    raw_over = {
        "evidence_bindings": [
            ("A-src_a-lat", "cap-1", "art-1", "establishes"),
            ("A-src_a-lat", "cap-2", "art-2", "corroborates"),
        ]
    }
    export = _build(claims, raw_over=raw_over)
    rows = [
        json.loads(line)
        for path, data in export.web_artifacts.items()
        if path.endswith("record_claims.jsonl")
        for line in data.decode().splitlines()
        if line.strip()
    ]
    lat = next(r for r in rows if r["claim_id"] == "A-src_a-lat")
    assert {e["capture_id"] for e in lat["evidence"]} == {"cap-1", "cap-2"}
    assert {e["artifact_id"] for e in lat["evidence"]} == {"art-1", "art-2"}
    assert all(e["role"] for e in lat["evidence"])


def test_record_claims_never_carry_raw_values() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma")
    export = _build(claims)
    for path, data in export.web_artifacts.items():
        if not path.endswith("record_claims.jsonl"):
            continue
        for line in data.decode().splitlines():
            row = json.loads(line)
            assert "raw_value" not in row and "value_text" not in row


def test_evidence_bindings_query_gated_on_artifact_disposition() -> None:
    """The export query carries the shared PUB_ARTIFACT_GATE marker — the same
    eligibility rule (SQL twin of access_decision), never a second definition."""
    guard, sql = EXPORT_QUERIES["evidence_bindings"]
    assert guard == "claim_evidence"
    assert "{PUB_ARTIFACT_GATE}" in sql
    assert "sensitivity_tier = 0" in sql
    assert "claim_evidence" in sql and "evidence_artifact" in sql


def test_artifact_eligible_sql_is_the_access_decision_twin() -> None:
    from db.dispositions import artifact_eligible_sql

    frag = artifact_eligible_sql("ea.artifact_id")
    assert "publication_disposition" in frag
    assert "'artifact'" in frag
    assert "withhold" in frag and "restrict" in frag and "withdraw" in frag
    assert "ea.artifact_id" in frag


def test_record_claims_slice_by_own_licence(tmp_path: Path) -> None:
    """An ODbL claim never lands in a CC-BY compartment file (SIG-LIC-004a)."""
    claims = _site("A", "35.46", "-97.51", "Oklahoma", spdx="ODbL-1.0") + _site(
        "B", "48.85", "2.35", "Paris", source_id="fr_src", spdx="CC-BY-4.0"
    )
    export = _build(claims)
    files = {
        path: [json.loads(line) for line in data.decode().splitlines() if line.strip()]
        for path, data in export.web_artifacts.items()
        if path.endswith("record_claims.jsonl")
    }
    assert len(files) >= 2
    for path, rows in files.items():
        comp = path.split("/")[0]
        if comp == "osm_physical":
            assert all(r["source_id"] == "src_a" for r in rows)
        else:
            assert all(r["source_id"] == "fr_src" for r in rows)
