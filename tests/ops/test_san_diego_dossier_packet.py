# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P32.20 (SIG-DOS-005): the San Diego dossier packet.

Every acceptance distinction the ticket demands is pinned here — each test
fails if the behaviour it names is removed:

* **subscription ≠ hardware** — the Vigilant LEARN ASR section is a
  hosted-database subscription (``access_mode="subscription"``): it
  evidences inbound access/pooled lookup only and mints no local SDPD
  camera, device count, deployment existence, fixed location or
  implementation claim anywhere in the packet;
* **prime contractor ≠ component vendor** — ``seller`` Ubicquia, Inc. (the
  named contracting party) and ``vendor`` Flock Safety, Inc. (the
  incorporated component supplier) stay distinct roles on distinct
  subjects, co-visible never ``disputed``; a vendor mention is never an
  operational relationship;
* **recommendation ≠ adoption** — the PAB recommendation exists by its
  index listing (existence + verbatim title + original span locator) and
  stays ``proposed``; the ASR self-report stays genre-distinct from
  oversight;
* **signature ≠ execution** — ``signed_date`` is the vendor-side date
  verbatim and ``City Date:`` is ``present_but_empty``; the genre stays
  ``contract`` and nothing calls the instrument executed;
* **Part VIII preflight is metadata-only** — the network-audit
  spreadsheet links (SRC-027) record a link-metadata preflight; no
  workbook/XLSX/ZIP/sharedStrings or row-level plate/person/query content
  is transported; the workbook acquisition path is ``rejected``
  permanently (E4-B3 = a);
* **temporal honesty** — the 2023-12-15 vendor-signed date, the 2025
  report period and the 2026-02-15 posted date stay document dates,
  never promoted to capture dates — the replay's retrieved/observed
  stamps carry each fixture's real authoring commit (git-derived, P34.22b);
* **gates** — release valid, ``review.status = not_run`` keeps
  ``pilot_complete`` honest (D-R10-HUMAN-1 OPEN), the bounded live RETURN
  PASS is prepared-not-executed under ``D-P32.20-1``, the CPRA follow-up
  drafts stay ``drafted`` with ``records_requests_sent == 0``, and
  ``dossier_san_diego`` stays ``ingestion_permitted=false``.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from exports.research_dossier import (
    PACKET_SCHEMA,
    QUESTION_IDS,
    build_dossier,
    build_portfolio,
    render_dossier_print_html,
    validate_packet,
)

from ops import san_diego_dossier_packet as sd

#: Predicates a subscription/hosted-access artifact must never mint — the
#: connector's emit-time guard list, re-checked here at the packet level.
_HARDWARE_PREDS = {
    "claimed_device_count",
    "active_device_count",
    "installed_device_count",
    "contracted_device_count",
    "invoiced_device_count",
    "deployment_exists",
    "fixed_asset_location",
    "asset_exists_at_location",
    "implements_technology",
}


def _claims(packet: dict, doc: str | None = None) -> list[dict]:
    return [
        r
        for r in packet["records"]
        if r.get("record_kind") == "claim" and (doc is None or r.get("document_id") == doc)
    ]


# --------------------------------------------------------------------------- #
# Packet composition + fact-to-capture binding
# --------------------------------------------------------------------------- #


def test_packet_is_valid_sig_dossier_packet() -> None:
    packet = sd.build_packet()
    assert packet["schema"] == PACKET_SCHEMA
    assert validate_packet(packet) == []
    assert packet["dossier_id"] == sd.DOSSIER_ID
    assert packet["subject"]["entity_id"] == sd.DEPLOYMENT
    # P34.22b: the as-of pair is the evidence anchor — the newest fixture
    # authoring commit — never a typed replay date.
    anchor_day = datetime.fromisoformat(packet["capture"]["anchor"]).date().isoformat()
    assert packet["as_of"] == {"world": anchor_day, "belief": anchor_day}


def test_packet_records_bind_every_claim_to_captured_bytes() -> None:
    """Every claim's document_id resolves to an evidence_artifact row with a
    capture digest — the fact-to-capture chain (a dropped artifact row fails)."""
    packet = sd.build_packet()
    artifacts = {
        r["document_id"] for r in packet["records"] if r.get("record_kind") == "evidence_artifact"
    }
    claims = _claims(packet)
    assert artifacts and claims
    for c in claims:
        assert c.get("document_id") in artifacts, f"{c['predicate_id']} cites a missing document"
        assert c.get("evidence", {}).get("locator"), f"{c['predicate_id']} has no locator"
        assert c["evidence"].get("source_url")
        # P34.22b: a replayed record carries the fixture commit date as its
        # retrieval stamp; a hand-authored stand-in carries none.
        if c.get("capture_kind") == "stand-in":
            assert not c["evidence"].get("retrieved_date"), (
                f"{c['predicate_id']}: a stand-in was never retrieved"
            )
            assert c["evidence"].get("fixture_committed_at")
        else:
            assert c["evidence"].get("retrieved_date"), (
                f"{c['predicate_id']}: a fixture replay carries the commit date"
            )


def test_four_dossier_documents_replayed_verbatim() -> None:
    """The real connector emit is consumed verbatim — 30 claims + 4 artifacts
    (+2 index pages) over the four committed fixtures; only transient ids
    are dropped."""
    packet = sd.build_packet()
    conn = [r for r in packet["records"] if r.get("connector") == "dossier_documents"]
    claims = [r for r in conn if r.get("record_kind") == "claim"]
    arts = [r for r in conn if r.get("record_kind") == "evidence_artifact"]
    assert len(claims) == 30
    assert {a["document_id"] for a in arts} == {
        "sd-asr-2025-vigilant",
        "sd-ubicquia-agreement-2023",
        "sd-technology-index",
        "sd-pab-index",
    }
    assert not any("claim_id" in r or "sys_period" in r for r in conn)
    # The packet adds exactly the authored distinction claims.
    authored = [
        r for r in packet["records"] if r.get("connector") == "ops.san_diego_dossier_packet"
    ]
    assert len(authored) == len(sd.authored_claims()) == 7


# --------------------------------------------------------------------------- #
# Subscription ≠ hardware — the flagship acceptance distinction
# --------------------------------------------------------------------------- #


def test_subscription_creates_no_local_hardware_assertion() -> None:
    """No claim citing the subscription document, and no claim on the
    subscription subject, carries a hardware/device predicate — subscription
    access never mints local SDPD hardware."""
    packet = sd.build_packet()
    asr = _claims(packet, "sd-asr-2025-vigilant")
    assert asr
    assert not any(c["predicate_id"] in _HARDWARE_PREDS for c in asr)
    subj = [c for c in _claims(packet) if c.get("subject_id") == sd.VIGILANT]
    assert not any(c["predicate_id"] in _HARDWARE_PREDS for c in subj)


def test_subscription_access_is_inbound_only() -> None:
    """The ASR evidences configured subscription access + pooled lookup +
    vendor-cloud scope — access INTO the hosted database, never an outbound
    sharing edge or a deployment."""
    packet = sd.build_packet()
    asr = _claims(packet, "sd-asr-2025-vigilant")
    preds = {c["predicate_id"] for c in asr}
    assert {"configured_access_edge", "pooled_lookup_participation", "data_system_scope"} <= preds
    assert "sharing_partner_degree" not in preds
    assert "deployment_exists" not in preds
    # The artifact row itself records the subscription access mode.
    art = next(
        r
        for r in packet["records"]
        if r.get("record_kind") == "evidence_artifact"
        and r.get("document_id") == "sd-asr-2025-vigilant"
    )
    assert art.get("access_mode") == "subscription"


def test_bounded_non_ownership_is_scoped_verbatim() -> None:
    """The agency's 'owns no ALPR cameras or hardware under this arrangement'
    statement is a scoped q3 clause — never a universal SDPD absence claim."""
    packet = sd.build_packet()
    claim = next(
        c
        for c in _claims(packet)
        if c.get("predicate_id") == "written_policy_value"
        and c.get("subject_id") == sd.VIGILANT
        and c.get("dossier_field") == "q3"
    )
    assert "under this arrangement" in str(claim["raw_value"])
    assert "arrangement" in str(claim["value"])
    assert claim["document_id"] == "sd-asr-2025-vigilant"


# --------------------------------------------------------------------------- #
# Prime contractor ≠ component vendor
# --------------------------------------------------------------------------- #


def test_prime_contractor_and_component_vendor_stay_distinct() -> None:
    """Ubicquia is the seller/prime; Flock Safety is the incorporated
    component vendor — distinct predicates, never collapsed."""
    packet = sd.build_packet()
    contract = _claims(packet, "sd-ubicquia-agreement-2023")
    sellers = {c["value"] for c in contract if c["predicate_id"] == "seller"}
    vendors = {c["value"] for c in contract if c["predicate_id"] == "vendor"}
    buyers = {c["value"] for c in contract if c["predicate_id"] == "buyer"}
    assert sellers == {"Ubicquia, Inc."}
    assert vendors == {"Flock Safety, Inc."}
    assert buyers == {"City of San Diego"}
    # Neither name bleeds into the other's role, anywhere in the packet.
    all_claims = _claims(packet)
    assert not any(
        c["predicate_id"] == "vendor" and "Ubicquia" in str(c["value"]) for c in all_claims
    )
    assert not any(
        c["predicate_id"] in {"seller", "buyer"} and "Flock" in str(c["value"]) for c in all_claims
    )
    # The authored role-split claim exists and cites the agreement.
    split = [
        c
        for c in all_claims
        if c.get("predicate_id") == "written_policy_value" and c.get("subject_id") == sd.CONTRACT
    ]
    assert split and "prime" in str(split[0]["value"]).lower()


def test_two_subjects_vendors_co_visible_not_disputed() -> None:
    """The subscription vendor (Vigilant, on ``sdpd-vigilant``) and the
    contract's component vendor (Flock, on the contract subject) describe
    different measured things — the same-scope rule must NOT fabricate a
    dispute between them."""
    d = _dossier()
    q1 = _answer(d, "q1")
    assert q1["state"] == "supported"
    assert not any(x.get("conflicting") for x in q1["assertions"])
    vendors = {x["value"] for x in q1["assertions"] if x["predicate"] == "vendor"}
    assert vendors == {"Vigilant Solutions", "Flock Safety, Inc."}


# --------------------------------------------------------------------------- #
# Recommendation ≠ adoption; self-report ≠ oversight
# --------------------------------------------------------------------------- #


def test_oversight_recommendation_stays_proposed() -> None:
    d = _dossier()
    q10 = _answer(d, "q10")
    assert q10["state"] == "supported"
    auth = [x for x in q10["assertions"] if x["predicate"] == "authorization_state"]
    assert len(auth) == 1
    assert "proposed" in str(auth[0]["value"]).lower()
    assert "adopt" not in str(auth[0]["value"]).lower().replace("adoption", "")
    # The recommendation's existence/title claims bind to the PAB index.
    titles = {x["value"] for x in q10["assertions"] if x["predicate"] == "title"}
    assert any("Recommendation" in str(t) for t in titles)
    # No claim anywhere asserts adoption/enactment of the recommendation —
    # the proposed state is a negated-status assertion, never a promoted one.
    packet = sd.build_packet()
    for c in _claims(packet):
        if c.get("predicate_id") in {"authorization_state", "effective_from"}:
            val = str(c.get("value")).lower()
            assert "adopted" not in val and "enacted" not in val


# --------------------------------------------------------------------------- #
# Signature ≠ execution
# --------------------------------------------------------------------------- #


def test_signature_uncertainty_never_called_executed() -> None:
    """The vendor-side date verbatim + the blank City date keep execution
    unverified: genre stays 'contract', the field-state is recorded, and no
    claim calls the agreement executed."""
    packet = sd.build_packet()
    contract = _claims(packet, "sd-ubicquia-agreement-2023")
    signed = [c for c in contract if c["predicate_id"] == "signed_date"]
    assert len(signed) == 1
    assert signed[0]["value"] == "2023-12-15"
    assert "Vendor Date" in str(signed[0]["raw_value"])
    # The City side is a recorded present_but_empty field-state.
    states = {
        (c.get("value"), c.get("field_state"))
        for c in contract
        if c.get("predicate_id") == "disclosure_field_state"
    }
    assert ("execution_state", "present_but_empty") in states
    # No claim asserts the instrument is executed; the document genre is the
    # honest 'procurement_record' — never an 'executed_contract' label.
    assert all(c.get("document_genre") == "procurement_record" for c in contract)
    assert all(c.get("evidence_genre") == "contract" for c in contract)
    assert not any("executed" in str(c.get("value")).lower() for c in contract)
    # q5 carries the unverified-execution declaration.
    partial = {
        p["question"]: p["rationale"] for p in (packet.get("declared") or {}).get("partial") or []
    }
    assert "q5" in partial and "unverified" in partial["q5"]


def test_contracted_count_is_not_installed() -> None:
    """The only device count is 500 units scoped contracted_units — contracted
    is never installed/active/current."""
    packet = sd.build_packet()
    counts = [c for c in _claims(packet) if c["predicate_id"] == "contracted_device_count"]
    assert len(counts) == 1
    assert counts[0]["value"] == 500
    scopes = {q["value"] for q in counts[0].get("qualifiers") or ()}
    assert "contracted_units" in scopes
    assert not any(
        c["predicate_id"]
        in {"installed_device_count", "active_device_count", "claimed_device_count"}
        for c in _claims(packet)
    )


# --------------------------------------------------------------------------- #
# The dossier: release validity, honest marks, the twelve questions
# --------------------------------------------------------------------------- #


def _dossier() -> dict:
    return build_dossier(sd.build_packet())


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


def test_mechanical_completeness_with_honest_partial_marks() -> None:
    """The SD corpus is the fullest of the S2 cities — the designed outcome
    is mechanical completeness with scoped partial answers; pilot completion
    stays blocked on the honest not_run review mark."""
    d = _dossier()
    comp = d["completeness"]
    assert comp["mechanical_complete"] is True
    assert comp["total"] == 29
    assert comp["per_question"]["q8"] >= 2
    assert comp["pilot_complete"] is False
    assert any("not_run" in b for b in comp["blocking"])


def test_all_twelve_questions_answered_explicitly() -> None:
    d = _dossier()
    assert [a["question"] for a in d["answers"]] == list(QUESTION_IDS)
    assert all(a["state"] for a in d["answers"])


# --------------------------------------------------------------------------- #
# Question-level semantics
# --------------------------------------------------------------------------- #


def test_q1_roles_evidenced_funder_partial() -> None:
    d = _dossier()
    q1 = _answer(d, "q1")
    by_pred: dict[str, set] = {}
    for x in q1["assertions"]:
        by_pred.setdefault(x["predicate"], set()).add(x["value"])
    assert by_pred["asset_operator"] == {"San Diego Police Department"}
    assert by_pred["buyer"] == {"City of San Diego"}
    assert by_pred["seller"] == {"Ubicquia, Inc."}
    assert by_pred["vendor"] == {"Vigilant Solutions", "Flock Safety, Inc."}
    assert q1["score"] == 2  # declared partial: funder not evidenced
    packet = sd.build_packet()
    partial = {p["question"] for p in (packet.get("declared") or {}).get("partial") or []}
    assert "q1" in partial


def test_q2_two_surfaces_never_collapsed() -> None:
    """The physical streetlight program and the Vigilant subscription are
    two distinct technologies on two subjects — never one program."""
    d = _dossier()
    q2 = _answer(d, "q2")
    techs = {x["value"] for x in q2["assertions"] if x["predicate"] == "technology"}
    assert len(techs) == 2
    assert any("Vigilant LEARN" in str(t) for t in techs)
    assert any("streetlight" in str(t) for t in techs)


def test_q4_access_is_subscription_not_hardware() -> None:
    d = _dossier()
    q4 = _answer(d, "q4")
    preds = {x["predicate"]: x["value"] for x in q4["assertions"]}
    assert preds["configured_access_edge"] is True
    assert preds["pooled_lookup_participation"] is True
    assert preds["data_system_scope"] == "vendor_cloud_shared"
    assert all(x["access_mode"] == "subscription" for x in q4["assertions"])


def test_q5_execution_partial_signed_date_document_date() -> None:
    d = _dossier()
    q5 = _answer(d, "q5")
    signed = [x for x in q5["assertions"] if x["predicate"] == "signed_date"]
    assert len(signed) == 1
    assert signed[0]["value"] == "2023-12-15"
    assert signed[0]["valid_from"] is None  # never promoted to a valid window
    # P34.22b: the replay stamps carry the agreement fixture's real authoring
    # commit — never a typed replay date.
    agreement_commit = (
        datetime.fromisoformat(
            d["capture"]["fixtures"]["sd-ubicquia-agreement-2023"]["committed_at"]
        )
        .date()
        .isoformat()
    )
    assert signed[0]["observed_at"] == agreement_commit
    assert signed[0]["retrieved_date"] == agreement_commit
    # The unresolved field-state rides the question's inventory.
    assert any(
        f["field"] == "execution_state" and f["state"] == "present_but_empty"
        for f in q5["field_states"]
    )
    assert q5["score"] == 2


def test_q7_retention_scoped_to_subscription() -> None:
    d = _dossier()
    q7 = _answer(d, "q7")
    ret = [x for x in q7["assertions"] if x["predicate"] == "retention_period"]
    assert len(ret) == 1
    assert ret[0]["value"] == "60 days"
    assert "ALPR data" in str(ret[0]["raw_value"])
    assert q7["score"] == 2  # declared partial — physical program unresolved


def test_q8_sharing_mode_evidenced_actors_not() -> None:
    """The pooled vendor-hosted sharing MODE is a stated clause; outbound
    actors stay unevidenced — a scoped partial, never a silent zero and
    never a fabricated roster."""
    d = _dossier()
    q8 = _answer(d, "q8")
    assert q8["state"] == "supported"
    assert q8["score"] == 2
    vals = [str(x["value"]) for x in q8["assertions"]]
    assert any("shared across subscribing agencies" in v for v in vals)
    assert not any(x["predicate"] == "sharing_partner_degree" for x in q8["assertions"])
    assert any(f.get("action") and f.get("closing_condition") for f in q8["follow_ups"])


def test_q9_dates_are_document_dates() -> None:
    """The report-period and posted dates stay document-stated values; the
    replay stamps track each citing fixture's authoring commit."""
    d = _dossier()
    q9 = _answer(d, "q9")
    vals = {x["value"] for x in q9["assertions"]}
    assert "2025" in vals and any("2026-02-15" in str(v) for v in vals)
    for x in q9["assertions"]:
        fx = d["capture"]["fixtures"].get(x["document_id"])
        if x.get("capture_kind") == "stand-in" or fx is None:
            assert x["retrieved_date"] is None
        else:
            commit_day = datetime.fromisoformat(fx["committed_at"]).date().isoformat()
            assert x["observed_at"] == commit_day
            assert x["retrieved_date"] == commit_day
            assert x["retrieved_date"] not in (str(x["value"]), x.get("valid_from"))


def test_q11_support_profile_all_probative() -> None:
    d = _dossier()
    q11 = _answer(d, "q11")
    assert q11["state"] == "derived"
    prof = q11["derivation"]["value"]
    assert prof["instrument_backed_claims"] == 36
    assert prof["non_probative_claims"] == 0
    assert prof["claims_by_genre"] == {
        "official_statement": 11,
        "contract": 12,
        "portal_document": 13,
    }


def test_q12_field_states_and_corrections_route() -> None:
    d = _dossier()
    q12 = _answer(d, "q12")
    assert q12["state"] == "supported"
    fields = {(f["field"], f["state"]) for f in q12["field_inventory"]}
    assert ("execution_state", "present_but_empty") in fields
    assert "corrections" in str(q12.get("correction_route"))


# --------------------------------------------------------------------------- #
# Part VIII preflight — metadata only, never a workbook transport
# --------------------------------------------------------------------------- #


def test_network_audit_preflight_is_metadata_only() -> None:
    pf = sd.network_audit_preflight()
    assert pf["schema"] == "sig.part-viii-preflight/1"
    assert pf["workbook_transport"] == "never"
    assert pf["acquisition_status"] == "rejected"
    # E4-B3 = a recorded as data: the workbook path is permanently barred,
    # the link-label metadata path kept.
    assert pf["decision"]["ref"] == "E4-B3"
    assert pf["decision"]["answer"] == "a"
    assert pf["deferral"] == "D-P32.20-1"
    assert pf["prohibited_content"]
    assert "SRC-027" in pf["source_reference"]
    # The packet carries the same preflight record for self-containment.
    assert sd.build_packet()["network_audit_preflight"] == pf


def test_no_workbook_or_row_level_content_anywhere(tmp_path: Path) -> None:
    """No artifact is or contains workbook bytes — the ZIP/XLSX signature,
    a sharedStrings member name in a binary context, or any claim citing an
    audit workbook. The preflight's own *description* of prohibited content
    is metadata, not payload."""
    out = sd.write(tmp_path / "artifacts")
    for key, path in out.items():
        blob = path.read_bytes()
        # ZIP container signature (XLSX is a zip) must never appear in or
        # as an artifact — no workbook transport of any kind.
        assert b"PK\x03\x04" not in blob, f"{key} contains zip/xlsx bytes"
        assert not str(path).endswith((".xlsx", ".zip"))
    packet = sd.build_packet()
    for c in _claims(packet):
        assert "workbook" not in str(c.get("document_id")).lower()
        assert "xlsx" not in str(c.get("document_id")).lower()
        assert "audit" not in str(c.get("source_field") or "").lower()
    # No claim asserts plate/person/per-query material.
    for c in _claims(packet):
        text = f"{c.get('value')} {c.get('raw_value')}".lower()
        for banned in ("license_plate", "plate_number", "officer_name", "per_search"):
            assert banned not in text


# --------------------------------------------------------------------------- #
# Follow-up drafts — drafted, never sent (CPRA routing)
# --------------------------------------------------------------------------- #


def test_follow_up_drafts_are_drafted_never_sent() -> None:
    fud = sd.follow_up_drafts()
    assert fud["schema"] == "sig.dossier-follow-up-drafts/1"
    assert fud["posture"] == "drafted_not_sent"
    assert fud["records_requests_sent"] == 0
    drafts = fud["records_request_drafts"]
    assert drafts, "the records-obtainable gaps must produce CPRA drafts"
    for draft in drafts:
        assert draft["status"] == "drafted"
        assert draft["records_law_key"] == "CA"
        assert draft["target_agency"] == "San Diego Police Department"
        assert "7920" in draft["statutory_citation"]
        assert draft["record_type"] == "alpr_contract"
    kinds = {t["task_type"] for t in fud["research_queue"]}
    assert "missing_contract" in kinds
    assert "coverage_hole" in kinds
    assert all(t["status"] == "generated" for t in fud["research_queue"])
    packet = sd.build_packet()
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
        "proposed",
        "present_but_empty",
        "2023-12-15",
        "Ubicquia",
        "Flock Safety",
        "not_run",
        "subscription",
    ):
        assert needle in html


def test_live_return_pass_is_bounded_and_unexecuted() -> None:
    rp = sd.live_return_pass()
    assert rp["schema"] == sd.LIVE_PASS_SCHEMA
    assert rp["status"] == "prepared_not_executed"
    assert rp["deferral"] == "D-P32.20-1"
    urls = {t["url"] for t in rp["targets"]}
    assert any("annual-surveillance-report" in u for u in urls)
    assert any("ubicquia" in u for u in urls)
    assert any("data-transparency/technology" in u for u in urls)
    assert any("pab" in u for u in urls)
    # The network-audit family appears ONLY as a metadata-only preflight target.
    audit = [t for t in rp["targets"] if "audit" in str(t.get("doc_id"))]
    assert audit and audit[0]["kind"] == "metadata_only_preflight"
    assert any("Part VIII" in p for p in rp["preconditions"])
    assert any("admissibility" in p for p in rp["preconditions"])
    assert any("HG-03" in p for p in rp["preconditions"])
    assert any("workbook" in g for g in rp["non_goals"])
    assert any("rights" in g for g in rp["non_goals"])
    assert rp["bounded_questions"]


def test_live_return_pass_records_byte_bound_exception() -> None:
    """E4-B4 = a — the two over-bound/403 targets carry the recorded
    per-target byte-bound exception plus exactly ONE bounded retry."""
    rp = sd.live_return_pass()
    by_id = {t["doc_id"]: t for t in rp["targets"]}
    for doc_id in ("sd-alpr-use-policy", "sd-pab-recommendation-2025"):
        t = by_id[doc_id]
        assert t["byte_bound_exception"]
        assert t["bounded_retries"] == 1


def test_evidence_pack_names_captures_and_posture() -> None:
    md = sd.evidence_pack_markdown()
    for needle in (
        "present_but_empty",
        "subscription",
        "Ubicquia",
        "proposed",
        "not_run",
        "D-P32.20-1",
        "D-R10-SOURCES-1",
        "sd-asr-2025-vigilant",
        "sd-ubicquia-agreement-2023",
        "rejected",
        "records_requests_sent",
    ):
        assert needle in md


def test_dossier_san_diego_stays_ingestion_gated() -> None:
    """The replay's in-memory flip never touches the registry row — the source
    stays gated (D-R10-SOURCES-1 OPEN), rights flips are HG-03 only."""
    import pytest
    from connectors.loader import IngestionNotPermitted, assert_loadable
    from connectors.registry import get

    assert get("dossier_san_diego").ingestion_permitted is False
    with pytest.raises(IngestionNotPermitted):
        assert_loadable(get("dossier_san_diego"))


# --------------------------------------------------------------------------- #
# Determinism + portfolio
# --------------------------------------------------------------------------- #


def test_artifact_write_is_deterministic(tmp_path: Path) -> None:
    a = sd.write(tmp_path / "a")
    b = sd.write(tmp_path / "b")
    assert set(a) == set(b) == set(sd.ARTIFACT_NAMES)
    assert len(a) == 8
    for key in a:
        assert a[key].read_bytes() == b[key].read_bytes(), f"{key} not deterministic"


def test_portfolio_wraps_the_dossier() -> None:
    portfolio = build_portfolio([sd.build_packet()])
    assert portfolio["summary"]["dossier_count"] == 1
    assert portfolio["summary"]["pilot_complete"] == 0
    assert portfolio["summary"]["release_invalid"] == 0
