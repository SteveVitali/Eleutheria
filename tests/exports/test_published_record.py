# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P32.13 (SIG-FIND-002) — the ``sig.published-record/1`` projection: ID-free
hashing, namespace binding, and honest unavailability states."""

from __future__ import annotations

import json

from exports.published_record import (
    claim_index_from_jsonl,
    projection_root,
    record_digest,
    record_from_site_row,
    record_key,
)


def _row(**over) -> dict:
    base = {
        "_rights": {
            "attribution": "© src",
            "license": "CC-BY-4.0",
            "source_id": "src_a",
            "terms_url": "https://example/terms",
        },
        "claim_ids": ["c-1", "c-2"],
        "entity_id": "ent-1",
        "entity_type": "deployment",
        "geometry": {"coordinates": [-97.5, 35.46], "type": "Point"},
        "jurisdiction": "OK",
        "label": "A site",
        "n_observation_claims": 2,
        "n_sources": 1,
        "point_status": "resolved",
        "precision": "full_precision",
        "source_id": "src_a",
        "spdx": "CC-BY-4.0",
        "tier": 0,
    }
    base.update(over)
    return base


def test_id_free_doc_excludes_namespace_fields() -> None:
    rec = record_from_site_row(_row(), compartment="sig_graph", license_id="CC-BY-4.0")
    bound = rec.bind("p-" + "a" * 64)
    # binding never changes the hashed content
    assert rec.id_free_doc() == bound.id_free_doc()
    assert record_digest(rec) == record_digest(bound)
    doc = bound.as_json()
    assert doc["publication_id"] == "p-" + "a" * 64
    assert doc["href"].startswith("/r/p-")


def test_record_key_is_compartment_scoped() -> None:
    assert record_key("osm_physical", "deployment", "ent-9") == ("osm_physical:deployment:ent-9")


def test_claim_anchors_degrade_honestly_without_claim_index() -> None:
    rec = record_from_site_row(_row(), compartment="sig_graph", license_id="CC-BY-4.0")
    anchors = {a.claim_id: a for a in rec.claim_anchors}
    assert anchors["c-1"].locator == "unlocated"
    assert anchors["c-1"].predicate_id is None
    assert rec.evidence_refs == ()


def test_claim_anchors_enriched_from_claim_index() -> None:
    index = claim_index_from_jsonl(
        [
            {
                "claim_id": "c-1",
                "predicate_id": "camera_latitude",
                "observed_at": "2026-05-01",
                "source_id": "src_a",
                "evidence": [
                    {"capture_id": "cap-1", "artifact_id": "art-1", "role": "establishes"}
                ],
            }
        ]
    )
    rec = record_from_site_row(
        _row(), compartment="sig_graph", license_id="CC-BY-4.0", claim_index=index
    )
    anchors = {a.claim_id: a for a in rec.claim_anchors}
    assert anchors["c-1"].predicate_id == "camera_latitude"
    assert anchors["c-2"].locator == "unlocated"
    ev = rec.evidence_refs[0]
    assert ev.artifact_id == "art-1" and ev.capture_id == "cap-1"
    assert ev.access == "metadata_only"


def test_projection_root_is_order_independent() -> None:
    a = record_from_site_row(_row(entity_id="e-a"), compartment="c", license_id="L")
    b = record_from_site_row(_row(entity_id="e-b"), compartment="c", license_id="L")
    assert projection_root([record_digest(a), record_digest(b)]) == projection_root(
        [record_digest(b), record_digest(a)]
    )


def test_record_json_is_deterministic() -> None:
    r1 = record_from_site_row(_row(), compartment="c", license_id="L").bind("p-" + "0" * 64)
    r2 = record_from_site_row(_row(), compartment="c", license_id="L").bind("p-" + "0" * 64)
    assert r1.json_bytes() == r2.json_bytes()
    doc = json.loads(r1.json_bytes())
    assert doc["schema"] == "sig.published-record/1"
