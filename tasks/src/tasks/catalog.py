# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The concrete task catalog of §33.2 (SIG-TASK-003/004).

P10.1 owns the *engine* — the detector DSL, the lifecycle, dispositions, queues,
anti-abuse. This module owns the **data**: the 34 enumerated task types of the
§33.2 catalog, each registered against :mod:`tasks.spec` with a versioned
``detector`` query and a **testable** ``closing_condition``. It is the payload that
turns the engine into a working research-coordination queue.

Two load-bearing disciplines are realized here:

* **SIG-TASK-003** — every §33.2 row is a registered :class:`~tasks.spec.TaskType`.
  A type whose ``closing_condition`` is not evaluable cannot register (the registry
  refuses it), so a "research this" row is a catalog *defect*, not a TODO. §33.2 is
  the count authority: :data:`CATALOG_SIZE` (34) is asserted, not assumed.
* **SIG-TASK-004** — every §31 contradiction detector maps to a task type. The §31
  ``contradiction_type`` vocabulary (``reconcile.model.CONTRADICTION_TYPES``) is the
  authoritative detector taxonomy; :data:`CONTRADICTION_TASK_MAP` routes each of its
  members to the catalog task that resolves it, so a live contradiction always
  surfaces as actionable work. The map is deliberately **many-to-one**: the §33.2
  catalog is coarser than the §31 type vocabulary, so several contradiction classes
  share the catalog task that resolves them (e.g. both a plain value disagreement and
  a policy/configuration divergence resolve through ``conflicting_retention``).

Detectors and closing conditions read a subject's current graph :class:`~tasks.spec.Facts`
(a ``Mapping[str, object]``). Here they read documented, in-memory fact keys — the
representative query surface P10.1's ``Facts`` type standardises; wiring each detector
to the real materialized graph is downstream. Each row is modelled so that the
detector stops firing exactly when the gap is resolved, which is what makes
auto-invalidation (SIG-TASK-006) and the closing condition (SIG-TASK-002) two views of
the same fact — see ``tests/tasks/test_tasks_catalog.py`` for the per-type fixtures.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from .spec import Detector, Facts, GeographicScope, TaskType, TaskTypeRegistry
from .vocabulary import AssigneeClass, Disposition, EffortEstimate

__all__ = [
    "CATALOG_SIZE",
    "CATALOG_TASK_TYPES",
    "CONTRADICTION_TASK_MAP",
    "build_catalog",
    "catalog",
]

#: The §33.2 catalog has exactly this many task types. §33.2 is the count authority
#: (the Part X AC was reconciled from "32" to "34"); this constant is asserted by the
#: test suite so the catalog cannot silently drift from the spec.
CATALOG_SIZE = 34

# --- disposition sets by assignee class (§33.4 vocabulary) --------------------
# Every row draws its permitted outcomes from the §33.4 Disposition vocabulary. The
# set a task may reach follows its assignee class: records/document work can be
# blocked by a fee or a denial or left awaiting a response, and search work can
# conclude "searched, found nothing" (which writes a CoverageRecord, SIG-TASK-009).
_COMMON: tuple[Disposition, ...] = (
    Disposition.RESOLVED_EVIDENCE_FOUND,
    Disposition.NOT_ACTIONABLE,
    Disposition.SUPERSEDED,
    Disposition.DEFERRED,
)
_WITH_NO_EVIDENCE: tuple[Disposition, ...] = (*_COMMON, Disposition.RESOLVED_NO_EVIDENCE_EXISTS)
_RECORDS: tuple[Disposition, ...] = (
    *_WITH_NO_EVIDENCE,
    Disposition.BLOCKED_ACCESS_DENIED,
    Disposition.BLOCKED_FEE,
    Disposition.BLOCKED_AWAITING_RESPONSE,
)

_DISPOSITIONS_BY_ASSIGNEE: dict[AssigneeClass, tuple[Disposition, ...]] = {
    AssigneeClass.RECORDS_REQUESTER: _RECORDS,
    AssigneeClass.DOCUMENT_REVIEWER: _RECORDS,
    AssigneeClass.FIELD_MAPPER: _WITH_NO_EVIDENCE,
    AssigneeClass.LOCAL_GROUP: _WITH_NO_EVIDENCE,
    AssigneeClass.ANALYST: _WITH_NO_EVIDENCE,
    AssigneeClass.CURATOR: _COMMON,
    AssigneeClass.DEVELOPER: _COMMON,
}


def _i(facts: Facts, key: str, default: int = 0) -> int:
    """Read an integer fact (the graph stores counts/ages as ints), else a default.

    Detectors read the loosely-typed :class:`~tasks.spec.Facts` mapping
    (``Mapping[str, object]``); this narrows a numeric fact to ``int`` so the
    detector logic stays statically typed rather than casting ``object`` inline.
    """
    value = facts.get(key, default)
    return value if isinstance(value, int) else default


def _static_priority(default: float) -> Callable[[Facts], float]:
    """A priority function that reads an explicit ``priority`` fact, else a band default."""
    return lambda facts: _f(facts, "priority", default)


def _f(facts: Facts, key: str, default: float) -> float:
    """Read a numeric fact as a float, else a default (see :func:`_i`)."""
    value = facts.get(key, default)
    return float(value) if isinstance(value, (int, float)) else default


def _t(
    *,
    slug: str,
    version: str,
    fires: Callable[[Facts], bool],
    closes: Callable[[Facts], bool],
    assignee: AssigneeClass,
    effort: EffortEstimate,
    scope: GeographicScope,
    priority_fn: Callable[[Facts], float] | None = None,
) -> TaskType:
    """Build one catalog :class:`~tasks.spec.TaskType` (all eight §33.1 fields)."""
    return TaskType(
        task_type=slug,
        detector=Detector(version=version, query=fires),
        priority_fn=priority_fn or _static_priority(0.5),
        closing_condition=closes,
        assignee_class=assignee,
        effort_estimate=effort,
        dispositions=_DISPOSITIONS_BY_ASSIGNEE[assignee],
        geographic_scope=scope,
    )


def _catalog_task_types() -> tuple[TaskType, ...]:
    """The 34 §33.2 task types, in catalog order. Each detector/closing pair reads the
    documented `Facts` keys named in ``tests/tasks/test_tasks_catalog.py``."""
    A, E, G = AssigneeClass, EffortEstimate, GeographicScope
    return (
        # 1 — Missing physical devices: active_device_count > mapped_device_count.
        _t(
            slug="missing_physical_devices",
            version="v1",
            fires=lambda f: _i(f, "active_device_count") > _i(f, "mapped_device_count"),
            closes=lambda f: _i(f, "mapped_device_count") >= _i(f, "active_device_count"),
            assignee=A.FIELD_MAPPER,
            effort=E.MODERATE,
            scope=G.JURISDICTION,
        ),
        # 2 — Missing contract: deployment evidenced, no procurement evidence.
        _t(
            slug="missing_contract",
            version="v1",
            fires=lambda f: (
                bool(f.get("deployment_evidenced")) and not f.get("procurement_evidence")
            ),
            closes=lambda f: bool(f.get("procurement_evidence")),
            assignee=A.RECORDS_REQUESTER,
            effort=E.SUBSTANTIAL,
            scope=G.JURISDICTION,
        ),
        # 3 — Conflicting retention: policy vs configuration divergence.
        _t(
            slug="conflicting_retention",
            version="v1",
            fires=lambda f: (
                "policy_retention_days" in f
                and "configured_retention_days" in f
                and f["policy_retention_days"] != f["configured_retention_days"]
            ),
            closes=lambda f: f.get("policy_retention_days") == f.get("configured_retention_days"),
            assignee=A.RECORDS_REQUESTER,
            effort=E.MODERATE,
            scope=G.JURISDICTION,
        ),
        # 4 — Stale evidence: currency STALE/HISTORICAL for the predicate class.
        _t(
            slug="stale_evidence",
            version="v1",
            fires=lambda f: f.get("currency") in {"STALE", "HISTORICAL"},
            closes=lambda f: f.get("currency") == "CURRENT",
            assignee=A.ANALYST,
            effort=E.QUICK,
            scope=G.JURISDICTION,
        ),
        # 5 — Orphaned device: asset with manufacturer, no operator.
        _t(
            slug="orphaned_device",
            version="v1",
            fires=lambda f: bool(f.get("has_manufacturer")) and not f.get("has_operator"),
            closes=lambda f: bool(f.get("has_operator")),
            assignee=A.FIELD_MAPPER,
            effort=E.MODERATE,
            scope=G.JURISDICTION,
        ),
        # 6 — New sharing node: org in a network list, absent from the registry.
        _t(
            slug="new_sharing_node",
            version="v1",
            fires=lambda f: bool(f.get("in_network_list")) and not f.get("in_registry"),
            closes=lambda f: bool(f.get("in_registry")),
            assignee=A.ANALYST,
            effort=E.MODERATE,
            scope=G.GLOBAL,
        ),
        # 7 — Vendor replacement: cancellation + new deployment in window.
        _t(
            slug="vendor_replacement",
            version="v1",
            fires=lambda f: (
                bool(f.get("cancellation_in_window")) and bool(f.get("new_deployment_in_window"))
            ),
            closes=lambda f: (
                bool(f.get("replacement_linked"))
                or not (f.get("cancellation_in_window") and f.get("new_deployment_in_window"))
            ),
            assignee=A.ANALYST,
            effort=E.MODERATE,
            scope=G.JURISDICTION,
        ),
        # 8 — Portal disappeared: artifact disappearance event.
        _t(
            slug="portal_disappeared",
            version="v1",
            fires=lambda f: bool(f.get("disappearance_event")),
            closes=lambda f: (
                bool(f.get("disappearance_explained")) or not f.get("disappearance_event")
            ),
            assignee=A.ANALYST,
            effort=E.MODERATE,
            scope=G.JURISDICTION,
        ),
        # 9 — Portal appeared, no known deployment: new portal, no deployment record.
        _t(
            slug="portal_appeared_no_deployment",
            version="v1",
            fires=lambda f: bool(f.get("new_portal")) and not f.get("deployment_record"),
            closes=lambda f: bool(f.get("deployment_record")),
            assignee=A.ANALYST,
            effort=E.MODERATE,
            scope=G.JURISDICTION,
        ),
        # 10 — Contract expiring: end_date within N days, no renewal evidence.
        _t(
            slug="contract_expiring",
            version="v1",
            fires=lambda f: (
                "days_to_end_date" in f
                and _i(f, "days_to_end_date") <= _i(f, "threshold_days", 90)
                and not f.get("renewal_evidence")
            ),
            closes=lambda f: (
                bool(f.get("renewal_evidence"))
                or _i(f, "days_to_end_date") > _i(f, "threshold_days", 90)
            ),
            assignee=A.LOCAL_GROUP,
            effort=E.MODERATE,
            scope=G.JURISDICTION,
            priority_fn=lambda f: _expiry_priority(f),
        ),
        # 11 — Sharing asymmetry: edge asserted by one side only.
        _t(
            slug="sharing_asymmetry",
            version="v1",
            fires=lambda f: bool(f.get("edge_asserted_by_one_side_only")),
            closes=lambda f: (
                bool(f.get("corroborated"))
                or bool(f.get("retracted"))
                or not f.get("edge_asserted_by_one_side_only")
            ),
            assignee=A.ANALYST,
            effort=E.MODERATE,
            scope=G.GLOBAL,
        ),
        # 12 — Device/jurisdiction mismatch: asset in A attributed to B.
        _t(
            slug="device_jurisdiction_mismatch",
            version="v1",
            fires=lambda f: (
                "located_in" in f and "attributed_to" in f and f["located_in"] != f["attributed_to"]
            ),
            closes=lambda f: (
                f.get("located_in") == f.get("attributed_to") or bool(f.get("mismatch_resolved"))
            ),
            assignee=A.FIELD_MAPPER,
            effort=E.MODERATE,
            scope=G.JURISDICTION,
        ),
        # 13 — Retention changed without policy change: config change, no policy claim.
        _t(
            slug="retention_changed_without_policy",
            version="v1",
            fires=lambda f: bool(f.get("config_changed")) and not f.get("policy_claim_present"),
            closes=lambda f: bool(f.get("policy_claim_present")),
            assignee=A.RECORDS_REQUESTER,
            effort=E.MODERATE,
            scope=G.JURISDICTION,
        ),
        # 14 — Network org without jurisdiction: org resolved, no jurisdiction.
        _t(
            slug="network_org_without_jurisdiction",
            version="v1",
            fires=lambda f: bool(f.get("org_resolved")) and not f.get("has_jurisdiction"),
            closes=lambda f: bool(f.get("has_jurisdiction")),
            assignee=A.ANALYST,
            effort=E.MODERATE,
            scope=G.GLOBAL,
        ),
        # 15 — Adoption without corroboration: Atlas row; no portal, contract, or device.
        _t(
            slug="adoption_without_corroboration",
            version="v1",
            fires=lambda f: (
                bool(f.get("atlas_row"))
                and not (f.get("has_portal") or f.get("has_contract") or f.get("has_device"))
            ),
            closes=lambda f: bool(
                f.get("has_portal") or f.get("has_contract") or f.get("has_device")
            ),
            assignee=A.RECORDS_REQUESTER,
            effort=E.SUBSTANTIAL,
            scope=G.JURISDICTION,
        ),
        # 16 — Grant with no deployment: surveillance grant awarded, no follow-up evidence.
        _t(
            slug="grant_without_deployment",
            version="v1",
            fires=lambda f: bool(f.get("grant_awarded")) and not f.get("deployment_evidence"),
            closes=lambda f: bool(f.get("deployment_evidence")),
            assignee=A.ANALYST,
            effort=E.MODERATE,
            scope=G.JURISDICTION,
        ),
        # 17 — Vendor acquisition relink: acquisition event; products need re-linking.
        _t(
            slug="vendor_acquisition_relink",
            version="v1",
            fires=lambda f: (
                bool(f.get("acquisition_event")) and bool(f.get("products_need_relinking"))
            ),
            closes=lambda f: not f.get("products_need_relinking") or not f.get("acquisition_event"),
            assignee=A.CURATOR,
            effort=E.MODERATE,
            scope=G.GLOBAL,
        ),
        # 18 — Sole-source / Tier-F support: a claim's only support is R5/R6.
        _t(
            slug="sole_source_tier_f_support",
            version="v1",
            fires=lambda f: f.get("only_support_reliability") in {"R5", "R6"},
            closes=lambda f: (
                bool(f.get("has_higher_reliability_support"))
                or f.get("only_support_reliability") not in {"R5", "R6"}
            ),
            assignee=A.ANALYST,
            effort=E.MODERATE,
            scope=G.GLOBAL,
        ),
        # 19 — Long-unverified claim: `unreviewed` beyond threshold.
        _t(
            slug="long_unverified_claim",
            version="v1",
            fires=lambda f: (
                f.get("review_status") == "unreviewed"
                and _i(f, "age_days") > _i(f, "threshold_days", 180)
            ),
            closes=lambda f: (
                f.get("review_status") != "unreviewed"
                or _i(f, "age_days") <= _i(f, "threshold_days", 180)
            ),
            assignee=A.CURATOR,
            effort=E.QUICK,
            scope=G.GLOBAL,
        ),
        # 20 — Link rot: artifact URL now 404s.
        _t(
            slug="link_rot",
            version="v1",
            fires=lambda f: _i(f, "url_status", 200) == 404,
            closes=lambda f: _i(f, "url_status", 200) != 404 or bool(f.get("archived_replacement")),
            assignee=A.DEVELOPER,
            effort=E.QUICK,
            scope=G.GLOBAL,
        ),
        # 21 — Re-extraction available: better parser version exists for stored captures.
        _t(
            slug="re_extraction_available",
            version="v1",
            fires=lambda f: _i(f, "stored_parser_version") < _i(f, "available_parser_version"),
            closes=lambda f: _i(f, "stored_parser_version") >= _i(f, "available_parser_version"),
            assignee=A.DEVELOPER,
            effort=E.MODERATE,
            scope=G.GLOBAL,
        ),
        # 22 — Candidate duplicate entities: ER tier 4/5 pair.
        _t(
            slug="candidate_duplicate_entities",
            version="v1",
            fires=lambda f: _i(f, "er_tier") in {4, 5},
            closes=lambda f: bool(f.get("adjudicated")) or _i(f, "er_tier") not in {4, 5},
            assignee=A.CURATOR,
            effort=E.MODERATE,
            scope=G.GLOBAL,
        ),
        # 23 — Litigation without docket: proceeding with no court record link.
        _t(
            slug="litigation_without_docket",
            version="v1",
            fires=lambda f: bool(f.get("proceeding_present")) and not f.get("docket_link"),
            closes=lambda f: bool(f.get("docket_link")),
            assignee=A.ANALYST,
            effort=E.MODERATE,
            scope=G.JURISDICTION,
        ),
        # 24 — Incident with only secondary sources: no R1/R2 support.
        _t(
            slug="incident_only_secondary_sources",
            version="v1",
            fires=lambda f: bool(f.get("incident_present")) and not f.get("has_primary_source"),
            closes=lambda f: bool(f.get("has_primary_source")),
            assignee=A.RECORDS_REQUESTER,
            effort=E.MODERATE,
            scope=G.JURISDICTION,
        ),
        # 25 — Unmapped vocabulary value: source value outside the vocabulary.
        _t(
            slug="unmapped_vocabulary_value",
            version="v1",
            fires=lambda f: (
                bool(f.get("source_value_present")) and not f.get("value_in_vocabulary")
            ),
            closes=lambda f: bool(f.get("value_in_vocabulary")),
            assignee=A.CURATOR,
            effort=E.QUICK,
            scope=G.GLOBAL,
        ),
        # 26 — Authorized but not deployed: authorization=authorized ∧ physical=not_installed.
        _t(
            slug="authorized_not_deployed",
            version="v1",
            fires=lambda f: (
                f.get("authorization") == "authorized" and f.get("physical") == "not_installed"
            ),
            closes=lambda f: (
                f.get("physical") != "not_installed"
                or f.get("authorization") != "authorized"
                or bool(f.get("resolved"))
            ),
            assignee=A.ANALYST,
            effort=E.MODERATE,
            scope=G.JURISDICTION,
        ),
        # 27 — Canceled but installed: procurement=canceled ∧ physical=installed.
        _t(
            slug="canceled_but_installed",
            version="v1",
            fires=lambda f: f.get("procurement") == "canceled" and f.get("physical") == "installed",
            closes=lambda f: (
                f.get("physical") != "installed"
                or f.get("procurement") != "canceled"
                or bool(f.get("resolved"))
            ),
            assignee=A.FIELD_MAPPER,
            effort=E.MODERATE,
            scope=G.JURISDICTION,
        ),
        # 28 — Free-trial capability: operational=active with no procurement transition.
        _t(
            slug="free_trial_capability",
            version="v1",
            fires=lambda f: (
                f.get("operational") == "active" and not f.get("procurement_transition")
            ),
            closes=lambda f: (
                bool(f.get("procurement_transition")) or f.get("operational") != "active"
            ),
            assignee=A.RECORDS_REQUESTER,
            effort=E.MODERATE,
            scope=G.JURISDICTION,
        ),
        # 29 — Cooperative contract unexplored: piggyback contract with no master record.
        _t(
            slug="cooperative_contract_unexplored",
            version="v1",
            fires=lambda f: bool(f.get("piggyback_contract")) and not f.get("master_record"),
            closes=lambda f: bool(f.get("master_record")),
            assignee=A.DOCUMENT_REVIEWER,
            effort=E.MODERATE,
            scope=G.JURISDICTION,
        ),
        # 30 — Coverage hole: jurisdiction with population above threshold and zero evidence.
        _t(
            slug="coverage_hole",
            version="v1",
            fires=lambda f: (
                _i(f, "population") >= _i(f, "threshold_population", 50_000)
                and _i(f, "evidence_count") == 0
            ),
            closes=lambda f: _i(f, "evidence_count") > 0 or bool(f.get("coverage_recorded")),
            assignee=A.LOCAL_GROUP,
            effort=E.SUBSTANTIAL,
            scope=G.JURISDICTION,
            priority_fn=lambda f: _coverage_hole_priority(f),
        ),
        # 31 — Unresolved contradiction aging: open contradiction beyond threshold.
        _t(
            slug="unresolved_contradiction_aging",
            version="v1",
            fires=lambda f: (
                bool(f.get("contradiction_open"))
                and _i(f, "open_age_days") > _i(f, "threshold_days", 30)
            ),
            closes=lambda f: (
                not f.get("contradiction_open")
                or _i(f, "open_age_days") <= _i(f, "threshold_days", 30)
            ),
            assignee=A.CURATOR,
            effort=E.MODERATE,
            scope=G.GLOBAL,
        ),
        # 32 — Candidate asset awaiting verification: CandidateAsset corroborated, unpromoted.
        _t(
            slug="candidate_asset_awaiting_verification",
            version="v1",
            fires=lambda f: bool(f.get("candidate_corroborated")) and not f.get("promoted"),
            closes=lambda f: bool(f.get("promoted")),
            assignee=A.FIELD_MAPPER,
            effort=E.MODERATE,
            scope=G.JURISDICTION,
        ),
        # 33 — Contract amendment chain incomplete: terms contradicted by a later source,
        #      no amends_contract child on file.
        _t(
            slug="contract_amendment_chain_incomplete",
            version="v1",
            fires=lambda f: (
                bool(f.get("terms_contradicted_by_later_source"))
                and not f.get("amends_contract_child")
            ),
            closes=lambda f: (
                bool(f.get("amends_contract_child"))
                or not f.get("terms_contradicted_by_later_source")
            ),
            assignee=A.RECORDS_REQUESTER,
            effort=E.MODERATE,
            scope=G.JURISDICTION,
        ),
        # 34 — Sharing snapshot stale: newest configured_access observation exceeds the
        #      FAST volatility threshold.
        _t(
            slug="sharing_snapshot_stale",
            version="v1",
            fires=lambda f: _i(f, "configured_access_age_days") > _i(f, "fast_threshold_days", 180),
            closes=lambda f: (
                _i(f, "configured_access_age_days") <= _i(f, "fast_threshold_days", 180)
            ),
            assignee=A.RECORDS_REQUESTER,
            effort=E.MODERATE,
            scope=G.JURISDICTION,
        ),
    )


def _expiry_priority(facts: Facts) -> float:
    """Urgency for a contract-expiring task: sooner expiry ⇒ higher priority (§33.1)."""
    if "priority" in facts:
        return _f(facts, "priority", 0.5)
    days = _i(facts, "days_to_end_date", 90)
    threshold = max(_i(facts, "threshold_days", 90), 1)
    return max(0.0, min(1.0, 1.0 - days / threshold))


def _coverage_hole_priority(facts: Facts) -> float:
    """Urgency for a coverage hole: larger unmapped population ⇒ higher priority (§33.1)."""
    if "priority" in facts:
        return _f(facts, "priority", 0.5)
    population = _i(facts, "population")
    # A soft saturating scale; a million-person hole approaches the ceiling.
    return min(1.0, population / 1_000_000)


#: The 34 §33.2 task types, in catalog order.
CATALOG_TASK_TYPES: tuple[TaskType, ...] = _catalog_task_types()

# --- SIG-TASK-004: the §31 contradiction detector → task type mapping ---------
# The authoritative detector taxonomy is the §31 `contradiction_type` vocabulary
# (`reconcile.model.CONTRADICTION_TYPES`, 9 members). Every member routes to the
# catalog task that resolves it, so detection always has a route to resolution.
# The map is many-to-one: the §33.2 catalog is coarser than the §31 vocabulary, so
# related contradiction classes share the task that resolves them. Keys are the
# literal `contradiction_type` values (kept in lockstep with `reconcile.model` by
# ``tests/tasks/test_tasks_catalog.py``, which cross-checks against the real set).
CONTRADICTION_TASK_MAP: Mapping[str, str] = {
    # Two sources give divergent values for the same predicate — obtain the
    # authoritative record. `conflicting_retention` is the catalog's archetypal
    # value-vs-value divergence task.
    "value_disagreement": "conflicting_retention",
    # Different count *predicates*/*bases* conflated as one — reconcile the counts.
    "predicate_conflation": "missing_physical_devices",
    "count_basis_mismatch": "missing_physical_devices",
    # A value outside its declared domain/vocabulary — map it or reject it.
    "value_domain_mismatch": "unmapped_vocabulary_value",
    # An edge asserted by only one side — corroborate or retract (exact match).
    "sharing_asymmetry": "sharing_asymmetry",
    # Policy says X, configuration does Y — §33.2 #3's detector is literally this.
    "policy_configuration_divergence": "conflicting_retention",
    # A lifecycle state that cannot co-occur (e.g. canceled yet installed).
    "temporal_impossibility": "canceled_but_installed",
    # Two records may be the same entity — adjudicate the ER pair.
    "identity_ambiguity": "candidate_duplicate_entities",
    # Apparent corroboration is one source copied without attribution ⇒ effectively
    # sole-source — verify that independent support exists.
    "undeclared_copying": "sole_source_tier_f_support",
}


def build_catalog() -> TaskTypeRegistry:
    """Register the full §33.2 catalog and return the registry (SIG-TASK-003).

    Registration is the SIG-TASK-002 gate: a row whose ``closing_condition`` is not
    testable would be refused here, so a successful build is itself the proof that
    every catalog row names a testable closing condition.
    """
    registry = TaskTypeRegistry()
    for task_type in CATALOG_TASK_TYPES:
        registry.register(task_type)
    return registry


def catalog() -> TaskTypeRegistry:
    """A freshly built catalog registry (§33.2). Alias for :func:`build_catalog`."""
    return build_catalog()
