# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The append-only subject re-key run (P35.24 / ADR-212; R11-L3-CP2, CONF-03b).

A ``sig.connector.subject`` key whose pinned fields were not unique upstream
merged multiple real subjects into one (F-518: 5,278 collided camera keys at
L2-M07; F-506: cross-tenant Legistar contracts + cross-state Atlas/EFF
agencies). Stored keys are append-only — they are never rewritten in place.
This run is the correction machinery:

- ``collision_scan`` re-derives the collided set from the LIVE spine via each
  pin's ``distinguish`` selectors (the 5,278 figure is a planning number —
  the real count is measured at run time and any drift is a finding);
- ``plan_subject`` groups the key's current claims into per-upstream-record
  evidence bundles (capture + extraction + locator) and clusters them by the
  pin's discriminator (camera: the bundle's coordinate pair; scoped families:
  the evidenced scope value in ``raw_context``);
- ``apply_subject`` closes each moved claim (the only permitted UPDATE —
  ``sys_period`` end), appends the corrected claim under its constituent
  subject with ``revises_claim`` + ``correction_reason`` + an identity-class
  ``content_digest``, re-binds the same evidence rows, and records one
  ``subject_rekey_decision`` per (old key, constituent) — INSERT-only,
  ``ON CONFLICT DO NOTHING``, +0 on rerun. One transaction per subject key,
  so an interrupted run resumes where it stopped.

Claims whose bundle carries no usable discriminator stay on the legacy key
and are reported ``unplaced`` — a constituent is never guessed.

The ``live_verification=false`` half lands the machinery only: the hosted
apply run + the post-count verification leg are queued under OM-19/OM-20.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .subject_keys import ParsedSubjectKey

from .identity_guard import SUBJECT_SCHEME, resolve_identities
from .subject_keys import (
    parse_subject_key,
    pins,
    registry_version,
    split_subject_key,
)
from .subject_types import entity_type_for_subject

#: The writer identity stamped on decisions + correction claims.
DECIDED_BY = "subject-rekey/1"
#: The written basis every correction row + decision carries.
DECISION_BASIS = (
    "P35.24 R11-L3-CP2 (ADR-212): pinned subject-key grammar — collided "
    "sig.connector.subject keys split into evidence-derived constituents"
)
#: claim.correction_reason stamped on every appended correction claim.
CORRECTION_REASON = "subject_rekey_constituent"
#: The ingest_run the corrections attach to (one per apply invocation).
RUN_CONNECTOR = "subject-rekey"
RUN_CONNECTOR_VERSION = "1.0.0"


@dataclass(frozen=True)
class Collision:
    """One pinned-family subject key holding claims from >1 real subject."""

    subject_id: str
    value: str
    pin_id: str
    selector: str
    distinct_values: int


@dataclass
class ClaimMove:
    claim_id: str
    new_value: str
    discriminator: str


@dataclass
class SubjectPlan:
    """The split plan for one collided subject key."""

    value: str
    entity_id: str
    pin_id: str
    parsed: ParsedSubjectKey | None
    #: new constituent value -> claims to move
    moves: list[ClaimMove] = field(default_factory=list)
    #: claims that stay on the legacy key (no usable discriminator)
    unplaced: list[str] = field(default_factory=list)
    already_decided: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _ClaimRow:
    claim_id: str
    predicate_id: str
    value_text: str | None
    value_num: Any
    raw_context: Any
    capture_id: str | None
    locator: Any


def _collision_selector_sql(selector: str) -> tuple[str, str, str]:
    """(join filter, distinct expression, non-null guard) for a distinguish
    selector — ``predicate:<id>`` or ``context:<key>``."""
    if selector.startswith("predicate:"):
        return (
            "AND c.predicate_id = %(pred)s",
            "coalesce(c.value_text, c.value_num::text)",
            "",
        )
    if selector.startswith("context:"):
        return ("", "c.raw_context->>%(ctx_key)s", "AND c.raw_context->>%(ctx_key)s IS NOT NULL")
    raise ValueError(f"unknown distinguish selector {selector!r}")


def collision_scan(conn: Any) -> list[Collision]:
    """Re-derive every pinned-family collided subject from the live spine.

    A key is collided when ANY of its pin's ``distinguish`` selectors shows
    >1 distinct current value — the live count, never the planning figure.
    """
    out: list[Collision] = []
    for pin in pins():
        for selector in pin.distinguish:
            filter_sql, distinct_expr, guard = _collision_selector_sql(selector)
            params: dict[str, Any] = {"like": f"{pin.family}%"}
            if selector.startswith("predicate:"):
                params["pred"] = selector.split(":", 1)[1]
            else:
                params["ctx_key"] = selector.split(":", 1)[1]
            rows = conn.execute(
                "SELECT k.value, k.entity_id::text AS entity_id,"
                f" count(DISTINCT {distinct_expr}) AS distinct_values"
                "  FROM entity_identity_key k"
                "  JOIN claim c ON c.subject_id = k.entity_id"
                "   AND upper_inf(c.sys_period)"
                f"  {filter_sql} {guard}"
                " WHERE k.scheme = %(scheme)s AND k.value LIKE %(like)s"
                " GROUP BY k.value, k.entity_id"
                " HAVING count(DISTINCT " + distinct_expr + ") > 1"
                " ORDER BY k.value",
                {**params, "scheme": SUBJECT_SCHEME},
            ).fetchall()
            for r in rows:
                out.append(
                    Collision(
                        subject_id=str(r["entity_id"]),
                        value=str(r["value"]),
                        pin_id=pin.pin_id,
                        selector=selector,
                        distinct_values=int(r["distinct_values"]),
                    )
                )
    # Same key may collide on two selectors — dedupe by subject value.
    dedup: dict[str, Collision] = {}
    for c in out:
        dedup.setdefault(c.value, c)
    return [dedup[k] for k in sorted(dedup)]


def _load_claims(conn: Any, entity_id: str) -> list[_ClaimRow]:
    rows = conn.execute(
        "SELECT c.claim_id::text, c.predicate_id, c.value_text, c.value_num,"
        "       c.raw_context, ce.capture_id::text, ce.locator"
        "  FROM claim c"
        "  LEFT JOIN claim_evidence ce ON ce.claim_id = c.claim_id"
        " WHERE c.subject_id = %s::uuid AND upper_inf(c.sys_period)"
        " ORDER BY c.claim_id, ce.capture_id",
        (entity_id,),
    ).fetchall()
    return [
        _ClaimRow(
            claim_id=str(r["claim_id"]),
            predicate_id=str(r["predicate_id"]),
            value_text=(None if r["value_text"] is None else str(r["value_text"])),
            value_num=r["value_num"],
            raw_context=r["raw_context"],
            capture_id=(None if r["capture_id"] is None else str(r["capture_id"])),
            locator=r["locator"],
        )
        for r in rows
    ]


def _context_discriminator(claims: list[_ClaimRow], ctx_key: str) -> str | None:
    """The single scope value a bundle evidences; None when absent/ambiguous."""
    values = {
        str(c.raw_context[ctx_key])
        for c in claims
        if isinstance(c.raw_context, dict) and c.raw_context.get(ctx_key) not in (None, "")
    }
    return values.pop() if len(values) == 1 else None


def _coordinate_pair(claims: list[_ClaimRow]) -> str | None:
    lat = lon = None
    for c in claims:
        if c.predicate_id == "camera_latitude" and c.value_num is not None:
            lat = str(c.value_num)
        elif c.predicate_id == "camera_longitude" and c.value_num is not None:
            lon = str(c.value_num)
    return f"{lat},{lon}" if lat is not None and lon is not None else None


def plan_subject(conn: Any, collision: Collision) -> SubjectPlan:
    """Read one collided key's current claims and group them into
    constituents by the pin's discriminator. Read-only."""
    pin = next(p for p in pins() if p.pin_id == collision.pin_id)
    parsed = parse_subject_key(collision.value)
    plan = SubjectPlan(
        value=collision.value,
        entity_id=collision.subject_id,
        pin_id=pin.pin_id,
        parsed=parsed,
    )
    if parsed is None:
        return plan
    claims = _load_claims(conn, collision.subject_id)

    # Already-decided constituents (a previous partial apply) — skip.
    decided = conn.execute(
        "SELECT DISTINCT new_value FROM subject_rekey_decision"
        " WHERE scheme = %s AND old_value = %s",
        (SUBJECT_SCHEME, collision.value),
    ).fetchall()
    plan.already_decided = [str(r["new_value"]) for r in decided]

    # Per-upstream-record bundles: same (capture, extraction-ish locator)
    # means same raw row; assertion-minted claims (no evidence row) form a
    # singleton bundle keyed by claim_id and land unplaced for coordinate
    # splitting (no coordinate evidence to bind them to a constituent).
    bundles: dict[tuple[str | None, str], list[_ClaimRow]] = {}
    for c in claims:
        locator_key = (
            json.dumps(c.locator, sort_keys=True, default=str) if c.locator is not None else ""
        )
        key = (c.capture_id, locator_key) if c.capture_id else (None, c.claim_id)
        bundles.setdefault(key, []).append(c)

    discriminator = pin.split_discriminator
    for _, bundle in sorted(bundles.items(), key=lambda item: (item[0][0] or "", item[0][1])):
        if discriminator == "coordinate_pair":
            disc = _coordinate_pair(bundle)
        elif discriminator and discriminator.startswith("context:"):
            disc = _context_discriminator(bundle, discriminator.split(":", 1)[1])
        else:
            disc = None
        if disc is None:
            plan.unplaced.extend(c.claim_id for c in bundle)
            continue
        new_value = split_subject_key(parsed, disc)
        if new_value in plan.already_decided:
            plan.unplaced.extend(c.claim_id for c in bundle)
            continue
        plan.moves.extend(
            ClaimMove(claim_id=c.claim_id, new_value=new_value, discriminator=disc) for c in bundle
        )
    return plan


def _ensure_run(conn: Any, *, mode: str) -> str:
    env = {k: v for k in ("TZ", "LC_ALL") if (v := os.environ.get(k))}
    row = conn.execute(
        "INSERT INTO ingest_run(connector_name, connector_version, code_commit,"
        " ruleset_version, vocab_version, parameters, environment, input_digests,"
        " status, finished_at) "
        "VALUES(%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::text[],'succeeded',clock_timestamp())"
        " RETURNING run_id::text",
        (
            RUN_CONNECTOR,
            RUN_CONNECTOR_VERSION,
            os.environ.get("SIG_CODE_COMMIT", "unknown"),
            registry_version(),
            registry_version(),
            json.dumps({"mode": mode, "registry_version": registry_version()}),
            json.dumps(env),
            [],
        ),
    ).fetchone()
    return str(row["run_id"])


def _insert_correction(conn: Any, claim_id: str, new_entity_id: str, run_id: str) -> str:
    """Close the old claim (sys_period end — the only permitted UPDATE) and
    append the corrected row under the constituent subject. Returns the new
    claim id. Columns are inherited verbatim; the digest is recomputed over
    the stored payload so the correction stays identity-class."""
    from evidence.claim_identity import PAYLOAD_VERSION

    from .claim_sink import bound_versions, content_digest, predicate_temporal_class

    old = conn.execute(
        "SELECT * FROM claim WHERE claim_id = %s::uuid AND upper_inf(sys_period)",
        (claim_id,),
    ).fetchone()
    if old is None:
        return ""  # already closed/decided by a prior partial apply
    closed = conn.execute(
        "UPDATE claim SET sys_period = tstzrange(lower(sys_period),"
        " clock_timestamp(), '[)') WHERE claim_id = %s::uuid"
        " AND upper_inf(sys_period)",
        (claim_id,),
    ).rowcount
    if closed != 1:
        raise RuntimeError(f"claim {claim_id} closed concurrently — reconcile, never re-close")
    cols = [
        "subject_id",
        "predicate_id",
        "object_entity",
        "object_type",
        "value_kind",
        "value_text",
        "value_num",
        "value_bool",
        "value_geom",
        "value_json",
        "unit",
        "raw_value",
        "raw_context",
        "normalization_id",
        "normalization_version",
        "valid_period",
        "valid_edtf",
        "valid_from_kind",
        "valid_to_kind",
        "observed_at",
        "observed_edtf",
        "observed_at_kind",
        "observed_unknown_reason",
        "source_reliability",
        "reliability_provisional",
        "claim_directness",
        "artifact_integrity",
        "legacy_source_tier",
        "claim_polarity",
        "rank",
        "review_status",
        "extraction_id",
        "asserted_by",
        "assertion_rationale",
        "derived_from_claim_ids",
        "ingest_run_id",
        "revises_claim",
        "correction_reason",
        "sensitivity_tier",
        "rights_id",
    ]
    payload: dict[str, Any] = {c: old[c] for c in cols}
    payload["subject_id"] = new_entity_id
    payload["ingest_run_id"] = run_id
    payload["revises_claim"] = claim_id
    payload["correction_reason"] = CORRECTION_REASON
    payload["payload_version"] = PAYLOAD_VERSION
    # Identity-class digest over the corrected payload — volatile acquisition
    # columns (run id, rights, correction linkage) never enter it; the
    # constituent subject change alone re-digests the fact so a post-split
    # re-ingest of the same record dedups onto this row. SIG-INGEST-004 /
    # P35.34: the seal carries the superseded claim's bound versions — the
    # re-keyed claim stands on the same extraction.
    bound_extractor_v, bound_normalizer_v = bound_versions(conn, claim_id)
    payload["content_digest"] = content_digest(
        payload,
        temporal_class=predicate_temporal_class(conn, str(old["predicate_id"])),
        extractor_version=bound_extractor_v,
        normalizer_version=bound_normalizer_v,
    )
    insert_cols = cols + ["payload_version", "content_digest"]
    from psycopg.types.json import Jsonb

    for json_col in ("value_json", "raw_context"):
        if isinstance(payload[json_col], dict):
            payload[json_col] = Jsonb(payload[json_col])
    placeholders = ", ".join(
        "%s::tstzrange"
        if c == "valid_period"
        else "%s::claim_rank"
        if c == "rank"
        else "%s::review_status"
        if c == "review_status"
        else "%s::uuid[]"
        if c == "derived_from_claim_ids"
        else "%s::uuid"
        if c
        in (
            "subject_id",
            "object_entity",
            "extraction_id",
            "asserted_by",
            "ingest_run_id",
            "revises_claim",
            "rights_id",
        )
        else "%s::smallint"
        if c == "sensitivity_tier"
        else "%s::jsonb"
        if c in ("value_json", "raw_context")
        else "%s"
        for c in insert_cols
    )
    row = conn.execute(
        f"INSERT INTO claim({', '.join(insert_cols)}) VALUES ({placeholders})"
        " RETURNING claim_id::text",
        tuple(payload[c] for c in insert_cols),
    ).fetchone()
    new_id = str(row["claim_id"])
    conn.execute(
        "INSERT INTO claim_evidence"
        "(claim_id, capture_id, extraction_id, role, locator, excerpt,"
        " weight_note, extraction_config_digest, extractor_version,"
        " binding_status, bound_at) "
        "SELECT %s::uuid, capture_id, extraction_id, role, locator, excerpt,"
        " weight_note, extraction_config_digest, extractor_version,"
        " binding_status, bound_at "
        "FROM claim_evidence WHERE claim_id = %s::uuid",
        (new_id, claim_id),
    )
    return new_id


def apply_subject(conn: Any, plan: SubjectPlan, run_id: str) -> dict[str, Any]:
    """Apply one subject's plan inside the caller's transaction:
    mint constituent subjects under the identity guard, close+append each
    moved claim, record one decision per constituent. INSERT-only besides
    the permitted sys_period close."""
    new_values = sorted({m.new_value for m in plan.moves})
    if not new_values:
        return {"moved": 0, "unplaced": len(plan.unplaced), "constituents": 0}
    # identity_guard reads positional rows; the run's connection is dict_row,
    # so hand it a tuple cursor sharing this transaction.
    from psycopg.rows import tuple_row

    resolved = resolve_identities(
        conn.cursor(row_factory=tuple_row),
        SUBJECT_SCHEME,
        new_values,
        entity_type=entity_type_for_subject(new_values[0]),
    )
    entity_by_value = resolved.entity_by_value
    moved = 0
    for move in plan.moves:
        new_entity = entity_by_value.get(move.new_value)
        if new_entity is None:  # pragma: no cover - guard guarantees presence
            raise RuntimeError(f"constituent {move.new_value!r} failed to resolve")
        _insert_correction(conn, move.claim_id, new_entity, run_id)
        moved += 1
    for value in new_values:
        members = [m for m in plan.moves if m.new_value == value]
        conn.execute(
            "INSERT INTO subject_rekey_decision"
            "(scheme, old_value, new_value, discriminator, claims_moved,"
            " run_id, registry_version, decided_by, basis) "
            "VALUES(%s,%s,%s,%s,%s,%s::uuid,%s,%s,%s)"
            " ON CONFLICT (scheme, old_value, new_value, registry_version) DO NOTHING",
            (
                SUBJECT_SCHEME,
                plan.value,
                value,
                members[0].discriminator if members else None,
                len(members),
                run_id,
                registry_version(),
                DECIDED_BY,
                DECISION_BASIS,
            ),
        )
    return {
        "moved": moved,
        "unplaced": len(plan.unplaced),
        "constituents": len(new_values),
    }


def run(
    dsn: str,
    *,
    apply_mode: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    """Plan (default) or apply the subject re-key.

    Returns the ``sig.subject-rekey/1`` report: the live collision count,
    per-key plans (dry-run) and per-key results (apply). Dry-run touches
    nothing; apply is per-subject transactions so an interrupted run resumes.
    """
    import psycopg
    from psycopg.rows import dict_row

    report: dict[str, Any] = {
        "artifact": "sig.subject-rekey/1",
        "mode": "apply" if apply_mode else "plan",
        "registry_version": registry_version(),
        "collided_subjects": 0,
        "subjects": [],
        "totals": {
            "claims_scanned": 0,
            "corrections_planned": 0,
            "corrections_applied": 0,
            "unplaced_claims": 0,
            "constituents": 0,
            "pre_collision_count": None,
            "post_collision_count": None,
        },
    }
    with psycopg.connect(dsn, autocommit=False, row_factory=dict_row) as conn:
        collisions = collision_scan(conn)
        report["collided_subjects"] = len(collisions)
        report["totals"]["pre_collision_count"] = len(collisions)
        if limit is not None:
            collisions = collisions[:limit]
        if not apply_mode:
            for col in collisions:
                plan = plan_subject(conn, col)
                report["totals"]["corrections_planned"] += len(plan.moves)
                report["totals"]["unplaced_claims"] += len(plan.unplaced)
                report["totals"]["claims_scanned"] += len(plan.moves) + len(plan.unplaced)
                report["subjects"].append(
                    {
                        "value": plan.value,
                        "pin": plan.pin_id,
                        "distinct": col.distinct_values,
                        "constituents": sorted({m.new_value for m in plan.moves}),
                        "moves": len(plan.moves),
                        "unplaced": len(plan.unplaced),
                        "already_decided": plan.already_decided,
                    }
                )
            conn.rollback()
            return report

        run_id = _ensure_run(conn, mode="apply")
        conn.commit()
        for col in collisions:
            with conn.transaction():
                plan = plan_subject(conn, col)
                result = apply_subject(conn, plan, run_id)
            report["totals"]["corrections_applied"] += result["moved"]
            report["totals"]["unplaced_claims"] += result["unplaced"]
            report["totals"]["constituents"] += result["constituents"]
            report["subjects"].append(
                {
                    "value": plan.value,
                    "pin": plan.pin_id,
                    "result": result,
                    "already_decided": plan.already_decided,
                }
            )
        post = collision_scan(conn)
        report["totals"]["post_collision_count"] = len(post)
        conn.rollback()
        return report
