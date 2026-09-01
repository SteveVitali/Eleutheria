# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Sharing-edge reconciliation (§29.3, SIG-RECON-034/035/036/037)."""

from __future__ import annotations

from datetime import date

import pytest
from reconcile.model import SHARING_ASYMMETRY
from reconcile.sharing import (
    ACCESS_KINDS,
    L1InferenceForbidden,
    SharingObservation,
    infer_access_from_use,
    reconcile_sharing,
)

WHEN = date(2026, 7, 1)


def _obs(asserted_by: str, frm: str, to: str, kind: str, **kw: object) -> SharingObservation:
    return SharingObservation(
        asserted_by=asserted_by, from_org=frm, to_org=to, access_kind=kind, observed_at=WHEN, **kw
    )


def test_the_three_edge_types_are_reconciled_separately() -> None:
    # SIG-RECON-034: the three edge types are never merged.
    assert set(ACCESS_KINDS) == {"configured_access", "observed_use", "declared_policy"}
    obs = [
        _obs("org:a", "org:a", "org:b", "configured_access"),
        _obs("org:a", "org:a", "org:b", "observed_use"),
    ]
    rec = reconcile_sharing(obs)
    kinds = {e.access_kind for e in rec.edges}
    assert kinds == {"configured_access", "observed_use"}
    # Each edge is scoped to a single kind; there is no merged edge.
    assert all(e.access_kind in ACCESS_KINDS for e in rec.edges)


def test_asymmetry_is_a_finding_not_a_merge() -> None:
    # SIG-RECON-035: A's export lists B, B's export does not list A.
    obs = [_obs("org:a", "org:a", "org:b", "configured_access")]
    rec = reconcile_sharing(obs)
    assert len(rec.contradictions) == 1
    con = rec.contradictions[0]
    assert con.contradiction_type == SHARING_ASYMMETRY
    # a research task is generated and linked
    assert len(rec.tasks) == 1
    assert rec.tasks[0].task_id in con.research_task_ids
    # both observations retained, nothing merged away
    assert rec.edges[0].corroborated is False


def test_reciprocated_edge_has_no_asymmetry() -> None:
    obs = [
        _obs("org:a", "org:a", "org:b", "configured_access"),
        _obs("org:b", "org:b", "org:a", "configured_access"),
    ]
    rec = reconcile_sharing(obs)
    assert rec.contradictions == ()
    a_to_b = next(e for e in rec.edges if (e.from_org, e.to_org) == ("org:a", "org:b"))
    assert a_to_b.corroborated is True


def test_single_snapshot_edge_carries_unknown_valid_from_kind() -> None:
    # SIG-RECON-036: no start date inferred from first observation.
    obs = [_obs("org:a", "org:a", "org:b", "configured_access", from_single_snapshot=True)]
    rec = reconcile_sharing(obs)
    assert rec.edges[0].valid_from_kind == "unknown"


def test_multi_snapshot_edge_can_have_known_start() -> None:
    obs = [
        _obs("org:a", "org:a", "org:b", "configured_access", from_single_snapshot=False),
        _obs("org:b", "org:b", "org:a", "configured_access", from_single_snapshot=False),
    ]
    rec = reconcile_sharing(obs)
    assert rec.edges[0].valid_from_kind == "known"


def test_observed_use_does_not_create_configured_access_at_l1() -> None:
    # SIG-RECON-037: use->access inference is L4-only, clearly labelled.
    obs = [
        _obs("org:a", "org:a", "org:b", "observed_use"),
        _obs("org:b", "org:b", "org:a", "observed_use"),
    ]
    rec = reconcile_sharing(obs)
    # no configured_access edge is materialized at L1 from the observed_use edges
    assert all(e.access_kind == "observed_use" for e in rec.edges)
    use_edge = rec.edges[0]
    inf = infer_access_from_use(use_edge)
    assert inf.layer == "L4"
    assert inf.confidence == "probable"
    assert inf.value["access_kind"] == "configured_access"  # type: ignore[index]


def test_infer_access_rejects_non_use_edges() -> None:
    obs = [
        _obs("org:a", "org:a", "org:b", "configured_access"),
        _obs("org:b", "org:b", "org:a", "configured_access"),
    ]
    rec = reconcile_sharing(obs)
    with pytest.raises(L1InferenceForbidden):
        infer_access_from_use(rec.edges[0])


def test_unknown_access_kind_is_rejected() -> None:
    with pytest.raises(ValueError, match="access_kind"):
        _obs("org:a", "org:a", "org:b", "telepathy")
