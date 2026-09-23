# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The P27.8 public cut-over producer (`ops/src/ops/publish.py`, ADR-096).

Two invariants under test: (1) the public build reads the real national export or fails
LOUD (never a fixtures fall-back, §38.1); (2) only the published compartment goes public —
no ODbL/share-alike/UNDETERMINED byte reaches a public object (§42 / Part VIII). The
classification runs against the SHIPPED `policy/data/licenses.toml`, so these tests also
pin that ODbL-1.0 + CC-BY-SA-4.0 are share-alike (restricted) there.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ops import deploy as D
from ops import publish as P

# --- fixtures -----------------------------------------------------------------

_WATERMARK = {
    "as_of_snapshot": "2026-09-22",
    "as_of_belief": "2026-09-22",
    "ruleset_version": "resolver-ruleset-2026.07",
    "resolver_version": "p08.1/1.0.0",
}


def _write_export(root: Path, artifacts: list[dict]) -> Path:
    """Write a minimal but real-shaped export bundle (manifest + artifact bytes + web/)."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "web").mkdir(exist_ok=True)
    for art in artifacts:
        target = root / art["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"bytes for {art['path']}\n", encoding="utf-8")
    manifest = {
        "concept_id": "sig",
        "release_id": "sig-2026-09-22-abcd1234",
        "content_key": "abcd1234ef567890",
        "reproducibility_inputs": _WATERMARK,
        "artifacts": artifacts,
    }
    (root / "manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    return root


def _national_bundle(root: Path) -> Path:
    """A national export mixing a CC-BY graph, ODbL OSM layer, CC-BY-SA portal, web JSONs."""
    return _write_export(
        root,
        [
            {"path": "sig_graph/claims.csv", "compartment": "sig_graph", "license": "CC-BY-4.0"},
            {
                "path": "osm_physical/devices.csv",
                "compartment": "osm_physical",
                "license": "ODbL-1.0",
            },
            {"path": "portal/eyes.csv", "compartment": "portal", "license": "CC-BY-SA-4.0"},
            {"path": "web/map.json", "compartment": "web", "license": "CC-BY-4.0"},
            {"path": "web/dossiers.json", "compartment": "web", "license": "CC-BY-4.0"},
            {"path": "datapackage.json", "compartment": "metadata", "license": "CC-BY-4.0"},
        ],
    )


def _completed(rc: int, out: str = "", err: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["npm"], returncode=rc, stdout=out, stderr=err)


# --- 1. the export-mode public build fails loud, never fixtures ---------------


def test_assert_export_present_missing_dir_fails_loud(tmp_path: Path) -> None:
    with pytest.raises(P.PublishError, match="absent"):
        P.assert_export_present(tmp_path / "national")


def test_assert_export_present_missing_manifest_fails_loud(tmp_path: Path) -> None:
    (tmp_path / "web").mkdir()  # a web dir but no manifest → not a real export
    with pytest.raises(P.PublishError, match="not a real export"):
        P.assert_export_present(tmp_path)


def test_assert_export_present_missing_web_fails_loud(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(P.PublishError, match="web/"):
        P.assert_export_present(tmp_path)


def test_assert_export_present_ok(tmp_path: Path) -> None:
    root = _national_bundle(tmp_path / "national")
    assert P.assert_export_present(root) == root


def test_public_export_dir_defaults_to_national_never_fixtures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SIG_EXPORT_DIR", raising=False)
    assert P.public_export_dir(tmp_path) == tmp_path / "exports" / "out" / "national"
    monkeypatch.setenv("SIG_EXPORT_DIR", "/somewhere/else")
    assert P.public_export_dir(tmp_path) == Path("/somewhere/else")


def test_build_public_web_fails_loud_without_export(tmp_path: Path) -> None:
    (tmp_path / "web").mkdir()

    def runner(cmd, **kw):  # pragma: no cover - must never be reached
        raise AssertionError("the build ran despite a missing export")

    with pytest.raises(P.PublishError, match="absent"):
        P.build_public_web(repo_root=tmp_path, export_dir=tmp_path / "national", runner=runner)


def test_build_public_web_uses_export_mode_and_national_dir(tmp_path: Path) -> None:
    (tmp_path / "web").mkdir()
    export = _national_bundle(tmp_path / "national")
    seen: dict[str, str] = {}

    def runner(cmd, *, env, **kw):
        seen.update(env)
        (tmp_path / "web" / "dist").mkdir(exist_ok=True)
        (tmp_path / "web" / "dist" / "index.html").write_text("<html></html>")
        return _completed(0)

    dist = P.build_public_web(repo_root=tmp_path, export_dir=export, runner=runner)
    assert dist == tmp_path / "web" / "dist"
    assert seen["SIG_DATA_SOURCE"] == "export"  # never fixtures for the public build
    assert seen["SIG_EXPORT_DIR"] == str(export)


def test_build_public_web_fails_loud_on_broken_build(tmp_path: Path) -> None:
    (tmp_path / "web").mkdir()
    export = _national_bundle(tmp_path / "national")

    def runner(cmd, **kw):
        return _completed(1, err="astro blew up")

    with pytest.raises(P.PublishError, match="FAILED"):
        P.build_public_web(repo_root=tmp_path, export_dir=export, runner=runner)


# --- 2. only the published compartment goes public ----------------------------


@pytest.mark.parametrize(
    ("compartment", "license_id", "expected"),
    [
        ("sig_graph", "CC-BY-4.0", "public"),
        ("web", "CC-BY-4.0", "public"),
        ("metadata", "CC-BY-4.0", "public"),
        ("ontology", "CC0-1.0", "public"),
        ("osm_physical", "ODbL-1.0", "restricted"),  # share-alike
        ("portal", "CC-BY-SA-4.0", "restricted"),  # share-alike
        ("mystery", "UNDETERMINED", "restricted"),  # unknown licence
        ("mystery", None, "restricted"),  # no licence at all
    ],
)
def test_classify_compartment_against_shipped_licenses(
    compartment: str, license_id: str | None, expected: str
) -> None:
    # registry=None → the real policy/data/licenses.toml (pins ODbL/CC-BY-SA share-alike).
    assert P.classify_compartment(compartment, license_id, None) == expected


def test_partition_places_compartments_correctly(tmp_path: Path) -> None:
    export = _national_bundle(tmp_path / "national")
    result = P.partition_export(export, tmp_path / "public", tmp_path / "restricted")
    assert set(result.public_artifacts) == {
        "sig_graph/claims.csv",
        "web/map.json",
        "web/dossiers.json",
        "datapackage.json",
    }
    assert set(result.restricted_artifacts) == {"osm_physical/devices.csv", "portal/eyes.csv"}
    # files physically landed in the right tree
    assert (tmp_path / "public" / "sig_graph" / "claims.csv").is_file()
    assert (tmp_path / "restricted" / "osm_physical" / "devices.csv").is_file()
    assert not (tmp_path / "public" / "osm_physical" / "devices.csv").exists()
    assert result.watermark["ruleset_version"] == "resolver-ruleset-2026.07"


def test_assert_public_clean_passes_on_partitioned_public_tree(tmp_path: Path) -> None:
    export = _national_bundle(tmp_path / "national")
    P.partition_export(export, tmp_path / "public", tmp_path / "restricted")
    P.assert_public_clean(tmp_path / "public")  # must not raise


def test_assert_public_clean_raises_on_odbl_leak(tmp_path: Path) -> None:
    # A producer bug leaks the ODbL layer into the public tree.
    leaked = _write_export(
        tmp_path / "public",
        [
            {"path": "sig_graph/claims.csv", "compartment": "sig_graph", "license": "CC-BY-4.0"},
            {
                "path": "osm_physical/devices.csv",
                "compartment": "osm_physical",
                "license": "ODbL-1.0",
            },
        ],
    )
    with pytest.raises(P.CompartmentLeak, match="osm_physical"):
        P.assert_public_clean(leaked)


def test_assert_public_clean_raises_on_undetermined_leak(tmp_path: Path) -> None:
    leaked = _write_export(
        tmp_path / "public",
        [{"path": "mystery/x.csv", "compartment": "mystery", "license": "UNDETERMINED"}],
    )
    with pytest.raises(P.CompartmentLeak, match="UNDETERMINED"):
        P.assert_public_clean(leaked)


def test_assert_public_clean_raises_on_stray_unlisted_file(tmp_path: Path) -> None:
    export = _national_bundle(tmp_path / "national")
    P.partition_export(export, tmp_path / "public", tmp_path / "restricted")
    # a restricted file copied in outside the manifest must still be caught
    (tmp_path / "public" / "osm_physical").mkdir(parents=True, exist_ok=True)
    (tmp_path / "public" / "osm_physical" / "sneaked.csv").write_text("odbl", encoding="utf-8")
    with pytest.raises(P.CompartmentLeak, match="not a published artifact"):
        P.assert_public_clean(tmp_path / "public")


# --- 3. built-from watermark + deploy wiring ----------------------------------


def test_export_watermark_extracts_release_and_ruleset(tmp_path: Path) -> None:
    export = _national_bundle(tmp_path / "national")
    wm = P.export_watermark(export)
    assert wm["release_id"] == "sig-2026-09-22-abcd1234"
    assert wm["as_of_snapshot"] == "2026-09-22"
    assert wm["ruleset_version"] == "resolver-ruleset-2026.07"


def test_run_public_prepare_end_to_end(tmp_path: Path) -> None:
    (tmp_path / "web").mkdir()
    export = _national_bundle(tmp_path / "national")

    def runner(cmd, *, env, **kw):
        (tmp_path / "web" / "dist").mkdir(exist_ok=True)
        (tmp_path / "web" / "dist" / "index.html").write_text("<html></html>")
        return _completed(0)

    result = P.run_public_prepare(repo_root=tmp_path, export_dir=export, runner=runner)
    assert result.dist == tmp_path / "web" / "dist"
    # public has the CC-BY graph, restricted has the ODbL layer — proven clean
    assert "sig_graph/claims.csv" in result.partition.public_artifacts
    assert "osm_physical/devices.csv" in result.partition.restricted_artifacts
    P.assert_public_clean(tmp_path / "exports" / "out" / "public")  # no raise
    assert result.partition.watermark["release_id"] == "sig-2026-09-22-abcd1234"


def test_deploy_plan_includes_export_build_partition_and_keeps_split() -> None:
    plan = D.build_gcp_plan(project="p", region="r")
    joined = "\n".join(plan.steps)
    # deliverable 1: the export-mode public build, fail-loud, pointed at the national export
    assert "SIG_DATA_SOURCE=export" in joined and "exports/out/national" in joined
    assert "FAILS LOUD" in joined
    # deliverable 2: partition + the public/restricted split is preserved
    assert "exports/out/public" in joined and "exports/out/restricted" in joined
    assert "sig-public  (PUBLISHED compartment only, public-read)" in joined
    assert "sig-restricted  (non-published compartments, PRIVATE)" in joined
