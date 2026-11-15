# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.37 (R11-K13-EV-03 / K8 EV-03, SIG-EVUI-004/005/009) — claim-view
generation + the real-capture diff fields.

* ``claim_view_bindings`` carries only REAL capture bindings —
  ``binding_status='actual_capture'`` on ``capture_classification='actual'``
  under the shared artifact/claim/seal gates and effective rights.
* Views generate for DOCUMENT-genre claims only, capped (D-K8-2); the cap
  and overflow emit in ``build.claim_views`` for /evidence/ (SIG-EVUI-009).
* The pane is lane × tier × Part VIII (SIG-EVUI-004): text_span only with
  stored text + a resolvable span; download only where the raw archive
  serves the digest; locator_only elsewhere; metadata_only where the bytes
  are withheld. A locator always; an excerpt ≤300 chars only where recorded
  terms permit (D-K8-1).
* The diff's ``fields`` are recorded predicate → raw-value pairs over real
  captures — never a fixture pair (SIG-EVUI-005).
"""

from __future__ import annotations

import json

from exports.claim_views import (
    CLAIM_VIEW_CAP,
    DOCUMENT_GENRES,
    EXCERPT_MAX_CHARS,
    claim_views,
    fields_by_capture,
)
from exports.spine_export import EXPORT_QUERIES
from test_spine_export import _build, _site


def _binding_row(**over):
    """A claim_view_bindings row in the SELECT's positional order."""
    row = [
        "claim-1",  # claim_id
        "cap-1",  # capture_id
        "art-1",  # artifact_id
        "establishes",  # role
        "actual_capture",  # binding_status
        "2026-07-02T00:00:00+00:00",  # bound_at
        json.dumps({"kind": "byte_range", "start": 4, "end": 12}),  # locator_json
        "quoted span text",  # excerpt
        "extractor-1.2",  # binding_extractor_version
        "2026-07-01T14:22:00+00:00",  # retrieved_at
        "sha256:d1",  # content_digest
        412_700,  # byte_size
        "application/pdf",  # media_type
        "public",  # storage_tier
        "actual",  # capture_classification
        "run-1",  # retrieved_by_run_id
        False,  # redaction_applied
        None,  # redaction_method
        None,  # redaction_version
        "contract",  # artifact_type
        "The contract",  # artifact_title
        "https://city.example/contract.pdf",  # artifact_url
        "src_a",  # artifact_source_id
        "entity-1",  # subject_id
        "auto_renews",  # predicate_id
        "true",  # raw_value
        "2026-07-01",  # observed_at
        "curator_reviewed",  # review_status
        "clause_extraction",  # extraction_method
        "clause-extractor",  # extraction_name
        "extractor-2.0",  # extraction_version
        "reviewed",  # extraction_review_status
    ]
    for k, v in over.items():
        idx = {
            "claim_id": 0,
            "capture_id": 1,
            "artifact_id": 2,
            "role": 3,
            "locator_json": 6,
            "excerpt": 7,
            "content_digest": 10,
            "storage_tier": 13,
            "capture_classification": 14,
            "artifact_type": 19,
            "artifact_source_id": 22,
            "predicate_id": 24,
            "raw_value": 25,
        }[k]
        row[idx] = v
    return tuple(row)


def test_query_gated_to_real_capture_bindings() -> None:
    """The producer binds only actual_capture + actual-classification rows
    under every shared gate — a synthetic run record never enters (SIG-EVUI-005)."""
    guard, sql = EXPORT_QUERIES["claim_view_bindings"]
    assert guard == "claim_evidence"
    assert "binding_status = 'actual_capture'" in sql
    assert "capture_classification = 'actual'" in sql
    assert "{PUB_CLAIM_GATE}" in sql and "{PUB_ARTIFACT_GATE}" in sql
    assert "{CAPTURE_SEAL_GATE}" in sql
    assert "{EFFECTIVE}" in sql and "redistributable = 'yes'" in sql
    assert "ce.locator" in sql and "ce.excerpt" in sql


def test_views_emit_for_document_genre_only() -> None:
    """SIG-EVUI-009: a document genre mints a view; a dataset genre does not."""
    raw = {
        "claim_view_bindings": [
            _binding_row(),
            _binding_row(claim_id="claim-ds", artifact_type="camera_registry", capture_id="cap-2"),
        ]
    }
    views, stats, _f = claim_views(raw)
    assert [v["claim_id"] for v in views] == ["claim-1"]
    assert stats["cap"] == CLAIM_VIEW_CAP
    assert stats["eligible"] == 1 and stats["emitted"] == 1 and stats["overflow"] == 0


def test_cap_bounds_emission_and_discloses_overflow() -> None:
    """D-K8-2: at most `cap` views; the overflow count is recorded verbatim."""
    rows = [_binding_row(claim_id=f"claim-{i:03d}", capture_id=f"cap-{i}") for i in range(5)]
    views, stats, _f = claim_views({"claim_view_bindings": rows}, cap=3)
    assert [v["claim_id"] for v in views] == ["claim-000", "claim-001", "claim-002"]
    assert stats["emitted"] == 3 and stats["overflow"] == 2 and stats["eligible"] == 5


def test_pane_decision_by_lane() -> None:
    """SIG-EVUI-004: lane × tier × Part VIII decides the pane — bytes never
    implied (download needs the archive's served href; restricted/metadata
    lanes never show a locator-link either)."""
    lanes = {
        "src_a": {"decision": _Lane("restricted")},
        "src_b": {"decision": _Lane("derived-only")},
        "src_c": {"decision": _Lane("raw-ok")},
    }
    rows = [
        _binding_row(claim_id="c-restricted", artifact_source_id="src_a"),
        _binding_row(claim_id="c-derived", artifact_source_id="src_b"),
        _binding_row(claim_id="c-download", artifact_source_id="src_c", capture_id="cap-3"),
    ]
    views, _s, _f = claim_views(
        {
            "claim_view_bindings": rows,
            "raw_hrefs": {"sha256:d1": "https://files.example/raw/sha256:d1"},
        },
        lane_by_source=lanes,
    )
    by_id = {v["claim_id"]: v for v in views}
    assert by_id["c-restricted"]["pane"]["kind"] == "metadata_only"
    assert by_id["c-derived"]["pane"]["kind"] == "locator_only"
    assert by_id["c-download"]["pane"]["kind"] == "download"
    assert by_id["c-download"]["capture"]["view_original"]["href"] == (
        "https://files.example/raw/sha256:d1"
    )
    # A raw-ok claim with NO served bytes stays locator_only — a label never
    # implies a route the release does not carry.
    views2, _s2, _f2 = claim_views({"claim_view_bindings": [rows[2]]}, lane_by_source=lanes)
    assert views2[0]["pane"]["kind"] == "locator_only"


def test_text_span_pane_only_with_stored_text_and_span() -> None:
    """The text pane needs the capture-text seam AND a resolvable span."""
    rows = [_binding_row()]
    lanes = {"src_a": {"decision": _Lane("raw-ok")}}
    # No capture_texts → locator form, never a text pane over absent bytes.
    views, _s, _f = claim_views({"claim_view_bindings": rows}, lane_by_source=lanes)
    assert views[0]["pane"]["kind"] in {"locator_only", "download"}
    # Text present + byte_range span → text_span with the stored text.
    views2, _s2, _f2 = claim_views(
        {
            "claim_view_bindings": rows,
            "capture_texts": {"sha256:d1": "0123quoted span text456"},
        },
        lane_by_source=lanes,
    )
    assert views2[0]["pane"]["kind"] == "text_span"
    assert views2[0]["capture"]["document_text"] == "0123quoted span text456"


def test_excerpt_only_where_terms_permit_within_300() -> None:
    """D-K8-1: a locator always; the recorded excerpt only where recorded
    terms permit quotation (or the raw-ok lane publishes the bytes), ≤300."""
    rows = [_binding_row(excerpt="x" * 40)]
    # derived-only + no quotation_permitted → no excerpt.
    views, _s, _f = claim_views(
        {"claim_view_bindings": rows},
        lane_by_source={"src_a": {"decision": _Lane("derived-only")}},
    )
    assert "excerpt" not in views[0]
    # recorded permission → the excerpt emits.
    views2, _s2, _f2 = claim_views(
        {"claim_view_bindings": rows},
        lane_by_source={"src_a": {"decision": _Lane("derived-only"), "quotation_permitted": True}},
    )
    assert views2[0]["excerpt"] == "x" * 40
    # raw-ok publishes bytes → the excerpt is trivially permitted.
    views3, _s3, _f3 = claim_views(
        {"claim_view_bindings": rows},
        lane_by_source={"src_a": {"decision": _Lane("raw-ok")}},
    )
    assert views3[0]["excerpt"] == "x" * 40
    # >300 chars never emits, even with permission.
    views4, _s4, _f4 = claim_views(
        {"claim_view_bindings": [_binding_row(excerpt="y" * (EXCERPT_MAX_CHARS + 1))]},
        lane_by_source={"src_a": {"decision": _Lane("raw-ok")}},
    )
    assert "excerpt" not in views4[0]


def test_diff_fields_are_recorded_values_only() -> None:
    """SIG-EVUI-005: fields are the recorded predicate → raw-value pairs over
    every bound publishable claim — the field-by-field diff's only input."""
    rows = [
        _binding_row(predicate_id="auto_renews", raw_value="true"),
        _binding_row(
            claim_id="claim-2",
            predicate_id="notice_window_days",
            raw_value="90",
        ),
        _binding_row(
            claim_id="claim-3",
            predicate_id="notice_window_days",
            raw_value="90",
            capture_id="cap-9",
        ),
    ]
    fields = fields_by_capture([dict(zip(_cols(), r, strict=False)) for r in rows])
    assert fields["cap-1"] == {"auto_renews": "true", "notice_window_days": "90"}
    assert fields["cap-9"] == {"notice_window_days": "90"}


def _cols() -> tuple[str, ...]:
    from exports.claim_views import CLAIM_VIEW_BINDING_COLUMNS

    return CLAIM_VIEW_BINDING_COLUMNS


class _Lane:
    def __init__(self, lane: str) -> None:
        self.lane = lane


def test_export_emits_generated_views_and_stats() -> None:
    """The full surface: `claim_views` populated + `build.claim_views` states
    the cap and overflow verbatim (SIG-EVUI-009)."""
    claims = _site("A", "35.46", "-97.51", "Oklahoma")
    export = _build(
        claims,
        raw_over={
            "evidence_artifacts": [],
            "claim_view_bindings": [_binding_row()],
        },
    )
    evidence = json.loads(export.web_artifacts["web/evidence.json"].decode("utf-8"))
    assert len(evidence["claim_views"]) == 1
    view = evidence["claim_views"][0]
    assert view["claim_id"] == "claim-1" and view["binding_status"] == "actual_capture"
    assert view["history"] and view["history"][0]["event"] == "asserted"
    stats = evidence["build"]["claim_views"]
    assert stats["cap"] == CLAIM_VIEW_CAP and stats["emitted"] == 1
    assert stats["eligible"] == 1 and stats["overflow"] == 0


def test_document_genre_set_is_the_recorded_document_classes() -> None:
    """The scope is the recorded document classes — datasets/run records
    (camera_registry, osm_node_set, connector_run, community_map,
    subscription, recommendation) are never view-eligible."""
    assert "camera_registry" not in DOCUMENT_GENRES
    assert "connector_run" not in DOCUMENT_GENRES
    assert "osm_node_set" not in DOCUMENT_GENRES
    assert "contract" in DOCUMENT_GENRES and "agenda_document" in DOCUMENT_GENRES
