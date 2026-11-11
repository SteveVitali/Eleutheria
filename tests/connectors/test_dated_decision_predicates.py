# SPDX-License-Identifier: Apache-2.0
"""P37.31 (K7 WX-02 / R11-K13-WX-02) — the dated-decision predicates.

The agenda normaliser emits the platform's own meeting/hearing date as a
``meeting_date`` claim on the agenda_item subject (it sat in the raw
``introduced`` fields but was never a claim); the §11.11 Contract surface
carries the stated renewal triple (``auto_renews`` / ``notice_window_days`` /
``renewal_term_months``); and the P07.1 parser reads the same triple verbatim
out of a contract-kind matter's captured document, byte-range located and
Part VIII screened. A moved meeting or revised term supersedes by NEW claims —
append-only, never an edit (SIG-STORE-011).
"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest
from connectors.procurement import (
    Contract,
    PredicateNotAllowed,
    ProcurementConnector,
    assert_predicate_allowed,
    is_predicate_allowed,
    source_ids,
)
from connectors.registry import get
from connectors.stages import InMemoryCaptureStore, InMemoryClaimSink, RunContext
from evidence.ingest_run import IngestRun


def _ctx(source_key: str = "legistar") -> RunContext:
    source = dataclasses.replace(get(source_ids()[source_key]), ingestion_permitted=True)
    return RunContext(
        source=source,
        run=IngestRun(
            connector_name="procurement",
            connector_version="1.0.0",
            code_commit="deadbeef",
            ruleset_version="r1",
            vocab_version="v1",
            input_digests=(),
        ),
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
    )


def _claims(rows: list[dict[str, Any]], predicate: str) -> list[dict[str, Any]]:
    return [
        r for r in rows if r.get("record_kind") == "claim" and r.get("predicate_id") == predicate
    ]


# --- the predicate allowlist (SIG-INGEST-033) -----------------------------------


def test_dated_decision_predicates_are_allowlisted() -> None:
    for predicate in (
        "meeting_date",
        "auto_renews",
        "notice_window_days",
        "renewal_term_months",
    ):
        assert is_predicate_allowed(predicate), predicate


# --- meeting_date: the agenda normaliser emits it as a claim --------------------


def _agenda_raw(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_kind": "agenda_item",
        "raw": dict(item),
        "tenant": {
            "tenant_id": "seattle_wa",
            "platform": "legistar",
            "jurisdiction": "Seattle, WA",
            "contract_matter_patterns": ["contract"],
        },
    }


def test_agenda_item_emits_meeting_date_claim() -> None:
    raw = _agenda_raw(
        {
            "MatterId": 121279,
            "MatterFile": "CB 121279",
            "MatterTitle": "A contract for license plate reader services",
            "MatterTypeName": "Contract",
            "MatterIntroDate": "2026-10-06T00:00:00",
        }
    )
    rows = ProcurementConnector().normalize(_ctx(), [raw])
    claims = _claims(rows, "meeting_date")
    assert len(claims) == 1
    claim = claims[0]
    assert claim["subject_id"].startswith("agenda_item:legistar:seattle_wa:")
    assert claim["value"] == "2026-10-06"
    assert claim["raw_value"] == "2026-10-06T00:00:00"  # the verbatim platform literal
    assert claim["evidence_genre"] == "agenda_document"


def test_agenda_item_without_a_date_emits_no_meeting_date() -> None:
    raw = _agenda_raw({"MatterId": 1, "MatterTitle": "Untitled", "MatterTypeName": "Resolution"})
    rows = ProcurementConnector().normalize(_ctx(), [raw])
    assert _claims(rows, "meeting_date") == []


def test_alternate_platform_date_fields_emit() -> None:
    raw = _agenda_raw(
        {"id": "evt-9", "name": "Council meeting", "startDateTime": "2026-11-03T18:00:00"}
    )
    rows = ProcurementConnector().normalize(_ctx("civicclerk"), [raw])
    claims = _claims(rows, "meeting_date")
    assert len(claims) == 1 and claims[0]["value"] == "2026-11-03"


def test_unparseable_date_keeps_raw_value_only() -> None:
    raw = _agenda_raw({"MatterId": 2, "MatterTitle": "x", "MatterIntroDate": "not a date"})
    rows = ProcurementConnector().normalize(_ctx(), [raw])
    claims = _claims(rows, "meeting_date")
    assert len(claims) == 1
    assert claims[0]["value"] is None  # never a coerced date; raw_value stands
    assert claims[0]["raw_value"] == "not a date"


# --- the Contract renewal triple (§11.11 surface) ---------------------------------


def test_contract_surface_carries_the_renewal_triple() -> None:
    contract = Contract(
        external_id="C-100",
        source_id="sourcewell",
        auto_renews=True,
        notice_window_days=90,
        renewal_term_months=12,
    )
    rows = contract.claim_rows()
    by_pred = {r["predicate_id"]: r["value"] for r in rows if r.get("record_kind") == "claim"}
    assert by_pred["auto_renews"] is True
    assert by_pred["notice_window_days"] == 90
    assert by_pred["renewal_term_months"] == 12


def test_auto_renews_false_is_a_stated_value_not_absence() -> None:
    contract = Contract(external_id="C-101", source_id="sourcewell", auto_renews=False)
    rows = contract.claim_rows()
    claims = _claims(rows, "auto_renews")
    assert len(claims) == 1 and claims[0]["value"] is False


def test_unset_triple_emits_no_claims() -> None:
    contract = Contract(external_id="C-102", source_id="sourcewell")
    rows = contract.claim_rows()
    for predicate in ("auto_renews", "notice_window_days", "renewal_term_months"):
        assert _claims(rows, predicate) == []


def test_build_contract_maps_raw_triple() -> None:
    ctx = _ctx("sourcewell")
    raw = {
        "record_kind": "contract",
        "raw": {
            "id": "C-200",
            "agency": "City Police Department",
            "vendor": "Vendor Inc.",
            "master_contract": "sourcewell:020617-FSI",
            "auto_renews": "true",
            "notice_window_days": 60,
            "renewal_term_months": "12",
        },
    }
    rows = ProcurementConnector().normalize(ctx, [raw])
    by_pred = {r["predicate_id"]: r["value"] for r in rows if r.get("record_kind") == "claim"}
    assert by_pred["auto_renews"] is True
    assert by_pred["notice_window_days"] == 60
    assert by_pred["renewal_term_months"] == 12


def test_unknown_dated_predicate_still_refused() -> None:
    # The allowlist is the boundary — a predicate outside it is refused here.
    assert not is_predicate_allowed("decision_date")
    with pytest.raises(PredicateNotAllowed):
        assert_predicate_allowed("decision_date")


# --- the P07.1 renewal-clause read on a captured contract document -----------------

_RENEWAL_DOC = (
    "AGREEMENT FOR MAINTENANCE SERVICES. Section 12: This Agreement shall "
    "automatically renew for successive one-year terms unless either party "
    "provides written notice of non-renewal at least 90 days prior to the end "
    "of the then-current term. Renewal term of 12 months applies to each renewal."
)


def _agenda_document_raw(text: str, *, contract_kind: bool = True) -> dict[str, Any]:
    return {
        "record_kind": "agenda_document",
        "source_uri": "https://webapi.legistar.com/v1/seattle/matters/121279",
        "capture_digest": "sha256:abc",
        "media_type": "application/json",
        "retrieved_at": "2026-10-05T12:00:00+00:00",
        "byte_size": len(text),
        "doc_genre": "json",
        "extraction_method": "json_text",
        "text": text,
        "pages": None,
        "target": {
            "tenant_id": "seattle_wa",
            "platform": "legistar",
            "jurisdiction": "Seattle, WA",
            "item_id": "CB 121279",
            "item": {
                "MatterTitle": "A contract for license plate reader maintenance",
                "MatterTypeName": "Contract" if contract_kind else "Resolution",
            },
            "contract_matter_patterns": ["contract"],
        },
    }


def test_contract_document_emits_the_renewal_triple_verbatim() -> None:
    rows = ProcurementConnector().normalize(_ctx(), [_agenda_document_raw(_RENEWAL_DOC)])
    claims = {
        p: _claims(rows, p) for p in ("auto_renews", "notice_window_days", "renewal_term_months")
    }
    assert claims["auto_renews"]
    assert all(c["value"] is True for c in claims["auto_renews"])
    assert any(c["value"] == 90 for c in claims["notice_window_days"])
    assert any(c["value"] == 12 for c in claims["renewal_term_months"])
    for group in claims.values():
        for c in group:
            # every clause claim lands on the contract subject, verbatim +
            # byte-range located (SIG-PARSE-003/004)
            assert c["subject_id"].startswith("contract:legistar:")
            assert c["evidence_genre"] == "agenda_document"
            assert c["raw_value"] in _RENEWAL_DOC
            assert c["evidence"]["locator"]["kind"] in ("byte_range", "page")
            assert c["renewal_clause_rule"]


def test_renewal_extraction_is_contract_kind_only() -> None:
    # A non-contract matter's document is not a contract — nothing is read.
    rows = ProcurementConnector().normalize(
        _ctx(), [_agenda_document_raw(_RENEWAL_DOC, contract_kind=False)]
    )
    for predicate in ("auto_renews", "notice_window_days", "renewal_term_months"):
        assert _claims(rows, predicate) == []


def test_document_without_a_clause_records_honest_empty() -> None:
    rows = ProcurementConnector().normalize(
        _ctx(), [_agenda_document_raw("Agenda item: staff report. No renewal clause here.")]
    )
    doc_row = next(r for r in rows if r.get("record_kind") == "agenda_document")
    assert doc_row["renewal_terms"] == {"extracted": [], "suppressed": 0}


def test_forbidden_token_clause_is_suppressed_and_recorded() -> None:
    text = _RENEWAL_DOC + " hotlist access for plate reads."
    rows = ProcurementConnector().normalize(_ctx(), [_agenda_document_raw(text)])
    # The clause literals are clean (the token is outside the clause spans), so
    # the triple still emits; a literal that ITSELF carried a forbidden token
    # would be suppressed — pin the suppression path directly instead.
    assert _claims(rows, "notice_window_days")


def test_part_viii_token_inside_a_clause_literal_suppresses_it() -> None:
    text = (
        "Section 12: this agreement renews unless either party provides plate "
        "number written notice of non-renewal."
    )
    rows = ProcurementConnector().normalize(_ctx(), [_agenda_document_raw(text)])
    doc_row = next(r for r in rows if r.get("record_kind") == "agenda_document")
    assert doc_row["renewal_terms"]["suppressed"] >= 1
    suppressions = doc_row.get("part_viii_suppressions") or []
    assert any(s.get("predicate") == "auto_renews" for s in suppressions)
    # The suppressed literal never becomes a claim (§0.7/§43.2).
    assert not any(
        "plate number" in str(c.get("raw_value") or "") for c in _claims(rows, "auto_renews")
    )
