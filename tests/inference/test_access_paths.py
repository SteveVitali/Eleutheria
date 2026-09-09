# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Access-path closure — the §30.2 bound (SIG-RECON-048/049/050, SIG-ONTO-042).

The three P12.2 acceptance criteria, exercised here:

* the three §12.2 access edge types are never merged, collapsed, or defaulted into
  one another (SIG-ONTO-042) — closure composes only ``configured_access`` /
  ``federates_search_to`` and preserves every hop's kind;
* closure respects hop limits, scope, and non-composition rules — ``observed_use``
  and query-direction ``distributes_list_to`` do not compose, scope may not broaden,
  an expired hop yields a historical (labelled) path, and confidence is the path
  minimum (SIG-RECON-049);
* paths beyond the published hop threshold are labelled speculative and excluded from
  headline figures, and every published path carries its full hop list with per-hop
  evidence (SIG-RECON-050).
"""

from __future__ import annotations

from datetime import date

import pytest
from inference.access_paths import (
    ACCESS_KINDS,
    COMPOSABLE_LABELS,
    CONFIDENCE_ORDER,
    DERIVATION_RULE,
    HISTORICAL,
    MAX_PATH_HOPS,
    NON_COMPOSING_ACCESS_KINDS,
    SPECULATIVE_HOP_THRESHOLD,
    AccessEdge,
    AccessPath,
    close_access_paths,
)

_AS_OF = date(2026, 1, 1)


def edge(
    frm: str,
    to: str,
    label: str = "configured_access",
    *,
    scope: str = "partner",
    confidence: str = "probable",
    valid_from: date | None = None,
    valid_to: date | None = None,
    valid_from_kind: str = "unknown",
    valid_to_kind: str = "ongoing",
) -> AccessEdge:
    return AccessEdge(
        from_org=frm,
        to_org=to,
        edge_label=label,
        scope=scope,
        evidence=(f"claim:{frm}->{to}",),
        confidence=confidence,
        valid_from=valid_from,
        valid_to=valid_to,
        valid_from_kind=valid_from_kind,
        valid_to_kind=valid_to_kind,
        edge_id=f"edge:{frm}{to}",
    )


def _targets(closure, **kw) -> set[str]:
    return set(closure.reachable(**kw))


# --- AC1: the three edge types are never merged --------------------------------


def test_the_three_access_kinds_are_exactly_the_canonical_set() -> None:
    # SIG-ONTO-042: closure reuses the P08.2 three-kind vocabulary, never a fourth or
    # a merged pseudo-kind.
    assert ACCESS_KINDS == ("configured_access", "observed_use", "declared_policy")
    assert len(set(ACCESS_KINDS)) == 3


def test_only_configured_access_and_federation_compose() -> None:
    # SIG-RECON-049 #1: exactly two labels compose; the other two sharing kinds do not.
    assert COMPOSABLE_LABELS == frozenset({"configured_access", "federates_search_to"})
    assert NON_COMPOSING_ACCESS_KINDS == frozenset({"observed_use", "declared_policy"})
    assert "configured_access" in COMPOSABLE_LABELS
    for kind in ("observed_use", "declared_policy"):
        assert kind not in COMPOSABLE_LABELS


def test_closure_never_relabels_a_hop_kind() -> None:
    # SIG-ONTO-042: a hop keeps the access_kind/edge_label it was given — closure does
    # not default observed/declared into configured, nor collapse the three into one.
    edges = [
        edge("A", "B", "configured_access"),
        edge("B", "C", "federates_search_to"),
    ]
    closure = close_access_paths(edges, source="A", as_of=_AS_OF, target="C")
    (path,) = closure.paths
    labels = [h.edge_label for h in path.hops]
    assert labels == ["configured_access", "federates_search_to"]


def test_access_edge_kinds_stay_distinct_and_are_not_defaulted() -> None:
    # SIG-ONTO-042: there is no operation that turns one kind into another. Each of the
    # three kinds keeps its own identity on the edge object.
    kinds = {
        edge("A", "B", "configured_access").edge_label,
        edge("A", "B", "observed_use").edge_label,
        edge("A", "B", "declared_policy").edge_label,
    }
    assert kinds == {"configured_access", "observed_use", "declared_policy"}


# --- AC2: closure respects hop limits, scope, and non-composition --------------


def test_observed_use_does_not_compose() -> None:
    # SIG-RECON-049 #1: A used B and B used C does NOT mean A can reach C.
    edges = [
        edge("A", "B", "configured_access"),
        edge("B", "C", "observed_use"),
    ]
    closure = close_access_paths(edges, source="A", as_of=_AS_OF)
    assert _targets(closure) == {"B"}  # C is unreachable through an observed_use hop


def test_a_standalone_observed_use_chain_reaches_nothing_by_composition() -> None:
    # SIG-RECON-049 #1: an all-observed_use graph composes into no derived reach.
    edges = [edge("A", "B", "observed_use"), edge("B", "C", "observed_use")]
    closure = close_access_paths(edges, source="A", as_of=_AS_OF)
    assert closure.paths == ()


def test_distributes_list_to_does_not_compose_in_the_query_direction() -> None:
    # SIG-RECON-049 #2: a hotlist flowing outward creates no inbound search path.
    edges = [
        edge("A", "B", "configured_access"),
        edge("B", "C", "distributes_list_to"),
    ]
    closure = close_access_paths(edges, source="A", as_of=_AS_OF)
    assert _targets(closure) == {"B"}


def test_federation_composes_with_configured_access() -> None:
    # SIG-RECON-049 #1: the two composable labels chain together.
    edges = [
        edge("A", "B", "federates_search_to"),
        edge("B", "C", "configured_access"),
    ]
    closure = close_access_paths(edges, source="A", as_of=_AS_OF, target="C")
    assert len(closure.paths) == 1
    assert closure.paths[0].orgs == ("A", "B", "C")


def test_scope_may_not_broaden_along_a_chain() -> None:
    # SIG-RECON-049 #3: a partner-scoped edge does not chain into a national-scoped one.
    edges = [
        edge("A", "B", "configured_access", scope="partner"),
        edge("B", "C", "configured_access", scope="national"),
    ]
    closure = close_access_paths(edges, source="A", as_of=_AS_OF)
    assert _targets(closure) == {"B"}  # partner -> national is refused


def test_scope_may_narrow_along_a_chain_and_path_scope_is_the_narrowest() -> None:
    # The converse is allowed: a national edge may chain into a partner edge, and the
    # path reaches only as broadly as its tightest hop.
    edges = [
        edge("A", "B", "configured_access", scope="national"),
        edge("B", "C", "configured_access", scope="partner"),
    ]
    closure = close_access_paths(edges, source="A", as_of=_AS_OF, target="C")
    (path,) = closure.paths
    assert path.scope == "partner"


def test_expired_hop_yields_a_historical_labelled_path() -> None:
    # SIG-RECON-049 #4: a path through an expired edge is historical, not live — and it
    # is labelled, never silently dropped.
    edges = [
        edge("A", "B", "configured_access"),
        edge(
            "B",
            "C",
            "configured_access",
            valid_to=date(2020, 1, 1),
            valid_to_kind="known",
        ),
    ]
    closure = close_access_paths(edges, source="A", as_of=_AS_OF, target="C")
    (path,) = closure.paths
    assert path.temporal_status == HISTORICAL
    assert path not in closure.headline_paths
    assert path in closure.historical_paths


def test_a_future_hop_is_not_asserted_as_of_the_query_time() -> None:
    # SIG-RECON-049 #4: closure never asserts a chain through an edge that has not begun.
    edges = [
        edge("A", "B", "configured_access"),
        edge(
            "B",
            "C",
            "configured_access",
            valid_from=date(2030, 1, 1),
            valid_from_kind="known",
        ),
    ]
    closure = close_access_paths(edges, source="A", as_of=_AS_OF)
    assert _targets(closure) == {"B"}


def test_single_snapshot_edge_is_always_valid() -> None:
    # SIG-ONTO-044: a single-snapshot sharing edge (unknown start / ongoing end) is
    # valid at any as-of; its start is never inferred from first observation.
    e = edge("A", "B", "configured_access")  # defaults: unknown / ongoing
    assert e.temporal_status(date(1990, 1, 1)) == "valid"
    assert e.temporal_status(date(2050, 1, 1)) == "valid"


def test_confidence_is_the_minimum_over_the_path_never_the_average() -> None:
    # SIG-RECON-049 #6: a chain is as strong as its weakest hop.
    edges = [
        edge("A", "B", "configured_access", confidence="certain"),
        edge("B", "C", "configured_access", confidence="possible"),
        edge("C", "D", "configured_access", confidence="probable"),
    ]
    closure = close_access_paths(edges, source="A", as_of=_AS_OF, target="D")
    (path,) = closure.paths
    assert path.confidence == "possible"  # the weakest hop, not the mean


def test_closure_produces_only_simple_paths_no_loops() -> None:
    edges = [
        edge("A", "B", "configured_access"),
        edge("B", "A", "configured_access"),
        edge("B", "C", "configured_access"),
    ]
    closure = close_access_paths(edges, source="A", as_of=_AS_OF)
    for path in closure.paths:
        assert len(set(path.orgs)) == len(path.orgs)  # no org repeats


def test_path_length_is_capped() -> None:
    # SIG-RECON-049 #5: enumeration is bounded — a long line graph never yields a path
    # longer than MAX_PATH_HOPS.
    orgs = [f"O{i}" for i in range(MAX_PATH_HOPS + 5)]
    edges = [edge(a, b, "configured_access") for a, b in zip(orgs, orgs[1:], strict=False)]
    closure = close_access_paths(edges, source=orgs[0], as_of=_AS_OF, max_hops=MAX_PATH_HOPS)
    assert closure.paths  # some paths found
    assert max(p.hop_count for p in closure.paths) == MAX_PATH_HOPS


# --- AC3: speculative labelling + full hop list with evidence ------------------


def _line(n: int) -> list[AccessEdge]:
    orgs = [f"O{i}" for i in range(n + 1)]
    return [edge(a, b, "configured_access") for a, b in zip(orgs, orgs[1:], strict=False)]


def test_paths_within_threshold_are_headline_and_not_speculative() -> None:
    closure = close_access_paths(_line(SPECULATIVE_HOP_THRESHOLD), source="O0", as_of=_AS_OF)
    at_threshold = next(p for p in closure.paths if p.hop_count == SPECULATIVE_HOP_THRESHOLD)
    assert not at_threshold.speculative
    assert at_threshold.is_headline


def test_paths_beyond_threshold_are_speculative_and_excluded_from_headlines() -> None:
    # SIG-RECON-050: beyond the published hop count, the path is speculative and MUST
    # NOT count as a shared-data relationship.
    over = SPECULATIVE_HOP_THRESHOLD + 1
    closure = close_access_paths(_line(over), source="O0", as_of=_AS_OF)
    longest = max(closure.paths, key=lambda p: p.hop_count)
    assert longest.hop_count == over
    assert longest.speculative
    assert not longest.is_headline
    assert longest in closure.speculative_paths
    # The far endpoint is reachable "at all" but NOT in the headline reachable set.
    assert longest.target in _targets(closure)
    assert longest.target not in _targets(closure, headline_only=True)


def test_every_published_path_carries_its_full_hop_list_with_per_hop_evidence() -> None:
    # SIG-RECON-049 #5 / SIG-UI-025: no unexplained "A can reach B".
    edges = [
        edge("A", "B", "configured_access"),
        edge("B", "C", "federates_search_to"),
    ]
    closure = close_access_paths(edges, source="A", as_of=_AS_OF, target="C")
    (path,) = closure.paths
    view = path.public_view()
    assert len(view["hops"]) == path.hop_count == 2
    for hop in view["hops"]:
        assert hop["evidence"]  # every hop shows its evidence
        assert hop["from_org"] and hop["to_org"] and hop["edge_label"]


def test_a_hop_without_evidence_is_rejected() -> None:
    # §3.1 / SIG-RECON-049 #5: an unexplained edge is forbidden at construction.
    with pytest.raises(ValueError, match="evidence"):
        AccessEdge(
            from_org="A",
            to_org="B",
            edge_label="configured_access",
            scope="partner",
            evidence=(),
        )


# --- L4 inference shape (SIG-RECON-047) ----------------------------------------


def test_path_becomes_a_labelled_l4_inference_never_an_observation() -> None:
    edges = [
        edge("A", "B", "configured_access", confidence="certain"),
        edge("B", "C", "configured_access", confidence="probable"),
    ]
    closure = close_access_paths(edges, source="A", as_of=_AS_OF, target="C")
    inf = closure.paths[0].to_inference()
    assert inf.layer == "L4"
    assert inf.is_observation is False
    assert inf.pushable_to_osm is False
    assert inf.derivation_rule == DERIVATION_RULE
    assert inf.rule_version
    assert inf.confidence == "probable"  # path minimum
    # input_claim_ids are the union of the hops' evidence, in order.
    assert inf.input_claim_ids == ("claim:A->B", "claim:B->C")
    assert inf.value["hops"] and len(inf.value["hops"]) == 2


def test_inference_input_claim_ids_dedupe_shared_evidence() -> None:
    shared = AccessEdge(
        from_org="A",
        to_org="B",
        edge_label="configured_access",
        scope="partner",
        evidence=("claim:x", "claim:y"),
    )
    second = AccessEdge(
        from_org="B",
        to_org="C",
        edge_label="configured_access",
        scope="partner",
        evidence=("claim:y", "claim:z"),
    )
    path = AccessPath(hops=(shared, second), as_of=_AS_OF)
    assert path.input_claim_ids == ("claim:x", "claim:y", "claim:z")


# --- construction guards -------------------------------------------------------


def test_confidence_order_is_least_to_most() -> None:
    assert CONFIDENCE_ORDER == ("possible", "probable", "certain")


def test_unknown_scope_and_confidence_are_rejected() -> None:
    with pytest.raises(ValueError, match="scope"):
        edge("A", "B", scope="galactic")
    with pytest.raises(ValueError, match="confidence"):
        edge("A", "B", confidence="certainish")


def test_self_loop_edge_is_rejected() -> None:
    with pytest.raises(ValueError, match="self-loop"):
        AccessEdge(
            from_org="A",
            to_org="A",
            edge_label="configured_access",
            scope="own",
            evidence=("c",),
        )


def test_non_contiguous_path_is_rejected() -> None:
    with pytest.raises(ValueError, match="contiguous"):
        AccessPath(hops=(edge("A", "B"), edge("C", "D")), as_of=_AS_OF)


def test_target_filter_returns_only_paths_to_that_target() -> None:
    edges = [
        edge("A", "B", "configured_access"),
        edge("B", "C", "configured_access"),
        edge("B", "D", "configured_access"),
    ]
    closure = close_access_paths(edges, source="A", as_of=_AS_OF, target="D")
    assert {p.target for p in closure.paths} == {"D"}
