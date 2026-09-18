# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P26.11 / SOURCES.10 — the OpenStates 50-state surveillance-legislation sweep.

Deterministic tests over the committed real-capture fixtures (the two
``/jurisdictions`` pages fetched live 2026-09-18 + the P26.4 bill fixture) —
no live network. Covered:

* the reviewed sweep plan bounds (per_page ≤ the v3 /bills max of 20, the
  hard query bound, the session-window rule);
* ``discover_more`` expansion of the captured index into bounded
  per-jurisdiction × per-family bill_search targets (the query plan riding
  the target row as data);
* typed bill claims under the reviewed claim-shape map — verbatim literals,
  locators, the bill record as evidence, NEVER a §11.14 LegalInstrument —
  while unmatched bills keep the P26.4 index_only link;
* the per-query ``bill_query`` outcome row (hits/empty, counts, truncation);
* fail-closed handling of API error envelopes and malformed captures;
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
    _bill_query_targets,
    _jurisdiction_abbr,
    _matched_legislation,
    _resolve_session,
    legislation_terms,
    openstates_plan,
)
from connectors.registry import get as get_source
from connectors.runner import run_connector_over_fixture
from connectors.stages import ContentDrift, InMemoryCaptureStore, RunContext
from evidence.ingest_run import IngestRun

_FIX = Path(__file__).parent / "fixtures" / "promoted"


def _bill(
    bill_id: str = "ocd-bill/ok-2026-X-1",
    identifier: str = "HB 1",
    title: str = "An Act relating to motor vehicles",
    **extra: Any,
) -> dict[str, Any]:
    bill = {
        "id": bill_id,
        "identifier": identifier,
        "title": title,
        "session": "2026",
        "jurisdiction": {
            "id": "ocd-jurisdiction/country:us/state:ok/government",
            "name": "Oklahoma",
            "classification": "state",
        },
        "latest_action_description": "Introduced",
        "latest_action_date": "2026-02-01",
        "openstates_url": "https://openstates.org/ok/bills/2026/HB1/",
        "sources": [{"url": "https://www.oklegislature.gov/BillInfo.aspx?Bill=HB1"}],
    }
    bill.update(extra)
    return bill


def _ctx(source_id: str = "openstates") -> RunContext:
    return RunContext(
        source=get_source(source_id),
        run=IngestRun("accountability", "1.0.0", "unknown", "r1", "v1", ()),
        captures=InMemoryCaptureStore(),
        parameters={"targets": []},
    )


def _capture(ctx: RunContext, data: bytes, uri: str) -> Any:
    return ctx.captures.put(data, media_type="application/json", source_uri=uri)


def _jurisdictions() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page in (1, 2):
        rows += json.loads((_FIX / f"openstates_jurisdictions_p{page}.json").read_bytes())[
            "results"
        ]
    return rows


# --- the reviewed plan + vocabulary (data) -------------------------------------


def test_legislation_vocab_covers_the_ticket_terms() -> None:
    """Every ticket-named phrase is covered by a reviewed term's patterns."""
    ids = {t["id"] for t in legislation_terms()}
    assert {
        "alpr",
        "surveillance_ordinance",
        "facial_recognition",
        "drone",
        "body_worn_camera",
        "gunshot_detection",
        "rtcc",
        "cctv",
        "automated_traffic_enforcement",
        "geofence_warrant",
        "cell_site_simulator",
        "data_broker",
        "predictive_policing",
    } <= ids
    # Every term declares a reviewed claim shape.
    assert all(t.get("claim_shape") in {"typed_claim", "index_only"} for t in legislation_terms())


def test_plan_bounds_are_the_verified_v3_bounds() -> None:
    plan = openstates_plan()
    # /bills per_page ∈ [1,20] — verified live 2026-09-18 (52 is /jurisdictions).
    assert 1 <= int(plan["bills_query"]["per_page"]) <= 20
    # The hard run bound covers the 56-jurisdiction × 4-family sweep with
    # headroom, and stays inside the 5/min × 60m task window (~300 requests).
    families = plan["query_families"]
    assert len(families) >= 3
    assert int(plan["bills_query"]["max_queries"]) >= 56 * len(families)
    assert int(plan["bills_query"]["max_queries"]) <= 300
    # The jurisdictions index is bounded at the v3 max page size.
    assert int(plan["jurisdiction_index"]["per_page"]) <= 52
    assert plan["session_window"]["classes"]


def test_jurisdiction_abbr_extraction() -> None:
    assert _jurisdiction_abbr("ocd-jurisdiction/country:us/state:tx/government") == "tx"
    assert _jurisdiction_abbr("ocd-jurisdiction/country:us/district:dc/government") == "dc"
    assert _jurisdiction_abbr("ocd-jurisdiction/country:us/territory:pr/government") == "pr"


def test_resolve_session_prefers_the_regular_window() -> None:
    """TX's real session list: the called session '892' must NOT shadow '89R'."""
    tx = next(j for j in _jurisdictions() if j["id"].endswith("state:tx/government"))
    classes = openstates_plan()["session_window"]["classes"]
    assert _resolve_session(tx["legislative_sessions"], classes) == "89R"


def test_resolve_session_edge_cases() -> None:
    classes = ["primary", "regular"]
    # No sessions → None (the query runs unfiltered — recorded, not invented).
    assert _resolve_session([], classes) is None
    # Sessions without a classification fall back to latest-start of any class.
    sessions = [
        {"identifier": "old", "start_date": "2020-01-01"},
        {"identifier": "new", "start_date": "2026-01-01"},
    ]
    assert _resolve_session(sessions, classes) == "new"


# --- the bounded sweep expansion ------------------------------------------------


def test_bill_query_targets_cover_every_jurisdiction() -> None:
    plan = openstates_plan()
    targets = _bill_query_targets(_jurisdictions(), plan)
    families = plan["query_families"]
    jurisdictions = _jurisdictions()
    assert len(jurisdictions) == 56  # 50 states + DC + 5 territories
    assert len(targets) == len(jurisdictions) * len(families)
    # Every target is a bounded bill_search row carrying the query plan as data.
    for target in targets:
        assert target["kind"] == "bill_search"
        assert target["plan_version"] == plan["plan_version"]
        assert target["per_page"] <= 20
        qs = parse_qs(urlsplit(str(target["url"])).query)
        assert qs["jurisdiction"]
        assert qs["per_page"] == ["20"]
        assert qs["sort"] == ["latest_action_desc"]
        assert " OR " in qs["q"][0]
    # TX carries the resolved regular session; AS (no sessions) has none.
    tx = next(t for t in targets if t["jurisdiction_abbr"] == "tx")
    assert tx["session"] == "89R"
    assert "session=89R" in str(tx["url"])
    as_target = next(t for t in targets if t["jurisdiction_abbr"] == "as")
    assert as_target["session"] is None
    assert "session" not in parse_qs(urlsplit(str(as_target["url"])).query)


def test_discover_more_expands_captured_index(tmp_path: Path) -> None:
    """The captured jurisdictions pages are the sweep's discovery surface."""
    connector = AccountabilityConnector()
    ctx = _ctx()
    captures = [
        _capture(
            ctx,
            (_FIX / f"openstates_jurisdictions_p{p}.json").read_bytes(),
            f"https://v3.openstates.org/jurisdictions?include=legislative_sessions"
            f"&classification=state&per_page=52&page={p}",
        )
        for p in (1, 2)
    ]
    targets = connector.discover_more(ctx, captures)
    assert len(targets) == 56 * len(openstates_plan()["query_families"])
    # The resolved targets are recorded for the children's post-capture context.
    assert len(ctx.resolved_targets) == len(targets)
    ids = {t["id"] for t in targets}
    assert "openstates-bills-ok-plates_traffic_enforcement" in ids
    assert "openstates-bills-pr-drones_bodycam_gunshot" in ids


def test_discover_more_drift_is_loud() -> None:
    connector = AccountabilityConnector()
    ctx = _ctx()
    bad = _capture(
        ctx,
        b'{"detail": "exceeded limit of 10/min: 15"}',
        "https://v3.openstates.org/jurisdictions?per_page=52&page=1",
    )
    with pytest.raises(ContentDrift):
        connector.discover_more(ctx, [bad])


def test_discover_more_ignores_non_openstates_sources() -> None:
    connector = AccountabilityConnector()
    ctx = _ctx("courtlistener_recap")
    assert connector.discover_more(ctx, []) == []


# --- typed claims under the reviewed claim-shape map ----------------------------


def test_matching_bills_emit_typed_claims() -> None:
    """The committed bill fixture: both titles match → typed claims, verbatim."""
    report = run_connector_over_fixture(
        "accountability",
        "openstates",
        _FIX / "openstates_bills_ok.json",
        media_type="application/json",
        kind="bill_search",
        target_url="https://v3.openstates.org/bills?jurisdiction=ok&q=alpr&per_page=10",
    )
    claims = [c for c in report.claims if c.get("record_kind") == "claim"]
    assert claims, "matching bills must emit typed claims"
    by_subject: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        by_subject.setdefault(str(claim["subject_id"]), []).append(claim)
    assert len(by_subject) == 2  # HB 3101 + SB 2200
    predicates = {c["predicate_id"] for c in claims}
    assert {
        "bill_external_id",
        "bill_identifier",
        "bill_title",
        "bill_session",
        "bill_jurisdiction",
        "bill_status",
        "bill_status_date",
        "bill_matched_keyword",
    } <= predicates
    # A pending bill is NEVER a §11.14 LegalInstrument (§3.1).
    assert not any(c.get("predicate_id") in {"legal_instrument", "statute"} for c in report.claims)
    # Every claim carries evidence with a locator + the bill record URL.
    for claim in claims:
        ev = claim.get("evidence") or {}
        assert ev.get("locator"), claim
        assert ev.get("source_url"), claim
        assert claim.get("license") == "CC0-1.0"
    # The verbatim matched literal is the keyword claim's raw_value.
    kw = {c["raw_value"] for c in claims if c["predicate_id"] == "bill_matched_keyword"}
    assert "automated license plate" in kw
    assert "surveillance camera" in kw
    # The keyword locator is a byte range into the named field.
    kw_claim = next(c for c in claims if c["predicate_id"] == "bill_matched_keyword")
    assert kw_claim["evidence"]["locator"]["kind"] == "byte_range"
    assert kw_claim["evidence"]["field"] == "title"
    # Status is the record's own latest-action text, verbatim.
    status = {c["raw_value"] for c in claims if c["predicate_id"] == "bill_status"}
    assert status == {"Referred to Committee on Public Safety", "Introduced"}


def test_unmatched_bill_keeps_the_index_only_link() -> None:
    """The claim-shape map: a bill matching no term stays a P26.4 evidence link."""
    connector = AccountabilityConnector()
    ctx = _ctx()
    capture = _capture(
        ctx,
        json.dumps(
            {
                "results": [_bill(title="An Act relating to municipal bonds")],
                "pagination": {"total_items": 1, "per_page": 20, "page": 1, "max_page": 1},
            }
        ).encode(),
        "https://v3.openstates.org/bills?jurisdiction=ok&q=x&per_page=20",
    )
    parsed = connector.parse(ctx, capture)
    rows = connector.normalize(ctx, connector.extract(ctx, parsed))
    links = [r for r in rows if r.get("record_kind") == "evidence_link"]
    assert len(links) == 1 and links[0]["index_only"] is True
    assert not any(r.get("record_kind") == "claim" for r in rows)


def test_bill_query_outcome_row_records_the_sweep_result() -> None:
    report = run_connector_over_fixture(
        "accountability",
        "openstates",
        _FIX / "openstates_bills_ok.json",
        media_type="application/json",
        kind="bill_search",
        target_url="https://v3.openstates.org/bills?jurisdiction=ok&q=alpr&per_page=10",
    )
    rows = [r for r in report.claims if r.get("record_kind") == "bill_query"]
    assert len(rows) == 1
    row = rows[0]
    assert row["outcome"] == "matched"
    assert row["bills_indexed"] == 2
    assert row["bills_matched"] == 2
    assert set(row["matched_terms"]) == {"alpr", "cctv"}
    assert row["capture_digest"]
    assert row["plan_version"] == openstates_plan()["plan_version"]


def test_jurisdiction_index_rows_record_the_window() -> None:
    connector = AccountabilityConnector()
    ctx = _ctx()
    capture = _capture(
        ctx,
        (_FIX / "openstates_jurisdictions_p1.json").read_bytes(),
        "https://v3.openstates.org/jurisdictions?per_page=52&page=1",
    )
    parsed = connector.parse(ctx, capture)
    rows = connector.normalize(ctx, connector.extract(ctx, parsed))
    index_rows = [r for r in rows if r.get("record_kind") == "jurisdiction_index"]
    assert len(index_rows) == 52
    tx = next(r for r in index_rows if r["jurisdiction_id"].endswith("state:tx/government"))
    assert tx["session_resolved"] == "89R"


# --- fail-closed envelopes + idempotency -----------------------------------------


def test_error_envelope_is_content_drift() -> None:
    """An API error/rate-limit envelope is ContentDrift, never a bogus bill."""
    connector = AccountabilityConnector()
    ctx = _ctx()
    capture = _capture(
        ctx,
        b'{"detail": "exceeded limit of 10/min: 15"}',
        "https://v3.openstates.org/bills?jurisdiction=ok&q=x&per_page=20",
    )
    parsed = connector.parse(ctx, capture)
    with pytest.raises(ContentDrift):
        connector.extract(ctx, parsed)


def test_malformed_capture_is_content_drift() -> None:
    connector = AccountabilityConnector()
    ctx = _ctx()
    capture = _capture(
        ctx,
        b"<html>cloudflare challenge</html>",
        "https://v3.openstates.org/bills?jurisdiction=ok&q=x&per_page=20",
    )
    with pytest.raises(ContentDrift):
        connector.parse(ctx, capture)


def test_claims_carry_no_volatile_fields() -> None:
    """Claim identity is stable bill content — no retrieval timestamps, no
    observation time, no capture ids may key a claim (the P26.6/P26.8
    digest-churn defect class). ``observed_at`` is deliberately absent: the
    observation time lives on the capture/evidence, so an unchanged record
    digests identically on ANY re-run — the idempotency the daily API quota
    requires (the atlas optional-observed_at pattern)."""
    report = run_connector_over_fixture(
        "accountability",
        "openstates",
        _FIX / "openstates_bills_ok.json",
        media_type="application/json",
        kind="bill_search",
        target_url="https://v3.openstates.org/bills?jurisdiction=ok&q=alpr&per_page=10",
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
        (_FIX / "openstates_bills_ok.json").read_bytes(),
        "https://v3.openstates.org/bills?jurisdiction=ok&q=alpr&per_page=10",
    )
    parsed = connector.parse(ctx, capture)
    first = connector.normalize(ctx, connector.extract(ctx, parsed))
    second = connector.normalize(ctx, connector.extract(ctx, parsed))
    from db.claim_sink import content_digest

    assert [content_digest(c) for c in first] == [content_digest(c) for c in second]


def test_matched_legislation_scans_alternate_titles() -> None:
    bill = _bill(
        title="An Act relating to public safety",
        other_titles=[{"title": "Drone Use Regulation Act"}],
    )
    matches, suppressed = _matched_legislation(bill)
    assert {m["term_id"] for m in matches} == {"drone"}
    assert matches[0]["field"] == "other_titles[0]"
    assert matches[0]["literal"] == "Drone"
    assert suppressed == set()


def test_part_viii_guard_suppresses_a_forbidden_literal() -> None:
    """The guard is literal-scoped (the P26.10 convention): a literal carrying a
    per-datum token is suppressed + recorded, never emitted."""
    from connectors.accountability import _guard_token

    assert _guard_token("a plate number ABC123") == "plate number"
    assert _guard_token("facial recognition") is None
    # A title mentioning a technology is institutional text — the clean literal
    # still emits; the guard only blocks literals carrying per-datum tokens.
    bill = _bill(title="An Act requiring plate number reporting by drone operators")
    matches, suppressed = _matched_legislation(bill)
    assert {m["term_id"] for m in matches} == {"drone"}
    assert suppressed == set()
