# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Adjudicators for the gold-set bootstrap (P28.1, ADR-099, design §2.3).

The gold set (:mod:`resolution.gold_set`) needs its pairs *adjudicated* against the
versioned prose rules (:func:`resolution.gold_set.adjudication_rules`). ``Adjudication``
already records ``adjudicator`` as a free string, so an **LLM adjudicator** slots in with
no schema change: it registers ``adjudicator="llm:<model>@<version>"``, reads the *same*
rules a human reads, and emits one of the three labels plus a rationale in ``note``.

Because an all-LLM gold set only measures agreement-with-the-LLM, this is a
*bootstrap*, calibrated against a human/maintainer seed (design §2.3, guardrail 1): the
LLM is trusted as gold only when its Cohen's κ against the seed clears the published bar
(``κ ≥ 0.7``); otherwise it is a *suggester* and its pairs route to review. The frozen
holdout is always human-verified (guardrail 2). This deliberate provisionality is the
open deferral **D-R6.1-EVAL**.

The LLM adjudicator here is realized as a **deterministic, rules-encoded** adjudicator
(``llm:rulebased@v1``): it applies the written adjudication rules programmatically so the
committed gold set and the eval numbers are reproducible in CI. Wiring a *live* model
adjudicator (with its stochastic rationale) behind the same :class:`Adjudicator`
interface — and re-measuring κ as the model drifts — is exactly the work
``D-R6.1-EVAL`` owns; the interface is designed so that swap needs no change here.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from .gold_set import GOLD_SET_RULES_VERSION, Adjudication, GoldLabel, adjudication_rules

__all__ = [
    "PairRecord",
    "CandidatePair",
    "Adjudicator",
    "RuleBasedLLMAdjudicator",
    "adjudicate_pairs",
    "weights_of",
]


@dataclass(frozen=True)
class PairRecord:
    """One side of a candidate pair — the fields an adjudicator reasons over."""

    entity_id: str
    normalized_name: str = ""
    state: str = ""
    organization_class: str = ""
    #: Canonical identifiers (scheme:value strings — ORI/GEOID/LEI/UEI/QID, gov domain).
    identifiers: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class CandidatePair:
    """A blocked candidate pair with its match weight (drives band stratification)."""

    pair_id: str
    left: PairRecord
    right: PairRecord
    weight: float


class Adjudicator(Protocol):
    """Anything that can label a candidate pair against the versioned rules."""

    @property
    def adjudicator_id(self) -> str: ...

    def adjudicate(self, pair: CandidatePair, *, dated: date) -> Adjudication: ...


@dataclass(frozen=True)
class RuleBasedLLMAdjudicator:
    """The bootstrap LLM adjudicator, applying the prose rules deterministically.

    Faithful to :func:`resolution.gold_set.adjudication_rules`:

    * a **shared canonical identifier** (or shared official government domain) is the
      corroboration the rules require → ``match``;
    * a **different state** denotes different organisations even on a name near-duplicate
      → ``non_match``;
    * a **name near-duplicate ALONE is not sufficient** for a match — same name/state/
      class but no shared identifier is genuinely ambiguous → ``not_enough_information``
      (the rules: "When in doubt … choose not_enough_information");
    * otherwise → ``non_match``.
    """

    model: str = "rulebased"
    version: str = "v1"

    @property
    def adjudicator_id(self) -> str:
        return f"llm:{self.model}@{self.version}"

    def adjudicate(self, pair: CandidatePair, *, dated: date) -> Adjudication:
        # Consult the versioned prose the same way a human adjudicator would.
        _ = adjudication_rules()
        label, note = self._decide(pair)
        return Adjudication(
            pair_id=pair.pair_id,
            adjudicator=self.adjudicator_id,
            label=label,
            dated=dated,
            ruleset_version=GOLD_SET_RULES_VERSION,
            note=note,
        )

    def _decide(self, pair: CandidatePair) -> tuple[GoldLabel, str]:
        left, right = pair.left, pair.right
        shared = left.identifiers & right.identifiers
        if shared:
            return GoldLabel.MATCH, f"shared canonical identifier {sorted(shared)[0]}"
        if left.state and right.state and left.state != right.state:
            return (
                GoldLabel.NON_MATCH,
                f"different state ({left.state} vs {right.state}); "
                "names similar but distinct bodies",
            )
        if (
            left.normalized_name
            and left.normalized_name == right.normalized_name
            and left.state == right.state
            and left.organization_class == right.organization_class
        ):
            return (
                GoldLabel.NOT_ENOUGH_INFORMATION,
                "same normalized name/state/class but no shared canonical identifier; "
                "a name near-duplicate alone is not sufficient (rules)",
            )
        return (
            GoldLabel.NON_MATCH,
            "no shared identifier and no corroborating signal for a match",
        )


def adjudicate_pairs(
    pairs: Iterable[CandidatePair],
    adjudicator: Adjudicator,
    *,
    dated: date,
) -> list[Adjudication]:
    """Adjudicate every pair with ``adjudicator`` (one :class:`Adjudication` each)."""
    return [adjudicator.adjudicate(p, dated=dated) for p in pairs]


def weights_of(pairs: Sequence[CandidatePair]) -> dict[str, float]:
    """The ``pair_id -> weight`` map :func:`resolution.gold_set.build_gold_set` needs."""
    return {p.pair_id: p.weight for p in pairs}
