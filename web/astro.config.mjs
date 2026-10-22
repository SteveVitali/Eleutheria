// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { defineConfig } from "astro/config";
import react from "@astrojs/react";
import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join, relative, resolve, sep } from "node:path";
import { resolveTileCopyList } from "./scripts/export-tiles.mjs";
import { buildManifest, classifyDist, writeManifest } from "./src/lib/page-types.ts";

// P21.5 (deliverable 3, LD-F07/H08) + P30.3 (ADR-106) + P31.15 (ADR-R9-TILES) +
// P35.52 (sig.map-tiles/2, ADR-156): in `export` mode the static build CONSUMES
// the rendered vector tiles the export produced — ONE archive PER LICENCE
// COMPARTMENT (`<compartment>-sites.<sha8>.pmtiles`, e.g. the ODbL osm_physical
// layer apart from the CC-BY graph) — never a merged, mixed-licence archive.
// Each is served as its own source with its own attribution
// (/map/style.json), over a plain background with NO basemap (Q8). The copy list is
// the SAME list `/map/style.json` is built from (data.ts getCompartmentTileSources):
// the manifest's `web/tiles/<compartment>-sites.<sha8>.pmtiles` artifacts plus the
// `web/tiles/index.json` contract index — so the style can never name an archive
// that was not copied, and no unlisted file is served.
// Fixtures mode (the CI default) is untouched.
function sigExportTiles() {
  return {
    name: "sig-export-tiles",
    hooks: {
      "astro:build:done": ({ dir }) => {
        // P35.51: the same manifest-listed copy runs under the `national`
        // overlay — the synthetic national fixture's per-compartment archives
        // (SIG_NATIONAL_DIR / the gitignored default `web/national/`).
        const mode = process.env.SIG_DATA_SOURCE;
        if (mode !== "export" && mode !== "national") return;
        const repoRoot = fileURLToPath(new URL("../", import.meta.url));
        const override =
          mode === "national" ? process.env.SIG_NATIONAL_DIR : process.env.SIG_EXPORT_DIR;
        // `npm --prefix web` runs scripts with cwd=web/, so a repo-relative
        // dir override must be anchored at the repo root, not the cwd.
        const exportDir =
          override !== undefined && override !== ""
            ? resolve(repoRoot, override)
            : join(repoRoot, mode === "national" ? "web/national" : "exports/out/okc");
        const destDir = join(fileURLToPath(dir), "tiles");
        // P34.34a: the copy list comes from resolveTileCopyList — a manifest
        // that lists zero archives is an HONEST empty-tile export (the map
        // page states it), not a build error; only a missing manifest or a
        // listed-but-absent archive fails loud.
        const { tilesDir, files } = resolveTileCopyList(exportDir, mode);
        if (files.length === 0) return;
        mkdirSync(destDir, { recursive: true });
        for (const f of files) cpSync(join(tilesDir, f), join(destDir, f));
      },
    },
  };
}

// P34.10 (SIG-OPS-003, G1 §3.2 item 1): the DEFAULT build emits only the
// allow-listed public surface (`ops/public_routes.toml`). Every route that must
// never ship to a public origin lives outside `src/pages/` under
// `src/internal/` — the authenticated curation shell `/curate/**` (ADR-068, a
// loopback-only app surface, never public), the withdrawn surfaces
// (`/contribution-back/` per C-12, `/visual-language/` per A-0.3 = b), and the
// not-yet-approved namespaces (`/releases/`, `/research-dossier/` — the former
// is also owned by the release pipeline, exactly one generator per G2 0b).
// They are injected ONLY when `SIG_BUILD_INTERNAL=1` — the web e2e suite sets it
// (its tests exercise the internal surface); a publishable build never carries
// them, and `sig-ops publish-web` independently refuses a tree that does.
const INTERNAL_ROUTES = [
  ["/curate", "curate/index.astro"],
  ["/curate/submit", "curate/submit.astro"],
  ["/curate/tasks", "curate/tasks.astro"],
  ["/curate/contradictions", "curate/contradictions.astro"],
  ["/curate/revert", "curate/revert.astro"],
  ["/curate/[id]", "curate/[id].astro"],
  ["/releases", "releases/index.astro"],
  ["/research-dossier", "research-dossier/index.astro"],
  ["/research-dossier/[slug]", "research-dossier/[slug].astro"],
  ["/research-dossier/[slug].json", "research-dossier/[slug].json.ts"],
  ["/contribution-back", "contribution-back.astro"],
  ["/visual-language", "visual-language.astro"],
];

function sigInternalRoutes() {
  const enabled = !["", "0", "false"].includes(
    (process.env.SIG_BUILD_INTERNAL ?? "").trim().toLowerCase(),
  );
  return {
    name: "sig-internal-routes",
    hooks: {
      "astro:config:setup": ({ injectRoute }) => {
        if (!enabled) return;
        for (const [pattern, file] of INTERNAL_ROUTES) {
          injectRoute({
            pattern,
            entrypoint: fileURLToPath(new URL(`./src/internal/${file}`, import.meta.url)),
          });
        }
      },
    },
  };
}

// P34.13 (QW-11): the chrome quick-fixes that belong to the BUILD, not a page —
// (a) the canonical-only sitemap (RI-51): walk the emitted pages and list a URL
// only when it is its OWN canonical — print pages canonicalise to their dossier
// and so never appear, and every URL resolves on the canonical origin — plus
// noindex pages never appear at all; (b) the flat /403.html + /410.html copies
// matching the /404.html error-page convention (the nginx `error_page` wiring
// that serves them is P34.40's dark roll — this row only builds the pages).
function sigChrome() {
  return {
    name: "sig-chrome",
    hooks: {
      "astro:build:done": ({ dir }) => {
        const distDir = fileURLToPath(dir);
        for (const code of ["403", "410"]) {
          const page = join(distDir, code, "index.html");
          if (existsSync(page)) cpSync(page, join(distDir, `${code}.html`));
        }
        const INTERNAL_SEGMENTS = new Set(
          INTERNAL_ROUTES.map(([pattern]) => pattern.split("/")[1]).concat(["task"]),
        );
        const origin = "https://surveillancegraph.org";
        const urls = [];
        const walk = (d) => {
          for (const entry of readdirSync(d, { withFileTypes: true })) {
            const full = join(d, entry.name);
            if (entry.isDirectory()) {
              walk(full);
            } else if (entry.name === "index.html") {
              const html = readFileSync(full, "utf-8");
              if (html.includes('name="robots" content="noindex"')) continue;
              const m = html.match(/<link rel="canonical" href="([^"]+)"/);
              if (!m) continue;
              const rel = `${relative(distDir, full).split(sep).join("/").replace(/index\.html$/, "")}`;
              const own = `${origin}/${rel}`;
              if (m[1] === own) urls.push(m[1]);
            }
          }
        };
        walk(distDir);
        const publicUrls = urls
          .filter((u) => !INTERNAL_SEGMENTS.has(new URL(u).pathname.split("/")[1]))
          .sort();
        // P35.39 (SIG-TRANSP-017 / J3 §6.6): the linked machine metadata is
        // sitemap-listed. The DCAT-3 catalog the export emits (`catalog.jsonld`
        // at the bundle root) is copied to a web-owned route — `/releases/` is a
        // protected prefix the release pipeline owns, so the build can never
        // serve it there. Export mode only: a fixtures build carries no real
        // catalog, and the sitemap never names a URL the built site will not
        // resolve (QW-11: every loc must answer on the emitted tree).
        if (process.env.SIG_DATA_SOURCE === "export") {
          const repoRoot = fileURLToPath(new URL("../", import.meta.url));
          const override = process.env.SIG_EXPORT_DIR;
          const exportDir =
            override !== undefined && override !== ""
              ? resolve(repoRoot, override)
              : join(repoRoot, "exports/out/okc");
          const catalogSrc = join(exportDir, "catalog.jsonld");
          if (existsSync(catalogSrc)) {
            mkdirSync(join(distDir, "data"), { recursive: true });
            cpSync(catalogSrc, join(distDir, "data", "catalog.jsonld"));
            publicUrls.push(`${origin}/data/catalog.jsonld`);
          }
        }
        const sitemap =
          `<?xml version="1.0" encoding="UTF-8"?>\n` +
          `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
          publicUrls.map((u) => `  <url><loc>${u}</loc></url>`).join("\n") +
          `\n</urlset>\n`;
        writeFileSync(join(distDir, "sitemap.xml"), sitemap);
      },
    },
  };
}

// P35.50 (UXK0-1, K0 §4.12 item 1, ADR-155, SIG-UI-041/NEW-4): route discovery —
// the `astro:build:done` hook walks `dist/**/*.html` and classifies every built
// route against web/src/lib/page-types.ts. An unclassified route or a route two
// registry entries claim at equal strength FAILS THE BUILD — a new page is
// classified before it ships, never silently. The hook also writes
// `dist/page-types.json` (`sig.page-types-manifest/1`), the discovered-route
// manifest every e2e/axe sweep iterates instead of a hand-maintained list. It
// runs LAST so it sees the complete emitted tree (the injected internal routes,
// the flat 403/410 copies and every generated page alike).
function sigPageTypes() {
  return {
    name: "sig-page-types",
    hooks: {
      "astro:build:done": ({ dir }) => {
        const distDir = fileURLToPath(dir);
        const { routes, errors } = classifyDist(distDir);
        if (errors.length > 0) {
          throw new Error(
            `page-type registry: ${errors.length} unclassifiable route(s)\n  ${errors.join("\n  ")}`,
          );
        }
        writeManifest(distDir, buildManifest(routes));
        console.log(`sig-page-types: ${routes.length} route(s) classified`);
      },
    },
  };
}

// The public SIG web shell (Phase 15). Astro is a zero-JS-by-default static-first
// framework: with no explicit `client:*` directive on a component, the built page
// ships no client JavaScript at all (SIG-UI-036). Archivability is therefore
// STRUCTURAL — re-enabling client JS requires an explicit, greppable `client:`
// directive in a `.astro` file, not silent erosion. `output: "static"` makes the
// whole build a set of plain HTML files that read from web archives years later
// (SIG-UI-037).
export default defineConfig({
  output: "static",
  // P27.9 (DECISION-SPA = B, ADR-097 extending ADR-068): React arrives via
  // @astrojs/react. It renders to STATIC HTML at build time by default (no client
  // JS) — client JavaScript ships ONLY for components carrying an explicit
  // `client:*` directive, which in the public surface is exactly the three named
  // islands (map / network / search). Every other page still ships zero `<script>`
  // (SIG-UI-036/037); each island preserves its no-JS fallback (SIG-UI-050).
  integrations: [react(), sigExportTiles(), sigInternalRoutes(), sigChrome(), sigPageTypes()],
  // The canonical public origin (P27.6 deliverable 4, ADR-093). This is the real
  // custom domain the launch surface is cited at; the belief-pinned permalinks
  // (SIG-UI-035) resolve against it. DNS/TLS cut-over completes in P27.10 — the
  // origin string is fixed here now so no permalink churns when the domain goes live.
  site: "https://surveillancegraph.org",
  // Trailing slashes normalised so belief-pinned permalinks are stable across
  // hosts and archives (SIG-UI-035).
  trailingSlash: "always",
  build: {
    // Inline nothing implicitly: keep assets as separate, cacheable, budgetable
    // files so the Lighthouse resource-size budgets (SIG-UI-041) are meaningful.
    inlineStylesheets: "never",
  },
  devToolbar: { enabled: false },
});
