# SPDX-License-Identifier: Apache-2.0
"""P35.56 (REL-04a, SIG-REL-007 ``Also:``) — verification suite A, fixture-verified.

Covers the ticket's deliverable 11 verbatim:

* an honest fixture release (a real ``build_release`` v2 tree + synthesised
  ``v/``/``s/`` site trees with the §6.1 stamp) passes the suite in both
  modes over the §4.2 tree origin — the JSON result rows are written and
  shaped ``{check, mode, status, detail, evidence, duration}``;
* **each V-check fails a seeded defect** — the catalog AC: a tampered
  artifact (V1), an unpushed identity (V2), an unlisted route / a denied
  route answering (V3), a missing stamp (V4), a containment escape and a
  dead link (V5), a script on a content page / an oversized page / an axe
  violation (V11), a secret-shaped string (V12), a disclosure whose
  confirmed text never renders (V13);
* the **skip-blocks** rule — a check whose legs cannot run (no axe runner,
  no origin) records ``skip`` and the suite verdict is ``blocked``;
* the **waiver contract** — only ``class_s`` may carry one, V12 is never
  waivable, the record lands in the result + the applied event detail;
* ``verb_verify`` keeps its bounded staged==built scope under no ``--mode``,
  and ``--apply`` journals ``verified`` only on a green suite.

Everything runs on the tree origin — a fixture answer recorded as
``origin_kind: "tree"``, never claimed as a staging or public run.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from exports.release import build_release

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ops" / "src"))

from ops import publish as _publish  # noqa: E402
from ops import release_pipeline as rp  # noqa: E402
from ops import release_verify as rv  # noqa: E402

T0 = datetime(2026, 10, 16, 12, 0, 0, tzinfo=UTC)
AS_OF_WORLD = "2026-10-16T00:00:00Z"
COMMIT = "0a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d"
LABEL = "sig-2026-10-16.1"

DISCLOSURE_ID = "live-api-line"
DISCLOSURE_TEXT = "The public API serves newer, unreleased records continuously."


# --------------------------------------------------------------------------- #
# The fixture — a real v2 release build + synthesised site trees              #
# --------------------------------------------------------------------------- #


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


def _write_export(root: Path, *, as_of: str = AS_OF_WORLD) -> Path:
    comp = "sig_graph"
    (root / comp).mkdir(parents=True)
    (root / "web").mkdir(parents=True)
    (root / comp / "sites.jsonl").write_text(
        "".join(json.dumps(_site_row(i)) + "\n" for i in (1, 2)), encoding="utf-8"
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
    manifest = {
        "artifacts": [
            {
                "path": f"{comp}/sites.jsonl",
                "compartment": comp,
                "license": "CC-BY-4.0",
                "sha256": "0" * 64,
                "byte_size": 1,
                "media_type": "application/json",
            }
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
            "as_of_world": as_of,
            "as_of_belief": as_of,
            "belief_pinned": False,
            "spine_watermark": "claims=42 closed=0 bump=42",
            "materialize_run": None,
            "sqitch_head": "p35.56-test-head",
            "restore_point": None,
        },
        "environment": "fixture",
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def _stamp_fields(site_release: dict[str, Any]) -> dict[str, str]:
    """The field set the §6.1 stamp renders — label/pub/commit8/as-of
    verbatim (the same values ``release_pages.release_stamp_view``
    projects)."""
    pub = str(site_release["publication_id"])
    return {
        "label": str(site_release["label"]),
        "pub": pub,
        "pub_short": f"{pub[:10]}…",
        "commit8": str(site_release["code"]["commit"])[:8],
        "as_of": "2026-10-16 00:00 UTC",
        "built": "2026-10-16 12:00 UTC",
    }


def _site_page(fields: dict[str, str], describedby: str, *, basis: str) -> str:
    """A minimal stamped page — the §6.1 contract's markup verbatim:
    one ``sig-release`` meta, one ``describedby`` link, one stamp block,
    the mut-basis line carrying the "API is live" sentence, and one J3
    §5.4 figure element (``data-artifact``/``data-pointer``/
    ``data-figure-value``) whose pointer must recompute — the V6 leg."""
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        "<title>fixture — SIG released record</title>"
        f'<meta name="sig-release" content="{fields["label"]} {fields["pub"]}">'
        f'<link rel="describedby" type="application/json" href="{describedby}">'
        "</head><body><main><h1>fixture</h1><p>fixture page</p>"
        '<figure data-figure-id="sites-total" data-artifact="web/coverage.json" '
        'data-pointer="/totals/sites" data-figure-value="2">2 sites</figure>'
        "</main><footer>"
        '<p class="stamp">Release '
        f"{fields['label']} · data as of {fields['as_of']} · "
        f"built {fields['built']} from code "
        f"<code>{fields['commit8']}</code> · "
        f"<code>{fields['pub_short']}</code> · "
        f'<a href="{describedby}"><code>release.json</code></a></p>'
        f'<p class="stamp mut">{basis}</p>'
        "</footer></body></html>"
    )


_LIVE_BASIS = 'The public API also serves newer, unreleased records, labelled "live".'
_LATEST_BASIS = (
    "This is the latest view. Cite the fixed copy. "
    'The public API also serves newer, unreleased records, labelled "live".'
)


def _write_site_tree(
    work_dir: Path,
    pub: str,
    site_release: dict[str, Any],
) -> None:
    """The ``v/<pub>/`` + ``s/<pub>/`` site trees the pipeline's Astro legs
    emit: every allow-list ``required`` entry, the stamp on every page, the
    ``release.json`` copy, ``page-types.json``, the ``/entity/`` convenience
    stubs + ``compat_index.json`` in the latest view (the §4.2 serving map
    lands them under ``v/<latest>``), and the ``s/<pub>/`` tree
    self-contained under its prefix (§5.3)."""
    from exports.release_pages import entity_stub, release_stamp_view

    fields = _stamp_fields(site_release)
    allowed = _publish.load_allowlist()
    site_rel = (work_dir / f"releases/{pub}/release.json").read_bytes()
    page_types = json.dumps(
        {
            "schema": "sig.page-types-manifest/1",
            "routes": [
                {"path": "/", "type": "T1"},
                {"path": "/map/", "type": "T2"},
                {"path": "/network/", "type": "T2"},
                {"path": "/search/", "type": "T2"},
            ],
        }
    )
    for ns in ("v", "s"):
        root = work_dir / ns / pub
        describedby = "/release.json" if ns == "v" else f"/s/{pub}/release.json"
        basis = (
            _LATEST_BASIS
            if ns == "v"
            else (
                f"This is the fixed copy of this page in release {LABEL}; "
                "the latest view is here. "
                'The public API also serves newer, unreleased records, labelled "live".'
            )
        )
        root.mkdir(parents=True, exist_ok=True)
        for entry in allowed.required:
            if entry in ("index.html", "page-types.json"):
                continue  # written below
            if entry.endswith(".html"):
                # the chrome error pages are stamped pages too — V4's
                # "every HTML page" criterion is verbatim
                (root / entry).write_text(
                    _site_page(fields, describedby, basis=basis), encoding="utf-8"
                )
            elif "." in entry or entry in ("403", "410"):
                (root / entry).write_text(f"fixture {entry}\n", encoding="utf-8")
            elif entry == "_astro":
                # an assets dir, never a page — a real build holds hashed
                # css/js and no index.html (the composed nginx would 404
                # ``/_astro/``); assets are written below
                continue
            else:
                (root / entry).mkdir(parents=True, exist_ok=True)
                (root / entry / "index.html").write_text(
                    _site_page(fields, describedby, basis=basis), encoding="utf-8"
                )
        (root / "_astro").mkdir(exist_ok=True)
        (root / "_astro" / "app.css").write_text("body{}\n", encoding="utf-8")
        (root / "page-types.json").write_text(page_types, encoding="utf-8")
        (root / "release.json").write_bytes(site_rel)
        (root / "index.html").write_text(
            _site_page(fields, describedby, basis=basis), encoding="utf-8"
        )
        # Suite-B surfaces (P35.58): the J3 artifacts V6's figure contract
        # recomputes (``coverage.json`` is the page figure's
        # ``data-artifact``; ``unplaced.json`` is the geometry-less
        # records' dossier rollup V9 recomputes) and the sources index
        # V8's attribution legs read.
        for stem, body in {
            "web/coverage.json": {
                "as_of_world": AS_OF_WORLD,
                "totals": {"sites": 2},
            },
            "web/sources.json": {
                "schema": "sig.sources-index/1",
                "as_of_world": AS_OF_WORLD,
                "sources": [
                    {
                        "source_id": "src_a",
                        "name": "Ohio DOT",
                        "license": {"spdx": "CC-BY-4.0"},
                        "map_contributor": True,
                        "records": 2,
                        "attribution": {"instances": 4},
                    }
                ],
            },
            "web/dossiers/unplaced.json": {
                "schema": "sig.dossier-rollup/1",
                "slug_path": "unplaced",
                "jurisdiction_key": None,
                "rollup": {"records": 2, "records_placed_only_here": 2},
                "page_refs": ["dossier/unplaced/"],
            },
            # V8's compartment licence index — the published copy under
            # artifact/ (the bucket-root /LICENCES.json route is the same
            # bytes through the publish layer)
            "LICENCES.json": {
                "schema": "sig.licences-index/1",
                "compartments": [
                    {
                        "compartment": "sig_graph",
                        "license": "CC-BY-4.0",
                        "attribution": "Ohio DOT",
                    }
                ],
            },
        }.items():
            f = root / "artifact" / stem
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(body), encoding="utf-8")
        # the map page's attribution element names every map_contributor
        # source (V8's upstream-holder leg)
        map_page = root / "map" / "index.html"
        if map_page.is_file():
            map_page.write_text(
                map_page.read_text(encoding="utf-8").replace(
                    "</main>",
                    '<p class="map-attribution">Map data © Ohio DOT and contributors</p></main>',
                ),
                encoding="utf-8",
            )
    # the latest-view overlays: entity convenience stubs + the compat index
    # (G3 §4.2: ``/entity/`` and ``/compat_index.json`` resolve inside
    # ``v/<latest>``)
    vroot = work_dir / "v" / pub
    stamp = release_stamp_view(site_release, describedby="/release.json", variant="latest")
    for i in (1, 2):
        (vroot / "entity" / "camera" / f"ent-{i}").mkdir(parents=True, exist_ok=True)
        (vroot / "entity" / "camera" / f"ent-{i}" / "index.html").write_bytes(
            entity_stub(
                entity_type="camera",
                entity_id=f"ent-{i}",
                latest_publication=pub,
                record_href=f"/r/{pub}/c/sig_graph/entity/camera/ent-{i}/index.html",
                stamp=stamp,
            )
        )
    (vroot / "compat_index.json").write_text(
        json.dumps({"schema": "sig.compat-index/1", "entries": []}), encoding="utf-8"
    )


#: The previously-promoted release the fixture registry records — the
#: "second promotion" posture (a real staging origin always serves the
#: current conf generation; a first-ever release would 404 ``/releases/``,
#: which V5 would honestly flag).
_OLD_PUB = "p-" + "a" * 64
_OLD_LABEL = "sig-2026-09-30.1"
_OLD_AS_OF = "2026-09-30T00:00:00Z"


def _write_registry(
    root: Path, pub: str, old_pub: str = _OLD_PUB, *, promoted: bool
) -> rp.LocalDirStore:
    """The release-root registry: labels + catalog + a conf gen. ``promoted``
    poses the post-promotion posture (gen 2 names the candidate latest and
    carries it in promoted.map); the default poses pre-promotion staging
    (gen 1 names the previous release — the candidate's ``as_of_world``
    monotonicity has a real predecessor to compare against)."""
    store = rp.LocalDirStore(root)
    reg = root / "registry"
    reg.mkdir(parents=True, exist_ok=True)
    (reg / "labels.json").write_text(
        json.dumps(
            {
                "schema": "sig.release-labels/1",
                "labels": [
                    {"label": _OLD_LABEL, "publication_id": old_pub},
                    {"label": LABEL, "publication_id": pub},
                ],
            }
        ),
        encoding="utf-8",
    )
    (reg / "catalog.json").write_text(
        json.dumps(
            {
                "schema": "sig.publication-catalog/2",
                "publications": [
                    {
                        "publication_id": old_pub,
                        "label": _OLD_LABEL,
                        "as_of_world": _OLD_AS_OF,
                        "state": "promoted",
                    },
                    {
                        "publication_id": pub,
                        "label": LABEL,
                        "as_of_world": AS_OF_WORLD,
                        "state": "promoted" if promoted else "staged",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    gen_n = 2 if promoted else 1
    latest_pub, latest_label = (pub, LABEL) if promoted else (old_pub, _OLD_LABEL)
    latest_doc = {
        "schema": "sig.latest-pointer/2",
        "publication_id": latest_pub,
        "label": latest_label,
        "conf_gen": gen_n,
        # P1's freshness leg — the activation stamp a real generation writes
        "activated_at": T0.isoformat(),
    }
    (reg / "latest.json").write_text(json.dumps(latest_doc), encoding="utf-8")
    gen = reg / "conf" / str(gen_n)
    (gen / "releases").mkdir(parents=True)
    promoted_set = {old_pub, pub} if promoted else {old_pub}
    (gen / "promoted.map").write_text(
        "".join(f"{p} 1;\n" for p in sorted(promoted_set)), encoding="utf-8"
    )
    (gen / "latest.json").write_text(json.dumps(latest_doc), encoding="utf-8")
    (gen / "withdrawn.conf").write_text("# empty barrier\n", encoding="utf-8")
    (gen / "selectors.conf").write_text("# empty selector routes\n", encoding="utf-8")
    label_aliases = f"location = /releases/{_OLD_LABEL} {{ return 301 /releases/{old_pub}/; }}\n"
    if promoted:
        label_aliases += f"location = /releases/{LABEL} {{ return 301 /releases/{pub}/; }}\n"
    (gen / "labels.conf").write_text(label_aliases, encoding="utf-8")
    (gen / "releases" / "index.html").write_text(
        '<!doctype html><html lang="en"><head><title>Releases</title></head>'
        "<body><main><h1>Releases</h1><p>releases index fixture</p></main></body></html>",
        encoding="utf-8",
    )
    (gen / "releases" / "catalog.json").write_text(
        (reg / "catalog.json").read_text(), encoding="utf-8"
    )
    (gen / "releases" / "latest.json").write_text(json.dumps(latest_doc), encoding="utf-8")
    # the activation-overlay objects the nginx `/releases/` prefix maps to
    # the staged root — the DCAT series catalog every v2 landing links
    staged_rel = root / "staged" / "releases"
    staged_rel.mkdir(parents=True, exist_ok=True)
    (staged_rel / "catalog.jsonld").write_text(
        json.dumps({"@context": "https://www.w3.org/ns/dcat3.jsonld", "dataset": []}),
        encoding="utf-8",
    )
    return store


def _build_candidate(
    tmp_path: Path,
    *,
    promoted: bool = False,
    disclosures: list[dict[str, Any]] | None = None,
) -> tuple[Path, str, rp.LocalDirStore]:
    """``(work_dir, pub, store)`` — a real built v2 tree + site trees +
    staged objects + registry, ready for a verify. The registry's prior
    latest is a REAL staged release (V14's diff baseline re-reads its
    catalog_entry/descriptor/record JSONs from ``staged/``)."""
    export = _write_export(tmp_path / "export")
    work_dir = tmp_path / "rel"
    build = build_release(
        export,
        work_dir,
        descriptor_version=2,
        label=LABEL,
        environment="production",
        code_commit=COMMIT,
        code_tree="clean",
        built_at=T0,
        ontology_generated_sha256="b" * 64,
        evaluation={"status": "deferred"},
        disclosures=disclosures,
    )
    pub = build.publication_id
    site_release = json.loads((work_dir / f"releases/{pub}/release.json").read_bytes())
    _write_site_tree(work_dir, pub, site_release)
    # the prior promoted release — same fixture shape, the older as_of
    old_export = _write_export(tmp_path / "export_old", as_of=_OLD_AS_OF)
    old_dir = tmp_path / "rel_old"
    old_build = build_release(
        old_export,
        old_dir,
        descriptor_version=2,
        label=_OLD_LABEL,
        environment="production",
        code_commit=COMMIT,
        code_tree="clean",
        built_at=datetime(2026, 9, 30, 12, 0, 0, tzinfo=UTC),
        ontology_generated_sha256="b" * 64,
        evaluation={"status": "deferred"},
    )
    old_pub = old_build.publication_id
    store = _write_registry(tmp_path / "relroot", pub, old_pub, promoted=promoted)
    # the staged objects the bounded leg re-proves (staged/*/{pub}/) — the
    # previous release's tree staged first, exactly as its own promote left it
    rp.verb_stage(store, apply_=True, work_dir=old_dir, now=T0)
    rp.verb_stage(store, apply_=True, work_dir=work_dir, now=T0)
    return work_dir, pub, store


class _ApiFixture:
    """The served-API fetcher (V7's ``api_fetcher``) — ``/`` + ``/health``
    name the release, ``/terms`` carries the live-spine basis header, and
    any slice document declared under ``r/<pub>/api/index.json`` answers
    the release's own bytes (a defect seeds a wrong answer)."""

    def __init__(
        self,
        work_dir: Path,
        pub: str,
        *,
        named_pub: str | None = None,
        terms_basis: str = "live-spine",
        missing: frozenset[str] = frozenset(),
        tampered: frozenset[str] = frozenset(),
    ) -> None:
        self.work_dir = work_dir
        self.pub = pub
        self.named_pub = named_pub or pub
        self.terms_basis = terms_basis
        self.missing = missing
        self.tampered = tampered

    def get(self, path: str) -> rv.FetchResult:
        norm = "/" + path.lstrip("/")
        if norm in ("/", "/health"):
            return rv.FetchResult(
                200,
                {"X-SIG-Basis": "live-spine"},
                json.dumps(
                    {"service": "sig-api", "release": {"publication_id": self.named_pub}}
                ).encode(),
            )
        index = self.work_dir / "r" / self.pub / "api" / "index.json"
        docs: dict[str, str] = {}
        if index.is_file():
            for d in json.loads(index.read_bytes()).get("documents") or []:
                docs[str(d.get("route") or "")] = str(d.get("path") or "")
        if norm in docs:
            if norm in self.missing:
                return rv.FetchResult(404, {}, b"not found")
            body = (self.work_dir / docs[norm]).read_bytes()
            if norm in self.tampered:
                doc = json.loads(body)
                doc["tampered"] = True
                body = json.dumps(doc).encode()
            return rv.FetchResult(
                200,
                {"X-SIG-Basis": "release", "X-SIG-Basis-Release": self.named_pub},
                body,
            )
        return rv.FetchResult(
            200,
            {"X-SIG-Basis": self.terms_basis},
            json.dumps({"route": norm, "basis": "live-spine"}).encode(),
        )


#: A green ``sig.quality-report/1`` — the shape
#: ``exports.quality.build_quality_report`` emits; V15's gate consumes it.
def _quality_report(**over: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "version": "sig.quality-report/1",
        "generated_at": T0.isoformat(),
        "placement": "S",
        "target": "fixture",
        "checks": [
            {
                "id": "q.coverage",
                "mode": "enforce",
                "outcome": "pass",
                "regression": False,
                "evaluated": True,
            }
        ],
        "summary": {"class_s_trigger": False},
    }
    doc.update(over)
    return doc


def _ctx(
    work_dir: Path,
    pub: str,
    store: rp.LocalDirStore,
    *,
    mode: str = "S",
    axe_runner: Any = lambda _url, _paths: {},  # noqa: E731 - a clean scan
    pushed: bool | None = True,
    tree_clean: bool | None = True,
    api_fetcher: Any = ...,
    quality_report: Any = ...,
    **kw: Any,
) -> rv.VerifyContext:
    reg = work_dir.parent / "relroot" / "registry"
    gen_n = 2 if mode == "P" else 1
    gen = reg / "conf" / str(gen_n)
    # the prior release's pub — the registry's pre-promotion latest (S) or
    # the catalog's other promoted entry (P)
    latest_pub = str(json.loads(store.read("registry/latest.json")).get("publication_id") or "")
    old_pub = latest_pub
    if mode == "P" and old_pub == pub:
        for e in json.loads(store.read("registry/catalog.json")).get("publications"):
            if e.get("publication_id") != pub and e.get("state") == "promoted":
                old_pub = str(e["publication_id"])
    overrides = {
        "/releases/": (gen / "releases" / "index.html").read_bytes(),
        "/releases/index.html": (gen / "releases" / "index.html").read_bytes(),
        "/releases/catalog.json": (gen / "releases" / "catalog.json").read_bytes(),
        "/releases/latest.json": (gen / "releases" / "latest.json").read_bytes(),
        # V8's licence index — the bucket-root route the publish layer serves
        "/LICENCES.json": json.dumps(
            {
                "schema": "sig.licences-index/1",
                "compartments": [
                    {
                        "compartment": "sig_graph",
                        "license": "CC-BY-4.0",
                        "attribution": "Ohio DOT",
                    }
                ],
            }
        ).encode(),
    }
    if mode == "S":
        # the DCAT series catalog — nginx's gated `location /releases/` maps
        # it to staged/releases/catalog.jsonld; staging never gates (GT-9)
        # so it serves on S legs. On P legs the same prefix is deny-gated
        # for non-pub paths → a real 404 publicly (D-P35.56-1); the fixture
        # carries the public answer faithfully, not a smoothed 200.
        overrides["/releases/catalog.jsonld"] = (
            work_dir.parent / "relroot" / "staged" / "releases" / "catalog.jsonld"
        ).read_bytes()
    kw.setdefault("previous_pub", old_pub)
    kw.setdefault("previous_dir", work_dir.parent / "relroot" / "staged")
    kw.setdefault("repo_root", REPO)
    return rv.VerifyContext(
        mode=mode,
        work_dir=work_dir,
        pub=pub,
        fetcher=rv.TreeFetcher(
            work_dir,
            pub,
            promoted=(frozenset({pub, old_pub}) if mode == "P" else None),
            staging=(mode == "S"),
            release_header=f"{LABEL} {pub}",
            conf_gen_header=str(gen_n),
            overrides=overrides,
            deny_conf=(gen / "withdrawn.conf").read_bytes(),
            tombstone_root=work_dir.parent / "relroot" / "staged",
        ),
        api_fetcher=_ApiFixture(work_dir, pub) if api_fetcher is ... else api_fetcher,
        quality_report=_quality_report() if quality_report is ... else quality_report,
        origin=f"tree:{work_dir}",
        origin_kind="tree",
        store=store,
        pushed=pushed,
        tree_clean=tree_clean,
        axe_runner=axe_runner,
        now=T0,
        **kw,
    )


def _results(suite: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {r["check"]: r for r in suite["results"]}


# --------------------------------------------------------------------------- #
# The honest fixture is green — every check passes over the tree origin       #
# --------------------------------------------------------------------------- #


def test_suite_a_green_over_the_tree_origin(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    ctx = _ctx(work_dir, pub, store)
    suite = rv.run_suite(ctx)
    rows = _results(suite)
    assert suite["schema"] == rv.RESULT_SCHEMA
    assert suite["mode"] == "S" and suite["publication_id"] == pub
    assert list(rows) == list(rv.CHECKS_S)
    fails = {k: r for k, r in rows.items() if r["status"] != "pass"}
    assert not fails, json.dumps(fails, indent=1)[:4000]
    assert suite["verdict"] == "pass" and not suite["promotion_blocked"]

    # and the P-mode subset over the post-promotion posture (a second
    # fixture — promoted=True writes the gen-2 conf naming the candidate)
    work_dir2, pub2, store2 = _build_candidate(tmp_path / "p", promoted=True)
    ctx_p = _ctx(work_dir2, pub2, store2, mode="P")
    suite_p = rv.run_suite(ctx_p)
    rows_p = _results(suite_p)
    assert list(rows_p) == list(rv.CHECKS_P), "the P table is the §5.5 subset verbatim"
    # the faithful tree mirror surfaces the same real serving gap the
    # composed nginx proves: stamped pages link /releases/catalog.jsonld
    # (release_pages' ld+json alternate) but the public deny gate 404s it —
    # V5's only tolerated finding is exactly that recorded defect
    # (D-P35.56-1); anything beyond it is a real failure.
    fails_p = {k: r for k, r in rows_p.items() if r["status"] != "pass"}
    assert set(fails_p) == {"V5"}, json.dumps(
        {k: (r["status"], r["detail"]) for k, r in fails_p.items()}, indent=1
    )[:2000]
    dead = fails_p["V5"]["evidence"].get("dead_or_undeclared", {})
    assert dead == {404: ["/releases/catalog.jsonld"]}, json.dumps(dead, indent=1)


def test_result_rows_are_written_as_json(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    suite = rv.run_suite(_ctx(work_dir, pub, store))
    out = tmp_path / "results"
    written = rv.write_results(suite, out)
    assert len(written) == len(rv.CHECKS_S) + 1
    (suite_doc,) = list(out.glob("suite-S-*.json"))
    doc = json.loads(suite_doc.read_text())
    assert doc["schema"] == rv.RESULT_SCHEMA
    for path in out.glob("S-V*.json"):
        row = json.loads(path.read_text())
        assert row["status"] in ("pass", "fail", "skip")
        assert {"check", "mode", "status", "detail", "duration"} <= set(row)
        assert row["origin_kind"] == "tree"


# --------------------------------------------------------------------------- #
# The seeded-defect catalog — one planted defect per check (deliverable 11)   #
# --------------------------------------------------------------------------- #


def test_v1_fails_on_a_tampered_artifact(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    integrity = json.loads((work_dir / f"releases/{pub}/integrity_manifest.json").read_bytes())
    victim = next(a["path"] for a in integrity["artifacts"] if a["path"].startswith("r/"))
    p = work_dir / victim
    p.write_bytes(p.read_bytes() + b"tampered")
    # the tampered local bytes are what the tree origin serves
    row = rv.check_v1(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert row["evidence"]["validation_state"] == "incomplete" or row["evidence"]["mismatched"]


def test_v2_fails_on_an_unpushed_commit(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    row = rv.check_v2(_ctx(work_dir, pub, store, pushed=False))
    assert row["status"] == "fail"
    assert any("pushed" in f for f in row["evidence"]["failures"])


def test_v2_fails_on_a_non_production_environment(tmp_path: Path) -> None:
    """V2's environment=production rule — a descriptor minted for staging
    fails (it also fails V1's integrity leg, since the pub no longer
    recomputes — the defect is genuinely blocking)."""
    export = _write_export(tmp_path / "export")
    work_dir = tmp_path / "rel"
    build = build_release(
        export,
        work_dir,
        descriptor_version=2,
        label=LABEL,
        environment="staging",  # ← the defect
        code_commit=COMMIT,
        code_tree="clean",
        built_at=T0,
        ontology_generated_sha256="b" * 64,
        evaluation={"status": "deferred"},
    )
    pub = build.publication_id
    site_release = json.loads((work_dir / f"releases/{pub}/release.json").read_bytes())
    _write_site_tree(work_dir, pub, site_release)
    store = _write_registry(tmp_path / "relroot", pub, promoted=False)
    row = rv.check_v2(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert any("environment" in f for f in row["evidence"]["failures"])


def test_v3_fails_on_an_unlisted_route(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    (work_dir / "v" / pub / "internal").mkdir(parents=True)
    (work_dir / "v" / pub / "internal" / "index.html").write_text("<html>x</html>")
    row = rv.check_v3(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert any("internal" in f for f in row["evidence"]["failures"])


def test_v3_fails_when_a_denied_route_answers(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    # seed /curate/ inside the snapshot tree — it answers on staging, where
    # nothing gates (the allow-list check on v/ stays clean: the route is
    # planted under s/ where the denied probe still hits it? — no: denied
    # probes are site-root routes; plant it in v/).
    (work_dir / "v" / pub / "curate").mkdir(parents=True)
    (work_dir / "v" / pub / "curate" / "index.html").write_text("<html>curate</html>")
    row = rv.check_v3(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert any("/curate/" in f for f in row["evidence"]["failures"])


def test_v4_fails_on_a_missing_stamp(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    victim = work_dir / "v" / pub / "index.html"
    victim.write_text(victim.read_text().replace('name="sig-release"', 'name="x-release"'))
    row = rv.check_v4(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert any("sig-release" in f for f in row["evidence"]["failures"])


def test_v4_fails_on_a_wrong_release_header(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    ctx = _ctx(work_dir, pub, store)
    ctx.fetcher = rv.TreeFetcher(
        work_dir,
        pub,
        staging=True,
        release_header=f"{LABEL} p-{'9' * 64}",  # the revision env drifts
    )
    row = rv.check_v4(ctx)
    assert row["status"] == "fail"
    assert any("X-SIG-Release" in f for f in row["evidence"]["failures"])


def test_v5_fails_on_a_containment_escape(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    victim = work_dir / "s" / pub / "index.html"
    victim.write_text(victim.read_text().replace("</main>", '</main><a href="/map/">escape</a>'))
    row = rv.check_v5(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert row["evidence"]["containment_escapes"]


def test_v5_fails_on_a_dead_link(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    victim = work_dir / "v" / pub / "index.html"
    victim.write_text(
        victim.read_text().replace("</main>", '</main><a href="/no-such-route/">dead</a>')
    )
    row = rv.check_v5(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert "404" in json.dumps(row["evidence"]["dead_or_undeclared"])


def test_v11_fails_on_a_script_tag(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    victim = work_dir / "v" / pub / "index.html"
    victim.write_text(
        victim.read_text().replace("</body>", '<script src="/_astro/x.js"></script></body>')
    )
    row = rv.check_v11(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert row["evidence"]["legs"]["zero_js"] == "fail"


def test_v11_fails_on_an_oversized_content_page(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    victim = work_dir / "v" / pub / "index.html"
    victim.write_text(victim.read_text() + "<!--" + "x" * 200_000 + "-->")
    row = rv.check_v11(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert row["evidence"]["budget_violations"]


def test_v11_fails_on_a_serious_axe_violation(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    bad_runner = lambda _url, paths: {  # noqa: E731
        p: [{"id": "color-contrast", "impact": "serious", "nodes": 2}] for p in paths
    }
    row = rv.check_v11(_ctx(work_dir, pub, store, axe_runner=bad_runner))
    assert row["status"] == "fail"
    assert row["evidence"]["legs"]["axe"] == "fail"


#: A credential-shaped literal the V12 seeded defect plants. Written as an
#: explicit concatenation so the file bytes never carry the contiguous key
#: shape — the repo secret gate (``AKIA[0-9A-Z]{16}``) scans literals;
#: ``find_secrets`` scans the fixture file the test writes at runtime and
#: sees the joined value.
FAKE_AWS_KEY = "AKIA" + "IOSFODNN7EXAMPLE"


def test_v12_fails_on_a_secret(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    victim = work_dir / "v" / pub / "sources" / "index.html"
    victim.write_text(victim.read_text() + FAKE_AWS_KEY)
    row = rv.check_v12(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert row["evidence"]["hits"]


def test_v13_fails_on_an_unrendered_disclosure(tmp_path: Path) -> None:
    toml = tmp_path / "disclosures.toml"
    toml.write_text(
        'schema = "sig.disclosures/1"\n'
        "[[disclosures]]\n"
        f'id = "{DISCLOSURE_ID}"\n'
        f'text = "{DISCLOSURE_TEXT}"\n'
        'targets = ["/corrections/"]\n'
    )
    work_dir, pub, store = _build_candidate(
        tmp_path,
        disclosures=[{"id": DISCLOSURE_ID, "text": DISCLOSURE_TEXT}],
    )
    ctx = _ctx(work_dir, pub, store, disclosures_path=toml)
    row = rv.check_v13(ctx)
    assert row["status"] == "fail"
    assert any(DISCLOSURE_ID in f for f in row["evidence"]["failures"])


def test_v13_passes_when_the_disclosure_renders(tmp_path: Path) -> None:
    toml = tmp_path / "disclosures.toml"
    toml.write_text(
        'schema = "sig.disclosures/1"\n'
        "[[disclosures]]\n"
        f'id = "{DISCLOSURE_ID}"\n'
        f'text = "{DISCLOSURE_TEXT}"\n'
        'targets = ["/corrections/"]\n'
    )
    work_dir, pub, store = _build_candidate(
        tmp_path,
        disclosures=[{"id": DISCLOSURE_ID, "text": DISCLOSURE_TEXT}],
    )
    for ns in ("v", "s"):
        page = work_dir / ns / pub / "corrections" / "index.html"
        page.write_text(page.read_text().replace("</main>", f"{DISCLOSURE_TEXT}</main>"))
    row = rv.check_v13(_ctx(work_dir, pub, store, disclosures_path=toml))
    assert row["status"] == "pass", row["evidence"].get("failures")


# --------------------------------------------------------------------------- #
# Skip-blocks + the waiver contract                                            #
# --------------------------------------------------------------------------- #


def test_a_skip_blocks_promotion(tmp_path: Path) -> None:
    """An absent axe runner is an honest skip — and the suite's verdict
    blocks promotion (SIG-ENG-042, not a silent pass)."""
    work_dir, pub, store = _build_candidate(tmp_path)
    suite = rv.run_suite(_ctx(work_dir, pub, store, axe_runner=None))
    assert _results(suite)["V11"]["status"] == "skip"
    assert suite["verdict"] == "blocked" and suite["promotion_blocked"]


def test_no_origin_records_every_check_skipped(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    out = rp.verb_verify(
        store,
        apply_=False,
        work_dir=work_dir,
        mode="S",
        pushed=True,
        tree_clean=True,
    )
    assert out["verdict"] == "failed"
    suite = out["suites"][0]
    assert suite["origin_kind"] == "none"
    assert all(r["status"] == "skip" for r in suite["results"])


def test_waiver_only_under_class_s_and_never_v12(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)

    # a failed V11 (inline script planted — no src, so no V5 link leg)
    victim = work_dir / "v" / pub / "index.html"
    victim.write_text(victim.read_text().replace("</body>", "<script>void 0</script></body>"))
    ctx_r = _ctx(work_dir, pub, store, release_class="class_r", waivers=("V11=readout/1",))
    suite_r = rv.run_suite(ctx_r)
    assert suite_r["verdict"] == "blocked"
    assert suite_r["waivers"] == []
    assert suite_r["waivers_ignored"]

    # the same under class_s — the waiver is recorded and unblocks
    ctx_s = _ctx(work_dir, pub, store, release_class="class_s", waivers=("V11=readout/1",))
    suite_s = rv.run_suite(ctx_s)
    assert suite_s["verdict"] == "waived" and not suite_s["promotion_blocked"]
    assert suite_s["waivers"] == [{"check": "V11", "ref": "readout/1", "class": "class_s"}]

    # and V12 can never be waived even under class_s
    secret_page = work_dir / "v" / pub / "sources" / "index.html"
    secret_page.write_text(secret_page.read_text() + FAKE_AWS_KEY)
    ctx_v12 = _ctx(work_dir, pub, store, release_class="class_s", waivers=("V12=readout/1",))
    suite_v12 = rv.run_suite(ctx_v12)
    assert suite_v12["verdict"] == "blocked"
    assert _results(suite_v12)["V12"]["status"] == "fail"


# --------------------------------------------------------------------------- #
# The verb wiring — bounded default, suite under --mode, the apply journal    #
# --------------------------------------------------------------------------- #


def test_verb_verify_bounded_scope_without_mode(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    out = rp.verb_verify(store, apply_=False, work_dir=work_dir)
    assert out["verdict"] == "verified"
    assert "suites" not in out
    assert "bounded" in out["scope"]


def test_verb_verify_suite_mode_journals_verified_on_green(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    out = rp.verb_verify(
        store,
        apply_=True,
        work_dir=work_dir,
        mode="S",
        tree_origin=True,
        pushed=True,
        tree_clean=True,
        results_dir=tmp_path / "results",
        axe_runner=lambda _url, _paths: {},
        api_fetcher=_ApiFixture(work_dir, pub),
        quality_report=_quality_report(),
    )
    assert out["verdict"] == "verified" and out["applied"]
    assert out["event"].startswith("registry/events/")
    assert "verified" in out["event"]
    suite = out["suites"][0]
    assert suite["origin_kind"] == "tree" and suite["verdict"] == "pass"
    assert out["results_written"] == len(rv.CHECKS_S) + 1


def test_verb_verify_apply_journals_failed_on_a_seeded_defect(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    victim = work_dir / "v" / pub / "sources" / "index.html"
    victim.write_text(victim.read_text() + FAKE_AWS_KEY)
    with pytest.raises(rp.PipelineError) as err:
        rp.verb_verify(
            store,
            apply_=True,
            work_dir=work_dir,
            mode="S",
            tree_origin=True,
            pushed=True,
            tree_clean=True,
            results_dir=tmp_path / "results",
            axe_runner=lambda _url, _paths: {},
            api_fetcher=_ApiFixture(work_dir, pub),
            quality_report=_quality_report(),
        )
    assert err.value.code == "verify-failed"
    # the journal records the failure — promotion sees no `verified` event
    events = [e for e in rp.list_events(store) if e.get("verb") == "failed"]
    assert events, "a failing verify must journal `failed`"


def test_verb_verify_tree_p_mode_gates_unpromoted_namespaces(tmp_path: Path) -> None:
    """P-mode over the tree: the promoted map gates — a staged-but-
    unpromoted pub 404s by construction (the §4.2 default-0). The tree
    mirror is faithful to the gated ``/releases/`` prefix too, so the
    recorded catalog.jsonld public gap (D-P35.56-1) is the suite's one
    tolerated finding here — anything else is a real failure."""
    work_dir, pub, store = _build_candidate(tmp_path, promoted=True)
    out = rp.verb_verify(
        store,
        apply_=False,
        work_dir=work_dir,
        mode="P",
        tree_origin=True,
        pushed=True,
        tree_clean=True,
        results_dir=tmp_path / "results",
        api_fetcher=_ApiFixture(work_dir, pub),
        quality_report=_quality_report(),
    )
    non_pass = {
        (r["check"], r["status"], r.get("detail"))
        for s in out["suites"]
        for r in s["results"]
        if r["status"] != "pass"
    }
    assert out["verdict"] == "failed"  # the recorded gap blocks, honestly
    assert {r[0] for r in non_pass} == {"V5"}, json.dumps(sorted(non_pass), indent=1)
    dead = [
        r["evidence"]["dead_or_undeclared"]
        for s in out["suites"]
        for r in s["results"]
        if r["check"] == "V5"
    ]
    assert dead == [{404: ["/releases/catalog.jsonld"]}]
