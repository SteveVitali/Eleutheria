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
    ANSWER_STATES,
    COMPLETE_MAX,
    COMPLETE_TOTAL,
    PACKET_SCHEMA,
    QUESTION_IDS,
    REQUIRED_CROSSWALK_FIELDS,
    REQUIRED_MINIMUM,
    SUBSCRIPTION_HARDWARE_GUARD,
    TEMPLATE_EXECUTION_GUARD,
    build_dossier,
    build_portfolio,
    render_dossier_print_html,
    render_portfolio_json,
    validate_packet,
)

_FIX = Path(__file__).resolve().parent.parent / "connectors" / "fixtures" / "dossier"
_RETRIEVED = datetime(2026, 10, 1, tzinfo=UTC)
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
        "searched_at": "2026-10-01",
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
        "as_of": {"world": "2026-10-01", "belief": "2026-10-01"},
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
            "retrieved_date": "2026-10-01",
            "extraction_method": "html_text",
            "locator": {"locator": "clause 1"},
        },
        "observed_at": "2026-10-01",
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
        "retrieved_date": "2026-10-01",
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
    # The record's declared data-currency date is NOT its retrieval date.
    assert as_of_claim["retrieved_date"] == "2026-10-01"
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
        _fake_claim("q5", "contract_end_date", "2027-06-30", doc="synth-doc"),
        _fake_claim("q9", "posted_date", "2026-08-18", doc="synth-doc"),
    ]
    dossier = build_dossier(_packet(records, unknown_qs=()))
    dw = dossier["decision_windows"]
    assert dw["next_decision_date"] == "2027-06-30"
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
    assert comp["total"] < COMPLETE_TOTAL
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
    assert "retrieved 2026-10-01" in html_doc  # the capture date is shown
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
    assert "Reviewed research dossier" in print_html


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
