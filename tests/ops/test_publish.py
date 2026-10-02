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
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from ops.gcs import GcsBucket

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
        ("web", "ODbL-1.0", "restricted"),  # an all-OSM map surface is not a SIG CC-BY surface
        ("nowhere", "CC-BY-4.0", "restricted"),  # a compartment nothing declares
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
        ("web", "ODbL-1.0", "compartment-licence-mismatch"),
        ("nowhere", "CC-BY-4.0", "unregistered-compartment"),
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


def test_web_analytics_partition_like_the_other_web_surfaces(tmp_path: Path) -> None:
    """P31.14: the ``web/analytics/`` family is a normal manifest-listed artifact —
    a single known licence in its declared compartment ships public; a compound
    ``AND`` label in the unregistered ``web_mixed`` partition stays PRIVATE."""
    export = _write_export(
        tmp_path / "national",
        [
            {
                "path": "web/analytics/density_bins.json",
                "compartment": "web_mixed",
                "license": "CC-BY-4.0 AND ODbL-1.0",
            },
            {
                "path": "web/analytics/centrality.json",
                "compartment": "web",
                "license": "CC-BY-4.0",
            },
            {
                "path": "web/analytics/provenance.json",
                "compartment": "web",
                "license": "CC-BY-4.0",
            },
        ],
    )
    result = P.partition_export(export, tmp_path / "public", tmp_path / "restricted")
    assert set(result.public_artifacts) == {
        "web/analytics/centrality.json",
        "web/analytics/provenance.json",
    }
    assert set(result.restricted_artifacts) == {"web/analytics/density_bins.json"}
    P.assert_public_clean(tmp_path / "public")  # the partitioned public tree stays clean


def test_assert_export_present_accepts_a_bundle_with_analytics(tmp_path: Path) -> None:
    root = _national_bundle(tmp_path / "national")
    (root / "web" / "analytics").mkdir(parents=True)
    assert P.assert_export_present(root) == root


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


def test_a_single_licence_non_ccby_map_surface_stays_restricted_and_publish_succeeds(
    tmp_path: Path,
) -> None:
    # Review finding (P30.3): an all-OSM export labels web/map.json ODbL-1.0; it must NOT
    # become a second licence in the public `web` compartment (which would fail the publish).
    export = _write_export(
        tmp_path / "national",
        [
            {
                "path": "osm_physical/sites.csv",
                "compartment": "osm_physical",
                "license": "ODbL-1.0",
            },
            {"path": "web/map.json", "compartment": "web", "license": "ODbL-1.0"},
            {"path": "web/coverage.json", "compartment": "web", "license": "CC-BY-4.0"},
        ],
    )
    result = P.partition_export(export, tmp_path / "public", tmp_path / "restricted")
    assert result.restricted_artifacts == ("web/map.json",)
    P.assert_public_clean(tmp_path / "public")  # no raise


def test_publishing_refuses_the_fixture_harness_presentation_data(tmp_path: Path) -> None:
    export = _national_bundle(tmp_path / "national")
    (export / "web" / "presentation").mkdir()
    with pytest.raises(P.PublishError, match="presentation"):
        P.assert_export_present(export)


def test_partition_fails_loud_on_a_listed_artifact_missing_on_disk(tmp_path: Path) -> None:
    export = _national_bundle(tmp_path / "national")
    (export / "portal" / "eyes.csv").unlink()
    with pytest.raises(P.PublishError, match="missing"):
        P.partition_export(export, tmp_path / "public", tmp_path / "restricted")


def test_the_site_may_not_serve_a_compartment_the_partition_withholds(tmp_path: Path) -> None:
    export = _national_bundle(tmp_path / "national")
    P.partition_export(export, tmp_path / "public", tmp_path / "restricted")
    dist = tmp_path / "dist"
    (dist / "tiles").mkdir(parents=True)
    (dist / "tiles" / "osm_physical-sites.pmtiles").write_bytes(b"PMTiles")
    P.assert_site_matches_partition(dist, tmp_path / "public")  # public tile → fine
    (dist / "tiles" / "withheld-sites.pmtiles").write_bytes(b"PMTiles")
    with pytest.raises(P.CompartmentLeak, match="withheld-sites"):
        P.assert_site_matches_partition(dist, tmp_path / "public")


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
    assert "sig-restricted  (non-published compartments, PRIVATE" in joined
    assert "LICENCES.json" in joined  # each public compartment labelled (ADR-106)


def test_deploy_plan_routes_public_publishes_through_publish_web() -> None:
    """P34.10 (SIG-OPS-004): the plan no longer prescribes a hand rsync to a
    public bucket — public bytes go through `sig-ops publish-web` only."""
    joined = "\n".join(D.build_gcp_plan(project="p", region="r").steps)
    assert "sig-ops publish-web" in joined
    assert "sig-web" in joined and "sig-public" in joined
    # no public-bucket sync step may be a bare hand rsync anymore
    public_steps = [
        s
        for s in D.build_gcp_plan(project="p", region="r").steps
        if "sig-web" in s or "sig-public" in s
    ]
    assert public_steps and all("gcloud storage rsync" not in s for s in public_steps)


# --- 4. the one allow-listed publish path (P34.10; SIG-OPS-003/004) ------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ALLOWLIST_PATH = _REPO_ROOT / "ops" / "public_routes.toml"


class _FakeSiteStore:
    """An in-memory object store driving a ``GcsBucket`` (upload/list/delete)."""

    def __init__(self, objects: dict[str, bytes] | None = None) -> None:
        self.objects: dict[str, bytes] = dict(objects or {})
        self.put_calls: list[str] = []
        self.delete_calls: list[str] = []

    def bucket(self) -> GcsBucket:
        import urllib.parse

        def opener(req, timeout):
            url = req.full_url
            method = req.get_method()
            if "/upload/storage/v1/" in url:
                name = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["name"][0]
                self.objects[name] = req.data or b""
                self.put_calls.append(name)
                return 200, b"{}"
            if method == "DELETE":
                name = urllib.parse.unquote(url.split("/o/", 1)[1].split("?")[0])
                self.objects.pop(name, None)
                self.delete_calls.append(name)
                return 200, b""
            prefix = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("prefix", [""])[0]
            items = [{"name": n} for n in sorted(self.objects) if n.startswith(prefix)]
            return 200, json.dumps({"items": items}).encode()

        return GcsBucket("fake-sig-web", token_provider=lambda: "fake", opener=opener)


def _emitted_top_level(filename: str) -> str:
    """The dist top-level entry a `src/pages`/`public` source file emits.

    Astro (trailingSlash=always) emits `index.astro`→`index.html`,
    `404.astro`→`404.html`, `foo.astro`→`foo/index.html` (top: `foo`), and a
    file endpoint `feed.xml.ts`→`feed.xml`; `public/` files pass verbatim.
    """
    if filename.endswith(".astro"):
        stem = filename[: -len(".astro")]
        return {"index": "index.html", "404": "404.html"}.get(stem, stem)
    if filename.endswith(".ts"):
        return filename[: -len(".ts")]  # an endpoint emits its literal name
    return filename


def _public_dist(root: Path) -> Path:
    """A minimal allow-listed site tree: every REQUIRED top-level entry from
    the committed allow-list (required names with a suffix are files; the rest
    are route dirs carrying an index.html)."""
    allow = P.load_allowlist(_ALLOWLIST_PATH)
    assert allow.required, "the committed allow-list must declare required entries"
    dist = root / "dist"
    for name in sorted(allow.required):
        if "." in name:
            dist.mkdir(parents=True, exist_ok=True)
            (dist / name).write_text(f"<html><body>{name}</body></html>", encoding="utf-8")
        else:
            sub = dist / name
            sub.mkdir(parents=True, exist_ok=True)
            (sub / ("app.css" if name == "_astro" else "index.html")).write_text(
                f"{name} content", encoding="utf-8"
            )
    return dist


def test_allowlist_committed_file_parses_and_carries_denied_routes() -> None:
    allow = P.load_allowlist(_ALLOWLIST_PATH)
    assert "index.html" in allow.top_level and "dossier" in allow.top_level
    # the contracted denied set (P34.10 deliverable 6)
    for route in ("/curate/", "/curate/submit/", "/releases/", "/research-dossier/", "/intake/"):
        assert route in allow.denied_routes
    assert any("demo" in r for r in allow.denied_routes)  # one demo page


def test_allowlist_missing_or_empty_fails_closed(tmp_path: Path) -> None:
    # an explicit path that does not exist refuses — never a silent substitute
    with pytest.raises(P.PublishError, match="does not exist"):
        P.load_allowlist(tmp_path / "nope.toml")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("SIG_PUBLIC_ROUTES", str(tmp_path / "nope2.toml"))
    try:
        with pytest.raises(P.PublishError, match="does not exist"):
            P.load_allowlist()
    finally:
        monkeypatch.undo()
    empty = tmp_path / "empty.toml"
    empty.write_text("[allowlist]\ntop_level = []\n", encoding="utf-8")
    with pytest.raises(P.PublishError, match="empty"):
        P.load_allowlist(empty)


def test_allowlisted_tree_passes_a_clean_build(tmp_path: Path) -> None:
    allow = P.load_allowlist(_ALLOWLIST_PATH)
    P.assert_allowlisted_tree(_public_dist(tmp_path), allow)  # no raise


@pytest.mark.parametrize("extra", ["curate", "releases", "research-dossier", "intake", "rogue"])
def test_allowlisted_tree_refuses_unlisted_top_level(tmp_path: Path, extra: str) -> None:
    allow = P.load_allowlist(_ALLOWLIST_PATH)
    dist = _public_dist(tmp_path)
    (dist / extra).mkdir()
    (dist / extra / "index.html").write_text("<html>leak</html>", encoding="utf-8")
    with pytest.raises(P.PublishError, match="not on the committed allow-list") as exc:
        P.assert_allowlisted_tree(dist, allow)
    assert extra in str(exc.value)


def test_allowlisted_tree_refuses_an_unlisted_file(tmp_path: Path) -> None:
    allow = P.load_allowlist(_ALLOWLIST_PATH)
    dist = _public_dist(tmp_path)
    (dist / "secret-plan.txt").write_text("internal", encoding="utf-8")
    with pytest.raises(P.PublishError, match="secret-plan.txt"):
        P.assert_allowlisted_tree(dist, allow)


def test_allowlisted_tree_refuses_a_build_missing_a_required_route(tmp_path: Path) -> None:
    """The other direction (G1 §3.2 item 6): a listed route the build silently
    dropped is a refusal too — an allow-list over an empty tree must not pass."""
    allow = P.load_allowlist(_ALLOWLIST_PATH)
    dist = _public_dist(tmp_path)
    shutil.rmtree(dist / "dossier")
    with pytest.raises(P.PublishError, match="required by the allow-list"):
        P.assert_allowlisted_tree(dist, allow)


def test_public_content_refuses_the_curation_banner(tmp_path: Path) -> None:
    dist = _public_dist(tmp_path)
    (dist / "corrections" / "index.html").write_text(
        '<html><p data-testid="curate-auth-banner">Authenticated curation</p></html>',
        encoding="utf-8",
    )
    with pytest.raises(P.PublishError, match="curate-auth-banner"):
        P.assert_public_tree_content(dist)


@pytest.mark.parametrize(
    "action",
    ['action="http://127.0.0.1:8001/curate/decide"', 'action="http://localhost:8001/x"'],
)
def test_public_content_refuses_loopback_form_actions(tmp_path: Path, action: str) -> None:
    dist = _public_dist(tmp_path)
    (dist / "corrections" / "index.html").write_text(
        f"<html><form method=post {action}></form></html>", encoding="utf-8"
    )
    with pytest.raises(P.PublishError, match="loopback"):
        P.assert_public_tree_content(dist)


def test_public_content_refuses_a_demo_task_page(tmp_path: Path) -> None:
    dist = _public_dist(tmp_path)
    task = dist / "task" / "new" / "abc"
    task.mkdir(parents=True)
    task.joinpath("index.html").write_text(
        '<html><dd data-testid="task-field-predicate">demo_not_researched</dd></html>',
        encoding="utf-8",
    )
    with pytest.raises(P.PublishError, match="demo_"):
        P.assert_public_tree_content(dist)


def test_public_content_refuses_demo_path_segments(tmp_path: Path) -> None:
    dist = _public_dist(tmp_path)
    demo = dist / "task" / "new" / "demo_roundtrip"
    demo.mkdir(parents=True)
    demo.joinpath("index.html").write_text("<html>demo</html>", encoding="utf-8")
    with pytest.raises(P.PublishError, match="demo_"):
        P.assert_public_tree_content(dist)


def test_public_content_passes_a_clean_tree(tmp_path: Path) -> None:
    P.assert_public_tree_content(_public_dist(tmp_path))  # no raise


def test_release_record_carries_the_contracted_fields(tmp_path: Path) -> None:
    dist = _public_dist(tmp_path)
    out = P.write_release_record(
        dist,
        release_id="web-20261003T000000Z-deadbeef",
        git_commit="deadbeefcafe",
        built_at="2026-10-03T00:00:00Z",
        data_release="sig-2026-09-27-ce480ab1",
        bucket="x-sig-web",
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == P.RELEASE_RECORD_SCHEMA
    assert doc["release_id"] == "web-20261003T000000Z-deadbeef"
    assert doc["git_commit"] == "deadbeefcafe"
    assert doc["built_at"] == "2026-10-03T00:00:00Z"
    assert doc["data_release"] == "sig-2026-09-27-ce480ab1"
    assert doc["image_digests"] == []  # recorded, empty for a static site
    assert doc["tree_digest"].startswith("sha256:")
    # the digest is reproducible over the tree minus the record itself
    assert doc["tree_digest"] == P.tree_digest(dist, exclude=frozenset({P.RELEASE_RECORD}))


def test_protected_object_marks_the_release_namespaces() -> None:
    for name in (
        "r/sig-2026/claims/x.json",
        "releases/sig-2026/index.html",
        "releases/index.html",
        "entity/abc.json",
        "conf/withdrawn_routes.conf",
        "compat_index.json",
        "release.json",
    ):
        assert P.is_protected_object(name), name
    for name in ("index.html", "curate/index.html", "task/new/x/index.html", "release2.json"):
        assert not P.is_protected_object(name), name


def test_plan_site_sync_never_deletes_release_trees() -> None:
    remote = [
        "index.html",  # kept (in local)
        "stale-page/index.html",  # retired — deleted
        "r/sig-2026/x.json",  # release tree — NEVER deleted
        "releases/sig-2026/index.html",  # release tree — NEVER deleted
        "releases/index.html",  # the release catalog — NEVER deleted
        "entity/e1.json",  # NEVER deleted
        "conf/withdrawn.conf",  # NEVER deleted
        "compat_index.json",  # NEVER deleted
    ]
    plan = P.plan_site_sync(["index.html"], remote)
    assert plan.deletes == ("stale-page/index.html",)
    for kept in ("r/sig-2026/x.json", "releases/index.html", "entity/e1.json"):
        assert kept in plan.protected_kept


def test_sync_tree_uploads_and_deletes_without_touching_release_namespaces(
    tmp_path: Path,
) -> None:
    store = _FakeSiteStore(
        {
            "old-page/index.html": b"stale",
            "r/sig-2026/x.json": b"release",
            "releases/sig-2026/index.html": b"catalog",
            "entity/e1.json": b"entity",
            "conf/withdrawn.conf": b"conf",
        }
    )
    dist = _public_dist(tmp_path)
    plan = P.sync_tree(store.bucket(), dist, delete_extras=True)
    assert store.objects["index.html"] == b"<html><body>index.html</body></html>"
    assert "old-page/index.html" in store.delete_calls
    assert "old-page/index.html" not in store.objects
    # the staged release namespaces survived the site redeploy untouched
    for name in (
        "r/sig-2026/x.json",
        "releases/sig-2026/index.html",
        "entity/e1.json",
        "conf/withdrawn.conf",
    ):
        assert store.objects[name] != b"" and name not in store.delete_calls
    assert "old-page/index.html" in plan.deletes


def test_sync_tree_append_only_leg_never_deletes(tmp_path: Path) -> None:
    store = _FakeSiteStore({"r/old/stale.json": b"still-there"})
    tree = tmp_path / "staged"
    (tree / "r" / "sig-x").mkdir(parents=True)
    (tree / "r" / "sig-x" / "index.html").write_text("rel", encoding="utf-8")
    P.sync_tree(store.bucket(), tree, delete_extras=False)
    assert store.delete_calls == []  # a publish NEVER deletes release bytes
    assert store.objects["r/old/stale.json"] == b"still-there"
    assert store.objects["r/sig-x/index.html"] == b"rel"


def test_sync_tree_refuses_a_plan_that_would_delete_a_protected_object(tmp_path: Path) -> None:
    store = _FakeSiteStore()
    dist = _public_dist(tmp_path)
    plan = P.SyncPlan(
        uploads=(), deletes=("r/sig-x/index.html",), protected_kept=(), remote_known=True
    )
    with pytest.raises(P.PublishError, match="protected"):
        P.sync_tree(store.bucket(), dist, delete_extras=True, plan=plan)
    assert store.delete_calls == []


def test_assert_release_tree_accepts_release_namespaces_only(tmp_path: Path) -> None:
    tree = tmp_path / "staged"
    for d in ("r", "releases", "entity", "conf"):
        (tree / d).mkdir(parents=True)
    (tree / "compat_index.json").write_text("{}", encoding="utf-8")
    P.assert_release_tree(tree)  # no raise
    (tree / "index.html").write_text("clobber", encoding="utf-8")
    with pytest.raises(P.PublishError, match="outside"):
        P.assert_release_tree(tree)


def _ok_absent_verify():
    from ops.observe import ProbeResult

    return [
        ProbeResult(
            service=f"absent-{n}", ok=True, latency_ms=1.0, ts="t", detail="absent (HTTP 404)"
        )
        for n in ("curate", "demo-task")
    ]


def test_publish_web_dry_run_plans_but_writes_nothing_remote(tmp_path: Path) -> None:
    store = _FakeSiteStore({"stale/index.html": b"x", "r/sig/a.json": b"keep"})
    dist = _public_dist(tmp_path)
    result = P.run_publish_web(
        dist=dist,
        apply=False,
        bucket=store.bucket(),
        allowlist_path=_ALLOWLIST_PATH,
        git_commit="c0ffee",
        now="2026-10-03T00:00:00Z",
    )
    assert not result.applied
    assert store.put_calls == [] and store.delete_calls == []  # dry-run mutates nothing remote
    assert "stale/index.html" in result.site_plan.deletes  # planned, not executed
    assert "r/sig/a.json" in result.site_plan.protected_kept
    assert (dist / P.RELEASE_RECORD).is_file()  # the record IS written locally
    assert result.record["release_id"].startswith("web-")


def test_publish_web_apply_syncs_once_and_probes(tmp_path: Path) -> None:
    store = _FakeSiteStore({"stale/index.html": b"x", "entity/e.json": b"keep"})
    dist = _public_dist(tmp_path)
    result = P.run_publish_web(
        dist=dist,
        apply=True,
        bucket=store.bucket(),
        allowlist_path=_ALLOWLIST_PATH,
        git_commit="c0ffee",
        now="2026-10-03T00:00:00Z",
        absent_verify=_ok_absent_verify,
    )
    assert result.applied
    assert store.delete_calls == ["stale/index.html"]  # exactly the unprotected extras
    assert store.objects["entity/e.json"] == b"keep"
    assert store.objects[P.RELEASE_RECORD]  # the record ships inside the tree
    assert len(result.absent_probes) == 2


def test_publish_web_apply_refuses_when_a_denied_route_is_present(tmp_path: Path) -> None:
    from ops.observe import ProbeResult

    store = _FakeSiteStore()
    dist = _public_dist(tmp_path)

    def present_probe():
        return [
            ProbeResult(
                service="absent-apex-curate",
                ok=False,
                latency_ms=1.0,
                ts="t",
                detail="present (HTTP 200)",
            )
        ]

    with pytest.raises(P.PublishError, match="denied routes are reachable"):
        P.run_publish_web(
            dist=dist,
            apply=True,
            bucket=store.bucket(),
            allowlist_path=_ALLOWLIST_PATH,
            git_commit="c0ffee",
            now="2026-10-03T00:00:00Z",
            absent_verify=present_probe,
        )


def test_publish_web_apply_refuses_zero_probe_coverage(tmp_path: Path) -> None:
    store = _FakeSiteStore()
    dist = _public_dist(tmp_path)
    with pytest.raises(P.PublishError, match="ZERO absence probes"):
        P.run_publish_web(
            dist=dist,
            apply=True,
            bucket=store.bucket(),
            allowlist_path=_ALLOWLIST_PATH,
            git_commit="c0ffee",
            now="2026-10-03T00:00:00Z",
            absent_verify=list,
        )


def test_publish_web_apply_requires_a_bucket(tmp_path: Path) -> None:
    dist = _public_dist(tmp_path)
    with pytest.raises(P.PublishError, match="destination bucket"):
        P.run_publish_web(
            dist=dist,
            apply=True,
            bucket=None,
            allowlist_path=_ALLOWLIST_PATH,
            git_commit="c0ffee",
            now="2026-10-03T00:00:00Z",
        )


def test_publish_web_refuses_before_any_write_on_a_leaking_tree(tmp_path: Path) -> None:
    store = _FakeSiteStore()
    dist = _public_dist(tmp_path)
    (dist / "curate").mkdir()
    (dist / "curate" / "index.html").write_text("<html>shell</html>", encoding="utf-8")
    with pytest.raises(P.PublishError, match="allow-list"):
        P.run_publish_web(
            dist=dist,
            apply=True,
            bucket=store.bucket(),
            allowlist_path=_ALLOWLIST_PATH,
            git_commit="c",
            now="2026-10-03T00:00:00Z",
        )
    assert store.put_calls == [] and store.delete_calls == []
    assert not (dist / P.RELEASE_RECORD).exists()  # refused before the record too


def test_publish_web_staged_tree_survives_and_publishes_in_the_same_run(
    tmp_path: Path,
) -> None:
    """AC: a staged release tree is published by the same command AND a
    bucket-resident staged tree survives a web redeploy."""
    store = _FakeSiteStore(
        {"r/sig-2026/claims/x.json": b"release bytes", "stale/index.html": b"old"}
    )
    dist = _public_dist(tmp_path)
    staged = tmp_path / "staged"
    (staged / "r" / "sig-2026-10" / "claims").mkdir(parents=True)
    (staged / "r" / "sig-2026-10" / "claims" / "a.json").write_text("{}", encoding="utf-8")
    (staged / "releases").mkdir()
    (staged / "releases" / "index.html").write_text("<html>catalog</html>", encoding="utf-8")
    result = P.run_publish_web(
        dist=dist,
        apply=True,
        bucket=store.bucket(),
        allowlist_path=_ALLOWLIST_PATH,
        release_tree=staged,
        git_commit="c0ffee",
        now="2026-10-03T00:00:00Z",
        absent_verify=_ok_absent_verify,
    )
    # one run: site extras deleted, staged tree uploaded, resident release bytes kept
    assert store.delete_calls == ["stale/index.html"]
    assert store.objects["r/sig-2026/claims/x.json"] == b"release bytes"
    assert store.objects["r/sig-2026-10/claims/a.json"] == b"{}"
    assert store.objects["releases/index.html"] == b"<html>catalog</html>"
    assert result.release_plan is not None and result.release_plan.deletes == ()


def test_publish_web_cli_dry_run_and_apply_guards(tmp_path: Path, monkeypatch) -> None:
    """The verb is dry-run by default; --apply without a bucket exits != 0."""
    from ops import cli

    dist = _public_dist(tmp_path)
    monkeypatch.delenv("SIG_GCP_PROJECT", raising=False)
    monkeypatch.delenv("SIG_WEB_BUCKET", raising=False)
    monkeypatch.delenv("SIG_PUBLIC_BUCKET", raising=False)
    rc = cli.main(["publish-web", "--dist", str(dist)])
    assert rc == 0  # dry-run: asserted + record written + plan printed
    rc = cli.main(["publish-web", "--dist", str(dist), "--apply"])
    assert rc != 0  # no destination bucket — refused, nothing synced


def test_every_denied_route_has_an_http_absent_probe_on_each_origin() -> None:
    """SIG-OPS-003: each [[denied]] route in the allow-list is probed absent on
    every public origin by the committed cadence rows."""
    from ops.scheduled import load_cadence

    allow = P.load_allowlist(_ALLOWLIST_PATH)
    cadence = load_cadence(_REPO_ROOT / "ops" / "cadence.toml")
    absent = [t for t in cadence.probe_targets if t.kind == "http-absent"]
    origins = {"surveillancegraph.org", "SIG_PROBE_WEB_URL", "storage.googleapis.com"}
    for route in allow.denied_routes:
        rows = [t for t in absent if t.path == route]
        covered = {
            "surveillancegraph.org"
            if "surveillancegraph.org" in t.url
            else (
                "SIG_PROBE_WEB_URL"
                if t.url_env == "SIG_PROBE_WEB_URL"
                else "storage.googleapis.com"
                if "storage.googleapis.com" in t.url
                else "?"
            )
            for t in rows
        }
        assert covered == origins, f"{route}: probed on {covered}, want all 3 origins"


def test_pages_dir_entries_are_allowlisted_or_internal() -> None:
    """Structural invariant: every top-level route source under src/pages maps
    to an allow-listed top-level entry, and the injected internal routes
    (web/src/internal + astro.config.mjs INTERNAL_ROUTES) map to routes that are
    NOT on the list — a route can never be both buildable-public and internal."""
    allow = P.load_allowlist(_ALLOWLIST_PATH)
    pages = _REPO_ROOT / "web" / "src" / "pages"
    internal = _REPO_ROOT / "web" / "src" / "internal"
    # the internal route sources moved out of src/pages (empty leftover dirs may
    # linger — a route exists iff a source FILE does)
    internal_tops = {e.stem if e.is_file() else e.name for e in internal.iterdir()}
    for f in pages.rglob("*"):
        if f.is_file():
            rel = f.relative_to(pages)
            top = rel.parent.name or rel.stem  # dir name, else file stem
            assert top not in internal_tops, f"{f}: internal route back under src/pages"
    for root in (pages, _REPO_ROOT / "web" / "public"):
        for entry in root.iterdir():
            top = entry.name if entry.is_dir() else _emitted_top_level(entry.name)
            assert top in allow.top_level, f"{root.name}/{entry.name} is not allow-listed"
    # no internal dir name may appear on the allow-list
    for entry in internal.iterdir():
        assert (entry.stem if entry.is_file() else entry.name) not in allow.top_level


def test_internal_routes_in_astro_config_are_off_the_allowlist() -> None:
    """The SIG_BUILD_INTERNAL injection table maps only to non-public routes."""
    import re as _re

    allow = P.load_allowlist(_ALLOWLIST_PATH)
    text = (_REPO_ROOT / "web" / "astro.config.mjs").read_text(encoding="utf-8")
    block = text.split("INTERNAL_ROUTES", 1)[1].split("];", 1)[0]
    patterns = _re.findall(r'\["(/[^"]*)",', block)
    assert patterns, "INTERNAL_ROUTES table unreadable — the check must not vacuously pass"
    for pattern in patterns:
        top = pattern.strip("/").split("/")[0]
        assert top not in allow.top_level, f"internal route {pattern} is allow-listed"
        # every internal route is also a denied-probe route or an explicit
        # withdrawn surface the cadence file documents — at minimum it must not
        # be servable from the public build, which the allow-list membership
        # check above proves.


#: The web-build environment gate, mirroring `_require_web_env` in
#: tests/e2e/test_composed_stack.py: the CI `python` job runs this suite but
#: installs no Node / `web/node_modules` — only the CI `web` job does, so a
#: real `npm run build` there cannot run (rc 127 "astro: not found"). Skip
#: cleanly instead of failing; the same builds are exercised by the web job's
#: own `npm run build` / e2e / `check:perf` runs.
_WEB_BUILD_UNAVAILABLE = (
    shutil.which("npm") is None or not (_REPO_ROOT / "web" / "node_modules").exists()
)
_WEB_BUILD_SKIP = pytest.mark.skipif(
    _WEB_BUILD_UNAVAILABLE,
    reason="web build environment unavailable (no npm / web/node_modules); "
    "the web build is covered by the CI `web` job",
)


@_WEB_BUILD_SKIP
def test_default_web_build_emits_no_internal_routes(tmp_path: Path) -> None:
    """AC: a build without SIG_BUILD_INTERNAL emits no curate/ (or any other
    non-public route). The route gate lives in astro.config.mjs, orthogonal to
    SIG_DATA_SOURCE — the fixtures build this runs is the same config the
    export-mode publish build runs (exports/out is gitignored, so CI has no
    export to build against; the publish path composes this same gate)."""
    import subprocess as _sp

    env = dict(os.environ)
    env.pop("SIG_BUILD_INTERNAL", None)
    proc = _sp.run(
        ["npm", "--prefix", str(_REPO_ROOT / "web"), "run", "build"],
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT,
        env=env,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    dist = _REPO_ROOT / "web" / "dist"
    for internal in (
        "curate",
        "releases",
        "research-dossier",
        "contribution-back",
        "visual-language",
    ):
        assert not (dist / internal).exists(), f"public build emitted {internal}/"
    # and every emitted top-level entry IS on the committed allow-list
    P.assert_allowlisted_tree(dist, P.load_allowlist(_ALLOWLIST_PATH))


@_WEB_BUILD_SKIP
def test_internal_build_flag_restores_the_full_surface(tmp_path: Path) -> None:
    """SIG_BUILD_INTERNAL=1 (the web e2e suite's flag) emits the internal routes."""
    import os as _os
    import subprocess as _sp

    env = dict(_os.environ, SIG_BUILD_INTERNAL="1")
    proc = _sp.run(
        ["npm", "--prefix", str(_REPO_ROOT / "web"), "run", "build"],
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT,
        env=env,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    dist = _REPO_ROOT / "web" / "dist"
    assert (dist / "curate" / "index.html").is_file()
    assert (dist / "releases" / "index.html").is_file()
    assert (dist / "research-dossier" / "index.html").is_file()
