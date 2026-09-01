# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""J-1 — the journalist's traversal, executed end to end (SIG-CHART-009/010).

The acceptance query for §2.2 J-1 / Appendix D, run against the P06.1 slice
fixture (Oklahoma City / OKCPD Flock ALPR). It is the single most demanding
integration test in the spec: it crosses independent source families and
disagreeing quantity claims, and every material fact it surfaces MUST resolve to
a document at a locator with a coverage/incompleteness statement.
"""

from __future__ import annotations

from acceptance import okc_slice as slice_mod
from exports.dossier import render_json, render_print_html
from reconcile.model import (
    POLICY_CONFIGURATION_DIVERGENCE,
    PREDICATE_CONFLATION,
    VALUE_DISAGREEMENT,
)

# The traversal §2.2 specifies, in order.
J1_ORDER = (
    "city",
    "police_agency",
    "deployment",
    "contract",
    "contracted_cameras",
    "mapped_devices",
    "sharing_relationships",
    "network_searches",
    "retention_settings",
    "policy",
    "related_litigation",
    "replacement_vendor",
)


def test_j1_executes_end_to_end() -> None:
    # AC1: J-1 executes end to end for the slice jurisdiction.
    graph = slice_mod.build_slice()
    hops = slice_mod.j1_traversal(graph)
    assert tuple(h.name for h in hops) == J1_ORDER
    # every hop lands on a concrete node
    for h in hops:
        assert h.node, f"hop {h.name} has no node"
    # the traversal crosses >= 3 independent source families (hardness precondition)
    families = {e.source_family for h in hops for e in h.evidence}
    assert len(families) >= 3, families


def test_every_material_fact_resolves_to_a_document_at_a_locator() -> None:
    # AC2 / SIG-CHART-010(a): each material fact carries resolvable evidence.
    graph = slice_mod.build_slice()
    facts = slice_mod.material_facts(graph)
    assert facts, "no material facts produced"
    for label, ev in facts:
        assert ev.resolves_to_document(), f"{label} does not resolve to a document at a locator"
        assert ev.stable_locator.startswith("http"), label
        assert "text_span" in ev.locator or "quote" in ev.locator, label


def test_at_least_one_genuine_contradiction_rendered_without_collapse() -> None:
    # AC3: a genuine contradiction is detected AND rendered without collapse.
    graph = slice_mod.build_slice()
    types = {c.contradiction_type for c in graph.contradictions}
    assert VALUE_DISAGREEMENT in types
    assert POLICY_CONFIGURATION_DIVERGENCE in types

    # rendered without collapse: both sides survive into the dossier API + print.
    dossier = slice_mod.build_dossier(graph)
    js = render_json(dossier)
    events = next(s for s in js["sections"] if s["id"] == "accountability_events")
    rendered = [r for r in events["rows"] if str(r["label"]).startswith("Contradiction:")]
    assert any("policy_configuration_divergence" in r["label"] for r in rendered)

    # the claimed-count disagreement retains BOTH figures (190 and 299), collapsing neither.
    disagreement = next(
        c for c in graph.contradictions if c.contradiction_type == VALUE_DISAGREEMENT
    )
    assert set(disagreement.claim_values) == {190, 299}
    html = render_print_html(dossier)
    assert "190" in html and "299" in html


def test_predicate_conflation_fires_on_deliberate_conflation() -> None:
    # AC4: PREDICATE_CONFLATION fires when the distinct count bases are conflated.
    graph = slice_mod.build_slice()
    assert graph.conflation.contradiction_type == PREDICATE_CONFLATION
    assert set(graph.conflation.claim_values) == {90, 299}


def test_count_predicates_are_distinct_with_their_own_resolutions() -> None:
    # AC4 / SIG-RECON-026/029: distinct predicates, each with its own answer.
    graph = slice_mod.build_slice()
    res = graph.reconciliation.resolutions
    assert res["contracted"].value == 90
    assert res["active"].value == 90
    assert res["mapped"].value == 299
    assert res["mapped"].lower_bound is True  # SIG-RECON-027
    # no single true count is emitted (SIG-RECON-029)
    import pytest

    with pytest.raises(NotImplementedError):
        graph.reconciliation.true_count()


def test_result_carries_a_coverage_and_incompleteness_statement() -> None:
    # SIG-CHART-010(b) / SIG-UI-011/012: a coverage statement accompanies the result.
    graph = slice_mod.build_slice()
    dossier = slice_mod.build_dossier(graph)
    js = render_json(dossier)
    assert js["what_we_dont_know"], "result set must carry a 'what we don't know' statement"
    assert "unresearched field" in js["incompleteness_banner"]


def test_unresolved_deltas_become_research_tasks() -> None:
    # §29.1 / SIG-RECON-029: the deltas are the findings, emitted as tasks.
    graph = slice_mod.build_slice()
    rec = graph.reconciliation
    assert rec.tasks, "expected research tasks from the deltas/disagreements"
    # the active(90)-vs-mapped(299) surplus is the attribution finding
    d = next(
        d for d in rec.unresolved_deltas if (d.higher_basis, d.lower_basis) == ("active", "mapped")
    )
    assert d.delta == -209
    assert d.task in rec.tasks
