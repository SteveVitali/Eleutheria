# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The reconciliation ruleset as data (SIG-RECON-005/012, SIG-STORE-017).

The ruleset is versioned, diffable, testable, and separately attributable from
the resolver. These tests pin its contract: it loads, it is versioned, its
strategy vocabulary is a superset of what the predicate registry names, and a
predicate with no strategy is not resolvable (SIG-RECON-013).
"""

from __future__ import annotations

import reconcile.ruleset as rmod
from reconcile.ruleset import load_ruleset
from reconcile.weight import predicate_registry


def test_ruleset_is_versioned_and_loads() -> None:
    rs = load_ruleset()
    assert rs.version
    assert rs.strategies
    assert rs.templates
    assert rs.support_terms and rs.agreement_terms and rs.prohibited_adjectives


def test_every_registry_strategy_is_in_the_ruleset_vocabulary() -> None:
    # SIG-RECON-012: predicates may only name a strategy the ruleset defines.
    named = {
        p["resolution_strategy"]
        for p in predicate_registry().values()
        if p.get("resolution_strategy")
    }
    rs = load_ruleset()
    assert named <= set(rs.strategies), named - set(rs.strategies)


def test_strategy_for_known_predicate() -> None:
    rs = load_ruleset()
    assert rs.strategy_for("active_device_count") == "latest_observation_wins"
    assert rs.strategy_for("contract_signed_date") == "authoritative_source_wins"


def test_strategy_for_never_resolve_is_returned_verbatim() -> None:
    rs = load_ruleset()
    # never_resolve is a real strategy; the resolver, not the ruleset, turns it
    # into UNRESOLVED.
    assert rs.strategy_for("asset_data_controller") == "never_resolve"


def test_recency_and_currency_flags_track_volatility() -> None:
    rs = load_ruleset()
    # IMMUTABLE: recency must not break a tie; currency can never make it stale.
    assert rs.recency_breaks_ties("contract_signed_date") is False
    assert rs.currency_can_stale("contract_signed_date") is False
    # FAST: both hold.
    assert rs.recency_breaks_ties("active_device_count") is True
    assert rs.currency_can_stale("active_device_count") is True


def test_tolerance_varies_by_volatility_class() -> None:
    rs = load_ruleset()
    # A fast-changing count tolerates more spread than a glacial one.
    assert rs.tolerance("active_device_count") == rs.numeric_tolerance["FAST"]
    assert rs.tolerance("active_device_count") > rs.numeric_tolerance["GLACIAL"]


def test_unknown_strategy_in_registry_is_rejected(monkeypatch) -> None:
    real = rmod.predicate_meta

    def fake(predicate_id: str) -> dict[str, object]:
        row = dict(real("active_device_count"))
        row["resolution_strategy"] = "made_up_strategy"
        return row

    monkeypatch.setattr(rmod, "predicate_meta", fake)
    rs = load_ruleset()
    try:
        rs.strategy_for("active_device_count")
    except ValueError as exc:
        assert "made_up_strategy" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected an unknown strategy to be rejected")
