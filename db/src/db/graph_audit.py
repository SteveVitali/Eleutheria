# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Whole-graph TI-6/TI-7 audits over the claim spine (P37.57b / R11-DEBT-01b).

ADR-025 established TI-1..TI-8 as pipeline data-quality checks
(:mod:`db.invariants`) run over the batch a connector is about to assert — and
recorded the gap this module closes: *"TI-6/TI-7 are batch checks, so they see
only the batch handed to them — a full-graph audit remains a separate nightly
job."* This is that job: a read-only whole-graph pass over the deployed schema,
runnable as ``sig-db graph-audit --dsn …`` and exercised in CI over a seeded
real spine (``tests/db/test_whole_graph_audits.py``).

**TI-6 (§9.6).** For predicates declared mutually exclusive — the §13.4
lifecycle tracks — the resolved intervals for one subject MUST NOT overlap at
L3. The physical guarantee already exists for the *live* view
(``resolution_no_overlap`` GiST EXCLUDE, ``WHERE upper_inf(sys_period)``); this
audit re-verifies it independently **and** extends it across all of belief
time: two resolutions on one subject inside one exclusive group are a violation
whenever their ``valid_period``s overlap *and* their ``sys_period``s overlap —
i.e. there ever existed an L3-as-of-belief view containing two mutually
exclusive states. A decision superseded before its successor was believed (the
sanctioned ``close_superseded_resolutions`` succession) has disjoint
``sys_period``s and is legal by construction.

The declaration is a set of *groups*: every predicate inside one group is
mutually exclusive with every other (including itself — same-predicate overlap
is the within-track case). §13.4's four orthogonal tracks are four singleton
groups — states within a track are mutually exclusive, while states on
different tracks co-hold by design (SIG-ONTO-061) and MUST NOT be flagged. The
fourth track predicate (``physical_state``) is declared here even where the
deployed ``vocab_predicate`` does not yet register it: an unrealised group
simply matches no rows, and declaring it keeps the §13.4 set complete.

**TI-7 (§9.6).** A ``supersedes`` chain MUST be acyclic and MUST terminate.
The audit walks every declared supersedes/succession-pointer surface in the
schema — the claim correction chain (``revises_claim``, §16.6) and retraction
chain (``retraction_of``), the derived-record succession links
(``entity_role.supersedes``, ``relationship.supersedes``,
``publication_disposition.supersedes``, the ``human_eval_*`` supersession
columns, ``evidence_artifact.supersedes_artifact_id``), the forward-pointing
``superseded_by`` vocab/technology/extraction links, and the two lineage
chains of the same acyclic-and-terminating shape (``entity.merged_into``,
``evidence_capture.parent_capture_id`` — the re-capture lineage a redacted
derivative hangs off, §10.1). Cycle direction is irrelevant to the check —
the walk runs on the pointer graph as stored. A pointer that runs off the
graph (a target row that does not exist — only constructible past its FK) is a
termination failure, not a pass.

**Drift guard.** ``SUPERSEDES_SURFACES`` is a *declaration*, and the audit
re-derives the live schema's self-referencing foreign keys from ``pg_catalog``:
any self-FK the registry does not name is reported as an un-audited surface and
fails the report — a schema change cannot silently widen the supersedes
surface without a declared decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import psycopg
from psycopg import sql

from .invariants import Violation

# ---------------------------------------------------------------------------
# TI-6 — the declared mutually-exclusive predicate groups (§9.6 / §13.4)
# ---------------------------------------------------------------------------

#: Each group is a set of predicate ids that are mutually exclusive with each
#: other on one subject: two resolved intervals inside one group may never
#: overlap (in valid time) while coexisting (in belief time). §13.4's four
#: tracks are orthogonal state variables — exclusivity is *within* a track —
#: so each track is its own singleton group. ``physical_state`` is declared
#: even where ``vocab_predicate`` does not yet register it (the group then
#: matches zero rows; the declaration is the §13.4 set, not the vocab diff).
MUTUALLY_EXCLUSIVE_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"procurement_state"}),
    frozenset({"physical_state"}),
    frozenset({"operational_state"}),
    frozenset({"authorization_state"}),
)


# ---------------------------------------------------------------------------
# TI-7 — the declared supersedes/succession-pointer surfaces
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChainSurface:
    """One self-referencing pointer column the TI-7 audit walks.

    ``kind`` labels the semantic family for the report (``supersedes`` /
    ``correction`` / ``retraction`` / ``lineage``); ``direction`` records the
    pointer's reading (``backward`` = the row points at what it replaces,
    ``forward`` = the row points at its replacement — ``superseded_by``
    columns). Cycles and non-termination are checked on the stored pointer
    graph either way.
    """

    table: str
    pk: str
    pointer: str
    kind: str
    direction: str
    note: str
    schema: str = "public"


SUPERSEDES_SURFACES: tuple[ChainSurface, ...] = (
    ChainSurface(
        "claim",
        "claim_id",
        "revises_claim",
        "correction",
        "backward",
        "§16.6 claim correction chain (correction_reason is CHECK-required)",
    ),
    ChainSurface(
        "claim",
        "claim_id",
        "retraction_of",
        "retraction",
        "backward",
        "§16.6 claim retraction chain",
    ),
    ChainSurface(
        "entity_role",
        "entity_role_id",
        "supersedes",
        "supersedes",
        "backward",
        "§12.4 role succession (the sanctioned sys_period close accompanies it)",
    ),
    ChainSurface(
        "relationship",
        "relationship_id",
        "supersedes",
        "supersedes",
        "backward",
        "§12.3 relationship succession",
    ),
    ChainSurface(
        "publication_disposition",
        "disposition_id",
        "supersedes",
        "supersedes",
        "backward",
        "ADR-124 disposition succession (append-only registry)",
    ),
    ChainSurface(
        "evidence_artifact",
        "artifact_id",
        "supersedes_artifact_id",
        "supersedes",
        "backward",
        "artifact supersession",
    ),
    ChainSurface(
        "extraction",
        "extraction_id",
        "superseded_by_extraction_id",
        "supersedes",
        "forward",
        "a re-parse supersedes the prior extraction of one capture",
    ),
    ChainSurface(
        "human_eval_label",
        "label_id",
        "supersedes_label_id",
        "supersedes",
        "backward",
        "ADR-128 eval-label supersession",
    ),
    ChainSurface(
        "human_eval_adjudication",
        "adjudication_id",
        "supersedes_adjudication_id",
        "supersedes",
        "backward",
        "ADR-128 adjudication supersession",
    ),
    ChainSurface(
        "technology",
        "technology_id",
        "superseded_by",
        "supersedes",
        "forward",
        "technology registry supersession",
    ),
    ChainSurface(
        "vocab_predicate",
        "predicate_id",
        "superseded_by",
        "supersedes",
        "forward",
        "predicate registry supersession",
    ),
    ChainSurface(
        "entity",
        "entity_id",
        "merged_into",
        "lineage",
        "forward",
        "entity merge pointer — the merge is itself a claim (CHECK bars the self-loop only)",
    ),
    ChainSurface(
        "evidence_capture",
        "capture_id",
        "parent_capture_id",
        "lineage",
        "backward",
        "re-capture lineage — a redacted derivative's parent (§10.1)",
    ),
)


# ---------------------------------------------------------------------------
# Schema self-FK discovery (the drift guard's input)
# ---------------------------------------------------------------------------


def self_referencing_fks(conn: Any) -> set[tuple[str, str, str]]:
    """The live schema's self-referencing foreign keys:
    ``{(schema, table, column)}``.

    Derived from ``pg_catalog`` so the audit's declaration is checked against
    the deployed truth — a new self-FK (a new supersedes surface nobody
    declared) is an un-audited surface and fails the report. All non-system
    namespaces are scanned, so a self-FK added in ``inference.*`` (or any
    future schema) is caught the same way.
    """
    rows = conn.execute(
        "SELECT ns.nspname, cls.relname, att.attname"
        "  FROM pg_catalog.pg_constraint con"
        "  JOIN pg_catalog.pg_namespace ns ON ns.oid = con.connamespace"
        "  JOIN pg_catalog.pg_class cls ON cls.oid = con.conrelid"
        "  JOIN pg_catalog.pg_attribute att"
        "    ON att.attrelid = con.conrelid AND att.attnum = ANY(con.conkey)"
        " WHERE con.contype = 'f' AND con.conrelid = con.confrelid"
        "   AND ns.nspname NOT IN ('pg_catalog', 'information_schema', 'sqitch')"
    ).fetchall()
    return {(str(ns), str(t), str(c)) for ns, t, c in rows}


def undeclared_self_fks(conn: Any) -> list[str]:
    """Self-referencing FKs in the live schema the registry does not name."""
    declared = {(s.schema, s.table, s.pointer) for s in SUPERSEDES_SURFACES}
    return sorted(f"{ns}.{table}.{col}" for ns, table, col in self_referencing_fks(conn) - declared)


# ---------------------------------------------------------------------------
# TI-6 — whole-graph resolved-interval audit
# ---------------------------------------------------------------------------


def audit_ti6(
    conn: Any,
    *,
    groups: tuple[frozenset[str], ...] | list[frozenset[str]] = MUTUALLY_EXCLUSIVE_GROUPS,
) -> list[Violation]:
    """TI-6 over the whole ``resolution`` table (all of belief time).

    For every declared mutually-exclusive group, a same-subject pair of
    resolutions inside the group violates TI-6 when their ``valid_period``s
    overlap AND their ``sys_period``s overlap — at some belief instant the L3
    view then held two mutually exclusive states. The live-view case (both
    rows ``upper_inf(sys_period)``) is the one ``resolution_no_overlap`` also
    guards; the belief-coexistence case (a superseded row whose window
    overlaps the successor's) is the whole-graph extension the batch check
    could never see.
    """
    violations: list[Violation] = []
    seen_pairs: set[tuple[str, str]] = set()
    for group in groups:
        preds = sorted(group)
        rows = conn.execute(
            "SELECT r1.subject_id::text, r1.resolution_id::text,"
            "       r2.resolution_id::text, r1.predicate_id, r2.predicate_id,"
            "       r1.valid_period::text, r2.valid_period::text,"
            "       r1.sys_period::text, r2.sys_period::text,"
            "       (pg_catalog.upper_inf(r1.sys_period)"
            "        AND pg_catalog.upper_inf(r2.sys_period)) AS both_live"
            "  FROM resolution r1"
            "  JOIN resolution r2"
            "    ON r1.subject_id = r2.subject_id"
            "   AND r1.resolution_id < r2.resolution_id"
            "   AND r1.valid_period && r2.valid_period"
            "   AND r1.sys_period && r2.sys_period"
            " WHERE r1.predicate_id = ANY(%s::text[])"
            "   AND r2.predicate_id = ANY(%s::text[])"
            " ORDER BY r1.subject_id",
            (preds, preds),
        ).fetchall()
        for subject, r1_id, r2_id, p1, p2, v1, v2, s1, s2, both_live in rows:
            if (r1_id, r2_id) in seen_pairs:
                continue
            seen_pairs.add((r1_id, r2_id))
            window = (
                "both live in the current resolved view"
                if both_live
                else "coexisted in belief time"
            )
            violations.append(
                Violation(
                    "TI-6",
                    subject,
                    f"mutually-exclusive resolutions {r1_id} ({p1} valid {v1}) "
                    f"and {r2_id} ({p2} valid {v2}) overlap and {window} "
                    f"(sys {s1} / {s2})",
                )
            )
    return violations


# ---------------------------------------------------------------------------
# TI-7 — supersedes-chain acyclicity + termination
# ---------------------------------------------------------------------------


def _chain_edges(conn: Any, surface: ChainSurface) -> tuple[set[str], dict[str, str]]:
    """``(all node ids, node -> pointer-target)`` for one declared surface."""
    stmt = sql.SQL("SELECT {}::text, {}::text FROM {}.{}").format(
        sql.Identifier(surface.pk),
        sql.Identifier(surface.pointer),
        sql.Identifier(surface.schema),
        sql.Identifier(surface.table),
    )
    nodes: set[str] = set()
    edges: dict[str, str] = {}
    for node, target in conn.execute(stmt).fetchall():
        nodes.add(str(node))
        if target is not None:
            edges[str(node)] = str(target)
    return nodes, edges


def audit_ti7(
    conn: Any,
    *,
    surfaces: tuple[ChainSurface, ...] = SUPERSEDES_SURFACES,
) -> tuple[list[Violation], dict[str, int]]:
    """TI-7 over every declared supersedes/succession pointer surface.

    Returns ``(violations, edges_walked)`` — ``edges_walked`` is the per-surface
    pointer count so a report can prove the audit ran the whole declared set.
    A chain violates TI-7 when it **cycles** (the walk revisits a node) or
    **runs off the graph** (a pointer target that is not a row — a termination
    failure only constructible past the foreign key).
    """
    violations: list[Violation] = []
    walked: dict[str, int] = {}
    for surface in surfaces:
        name = f"{surface.table}.{surface.pointer}"
        nodes, edges = _chain_edges(conn, surface)
        walked[name] = len(edges)
        reported_cycles: set[tuple[str, ...]] = set()
        reported_ghosts: set[str] = set()
        for start in edges:
            path: list[str] = []
            seen: set[str] = set()
            node: str = start
            while True:
                if node in seen:
                    cyc = path[path.index(node) :]
                    pivot = cyc.index(min(cyc))
                    canon = tuple(cyc[pivot:] + cyc[:pivot])
                    if canon not in reported_cycles:
                        reported_cycles.add(canon)
                        violations.append(
                            Violation(
                                "TI-7",
                                name,
                                f"{surface.kind} chain cycles "
                                f"({' -> '.join(cyc + [node])}) — a supersedes "
                                "chain MUST be acyclic",
                            )
                        )
                    break
                if node not in nodes:
                    if node not in reported_ghosts:
                        reported_ghosts.add(node)
                        violations.append(
                            Violation(
                                "TI-7",
                                name,
                                f"{surface.kind} chain runs off the graph at "
                                f"{node} (no such {surface.table} row) — a "
                                "supersedes chain MUST terminate",
                            )
                        )
                    break
                seen.add(node)
                path.append(node)
                nxt = edges.get(node)
                if nxt is None:
                    break  # terminates at a node with no outgoing pointer
                node = nxt
    return violations, walked


# ---------------------------------------------------------------------------
# The whole-graph pass
# ---------------------------------------------------------------------------


@dataclass
class GraphAuditReport:
    """One whole-graph audit result (§9.6 TI-6/TI-7)."""

    resolutions_scanned: int
    edges_walked: dict[str, int]
    ti6_violations: list[Violation] = field(default_factory=list)
    ti7_violations: list[Violation] = field(default_factory=list)
    unaudited_self_fks: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.ti6_violations and not self.ti7_violations and not self.unaudited_self_fks

    @property
    def violations(self) -> list[Violation]:
        return [*self.ti6_violations, *self.ti7_violations]

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "resolutions_scanned": self.resolutions_scanned,
            "edges_walked": dict(sorted(self.edges_walked.items())),
            "unaudited_self_fks": self.unaudited_self_fks,
            "violations": [
                {"invariant": v.invariant, "subject": v.subject, "reason": v.reason}
                for v in self.violations
            ],
        }


def audit_graph(
    conn: Any,
    *,
    groups: tuple[frozenset[str], ...] | list[frozenset[str]] = MUTUALLY_EXCLUSIVE_GROUPS,
    surfaces: tuple[ChainSurface, ...] = SUPERSEDES_SURFACES,
) -> GraphAuditReport:
    """Run the whole-graph TI-6/TI-7 pass. Read-only — the audit never writes."""
    scanned = conn.execute("SELECT count(*) FROM resolution").fetchone()[0]
    ti6 = audit_ti6(conn, groups=groups)
    ti7, walked = audit_ti7(conn, surfaces=surfaces)
    return GraphAuditReport(
        resolutions_scanned=int(scanned),
        edges_walked=walked,
        ti6_violations=ti6,
        ti7_violations=ti7,
        unaudited_self_fks=undeclared_self_fks(conn),
    )


def run(dsn: str) -> dict[str, Any]:
    """Connect to ``dsn``, run the whole-graph audit, return the report dict."""
    with psycopg.connect(dsn, autocommit=False) as conn:
        return audit_graph(conn).as_dict()
