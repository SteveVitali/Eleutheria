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
    HISTORICAL,
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
        # P35.30: read_materialized_edges now also selects observed_at and
        # upper(valid_period) — the fake must return them in SELECT order.
        "observed_at": "2026-05-01",
        "valid_to": None,
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
                    # P35.30 columns, in SELECT order (date objects, like the
                    # real psycopg row — isoformat'd by the reader).
                    date.fromisoformat(r["observed_at"]),
                    r["valid_to"],
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


def test_adaptor_carries_the_full_evidence_claims_set() -> None:
    # GX-07 (P37.21): a materialized row's ``evidence_claims`` carries the whole
    # backing set — the hop's per-hop evidence is the full set, sorted, never
    # just the representative ``evidence_claim``.
    row = _edge(A, B, "configured_access", "c-ab-1")
    row["evidence_claims"] = ["c-ab-2", "c-ab-1", "c-ab-2"]
    edges = access_edges_from_materialized([row])
    assert edges[0].evidence == ("c-ab-1", "c-ab-2")


def test_adaptor_maps_an_ended_bound_kind_to_known_with_the_date() -> None:
    # Live vs historical (GX-07): a recorded valid-period end — bound-kind
    # ``exact``/``before``/``after`` with its ``valid_to`` date — maps onto the
    # closure's ``known`` so the hop can expire the path at as-of.
    row = _edge(A, B)
    row["valid_to_kind"] = "exact"
    row["valid_to"] = "2020-01-28"
    (e,) = access_edges_from_materialized([row])
    assert e.valid_to_kind == "known"
    assert e.valid_to == date(2020, 1, 28)
    assert e.temporal_status(date(2026, 9, 1)) == "expired"
    assert e.temporal_status(date(2019, 1, 1)) == "valid"


def test_adaptor_marks_a_continuing_edge_ongoing_and_the_rest_unknown() -> None:
    row = _edge(A, B)
    row["valid_to_kind"] = "never"
    (e,) = access_edges_from_materialized([row])
    assert e.valid_to_kind == "ongoing" and e.valid_to is None
    row["valid_to_kind"] = "undated"
    (e,) = access_edges_from_materialized([row])
    assert e.valid_to_kind == "unknown" and e.valid_to is None


def test_close_over_spine_marks_a_path_through_an_ended_hop_historical() -> None:
    # A -> B -> C where B -> C recorded its end: the path is labelled
    # historical — kept visible, never dropped and never present-tense.
    ended = _edge(B, C, "configured_access", "c-bc")
    ended["valid_to_kind"] = "exact"
    ended["valid_to"] = date(2020, 1, 28)
    conn = _FakeConn([_edge(A, B, "configured_access", "c-ab"), ended])
    closure = close_access_paths_over_spine(conn, source=A, as_of=date(2026, 9, 1))
    two_hop = [p for p in closure.paths if p.hop_count == 2]
    assert two_hop and two_hop[0].temporal_status == HISTORICAL
    assert two_hop[0].is_headline is False
