# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Materialize §28 resolution envelopes into the spine (P28.1, ADR-099).

The §16.4 ``resolution`` table is a stored, attributable, diffable DECISION record
(SIG-STORE-014), not a view. Until P28.1 the launch posture computed the resolution
envelope on read (ADR-092) and this table held no rows. :func:`materialize_resolutions`
runs the §28 resolver (:func:`reconcile.resolve.RESOLVE`) over the real spine and
**writes** the resulting envelopes as durable rows, honoring every invariant the spine
demands:

* **Append-only (ADR-005, §16.4).** A resolution is a stored decision. This module only
  ``INSERT``s — there is no ``UPDATE``/``DELETE`` path. A genuinely changed input yields
  a new SIG-RECON-020 ``input_digest`` and a *superseding* decision (close the prior
  ``sys_period`` first); a re-run over unchanged inputs is a no-op.
* **Idempotent (+0).** The insert is ``ON CONFLICT (input_digest) DO NOTHING`` against
  the ``resolution_input_digest_key`` partial unique index (the ``resolution_materialize``
  sqitch change), so replaying the materializer over the same claims inserts each
  envelope exactly once.
* **Contradictions stay visible (§3.1).** Both ``RESOLVED`` and first-class
  ``unresolved_conflict`` envelopes are written (SIG-STORE-015); nothing is collapsed to
  a single number that the evidence does not support.
* **Every write is labelled.** Each row carries the resolver/ruleset versions, the
  strategy, the rationale code + quotable text, the confidence, and machine-readable
  support/dissent counts — the provenance the defining standard requires.

Predicates the resolver's ruleset does not cover (``KeyError``) or does not adjudicate
(no strategy — SIG-RECON-013) are **skipped**, not guessed: they are counted and left to
the observation-envelope fallback (ADR-092), never materialized as a fabricated decision.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from .resolve import RESOLVE, Claim, Resolution
from .ruleset import Ruleset, load_ruleset

__all__ = [
    "MaterializeSummary",
    "SUPPORT_TO_CONFIDENCE",
    "read_claim_groups",
    "resolution_row",
    "materialize_resolutions",
]

#: §10.7 support axis → the resolution table's ``confidence`` vocabulary. The support
#: level of the winning value's own evidence, distinct from the agreement axis (which is
#: carried in ``evidence_counts`` and ``contradiction_state``).
SUPPORT_TO_CONFIDENCE: dict[str, str] = {
    "CONFIRMED": "confirmed",
    "STRONGLY_SUPPORTED": "strongly_supported",
    "PROBABLE": "probable",
    "WEAKLY_SUPPORTED": "weakly_supported",
    "UNSUPPORTED": "unsupported",
}

_CONFIDENCE_DEFINITION: dict[str, str] = {
    "confirmed": "§10.7 support: multiple independent methods confirm the value.",
    "strongly_supported": "§10.7 support: strong, directly-sourced evidence for the value.",
    "probable": "§10.7 support: corroborated but not confirmed.",
    "weakly_supported": "§10.7 support: a single weak-signal source.",
    "unsupported": "§10.7 support: no probative evidence for the value.",
}


@dataclass(frozen=True)
class MaterializeSummary:
    """The outcome of one materialization pass — every group is accounted for."""

    considered_pairs: int = 0
    inserted: int = 0
    skipped_existing: int = 0
    skipped_unresolvable: int = 0
    resolved: int = 0
    unresolved: int = 0

    @property
    def written(self) -> int:
        return self.inserted

    def as_dict(self) -> dict[str, int]:
        return {
            "considered_pairs": self.considered_pairs,
            "inserted": self.inserted,
            "skipped_existing": self.skipped_existing,
            "skipped_unresolvable": self.skipped_unresolvable,
            "resolved": self.resolved,
            "unresolved": self.unresolved,
        }


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date(1970, 1, 1)


def _value(kind: str, text: Any, num: Any, boolean: Any) -> object:
    if kind != "value":
        return None
    if boolean is not None:
        return bool(boolean)
    if num is not None:
        f = float(num)
        return int(f) if f.is_integer() else f
    return text


def read_claim_groups(
    conn: Any,
    *,
    jurisdiction: str | None = None,
    subject: str | None = None,
    predicate: str | None = None,
) -> dict[tuple[str, str], list[Claim]]:
    """Read L0 tier-0 claims from the spine, grouped by ``(subject, predicate)``.

    Mirrors the read the read-only ``reconcile resolve`` CLI performs (contradictions
    visible, §3.1): the same lateral-join evidence chain for the source id/genre, the
    same tier-0-only filter, ordered deterministically.
    """
    where = ["c.sensitivity_tier = 0"]
    params: list[Any] = []
    if subject:
        where.append("c.subject_id = %s")
        params.append(subject)
    if predicate:
        where.append("c.predicate_id = %s")
        params.append(predicate)
    if jurisdiction:
        where.append(
            "c.subject_id IN (SELECT entity_id FROM entity_identifier WHERE value ILIKE %s)"
        )
        params.append(f"%{jurisdiction}%")

    rows = conn.execute(
        "SELECT c.subject_id, c.predicate_id, c.claim_id, c.value_kind, c.value_text, "
        "       c.value_num, c.value_bool, c.raw_value, c.observed_at, c.source_reliability, "
        "       c.artifact_integrity, c.review_status, ea.source_id, ea.artifact_type "
        "  FROM claim c "
        "  LEFT JOIN LATERAL ("
        "     SELECT ea.source_id, ea.artifact_type FROM claim_evidence ce "
        "       JOIN evidence_capture ec ON ec.capture_id = ce.capture_id "
        "       JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id "
        "      WHERE ce.claim_id = c.claim_id LIMIT 1) ea ON true "
        " WHERE " + " AND ".join(where) + " ORDER BY c.subject_id, c.predicate_id, c.claim_id",
        tuple(params),
    ).fetchall()

    groups: dict[tuple[str, str], list[Claim]] = {}
    for r in rows:
        key = (str(r[0]), str(r[1]))
        groups.setdefault(key, []).append(
            Claim(
                claim_id=str(r[2]),
                subject_id=str(r[0]),
                predicate_id=str(r[1]),
                value=_value(r[3], r[4], r[5], r[6]),
                reliability=r[9],
                integrity=r[10],
                genre=r[13] or "",
                observed_at=_as_date(r[8]) if r[8] else date(1970, 1, 1),
                raw_value=r[7] or "",
                review_status=r[11] or "active",
                source_id=r[12] or "",
                count_basis=str(r[1]).removesuffix("_device_count")
                if str(r[1]).endswith("_device_count")
                else None,
            )
        )
    return groups


def resolution_row(resolved: Resolution, *, ruleset: Ruleset) -> dict[str, Any] | None:
    """Map a :class:`~reconcile.resolve.Resolution` onto a ``resolution`` table row.

    Returns ``None`` for an envelope that cannot be a stored decision — no strategy was
    assigned to the predicate (SIG-RECON-013): SIG records the claims but does not
    adjudicate, so there is no decision to materialize.
    """
    if resolved.strategy_id is None:
        return None

    value = resolved.value
    value_num: float | int | None = None
    value_text: str | None = None
    if resolved.resolution_status == "RESOLVED" and value is not None:
        if isinstance(value, bool):
            value_text = "true" if value else "false"
        elif isinstance(value, (int, float)):
            value_num = value
            value_text = str(value)
        else:
            value_text = str(value)

    confidence = SUPPORT_TO_CONFIDENCE.get(resolved.support, "unsupported")
    evidence_counts = {
        "support": resolved.support,
        "agreement": resolved.agreement,
        "n_considered": len(resolved.considered_claim_ids),
        "n_supporting": len(resolved.supporting_claim_ids),
        "n_dissenting": len(resolved.dissenting_claim_ids),
        "n_independence_classes": len(resolved.independence_class_ids),
        "rules_fired": list(resolved.rules_fired),
        "resolution_status": resolved.resolution_status,
        "unresolved_code": resolved.unresolved_code,
    }
    return {
        "subject_id": resolved.subject_id,
        "predicate_id": resolved.predicate_id,
        "value_kind": "value",
        "value_text": value_text,
        "value_num": value_num,
        "winning_claim": resolved.winning_claim_id,
        "considered_claims": list(resolved.considered_claim_ids),
        "dissenting_claims": list(resolved.dissenting_claim_ids),
        "contradiction_state": resolved.contradiction_state,
        "strategy_id": resolved.strategy_id,
        "rationale_code": resolved.rationale_code,
        "rationale_text": resolved.rationale_text,
        "confidence": confidence,
        "evidence_counts": json.dumps(evidence_counts),
        "resolver_version": resolved.resolver_version,
        "ruleset_version": resolved.ruleset_version,
        "input_digest": resolved.input_digest,
        "as_of_world": resolved.as_of_world,
        "_template": ruleset.template(resolved.rationale_code),
        "_strategy_definition": _strategy_definition(ruleset, resolved.strategy_id),
        "_confidence_definition": _CONFIDENCE_DEFINITION.get(confidence, confidence),
    }


def _strategy_definition(ruleset: Ruleset, strategy_id: str) -> str:
    definition = ruleset.strategies.get(strategy_id)
    if definition:
        return str(definition)
    return f"§28 resolution strategy {strategy_id} (SIG-RECON-012)"


def _ensure_vocab(conn: Any, row: dict[str, Any]) -> None:
    """Upsert the FK vocab rows this envelope references (append-only, idempotent).

    Mirrors ``PgClaimSink._ensure_resolution_strategy``: every prerequisite is an
    ``INSERT ... ON CONFLICT DO NOTHING``, never an update.
    """
    conn.execute(
        "INSERT INTO vocab_resolution_strategy(strategy_id, definition) "
        "VALUES (%s, %s) ON CONFLICT (strategy_id) DO NOTHING",
        (row["strategy_id"], row["_strategy_definition"]),
    )
    conn.execute(
        "INSERT INTO vocab_rationale(rationale_code, template) "
        "VALUES (%s, %s) ON CONFLICT (rationale_code) DO NOTHING",
        (row["rationale_code"], row["_template"]),
    )
    conn.execute(
        "INSERT INTO vocab_confidence(confidence, definition) "
        "VALUES (%s, %s) ON CONFLICT (confidence) DO NOTHING",
        (row["confidence"], row["_confidence_definition"]),
    )


def _insert_resolution(conn: Any, row: dict[str, Any]) -> bool:
    """INSERT one resolution row, idempotent on ``input_digest``. True iff inserted."""
    result = conn.execute(
        "INSERT INTO resolution"
        "(subject_id, predicate_id, value_kind, value_text, value_num, valid_period, "
        " winning_claim, considered_claims, dissenting_claims, contradiction_state, "
        " strategy_id, rationale_code, rationale_text, confidence, evidence_counts, "
        " resolver_version, ruleset_version, decided_by, input_digest) "
        "VALUES (%s, %s, %s, %s, %s, tstzrange(%s::timestamptz, NULL, '[)'), "
        " %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, 'auto', %s) "
        "ON CONFLICT (input_digest) WHERE input_digest IS NOT NULL "
        "DO NOTHING RETURNING resolution_id",
        (
            row["subject_id"],
            row["predicate_id"],
            row["value_kind"],
            row["value_text"],
            row["value_num"],
            row["as_of_world"],
            row["winning_claim"],
            row["considered_claims"],
            row["dissenting_claims"],
            row["contradiction_state"],
            row["strategy_id"],
            row["rationale_code"],
            row["rationale_text"],
            row["confidence"],
            row["evidence_counts"],
            row["resolver_version"],
            row["ruleset_version"],
            row["input_digest"],
        ),
    ).fetchone()
    return result is not None


def materialize_resolutions(
    conn: Any,
    *,
    jurisdiction: str | None = None,
    subject: str | None = None,
    predicate: str | None = None,
    as_of: date | None = None,
    ruleset: Ruleset | None = None,
    role: str | None = None,
) -> MaterializeSummary:
    """Run the §28 resolver over the spine and materialize the envelopes (P28.1).

    Reads tier-0 claims grouped by ``(subject, predicate)``, resolves each group, and
    writes the decision as an append-only, idempotent ``resolution`` row. Returns a
    :class:`MaterializeSummary`; a second call over unchanged claims inserts +0.
    """
    rs = ruleset or load_ruleset()
    if role:
        conn.execute(f"SET ROLE {role}")
    as_of_world = as_of or datetime.now(tz=UTC).date()

    groups = read_claim_groups(
        conn, jurisdiction=jurisdiction, subject=subject, predicate=predicate
    )

    considered = inserted = skipped_existing = skipped_unresolvable = 0
    resolved_n = unresolved_n = 0
    for (subj, pred), claims in sorted(groups.items()):
        considered += 1
        try:
            resolved = RESOLVE(
                subj, pred, claims, as_of_world=as_of_world, as_of_belief=as_of_world, ruleset=rs
            )
        except KeyError:
            # Predicate not in the resolver ruleset — not materializable (ADR-092 fallback).
            skipped_unresolvable += 1
            continue
        row = resolution_row(resolved, ruleset=rs)
        if row is None:
            # No strategy assigned (SIG-RECON-013): recorded, not adjudicated.
            skipped_unresolvable += 1
            continue
        _ensure_vocab(conn, row)
        if _insert_resolution(conn, row):
            inserted += 1
        else:
            skipped_existing += 1
        if resolved.resolution_status == "RESOLVED":
            resolved_n += 1
        else:
            unresolved_n += 1

    return MaterializeSummary(
        considered_pairs=considered,
        inserted=inserted,
        skipped_existing=skipped_existing,
        skipped_unresolvable=skipped_unresolvable,
        resolved=resolved_n,
        unresolved=unresolved_n,
    )


def materialize_from_dsn(dsn: str, **kwargs: Any) -> MaterializeSummary:
    """Open an autocommit connection from ``dsn`` and materialize (CLI convenience)."""
    import psycopg  # available via the sig-db dependency (driver stays in `db`)

    conn = psycopg.connect(dsn, autocommit=True)
    try:
        return materialize_resolutions(conn, **kwargs)
    finally:
        conn.close()
