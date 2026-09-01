# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Access-path closure — SIG's most powerful and most dangerous inference (§30.2).

"Can organization A reach organization B's data, through *any* chain?" is the
transitive-closure question OL-22.4-01 identifies as central (SIG-RECON-048). It
MUST be implemented, and it MUST be bounded (SIG-RECON-049): an unbounded or
unlabelled closure turns a finding into an insinuation — a false "A can search C"
built from "A searched B and B searched C", or an unexplained seven-hop theoretical
path rendered as if it were a shared-data relationship.

The bounds this module enforces, each a named safety rule, are:

* **Only ``configured_access`` and ``federates_search_to`` compose**
  (:data:`COMPOSABLE_LABELS`). ``observed_use`` does not compose — that A used B and
  B used C does not mean A can reach C. ``declared_policy`` is a statement, not a
  channel. ``distributes_list_to`` does not compose in the query direction: a
  hotlist flowing outward creates no inbound search path (§12.3 rule 3). These are
  precisely the three §12.2 sharing edge types kept **separate** — closure never
  merges, collapses, or defaults one into another (SIG-ONTO-042); a hop keeps the
  ``access_kind``/``edge_label`` it was given.
* **Scope may not broaden along a chain** — a partner-scoped edge does not chain
  into a national-scoped one (:func:`_scope_breadth`). A path's scope is the
  narrowest hop's.
* **Every hop must be currently valid at the as-of time.** A path through an expired
  edge is a *historical* path and is labelled so (:data:`HISTORICAL`); a path through
  an edge that has not yet begun is not asserted at all.
* **Path length is capped and reported.** Every path carries its full hop list with
  each hop's evidence — an unexplained "A can reach B" is the forbidden unexplained
  edge (§3.1). Enumeration stops at :data:`MAX_PATH_HOPS`.
* **Confidence is the minimum over the path**, never the average — a chain is as
  strong as its weakest hop (:data:`CONFIDENCE_ORDER`).
* **Beyond :data:`SPECULATIVE_HOP_THRESHOLD` hops a path is labelled speculative**
  and excluded from headline figures (SIG-RECON-050); it is still shown, with its
  hops, but never blurred into "these agencies share data".

The output is an **L4 inference** (SIG-RECON-047): :meth:`AccessPath.to_inference`
carries ``derivation_rule`` / ``derived_at`` / ``input_claim_ids`` and is never an
observation. Edges are normalized into accessor→provider reachability terms before
closure (``from_org`` is the accessor, ``to_org`` the data holder); mapping the raw
§12.5 ``AccessRelationship`` / §12.3 integration edges into that form (respecting
each edge type's native direction) is the caller's responsibility. This module owns
the closure bound; it does not fork the P08.2 sharing-edge reconciler that lands the
edges (SIG-RECON-034/037).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime

from reconcile.model import Inference
from reconcile.sharing import ACCESS_KINDS

__all__ = [
    "ACCESS_KINDS",
    "COMPOSABLE_LABELS",
    "NON_COMPOSING_ACCESS_KINDS",
    "CONFIDENCE_ORDER",
    "SCOPE_ORDER",
    "MAX_PATH_HOPS",
    "SPECULATIVE_HOP_THRESHOLD",
    "DERIVATION_RULE",
    "RULE_VERSION",
    "LIVE",
    "HISTORICAL",
    "AccessEdge",
    "AccessPath",
    "AccessPathClosure",
    "close_access_paths",
]

#: The only two edge labels that compose in a reachability chain (SIG-RECON-049 #1).
#: ``configured_access`` is one of the three §12.2 sharing kinds; ``federates_search_to``
#: is a §12.3 integration edge where the query moves but the corpus stays with the
#: holder. Every other label — including the other two sharing kinds and
#: ``distributes_list_to`` — is deliberately excluded.
COMPOSABLE_LABELS: frozenset[str] = frozenset({"configured_access", "federates_search_to"})

#: The §12.2 sharing kinds that MUST NOT compose (kept here to make the exclusion
#: explicit and testable): ``observed_use`` (use is not access) and ``declared_policy``
#: (a statement is not a channel). Never merged into ``configured_access``.
NON_COMPOSING_ACCESS_KINDS: frozenset[str] = frozenset(ACCESS_KINDS) - COMPOSABLE_LABELS

#: Confidence labels from least to most confident (§29.2 uses ``probable`` as the
#: default). Path confidence is the *minimum* over the hops (SIG-RECON-049 #6).
CONFIDENCE_ORDER: tuple[str, ...] = ("possible", "probable", "certain")

#: Capability scope from narrowest to broadest (§11.6). Used only to forbid a chain
#: from *broadening* its reach (SIG-RECON-049 #3); ``commercial`` is treated as the
#: broadest since a commercial-scope relationship is the least self-limiting.
SCOPE_ORDER: tuple[str, ...] = (
    "subject",
    "own",
    "partner",
    "state",
    "region",
    "national",
    "commercial",
)

#: The hard enumeration cap: closure never builds a path longer than this many hops
#: (SIG-RECON-049 #5). Distinct from the speculative threshold below.
MAX_PATH_HOPS: int = 8

#: The published hop count beyond which a path is labelled speculative and excluded
#: from headline figures (SIG-RECON-050). A 1..THRESHOLD-hop path is publishable as a
#: finding; a longer one is shown but never counted as a shared-data relationship.
SPECULATIVE_HOP_THRESHOLD: int = 3

DERIVATION_RULE = "access_path_closure/§30.2"
RULE_VERSION = "p12.2/1"

#: Temporal labels for a whole path (SIG-RECON-049 #4).
LIVE = "live"
HISTORICAL = "historical"

_CONFIDENCE_RANK = {label: i for i, label in enumerate(CONFIDENCE_ORDER)}
_SCOPE_RANK = {scope: i for i, scope in enumerate(SCOPE_ORDER)}


def _now() -> datetime:
    return datetime.now(UTC)


def _scope_breadth(scope: str) -> int:
    """The breadth rank of a scope; broader scopes rank higher (SIG-RECON-049 #3)."""
    try:
        return _SCOPE_RANK[scope]
    except KeyError as exc:  # pragma: no cover - guarded at construction
        raise ValueError(f"unknown scope {scope!r} (§11.6 expects one of {SCOPE_ORDER})") from exc


@dataclass(frozen=True)
class AccessEdge:
    """One directed reachability edge available to closure (normalized).

    ``from_org`` is the **accessor** and ``to_org`` the **data holder**: the edge
    asserts that ``from_org`` can reach ``to_org``'s data. ``edge_label`` is either a
    §12.2 sharing ``access_kind`` (``configured_access`` / ``observed_use`` /
    ``declared_policy``) or a §12.3 integration ``edge_type`` (``federates_search_to``,
    ``distributes_list_to``, …); it is preserved verbatim and used only to decide
    composability — closure never rewrites it (SIG-ONTO-042).

    ``evidence`` is required and non-empty: a hop with no supporting claim would make
    the derived path an unexplained edge, which the defining standard forbids
    (§3.1, SIG-RECON-049 #5).
    """

    from_org: str
    to_org: str
    edge_label: str
    scope: str
    evidence: tuple[str, ...]
    confidence: str = "probable"
    valid_from: date | None = None
    valid_to: date | None = None
    valid_from_kind: str = "unknown"
    valid_to_kind: str = "ongoing"
    edge_id: str = ""
    asserted_by: str = ""

    def __post_init__(self) -> None:
        if not self.from_org or not self.to_org:
            raise ValueError(
                "an AccessEdge MUST name both endpoints (every node has identity, §3.1)"
            )
        if self.from_org == self.to_org:
            raise ValueError(
                f"an AccessEdge MUST be between two orgs, not a self-loop ({self.from_org!r})"
            )
        if self.scope not in _SCOPE_RANK:
            raise ValueError(f"unknown scope {self.scope!r} (§11.6 expects one of {SCOPE_ORDER})")
        if self.confidence not in _CONFIDENCE_RANK:
            raise ValueError(
                f"unknown confidence {self.confidence!r} (expected one of {CONFIDENCE_ORDER})"
            )
        if not self.evidence:
            raise ValueError(
                "an AccessEdge MUST carry at least one evidence/claim id — an unexplained "
                "hop is the forbidden unexplained edge (§3.1, SIG-RECON-049 #5)"
            )

    @property
    def composes(self) -> bool:
        """Whether this edge may be a hop in a reachability chain (SIG-RECON-049 #1/#2)."""
        return self.edge_label in COMPOSABLE_LABELS

    @property
    def scope_breadth(self) -> int:
        return _SCOPE_RANK[self.scope]

    def temporal_status(self, as_of: date) -> str:
        """This hop's validity at ``as_of``: ``valid`` / ``expired`` / ``future``.

        A known ``valid_to`` before ``as_of`` is expired; a known ``valid_from`` after
        ``as_of`` is future. A single-snapshot sharing edge (``valid_from_kind='unknown'``,
        ``valid_to_kind='ongoing'``, SIG-ONTO-044) is always ``valid`` — a snapshot
        proves the state at observation and nothing about when sharing began or ends.
        """
        if self.valid_to_kind == "known" and self.valid_to is not None and self.valid_to < as_of:
            return "expired"
        if (
            self.valid_from_kind == "known"
            and self.valid_from is not None
            and self.valid_from > as_of
        ):
            return "future"
        return "valid"

    def hop_view(self) -> dict[str, object]:
        """The per-hop projection every published path must carry (SIG-RECON-049 #5)."""
        return {
            "from_org": self.from_org,
            "to_org": self.to_org,
            "edge_label": self.edge_label,
            "scope": self.scope,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "edge_id": self.edge_id,
            "asserted_by": self.asserted_by,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "valid_from_kind": self.valid_from_kind,
            "valid_to_kind": self.valid_to_kind,
        }


@dataclass(frozen=True)
class AccessPath:
    """A derived reachability path ``source → … → target`` and its labels.

    Carries its full hop list (:attr:`hops`) — never a bare "A can reach B". The
    class computes, and never lets a caller override, the safety labels: the
    path-minimum :attr:`confidence`, the :attr:`temporal_status`, whether it is
    :attr:`speculative`, and whether it belongs in :attr:`is_headline` figures.
    """

    hops: tuple[AccessEdge, ...]
    as_of: date
    speculative_hop_threshold: int = SPECULATIVE_HOP_THRESHOLD

    def __post_init__(self) -> None:
        if not self.hops:
            raise ValueError("an AccessPath MUST have at least one hop")
        for a, b in zip(self.hops, self.hops[1:], strict=False):
            if a.to_org != b.from_org:
                raise ValueError(
                    f"hops are not contiguous: {a.from_org}->{a.to_org} then "
                    f"{b.from_org}->{b.to_org} (a path must be a connected chain)"
                )

    @property
    def source(self) -> str:
        return self.hops[0].from_org

    @property
    def target(self) -> str:
        return self.hops[-1].to_org

    @property
    def orgs(self) -> tuple[str, ...]:
        """The ordered node list source..target."""
        return (self.hops[0].from_org, *(h.to_org for h in self.hops))

    @property
    def hop_count(self) -> int:
        return len(self.hops)

    @property
    def confidence(self) -> str:
        """The minimum confidence over the hops — never the average (SIG-RECON-049 #6)."""
        return min((h.confidence for h in self.hops), key=lambda c: _CONFIDENCE_RANK[c])

    @property
    def scope(self) -> str:
        """The narrowest hop scope — a chain reaches only as broadly as its tightest hop."""
        return min((h.scope for h in self.hops), key=lambda s: _SCOPE_RANK[s])

    @property
    def temporal_status(self) -> str:
        """``live`` if every hop is valid at :attr:`as_of`, else ``historical``.

        A path is only constructed when no hop is *future* (closure never asserts a
        chain through an edge that has not begun), so the only two outcomes are a
        fully-live path or one labelled historical because a hop has expired.
        """
        if any(h.temporal_status(self.as_of) == "expired" for h in self.hops):
            return HISTORICAL
        return LIVE

    @property
    def speculative(self) -> bool:
        """Beyond the published hop threshold, the path is speculative (SIG-RECON-050)."""
        return self.hop_count > self.speculative_hop_threshold

    @property
    def is_headline(self) -> bool:
        """Whether this path may appear in headline figures.

        Only a live, non-speculative path counts (SIG-RECON-050). A single direct hop
        is an observation, not a closure inference, so it is excluded from the derived
        headline set too.
        """
        return self.temporal_status == LIVE and not self.speculative and self.hop_count >= 2

    @property
    def input_claim_ids(self) -> tuple[str, ...]:
        """Every hop's evidence ids, in path order, de-duplicated."""
        seen: dict[str, None] = {}
        for hop in self.hops:
            for cid in hop.evidence:
                seen.setdefault(cid, None)
        return tuple(seen)

    def hop_views(self) -> tuple[dict[str, object], ...]:
        return tuple(h.hop_view() for h in self.hops)

    def rationale(self) -> str:
        chain = " -> ".join(self.orgs)
        via = "; ".join(f"{h.from_org}->{h.to_org} ({h.edge_label}, {h.scope})" for h in self.hops)
        return (
            f"{self.source} can reach {self.target} via {chain} "
            f"[{self.hop_count} hop(s): {via}]. Confidence is the path minimum "
            f"({self.confidence}); scope is the narrowest hop ({self.scope}); "
            f"temporal status {self.temporal_status}"
            + (
                "; SPECULATIVE — beyond the published hop threshold, excluded from "
                "headline figures (SIG-RECON-050)."
                if self.speculative
                else "."
            )
        )

    def public_view(self) -> dict[str, object]:
        """The API/export projection — always carries the full hop list (SIG-UI-025)."""
        return {
            "source": self.source,
            "target": self.target,
            "hop_count": self.hop_count,
            "confidence": self.confidence,
            "scope": self.scope,
            "temporal_status": self.temporal_status,
            "speculative": self.speculative,
            "is_headline": self.is_headline,
            "hops": list(self.hop_views()),
            "rationale": self.rationale(),
        }

    def to_inference(self, *, derived_at: datetime | None = None) -> Inference:
        """This path as a labelled L4 inference (SIG-RECON-047), never an observation.

        Carries ``derivation_rule`` / ``rule_version`` / ``input_claim_ids`` and the
        path-minimum ``confidence``; the value keeps the full hop list and every safety
        label so no downstream surface can render "A can reach B" without them.
        """
        return Inference(
            subject_id=self.source,
            predicate_id="access_path_reaches",
            value={
                "target": self.target,
                "hop_count": self.hop_count,
                "scope": self.scope,
                "temporal_status": self.temporal_status,
                "speculative": self.speculative,
                "is_headline": self.is_headline,
                "hops": list(self.hop_views()),
            },
            derivation_rule=DERIVATION_RULE,
            rule_version=RULE_VERSION,
            input_claim_ids=self.input_claim_ids,
            confidence=self.confidence,
            rationale=self.rationale(),
        )


@dataclass(frozen=True)
class AccessPathClosure:
    """The result of a closure query — all paths, partitioned by publishability."""

    source: str
    as_of: date
    paths: tuple[AccessPath, ...]

    @property
    def headline_paths(self) -> tuple[AccessPath, ...]:
        """Live, non-speculative, multi-hop paths — the only ones fit for headlines."""
        return tuple(p for p in self.paths if p.is_headline)

    @property
    def speculative_paths(self) -> tuple[AccessPath, ...]:
        """Paths beyond the published hop threshold (SIG-RECON-050)."""
        return tuple(p for p in self.paths if p.speculative)

    @property
    def historical_paths(self) -> tuple[AccessPath, ...]:
        """Paths that pass through an expired hop (SIG-RECON-049 #4)."""
        return tuple(p for p in self.paths if p.temporal_status == HISTORICAL)

    def reachable(self, *, headline_only: bool = False) -> frozenset[str]:
        """The set of orgs reachable from :attr:`source`.

        With ``headline_only`` the speculative and historical paths are excluded — the
        answer a headline "can reach" figure is allowed to use (SIG-RECON-050).
        """
        pool = self.headline_paths if headline_only else self.paths
        return frozenset(p.target for p in pool)


def close_access_paths(
    edges: Iterable[AccessEdge],
    *,
    source: str,
    as_of: date,
    target: str | None = None,
    max_hops: int = MAX_PATH_HOPS,
    speculative_hop_threshold: int = SPECULATIVE_HOP_THRESHOLD,
) -> AccessPathClosure:
    """Enumerate bounded reachability paths from ``source`` (SIG-RECON-048/049/050).

    Only composable edges (:data:`COMPOSABLE_LABELS`) are ever traversed, so
    ``observed_use`` / ``declared_policy`` / ``distributes_list_to`` edges in ``edges``
    contribute no chain. A hop is refused when it would broaden the chain's scope
    (SIG-RECON-049 #3) or when it is *future* at ``as_of`` (it has not begun); an
    *expired* hop is allowed but taints the whole path as historical. Simple paths
    only (no org repeats — closure never loops). Enumeration stops at ``max_hops``.

    Returns every discovered path (length ≥ 1). When ``target`` is given, only paths
    ending at ``target`` are returned. The caller reads publishability off each path
    (:attr:`AccessPath.is_headline` / :attr:`AccessPath.speculative`); nothing here
    silently drops a long or historical path — it is labelled, not blurred.
    """
    if max_hops < 1:
        raise ValueError("max_hops must be at least 1")

    # Index only the composable edges by their accessor endpoint — the non-composing
    # kinds are never traversal candidates (SIG-RECON-049 #1/#2).
    out_edges: dict[str, list[AccessEdge]] = {}
    for edge in edges:
        if edge.composes:
            out_edges.setdefault(edge.from_org, []).append(edge)

    found: list[AccessPath] = []

    def _walk(node: str, chain: tuple[AccessEdge, ...], visited: frozenset[str]) -> None:
        if len(chain) >= max_hops:
            return
        for edge in out_edges.get(node, ()):
            nxt = edge.to_org
            if nxt in visited:
                continue  # simple paths only — never loop
            # A future hop cannot extend a chain asserted as of `as_of`.
            if edge.temporal_status(as_of) == "future":
                continue
            # Scope may not broaden along the chain (SIG-RECON-049 #3).
            if chain and edge.scope_breadth > chain[-1].scope_breadth:
                continue
            new_chain = (*chain, edge)
            if target is None or nxt == target:
                found.append(
                    AccessPath(
                        hops=new_chain,
                        as_of=as_of,
                        speculative_hop_threshold=speculative_hop_threshold,
                    )
                )
            _walk(nxt, new_chain, visited | {nxt})

    _walk(source, (), frozenset({source}))
    # Deterministic order: shorter paths first, then by node list.
    found.sort(key=lambda p: (p.hop_count, p.orgs))
    return AccessPathClosure(source=source, as_of=as_of, paths=tuple(found))
