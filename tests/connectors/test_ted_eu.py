# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P26.15 (SOURCES.14) — the EU tender sweep: TED (Tenders Electronic Daily).

Tests the bounded Search-API sweep end to end over the committed real-capture
fixture: target generation (11 keyword + 10 verified CPV slices, one
PAGE_NUMBER page each), the verbatim POST body, fail-closed envelope/shape
checks, per-slice outcome rows, verbatim-literal ``matched_keyword`` claims,
the alpha-3→alpha-2 jurisdiction mapping, and the procured-≠-deployed
invariant — a tender notice asserts procurement text, never deployment.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest
from connectors.net import PoliteFetcher, RobotsResult
from connectors.procurement import (
    PredicateNotAllowed,
    ProcurementConnector,
    assert_predicate_allowed,
    source_ids,
    ted_eu_country_map,
    ted_eu_cpv_codes,
    ted_eu_keywords,
    ted_eu_search_targets,
    ted_eu_sweep_config,
)
from connectors.registry import get
from connectors.stages import (
    ContentDrift,
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun

from connectors import pipeline

_FIXTURE = Path(__file__).parent / "fixtures" / "ted_eu_search_page1.json"
_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"
_ENDPOINT = "https://api.ted.europa.eu/v3/notices/search"


# --- local fixtures -----------------------------------------------------------


def _ingest_run() -> IngestRun:
    return IngestRun(
        connector_name="procurement",
        connector_version="1.0.0",
        code_commit="deadbeef",
        ruleset_version="r1",
        vocab_version="v1",
        input_digests=(),
    )


def _ctx(**kwargs: Any) -> RunContext:
    """A RunContext against the ted_eu source (loader gate open for the test)."""
    source = dataclasses.replace(get(source_ids()["ted_eu"]), ingestion_permitted=True)
    return RunContext(
        source=source,
        run=_ingest_run(),
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        **kwargs,
    )


class _SequenceTransport:
    """A transport that returns queued responses per URL — no real network."""

    def __init__(self, responses: dict[str, list[tuple[int, bytes, str]]]) -> None:
        self._responses = {k: list(v) for k, v in responses.items()}
        self.request_log: list[str] = []
        self.bodies: list[bytes | None] = []
        self.headers_log: list[dict[str, str]] = []

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ROBOTS_ALLOW_ALL)

    def request(
        self,
        url: str,
        *,
        user_agent: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
    ) -> FetchResult:
        self.request_log.append(url)
        self.bodies.append(body)
        self.headers_log.append(dict(headers or {}))
        status, body_, media = self._responses[url].pop(0)
        return FetchResult(url=url, status=status, body=body_, media_type=media)


def _fetcher(transport: _SequenceTransport) -> PoliteFetcher:
    return PoliteFetcher(
        connector_name="procurement", connector_version="1.0.0", transport=transport
    )


def _fixture_bytes() -> bytes:
    return _FIXTURE.read_bytes()


def _parsed(ctx: RunContext) -> dict[str, Any]:
    capture = ctx.captures.put(
        _fixture_bytes(), media_type="application/json", source_uri=_ENDPOINT
    )
    return ProcurementConnector().parse(ctx, capture)


# --- the reviewed sweep plan (data invariants) --------------------------------


def test_ted_eu_sweep_plan_is_bounded_and_documented() -> None:
    cfg = ted_eu_sweep_config()
    # The documented TED bounds: ≤250 notices/page, ≤10k field-values/page.
    assert 0 < int(cfg["page_size"]) <= 250
    assert int(cfg["page_size"]) * len(cfg["fields"]) <= 10_000
    # PAGE_NUMBER pagination only — ITERATION/scroll mode is never used.
    assert cfg["pagination_mode"] == "PAGE_NUMBER"
    assert int(cfg["max_pages_per_slice"]) == 1
    assert int(cfg["search_window_days"]) > 0
    # The reviewed slice sets: the ticket's 11 keywords + the verified CPV set.
    assert len(ted_eu_keywords()) == 11
    assert len(ted_eu_cpv_codes()) == 10
    cpv = {str(c["code"]) for c in ted_eu_cpv_codes()}
    # The dominant video-surveillance code verified on live notices.
    assert "32323500" in cpv
    # 38000000 (the whole laboratory/optical division) was reviewed and
    # rejected — not a surveillance code.
    assert "38000000" not in cpv


def test_ted_eu_targets_are_bounded_post_slices() -> None:
    import datetime as dt

    targets = ted_eu_search_targets(today=dt.date(2026, 9, 18))
    # 11 keyword slices + 10 CPV slices, one page each.
    assert len(targets) == 21
    ids = [t["id"] for t in targets]
    assert len(set(ids)) == len(ids)
    kw = [t for t in targets if t["query_kind"] == "keyword"]
    cpv = [t for t in targets if t["query_kind"] == "cpv"]
    assert len(kw) == 11 and len(cpv) == 10
    for t in targets:
        # Every slice is a POST to the documented search endpoint; the slice
        # id rides the never-transmitted #sig-slice provenance fragment.
        assert t["kind"] == "ted_eu_search"
        assert t["url"].startswith(_ENDPOINT)
        assert f"#sig-slice={t['id']}" in t["url"]
        assert t["page"] == 1 and t["limit"] <= 250
        body = t["post_body"]
        assert body["paginationMode"] == "PAGE_NUMBER"
        assert "iterationNextToken" not in body
        # The rolling window bound is IN THE QUERY — a deterministic function
        # of the injected run date, never a credential or a volatile field.
        assert "publication-date>=20260521" in body["query"]
        assert body["limit"] <= 250 and body["page"] == 1
        assert len(body["fields"]) == 22
        # No auth anywhere — the Search API is keyless.
        assert not any(
            k.lower() in ("api_key", "apikey", "key", "token", "authorization") for k in body
        )
    for t in kw:
        assert t["query"].startswith('FT~"') and "AND" in t["query"]
    for t in cpv:
        assert t["query"].startswith("classification-cpv=")


def test_ted_eu_target_queries_are_deterministic() -> None:
    import datetime as dt

    a = ted_eu_search_targets(today=dt.date(2026, 9, 18))
    b = ted_eu_search_targets(today=dt.date(2026, 9, 18))
    assert a == b
    # The window rolls with the run date — next month covers the new window.
    c = ted_eu_search_targets(today=dt.date(2026, 10, 18))
    assert a != c
    assert "publication-date>=20260620" in c[0]["post_body"]["query"]


def test_ted_eu_discover_expands_and_dedupes() -> None:
    conn = ProcurementConnector()
    supplied = {
        "id": "ted_kw:cctv:p1",  # collides with a generated slice id
        "url": f"{_ENDPOINT}#sig-slice=ted_kw:cctv:p1",
        "kind": "ted_eu_search",
        "post_body": {"query": 'FT~"CCTV"', "page": 1, "limit": 250},
    }
    ctx = _ctx(parameters={"targets": [supplied]})
    targets = conn.discover(ctx)
    assert len(targets) == 21  # supplied collides → no double-fetch
    assert targets[0] is supplied
    ctx2 = _ctx(parameters={"targets": [], "sweep_expansion": False})
    assert conn.discover(ctx2) == []


# --- the POST body rides the shared fetch seam ---------------------------------


def test_ted_eu_post_body_sent_verbatim_as_json() -> None:
    url = f"{_ENDPOINT}#sig-slice=ted_kw:cctv:p1"
    post_body = {"query": 'FT~"CCTV"', "fields": ["publication-number"], "page": 1}
    transport = _SequenceTransport({url: [(200, _fixture_bytes(), "application/json")]})
    ctx = _ctx(
        fetcher=_fetcher(transport),
        parameters={
            "targets": [
                {
                    "url": url,
                    "id": "ted_kw:cctv:p1",
                    "kind": "ted_eu_search",
                    "post_body": post_body,
                }
            ],
            "sweep_expansion": False,
        },
    )
    report = pipeline.run(ProcurementConnector(), ctx)
    assert report.asserted
    assert transport.bodies == [json.dumps(post_body, sort_keys=True).encode("utf-8")]
    assert transport.headers_log[0]["Content-Type"] == "application/json"
    assert "Authorization" not in transport.headers_log[0]


# --- fixture parse / extract / normalize ---------------------------------------


def test_ted_eu_fixture_parses_real_response_shape() -> None:
    ctx = _ctx()
    parsed = _parsed(ctx)
    assert parsed["kind"] == "ted_eu_search"
    payload = parsed["payload"]
    assert len(payload["notices"]) == 2
    assert payload["totalNoticeCount"] == 1120
    assert payload["timedOut"] is False


def test_ted_eu_extract_emits_notice_records_and_slice_outcome() -> None:
    ctx = _ctx(
        parameters={
            "targets": [
                {
                    "id": "ted_kw:surveillance_camera:p1",
                    "url": f"{_ENDPOINT}#sig-slice=ted_kw:surveillance_camera:p1",
                    "kind": "ted_eu_search",
                    "query_kind": "keyword",
                    "ted_keyword": "surveillance_camera",
                    "slice": "ted_kw:surveillance_camera:p1",
                    "page": 1,
                    "limit": 250,
                    "query": 'FT~"surveillance camera" AND publication-date>=20260521',
                    "plan_version": "2026.09.18.1",
                }
            ]
        }
    )
    capture = ctx.captures.put(
        _fixture_bytes(),
        media_type="application/json",
        source_uri=f"{_ENDPOINT}#sig-slice=ted_kw:surveillance_camera:p1",
    )
    parsed = ProcurementConnector().parse(ctx, capture)
    records = ProcurementConnector().extract(ctx, parsed)
    notices = [r for r in records if r["record_kind"] == "procurement_notice"]
    slices = [r for r in records if r["record_kind"] == "ted_eu_slice"]
    assert len(notices) == 2
    assert len(slices) == 1
    sl = slices[0]
    assert sl["outcome"] == "hits"
    assert sl["items_count"] == 2
    assert sl["total_notice_count"] == 1120
    # 1120 matches > the one bounded page — the bound is recorded honestly.
    assert sl["truncated"] is True
    assert sl["provenance"]["ted_keyword"] == "surveillance_camera"
    assert sl["provenance"]["query_kind"] == "keyword"
    for rec in notices:
        assert rec["notice_provenance"]["api"] == "ted_eu"
        assert rec["row_index"] in (0, 1)


def test_ted_eu_generated_slice_provenance_resolves_after_discover() -> None:
    # A capture for a GENERATED sweep slice (not a parameters target) must
    # still recover its provenance — discover() registers generated targets
    # on ctx.resolved_targets so extract's source_uri lookup finds them.
    conn = ProcurementConnector()
    ctx = _ctx(parameters={"targets": []})
    generated = conn.discover(ctx)
    assert len(generated) == 21
    cpv_target = next(t for t in generated if t["query_kind"] == "cpv")
    capture = ctx.captures.put(
        _fixture_bytes(),
        media_type="application/json",
        source_uri=str(cpv_target["url"]),
    )
    parsed = conn.parse(ctx, capture)
    records = conn.extract(ctx, parsed)
    sl = next(r for r in records if r["record_kind"] == "ted_eu_slice")
    assert sl["provenance"]["query_kind"] == "cpv"
    assert sl["provenance"]["cpv_code"] == cpv_target["cpv_code"]
    assert sl["provenance"]["query"] == cpv_target["query"]
    # Claims on the notice records carry the same slice provenance.
    notice = next(r for r in records if r["record_kind"] == "procurement_notice")
    assert notice["notice_provenance"]["cpv_code"] == cpv_target["cpv_code"]
    # Never the literal string "None".
    assert all(v != "None" for v in sl["provenance"].values() if isinstance(v, str))


def _normalized(ctx: RunContext) -> list[dict[str, Any]]:
    parsed = _parsed(ctx)
    records = ProcurementConnector().extract(ctx, parsed)
    return ProcurementConnector().normalize(ctx, records)


def test_ted_eu_normalize_typed_claims_verbatim() -> None:
    ctx = _ctx()
    claims = _normalized(ctx)

    notice = next(r for r in claims if r.get("record_kind") == "procurement_notice")
    assert notice["subject_id"] == "procurement_notice:ted_eu:351100-2025"
    assert notice["external_id"] == "351100-2025"
    assert notice["notice_type"] == "can-standard"
    assert notice["raw"]["publication-number"] == "351100-2025"

    by_pred: dict[str, list[dict[str, Any]]] = {}
    for c in claims:
        if c.get("record_kind") == "claim":
            by_pred.setdefault(str(c["predicate_id"]), []).append(c)

    # external_id / buyer — verbatim literals.
    ext = by_pred["external_id"][0]
    assert ext["raw_value"] == "351100-2025"
    buyer = by_pred["buyer"][0]
    assert "Straży Granicznej" in buyer["raw_value"]
    assert buyer["candidate_identifier"]["scheme"] == "procurement.org_name"

    # notice_type + title — verbatim literals only when the source states them.
    nts = {c["subject_id"]: c["raw_value"] for c in by_pred["notice_type"]}
    assert nts["procurement_notice:ted_eu:351100-2025"] == "can-standard"
    assert nts["procurement_notice:ted_eu:353033-2025"] == "cn-standard"
    titles = {c["subject_id"]: c["raw_value"] for c in by_pred["title"]}
    assert "Dostawa" in titles["procurement_notice:ted_eu:351100-2025"]

    # seller — the verbatim winner-name literal, only on the award notice.
    sellers = {c["subject_id"]: c for c in by_pred["seller"]}
    seller = sellers["procurement_notice:ted_eu:351100-2025"]
    assert seller["raw_value"]
    assert seller["candidate_identifier"]["scheme"] == "procurement.org_name"
    assert "procurement_notice:ted_eu:353033-2025" not in sellers

    # products — verbatim classification-cpv codes, deduped.
    cpv_claims = by_pred["products"]
    cpv_codes = {(c["subject_id"], c["raw_value"]) for c in cpv_claims}
    assert ("procurement_notice:ted_eu:351100-2025", "32323500") in cpv_codes

    # country: verbatim alpha-3 raw_value + reviewed alpha-2 identifier.
    country = by_pred["country"][0]
    assert country["raw_value"] == "POL" and country["value"] == "PL"
    assert country["candidate_identifier"] == {"scheme": "iso.3166_1_alpha2", "value": "PL"}

    # value where stated (notice 0: 1 248 710.76 PLN).
    amount = by_pred["amount"][0]
    assert "1248710.76" in amount["raw_value"] and "PLN" in amount["raw_value"]

    # description + posted_date verbatim.
    assert by_pred["description"][0]["raw_value"].startswith("Przedmiotem")
    assert by_pred["posted_date"][0]["value"] == "2025-06-02"
    assert by_pred["posted_date"][0]["raw_value"].startswith("2025-06-02")

    # place_of_performance: verbatim NUTS codes + city — never an iso.3166_2 id.
    pops = by_pred["place_of_performance"]
    literals = {p["raw_value"] for p in pops}
    assert "PL822" in literals and "Przemyśl" in literals and "POL" in literals
    assert all("candidate_identifier" not in p for p in pops)

    # matched_keyword: the verbatim literal slice, term id as value.
    mks = by_pred["matched_keyword"]
    terms = {(m["value"], m["raw_value"]) for m in mks}
    assert any(t == "surveillance_camera" for t, _ in terms)
    for m in mks:
        assert m["raw_value"]  # verbatim literal, never the query
        ev = m["evidence"]
        assert ev["field"].startswith(("notice-title", "description-proc"))
        assert ev["locator"]["kind"] == "byte_range"
        assert ev["record_row"] in (0, 1)
        assert ev["capture_digest"]

    # lifecycle: can-standard → awarded, cn-standard → rfp_issued.
    lifecycles = {c["subject_id"]: c["value"]["state"] for c in by_pred["lifecycle_transition"]}
    assert lifecycles["procurement_notice:ted_eu:351100-2025"] == "awarded"
    assert lifecycles["procurement_notice:ted_eu:353033-2025"] == "rfp_issued"


def test_ted_eu_matched_keyword_is_verbatim_literal_not_query() -> None:
    # A term the notice does NOT contain verbatim emits no fact claim — the
    # query that found the page is provenance, never an asserted literal.
    ctx = _ctx()
    claims = _normalized(ctx)
    matched = [
        c
        for c in claims
        if c.get("record_kind") == "claim" and c["predicate_id"] == "matched_keyword"
    ]
    # "acoustic_gunshot" appears nowhere in the fixture notices.
    assert not any(c["value"] == "acoustic_gunshot" for c in matched)
    # Every emitted literal is a verbatim slice of the fixture's own text.
    raw_text = _FIXTURE.read_text(encoding="utf-8")
    for c in claims:
        if c.get("predicate_id") == "matched_keyword" and c.get("raw_value"):
            assert c["raw_value"] in raw_text


def test_ted_eu_procured_never_deployed() -> None:
    ctx = _ctx()
    claims = _normalized(ctx)
    forbidden = {
        "deployment_exists",
        "device_count",
        "camera_count",
        "configuration_state",
        "records_request",
        "response_status",
        "parsed_document_claim",
    }
    for c in claims:
        assert c.get("predicate_id") not in forbidden
    with pytest.raises(PredicateNotAllowed):
        assert_predicate_allowed("deployment_exists")


def test_ted_eu_unmapped_country_keeps_verbatim_no_fabricated_identifier() -> None:
    ctx = _ctx()
    parsed = _parsed(ctx)
    notice = dict(parsed["payload"]["notices"][0])
    notice["buyer-country"] = ["XYZ"]  # an alpha-3 outside the reviewed map
    notice["organisation-country-buyer"] = ["XYZ"]
    raw = {
        "record_kind": "procurement_notice",
        "raw": notice,
        "notice_provenance": {"api": "ted_eu"},
        "row_index": 0,
    }
    rows = ProcurementConnector().normalize(ctx, [raw])
    country = next(r for r in rows if r.get("predicate_id") == "country")
    assert country["raw_value"] == "XYZ"
    # An unmapped alpha-3 keeps the verbatim literal and emits NO normalized
    # identifier — a code is never fabricated.
    assert "candidate_identifier" not in country


def test_ted_eu_i18n_without_english_uses_notice_language() -> None:
    ctx = _ctx()
    raw = {
        "record_kind": "procurement_notice",
        "raw": {
            "publication-number": "1-2026",
            "buyer-name": {"deu": ["Stadt Leipzig"]},
            "buyer-country": ["DEU"],
            "notice-title": {"deu": "Videoüberwachung Lieferung"},
        },
        "notice_provenance": {"api": "ted_eu"},
        "row_index": 0,
    }
    rows = ProcurementConnector().normalize(ctx, [raw])
    buyer = next(r for r in rows if r.get("predicate_id") == "buyer")
    assert buyer["raw_value"] == "Stadt Leipzig"
    country = next(r for r in rows if r.get("predicate_id") == "country")
    assert country["value"] == "DE"


# --- fail-closed drift + timed-out pages ----------------------------------------


def _capture(ctx: RunContext, data: bytes) -> Any:
    return ctx.captures.put(data, media_type="application/json", source_uri=_ENDPOINT)


def test_ted_eu_error_envelope_is_content_drift() -> None:
    ctx = _ctx()
    envelope = json.dumps(
        {
            "message": "Unknown search field 'bogus' found in expert query",
            "error": {"type": "QUERY_UNKNOWN_FIELD"},
        }
    ).encode()
    with pytest.raises(ContentDrift):
        ProcurementConnector().parse(ctx, _capture(ctx, envelope))


def test_ted_eu_missing_notices_list_is_content_drift() -> None:
    ctx = _ctx()
    with pytest.raises(ContentDrift):
        ProcurementConnector().parse(ctx, _capture(ctx, b'{"totalNoticeCount": 3}'))
    with pytest.raises(ContentDrift):
        ProcurementConnector().parse(ctx, _capture(ctx, b'{"notices": {"a": 1}}'))
    with pytest.raises(ContentDrift):
        ProcurementConnector().parse(ctx, _capture(ctx, b'{"notices": [1, 2, 3]}'))
    with pytest.raises(ContentDrift):
        ProcurementConnector().parse(ctx, _capture(ctx, b"[1, 2, 3]"))
    with pytest.raises(ContentDrift):
        ProcurementConnector().parse(ctx, _capture(ctx, b"<html>oops</html>"))


def test_ted_eu_timed_out_page_records_outcome_without_claims() -> None:
    ctx = _ctx()
    payload = json.loads(_fixture_bytes())
    payload["timedOut"] = True
    capture = ctx.captures.put(
        json.dumps(payload).encode(), media_type="application/json", source_uri=_ENDPOINT
    )
    parsed = ProcurementConnector().parse(ctx, capture)
    records = ProcurementConnector().extract(ctx, parsed)
    assert not any(r["record_kind"] == "procurement_notice" for r in records)
    sl = next(r for r in records if r["record_kind"] == "ted_eu_slice")
    assert sl["outcome"] == "timed_out" and sl["timed_out"] is True


def test_ted_eu_empty_page_is_honest_empty() -> None:
    ctx = _ctx()
    empty = {"notices": [], "totalNoticeCount": 0, "iterationNextToken": None, "timedOut": False}
    capture = ctx.captures.put(
        json.dumps(empty).encode(), media_type="application/json", source_uri=_ENDPOINT
    )
    records = ProcurementConnector().extract(ctx, ProcurementConnector().parse(ctx, capture))
    sl = next(r for r in records if r["record_kind"] == "ted_eu_slice")
    assert sl["outcome"] == "empty" and sl["items_count"] == 0


# --- rate-limit / refusal honesty ------------------------------------------------


def test_ted_eu_persistent_429_is_disappearance_never_reprobed() -> None:
    url = f"{_ENDPOINT}#sig-slice=ted_kw:cctv:p1"
    transport = _SequenceTransport({url: [(429, b'{"error":"rate limited"}', "application/json")]})
    ctx = _ctx(
        fetcher=_fetcher(transport),
        parameters={
            "targets": [
                {"url": url, "id": "ted_kw:cctv:p1", "kind": "ted_eu_search", "post_body": {}}
            ],
            "sweep_expansion": False,
        },
    )
    report = pipeline.run(ProcurementConnector(), ctx)
    # One attempt, one recorded disappearance — a refused slice is an outcome,
    # never silently retried outside the transport's recorded backoff.
    assert transport.request_log == [url]
    assert len(report.disappearances) == 1
    assert not any(c.get("record_kind") == "procurement_notice" for c in report.claims)


# --- reproducibility -------------------------------------------------------------


def test_ted_eu_replay_is_deterministic() -> None:
    ctx = _ctx()
    first = _normalized(ctx)
    second = _normalized(_ctx())
    assert first == second


def test_ted_eu_shadow_diff_is_zero() -> None:
    ctx = _ctx(shadow=True)
    claims_shadow = _normalized(ctx)
    claims_replay = _normalized(_ctx(replay=True))
    assert claims_shadow == claims_replay


def test_ted_eu_end_to_end_pipeline_over_fixture() -> None:
    url = f"{_ENDPOINT}#sig-slice=ted_kw:surveillance_camera:p1"
    transport = _SequenceTransport({url: [(200, _fixture_bytes(), "application/json")]})
    ctx = _ctx(
        fetcher=_fetcher(transport),
        parameters={
            "targets": [
                {
                    "url": url,
                    "id": "ted_kw:surveillance_camera:p1",
                    "kind": "ted_eu_search",
                    "record_kind": "ted_eu_slice",
                    "query_kind": "keyword",
                    "ted_keyword": "surveillance_camera",
                    "slice": "ted_kw:surveillance_camera:p1",
                    "page": 1,
                    "limit": 250,
                    "query": 'FT~"surveillance camera" AND publication-date>=20260521',
                    "plan_version": "2026.09.18.1",
                    "post_body": {"query": 'FT~"surveillance camera"', "page": 1, "limit": 250},
                }
            ],
            "sweep_expansion": False,
        },
    )
    report = pipeline.run(ProcurementConnector(), ctx)
    assert report.asserted
    assert not report.disappearances
    kinds = {c.get("record_kind") for c in report.claims}
    assert "procurement_notice" in kinds and "ted_eu_slice" in kinds
    notices = [c for c in report.claims if c.get("record_kind") == "procurement_notice"]
    assert {n["external_id"] for n in notices} == {"351100-2025", "353033-2025"}


# --- registry / gate / credentials ----------------------------------------------


def test_ted_eu_registered_loadable_cc_by() -> None:
    src = get("ted_eu")
    assert src.id == "ted_eu"
    # GL-GATE-06 flip — the SIMAP legal notice resolves verbatim (packet
    # docs/build/reports/rights/ted_eu.md): notices freely reusable under
    # Commission Decision 2011/833/EU, editorial CC-BY-4.0, metadata CC0-1.0.
    assert src.ingestion_permitted is True
    assert src.rights.spdx == "CC-BY-4.0"
    assert src.rights.redistributable is True and src.rights.derivative_permitted is True


def test_ted_eu_needs_no_credential() -> None:
    # The Search API is keyless — no env var, no key field, anywhere in the
    # committed sweep configuration (verified live 2026-09-18).
    cfg_blob = json.dumps(ted_eu_sweep_config(), sort_keys=True)
    for needle in ("api_key", "apiKey", "SIG_TED", "Authorization", "Bearer"):
        assert needle not in cfg_blob
    live = Path("connectors/src/connectors/data/live_targets.toml").read_text()
    assert "ted_eu" in live and "SIG_TED" not in live
    assert ted_eu_country_map()["POL"] == "PL" and ted_eu_country_map()["DEU"] == "DE"
