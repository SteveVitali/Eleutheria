# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Unit tests for the sharing/access relationship materializer (P28.2).

The real DB round-trip (sqitch deploy/revert/verify, insert-only, idempotent +0 over
PG18+PostGIS) is covered by ``tests/db/test_relationship_materialize.py``; these are the
pure mapping / reconcile / accounting tests that need no Postgres. The §29.3 sharing-edge
reconciliation itself is P08.2's (``reconcile.sharing``) and is exercised here only as a
CONSUMED dependency (SIG-ENG-035), never re-implemented.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from reconcile.materialize import (
    ACCESS_KIND_PREDICATE_HINTS,
    EdgeMaterializeSummary,
    classify_access_kind,
    edge_row,
    materialize_sharing_edges,
    read_materialized_edges,
    read_sharing_observations,
)
from reconcile.sharing import ReconciledEdge, SharingObservation, reconcile_sharing

A = "00000000-0000-0000-0000-0000000000a1"
B = "00000000-0000-0000-0000-0000000000b2"
C = "00000000-0000-0000-0000-0000000000c3"
CLAIM_1 = "00000000-0000-0000-0000-0000000011a1"
CLAIM_2 = "00000000-0000-0000-0000-0000000022b2"


def _reconciled(
    frm: str = A,
    to: str = B,
    kind: str = "configured_access",
    claims: tuple[str, ...] = (CLAIM_1,),
    corroborated: bool = False,
) -> ReconciledEdge:
    obs = tuple(
        SharingObservation(
            asserted_by=frm,
            from_org=frm,
            to_org=to,
            access_kind=kind,
            observed_at=date(2026, 5, 1),
            from_single_snapshot=True,
            claim_id=c,
        )
        for c in claims
    )
    return ReconciledEdge(
        from_org=frm,
        to_org=to,
        access_kind=kind,
        valid_from_kind="unknown",
        corroborated=corroborated,
        observations=obs,
    )


# --- classification ---------------------------------------------------------


def test_classify_maps_sharing_predicates_to_the_three_kinds() -> None:
    assert classify_access_kind("configured_sharing_partner") == "configured_access"
    assert classify_access_kind("observed_national_search") == "observed_use"
    assert classify_access_kind("declared_sharing_policy") == "declared_policy"


def test_classify_returns_none_for_unclassifiable_predicate() -> None:
    # Never coerced into a kind the evidence does not support (SIG-ONTO-042).
    assert classify_access_kind("active_device_count") is None
    assert classify_access_kind("camera_latitude") is None


def test_hints_only_name_the_three_access_kinds() -> None:
    kinds = {k for _, k in ACCESS_KIND_PREDICATE_HINTS}
    assert kinds == {"configured_access", "observed_use", "declared_policy"}


# --- edge_row mapping -------------------------------------------------------


def test_edge_row_maps_reconciled_edge_to_relationship_columns() -> None:
    row = edge_row(_reconciled())
    assert row is not None
    assert row["from_entity"] == A and row["to_entity"] == B
    # §12.5: access_kind IS the edge_type for an access relationship.
    assert row["edge_type"] == "configured_access"
    assert row["access_kind"] == "configured_access"
    assert row["direction"] == "a_to_b"
    assert row["valid_from_kind"] == "unknown"
    assert row["valid_to_kind"] == "ongoing"  # SIG-ONTO-044: snapshot proves current state
    assert row["evidence_claim"] == CLAIM_1  # evidenced (§3.1)
    assert row["observed_at"] == date(2026, 5, 1)
    assert row["input_digest"]


def test_edge_row_picks_deterministic_representative_claim() -> None:
    row = edge_row(_reconciled(claims=(CLAIM_2, CLAIM_1)))
    assert row is not None
    # min claim id, independent of observation order.
    assert row["evidence_claim"] == CLAIM_1
    assert row["evidence_claims"] == [CLAIM_1, CLAIM_2]


def test_edge_row_is_none_for_name_only_partner() -> None:
    # A partner that is not a resolved entity (object_entity NULL) cannot be a
    # relationship FK — reconciled but not materialized, never a fabricated node.
    assert edge_row(_reconciled(to="City Police Department")) is None


def test_edge_row_is_none_without_evidence() -> None:
    edge = ReconciledEdge(
        from_org=A,
        to_org=B,
        access_kind="configured_access",
        valid_from_kind="unknown",
        corroborated=False,
        observations=(),
    )
    assert edge_row(edge) is None


# --- idempotency digest -----------------------------------------------------


def test_input_digest_is_deterministic() -> None:
    r1 = edge_row(_reconciled())
    r2 = edge_row(_reconciled())
    assert r1 is not None and r2 is not None
    assert r1["input_digest"] == r2["input_digest"]


def test_input_digest_changes_with_evidence_set() -> None:
    one = edge_row(_reconciled(claims=(CLAIM_1,)))
    two = edge_row(_reconciled(claims=(CLAIM_1, CLAIM_2)))
    assert one is not None and two is not None
    # A changed evidence set → a new digest → a superseding append-only row.
    assert one["input_digest"] != two["input_digest"]


def test_input_digest_differs_by_access_kind() -> None:
    ca = edge_row(_reconciled(kind="configured_access"))
    du = edge_row(_reconciled(kind="observed_use"))
    assert ca is not None and du is not None
    assert ca["input_digest"] != du["input_digest"]


# --- contradictions stay visible (reused P08.2 reconciler) ------------------


def test_asymmetry_is_surfaced_not_reconciled_away() -> None:
    # A says A->B (configured_access) but B does not reciprocate: the P08.2 reconciler
    # emits a SHARING_ASYMMETRY contradiction + task, and BOTH observations are kept.
    obs = [
        SharingObservation(
            asserted_by=A,
            from_org=A,
            to_org=B,
            access_kind="configured_access",
            observed_at=date(2026, 5, 1),
            claim_id=CLAIM_1,
        )
    ]
    result = reconcile_sharing(obs)
    assert len(result.edges) == 1  # the A->B edge is kept
    assert len(result.contradictions) == 1
    assert result.contradictions[0].contradiction_type == "sharing_asymmetry"
    assert len(result.tasks) == 1


# --- summary ----------------------------------------------------------------


def test_summary_accounts_for_every_edge() -> None:
    s = EdgeMaterializeSummary(
        considered_claims=4,
        observations=3,
        edges_reconciled=3,
        inserted=2,
        skipped_existing=0,
        skipped_unmapped=1,
        contradictions=1,
        asymmetry_tasks=1,
        by_access_kind={"configured_access": 2},
    )
    assert s.written == 2
    d = s.as_dict()
    assert d["inserted"] == 2 and d["skipped_unmapped"] == 1
    assert d["by_access_kind"] == {"configured_access": 2}


# --- read + materialize over a fake connection (accounting + idempotency) ---


class _FakeCursor:
    def __init__(self, rows: list[tuple[Any, ...]] | None, one: tuple[Any, ...] | None) -> None:
        self._rows = rows
        self._one = one

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._rows or []

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._one


class _FakeConn:
    """A minimal spine stand-in: canned sharing claims + an idempotent relationship store."""

    def __init__(self, claim_rows: list[tuple[Any, ...]]) -> None:
        self._claim_rows = claim_rows
        self.stored: dict[str, tuple[Any, ...]] = {}  # input_digest -> row params
        self.set_roles: list[str] = []

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> _FakeCursor:
        if sql.startswith("SET ROLE"):
            self.set_roles.append(sql)
            return _FakeCursor(None, None)
        if "FROM claim" in sql:
            return _FakeCursor(self._claim_rows, None)
        if "INSERT INTO relationship" in sql:
            digest = params[-1]
            if digest in self.stored:
                return _FakeCursor(None, None)  # ON CONFLICT DO NOTHING
            self.stored[digest] = params
            return _FakeCursor(None, (f"rel-{len(self.stored)}",))
        if "FROM relationship" in sql:
            out = []
            for i, p in enumerate(self.stored.values()):
                # (from,to,edge_type,access_kind,direction,valid_period-lower,vfk,vtk,
                #  asserted_by,observed_at,evidence_claim,input_digest) as inserted
                out.append(
                    (
                        p[0],
                        p[1],
                        p[2],
                        p[3],
                        p[4],
                        p[6],
                        p[7],
                        p[8],
                        date(2026, 5, 1),
                        p[10],
                        f"rel-{i + 1}",
                    )
                )
            return _FakeCursor(out, None)
        raise AssertionError(f"unexpected SQL: {sql}")


def _claim_row(claim_id: str, subject: str, partner: str, pred: str) -> tuple[Any, ...]:
    # matches read_sharing_observations SELECT column order.
    return (claim_id, subject, pred, partner, date(2026, 5, 1))


def test_read_sharing_observations_maps_and_skips_unclassifiable() -> None:
    conn = _FakeConn(
        [
            _claim_row(CLAIM_1, A, B, "configured_sharing_partner"),
            _claim_row(CLAIM_2, A, C, "active_device_count"),  # not a sharing kind → skipped
        ]
    )
    obs, considered = read_sharing_observations(conn)
    assert considered == 2
    assert len(obs) == 1
    o = obs[0]
    assert o.from_org == A and o.to_org == B and o.asserted_by == A
    assert o.access_kind == "configured_access"
    assert o.claim_id == CLAIM_1


def test_materialize_is_append_only_and_idempotent() -> None:
    conn = _FakeConn([_claim_row(CLAIM_1, A, B, "configured_sharing_partner")])
    first = materialize_sharing_edges(conn)
    assert first.inserted == 1
    assert first.by_access_kind == {"configured_access": 1}
    # Re-run over unchanged claims inserts +0 (idempotent).
    second = materialize_sharing_edges(conn)
    assert second.inserted == 0
    assert second.skipped_existing == 1
    # The materialized edge round-trips through the P28.5 read seam.
    edges = read_materialized_edges(conn)
    assert len(edges) == 1
    assert edges[0]["from_entity"] == A and edges[0]["access_kind"] == "configured_access"
    assert edges[0]["evidence_claim"] == CLAIM_1
