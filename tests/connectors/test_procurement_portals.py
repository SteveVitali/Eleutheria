# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for the procurement-portal tenant expansion (P26.10 / SOURCES.9).

Cover the P26.10 contract: a published multi-tenant registry of public
procurement surfaces (BidNet storefronts, Socrata contract datasets, gated
Bonfire/OpenGov portals); target expansion bounded by reviewed per-tenant and
per-run windows; BidNet storefront index → item detail continuation where the
detail URL is ALWAYS the item's own link, never constructed; Socrata
``/resource/*.json`` rows where the record IS the document; ``procurement_notice``
+ verbatim ``content_term`` claims with byte-range/row locators; honest
empty/no-match outcomes; fail-closed drift on markup change or API envelopes;
and gated surfaces that never fabricate a parse (§3.1, SIG-INGEST-002/014).
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from connectors.net import PoliteFetcher, RateLimiter, RobotsResult
from connectors.procurement import (
    ContentDrift,
    ProcurementConnector,
    content_vocab_version,
    platform_endpoints,
    portal_targets,
    portal_tenants,
    procurement_portal_sources,
    source_ids,
    vocab_version,
)
from connectors.registry import CompactStatus, CustodyPosture, get
from connectors.stages import (
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun

FIXTURES = Path(__file__).parent / "fixtures" / "procportal"

_BIDNET_INDEX_URL = (
    "https://www.bidnetdirect.com/maryland/montgomerycounty/"
    "solicitations/closed-bids?keywords=surveillance"
)
_BIDNET_DETAIL_URL = (
    "https://www.bidnetdirect.com/maryland/montgomerycounty/solicitations/"
    "Security-Camera-System/0000354724?purchasingGroupId=182876351&origin=2"
)


def _ingest_run() -> IngestRun:
    return IngestRun(
        connector_name="procurement",
        connector_version="1.0.0",
        code_commit="deadbeef",
        ruleset_version="r1",
        vocab_version="v1",
        input_digests=(),
    )


class _SequenceTransport:
    """Queued per-URL responses; unmapped URLs answer 404 (recorded disappearance)."""

    def __init__(self, responses: dict[str, list[tuple[int, bytes, str]]]) -> None:
        self._responses = {k: list(v) for k, v in responses.items()}
        self.request_log: list[str] = []

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text="User-agent: *\nAllow: /\n")

    def request(
        self,
        url: str,
        *,
        user_agent: str,
        headers: Mapping[str, str] | None = None,
        body: bytes | None = None,
    ) -> FetchResult:
        self.request_log.append(url)
        if url in self._responses and self._responses[url]:
            status, body_, media = self._responses[url].pop(0)
            return FetchResult(url=url, status=status, body=body_, media_type=media)
        return FetchResult(url=url, status=404, body=b"not found", media_type="text/plain")


def _fetcher(transport: _SequenceTransport) -> PoliteFetcher:
    return PoliteFetcher(
        connector_name="procurement",
        connector_version="1.0.0",
        transport=transport,
        rate_limiter=RateLimiter(sleep=lambda _s: None),
    )


def _ctx(
    source_key: str,
    *,
    transport: _SequenceTransport | None = None,
    targets: list[Mapping[str, Any]] | None = None,
    permitted: bool = True,
) -> RunContext:
    source = get(source_ids()[source_key])
    if permitted:
        # The fixture pipeline opens the loader gate on the source record the
        # way a reviewer flip would — never by bypassing the gate.
        source = dataclasses.replace(
            source,
            ingestion_permitted=True,
            compact_status=CompactStatus.PUBLIC_TERMS_ONLY,
            custody_posture=CustodyPosture.MIRROR,
        )
    return RunContext(
        source=source,
        run=_ingest_run(),
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        fetcher=_fetcher(transport) if transport is not None else None,
        parameters={"targets": list(targets or [])},
    )


def _capture(ctx: RunContext, uri: str, data: bytes, media: str) -> Any:
    return ctx.captures.put(data, media_type=media, source_uri=uri)


def _bidnet_index_target(**over: Any) -> dict[str, Any]:
    target = {
        "id": "maryland_montgomerycounty:closed:kw:surveillance",
        "url": _BIDNET_INDEX_URL,
        "kind": "portal_index",
        "platform": "bidnet",
        "tenant_id": "maryland_montgomerycounty",
        "tenant": "montgomerycounty",
        "jurisdiction": "Montgomery County, Maryland",
        "index_kind": "closed",
        "index_keyword": "surveillance",
        "doc_per_tenant": 5,
        "doc_run_cap": 25,
    }
    target.update(over)
    return target


# --- the tenant registry ------------------------------------------------------


def test_portal_tenant_registry_is_published_and_seeded() -> None:
    """P26.10 AC: ≥10 procurement tenants enumerated with provenance."""
    tenants = portal_tenants()
    assert len(tenants) >= 10
    # Every tenant carries the provenance the claims stamp back: platform,
    # source, jurisdiction, and the reviewed bounds.
    for tenant_id, row in tenants.items():
        assert row.get("platform"), tenant_id
        assert row.get("source_id"), tenant_id
        assert row.get("jurisdiction"), tenant_id


def test_portal_registry_covers_the_reviewed_platforms() -> None:
    platforms = {str(t.get("platform")) for t in portal_tenants().values()}
    assert {"bidnet", "socrata", "bonfire", "opengov"} <= platforms


def test_all_portal_sources_are_registered_registry_rows() -> None:
    for source_id in procurement_portal_sources():
        record = get(source_id)  # raises KeyError on an unregistered row
        assert record.id == source_id


# --- target expansion ----------------------------------------------------------


def test_portal_targets_expand_per_source() -> None:
    for source_id in procurement_portal_sources():
        targets = portal_targets(source_id=source_id)
        assert targets, source_id
        for target in targets:
            assert target["url"].startswith("https://")
            assert target.get("kind") == "portal_index"
            assert target.get("platform")


def test_portal_target_urls_are_unique() -> None:
    urls = [t["url"] for t in portal_targets()]
    assert len(urls) == len(set(urls))


def test_bidnet_targets_ride_the_reviewed_windows() -> None:
    targets = portal_targets(source_id="bidnet_direct")
    kinds = {t.get("index_kind") for t in targets}
    assert {"open", "closed", "awarded"} <= kinds
    # Keyword-window targets carry the reviewed keyword; unfiltered carry none.
    kw = [t for t in targets if t.get("index_keyword")]
    assert kw and all(t["index_kind"] for t in kw)
    # Reviewed bounds ride every target row as data.
    assert all(t.get("doc_per_tenant") for t in targets)
    assert all(t.get("doc_run_cap") for t in targets)


def test_socrata_targets_are_bounded_soql_slices() -> None:
    targets = portal_targets(source_id="procportal_nyc_ny")
    rows = [t for t in targets if t["index_kind"] == "rows"]
    assert len(rows) == 1
    url = rows[0]["url"]
    assert url.startswith("https://data.cityofnewyork.us/resource/dg92-zbpx.json")
    assert "%24limit=500" in url or "$limit=500" in url
    assert "%24order=" in url or "$order=" in url
    # Field aliases ride the target (the reviewed dataset column names).
    assert "request_id" in rows[0]["id_fields"]
    assert "short_title" in rows[0]["title_fields"]
    # P35.9 (ACQ-05): the reviewed `crol` portal_where definition adds the
    # bounded where slices BESIDE the rows window — one target per reviewed
    # term OR-group, each carrying the B00329-shaped `upper(f) like '%T%'`
    # clause, its term group, and the reviewed term-set provenance.
    where = [t for t in targets if t["index_kind"] == "where"]
    assert where
    for t in where:
        assert "%24where=" in t["url"] or "$where=" in t["url"]
        assert "upper%28vendor_name%29" in t["url"] or "upper(vendor_name)" in t["url"]
        assert t["portal_where"] == "crol"
        assert t["acq_keyword_terms"] == "crol"
        assert t["where_terms"]
        assert t["where_fields"]


def test_gated_portals_expand_to_their_portal_surface_only() -> None:
    # Bonfire/OpenGov are gated: their targets are the portal surface whose
    # refusal/challenge is the recorded outcome — never a fabricated parse.
    bonfire = portal_targets(source_id="bonfire")
    assert {t["platform"] for t in bonfire} == {"bonfire"}
    assert all(t["url"].endswith("/portal") for t in bonfire)
    opengov = portal_targets(source_id="opengov_procurement")
    assert {t["platform"] for t in opengov} == {"opengov"}


def test_census_rows_emit_no_targets() -> None:
    # The platform_census rows record coverage, not fetch surfaces.
    urls = [t["url"] for t in portal_targets()]
    assert not any("census" in u for u in urls)


# --- BidNet pipeline: index → notice → detail continuation ----------------------


def test_bidnet_index_pipeline_emits_notices_and_detail_document() -> None:
    """A captured storefront index yields item notices AND resolves detail pages.

    The detail URL is the item's own ``solicitation-link`` href — the
    connector never constructs one. The captured detail page scans against the
    reviewed vocabulary and emits verbatim ``content_term`` claims with
    byte-range locators.
    """
    from connectors import pipeline

    index_html = (FIXTURES / "bidnet_index_closed_surv.html").read_bytes()
    detail_html = (FIXTURES / "bidnet_detail_security_camera.html").read_bytes()
    transport = _SequenceTransport(
        {
            _BIDNET_INDEX_URL: [(200, index_html, "text/html")],
            _BIDNET_DETAIL_URL: [(200, detail_html, "text/html")],
        }
    )
    ctx = _ctx(
        "bidnet_direct",
        transport=transport,
        targets=[_bidnet_index_target()],
    )
    report = pipeline.run(ProcurementConnector(), ctx)
    assert report.asserted
    kinds = {c.get("record_kind") for c in report.claims}
    assert {"portal_index", "procurement_notice", "portal_document", "claim"} <= kinds

    index_row = next(c for c in report.claims if c.get("record_kind") == "portal_index")
    assert index_row["outcome"] == "items"
    assert index_row["items_count"] == 2
    assert index_row["index_kind"] == "closed"
    assert index_row["index_keyword"] == "surveillance"

    notices = [c for c in report.claims if c.get("record_kind") == "procurement_notice"]
    assert len(notices) == 2
    titles = {n.get("title") for n in notices}
    assert "Security Camera System" in titles
    for notice in notices:
        surface = notice["predicate_surface"]
        # The document surface is the item's OWN detail link.
        assert surface["document"].startswith(
            "https://www.bidnetdirect.com/maryland/montgomerycounty/solicitations/"
        )
        assert notice["raw"]  # the verbatim item row is preserved

    doc = next(c for c in report.claims if c.get("record_kind") == "portal_document")
    assert doc["outcome"] == "matched"

    terms = [
        c
        for c in report.claims
        if c.get("record_kind") == "claim" and c.get("predicate_id") == "content_term"
    ]
    assert terms
    term_ids = {t["value"] for t in terms}
    assert "alpr" in term_ids
    for term in terms:
        # raw_value is the VERBATIM literal slice of the captured text —
        # "License Plate Recognition" is the reviewed alpr term's literal.
        assert term["raw_value"]
        locator = term["evidence"]["locator"]
        assert locator["kind"] == "byte_range"
        # The literal is a slice of the captured document text — verify by
        # construction against the document row's scanned text is impossible
        # here, so assert the locator is internally consistent.
        assert locator["end"] > locator["start"]
        assert term["evidence"]["source_url"] == _BIDNET_DETAIL_URL
        assert term["document_subject"].startswith("portal_document:bidnet_direct:")


def test_bidnet_detail_url_is_the_items_own_link() -> None:
    """The continuation fetches the href the page carried — never a built URL."""
    from connectors import pipeline

    index_html = (FIXTURES / "bidnet_index_closed_surv.html").read_bytes()
    detail_html = (FIXTURES / "bidnet_detail_security_camera.html").read_bytes()
    transport = _SequenceTransport(
        {
            _BIDNET_INDEX_URL: [(200, index_html, "text/html")],
            _BIDNET_DETAIL_URL: [(200, detail_html, "text/html")],
        }
    )
    ctx = _ctx(
        "bidnet_direct",
        transport=transport,
        targets=[_bidnet_index_target()],
    )
    pipeline.run(ProcurementConnector(), ctx)
    # The resolved detail targets were fetched at the item's own hrefs.
    detail_fetches = [
        u for u in transport.request_log if "/solicitations/" in u and "keywords=" not in u
    ]
    assert _BIDNET_DETAIL_URL in detail_fetches


def test_bidnet_empty_window_is_an_honest_empty_outcome() -> None:
    """A zero-result keyword window is ``empty``, never drift, never a claim."""
    from connectors import pipeline

    empty_html = (FIXTURES / "bidnet_index_empty_surv.html").read_bytes()
    url = (
        "https://www.bidnetdirect.com/maryland/montgomerycounty/"
        "solicitations/open-bids?keywords=surveillance"
    )
    transport = _SequenceTransport({url: [(200, empty_html, "text/html")]})
    ctx = _ctx(
        "bidnet_direct",
        transport=transport,
        targets=[_bidnet_index_target(url=url, index_kind="open")],
    )
    report = pipeline.run(ProcurementConnector(), ctx)
    index_row = next(c for c in report.claims if c.get("record_kind") == "portal_index")
    assert index_row["outcome"] == "empty"
    assert index_row["items_count"] == 0
    # No notice, no document, no content_term — nothing fabricated (§3.1).
    assert not any(c.get("record_kind") == "procurement_notice" for c in report.claims)
    assert not any(
        c.get("predicate_id") == "content_term" and c.get("record_kind") == "claim"
        for c in report.claims
    )


def test_bidnet_markup_drift_fails_closed() -> None:
    """A page carrying neither item markup nor the list container is ContentDrift."""
    conn = ProcurementConnector()
    target = _bidnet_index_target()
    ctx = _ctx("bidnet_direct", targets=[target])
    cap = _capture(
        ctx, target["url"], (FIXTURES / "bidnet_index_drift.html").read_bytes(), "text/html"
    )
    with pytest.raises(ContentDrift):
        conn.parse(ctx, cap)


def test_bidnet_detail_page_without_field_markup_fails_closed() -> None:
    """A detail page missing mets-field/descriptionText markup is drift, not empty."""
    conn = ProcurementConnector()
    ctx = _ctx("bidnet_direct", targets=[_bidnet_index_target()])
    doc_target = {
        "id": "maryland_montgomerycounty:doc:1",
        "url": _BIDNET_DETAIL_URL,
        "kind": "portal_document",
        "platform": "bidnet",
        "tenant_id": "maryland_montgomerycounty",
        "jurisdiction": "Montgomery County, Maryland",
        "item": {"sol_num": "1"},
        "item_id": "1",
        "index_url": _BIDNET_INDEX_URL,
    }
    ctx.resolved_targets[_BIDNET_DETAIL_URL] = doc_target
    cap = _capture(ctx, _BIDNET_DETAIL_URL, b"<html><body>gone</body></html>", "text/html")
    with pytest.raises(ContentDrift):
        conn.parse(ctx, cap)


def test_bidnet_discovery_is_bounded_per_tenant_and_per_run() -> None:
    """``doc_per_tenant``/``doc_run_cap`` bound the detail continuation."""
    conn = ProcurementConnector()
    target = _bidnet_index_target(doc_per_tenant=1, doc_run_cap=1)
    ctx = _ctx("bidnet_direct", targets=[target])
    index_html = (FIXTURES / "bidnet_index_closed_surv.html").read_bytes()
    cap = _capture(ctx, target["url"], index_html, "text/html")
    resolved = conn.discover_more(ctx, [cap])
    # Two items on the page, but the reviewed cap binds: exactly one resolves.
    assert len(resolved) == 1
    assert resolved[0]["kind"] == "portal_document"
    assert resolved[0]["url"].startswith("https://www.bidnetdirect.com/")


def test_bidnet_index_items_preserve_verbatim_fields() -> None:
    conn = ProcurementConnector()
    ctx = _ctx("bidnet_direct", targets=[_bidnet_index_target()])
    index_html = (FIXTURES / "bidnet_index_closed_surv.html").read_bytes()
    cap = _capture(ctx, _BIDNET_INDEX_URL, index_html, "text/html")
    rows = conn.normalize(ctx, conn.extract(ctx, conn.parse(ctx, cap)))
    notices = [r for r in rows if r.get("record_kind") == "procurement_notice"]
    sec = next(n for n in notices if n.get("title") == "Security Camera System")
    assert sec["raw"]["sol_num"] == "1167294"
    assert sec["raw"]["published"] == "06/06/2024"  # verbatim, never re-parsed
    assert sec["jurisdiction"] == "Montgomery County, Maryland"


# --- Socrata pipeline: the row IS the document ----------------------------------


def _nyc_target() -> Mapping[str, Any]:
    return portal_targets(source_id="procportal_nyc_ny")[0]


def _nyc_surveillance_where_target() -> Mapping[str, Any]:
    """The where slice owning every fixture row ('surveillance' ⇒ g5)."""
    return next(
        t
        for t in portal_targets(source_id="procportal_nyc_ny")
        if t.get("index_kind") == "where" and "surveillance" in t["where_terms"]
    )


def test_socrata_rows_emit_notices_documents_and_verbatim_terms() -> None:
    """Each SoQL row is its own document: notice + doc outcome + row locators.

    P35.9: every fixture row LIKE-matches the 'surveillance' term, so the g5
    where slice owns their claim sets; the generic rows window records them
    pruned and emits none.
    """
    from connectors import pipeline

    rows_json = (FIXTURES / "socrata_nyc_crol.json").read_bytes()
    target = _nyc_target()
    where_target = _nyc_surveillance_where_target()
    transport = _SequenceTransport(
        {
            str(target["url"]): [(200, rows_json, "application/json")],
            str(where_target["url"]): [(200, rows_json, "application/json")],
        }
    )
    ctx = _ctx("procportal_nyc_ny", transport=transport, targets=[target, where_target])
    report = pipeline.run(ProcurementConnector(), ctx)
    assert report.asserted

    notices = [c for c in report.claims if c.get("record_kind") == "procurement_notice"]
    assert len(notices) == 5
    assert {n["index_kind"] for n in notices} == {"where"}
    docs = [c for c in report.claims if c.get("record_kind") == "portal_document"]
    assert len(docs) == 5
    # Every row carries a row_index locator into the captured array.
    assert sorted(d["row_index"] for d in docs) == [0, 1, 2, 3, 4]

    terms = [
        c
        for c in report.claims
        if c.get("record_kind") == "claim" and c.get("predicate_id") == "content_term"
    ]
    assert terms
    for term in terms:
        ev = term["evidence"]
        assert ev["locator"]["kind"] == "byte_range"
        assert ev["field"] in (
            "short_title",
            "additional_description_1",
            "additional_description_2",
            "additional_description_3",
        )
        assert "record_row" in ev
        # The literal is verbatim: locate it in the named field of the named row.
        row = json.loads(rows_json)[ev["record_row"]]
        field_text = row[ev["field"]]
        assert field_text[ev["locator"]["start"] : ev["locator"]["end"]] == term["raw_value"]


def test_socrata_notice_type_maps_only_reviewed_transitions() -> None:
    """Award→awarded, Solicitation→rfp_issued; unlisted types assert nothing.

    P35.9: the fixture rows are owned by the 'surveillance' where slice —
    serve the same register rows there so their claims emit under the
    tighter tier (the rows fallback prunes them).
    """
    from connectors import pipeline

    rows_json = (FIXTURES / "socrata_nyc_crol.json").read_bytes()
    target = _nyc_target()
    where_target = _nyc_surveillance_where_target()
    transport = _SequenceTransport(
        {
            str(target["url"]): [(200, rows_json, "application/json")],
            str(where_target["url"]): [(200, rows_json, "application/json")],
        }
    )
    ctx = _ctx("procportal_nyc_ny", transport=transport, targets=[target, where_target])
    report = pipeline.run(ProcurementConnector(), ctx)

    lifecycles = {
        c["subject_id"]: c["value"]["state"]
        for c in report.claims
        if c.get("predicate_id") == "lifecycle_transition"
    }
    assert lifecycles["procurement_notice:procportal_nyc_ny:new_york_ny:20260708012"] == "awarded"
    assert (
        lifecycles["procurement_notice:procportal_nyc_ny:new_york_ny:20251028033"] == "rfp_issued"
    )
    # "Notice", "Public Comment", "Intent to Award" — no guessed transition (§3.1).
    assert len(lifecycles) == 2


def test_socrata_error_envelope_fails_closed() -> None:
    """A JSON object (the SoQL error envelope) is drift, not an index."""
    conn = ProcurementConnector()
    target = _nyc_target()
    ctx = _ctx("procportal_nyc_ny", targets=[target])
    cap = _capture(
        ctx,
        str(target["url"]),
        json.dumps({"error": True, "message": "permission denied"}).encode(),
        "application/json",
    )
    with pytest.raises(ContentDrift):
        conn.parse(ctx, cap)


def test_socrata_undecodable_body_fails_closed() -> None:
    conn = ProcurementConnector()
    target = _nyc_target()
    ctx = _ctx("procportal_nyc_ny", targets=[target])
    cap = _capture(ctx, str(target["url"]), b"<html>challenged</html>", "application/json")
    with pytest.raises(ContentDrift):
        conn.parse(ctx, cap)


def test_socrata_empty_array_is_an_honest_empty_window() -> None:
    conn = ProcurementConnector()
    target = _nyc_target()
    ctx = _ctx("procportal_nyc_ny", targets=[target])
    cap = _capture(ctx, str(target["url"]), b"[]", "application/json")
    rows = conn.normalize(ctx, conn.extract(ctx, conn.parse(ctx, cap)))
    index_row = next(r for r in rows if r.get("record_kind") == "portal_index")
    assert index_row["outcome"] == "empty"
    assert index_row["items_count"] == 0


# --- gated surfaces never fabricate a parse -------------------------------------


def test_bonfire_capture_is_drift_by_construction() -> None:
    """Bonfire has no reviewed markup contract — its captured body is ContentDrift."""
    conn = ProcurementConnector()
    target = portal_targets(source_id="bonfire")[0]
    ctx = _ctx("bonfire", targets=[target])
    cap = _capture(
        ctx, str(target["url"]), (FIXTURES / "bonfire_portal_shell.html").read_bytes(), "text/html"
    )
    with pytest.raises(ContentDrift):
        conn.parse(ctx, cap)


def test_opengov_capture_is_drift_by_construction() -> None:
    """OpenGov's challenged portal carries no reviewed contract — ContentDrift."""
    conn = ProcurementConnector()
    target = portal_targets(source_id="opengov_procurement")[0]
    ctx = _ctx("opengov_procurement", targets=[target])
    cap = _capture(
        ctx, str(target["url"]), (FIXTURES / "opengov_portal_home.html").read_bytes(), "text/html"
    )
    with pytest.raises(ContentDrift):
        conn.parse(ctx, cap)


def test_loader_gate_refuses_gated_portal_sources() -> None:
    """The registry rows are gated; the loader refuses them before any fetch."""
    from connectors.loader import IngestionNotPermitted, assert_loadable

    # BidNet (not_contacted), Bonfire (robots Disallow:/), OpenGov (challenged)
    # and Chicago Socrata (no licence metadata) stay gated.
    for source_key in ("bidnet_direct", "bonfire", "opengov_procurement", "procportal_chicago_il"):
        with pytest.raises(IngestionNotPermitted):
            assert_loadable(get(source_ids()[source_key]))


def test_flipped_socrata_sources_pass_the_loader_gate() -> None:
    """The four licence-reviewed city datasets cleared GL-GATE-06 (verbatim basis
    in their rights packets) — the gate opens on the registry row alone."""
    from connectors.loader import assert_loadable

    for source_key in (
        "procportal_austin_tx",
        "procportal_sf_ca",
        "procportal_kcmo_mo",
        "procportal_nyc_ny",
    ):
        record = assert_loadable(get(source_ids()[source_key]))
        assert record.ingestion_permitted


# --- vocabulary / provenance stamps ----------------------------------------------


def test_portal_index_predicate_is_allowlisted() -> None:
    from connectors.procurement import assert_predicate_allowed

    assert assert_predicate_allowed("portal_index") == "portal_index"


def test_portal_rows_stamp_vocab_versions() -> None:
    conn = ProcurementConnector()
    where_target = _nyc_surveillance_where_target()
    ctx = _ctx("procportal_nyc_ny", targets=[_nyc_target(), where_target])
    rows_json = (FIXTURES / "socrata_nyc_crol.json").read_bytes()
    caps = [
        _capture(ctx, str(t["url"]), rows_json, "application/json")
        for t in (_nyc_target(), where_target)
    ]
    rows = [r for cap in caps for r in conn.normalize(ctx, conn.extract(ctx, conn.parse(ctx, cap)))]
    for index_row in (r for r in rows if r.get("record_kind") == "portal_index"):
        assert index_row["content_vocab_version"] == content_vocab_version()
    doc_row = next(r for r in rows if r.get("record_kind") == "portal_document")
    assert doc_row["content_vocab_version"] == content_vocab_version()
    assert vocab_version()


def test_platform_endpoints_carry_the_reviewed_portal_facts() -> None:
    cfg = platform_endpoints()
    assert "bidnet" in cfg
    assert "socrata" in cfg
    assert cfg["bidnet"].get("doc_per_tenant") or cfg["bidnet"].get("doc_run_cap")


# --- live-target plumbing ---------------------------------------------------------


def test_live_targets_expand_the_portal_registry() -> None:
    from connectors.live_targets import live_targets

    targets = live_targets("bidnet_direct")
    assert len(targets) > 10
    assert all(t.get("kind") == "portal_index" for t in targets)
    nyc = live_targets("procportal_nyc_ny")
    # P35.9: the rows window plus the reviewed where-slice term groups.
    assert len(nyc) == 1 + len(
        [t for t in portal_targets(source_id="procportal_nyc_ny") if t["index_kind"] == "where"]
    )
    assert "resource/dg92-zbpx.json" in nyc[0]["url"]
    assert all(t.get("kind") == "portal_index" for t in nyc)


def test_api_allowlist_covers_the_socrata_hosts() -> None:
    from connectors.registry import load_table

    allowlist = load_table("api_allowlist")
    hosts = {(row["host"], row["endpoint_prefix"]) for row in allowlist.get("api_host", [])}
    for host in (
        "data.austintexas.gov",
        "data.sf.gov",
        "data.kcmo.org",
        "data.cityofnewyork.us",
    ):
        assert (host, "/resource/") in hosts


# --- P35.9 (ACQ-05, I8 §4.2): portal_where, CROL post-filter, pruned fallback --
# KP-* rows keep; FP-* rows are the I9b-Q008 false-positive classes (%BRINC%
# recall — 'Parsons Brinckerhoff' never matches \bbrinc\b; %CLEARVIEW% —
# 'Clearview Data Systems' is not the disambiguated Clearview AI literal).
_CROL_WHERE_ROWS = [
    {  # kept — the reviewed vendor literal matches verbatim (\bflock group\b)
        "request_id": "KP-FLOCK",
        "vendor_name": "FLOCK GROUP, INC.",
        "short_title": "Maintenance for the license plate reader network",
        "type_of_notice_description": "Award",
        "agency_name": "New York City Police Department",
        "start_date": "2026-01-05T00:00:00.000",
    },
    {  # kept — the reviewed literal lives in the description fan-out field
        "request_id": "KP-DESC",
        "vendor_name": "ACME CONSULTING LLC",
        "short_title": "Consulting services",
        "additional_description_1": "O&M of the city's gunshot detection network.",
        "start_date": "2026-01-06T00:00:00.000",
    },
    {
        "request_id": "FP-BRINC",
        "vendor_name": "PARSONS BRINCKERHOFF INC",
        "short_title": "Structural engineering services",
        "start_date": "2026-01-07T00:00:00.000",
    },
    {
        "request_id": "FP-CLEARVIEW",
        "vendor_name": "CLEARVIEW DATA SYSTEMS",
        "short_title": "Records management services",
        "start_date": "2026-01-08T00:00:00.000",
    },
]


def _where_targets() -> list[Mapping[str, Any]]:
    return [
        t for t in portal_targets(source_id="procportal_nyc_ny") if t.get("index_kind") == "where"
    ]


def test_socrata_where_targets_compose_soql_or_groups() -> None:
    """`crol` composes bounded B00329-shaped slices: one target per reviewed
    term group, `upper(<field>) like '%<TERM>%'` OR'ed across the fields."""
    from urllib.parse import parse_qs, urlparse

    from connectors.procurement import acq_keyword_term_set

    where = _where_targets()
    terms = acq_keyword_term_set("crol")
    group_size = 6  # the reviewed [portal_where.crol] bound
    assert len(where) == (len(terms) + group_size - 1) // group_size
    # The groups partition the reviewed set — full coverage, in order, no dupes.
    assert [t for w in where for t in w["where_terms"]] == terms
    for w in where:
        assert w["portal_where"] == "crol"
        assert w["acq_keyword_terms"] == "crol"
        assert w["where_fields"] == [
            "vendor_name",
            "short_title",
            "additional_description_1",
            "additional_description_2",
            "additional_description_3",
        ]
        q = parse_qs(urlparse(str(w["url"])).query)
        assert q["$limit"] == ["500"]
        assert q["$order"] == ["start_date DESC"]
        clause = q["$where"][0]
        for field in w["where_fields"]:
            assert f"upper({field}) like" in clause
        for term in w["where_terms"]:
            assert f"'%{term.upper()}%'" in clause


def test_socrata_where_slice_postfilter_drops_known_false_positives() -> None:
    """I9b-Q008: %TERM% LIKE is recall; the verbatim scan is precision —
    'PARSONS BRINCKERHOFF' (%BRINC%) drops; rows owned by a LATER where
    group record `pruned` and emit there. The Flock vendor row keeps."""
    conn = ProcurementConnector()
    target = next(t for t in _where_targets() if "brinc" in t["where_terms"])
    ctx = _ctx("procportal_nyc_ny")
    ctx.resolved_targets[str(target["url"])] = dict(target)
    cap = _capture(
        ctx,
        str(target["url"]),
        json.dumps(_CROL_WHERE_ROWS).encode(),
        "application/json",
    )
    rows = conn.normalize(ctx, conn.extract(ctx, conn.parse(ctx, cap)))

    index_rows = [r for r in rows if r.get("record_kind") == "portal_index"]
    assert len(index_rows) == 1
    index_row = index_rows[0]
    assert index_row["items_count"] == 4
    assert index_row["precise_count"] == 1
    assert index_row["dropped_count"] == 1  # Parsons Brinckerhoff — recall noise
    assert index_row["pruned_count"] == 2  # owned by the gunshot/clearview groups
    assert index_row["portal_where"] == "crol"
    assert index_row["acq_keyword_terms"] == "crol"
    assert index_row["index_kind"] == "where"
    assert index_row["outcome"] == "items"

    notices = [r for r in rows if r.get("record_kind") == "procurement_notice"]
    kept = {n["external_id"] for n in notices}
    assert kept == {"KP-FLOCK"}
    # The false-positive literals never reach any claim surface.
    for c in rows:
        literal = str(c.get("raw_value") or "") + str(c.get("value") or "")
        assert "BRINCKERHOFF" not in literal
        assert "CLEARVIEW DATA" not in literal


def test_socrata_full_pass_emits_each_envelope_once() -> None:
    """The whole CROL pass emits each record once, under its owning tier:
    KP-FLOCK under 'flock' (g0), KP-DESC under 'gunshot' (g5) with its
    verbatim `content_term` + description-fan-out claims located to the desc
    field; the FP rows drop at their owning groups; the rows fallback prunes
    all four (never a second claim set on an owned envelope)."""
    conn = ProcurementConnector()
    targets = portal_targets(source_id="procportal_nyc_ny")
    ctx = _ctx("procportal_nyc_ny")
    body = json.dumps(_CROL_WHERE_ROWS).encode()
    raws = []
    for target in targets:
        ctx.resolved_targets[str(target["url"])] = dict(target)
        cap = _capture(ctx, str(target["url"]), body, "application/json")
        raws.extend(conn.extract(ctx, conn.parse(ctx, cap)))
    rows = conn.normalize(ctx, raws)

    notices = [r for r in rows if r.get("record_kind") == "procurement_notice"]
    by_id = {n["external_id"]: n for n in notices}
    assert sorted(by_id) == ["KP-DESC", "KP-FLOCK"]
    assert {n["index_kind"] for n in by_id.values()} == {"where"}
    docs = [r for r in rows if r.get("record_kind") == "portal_document"]
    assert {d["external_id"] for d in docs} == {"KP-FLOCK", "KP-DESC"}
    # The fan-out hit carries verbatim term + description claims located to
    # the populated desc field by byte range.
    terms = [
        c
        for c in rows
        if c.get("record_kind") == "claim" and c.get("predicate_id") == "content_term"
    ]
    assert any(
        t["evidence"]["field"] == "additional_description_1"
        and t["raw_value"] == "gunshot detection"
        for t in terms
    )
    desc = [
        c
        for c in rows
        if c.get("record_kind") == "claim" and c.get("predicate_id") == "description"
    ]
    kp_desc = next(c for c in desc if "gunshot detection" in str(c["value"]))
    assert kp_desc["evidence"]["field"] == "additional_description_1"
    assert kp_desc["evidence"]["locator"]["kind"] == "byte_range"
    assert kp_desc["raw_value"] == kp_desc["value"]
    # Every slice records its honest outcome; the fallback pruned all four
    # envelopes to the tighter tier and kept none.
    index = {r["index_kind"]: r for r in rows if r.get("record_kind") == "portal_index"}
    assert index["rows"]["pruned_count"] == 4
    assert index["rows"]["precise_count"] == 0


def test_pruned_fallback_is_deterministic_under_replay() -> None:
    """Replay + shadow over a mixed rows/where capture set diffs to zero —
    the envelope prune is pure and order-stable (SIG-INGEST-017/019)."""
    from connectors.replay import diff_claim_sets, replay, shadow_replay

    conn = ProcurementConnector()
    targets = portal_targets(source_id="procportal_nyc_ny")
    rows_target = next(t for t in targets if t["index_kind"] == "rows")
    where_target = next(t for t in targets if t["index_kind"] == "where")
    ctx = _ctx("procportal_nyc_ny")
    ctx.resolved_targets[str(rows_target["url"])] = dict(rows_target)
    ctx.resolved_targets[str(where_target["url"])] = dict(where_target)
    body = json.dumps(_CROL_WHERE_ROWS).encode()
    captures = [
        _capture(ctx, str(t["url"]), body, "application/json") for t in (rows_target, where_target)
    ]
    # The "current" set runs the same per-capture path the driver runs —
    # run_post_capture includes link-stage object_ref stamps a bare
    # normalize() never produces.
    from connectors.pipeline import run_post_capture

    claims = [c for cap in captures for c in run_post_capture(conn, ctx, cap)]
    diff = shadow_replay(conn, ctx, captures, claims)
    assert diff.changed_count == 0
    replayed = replay(conn, ctx, captures)
    assert diff_claim_sets(claims, replayed).changed_count == 0


def test_portal_where_defs_and_tenant_scope() -> None:
    """AC: the dormant `cook_county` def composes B00329 clauses; only the CROL
    tenant names a portal_where today (Cook County/WA DES rows are P36.7's)."""
    from connectors.procurement import (
        _socrata_where_clause,
        acq_keyword_term_set,
        portal_where_defs,
    )

    defs = portal_where_defs()
    assert {"crol", "cook_county"} <= set(defs)
    cc = defs["cook_county"]
    clause = _socrata_where_clause(cc["fields"], acq_keyword_term_set(cc["terms"])[:2])
    assert "upper(vendor_name) like '%FLOCK%'" in clause
    assert "upper(description) like '%AXON%'" in clause
    wired = [tid for tid, row in portal_tenants().items() if row.get("portal_where")]
    assert wired == ["new_york_ny"]
    # Every other socrata tenant emits only the plain rows window.
    for source_id in (
        "procportal_austin_tx",
        "procportal_sf_ca",
        "procportal_kcmo_mo",
        "procportal_chicago_il",
    ):
        targets = portal_targets(source_id=source_id)
        assert [t["index_kind"] for t in targets] == ["rows"], source_id
        assert all("$where" not in t["url"] for t in targets)
