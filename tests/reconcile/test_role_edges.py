# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Unit tests for the P35.26 role-edge succession model (no Postgres).

The real-spine round-trip (sqitch deploy, append-only supersession, the
epoch-zero CHECKs, ``operator_state``) lives in
``tests/db/test_role_edges.py``; these tests pin the pure model — lineage
episodes, the undated-marker mapping, and digest stability — so a regression
in the succession math fails fast without a container.
"""

from __future__ import annotations

from datetime import UTC, datetime

from db.organization_roles import (
    ABSENCE_PREDICATES,
    EDGE_ROLE_VOCABULARY,
    ENTITY_REF_ROLES,
    ROLE_OF_PREDICATE,
    SPEC_12_4_ROLES,
    UNKNOWN_ROLE_STATES,
    UNKNOWN_STATE_FOR_ROLE,
    OrganizationRole,
    role_slot,
)
from reconcile.materialize import (
    _desired_role_rows,
    _episodes,
    _role_edge_input_digest,
    _RoleClaim,
)

SUBJ = "00000000-0000-0000-0000-0000000000aa"
ORG_A = "00000000-0000-0000-0000-0000000000b1"
ORG_B = "00000000-0000-0000-0000-0000000000c2"
C1 = "00000000-0000-0000-0000-000000000011"
C2 = "00000000-0000-0000-0000-000000000022"
C3 = "00000000-0000-0000-0000-000000000033"

_T0 = datetime(2026, 1, 1, tzinfo=UTC)
_T1 = datetime(2026, 6, 1, tzinfo=UTC)
_T2 = datetime(2026, 9, 1, tzinfo=UTC)


def _claim(
    claim_id: str,
    state: tuple[str, str | None],
    *,
    order_dt: datetime,
    evid_dt: datetime | None = None,
    lineage: str = "L1",
    role: str = "operator",
    revises_claim: str | None = None,
    retraction_of: str | None = None,
) -> _RoleClaim:
    return _RoleClaim(
        claim_id=claim_id,
        subject_id=SUBJ,
        slot="operator",
        state=state,
        role=role,
        order_dt=order_dt,
        evid_dt=evid_dt if evid_dt is not None else order_dt,
        valid_upper=None,
        observed_at=evid_dt,
        asserted_by=None,
        revises_claim=revises_claim,
        retraction_of=retraction_of,
        lineage=lineage,
    )


# --- taxonomy: slots + vocabulary -------------------------------------------- #


def test_operator_and_unknown_share_one_slot() -> None:
    # The explicit unknown competes for the operator slot — a later operator
    # edge supersedes the marker and vice versa (SIG-ONTO-028).
    assert role_slot("operator") == role_slot("operator_unknown") == "operator"
    assert role_slot("vendor") == "vendor"


def test_unknown_markers_are_absence_derived() -> None:
    assert ABSENCE_PREDICATES == {"operator_absent": OrganizationRole.OPERATOR}
    assert UNKNOWN_STATE_FOR_ROLE == {OrganizationRole.OPERATOR: "operator_unknown"}
    assert UNKNOWN_ROLE_STATES == {"operator_unknown"}


def test_provenance_predicates_never_map_to_entity_ref_roles() -> None:
    # The recorded defect made structural: every provenance-role predicate is
    # outside the edge-bearing role set.
    for pred in ("camera_registry_publisher", "published_by", "listed_by"):
        role = ROLE_OF_PREDICATE.get(pred)
        assert role is OrganizationRole.PUBLISHER
        assert role not in ENTITY_REF_ROLES


def test_the_edge_vocabulary_is_the_union() -> None:
    assert "operator_unknown" in EDGE_ROLE_VOCABULARY
    assert "maintainer" in EDGE_ROLE_VOCABULARY
    # Every §12.4 name and every enum role is admitted.
    assert SPEC_12_4_ROLES <= EDGE_ROLE_VOCABULARY
    assert {r.value for r in OrganizationRole} <= EDGE_ROLE_VOCABULARY


# --- episodes: within-lineage succession -------------------------------------- #


def test_same_lineage_state_change_closes_the_prior_episode() -> None:
    claims = [
        _claim(C1, ("actor", ORG_A), order_dt=_T0),
        _claim(C2, ("actor", ORG_B), order_dt=_T1),
    ]
    eps = _episodes(claims)
    assert len(eps) == 2
    first, second = eps[0], eps[1]
    assert first.close_dt == _T1
    assert first.close_claim == C2  # the succeeding claim names itself
    assert second.close_dt is None


def test_same_state_claims_extend_one_episode() -> None:
    claims = [
        _claim(C1, ("actor", ORG_A), order_dt=_T0),
        _claim(C2, ("actor", ORG_A), order_dt=_T1),
    ]
    eps = _episodes(claims)
    assert len(eps) == 1
    assert eps[0].close_dt is None
    assert {c.claim_id for c in eps[0].claims} == {C1, C2}


def test_absence_then_operator_closes_the_unknown_episode() -> None:
    claims = [
        _claim(C1, ("unknown", None), order_dt=_T0, role="operator_unknown"),
        _claim(C2, ("actor", ORG_A), order_dt=_T1),
    ]
    eps = _episodes(claims)
    assert eps[0].state == ("unknown", None)
    assert eps[0].close_dt == _T1
    assert eps[0].close_claim == C2


def test_cross_lineage_states_stay_concurrent() -> None:
    claims = [
        _claim(C1, ("actor", ORG_A), order_dt=_T0, lineage="L1"),
        _claim(C2, ("actor", ORG_B), order_dt=_T1, lineage="L2"),
    ]
    eps = _episodes(claims)
    # Distinct voices: neither closes the other (§3.1 — kept visible).
    assert all(ep.close_dt is None for ep in eps)


def test_revises_claim_closes_the_revised_episode() -> None:
    claims = [
        _claim(C1, ("actor", ORG_A), order_dt=_T0, lineage="L1"),
        _claim(C2, ("actor", ORG_B), order_dt=_T1, lineage="L2", revises_claim=C1),
    ]
    eps = _episodes(claims)
    revised = next(ep for ep in eps if ep.state == ("actor", ORG_A))
    assert revised.close_dt == _T1
    assert revised.close_claim == C2


def test_an_older_correction_does_not_close_a_newer_state() -> None:
    claims = [
        _claim(C1, ("actor", ORG_A), order_dt=_T1, lineage="L1"),
        # The "correction" pre-dates the claim it names — corrects nothing.
        _claim(C2, ("actor", ORG_B), order_dt=_T0, lineage="L2", revises_claim=C1),
    ]
    eps = _episodes(claims)
    revised = next(ep for ep in eps if ep.state == ("actor", ORG_A))
    assert revised.close_dt is None


# --- desired rows: undated + merged open states ------------------------------- #


def test_undated_claim_produces_undated_row() -> None:
    claims = [
        _RoleClaim(
            claim_id=C1,
            subject_id=SUBJ,
            slot="operator",
            state=("actor", ORG_A),
            role="operator",
            order_dt=_T0,  # ordering falls back to sys time…
            evid_dt=None,  # …but the EVIDENCED bound stays absent
            valid_upper=None,
            observed_at=None,
            asserted_by=None,
            revises_claim=None,
            retraction_of=None,
            lineage="L1",
        )
    ]
    rows = _desired_role_rows(SUBJ, "operator", claims)
    assert len(rows) == 1
    row = rows[0]
    assert row["valid_lower"] is None
    assert row["valid_from_kind"] == "undated"  # explicit, never an epoch
    assert row["valid_to_kind"] == "ongoing"
    assert row["observed_at"] is None
    assert row["actor_id"] == ORG_A
    assert row["evidence_claims"] == [C1]


def test_unknown_state_maps_to_the_marker_role() -> None:
    claims = [_claim(C1, ("unknown", None), order_dt=_T0, role="operator_unknown")]
    rows = _desired_role_rows(SUBJ, "operator", claims)
    assert len(rows) == 1
    assert rows[0]["role"] == "operator_unknown"
    assert rows[0]["actor_id"] is None


def test_open_same_state_episodes_merge_across_lineages() -> None:
    claims = [
        _claim(C1, ("actor", ORG_A), order_dt=_T0, lineage="L1"),
        _claim(C2, ("actor", ORG_A), order_dt=_T1, lineage="L2"),
        _claim(C3, ("actor", ORG_B), order_dt=_T1, lineage="L3"),
    ]
    rows = _desired_role_rows(SUBJ, "operator", claims)
    assert len(rows) == 2
    merged = next(r for r in rows if r["actor_id"] == ORG_A)
    assert merged["evidence_claims"] == [C1, C2]  # corroborated across voices


def test_closed_episode_links_its_timeline_successor() -> None:
    claims = [
        _claim(C1, ("actor", ORG_A), order_dt=_T0),
        _claim(C2, ("actor", ORG_B), order_dt=_T1),
        _claim(C3, ("actor", ORG_A), order_dt=_T2),
    ]
    rows = _desired_role_rows(SUBJ, "operator", claims)
    # A→B→A: three episodes, B closed at T2, open A linked to B's row.
    assert len(rows) == 3
    open_row = next(r for r in rows if r["valid_to_kind"] == "ongoing")
    closed_b = next(r for r in rows if r["actor_id"] == ORG_B and r["valid_to_kind"] != "ongoing")
    assert open_row["_chain_pred"] is closed_b
    assert closed_b["superseded_by_claim"] == C3


def test_digest_changes_with_evidence_and_stability() -> None:
    claims = [_claim(C1, ("actor", ORG_A), order_dt=_T0)]
    row1 = _desired_role_rows(SUBJ, "operator", claims)[0]
    row2 = _desired_role_rows(SUBJ, "operator", claims)[0]
    assert row1["input_digest"] == row2["input_digest"]  # deterministic
    claims2 = claims + [_claim(C2, ("actor", ORG_A), order_dt=_T1)]
    row3 = _desired_role_rows(SUBJ, "operator", claims2)[0]
    # A changed evidence set → a distinct digest → belief supersession lands.
    assert row3["input_digest"] != row1["input_digest"]
    assert row3["evidence_claims"] == [C1, C2]


def test_digest_keys_every_temporal_input() -> None:
    row = {
        "entity_id": SUBJ,
        "actor_id": ORG_A,
        "role": "operator",
        "valid_lower": _T0,
        "valid_upper": None,
        "valid_from_kind": "exact",
        "valid_to_kind": "ongoing",
        "observed_at": _T0,
        "asserted_by": None,
        "superseded_by_claim": None,
        "evidence_claims": [C1],
    }
    base = _role_edge_input_digest(row)
    assert _role_edge_input_digest(row) == base
    changed = dict(row, valid_from_kind="undated")
    assert _role_edge_input_digest(changed) != base
