# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P32.19 (SIG-DOS-004): the Tulsa dossier packet.

Every acceptance distinction the ticket demands is pinned here — each test
fails if the behaviour it names is removed:

* **template ≠ executed** — the MOU template's blank Licensor/Licensee/Date
  fields are recorded ``present_but_empty``; no claim on the template asserts
  an executed contract, a buyer/seller, a signature date, or an actual
  sharing edge; its offered terms land only as D6 claims;
* **unsupported ≠ zero** — counts, spend, partners, actual use/sharing and
  oversight are ``unknown`` with named sources searched, a search date and a
  precise follow-up — never a fabricated affirmative and never a silent zero;
* **policy effective ≠ retrieval date** — the stated 2023-07-07/2023-10-04
  effective dates stay document dates; the replay's 2026-10-01
  retrieved/observed date stays the capture date; the 2023 files are never
  asserted to be the current versions;
* **scope honesty** — the only numeric retention period is scoped verbatim to
  manually entered LPR data; 113E's absent uniform period stays an
  ``absent`` field-state; two distinct ALPR products never collapse to one;
* **gates** — release valid, ``review.status = not_run`` keeps
  ``pilot_complete`` honest (D-R10-HUMAN-1 OPEN), the bounded live RETURN
  PASS is prepared-not-executed under ``D-P32.19-1``, the follow-up/request
  drafts stay ``drafted`` with ``records_requests_sent == 0``, and
  ``dossier_tulsa`` stays ``ingestion_permitted=false``.
"""

from __future__ import annotations

from pathlib import Path

from exports.research_dossier import (
    PACKET_SCHEMA,
    QUESTION_IDS,
    build_dossier,
    build_portfolio,
    render_dossier_print_html,
    validate_packet,
)

from ops import tulsa_dossier_packet as tp

# --------------------------------------------------------------------------- #
# Packet composition + fact-to-capture binding
# --------------------------------------------------------------------------- #


def test_packet_is_valid_sig_dossier_packet() -> None:
    packet = tp.build_packet()
    assert packet["schema"] == PACKET_SCHEMA
    assert validate_packet(packet) == []
    assert packet["dossier_id"] == tp.DOSSIER_ID
    assert packet["subject"]["entity_id"] == tp.DEPLOYMENT
    assert packet["as_of"] == {"world": "2026-10-01", "belief": "2026-10-01"}


def test_packet_records_bind_every_claim_to_captured_bytes() -> None:
    """Every claim's document_id resolves to an evidence_artifact row with a
    capture digest — the fact-to-capture chain (a dropped artifact row fails)."""
    packet = tp.build_packet()
    artifacts = {
        r["document_id"] for r in packet["records"] if r.get("record_kind") == "evidence_artifact"
    }
    claims = [r for r in packet["records"] if r.get("record_kind") == "claim"]
    assert artifacts and claims
    for c in claims:
        assert c.get("document_id") in artifacts, f"{c['predicate_id']} cites a missing document"
        assert c.get("evidence", {}).get("locator"), f"{c['predicate_id']} has no locator"
        assert c["evidence"].get("source_url")
        assert c["evidence"].get("retrieved_date")


def test_three_dossier_documents_replayed_verbatim() -> None:
    """The real connector emit is consumed verbatim — 15 claims + 3 artifacts
    over the three committed fixtures; only transient ids are dropped."""
    packet = tp.build_packet()
    conn = [r for r in packet["records"] if r.get("connector") == "dossier_documents"]
    claims = [r for r in conn if r.get("record_kind") == "claim"]
    arts = [r for r in conn if r.get("record_kind") == "evidence_artifact"]
    assert len(claims) == 15
    assert {a["document_id"] for a in arts} == {
        "tulsa-mou-template",
        "tulsa-policy-113c",
        "tulsa-policy-113e",
    }
    # Transient connector ids never leak into the packet.
    assert not any("claim_id" in r or "sys_period" in r for r in conn)


# --------------------------------------------------------------------------- #
# Template ≠ executed — the flagship acceptance distinction
# --------------------------------------------------------------------------- #


def test_mou_template_creates_no_executed_instrument_or_sharing_edge() -> None:
    packet = tp.build_packet()
    mou = [
        c
        for c in packet["records"]
        if c.get("document_id") == "tulsa-mou-template" and c.get("record_kind") == "claim"
    ]
    assert len(mou) == 5  # two term claims + three blank-field states
    # The template's offered terms emit only D6 claims under non-execution
    # predicates; every record is agency-statement class (claim_directness D6).
    assert all(c.get("claim_directness") == "D6" for c in mou)
    assert all(c.get("evidence_genre") == "template" for c in mou)
    executed = {
        "buyer",
        "seller",
        "signed_date",
        "contract_value",
        "amends_contract",
        "configured_access_edge",
        "sharing_partner_degree",
        "pooled_lookup_participation",
        "legal_authority",
    }
    assert not any(c["predicate_id"] in executed for c in mou)


def test_template_blank_fields_recorded_present_but_empty() -> None:
    packet = tp.build_packet()
    mou = [c for c in packet["records"] if c.get("document_id") == "tulsa-mou-template"]
    states = {c.get("value"): c.get("field_state") for c in mou if c.get("field_state")}
    assert states == {
        "buyer": "present_but_empty",
        "seller": "present_but_empty",
        "signed_date": "present_but_empty",
    }


def test_offered_terms_are_claims_not_participants() -> None:
    """The MOU's purpose/use clauses land as stated terms — never a partner
    entity, an access edge, or an executed sharing relationship."""
    packet = tp.build_packet()
    mou = [
        c
        for c in packet["records"]
        if c.get("document_id") == "tulsa-mou-template"
        and c.get("record_kind") == "claim"
        and not c.get("field_state")
    ]
    by_pred = {c["predicate_id"]: c["value"] for c in mou}
    assert by_pred["written_policy_value"] == "camera integration memorandum of understanding"
    assert "legitimate law enforcement" in by_pred["use_restriction"]
    # No record anywhere in the packet asserts the MOU's parties exist.
    packet_claims = [c for c in packet["records"] if c.get("record_kind") == "claim"]
    assert not any(c["predicate_id"] in {"buyer", "seller"} for c in packet_claims)


# --------------------------------------------------------------------------- #
# The dossier: release validity, honest marks, the twelve questions
# --------------------------------------------------------------------------- #


def _dossier() -> dict:
    return build_dossier(tp.build_packet())


def _answer(d: dict, q: str) -> dict:
    return next(a for a in d["answers"] if a["question"] == q)


def test_release_valid_and_review_never_fabricated() -> None:
    d = _dossier()
    assert d["release"]["valid"] is True
    assert d["release"]["violations"] == []
    assert d["review_status"] == "not_run"
    assert d["completeness"]["pilot_complete"] is False
    review_item = next(i for i in d["checklist"] if i["item"] == "independent_semantic_review")
    assert review_item["status"] == "fail"  # honest: no reviewer ran


def test_contract_chain_completion_gate_stays_unresolved() -> None:
    """The S2 designed outcome for Tulsa: the unknown procurement/share-chain
    keeps the mechanical gate honestly incomplete — never padded to pass."""
    d = _dossier()
    comp = d["completeness"]
    assert comp["mechanical_complete"] is False
    blocking = " | ".join(comp["blocking"])
    assert "q5" in blocking and "rubric_total" in blocking
    # The dossier reports honestly rather than manufacturing a 28/36.
    assert comp["total"] < 28


def test_all_twelve_questions_answered_explicitly() -> None:
    d = _dossier()
    assert [a["question"] for a in d["answers"]] == list(QUESTION_IDS)
    assert all(a["state"] for a in d["answers"])


# --------------------------------------------------------------------------- #
# Question-level semantics
# --------------------------------------------------------------------------- #


def test_q1_operator_evidenced_buyer_funder_unknown() -> None:
    d = _dossier()
    q1 = _answer(d, "q1")
    ops = [x for x in q1["assertions"] if x["predicate"] == "asset_operator"]
    assert len(ops) == 1 and ops[0]["value"] == "Tulsa Police Department"
    assert ops[0]["document_id"] == "tulsa-policy-113c"
    # The authored claim cites the policy page (locator + capture digest bound).
    assert ops[0]["locator"] == {"kind": "page", "page": 1}
    assert ops[0]["capture_digest"]
    # Buyer/funder are NOT asserted — the MOU's blank fields are recorded
    # field-states, and the question is declared partial.
    assert not any(x["predicate"] in {"buyer", "seller", "funder"} for x in q1["assertions"])
    assert q1["score"] == 2
    packet = tp.build_packet()
    partial = {p["question"] for p in (packet.get("declared") or {}).get("partial") or []}
    assert "q1" in partial
    assert any(f.get("action") for f in q1["follow_ups"])


def test_q2_two_distinct_products_never_collapsed() -> None:
    d = _dossier()
    q2 = _answer(d, "q2")
    techs = {x["value"] for x in q2["assertions"] if x["predicate"] == "technology"}
    assert techs == {"Flock Safety fixed ALPR", "Axon Fleet 3 in-car ALPR"}
    assert q2["score"] == 3


def test_q3_inventory_unknown_with_scoped_lead() -> None:
    d = _dossier()
    q3 = _answer(d, "q3")
    assert q3["state"] == "unknown"
    assert q3["search_basis"]["outcome"] == "searched_not_found"
    assert q3["search_basis"]["sources_searched"]
    assert q3["search_basis"]["searched_at"]
    assert any(f.get("action") and f.get("closing_condition") for f in q3["follow_ups"])


def test_q4_template_purpose_is_not_external_access() -> None:
    d = _dossier()
    q4 = _answer(d, "q4")
    assert q4["state"] == "unknown"
    assert q4["search_basis"]["outcome"] == "searched_not_found"
    # No configured-access/partner/participation claim exists anywhere.
    packet = tp.build_packet()
    assert not any(
        c["predicate_id"]
        in {"configured_access_edge", "pooled_lookup_participation", "sharing_partner_degree"}
        for c in packet["records"]
        if c.get("record_kind") == "claim"
    )


def test_q5_procurement_unknown_searched_not_found() -> None:
    """'Searched, not found' — never 'no contract exists', never zero spend."""
    d = _dossier()
    q5 = _answer(d, "q5")
    assert q5["state"] == "unknown"
    assert q5["search_basis"]["outcome"] == "searched_not_found"
    assert any(
        "searched" in str(s).lower() or "search" in str(s).lower()
        for s in q5["search_basis"]["sources_searched"]
    )
    assert any(f.get("action") and f.get("closing_condition") for f in q5["follow_ups"])
    # No spend/contract claim exists in the packet at all.
    packet = tp.build_packet()
    assert not any(
        c["predicate_id"] in {"contract_value", "funding_amount", "signed_date"}
        for c in packet["records"]
        if c.get("record_kind") == "claim"
    )


def test_q6_authority_policy_evidenced_chain_partial() -> None:
    d = _dossier()
    q6 = _answer(d, "q6")
    preds = {x["predicate"]: x["value"] for x in q6["assertions"]}
    assert preds["enacting_body"] == "Tulsa Police Department"
    assert preds["written_policy_value"] == "camera integration memorandum of understanding"
    assert q6["score"] == 2  # declared partial: no authorizing instrument beyond policy
    packet = tp.build_packet()
    partial = {p["question"] for p in (packet.get("declared") or {}).get("partial") or []}
    assert "q6" in partial


def test_q7_retention_scoped_to_manually_entered_only() -> None:
    """The 12-month clause applies verbatim to manually entered LPR data — it
    is NEVER generalized to a uniform scan-retention rule, and 113E's uniform
    period stays a reviewed `absent` field-state."""
    d = _dossier()
    q7 = _answer(d, "q7")
    ret = next(x for x in q7["assertions"] if x["predicate"] == "retention_period")
    assert ret["value"] == "12 months"
    assert "manually entered" in str(ret["raw_value"]).lower()
    # Both use-restriction policies render verbatim.
    uses = {x["value"] for x in q7["assertions"] if x["predicate"] == "use_restriction"}
    assert "authorized personnel only" in uses
    assert any("legitimate law enforcement purposes and official business" in u for u in uses)
    assert "legitimate law enforcement purposes only" in uses
    # The field-state inventory carries the 113E absence, reviewably.
    q12 = _answer(d, "q12")
    absent = [
        f
        for f in q12["field_inventory"]
        if f["field"] == "retention_period" and f["document_id"] == "tulsa-policy-113e"
    ]
    assert absent and absent[0]["state"] == "absent"


def test_q8_approval_rule_no_observed_share() -> None:
    d = _dossier()
    q8 = _answer(d, "q8")
    share = [x for x in q8["assertions"] if x["predicate"] == "sharing_restriction"]
    assert share and "Chief of Police or designee approval" in share[0]["value"]
    # The actual sharing actors/mode are unknown — declared partial + follow-up.
    assert q8["score"] == 2
    assert any(f.get("action") for f in q8["follow_ups"])


def test_q9_effective_dates_are_document_dates_co_visible() -> None:
    """Both stated effective dates render, each bound to its own document and
    never promoted to a retrieval date; the same-scope flag keeps both visible
    rather than silently collapsing the two instruments."""
    d = _dossier()
    q9 = _answer(d, "q9")
    pairs = {(x["value"], x["document_id"]) for x in q9["assertions"]}
    assert ("2023-07-07", "tulsa-policy-113c") in pairs
    assert ("2023-10-04", "tulsa-policy-113e") in pairs
    for x in q9["assertions"]:
        assert x["valid_from"] == x["value"]  # stated date rides the valid window
        assert x["observed_at"] == "2026-10-01"  # the replay/capture date
        assert x["retrieved_date"] == "2026-10-01"
        assert x["valid_from"] != x["retrieved_date"]


def test_q10_oversight_unknown_with_search_basis() -> None:
    d = _dossier()
    q10 = _answer(d, "q10")
    assert q10["state"] == "unknown"
    assert q10["search_basis"]["outcome"] == "searched_not_found"
    assert any(f.get("action") for f in q10["follow_ups"])


def test_q11_support_profile_classifies_evidence_genres() -> None:
    d = _dossier()
    q11 = _answer(d, "q11")
    assert q11["state"] == "derived"
    prof = q11["derivation"]["value"]
    assert prof["instrument_backed_claims"] == 10  # agency-policy + operator claims
    assert prof["non_probative_claims"] == 5  # the template's D6 records
    assert prof["claims_by_genre"] == {"template": 2, "agency_policy": 10}
    # Every template claim is D6 — offered terms are agency-statement class.
    packet = tp.build_packet()
    mou = [
        c
        for c in packet["records"]
        if c.get("document_id") == "tulsa-mou-template" and c.get("record_kind") == "claim"
    ]
    assert all(c.get("claim_directness") == "D6" for c in mou)


def test_q12_unknowns_and_corrections_route() -> None:
    d = _dossier()
    q12 = _answer(d, "q12")
    assert q12["state"] == "supported"
    fields = {(f["field"], f["state"]) for f in q12["field_inventory"]}
    assert ("buyer", "present_but_empty") in fields
    assert ("seller", "present_but_empty") in fields
    assert ("signed_date", "present_but_empty") in fields
    assert ("retention_period", "absent") in fields
    assert "corrections" in q12["correction_route"] or "/corrections/" in str(
        q12.get("correction_route")
    )
    # Unknown questions all carry the documented basis + precise follow-up.
    for q in ("q3", "q4", "q5", "q10"):
        a = _answer(d, q)
        assert a["state"] == "unknown"
        assert a["search_basis"]["sources_searched"]
        assert a["search_basis"]["outcome"] == "searched_not_found"
        assert all(f.get("action") and f.get("closing_condition") for f in a["follow_ups"])


# --------------------------------------------------------------------------- #
# Follow-up drafts — drafted, never sent
# --------------------------------------------------------------------------- #


def test_follow_up_drafts_are_drafted_never_sent() -> None:
    fud = tp.follow_up_drafts()
    assert fud["schema"] == "sig.dossier-follow-up-drafts/1"
    assert fud["posture"] == "drafted_not_sent"
    assert fud["records_requests_sent"] == 0
    # The executed-contract gap routes to the Oklahoma statute draft for TPD.
    drafts = fud["records_request_drafts"]
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft["status"] == "drafted"
    assert draft["records_law_key"] == "OK"
    assert draft["target_agency"] == "Tulsa Police Department"
    assert "24A" in draft["statutory_citation"]
    assert draft["record_type"] == "alpr_contract"
    # No filer identity or send path is fabricated: the draft names the
    # placeholder contact and stays drafted.
    assert "drafted" == draft["status"]
    # The remaining gaps stay honest research tasks on the queue.
    kinds = {t["task_type"] for t in fud["research_queue"]}
    assert "missing_contract" in kinds
    assert "coverage_hole" in kinds
    assert all(t["status"] == "generated" for t in fud["research_queue"])
    # The packet's per-question follow-ups carry the closing conditions.
    packet = tp.build_packet()
    for f in packet["follow_ups"]:
        assert f["action"] and f["closing_condition"]


# --------------------------------------------------------------------------- #
# Ledger, print, RETURN PASS, gates
# --------------------------------------------------------------------------- #


def test_ledger_binds_every_rendered_fact() -> None:
    d = _dossier()
    rendered = [r for r in d["ledger"] if r["state"] == "rendered"]
    assert rendered
    for r in rendered:
        if r["predicate"] == "evidence_profile":
            continue
        assert r["claim_digest"]
        assert r["capture_digest"]
        assert r["locator"]


def test_print_html_renders_distinctions() -> None:
    d = _dossier()
    html = render_dossier_print_html(d)
    for needle in (
        "present_but_empty",
        "manually entered",
        "2023-07-07",
        "2023-10-04",
        "searched_not_found",
        "not_run",
    ):
        assert needle in html


def test_live_return_pass_is_bounded_and_unexecuted() -> None:
    rp = tp.live_return_pass()
    assert rp["schema"] == tp.LIVE_PASS_SCHEMA
    assert rp["status"] == "prepared_not_executed"
    assert rp["deferral"] == "D-P32.19-1"
    urls = {t["url"] for t in rp["targets"]}
    assert len(urls) == len(rp["targets"]) == 6
    # The three registered dossier targets + the reviewed leads.
    assert any("policy-113c" in u for u in urls)
    assert any("policy-113e" in u for u in urls)
    assert any("camera-integration-mou-template" in u for u in urls)
    assert any("flock-safety" in u for u in urls)
    assert any("policies-and-procedures" in u for u in urls)
    assert any("corridor-safety-guide" in u for u in urls)
    assert any("HG-03" in p for p in rp["preconditions"])
    assert any("Part VIII" in p for p in rp["preconditions"])
    assert any("rights" in g for g in rp["non_goals"])
    assert any("request" in g or "sent" in g for g in rp["non_goals"])
    assert rp["bounded_questions"]


def test_evidence_pack_names_captures_and_posture() -> None:
    md = tp.evidence_pack_markdown()
    for needle in (
        "present_but_empty",
        "TEMPLATE",
        "not_run",
        "D-P32.19-1",
        "D-R10-SOURCES-1",
        "tulsa-mou-template",
        "tulsa-policy-113c",
        "tulsa-policy-113e",
        "manually entered",
        "records_requests_sent",
    ):
        assert needle in md


def test_dossier_tulsa_stays_ingestion_gated() -> None:
    """The replay's in-memory flip never touches the registry row — the source
    stays gated (D-R10-SOURCES-1 OPEN), rights flips are HG-03 only."""
    import pytest
    from connectors.loader import IngestionNotPermitted, assert_loadable
    from connectors.registry import get

    assert get("dossier_tulsa").ingestion_permitted is False
    # The live gate still refuses the source.
    with pytest.raises(IngestionNotPermitted):
        assert_loadable(get("dossier_tulsa"))


def test_no_part_viii_or_fabricated_participant_data() -> None:
    """No plate/trip/person/officer material and no invented partner, roster,
    count, or spend appears anywhere in the packet."""
    packet = tp.build_packet()
    blob = str(packet).lower()
    for banned in ("plate_number", "license_plate", "trip", "person_name", "officer"):
        assert banned not in blob
    claims = [c for c in packet["records"] if c.get("record_kind") == "claim"]
    banned_preds = {
        "sharing_partner_degree",
        "pooled_lookup_participation",
        "configured_access_edge",
        "claimed_device_count",
        "contract_value",
        "buyer",
        "seller",
        "funder",
    }
    assert not any(c["predicate_id"] in banned_preds for c in claims)


# --------------------------------------------------------------------------- #
# Determinism + portfolio
# --------------------------------------------------------------------------- #


def test_artifact_write_is_deterministic(tmp_path: Path) -> None:
    a = tp.write(tmp_path / "a")
    b = tp.write(tmp_path / "b")
    assert set(a) == set(b) == set(tp.ARTIFACT_NAMES)
    for key in a:
        assert a[key].read_bytes() == b[key].read_bytes(), f"{key} not deterministic"


def test_portfolio_wraps_the_dossier() -> None:
    portfolio = build_portfolio([tp.build_packet()])
    assert portfolio["summary"]["dossier_count"] == 1
    assert portfolio["summary"]["pilot_complete"] == 0
    assert portfolio["summary"]["release_invalid"] == 0
