# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The Zenodo production deposit *package* (P37.55, D-J3-9 [B-21] = yes).

The package carries openly licensed compartments only — the GL-GATE-07
risk-accepted lanes (``operator_accepted`` / ``public_record``, by compartment
name *and* by licence token, so the combined-licence ``web_mixed`` web
compartment cannot slip through) are excluded; evidence bytes are excluded by
size; every byte hashed must equal the manifest's recorded digest or the build
refuses. The publish is the operator's (OP-19) — nothing here deposits.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from exports.deposit_package import DepositPackageError, build_deposit_package

from exports import deposit_package as dp

REPO_ROOT = Path(__file__).resolve().parents[2]


def _artifact(path: str, compartment: str, license_id: str, data: bytes) -> dict:
    return {
        "name": Path(path).name,
        "path": path,
        "media_type": "text/csv",
        "compartment": compartment,
        "license": license_id,
        "byte_size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _export(tmp_path: Path, rows: list[tuple[str, str, str, bytes]]) -> Path:
    export = tmp_path / "export"
    artifacts = []
    for path, compartment, license_id, data in rows:
        p = export / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        artifacts.append(_artifact(path, compartment, license_id, data))
    export.mkdir(exist_ok=True)
    (export / "manifest.json").write_text(
        json.dumps(
            {
                "release_id": "sig-2026-11-14-abcdef12",
                "concept_id": "sig",
                "content_key": "deadbeef",
                "artifacts": artifacts,
            }
        )
    )
    return export


_ROWS = [
    ("sig_graph/claims.csv", "sig_graph", "CC-BY-4.0", b"claims"),
    ("osm_physical/sites.csv", "osm_physical", "ODbL-1.0", b"sites"),
    ("metadata/datapackage.json", "metadata", "CC-BY-4.0", b"{}"),
    (
        "operator_accepted/rows.csv",
        "operator_accepted",
        "LicenseRef-OperatorAccepted-DBRight",
        b"oa",
    ),
    (
        "public_record/rows.csv",
        "public_record",
        "LicenseRef-PublicRecord-FactualCompilation",
        b"pr",
    ),
    (
        "web/index.json",
        "web",
        "CC-BY-4.0",
        b"web-surface-views",
    ),
    (
        "derived_facts/facts.csv",
        "derived_facts",
        "LicenseRef-DerivedFacts-Citations",
        b"facts",
    ),
    ("evidence/captures.jsonl", "evidence", "CC-BY-4.0", b"evidence-bytes"),
]


def test_open_compartments_only_are_packaged(tmp_path: Path) -> None:
    export = _export(tmp_path, _ROWS)
    out = tmp_path / "pkg"
    build_deposit_package(export.as_posix(), out.as_posix())
    names = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    # included: the three open artifacts + the four package documents.
    assert "sig_graph/claims.csv" in names
    assert "osm_physical/sites.csv" in names
    assert "metadata/datapackage.json" in names
    # excluded lanes never ship.
    assert not any("operator_accepted" in n or "public_record" in n for n in names)
    assert "web/index.json" not in names  # derived views, not a deposit surface
    assert "derived_facts/facts.csv" not in names  # a publication basis, not open
    assert "evidence/captures.jsonl" not in names
    assert {"manifest.json", "digests.json", "deposit-package.json", "README.md"} <= set(names)


def test_filtered_manifest_and_digest_manifest(tmp_path: Path) -> None:
    export = _export(tmp_path, _ROWS)
    out = tmp_path / "pkg"
    build_deposit_package(export.as_posix(), out.as_posix())
    manifest = json.loads((out / "manifest.json").read_text())
    comps = {a["compartment"] for a in manifest["artifacts"]}
    assert comps == {"sig_graph", "osm_physical", "metadata"}
    # The release identity is preserved — the package is the same release's subset.
    assert manifest["release_id"] == "sig-2026-11-14-abcdef12"
    digests = json.loads((out / "digests.json").read_text())
    # Every artifact's digest rides, excluded lanes included (§38.2).
    assert len(digests) == len(_ROWS)
    assert "operator_accepted/rows.csv" in digests


def test_combined_license_is_denied_by_token_not_name(tmp_path: Path) -> None:
    """A combined licence string carrying a risk-lane token is refused by the
    token rule — no compartment-name list would see it."""
    a = _artifact(
        "mixed/m.json",
        "mixed",
        "CC-BY-4.0 AND LicenseRef-PublicRecord-FactualCompilation",
        b"x",
    )
    assert dp.classify_artifact(a) == "denied-license"


def test_undeclared_compartments_are_excluded_allow_list(tmp_path: Path) -> None:
    """The allow-list is fail-closed: `web` view indexes and the `derived_facts`
    publication basis are not registry-declared open compartments."""
    assert dp.classify_artifact(_artifact("web/m.json", "web", "CC-BY-4.0", b"x")) == (
        "not-open-compartment"
    )
    assert (
        dp.classify_artifact(
            _artifact("d/f.csv", "derived_facts", "LicenseRef-DerivedFacts-Citations", b"x")
        )
        == "not-open-compartment"
    )
    # The export's own descriptor docs always ride — they ARE the package.
    assert dp.classify_artifact(_artifact("m.json", "metadata", "CC-BY-4.0", b"x")) is None


def test_descriptor_records_the_exclusion_accounting(tmp_path: Path) -> None:
    export = _export(tmp_path, _ROWS)
    out = tmp_path / "pkg"
    build_deposit_package(export.as_posix(), out.as_posix())
    desc = json.loads((out / "deposit-package.json").read_text())
    assert desc["schema"] == "sig.deposit-package/1"
    assert set(desc["included"]["compartments"]) == {"metadata", "osm_physical", "sig_graph"}
    reasons = desc["excluded"]
    assert reasons["denied-compartment"]["files"] == 2
    assert reasons["not-open-compartment"]["files"] == 2
    assert reasons["evidence-bytes"]["files"] == 1
    # The Zenodo metadata block is present for the OP-19 upload.
    assert desc["zenodo_metadata"]["upload_type"] == "dataset"


def test_integrity_mismatch_refuses_the_build(tmp_path: Path) -> None:
    rows = [("sig_graph/claims.csv", "sig_graph", "CC-BY-4.0", b"claims")]
    export = _export(tmp_path, rows)
    # Corrupt the bytes after the manifest was written.
    (export / "sig_graph/claims.csv").write_bytes(b"tampered")
    with pytest.raises(DepositPackageError, match="hash"):
        build_deposit_package(export.as_posix(), (tmp_path / "pkg").as_posix())


def test_missing_manifest_and_empty_package_refuse(tmp_path: Path) -> None:
    with pytest.raises(DepositPackageError):
        build_deposit_package((tmp_path / "nope").as_posix(), (tmp_path / "pkg").as_posix())
    export = _export(tmp_path, _ROWS[3:4])  # only a denied lane
    with pytest.raises(DepositPackageError, match="deposit nothing"):
        build_deposit_package(export.as_posix(), (tmp_path / "pkg").as_posix())


def test_artifact_missing_compartment_or_license_fails_loud(tmp_path: Path) -> None:
    bad = _artifact("x.csv", "sig_graph", "CC-BY-4.0", b"x")
    bad.pop("compartment")
    with pytest.raises(DepositPackageError):
        dp.classify_artifact(bad)
    bad2 = _artifact("x.csv", "sig_graph", "CC-BY-4.0", b"x")
    bad2.pop("license")
    with pytest.raises(DepositPackageError):
        dp.classify_artifact(bad2)


def test_cli_deposit_package_writes_package_and_report(tmp_path: Path) -> None:
    export = _export(tmp_path, _ROWS)
    out = tmp_path / "pkg"
    report = tmp_path / "report.json"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "exports",
            "deposit-package",
            "--in",
            str(export),
            "--out",
            str(out),
            "--report",
            str(report),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(report.read_text())
    assert doc["schema"] == "sig.deposit-package/1"
    assert doc["included"]["files"] == 3
    assert (out / "manifest.json").is_file()


def test_cli_deposit_production_gates_on_sig_zenodo_token(tmp_path: Path) -> None:
    """`--production` without SIG_ZENODO_TOKEN is gate-pending OP-19 — exit 4,
    nothing written (OM-20: never pre-authorised)."""
    export = _export(tmp_path, _ROWS[:1])
    import os

    env = {k: v for k, v in os.environ.items() if k != "SIG_ZENODO_TOKEN"}
    proc = subprocess.run(
        [sys.executable, "-m", "exports", "deposit", "--in", str(export), "--production"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
    )
    assert proc.returncode == 4
    assert "gate pending" in proc.stderr and "OP-19" in proc.stderr


def test_cli_deposit_production_and_sandbox_conflict(tmp_path: Path) -> None:
    export = _export(tmp_path, _ROWS[:1])
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "exports",
            "deposit",
            "--in",
            str(export),
            "--production",
            "--sandbox",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 2
    assert "mutually exclusive" in proc.stderr


def test_production_transport_targets_zenodo_org_not_sandbox() -> None:
    """The production path must hit zenodo.org and mint 10.5281 DOIs — never
    the sandbox's 10.5072 test DOIs (RISK-P21-08)."""
    import httpx
    from exports.zenodo import ZenodoHttpTransport

    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if request.method == "POST" and request.url.path == "/api/deposit/depositions":
            return httpx.Response(201, json={"id": 7, "links": {"bucket": "https://zenodo.org/b"}})
        if request.method == "PUT":
            return httpx.Response(200, json={})
        return httpx.Response(
            200,
            json={"doi": "10.5281/zenodo.100", "conceptdoi": "10.5281/zenodo.99"},
        )

    t = ZenodoHttpTransport(token="tok", sandbox=False, transport=httpx.MockTransport(handler))
    concept, version = t.deposit(
        concept_id="sig",
        version="v1",
        files={"a": b"b"},
        metadata=dp.DepositMetadata(
            title="t", version="v1", concept_id="sig", licenses=("CC-BY-4.0",)
        ),
    )
    assert seen and all("zenodo.org" in u and "sandbox" not in u for u in seen)
    assert concept == "10.5281/zenodo.99" and version == "10.5281/zenodo.100"
