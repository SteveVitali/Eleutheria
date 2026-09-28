# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The post-evaluation release candidate (P32.23a, SIG-TRUST-010, ADR-142).

This module builds **one unpublished release candidate** from the frozen
P32.22 repaired-input snapshot. The operator's 2026-10-19 choice deferred the
whole S3 human-evaluation spine (HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23), so
there is **no final evaluation decision**: the candidate is built under the
active PROVISIONAL resolution policy and every surface that describes it
carries that deferral.

The contract this module keeps:

* **One identity everywhere.** ``sig.candidate-identity/1`` pins the ruleset
  (``provisional-ruleset/1``), the frozen repaired-input snapshot digest, the
  evaluation state (``deferred``, ``eval-confidence/1`` mode ``shadow``,
  ``applied`` empty), and the same ``ruleset_version`` the export BuildSpec
  and release descriptor stamp — no artifact cites a pre-evaluation preview
  identity, and the per-artifact manifests agree by construction.
* **Changed input stops.** Before anything materializes, the recorded
  ``population_frame.claim_ids`` are reloaded from the live spine: a missing
  claim, a population-digest drift, or an eligibility-set drift is a
  fail-closed reassessment stop — old eligibility is never carried silently.
* **+0 rematerialization.** The six materializers run in the recorded
  dependency order, then a second pass proves ``+0``; the execution appends
  its own ``ingest_run`` + ``ingest_run_completion`` rows so the completion
  is itself spine history.
* **Deferred evaluation is the inconclusive case.** Safe provisional /
  review-only disclosures only; ``eval-confidence/1`` stays ``shadow`` and
  ``applied`` stays empty; P32.10's confidence policy is never activated;
  no resolved count from any prior preview is reused — the only
  resolved-sites figure the disclosure may quote is parsed from THIS build's
  materialized coverage.
* **Unpublished by construction.** The candidate stages through
  ``exports.release.build_release`` (the real namespace builder) but the
  module never calls ``activate()`` or ``rollback()``; the publication
  pointer is read before and after staging and a drift is a hard failure.
  The rollback packet is a prepared pointer-reversal plan, not a mutation.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

__all__ = [
    "CANDIDATE_VERSION",
    "IDENTITY_VERSION",
    "DISCLOSURE_VERSION",
    "MATERIALIZATION_VERSION",
    "MANIFEST_VERSION",
    "ROLLBACK_VERSION",
    "RETURN_PASS_VERSION",
    "PROVISIONAL_RULESET",
    "EVAL_POLICY",
    "EVAL_STATUS",
    "EVAL_DEFERRAL_NOTE",
    "EVAL_DISCLOSURE",
    "CandidateError",
    "candidate_identity",
    "assert_shadow_evaluator",
    "verify_population_frame",
    "run_candidate_materialization",
    "build_candidate_export",
    "read_publication_pointer",
    "stage_candidate_release",
    "resolved_sites_figure",
    "build_disclosure",
    "build_rollback_packet",
    "build_candidate_return_pass",
    "build_candidate_manifest",
    "write_candidate_packet",
    "run_candidate",
]

CANDIDATE_VERSION = "sig.release-candidate/1"
IDENTITY_VERSION = "sig.candidate-identity/1"
DISCLOSURE_VERSION = "sig.candidate-disclosure/1"
MATERIALIZATION_VERSION = "sig.candidate-materialization/1"
MANIFEST_VERSION = "sig.candidate-manifest/1"
ROLLBACK_VERSION = "sig.candidate-rollback/1"
RETURN_PASS_VERSION = "candidate-return-pass/1"

#: The ingest_run connector identity stamped on the execution rows this build
#: appends (distinct from ``sig.recovery.apply`` — this is a new execution).
CONNECTOR = "sig.release-candidate"

#: The ruleset identity the candidate stamps. The camera-site auto-write tiers
#: and the 0.98 historical point-gate remain PROVISIONAL-active (D-R6.1-EVAL
#: OPEN) — naming the ruleset ``provisional-ruleset/1`` makes the provisional
#: basis part of the release identity, not a footnote.
PROVISIONAL_RULESET = "provisional-ruleset/1"

EVAL_POLICY = "eval-confidence/1"
EVAL_STATUS = "deferred"

EVAL_DEFERRAL_NOTE = (
    "2026-10-19 operator choice: the S3 human-evaluation spine "
    "(HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23) is deferred wholesale. There is "
    "NO final evaluation decision — this candidate is built under the active "
    "PROVISIONAL resolution policy, with the deferral disclosed everywhere the "
    "candidate is described."
)

EVAL_DISCLOSURE = (
    "PROVISIONAL EVALUATION BASIS — review-only. The S3 human-evaluation spine "
    "is deferred wholesale by explicit operator choice (2026-10-19): there is "
    "no final evaluation decision. The camera-site auto-write tiers and the "
    "historical 0.98 point-gate remain PROVISIONAL-active (D-R6.1-EVAL stays "
    "OPEN) and eval-confidence/1 stays mode=shadow with applied=[] — nothing "
    "was promoted, demoted, or certified. Any resolved-sites figure on this "
    "candidate is computed from THIS build's materialized export, carries its "
    "own denominator, and is provisional/review-only — it is not a certified "
    "count, and no figure is carried from any prior preview or evaluation "
    "artifact."
)

DEFAULT_NOTE = (
    "release candidate — provisional ruleset on the frozen repaired-input "
    "snapshot; evaluation deferred (2026-10-19, no final evaluation decision); "
    "unpublished"
)
DEFAULT_SPINE_LABEL = (
    "P32.23a release candidate (provisional ruleset over the frozen P32.22 "
    "repaired-input snapshot; the S3 human-evaluation spine is deferred — "
    "there is no final evaluation decision)"
)


class CandidateError(Exception):
    """A fail-closed refusal inside the candidate build.

    Carries ``code`` so the CLI and tests can discriminate the failure class:
    ``changed_input`` (population/semantics drift), ``activated_policy``
    (the shadow gate was applied), ``pointer_mutation`` (the publication
    pointer moved), ``bad_snapshot``/``bad_input`` (contract violations).
    """

    def __init__(self, code: str, message: str, detail: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.detail = detail


# ---------------------------------------------------------------------------
# Small serialisation/digest helpers (the same canonical-JSON contract the
# exports manifest uses — sorted keys, compact separators, trailing newline).
# ---------------------------------------------------------------------------


def _canonical(obj: Any) -> bytes:
    return (
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _sha_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _pretty(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n"


def load_json(path: str | Path) -> dict[str, Any]:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise CandidateError("bad_input", f"expected a JSON object at {path}")
    return doc


def _write_json(path: Path, doc: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _pretty(doc)
    path.write_text(text, encoding="utf-8")
    return _sha(text.encode("utf-8"))


# ---------------------------------------------------------------------------
# The frozen snapshot + the one candidate identity.
# ---------------------------------------------------------------------------


def _snapshot_digest(snapshot: Mapping[str, Any]) -> str:
    digest = str(snapshot.get("snapshot_digest") or "")
    if not digest:
        raise CandidateError(
            "bad_snapshot",
            "the input snapshot carries no snapshot_digest — the candidate "
            "must pin a frozen repaired-input snapshot",
        )
    return digest


def assert_shadow_evaluator(shadow_report: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Re-read the live ``eval-confidence/1`` posture; refuse if it applied.

    The candidate pins the evaluator at ``mode=shadow, applied=[]``. If the
    installed policy ever flips active (or reports a non-empty applied set),
    the build stops — a candidate cannot cite a shadow identity against an
    activated gate (SIG-TRUST-010).
    """
    from ops.recovery_apply import build_provisional_vs_shadow

    report = dict(shadow_report) if shadow_report is not None else build_provisional_vs_shadow()
    sh = report.get("shadow_evaluator") or {}
    if sh.get("mode") != "shadow":
        raise CandidateError(
            "activated_policy",
            f"eval-confidence/1 is mode={sh.get('mode')!r}, not 'shadow' — the "
            "candidate identity is provisional/shadow; activation is P32.24's "
            "measured-decision stage, not this build",
        )
    if list(sh.get("applied") or []):
        raise CandidateError(
            "activated_policy",
            f"eval-confidence/1 reports a non-empty applied set {sh.get('applied')!r} — "
            "the candidate may only pin applied=[]",
        )
    return report


def candidate_identity(
    *,
    snapshot: Mapping[str, Any],
    shadow_report: Mapping[str, Any] | None = None,
    code_commit: str | None = None,
    ruleset_version: str = PROVISIONAL_RULESET,
) -> dict[str, Any]:
    """``sig.candidate-identity/1`` — the one identity every artifact cites.

    Deterministic in its inputs (no clock): the same snapshot + policy posture
    always produce the same identity digest, so the manifest, the disclosure,
    the rollback packet, and the release descriptor can all be checked to
    agree.
    """
    shadow = assert_shadow_evaluator(shadow_report)
    sh = shadow.get("shadow_evaluator") or {}
    frame = snapshot.get("population_frame") or {}
    identity: dict[str, Any] = {
        "identity_version": IDENTITY_VERSION,
        "candidate_version": CANDIDATE_VERSION,
        "ruleset_version": ruleset_version,
        "code_commit": code_commit,
        "frozen_snapshot": {
            "snapshot_version": snapshot.get("snapshot_version"),
            "snapshot_digest": _snapshot_digest(snapshot),
            "status": snapshot.get("status"),
            "claim_count": frame.get("claim_count"),
            "post_apply_population_digest": frame.get("post_apply_population_digest"),
        },
        "evaluation": {
            "status": EVAL_STATUS,
            "decision": None,
            "decision_ref": None,
            "basis": "provisional-policy",
            "deferred_by": EVAL_DEFERRAL_NOTE,
            "policy_version": sh.get("policy_version"),
            "policy_id": EVAL_POLICY,
            "mode": sh.get("mode"),
            "applied": list(sh.get("applied") or []),
            "eval_units": sh.get("eval_units"),
            "activation_attempts_refused": sh.get("activation_attempts_refused"),
            "provisional_rules_active": [
                r.get("rule") for r in shadow.get("active_provisional_rules") or []
            ],
            "p32_10_confidence_policy": "installed-but-shadow; NOT activated",
            "disclosure": EVAL_DISCLOSURE,
        },
        "provisional": True,
        "review_only": True,
        "published": False,
    }
    identity["identity_digest"] = _sha(_canonical(identity))
    return identity


# ---------------------------------------------------------------------------
# Changed-input verification (the "stop for reassessment" guard, §3.1).
# ---------------------------------------------------------------------------


def verify_population_frame(conn: Any, snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Reload the frozen population from the live spine; STOP on drift.

    The frame's recorded ``claim_ids`` are re-selected; the audit's
    ``population_digest`` (sha256 over the sorted id list) and the
    ``eligible_claim_ids`` (the shared ``publication-eligibility/1`` set — the
    semantics) are recomputed and compared. ANY drift is a
    ``changed_input`` refusal — the candidate never silently carries old
    eligibility over a changed sample population.
    """
    from db.evidence_audit import load_audit_input

    frame = snapshot.get("population_frame") or {}
    recorded_ids = sorted(str(c) for c in frame.get("claim_ids") or [])
    if not recorded_ids:
        raise CandidateError(
            "bad_snapshot",
            "the frozen snapshot records no population_frame.claim_ids — there "
            "is no sample population to reconcile against",
        )
    load = load_audit_input(conn, claim_ids=recorded_ids)
    present = sorted({str(r.get("claim_id")) for r in load.rows})
    present_set = set(present)
    missing = [c for c in recorded_ids if c not in present_set]
    digest = "sha256:" + hashlib.sha256(json.dumps(present).encode("utf-8")).hexdigest()
    recorded_digest = str(
        frame.get("post_apply_population_digest") or frame.get("pre_apply_population_digest") or ""
    )
    eligible_now = sorted(str(c) for c in load.eligible_claim_ids)
    eligible_recorded = sorted(str(c) for c in frame.get("eligible_claim_ids") or [])

    checks: dict[str, Any] = {
        "claims_recorded": len(recorded_ids),
        "claims_present": len(present),
        "claims_missing": missing,
        "population_digest": digest,
        "population_digest_recorded": recorded_digest,
        "population_digest_matches": digest == recorded_digest,
        "eligible_recorded_count": len(eligible_recorded),
        "eligible_now_count": len(eligible_now),
        "eligible_gained": sorted(set(eligible_now) - set(eligible_recorded)),
        "eligible_lost": sorted(set(eligible_recorded) - set(eligible_now)),
        "eligibility_matches": eligible_now == eligible_recorded,
        "watermark_now": load.watermark,
        "watermark_recorded": frame.get("watermark_post"),
    }
    problems: list[str] = []
    if missing:
        problems.append(
            f"{len(missing)} claims of the frozen population are absent from "
            f"the spine ({missing[:3]}{'…' if len(missing) > 3 else ''})"
        )
    if recorded_digest and digest != recorded_digest:
        problems.append(
            f"the population digest drifted ({recorded_digest} → {digest}) — "
            "the sample population changed"
        )
    if eligible_now != eligible_recorded:
        problems.append(
            "publication eligibility changed since the snapshot was frozen "
            f"(+{len(checks['eligible_gained'])}/-{len(checks['eligible_lost'])}) — "
            "the eligibility semantics changed"
        )
    if problems:
        raise CandidateError(
            "changed_input",
            "changed input affecting the sample population or semantics — "
            "stopping for reassessment instead of carrying old eligibility "
            "forward: " + "; ".join(problems),
            detail=checks,
        )
    return checks


# ---------------------------------------------------------------------------
# Dependency-ordered rematerialization + the appended execution completion.
# ---------------------------------------------------------------------------


def _candidate_execution_run(
    conn: Any,
    *,
    identity_digest: str,
    snapshot_digest: str,
    plan_digest: str | None,
    code_commit: str | None,
) -> str:
    """Mint the ONE ``ingest_run`` for this candidate execution (append-only)."""
    from policy import intake as pint

    parameters = {
        "candidate_identity_digest": identity_digest,
        "frozen_snapshot_digest": snapshot_digest,
        "recovery_plan_digest": plan_digest,
        "evaluation": {"status": EVAL_STATUS, "policy": EVAL_POLICY, "mode": "shadow"},
        "unpublished": True,
    }
    row = conn.execute(
        "INSERT INTO ingest_run(connector_name, connector_version, code_commit,"
        " ruleset_version, vocab_version, parameters, environment, input_digests,"
        " status, finished_at) "
        "VALUES(%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::text[],'succeeded',clock_timestamp())"
        " RETURNING run_id::text",
        (
            CONNECTOR,
            CANDIDATE_VERSION,
            code_commit or "unrecorded",
            PROVISIONAL_RULESET,
            pint.contract_version(),
            json.dumps(parameters),
            json.dumps({}),
            [d for d in (identity_digest, snapshot_digest, plan_digest) if d],
        ),
    ).fetchone()
    if row is None:
        raise CandidateError("internal", "ingest_run insert returned no run_id")
    return str(row["run_id"] if hasattr(row, "keys") else row[0])


def run_candidate_materialization(
    conn: Any,
    *,
    identity_digest: str,
    snapshot_digest: str,
    plan_digest: str | None = None,
    role: str | None = None,
    code_commit: str | None = None,
    sqitch_head: str | None = None,
) -> dict[str, Any]:
    """``sig.candidate-materialization/1`` — rematerialize + prove ``+0``.

    Runs the recorded dependency order twice over the same connection: pass 1
    rematerializes the read surface; pass 2 must insert +0 (idempotent by
    construction — the proof the surface is stable under the pinned inputs).
    The execution appends its own ``ingest_run`` +
    ``ingest_run_completion`` (status ``ok`` on a clean +0, ``failed``
    otherwise — recorded before the refusal is raised).
    """
    from db.run_completion import append_completion

    from ops.recovery_apply import REMATERIALIZE_ORDER, run_rematerialize

    t0 = time.monotonic()
    pass_one = run_rematerialize(conn, role=role)
    rerun = run_rematerialize(conn, role=role)
    inserted_one = sum(int(r.get("inserted") or 0) for r in pass_one)
    inserted_rerun = sum(int(r.get("inserted") or 0) for r in rerun)
    errors = [
        {"step": r.get("step"), "error": r.get("error")}
        for r in (*pass_one, *rerun)
        if r.get("error")
    ]
    plus_zero = inserted_rerun == 0 and not any(r.get("error") for r in rerun)

    run_id = _candidate_execution_run(
        conn,
        identity_digest=identity_digest,
        snapshot_digest=snapshot_digest,
        plan_digest=plan_digest,
        code_commit=code_commit,
    )
    status = "ok" if plus_zero and not errors else "failed"
    completion_id = append_completion(
        conn,
        run_id=run_id,
        status=status,
        claims_inserted=inserted_one,
        detail=(
            f"P32.23a release candidate materialization — pass-1 +{inserted_one}, "
            f"rerun +{inserted_rerun} ({'clean +0' if plus_zero else 'NOT idempotent'})"
        ),
    )
    report: dict[str, Any] = {
        "materialization_version": MATERIALIZATION_VERSION,
        "dependency_order": list(REMATERIALIZE_ORDER),
        "pass_one": pass_one,
        "rerun": rerun,
        "inserted_pass_one": inserted_one,
        "inserted_rerun": inserted_rerun,
        "plus_zero": plus_zero,
        "errors": errors,
        "seconds": round(time.monotonic() - t0, 3),
        "execution": {
            "ingest_run_id": run_id,
            "completion_id": completion_id,
            "completion_status": status,
            "code_commit": code_commit,
            "sqitch_head": sqitch_head,
        },
        "note": "audit history preserved: the P32.22 apply receipts and this "
        "execution's run/completion rows coexist append-only; nothing "
        "rewrites history",
    }
    if errors:
        raise CandidateError(
            "materialization_failed",
            f"a rematerialization step errored: {errors}",
            detail=report,
        )
    if not plus_zero:
        raise CandidateError(
            "materialization_not_idempotent",
            f"the rematerialization rerun inserted +{inserted_rerun} — the "
            "read surface is not stable under the pinned inputs",
            detail=report,
        )
    return report


# ---------------------------------------------------------------------------
# The compartmented export + the unpublished staged release.
# ---------------------------------------------------------------------------


def build_candidate_export(
    conn: Any,
    *,
    as_of: str | None = None,
    belief: Any = None,
    note: str = DEFAULT_NOTE,
    spine_label: str = DEFAULT_SPINE_LABEL,
    ruleset_version: str = PROVISIONAL_RULESET,
    resolver_version: str | None = None,
    dossier_packets: Sequence[Mapping[str, Any]] | None = None,
) -> Any:
    """The licence-compartmented spine export, stamped with the candidate
    ruleset identity (``provisional-ruleset/1``) and the deferral-carrying
    note/label — one ``REPEATABLE READ READ ONLY`` snapshot, no mutation."""
    from exports.spine_export import run_spine_export

    return run_spine_export(
        conn,
        as_of=as_of,
        belief=belief,
        note=note,
        spine_label=spine_label,
        ruleset_version=ruleset_version,
        resolver_version=resolver_version,
        dossier_packets=dossier_packets,
    )


def read_publication_pointer(registry_dir: str | Path | None) -> dict[str, Any] | None:
    """The mutable ``latest.json`` content (the publication pointer), or
    ``None`` when no pointer exists yet. Read-only — never written here."""
    if registry_dir is None:
        return None
    latest = Path(registry_dir) / "latest.json"
    if not latest.exists():
        return None
    try:
        doc = json.loads(latest.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:  # a corrupt pointer is itself a finding
        raise CandidateError(
            "bad_input", f"the publication pointer at {latest} is unreadable: {exc}"
        ) from exc
    return doc if isinstance(doc, dict) else None


def stage_candidate_release(
    export_dir: str | Path,
    release_dir: str | Path,
    *,
    renderer_revision: str,
    registry_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Build the immutable ``r/<publication_id>`` namespace — WITHOUT
    activation.

    ``build_release`` is the real namespace builder (records, browse/jurisdiction
    pages, evidence pages, dossiers, per-compartment FTS5 indexes, the
    descriptor, the manifest); ``validate_release`` re-verifies it. Neither
    ``activate()`` nor ``rollback()`` is ever called — the publication pointer
    is captured before and after, and any drift is a hard failure.
    """
    from exports.release import build_release, validate_release

    pointer_before = read_publication_pointer(registry_dir)
    build = build_release(export_dir, release_dir, renderer_revision=renderer_revision)
    validation = validate_release(release_dir)
    pointer_after = read_publication_pointer(registry_dir)
    if pointer_after != pointer_before:
        raise CandidateError(
            "pointer_mutation",
            "the publication pointer changed during candidate staging — the "
            "candidate must leave latest.json byte-identical",
            detail={"before": pointer_before, "after": pointer_after},
        )
    return {
        "build": build,
        "validation": validation,
        "pointer_before": pointer_before,
        "pointer_after": pointer_after,
        "pointer_unchanged": True,
        "activated": False,
        "staged_at_dir": str(release_dir),
    }


def resolved_sites_figure(export_dir: str | Path) -> dict[str, Any] | None:
    """The ONLY resolved-sites figure the candidate may quote.

    Parsed from THIS build's ``web/coverage.json`` — never from the snapshot,
    the apply report, or any prior preview. A figure that presents as a
    population total (the optimistic-count failure mode) is refused outright.
    """
    cov_path = Path(export_dir) / "web" / "coverage.json"
    if not cov_path.exists():
        return None
    try:
        cov = json.loads(cov_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    metrics = (
        list(cov)
        if isinstance(cov, list)
        else list(cov.get("metrics") or [])
        if isinstance(cov, dict)
        else []
    )
    for metric in metrics:
        if str(metric.get("id")) != "resolved_sites":
            continue
        if metric.get("is_population_total"):
            raise CandidateError(
                "optimistic_count",
                "the build's resolved-sites metric is framed as a population "
                "total — the deferred-evaluation candidate may only carry "
                "denominated, provisional figures",
            )
        return {
            "metric_id": "resolved_sites",
            "value": metric.get("value"),
            "denominator": metric.get("denominator"),
            "provisional": True,
            "source": "this build's materialized web/coverage.json only",
        }
    return None


# ---------------------------------------------------------------------------
# The disclosure, the rollback packet, the manifest.
# ---------------------------------------------------------------------------


def build_disclosure(
    *,
    identity: Mapping[str, Any],
    export_dir: str | Path,
    apply_report: Mapping[str, Any] | None = None,
    materialization: Mapping[str, Any] | None = None,
    build_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """``sig.candidate-disclosure/1`` — the final change/suppression/evaluation
    disclosure for this exact candidate (provisional, review-only)."""
    export_dir = Path(export_dir)
    exclusions: dict[str, Any] = {}
    ex_path = export_dir / "exclusions.json"
    if ex_path.exists():
        try:
            exclusions = json.loads(ex_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            exclusions = {}
    refused_slices = list(exclusions.get("refused") or [])
    totals = dict(exclusions.get("totals") or {})
    counts = dict((apply_report or {}).get("counts") or {})
    results = list((apply_report or {}).get("results") or [])
    dispositions = [r for r in results if r.get("disposition_id")]
    disclosure: dict[str, Any] = {
        "disclosure_version": DISCLOSURE_VERSION,
        "candidate_identity_digest": identity.get("identity_digest"),
        "status": "provisional_review_only",
        "published": False,
        "change_disclosure": {
            "source": "P32.22 bounded recovery apply (recovery-apply-report/1)",
            "counts": counts,
            "applied_action_digests": [
                str(r.get("action_digest"))
                for r in results
                if r.get("outcome") in ("applied", "conflict_existing")
            ],
            "rerun_plus_zero": (apply_report or {}).get("rerun", {}).get("plus_zero"),
            "candidate_rematerialization_plus_zero": (materialization or {}).get("plus_zero"),
            "audit_history": "append-only — the apply receipts and this "
            "execution's ingest_run/completion rows coexist; nothing rewrites "
            "history",
        },
        "suppression_disclosure": {
            "dispositions_recorded": len(dispositions),
            "disposition_ids": [str(r.get("disposition_id")) for r in dispositions],
            "export_refused_slices": refused_slices,
            "export_refused_totals": totals,
            "export_exclusions_generated_at": exclusions.get("generated_at"),
            "export_exclusions_note": exclusions.get("note"),
            "note": "withheld/refused slices are recorded loudly in "
            "exclusions.json inside the candidate namespace — never silently "
            "dropped",
        },
        "evaluation_disclosure": EVAL_DISCLOSURE,
        "evaluation": {
            "status": EVAL_STATUS,
            "decision": None,
            "basis": "provisional-policy",
            "policy_id": EVAL_POLICY,
            "mode": (identity.get("evaluation") or {}).get("mode"),
            "applied": [],
            "p32_10_confidence_policy_activated": False,
        },
        "resolved_sites": resolved_sites_figure(export_dir),
        "resolved_sites_note": (
            "the only resolved-sites figure permitted on this candidate is the "
            "one parsed from THIS build's web/coverage.json; no figure from any "
            "prior preview/republish artifact is reused (the deferred "
            "evaluation cannot inherit an optimistic count)"
        ),
        "prior_preview_counts_reused": False,
        "records_built": (build_report or {}).get("records"),
        "statement": (
            "no final evaluation decision exists; this candidate's claims are "
            "provisional and review-only; publication requires P32.24 "
            "validation + GATE-G3/HG-11 + P32.25 — none of which this build ran"
        ),
    }
    return disclosure


def build_rollback_packet(
    *,
    identity: Mapping[str, Any],
    publication_id: str | None,
    release_manifest_sha256: str | None,
    descriptor_sha256: str | None,
    disclosure_digest: str | None,
    pointer_before: Mapping[str, Any] | None,
    materialization: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """``sig.candidate-rollback/1`` — the prepared pointer-reversal plan.

    The candidate is unpublished; this packet records how the publication
    pointer is reversed IF P32.25 ever activates it — the mutable
    ``latest.json`` flips back to the recorded prior pointer (or is removed if
    none existed), the immutable ``r/<publication_id>`` namespace is retained
    as history, and the staged copy is removed. Nothing here mutates anything.
    """
    prior_pointer = dict(pointer_before) if pointer_before else None
    return {
        "rollback_version": ROLLBACK_VERSION,
        "status": "prepared_not_needed",
        "candidate": {
            "candidate_identity_digest": identity.get("identity_digest"),
            "publication_id": publication_id,
            "release_manifest_sha256": release_manifest_sha256,
            "descriptor_sha256": descriptor_sha256,
            "disclosure_digest": disclosure_digest,
            "published": False,
        },
        "publication_pointer_before": prior_pointer,
        "publication_pointer_after_staging": prior_pointer,
        "pointer_unchanged": True,
        "reversal_plan": {
            "mechanism": (
                "pointer-only reversal through exports.release.rollback on the "
                "served registry — the mutable latest.json flips to the "
                "recorded prior pointer; the immutable r/<pub> namespace is "
                "never deleted (append-only release history)"
            ),
            "if_no_prior_pointer": (
                "no latest.json existed before this candidate — reversal "
                "removes the pointer entirely rather than fabricating a "
                "predecessor"
                if prior_pointer is None
                else f"latest.json returns to publication_id "
                f"{prior_pointer.get('publication_id')!r} "
                f"(manifest {str(prior_pointer.get('manifest_sha256'))[:24]}…)"
            ),
            "steps": [
                "confirm the candidate publication_id is currently pointed at",
                "run exports.release.rollback(registry, to=<prior pointer>) "
                "or remove latest.json when no prior pointer existed",
                "re-validate the registry (catalog + compatibility indexes)",
                "leave the immutable r/<publication_id> tree untouched — it is "
                "history, and its manifest/descriptor remain verifiable",
            ],
        },
        "preconditions": [
            "the candidate was actually activated by P32.25 (this build never "
            "activates — the packet is preparation, not a mutation)",
            "operator authorization under the HG-11/GATE-G3 chain",
        ],
        "change_disclosure_ref": "suppression + change counts live in the "
        "companion sig.candidate-disclosure/1 (digest recorded above)",
        "materialization_plus_zero": (materialization or {}).get("plus_zero"),
    }


def build_candidate_return_pass(
    *,
    identity_digest: str | None,
    snapshot_digest: str,
    hosted_dsn_env: str = "SIG_HOSTED_DSN",
) -> dict[str, Any]:
    """The OPEN live-stage return-pass packet (prepared, not executed).

    The fixture candidate is evidence over the engineering spine only. The
    production candidate still needs the production repaired spine — the
    operator-gated D-R10-LIVE-1 execution — and then the SAME pipeline this
    module runs. This packet pins that contract without claiming the live
    half happened.
    """
    return {
        "packet_version": RETURN_PASS_VERSION,
        "status": "prepared_not_executed",
        "purpose": (
            "build the production release candidate over the hosted repaired "
            "spine — the SAME pipeline this module ran on the fixture "
            "(frame-verify → +0 rematerialize → export → stage → disclose), "
            "under recorded operator authorization"
        ),
        "fixture_execution": {
            "candidate_identity_digest": identity_digest,
            "frozen_snapshot_digest": snapshot_digest,
            "provisional": True,
        },
        "prerequisite_open_deferrals": [
            "D-R10-LIVE-1 — the production bounded apply + freeze must land "
            "first (the hosted repaired-input snapshot this candidate pins)",
            "the production snapshot must be sig.repaired-snapshot/1 "
            "frozen_unpublished — never a preview identity",
        ],
        "commands": [
            {
                "step": "production bounded apply + freeze (D-R10-LIVE-1)",
                "command": (
                    f"uv run sig-ops recovery-apply --dsn ${hosted_dsn_env} "
                    "--plan <live-plan> "
                    "--audit <live-audit> --apply --execution-id <id> "
                    "--authority <op-ref> --capture-dir <OCFL root> "
                    "--verify-rerun --rematerialize --out <live-apply>/ && "
                    f"uv run sig-ops recovery-freeze --dsn ${hosted_dsn_env} "
                    "--apply-report <live-apply>/APPLY_REPORT.json "
                    "--plan <plan> --audit <audit> --out <live-apply>/"
                ),
                "notes": "produces the hosted frozen snapshot — same contract "
                "the fixture stage ran",
            },
            {
                "step": "release candidate over the hosted snapshot",
                "command": (
                    f"uv run sig-ops release-candidate --dsn ${hosted_dsn_env} "
                    "--snapshot <live-apply>/REPAIRED_SNAPSHOT.json "
                    "--plan <plan> --audit <audit> "
                    "--apply-report <live-apply>/APPLY_REPORT.json "
                    "--registry <release registry> --out <candidate>/"
                ),
                "notes": "the same frame-verify/+0/stage pipeline; stops "
                "fail-closed on changed input or an activated shadow gate",
            },
        ],
        "verification_checklist": [
            "population frame reconciles to the hosted snapshot, digest-for-digest",
            "rematerialization dependency order ran; rerun +0",
            "the release namespace validates; every manifest cites the same "
            "candidate identity digest",
            "eval-confidence/1 is shadow with applied=[] at build time",
            "latest.json is byte-identical before and after staging",
            "the disclosure is provisional/review-only; no prior preview count is quoted",
            "the candidate remains unpublished until P32.24 + GATE-G3 + P32.25",
        ],
        "explicit_reservations": [
            "D-R10-LIVE-1 stays OPEN until the production stage lands",
            "no publication, no HG-11 tick, no source-rights flip, no human label",
            "eval-confidence/1 stays shadow; P32.10 activation needs the "
            "measured P32.23 decision (deferred, not skipped forever)",
        ],
    }


def build_candidate_manifest(
    *,
    identity: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    frame_check: Mapping[str, Any],
    materialization: Mapping[str, Any],
    staged: Mapping[str, Any],
    disclosure: Mapping[str, Any],
    rollback: Mapping[str, Any],
    return_pass: Mapping[str, Any],
    dossier_packet_digests: Mapping[str, str] | None = None,
    apply_report: Mapping[str, Any] | None = None,
    plan_digest: str | None = None,
    audit_digest: str | None = None,
) -> dict[str, Any]:
    """``sig.candidate-manifest/1`` — the roll-up record P32.24 validates.

    Pins one candidate identity digest plus the digests of every emitted
    artifact group so a reviewer can recompute any single artifact and check
    the whole packet is the one this manifest describes.
    """
    build = staged.get("build")
    descriptor = (build.descriptor if build else {}) or {}
    descriptor_sha = _sha(_canonical(descriptor)) if descriptor else None
    export_manifest_sha = staged.get("export_manifest_sha256")
    validation = staged.get("validation")
    validation_state = getattr(validation, "state", None)
    return {
        "manifest_version": MANIFEST_VERSION,
        "candidate": {
            "candidate_version": CANDIDATE_VERSION,
            "identity_digest": identity.get("identity_digest"),
            "ruleset_version": identity.get("ruleset_version"),
            "frozen_snapshot_digest": (identity.get("frozen_snapshot") or {}).get(
                "snapshot_digest"
            ),
            "evaluation_status": (identity.get("evaluation") or {}).get("status"),
            "evaluation_policy": EVAL_POLICY,
            "evaluation_mode": (identity.get("evaluation") or {}).get("mode"),
            "published": False,
            "provisional": True,
            "review_only": True,
        },
        "identity": identity,
        "inputs": {
            "snapshot": {
                "version": snapshot.get("snapshot_version"),
                "digest": _snapshot_digest(snapshot),
                "status": snapshot.get("status"),
                "predecessor": "P32.22 bounded recovery (frozen repaired-input "
                "snapshot; itself 'not_a_release_candidate' by design)",
            },
            "recovery_plan_digest": plan_digest,
            "post_apply_audit_digest": audit_digest,
            "apply_report_version": (apply_report or {}).get("report_version"),
            "dossier_packets": dict(dossier_packet_digests or {}),
        },
        "frame_check": frame_check,
        "materialization": {
            "materialization_version": MATERIALIZATION_VERSION,
            "dependency_order": (materialization or {}).get("dependency_order"),
            "inserted_pass_one": (materialization or {}).get("inserted_pass_one"),
            "inserted_rerun": (materialization or {}).get("inserted_rerun"),
            "plus_zero": (materialization or {}).get("plus_zero"),
            "execution": (materialization or {}).get("execution"),
        },
        "release": {
            "publication_id": build.publication_id if build else None,
            "descriptor": descriptor,
            "descriptor_sha256": descriptor_sha,
            "input_export_manifest_sha256": descriptor.get("input_manifest_sha256"),
            "export_manifest_sha256": export_manifest_sha,
            "release_manifest_sha256": build.manifest_sha256 if build else None,
            "compartments": (build.report.get("compartments") if build else []),
            "total_records": (build.report.get("records") if build else None),
            "validation_state": validation_state,
            "validation_ok": validation_state == "complete",
            "activated": False,
            "unpublished_by_construction": True,
        },
        "publication_pointer": {
            "before": staged.get("pointer_before"),
            "after": staged.get("pointer_after"),
            "unchanged": staged.get("pointer_unchanged"),
            "note": "latest.json was read before and after staging; the "
            "candidate never calls activate()/rollback()",
        },
        "disclosure": disclosure,
        "rollback_packet": rollback,
        "live_return_pass": return_pass,
        "deferral_dispositions": [
            {"id": "D-R10-HUMAN-1", "disposition": "amended_open", "note": EVAL_DEFERRAL_NOTE},
            {
                "id": "D-R6.1-EVAL",
                "disposition": "open",
                "note": "provisional rules remain active; the candidate pins "
                "them as provisional-ruleset/1",
            },
            {
                "id": "D-R10-LIVE-1",
                "disposition": "open",
                "note": "the production candidate still needs the hosted "
                "repaired spine — the return-pass packet pins it",
            },
            {
                "id": "D-R10-PUBLISH-1",
                "disposition": "open",
                "note": "publication needs P32.24 validation + GATE-G3 + P32.25",
            },
        ],
        "eval_disclosure": EVAL_DISCLOSURE,
    }


# ---------------------------------------------------------------------------
# Rendering + writing the packet.
# ---------------------------------------------------------------------------


def render_manifest_markdown(manifest: Mapping[str, Any]) -> str:
    c = manifest.get("candidate") or {}
    rel = manifest.get("release") or {}
    mat = manifest.get("materialization") or {}
    ptr = manifest.get("publication_pointer") or {}
    lines = [
        "# Release candidate manifest — P32.23a (`sig.candidate-manifest/1`)",
        "",
        "> **Unpublished.** Built under the active PROVISIONAL resolution policy;",
        "> the S3 human-evaluation spine is deferred — there is no final",
        "> evaluation decision. `eval-confidence/1` is shadow (`applied=[]`);",
        "> P32.10's confidence policy is not activated.",
        "",
        f"- identity digest: `{c.get('identity_digest')}`",
        f"- ruleset: `{c.get('ruleset_version')}`",
        f"- frozen snapshot: `{c.get('frozen_snapshot_digest')}`",
        f"- evaluation: **{c.get('evaluation_status')}** · policy "
        f"`{c.get('evaluation_policy')}` mode `{c.get('evaluation_mode')}`",
        f"- publication id (staged, NOT activated): `{rel.get('publication_id')}`",
        f"- release manifest: `{rel.get('release_manifest_sha256')}`",
        f"- descriptor sha256: `{rel.get('descriptor_sha256')}`",
        f"- validation ok: `{rel.get('validation_ok')}`",
        f"- records built: `{rel.get('total_records')}`",
        "",
        "## Materialization (dependency order)",
        "",
        f"- pass-1 inserted +{mat.get('inserted_pass_one')} · "
        f"rerun inserted +{mat.get('inserted_rerun')} · "
        f"**+0: {mat.get('plus_zero')}**",
        f"- order: {' → '.join(mat.get('dependency_order') or [])}",
        "",
        "## Publication pointer",
        "",
        f"- before: `{json.dumps(ptr.get('before'), sort_keys=True)}`",
        f"- after: `{json.dumps(ptr.get('after'), sort_keys=True)}`",
        f"- unchanged: `{ptr.get('unchanged')}`",
        "",
        "## Deferral dispositions",
        "",
    ]
    for d in manifest.get("deferral_dispositions") or []:
        lines.append(f"- **{d['id']}** — `{d['disposition']}` — {d['note']}")
    lines += ["", manifest.get("eval_disclosure", ""), ""]
    return "\n".join(lines)


def render_disclosure_markdown(d: Mapping[str, Any]) -> str:
    ch = d.get("change_disclosure") or {}
    su = d.get("suppression_disclosure") or {}
    rs = d.get("resolved_sites")
    lines = [
        "# Candidate disclosure — provisional / review-only",
        "",
        f"- identity `{d.get('candidate_identity_digest')}` · published: **{d.get('published')}**",
        f"- changes: {(ch.get('counts'))} · rerun +0 `{ch.get('rerun_plus_zero')}` "
        f"· rematerialization +0 `{ch.get('candidate_rematerialization_plus_zero')}`",
        f"- suppressions: {su.get('dispositions_recorded')} dispositions + "
        f"{(su.get('export_refused_totals') or {}).get('refused_slices', 0)} "
        "refused licence slices",
        f"- resolved sites: `{rs.get('value') if rs else 'none on this build'}`"
        + (f" ({rs.get('denominator')})" if rs else ""),
        f"- prior preview counts reused: **{d.get('prior_preview_counts_reused')}**",
        "",
        d.get("evaluation_disclosure", ""),
        "",
        d.get("statement", ""),
    ]
    return "\n".join(lines)


def render_rollback_markdown(p: Mapping[str, Any]) -> str:
    c = p.get("candidate") or {}
    rp = p.get("reversal_plan") or {}
    steps = "\n".join(f"1. {s}" for s in rp.get("steps") or [])
    pre = "\n".join(f"- {s}" for s in p.get("preconditions") or [])
    return (
        f"# Candidate rollback packet — `{p.get('rollback_version')}`\n\n"
        f"> Status: **{p.get('status')}** — the candidate is unpublished; this is\n"
        f"> a prepared pointer-reversal plan, not a mutation.\n\n"
        f"- publication `{c.get('publication_id')}` · manifest "
        f"`{str(c.get('release_manifest_sha256'))[:24]}…`\n"
        f"- pointer unchanged by this build: `{p.get('pointer_unchanged')}`\n\n"
        f"## Reversal\n\n{rp.get('mechanism')}\n\n{rp.get('if_no_prior_pointer')}\n\n"
        f"{steps}\n\n## Preconditions\n\n{pre}\n"
    )


def write_candidate_packet(
    out_dir: str | Path,
    *,
    manifest: Mapping[str, Any],
    disclosure: Mapping[str, Any],
    rollback: Mapping[str, Any],
    materialization: Mapping[str, Any],
    return_pass: Mapping[str, Any],
) -> dict[str, Path]:
    """Write the six packet artifacts + their markdown renderings."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    files = {
        "manifest": ("CANDIDATE_MANIFEST.json", manifest),
        "disclosure": ("DISCLOSURE.json", disclosure),
        "rollback": ("ROLLBACK_PACKET.json", rollback),
        "materialization": ("MATERIALIZATION.json", materialization),
        "return_pass": ("LIVE_RETURN_PASS.json", return_pass),
    }
    for key, (name, doc) in files.items():
        path = out / name
        _write_json(path, doc)
        paths[key] = path
    (out / "CANDIDATE_MANIFEST.md").write_text(render_manifest_markdown(manifest), encoding="utf-8")
    (out / "DISCLOSURE.md").write_text(render_disclosure_markdown(disclosure), encoding="utf-8")
    (out / "ROLLBACK_PACKET.md").write_text(render_rollback_markdown(rollback), encoding="utf-8")
    paths["manifest_md"] = out / "CANDIDATE_MANIFEST.md"
    paths["disclosure_md"] = out / "DISCLOSURE.md"
    paths["rollback_md"] = out / "ROLLBACK_PACKET.md"
    return paths


# ---------------------------------------------------------------------------
# The whole pipeline.
# ---------------------------------------------------------------------------


def run_candidate(
    conn: Any,
    *,
    snapshot: Mapping[str, Any],
    out_dir: str | Path,
    plan: Mapping[str, Any] | None = None,
    audit: Mapping[str, Any] | None = None,
    apply_report: Mapping[str, Any] | None = None,
    shadow_report: Mapping[str, Any] | None = None,
    registry_dir: str | Path | None = None,
    as_of: str | None = None,
    belief: Any = None,
    role: str | None = None,
    dossier_packets: Sequence[Mapping[str, Any]] | None = None,
    code_commit: str | None = None,
    sqitch_head: str | None = None,
    renderer_revision: str | None = None,
    export_subdir: str = "candidate_export",
    release_subdir: str = "candidate_release",
) -> dict[str, Any]:
    """Build the whole unpublished candidate packet; return the manifest + paths.

    Order (fail-closed at every seam):

    1. shadow-evaluator invariant + candidate identity;
    2. frozen population-frame verification — changed input stops;
    3. dependency-ordered rematerialization + `+0` rerun + appended completion;
    4. the licence-compartmented export under `provisional-ruleset/1`;
    5. the staged release namespace + validation (never `activate()`);
    6. disclosure + rollback packet + return-pass + the roll-up manifest.
    """
    out = Path(out_dir)
    export_dir = out / export_subdir
    release_dir = out / release_subdir

    identity = candidate_identity(
        snapshot=snapshot, shadow_report=shadow_report, code_commit=code_commit
    )
    identity_digest = str(identity["identity_digest"])
    snapshot_digest = _snapshot_digest(snapshot)
    plan_digest = None
    if plan:
        plan_digest = str(plan.get("plan_digest") or "") or None
    audit_digest = None
    if audit:
        inp = audit.get("input") or {}
        audit_digest = str(inp.get("population_digest") or "") or None

    frame_check = verify_population_frame(conn, snapshot)
    materialization = run_candidate_materialization(
        conn,
        identity_digest=identity_digest,
        snapshot_digest=snapshot_digest,
        plan_digest=plan_digest,
        role=role,
        code_commit=code_commit,
        sqitch_head=sqitch_head,
    )
    export = build_candidate_export(
        conn,
        as_of=as_of,
        belief=belief,
        dossier_packets=dossier_packets,
    )
    export.write_to(export_dir)
    export_manifest = json.loads((export_dir / "manifest.json").read_text(encoding="utf-8"))
    export_manifest_sha = (
        "sha256:" + hashlib.sha256((export_dir / "manifest.json").read_bytes()).hexdigest()
    )

    staged = stage_candidate_release(
        export_dir,
        release_dir,
        renderer_revision=renderer_revision or code_commit or "unknown",
        registry_dir=registry_dir,
    )
    staged["export_manifest_sha256"] = export_manifest_sha

    disclosure = build_disclosure(
        identity=identity,
        export_dir=export_dir,
        apply_report=apply_report,
        materialization=materialization,
        build_report=staged["build"].report,
    )
    disclosure_digest = _sha(_canonical(disclosure))
    rollback = build_rollback_packet(
        identity=identity,
        publication_id=staged["build"].publication_id,
        release_manifest_sha256=staged["build"].manifest_sha256,
        descriptor_sha256=_sha(_canonical(staged["build"].descriptor)),
        disclosure_digest=disclosure_digest,
        pointer_before=staged["pointer_before"],
        materialization=materialization,
    )
    return_pass = build_candidate_return_pass(
        identity_digest=identity_digest, snapshot_digest=snapshot_digest
    )
    dossier_packet_digests = {
        str(i): _sha(_canonical(p)) for i, p in enumerate(dossier_packets or [])
    }
    manifest = build_candidate_manifest(
        identity=identity,
        snapshot=snapshot,
        frame_check=frame_check,
        materialization=materialization,
        staged=staged,
        disclosure=disclosure,
        rollback=rollback,
        return_pass=return_pass,
        dossier_packet_digests=dossier_packet_digests,
        apply_report=apply_report,
        plan_digest=plan_digest,
        audit_digest=audit_digest,
    )
    manifest["export_manifest"] = export_manifest
    paths = write_candidate_packet(
        out,
        manifest=manifest,
        disclosure=disclosure,
        rollback=rollback,
        materialization=materialization,
        return_pass=return_pass,
    )
    manifest["_paths"] = {k: str(v) for k, v in paths.items()}
    return manifest
