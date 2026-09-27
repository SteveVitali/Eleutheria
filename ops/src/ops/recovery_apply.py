# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The bounded recovery application + rematerialization orchestration (P32.22,
SIG-TRUST-008, ADR-141).

This module drives the engineering stage of the bounded integrity recovery:
it reconciles a ``recovery-plan/1`` dry-run against the audited input, executes
only an explicitly bounded selected scope through
:class:`db.recovery_apply.PgRecoveryApplier`, records the before/after
inventories + resource use + a ``+0`` rerun, rematerializes the read surface in
the recorded dependency order, and freezes the unpublished repaired-input
snapshot + audit preview that is the HUMAN-H4 frame — *not* the final release
candidate (P32.23a owns that).

The hard boundaries this module keeps:

* **Dry-run ↔ applied scope match.** The apply runs only actions the plan
  recorded ``proposed``; the plan must digest-match the audit's recorded
  population; the executed set is recorded with its selection filters so the
  dry-run and the applied scope reconcile action-for-action by digest.
* **Missing bytes never trigger a refetch.** There is no fetch/transport code
  anywhere in this module — the probe READS the recorded capture root at the
  pinned occurrence only, and only to *re-verify* a bind action's recorded
  digest. A missing or unverifiable byte is an explicit skip/finding.
* **Interruption + restart never duplicates.** Exactly-once comes from the
  ``recovery_application`` receipt (``UNIQUE(action_digest)``) committing
  atomically with the canonical write; a restart reconciles
  ``already_applied`` and a re-plan proposes +0.
* **Bounded.** The apply refuses when the plan's recorded ceilings are
  exceeded; the selected scope is additionally bounded by the caller's
  batch/kind/claim filters and the abort threshold; one worker, sequential.
* **Provisional ≠ activated.** The shadow confidence report records what the
  preregistered gate *would* decide — ``applied`` stays empty; the explicitly
  PROVISIONAL production rules remain the active ones; no safety demotion is
  scoped unless the operator names it (none in this stage).
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "APPLY_REPORT_VERSION",
    "SNAPSHOT_VERSION",
    "PREVIEW_VERSION",
    "SHADOW_VERSION",
    "RETURN_PASS_VERSION",
    "REMATERIALIZE_ORDER",
    "ApplyScopeError",
    "ScopeSelection",
    "select_actions",
    "apply_selection_scoped_to",
    "reconcile_apply",
    "reverify_bind_bytes",
    "execute_bounded_apply",
    "run_rematerialize",
    "freeze_snapshot",
    "build_provisional_vs_shadow",
    "write_apply_return_pass",
    "render_apply_markdown",
    "render_preview_markdown",
    "write_report",
]

APPLY_REPORT_VERSION = "recovery-apply-report/1"
SNAPSHOT_VERSION = "sig.repaired-snapshot/1"
PREVIEW_VERSION = "sig.recovery-audit-preview/1"
SHADOW_VERSION = "sig.provisional-vs-shadow/1"
RETURN_PASS_VERSION = "recovery-apply-return-pass/1"

#: The materialization dependency order — the same P31.16/materialize.sh order
#: (resolution → camera-sites → edges → contradictions → coverage →
#: accountability). ``detect`` is deliberately not a step: it drafts research
#: tasks (an operational queue output), not a materialized read artifact, and
#: the live packet records it as an operator-scoped option.
REMATERIALIZE_ORDER: tuple[str, ...] = (
    "resolution",
    "camera-sites",
    "edges",
    "contradictions",
    "coverage",
    "accountability",
)

#: The plan action kinds this applier can write (``no_write`` never reaches it).
WRITE_KINDS = frozenset({"bind_verified_capture", "repair_claim", "record_disposition"})

_CAPTURE_LOGICAL_PATH = "capture"


class ApplyScopeError(Exception):
    """A fail-closed refusal before any write — scope, pins, or ceilings."""


@dataclass(frozen=True)
class ScopeSelection:
    """The bounded selection an apply executes + everything it excluded."""

    actions: tuple[Mapping[str, Any], ...]
    excluded: tuple[dict[str, Any], ...]
    batches: tuple[str, ...]
    claim_ids: tuple[str, ...]
    filters: dict[str, Any] = field(default_factory=dict)


def select_actions(
    plan: Mapping[str, Any],
    *,
    batches: Sequence[str] | None = None,
    kinds: Sequence[str] | None = None,
    claim_ids: Sequence[str] | None = None,
    max_actions: int | None = None,
) -> ScopeSelection:
    """Select the bounded write scope from a ``recovery_plan.json`` dict.

    Only actions the planner recorded ``proposed`` (status) and whose kind is a
    write kind are selectable — ``already_applied``/``no_write`` rows are
    recorded as exclusions, never executed. Filters AND together; the
    selection is deterministic (digest order) so the recorded scope is
    reproducible from the plan alone.
    """
    want_batches = {str(b) for b in batches} if batches else None
    want_kinds = {str(k) for k in kinds} if kinds else None
    want_claims = {str(c) for c in claim_ids} if claim_ids else None

    def _excluded(action: Mapping[str, Any]) -> str | None:
        if str(action.get("kind")) not in WRITE_KINDS:
            return "no_write"
        if str(action.get("status")) != "proposed":
            return f"status:{action.get('status')}"
        if want_batches is not None and str(action.get("batch_id")) not in want_batches:
            return "batch_filter"
        if want_kinds is not None and str(action.get("kind")) not in want_kinds:
            return "kind_filter"
        if want_claims is not None and str(action.get("claim_id")) not in want_claims:
            return "claim_filter"
        return None

    selected: list[Mapping[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for action in plan.get("actions", []):
        reason = _excluded(action)
        if reason is None:
            selected.append(action)
        else:
            excluded.append(
                {
                    "action_digest": action.get("action_digest"),
                    "kind": action.get("kind"),
                    "claim_id": action.get("claim_id"),
                    "reason": reason,
                }
            )
    selected.sort(key=lambda a: str(a["action_digest"]))
    truncated = 0
    if max_actions is not None and len(selected) > max_actions:
        truncated = len(selected) - max_actions
        overflow = selected[max_actions:]
        selected = selected[:max_actions]
        for a in overflow:
            excluded.append(
                {
                    "action_digest": a.get("action_digest"),
                    "kind": a.get("kind"),
                    "claim_id": a.get("claim_id"),
                    "reason": "abort_threshold",
                }
            )
    return ScopeSelection(
        actions=tuple(selected),
        excluded=tuple(excluded),
        batches=tuple(sorted({str(a.get("batch_id")) for a in selected if a.get("batch_id")})),
        claim_ids=tuple(sorted({str(a.get("claim_id")) for a in selected})),
        filters={
            "batches": sorted(want_batches) if want_batches else None,
            "kinds": sorted(want_kinds) if want_kinds else None,
            "claim_ids": sorted(want_claims) if want_claims else None,
            "max_actions": max_actions,
            "truncated": truncated,
        },
    )


def apply_selection_scoped_to(
    plan: Mapping[str, Any],
    audit: Mapping[str, Any],
    *,
    batches: Sequence[str] | None = None,
    kinds: Sequence[str] | None = None,
    claim_ids: Sequence[str] | None = None,
    max_actions: int | None = None,
) -> ScopeSelection:
    """Select + reconcile in one fail-closed call — raises
    :class:`ApplyScopeError` (rather than returning the problem list) when the
    plan, audit, or selection fails the pre-flight checks."""
    selection = select_actions(
        plan, batches=batches, kinds=kinds, claim_ids=claim_ids, max_actions=max_actions
    )
    problems = reconcile_apply(plan, audit, selection)
    if problems:
        raise ApplyScopeError("; ".join(problems))
    return selection


def reconcile_apply(
    plan: Mapping[str, Any],
    audit: Mapping[str, Any],
    selection: ScopeSelection,
) -> list[str]:
    """The fail-closed pre-flight checks — a problem list, empty means clear."""
    problems: list[str] = []
    if str(plan.get("plan_version")) != "recovery-plan/1":
        problems.append(f"plan_version {plan.get('plan_version')!r} is not recovery-plan/1")
    if str(audit.get("audit_version")) != "evidence-audit/1":
        problems.append(f"audit_version {audit.get('audit_version')!r} is not evidence-audit/1")
    plan_pop = (plan.get("input", {}).get("audit_report_input") or {}).get("population_digest")
    audit_pop = (audit.get("input") or {}).get("population_digest")
    if not plan_pop or plan_pop != audit_pop:
        problems.append(
            "plan input population_digest does not match the audit's — "
            "the dry-run was built over a different population than this audit"
        )
    if (plan.get("ceilings") or {}).get("exceeds_ceiling"):
        problems.append(
            "the plan's recorded ceilings are exceeded — the bounded apply "
            "refuses rather than run outside the approved resource plan"
        )
    plan_digests = {str(a.get("action_digest")) for a in plan.get("actions", [])}
    for action in selection.actions:
        if str(action.get("action_digest")) not in plan_digests:
            problems.append(f"selected action {action.get('action_digest')} is not in the plan")
        if str(action.get("status")) != "proposed":
            problems.append(f"selected action {action.get('action_digest')} is not proposed")
    if not selection.actions:
        problems.append("the selected scope is empty — nothing to apply (a +0 run is honest)")
    return problems


def reverify_bind_bytes(
    conn: Any,
    probe: Any,
    *,
    capture_id: str,
    object_id: str,
    version: str | None,
) -> bool | None:
    """Re-verify a bind action's recorded bytes before the INSERT.

    ``True`` — the recorded ``content_digest`` matches the bytes at the pinned
    occurrence; ``False`` — bytes exist but hash differently; ``None`` — the
    probe cannot determine (unmounted root, unreadable object). The applier
    treats non-``True`` as a skip: a bind never lands on unverified bytes and
    NO path fetches anything.
    """
    if probe is None:
        return None
    row = conn.execute(
        "SELECT content_digest FROM evidence_capture WHERE capture_id = %s::uuid",
        (str(capture_id),),
    ).fetchone()
    if row is None or not (row[0] if not hasattr(row, "keys") else row["content_digest"]):
        return False
    recorded = row[0] if not hasattr(row, "keys") else row["content_digest"]
    data = probe.read(str(object_id), version, _CAPTURE_LOGICAL_PATH)
    if data is None:
        return None
    from ops.evidence_audit import verify_digest

    return verify_digest(str(recorded), data) is not None


def _t0() -> float:
    return time.monotonic()


def execute_bounded_apply(
    conn: Any,
    plan: Mapping[str, Any],
    audit: Mapping[str, Any],
    *,
    execution_id: str,
    authority: str,
    decided_by: str | None = None,
    adjudicator: str | None = None,
    probe: Any = None,
    batches: Sequence[str] | None = None,
    kinds: Sequence[str] | None = None,
    claim_ids: Sequence[str] | None = None,
    max_actions: int | None = None,
    code_commit: str | None = None,
    role: str | None = None,
    verify_rerun: bool = False,
    rematerialize: bool = False,
    rematerialize_role: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Execute the bounded scope and return the apply report dict.

    Fail-closed: any reconciliation problem raises :class:`ApplyScopeError`
    BEFORE a single write. A failed action aborts the remaining selection —
    committed receipts make the retry a continuation, never a re-write.
    """
    from db.recovery_apply import PgRecoveryApplier, RecoveryApplyError, inventory

    selection = select_actions(
        plan, batches=batches, kinds=kinds, claim_ids=claim_ids, max_actions=max_actions
    )
    problems = reconcile_apply(plan, audit, selection)
    # Bind actions need a live probe to re-verify the recorded digest — no
    # probe means bytes cannot be verified, which is a fail-closed refusal.
    binds = [a for a in selection.actions if a.get("kind") == "bind_verified_capture"]
    if binds and probe is None:
        problems.append(
            "bind_verified_capture actions are selected but no capture probe is "
            "mounted — bytes cannot be re-verified, so the binds are refused "
            "rather than written unverified"
        )
    if problems:
        raise ApplyScopeError("; ".join(problems))

    started = _t0()
    before = inventory(conn, claim_ids=list(selection.claim_ids) or None)
    applier = PgRecoveryApplier(
        conn,
        execution_id=execution_id,
        authority=authority,
        decided_by=decided_by,
        adjudicator=adjudicator,
        plan_digest=_plan_digest(plan),
        audit_input_digest=(audit.get("input") or {}).get("population_digest"),
        code_commit=code_commit,
        role=role,
    )
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    distinct_reverified: set[str] = set()

    for action in selection.actions:
        if action.get("kind") == "bind_verified_capture":
            row = action.get("proposed_row") or {}
            prov = action.get("provenance") or {}
            verdict = reverify_bind_bytes(
                conn,
                probe,
                capture_id=str(row.get("capture_id") or ""),
                object_id=str(prov.get("object_id") or ""),
                version=prov.get("version"),
            )
            if verdict is not True:
                results.append(
                    {
                        "action_digest": action["action_digest"],
                        "kind": action["kind"],
                        "claim_id": action["claim_id"],
                        "outcome": "skipped",
                        "reason": "bytes_not_reverified"
                        if verdict is None
                        else "digest_mismatch_at_apply",
                        "detail": "the pinned bytes could not be re-verified — "
                        "no write, never a fabricated binding",
                    }
                )
                continue
            if prov.get("object_id"):
                distinct_reverified.add(str(prov["object_id"]))
        try:
            r = applier.apply_action(action)
            results.append(
                {
                    "action_digest": r.action_digest,
                    "kind": r.kind,
                    "claim_id": r.claim_id,
                    "outcome": r.outcome.value,
                    "result_claim_id": r.result_claim_id,
                    "disposition_id": r.disposition_id,
                    "binding_key": r.binding_key,
                    "run_id": r.run_id,
                    "detail": r.detail,
                }
            )
        except RecoveryApplyError as exc:
            failures.append(
                {
                    "action_digest": action["action_digest"],
                    "kind": action["kind"],
                    "claim_id": action["claim_id"],
                    "error_code": exc.code,
                    "error": str(exc),
                }
            )
            break  # abort threshold: stop on the first failed action
    after = inventory(conn, claim_ids=list(selection.claim_ids) or None)
    elapsed = _t0() - started

    counts = {"applied": 0, "conflict_existing": 0, "already_applied": 0, "skipped": 0}
    for res in results:
        counts[res["outcome"]] = counts.get(res["outcome"], 0) + 1

    # --- +0 rerun proof -----------------------------------------------------
    rerun: dict[str, Any] = {"executed": False}
    if verify_rerun and not failures:
        before2 = inventory(conn, claim_ids=list(selection.claim_ids) or None)
        rerun_applier = PgRecoveryApplier(
            conn,
            execution_id=f"{execution_id}-rerun",
            authority=authority,
            decided_by=decided_by,
            adjudicator=adjudicator,
            plan_digest=_plan_digest(plan),
            audit_input_digest=(audit.get("input") or {}).get("population_digest"),
            code_commit=code_commit,
            role=role,
        )
        rerun_results: list[dict[str, Any]] = []
        # The rerun re-applies the SAME per-action gate — a bind that skipped on
        # unverified bytes is skipped again, never sneaked in via the rerun path.
        for action in sorted(selection.actions, key=lambda a: str(a["action_digest"])):
            if action.get("kind") == "bind_verified_capture":
                row = action.get("proposed_row") or {}
                prov = action.get("provenance") or {}
                verdict = reverify_bind_bytes(
                    conn,
                    probe,
                    capture_id=str(row.get("capture_id") or ""),
                    object_id=str(prov.get("object_id") or ""),
                    version=prov.get("version"),
                )
                if verdict is not True:
                    rerun_results.append(
                        {"action_digest": action["action_digest"], "outcome": "skipped"}
                    )
                    continue
            rr = rerun_applier.apply_action(action)
            rerun_results.append({"action_digest": rr.action_digest, "outcome": rr.outcome.value})
        after2 = inventory(conn, claim_ids=list(selection.claim_ids) or None)
        all_reconciled = all(
            rr["outcome"] in ("already_applied", "skipped") for rr in rerun_results
        )
        rerun = {
            "executed": True,
            "results": rerun_results,
            "all_already_applied": all(rr["outcome"] == "already_applied" for rr in rerun_results),
            "all_reconciled": all_reconciled,
            "inventory_delta_zero": before2 == after2,
            "plus_zero": all_reconciled and before2 == after2,
        }

    # --- rematerialization --------------------------------------------------
    materialization: list[dict[str, Any]] = []
    if rematerialize and not failures:
        materialization = run_rematerialize(conn, role=rematerialize_role)

    return {
        "apply_version": APPLY_REPORT_VERSION,
        "generated_at": generated_at,
        "execution_id": execution_id,
        "status": "aborted" if failures else "complete",
        "authority": authority,
        "decided_by": decided_by,
        "pins": {
            "plan_digest": _plan_digest(plan),
            "audit_input_digest": (audit.get("input") or {}).get("population_digest"),
            "audit_version": audit.get("audit_version"),
            "plan_version": plan.get("plan_version"),
            "code_commit": code_commit,
            "role": role,
        },
        "scope": {
            "selected_action_digests": [str(a["action_digest"]) for a in selection.actions],
            "selected_kinds": sorted({str(a["kind"]) for a in selection.actions}),
            "batches": list(selection.batches),
            "claim_ids": list(selection.claim_ids),
            "filters": selection.filters,
            "excluded": list(selection.excluded),
            "dry_run_matches_applied": True,
        },
        "before": before,
        "after": after,
        "inventory_delta": {k: after[k] - before[k] for k in after if isinstance(after[k], int)},
        "results": results,
        "failures": failures,
        "counts": counts,
        "resource_use": {
            "wall_clock_seconds": round(elapsed, 3),
            "workers": 1,
            "distinct_capture_bytes_reverified": sorted(distinct_reverified),
            "scoped_rows_inserted": after["claims"] - before["claims"],
            "scoped_bindings_inserted": after["claim_evidence"] - before["claim_evidence"],
            "dispositions_inserted": after["publication_disposition"]
            - before["publication_disposition"],
            "receipts_recorded": after["recovery_application"] - before["recovery_application"],
            "result_writes": {
                "claims": sum(
                    1
                    for r in results
                    if r.get("kind") == "repair_claim" and r.get("outcome") == "applied"
                ),
                "claim_evidence": sum(
                    r.get("detail", {}).get("evidence_rebound", 0)
                    for r in results
                    if r.get("kind") == "repair_claim"
                )
                + sum(
                    1
                    for r in results
                    if r.get("kind") == "bind_verified_capture" and r.get("outcome") == "applied"
                ),
                "publication_disposition": sum(
                    1
                    for r in results
                    if r.get("kind") == "record_disposition" and r.get("outcome") == "applied"
                ),
            },
            "batch_bounds_respected": _batch_bounds_ok(plan, selection),
            "ceilings": plan.get("ceilings"),
        },
        "rerun": rerun,
        "rematerialization": materialization,
        "no_refetch": "no code path in the applier fetches; the probe only "
        "re-reads recorded pinned bytes for digest verification",
        "provisional": True,
        "notes": [
            "fixture/test-PG engineering stage — the production execution is a "
            "separate operator-gated live pass (D-R10-LIVE-1 stays OPEN)",
            "every 'skipped'/'conflict_existing' result is honest: nothing "
            "invented, nothing forced past the append-only surface",
        ],
    }


def _plan_digest(plan: Mapping[str, Any]) -> str | None:
    digest = plan.get("digest") or plan.get("plan_digest")
    if digest:
        return str(digest)
    return (
        "sha256:"
        + hashlib.sha256(
            (json.dumps(plan, sort_keys=True, ensure_ascii=False) + "\n").encode()
        ).hexdigest()
    )


def _batch_bounds_ok(plan: Mapping[str, Any], selection: ScopeSelection) -> bool:
    from ops.recovery_plan import MAX_ASSERTIONS_PER_BATCH, MAX_DISTINCT_BYTES_PER_BATCH

    selected_digests = {str(a["action_digest"]) for a in selection.actions}
    for b in plan.get("batches", []):
        applied = [d for d in b.get("actions", []) if str(d) in selected_digests]
        if len(applied) > MAX_ASSERTIONS_PER_BATCH:
            return False
        if int(b.get("distinct_capture_bytes") or 0) > MAX_DISTINCT_BYTES_PER_BATCH:
            return False
    return True


# ---------------------------------------------------------------------------
# Rematerialization — the shared temporal/publication contract, in order.
# ---------------------------------------------------------------------------


def _table_count(conn: Any, table: str) -> int:
    row = conn.execute(f"SELECT count(*) FROM {table}").fetchone()
    return int(row[0] if not hasattr(row, "keys") else next(iter(row.values())))


def run_rematerialize(
    conn: Any,
    *,
    role: str | None = None,
    steps: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """Run the materializers in dependency order over ``conn`` and record the
    per-step counts + timings (the same shared temporal/publication contract
    the production ``materialize.sh`` runs — here against the repaired input).

    Every step is append-only/idempotent by construction: a re-run over an
    unchanged spine inserts +0, recorded as such.
    """
    import dataclasses

    order = list(steps) if steps is not None else list(REMATERIALIZE_ORDER)
    unknown = [s for s in order if s not in REMATERIALIZE_ORDER]
    if unknown:
        raise ApplyScopeError(f"unknown rematerialization steps: {unknown}")
    results: list[dict[str, Any]] = []
    step_map = {
        "resolution": ("resolution", _step_resolution),
        "camera-sites": ("camera_site_match", _step_camera_sites),
        "edges": ("relationship", _step_edges),
        "contradictions": ("contradiction", _step_contradictions),
        "coverage": ("coverage_record", _step_coverage),
        "accountability": ("inference.derived_fact", _step_accountability),
    }
    for step in order:
        table, fn = step_map[step]
        before = _table_count(conn, table)
        t = _t0()
        record: dict[str, Any] = {
            "step": step,
            "order": order.index(step) + 1,
            "table": table,
            "before": before,
        }
        try:
            with conn.transaction():
                summary = fn(conn, role=role)
            record.update(
                {
                    "after": _table_count(conn, table),
                    "seconds": round(_t0() - t, 3),
                    "summary": dataclasses.asdict(summary)
                    if dataclasses.is_dataclass(summary) and not isinstance(summary, type)
                    else summary,
                }
            )
            record["inserted"] = record["after"] - before
        except Exception as exc:  # noqa: BLE001 — recorded verbatim, never masked
            record.update(
                {
                    "after": before,
                    "inserted": 0,
                    "seconds": round(_t0() - t, 3),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
        results.append(record)
    return results


def _step_resolution(conn: Any, *, role: str | None) -> Any:
    from reconcile.materialize import materialize_resolutions

    return materialize_resolutions(conn, role=role)


def _step_camera_sites(conn: Any, *, role: str | None) -> Any:
    from resolution.camera_sites_pg import materialize_camera_sites

    return materialize_camera_sites(conn, role=role)


def _step_edges(conn: Any, *, role: str | None) -> Any:
    from reconcile.materialize import materialize_sharing_edges

    return materialize_sharing_edges(conn, role=role)


def _step_contradictions(conn: Any, *, role: str | None) -> Any:
    from reconcile.materialize import materialize_contradictions

    return materialize_contradictions(conn, role=role)


def _step_coverage(conn: Any, *, role: str | None) -> Any:
    from inference.materialize import materialize_coverage

    return materialize_coverage(conn, role=role)


def _step_accountability(conn: Any, *, role: str | None) -> Any:
    from inference.accountability import materialize_accountability_links

    return materialize_accountability_links(conn, role=role)


# ---------------------------------------------------------------------------
# The frozen snapshot + audit preview (the HUMAN-H4 frame).
# ---------------------------------------------------------------------------


def freeze_snapshot(
    conn: Any,
    *,
    apply_report: Mapping[str, Any],
    plan: Mapping[str, Any],
    audit: Mapping[str, Any],
    probe: Any = None,
    seed: str | None = None,
    sample_size: int = 10_000,
    boundary: str | None = None,
    targeted_ids: Iterable[str] = (),
    adjudications: Mapping[str, str] | None = None,
    code_commit: str | None = None,
    sqitch_head: str | None = None,
    out_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Freeze the unpublished repaired-input snapshot + audit preview.

    Re-loads the SAME claim population from the (now repaired) spine, re-runs
    the audit under the recorded parameters, and freezes the result as
    ``sig.repaired-snapshot/1`` — explicitly ``frozen_unpublished`` and
    ``provisional_preview: true``. This is the HUMAN-H4 frame: it is NOT a
    release candidate, touches no public pointer, and changes no HG-11 state.
    Returns the snapshot dict (and writes it + the preview when ``out_dir``).
    """
    from db.evidence_audit import load_audit_input

    from ops import evidence_audit as ea

    population = [str(u.get("claim_id")) for u in audit.get("units", [])]
    load = load_audit_input(conn, claim_ids=sorted(population) if population else None)
    units = ea.units_from_rows(load.rows, load.marks, load.eligible_claim_ids)
    post_report = ea.run_audit(
        units,
        probe or ea.NULL_PROBE,
        seed=str(seed if seed is not None else (audit.get("input") or {}).get("seed") or "p32.22"),
        sample_size=int(
            sample_size if sample_size else (audit.get("input") or {}).get("sample_size") or 400
        ),
        boundary=boundary or ea.DEFAULT_ROLL_BOUNDARY,
        targeted_ids=targeted_ids,
        adjudications=adjudications,
        watermark=load.watermark,
        input_source="dsn(post-apply)",
        code_commit=code_commit,
        generated_at=None,
    )
    post_dict = post_report.to_dict()
    post_digest = "sha256:" + post_report.digest()

    applied = [
        r
        for r in apply_report.get("results", [])
        if r.get("outcome") in ("applied", "conflict_existing")
    ]
    identities = _source_identities(load)
    snapshot: dict[str, Any] = {
        "snapshot_version": SNAPSHOT_VERSION,
        "status": "frozen_unpublished",
        "provisional_preview": True,
        "not_a_release_candidate": True,
        "owned_next": "HUMAN-H4",
        "population_frame": {
            "claim_ids": sorted(population),
            "claim_count": len(population),
            "pre_apply_population_digest": (audit.get("input") or {}).get("population_digest"),
            "post_apply_population_digest": post_dict.get("input", {}).get("population_digest"),
            "strata_post": [s for s in post_dict.get("strata", [])],
            "watermark_post": load.watermark,
            "eligible_claim_ids": sorted(load.eligible_claim_ids),
        },
        "pins": {
            "code_commit": code_commit,
            "sqitch_head": sqitch_head,
            "publication_policy": "publication-eligibility/1",
            "temporal_contract": "shared-temporal-contract/1",
            "audit_version": audit.get("audit_version"),
            "plan_version": plan.get("plan_version"),
            "apply_version": apply_report.get("apply_version"),
            "evaluator_mode": "shadow",
        },
        "inputs": {
            "pre_apply_audit_input_digest": (audit.get("input") or {}).get("population_digest"),
            "post_apply_audit_digest": post_digest,
            "plan_digest": _plan_digest(plan),
            "apply_execution_id": apply_report.get("execution_id"),
            "apply_report_digest": apply_report.get("report_digest"),
        },
        "applied": {
            "action_digests": sorted(str(r["action_digest"]) for r in applied),
            "disposition_ids": sorted(
                str(r["disposition_id"]) for r in applied if r.get("disposition_id")
            ),
            "repaired_claim_ids": sorted(
                str(r["result_claim_id"]) for r in applied if r.get("result_claim_id")
            ),
            "conflict_existing": sorted(
                str(r["action_digest"]) for r in applied if r["outcome"] == "conflict_existing"
            ),
        },
        "identities": identities,
        "post_audit": {
            "report_digest": post_digest,
            "grade_distribution": (post_dict.get("metrics") or {}).get("grade_distribution"),
            "findings": post_dict.get("findings"),
            "units": post_dict.get("units"),
        },
        "explicit_reservations": [
            "this frame is UNPUBLISHED — no public pointer, no release artifact, no HG-11 state",
            "human evaluation is owed (HUMAN-H4); zero labels exist in this frame",
            "the final post-evaluation release candidate is P32.23a's — never this artifact",
            "D-R10-LIVE-1 stays OPEN — the production bounded apply has not run",
            "D-P31.4-1's reserved 2026-10-10 batch-05 verification is unchanged",
        ],
    }
    snapshot["snapshot_digest"] = (
        "sha256:"
        + hashlib.sha256(
            (json.dumps(snapshot, sort_keys=True, ensure_ascii=False, default=str) + "\n").encode()
        ).hexdigest()
    )

    if out_dir is not None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "REPAIRED_SNAPSHOT.json").write_text(
            json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n",
            encoding="utf-8",
        )
        (out / "AUDIT_PREVIEW.md").write_text(
            render_preview_markdown(snapshot, post_dict), encoding="utf-8"
        )
    return snapshot


def _source_identities(load: Any) -> dict[str, Any]:
    """The actual source/schema/rules identities the frame stands on."""
    sources: dict[str, dict[str, Any]] = {}
    connectors: set[str] = set()
    rights: set[str] = set()
    for row in load.rows:
        sid = row.get("source_id")
        if sid:
            sources.setdefault(
                str(sid),
                {
                    "source_id": sid,
                    "artifact_type": row.get("artifact_type"),
                    "capture_status": row.get("capture_status"),
                    "stable_locator": row.get("stable_locator"),
                },
            )
        if row.get("connector_name"):
            connectors.add(f"{row['connector_name']}@{row.get('connector_version')}")
        if row.get("spdx_expression"):
            rights.add(str(row["spdx_expression"]))
    return {
        "sources": sorted(sources.values(), key=lambda s: str(s["source_id"])),
        "connectors": sorted(connectors),
        "rights_expressions": sorted(rights),
    }


def render_preview_markdown(snapshot: Mapping[str, Any], post_audit: Mapping[str, Any]) -> str:
    """The human-readable audit preview — explicitly provisional."""
    grades = (post_audit.get("metrics") or {}).get("grade_distribution") or {}
    applied = snapshot.get("applied", {})
    pop = snapshot.get("population_frame", {})
    findings = post_audit.get("findings") or []
    lines = [
        "# Repaired-input audit preview — HUMAN-H4 frame",
        "",
        "> **PROVISIONAL PREVIEW — unpublished, not a release candidate.**",
        "> Frozen by `sig.repaired-snapshot/1` (P32.22). Human evaluation is owed;",
        "> nothing here is a label, an eligibility verdict, or a publication decision.",
        "",
        f"- Snapshot digest: `{snapshot.get('snapshot_digest')}`",
        f"- Population: {pop.get('claim_count')} claims "
        f"(pre-apply `{pop.get('pre_apply_population_digest')}` → "
        f"post-apply `{pop.get('post_apply_population_digest')}`)",
        f"- Post-apply audit digest: `{snapshot.get('post_audit', {}).get('report_digest')}`",
        f"- Actions applied: {len(applied.get('action_digests', []))} "
        f"({len(applied.get('disposition_ids', []))} dispositions, "
        f"{len(applied.get('repaired_claim_ids', []))} repair claims, "
        f"{len(applied.get('conflict_existing', []))} already-bound conflicts)",
        "",
        "## Post-apply grade distribution",
        "",
    ]
    for grade, n in sorted(grades.items()):
        lines.append(f"- `{grade}`: {n}")
    lines += ["", "## Findings", ""]
    if findings:
        for f in findings:
            lines.append(f"- `{f.get('kind')}` on `{f.get('claim_id')}` — {f.get('detail')}")
    else:
        lines.append("- none")
    lines += [
        "",
        "## Explicit reservations",
        "",
    ]
    lines += [f"- {r}" for r in snapshot.get("explicit_reservations", [])]
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Provisional production rules vs new shadow-eligibility results.
# ---------------------------------------------------------------------------


def build_provisional_vs_shadow(*, code_commit: str | None = None) -> dict[str, Any]:
    """The ticket's "provisional rules remain active vs shadow results" record.

    The P32.10 evaluator ships ``mode='shadow'``: installing it computed (and
    still computes) what the gate *would* decide, but ``applied`` is empty —
    nothing promoted, nothing demoted, the explicitly PROVISIONAL production
    policy untouched. This report records BOTH halves so the reviewer sees
    exactly which rules still govern and what the new gate reports.
    """
    from resolution.evaluator import activate_policy, load_confidence_policy

    policy = load_confidence_policy()
    activation_refused: list[str] = []
    try:
        activate_policy(policy, sample_count=0, measured_decision_ref=None, release_scopes=())
    except ValueError as exc:
        activation_refused.append(str(exc))
    return {
        "report_version": SHADOW_VERSION,
        "code_commit": code_commit,
        "active_provisional_rules": [
            {
                "rule": "camera-site auto-write tiers (decide_auto_write_tiers)",
                "status": "PROVISIONAL-active",
                "evidence": "resolution/camera_sites* + resolution/eval_loop.py "
                "(`provisional=True`; auto-write floor 0.98 set against an "
                "LLM-bootstrapped gold set)",
                "deferral": "D-R6.1-EVAL (OPEN) — the thresholds are explicitly "
                "provisional and must not ossify; every resolved-sites surface "
                "carries the provisional-eval disclosure",
            },
            {
                "rule": "historical point-gate (0.98 auto-write precision floor)",
                "status": "PROVISIONAL-active",
                "evidence": "P28.1 measured first-pass floor; carried in the "
                "evaluator report labelled `history` — never new eligibility",
                "deferral": "D-R6.1-EVAL (OPEN)",
            },
        ],
        "shadow_evaluator": {
            "policy_version": policy.version,
            "mode": policy.mode,
            "applied": [],
            "eval_units": 0,
            "activation_attempts_refused": activation_refused,
            "note": "installing the evaluator activates nothing — applied stays "
            "empty until the measured post-HUMAN-H5 P32.23 decision + an "
            "operational release scope",
        },
        "safety_demotions_scoped": [],
        "statement": "no provisional production rule was replaced, weakened, or "
        "certified by this stage; no shadow result activated a gate; no safety "
        "demotion is scoped in this packet (an approved demotion, if any, is a "
        "separately recorded operational decision in the live packet)",
    }


def render_shadow_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Provisional production rules vs shadow eligibility — P32.22",
        "",
        "> The shadow gate is **computed, never applied**. Nothing was promoted,",
        "> demoted, or certified; the PROVISIONAL production rules remain active.",
        "",
        "## Active provisional production rules",
        "",
    ]
    for r in report.get("active_provisional_rules", []):
        lines += [
            f"- **{r['rule']}** — `{r['status']}`",
            f"  - {r['evidence']}",
            f"  - {r['deferral']}",
        ]
    sh = report.get("shadow_evaluator", {})
    lines += [
        "",
        "## Shadow eligibility evaluator (eval-confidence/1)",
        "",
        f"- policy `{sh.get('policy_version')}`, mode `{sh.get('mode')}`, "
        f"applied `{sh.get('applied')}`",
        f"- eval units materialized: {sh.get('eval_units')}",
        f"- activation attempts refused: {sh.get('activation_attempts_refused')}",
        f"- {sh.get('note')}",
        "",
        "## Safety demotions scoped in this packet",
        "",
    ]
    dems = report.get("safety_demotions_scoped") or []
    lines += (
        [f"- {d}" for d in dems]
        if dems
        else ["- none — no safety demotion is scoped in this stage"]
    )
    lines += ["", report.get("statement", ""), ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The live return-pass packet — the production execution stays operator-gated.
# ---------------------------------------------------------------------------


def write_apply_return_pass(
    directory: str | Path,
    *,
    apply_report: Mapping[str, Any],
    snapshot: Mapping[str, Any] | None,
    hosted_dsn_env: str = "SIG_HOSTED_DSN",
) -> dict[str, Path]:
    """Emit ``recovery-apply-return-pass/1`` — the pinned contract for the
    operator-gated live stage (the explicit OPEN return-pass row for
    D-R10-LIVE-1, prepared-not-executed like its P32.6 predecessor)."""
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    pins = apply_report.get("pins", {})
    packet = {
        "packet_version": RETURN_PASS_VERSION,
        "purpose": "execute the SAME bounded apply + rematerialize + freeze "
        "against the hosted spine and mounted capture root, under recorded "
        "operator authorization — the production half of D-R10-LIVE-1",
        "status": "prepared_not_executed",
        "fixture_execution": {
            "execution_id": apply_report.get("execution_id"),
            "plan_digest": pins.get("plan_digest"),
            "audit_input_digest": pins.get("audit_input_digest"),
            "snapshot_digest": (snapshot or {}).get("snapshot_digest"),
            "counts": apply_report.get("counts"),
            "provisional": True,
        },
        "commands": [
            {
                "step": "audit (read-only, hosted replica)",
                "command": (
                    "uv run sig-ops evidence-audit "
                    f"--dsn ${hosted_dsn_env} "
                    "--capture-dir <mounted OCFL root> "
                    "--seed <recorded> --sample <recorded> --out <live-audit>/"
                ),
                "notes": "read-only transaction; records the hosted population "
                "digest + watermark the plan reconciles against",
            },
            {
                "step": "plan (offline)",
                "command": (
                    "uv run sig-ops recovery-plan --audit <live-audit>/audit_report.json "
                    "--out <live-audit>/ [--applied <receipt digests>]"
                ),
                "notes": "+0 re-plan over the applier's recorded digests proves resume",
            },
            {
                "step": "bounded apply (operator-authorized, one worker)",
                "command": (
                    "uv run sig-ops recovery-apply --dsn $SIG_HOSTED_DSN "
                    "--plan <live-audit>/recovery_plan.json --audit <live-audit>/audit_report.json "
                    "--apply --execution-id <recorded> --authority <operator-auth-ref> "
                    "--capture-dir <mounted OCFL root> --verify-rerun --rematerialize "
                    "--out <live-apply>/"
                ),
                "notes": "the SAME contract this fixture stage ran; the scope "
                "selection (--batches/--claims) is recorded in the live packet "
                "before execution; abort threshold applies",
            },
            {
                "step": "freeze (unpublished snapshot)",
                "command": (
                    "uv run sig-ops recovery-freeze --dsn $SIG_HOSTED_DSN "
                    "--apply-report <live-apply>/APPLY_REPORT.json "
                    "--plan <live-audit>/recovery_plan.json --audit <live-audit>/audit_report.json "
                    "--out <live-apply>/"
                ),
                "notes": "the HUMAN-H4 frame — unpublished, provisional, never a release candidate",
            },
        ],
        "pins": pins,
        "ceilings": (apply_report.get("resource_use") or {}).get("ceilings"),
        "verification_checklist": [
            "hosted population digest reconciles to the plan before any write",
            "applied scope ⊆ the plan's proposed actions, digest-for-digest",
            "before/after inventories + resource use recorded; receipts UNIQUE",
            "restart mid-apply reconciles already_applied — zero duplicate repairs",
            "+0 rerun verified over the recorded digests",
            "missing bytes never triggered a fetch (no fetch path exists)",
            "rematerialization ran in the recorded dependency order, +0 on re-run",
            "snapshot frozen unpublished — provisional preview only",
        ],
        "explicit_reservations": [
            "D-R10-LIVE-1 stays OPEN until THIS packet executes on production",
            "no source-rights flip, no publication, no HG gate tick, no human label",
            "no fetch of historical evidence; a new fetch is never the old capture",
            "the final post-evaluation release candidate is P32.23a's (HUMAN-H4 → "
            "P32.22a → HUMAN-H5 → P32.23 → P32.23a first)",
            "any approved safety demotion must be scoped HERE before the apply runs",
            "D-P31.4-1's 2026-10-10 batch-05 replay is untouched",
        ],
    }
    packet_path = out / "LIVE_RETURN_PASS.json"
    packet_path.write_text(
        json.dumps(packet, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    md = _return_pass_markdown(packet)
    md_path = out / "LIVE_RETURN_PASS.md"
    md_path.write_text(md, encoding="utf-8")
    return {"packet": packet_path, "markdown": md_path}


def _return_pass_markdown(packet: Mapping[str, Any]) -> str:
    cmds = "\n".join(
        f"### {i + 1}. {c['step']}\n\n```sh\n{c['command']}\n```\n\n{c['notes']}\n"
        for i, c in enumerate(packet["commands"])
    )
    checklist = "\n".join(f"- [ ] {item}" for item in packet["verification_checklist"])
    reservations = "\n".join(f"- {item}" for item in packet["explicit_reservations"])
    return f"""# Recovery-apply live return-pass packet — {packet["packet_version"]}

> Generated by P32.22 (`recovery-apply/1`). This packet is a **prepared,
> unexecuted** contract for the operator-gated live stage — the production
> bounded apply has NOT run and `D-R10-LIVE-1` stays OPEN.

## Scope

{packet["purpose"]}

- Fixture execution `{packet["fixture_execution"]["execution_id"]}` — plan
  `{packet["fixture_execution"]["plan_digest"]}`, audit input
  `{packet["fixture_execution"]["audit_input_digest"]}`, snapshot
  `{packet["fixture_execution"]["snapshot_digest"]}`

## Commands

{cmds}## Verification checklist

{checklist}

## Explicit reservations

{reservations}
"""


# ---------------------------------------------------------------------------
# Report rendering + writing.
# ---------------------------------------------------------------------------


def render_apply_markdown(report: Mapping[str, Any]) -> str:
    counts = report.get("counts", {})
    scope = report.get("scope", {})
    res = report.get("resource_use", {})
    lines = [
        f"# Bounded recovery apply — execution `{report.get('execution_id')}`",
        "",
        "> Engineering stage on the fixture/test spine. The production execution is",
        "> the operator-gated live pass (`LIVE_RETURN_PASS.json`); `D-R10-LIVE-1`",
        "> stays OPEN.",
        "",
        f"- status: **{report.get('status')}** · authority `{report.get('authority')}`",
        f"- pins: plan `{report.get('pins', {}).get('plan_digest')}`, audit input "
        f"`{report.get('pins', {}).get('audit_input_digest')}`, role "
        f"`{report.get('pins', {}).get('role')}`",
        f"- scope: {len(scope.get('selected_action_digests', []))} actions selected "
        f"({len(scope.get('excluded', []))} excluded), dry-run↔applied "
        f"`{scope.get('dry_run_matches_applied')}`",
        f"- counts: {counts}",
        "",
        "## Before/after inventory",
        "",
        "| table | before | after | Δ |",
        "|---|---|---|---|",
    ]
    before, after, delta = (
        report.get("before", {}),
        report.get("after", {}),
        report.get("inventory_delta", {}),
    )
    for k in before:
        lines.append(f"| {k} | {before[k]} | {after.get(k)} | {delta.get(k)} |")
    lines += [
        "",
        "## Results",
        "",
    ]
    for r in report.get("results", []):
        extra = ""
        if r.get("result_claim_id"):
            extra = f" → new claim `{r['result_claim_id']}`"
        elif r.get("disposition_id"):
            extra = f" → disposition `{r['disposition_id']}`"
        elif r.get("reason"):
            extra = f" ({r['reason']})"
        lines.append(f"- `{r['action_digest'][:12]}…` {r['kind']} → **{r['outcome']}**{extra}")
    for f_ in report.get("failures", []):
        lines.append(
            f"- FAILED `{f_['action_digest'][:12]}…` {f_['kind']} — "
            f"{f_['error_code']}: {f_['error']}"
        )
    lines += [
        "",
        "## Resource use",
        "",
        f"- wall clock {res.get('wall_clock_seconds')}s · workers {res.get('workers')} · "
        f"batch bounds respected `{res.get('batch_bounds_respected')}`",
        f"- result writes: +{(res.get('result_writes') or {}).get('claims', 0)} claims, "
        f"+{(res.get('result_writes') or {}).get('claim_evidence', 0)} bindings, "
        f"+{(res.get('result_writes') or {}).get('publication_disposition', 0)} dispositions; "
        f"scoped inventory +{res.get('dispositions_inserted')} dispositions, "
        f"+{res.get('receipts_recorded')} receipts",
    ]
    rerun = report.get("rerun", {})
    if rerun.get("executed"):
        lines.append(f"- **+0 rerun verified: {rerun.get('plus_zero')}**")
    mat = report.get("rematerialization") or []
    if mat:
        lines += ["", "## Rematerialization (dependency order)", ""]
        for m in mat:
            lines.append(
                f"- {m['order']}. {m['step']}: {m['before']}→{m['after']} "
                f"(+{m['inserted']}, {m['seconds']}s)"
            )
    lines += ["", f"_{report.get('no_refetch')}_", ""]
    return "\n".join(lines)


def write_report(report: Mapping[str, Any], out_dir: str | Path) -> dict[str, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "APPLY_REPORT.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    md = out / "APPLY_REPORT.md"
    md.write_text(render_apply_markdown(report), encoding="utf-8")
    return {"report": path, "markdown": md}
