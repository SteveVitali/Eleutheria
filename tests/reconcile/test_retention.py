# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Retention reconciliation (§29.5, SIG-RECON-043)."""

from __future__ import annotations

from datetime import date

import pytest
from reconcile.retention import (
    CONFIGURED,
    POLICY_WRITTEN,
    RETENTION_PREDICATES,
    VENDOR_DEFAULT,
    RetentionClaim,
    VendorDefaultLeak,
    apply_vendor_default_change,
    populate_configured_from_vendor_default,
    reconcile_retention,
)

WHEN = date(2026, 1, 1)


def _c(pred: str, days: int, when: date = WHEN) -> RetentionClaim:
    return RetentionClaim(predicate=pred, days=days, observed_at=when)


def test_three_predicates_stay_distinct() -> None:
    assert set(RETENTION_PREDICATES) == {POLICY_WRITTEN, CONFIGURED, VENDOR_DEFAULT}
    rec = reconcile_retention(
        "dep:1", [_c(POLICY_WRITTEN, 30), _c(CONFIGURED, 90), _c(VENDOR_DEFAULT, 30)]
    )
    assert rec.values[POLICY_WRITTEN] == 30
    assert rec.values[CONFIGURED] == 90
    assert rec.values[VENDOR_DEFAULT] == 30


def test_policy_versus_configured_disagreement_is_a_finding() -> None:
    rec = reconcile_retention("dep:1", [_c(POLICY_WRITTEN, 30), _c(CONFIGURED, 90)])
    assert rec.contradictions
    assert rec.tasks
    con = rec.contradictions[0]
    assert set(con.claim_values) == {30, 90}
    assert con.research_task_ids


def test_configured_matching_policy_has_no_finding() -> None:
    rec = reconcile_retention("dep:1", [_c(POLICY_WRITTEN, 30), _c(CONFIGURED, 30)])
    assert rec.contradictions == ()


def test_configured_diverging_from_vendor_default_is_a_finding() -> None:
    rec = reconcile_retention("dep:1", [_c(CONFIGURED, 90), _c(VENDOR_DEFAULT, 30)])
    assert any("default" in c.note for c in rec.contradictions)


def test_vendor_default_never_populates_configuration() -> None:
    # SIG-ONTO-036: the shipped default is never written into configuration.
    with pytest.raises(VendorDefaultLeak):
        populate_configured_from_vendor_default(30)


def test_vendor_default_change_is_not_retroactive() -> None:
    # SIG-RECON-043: a vendor changing its default does not change existing config.
    assert apply_vendor_default_change(configured_days=90, new_vendor_default_days=30) == 90
    # even when the deployment has no explicit configured value, the default does
    # not silently become one.
    assert apply_vendor_default_change(configured_days=None, new_vendor_default_days=30) is None


def test_latest_observation_wins_within_a_predicate() -> None:
    rec = reconcile_retention(
        "dep:1",
        [_c(CONFIGURED, 30, date(2024, 1, 1)), _c(CONFIGURED, 90, date(2026, 1, 1))],
    )
    assert rec.values[CONFIGURED] == 90


def test_unknown_predicate_is_rejected() -> None:
    with pytest.raises(ValueError, match="retention predicate"):
        RetentionClaim(predicate="retention_days", days=30, observed_at=WHEN)
