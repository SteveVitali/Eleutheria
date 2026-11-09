# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

"""P36.54 (K6 VIZ-01a) — dossier map + locator figure emission.

The placement-bound export emits, per D-K4-3 page:

* the **restricted** ``sig.dossier-visuals/1`` geometry under
  ``inputs/dossier-visuals/<slug>.json`` — deterministic, present on disk
  via ``restricted_artifacts``, NEVER in ``web_artifacts`` or the manifest
  (SIG-UI-134 / DV12);
* the published ``figures[]`` metadata twin on each ``sig.dossier/2`` (id,
  caption, desc counts, links, rule — NO geometry, K6 §9.2);
* ``web/map/coverage_by_jurisdiction.json`` under the real
  ``declared-scope@1`` rule (D-K1-4 = yes, ADR-241 — P37.17 replaced the
  soft ``rule-pending@1`` posture);
* the ``sig.locator-symbols/1`` sheet + index and the country/admin-1
  standalone SVG downloads (D-K6-5);
* the ``sig.dossier-visuals-index/1`` size/time report.
"""

from __future__ import annotations

import importlib.util as _ilu
import json

import pytest
from placement_fixtures import build_placement_env
from test_spine_export import _build24, _fixture_claims

_needs_duckdb = pytest.mark.skipif(
    _ilu.find_spec("duckdb") is None,
    reason="duckdb is required for the placement engine",
)


@pytest.fixture(scope="module")
def env(tmp_path_factory: pytest.TempPathFactory):
    return build_placement_env(tmp_path_factory.mktemp("dossier_visuals"))


@pytest.fixture(scope="module")
def engine(env):
    from exports.placement import PlacementEngine

    return PlacementEngine(env.pack_dir, env.registry_path, spec_path=env.spec_path)


@pytest.fixture(scope="module")
def export(engine):
    from test_keyed_dossiers import _extra_claims

    return _build24(_fixture_claims() + _extra_claims(), placement=engine)


def _visuals(export) -> dict[str, dict]:
    out = {}
    for path, data in export.restricted_artifacts.items():
        if path.startswith("inputs/dossier-visuals/") and path.endswith(".json"):
            doc = json.loads(data.decode("utf-8"))
            if doc.get("schema") == "sig.dossier-visuals/1":
                out[doc["jurisdiction"]["slug_path"]] = doc
    return out


EXPECTED_PAGES = {
    "usa",
    "usa/ca",
    "usa/fl",
    "usa/ca/verdin-county-06037",
    "gbr",
    "idn",
}


@_needs_duckdb
def test_visuals_emit_restricted_and_never_published(export) -> None:
    """DV12/SIG-UI-134: the geometry docs exist ONLY as restricted inputs —
    never a ``web/`` artifact and never a manifest row."""
    docs = _visuals(export)
    assert set(docs) == EXPECTED_PAGES
    for path in export.restricted_artifacts:
        assert not path.startswith("web/")
    for path in export.web_artifacts:
        assert "dossier-visuals" not in path and "dossier_visuals" not in path
    manifest_paths = {a.path for a in export.manifest.artifacts}
    assert not any("dossier-visuals" in p for p in manifest_paths)


@_needs_duckdb
def test_figures_byte_deterministic(engine) -> None:
    """Rebuilding the same export yields byte-identical restricted docs."""
    from test_keyed_dossiers import _extra_claims

    a = _build24(_fixture_claims() + _extra_claims(), placement=engine)
    b = _build24(_fixture_claims() + _extra_claims(), placement=engine)
    # The size/time report's wall_seconds legitimately differs run to run —
    # every other byte (figure SVG, geometry, indexes) must be identical.
    a_docs = {k: v for k, v in a.restricted_artifacts.items() if not k.endswith("index.json")}
    b_docs = {k: v for k, v in b.restricted_artifacts.items() if not k.endswith("index.json")}
    assert a_docs == b_docs
    ra = json.loads(a.restricted_artifacts["inputs/dossier-visuals/index.json"])
    rb = json.loads(b.restricted_artifacts["inputs/dossier-visuals/index.json"])
    ra.pop("wall_seconds"), rb.pop("wall_seconds")
    assert ra == rb


@_needs_duckdb
def test_map_figure_shape_and_honesty_counters(export) -> None:
    docs = _visuals(export)
    usa = docs["usa"]["map"]
    assert usa["schema"] == "sig.figure-geo-meta/1"
    assert usa["mode"] in ("points", "h3-areas")
    svg = usa["svg"]
    assert svg.startswith("<svg")
    assert 'class="sig-fig' in svg
    # DV12: no per-area numeric leak — no data-*, no per-area <title>.
    assert "data-" not in svg
    assert "<script" not in svg
    # The children layer: US states — the real declared-scope@1 rule
    # (D-K1-4 = yes, ADR-241; the P35.x `rule_pending` soft posture is gone):
    # a source's declared scope covers the child jkey and its descendants.
    kids = {c["jkey"]: c for c in usa["children"]}
    assert "us.census.geoid.county:06037" not in kids  # counties are grandchildren
    assert kids["iso3166-2:US-CA"]["coverage"] == "covered"
    assert kids["iso3166-2:US-CA"]["href"] == "/dossier/usa/ca/"
    # A state with no dossier page draws outline-only (no link).
    assert kids["iso3166-2:US-KS"]["href"] is None
    # The rule honestly distinguishes "looked" from "not looked": the
    # fixture's registry declares no scope covering Kansas.
    assert kids["iso3166-2:US-KS"]["coverage"] == "not_covered"


@_needs_duckdb
def test_not_drawn_counters_on_the_fixture(export) -> None:
    docs = _visuals(export)
    # CA dossier: B is declared-CA located-FL → located_elsewhere keyed on FL's leaf.
    ca = docs["usa/ca"]["map"]
    nd = ca["not_drawn"]
    assert [x["jkey"] for x in nd["located_elsewhere"]] == ["us.census.geoid.county:20100"] or any(
        j.startswith("us.census.geoid.county:") or j == "iso3166-2:US-FL"
        for j, _ in [(x["jkey"], x["records"]) for x in nd["located_elsewhere"]]
    )
    # E (declared CA, centroid-stamped → declared fallback, point withheld)
    # counts under `conflicting` — withheld coordinates, the K6 V-3 third
    # honesty line; the fixture carries no no-coordinate record, so
    # declared_no_point is the honest 0.
    assert nd["conflicting"] >= 1
    assert nd["declared_no_point"] == 0
    # GBR dossier: C (axis_swap_suspected) + D (null_island) are withheld → conflicting.
    gbr = docs["gbr"]["map"]
    assert gbr["not_drawn"]["conflicting"] == 2
    # Every drawable record's count reconciles: drawn + not-drawn = records_total.
    for doc in docs.values():
        m = doc["map"]
        if m.get("status") == "no_boundary":
            continue
        drawn = m["desc"]["records_drawn"]
        total_not_drawn = (
            m["not_drawn"]["declared_no_point"]
            + sum(x["records"] for x in m["not_drawn"]["located_elsewhere"])
            + m["not_drawn"]["conflicting"]
            + m["not_drawn"]["tier3"]
        )
        assert drawn + total_not_drawn == m["desc"]["records_total"], doc["jurisdiction"][
            "slug_path"
        ]


@_needs_duckdb
def test_county_children_via_containment(export) -> None:
    """A US county's children are its census places (containment-derived —
    registry parentage names a place's STATE, never its county)."""
    county = _visuals(export)["usa/ca/verdin-county-06037"]["map"]
    kids = {c["jkey"]: c for c in county["children"]}
    assert set(kids) == {"us.census.geoid.place:0644000"}  # Verdin city only
    assert kids["us.census.geoid.place:0644000"]["coverage"] == "covered"
    # Below the D-K4-3 page threshold → outline drawn, no drill-down link.
    assert kids["us.census.geoid.place:0644000"]["href"] is None


@_needs_duckdb
def test_locator_geometry_and_symbols(export) -> None:
    docs = _visuals(export)
    # A state locates inside its country; a county inside its state; a
    # country has no parent context → typed absence, never a blank locator.
    ca = docs["usa/ca"]["locator"]
    assert ca["parent_symbol"].startswith("loc-")
    assert ca["parent_jkey"] == "iso3166-1:US"
    assert ca["child_d"].startswith("M")
    assert ca["viewbox"][0] == 160
    county = docs["usa/ca/verdin-county-06037"]["locator"]
    assert county["parent_jkey"] == "iso3166-2:US-CA"
    assert docs["usa"]["locator"]["status"] == "no_parent_context"
    # The public symbol sheet carries exactly the needed parents.
    sheet = json.loads(export.web_artifacts["web/figures/locator-symbols.json"])
    assert sheet["schema"] == "sig.locator-symbols/1"
    assert set(sheet["symbols"]) == {"iso3166-1:US", "iso3166-2:US-CA"}
    svg = export.web_artifacts["web/figures/locator-symbols.svg"].decode()
    assert "loc-iso3166-1-us" in svg and "loc-iso3166-2-us-ca" in svg


@_needs_duckdb
def test_coverage_layer_is_declared_scope(export) -> None:
    """The real ``declared-scope@1`` coverage table (D-K1-4 = yes, ADR-241 —
    P37.17 replaced the soft ``rule-pending@1`` emission)."""
    cov = json.loads(export.web_artifacts["web/map/coverage_by_jurisdiction.json"])
    assert cov["schema"] == "sig.jurisdiction-coverage/1"
    assert cov["rule_version"] == "declared-scope@1"
    assert cov["rule_decision"] == "D-K1-4"
    assert cov["pending"] is False
    assert cov["legend"] == (
        "Where SIG has looked: a source counts where it declares coverage; "
        "global crowdsourced sources (OSM, DeFlock) are listed but do not count"
    )
    # The corroboration legend names the L3 CONF-07b gap honestly (UXR-14).
    assert cov["corroboration_legend"] == ("2+ source records; republications not yet collapsed")
    rows = cov["jurisdictions"]
    # Declared scope covers a jkey and its descendants — the fixture's
    # declared CA scope covers the state, the county and Verdin city.
    assert rows["iso3166-2:US-CA"]["coverage"] == "covered"
    assert rows["us.census.geoid.county:06037"]["coverage"] == "covered"
    assert rows["us.census.geoid.place:0644000"]["coverage"] == "covered"
    # Nothing declares Kansas or Indonesia — honestly "not looked".
    assert rows["iso3166-2:US-KS"]["coverage"] == "not_covered"
    assert rows["iso3166-1:ID"]["coverage"] == "not_covered"
    for row in rows.values():
        assert row["coverage"] in ("covered", "not_covered")
        assert row["basis"] == "declared_scope"
        assert isinstance(row["observed_sources"], list)
        assert isinstance(row["sources"], list)
        assert isinstance(row["technologies"], list)
        # Crowdsourced/scope-less sources are listed, never counted (D-K1-4 (b)).
        assert isinstance(row["global_sources_not_counted"], list)


@_needs_duckdb
def test_standalone_downloads_d_k6_5_scope(export) -> None:
    """Standalone SVGs exist for country + admin-1 dossiers ONLY (D-K6-5)."""
    svgs = sorted(p for p in export.web_artifacts if p.startswith("web/figures/dossier/"))
    assert svgs == [
        "web/figures/dossier/gbr.svg",
        "web/figures/dossier/idn.svg",
        "web/figures/dossier/usa.svg",
        "web/figures/dossier/usa/ca.svg",
        "web/figures/dossier/usa/fl.svg",
    ]
    for path in svgs:
        svg = export.web_artifacts[path].decode()
        assert svg.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert "<style>" in svg  # the standalone document's permitted block
        assert "prefers-color-scheme" in svg
        # DV12: no per-area numeric leak — no data-* ATTRIBUTE (the
        # --fig-data-* CSS variable names inside the style block are fine).
        import re as _re

        assert _re.search(r"\sdata-[a-zA-Z]", svg) is None
        assert "<script" not in svg
    # The county dossier earns no download (D-K6-5).
    assert "web/figures/dossier/usa/ca/verdin-county-06037.svg" not in export.web_artifacts


@_needs_duckdb
def test_dossier_doc_figures_twin_no_geometry(export) -> None:
    """The published twin carries id/caption/desc/links/rule — no geometry."""
    for path, data in export.web_artifacts.items():
        if not (
            path.startswith("web/dossiers/")
            and path.endswith(".json")
            and not path.endswith("index.json")
        ):
            continue
        doc = json.loads(data)
        figs = doc.get("figures")
        assert figs and figs[0]["figure_id"] == "fig-map"
        row = figs[0]
        assert row["caption_drafted"].startswith("agent-drafted")
        assert row["links"]["sites"] == f"/dossier/{doc['slug_path']}/sites/"
        # 'rule pending' posture is stated on the soft layer.
        if row["caption"] is not None:
            assert "rule pending" in row["caption"]
        assert "svg" not in row["meta"] and "outline_d" not in row["meta"]
        # Download link only for country/admin-1 (D-K6-5).
        if doc["slug_path"].count("/") >= 2:
            assert row["links"]["download"] is None


@_needs_duckdb
def test_visuals_index_report(export) -> None:
    rep = json.loads(export.restricted_artifacts["inputs/dossier-visuals/index.json"])
    assert rep["schema"] == "sig.dossier-visuals-index/1"
    assert rep["dossier_figures"] == len(EXPECTED_PAGES)
    assert rep["standalone_svgs"] == 5
    assert rep["locator_parent_symbols"] == 2
    assert rep["wall_seconds"] >= 0
    by_slug = {r["slug_path"]: r for r in rep["rows"]}
    assert set(by_slug) == EXPECTED_PAGES
    for row in rep["rows"]:
        assert row["bytes"] > 0 and row["gzip_bytes"] > 0
        assert row["path"].startswith("inputs/dossier-visuals/")


@_needs_duckdb
def test_no_placement_no_visuals() -> None:
    """No engine bound → honest degrade: no visuals, no coverage layer, no
    restricted artifacts, and the pre-keyed flat dossiers stay byte-stable."""
    export = _build24(_fixture_claims())
    assert export.restricted_artifacts == {}
    assert "web/map/coverage_by_jurisdiction.json" not in export.web_artifacts
    assert "web/figures/locator-symbols.json" not in export.web_artifacts


@_needs_duckdb
def test_spec_children_all_carry_a_real_coverage_verdict(export) -> None:
    """Every emitted child in every figure carries a closed-vocabulary
    ``declared-scope@1`` verdict — ``covered``/``not_covered``, never the
    retired soft ``rule_pending`` placeholder (D-K1-4 = yes, ADR-241)."""
    for doc in _visuals(export).values():
        m = doc["map"]
        for child in m.get("children", []):
            assert child["coverage"] in ("covered", "not_covered")
