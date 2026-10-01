# SPDX-License-Identifier: Apache-2.0
"""The bounded recovery apply (P32.22, SIG-TRUST-008, ADR-141) — real-PG suite.

Docker-gated: seeds the committed P32.6 fixture into a fully deployed spine
(sqitch plan through ``recovery_apply``), rebuilds the audit + plan over the
REAL rows, then asserts the whole exactly-once / bounded / fail-closed contract:

* dry-run ↔ applied scope match (only ``proposed`` actions, digest-for-digest);
* per-action atomic receipt — a restart reconciles ``already_applied``, never a
  duplicate repair; a re-plan over recorded digests proposes +0;
* record_disposition writes through the shared policy validator with the
  operator authority (the plan's placeholder never lands);
* repair_claim performs the §16.6 pair — the prior claim's ``sys_period``
  closes and a NEW ``revises_claim`` row carries the adjudicated fields;
* bind_verified_capture re-verifies bytes before insert and the
  ``(claim_id,capture_id,role)`` PK deduplicates honestly
  (``conflict_existing`` — never an invented row, never an UPDATE);
* missing/unverifiable bytes skip the bind — there is no fetch path to invoke;
* ``sig_recovery`` is least-privilege: the receipt + narrow writes land while
  every other mutation (non-sys_period UPDATE, DELETE, capture/extraction/
  blob inserts) is refused;
* a second full run reports +0; rematerialization runs in dependency order;
* the frozen snapshot is explicitly ``frozen_unpublished`` + provisional.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.usefixtures("sig_database")

FIXTURE_DIR = (
    Path(__file__).resolve().parents[2] / "docs" / "build" / "reports" / "p32.6-legacy-evidence"
)


def _seeded(conn):
    """Seed the fixture + return the id map."""
    from ops.recovery_fixture import seed_fixture_spine

    return seed_fixture_spine(conn, FIXTURE_DIR)


def _audit(conn, id_map):
    """Re-run the audit over the REAL seeded rows (the same call the CLI makes)."""
    from db.evidence_audit import load_audit_input
    from evidence.ocfl import OcflStore
    from evidence.storage import LocalFileStore

    from ops import evidence_audit as ea

    claim_ids = sorted(id_map["claims"].values())
    load = load_audit_input(conn, claim_ids=claim_ids)
    units = ea.units_from_rows(load.rows, load.marks, load.eligible_claim_ids)
    probe = ea.OcflCaptureProbe(
        OcflStore(LocalFileStore(str(id_map["capture_root"]))),
        root_desc=str(id_map["capture_root"]),
    )
    report = ea.run_audit(
        units,
        probe,
        seed="p32.22-fixture-seed-v1",
        sample_size=16,
        targeted_ids=list(id_map["targeted_ids"].values()),
        adjudications=dict(id_map["adjudications"]),
        watermark=load.watermark,
        input_source="test-pg",
        generated_at=None,
    )
    return report.to_dict(), probe, load


def _plan(audit_dict, id_map):
    """The plan with adjudicator repair instructions for the unsupported unit."""
    from ops.recovery_plan import build_recovery_plan

    unsupported = id_map["claims"]["claim-unsupported-0"]
    repairs = {
        unsupported: {
            "revised_fields": {
                "value_text": "adjudicated-operator",
                "raw_value": "adjudicated-raw",
            },
            "basis": "fixture adjudicator: unsupported operator-role claim repaired",
            "locator": {"kind": "byte_range", "start": 0, "end": 4},
        }
    }
    return build_recovery_plan(audit_dict, repair_instructions=repairs).to_dict()


def _apply_kwargs():
    return dict(
        execution_id="exec-p32-22-test",
        authority="op:test-authority/P32.22",
        decided_by="operator:test",
        adjudicator="fixture-adjudicator",
    )


# ---------------------------------------------------------------------------
# The end-to-end bounded apply
# ---------------------------------------------------------------------------


def test_apply_records_scope_match_dispositions_and_repair(conn):
    from ops.recovery_apply import execute_bounded_apply

    id_map = _seeded(conn)
    audit, probe, _ = _audit(conn, id_map)
    plan = _plan(audit, id_map)

    report = execute_bounded_apply(
        conn, plan, audit, probe=probe, verify_rerun=True, **_apply_kwargs()
    )
    assert report["status"] == "complete"
    assert report["scope"]["dry_run_matches_applied"] is True
    # every executed action was a plan-proposed action — digest-for-digest
    proposed = {a["action_digest"] for a in plan["actions"] if a["status"] == "proposed"}
    assert set(report["scope"]["selected_action_digests"]) == proposed
    counts = report["counts"]
    assert counts["applied"] >= 4, counts  # 3 dispositions + 1 repair
    assert report["rerun"]["plus_zero"] is True

    # The dispositions landed with the OPERATOR authority, never the placeholder.
    rows = conn.execute(
        "SELECT target_id, disposition, reason_category, authority "
        "FROM publication_disposition ORDER BY disposition_seq"
    ).fetchall()
    assert len(rows) == 3
    assert all(r[1] == "withhold" and r[2] == "pending_publication_review" for r in rows)
    assert all("P32.22" in r[3] for r in rows)
    assert all("requires P32.22" not in r[3] for r in rows)

    # The repair is a §16.6 pair: old claim closed, NEW row carries the fields.
    unsupported = id_map["claims"]["claim-unsupported-0"]
    repaired = conn.execute(
        "SELECT claim_id::text, value_text, revises_claim::text, correction_reason "
        "FROM claim WHERE revises_claim = %s::uuid",
        (unsupported,),
    ).fetchone()
    assert repaired is not None, "the corrected claim must be a NEW row"
    assert repaired[1] == "adjudicated-operator"
    assert repaired[2] == unsupported
    assert repaired[3] == "evidence_audit_unsupported_role"
    closed = conn.execute(
        "SELECT upper_inf(sys_period) FROM claim WHERE claim_id = %s::uuid",
        (unsupported,),
    ).fetchone()
    assert closed[0] is False, "the old claim's sys_period must be closed"
    # The new claim inherits the SAME captures (the corrected reading stands
    # on the same evidence).
    rebound = conn.execute(
        "SELECT count(*) FROM claim_evidence WHERE claim_id = %s::uuid",
        (repaired[0],),
    ).fetchone()[0]
    assert rebound == 1

    # Receipts: one per action, keyed by action_digest, ingested into a run.
    receipts = conn.execute(
        "SELECT action_digest, kind, outcome, authority FROM recovery_application "
        "ORDER BY action_digest"
    ).fetchall()
    assert {r[0] for r in receipts} == proposed
    assert all(r[3] == "op:test-authority/P32.22" for r in receipts)


def test_restart_reconciles_already_applied_never_duplicates(conn):
    """An interrupted applier re-running the same actions reconciles to the
    recorded receipts — the UNIQUE(action_digest) barrier forbids a second
    canonical write AND a second receipt."""
    from db.recovery_apply import PgRecoveryApplier, applied_digests, inventory
    from ops.recovery_apply import execute_bounded_apply

    id_map = _seeded(conn)
    audit, probe, _ = _audit(conn, id_map)
    plan = _plan(audit, id_map)
    execute_bounded_apply(conn, plan, audit, probe=probe, **_apply_kwargs())

    before = inventory(conn, claim_ids=list(id_map["claims"].values()))
    applier = PgRecoveryApplier(conn, **_apply_kwargs())
    results = applier.apply_plan([a for a in plan["actions"] if a["status"] == "proposed"])
    assert all(r.outcome.value == "already_applied" for r in results)
    after = inventory(conn, claim_ids=list(id_map["claims"].values()))
    assert before == after, "a restart must be a strict no-write reconcile"
    # the recorded digests are exactly the proposed set
    assert applied_digests(conn) == {
        a["action_digest"] for a in plan["actions"] if a["status"] == "proposed"
    }


def test_replan_over_recorded_digests_proposes_plus_zero(conn):
    from db.recovery_apply import applied_digests
    from ops.recovery_apply import execute_bounded_apply
    from ops.recovery_plan import build_recovery_plan

    id_map = _seeded(conn)
    audit, probe, _ = _audit(conn, id_map)
    plan = _plan(audit, id_map)
    execute_bounded_apply(conn, plan, audit, probe=probe, **_apply_kwargs())

    unsupported = id_map["claims"]["claim-unsupported-0"]
    repairs = {  # identical to _plan — a DIFFERENT adjudication is a NEW action
        unsupported: {
            "revised_fields": {
                "value_text": "adjudicated-operator",
                "raw_value": "adjudicated-raw",
            },
            "basis": "fixture adjudicator: unsupported operator-role claim repaired",
            "locator": {"kind": "byte_range", "start": 0, "end": 4},
        }
    }
    replan = build_recovery_plan(
        audit,
        applied_digests=applied_digests(conn),
        repair_instructions=repairs,
    ).to_dict()
    statuses = {a["status"] for a in replan["actions"]}
    assert "proposed" not in statuses, "a +0 re-plan must propose no writes"
    assert "already_applied" in statuses


def test_second_execution_is_plus_zero(conn):
    from db.recovery_apply import inventory
    from ops.recovery_apply import execute_bounded_apply

    id_map = _seeded(conn)
    audit, probe, _ = _audit(conn, id_map)
    plan = _plan(audit, id_map)
    execute_bounded_apply(conn, plan, audit, probe=probe, **_apply_kwargs())
    before = inventory(conn, claim_ids=list(id_map["claims"].values()))
    report2 = execute_bounded_apply(
        conn, plan, audit, probe=probe, verify_rerun=True, **_apply_kwargs()
    )
    after = inventory(conn, claim_ids=list(id_map["claims"].values()))
    assert report2["counts"]["already_applied"] == len(report2["scope"]["selected_action_digests"])
    assert before == after


# ---------------------------------------------------------------------------
# The least-privilege role
# ---------------------------------------------------------------------------


def test_sig_recovery_is_refused_everything_outside_its_write_surface(conn):
    """Under SET LOCAL ROLE sig_recovery, every mutation outside the narrow
    grant list is refused — by privilege AND by the append-only triggers."""
    _seeded(conn)
    for sql in (
        "UPDATE claim SET raw_value = 'nope'",
        "DELETE FROM claim",
        "DELETE FROM claim_evidence",
        "UPDATE claim_evidence SET binding_status = 'replayed'",
        "UPDATE recovery_application SET outcome = 'applied'",
        "DELETE FROM recovery_application",
        "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,"
        " media_type,retrieved_at,retrieved_by_run_id,ocfl_object_id,"
        " ocfl_version,capture_method,capture_tool_version)"
        " VALUES(uuidv7(),'x',1,'t',clock_timestamp(),uuidv7(),'o','v1','m','v')",
        "INSERT INTO evidence_blob(blob_digest,source_uri,byte_size,"
        " ocfl_object_id,ocfl_version) VALUES('x','y',1,'o','v1')",
    ):
        import psycopg

        with pytest.raises(psycopg.Error), conn.transaction():
            conn.execute("SET LOCAL ROLE sig_recovery")
            conn.execute(sql)


def test_sig_recovery_writes_through_its_surface(conn):
    """The positive half: the role performs a real disposition + receipt via the
    applier path (privilege-granted), reading the claim it targets through the
    sealed-reader membership."""
    from db.recovery_apply import PgRecoveryApplier

    id_map = _seeded(conn)
    action = _craft_action(
        id_map["claims"]["claim-rec-0"],
        "record_disposition",
        {
            "target_kind": "claim",
            "target_id": id_map["claims"]["claim-rec-0"],
            "disposition": "withhold",
            "reason_category": "pending_publication_review",
            "rationale": "role-surface test",
        },
        digest_seed="disp-role-1",
    )
    applier = PgRecoveryApplier(conn, role="sig_recovery", **_apply_kwargs())
    result = applier.apply_action(action)
    assert result.outcome.value == "applied"
    row = conn.execute(
        "SELECT authority, reason_category FROM publication_disposition"
        " WHERE disposition_id = %s::uuid",
        (result.disposition_id,),
    ).fetchone()
    assert row[0] == "op:test-authority/P32.22"


def test_marker_is_append_only(conn):
    from ops.recovery_apply import execute_bounded_apply

    id_map = _seeded(conn)
    audit, probe, _ = _audit(conn, id_map)
    plan = _plan(audit, id_map)
    execute_bounded_apply(conn, plan, audit, probe=probe, **_apply_kwargs())
    import psycopg

    with pytest.raises(psycopg.Error), conn.transaction():
        conn.execute("UPDATE recovery_application SET outcome = 'applied'")
    with pytest.raises(psycopg.Error), conn.transaction():
        conn.execute("DELETE FROM recovery_application")
    # the receipt rows are still there (statement-level abort rolled back)
    n = conn.execute("SELECT count(*) FROM recovery_application").fetchone()[0]
    assert n >= 4


# ---------------------------------------------------------------------------
# Per-action honesty: bind conflict / missing bytes / Part VIII / scope
# ---------------------------------------------------------------------------


def _craft_action(claim_id: str, kind: str, proposed_row: dict, *, digest_seed: str) -> dict:
    import hashlib

    return {
        "action_digest": hashlib.sha256(digest_seed.encode()).hexdigest(),
        "kind": kind,
        "status": "proposed",
        "claim_id": claim_id,
        "proposed_row": proposed_row,
        "provenance": {},
        "batch_id": "batch-001",
    }


def test_bind_on_already_bound_capture_records_conflict_existing(conn):
    from db.recovery_apply import PgRecoveryApplier

    id_map = _seeded(conn)
    claim_id = id_map["claims"]["claim-rec-0"]
    capture_id = id_map["captures"]["cap-r0"]
    # claim-rec-0 ALREADY binds cap-r0 under 'establishes' — the PK deduplicates.
    action = _craft_action(
        claim_id,
        "bind_verified_capture",
        {
            "claim_id": claim_id,
            "capture_id": capture_id,
            "role": "establishes",
            "binding_status": "replayed",
            "locator": {"kind": "byte_range", "start": 0, "end": 4},
        },
        digest_seed="bind-conflict-1",
    )
    applier = PgRecoveryApplier(conn, **_apply_kwargs())
    result = applier.apply_action(action)
    assert result.outcome.value == "conflict_existing"
    assert result.detail["untyped_existing"] is False
    n = conn.execute(
        "SELECT count(*) FROM claim_evidence WHERE claim_id = %s::uuid",
        (claim_id,),
    ).fetchone()[0]
    assert n == 1, "no duplicate row, and never an UPDATE of the immutable link"


def test_bind_of_a_new_role_pair_applies(conn):
    from db.recovery_apply import PgRecoveryApplier

    id_map = _seeded(conn)
    claim_id = id_map["claims"]["claim-rec-0"]
    capture_id = id_map["captures"]["cap-r1"]  # bound to a DIFFERENT claim
    action = _craft_action(
        claim_id,
        "bind_verified_capture",
        {
            "claim_id": claim_id,
            "capture_id": capture_id,
            "role": "corroborates",
            "binding_status": "replayed",
            "locator": None,
        },
        digest_seed="bind-new-1",
    )
    applier = PgRecoveryApplier(conn, **_apply_kwargs())
    result = applier.apply_action(action)
    assert result.outcome.value == "applied"
    n = conn.execute(
        "SELECT count(*) FROM claim_evidence WHERE claim_id = %s::uuid"
        " AND capture_id = %s::uuid AND role = 'corroborates'",
        (claim_id, capture_id),
    ).fetchone()[0]
    assert n == 1


def test_bind_to_a_dangling_capture_refuses(conn):
    import uuid

    from db.recovery_apply import PgRecoveryApplier, RecoveryApplyError

    id_map = _seeded(conn)
    action = _craft_action(
        id_map["claims"]["claim-rec-0"],
        "bind_verified_capture",
        {
            "claim_id": id_map["claims"]["claim-rec-0"],
            "capture_id": str(uuid.uuid4()),
            "role": "establishes",
        },
        digest_seed="bind-dangling-1",
    )
    applier = PgRecoveryApplier(conn, **_apply_kwargs())
    with pytest.raises(RecoveryApplyError) as excinfo:
        applier.apply_action(action)
    assert excinfo.value.code == "capture_missing"


def test_missing_bytes_skip_never_fetch(conn):
    """A bind whose pinned bytes cannot be re-verified is SKIPPED — no write,
    and the applier holds no fetch/transport code to call."""
    from db.evidence_audit import load_audit_input
    from ops.recovery_apply import execute_bounded_apply

    from ops import evidence_audit as ea

    id_map = _seeded(conn)
    claim_ids = sorted(id_map["claims"].values())
    load = load_audit_input(conn, claim_ids=claim_ids)
    units = ea.units_from_rows(load.rows, load.marks, load.eligible_claim_ids)
    audit = ea.run_audit(
        units,
        ea.NULL_PROBE,  # no root mounted — nothing can verify
        seed="p32.22-skip-test",
        sample_size=16,
        adjudications=dict(id_map["adjudications"]),
        input_source="test-pg",
        generated_at=None,
    ).to_dict()
    # Craft a bind action over the real capture whose object id is known.
    capture_id = id_map["captures"]["cap-r1"]
    plan = {
        "plan_version": "recovery-plan/1",
        "input": {"audit_report_input": {"population_digest": audit["input"]["population_digest"]}},
        "ceilings": {"exceeds_ceiling": False},
        "batches": [
            {
                "batch_id": "batch-001",
                "actions": [],
                "write_actions": 0,
                "distinct_capture_bytes": 0,
            }
        ],
        "actions": [
            _craft_action(
                id_map["claims"]["claim-rec-1"],
                "bind_verified_capture",
                {
                    "claim_id": id_map["claims"]["claim-rec-1"],
                    "capture_id": capture_id,
                    "role": "corroborates",
                    "binding_status": "replayed",
                },
                digest_seed="bind-nullprobe-1",
            )
        ],
    }
    report = execute_bounded_apply(
        conn,
        plan,
        audit,
        probe=ea.NULL_PROBE,
        execution_id="exec-skip",
        authority="op:test-authority/P32.22",
    )
    assert report["results"][0]["outcome"] == "skipped"
    assert report["results"][0]["reason"] == "bytes_not_reverified"
    assert not conn.execute(
        "SELECT 1 FROM claim_evidence WHERE claim_id = %s::uuid AND role = 'corroborates'",
        (id_map["claims"]["claim-rec-1"],),
    ).fetchone(), "unverified bytes never produce a row — and nothing fetched"


def test_repair_refuses_part_viii_payloads(conn):
    from db.recovery_apply import PgRecoveryApplier, RecoveryApplyError

    id_map = _seeded(conn)
    claim_id = id_map["claims"]["claim-rec-0"]
    action = _craft_action(
        claim_id,
        "repair_claim",
        {
            "revises_claim": claim_id,
            "revised_fields": {"value_text": "SSN 123-45-6789"},
            "correction_reason": "x",
        },
        digest_seed="repair-unsafe-1",
    )
    applier = PgRecoveryApplier(conn, **_apply_kwargs())
    with pytest.raises(RecoveryApplyError) as excinfo:
        applier.apply_action(action)
    assert excinfo.value.code == "unsafe_payload"


def test_repair_refuses_fields_outside_the_allowlist(conn):
    from db.recovery_apply import PgRecoveryApplier, RecoveryApplyError

    id_map = _seeded(conn)
    claim_id = id_map["claims"]["claim-rec-0"]
    action = _craft_action(
        claim_id,
        "repair_claim",
        {
            "revises_claim": claim_id,
            "revised_fields": {"subject_id": "11111111-1111-1111-1111-111111111111"},
            "correction_reason": "x",
        },
        digest_seed="repair-subject-1",
    )
    applier = PgRecoveryApplier(conn, **_apply_kwargs())
    with pytest.raises(RecoveryApplyError) as excinfo:
        applier.apply_action(action)
    assert excinfo.value.code == "revised_field_out_of_scope"


def test_non_proposed_actions_are_never_writable(conn):
    from db.recovery_apply import PgRecoveryApplier, RecoveryApplyError

    id_map = _seeded(conn)
    action = _craft_action(
        id_map["claims"]["claim-rec-0"],
        "bind_verified_capture",
        {"capture_id": id_map["captures"]["cap-r0"], "role": "establishes"},
        digest_seed="bind-status-1",
    )
    action["status"] = "already_applied"
    applier = PgRecoveryApplier(conn, **_apply_kwargs())
    with pytest.raises(RecoveryApplyError) as excinfo:
        applier.apply_action(action)
    assert excinfo.value.code == "not_proposed"


# ---------------------------------------------------------------------------
# Rematerialization + the frozen snapshot
# ---------------------------------------------------------------------------


def test_rematerialize_runs_in_dependency_order(conn):
    from ops.recovery_apply import REMATERIALIZE_ORDER, execute_bounded_apply

    id_map = _seeded(conn)
    audit, probe, _ = _audit(conn, id_map)
    plan = _plan(audit, id_map)
    report = execute_bounded_apply(
        conn,
        plan,
        audit,
        probe=probe,
        rematerialize=True,
        **_apply_kwargs(),
    )
    steps = report["rematerialization"]
    assert [s["step"] for s in steps] == list(REMATERIALIZE_ORDER)
    assert [s["order"] for s in steps] == [1, 2, 3, 4, 5, 6]
    for s in steps:
        assert "error" not in s, f"{s['step']} errored: {s.get('error')}"
        assert s["inserted"] >= 0


def test_freeze_snapshot_is_unpublished_and_provisional(conn, tmp_path):
    from ops.recovery_apply import execute_bounded_apply, freeze_snapshot

    id_map = _seeded(conn)
    audit, probe, _ = _audit(conn, id_map)
    plan = _plan(audit, id_map)
    apply_report = execute_bounded_apply(conn, plan, audit, probe=probe, **_apply_kwargs())

    snapshot = freeze_snapshot(
        conn,
        apply_report=apply_report,
        plan=plan,
        audit=audit,
        probe=probe,
        targeted_ids=list(id_map["targeted_ids"].values()),
        adjudications=dict(id_map["adjudications"]),
        out_dir=tmp_path,
    )
    assert snapshot["snapshot_version"] == "sig.repaired-snapshot/1"
    assert snapshot["status"] == "frozen_unpublished"
    assert snapshot["provisional_preview"] is True
    assert snapshot["not_a_release_candidate"] is True
    assert snapshot["owned_next"] == "HUMAN-H4"
    assert snapshot["population_frame"]["claim_count"] == 16
    # The 3 withheld claims left the eligible set — recorded, not hidden.
    assert len(snapshot["population_frame"]["eligible_claim_ids"]) == 13
    repaired = snapshot["applied"]["repaired_claim_ids"]
    assert repaired, "the repair claim id must be recorded"
    # artifact files
    doc = json.loads((tmp_path / "REPAIRED_SNAPSHOT.json").read_text())
    assert doc["snapshot_digest"].startswith("sha256:")
    preview = (tmp_path / "AUDIT_PREVIEW.md").read_text()
    assert "PROVISIONAL PREVIEW" in preview
    assert "not a release candidate" in preview
