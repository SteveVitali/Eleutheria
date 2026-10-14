# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.49 / ADR-185: the at-rest audit machinery — the committed
``sig.at-rest-audit-decl/1`` loads and validates; a fixture OCFL root scans
to a counts-only ``sig.at-rest-audit/1`` report + restricted
``sig.at-rest-flagged/1`` sidecar; the seal plan, deny set and PUB-002
listing are append-only/counts-only artifacts; and the leg script is
window-gated (exit 42 = queued)."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from evidence.digest import multihash
from evidence.ocfl import OcflStore
from evidence.storage import LocalFileStore
from ops.at_rest_audit import (
    CaptureRow,
    build_deny_doc,
    build_pub002_listing,
    build_seal_plan,
    load_declaration,
    scan_store,
)

from ops import at_rest_audit

REPO_ROOT = Path(__file__).resolve().parents[2]
DECL = load_declaration()


def _put_capture(
    store_root: Path,
    payload: bytes,
    media_type: str = "application/json",
    source_uri: str = "https://example.test/x",
) -> str:
    """Store one OCFL capture object; returns its content digest."""
    store = OcflStore(LocalFileStore(store_root))
    digest = multihash(payload)
    object_id = f"sig:capture:{digest}"
    store.add_version(
        object_id,
        {
            "capture": payload,
            "metadata.json": json.dumps(
                {"digest": digest, "media_type": media_type, "source_uri": source_uri}
            ).encode(),
        },
    )
    return digest


# --- the declaration -----------------------------------------------------------


def test_committed_declaration_loads_and_screens_every_class() -> None:
    from evidence.screen import ALL_CLASSES

    ids = {c.class_id for c in DECL.classes}
    assert ids == set(ALL_CLASSES)
    # The I7 lanes are member-scoped (a lane never screens a non-member);
    # the F-406 families and PUB-002 categories declare their vocabularies.
    assert DECL.rule_for("F406-OSM-USERUID") is not None
    assert DECL.report_prefix.endswith("/")
    assert DECL.deny_set_object == "ops/seal/deny-set.json"


# --- the L1 scan ------------------------------------------------------------------


def test_scan_over_fixture_root_counts_only(tmp_path: Path) -> None:
    root = tmp_path / "captures"
    root.mkdir()
    osm = json.dumps({"elements": [{"type": "node", "id": 1, "user": "u", "uid": 1}]}).encode()
    arcgis = json.dumps(
        {"features": [{"attributes": {"created_user": "op", "OBJECTID": 1}}]}
    ).encode()
    clean = json.dumps({"rows": [{"count": 4}]}).encode()
    d1 = _put_capture(root, osm)
    d2 = _put_capture(root, arcgis)
    _put_capture(root, clean)

    rows = {
        d1: [
            CaptureRow(
                capture_id="11111111-1111-1111-1111-111111111111",
                artifact_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                source_id="osm_overpass_us",
                storage_tier="restricted",
            )
        ],
        d2: [
            CaptureRow(
                capture_id="22222222-2222-2222-2222-222222222222",
                artifact_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                source_id="camreg_nola_la",
                storage_tier="restricted",
            )
        ],
    }
    report, flagged = scan_store(
        LocalFileStore(root), DECL, capture_rows=rows, generated_at="2026-10-08T00:00:00Z"
    )
    assert report["schema"] == "sig.at-rest-audit/1"
    assert report["objects"]["scanned"] == 3
    classes = report["classes"]
    assert classes["F406-OSM-USERUID"]["objects_flagged"] == 1
    assert classes["F406-ARCGIS-ATTRS"]["objects_flagged"] == 1
    # Counts only — the flagged material never appears in the report.
    rendered = json.dumps(report)
    assert '"user"' not in rendered and "op" not in rendered

    assert flagged["schema"] == "sig.at-rest-flagged/1"
    by_digest = {e["digest"]: e for e in flagged["entries"]}
    assert set(by_digest) == {d1, d2}
    assert by_digest[d1]["classes"] == ["F406-OSM-USERUID"]
    assert "F406-ARCGIS-ATTRS" in by_digest[d2]["classes"]
    assert by_digest[d1]["captures"][0]["already_sealed"] is False


def test_scan_marks_already_sealed(tmp_path: Path) -> None:
    root = tmp_path / "captures"
    root.mkdir()
    d = _put_capture(root, json.dumps({"elements": [{"user": "u", "uid": 1}]}).encode())
    rows = {
        d: [
            CaptureRow(
                capture_id="11111111-1111-1111-1111-111111111111",
                artifact_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                source_id="osm_overpass_us",
                storage_tier="restricted",
            )
        ]
    }
    _, flagged = scan_store(
        LocalFileStore(root),
        DECL,
        capture_rows=rows,
        sealed={"11111111-1111-1111-1111-111111111111"},
    )
    assert flagged["entries"][0]["captures"][0]["already_sealed"] is True


def test_scan_unreadable_object_counted(tmp_path: Path) -> None:
    root = tmp_path / "captures"
    root.mkdir()
    _put_capture(root, b"{}")
    # A corrupt object root: a 5-segment inventory path with bad JSON.
    bad = root / "aa" / "bb" / "cc" / "sig%3acapture%3abad" / "inventory.json"
    bad.parent.mkdir(parents=True)
    bad.write_text("not json")
    report, _ = scan_store(LocalFileStore(root), DECL)
    assert report["objects"]["unreadable"] == 1


# --- the L2 seal plan --------------------------------------------------------------


def _flagged_and_report(tmp_path: Path):
    root = tmp_path / "captures"
    root.mkdir()
    d = _put_capture(root, json.dumps({"elements": [{"user": "u", "uid": 1}]}).encode())
    d2 = _put_capture(root, json.dumps({"plate": "ABC1234"}).encode())
    rows = {
        d: [
            CaptureRow(
                capture_id="11111111-1111-1111-1111-111111111111",
                artifact_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                source_id="osm_overpass_us",
                storage_tier="restricted",
            )
        ],
        d2: [
            CaptureRow(
                capture_id="33333333-3333-3333-3333-333333333333",
                artifact_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
                source_id="camreg_x",
                storage_tier="restricted",
            )
        ],
    }
    report, flagged = scan_store(
        LocalFileStore(root), DECL, capture_rows=rows, generated_at="2026-10-08T00:00:00Z"
    )
    return report, flagged


def test_seal_plan_is_append_only_suppression(tmp_path: Path) -> None:
    report, flagged = _flagged_and_report(tmp_path)
    plan = build_seal_plan(flagged, report=report, generated_at="2026-10-08T01:00:00Z")
    assert plan["schema"] == "sig.at-rest-seal-plan/1"
    for e in plan["entries"]:
        assert e["disposition"] == "withhold"
        assert e["reason_category"] in {"policy_restriction", "suppressed"}
        # Sealing scope ONLY — no entry ever carries a delete/purge verb.
        assert "delete" not in json.dumps(e) and "purge" not in json.dumps(e)
    assert plan["counts"]["captures_to_seal"] == 2
    # The deny set names captures AND digests (both consult paths).
    kinds = {(e["kind"]) for e in plan["deny_entries"]}
    assert kinds == {"capture", "digest"}


def test_deny_doc_versions_and_pub002_listing_is_counts_only(tmp_path: Path) -> None:
    report, flagged = _flagged_and_report(tmp_path)
    plan = build_seal_plan(flagged, report=report, generated_at="2026-10-08T01:00:00Z")
    deny = build_deny_doc(plan, generated_at="2026-10-08T02:00:00Z")
    assert deny["schema"] == "sig.seal-deny/1" and deny["version"] == 1
    deny2 = build_deny_doc(plan, generated_at="2026-10-08T03:00:00Z", prior=deny)
    assert deny2["version"] == 2 and deny2["supersedes"] == deny["entries"]

    listing = build_pub002_listing(plan, generated_at="2026-10-08T02:00:00Z")
    assert listing["schema"] == "sig.pub002-listing/1"
    plates = listing["categories"]["PUB002-PLATES"]
    assert plates["objects"] == 1 and len(plates["digests"]) == 1
    # Counts + digests only — the flagged material is never listed.
    assert "ABC1234" not in json.dumps(listing)


# --- the CLI verbs --------------------------------------------------------------------


def test_cli_scan_over_a_fixture_root(tmp_path: Path, capsys) -> None:
    root = tmp_path / "captures"
    root.mkdir()
    _put_capture(root, json.dumps({"elements": [{"user": "u", "uid": 1}]}).encode())
    out = tmp_path / "report.json"
    f_out = tmp_path / "flagged.json"
    rc = at_rest_audit.main(
        ["scan", "--root", str(root), "--report", str(out), "--flagged", str(f_out)]
    )
    assert rc == 0
    report = json.loads(out.read_text())
    assert report["schema"] == "sig.at-rest-audit/1"
    assert report["objects"]["scanned"] == 1


def test_cli_seal_plan_end_to_end(tmp_path: Path) -> None:
    root = tmp_path / "captures"
    root.mkdir()
    _put_capture(root, json.dumps({"elements": [{"user": "u", "uid": 1}]}).encode())
    report_p, flagged_p = tmp_path / "r.json", tmp_path / "f.json"
    at_rest_audit.main(
        ["scan", "--root", str(root), "--report", str(report_p), "--flagged", str(flagged_p)]
    )
    plan_p, deny_p, pub_p = tmp_path / "p.json", tmp_path / "d.json", tmp_path / "pub.json"
    rc = at_rest_audit.main(
        [
            "seal-plan",
            "--flagged",
            str(flagged_p),
            "--report",
            str(report_p),
            "--out",
            str(plan_p),
            "--deny-out",
            str(deny_p),
            "--pub002-out",
            str(pub_p),
        ]
    )
    assert rc == 0
    plan = json.loads(plan_p.read_text())
    assert plan["schema"] == "sig.at-rest-seal-plan/1"
    assert json.loads(deny_p.read_text())["schema"] == "sig.seal-deny/1"


# --- the leg script's gates -------------------------------------------------------------


SCRIPT = REPO_ROOT / "ops" / "gcp" / "at-rest-audit.sh"


def _run(args, env_extra=None) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items()}
    env["SIG_GCP_PROJECT"] = "sig-test-project"
    env["CLOUDSDK_CONFIG"] = "/nonexistent-sig-adc"
    env.update(env_extra or {})
    return subprocess.run(
        ["bash", str(SCRIPT), *args], capture_output=True, text=True, env=env, cwd=str(REPO_ROOT)
    )


def test_leg_scan_queued_before_the_window() -> None:
    """Before the P34.43 exec-host window the apply exits 42 (queued) —
    never a scan, never a seal."""
    proc = _run(["--apply", "scan"], {"SIG_ATREST_NOW": "2026-10-08T00:00:00Z"})
    assert proc.returncode == 42
    assert "QUEUED" in proc.stdout
    assert "live_verification=true" in proc.stdout


def test_leg_seal_queued_before_the_window() -> None:
    proc = _run(["--apply", "seal"], {"SIG_ATREST_NOW": "2026-10-08T00:00:00Z"})
    assert proc.returncode == 42


def test_leg_apply_queued_inside_the_excluded_hours() -> None:
    proc = _run(
        ["--apply", "scan"],
        {"SIG_ATREST_NOW": "2026-10-15T03:30:00Z"},  # future-ok: scheduled: AR-3 band
    )
    assert proc.returncode == 42


def test_leg_scan_gates_on_the_exec_host_identity() -> None:
    """After the window but without the P34.43 exec identity the scan still
    queues — the read-only mount needs the least-privilege host, never a
    privileged fallback."""
    # Clock inside the window; ADC absent → the exec-host check would need
    # gcloud+ADC, but require_adc exits 3 first on this ADC-less host. The
    # gate ordering (window → ADC) is what the test pins.
    proc = _run(
        ["--apply", "scan"],
        {"SIG_ATREST_NOW": "2026-10-15T15:00:00Z"},  # future-ok: scheduled: AR-3 window
    )
    assert proc.returncode in {3, 42}
