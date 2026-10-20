# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.74 — the probe-only Flock transparency-portal connector (WV-10/ADR-188).

Every acceptance criterion is pinned here against committed fixtures — NO
network: a FakeTransport serves the canned pages and a PoliteFetcher over it
exercises the real opt-out / robots / challenge machinery. The source row
stays ingestion_permitted=false; tests permit it on an in-memory copy
exactly like the atlas/osm/flock connector tests.

Covered: the committed inventory's invariants; the mirror-schema parse
(served / no-payload / slug-mismatch / row-level-shape refusal); the
in-memory Part VIII screen firing before persistence; the verbatim terms
capture; the CC BY-SA 4.0 + portal-compartment stamping; every refusal kind
on the probe-run record; and the "no circumvention, no discovery, no live
egress in the default path" guards.
"""

from __future__ import annotations

import dataclasses
import inspect
import json
import re
import tomllib
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
from connectors.flock_portal_probe import (
    PAGE_SCHEMA,
    PORTAL_COMPARTMENT,
    PROBE_CONNECTOR_NAME,
    PROBE_SOURCE_ID,
    TARGETS_SCHEMA,
    FlockPortalProbeConnector,
    PortalSchemaError,
    ProbeInventory,
    ProbeTarget,
    allowed_field_names,
    load_probe_inventory,
    parse_portal_page,
    probe_run_record,
    probe_schema,
    write_probe_run_record,
)
from connectors.loader import IngestionNotPermitted
from connectors.net import PoliteFetcher, RateLimiter, RobotsResult
from connectors.opt_out import OptOutEntry, OptOutRegister
from connectors.registry import get
from connectors.replay import replay
from connectors.runner import CONNECTOR_FOR_SOURCE
from connectors.stages import (
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun

import connectors
from connectors import pipeline

_FIX = Path(__file__).parent / "fixtures" / "flock_portal_probe"
_DATA = Path(__file__).parents[2] / "connectors" / "src" / "connectors" / "data"
_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"
_HOST = "transparency.flocksafety.com"


class FakeTransport:
    """Canned responses over the shared seam — never a socket (SIG-INGEST-011)."""

    def __init__(
        self,
        responses: dict[str, FetchResult],
        *,
        robots_text: str | None = _ROBOTS_ALLOW_ALL,
        robots_status: int | None = None,
    ) -> None:
        self._responses = dict(responses)
        self._robots_text = robots_text
        self._robots_status = robots_status
        self.request_log: list[str] = []
        self.robots_log: list[str] = []
        self.header_log: list[dict[str, str] | None] = []

    def robots(self, robots_url: str) -> RobotsResult:
        self.robots_log.append(robots_url)
        return RobotsResult(text=self._robots_text, status=self._robots_status)

    def request(self, url: str, *, user_agent: str, headers: Any = None) -> FetchResult:
        self.request_log.append(url)
        self.header_log.append(dict(headers) if headers is not None else None)
        return self._responses[url]


def _fixture_bytes(name: str) -> bytes:
    return (_FIX / name).read_bytes()


def _served(url: str, fixture: str, **kw: Any) -> FetchResult:
    return FetchResult(
        url=url,
        status=200,
        body=_fixture_bytes(fixture),
        media_type="text/html",
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        **kw,
    )


def _inventory(*targets: ProbeTarget) -> ProbeInventory:
    """A bounded test inventory — injected, never the committed 917."""
    base = load_probe_inventory()
    return dataclasses.replace(base, portals=tuple(targets))


def _target(slug: str, *, opted_out: bool = False) -> ProbeTarget:
    return ProbeTarget(slug=slug, url=f"https://{_HOST}/{slug}", opted_out=opted_out)


def _connector(*targets: ProbeTarget) -> FlockPortalProbeConnector:
    return FlockPortalProbeConnector(inventory=_inventory(*targets))


def _ctx(fetcher: Any, *, parameters: dict[str, Any] | None = None) -> RunContext:
    # The registry row stays ingestion_permitted=false; a reviewer flips it —
    # the tests exercise the connector on a permitted COPY (SIG-INGEST-028
    # stays exercised by the default-path tests below).
    source = dataclasses.replace(get(PROBE_SOURCE_ID), ingestion_permitted=True)
    return RunContext(
        source=source,
        run=IngestRun(PROBE_CONNECTOR_NAME, "1.0.0", "deadbeef", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters=parameters or {},
    )


def _fetcher(transport: FakeTransport, **kw: Any) -> PoliteFetcher:
    return PoliteFetcher(
        connector_name=PROBE_CONNECTOR_NAME,
        connector_version="1.0.0",
        transport=transport,
        rate_limiter=RateLimiter(sleep=lambda s: None),
        **kw,
    )


def _run(
    pages: dict[str, FetchResult],
    *targets: ProbeTarget,
    robots_text: str | None = _ROBOTS_ALLOW_ALL,
    **fetcher_kw: Any,
) -> tuple[Any, FlockPortalProbeConnector, FakeTransport]:
    """End-to-end pipeline run over canned pages — zero network."""
    transport = FakeTransport(pages, robots_text=robots_text)
    conn = _connector(*targets)
    report = pipeline.run(conn, _ctx(_fetcher(transport, **fetcher_kw)))
    return report, conn, transport


# --- the committed probe inventory (data invariants) ----------------------------


def test_inventory_count_and_provenance() -> None:
    """917 portals, provenance recorded — the I3-L005 derived set, committed."""
    inv = load_probe_inventory()
    assert len(inv.portals) == 917
    assert inv.source_uri == "https://eyesonflock.com/api/v1/data"
    assert inv.upstream_snapshot_date == "2026-09-23T10:15:16.751Z"
    assert inv.captured_on == "2026-10-11"
    assert len(inv.snapshot_sha256) == 64
    assert "organizations_shared_with" in inv.selection_rule
    assert inv.upstream_portals == 1528
    assert inv.waiver


def test_inventory_is_sorted_unique_https_slug_urls() -> None:
    inv = load_probe_inventory()
    slugs = [p.slug for p in inv.portals]
    assert slugs == sorted(slugs)
    assert len(set(slugs)) == len(slugs)
    for p in inv.portals:
        parts = urlsplit(p.url)
        assert parts.scheme == "https"
        assert parts.netloc == _HOST
        assert parts.path == f"/{p.slug}"
        assert not parts.query and not parts.fragment


def test_inventory_carries_identifiers_only() -> None:
    """SIG-INGEST-045i: {slug, url} rows — no portal content, ever."""
    table = tomllib.loads((_DATA / "flock_portal_probe_targets.toml").read_text("utf-8"))
    assert table["schema"] == TARGETS_SCHEMA
    rows = table["inventory"]["portals"]
    assert all(set(r) == {"slug", "url"} for r in rows)
    # No row may carry a per-search / per-plate / per-person FIELD — the row
    # keys are exactly {slug, url} (asserted above); belt-and-suspenders, no
    # KEY matches the denied vocabulary either.
    denied = {p.lower() for p in probe_schema().get("denied_fields") or ()}
    import fnmatch

    assert not any(
        k.lower() in denied or any(fnmatch.fnmatch(k.lower(), pat) for pat in denied)
        for r in rows
        for k in r
    )


def test_inventory_validation_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """A malformed inventory refuses to load (unsorted/duplicate/wrong count)."""
    real = tomllib.loads((_DATA / "flock_portal_probe_targets.toml").read_text("utf-8"))

    def _broken(**kw: Any) -> dict[str, Any]:
        table = dict(real)
        inv = dict(table["inventory"])
        # Unsorted, count-lying rows — the loader must refuse, never probe.
        inv["portals"] = [
            {"slug": "zzz", "url": f"https://{_HOST}/zzz"},
            {"slug": "aaa", "url": f"https://{_HOST}/aaa"},
        ]
        inv["portal_count"] = 2
        table["inventory"] = inv
        return table

    monkeypatch.setattr("connectors.flock_portal_probe.load_table", lambda _name: _broken())
    with pytest.raises(ValueError, match="slug-sorted"):
        load_probe_inventory()

    def _dup(**kw: Any) -> dict[str, Any]:
        table = dict(real)
        inv = dict(table["inventory"])
        inv["portals"] = [
            {"slug": "aaa", "url": f"https://{_HOST}/aaa"},
            {"slug": "aaa", "url": f"https://{_HOST}/aaa"},
        ]
        inv["portal_count"] = 2
        table["inventory"] = inv
        return table

    monkeypatch.setattr("connectors.flock_portal_probe.load_table", lambda _name: _dup())
    with pytest.raises(ValueError, match="duplicate"):
        load_probe_inventory()


def test_registry_row_stays_gated() -> None:
    """The direct source stays OFF (HG-03/ING-GO-B is the operator's flip)."""
    row = get(PROBE_SOURCE_ID)
    assert row.ingestion_permitted is False
    # DERIVE custody — the probe persists only the screened extraction.
    assert row.custody_posture.value == "DERIVE"
    assert CONNECTOR_FOR_SOURCE[PROBE_SOURCE_ID] == PROBE_CONNECTOR_NAME
    # The loader gate stands: an unpermitted source refuses before any fetch.
    unpermitted_ctx = RunContext(
        source=get(PROBE_SOURCE_ID),  # the committed row — ingestion_permitted=false
        run=IngestRun(PROBE_CONNECTOR_NAME, "1.0.0", "deadbeef", "r1", "v1", ()),
        fetcher=None,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
    )
    with pytest.raises(IngestionNotPermitted):
        pipeline.run(
            FlockPortalProbeConnector(inventory=_inventory(_target("x"))),
            unpermitted_ctx,
        )


def test_registered_and_distinct_from_aggregator() -> None:
    """The probe is its own connector identity; eyes_on_flock is untouched."""
    assert CONNECTOR_FOR_SOURCE["eyes_on_flock"] == "flock_portal"
    assert CONNECTOR_FOR_SOURCE[PROBE_SOURCE_ID] == "flock_portal_probe"
    cls = connectors.flock_portal_probe.FlockPortalProbeConnector
    assert cls.name == "flock_portal_probe"


# --- mirror-schema parse (pure function over committed fixtures) -----------------


def test_parse_served_page_extracts_allowlist_and_terms() -> None:
    parsed = parse_portal_page(
        _fixture_bytes("served_sunnydale.html"),
        url=f"https://{_HOST}/sunnydale-ca-pd",
        slug="sunnydale-ca-pd",
    )
    portal = dict(parsed.page.portal)
    assert portal["slug"] == "sunnydale-ca-pd"
    assert portal["total_cameras"] == 14
    assert portal["organizations_shared_with"] == ["hellmouth-ca-pd", "city-of-sunnydale-pd"]
    # Aggregates stay; the denied `description` is refused by NAME.
    assert "description" in parsed.page.refused_fields
    assert "description" not in portal
    # Verbatim terms — the element text, not a paraphrase.
    assert parsed.page.terms_text is not None
    assert "Flock Transparency Terms" in parsed.page.terms_text
    # The artifact the connector persists — canonical page record.
    rec = parsed.page.record()
    assert rec["schema"] == PAGE_SCHEMA
    assert "search_audit" not in json.dumps(rec)


def test_parse_terms_from_payload_field() -> None:
    parsed = parse_portal_page(
        _fixture_bytes("served_terms_payload.html"),
        url=f"https://{_HOST}/summersville-ca-pd",
        slug="summersville-ca-pd",
    )
    assert parsed.page.portal["slug"] == "summersville-ca-pd"
    assert parsed.page.terms_text is not None
    assert "verbatim capture" in parsed.page.terms_text
    assert "punctuation &  spacing" in parsed.page.terms_text  # verbatim — spacing kept


def test_parse_refuses_missing_payload() -> None:
    with pytest.raises(PortalSchemaError):
        parse_portal_page(
            _fixture_bytes("no_payload.html"),
            url=f"https://{_HOST}/sunnydale-ca-pd",
            slug="sunnydale-ca-pd",
        )


def test_parse_refuses_slug_mismatch() -> None:
    with pytest.raises(PortalSchemaError, match="different portal slug"):
        parse_portal_page(
            _fixture_bytes("slug_mismatch.html"),
            url=f"https://{_HOST}/sunnydale-ca-pd",
            slug="sunnydale-ca-pd",
        )


def test_parse_refuses_row_level_values() -> None:
    """A dict/list-of-dicts under an allowlisted key is refused, never kept."""
    body = (
        b'<script type="application/json">'
        + json.dumps(
            {
                "portal": {
                    "slug": "sunnydale-ca-pd",
                    "total_cameras": 1,
                    "organizations_shared_with": [{"org": "x", "plate": "Y"}],  # row-level
                }
            }
        ).encode()
        + b"</script>"
    )
    parsed = parse_portal_page(body, url="u", slug="sunnydale-ca-pd")
    assert "organizations_shared_with" not in parsed.page.portal
    assert "organizations_shared_with" in parsed.page.refused_fields


# --- the served path end-to-end ----------------------------------------------------


def test_served_portal_captures_extraction_not_raw_page() -> None:
    """capture() persists sig.flock-portal-page/1 — NEVER the vendor's HTML."""
    t0 = _target("sunnydale-ca-pd")
    transport = FakeTransport({t0.url: _served(t0.url, "served_sunnydale.html")})
    conn = _connector(t0)
    ctx = _ctx(_fetcher(transport))
    report = pipeline.run(conn, ctx)
    assert len(report.captures) == 1
    cap = report.captures[0]
    stored = ctx.captures.get(cap.digest)
    assert cap.media_type == "application/json"
    assert b"<html" not in stored  # raw page never persisted
    assert json.loads(stored.decode("utf-8"))["schema"] == PAGE_SCHEMA
    assert len(transport.request_log) == 1  # exactly ONE GET per portal


def test_served_portal_claims_stamped_ccbysa_portal_compartment() -> None:
    t0 = _target("sunnydale-ca-pd")
    transport = FakeTransport({t0.url: _served(t0.url, "served_sunnydale.html")})
    conn = _connector(t0)
    ctx = _ctx(_fetcher(transport))
    report = pipeline.run(conn, ctx)
    assert report.captures
    capture = report.captures[0]
    stored = ctx.captures.get(capture.digest)
    doc = json.loads(stored.decode("utf-8"))
    assert doc["schema"] == PAGE_SCHEMA
    assert doc["slug"] == "sunnydale-ca-pd"
    assert doc["portal"]["total_cameras"] == 14
    assert doc["terms_text"] and "Flock Transparency Terms" in doc["terms_text"]
    assert b"<html" not in stored
    # Claims: portal-compartment, CC-BY-SA-4.0, ai_training_permitted=false,
    # the PROBE source id — never the aggregator's eyes_on_flock.
    assert report.claims
    for c in report.claims:
        assert c["compartment"] == PORTAL_COMPARTMENT
        assert c["license"] == "CC-BY-SA-4.0"
        assert c["ai_training_permitted"] is False
        assert c["source_id"] == PROBE_SOURCE_ID
    preds = {c.get("predicate_id") for c in report.claims}
    assert "portal_exists" in preds
    assert "active_device_count" in preds
    # A configured-sharing edge ran through the §29.3 reconciler.
    assert "configured_sharing_partner" in preds


def test_run_produces_one_probe_run_record() -> None:
    """Exactly one sig.probe-run/1 per run — deterministic modulo generated_at."""
    t0 = _target("sunnydale-ca-pd")
    t1 = _target("adrian-mi-pd")
    report, conn, _ = _run(
        {
            t0.url: _served(t0.url, "served_sunnydale.html"),
            t1.url: FetchResult(
                url=t1.url,
                status=403,
                body=b"Forbidden",
                media_type="text/html",
                retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
        },
        t0,
        t1,
    )
    rec = probe_run_record(conn, report, run_id="r1", generated_at="2026-01-01T00:00:00Z")
    assert rec["version"] == "sig.probe-run/1"
    assert rec["probe"] == "flock-portal-probe"
    assert rec["source_id"] == PROBE_SOURCE_ID
    assert rec["overall"] == "pass"
    results = {r["portal"]: r for r in rec["results"]}
    assert results["sunnydale-ca-pd"]["result"] == "served"
    assert results["adrian-mi-pd"]["result"] == "refused"
    assert results["adrian-mi-pd"]["refusal_kind"] == "challenge"
    # Deterministic serialization — same inputs, same digest.
    rec2 = probe_run_record(conn, report, run_id="r1", generated_at="2026-01-01T00:00:00Z")
    assert json.dumps(rec, sort_keys=True) == json.dumps(rec2, sort_keys=True)
    assert rec["output_digest"] == rec2["output_digest"]
    # The verbatim terms land on the record, deduplicated by digest.
    assert rec["terms"]
    assert any("Flock Transparency Terms" in v for v in rec["terms"].values())
    # Write is append-only under the probe-records surface.
    out = write_probe_run_record(rec, Path("/tmp/probe_records_test"))
    assert out.exists() and "sig.probe-run/1" in out.read_text()


def test_challenge_403_stops_and_records() -> None:
    """WV-10: a 403 challenge ends the attempt — recorded, never retried."""
    t0 = _target("sunnydale-ca-pd")
    report, conn, transport = _run(
        {
            t0.url: FetchResult(
                url=t0.url,
                status=403,
                body=b"Forbidden",
                media_type="text/html",
                retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        },
        t0,
    )
    assert not report.captures and report.claim_count == 0
    assert len(transport.request_log) == 1  # one attempt, no retry
    kinds = {o["refusal_kind"] for o in conn.outcomes}
    assert kinds == {"challenge"}
    assert report.last_challenge_status == 403
    statuses = {d.event.failing_status for d in report.disappearances}
    assert statuses == {"access_restricted"}


def test_interstitial_2xx_is_a_recorded_challenge() -> None:
    """A 2xx bot-management stub is a challenge — same stop, finer kind."""
    t0 = _target("sunnydale-ca-pd")
    report, conn, _ = _run({t0.url: _served(t0.url, "interstitial.html")}, t0)
    assert not report.captures
    o = conn.outcomes[0]
    assert o["refusal_kind"] == "interstitial"
    assert {d.event.failing_status for d in report.disappearances} == {"access_restricted"}


def test_404_is_a_recorded_gone() -> None:
    t0 = _target("sunnydale-ca-pd")
    report, conn, _ = _run(
        {
            t0.url: FetchResult(
                url=t0.url,
                status=404,
                body=b"nope",
                media_type="text/html",
                retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        },
        t0,
    )
    assert not report.captures
    assert conn.outcomes[0]["refusal_kind"] == "http_404"
    assert {d.event.failing_status for d in report.disappearances} == {"link_rotted"}


def test_schema_refusal_is_recorded_not_captured() -> None:
    t0 = _target("sunnydale-ca-pd")
    report, conn, _ = _run({t0.url: _served(t0.url, "no_payload.html")}, t0)
    assert not report.captures
    assert conn.outcomes[0]["refusal_kind"] == "schema_refusal"
    assert {r["refusal"] for r in report.refusals} == {"SchemaRefusal"}


def test_part_viii_screen_refuses_whole_page_before_persistence() -> None:
    """A page carrying a plate-named field is refused WHOLE — zero bytes persist."""
    t0 = _target("hellmouth-ca-pd")
    report, conn, transport = _run({t0.url: _served(t0.url, "served_hellmouth_screened.html")}, t0)
    assert not report.captures and report.claim_count == 0
    o = conn.outcomes[0]
    assert o["refusal_kind"] == "screened"
    assert "PUB002-PLATES" in o["screen_hits"]
    assert {r["refusal"] for r in report.refusals} == {"ScreenedRefusal"}
    # The capture store holds nothing — screened bytes never persisted.
    assert len(transport.request_log) == 1


def test_host_optout_zero_egress() -> None:
    """§26 rule 7: an opted-out HOST receives zero egress — not even robots."""
    t0 = _target("sunnydale-ca-pd")
    register = OptOutRegister(
        entries=(
            OptOutEntry(
                host=_HOST,
                recorded_on=date(2026, 10, 1),
                evidence="test opt-out entry",
            ),
        )
    )
    transport = FakeTransport({t0.url: _served(t0.url, "served_sunnydale.html")})
    conn = _connector(t0)
    report = pipeline.run(conn, _ctx(_fetcher(transport, opt_out_register=register)))
    assert not report.captures
    assert transport.request_log == [] and transport.robots_log == []
    assert {o["refusal_kind"] for o in conn.outcomes} == {"opt_out"}
    assert {r["refusal"] for r in report.refusals} == {"HostOptOut"}


def test_rights_reservation_refusal() -> None:
    """SIG-INGEST-046c: an affirmative Content-Signal/TDM reservation on the
    response is honoured as a refusal — bytes never captured."""
    t0 = _target("sunnydale-ca-pd")
    report, conn, _ = _run(
        {
            t0.url: FetchResult(
                url=t0.url,
                status=200,
                body=_fixture_bytes("served_sunnydale.html"),
                media_type="text/html",
                retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
                headers={"Content-Signal": "ai-train=no"},
            )
        },
        t0,
    )
    assert not report.captures and report.claim_count == 0
    assert {o["refusal_kind"] for o in conn.outcomes} == {"rights_reservation"}
    assert {r["refusal"] for r in report.refusals} == {"ReservationRefused"}


def test_portal_optout_zero_egress() -> None:
    """Portal-granular opt-out (the committed `opted_out_portals` column)."""
    t0 = _target("sunnydale-ca-pd", opted_out=True)
    transport = FakeTransport({t0.url: _served(t0.url, "served_sunnydale.html")})
    conn = _connector(t0)
    report = pipeline.run(conn, _ctx(_fetcher(transport)))
    assert not report.captures
    assert transport.request_log == [] and transport.robots_log == []
    assert {o["refusal_kind"] for o in conn.outcomes} == {"PortalOptedOut"}
    assert {r["refusal"] for r in report.refusals} == {"PortalOptedOut"}


def test_discover_refuses_targets_outside_inventory() -> None:
    """ADR-188 adds no discovery: an unlisted URL refuses at discover()."""
    conn = _connector(_target("sunnydale-ca-pd"))
    ctx = _ctx(
        _fetcher(FakeTransport({})),
        parameters={"targets": [{"id": "rogue", "url": "https://example.com/rogue"}]},
    )
    with pytest.raises(ValueError, match="not in the committed probe inventory"):
        conn.discover(ctx)


def test_replay_rederives_claims_without_fetch() -> None:
    """Post-capture stages are pure functions of the screened capture (SIG-INGEST-002)."""
    t0 = _target("sunnydale-ca-pd")
    transport = FakeTransport({t0.url: _served(t0.url, "served_sunnydale.html")})
    conn = _connector(t0)
    ctx = _ctx(_fetcher(transport))
    report = pipeline.run(conn, ctx)
    capture = report.captures[0]
    # Replay re-derives from the stored capture — zero requests, no fetcher.
    before = list(transport.request_log)
    claims = replay(_connector(t0), dataclasses.replace(ctx, fetcher=None), [capture])
    assert transport.request_log == before
    live_predicates = {c.get("predicate_id") for c in report.claims}
    replay_predicates = {c.get("predicate_id") for c in claims}
    assert live_predicates == replay_predicates


def test_no_circumvention_anywhere() -> None:
    """SIG-INGEST-013/036/037: no browser automation, proxy, or challenge-solving."""
    src = inspect.getsource(connectors.flock_portal_probe)
    forbidden = re.compile(
        r"playwright|selenium|puppeteer|undetected|cloudscraper|"
        r"headless|proxy_rotate|rotate_proxy|import requests|import httpx|"
        r"urllib\.request|cookie",
        re.I,
    )
    assert not forbidden.search(src), forbidden.search(src)


def test_egress_only_through_shared_seam() -> None:
    """The connector holds no transport/HTTP client — ctx.fetcher only."""
    init_src = inspect.getsource(FlockPortalProbeConnector.__init__)
    assert "transport" not in init_src
    assert "PoliteFetcher(" not in init_src


def test_all_refused_run_is_pass_but_zero_attempt_fails() -> None:
    """Expected yield ≈ 0 is honest (F2.1); attempting nothing is a FAIL."""
    t0 = _target("sunnydale-ca-pd")
    report, conn, _ = _run({t0.url: _served(t0.url, "interstitial.html")}, t0)
    rec = probe_run_record(conn, report, run_id="r", generated_at="t")
    assert rec["overall"] == "pass"
    assert rec["checks"]["served"]["count"] == 0
    assert rec["checks"]["refusals"]["count"] == 1

    # A connector whose outcome ledger is empty while the driver issued
    # fetches → coverage FAIL (an unmeasured fetch is a loud failure).
    idle = _connector(t0)
    rec2 = probe_run_record(idle, report, run_id="r2", generated_at="t")
    assert rec2["checks"]["coverage"]["verdict"] == "fail"
    assert rec2["overall"] == "fail"


def test_no_per_search_per_plate_fields_anywhere() -> None:
    """SIG-PUB-002/003a: the emitted surface is aggregate-only — static + dynamic."""
    # The allowlist contains no per-search/per-plate field.
    allowed = allowed_field_names()
    assert not ({"plate", "plates", "vrm", "vin", "search_log", "search_audit"} & set(allowed))
    # Every served fixture's emitted claims + persisted capture carry
    # aggregates only — the screened fixture's plate values never surface.
    t0 = _target("sunnydale-ca-pd")
    transport = FakeTransport({t0.url: _served(t0.url, "served_sunnydale.html")})
    conn = _connector(t0)
    ctx = _ctx(_fetcher(transport))
    report = pipeline.run(conn, ctx)
    for c in report.claims:
        blob = json.dumps(c, default=str).lower()
        for bad in ("8ksoma1", "case_number", "officer", "search_reason"):
            assert bad not in blob
    stored = ctx.captures.get(report.captures[0].digest)
    assert b"8ksoma1" not in stored and b"plate" not in stored
