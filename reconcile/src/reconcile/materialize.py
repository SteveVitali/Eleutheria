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
  ``INSERT``s decision rows — there is no ``UPDATE``/``DELETE`` path on them. A
  genuinely changed input yields a new SIG-RECON-020 ``input_digest`` and a
  *superseding* decision; since P31.7 (ADR-R9-RESIGHT, when re-sighting links made
  capture-dated inputs actually change) the prior live ``auto`` decision's
  ``sys_period`` is closed first by the SECURITY DEFINER
  ``close_superseded_resolutions`` (§16.4's sanctioned supersession — a closed
  decision is kept as history, never edited in place or deleted); a re-run over
  unchanged inputs is a no-op.
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
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from typing import Any

from db.occurrences import (
    BELIEF_NOW,
    BELIEF_PARAM,
    observation_instant,
    occurrence_lateral,
)
from db.organization_roles import (
    ABSENCE_PREDICATES,
    ENTITY_REF_ROLES,
    ROLE_OF_PREDICATE,
    UNKNOWN_STATE_FOR_ROLE,
    role_slot,
)

from .contradiction import materialize as materialize_contradiction_entity
from .model import Contradiction
from .resolve import RESOLVE, Claim, Resolution
from .ruleset import Ruleset, load_ruleset
from .sharing import ACCESS_KINDS, ReconciledEdge, SharingObservation, reconcile_sharing

__all__ = [
    "MaterializeSummary",
    "SUPPORT_TO_CONFIDENCE",
    "read_claim_groups",
    "resolution_row",
    "materialize_resolutions",
    "read_materialized_resolutions",
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
    # P28.3 — the first-class, VISIBLE §31 contradiction object
    "ContradictionMaterializeSummary",
    "CONTRADICTION_CONFLICT_STATES",
    "contradiction_input_digest",
    "contradiction_row",
    "detected_contradictions",
    "materialize_contradictions",
    "materialize_contradictions_from_dsn",
    "read_materialized_contradictions",
    # P35.26 — role edges + explicit-unknown states (R11-L3-CP7)
    "RoleMaterializeSummary",
    "materialize_role_edges",
    "materialize_role_edges_from_dsn",
    "read_materialized_role_edges",
    "operator_state",
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
    #: Live ``auto`` decisions this pass superseded — their ``sys_period`` was closed
    #: by ``close_superseded_resolutions`` because the re-sighting-aware
    #: ``input_digest`` changed (P31.7 / ADR-R9-RESIGHT).
    superseded: int = 0
    #: Pairs left to a live NON-``auto`` (human) decision with a different digest:
    #: never auto-superseded, never crashed on — counted and reported.
    skipped_pinned: int = 0

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
            "superseded": self.superseded,
            "skipped_pinned": self.skipped_pinned,
        }


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date(1970, 1, 1)


#: The capture-time fallback for a claim that carries no ``observed_at`` (ADR-104,
#: revised by ADR-R9-RESIGHT). A registry connector deliberately keeps the per-run
#: retrieval timestamp out of the claim (so an unchanged registry does not mint
#: duplicate claims), which leaves ``claim.observed_at`` NULL; the capture's
#: ``retrieved_at`` is when the source was seen asserting the value. Since P31.7 every
#: re-sighting is linked (``record_resightings``), so the LATEST capture is used — the
#: most recent time the source was seen asserting the value. That is what makes a
#: reverting A → B → A value resolve to A under ``latest_observation_wins``: the
#: restated A's latest sighting post-dates B's.
#:
#: P32.4 / ADR-123 replaces the bare ``max(retrieved_at)`` probe with the shared
#: eligible-occurrence lateral (:func:`db.occurrences.occurrence_lateral`): only
#: ``role='establishes'`` bindings count (a corroborating/contradicting link is not
#: a sighting), and ``bound_at <= belief`` so a later capture/replay/correction can
#: never re-date a frozen past-belief read. Alias ``occ``; the lateral also carries
#: the source/genre/occurrence refs outputs preserve. This constant is the
#: current-knowledge variant kept for back-compat imports.
CAPTURE_TIME_JOIN = occurrence_lateral(BELIEF_NOW)

#: The count-scope / evidence-origin qualifiers (P32.3 / SIG-TRUST-004,
#: ADR-122). Reads the typed ``claim_qualifier`` surface P32.2 added: the
#: ``count_scope`` qualifier's ``value_text`` is the scope label and its
#: ``jurisdiction`` column is the evidenced jurisdiction the scope is anchored
#: to; ``count_scope_detail`` refines the scope (``privately_owned`` …);
#: ``evidence_origin`` marks seeded/fixture material (``seed_fixture``) so no
#: read surface presents it as primary live evidence. Alias ``q``; select
#: ``q.count_scope, q.count_scope_detail, q.count_scope_jurisdiction,
#: q.evidence_origin``.
COUNT_QUALIFIER_JOIN = (
    "  LEFT JOIN LATERAL ("
    "     SELECT max(CASE WHEN q.qualifier_id = 'count_scope' THEN q.value_text END)"
    "              AS count_scope,"
    "            max(CASE WHEN q.qualifier_id = 'count_scope_detail' THEN q.value_text END)"
    "              AS count_scope_detail,"
    "            max(CASE WHEN q.qualifier_id = 'count_scope' THEN q.jurisdiction END)"
    "              AS count_scope_jurisdiction,"
    "            max(CASE WHEN q.qualifier_id = 'evidence_origin' THEN q.value_text END)"
    "              AS evidence_origin"
    "       FROM claim_qualifier q WHERE q.claim_id = c.claim_id) q ON true "
)

#: ``Claim.observed_at_basis`` for a claim dated from its LATEST sighting's capture
#: (labelled by the resolver in ``rules_fired``). ADR-104's interim name was
#: ``capture_retrieved_at`` (earliest capture, before re-sightings were linked); the
#: new name keeps pre/post-ADR-R9-RESIGHT envelopes distinguishable.
CAPTURE_TIME_BASIS = "capture_retrieved_at_latest"

#: The pre-ADR-104 placeholder for an undated claim with no capture time either.
_UNDATED = date(1970, 1, 1)

#: P35.25 (SIG-CONF-014): the declared-lineage read. ``claim_lineage`` is an
#: additive P35.25 table — a spine deployed before the change simply has no
#: declared lineage, and every claim resolves ``unclassified`` (the honest
#: default: undeclared material never counts as independent). Present, the
#: join supplies each claim's declared ``independence_class``/``id_namespace``
#: and any recovered ``derived_from_claim_ids`` ancestry; a claim whose own
#: class is undeclared but whose ancestor's is declared inherits the
#: ANCESTOR's class (a derivation copies its upstream's voice — never a
#: second independent one).
_LINEAGE_JOIN = "  LEFT JOIN claim_lineage cl ON cl.claim_id = c.claim_id "
_LINEAGE_COLS = (
    "cl.independence_class, cl.id_namespace, cl.derived_from_claim_ids, c.derived_from_claim_ids"
)
_NO_LINEAGE_COLS = "NULL, NULL, NULL, c.derived_from_claim_ids"
_ANCESTOR_CLASS_SQL = (
    "SELECT claim_id::text, independence_class FROM claim_lineage WHERE claim_id = ANY(%s::uuid[])"
)


def _resolve_lineage(conn: Any, built: list[tuple[Claim, list[str], str | None]]) -> None:
    """Inherit ancestor independence classes for undeclared derived claims.

    ``built`` holds ``(claim, derived_ids, stored_class)`` triples. A claim
    with derivation ancestry but no declared class takes the ancestor's class
    when one ancestor's ``claim_lineage`` row declares a real class (one-hop
    lookup — deeper chains stay unclassified, never guessed). The result is
    written back onto the group lists by replacing the Claim values — the
    frozen dataclass is rebuilt, never mutated.
    """
    ancestors: set[str] = set()
    for claim, derived, stored in built:
        declared = stored if stored and stored != "unclassified" else claim.independence_class
        if declared or claim.derived_from_source:
            continue
        ancestors.update(derived)
    if not ancestors:
        return
    ancestor_class: dict[str, str] = {}
    for cid, cls in conn.execute(_ANCESTOR_CLASS_SQL, (sorted(ancestors),)).fetchall():
        if cls and cls != "unclassified":
            ancestor_class[str(cid)] = str(cls)
    for i, (claim, derived, stored) in enumerate(built):
        declared = stored if stored and stored != "unclassified" else claim.independence_class
        if declared or claim.derived_from_source:
            continue
        inherited = next((ancestor_class[a] for a in sorted(derived) if a in ancestor_class), None)
        if inherited is not None:
            built[i] = (replace(claim, independence_class=inherited), derived, stored)


def observation_time(observed_at: Any, retrieved_at: Any) -> tuple[date, str]:
    """``(observed_at, basis)`` for the resolver's ``Claim`` (ADR-104).

    The claim's own ``observed_at`` when it has one (basis ``"claim"``); else the
    LATEST sighting capture's ``retrieved_at`` (basis ``CAPTURE_TIME_BASIS``, which
    the resolver labels in ``rules_fired``; ADR-R9-RESIGHT); else the historical
    1970 placeholder, which makes the claim HISTORICAL — undated evidence is never
    treated as current.
    """
    if observed_at:
        return _as_date(observed_at), "claim"
    if retrieved_at:
        # UTC calendar date, independent of the reading session's time zone, so every
        # reader (materializer, CLI, API) derives the same date and input_digest.
        if isinstance(retrieved_at, datetime) and retrieved_at.tzinfo is not None:
            retrieved_at = retrieved_at.astimezone(UTC)
        return _as_date(retrieved_at), CAPTURE_TIME_BASIS
    return _UNDATED, "claim"


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
    as_of_belief: datetime | None = None,
) -> dict[tuple[str, str], list[Claim]]:
    """Read L0 tier-0 claims from the spine, grouped by ``(subject, predicate)``.

    Mirrors the read the read-only ``reconcile resolve`` CLI performs (contradictions
    visible, §3.1): the same lateral-join evidence chain for the source id/genre, the
    same tier-0-only filter, ordered deterministically. When ``as_of_belief`` is given
    the read is belief-filtered (``sys_period @> belief``) exactly as
    ``api.store_pg._public_claim_groups`` does — so a claim whose transaction-time
    interval has been closed (an append-only retraction) drops out of the current
    belief; the default (``None``) keeps the P28.1 all-claims behaviour unchanged.
    """
    where = ["c.sensitivity_tier = 0"]
    params: list[Any] = []
    if as_of_belief is not None:
        where.append("c.sys_period @> %s::timestamptz")
        params.append(as_of_belief)
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

    # The eligible-occurrence lateral carries its own belief bound — the SAME
    # instant the ``sys_period @> belief`` filter uses, so a claim and its
    # evidence bindings are visible at exactly the same knowledge instant
    # (ADR-123). ``None`` reads current knowledge (``clock_timestamp()``).
    occ_belief = BELIEF_PARAM if as_of_belief is not None else BELIEF_NOW
    occ_params = [as_of_belief] if as_of_belief is not None else []

    # P35.25: the claim_lineage join runs only where the additive change has
    # deployed — an un-migrated spine resolves every claim ``unclassified``,
    # the honest pre-declaration state.
    lineage_probe = conn.execute("SELECT to_regclass('public.claim_lineage')").fetchone()
    has_lineage = bool(lineage_probe and lineage_probe[0])
    lineage_cols = _LINEAGE_COLS if has_lineage else _NO_LINEAGE_COLS
    lineage_join = _LINEAGE_JOIN if has_lineage else " "

    rows = conn.execute(
        "SELECT c.subject_id, c.predicate_id, c.claim_id, c.value_kind, c.value_text, "
        "       c.value_num, c.value_bool, c.raw_value, c.observed_at, c.source_reliability, "
        "       c.artifact_integrity, c.review_status, occ.source_id, occ.artifact_type, "
        "       occ.retrieved_at, occ.capture_id, occ.bound_at, "
        "       q.count_scope, q.count_scope_detail, q.count_scope_jurisdiction, "
        "       q.evidence_origin, "
        f"       {lineage_cols}"
        "  FROM claim c "
        + occurrence_lateral(occ_belief)
        + COUNT_QUALIFIER_JOIN
        + lineage_join
        + " WHERE "
        + " AND ".join(where)
        + " ORDER BY c.subject_id, c.predicate_id, c.claim_id",
        tuple(occ_params + params),
    ).fetchall()

    groups: dict[tuple[str, str], list[Claim]] = {}
    # (claim, derived ids, stored lineage class) — the derived/undeclared
    # ancestry pass below may inherit the ancestor's declared class.
    built: list[tuple[Claim, list[str], str | None]] = []
    for r in rows:
        key = (str(r[0]), str(r[1]))
        observed_at, basis = observation_time(r[8], r[14])
        stored_class = r[21] or None
        stored_ns = r[22] or None
        derived_ids = sorted({str(x) for x in (r[23] or ())} | {str(x) for x in (r[24] or ())})
        claim = Claim(
            claim_id=str(r[2]),
            subject_id=str(r[0]),
            predicate_id=str(r[1]),
            value=_value(r[3], r[4], r[5], r[6]),
            reliability=r[9],
            integrity=r[10],
            genre=r[13] or "",
            observed_at=observed_at,
            observed_at_basis=basis,
            observed_instant=observation_instant(r[8], r[14]),
            occurrence_capture_id=str(r[15]) if r[15] is not None else None,
            occurrence_retrieved_at=r[14],
            occurrence_bound_at=r[16],
            raw_value=r[7] or "",
            review_status=r[11] or "active",
            source_id=r[12] or "",
            count_basis=str(r[1]).removesuffix("_device_count")
            if str(r[1]).endswith("_device_count")
            else None,
            count_scope=r[17],
            count_scope_detail=r[18],
            count_scope_jurisdiction=r[19],
            evidence_origin=r[20],
            independence_class=(
                stored_class if stored_class and stored_class != "unclassified" else None
            ),
            id_namespace=stored_ns,
            derived_from_claim_ids=tuple(derived_ids),
        )
        groups.setdefault(key, []).append(claim)
        built.append((claim, derived_ids, stored_class))
    # P35.25: undeclared claims carrying derivation ancestry inherit the
    # ancestor's declared class when one resolves (a derivation is its
    # upstream's voice — never a second independent one).
    if has_lineage:
        _resolve_lineage(conn, built)
        replaced = {c.claim_id: c for c, _d, _s in built}
        groups = {k: [replaced.get(m.claim_id, m) for m in ms] for k, ms in groups.items()}
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
        # P35.25 (SIG-CONF-014): how much of the considered evidence carries no
        # declared lineage — the ``unclassified`` pseudo-class never counts as
        # an independent voice, and this count keeps the remainder visible.
        "n_unclassified_claims": len(resolved.unclassified_claim_ids),
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
    as_of_belief: datetime | None = None,
    ruleset: Ruleset | None = None,
    role: str | None = None,
    progress: Callable[[int, int, int], None] | None = None,
    progress_every: int = 100_000,
    batch_size: int = 1_000,
) -> MaterializeSummary:
    """Run the §28 resolver over the spine and materialize the envelopes (P28.1).

    Reads tier-0 claims grouped by ``(subject, predicate)``, resolves each group, and
    writes the decision as an append-only, idempotent ``resolution`` row. Returns a
    :class:`MaterializeSummary`; a second call over unchanged claims inserts +0.
    ``progress(considered, total, inserted)`` — if given — is called every
    ``progress_every`` groups so a long hosted pass reports throughput (ETA) as it runs.

    ``as_of_belief`` pins the whole read to one knowledge instant (ADR-123): claims
    outside ``sys_period @> belief`` are invisible AND evidence bindings with
    ``bound_at > belief`` are invisible — a later capture/replay/correction cannot
    re-date or un-see a frozen past-belief materialization. Default ``None`` reads
    current knowledge, the P28.1 behaviour.
    """
    rs = ruleset or load_ruleset()
    if role:
        conn.execute(f"SET ROLE {role}")
    as_of_world = as_of or datetime.now(tz=UTC).date()

    groups = read_claim_groups(
        conn,
        jurisdiction=jurisdiction,
        subject=subject,
        predicate=predicate,
        as_of_belief=as_of_belief,
    )

    considered = inserted = skipped_existing = skipped_unresolvable = 0
    superseded = skipped_pinned = 0
    resolved_n = unresolved_n = 0
    # The FK vocab rows are few (strategies x rationale codes x confidences); upsert each
    # distinct triple once per pass instead of three round-trips per envelope — the write
    # path is latency-bound at hosted scale (P30.1/P30.2). Still INSERT ... DO NOTHING only.
    ensured_vocab: set[tuple[str, str, str]] = set()
    # Envelopes are written in batches of ``batch_size``, one transaction per batch, so a
    # hosted pass pays one commit per batch rather than one per row. Each insert stays
    # ``ON CONFLICT (input_digest) DO NOTHING``: a failed batch rolls back whole and a re-run
    # completes it (+0 for everything already written).
    pending: list[dict[str, Any]] = []

    def flush() -> tuple[int, int, int, int]:
        added = existing = closed = pinned = 0
        with conn.transaction():
            # Supersession (P31.7 / ADR-R9-RESIGHT): a re-sighting moves a claim's
            # latest-capture date, which changes the SIG-RECON-020 input_digest —
            # a genuinely changed input yields a NEW decision row and the prior
            # live decision's ``sys_period`` is closed first (§16.4), never an
            # in-place edit. ``close_superseded_resolutions`` is SECURITY DEFINER
            # so ``sig_materialize`` stays INSERT-only; it closes only live
            # ``decided_by='auto'`` rows whose digest differs, and reports the
            # pairs a live non-auto (human) decision still holds — those inserts
            # are skipped, never crashed on and never silently overridden.
            transitions = conn.execute(
                "SELECT subject_id::text, predicate_id, action "
                "FROM close_superseded_resolutions(%s::uuid[], %s::text[], %s::text[])",
                (
                    [row["subject_id"] for row in pending],
                    [row["predicate_id"] for row in pending],
                    [row["input_digest"] for row in pending],
                ),
            ).fetchall()
            blocked = {
                (str(subject_id), predicate_id)
                for subject_id, predicate_id, action in transitions
                if action == "blocked"
            }
            closed = sum(1 for *_rest, action in transitions if action == "closed")
            for row in pending:
                if (row["subject_id"], row["predicate_id"]) in blocked:
                    pinned += 1
                    continue
                vocab_key = (row["strategy_id"], row["rationale_code"], row["confidence"])
                if vocab_key not in ensured_vocab:
                    _ensure_vocab(conn, row)
                    ensured_vocab.add(vocab_key)
                if _insert_resolution(conn, row):
                    added += 1
                else:
                    existing += 1
        pending.clear()
        return added, existing, closed, pinned

    total = len(groups)
    for (subj, pred), claims in sorted(groups.items()):
        considered += 1
        if progress is not None and considered % progress_every == 0:
            progress(considered, total, inserted)
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
        pending.append(row)
        if resolved.resolution_status == "RESOLVED":
            resolved_n += 1
        else:
            unresolved_n += 1
        if len(pending) >= batch_size:
            added, existing, closed, pinned = flush()
            inserted += added
            skipped_existing += existing
            superseded += closed
            skipped_pinned += pinned
    if pending:
        added, existing, closed, pinned = flush()
        inserted += added
        skipped_existing += existing
        superseded += closed
        skipped_pinned += pinned

    return MaterializeSummary(
        considered_pairs=considered,
        inserted=inserted,
        skipped_existing=skipped_existing,
        skipped_unresolvable=skipped_unresolvable,
        resolved=resolved_n,
        unresolved=unresolved_n,
        superseded=superseded,
        skipped_pinned=skipped_pinned,
    )


def materialize_from_dsn(dsn: str, **kwargs: Any) -> MaterializeSummary:
    """Open an autocommit connection from ``dsn`` and materialize (CLI convenience)."""
    import psycopg  # available via the sig-db dependency (driver stays in `db`)

    conn = psycopg.connect(dsn, autocommit=True)
    try:
        return materialize_resolutions(conn, **kwargs)
    finally:
        conn.close()


def read_materialized_resolutions(conn: Any, *, role: str | None = None) -> list[dict[str, Any]]:
    """Read the materialized ``resolution`` envelopes (the P28.5 surface seam, ADR-101).

    The real resolution dataset the P28.5 surface refresh consumes to derive the honest
    "N resolved sites (from M observations)" framing off the materialized graph instead of
    the compute-on-read observation envelope (ADR-092). Read-only; deterministically ordered;
    every row carries its ``contradiction_state`` and confidence, and ``resolved`` is True iff
    the envelope picked a winning claim (an ``unresolved_conflict`` envelope resolves nothing,
    so it is materialized but not counted as a resolved site — contradictions stay visible,
    §3.1). Only rows the materializer wrote (``input_digest IS NOT NULL``) that are
    CURRENT — ``upper_inf(sys_period)`` — are returned: a superseded decision (closed
    ``sys_period``, P31.7 / ADR-R9-RESIGHT) stays in the table as recorded history but
    is not part of the resolved surface.
    """
    if role:
        conn.execute(f"SET ROLE {role}")
    rows = conn.execute(
        "SELECT resolution_id::text, subject_id::text, predicate_id, value_kind, "
        "       value_text, value_num, winning_claim::text, contradiction_state, confidence "
        "  FROM resolution "
        " WHERE input_digest IS NOT NULL AND upper_inf(sys_period) "
        " ORDER BY subject_id, predicate_id, resolution_id"
    ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "resolution_id": r[0],
                "subject_id": r[1],
                "predicate_id": r[2],
                "value_kind": r[3],
                "value_text": r[4],
                "value_num": None if r[5] is None else float(r[5]),
                "winning_claim": None if r[6] is None else str(r[6]),
                "contradiction_state": r[7],
                "confidence": r[8],
                # A resolved decision picked a winning claim; an unresolved_conflict did not.
                "resolved": r[6] is not None,
            }
        )
    return out


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
    #: Live rows sys_period-closed because this pass's row for the same
    #: (from,to,kind) carries a different digest — recorded succession (P35.26).
    superseded: int = 0
    #: Live rows closed because no claim set evidences their edge any more.
    closed_stale: int = 0
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
            "superseded": self.superseded,
            "closed_stale": self.closed_stale,
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
                # P35.26 / SIG-ONTO-030: an undated claim is UNDATED — never the
                # 1970-01-01 placeholder the pre-fix path wrote.
                observed_at=_as_date(observed_at) if observed_at else None,
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
        "observed_at": row["observed_at"],
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
        # P35.26 / SIG-ONTO-030: an edge with no evidenced date is explicitly
        # `undated` (its valid_period is unbounded), never the reconciler's
        # snapshot-start kind and never an epoch bound; a dated edge keeps the
        # reconciler's start kind (SIG-RECON-036 — a snapshot never proves a start).
        "valid_from_kind": reconciled.valid_from_kind if observed_at else "undated",
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
    """INSERT one relationship edge, idempotent on ``input_digest``. True iff inserted.

    ``observed_at=None`` writes an UNBOUNDED ``valid_period`` + NULL
    ``observed_at`` — the explicit undated edge (P35.26 / SIG-ONTO-030), never
    an epoch bound. ``supersedes`` (P35.26) links the recorded succession to
    the live row this row replaces.
    """
    observed = row["observed_at"]
    result = conn.execute(
        "INSERT INTO relationship"
        "(from_entity, to_entity, edge_type, access_kind, direction, "
        " valid_period, valid_from_kind, valid_to_kind, asserted_by, observed_at, "
        " evidence_claim, input_digest, supersedes) "
        "VALUES (%s, %s, %s, %s, %s, "
        " tstzrange(%s::timestamptz, NULL, '[)'), %s, %s, %s, %s::timestamptz, %s, %s, %s) "
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
            row.get("supersedes"),
        ),
    ).fetchone()
    return result is not None


def _live_relationship_edges(
    conn: Any, *, subjects: list[str]
) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    """The live (``upper_inf(sys_period)``) materialized edges keyed by ``(from,to,type)``.

    Scoped to the subject entities this pass actually read — a ``--subject`` /
    ``--jurisdiction`` filtered run never touches another subject's edges.
    """
    if not subjects:
        return {}
    rows = conn.execute(
        "SELECT relationship_id::text, from_entity::text, to_entity::text, edge_type, "
        "       input_digest, lower(sys_period) "
        "  FROM relationship "
        " WHERE upper_inf(sys_period) AND input_digest IS NOT NULL "
        "   AND from_entity = ANY(%s::uuid[])"
        " ORDER BY from_entity, to_entity, edge_type, sys_period",
        (subjects,),
    ).fetchall()
    out: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for rid, frm, to, kind, digest, sys_lower in rows:
        out.setdefault((str(frm), str(to), str(kind)), []).append(
            {
                "relationship_id": str(rid),
                "input_digest": digest,
                "sys_lower": sys_lower,
            }
        )
    return out


def _close_relationship_ids(conn: Any, ids: list[str]) -> int:
    """Close the sys_period of live relationship rows (the sanctioned mutation).

    ``close_superseded_relationships`` is SECURITY DEFINER (the role_edges
    sqitch change): the caller keeps an INSERT-only posture, and only rows
    still live are closed — a re-run over an already-closed set is +0.
    Returns the number of rows actually closed.
    """
    if not ids:
        return 0
    rows = conn.execute(
        "SELECT relationship_id::text FROM close_superseded_relationships(%s::uuid[])",
        (ids,),
    ).fetchall()
    return len(rows)


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
    superseded = closed_stale = 0
    by_kind: dict[str, int] = {}

    # P35.26 / GQ-15: supersession is a RECORDED edge succession. Live rows for
    # the subjects this pass read whose digest differs from the pass's row (or
    # whose edge no claim set evidences any more) have their sys_period closed
    # by ``close_superseded_relationships`` — the one sanctioned temporal
    # mutation, never an in-place edit — and the new row's ``supersedes`` links
    # the predecessor. Scope: only ``from_entity`` subjects this pass read.
    read_subjects = sorted({o.from_org for o in observations if _is_uuid(o.from_org)})
    live = _live_relationship_edges(conn, subjects=read_subjects)

    desired_keys: set[tuple[str, str, str]] = set()
    for reconciled in reconciliation.edges:
        row = edge_row(reconciled)
        if row is None:
            skipped_unmapped += 1
            continue
        key = (row["from_entity"], row["to_entity"], row["edge_type"])
        desired_keys.add(key)
        live_rows = live.get(key, [])
        # The live row with a DIFFERENT digest is a superseded version of this
        # edge — close it and link the succession.
        predecessors = [r for r in live_rows if r["input_digest"] != row["input_digest"]]
        if predecessors:
            # Deterministic link: the most recently opened predecessor.
            predecessors.sort(key=lambda r: r["sys_lower"], reverse=True)
            row["supersedes"] = predecessors[0]["relationship_id"]
            closed = _close_relationship_ids(conn, [r["relationship_id"] for r in predecessors])
            superseded += closed
        if _insert_relationship(conn, row):
            inserted += 1
            by_kind[reconciled.access_kind] = by_kind.get(reconciled.access_kind, 0) + 1
        else:
            skipped_existing += 1

    # A live edge for a read subject whose (from,to,type) this pass produced
    # nothing for is stale — its evidence set is gone; close it.
    stale_ids = [
        r["relationship_id"] for key, rows in live.items() if key not in desired_keys for r in rows
    ]
    if stale_ids:
        closed_stale = _close_relationship_ids(conn, stale_ids)

    return EdgeMaterializeSummary(
        considered_claims=considered,
        observations=len(observations),
        edges_reconciled=len(reconciliation.edges),
        inserted=inserted,
        skipped_existing=skipped_existing,
        skipped_unmapped=skipped_unmapped,
        superseded=superseded,
        closed_stale=closed_stale,
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

    P35.26: only LIVE rows (``upper_inf(sys_period)``) — a superseded edge stays
    in the table as recorded succession history but is not part of the current
    network dataset (0 live duplicates per (from,to,kind), GQ-15).
    """
    if role:
        conn.execute(f"SET ROLE {role}")
    rows = conn.execute(
        "SELECT from_entity::text, to_entity::text, edge_type, access_kind, direction, "
        "       valid_from_kind, valid_to_kind, asserted_by::text, "
        "       lower(valid_period), evidence_claim::text, relationship_id::text "
        "  FROM relationship "
        " WHERE input_digest IS NOT NULL AND upper_inf(sys_period) "
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


# ============================================================================
# P28.3 — Materialize the first-class, VISIBLE §31 contradiction object.
#
# The Appendix C.6 ``contradiction`` table (the point of retiring Risk 3 — a
# disagreement kept VISIBLE, never silently reconciled, §3.1) has existed since
# P02.1 but has never held a row: the launch posture computed contradictions on
# read (ADR-092, ``api.store_pg._compute_on_read``). :func:`materialize_contradictions`
# runs the SAME detector that compute-on-read uses — the §28 resolver
# (:func:`reconcile.resolve.RESOLVE`), which itself performs the §29.1 count-basis
# reconciliation guard and emits :class:`reconcile.model.Contradiction` objects
# (the 299-vs-190 pattern surfaces here as a within-predicate value disagreement) —
# over the real (resolved) spine and WRITES each detected contradiction as a durable
# ``contradiction`` row, honoring every invariant the spine demands:
#
# * **Contradictions stay VISIBLE (§3.1).** Both open and settled contradictions are
#   written and read back; nothing is collapsed to a single value the evidence does
#   not support. Every row carries BOTH evidence sides in ``claim_ids``.
# * **Append-only + lifecycle-aware (ADR-005, SIG-RECON-021/055).** This path only
#   ``INSERT``s — there is no ``UPDATE``/``DELETE``. A contradiction resolved by later
#   evidence (an OPEN finding the resolver no longer detects over the current spine)
#   is materialized as a NEW ``superseded`` state row via the model lifecycle
#   (:meth:`reconcile.model.Contradiction.supersede`); the open row is retained in
#   history, never deleted.
# * **Idempotent (+0).** The insert is ``ON CONFLICT (input_digest) DO NOTHING``
#   against the ``contradiction_input_digest_key`` partial unique index (the
#   ``contradiction_materialize`` sqitch change). The digest folds in the lifecycle
#   ``status``, so re-running over an unchanged spine inserts each state exactly once.
# * **REUSE, not re-implement (SIG-ENG-035).** The §31 entity + content-derived
#   identity are the P08.3 :func:`reconcile.contradiction.materialize` /
#   :func:`derive_contradiction_id`; the §29 reconciliation is
#   :func:`reconcile.resolve.RESOLVE` (which consumes ``reconcile.counts``) and the
#   detected objects are :class:`reconcile.model.Contradiction`. :func:`contradiction_row`
#   maps ANY ``reconcile.model.Contradiction`` onto a row, so a contradiction produced
#   by ``reconcile.counts`` (§29 count reconciliation) or ``reconcile.lifecycle``
#   (§29.4 procurement-vs-physical) materializes through the same writer.
#
# Materializing the research tasks a contradiction generates is a separate concern
# (the ``research_task`` table + FK linkage); ``research_task_ids`` is left NULL here
# — the contradiction entity and its visible evidence sides are what this ticket owns.
# ============================================================================

#: The resolver ``contradiction_state`` values that name a genuine conflict — the
#: exact set ``api.store_pg._compute_on_read`` surfaces as a contradiction. A
#: ``uncontested`` / ``none`` / insufficient resolution is NOT a contradiction.
CONTRADICTION_CONFLICT_STATES: frozenset[str] = frozenset(
    {"resolved_conflict", "unresolved_conflict"}
)


@dataclass(frozen=True)
class ContradictionMaterializeSummary:
    """The outcome of one contradiction materialization pass — every group accounted for."""

    considered_pairs: int = 0
    detected: int = 0
    inserted: int = 0
    skipped_existing: int = 0
    skipped_unevidenced: int = 0
    superseded: int = 0
    by_type: dict[str, int] = field(default_factory=dict)

    @property
    def written(self) -> int:
        return self.inserted + self.superseded

    def as_dict(self) -> dict[str, Any]:
        return {
            "considered_pairs": self.considered_pairs,
            "detected": self.detected,
            "inserted": self.inserted,
            "skipped_existing": self.skipped_existing,
            "skipped_unevidenced": self.skipped_unevidenced,
            "superseded": self.superseded,
            "by_type": dict(sorted(self.by_type.items())),
        }


def contradiction_input_digest(row: dict[str, Any]) -> str:
    """A deterministic sha256 over a contradiction's reproducible detected state.

    The idempotency key: two passes over the same detected contradiction in the same
    lifecycle state (same subject, predicate, type, sorted claim-id set, status,
    severity) digest identically → the insert is a no-op (+0). A lifecycle transition
    (``open`` → ``superseded``) changes the ``status`` component → a new digest → a new
    superseding append-only row, never an edit of the open one.
    """
    stable = {
        "subject_id": row["subject_id"],
        "predicate_id": row["predicate_id"],
        "contradiction_type": row["contradiction_type"],
        "claim_ids": sorted(str(c) for c in row["claim_ids"]),
        "status": row["status"],
        "severity": row["severity"],
    }
    payload = json.dumps(stable, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def contradiction_row(detected: Contradiction) -> dict[str, Any] | None:
    """Map a :class:`reconcile.model.Contradiction` onto a ``contradiction`` table row.

    Mirrors the ``api.store_pg._persisted_contradictions`` shape (subject_id,
    predicate_id, contradiction_type, status, claim_ids) plus the lifecycle/severity
    columns. Returns ``None`` for a contradiction with no linked claim ids — a
    ``contradiction`` row requires ``claim_ids`` NOT NULL and SIG never asserts an
    unevidenced contradiction (§3.1): both disagreeing sides must resolve to real
    claim rows. ``input_digest`` is the idempotency key (folds in the lifecycle
    ``status``). ``research_task_ids`` is left NULL (materializing task rows is a
    separate concern).
    """
    claim_ids = [str(c) for c in detected.claim_ids if c]
    if not claim_ids:
        return None
    row: dict[str, Any] = {
        "subject_id": detected.subject_id,
        "predicate_id": detected.predicate_id,
        "contradiction_type": detected.contradiction_type,
        "claim_ids": claim_ids,
        "severity": detected.severity,
        "status": detected.status,
        "resolution_note": detected.resolution_note,
        "resolved_by": detected.resolved_by,
        "resolved_at": detected.resolved_at,
    }
    row["input_digest"] = contradiction_input_digest(row)
    return row


def detected_contradictions(
    subject_id: str, predicate_id: str, resolved: Resolution, claims: list[Claim]
) -> list[Contradiction]:
    """The materializable §31 contradiction entities for one resolved (subject, predicate).

    Mirrors ``api.store_pg._compute_on_read``: the resolver's own emitted §29.1/§28
    ``Contradiction``s (predicate-conflation / value-domain-mismatch — CONSUMED from
    :func:`reconcile.resolve.RESOLVE`, which runs the §29 count-basis reconciliation)
    are materialized with their real types; and a plain within-predicate value
    disagreement (the 299-vs-190 pattern) — signalled by
    ``contradiction_state ∈ CONTRADICTION_CONFLICT_STATES`` — is synthesized as a
    ``value_disagreement`` entity. Each entity is given a stable, content-derived
    identity by the P08.3 :func:`reconcile.contradiction.materialize` and carries BOTH
    evidence sides in ``claim_ids`` (the group's considered claims).
    """
    considered = tuple(resolved.considered_claim_ids)
    out: list[Contradiction] = []
    for c in resolved.contradictions:
        out.append(materialize_contradiction_entity(c, claim_ids=considered or c.claim_ids))
    # Mirror api.store_pg._compute_on_read: at most one synthesized record per pair, and
    # only when the resolver emitted none of its own (predicate-conflation /
    # value-domain-mismatch already speak for the group).
    conflict = resolved.contradiction_state in CONTRADICTION_CONFLICT_STATES
    if not resolved.contradictions and conflict:
        values = tuple(sorted({repr(c.value) for c in claims}))
        detected = Contradiction(
            contradiction_type="value_disagreement",
            subject_id=subject_id,
            predicate_id=predicate_id,
            claim_values=values,
            note=(
                f"{predicate_id}: {len(considered)} claims disagree "
                f"({resolved.contradiction_state}); both retained, neither collapsed (§3.1)."
            ),
            severity="notable",
            status="open",
            claim_ids=considered,
        )
        out.append(materialize_contradiction_entity(detected, claim_ids=considered))
    return out


def _insert_contradiction(conn: Any, row: dict[str, Any]) -> bool:
    """INSERT one contradiction row, idempotent on ``input_digest``. True iff inserted."""
    result = conn.execute(
        "INSERT INTO contradiction"
        "(subject_id, predicate_id, contradiction_type, claim_ids, severity, status, "
        " resolution_note, resolved_by, resolved_at, input_digest) "
        "VALUES (%s, %s, %s, %s::uuid[], %s, %s, %s, %s, %s::timestamptz, %s) "
        "ON CONFLICT (input_digest) WHERE input_digest IS NOT NULL "
        "DO NOTHING RETURNING contradiction_id",
        (
            row["subject_id"],
            row["predicate_id"],
            row["contradiction_type"],
            row["claim_ids"],
            row["severity"],
            row["status"],
            row["resolution_note"],
            row["resolved_by"],
            row["resolved_at"],
            row["input_digest"],
        ),
    ).fetchone()
    return result is not None


def _open_contradictions(conn: Any) -> list[tuple[str, str, str, list[str]]]:
    """The live (open / under_research) materialized contradictions, for supersession."""
    rows = conn.execute(
        "SELECT subject_id::text, predicate_id, contradiction_type, claim_ids "
        "  FROM contradiction "
        " WHERE status IN ('open', 'under_research') AND input_digest IS NOT NULL "
        " ORDER BY subject_id, predicate_id, contradiction_type"
    ).fetchall()
    return [(str(r[0]), str(r[1]), str(r[2]), [str(x) for x in (r[3] or ())]) for r in rows]


def _superseded_keys(conn: Any) -> set[tuple[str, str, str]]:
    """The (subject, predicate, type) triples that already carry a superseded row."""
    rows = conn.execute(
        "SELECT subject_id::text, predicate_id, contradiction_type "
        "  FROM contradiction WHERE status = 'superseded' AND input_digest IS NOT NULL"
    ).fetchall()
    return {(str(r[0]), str(r[1]), str(r[2])) for r in rows}


def materialize_contradictions(
    conn: Any,
    *,
    jurisdiction: str | None = None,
    subject: str | None = None,
    predicate: str | None = None,
    as_of: date | None = None,
    ruleset: Ruleset | None = None,
    role: str | None = None,
) -> ContradictionMaterializeSummary:
    """Run §29 reconciliation over the spine and materialize contradictions (P28.3).

    Reads tier-0 claims grouped by ``(subject, predicate)``, runs the §28 ``RESOLVE``
    (the detector ``api.store_pg._compute_on_read`` uses — CONSUMED), and writes an
    append-only, idempotent ``contradiction`` row for every genuine conflict — kept
    VISIBLE with both evidence sides, never reconciled away (§3.1). A prior OPEN
    contradiction the resolver no longer detects over the current spine is materialized
    as a NEW ``superseded`` state row (never a delete). Returns a summary; a second call
    over an unchanged spine inserts +0.
    """
    rs = ruleset or load_ruleset()
    if role:
        conn.execute(f"SET ROLE {role}")
    belief = datetime.now(tz=UTC)
    as_of_world = as_of or belief.date()

    # Belief-filtered exactly as api.store_pg._compute_on_read: a claim whose sys_period
    # was closed (an append-only retraction) is no longer in the current belief, so its
    # disagreement resolves — the lifecycle transition the supersession pass detects.
    groups = read_claim_groups(
        conn,
        jurisdiction=jurisdiction,
        subject=subject,
        predicate=predicate,
        as_of_belief=belief,
    )

    considered = detected = inserted = skipped_existing = skipped_unevidenced = 0
    by_type: dict[str, int] = {}
    detected_keys: set[tuple[str, str, str]] = set()
    for (subj, pred), claims in sorted(groups.items()):
        considered += 1
        try:
            resolved = RESOLVE(
                subj, pred, claims, as_of_world=as_of_world, as_of_belief=as_of_world, ruleset=rs
            )
        except KeyError:
            # Predicate not in the resolver ruleset — not materializable (ADR-092 fallback).
            continue
        for entity in detected_contradictions(subj, pred, resolved, claims):
            detected += 1
            row = contradiction_row(entity)
            if row is None:
                skipped_unevidenced += 1
                continue
            detected_keys.add((subj, pred, entity.contradiction_type))
            if _insert_contradiction(conn, row):
                inserted += 1
                by_type[entity.contradiction_type] = by_type.get(entity.contradiction_type, 0) + 1
            else:
                skipped_existing += 1

    superseded = _supersede_resolved(conn, detected_keys, as_of=as_of_world)

    return ContradictionMaterializeSummary(
        considered_pairs=considered,
        detected=detected,
        inserted=inserted,
        skipped_existing=skipped_existing,
        skipped_unevidenced=skipped_unevidenced,
        superseded=superseded,
        by_type=by_type,
    )


def _supersede_resolved(conn: Any, detected_keys: set[tuple[str, str, str]], *, as_of: date) -> int:
    """Append a ``superseded`` state row for each open contradiction no longer detected.

    Lifecycle-aware + append-only (SIG-RECON-021/055): a contradiction the resolver no
    longer detects over the current spine (later evidence resolved the disagreement) is
    NOT deleted — the open row stays visible in history and a NEW ``superseded`` row is
    appended via the model lifecycle (:meth:`reconcile.model.Contradiction.supersede`).
    Idempotent: a triple that already carries a superseded row is skipped, so re-runs
    add +0.
    """
    already = _superseded_keys(conn)
    at = datetime(as_of.year, as_of.month, as_of.day, tzinfo=UTC)
    superseded = 0
    for subj, pred, ctype, claim_ids in _open_contradictions(conn):
        key = (subj, pred, ctype)
        if key in detected_keys or key in already:
            continue
        prior = Contradiction(
            contradiction_type=ctype,
            subject_id=subj,
            predicate_id=pred,
            claim_values=(),
            note="superseded by later evidence",
            status="open",
            claim_ids=tuple(claim_ids),
        )
        settled = prior.supersede(at=at)
        row = contradiction_row(settled)
        if row is None:
            continue
        row["resolution_note"] = (
            "no longer detected by the resolver over the current spine — superseded by "
            "later evidence (append-only; the open finding is retained in history, "
            "§3.1/SIG-RECON-021)."
        )
        row["resolved_by"] = "auto"
        row["input_digest"] = contradiction_input_digest(row)
        if _insert_contradiction(conn, row):
            superseded += 1
            already.add(key)
    return superseded


def read_materialized_contradictions(conn: Any, *, role: str | None = None) -> list[dict[str, Any]]:
    """Read the materialized contradictions (the P28.5 surface seam, `_persisted_contradictions`).

    The real, live contradiction dataset the P28.5 surface refresh consumes to render
    contradictions with their evidence on both sides — mirrors the
    ``api.store_pg._persisted_contradictions`` projection exactly (contradiction_id,
    subject_id, predicate_id, contradiction_type, status, claim_ids). Read-only;
    deterministically ordered; every contradiction — open and settled — is included,
    nothing suppressed (§3.1/SIG-RECON-055).
    """
    if role:
        conn.execute(f"SET ROLE {role}")
    rows = conn.execute(
        "SELECT contradiction_id::text, subject_id::text, predicate_id, contradiction_type, "
        "       status, severity, claim_ids "
        "  FROM contradiction "
        " WHERE input_digest IS NOT NULL "
        " ORDER BY subject_id, predicate_id, contradiction_type, status, contradiction_id"
    ).fetchall()
    return [
        {
            "contradiction_id": r[0],
            "subject_id": r[1],
            "predicate_id": r[2],
            "contradiction_type": r[3],
            "status": r[4],
            "severity": r[5],
            "claim_ids": [str(x) for x in (r[6] or ())],
        }
        for r in rows
    ]


def materialize_contradictions_from_dsn(dsn: str, **kwargs: Any) -> ContradictionMaterializeSummary:
    """Open an autocommit connection from ``dsn`` and materialize contradictions (CLI)."""
    import psycopg  # available via the sig-db dependency (driver stays in `db`)

    conn = psycopg.connect(dsn, autocommit=True)
    try:
        return materialize_contradictions(conn, **kwargs)
    finally:
        conn.close()


# ============================================================================
# P35.26 — Materialize organisation-role edges + explicit-unknown states.
#
# The ``entity_role`` table (the ``role_edges`` sqitch change) is the stored,
# evidenced, DATED role-edge record: who operates / owns / vendors / funds /
# accesses the subject, WHEN the evidence says the role held (``valid_period``
# + closed bound-kind vocabulary), and which claim supersedes which (the
# ``supersedes`` / ``superseded_by_claim`` succession chain — SIG-EPIS-029).
#
# The honest-posture rules this materializer encodes:
#
# * **Roles come only from evidence (SIG-TRUST-003).** A ``entity_role`` row is
#   written only from a live tier-0 claim carrying ``object_entity`` under a
#   predicate the canonical taxonomy maps to an operational role
#   (``db.organization_roles.ROLE_OF_PREDICATE`` ∩ ``ENTITY_REF_ROLES``).
#   Provenance-role claims (``camera_registry_publisher``, ``published_by``) are
#   literal — they NEVER mint a role edge, so a publisher can never read as an
#   operator.
# * **Operator absence is a first-class state (SIG-ONTO-028).** An
#   ``operator_absent`` claim materializes an ``operator_unknown`` row —
#   ``actor_id`` NULL, evidenced by the absence claim — not a fabricated actor
#   and not missing data. The unknown state competes for the operator SLOT: a
#   later operator claim supersedes it, a later absence claim supersedes an
#   operator edge (same succession machinery).
# * **Dated edges, never the epoch placeholder (SIG-ONTO-030/032).** An edge's
#   ``valid_period`` lower is the earliest evidenced bound across its claims
#   (``valid_period`` lower, else ``observed_at``); a claim with no evidenced
#   date produces an UNBOUNDED period + ``valid_from_kind='undated'`` — the
#   explicit undated marker, never ``1970-01-01`` (the CHECK rejects an
#   epoch-zero write regardless).
# * **Supersession is a recorded edge succession (SIG-EPIS-029).** Two drivers:
#   (a) WITHIN one claim lineage (``claim_lineage.source_id``, P35.25 — a claim
#   with no lineage row is its own lineage): successive DISTINCT states of the
#   same (subject, slot) are the source's successive statements — the earlier
#   episode's edge closes at the later claim's date and
#   ``superseded_by_claim`` names it; (b) explicit corrections: a claim's
#   ``revises_claim``/``retraction_of`` closes the revised claim's state at the
#   corrector's date. Cross-LINEAGE disagreement stays concurrent — both edges
#   live, never silently reconciled (§3.1). Open (current) episodes of the same
#   state merge their evidence across lineages into one corroborated edge;
#   closed episodes stay per-lineage rows (distinct ended spans are distinct
#   facts).
# * **Append-only + idempotent (+0).** Only ``INSERT`` plus the
#   SECURITY-DEFINER ``close_superseded_entity_roles`` sys_period close (the
#   sanctioned temporal mutation — the caller keeps INSERT-only posture). A
#   live row whose ``input_digest`` no longer matches closes as a superseded
#   version; a re-run over unchanged claims is +0.
# ============================================================================

#: Predicates whose entity_ref claims materialize role edges — the operational
#: roles only (provenance roles are literal provenance, never edges).
_ROLE_EDGE_PREDICATES: tuple[str, ...] = tuple(
    sorted(p for p, r in ROLE_OF_PREDICATE.items() if r in ENTITY_REF_ROLES)
)
_ABSENCE_PREDICATES: tuple[str, ...] = tuple(sorted(ABSENCE_PREDICATES))


@dataclass(frozen=True)
class RoleMaterializeSummary:
    """The outcome of one role-edge materialization pass — every slot accounted for."""

    considered_claims: int = 0
    subjects: int = 0
    slots: int = 0
    inserted: int = 0
    skipped_existing: int = 0
    #: Live rows sys_period-closed as superseded versions (belief succession)
    #: or as states whose evidence is gone.
    superseded: int = 0
    closed_stale: int = 0
    #: ``operator_unknown`` marker rows written this pass.
    unknown_states: int = 0
    dry_run: bool = False
    by_role: dict[str, int] = field(default_factory=dict)

    @property
    def written(self) -> int:
        return self.inserted

    def as_dict(self) -> dict[str, Any]:
        return {
            "considered_claims": self.considered_claims,
            "subjects": self.subjects,
            "slots": self.slots,
            "inserted": self.inserted,
            "skipped_existing": self.skipped_existing,
            "superseded": self.superseded,
            "closed_stale": self.closed_stale,
            "unknown_states": self.unknown_states,
            "dry_run": self.dry_run,
            "by_role": dict(sorted(self.by_role.items())),
        }


@dataclass(frozen=True)
class _RoleClaim:
    """One live tier-0 claim bearing on a subject's role state."""

    claim_id: str
    subject_id: str
    slot: str  # the competition slot ('operator', 'vendor', …)
    state: tuple[str, str | None]  # ('actor', object_entity) | ('unknown', None)
    role: str  # the entity_role.role value this claim evidences
    order_dt: datetime  # ordering instant: valid_lower | observed_at | sys_lower
    evid_dt: datetime | None  # evidenced bound date (valid_lower | observed_at), never sys
    valid_upper: datetime | None  # evidenced upper bound, if the claim carries one
    observed_at: datetime | None
    asserted_by: str | None
    revises_claim: str | None
    retraction_of: str | None
    lineage: str  # claim_lineage.source_id; a claim with no row is its own lineage


@dataclass
class _RoleEpisode:
    """A contiguous run of one state inside one claim lineage."""

    state: tuple[str, str | None]
    role: str
    lineage: str
    claims: list[_RoleClaim]
    close_dt: datetime | None = None
    close_kind: str = "exact"
    close_claim: str | None = None


def _read_role_claims(
    conn: Any,
    *,
    jurisdiction: str | None = None,
    subject: str | None = None,
    slot: str | None = None,
    after_subject: str | None = None,
    limit: int | None = None,
) -> tuple[dict[tuple[str, str], list[_RoleClaim]], int]:
    """Read the role-bearing claims, grouped by ``(subject_id, slot)``."""
    where = [
        "c.sensitivity_tier = 0",
        "upper_inf(c.sys_period)",
        "("
        "  (c.object_entity IS NOT NULL AND c.predicate_id = ANY(%s::text[]))"
        "  OR (c.value_bool IS TRUE AND c.predicate_id = ANY(%s::text[]))"
        ")",
    ]
    params: list[Any] = [_role_predicates_for_slot(slot), list(_ABSENCE_PREDICATES)]
    if subject:
        where.append("c.subject_id = %s")
        params.append(subject)
    if jurisdiction:
        where.append(
            "c.subject_id IN (SELECT entity_id FROM entity_identifier WHERE value ILIKE %s)"
        )
        params.append(f"%{jurisdiction}%")
    if after_subject:
        # subject_id is text; uuid-shaped subjects order identically under a
        # plain text comparison — never cast the column (a non-uuid subject
        # would abort the whole scan).
        where.append("c.subject_id > %s")
        params.append(after_subject)

    # claim_lineage is additive (P35.25); probe like read_claim_groups — a
    # spine without it resolves every claim to its own lineage.
    probe = conn.execute("SELECT to_regclass('public.claim_lineage')").fetchone()
    lineage_join = (
        "  LEFT JOIN claim_lineage cl ON cl.claim_id = c.claim_id " if probe and probe[0] else " "
    )
    lineage_col = "cl.source_id" if probe and probe[0] else "NULL"

    rows = conn.execute(
        "SELECT c.claim_id::text, c.subject_id::text, c.predicate_id, c.object_entity::text,"
        "       lower(c.valid_period), upper(c.valid_period),"
        "       c.observed_at, lower(c.sys_period),"
        "       c.asserted_by::text, c.revises_claim::text, c.retraction_of::text,"
        f"      {lineage_col}"
        "  FROM claim c "
        + lineage_join
        + " WHERE "
        + " AND ".join(where)
        + " ORDER BY c.subject_id, c.claim_id"
        + (" LIMIT %s" if limit else ""),
        tuple(params + ([limit] if limit else [])),
    ).fetchall()

    groups: dict[tuple[str, str], list[_RoleClaim]] = {}
    considered = 0
    for r in rows:
        considered += 1
        (
            claim_id,
            subj,
            pred,
            obj,
            v_lower,
            v_upper,
            observed,
            sys_lower,
            asserted,
            revises,
            retracts,
            source_id,
        ) = r
        pred = str(pred)
        if pred in ABSENCE_PREDICATES:
            slot_name = str(ABSENCE_PREDICATES[pred])
            state: tuple[str, str | None] = ("unknown", None)
            role_name = UNKNOWN_STATE_FOR_ROLE[slot_name]
        else:
            role_enum = ROLE_OF_PREDICATE.get(pred)
            if role_enum is None or role_enum not in ENTITY_REF_ROLES or obj is None:
                continue  # provenance roles / unmapped predicates never edge
            role_name = str(role_enum)
            slot_name = role_slot(role_name)
            state = ("actor", str(obj))
        if slot is not None and slot_name != slot:
            continue
        evid = v_lower or observed
        order = evid or sys_lower
        if not _is_uuid(str(subj)):
            # entity_role.entity_id is an entity FK — a non-uuid subject
            # (e.g. an `osm:node/…` literal subject) can never bind a role
            # edge; its claim stays evidence, the edge simply does not exist.
            continue
        groups.setdefault((str(subj), slot_name), []).append(
            _RoleClaim(
                claim_id=str(claim_id),
                subject_id=str(subj),
                slot=slot_name,
                state=state,
                role=role_name,
                order_dt=order,
                evid_dt=evid,
                valid_upper=v_upper,
                observed_at=observed,
                asserted_by=None if asserted is None else str(asserted),
                revises_claim=None if revises is None else str(revises),
                retraction_of=None if retracts is None else str(retracts),
                lineage=str(source_id) if source_id else f"claim:{claim_id}",
            )
        )
    return groups, considered


def _role_predicates_for_slot(slot: str | None) -> list[str]:
    """The role predicates to read — all, or just those mapping to ``slot``."""
    if slot is None:
        return list(_ROLE_EDGE_PREDICATES)
    return [p for p in _ROLE_EDGE_PREDICATES if role_slot(str(ROLE_OF_PREDICATE[p])) == slot]


def _episodes(claims: list[_RoleClaim]) -> list[_RoleEpisode]:
    """Succession episodes for one (subject, slot): within-lineage state runs,
    closed by later same-lineage states or explicit revises/retraction claims.
    """
    by_lineage: dict[str, list[_RoleClaim]] = {}
    for c in claims:
        by_lineage.setdefault(c.lineage, []).append(c)

    episodes: list[_RoleEpisode] = []
    for lineage, lclaims in sorted(by_lineage.items()):
        lclaims.sort(key=lambda c: (c.order_dt, c.claim_id))
        lineage_eps: list[_RoleEpisode] = []
        for c in lclaims:
            if lineage_eps and lineage_eps[-1].state == c.state:
                lineage_eps[-1].claims.append(c)
            else:
                lineage_eps.append(
                    _RoleEpisode(state=c.state, role=c.role, lineage=lineage, claims=[c])
                )
        # Within-lineage succession: a later DISTINCT state closes the earlier
        # episode at the later claim's date — the source's own statement moved
        # on (recorded, never silent — superseded_by_claim names it).
        for prior, nxt in zip(lineage_eps, lineage_eps[1:], strict=False):
            first = nxt.claims[0]
            prior.close_dt = first.evid_dt or first.order_dt
            prior.close_kind = "exact" if first.evid_dt else "before"
            prior.close_claim = first.claim_id
        episodes.extend(lineage_eps)

    # Explicit corrections: a claim's revises_claim/retraction_of closes the
    # state its target evidenced — cross-lineage, at the corrector's date.
    targets: dict[str, _RoleEpisode] = {}
    for ep in episodes:
        for c in ep.claims:
            targets[c.claim_id] = ep
    for c in claims:
        for target in (c.revises_claim, c.retraction_of):
            tgt_ep = targets.get(target) if target else None
            if tgt_ep is None:
                continue
            close_dt = c.evid_dt or c.order_dt
            if close_dt <= min(cc.order_dt for cc in tgt_ep.claims):
                continue  # a "correction" that pre-dates the claim corrects nothing
            if tgt_ep.close_dt is None or close_dt < tgt_ep.close_dt:
                tgt_ep.close_dt = close_dt
                tgt_ep.close_kind = "exact" if c.evid_dt else "before"
                tgt_ep.close_claim = c.claim_id
    return episodes


def _role_edge_input_digest(row: dict[str, Any]) -> str:
    """sha256 over a role edge's reproducible content — the +0 idempotency key."""
    stable = {
        "entity_id": row["entity_id"],
        "actor_id": row["actor_id"],
        "role": row["role"],
        "valid_lower": row["valid_lower"],
        "valid_upper": row["valid_upper"],
        "valid_from_kind": row["valid_from_kind"],
        "valid_to_kind": row["valid_to_kind"],
        "observed_at": row["observed_at"],
        "asserted_by": row["asserted_by"],
        "superseded_by_claim": row["superseded_by_claim"],
        "evidence_claims": sorted(row["evidence_claims"]),
    }
    payload = json.dumps(stable, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _episode_row(
    subject: str,
    slot: str,
    state: tuple[str, str | None],
    claims: list[_RoleClaim],
    *,
    close_dt: datetime | None,
    close_kind: str,
    close_claim: str | None,
) -> dict[str, Any]:
    """Map one episode (or one merged open-episode group) onto an entity_role row."""
    role = slot if state[0] == "actor" else UNKNOWN_STATE_FOR_ROLE[slot]
    actor = state[1] if state[0] == "actor" else None
    evid_lowers = [c.evid_dt for c in claims if c.evid_dt is not None]
    valid_lower = min(evid_lowers) if evid_lowers else None
    bounded_uppers = [c.valid_upper for c in claims if c.valid_upper is not None]
    evid_upper = max(bounded_uppers) if bounded_uppers else None

    if close_dt is not None and (evid_upper is None or close_dt < evid_upper):
        valid_upper, to_kind = close_dt, close_kind
    elif evid_upper is not None:
        valid_upper, to_kind = evid_upper, "exact"
    else:
        valid_upper, to_kind = None, "ongoing"

    observed = max((c.observed_at for c in claims if c.observed_at), default=None)
    asserted_by = min((c.asserted_by for c in claims if c.asserted_by), default=None)
    eclaims = sorted(c.claim_id for c in claims)
    row: dict[str, Any] = {
        "entity_id": subject,
        "actor_id": actor,
        "role": role,
        "valid_lower": valid_lower,
        "valid_upper": valid_upper,
        "valid_from_kind": "exact" if valid_lower else "undated",
        "valid_to_kind": to_kind,
        "observed_at": observed,
        "asserted_by": asserted_by,
        "evidence_claim": eclaims[0],
        "evidence_claims": eclaims,
        "superseded_by_claim": close_claim,
    }
    row["input_digest"] = _role_edge_input_digest(row)
    return row


def _desired_role_rows(subject: str, slot: str, claims: list[_RoleClaim]) -> list[dict[str, Any]]:
    """The desired entity_role rows for one (subject, slot) — the materializer's
    derived truth. Each row carries ``_chain_pred`` (the row object its state
    succeeds, when the succession is a timeline move, not a re-version)."""
    episodes = _episodes(claims)

    # Open same-state episodes merge ACROSS lineages into one corroborated
    # edge; closed episodes stay per-lineage (distinct ended spans).
    open_groups: dict[tuple[str, str | None], list[_RoleEpisode]] = {}
    closed_eps: list[_RoleEpisode] = []
    for ep in episodes:
        if ep.close_dt is None:
            open_groups.setdefault(ep.state, []).append(ep)
        else:
            closed_eps.append(ep)

    rows: list[dict[str, Any]] = []
    row_of_episode: dict[int, dict[str, Any]] = {}

    def _pred_of(ep: _RoleEpisode, lineage_eps: list[_RoleEpisode]) -> dict[str, Any] | None:
        idx = lineage_eps.index(ep)
        if idx == 0:
            return None
        return row_of_episode.get(id(lineage_eps[idx - 1]))

    # Index episodes back to their lineage chains for predecessor wiring.
    lineage_chains: dict[str, list[_RoleEpisode]] = {}
    for ep in episodes:
        lineage_chains.setdefault(ep.lineage, []).append(ep)

    # Closed episodes first. Ordering: each lineage's episodes in chain order
    # (a predecessor ALWAYS precedes its successor — a flat time sort could tie
    # on equal order_dt and emit a successor before the row it supersedes);
    # lineages themselves sorted by name keeps the whole pass deterministic.
    del closed_eps
    for lineage in sorted(lineage_chains):
        for ep in lineage_chains[lineage]:
            if ep.close_dt is None:
                continue
            row = _episode_row(
                subject,
                slot,
                ep.state,
                ep.claims,
                close_dt=ep.close_dt,
                close_kind=ep.close_kind,
                close_claim=ep.close_claim,
            )
            pred = _pred_of(ep, lineage_chains[lineage])
            if pred is not None:
                row["_chain_pred"] = pred
            row_of_episode[id(ep)] = row
            rows.append(row)

    # Merged open groups — the current corroborated state rows.
    for state, eps in sorted(open_groups.items(), key=lambda kv: (kv[0][0], kv[0][1] or "")):
        merged_claims = sorted((c for ep in eps for c in ep.claims), key=lambda c: c.claim_id)
        row = _episode_row(
            subject, slot, state, merged_claims, close_dt=None, close_kind="exact", close_claim=None
        )
        # The timeline predecessor: the member lineages' immediately-prior
        # closed episodes; the one with the latest close wins (deterministic).
        preds: list[tuple[Any, dict[str, Any]]] = []
        for ep in eps:
            chain = lineage_chains[ep.lineage]
            idx = chain.index(ep)
            if idx == 0:
                continue
            prev = chain[idx - 1]
            if prev.close_dt is not None and id(prev) in row_of_episode:
                preds.append((prev.close_dt, row_of_episode[id(prev)]))
        if preds:
            preds.sort(key=lambda t: (t[0], t[1]["input_digest"]))
            row["_chain_pred"] = preds[-1][1]
        rows.append(row)

    return rows


def _live_role_rows(
    conn: Any, *, subjects: list[str]
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Live entity_role rows for the read subjects, keyed by ``(entity_id, slot)``."""
    if not subjects:
        return {}
    rows = conn.execute(
        "SELECT entity_role_id::text, entity_id::text, actor_id::text, role,"
        "       input_digest, superseded_by_claim::text, lower(sys_period)"
        "  FROM entity_role"
        " WHERE entity_id = ANY(%s::uuid[]) AND upper_inf(sys_period)"
        " ORDER BY entity_id, role, sys_period",
        (subjects,),
    ).fetchall()
    out: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for rid, ent, actor, role, digest, close_claim, sys_lower in rows:
        out.setdefault((str(ent), role_slot(role)), []).append(
            {
                "entity_role_id": str(rid),
                "entity_id": str(ent),
                "actor_id": None if actor is None else str(actor),
                "role": str(role),
                "input_digest": digest,
                "superseded_by_claim": None if close_claim is None else str(close_claim),
                "sys_lower": sys_lower,
            }
        )
    return out


def _insert_entity_role(conn: Any, row: dict[str, Any]) -> tuple[str | None, bool]:
    """INSERT one entity_role row, idempotent on ``input_digest``.

    Returns ``(entity_role_id, inserted)`` — ``inserted`` True only when this
    call wrote the row. On a digest conflict the LIVE row's id is returned with
    ``inserted=False`` so chain successors can still link; a digest that exists
    only on a closed row returns ``(None, False)`` — history is not revived.
    """
    result = conn.execute(
        "INSERT INTO entity_role"
        "(entity_id, actor_id, role, valid_period, valid_from_kind, valid_to_kind,"
        " observed_at, asserted_by, evidence_claim, superseded_by_claim, supersedes,"
        " input_digest)"
        " VALUES (%s, %s, %s, tstzrange(%s::timestamptz, %s::timestamptz, '[)'),"
        " %s, %s, %s::timestamptz, %s, %s, %s, %s, %s)"
        " ON CONFLICT (input_digest) WHERE input_digest IS NOT NULL"
        " DO NOTHING RETURNING entity_role_id",
        (
            row["entity_id"],
            row["actor_id"],
            row["role"],
            row["valid_lower"],
            row["valid_upper"],
            row["valid_from_kind"],
            row["valid_to_kind"],
            row["observed_at"],
            row["asserted_by"],
            row["evidence_claim"],
            row["superseded_by_claim"],
            row.get("supersedes"),
            row["input_digest"],
        ),
    ).fetchone()
    if result is not None:
        return str(result[0]), True
    existing = conn.execute(
        "SELECT entity_role_id::text FROM entity_role"
        " WHERE input_digest = %s AND upper_inf(sys_period)",
        (row["input_digest"],),
    ).fetchone()
    return (None if existing is None else str(existing[0])), False


def _close_entity_role_ids(conn: Any, ids: list[str]) -> int:
    """Close the sys_period of live entity_role rows (the sanctioned mutation)."""
    if not ids:
        return 0
    rows = conn.execute(
        "SELECT entity_role_id::text FROM close_superseded_entity_roles(%s::uuid[])",
        (ids,),
    ).fetchall()
    return len(rows)


def materialize_role_edges(
    conn: Any,
    *,
    jurisdiction: str | None = None,
    subject: str | None = None,
    slot: str | None = None,
    after_subject: str | None = None,
    limit: int | None = None,
    role: str | None = None,
    dry_run: bool = False,
) -> RoleMaterializeSummary:
    """Materialize organisation-role edges + explicit-unknown states (P35.26).

    Reads role-bearing claims, builds the per-(subject, slot) succession
    model, and writes append-only, idempotent ``entity_role`` rows —
    ``dry_run=True`` computes the identical summary while writing nothing (the
    queued hosted leg's review posture). A re-run over unchanged claims is +0.
    """
    if role:
        conn.execute(f"SET ROLE {role}")

    groups, considered = _read_role_claims(
        conn,
        jurisdiction=jurisdiction,
        subject=subject,
        slot=slot,
        after_subject=after_subject,
        limit=limit,
    )
    subjects = sorted({s for s, _s in groups})
    live = _live_role_rows(conn, subjects=subjects)

    inserted = skipped_existing = superseded = closed_stale = unknown_states = 0
    by_role: dict[str, int] = {}

    for (subj, slot_name), claims in sorted(groups.items()):
        desired = _desired_role_rows(subj, slot_name, claims)
        live_rows = live.get((subj, slot_name), [])
        live_by_digest = {r["input_digest"]: r for r in live_rows if r["input_digest"]}

        # Belief supersession: a live row matching a desired row's logical edge
        # (same entity/actor/role/close-claim) with a different digest is its
        # superseded version — close it and the new row links to it.
        logical_of_live = {
            (
                r["entity_id"],
                r["actor_id"],
                r["role"],
                r["superseded_by_claim"],
            ): r
            for r in live_rows
        }
        close_ids: list[str] = []
        matched_live: set[str] = set()
        for row in desired:
            key = (
                row["entity_id"],
                row["actor_id"],
                row["role"],
                row["superseded_by_claim"],
            )
            live_match = logical_of_live.get(key)
            if (
                live_match is not None
                and live_match["input_digest"] != row["input_digest"]
                and live_match["entity_role_id"] not in matched_live
            ):
                matched_live.add(live_match["entity_role_id"])
                close_ids.append(live_match["entity_role_id"])
                row["supersedes"] = live_match["entity_role_id"]

        desired_digests = {r["input_digest"] for r in desired}
        for r in live_rows:
            if r["input_digest"] in desired_digests or r["entity_role_id"] in matched_live:
                continue
            close_ids.append(r["entity_role_id"])  # stale — no evidence left

        if not dry_run and close_ids:
            n = _close_entity_role_ids(conn, close_ids)
            superseded += len(matched_live)
            closed_stale += n - len(matched_live)
        elif dry_run:
            superseded += len(matched_live)
            closed_stale += len(close_ids) - len(matched_live)

        # Wire timeline succession: a desired row's `_chain_pred` links to the
        # row (live or just-inserted) its state succeeds.
        id_by_row: dict[int, str] = {
            id(r): live_by_digest[r["input_digest"]]["entity_role_id"]
            for r in desired
            if r["input_digest"] in live_by_digest
        }
        for row in desired:
            pred = row.get("_chain_pred")
            if pred is not None and "supersedes" not in row:
                pred_id = id_by_row.get(id(pred))
                if pred_id is not None:
                    row["supersedes"] = pred_id
            if dry_run:
                if row["input_digest"] in live_by_digest:
                    skipped_existing += 1
                else:
                    inserted += 1
                continue
            new_id, did_insert = _insert_entity_role(conn, row)
            if new_id is None:
                # A closed row already carries this exact content — history is
                # not revived; the superseding row stands.
                skipped_existing += 1
                continue
            id_by_row[id(row)] = new_id
            if did_insert:
                inserted += 1
                by_role[row["role"]] = by_role.get(row["role"], 0) + 1
                if row["actor_id"] is None:
                    unknown_states += 1
            else:
                skipped_existing += 1

    return RoleMaterializeSummary(
        considered_claims=considered,
        subjects=len(subjects),
        slots=len(groups),
        inserted=inserted,
        skipped_existing=skipped_existing,
        superseded=superseded,
        closed_stale=closed_stale,
        unknown_states=unknown_states,
        dry_run=dry_run,
        by_role=by_role,
    )


def materialize_role_edges_from_dsn(dsn: str, **kwargs: Any) -> RoleMaterializeSummary:
    """Open an autocommit connection from ``dsn`` and materialize role edges (CLI)."""
    import psycopg  # available via the sig-db dependency (driver stays in `db`)

    conn = psycopg.connect(dsn, autocommit=True)
    try:
        return materialize_role_edges(conn, **kwargs)
    finally:
        conn.close()


def read_materialized_role_edges(conn: Any, *, role: str | None = None) -> list[dict[str, Any]]:
    """Read the live materialized ``entity_role`` rows (the current role-edge set).

    Only ``upper_inf(sys_period)`` rows — a superseded version stays in the
    table as recorded succession history (queryable through ``supersedes``)
    but is not part of the current role graph.
    """
    if role:
        conn.execute(f"SET ROLE {role}")
    rows = conn.execute(
        "SELECT entity_role_id::text, entity_id::text, actor_id::text, role,"
        "       lower(valid_period), upper(valid_period), valid_from_kind, valid_to_kind,"
        "       observed_at, asserted_by::text, evidence_claim::text,"
        "       supersedes::text, superseded_by_claim::text"
        "  FROM entity_role"
        " WHERE input_digest IS NOT NULL AND upper_inf(sys_period)"
        " ORDER BY entity_id, role, actor_id NULLS LAST, entity_role_id"
    ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "entity_role_id": r[0],
                "entity_id": r[1],
                "actor_id": r[2],
                "role": r[3],
                "valid_from": r[4].isoformat() if isinstance(r[4], (datetime, date)) else None,
                "valid_to": r[5].isoformat() if isinstance(r[5], (datetime, date)) else None,
                "valid_from_kind": r[6],
                "valid_to_kind": r[7],
                "observed_at": r[8].isoformat() if isinstance(r[8], (datetime, date)) else None,
                "asserted_by": r[9],
                "evidence_claim": r[10],
                "supersedes": r[11],
                "superseded_by_claim": r[12],
            }
        )
    return out


def operator_state(conn: Any, entity_id: str, *, role: str | None = None) -> dict[str, Any]:
    """A subject's explicit operator state (SIG-ONTO-028).

    ``{"state": "operator", "actors": [...]}`` when live operator edges exist;
    ``{"state": "operator_unknown", ...}`` when the explicit-unknown marker row
    is live; ``{"state": "not_asserted"}`` when the slot carries neither — the
    distinction between *evidenced-absent* and *never-asked* stays honest.
    """
    if role:
        conn.execute(f"SET ROLE {role}")
    rows = conn.execute(
        "SELECT actor_id::text, role, evidence_claim::text FROM entity_role"
        " WHERE entity_id = %s AND upper_inf(sys_period)"
        "   AND role IN ('operator', 'operator_unknown')"
        " ORDER BY role, actor_id NULLS LAST",
        (entity_id,),
    ).fetchall()
    actors = sorted({str(r[0]) for r in rows if r[0] is not None and r[1] == "operator"})
    unknown = [str(r[2]) for r in rows if r[1] == "operator_unknown"]
    if actors:
        return {"entity_id": str(entity_id), "state": "operator", "actors": actors}
    if unknown:
        return {
            "entity_id": str(entity_id),
            "state": "operator_unknown",
            "actors": [],
            "evidence_claim": unknown[0],
        }
    return {"entity_id": str(entity_id), "state": "not_asserted", "actors": []}
