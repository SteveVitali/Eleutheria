# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The append-only typed-identity write (P35.14b; L1 NEW-5 / FM-17, SIG-IDENT-025).

Before this row every ``sig.connector.subject`` minted ``entity_type =
'deployment'`` — agencies, contracts, portals, bills and meetings are all
served and joined as deployments. The spine is append-only, so the correction
is NOT an ``UPDATE`` of the mistyped ``entity`` rows: it is a NEW
``entity_type_decision`` row per affected subject, recorded under the map
version that decided it. Readers resolve an entity's *current* type through
``entity_current_type`` (latest decision wins, falling back to the recorded
column); history is preserved.

Semantics a caller can rely on:

* **Read the guard keys, never guess.** The write enumerates
  ``entity_identity_key`` (the identity decision table) — exactly the subjects
  the spine keyed — and looks each value up in the declared
  ``subject_entity_types.toml`` map. A value the map does not cover is
  *reported*, never typed: the correction is as fail-closed as the mint path.
* **A decision only supersedes a differing type.** When the entity's effective
  type already equals the mapped type (minted correctly, or a prior decision
  already corrected it) there is nothing to write.
* **Insert-only + idempotent.** ``INSERT … ON CONFLICT DO NOTHING`` against
  ``UNIQUE (scheme, value, entity_type, map_version)``: a re-run of the same
  map version appends +0. A superseding correction under a later map version is
  a NEW row, never a rewrite.
* **Dry-run by default.** ``plan_decisions`` performs the same read the apply
  path performs and writes nothing; ``apply_decisions`` is the only write path
  and is what the L1 leg's ``--apply`` invokes inside AR-3 + AR-2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .identity_guard import SUBJECT_SCHEME
from .subject_types import UnmappedSubjectScheme, entity_type_for_subject, map_version

#: The ``decided_by`` recorded on rows this writer lands.
DECIDED_BY = "typed-identity-write/1"
#: The decision's written basis (what evidence supports it).
DECISION_BASIS = "P35.14b NEW-5/FM-17: subject-scheme → entity-type map correction"

_READ_KEYED_SUBJECTS = (
    "SELECT k.value, k.entity_id, e.entity_type, "
    "  (SELECT d.entity_type FROM entity_type_decision d"
    "    WHERE d.entity_id = e.entity_id"
    "    ORDER BY d.decision_seq DESC LIMIT 1) AS decided_type "
    "FROM entity_identity_key k JOIN entity e ON e.entity_id = k.entity_id "
    "WHERE k.scheme = %s ORDER BY k.value"
)

_INSERT_DECISION = (
    "INSERT INTO entity_type_decision"
    " (scheme, value, entity_id, prior_type, entity_type, map_version,"
    "  decided_by, basis) "
    "VALUES (%s, %s, %s::uuid, %s, %s, %s, %s, %s) "
    "ON CONFLICT (scheme, value, entity_type, map_version) DO NOTHING "
    "RETURNING decision_seq"
)


@dataclass(frozen=True)
class PendingDecision:
    """One correction the apply path would write."""

    scheme: str
    value: str
    entity_id: str
    prior_type: str
    entity_type: str


@dataclass
class TypedIdentityPlan:
    """What a dry-run read found — the apply path's exact input."""

    map_version: str = field(default_factory=map_version)
    subjects_scanned: int = 0
    #: (value, recorded_type) pairs whose prefix the map does not cover —
    #: reported, never typed (fail-closed like the mint path).
    unmapped: list[tuple[str, str]] = field(default_factory=list)
    pending: list[PendingDecision] = field(default_factory=list)

    def report(self, *, inserted: int | None = None) -> dict[str, Any]:
        """The JSON-serializable plan/apply summary the CLI prints."""
        by_type: dict[str, int] = {}
        for d in self.pending:
            by_type[d.entity_type] = by_type.get(d.entity_type, 0) + 1
        out: dict[str, Any] = {
            "map_version": self.map_version,
            "subjects_scanned": self.subjects_scanned,
            "unmapped_count": len(self.unmapped),
            "unmapped": [{"value": v, "recorded_type": t} for v, t in self.unmapped],
            "pending_by_entity_type": by_type,
            "pending_count": len(self.pending),
        }
        if inserted is not None:
            out["inserted"] = inserted
        return out


def plan_decisions(conn: Any) -> TypedIdentityPlan:
    """Read the keyed subjects and compute the corrections — writes nothing.

    ``conn`` is anything with psycopg's ``execute``. Runs inside the caller's
    transaction; a dry-run never needs one of its own.
    """
    plan = TypedIdentityPlan()
    for value, entity_id, recorded_type, decided_type in conn.execute(
        _READ_KEYED_SUBJECTS, (SUBJECT_SCHEME,)
    ).fetchall():
        plan.subjects_scanned += 1
        value_s = str(value)
        try:
            mapped = entity_type_for_subject(value_s)
        except UnmappedSubjectScheme:
            plan.unmapped.append((value_s, str(recorded_type)))
            continue
        effective = str(decided_type or recorded_type)
        if mapped == effective:
            continue
        plan.pending.append(
            PendingDecision(
                scheme=SUBJECT_SCHEME,
                value=value_s,
                entity_id=str(entity_id),
                prior_type=effective,
                entity_type=mapped,
            )
        )
    return plan


def apply_decisions(conn: Any, plan: TypedIdentityPlan) -> int:
    """Insert the pending decisions (append-only); return the count landed.

    ``ON CONFLICT DO NOTHING`` makes a re-run of the same map version +0 —
    the row already recorded is the decision, never a duplicate.
    """
    inserted = 0
    for d in plan.pending:
        row = conn.execute(
            _INSERT_DECISION,
            (
                d.scheme,
                d.value,
                d.entity_id,
                d.prior_type,
                d.entity_type,
                plan.map_version,
                DECIDED_BY,
                DECISION_BASIS,
            ),
        ).fetchone()
        if row is not None:
            inserted += 1
    return inserted


def run(dsn: str, *, apply_mode: bool = False) -> dict[str, Any]:
    """The CLI path: plan (dry-run) or apply the typed-identity write.

    Apply commits one transaction for the whole pass — either every pending
    decision lands or none does (a partial correction is never recorded).
    """
    import psycopg

    with psycopg.connect(dsn, autocommit=False) as conn:
        plan = plan_decisions(conn)
        if not apply_mode:
            return {"mode": "plan", **plan.report()}
        inserted = apply_decisions(conn, plan)
        conn.commit()
    return {"mode": "apply", **plan.report(inserted=inserted)}


__all__ = [
    "DECIDED_BY",
    "DECISION_BASIS",
    "PendingDecision",
    "TypedIdentityPlan",
    "apply_decisions",
    "plan_decisions",
    "run",
]
