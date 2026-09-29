# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P29.2 — the detector run over the materialized graph → the research queue.

These prove the pure orchestration (`tasks.detect`): the §33.2 catalog is run over the
Round-6 materialized detector outputs (contradictions/coverage/edges) to mint a deduped,
rate-limited, trigger-citing research queue, and statute-templated records requests are
DRAFTED, never sent. The DB persistence is proven over real PG in
`tests/db/test_research_queue_materialize.py`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tasks.catalog import CONTRADICTION_TASK_MAP
from tasks.detect import (
    JurisdictionInfo,
    MaterializedInputs,
    records_request_drafts,
    run_detectors,
)
from tasks.geographic import GeographicQueue
from tasks.lifecycle import RateLimiter
from tasks.vocabulary import AssigneeClass

NOW = datetime(2026, 9, 23, 12, 0, 0, tzinfo=UTC)


def _contradiction(
    cid: str, subject: str, ctype: str, *, status: str = "open", severity: str = "notable"
) -> dict:
    return {
        "contradiction_id": cid,
        "subject_id": subject,
        "predicate_id": "retention_days",
        "contradiction_type": ctype,
        "status": status,
        "severity": severity,
        "claim_ids": ["claimA", "claimB"],
    }


def _coverage(
    cid: str,
    subject: str,
    predicate: str,
    *,
    absence: str = "not_researched",
    jurisdiction: str | None = "jur1",
) -> dict:
    return {
        "coverage_id": cid,
        "subject_id": subject,
        "subject_class": None,
        "jurisdiction_id": jurisdiction,
        "predicate_id": predicate,
        "absence_kind": absence,
    }


def _edge(
    rid: str, subject: str, *, valid_from: str, access_kind: str = "configured_access"
) -> dict:
    return {
        "relationship_id": rid,
        "from_entity": subject,
        "to_entity": "other",
        "access_kind": access_kind,
        "valid_from": valid_from,
    }


def _ok_resolver(_subject: str | None, _jurisdiction: str | None) -> JurisdictionInfo:
    return JurisdictionInfo(records_law_key="OK", target_agency="Oklahoma City PD")


# --- deliverable 1: detectors → research queue -------------------------------


def test_open_contradiction_generates_its_mapped_catalog_task() -> None:
    # SIG-TASK-004: every §31 contradiction_type routes to the task that resolves it.
    res = run_detectors(
        MaterializedInputs(contradictions=[_contradiction("c1", "s1", "value_disagreement")]),
        now=NOW,
    )
    assert len(res.queue) == 1
    task = res.queue[0]
    assert task.task_type == CONTRADICTION_TASK_MAP["value_disagreement"]
    assert task.subject_id == "s1"


def test_every_contradiction_type_is_routable() -> None:
    rows = [
        _contradiction(f"c{i}", f"s{i}", ctype)
        for i, ctype in enumerate(sorted(CONTRADICTION_TASK_MAP))
    ]
    res = run_detectors(MaterializedInputs(contradictions=rows), now=NOW)
    assert res.summary.unroutable == 0
    assert res.summary.generated == len(rows)


def test_settled_contradiction_generates_no_task() -> None:
    res = run_detectors(
        MaterializedInputs(
            contradictions=[_contradiction("c1", "s1", "value_disagreement", status="superseded")]
        ),
        now=NOW,
    )
    assert res.queue == []


def test_coverage_gap_routes_records_obtainable_vs_field() -> None:
    res = run_detectors(
        MaterializedInputs(
            coverage=[
                _coverage("cov1", "s1", "procurement_contract"),  # records-obtainable
                _coverage("cov2", "s2", "device_count", absence="searched_not_found"),  # field
            ]
        ),
        now=NOW,
    )
    by = res.summary.by_task_type
    assert by.get("missing_contract") == 1
    assert by.get("coverage_hole") == 1


def test_non_gap_coverage_row_generates_nothing() -> None:
    res = run_detectors(
        MaterializedInputs(coverage=[_coverage("cov1", "s1", "x", absence="not_applicable")]),
        now=NOW,
    )
    assert res.queue == []


def test_stale_edge_generates_renewal_fresh_edge_does_not() -> None:
    res = run_detectors(
        MaterializedInputs(
            edges=[
                _edge("r1", "s1", valid_from="2025-01-01T00:00:00+00:00"),  # >180d stale
                _edge("r2", "s2", valid_from=(NOW - timedelta(days=10)).isoformat()),  # fresh
            ]
        ),
        now=NOW,
    )
    assert [t.task_type for t in res.queue] == ["sharing_snapshot_stale"]
    assert res.queue[0].subject_id == "s1"


# --- cross-cutting: every generated task cites its trigger --------------------


def test_every_generated_task_cites_its_trigger() -> None:
    res = run_detectors(
        MaterializedInputs(
            contradictions=[_contradiction("c1", "s1", "value_disagreement")],
            coverage=[_coverage("cov1", "s2", "procurement_contract")],
            edges=[_edge("r1", "s3", valid_from="2025-01-01T00:00:00+00:00")],
        ),
        now=NOW,
    )
    assert res.queue, "expected a non-empty queue"
    for task in res.queue:
        assert task.trigger_kind in {"contradiction", "coverage", "relationship"}
        assert task.trigger_ref  # non-empty
    trg = {t.trigger_ref for t in res.queue}
    assert trg == {"c1", "cov1", "r1"}


# --- anti-abuse: dedup + rate limit ------------------------------------------


def test_duplicate_task_type_subject_is_suppressed() -> None:
    # SIG-TASK-007: at most one task per (task_type, subject).
    res = run_detectors(
        MaterializedInputs(
            contradictions=[
                _contradiction("c1", "s1", "value_disagreement"),
                _contradiction("c2", "s1", "value_disagreement"),  # same (type, subject)
            ]
        ),
        now=NOW,
    )
    assert res.summary.generated == 1
    assert res.summary.deduplicated == 1


def test_per_subject_rate_limit_caps_generation() -> None:
    # SIG-TASK-013: one badly-modelled subject cannot flood the queue. Distinct task types
    # on one subject, capped at 2 generations/window.
    rows = [
        _contradiction("c1", "s1", "value_disagreement"),  # -> conflicting_retention
        _contradiction("c2", "s1", "identity_ambiguity"),  # -> candidate_duplicate_entities
        _contradiction("c3", "s1", "sharing_asymmetry"),  # -> sharing_asymmetry
    ]
    limiter = RateLimiter(max_per_window=2, window=timedelta(hours=1))
    res = run_detectors(MaterializedInputs(contradictions=rows), now=NOW, rate_limiter=limiter)
    assert res.summary.generated == 2
    assert res.summary.rate_limited == 1


# --- geo queues (§33.5): priority, never exclusivity -------------------------


def test_geographic_queue_orders_without_gatekeeping() -> None:
    res = run_detectors(
        MaterializedInputs(
            coverage=[
                _coverage(
                    "cov1", "s1", "device_count", absence="not_researched", jurisdiction="jurA"
                ),
                _coverage(
                    "cov2", "s2", "device_count", absence="not_researched", jurisdiction="jurB"
                ),
            ]
        ),
        now=NOW,
    )
    queue = res.queue
    gq = GeographicQueue()
    gq.claim(jurisdiction_id="jurB", group_id="grp", now=NOW, ttl=timedelta(days=30))
    ordered = gq.order_for_group(queue, group_id="grp", now=NOW)
    # The claimed jurisdiction sorts first — but every task remains workable (nothing filtered).
    assert ordered[0].jurisdiction_id == "jurB"
    assert len(ordered) == len(queue)


# --- deliverable 2: records requests are DRAFTED, never sent ------------------


def test_records_requests_are_drafted_statute_templated_never_sent() -> None:
    res = run_detectors(
        MaterializedInputs(
            contradictions=[_contradiction("c1", "s1", "value_disagreement")],  # records_requester
        ),
        now=NOW,
        jurisdiction_resolver=_ok_resolver,
    )
    assert res.summary.records_request_drafts == 1
    assert res.summary.as_dict()["records_requests_sent"] == 0
    draft = res.drafts[0]
    assert draft.status == "drafted"  # NEVER "sent"
    assert draft.statutory_citation  # a real statute citation was selected
    # The filer is left for the contributor who files it — SIG fabricates no consent.
    assert "the contributor who files this request" in draft.draft_body
    # No transmit/send affordance exists on the draft.
    assert not hasattr(draft, "send")
    assert not hasattr(draft, "transmit")


def test_only_records_oriented_tasks_draft_requests() -> None:
    # A coverage_hole (local_group) drafts nothing; a records_requester task does.
    res = run_detectors(
        MaterializedInputs(
            coverage=[
                _coverage("cov1", "s1", "device_count", absence="not_researched")
            ],  # coverage_hole
        ),
        now=NOW,
        jurisdiction_resolver=_ok_resolver,
    )
    assert all(t.spec.assignee_class == AssigneeClass.LOCAL_GROUP for t in res.queue)
    assert res.drafts == []


def test_residency_restricted_jurisdiction_routes_to_local_filers() -> None:
    # SIG-TASK-016a/b: a restricted state's draft carries a routing note, not an invalid request.
    def va(_s, _j):
        return JurisdictionInfo(records_law_key="VA", target_agency="Fairfax County PD")

    res = run_detectors(
        MaterializedInputs(contradictions=[_contradiction("c1", "s1", "value_disagreement")]),
        now=NOW,
        jurisdiction_resolver=va,
    )
    assert res.summary.residency_routed_drafts == 1
    assert res.drafts[0].residency_restricted is True
    assert "resident" in res.drafts[0].routing_note.lower()


def test_no_resolver_means_no_drafts() -> None:
    res = run_detectors(
        MaterializedInputs(contradictions=[_contradiction("c1", "s1", "value_disagreement")]),
        now=NOW,
    )
    assert res.drafts == []
    assert res.summary.records_request_drafts == 0


def test_unmapped_jurisdiction_yields_task_but_no_draft() -> None:
    res = run_detectors(
        MaterializedInputs(contradictions=[_contradiction("c1", "s1", "value_disagreement")]),
        now=NOW,
        jurisdiction_resolver=lambda _s, _j: None,  # cannot resolve
    )
    assert len(res.queue) == 1  # the task is still queued
    assert res.drafts == []  # but no records request is drafted


def test_records_drafts_helper_matches_run() -> None:
    res = run_detectors(
        MaterializedInputs(contradictions=[_contradiction("c1", "s1", "value_disagreement")]),
        now=NOW,
    )
    drafts = records_request_drafts(res.queue, jurisdiction_resolver=_ok_resolver)
    assert len(drafts) == 1


# --- honest degrade ----------------------------------------------------------


def test_empty_inputs_yield_empty_queue() -> None:
    res = run_detectors(MaterializedInputs(), now=NOW, jurisdiction_resolver=_ok_resolver)
    assert res.queue == []
    assert res.drafts == []
    assert res.summary.generated == 0
