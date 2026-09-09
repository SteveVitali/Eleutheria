# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The claim-sink factory the connector runner selects a write target through (§16).

A connector run threads a :class:`connectors.stages.ClaimSink` on its
:class:`~connectors.stages.RunContext`; ``load()`` asserts the run's claims into
it on a live run only (never on replay/shadow). Two sinks exist:

* the in-memory default (``InMemoryClaimSink``) — the test/replay target, and
* the PostgreSQL spine (``db.claim_sink.PgClaimSink``) — the production target
  wired in P19.4, selected with ``--sink pg --dsn …``.

The ``connectors`` package must not depend on the psycopg driver directly (that
belongs to the ``db`` package, which owns the physical store); this factory keeps
that boundary by delegating connection-opening to
:meth:`db.claim_sink.PgClaimSink.from_dsn`. ``import connectors`` therefore never
pulls in psycopg unless a PG sink is actually requested at runtime.
"""

from __future__ import annotations

from typing import Any

from .stages import ClaimSink, InMemoryClaimSink

#: The sink kinds the runner accepts (``--sink``).
SINK_KINDS = ("memory", "pg")


def make_claim_sink(kind: str = "memory", *, dsn: str | None = None, **kwargs: Any) -> ClaimSink:
    """Build the selected :class:`ClaimSink`.

    ``kind='memory'`` returns an :class:`InMemoryClaimSink` (the default, unchanged
    behaviour). ``kind='pg'`` requires a ``dsn`` and returns a ``PgClaimSink`` bound
    to that database; the psycopg import lives behind this branch so the in-memory
    path has no driver dependency.
    """
    if kind == "memory":
        return InMemoryClaimSink()
    if kind == "pg":
        if not dsn:
            raise ValueError("the 'pg' claim sink requires a --dsn connection string")
        from db.claim_sink import PgClaimSink  # local import: psycopg stays in `db`

        return PgClaimSink.from_dsn(dsn, **kwargs)
    raise ValueError(f"unknown claim-sink kind {kind!r}; expected one of {SINK_KINDS}")


__all__ = ["SINK_KINDS", "make_claim_sink"]
