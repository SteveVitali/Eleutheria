# SPDX-License-Identifier: Apache-2.0
"""tests/exports/test_sbom.py — the P37.4a release SBOM (SIG-SEC-006, ADR-231).

The acceptance shape: **SBOM and signature per release** — every export emits
``sbom.cdx.json`` (deterministic CycloneDX 1.5 rendered from the committed
``pylock.toml``, never the ambient env), SHA256SUMS covers it as a declared
sidecar member, and the pipeline signature verifies.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from exports.downloads import verify_downloads, write_integrity_files
from exports.minisign import generate_keypair, verify_detached

from exports import sbom as SB

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCK = REPO_ROOT / "pylock.toml"


def _lock() -> Path:
    assert LOCK.is_file()
    return LOCK


def test_render_is_deterministic() -> None:
    a = SB.render_sbom(_lock())
    b = SB.render_sbom(_lock())
    assert a == b
    doc = json.loads(a)
    assert doc["bomFormat"] == "CycloneDX" and doc["specVersion"] == "1.5"
    assert len(doc["components"]) > 50  # the locked workspace is non-trivial


def test_no_timestamp_or_serial_breaks_reproducibility() -> None:
    doc = json.loads(SB.render_sbom(_lock()))
    assert "timestamp" not in doc["metadata"]
    assert "serialNumber" not in doc


def test_components_carry_purl_and_hashes() -> None:
    doc = json.loads(SB.render_sbom(_lock()))
    comp = next(c for c in doc["components"] if c["name"] == "fastapi")
    assert comp["purl"].startswith("pkg:pypi/fastapi@")
    assert any(h["alg"] == "SHA-256" for h in comp["hashes"])
    refs = {c["bom-ref"] for c in doc["components"]}
    assert len(refs) == len(doc["components"])  # bom-refs unique


def test_emit_writes_sbom_and_signature(tmp_path: Path) -> None:
    pub, secret = generate_keypair()
    out = SB.emit_sbom(tmp_path, lock_path=_lock(), signing_secret_b64=secret)
    assert out == {"emitted": True, "sbom": SB.SBOM_FILE, "signed": True}
    data = (tmp_path / SB.SBOM_FILE).read_bytes()
    sig = (tmp_path / SB.SBOM_MINISIG_FILE).read_text()
    assert verify_detached(data, sig, pub)
    assert (tmp_path / "sig-release.minisign.pub").read_text() == pub


def test_emit_unsigned_and_missing_lock_are_honest(tmp_path: Path) -> None:
    out = SB.emit_sbom(tmp_path, lock_path=_lock())
    assert out["signed"] is False and not (tmp_path / SB.SBOM_MINISIG_FILE).exists()
    out = SB.emit_sbom(tmp_path, lock_path=tmp_path / "nope.toml")
    assert out["emitted"] is False


def test_sbom_is_sums_covered_and_verifies(tmp_path: Path) -> None:
    # A minimal export dir: manifest + one artifact + the sbom sidecar.
    (tmp_path / "manifest.json").write_text(json.dumps({"artifacts": []}))
    SB.emit_sbom(tmp_path, lock_path=_lock())
    write_integrity_files(tmp_path)
    sums = (tmp_path / "SHA256SUMS").read_text()
    assert "sbom.cdx.json" in sums
    verdict = verify_downloads(tmp_path)
    assert verdict["failures"] == [], verdict
    # a tampered sbom must fail the sums check loud
    (tmp_path / SB.SBOM_FILE).write_bytes(b"tampered")
    verdict = verify_downloads(tmp_path)
    assert any("sbom.cdx.json: sha256 mismatch" in f for f in verdict["failures"])


@pytest.mark.parametrize("artifact", ["manifest.json"])
def test_sidecar_membership_is_declared(tmp_path: Path, artifact: str) -> None:
    # an undeclared non-manifest file in sums still fails — only the declared
    # sidecar set passes.
    (tmp_path / artifact).write_text(json.dumps({"artifacts": []}))
    SB.emit_sbom(tmp_path, lock_path=_lock())
    (tmp_path / "SHA256SUMS").write_text("0" * 64 + "  mystery.bin\n")
    verdict = verify_downloads(tmp_path)
    assert any("mystery.bin" in f for f in verdict["failures"])
