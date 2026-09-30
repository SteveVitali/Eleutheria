# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Duplicate-identifier triage: a recorded decision for every shared ``(scheme, value)``.

P31.3 / ADR-110 (closes D-P30.4-3). The identity guard stops NEW duplicate entities.
The ones already in the spine stay, because the spine is append-only. Each of them
gets a recorded decision instead. The decision goes through the existing decision
writer: :class:`resolution.review_pg.PgReviewQueue`. The pair is enqueued as an
``er_match`` review item, and the decision is appended as a ``review_decision``:
``accept`` means *same_as* (the two entities are one), and ``reject`` means
*distinct*. That is the queue's ER vocabulary (design §3: ``accept`` → same_as,
``reject`` → distinct, which P31.11 consumes). Nothing here mutates an entity, an
identifier or a claim. Both identifier rows stay, so the duplicate query keeps
returning the pair, now with its decision attached.

The decisions are **committed data** (``data/identity_duplicate_decisions.json``).
Each one names the two entity ids and carries the evidence it was decided on. The
operator delegated these calls to engineering (LEDGER GATE DECISIONS 2026-09-24,
Q6).

* ``sig-resolution identity-triage --dsn …`` is read-only. It lists every pair the
  duplicate query returns, with its evidence and whether a decision is recorded.
  It exits 1 if any pair has no decision (the acceptance check).
* ``… --apply`` appends the committed decisions for the pairs that have none yet.
  A re-run is +0.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from importlib.resources import files
from typing import Any

from .review_queue import ACCEPT, ER_MATCH, REJECT, ReviewItem

#: The duplicate query named by D-P30.4-3's verification rule.
DUPLICATE_PAIRS_QUERY = (
    "SELECT scheme, value FROM entity_identifier "
    "GROUP BY scheme, value HAVING count(DISTINCT entity_id) > 1 ORDER BY scheme, value"
)

_ENTITY_EVIDENCE = (
    "SELECT e.entity_id::text, e.entity_type, e.created_at, "
    "       (SELECT array_agg(x.scheme || '=' || x.value ORDER BY x.scheme, x.value) "
    "          FROM entity_identifier x WHERE x.entity_id = e.entity_id), "
    "       (SELECT count(*) FROM claim c WHERE c.subject_id = e.entity_id), "
    "       (SELECT o.organization_type || ' / ' || coalesce(o.cached_canonical_name, '') "
    "          FROM organization o WHERE o.entity_id = e.entity_id) "
    "  FROM entity_identifier ei JOIN entity e ON e.entity_id = ei.entity_id "
    " WHERE ei.scheme = %s AND ei.value = %s "
    " ORDER BY e.created_at, e.entity_id"
)

_DECISION_FOR = {"same_as": ACCEPT, "distinct": REJECT}


@dataclass(frozen=True)
class EntityEvidence:
    entity_id: str
    entity_type: str
    created_at: str
    identifiers: tuple[str, ...]
    claims: int
    organization: str | None

    def as_json(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "created_at": self.created_at,
            "identifiers": list(self.identifiers),
            "claims": self.claims,
            "organization": self.organization,
        }


@dataclass
class PairStatus:
    """One ``(canonical, other)`` entity pair sharing ``(scheme, value)``."""

    scheme: str
    value: str
    left: EntityEvidence  # the earliest-created entity (the one the guard keys)
    right: EntityEvidence
    committed: Mapping[str, Any] | None = None
    recorded: list[str] = field(default_factory=list)  # recorded review decisions

    @property
    def item_id(self) -> str:
        a, b = sorted((self.left.entity_id, self.right.entity_id))
        return f"er_match:identity_duplicate:{a}:{b}"


def load_decisions(path: str | None = None) -> list[dict[str, Any]]:
    """The committed engineering decisions (the packaged data file by default)."""
    if path is None:
        raw = files("resolution").joinpath("data", "identity_duplicate_decisions.json")
        doc = json.loads(raw.read_text(encoding="utf-8"))
    else:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    decisions = list(doc["decisions"])
    for d in decisions:
        if d["decision"] not in _DECISION_FOR:
            raise ValueError(f"decision must be same_as|distinct, got {d['decision']!r}")
        if not d.get("rationale"):
            raise ValueError("every decision carries its rationale")
    return decisions


def _evidence(conn: Any, scheme: str, value: str) -> list[EntityEvidence]:
    rows = conn.execute(_ENTITY_EVIDENCE, (scheme, value)).fetchall()
    return [
        EntityEvidence(
            entity_id=str(r[0]),
            entity_type=str(r[1]),
            created_at=r[2].isoformat() if hasattr(r[2], "isoformat") else str(r[2]),
            identifiers=tuple(r[3] or ()),
            claims=int(r[4]),
            organization=r[5],
        )
        for r in rows
    ]


def _find_committed(
    decisions: Sequence[Mapping[str, Any]], scheme: str, value: str, pair: set[str]
) -> Mapping[str, Any] | None:
    for d in decisions:
        if d["scheme"] == scheme and d["value"] == value and set(d["entities"]) == pair:
            return d
    return None


def triage(conn: Any, decisions: Sequence[Mapping[str, Any]]) -> list[PairStatus]:
    """Every duplicate pair on the spine, with its evidence and recorded decisions (read-only).

    A value shared by ``n`` entities yields ``n - 1`` pairs, each one pairing the
    earliest-created entity (the guard's key) with a later one.
    """
    out: list[PairStatus] = []
    for scheme, value in conn.execute(DUPLICATE_PAIRS_QUERY).fetchall():
        entities = _evidence(conn, str(scheme), str(value))
        canonical, others = entities[0], entities[1:]
        for other in others:
            status = PairStatus(str(scheme), str(value), canonical, other)
            status.committed = _find_committed(
                decisions, status.scheme, status.value, {canonical.entity_id, other.entity_id}
            )
            status.recorded = [
                str(r[0])
                for r in conn.execute(
                    "SELECT decision FROM review_decision WHERE item_id = %s "
                    "ORDER BY decided_at, decision_id",
                    (status.item_id,),
                ).fetchall()
            ]
            out.append(status)
    return out


def review_item_for(status: PairStatus, decision: Mapping[str, Any]) -> ReviewItem:
    """The ``er_match`` proposal a duplicate pair is decided on (payload = its evidence)."""
    a, b = sorted((status.left.entity_id, status.right.entity_id))
    return ReviewItem(
        item_id=status.item_id,
        kind=ER_MATCH,
        summary=(
            f"Same entity? {a} and {b} share identifier {status.scheme}={status.value} "
            "(P31.3 duplicate-identifier triage)"
        ),
        payload={
            "left": a,
            "right": b,
            "origin": "identity_duplicate_triage",
            "ticket": "P31.3",
            "adr": "ADR-110",
            "scheme": status.scheme,
            "value": status.value,
            "canonical_entity": status.left.entity_id,
            "entities": [status.left.as_json(), status.right.as_json()],
            "evidence": dict(decision.get("evidence") or {}),
        },
    )


def apply_decisions(queue: Any, statuses: Sequence[PairStatus], *, reviewer: str) -> int:
    """Append the committed decision for every pair that has none yet; return how many."""
    appended = 0
    for status in statuses:
        if status.recorded or status.committed is None:
            continue
        queue.enqueue(review_item_for(status, status.committed))
        queue.decide(
            status.item_id,
            _DECISION_FOR[str(status.committed["decision"])],
            reviewer=reviewer,
            rationale=str(status.committed["rationale"]),
        )
        status.recorded = [_DECISION_FOR[str(status.committed["decision"])]]
        appended += 1
    return appended


def as_report(statuses: Sequence[PairStatus]) -> list[dict[str, Any]]:
    return [
        {
            "scheme": s.scheme,
            "value": s.value,
            "item_id": s.item_id,
            "entities": [s.left.as_json(), s.right.as_json()],
            "committed_decision": (s.committed or {}).get("decision"),
            "recorded_decisions": list(s.recorded),
        }
        for s in statuses
    ]


__all__ = [
    "DUPLICATE_PAIRS_QUERY",
    "PairStatus",
    "apply_decisions",
    "as_report",
    "load_decisions",
    "review_item_for",
    "triage",
]
