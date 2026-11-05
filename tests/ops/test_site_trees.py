# SPDX-License-Identifier: Apache-2.0
"""P36.66b (TX-13b split b, ADR-161/162, SIG-REL-008) — the ``v/<pub>/`` +
``s/<pub>/`` site-tree assembly (the withdrawal index ``page_index.json``,
the release.json copies, the latest-view overlays, the containment scan)
and the ``selectors.conf`` edge registry the promotion composes."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ops import release_conf as rc
from ops import release_pipeline as rp
from ops import site_trees as st

PUB = "p-" + "a" * 64
NOW = datetime(2026, 11, 4, 12, 0, 0, tzinfo=UTC)


def _work_dir(tmp_path: Path) -> Path:
    """A built release's work_dir shape: releases/<pub>/ + release.json +
    one record row under r/<pub>/c/<comp>/."""
    work = tmp_path / "work"
    (work / "releases" / PUB).mkdir(parents=True)
    (work / "releases" / PUB / "release.json").write_text(
        json.dumps({"schema": "sig.site-release/1", "publication_id": PUB})
    )
    comp = work / "r" / PUB / "c" / "sig_graph"
    comp.mkdir(parents=True)
    (comp / "records.index.jsonl").write_text(
        json.dumps(
            {
                "entity_type": "deployment",
                "entity_id": "ent-1",
                "path": f"r/{PUB}/c/sig_graph/entity/deployment/ent-1/index.html",
            }
        )
        + "\n"
    )
    return work


def _dist(tmp_path: Path, name: str, pages: dict[str, str]) -> Path:
    """A minimal Astro dist: one index.html per named route."""
    d = tmp_path / name
    for route, body in pages.items():
        out = d / route.strip("/")
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(body, encoding="utf-8")
    return d


# --------------------------------------------------------------------------- #
# page_index — the withdrawal index                                          #
# --------------------------------------------------------------------------- #


def test_page_index_maps_routes_to_embedded_ids(tmp_path: Path) -> None:
    sroot = tmp_path / "s" / PUB
    page = sroot / "dossier" / "okc"
    page.mkdir(parents=True)
    (page / "index.html").write_text(
        f'<tr data-claim-id="claim-9"></tr>'
        f'<td data-artifact-id="art-7"></td>'
        f'<a href="/r/{PUB}/c/sig_graph/entity/deployment/ent-1/">rec</a>'
    )
    doc = st.page_index_document(sroot, PUB)
    assert doc["schema"] == st.PAGE_INDEX_SCHEMA
    assert doc["publication_id"] == PUB
    (row,) = doc["pages"]
    assert row["route"] == f"s/{PUB}/dossier/okc/"
    assert row["claim_ids"] == ["claim-9"]
    assert row["artifact_ids"] == ["art-7"]
    assert row["entity_ids"] == ["ent-1"]


def test_page_index_empty_ids_omitted(tmp_path: Path) -> None:
    sroot = tmp_path / "s" / PUB
    (sroot / "about").mkdir(parents=True)
    (sroot / "about" / "index.html").write_text("<h1>about</h1>")
    doc = st.page_index_document(sroot, PUB)
    (row,) = doc["pages"]
    assert row == {"route": f"s/{PUB}/about/"}


def test_page_index_refuses_bad_pub(tmp_path: Path) -> None:
    with pytest.raises(rp.PipelineError):
        st.page_index_document(tmp_path, "not-a-pub")


# --------------------------------------------------------------------------- #
# containment                                                                 #
# --------------------------------------------------------------------------- #


def test_scan_containment_flags_escape_and_allows_exceptions() -> None:
    html = (
        '<a href="/dossier/okc/">escapes</a>'
        f'<a href="/s/{PUB}/dossier/okc/">inside</a>'
        '<a href="//evil.example/x">proto</a>'
        f'<a href="/r/{PUB}/c/sig_graph/entity/deployment/ent-1/">record</a>'
        '<a href="/releases/">catalog</a>'
        '<a href="/v1/coverage/national">live api</a>'
        '<a href="/intake/x">intake</a>'
    )
    violations = st.scan_containment(html, base=f"/s/{PUB}/")
    assert len(violations) == 2
    assert any(v.startswith("protocol-relative") for v in violations)
    assert any("escapes" in v for v in violations)


def test_embedded_ids_covers_data_attrs_and_record_links() -> None:
    ids = st.embedded_ids(
        f'<tr data-claim-id="c1"/><td data-entity-id="e1"/>'
        f'<a href="/r/{PUB}/c/sig_graph/entity/deployment/e2/x">rec</a>'
        f'<span data-artifact-id="a1"/>'
    )
    assert ids == {
        "entity_ids": ["e1", "e2"],
        "claim_ids": ["c1"],
        "artifact_ids": ["a1"],
    }


# --------------------------------------------------------------------------- #
# assemble_site_trees                                                         #
# --------------------------------------------------------------------------- #


def test_assemble_copies_trees_release_json_and_emits_index(tmp_path: Path) -> None:
    work = _work_dir(tmp_path)
    latest = _dist(tmp_path, "latest", {"": "<h1>latest</h1>", "about/": "<p>a</p>"})
    snap = _dist(
        tmp_path,
        "snap",
        {
            "": f'<a href="/s/{PUB}/about/">home</a>',
            "about/": f'<a href="/r/{PUB}/c/sig_graph/entity/deployment/ent-1/">r</a>',
        },
    )
    out = st.assemble_site_trees(work, PUB, latest_dist=latest, snapshot_dist=snap)
    assert (work / "v" / PUB / "index.html").is_file()
    assert (work / "v" / PUB / "release.json").is_file()
    assert (work / "s" / PUB / "index.html").is_file()
    assert (work / "s" / PUB / "release.json").is_file()
    assert (work / "v" / PUB / "entity" / "deployment" / "ent-1" / "index.html").is_file()
    assert (work / "v" / PUB / "compat_index.json").is_file()
    idx = json.loads((work / "s" / PUB / "page_index.json").read_text())
    assert idx["schema"] == st.PAGE_INDEX_SCHEMA
    routes = {p["route"] for p in idx["pages"]}
    assert f"s/{PUB}/about/" in routes
    assert out["trees"]["s"]["containment_violations"] == 0
    assert out["trees"]["v"]["entity_stubs"] == 1


def test_assemble_refuses_containment_escape(tmp_path: Path) -> None:
    work = _work_dir(tmp_path)
    snap = _dist(tmp_path, "snap", {"": '<a href="/dossier/okc/">escapes</a>'})
    with pytest.raises(rp.PipelineError, match="escap"):
        st.assemble_site_trees(work, PUB, snapshot_dist=snap)
    assert not (work / "s" / PUB).exists() or not any((work / "s" / PUB).iterdir())


def test_assemble_refuses_empty_dist_and_existing_tree(tmp_path: Path) -> None:
    work = _work_dir(tmp_path)
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(rp.PipelineError, match="vacuous"):
        st.assemble_site_trees(work, PUB, snapshot_dist=empty)
    snap = _dist(tmp_path, "snap", {"": f'<a href="/s/{PUB}/about/">x</a>'})
    st.assemble_site_trees(work, PUB, snapshot_dist=snap)
    with pytest.raises(rp.PipelineError, match="already populated"):
        st.assemble_site_trees(work, PUB, snapshot_dist=snap)


def test_assemble_refuses_missing_release_json(tmp_path: Path) -> None:
    work = tmp_path / "bare"
    work.mkdir()
    snap = _dist(tmp_path, "snap", {"": "<h1>x</h1>"})
    with pytest.raises(rp.PipelineError, match="no release.json"):
        st.assemble_site_trees(work, PUB, snapshot_dist=snap)


def test_verb_sites_dry_run_and_apply(tmp_path: Path) -> None:
    work = _work_dir(tmp_path)
    store = rp.LocalDirStore(tmp_path / "registry")
    snap = _dist(tmp_path, "snap", {"": f'<a href="/s/{PUB}/about/">x</a>'})
    latest = _dist(tmp_path, "latest", {"": "<h1>v</h1>"})
    dry = st.verb_sites(store, apply_=False, work_dir=work, latest_dist=latest, snapshot_dist=snap)
    assert dry["dry_run"] is True and not dry["applied"]
    out = st.verb_sites(
        store, apply_=True, work_dir=work, latest_dist=latest, snapshot_dist=snap, now=NOW
    )
    assert out["applied"] is True
    assert out["publication_id"] == PUB
    events = [e for e in rp.list_events(store, PUB) if e.get("verb") == "sites"]
    assert len(events) == 1


# --------------------------------------------------------------------------- #
# selectors.conf — the J3 §8.3 edge registry                                  #
# --------------------------------------------------------------------------- #


def _render(entries: list[dict], *, gen: int = 3, current: str = PUB) -> str:
    return rc.render_selectors_conf(entries, gen=gen, current_pub=current).decode()


def test_selectors_conf_exact_match_redirects_into_snapshot() -> None:
    conf = _render(
        [
            {
                "publication_id": PUB,
                "as_of_world": "2026-09-24",
                "as_of_belief": "2026-09-25",
                "ruleset_version": "ruleset-1",
            }
        ]
    )
    assert (
        f'if ($sig_sel_key = "2026-09-24|2026-09-25|ruleset-1") '
        f"{{ return 302 /s/{PUB}$uri; }}" in conf
    )
    # partial subsets resolve uniquely too
    assert f'if ($sig_sel_key = "2026-09-24||") {{ return 302 /s/{PUB}$uri; }}' in conf
    assert f'if ($sig_sel_key = "||ruleset-1") {{ return 302 /s/{PUB}$uri; }}' in conf


def test_selectors_conf_ambiguous_names_candidates_409() -> None:
    pub2 = "p-" + "b" * 64
    conf = _render(
        [
            {
                "publication_id": PUB,
                "as_of_world": "2026-09-24",
                "as_of_belief": "2026-09-25",
                "ruleset_version": "ruleset-1",
            },
            {
                "publication_id": pub2,
                "as_of_world": "2026-09-24",
                "as_of_belief": "2026-09-25",
                "ruleset_version": "ruleset-1",
            },
        ]
    )
    assert "return 409" in conf
    assert f"/releases/{PUB}/" in conf and f"/releases/{pub2}/" in conf


def test_selectors_conf_unmatched_404_and_malformed_400() -> None:
    conf = _render([])
    assert 'if ($sig_sel_w ~ "[^0-9-]") { return 400; }' in conf
    assert 'if ($sig_sel_any != "") { return 404' in conf
    assert "never substitutes a different cut" in conf
    assert f"/releases/{PUB}/" in conf


def test_selectors_conf_normalises_instants_to_date() -> None:
    conf = _render([])
    assert 'if ($sig_sel_w ~ "^([0-9]{4}-[0-9]{2}-[0-9]{2})[T ]") { set $sig_sel_w $1; }' in conf


def test_selector_patterns_cover_all_subsets() -> None:
    pats = dict(
        st_key
        for st_key in rc._selector_patterns(
            {
                "publication_id": PUB,
                "as_of_world": "w",
                "as_of_belief": "b",
                "ruleset_version": "r",
            }
        )
    )
    assert set(pats) == {
        "w|b|r",
        "w|b|",
        "w||r",
        "|b|r",
        "w||",
        "|b|",
        "||r",
    }


def test_render_selectors_refuses_unsafe_key() -> None:
    with pytest.raises(rp.PipelineError, match="conf-unsafe"):
        rc.render_selectors_conf(
            [
                {
                    "publication_id": PUB,
                    "as_of_world": 'x"; } evil { #',
                    "as_of_belief": "",
                    "ruleset_version": "",
                }
            ],
            gen=1,
        )


def test_compose_generation_emits_real_selectors_conf(tmp_path: Path) -> None:
    """promote composes selectors.conf from the promoted set's compat
    blocks — never the empty placeholder once a promoted release names
    an as-of pair."""
    store_root = tmp_path / "store"
    store = rp.LocalDirStore(store_root)
    (store_root / "staged" / "releases" / PUB).mkdir(parents=True)
    (store_root / "staged" / "releases" / PUB / "catalog_entry.json").write_bytes(
        json.dumps(
            {
                "publication_id": PUB,
                "data_release_id": "sig-2026-09-24.1",
                "manifest_sha256": "f" * 64,
                "descriptor_sha256": "e" * 64,
                "compat": {
                    "as_of_world": "2026-09-24",
                    "as_of_belief": "2026-09-25",
                    "ruleset_version": "ruleset-1",
                },
            }
        ).encode()
    )
    files = rc.compose_generation(
        store,
        gen=1,
        pub=PUB,
        label="sig-2026-09-24.1",
        release_class="class_r",
        approval_ref=None,
        meta={"manifest_sha256": "f" * 64},
        api_image=None,
        web_image=None,
        now=NOW,
    )
    conf = files["selectors.conf"].decode()
    assert f"return 302 /s/{PUB}$uri;" in conf
    assert "return 404" in conf
