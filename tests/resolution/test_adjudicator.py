# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The LLM (rules-encoded) adjudicator for the gold-set bootstrap (P28.1, ADR-099)."""

from __future__ import annotations

from datetime import date

from resolution.adjudicator import (
    CandidatePair,
    PairRecord,
    RuleBasedLLMAdjudicator,
    adjudicate_pairs,
    weights_of,
)
from resolution.gold_set import GoldLabel, build_gold_set


def _pair(pair_id: str, left: PairRecord, right: PairRecord, weight: float) -> CandidatePair:
    return CandidatePair(pair_id=pair_id, left=left, right=right, weight=weight)


def test_shared_canonical_identifier_is_a_match() -> None:
    adj = RuleBasedLLMAdjudicator()
    assert adj.adjudicator_id == "llm:rulebased@v1"
    p = _pair(
        "p1",
        PairRecord("a", "okc police", "OK", "us.le.municipal_police", frozenset({"ori:OK05501"})),
        PairRecord(
            "b", "oklahoma city pd", "OK", "us.le.municipal_police", frozenset({"ori:OK05501"})
        ),
        9.0,
    )
    a = adj.adjudicate(p, dated=date(2026, 9, 1))
    assert a.label == GoldLabel.MATCH
    assert "shared canonical identifier" in a.note
    assert a.adjudicator == "llm:rulebased@v1"


def test_different_state_is_a_non_match() -> None:
    adj = RuleBasedLLMAdjudicator()
    p = _pair(
        "p2",
        PairRecord("a", "springfield police", "IL", "us.le.municipal_police"),
        PairRecord("b", "springfield police", "MO", "us.le.municipal_police"),
        6.0,
    )
    assert adj.adjudicate(p, dated=date(2026, 9, 1)).label == GoldLabel.NON_MATCH


def test_name_duplicate_alone_is_not_enough_information() -> None:
    adj = RuleBasedLLMAdjudicator()
    p = _pair(
        "p3",
        PairRecord("a", "metro police", "TX", "us.le.municipal_police"),
        PairRecord("b", "metro police", "TX", "us.le.municipal_police"),
        3.0,
    )
    # A name near-duplicate ALONE is not sufficient (rules) -> honest uncertainty.
    assert adj.adjudicate(p, dated=date(2026, 9, 1)).label == GoldLabel.NOT_ENOUGH_INFORMATION


def test_no_signal_is_non_match() -> None:
    adj = RuleBasedLLMAdjudicator()
    p = _pair(
        "p4",
        PairRecord("a", "acme cameras", "CA", "vendor"),
        PairRecord("b", "beta surveillance", "CA", "vendor"),
        -1.0,
    )
    assert adj.adjudicate(p, dated=date(2026, 9, 1)).label == GoldLabel.NON_MATCH


def test_kappa_between_seed_and_llm_over_a_gold_set() -> None:
    adj = RuleBasedLLMAdjudicator()
    dated = date(2026, 9, 1)
    pairs = [
        _pair(
            "p1",
            PairRecord("a", "okc pd", "OK", "us.le.municipal_police", frozenset({"ori:OK055"})),
            PairRecord("b", "okc police", "OK", "us.le.municipal_police", frozenset({"ori:OK055"})),
            9.0,
        ),
        _pair(
            "p2",
            PairRecord("a", "springfield pd", "IL", "us.le.municipal_police"),
            PairRecord("b", "springfield pd", "MO", "us.le.municipal_police"),
            6.0,
        ),
        _pair(
            "p3",
            PairRecord("a", "metro police", "TX", "us.le.municipal_police"),
            PairRecord("b", "metro police", "TX", "us.le.municipal_police"),
            3.0,
        ),
    ]
    llm = adjudicate_pairs(pairs, adj, dated=dated)
    # A maintainer seed that AGREES on the two clear pairs and DIFFERS on the ambiguous
    # boundary pair (p3): the maintainer, using external knowledge, calls it a match.
    from resolution.gold_set import Adjudication

    seed = [
        Adjudication("p1", "seed:maintainer@sig", GoldLabel.MATCH, dated, "1", "shared ORI"),
        Adjudication(
            "p2", "seed:maintainer@sig", GoldLabel.NON_MATCH, dated, "1", "different state"
        ),
        Adjudication(
            "p3", "seed:maintainer@sig", GoldLabel.MATCH, dated, "1", "confirmed off-catalog"
        ),
    ]
    gs = build_gold_set(
        weights=weights_of(pairs), adjudications=[*llm, *seed], holdout_fraction=0.0
    )
    k = gs.kappa("seed:maintainer@sig", adj.adjudicator_id)
    assert -1.0 <= k <= 1.0
    # p3 is a genuine disagreement -> disputed (label None), never a silent pick.
    assert gs.by_id("p3").disputed
    assert not gs.by_id("p1").disputed
