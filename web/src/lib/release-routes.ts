// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.18 (UXK14-2; SIG-UI-051/UXR-01) — the release route manifest: the set
 * of public routes the served build actually emits, so the chrome renders a
 * section or menu item only when its target resolves in THIS release.
 *
 * The manifest is computed, never hand-maintained:
 *
 *   1. Every STATIC `.astro` page under `src/pages/` emits its route — the
 *      file on disk is the route contract (`dossier/index.astro` →
 *      `dossier/`). Dynamic `[param]`/catch-all files contribute nothing on
 *      their own: their emitted routes are data-dependent, so they never
 *      stand in for a nav target.
 *   2. Routes whose emission is data-dependent resolve through explicit
 *      PROBES — declared beside the same condition the page's own
 *      `getStaticPaths` uses (the "Not yet placed" report, the freshness
 *      sort index). An absent probe target is simply never offered.
 *   3. `SIG_DATA_SOURCE=export` additionally reads the release pipeline's
 *      declared served routes — `<exportDir>/web/site-routes.json`
 *      (`sig.site-routes/1`, `{schema, routes:[…]}`) — when the pipeline
 *      emits it; absent means nothing extra is offered.
 *
 * Internal surfaces are never members: they live under `src/internal/`
 * (`/curate/**`, `/releases/`, `/research-dossier/**`, `/visual-language/`,
 * `/contribution-back/`), outside the scanned tree, and a publishable build
 * does not emit them (SIG-OPS-003). A nav target that names one never
 * renders — which is the point of the manifest.
 *
 * Routes are strings WITHOUT a leading slash (`dossier/`), matching
 * `nav.ts`'s convention; the home page is `""`. `withBase()` joins them at
 * render.
 */

import { existsSync, readFileSync } from "node:fs";
import { basename, join } from "node:path";
import { dataSource, exportDir, getUnplacedReport } from "./data";

/**
 * The page files under `src/pages/` — Vite resolves the glob at bundle time,
 * so the same key set exists in dev, in vitest, and inside the prerender
 * bundle (a filesystem scan would anchor on the emitted chunk's URL, not the
 * source tree). Keys are POSIX paths relative to this module
 * (`../pages/dossier/index.astro`); the `src/internal/` tree is outside the
 * glob, so internal surfaces can never enter the manifest.
 */
const PAGE_MODULES = import.meta.glob("../pages/**/*.astro");
const PAGES_PREFIX = "../pages/";

const SITE_ROUTES_SCHEMA = "sig.site-routes/1";

/**
 * The route a static `.astro` page emits, sans leading slash — `index.astro`
 * → `""`, `watch.astro` → `watch/`, `data/dictionary.astro` →
 * `data/dictionary/`. Dynamic pages and non-page files return `null`.
 */
function routeForFile(rel: string): string | null {
  if (!rel.endsWith(".astro")) return null;
  if (rel.includes("[")) return null; // dynamic emitters never stand in for nav targets
  const bare = rel.slice(0, -".astro".length);
  const base = basename(bare);
  // `bare` minus its last segment — "data/index" → "data/" or "" for a
  // top-level page (the directory prefix keeps its trailing separator).
  const dir = bare.slice(0, bare.length - base.length);
  return base === "index" ? dir : `${bare}/`;
}

/**
 * The release pipeline's declared served routes, `export` mode only. The
 * file is OPTIONAL — an export that does not declare extra routes emits
 * none and the manifest stands on the emitted pages alone. A PRESENT file
 * that is malformed fails the build (fail-closed, SIG-ENG-042) rather than
 * silently dropping the declared routes.
 */
function declaredSiteRoutes(): string[] {
  const path = join(exportDir(), "web", "site-routes.json");
  if (!existsSync(path)) return [];
  let parsed: unknown;
  try {
    parsed = JSON.parse(readFileSync(path, "utf-8"));
  } catch (cause) {
    throw new Error(`${path}: not valid JSON`, { cause });
  }
  const doc = parsed as { schema?: unknown; routes?: unknown };
  if (doc.schema !== SITE_ROUTES_SCHEMA || !Array.isArray(doc.routes)) {
    throw new Error(
      `${path}: expected a ${SITE_ROUTES_SCHEMA} object with a routes array`,
    );
  }
  return doc.routes.map((r) => {
    if (typeof r !== "string") {
      throw new Error(`${path}: route entries must be strings`);
    }
    return r.replace(/^\/+/, "");
  });
}

/**
 * The set of routes this build's chrome may target. Empty string is the
 * home route; every other entry is a trailing-slash route sans leading
 * slash (`dossier/`, `data/dictionary/`).
 */
export function releaseRoutes(): Set<string> {
  const routes = new Set<string>();
  for (const key of Object.keys(PAGE_MODULES)) {
    if (!key.startsWith(PAGES_PREFIX)) continue;
    const route = routeForFile(key.slice(PAGES_PREFIX.length));
    if (route !== null) routes.add(route);
  }

  // --- Probes: routes a dynamic page emits only under a data condition ----
  // `dossier/[...path].astro` emits /dossier/unplaced/ exactly when the
  // unplaced report exists — the same condition its getStaticPaths uses.
  if (getUnplacedReport() !== null) routes.add("dossier/unplaced/");
  // `data-freshness/[...sort].astro` always emits its unsorted index
  // (params.sort === undefined) whenever the page exists.
  if (`${PAGES_PREFIX}data-freshness/[...sort].astro` in PAGE_MODULES) {
    routes.add("data-freshness/");
  }

  // --- The release pipeline's declared served routes (export mode only) ---
  if (dataSource() === "export") {
    for (const route of declaredSiteRoutes()) routes.add(route);
  }
  return routes;
}
