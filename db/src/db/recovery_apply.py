# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The bounded recovery application write path (P32.22 / SIG-TRUST-008, ADR-141).

P32.6's ``recovery-plan/1`` is dry-run-only by contract: it proposes INSERT-only
actions against the append-only spine and never writes. This module is the
**application half** — the only code path that turns a proposed action into a
committed row, and it runs under the least-privilege ``sig_recovery`` role the
``recovery_apply`` sqitch change ships.

Exactly-once, by construction (the same shape the P32.16a intake bridge uses):

* every action executes inside ONE transaction — per-action advisory lock on
  the action digest, a ``recovery_application`` marker check, the canonical
  write, and the marker INSERT commit together;
* ``UNIQUE(action_digest)`` is the barrier: a crash before commit leaves
  nothing; a crash after commit reconciles to the committed receipt
  (``already_applied``) — interruption and restart can never produce a
  duplicate repair, and feeding the recorded digests back into the planner
  yields a +0 re-plan;
* a failed action rolls back whole — no half-applied repair, no orphan marker.

The three write kinds map to the append-only targets the planner names:

* ``record_disposition`` → ``publication_disposition`` through
  :func:`db.dispositions.record_disposition` — validated by the same
  ``policy.eligibility.new_disposition`` the CHECK constraint enforces. The
  proposal's placeholder authority is REPLACED by the operator authorization
  the apply was invoked under; the rationale keeps the audit's recorded basis.
* ``repair_claim`` → the §16.6 correction pair: close the old claim's
  ``sys_period`` (the only UPDATE the append-only trigger permits — a
  concurrent close makes it a no-row update, so it errors stale rather than
  double-closing), INSERT the corrected claim carrying ``revises_claim`` +
  ``correction_reason`` + the adjudicator's ``asserted_by`` entity, and re-bind
  the SAME captures to the new assertion. Repaired values come only from the
  adjudicator's ``repair_instructions`` — nothing is invented — and every
  revised string passes the Part VIII refusal screen before persistence.
* ``bind_verified_capture`` → ``INSERT claim_evidence … ON CONFLICT DO
  NOTHING``. The audit only verifies captures bound under ``establishes``, so
  a plan's bind proposal names a capture the claim already links — the
  ``(claim_id, capture_id, role)`` PK then deduplicates it. That is recorded
  honestly as ``conflict_existing`` (with the existing row's typedness in
  ``detail`` for HUMAN-H4), never fabricated as a new row and never retried
  into an UPDATE (claim_evidence is trigger-immutable).

This module holds no probe, transport, or fetch code of any kind — missing
bytes can never trigger a refetch because no path to one exists.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from policy.eligibility import (
    Disposition,
    ReasonCategory,
    TargetKind,
    new_disposition,
)

from policy import intake as pint

from .claim_sink import content_digest
from .dispositions import record_disposition
from .evidence_audit import row_to_dict
from .identity_guard import CURATOR_HANDLE_SCHEME, resolve_identities

__all__ = [
    "APPLY_VERSION",
    "RECOVERY_ROLE",
    "RECOVERY_CONNECTOR",
    "ApplyOutcome",
    "ActionResult",
    "RecoveryApplyError",
    "PgRecoveryApplier",
    "applied_digests",
    "inventory",
]

#: Contract version stamped on the apply report and the ingest_run rows.
APPLY_VERSION = "recovery-apply/1"
#: The least-privilege role the ``recovery_apply`` sqitch change mints.
RECOVERY_ROLE = "sig_recovery"
#: The ingest_run identity the applier stamps on the claims it asserts.
RECOVERY_CONNECTOR = "sig.recovery.apply"


#: Receipt outcome the marker records when the action's canonical row was
#: written vs deduplicated by the append-only PK.
class ApplyOutcome(StrEnum):
    APPLIED = "applied"
    #: claim_evidence's (claim_id, capture_id, role) PK deduplicated the bind —
    #: the verified capture was already bound. Honest +0, recorded, not a new row.
    CONFLICT_EXISTING = "conflict_existing"
    #: The marker already exists — a reconciled restart, never a re-write.
    ALREADY_APPLIED = "already_applied"


class RecoveryApplyError(Exception):
    """A fail-closed apply refusal — ``code`` is stable for tests/reports."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ActionResult:
    """What one apply_action call committed (or reconciled to)."""

    action_digest: str
    kind: str
    claim_id: str
    outcome: ApplyOutcome
    result_claim_id: str | None = None
    disposition_id: str | None = None
    binding_key: str | None = None
    run_id: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)


_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_EXEC_RE = re.compile(r"^[A-Za-z0-9_:.=-]{4,128}$")

#: Claim columns an adjudicated repair may revise — a fail-closed allowlist.
#: ``value_geom`` is deliberately absent: spatial corrections are outside the
#: bounded scope (the new claim inherits the old geometry verbatim).
_REVISABLE_FIELDS = frozenset(
    {
        "predicate_id",
        "object_type",
        "object_entity",
        "value_text",
        "value_num",
        "value_bool",
        "value_json",
        "unit",
        "raw_value",
        "raw_context",
        "normalization_id",
        "normalization_version",
        "observed_at",
        "observed_edtf",
        "observed_at_kind",
        "observed_unknown_reason",
        "valid_period",
        "valid_edtf",
        "valid_from_kind",
        "valid_to_kind",
        "source_reliability",
        "reliability_provisional",
        "claim_directness",
        "artifact_integrity",
        "legacy_source_tier",
        "claim_polarity",
        "rank",
        "sensitivity_tier",
        "rights_id",
    }
)

#: Column → INSERT cast fragment for the correction claim insert.
_CLAIM_CASTS: dict[str, str] = {
    "subject_id": "%s::uuid",
    "predicate_id": "%s",
    "object_entity": "%s::uuid",
    "object_type": "%s",
    "value_kind": "%s::value_kind",
    "value_text": "%s",
    "value_num": "%s",
    "value_bool": "%s",
    "value_json": "%s",
    "unit": "%s",
    "value_geom": "%s::geometry",
    "raw_value": "%s",
    "raw_context": "%s",
    "normalization_id": "%s",
    "normalization_version": "%s",
    "valid_period": "%s::tstzrange",
    "valid_edtf": "%s",
    "valid_from_kind": "%s",
    "valid_to_kind": "%s",
    "observed_at": "%s",
    "observed_edtf": "%s",
    "observed_at_kind": "%s",
    "observed_unknown_reason": "%s",
    "source_reliability": "%s",
    "reliability_provisional": "%s",
    "claim_directness": "%s",
    "artifact_integrity": "%s",
    "legacy_source_tier": "%s",
    "claim_polarity": "%s",
    "rank": "%s::claim_rank",
    "review_status": "%s::review_status",
    "extraction_id": "%s::uuid",
    "asserted_by": "%s::uuid",
    "assertion_rationale": "%s",
    "derived_from_claim_ids": "%s::uuid[]",
    "revises_claim": "%s::uuid",
    "retraction_of": "%s::uuid",
    "correction_reason": "%s",
    "ingest_run_id": "%s::uuid",
    "rights_id": "%s::uuid",
    "sensitivity_tier": "%s",
    "assertion_map_id": "%s",
    "assertion_map_basis": "%s",
    "content_digest": "%s",
}

#: Columns of the new correction row — every scalar copied from the old claim
#: plus the recorded correction metadata. ``claim_id``/``sys_period``/
#: ``created_at``/``recorded_at`` come from DEFAULTs.
_CLAIM_INSERT_COLUMNS: tuple[str, ...] = (
    "subject_id",
    "predicate_id",
    "object_entity",
    "object_type",
    "value_kind",
    "value_text",
    "value_num",
    "value_bool",
    "value_json",
    "unit",
    "value_geom",
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
    "revises_claim",
    "retraction_of",
    "correction_reason",
    "ingest_run_id",
    "rights_id",
    "sensitivity_tier",
    "assertion_map_id",
    "assertion_map_basis",
    "content_digest",
)


def applied_digests(conn: Any) -> set[str]:
    """The recorded action digests — the resume feed for a +0 re-plan."""
    rows = conn.execute("SELECT action_digest FROM recovery_application").fetchall()
    return {str(r[0] if not hasattr(r, "keys") else r["action_digest"]) for r in rows}


def inventory(conn: Any, *, claim_ids: list[str] | None = None) -> dict[str, Any]:
    """A bounded before/after fingerprint of the touched surface.

    Counts of the four tables an apply can touch (plus the marker table),
    optionally scoped to the selected claim population so a bounded apply
    reconciles its own footprint rather than the whole spine's.
    """

    def _one(sql: str, params: tuple[Any, ...] = ()) -> int:
        row = conn.execute(sql, params).fetchone()
        return int(row[0] if not hasattr(row, "keys") else next(iter(row.values())))

    scope = ""
    params: tuple[Any, ...] = ()
    if claim_ids is not None:
        scope = " WHERE claim_id = ANY(%s::uuid[])"
        params = (claim_ids,)
    claims = _one(f"SELECT count(*) FROM claim{scope}", params)
    bindings = _one(f"SELECT count(*) FROM claim_evidence{scope}", params)
    disps = _one(
        "SELECT count(*) FROM publication_disposition"
        + (
            " WHERE target_kind = 'claim' AND target_id = ANY(%s::text[])"
            if claim_ids is not None
            else ""
        ),
        (claim_ids,) if claim_ids is not None else (),
    )
    receipts = _one(
        "SELECT count(*) FROM recovery_application"
        + (" WHERE claim_id = ANY(%s::uuid[])" if claim_ids is not None else ""),
        (claim_ids,) if claim_ids is not None else (),
    )
    runs = _one("SELECT count(*) FROM ingest_run")
    return {
        "claims": claims,
        "claim_evidence": bindings,
        "publication_disposition": disps,
        "recovery_application": receipts,
        "ingest_run": runs,
    }


class PgRecoveryApplier:
    """Per-action, exactly-once apply of ``recovery-plan/1`` proposals.

    ``apply_action`` wraps its whole body in one transaction — caller-free
    atomicity. ``apply_plan`` iterates the selected actions in deterministic
    digest order; an action's failure aborts ITS transaction and is recorded,
    never half-committed. ``authority`` is the operator authorization stamped
    on every disposition + marker — the planner's placeholder never lands.
    """

    def __init__(
        self,
        conn: Any,
        *,
        execution_id: str,
        authority: str,
        decided_by: str | None = None,
        adjudicator: str | None = None,
        plan_digest: str | None = None,
        audit_input_digest: str | None = None,
        code_commit: str | None = None,
        role: str | None = None,
    ) -> None:
        if not _EXEC_RE.match(execution_id):
            raise RecoveryApplyError(
                "bad_execution_id", f"execution_id {execution_id!r} is malformed"
            )
        if not authority:
            raise RecoveryApplyError(
                "authority_required", "an apply requires the operator authority string"
            )
        self._conn = conn
        self._execution_id = execution_id
        self._authority = authority
        self._decided_by = decided_by
        self._adjudicator = adjudicator
        self._plan_digest = plan_digest
        self._audit_input_digest = audit_input_digest
        self._code_commit = code_commit or os.environ.get("SIG_CODE_COMMIT", "unknown")
        self._role = role
        self._run_id: str | None = None

    @classmethod
    def from_dsn(
        cls, dsn: str, *, role: str | None = RECOVERY_ROLE, **kwargs: Any
    ) -> PgRecoveryApplier:
        """Open an autocommit connection from ``dsn`` and SET ROLE to the
        least-privilege applier (the live-pass shape; tests share one conn)."""
        import psycopg

        conn = psycopg.connect(dsn, autocommit=True)
        try:
            if role:
                conn.execute(f"SET ROLE {role}")
            return cls(conn, role=role, **kwargs)
        except Exception:
            conn.close()
            raise

    @property
    def conn(self) -> Any:
        return self._conn

    # -- the public entry points ------------------------------------------- #

    def apply_action(self, action: Mapping[str, Any]) -> ActionResult:
        """Apply ONE plan action in a single transaction.

        ``action`` is a ``recovery_plan.json`` action dict: ``action_digest``,
        ``kind``, ``status``, ``claim_id``, ``proposed_row``, ``provenance``,
        ``batch_id``. Only ``proposed`` write kinds reach the apply path —
        ``no_write``/already-applied rows are the caller's skip, and a
        non-proposed status here is a fail-closed error, never a write.
        """
        digest = str(action.get("action_digest") or "")
        kind = str(action.get("kind") or "")
        claim_id = str(action.get("claim_id") or "")
        status = str(action.get("status") or "")
        if not _DIGEST_RE.match(digest):
            raise RecoveryApplyError(
                "bad_action_digest", f"action_digest {digest!r} is not a 64-hex digest"
            )
        if kind not in {"bind_verified_capture", "repair_claim", "record_disposition"}:
            raise RecoveryApplyError("not_writable", f"action kind {kind!r} is not a write kind")
        if status != "proposed":
            raise RecoveryApplyError(
                "not_proposed",
                f"action {digest} has status {status!r} — only 'proposed' actions are writable",
            )
        with self._conn.transaction():
            if self._role:
                from psycopg import sql

                self._conn.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(self._role)))
            # Serialize concurrent appliers of the same action for the life of
            # this transaction — the loser waits, then reconciles on the marker.
            self._conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s)::bigint)", (digest,))
            cur = self._conn.execute(
                "SELECT outcome, result_claim_id::text, disposition_id::text,"
                " binding_key, ingest_run_id::text, detail FROM recovery_application"
                " WHERE action_digest = %s",
                (digest,),
            )
            existing = cur.fetchone()
            if existing is not None:
                ex = row_to_dict(cur.description, existing)
                return ActionResult(
                    action_digest=digest,
                    kind=kind,
                    claim_id=claim_id,
                    outcome=ApplyOutcome.ALREADY_APPLIED,
                    result_claim_id=ex["result_claim_id"],
                    disposition_id=ex["disposition_id"],
                    binding_key=ex["binding_key"],
                    run_id=ex["ingest_run_id"],
                    detail={
                        "reconciled_receipt": True,
                        "recorded_outcome": ex["outcome"],
                        "recorded_detail": ex["detail"],
                    },
                )
            if kind == "record_disposition":
                result = self._apply_disposition(digest, claim_id, action)
            elif kind == "bind_verified_capture":
                result = self._apply_bind(digest, claim_id, action)
            else:
                result = self._apply_repair(digest, claim_id, action)
            self._insert_receipt(result, action)
            return result

    def apply_plan(self, actions: list[Mapping[str, Any]]) -> list[ActionResult]:
        """Apply the selected actions in deterministic digest order."""
        selected = sorted(actions, key=lambda a: str(a["action_digest"]))
        return [self.apply_action(a) for a in selected]

    # -- record_disposition ------------------------------------------------- #

    def _apply_disposition(
        self, digest: str, claim_id: str, action: Mapping[str, Any]
    ) -> ActionResult:
        row = dict(action.get("proposed_row") or {})
        try:
            record = new_disposition(
                target_kind=TargetKind(str(row.get("target_kind") or "claim")),
                target_id=str(row.get("target_id") or claim_id),
                disposition=Disposition(str(row["disposition"])),
                reason_category=ReasonCategory(str(row["reason_category"])),
                authority=self._authority,
                decided_by=self._decided_by,
                rationale=str(row.get("rationale") or ""),
            )
        except (KeyError, ValueError) as exc:
            raise RecoveryApplyError(
                "bad_proposed_row",
                f"record_disposition proposed_row is malformed: {exc}",
            ) from exc
        disposition_id = record_disposition(self._conn, record)
        return ActionResult(
            action_digest=digest,
            kind="record_disposition",
            claim_id=claim_id,
            outcome=ApplyOutcome.APPLIED,
            disposition_id=disposition_id,
            run_id=self._execution_run(),
            detail={
                "target_kind": record.target_kind.value,
                "disposition": record.disposition.value,
                "reason_category": record.reason_category.value,
                "policy_version": record.policy_version,
                "proposed_authority_replaced": row.get("authority"),
            },
        )

    # -- bind_verified_capture ---------------------------------------------- #

    def _apply_bind(self, digest: str, claim_id: str, action: Mapping[str, Any]) -> ActionResult:
        row = dict(action.get("proposed_row") or {})
        capture_id = str(row.get("capture_id") or "")
        role = str(row.get("role") or "establishes")
        locator = row.get("locator")
        # The capture occurrence must exist — a bind to a dangling capture is a
        # fail-closed refusal, never a fabricated link.
        cap = self._conn.execute(
            "SELECT capture_id::text, content_digest, capture_classification"
            " FROM evidence_capture WHERE capture_id = %s::uuid",
            (capture_id,),
        ).fetchone()
        if cap is None:
            raise RecoveryApplyError(
                "capture_missing",
                f"bind target capture {capture_id} does not exist — no row may be invented",
            )
        target = self._conn.execute(
            "SELECT 1 FROM claim WHERE claim_id = %s::uuid", (claim_id,)
        ).fetchone()
        if target is None:
            raise RecoveryApplyError("claim_missing", f"claim {claim_id} does not exist")
        policy_note = str(row.get("policy_note") or "")
        cur = self._conn.execute(
            "INSERT INTO claim_evidence(claim_id, capture_id, role, locator,"
            " weight_note, binding_status)"
            " VALUES(%s::uuid, %s::uuid, %s, %s, %s, %s)"
            " ON CONFLICT (claim_id, capture_id, role) DO NOTHING",
            (
                claim_id,
                capture_id,
                role,
                json.dumps(locator) if locator is not None else None,
                policy_note,
                str(row.get("binding_status") or "replayed"),
            ),
        )
        binding_key = f"{claim_id}|{capture_id}|{role}"
        if cur.rowcount == 1:
            return ActionResult(
                action_digest=digest,
                kind="bind_verified_capture",
                claim_id=claim_id,
                outcome=ApplyOutcome.APPLIED,
                binding_key=binding_key,
                run_id=self._execution_run(),
                detail={
                    "provenance": dict(action.get("provenance") or {}),
                    "policy_note": policy_note,
                },
            )
        existing = self._conn.execute(
            "SELECT binding_status, locator, extractor_version FROM claim_evidence"
            " WHERE claim_id = %s::uuid AND capture_id = %s::uuid AND role = %s",
            (claim_id, capture_id, role),
        ).fetchone()
        existing_row = (
            {
                "binding_status": existing[0],
                "locator": existing[1],
                "extractor_version": existing[2],
            }
            if existing is not None
            else None
        )
        untyped = bool(
            existing_row
            and existing_row["binding_status"] in ("legacy_synthetic", "document_only", None)
            and not existing_row["locator"]
        )
        return ActionResult(
            action_digest=digest,
            kind="bind_verified_capture",
            claim_id=claim_id,
            outcome=ApplyOutcome.CONFLICT_EXISTING,
            binding_key=binding_key,
            run_id=self._execution_run(),
            detail={
                "existing_binding": existing_row,
                "untyped_existing": untyped,
                "finding": (
                    "bind proposal targets an already-bound capture; the "
                    "(claim_id,capture_id,role) PK deduplicated it — no new row, "
                    "never an UPDATE of the immutable link"
                ),
                "provenance": dict(action.get("provenance") or {}),
            },
        )

    # -- repair_claim ------------------------------------------------------- #

    def _apply_repair(self, digest: str, claim_id: str, action: Mapping[str, Any]) -> ActionResult:
        row = dict(action.get("proposed_row") or {})
        provenance = dict(action.get("provenance") or {})
        revised = dict(row.get("revised_fields") or {})
        unknown = set(revised) - _REVISABLE_FIELDS
        if unknown:
            raise RecoveryApplyError(
                "revised_field_out_of_scope",
                f"revised_fields {sorted(unknown)} are outside the bounded repair allowlist",
            )
        for key, val in revised.items():
            if isinstance(val, str) and pint.screen_part_viii(val) is not None:
                raise RecoveryApplyError(
                    "unsafe_payload",
                    f"revised field {key} matches the Part VIII refusal screen",
                )
            if (
                key in ("value_json", "raw_context")
                and val is not None
                and pint.screen_part_viii(json.dumps(val)) is not None
            ):
                raise RecoveryApplyError(
                    "unsafe_payload",
                    f"revised field {key} matches the Part VIII refusal screen",
                )
        if str(row.get("revises_claim") or "") != claim_id:
            raise RecoveryApplyError(
                "revises_mismatch",
                "the repair's revises_claim must name the action's claim_id",
            )
        old = self._claim_row(claim_id)
        if old is None:
            raise RecoveryApplyError("claim_missing", f"claim {claim_id} does not exist")
        # §16.6 step 1 — close prior belief (the ONLY permitted update; a
        # concurrent close makes this a no-row update → stale, not double).
        closed = self._conn.execute(
            "UPDATE claim SET sys_period = tstzrange(lower(sys_period),"
            " clock_timestamp(), '[)') WHERE claim_id = %s::uuid"
            " AND upper_inf(sys_period)",
            (claim_id,),
        ).rowcount
        if closed != 1:
            raise RecoveryApplyError(
                "stale_record",
                "the target claim closed concurrently — reconcile, never re-close",
            )
        basis = str(provenance.get("adjudicator_basis") or "adjudicated repair")
        adjudicator_handle = self._adjudicator or _adjudicator_handle(basis)
        asserted_by = self._adjudicator_entity(adjudicator_handle)
        new_claim_id = self._insert_repair_claim(
            old=old,
            revised=revised,
            asserted_by=asserted_by,
            basis=basis,
            correction_reason=str(row.get("correction_reason") or "evidence_audit_repair"),
            run_id=self._execution_run(),
        )
        rebound = self._rebind_evidence(claim_id, new_claim_id)
        return ActionResult(
            action_digest=digest,
            kind="repair_claim",
            claim_id=claim_id,
            outcome=ApplyOutcome.APPLIED,
            result_claim_id=new_claim_id,
            run_id=self._execution_run(),
            detail={
                "adjudicator_basis": basis,
                "adjudicator": adjudicator_handle,
                "revised_fields": sorted(revised),
                "evidence_rebound": rebound,
                "predicate_id": str(row.get("predicate_id") or old["predicate_id"]),
            },
        )

    def _claim_row(self, claim_id: str) -> dict[str, Any] | None:
        cur = self._conn.execute("SELECT * FROM claim WHERE claim_id = %s::uuid", (claim_id,))
        row = cur.fetchone()
        if row is None:
            return None
        if hasattr(row, "keys"):
            return dict(row)
        return row_to_dict(cur.description, row)

    def _insert_repair_claim(
        self,
        *,
        old: dict[str, Any],
        revised: dict[str, Any],
        asserted_by: str,
        basis: str,
        correction_reason: str,
        run_id: str,
    ) -> str:
        """The §16.6 new-assertion row — inherits the old claim's whole
        epistemic/rights/sensitivity posture; the repair changes ONLY the
        fields the adjudicator's revised_fields names."""
        payload: dict[str, Any] = {c: old.get(c) for c in _CLAIM_INSERT_COLUMNS}
        for key, val in revised.items():
            if key not in payload:
                raise RecoveryApplyError(
                    "revised_field_out_of_scope", f"{key} is not a claim column"
                )
            payload[key] = val
        payload.update(
            {
                "extraction_id": None,  # asserted origin — the adjudicator path
                "asserted_by": asserted_by,
                "assertion_rationale": basis,
                "revises_claim": str(old["claim_id"]),
                "retraction_of": None,
                "correction_reason": correction_reason,
                "ingest_run_id": run_id,
                "review_status": old["review_status"],
            }
        )
        # Inherit value_kind verbatim (a repair never re-kinds) and keep
        # geometry/identity provenance as recorded.
        payload["value_kind"] = old["value_kind"]
        payload["content_digest"] = content_digest(
            {k: v for k, v in payload.items() if k != "content_digest"}
        )
        cols = list(_CLAIM_INSERT_COLUMNS)
        params: list[Any] = []
        from psycopg.types.json import Jsonb

        for c in cols:
            v = payload.get(c)
            if c in ("value_json", "raw_context") and v is not None:
                v = Jsonb(v)
            params.append(v)
        row = self._conn.execute(
            f"INSERT INTO claim({', '.join(cols)}) "
            f"VALUES ({', '.join(_CLAIM_CASTS[c] for c in cols)})"
            " RETURNING claim_id::text",
            tuple(params),
        ).fetchone()
        assert row is not None
        return str(row["claim_id"] if hasattr(row, "keys") else row[0])

    def _rebind_evidence(self, old_claim_id: str, new_claim_id: str) -> int:
        """Re-bind the SAME captures to the new assertion — the corrected
        reading stands on the same evidence; each binding's own provenance is
        preserved verbatim."""
        cur = self._conn.execute(
            "INSERT INTO claim_evidence"
            "(claim_id, capture_id, extraction_id, role, locator, excerpt,"
            " weight_note, extraction_config_digest, extractor_version,"
            " binding_status, bound_at) "
            "SELECT %s::uuid, capture_id, extraction_id, role, locator, excerpt,"
            " weight_note, extraction_config_digest, extractor_version,"
            " binding_status, bound_at "
            "FROM claim_evidence WHERE claim_id = %s::uuid"
            " ON CONFLICT (claim_id, capture_id, role) DO NOTHING",
            (new_claim_id, old_claim_id),
        )
        return cur.rowcount or 0

    def _adjudicator_entity(self, handle: str) -> str:
        """The adjudicator's ONE person entity (§11.3 attributable curators) —
        minted/adopted under the ADR-110 guard, stable across applications."""
        cur = self._conn.cursor()
        res = resolve_identities(cur, CURATOR_HANDLE_SCHEME, [handle], entity_type="person")
        return str(res.entity_by_value[handle])

    # -- the marker + the execution's own run -------------------------------- #

    def _execution_run(self) -> str:
        """The ONE ingest_run for this bounded execution — minted lazily so a
        dry-run/empty scope records no run row."""
        if self._run_id is not None:
            return self._run_id
        env = {k: v for k in ("TZ", "LC_ALL") if (v := os.environ.get(k))}
        row = self._conn.execute(
            "INSERT INTO ingest_run(connector_name, connector_version, code_commit,"
            " ruleset_version, vocab_version, parameters, environment, input_digests,"
            " status, finished_at) "
            "VALUES(%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::text[],'succeeded',clock_timestamp())"
            " RETURNING run_id::text",
            (
                RECOVERY_CONNECTOR,
                APPLY_VERSION,
                self._code_commit,
                "recovery-plan/1",
                pint.contract_version(),
                json.dumps(
                    {
                        "execution_id": self._execution_id,
                        "plan_digest": self._plan_digest,
                        "audit_input_digest": self._audit_input_digest,
                        "bounded": True,
                    }
                ),
                json.dumps(env),
                [d for d in (self._plan_digest, self._audit_input_digest) if d],
            ),
        ).fetchone()
        assert row is not None
        self._run_id = str(row["run_id"] if hasattr(row, "keys") else row[0])
        return self._run_id

    def _insert_receipt(self, result: ActionResult, action: Mapping[str, Any]) -> None:
        self._conn.execute(
            "INSERT INTO recovery_application(action_digest, execution_id, batch_id,"
            " kind, claim_id, outcome, result_claim_id, disposition_id, binding_key,"
            " plan_digest, audit_input_digest, authority, ingest_run_id, detail)"
            " VALUES(%s,%s,%s,%s,%s::uuid,%s,%s::uuid,%s::uuid,%s,%s,%s,%s,%s::uuid,%s::jsonb)",
            (
                result.action_digest,
                self._execution_id,
                action.get("batch_id"),
                result.kind,
                result.claim_id,
                result.outcome.value,
                result.result_claim_id,
                result.disposition_id,
                result.binding_key,
                self._plan_digest,
                self._audit_input_digest,
                self._authority,
                result.run_id,
                json.dumps(result.detail, default=str),
            ),
        )


def _adjudicator_handle(basis: str) -> str:
    """Derive a stable curator handle from the adjudicator basis string —
    deterministic so a restart resolves to the SAME entity."""
    slug = re.sub(r"[^a-z0-9_.-]+", "-", basis.lower()).strip("-") or "adjudicator"
    slug = slug[:64]
    return f"adj-{hashlib.sha256(basis.encode()).hexdigest()[:10]}-{slug[:40]}"
