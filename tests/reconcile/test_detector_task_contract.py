# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The detector→task contract, applied to every contradiction detector (SIG-RECON-057).

§31 requires that *every* contradiction detector emit a research task with a
defined closing condition — the contract that turns disagreement into work. This
suite drives each detector (the §29 workflows *and* the resolver's Phase-2 guards)
on a triggering fixture and asserts, via
:func:`reconcile.contradiction.assert_detector_task_contract`, that every emitted
contradiction links a task with a non-empty closing condition.
"""

from __future__ import annotations

from datetime import date

from reconcile.additional import (
    CapabilityClaim,
    CostClaim,
    CoverageClaim,
    reconcile_capability,
    reconcile_cost,
    reconcile_geographic_coverage,
    reconcile_organization_existence,
)
from reconcile.contradiction import assert_detector_task_contract, detector_task_violations
from reconcile.counts import reconcile_counts
from reconcile.lifecycle import render_lifecycle_status
from reconcile.model import Contradiction, CountClaim, Evidence, ResearchTask
from reconcile.policy_config import (
    PROHIBITED,
    ConfigurationState,
    PolicyStatement,
    reconcile_policy_configuration,
)
from reconcile.resolve import RESOLVE, Claim
from reconcile.retention import RetentionClaim, reconcile_retention
from reconcile.sharing import SharingObservation, reconcile_sharing

AS_OF = date(2026, 9, 1)


def _ev() -> Evidence:
    return Evidence(
        source_id="src:x",
        source_family="x",
        artifact_type="portal_snapshot",
        stable_locator="https://example/x",
        capture_digest="b" + "0" * 40,
        locator={"selector": "#x"},
    )


def _count(basis: str, value: int, *, R: str, genre: str, observed: date) -> CountClaim:
    return CountClaim(
        count_basis=basis,
        value=value,
        reliability=R,
        integrity="I1",
        observed_at=observed,
        genre=genre,
        evidence=_ev(),
    )


def _claim(claim_id: str, value: object, *, genre: str, count_basis: str | None = None) -> Claim:
    return Claim(
        claim_id=claim_id,
        subject_id="dep:okc",
        predicate_id="active_device_count",
        value=value,
        reliability="R2",
        integrity="I1",
        genre=genre,
        observed_at=date(2026, 7, 1),
        source_id=f"src:{claim_id}",
        count_basis=count_basis,
    )


def _counts_output() -> tuple[list[Contradiction], list[ResearchTask]]:
    rec = reconcile_counts(
        "dep:okc",
        [
            _count("claimed", 299, R="R4", genre="news_article", observed=date(2026, 8, 3)),
            _count("claimed", 190, R="R2", genre="council_minutes", observed=date(2026, 8, 18)),
        ],
        as_of=AS_OF,
    )
    return list(rec.contradictions), list(rec.tasks)


def _sharing_output() -> tuple[list[Contradiction], list[ResearchTask]]:
    rec = reconcile_sharing(
        [
            SharingObservation(
                asserted_by="org:a",
                from_org="org:a",
                to_org="org:b",
                access_kind="configured_access",
                observed_at=date(2026, 6, 1),
                evidence=_ev(),
            )
        ]
    )
    return list(rec.contradictions), list(rec.tasks)


def _retention_output() -> tuple[list[Contradiction], list[ResearchTask]]:
    rec = reconcile_retention(
        "dep:okc",
        [
            RetentionClaim("policy_written_retention_days", 30, date(2026, 6, 1), _ev()),
            RetentionClaim("configured_retention_days", 90, date(2026, 6, 1), _ev()),
        ],
    )
    return list(rec.contradictions), list(rec.tasks)


def _policy_config_output() -> tuple[list[Contradiction], list[ResearchTask]]:
    res = reconcile_policy_configuration(
        PolicyStatement("dep:okc", "immigration_query", PROHIBITED, _ev()),
        ConfigurationState("dep:okc", "immigration_query", enabled=True, evidence=_ev()),
    )
    cons = [res.contradiction] if res.contradiction else []
    tasks = [res.task] if res.task else []
    return cons, tasks


def _cost_output() -> tuple[list[Contradiction], list[ResearchTask]]:
    rec = reconcile_cost(
        "dep:okc",
        [
            CostClaim("contract_value", 100_000, date(2026, 6, 1), evidence=_ev()),
            CostClaim("invoiced_total", 120_000, date(2026, 6, 1), evidence=_ev()),
        ],
    )
    return list(rec.contradictions), list(rec.tasks)


def _org_existence_output() -> tuple[list[Contradiction], list[ResearchTask]]:
    findings = reconcile_organization_existence(["Phantom LLC"], known_registry_ids=set())
    cons = [f.contradiction for f in findings if f.contradiction]
    tasks = [f.task for f in findings if f.task]
    return cons, tasks


def _capability_output() -> tuple[list[Contradiction], list[ResearchTask]]:
    rec = reconcile_capability(
        "org:a",
        "face_recognition",
        [
            CapabilityClaim("org:a", "face_recognition", "configured", True, date(2026, 6, 1)),
            CapabilityClaim("org:a", "face_recognition", "configured", False, date(2026, 6, 2)),
        ],
    )
    return list(rec.contradictions), list(rec.tasks)


def _coverage_output() -> tuple[list[Contradiction], list[ResearchTask]]:
    rec = reconcile_geographic_coverage(
        "dep:okc",
        [
            CoverageClaim("dep:okc", "city_limits", "OKC city", date(2026, 6, 1)),
            CoverageClaim("dep:okc", "city_limits", "OKC metro", date(2026, 6, 2)),
        ],
    )
    return list(rec.contradictions), list(rec.tasks)


def _lifecycle_output() -> tuple[list[Contradiction], list[ResearchTask]]:
    status = render_lifecycle_status(
        "dep:okc", procurement_state="canceled", physical_state="installed", as_of_edtf="2026-08"
    )
    cons = [status.contradiction] if status.contradiction else []
    tasks = [status.task] if status.task else []
    return cons, tasks


def _resolver_value_domain_output() -> tuple[list[Contradiction], list[ResearchTask]]:
    good = _claim("good", 38, genre="portal_snapshot")
    bad = _claim("bad", "not-an-int", genre="portal_snapshot")
    r = RESOLVE(
        "dep:okc", "active_device_count", [good, bad], as_of_world=AS_OF, as_of_belief=AS_OF
    )
    return list(r.contradictions), list(r.tasks)


def _resolver_predicate_conflation_output() -> tuple[list[Contradiction], list[ResearchTask]]:
    active = _claim("active", 38, genre="portal_snapshot", count_basis="active")
    contracted = _claim("contracted", 42, genre="executed_contract", count_basis="contracted")
    r = RESOLVE(
        "dep:okc",
        "active_device_count",
        [active, contracted],
        as_of_world=AS_OF,
        as_of_belief=AS_OF,
    )
    return list(r.contradictions), list(r.tasks)


DETECTORS = {
    "counts.value_disagreement": _counts_output,
    "sharing.asymmetry": _sharing_output,
    "retention.divergence": _retention_output,
    "policy_config.divergence": _policy_config_output,
    "additional.cost": _cost_output,
    "additional.org_existence": _org_existence_output,
    "additional.capability": _capability_output,
    "additional.coverage": _coverage_output,
    "lifecycle.canceled_hardware_present": _lifecycle_output,
    "resolver.value_domain_mismatch": _resolver_value_domain_output,
    "resolver.predicate_conflation": _resolver_predicate_conflation_output,
}


def test_every_detector_emits_at_least_one_contradiction_on_its_fixture() -> None:
    # Guard: a fixture that stops triggering would make the contract vacuously true.
    for name, produce in DETECTORS.items():
        contradictions, _ = produce()
        assert contradictions, f"{name}: fixture produced no contradiction to check"


def test_every_detector_honours_the_detector_task_contract() -> None:
    for name, produce in DETECTORS.items():
        contradictions, tasks = produce()
        violations = detector_task_violations(contradictions, tasks)
        assert not violations, f"{name}: {violations}"
        assert_detector_task_contract(contradictions, tasks)  # raises on violation
