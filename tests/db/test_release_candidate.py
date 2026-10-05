# SPDX-License-Identifier: Apache-2.0
"""The P32.23a post-evaluation release candidate (SIG-TRUST-010, ADR-142) —
real-PG suite.

Docker-gated: rebuilds the P32.22 fixture stage on a fully deployed spine
(seed → audit → plan → bounded apply → frozen snapshot), then runs the
candidate pipeline end-to-end and asserts:

* the frozen population frame reconciles — a changed input STOPS the build
  (missing claim, drifted eligibility semantics);
* the rematerialization runs in the recorded dependency order and the rerun
  is +0, with the execution completion appended to spine history;
* every artifact cites ONE candidate identity — provisional ruleset + frozen
  snapshot digest + evaluation ``deferred`` under ``eval-confidence/1``
  ``shadow`` (``applied=[]``), the deferral disclosed inside the namespace;
* the release namespace validates as complete while the publication pointer
  stays byte-identical — the candidate is unpublished by construction;
* the disclosure is provisional/review-only, quotes no prior preview count,
  and records the change + suppression + evaluation facts.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.usefixtures("sig_database")

FIXTURE_DIR = (
    Path(__file__).resolve().parents[2] / "docs" / "build" / "reports" / "p32.6-legacy-evidence"
)
P32_22_DIR = (
    Path(__file__).resolve().parents[2] / "docs" / "build" / "reports" / "p32.22-bounded-recovery"
)


def _seeded(conn):
    from ops.recovery_fixture import seed_fixture_spine

    return seed_fixture_spine(conn, FIXTURE_DIR)


def _audit(conn, id_map):
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
        execution_id="exec-p32-23a-test",
        authority="op:test-authority/P32.23a",
        decided_by="operator:test",
        adjudicator="fixture-adjudicator",
    )


def _repaired_spine(conn, tmp_path):
    """Rebuild the P32.22 fixture stage: seed → audit → plan → apply → freeze."""
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
    return {
        "id_map": id_map,
        "audit": audit,
        "plan": plan,
        "apply_report": apply_report,
        "snapshot": snapshot,
    }


# ---------------------------------------------------------------------------
# The happy path — one unpublished candidate, one identity, +0 proven.
# ---------------------------------------------------------------------------


def test_candidate_builds_one_unpublished_release(conn, tmp_path):
    from ops.recovery_apply import REMATERIALIZE_ORDER

    from ops import release_candidate as rc

    stage = _repaired_spine(conn, tmp_path / "stage")
    registry = tmp_path / "registry"
    registry.mkdir()
    out = tmp_path / "candidate"

    manifest = rc.run_candidate(
        conn,
        snapshot=stage["snapshot"],
        out_dir=out,
        plan=stage["plan"],
        audit=stage["audit"],
        apply_report=stage["apply_report"],
        registry_dir=registry,
        as_of="2026-10-19",
        code_commit="test-commit",
    )

    cand = manifest["candidate"]
    assert cand["published"] is False
    assert cand["ruleset_version"] == rc.PROVISIONAL_RULESET
    assert cand["evaluation_status"] == "deferred"
    assert cand["evaluation_policy"] == "eval-confidence/1"
    assert cand["evaluation_mode"] == "shadow"
    assert cand["frozen_snapshot_digest"] == stage["snapshot"]["snapshot_digest"]
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", cand["identity_digest"])

    # --- +0 rematerialization in dependency order -------------------------- #
    mat = manifest["materialization"]
    assert mat["dependency_order"] == list(REMATERIALIZE_ORDER)
    assert mat["inserted_rerun"] == 0
    assert mat["plus_zero"] is True
    # the execution completion was appended to spine history
    run_row = conn.execute(
        "SELECT connector_name, connector_version, ruleset_version, status "
        "FROM ingest_run WHERE run_id = %s::uuid",
        (mat["execution"]["ingest_run_id"],),
    ).fetchone()
    assert run_row[0] == "sig.release-candidate"
    assert run_row[1] == rc.CANDIDATE_VERSION
    assert run_row[2] == rc.PROVISIONAL_RULESET
    completion = conn.execute(
        "SELECT status, claims_inserted FROM ingest_run_completion WHERE run_id = %s::uuid",
        (mat["execution"]["ingest_run_id"],),
    ).fetchone()
    assert completion[0] == "ok"
    assert completion[1] == mat["inserted_pass_one"]

    # --- the staged release namespace validates; identity agrees everywhere - #
    rel = manifest["release"]
    assert rel["unpublished_by_construction"] is True
    assert rel["activated"] is False
    assert rel["validation_ok"] is True
    assert re.fullmatch(r"p-[0-9a-f]{64}", rel["publication_id"])
    # cross-artifact identity: descriptor ruleset == candidate ruleset
    assert rel["descriptor"]["ruleset_version"] == rc.PROVISIONAL_RULESET
    descriptor = json.loads(
        (
            out / "candidate_release" / "releases" / rel["publication_id"] / "descriptor.json"
        ).read_text()
    )
    assert descriptor["ruleset_version"] == rc.PROVISIONAL_RULESET
    export_manifest = json.loads((out / "candidate_export" / "manifest.json").read_text())
    assert export_manifest["reproducibility_inputs"]["ruleset_version"] == rc.PROVISIONAL_RULESET

    # --- the deferral is disclosed inside the emitted bytes ---------------- #
    exclusions = json.loads((out / "candidate_export" / "exclusions.json").read_text())
    assert "deferred" in exclusions["note"]
    assert "no final evaluation decision" in exclusions["note"]
    # the provisional basis is stamped inside the analytics payload too — the
    # ruleset identity is the provisional-ruleset/1 string, not a hidden footnote
    analytics_prov = json.loads(
        (out / "candidate_export" / "web" / "analytics" / "provenance.json").read_text()
    )
    assert "provisional-ruleset/1" in json.dumps(analytics_prov)

    # --- unpublished: no latest.json written anywhere ---------------------- #
    assert not (registry / "latest.json").exists()
    assert not list((out / "candidate_release").rglob("latest.json"))
    ptr = manifest["publication_pointer"]
    assert ptr["unchanged"] is True and ptr["before"] is None and ptr["after"] is None

    # --- disclosure: provisional, review-only, no prior count -------------- #
    disclosure = json.loads((out / "DISCLOSURE.json").read_text())
    assert disclosure["status"] == "provisional_review_only"
    assert disclosure["published"] is False
    assert disclosure["prior_preview_counts_reused"] is False
    assert disclosure["evaluation"]["status"] == "deferred"
    assert disclosure["evaluation"]["applied"] == []
    assert disclosure["evaluation"]["p32_10_confidence_policy_activated"] is False
    assert disclosure["change_disclosure"]["counts"]["applied"] == 4
    assert disclosure["suppression_disclosure"]["dispositions_recorded"] == 3
    assert "no final evaluation decision" in disclosure["evaluation_disclosure"].lower()
    # the fixture has no geolocated camera records — honest absence, no figure
    assert disclosure["resolved_sites"] is None

    # --- rollback packet ---------------------------------------------------- #
    rollback = json.loads((out / "ROLLBACK_PACKET.json").read_text())
    assert rollback["status"] == "prepared_not_needed"
    assert rollback["candidate"]["publication_id"] == rel["publication_id"]
    assert rollback["pointer_unchanged"] is True
    assert rollback["candidate"]["candidate_identity_digest"] == cand["identity_digest"]

    # --- packet artifacts all exist ------------------------------------------ #
    for name in (
        "CANDIDATE_MANIFEST.json",
        "CANDIDATE_MANIFEST.md",
        "DISCLOSURE.json",
        "DISCLOSURE.md",
        "ROLLBACK_PACKET.json",
        "ROLLBACK_PACKET.md",
        "MATERIALIZATION.json",
        "LIVE_RETURN_PASS.json",
    ):
        assert (out / name).exists(), name

    # --- no pre-evaluation preview identity is cited ------------------------- #
    # the manifest cites the SNAPSHOT (provenance), never claims the snapshot
    # IS the candidate — and must not reuse the pre-ticket ruleset id
    candidate_doc = json.loads((out / "CANDIDATE_MANIFEST.json").read_text())
    assert candidate_doc["candidate"]["ruleset_version"] == rc.PROVISIONAL_RULESET
    assert export_manifest["reproducibility_inputs"]["ruleset_version"] != ("export-buildspec/1")


def test_candidate_pointer_bytes_unchanged_with_existing_pointer(conn, tmp_path):
    """With a real latest.json in the registry, staging leaves it byte-identical."""
    from ops import release_candidate as rc

    stage = _repaired_spine(conn, tmp_path / "stage")
    registry = tmp_path / "registry"
    registry.mkdir()
    prior = {
        "schema": "sig.publication-pointer/1",
        "publication_id": "sig-pub-priorpoint",
        "manifest_sha256": "a" * 64,
        "data_release_id": "sig-2026-09-27-ce480ab1",
        "ordinal": 7,
    }
    latest_bytes = (json.dumps(prior, indent=2) + "\n").encode()
    (registry / "latest.json").write_bytes(latest_bytes)

    manifest = rc.run_candidate(
        conn,
        snapshot=stage["snapshot"],
        out_dir=tmp_path / "candidate",
        registry_dir=registry,
        as_of="2026-10-19",
    )
    assert (registry / "latest.json").read_bytes() == latest_bytes
    ptr = manifest["publication_pointer"]
    assert ptr["unchanged"] is True
    assert ptr["before"]["publication_id"] == "sig-pub-priorpoint"
    assert ptr["after"]["publication_id"] == "sig-pub-priorpoint"


def test_candidate_export_read_only_and_compartments(conn, tmp_path):
    """The export stays inside its licence compartments and mutates nothing
    beyond the materialized-surface + execution rows it owns."""
    from ops import release_candidate as rc

    stage = _repaired_spine(conn, tmp_path / "stage")
    manifest = rc.run_candidate(
        conn,
        snapshot=stage["snapshot"],
        out_dir=tmp_path / "candidate",
        as_of="2026-10-19",
    )
    # every emitted compartment artifact carries a licence + checksum; the
    # ODbL separation rule was exercised by the export gate itself
    export_manifest = json.loads(
        (tmp_path / "candidate" / "candidate_export" / "manifest.json").read_text()
    )
    for art in export_manifest["artifacts"]:
        assert art["license"], art["path"]
        assert re.fullmatch(r"[0-9a-f]{64}", art["sha256"])
    # the recovery claims are still exactly what P32.22 left — nothing rewrote
    # them (the candidate is a read + materialize + stage, not a repair)
    count = conn.execute("SELECT count(*) FROM claim").fetchone()[0]
    assert count == 17  # 16 fixture + 1 repair row from the apply stage
    assert manifest["frame_check"]["population_digest_matches"] is True
    assert manifest["frame_check"]["eligibility_matches"] is True


# ---------------------------------------------------------------------------
# Changed input → reassessment stop (fail-closed, never carry old eligibility).
# ---------------------------------------------------------------------------


def test_candidate_refuses_a_missing_population_claim(conn, tmp_path):
    from ops import release_candidate as rc

    stage = _repaired_spine(conn, tmp_path / "stage")
    snapshot = dict(stage["snapshot"])
    frame = dict(snapshot["population_frame"])
    frame["claim_ids"] = sorted({*frame["claim_ids"], "00000000-0000-0000-0000-0000000000ff"})
    snapshot["population_frame"] = frame
    with pytest.raises(rc.CandidateError) as exc:
        rc.run_candidate(
            conn,
            snapshot=snapshot,
            out_dir=tmp_path / "candidate",
            as_of="2026-10-19",
        )
    assert exc.value.code == "changed_input"
    # nothing was staged when the frame check failed
    assert not (tmp_path / "candidate" / "candidate_release").exists()


def test_candidate_refuses_drifted_eligibility_semantics(conn, tmp_path):
    from ops import release_candidate as rc

    stage = _repaired_spine(conn, tmp_path / "stage")
    snapshot = dict(stage["snapshot"])
    frame = dict(snapshot["population_frame"])
    frame["eligible_claim_ids"] = frame["eligible_claim_ids"][:5]  # semantics drift
    snapshot["population_frame"] = frame
    with pytest.raises(rc.CandidateError) as exc:
        rc.run_candidate(
            conn,
            snapshot=snapshot,
            out_dir=tmp_path / "candidate",
            as_of="2026-10-19",
        )
    assert exc.value.code == "changed_input"


def test_candidate_refuses_when_a_real_disposition_changes_eligibility(conn, tmp_path):
    """A REAL semantics change — a new withhold disposition lands after the
    freeze — must stop the build, not carry the old eligible set forward."""
    from db.dispositions import record_disposition
    from policy.eligibility import (
        Disposition,
        ReasonCategory,
        TargetKind,
        new_disposition,
    )

    from ops import release_candidate as rc

    stage = _repaired_spine(conn, tmp_path / "stage")
    eligible = sorted(stage["snapshot"]["population_frame"]["eligible_claim_ids"])
    victim = eligible[0]
    # an operator withholds one previously-eligible claim post-freeze
    record_disposition(
        conn,
        new_disposition(
            target_kind=TargetKind.CLAIM,
            target_id=victim,
            disposition=Disposition.WITHHOLD,
            reason_category=ReasonCategory.REVIEW_PENDING,
            authority="op:test/P32.23a-semantics-change",
            decided_by="operator:test",
        ),
    )
    with pytest.raises(rc.CandidateError) as exc:
        rc.run_candidate(
            conn,
            snapshot=stage["snapshot"],
            out_dir=tmp_path / "candidate",
            as_of="2026-10-19",
        )
    assert exc.value.code == "changed_input"
    assert "eligibility" in str(exc.value).lower()
    detail = exc.value.detail
    assert detail["eligible_lost"] == [victim]


def test_candidate_refuses_on_activated_shadow_policy(conn, tmp_path):
    from ops import release_candidate as rc

    stage = _repaired_spine(conn, tmp_path / "stage")
    shadow = json.loads((P32_22_DIR / "PROVISIONAL_VS_SHADOW.json").read_text(encoding="utf-8"))
    shadow["shadow_evaluator"]["mode"] = "active"
    with pytest.raises(rc.CandidateError) as exc:
        rc.run_candidate(
            conn,
            snapshot=stage["snapshot"],
            out_dir=tmp_path / "candidate",
            shadow_report=shadow,
            as_of="2026-10-19",
        )
    assert exc.value.code == "activated_policy"
