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

import hashlib
import json
import uuid as _uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from .resolve import RESOLVE, Claim, Resolution
from .ruleset import Ruleset, load_ruleset
from .sharing import ACCESS_KINDS, ReconciledEdge, SharingObservation, reconcile_sharing

__all__ = [
    "MaterializeSummary",
    "SUPPORT_TO_CONFIDENCE",
    "read_claim_groups",
    "resolution_row",
    "materialize_resolutions",
    # P28.2 — sharing/access relationship edges
    "EdgeMaterializeSummary",
    "ACCESS_KIND_PREDICATE_HINTS",
    "classify_access_kind",
    "read_sharing_observations",
    "edge_input_digest",
    "edge_row",
    "materialize_sharing_edges",
    "materialize_sharing_edges_from_dsn",
    "read_materialized_edges",
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


# ============================================================================
# P28.2 — Materialize the sharing/access relationship network (§29.3, ADR-101).
#
# The Appendix C.5 ``relationship`` table (the §12 edge catalog) is a stored,
# evidenced, perspectival edge record. Until P28.2 the launch posture computed the
# sharing edges on read (ADR-092, ``exports.shaping.shape_sharing_edges``) and this
# table held no rows. :func:`materialize_sharing_edges` reads the sharing-edge
# claims out of the real spine, runs the **P08.2** §29.3 sharing-edge reconciler
# (:func:`reconcile.sharing.reconcile_sharing` — CONSUMED here, never re-implemented,
# SIG-ENG-035), and WRITES the reconciled directed access edges as durable
# ``relationship`` rows, honoring every invariant the spine demands:
#
# * **Append-only (ADR-005, §12.1).** An edge is a stored, evidenced fact. This
#   path only ``INSERT``s — there is no ``UPDATE``/``DELETE``. A changed evidence
#   set yields a new :func:`edge_input_digest` and a *superseding* row; a re-run
#   over unchanged claims is a no-op (+0).
# * **Idempotent (+0).** The insert is ``ON CONFLICT (input_digest) DO NOTHING``
#   against the ``relationship_input_digest_key`` partial unique index (the
#   ``relationship_materialize`` sqitch change).
# * **The three access kinds are never merged (SIG-ONTO-042/SIG-RECON-034).** The
#   reconciler keeps ``configured_access`` / ``observed_use`` / ``declared_policy``
#   strictly separate; each materialized row carries its own ``access_kind``, and
#   ``edge_type`` is set to that access_kind (§12.5: ``access_kind`` is "which of the
#   three edge types of §12.2"; §12.9 speaks of "``configured_access`` edges").
# * **Contradictions stay VISIBLE (§3.1).** Directional asymmetry ("A's export
#   lists B but B's export does not reciprocate") is a ``SHARING_ASYMMETRY``
#   contradiction the reconciler emits; both directional edges are retained as
#   separate rows and the contradictions are RETURNED, never silently reconciled.
#   Materializing the ``contradiction`` rows themselves is P28.3 — out of scope
#   here, so they are surfaced in the summary, not written.
# * **Every edge is evidenced (§3.1, no unevidenced edges).** ``evidence_claim`` is
#   NOT NULL — a materialized edge always resolves to a real backing claim.
#
# ``to_org`` endpoints that do not resolve to an ``entity`` (a name-only partner,
# ``object_entity IS NULL``) are still reconciled (so asymmetry detection stays
# complete) but are NOT materialized — a ``relationship`` row requires both
# endpoints as ``entity`` FKs; they are counted ``skipped_unmapped``, never a
# fabricated node.
# ============================================================================

#: Substring hints mapping a sharing-edge predicate to its §12.2 access kind. This
#: is a predicate→kind *classification map* (data), not the §29.3 reconciliation
#: logic (which is owned by P08.2 and consumed via :func:`reconcile_sharing`). Kept
#: consistent with ``exports.shaping._classify_access_kind`` without a layering
#: dependency (``exports`` depends on ``reconcile``, never the reverse).
ACCESS_KIND_PREDICATE_HINTS: tuple[tuple[str, str], ...] = (
    ("configured", "configured_access"),
    ("sharing_partner", "configured_access"),
    ("observed", "observed_use"),
    ("_use", "observed_use"),
    ("seen", "observed_use"),
    ("declared", "declared_policy"),
    ("policy", "declared_policy"),
    ("mou", "declared_policy"),
    ("agreement", "declared_policy"),
)


def classify_access_kind(predicate_id: str) -> str | None:
    """Map a sharing-edge predicate to one of the three §12.2 access kinds, or ``None``.

    Returns ``None`` for a predicate that cannot be honestly classified — such an
    edge is skipped (never coerced into a kind the evidence does not support,
    SIG-ONTO-042).
    """
    p = predicate_id.lower()
    for hint, kind in ACCESS_KIND_PREDICATE_HINTS:
        if hint in p:
            return kind
    return None


def _is_uuid(value: str) -> bool:
    try:
        _uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    return True


@dataclass(frozen=True)
class EdgeMaterializeSummary:
    """The outcome of one sharing-edge materialization pass — every edge accounted for."""

    considered_claims: int = 0
    observations: int = 0
    edges_reconciled: int = 0
    inserted: int = 0
    skipped_existing: int = 0
    skipped_unmapped: int = 0
    contradictions: int = 0
    asymmetry_tasks: int = 0
    by_access_kind: dict[str, int] = field(default_factory=dict)

    @property
    def written(self) -> int:
        return self.inserted

    def as_dict(self) -> dict[str, Any]:
        return {
            "considered_claims": self.considered_claims,
            "observations": self.observations,
            "edges_reconciled": self.edges_reconciled,
            "inserted": self.inserted,
            "skipped_existing": self.skipped_existing,
            "skipped_unmapped": self.skipped_unmapped,
            "contradictions": self.contradictions,
            "asymmetry_tasks": self.asymmetry_tasks,
            "by_access_kind": dict(sorted(self.by_access_kind.items())),
        }


def read_sharing_observations(
    conn: Any,
    *,
    jurisdiction: str | None = None,
    subject: str | None = None,
) -> tuple[list[SharingObservation], int]:
    """Read sharing-edge claims from the spine as directed §29.3 observations.

    Reads tier-0, currently-valid claims that carry an ``entity_ref`` partner
    (``object_entity IS NOT NULL``) under a sharing/access predicate, and maps each
    to a :class:`~reconcile.sharing.SharingObservation` directed ``subject → partner``
    (the connector convention: the subject's snapshot asserts the edge). ``asserted_by``
    is the reporting subject's entity id — the perspective §29.3 asymmetry detection
    keys on. Returns ``(observations, considered_claims)``.
    """
    where = [
        "c.sensitivity_tier = 0",
        "c.object_entity IS NOT NULL",
        "upper_inf(c.sys_period)",
    ]
    params: list[Any] = []
    if subject:
        where.append("c.subject_id = %s")
        params.append(subject)
    if jurisdiction:
        where.append(
            "c.subject_id IN (SELECT entity_id FROM entity_identifier WHERE value ILIKE %s)"
        )
        params.append(f"%{jurisdiction}%")

    rows = conn.execute(
        "SELECT c.claim_id, c.subject_id, c.predicate_id, c.object_entity, c.observed_at "
        "  FROM claim c "
        " WHERE " + " AND ".join(where) + " ORDER BY c.subject_id, c.predicate_id, c.claim_id",
        tuple(params),
    ).fetchall()

    observations: list[SharingObservation] = []
    considered = 0
    for r in rows:
        considered += 1
        claim_id, subject_id, predicate_id, object_entity, observed_at = r
        access_kind = classify_access_kind(str(predicate_id))
        if access_kind is None or access_kind not in ACCESS_KINDS:
            # A predicate we cannot honestly classify into a §12.2 kind — skipped,
            # never coerced (SIG-ONTO-042). Counted as considered, produces no edge.
            continue
        observations.append(
            SharingObservation(
                asserted_by=str(subject_id),
                from_org=str(subject_id),
                to_org=str(object_entity),
                access_kind=access_kind,
                observed_at=_as_date(observed_at) if observed_at else date(1970, 1, 1),
                from_single_snapshot=True,
                evidence=None,
                claim_id=str(claim_id),
            )
        )
    return observations, considered


def edge_input_digest(row: dict[str, Any]) -> str:
    """A deterministic sha256 over a reconciled edge's reproducible content.

    The idempotency key: two materialization passes over the same reconciled edge
    (same endpoints, kind, direction, temporal-bound kind, perspective, and the same
    sorted evidence-claim id set) digest identically → the insert is a no-op (+0). A
    changed evidence set → a new digest → a superseding append-only row.
    """
    stable = {
        "from_entity": row["from_entity"],
        "to_entity": row["to_entity"],
        "edge_type": row["edge_type"],
        "access_kind": row["access_kind"],
        "direction": row["direction"],
        "valid_from_kind": row["valid_from_kind"],
        "valid_to_kind": row["valid_to_kind"],
        "asserted_by": row["asserted_by"],
        "evidence_claims": sorted(row["evidence_claims"]),
    }
    payload = json.dumps(stable, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def edge_row(reconciled: ReconciledEdge) -> dict[str, Any] | None:
    """Map a §29.3 :class:`ReconciledEdge` onto a ``relationship`` table row.

    Returns ``None`` when an endpoint does not resolve to an ``entity`` (a name-only
    partner) — a ``relationship`` row requires both endpoints as ``entity`` FKs, so
    the edge is reconciled but not materialized (counted ``skipped_unmapped``), never
    a fabricated node. ``edge_type`` = ``access_kind`` (§12.5). ``evidence_claim`` is
    the deterministic representative backing claim (min claim id); the full evidence
    set feeds the idempotency digest.
    """
    from_entity = reconciled.from_org
    to_entity = reconciled.to_org
    if not (_is_uuid(from_entity) and _is_uuid(to_entity)):
        return None
    evidence_claims = sorted(o.claim_id for o in reconciled.observations if o.claim_id)
    if not evidence_claims:
        return None  # no unevidenced edges (§3.1)
    observed_dates = [o.observed_at for o in reconciled.observations if o.observed_at]
    observed_at = min(observed_dates) if observed_dates else None
    asserted_by = min(
        (o.asserted_by for o in reconciled.observations if o.asserted_by), default=from_entity
    )
    row: dict[str, Any] = {
        "from_entity": from_entity,
        "to_entity": to_entity,
        # §12.5: access_kind IS "which of the three edge types of §12.2"; the DB
        # edge_type catalog carries it (never 'integrates_with', SIG-ONTO-045).
        "edge_type": reconciled.access_kind,
        "access_kind": reconciled.access_kind,
        "direction": reconciled.direction,
        "valid_from_kind": reconciled.valid_from_kind,
        # A single-snapshot edge proves the current state, not when it ends
        # (SIG-ONTO-044): ongoing, never inferred.
        "valid_to_kind": "ongoing",
        "asserted_by": asserted_by,
        "observed_at": observed_at,
        "evidence_claim": evidence_claims[0],
        "evidence_claims": evidence_claims,
        "corroborated": reconciled.corroborated,
    }
    row["input_digest"] = edge_input_digest(row)
    return row


def _insert_relationship(conn: Any, row: dict[str, Any]) -> bool:
    """INSERT one relationship edge, idempotent on ``input_digest``. True iff inserted."""
    observed = row["observed_at"]
    result = conn.execute(
        "INSERT INTO relationship"
        "(from_entity, to_entity, edge_type, access_kind, direction, "
        " valid_period, valid_from_kind, valid_to_kind, asserted_by, observed_at, "
        " evidence_claim, input_digest) "
        "VALUES (%s, %s, %s, %s, %s, "
        " tstzrange(%s::timestamptz, NULL, '[)'), %s, %s, %s, %s::timestamptz, %s, %s) "
        "ON CONFLICT (input_digest) WHERE input_digest IS NOT NULL "
        "DO NOTHING RETURNING relationship_id",
        (
            row["from_entity"],
            row["to_entity"],
            row["edge_type"],
            row["access_kind"],
            row["direction"],
            observed,
            row["valid_from_kind"],
            row["valid_to_kind"],
            row["asserted_by"],
            observed,
            row["evidence_claim"],
            row["input_digest"],
        ),
    ).fetchone()
    return result is not None


def materialize_sharing_edges(
    conn: Any,
    *,
    jurisdiction: str | None = None,
    subject: str | None = None,
    role: str | None = None,
) -> EdgeMaterializeSummary:
    """Run the §29.3 sharing-edge reconciler over the spine and materialize edges (P28.2).

    Reads sharing-edge claims, reconciles them through **P08.2**
    (:func:`reconcile.sharing.reconcile_sharing` — consumed, not re-implemented), and
    writes each reconciled directed access edge as an append-only, idempotent
    ``relationship`` row. Contradictions (asymmetry) are RETURNED (kept visible),
    never written (P28.3 owns materializing them). A second call over unchanged
    claims inserts +0.
    """
    if role:
        conn.execute(f"SET ROLE {role}")

    observations, considered = read_sharing_observations(
        conn, jurisdiction=jurisdiction, subject=subject
    )
    # P08.2 §29.3 — the sole owner of sharing-edge reconciliation (SIG-RECON-034/035).
    reconciliation = reconcile_sharing(observations)

    inserted = skipped_existing = skipped_unmapped = 0
    by_kind: dict[str, int] = {}
    for reconciled in reconciliation.edges:
        row = edge_row(reconciled)
        if row is None:
            skipped_unmapped += 1
            continue
        if _insert_relationship(conn, row):
            inserted += 1
            by_kind[reconciled.access_kind] = by_kind.get(reconciled.access_kind, 0) + 1
        else:
            skipped_existing += 1

    return EdgeMaterializeSummary(
        considered_claims=considered,
        observations=len(observations),
        edges_reconciled=len(reconciliation.edges),
        inserted=inserted,
        skipped_existing=skipped_existing,
        skipped_unmapped=skipped_unmapped,
        contradictions=len(reconciliation.contradictions),
        asymmetry_tasks=len(reconciliation.tasks),
        by_access_kind=by_kind,
    )


def read_materialized_edges(conn: Any, *, role: str | None = None) -> list[dict[str, Any]]:
    """Read the materialized ``relationship`` edges as the network edge dataset (P28.5 seam).

    The "real edge dataset" that the P28.5 surface refresh (ADR-101) consumes to
    render the network island off the materialized graph instead of the compute-on-read
    shaping envelope. Read-only; deterministically ordered; every edge carries its
    access kind, direction, corroboration, temporal-bound kinds, and its backing
    ``evidence_claim`` (provenance). Never returns an unevidenced edge.
    """
    if role:
        conn.execute(f"SET ROLE {role}")
    rows = conn.execute(
        "SELECT from_entity::text, to_entity::text, edge_type, access_kind, direction, "
        "       valid_from_kind, valid_to_kind, asserted_by::text, "
        "       lower(valid_period), evidence_claim::text, relationship_id::text "
        "  FROM relationship "
        " WHERE input_digest IS NOT NULL "
        " ORDER BY from_entity, to_entity, access_kind, relationship_id"
    ).fetchall()
    edges: list[dict[str, Any]] = []
    for r in rows:
        edges.append(
            {
                "from_entity": r[0],
                "to_entity": r[1],
                "edge_type": r[2],
                "access_kind": r[3],
                "direction": r[4],
                "valid_from_kind": r[5],
                "valid_to_kind": r[6],
                "asserted_by": None if r[7] is None else r[7],
                "valid_from": r[8].isoformat() if isinstance(r[8], (datetime, date)) else None,
                "evidence_claim": r[9],
                "relationship_id": r[10],
            }
        )
    return edges


def materialize_sharing_edges_from_dsn(dsn: str, **kwargs: Any) -> EdgeMaterializeSummary:
    """Open an autocommit connection from ``dsn`` and materialize sharing edges (CLI)."""
    import psycopg  # available via the sig-db dependency (driver stays in `db`)

    conn = psycopg.connect(dsn, autocommit=True)
    try:
        return materialize_sharing_edges(conn, **kwargs)
    finally:
        conn.close()
