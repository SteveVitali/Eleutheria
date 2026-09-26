# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P25.5 live-extraction adapters — field claims from captured bytes, fail-closed.

These tests drive the REAL ``pipeline.run`` over a per-URL canned transport (no
network, SIG-INGEST-011): the index/feed/document fixtures under
``tests/connectors/fixtures/`` stand in for the captured upstream bytes, and the
``discover_more`` continuation fetches resolved children through the same
fetcher — so bounded fan-out, per-child dispositions, drift refusal, and the
privacy/epistemic guards are exercised end to end.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest
from connectors.france_belgium import parse_atom_feed, parse_raa_index
from connectors.net import PoliteFetcher, RobotsResult
from connectors.pipeline import run
from connectors.registry import get
from connectors.stages import (
    ContentDrift,
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
    registered_connectors,
)
from evidence.ingest_run import IngestRun
from support import minimal_pdf

_FIX = Path(__file__).resolve().parent / "fixtures"
_FRA = _FIX / "france"
_CCOPS = _FIX / "ccops"
_PW = _FIX / "pathways"

_RETRIEVED = datetime(2026, 9, 15, tzinfo=UTC)
_ALLOW_ALL = "User-agent: *\nAllow: /\n"


class MapTransport:
    """Per-URL canned responses + per-host robots — no real network."""

    def __init__(
        self,
        responses: Mapping[str, FetchResult],
        *,
        disallow_hosts: frozenset[str] = frozenset(),
    ) -> None:
        self._responses = dict(responses)
        self._disallow = disallow_hosts
        self.request_log: list[str] = []
        self.robots_log: list[str] = []

    def robots(self, robots_url: str) -> RobotsResult:
        self.robots_log.append(robots_url)
        if urlparse(robots_url).netloc in self._disallow:
            return RobotsResult(text="User-agent: *\nDisallow: /")
        return RobotsResult(text=_ALLOW_ALL)

    def request(
        self,
        url: str,
        *,
        user_agent: str,
        headers: Mapping[str, str] | None = None,
        body: bytes | None = None,
    ) -> FetchResult:
        self.request_log.append(url)
        result = self._responses[url]
        return dataclasses.replace(result, url=url)


def _resp(url: str, body: bytes, media_type: str, status: int = 200) -> FetchResult:
    return FetchResult(
        url=url,
        status=status,
        body=body,
        media_type=media_type,
        retrieved_at=_RETRIEVED,
    )


def _run(
    source_id: str,
    connector_name: str,
    targets: list[dict[str, Any]],
    responses: Mapping[str, FetchResult],
    *,
    disallow_hosts: frozenset[str] = frozenset(),
) -> tuple[Any, MapTransport]:
    report, transport, _ctx = _run_ctx(
        source_id, connector_name, targets, responses, disallow_hosts=disallow_hosts
    )
    return report, transport


def _run_ctx(
    source_id: str,
    connector_name: str,
    targets: list[dict[str, Any]],
    responses: Mapping[str, FetchResult],
    *,
    disallow_hosts: frozenset[str] = frozenset(),
) -> tuple[Any, MapTransport, RunContext]:
    connector = registered_connectors()[connector_name]()
    source = dataclasses.replace(get(source_id), ingestion_permitted=True)
    transport = MapTransport(responses, disallow_hosts=disallow_hosts)
    fetcher = PoliteFetcher(
        connector_name=connector.name,
        connector_version=connector.version,
        transport=transport,
    )
    ctx = RunContext(
        source=source,
        run=IngestRun(connector.name, connector.version, "test", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": targets},
    )
    return run(connector, ctx), transport, ctx


# --- RAA prefectures: resource index → bounded instrument documents -----------


_RAA_INDEX_URL = "https://static.data.gouv.fr/x/raa-des-prefectures.csv"


def _raa_targets(**spec: Any) -> list[dict[str, Any]]:
    return [{"id": "raa-index", "url": _RAA_INDEX_URL, "kind": "resource_index", **spec}]


def _raa_responses(pdf: bytes | None = None, status: int = 200) -> dict[str, FetchResult]:
    index = _FRA.joinpath("raa_index.csv").read_bytes()
    pdf = pdf if pdf is not None else minimal_pdf([["Arrêté préfectoral", "vu le code"]])
    responses: dict[str, FetchResult] = {
        _RAA_INDEX_URL: _resp(_RAA_INDEX_URL, index, "text/csv"),
    }
    for url in (
        "https://www.yonne.gouv.fr/contenu/telechargement/66000/490001/file/raa_89_2026_01.pdf",
        "https://www.ain.gouv.fr/contenu/telechargement/11000/50001/file/raa_01_2026_02.pdf",
        "https://www.nord.gouv.fr/contenu/telechargement/59000/60001/file/raa_59_2026_03.pdf",
        "https://www.paris.fr/contenu/raa/raa_75_2026_04.pdf",
        "https://www.manche.fr/raa/raa_50_2026_04.pdf",
    ):
        responses[url] = _resp(url, pdf, "application/pdf", status=status)
    return responses


def test_raa_index_parse_is_strict() -> None:
    index = parse_raa_index(
        _FRA.joinpath("raa_index.csv").read_bytes(), source_id="raa_prefectures"
    )
    assert index.header == ("titre", "url", "departement", "mise_a_jour")
    # The empty-departement row is malformed (counted, skipped), not drift.
    assert index.malformed_count == 1
    assert index.entry_count == 8


def test_raa_index_header_drift_fails_closed() -> None:
    drifted = b"titre;lien;departement;mise_a_jour\nfoo;https://x/y.pdf;89;2026-09-14\n"
    with pytest.raises(ContentDrift):
        parse_raa_index(drifted, source_id="raa_prefectures")


def test_raa_index_empty_capture_is_drift() -> None:
    with pytest.raises(ContentDrift):
        parse_raa_index(b"", source_id="raa_prefectures")


def test_raa_fanout_is_bounded_and_yields_arrete_claims() -> None:
    report, transport = _run(
        "raa_prefectures",
        "france_belgium_records",
        _raa_targets(max_documents=2),
        _raa_responses(),
    )
    children = [u for u in transport.request_log if u != _RAA_INDEX_URL]
    assert children == [
        "https://www.yonne.gouv.fr/contenu/telechargement/66000/490001/file/raa_89_2026_01.pdf",
        "https://www.ain.gouv.fr/contenu/telechargement/11000/50001/file/raa_01_2026_02.pdf",
    ]
    instruments = [r for r in report.claims if r.get("record_kind") == "legal_instrument"]
    assert len(instruments) == 2
    yonne = next(r for r in instruments if "raa_89_2026_01" in r["external_id"])
    assert yonne["instrument_type"] == "fr.arrete_prefectoral"
    claims = {
        r["predicate_id"]: r
        for r in report.claims
        if r.get("record_kind") == "claim" and r.get("subject_id") == yonne["subject_id"]
    }
    # The titre literal "du 05 janvier 2026" → effective_from; CSI L252 derives
    # the five-year sunset, marked derived — never stored.
    assert claims["effective_from"]["value"] == "2026-01-05"
    sunset = claims["sunset_date"]
    assert sunset["value"] == "2031-01-05"
    assert sunset["derived"] is True
    assert sunset["derivation"] == "csi_l252_five_year_validity"
    assert claims["jurisdiction"]["value"] == "89"
    # Evidence completeness: source url, retrieval date, method, row locator.
    ev = sunset["evidence"]
    assert ev["source_url"].endswith("raa_89_2026_01.pdf")
    assert ev["retrieved_date"] == "2026-09-15"
    assert ev["extraction_method"] == "structured_import"
    assert ev["locator"]["kind"] == "row"
    assert sunset["observed_at"] == "2026-09-15"


def test_raa_fanout_respects_departement_and_https_bounds() -> None:
    report, transport = _run(
        "raa_prefectures",
        "france_belgium_records",
        _raa_targets(departements=["75"]),
        _raa_responses(),
    )
    children = [u for u in transport.request_log if u != _RAA_INDEX_URL]
    # Only the Paris row survives the departement allowlist; the 2A row is
    # http-only (dropped by require_https), the no-dept row is malformed.
    assert children == ["https://www.paris.fr/contenu/raa/raa_75_2026_04.pdf"]


def test_raa_index_drift_in_the_run_propagates() -> None:
    drifted = b"col1;col2\na;b\n"
    responses = {_RAA_INDEX_URL: _resp(_RAA_INDEX_URL, drifted, "text/csv")}
    with pytest.raises(ContentDrift):
        _run(
            "raa_prefectures",
            "france_belgium_records",
            _raa_targets(),
            responses,
        )


def test_raa_child_disappearance_is_recorded_not_fatal() -> None:
    report, transport = _run(
        "raa_prefectures",
        "france_belgium_records",
        _raa_targets(max_documents=2),
        _raa_responses(status=404),
    )
    assert len(report.disappearances) == 2
    # No instrument claims, but the index capture itself is still evidenced.
    assert not [r for r in report.claims if r.get("record_kind") == "legal_instrument"]
    assert any(r.get("record_kind") == "evidence_artifact" for r in report.claims)


def test_raa_child_robots_disallow_is_recorded_and_fetched() -> None:
    # GL-GATE-08 / ADR-088: a per-document robots Disallow no longer refuses —
    # the documents are fetched and each fetch is marked robots_disregarded.
    report, _, ctx = _run_ctx(
        "raa_prefectures",
        "france_belgium_records",
        _raa_targets(max_documents=2),
        _raa_responses(),
        disallow_hosts=frozenset({"www.yonne.gouv.fr", "www.ain.gouv.fr"}),
    )
    assert not [r for r in report.refusals if "RobotsDisallowed" in r["refusal"]]
    disregarded = ctx.fetcher.robots_disregarded
    assert len(disregarded) == 2
    assert all(d["verdict"] == "disallowed" for d in disregarded)
    # The seed index fetch still succeeded — the run did not die.
    assert any(r.get("record_kind") == "quality_report" for r in report.claims)


# --- MaDada: Atom feed → records-request contexts, request text never kept ----


_MADADA_URL = "https://madada.fr/feed/search/%20x"


def _madada_run(body: bytes | None = None):
    body = body if body is not None else _FRA.joinpath("madada_feed.atom").read_bytes()
    return _run(
        "madada",
        "france_belgium_records",
        [{"id": "madada-feed", "url": _MADADA_URL, "kind": "feed"}],
        {_MADADA_URL: _resp(_MADADA_URL, body, "application/atom+xml")},
    )


def test_madada_feed_parses_entries() -> None:
    entries = parse_atom_feed(_FRA.joinpath("madada_feed.atom").read_bytes(), source_id="madada")
    assert len(entries) == 2
    assert entries[0].atom_id == "tag:madada.fr,2026:InfoRequestEvent/1042"


def test_madada_feed_emits_cada_contexts_and_never_request_text() -> None:
    report, _ = _madada_run()
    claims = [r for r in report.claims if r.get("record_kind") == "claim"]
    assert len(claims) == 2
    for claim in claims:
        assert claim["predicate_id"] == "acquisition_method"
        assert claim["value"] == "fr.cada"
        assert claim["subject_id"].startswith("madada:request_event/")
        ev = claim["evidence"]
        assert ev["locator"]["kind"] == "row"
        assert ev["source_url"].startswith("https://madada.fr/request/")
    # Request text is never retained anywhere in the emitted rows.
    rendered = str(report.claims)
    for leaked in (
        "registre des caméras",
        "Je vous prie",
        "Madame Durant",
        "Monsieur Martin",
        "Demande CADA",
        "Transparence",
    ):
        assert leaked not in rendered, leaked


def test_madada_feed_shape_drift_fails_closed() -> None:
    with pytest.raises(ContentDrift):
        _madada_run(b"<rss><item/></rss>")
    with pytest.raises(ContentDrift):
        _madada_run(
            b'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">'
            b"<entry><id>x</id></entry></feed>"  # no link — the entry shape changed
        )


# --- declarationcamera_be: the Belgian eID boundary is honest -----------------


def test_declarationcamera_be_has_no_anonymous_target() -> None:
    # The register sits behind Belgian eID — no anonymous path is registered and
    # the runner refuses rather than inventing one (HG-04; PARTIAL/OPEN).
    from connectors.live_targets import NoLiveTargets, live_targets
    from connectors.runner import RunMode, run_source

    assert live_targets("declarationcamera_be") == []
    with pytest.raises(NoLiveTargets):
        run_source("declarationcamera_be", mode=RunMode.LIVE)


# --- CCOPS: index page → bounded disclosure documents -------------------------


_NYC_INDEX_URL = "https://www.nyc.gov/site/nypd/about/about-nypd/policy/post-act.page"
_ALPR_PDF_URL = (
    "https://www.nyc.gov/assets/nypd/downloads/pdf/post-final/"
    "automatic-license-plate-readers-nypd-impact-and-use-policy_2.4.26.pdf"
)
_CSS_PDF_URL = (
    "https://www.nyc.gov/assets/nypd/downloads/pdf/post-final/"
    "cell-site-simulators-nypd-impact-and-use-policy_2.4.26.pdf"
)
_SS_PDF_URL = (
    "https://www.nyc.gov/assets/nypd/downloads/pdf/post-final/"
    "shotspotter-nypd-impact-and-use-policy_2.4.26.pdf"
)

# An IUP-shaped single page: every mandated section heading except
# DISPARATE IMPACTS (absent), with PUBLIC ACCESS OR USE left empty
# (present_but_empty). The page carries its own UPDATED: revision literal.
_IUP_LINES = [
    "CELL-SITE SIMULATORS:",
    "IMPACT & USE POLICY",
    "UPDATED: FEBRUARY 4, 2026",
    "The POST Act requires the NYPD to publish impact and use policies.",
    "I. CAPABILITIES OF THE TECHNOLOGY",
    "Cell-site simulators can locate devices within their range.",
    "II. RULES, PROCESSES & GUIDELINES",
    "Use requires supervisory approval under these rules.",
    "III. SAFEGUARD & SECURITY MEASURES",
    "Access is restricted and logged by the department.",
    "IV. RETENTION, ACCESS & USE",
    "Data is retained for up to 90 days and access is audited.",
    "V. PUBLIC ACCESS OR USE",
    "VI. EXTERNAL ENTITIES",
    "Data may be shared with partner agencies as authorized.",
    "VII. TRAINING",
    "Operators receive department training before use.",
    "VIII. INTERNAL AUDIT & OVERSIGHT",
    "Oversight is provided by audit units.",
    "IX. HEALTH & SAFETY REPORTING",
    "Health and safety impacts are reported.",
]


def _nyc_responses(child: bytes | None = None, status: int = 200) -> dict[str, FetchResult]:
    index = _CCOPS.joinpath("post_act_index.html").read_bytes()
    child = child if child is not None else minimal_pdf([_IUP_LINES])
    responses = {
        _NYC_INDEX_URL: _resp(_NYC_INDEX_URL, index, "text/html"),
        _CSS_PDF_URL: _resp(_CSS_PDF_URL, child, "application/pdf", status=status),
        _ALPR_PDF_URL: _resp(_ALPR_PDF_URL, child, "application/pdf", status=status),
        _SS_PDF_URL: _resp(_SS_PDF_URL, child, "application/pdf", status=status),
    }
    return responses


def test_ccops_index_discovers_bounded_filings_and_extracts_fields() -> None:
    report, transport = _run(
        "ccops_nyc_post",
        "government_mandated_disclosure",
        [{"id": "post-index", "url": _NYC_INDEX_URL, "kind": "index_page", "max_documents": 2}],
        _nyc_responses(),
    )
    children = [u for u in transport.request_log if u != _NYC_INDEX_URL]
    # Two spec-matching /post-final/*.pdf links, bounded at max_documents=2; the
    # contact link and the off-host council link never resolve.
    assert children == [_CSS_PDF_URL, _ALPR_PDF_URL]
    kinds = [r["record_kind"] for r in report.claims]
    assert "index_page" in kinds and "evidence_artifact" in kinds
    claims = [r for r in report.claims if r.get("record_kind") == "claim"]
    assert claims
    css = [c for c in claims if "cell-site-simulators" in str(c["evidence"]["source_url"])]
    assert css, "no claims from the cell-site-simulators filing"
    by_pred = {c["predicate_id"]: c for c in css}
    assert by_pred["ordinance_citation"]["claim_type"] == "ordinance"
    assert by_pred["ordinance_citation"]["value"] == "NYC Administrative Code § 14-189 (POST Act)"
    assert by_pred["ordinance_citation"]["raw_value"] == "POST Act"
    assert by_pred["technology"]["value"] == "Cell-Site Simulators"
    assert by_pred["technology"]["raw_value"] == "CELL-SITE SIMULATORS"
    assert by_pred["technology"]["evidence"]["extraction_method"] == "pdf_text"
    assert by_pred["technology"]["evidence"]["locator"]["kind"] == "page"
    assert by_pred["legal_authority"]["raw_value"] == "POST Act"
    assert by_pred["retention_period"]["raw_value"].lower().endswith("90 days")
    # Every claim is a per-agency aggregate row, dated + evidenced. Ordinance
    # claims are jurisdiction-scoped and key on the enacting body (the
    # _ordinance_claims convention); disclosure claims key on the agency.
    # Filing-derived claims carry the filing's revision as reporting_period;
    # index-page claims carry the observation date.
    for claim in claims:
        from_index = "post-act.page" in str(claim["evidence"]["source_url"])
        if claim["claim_type"] == "ordinance":
            assert claim["agency"] == "New York City Council"
        else:
            assert claim["agency"] == "New York City Police Department"
        assert claim["reporting_period"] == ("2026-09-15" if from_index else "2026-02-04")
        assert claim["aggregate_level"] == "agency_technology_period"
        assert claim["observed_at"] == "2026-09-15"
    # Mandated != populated: field states are recorded, never fabricated.
    states = {
        c["raw_value"]: c["value"] for c in css if c["predicate_id"] == "disclosure_field_state"
    }
    assert states["capabilities"] == "answered"
    assert states["retention_access_use"] == "answered"
    assert states["public_access"] == "present_but_empty"
    assert states["disparate_impacts"] == "absent"


def test_ccops_index_page_with_no_filing_links_is_drift() -> None:
    bare = b"<html><body><h1>POST Act</h1><p>nothing linked</p></body></html>"
    with pytest.raises(ContentDrift):
        _run(
            "ccops_nyc_post",
            "government_mandated_disclosure",
            [{"id": "post-index", "url": _NYC_INDEX_URL, "kind": "index_page"}],
            {_NYC_INDEX_URL: _resp(_NYC_INDEX_URL, bare, "text/html")},
        )


def test_ccops_document_without_text_is_an_artifact_only() -> None:
    # An image-only/malformed PDF yields no text layer: the capture is evidence,
    # never fabricated fields.
    report, _ = _run(
        "ccops_nyc_post",
        "government_mandated_disclosure",
        [{"id": "doc", "url": _CSS_PDF_URL, "kind": "disclosure_document"}],
        {_CSS_PDF_URL: _resp(_CSS_PDF_URL, b"%PDF-1.4\nbroken", "application/pdf")},
    )
    kinds = [r["record_kind"] for r in report.claims]
    assert "evidence_artifact" in kinds
    assert "claim" not in kinds


def test_ccops_part_viii_token_in_a_literal_suppresses_not_crashes() -> None:
    # The real ALPR filing's technology name literally contains a forbidden
    # Part VIII token: the claim is suppressed and the suppression recorded on
    # the artifact row — never emitted, never a crash.
    alpr_lines = list(_IUP_LINES)
    alpr_lines[0] = "AUTOMATIC LICENSE PLATE READERS:"
    report, _ = _run(
        "ccops_nyc_post",
        "government_mandated_disclosure",
        [{"id": "post-index", "url": _NYC_INDEX_URL, "kind": "index_page", "max_documents": 1}],
        _nyc_responses(child=minimal_pdf([alpr_lines])),
    )
    claims = [r for r in report.claims if r.get("record_kind") == "claim"]
    assert not any(c["predicate_id"] == "technology" for c in claims)
    artifacts = [r for r in report.claims if r.get("record_kind") == "evidence_artifact"]
    assert any(a.get("part_viii_suppressions") for a in artifacts)


# --- Pathways: captured documents → genre-gated claims ------------------------


_EFF_RTCC_URL = (
    "https://www.eff.org/deeplinks/2023/05/"
    "neighborhood-watch-out-cops-are-incorporating-private-cameras-their-real-time"
)


def test_pathways_document_claims_from_captured_bytes() -> None:
    report, _ = _run(
        "pathways_rtcc_federation",
        "pathways",
        [{"id": "eff-rtcc", "url": _EFF_RTCC_URL, "kind": "pathway_document"}],
        {
            _EFF_RTCC_URL: _resp(
                _EFF_RTCC_URL, _PW.joinpath("eff_rtcc_page.html").read_bytes(), "text/html"
            )
        },
    )
    claims = [r for r in report.claims if r.get("record_kind") == "claim"]
    assert claims
    # Genre is re-derived from the bytes, never trusted from the configured
    # kind: the page describes a vendor product (Fusus) so it classifies
    # vendor_disclosure — permitted: vendor_product claims only, NEVER a
    # deployment claim.
    assert all(c["document_genre"] == "vendor_disclosure" for c in claims)
    assert all(c["claim_type"] == "vendor_product" for c in claims)
    assert all(c["predicate_id"] == "technology" for c in claims)
    assert not any(c["claim_type"] == "deployment" for c in claims)
    tech_claim = next(c for c in claims if c["conformance_pathway"] == "rtcc_hub")
    assert tech_claim["raw_value"] == "real-time crime center"
    assert tech_claim["evidence"]["locator"]["kind"] == "byte_range"
    assert tech_claim["evidence"]["source_url"] == _EFF_RTCC_URL
    artifact = next(r for r in report.claims if r["record_kind"] == "evidence_artifact")
    assert artifact["document_genre"] == "vendor_disclosure"
    assert artifact["license_spdx"] == get("pathways_rtcc_federation").rights.spdx


def test_pathways_deployment_report_document_yields_deployment_claim() -> None:
    pdf = minimal_pdf(
        [
            [
                "CITY POLICE ANNUAL SURVEILLANCE REPORT",
                "This deployment report covers the gunshot detection system",
                "operated under ShotSpotter sensors currently operating citywide.",
            ]
        ]
    )
    report, _ = _run(
        "pathways_acoustic_drone_location",
        "pathways",
        [
            {
                "id": "doc",
                "url": "https://example.gov/annual-surveillance-report.pdf",
                "kind": "pathway_document",
            }
        ],
        {
            "https://example.gov/annual-surveillance-report.pdf": _resp(
                "https://example.gov/annual-surveillance-report.pdf", pdf, "application/pdf"
            )
        },
    )
    claims = [r for r in report.claims if r.get("record_kind") == "claim"]
    deployed = [c for c in claims if c["predicate_id"] == "deployed"]
    assert deployed and all(c["claim_type"] == "deployment" for c in deployed)
    assert all(c["document_genre"] == "deployment_report" for c in deployed)


def test_pathways_procurement_document_never_deploys() -> None:
    pdf = minimal_pdf(
        [
            [
                "PURCHASE ORDER 2026-114",
                "Line item: ShotSpotter sensor renewal, unit price $25000",
                "Vendor: SoundThinking. Total price $25000.",
            ]
        ]
    )
    report, _ = _run(
        "pathways_acoustic_drone_location",
        "pathways",
        [{"id": "doc", "url": "https://example.gov/po-2026-114.pdf", "kind": "pathway_document"}],
        {
            "https://example.gov/po-2026-114.pdf": _resp(
                "https://example.gov/po-2026-114.pdf", pdf, "application/pdf"
            )
        },
    )
    claims = [r for r in report.claims if r.get("record_kind") == "claim"]
    assert all(c["claim_type"] != "deployment" for c in claims)
    assert all(c["document_genre"] == "procurement_record" for c in claims)


# --- replay/shadow determinism over the new capture kinds ----------------------


def test_raa_index_replay_and_shadow_are_deterministic() -> None:
    from connectors.runner import RunMode, run_source

    fixture = _FRA / "raa_index.csv"
    shadow = run_source(
        "raa_prefectures",
        mode=RunMode.SHADOW,
        fixture=fixture,
        kind="resource_index",
        media_type="text/csv",
    )
    assert shadow.diff is not None and shadow.diff.changed_count == 0
    replay = run_source(
        "raa_prefectures",
        mode=RunMode.REPLAY,
        fixture=fixture,
        kind="resource_index",
        media_type="text/csv",
    )
    assert replay.replay_reproducible


def test_madada_feed_shadow_diff_zero() -> None:
    from connectors.runner import RunMode, run_source

    report = run_source(
        "madada",
        mode=RunMode.SHADOW,
        fixture=_FRA / "madada_feed.atom",
        kind="feed",
        media_type="application/atom+xml",
    )
    assert report.diff is not None and report.diff.changed_count == 0
    assert any(r.get("record_kind") == "claim" for r in report.claims)


def test_ccops_index_shadow_diff_zero() -> None:
    from connectors.runner import RunMode, run_source

    report = run_source(
        "ccops_nyc_post",
        mode=RunMode.SHADOW,
        fixture=_CCOPS / "post_act_index.html",
        kind="index_page",
        media_type="text/html",
    )
    assert report.diff is not None and report.diff.changed_count == 0


def test_pathways_document_shadow_diff_zero() -> None:
    from connectors.runner import RunMode, run_source

    report = run_source(
        "pathways_rtcc_federation",
        mode=RunMode.SHADOW,
        fixture=_PW / "eff_rtcc_page.html",
        kind="pathway_document",
        media_type="text/html",
    )
    assert report.diff is not None and report.diff.changed_count == 0
    assert any(r.get("record_kind") == "claim" for r in report.claims)


# --- DECP dataset-API indirection (P25.7) -------------------------------------
#
# The DECP consolidated files are data.gouv.fr *resources* whose static URLs
# carry a regeneration timestamp — the pinned URL 404s on republish. The seed
# target is the dataset-API document; the connector resolves the reviewed
# resource's CURRENT url from the captured index. A regenerated resource still
# resolves (new URL); a removed resource is a recorded disappearance, never a
# silent stale-URL fallback.


_DECP_API_URL = (
    "https://www.data.gouv.fr/api/1/datasets/"
    "donnees-essentielles-de-la-commande-publique-fichiers-consolides/"
)
_DECP_RESOURCE_URL = (
    "https://static.data.gouv.fr/resources/"
    "donnees-essentielles-de-la-commande-publique-fichiers-consolides/"
    "20260623-084347/decp-2024-01.json"
)
# A regenerated resource moves URL (new timestamp) — the indirection must follow.
_DECP_RESOURCE_URL_REGEN = (
    "https://static.data.gouv.fr/resources/"
    "donnees-essentielles-de-la-commande-publique-fichiers-consolides/"
    "20260701-120000/decp-2024-01.json"
)


def _decp_targets() -> list[dict[str, Any]]:
    return [
        {
            "id": "decp-dataset",
            "url": _DECP_API_URL,
            "kind": "dataset_index",
            "resource_title": "decp-2024-01.json",
            "resource_kind": "contract",
        }
    ]


def _decp_dataset_doc(*, resources: list[dict[str, Any]] | None = None) -> bytes:
    if resources is None:
        resources = [
            {
                "title": "decp.json",
                "url": "https://static.data.gouv.fr/resources/x/20260623-084347/decp.json",
                "id": "r0",
                "last_modified": "2026-06-23T08:43:47",
                "format": "json",
            },
            {
                "title": "decp-2024-01.json",
                "url": _DECP_RESOURCE_URL,
                "id": "r1",
                "last_modified": "2026-06-23T08:43:47",
                "format": "json",
            },
        ]
    return json.dumps(
        {
            "id": "5c94d620-11b4-4b1f-9c1d-decp",
            "title": "Données essentielles de la commande publique",
            "resources": resources,
        }
    ).encode("utf-8")


def _decp_responses(
    dataset: bytes, resource_url: str = _DECP_RESOURCE_URL
) -> dict[str, FetchResult]:
    marches = _FRA.joinpath("decp_marches.json").read_bytes()
    return {
        _DECP_API_URL: _resp(_DECP_API_URL, dataset, "application/json"),
        resource_url: _resp(resource_url, marches, "application/json"),
    }


def test_decp_dataset_api_resolves_the_current_resource_url() -> None:
    """The pinned static URL is no longer fetched: the dataset doc resolves it."""
    report, transport = _run(
        "decp_fr",
        "france_belgium_procurement",
        _decp_targets(),
        _decp_responses(_decp_dataset_doc()),
    )
    assert transport.request_log == [_DECP_API_URL, _DECP_RESOURCE_URL]
    contracts = [r for r in report.claims if r.get("record_kind") == "contract"]
    assert len(contracts) == 2  # the committed decp_marches fixture carries two
    index_rows = [
        r
        for r in report.claims
        if r.get("record_kind") == "quality_report" and r.get("capture_kind") == "dataset_index"
    ]
    assert len(index_rows) == 1
    assert index_rows[0]["resource_title"] == "decp-2024-01.json"
    assert index_rows[0]["resource_count"] == 2


def test_decp_regenerated_resource_resolves_to_the_new_url() -> None:
    """A republished resource moves URL; the run follows the index, not a pin."""
    report, transport = _run(
        "decp_fr",
        "france_belgium_procurement",
        _decp_targets(),
        _decp_responses(
            _decp_dataset_doc(
                resources=[
                    {
                        "title": "decp-2024-01.json",
                        "url": _DECP_RESOURCE_URL_REGEN,
                        "id": "r9",
                        "last_modified": "2026-07-01T12:00:00",
                        "format": "json",
                    }
                ]
            ),
            resource_url=_DECP_RESOURCE_URL_REGEN,
        ),
    )
    assert transport.request_log == [_DECP_API_URL, _DECP_RESOURCE_URL_REGEN]
    assert any(r.get("record_kind") == "contract" for r in report.claims)
    assert not report.disappearances


def test_decp_removed_resource_is_a_recorded_disappearance() -> None:
    """A resource absent from the dataset is a recorded link_rotted event."""
    report, transport = _run(
        "decp_fr",
        "france_belgium_procurement",
        _decp_targets(),
        _decp_responses(
            _decp_dataset_doc(
                resources=[
                    {
                        "title": "decp-2025-01.json",
                        "url": "https://static.data.gouv.fr/resources/x/t/decp-2025-01.json",
                        "id": "r2",
                        "format": "json",
                    }
                ]
            )
        ),
    )
    # The dataset index still fetched; NO static resource URL was ever hit.
    assert transport.request_log == [_DECP_API_URL]
    assert len(report.disappearances) == 1
    event = report.disappearances[0].event
    assert event.artifact_id == "decp-dataset:decp-2024-01.json"
    assert event.failing_status == "link_rotted"
    assert not [r for r in report.claims if r.get("record_kind") == "contract"]


def test_decp_ambiguous_resource_selector_fails_loud() -> None:
    """Two same-titled resources is drift — never a silent pick."""
    with pytest.raises(ContentDrift):
        _run(
            "decp_fr",
            "france_belgium_procurement",
            _decp_targets(),
            _decp_responses(
                _decp_dataset_doc(
                    resources=[
                        {"title": "decp-2024-01.json", "url": "https://static.data.gouv.fr/a"},
                        {"title": "decp-2024-01.json", "url": "https://static.data.gouv.fr/b"},
                    ]
                )
            ),
        )


@pytest.mark.parametrize(
    "bad_doc",
    [
        b"not json",
        json.dumps(["not", "an", "object"]).encode(),
        json.dumps({"id": "x", "resources": {"not": "a list"}}).encode(),
        json.dumps({"id": "x", "resources": [{"title": "decp-2024-01.json"}]}).encode(),
        json.dumps({"id": "x", "resources": [{"url": "https://x/y.json"}]}).encode(),
    ],
)
def test_decp_dataset_shape_drift_fails_closed(bad_doc: bytes) -> None:
    with pytest.raises(ContentDrift):
        _run(
            "decp_fr",
            "france_belgium_procurement",
            _decp_targets(),
            {_DECP_API_URL: _resp(_DECP_API_URL, bad_doc, "application/json")},
        )


def test_decp_dataset_selector_is_required_data() -> None:
    """A dataset_index target without resource_title is drift, not a guess."""
    targets = [{"id": "decp-dataset", "url": _DECP_API_URL, "kind": "dataset_index"}]
    with pytest.raises(ContentDrift):
        _run(
            "decp_fr",
            "france_belgium_procurement",
            targets,
            {_DECP_API_URL: _resp(_DECP_API_URL, _decp_dataset_doc(), "application/json")},
        )


def test_decp_live_target_is_the_dataset_api_document() -> None:
    """The configured live target is the allow-listed API doc + the selector."""
    from connectors.live_targets import live_targets

    targets = live_targets("decp_fr")
    assert len(targets) == 1
    target = targets[0]
    assert target["kind"] == "dataset_index"
    assert target["url"].startswith("https://www.data.gouv.fr/api/1/datasets/")
    assert target["resource_title"] == "decp-2024-01.json"
    # The timestamped static URL is gone from the configuration entirely.
    assert "static.data.gouv.fr" not in target["url"]


# --- P31.13 (BREADTH.2): Oakland / Cambridge / Somerville CCOPS filings --------

_OAK_INDEX_URL = (
    "https://www.oaklandca.gov/Government/Boards-Commissions/Privacy-Advisory-Commission"
)
_OAK_ORD_URL = (
    "https://www.oaklandca.gov/files/assets/city/v/1/boards-amp-commissions/"
    "documents/pac/omc-9.64-january-2021-005.pdf"
)
_OAK_ALPR19_URL = (
    "https://www.oaklandca.gov/files/assets/city/v/1/boards-amp-commissions/"
    "documents/pac/automated-license-plate-reader-annual-report-2019.pdf"
)
_OAK_ALPR20_URL = _OAK_ALPR19_URL.replace("-2019.pdf", "-2020.pdf")
_OAK_ALPR21_URL = _OAK_ALPR19_URL.replace("-2019.pdf", "-2021.pdf")
_OAK_SS20_URL = (
    "https://www.oaklandca.gov/files/assets/city/v/1/boards-amp-commissions/"
    "documents/pac/shotspotter-annual-report-2020.pdf"
)
_OAK_SS21_URL = _OAK_SS20_URL.replace("-2020.pdf", "-2021.pdf")
_OAK_MID20_URL = (
    "https://www.oaklandca.gov/files/assets/city/v/1/boards-amp-commissions/"
    "documents/pac/mobile-id-annual-report-2020.pdf"
)

# An Oakland §9.64 annual-report memorandum: the filing's own DATE: field label
# and the verbatim "Oakland Municipal Code (OMC) 9.64" legal-authority literal.
_OAK_MEMO = [
    "CITY OF OAKLAND",
    "MEMORANDUM",
    "TO: Honorable City Council",
    "FROM: Oakland Police Department",
    "DATE: March 22, 2022",
    "SUBJECT: Annual report on approved surveillance technology use",
    "Oakland Municipal Code (OMC) 9.64 requires this annual report",
    "under the Department's use policy.",
]
_OAK_ORD = [
    "SURVEILLANCE TECHNOLOGY ORDINANCE",
    "Oakland Municipal Code Chapter 9.64, adopted by the City Council",
    "as Ordinance 13489, regulates acquisition and use of surveillance",
    "technology by City departments.",
]


def _oak_responses(status: int = 200) -> dict[str, FetchResult]:
    index = _CCOPS.joinpath("oakland_pac_index.html").read_bytes()
    memo = minimal_pdf([_OAK_MEMO])
    responses = {
        _OAK_INDEX_URL: _resp(_OAK_INDEX_URL, index, "text/html"),
        _OAK_ORD_URL: _resp(
            _OAK_ORD_URL, minimal_pdf([_OAK_ORD]), "application/pdf", status=status
        ),
        _OAK_SS20_URL: _resp(_OAK_SS20_URL, memo, "application/pdf", status=status),
        _OAK_SS21_URL: _resp(_OAK_SS21_URL, memo, "application/pdf", status=status),
        _OAK_MID20_URL: _resp(_OAK_MID20_URL, memo, "application/pdf", status=status),
    }
    for url in (_OAK_ALPR19_URL, _OAK_ALPR20_URL, _OAK_ALPR21_URL):
        responses[url] = _resp(url, memo, "application/pdf", status=status)
    return responses


def test_oakland_index_discovers_bounded_filings_and_extracts_fields() -> None:
    report, transport = _run(
        "ccops_oakland",
        "government_mandated_disclosure",
        [
            {
                "id": "oak-index",
                "url": _OAK_INDEX_URL,
                "kind": "index_page",
                "max_documents": 5,
                "anchor_pattern": r"(?i)annual\s+report|surveillance\s+technology\s+ordinance",
            }
        ],
        _oak_responses(),
    )
    children = [u for u in transport.request_log if u != _OAK_INDEX_URL]
    # The reviewed anchor set, in the page's own document order, bounded at 5.
    assert children == [
        _OAK_ORD_URL,
        _OAK_ALPR19_URL,
        _OAK_ALPR20_URL,
        _OAK_ALPR21_URL,
        _OAK_SS20_URL,
    ]
    kinds = [r["record_kind"] for r in report.claims]
    assert "index_page" in kinds and "evidence_artifact" in kinds
    claims = [r for r in report.claims if r.get("record_kind") == "claim"]
    assert claims

    ss = [c for c in claims if "shotspotter-annual-report-2020" in str(c["evidence"]["source_url"])]
    assert ss, "no claims from the ShotSpotter filing"
    by_pred = {c["predicate_id"]: c for c in ss}
    assert by_pred["ordinance_citation"]["claim_type"] == "ordinance"
    assert (
        by_pred["ordinance_citation"]["value"]
        == "Oakland Municipal Code Chapter 9.64 (Surveillance Technology Ordinance)"
    )
    # The filing's own declared Date: field is the reporting period; the
    # technology name comes from the index link's anchor text verbatim.
    assert by_pred["technology"]["value"] == "Shotspotter"
    assert by_pred["technology"]["raw_value"] == "Shotspotter"
    assert by_pred["technology"]["reporting_period"] == "2022-03-22"
    assert "9.64" in by_pred["legal_authority"]["raw_value"]
    for claim in claims:
        if claim["claim_type"] == "ordinance":
            assert claim["agency"] == "Oakland City Council"
        else:
            assert claim["agency"] == "Oakland Police Department"
        assert claim["aggregate_level"] == "agency_technology_period"

    # Part VIII: the ALPR filings' technology literal contains a forbidden
    # token — suppressed at the claim surface, recorded on the artifact.
    assert not any(
        c["predicate_id"] == "technology" and "plate" in str(c.get("value", "")).lower()
        for c in claims
    )
    artifacts = [r for r in report.claims if r.get("record_kind") == "evidence_artifact"]
    assert any(a.get("part_viii_suppressions") for a in artifacts)


def test_oakland_ordinance_doc_carries_no_technology_and_no_field_claims() -> None:
    # The ordinance itself is a jurisdiction-scoped instrument document, not a
    # per-technology filing — no `technology`/field claims are fabricated.
    report, _ = _run(
        "ccops_oakland",
        "government_mandated_disclosure",
        [{"id": "ord", "url": _OAK_ORD_URL, "kind": "disclosure_document"}],
        {_OAK_ORD_URL: _resp(_OAK_ORD_URL, minimal_pdf([_OAK_ORD]), "application/pdf")},
    )
    claims = [r for r in report.claims if r.get("record_kind") == "claim"]
    assert {c["claim_type"] for c in claims} == {"ordinance"}
    assert not any(c["predicate_id"] == "technology" for c in claims)


_CAM_INDEX_URL = (
    "https://cambridgema.iqm2.com/Citizens/Detail_LegiFile.aspx"
    "?ID=18518&highlightTerms=surveillance"
)
_CAM_ASR_URL = "https://CambridgeMA.IQM2.com/Citizens/FileOpen.aspx?Type=4&ID=14080"

# The Chapter 2.128 mandated questionnaire — the eight questions the combined
# citywide filing repeats per department (verbatim from the live filing).
_CAM_QUESTIONS = [
    "1. What Surveillance Technologies has the department used in the last year?",
    "2. Has any Surveillance Technology data been shared with a third-party?",
    "3. What complaints (if any) has your department received about Surveillance Technology?",
    "4. Were any violations of the Surveillance Use Policy found in the last year?",
    "5. Has Surveillance Technology been effective in achieving its identified purpose?",
    "6. Did the department receive any public records requests concerning Surveillance Technology?",
    "7. What were the total annual costs of the Surveillance Technology?",
    "8. Are any communities disproportionately impacted by Surveillance Technology?",
]


def _cam_department_block(tech: str) -> list[str]:
    return [
        f"Surveillance Technology: {tech}",
        *(line for q in _CAM_QUESTIONS for line in (q, "No complaints or violations recorded.")),
    ]


_CAM_LINES = [
    "CITY OF CAMBRIDGE",
    "ANNUAL SURVEILLANCE REPORT",
    "Date: 02/27/2023",
    "Chapter 2.128 of the Cambridge Municipal Code requires this report.",
    "Department: Community Development Department",
    *_cam_department_block("- Media Monitoring - Meltwater"),
    "Department: Emergency Communications",
    *_cam_department_block("RapidSOS Emergency Data Integration System"),
]


def test_cambridge_legifile_attachment_resolves_and_extracts() -> None:
    report, transport = _run(
        "ccops_cambridge",
        "government_mandated_disclosure",
        [
            {
                "id": "cam-index",
                "url": _CAM_INDEX_URL,
                "kind": "index_page",
                "max_documents": 2,
                "anchor_pattern": r"(?i)annual\s+surveillance\s+report",
            }
        ],
        {
            _CAM_INDEX_URL: _resp(
                _CAM_INDEX_URL,
                _CCOPS.joinpath("cambridge_legifile_index.html").read_bytes(),
                "text/html",
            ),
            _CAM_ASR_URL: _resp(_CAM_ASR_URL, minimal_pdf([_CAM_LINES]), "application/pdf"),
        },
    )
    # Only the annual-report attachment resolves — the Type=30 "Printout"
    # sibling link fails the reviewed anchor pattern.
    children = [u for u in transport.request_log if u != _CAM_INDEX_URL]
    assert children == [_CAM_ASR_URL]
    claims = [r for r in report.claims if r.get("record_kind") == "claim"]
    assert claims
    doc_claims = [c for c in claims if "FileOpen" in str(c["evidence"]["source_url"])]
    assert doc_claims
    techs = [c for c in doc_claims if c["predicate_id"] == "technology"]
    # technology_field_multi: each department filing's own field literal lands —
    # one verbatim technology claim per occurrence, deterministic order.
    assert [t["value"] for t in techs] == [
        "Media Monitoring - Meltwater",
        "RapidSOS Emergency Data Integration System",
    ]
    assert techs[0]["raw_value"] == "Media Monitoring - Meltwater"
    # The filing's own Date: label is the reporting period.
    assert techs[0]["reporting_period"] == "2023-02-27"
    authority = next(c for c in doc_claims if c["predicate_id"] == "legal_authority")
    assert "2.128" in authority["raw_value"]
    # The combined filing's field-state claims ride the filing-level aggregate
    # technology marker, not any single listed system.
    states = {
        c["raw_value"]: c["value"]
        for c in doc_claims
        if c["predicate_id"] == "disclosure_field_state"
    }
    assert len(states) == 8
    assert all(v == "answered" for v in states.values())
    state_rows = [c for c in doc_claims if c["predicate_id"] == "disclosure_field_state"]
    assert all(r["technology"] == "(combined filing)" for r in state_rows)
    for c in doc_claims:
        if c["claim_type"] == "ordinance":
            assert c["agency"] == "Cambridge City Council"
        else:
            assert c["agency"] == "City of Cambridge"


_SOM_INDEX_URL = (
    "https://somervillema.legistar.com/LegislationDetail.aspx"
    "?GUID=11D1E64A-529B-4218-8F99-A3E07B0C1476&ID=7350978"
)
_SOM_DOC_URLS = {
    "combined": "https://somervillema.legistar.com/View.ashx?M=F&ID=14108438"
    "&GUID=0B37E474-C031-4DA6-BD5C-C84B22815A0F",
    "flir": "https://somervillema.legistar.com/View.ashx?M=F&ID=14108439"
    "&GUID=65B9E3A5-B6FC-42D0-9A4E-6548DCA63767",
    "thermal": "https://somervillema.legistar.com/View.ashx?M=F&ID=14108440"
    "&GUID=1BDBD43D-A25E-413F-828E-47C9E9406E58",
    "hs_cameras": "https://somervillema.legistar.com/View.ashx?M=F&ID=14108441"
    "&GUID=EAFCDC4A-2DB5-4B10-91D6-371CE0732080",
    "nextgen911": "https://somervillema.legistar.com/View.ashx?M=F&ID=14108442"
    "&GUID=6B59E8EF-417E-492A-B80D-C50A919172FE",
    "shotspotter": "https://somervillema.legistar.com/View.ashx?M=F&ID=14108443"
    "&GUID=3AAB9E28-40CC-4A86-A306-3F5E2285E2EE",
}

# The §10-66(b) mandated questionnaire — the nine questions verbatim (split only
# for line length; `_normalize_heading` folds whitespace, so a wrapped question
# still matches its mandated heading contiguously).
_SOM_QUESTIONS = [
    "1. A description of how surveillance technology has been used:",
    "2. Whether and how often data acquired through the use of the surveillance "
    "technology was shared:",
    "3. A summary of community complaints or concerns about the surveillance technology, if any:",
    "4. The results of any internal audits, any information about violations of "
    "the surveillance use policy,",
    "5. Whether the surveillance technology has been effective at achieving its "
    "identified purpose:",
    "6. The number of public records requests received by the city seeking "
    "documents concerning it:",
    "7. An estimate of the total annual costs for the surveillance technology, "
    "including personnel and other:",
    "8. Whether the civil rights and liberties of any communities or groups, "
    "including communities of color, are impacted:",
    "9. A disclosure of any new agreements made in the past 12 months with "
    "non-city entities that may acquire data:",
]


def _somerville_filing(tech: str) -> bytes:
    lines = [
        "APPENDIX B: CITY OF SOMERVILLE ANNUAL SURVEILLANCE REPORT",
        "Filed under Ordinance Chapter 10-66 (the surveillance technology ordinance).",
        "Department/Unit: Somerville Police Department",
        f"Surveillance Technology: {tech}",
        "Date: 2/19/25",
        *(
            line
            for q in _SOM_QUESTIONS
            for line in (q, "Answered in the affirmative per the filed report.")
        ),
    ]
    return minimal_pdf([lines])


def _som_responses(status: int = 200) -> dict[str, FetchResult]:
    index = _CCOPS.joinpath("somerville_legistar_index.html").read_bytes()
    tech_by_key = {
        "combined": "Citywide Camera Network",
        "flir": "FLIR Thermal Imaging Cameras",
        "thermal": "Thermal Imaging Cameras",
        "hs_cameras": "Homeland Security Cameras",
        "nextgen911": "Advanced Next Gen 911",
        "shotspotter": "ShotSpotter",
    }
    responses = {_SOM_INDEX_URL: _resp(_SOM_INDEX_URL, index, "text/html")}
    for key, url in _SOM_DOC_URLS.items():
        responses[url] = _resp(
            url, _somerville_filing(tech_by_key[key]), "application/pdf", status=status
        )
    return responses


def test_somerville_legistar_filings_fan_out_bounded_and_extract() -> None:
    report, transport = _run(
        "ccops_somerville",
        "government_mandated_disclosure",
        [
            {
                "id": "som-index",
                "url": _SOM_INDEX_URL,
                "kind": "index_page",
                "max_documents": 6,
                "anchor_pattern": r"(?i)surveillance\s+technology\s+annual\s+report",
            }
        ],
        _som_responses(),
    )
    children = [u for u in transport.request_log if u != _SOM_INDEX_URL]
    # The six §10-66(b) filings in document order; the calendar link is off-spec.
    assert children == list(_SOM_DOC_URLS.values())
    claims = [r for r in report.claims if r.get("record_kind") == "claim"]
    assert claims
    ss = [c for c in claims if _SOM_DOC_URLS["shotspotter"] == str(c["evidence"]["source_url"])]
    assert ss, "no claims from the ShotSpotter filing"
    by_pred = {c["predicate_id"]: c for c in ss}
    # The filing's own questionnaire field literal + two-digit-year Date label.
    assert by_pred["technology"]["value"] == "ShotSpotter"
    assert by_pred["technology"]["raw_value"] == "ShotSpotter"
    assert by_pred["technology"]["reporting_period"] == "2025-02-19"
    assert "10-66" in by_pred["legal_authority"]["raw_value"]
    # The nine §10-66(b) mandated questions: every one is an answered field
    # (mandated != populated is recorded, never fabricated).
    states = {
        c["raw_value"]: c["value"] for c in ss if c["predicate_id"] == "disclosure_field_state"
    }
    assert len(states) == 9
    assert all(v == "answered" for v in states.values())
    for c in ss:
        if c["claim_type"] == "ordinance":
            assert c["agency"] == "Somerville City Council"
        else:
            assert c["agency"] == "City of Somerville"
        assert c["aggregate_level"] == "agency_technology_period"
    # The combined "Annual Report 2024" filing's anchor yields a bare year —
    # dropped as a technology; its own field literal is what lands.
    combined_tech = [
        c
        for c in claims
        if c["predicate_id"] == "technology"
        and _SOM_DOC_URLS["combined"] == str(c["evidence"]["source_url"])
    ]
    assert [c["value"] for c in combined_tech] == ["Citywide Camera Network"]


def test_somerville_fan_out_is_bounded_when_over_cap() -> None:
    report, transport = _run(
        "ccops_somerville",
        "government_mandated_disclosure",
        [
            {
                "id": "som-index",
                "url": _SOM_INDEX_URL,
                "kind": "index_page",
                "max_documents": 2,
                "anchor_pattern": r"(?i)surveillance\s+technology\s+annual\s+report",
            }
        ],
        _som_responses(),
    )
    children = [u for u in transport.request_log if u != _SOM_INDEX_URL]
    assert children == [_SOM_DOC_URLS["combined"], _SOM_DOC_URLS["flir"]]


# --- P31.13: reporting-period + multi-technology extraction --------------------


def test_reporting_period_reads_the_new_date_and_year_forms() -> None:
    from connectors.government_mandated_disclosure import _reporting_period

    # The NYC UPDATED: revision literal (pre-existing behaviour).
    assert _reporting_period("UPDATED: FEBRUARY 4, 2026", "x.pdf") == "2026-02-04"
    # Cambridge's filing label: `Date: 02/27/2023` (numeric M/D/YYYY).
    assert _reporting_period("Date: 02/27/2023", "FileOpen.aspx") == "2023-02-27"
    # Somerville's two-digit year: `Date: 2/19/25`.
    assert _reporting_period("Date: 2/19/25", "View.ashx") == "2025-02-19"
    # Oakland's named-month memo date: `DATE: March 22, 2022`.
    assert _reporting_period("DATE: March 22, 2022", "x.pdf") == "2022-03-22"
    # An anchor-carried M-D-YYYY date when the document carries none.
    assert (
        _reporting_period("no date field", "x.pdf", "Annual Surveillance Report 02-27-2023")
        == "2023-02-27"
    )
    # The covered year in a filename slug / anchor title is the filing's own
    # year-granularity literal — recorded as-is.
    assert _reporting_period("no date field", "shotspotter-annual-report-2021.pdf") == "2021"
    assert _reporting_period("no date field", "x.pdf", "Annual Report (2019)") == "2019"
    # Nothing declared -> None: a claim with no period is not emitted.
    assert _reporting_period("no date field", "x.pdf") is None


def test_document_technologies_extracts_field_anchor_and_multi() -> None:
    from connectors.government_mandated_disclosure import (
        _document_technologies,
        source_adapter,
    )

    oak = source_adapter("ccops_oakland")
    cam = source_adapter("ccops_cambridge")
    som = source_adapter("ccops_somerville")

    # Anchor-derived (Oakland `<tech> Annual Report (YYYY)`).
    assert _document_technologies(
        "x.pdf", ("plain memo text",), oak, "Shotspotter Annual Report (2020)(PDF, 9MB)"
    ) == [("Shotspotter", "Shotspotter")]
    # A bare year in the anchor is the covered year, not a technology.
    assert (
        _document_technologies("x.pdf", ("plain memo text",), oak, "Surveillance Report 2024") == []
    )
    # Field-literal with multi: the combined Cambridge filing names each
    # department's technology once per occurrence.
    cam_page = (
        "Surveillance Technology: • Media Monitoring - Meltwater\n"
        "Surveillance Technology: RapidSOS Emergency Data Integration System\n"
        "Surveillance Technology: Media Monitoring - Meltwater"
    )
    assert _document_technologies("x.pdf", (cam_page,), cam) == [
        ("Media Monitoring - Meltwater", "Media Monitoring - Meltwater"),
        (
            "RapidSOS Emergency Data Integration System",
            "RapidSOS Emergency Data Integration System",
        ),
    ]
    # Somerville single-tech field literal (multi unset -> first only).
    som_page = "Surveillance Technology: ShotSpotter\nSurveillance Technology: FLIR\n"
    assert _document_technologies("x.pdf", (som_page,), som) == [("ShotSpotter", "ShotSpotter")]
    # Anchor fallback when the document has no field literal: the Somerville
    # `... Annual Report <tech>` attachments name the filing verbatim.
    assert _document_technologies(
        "View.ashx",
        ("no field literal on this page",),
        som,
        "Revised 2024 Surveillance Technology Annual Report ShotSpotter",
    ) == [("ShotSpotter", "ShotSpotter")]
    # A bare-year anchor residue is dropped (the combined city filing).
    assert (
        _document_technologies(
            "View.ashx",
            ("no field literal on this page",),
            som,
            "Revised Surveillance Technology Annual Report 2024",
        )
        == []
    )


def test_new_ccops_sources_are_registered_routed_and_gated() -> None:
    # The three P31.13 sources are registry rows of the mandated-disclosure
    # class, routed to this connector, and carry reviewed index_page targets.
    # Their ingestion_permitted flips are the P29.3 GL-GATE-07 rights packets
    # (operator decisions — never a code change).
    from connectors.live_targets import live_targets
    from connectors.runner import CONNECTOR_FOR_SOURCE

    for source_id in ("ccops_oakland", "ccops_cambridge", "ccops_somerville"):
        assert CONNECTOR_FOR_SOURCE[source_id] == "government_mandated_disclosure"
        rec = get(source_id)
        assert rec.ingestion_permitted is True
        targets = live_targets(source_id)
        assert targets and all(t["kind"] == "index_page" for t in targets)
        assert all(t.get("max_documents", 8) <= 8 for t in targets)
