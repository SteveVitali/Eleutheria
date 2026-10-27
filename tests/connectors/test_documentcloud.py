# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.77 — the DocumentCloud / MuckRock released-materials connector.

Every acceptance criterion is pinned here against committed fixtures — NO
network: a FakeTransport serves the canned pages and a PoliteFetcher over it
exercises the real opt-out / robots / challenge machinery. Both source rows
stay ingestion_permitted=false; tests permit them on in-memory copies
exactly like the axon_connect tests.

Covered: the committed inventory's invariants (public surfaces only, sorted,
https); the rendition model (allowlisted fields kept, Part VIII-screened
candidates dropped to redacted_fields with name + classes + value hash,
denied payload names in refused_fields, uploader-page linkage + original
sha256 on every record); the verbatim terms capture (SIG-LIC-004a); the
recorded refusal for an unreliable redaction (never raw bytes); the
non-public-surface refusals (access != public, credential URLs, private
endpoints, off-inventory discovery); the loader gate refusing both sources;
and the "no circumvention, no discovery, no live egress in the default
path" guards.
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
from connectors.documentcloud import (
    REFUSAL_SCHEMA,
    RENDITION_SCHEMA,
    TERMS_SCHEMA,
    DocumentCloudConnector,
    PredicateNotAllowed,
    ReleaseTarget,
    _url_is_public_surface,
    documentcloud_targets,
    load_inventory,
    load_screen_declaration,
    parse_api_document,
    parse_public_page,
    parse_terms_page,
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
from evidence.screen import Rule, ScreenDeclaration, declaration_from_table

import connectors
from connectors import pipeline

_FIX = Path(__file__).parent / "fixtures" / "documentcloud"
_DATA = Path(__file__).parents[2] / "connectors" / "src" / "connectors" / "data"
_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"
_DC_DOC_URL = "https://api.www.documentcloud.org/api/documents/26182924/"
_DC_PAGE_URL = (
    "https://www.documentcloud.org/documents/"
    "26182924-pittsboro-police-department-flock-safety-shared-devices-list/"
)
_MR_PAGE_URL = (
    "https://www.muckrock.com/foi/los-angeles-91/"
    "automated-license-plate-readers-los-angeles-police-department-136412/"
)


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


def _served(url: str, fixture: str, media_type: str = "text/html", **kw: Any) -> FetchResult:
    return FetchResult(
        url=url,
        status=200,
        body=_fixture_bytes(fixture),
        media_type=media_type,
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        **kw,
    )


def _target(target_id: str) -> ReleaseTarget:
    t = load_inventory().get(target_id)
    assert t is not None
    return t


def _connector(**kw: Any) -> DocumentCloudConnector:
    return DocumentCloudConnector(**kw)


def _ctx(
    fetcher: Any,
    *,
    source_id: str = "documentcloud",
    parameters: dict[str, Any] | None = None,
) -> RunContext:
    # The registry rows stay ingestion_permitted=false; a reviewer flips them —
    # the tests exercise the connector on a permitted COPY (SIG-INGEST-028
    # stays exercised by the gate tests below).
    source = dataclasses.replace(get(source_id), ingestion_permitted=True)
    return RunContext(
        source=source,
        run=IngestRun("documentcloud", "1.0.0", "deadbeef", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters=parameters or {},
    )


def _fetcher(transport: FakeTransport, **kw: Any) -> PoliteFetcher:
    return PoliteFetcher(
        connector_name="documentcloud",
        connector_version="1.0.0",
        transport=transport,
        rate_limiter=RateLimiter(sleep=lambda s: None),
        **kw,
    )


def _run(
    pages: dict[str, FetchResult],
    targets: list[dict[str, Any]],
    *,
    source_id: str = "documentcloud",
    connector: DocumentCloudConnector | None = None,
    **fetcher_kw: Any,
) -> tuple[Any, DocumentCloudConnector, FakeTransport]:
    """End-to-end pipeline run over canned pages — zero network."""
    transport = FakeTransport(pages)
    conn = connector or _connector()
    ctx = _ctx(
        _fetcher(transport, **fetcher_kw), source_id=source_id, parameters={"targets": targets}
    )
    report = pipeline.run(conn, ctx)
    return report, conn, transport


def _tg(target_id: str) -> dict[str, Any]:
    row = _target(target_id)
    return {"id": row.id, "url": row.url, "kind": row.kind, "source": row.source}


# --- the committed seed inventory (data invariants) ------------------------------


def test_inventory_count_sort_and_shape() -> None:
    """Eleven committed seeds, sorted, https-only, public surfaces only."""
    inv = load_inventory()
    assert len(inv.targets) == 11
    ids = [t.id for t in inv.targets]
    assert ids == sorted(ids)
    kinds = {t.kind for t in inv.targets}
    assert kinds == {
        "api_document",
        "api_project",
        "document_page",
        "project_page",
        "muckrock_page",
        "terms_page",
    }
    for t in inv.targets:
        parts = urlsplit(t.url)
        assert parts.scheme == "https"
        assert not parts.username and not parts.query and not parts.fragment
        assert parts.netloc in {
            "api.www.documentcloud.org",
            "www.documentcloud.org",
            "www.muckrock.com",
        }
        assert t.evidence and (t.expect or t.kind == "terms_page")
        assert _url_is_public_surface(t.url, kind=t.kind, platform=t.platform)
    # Identifiers + provenance only — no content columns on the rows.
    table = tomllib.loads((_DATA / "documentcloud_targets.toml").read_text("utf-8"))
    assert table["schema"] == "sig.documentcloud-targets/1"
    for row in table["inventory"]["targets"]:
        assert set(row) <= {
            "id",
            "source",
            "platform",
            "kind",
            "url",
            "document_id",
            "expect",
            "evidence",
        }


def test_live_targets_scope_per_source() -> None:
    dc = documentcloud_targets("documentcloud")
    mrp = documentcloud_targets("muckrock_public")
    assert len(dc) == 10 and len(mrp) == 1
    assert mrp[0]["url"] == _MR_PAGE_URL


def test_inventory_validation_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """A malformed inventory refuses to load (unsorted/duplicate/count-lying/non-public)."""
    real = load_inventory()
    from connectors._data import load_table as _real_load_table

    def _broken_count() -> dict[str, Any]:
        table = tomllib.loads((_DATA / "documentcloud_targets.toml").read_text("utf-8"))
        table["inventory"]["target_count"] = 99
        return table

    monkeypatch.setattr(
        "connectors.documentcloud.load_table",
        lambda name: _broken_count() if name == "documentcloud_targets" else _real_load_table(name),
    )
    with pytest.raises(ValueError, match="target_count"):
        load_inventory()
    assert len(real.targets) == 11


def test_public_surface_invariant_refuses_private_paths() -> None:
    """A non-public path is never a fetchable surface — fail-closed at both seams."""
    bad = [
        # the authenticated api_v2 endpoint — never a public page
        "https://www.muckrock.com/api_v2/requests/136412/",
        # credential-bearing URL
        "https://user:pass@www.documentcloud.org/documents/26182924-x/",
        # query/fragment-bearing
        "https://api.www.documentcloud.org/api/documents/26182924/?key=abc",
        # http only
        "http://www.documentcloud.org/documents/26182924-x/",
        # uncommitted host
        "https://example.com/documents/26182924-x/",
        # a private account path on a committed host
        "https://www.documentcloud.org/accounts/login/",
    ]
    for url in bad:
        assert not _url_is_public_surface(url, kind="document_page", platform="documentcloud")
        assert not _url_is_public_surface(url, kind="muckrock_page", platform="muckrock")


def test_registry_rows_stay_gated() -> None:
    """Both sources stay OFF — leg B's flip is the operator's act (OP-26/HG-03)."""
    dc = get("documentcloud")
    mrp = get("muckrock_public")
    assert dc.ingestion_permitted is False
    assert mrp.ingestion_permitted is False
    assert mrp.custody_posture.value == "DERIVE"
    assert CONNECTOR_FOR_SOURCE["documentcloud"] == "documentcloud"
    assert CONNECTOR_FOR_SOURCE["muckrock_public"] == "documentcloud"
    # The loader gate stands: the committed rows refuse before any fetch.
    for source in (dc, mrp):
        unpermitted_ctx = RunContext(
            source=source,
            run=IngestRun("documentcloud", "1.0.0", "deadbeef", "r1", "v1", ()),
            fetcher=None,
            captures=InMemoryCaptureStore(),
            claim_sink=InMemoryClaimSink(),
        )
        with pytest.raises(IngestionNotPermitted):
            pipeline.run(_connector(), unpermitted_ctx)


# --- the rendition model (pure over committed fixtures) ----------------------------


def test_api_document_rendition_redacts_and_preserves() -> None:
    """The released-document record: allowlisted fields + redaction provenance."""
    t = _target("dc-api-26182924")
    rec, reason = parse_api_document(
        _fixture_bytes("api_doc_26182924.json"),
        target=t,
        retrieved_at="2026-10-01T00:00:00Z",
        decl=load_screen_declaration(),
    )
    assert reason == "" and rec["schema"] == RENDITION_SCHEMA
    # The uploader's public page + the original's digest ride the record.
    assert rec["uploader_page"] == _DC_PAGE_URL
    assert len(rec["original_sha256"]) == 64 and rec["original_bytes"] > 0
    # Allowlisted structural fields land verbatim.
    f = rec["fields"]
    assert f["id"] == "26182924" and f["access"] == "public"
    assert f["title"].startswith("Pittsboro Police Department")
    assert f["organization_name"] == "MuckRock News"
    # Person-named + free-text candidates dropped — name + classes + value hash,
    # never the value.
    redacted = {r["field"]: r for r in rec["redacted_fields"]}
    assert redacted["contributor"]["classes"] == ["I7-S7"]
    assert redacted["description"]["classes"] == ["I7-S6"]
    assert redacted["source"]["classes"] == ["I7-S6"]
    blob = json.dumps(rec)
    assert "Jane Doe" not in blob and "officer" not in blob


def test_document_page_rendition_meta_only() -> None:
    """The uploader page's rendition: meta/title + refused payload names only."""
    t = _target("dc-page-26182924")
    rec, reason = parse_public_page(
        _fixture_bytes("doc_page_26182924.html"),
        target=t,
        retrieved_at="2026-10-01T00:00:00Z",
        decl=load_screen_declaration(),
    )
    assert reason == "" and rec["schema"] == RENDITION_SCHEMA
    assert rec["uploader_page"] == _DC_PAGE_URL
    assert "uploader_email" in rec["refused_fields"]  # denied name — never a value
    assert "jane.doe@example.org" not in json.dumps(rec)
    redacted = {r["field"] for r in rec["redacted_fields"]}
    assert {"description", "author"} <= redacted


def test_muckrock_page_status_marker() -> None:
    t = _target("mr-page-136412")
    rec, reason = parse_public_page(
        _fixture_bytes("muckrock_page_136412.html"),
        target=t,
        retrieved_at="2026-10-01T00:00:00Z",
        decl=load_screen_declaration(),
    )
    assert reason == ""
    assert rec["source"] == "muckrock_public"
    assert rec["fields"]["status_marker"] == "completed"
    assert rec["uploader_page"] == _MR_PAGE_URL


def test_terms_page_verbatim_capture() -> None:
    """SIG-LIC-004a: the platform terms text lands verbatim + digest-pinned."""
    t = _target("dc-terms-tos")
    rec, reason = parse_terms_page(
        _fixture_bytes("tos_page.html"),
        target=t,
        retrieved_at="2026-10-01T00:00:00Z",
        decl=load_screen_declaration(),
    )
    assert reason == "" and rec["schema"] == TERMS_SCHEMA
    assert "data mining, robots, or similar data" in rec["terms_text"]
    assert len(rec["terms_sha256"]) == 64
    assert rec["terms_truncated"] is False


def test_non_public_access_refuses() -> None:
    """An access!=public API record is not a public surface — refused whole."""
    t = _target("dc-api-26182924")
    private = json.dumps({"id": 26182924, "access": "private"}).encode()
    with pytest.raises(Exception, match="not a public"):
        parse_api_document(private, target=t, retrieved_at=None, decl=load_screen_declaration())


def test_wrong_seed_page_refused() -> None:
    """A page contradicting the committed seed is refused — never guessed."""
    t = _target("dc-page-26182924")
    with pytest.raises(Exception, match="expect"):
        parse_public_page(
            _fixture_bytes("not_the_seed.html"),
            target=t,
            retrieved_at=None,
            decl=load_screen_declaration(),
        )


# --- the recorded refusal (no reliable redaction → never raw bytes) ----------------


def _dirty_screen() -> ScreenDeclaration:
    """A declaration flagging ``uploader_page`` — makes every rendition dirty.

    Augments the committed I7-S7 class (already a member of the rendition
    lanes) with a ``uploader_page`` field rule so the finished rendition
    record screens dirty — the honest ``unreliable_redaction`` trigger.
    """
    base = declaration_from_table(
        tomllib.loads(Path("ops/at_rest_audit.toml").read_text("utf-8")),
        source="test",
    )
    classes = []
    for c in base.classes:
        if c.class_id == "I7-S7":
            c = dataclasses.replace(
                c,
                rules=tuple(c.rules) + (Rule(kind="fields", fields=("uploader_page",)),),
            )
        classes.append(c)
    return dataclasses.replace(base, classes=tuple(classes))


def test_unreliable_redaction_persists_refusal_record() -> None:
    """A rendition that cannot screen clean persists the refusal — never raw."""
    conn = _connector(screen=_dirty_screen())
    transport = FakeTransport(
        {_DC_DOC_URL: _served(_DC_DOC_URL, "api_doc_26182924.json", "application/json")}
    )
    ctx = _ctx(_fetcher(transport), parameters={"targets": [_tg("dc-api-26182924")]})
    report = pipeline.run(conn, ctx)
    # The refusal RECORD is the persisted artifact — the rendition never was.
    assert len(report.captures) == 1
    stored = json.loads(ctx.captures.get(report.captures[0].digest).decode("utf-8"))
    assert stored["schema"] == REFUSAL_SCHEMA
    assert stored["reason"] == "unreliable_redaction"
    assert stored["uploader_page"] == _DC_PAGE_URL
    assert b"Jane Doe" not in ctx.captures.get(report.captures[0].digest)
    o = conn.outcomes[0]
    assert o["result"] == "refusal_recorded" and o["refusal_kind"] == "unreliable_redaction"
    assert o["result"] == "refusal_recorded" and o["refusal_kind"] == "unreliable_redaction"
    assert o["screen_hits"]
    assert len(transport.request_log) == 1


def test_capture_refusal_row_is_counts_only() -> None:
    """The emitted refusal row: pointer + classes + counts + hash, no content."""
    conn = _connector(screen=_dirty_screen())
    report, conn, _ = _run(
        {_DC_DOC_URL: _served(_DC_DOC_URL, "api_doc_26182924.json", "application/json")},
        [_tg("dc-api-26182924")],
        connector=conn,
    )
    rows = [c for c in report.claims if c.get("record_kind") == "capture_refusal"]
    assert len(rows) == 1
    row = rows[0]
    assert row["reason"] == "unreliable_redaction"
    assert row["original_sha256"] and row["upstream_url"] == _DC_DOC_URL
    blob = json.dumps(row, default=str)
    assert "Jane Doe" not in blob and "Shared Devices" not in blob


# --- the served path end-to-end -----------------------------------------------------


def test_captured_bytes_are_records_never_served() -> None:
    """capture() persists the screened records — NEVER the served bytes."""
    pages = {
        _DC_DOC_URL: _served(_DC_DOC_URL, "api_doc_26182924.json", "application/json"),
        _DC_PAGE_URL: _served(_DC_PAGE_URL, "doc_page_26182924.html"),
        _MR_PAGE_URL: _served(_MR_PAGE_URL, "muckrock_page_136412.html"),
    }
    targets = [_tg("dc-api-26182924"), _tg("dc-page-26182924"), _tg("mr-page-136412")]
    transport = FakeTransport(pages)
    conn = _connector()
    ctx = _ctx(_fetcher(transport), source_id="documentcloud", parameters={"targets": targets})
    report = pipeline.run(conn, ctx)
    assert len(report.captures) == 3
    for c in report.captures:
        blob = ctx.captures.get(c.digest)
        rec = json.loads(blob.decode("utf-8"))
        assert rec["schema"] == RENDITION_SCHEMA
        assert b"<html" not in blob and "description" not in rec.get("fields", {})
    assert len(transport.request_log) == 3  # exactly ONE GET per bounded target


def test_claims_link_the_uploaders_page() -> None:
    """Every claim carries the uploader's public page URL — the ticket's rule."""
    report, conn, _ = _run(
        {_DC_DOC_URL: _served(_DC_DOC_URL, "api_doc_26182924.json", "application/json")},
        [_tg("dc-api-26182924")],
    )
    claims = [c for c in report.claims if c.get("record_kind") == "claim"]
    assert claims
    for c in claims:
        assert c["uploader_page"] == _DC_PAGE_URL
        assert c["source_id"] == "documentcloud"
        assert c["ai_training_permitted"] is False
    preds = {c["predicate_id"] for c in claims}
    assert {"platform", "acquisition_method", "title"} <= preds
    # The index row + the artifact row.
    kinds = {c.get("record_kind") for c in report.claims}
    assert "document_index" in kinds and "evidence_artifact" in kinds
    idx = next(c for c in report.claims if c.get("record_kind") == "document_index")
    assert idx["predicate_id"] == "released_documents"
    assert idx["integrity"] == "screened_rendition"
    art = next(c for c in report.claims if c.get("record_kind") == "evidence_artifact")
    assert art["integrity"] == "screened_rendition"
    # No person bytes on the wire.
    blob = json.dumps(report.claims, default=str)
    assert "Jane Doe" not in blob


def test_terms_capture_row() -> None:
    """The SIG-TRANSP-004 terms row: URL + digest + capture date."""
    t = _target("dc-terms-tos")
    report, conn, _ = _run(
        {t.url: _served(t.url, "tos_page.html")},
        [_tg("dc-terms-tos")],
    )
    rows = [c for c in report.claims if c.get("record_kind") == "terms_capture"]
    assert len(rows) == 1
    row = rows[0]
    assert row["terms_url"] == "https://www.muckrock.com/tos/"
    assert len(row["terms_sha256"]) == 64 and row["captured_at"]


def test_project_index_is_collection_not_documents() -> None:
    """A project rendition is a collection_index — member names never extracted."""
    t = _target("dc-api-209393")
    report, conn, _ = _run(
        {t.url: _served(t.url, "api_project_209393.json", "application/json")},
        [_tg("dc-api-209393")],
    )
    rows = [c for c in report.claims if c.get("record_kind") == "collection_index"]
    assert len(rows) == 1
    row = rows[0]
    assert row["uploader_page"].endswith("fog-data-science-public-209393/")
    # Member document ids never surface as claims.
    blob = json.dumps(report.claims, default=str)
    for member in ("24501234", "24501235", "24501236"):
        assert member not in blob


def test_muckrock_source_attribution() -> None:
    """A muckrock_public rendition stamps its own source id — never the DC row's."""
    t = _target("mr-page-136412")
    report, conn, _ = _run(
        {t.url: _served(t.url, "muckrock_page_136412.html")},
        [_tg("mr-page-136412")],
        source_id="muckrock_public",
    )
    for c in report.claims:
        assert c["source_id"] == "muckrock_public"


def test_challenge_and_disappearances_recorded() -> None:
    """A 403 ends the target's attempt — recorded, never retried (SIG-INGEST-037)."""
    report, conn, transport = _run(
        {
            _DC_DOC_URL: FetchResult(
                url=_DC_DOC_URL,
                status=403,
                body=b"Forbidden",
                media_type="text/html",
                retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
            _DC_PAGE_URL: _served(_DC_PAGE_URL, "doc_page_26182924.html"),
        },
        [_tg("dc-api-26182924"), _tg("dc-page-26182924")],
    )
    refusal = next(o for o in conn.outcomes if o["result"] == "refused")
    assert refusal["refusal_kind"] == "challenge" and refusal["status"] == 403
    assert {d.event.failing_status for d in report.disappearances} == {"access_restricted"}
    # The page target still captured — one target's refusal never aborts.
    assert len(report.captures) == 1
    assert len(transport.request_log) == 2


def test_interstitial_2xx_is_a_recorded_challenge() -> None:
    report, conn, _ = _run(
        {_DC_PAGE_URL: _served(_DC_PAGE_URL, "interstitial.html")},
        [_tg("dc-page-26182924")],
    )
    assert not report.captures
    assert conn.outcomes[0]["refusal_kind"] == "interstitial"
    assert {d.event.failing_status for d in report.disappearances} == {"access_restricted"}


def test_host_optout_zero_egress() -> None:
    """The host-level register (§26 rule 7) is consulted before any egress."""
    register = OptOutRegister(
        entries=(
            OptOutEntry(host="www.documentcloud.org", recorded_on=date(2026, 10, 1), evidence="t"),
        )
    )
    transport = FakeTransport({_DC_PAGE_URL: _served(_DC_PAGE_URL, "doc_page_26182924.html")})
    conn = _connector()
    report = pipeline.run(
        conn,
        _ctx(
            _fetcher(transport, opt_out_register=register),
            parameters={"targets": [_tg("dc-page-26182924")]},
        ),
    )
    assert not report.captures
    assert transport.request_log == [] and transport.robots_log == []
    assert {r["refusal"] for r in report.refusals} == {"HostOptOut"}


def test_target_optout_zero_egress() -> None:
    """§26 rule 7 at target granularity — the committed opted_out_targets column."""
    inv = load_inventory()
    opted = {t.id for t in inv.targets if t.id == "dc-page-26182924"}
    inv2 = dataclasses.replace(
        inv,
        targets=tuple(dataclasses.replace(t, opted_out=t.id in opted) for t in inv.targets),
    )
    conn = _connector(inventory=inv2)
    transport = FakeTransport({_DC_PAGE_URL: _served(_DC_PAGE_URL, "doc_page_26182924.html")})
    report = pipeline.run(
        conn,
        _ctx(_fetcher(transport), parameters={"targets": [_tg("dc-page-26182924")]}),
    )
    assert not report.captures
    assert transport.request_log == []
    assert {o["refusal_kind"] for o in conn.outcomes} == {"opted_out"}


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
    transport = FakeTransport(
        {_DC_DOC_URL: _served(_DC_DOC_URL, "api_doc_26182924.json", "application/json")}
    )
    conn = _connector()
    ctx = _ctx(_fetcher(transport), parameters={"targets": [_tg("dc-api-26182924")]})
    report = pipeline.run(conn, ctx)
    capture = report.captures[0]
    before = list(transport.request_log)
    claims = replay(_connector(), dataclasses.replace(ctx, fetcher=None), [capture])
    assert transport.request_log == before
    assert {c.get("predicate_id") for c in claims if c.get("predicate_id")} == {
        c.get("predicate_id") for c in report.claims if c.get("predicate_id")
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


def test_emitted_fact_with_denied_field_fails_loud() -> None:
    """A denied field name in emitted facts raises — never a warning."""
    conn = _connector()
    ctx = _ctx(_fetcher(FakeTransport({})))
    bad = [
        {
            "record_kind": "documentcloud_rendition",
            "schema": RENDITION_SCHEMA,
            "uploader_page": "u",
            "contact_email": "x@y",
        }
    ]
    with pytest.raises(PredicateNotAllowed, match="denied"):
        conn.normalize(ctx, bad)


def test_no_circumvention_anywhere() -> None:
    """SIG-INGEST-013/036/037: no browser automation, proxy, or challenge-solving."""
    src = inspect.getsource(connectors.documentcloud)
    forbidden = re.compile(
        r"playwright|selenium|puppeteer|undetected|cloudscraper|"
        r"headless|proxy_rotate|rotate_proxy|import requests|import httpx|"
        r"urllib\.request|cookie|api_key|authorization",
        re.I,
    )
    assert not forbidden.search(src), forbidden.search(src)


def test_egress_only_through_shared_seam() -> None:
    """The connector holds no transport/HTTP client — ctx.fetcher only."""
    init_src = inspect.getsource(DocumentCloudConnector.__init__)
    assert "transport" not in init_src
    assert "PoliteFetcher(" not in init_src


def test_emitted_predicates_are_allowlisted() -> None:
    """Every predicate the connector may write is allowlisted + ontology-bound."""
    allowlist = predicate_allowlist()
    assert allowlist == {
        "released_documents",
        "platform",
        "acquisition_method",
        "title",
    }
    report, conn, _ = _run(
        {_DC_DOC_URL: _served(_DC_DOC_URL, "api_doc_26182924.json", "application/json")},
        [_tg("dc-api-26182924")],
    )
    for c in report.claims:
        if c.get("record_kind") in {
            "claim",
            "document_index",
            "collection_index",
            "evidence_artifact",
        }:
            assert c["predicate_id"] in allowlist
