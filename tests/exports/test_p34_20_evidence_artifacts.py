# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.20 (K8 NEW-6 / SIG-EVUI-D04+D08) — the evidence-artifacts export carries
what the /evidence/ interim artifact list needs: the registry ``source_name``,
the honest ``capture_classification`` (synthetic captures are run records,
never presented as captures), and the S-6-scrubbed ``upstream_url`` — all under
the shared ``{PUB_ARTIFACT_GATE}`` publication gate (P32.5/ADR-124)."""

from __future__ import annotations

import json

from exports.spine_export import EXPORT_QUERIES
from test_spine_export import _build, _site


def _evidence_artifact_row(**over):
    """An evidence_artifacts row in the widened P34.20 shape."""
    row = [
        "art-1",  # artifact_id
        "src_a",  # source_id
        "The source document",  # title
        "news_article",  # artifact_type
        "https://example.org/doc",  # stable_locator
        "primary",  # primary_or_secondary
        "captured",  # capture_status
        "2026-09",  # published_at_edtf
        "Example Source",  # source_name (source_registry)
        "synthetic",  # capture_classification (latest evidence_capture)
        "https://example.org/doc",  # upstream_url (S-6 gated; NULL when refused)
    ]
    for k, v in over.items():
        idx = {
            "title": 2,
            "source_name": 8,
            "capture_classification": 9,
            "upstream_url": 10,
        }[k]
        row[idx] = v
    return tuple(row)


def test_evidence_artifacts_query_carries_the_shared_artifact_gate() -> None:
    """SIG-EVUI-D05 / AC3 — the published-artifact list is gated exactly like
    every other surface: the SQL twin of access_decision, never a second
    eligibility rule."""
    guard, sql = EXPORT_QUERIES["evidence_artifacts"]
    assert guard == "evidence_artifact"
    assert "{PUB_ARTIFACT_GATE}" in sql
    assert "sensitivity_tier = 0" in sql
    assert "capture_status = 'captured'" in sql


def test_evidence_artifacts_query_carries_the_list_fields() -> None:
    """K8 NEW-6 — the registry name join, the capture-class read, and the
    effective-rights scrub on the upstream URL are all in the producer query."""
    _guard, sql = EXPORT_QUERIES["evidence_artifacts"]
    # the source display name comes from the registry, never fabricated
    assert "source_registry" in sql and "source_name" in sql
    # the honest capture class is the latest capture's
    assert "capture_classification" in sql and "evidence_capture" in sql
    # S-6: the upstream link only where EFFECTIVE rights are redistributable
    assert "{EFFECTIVE}" in sql  # the latest_decision CTE
    assert "latest_decision" in sql and "rights_record" in sql
    assert "redistributable = 'yes'" in sql


def test_evidence_surface_emits_the_list_fields() -> None:
    """The emitted artifact carries source_name / capture_classification /
    upstream_url when the query produced them — and omits them honestly when
    the query returned NULL (never a fabricated value)."""
    claims = _site("A", "35.46", "-97.51", "Oklahoma")
    rows = [
        _evidence_artifact_row(),
        _evidence_artifact_row(source_name=None, capture_classification=None, upstream_url=None),
    ]
    export = _build(claims, raw_over={"evidence_artifacts": rows})
    evidence = json.loads(export.web_artifacts["web/evidence.json"].decode("utf-8"))
    rich, bare = evidence["artifacts"]
    assert rich["source_name"] == "Example Source"
    assert rich["capture_classification"] == "synthetic"
    assert rich["upstream_url"] == "https://example.org/doc"
    # honest absence: NULL columns emit no key, never "" or a guessed value
    assert "source_name" not in bare
    assert "capture_classification" not in bare
    assert "upstream_url" not in bare


def test_evidence_surface_still_emits_claim_views_empty() -> None:
    """F-416: no claim is bound to a publishable document view yet — the
    claim_views key is an honest empty list (the interim artifact list is the
    page's content)."""
    claims = _site("A", "35.46", "-97.51", "Oklahoma")
    export = _build(claims, raw_over={"evidence_artifacts": [_evidence_artifact_row()]})
    evidence = json.loads(export.web_artifacts["web/evidence.json"].decode("utf-8"))
    assert evidence["claim_views"] == []
