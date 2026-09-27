# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P26.12 / SOURCES.11 — the Congress.gov federal surveillance-legislation sweep.

Deterministic tests over the committed fixtures (the REAL 2026-09-18 page-1
capture of ``/v3/bill/119?limit=250`` + a small synthetic bills page in the
verified v3 shape) — no live network. Covered:

* the reviewed sweep plan bounds (per_page ≤ the v3 max of 250, the hard
  per-congress page bound, congresses = [119]);
* the federal vocabulary additions (``fisa_702``, ``government_surveillance``)
  alongside the shared P26.11 set;
* ``discover_more`` expansion of a captured seed page's ``pagination.count``
  into bounded ``/bill/{congress}?offset=N`` page targets — congress + page
  offset + plan version riding the target row as data, truncation loud at the
  plan bound;
* typed federal bill claims — the conventional citation as typed identifier
  with the verbatim ``"TYPE NUMBER"`` as raw, chamber, congress-as-session,
  the reviewed federal jurisdiction label, verbatim latest-action status,
  byte-range-into-title keyword locators, the derived congress.gov public
  record URL — NEVER a §11.14 LegalInstrument — while unmatched bills keep
  the ``index_only`` evidence link;
* the per-page ``bill_query`` outcome row (congress, page offset, counts,
  truncation);
* fail-closed handling of the api.data.gov error envelope + malformed
  captures;
* claim-digest idempotency — no volatile field keys a claim.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
from connectors.accountability import (
    AccountabilityConnector,
    _congress_external_id,
    _congress_identifier,
    _congress_number,
    _congress_ordinal,
    _congress_public_url,
    _matched_legislation,
    congress_gov_config,
    congress_gov_plan,
    legislation_terms,
)
from connectors.registry import get as get_source
from connectors.runner import run_connector_over_fixture
from connectors.stages import ContentDrift, InMemoryCaptureStore, RunContext
from evidence.ingest_run import IngestRun

_FIX = Path(__file__).parent / "fixtures" / "promoted"
_SEED_URL = "https://api.congress.gov/v3/bill/119?limit=250&offset=0&format=json"


def _ctx(
    source_id: str = "congress_gov", targets: list[dict[str, Any]] | None = None
) -> RunContext:
    return RunContext(
        source=get_source(source_id),
        run=IngestRun("accountability", "1.0.0", "unknown", "r1", "v1", ()),
        captures=InMemoryCaptureStore(),
        parameters={
            "targets": targets
            if targets is not None
            else [
                {
                    "id": "congress-gov-bill-119-p1",
                    "url": _SEED_URL,
                    "kind": "congress_bill_index",
                    "congress": "119",
                }
            ]
        },
    )


def _capture(ctx: RunContext, data: bytes, uri: str) -> Any:
    return ctx.captures.put(data, media_type="application/json", source_uri=uri)


def _bill(congress: int = 119, **extra: Any) -> dict[str, Any]:
    bill = {
        "congress": congress,
        "type": "HR",
        "number": "1",
        "originChamber": "House",
        "originChamberCode": "H",
        "title": "To provide for the adjustment of certain payments.",
        "introducedDate": "2025-01-03",
        "latestAction": {"actionDate": "2025-01-03", "text": "Introduced in House"},
        "updateDate": "2025-01-04",
        "url": "https://api.congress.gov/v3/bill/119/hr/1?format=json",
    }
    bill.update(extra)
    return bill


# --- the reviewed plan + vocabulary (data) -------------------------------------


def test_legislation_vocab_covers_the_federal_terms() -> None:
    """The P26.11 set plus the P26.12 federal additions — every ticket-named
    topic has a reviewed term."""
    ids = {t["id"] for t in legislation_terms()}
    assert {
        "alpr",
        "facial_recognition",
        "drone",
        "body_worn_camera",
        "gunshot_detection",
        "rtcc",
        "geofence_warrant",
        "cell_site_simulator",
        "data_broker",
        "predictive_policing",
        # P26.12 federal additions:
        "fisa_702",
        "government_surveillance",
    } <= ids
    # The federal terms cover the ticket's named phrases.
    fisa = next(t for t in legislation_terms() if t["id"] == "fisa_702")
    pats = " ".join(str(p) for p in fisa["patterns"])
    for phrase in ("foreign intelligence surveillance", "fisa", "section 702"):
        assert phrase in pats


def test_congress_plan_bounds_are_the_verified_v3_bounds() -> None:
    plan = congress_gov_plan()
    cfg = plan["bill_index"]
    assert cfg["endpoint"] == "/bill"
    assert cfg["congresses"] == [119]
    # limit ∈ [1,250] — the documented v3 page bound (api.congress.gov README).
    assert 1 <= int(cfg["per_page"]) <= 250
    # The hard per-congress bound stays inside the documented quota: 96 pages
    # is ~76 requests for the observed 18,887-bill index (5,000 req/hour).
    assert 1 <= int(cfg["max_pages_per_congress"]) <= 100
    assert plan["plan_version"]


def test_congress_config_is_header_authed_cc0() -> None:
    cfg = congress_gov_config()
    assert cfg["api_key_header"] == "X-Api-Key"
    assert cfg["api_key_env"] == "SIG_DATA_GOV_KEY"
    assert cfg["spdx"] == "CC0-1.0"
    assert cfg["jurisdiction_label"] == "United States Congress"


# --- the URL / identifier helpers ------------------------------------------------


def test_congress_number_from_path() -> None:
    assert _congress_number("https://api.congress.gov/v3/bill/119?offset=0") == "119"
    assert _congress_number("https://api.congress.gov/v3/bill/118/hr/1") == "118"
    assert _congress_number("https://example.org/no-congress") is None


def test_congress_ordinal() -> None:
    assert _congress_ordinal(119) == "119th"
    assert _congress_ordinal("111") == "111th"
    assert _congress_ordinal("x") is None


def test_identifier_typed_and_verbatim_raw() -> None:
    typed, raw = _congress_identifier(_bill(type="S", number="1355"))
    assert typed == "S. 1355"
    assert raw == "S 1355"
    # Every reviewed type maps to its conventional citation prefix.
    expected = {
        "HR": "H.R.",
        "S": "S.",
        "HRES": "H.Res.",
        "SRES": "S.Res.",
        "HJRES": "H.J.Res.",
        "SJRES": "S.J.Res.",
        "HCONRES": "H.Con.Res.",
        "SCONRES": "S.Con.Res.",
    }
    for bill_type, prefix in expected.items():
        typed, raw = _congress_identifier(_bill(type=bill_type, number="9"))
        assert typed == f"{prefix} 9"
        assert raw == f"{bill_type} 9"
    # An unmapped type falls back to the verbatim form — never guessed.
    typed, raw = _congress_identifier(_bill(type="XBILL", number="9"))
    assert typed == "XBILL 9" and raw == "XBILL 9"


def test_public_url_derivation() -> None:
    url = _congress_public_url(_bill(congress=119, type="S", number="1355"))
    assert url == "https://www.congress.gov/bill/119th-congress/senate-bill/1355"
    assert (
        _congress_public_url(_bill(congress=118, type="HJRES", number="44"))
        == "https://www.congress.gov/bill/118th-congress/house-joint-resolution/44"
    )
    # An unmapped type yields None — the caller falls back to the verbatim url.
    assert _congress_public_url(_bill(type="XBILL")) is None


def test_external_id_shape() -> None:
    assert _congress_external_id(_bill(congress=119, type="S", number="1355")) == "119-s-1355"


# --- the bounded sweep expansion ------------------------------------------------


def test_discover_more_expands_the_real_seed_page() -> None:
    """The captured page-1's pagination.count (18,887 — the real 2026-09-18
    index size) expands to the remaining bounded /bill/119 pages."""
    connector = AccountabilityConnector()
    ctx = _ctx()
    capture = _capture(ctx, (_FIX / "congress_gov_bill119_p1.json").read_bytes(), _SEED_URL)
    targets = connector.discover_more(ctx, [capture])
    plan = congress_gov_plan()["bill_index"]
    per_page = int(plan["per_page"])
    # count=18887 → offsets 250..18750 → 75 pages (the seed IS page 1).
    assert len(targets) == (18887 - 1) // per_page
    assert len(targets) <= int(plan["max_pages_per_congress"]) - 1
    for i, target in enumerate(targets):
        assert target["kind"] == "congress_bill_index"
        assert target["congress"] == "119"
        assert target["page_offset"] == (i + 1) * per_page
        assert target["plan_version"] == congress_gov_plan()["plan_version"]
        qs = parse_qs(urlsplit(str(target["url"])).query)
        assert qs["limit"] == [str(per_page)]
        assert qs["offset"] == [str((i + 1) * per_page)]
        assert "/bill/119" in str(target["url"])
        # No credential ever rides the generated URL (HG-09).
        assert "api_key" not in qs and "apikey" not in qs
    assert len(ctx.resolved_targets) == len(targets)


def test_discover_more_bounds_a_giant_index() -> None:
    """A count beyond the plan bound generates only bound-1 pages — truncation
    is recorded loud on the outcome rows, never a crawl."""
    connector = AccountabilityConnector()
    ctx = _ctx()
    payload = {"bills": [_bill()], "pagination": {"count": 99999}}
    capture = _capture(ctx, json.dumps(payload).encode(), _SEED_URL)
    targets = connector.discover_more(ctx, [capture])
    max_pages = int(congress_gov_plan()["bill_index"]["max_pages_per_congress"])
    assert len(targets) == max_pages - 1


def test_discover_more_ignores_non_seed_captures() -> None:
    """A generated page never re-expands — exactly one bounded pass."""
    connector = AccountabilityConnector()
    ctx = _ctx()
    capture = _capture(
        ctx,
        json.dumps({"bills": [_bill()], "pagination": {"count": 99999}}).encode(),
        "https://api.congress.gov/v3/bill/119?limit=250&offset=250&format=json",
    )
    assert connector.discover_more(ctx, [capture]) == []


def test_discover_more_drift_is_loud() -> None:
    connector = AccountabilityConnector()
    ctx = _ctx()
    bad = _capture(
        ctx,
        b'{"error":{"code":"API_KEY_MISSING","message":"No api_key was supplied."}}',
        _SEED_URL,
    )
    with pytest.raises(ContentDrift):
        connector.discover_more(ctx, [bad])


def test_discover_more_ignores_other_sources() -> None:
    connector = AccountabilityConnector()
    ctx = _ctx("courtlistener_recap", targets=[])
    assert connector.discover_more(ctx, []) == []


# --- typed claims under the reviewed claim-shape map ----------------------------


def test_matching_federal_bills_emit_typed_claims() -> None:
    """The synthetic page: two surveillance bills → typed claims, verbatim."""
    report = run_connector_over_fixture(
        "accountability",
        "congress_gov",
        _FIX / "congress_gov_bills_fisa.json",
        media_type="application/json",
        kind="congress_bill_index",
        target_url=_SEED_URL,
    )
    claims = [c for c in report.claims if c.get("record_kind") == "claim"]
    assert claims, "matching federal bills must emit typed claims"
    by_subject: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        by_subject.setdefault(str(claim["subject_id"]), []).append(claim)
    assert len(by_subject) == 2  # S 1355 + HR 4587; the HRES stays index-only
    predicates = {c["predicate_id"] for c in claims}
    assert {
        "bill_external_id",
        "bill_identifier",
        "bill_title",
        "bill_session",
        "bill_jurisdiction",
        "bill_chamber",
        "bill_status",
        "bill_status_date",
        "bill_matched_keyword",
    } <= predicates
    # A pending federal bill is NEVER a §11.14 LegalInstrument (§3.1).
    assert not any(c.get("predicate_id") in {"legal_instrument", "statute"} for c in report.claims)
    # The federal surface the state sweep does not carry:
    chambers = {c["raw_value"] for c in claims if c["predicate_id"] == "bill_chamber"}
    assert chambers == {"Senate", "House"}
    sessions = {c["raw_value"] for c in claims if c["predicate_id"] == "bill_session"}
    assert sessions == {"119"}
    jurisdictions = {c["raw_value"] for c in claims if c["predicate_id"] == "bill_jurisdiction"}
    assert jurisdictions == {"United States Congress"}
    # The typed identifier is the conventional citation; raw stays verbatim.
    ident = {c["raw_value"]: c["value"] for c in claims if c["predicate_id"] == "bill_identifier"}
    assert ident == {"S 1355": "S. 1355", "HR 4587": "H.R. 4587"}
    # Verbatim literals are the keyword claims' raw_values.
    kw = {c["raw_value"] for c in claims if c["predicate_id"] == "bill_matched_keyword"}
    assert "Government Surveillance" in kw
    assert "Foreign Intelligence Surveillance" in kw
    # Every claim carries evidence with a locator + the derived public record URL.
    for claim in claims:
        ev = claim.get("evidence") or {}
        assert ev.get("locator"), claim
        assert str(ev.get("source_url") or "").startswith(
            "https://www.congress.gov/bill/119th-congress/"
        ), claim
        assert claim.get("license") == "CC0-1.0"
    kw_claim = next(c for c in claims if c["predicate_id"] == "bill_matched_keyword")
    assert kw_claim["evidence"]["locator"]["kind"] == "byte_range"
    assert kw_claim["evidence"]["field"] == "title"
    # Status is the record's own latest-action text, verbatim.
    status = {c["raw_value"] for c in claims if c["predicate_id"] == "bill_status"}
    assert "Read twice and referred to the Committee on the Judiciary." in status


def test_unmatched_federal_bill_keeps_the_index_only_link() -> None:
    """A bill matching no term stays an index_only primary_record evidence
    link — never normalized to a fact, never a LegalInstrument."""
    connector = AccountabilityConnector()
    ctx = _ctx()
    capture = _capture(
        ctx,
        json.dumps(
            {
                "bills": [_bill(title="To designate a post office.")],
                "pagination": {"count": 1},
            }
        ).encode(),
        _SEED_URL,
    )
    parsed = connector.parse(ctx, capture)
    rows = connector.normalize(ctx, connector.extract(ctx, parsed))
    links = [r for r in rows if r.get("record_kind") == "evidence_link"]
    assert len(links) == 1 and links[0]["index_only"] is True
    assert links[0]["source_class"] == "primary_record"
    assert links[0]["legislative_jurisdiction"] == "United States Congress"
    assert not any(r.get("record_kind") == "claim" for r in rows)


def test_bill_query_outcome_row_records_the_federal_page() -> None:
    report = run_connector_over_fixture(
        "accountability",
        "congress_gov",
        _FIX / "congress_gov_bills_fisa.json",
        media_type="application/json",
        kind="congress_bill_index",
        target_url=_SEED_URL,
    )
    rows = [r for r in report.claims if r.get("record_kind") == "bill_query"]
    assert len(rows) == 1
    row = rows[0]
    assert row["outcome"] == "matched"
    assert row["bills_indexed"] == 3
    assert row["bills_matched"] == 2
    assert set(row["matched_terms"]) == {"fisa_702", "government_surveillance"}
    assert row["congress"] == "119"
    assert row["page_offset"] == 0
    assert row["total_items"] == 3
    assert row["truncated"] is False
    assert row["capture_digest"]
    assert row["plan_version"] == congress_gov_plan()["plan_version"]


def test_real_page_indexes_verbatim() -> None:
    """The real 250-bill capture parses + normalizes: 250 index links, an
    honest empty outcome row (page 1 carries no vocab match), no typed claims."""
    connector = AccountabilityConnector()
    ctx = _ctx()
    capture = _capture(ctx, (_FIX / "congress_gov_bill119_p1.json").read_bytes(), _SEED_URL)
    parsed = connector.parse(ctx, capture)
    rows = connector.normalize(ctx, connector.extract(ctx, parsed))
    links = [r for r in rows if r.get("record_kind") == "evidence_link"]
    assert len(links) == 250
    assert all(r["index_only"] is True for r in links)
    outcome = next(r for r in rows if r.get("record_kind") == "bill_query")
    assert outcome["bills_indexed"] == 250
    assert outcome["outcome"] == "empty"
    assert outcome["congress"] == "119"
    assert outcome["total_items"] == 18887
    assert outcome["truncated"] is True  # 18,887 total > 250 returned — honest


# --- fail-closed envelopes + idempotency -----------------------------------------


def test_api_error_envelope_is_content_drift() -> None:
    """The api.data.gov error shape is ContentDrift, never a bogus bill."""
    connector = AccountabilityConnector()
    ctx = _ctx()
    capture = _capture(
        ctx,
        b'{"error":{"code":"API_KEY_MISSING","message":"No api_key was supplied. '
        b'Get one at https://api.congress.gov:443"}}',
        _SEED_URL,
    )
    parsed = connector.parse(ctx, capture)
    with pytest.raises(ContentDrift):
        connector.extract(ctx, parsed)


def test_malformed_capture_is_content_drift() -> None:
    connector = AccountabilityConnector()
    ctx = _ctx()
    capture = _capture(ctx, b"<html>cloudflare challenge</html>", _SEED_URL)
    with pytest.raises(ContentDrift):
        connector.parse(ctx, capture)


def test_non_bills_shape_is_content_drift() -> None:
    connector = AccountabilityConnector()
    ctx = _ctx()
    capture = _capture(ctx, b'{"amendments": []}', _SEED_URL)
    parsed = connector.parse(ctx, capture)
    with pytest.raises(ContentDrift):
        connector.extract(ctx, parsed)


def test_claims_carry_no_volatile_fields() -> None:
    """Claim identity is stable bill content — no retrieval timestamps, no
    observation time, no capture ids may key a claim (the P26.6/P26.8
    digest-churn defect class). ``observed_at`` is deliberately absent: the
    observation time lives on the capture/evidence, so an unchanged record
    digests identically on ANY re-run — the idempotency the hourly quota
    requires."""
    report = run_connector_over_fixture(
        "accountability",
        "congress_gov",
        _FIX / "congress_gov_bills_fisa.json",
        media_type="application/json",
        kind="congress_bill_index",
        target_url=_SEED_URL,
    )
    claims = [c for c in report.claims if c.get("record_kind") == "claim"]
    for claim in claims:
        for key in (
            "retrieved_at",
            "retrieved_date",
            "observed_at",
            "capture_digest",
            "capture_id",
        ):
            assert key not in claim, (key, claim)
            assert key not in (claim.get("evidence") or {}), (key, claim)


def test_normalize_is_deterministic() -> None:
    """The same capture normalizes to byte-identical rows modulo generated
    ids/timestamps — the digest-stable half of the idempotency proof."""
    connector = AccountabilityConnector()
    ctx = _ctx()
    capture = _capture(
        ctx,
        (_FIX / "congress_gov_bills_fisa.json").read_bytes(),
        _SEED_URL,
    )
    parsed = connector.parse(ctx, capture)
    first = connector.normalize(ctx, connector.extract(ctx, parsed))
    second = connector.normalize(ctx, connector.extract(ctx, parsed))
    from db.claim_sink import content_digest

    assert [content_digest(c) for c in first] == [content_digest(c) for c in second]


def test_matched_legislation_reads_the_federal_title() -> None:
    """The local scan is the match of record — the Congress.gov bill list has
    no server-side keyword query."""
    bill = _bill(title="Cell-Site Simulator Warrant Act of 2025")
    matches, suppressed = _matched_legislation(bill)
    assert {m["term_id"] for m in matches} == {"cell_site_simulator"}
    assert matches[0]["field"] == "title"
    assert matches[0]["literal"] == "Cell-Site Simulator"
    assert suppressed == set()
