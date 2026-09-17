# SPDX-License-Identifier: Apache-2.0
"""P26.6 — agenda-document continuation: the procurement connector resolves
linked agenda/minutes/matter documents off a captured index, fetches them under
a reviewed per-tenant/per-run bound carried on the target row as data, and emits
typed ``content_term`` claims whose ``raw_value`` is a verbatim slice of the
captured document text located by a byte_range/page locator (the OKC document
convention). A document that does not parse as the platform's declared genre
records ContentDrift per document (the run continues); empty documents, refused
fetches, and gone documents record honest outcomes — never a fabricated claim.
"""

import dataclasses
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import connectors.procurement as procurement
import pytest
from connectors.net import PoliteFetcher, RateLimiter, RobotsResult
from connectors.pipeline import run
from connectors.procurement import (
    ProcurementConnector,
    content_guard_token,
    content_terms,
    scan_agenda_content,
    source_ids,
    tenant_targets,
)
from connectors.registry import get
from connectors.stages import (
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun

FIXTURES = Path(__file__).parent / "fixtures" / "promoted"
_ALLOW_ALL = "User-agent: *\nAllow: /\n"


def _fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _ingest_run() -> IngestRun:
    return IngestRun(
        connector_name="procurement",
        connector_version="1.0.0",
        code_commit="deadbeef",
        ruleset_version="r1",
        vocab_version="v1",
        input_digests=(),
    )


class _MapTransport:
    """URL-substring-keyed canned responses — no real network."""

    def __init__(self) -> None:
        self.responses: list[tuple[str, int, bytes, str]] = []
        self.robots_map: dict[str, str] = {}
        self.requested: list[str] = []

    def add(self, needle: str, status: int, body: bytes, media: str) -> None:
        self.responses.append((needle, status, body, media))

    def robots(self, robots_url: str) -> RobotsResult:
        for needle, text in self.robots_map.items():
            if needle in robots_url:
                return RobotsResult(text=text, status=200)
        return RobotsResult(text=_ALLOW_ALL, status=200)

    def request(
        self, url: str, *, user_agent: str, headers: Any = None, body: bytes | None = None
    ) -> FetchResult:
        self.requested.append(url)
        for needle, status, resp_body, media in self.responses:
            if needle in url:
                return FetchResult(
                    url=url,
                    status=status,
                    body=resp_body,
                    media_type=media,
                    retrieved_at=datetime(2026, 9, 17, tzinfo=UTC),
                )
        return FetchResult(
            url=url,
            status=404,
            body=b"",
            media_type="text/plain",
            retrieved_at=datetime(2026, 9, 17, tzinfo=UTC),
        )


def _target(platform: str) -> dict[str, Any]:
    return tenant_targets(platform)[0]


@pytest.fixture
def pin_tenant(monkeypatch: pytest.MonkeyPatch):
    """Restrict an agenda-platform run to ONE tenant target — the registry fans
    out to every tenant by design, so tests pin the tenant set deterministically."""

    def _pin(platform: str) -> dict[str, Any]:
        target = _target(platform)
        monkeypatch.setattr(procurement, "tenant_targets", lambda platform=None: [target])
        return target

    return _pin


def _run_platform(
    platform: str, transport: _MapTransport, *, target: dict[str, Any]
) -> tuple[Any, RunContext]:
    """A full pipeline run over one agenda-platform tenant (loader gate open)."""
    source = dataclasses.replace(get(source_ids()[platform]), ingestion_permitted=True)
    fetcher = PoliteFetcher(
        connector_name="procurement",
        connector_version="1.0.0",
        transport=transport,
        rate_limiter=RateLimiter(sleep=lambda s: None),
    )
    ctx = RunContext(
        source=source,
        run=_ingest_run(),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": [target]},
    )
    return run(ProcurementConnector(), ctx), ctx


def _claims(report: Any, predicate: str) -> list[dict[str, Any]]:
    return [
        c
        for c in report.claims
        if c.get("record_kind") == "claim" and c.get("predicate_id") == predicate
    ]


def _doc_rows(report: Any) -> list[dict[str, Any]]:
    return [c for c in report.claims if c.get("record_kind") == "agenda_document"]


# --- bounds ride the target row as data (AC1) --------------------------------


def test_reviewed_document_bounds_ride_every_agenda_target() -> None:
    for platform in ("legistar", "primegov", "civicclerk", "escribe"):
        targets = tenant_targets(platform)
        assert targets, platform
        for t in targets:
            assert isinstance(t["doc_per_tenant"], int) and t["doc_per_tenant"] > 0
            assert isinstance(t["doc_run_cap"], int) and t["doc_run_cap"] > 0


def test_per_tenant_window_is_target_data_not_code(
    pin_tenant: Any,
) -> None:
    """Shrinking the reviewed bound on the row shrinks the fan-out — the bound
    is data, never a hidden constant."""
    target = dict(_target("legistar"))
    target["doc_per_tenant"] = 1
    pin_tenant("legistar")
    transport = _MapTransport()
    transport.add("/matters?", 200, _fixture("legistar_seattle_matters.json"), "application/json")
    transport.add(
        "/matters/",
        200,
        _fixture("legistar_seattle_matter_11400.json"),
        "application/json",
    )
    report, _ctx = _run_platform("legistar", transport, target=target)
    doc_requests = [
        u for u in transport.requested if "/matters/" in u.rstrip("/").rsplit("?", 1)[0]
    ]
    assert len(doc_requests) == 1
    assert _doc_rows(report)


# --- the reviewed vocabulary (AC2) --------------------------------------------


def test_content_vocab_covers_the_ticket_terms() -> None:
    text = (
        "alpr automated license plate flock safety vigilant rtcc real-time crime "
        "drone uas shotspotter soundthinking surveillance ordinance ccops "
        "facial recognition body-worn cctv license plate reader"
    )
    matched_ids = {m["term_id"] for m in scan_agenda_content(text)}
    for term_id in (
        "alpr",
        "flock_safety",
        "vigilant",
        "rtcc",
        "drone",
        "shotspotter",
        "surveillance_ordinance",
        "facial_recognition",
        "body_worn_camera",
        "cctv",
    ):
        assert term_id in matched_ids, term_id


def test_matched_literals_are_verbatim_not_normalized() -> None:
    text = "the CCTV network expansion"
    cctv = next(m for m in scan_agenda_content(text) if m["term_id"] == "cctv")
    assert cctv["literal"] == "CCTV"
    assert text[cctv["start"] : cctv["end"]] == "CCTV"


def test_contract_notice_terms_match_procurement_matter_language() -> None:
    ids = {m["term_id"] for m in scan_agenda_content("a professional services agreement")}
    assert "contract_notice" in ids


def test_forbidden_token_guard() -> None:
    assert content_guard_token("hotlist hit for plate number ABC123") is not None
    assert content_guard_token("automated license plate") is None


def test_content_terms_are_reviewed_data() -> None:
    terms = content_terms()
    assert len(terms) >= 14
    assert all(t["id"] and t["patterns"] for t in terms)


# --- per-platform document paths (AC1/AC2) -------------------------------------


def test_legistar_matter_document_emits_verbatim_claims(pin_tenant: Any) -> None:
    target = pin_tenant("legistar")
    transport = _MapTransport()
    transport.add("/matters?", 200, _fixture("legistar_seattle_matters.json"), "application/json")
    transport.add(
        "/matters/",
        200,
        _fixture("legistar_seattle_matter_11400.json"),
        "application/json",
    )
    report, ctx = _run_platform("legistar", transport, target=target)

    claims = _claims(report, "content_term")
    assert claims, "the matter detail document carries surveillance terms"
    docs = _doc_rows(report)
    assert docs and all(d["outcome"] == "matched" for d in docs)
    body = ctx.captures.get(docs[0]["capture_digest"])
    text = body.decode("utf-8")
    for claim in claims:
        raw = claim["raw_value"]
        locator = claim["evidence"]["locator"]
        # verbatim: the emitted literal is a slice of the captured document
        # text at the locator's byte_range (the OKC convention, AC2).
        assert locator["kind"] == "byte_range"
        assert text[locator["start"] : locator["end"]] == raw
    values = {c["value"] for c in claims}
    assert {"alpr", "flock_safety", "surveillance_ordinance"} & values
    # Claims land on the matter's own agenda_item subject; a contract-type
    # matter additionally carries them on its contract subject.
    assert all(
        c["subject_id"].startswith(("agenda_item:legistar:", "contract:legistar:")) for c in claims
    )
    # The capture↔document map lives on the agenda_document row, not inside the
    # claim: a byte-volatile capture id must not key the claim's content_digest
    # (a re-fetch of a churning page then mints duplicate claims).
    doc_urls = {d["raw_value"] for d in docs}
    assert all(c["evidence"]["source_url"] in doc_urls for c in claims)
    assert all(d["capture_digest"] for d in docs)


def test_civicclerk_meeting_document_via_agenda_id(pin_tenant: Any) -> None:
    target = pin_tenant("civicclerk")
    transport = _MapTransport()
    transport.add("/v1/Events", 200, _fixture("civicclerk_maui_events.json"), "application/json")
    transport.add(
        "/v1/Meetings/4501",
        200,
        _fixture("civicclerk_maui_meeting_4501.json"),
        "application/json",
    )
    report, _ctx = _run_platform("civicclerk", transport, target=target)

    meeting_requests = [u for u in transport.requested if "/v1/Meetings/" in u]
    # agendaId 4501 resolves a document; the event with agendaId 0 resolves none.
    assert meeting_requests == [f"https://{target['tenant']}.api.civicclerk.com/v1/Meetings/4501"]
    claims = _claims(report, "content_term")
    values = {c["value"] for c in claims}
    assert "alpr" in values and "body_worn_camera" in values
    assert all(c["evidence"]["locator"]["kind"] == "byte_range" for c in claims)


def test_escribe_meeting_page_html(pin_tenant: Any) -> None:
    target = pin_tenant("escribe")
    transport = _MapTransport()
    transport.add(
        "GetCalendarMeetings",
        200,
        _fixture("escribe_victoria_meetings.json"),
        "application/json",
    )
    transport.add("/Meeting.aspx?Id=", 200, _fixture("escribe_nanaimo_meeting.html"), "text/html")
    report, _ctx = _run_platform("escribe", transport, target=target)

    claims = _claims(report, "content_term")
    values = {c["value"] for c in claims}
    assert {"shotspotter", "rtcc", "cctv"} & values
    assert all(c["evidence"]["locator"]["kind"] == "byte_range" for c in claims)


def test_primegov_portal_link_from_captured_payload(pin_tenant: Any) -> None:
    target = pin_tenant("primegov")
    transport = _MapTransport()
    transport.add("/search", 200, _fixture("primegov_lacity_search.json"), "application/json")
    transport.add(
        "/Portal/Meeting",
        200,
        _fixture("primegov_portal_meeting.html"),
        "text/html",
    )
    report, _ctx = _run_platform("primegov", transport, target=target)

    portal_requests = [u for u in transport.requested if "/Portal/Meeting" in u]
    # The document URL is the meeting's own portal-link field — never constructed.
    assert portal_requests
    assert all(
        u.startswith("https://lacity.primegov.com/Portal/Meeting?meetingTemplateId=")
        for u in portal_requests
    )
    assert "https://lacity.primegov.com/Portal/Meeting?meetingTemplateId=5512" in portal_requests
    values = {c["value"] for c in _claims(report, "content_term")}
    assert {"alpr", "drone"} & values


def test_pdf_document_extracts_page_locators(pin_tenant: Any) -> None:
    target = pin_tenant("primegov")  # doc_genre "any" — the bytes decide
    transport = _MapTransport()
    transport.add("/search", 200, _fixture("primegov_lacity_search.json"), "application/json")
    transport.add("/Portal/Meeting", 200, _fixture("agenda_cctv_doc.pdf"), "application/pdf")
    report, _ctx = _run_platform("primegov", transport, target=target)

    claims = _claims(report, "content_term")
    assert claims
    assert all(c["evidence"]["locator"]["kind"] == "page" for c in claims)
    assert all(c["evidence"]["locator"]["page"] == 1 for c in claims)
    assert {c["value"] for c in claims} >= {"cctv", "drone"}


# --- honest outcomes (AC3) -----------------------------------------------------


def test_genre_drift_records_per_document_and_the_run_continues(
    pin_tenant: Any,
) -> None:
    target = pin_tenant("civicclerk")
    index = json.loads(_fixture("civicclerk_maui_events.json"))
    index[1]["agendaId"] = 4502  # a second event carrying an agenda
    transport = _MapTransport()
    transport.add("/v1/Events", 200, json.dumps(index).encode(), "application/json")
    # 4501 answers HTML where JSON was declared — genre drift, fail closed.
    transport.add("/v1/Meetings/4501", 200, b"<html>oops</html>", "text/html")
    transport.add(
        "/v1/Meetings/4502",
        200,
        _fixture("civicclerk_maui_meeting_4501.json"),
        "application/json",
    )
    report, _ctx = _run_platform("civicclerk", transport, target=target)

    assert len(report.drifted) == 1
    drift = report.drifted[0]
    assert "Meetings/4501" in drift["url"]
    assert drift["platform"] == "civicclerk"
    assert drift["refusal"] == "ContentDrift"
    assert "genre" in drift["detail"] or "JSON" in drift["detail"]
    # the sibling document still extracted — per-document isolation (AC3)
    assert _claims(report, "content_term")


def test_missing_required_fields_is_drift_not_a_document(pin_tenant: Any) -> None:
    target = pin_tenant("legistar")
    transport = _MapTransport()
    transport.add("/matters?", 200, _fixture("legistar_seattle_matters.json"), "application/json")
    transport.add("/matters/", 200, b'{"Unexpected": true}', "application/json")
    report, _ctx = _run_platform("legistar", transport, target=target)
    assert report.drifted, "a JSON body missing every required field is drift"
    assert not _doc_rows(report)


def test_empty_document_records_empty_outcome(pin_tenant: Any) -> None:
    target = pin_tenant("escribe")
    transport = _MapTransport()
    transport.add(
        "GetCalendarMeetings",
        200,
        _fixture("escribe_victoria_meetings.json"),
        "application/json",
    )
    transport.add("/Meeting.aspx?Id=", 200, b"<html><body> </body></html>", "text/html")
    report, _ctx = _run_platform("escribe", transport, target=target)

    docs = _doc_rows(report)
    assert docs and all(d["outcome"] == "empty" for d in docs)
    assert not _claims(report, "content_term")


def test_robots_refused_document_records_a_politeness_refusal(pin_tenant: Any) -> None:
    target = pin_tenant("escribe")
    transport = _MapTransport()
    transport.add(
        "GetCalendarMeetings",
        200,
        _fixture("escribe_victoria_meetings.json"),
        "application/json",
    )
    # The index path is allowed; the document path is robots-disallowed — the
    # honest outcome is a recorded per-document politeness refusal, no capture,
    # no claims, and the run continues.
    transport.robots_map["escribemeetings.com"] = "User-agent: *\nDisallow: /Meeting.aspx\n"
    report, _ctx = _run_platform("escribe", transport, target=target)

    refusals = [r for r in report.refusals if "Meeting.aspx" in r["url"]]
    assert refusals, "a robots-disallowed document is a recorded refusal"
    assert refusals[0]["refusal"] == "RobotsDisallowed"
    assert not _doc_rows(report)


def test_document_404_records_a_disappearance_not_a_row(pin_tenant: Any) -> None:
    target = pin_tenant("escribe")
    transport = _MapTransport()
    transport.add(
        "GetCalendarMeetings",
        200,
        _fixture("escribe_victoria_meetings.json"),
        "application/json",
    )
    transport.add("/Meeting.aspx?Id=", 404, b"", "text/plain")
    report, _ctx = _run_platform("escribe", transport, target=target)

    assert report.disappearances, "a gone document is a first-class disappearance"
    assert not _doc_rows(report)
    assert not _claims(report, "content_term")


# --- window + idempotency (AC3/AC4) --------------------------------------------


def test_discover_more_needs_an_index_capture() -> None:
    # no index capture → nothing resolved
    ctx = RunContext(
        source=dataclasses.replace(get(source_ids()["legistar"]), ingestion_permitted=True),
        run=_ingest_run(),
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={},
    )
    assert ProcurementConnector().discover_more(ctx, ()) == []

    # non-agenda sources never fan out
    ctx2 = RunContext(
        source=dataclasses.replace(get(source_ids()["sourcewell"]), ingestion_permitted=True),
        run=_ingest_run(),
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={},
    )
    assert ProcurementConnector().discover_more(ctx2, ()) == []


def test_rerun_is_idempotent(pin_tenant: Any) -> None:
    def once() -> tuple[set[str], set[str]]:
        target = pin_tenant("legistar")
        transport = _MapTransport()
        transport.add(
            "/matters?",
            200,
            _fixture("legistar_seattle_matters.json"),
            "application/json",
        )
        transport.add(
            "/matters/",
            200,
            _fixture("legistar_seattle_matter_11400.json"),
            "application/json",
        )
        report, _ctx = _run_platform("legistar", transport, target=target)
        claim_rows = {
            json.dumps(
                {k: c.get(k) for k in ("subject_id", "predicate_id", "value", "raw_value")},
                sort_keys=True,
            )
            for c in report.claims
        }
        return {c.digest for c in report.captures}, claim_rows

    captures_a, claims_a = once()
    captures_b, claims_b = once()
    assert captures_a == captures_b
    assert claims_a == claims_b


# --- guards --------------------------------------------------------------------


def test_no_person_or_per_datum_predicates_are_emitted(pin_tenant: Any) -> None:
    target = pin_tenant("legistar")
    transport = _MapTransport()
    transport.add("/matters?", 200, _fixture("legistar_seattle_matters.json"), "application/json")
    transport.add(
        "/matters/",
        200,
        _fixture("legistar_seattle_matter_11400.json"),
        "application/json",
    )
    report, _ctx = _run_platform("legistar", transport, target=target)
    forbidden = {
        "officer_name",
        "person_name",
        "plate_number",
        "per_trip",
        "per_search",
    }
    for claim in report.claims:
        assert claim.get("predicate_id") not in forbidden
        raw = str(claim.get("raw_value") or "")
        assert "hotlist" not in raw.lower()


def test_document_url_uses_captured_fields_only() -> None:
    from connectors.procurement import _document_url

    ep = {"doc_url_template": "{api_base}/Meetings/{item_id}", "doc_id_keys": ["agendaId"]}
    index_target = {"api_base": "https://x.example/v1", "tenant": "x"}
    assert _document_url({"agendaId": 7}, index_target, ep) == "https://x.example/v1/Meetings/7"
    # a zero/absent id resolves no document — never a guessed URL
    assert _document_url({"agendaId": 0}, index_target, ep) is None
    assert _document_url({}, index_target, ep) is None
    # an item's own link field wins over the template (doc_link_keys)
    ep2 = {"doc_link_keys": ["portalLink"], "doc_url_template": "{api_base}/x/{item_id}"}
    assert (
        _document_url({"portalLink": "https://p.example/doc/9"}, index_target, ep2)
        == "https://p.example/doc/9"
    )


def test_bounded_window_is_stable_under_shuffled_index_order() -> None:
    """eScribe's calendar endpoint returns the same meeting SET in a different
    order per call (verified live 2026-09-17). The bounded selection is a
    function of the item set — doc_order_fields date desc, id tie-break — so a
    shuffled index yields the same document window and a re-run dedupes."""
    from connectors.procurement import _select_document_items

    items = [
        {"ID": f"id-{n}", "StartDate": f"2026/0{n + 1}/15 10:00:00", "MeetingName": f"M{n}"}
        for n in range(6)
    ]
    cfg = {"doc_order_fields": ["StartDate"]}
    first = _select_document_items(items, {}, cfg, 3)
    shuffled = [items[i] for i in (3, 0, 5, 1, 4, 2)]
    second = _select_document_items(shuffled, {}, cfg, 3)
    assert [i["ID"] for i, _ in first] == [i["ID"] for i, _ in second]
    # most-recent-first: the three newest meetings are the window
    assert {i["ID"] for i, _ in first} == {"id-5", "id-4", "id-3"}


def test_same_item_set_reselects_same_documents_end_to_end(pin_tenant: Any) -> None:
    """End-to-end: two runs over the same meeting set in different payload
    order fetch the same bounded document set (idempotent window)."""
    meetings = [
        {"ID": f"m-{n}", "StartDate": f"2026/0{n + 1}/10 12:00:00", "MeetingName": f"Meeting {n}"}
        for n in range(5)
    ]

    def _payload(order: list[int]) -> bytes:
        return json.dumps({"d": [meetings[i] for i in order]}).encode()

    def _one_run(order: list[int]) -> tuple[Any, _MapTransport]:
        target = dict(pin_tenant("escribe"))
        target["doc_per_tenant"] = 2
        transport = _MapTransport()
        transport.add("GetCalendarMeetings", 200, _payload(order), "application/json")
        transport.add("Meeting.aspx", 200, _fixture("escribe_nanaimo_meeting.html"), "text/html")
        return _run_platform("escribe", transport, target=target)[0], transport

    _r1, t1 = _one_run([0, 1, 2, 3, 4])
    _r2, t2 = _one_run([4, 2, 0, 3, 1])
    docs1 = sorted(u for u in t1.requested if "Meeting.aspx" in u)
    docs2 = sorted(u for u in t2.requested if "Meeting.aspx" in u)
    assert docs1 == docs2 and len(docs1) == 2
