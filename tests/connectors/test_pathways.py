# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `pathways` connector — Stage-5 P17 pathway population (§46, P21.9, ADR-071).

Pins the deliverables: the connector is registered; it emits typed, evidenced P17 claims
through the ADR-033-deferred parser layers; the procured≠deployed epistemic rule
(RISK-P21-16) is enforced at both the genre and predicate level; the LINK-posture sources
refuse a live run (exit 3, LiveGateRefused); and a shadow replay over the committed
fixtures is byte-identical (0 diffs, SIG-INGEST-019).
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from connectors.net import FetchResult, PoliteFetcher, RobotsResult
from connectors.pipeline import run
from connectors.registry import CompactStatus, CustodyPosture, get
from connectors.replay import shadow_replay
from connectors.runner import LiveGateRefused, RunMode, run_source
from connectors.stages import (
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
    registered_connectors,
)
from evidence.ingest_run import IngestRun
from parsing.genre import DEPLOYMENT_GENRES, DocumentGenre

from connectors import pathways as pw

_FIX = Path(__file__).parent / "fixtures" / "pathways"
_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"
_FAMILIES = ("rtcc_federation", "fr_css_forensics", "acoustic_drone_location")


class _StaticTransport:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ROBOTS_ALLOW_ALL)

    def request(self, url: str, *, user_agent: str) -> FetchResult:
        return FetchResult(
            url=url,
            status=200,
            body=self._body,
            media_type="application/json",
            retrieved_at=datetime(2026, 8, 20, tzinfo=UTC),
        )


def _flipped_ctx(source_id: str, fixture: str) -> RunContext:
    """A RunContext for a FLIPPED source (post-packet state; the seed stays gated)."""
    transport = _StaticTransport((_FIX / fixture).read_bytes())
    fetcher = PoliteFetcher(
        connector_name="pathways", connector_version="1.0.0", transport=transport
    )
    source = dataclasses.replace(
        get(source_id),
        ingestion_permitted=True,
        custody_posture=CustodyPosture.REFERENCE,
        compact_status=CompactStatus.PUBLIC_TERMS_ONLY,
    )
    return RunContext(
        source=source,
        run=IngestRun("pathways", "1.0.0", "deadbeef", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": [{"id": "t1", "url": f"https://{source_id}/x", "kind": "bulk"}]},
    )


def _run_family(family: str) -> list[dict[str, Any]]:
    source_id = pw.pathway_family_source(family)
    ctx = _flipped_ctx(source_id, f"{family}.json")
    return run(pw.PathwaysConnector(), ctx).claims


# --- registration + gating ----------------------------------------------------


def test_connector_is_registered() -> None:
    assert "pathways" in registered_connectors()


def test_all_three_family_sources_keep_link_posture_and_are_gated() -> None:
    # §22.7 / HG-03: the sources stay LINK-posture and not-yet-permitted; a live run
    # against each REFUSES before any fetch (exit 3 via LiveGateRefused).
    for family in _FAMILIES:
        sid = pw.pathway_family_source(family)
        rec = get(sid)
        assert rec.custody_posture.value == "LINK"
        assert rec.ingestion_permitted is False
        assert rec.rights.spdx.strip().upper() == "UNDETERMINED"
        with pytest.raises(LiveGateRefused):
            run_source(sid, mode=RunMode.LIVE)


# --- claims are typed + evidenced ---------------------------------------------


@pytest.mark.parametrize("family", _FAMILIES)
def test_family_emits_typed_evidenced_claims(family: str) -> None:
    claims = _run_family(family)
    assert claims
    for c in claims:
        assert c["claim_type"] in pw.claim_types()  # typed (§3.1)
        assert c["predicate_id"] in pw.predicate_allowlist()
        assert c["raw_value"] is not None  # P2 preserved
        ev = c["evidence"]
        assert ev["source_url"] and ev["retrieved_date"]  # evidenced + dated
        assert ev["locator"] and ev["extraction_method"]  # locator mandatory (SIG-PARSE-003)


def test_parser_layers_are_exercised() -> None:
    # The ADR-033-deferred layers actually run: pdf_table (procurement) + pdf_text (policy).
    methods = {c["evidence"]["extraction_method"] for f in _FAMILIES for c in _run_family(f)}
    assert "pdf_table" in methods  # layer-4 table extraction (parsing.tables)
    assert "pdf_text" in methods  # layer-3 clause locator (parsing.clauses)


# --- the procured != deployed epistemic rule (RISK-P21-16, §46) ---------------


def test_no_deployment_claim_originates_from_a_procurement_genre_document() -> None:
    # AC: "no claim of type `deployed` originates from a procurement-genre fixture."
    for family in _FAMILIES:
        for c in _run_family(family):
            if c["claim_type"] == "deployment":
                assert c["document_genre"] in {g.value for g in DEPLOYMENT_GENRES}
                assert c["document_genre"] != DocumentGenre.PROCUREMENT_RECORD.value


def test_deployment_claim_from_procurement_genre_is_refused() -> None:
    # The genre-level guard: a deployment claim from a procurement record raises.
    ctx = pw.DocumentContext(
        source_id="pathways_rtcc_federation",
        source_url="https://example/x",
        retrieved_date="2026-08-20",
        genre=DocumentGenre.PROCUREMENT_RECORD,
        conformance_pathway="rtcc_hub",
        pathway_family="rtcc_federation",
    )
    with pytest.raises(pw.DeploymentInferenceError):
        pw.pathway_claim(
            ctx,
            claim_type="deployment",
            subject_kind="deployment",
            subject_id="dep:x",
            predicate="deployed",
            value=True,
            raw_value="True",
            extraction_method="pdf_table",
            locator={"kind": "row", "row": 0},
        )


def test_deployment_predicate_on_a_non_deployment_claim_is_refused() -> None:
    # The predicate-level guard behind the genre gate: a deployment predicate may ride
    # only on a deployment claim, even from a deployment-genre document.
    ctx = pw.DocumentContext(
        source_id="pathways_fr_css_forensics",
        source_url="https://example/x",
        retrieved_date="2026-08-20",
        genre=DocumentGenre.DEPLOYMENT_REPORT,
        conformance_pathway="css_and_forensics",
        pathway_family="fr_css_forensics",
    )
    with pytest.raises(pw.DeploymentInferenceError):
        pw.pathway_claim(
            ctx,
            claim_type="vendor_product",
            subject_kind="deployment",
            subject_id="dep:x",
            predicate="in_operation",
            value=True,
            raw_value="True",
            extraction_method="structured_import",
            locator={"kind": "row", "row": 0},
        )


def test_deployment_claim_from_deployment_report_is_admitted() -> None:
    # The positive case: a deployment claim IS admitted from a deployment-genre document.
    ctx = pw.DocumentContext(
        source_id="pathways_acoustic_drone_location",
        source_url="https://example/x",
        retrieved_date="2026-08-20",
        genre=DocumentGenre.DEPLOYMENT_REPORT,
        conformance_pathway="gunshot_detection",
        pathway_family="acoustic_drone_location",
    )
    claim = pw.pathway_claim(
        ctx,
        claim_type="deployment",
        subject_kind="deployment",
        subject_id="dep:gunshot-city-pd",
        predicate="deployed",
        value=True,
        raw_value="True",
        extraction_method="structured_import",
        locator={"kind": "row", "row": 0},
    )
    assert claim["claim_type"] == "deployment"
    assert claim["document_genre"] == "deployment_report"


def test_mislabelled_genre_is_rejected_genre_is_re_derived_from_text() -> None:
    # RISK-P21-16: the genre used for the guard is DERIVED from the document text, not
    # trusted from the fixture label. A procurement document mislabelled as a deployment
    # report is rejected at extraction.
    doc = {
        "pathway_family": "rtcc_federation",
        "documents": [
            {
                "id": "mislabelled",
                "conformance_pathway": "rtcc_hub",
                "genre": "deployment_report",
                "kind": "assertions",
                "source_url": "https://example/x",
                "text": "Purchase Order 999. Vendor | Product | Amount. sole source contract no.",
                "subject_id": "dep:x",
                "assertions": [
                    {"predicate": "deployed", "value": True, "claim_type": "deployment"}
                ],
            }
        ],
    }
    with pytest.raises(pw.ClaimTypeNotPermitted):
        pw.extract_documents(doc)


def test_predicate_allowlist_is_enforced() -> None:
    with pytest.raises(pw.PredicateNotAllowed):
        pw.assert_predicate_allowed("per_person_location")


def test_deployment_genres_stay_in_lockstep_with_parsing() -> None:
    # The vocab mirror of parsing.genre.DEPLOYMENT_GENRES must not drift.
    assert pw.deployment_genres() == DEPLOYMENT_GENRES


# --- shadow determinism (SIG-INGEST-019) --------------------------------------


@pytest.mark.parametrize("family", _FAMILIES)
def test_shadow_replay_over_fixture_has_zero_diffs(family: str) -> None:
    source_id = pw.pathway_family_source(family)
    ctx = _flipped_ctx(source_id, f"{family}.json")
    report = run(pw.PathwaysConnector(), ctx)
    diff = shadow_replay(pw.PathwaysConnector(), ctx, report.captures, report.claims)
    assert diff.changed_count == 0


def test_fixtures_have_a_sources_md() -> None:
    # AC: each fixture directory cites the public document URL + retrieval date.
    assert (_FIX / "SOURCES.md").exists()
    text = (_FIX / "SOURCES.md").read_text()
    for family in _FAMILIES:
        assert f"{family}.json" in text
