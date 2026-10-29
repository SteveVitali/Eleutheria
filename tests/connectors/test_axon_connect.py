# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.76 — the Axon Fusus `Connect <Place>` connector + marked-host screen.

Every acceptance criterion is pinned here against committed fixtures — NO
network: a FakeTransport serves the canned pages and a PoliteFetcher over it
exercises the real opt-out / robots / challenge machinery. The source row
stays ingestion_permitted=false; tests permit it on an in-memory copy
exactly like the flock probe tests.

Covered: the committed inventory's invariants; the Connect-page parse
(brand / modes / verbatim clauses / identity check / embedded-JSON denylist);
the `/:8443/faststream/login.html` screen record (recognised + unmarked);
the in-memory Part VIII screen refusing a registrant-byte page whole before
persistence; the programme-only claim surface and the candidate-of-record
row; the loader gate refusing the unpermitted source; discover refusing
outside the committed set; and the "no circumvention, no discovery, no live
egress in the default path" guards.
"""

from __future__ import annotations

import dataclasses
import inspect
import json
import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
from connectors.axon_connect import (
    PAGE_SCHEMA,
    SCREEN_SCHEMA,
    SOURCE_ID,
    AxonConnectConnector,
    ConnectSite,
    PredicateNotAllowed,
    connect_targets,
    fusus_screen_record,
    load_inventory,
    parse_connect_page,
    predicate_allowlist,
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

_FIX = Path(__file__).parent / "fixtures" / "axon_connect"
_DATA = Path(__file__).parents[2] / "connectors" / "src" / "connectors" / "data"
_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"
_HOST = "connectshawneecounty.org"
_SITE = "connect_shawnee_county"


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

    def robots(self, robots_url: str) -> RobotsResult:
        self.robots_log.append(robots_url)
        return RobotsResult(text=self._robots_text, status=self._robots_status)

    def request(self, url: str, *, user_agent: str, headers: Any = None) -> FetchResult:
        self.request_log.append(url)
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


def _site(*, opted_out: bool = False) -> ConnectSite:
    return dataclasses.replace(load_inventory().site(_SITE), opted_out=opted_out)  # type: ignore[union-attr]


def _site_targets(site: ConnectSite) -> list[dict[str, Any]]:
    return [
        {
            "id": f"{site.site}:page",
            "url": site.registration_url,
            "kind": "connect_page",
            "site": site.site,
            "subject_id": f"connect_site:{site.site}",
        },
        {
            "id": f"{site.site}:8443",
            "url": site.screen_url,
            "kind": "marked_host_screen",
            "site": site.site,
            "subject_id": f"fusus_host:{site.host}",
        },
    ]


def _connector(site: ConnectSite | None = None) -> AxonConnectConnector:
    site = site or _site()
    inv = load_inventory()
    return AxonConnectConnector(
        inventory=dataclasses.replace(inv, sites=(site,)),
    )


def _ctx(fetcher: Any, *, parameters: dict[str, Any] | None = None) -> RunContext:
    # The registry row stays ingestion_permitted=false; a reviewer flips it —
    # the tests exercise the connector on a permitted COPY (SIG-INGEST-028
    # stays exercised by the default-path tests below).
    source = dataclasses.replace(get(SOURCE_ID), ingestion_permitted=True)
    return RunContext(
        source=source,
        run=IngestRun("axon_connect", "1.0.0", "deadbeef", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters=parameters or {},
    )


def _fetcher(transport: FakeTransport, **kw: Any) -> PoliteFetcher:
    return PoliteFetcher(
        connector_name="axon_connect",
        connector_version="1.0.0",
        transport=transport,
        rate_limiter=RateLimiter(sleep=lambda s: None),
        **kw,
    )


def _run(
    pages: dict[str, FetchResult],
    site: ConnectSite | None = None,
    targets: list[dict[str, Any]] | None = None,
    **fetcher_kw: Any,
) -> tuple[Any, AxonConnectConnector, FakeTransport]:
    """End-to-end pipeline run over canned pages — zero network."""
    site = site or _site()
    transport = FakeTransport(pages)
    conn = _connector(site)
    params = {"targets": targets} if targets is not None else None
    report = pipeline.run(conn, _ctx(_fetcher(transport, **fetcher_kw), parameters=params))
    return report, conn, transport


# --- the committed site inventory (data invariants) ------------------------------


def test_inventory_count_sort_and_shape() -> None:
    """Six committed sites, sorted, https-only, identifiers + provenance only."""
    inv = load_inventory()
    assert len(inv.sites) == 6
    ids = [s.site for s in inv.sites]
    assert ids == sorted(ids)
    for s in inv.sites:
        parts = urlsplit(s.registration_url)
        assert parts.scheme == "https" and parts.netloc == s.host
        assert s.screen_url == f"https://{s.host}:8443/faststream/login.html"
        assert s.expect and s.agency and s.evidence
    assert inv.source_ref == "I9a-C003"
    # Identifiers only — no content columns on the rows.
    import tomllib

    table = tomllib.loads((_DATA / "axon_connect_targets.toml").read_text("utf-8"))
    assert table["schema"] == "sig.axon-connect-targets/1"
    for row in table["inventory"]["sites"]:
        assert set(row) <= {
            "site",
            "host",
            "registration_url",
            "agency",
            "jurisdiction",
            "status",
            "expect",
            "evidence",
        }


def test_two_bounded_targets_per_site() -> None:
    targets = connect_targets()
    assert len(targets) == 12
    kinds = {t["kind"] for t in targets}
    assert kinds == {"connect_page", "marked_host_screen"}
    assert all(t["url"].startswith("https://") for t in targets)


def test_inventory_validation_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """A malformed inventory refuses to load (unsorted/duplicate/count-lying)."""
    real = load_inventory()

    def _broken_count(**kw: Any) -> dict[str, Any]:
        import tomllib

        table = tomllib.loads((_DATA / "axon_connect_targets.toml").read_text("utf-8"))
        table["inventory"]["site_count"] = 99
        return table

    monkeypatch.setattr("connectors.axon_connect.load_table", lambda _name: _broken_count())
    with pytest.raises(ValueError, match="site_count"):
        load_inventory()
    assert len(real.sites) == 6


def test_registry_row_stays_gated() -> None:
    """The source stays OFF — leg B's flip is the operator's act (OP-26/HG-03)."""
    row = get(SOURCE_ID)
    assert row.ingestion_permitted is False
    assert row.custody_posture.value == "DERIVE"
    assert CONNECTOR_FOR_SOURCE[SOURCE_ID] == "axon_connect"
    # The loader gate stands: the committed row refuses before any fetch.
    unpermitted_ctx = RunContext(
        source=get(SOURCE_ID),
        run=IngestRun("axon_connect", "1.0.0", "deadbeef", "r1", "v1", ()),
        fetcher=None,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
    )
    with pytest.raises(IngestionNotPermitted):
        pipeline.run(_connector(), unpermitted_ctx)


def test_registered_identity() -> None:
    cls = connectors.axon_connect.AxonConnectConnector
    assert cls.name == "axon_connect"
    assert "axon_community_connect" not in CONNECTOR_FOR_SOURCE  # untouched neighbour row


# --- the connect_page parse (pure over committed fixtures) ------------------------


def test_parse_served_connect_page_programme_facts() -> None:
    parsed = parse_connect_page(
        _fixture_bytes("connect_shawnee.html"),
        url=f"https://{_HOST}/camera-registration/",
        site=_site(),
    )
    page = parsed.page
    assert page.programme_name == "Connect Shawnee County and the City of Topeka"
    assert page.modes_offered == ("registration", "integration")
    assert page.vendor_marked is True
    # The verbatim stated-use clauses land — the template's no-access sentence.
    assert any("does not allow" in c for c in page.stated_use_clauses)
    assert page.terms_text is not None and "Axon Fusus" in page.terms_text
    rec = page.record()
    assert rec["schema"] == PAGE_SCHEMA
    assert rec["page_sha256"] and rec["page_bytes"] > 0
    assert b"<html" not in page.record_bytes()


def test_parse_refuses_wrong_site() -> None:
    """A Connect-shaped page for another place contradicts the committed site."""
    with pytest.raises(Exception, match="expect"):
        parse_connect_page(
            _fixture_bytes("wrong_site.html"),
            url=f"https://{_HOST}/camera-registration/",
            site=_site(),
        )


def test_parse_refuses_no_programme_markers() -> None:
    """A page on a committed host that is not a Connect page refuses whole."""
    with pytest.raises(Exception, match="marker"):
        parse_connect_page(
            _fixture_bytes("not_faststream.html"),
            url=f"https://{_HOST}/camera-registration/",
            site=dataclasses.replace(_site(), expect=("works",)),
        )


# --- the :8443 marked-host screen ---------------------------------------------------


def test_screen_record_recognises_marked_host() -> None:
    """A served faststream login page is a recognised marked host — hash-pinned."""
    result = _served(f"https://{_HOST}:8443/faststream/login.html", "faststream_login.html")
    rec = fusus_screen_record(result, site=_site())
    assert rec["schema"] == SCREEN_SCHEMA
    assert rec["recognised"] is True
    assert "faststream" in rec["markers_hit"] and "fusus" in rec["markers_hit"]
    assert rec["status"] == 200
    assert len(rec["page_sha256"]) == 64 and rec["page_bytes"] > 0
    # The record carries NO page bytes — hash + markers + status only.
    assert "body" not in rec and "<html" not in json.dumps(rec).lower()


def test_screen_record_unmarked_host() -> None:
    result = _served(f"https://{_HOST}:8443/faststream/login.html", "not_faststream.html")
    rec = fusus_screen_record(result, site=_site())
    assert rec["recognised"] is False and rec["markers_hit"] == []


# --- the served path end-to-end -----------------------------------------------------


def test_connect_page_and_screen_capture_records_only() -> None:
    """capture() persists the screened records — NEVER the served bytes."""
    site = _site()
    t_page, t_screen = _site_targets(site)
    transport = FakeTransport(
        {
            t_page["url"]: _served(t_page["url"], "connect_shawnee.html"),
            t_screen["url"]: _served(t_screen["url"], "faststream_login.html"),
        }
    )
    conn = _connector(site)
    ctx = _ctx(_fetcher(transport))
    report = pipeline.run(conn, ctx)
    assert len(report.captures) == 2
    stored = {
        json.loads(ctx.captures.get(c.digest).decode("utf-8"))["schema"] for c in report.captures
    }
    assert stored == {PAGE_SCHEMA, SCREEN_SCHEMA}
    for c in report.captures:
        blob = ctx.captures.get(c.digest)
        assert b"<html" not in blob  # raw served bytes never persisted
    assert len(transport.request_log) == 2  # exactly ONE GET per bounded target


def test_page_claims_are_programme_facts_only() -> None:
    site = _site()
    t_page, _t_screen = _site_targets(site)
    report, conn, _ = _run(
        {t_page["url"]: _served(t_page["url"], "connect_shawnee.html")},
        site,
        targets=[t_page],
    )
    claims = [c for c in report.claims if c.get("record_kind") == "claim"]
    assert claims
    preds = {c["predicate_id"] for c in claims}
    assert "camera_registration_portal" in preds
    assert "camera_registry_publisher" in preds
    assert "agency_name" in preds
    assert "portal_stated_prohibited_use" in preds
    for c in claims:
        assert c["subject_id"] == f"connect_site:{_SITE}"
        assert c["source_id"] == SOURCE_ID
        assert c["ai_training_permitted"] is False
    pub = next(c for c in claims if c["predicate_id"] == "camera_registry_publisher")
    assert pub["value"] == "Shawnee County Sheriff's Office + City of Topeka"
    # Programme-facts-only on the wire: no registrant vocabulary anywhere.
    blob = json.dumps(report.claims, default=str).lower()
    for bad in ("registrant", "first_name", "last_name", "email", "phone", "address1"):
        assert bad not in blob


def test_screen_candidate_is_a_record_not_a_feed() -> None:
    """The marked-host presence lands as acquisition_candidate — never a claim."""
    site = _site()
    _t_page, t_screen = _site_targets(site)
    report, conn, _ = _run(
        {t_screen["url"]: _served(t_screen["url"], "faststream_login.html")},
        site,
        targets=[t_screen],
    )
    cands = [c for c in report.claims if c.get("record_kind") == "acquisition_candidate"]
    assert len(cands) == 1
    cand = cands[0]
    assert cand["candidate_kind"] == "fusus_marked_host"
    assert cand["subject_id"] == f"fusus_host:{_HOST}"
    assert cand["recognised"] is True
    assert cand["page_sha256"]
    # No claim row derives from a screen target.
    assert not [c for c in report.claims if c.get("record_kind") == "claim"]


def test_screened_page_refused_whole_zero_bytes() -> None:
    """A page serving registrant-byte fields is refused WHOLE — R11-A16 absolute."""
    site = _site()
    t_page, _ = _site_targets(site)
    report, conn, transport = _run(
        {t_page["url"]: _served(t_page["url"], "screened_registrant.html")},
        site,
        targets=[t_page],
    )
    assert not report.captures and report.claim_count == 0
    o = conn.outcomes[0]
    assert o["refusal_kind"] == "screened"
    assert o["screen_hits"]  # counts only, never the field values
    assert {r["refusal"] for r in report.refusals} == {"ScreenedRefusal"}
    assert len(transport.request_log) == 1


def test_emitted_fact_with_registrant_field_fails_loud() -> None:
    """A registrant-byte field in emitted facts raises — never a warning."""
    conn = _connector()
    ctx = _ctx(_fetcher(FakeTransport({})))
    bad = [
        {
            "record_kind": "axon_connect_page",
            "site": _SITE,
            "registrant_name": "x",
            "url": "u",
            "programme_name": "n",
            "page_sha256": "h",
            "page_bytes": 1,
        }
    ]
    with pytest.raises(PredicateNotAllowed, match="denied"):
        conn.normalize(ctx, bad)


def test_challenge_and_disappearances_recorded() -> None:
    """A 403 ends the target's attempt — recorded, never retried (SIG-INGEST-037).

    The shared fetcher raises ChallengeEncountered on 401/403/429 (a challenge
    is never defeated); the connector's ledger keeps the finer kind and the
    driver records the ``access_restricted`` disappearance.
    """
    site = _site()
    t_page, t_screen = _site_targets(site)
    report, conn, transport = _run(
        {
            t_page["url"]: FetchResult(
                url=t_page["url"],
                status=403,
                body=b"Forbidden",
                media_type="text/html",
                retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
            t_screen["url"]: _served(t_screen["url"], "faststream_login.html"),
        },
        site,
        targets=[t_page, t_screen],
    )
    refusal = next(o for o in conn.outcomes if o["result"] == "refused")
    assert refusal["refusal_kind"] == "challenge" and refusal["status"] == 403
    assert {d.event.failing_status for d in report.disappearances} == {"access_restricted"}
    # The screen target still captured — one target's refusal never aborts.
    assert len(report.captures) == 1
    assert len(transport.request_log) == 2  # each target attempted exactly once


def test_interstitial_2xx_is_a_recorded_challenge() -> None:
    site = _site()
    t_page, _ = _site_targets(site)
    report, conn, _ = _run(
        {t_page["url"]: _served(t_page["url"], "interstitial.html")},
        site,
        targets=[t_page],
    )
    assert not report.captures
    assert conn.outcomes[0]["refusal_kind"] == "interstitial"
    assert {d.event.failing_status for d in report.disappearances} == {"access_restricted"}


def test_site_optout_zero_egress() -> None:
    """§26 rule 7 at site granularity — the committed opted_out_sites column."""
    site = _site(opted_out=True)
    t_page, _ = _site_targets(site)
    transport = FakeTransport({t_page["url"]: _served(t_page["url"], "connect_shawnee.html")})
    conn = _connector(site)
    report = pipeline.run(conn, _ctx(_fetcher(transport), parameters={"targets": [t_page]}))
    assert not report.captures
    assert transport.request_log == [] and transport.robots_log == []
    assert {o["refusal_kind"] for o in conn.outcomes} == {"opted_out"}
    assert {r["refusal"] for r in report.refusals} == {"ConnectSiteOptedOut"}


def test_host_optout_zero_egress() -> None:
    """The host-level register (§26 rule 7) is consulted before any egress."""
    site = _site()
    t_page, _ = _site_targets(site)
    register = OptOutRegister(
        entries=(OptOutEntry(host=_HOST, recorded_on=date(2026, 10, 1), evidence="t"),)
    )
    transport = FakeTransport({t_page["url"]: _served(t_page["url"], "connect_shawnee.html")})
    conn = _connector(site)
    report = pipeline.run(
        conn,
        _ctx(_fetcher(transport, opt_out_register=register), parameters={"targets": [t_page]}),
    )
    assert not report.captures
    assert transport.request_log == [] and transport.robots_log == []
    assert {r["refusal"] for r in report.refusals} == {"HostOptOut"}


def test_discover_refuses_targets_outside_inventory() -> None:
    """No discovery: an unlisted URL refuses at discover() (SIG-INGEST-045i)."""
    conn = _connector()
    ctx = _ctx(
        _fetcher(FakeTransport({})),
        parameters={"targets": [{"id": "rogue", "url": "https://example.com/rogue"}]},
    )
    with pytest.raises(ValueError, match="not in the committed"):
        conn.discover(ctx)


def test_replay_rederives_without_fetch() -> None:
    """Post-capture stages are pure functions of the screened capture."""
    site = _site()
    t_page, _ = _site_targets(site)
    transport = FakeTransport({t_page["url"]: _served(t_page["url"], "connect_shawnee.html")})
    conn = _connector(site)
    ctx = _ctx(_fetcher(transport), parameters={"targets": [t_page]})
    report = pipeline.run(conn, ctx)
    capture = report.captures[0]
    before = list(transport.request_log)
    claims = replay(_connector(site), dataclasses.replace(ctx, fetcher=None), [capture])
    assert transport.request_log == before
    assert {c.get("predicate_id") for c in claims} == {
        c.get("predicate_id") for c in report.claims if c.get("record_kind") == "claim"
    }


def test_capture_refuses_unscreened_bytes() -> None:
    """capture() never persists bytes fetch() never screened — fail-closed."""
    conn = _connector()
    ctx = _ctx(_fetcher(FakeTransport({})))
    foreign = FetchResult(
        url="https://nowhere.example/",
        status=200,
        body=b"<html></html>",
        media_type="text/html",
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    with pytest.raises(ValueError, match="no screened artifact"):
        conn.capture(ctx, foreign)


def test_no_circumvention_anywhere() -> None:
    """SIG-INGEST-013/036/037: no browser automation, proxy, or challenge-solving."""
    src = inspect.getsource(connectors.axon_connect)
    forbidden = re.compile(
        r"playwright|selenium|puppeteer|undetected|cloudscraper|"
        r"headless|proxy_rotate|rotate_proxy|import requests|import httpx|"
        r"urllib\.request|cookie",
        re.I,
    )
    assert not forbidden.search(src), forbidden.search(src)


def test_egress_only_through_shared_seam() -> None:
    """The connector holds no transport/HTTP client — ctx.fetcher only."""
    init_src = inspect.getsource(AxonConnectConnector.__init__)
    assert "transport" not in init_src
    assert "PoliteFetcher(" not in init_src


def test_emitted_predicates_are_allowlisted_and_registered() -> None:
    """Every predicate the connector may write is allowlisted + registry-bound."""
    allowlist = predicate_allowlist()
    assert allowlist == {
        "camera_registration_portal",
        "camera_registry_publisher",
        "agency_name",
        "portal_stated_prohibited_use",
    }
    site = _site()
    t_page, t_screen = _site_targets(site)
    report, conn, _ = _run(
        {
            t_page["url"]: _served(t_page["url"], "connect_shawnee.html"),
            t_screen["url"]: _served(t_screen["url"], "faststream_login.html"),
        },
        site,
        targets=[t_page, t_screen],
    )
    for c in report.claims:
        if c.get("record_kind") == "claim":
            assert c["predicate_id"] in allowlist
