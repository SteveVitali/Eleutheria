# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""ER as a distinct, re-runnable pipeline stage (§27, SIG-RECON-001/002) and public
identifier stability across cluster change (SIG-IDENT-032): the run record, the
six-tier composition, re-clustering under a new ruleset without destroying the prior
clustering, and routing merges/splits through the stability contract."""

from __future__ import annotations

from datetime import date

import pytest
from resolution.cascade import Candidate
from resolution.er_run import (
    ERRun,
    cluster_same_as,
    recluster,
    run_entity_resolution,
    stabilise_cluster_change,
    stage_between,
)
from resolution.identity import identifier_set
from resolution.public_id import PublicIdRegistry
from resolution.temporal_identity import OrganizationRelationType


def _run(ruleset_version: str = "r1", run_id: str = "run-1") -> ERRun:
    return ERRun(
        resolver_version="0.0.0",
        model_version="1",
        ruleset_version=ruleset_version,
        code_commit="deadbeef",
        input_digests=("sha256:abc",),
        run_id=run_id,
    )


def _candidates() -> list[Candidate]:
    # A tier-0 auto-write pair (shared ORI); a Springfield collision pair that the
    # deterministic cascade refuses (tier 2 collision) and hands to the probabilistic
    # tier; and an isolated vendor with no match.
    return [
        Candidate(
            "A1",
            "us.le.sheriff",
            "Travis County Sheriff's Office",
            "TX",
            identifiers=identifier_set([("us.fbi.ori", "TX2270000")]),
        ),
        Candidate(
            "A2",
            "us.le.sheriff",
            "Travis County Sheriff's Department",
            "TX",
            identifiers=identifier_set([("us.fbi.ori", "TX2270000")]),
        ),
        Candidate("C1", "us.le.municipal_police", "Springfield Police Department", "IL"),
        Candidate("C2", "us.le.municipal_police", "Springfield Police Department", "IL"),
        Candidate("D1", "private.company", "Zeta Surveillance Systems", "NV"),
    ]


# --- SIG-RECON-001: the run record + the distinct stage -----------------------


def test_stage_runs_between_normalize_and_load() -> None:
    assert stage_between() == ("normalize", "load")


def test_run_record_enforces_deterministic_environment() -> None:
    with pytest.raises(ValueError, match="LC_ALL"):
        ERRun(
            resolver_version="0.0.0",
            model_version="1",
            ruleset_version="r1",
            code_commit="x",
            environment={"TZ": "UTC"},  # missing LC_ALL=C
        )


def test_run_record_row_has_versions_and_status() -> None:
    row = _run().to_row()
    assert row["ruleset_version"] == "r1"
    assert row["model_version"] == "1"
    assert row["run_kind"] == "entity_resolution"
    assert row["status"] == "running"


def test_completed_and_rolled_back_status_transitions() -> None:
    run = _run()
    assert run.completed().status == "completed"
    assert run.rolled_back().status == "rolled_back"


# --- SIG-IDENT-020: the six-tier composition ----------------------------------


def test_composition_auto_writes_deterministic_and_proposes_probabilistic() -> None:
    result = run_entity_resolution(_candidates(), run=_run())
    # deterministic tier-0 auto-write on the shared-ORI pair
    auto_ids = {frozenset((m.left, m.right)) for m in result.auto_writes}
    assert frozenset(("A1", "A2")) in auto_ids
    assert all(m.disposition == "auto_write" for m in result.auto_writes)
    # the Springfield collision pair is PROPOSED, never auto-written
    proposal_ids = {frozenset((m.left, m.right)) for m in result.proposals}
    assert frozenset(("C1", "C2")) in proposal_ids
    assert all(m.disposition == "review" for m in result.proposals)


def test_auto_written_pairs_are_never_also_proposed() -> None:
    result = run_entity_resolution(_candidates(), run=_run())
    auto = {frozenset((m.left, m.right)) for m in result.auto_writes}
    proposed = {frozenset((m.left, m.right)) for m in result.proposals}
    assert auto.isdisjoint(proposed)


def test_auto_write_pair_is_clustered_but_proposed_pair_is_not() -> None:
    result = run_entity_resolution(_candidates(), run=_run())
    assert result.clusters["A1"] == result.clusters["A2"]  # auto-write clusters
    assert result.clusters["C1"] != result.clusters["C2"]  # PROPOSED does not cluster
    assert result.run.status == "completed"


def test_report_records_blocking_sizes_and_passes_gate() -> None:
    result = run_entity_resolution(_candidates(), run=_run())
    assert result.report.blocking_sizes  # every rule sized (SIG-IDENT-023)
    assert result.report.blocking_ok


# --- same_as assertions -------------------------------------------------------


def test_cluster_same_as_emits_star_relations() -> None:
    result = run_entity_resolution(_candidates(), run=_run())
    relations = cluster_same_as(result, dated=date(2026, 1, 1))
    same_as = [r for r in relations if {r.from_entity, r.to_entity} == {"A1", "A2"}]
    assert len(same_as) == 1
    assert same_as[0].relation_type is OrganizationRelationType.SAME_AS


# --- SIG-RECON-002: re-runnable without destroying prior clustering -----------


def test_rerun_requires_a_new_ruleset_version() -> None:
    with pytest.raises(ValueError, match="new ruleset version"):
        _run(ruleset_version="r1").rerun(ruleset_version="r1")


def test_rerun_chains_to_previous_and_flags_rerun() -> None:
    new = _run(ruleset_version="r1", run_id="run-1").rerun(ruleset_version="r2", run_id="run-2")
    assert new.is_rerun is True
    assert new.previous_run_id == "run-1"
    assert new.ruleset_version == "r2"


def test_recluster_produces_new_run_without_touching_the_prior_result() -> None:
    candidates = _candidates()
    first = run_entity_resolution(candidates, run=_run(ruleset_version="r1", run_id="run-1"))
    first_same_as = cluster_same_as(first, dated=date(2026, 1, 1))

    second = recluster(first, candidates, new_ruleset_version="r2", run_id="run-2")
    assert second.run.is_rerun and second.run.ruleset_version == "r2"
    assert second.run.previous_run_id == "run-1"
    # the prior run's assertions are untouched (append-only history)
    assert cluster_same_as(first, dated=date(2026, 1, 1)) == first_same_as
    # the re-run still resolves the deterministic cluster
    assert second.clusters["A1"] == second.clusters["A2"]


# --- SIG-IDENT-032: stable public identifiers across cluster change -----------


def test_merge_preserves_survivor_and_redirects_the_retired_id() -> None:
    reg = PublicIdRegistry()
    reg.register("sig:organization:aaa")
    reg.register("sig:organization:bbb")
    events = stabilise_cluster_change(
        reg,
        before={"e1": "sig:organization:aaa", "e2": "sig:organization:bbb"},
        after={"e1": "merged", "e2": "merged"},
        dated=date(2026, 6, 1),
    )
    assert len(events) == 1 and events[0].event_type == "merge"
    # survivor (smallest id) stays live; the other redirects to it — never reassigned
    assert reg.resolve("sig:organization:aaa").status == "active"
    redirect = reg.resolve("sig:organization:bbb")
    assert redirect.status == "redirect" and redirect.target == "sig:organization:aaa"


def test_split_tombstones_source_into_minted_successors() -> None:
    reg = PublicIdRegistry()
    reg.register("sig:organization:aaa")
    counter = iter(range(100))
    events = stabilise_cluster_change(
        reg,
        before={"e1": "sig:organization:aaa", "e2": "sig:organization:aaa"},
        after={"e1": "g1", "e2": "g2"},
        dated=date(2026, 6, 1),
        mint_id=lambda: f"sig:organization:s{next(counter)}",
    )
    assert len(events) == 1 and events[0].event_type == "split"
    resolution = reg.resolve("sig:organization:aaa")
    assert resolution.status == "split"
    assert len(resolution.targets) == 2


def test_split_without_a_minter_is_refused() -> None:
    reg = PublicIdRegistry()
    reg.register("sig:organization:aaa")
    with pytest.raises(ValueError, match="mint_id"):
        stabilise_cluster_change(
            reg,
            before={"e1": "sig:organization:aaa", "e2": "sig:organization:aaa"},
            after={"e1": "g1", "e2": "g2"},
            dated=date(2026, 6, 1),
        )


def test_unchanged_shape_produces_no_events() -> None:
    reg = PublicIdRegistry()
    reg.register("sig:organization:aaa")
    events = stabilise_cluster_change(
        reg,
        before={"e1": "sig:organization:aaa", "e2": "sig:organization:aaa"},
        after={"e1": "same", "e2": "same"},
        dated=date(2026, 6, 1),
    )
    assert events == []
    assert reg.resolve("sig:organization:aaa").status == "active"
