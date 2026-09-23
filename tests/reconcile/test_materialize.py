# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Unit tests for the resolution materializer's row mapping (P28.1, ADR-099).

The DB round-trip (sqitch deploy/revert/verify, insert-only, idempotent +0) is covered
by ``tests/db/test_resolution_materialize.py``; these are the pure mapping/accounting
tests that need no Postgres.
"""

from __future__ import annotations

import json
from datetime import date, datetime

from reconcile.materialize import (
    SUPPORT_TO_CONFIDENCE,
    MaterializeSummary,
    resolution_row,
)
from reconcile.resolve import Resolution
from reconcile.ruleset import load_ruleset


def _resolution(**overrides: object) -> Resolution:
    base: dict[str, object] = dict(
        subject_id="00000000-0000-0000-0000-000000000001",
        predicate_id="claimed_device_count",
        resolution_status="RESOLVED",
        value=299,
        support="CONFIRMED",
        agreement="UNCONTESTED",
        currency="CURRENT",
        contradiction_state="uncontested",
        strategy_id="authoritative_source_wins",
        rationale_code="RESOLVED_DIRECT",
        rationale_text="299, as reported by the city.",
        winning_claim_id="00000000-0000-0000-0000-0000000000aa",
        considered_claim_ids=("00000000-0000-0000-0000-0000000000aa",),
        supporting_claim_ids=("00000000-0000-0000-0000-0000000000aa",),
        dissenting_claim_ids=(),
        excluded=(),
        independence_class_ids=("cls-1",),
        rules_fired=("authoritative_source_wins",),
        ruleset_version="1.0.0",
        resolver_version="p08.1/1.0.0",
        input_digest="deadbeef",
        as_of_world=date(2026, 9, 1),
        as_of_belief=date(2026, 9, 1),
        computed_at=datetime(2026, 9, 1),
    )
    base.update(overrides)
    return Resolution(**base)  # type: ignore[arg-type]


def test_support_confidence_map_is_total_over_support_axis() -> None:
    for support in (
        "CONFIRMED",
        "STRONGLY_SUPPORTED",
        "PROBABLE",
        "WEAKLY_SUPPORTED",
        "UNSUPPORTED",
    ):
        assert support in SUPPORT_TO_CONFIDENCE


def test_resolved_row_maps_value_and_provenance() -> None:
    rs = load_ruleset()
    row = resolution_row(_resolution(), ruleset=rs)
    assert row is not None
    assert row["value_kind"] == "value"
    assert row["value_num"] == 299
    assert row["value_text"] == "299"
    assert row["confidence"] == "confirmed"
    assert row["contradiction_state"] == "uncontested"
    assert row["strategy_id"] == "authoritative_source_wins"
    assert row["input_digest"] == "deadbeef"
    assert row["winning_claim"] == "00000000-0000-0000-0000-0000000000aa"
    # evidence_counts is machine-readable JSON carrying support + agreement + counts.
    counts = json.loads(row["evidence_counts"])
    assert counts["support"] == "CONFIRMED"
    assert counts["agreement"] == "UNCONTESTED"
    assert counts["n_considered"] == 1
    # the ensure-vocab template comes from the versioned ruleset, not invented.
    assert row["_template"] == rs.template("RESOLVED_DIRECT")


def test_unresolved_conflict_is_still_materialized_with_no_value() -> None:
    row = resolution_row(
        _resolution(
            resolution_status="UNRESOLVED",
            value=None,
            support="WEAKLY_SUPPORTED",
            agreement="IRRECONCILABLE",
            contradiction_state="unresolved_conflict",
            rationale_code="UNRESOLVED_IRRECONCILABLE",
            winning_claim_id=None,
        ),
        ruleset=load_ruleset(),
    )
    assert row is not None
    # contradictions stay visible (§3.1): the envelope is written, value is NULL.
    assert row["value_text"] is None
    assert row["value_num"] is None
    assert row["contradiction_state"] == "unresolved_conflict"
    assert row["winning_claim"] is None


def test_no_strategy_envelope_is_not_materializable() -> None:
    # SIG-RECON-013: silence yields no decision to store.
    row = resolution_row(
        _resolution(strategy_id=None, rationale_code="UNRESOLVED_NO_STRATEGY"),
        ruleset=load_ruleset(),
    )
    assert row is None


def test_boolean_value_serializes_without_value_num() -> None:
    row = resolution_row(_resolution(value=True), ruleset=load_ruleset())
    assert row is not None
    assert row["value_text"] == "true"
    assert row["value_num"] is None


def test_summary_accounts_for_every_group() -> None:
    s = MaterializeSummary(
        considered_pairs=5,
        inserted=3,
        skipped_existing=1,
        skipped_unresolvable=1,
        resolved=2,
        unresolved=2,
    )
    assert s.written == 3
    assert s.as_dict()["considered_pairs"] == 5
