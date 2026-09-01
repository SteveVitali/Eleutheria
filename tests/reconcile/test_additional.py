# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Additional reconciliation workflows (§29.8, SIG-RECON-046)."""

from __future__ import annotations

from datetime import date

import pytest
from reconcile.additional import (
    CapabilityClaim,
    CostClaim,
    CoverageClaim,
    reconcile_capability,
    reconcile_cost,
    reconcile_geographic_coverage,
    reconcile_organization_existence,
)
from reconcile.model import IDENTITY_AMBIGUITY

WHEN = date(2026, 1, 1)


# --- cost / contract-value ----------------------------------------------------


def test_cost_bases_stay_distinct_and_deltas_are_findings() -> None:
    claims = [
        CostClaim(basis="contract_value", amount_cents=100_000, observed_at=WHEN),
        CostClaim(basis="invoiced_total", amount_cents=120_000, observed_at=WHEN),
    ]
    rec = reconcile_cost("dep:1", claims)
    assert rec.values["contract_value"] == 100_000
    assert rec.values["invoiced_total"] == 120_000
    assert rec.contradictions and rec.tasks


def test_cost_agreement_has_no_finding() -> None:
    claims = [
        CostClaim(basis="contract_value", amount_cents=100_000, observed_at=WHEN),
        CostClaim(basis="budget_line", amount_cents=100_000, observed_at=WHEN),
    ]
    assert reconcile_cost("dep:1", claims).contradictions == ()


def test_cost_mixed_currency_is_rejected() -> None:
    claims = [
        CostClaim(basis="contract_value", amount_cents=1, observed_at=WHEN, currency="USD"),
        CostClaim(basis="invoiced_total", amount_cents=1, observed_at=WHEN, currency="EUR"),
    ]
    with pytest.raises(ValueError, match="currenc"):
        reconcile_cost("dep:1", claims)


def test_unknown_cost_basis_is_rejected() -> None:
    with pytest.raises(ValueError, match="cost basis"):
        CostClaim(basis="sticker_price", amount_cents=1, observed_at=WHEN)


# --- organization-existence (§14.4) -------------------------------------------


def test_unknown_org_named_in_a_list_is_a_finding() -> None:
    findings = reconcile_organization_existence(
        ["org:known", "Phantom LLC"], {"org:known"}, named_in="a Flock network list"
    )
    by_name = {f.org_name: f for f in findings}
    assert by_name["org:known"].known is True
    assert by_name["org:known"].contradiction is None
    phantom = by_name["Phantom LLC"]
    assert phantom.known is False
    assert phantom.contradiction is not None
    assert phantom.contradiction.contradiction_type == IDENTITY_AMBIGUITY
    assert phantom.task is not None


# --- capability (SIG-ONTO-018) ------------------------------------------------


def test_marketed_capability_does_not_imply_configured() -> None:
    claims = [
        CapabilityClaim(
            org_id="org:a",
            capability="face_recognition",
            kind="marketed",
            present=True,
            observed_at=WHEN,
        ),
    ]
    rec = reconcile_capability("org:a", "face_recognition", claims)
    assert rec.by_kind["marketed"] is True
    assert rec.by_kind["configured"] is None  # never inferred from marketed
    assert rec.by_kind["observed"] is None


def test_within_kind_disagreement_is_a_finding_and_stays_unresolved() -> None:
    claims = [
        CapabilityClaim(
            org_id="org:a",
            capability="alpr",
            kind="configured",
            present=True,
            observed_at=WHEN,
            claim_id="c1",
        ),
        CapabilityClaim(
            org_id="org:a",
            capability="alpr",
            kind="configured",
            present=False,
            observed_at=WHEN,
            claim_id="c2",
        ),
    ]
    rec = reconcile_capability("org:a", "alpr", claims)
    assert rec.contradictions and rec.tasks
    assert rec.by_kind["configured"] is None


def test_unknown_capability_kind_is_rejected() -> None:
    with pytest.raises(ValueError, match="capability kind"):
        CapabilityClaim(org_id="o", capability="c", kind="rumored", present=True, observed_at=WHEN)


# --- geographic-coverage ------------------------------------------------------


def test_distinct_scopes_stay_distinct() -> None:
    claims = [
        CoverageClaim(
            subject_id="dep:1", scope="city_limits", area_label="OKC city", observed_at=WHEN
        ),
        CoverageClaim(subject_id="dep:1", scope="metro", area_label="OKC metro", observed_at=WHEN),
    ]
    rec = reconcile_geographic_coverage("dep:1", claims)
    assert rec.by_scope == {"city_limits": "OKC city", "metro": "OKC metro"}
    assert rec.contradictions == ()


def test_within_scope_disagreement_is_a_finding() -> None:
    claims = [
        CoverageClaim(subject_id="dep:1", scope="metro", area_label="A", observed_at=WHEN),
        CoverageClaim(subject_id="dep:1", scope="metro", area_label="B", observed_at=WHEN),
    ]
    rec = reconcile_geographic_coverage("dep:1", claims)
    assert rec.by_scope["metro"] is None
    assert rec.contradictions and rec.tasks
