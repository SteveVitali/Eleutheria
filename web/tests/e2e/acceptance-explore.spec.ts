// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.64 (R11-K13-ACC-EXPLORE — the K2 GX-10 / K6 VIZ-05 merge): the
// entity/graph/dossier-figure acceptance battery, emitted-route half. Two
// requirement families are swept over the BUILT site (never a hand list,
// SIG-ENG-042 — a vacuous pass fails too):
//
//   * SIG-UI-D20 (UXR-03): no UUID, connector key or registry id renders as
//     visible text in h1–h3, a, td, li or SVG text outside an Identifiers /
//     cite / figure-evidence block — every mention is a link or a typed
//     absence. The same rule binds the overview graphs' resolved `l` label
//     fields (`/graph/<ov>/<compartment>.json`).
//   * SIG-UI-DV01…DV12 (K6 §12): the dossier-figure contract over every
//     emitted dossier page — the drawn map figure (or the typed absence),
//     the binning mode, the ≤40-node linked network figure with
//     JS-off-togglable access kinds, the explore-bar/scoped-search
//     jurisdiction facets, zero T2 bytes before activation, the inline
//     figure size cap, the print figure pages, figure accessibility, the
//     records-side parity chain (figure = twin = rollup = children Σ +
//     placed-only-here = caption decomposition), the single legend lexicon,
//     and the restricted-input posture.
//
// The interactive half — the J-1…J-6 and VJ-1…VJ-6 labelled agent
// walkthroughs, axe in interaction states, and the activated-map box —
// lives in acceptance-explore-journeys.spec.ts. What the fixture corpus
// cannot settle is recorded in the committed acceptance packet, never
// silently skipped.

import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { gzipSync } from "node:zlib";
import {
  DIST_DIR,
  REPO_ROOT,
  emittedRoutes,
  parseFigureRegions,
  visibleTextMinusIdSpans,
} from "./acceptance";

// ---------------------------------------------------------------------------
// The emitted route corpus, once.
// ---------------------------------------------------------------------------

interface PageRec {
  route: string;
  html: string;
  component: string;
}

const PAGE_TYPES = JSON.parse(
  readFileSync(join(DIST_DIR, "page-types.json"), "utf-8"),
) as { dataSource: string; routes: { path: string; component: string }[] };
const componentOf = new Map(PAGE_TYPES.routes.map((r) => [r.path, r.component]));

const PAGES: PageRec[] = [];
for (const route of emittedRoutes()) {
  if (!route.endsWith("/")) continue;
  let html: string;
  try {
    html = readFileSync(join(DIST_DIR, route.slice(1), "index.html"), "utf-8");
  } catch {
    continue;
  }
  PAGES.push({ route, html, component: componentOf.get(route) ?? "" });
}

const byComponent = (component: string): PageRec[] =>
  PAGES.filter((p) => p.component === component);

// The place-dossier set: the dossier template also emits the slug-history
// redirect stubs (`/dossier/bd/` "Corrected", `/dossier/id/` "Split",
// `/dossier/unresolved/` "Moved") and the `/dossier/unplaced/` data-quality
// report — none of which is a place dossier. The discriminator is the
// twin: a place dossier carries its row in `web/dossiers.json`.
const DOSSIER_DOCS_EARLY = JSON.parse(
  readFileSync(join(DIST_DIR, "artifact/web/dossiers.json"), "utf-8"),
) as Record<string, unknown>[];
const TWIN_SLUGS = new Set(
  DOSSIER_DOCS_EARLY.map((d) => String(d.slug_path ?? d.slug)),
);
const DOSSIERS = byComponent("pages/dossier/[...path].astro").filter((p) =>
  TWIN_SLUGS.has(p.route.replace(/^\/dossier\//, "").replace(/\/$/, "")),
);
const PRINTS = byComponent("pages/dossier/[...path]/print.astro");

const num = (s: string | null): number => (s === null ? NaN : Number(s));

// ---------------------------------------------------------------------------
// SIG-UI-D20 — the legible-identifier crawl.
// ---------------------------------------------------------------------------

const UUID_RE = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi;
// The K2 §8 key pattern `^[a-z_]+:[^ ]+:` — registry keys carry two colons
// (`sig:agency:…`, `cap:portal:1`); one-colon place keys (`iso3166-2:US-OK`,
// `us.census.geoid.county:40109`, `fixture:usa/ok`) fail the leading
// [a-z_]+ class by their digits/dots and stay lawful prose.
const KEY_RE = /\b[a-z_][a-z0-9_]*:[A-Za-z0-9_.-]+:[A-Za-z0-9_.:-]+/g;

test.describe("SIG-UI-D20 — no identifier leaks as visible text (UXR-03)", () => {
  test("every emitted page renders 0 UUID/key patterns outside id blocks", () => {
    const failures: string[] = [];
    for (const p of PAGES) {
      const text = visibleTextMinusIdSpans(p.html);
      for (const m of text.matchAll(UUID_RE)) {
        failures.push(`${p.route}: UUID "${m[0]}" as visible text`);
      }
      for (const m of text.matchAll(KEY_RE)) {
        failures.push(`${p.route}: key "${m[0]}" as visible text`);
      }
    }
    expect(failures, failures.join("\n")).toEqual([]);
  });

  test("every graph overview doc's `l` labels resolve to legible labels", () => {
    const docs: { file: string; doc: Record<string, unknown> }[] = [];
    for (const route of emittedRoutes()) {
      const m = /^\/graph\/([a-z-]+)\/([a-z_]+)\.json$/.exec(route);
      if (!m) continue;
      docs.push({
        file: route,
        doc: JSON.parse(readFileSync(join(DIST_DIR, route.slice(1)), "utf-8")),
      });
    }
    expect(docs.length, "no overview docs — vacuous sweep").toBeGreaterThan(0);
    const failures: string[] = [];
    for (const { file, doc } of docs) {
      const dict = (doc.dict ?? {}) as Record<string, unknown>;
      const labels = Array.isArray(dict.labels) ? (dict.labels as string[]) : null;
      if (!labels || labels.length === 0) {
        failures.push(`${file}: dict.labels missing/empty — nodes cannot be named`);
        continue;
      }
      for (const label of labels) {
        if (UUID_RE.test(label) || KEY_RE.test(label) || !label.trim()) {
          failures.push(`${file}: dict label "${label}" is a key, not a label`);
        }
      }
      const nodes = (doc.nodes ?? {}) as Record<string, unknown>;
      const idx = Array.isArray(nodes.l) ? (nodes.l as number[]) : [];
      for (const i of idx) {
        if (!(i >= 0 && i < labels.length)) {
          failures.push(`${file}: nodes.l=${i} outside dict.labels (${labels.length})`);
        }
      }
    }
    expect(failures, failures.join("\n")).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// The dossier twin corpus (dossiers.json) for the parity legs.
// ---------------------------------------------------------------------------

const DOSSIER_DOCS = JSON.parse(
  readFileSync(join(DIST_DIR, "artifact/web/dossiers.json"), "utf-8"),
) as Record<string, unknown>[];
const twinBySlug = new Map<string, Record<string, unknown>>();
for (const doc of DOSSIER_DOCS) {
  twinBySlug.set(String(doc.slug_path ?? doc.slug), doc);
}

const figMapDesc = (doc: Record<string, unknown>): Record<string, unknown> | null => {
  const figs = (doc.figures ?? []) as Record<string, unknown>[];
  const fm = figs.find((f) => f.figure_id === "fig-map");
  const desc = (fm?.meta as Record<string, unknown> | undefined)?.desc;
  return (desc ?? null) as Record<string, unknown> | null;
};

/** The caption's drawn/not-drawn decomposition, parsed verbatim. */
function captionCounts(html: string): {
  drawn: number;
  total: number;
  noPoint: number;
  elsewhere: number;
  conflicting: number;
  tier3: number;
} | null {
  const m = /(\d+) of (\d+) published records drawn[^;]*; (\d+) have no published point, (\d+) declared here are located elsewhere, (\d+) withheld as conflicting coordinates, (\d+) at precision tier 3/.exec(
    html,
  );
  if (!m) return null;
  return {
    drawn: Number(m[1]),
    total: Number(m[2]),
    noPoint: Number(m[3]),
    elsewhere: Number(m[4]),
    conflicting: Number(m[5]),
    tier3: Number(m[6]),
  };
}

test.describe("SIG-UI-DV01 — every dossier carries the map figure or its typed absence", () => {
  test("each dossier page draws fig-map + caption contract or the typed absence", () => {
    expect(DOSSIERS.length, "no dossier pages — vacuous sweep").toBeGreaterThan(0);
    const failures: string[] = [];
    for (const p of DOSSIERS) {
      const drawn = /data-testid="fig1-static"><svg/.test(p.html);
      const empty = p.html.includes('data-testid="empty-state"');
      if (!drawn && !empty) {
        failures.push(`${p.route}: neither fig-map nor a typed absence`);
        continue;
      }
      if (!drawn) continue;
      const cap = /data-testid="fig1-caption"[\s\S]*?<\/figcaption>/.exec(p.html);
      if (!cap) {
        failures.push(`${p.route}: drawn figure without fig1-caption`);
        continue;
      }
      for (const need of ["release", "not a census", "licence", "published records"]) {
        if (!cap[0].toLowerCase().includes(need)) {
          failures.push(`${p.route}: caption missing "${need}"`);
        }
      }
      // DV01: "a place-level table with equal counts MUST follow" — the
      // child-jurisdiction rollup block carries per-place record figures.
      // A leaf dossier (no children in the twin) has no table to follow.
      const slug = p.route.replace(/^\/dossier\//, "").replace(/\/$/, "");
      const twin = twinBySlug.get(slug);
      const children = ((twin?.children ?? []) as unknown[]).length;
      if (
        children > 0 &&
        !p.html.includes('data-testid="dossier-children"') &&
        !p.html.includes('data-testid="dossier-rollup"')
      ) {
        failures.push(`${p.route}: no place-level table/rollup block follows the figure`);
      }
    }
    expect(failures, failures.join("\n")).toEqual([]);
  });
});

test.describe("SIG-UI-DV10 — the figure's counts equal the dossier's record chain", () => {
  test("fig-map value = twin desc.records_total = rollup.records; caption decomposes", () => {
    const failures: string[] = [];
    let drawnCount = 0;
    for (const p of DOSSIERS) {
      if (!/data-testid="fig1-static"><svg/.test(p.html)) continue;
      drawnCount += 1;
      const slug = p.route.replace(/^\/dossier\//, "").replace(/\/$/, "");
      const twin = twinBySlug.get(slug);
      const figures = parseFigureRegions(p.html, p.route);
      const mapTotal = figures.find((f) => f.id === "map-total");
      if (!twin) {
        failures.push(`${p.route}: no twin doc for slug ${slug}`);
        continue;
      }
      if (!mapTotal) {
        failures.push(`${p.route}: no map-total figure region`);
        continue;
      }
      const desc = figMapDesc(twin);
      if (!desc) {
        failures.push(`${p.route}: twin carries no figures[fig-map].meta.desc`);
        continue;
      }
      const declared = num(mapTotal.value);
      if (declared !== Number(desc.records_total)) {
        failures.push(
          `${p.route}: figure value ${declared} ≠ twin desc.records_total ${desc.records_total}`,
        );
      }
      const rollup = (twin.rollup ?? null) as Record<string, unknown> | null;
      if (rollup && rollup.records !== undefined) {
        if (Number(rollup.records) !== declared) {
          failures.push(
            `${p.route}: figure value ${declared} ≠ rollup.records ${rollup.records}`,
          );
        }
        // Σ place-table + placed_only_here conservation — the DV01
        // "equal counts" the place-level table must carry.
        const children = (twin.children ?? []) as Record<string, unknown>[];
        const sum =
          children.reduce((a, c) => a + Number(c.records ?? 0), 0) +
          Number(rollup.records_placed_only_here ?? 0);
        if (sum !== declared) {
          failures.push(
            `${p.route}: childrenΣ+placed_only_here ${sum} ≠ figure ${declared}`,
          );
        }
        if (rollup.conserved !== true) {
          failures.push(`${p.route}: rollup.conserved is not true`);
        }
      }
      const cap = captionCounts(p.html);
      if (!cap) {
        failures.push(`${p.route}: caption decomposition did not parse`);
        continue;
      }
      if (cap.total !== declared) {
        failures.push(`${p.route}: caption total ${cap.total} ≠ figure ${declared}`);
      }
      if (cap.drawn + cap.noPoint + cap.elsewhere + cap.conflicting + cap.tier3 !== cap.total) {
        failures.push(
          `${p.route}: caption parts ${cap.drawn}+${cap.noPoint}+${cap.elsewhere}+` +
            `${cap.conflicting}+${cap.tier3} ≠ total ${cap.total}`,
        );
      }
      if (Number(desc.records_drawn) !== cap.drawn) {
        failures.push(
          `${p.route}: caption drawn ${cap.drawn} ≠ twin desc.records_drawn ${desc.records_drawn}`,
        );
      }
      // map-recon's figure value is the DRAWN count (the reconciliation
      // sentence's subject), not the total.
      const recon = figures.find((f) => f.id === "map-recon");
      if (!recon || num(recon.value) !== cap.drawn) {
        failures.push(`${p.route}: map-recon figure missing or disagrees (${recon?.value} ≠ ${cap.drawn})`);
      }
    }
    expect(drawnCount, "no drawn map figures — vacuous parity sweep").toBeGreaterThan(0);
    expect(failures, failures.join("\n")).toEqual([]);
  });

  test("every map-embed doc is self-consistent (records = pointCount)", () => {
    const failures: string[] = [];
    let count = 0;
    for (const route of emittedRoutes()) {
      const m = /^\/dossier\/(.+)\/map-embed\.json$/.exec(route);
      if (!m) continue;
      count += 1;
      const doc = JSON.parse(readFileSync(join(DIST_DIR, route.slice(1)), "utf-8"));
      if (doc.schema !== "sig.dossier-map-embed/1") {
        failures.push(`${route}: schema ${doc.schema}`);
      }
      if (doc.pointCount !== (doc.records as unknown[]).length) {
        failures.push(`${route}: pointCount ${doc.pointCount} ≠ records ${doc.records.length}`);
      }
      if (typeof doc.unplotted !== "number" || doc.unplotted < 0) {
        failures.push(`${route}: unplotted ${doc.unplotted}`);
      }
      // DV12 posture on the embed payload itself: the records carry
      // published-point coordinates only — never a data-n / per-area key.
      for (const rec of doc.records as Record<string, unknown>[]) {
        for (const k of Object.keys(rec)) {
          if (/^data[-_]/i.test(k) || /^n$/i.test(k)) {
            failures.push(`${route}: record carries numeric-key field "${k}"`);
          }
        }
      }
    }
    expect(count, "no map-embed docs — vacuous sweep").toBeGreaterThan(0);
    expect(failures, failures.join("\n")).toEqual([]);
  });
});

test.describe("SIG-UI-DV02 — the drawn binning mode agrees with its elements", () => {
  test("h3-areas figures draw areas; points figures draw points — never mixed", () => {
    const failures: string[] = [];
    for (const p of DOSSIERS) {
      const m = /rule \((points|h3-areas)\)/.exec(p.html);
      if (!m) continue;
      const areas = (p.html.match(/class="[^"]*sig-fig-area/g) ?? []).length;
      const points = (p.html.match(/class="[^"]*sig-fig-point/g) ?? []).length;
      if (m[1] === "h3-areas" && (areas === 0 || points > 0)) {
        failures.push(`${p.route}: declared h3-areas but areas=${areas} points=${points}`);
      }
      if (m[1] === "points" && (points === 0 || areas > 0)) {
        failures.push(`${p.route}: declared points but points=${points} areas=${areas}`);
      }
    }
    expect(failures, failures.join("\n")).toEqual([]);
  });
});

test.describe("SIG-UI-DV03 — the network figure's contract", () => {
  test("drawn figures: ≤40 linked nodes, kind classes + toggles, table-twin parity, no ranking", () => {
    const failures: string[] = [];
    let drawn = 0;
    let empty = 0;
    for (const p of DOSSIERS) {
      const slot = /data-testid="network-figure-slot"[\s\S]*?<\/section>/.exec(p.html);
      if (!slot) continue;
      const hasFigure = slot[0].includes('data-testid="network-figure"');
      if (!hasFigure) {
        empty += 1;
        if (/<svg\b/.test(slot[0])) {
          failures.push(`${p.route}: svg inside an undrawn network slot`);
        }
        continue;
      }
      drawn += 1;
      const wide = /data-testid="network-figure-wide">([\s\S]*?)<\/svg>/.exec(slot[0]);
      if (!wide) {
        failures.push(`${p.route}: drawn slot without the wide svg`);
        continue;
      }
      const svg = wide[1];
      const nodes = (svg.match(/class="[^"]*sig-fig-node[\s"]/g) ?? []).length;
      if (nodes > 40) failures.push(`${p.route}: ${nodes} > 40 drawn nodes`);
      // Every drawn node sits inside an <a> — UXR-03/DV03 "every node links".
      const linkedNodes = (svg.match(/<a href="[^"]+">[\s\S]*?sig-fig-node/g) ?? []).length;
      const nodeMarks = (svg.match(/class="sig-fig-node /g) ?? []).length;
      if (linkedNodes !== nodeMarks) {
        failures.push(`${p.route}: ${nodeMarks - linkedNodes} unlinked node marks`);
      }
      for (const kind of ["configured", "declared", "observed"]) {
        if (!svg.includes(`sig-fig-edge-acc-${kind}`)) {
          failures.push(`${p.route}: no sig-fig-edge-acc-${kind} mark`);
        }
      }
      // The JS-off toggles name each access kind.
      for (const t of ["k-configured", "k-declared", "k-observed", "k-historical"]) {
        if (!slot[0].includes(`id="${t}"`)) {
          failures.push(`${p.route}: toggle ${t} missing`);
        }
      }
      if (/\b(top|most)\b/i.test(svg.replace(/<[^>]+>/g, " "))) {
        failures.push(`${p.route}: ranking copy inside the figure`);
      }
      // Table-twin parity — one table row per drawn edge, the H-2 fields
      // named in the header.
      const twin = /data-testid="network-table-twin">([\s\S]*?)<\/details>/.exec(slot[0]);
      if (!twin) {
        failures.push(`${p.route}: drawn figure without the table twin`);
        continue;
      }
      const rows = (twin[1].match(/<tr\b/g) ?? []).length - 1; // minus header
      const edges = (svg.match(/class="sig-fig-edge[\s"]/g) ?? []).length;
      if (rows !== edges) {
        failures.push(`${p.route}: table rows ${rows} ≠ drawn edges ${edges}`);
      }
      for (const h of ["relation", "date", "currency", "support", "sources"]) {
        if (!twin[1].includes(`>${h}<`)) {
          failures.push(`${p.route}: table twin missing H-2 field "${h}"`);
        }
      }
    }
    expect(drawn + empty, "no network slots — vacuous sweep").toBeGreaterThan(0);
    expect(failures, failures.join("\n")).toEqual([]);
  });
});

test.describe("SIG-UI-DV04/DV06 — the dossier's facets travel", () => {
  test("every dossier carries the explore bar + scoped GET search for its jurisdiction", () => {
    const failures: string[] = [];
    for (const p of DOSSIERS) {
      for (const id of ["explore-map", "explore-network", "explore-search"]) {
        const m = new RegExp(
          `data-testid="${id}"[^>]*href="([^"]+)"|href="([^"]+)"[^>]*data-testid="${id}"`,
        ).exec(p.html);
        const href = m ? (m[1] ?? m[2]) : null;
        if (!href) {
          failures.push(`${p.route}: explore-bar link ${id} missing`);
          continue;
        }
        if (!/[?&]v=2/.test(href)) {
          failures.push(`${p.route}: ${id} href "${href}" is not workspace-state v2`);
        }
      }
      // A KEYED dossier (the twin names a registry jurisdiction_key) MUST
      // scope the bar's links and carry the hidden scope input; an
      // unkeyed dossier has no key to pass — its links submit unscoped,
      // so no facet is claimed and nothing is misrepresented.
      const slug = p.route.replace(/^\/dossier\//, "").replace(/\/$/, "");
      const keyed = Boolean(twinBySlug.get(slug)?.jurisdiction_key);
      if (keyed) {
        for (const m of p.html.matchAll(/href="([^"]+)"[^>]*data-testid="(explore-[^"]+)"|data-testid="(explore-[^"]+)"[^>]*href="([^"]+)"/g)) {
          const href = m[1] ?? m[4];
          if (href && !/jurisdiction=/.test(href)) {
            failures.push(`${p.route}: keyed dossier's ${m[2] ?? m[3]} href carries no jurisdiction=`);
          }
        }
      }
      const formTag = /<form\b[^>]*data-testid="dossier-scoped-search-form"[^>]*>/.exec(
        p.html,
      );
      if (!formTag) {
        failures.push(`${p.route}: no scoped GET search form`);
        continue;
      }
      if (!/method="get"/i.test(formTag[0])) {
        failures.push(`${p.route}: scoped search is not a GET form`);
      }
      const action = /action="([^"]+)"/.exec(formTag[0]);
      if (!action || !/releases\/.+\/search/.test(action[1])) {
        failures.push(`${p.route}: scoped search action "${action?.[1]}" is not release-pinned`);
      }
      if (keyed) {
        const scopeTag = /<input\b[^>]*data-testid="dossier-scoped-search-scope"[^>]*>/.exec(
          p.html,
        );
        const scopeVal = scopeTag ? /value="([^"]+)"/.exec(scopeTag[0]) : null;
        if (!scopeVal || !scopeVal[1]) {
          failures.push(`${p.route}: no hidden jurisdiction scope input`);
        }
      }
    }
    expect(failures, failures.join("\n")).toEqual([]);
  });
});

test.describe("SIG-UI-DV05 — zero T2 payload before an explicit action", () => {
  test("no dossier page loads island/app code; only allow-listed kit modules", () => {
    const failures: string[] = [];
    for (const p of DOSSIERS) {
      if (/<script[^>]+src="\/_astro\//.test(p.html)) {
        failures.push(`${p.route}: an /_astro/ island chunk ships with the page`);
      }
      for (const m of p.html.matchAll(/<script[^>]+src="([^"]+)"/g)) {
        if (!m[1].startsWith("/_kit/sig-")) {
          failures.push(`${p.route}: non-kit script "${m[1]}"`);
        }
      }
      if (/"sig-map-embed"|MapIsland|MapApp/.test(p.html.replace(/\/_astro\/[^"]+/, ""))) {
        if (p.html.includes('class="map-island')) {
          failures.push(`${p.route}: a map island mount ships with the page`);
        }
      }
    }
    expect(failures, failures.join("\n")).toEqual([]);
  });
});

test.describe("SIG-UI-DV07 — the inline figure's size cap", () => {
  test("every emitted fig1 static svg is ≤60 elements and ≤30 KiB gzip", () => {
    const failures: string[] = [];
    let count = 0;
    for (const p of DOSSIERS) {
      const m = /data-testid="fig1-static">([\s\S]*?<\/svg>)/.exec(p.html);
      if (!m) continue;
      count += 1;
      const elements = (m[1].match(/<(path|circle|rect|line|ellipse|polygon|text|g|a|title|desc)\b/g) ?? [])
        .length;
      const gz = gzipSync(Buffer.from(m[1], "utf-8")).length;
      if (elements > 60) failures.push(`${p.route}: ${elements} svg elements > 60`);
      if (gz > 30 * 1024) failures.push(`${p.route}: ${gz} gzip bytes > 30 KiB`);
    }
    expect(count, "no drawn fig1 svgs — vacuous sweep").toBeGreaterThan(0);
    expect(failures, failures.join("\n")).toEqual([]);
  });
});

test.describe("SIG-UI-DV08 — the print form carries every figure", () => {
  test("every print route: brief first, terms last, figure pages carry the static rendition", () => {
    const failures: string[] = [];
    for (const p of PRINTS) {
      if (/<script\b/.test(p.html)) failures.push(`${p.route}: a script ships on the T0 print page`);
      if (/sig-activate|<canvas\b/.test(p.html)) {
        failures.push(`${p.route}: a control/canvas ships on the print page`);
      }
      const kinds = [...p.html.matchAll(/data-page-kind="([^"]+)"/g)].map((m) => m[1]);
      if (kinds[0] !== "brief") failures.push(`${p.route}: first print page is ${kinds[0]}, not brief`);
      if (kinds[kinds.length - 1] !== "terms") {
        failures.push(`${p.route}: last print page is ${kinds[kinds.length - 1]}, not terms`);
      }
      const pages = p.html.split(/<div class="sig-print-page"/).slice(1);
      for (const [i, seg] of pages.entries()) {
        if (!seg.includes('data-testid="print-runhead"')) {
          failures.push(`${p.route}: print page ${i + 1} has no running head`);
        }
        if (!seg.includes('data-testid="print-footer"')) {
          failures.push(`${p.route}: print page ${i + 1} has no footer`);
        }
        if (!/permalink|sig-print-permalink|print-permalink/.test(seg)) {
          failures.push(`${p.route}: print page ${i + 1} carries no permalink`);
        }
      }
      // Every figure page carries its caption + as-of + permalink.
      for (const m of p.html.matchAll(/data-testid="print-figure"[\s\S]*?<\/figure>/g)) {
        if (!/sig-print-figure__asof|As of world/.test(m[0])) {
          failures.push(`${p.route}: a print figure carries no as-of`);
        }
        if (!/sig-print-figure__permalink/.test(m[0])) {
          failures.push(`${p.route}: a print figure carries no permalink`);
        }
        if (m[0].includes('data-figure-kind="map"') && !/<svg\b/.test(m[0])) {
          failures.push(`${p.route}: the map figure page has no static rendition`);
        }
      }
    }
    expect(failures, failures.join("\n")).toEqual([]);
  });

  test("a dossier whose page draws fig-map prints the map on page 2 (DV08)", () => {
    const failures: string[] = [];
    for (const p of PRINTS) {
      const slug = p.route.replace(/^\/dossier\//, "").replace(/\/print\/$/, "");
      const twin = twinBySlug.get(slug);
      const drawn = twin ? figMapDesc(twin) !== null : false;
      if (!drawn) continue;
      const figPages = [
        ...p.html.matchAll(/data-testid="print-figure" data-figure-kind="([^"]+)"|data-figure-kind="([^"]+)" data-testid="print-figure"/g),
      ].map((m) => m[1] ?? m[2]);
      if (figPages[0] !== "map") {
        failures.push(`${p.route}: drawn fig-map but no leading map print page (kinds: ${figPages})`);
      }
      // the figure page sits immediately after the brief — the map leads page 2.
      const order = [...p.html.matchAll(/data-page-kind="([^"]+)"/g)].map((m) => m[1]);
      if (order[1] !== "figures") {
        failures.push(`${p.route}: page 2 is ${order[1]}, not the figure page`);
      }
    }
    expect(failures, failures.join("\n")).toEqual([]);
  });
});

test.describe("SIG-UI-DV09 — figure accessibility structure", () => {
  test("every drawn network figure has the skip link, an accessible svg and a labelled twin", () => {
    const failures: string[] = [];
    for (const p of DOSSIERS) {
      if (!p.html.includes('data-testid="network-figure"')) continue;
      if (!/sig-net-skip/.test(p.html)) {
        failures.push(`${p.route}: no skip link ahead of the network figure`);
      }
      const m = /data-testid="network-figure-wide"><svg[^>]*(role|aria-label)[^>]*>/.exec(p.html);
      if (!m || !/role="(img|group)"/.test(m[0]) || !/aria-label="[^"]+"/.test(m[0])) {
        failures.push(`${p.route}: network svg lacks role + aria-label`);
      }
      if (!/<table\b/.test(p.html)) {
        failures.push(`${p.route}: no table twin follows the figure`);
      }
    }
    expect(failures, failures.join("\n")).toEqual([]);
  });
});

test.describe("SIG-UI-DV11 — one legend lexicon", () => {
  const VOCAB = new Set<string>();
  {
    const src = readFileSync(
      join(REPO_ROOT, "exports/src/exports/figures/lexicon.py"),
      "utf-8",
    );
    const block = /FIGURE_CLASSES = \(\n([\s\S]*?)\n\)/.exec(src);
    for (const m of (block?.[1] ?? "").matchAll(/"(sig-fig[a-z0-9-]*)"/g)) {
      VOCAB.add(m[1]);
    }
    expect(VOCAB.size, "lexicon vocabulary empty — the mirror moved").toBeGreaterThan(20);
  }
  test("every figure-SVG sig-fig-* class is a lexicon class; every drawn edge kind is named in the legend", () => {
    const emitted = new Set<string>();
    const failures: string[] = [];
    // The lexicon binds the marks INSIDE figure SVGs — component/layout
    // classes (sig-fig-net, sig-fig-links, sig-figure, …) sit outside the
    // svg and are styled by their own rules, not the figure vocabulary.
    for (const p of PAGES) {
      for (const svg of p.html.matchAll(/<svg[\s\S]*?<\/svg>/g)) {
        for (const m of svg[0].matchAll(/class="([^"]+)"/g)) {
          for (const cls of m[1].split(/\s+/)) {
            // sig-fig-* symbols only — `sig-figure`/`sig-figure-frame` are
            // the J3 <Figure> component's own classes, not figure marks.
            if (/^sig-fig(-|$)/.test(cls) && cls !== "sig-figure" && !cls.startsWith("sig-figure")) {
              emitted.add(cls);
            }
          }
        }
      }
    }
    for (const cls of emitted) {
      if (!VOCAB.has(cls)) failures.push(`emitted class "${cls}" is not a lexicon class`);
    }
    // A drawn edge kind must carry its legend meaning on the same page.
    for (const p of DOSSIERS) {
      if (!p.html.includes('data-testid="network-figure"')) continue;
      const legend = /data-testid="network-figure-legend">([\s\S]*?)<\/ul>/.exec(p.html);
      if (!legend) {
        failures.push(`${p.route}: drawn network figure without a legend`);
        continue;
      }
      for (const m of p.html.matchAll(/sig-fig-edge-acc-([a-z]+)/g)) {
        if (!legend[1].includes(m[1])) {
          failures.push(`${p.route}: edge kind "${m[1]}" drawn but not named in the legend`);
        }
      }
      if (/sig-fig-edge-muted/.test(p.html) && !/muted|historical|undated/.test(legend[1])) {
        failures.push(`${p.route}: muted edges drawn; the legend never names the channel`);
      }
    }
    expect(failures, failures.join("\n")).toEqual([]);
  });
});

test.describe("SIG-UI-DV12 — restricted-input posture", () => {
  test("figures carry no per-area numeric data; the visuals input ships nothing", () => {
    const failures: string[] = [];
    for (const p of DOSSIERS) {
      // Per-area marks may not carry data attributes or titles — the kit
      // emits exactly one svg-level <title> + <desc>; a second <title> is a
      // per-mark leak.
      for (const m of p.html.matchAll(/<svg[\s\S]*?<\/svg>/g)) {
        const titles = (m[0].match(/<title>/g) ?? []).length;
        if (titles > 1) {
          failures.push(`${p.route}: ${titles} <title> elements in one svg — a per-mark leak`);
        }
        for (const mark of m[0].matchAll(/<(path|circle|rect)[^>]*\sdata-[^>]*>/g)) {
          failures.push(`${p.route}: a figure mark carries a data-* attribute: ${mark[0].slice(0, 120)}`);
        }
        for (const mark of m[0].matchAll(/<(path|circle|rect|text)[^>]*>([\s\S]*?)<title>/g)) {
          failures.push(`${p.route}: a per-mark <title> leaks data near ${mark[0].slice(0, 80)}`);
        }
      }
    }
    for (const route of emittedRoutes()) {
      if (/dossier-visuals|dossier_visuals|\/inputs\//.test(route)) {
        failures.push(`restricted input ships at ${route}`);
      }
    }
    expect(failures, failures.join("\n")).toEqual([]);
  });
});
