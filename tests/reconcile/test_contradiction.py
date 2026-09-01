# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The materialized Contradiction entity + lifecycle (§31, SIG-RECON-053..057).

Covers the P08.3 acceptance criteria: the entity's field set and identity; the
five-state lifecycle with ``accepted_unresolvable`` terminal; resolution that sets
status without deleting; the ``severity = blocking`` → ``UNRESOLVED`` (``U7``)
manual brake; ``unresolved_conflict`` being publishable (an open contradiction is
exposed, not hidden); and the detector→task contract across every detector.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest
from reconcile.contradiction import (
    DetectorTaskViolation,
    assert_detector_task_contract,
    derive_contradiction_id,
    detector_task_violations,
    forces_unresolved,
    materialize,
    open_blocking_contradictions,
    publishable_view,
)
from reconcile.model import (
    CONTRADICTION_STATUSES,
    OPEN_STATUSES,
    TERMINAL_STATUSES,
    Contradiction,
    ContradictionLifecycleError,
)
from reconcile.resolve import RESOLVE, Claim

AS_OF = date(2026, 9, 1)


def _con(**overrides: object) -> Contradiction:
    base: dict[str, object] = {
        "contradiction_type": "value_disagreement",
        "subject_id": "dep:okc",
        "predicate_id": "active_device_count",
        "claim_values": (38, 40),
        "note": "two sources disagree on the active count",
        "research_task_ids": ("task:1",),
    }
    base.update(overrides)
    return Contradiction(**base)  # type: ignore[arg-type]


# --- SIG-RECON-053: the materialized entity + its field set ------------------


def test_entity_has_the_full_field_set_and_identity() -> None:
    c = materialize(
        _con(severity="notable"),
        claim_ids=("claim:a", "claim:b"),
        contradiction_id="contradiction:pinned",
    )
    assert c.contradiction_id == "contradiction:pinned"
    assert c.claim_ids == ("claim:a", "claim:b")
    assert c.contradiction_type == "value_disagreement"
    assert c.subject_id == "dep:okc" and c.predicate_id == "active_device_count"
    assert c.severity == "notable" and c.status == "open"
    assert c.research_task_ids == ("task:1",)
    # resolution fields exist and start empty
    assert c.resolution_note is None and c.resolved_by is None and c.resolved_at is None


def test_materialized_identity_is_content_derived_and_idempotent() -> None:
    detected = _con()
    a = materialize(detected, claim_ids=("claim:a", "claim:b"))
    b = materialize(detected, claim_ids=("claim:b", "claim:a"))  # order-insensitive
    assert a.contradiction_id == b.contradiction_id == derive_contradiction_id(a)
    assert a.contradiction_id.startswith("contradiction:")


def test_invalid_severity_and_status_are_rejected() -> None:
    with pytest.raises(ValueError, match="severity"):
        _con(severity="catastrophic")
    with pytest.raises(ValueError, match="status"):
        _con(status="pending")


def test_the_lifecycle_vocab_matches_the_spec() -> None:
    assert CONTRADICTION_STATUSES == {
        "open",
        "under_research",
        "resolved",
        "accepted_unresolvable",
        "superseded",
    }
    assert OPEN_STATUSES == {"open", "under_research"}
    assert TERMINAL_STATUSES == {"resolved", "accepted_unresolvable", "superseded"}


# --- SIG-RECON-055: resolution sets status; it does NOT delete ---------------


def test_resolution_sets_status_and_does_not_delete() -> None:
    c = materialize(_con(), claim_ids=("claim:a", "claim:b"))
    resolved = c.resolve(
        note="portal export is dispositive", by="curator:jane", at=datetime(2026, 9, 2)
    )
    assert resolved.status == "resolved"
    assert resolved.resolution_note == "portal export is dispositive"
    assert resolved.resolved_by == "curator:jane"
    assert resolved.resolved_at == datetime(2026, 9, 2)
    # nothing deleted: the disagreeing claims, type, evidence and tasks remain visible
    assert resolved.claim_ids == ("claim:a", "claim:b")
    assert resolved.contradiction_type == "value_disagreement"
    assert resolved.research_task_ids == ("task:1",)
    # the original open record is untouched (append-only; new record returned)
    assert c.status == "open"


def test_resolved_contradiction_remains_visible_in_history() -> None:
    c = materialize(_con(), claim_ids=("claim:a",))
    history = [c, c.begin_research(), c.resolve(note="settled", by="curator:x")]
    # the resolved one is still present and still carries its identity + claims
    resolved = history[-1]
    assert resolved.status == "resolved"
    assert any(h.status == "resolved" for h in history)
    assert resolved.contradiction_id == c.contradiction_id


def test_resolve_requires_note_and_actor() -> None:
    c = _con()
    with pytest.raises(ValueError, match="resolution_note"):
        c.resolve(note="", by="curator:x")
    with pytest.raises(ValueError, match="resolved_by"):
        c.resolve(note="settled", by="")


# --- SIG-RECON-056: the lifecycle transitions + accepted_unresolvable --------


def test_open_flows_through_under_research_to_resolved() -> None:
    c = _con()
    assert c.status == "open" and c.is_open
    r = c.begin_research()
    assert r.status == "under_research" and r.is_open
    done = r.resolve(note="found the dispositive source", by="curator:x")
    assert done.status == "resolved" and done.is_terminal and not done.is_open


def test_accepted_unresolvable_is_a_legitimate_terminal_state() -> None:
    c = _con()
    accepted = c.accept_unresolvable(
        note="no source can settle this with available evidence", by="curator:x"
    )
    assert accepted.status == "accepted_unresolvable"
    assert accepted.is_terminal and not accepted.is_open
    # terminal: it cannot be re-opened or re-settled, only superseded by a new record
    with pytest.raises(ContradictionLifecycleError):
        accepted.begin_research()
    with pytest.raises(ContradictionLifecycleError):
        accepted.resolve(note="x", by="y")
    assert accepted.supersede().status == "superseded"


def test_illegal_transitions_are_refused() -> None:
    resolved = _con().resolve(note="settled", by="curator:x")
    with pytest.raises(ContradictionLifecycleError):
        resolved.begin_research()  # cannot research a settled contradiction
    with pytest.raises(ContradictionLifecycleError):
        _con(status="under_research").begin_research()  # only open -> under_research
    with pytest.raises(ContradictionLifecycleError):
        _con(status="superseded").supersede()  # already superseded


# --- SIG-RECON-054: severity=blocking forces UNRESOLVED (U7) -----------------


def _agreeing_claims() -> list[Claim]:
    """Two independent sources agreeing — this pair RESOLVES without a brake."""
    return [
        Claim(
            claim_id="claim:portal",
            subject_id="dep:okc",
            predicate_id="active_device_count",
            value=38,
            reliability="R2",
            integrity="I1",
            genre="portal_snapshot",
            observed_at=date(2026, 7, 1),
            source_id="src:portal",
            count_basis="active",
            structured_exact=True,
        ),
        Claim(
            claim_id="claim:minutes",
            subject_id="dep:okc",
            predicate_id="active_device_count",
            value=38,
            reliability="R2",
            integrity="I1",
            genre="council_minutes",
            observed_at=date(2026, 6, 15),
            source_id="src:council",
            count_basis="active",
        ),
    ]


def test_open_blocking_contradiction_forces_unresolved_u7() -> None:
    claims = _agreeing_claims()
    # sanity: without a brake the pair resolves
    baseline = RESOLVE(
        "dep:okc", "active_device_count", claims, as_of_world=AS_OF, as_of_belief=AS_OF
    )
    assert baseline.resolution_status == "RESOLVED"

    blocking = materialize(
        _con(severity="blocking", note="curator believes this is unsafe to publish"),
        claim_ids=("claim:portal", "claim:minutes"),
    )
    assert forces_unresolved([blocking], subject_id="dep:okc", predicate_id="active_device_count")
    braked = RESOLVE(
        "dep:okc",
        "active_device_count",
        claims,
        as_of_world=AS_OF,
        as_of_belief=AS_OF,
        blocking_contradiction=forces_unresolved(
            [blocking], subject_id="dep:okc", predicate_id="active_device_count"
        ),
    )
    assert braked.resolution_status == "UNRESOLVED"
    assert braked.unresolved_code == "U7"
    # the brake stops publication without deleting the value: it is retained as last-known
    assert braked.last_known_value == 38


def test_brake_only_bites_for_open_blocking_on_the_same_pair() -> None:
    blocking = materialize(_con(severity="blocking"), claim_ids=("c",))
    # resolved blocking no longer brakes (SIG-RECON-054 is about the OPEN brake)
    resolved = blocking.resolve(note="cleared", by="curator:x")
    assert not forces_unresolved(
        [resolved], subject_id="dep:okc", predicate_id="active_device_count"
    )
    # a non-blocking open contradiction does not brake
    notable = materialize(_con(severity="notable"), claim_ids=("c",))
    assert not forces_unresolved(
        [notable], subject_id="dep:okc", predicate_id="active_device_count"
    )
    # a blocking contradiction on a DIFFERENT pair does not brake this one
    assert not forces_unresolved(
        [blocking], subject_id="dep:okc", predicate_id="contracted_device_count"
    )
    assert open_blocking_contradictions(
        [blocking], subject_id="dep:okc", predicate_id="active_device_count"
    ) == (blocking,)


# --- SIG-RECON-055 / AC1: unresolved_conflict is publishable -----------------


def test_open_contradiction_is_published_as_unresolved_conflict_not_suppressed() -> None:
    open_c = materialize(_con(), claim_ids=("claim:a",))
    resolved_c = materialize(_con(subject_id="dep:tulsa"), claim_ids=("claim:z",)).resolve(
        note="settled", by="curator:x"
    )
    view = publishable_view([open_c, resolved_c])
    # BOTH are exposed — nothing is hidden — and the open one surfaces as a conflict
    assert len(view) == 2
    states = {v["subject_id"]: v["contradiction_state"] for v in view}
    assert states["dep:okc"] == "unresolved_conflict"
    assert states["dep:tulsa"] == "resolved"
    # the projection carries the identity, claims and tasks a read surface needs
    okc = next(v for v in view if v["subject_id"] == "dep:okc")
    assert okc["contradiction_id"] == open_c.contradiction_id
    assert okc["claim_ids"] == ["claim:a"]
    assert okc["research_task_ids"] == ["task:1"]


def test_resolution_contradiction_state_exposes_open_conflict() -> None:
    # The resolver already surfaces an open conflict on the resolution itself.
    a = Claim(
        claim_id="a",
        subject_id="dep:x",
        predicate_id="active_device_count",
        value=38,
        reliability="R2",
        integrity="I1",
        genre="portal_snapshot",
        observed_at=date(2026, 7, 1),
        source_id="src:a",
        count_basis="active",
    )
    b = Claim(
        claim_id="b",
        subject_id="dep:x",
        predicate_id="active_device_count",
        value=52,
        reliability="R2",
        integrity="I1",
        genre="portal_snapshot",
        observed_at=date(2026, 7, 1),
        source_id="src:b",
        count_basis="active",
    )
    r = RESOLVE("dep:x", "active_device_count", [a, b], as_of_world=AS_OF, as_of_belief=AS_OF)
    assert r.resolution_status == "UNRESOLVED"
    assert r.contradiction_state == "unresolved_conflict"


# --- SIG-RECON-057: the detector→task contract -------------------------------


def test_detector_task_contract_helper_flags_a_taskless_contradiction() -> None:
    taskless = _con(research_task_ids=())
    assert detector_task_violations([taskless], []) == [
        "value_disagreement on dep:okc/active_device_count: emits no research task (SIG-RECON-057)"
    ]
    with pytest.raises(DetectorTaskViolation):
        assert_detector_task_contract([taskless], [])


def test_detector_task_contract_flags_dangling_or_empty_closing_condition() -> None:
    from reconcile.model import ResearchTask

    dangling = _con(research_task_ids=("task:missing",))
    assert any("not among emitted tasks" in v for v in detector_task_violations([dangling], []))

    empty = _con(research_task_ids=("task:1",))
    bad_task = ResearchTask(
        task_id="task:1",
        task_type="t",
        subject_id="dep:okc",
        closing_condition="",
        detector_version="v",
    )
    assert any(
        "empty closing_condition" in v for v in detector_task_violations([empty], [bad_task])
    )
