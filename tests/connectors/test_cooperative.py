# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.78 — the Sourcewell + OMNIA Partners cooperative contract-page connector.

Every acceptance criterion is pinned here against committed fixtures — NO
network: a FakeTransport serves the canned pages and a PoliteFetcher over it
exercises the real opt-out / robots / challenge machinery. Both source rows
stay ingestion_permitted=false; tests permit them on in-memory copies
exactly like the documentcloud tests.

Covered: the committed inventory's invariants (public unauthenticated
surfaces only, sorted, https); the rendition model (allowlisted fields kept,
Part VIII-screened candidates dropped to redacted_fields with name +
classes + value hash, denied payload names in refused_fields, contract-page
linkage + original sha256 on every record); the verbatim terms capture
(SIG-LIC-004a / SIG-TRANSP-004); the contract subject the master award
carries (candidate, never resolved); the recorded refusal for an unreliable
redaction (never raw bytes); the non-public-surface refusals (credential
URLs, member/private paths, unvetted hosts, off-inventory discovery); the
member-gated documents being pointers only; the loader gate refusing both
sources; and the "no circumvention, no discovery, no live egress in the
default path" guards.
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
from connectors.cooperative import (
    REFUSAL_SCHEMA,
    RENDITION_SCHEMA,
    TERMS_SCHEMA,
    ContractTarget,
    CooperativeConnector,
    PredicateNotAllowed,
    _url_is_public_surface,
    cooperative_targets,
    load_inventory,
    load_screen_declaration,
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

_FIX = Path(__file__).parent / "fixtures" / "cooperative"
_DATA = Path(__file__).parents[2] / "connectors" / "src" / "connectors" / "data"
_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"
_SW_CONTRACT_URL = "https://www.sourcewell-mn.gov/cooperative-purchasing/101223-axn"
_SW_TERMS_URL = "https://www.sourcewell-mn.gov/terms-use"
_OP_SUPPLIER_URL = "https://www.omniapartners.com/suppliers/flock-safety"
_OP_DOCS_URL = "https://www.omniapartners.com/suppliers/gaggle/public-sector/contract-documents"
_OP_TERMS_URL = "https://www.omniapartners.com/terms-of-use"


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


def _target(target_id: str) -> ContractTarget:
    t = load_inventory().get(target_id)
    assert t is not None
    return t


def _connector(**kw: Any) -> CooperativeConnector:
    return CooperativeConnector(**kw)


def _ctx(
    fetcher: Any,
    *,
    source_id: str = "sourcewell",
    parameters: dict[str, Any] | None = None,
) -> RunContext:
    # The registry rows stay ingestion_permitted=false; a reviewer flips them —
    # the tests exercise the connector on a permitted COPY (SIG-INGEST-028
    # stays exercised by the gate tests below).
    source = dataclasses.replace(get(source_id), ingestion_permitted=True)
    return RunContext(
        source=source,
        run=IngestRun("cooperative", "1.0.0", "deadbeef", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters=parameters or {},
    )


def _fetcher(transport: FakeTransport, **kw: Any) -> PoliteFetcher:
    return PoliteFetcher(
        connector_name="cooperative",
        connector_version="1.0.0",
        transport=transport,
        rate_limiter=RateLimiter(sleep=lambda s: None),
        **kw,
    )


def _run(
    pages: dict[str, FetchResult],
    targets: list[dict[str, Any]],
    *,
    source_id: str = "sourcewell",
    connector: CooperativeConnector | None = None,
    **fetcher_kw: Any,
) -> tuple[Any, CooperativeConnector, FakeTransport]:
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
    """Five committed seeds, sorted, https-only, public surfaces only."""
    inv = load_inventory()
    assert len(inv.targets) == 5
    ids = [t.id for t in inv.targets]
    assert ids == sorted(ids)
    kinds = {t.kind for t in inv.targets}
    assert kinds == {
        "contract_page",
        "supplier_page",
        "contract_documents_page",
        "sw_terms_page",
        "om_terms_page",
    }
    for t in inv.targets:
        parts = urlsplit(t.url)
        assert parts.scheme == "https"
        assert not parts.username and not parts.query and not parts.fragment
        assert parts.netloc in {"www.sourcewell-mn.gov", "www.omniapartners.com"}
        assert t.evidence and (t.expect or t.kind in {"sw_terms_page", "om_terms_page"})
        assert _url_is_public_surface(t.url, kind=t.kind, platform=t.platform)
    # Identifiers + provenance only — no content columns on the rows.
    table = tomllib.loads((_DATA / "cooperative_targets.toml").read_text("utf-8"))
    assert table["schema"] == "sig.cooperative-targets/1"
    for row in table["inventory"]["targets"]:
        assert set(row) <= {
            "id",
            "source",
            "platform",
            "kind",
            "url",
            "contract_id",
            "expect",
            "evidence",
        }


def test_live_targets_scope_per_source() -> None:
    sw = cooperative_targets("sourcewell")
    op = cooperative_targets("omnia_partners")
    assert len(sw) == 2 and len(op) == 3
    assert {t["url"] for t in sw} == {_SW_CONTRACT_URL, _SW_TERMS_URL}
    assert _OP_SUPPLIER_URL in {t["url"] for t in op}


def test_inventory_validation_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """A malformed inventory refuses to load (count-lying, non-public, off-source)."""
    real = load_inventory()
    from connectors._data import load_table as _real_load_table

    def _broken_count() -> dict[str, Any]:
        table = tomllib.loads((_DATA / "cooperative_targets.toml").read_text("utf-8"))
        table["inventory"]["target_count"] = 99
        return table

    monkeypatch.setattr(
        "connectors.cooperative.load_table",
        lambda name: _broken_count() if name == "cooperative_targets" else _real_load_table(name),
    )
    with pytest.raises(ValueError, match="target_count"):
        load_inventory()
    assert len(real.targets) == 5


def test_public_surface_invariant_refuses_private_paths() -> None:
    """A non-public path is never a fetchable surface — fail-closed at both seams."""
    bad = [
        # credential-bearing URL
        "https://user:pass@www.sourcewell-mn.gov/cooperative-purchasing/101223-axn",
        # query/fragment-bearing
        "https://www.omniapartners.com/suppliers/flock-safety?key=abc",
        # http only
        "http://www.sourcewell-mn.gov/cooperative-purchasing/101223-axn",
        # uncommitted host
        "https://example.com/cooperative-purchasing/101223-axn",
        "https://files.sourcewell.org/101223-axn/contract.pdf",
        # a member/private path on a committed host
        "https://www.sourcewell-mn.gov/member/login",
        "https://www.omniapartners.com/account/dashboard",
        # the wrong kind's path
        "https://www.omniapartners.com/cooperative-purchasing/101223-axn",
    ]
    for url in bad:
        for kind, platform in (
            ("contract_page", "sourcewell"),
            ("supplier_page", "omnia"),
            ("contract_documents_page", "omnia"),
        ):
            assert not _url_is_public_surface(url, kind=kind, platform=platform), url


def test_registry_rows_stay_gated() -> None:
    """Both sources stay OFF — leg B's flip is the operator's act (OP-26/HG-03)."""
    sw = get("sourcewell")
    op = get("omnia_partners")
    assert sw.ingestion_permitted is False
    assert op.ingestion_permitted is False
    assert CONNECTOR_FOR_SOURCE["sourcewell"] == "cooperative"
    assert CONNECTOR_FOR_SOURCE["omnia_partners"] == "cooperative"
    # The loader gate stands: the committed rows refuse before any fetch.
    for source in (sw, op):
        unpermitted_ctx = RunContext(
            source=source,
            run=IngestRun("cooperative", "1.0.0", "deadbeef", "r1", "v1", ()),
            fetcher=None,
            captures=InMemoryCaptureStore(),
            claim_sink=InMemoryClaimSink(),
        )
        with pytest.raises(IngestionNotPermitted):
            pipeline.run(_connector(), unpermitted_ctx)


# --- the rendition model (pure over committed fixtures) ----------------------------


def test_contract_page_rendition_redacts_and_preserves() -> None:
    """The master-award record: allowlisted fields + redaction provenance."""
    t = _target("sw-contract-101223-axn")
    rec, reason = parse_public_page(
        _fixture_bytes("sw_contract_101223_axn.html"),
        target=t,
        retrieved_at="2026-10-01T00:00:00Z",
        decl=load_screen_declaration(),
    )
    assert reason == "" and rec["schema"] == RENDITION_SCHEMA
    # The contract page + the original's digest ride the record.
    assert rec["contract_page"] == _SW_CONTRACT_URL
    assert rec["contract_id"] == "101223-AXN"
    assert len(rec["original_sha256"]) == 64 and rec["original_bytes"] > 0
    f = rec["fields"]
    assert f["collection_kind"] == "sourcewell_contract_page"
    assert f["linked_document_count"] == 4  # pointers counted, never carried
    assert "Axon Enterprise" in f["title"]
    # Person-named + free-text candidates dropped — name + classes + value
    # hash, never the value (the I7-U478 staff-contact name hazard).
    redacted = {r["field"]: r for r in rec["redacted_fields"]}
    assert redacted["author"]["classes"] == ["I7-S7"]
    assert redacted["contact_name"]["classes"] == ["I7-S7"]
    assert redacted["description"]["classes"] == ["I7-S6"]
    # Denied payload names in refused_fields — names, never values.
    assert {"contact_email", "staff_phone"} <= set(rec["refused_fields"])
    blob = json.dumps(rec)
    assert "Jane Sample" not in blob and "jsample@example.org" not in blob


def test_supplier_page_rendition() -> None:
    t = _target("op-supplier-flock")
    rec, reason = parse_public_page(
        _fixture_bytes("op_supplier_flock.html"),
        target=t,
        retrieved_at="2026-10-01T00:00:00Z",
        decl=load_screen_declaration(),
    )
    assert reason == ""
    assert rec["source"] == "omnia_partners"
    assert rec["fields"]["collection_kind"] == "omnia_supplier_page"
    assert rec["contract_page"] == _OP_SUPPLIER_URL
    assert "member_email" in rec["refused_fields"]
    assert "sales@example.org" not in json.dumps(rec)


def test_contract_documents_page_marks_member_gated() -> None:
    """The documents route through a member form — gated, recorded, never submitted."""
    t = _target("op-docs-gaggle")
    rec, reason = parse_public_page(
        _fixture_bytes("op_docs_gaggle.html"),
        target=t,
        retrieved_at="2026-10-01T00:00:00Z",
        decl=load_screen_declaration(),
    )
    assert reason == ""
    assert rec["fields"]["collection_kind"] == "omnia_contract_documents_page"
    assert rec["fields"]["documents_member_gated"] is True
    assert rec["fields"]["linked_document_count"] == 2  # pointers only
    # The member-gated file URLs are never carried.
    blob = json.dumps(rec)
    assert "master-agreement.pdf" not in blob and "exhibit-a.pdf" not in blob


def test_terms_pages_verbatim_capture() -> None:
    """SIG-LIC-004a: the platforms' terms texts land verbatim + digest-pinned."""
    for tid, fixture, needle in (
        ("sw-terms", "sw_terms.html", "robots or spiders"),
        ("op-terms", "op_terms.html", '"scraping," "crawling," harvesting'),
    ):
        t = _target(tid)
        rec, reason = parse_terms_page(
            _fixture_bytes(fixture),
            target=t,
            retrieved_at="2026-10-01T00:00:00Z",
            decl=load_screen_declaration(),
        )
        assert reason == "" and rec["schema"] == TERMS_SCHEMA
        assert needle in rec["terms_text"]
        assert len(rec["terms_sha256"]) == 64
        assert rec["terms_truncated"] is False


def test_wrong_seed_page_refused() -> None:
    """A page contradicting the committed seed is refused — never guessed."""
    t = _target("sw-contract-101223-axn")
    with pytest.raises(Exception, match="expect"):
        parse_public_page(
            _fixture_bytes("not_the_seed.html"),
            target=t,
            retrieved_at=None,
            decl=load_screen_declaration(),
        )


# --- the recorded refusal (no reliable redaction → never raw bytes) ----------------


def _dirty_screen() -> ScreenDeclaration:
    """A declaration flagging ``contract_page`` — makes every rendition dirty."""
    base = declaration_from_table(
        tomllib.loads(Path("ops/at_rest_audit.toml").read_text("utf-8")),
        source="test",
    )
    classes = []
    for c in base.classes:
        if c.class_id == "I7-S7":
            c = dataclasses.replace(
                c,
                rules=tuple(c.rules) + (Rule(kind="fields", fields=("contract_page",)),),
            )
        classes.append(c)
    return dataclasses.replace(base, classes=tuple(classes))


def test_unreliable_redaction_persists_refusal_record() -> None:
    """A rendition that cannot screen clean persists the refusal — never raw."""
    conn = _connector(screen=_dirty_screen())
    transport = FakeTransport(
        {_SW_CONTRACT_URL: _served(_SW_CONTRACT_URL, "sw_contract_101223_axn.html")}
    )
    ctx = _ctx(_fetcher(transport), parameters={"targets": [_tg("sw-contract-101223-axn")]})
    report = pipeline.run(conn, ctx)
    # The refusal RECORD is the persisted artifact — the rendition never was.
    assert len(report.captures) == 1
    stored = json.loads(ctx.captures.get(report.captures[0].digest).decode("utf-8"))
    assert stored["schema"] == REFUSAL_SCHEMA
    assert stored["reason"] == "unreliable_redaction"
    assert stored["contract_page"] == _SW_CONTRACT_URL
    assert b"Jane Sample" not in ctx.captures.get(report.captures[0].digest)
    o = conn.outcomes[0]
    assert o["result"] == "refusal_recorded" and o["refusal_kind"] == "unreliable_redaction"
    assert o["screen_hits"]
    assert len(transport.request_log) == 1


def test_capture_refusal_row_is_counts_only() -> None:
    """The emitted refusal row: pointer + classes + counts + hash, no content."""
    conn = _connector(screen=_dirty_screen())
    report, conn, _ = _run(
        {_SW_CONTRACT_URL: _served(_SW_CONTRACT_URL, "sw_contract_101223_axn.html")},
        [_tg("sw-contract-101223-axn")],
        connector=conn,
    )
    rows = [c for c in report.claims if c.get("record_kind") == "capture_refusal"]
    assert len(rows) == 1
    row = rows[0]
    assert row["reason"] == "unreliable_redaction"
    assert row["original_sha256"] and row["upstream_url"] == _SW_CONTRACT_URL
    blob = json.dumps(row, default=str)
    assert "Jane Sample" not in blob and "Axon Enterprise" not in blob


# --- the served path end-to-end -----------------------------------------------------


def test_captured_bytes_are_records_never_served() -> None:
    """capture() persists the screened records — NEVER the served bytes."""
    pages = {
        _SW_CONTRACT_URL: _served(_SW_CONTRACT_URL, "sw_contract_101223_axn.html"),
        _OP_SUPPLIER_URL: _served(_OP_SUPPLIER_URL, "op_supplier_flock.html"),
        _OP_DOCS_URL: _served(_OP_DOCS_URL, "op_docs_gaggle.html"),
    }
    targets = [_tg("sw-contract-101223-axn"), _tg("op-supplier-flock"), _tg("op-docs-gaggle")]
    transport = FakeTransport(pages)
    conn = _connector()
    ctx = _ctx(_fetcher(transport), source_id="sourcewell", parameters={"targets": targets})
    report = pipeline.run(conn, ctx)
    assert len(report.captures) == 3
    for c in report.captures:
        blob = ctx.captures.get(c.digest)
        rec = json.loads(blob.decode("utf-8"))
        assert rec["schema"] == RENDITION_SCHEMA
        assert b"<html" not in blob and "description" not in rec.get("fields", {})
    assert len(transport.request_log) == 3  # exactly ONE GET per bounded target


def test_claims_link_the_contract_page() -> None:
    """Every claim carries the cooperative's public contract page — the rule."""
    report, conn, _ = _run(
        {_SW_CONTRACT_URL: _served(_SW_CONTRACT_URL, "sw_contract_101223_axn.html")},
        [_tg("sw-contract-101223-axn")],
    )
    claims = [c for c in report.claims if c.get("record_kind") == "claim"]
    assert claims
    for c in claims:
        assert c["contract_page"] == _SW_CONTRACT_URL
        assert c["source_id"] == "sourcewell"
        assert c["ai_training_permitted"] is False
    preds = {c["predicate_id"] for c in claims}
    assert {
        "contract",
        "contract_number",
        "external_id",
        "platform",
        "acquisition_method",
        "title",
    } <= preds
    # The master award's candidate subject — contract:sourcewell:101223-AXN.
    subj = {c["subject_id"] for c in claims if c["predicate_id"] == "contract"}
    assert subj == {"contract:sourcewell:101223-AXN"}
    # The index row + the artifact row.
    kinds = {c.get("record_kind") for c in report.claims}
    assert "contract_index" in kinds and "evidence_artifact" in kinds
    idx = next(c for c in report.claims if c.get("record_kind") == "contract_index")
    assert idx["predicate_id"] == "contract"
    assert idx["integrity"] == "screened_rendition"
    art = next(c for c in report.claims if c.get("record_kind") == "evidence_artifact")
    assert art["integrity"] == "screened_rendition"
    # No person bytes on the wire.
    blob = json.dumps(report.claims, default=str)
    assert "Jane Sample" not in blob


def test_supplier_page_index_row_not_contract() -> None:
    """A supplier page is a page_index — no contract entity is minted."""
    t = _target("op-supplier-flock")
    report, conn, _ = _run(
        {t.url: _served(t.url, "op_supplier_flock.html")},
        [_tg("op-supplier-flock")],
        source_id="omnia_partners",
    )
    rows = [c for c in report.claims if c.get("record_kind") == "page_index"]
    assert len(rows) == 1
    assert rows[0]["predicate_id"] == "document"
    assert rows[0]["contract_page"] == _OP_SUPPLIER_URL
    # No contract claims — the public page states no number.
    preds = {c["predicate_id"] for c in report.claims if c.get("record_kind") == "claim"}
    assert "contract" not in preds and "contract_number" not in preds
    for c in report.claims:
        assert c["source_id"] == "omnia_partners"


def test_terms_capture_row() -> None:
    """The SIG-TRANSP-004 terms row: URL + digest + capture date."""
    t = _target("sw-terms")
    report, conn, _ = _run(
        {t.url: _served(t.url, "sw_terms.html")},
        [_tg("sw-terms")],
    )
    rows = [c for c in report.claims if c.get("record_kind") == "terms_capture"]
    assert len(rows) == 1
    row = rows[0]
    assert row["terms_url"] == _SW_TERMS_URL
    assert len(row["terms_sha256"]) == 64 and row["captured_at"]
    assert row["contract_page"] == _SW_TERMS_URL


def test_challenge_and_disappearances_recorded() -> None:
    """A 403 ends the target's attempt — recorded, never retried (SIG-INGEST-037)."""
    report, conn, transport = _run(
        {
            _SW_CONTRACT_URL: FetchResult(
                url=_SW_CONTRACT_URL,
                status=403,
                body=b"Forbidden",
                media_type="text/html",
                retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
            _OP_SUPPLIER_URL: _served(_OP_SUPPLIER_URL, "op_supplier_flock.html"),
        },
        [_tg("sw-contract-101223-axn"), _tg("op-supplier-flock")],
    )
    refusal = next(o for o in conn.outcomes if o["result"] == "refused")
    assert refusal["refusal_kind"] == "challenge" and refusal["status"] == 403
    assert {d.event.failing_status for d in report.disappearances} == {"access_restricted"}
    # The other target still captured — one target's refusal never aborts.
    assert len(report.captures) == 1
    assert len(transport.request_log) == 2


def test_interstitial_2xx_is_a_recorded_challenge() -> None:
    report, conn, _ = _run(
        {_SW_CONTRACT_URL: _served(_SW_CONTRACT_URL, "interstitial.html")},
        [_tg("sw-contract-101223-axn")],
    )
    assert not report.captures
    assert conn.outcomes[0]["refusal_kind"] == "interstitial"
    assert {d.event.failing_status for d in report.disappearances} == {"access_restricted"}


def test_host_optout_zero_egress() -> None:
    """The host-level register (§26 rule 7) is consulted before any egress."""
    register = OptOutRegister(
        entries=(
            OptOutEntry(host="www.sourcewell-mn.gov", recorded_on=date(2026, 10, 1), evidence="t"),
        )
    )
    transport = FakeTransport(
        {_SW_CONTRACT_URL: _served(_SW_CONTRACT_URL, "sw_contract_101223_axn.html")}
    )
    conn = _connector()
    report = pipeline.run(
        conn,
        _ctx(
            _fetcher(transport, opt_out_register=register),
            parameters={"targets": [_tg("sw-contract-101223-axn")]},
        ),
    )
    assert not report.captures
    assert transport.request_log == [] and transport.robots_log == []
    assert {r["refusal"] for r in report.refusals} == {"HostOptOut"}


def test_target_optout_zero_egress() -> None:
    """§26 rule 7 at target granularity — the committed opted_out_targets column."""
    inv = load_inventory()
    opted = {t.id for t in inv.targets if t.id == "sw-contract-101223-axn"}
    inv2 = dataclasses.replace(
        inv,
        targets=tuple(dataclasses.replace(t, opted_out=t.id in opted) for t in inv.targets),
    )
    conn = _connector(inventory=inv2)
    transport = FakeTransport(
        {_SW_CONTRACT_URL: _served(_SW_CONTRACT_URL, "sw_contract_101223_axn.html")}
    )
    report = pipeline.run(
        conn,
        _ctx(_fetcher(transport), parameters={"targets": [_tg("sw-contract-101223-axn")]}),
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
        {_SW_CONTRACT_URL: _served(_SW_CONTRACT_URL, "sw_contract_101223_axn.html")}
    )
    conn = _connector()
    ctx = _ctx(_fetcher(transport), parameters={"targets": [_tg("sw-contract-101223-axn")]})
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
            "record_kind": "cooperative_rendition",
            "schema": RENDITION_SCHEMA,
            "contract_page": "u",
            "contact_email": "x@y",
        }
    ]
    with pytest.raises(PredicateNotAllowed, match="denied"):
        conn.normalize(ctx, bad)


def test_no_circumvention_anywhere() -> None:
    """SIG-INGEST-013/036/037: no browser automation, proxy, or challenge-solving."""
    src = inspect.getsource(connectors.cooperative)
    forbidden = re.compile(
        r"playwright|selenium|puppeteer|undetected|cloudscraper|"
        r"headless|proxy_rotate|rotate_proxy|import requests|import httpx|"
        r"urllib\.request|cookie|api_key|authorization",
        re.I,
    )
    assert not forbidden.search(src), forbidden.search(src)


def test_egress_only_through_shared_seam() -> None:
    """The connector holds no transport/HTTP client — ctx.fetcher only."""
    init_src = inspect.getsource(CooperativeConnector.__init__)
    assert "transport" not in init_src
    assert "PoliteFetcher(" not in init_src


def test_emitted_predicates_are_allowlisted() -> None:
    """Every predicate the connector may write is allowlisted + ontology-bound."""
    allowlist = predicate_allowlist()
    assert allowlist == {
        "contract",
        "contract_number",
        "external_id",
        "document",
        "platform",
        "acquisition_method",
        "released_documents",
        "title",
    }
    report, conn, _ = _run(
        {_SW_CONTRACT_URL: _served(_SW_CONTRACT_URL, "sw_contract_101223_axn.html")},
        [_tg("sw-contract-101223-axn")],
    )
    for c in report.claims:
        if c.get("record_kind") in {
            "claim",
            "contract_index",
            "page_index",
            "evidence_artifact",
        }:
            assert c["predicate_id"] in allowlist
