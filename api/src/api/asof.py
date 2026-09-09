# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""As-of semantics for every read endpoint (§37.2, §9.4).

Every read endpoint accepts ``as_of_world`` and ``as_of_belief`` (SIG-API-005),
resolves them through :class:`db.temporal.AsOf` — which defaults them *explicitly*
(world = today, belief = now, SIG-TIME-007) — and echoes the resolved instants
back so omission never silently means "latest". The resolved pair also decides
cacheability (SIG-API-006): a belief-pinned request is immutable and served with
a long, ``immutable`` cache lifetime; a ``now``-pinned request must not be cached.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from db.temporal import AsOf
from fastapi import HTTPException, Query
from starlette.responses import Response

from .models import AsOfEcho

#: One year, the immutable-response cache lifetime for a belief-pinned read.
_IMMUTABLE_MAX_AGE = 31_536_000


def _parse(value: str | None, *, name: str) -> datetime | date | None:
    """Parse an ISO-8601 date or datetime query value; ``None`` stays ``None``.

    A malformed value is a client error (400), not a server error — it is the
    caller's parameter, so the ``ValueError`` never becomes a 500.
    """
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        pass
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail=f"invalid {name} parameter: {value!r} is not ISO-8601"
        ) from exc


@dataclass(frozen=True)
class AsOfContext:
    """A resolved as-of pair plus its cache decision, shared by every endpoint.

    A request is **belief-pinned** iff the caller supplied ``as_of_belief``
    explicitly: an explicit belief is a fixed assertion-time cut whose answer is
    reproducible forever, so it is immutable and long-cacheable. A *defaulted*
    belief resolves to a fresh "now" on every request — what we believe now can
    change — so it must never be cached (SIG-API-006). The decision therefore does
    not depend on a wall-clock read at all: it is purely whether belief was given.
    """

    asof: AsOf
    belief_pinned: bool

    @classmethod
    def build(cls, asof: AsOf) -> AsOfContext:
        return cls(asof=asof, belief_pinned=not asof.belief_defaulted)

    def echo(self) -> AsOfEcho:
        """The as-of block echoed in the response body (SIG-API-005)."""
        return AsOfEcho(
            as_of_world=self.asof.world,
            as_of_belief=self.asof.belief,
            world_defaulted=self.asof.world_defaulted,
            belief_defaulted=self.asof.belief_defaulted,
            question=self.asof.question().value,
            belief_pinned=self.belief_pinned,
        )

    def apply_cache(self, response: Response) -> None:
        """Set ``Cache-Control`` from the as-of pair (SIG-API-006).

        Belief-pinned → immutable, long-lived. ``now``-pinned → ``no-store``: what
        we currently believe can change under the caller's feet, so a cache would
        serve a stale answer as if it were reproducible.
        """
        if self.belief_pinned:
            response.headers["Cache-Control"] = f"public, max-age={_IMMUTABLE_MAX_AGE}, immutable"
        else:
            response.headers["Cache-Control"] = "no-store"
        # The as-of pair is carried in the query string, so the request URI already
        # keys the cache on it; Vary only needs the representation-selecting header.
        response.headers["Vary"] = "Accept"


def as_of_dependency(
    as_of_world: str | None = Query(
        default=None,
        description="ISO-8601 world (valid-time) instant; defaults explicitly to today.",
    ),
    as_of_belief: str | None = Query(
        default=None,
        description="ISO-8601 belief (assertion-time) instant; defaults explicitly to now.",
    ),
) -> AsOfContext:
    """FastAPI dependency: resolve the two as-of axes for a read (SIG-API-005)."""
    resolved = AsOf.resolve(
        _parse(as_of_world, name="as_of_world"),
        _parse(as_of_belief, name="as_of_belief"),
    )
    return AsOfContext.build(resolved)
