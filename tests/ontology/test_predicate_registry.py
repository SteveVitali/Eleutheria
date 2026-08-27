# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The predicate registry (§13.6, SIG-ONTO-066/067): every predicate carries a
volatility class + half-life, a resolution strategy, and a directness row."""

from __future__ import annotations

import json

import pytest
from support import generated_dir, load_vocab

VOLATILITY = {"IMMUTABLE", "GLACIAL", "SLOW", "MODERATE", "FAST", "VOLATILE"}
STRATEGIES = {
    "latest_observation_wins",
    "authoritative_source_wins",
    "interval_union",
    "interval_intersection",
    "max_support",
    "never_resolve",
}
DIRECTNESS = {"D1", "D2", "D3", "D4", "D5", "D6"}


@pytest.fixture(scope="module")
def registry() -> dict:
    # The generated artifact the reconcile ruleset (P08) will consume.
    return json.loads((generated_dir() / "registry" / "predicate_registry.json").read_text())


def test_registry_is_non_trivially_seeded(registry: dict) -> None:
    assert len(registry["predicates"]) >= 40
    ids = [p["predicate_id"] for p in registry["predicates"]]
    assert len(ids) == len(set(ids))


def test_every_predicate_has_volatility_strategy_and_directness_row(registry: dict) -> None:
    # SIG-ONTO-067 — the load-bearing acceptance criterion (AC3): a predicate with
    # no volatility class and no resolution strategy cannot be resolved.
    genres = set(registry["artifact_genres"])
    assert genres, "no artifact genres declared"
    for p in registry["predicates"]:
        pid = p["predicate_id"]
        assert p["volatility_class"] in VOLATILITY, pid
        assert p["half_life"], pid
        assert p["resolution_strategy"] in STRATEGIES, pid
        directness = p["directness"]
        assert set(directness) == genres, pid  # a full row over every artifact genre
        assert all(v in DIRECTNESS for v in directness.values()), pid


def test_immutable_and_glacial_predicates_use_non_recency_strategies(registry: dict) -> None:
    # SIG-RECON-010: recency must not break ties for IMMUTABLE/GLACIAL predicates.
    for p in registry["predicates"]:
        if p["volatility_class"] in {"IMMUTABLE", "GLACIAL"}:
            assert p["resolution_strategy"] != "latest_observation_wins", p["predicate_id"]


def test_contested_facts_are_never_resolved(registry: dict) -> None:
    # §12.4 / SIG-RECON-012: a contested data-controller assertion is recorded, not adjudicated.
    by_id = {p["predicate_id"]: p for p in registry["predicates"]}
    assert by_id["asset_data_controller"]["resolution_strategy"] == "never_resolve"


def test_registry_matches_source(registry: dict) -> None:
    src = load_vocab("predicates")
    assert len(registry["predicates"]) == len(src["predicates"])
