# SPDX-License-Identifier: Apache-2.0
"""The P32.22 bounded-recovery-apply suite — offline half (SIG-TRUST-008).

Scope reconciliation is fail-closed (a plan built over a different audit, a
breached ceiling, or a non-proposed selection refuses before any write), the
selection filters are deterministic and recorded, the +0-replan and return-pass
artifacts keep their contract shape, and the provisional-vs-shadow report keeps
the PROVISIONAL production rules active with an empty applied set. The DB half
(real PostgreSQL) lives in tests/db/test_recovery_apply.py.
"""

from __future__ import annotations

import json
from pathlib import Path

from evidence.digest import multihash
from ops.evidence_audit import (
    CaptureRecord,
    ClaimBinding,
    ClaimUnit,
    FixtureCaptureProbe,
    run_audit,
)
from ops.recovery_apply import (
    ApplyScopeError,
    apply_selection_scoped_to,
    build_provisional_vs_shadow,
    reconcile_apply,
    render_shadow_markdown,
    select_actions,
    write_apply_return_pass,
    write_report,
)
from ops.recovery_plan import ActionKind, build_recovery_plan

POST = "2026-10-01T00:00:00Z"


def _bytes(t: str) -> bytes:
    return t.encode()


def _cap(text: str, **kw) -> CaptureRecord:
    digest = multihash(_bytes(text))
    base = dict(
        capture_id=f"cap-{text}",
        classification="actual",
        content_digest=digest,
        byte_size=len(_bytes(text)),
        ocfl_object_id=f"sig:capture:{digest}",
        ocfl_version="v1",
        storage_tier="public",
        retrieved_at=POST,
        retrieved_by_run_id="run-1",
        marks=(
            {
                "run_id": "run-1",
                "capture_digest": digest,
                "ocfl_object_id": f"sig:capture:{digest}",
                "ocfl_version": "v1",
                "retrieved_at": POST,
            },
        ),
    )
    base.update(kw)
    return CaptureRecord(**base)


def _bind(cap, **kw) -> ClaimBinding:
    base = dict(
        role="establishes",
        binding_status="document_only",
        locator={"kind": "byte_range", "start": 0, "end": 3},
        extractor_version="p/1",
        capture=cap,
    )
    base.update(kw)
    return ClaimBinding(**base)


def _unit(cid, bindings=(), **kw) -> ClaimUnit:
    base = dict(
        claim_id=cid,
        predicate_id="camera_location",
        source_id="atlas_registry",
        connector_name="atlas_registry",
        rights_spdx="CC-BY-4.0",
        compartment="cc_by",
        bindings=tuple(bindings),
        publication_eligible=True,
    )
    base.update(kw)
    return ClaimUnit(**base)


def _report(units, probe=None, **kw) -> dict:
    return run_audit(
        list(units),
        probe or FixtureCaptureProbe({}),
        seed="apply-test",
        sample_size=10_000,
        **kw,
    ).to_dict()


def _report_and_plan(units, probe=None, **plan_kw):
    report = _report(units, probe, adjudications={u.claim_id: "unresolved" for u in units})
    plan = build_recovery_plan(report, **plan_kw).to_dict()
    return report, plan


def _unrecoverable_plan():
    """A plan with two proposed record_disposition actions (unrecoverable
    eligible claims → withhold proposals) — the selectable write scope."""
    units = [
        _unit(
            "claim-miss-0",
            [_bind(_cap("gone-0", ocfl_object_id="sig:capture:absent-0", marks=()))],
        ),
        _unit(
            "claim-miss-1",
            [_bind(_cap("gone-1", ocfl_object_id="sig:capture:absent-1", marks=()))],
        ),
    ]
    return _report_and_plan(units, FixtureCaptureProbe({}))


def _unsupported_plan(repair: dict | None):
    """claim-unsupported has an unsupported_role_mapping flag → repair_claim +
    disposition when the adjudicator supplies instructions."""
    cap = _cap(
        "synth-cap",
        classification="synthetic",
        content_digest="",
        byte_size=0,
        ocfl_object_id=None,
        ocfl_version=None,
        marks=(),
    )
    unit = _unit(
        "claim-unsupported",
        [_bind(cap, binding_status="legacy_synthetic", locator=None, extractor_version=None)],
        predicate_id="camera_operator",
        object_entity="ent-flock",
    )
    repairs = {"claim-unsupported": repair} if repair else None
    return _report_and_plan([unit], FixtureCaptureProbe({}), repair_instructions=repairs)


# ---------------------------------------------------------------------------
# select_actions — the bounded selection contract
# ---------------------------------------------------------------------------


def test_select_only_proposed_write_kinds():
    _, plan = _unrecoverable_plan()
    sel = select_actions(plan)
    assert sel.actions, "the unrecoverable eligible claims must propose dispositions"
    for a in sel.actions:
        assert a["kind"] in {"record_disposition"}
        assert a["status"] == "proposed"
    reasons = {e["reason"] for e in sel.excluded}
    assert reasons == {"no_write"}
    # deterministic order — digest-sorted
    assert [a["action_digest"] for a in sel.actions] == sorted(
        a["action_digest"] for a in sel.actions
    )


def test_select_batch_filter():
    _, plan = _unrecoverable_plan()
    batches = {a["batch_id"] for a in plan["actions"] if a["batch_id"]}
    assert len(batches) >= 1
    sel = select_actions(plan, batches=[sorted(batches)[0]])
    assert {a["batch_id"] for a in sel.actions} == {sorted(batches)[0]}
    # A batch outside the plan selects nothing and records the exclusion.
    none_sel = select_actions(plan, batches=["batch-999"])
    assert not none_sel.actions
    assert any(e["reason"] == "batch_filter" for e in none_sel.excluded)


def test_select_kind_filter_excludes():
    _, plan = _unrecoverable_plan()
    sel = select_actions(plan, kinds=["repair_claim"])
    assert not sel.actions
    assert all(e["reason"] == "kind_filter" or e["reason"] == "no_write" for e in sel.excluded)
    assert any(e["reason"] == "kind_filter" for e in sel.excluded)


def test_select_claim_filter():
    _, plan = _unrecoverable_plan()
    claim_ids = sorted({a["claim_id"] for a in plan["actions"] if a["status"] == "proposed"})
    sel = select_actions(plan, claim_ids=[claim_ids[0]])
    assert {a["claim_id"] for a in sel.actions} == {claim_ids[0]}


def test_max_actions_is_an_abort_threshold():
    _, plan = _unrecoverable_plan()
    sel = select_actions(plan, max_actions=1)
    assert len(sel.actions) == 1
    assert sel.filters["truncated"] >= 1
    assert any(e["reason"] == "abort_threshold" for e in sel.excluded)


# ---------------------------------------------------------------------------
# reconcile_apply — fail-closed before any write
# ---------------------------------------------------------------------------


def test_reconcile_accepts_a_matching_plan():
    report, plan = _unrecoverable_plan()
    sel = select_actions(plan)
    assert reconcile_apply(plan, report, sel) == []


def test_reconcile_refuses_a_plan_over_a_different_population():
    report, plan = _unrecoverable_plan()
    other = dict(report)
    other["input"] = {**report["input"], "population_digest": "sha256:deadbeef"}
    problems = reconcile_apply(plan, other, select_actions(plan))
    assert any("population_digest" in p for p in problems)


def test_reconcile_refuses_a_wrong_plan_version():
    report, plan = _unrecoverable_plan()
    bad = dict(plan, plan_version="recovery-plan/0")
    problems = reconcile_apply(bad, report, select_actions(plan))
    assert any("plan_version" in p for p in problems)


def test_reconcile_refuses_a_breached_ceiling():
    report, plan = _unrecoverable_plan()
    bad = dict(plan)
    bad["ceilings"] = {**plan["ceilings"], "exceeds_ceiling": True}
    problems = reconcile_apply(bad, report, select_actions(plan))
    assert any("ceiling" in p for p in problems)


def test_reconcile_refuses_empty_scope():
    report, plan = _unrecoverable_plan()
    sel = select_actions(plan, kinds=["repair_claim"])
    problems = reconcile_apply(plan, report, sel)
    assert any("empty" in p for p in problems)


def test_apply_scope_error_is_the_refusal_type():
    assert issubclass(ApplyScopeError, Exception)


# ---------------------------------------------------------------------------
# Report + packet writers — the committed artifact shapes
# ---------------------------------------------------------------------------


def test_apply_report_renders_and_writes(tmp_path: Path):
    report = {
        "apply_version": "recovery-apply-report/1",
        "execution_id": "exec-test-1",
        "status": "complete",
        "authority": "op:fixture-auth",
        "decided_by": "operator:t",
        "pins": {
            "plan_digest": "sha256:x",
            "audit_input_digest": "sha256:y",
            "role": "sig_recovery",
        },
        "scope": {
            "selected_action_digests": ["a" * 64],
            "selected_kinds": ["record_disposition"],
            "batches": ["batch-001"],
            "claim_ids": ["c1"],
            "filters": {},
            "excluded": [],
            "dry_run_matches_applied": True,
        },
        "before": {
            "claims": 1,
            "claim_evidence": 1,
            "publication_disposition": 0,
            "recovery_application": 0,
            "ingest_run": 1,
        },
        "after": {
            "claims": 1,
            "claim_evidence": 1,
            "publication_disposition": 1,
            "recovery_application": 1,
            "ingest_run": 2,
        },
        "inventory_delta": {
            "claims": 0,
            "claim_evidence": 0,
            "publication_disposition": 1,
            "recovery_application": 1,
            "ingest_run": 1,
        },
        "results": [
            {
                "action_digest": "a" * 64,
                "kind": "record_disposition",
                "claim_id": "c1",
                "outcome": "applied",
                "result_claim_id": None,
                "disposition_id": "d-1",
                "binding_key": None,
                "run_id": "r-1",
                "detail": {},
            }
        ],
        "failures": [],
        "counts": {"applied": 1, "conflict_existing": 0, "already_applied": 0, "skipped": 0},
        "resource_use": {
            "wall_clock_seconds": 0.1,
            "workers": 1,
            "distinct_capture_bytes_reverified": [],
            "scoped_rows_inserted": 0,
            "scoped_bindings_inserted": 0,
            "dispositions_inserted": 1,
            "receipts_recorded": 1,
            "result_writes": {"claims": 0, "claim_evidence": 0, "publication_disposition": 1},
            "batch_bounds_respected": True,
            "ceilings": {},
        },
        "rerun": {
            "executed": True,
            "results": [],
            "all_already_applied": True,
            "inventory_delta_zero": True,
            "plus_zero": True,
        },
        "rematerialization": [],
        "no_refetch": "no fetch path exists",
        "provisional": True,
        "notes": [],
    }
    paths = write_report(report, tmp_path)
    doc = json.loads(paths["report"].read_text())
    assert doc["apply_version"] == "recovery-apply-report/1"
    assert doc["scope"]["dry_run_matches_applied"] is True
    md = paths["markdown"].read_text()
    assert "+0 rerun verified: True" in md
    assert "D-R10-LIVE-1" in md


def test_return_pass_packet_keeps_the_live_contract(tmp_path: Path):
    report = {
        "execution_id": "exec-test-2",
        "pins": {"plan_digest": "sha256:p", "audit_input_digest": "sha256:a"},
        "counts": {"applied": 2},
        "resource_use": {"ceilings": {"max_assertions": 10_000}},
    }
    paths = write_apply_return_pass(tmp_path, apply_report=report, snapshot=None)
    packet = json.loads(paths["packet"].read_text())
    assert packet["packet_version"] == "recovery-apply-return-pass/1"
    assert packet["status"] == "prepared_not_executed"
    assert any("D-R10-LIVE-1" in r for r in packet["explicit_reservations"])
    assert any("P32.23a" in r for r in packet["explicit_reservations"])
    assert any("recovery-apply" in c["command"] for c in packet["commands"])
    assert any("recovery-freeze" in c["command"] for c in packet["commands"])
    md = paths["markdown"].read_text()
    assert "prepared" in md and "OPEN" in md


def test_provisional_vs_shadow_report_shape():
    report = build_provisional_vs_shadow(code_commit="abc123")
    assert report["report_version"] == "sig.provisional-vs-shadow/1"
    assert report["shadow_evaluator"]["mode"] == "shadow"
    assert report["shadow_evaluator"]["applied"] == []
    assert report["safety_demotions_scoped"] == []
    rules = {r["rule"] for r in report["active_provisional_rules"]}
    assert any("camera" in r for r in rules)
    for r in report["active_provisional_rules"]:
        assert "PROVISIONAL" in r["status"]
        assert "D-R6.1-EVAL" in r["deferral"]
    md = render_shadow_markdown(report)
    assert "computed, never applied" in md
    assert "none" in md


# ---------------------------------------------------------------------------
# The CLI dry-reconcile path (no DSN needed — the default is zero writes)
# ---------------------------------------------------------------------------


def test_cli_recovery_apply_dry_reconcile(tmp_path: Path, capsys):
    from ops.cli import main

    report, plan = _unrecoverable_plan()
    (tmp_path / "audit_report.json").write_text(json.dumps(report))
    (tmp_path / "recovery_plan.json").write_text(json.dumps(plan))
    rc = main(
        [
            "recovery-apply",
            "--plan",
            str(tmp_path / "recovery_plan.json"),
            "--audit",
            str(tmp_path / "audit_report.json"),
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "dry reconcile" in out
    assert "selected" in out


def test_cli_recovery_apply_refuses_a_mismatched_plan(tmp_path: Path, capsys):
    from ops.cli import main

    report, plan = _unrecoverable_plan()
    bad = dict(report)
    bad["input"] = {**report["input"], "population_digest": "sha256:ffff"}
    (tmp_path / "audit_report.json").write_text(json.dumps(bad))
    (tmp_path / "recovery_plan.json").write_text(json.dumps(plan))
    rc = main(
        [
            "recovery-apply",
            "--plan",
            str(tmp_path / "recovery_plan.json"),
            "--audit",
            str(tmp_path / "audit_report.json"),
        ]
    )
    assert rc == 3
    assert "REFUSED" in capsys.readouterr().err


def test_cli_recovery_apply_requires_authority(tmp_path: Path, capsys):
    from ops.cli import main

    report, plan = _unrecoverable_plan()
    (tmp_path / "audit_report.json").write_text(json.dumps(report))
    (tmp_path / "recovery_plan.json").write_text(json.dumps(plan))
    rc = main(
        [
            "recovery-apply",
            "--plan",
            str(tmp_path / "recovery_plan.json"),
            "--audit",
            str(tmp_path / "audit_report.json"),
            "--apply",
            "--execution-id",
            "exec-1",
        ]
    )
    assert rc == 2
    assert "authority" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Repair path — the planner's repair proposal carries the adjudicator fields
# ---------------------------------------------------------------------------


def test_repair_proposal_carries_adjudicator_fields():
    repair = {
        "revised_fields": {"value_text": "corrected", "raw_value": "corrected-raw"},
        "basis": "adjudicator: the unsupported operator role is a repair",
        "locator": {"kind": "byte_range", "start": 0, "end": 8},
    }
    _, plan = _unsupported_plan(repair)
    kinds = {a["kind"] for a in plan["actions"]}
    assert ActionKind.REPAIR_CLAIM.value in kinds
    repair_action = next(a for a in plan["actions"] if a["kind"] == "repair_claim")
    assert repair_action["status"] == "proposed"
    assert repair_action["proposed_row"]["revises_claim"] == "claim-unsupported"
    assert repair_action["proposed_row"]["revised_fields"]["value_text"] == "corrected"
    assert repair_action["proposed_row"]["correction_reason"] == "evidence_audit_unsupported_role"
    assert repair_action["provenance"]["adjudicator_basis"] == repair["basis"]


def test_no_repair_without_adjudicator_instructions():
    _, plan = _unsupported_plan(None)
    repair = [a for a in plan["actions"] if a["kind"] == "repair_claim"]
    assert not repair, "an unsupported role must stay a finding, never a silent repair"


def test_selection_covers_repair_and_disposition():
    repair = {
        "revised_fields": {"value_text": "corrected"},
        "basis": "adjudicator basis",
        "locator": {},
    }
    _, plan = _unsupported_plan(repair)
    sel = select_actions(plan)
    kinds = {a["kind"] for a in sel.actions}
    assert "repair_claim" in kinds
    assert "record_disposition" in kinds


# apply_selection_scoped_to is exercised in tests/db; here assert it exists.
def test_apply_selection_helper_exists():
    assert callable(apply_selection_scoped_to)
