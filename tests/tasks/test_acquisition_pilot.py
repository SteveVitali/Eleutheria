# SPDX-License-Identifier: Apache-2.0
"""P32.21 — the measured gap-closing acquisition pilot (SIG-ACQ-004).

Covers the batch contract: the five-family selection under the live-stage
ceilings (≤2 incremental non-portfolio families, ≤10 documents/aggregate
rows per family, ≤2 new protocol families, ≤5 total including the three
pilot cities), the recorded rejected alternatives, the fail-closed
exclusions (P31-owned, duplicate, blocked, screening-required, prohibited
metadata-only SRC-027), the funnel + maintenance measurement over committed
artifacts (offline replay, never live), the before/after gap ledger's
unique-contribution reconciliation, the per-family
continue/stop/improve recommendations, and the exact gate packets for the
bounded live slices — every slice pinned to an OPEN return-pass row because
no approval reference exists.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from tasks.acquisition import build_queue
from tasks.acquisition_pilot import (
    BATCH_SCHEMA,
    CEILINGS,
    FUNNEL_STAGES,
    GAP_LEDGER_SCHEMA,
    PILOT_DEFERRAL,
    PORTFOLIO,
    READOUT_SCHEMA,
    RETRY_BUDGET_PER_TARGET,
    RETURN_PASS_SCHEMA,
    FamilySelection,
    PilotBatch,
    PilotCeilings,
    PilotError,
    RejectReason,
    check_batch,
    check_pilot,
    pilot_readout,
    read_dossier_facts,
    render_readout,
    select_batch,
)
from tasks.cli import main as tasks_cli_main

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def entries():
    """The real reviewed queue (P32.11)."""
    return build_queue()


@pytest.fixture(scope="module")
def readout(entries):
    return pilot_readout(entries)


# --------------------------------------------------------------------------- #
# Batch selection                                                             #
# --------------------------------------------------------------------------- #


def test_batch_is_five_families_three_portfolio_two_incremental(entries):
    batch = select_batch(entries)
    assert len(batch.families) == 5
    portfolio = [f for f in batch.families if f.slot == "portfolio"]
    incremental = [f for f in batch.families if f.slot == "incremental"]
    assert len(portfolio) == 3
    assert len(incremental) == 2
    assert {f.family_id for f in portfolio} == {"okc", "tulsa", "san-diego"}
    assert {f.lineage_group for f in incremental} == {
        "oklahoma-state",
        "california-state-auditor",
    }
    # Five families = five distinct provenance groups.
    assert len({f.lineage_group for f in batch.families}) == 5


def test_batch_schema_and_version(readout):
    assert readout["batch"]["schema"] == BATCH_SCHEMA
    assert readout["schema"] == READOUT_SCHEMA


def test_src027_kept_outside_the_acquired_batch(entries):
    batch = select_batch(entries)
    for fam in batch.families:
        assert "SRC-027" not in fam.candidate_ids
    sd = next(f for f in batch.families if f.family_id == "san-diego")
    assert "SRC-027" in sd.excluded_candidate_ids
    # …and it is recorded as a rejected alternative with the prohibited reason.
    reasons = {r.reason for r in batch.rejected if r.candidate_id == "SRC-027"}
    assert RejectReason.PROHIBITED in reasons


def test_incremental_family_slices_close_recorded_dossier_gaps(entries):
    batch = select_batch(entries)
    ok_state = next(f for f in batch.families if f.lineage_group == "oklahoma-state")
    # The slice brings the P0-dossier authority-chain candidate + the
    # contract-channel candidate; the award members stay outside the batch.
    assert set(ok_state.candidate_ids) == {"SRC-006", "SRC-007"}
    assert set(ok_state.excluded_candidate_ids) == {"SRC-008", "SRC-009"}
    assert "dossier" in ok_state.rationale or "SRC-007" in ok_state.rationale


def test_every_non_selected_candidate_has_a_recorded_reason(entries, readout):
    selected = {cid for f in readout["batch"]["families"] for cid in f["candidate_ids"]}
    rejected = {r["candidate_id"] for r in readout["batch"]["rejected_alternatives"]}
    every = {e.passport.candidate_id for e in entries}
    # Every candidate outside the batch is a recorded rejection…
    assert every - selected <= rejected
    # …and every selected candidate ALSO recorded as rejected is a portfolio
    # member (rejected *as an incremental candidate*, never silently dropped).
    for cid in selected & rejected:
        reasons = {
            r["reason"]
            for r in readout["batch"]["rejected_alternatives"]
            if r["candidate_id"] == cid
        }
        assert "portfolio_member" in reasons


def test_rejected_alternatives_carry_expected_reasons(readout):
    by_id = {}
    for r in readout["batch"]["rejected_alternatives"]:
        by_id.setdefault(r["candidate_id"], set()).add(r["reason"])
    assert by_id["SRC-024"] == {"preflight_screening_owed"}
    assert by_id["SRC-025"] == {"preflight_screening_owed"}
    assert by_id["SRC-008"] == {"no_recorded_award_gap"}
    assert by_id["SRC-022"] == {"no_recorded_award_gap"}
    # The cooperative-contract improvement is the ranked next-in-line.
    assert by_id["SRC-010"] == {"capacity"}
    assert by_id["SRC-012"] == {"capacity"}
    # P31-owned sources can never be re-onboarded (real joins in this inventory).
    assert by_id["SRC-023"] == {"p31_owned"}
    assert by_id["SRC-026"] == {"p31_owned"}
    # Portfolio members are named, not silently dropped.
    assert "portfolio_member" in by_id["SRC-004"]


def test_no_p31_owned_or_mirror_in_batch(entries, readout):
    selected = {cid for f in readout["batch"]["families"] for cid in f["candidate_ids"]}
    for cid in selected:
        e = next(x for x in entries if x.passport.candidate_id == cid)
        assert not any(ls.p31_owned for ls in e.join.linked)
        assert e.passport.independent_yield


def test_incremental_slot_respects_rank_order_when_leader_removed(entries):
    """Determinism + rank-order proof: with oklahoma-state out of the pool,
    the next-ranked acquisition-shape family (sourcewell) fills the slot."""
    reduced = [e for e in entries if e.passport.lineage_group != "oklahoma-state"]
    batch = select_batch(reduced)
    groups = {f.lineage_group for f in batch.families if f.slot == "incremental"}
    assert groups == {"sourcewell-cooperative", "california-state-auditor"}


def test_incremental_ceiling_fails_closed(entries):
    with pytest.raises(PilotError):
        select_batch(entries, ceilings=PilotCeilings(incremental_families=1))


def test_total_family_ceiling_fails_closed(entries):
    with pytest.raises(PilotError):
        select_batch(entries, ceilings=PilotCeilings(total_families=4))


def test_check_batch_flags_duplicate_groups(entries):
    batch = select_batch(entries)
    dup = FamilySelection(
        slot="incremental",
        family_id="dup",
        lineage_group="oklahoma-state",
        role="x",
        candidate_ids=(),
        excluded_candidate_ids=(),
        rule="P-SEL-2",
        rationale="x",
    )
    bad = PilotBatch(
        schema=BATCH_SCHEMA,
        selection_version="test",
        ceilings=CEILINGS,
        families=(*batch.families, dup),
        rejected=batch.rejected,
        totals={},
    )
    violations = check_batch(bad, entries)
    assert any("lineage group" in v or "families" in v for v in violations)


def test_check_batch_flags_src027_in_batch(entries):
    batch = select_batch(entries)
    bad_fam = FamilySelection(
        slot="incremental",
        family_id="san-diego-municipal",
        lineage_group="san-diego-municipal",
        role="x",
        candidate_ids=("SRC-027",),
        excluded_candidate_ids=(),
        rule="P-SEL-2",
        rationale="x",
    )
    bad = PilotBatch(
        schema=BATCH_SCHEMA,
        selection_version="test",
        ceilings=CEILINGS,
        families=(*batch.families[:3], bad_fam),
        rejected=batch.rejected,
        totals={},
    )
    violations = check_batch(bad, entries)
    assert any("SRC-027" in v for v in violations)


# --------------------------------------------------------------------------- #
# Dossier facts — offline replay measurement                                  #
# --------------------------------------------------------------------------- #


def test_dossier_facts_from_committed_artifacts():
    by_id = {pf.family_id: pf for pf in PORTFOLIO}
    okc = read_dossier_facts(by_id["okc"])
    assert okc.captures == 3  # only the dossier_okc family's own slice
    assert okc.claims == 37
    assert okc.claims_by_source["dossier_okc"] == 16
    assert okc.mechanical_complete is True
    assert okc.pilot_complete is False
    assert okc.review_status == "not_run"
    sd = read_dossier_facts(by_id["san-diego"])
    assert sd.captures == 6  # 4 artifacts + 2 index_page, one source family
    assert len(sd.documents) == 4
    assert sd.unique_to_family_slugs  # the only source family on the dossier
    assert sd.return_pass_targets == 9
    tulsa = read_dossier_facts(by_id["tulsa"])
    assert tulsa.mechanical_complete is False  # the honest 24/36 partial


def test_unique_contributions_are_assertion_level():
    """A shared question with multiple sources is never counted unique."""
    okc = read_dossier_facts(PORTFOLIO[0])
    # dossier_okc shares every question it touches with at least one other
    # pre-existing registered source — its uniqueness is at fact level.
    assert okc.shared_slugs
    assert okc.unique_assertions > 0
    # Unique + shared slugs never double-count.
    assert not (set(okc.unique_to_family_slugs) & set(okc.shared_slugs))


# --------------------------------------------------------------------------- #
# Funnel + maintenance burden                                                 #
# --------------------------------------------------------------------------- #


def test_funnel_stage_order_and_live_zero(readout):
    funnel = readout["funnel"]
    assert funnel["stages"] == list(FUNNEL_STAGES)
    for fam in funnel["families"].values():
        assert fam["funnel"]["capture"]["captured_live"] == 0
    assert funnel["totals"]["captured_live_all_families"] == 0


def test_funnel_portfolio_counts_come_from_packets(readout):
    fam = readout["funnel"]["families"]
    assert fam["okc"]["funnel"]["capture"]["captures_offline_fixture"] == 3
    assert fam["okc"]["funnel"]["extraction"]["claims_emitted"] == 37
    assert fam["tulsa"]["funnel"]["extraction"]["claims_emitted"] == 16
    assert fam["san-diego"]["funnel"]["capture"]["captures_offline_fixture"] == 6


def test_funnel_labels_offline_replay_never_live(readout):
    fam = readout["funnel"]["families"]
    assert "offline" in fam["okc"]["funnel"]["capture"]["basis"]
    assert fam["okc"]["funnel"]["approval_gate"]["approval_refs"] == []
    assert fam["okc"]["funnel"]["approval_gate"]["decisions_recorded"] == 0


def test_incremental_funnel_is_pending_live(readout):
    fam = readout["funnel"]["families"]
    inc = fam["oklahoma-state"]
    assert inc["funnel"]["capture"]["documents_in_slice"] == 4
    assert inc["funnel"]["capture"]["documents_in_slice"] <= 10
    assert inc["funnel"]["capture"]["captured_live"] == 0
    assert inc["funnel"]["link_support"]["status"] == "pending_live"
    assert set(inc["funnel"]["candidate_qualification"]["excluded_from_batch"]) == {
        "SRC-008",
        "SRC-009",
    }


def test_maintenance_burden_fields(readout):
    for fam in readout["funnel"]["families"].values():
        m = fam["maintenance"]
        assert m["target_count"] >= 0
        assert m["protocol_count"] >= 0
        assert m["new_protocol_families"] == 0
        assert m["expected_refresh"]
        assert m["effort_owner"]
        assert m["retry_budget"]["per_target"] == RETRY_BUDGET_PER_TARGET
        assert m["cost"]["measured_minutes"] is None
        # Burden is distinguished: one-time setup (estimate only), recurring
        # maintenance, and never-fabricated measured minutes.
        assert m["cost"]["one_time_setup"]
        assert m["cost"]["recurring_maintenance"]
    sd_failures = readout["funnel"]["families"]["san-diego"]["maintenance"]["retry_budget"][
        "recorded_failures"
    ]
    assert any("403" in f or "16 MB" in f for f in sd_failures)


def test_blocked_targets_visible_with_reasons_and_budget(readout):
    blocked = {b["candidate_id"]: b for b in readout["funnel"]["blocked_targets_visible"]}
    # Every gate-blocked/prohibited/undetermined target stays visible.
    assert "SRC-027" in blocked
    assert any("prohibited" in r for r in blocked["SRC-027"]["reasons"])
    assert "SRC-024" in blocked
    assert any("screening" in r for r in blocked["SRC-024"]["reasons"])
    assert any("403" in r for r in blocked["SRC-001"]["reasons"])
    for b in blocked.values():
        assert b["retry_budget"] == RETRY_BUDGET_PER_TARGET
        assert b["escalation"]


# --------------------------------------------------------------------------- #
# Gap ledger                                                                  #
# --------------------------------------------------------------------------- #


def test_gap_ledger_schema_and_reconciliation(readout):
    ledger = readout["gap_ledger"]
    assert ledger["schema"] == GAP_LEDGER_SCHEMA
    rec = ledger["reconciliation"]
    assert rec["double_counted"] == 0
    assert rec["mirror_as_independent"] == 0
    assert rec["p31_duplicate_onboarding"] == 0
    # San Diego's single family uniquely supports every assertion-backed
    # slug (a supported slug with zero assertions is never claimed unique).
    sd = ledger["after"]["san-diego"]
    assert set(sd["unique_supported_slugs"]) <= set(sd["supported_slugs"])
    assert len(sd["unique_supported_slugs"]) == 10
    assert sd["unique_assertions"] > 0


def test_gap_ledger_incrementals_are_pending_live_never_counted(readout):
    for fam_id in ("oklahoma-state", "california-state-auditor"):
        after = readout["gap_ledger"]["after"][fam_id]
        assert after["supported_slugs"] == []
        assert "pending_live" in after["status"]
        assert after["expected_unique_contribution"]


def test_no_award_gap_recorded_in_dossier_ledgers(readout):
    hits = readout["funnel"]["rejected_families_still_visible"]["award_precondition_evidence"]
    assert hits == []


# --------------------------------------------------------------------------- #
# Recommendations                                                             #
# --------------------------------------------------------------------------- #


def test_recommendations_one_verdict_per_family(readout):
    recs = {r["family_id"]: r for r in readout["recommendations"]}
    assert set(recs) == set(readout["funnel"]["families"])
    assert recs["tulsa"]["verdict"] == "improve"  # honest partial dossier
    assert recs["okc"]["verdict"] == "continue"
    assert recs["san-diego"]["verdict"] == "continue"
    assert recs["oklahoma-state"]["verdict"] == "continue"
    assert recs["california-state-auditor"]["verdict"] == "continue"
    for r in recs.values():
        assert r["unique_closure"]
        assert r["cost_basis"]
        assert r["stop_conditions"]
        assert r["conditions"]
    # SRC-027 gets no recommendation — it is not a batch family.
    assert "SRC-027" not in recs


# --------------------------------------------------------------------------- #
# Gate packets                                                                #
# --------------------------------------------------------------------------- #


def test_return_pass_packet_schema_status_deferral(readout):
    rp = readout["return_pass"]
    assert rp["schema"] == RETURN_PASS_SCHEMA
    assert rp["status"] == "prepared_not_executed"
    assert rp["deferral"] == PILOT_DEFERRAL
    assert rp["portfolio_return_passes"] == [
        "D-P32.18-1",
        "D-P32.19-1",
        "D-P32.20-1",
    ]


def test_return_pass_targets_within_caps_no_approvals(readout):
    rp = readout["return_pass"]
    assert len(rp["families"]) == 2
    for fam in rp["families"]:
        assert fam["approval_refs"] == []
        assert len(fam["targets"]) <= fam["document_cap"] == 10
        assert fam["new_protocol_families"] == 0
        for t in fam["targets"]:
            assert t["url"].startswith("https://")
            assert t["goal"]
    ok = next(f for f in rp["families"] if f["family"] == "oklahoma-state")
    assert set(ok["candidate_ids"]) == {"SRC-006", "SRC-007"}
    assert set(ok["excluded_candidate_ids"]) == {"SRC-008", "SRC-009"}
    assert len(ok["targets"]) == 4


def test_return_pass_non_goals_and_preconditions(readout):
    rp = readout["return_pass"]
    blob = " ".join(rp["non_goals"]).lower()
    assert "crawler" in blob
    assert "workbook" in blob or "sharedstrings" in blob
    assert "rights flip" in blob or "ingestion_permitted" in blob
    assert "records request" in blob
    assert "spending" in blob
    prec = " ".join(rp["preconditions"])
    assert "HG-03" in prec
    assert "Part VIII" in prec


# --------------------------------------------------------------------------- #
# Readout + check_pilot invariants                                            #
# --------------------------------------------------------------------------- #


def test_descriptive_only_and_no_causal_claim(readout):
    assert readout["descriptive_only"]
    assert "not run" in readout["funnel"]["matched_comparison"]
    assert readout["live_verification"] is False
    assert readout["expansion"]


def test_check_pilot_zero_violations(readout, entries):
    assert check_pilot(readout, entries) == []


def test_check_pilot_flags_fabricated_live_capture(readout, entries):
    bad = copy.deepcopy(readout)
    bad["funnel"]["families"]["okc"]["funnel"]["capture"]["captured_live"] = 1
    violations = check_pilot(bad, entries)
    assert any("live capture" in v for v in violations)


def test_check_pilot_flags_fabricated_approval_ref(readout, entries):
    bad = copy.deepcopy(readout)
    bad["return_pass"]["families"][0]["approval_refs"] = ["HG-03:fake"]
    violations = check_pilot(bad, entries)
    assert any("approval" in v for v in violations)


def test_check_pilot_flags_src027_in_batch(readout, entries):
    bad = copy.deepcopy(readout)
    bad["batch"]["families"][0]["candidate_ids"].append("SRC-027")
    violations = check_pilot(bad, entries)
    assert any("SRC-027" in v for v in violations)


def test_check_pilot_flags_measured_minutes_fabrication(readout, entries):
    bad = copy.deepcopy(readout)
    bad["funnel"]["families"]["okc"]["maintenance"]["cost"]["measured_minutes"] = 42
    violations = check_pilot(bad, entries)
    assert any("measured_minutes" in v for v in violations)


def test_check_pilot_flags_missing_deferral(readout, entries):
    bad = copy.deepcopy(readout)
    bad["deferrals"]["opened"] = []
    violations = check_pilot(bad, entries)
    assert any("return-pass" in v for v in violations)


def test_check_pilot_verifies_the_open_rows_in_the_register(readout, entries, tmp_path):
    """A named deferral is only an OPEN row when DEFERRALS.md carries it."""
    # Empty root → the register is missing → the check fails closed.
    violations = check_pilot(readout, entries, root=tmp_path)
    assert any("DEFERRALS" in v for v in violations)
    # A register without the owned row fails too.
    (tmp_path / "docs/tickets").mkdir(parents=True)
    (tmp_path / "docs/tickets/DEFERRALS.md").write_text(
        "| id | kind | item | why | unblocked | verify | proxy | status |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| D-P32.18-1 | P | x | y | z | w | p | OPEN |\n"
        "| D-P32.19-1 | P | x | y | z | w | p | OPEN |\n"
        "| D-P32.20-1 | P | x | y | z | w | p | OPEN |\n"
    )
    violations = check_pilot(readout, entries, root=tmp_path)
    assert any("D-P32.21-1" in v for v in violations)
    # And a CLOSED row is not an OPEN home.
    (tmp_path / "docs/tickets/DEFERRALS.md").write_text(
        "| id | kind | item | why | unblocked | verify | proxy | status |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| D-P32.18-1 | P | x | y | z | w | p | OPEN |\n"
        "| D-P32.19-1 | P | x | y | z | w | p | OPEN |\n"
        "| D-P32.20-1 | P | x | y | z | w | p | OPEN |\n"
        "| D-P32.21-1 | P | x | y | z | w | p | DONE |\n"
    )
    violations = check_pilot(readout, entries, root=tmp_path)
    assert any("D-P32.21-1" in v and "OPEN" in v for v in violations)


def test_render_readout_markdown(readout):
    md = render_readout(readout)
    assert "descriptive only" in md
    assert "SRC-027" in md
    assert "D-P32.21-1" in md
    assert "new scope decision" in md
    assert "**continue**" in md and "**improve**" in md
    assert "oklahoma-state" in md and "california-state-auditor" in md


def test_readout_is_deterministic(entries):
    a = json.dumps(pilot_readout(entries), sort_keys=True)
    b = json.dumps(pilot_readout(entries), sort_keys=True)
    assert a == b


def test_no_network_surface_in_module():
    """The pilot reads committed artifacts only — no fetch machinery exists."""
    src = (REPO_ROOT / "tasks/src/tasks/acquisition_pilot.py").read_text()
    for forbidden in ("import httpx", "import urllib", "import socket", "requests."):
        assert forbidden not in src


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #


def test_cli_pilot_check_green(capsys):
    assert tasks_cli_main(["acquisition", "pilot-check"]) == 0
    out = capsys.readouterr().out
    assert "0 violations" in out


def test_cli_pilot_writes_artifacts(tmp_path, capsys):
    out_dir = tmp_path / "pilot"
    assert tasks_cli_main(["acquisition", "pilot", "--out", str(out_dir)]) == 0
    capsys.readouterr()
    batch = json.loads((out_dir / "BATCH.json").read_text())
    assert batch["schema"] == BATCH_SCHEMA
    rp = json.loads((out_dir / "ACQ_PILOT_RETURN_PASS.json").read_text())
    assert rp["schema"] == RETURN_PASS_SCHEMA
    assert rp["status"] == "prepared_not_executed"
    funnel = json.loads((out_dir / "FUNNEL.json").read_text())
    assert funnel["totals"]["captured_live_all_families"] == 0
    ledger = json.loads((out_dir / "GAP_LEDGER.json").read_text())
    assert ledger["schema"] == GAP_LEDGER_SCHEMA
    md = (out_dir / "READOUT.md").read_text()
    assert "descriptive only" in md
    readout = json.loads((out_dir / "READOUT.json").read_text())
    assert readout["schema"] == READOUT_SCHEMA


def test_cli_pilot_json_stdout(capsys):
    assert tasks_cli_main(["acquisition", "pilot", "--json"]) == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["schema"] == READOUT_SCHEMA
