# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.36 (R11-K13-TX-08a / J3 §5.1–5.3, SIG-TRANSP-011) — the per-compartment
``sig.statement/1`` statements files, the S-6-gated ``upstream_href``, and the
shared ``<ProvenancePanel>`` contract (UXR-33).

Fixture-verified layer: schema per compartment, S-6 URL cases, the four J3 §5.1
binding-state wordings verbatim, ODbL separation, the release-tree statements
file, and the record JSON's embedded statements.
"""

from __future__ import annotations

import json
from pathlib import Path

from exports.manifest import canonical_json, sha256_hex
from exports.provenance_panel import (
    BINDING_STATE_TEMPLATES,
    NOT_RECORDED,
    panel_from_statement,
    panel_html,
)
from exports.published_record import record_from_site_row
from exports.release import build_release
from exports.statements import (
    BINDING_DETAIL_COLUMNS,
    BINDING_STATES,
    CLAIM_PROVENANCE_COLUMNS,
    STATEMENT_SCHEMA,
    UPSTREAM_STATUSES,
)
from exports.transparency import SOURCE_RIGHTS_COLUMNS
from policy.transparency import TRANSPARENCY_SOURCE_VIEW_COLUMNS
from test_spine_export import _build, _site

REVISION = "a" * 40


def _cols_to_tuple(row: dict, columns: tuple[str, ...]) -> tuple:
    """A dict-shaped fixture row → the positional tuple the raw seam carries
    (``fetchall`` rows are positional; ``_rows`` zips by column order)."""
    return tuple(row.get(c) for c in columns)


def _detail_t(
    claim_id: str,
    *,
    capture_id: str = "cap-1",
    artifact_id: str = "art-1",
    role: str = "establishes",
    binding_status: str = "legacy_synthetic",
    bound_at: str = "2026-05-02T00:00:00+00:00",
    extractor_version: str | None = "extractor/1.2",
    retrieved_at: str = "2026-05-01T12:00:00+00:00",
    content_digest: str = "sha256:" + "ab" * 32,
    byte_size: int = 0,
    media_type: str = "text/html",
    storage_tier: str = "public",
    capture_classification: str = "synthetic",
    retrieved_by_run_id: str = "run-1",
    artifact_url: str | None = None,
    artifact_source_id: str = "src_a",
    acquisition_method: str = "http_get",
    extraction_method: str | None = "structured_parse",
    extraction_name: str | None = "camreg",
    extraction_version: str | None = "1.2",
    extraction_review_status: str | None = "unreviewed",
) -> tuple:
    """One ``claim_binding_detail`` row (the EXPORT_QUERIES column order)."""
    return _cols_to_tuple(
        {
            "claim_id": claim_id,
            "capture_id": capture_id,
            "artifact_id": artifact_id,
            "role": role,
            "binding_status": binding_status,
            "bound_at": bound_at,
            "extractor_version": extractor_version,
            "retrieved_at": retrieved_at,
            "content_digest": content_digest,
            "byte_size": byte_size,
            "media_type": media_type,
            "storage_tier": storage_tier,
            "capture_classification": capture_classification,
            "retrieved_by_run_id": retrieved_by_run_id,
            "artifact_url": artifact_url,
            "artifact_source_id": artifact_source_id,
            "acquisition_method": acquisition_method,
            "extraction_method": extraction_method,
            "extraction_name": extraction_name,
            "extraction_version": extraction_version,
            "extraction_review_status": extraction_review_status,
        },
        BINDING_DETAIL_COLUMNS,
    )


def _provenance_t(
    claim_id: str,
    *,
    review_status: str = "unreviewed",
    claim_directness: str = "D2",
    source_reliability: str = "R3",
    artifact_integrity: str = "I1",
    ingest_run_id: str = "run-9",
    recorded_at: str = "2026-05-02T00:00:00+00:00",
    revises_claim: str | None = None,
    retraction_of: str | None = None,
) -> tuple:
    return _cols_to_tuple(
        {
            "claim_id": claim_id,
            "review_status": review_status,
            "claim_directness": claim_directness,
            "source_reliability": source_reliability,
            "artifact_integrity": artifact_integrity,
            "ingest_run_id": ingest_run_id,
            "recorded_at": recorded_at,
            "revises_claim": revises_claim,
            "retraction_of": retraction_of,
        },
        CLAIM_PROVENANCE_COLUMNS,
    )


def _rights_t(
    source_id: str,
    *,
    custody: str = "HOLD",
    spdx: str = "CC-BY-4.0",
    redistributable: bool = True,
    reviewed: bool = True,
) -> tuple:
    """One ``transparency_source_rights`` row (SOURCE_RIGHTS_COLUMNS)."""
    return _cols_to_tuple(
        {
            "source_id": source_id,
            "custody_posture": custody,
            "spdx_expression": spdx,
            "redistributable": redistributable,
            "reviewed": reviewed,
            "ingestion_permitted": True,
        },
        SOURCE_RIGHTS_COLUMNS,
    )


def _view_t(source_id: str, *, lane: str, part_viii_class: str = "") -> tuple:
    """One ``v_transparency_source`` mirror row — only the lane/p8 fields the
    lane map reads are populated (``TRANSPARENCY_SOURCE_VIEW_COLUMNS``)."""
    return _cols_to_tuple(
        {"source_id": source_id, "lane": lane, "part_viii_class": part_viii_class},
        TRANSPARENCY_SOURCE_VIEW_COLUMNS,
    )


def _statements(export, comp: str) -> dict[str, dict]:
    data = export.web_artifacts[f"{comp}/statements.jsonl"]
    return {
        r["claim_id"]: r
        for r in (json.loads(line) for line in data.decode().splitlines() if line.strip())
    }


def _all_statements(export) -> dict[str, list[dict]]:
    return {
        path: [json.loads(line) for line in data.decode().splitlines() if line.strip()]
        for path, data in export.web_artifacts.items()
        if path.endswith("/statements.jsonl")
    }


# --- deliverable 1: per-compartment sig.statement/1 files -------------------- #


def test_statements_emitted_per_compartment_with_manifest_entries() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma") + _site(
        "B", "48.85", "2.35", "Paris", source_id="fr_src", spdx="CC-BY-4.0"
    )
    export = _build(claims)
    arts = {a.path: a for a in export.manifest.artifacts if a.path.endswith("statements.jsonl")}
    assert set(arts) == {"osm_physical/statements.jsonl", "sig_graph/statements.jsonl"}
    for path, art in arts.items():
        comp = path.split("/")[0]
        assert art.compartment == comp
        assert art.schema == STATEMENT_SCHEMA
        assert art.media_type == "application/x-ndjson"
        assert art.sha256 == sha256_hex(export.web_artifacts[path])
        assert art.byte_size == len(export.web_artifacts[path])
        assert art.row_count == len(_statements(export, comp))
        assert art.distinct_entities is not None


def test_statements_rows_carry_the_contract_and_no_raw_values() -> None:
    export = _build(_site("A", "35.46", "-97.51", "Oklahoma"))
    files = _all_statements(export)
    assert files
    for rows in files.values():
        for row in rows:
            assert row["schema"] == STATEMENT_SCHEMA
            assert row["claim_id"].startswith("A-src_a-")
            assert row["entity_id"] == "A"
            assert row["predicate_id"].startswith("camera_")
            assert row["source_id"] == "src_a"
            assert row["value"] == "not_published"
            assert row["binding_status"] == NOT_RECORDED  # no bindings recorded
            assert row["capture"] is None
            assert row["upstream"]["status"] == "no_upstream_url_recorded"
            assert row["view_original"]["kind"] == NOT_RECORDED
            assert set(row["epistemics"]) == {
                "directness",
                "reliability",
                "integrity",
                "review_status",
            }
            # a raw claim literal never publishes
            assert "raw_value" not in row and "value_text" not in row


def test_statements_slice_by_own_licence_odbl_separation() -> None:
    """An ODbL claim never lands in a CC-BY statements file (SIG-LIC-004a)."""
    claims = _site("A", "35.46", "-97.51", "Oklahoma", spdx="ODbL-1.0") + _site(
        "B", "48.85", "2.35", "Paris", source_id="fr_src", spdx="CC-BY-4.0"
    )
    export = _build(claims)
    files = _all_statements(export)
    assert len(files) == 2
    for path, rows in files.items():
        comp = path.split("/")[0]
        if comp == "osm_physical":
            assert all(r["source_id"] == "src_a" for r in rows)
            assert all(r["rights"]["spdx"] == "ODbL-1.0" for r in rows)
        else:
            assert all(r["source_id"] == "fr_src" for r in rows)
            assert all(r["rights"]["spdx"] == "CC-BY-4.0" for r in rows)


def test_record_claims_still_emit_and_stay_compatible() -> None:
    """The statements file is additive — the record_claims stream is unchanged."""
    export = _build(_site("A", "35.46", "-97.51", "Oklahoma"))
    rc = json.loads(export.web_artifacts["osm_physical/record_claims.jsonl"].split(b"\n")[0])
    st = _statements(export, "osm_physical")
    row = st[rc["claim_id"]]
    for key in ("claim_id", "entity_id", "predicate_id", "observed_at", "source_id"):
        assert rc[key] == row[key]


# --- deliverable 2: upstream_href through the S-6 gate ----------------------- #


def test_upstream_full_url_on_raw_ok_gate_passed() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma", spdx="CC-BY-4.0")
    raw_over = {
        "evidence_bindings": [("A-src_a-lat", "cap-1", "art-1", "establishes")],
        "claim_binding_detail": [
            _detail_t("A-src_a-lat", artifact_url="https://portal.example.gov/cams")
        ],
        "transparency_source_rights": [_rights_t("src_a")],
    }
    export = _build(claims, raw_over=raw_over)
    row = _statements(export, "sig_graph")["A-src_a-lat"]
    assert row["upstream"]["status"] == "full_url"
    assert row["upstream"]["url"] == "https://portal.example.gov/cams"
    assert row["upstream"]["host"] == "portal.example.gov"


def test_upstream_credentials_stripped() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma", spdx="CC-BY-4.0")
    raw_over = {
        "claim_binding_detail": [
            _detail_t(
                "A-src_a-lat",
                # A credential-shaped param (S-1 CREDENTIAL_QUERY_RE names) —
                # `token=`, not an `api_key=` literal, so the secrets scan
                # (no credential-bearing URL params in tracked files) holds.
                artifact_url="https://portal.example.gov/cams?token=SECRET&page=2",
            )
        ],
        "transparency_source_rights": [_rights_t("src_a")],
    }
    export = _build(claims, raw_over=raw_over)
    row = _statements(export, "sig_graph")["A-src_a-lat"]
    assert "SECRET" not in export.web_artifacts["sig_graph/statements.jsonl"].decode()
    assert row["upstream"]["url"] == "https://portal.example.gov/cams?page=2"


def test_upstream_host_only_for_link_only_lane() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma", spdx="CC-BY-4.0")
    raw_over = {
        "claim_binding_detail": [
            _detail_t("A-src_a-lat", artifact_url="https://docs.example.gov/a/123")
        ],
        "transparency_source_rights": [_rights_t("src_a", custody="LINK")],
    }
    export = _build(claims, raw_over=raw_over)
    row = _statements(export, "sig_graph")["A-src_a-lat"]
    assert row["upstream"]["status"] == "host_only"
    assert row["upstream"]["url"] is None
    assert row["upstream"]["host"] == "docs.example.gov"
    assert row["upstream"]["path_sha256"]


def test_upstream_withheld_for_ip_host() -> None:
    """S-5 wins over S-6 — an IP-literal host publishes nothing."""
    claims = _site("A", "35.46", "-97.51", "Oklahoma", spdx="CC-BY-4.0")
    raw_over = {
        "claim_binding_detail": [_detail_t("A-src_a-lat", artifact_url="http://192.168.0.5/cams")],
        "transparency_source_rights": [_rights_t("src_a")],
    }
    export = _build(claims, raw_over=raw_over)
    row = _statements(export, "sig_graph")["A-src_a-lat"]
    assert row["upstream"]["status"] == "withheld_by_policy"
    assert row["upstream"]["url"] is None
    assert row["upstream"]["path_sha256"] is None


def test_upstream_withheld_for_sealed_part_viii() -> None:
    """A sealed Part VIII class withholds even the host."""
    claims = _site("A", "35.46", "-97.51", "Oklahoma", spdx="CC-BY-4.0")
    raw_over = {
        "claim_binding_detail": [
            _detail_t("A-src_a-lat", artifact_url="https://docs.example.gov/person/123")
        ],
        "transparency_source_rights": [_rights_t("src_a")],
        "transparency_sources": [_view_t("src_a", lane="raw-ok", part_viii_class="P8-1")],
    }
    export = _build(claims, raw_over=raw_over)
    row = _statements(export, "sig_graph")["A-src_a-lat"]
    assert row["upstream"]["status"] == "withheld_by_policy"
    assert "person" not in json.dumps(row["upstream"])
    assert row["view_original"]["kind"] == "not_redistributable"


def test_upstream_no_url_recorded_named_absence() -> None:
    export = _build(_site("A", "35.46", "-97.51", "Oklahoma"))
    row = _statements(export, "osm_physical")["A-src_a-lat"]
    assert row["upstream"]["status"] == "no_upstream_url_recorded"
    assert row["upstream"]["url"] is None


def test_published_record_upstream_href_through_s6() -> None:
    """``source_refs[].upstream_href`` is the S-6 form, never a raw URL."""
    site_row = {
        "entity_id": "A",
        "entity_type": "deployment",
        "source_id": "src_a",
        "spdx": "CC-BY-4.0",
        "claim_ids": ["c1"],
        "_rights": {"source_id": "src_a", "attribution": "© src_a"},
    }
    claim_index = {
        "c1": {
            "schema": STATEMENT_SCHEMA,
            "claim_id": "c1",
            "entity_id": "A",
            "predicate_id": "camera_latitude",
            "observed_at": "2026-05-01",
            "source_id": "src_a",
            "upstream": {
                "status": "host_only",
                "url": None,
                "host": "docs.example.gov",
                "path_sha256": "0123abcd",
            },
        }
    }
    rec = record_from_site_row(
        site_row, compartment="sig_graph", license_id="CC-BY-4.0", claim_index=claim_index
    )
    src = rec.source_refs[0]
    assert src["upstream_href"] == "docs.example.gov#path_sha256:0123abcd"
    assert src["upstream_host"] == "docs.example.gov"
    assert src["upstream_status"] == "host_only"
    # The embedded statement row is the panel's data contract.
    assert rec.claim_statements[0]["claim_id"] == "c1"


def test_published_record_upstream_named_absence_without_statements() -> None:
    """A pre-P35.36 claim index emits the named absence, never a dropped key."""
    rec = record_from_site_row(
        {
            "entity_id": "A",
            "entity_type": "deployment",
            "source_id": "src_a",
            "spdx": "CC-BY-4.0",
            "claim_ids": ["c1"],
            "_rights": {},
        },
        compartment="sig_graph",
        license_id="CC-BY-4.0",
        claim_index={"c1": {"claim_id": "c1", "source_id": "src_a"}},
    )
    assert rec.source_refs[0]["upstream_href"] == "no_upstream_url_recorded"
    assert rec.claim_statements == ()


# --- deliverable 3–4: the shared panel contract + verbatim states ------------ #


def test_all_four_binding_states_render_verbatim() -> None:
    """J3 §5.1's four state sentences render verbatim, slot-filled."""
    base = {"claim_id": "c1", "source_id": "src_a"}
    cases = {
        "actual_capture": {
            **base,
            "binding_status": "actual_capture",
            "capture": {"retrieved_at": "2026-05-01T12:00:00Z", "digest": "sha256:abc"},
            "upstream": {"status": "host_only", "host": "docs.example.gov"},
        },
        "replayed": {
            **base,
            "binding_status": "replayed",
            "capture": {
                "bound_at": "2026-05-02",
                "retrieved_at": "2026-05-01",
            },
        },
        "document_only": {**base, "binding_status": "document_only"},
        "legacy_synthetic": {
            **base,
            "binding_status": "legacy_synthetic",
            "recorded": {"run_id": "run-9", "at": "2026-05-02T00:00:00Z"},
        },
    }
    expected = {
        "actual_capture": "Captured from docs.example.gov on 2026-05-01T12:00:00Z; "
        "sha256 sha256:abc.",
        "replayed": "Re-derived on 2026-05-02 from a capture made on 2026-05-01.",
        "document_only": "Extracted from a document; no page capture.",
        "legacy_synthetic": "Recorded by run run-9 on 2026-05-02. SIG did not keep a "
        "per-record copy of the source for this run; the source's page lists the "
        "run and its captures.",
    }
    for state in BINDING_STATES:
        stmt = cases[state]
        panel = panel_from_statement(stmt, claim_id="c1")
        assert panel["binding_status"] == state
        assert panel["binding_text"] == expected[state]
        # the template is the constant — no surface improvises the wording
        assert BINDING_STATE_TEMPLATES[state].split("{")[0] in panel["binding_text"]


def test_not_recorded_state_is_named_not_fabricated() -> None:
    """A claim with no published binding renders the honest fifth state."""
    panel = panel_from_statement(None, claim_id="c-missing")
    assert panel["binding_status"] == NOT_RECORDED
    assert panel["binding_text"] == BINDING_STATE_TEMPLATES[NOT_RECORDED]
    # every field is a named absence — nothing blank, nothing implied
    html = panel_html(panel)
    assert 'id="claim-c-missing"' in html
    assert "not_recorded" in html
    assert "Captured" not in html and "document" not in panel["binding_text"].lower()


def test_panel_fields_are_never_blank() -> None:
    """Every J3 §5.2 field renders a value or a named absence token."""
    panel = panel_from_statement(
        {
            "claim_id": "c1",
            "source_id": "src_a",
            "binding_status": "legacy_synthetic",
            "recorded": {"run_id": "run-9", "at": "2026-05-02"},
            "rights": {"spdx": "CC-BY-4.0", "attribution": "© src_a"},
        },
        claim_id="c1",
        json_href="/r/p-x/c/sig_graph/entity/deployment/A.json",
    )
    html = panel_html(panel)
    for label in (
        "Source",
        "Binding state",
        "Capture retrieved",
        "Capture digest",
        "Capture bytes",
        "Capture media type",
        "Upstream",
        "View original",
        "Extraction",
        "Directness class",
        "Epistemic tier + review status",
        "Contradictions",
        "Supersession",
        "Rights",
        "Equivalent requests",
        "Dispute",
    ):
        assert f"<dt>{label}</dt>" in html
    assert "<dd></dd>" not in html and "<dd> </dd>" not in html
    assert "Not yet independently reviewed" in html  # unreviewed → §5.2 wording
    assert 'href="/sources/"' in html
    assert "/dispute/" in html


def test_statement_rows_carry_binding_status_and_capture_detail() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma", spdx="CC-BY-4.0")
    raw_over = {
        "claim_binding_detail": [
            _detail_t(
                "A-src_a-lat",
                binding_status="actual_capture",
                byte_size=4096,
                artifact_url="https://portal.example.gov/cams",
            )
        ],
        "claim_provenance": [_provenance_t("A-src_a-lat")],
        "transparency_source_rights": [_rights_t("src_a")],
    }
    export = _build(claims, raw_over=raw_over)
    rows = _statements(export, "sig_graph")
    lat = rows["A-src_a-lat"]
    assert lat["binding_status"] == "actual_capture"
    assert lat["capture"]["byte_size"] == 4096
    assert lat["capture"]["digest"].startswith("sha256:")
    assert lat["epistemics"]["directness"] == "D2"
    assert lat["recorded"]["run_id"] == "run-9"
    assert lat["extraction"]["method"] == "structured_parse"
    assert lat["view_original"]["kind"] == "download_original"
    assert lat["upstream"]["url"] == "https://portal.example.gov/cams"
    # unbound claims stay honest
    assert rows["A-src_a-lon"]["binding_status"] == NOT_RECORDED


def test_statement_upstream_status_is_closed_vocabulary() -> None:
    export = _build(_site("A", "35.46", "-97.51", "Oklahoma"))
    for rows in _all_statements(export).values():
        for row in rows:
            assert row["upstream"]["status"] in UPSTREAM_STATUSES


# --- the release tree ------------------------------------------------------- #


def _stmt_row(comp: str, source: str, lic: str, **over) -> dict:
    row = {
        "schema": STATEMENT_SCHEMA,
        "claim_id": f"claim-{source}-0-a",
        "entity_id": f"ent-{source}-0",
        "predicate_id": "camera_latitude",
        "observed_at": "2026-05-01",
        "source_id": source,
        "value": "not_published",
        "binding_status": "legacy_synthetic",
        "upstream": {"status": "no_upstream_url_recorded", "url": None, "host": None},
        "rights": {"spdx": lic, "compartment": comp},
    }
    row.update(over)
    return row


def test_release_tree_carries_per_compartment_statements(tmp_path: Path) -> None:
    """The release copies each compartment's statements.jsonl into the
    immutable tree — integrity-listed, compartment-licenced."""
    from test_release import _write_export

    export = _write_export(tmp_path / "export", n_records=1)
    for comp, src, lic in (
        ("sig_graph", "src_a", "CC-BY-4.0"),
        ("osm_physical", "src_osm", "ODbL-1.0"),
    ):
        (export / comp / "statements.jsonl").write_text(
            canonical_json(_stmt_row(comp, src, lic)).decode(), encoding="utf-8"
        )
    build = build_release(export, tmp_path / "rel", renderer_revision=REVISION)
    pub = build.publication_id
    for comp in ("sig_graph", "osm_physical"):
        p = tmp_path / "rel" / "r" / pub / "c" / comp / "statements.jsonl"
        assert p.is_file()
        rows = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
        assert rows[0]["schema"] == STATEMENT_SCHEMA
    # statements are indexed for the record pages AND rendered as panels
    page = next(p for p in (tmp_path / "rel").rglob("index.html") if "/entity/" in p.as_posix())
    text = page.read_text()
    assert "provenance-panel" in text
    assert 'id="claim-' in text


def test_release_claim_index_prefers_statements(tmp_path: Path) -> None:
    """A claim covered by BOTH files reads the statements row."""
    from test_release import _write_export

    export = _write_export(tmp_path / "export", n_records=1, two_compartments=False)
    stmt = _stmt_row("sig_graph", "src_a", "CC-BY-4.0", binding_status="document_only")
    (export / "sig_graph" / "statements.jsonl").write_text(
        canonical_json(stmt).decode(), encoding="utf-8"
    )
    from exports.release import _claim_index

    idx = _claim_index(export)
    assert idx["claim-src_a-0-a"]["schema"] == STATEMENT_SCHEMA
    # record_claims rows still index claims statements do not carry
    assert idx["claim-src_a-0-b"]["claim_id"] == "claim-src_a-0-b"


def test_panel_anchor_id_unique_per_claim() -> None:
    p1 = panel_html(panel_from_statement(None, claim_id="c-1"))
    p2 = panel_html(panel_from_statement(None, claim_id="c-2"))
    assert 'id="claim-c-1"' in p1 and 'id="claim-c-2"' in p2
    assert 'data-binding-state="not_recorded"' in p1
