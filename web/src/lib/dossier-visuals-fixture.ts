// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.55 (K6 VIZ-02): the committed `sig.dossier-visuals/1` fixture corpus —
 * the same document shape P36.54's export emits under
 * `inputs/dossier-visuals/`, authored so every dossier the fixture build
 * renders carries the visuals doc the v2 template reads. The SVGs are small
 * deterministic stand-ins (an outline + a few marks) — the fixture proves the
 * page's render contract (typed states, caption wiring, reconciliation
 * counters, the accessible twin), not the geography.
 *
 * Reconciliation is authored, never accidental (SIG-UI-132): every doc's
 * `desc.records_total` equals its fixture dossier's published record figure
 * and `records_drawn + not-drawn counters == records_total` — the unit test
 * (`dossier-visuals.test.ts`) recomputes both against the dossiers.
 */

import type {
  DossierVisualsDoc,
  LocatorSymbols,
  MapMeta,
  NetworkSlot,
} from "./dossier-visuals";
import { DOSSIERS } from "./dossier-fixture";
import type { Dossier } from "./dossier";

const SCHEMA = "sig.dossier-visuals/1";
const META_SCHEMA = "sig.figure-geo-meta/1";

/** Per-dossier authored count set: [records_total, records_drawn, elsewhere, conflicting, tier3]. */
const COUNTS: Record<string, [number, number, number, number, number]> = {
  usa: [5666, 5401, 3, 0, 0],
  "usa/ok": [480, 420, 3, 0, 0],
  "usa/ok/oklahoma-county-40109": [420, 391, 3, 0, 0],
  "usa/ok/oklahoma-city-4064000": [391, 361, 0, 0, 0],
  "usa/ok/cleveland-county-40131": [48, 48, 0, 0, 0],
  "usa/ok/norman-city-4055000": [8, 8, 0, 0, 0],
  "usa/tx": [5120, 4913, 0, 0, 0],
  "usa/tx/harris-county-48201": [5032, 5032, 0, 0, 0],
  can: [1546, 1546, 0, 0, 0],
  "can/on": [1534, 1534, 0, 0, 0],
  fra: [212, 212, 0, 0, 0],
  deu: [154, 154, 0, 0, 0],
  // The worked flat dossiers — the OKC numbers mirror the dossier's own
  // record (38 reported active, 31 independently mapped, 7 unmapped).
  "oklahoma-city": [38, 31, 0, 0, 0],
  "paris-alpr": [12, 10, 0, 0, 0],
  "brussels-alpr": [9, 7, 0, 0, 0],
};

/** The dossier whose typed `no_boundary` state the fixture exercises. */
const NO_BOUNDARY = "usa/vi";

/** A deterministic pseudo-polygon path (a jittered rectangle) — fixture geometry. */
function blob(cx: number, cy: number, w: number, h: number, seed: number): string {
  const pts: [number, number][] = [];
  for (let i = 0; i < 8; i++) {
    const a = (Math.PI * 2 * i) / 8;
    const j = 0.75 + ((seed * 37 + i * 91) % 50) / 200; // 0.75–0.995
    pts.push([cx + (Math.cos(a) * w * j) / 2, cy + (Math.sin(a) * h * j) / 2]);
  }
  return `M ${pts.map((p) => `${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" L ")} Z`;
}

function seedOf(slug: string): number {
  let s = 0;
  for (const c of slug) s = (s * 31 + c.charCodeAt(0)) % 9973;
  return s;
}

/** The small deterministic fixture SVG — outline, child outlines, marks. */
function fixtureSvg(d: Dossier, drawn: number, children: { href: string | null }[]): string {
  void children;
  const seed = seedOf(d.slug);
  const mode = drawn > 1000 ? "h3-areas" : "points";
  const marks = Math.min(drawn, mode === "h3-areas" ? 11 : 9);
  const parts: string[] = [
    `<path d="${blob(360, 230, 640, 400, seed)}" class="sig-fig-outline"></path>`,
  ];
  children.forEach((c, i) => {
    const d2 = blob(140 + (i % 3) * 220, 150 + Math.floor(i / 3) * 160, 150, 110, seed + i);
    // No <a> wrappers — SVG links would be non-focusable interactive
    // content (axe nested-interactive) and intercept pointer clicks; the
    // accessible twin (places table) carries the drill-down links.
    const path = `<path d="${d2}" class="sig-fig-child sig-fig-child-pending"></path>`;
    parts.push(path);
  });
  for (let i = 0; i < marks; i++) {
    const x = 120 + ((seed * 13 + i * 67) % 480);
    const y = 110 + ((seed * 29 + i * 53) % 240);
    parts.push(
      mode === "points"
        ? `<circle cx="${x}" cy="${y}" r="4" class="sig-fig-point sig-fig-src-single"></circle>`
        : `<path d="${blob(x, y, 34, 30, seed + i * 7)}" class="sig-fig-area sig-fig-src-single"></path>`,
    );
  }
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 460" ` +
    `class="sig-fig sig-fig-geo" role="img" ` +
    `aria-label="Fixture stand-in map of ${d.name ?? d.jurisdiction} published records">` +
    parts.join("") +
    `</svg>`
  );
}

function meta(
  d: Dossier,
  counts: [number, number, number, number, number],
  children: { jkey: string; coverage: string; drawn: boolean; href: string | null }[],
): MapMeta {
  const [total, drawn, elsewhere, conflicting, tier3] = counts;
  const noPoint = total - drawn - elsewhere - conflicting - tier3;
  return {
    schema: META_SCHEMA,
    viewbox: [720, 460],
    zoom: drawn > 1000 ? 6 : 11,
    mode: drawn > 1000 ? "h3-areas" : "points",
    h3_res: drawn > 1000 ? 4 : null,
    rule: "published-points-and-h3",
    cap_actions: [],
    not_drawn: {
      declared_no_point: noPoint,
      located_elsewhere: elsewhere > 0 ? [{ jkey: "fixture:elsewhere", records: elsewhere }] : [],
      conflicting,
      tier3,
    },
    desc: {
      records_drawn: drawn,
      areas_drawn: drawn > 1000 ? Math.min(drawn, 11) : 0,
      records_total: total,
      jurisdiction: d.jurisdiction_key ?? d.slug,
      release: "fixture-build",
      publication_id: null,
    },
    compartments_drawn: ["sig-public"],
    children,
    boundary_vintage: d.boundary_vintage ?? "fixture-pack@1",
    size_bytes: 0,
    gzip_bytes: 0,
  };
}

/** The parent-context glyph each drawn locator cites (fixture stand-in). */
const PARENT_BLOB = blob(80, 50, 140, 86, 4242);

// ---------------------------------------------------------------------------
// P37.28 (K6 VIZ-01b): the fixture `networks[]` corpus — a small authored
// stand-in proving the page's render contract (drawn figure, toggles, table
// twin, typed absences). Same posture as the map stand-in above: the fixture
// proves the contract, not the graph.
// ---------------------------------------------------------------------------

function fixtureNetSvg(variant: "wide" | "narrow", withAcc: boolean): string {
  const w = variant === "wide" ? 720 : 360;
  const nodes: string[] = [
    `<a href="/entity/agency/oklahoma-city-police--a1b2c3d/"><path d="M10 40a4.5 4.5 0 1 0 9 0a4.5 4.5 0 1 0 -9 0Z" class="sig-fig-node sig-fig-node-agency"/><text x="24" y="44" class="sig-fig-node-label">Oklahoma City Police…</text></a>`,
    `<a href="/entity/agency/county-sheriff--e4f5g6h/"><path d="M10 60a4.5 4.5 0 1 0 9 0a4.5 4.5 0 1 0 -9 0Z" class="sig-fig-node sig-fig-node-agency"/><text x="24" y="64" class="sig-fig-node-label">Oklahoma County Sheriff</text></a>`,
    `<a href="/graphs/supply/usa-ok/"><path d="M${w - 24} 50a4.5 4.5 0 1 0 9 0a4.5 4.5 0 1 0 -9 0Z" class="sig-fig-node sig-fig-node-vendor"/><text x="${w - 38}" y="54" class="sig-fig-node-label" text-anchor="end">Flock Safety</text></a>`,
  ];
  const edges = withAcc
    ? `<g aria-hidden="true"><path d="M20 40C200 40 500 50 ${w - 34} 50" class="sig-fig-edge sig-fig-edge-acc-configured"/><path d="M20 60C200 60 500 52 ${w - 34} 50" class="sig-fig-edge sig-fig-edge-acc-declared"/><path d="M20 50C200 50 500 46 ${w - 34} 50" class="sig-fig-edge sig-fig-edge-acc-observed"/><path d="M20 55C200 55 500 55 ${w - 34} 50" class="sig-fig-edge sig-fig-edge-muted"/></g>`
    : `<g aria-hidden="true"><path d="M20 50C200 50 500 50 ${w - 34} 50" class="sig-fig-edge"/></g>`;
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} 120" class="sig-fig sig-fig-graph" role="img" ` +
    `aria-label="Fixture stand-in ${variant} network figure">` +
    `<title>Fixture stand-in network figure (${variant})</title>` +
    `<desc>Fixture stand-in: 2 anchors, 1 counterparty, 4 recorded relations.</desc>` +
    edges +
    nodes.join("") +
    `<text x="8" y="110" class="sig-fig-legend">configured (solid) · declared (dashed) · observed (double) · muted = historical/undated</text>` +
    `</svg>`
  );
}

const TWIN_COLS = [
  "counterparty",
  "relation",
  "direction",
  "access_kind",
  "date",
  "date_kind",
  "currency",
  "support",
  "sources",
  "evidence",
];

function drawnAccess(slug: string): NetworkSlot {
  return {
    figure_id: "fig-access",
    slot: "fig-4",
    family: "access",
    overview: "access",
    title: "Who can search this data",
    status: "drawn",
    svg: fixtureNetSvg("wide", true),
    svg_narrow: fixtureNetSvg("narrow", true),
    meta: {
      schema: "sig.figure-graph-meta/1",
      viewbox: [720, 120],
      narrow_viewbox: [360, 120],
      mode: "bipartite",
      cap_actions: [],
      legend: [
        { id: "line:configured", label: "configured", plain: "a configured access edge (solid line)" },
        { id: "line:declared", label: "declared", plain: "a declared-policy access edge (dashed line)" },
        { id: "line:observed", label: "observed", plain: "an observed-use access edge (double line)" },
        { id: "currency:muted", label: "historical or undated", plain: "muted ink marks a historical or undated edge" },
      ],
      table_columns: TWIN_COLS,
      table_rows: [
        {
          counterparty: "Flock Safety",
          href: "/graphs/access/usa-ok/",
          relation: "configured access to",
          direction: "outbound",
          access_kind: "configured",
          date: "2024-01-15",
          date_kind: "single",
          currency: "current",
          support: "WEAKLY_SUPPORTED",
          sources: 1,
          evidence: ["claim-fixture-1"],
        },
        {
          counterparty: "Oklahoma County Sheriff",
          href: "/entity/agency/county-sheriff--e4f5g6h/",
          relation: "declared-policy access to",
          direction: "outbound",
          access_kind: "declared",
          date: "—",
          date_kind: "undated",
          currency: "aging",
          support: "WEAKLY_SUPPORTED",
          sources: 1,
          evidence: ["claim-fixture-2"],
        },
      ],
      node_count: 3,
      edge_count: 2,
      desc: { title: "Who can search this data", as_of_world: "2026-09-20", anchors: 2, counterparties: 1, edges: 2, drawn_edges: 2 },
      size_bytes: 2400,
      gzip_bytes: 900,
    },
    anchors_drawn: 2,
    counterparties_drawn: 1,
    edges_drawn: 2,
    cap_actions: [],
    toggle_kinds: ["configured", "declared", "observed"],
    table_rows_total: 2,
    table_href: `/graphs/access/${slug}/`,
    explore_href: `/explore/?v=2&overview=access&jurisdiction=fixture:${slug}`,
    anchor_attrs: {},
    degree_facts: [
      { count: 9, observed: "2024-03-01", sources: ["fixture-src"], claim_ids: ["claim-fixture-3"] },
    ],
    by_source: [{ source_id: "fixture-src", value: 2 }],
  };
}

function emptyNet(slot: string, figureId: string, overview: string, title: string, status: string, reason: string, slug: string): NetworkSlot {
  return {
    figure_id: figureId,
    slot,
    family: overview,
    overview,
    title,
    status,
    reason,
    anchors_total: status === "no_anchors" ? 0 : 2,
    edges_total: 0,
    degree_facts: [],
    table_href: `/graphs/${overview}/${slug}/`,
    explore_href: `/explore/?v=2&overview=${overview}&jurisdiction=fixture:${slug}`,
  } as NetworkSlot;
}

/** The emitted `networks[]` — drawn on usa/ok (the fixture's worked dossier)
 *  and typed absences everywhere else. `usa` (country) carries the
 *  country_no_figure state (K2 G-2). */
function buildNetworks(d: Dossier): NetworkSlot[] {
  const slug = d.slug;
  const country = (d.level ?? "") === "country" || slug === "usa" || slug === "can" || slug === "fra" || slug === "deu";
  if (country) {
    return [
      emptyNet("fig-2", "fig-supply", "supply", "Who runs and supplies it", "country_no_figure", "no node-link figure at the national level — the national relationship set reads as a count table, never a hairball (K2 G-2)", "usa"),
      emptyNet("fig-3", "fig-funding", "funding", "Who funds it", "country_no_figure", "no node-link figure at the national level — the national relationship set reads as a count table, never a hairball (K2 G-2)", "usa"),
      emptyNet("fig-4", "fig-access", "access", "Who can search this data", "country_no_figure", "no node-link figure at the national level — the national relationship set reads as a count table, never a hairball (K2 G-2)", "usa"),
      emptyNet("fig-5", "fig-policy", "governance", "Which rules apply", "country_no_figure", "no node-link figure at the national level — the national relationship set reads as a count table, never a hairball (K2 G-2)", "usa"),
    ];
  }
  if (slug === "usa/ok") {
    return [
      emptyNet("fig-2", "fig-supply", "supply", "Who runs and supplies it", "no_evidenced_edges", "entities are placed here but carry no recorded relationship of this kind in this release", slug),
      emptyNet("fig-3", "fig-funding", "funding", "Who funds it", "no_anchors", "SIG's release places no entity in this jurisdiction with a recorded relationship of this kind", slug),
      drawnAccess(slug),
      emptyNet("fig-5", "fig-policy", "governance", "Which rules apply", "no_anchors", "SIG's release places no entity in this jurisdiction with a recorded relationship of this kind", slug),
    ];
  }
  return [
    emptyNet("fig-2", "fig-supply", "supply", "Who runs and supplies it", "no_anchors", "SIG's release places no entity in this jurisdiction with a recorded relationship of this kind", slug),
    emptyNet("fig-3", "fig-funding", "funding", "Who funds it", "no_anchors", "SIG's release places no entity in this jurisdiction with a recorded relationship of this kind", slug),
    emptyNet("fig-4", "fig-access", "access", "Who can search this data", "no_anchors", "SIG's release places no entity in this jurisdiction with a recorded relationship of this kind", slug),
    emptyNet("fig-5", "fig-policy", "governance", "Which rules apply", "no_anchors", "SIG's release places no entity in this jurisdiction with a recorded relationship of this kind", slug),
  ];
}

function buildDoc(d: Dossier): DossierVisualsDoc {
  const jkey = d.jurisdiction_key ?? `fixture:${d.slug}`;
  const childRows = (d.children ?? []).map((c) => ({
    jkey: c.jkey,
    coverage: "rule_pending", // D-K1-4 verbatim — every child pending the rule
    drawn: true,
    href: c.page && c.slug_path ? `/dossier/${c.slug_path}/` : null,
  }));
  const counts = COUNTS[d.slug];
  const map: DossierVisualsDoc["map"] =
    d.slug === NO_BOUNDARY || counts === undefined
      ? {
          status: "no_boundary",
          reason:
            "the boundary pack mints no verified outline for this registry key — the figure is a typed absence, not a blank map",
          records_total: counts?.[0] ?? 66,
        }
      : { ...meta(d, counts, childRows), svg: fixtureSvg(d, counts[1], childRows) };
  const hasParent = Boolean(d.parent_jkey) || (d.jurisdiction_key === undefined && d.slug !== "usa");
  const locator: DossierVisualsDoc["locator"] = hasParent
    ? {
        parent_symbol: "loc-fixture-parent",
        parent_jkey: d.parent_jkey ?? "fixture:parent",
        child_d: blob(80 + (seedOf(d.slug) % 30), 50 + (seedOf(d.slug) % 16), 30, 20, seedOf(d.slug)),
        viewbox: [160, 101],
      }
    : { status: "no_parent_context", parent_jkey: null };
  return {
    schema: SCHEMA,
    release: { label: "fixture-build", publication_id: null, as_of_world: "2026-09-20" },
    jurisdiction: {
      jkey,
      slug_path: d.slug,
      level: d.level ?? "unkeyed",
      chain: (d.chain ?? []).map((c) => c.jkey),
      name: d.display_name ?? d.name ?? d.jurisdiction,
    },
    map,
    locator,
    networks: buildNetworks(d), // P37.28 (VIZ-01b) — drawn/typed entries.
    timeline_items: 0,
  };
}

/** The fixture `sig.dossier-visuals/1` corpus — slug path → doc. */
export const DOSSIER_VISUALS_FIXTURE: Record<string, DossierVisualsDoc> =
  Object.fromEntries(DOSSIERS.map((d) => [d.slug, buildDoc(d)]));

/** The fixture `sig.locator-symbols/1` sheet — one parent glyph for all fixture locators. */
export const LOCATOR_SYMBOLS_FIXTURE: LocatorSymbols = {
  index: Object.fromEntries(
    DOSSIERS.filter((d) => {
      const doc = DOSSIER_VISUALS_FIXTURE[d.slug];
      return doc && "parent_jkey" in doc.locator && doc.locator.parent_jkey;
    }).map((d) => {
      const doc = DOSSIER_VISUALS_FIXTURE[d.slug]!;
      const pj = "parent_jkey" in doc.locator ? doc.locator.parent_jkey : "fixture:parent";
      return [pj, { symbol: "loc-fixture-parent", viewbox: [160, 101] as [number, number] }];
    }),
  ),
  paths: { "loc-fixture-parent": PARENT_BLOB },
};

/**
 * The `figures[]` twin rows (sig.dossier/2 — metadata, never geometry) the
 * fixtures mint: the fig-map row whose caption + desc counts the page cites.
 */
export function fixtureFigureTwin(slug: string, _download: boolean): Dossier["figures"] {
  const doc = DOSSIER_VISUALS_FIXTURE[slug];
  if (!doc || !("desc" in doc.map)) return undefined;
  const m = doc.map;
  const nd = m.not_drawn;
  const nElsewhere = nd.located_elsewhere.reduce((n, r) => n + r.records, 0);
  const name = doc.jurisdiction.name;
  return [
    {
      figure_id: "fig-map",
      kind: "map",
      caption:
        `Where SIG's published records are in ${name}. ${m.desc.records_drawn} of ` +
        `${m.desc.records_total} published records drawn under the ${m.rule} rule ` +
        `(${m.mode}); ${nd.declared_no_point} have no published point, ` +
        `${nElsewhere} declared here are located elsewhere, ${nd.conflicting} withheld ` +
        `as conflicting coordinates, ${nd.tier3} at precision tier 3. Not a census — ` +
        `counts show what the named sources publish. Where SIG has looked: rule ` +
        `pending — hollow areas rest on one source.`,
      caption_drafted: "agent-drafted (K6 §5.1 template, labelled — VIZ-02 binds the copy)",
      meta: m,
      links: {
        sites: `/dossier/${slug}/sites/`,
        // The standalone SVG download ships only with a real release export —
        // fixtures emit no `web/figures/dossier/*.svg` bytes, so the fixture
        // twin names the file absent rather than linking a 404 (link-crawl).
        download: null,
      },
    },
  ];
}
