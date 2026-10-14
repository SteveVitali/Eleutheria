# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P32.17 `sig.dossier-packet/1` → `sig.dossier-portfolio/1` — the
evidence-complete research-dossier machinery (ticket 178, SIG-DOS-001/002).

Drives the REAL `dossier_documents` connector over the committed OKC fixtures
(the landed P32.12 emit path — no network, a URL-keyed canned transport), then
composes `sig.dossier-packet/1` inputs around the emitted records. Covers every
contract row: the twelve-question schema + six-state vocabulary, the
fact-to-capture ledger, question-level absence rules, the independent
completion checklist, the 0–3 rubric + the 28/36 / q1·q5·q7·q8≥2 pilot gate,
fail-closed release validation (unsupported affirmative, misclassified
instrument, hidden conflict, fabricated absence, blank answers), the
six-state render incl. print-HTML qualifier/citation preservation, original
(publication/effective/coverage/as-of) vs capture-date discipline, actor
roles, decision windows, and the inventory-vs-research distinction.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from connectors.dossier_documents import crosswalk, vocab
from connectors.live_targets import live_targets
from connectors.net import PoliteFetcher, RateLimiter, RobotsResult
from connectors.okc_documents import assert_part_viii_safe  # noqa: F401 — keep the guard near
from connectors.pipeline import run
from connectors.registry import CompactStatus, get
from connectors.stages import (
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
    get_connector,
)
from evidence.ingest_run import IngestRun
from exports.research_dossier import (
    ACQ_COMMITTED_TRANSCRIPTION,
    ACQ_LIVE_CAPTURE,
    ACQ_STAND_IN,
    ANSWER_STATES,
    COMPLETE_MAX,
    COMPLETE_TOTAL,
    PACKET_SCHEMA,
    QUESTION_IDS,
    REQUIRED_CROSSWALK_FIELDS,
    REQUIRED_MINIMUM,
    SUBSCRIPTION_HARDWARE_GUARD,
    TEMPLATE_EXECUTION_GUARD,
    acquisition_label,
    build_dossier,
    build_portfolio,
    capture_chronology_violations,
    displayed_date_violations,
    render_dossier_print_html,
    render_portfolio_json,
    review_label,
    validate_packet,
)

_FIX = Path(__file__).resolve().parent.parent / "connectors" / "fixtures" / "dossier"
#: The canned transport's stamp — a simulated live-fetch date, the ONE date
#: source every synthetic record/assertion in this file derives from (P34.22b:
#: a date is bound to the clock that stamped it, never re-typed downstream).
_RETRIEVED = datetime(2026, 10, 1, tzinfo=UTC)
_RETRIEVED_DATE = _RETRIEVED.date().isoformat()
_ALLOW_ALL = "User-agent: *\nAllow: /\n"
CONNECTOR = "dossier_documents"

#: doc_id -> (fixture file, media type) — mirrors tests/connectors/test_dossier_documents.py.
FIXTURE_FOR_DOC: dict[str, tuple[str, str]] = {
    "okc-flock-usage-2026": ("okc_usage_page.html", "text/html"),
    "okc-council-memo-2026-08": ("okc_council_memo_2026.pdf", "application/pdf"),
    "okc-flock-amendment-2026": ("okc_amendment_1_2026.pdf", "application/pdf"),
    "tulsa-mou-template": ("tulsa_mou_template.pdf", "application/pdf"),
    "tulsa-policy-113c": ("tulsa_policy_113c.pdf", "application/pdf"),
    "tulsa-policy-113e": ("tulsa_policy_113e.pdf", "application/pdf"),
    "sd-asr-2025-vigilant": ("sd_asr_2025_vigilant.pdf", "application/pdf"),
    "sd-ubicquia-agreement-2023": ("sd_ubicquia_agreement_2023.pdf", "application/pdf"),
    "sd-technology-index": ("sd_technology_index.html", "text/html"),
    "sd-pab-index": ("sd_pab_index.html", "text/html"),
}

_OKC_DOCS = ("okc-flock-usage-2026", "okc-council-memo-2026-08", "okc-flock-amendment-2026")


class _MapTransport:
    """URL-keyed canned responses — no real network (SIG-INGEST-011)."""

    def __init__(self) -> None:
        self.responses: dict[str, tuple[bytes, str]] = {}
        self.requested: list[str] = []

    def add_url(self, url: str, body: bytes, media: str) -> None:
        self.responses[url] = (body, media)

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ALLOW_ALL, status=200)

    def request(
        self, url: str, *, user_agent: str, headers: Any = None, body: bytes | None = None
    ) -> FetchResult:
        self.requested.append(url)
        if url in self.responses:
            resp_body, media = self.responses[url]
            return FetchResult(
                url=url,
                status=200,
                body=resp_body,
                media_type=media,
                retrieved_at=_RETRIEVED,
            )
        return FetchResult(
            url=url, status=404, body=b"", media_type="text/plain", retrieved_at=_RETRIEVED
        )


def _targets(source_id: str, doc_ids: tuple[str, ...]) -> list[dict[str, Any]]:
    out = []
    for target in live_targets(source_id):
        doc_id = str(target.get("doc_id") or target.get("id"))
        if doc_id in doc_ids:
            import copy

            out.append(copy.deepcopy(target))
    return out


def _ctx(source_id: str, targets: list[dict[str, Any]]) -> RunContext:
    source = dataclasses.replace(
        get(source_id),
        ingestion_permitted=True,
        compact_status=CompactStatus.PUBLIC_TERMS_ONLY,
    )
    transport = _MapTransport()
    for target in targets:
        doc_id = str(target.get("doc_id") or target.get("id"))
        name, media = FIXTURE_FOR_DOC[doc_id]
        transport.add_url(str(target["url"]), (_FIX / name).read_bytes(), media)
    fetcher = PoliteFetcher(
        connector_name=CONNECTOR,
        connector_version="1.0.0",
        transport=transport,
        rate_limiter=RateLimiter(sleep=lambda s: None),
    )
    return RunContext(
        source=source,
        run=IngestRun(CONNECTOR, "1.0.0", "deadbeef", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": targets},
    )


@pytest.fixture(scope="module")
def okc_records() -> list[dict[str, Any]]:
    """The REAL emitted `dossier_documents` records over the OKC fixtures."""
    connector = get_connector(CONNECTOR)()
    targets = _targets("dossier_okc", _OKC_DOCS)
    report = run(connector, _ctx("dossier_okc", targets))
    return [dict(r) for r in report.claims]


def _search_entry(qid: str, outcome: str = "searched_not_found") -> dict[str, Any]:
    return {
        "question": qid,
        "sought": f"the {qid} answer",
        "sources_searched": ["dossier_contracts", "dossier_admin"],
        "searched_at": _RETRIEVED_DATE,
        "outcome": outcome,
        "scope_note": "city-owned deployment scope only",
        "note": "recorded search",
    }


def _follow_up(qid: str) -> dict[str, Any]:
    return {
        "question": qid,
        "action": f"obtain a record establishing the {qid} answer",
        "next_evidence": "the named document or the agency's written no-records response",
        "closing_condition": "a captured document settles the field, or the agency "
        "states in writing that no such record exists",
    }


def _packet(
    records: list[dict[str, Any]],
    *,
    unknown_qs: tuple[str, ...] = ("q1", "q2", "q4", "q10"),
    declared: dict[str, Any] | None = None,
    review: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The OKC packet: real emitted records + documented unknowns + follow-ups."""
    packet: dict[str, Any] = {
        "schema": PACKET_SCHEMA,
        "dossier_id": "okc-alpr",
        "subject": {
            "slug": "okc-alpr",
            "label": "Oklahoma City ALPR programme",
            "jurisdiction": "Oklahoma City, Oklahoma",
            "jurisdiction_slug": "oklahoma-city",
        },
        "as_of": {"world": _RETRIEVED_DATE, "belief": _RETRIEVED_DATE},
        "records": records,
        "search_log": [_search_entry(q) for q in unknown_qs],
        "follow_ups": [_follow_up(q) for q in unknown_qs],
        "review": review or {"status": "not_run", "reviewer_role": "independent semantic reviewer"},
    }
    if declared:
        packet["declared"] = declared
    if extra:
        packet.update(extra)
    return packet


def _fake_claim(
    qid: str,
    predicate: str,
    value: Any,
    *,
    doc: str = "synth-doc",
    field: str = "synth_field",
    qualifiers: list[dict[str, Any]] | None = None,
    valid_from: str | None = None,
    valid_to: str | None = None,
    genre: str = "executed_contract",
    field_state: str | None = None,
    value_kind: str | None = None,
) -> dict[str, Any]:
    """A synthetic emitted-claim record (the dossier_claim shape)."""
    claim: dict[str, Any] = {
        "record_kind": "claim",
        "connector": "dossier_documents",
        "source_id": "dossier_test",
        "subject_id": "sig:deployment:test",
        "predicate_id": predicate,
        "value": value,
        "raw_value": str(value),
        "document_genre": genre,
        "evidence_genre": genre,
        "document_id": doc,
        "source_field": field,
        "dossier_field": qid,
        "sensitivity_class": "C1",
        "assertion_rationale": "test assertion",
        "evidence": {
            "source_url": f"https://example/{doc}",
            "retrieved_date": _RETRIEVED_DATE,
            "extraction_method": "html_text",
            "locator": {"locator": "clause 1"},
        },
        "observed_at": _RETRIEVED_DATE,
        "source_attribution": "dossier_test",
    }
    if qualifiers:
        claim["qualifiers"] = qualifiers
    if valid_from:
        claim["valid_from"] = valid_from
        claim["valid_from_kind"] = "exact"
    if valid_to:
        claim["valid_to"] = valid_to
        claim["valid_to_kind"] = "exact"
    if field_state:
        claim["field_state"] = field_state
    if value_kind:
        claim["value_kind"] = value_kind
    return claim


def _artifact(doc: str = "synth-doc") -> dict[str, Any]:
    return {
        "record_kind": "evidence_artifact",
        "connector": "dossier_documents",
        "source_id": "dossier_test",
        "source_uri": f"https://example/{doc}",
        "capture_digest": f"cap-{doc}",
        "media_type": "text/html",
        "byte_size": 100,
        "document_id": doc,
        "document_genre_derived": "executed_contract",
        "evidence_genre": "executed_contract",
        "access_mode": "document",
        "method": "html_text",
        "retrieved_date": _RETRIEVED_DATE,
        "sensitivity_class": "C1",
    }


# --------------------------------------------------------------------------- #
# AC1 — every question represented with a legal state + basis
# --------------------------------------------------------------------------- #


def test_every_question_present_with_legal_state(okc_records: list[dict[str, Any]]) -> None:
    dossier = build_dossier(_packet(okc_records))
    assert len(dossier["answers"]) == 12
    assert [a["question"] for a in dossier["answers"]] == list(QUESTION_IDS)
    for a in dossier["answers"]:
        assert a["state"] in ANSWER_STATES
        # evidence-backed answers cite assertions; unknowns cite a search basis
        if a["state"] == "unknown":
            assert a["search_basis"] and a["search_basis"]["outcome"] in {
                "searched_not_found",
                "access_blocked",
                "version_unverified",
                "not_researched",
            }
        assert isinstance(a["score"], int) and 0 <= a["score"] <= 3


def test_blank_fields_cannot_inflate_completeness(okc_records: list[dict[str, Any]]) -> None:
    """An undocumented unknown (no search basis, no follow-up) scores 0 and
    draws release violations — it cannot pass off as a covered question."""
    packet = _packet(okc_records, unknown_qs=())
    dossier = build_dossier(packet)
    by_q = {a["question"]: a for a in dossier["answers"]}
    assert by_q["q1"]["state"] == "unknown"
    assert by_q["q1"]["score"] == 0
    codes = {v["code"] for v in dossier["release"]["violations"]}
    assert "unknown_without_basis" in codes
    assert "unknown_without_followup" in codes
    # A blank unknown is NOT a hidden 'searched_not_found' — the mechanical
    # fill records the honest worst basis.
    fill = next(e for e in dossier["search_log"] if e["question"] == "q1")
    assert fill["outcome"] == "not_researched" and fill["declared"] is False


def test_packet_schema_validation(okc_records: list[dict[str, Any]]) -> None:
    assert validate_packet(_packet(okc_records)) == []
    assert validate_packet({"schema": "nope"}) != []
    bad = _packet(okc_records)
    bad["declared"] = {"not_applicable": [{"question": "q99", "rationale": "x"}]}
    assert validate_packet(bad) != []
    with pytest.raises(ValueError, match="invalid"):
        build_dossier({"schema": "nope"})


def test_kind_is_research_dossier_not_inventory(okc_records: list[dict[str, Any]]) -> None:
    dossier = build_dossier(_packet(okc_records))
    assert dossier["kind"] == "research_dossier"
    assert dossier["schema"] == "sig.research-dossier/1"


# --------------------------------------------------------------------------- #
# AC2 — fail-closed release validation vs honest unknowns
# --------------------------------------------------------------------------- #


def test_honest_researched_unknowns_pass_release(okc_records: list[dict[str, Any]]) -> None:
    dossier = build_dossier(_packet(okc_records))
    assert dossier["release"]["valid"]
    for a in dossier["answers"]:
        if a["state"] == "unknown":
            assert a["search_basis"]["sources_searched"]
            assert a["follow_ups"] and a["follow_ups"][0]["closing_condition"]


def test_unsupported_affirmative_fails_release() -> None:
    """A supported answer whose assertion has no capture binding / locator
    fails release validation — the affirmative claim is unsupported."""
    records = [_artifact()]
    claim = _fake_claim("q5", "contract_value", 100000)
    claim["evidence"]["locator"] = None  # no locator — an uncitable claim
    records.append(claim)
    dossier = build_dossier(_packet(records, unknown_qs=()))
    assert not dossier["release"]["valid"]
    assert any(
        v["code"] == "unsupported_affirmative_claim" for v in dossier["release"]["violations"]
    )


def test_missing_capture_binding_fails_release() -> None:
    records = [_fake_claim("q5", "contract_value", 100000, doc="no-artifact-doc")]
    dossier = build_dossier(_packet(records, unknown_qs=()))
    assert any(
        v["code"] == "unsupported_affirmative_claim" for v in dossier["release"]["violations"]
    )


def test_misclassified_instrument_fails_release() -> None:
    """A template asserting an executed-instrument predicate is caught by the
    release-side twin of the connector's emit guard."""
    records = [
        _artifact(),
        _fake_claim("q5", "signed_date", "2026-08-01", genre="template"),
    ]
    dossier = build_dossier(_packet(records, unknown_qs=()))
    assert not dossier["release"]["valid"]
    assert any(v["code"] == "misclassified_instrument" for v in dossier["release"]["violations"])


def test_subscription_hardware_guard_fails_release() -> None:
    records = [
        _artifact(),
        _fake_claim("q3", "claimed_device_count", 42, genre="subscription"),
    ]
    dossier = build_dossier(_packet(records, unknown_qs=()))
    assert any(v["code"] == "misclassified_instrument" for v in dossier["release"]["violations"])


def test_derived_hides_conflict_fails_release() -> None:
    """A derived answer that excludes one side of a same-scope conflict is a
    hidden conflict — fail closed (the answer must be disputed)."""
    records = [
        _artifact(),
        _fake_claim("q3", "claimed_device_count", 190, doc="synth-doc"),
        _fake_claim(
            "q3",
            "claimed_device_count",
            299,
            doc="synth-doc2",
            qualifiers=[{"predicate": "count_scope", "value": "metro"}],
        ),
    ]
    records.append(_artifact("synth-doc2"))
    # Same scope (empty vs metro)? — make them BOTH unscoped so scopes match.
    records[2]["qualifiers"] = []
    from db.claim_sink import content_digest

    declared = {
        "derived": [
            {
                "question": "q3",
                "method": "sum",
                "value": 299,
                "inputs": [content_digest(records[2])],
            }
        ]
    }
    dossier = build_dossier(_packet(records, unknown_qs=(), declared=declared))
    assert any(v["code"] == "derived_hides_conflict" for v in dossier["release"]["violations"])


def test_not_applicable_with_evidence_fails_release() -> None:
    records = [_artifact(), _fake_claim("q4", "configured_access_edge", "vigilant")]
    declared = {"not_applicable": [{"question": "q4", "rationale": "no external access"}]}
    dossier = build_dossier(_packet(records, unknown_qs=(), declared=declared))
    assert any(
        v["code"] == "not_applicable_with_evidence" for v in dossier["release"]["violations"]
    )
    # and the suppressed evidence is still on the ledger — a reviewer can see it.
    assert any(r["state"] == "suppressed" and r["question"] == "q4" for r in dossier["ledger"])


def test_withheld_without_basis_fails_release() -> None:
    records = [_artifact(), _fake_claim("q8", "sharing_restriction", "no federal")]
    declared = {"withheld": [{"question": "q8", "basis": "", "reason": ""}]}
    dossier = build_dossier(_packet(records, unknown_qs=(), declared=declared))
    assert any(v["code"] == "withheld_without_basis" for v in dossier["release"]["violations"])


def test_derived_unresolved_inputs_fail_release() -> None:
    declared = {
        "derived": [{"question": "q3", "method": "sum", "value": 5, "inputs": ["deadbeef" * 8]}]
    }
    dossier = build_dossier(_packet([], unknown_qs=(), declared=declared))
    assert any(v["code"] == "derived_unresolved_inputs" for v in dossier["release"]["violations"])


def test_blank_derived_answer_fails_release() -> None:
    declared = {"derived": [{"question": "q3", "method": "", "value": None, "inputs": []}]}
    dossier = build_dossier(_packet([], unknown_qs=(), declared=declared))
    assert any(v["code"] == "blank_answer" for v in dossier["release"]["violations"])


def test_fabricated_absence_fails_release() -> None:
    """A documented searched_not_found on a question that holds evidence claims
    is a fabricated absence — never 'no record found' → 'no system'."""
    records = [_artifact(), _fake_claim("q5", "contract_value", 100000)]
    packet = _packet(records, unknown_qs=())
    packet["search_log"].append(_search_entry("q5"))
    dossier = build_dossier(packet)
    assert any(v["code"] == "absence_fabricated" for v in dossier["release"]["violations"])


def test_restricted_claim_rendered_fails_release() -> None:
    claim = _fake_claim("q5", "contract_value", 100000)
    records = [_artifact(), claim]
    from db.claim_sink import content_digest

    packet = _packet(records, unknown_qs=())
    packet["restricted"] = [{"digest": content_digest(claim), "reason": "under rights review"}]
    dossier = build_dossier(packet)
    assert any(v["code"] == "restricted_claim_rendered" for v in dossier["release"]["violations"])


# --------------------------------------------------------------------------- #
# AC3 — same-scope conflict visibility + rendering fidelity
# --------------------------------------------------------------------------- #


def test_same_scope_conflict_renders_disputed() -> None:
    records = [
        _artifact(),
        _fake_claim("q3", "claimed_device_count", 190, doc="synth-doc"),
        _fake_claim("q3", "claimed_device_count", 299, doc="synth-doc"),
    ]
    dossier = build_dossier(_packet(records, unknown_qs=()))
    q3 = next(a for a in dossier["answers"] if a["question"] == "q3")
    assert q3["state"] == "disputed"
    # BOTH competing values stay visible — nothing collapses to a winner.
    values = sorted(x["value"] for x in q3["assertions"])
    assert values == [190, 299]
    assert all(x.get("conflicting") for x in q3["assertions"])
    assert "Same-scope" in q3["summary"]


def test_different_scope_is_not_a_conflict() -> None:
    """The §29 discipline: '42 metro' vs '38 city limits' are different
    quantities — co-visible scoped assertions, never a false contradiction."""
    records = [
        _artifact(),
        _fake_claim(
            "q3",
            "claimed_device_count",
            190,
            doc="synth-doc",
            qualifiers=[{"predicate": "count_scope", "value": "city_limits"}],
        ),
        _fake_claim(
            "q3",
            "claimed_device_count",
            299,
            doc="synth-doc",
            qualifiers=[{"predicate": "count_scope", "value": "metro"}],
        ),
    ]
    dossier = build_dossier(_packet(records, unknown_qs=()))
    q3 = next(a for a in dossier["answers"] if a["question"] == "q3")
    assert q3["state"] == "supported"
    scopes = {x["scope"]["count_scope"] for x in q3["assertions"]}
    assert scopes == {"city_limits", "metro"}


def test_different_subjects_are_not_a_conflict() -> None:
    """P32.20: two conflict-eligible claims about DIFFERENT subjects describe
    different measured things — a hosted subscription's vendor and a separate
    contract's component vendor co-exist; only same-subject disagreement flags."""
    records = [
        _artifact(),
        {
            **_fake_claim("q1", "vendor", "Vendor A", doc="synth-doc"),
            "subject_id": "sig:deployment:subscription",
        },
        {
            **_fake_claim("q1", "vendor", "Vendor B", doc="synth-doc"),
            "subject_id": "contract:some-agreement",
        },
    ]
    dossier = build_dossier(_packet(records, unknown_qs=()))
    q1 = next(a for a in dossier["answers"] if a["question"] == "q1")
    assert q1["state"] == "supported"
    assert not any(x.get("conflicting") for x in q1["assertions"])
    values = sorted(x["value"] for x in q1["assertions"])
    assert values == ["Vendor A", "Vendor B"]
    # Same values on the SAME subject still flag — the detector's purpose.
    same = [
        _artifact(),
        _fake_claim("q1", "vendor", "Vendor A", doc="synth-doc"),
        _fake_claim("q1", "vendor", "Vendor B", doc="synth-doc"),
    ]
    q1_same = next(
        a for a in build_dossier(_packet(same, unknown_qs=()))["answers"] if a["question"] == "q1"
    )
    assert q1_same["state"] == "disputed"
    assert all(x.get("conflicting") for x in q1_same["assertions"])


def test_verbatim_clauses_do_not_conflict(okc_records: list[dict[str, Any]]) -> None:
    """Two different stated clause texts are two rules — never a contradiction."""
    dossier = build_dossier(_packet(okc_records))
    q7 = next(a for a in dossier["answers"] if a["question"] == "q7")
    # The fixture emits retention_period + TWO use_restriction clauses — the
    # verbatim predicates must not fabricate a dispute.
    assert q7["state"] == "supported"
    assert any(x["predicate"] == "use_restriction" for x in q7["assertions"])


def test_date_semantics_preserved(okc_records: list[dict[str, Any]]) -> None:
    """Original dates (valid_*/as-of/posted) stay distinct from capture
    (retrieved/observed) dates — a posting date never promotes to effective."""
    dossier = build_dossier(_packet(okc_records))
    q9 = next(a for a in dossier["answers"] if a["question"] == "q9")
    as_of_claim = next(x for x in q9["assertions"] if x["predicate"] == "as_of")
    assert as_of_claim["value"] == "2026-08-18"
    # The record's declared data-currency date is NOT its retrieval date —
    # the stamp is the transport's own, derived never re-typed.
    assert as_of_claim["retrieved_date"] == _RETRIEVED_DATE
    assert as_of_claim["retrieved_date"] != as_of_claim["value"]


def test_fact_to_capture_ledger(okc_records: list[dict[str, Any]]) -> None:
    dossier = build_dossier(_packet(okc_records))
    rendered = [
        r
        for r in dossier["ledger"]
        if r["state"] == "rendered" and r["predicate"] != "evidence_profile"
    ]
    assert rendered
    for row in rendered:
        assert row["claim_digest"] and len(row["claim_digest"]) == 64
        assert row["capture_digest"], f"{row['fact']} lacks a capture binding"
        assert row["locator"]
        assert row["source_url"] and row["retrieved_date"]
    # Every rendered assertion maps to exactly one ledger row.
    total_assertions = sum(len(a.get("assertions") or ()) for a in dossier["answers"])
    assert total_assertions == len(rendered)


def test_actor_roles_stay_distinct() -> None:
    records = [
        _artifact(),
        _fake_claim("q1", "buyer", "City of OKC", doc="synth-doc"),
        _fake_claim("q1", "vendor", "Flock Safety", doc="synth-doc"),
    ]
    dossier = build_dossier(_packet(records, unknown_qs=()))
    q1 = next(a for a in dossier["answers"] if a["question"] == "q1")
    preds = {x["predicate"] for x in q1["assertions"]}
    assert preds == {"buyer", "vendor"}  # never collapsed into one 'operator'


def test_decision_windows() -> None:
    records = [
        _artifact(),
        _fake_claim(
            "q5",
            "contract_end_date",
            "2027-06-30",  # future-ok: synthetic: synth-doc
            doc="synth-doc",
        ),
        _fake_claim("q9", "posted_date", "2026-08-18", doc="synth-doc"),
    ]
    dossier = build_dossier(_packet(records, unknown_qs=()))
    dw = dossier["decision_windows"]
    assert dw["next_decision_date"] == "2027-06-30"  # future-ok: synthetic: synth-doc claim
    preds = {w["predicate"] for w in dw["windows"]}
    assert {"contract_end_date", "posted_date"} <= preds


def test_withheld_renders_state_not_value() -> None:
    claim = _fake_claim("q8", "sharing_restriction", "confidential clause")
    records = [_artifact(), claim]
    declared = {
        "withheld": [
            {
                "question": "q8",
                "basis": "Part VIII sensitivity review",
                "reason": "the clause's detail is restricted pending rights review",
            }
        ]
    }
    dossier = build_dossier(_packet(records, unknown_qs=(), declared=declared))
    q8 = next(a for a in dossier["answers"] if a["question"] == "q8")
    assert q8["state"] == "withheld"
    assert q8["assertions"] == []  # the value is never rendered
    # The ledger keeps only the digest — citation without the leaked fact.
    row = next(r for r in dossier["ledger"] if r["question"] == "q8")
    assert row["state"] == "withheld" and row["fact"] == "(withheld)"
    assert "confidential" not in json.dumps(q8)
    # …and the withheld value leaks nowhere in the emitted dossier at all.
    assert "confidential clause" not in json.dumps(dossier)


def test_redacted_field_renders_somevalue() -> None:
    records = [
        _artifact(),
        _fake_claim(
            "q7",
            "retention_period",
            None,
            doc="synth-doc",
            field_state="redacted",
            value_kind="somevalue",
        ),
    ]
    dossier = build_dossier(_packet(records, unknown_qs=()))
    q7 = next(a for a in dossier["answers"] if a["question"] == "q7")
    assert q7["state"] == "supported"
    assert q7["assertions"][0]["field_state"] == "redacted"
    assert q7["assertions"][0]["value"] is None
    assert q7["score"] == 2  # a redacted field is partial, never fully scoped


# --------------------------------------------------------------------------- #
# AC4 — rubric + the portfolio gate
# --------------------------------------------------------------------------- #


def _complete_records() -> list[dict[str, Any]]:
    """A synthetic packet whose dossier is mechanically complete — every
    question answered on a scoped/dated basis (score 3 for q1–q10)."""
    records = [_artifact(), _artifact("synth-doc2")]
    records += [
        _fake_claim("q1", "buyer", "City of OKC", valid_from="2026-07-01"),
        _fake_claim("q1", "vendor", "Flock Safety", valid_from="2026-07-01"),
        _fake_claim("q2", "technology", "Flock fixed ALPR", valid_from="2026-07-01"),
        _fake_claim(
            "q3",
            "claimed_device_count",
            90,
            qualifiers=[{"predicate": "count_scope", "value": "city_limits"}],
            valid_from="2026-07-01",
        ),
        _fake_claim(
            "q4",
            "configured_access_edge",
            "vigilant pooled lookup",
            qualifiers=[{"predicate": "access_scope", "value": "configured"}],
            valid_from="2026-07-01",
        ),
        _fake_claim("q5", "contract_value", 270000, valid_from="2026-07-01"),
        _fake_claim("q6", "legal_authority", "OKC Ordinance 26-100", valid_from="2026-07-01"),
        _fake_claim("q7", "retention_period", "7 days", valid_from="2026-07-01"),
        _fake_claim("q8", "sharing_restriction", "no federal disclosure", valid_from="2026-07-01"),
        _fake_claim("q9", "effective_from", "2026-07-01"),
        _fake_claim("q10", "document", "https://example/oversight.pdf", valid_from="2026-07-01"),
    ]
    return records


def test_rubric_gate_mechanical_complete() -> None:
    dossier = build_dossier(_packet(_complete_records(), unknown_qs=()))
    comp = dossier["completeness"]
    assert comp["total"] >= COMPLETE_TOTAL
    assert comp["mechanical_complete"] is True
    for q, floor in REQUIRED_MINIMUM.items():
        assert comp["per_question"][q] >= floor, q
    # …but pilot_complete stays false while the independent review is not_run —
    # the machinery never fabricates the human mark (D-R10-HUMAN-1).
    assert comp["pilot_complete"] is False
    assert any("independent_review" in b for b in comp["blocking"])


def test_pilot_complete_only_with_completed_review() -> None:
    dossier = build_dossier(
        _packet(
            _complete_records(),
            unknown_qs=(),
            review={
                "status": "completed",
                "reviewer_role": "independent semantic reviewer",
                "completed_at": "2026-10-02",
                "scope": "material governance/contract/relationship assertions",
                "notes": ["reviewed all 12 answers against the cited captures"],
            },
        )
    )
    assert dossier["completeness"]["pilot_complete"] is True
    assert dossier["release"]["valid"]


def test_lower_score_stays_incomplete(okc_records: list[dict[str, Any]]) -> None:
    dossier = build_dossier(_packet(okc_records))
    comp = dossier["completeness"]
    # The four searched-but-unanswered questions keep the packet incomplete in
    # the dimension the gate enforces: q1 scores below its required floor even
    # though the numeric total reaches the 28 line — a total alone never passes.
    assert comp["per_question"]["q1"] < REQUIRED_MINIMUM["q1"]
    assert any("q1" in b for b in comp["blocking"])
    assert comp["mechanical_complete"] is False
    assert comp["pilot_complete"] is False
    assert comp["max"] == COMPLETE_MAX == 36


def test_scores_follow_the_rubric() -> None:
    # 0 = unresearched, 1 = documented unknown, 2 = traceable partial, 3 = scoped.
    records = [_artifact(), _fake_claim("q3", "claimed_device_count", 90)]  # unscoped
    dossier = build_dossier(_packet(records, unknown_qs=()))
    q3 = next(a for a in dossier["answers"] if a["question"] == "q3")
    assert q3["score"] == 2  # traceable but missing the count universe
    q1 = next(a for a in dossier["answers"] if a["question"] == "q1")
    assert q1["score"] == 0  # no basis, no follow-up → unresearched


def test_not_applicable_scores_when_valid() -> None:
    declared = {
        "not_applicable": [
            {
                "question": "q4",
                "rationale": (
                    "the deployment is a standalone local system with no "
                    "external/hosted data-system relationship"
                ),
            }
        ]
    }
    dossier = build_dossier(_packet([], unknown_qs=(), declared=declared))
    q4 = next(a for a in dossier["answers"] if a["question"] == "q4")
    assert q4["state"] == "not_applicable" and q4["score"] == 3
    assert dossier["release"]["valid"] is False or all(
        v["question"] != "q4" for v in dossier["release"]["violations"]
    )


# --------------------------------------------------------------------------- #
# AC5 — the independent completion checklist
# --------------------------------------------------------------------------- #


def test_completion_checklist_items(okc_records: list[dict[str, Any]]) -> None:
    dossier = build_dossier(_packet(okc_records))
    items = {c["item"]: c["status"] for c in dossier["checklist"]}
    for required in (
        "all_twelve_questions_present",
        "states_legal",
        "affirmatives_evidence_backed",
        "search_log_complete",
        "same_scope_conflicts_visible",
        "scope_and_time_comparable",
        "instrument_genre_classified",
        "independent_semantic_review",
        "restrictions_consumed",
        "rubric_threshold",
        "no_unsupported_claims",
    ):
        assert required in items, required
    # The review mark is honest — not_run is a real state, never green.
    assert items["independent_semantic_review"] == "fail"


# --------------------------------------------------------------------------- #
# AC6 — renderers + mirrors + portfolio
# --------------------------------------------------------------------------- #


def test_portfolio_json_and_summary(okc_records: list[dict[str, Any]]) -> None:
    portfolio = build_portfolio([_packet(okc_records), _packet(_complete_records(), unknown_qs=())])
    assert portfolio["schema"] == "sig.dossier-portfolio/1"
    assert portfolio["summary"]["dossier_count"] == 2
    data = render_portfolio_json(portfolio)
    reparsed = json.loads(data)
    assert reparsed["schema"] == "sig.dossier-portfolio/1"
    assert len(reparsed["dossiers"]) == 2


def test_print_html_preserves_qualifiers_and_citations() -> None:
    scope = [{"predicate": "count_scope", "value": "city_limits"}]
    records = [
        _artifact(),
        _fake_claim(
            "q3",
            "claimed_device_count",
            190,
            doc="synth-doc",
            qualifiers=scope,
            valid_from="2026-01-01",
        ),
        _fake_claim("q3", "claimed_device_count", 299, doc="synth-doc", qualifiers=list(scope)),
    ]
    dossier = build_dossier(_packet(records, unknown_qs=()))
    q3 = next(a for a in dossier["answers"] if a["question"] == "q3")
    assert q3["state"] == "disputed"
    html_doc = render_dossier_print_html(dossier)
    assert "disputed" in html_doc
    assert "count_scope=city_limits" in html_doc  # the qualifier survives print
    assert "cap-synth-doc" in html_doc  # the capture digest is a printed citation
    assert f"retrieved {_RETRIEVED_DATE}" in html_doc  # the capture date is shown
    assert "valid 2026-01-01" in html_doc  # the document's own date is shown
    assert "≠" in html_doc  # the conflict marker survives
    assert "next_decision_date" in html_doc
    assert "Completion checklist" in html_doc


def test_guard_lists_mirror_the_vocab_toml() -> None:
    """The release-side guard lists must equal the connector's emit-time
    vocabulary — drift between the two is caught here, not in production."""
    assert set(TEMPLATE_EXECUTION_GUARD) == set(vocab()["template_execution_guard"])
    assert set(SUBSCRIPTION_HARDWARE_GUARD) == set(vocab()["subscription_hardware_guard"])
    required = {name for name, row in crosswalk()["fields"].items() if row.get("required")}
    assert set(REQUIRED_CROSSWALK_FIELDS) == required


def test_cli_dossier_portfolio(tmp_path: Path, okc_records: list[dict[str, Any]]) -> None:
    """`sig-exports dossier-portfolio` writes web/research_dossiers.json + the
    print HTML, and exits 4 when a dossier is release-invalid."""
    import exports.cli as cli

    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(_packet(okc_records)), encoding="utf-8")
    out = tmp_path / "out"
    code = cli.main(["dossier-portfolio", "--packet", str(packet_path), "--out", str(out)])
    assert code == 0
    artifact = json.loads((out / "web" / "research_dossiers.json").read_text())
    assert artifact["schema"] == "sig.dossier-portfolio/1"
    print_html = (out / "web" / "research_dossier" / "okc-alpr.print.html").read_text()
    # P34.35 (F-153): the print's review wording derives from the recorded
    # status — "reviewed" is never hard-coded against a `not_run` mark.
    assert "Reviewed research dossier" not in print_html
    assert "independent review not yet run" in print_html


def test_cli_dossier_portfolio_fails_closed(tmp_path: Path) -> None:
    import exports.cli as cli

    records = [_artifact(), _fake_claim("q5", "signed_date", "2026-08-01", genre="template")]
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(_packet(records, unknown_qs=())), encoding="utf-8")
    out = tmp_path / "out"
    code = cli.main(["dossier-portfolio", "--packet", str(packet_path), "--out", str(out)])
    assert code == 4  # misclassified instrument → release-invalid


def test_spine_export_emits_research_dossiers_surface() -> None:
    """`web/research_dossiers.json` lands in the export's web artifacts when
    packets are supplied, and nowhere when they are not (honest absence)."""
    sys.path.insert(0, str(Path(__file__).parent))
    import test_spine_export as se

    export = se._build(se._site("A", "35.46", "-97.51", "Oklahoma"))
    assert "web/research_dossiers.json" not in export.web_artifacts

    records = [_artifact(), _fake_claim("q5", "contract_value", 100000)]
    export = se._build(
        se._site("A", "35.46", "-97.51", "Oklahoma"),
        dossier_packets=[_packet(records, unknown_qs=())],
    )
    assert "web/research_dossiers.json" in export.web_artifacts


# --------------------------------------------------------------------------- #
# P34.35 — acquisition labels, review label, true dates, licence/permalink
# (C4 NEW-2/NEW-3/NEW-22/NEW-23/NEW-32, F-152/F-153, F-16, DR-C4-03/04/15)
# --------------------------------------------------------------------------- #


def _standin_artifact(doc: str = "standin-doc") -> dict[str, Any]:
    """A document artifact whose bytes are hand-authored committed stand-ins."""
    art = _artifact(doc)
    art["capture_kind"] = "stand-in"
    art["committed_at"] = "2026-09-27T12:06:40+00:00"
    del art["retrieved_date"]
    return art


def _standin_claim(
    qid: str, predicate: str, value: Any, doc: str = "standin-doc"
) -> dict[str, Any]:
    """A declared stand-in claim — hand-authored bytes, never retrieved."""
    claim = _fake_claim(qid, predicate, value, doc=doc)
    claim["capture_kind"] = "stand-in"
    claim["committed_at"] = "2026-09-27"
    del claim["evidence"]["retrieved_date"]  # a stand-in was never retrieved
    return claim


def _transcription_artifact(doc: str = "transcription-doc") -> dict[str, Any]:
    """An artifact bound to committed transcription bytes (the P06.1 posture)."""
    art = _artifact(doc)
    art["method"] = "fixture_transcription"
    art["access_mode"] = "committed_fixture"
    art["committed_at"] = "2026-09-13T20:21:05+00:00"
    del art["retrieved_date"]
    return art


def _transcription_claim(
    qid: str, predicate: str, value: Any, doc: str = "transcription-doc"
) -> dict[str, Any]:
    """A claim replayed over committed transcription bytes."""
    claim = _fake_claim(qid, predicate, value, doc=doc)
    claim["capture_kind"] = "fixture_replay"
    claim["committed_at"] = "2026-09-13"
    claim["evidence"]["extraction_method"] = "fixture_transcription"
    del claim["evidence"]["retrieved_date"]
    return claim


def _all_assertions(dossier: dict[str, Any]) -> list[dict[str, Any]]:
    return [x for a in dossier["answers"] for x in a["assertions"]]


def test_acquisition_three_way_mixed_dossier(okc_records: list[dict[str, Any]]) -> None:
    """A fixture dossier mixing live, transcribed and stand-in evidence marks
    every rendered assertion's acquisition correctly (DR-C4-03)."""
    records = list(okc_records)  # the canned-live connector emissions
    records += [
        _standin_artifact(),
        _transcription_artifact(),
        _standin_claim("q1", "buyer", "City of Oklahoma City"),
        _transcription_claim("q1", "vendor", "Flock Safety"),
    ]
    dossier = build_dossier(_packet(records))
    assertions = _all_assertions(dossier)
    by_doc: dict[str, list[dict[str, Any]]] = {}
    for x in assertions:
        by_doc.setdefault(str(x["document_id"]), []).append(x)
    # canned-live claims (document access + a real retrieval stamp) → live capture
    live_docs = {d for d in by_doc if d not in {"standin-doc", "transcription-doc"}}
    assert live_docs
    for d in live_docs:
        assert all(x["acquisition"] == ACQ_LIVE_CAPTURE for x in by_doc[d])
    assert by_doc["standin-doc"][0]["acquisition"] == ACQ_STAND_IN
    assert by_doc["transcription-doc"][0]["acquisition"] == ACQ_COMMITTED_TRANSCRIPTION
    # the ledger carries the same label per fact — which facts rest on
    # stand-ins is a direct read (F-16).
    vocab = {ACQ_LIVE_CAPTURE, ACQ_COMMITTED_TRANSCRIPTION, ACQ_STAND_IN}
    for row in dossier["ledger"]:
        if row.get("acquisition"):
            assert row["acquisition"] in vocab
    stand_in_facts = {r["fact"] for r in dossier["ledger"] if r.get("acquisition") == ACQ_STAND_IN}
    assert "buyer='City of Oklahoma City'" in stand_in_facts


def test_evidence_posture_summary(okc_records: list[dict[str, Any]]) -> None:
    """The dossier JSON says plainly which facts rest on non-live bytes (F-16)."""
    records = list(okc_records) + [
        _standin_artifact(),
        _standin_claim("q1", "buyer", "City of Oklahoma City"),
    ]
    dossier = build_dossier(_packet(records))
    posture = dossier["evidence_posture"]
    assert posture["has_non_live"] is True
    assert posture["acquisition_counts"][ACQ_STAND_IN] >= 1
    assert "q1" in posture["questions_with_non_live"]
    assert "buyer='City of Oklahoma City'" in posture["stand_in_facts"]


def test_live_only_dossier_shows_no_disclosure(okc_records: list[dict[str, Any]]) -> None:
    """A dossier resting only on live captures carries no non-live posture."""
    dossier = build_dossier(_packet(okc_records))
    posture = dossier["evidence_posture"]
    assert posture["has_non_live"] is False
    assert posture["acquisition_counts"][ACQ_STAND_IN] == 0
    assert posture["acquisition_counts"][ACQ_COMMITTED_TRANSCRIPTION] == 0
    assert posture["questions_with_non_live"] == []
    assert posture["stand_in_facts"] == []
    html_doc = render_dossier_print_html(dossier)
    assert "non-live evidence" not in html_doc
    assert "live capture" in html_doc  # every assertion row is labelled


def test_acquisition_label_fail_closed() -> None:
    """No retrieval stamp and no transcription marker → never overclaim:
    the only honest label left is a stand-in."""
    claim = _fake_claim("q5", "contract_value", 1)
    del claim["evidence"]["retrieved_date"]
    assert acquisition_label(claim, None) == ACQ_STAND_IN


def test_review_label_derives_from_recorded_status() -> None:
    import re

    assert review_label("completed") == "independently reviewed"
    assert review_label("pending") == "independent review pending"
    assert review_label("not_run") == "independent review not yet run"
    assert "reviewed" not in review_label("not_run")

    records = [_artifact(), _fake_claim("q5", "contract_value", 100000)]
    for status, expected, word_allowed in (
        ("not_run", "independent review not yet run", False),
        ("pending", "independent review pending", False),
        ("completed", "independently reviewed", True),
    ):
        dossier = build_dossier(
            _packet(
                records,
                review={"status": status, "reviewer_role": "independent semantic reviewer"},
            )
        )
        assert dossier["review_label"] == expected
        blob = json.dumps(dossier) + render_dossier_print_html(dossier)
        found = re.search(r"\breviewed\b", blob, re.IGNORECASE)
        assert (found is not None) == word_allowed, (
            f"status {status}: 'reviewed' rendered={found is not None}"
        )


def test_print_disclosure_labels_and_footer(okc_records: list[dict[str, Any]]) -> None:
    """Print carries licence + permalink + per-page as-of on EVERY page
    (C4 NEW-22/NEW-23) and each assertion row names how its bytes were
    obtained (DR-C4-03)."""
    records = list(okc_records) + [
        _standin_artifact(),
        _transcription_artifact(),
        _standin_claim("q1", "buyer", "City of Oklahoma City"),
        _transcription_claim("q1", "vendor", "Flock Safety"),
    ]
    dossier = build_dossier(_packet(records))
    html_doc = render_dossier_print_html(dossier)
    # all three acquisition labels appear on their rows
    assert ">live capture<" in html_doc
    assert ">committed transcription<" in html_doc
    assert ">stand-in<" in html_doc
    # the page-one disclosure names the non-live posture
    assert "non-live evidence" in html_doc
    # every page footer carries licence, permalink and the as-of pair
    footers = html_doc.count("class='footer'")
    pages = html_doc.count("class='page'")
    assert footers == pages and footers >= 4
    for seg in html_doc.split("class='footer'")[1:]:
        seg = seg.split("</p>")[0]
        assert "CC-BY-4.0" in seg, "licence missing from a printed page"
        assert "surveillancegraph.org/research-dossier/okc-alpr/" in seg, (
            "permalink missing from a printed page"
        )
        assert "as-of world" in seg and "belief" in seg, "as-of missing from a printed page"


def test_dossier_json_carries_licence_permalink(okc_records: list[dict[str, Any]]) -> None:
    dossier = build_dossier(_packet(okc_records))
    assert dossier["licence"]["artifact"] == "CC-BY-4.0"
    assert isinstance(dossier["licence"]["record_spdx"], list)
    assert dossier["permalink"] == "https://surveillancegraph.org/research-dossier/okc-alpr/"


def test_rendered_dates_equal_their_records(okc_records: list[dict[str, Any]]) -> None:
    """Every rendered stamp is lifted from its record verbatim — no re-typing."""
    from db.claim_sink import content_digest

    packet = _packet(okc_records)
    claims = {content_digest(c): c for c in packet["records"] if c.get("record_kind") == "claim"}
    dossier = build_dossier(packet)
    for x in _all_assertions(dossier):
        claim = claims[x["claim_digest"]]
        ev = claim.get("evidence") or {}
        assert x["retrieved_date"] == ev.get("retrieved_date")
        assert x["observed_at"] == claim.get("observed_at")
    assert dossier["as_of"] == packet["as_of"]


def test_planted_future_date_fails_the_build_guard(okc_records: list[dict[str, Any]]) -> None:
    """DR-C4-15: a displayed date later than the build clock refuses compose —
    at the packet check and again at the rendered-dossier check."""
    import copy

    packet = _packet(copy.deepcopy(okc_records))
    packet["records"][0]["retrieved_at"] = (
        "2999-01-01T00:00:00+00:00"  # future-ok: synthetic: sentinel tripping the clock guard
    )
    assert any("build" in p for p in capture_chronology_violations(packet))
    with pytest.raises(ValueError):
        build_dossier(packet)


def test_planted_future_search_stamp_fails() -> None:
    packet = _packet([_artifact(), _fake_claim("q5", "contract_value", 1)], unknown_qs=("q10",))
    packet["search_log"][0]["searched_at"] = (
        "2999-12-31"  # future-ok: synthetic: sentinel tripping the clock guard
    )
    assert any("searched_at" in p and "build" in p for p in validate_packet(packet))
    with pytest.raises(ValueError):
        build_dossier(packet)


def test_planted_future_review_stamp_fails_after_compose(okc_records: list[dict[str, Any]]) -> None:
    """A stamp the packet check does not own (the free-form review record) is
    still refused when the composed dossier is checked."""
    packet = _packet(okc_records)
    packet["review"] = {
        "status": "completed",
        "completed_at": "2999-01-01",  # future-ok: synthetic: sentinel tripping the clock guard
    }
    with pytest.raises(ValueError, match="future displayed dates"):
        build_dossier(packet)


def test_review_completed_at_before_build_is_fine(okc_records: list[dict[str, Any]]) -> None:
    packet = _packet(okc_records)
    packet["review"] = {"status": "completed", "completed_at": "2026-10-04"}
    assert build_dossier(packet)["review_label"] == "independently reviewed"


def test_displayed_date_violations_walks_the_render(okc_records: list[dict[str, Any]]) -> None:
    import copy

    dossier = build_dossier(_packet(okc_records))
    assert displayed_date_violations(dossier) == []
    target = next(a for a in dossier["answers"] if a["assertions"])
    planted = copy.deepcopy(dossier)
    pa = next(a for a in planted["answers"] if a["assertions"])
    pa["assertions"][0]["retrieved_date"] = (
        "2999-01-01"  # future-ok: synthetic: sentinel tripping the clock guard
    )
    assert target["assertions"][0]["retrieved_date"]  # the record had a stamp
    assert any("retrieved_date" in p for p in displayed_date_violations(planted))
    # stated document dates are real-world claims — exempt from the clock guard
    stated = copy.deepcopy(dossier)
    sa = next(a for a in stated["answers"] if a["assertions"])
    sa["assertions"][0]["valid_from"] = "2999-01-01"
    sa["assertions"][0]["valid_to"] = "2999-12-31"
    assert displayed_date_violations(stated) == []
