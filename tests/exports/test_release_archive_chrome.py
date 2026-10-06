# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.34a (G2 step-4, ACT-16 first half) — release-archive correctness:

- the same-origin link-resolution crawl (``link_crawl_failures``) and its
  wiring into ``validate_release``/``activate`` (DR-C4-01 agent draft);
- the relative-link depth repair (site-root-absolute archive links resolve
  from every route depth);
- the archive chrome on every exports-rendered page (site navigation, the
  dispute/correction link, the licence of the data shown — C4 NEW-5/NEW-22,
  F-155; SIG-UI-033, SIG-UI-049, SIG-LIC-011);
- the §12.2 access-edge type on record claims and released pages
  (C4 NEW-6, F-156; SIG-UI-024);
- the released dossier's provisional posture + landing links (C4 NEW-7);
- the honest zero-record landing (C4 NEW-31);
- ``web/leverage.json`` emitted by ``build_spine_export`` (F5 PKG-03a).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import exports.release as release_mod
import pytest
from exports.manifest import canonical_json
from exports.published_record import record_from_site_row
from exports.release import (
    ReleaseError,
    activate,
    build_release,
    link_crawl_failures,
    validate_release,
)
from exports.release_pages import (
    DISPUTE_HREF,
    SITE_NAV,
    browse_page,
    compartment_page,
    dossier_page,
    dossier_slug,
    entity_stub,
    error_page,
    evidence_page,
    jurisdiction_page,
    record_page,
    release_landing,
    releases_index,
    search_page,
    tombstone_page,
)
from test_release import REVISION, _claim_row, _site_row, _write_export
from test_spine_export import _build as _build_spine
from test_spine_export import _claim, _site


def _fixture_release(tmp_path: Path, name: str = "rel", **kw):
    export = _write_export(tmp_path / f"export-{name}", **kw)
    return build_release(export, tmp_path / name, renderer_revision=REVISION)


def _html(build, rel: str) -> str:
    return (build.out_dir / rel).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Deliverable 2 — the link-resolution crawl                                   #
# --------------------------------------------------------------------------- #


def test_fixture_release_crawl_finds_zero_broken_links(tmp_path: Path) -> None:
    """AC: a crawl of every exports-rendered page finds 0 broken links."""
    build = _fixture_release(tmp_path)
    assert link_crawl_failures(build.out_dir) == []
    assert validate_release(build.out_dir).state == "complete"


def test_crawl_resolves_relative_root_relative_and_index_routes(tmp_path: Path) -> None:
    """Relative links resolve against the PAGE's directory; directory routes
    resolve to index.html; queries/fragments/external schemes never follow."""
    root = tmp_path / "corpus"
    page = root / "r" / "pub" / "c" / "comp" / "browse" / "kind" / "2"
    page.mkdir(parents=True)
    (page / "index.html").write_text(
        # three levels up — browse/kind/2/ → c/comp/ — then into jurisdiction;
        # the historical bug resolved one level too shallow (C4 NEW-1).
        '<a href="../../../jurisdiction/ok/1/">a</a>'
        '<a href="/r/pub/c/comp/descriptor.json">b</a>'
        '<a href="../../../jurisdiction/ok/1/?q=1#frag">c</a>'
        '<a href="#only-fragment">d</a>'
        '<a href="https://example.com/x">e</a>'
        '<a href="mailto:a@b">f</a>'
        '<a href="//cdn.example/x">g</a>',
        encoding="utf-8",
    )
    (root / "r" / "pub" / "c" / "comp" / "descriptor.json").write_bytes(b"{}")
    (root / "r" / "pub" / "c" / "comp" / "jurisdiction" / "ok" / "1").mkdir(parents=True)
    (root / "r" / "pub" / "c" / "comp" / "jurisdiction" / "ok" / "1" / "index.html").write_text(
        "<p>ok</p>", encoding="utf-8"
    )
    assert link_crawl_failures(root) == []


def test_crawl_flags_a_broken_link_naming_page_and_target(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    page = root / "r" / "pub" / "x"
    page.mkdir(parents=True)
    (page / "index.html").write_text('<a href="/r/pub/c/sig/nope/">x</a>', encoding="utf-8")
    failures = link_crawl_failures(root)
    assert len(failures) == 1
    assert "r/pub/x/index.html" in failures[0]
    assert "/r/pub/c/sig/nope" in failures[0]


def test_crawl_treats_explicitly_denied_routes_as_410(tmp_path: Path) -> None:
    """The withdrawal barrier's 410 tombstone is a recorded answer — a link to
    a denied route resolves as 410, never a missing-file failure."""
    root = tmp_path / "corpus"
    (root / "p").mkdir(parents=True)
    (root / "p" / "index.html").write_text('<a href="/denied/route/">x</a>', encoding="utf-8")
    assert link_crawl_failures(root) != []
    assert link_crawl_failures(root, denied_routes=["denied/route"]) == []
    assert link_crawl_failures(root, denied_routes=["denied/route/index.html"]) == []


def test_validate_release_fails_on_a_planted_broken_link(tmp_path: Path) -> None:
    """AC: a planted broken link makes ``validate_release`` fail with page and
    target named — the integrity manifest is repaired first so ONLY the crawl
    can flag it."""
    build = _fixture_release(tmp_path)
    pub = build.publication_id
    page_rel = f"r/{pub}/c/sig_graph/index.html"
    page = build.out_dir / page_rel
    page.write_text(
        page.read_text().replace(
            "</body>", f'<a href="/r/{pub}/c/sig_graph/ghost/">ghost</a></body>'
        )
    )
    im_path = build.out_dir / f"releases/{pub}/integrity_manifest.json"
    integrity = json.loads(im_path.read_text())
    for a in integrity["artifacts"]:
        if a["path"] == page_rel:
            data = page.read_bytes()
            a["sha256"] = hashlib.sha256(data).hexdigest()
            a["byte_size"] = len(data)
    im_path.write_bytes(canonical_json(integrity))
    report = validate_release(build.out_dir)
    assert report.state == "incomplete"
    link_failures = [f for f in report.failures if "unresolved same-origin link" in f]
    assert link_failures, f"crawl failure absent from {report.failures}"
    assert page_rel in link_failures[0]
    assert f"/r/{pub}/c/sig_graph/ghost" in link_failures[0]


def test_activate_refuses_when_the_staged_tree_carries_a_broken_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The activation-time crawl runs over the composed staged tree (after the
    withdrawal barrier) — a broken link there refuses activation before the
    catalog or the latest pointer moves."""
    build = _fixture_release(tmp_path)
    real = release_mod.apply_withdrawals

    def plant(staged: Path, withdrawals):  # noqa: ANN001, ANN202
        out = real(staged, withdrawals)
        bad = staged / "planted" / "index.html"
        bad.parent.mkdir(parents=True)
        bad.write_text('<a href="/ghost/route/">x</a>', encoding="utf-8")
        return out

    monkeypatch.setattr(release_mod, "apply_withdrawals", plant)
    with pytest.raises(ReleaseError, match="unresolved same-origin"):
        activate(tmp_path / "registry", build.out_dir)
    assert not (tmp_path / "registry" / "latest.json").exists()


# --------------------------------------------------------------------------- #
# Deliverable 3 — archive chrome on every page type                           #
# --------------------------------------------------------------------------- #


def _released_record() -> object:
    claim_index = {
        "claim-src_a-0-a": {
            "predicate_id": "camera_latitude",
            "observed_at": "2026-05-01",
            "source_id": "src_a",
            "evidence": [{"capture_id": "cap-1", "artifact_id": "art-1", "role": "establishes"}],
        }
    }
    rec = record_from_site_row(
        _site_row(0, "src_a", "CC-BY-4.0"),
        compartment="sig_graph",
        license_id="CC-BY-4.0",
        claim_index=claim_index,
    )
    return rec.bind("pub-1")


_DOSSIER = {
    "jurisdiction": "Oklahoma",
    "slug": "oklahoma",
    "asOf": {"as_of_world": "2026-09-27", "as_of_belief": "2026-09-27"},
    "rulesetVersion": "p27.3/1.0.0",
    "sections": [{"section_id": "at_a_glance"}],
    "gaps": [],
}

_LANDING_ENTRY = {
    "publication_id": "pub-1",
    "data_release_id": "dr-1",
    "record_count": 2,
    "compartments": [{"compartment": "sig_graph", "license": "CC-BY-4.0", "record_count": 2}],
    "reproducibility": {"as_of_world": "2026-09-27"},
}

# name → (rendered bytes, the licence the page must disclose or None when the
# page honestly shows no data).
_CHROME_PAGES = {
    "record": (record_page(_released_record(), latest_stub="/entity/deployment/e0/"), "CC-BY-4.0"),
    "browse": (
        browse_page(
            publication_id="pub-1",
            compartment="sig_graph",
            kind="deployment",
            page=1,
            page_count=1,
            items=[
                {"entity_id": "e0", "entity_type": "deployment", "jurisdiction": "OK", "label": "S"}
            ],
            total=1,
            licence="CC-BY-4.0",
        ),
        "CC-BY-4.0",
    ),
    "jurisdiction": (
        jurisdiction_page(
            publication_id="pub-1",
            compartment="sig_graph",
            jurisdiction="OK",
            page=1,
            page_count=1,
            items=[
                {"entity_id": "e0", "entity_type": "deployment", "jurisdiction": "OK", "label": "S"}
            ],
            total=1,
            licence="CC-BY-4.0",
        ),
        "CC-BY-4.0",
    ),
    "compartment": (
        compartment_page(
            publication_id="pub-1",
            compartment="sig_graph",
            licence="CC-BY-4.0",
            record_count=1,
            kinds={"deployment": 1},
            jurisdictions={"OK": 1},
        ),
        "CC-BY-4.0",
    ),
    "evidence": (
        evidence_page(
            publication_id="pub-1",
            compartment="sig_graph",
            artifact={"artifact_id": "art-1", "source": "src_a"},
            licence="CC-BY-4.0",
        ),
        "CC-BY-4.0",
    ),
    "dossier": (
        dossier_page(publication_id="pub-1", dossier=_DOSSIER, licence="CC-BY-4.0"),
        "CC-BY-4.0",
    ),
    "landing": (release_landing(_LANDING_ENTRY), "per compartment"),
    "index": (releases_index([], latest=None), "CC-BY-4.0"),
    "stub": (
        entity_stub(
            entity_type="deployment",
            entity_id="e0",
            latest_publication="pub-1",
            record_href="/r/pub-1/c/sig_graph/entity/deployment/e0/",
        ),
        "pointer",
    ),
    "search": (
        search_page(
            action="/r/pub-1/c/sig_graph/search",
            publication_id="pub-1",
            compartment="sig_graph",
            licence="CC-BY-4.0",
            params={},
            facet_options={},
            result={"results": [], "scope": {}, "query": {}},
        ),
        "CC-BY-4.0",
    ),
    # Pages that show no compartment data carry no licence line — an honest
    # absence, never a fabricated basis.
    "tombstone": (
        tombstone_page(
            path="/r/pub-1/c/sig_graph/entity/deployment/e0/",
            reason_category="safety_withdrawal",
            authority="test-authority",
            decided="2026-09-27",
            policy_version="policy/1",
        ),
        None,
    ),
    "error": (error_page(title="Not found", detail="no route"), None),
}


@pytest.mark.parametrize("name", sorted(_CHROME_PAGES))
def test_every_page_type_carries_archive_chrome(name: str) -> None:
    """C4 NEW-5/NEW-22 (SIG-UI-033, SIG-UI-049, SIG-LIC-011): every page the
    export renders carries the site navigation and the dispute/correction
    link; a page that shows data also names its licence."""
    page, licence = _CHROME_PAGES[name]
    html = page.decode("utf-8")
    assert '<nav class="site-nav"' in html
    for _label, href in SITE_NAV:
        assert f'href="{href}"' in html
    assert DISPUTE_HREF in html
    assert "Dispute or correct this record" in html
    if licence is not None:
        assert "Licence of the data on this page:" in html
        assert licence in html
    else:
        assert "Licence of the data on this page:" not in html
    assert "<script" not in html


def test_built_release_pages_all_carry_chrome(tmp_path: Path) -> None:
    """The end-to-end sweep: every HTML artifact of a real build carries the
    nav, the dispute link, and a licence or the honest no-licence state."""
    build = _fixture_release(tmp_path)
    pages = list(build.out_dir.rglob("*.html"))
    assert pages, "fixture release emitted no pages"
    for p in pages:
        html = p.read_text(encoding="utf-8")
        rel = p.relative_to(build.out_dir).as_posix()
        assert '<nav class="site-nav"' in html, rel
        assert DISPUTE_HREF in html, rel
        assert "Licence of the data on this page:" in html, rel


# --------------------------------------------------------------------------- #
# Deliverable 1 — the link-depth repair (site-root-absolute archive links)     #
# --------------------------------------------------------------------------- #


def test_record_page_evidence_links_are_root_absolute(tmp_path: Path) -> None:
    """C4 NEW-1 / F-151: an evidence link emitted from the entity route must
    resolve — the old ../../ form resolved one level too shallow."""
    build = _fixture_release(tmp_path)
    pub = build.publication_id
    page = _html(build, f"r/{pub}/c/sig_graph/entity/deployment/ent-src_a-0/index.html")
    assert f'href="/r/{pub}/c/sig_graph/evidence/art-sig_graph/"' in page
    assert "../../evidence/" not in page


def test_cross_compartment_evidence_links_resolve(tmp_path: Path) -> None:
    """P34.34a fix-forward — the seeded-PG release in CI (the leg a
    Docker-less local run skips) caught a REAL dead link: a record in
    ``osm_physical`` citing an artifact published under ``sig_graph`` linked
    the record's own compartment. The link must name the artifact's
    compartment; an artifact absent from the release renders the honest
    "not published" cell, never a dead link."""
    export = _write_export(tmp_path / "export")
    claims_path = export / "osm_physical" / "record_claims.jsonl"
    rows = [json.loads(line) for line in claims_path.read_text().splitlines() if line.strip()]
    for row in rows:
        if row["claim_id"] == "claim-src_osm-0-a":
            row["evidence"][0]["artifact_id"] = "art-sig_graph"  # other compartment
        if row["claim_id"] == "claim-src_osm-1-a":
            row["evidence"][0]["artifact_id"] = "art-not-published"  # absent entirely
    claims_path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    build = build_release(export, tmp_path / "rel", renderer_revision=REVISION)
    pub = build.publication_id
    page = _html(build, f"r/{pub}/c/osm_physical/entity/deployment/ent-src_osm-0/index.html")
    assert f'href="/r/{pub}/c/sig_graph/evidence/art-sig_graph/"' in page
    assert "/c/osm_physical/evidence/art-sig_graph/" not in page
    page1 = _html(build, f"r/{pub}/c/osm_physical/entity/deployment/ent-src_osm-1/index.html")
    assert "artifact not published in this release" in page1
    assert "art-not-published" not in page1  # no dead href, no bare id
    assert link_crawl_failures(build.out_dir) == []
    assert validate_release(build.out_dir).state == "complete"


def test_browse_and_jurisdiction_rows_link_root_absolute(tmp_path: Path) -> None:
    build = _fixture_release(tmp_path)
    pub = build.publication_id
    for rel in (
        f"r/{pub}/c/sig_graph/browse/deployment/1/index.html",
        f"r/{pub}/c/sig_graph/jurisdiction/OK/1/index.html",
    ):
        page = _html(build, rel)
        assert f'href="/r/{pub}/c/sig_graph/entity/deployment/ent-src_a-0/"' in page, rel
        assert "../../entity/" not in page, rel


# --------------------------------------------------------------------------- #
# Deliverable 4 — the §12.2 access-edge type                                  #
# --------------------------------------------------------------------------- #


def test_record_claims_carry_the_access_kind(tmp_path: Path) -> None:
    """SIG-UI-024 / C4 NEW-6: an access-vocabulary claim lands in
    record_claims.jsonl with its §12.2 kind; a materialized edge's recorded
    kind wins for its evidence_claim; an unclassifiable access predicate is
    honestly ``unclassified``; an ordinary claim carries no key at all."""
    claims = _site("A", "35.46", "-97.51", "Oklahoma") + [
        _claim("A-sh-cfg", "A", "configured_sharing_partner", value_text="Partner X"),
        _claim("A-sh-obs", "A", "observed_use_edge", value_text="feed"),
        _claim("A-sh-uni", "A", "mystery_access_protocol", value_text="?"),
    ]
    export = _build_spine(
        claims,
        raw_over={
            # The reconciler's recorded kind wins — never re-derived.
            "materialized_edges": [
                {
                    "from_entity": "A",
                    "to_entity": "P",
                    "access_kind": "declared_policy",
                    "edge_type": "shares_with",
                    "evidence_claim": "A-src_a-lat",
                }
            ]
        },
    )
    rows = {}
    for path, data in export.web_artifacts.items():
        if path.endswith("record_claims.jsonl"):
            for line in data.decode().splitlines():
                if line.strip():
                    row = json.loads(line)
                    rows[row["claim_id"]] = row
    assert rows["A-sh-cfg"]["access_kind"] == "configured_access"
    assert rows["A-sh-obs"]["access_kind"] == "observed_use"
    assert rows["A-sh-uni"]["access_kind"] == "unclassified"
    # the materialized edge's recorded kind wins over the claim's predicate
    assert rows["A-src_a-lat"]["access_kind"] == "declared_policy"
    # an ordinary claim carries no key (byte-identical for non-edge rows)
    assert "access_kind" not in rows["A-src_a-jur"]


def test_published_record_json_and_page_render_the_access_kind() -> None:
    """The released record carries the type additively (JSON) and renders the
    distinct kinds on the archive page (never an untyped sharing_access)."""
    claim_index = {
        "claim-src_a-0-a": {
            "predicate_id": "configured_sharing_partner",
            "observed_at": "2026-05-01",
            "source_id": "src_a",
            "access_kind": "configured_access",
        },
        "claim-src_a-0-b": {
            "predicate_id": "observed_use_edge",
            "observed_at": "2026-05-01",
            "source_id": "src_a",
            "access_kind": "observed_use",
        },
    }
    rec = record_from_site_row(
        _site_row(0, "src_a", "CC-BY-4.0"),
        compartment="sig_graph",
        license_id="CC-BY-4.0",
        claim_index=claim_index,
    ).bind("pub-1")
    anchors = {a.claim_id: a for a in rec.claim_anchors}
    assert anchors["claim-src_a-0-a"].access_kind == "configured_access"
    assert anchors["claim-src_a-0-b"].access_kind == "observed_use"
    doc = json.loads(rec.json_bytes())
    kinds = {a["claim_id"]: a["access_kind"] for a in doc["claim_anchors"]}
    assert kinds == {
        "claim-src_a-0-a": "configured_access",
        "claim-src_a-0-b": "observed_use",
    }
    html = record_page(rec, latest_stub="/entity/deployment/ent-src_a-0/").decode()
    assert "Access edge" in html
    assert "configured_access" in html and "observed_use" in html
    assert "sharing_access" not in html


def test_claim_anchor_omits_the_key_when_not_access_typed() -> None:
    """Back-compat: an ordinary claim anchor emits no ``access_kind`` key —
    the released document stays byte-identical for non-edge records."""
    rec = record_from_site_row(
        _site_row(0, "src_a", "CC-BY-4.0"),
        compartment="sig_graph",
        license_id="CC-BY-4.0",
        claim_index={
            "claim-src_a-0-a": _claim_row("claim-src_a-0-a", "ent-src_a-0", "src_a", None)
        },
    )
    for anchor in rec.as_json()["claim_anchors"]:
        assert "access_kind" not in anchor


# --------------------------------------------------------------------------- #
# Deliverable 5 — released dossiers: provisional posture + landing links       #
# --------------------------------------------------------------------------- #


def test_dossier_page_states_the_provisional_posture() -> None:
    """C4 NEW-7 / F-157: a released dossier is a computed inventory overview —
    'no human check performed' (ADR-152), never 'reviewed'."""
    html = dossier_page(publication_id="pub-1", dossier=_DOSSIER, licence="CC-BY-4.0").decode()
    assert "provisional" in html.lower()
    assert "no human check performed" in html
    assert "reviewed" not in html.lower()


def test_release_landing_links_every_emitted_dossier(tmp_path: Path) -> None:
    build = _fixture_release(tmp_path)
    pub = build.publication_id
    # the fixture dossier has jurisdiction OK and no slug field
    candidates = list(build.out_dir.glob(f"r/{pub}/dossier/*/index.html"))
    assert candidates, "no released dossier emitted"
    landing = _html(build, f"releases/{pub}/index.html")
    for d in candidates:
        slug = d.parent.name
        assert f'href="/r/{pub}/dossier/{slug}/"' in landing
    # the dossier page itself carries posture + licence chrome
    for d in candidates:
        html = d.read_text()
        assert "provisional" in html.lower()
        assert "reviewed" not in html.lower()
        assert "Licence of the data on this page:" in html


def test_dossier_slug_helper_matches_the_emitter() -> None:
    assert dossier_slug({"jurisdiction": "Oklahoma"}) == "Oklahoma"
    assert dossier_slug({"slug": "oklahoma", "jurisdiction": "OK"}) == "oklahoma"
    assert dossier_slug({}) == "unknown"


# --------------------------------------------------------------------------- #
# Deliverable 6 — the honest zero-record landing                              #
# --------------------------------------------------------------------------- #


def test_zero_record_release_landing_explains_itself(tmp_path: Path) -> None:
    """C4 NEW-31: a verified, complete release with zero records says so —
    an honest bounded result, never a silent empty page."""
    build = _fixture_release(tmp_path, name="empty", n_records=0)
    landing = _html(build, f"releases/{build.publication_id}/index.html")
    assert "no records" in landing.lower()
    assert "not a rendering fault" in landing
    assert validate_release(build.out_dir).state == "complete"
    assert link_crawl_failures(build.out_dir) == []


def test_zero_record_compartment_page_states_the_empty_index(tmp_path: Path) -> None:
    build = _fixture_release(tmp_path, name="empty2", n_records=0, two_compartments=False)
    comp = build.out_dir / f"r/{build.publication_id}/c/sig_graph/index.html"
    if comp.exists():
        html = comp.read_text()
        assert "no records" in html.lower()


# --------------------------------------------------------------------------- #
# Deliverable 7 — web/leverage.json from build_spine_export                   #
# --------------------------------------------------------------------------- #


def test_spine_export_emits_the_leverage_metric() -> None:
    """F5 PKG-03a: web/leverage.json is a first-class web artifact of every
    spine export — the zeroed ledger is the honest 'measured nothing yet',
    licence-labelled and manifest-listed."""
    export = _build_spine(_site("A", "35.46", "-97.51", "Oklahoma"))
    data = export.web_artifacts["web/leverage.json"].decode("utf-8")
    rec = json.loads(data)
    assert rec["hashtag"].startswith("#sig_")
    assert rec["accepted_operator_attributions"] == 0
    assert rec["attributed_changeset_ids"] == []
    # Part VIII §0.7: no OSM user data anywhere in the record
    assert not re.search(r'"(user|uid)"|mapper', data)
    art = next(a for a in export.manifest.artifacts if a.path == "web/leverage.json")
    assert art.license == "CC-BY-4.0"
    assert art.sha256 and art.sha256 != "x"


def test_spine_export_leverage_folds_a_recorded_feed() -> None:
    """A recorded changeset feed bound to the export (raw['osm_changeset_feeds']
    — replay bytes, HG-08; nothing fetched live) is folded into the metric."""
    xml = (
        Path(__file__).parent.parent / "tasks" / "fixtures" / "osm_changesets_okc_page1.xml"
    ).read_bytes()
    export = _build_spine(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={"osm_changeset_feeds": [xml]},
    )
    rec = json.loads(export.web_artifacts["web/leverage.json"])
    assert rec["accepted_operator_attributions"] >= 1
    assert "140000001" in rec["attributed_changeset_ids"]
