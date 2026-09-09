# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The PostgreSQL backend for the internal review queue (§14.6, §25, §27).

Until P19.5 the :class:`resolution.review_queue.ReviewQueue` was a JSON-serialisable
value object only — the persistence P05.1 deferred. This module gives it a durable
PostgreSQL home so the composed spine can round-trip entity-resolution review:
``sig-resolution match --dsn`` reads org candidates from the PG spine, scores them,
and **enqueues** the tier-4/5 PROPOSED proposals as ``review_item`` rows; a curator
then records an accept/reject with ``sig-resolution review decide --dsn``, which
appends a ``review_decision`` row.

The two invariants of the in-memory queue are preserved and, where PostgreSQL lets
us, strengthened:

* **Append-only decisions (P1–P3, SIG-IDENT-026).** :meth:`PgReviewQueue.decide`
  only ever inserts a ``review_decision`` row — no in-place mutation or row removal
  anywhere in this module. Exactly one row is written per call; deciding the same
  item again appends a new row (a decision *history*), so a reversal is a new
  attributable assertion, not an edit. ``decided_at`` is set **by the database**
  (``clock_timestamp()`` default), never by this code.
* **Nothing here writes to the graph.** Like the in-memory queue this records a
  decision; it has no path that mutates an entity, mints an identifier, or emits a
  claim (SIG-IDENT-026, SIG-LLM-002).

The JSONL/in-memory :class:`ReviewQueue` remains the **default** for every existing
test; this backend is additive and selected explicitly by the ``--dsn`` CLI path.
``connectors``-style packages must not import psycopg directly, but ``resolution``
already depends on ``sig-db`` and drives PG through it (as ``reconcile.cli`` does),
so the driver import is local to this module.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from .review_queue import _DECISIONS, ReviewDecision, ReviewItem

__all__ = ["PgReviewQueue"]


class PgReviewQueue:
    """A :class:`resolution.review_queue.ReviewQueue`-shaped backend over PostgreSQL.

    Constructed from an open psycopg connection (:meth:`from_dsn` opens one from a
    DSN). Mirrors the enqueue → pending → decide surface of the in-memory queue, but
    reads and writes the ``review_item`` / ``review_decision`` tables so proposals
    and adjudications survive across processes and are visible to the API.
    """

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    @classmethod
    def from_dsn(cls, dsn: str) -> PgReviewQueue:
        """Open an autocommit connection from ``dsn`` and wrap it in a PG queue."""
        import psycopg  # available via the sig-db dependency (driver stays in `db`)

        return cls(psycopg.connect(dsn, autocommit=True))

    # --- enqueue / read --------------------------------------------------------

    def enqueue(self, item: ReviewItem) -> bool:
        """Persist a proposal as a ``review_item`` row (idempotent).

        Returns ``True`` if a new row was inserted, ``False`` if the same proposal
        (by ``item_id``) was already present — so replaying a match over the same
        candidate set never duplicates a proposal.
        """
        row = self._conn.execute(
            "INSERT INTO review_item"
            "(item_id, kind, summary, confidence, overall_weight, model_id,"
            " prompt_version, payload) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (item_id) DO NOTHING RETURNING item_id",
            (
                item.item_id,
                item.kind,
                item.summary,
                json.dumps([f.to_row() for f in item.confidence]),
                item.overall_weight,
                item.model_id,
                item.prompt_version,
                json.dumps(dict(item.payload)),
            ),
        ).fetchone()
        return row is not None

    def _item_row(self, item_id: str) -> ReviewItem | None:
        row = self._conn.execute(
            "SELECT item_id, kind, summary, confidence, overall_weight, model_id, "
            "       prompt_version, payload "
            "  FROM review_item WHERE item_id = %s",
            (item_id,),
        ).fetchone()
        if row is None:
            return None
        return ReviewItem.from_row(
            {
                "item_id": row[0],
                "kind": row[1],
                "summary": row[2],
                "confidence": row[3] or [],
                "overall_weight": row[4],
                "model_id": row[5],
                "prompt_version": row[6],
                "payload": row[7] or {},
            }
        )

    def get(self, item_id: str) -> ReviewItem | None:
        """The persisted proposal with this id, or ``None``."""
        return self._item_row(item_id)

    def pending(self) -> tuple[ReviewItem, ...]:
        """Proposals with no decision yet, ordered by id (deterministic for the UI)."""
        rows = self._conn.execute(
            "SELECT ri.item_id, ri.kind, ri.summary, ri.confidence, ri.overall_weight, "
            "       ri.model_id, ri.prompt_version, ri.payload "
            "  FROM review_item ri "
            "  LEFT JOIN review_decision rd ON rd.item_id = ri.item_id "
            " WHERE rd.item_id IS NULL "
            " ORDER BY ri.item_id",
            (),
        ).fetchall()
        return tuple(
            ReviewItem.from_row(
                {
                    "item_id": r[0],
                    "kind": r[1],
                    "summary": r[2],
                    "confidence": r[3] or [],
                    "overall_weight": r[4],
                    "model_id": r[5],
                    "prompt_version": r[6],
                    "payload": r[7] or {},
                }
            )
            for r in rows
        )

    def decisions(self, item_id: str | None = None) -> tuple[ReviewDecision, ...]:
        """The append-only decision history, optionally filtered to one item."""
        if item_id is None:
            rows = self._conn.execute(
                "SELECT item_id, decision, reviewer, decided_at, model_id, prompt_version, "
                "       rationale FROM review_decision ORDER BY decided_at, decision_id",
                (),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT item_id, decision, reviewer, decided_at, model_id, prompt_version, "
                "       rationale FROM review_decision WHERE item_id = %s "
                "ORDER BY decided_at, decision_id",
                (item_id,),
            ).fetchall()
        return tuple(
            ReviewDecision.from_row(
                {
                    "item_id": r[0],
                    "decision": r[1],
                    "reviewer": r[2],
                    "decided_at": str(r[3]),
                    "model_id": r[4],
                    "prompt_version": r[5],
                    "rationale": r[6],
                }
            )
            for r in rows
        )

    # --- decide (append-only) --------------------------------------------------

    def decide(
        self,
        item_id: str,
        decision: str,
        *,
        reviewer: str,
        rationale: str | None = None,
    ) -> ReviewDecision:
        """Append exactly one ``review_decision`` row for ``item_id`` (SIG-IDENT-026).

        The decision is append-only: this only ``INSERT``s, so deciding the same item
        again records a new row (a decision history), never an edit. Copies the item's
        ``model_id``/``prompt_version`` onto the decision so an adjudication of model
        output always logs the model and prompt that proposed it. ``decided_at`` is set
        by the database.
        """
        if decision not in _DECISIONS:
            raise ValueError(f"decision must be one of {sorted(_DECISIONS)}, got {decision!r}")
        if not reviewer:
            raise ValueError("a review decision MUST record the human reviewer (SIG-IDENT-026)")
        item = self._item_row(item_id)
        if item is None:
            raise ValueError(f"no such review item {item_id!r}")
        # A model-assisted decision without its provenance is a violation (SIG-IDENT-026).
        if item.model_assisted and (item.model_id is None or item.prompt_version is None):
            raise ValueError(
                "a decision on model-assisted output MUST log model_id and prompt_version "
                "(SIG-IDENT-026)"
            )
        row = self._conn.execute(
            "INSERT INTO review_decision"
            "(item_id, decision, reviewer, model_id, prompt_version, rationale) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "RETURNING item_id, decision, reviewer, decided_at, model_id, prompt_version, "
            "rationale",
            (item_id, decision, reviewer, item.model_id, item.prompt_version, rationale),
        ).fetchone()
        assert row is not None
        return ReviewDecision.from_row(
            {
                "item_id": row[0],
                "decision": row[1],
                "reviewer": row[2],
                "decided_at": str(row[3]),
                "model_id": row[4],
                "prompt_version": row[5],
                "rationale": row[6],
            }
        )

    def enqueue_matches(self, matches: Sequence[Any]) -> int:
        """Enqueue every match as a proposal; return how many were newly inserted."""
        from .review_queue import review_item_from_match

        added = 0
        for match in matches:
            if self.enqueue(review_item_from_match(match)):
                added += 1
        return added
