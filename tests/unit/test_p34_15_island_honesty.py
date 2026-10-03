# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.15 island-honesty sweeps (QW-12, K1 NEW-20, K12b NEW-7, K2 NEW-6 /
D-K2-2, K6 NEW-1).

Source-level invariants the e2e and component tests cannot reach:

* the retired ``/task/`` surface never comes back as a link (K12b NEW-7 — the
  5,290 dead gap links stay counts, never hrefs);
* the network page carries neither a centrality statistic element nor the
  withdrawn "deterministic identity resolution … exact … never an estimate"
  claim (K2 NEW-6, SIG-IDENT-030 by abstention);
* the analytics exporter emits an empty ``statistics`` list — the `focus`
  block is a presentation mechanism, not a published ranking;
* no literal link anywhere in ``web/src`` carries a ``sig.workspace-state/1``
  parameter the target island does not apply (K6 NEW-1's link half), and the
  ignored-parameter notice is actually rendered by all three islands.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_SRC = REPO_ROOT / "web/src"
PAGES = WEB_SRC / "pages"

# The contract parameters each view applies — mirrored from APPLIED_PARAMS in
# web/src/lib/workspace-state.ts (kept in sync by test_applied_params_mirror).
APPLIED_PARAMS = {
    "list": {"release", "q", "kind", "focus", "view"},
    "map": {"release", "collection", "focus", "view"},
    "network": {"release", "focus", "view"},
}
VIEW_FOR_PATH = {"/map/": "map", "/network/": "network", "/search/": "list"}
# Only contract params gate a link: `v` versions the contract, and unknown
# params already fail visibly via the parse `issues` note (never read as
# filters). Everything else the target does not apply is an offender.
CONTRACT_PARAMS = {
    "release",
    "collection",
    "q",
    "kind",
    "jurisdiction",
    "technology",
    "source",
    "location",
    "focus",
    "view",
    "page",
}


def _web_sources() -> list[Path]:
    files: list[Path] = []
    bases = [WEB_SRC / "pages", WEB_SRC / "components", WEB_SRC / "layouts", WEB_SRC / "islands"]
    for base in bases:
        files.extend(sorted(base.rglob("*.astro")))
        files.extend(sorted(base.rglob("*.tsx")))
    return files


def test_no_task_link_ever_returns() -> None:
    """K12b NEW-7: gap affordances are counts leading to the dossier — the
    retired `/task/` intake surface is never linked again."""
    offenders: list[str] = []
    for path in _web_sources():
        if "internal" in path.parts:
            continue
        for m in re.finditer(r'href\s*=\s*[{"\']?(/task/[^"\'}\s]*)', path.read_text("utf-8")):
            offenders.append(f"{path.relative_to(REPO_ROOT)}: {m.group(1)}")
    assert offenders == [], f"dead /task/ links present: {offenders}"


def _rendered_body(path: Path) -> str:
    """The emitted markup region with HTML comments stripped — code comments
    may name the withdrawn claim; rendered text must not."""
    src = path.read_text("utf-8")
    body = src.split("---", 2)[2] if src.startswith("---") else src
    return re.sub(r"<!--.*?-->", "", body, flags=re.S)


def test_network_page_carries_no_centrality_or_exact_identity_claim() -> None:
    """K2 NEW-6 / D-K2-2: /network/ publishes no statistic element and no
    'deterministic identity resolution … exact' claim; the withdrawal note is
    honest abstention copy, not a zero measurement."""
    body = _rendered_body(PAGES / "network.astro")
    for forbidden in (
        "centrality-stat",
        "er-disclosure",
        "deterministic identity resolution",
        "exact for the exported graph",
        "never an estimate",
        "exact",
    ):
        assert forbidden not in body, f"/network/ still carries {forbidden!r}"
    src = (PAGES / "network.astro").read_text("utf-8")
    assert "getNetworkCentrality" not in src and "CENTRALITY_STATS" not in src
    # The abstention is stated, not silent.
    assert 'data-testid="centrality-withdrawn"' in src


def test_network_island_carries_no_centrality_rendering() -> None:
    """No centrality prop, element or import — the doc comment may name the
    withdrawal; code may not carry a statistic."""
    src = (WEB_SRC / "islands/NetworkIsland.tsx").read_text("utf-8")
    body = re.sub(r"/\*.*?\*/", "", src, flags=re.S)  # strip block comments
    for forbidden in (
        "centrality",
        "graph-island-centrality",
        "graph-island-er-disclosure",
        "CentralityStatistic",
        "selectedStats",
    ):
        assert forbidden not in body, f"NetworkIsland still carries {forbidden!r}"


def test_exported_analytics_abstains_from_the_ranking() -> None:
    """The exporter's centrality artifact ships an EMPTY statistics list; the
    focus block keeps its stated rule so the ego view can centre
    deterministically. (The emitted payload is swept for the withdrawn claim
    by tests/exports/test_export_analytics.py — the module's comments may name
    it only to say it is withdrawn.)"""
    src = (REPO_ROOT / "exports/src/exports/analytics.py").read_text("utf-8")
    assert "statistics=[]," in src
    assert "_ER_DISCLOSURE" not in src
    # The fixture-export mirror does the same.
    fx = (REPO_ROOT / "web/scripts/build-fixture-export.ts").read_text("utf-8")
    assert "statistics: []" in fx
    assert "CENTRALITY_STATS" not in fx


def test_map_page_counts_records_not_devices_and_suppresses_no_silently() -> None:
    """QW-12: the tabular equivalent says "records", the bins table prints the
    suppressed word rather than a number, and the legend is data-filtered."""
    src = (PAGES / "map.astro").read_text("utf-8")
    assert "Located records (tabular equivalent)" in src
    assert "Records without a published point" in src
    assert "binCountLabel(bin)" in src  # suppressed cells print the word, not a figure
    assert "layerControlsWithData" in src and "layersWithData" in src
    # No literal "assets" count sentence remains (record vocabulary only).
    assert "device(s)" not in src
    # The contested count never fabricates a dossier link — it is conditional
    # on the slug existing.
    assert "dossierSlugFor" in src and "DOSSIER_SLUGS" in src


def test_map_intro_no_longer_claims_zero_js_above_the_island() -> None:
    """K1 NEW-20: the intro paragraph must not say the map ships no client
    JavaScript — the opt-in island hydrates on this route."""
    src = (PAGES / "map.astro").read_text("utf-8")
    body = src.split("---", 2)[2]
    assert "no client JavaScript" not in body
    assert "renders as static content" not in body


def test_island_links_never_carry_a_facet_the_target_ignores() -> None:
    """K6 NEW-1 (link half): every literal island href in web source applies
    every contract parameter it carries — a link that would land on an
    unfiltered view named as filtered is an offender."""
    href_re = re.compile(
        r"(?:href\s*=\s*|viewHref\([^,]+,\s*|workspaceHref\()"
        r'["\'](/map/|/network/|/search/)\?([^"\']*)["\']'
    )
    offenders: list[str] = []
    for path in _web_sources():
        if "internal" in path.parts:
            continue
        for m in href_re.finditer(path.read_text("utf-8")):
            route, query = m.group(1), m.group(2)
            view = VIEW_FOR_PATH[route]
            params = {p.split("=")[0] for p in query.split("&") if p} - {"v"}
            ignored = {p for p in params & CONTRACT_PARAMS if p not in APPLIED_PARAMS[view]}
            if ignored:
                offenders.append(
                    f"{path.relative_to(REPO_ROOT)}: {route}?{query} ignores {sorted(ignored)}"
                )
    assert offenders == [], f"island links carrying ignored facets: {offenders}"


def test_every_island_renders_the_ignored_facet_notice() -> None:
    """K6 NEW-1 (surface half): all three islands destructure `ignored` from
    useWorkspaceState and render the facetNoticeText notice visibly."""
    for island in ["MapIsland.tsx", "NetworkIsland.tsx", "SearchIsland.tsx"]:
        src = (WEB_SRC / "islands" / island).read_text("utf-8")
        assert "ignored" in src, f"{island} never reads the ignored-param list"
        assert "facetNoticeText" in src, f"{island} never renders the notice"
        assert 'data-testid="facet-not-applied"' in src
    ws = (WEB_SRC / "lib/workspace-state.ts").read_text("utf-8")
    assert "unappliedParams" in ws and "IGNORED_FACET_NOTICE" in ws


def test_applied_params_mirror_the_workspace_contract() -> None:
    """The APPLIED_PARAMS table in this file must mirror the single source of
    truth in workspace-state.ts — drift here would blind the link sweep."""
    ws = (WEB_SRC / "lib/workspace-state.ts").read_text("utf-8")
    m = re.search(
        r"export const APPLIED_PARAMS: Record<WorkspaceView, readonly string\[\]> = \{(.*?)\};",
        ws,
        re.S,
    )
    assert m, "APPLIED_PARAMS table not found in workspace-state.ts"
    parsed: dict[str, set[str]] = {}
    for vm in re.finditer(r"(\w+): \[([^\]]*)\]", m.group(1)):
        parsed[vm.group(1)] = set(re.findall(r'"([^"]+)"', vm.group(2)))
    assert parsed == APPLIED_PARAMS
