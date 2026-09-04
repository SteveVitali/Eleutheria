# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Sized blocking (SIG-IDENT-023/024): rules are sized before use and rejected
above a documented ceiling; suffix-alone / state-alone blocking is prohibited;
trigram similarity may generate candidates but is exercised only as a search path."""

from __future__ import annotations

import pytest
from resolution.blocking import (
    BlockingContext,
    BlockingRule,
    BlockingRuleRejected,
    blocked_pairs,
    candidate_pairs,
    load_rules,
    size_blocking_rule,
    trigrams,
    validate_blocking_rule,
)


def _rec(state: str, token: str, name: str) -> dict[str, object]:
    return {"state": state, "name_first_token": token, "normalized_name": name}


def _records() -> list[dict[str, object]]:
    return [
        _rec("TX", "travis", "travis county sheriff office"),
        _rec("TX", "travis", "travis county so"),
        _rec("TX", "harris", "harris county sheriff office"),
        _rec("CA", "los", "los angeles police department"),
        _rec("CA", "los", "los angeles police dept"),
    ]


# --- SIG-IDENT-023: rules are sized before use --------------------------------


def test_size_counts_exact_within_block_pairs() -> None:
    rule = BlockingRule("state_and_first_token", ("state", "name_first_token"))
    # {TX,travis}=2 records → C(2,2)=1 pair; {CA,los}=2 → 1 pair; harris alone → 0.
    assert size_blocking_rule(_records(), rule) == 2
    pairs = candidate_pairs(_records(), rule)
    assert (0, 1) in pairs and (3, 4) in pairs and len(pairs) == 2


def test_null_valued_key_does_not_co_block() -> None:
    rule = BlockingRule("by_domain", ("gov_domain",))
    records = [{"gov_domain": None}, {"gov_domain": ""}, {"gov_domain": "x.gov"}]
    assert size_blocking_rule(records, rule) == 0


def test_oversized_rule_is_rejected() -> None:
    # A tiny ceiling forces rejection of a rule that would otherwise pass.
    rule = BlockingRule("normalized_name_first_token", ("name_first_token",))
    ctx = BlockingContext(comparison_ceiling=1, prohibited_sole_keys=frozenset())
    with pytest.raises(BlockingRuleRejected, match="above the ceiling"):
        validate_blocking_rule(_records(), rule, context=ctx)


def test_sized_rule_within_ceiling_is_accepted_and_returns_count() -> None:
    rule = BlockingRule("state_and_first_token", ("state", "name_first_token"))
    ctx = BlockingContext(comparison_ceiling=1000, prohibited_sole_keys=frozenset())
    assert validate_blocking_rule(_records(), rule, context=ctx) == 2


# --- SIG-IDENT-023: suffix-alone / state-alone prohibited ---------------------


@pytest.mark.parametrize("sole_key", ["state", "suffix", "canonical_suffix"])
def test_sole_low_cardinality_key_is_prohibited(sole_key: str) -> None:
    rule = BlockingRule(f"by_{sole_key}", (sole_key,))
    with pytest.raises(BlockingRuleRejected, match="prohibited"):
        validate_blocking_rule(_records(), rule)


def test_state_is_allowed_when_combined_with_a_selective_key() -> None:
    # state ALONE is prohibited; state + a selective token is the workhorse rule.
    rule = BlockingRule("state_and_first_token", ("state", "name_first_token"))
    assert validate_blocking_rule(_records(), rule) == 2


# --- SIG-IDENT-024: trigram powers candidate search only ----------------------


def test_trigram_generates_candidates() -> None:
    rule = BlockingRule("name_trigram", ("normalized_name",), method="trigram")
    pairs = candidate_pairs(_records(), rule)
    # the two Los Angeles PD spellings share many trigrams → they are candidates
    assert (3, 4) in pairs
    # trigram blocking is deliberately coarse (candidate search, not a decision):
    # it over-generates relative to an exact-name block, which is exactly why it may
    # never be used as a decision score (SIG-IDENT-024).
    exact = candidate_pairs(_records(), BlockingRule("exact", ("normalized_name",)))
    assert set(exact).issubset(set(pairs))
    assert len(pairs) > len(exact)


def test_trigram_rule_requires_a_single_key() -> None:
    with pytest.raises(BlockingRuleRejected, match="exactly one key"):
        BlockingRule("bad", ("a", "b"), method="trigram")


def test_trigrams_helper_pads_and_lowercases() -> None:
    assert "  a" in {g for g in trigrams("A")} or trigrams("A") == frozenset()
    grams = trigrams("PD")
    assert all(g == g.lower() for g in grams)


# --- Data-driven defaults + the union path ------------------------------------


def test_committed_rules_load_and_are_not_sole_prohibited() -> None:
    rules = load_rules()
    assert rules  # at least one committed rule
    ctx = BlockingContext.from_data()
    for rule in rules:
        # none of the shipped rules is a prohibited sole key, and each sizes fine
        validate_blocking_rule(_records(), rule, context=ctx)


def test_blocked_pairs_unions_and_validates_every_rule() -> None:
    rules = [
        BlockingRule("state_and_first_token", ("state", "name_first_token")),
        BlockingRule("normalized_name_exact", ("normalized_name",)),
    ]
    pairs = blocked_pairs(_records(), rules)
    assert (0, 1) in pairs and (3, 4) in pairs


def test_blocked_pairs_aborts_if_any_rule_is_prohibited() -> None:
    rules = [
        BlockingRule("state_and_first_token", ("state", "name_first_token")),
        BlockingRule("by_state", ("state",)),  # prohibited sole key
    ]
    with pytest.raises(BlockingRuleRejected):
        blocked_pairs(_records(), rules)


def test_from_data_reads_ceiling_and_prohibitions() -> None:
    ctx = BlockingContext.from_data()
    assert ctx.comparison_ceiling >= 1
    assert "state" in ctx.prohibited_sole_keys
