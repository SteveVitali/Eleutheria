# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.13 / SIG-REL-009 (G3 §6.1–6.3) — the release provenance stamp.

Covers:

* ``sig.site-release/1`` — ``site_release_document`` renders the v2
  descriptor verbatim (SIG-MEM-011: never recomputed), ``validate_site_release``
  is fail-closed on every load-bearing field;
* the release build emits ``releases/<pub>/release.json`` plus the
  byte-identical site-root ``release.json``, outside the integrity-manifest
  hash cycle (its ``integrity_manifest.sha256`` names the manifest digest);
* ``validate_release`` cross-checks the object against the descriptor +
  manifest and fails on a missing, tampered or drifted copy — and on a
  release.json left on a v1 tree;
* every release page carries ``<meta name="sig-release">``, the
  ``describedby`` link and the §6.1 stamp line; record JSON twins carry the
  ``release``/``licence`` blocks;
* ``activate``/``rollback``/``clear_latest_pointer`` re-point the staged
  site-root release.json with the latest pointer — mutable overlay pages
  answer "latest view" and cite the fixed ``/r/<pub>/`` copy.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from exports.manifest import canonical_json, sha256_hex
from exports.release import (
    activate,
    build_release,
    clear_latest_pointer,
    rollback,
    validate_release,
)
from exports.release_pages import release_stamp_view

from exports import site_release as SR

T0 = datetime(2026, 10, 16, 12, 0, 0, tzinfo=UTC)
AS_OF_WORLD = "2026-10-16T00:00:00Z"
AS_OF_BELIEF = "2026-10-16T00:00:00Z"
COMMIT = "0a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d"


def _site_row(i: int) -> dict[str, Any]:
    return {
        "entity_type": "camera",
        "entity_id": f"ent-{i}",
        "source_id": "src_a",
        "label": f"Site {i}",
        "technology": "alpr",
        "jurisdiction": "OK",
        "claim_ids": [f"claim-{i}"],
        "geometry": None,
        "_rights": {
            "source_id": "src_a",
            "attribution_required": True,
            "attribution": "Test Source",
            "spdx": "CC-BY-4.0",
        },
    }


def _write_export(root: Path) -> Path:
    comp = "sig_graph"
    (root / comp).mkdir(parents=True)
    (root / "web").mkdir(parents=True)
    rows = [_site_row(1), _site_row(2)]
    (root / comp / "sites.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8"
    )
    (root / comp / "record_claims.jsonl").write_text(
        "".join(
            json.dumps(
                {
                    "claim_id": f"claim-{i}",
                    "entity_id": f"ent-{i}",
                    "source_id": "src_a",
                    "evidence_artifact_ids": [],
                }
            )
            + "\n"
            for i in (1, 2)
        ),
        encoding="utf-8",
    )
    (root / "web" / "evidence.json").write_text(
        json.dumps({"artifacts": [], "claim_views": []}), encoding="utf-8"
    )
    manifest: dict[str, Any] = {
        "artifacts": [
            {
                "path": f"{comp}/sites.jsonl",
                "compartment": comp,
                "license": "CC-BY-4.0",
                "sha256": "0" * 64,
                "byte_size": 1,
                "media_type": "application/json",
            },
            {
                "path": "web/terms_disclosure.json",
                "compartment": "web",
                "license": "CC-BY-4.0",
                "sha256": "1" * 64,
                "byte_size": 1,
                "media_type": "application/json",
            },
        ],
        "concept_id": "sig",
        "content_key": "a" * 64,
        "release_id": "sig-export-20261016T000000Z-deadbeef",
        "reproducibility_inputs": {
            "as_of_belief": "2026-10-16",
            "as_of_snapshot": "2026-10-16",
            "resolver_version": "0.1.0+g00000000",
            "ruleset_version": "p27.3/1.0.0",
        },
        "snapshot": {
            "as_of_world": AS_OF_WORLD,
            "as_of_belief": AS_OF_BELIEF,
            "belief_pinned": False,
            "spine_watermark": "claims=42 closed=0 bump=42",
            "materialize_run": None,
            "sqitch_head": "p35.13-test-head",
            "restore_point": None,
        },
        "environment": "fixture",
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def _v2_build(
    tmp_path: Path,
    export: Path,
    name: str = "rel",
    registry: Path | None = None,
    **kw: Any,
):
    kw.setdefault("descriptor_version", 2)
    kw.setdefault("built_at", T0)
    kw.setdefault("code_commit", COMMIT)
    kw.setdefault("code_tree", "clean")
    kw.setdefault("ontology_generated_sha256", "b" * 64)
    if registry is None:
        registry = tmp_path / "registry"
    if "label" not in kw and "labels_registry" not in kw:
        kw["labels_registry"] = registry
    return build_release(export, tmp_path / name, **kw)


def _v1_build(tmp_path: Path, export: Path, name: str = "rel-v1", **kw: Any):
    kw.setdefault("descriptor_version", 1)
    kw.setdefault("built_at", T0)
    kw.setdefault("code_commit", COMMIT)
    kw.setdefault("renderer_revision", "p35.13-test-renderer")
    return build_release(export, tmp_path / name, **kw)


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# The document + its validator                                                 #
# --------------------------------------------------------------------------- #


def test_document_renders_descriptor_fields_verbatim(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _v2_build(tmp_path, export)
    doc = _json(build.out_dir / f"releases/{build.publication_id}/release.json")
    desc = build.descriptor
    assert doc["schema"] == "sig.site-release/1"
    assert doc["label"] == desc["label"]
    assert doc["publication_id"] == build.publication_id
    assert doc["descriptor_sha256"] == sha256_hex(canonical_json(desc))
    assert doc["as_of_world"] == desc["snapshot"]["as_of_world"]
    assert doc["as_of_belief"] == desc["snapshot"]["as_of_belief"]
    assert doc["belief_pinned"] == desc["snapshot"]["belief_pinned"]
    assert doc["spine_watermark"] == desc["snapshot"]["spine_watermark"]
    assert doc["built_at"] == desc["build"]["built_at"]
    assert doc["code"]["commit"] == COMMIT
    assert doc["code"]["url"].endswith(f"/commit/{COMMIT}")
    assert doc["integrity_manifest"] == {
        "path": f"releases/{build.publication_id}/integrity_manifest.json",
        "sha256": build.manifest_sha256,
    }
    assert SR.validate_site_release(doc) == []


def test_document_refuses_a_v1_descriptor() -> None:
    with pytest.raises(ValueError, match="sig.publication-descriptor/2"):
        SR.site_release_document(
            {"schema": "sig.publication-descriptor/1"},
            "p-" + "a" * 64,
            integrity_manifest_sha256="0" * 64,
            routes_sha256=None,
        )


def test_validator_is_fail_closed_per_field() -> None:
    good = {
        "schema": "sig.site-release/1",
        "label": "sig-2026-10-16.1",
        "publication_id": "p-" + "a" * 64,
        "descriptor_sha256": "b" * 64,
        "as_of_world": AS_OF_WORLD,
        "as_of_belief": AS_OF_BELIEF,
        "belief_pinned": True,
        "spine_watermark": "claims=42",
        "built_at": "2026-10-16T12:00:00Z",
        "code": {
            "commit": COMMIT,
            "url": f"https://github.com/SteveVitali/Eleutheria/commit/{COMMIT}",
            "repository": "https://github.com/SteveVitali/Eleutheria",
        },
        "versions": {},
        "evaluation": {"status": "gate_pending", "deferral_refs": []},
        "disclosures": [],
        "routes_sha256": "c" * 64,
        "integrity_manifest": {
            "path": "releases/" + "p-" + "a" * 64 + "/integrity_manifest.json",
            "sha256": "d" * 64,
        },
    }
    assert SR.validate_site_release(good) == []
    # Every load-bearing field: absent/wrong is a named failure.
    for field, bad in [
        ("schema", "sig.site-release/0"),
        ("label", "release-1"),
        ("publication_id", "p-xyz"),
        ("descriptor_sha256", "zz"),
        ("as_of_world", "October 16"),
        ("as_of_belief", None),
        ("belief_pinned", "yes"),
        ("built_at", "not-an-instant"),
    ]:
        doc = {**good, field: bad}
        assert SR.validate_site_release(doc), f"{field}={bad!r} must fail"
    for code_bad in [
        None,
        {"commit": "short", "url": "u", "repository": "r"},
        {"commit": COMMIT, "repository": "r"},  # url absent — no link
    ]:
        doc = {**good, "code": code_bad}
        assert SR.validate_site_release(doc), f"code={code_bad!r} must fail"
    doc = {**good, "integrity_manifest": {"path": "x", "sha256": "zz"}}
    assert SR.validate_site_release(doc)
    # Declared-empty ancillary fields are honest, never failures.
    doc = {**good, "routes_sha256": None, "spine_watermark": None}
    assert SR.validate_site_release(doc) == []


# --------------------------------------------------------------------------- #
# The build emits the object — placement, copies, the hash cycle               #
# --------------------------------------------------------------------------- #


def test_v2_build_emits_both_copies_byte_identical(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _v2_build(tmp_path, export)
    pub = build.publication_id
    ns = build.out_dir / f"releases/{pub}/release.json"
    root = build.out_dir / "release.json"
    assert ns.is_file() and root.is_file()
    assert ns.read_bytes() == root.read_bytes()
    # Outside the integrity-manifest hash cycle (it names the digest).
    covered = {
        a["path"]
        for a in _json(build.out_dir / f"releases/{pub}/integrity_manifest.json")["artifacts"]
    }
    assert f"releases/{pub}/release.json" not in covered
    assert "release.json" not in covered


def test_validate_release_passes_clean_and_fails_on_tamper(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _v2_build(tmp_path, export)
    pub = build.publication_id
    assert validate_release(build.out_dir).state == "complete"

    # Tampered namespace copy → field cross-check fails.
    tampered = tmp_path / "t1"
    shutil.copytree(build.out_dir, tampered)
    doc = _json(tampered / f"releases/{pub}/release.json")
    doc["label"] = "sig-1999-01-01.9"
    (tampered / f"releases/{pub}/release.json").write_bytes(canonical_json(doc))
    report = validate_release(tampered)
    assert report.state != "complete"
    assert any("release.json" in f for f in report.failures)

    # Missing root copy → describedby dead-ends, named a failure.
    missing = tmp_path / "t2"
    shutil.copytree(build.out_dir, missing)
    (missing / "release.json").unlink()
    report = validate_release(missing)
    assert report.state != "complete"
    assert any("site-root release.json" in f for f in report.failures)

    # Drifted root copy → the two copies must be byte-identical.
    drifted = tmp_path / "t3"
    shutil.copytree(build.out_dir, drifted)
    doc = _json(drifted / "release.json")
    doc["routes_sha256"] = None
    (drifted / "release.json").write_bytes(canonical_json(doc))
    report = validate_release(drifted)
    assert report.state != "complete"
    assert any("byte-identical" in f for f in report.failures)


def test_release_json_on_a_v1_tree_is_a_failure(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _v1_build(tmp_path, export)
    pub = build.publication_id
    assert not (build.out_dir / "release.json").exists()
    assert not (build.out_dir / f"releases/{pub}/release.json").exists()
    # Plant a stray file — a v1 tree must not carry the v2 object.
    (build.out_dir / "release.json").write_bytes(b"{}")
    report = validate_release(build.out_dir)
    assert report.state != "complete"
    assert any("non-v2" in f for f in report.failures)


# --------------------------------------------------------------------------- #
# The stamp on the emitted pages + JSON twins                                  #
# --------------------------------------------------------------------------- #


def test_every_release_page_carries_the_stamp(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _v2_build(tmp_path, export)
    pub = build.publication_id
    label = build.descriptor["label"]
    pages = [
        build.out_dir / f"releases/{pub}/index.html",
        build.out_dir / f"r/{pub}/index.html",
        build.out_dir / f"r/{pub}/c/sig_graph/index.html",
        build.out_dir / f"r/{pub}/c/sig_graph/entity/camera/ent-1/index.html",
        build.out_dir / f"r/{pub}/c/sig_graph/browse/camera/1/index.html",
    ]
    for page in pages:
        assert page.is_file(), page
        html = page.read_text(encoding="utf-8")
        assert f'<meta name="sig-release" content="{label} {pub}">' in html, page
        assert (
            '<link rel="describedby" type="application/json" '
            f'href="/releases/{pub}/release.json">' in html
        ), page
        assert f"Release {label} · data as of 2026-10-16 00:00 UTC" in html, page
        assert "This is the fixed copy of this release" in html, page
        assert COMMIT[:8] in html, page


def test_record_json_carries_release_and_licence_blocks(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _v2_build(tmp_path, export)
    pub = build.publication_id
    rec = _json(build.out_dir / f"r/{pub}/c/sig_graph/entity/camera/ent-1.json")
    assert rec["release"] == {
        "label": build.descriptor["label"],
        "publication_id": pub,
        "as_of_world": AS_OF_WORLD,
    }
    assert rec["licence"] == {"id": "CC-BY-4.0", "compartment": "sig_graph"}


def test_v1_pages_stay_honestly_unstamped(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _v1_build(tmp_path, export)
    pub = build.publication_id
    page = build.out_dir / f"releases/{pub}/index.html"
    html = page.read_text(encoding="utf-8")
    assert 'name="sig-release"' not in html
    assert 'rel="describedby"' not in html
    # And its record JSON declares the blocks empty, never fabricated.
    rec = _json(build.out_dir / f"r/{pub}/c/sig_graph/entity/camera/ent-1.json")
    assert rec["release"]["label"] is None
    assert rec["release"]["publication_id"] == pub
    assert rec["licence"] == {"id": "CC-BY-4.0", "compartment": "sig_graph"}


def test_stamp_never_overclaims_the_descriptor_posture(tmp_path: Path) -> None:
    """SIG-REL-009 interim-text rule (G3 §6.1 NEW-2): the stamp's wording
    reflects the descriptor's ACTUAL posture — the fixture release is not
    belief-pinned, so no stamp anywhere in the emitted tree may call itself
    'pinned', and the site-release object reports `belief_pinned: false`
    verbatim, never an upgraded claim."""
    import re

    export = _write_export(tmp_path / "export")
    build = _v2_build(tmp_path, export)
    assert build.descriptor["snapshot"]["belief_pinned"] is False
    assert _json(build.out_dir / "release.json")["belief_pinned"] is False
    stamps = 0
    for html_path in build.out_dir.rglob("*.html"):
        for m in re.finditer(
            r'<p class="stamp[^"]*">(.*?)</p>',
            html_path.read_text(encoding="utf-8"),
        ):
            stamps += 1
            text = re.sub(r"<[^>]+>", "", m.group(1))
            assert "pinned" not in text.lower(), (
                f"{html_path}: the stamp claims a pinning posture the descriptor does not evidence"
            )
    assert stamps > 0, "the stamped release must actually render stamps"


# --------------------------------------------------------------------------- #
# release_stamp_view — the layout projection                                   #
# --------------------------------------------------------------------------- #


def test_stamp_view_projects_and_none_passes() -> None:
    assert release_stamp_view(None, describedby="/release.json") is None
    assert release_stamp_view({"label": 1}, describedby="/release.json") is None
    view = release_stamp_view(
        {
            "label": "sig-2026-10-16.1",
            "publication_id": "p-" + "a" * 64,
            "as_of_world": "2026-10-16T00:00:00Z",
            "built_at": "2026-10-16T12:00:00Z",
            "code": {
                "commit": COMMIT,
                "url": f"https://x/commit/{COMMIT}",
            },
        },
        describedby="/release.json",
        variant="latest",
    )
    assert view == {
        "label": "sig-2026-10-16.1",
        "publication_id": "p-" + "a" * 64,
        "pub_short": "p-aaaaaaaa…",
        "as_of": "2026-10-16 00:00 UTC",
        "built": "2026-10-16 12:00 UTC",
        "commit8": COMMIT[:8],
        "commit_href": f"https://x/commit/{COMMIT}",
        "describedby": "/release.json",
        "variant": "latest",
    }


# --------------------------------------------------------------------------- #
# Activation — the site-root release.json follows the pointer                  #
# --------------------------------------------------------------------------- #


def test_activation_stages_root_release_json_and_mutable_stamps(
    tmp_path: Path,
) -> None:
    export = _write_export(tmp_path / "export")
    build = _v2_build(tmp_path, export)
    pub = build.publication_id
    registry = tmp_path / "registry"
    activate(registry, build.out_dir, now=T0)
    staged = registry / "staged"

    # The site-root object IS the active release's immutable bytes.
    assert (staged / "release.json").read_bytes() == (
        staged / f"releases/{pub}/release.json"
    ).read_bytes()

    # The mutable overlay names the release it answers for.
    index = (staged / "releases/index.html").read_text(encoding="utf-8")
    label = build.descriptor["label"]
    assert f'<meta name="sig-release" content="{label} {pub}">' in index
    assert 'href="/release.json"' in index
    assert "This is the latest view." in index
    assert f"/r/{pub}/" in index

    stub = (staged / "entity/camera/ent-1/index.html").read_text(encoding="utf-8")
    assert "This is the latest view." in stub


def test_rollback_repoints_root_release_json(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    a = _v2_build(tmp_path, export, name="a")
    b = _v2_build(tmp_path, export, name="b")
    registry = tmp_path / "registry"
    activate(registry, a.out_dir, now=T0)
    activate(registry, b.out_dir, now=T0)
    staged = registry / "staged"
    assert _json(staged / "release.json")["publication_id"] == b.publication_id

    rollback(registry, a.publication_id, now=T0)
    assert _json(staged / "release.json")["publication_id"] == a.publication_id
    assert (staged / "release.json").read_bytes() == (
        staged / f"releases/{a.publication_id}/release.json"
    ).read_bytes()


def test_clear_latest_pointer_removes_root_release_json(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _v2_build(tmp_path, export)
    registry = tmp_path / "registry"
    activate(registry, build.out_dir, now=T0)
    staged = registry / "staged"
    assert (staged / "release.json").exists()
    clear_latest_pointer(registry, now=T0)
    assert not (staged / "release.json").exists()
    index = (staged / "releases/index.html").read_text(encoding="utf-8")
    assert 'name="sig-release"' not in index


def test_activation_of_a_v1_release_stays_unstamped(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _v1_build(tmp_path, export)
    registry = tmp_path / "registry"
    activate(registry, build.out_dir, now=T0)
    staged = registry / "staged"
    assert not (staged / "release.json").exists()
    index = (staged / "releases/index.html").read_text(encoding="utf-8")
    assert 'name="sig-release"' not in index
