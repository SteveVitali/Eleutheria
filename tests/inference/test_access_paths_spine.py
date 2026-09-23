# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Access-path closure over the MATERIALIZED relationship edges (P28.2).

The closure bound itself is P12.2's (``inference.access_paths.close_access_paths``) and
is CONSUMED here (SIG-ENG-035), never re-implemented; these tests cover only the
materialized-edge → :class:`AccessEdge` adaptor and the spine-reading wrapper.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from inference.access_paths import (
    DEFAULT_MATERIALIZED_SCOPE,
    access_edges_from_materialized,
    close_access_paths_over_spine,
)

A = "00000000-0000-0000-0000-0000000000a1"
B = "00000000-0000-0000-0000-0000000000b2"
C = "00000000-0000-0000-0000-0000000000c3"


def _edge(
    frm: str, to: str, kind: str = "configured_access", claim: str = "claim-1"
) -> dict[str, Any]:
    return {
        "from_entity": frm,
        "to_entity": to,
        "edge_type": kind,
        "access_kind": kind,
        "direction": "a_to_b",
        "valid_from_kind": "unknown",
        "valid_to_kind": "ongoing",
        "asserted_by": frm,
        "valid_from": "2026-05-01",
        "evidence_claim": claim,
        "relationship_id": f"rel-{frm}-{to}",
    }


def test_adaptor_maps_access_kind_to_edge_label_verbatim() -> None:
    edges = access_edges_from_materialized([_edge(A, B, "configured_access")])
    assert len(edges) == 1
    e = edges[0]
    assert e.from_org == A and e.to_org == B
    assert e.edge_label == "configured_access"  # SIG-ONTO-042: kept verbatim, decides composability
    assert e.composes is True
    assert e.scope == DEFAULT_MATERIALIZED_SCOPE
    assert e.evidence == ("claim-1",)


def test_adaptor_skips_unevidenced_edge() -> None:
    bad = _edge(A, B)
    bad["evidence_claim"] = None
    assert access_edges_from_materialized([bad]) == []


def test_observed_use_does_not_compose() -> None:
    edges = access_edges_from_materialized([_edge(A, B, "observed_use")])
    assert edges[0].composes is False


class _FakeCursor:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._rows


class _FakeConn:
    """Returns materialized-edge rows in read_materialized_edges' column order."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> _FakeCursor:
        assert "FROM relationship" in sql
        out = []
        for r in self._rows:
            out.append(
                (
                    r["from_entity"],
                    r["to_entity"],
                    r["edge_type"],
                    r["access_kind"],
                    r["direction"],
                    r["valid_from_kind"],
                    r["valid_to_kind"],
                    r["asserted_by"],
                    date.fromisoformat(r["valid_from"]),
                    r["evidence_claim"],
                    r["relationship_id"],
                )
            )
        return _FakeCursor(out)


def test_close_over_spine_chains_composable_edges() -> None:
    # A -> B -> C, both configured_access → a 2-hop reachability path (headline).
    conn = _FakeConn(
        [_edge(A, B, "configured_access", "c-ab"), _edge(B, C, "configured_access", "c-bc")]
    )
    closure = close_access_paths_over_spine(conn, source=A, as_of=date(2026, 9, 1))
    reachable = closure.reachable()
    assert B in reachable and C in reachable
    two_hop = [p for p in closure.paths if p.hop_count == 2]
    assert two_hop and two_hop[0].target == C and two_hop[0].is_headline


def test_close_over_spine_does_not_chain_observed_use() -> None:
    # observed_use does not compose: A used B, B used C does NOT mean A can reach C.
    conn = _FakeConn([_edge(A, B, "observed_use", "o-ab"), _edge(B, C, "observed_use", "o-bc")])
    closure = close_access_paths_over_spine(conn, source=A, as_of=date(2026, 9, 1))
    assert closure.paths == ()
