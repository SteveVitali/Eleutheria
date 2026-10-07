# SPDX-License-Identifier: Apache-2.0
"""P32.11 — the gap-driven reviewed acquisition queue (§55.6).

Covers SIG-ACQ-001 (gap-first, provenance, lineage/dup dedup) and
SIG-ACQ-002 (passport completeness, three separate rights lanes, hard
rights/sensitivity gates, Part VIII preflight), plus the acceptance criteria:
mirrors never corroborate, an existing source is never onboarded twice,
usefulness never overrides gates, municipal publication is not auto-CC0, and
scores are explainable/versioned with uncertainty and measured-vs-estimated
cost. Everything is offline: no fetch, no flip, no minted decision.
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from connectors.registry import registry as source_registry
from tasks.acquisition import (
    CandidatePassport,
    CostRecord,
    LaneDecision,
    LaneRecord,
    LineageClass,
    LinkKind,
    PreflightStatus,
    QueueDisposition,
    RegistryLinkSpec,
    RegistryRelation,
    build_queue,
    check_queue,
    diff_assessments,
    disposition_for,
    gates_for,
    independent_corroboration,
    join_candidate,
    load_research_rows,
    missing_questions,
    normalize_url,
    queue_report,
    rank_entries,
    review_packet,
    score,
)
from tasks.cli import main as tasks_cli_main

from tasks import acquisition as acq

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def entries():
    """The real seeded queue — 27 candidates joined to the live registry."""
    return build_queue()


@pytest.fixture(scope="module")
def by_id(entries):
    return {e.passport.candidate_id: e for e in entries}


def _mutate(p: CandidatePassport, **kw) -> CandidatePassport:
    """Clone a valid seeded passport with fields replaced (a synthetic case
    must still pass every passport invariant on its own)."""
    return replace(p, **kw)


# --------------------------------------------------------------------------- #
# Seeding — the researched inventory, verbatim, approving nothing             #
# --------------------------------------------------------------------------- #


def test_seed_loads_all_27_research_rows(entries, by_id):
    rows = load_research_rows()
    assert len(rows) == 27
    assert len(entries) == 27
    assert set(by_id) == {r["candidate_id"] for r in rows}
    # provenance carried verbatim — the CSV is the source of truth for leads
    for r in rows:
        p = by_id[r["candidate_id"]].passport
        assert p.discovery.primary_url == r["primary_url"]
        assert p.discovery.review_status == r["review_status"]
        assert p.claims_supported == r["claims_supported"]
        assert p.not_supported == r["not_supported"]
        assert p.priority == r["priority"]


def test_every_candidate_carries_a_passport(entries):
    for e in entries:
        p = e.passport
        assert p.authority and p.jurisdiction and p.novelty
        # SIG-ACQ-001: acquisition starts from a NAMED gap, not a bare source —
        # and SIG-ACQ-002: scope/time is a passport element
        assert p.gap and p.content_window
        assert p.discovery.primary_url and p.discovery.review_status
        assert p.lineage_group
        assert p.target_predicates
        assert not p.problems()  # completeness validated at load


DECIDED_BY_PREPARED_FLIP = {
    "SRC-001",
    "SRC-002",
    "SRC-003",
    "SRC-004",
    "SRC-005",
    "SRC-006",
    "SRC-007",
    "SRC-011",
}


def test_only_the_prepared_flip_batch_is_decided(entries):
    """The r11/sources-flips apply (HG-03, E4-B1 = a) decides all three lanes
    of exactly the 8 selected candidates — each citing the recorded
    p3438_dispositions.json disposition — and mints nothing else: every other
    candidate stays undetermined, inadmissible and not onboardable (the queue
    still cannot mint a rights decision)."""
    for e in entries:
        lanes = [r for _l, r in e.passport.rights.lanes()]
        if e.passport.candidate_id in DECIDED_BY_PREPARED_FLIP:
            assert all(r.decision == LaneDecision.DECIDED for r in lanes)
            for r in lanes:
                assert "p3438_dispositions.json" in r.decision_ref
                assert r.decided_by and r.decided_on and r.basis
            assert acq.Gate.RIGHTS_UNDETERMINED not in e.gates
        else:
            assert all(r.decision != LaneDecision.DECIDED for r in lanes)
            assert acq.Gate.RIGHTS_UNDETERMINED in e.gates
            assert not e.admissible
            assert not e.onboardable


def test_seed_assessment_is_versioned_estimated_not_measured(entries):
    for e in entries:
        a = e.passport.dimensions
        assert a.version == acq.SEED_VERSION
        assert a.assessor  # a role label, never a personal name
        assert a.measured is False
        assert e.score_result.assessment_version == acq.SEED_VERSION
        assert e.score_result.scoring_version == acq.SCORING_VERSION


def test_queue_is_data_not_code(entries, by_id):
    """Every candidate is a reviewable row — including refused/blocked ones
    (kept visible, never silently dropped)."""
    dispositions = {e.disposition for e in entries}
    assert QueueDisposition.REVIEW_NEW_TARGET in dispositions
    assert QueueDisposition.REVIEW_IMPROVEMENT in dispositions
    # the seeded inventory contains no literal duplicates or rejections —
    # but nothing may have been dropped to claim that
    assert len(entries) == len(by_id)


# --------------------------------------------------------------------------- #
# Registry + P31 join — never onboard an existing source twice                #
# --------------------------------------------------------------------------- #


def test_same_source_is_improvement_never_reonboarded(by_id):
    for cid, src in (
        ("SRC-010", "sourcewell"),
        ("SRC-019", "ccops_berkeley"),
        ("SRC-020", "ccops_boston"),
        ("SRC-025", "faa_drone_waivers"),
    ):
        e = by_id[cid]
        same = [ls for ls in e.join.linked if ls.link.kind == LinkKind.SAME_SOURCE]
        assert [ls.source_id for ls in same] == [src]
        assert e.join.relation == RegistryRelation.EXISTING_UNPERMITTED
        assert e.disposition == QueueDisposition.REVIEW_IMPROVEMENT
        assert e.kind == "improvement"
        assert not e.onboardable


def test_p31_owned_source_refuses_reonboarding(by_id):
    """A same_source link into a P31.12/.13-owned source is consumed or
    improved under prior decisions — never emitted as new work."""
    p = by_id["SRC-023"].passport
    synthetic = _mutate(
        p,
        registry_links=(RegistryLinkSpec("gao_surveillance_reports", LinkKind.SAME_SOURCE),),
    )
    join = join_candidate(synthetic, dispositions={})
    assert join.relation == RegistryRelation.P31_OWNED
    gates = gates_for(synthetic, join)
    assert acq.Gate.P31_OWNED in gates
    assert disposition_for(synthetic, join, gates) == QueueDisposition.CONSUME_EXISTING


def test_related_links_resolve_and_carry_p31_dispositions(by_id):
    e = by_id["SRC-023"]  # related → dhs_oig_reports, dhs_fusion_center_assessments
    linked = {ls.source_id for ls in e.join.linked}
    assert {"dhs_oig_reports", "dhs_fusion_center_assessments"} <= linked
    for ls in e.join.linked:
        assert ls.p31_owned  # both are P31.12/.13-owned
        assert ls.dispositions  # the recorded rights dispositions are joined
        assert all(d.source_id == ls.source_id for d in ls.dispositions)
    # net_new relation stays net_new — related context is not identity
    assert e.join.relation == RegistryRelation.NET_NEW


def test_unknown_registry_link_fails_closed():
    """A link id that resolves to no registered source fails the join loudly —
    dedupe context can never silently reference a phantom row."""
    table = tomllib.loads((REPO_ROOT / "tasks/src/tasks/data/acquisition_queue.toml").read_text())
    table["candidates"]["SRC-001"]["links"] = [{"id": "no_such_source", "kind": "related"}]
    with pytest.raises(acq.AcquisitionQueueError, match="no_such_source"):
        build_queue(queue_table=table)


# --------------------------------------------------------------------------- #
# Lineage + duplicates — mirrors never corroborate                            #
# --------------------------------------------------------------------------- #


def test_non_independent_lineage_cannot_score_independence(by_id):
    """SRC-027 is an aggregate over the same SDPD audit corpus — I must be 0
    and it can never corroborate SRC-003 (same lineage group, non-independent
    class)."""
    e27, e03 = by_id["SRC-027"], by_id["SRC-003"]
    assert e27.passport.lineage_class == LineageClass.DERIVED_SUMMARY
    assert e27.passport.independent_yield is False
    assert e27.passport.dimensions.values["I"] == 0
    assert e27.score_result.contributions["I"] == 0
    assert not independent_corroboration(e27.passport, e03.passport)
    assert not independent_corroboration(e03.passport, e27.passport)


def test_same_lineage_group_is_one_provenance(by_id):
    """Two genuinely independent publishers could corroborate; two candidates
    in one institutional lineage group never do."""
    e03, e04 = by_id["SRC-003"], by_id["SRC-004"]  # both san-diego-municipal
    assert e03.passport.lineage_class == LineageClass.INDEPENDENT_ACCOUNT
    assert e04.passport.lineage_class == LineageClass.INDEPENDENT_ACCOUNT
    assert not independent_corroboration(e03.passport, e04.passport)
    # distinct groups with independent classes CAN corroborate
    e02 = by_id["SRC-002"]
    assert independent_corroboration(e02.passport, e03.passport)


def test_mirror_dimension_i_is_refused(by_id):
    """A passport that claims independence credit for a non-independent
    lineage class fails validation at load."""
    p = by_id["SRC-027"].passport
    bad = _mutate(p, dimensions=replace(p.dimensions, values={**p.dimensions.values, "I": 2}))
    assert any("cannot yield independent" in m for m in bad.problems())


def test_literal_url_duplicate_refused(by_id):
    """Two candidates sharing a normalized URL are one artifact — the second
    is a duplicate, never onboarded."""
    p = by_id["SRC-001"].passport
    twin = _mutate(
        p,
        candidate_id="SRC-999",
        lineage_group="elsewhere",
        discovery=replace(
            p.discovery,
            # same artifact behind a different scheme/query/trailing slash —
            # normalisation must still collapse it to the same URL
            primary_url="HTTPS://"
            + p.discovery.primary_url.split("://", 1)[-1].rstrip("/")
            + "/?utm=x",
        ),
    )
    join = join_candidate(twin, dispositions={}, peers=[p])
    assert join.relation == RegistryRelation.DUPLICATE
    assert join.duplicate_of == "candidate:SRC-001"
    assert disposition_for(twin, join, gates_for(twin, join)) == (
        QueueDisposition.REFUSED_DUPLICATE
    )


def test_registered_homepage_collision_is_duplicate(by_id):
    """A candidate URL colliding with a registered homepage is a duplicate of
    that source — no second onboarding."""
    reg = source_registry()
    home = next(r.homepage_url for r in reg.values() if r.homepage_url)
    p = by_id["SRC-013"].passport  # net_new with no same_source links
    synthetic = _mutate(
        p,
        candidate_id="SRC-998",
        registry_links=(),
        discovery=replace(p.discovery, primary_url="https://" + home.split("://", 1)[-1]),
    )
    join = join_candidate(synthetic, registry=reg, dispositions={}, peers=[])
    assert join.relation == RegistryRelation.DUPLICATE
    assert join.duplicate_of.startswith("source:")


def test_normalize_url():
    assert normalize_url("HTTPS://WWW.Example.com/path/?q=1#f") == "example.com/path"
    assert normalize_url("example.com/path") == "example.com/path"


# --------------------------------------------------------------------------- #
# Hard gates — usefulness never opens them (SIG-ACQ-002)                      #
# --------------------------------------------------------------------------- #


def _all_decided(rights) -> object:
    good = LaneRecord(
        decision=LaneDecision.DECIDED,
        decision_ref="docs/build/reports/rights/test_packet.md",
        decided_by="sig-rights-review",
        decided_on=date(2026, 9, 26),
        basis="permissible per recorded review",
    )
    return replace(
        rights,
        document_bytes=good,
        fact_extraction=good,
        derived_publication=good,
    )


def test_undetermined_rights_gate_blocks_any_score(by_id):
    # SRC-009 (excluded from the prepared-flip batch — its lanes stay
    # undetermined, so the gate still bites regardless of score).
    p = by_id["SRC-009"].passport
    assert p.dimensions.values == {d: p.dimensions.values[d] for d in acq.DIMENSIONS}
    e = by_id["SRC-009"]
    assert acq.Gate.RIGHTS_UNDETERMINED in e.gates
    assert not e.admissible  # a high score buys nothing


def test_rejected_rights_blocked_regardless_of_usefulness(by_id):
    p = by_id["SRC-002"].passport
    rejected = _mutate(
        p,
        rights=replace(
            _all_decided(p.rights),
            fact_extraction=LaneRecord(
                decision=LaneDecision.REJECTED, basis="terms forbid extraction"
            ),
        ),
    )
    join = join_candidate(rejected, dispositions={}, peers=[])
    gates = gates_for(rejected, join)
    assert acq.Gate.RIGHTS_REJECTED in gates
    assert acq.Gate.RIGHTS_UNDETERMINED not in gates
    assert disposition_for(rejected, join, gates) == QueueDisposition.BLOCKED


def test_sensitive_rejection_is_terminal_not_a_score(by_id):
    """Part VIII REJECTED → BLOCKED; no usefulness offset exists — S can only
    push the score down, never clear the gate."""
    p = by_id["SRC-001"].passport
    sensitive = _mutate(p, preflight=replace(p.preflight, status=PreflightStatus.REJECTED))
    join = join_candidate(sensitive, dispositions={}, peers=[])
    gates = gates_for(sensitive, join)
    assert acq.Gate.SENSITIVE_REJECTED in gates
    assert disposition_for(sensitive, join, gates) == QueueDisposition.BLOCKED


def test_prohibited_until_review_is_a_gate_not_a_veto(by_id):
    """prohibited_until_review = a gate on admissibility, not the outright
    BLOCKED disposition a rejected/blocked record gets. P34.38 records
    E4-B3 on SRC-027 itself (rejected), so the semantic is exercised on a
    mutated passport."""
    e = by_id["SRC-027"]
    p = e.passport
    prohibited = _mutate(
        p, preflight=replace(p.preflight, status=PreflightStatus.PROHIBITED_UNTIL_REVIEW)
    )
    join = join_candidate(prohibited, dispositions={}, peers=[])
    gates = gates_for(prohibited, join)
    assert acq.Gate.PREFLIGHT_PROHIBITED in gates
    assert acq.Gate.SENSITIVE_REJECTED not in gates
    assert disposition_for(prohibited, join, gates) != QueueDisposition.BLOCKED


def test_src027_workbook_path_rejected_metadata_path_kept(by_id):
    """E4-B3 = a (2026-10-01T04:51:39Z): the per-query network-audit
    workbooks are metadata-only permanently — the recorded status is
    ``rejected`` (a hard rejection no score can offset), the link-label
    metadata path is kept."""
    e = by_id["SRC-027"]
    assert e.passport.preflight.status == PreflightStatus.REJECTED
    assert acq.Gate.SENSITIVE_REJECTED in e.gates
    assert e.disposition == QueueDisposition.BLOCKED
    assert not e.admissible
    assert "metadata" in e.passport.preflight.notes.lower()


def test_municipal_publication_is_not_auto_cc0(by_id):
    """A municipal publisher observed → the municipal_rights_review gate and
    the non-edict question — municipal publication alone can never satisfy a
    lane (SRC-012 stays undetermined — outside the prepared-flip batch)."""
    e = by_id["SRC-012"]
    assert acq.Gate.MUNICIPAL_RIGHTS_REVIEW in e.gates
    qs = " ".join(e.missing_questions)
    assert "not auto-CC0" in qs
    # the flag alone never marks a lane decided
    decided_flags = [lr.decision == LaneDecision.DECIDED for _, lr in e.passport.rights.lanes()]
    assert not any(decided_flags)


def test_screening_required_flags_generate_preflight_gate_and_questions(by_id):
    for cid in ("SRC-024", "SRC-025", "SRC-027"):
        e = by_id[cid]
        assert e.passport.preflight.flags
        qs = " ".join(e.missing_questions).lower()
        assert "excluded category" in qs


def test_decided_lanes_require_a_recorded_disposition(by_id):
    """A lane cannot be decided without citing the recorded review — the
    queue can only cite a disposition, never mint one."""
    p = by_id["SRC-001"].passport
    fake = LaneRecord(decision=LaneDecision.DECIDED)  # no ref/by/date/basis
    bad = _mutate(p, rights=replace(p.rights, document_bytes=fake))
    problems = bad.rights.problems()
    assert any("decision_ref" in m for m in problems)
    assert any("decided_by" in m for m in problems)
    assert any("decision date" in m for m in problems)
    assert any("basis" in m for m in problems)


# --------------------------------------------------------------------------- #
# Score model — versioned, explainable, honest about unknowns                 #
# --------------------------------------------------------------------------- #


def test_score_matches_the_versioned_model(by_id):
    """acq-score/1 = 3G+3R+2I+2U+T+J−2E−2A−2S, and the contribution table
    explains every point."""
    e = by_id["SRC-002"]
    v = e.passport.dimensions.values
    expected = (
        3 * v["G"]
        + 3 * v["R"]
        + 2 * v["I"]
        + 2 * v["U"]
        + v["T"]
        + v["J"]
        - 2 * v["E"]
        - 2 * v["A"]
        - 2 * v["S"]
    )
    assert e.score_result.value == expected
    assert sum(e.score_result.contributions.values()) == expected
    for d in acq.DIMENSIONS:
        assert e.score_result.contributions[d] == acq.DIMENSION_WEIGHTS[d] * v[d]


def test_unknown_dimensions_stay_unknown(by_id):
    p = by_id["SRC-001"].passport
    unknown = _mutate(
        p,
        dimensions=replace(p.dimensions, values={**p.dimensions.values, "E": None}),
    )
    result = score(unknown.dimensions)
    assert result.value is None
    assert result.unscored_dimensions == ("E",)
    # contributions still show the computed parts (E contributes 0 but is
    # named unscored — never silently defaulted)
    assert "E" in result.contributions


def test_diff_assessments_explains_a_score_change(by_id):
    p = by_id["SRC-001"].passport
    a = p.dimensions
    b = replace(a, version="acq-review/1", values={**a.values, "R": 1, "A": 0})
    deltas = diff_assessments(a, b)
    by_dim = {d.dimension: d for d in deltas}
    assert set(by_dim) == {"R", "A"}
    assert by_dim["R"].delta == -6  # weight +3 × (1−3)
    assert by_dim["A"].delta == 4  # weight −2 × (0−2)
    assert score(a).value + sum(d.delta for d in deltas) == score(b).value


def test_invalid_dimensions_fail(by_id):
    p = by_id["SRC-001"].passport
    for bad_vals in (
        {**p.dimensions.values, "G": 4},
        {**p.dimensions.values, "S": -1},
    ):
        bad = replace(p.dimensions, values=bad_vals)
        assert bad.problems()
        with pytest.raises(acq.AcquisitionQueueError):
            score(bad)
    missing_key = dict(p.dimensions.values)
    del missing_key["G"]
    assert replace(p.dimensions, values=missing_key).problems()


def test_rank_is_deterministic_and_score_ordered(entries):
    ranked = rank_entries(entries)
    vals = [
        (e.score_result.value if e.score_result.value is not None else -(10**9)) for e in ranked
    ]
    assert vals == sorted(vals, reverse=True)
    assert ranked == rank_entries(rank_entries(entries))  # stable


def test_score_is_a_utility_signal_not_a_probability(entries):
    """The report tells the reader the ordinal score is a prioritisation aid
    — and blocked/unscored rows stay visible."""
    report = queue_report(entries)
    assert "approves nothing" in report
    assert acq.SCORING_VERSION in report


# --------------------------------------------------------------------------- #
# Uncertainty + cost honesty                                                  #
# --------------------------------------------------------------------------- #


def test_uncertainty_tracks_the_recorded_review_depth(by_id):
    e27 = by_id["SRC-027"]
    assert "bytes never fetched" in e27.uncertainty
    e11 = by_id["SRC-011"]  # primary_search_excerpts
    assert "search-result excerpts only" in e11.uncertainty
    for e in (e27, e11):
        assert e.passport.discovery.review_status in e.uncertainty


def test_cost_keeps_estimated_and_measured_separate(entries):
    for e in entries:
        c = e.passport.cost
        assert c.estimated_effort  # the research band
        assert c.measured_minutes is None  # no approved run → nothing measured
        assert not c.problems()


def test_measured_cost_requires_a_basis(by_id):
    p = by_id["SRC-001"].passport
    bad = _mutate(p, cost=CostRecord(estimated_effort="M", measured_minutes=45))
    assert any("measured_basis" in m for m in bad.problems())
    good = _mutate(
        p,
        cost=CostRecord(
            estimated_effort="M",
            measured_minutes=45,
            measured_basis="approved run 2026-09-30",
        ),
    )
    assert not good.problems()


# --------------------------------------------------------------------------- #
# Missing questions + review packets                                          #
# --------------------------------------------------------------------------- #


def test_missing_questions_cover_every_open_lane(by_id):
    e = by_id["SRC-012"]  # undetermined — outside the prepared-flip batch
    qs = e.missing_questions
    assert len(qs) >= 4
    joined = " ".join(qs)
    assert "capture and retention" in joined  # document_bytes
    assert "factual fields extracted" in joined  # fact_extraction
    assert "licence compartment" in joined  # derived_publication
    assert "not auto-CC0" in joined  # municipal flag
    assert e.passport.rights_access_unknowns in joined  # research unknown verbatim


def test_decided_lanes_close_their_question(by_id):
    p = by_id["SRC-001"].passport
    decided = _mutate(p, rights=_all_decided(p.rights))
    qs = " ".join(missing_questions(decided, join_candidate(decided, dispositions={})))
    assert "capture and retention" not in qs  # the decided lane's question is answered
    assert "not auto-CC0" in qs  # the municipal question persists until answered


def test_related_sources_generate_dedupe_questions(by_id):
    e = by_id["SRC-012"]  # related → ccops_seattle, camreg_seattle_wa
    qs = " ".join(e.missing_questions)
    assert "ccops_seattle" in qs and "net-new remainder" in qs


def test_review_packet_carries_every_required_section(by_id):
    for cid in ("SRC-001", "SRC-010", "SRC-027"):
        packet = review_packet(by_id[cid])
        for needle in (
            "authorizes nothing",
            "## Passport",
            "Named gap",
            "Content window",
            "## Registry + disposition join",
            "## Lineage",
            "## Rights (three separate lanes)",
            "## Part VIII preflight",
            "## Score (versioned inputs)",
            "## Gates",
            "## Cost + uncertainty",
            "## Missing questions",
        ):
            assert needle in packet, f"{cid} packet missing {needle!r}"


def test_packet_shows_recorded_dispositions_for_p31_links(by_id):
    packet = review_packet(by_id["SRC-023"])
    assert "recorded disposition" in packet
    assert "P31.12/.13-owned" in packet


def test_blocked_and_refused_rows_stay_visible(by_id):
    # synthetic: refuse a duplicate and block a sensitive candidate
    p = by_id["SRC-013"].passport
    dup = _mutate(
        p,
        candidate_id="SRC-997",
        discovery=replace(p.discovery, primary_url=by_id["SRC-013"].passport.discovery.primary_url),
    )
    from tasks.acquisition import QueueEntry

    join = join_candidate(dup, dispositions={}, peers=[p])
    e = QueueEntry(
        passport=dup,
        join=join,
        score_result=score(dup.dimensions),
        gates=gates_for(dup, join),
        disposition=disposition_for(dup, join, gates_for(dup, join)),
        kind="new_target",
        uncertainty="synthetic",
        missing_questions=("q",),
    )
    assert e.disposition == QueueDisposition.REFUSED_DUPLICATE
    assert "duplicate" in " ".join(g.value for g in e.gates)


# --------------------------------------------------------------------------- #
# Check invariants + the JSON projection                                      #
# --------------------------------------------------------------------------- #


def test_check_queue_zero_violations_on_seed(entries):
    assert check_queue(entries) == []


def test_check_queue_catches_a_decision_without_reference(by_id):
    p = by_id["SRC-001"].passport
    fake_lane = LaneRecord(
        decision=LaneDecision.DECIDED, decided_by="r", decided_on=date(2026, 9, 26), basis="b"
    )
    forged = _mutate(p, rights=replace(p.rights, document_bytes=fake_lane))
    e = replace(by_id["SRC-001"], passport=forged)
    violations = check_queue([e])
    assert any("decision_ref" in v for v in violations)


def test_json_projection_is_machine_readable(entries):
    out = acq.entries_as_json(entries)
    assert len(out) == 27
    json.dumps(out)  # serializable
    by = {r["candidate_id"]: r for r in out}
    assert by["SRC-027"]["independent_yield"] is False
    assert by["SRC-027"]["score"]["contributions"]["I"] == 0
    assert "sensitive_rejected" in by["SRC-027"]["gates"]
    assert by["SRC-010"]["relation"] == "existing_unpermitted"
    assert by["SRC-010"]["kind"] == "improvement"
    for row in out:
        assert row["cost"]["measured_minutes"] is None
        assert row["cost"]["estimated_effort"]
        assert row["missing_questions"]
        assert row["uncertainty"]


# --------------------------------------------------------------------------- #
# The CLI                                                                      #
# --------------------------------------------------------------------------- #


def test_cli_check_and_queue_and_explain(capsys, tmp_path):
    assert tasks_cli_main(["acquisition", "check"]) == 0
    assert "0 violations" in capsys.readouterr().out

    assert tasks_cli_main(["acquisition", "queue", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 27

    assert tasks_cli_main(["acquisition", "explain", "--candidate", "SRC-027"]) == 0
    out = capsys.readouterr().out
    assert "contribution=" in out and "sensitive_rejected" in out


def test_cli_packet_writes_review_inputs(tmp_path, capsys):
    assert (
        tasks_cli_main(["acquisition", "packet", "--candidate", "SRC-001", "--out", str(tmp_path)])
        == 0
    )
    packet = (tmp_path / "SRC-001.md").read_text()
    assert "authorizes nothing" in packet
    assert "Missing questions" in packet


def test_cli_explain_other_diffs_versions(tmp_path, capsys):
    """An alternate queue file under a new assessment version diffs the
    changed dimensions with weighted deltas — score changes are explained
    from the versioned inputs, never a black box."""
    text = (REPO_ROOT / "tasks/src/tasks/data/acquisition_queue.toml").read_text()
    text = text.replace('version = "acq-seed/1"', 'version = "acq-review/2"')
    lo, hi = text.index("[candidates.SRC-001]"), text.index("[candidates.SRC-002]")
    seg = text[lo:hi].replace("R = 3,", "R = 1,", 1)
    alt = tmp_path / "queue_v2.toml"
    alt.write_text(text[:lo] + seg + text[hi:])
    assert (
        tasks_cli_main(["acquisition", "explain", "--candidate", "SRC-001", "--other", str(alt)])
        == 0
    )
    out = capsys.readouterr().out
    assert "acq-seed/1 → acq-review/2" in out
    assert "R: 3 → 1" in out
    assert "Δ score -6" in out
