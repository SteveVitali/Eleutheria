# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The bounded recovery planner — ``recovery-plan/1`` (P32.6, SIG-TRUST-007, ADR-125).

Consumes an ``evidence-audit/1`` report and produces a **dry-run-only**,
append-only recovery plan: every proposed action is an INSERT against the
spine's append-only tables — ``claim_evidence`` (typed re-bindings of verified
captures), ``claim`` (corrected repairs carrying ``revises_claim``), and
``publication_disposition`` (the P32.5 registry — the only "change" mechanism
the access surface reads). Nothing in this module writes to the spine, fetches
a byte, or reconstructs missing evidence as if it were old.

The rules the acceptance criteria name, mechanically:

* **Ambiguous lineage ⇒ zero writes.** A unit flagged ``ambiguous_lineage`` or
  ``dangling_capture`` gets a ``no_write`` action — an explicit, visible
  record that a reviewer must arbitrate — never a guess.
* **Unrecoverable stays unrecoverable.** Missing/mismatched bytes get a
  ``no_write`` action preserving the status (plus, when the claim is currently
  public-eligible, a *proposed* ``pending_publication_review`` disposition —
  a proposal a P32.22 operator applies under real authority, never applied
  here). A ``digest_mismatch`` NEVER proposes adopting the stored bytes as the
  old capture.
* **Restricted stays restricted.** ``restricted_not_public`` units get a
  ``no_write`` action noting the privileged verification path — no public
  action is proposed, and restriction is never conflated with loss.
* **Repairs are proposed, never invented.** A ``repair_claim`` action is
  emitted only for claims an adjudicator's ``repair_instructions`` record
  corrects (the audit cannot invent values); otherwise an unsupported
  semantic stays a finding, optionally with a disposition proposal.
* **Bounded, resumable, +0 restart.** Actions carry a deterministic digest of
  their full provenance; feeding the set of already-applied digests yields
  ``already_applied`` statuses and no duplicate disposition proposals. Actions
  partition into batches honouring the S1 recovery bound — at most
  :data:`MAX_ASSERTIONS_PER_BATCH` actions or :data:`MAX_DISTINCT_BYTES_PER_BATCH`
  of distinct capture bytes, whichever binds first.

The plan records row/disk/time **estimates** citing the measured ceilings —
the ADR-111 hosted land rate (~180k claims/min), the S1 pilot bound
(2 GiB / 40 claims / 30 min / one worker), the recovery batch bound
(10 000 assertions / 250 MiB), and the storage-headroom rules (warn 70 %,
require disposition 85 % or < 20 % free) — so a reviewer can check feasibility
before the live pass this packet *prepares* but does not perform.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

__all__ = [
    "PLAN_VERSION",
    "MAX_ASSERTIONS_PER_BATCH",
    "MAX_DISTINCT_BYTES_PER_BATCH",
    "ActionKind",
    "ActionStatus",
    "PlanAction",
    "RecoveryPlan",
    "build_recovery_plan",
    "plan_digests",
    "write_live_packet",
]

#: Contract version stamped on every plan (ADR-125).
PLAN_VERSION = "recovery-plan/1"

#: S1 research §6 recovery bounds — whichever binds first, one worker.
MAX_ASSERTIONS_PER_BATCH = 10_000
MAX_DISTINCT_BYTES_PER_BATCH = 250 * 1024 * 1024  # 250 MiB of DISTINCT bytes

#: Measured/cited rate constants for the estimate block.
#: ADR-111 §results: hosted sink land rate ~179.9k claims/min (dot_511_wa bench);
#: the replay pass measured ~138k records/min end to end on the small tier.
CITED_CLAIM_LAND_RATE_PER_MIN = 180_000  # ADR-111 hosted measurement
CITED_REPLAY_RATE_PER_MIN = 138_000  # ADR-111 replay measurement
#: Conservative sequential-read assumption for a mounted/gcsfuse root — the
#: hosted mount is network-backed; 50 MiB/s is deliberately below a local disk.
CITED_BYTE_READ_BYTES_PER_S = 50 * 1024 * 1024

#: Storage-headroom rules (S1 §6): warn at 70 % projected, require a recorded
#: disposition at 85 % projected or before any batch under 20 % free headroom.
WARN_CAPACITY_FRACTION = 0.70
REQUIRE_DISPOSITION_FRACTION = 0.85
MIN_BATCH_HEADROOM = 0.20


class ActionKind(StrEnum):
    """The append-only action kinds a plan may propose — INSERT-only targets."""

    #: INSERT claim_evidence — a typed binding of a verified capture to a claim
    #: currently bound only to a synthetic/legacy placeholder.
    BIND_VERIFIED_CAPTURE = "bind_verified_capture"
    #: INSERT claim (with ``revises_claim``) — an adjudicator-specified repair.
    REPAIR_CLAIM = "repair_claim"
    #: INSERT publication_disposition — the P32.5 registry row; the ONLY
    #: "change" mechanism, and only ever *proposed* by this planner.
    RECORD_DISPOSITION = "record_disposition"
    #: No write at all — the honest action for ambiguous/unrecoverable/
    #: restricted/mismatch units. Visible, counted, never a guess.
    NO_WRITE = "no_write"


class ActionStatus(StrEnum):
    PROPOSED = "proposed"
    #: Digest already in the applied set — a restarted run reports +0.
    ALREADY_APPLIED = "already_applied"
    DEFERRED_AMBIGUOUS = "deferred_ambiguous"
    UNRECOVERABLE = "unrecoverable"
    RESTRICTED = "restricted"
    DIGEST_MISMATCH = "digest_mismatch_finding"
    NOT_APPLICABLE = "not_applicable"


#: The append-only tables each write-kind lands in (asserted by tests).
TARGET_TABLES: dict[ActionKind, str | None] = {
    ActionKind.BIND_VERIFIED_CAPTURE: "claim_evidence",
    ActionKind.REPAIR_CLAIM: "claim",
    ActionKind.RECORD_DISPOSITION: "publication_disposition",
    ActionKind.NO_WRITE: None,
}


@dataclass(frozen=True)
class PlanAction:
    """One proposed (or deliberately declined) action."""

    action_digest: str
    kind: ActionKind
    status: ActionStatus
    claim_id: str
    target_table: str | None
    #: The exact row the applier would INSERT (proposals) or {} (no_write).
    proposed_row: Mapping[str, Any]
    #: The provenance the applier must re-verify before writing.
    provenance: Mapping[str, Any]
    rationale: str
    batch_id: str | None = None


def _action_digest(kind: ActionKind, claim_id: str, row: Mapping[str, Any]) -> str:
    """The deterministic identity of an action — same input, same digest."""
    payload = json.dumps(
        {"kind": kind.value, "claim_id": claim_id, "row": row},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass
class RecoveryPlan:
    """The bounded, resumable, append-only recovery plan."""

    plan_version: str
    generated_at: str | None
    input: dict[str, Any]
    actions: list[PlanAction]
    batches: list[dict[str, Any]]
    estimates: dict[str, Any]
    ceilings: dict[str, Any]
    zero_write_rules: list[str]
    totals: dict[str, Any]
    resume: dict[str, Any]
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_version": self.plan_version,
            "generated_at": self.generated_at,
            "input": self.input,
            "actions": [
                {
                    "action_digest": a.action_digest,
                    "kind": a.kind.value,
                    "status": a.status.value,
                    "claim_id": a.claim_id,
                    "target_table": a.target_table,
                    "proposed_row": dict(a.proposed_row),
                    "provenance": dict(a.provenance),
                    "rationale": a.rationale,
                    "batch_id": a.batch_id,
                }
                for a in self.actions
            ],
            "batches": self.batches,
            "estimates": self.estimates,
            "ceilings": self.ceilings,
            "zero_write_rules": self.zero_write_rules,
            "totals": self.totals,
            "resume": self.resume,
            "limitations": self.limitations,
        }

    def dumps(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"

    def digest(self) -> str:
        return hashlib.sha256(self.dumps().encode("utf-8")).hexdigest()

    def write(self, path: str | Path) -> None:
        Path(path).write_text(self.dumps(), encoding="utf-8")


def plan_digests(plan: RecoveryPlan) -> list[str]:
    """The action digests an applier records on its resume marker."""
    return sorted(a.action_digest for a in plan.actions)


def _proposed_disposition(claim_id: str, reason: str) -> dict[str, Any]:
    """The ``publication_disposition`` row a `record_disposition` action proposes."""
    return {
        "target_kind": "claim",
        "target_id": claim_id,
        "disposition": "withhold",
        "reason_category": "pending_publication_review",
        "policy_version": "publication-eligibility/1",
        "authority": "recovery-plan/1 proposal — requires P32.22 operator authorization",
        "rationale": reason,
    }


def _bind_row(claim_id: str, capture_id: str, unit_row: Mapping[str, Any]) -> dict[str, Any]:
    """The ``claim_evidence`` row a `bind_verified_capture` action proposes."""
    return {
        "claim_id": claim_id,
        "capture_id": capture_id,
        "role": "establishes",
        "binding_status": "replayed",
        "locator": unit_row.get("locator"),
        "policy_note": "append-only binding of the audit-verified capture (P32.2 typed surface)",
    }


def build_recovery_plan(
    report: Mapping[str, Any],
    *,
    applied_digests: Iterable[str] = (),
    repair_instructions: Mapping[str, Mapping[str, Any]] | None = None,
    withhold_unverifiable_public: bool = True,
    free_storage_bytes: int | None = None,
    generated_at: str | None = None,
) -> RecoveryPlan:
    """Build the recovery plan from an ``evidence-audit/1`` report dict.

    ``applied_digests`` is the resume input — digests an applier recorded on
    prior batches; matching actions report ``already_applied`` and are not
    re-proposed (a restarted run plans +0 writes).

    ``repair_instructions`` is the adjudicator channel:
    ``{claim_id: {"revised_fields": {...}, "basis": "...", "locator": {...}}}``
    — without one, an unsupported semantic NEVER becomes a repair proposal.

    ``free_storage_bytes`` is the projected free space on the target store;
    when supplied the headroom rules evaluate against it.
    """
    applied = {str(d) for d in applied_digests}
    repairs = dict(repair_instructions or {})
    actions: list[PlanAction] = []

    def _emit(
        kind: ActionKind,
        status: ActionStatus,
        claim_id: str,
        row: Mapping[str, Any],
        provenance: Mapping[str, Any],
        rationale: str,
    ) -> PlanAction:
        digest = _action_digest(kind, claim_id, row)
        if digest in applied and status == ActionStatus.PROPOSED:
            status = ActionStatus.ALREADY_APPLIED
        action = PlanAction(
            action_digest=digest,
            kind=kind,
            status=status,
            claim_id=claim_id,
            target_table=TARGET_TABLES[kind],
            proposed_row=dict(row),
            provenance=dict(provenance),
            rationale=rationale,
        )
        actions.append(action)
        return action

    for unit in report.get("units", []):
        claim_id = str(unit.get("claim_id"))
        grade = unit.get("grade")
        flags = set(unit.get("flags") or [])
        eligible = unit.get("publication_eligible")
        checks = unit.get("capture_checks") or []
        verified = [
            c
            for c in checks
            if c.get("verdict") == "verified_bytes" and not c.get("restricted_access")
        ]

        # --- zero-write cases (explicit, counted) ---------------------------
        if "ambiguous_lineage" in flags or "dangling_capture" in flags:
            _emit(
                ActionKind.NO_WRITE,
                ActionStatus.DEFERRED_AMBIGUOUS,
                claim_id,
                {},
                {"grade": grade, "flags": sorted(flags)},
                "ambiguous or dangling lineage — zero writes; a recorded reviewer "
                "disposition is required before any binding can be proposed",
            )
            continue
        if "digest_mismatch" in flags:
            _emit(
                ActionKind.NO_WRITE,
                ActionStatus.DIGEST_MISMATCH,
                claim_id,
                {},
                {"grade": grade, "flags": sorted(flags), "capture_checks": checks},
                "stored bytes hash to neither recorded digest format — the bytes are "
                "NEVER adopted as the old capture; finding preserved",
            )
            continue
        if grade == "restricted_not_public":
            _emit(
                ActionKind.NO_WRITE,
                ActionStatus.RESTRICTED,
                claim_id,
                {},
                {"grade": grade, "capture_checks": checks},
                "restricted/sealed bytes — privileged verification path only; no "
                "public action proposed and access restriction is not evidence loss",
            )
            continue
        if grade == "unrecoverable":
            _emit(
                ActionKind.NO_WRITE,
                ActionStatus.UNRECOVERABLE,
                claim_id,
                {},
                {"grade": grade, "capture_checks": checks},
                "recorded evidence is absent or unverifiable — unrecoverable status "
                "preserved; no reconstruction attempted",
            )
            if withhold_unverifiable_public and eligible:
                _emit(
                    ActionKind.RECORD_DISPOSITION,
                    ActionStatus.PROPOSED,
                    claim_id,
                    _proposed_disposition(
                        claim_id,
                        "claim's evidence is unverifiable under evidence-audit/1; "
                        "withheld pending the P32.22 review this plan proposes",
                    ),
                    {"grade": grade, "policy": "publication-eligibility/1"},
                    "public claim with unverifiable evidence — proposed withhold "
                    "disposition for the P32.22 authorized apply (never applied here)",
                )
            continue

        # --- write-proposing cases ------------------------------------------
        if "unsupported_role_mapping" in flags:
            instruction = repairs.get(claim_id)
            if instruction:
                _emit(
                    ActionKind.REPAIR_CLAIM,
                    ActionStatus.PROPOSED,
                    claim_id,
                    {
                        "predicate_id": instruction["revised_fields"].get(
                            "predicate_id", unit.get("predicate_id")
                        ),
                        "revises_claim": claim_id,
                        "revised_fields": dict(instruction["revised_fields"]),
                        "correction_reason": "evidence_audit_unsupported_role",
                    },
                    {
                        "adjudicator_basis": instruction.get("basis"),
                        "policy": "the corrected claim is a NEW row; the original stays",
                    },
                    "adjudicator-specified repair for an unsupported role mapping",
                )
                if eligible:
                    _emit(
                        ActionKind.RECORD_DISPOSITION,
                        ActionStatus.PROPOSED,
                        claim_id,
                        _proposed_disposition(
                            claim_id,
                            "unsupported role mapping superseded by an adjudicated "
                            "repair claim; withheld pending the P32.22 apply",
                        ),
                        {"grade": grade},
                        "withhold the unsupported claim once its repair lands",
                    )
            else:
                _emit(
                    ActionKind.NO_WRITE,
                    ActionStatus.UNRECOVERABLE,
                    claim_id,
                    {},
                    {"grade": grade, "flags": sorted(flags)},
                    "unsupported role mapping with no adjudicator repair — preserved "
                    "as a finding, never silently re-mapped or upgraded",
                )
            continue

        # Verified bytes + a claim whose recorded binding lacks the typed
        # lineage (synthetic/legacy placeholder) → bind the verified capture.
        if (grade == "document_locatable" and verified) or (
            grade == "source_attributed_only" and verified
        ):
            best = min(
                verified,
                key=lambda c: (str(c.get("capture_id") or ""), str(c.get("object_id") or "")),
            )
            _emit(
                ActionKind.BIND_VERIFIED_CAPTURE,
                ActionStatus.PROPOSED,
                claim_id,
                _bind_row(claim_id, str(best.get("capture_id") or ""), unit),
                {
                    "object_id": best.get("object_id"),
                    "version": best.get("version"),
                    "matched_algorithm": best.get("matched_algorithm"),
                    "evidence": "verified bytes at the pinned occurrence; the applier "
                    "re-verifies the digest before INSERT",
                },
                "bind the audit-verified capture occurrence as a typed "
                "'replayed' binding (append-only; the placeholder stays)",
            )
            continue

        # Healthy / everything else — nothing to recover.
        _emit(
            ActionKind.NO_WRITE,
            ActionStatus.NOT_APPLICABLE,
            claim_id,
            {},
            {"grade": grade, "flags": sorted(flags)},
            f"no recovery action applies to a {grade} unit"
            + (" (exact replay already proven)" if grade == "exact_replayable" else ""),
        )

    # --- batch partition ----------------------------------------------------
    # Actions are ordered deterministically (digest order); a batch closes when
    # the NEXT write-action would exceed 10 000 assertions or 250 MiB of
    # distinct capture bytes (S1 §6, whichever binds first).
    write_actions = [a for a in actions if a.kind != ActionKind.NO_WRITE]
    write_actions.sort(key=lambda a: a.action_digest)
    batches: list[dict[str, Any]] = []
    current: list[PlanAction] = []
    current_bytes: set[str] = set()
    current_bytes_size = 0

    # object_id → recorded byte_size (distinct-byte accounting per batch).
    object_bytes: dict[str, int] = {}
    for unit in report.get("units", []):
        for c in unit.get("capture_checks") or []:
            oid = c.get("object_id")
            if oid:
                object_bytes[str(oid)] = int(c.get("byte_size") or 0)

    def _bytes_of(action: PlanAction) -> set[str]:
        oid = action.provenance.get("object_id")
        return {str(oid)} if oid else set()

    def _close() -> None:
        nonlocal current, current_bytes, current_bytes_size
        if current:
            bid = f"batch-{len(batches) + 1}"
            for a in current:
                # PlanAction is frozen; the batch assignment is planner-internal.
                object.__setattr__(a, "batch_id", bid)
            batches.append(
                {
                    "batch_id": bid,
                    "actions": [a.action_digest for a in current],
                    "write_actions": len(current),
                    "distinct_capture_bytes": current_bytes_size,
                }
            )
        current = []
        current_bytes = set()
        current_bytes_size = 0

    for action in write_actions:
        new_ids = _bytes_of(action) - current_bytes
        new_size = sum(object_bytes.get(i, 0) for i in new_ids)
        if current and (
            len(current) >= MAX_ASSERTIONS_PER_BATCH
            or current_bytes_size + new_size > MAX_DISTINCT_BYTES_PER_BATCH
        ):
            _close()
            new_ids = _bytes_of(action) - current_bytes
            new_size = sum(object_bytes.get(i, 0) for i in new_ids)
        current.append(action)
        current_bytes |= new_ids
        current_bytes_size += new_size
    _close()
    # The no-write actions are recorded but carry no batch — they write nothing.

    # --- estimates ----------------------------------------------------------
    by_table: dict[str, int] = {}
    for a in actions:
        if a.status == ActionStatus.PROPOSED and a.target_table:
            by_table[a.target_table] = by_table.get(a.target_table, 0) + 1
    total_rows = sum(by_table.values())
    distinct_bytes = sum(b["distinct_capture_bytes"] for b in batches)
    est_rows_seconds = total_rows / CITED_CLAIM_LAND_RATE_PER_MIN * 60.0 if total_rows else 0.0
    est_replay_seconds = (
        len([a for a in write_actions if a.status == ActionStatus.PROPOSED])
        / CITED_REPLAY_RATE_PER_MIN
        * 60.0
        if write_actions
        else 0.0
    )
    est_byte_seconds = distinct_bytes / CITED_BYTE_READ_BYTES_PER_S if distinct_bytes else 0.0
    estimates = {
        "rows_planned": by_table,
        "total_rows": total_rows,
        "write_actions": len([a for a in write_actions if a.status == ActionStatus.PROPOSED]),
        "distinct_capture_bytes": distinct_bytes,
        "estimated_seconds": {
            "row_writes": round(est_rows_seconds, 3),
            "replay_apply": round(est_replay_seconds, 3),
            "byte_reads": round(est_byte_seconds, 3),
            "total": round(est_rows_seconds + est_replay_seconds + est_byte_seconds, 3),
        },
        "rates_cited": {
            "claim_land_rate_per_min": CITED_CLAIM_LAND_RATE_PER_MIN,
            "replay_rate_per_min": CITED_REPLAY_RATE_PER_MIN,
            "byte_read_bytes_per_s": CITED_BYTE_READ_BYTES_PER_S,
            "sources": [
                "ADR-111 hosted sink bench (~179.9k claims/min, dot_511_wa)",
                "ADR-111 replay pass (~138k records/min end to end)",
                "conservative 50 MiB/s sequential read on the mounted root",
            ],
        },
        "storage_projection": _storage_projection(free_storage_bytes, distinct_bytes),
    }
    ceilings = {
        "pilot": {
            "max_claims": 40,
            "byte_budget": 2 * 1024 * 1024 * 1024,
            "wall_clock_minutes": 30,
            "workers": 1,
            "source": "S1-evidence-integrity research §6",
        },
        "recovery_batch": {
            "max_assertions": MAX_ASSERTIONS_PER_BATCH,
            "max_distinct_bytes": MAX_DISTINCT_BYTES_PER_BATCH,
            "workers": 1,
            "source": "S1-evidence-integrity research §6",
        },
        "storage_headroom": {
            "warn_at_fraction": WARN_CAPACITY_FRACTION,
            "require_disposition_at_fraction": REQUIRE_DISPOSITION_FRACTION,
            "min_batch_free_headroom": MIN_BATCH_HEADROOM,
        },
        "exceeds_ceiling": _exceeds(batches, estimates),
    }
    totals = {
        "actions": len(actions),
        "proposed": sum(1 for a in actions if a.status == ActionStatus.PROPOSED),
        "already_applied": sum(1 for a in actions if a.status == ActionStatus.ALREADY_APPLIED),
        "deferred_ambiguous": sum(
            1 for a in actions if a.status == ActionStatus.DEFERRED_AMBIGUOUS
        ),
        "unrecoverable": sum(1 for a in actions if a.status == ActionStatus.UNRECOVERABLE),
        "restricted": sum(1 for a in actions if a.status == ActionStatus.RESTRICTED),
        "digest_mismatch": sum(1 for a in actions if a.status == ActionStatus.DIGEST_MISMATCH),
        "batches": len(batches),
        "writes_proposed": sum(
            1 for a in actions if a.status == ActionStatus.PROPOSED and a.target_table
        ),
    }
    resume = {
        "plan_digest_fields": ["kind", "claim_id", "proposed_row"],
        "applied_digest_source": "the applier's resume marker — feed applied digests "
        "back via --applied for a +0 re-plan",
        # +0 means a re-plan over the applied digests proposes no new writes.
        "second_run_is_plus_zero": totals["writes_proposed"] == 0,
        "input_report_digest": report.get("input", {}).get("population_digest"),
    }
    zero_write_rules = [
        "ambiguous_lineage or dangling_capture => NO_WRITE (deferred_ambiguous); "
        "a recorded reviewer disposition is required before any binding is proposed",
        "unrecoverable => NO_WRITE preserving the status; a proposed "
        "pending_publication_review disposition only when the claim is currently public",
        "digest_mismatch => NO_WRITE; stored bytes are NEVER adopted as the old capture",
        "restricted_not_public => NO_WRITE (restricted); the privileged verification "
        "path is noted, no public action proposed",
        "unsupported_role_mapping without an adjudicator repair => NO_WRITE; never "
        "silently re-mapped, upgraded, or silently weakened",
        "every write action targets an append-only table (claim / claim_evidence / "
        "publication_disposition) and carries the provenance its applier re-verifies",
    ]
    limitations = [
        "Dry-run only: no spine mutation, no fetch, no publication change — the "
        "authorized apply is P32.22 (D-R10-LIVE-1).",
        "Dispositions are PROPOSALS: authority string marks them as requiring "
        "P32.22 operator authorization; a real decided_by is recorded at apply.",
        "Estimates cite measured rates; actual hosted throughput is re-measured "
        "at apply time under the same pinned image.",
        "A re-fetch is never proposed: 'recoverable' requires preserved bytes "
        "plus provable lineage; missing history stays missing.",
    ]
    return RecoveryPlan(
        plan_version=PLAN_VERSION,
        generated_at=generated_at,
        input={
            "audit_version": report.get("audit_version"),
            "audit_report_input": report.get("input", {}),
            "withhold_unverifiable_public": withhold_unverifiable_public,
            "applied_digests_supplied": len(applied),
            "repair_instructions": sorted(repairs),
        },
        actions=actions,
        batches=batches,
        estimates=estimates,
        ceilings=ceilings,
        zero_write_rules=zero_write_rules,
        totals=totals,
        resume=resume,
        limitations=limitations,
    )


def _storage_projection(free_bytes: int | None, planned_bytes: int) -> dict[str, Any]:
    """The headroom projection against the reported free space."""
    if free_bytes is None:
        return {"free_storage_bytes_supplied": False}
    projected_used_fraction = (planned_bytes / free_bytes) if free_bytes else 1.0
    return {
        "free_storage_bytes_supplied": True,
        "free_storage_bytes": free_bytes,
        "planned_bytes": planned_bytes,
        "projected_use_fraction_of_free": round(projected_used_fraction, 6),
        "warn_70pct": planned_bytes > WARN_CAPACITY_FRACTION * free_bytes,
        "require_disposition_85pct": planned_bytes > REQUIRE_DISPOSITION_FRACTION * free_bytes,
        "batch_headroom_ok": planned_bytes < (1.0 - MIN_BATCH_HEADROOM) * free_bytes
        if free_bytes
        else False,
    }


def _exceeds(batches: Sequence[Mapping[str, Any]], estimates: Mapping[str, Any]) -> bool:
    """Whether any batch or estimate crosses a named ceiling."""
    for b in batches:
        if int(b.get("write_actions") or 0) > MAX_ASSERTIONS_PER_BATCH:
            return True
        if int(b.get("distinct_capture_bytes") or 0) > MAX_DISTINCT_BYTES_PER_BATCH:
            return True
    storage = estimates.get("storage_projection") or {}
    return bool(
        storage.get("require_disposition_85pct") or storage.get("batch_headroom_ok") is False
    )


def write_live_packet(
    plan: RecoveryPlan,
    report: Mapping[str, Any],
    directory: str | Path,
    *,
    capture_dir_desc: str = "the mounted OCFL capture root",
    hosted_dsn_env: str = "SIG_HOSTED_RO_DSN",
) -> dict[str, Path]:
    """Emit the live return-pass packet — the pinned re-dispatch contract.

    The packet is what the later live stage executes: the same audit against
    the hosted read-replica and mounted capture root, then this planner, with
    the invariants restated so the pass cannot drift into a re-fetch or a
    live mutation. Returns the written paths.
    """
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    packet = {
        "packet_version": "live-return-pass/1",
        "purpose": "execute the read-only legacy evidence audit + recovery plan "
        "against the hosted spine and mounted capture root; mutation stays with P32.22",
        "audit_input_digest": report.get("input", {}).get("population_digest"),
        "audit_version": report.get("audit_version"),
        "plan_version": plan.plan_version,
        "commands": [
            {
                "step": "audit (read-only)",
                "command": (
                    "uv run sig-ops evidence-audit "
                    f"--dsn ${hosted_dsn_env} "
                    "--capture-dir <mounted OCFL root> "
                    f"--seed {report.get('input', {}).get('seed', '<recorded seed>')} "
                    "--sample <recorded sample size> "
                    "--roll-boundary <recorded boundary> "
                    "--out docs/build/reports/<live-audit>/"
                ),
                "notes": "read-only transaction on the hosted replica; records the "
                "spine watermark + input digest the plan reconciles against",
            },
            {
                "step": "plan (offline)",
                "command": (
                    "uv run sig-ops recovery-plan "
                    "--audit docs/build/reports/<live-audit>/audit_report.json "
                    "--out docs/build/reports/<live-audit>/ "
                    "[--applied <resume-digests file>]"
                ),
                "notes": "feeds the applier's recorded action digests back for a +0 "
                "re-plan; emits the disposition/repair proposals P32.22 applies",
            },
        ],
        "pins": {
            "code_commit": report.get("input", {}).get("code_commit") or "recorded at run",
            "sqitch_head": "the deployed sqitch change at run time (recorded by the audit)",
            "policy_version": "publication-eligibility/1",
            "capture_root": capture_dir_desc,
        },
        "ceilings": plan.ceilings,
        "verification_checklist": [
            "population digest + watermark recorded; re-run compares against the same selection",
            "byte budget ≤ 2 GiB pilot bound honoured; UNVERIFIED (never 'missing') "
            "for anything beyond it",
            "occurrence confidence exact/bounded/unknown reported separately",
            "zero writes planned for ambiguous lineage; unrecoverable preserved",
            "second plan over the applier's recorded digests yields +0 proposed writes",
            "no fetch of historical evidence, no quota-bound API call, no live "
            "mutation, no gate signature",
        ],
        "explicit_reservations": [
            "live recovery mutation is reserved for P32.22 (D-R10-LIVE-1)",
            "HG gates unchanged: no source-rights flip, no publication, no human label",
            "API quotas remain unfetched — the audit reads only stored bytes",
            "a new fetch is NEVER the old capture: missing history is reported, not reconstructed",
        ],
    }
    packet_path = out / "live_return_pass_packet.json"
    packet_path.write_text(
        json.dumps(packet, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    md = _packet_markdown(packet)
    md_path = out / "LIVE_RETURN_PASS.md"
    md_path.write_text(md, encoding="utf-8")
    return {"packet": packet_path, "markdown": md_path}


def _packet_markdown(packet: Mapping[str, Any]) -> str:
    cmds = "\n".join(
        f"### {i + 1}. {c['step']}\n\n```sh\n{c['command']}\n```\n\n{c['notes']}\n"
        for i, c in enumerate(packet["commands"])
    )
    checklist = "\n".join(f"- [ ] {item}" for item in packet["verification_checklist"])
    reservations = "\n".join(f"- {item}" for item in packet["explicit_reservations"])
    return f"""# Live return-pass packet — {packet["audit_version"]} / {packet["plan_version"]}

> Generated by P32.6 (`recovery-plan/1`). This packet is a **prepared, unexecuted**
> contract for the later live stage. Executing it is the live pass — it is NOT a
> claim that the pass already ran.

## Scope

{packet["purpose"]}

- Audit input digest: `{packet["audit_input_digest"]}`
- Pins: code `{packet["pins"]["code_commit"]}`, sqitch `{packet["pins"]["sqitch_head"]}`,
  policy `{packet["pins"]["policy_version"]}`, capture root `{packet["pins"]["capture_root"]}`

## Commands

{cmds}
## Verification checklist

{checklist}

## Explicit reservations

{reservations}
"""


def load_report(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
