# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Entity resolution as a distinct, re-runnable pipeline stage (§27, SIG-RECON-001/002).

This module composes the six-tier cascade into a single ER run and gives that run the
operational shape §27 requires:

* **A distinct stage between ``normalize()`` and ``load()``** (SIG-RECON-001). An
  :class:`ERRun` is the run record — resolver/model/ruleset versions, code commit,
  input digests, a deterministic environment — analogous to the connectors'
  ``ingest_run``. Every proposal and auto-write points back to it, and it carries its
  own :class:`ERQualityReport` and a rollback status.
* **Re-runnable without destroying prior clustering** (SIG-RECON-002). :func:`recluster`
  runs again under a *new* ruleset version and emits *new* ``same_as`` assertions
  (:class:`resolution.temporal_identity.OrganizationRelation`); it never mutates the
  previous run's assertions — the history is append-only.
* **Stable public identifiers across cluster change** (SIG-IDENT-032). When a re-run
  changes cluster shape, :func:`stabilise_cluster_change` routes the merges and splits
  through :class:`resolution.public_id.PublicIdRegistry`, so a surviving identifier is
  preserved and a retired one becomes a redirect/tombstone — never silently reassigned.

The composition itself: deterministic tiers 0–3 (:func:`resolution.cascade.resolve`)
auto-write over sized-blocked candidate pairs; the fall-through pairs are scored by the
Splink matcher (:mod:`resolution.probabilistic`) and become tier-4/5 PROPOSED proposals.
Only auto-writes form clusters — a PROPOSED pair waits for review (P05.2) before it can
move an identifier (SIG-IDENT-020).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date

from .blocking import BlockingContext, blocked_pairs, load_rules
from .cascade import Candidate, CascadeContext, MatchResult, resolve
from .probabilistic import ProbabilisticMatch, ProbabilisticMatcher
from .public_id import MergeSplitEvent, PublicIdRegistry
from .quality_gates import (
    PRF,
    ClusterShapeAlert,
    ClusterShapeContext,
    DemotionDecision,
    cluster_shape_alerts,
    pair_key,
)
from .temporal_identity import OrganizationRelation, OrganizationRelationType

__all__ = [
    "ER_STAGE_NAME",
    "PIPELINE_PREDECESSOR",
    "PIPELINE_SUCCESSOR",
    "ERRun",
    "ERQualityReport",
    "ERResult",
    "stage_between",
    "run_entity_resolution",
    "cluster_same_as",
    "recluster",
    "stabilise_cluster_change",
]

# ER is the pipeline stage that sits strictly between normalize() and load() — the
# claim is normalised first, then resolved to an identity, then loaded (SIG-RECON-001).
ER_STAGE_NAME = "entity_resolution"
PIPELINE_PREDECESSOR = "normalize"
PIPELINE_SUCCESSOR = "load"

# The environment an ER run records, mirroring the connectors' deterministic ingest
# environment (LC_ALL=C / TZ=UTC) without taking a new inter-package dependency.
_REQUIRED_ENVIRONMENT = {"LC_ALL": "C", "TZ": "UTC"}


def _deterministic_environment(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(_REQUIRED_ENVIRONMENT)
    if extra:
        env.update(extra)
    return env


def stage_between() -> tuple[str, str]:
    """The stage ER runs between: ``("normalize", "load")`` (SIG-RECON-001)."""
    return (PIPELINE_PREDECESSOR, PIPELINE_SUCCESSOR)


@dataclass(frozen=True)
class ERRun:
    """The ER run record (SIG-RECON-001) — the reproducibility + rollback anchor.

    Versions are recorded so a re-run is distinguishable and a clustering can always be
    tied to the exact resolver, model, and ruleset that produced it. ``status`` moves
    ``running`` → ``completed`` (or ``rolled_back``); ``is_rerun``/``previous_run_id``
    chain a re-clustering to what it superseded (SIG-RECON-002).
    """

    resolver_version: str
    model_version: str
    ruleset_version: str
    code_commit: str
    input_digests: tuple[str, ...] = ()
    gold_set_version: str | None = None
    parameters: dict[str, object] = field(default_factory=dict)
    environment: dict[str, str] = field(default_factory=_deterministic_environment)
    run_kind: str = ER_STAGE_NAME
    run_id: str | None = None
    previous_run_id: str | None = None
    is_rerun: bool = False
    status: str = "running"

    def __post_init__(self) -> None:
        for key, expected in _REQUIRED_ENVIRONMENT.items():
            if self.environment.get(key) != expected:
                raise ValueError(
                    f"an ER run must record {key}={expected} (SIG-RECON-001), "
                    f"got {self.environment.get(key)!r}"
                )

    def to_row(self) -> dict[str, object]:
        return {
            "resolver_version": self.resolver_version,
            "model_version": self.model_version,
            "ruleset_version": self.ruleset_version,
            "code_commit": self.code_commit,
            "input_digests": list(self.input_digests),
            "gold_set_version": self.gold_set_version,
            "parameters": self.parameters,
            "environment": self.environment,
            "run_kind": self.run_kind,
            "run_id": self.run_id,
            "previous_run_id": self.previous_run_id,
            "is_rerun": self.is_rerun,
            "status": self.status,
        }

    def completed(self) -> ERRun:
        return replace(self, status="completed")

    def rolled_back(self) -> ERRun:
        """Mark the run rolled back — the SIG-RECON-001 rollback path."""
        return replace(self, status="rolled_back")

    def rerun(
        self, *, ruleset_version: str, code_commit: str | None = None, run_id: str | None = None
    ) -> ERRun:
        """A fresh run that supersedes this one under a NEW ruleset (SIG-RECON-002).

        The new run points back at this one (``previous_run_id``) and is flagged
        ``is_rerun``; a re-cluster MUST bump the ruleset version so its ``same_as``
        assertions are attributable to a distinct ruleset, never conflated with the
        prior run's.
        """
        if ruleset_version == self.ruleset_version:
            raise ValueError(
                "a re-run MUST use a new ruleset version so its clustering is "
                "attributable and does not overwrite the prior run (SIG-RECON-002)"
            )
        return replace(
            self,
            ruleset_version=ruleset_version,
            code_commit=code_commit if code_commit is not None else self.code_commit,
            run_id=run_id,
            previous_run_id=self.run_id,
            is_rerun=True,
            status="running",
        )


@dataclass(frozen=True)
class ERQualityReport:
    """The quality report a run carries (SIG-RECON-001, §14.7 gates).

    ``blocking_sizes`` proves every rule was sized (SIG-IDENT-023). ``cluster_alerts``
    are the shape alerts (SIG-IDENT-029). The gold-dependent fields
    (``tier_metrics``/``bcubed``/``demotions``/``kappa``) are populated by
    :func:`resolution.quality_gates` when a gold set is supplied (SIG-IDENT-028).
    """

    blocking_sizes: dict[str, int]
    cluster_alerts: tuple[ClusterShapeAlert, ...] = ()
    tier_metrics: dict[int, PRF] = field(default_factory=dict)
    bcubed: PRF | None = None
    demotions: tuple[DemotionDecision, ...] = ()
    kappa: float | None = None

    @property
    def blocking_ok(self) -> bool:
        """True iff every blocking rule was sized (i.e. the run passed the gate)."""
        return all(size >= 0 for size in self.blocking_sizes.values())

    @property
    def demoted_tiers(self) -> tuple[int, ...]:
        return tuple(d.tier for d in self.demotions if d.demoted)


@dataclass(frozen=True)
class ERResult:
    """The output of one ER run: auto-writes, PROPOSED proposals, clusters, report."""

    run: ERRun
    auto_writes: tuple[MatchResult, ...]
    proposals: tuple[ProbabilisticMatch, ...]
    clusters: dict[str, str]
    report: ERQualityReport


def _record_for(candidate: Candidate) -> dict[str, object]:
    """The matcher/blocking record derived from a deterministic-cascade candidate."""
    normalized = candidate.normalized_name
    first_token = normalized.split(" ", 1)[0] if normalized else ""
    return {
        "unique_id": candidate.entity_id,
        "normalized_name": normalized,
        "name_first_token": first_token,
        "state": candidate.state,
        "organization_class": candidate.organization_class,
    }


def _union_find(edges: Iterable[tuple[str, str]], nodes: Iterable[str]) -> dict[str, str]:
    parent: dict[str, str] = {n: n for n in nodes}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            # deterministic survivor: the lexicographically smaller root
            lo, hi = sorted((ra, rb))
            parent[hi] = lo
    return {n: find(n) for n in parent}


def run_entity_resolution(
    candidates: Sequence[Candidate],
    *,
    run: ERRun,
    matcher: ProbabilisticMatcher | None = None,
    cascade_context: CascadeContext | None = None,
    blocking_context: BlockingContext | None = None,
    cluster_shape_context: ClusterShapeContext | None = None,
) -> ERResult:
    """Run the six-tier cascade over ``candidates`` as one ER stage (SIG-IDENT-020).

    Deterministic tiers 0–3 auto-write over sized-blocked candidate pairs; the
    remaining blocked pairs are scored by the Splink matcher and become tier-4/5
    PROPOSED proposals. Auto-write edges are clustered (union-find); PROPOSED pairs do
    not cluster. The returned report carries the blocking sizes and cluster-shape
    alerts; gold-set metrics are added by :func:`resolution.quality_gates`.
    """
    the_matcher = matcher if matcher is not None else ProbabilisticMatcher.from_data()
    block_ctx = blocking_context if blocking_context is not None else BlockingContext.from_data()

    records = [_record_for(c) for c in candidates]
    by_id = {c.entity_id: c for c in candidates}

    # Sized blocking for the deterministic pass (SIG-IDENT-023). Only the equijoin
    # rules generate deterministic candidate pairs; the trigram rule is a probabilistic
    # candidate-search aid (SIG-IDENT-024) the matcher owns, so it is excluded here — the
    # deterministic tiers must not depend on trigram sizing.
    equijoin_rules = [r for r in load_rules() if r.method == "equijoin"]
    index_pairs = blocked_pairs(records, equijoin_rules, context=block_ctx)
    ids = [str(r["unique_id"]) for r in records]

    auto_writes: list[MatchResult] = []
    auto_write_edges: list[tuple[str, str]] = []
    auto_written: set[tuple[str, str]] = set()
    for i, j in index_pairs:
        a, b = by_id[ids[i]], by_id[ids[j]]
        result = resolve(a, b, context=cascade_context)
        if result is not None:
            auto_writes.append(result)
            edge = pair_key(a.entity_id, b.entity_id)
            auto_write_edges.append(edge)
            auto_written.add(edge)

    # Probabilistic tiers 4/5 for the fall-through pairs (never the auto-written ones).
    proposals = [
        m for m in the_matcher.match(records) if pair_key(m.left, m.right) not in auto_written
    ]

    clusters = _union_find(auto_write_edges, ids)

    org_class_by_id = {c.entity_id: c.organization_class for c in candidates}
    alerts = cluster_shape_alerts(
        clusters,
        auto_write_edges,
        org_class_by_id,
        context=cluster_shape_context,
    )

    report = ERQualityReport(
        blocking_sizes=the_matcher.size_blocking(records),
        cluster_alerts=tuple(alerts),
    )
    return ERResult(
        run=run.completed(),
        auto_writes=tuple(auto_writes),
        proposals=tuple(proposals),
        clusters=clusters,
        report=report,
    )


def cluster_same_as(
    result: ERResult,
    *,
    dated: date,
    evidence_claim: str | None = None,
) -> list[OrganizationRelation]:
    """The ``same_as`` assertions for a run's auto-write clusters (SIG-RECON-002).

    One relation per non-representative member (a star to the cluster's representative
    id), so a cluster of *n* yields *n−1* edges rather than every pair. The relations
    belong to ``result.run`` and thus to its ruleset version; a re-run under a new
    ruleset produces a new set without touching these.
    """
    members: dict[str, list[str]] = {}
    for element, cluster_id in result.clusters.items():
        members.setdefault(cluster_id, []).append(element)
    relations: list[OrganizationRelation] = []
    for representative, elements in members.items():
        for element in sorted(elements):
            if element == representative:
                continue
            relations.append(
                OrganizationRelation(
                    from_entity=element,
                    to_entity=representative,
                    relation_type=OrganizationRelationType.SAME_AS,
                    valid_from=dated,
                    evidence_claim=evidence_claim,
                )
            )
    return relations


def recluster(
    previous: ERResult,
    candidates: Sequence[Candidate],
    *,
    new_ruleset_version: str,
    code_commit: str | None = None,
    run_id: str | None = None,
    matcher: ProbabilisticMatcher | None = None,
    cascade_context: CascadeContext | None = None,
    blocking_context: BlockingContext | None = None,
) -> ERResult:
    """Re-run ER under a new ruleset without destroying the prior clustering (SIG-RECON-002).

    Produces a fresh :class:`ERResult` whose run chains back to ``previous.run`` and
    carries the new ruleset version. The previous result is returned untouched (its
    ``same_as`` assertions remain valid, append-only history); the caller decides how to
    stabilise identifiers across the shape change (:func:`stabilise_cluster_change`).
    """
    new_run = previous.run.rerun(
        ruleset_version=new_ruleset_version, code_commit=code_commit, run_id=run_id
    )
    return run_entity_resolution(
        candidates,
        run=new_run,
        matcher=matcher,
        cascade_context=cascade_context,
        blocking_context=blocking_context,
    )


def stabilise_cluster_change(
    registry: PublicIdRegistry,
    *,
    before: Mapping[str, str],
    after: Mapping[str, str],
    dated: date,
    mint_id: Callable[[], str] | None = None,
) -> list[MergeSplitEvent]:
    """Route a re-run's cluster-shape change through the stability contract (SIG-IDENT-032).

    ``before`` and ``after`` map each element to its cluster's **public identifier** in
    the old and new clustering (the old ids are live in ``registry``). Every after-group
    that unites two or more old ids is applied as a :meth:`PublicIdRegistry.merge`
    (survivor = the smallest old id); every old id whose members scatter into two or
    more after-groups is applied as a :meth:`PublicIdRegistry.split` into freshly minted
    successor ids (``mint_id`` required). Surviving identifiers are preserved and retired
    ones become redirects/tombstones — never silently reassigned.
    """
    events: list[MergeSplitEvent] = []
    elements = sorted(set(before) & set(after))

    # Merges: group elements by their new cluster id; if a new group spans >1 old id,
    # merge those old ids.
    after_to_old: dict[str, set[str]] = {}
    for element in elements:
        after_to_old.setdefault(after[element], set()).add(before[element])
    for old_ids in after_to_old.values():
        if len(old_ids) >= 2:
            sources = tuple(sorted(old_ids))
            events.append(registry.merge(sources=sources, survivor=sources[0], dated=dated))

    # Splits: group elements by their old cluster id; if an old id scatters into >1 new
    # group, split it into minted successor ids.
    old_to_after: dict[str, set[str]] = {}
    for element in elements:
        old_to_after.setdefault(before[element], set()).add(after[element])
    for old_id, new_groups in sorted(old_to_after.items()):
        if len(new_groups) >= 2:
            if mint_id is None:
                raise ValueError(
                    "a cluster split needs a mint_id to create successor identifiers "
                    "(SIG-IDENT-032)"
                )
            successors = tuple(registry.register(mint_id()) for _ in sorted(new_groups))
            events.append(registry.split(source=old_id, into=successors, dated=dated))
    return events
