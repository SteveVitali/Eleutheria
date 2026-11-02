// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P35.50 (UXK0-1, K0 NEW-4, SIG-UI-041): the e2e/axe sweeps iterate the
// DISCOVERED route set — every route the build emitted, classified by
// src/lib/page-types.ts — never a hand-maintained list. The build hook writes
// `dist/page-types.json` (`sig.page-types-manifest/1`); this module reads that
// manifest, so the sweeps can never drift from the built site the preview
// server serves. A missing manifest fails loud: `npm run check` builds before
// `test:e2e`, and a bare `npx playwright test` against an older dist still
// iterates the routes that dist actually carries.
//
// Semantic subsets (SHELL_PAGES, CHROME_PAGES, FRESHNESS_SORT_PAGES, …) are
// DERIVED from the manifest's `type` and `chrome` fields — a new route lands
// in the right sweeps by classification, and the "staging-verified" AC of the
// contract is the discovered-vs-hand-list count recorded in the run ledger.

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import type { Page, Response } from "@playwright/test";

export type PageType = "T0" | "T1" | "T2" | "T3";

export interface DiscoveredRoute {
  path: string;
  file: string;
  type: PageType;
  pattern: string;
  owner: string;
  contract: string;
  chrome: string;
  internal: boolean;
}

interface PageTypesManifest {
  schema: string;
  routes: DiscoveredRoute[];
}

const MANIFEST_URL = new URL("../../dist/page-types.json", import.meta.url);

function loadManifest(): PageTypesManifest {
  let raw: string;
  try {
    raw = readFileSync(fileURLToPath(MANIFEST_URL), "utf-8");
  } catch {
    throw new Error(
      `pages.ts: ${fileURLToPath(MANIFEST_URL)} is missing — the e2e suite iterates the discovered routes of the BUILT site; run \`npm run build\` first (the playwright webServer does it for you)`,
    );
  }
  const manifest = JSON.parse(raw) as PageTypesManifest;
  if (manifest.schema !== "sig.page-types-manifest/1") {
    throw new Error(
      `pages.ts: dist/page-types.json schema ${manifest.schema} — expected sig.page-types-manifest/1 (stale dist? rebuild)`,
    );
  }
  return manifest;
}

const MANIFEST = loadManifest();

/** Every built HTML route, classified — the sweep source of truth. */
export const DISCOVERED_ROUTES: readonly DiscoveredRoute[] = MANIFEST.routes;

const pathsOf = (pred: (r: DiscoveredRoute) => boolean): string[] =>
  DISCOVERED_ROUTES.filter(pred).map((r) => r.path);

const typeIs = (t: PageType) => (r: DiscoveredRoute) => r.type === t;

/** Routes by declared page type (the registry's T0/T1/T2/T3 classes). */
export const T0_PAGES = pathsOf(typeIs("T0"));
export const T1_PAGES = pathsOf(typeIs("T1"));
export const T2_PAGES = pathsOf(typeIs("T2"));
export const T3_PAGES = pathsOf(typeIs("T3"));
export const PAGES_BY_TYPE: Readonly<Record<PageType, readonly string[]>> = {
  T0: T0_PAGES,
  T1: T1_PAGES,
  T2: T2_PAGES,
  T3: T3_PAGES,
};

// ---------------------------------------------------------------------------
// Derived sweep lists — every one is computed from the discovered set.
// ---------------------------------------------------------------------------

// The standard shell-layout pages: full chrome (nav + the citation affordance,
// SIG-UI-035), regardless of page type — T0 dispute/chrome pages, T1 content,
// T2 explore pages all carry it. The print pages (chrome="print") are
// standalone documents and the internal routes stay distinguishable via
// `internal` on DISCOVERED_ROUTES.
export const SHELL_PAGES = pathsOf((r) => r.chrome === "full");
export const ALL_PAGES = SHELL_PAGES;

// The chrome-light pages (minimal chrome, noindex): branded error pages and
// the /terms forwarder.
export const CHROME_PAGES = pathsOf((r) => r.chrome === "minimal");

// The standalone print documents (T0, paginated layout).
export const PRINT_PAGES = pathsOf((r) => r.chrome === "print");

// The authenticated curation surface (ADR-068) — every discovered T3 route.
export const CURATE_PAGES = T3_PAGES;
// The compare page id is URL-encoded (the item_id carries ':' and '~').
export const CURATE_COMPARE_PAGE = "/curate/er_match%3Aagency%3Aokcpd~agency%3Aokc-pd/";

// The T2 explore surfaces — the pages that ship island scripts today.
export const ISLAND_PAGES = T2_PAGES;

// The full a11y surface for the axe sweep: EVERY discovered route (K0 §4.12 —
// axe on every discovered route; SIG-UI-037 WCAG 2.2 AA everywhere, incl. the
// T0 print/tombstone pages and the T3 curation pages P21.6 already swept).
export const A11Y_PAGES = pathsOf(() => true);

// The data-freshness table's pre-rendered static sort routes (P27.7): every
// discovered route under /data-freshness/ that is not the index itself —
// sorting is a plain GET to a distinct page, so each emitted sort route must
// meet WCAG 2.2 AA like the base page.
export const FRESHNESS_SORT_PAGES = pathsOf(
  (r) => r.path.startsWith("/data-freshness/") && r.path !== "/data-freshness/",
);

// The jurisdiction-conditional dossiers (localised, public-employee name
// withheld — SIG-PUB-017, §44): every discovered non-print dossier route that
// is not the index, the honest unplaced report, or the worked OKC dossier.
export const DOSSIER_SLUG = "oklahoma-city";
export const JURISDICTION_DOSSIER_PAGES = pathsOf(
  (r) =>
    r.path.startsWith("/dossier/") &&
    r.type === "T1" &&
    !r.path.endsWith("/print/") &&
    !["/dossier/", "/dossier/unplaced/", `/dossier/${DOSSIER_SLUG}/`].includes(r.path),
);

// ---------------------------------------------------------------------------
// Named fixture anchors — routes/params a spec addresses deliberately (these
// name test fixtures, not sweep membership).
// ---------------------------------------------------------------------------

// The seven outline surfaces + the required eighth (the corrections log), asserted to
// exist across the built Phase-15 site (P15.5 deliverable 6 / AC1). Each maps to a
// representative page (the recommender lives on /watch/; the viewer at /evidence/*).
export const PHASE15_SURFACES = {
  dossier: "/dossier/oklahoma-city/",
  map: "/map/",
  network: "/network/",
  watch: "/watch/",
  evidence_recommender: "/watch/",
  evidence_viewer: "/evidence/active-device-count/",
  research_queue: "/research-queue/",
  corrections_log: "/corrections/",
} as const;

// The worked dossier's canonical slug + its derived surfaces (SIG-UI-010..015).
export const DOSSIER_PAGE = `/dossier/${DOSSIER_SLUG}/`;
export const DOSSIER_PRINT = `/dossier/${DOSSIER_SLUG}/print/`;
export const DOSSIER_JSON = `/dossier/${DOSSIER_SLUG}.json`;

// The reviewed research-dossier portfolio (P32.17, SIG-DOS-001/002) — the
// fixture dossier exercising all six answer states.
export const RESEARCH_INDEX = "/research-dossier/";
export const RESEARCH_SLUG = "okc-alpr";
export const RESEARCH_PAGE = `/research-dossier/${RESEARCH_SLUG}/`;
export const RESEARCH_JSON = `/research-dossier/${RESEARCH_SLUG}.json`;

// The no-op sort routes that must NOT exist in the build (K12b NEW-11) — asserted
// 404 in the freshness spec. (A negative-case list by design: these must stay
// un-emitted, which is exactly what the discovery hook's fail-closed contract
// guarantees for the positive direction.)
export const REMOVED_FRESHNESS_SORT_PAGES = [
  "/data-freshness/stale/",
  "/data-freshness/volatility/",
] as const;

// ---------------------------------------------------------------------------
// Navigation over the discovered-route set
// ---------------------------------------------------------------------------

/**
 * `page.goto` for a route a sweep iterates, settled through K4 §8.2's
 * zero-JS instant-redirect stub (`<meta http-equiv="refresh" content="0;
 * url=…">` — a real client navigation every browser follows, JS on or off,
 * e.g. `/dossier/unresolved/` → `/dossier/unplaced/`). Two races sit between
 * the goto and the caller's first evaluation: a refresh still pending from
 * the PREVIOUS route interrupts this goto ("Navigation … is interrupted"),
 * and this page's own refresh destroys the execution context mid-evaluate.
 * The sweep measures the document a visitor lands on, so a detected refresh
 * is waited out rather than fought — every assertion runs on exactly what
 * ships.
 */
export async function gotoSettled(page: Page, path: string): Promise<Response | null> {
  for (let attempt = 0; ; attempt += 1) {
    let resp: Response | null;
    try {
      resp = await page.goto(path);
    } catch (error) {
      // The previous route's instant redirect was still in flight and won —
      // let it land, then navigate again (bounded: a refresh commits at once).
      if (attempt >= 3) throw error;
      await page.waitForLoadState("networkidle").catch(() => undefined);
      continue;
    }
    let instantRefresh = false;
    try {
      const content = await page.evaluate(
        () =>
          document
            .querySelector('meta[http-equiv="refresh"]')
            ?.getAttribute("content") ?? null,
      );
      instantRefresh = content !== null && /^\s*0\s*;/.test(content);
    } catch {
      // The evaluate's context died mid-check — this route IS the redirect
      // stub and its follow-up navigation is already in flight.
      instantRefresh = true;
    }
    if (instantRefresh) {
      // The browser performs the redirect itself — wait for the settled
      // document the visitor lands on (a 0-second refresh fires at once;
      // networkidle covers the follow-up load, never a fixed sleep).
      await page.waitForLoadState("networkidle");
    }
    return resp;
  }
}
