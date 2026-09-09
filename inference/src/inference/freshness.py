# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Freshness measured relative to predicate volatility, not absolute days (§32.4).

A two-year-old contract *signing date* is fresh; a two-year-old *active device
count* is historical (SIG-METRIC-006). So freshness MUST be a function of the
predicate's volatility class and half-life, never a flat age threshold. That
derivation already exists — it is the §28.3 currency `C1..C4` the resolver uses
(:func:`reconcile.weight.currency`) — so this module reuses it rather than
inventing a second, divergent notion of "stale".

On top of the per-claim currency it builds the §32.4 per-source freshness surface
(SIG-METRIC-007): for each source, the last successful run, the last content change,
the current status, and the count of entities whose evidence is stale for their
predicate class — the data a public data-freshness page renders.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime

from reconcile.weight import currency, predicate_meta

__all__ = [
    "CURRENCY_LABEL",
    "STALE_CURRENCIES",
    "predicate_currency",
    "is_stale_for_predicate",
    "SourceFreshness",
    "source_freshness",
]

#: Human labels for the §28.3 currency classes (C1..C4).
CURRENCY_LABEL: dict[str, str] = {
    "C1": "current",
    "C2": "aging",
    "C3": "stale",
    "C4": "historical",
}

#: The currency classes that count as "stale for the predicate class" (§32.4).
#: C1/C2 are still within a useful multiple of the half-life; C3/C4 are not.
STALE_CURRENCIES: frozenset[str] = frozenset({"C3", "C4"})


def predicate_currency(predicate_id: str, *, observed_at: date, as_of: date) -> str:
    """The currency class `C1..C4` of an observation, per the predicate (SIG-METRIC-006).

    Delegates to the §28.3 derivation over the predicate registry's volatility class
    and half-life — so the *same* age yields a different currency for a FAST predicate
    than for an IMMUTABLE one. This is what "relative to volatility, not absolute
    days" means concretely.
    """
    meta = predicate_meta(predicate_id)
    return currency(
        volatility_class=meta["volatility_class"],
        half_life=meta["half_life"],
        observed_at=observed_at,
        as_of=as_of,
    )


def is_stale_for_predicate(predicate_id: str, *, observed_at: date, as_of: date) -> bool:
    """Whether an observation is stale for its predicate class (§32.4, SIG-METRIC-007)."""
    return (
        predicate_currency(predicate_id, observed_at=observed_at, as_of=as_of) in STALE_CURRENCIES
    )


@dataclass(frozen=True)
class SourceFreshness:
    """The per-source freshness surface a data-freshness page shows (SIG-METRIC-007).

    `stale_count` is the number of entities from this source whose evidence is stale
    *for their predicate class* — computed via :func:`is_stale_for_predicate`, not a
    flat age. `status` is the source's own operational status (e.g. `ok`, `degraded`,
    `blocked`); it is carried verbatim, not inferred here.
    """

    source_id: str
    last_successful_run: datetime | None
    last_content_change: datetime | None
    status: str
    stale_count: int
    tracked_count: int

    def __post_init__(self) -> None:
        if self.stale_count < 0 or self.tracked_count < 0:
            raise ValueError(f"source {self.source_id!r} has a negative count")
        if self.stale_count > self.tracked_count:
            raise ValueError(
                f"source {self.source_id!r}: {self.stale_count} stale exceeds "
                f"{self.tracked_count} tracked"
            )

    def as_json(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "last_successful_run": (
                self.last_successful_run.isoformat() if self.last_successful_run else None
            ),
            "last_content_change": (
                self.last_content_change.isoformat() if self.last_content_change else None
            ),
            "status": self.status,
            "stale_count": self.stale_count,
            "tracked_count": self.tracked_count,
        }


def source_freshness(
    source_id: str,
    *,
    status: str,
    last_successful_run: datetime | None,
    last_content_change: datetime | None,
    observations: Iterable[tuple[str, date]],
    as_of: date,
) -> SourceFreshness:
    """Build the §32.4 freshness surface for one source (SIG-METRIC-007).

    `observations` is `(predicate_id, observed_at)` for each tracked entity; the
    stale count is those stale for their predicate class as of `as_of`. Freshness is
    per-predicate volatility throughout — a source of IMMUTABLE contract dates is
    never stale, however old (SIG-METRIC-006).
    """
    obs = list(observations)
    stale = sum(
        1
        for predicate_id, observed_at in obs
        if is_stale_for_predicate(predicate_id, observed_at=observed_at, as_of=as_of)
    )
    return SourceFreshness(
        source_id=source_id,
        last_successful_run=last_successful_run,
        last_content_change=last_content_change,
        status=status,
        stale_count=stale,
        tracked_count=len(obs),
    )
