# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Temporal kinds, ongoing-rendering, and the two-axis as-of query contract (§9).

Two things live here:

* The **bound kinds** (§9.3) and the rule that `valid_to_kind = 'ongoing'` is
  NEVER "true now" (SIG-TIME-004/005): every consumer MUST render an ongoing
  bound with the observation date attached. `render_valid_bound` produces the
  only conformant strings; `assert_conformant_rendering` rejects the forbidden
  "currently ..." phrasing so the rule is testable.

* The **as-of query contract** (§9.4). Only two of the five temporal dimensions
  are queryable AS OF axes (SIG-TIME-016): T1 valid time (`as_of_world`) and T5
  assertion time (`as_of_belief`). :class:`AsOf` carries both, defaults them
  *explicitly* (world = today, belief = now — SIG-TIME-007), builds the parametric
  `WHERE` predicate every read path shares, and names which of the four questions
  a given pair asks (the fourth — both pinned to the past — is what makes a SIG
  citation reproducible, SIG-TIME-008/009). The database-side counterpart is the
  `claim_as_of` / `resolution_as_of` SQL functions in the `temporal_invariants`
  sqitch change; this predicate is byte-for-byte the same filter they apply.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum


class ValidBoundKind(StrEnum):
    """The closed vocabulary for `valid_from_kind` / `valid_to_kind` (§9.3)."""

    EXACT = "exact"
    ONGOING = "ongoing"
    UNKNOWN = "unknown"
    BEFORE = "before"
    AFTER = "after"
    NEVER = "never"


class ObservedAtKind(StrEnum):
    """The closed vocabulary for `observed_at_kind` (§16.2)."""

    EXACT = "exact"
    APPROXIMATE = "approximate"
    BOUNDED_ABOVE = "bounded_above"
    UNKNOWN = "unknown"


def _as_day(value: datetime | date | str) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def render_valid_bound(
    kind: ValidBoundKind | str,
    bound: datetime | date | str | None,
    *,
    observed_at: datetime | date | str | None = None,
) -> str:
    """Render one validity bound conformantly with its kind (§9.3, SIG-TIME-005).

    `ongoing` is the load-bearing case: it MUST be rendered with the observation
    date attached ("as observed <date>"), never as "currently"/"now". Rendering an
    ongoing bound without an observation date is non-conformant and raises.
    """
    kind = ValidBoundKind(kind)
    if kind is ValidBoundKind.ONGOING:
        if observed_at is None:
            raise ValueError(
                "an 'ongoing' bound MUST be rendered with its observation date "
                "attached (SIG-TIME-005); 'currently'/'now' is non-conformant"
            )
        return f"ongoing (as observed {_as_day(observed_at)})"
    if kind is ValidBoundKind.UNKNOWN:
        return "unknown"
    if kind is ValidBoundKind.NEVER:
        return "n/a"
    if bound is None:
        raise ValueError(f"kind {kind.value!r} requires a bound instant")
    if kind is ValidBoundKind.EXACT:
        return _as_day(bound)
    if kind is ValidBoundKind.BEFORE:
        return f"by {_as_day(bound)}"
    return f"from {_as_day(bound)}"  # AFTER


# Phrasings that assert an ongoing edge is true *now* — the P12 violation
# SIG-TIME-005 forbids ("installed is not active").
_FORBIDDEN_NOW_TERMS = ("currently", "presently", "as of now", "right now", "at present")


def assert_conformant_rendering(text: str, kind: ValidBoundKind | str) -> None:
    """Fail if an `ongoing` rendering claims present-tense truth (SIG-TIME-005)."""
    if ValidBoundKind(kind) is not ValidBoundKind.ONGOING:
        return
    lowered = text.lower()
    for term in _FORBIDDEN_NOW_TERMS:
        if term in lowered:
            raise ValueError(
                f"non-conformant ongoing rendering {text!r}: {term!r} asserts "
                f"present-tense truth; attach the observation date instead "
                f"(SIG-TIME-005)"
            )
    if "observed" not in lowered:
        raise ValueError(
            f"non-conformant ongoing rendering {text!r}: an ongoing bound MUST "
            f"carry its observation date (SIG-TIME-005)"
        )


# --- as-of query contract (§9.4) ---------------------------------------------


class AsOfQuestion(StrEnum):
    """The four questions the two as-of axes span (§9.4)."""

    CURRENT_BELIEF_NOW = "what we currently believe is true now"
    CURRENT_BELIEF_PAST = "what we now believe was true then"
    PAST_BELIEF_NOW = "what we believed, on that date, was true now"
    PAST_BELIEF_PAST = "what we believed on date B about the state on date W"


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _coerce(value: datetime | date | None, *, default: datetime) -> datetime:
    if value is None:
        return default
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime(value.year, value.month, value.day, tzinfo=UTC)


@dataclass(frozen=True)
class AsOf:
    """A resolved pair of as-of axes and the shared query predicate they imply.

    `world` filters T1 (valid time, `valid_period`); `belief` filters T5
    (assertion time, `sys_period`). Both default *explicitly* (SIG-TIME-007):
    `world = today`, `belief = now`. Observation time (T2) is deliberately NOT an
    axis here — it is an ordering scalar, not something you travel along
    (SIG-TIME-016).
    """

    world: datetime
    belief: datetime
    world_defaulted: bool
    belief_defaulted: bool

    @classmethod
    def resolve(
        cls,
        as_of_world: datetime | date | None = None,
        as_of_belief: datetime | date | None = None,
        *,
        now: datetime | None = None,
    ) -> AsOf:
        """Resolve the two axes, filling defaults explicitly (SIG-TIME-007)."""
        current = now or _utcnow()
        today = datetime(current.year, current.month, current.day, tzinfo=UTC)
        return cls(
            world=_coerce(as_of_world, default=today),
            belief=_coerce(as_of_belief, default=current),
            world_defaulted=as_of_world is None,
            belief_defaulted=as_of_belief is None,
        )

    def where(self, *, valid_col: str = "valid_period", sys_col: str = "sys_period") -> str:
        """The parametric `WHERE` fragment (two placeholders: world, belief)."""
        return f"{valid_col} @> %s::timestamptz AND {sys_col} @> %s::timestamptz"

    def params(self) -> tuple[datetime, datetime]:
        """Bind parameters for :meth:`where`, in order (world, belief)."""
        return (self.world, self.belief)

    def question(self, *, now: datetime | None = None) -> AsOfQuestion:
        """Which of the four §9.4 questions this pair asks."""
        current = now or _utcnow()
        today = datetime(current.year, current.month, current.day, tzinfo=UTC)
        world_is_now = self.world >= today
        belief_is_now = self.belief_defaulted or self.belief >= current
        if world_is_now and belief_is_now:
            return AsOfQuestion.CURRENT_BELIEF_NOW
        if not world_is_now and belief_is_now:
            return AsOfQuestion.CURRENT_BELIEF_PAST
        if world_is_now and not belief_is_now:
            return AsOfQuestion.PAST_BELIEF_NOW
        return AsOfQuestion.PAST_BELIEF_PAST
