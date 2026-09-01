# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for the `records` connector (§23.5, §11.19, P07.2).

Cover the four Phase-7 ACs sub-set to this ticket plus the cross-cutting
invariants: the no_responsive_records -> CoverageRecord bridge (SIG-ONTO-040),
targeted-lookup discipline (SIG-INGEST-036/037), MuckRock api_v2 + short-lived JWT
(§23.5, F4.1/F4.2/F4.3) with a run record + quality report per capture, released
documents captured as EvidenceArtifact rows linked from the request, the predicate
allowlist (SIG-INGEST-033), and candidate-identifier-only party keying
(SIG-INGEST-034).
"""

from __future__ import annotations

import dataclasses
import io
import json
import zipfile
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from connectors.net import ChallengeEncountered, PoliteFetcher, RobotsResult
from connectors.records import (
    CrawlAttempted,
    EvidenceArtifactRow,
    InvalidRecordsRequest,
    MuckRockToken,
    MuckRockTokenCache,
    PredicateNotAllowed,
    RecordsConnector,
    RecordsRequest,
    WrongMuckRockApiVersion,
    agency_candidate,
    assert_muckrock_api_v2,
    assert_predicate_allowed,
    assert_targeted_lookup,
    classify_released_document,
    coverage_record_row,
    coverage_trigger_status,
    evidence_artifact_id,
    forbidden_predicate_genres,
    is_predicate_allowed,
    load_claims_for_l1,
    muckrock_endpoint,
    platforms,
    predicate_allowlist,
    response_statuses,
    source_ids,
)
from connectors.registry import get
from connectors.stages import (
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun
from support import load_schemaview

_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"


# --- local fixtures -----------------------------------------------------------


def _ingest_run(name: str = "records") -> IngestRun:
    return IngestRun(
        connector_name=name,
        connector_version="1.0.0",
        code_commit="deadbeef",
        ruleset_version="r1",
        vocab_version="v1",
        input_digests=(),
    )


def _ctx(source_key: str = "nextrequest", **kwargs: Any) -> RunContext:
    """A RunContext against a permitted records source (loader gate open)."""
    source = dataclasses.replace(get(source_ids()[source_key]), ingestion_permitted=True)
    return RunContext(
        source=source,
        run=_ingest_run(),
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        **kwargs,
    )


class _StaticToken:
    """A TokenSource that mints deterministic, monotonically-numbered tokens."""

    def __init__(self) -> None:
        self.calls = 0

    def mint(self) -> str:
        self.calls += 1
        return f"jwt-{self.calls}"


class _Clock:
    """A hand-advanced clock for deterministic TTL tests."""

    def __init__(self, start: datetime | None = None) -> None:
        self.now = start or datetime(2026, 9, 1, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


class _SequenceTransport:
    """A transport that returns queued responses per URL (for refresh-on-401)."""

    def __init__(self, responses: dict[str, list[tuple[int, bytes, str]]]) -> None:
        self._responses = {k: list(v) for k, v in responses.items()}
        self.request_log: list[str] = []
        self.header_log: list[Mapping[str, str] | None] = []

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ROBOTS_ALLOW_ALL)

    def request(
        self, url: str, *, user_agent: str, headers: Mapping[str, str] | None = None
    ) -> FetchResult:
        self.request_log.append(url)
        self.header_log.append(dict(headers) if headers is not None else None)
        status, body, media = self._responses[url].pop(0)
        return FetchResult(url=url, status=status, body=body, media_type=media)


# --- AC1: no_responsive_records -> CoverageRecord (SIG-ONTO-040) --------------


def _no_responsive_request() -> RecordsRequest:
    return RecordsRequest(
        external_id="98765",
        platform="muckrock",
        source_id="muckrock",
        target_agency="Oklahoma City Police Department",
        response_status="no_responsive_records",
        response_date="2026-05-01",
    )


def test_no_responsive_records_writes_a_coverage_record() -> None:
    # SIG-ONTO-040 / AC1: an on-record "no responsive documents" is stored as
    # evidence (a NO_EVIDENCE_FOUND coverage record), never discarded as a null.
    request = _no_responsive_request()
    row = coverage_record_row(request, sources_searched=["muckrock:OKCPD"])
    assert row["record_kind"] == "coverage_record"
    assert row["absence_state"] == "NO_EVIDENCE_FOUND"
    assert row["absence_kind"] == "searched_not_found"
    assert row["raw_value"] == "no_responsive_records"
    assert row["records_request_id"] == "98765"


def test_coverage_record_must_name_the_sources_searched() -> None:
    # SIG-TIME-011: a NO_EVIDENCE_FOUND record without sources is rejected.
    with pytest.raises(ValueError):
        coverage_record_row(_no_responsive_request(), sources_searched=[])


def test_coverage_record_only_for_the_positive_finding_status() -> None:
    fulfilled = dataclasses.replace(_no_responsive_request(), response_status="fulfilled")
    with pytest.raises(ValueError):
        coverage_record_row(fulfilled, sources_searched=["muckrock:OKCPD"])


def test_no_responsive_records_flows_through_normalize() -> None:
    # The bridge fires inside the connector, not just the standalone helper.
    ctx = _ctx("muckrock")
    raw = {
        "record_kind": "records_request",
        "raw": {
            "id": "98765",
            "platform": "muckrock",
            "agency": "Oklahoma City Police Department",
            "status": "no_responsive_records",
        },
    }
    rows = RecordsConnector().normalize(ctx, [raw])
    coverage = [r for r in rows if r.get("record_kind") == "coverage_record"]
    assert len(coverage) == 1
    assert coverage[0]["absence_state"] == "NO_EVIDENCE_FOUND"
    assert coverage[0]["sources_searched"]  # non-empty (SIG-TIME-011)


def test_a_fulfilled_request_writes_no_coverage_record() -> None:
    ctx = _ctx("muckrock")
    raw = {
        "record_kind": "records_request",
        "raw": {"id": "1", "platform": "muckrock", "status": "fulfilled"},
    }
    rows = RecordsConnector().normalize(ctx, [raw])
    assert not any(r.get("record_kind") == "coverage_record" for r in rows)


# --- AC2: targeted-lookup discipline; no crawl (SIG-INGEST-036/037) -----------


def test_crawl_mode_target_is_refused() -> None:
    for mode in ("crawl", "enumerate", "list", "scrape"):
        with pytest.raises(CrawlAttempted):
            assert_targeted_lookup({"mode": mode, "url": "https://x/api_v2/requests/1/"})


def test_paginated_target_is_refused() -> None:
    with pytest.raises(CrawlAttempted):
        assert_targeted_lookup({"url": "https://x/api_v2/requests/", "page": 2})


def test_bare_listing_endpoint_is_refused() -> None:
    with pytest.raises(CrawlAttempted):
        assert_targeted_lookup({"url": "https://www.muckrock.com/api_v2/requests/"})
    with pytest.raises(CrawlAttempted):
        assert_targeted_lookup({"url": "https://x.nextrequest.com/client/requests"})


def test_specific_lookup_is_allowed() -> None:
    # A specific id (in the target or the URL, incl. a filter query) is a lookup.
    assert_targeted_lookup(
        {"external_id": "123", "url": "https://www.muckrock.com/api_v2/requests/123/"}
    )
    assert_targeted_lookup({"url": "https://www.muckrock.com/api_v2/requests/?id=123"})
    assert_targeted_lookup({"document_url": "https://cdn/doc.pdf", "url": "https://cdn/doc.pdf"})


def test_discover_returns_only_supplied_targets_and_refuses_a_crawl() -> None:
    conn = RecordsConnector()
    assert conn.discover(_ctx()) == []
    targets = [{"external_id": "1", "url": "https://www.muckrock.com/api_v2/requests/1/"}]
    assert conn.discover(_ctx(parameters={"targets": targets})) == targets
    with pytest.raises(CrawlAttempted):
        conn.discover(_ctx(parameters={"targets": [{"mode": "crawl", "url": "https://x/"}]}))


# --- AC3: MuckRock api_v2 + short-lived JWT; run record + quality report -------


def test_muckrock_endpoints_are_api_v2_never_v1() -> None:
    # §23.5 / F4.1: the outline's api_v1 reference is wrong.
    url = muckrock_endpoint("requests", "12345")
    assert url == "https://www.muckrock.com/api_v2/requests/12345/"
    assert assert_muckrock_api_v2(url) == url
    with pytest.raises(WrongMuckRockApiVersion):
        assert_muckrock_api_v2("https://www.muckrock.com/api_v1/foia/?format=json")


def test_muckrock_data_endpoint_requires_a_jwt() -> None:
    # F4.2: there is no unauthenticated read path; a run without a token cache is a
    # hard error, not a silent unauthenticated fetch.
    ctx = _ctx("muckrock", fetcher=object(), parameters={})
    conn = RecordsConnector()
    with pytest.raises(WrongMuckRockApiVersion):
        conn.fetch(ctx, {"external_id": "1", "url": muckrock_endpoint("requests", "1")})


def test_fetch_attaches_the_bearer_jwt_to_a_muckrock_data_endpoint() -> None:
    url = muckrock_endpoint("requests", "1")
    transport = _SequenceTransport({url: [(200, b'{"id": 1}', "application/json")]})
    fetcher = PoliteFetcher(
        connector_name="records", connector_version="1.0.0", transport=transport
    )
    cache = MuckRockTokenCache(_StaticToken())
    ctx = _ctx("muckrock", fetcher=fetcher)
    conn = RecordsConnector(token_cache=cache)
    result = conn.fetch(ctx, {"external_id": "1", "url": url})
    assert result.status == 200
    assert transport.header_log[0] == {"Authorization": "Bearer jwt-1"}


def test_jwt_lifetime_is_five_minutes_and_effective_ttl_is_shorter() -> None:
    # F4.3: the token lives 5 minutes; the cache reuses it for a shorter window so
    # a fetch never rides a token about to expire.
    cache = MuckRockTokenCache(_StaticToken())
    assert cache._ttl == 300
    assert cache.effective_ttl_seconds < 300


def test_the_jwt_cache_refreshes_before_the_token_expires() -> None:
    clock = _Clock()
    cache = MuckRockTokenCache(_StaticToken(), clock=clock)
    first = cache.token()
    assert cache.mint_count == 1
    # Within the effective TTL: same token, no re-mint.
    clock.advance(cache.effective_ttl_seconds - 1)
    assert cache.token().access == first.access
    assert cache.mint_count == 1
    # Past the refresh margin: a fresh token is minted (never rides a stale JWT).
    clock.advance(5)
    assert cache.token().access != first.access
    assert cache.mint_count == 2


def test_token_expiry_semantics() -> None:
    token = MuckRockToken(access="j", issued_at=datetime(2026, 9, 1, tzinfo=UTC), ttl_seconds=300)
    assert not token.is_expired(datetime(2026, 9, 1, 0, 4, tzinfo=UTC))
    assert token.is_expired(datetime(2026, 9, 1, 0, 5, tzinfo=UTC))
    assert token.needs_refresh(datetime(2026, 9, 1, 0, 4, 40, tzinfo=UTC), margin_seconds=30)


def test_fetch_refreshes_the_jwt_on_a_401_and_retries_once() -> None:
    # F4.3: a 401 mid-run means the 5-minute token expired; refresh once and retry.
    url = muckrock_endpoint("requests", "1")
    transport = _SequenceTransport(
        {url: [(401, b"", "application/json"), (200, b'{"id": 1}', "application/json")]}
    )
    fetcher = PoliteFetcher(
        connector_name="records", connector_version="1.0.0", transport=transport
    )
    source = _StaticToken()
    cache = MuckRockTokenCache(source)
    ctx = _ctx("muckrock", fetcher=fetcher)
    conn = RecordsConnector(token_cache=cache)
    result = conn.fetch(ctx, {"external_id": "1", "url": url})
    assert result.status == 200
    assert source.calls == 2  # minted once, then refreshed on the 401
    assert transport.request_log == [url, url]


def test_a_persistent_challenge_still_propagates() -> None:
    # Two 401s: the refresh-retry does not defeat a genuine, persistent challenge.
    url = muckrock_endpoint("requests", "1")
    transport = _SequenceTransport(
        {url: [(401, b"", "application/json"), (401, b"", "application/json")]}
    )
    fetcher = PoliteFetcher(
        connector_name="records", connector_version="1.0.0", transport=transport
    )
    ctx = _ctx("muckrock", fetcher=fetcher)
    conn = RecordsConnector(token_cache=MuckRockTokenCache(_StaticToken()))
    with pytest.raises(ChallengeEncountered):
        conn.fetch(ctx, {"external_id": "1", "url": url})


def test_a_run_record_and_quality_report_are_produced_per_capture() -> None:
    # AC3: a run record (IngestRun on ctx.run) + a quality report per capture.
    ctx = _ctx("muckrock")
    raw = {
        "record_kind": "records_request",
        "raw": {
            "id": "1",
            "platform": "muckrock",
            "status": "fulfilled",
            "released_documents": ["https://cdn/a.pdf"],
        },
    }
    rows = RecordsConnector().normalize(ctx, [raw])
    reports = [r for r in rows if r.get("record_kind") == "quality_report"]
    assert len(reports) == 1
    report = reports[0]
    assert report["capture_kind"] == "records_request"
    assert report["connector_name"] == "records"
    assert report["records_request_count"] == 1
    assert report["released_document_count"] == 1
    # The run record itself is the IngestRun the run threads through (SIG-EVID-016).
    assert ctx.run.to_row()["connector_name"] == "records"


# --- AC4: released documents captured as EvidenceArtifact rows, linked ---------


def test_released_documents_link_by_stable_artifact_id() -> None:
    urls = ["https://cdn/a.pdf", "https://cdn/b.pdf"]
    request = RecordsRequest(
        external_id="1",
        platform="muckrock",
        source_id="muckrock",
        released_documents=tuple(evidence_artifact_id(u) for u in urls),
    )
    assert request.released_documents == (
        evidence_artifact_id(urls[0]),
        evidence_artifact_id(urls[1]),
    )
    # The id is a stable function of the source URI (linkage holds pre-capture).
    assert evidence_artifact_id(urls[0]) == evidence_artifact_id(urls[0])
    assert evidence_artifact_id(urls[0]) != evidence_artifact_id(urls[1])


def test_a_released_document_capture_becomes_an_evidence_artifact_linked_to_the_request() -> None:
    # AC4: drive the connector over a released-document capture and assert the
    # EvidenceArtifact row's id matches what the request links to.
    ctx = _ctx("documentcloud")
    url = "https://cdn/response.pdf"
    pdf = b"%PDF-1.4\n1 0 obj<< /Font << >> >>endobj\ntrailer<< >>\n%%EOF"
    capture = ctx.captures.put(pdf, media_type="application/pdf", source_uri=url)
    conn = RecordsConnector()
    parsed = conn.parse(ctx, capture)
    extracted = conn.extract(ctx, parsed)
    rows = conn.normalize(ctx, extracted)
    artifacts = [r for r in rows if r.get("record_kind") == "evidence_artifact"]
    assert len(artifacts) == 1
    assert artifacts[0]["subject_id"] == evidence_artifact_id(url)
    assert artifacts[0]["capture_digest"] == capture.digest
    # The classification verdict proves the P07.1 parser was called (SIG-PARSE-002).
    assert artifacts[0]["classification"]["file_format"] == "pdf"
    assert artifacts[0]["classification"]["recommended_layer"] == "pdf_text"


def test_a_mixed_format_zip_response_is_classified_per_member() -> None:
    # A records response bundle is a mixed-format ZIP → classified per member,
    # by calling the P07.1 parser (classify_archive), not parsed here.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("scan.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
        zf.writestr("data.csv", b"a,b\n1,2\n")
    verdict = classify_released_document("response.zip", buf.getvalue())
    row = verdict.to_row()
    assert row["file_format"] == "zip"
    assert {m["filename"] for m in row["members"]} == {"scan.png", "data.csv"}


def test_evidence_artifact_row_shape() -> None:
    artifact = EvidenceArtifactRow(
        artifact_id=evidence_artifact_id("https://cdn/a.pdf"),
        source_id="documentcloud",
        source_uri="https://cdn/a.pdf",
        capture_digest="deadbeef",
        media_type="application/pdf",
        byte_size=10,
        records_request_id="1",
        classification={"file_format": "pdf"},
    )
    row = artifact.to_row()
    assert row["published_by"] == "documentcloud"
    assert row["predicate_id"] == "released_documents"
    assert row["capture_digest"] == "deadbeef"


# --- Predicate allowlist (SIG-INGEST-033) -------------------------------------


def test_predicate_allowlist_is_the_records_request_surface() -> None:
    assert "records_request" in predicate_allowlist()
    for predicate in (
        "records_request",
        "requesting_party",
        "target_agency",
        "request_text",
        "filed_date",
        "response_date",
        "response_status",
        "statutory_basis",
        "platform",
        "external_id",
        "released_documents",
    ):
        assert is_predicate_allowed(predicate), predicate


def test_writing_outside_the_allowlist_is_a_schema_error() -> None:
    with pytest.raises(PredicateNotAllowed):
        assert_predicate_allowed("deployment_exists")
    with pytest.raises(PredicateNotAllowed):
        assert_predicate_allowed("contract_value")


def test_forbidden_genres_are_outside_the_allowlist() -> None:
    for genre in forbidden_predicate_genres():
        assert not is_predicate_allowed(genre), genre


# --- Vocabulary lock-step with the frozen ontology enums (§11.19) -------------


def test_response_status_vocab_matches_the_ontology_enum() -> None:
    sv = load_schemaview()
    enum = set(sv.get_enum("RecordsResponseStatus").permissible_values)
    assert response_statuses() == enum
    # SIG-ONTO-040: the coverage trigger is a real member of the vocabulary.
    assert coverage_trigger_status() in enum


def test_platform_vocab_matches_the_ontology_enum() -> None:
    sv = load_schemaview()
    enum = set(sv.get_enum("RecordsPlatform").permissible_values)
    assert platforms() == enum


# --- Candidate identifiers only, never resolution (SIG-INGEST-034) ------------


def test_party_predicates_carry_a_candidate_identifier_not_a_resolution() -> None:
    request = RecordsRequest(
        external_id="1",
        platform="muckrock",
        source_id="muckrock",
        target_agency="Oklahoma City Police Department",
    )
    rows = request.claim_rows()
    agency_rows = [r for r in rows if r.get("predicate_id") == "target_agency"]
    assert len(agency_rows) == 1
    ident = agency_rows[0]["candidate_identifier"]
    assert ident["scheme"] == "records.agency_name"  # a name → surrogate path
    assert "resolved_entity_id" not in agency_rows[0]


def test_numeric_agency_routes_to_the_platform_scheme() -> None:
    assert agency_candidate("4242", platform="muckrock") == {
        "scheme": "muckrock.agency",
        "value": "4242",
    }
    assert agency_candidate("OKCPD", platform="muckrock")["scheme"] == "records.agency_name"


# --- RecordsRequest validation (§11.19) ---------------------------------------


def test_invalid_platform_is_rejected() -> None:
    with pytest.raises(InvalidRecordsRequest):
        RecordsRequest(external_id="1", platform="carrier_pigeon", source_id="muckrock")


def test_invalid_response_status_is_rejected() -> None:
    with pytest.raises(InvalidRecordsRequest):
        RecordsRequest(
            external_id="1", platform="muckrock", source_id="muckrock", response_status="pending"
        )


def test_external_id_is_required() -> None:
    with pytest.raises(InvalidRecordsRequest):
        RecordsRequest(external_id="", platform="muckrock", source_id="muckrock")


# --- Append-only load contract (SIG-INGEST-003) -------------------------------


def test_load_adds_identity_only_to_claim_and_entity_rows() -> None:
    rows = [
        {"record_kind": "records_request", "subject_id": "records:muckrock:1"},
        {"record_kind": "claim", "subject_id": "records:muckrock:1", "predicate_id": "external_id"},
        {"record_kind": "coverage_record", "subject_id": "agency:x"},
        {"record_kind": "evidence_artifact", "subject_id": "records:artifact:z"},
        {"record_kind": "quality_report", "capture_digest": "d"},
    ]
    loaded = load_claims_for_l1(rows)
    by_kind = {r["record_kind"]: r for r in loaded}
    assert "claim_id" in by_kind["records_request"] and "sys_period" in by_kind["records_request"]
    assert "claim_id" in by_kind["claim"]
    assert "claim_id" not in by_kind["coverage_record"]
    assert "claim_id" not in by_kind["evidence_artifact"]
    assert "claim_id" not in by_kind["quality_report"]


# --- Integration: the full pipeline over a records request (SIG-INGEST-001) ---


def test_the_pipeline_ingests_a_records_request_end_to_end() -> None:
    from connectors import pipeline

    url = "https://city.nextrequest.com/client/requests/req-77"
    payload = {
        "id": "req-77",
        "platform": "nextrequest",
        "agency": "Example PD",
        "status": "fulfilled",
        "title": "ALPR contracts",
        "documents": [{"url": "https://cdn/a.pdf"}, {"url": "https://cdn/b.pdf"}],
    }
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    transport = _SequenceTransport({url: [(200, body, "application/json")]})
    fetcher = PoliteFetcher(
        connector_name="records", connector_version="1.0.0", transport=transport
    )
    ctx = _ctx(
        "nextrequest",
        fetcher=fetcher,
        parameters={"targets": [{"external_id": "req-77", "url": url}]},
    )
    report = pipeline.run(RecordsConnector(), ctx)
    assert report.asserted
    assert report.captures  # the request JSON was captured
    kinds = {c.get("record_kind") for c in report.claims}
    assert "records_request" in kinds
    assert "quality_report" in kinds
    # The request links both released documents by stable EvidenceArtifact id.
    entity = next(c for c in report.claims if c.get("record_kind") == "records_request")
    assert entity["released_documents"] == [
        evidence_artifact_id("https://cdn/a.pdf"),
        evidence_artifact_id("https://cdn/b.pdf"),
    ]


def test_released_documents_captured_in_a_follow_up_run_match_the_request_links() -> None:
    # AC4 end-to-end: the request run links documents by id; a targeted follow-up
    # run that captures those documents produces EvidenceArtifact rows with exactly
    # those ids — the request↔artifact linkage holds across the two targeted runs.
    from connectors import pipeline

    req_url = "https://city.nextrequest.com/client/requests/req-9"
    doc_urls = ["https://cdn/x.pdf", "https://cdn/y.pdf"]
    payload = {
        "id": "req-9",
        "platform": "nextrequest",
        "status": "fulfilled",
        "documents": [{"url": u} for u in doc_urls],
    }
    pdf = b"%PDF-1.4\n1 0 obj<< /Font << >> >>endobj\n%%EOF"
    responses = {req_url: [(200, json.dumps(payload, sort_keys=True).encode(), "application/json")]}
    for u in doc_urls:
        responses[u] = [(200, pdf, "application/pdf")]
    transport = _SequenceTransport(responses)
    fetcher = PoliteFetcher(
        connector_name="records", connector_version="1.0.0", transport=transport
    )

    req_ctx = _ctx(
        "nextrequest",
        fetcher=fetcher,
        parameters={"targets": [{"external_id": "req-9", "url": req_url}]},
    )
    req_report = pipeline.run(RecordsConnector(), req_ctx)
    entity = next(c for c in req_report.claims if c.get("record_kind") == "records_request")
    linked_ids = set(entity["released_documents"])

    doc_ctx = _ctx(
        "nextrequest",
        fetcher=fetcher,
        parameters={"targets": [{"document_url": u, "url": u} for u in doc_urls]},
    )
    doc_report = pipeline.run(RecordsConnector(), doc_ctx)
    artifact_ids = {
        c["subject_id"] for c in doc_report.claims if c.get("record_kind") == "evidence_artifact"
    }
    assert artifact_ids == linked_ids
    assert len(artifact_ids) == 2
