# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Records-request generation, residency routing, consent, coverage (§36).

The three ticket ACs live here:
* AC1 (SIG-TASK-015): the emitted request cites the correct statute for the target.
* AC2 (SIG-TASK-016a/016b): a residency-restricted jurisdiction with a non-resident
  (or unknown-residency) filer refuses to emit, routes to the geographic queue, and
  records the constraint as a coverage fact — instead of emitting a doomed request.
* AC3 (SIG-TASK-009 via the records path): a no-responsive-records reply writes a
  `CoverageRecord`.
Plus the consent gate (SIG-TASK-018) and the reference-table edge cases.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from inference.coverage import CoverageRecord
from tasks.geographic import GeographicQueue
from tasks.groups import LocalGroup, LocalGroupRegistry
from tasks.lifecycle import ResearchTask, TaskPool
from tasks.records_request import (
    ConsentNotGrantedError,
    Filer,
    GeneratedRecordsRequest,
    RecordsRequestGenerator,
    ResearchGap,
    ResidencyStatus,
    UnknownJurisdictionError,
    record_no_responsive_records,
    records_law_for,
    residency_barrier_coverage,
)
from tasks.spec import Detector, GeographicScope, TaskType
from tasks.vocabulary import AssigneeClass, Disposition, EffortEstimate, TaskStatus

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _gap(jurisdiction_id: str, record_type: str = "alpr_contract") -> ResearchGap:
    return ResearchGap(
        predicate_id="contracted_device_count",
        jurisdiction_id=jurisdiction_id,
        target_agency="Example County Sheriff",
        records_contact="foia@example.gov",
        record_type=record_type,
        subject_id="agency:example",
    )


def _consenting(residency: ResidencyStatus) -> Filer:
    return Filer(
        filer_id="u1",
        display_name="Jane Doe",
        residency_status=residency,
        consent_granted=True,
        acknowledged_public_act=True,
    )


# --- AC1: emit with the correct statute (SIG-TASK-015) ------------------------


@pytest.mark.parametrize(
    ("jurisdiction_id", "record_type"),
    [
        ("CA", "alpr_contract"),
        ("NY", "camera_deployment"),
        ("TX", "surveillance_policy"),
        ("IL", "drone_program"),
        ("WA", "face_recognition"),
    ],
)
def test_emits_the_correct_statute_for_the_jurisdiction(
    jurisdiction_id: str, record_type: str
) -> None:
    """AC1 / SIG-TASK-015: the emitted citation matches the reference table."""
    gen = RecordsRequestGenerator()
    result = gen.generate(_gap(jurisdiction_id, record_type), _consenting(ResidencyStatus.RESIDENT))
    assert result.was_emitted
    request = result.emitted
    assert request is not None
    law = records_law_for(jurisdiction_id)
    assert request.statutory_citation == law.citation
    assert request.statute_name == law.statute
    assert law.citation in request.request_text
    assert law.statute in request.request_text


def test_emitted_request_carries_the_sig_task_015_surface() -> None:
    """SIG-TASK-015: agency + records contact, statute, proven language, records sought."""
    gen = RecordsRequestGenerator()
    result = gen.generate(_gap("CA"), _consenting(ResidencyStatus.RESIDENT), now=_NOW)
    request = result.emitted
    assert isinstance(request, GeneratedRecordsRequest)
    assert request.target_agency == "Example County Sheriff"
    assert request.records_contact == "foia@example.gov"
    assert request.records_sought  # the specific records sought
    assert request.records_sought in request.request_text
    assert request.target_agency in request.request_text
    # provenance: the versions are stamped (§20).
    assert request.template_version
    assert request.template_set_version
    assert request.table_version
    assert request.generated_at == _NOW


# --- AC2: residency is operationally binding (SIG-TASK-016a/016b) -------------


def test_non_resident_in_restricted_jurisdiction_refuses_routes_and_records_coverage() -> None:
    """AC2 / SIG-TASK-016a: refuse to emit, route to the queue, record a coverage fact."""
    gen = RecordsRequestGenerator()
    registry = LocalGroupRegistry()
    registry.register(
        LocalGroup("g1", "Virginia Cop Watch", "VA", "https://example.org", "team@example.org")
    )
    queue = GeographicQueue()
    queue.claim(jurisdiction_id="VA", group_id="g1", now=_NOW, ttl=timedelta(days=30))

    result = gen.generate(
        _gap("VA"),
        Filer("u2", "Out-of-Stater", ResidencyStatus.NON_RESIDENT),
        registry=registry,
        queue=queue,
        now=_NOW,
    )

    # 1. Refused to emit.
    assert not result.was_emitted
    assert result.emitted is None
    block = result.residency_block
    assert block is not None

    # 2. Routed to the jurisdiction's local filers (the load-bearing registry) and
    #    the active claimant group in the geographic queue (§33.5).
    assert [g.group_id for g in block.local_filers] == ["g1"]
    assert block.claimant_groups == frozenset({"g1"})

    # 3. The constraint is recorded as a coverage fact — attributed to the legal
    #    barrier, NOT read as "searched and found nothing" (§9.5/§32.2).
    cov = block.coverage
    assert isinstance(cov, CoverageRecord)
    assert cov.absence_kind == "not_researched"
    assert cov.absence_kind != "searched_not_found"
    assert cov.jurisdiction_id == "VA"
    assert cov.subject_id == "agency:example"
    assert cov.search_method == "residency_barrier:Va. Code § 2.2-3700"


def test_unknown_residency_defaults_to_restrictive() -> None:
    """SIG-TASK-016b: unknown residency defaults to routing, never assumes openness."""
    gen = RecordsRequestGenerator()
    result = gen.generate(_gap("TN"), Filer("u3", "Unclear", ResidencyStatus.UNKNOWN))
    assert not result.was_emitted
    block = result.residency_block
    assert block is not None
    assert block.residency_status is ResidencyStatus.UNKNOWN
    assert block.coverage.absence_kind == "not_researched"


def test_resident_in_restricted_jurisdiction_emits() -> None:
    """A confirmed resident is a valid filer even in a restricted jurisdiction."""
    gen = RecordsRequestGenerator()
    result = gen.generate(_gap("VA"), _consenting(ResidencyStatus.RESIDENT))
    assert result.was_emitted
    assert result.emitted is not None
    assert result.emitted.statutory_citation == "Va. Code § 2.2-3700"


def test_non_resident_in_open_jurisdiction_emits() -> None:
    """Residency only binds in the six restricted states; an open state emits."""
    gen = RecordsRequestGenerator()
    filer = Filer("u4", "Anyone", ResidencyStatus.NON_RESIDENT, True, True)
    result = gen.generate(_gap("CA"), filer)
    assert result.was_emitted


def test_residency_block_does_not_require_consent() -> None:
    """The blocked path routes to a local filer; it does not file on this filer's behalf."""
    gen = RecordsRequestGenerator()
    # No consent, but restricted + non-resident: routing must not raise.
    result = gen.generate(_gap("AL"), Filer("u5", "Nonconsenting Nonresident"))
    assert not result.was_emitted
    assert result.residency_block is not None


def test_residency_barrier_coverage_is_never_searched_not_found() -> None:
    """The §32.2 distinction: a legal barrier is not an absence of surveillance."""
    law = records_law_for("KY")
    cov = residency_barrier_coverage(_gap("KY"), law, searched_by="u1")
    assert cov.absence_kind == "not_researched"
    assert cov.epistemic_state is not None
    assert cov.epistemic_state.value == "NOT_RESEARCHED"


# --- consent gate (SIG-TASK-018) ----------------------------------------------


def test_emit_without_consent_is_refused() -> None:
    """SIG-TASK-018: SIG does not file on a contributor's behalf without consent."""
    gen = RecordsRequestGenerator()
    filer = Filer("u6", "No Consent", ResidencyStatus.RESIDENT, consent_granted=False)
    with pytest.raises(ConsentNotGrantedError, match="has not consented"):
        gen.generate(_gap("CA"), filer)


def test_emit_without_public_act_acknowledgement_is_refused() -> None:
    """SIG-TASK-018: the filer must acknowledge filing is a public act attributable to them."""
    gen = RecordsRequestGenerator()
    filer = Filer(
        "u7",
        "Consented Only",
        ResidencyStatus.RESIDENT,
        consent_granted=True,
        acknowledged_public_act=False,
    )
    with pytest.raises(ConsentNotGrantedError, match="public act"):
        gen.generate(_gap("CA"), filer)


def test_emitted_request_states_it_is_a_public_act() -> None:
    """SIG-TASK-018: the emitted request makes the public-act attribution clear."""
    gen = RecordsRequestGenerator()
    request = gen.generate(_gap("CA"), _consenting(ResidencyStatus.RESIDENT)).emitted
    assert request is not None
    assert request.public_act_notice
    assert request.public_act_notice in request.request_text
    assert request.filer_display_name in request.public_act_notice


# --- reference-table + gap edge cases -----------------------------------------


def test_unknown_jurisdiction_is_refused() -> None:
    gen = RecordsRequestGenerator()
    with pytest.raises(UnknownJurisdictionError):
        gen.generate(_gap("ZZ"), _consenting(ResidencyStatus.RESIDENT))


def test_gap_requires_a_subject_identity() -> None:
    """§3.1: every node has identity — a gap with no subject is refused."""
    with pytest.raises(ValueError, match="MUST identify a subject"):
        ResearchGap(
            predicate_id="p",
            jurisdiction_id="CA",
            target_agency="a",
            records_contact="c",
            record_type="alpr_contract",
        )


# --- AC3: resolved_no_evidence_exists via the records path (SIG-TASK-009) ------


def _records_task_type() -> TaskType:
    return TaskType(
        task_type="missing_alpr_contract",
        detector=Detector(version="v1", query=lambda facts: True),
        priority_fn=lambda facts: 1.0,
        closing_condition=lambda facts: bool(facts.get("closed", False)),
        assignee_class=AssigneeClass.RECORDS_REQUESTER,
        effort_estimate=EffortEstimate.MODERATE,
        dispositions=(
            Disposition.RESOLVED_EVIDENCE_FOUND,
            Disposition.RESOLVED_NO_EVIDENCE_EXISTS,
            Disposition.BLOCKED_FEE,
        ),
        geographic_scope=GeographicScope.JURISDICTION,
    )


def _verified_task(subject: str = "agency:example") -> ResearchTask:
    pool = TaskPool()
    task = pool.generate(_records_task_type(), subject, facts={}, now=_NOW)
    assert task is not None
    task.triage()
    task.claim("alice", now=_NOW, timeout=timedelta(days=7))
    task.start()
    task.submit()
    task.verify()
    return task


def test_no_responsive_records_writes_a_coverage_record() -> None:
    """AC3 / SIG-TASK-009: a no-responsive-records reply becomes queryable data."""
    gen = RecordsRequestGenerator()
    request = gen.generate(_gap("CA"), _consenting(ResidencyStatus.RESIDENT)).emitted
    assert request is not None
    task = _verified_task()

    coverage = record_no_responsive_records(
        task, request, searched_at=_NOW, searched_by="alice", extra_sources=("agency portal",)
    )

    assert isinstance(coverage, CoverageRecord)
    assert coverage.absence_kind == "searched_not_found"
    assert coverage.subject_id == "agency:example"
    assert coverage.predicate_id == "contracted_device_count"
    # The emitted request is the primary named source (SIG-METRIC-002).
    assert coverage.sources_searched == (
        "Example County Sheriff records request under Cal. Gov. Code § 7920.000",
        "agency portal",
    )
    # And the task closed through the single coverage-writing bridge.
    assert task.status is TaskStatus.CLOSED
    assert task.disposition is Disposition.RESOLVED_NO_EVIDENCE_EXISTS
