# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.51 (R11-K13-TX-08b) — evidence-anchor capture history + view original.

* ``statements.capture_view_original`` + ``view_original_block(raw_href=…)`` are
  the J3 §5.3 machinery — the lane × Part VIII × bytes-stored table, an S-6-only
  href for ``view_at_source``, and a caller-minted raw locator for the byte
  downloads (never a link to a route the release does not carry).
* ``release_pages.evidence_page`` renders the K8 §4.2 capture history — one row
  per capture with classification (a ``synthetic`` capture is labelled a run
  record) and the per-row view-original state.
"""

from __future__ import annotations

from exports.release_pages import evidence_page
from exports.statements import (
    UPSTREAM_FULL_URL,
    UPSTREAM_HOST_ONLY,
    UPSTREAM_WITHHELD,
    capture_view_original,
    upstream_block,
    view_original_block,
)


def _upstream(status: str) -> dict:
    return {
        "full_url": {
            "status": UPSTREAM_FULL_URL,
            "url": "https://city.example/doc.pdf",
            "host": "city.example",
            "path_sha256": None,
        },
        "host_only": {
            "status": UPSTREAM_HOST_ONLY,
            "url": None,
            "host": "city.example",
            "path_sha256": "ab12cd34",
        },
        "withheld": {"status": UPSTREAM_WITHHELD, "url": None, "host": None, "path_sha256": None},
        "none": {
            "status": "no_upstream_url_recorded",
            "url": None,
            "host": None,
            "path_sha256": None,
        },
    }[status]


def test_view_original_table_covers_every_lane_cell() -> None:
    """J3 §5.3 verbatim: lane × Part VIII × bytes-stored decides the label."""
    # raw-ok clear + bytes → download original
    vo = capture_view_original(
        lane="raw-ok", part_viii_class=None, bytes_stored=True, upstream=_upstream("full_url")
    )
    assert vo["kind"] == "download_original" and vo["label"] == "Download original"
    # raw-ok P8-5/6/8 + bytes → redacted copy
    vo = capture_view_original(
        lane="raw-ok", part_viii_class="P8-5", bytes_stored=True, upstream=_upstream("full_url")
    )
    assert vo["kind"] == "download_redacted"
    # raw-ok, no bytes → view at source + "did not retain"
    vo = capture_view_original(
        lane="raw-ok", part_viii_class=None, bytes_stored=False, upstream=_upstream("full_url")
    )
    assert vo["kind"] == "view_at_source" and vo["href"] == "https://city.example/doc.pdf"
    assert vo["note"] == "SIG did not retain these bytes"
    # derived-only / link-only → view at source (S-6 href only)
    for lane in ("derived-only", "link-only"):
        vo = capture_view_original(
            lane=lane, part_viii_class=None, bytes_stored=False, upstream=_upstream("host_only")
        )
        assert vo["kind"] == "view_at_source" and vo["href"] == "https://city.example/"
    # restricted lane or sealed class → not redistributable, never a URL
    vo = capture_view_original(
        lane="restricted", part_viii_class=None, bytes_stored=True, upstream=_upstream("withheld")
    )
    assert vo["kind"] == "not_redistributable" and vo["href"] is None and "terms" in vo["note"]
    vo = capture_view_original(
        lane="raw-ok", part_viii_class="P8-1", bytes_stored=True, upstream=_upstream("withheld")
    )
    assert vo["kind"] == "not_redistributable" and vo["href"] is None and "P8-1" in vo["note"]
    # unknown → rights not reviewed
    vo = capture_view_original(
        lane="unknown", part_viii_class=None, bytes_stored=False, upstream=_upstream("none")
    )
    assert vo["kind"] == "rights_not_reviewed" and vo["href"] is None


def test_view_original_block_gates_on_binding_and_mints_raw_href() -> None:
    """TX-08b's machinery: a recorded binding + a caller-minted raw locator
    yields the byte-download link; no locator → the label without a link."""
    vo = view_original_block(
        binding_status="actual_capture",
        lane="raw-ok",
        part_viii_class=None,
        bytes_stored=True,
        upstream=_upstream("full_url"),
        raw_href="raw/zQmAb12",
    )
    assert vo["kind"] == "download_original" and vo["href"] == "raw/zQmAb12"
    vo = view_original_block(
        binding_status="actual_capture",
        lane="raw-ok",
        part_viii_class=None,
        bytes_stored=True,
        upstream=_upstream("full_url"),
    )
    assert vo["kind"] == "download_original" and vo["href"] is None
    # no published binding → the named absence, never a label
    vo = view_original_block(
        binding_status="not_recorded",
        lane="raw-ok",
        part_viii_class=None,
        bytes_stored=True,
        upstream=_upstream("full_url"),
        raw_href="raw/x",
    )
    assert vo["kind"] == "not_recorded" and vo["href"] is None


def test_upstream_block_scrubs_per_lane() -> None:
    """The S-6 publication form — full URL only for publishing lanes."""
    full = upstream_block("https://city.example/doc.pdf?token=x", lane="raw-ok", gate_passed=True)
    assert full["status"] == "full_url" and "token" not in (full["url"] or "")
    host_only = upstream_block("https://city.example/doc.pdf", lane="link-only", gate_passed=True)
    assert host_only["status"] == "host_only" and host_only["url"] is None
    assert host_only["path_sha256"]
    withheld = upstream_block(
        "https://city.example/doc.pdf", lane="raw-ok", gate_passed=True, part_viii_class="P8-1"
    )
    assert withheld["status"] == "withheld_by_policy" and withheld["url"] is None


def _artifact(captures: list[dict]) -> dict:
    return {
        "artifact_id": "art-1",
        "title": "OKC procurement portal — solicitation NA230000215",
        "source": "okc_procurement",
        "artifact_type": "web_page",
        "directness": "primary",
        "currency": "2026-06",
        "capture_status": "captured",
        "permalink": "evd:okc:na230000215",
        "lane": "raw-ok",
        "lane_basis": "registry:[redistribution]",
        "part_viii_class": None,
        "upstream": _upstream("full_url"),
        "captures": captures,
    }


def test_evidence_page_renders_capture_history_and_view_original() -> None:
    """K8 §4.2: one row per capture — digest/bytes/media/HTTP/method/
    classification/tier — each with its J3 §5.3 view-original state."""
    art = _artifact(
        [
            {
                "capture_id": "cap-1",
                "retrieved_at": "2026-06-01T00:00:00+00:00",
                "content_digest": "zQmDigest1",
                "digest_blake3": "b3:aa11",
                "byte_size": 512,
                "media_type": "text/html",
                "http_status": 200,
                "capture_method": "http_get",
                "storage_tier": "public",
                "capture_classification": "actual",
                "view_original": {
                    "kind": "download_original",
                    "label": "Download original",
                    "href": None,
                    "note": None,
                },
            },
            {
                "capture_id": "cap-2",
                "retrieved_at": "2026-07-01T00:00:00+00:00",
                "content_digest": "zQmDigest2",
                "byte_size": 0,
                "media_type": "text/html",
                "http_status": 200,
                "capture_method": "http_get",
                "storage_tier": "public",
                "capture_classification": "synthetic",
                "view_original": {
                    "kind": "view_at_source",
                    "label": "View at source",
                    "href": "https://city.example/doc.pdf",
                    "note": "SIG did not retain these bytes",
                },
            },
        ]
    )
    html = evidence_page(
        publication_id="p-abc", compartment="web", artifact=art, licence="CC-BY-4.0"
    ).decode()
    assert "Capture history" in html
    assert "cap-1" in html and "cap-2" in html
    assert "zQmDigest1" in html and "b3:aa11" in html
    assert "run record" in html  # the synthetic row is labelled
    assert "Download original" in html
    assert 'href="https://city.example/doc.pdf"' in html  # the S-6 href
    assert "SIG did not retain these bytes" in html
    # the upstream block renders the gated URL
    assert "Upstream" in html and "city.example/doc.pdf" in html
    assert "<script" not in html  # T0 — no script ever


def test_evidence_page_states_an_empty_capture_history() -> None:
    """A publishable artifact with no captures renders the typed empty state."""
    html = evidence_page(
        publication_id="p-abc", compartment="web", artifact=_artifact([]), licence="CC-BY-4.0"
    ).decode()
    assert "No captures are published for this artifact" in html


def test_evidence_page_withheld_upstream_never_links() -> None:
    """A sealed-class artifact shows the named absence — no URL (S-5/S-6)."""
    art = _artifact([])
    art["upstream"] = _upstream("withheld")
    html = evidence_page(
        publication_id="p-abc", compartment="web", artifact=art, licence="CC-BY-4.0"
    ).decode()
    assert "withheld_by_policy" in html
    assert "city.example" not in html
