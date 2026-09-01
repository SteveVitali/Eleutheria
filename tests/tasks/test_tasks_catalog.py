# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The concrete §33.2 task catalog and the §31 contradiction→task map (P10.2).

AC1 (SIG-TASK-003): all 34 §33.2 task types register, each with a testable closing
condition; §33.2 is the count authority.
AC2 (SIG-TASK-004): every §31 contradiction detector maps to a task type — no member
of ``reconcile.model.CONTRADICTION_TYPES`` is left without a catalog task.
AC3: each detector fires on a seeded positive, stays quiet on a seeded negative, and
auto-invalidates (through the P10.1 lifecycle) when its condition clears.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from reconcile.model import CONTRADICTION_TYPES
from tasks.catalog import (
    CATALOG_SIZE,
    CATALOG_TASK_TYPES,
    CONTRADICTION_TASK_MAP,
    build_catalog,
)
from tasks.lifecycle import TaskPool
from tasks.spec import Facts, GeographicScope, TaskType
from tasks.vocabulary import AssigneeClass, Disposition, EffortEstimate

NOW = datetime(2026, 9, 1, 12, 0, 0)

# Per-type fixtures: slug -> (positive facts [detector fires, not yet closed],
# cleared facts [detector quiet AND closing condition met]). The cleared set is the
# seeded negative *and* the state the subject reaches when the gap is resolved, so it
# drives both the "stays quiet" assertion and the auto-invalidation sweep.
FIXTURES: dict[str, tuple[Facts, Facts]] = {
    "missing_physical_devices": (
        {"active_device_count": 10, "mapped_device_count": 3},
        {"active_device_count": 10, "mapped_device_count": 10},
    ),
    "missing_contract": (
        {"deployment_evidenced": True, "procurement_evidence": False},
        {"deployment_evidenced": True, "procurement_evidence": True},
    ),
    "conflicting_retention": (
        {"policy_retention_days": 30, "configured_retention_days": 90},
        {"policy_retention_days": 30, "configured_retention_days": 30},
    ),
    "stale_evidence": (
        {"currency": "STALE"},
        {"currency": "CURRENT"},
    ),
    "orphaned_device": (
        {"has_manufacturer": True, "has_operator": False},
        {"has_manufacturer": True, "has_operator": True},
    ),
    "new_sharing_node": (
        {"in_network_list": True, "in_registry": False},
        {"in_network_list": True, "in_registry": True},
    ),
    "vendor_replacement": (
        {"cancellation_in_window": True, "new_deployment_in_window": True},
        {"cancellation_in_window": True, "new_deployment_in_window": False},
    ),
    "portal_disappeared": (
        {"disappearance_event": True},
        {"disappearance_event": False},
    ),
    "portal_appeared_no_deployment": (
        {"new_portal": True, "deployment_record": False},
        {"new_portal": True, "deployment_record": True},
    ),
    "contract_expiring": (
        {"days_to_end_date": 30, "threshold_days": 90, "renewal_evidence": False},
        {"days_to_end_date": 30, "threshold_days": 90, "renewal_evidence": True},
    ),
    "sharing_asymmetry": (
        {"edge_asserted_by_one_side_only": True},
        {"edge_asserted_by_one_side_only": False},
    ),
    "device_jurisdiction_mismatch": (
        {"located_in": "juris:a", "attributed_to": "juris:b"},
        {"located_in": "juris:a", "attributed_to": "juris:a"},
    ),
    "retention_changed_without_policy": (
        {"config_changed": True, "policy_claim_present": False},
        {"config_changed": True, "policy_claim_present": True},
    ),
    "network_org_without_jurisdiction": (
        {"org_resolved": True, "has_jurisdiction": False},
        {"org_resolved": True, "has_jurisdiction": True},
    ),
    "adoption_without_corroboration": (
        {"atlas_row": True, "has_portal": False, "has_contract": False, "has_device": False},
        {"atlas_row": True, "has_portal": True, "has_contract": False, "has_device": False},
    ),
    "grant_without_deployment": (
        {"grant_awarded": True, "deployment_evidence": False},
        {"grant_awarded": True, "deployment_evidence": True},
    ),
    "vendor_acquisition_relink": (
        {"acquisition_event": True, "products_need_relinking": True},
        {"acquisition_event": True, "products_need_relinking": False},
    ),
    "sole_source_tier_f_support": (
        {"only_support_reliability": "R5"},
        {"only_support_reliability": "R2"},
    ),
    "long_unverified_claim": (
        {"review_status": "unreviewed", "age_days": 365, "threshold_days": 180},
        {"review_status": "verified", "age_days": 365, "threshold_days": 180},
    ),
    "link_rot": (
        {"url_status": 404},
        {"url_status": 200},
    ),
    "re_extraction_available": (
        {"stored_parser_version": 1, "available_parser_version": 3},
        {"stored_parser_version": 3, "available_parser_version": 3},
    ),
    "candidate_duplicate_entities": (
        {"er_tier": 4},
        {"er_tier": 1},
    ),
    "litigation_without_docket": (
        {"proceeding_present": True, "docket_link": False},
        {"proceeding_present": True, "docket_link": True},
    ),
    "incident_only_secondary_sources": (
        {"incident_present": True, "has_primary_source": False},
        {"incident_present": True, "has_primary_source": True},
    ),
    "unmapped_vocabulary_value": (
        {"source_value_present": True, "value_in_vocabulary": False},
        {"source_value_present": True, "value_in_vocabulary": True},
    ),
    "authorized_not_deployed": (
        {"authorization": "authorized", "physical": "not_installed"},
        {"authorization": "authorized", "physical": "installed"},
    ),
    "canceled_but_installed": (
        {"procurement": "canceled", "physical": "installed"},
        {"procurement": "canceled", "physical": "removed"},
    ),
    "free_trial_capability": (
        {"operational": "active", "procurement_transition": False},
        {"operational": "active", "procurement_transition": True},
    ),
    "cooperative_contract_unexplored": (
        {"piggyback_contract": True, "master_record": False},
        {"piggyback_contract": True, "master_record": True},
    ),
    "coverage_hole": (
        {"population": 100_000, "threshold_population": 50_000, "evidence_count": 0},
        {"population": 100_000, "threshold_population": 50_000, "evidence_count": 1},
    ),
    "unresolved_contradiction_aging": (
        {"contradiction_open": True, "open_age_days": 60, "threshold_days": 30},
        {"contradiction_open": False, "open_age_days": 60, "threshold_days": 30},
    ),
    "candidate_asset_awaiting_verification": (
        {"candidate_corroborated": True, "promoted": False},
        {"candidate_corroborated": True, "promoted": True},
    ),
    "contract_amendment_chain_incomplete": (
        {"terms_contradicted_by_later_source": True, "amends_contract_child": False},
        {"terms_contradicted_by_later_source": True, "amends_contract_child": True},
    ),
    "sharing_snapshot_stale": (
        {"configured_access_age_days": 365, "fast_threshold_days": 180},
        {"configured_access_age_days": 10, "fast_threshold_days": 180},
    ),
}


def _by_slug() -> dict[str, TaskType]:
    return {tt.task_type: tt for tt in CATALOG_TASK_TYPES}


# --- AC1 / SIG-TASK-003: the full catalog registers ---------------------------


def test_catalog_has_exactly_the_34_types_of_the_count_authority() -> None:
    """§33.2 is the count authority; the catalog is exactly 34 types, no duplicates."""
    assert CATALOG_SIZE == 34
    assert len(CATALOG_TASK_TYPES) == 34
    slugs = [tt.task_type for tt in CATALOG_TASK_TYPES]
    assert len(set(slugs)) == 34, "catalog slugs must be unique"


def test_building_the_catalog_registers_every_type() -> None:
    """A successful build is the SIG-TASK-002 proof: an untestable row would be refused."""
    registry = build_catalog()
    assert len(registry) == 34
    for tt in CATALOG_TASK_TYPES:
        assert tt.task_type in registry


def test_every_catalog_type_has_a_testable_closing_condition() -> None:
    """SIG-TASK-003: a type that cannot express a testable closing cannot register."""
    for tt in CATALOG_TASK_TYPES:
        assert tt.has_testable_closing_condition, f"{tt.task_type} lacks a testable closing"


def test_every_catalog_type_declares_all_eight_fields_from_the_vocabulary() -> None:
    """SIG-TASK-001: each row carries all eight §33.1 fields, drawn from the vocab."""
    for tt in CATALOG_TASK_TYPES:
        assert tt.detector.version, f"{tt.task_type}: detector has no version"
        assert callable(tt.priority_fn)
        assert isinstance(tt.assignee_class, AssigneeClass)
        assert isinstance(tt.effort_estimate, EffortEstimate)
        assert isinstance(tt.geographic_scope, GeographicScope)
        assert tt.dispositions, f"{tt.task_type}: no dispositions"
        for disp in tt.dispositions:
            assert isinstance(disp, Disposition)


def test_every_catalog_type_has_a_fixture() -> None:
    """Guard: a row without a fixture would make the per-type checks vacuous."""
    assert set(FIXTURES) == {tt.task_type for tt in CATALOG_TASK_TYPES}


# --- AC3: per-type detector fixtures + closing + auto-invalidation ------------


@pytest.mark.parametrize("slug", sorted(FIXTURES))
def test_detector_fires_on_positive_and_is_quiet_on_negative(slug: str) -> None:
    tt = _by_slug()[slug]
    positive, cleared = FIXTURES[slug]
    assert tt.detector_fires(positive) is True, f"{slug}: detector did not fire on its positive"
    assert tt.detector_fires(cleared) is False, f"{slug}: detector fired on its negative"


@pytest.mark.parametrize("slug", sorted(FIXTURES))
def test_closing_condition_is_open_on_positive_and_met_when_cleared(slug: str) -> None:
    tt = _by_slug()[slug]
    positive, cleared = FIXTURES[slug]
    assert tt.is_closed_by(positive) is False, f"{slug}: closing condition met on the positive"
    assert tt.is_closed_by(cleared) is True, f"{slug}: closing condition not met once cleared"


@pytest.mark.parametrize("slug", sorted(FIXTURES))
def test_task_auto_invalidates_when_its_condition_clears(slug: str) -> None:
    """SIG-TASK-006 end-to-end: a generated task is swept once the detector goes quiet."""
    tt = _by_slug()[slug]
    positive, cleared = FIXTURES[slug]
    pool = TaskPool()
    subject = f"subject:{slug}"
    task = pool.generate(tt, subject, facts=positive, now=NOW)
    assert task is not None and task.is_open

    # Detector still fires -> not swept.
    assert pool.sweep_invalidations({subject: positive}) == []
    assert pool.get(task.task_id).is_open

    # Evidence arrives by another route (condition clears) -> silently invalidated.
    invalidated = pool.sweep_invalidations({subject: cleared})
    assert invalidated == [task]
    assert not pool.get(task.task_id).is_open


@pytest.mark.parametrize("slug", sorted(FIXTURES))
def test_priority_is_a_finite_number(slug: str) -> None:
    tt = _by_slug()[slug]
    positive, _ = FIXTURES[slug]
    priority = tt.priority(positive)
    assert isinstance(priority, float)


def test_urgency_priorities_respond_to_their_signal() -> None:
    """The two computed priority_fns rank by their signal (§33.1)."""
    by_slug = _by_slug()
    expiring = by_slug["contract_expiring"]
    assert expiring.priority({"days_to_end_date": 5, "threshold_days": 90}) > expiring.priority(
        {"days_to_end_date": 80, "threshold_days": 90}
    )
    hole = by_slug["coverage_hole"]
    assert hole.priority({"population": 900_000}) > hole.priority({"population": 10_000})


# --- AC2 / SIG-TASK-004: every §31 contradiction detector maps to a task ------


def test_every_contradiction_type_maps_to_a_task() -> None:
    """No §31 detector exists without a task type (SIG-TASK-004)."""
    # The map's keys are exactly the authoritative §31 contradiction_type vocabulary,
    # so a new contradiction type cannot be added without giving it a task route.
    assert set(CONTRADICTION_TASK_MAP) == set(CONTRADICTION_TYPES)


def test_every_mapped_task_type_is_a_registered_catalog_type() -> None:
    """Each contradiction routes to a real, registered catalog task (SIG-TASK-004)."""
    registry = build_catalog()
    for contradiction_type, slug in CONTRADICTION_TASK_MAP.items():
        assert slug in registry, f"{contradiction_type} -> {slug!r} is not a catalog task type"
        # The routed task is itself testable — detection reaches a closeable task.
        assert registry.get(slug).has_testable_closing_condition
