# SPDX-License-Identifier: Apache-2.0
"""Offline tests for the P32.25 accepted-release publish + verification
harness (SIG-TRUST-009, ADR-144).

The run exercises the REAL ``exports.release`` machinery (activate/rollback/
clear_latest_pointer/record_withdrawal/apply_withdrawals/route_access/
resolve_selector/validate_release) over the committed GATE-G3-accepted
fixture candidate in throwaway registries — the committed packet is never
written. The production surface is not probed; that is the recorded return
pass, never claimed here.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from exports.release import ReleaseError

from exports import release as rel
from ops import release_publish_verify as rpv

REPO = Path(__file__).resolve().parents[2]
CANDIDATE = REPO / "docs" / "build" / "reports" / "p32.23a-release-candidate"
PRIOR = (
    REPO
    / "docs"
    / "build"
    / "reports"
    / "p32.24-investigation-journey-verification"
    / "corpus_export"
)
GATE = REPO / "docs" / "build" / "readouts" / "GATE-G3.md"


def _manifest() -> dict:
    """The committed candidate manifest — the expectations below are derived
    from it (P34.22a: tests move from pinned values to manifest-derived)."""
    return json.loads((CANDIDATE / "CANDIDATE_MANIFEST.json").read_text())


@pytest.fixture(scope="module")
def pins() -> rpv.CandidatePins:
    return rpv.pins_from_candidate_dir(CANDIDATE)


def _integrity_artifacts() -> list[dict]:
    manifest = json.loads(
        next(
            (CANDIDATE / "candidate_release" / "releases").glob("*/integrity_manifest.json")
        ).read_text()
    )
    return manifest["artifacts"]


@pytest.fixture(scope="module")
def proof(tmp_path_factory) -> dict:
    """One shared bounded-publish run — every assertion reads the SAME
    emitted evidence packet."""
    out = tmp_path_factory.mktemp("rpv") / "report"
    return rpv.run(
        candidate_dir=CANDIDATE,
        out_dir=out,
        prior_export_dir=PRIOR,
        gate_readout=GATE,
        config_path=REPO / "ops" / "config.toml",
    )


def _check(proof: dict, check_id: str) -> dict:
    for c in proof["checks"]:
        if c["id"] == check_id:
            return c
    raise AssertionError(f"check {check_id} absent from the proof")


# ---------------------------------------------------------------------------
# Preflight — the packet must BE the accepted candidate
# ---------------------------------------------------------------------------


def test_preflight_pins_exactly_the_accepted_candidate(
    proof: dict, pins: rpv.CandidatePins
) -> None:
    chk = _check(proof, "PF.candidate_pinned")
    assert chk["status"] == "pass"
    accepted = proof["accepted"]
    manifest = _manifest()
    release = manifest["release"]
    cand = manifest["candidate"]
    assert accepted["publication_id"] == pins.publication_id == release["publication_id"]
    assert accepted["identity_digest"] == pins.identity_digest == cand["identity_digest"]
    assert (
        accepted["frozen_snapshot_digest"]
        == pins.frozen_snapshot_digest
        == cand["frozen_snapshot_digest"]
    )
    assert accepted["ruleset_version"] == "provisional-ruleset/1"
    assert accepted["data_release_id"] == release["descriptor"]["data_release_id"]
    assert accepted["as_of_world"] == release["descriptor"]["as_of_world"]
    assert accepted["as_of_belief"] == release["descriptor"]["as_of_belief"]
    assert accepted["evaluation"] == {
        "status": "deferred",
        "mode": "shadow",
        "applied": [],
    }
    assert accepted["artifact_count"] == len(_integrity_artifacts())


def test_proof_reports_the_superseded_candidate_posture(proof: dict) -> None:
    """P34.22a / B-4: pointed at the p32.23a packet the run reports rehearsal
    evidence of a superseded candidate — never a production verification."""
    assert proof["subject"]["superseded"] is True
    assert proof["subject"]["posture"] == rpv.SUPERSEDED_POSTURE
    assert "superseded" in proof["subject"]["posture"]
    assert "no publish authorised" in proof["subject"]["posture"]
    chk = _check(proof, "PF.publish_authority")
    assert chk["status"] == "deferred"
    assert "superseded candidate" in chk["detail"]
    readme = (Path(proof["publish"]["registry"]).parent / "README.md").read_text()
    assert "no publish authorised" in readme


def test_gate_readout_is_the_publish_authority(proof: dict) -> None:
    assert _check(proof, "PF.gate_signed")["status"] == "pass"


def test_preflight_refuses_a_different_candidate(tmp_path: Path) -> None:
    """A packet claiming a different publication id can never be published by
    this run — the gate-signed readout is the publish authority: a manifest
    naming a publication the readout does not has no publish authority."""
    tampered = tmp_path / "packet"
    shutil.copytree(CANDIDATE, tampered)
    cman_path = tampered / "CANDIDATE_MANIFEST.json"
    cman = json.loads(cman_path.read_text())
    cman["release"]["publication_id"] = "p-not-the-accepted-one"
    cman_path.write_text(json.dumps(cman))
    with pytest.raises(rpv.PublishVerificationError, match="publish authority"):
        rpv.preflight(tampered, GATE, rpv.pins_from_candidate_dir(tampered))


def test_preflight_refuses_tampered_bytes(tmp_path: Path, pins: rpv.CandidatePins) -> None:
    tampered = tmp_path / "packet"
    shutil.copytree(CANDIDATE, tampered)
    victim = next((tampered / "candidate_release" / "r").rglob("index.html"))
    victim.write_bytes(victim.read_bytes() + b"tampered")
    with pytest.raises(rpv.PublishVerificationError):
        rpv.preflight(tampered, GATE, pins)


def test_preflight_refuses_without_a_signed_gate(tmp_path: Path, pins: rpv.CandidatePins) -> None:
    unsigned = tmp_path / "GATE-G3.md"
    unsigned.write_text("# GATE-G3\nStatus: pending\n")
    with pytest.raises(rpv.PublishVerificationError, match="publish authority"):
        rpv.preflight(CANDIDATE, unsigned, pins)


def test_a_dossier_claiming_completion_is_refused(tmp_path: Path, pins: rpv.CandidatePins) -> None:
    tampered = tmp_path / "packet"
    shutil.copytree(CANDIDATE, tampered)
    dp = tampered / "candidate_export" / "web" / "research_dossiers.json"
    doc = json.loads(dp.read_text())
    doc["dossiers"][0]["completeness"]["pilot_complete"] = True
    dp.write_text(json.dumps(doc))
    with pytest.raises(rpv.PublishVerificationError, match="pilot completion"):
        rpv.preflight(tampered, GATE, pins)


# ---------------------------------------------------------------------------
# The atomic publish
# ---------------------------------------------------------------------------


def test_pointer_flips_after_full_validation(proof: dict, pins: rpv.CandidatePins) -> None:
    assert _check(proof, "P.validate_first")["status"] == "pass"
    pointer = proof["publish"]["pointer"]
    assert pointer["before"] is None
    assert pointer["after"]["publication_id"] == pins.publication_id
    assert pointer["after"]["manifest_sha256"] == pins.release_manifest_sha256
    assert _check(proof, "P.staged_revalidates")["status"] == "pass"
    assert _check(proof, "P.activation_receipt")["status"] == "pass"


def test_publish_refuses_a_non_fresh_registry(tmp_path: Path, pins: rpv.CandidatePins) -> None:
    reg = tmp_path / "registry"
    reg.mkdir()
    (reg / "stale.txt").write_text("x")
    with pytest.raises(rpv.PublishVerificationError, match="not empty"):
        rpv.publish(CANDIDATE, reg, pins)


# ---------------------------------------------------------------------------
# Public verification
# ---------------------------------------------------------------------------


def test_all_public_checks_pass(proof: dict) -> None:
    expected = {
        "V.digests",
        "V.http_reads",
        "V.citations",
        "V.records_honest_zero",
        "V.search_honest",
        "V.tiles_honest",
        "V.withdrawal_barrier",
        "V.suppressed_slices",
        "V.disclosures",
        "V.intake_unavailable",
        "V.zero_js",
    }
    ids = {c["id"] for c in proof["checks"]}
    assert expected <= ids
    for cid in expected:
        assert _check(proof, cid)["status"] == "pass", cid


def test_unauthenticated_reads_match_approved_digests(proof: dict) -> None:
    chk = _check(proof, "V.http_reads")
    ev = chk["evidence"]
    assert ev["non_200"] == []
    assert ev["digest_mismatches"] == []
    # every manifest artifact + the directory/overlay routes
    assert ev["gets"] >= len(_integrity_artifacts()) + 5
    digests = _check(proof, "V.digests")["evidence"]
    assert digests["mismatches"] == [] and digests["undeclared"] == []


def test_search_is_honestly_absent_not_a_fallback(proof: dict) -> None:
    outcomes = _check(proof, "V.search_honest")["evidence"]["outcomes"]
    by_comp = {(o["pub"], o["comp"]): (o["status"], o["code"]) for o in outcomes}
    for (_pub, _comp), got in by_comp.items():
        assert got[0] == 404
        assert got[1] in {"unknown_compartment", "unknown_publication"}


def test_intake_is_verified_unavailable_only(proof: dict) -> None:
    ev = _check(proof, "V.intake_unavailable")["evidence"]
    assert ev["config_operational"] is False
    assert ev["env_gate"] is False
    assert ev["armed_env_but_uncommitted_config"] is False
    assert ev["new_status"] == 503
    assert ev["post_status"] == 503
    assert ev["staged_intake_refs"] == []
    assert "synthetic" in _check(proof, "V.intake_unavailable")["detail"].lower()


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------


def test_prior_release_rollback_is_atomic(proof: dict) -> None:
    ev = _check(proof, "R.prior_release")["evidence"]
    assert ev["post_latest"]["publication_id"] == rpv.PRIOR_RELEASE_ID
    assert ev["post_latest"]["rolled_back"] is True
    # old citations preserve bytes — the candidate's unaffected artifact
    # still serves the approved digest after the rollback
    assert ev["untouched_route_digest_ok"] is True
    # current withdrawals keep denying under the rollback
    assert ev["denied_candidate_route_permitted"] is False
    assert ev["denied_prior_route_permitted"] is False
    assert ev["catalog_publications"] == 2


def test_no_prior_pointer_rollback(proof: dict) -> None:
    ev = _check(proof, "R.no_prior_pointer")["evidence"]
    assert ev["latest_exists"] is False
    assert ev["catalog_publications"] == 1
    assert ev["evidence_route_digest_ok"] is True
    assert ev["receipt"]["cleared"] is True


def test_failed_deploy_leaves_previous_release(proof: dict) -> None:
    ev = _check(proof, "R.refused_deploy")["evidence"]
    assert ev["activate_refused"] is True
    assert ev["latest_unchanged"] is True
    assert ev["catalog_unchanged"] is True


def test_clear_latest_pointer_refuses_when_absent(tmp_path: Path) -> None:
    """clear_latest_pointer is not silently idempotent — a registry with no
    pointer has nothing to clear."""
    registry = tmp_path / "registry"
    registry.mkdir()
    with pytest.raises(ReleaseError, match="already absent"):
        rel.clear_latest_pointer(registry)


def test_tombstoning_never_mutates_the_release_input(tmp_path: Path) -> None:
    """Regression for the hardlink write-through: staged artifacts are
    hardlinks into the release dir, so a tombstone write used to corrupt the
    immutable release input (P32.24's committed corpus_release was hit by
    exactly this). Denying a route must leave the release dir byte-identical."""
    release_dir = tmp_path / "release"
    shutil.copytree(CANDIDATE / "candidate_release", release_dir)
    registry = tmp_path / "registry"
    rel.activate(registry, release_dir)
    manifest = json.loads(next(release_dir.glob("releases/*/integrity_manifest.json")).read_text())
    art = next(a for a in manifest["artifacts"] if "evidence" in a["path"])
    uuid = art["path"].split("evidence/")[1].split("/")[0]
    before = (release_dir / art["path"]).read_bytes()
    from datetime import UTC, datetime

    from policy.eligibility import (
        Disposition,
        ReasonCategory,
        TargetKind,
        new_disposition,
    )

    rel.record_withdrawal(
        registry,
        [
            new_disposition(
                target_kind=TargetKind.ARTIFACT,
                target_id=uuid,
                disposition=Disposition.WITHDRAW,
                reason_category=ReasonCategory.SAFETY_WITHDRAWAL,
                authority="test",
                decided_at=datetime(2026, 10, 20, tzinfo=UTC),
            )
        ],
    )
    # the staged route is a tombstone now, but the release bytes are untouched
    assert (release_dir / art["path"]).read_bytes() == before
    staged_tomb = registry / "staged" / art["path"].rsplit("index.html", 1)[0] / "index.html"
    assert b"tombstone" in staged_tomb.read_bytes().lower() or (
        b"withdrawn" in staged_tomb.read_bytes().lower()
    )


# ---------------------------------------------------------------------------
# The proof itself
# ---------------------------------------------------------------------------


def test_verdict_and_report_artifacts(proof: dict, tmp_path_factory) -> None:
    assert proof["schema"] == rpv.PROOF_SCHEMA
    assert proof["verdict"] == "pass"
    assert proof["live_verification"] is False
    assert proof["counts"]["fail"] == 0
    # the emitted packet
    out = Path(proof["publish"]["registry"]).parent
    assert (out / "PUBLISH_PROOF.json").exists()
    assert (out / "PUBLIC_VERIFICATION.md").exists()
    assert (out / "ROLLBACK_REHEARSAL.json").exists()
    assert (out / "LIVE_RETURN_PASS.json").exists()
    rp = json.loads((out / "LIVE_RETURN_PASS.json").read_text())
    assert rp["status"] == "prepared_not_executed"
    assert {d["id"] for d in rp["open_deferrals"]} == {
        "D-R10-PUBLISH-1",
        "D-P32.23a-1",
        "D-R10-LIVE-1",
        "D-P32.16-1",
    }
    md = (out / "PUBLIC_VERIFICATION.md").read_text()
    assert "No production exposure is claimed" in md
    assert "NOT DONE" in md


def test_a_non_pass_check_requires_owner_and_landing() -> None:
    with pytest.raises(rpv.PublishVerificationError, match="owner"):
        rpv._check("X.test", "fail", "something", owner=None, landing=None)


def test_cli_wiring() -> None:
    from ops.cli import build_parser

    parser = build_parser()
    # --candidate is required — no production default exists (P34.22a)
    with pytest.raises(SystemExit):
        parser.parse_args(["release-publish", "--out", "x"])
    args = parser.parse_args(
        ["release-publish", "--out", "x", "--candidate", "docs/build/reports/x"]
    )
    assert args.command == "release-publish"
    assert args.candidate == "docs/build/reports/x"


def test_committed_packet_is_untouched_by_the_run(proof: dict) -> None:
    """The run stages copies — the committed candidate packet must be
    byte-identical afterwards (a hardlink write-through would corrupt it)."""
    manifest = json.loads(
        next(
            (CANDIDATE / "candidate_release" / "releases").glob("*/integrity_manifest.json")
        ).read_text()
    )
    for art in manifest["artifacts"]:
        p = CANDIDATE / "candidate_release" / art["path"]
        import hashlib

        assert hashlib.sha256(p.read_bytes()).hexdigest() == art["sha256"], art["path"]
