# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The three OKC document connectors (LIVE.1a, GL-LIVE-01, P23.5).

Pins the deliverables: `okc_procurement` / `okcpd_policy` / `ok_statute` are registered
and wired to their green registry sources (RIGHTS.1 / HG-03); each fetches → captures →
parses via sig-parsing → emits the fixture-encoded claims, and a shadow replay over the
committed fixture is byte-identical (0 diffs, SIG-INGEST-019). Part VIII §0.7 is honored
on every parsed claim: no plate/trip/per-person data (`assert_part_viii_safe`), the
officer-naming gate (`assert_person_naming_permitted`), and the sensitivity tier travel
with the claim — each guarded by a test that fails if the guard is removed.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from connectors.net import FetchResult, PoliteFetcher, RobotsResult
from connectors.pipeline import run
from connectors.registry import get
from connectors.replay import shadow_replay
from connectors.runner import CONNECTOR_FOR_SOURCE, RunMode, is_review_status_green, run_source
from connectors.stages import (
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
    registered_connectors,
)
from evidence.ingest_run import IngestRun
from parsing.genre import DocumentGenre
from policy.officer import OfficerNamingProngs, ReviewerConcurrence
from policy.publication import excluded_kinds

from connectors import okc_documents as okc

_FIX = Path(__file__).parent / "fixtures" / "okc"
_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"

# The three connectors, keyed by name = registry source id (they coincide here).
_CONNECTORS = ("okc_procurement", "okcpd_policy", "ok_statute")


class _StaticTransport:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ROBOTS_ALLOW_ALL)

    def request(self, url: str, *, user_agent: str, headers: Any | None = None) -> FetchResult:
        return FetchResult(
            url=url,
            status=200,
            body=self._body,
            media_type="application/json",
            retrieved_at=datetime(2026, 8, 20, tzinfo=UTC),
        )


def _ctx(name: str) -> RunContext:
    transport = _StaticTransport((_FIX / f"{name}.json").read_bytes())
    fetcher = PoliteFetcher(connector_name=name, connector_version="1.0.0", transport=transport)
    source = dataclasses.replace(get(name), ingestion_permitted=True)
    return RunContext(
        source=source,
        run=IngestRun(name, "1.0.0", "deadbeef", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": [{"id": "t1", "url": f"https://{name}/x", "kind": "doc"}]},
    )


def _run(name: str) -> list[dict[str, Any]]:
    connector = registered_connectors()[name]()
    return run(connector, _ctx(name)).claims


# --- registration + wiring ----------------------------------------------------


@pytest.mark.parametrize("name", _CONNECTORS)
def test_connector_is_registered(name: str) -> None:
    assert name in registered_connectors()


@pytest.mark.parametrize("name", _CONNECTORS)
def test_source_is_wired_to_its_connector(name: str) -> None:
    assert CONNECTOR_FOR_SOURCE[name] == name


@pytest.mark.parametrize("name", _CONNECTORS)
def test_source_is_green_hg03_satisfied(name: str) -> None:
    # RIGHTS.1 (P21.1 re-run, GL-GATE-03) flipped these three to ingestion_permitted;
    # a live fetch is now permitted (the fetch itself is P21.3 + HG-09, deferred).
    assert is_review_status_green(name), f"{name} must be green for the LIVE.1a code half"


# --- claims are typed, evidenced, and match the fixture-encoded facts ---------


@pytest.mark.parametrize("name", _CONNECTORS)
def test_emits_typed_evidenced_claims(name: str) -> None:
    claims = _run(name)
    assert claims
    allowlist = okc.predicate_allowlist(name)
    for c in claims:
        assert c["predicate_id"] in allowlist  # typed + allowlisted (SIG-INGEST-033)
        assert c["raw_value"] is not None  # P2 preserved
        assert c["connector"] == name
        ev = c["evidence"]
        assert ev["source_url"] and ev["retrieved_date"]  # evidenced + dated
        assert ev["locator"] and ev["extraction_method"]  # locator mandatory (SIG-PARSE-003)


def test_parser_layers_are_exercised() -> None:
    methods = {c["evidence"]["extraction_method"] for n in _CONNECTORS for c in _run(n)}
    assert "pdf_table" in methods  # layer-4 table extraction (parsing.tables) — procurement
    assert "pdf_text" in methods  # layer-3 clause locator (parsing.clauses) — policy/statute


def test_procurement_emits_the_fixture_encoded_contract_facts() -> None:
    by_pred = {c["predicate_id"]: c for c in _run("okc_procurement")}
    assert by_pred["contract_number"]["value"] == "C241032"
    assert by_pred["contract_amount"]["value"] == 270000.0
    assert by_pred["contract_amount"]["raw_value"] == "$270,000"  # P2 verbatim
    assert by_pred["quantity"]["value"] == 90
    assert by_pred["vendor_name"]["value"] == "Flock Safety"


def test_policy_emits_the_fixture_encoded_sharing_restriction() -> None:
    values = {c["predicate_id"]: c["value"] for c in _run("okcpd_policy")}
    assert "law enforcement information database" in values["sharing_restriction"]


def test_statute_emits_the_fixture_encoded_citation_and_restriction() -> None:
    values = {c["predicate_id"]: c["value"] for c in _run("ok_statute")}
    assert "7-606.1" in values["statutory_citation"]
    assert values["use_restriction"] == "limited to insurance enforcement"


# --- shadow replay is byte-identical (0 diffs, SIG-INGEST-019) ----------------


@pytest.mark.parametrize("name", _CONNECTORS)
def test_shadow_replay_over_fixture_has_zero_diffs(name: str) -> None:
    connector = registered_connectors()[name]()
    ctx = _ctx(name)
    report = run(connector, ctx)
    diff = shadow_replay(registered_connectors()[name](), ctx, report.captures, report.claims)
    assert diff.changed_count == 0


@pytest.mark.parametrize("name", _CONNECTORS)
def test_run_source_shadow_and_replay(name: str) -> None:
    fixture = _FIX / f"{name}.json"
    shadow = run_source(name, mode=RunMode.SHADOW, fixture=fixture, kind="doc")
    replay = run_source(name, mode=RunMode.REPLAY, fixture=fixture, kind="doc")
    assert shadow.diff is not None and shadow.diff.changed_count == 0
    assert replay.replay_reproducible is True


# --- Part VIII §0.7: no plate/trip/per-person data (test fails if removed) -----


@pytest.mark.parametrize(
    "bad",
    [
        "per_person_location",
        "license_plate_number",
        "per_trip_route",
        "travel_history",
        "per_search_hit",
    ],
)
def test_part_viii_guard_refuses_forbidden_predicate(bad: str) -> None:
    with pytest.raises(okc.PartVIIIViolation):
        okc.assert_part_viii_safe(bad, "some value")


def test_part_viii_guard_refuses_forbidden_raw_value() -> None:
    # The token can hide in the VALUE, not just the predicate name — scanned too.
    with pytest.raises(okc.PartVIIIViolation):
        okc.assert_part_viii_safe("use_restriction", "records the license plate of each vehicle")


def test_part_viii_guard_refuses_categorically_excluded_kind() -> None:
    # Any policy/data/exclusions.toml kind is refused at the ingest boundary (§43.2).
    for kind in excluded_kinds():
        with pytest.raises(okc.PartVIIIViolation):
            okc.assert_part_viii_safe(kind, "x")


def test_okc_claim_routes_through_the_part_viii_guard() -> None:
    # A claim whose raw value carries a plate token is refused by okc_claim itself —
    # if the guard call is removed from okc_claim, this test fails.
    ctx = okc.DocumentContext(
        connector="okcpd_policy",
        source_id="okcpd_policy",
        source_url="https://example/x",
        retrieved_date="2026-09-01",
        genre=DocumentGenre.POLICY_DOCUMENT,
        subject_id="sig:deployment:okc-okcpd-flock",
    )
    with pytest.raises(okc.PartVIIIViolation):
        okc.okc_claim(
            ctx,
            predicate="use_restriction",
            value="stores the license plate of every passing car",
            raw_value="stores the license plate of every passing car",
            extraction_method="pdf_text",
            locator={"kind": "byte_range", "start": 0, "end": 1},
        )


def test_no_emitted_claim_carries_a_forbidden_token() -> None:
    # End-to-end: the real fixtures emit institutional facts only.
    tokens = okc.forbidden_tokens()
    for name in _CONNECTORS:
        for c in _run(name):
            hay = f"{c['predicate_id']} {c['raw_value']}".lower()
            assert not any(t in hay for t in tokens)


# --- Part VIII §43.4: the officer-naming gate (test fails if removed) ---------


def test_person_naming_predicate_is_refused_by_default() -> None:
    # A person-named claim with no prongs + no reviewers defaults to no-publish.
    with pytest.raises(okc.OfficerNamingRefused):
        okc.assert_person_naming_permitted("officer_name")


def test_person_naming_permitted_only_with_all_prongs_and_two_reviewers() -> None:
    prongs = OfficerNamingProngs(True, True, True, True, True)
    reviewers = (
        ReviewerConcurrence("rev-a", True, "official conduct on the face of an R1 record"),
        ReviewerConcurrence("rev-b", True, "public in-jurisdiction; claim fails without the name"),
    )
    # All prongs + two independent written concurrences → the gate permits it.
    okc.assert_person_naming_permitted("officer_name", prongs=prongs, reviewers=reviewers)
    # One reviewer is not enough (SIG-PUB-008).
    with pytest.raises(okc.OfficerNamingRefused):
        okc.assert_person_naming_permitted("officer_name", prongs=prongs, reviewers=reviewers[:1])


def test_non_person_predicate_bypasses_the_officer_gate() -> None:
    # A non-person-naming predicate is unaffected by the officer test.
    okc.assert_person_naming_permitted("contract_amount")


# --- Part VIII §43.3: the sensitivity tier travels with the claim -------------


@pytest.mark.parametrize("name", _CONNECTORS)
def test_every_claim_carries_a_sensitivity_tier(name: str) -> None:
    # If the sensitivity stamp is removed from okc_claim, this test fails.
    for c in _run(name):
        assert c["sensitivity_class"] == okc.default_sensitivity_class().value
        assert c["geo_tier"] == 0  # C1 institutional/public-record facts, no coordinate


# --- the predicate allowlist as a hard schema gate (SIG-INGEST-033) -----------


def test_predicate_allowlist_is_enforced() -> None:
    with pytest.raises(okc.PredicateNotAllowed):
        okc.assert_predicate_allowed("okc_procurement", "deployed")


def test_each_connector_has_a_disjoint_source_and_allowlist() -> None:
    for name in _CONNECTORS:
        cfg = okc.connector_config(name)
        assert cfg["source_id"] == name
        assert okc.predicate_allowlist(name)


# --- genre is re-derived from the text, never trusted from a label ------------


def test_mislabelled_genre_is_rejected() -> None:
    doc = {
        "connector": "okc_procurement",
        "documents": [
            {
                "id": "mislabelled",
                "genre": "policy_document",  # a policy label on a procurement connector
                "kind": "procurement_table",
                "source_url": "https://example/x",
                "subject_id": "contract:x",
                "text": "Vendor | Amount\nFlock | $1",
                "columns": {"Vendor": {"predicate": "vendor_name"}},
            }
        ],
    }
    with pytest.raises(ValueError):
        okc.extract_documents("okc_procurement", doc)


# --- the fixtures cite their public sources -----------------------------------


def test_fixtures_have_a_sources_md() -> None:
    assert (_FIX / "SOURCES.md").exists()
    text = (_FIX / "SOURCES.md").read_text()
    for name in _CONNECTORS:
        assert f"{name}.json" in text


# --- the live document path (P25.8 / D-LIVE.1a-1) ------------------------------
#
# A configured live target may carry a reviewed clause map; a real captured page
# (not the fixture envelope) is sliced at its § marker into the same document
# shape, so the clause layer emits real typed claims. An absent marker is a
# recorded ContentDrift — never a claim asserted beyond the capture (§3.1).

_STATUTE_PAGE = (
    "<html><body><div>"
    "7-606.1 - Uninsured Vehicle Enforcement Program - Implementation - "
    "Automatic License Plate Reader System - Restrictions - Annual Report "
    "This Statute Will Go Into Effect Effective On: 01/01/2027 "
    "Cite as: 47 O.S. § 7-606.1 (OSCN 2026) "
    "A. There is hereby created the Uninsured Vehicle Enforcement Program. "
    "B. The Uninsured Vehicle Enforcement Program shall be implemented and "
    "administered by the district attorneys of the State of Oklahoma "
    "within their respective districts or at the District Attorneys Council. "
    "To implement this program, the use of technology and software to aid in "
    "detection of offenses involving uninsured motorists is necessary and "
    "district attorneys and participating law enforcement agencies shall have "
    "the authority to enter into contractual agreements with automated license "
    "plate reader providers to provide necessary technology, equipment, and "
    "maintenance thereof. "
    "C. 1. Participating law enforcement agencies may use automatic license "
    "plate reader systems to access and collect data for the investigation, "
    "detection, analysis, or enforcement of Oklahoma's Compulsory Insurance "
    "Law."
    "</div></body></html>"
)

_STATUTE_TARGET = {
    "id": "ok-statute-47-7-606-1",
    "url": "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=478582",
    "kind": "document_page",
    "doc_id": "okc-statute-47-7-606-1",
    "subject_id": "sig:deployment:okc-okcpd-flock",
    "section": "7-606.1",
    "clauses": [
        {
            "clause": "7-606.1",
            "predicate": "statutory_citation",
            "value": "47 O.S. § 7-606.1",
            "literal": "§ 7-606.1 (OSCN 2026)",
            "value_kind": "text",
        },
        {
            "clause": "7-606.1",
            "predicate": "use_restriction",
            "value": "limited to insurance enforcement",
            "literal": "enforcement of Oklahoma's Compulsory Insurance Law",
            "value_kind": "text",
        },
    ],
}


class _PageTransport(_StaticTransport):
    """A transport that serves a real web page (text/html), not the envelope."""

    def request(self, url: str, *, user_agent: str, headers: Any | None = None) -> FetchResult:
        result = super().request(url, user_agent=user_agent, headers=headers)
        return dataclasses.replace(result, media_type="text/html")


def _live_ctx(body: bytes, target: dict[str, Any]) -> RunContext:
    name = "ok_statute"
    transport = _PageTransport(body)
    fetcher = PoliteFetcher(connector_name=name, connector_version="1.0.0", transport=transport)
    source = dataclasses.replace(get(name), ingestion_permitted=True)
    return RunContext(
        source=source,
        run=IngestRun(name, "1.0.0", "deadbeef", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": [target]},
    )


def test_live_page_yields_typed_statute_claims() -> None:
    connector = registered_connectors()["ok_statute"]()
    claims = run(connector, _live_ctx(_STATUTE_PAGE.encode(), _STATUTE_TARGET)).claims
    by_pred = {c["predicate_id"]: c for c in claims}
    assert "7-606.1" in by_pred["statutory_citation"]["value"]
    assert by_pred["use_restriction"]["value"] == "limited to insurance enforcement"
    for c in claims:
        assert c["evidence"]["locator"]
        assert c["evidence"]["source_url"].endswith("CiteID=478582")


def test_live_page_latin1_section_marker() -> None:
    # OSCN serves Latin-1: the § byte (0xA7) must survive the decode or the
    # clause layer cannot locate the section marker.
    connector = registered_connectors()["ok_statute"]()
    claims = run(connector, _live_ctx(_STATUTE_PAGE.encode("cp1252"), _STATUTE_TARGET)).claims
    assert {c["predicate_id"] for c in claims} == {
        "statutory_citation",
        "use_restriction",
    }


def test_live_page_missing_section_is_content_drift() -> None:
    from connectors.stages import ContentDrift

    connector = registered_connectors()["ok_statute"]()
    drifted = _STATUTE_PAGE.replace("§ 7-606.1", "§ 9-999").encode()
    with pytest.raises(ContentDrift):
        run(connector, _live_ctx(drifted, _STATUTE_TARGET))


def test_live_page_absent_literal_is_content_drift() -> None:
    # The reviewed literal MUST appear in the captured section — a fact whose
    # literal is absent is recorded drift, never a claim beyond the capture.
    from connectors.stages import ContentDrift

    connector = registered_connectors()["ok_statute"]()
    target = {
        **_STATUTE_TARGET,
        "clauses": [
            {
                "clause": "7-606.1",
                "predicate": "use_restriction",
                "value": "x",
                "literal": "a sentence that is not in the captured page",
                "value_kind": "text",
            }
        ],
    }
    with pytest.raises(ContentDrift):
        run(connector, _live_ctx(_STATUTE_PAGE.encode(), target))


def test_live_claim_keeps_verbatim_literal_as_raw_value() -> None:
    # P2: the typed interpretation sits in `value`; the verbatim source literal
    # is the claim's raw_value.
    connector = registered_connectors()["ok_statute"]()
    claims = run(connector, _live_ctx(_STATUTE_PAGE.encode(), _STATUTE_TARGET)).claims
    by_pred = {c["predicate_id"]: c for c in claims}
    cite = by_pred["statutory_citation"]
    assert cite["value"] == "47 O.S. § 7-606.1"  # reviewed interpretation
    assert cite["raw_value"] == "§ 7-606.1 (OSCN 2026)"  # verbatim source literal


def _make_pdf(lines: list[str]) -> bytes:
    """A minimal single-page PDF with a real text layer (xref-correct)."""
    import io

    objs = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>endobj",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R"
        b"/Resources<</Font<</F1 5 0 R>>>>>>endobj",
    ]
    ops = " ".join(f"({line}) Tj T*" for line in lines)
    body = f"BT /F1 12 Tf 72 720 Td 14 TL {ops} ET".encode()
    objs.append(f"<< /Length {len(body)} >>".encode() + b"\nstream\n" + body + b"\nendstream")
    objs.append(b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj")
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objs, 1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode())
        out.write(obj)
        if not obj.endswith(b"endobj"):
            out.write(b"endobj")
        out.write(b"\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(f"trailer<</Size {len(objs) + 1}/Root 1 0 R>>\nstartxref\n{xref}\n%%EOF".encode())
    return out.getvalue()


_POLICY_TARGET = {
    "id": "okcpd-ops-manual-5-118",
    "url": "https://www.okc.gov/files/assets/city/v/2/police/documents/operations-manual-6th-edition-june-15-2026.pdf",
    "kind": "document_page",
    "doc_id": "okc-ops-manual-5-118",
    "subject_id": "sig:deployment:okc-okcpd-flock",
    "section": "5-118",
    "clauses": [
        {
            "clause": "5-118",
            "predicate": "use_restriction",
            "value": "official law enforcement purposes only",
            "literal": "used exclusively for official law enforcement purposes",
            "value_kind": "text",
        },
    ],
}


def test_live_pdf_manual_yields_page_located_claims() -> None:
    # A real captured PDF (no § marker, bare "5-118" heading) locates the cited
    # section, verifies the reviewed literal, and emits a page-located claim.
    name = "okcpd_policy"
    pdf = _make_pdf(
        [
            "5-117 Response to Emergency Call Out",
            "All personnel respond to duty when called.",
            "5-118 Automated License Plate Readers",
            "The data captured will be used exclusively for official law enforcement purposes.",
            "5-119 Facial Comparison Program",
        ]
    )
    transport = _PageTransport(pdf)
    fetcher = PoliteFetcher(connector_name=name, connector_version="1.0.0", transport=transport)
    source = dataclasses.replace(get(name), ingestion_permitted=True)
    ctx = RunContext(
        source=source,
        run=IngestRun(name, "1.0.0", "deadbeef", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": [_POLICY_TARGET]},
    )
    claims = run(registered_connectors()[name](), ctx).claims
    assert len(claims) == 1
    claim = claims[0]
    assert claim["predicate_id"] == "use_restriction"
    assert claim["raw_value"] == "used exclusively for official law enforcement purposes"
    assert claim["evidence"]["locator"] == {"kind": "page", "page": 1}
    assert claim["evidence"]["extraction_method"] == "pdf_text"


def test_live_pdf_toc_entry_is_not_the_section() -> None:
    # A dot-leader table-of-contents line is not the section body — the slice
    # must come from the real heading, or the literal check records drift.
    from connectors.stages import ContentDrift

    pdf = _make_pdf(
        [
            "5-118 Automated License Plate Readers ............. 274",
            "5-119 Facial Comparison Program",
        ]
    )
    name = "okcpd_policy"
    transport = _PageTransport(pdf)
    fetcher = PoliteFetcher(connector_name=name, connector_version="1.0.0", transport=transport)
    source = dataclasses.replace(get(name), ingestion_permitted=True)
    ctx = RunContext(
        source=source,
        run=IngestRun(name, "1.0.0", "deadbeef", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": [_POLICY_TARGET]},
    )
    with pytest.raises(ContentDrift):
        run(registered_connectors()[name](), ctx)
