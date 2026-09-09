# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Versioned templates with measured success rates (§36, SIG-TASK-017).

Request language MUST be versioned and its success rate measured; language that
produces denials is flagged for revision, and which wording works is itself a
finding. These tests exercise the library (versions per record type) and the
outcome log (measured rate + the revision flag with its minimum-sample guard).
"""

from __future__ import annotations

from tasks.records_request import RequestTemplate, TemplateOutcomeLog, template_library


def test_every_record_type_has_at_least_one_version() -> None:
    """SIG-TASK-017: templates are versioned data, not free-floating strings."""
    lib = template_library()
    assert lib.record_types()
    for record_type in lib.record_types():
        versions = lib.versions(record_type)
        assert versions
        for tmpl in versions:
            assert isinstance(tmpl, RequestTemplate)
            assert tmpl.version
            assert tmpl.body
            assert tmpl.records_sought


def test_current_returns_the_latest_version() -> None:
    lib = template_library()
    versions = lib.versions("alpr_contract")
    assert lib.current("alpr_contract") is versions[-1]


def test_set_version_is_stamped() -> None:
    assert template_library().set_version


def test_success_rate_is_none_before_any_outcome() -> None:
    log = TemplateOutcomeLog()
    assert log.success_rate("alpr_contract", "v1") is None
    assert log.sample_size("alpr_contract", "v1") == 0
    assert not log.needs_revision("alpr_contract", "v1")


def test_success_rate_is_measured_from_recorded_outcomes() -> None:
    """SIG-TASK-017: the rate is measured, not assumed."""
    log = TemplateOutcomeLog()
    for succeeded in (True, True, True, False):
        log.record_outcome("alpr_contract", "v1", succeeded=succeeded)
    assert log.sample_size("alpr_contract", "v1") == 4
    assert log.success_rate("alpr_contract", "v1") == 0.75


def test_denial_producing_language_is_flagged_for_revision() -> None:
    """SIG-TASK-017: a version that mostly produces denials is flagged."""
    log = TemplateOutcomeLog(revision_success_floor=0.5, revision_min_sample=5)
    # 1 success in 6 filings — well below the floor, past the minimum sample.
    log.record_outcome("camera_deployment", "v1", succeeded=True)
    for _ in range(5):
        log.record_outcome("camera_deployment", "v1", succeeded=False)
    assert log.needs_revision("camera_deployment", "v1")
    assert ("camera_deployment", "v1") in log.flagged_for_revision()


def test_undersampled_version_is_not_flagged() -> None:
    """A single early denial must not condemn a template (the min-sample guard)."""
    log = TemplateOutcomeLog(revision_success_floor=0.5, revision_min_sample=5)
    log.record_outcome("drone_program", "v1", succeeded=False)
    log.record_outcome("drone_program", "v1", succeeded=False)
    assert log.success_rate("drone_program", "v1") == 0.0
    assert not log.needs_revision("drone_program", "v1")  # only 2 < 5 samples
    assert ("drone_program", "v1") not in log.flagged_for_revision()


def test_working_language_is_not_flagged() -> None:
    """A high-success version stays; the finding is that its language works."""
    log = TemplateOutcomeLog(revision_success_floor=0.5, revision_min_sample=5)
    for _ in range(8):
        log.record_outcome("surveillance_policy", "v1", succeeded=True)
    assert log.success_rate("surveillance_policy", "v1") == 1.0
    assert not log.needs_revision("surveillance_policy", "v1")
    assert log.flagged_for_revision() == frozenset()
