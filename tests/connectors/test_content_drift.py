# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Document-connector content-drift hardening (P25.1 / ADR-082).

A live fetch returns the raw document (a PDF / a web page), not the structured
fixture envelope the OKC document connectors consume. Rather than crash with an
opaque error or emit garbage, the connector raises :class:`ContentDrift` (fail
loud, recorded — 0 claims). Replay/shadow over the committed fixtures is unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from connectors.okc_documents import extract_documents, parse_okc_document
from connectors.runner import FetchRecord
from connectors.stages import ContentDrift

_FIXTURE = Path(__file__).parent / "fixtures" / "okc" / "okc_procurement.json"


def test_content_drift_is_a_valueerror_for_backcompat() -> None:
    assert issubclass(ContentDrift, ValueError)


def test_valid_fixture_still_parses() -> None:
    """The committed structured fixture parses unchanged (shadow/replay path)."""
    payload = parse_okc_document("okc_procurement", _FIXTURE.read_bytes())
    assert "connector" in payload and "documents" in payload


def test_live_pdf_bytes_raise_content_drift_not_garbage() -> None:
    with pytest.raises(ContentDrift) as exc:
        parse_okc_document("okc_procurement", b"%PDF-1.7\n1 0 obj<< >>endobj\n")
    assert "okc_procurement" in str(exc.value)
    assert "PDF" in str(exc.value)


def test_live_html_page_raises_content_drift() -> None:
    with pytest.raises(ContentDrift):
        parse_okc_document("okc_procurement", b"<!doctype html><html><body>hi</body></html>")


def test_unexpected_json_shape_raises_content_drift() -> None:
    with pytest.raises(ContentDrift):
        parse_okc_document("okc_procurement", json.dumps({"something": "else"}).encode("utf-8"))


def test_missing_expected_clause_raises_content_drift() -> None:
    """A fetched policy doc that no longer contains the cited clause fails loud."""
    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "okc" / "okcpd_policy.json").read_text()
    )
    fixture["documents"][0]["clauses"][0]["clause"] = "99-999-does-not-exist"
    with pytest.raises(ContentDrift):
        extract_documents("okcpd_policy", fixture)


def test_fetch_record_carries_content_drift_field() -> None:
    """The fetch record records the drift (0 claims), so a live run is auditable."""
    rec = FetchRecord(
        source_id="okc_procurement",
        connector="okc_procurement",
        mode="live",
        started_at="2026-09-15T00:00:00+00:00",
        duration_seconds=0.1,
        content_drift="content drift for source 'okc_procurement': ...",
    )
    d = rec.to_dict()
    assert d["content_drift"] and d["claim_count"] == 0
