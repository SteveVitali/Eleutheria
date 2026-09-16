# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The P25.4 curated coarse-dataset adapters (§22.7, SIG-INGEST-042).

Each counsel-flipped coarse source's REAL data surface — the Carnegie index
page's embedded JS dataset array (discovered via its ``<script src>`` chunks)
and the FRWM page's linked Google Sheet (six gviz CSVs) — is parsed STRICTLY
into the connector's curated ``rows`` payload at country/vendor granularity.
A changed upstream shape is ``ContentDrift``; a per-search/per-person field is
refused by the aggregate-only gate; every emitted claim carries evidence +
timestamp + locator.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from connectors.live_targets import live_targets
from connectors.net import FetchResult, PoliteFetcher, RateLimiter, RobotsResult
from connectors.pipeline import run
from connectors.registry import CompactStatus, CustodyPosture, get
from connectors.replay import diff_claim_sets, shadow_replay
from connectors.stages import (
    ContentDrift,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun

from connectors import coarse_international as ci

_FIX = Path(__file__).parent / "fixtures" / "coarse_international" / "adapter"
_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"
_RETRIEVED = datetime(2026, 9, 16, tzinfo=UTC)

_CARNEGIE_PAGE = "https://carnegieendowment.org/features/ai-global-surveillance-technology"
_DATA_CHUNK = "https://carnegieendowment.org/_next/static/chunks/02dsg86hwl1n3.js"
_FRWM_PAGE = "https://surfshark.com/facial-recognition-map"

_FRWM_SHEETS = {
    "North America": "689675349",
    "South America": "520821635",
    "Europe": "102380128",
    "Middle East & Central Asia": "2060189382",
    "Rest of Asia and Oceania": "1320430692",
    "Africa": "0",
}
_FRWM_CSV_FIXTURES = {
    "North America": "frwm_sheet_north_america.csv",
    "South America": "frwm_sheet_south_america.csv",
    "Europe": "frwm_sheet_europe.csv",
    "Middle East & Central Asia": "frwm_sheet_me_central_asia.csv",
    "Rest of Asia and Oceania": "frwm_sheet_asia_oceania.csv",
    "Africa": "frwm_sheet_africa.csv",
}


def _sheet_url(gid: str) -> str:
    return (
        "https://docs.google.com/spreadsheets/d/"
        "157mTA67QAMxb0N4e7tO755r9uw2wsaT1z2rcCO1hPIU/gviz/tq"
        f"?tqx=out:csv&gid={gid}"
    )


class _MappedTransport:
    """Serves per-URL fixture bytes — no real network (SIG-INGEST-011)."""

    def __init__(self, bodies: dict[str, tuple[bytes, str]]) -> None:
        self._bodies = bodies

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ROBOTS_ALLOW_ALL)

    def request(
        self,
        url: str,
        *,
        user_agent: str,
        headers: Any = None,
        body: bytes | None = None,
    ) -> FetchResult:
        if url not in self._bodies:
            return FetchResult(url=url, status=404, body=b"", retrieved_at=_RETRIEVED)
        content, media_type = self._bodies[url]
        return FetchResult(
            url=url,
            status=200,
            body=content,
            media_type=media_type,
            retrieved_at=_RETRIEVED,
        )


def _ctx(source_id: str, transport: _MappedTransport, targets: list[dict[str, Any]]):
    source = dataclasses.replace(
        get(source_id),
        ingestion_permitted=True,
        custody_posture=CustodyPosture.REFERENCE,
        compact_status=CompactStatus.PUBLIC_TERMS_ONLY,
    )
    fetcher = PoliteFetcher(
        connector_name="coarse_international",
        connector_version=ci.CoarseInternationalConnector.version,
        transport=transport,
        # Fixtures are served instantly; the politeness delay is not under test.
        rate_limiter=RateLimiter(default_delay=0.0),
    )
    return RunContext(
        source=source,
        run=IngestRun("coarse_international", "1.1.0", "deadbeef", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": targets},
    )


def _carnegie_transport() -> _MappedTransport:
    bodies: dict[str, tuple[bytes, str]] = {
        _CARNEGIE_PAGE: ((_FIX / "carnegie_index.html").read_bytes(), "text/html"),
        _DATA_CHUNK: ((_FIX / "carnegie_chunk.js").read_bytes(), "application/javascript"),
    }
    # Every other chunk link resolves to a non-data asset.
    for src in _chunk_urls():
        bodies.setdefault(
            src, ((_FIX / "carnegie_chunk_lib.js").read_bytes(), "application/javascript")
        )
    return _MappedTransport(bodies)


def _chunk_urls() -> list[str]:
    from parsing.document import html_script_srcs

    return [
        s
        for s in html_script_srcs((_FIX / "carnegie_index.html").read_bytes(), _CARNEGIE_PAGE)
        if "/_next/static/chunks/" in s
    ]


def _frwm_transport() -> _MappedTransport:
    bodies: dict[str, tuple[bytes, str]] = {
        _FRWM_PAGE: ((_FIX / "frwm_page.html").read_bytes(), "text/html"),
    }
    for sheet, gid in _FRWM_SHEETS.items():
        bodies[_sheet_url(gid)] = (
            (_FIX / _FRWM_CSV_FIXTURES[sheet]).read_bytes(),
            "text/csv",
        )
    return _MappedTransport(bodies)


def _frwm_targets() -> list[dict[str, Any]]:
    return [
        {"id": "surfshark-frwm", "url": _FRWM_PAGE, "kind": "document"},
        *[
            {"id": f"frwm-sheet:{gid}", "url": _sheet_url(gid), "kind": "dataset_csv", "sheet": s}
            for s, gid in _FRWM_SHEETS.items()
        ],
    ]


# --- carnegie: the embedded-dataset page ----------------------------------------


def test_carnegie_index_page_resolves_bounded_chunk_targets() -> None:
    """The page's 28 real chunk links become bounded same-host dataset_chunk targets."""
    ctx = _ctx(
        "carnegie_ai_gsi",
        _carnegie_transport(),
        [{"id": "page", "url": _CARNEGIE_PAGE, "kind": "document"}],
    )
    connector = ci.CoarseInternationalConnector()
    report = run(connector, ctx)
    resolved = ctx.resolved_targets
    assert len(resolved) == 28  # every real chunk link, deduped
    for url, target in resolved.items():
        assert target["kind"] == "dataset_chunk"
        assert target["index_url"] == _CARNEGIE_PAGE
        assert url.startswith("https://carnegieendowment.org/_next/static/chunks/")
        assert url.endswith(".js")
    # the page itself is provenance, the chunks are the dataset surface
    assert report.captures


def test_carnegie_chunk_yields_country_claims_with_evidence() -> None:
    """The data chunk -> per-country typed claims, all evidenced + dated + located."""
    ctx = _ctx(
        "carnegie_ai_gsi",
        _carnegie_transport(),
        [{"id": "page", "url": _CARNEGIE_PAGE, "kind": "document"}],
    )
    report = run(ci.CoarseInternationalConnector(), ctx)
    claims = [c for c in report.claims if c["record_kind"] == "claim"]
    # 75 countries × (membership + 5 flags) + per-country supplier claims
    assert len(claims) > 75 * 6
    subjects = {c["subject_id"] for c in claims}
    assert "jurisdiction:iso.3166-1:DZ" in subjects
    assert "jurisdiction:iso.3166-1:US" in subjects
    assert len(subjects) == 75
    for c in claims:
        assert c["granularity"] == "country"
        assert c["subject_kind"] == "jurisdiction"
        assert c["disaggregation_prohibited"] is True
        assert c["predicate_id"] in ci.coarse_predicate_allowlist()
        # every live claim is evidenced + dated + located (P1–P3, §3.1)
        assert c["evidence"]["source_url"] == _DATA_CHUNK
        assert c["evidence"]["retrieved_date"] == "2026-09-16"
        assert c["observed_at"] == "2026-09-16"
        assert c["evidence"]["locator"]["kind"] == "byte_range"
        assert c["raw_value"]
        assert c["vocab_version"] == ci.vocab_version()
    # an evidenced negative: Algeria is NOT flagged US-supplied
    dz_us = next(
        c
        for c in claims
        if c["subject_id"] == "jurisdiction:iso.3166-1:DZ"
        and c["predicate_id"] == "ai_surveillance_tech_from_us"
    )
    assert dz_us["value"] is False
    # a supplier claim (verbatim upstream name, country-level subject)
    dz_sup = next(
        c
        for c in claims
        if c["subject_id"] == "jurisdiction:iso.3166-1:DZ"
        and c["predicate_id"] == "ai_surveillance_supplier"
    )
    assert dz_sup["value"] == "BAE"
    assert "BAE, Huawei" in dz_sup["raw_value"]
    # the dataset capture's quality report records the entry count
    qr = next(
        c
        for c in report.claims
        if c["record_kind"] == "quality_report" and c["capture_kind"] == "embedded_dataset"
    )
    assert qr["entry_count"] == 75


def test_carnegie_non_data_chunk_yields_zero_claims() -> None:
    """A JS chunk without the dataset marker is a js_asset — no claims, no artifact."""
    entries = ci.parse_embedded_dataset(
        (_FIX / "carnegie_chunk_lib.js").read_bytes(),
        source_id="carnegie_ai_gsi",
        spec=ci.adapter_spec("carnegie_ai_gsi"),
    )
    assert entries is None


def test_carnegie_chunk_drift_is_loud() -> None:
    """Marker present but a malformed entry -> ContentDrift, never silent zero."""
    with pytest.raises(ContentDrift):
        ci.parse_embedded_dataset(
            (_FIX / "carnegie_chunk_drift.js").read_bytes(),
            source_id="carnegie_ai_gsi",
            spec=ci.adapter_spec("carnegie_ai_gsi"),
        )


def test_carnegie_index_page_without_chunk_links_is_drift() -> None:
    """A page that lost its <script src> chunks fails loud in discover_more."""
    page = b"<html><head></head><body>redesigned</body></html>"
    ctx = _ctx(
        "carnegie_ai_gsi",
        _MappedTransport({_CARNEGIE_PAGE: (page, "text/html")}),
        [{"id": "page", "url": _CARNEGIE_PAGE, "kind": "document"}],
    )
    with pytest.raises(ContentDrift):
        run(ci.CoarseInternationalConnector(), ctx)


def test_carnegie_chunk_partial_extraction_is_drift() -> None:
    """Fewer than min_entries embedded entries is drift — not a small answer."""
    data = (_FIX / "carnegie_chunk.js").read_bytes()
    marker = ci.adapter_spec("carnegie_ai_gsi")["entry_marker"].encode()
    first = data.find(marker)
    snippet = data[:first] + data[first : data.find(b"},{arrayItem:", first) + 1] + b"]"
    with pytest.raises(ContentDrift):
        ci.parse_embedded_dataset(
            snippet, source_id="carnegie_ai_gsi", spec=ci.adapter_spec("carnegie_ai_gsi")
        )


# --- frwm: the linked-sheet dataset --------------------------------------------


def test_frwm_sheets_yield_194_country_status_claims() -> None:
    """The six gviz CSVs -> 194 typed status claims; the page stays an artifact."""
    ctx = _ctx("facial_recognition_world_map", _frwm_transport(), _frwm_targets())
    report = run(ci.CoarseInternationalConnector(), ctx)
    claims = [c for c in report.claims if c["record_kind"] == "claim"]
    assert len(claims) == 194
    kinds = {c["record_kind"] for c in report.claims}
    assert "evidence_artifact" in kinds  # the page remains provenance
    for c in claims:
        assert c["predicate_id"] == "facial_recognition_status"
        assert c["subject_kind"] == "jurisdiction"
        assert c["granularity"] == "country"
        assert c["value"] in {
            "in_use",
            "approved_not_implemented",
            "considering",
            "banned",
            "no_evidence",
            "monitored_by_israel",
        }
        assert c["evidence"]["retrieved_date"] == "2026-09-16"
        assert c["observed_at"] == "2026-09-16"
        assert c["evidence"]["locator"]["kind"] == "cell"
        assert c["evidence"]["locator"]["sheet"] in _FRWM_SHEETS
        assert c["raw_value"]
    # the upstream Egypt contradiction is kept, not reconciled (P3)
    egypt = [c for c in claims if c["subject_id"] == "jurisdiction:iso.3166-1:EG"]
    assert {c["value"] for c in egypt} == {"in_use", "considering"}
    assert {c["evidence"]["locator"]["sheet"] for c in egypt} == {
        "Middle East & Central Asia",
        "Africa",
    }
    # England/Scotland are iso.3166-2 subjects
    eng = next(c for c in claims if c["raw_value"].startswith("England"))
    assert eng["subject_id"] == "jurisdiction:iso.3166-2:GB-ENG"
    # source citations ride the claim
    cited = next(c for c in claims if c["source_citations"])
    assert all(u.startswith("http") for u in cited["source_citations"])


def test_frwm_live_targets_register_the_six_sheets() -> None:
    targets = live_targets("facial_recognition_world_map")
    csvs = [t for t in targets if t["kind"] == "dataset_csv"]
    assert len(csvs) == 6
    assert {t["sheet"] for t in csvs} == set(_FRWM_SHEETS)


@pytest.mark.parametrize(
    "fixture",
    ["frwm_drift_header.csv", "frwm_unknown_country.csv", "frwm_unknown_status.csv"],
)
def test_frwm_shape_drift_fails_closed(fixture: str) -> None:
    """Changed header / unmapped country / unmapped status -> ContentDrift."""
    with pytest.raises(ContentDrift):
        ci.parse_dataset_csv(
            (_FIX / fixture).read_bytes(),
            source_id="facial_recognition_world_map",
            spec=ci.adapter_spec("facial_recognition_world_map"),
        )


def test_frwm_page_without_dataset_link_is_drift() -> None:
    """The page<->sheet binding is checked on the document capture (fail loud)."""
    page = b"<html><body>no dataset link any more</body></html>"
    ctx = _ctx(
        "facial_recognition_world_map",
        _MappedTransport({_FRWM_PAGE: (page, "text/html")}),
        [{"id": "page", "url": _FRWM_PAGE, "kind": "document"}],
    )
    with pytest.raises(ContentDrift):
        run(ci.CoarseInternationalConnector(), ctx)


def test_frwm_sheet_with_forbidden_column_is_refused() -> None:
    """A per-person column on a live surface trips ContentDrift on the header —
    and the aggregate gate independently refuses the field name."""
    with pytest.raises(ContentDrift):  # header drift fires first
        ci.parse_dataset_csv(
            (_FIX / "frwm_person_column.csv").read_bytes(),
            source_id="facial_recognition_world_map",
            spec=ci.adapter_spec("facial_recognition_world_map"),
        )
    with pytest.raises(ci.CoarseNonAggregateError):
        ci.assert_coarse_aggregate_fields(["Country", "Search subject name"])


# --- the aggregate-only + typed gates over the curated path ---------------------


def test_curated_row_with_per_search_field_is_refused() -> None:
    """The aggregate gate runs on every normalized row, curated path included."""
    ctx = _ctx(
        "carnegie_ai_gsi",
        _MappedTransport({}),
        [{"id": "t1", "url": "https://carnegie_ai_gsi/x", "kind": "bulk"}],
    )
    connector = ci.CoarseInternationalConnector()
    parsed = {
        "rows": [
            {
                "subject_id": "jurisdiction:iso.3166-1:CN",
                "predicate": "uses_ai_surveillance",
                "value": True,
                "raw_value": "x",
                "search_id": "abc-123",  # a per-search field — refused
            }
        ]
    }
    with pytest.raises(ci.CoarseNonAggregateError):
        connector.normalize(
            ctx, [{"dataset_id": "carnegie_ai_gsi", "row": dict(parsed["rows"][0])}]
        )


def test_curated_row_with_unlisted_predicate_is_refused() -> None:
    ctx = _ctx(
        "carnegie_ai_gsi",
        _MappedTransport({}),
        [{"id": "t1", "url": "https://carnegie_ai_gsi/x", "kind": "bulk"}],
    )
    connector = ci.CoarseInternationalConnector()
    row = {
        "subject_id": "jurisdiction:iso.3166-1:CN",
        "predicate": "camera_count",  # outside the coarse allowlist
        "value": 42,
        "raw_value": "x",
    }
    with pytest.raises(ci.CoarsePredicateNotAllowed):
        connector.normalize(ctx, [{"dataset_id": "carnegie_ai_gsi", "row": row}])


# --- append-only + shadow replay ------------------------------------------------


def test_changed_snapshot_yields_new_dated_claims_never_overwrites() -> None:
    """A changed upstream value is a NEW claim; the old interpretation is retained."""
    v1 = (_FIX / "frwm_sheet_north_america.csv").read_bytes()
    v2 = v1.replace(b'"Bahamas","In use"', b'"Bahamas","Considering technology"')
    ctx = _ctx("facial_recognition_world_map", _MappedTransport({}), [])
    connector = ci.CoarseInternationalConnector()
    c1 = ctx.captures.put(
        v1, media_type="text/csv", source_uri=_sheet_url("689675349"), retrieved_at=_RETRIEVED
    )
    c2 = ctx.captures.put(
        v2,
        media_type="text/csv",
        source_uri=_sheet_url("689675349"),
        retrieved_at=datetime(2026, 10, 1, tzinfo=UTC),
    )
    ctx.resolved_targets[_sheet_url("689675349")] = {
        "id": "frwm-sheet:689675349",
        "url": _sheet_url("689675349"),
        "kind": "dataset_csv",
        "sheet": "North America",
    }
    from connectors.pipeline import run_post_capture

    claims1 = run_post_capture(connector, ctx, c1)
    claims2 = run_post_capture(connector, ctx, c2)
    diff = diff_claim_sets(claims1, claims2)
    # A re-fetch of a changed snapshot adds the whole NEW dated claim set —
    # every claim carries its retrieval date, so the new snapshot is `added`
    # wholesale and nothing is overwritten in place (the old set stays).
    assert len(diff.added) == len(claims2) == len(claims1)
    bahamas_new = next(c for c in diff.added if c["subject_id"] == "jurisdiction:iso.3166-1:BS")
    assert bahamas_new["value"] == "considering"
    assert bahamas_new["observed_at"] == "2026-10-01"  # new dated claim
    assert "Considering technology" in bahamas_new["raw_value"]
    bahamas_old = next(c for c in diff.removed if c["subject_id"] == "jurisdiction:iso.3166-1:BS")
    assert bahamas_old["value"] == "in_use"


def test_shadow_replay_over_adapter_fixtures_has_zero_diffs() -> None:
    """Byte-identical re-runs over the adapter surfaces replay clean (SIG-INGEST-019)."""
    ctx = _ctx("facial_recognition_world_map", _frwm_transport(), _frwm_targets())
    connector = ci.CoarseInternationalConnector()
    report = run(connector, ctx)
    diff = shadow_replay(connector, ctx, report.captures, report.claims)
    assert diff.changed_count == 0

    ctx2 = _ctx(
        "carnegie_ai_gsi",
        _carnegie_transport(),
        [{"id": "page", "url": _CARNEGIE_PAGE, "kind": "document"}],
    )
    report2 = run(connector, ctx2)
    diff2 = shadow_replay(connector, ctx2, report2.captures, report2.claims)
    assert diff2.changed_count == 0


def test_aspi_stays_document_capture_only() -> None:
    """ASPI has no reachable data surface — a document target only, no claims."""
    spec = ci.adapter_spec("aspi_mapping_chinas_tech_giants")
    assert spec["kind"] == "document"
    targets = live_targets("aspi_mapping_chinas_tech_giants")
    assert [t["kind"] for t in targets] == ["document"]
