# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P32.18 (SIG-DOS-003): the Oklahoma City dossier packet + correction packet.

Every acceptance distinction the ticket demands is pinned here — each test
fails if the behaviour it names is removed:

* the scope partition (299 metro / 90 city-owned / ~100 private / 90 active /
  90 contracted) stays co-visible and is NEVER a same-scope contradiction;
* the derived "~190" is labelled derived with named inputs, never a claim;
* journalism (D6) is never an instrument; council materials are never
  executed-contract evidence; the amendment is not asserted executed;
* temporal semantics — the 7-day retention's STATED effective date survives
  (announced, never promoted to operational);
* UVED applicability stays scoped (§7-606.1 governs the insurance-enforcement
  program; no claim generalizes it to the Flock deployment);
* release validation, the honest ``not_run`` review mark, the bounded live
  RETURN PASS deferral, and artifact determinism all hold.
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

from ops import dossier_packet as dp
from ops import seed_correction as sc

# --------------------------------------------------------------------------- #
# Packet composition
# --------------------------------------------------------------------------- #


def test_packet_is_valid_sig_dossier_packet() -> None:
    packet = dp.build_packet()
    assert packet["schema"] == PACKET_SCHEMA
    assert validate_packet(packet) == []
    assert packet["dossier_id"] == dp.DOSSIER_ID
    assert packet["subject"]["entity_id"] == dp.DEPLOYMENT


def test_packet_records_bind_every_claim_to_captured_bytes() -> None:
    """Every claim in the packet carries a document_id whose evidence_artifact
    row exists and holds a capture digest — the fact-to-capture chain the
    reviewer traces (a dropped artifact row must fail this)."""
    packet = dp.build_packet()
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
    """The real connector emit is consumed verbatim — no authored rewriting."""
    packet = dp.build_packet()
    claims = [
        r
        for r in packet["records"]
        if r.get("connector") == "dossier_documents" and r.get("record_kind") == "claim"
    ]
    assert len(claims) == 16
    assert sum(1 for r in packet["records"] if r.get("record_kind") == "evidence_artifact") >= 4
    usage = [c for c in claims if c.get("document_id") == "okc-flock-usage-2026"]
    by_pred = {c["predicate_id"]: c for c in usage}
    assert by_pred["claimed_device_count"]["value"] == 90
    assert by_pred["sharing_partner_degree"]["value"] == 109
    assert by_pred["as_of"]["value"] == "2026-08-18"
    # Signature uncertainty stays a recorded field state, never inferred.
    fs = [c for c in claims if c.get("field_state") == "present_but_empty"]
    assert {c["source_field"] for c in fs} == {"signed_date", "execution_state"}


# --------------------------------------------------------------------------- #
# The dossier: release validity, completeness, honest review mark
# --------------------------------------------------------------------------- #


def _dossier() -> dict:
    return build_dossier(dp.build_packet())


def test_release_valid_mechanical_not_pilot() -> None:
    d = _dossier()
    assert d["release"]["valid"] is True
    assert d["release"]["violations"] == []
    assert d["completeness"]["mechanical_complete"] is True
    # pilot_complete requires a COMPLETED independent review — never fabricated.
    assert d["completeness"]["pilot_complete"] is False
    assert d["review_status"] == "not_run"
    assert any("independent_review" in b for b in d["completeness"]["blocking"])
    review_item = next(i for i in d["checklist"] if i["item"] == "independent_semantic_review")
    assert review_item["status"] == "fail"  # honest: no reviewer ran


def test_all_twelve_questions_answered_explicitly() -> None:
    d = _dossier()
    assert [a["question"] for a in d["answers"]] == list(QUESTION_IDS)
    assert all(a["state"] for a in d["answers"])
    # No question is a silent blank: the only sub-3 scores are declared partials.
    partial = {a["question"] for a in d["answers"] if a["score"] < 3}
    assert partial == {"q6", "q8"}


# --------------------------------------------------------------------------- #
# Scope partition (the flagship acceptance distinction)
# --------------------------------------------------------------------------- #


def test_299_metro_vs_city_counts_is_not_a_contradiction() -> None:
    d = _dossier()
    q3 = next(a for a in d["answers"] if a["question"] == "q3")
    values = {
        (x["predicate"], x["value"], (x["scope"] or {}).get("count_scope"))
        for x in q3["assertions"]
    }
    assert ("claimed_device_count", 299, "metro") in values
    assert ("claimed_device_count", 90, "city_owned") in values
    assert ("claimed_device_count", 100, "city_limits") in values
    # Different scopes → nothing flagged conflicting, no disputed state.
    assert q3["state"] != "disputed"
    assert not any(x.get("conflicting") for x in q3["assertions"])


def test_90_owned_is_not_90_active() -> None:
    d = _dossier()
    q3 = next(a for a in d["answers"] if a["question"] == "q3")
    owned = [
        x for x in q3["assertions"] if x["predicate"] == "claimed_device_count" and x["value"] == 90
    ]
    active = [x for x in q3["assertions"] if x["predicate"] == "active_device_count"]
    contracted = [x for x in q3["assertions"] if x["predicate"] == "contracted_device_count"]
    assert owned and active and contracted
    # Three different questions, three different records — never collapsed.
    assert owned[0]["scope"].get("count_scope") == "city_owned"
    assert active[0]["scope"].get("count_scope_detail") == "agency_operated"
    assert active[0]["value"] == 90 and contracted[0]["value"] == 90


def test_derived_190_is_labelled_not_a_claim() -> None:
    d = _dossier()
    q3 = next(a for a in d["answers"] if a["question"] == "q3")
    assert q3["state"] == "derived"
    view = q3["derivation"]["value"]
    assert view["label"] == "~190" and view["derived"] is True and view["approximate"] is True
    assert view["inputs"] == [90, 100]
    # The two input claims resolve inside the packet — a derived answer with a
    # dangling input would be a release violation.
    assert len(q3["derivation"]["inputs"]) == 2
    # No packet claim asserts 190 — it exists only as the derivation's label.
    packet = dp.build_packet()
    assert not any(
        c.get("value") == 190 for c in packet["records"] if c.get("record_kind") == "claim"
    )


# --------------------------------------------------------------------------- #
# Evidence-class discipline
# --------------------------------------------------------------------------- #


def test_journalism_is_d6_never_instrument() -> None:
    d = _dossier()
    q11 = next(a for a in d["answers"] if a["question"] == "q11")
    prof = q11["derivation"]["value"]
    assert prof["non_probative_claims"] >= 8  # the authored journalism/council claims
    packet = dp.build_packet()
    journ = [
        c
        for c in packet["records"]
        if c.get("evidence_genre") == "news_article" and c.get("record_kind") == "claim"
    ]
    assert journ and all(c.get("claim_directness") == "D6" for c in journ)


def test_council_memo_is_not_executed_contract() -> None:
    packet = dp.build_packet()
    memo = [
        c
        for c in packet["records"]
        if c.get("document_id") == "okc-council-memo-2026-08" and c.get("record_kind") == "claim"
    ]
    assert memo
    assert all(c["evidence_genre"] == "agenda_document" for c in memo)
    assert all(c["document_genre"] == "procurement_record" for c in memo)
    assert all(c["evidence_genre"] != "executed_contract" for c in memo)


def test_amendment_execution_unverified() -> None:
    packet = dp.build_packet()
    amend = [
        c
        for c in packet["records"]
        if c.get("document_id") == "okc-flock-amendment-2026" and c.get("record_kind") == "claim"
    ]
    # The signature block is partially evidenced: field-states recorded, no
    # signed_date/effective claim asserted.
    assert not any(c["predicate_id"] in {"signed_date", "effective_from"} for c in amend)
    states = {c["source_field"]: c.get("field_state") for c in amend if c.get("field_state")}
    assert states == {"signed_date": "present_but_empty", "execution_state": "present_but_empty"}
    # The vendor disclosure restriction stays actor-scoped — a restriction on
    # Company disclosure, never generalized to every City-authorized share.
    restrict = next(c for c in amend if c["predicate_id"] == "sharing_restriction")
    assert "customer data" in restrict["value"]
    proc_except = next(c for c in amend if c["predicate_id"] == "use_restriction")
    assert "compulsory legal process" in proc_except["value"]


# --------------------------------------------------------------------------- #
# Temporal + authority semantics
# --------------------------------------------------------------------------- #


def test_retention_announced_effective_date_preserved() -> None:
    d = _dossier()
    q7 = next(a for a in d["answers"] if a["question"] == "q7")
    ret = next(x for x in q7["assertions"] if x["predicate"] == "retention_period")
    assert ret["value"] == "7 days"
    # Stated effective 2026-10-01 — NOT the capture date (2026-10-01 replay) and
    # never an observed operational date.
    assert ret["valid_from"] == "2026-10-01"
    assert ret["observed_at"] == "2026-10-01"
    exc = next(x for x in q7["assertions"] if "investigation" in str(x["value"]))
    assert exc["predicate"] == "use_restriction"
    # The announced 30→7 transition is a separate stated fact (journalism).
    assert any(
        x["predicate"] == "written_policy_value" and "30" in str(x["value"])
        for x in q7["assertions"]
    )


def test_uved_statute_stays_scoped_to_its_program() -> None:
    d = _dossier()
    q6 = next(a for a in d["answers"] if a["question"] == "q6")
    stat = [x for x in q6["assertions"] if x["document_id"] == "okc-statute-47-7-606-1"]
    assert stat
    cite = next(x for x in stat if x["predicate"] == "statutory_citation")
    assert "7-606.1" in cite["value"]
    restr = next(x for x in stat if x["predicate"] == "use_restriction")
    assert restr["value"] == "limited to insurance enforcement"
    # No claim anywhere asserts the statute APPLIES to the Flock program —
    # applicability is declared partial in the packet, not inferred.
    assert q6["score"] == 2
    packet = dp.build_packet()
    partial = {p["question"]: p for p in (packet.get("declared") or {}).get("partial") or []}
    assert "q6" in partial
    assert "unresolved" in partial["q6"]["rationale"]


def test_legal_conclusion_not_inferred_from_city_page() -> None:
    """The official usage page supports page facts only — no authorization or
    legality claim cites it."""
    packet = dp.build_packet()
    usage = [
        c
        for c in packet["records"]
        if c.get("document_id") == "okc-flock-usage-2026" and c.get("record_kind") == "claim"
    ]
    legal = {"authorization_state", "legal_authority", "statutory_citation"}
    assert not any(c["predicate_id"] in legal for c in usage)


def test_partner_degree_is_not_a_device_count() -> None:
    d = _dossier()
    q8 = next(a for a in d["answers"] if a["question"] == "q8")
    deg = next(x for x in q8["assertions"] if x["predicate"] == "sharing_partner_degree")
    assert deg["value"] == 109
    assert deg["scope"]["count_scope"] == "partner_agencies"
    # The roster itself is unknown — declared partial, follow-up names it.
    packet = dp.build_packet()
    partial = {p["question"]: p for p in (packet.get("declared") or {}).get("partial") or []}
    assert "q8" in partial
    assert any(f.get("action") for f in q8["follow_ups"])


def test_decision_window_and_temporal_kinds() -> None:
    d = _dossier()
    assert d["decision_windows"]["next_decision_date"] == "2027-06-30"
    q9 = next(a for a in d["answers"] if a["question"] == "q9")
    preds = {x["predicate"] for x in q9["assertions"]}
    assert {"as_of", "posted_date", "lifecycle_transition", "contract_end_date"} <= preds


# --------------------------------------------------------------------------- #
# The ledger + print artifact
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


def test_print_html_renders_scope_and_citations() -> None:
    d = _dossier()
    html = render_dossier_print_html(d)
    assert "count_scope" in html
    assert "retrieved" in html
    assert "independent_review" in html or "not_run" in html


# --------------------------------------------------------------------------- #
# The seed-correction packet (committed shape — no DB needed)
# --------------------------------------------------------------------------- #


def test_correction_packet_is_additive_not_destructive() -> None:
    pkt = sc.correction_packet()
    assert pkt["schema"] == sc.PACKET_SCHEMA
    assert pkt["status"] == "prepared" and pkt["review"]["status"] == "not_run"
    # The legacy flagship records are TARGETS, never rewrites: the packet
    # carries the exact pre-P32.3 rows plus appended replacements.
    targets = {c["correction_id"]: c["target_record"] for c in pkt["corrections"]}
    assert targets["bacy-190-derived-not-sourced"]["value"] == 190
    assert targets["deflock-299-metro-scope"]["evidence_genre"] == "news_article"
    # Every correction names its reason (the §16.6 CHECK requires one).
    assert all(c["correction_reason"] for c in pkt["corrections"])


def test_correction_replacements_carry_scope_and_origin() -> None:
    pkt = sc.correction_packet()
    repl = {c["correction_id"]: c["replacement_records"][0] for c in pkt["corrections"]}

    def quals(r):
        return {q["qualifier_id"]: q["value"] for q in r["qualifiers"]}

    assert quals(repl["deflock-299-metro-scope"])["count_scope"] == "metro"
    assert quals(repl["bacy-190-derived-not-sourced"])["count_scope"] == "city_limits"
    assert quals(repl["bacy-190-derived-not-sourced"])["count_scope_detail"] == "privately_owned"
    assert quals(repl["bacy-90-active-scope"])["count_scope_detail"] == "agency_operated"
    assert quals(repl["contract-90-scope"])["count_scope"] == "city_limits"
    # Fixture origin is labelled on every replacement.
    assert all(quals(r)["evidence_origin"] == "seed_fixture" for r in repl.values())
    # The bacy replacement asserts the SOURCED ~100 — never the derived 190.
    assert repl["bacy-190-derived-not-sourced"]["value"] == 100
    # ODbL licence compartment preserved verbatim on the OSM row.
    assert repl["osm-31-metro-scope"]["spdx"] == "ODbL-1.0"


def test_derived_label_is_a_labelled_roll_up() -> None:
    pkt = sc.correction_packet()
    labels = pkt["derived_labels"]
    assert len(labels) == 1
    view = labels[0]["view"]
    assert view["label"] == "~190"
    assert view["layer"] == "L4" and view["derived"] and view["approximate"]
    assert view["inputs"] == [90, 100]
    assert view["assumptions"]
    # The packet's digest-stable: two builds produce identical bytes.
    assert sc.render_packet_json(pkt) == sc.render_packet_json(sc.correction_packet())


# --------------------------------------------------------------------------- #
# Live RETURN PASS + evidence pack
# --------------------------------------------------------------------------- #


def test_live_return_pass_is_bounded_and_unexecuted() -> None:
    rp = dp.live_return_pass()
    assert rp["schema"] == dp.LIVE_PASS_SCHEMA
    assert rp["status"] == "prepared_not_executed"
    assert rp["deferral"] == "D-P32.18-1"
    urls = {t["url"] for t in rp["targets"]}
    assert len(urls) == len(rp["targets"]) == 6
    assert any("oscn.net" in u for u in urls)
    assert any("purchasing" in u for u in urls)
    assert any("HG-03" in p for p in rp["preconditions"])
    assert any("rights" in g for g in rp["non_goals"])


def test_evidence_pack_names_captures_and_gaps() -> None:
    md = dp.evidence_pack_markdown()
    assert "present_but_empty" in md  # signature uncertainty surfaced
    assert "not_run" in md
    assert "D-P32.18-1" in md
    assert "D-R10-SOURCES-1" in md
    for doc in (
        "okc-flock-usage-2026",
        "okc-council-memo-2026-08",
        "okc-flock-amendment-2026",
        "okc-statute-47-7-606-1",
        "okc-ops-manual-5-118",
        "okc-contract-c241032",
    ):
        assert doc in md


# --------------------------------------------------------------------------- #
# Determinism — the committed artifacts regenerate byte-identically
# --------------------------------------------------------------------------- #


def test_artifact_write_is_deterministic(tmp_path: Path) -> None:
    a = dp.write(tmp_path / "a")
    b = dp.write(tmp_path / "b")
    for key in a:
        assert a[key].read_bytes() == b[key].read_bytes(), f"{key} not deterministic"


def test_portfolio_wraps_the_dossier() -> None:
    portfolio = build_portfolio([dp.build_packet()])
    assert portfolio["summary"]["dossier_count"] == 1
    assert portfolio["summary"]["mechanical_complete"] == 1
    assert portfolio["summary"]["pilot_complete"] == 0
    assert portfolio["summary"]["release_invalid"] == 0


def test_derived_context_claims_stay_visible() -> None:
    """The shared-machinery fix: a derived q3 keeps the question's other scoped
    evidence rendered as context — 299-metro must not vanish under the ~190."""
    d = _dossier()
    q3 = next(a for a in d["answers"] if a["question"] == "q3")
    context = [x for x in q3["assertions"] if x.get("context")]
    assert any(x["value"] == 299 for x in context)
    ledger = [r for r in d["ledger"] if r["question"] == "q3"]
    assert len(ledger) == len(q3["assertions"])  # no double-logging, no hiding
