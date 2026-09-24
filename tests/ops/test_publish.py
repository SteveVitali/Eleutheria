# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The public cut-over producer (`ops/src/ops/publish.py`, ADR-096 as superseded by ADR-106).

Two invariants under test: (1) the public build reads the real national export or fails
LOUD (never a fixtures fall-back, §38.1); (2) only licence-separated, publishable
compartments go public — the share-alike ODbL/CC-BY-SA compartments publish as their OWN
compartments (ADR-106, operator decision 2026-09-24), while no UNDETERMINED / excluded /
mixed-licence byte reaches a public object and no public compartment ever carries two
licences (§42 / Part VIII; ODbL never merged with CC-BY, 4.4(a)). The classification runs
against the SHIPPED `policy/data/licenses.toml`.
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
    """A national export: a CC-BY graph, the ODbL OSM layer, a CC-BY-SA portal, web JSONs
    (the map surface drawing on several licences — a mixed-licence render input), and an
    UNDETERMINED stray the producer must keep private."""
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
            {
                "path": "web/tiles/osm_physical-sites.pmtiles",
                "compartment": "osm_physical",
                "license": "ODbL-1.0",
            },
            {
                "path": "web/map.json",
                "compartment": "web",
                "license": "CC-BY-4.0 AND CC-BY-SA-4.0 AND ODbL-1.0",
            },
            {"path": "web/dossiers.json", "compartment": "web", "license": "CC-BY-4.0"},
            {"path": "datapackage.json", "compartment": "metadata", "license": "CC-BY-4.0"},
            {"path": "mystery/x.csv", "compartment": "mystery", "license": "UNDETERMINED"},
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


def test_build_public_web_strips_the_non_public_curation_shell(tmp_path: Path) -> None:
    # P30.3: /curate/** is the authenticated curation surface ("not public", ADR-068).
    (tmp_path / "web").mkdir()
    export = _national_bundle(tmp_path / "national")

    def runner(cmd, *, env, **kw):
        dist = tmp_path / "web" / "dist"
        (dist / "curate" / "tasks").mkdir(parents=True, exist_ok=True)
        (dist / "curate" / "index.html").write_text("<html>curation</html>")
        (dist / "index.html").write_text("<html></html>")
        return _completed(0)

    dist = P.build_public_web(repo_root=tmp_path, export_dir=export, runner=runner)
    assert (dist / "index.html").is_file()
    assert not (dist / "curate").exists()


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
        # ADR-106: share-alike compartments are PUBLIC as their own separate compartments
        ("osm_physical", "ODbL-1.0", "public"),
        ("portal", "CC-BY-SA-4.0", "public"),
        ("dot511_ccbysa2", "CC-BY-SA-2.0", "public"),
        ("mystery", "UNDETERMINED", "restricted"),  # unknown licence
        ("mystery", None, "restricted"),  # no licence at all
        ("mystery", "", "restricted"),  # empty licence
        ("web", "CC-BY-4.0 AND ODbL-1.0", "restricted"),  # mixed-licence artifact
        ("web", "ODbL-1.0 OR CC-BY-4.0", "restricted"),  # compound expression
        ("osm_physical", "CC-BY-4.0", "restricted"),  # licence disagrees with compartment
        ("sig_graph", "ODbL-1.0", "restricted"),  # ODbL filed into the CC-BY graph
    ],
)
def test_classify_compartment_against_shipped_licenses(
    compartment: str, license_id: str | None, expected: str
) -> None:
    # registry=None → the real policy/data/licenses.toml.
    assert P.classify_compartment(compartment, license_id, None) == expected


@pytest.mark.parametrize(
    ("compartment", "license_id", "reason"),
    [
        ("osm_physical", "ODbL-1.0", None),
        ("mystery", "UNDETERMINED", "unknown-licence"),
        ("web", "CC-BY-4.0 AND ODbL-1.0", "mixed-licence"),
        ("web", ["CC-BY-4.0", "ODbL-1.0"], "mixed-licence"),
        ("sig_graph", "ODbL-1.0", "compartment-licence-mismatch"),
    ],
)
def test_restriction_reason_names_why(compartment: str, license_id: object, reason: str) -> None:
    assert P.restriction_reason(compartment, license_id, None) == reason


def test_a_recorded_export_exclusion_stays_restricted() -> None:
    registry = {
        "licenses": {
            "LicenseRef-Pending": {
                "share_alike": False,
                "relicensable_to": ["LicenseRef-Pending"],
                "export_disposition": "excluded",
                "exclusion": "counsel-pending",
            }
        },
        "compartments": {},
    }
    assert P.restriction_reason("x", "LicenseRef-Pending", registry) == "excluded:counsel-pending"
    assert P.classify_compartment("x", "LicenseRef-Pending", registry) == "restricted"


def test_partition_places_compartments_correctly(tmp_path: Path) -> None:
    export = _national_bundle(tmp_path / "national")
    result = P.partition_export(export, tmp_path / "public", tmp_path / "restricted")
    assert set(result.public_artifacts) == {
        "sig_graph/claims.csv",
        "osm_physical/devices.csv",
        "portal/eyes.csv",
        "web/tiles/osm_physical-sites.pmtiles",
        "web/dossiers.json",
        "datapackage.json",
    }
    # the mixed-licence render input + the UNDETERMINED stray stay PRIVATE
    assert set(result.restricted_artifacts) == {"web/map.json", "mystery/x.csv"}
    # files physically landed in the right tree
    assert (tmp_path / "public" / "sig_graph" / "claims.csv").is_file()
    assert (tmp_path / "public" / "osm_physical" / "devices.csv").is_file()
    assert (tmp_path / "restricted" / "web" / "map.json").is_file()
    assert (tmp_path / "restricted" / "mystery" / "x.csv").is_file()
    assert not (tmp_path / "public" / "web" / "map.json").exists()
    assert not (tmp_path / "public" / "mystery" / "x.csv").exists()
    assert result.watermark["ruleset_version"] == "resolver-ruleset-2026.07"


def test_assert_public_clean_passes_on_partitioned_public_tree(tmp_path: Path) -> None:
    export = _national_bundle(tmp_path / "national")
    P.partition_export(export, tmp_path / "public", tmp_path / "restricted")
    P.assert_public_clean(tmp_path / "public")  # must not raise


def test_a_separate_odbl_compartment_is_clean(tmp_path: Path) -> None:
    # ADR-106: the ODbL layer in its OWN compartment beside the CC-BY graph is publishable.
    public = _write_export(
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
    P.assert_public_clean(public)  # must not raise


def test_assert_public_clean_raises_on_odbl_merged_into_the_ccby_graph(tmp_path: Path) -> None:
    # A producer bug files ODbL rows into the CC-BY graph compartment → a mixed compartment.
    leaked = _write_export(
        tmp_path / "public",
        [
            {"path": "sig_graph/claims.csv", "compartment": "sig_graph", "license": "CC-BY-4.0"},
            {"path": "sig_graph/osm.csv", "compartment": "sig_graph", "license": "ODbL-1.0"},
        ],
    )
    with pytest.raises(P.CompartmentLeak, match="compartment-licence-mismatch") as exc:
        P.assert_public_clean(leaked)
    assert "mixes licences" in str(exc.value)


def test_assert_public_clean_raises_on_a_mixed_licence_artifact(tmp_path: Path) -> None:
    leaked = _write_export(
        tmp_path / "public",
        [
            {
                "path": "web/map.json",
                "compartment": "web",
                "license": "CC-BY-4.0 AND ODbL-1.0",
            }
        ],
    )
    with pytest.raises(P.CompartmentLeak, match="mixed-licence"):
        P.assert_public_clean(leaked)


def test_assert_public_clean_raises_on_an_unregistered_mixed_compartment(tmp_path: Path) -> None:
    # Two single-licence artifacts in one UNregistered compartment (e.g. `web`) still mix.
    leaked = _write_export(
        tmp_path / "public",
        [
            {"path": "web/a.json", "compartment": "web", "license": "CC-BY-4.0"},
            {"path": "web/b.json", "compartment": "web", "license": "ODbL-1.0"},
        ],
    )
    with pytest.raises(P.CompartmentLeak, match="mixes licences"):
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
    # public carries the CC-BY graph AND the separate ODbL compartment; the mixed render
    # input + the UNDETERMINED stray are restricted — proven clean
    assert "sig_graph/claims.csv" in result.partition.public_artifacts
    assert "osm_physical/devices.csv" in result.partition.public_artifacts
    assert "web/map.json" in result.partition.restricted_artifacts
    assert "mystery/x.csv" in result.partition.restricted_artifacts
    public = tmp_path / "exports" / "out" / "public"
    P.assert_public_clean(public)  # no raise
    assert (public / P.LICENCE_INDEX).is_file()
    assert result.partition.watermark["release_id"] == "sig-2026-09-22-abcd1234"


def test_licence_index_labels_every_public_compartment(tmp_path: Path) -> None:
    export = _national_bundle(tmp_path / "national")
    P.partition_export(export, tmp_path / "public", tmp_path / "restricted")
    out = P.write_licence_index(tmp_path / "public")
    doc = json.loads(out.read_text(encoding="utf-8"))
    by = {c["compartment"]: c for c in doc["compartments"]}
    assert set(by) == {"sig_graph", "osm_physical", "portal", "web", "metadata"}
    assert by["osm_physical"]["license"] == "ODbL-1.0"
    assert by["osm_physical"]["share_alike"] is True
    assert "OpenStreetMap contributors" in by["osm_physical"]["attribution"]
    assert by["osm_physical"]["license_url"] == "https://opendatacommons.org/licenses/odbl/1-0/"
    assert by["portal"]["license"] == "CC-BY-SA-4.0"
    assert by["sig_graph"]["license"] == "CC-BY-4.0"
    assert "web/tiles/osm_physical-sites.pmtiles" in by["osm_physical"]["paths"]
    # restricted artifacts are never indexed as public
    indexed = {p for c in doc["compartments"] for p in c["paths"]}
    assert "web/map.json" not in indexed and "mystery/x.csv" not in indexed
    P.assert_public_clean(tmp_path / "public")  # the index is not a stray data file


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
    assert "LICENCES.json" in joined  # each public compartment labelled (ADR-106)
