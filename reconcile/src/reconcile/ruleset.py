# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The reconciliation ruleset — loaded as data, never hard-coded (SIG-RECON-005).

``RESOLVE`` is deterministic, rule-based code (SIG-RECON-004); the *policy* it
applies — numeric tolerances, rationale templates, the strategy vocabulary — is
this versioned, diffable, testable, separately-attributable artifact
(``data/ruleset.toml``, SIG-STORE-017). The per-predicate epistemics
(volatility, half-life, strategy, the directness matrix) are the ontology-owned
predicate registry the resolver also consumes (SIG-RECON-009); this module
exposes both behind one :class:`Ruleset` so the resolver has a single policy
surface.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from typing import Any

from .weight import predicate_meta

__all__ = ["Ruleset", "load_ruleset"]

#: Volatility classes for which currency is allowed to make the winner too stale
#: to assert (SIG-RECON-014 U5). IMMUTABLE/GLACIAL/SLOW change slowly enough that
#: a stale-but-unchallenged value is still the answer.
_U5_VOLATILE_CLASSES = frozenset({"MODERATE", "FAST", "VOLATILE"})


@cache
def _raw() -> dict[str, Any]:
    resource = files("reconcile").joinpath("data", "ruleset.toml")
    with resource.open("rb") as fh:
        return tomllib.load(fh)


@dataclass(frozen=True)
class Ruleset:
    """The resolved reconciliation policy: the ruleset file plus registry access.

    Instances are cheap immutable views; construct via :func:`load_ruleset`.
    """

    version: str
    numeric_tolerance: dict[str, float]
    strategies: dict[str, str]
    templates: dict[str, str]
    support_terms: tuple[str, ...]
    agreement_terms: tuple[str, ...]
    prohibited_adjectives: tuple[str, ...]

    # --- per-predicate epistemics (from the ontology-owned registry) ---------

    def predicate(self, predicate_id: str) -> dict[str, Any]:
        """The registry row for ``predicate_id`` (raises ``KeyError`` if absent)."""
        return predicate_meta(predicate_id)

    def strategy_for(self, predicate_id: str) -> str | None:
        """The predicate's resolution strategy, or ``None`` if the registry names
        none — silence in the ruleset is not resolvable (SIG-RECON-013)."""
        strategy = self.predicate(predicate_id).get("resolution_strategy")
        if not strategy:
            return None
        if strategy not in self.strategies:
            raise ValueError(
                f"predicate {predicate_id!r} names unknown strategy {strategy!r} "
                "(not in the ruleset strategy vocabulary, SIG-RECON-012)"
            )
        return strategy

    def volatility_class(self, predicate_id: str) -> str:
        return self.predicate(predicate_id)["volatility_class"]

    def half_life(self, predicate_id: str) -> str:
        return self.predicate(predicate_id)["half_life"]

    def recency_breaks_ties(self, predicate_id: str) -> bool:
        """Whether a newer observation may break a tie (SIG-RECON-010).

        For IMMUTABLE and GLACIAL predicates it MUST NOT: a newer claim about a
        2019 signing date has no advantage from being newer.
        """
        return self.volatility_class(predicate_id) not in {"IMMUTABLE", "GLACIAL"}

    def currency_can_stale(self, predicate_id: str) -> bool:
        """Whether U5 may fire for this predicate (SIG-RECON-014/015)."""
        return self.volatility_class(predicate_id) in _U5_VOLATILE_CLASSES

    def tolerance(self, predicate_id: str) -> float:
        """The relative-spread tolerance for a numeric predicate (U4; §10.7)."""
        cls = self.volatility_class(predicate_id)
        return self.numeric_tolerance.get(cls, self.numeric_tolerance["default"])

    def template(self, rationale_code: str) -> str:
        try:
            return self.templates[rationale_code]
        except KeyError:  # pragma: no cover - guarded by the template test
            raise KeyError(
                f"no rationale template for {rationale_code!r} (SIG-RECON-022)"
            ) from None


@cache
def load_ruleset() -> Ruleset:
    """Load the committed ruleset (``data/ruleset.toml``), cached per process."""
    raw = _raw()
    style = raw["style"]
    return Ruleset(
        version=raw["ruleset_version"],
        numeric_tolerance=dict(raw["numeric_tolerance"]),
        strategies=dict(raw["strategies"]),
        templates=dict(raw["templates"]),
        support_terms=tuple(style["support_terms"]),
        agreement_terms=tuple(style["agreement_terms"]),
        prohibited_adjectives=tuple(style["prohibited_adjectives"]),
    )
