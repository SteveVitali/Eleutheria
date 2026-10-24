# SPDX-License-Identifier: Apache-2.0
"""Synthesized release-candidate packet fixture (P35.53 / G3 NEW-5).

The committed ``/r/p-…`` release trees and staging registries under
``docs/build/reports/`` are evicted — real candidate trees and registries do
not live in the public repository (G3 RM-8). The release-verification suites
therefore *regenerate* their subject at test time instead of reading
committed bytes.

``build_candidate_packet`` mirrors ``ops.release_candidate.run_candidate``
verbatim minus its two DB legs (population-frame verification and the
dependency-ordered rematerialization rerun — both need a live spine):

* the frozen snapshot + shadow report + apply report come from the committed
  P32.22 bounded-recovery packet (report files — they stay);
* the licence-compartmented export comes from the committed p32.23a
  ``candidate_export/`` (an export, not a release tree — it stays);
* the ``candidate_release/`` tree is built fresh by ``exports.release`` —
  deterministic under the current projection, never pinned byte-for-byte.

The emitted packet is honest: its materialization/frame-check fields are
labelled ``synthesized_fixture`` rather than claiming DB evidence it does
not have, and ``write_gate_readout`` mints a *fixture* gate record (the
signed production readout is never fabricated — this one exists only so the
publish machinery's "the gate must name THIS candidate" agreement check has
a subject).
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from ops import release_candidate as rc

REPO = Path(__file__).resolve().parents[2]
P32_22 = REPO / "docs" / "build" / "reports" / "p32.22-bounded-recovery"
P32_23A = REPO / "docs" / "build" / "reports" / "p32.23a-release-candidate"

SNAPSHOT_PATH = P32_22 / "REPAIRED_SNAPSHOT.json"
SHADOW_PATH = P32_22 / "PROVISIONAL_VS_SHADOW.json"
APPLY_REPORT_PATH = P32_22 / "APPLY_REPORT.json"
CANDIDATE_EXPORT = P32_23A / "candidate_export"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_candidate_packet(root: Path | str, *, superseded: bool = True) -> Path:
    """Assemble a complete, internally-consistent candidate packet under
    ``root/packet`` — the same layout the committed packet carried, built by
    the real machinery over the committed recovery + export inputs."""
    root = Path(root)
    packet = root / "packet"
    packet.mkdir(parents=True, exist_ok=True)

    export_dir = packet / "candidate_export"
    shutil.copytree(CANDIDATE_EXPORT, export_dir)
    # The export's recorded artifact list lives in the *committed packet
    # manifest's* export_manifest block — it was re-pinned under P34.18's
    # source-id rename while the export's own manifest.json keeps the
    # build-time digests. The packet's recorded set is what verifies the
    # export bytes; its sha stays the sha of manifest.json itself.
    committed_manifest = json.loads((P32_23A / "CANDIDATE_MANIFEST.json").read_text())
    export_manifest = committed_manifest.get("export_manifest") or json.loads(
        (export_dir / "manifest.json").read_text()
    )
    staged_export_sha = "sha256:" + _sha((export_dir / "manifest.json").read_bytes())

    snapshot = rc.load_json(SNAPSHOT_PATH)
    shadow = rc.load_json(SHADOW_PATH)
    apply_report = rc.load_json(APPLY_REPORT_PATH)
    identity = rc.candidate_identity(snapshot=snapshot, shadow_report=shadow, code_commit="fixture")

    release_dir = packet / "candidate_release"
    scratch_registry = root / "scratch-registry"
    scratch_registry.mkdir(exist_ok=True)
    staged = rc.stage_candidate_release(
        export_dir,
        release_dir,
        renderer_revision="fixture",
        registry_dir=scratch_registry,
    )
    staged["export_manifest_sha256"] = staged_export_sha

    # The two DB legs are honestly labelled — the packet records that the
    # population-frame + rematerialization evidence is fixture-synthesized,
    # never fabricated as a live-spine result.
    frame_check: dict[str, Any] = {
        "frame_check_version": "synthesized_fixture",
        "note": "the DB-backed population-frame verification is not part of "
        "the synthesized packet — see run_candidate for the live leg",
    }
    materialization: dict[str, Any] = {
        "materialization_version": rc.MATERIALIZATION_VERSION,
        "dependency_order": None,
        "inserted_pass_one": None,
        "inserted_rerun": None,
        "plus_zero": None,
        "execution": "synthesized_fixture",
        "note": "the DB-backed rematerialization rerun is not part of the "
        "synthesized packet — see run_candidate for the live leg",
    }

    disclosure = rc.build_disclosure(
        identity=identity,
        export_dir=export_dir,
        apply_report=apply_report,
        materialization=materialization,
        build_report=staged["build"].report,
    )
    disclosure_digest = rc._sha(rc._canonical(disclosure))
    build = staged["build"]
    rollback = rc.build_rollback_packet(
        identity=identity,
        publication_id=build.publication_id,
        release_manifest_sha256=build.manifest_sha256,
        descriptor_sha256=rc._sha(rc._canonical(build.descriptor)),
        disclosure_digest=disclosure_digest,
        pointer_before=staged["pointer_before"],
        materialization=materialization,
    )
    return_pass = rc.build_candidate_return_pass(
        identity_digest=str(identity["identity_digest"]),
        snapshot_digest=rc._snapshot_digest(snapshot),
    )
    manifest = rc.build_candidate_manifest(
        identity=identity,
        snapshot=snapshot,
        frame_check=frame_check,
        materialization=materialization,
        staged=staged,
        disclosure=disclosure,
        rollback=rollback,
        return_pass=return_pass,
        dossier_packet_digests={},
        apply_report=apply_report,
        plan_digest=None,
        audit_digest=None,
    )
    manifest["export_manifest"] = export_manifest
    rc.write_candidate_packet(
        packet,
        manifest=manifest,
        disclosure=disclosure,
        rollback=rollback,
        materialization=materialization,
        return_pass=return_pass,
    )

    if superseded:
        pub = str(build.publication_id)
        (packet / "CORRECTION.md").write_text(
            "# Correction\n\n"
            f"## Supersession record — {pub}\n\n"
            f"the synthesized fixture candidate {pub} is superseded on "
            "creation — it is rehearsal evidence, never a publishable "
            "subject (the same posture the committed p32.23a packet recorded).\n",
            encoding="utf-8",
        )
    return packet


def write_gate_readout(packet_dir: Path | str, path: Path | str) -> Path:
    """Write a *fixture* gate readout whose SIGNED record names exactly this
    synthesized packet — the publish machinery's agreement check needs a
    readout that binds the fixture's own pins (never the production gate)."""
    manifest = json.loads((Path(packet_dir) / "CANDIDATE_MANIFEST.json").read_text())
    cand = manifest["candidate"]
    rel = manifest["release"]
    pub = str(rel["publication_id"])
    text = (
        "# Fixture gate readout — synthesized by tests/ops/candidate_fixture.py\n\n"
        "Status: SIGNED (fixture — a test-minted record, never the production\n"
        "gate's signed acceptance; it exists so the publish authority check has\n"
        "a subject that names this exact synthesized packet)\n\n"
        f"- publication_id: {pub}\n"
        f"- identity_digest: {cand['identity_digest']}\n"
        f"- frozen_snapshot_digest: {cand['frozen_snapshot_digest']}\n"
        f"- ruleset_version: {cand['ruleset_version']}\n"
    )
    out = Path(path)
    out.write_text(text, encoding="utf-8")
    return out
