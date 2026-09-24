// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { defineConfig } from "astro/config";
import react from "@astrojs/react";
import { cpSync, existsSync, mkdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

// P21.5 (deliverable 3, LD-F07/H08): in `export` mode the static build CONSUMES the
// rendered vector tiles the jurisdiction export produced. `sig-exports build
// --jurisdiction <j>` renders the ODbL device layer to
// `<exportDir>/web/tiles/sig-infrastructure.pmtiles`; this integration copies it to
// `<dist>/tiles/…` so the map's self-hosted PMTiles source (SIG-UI-038, /map/style.json)
// resolves to a REAL rendered archive. Fixtures mode (the CI default) is untouched.
function sigExportTiles() {
  return {
    name: "sig-export-tiles",
    hooks: {
      "astro:build:done": ({ dir }) => {
        if (process.env.SIG_DATA_SOURCE !== "export") return;
        const repoRoot = fileURLToPath(new URL("../", import.meta.url));
        const exportDir = process.env.SIG_EXPORT_DIR ?? join(repoRoot, "exports/out/okc");
        const tilesDir = join(exportDir, "web", "tiles");
        const src = join(tilesDir, "sig-infrastructure.pmtiles");
        const destDir = join(fileURLToPath(dir), "tiles");
        if (existsSync(src)) {
          mkdirSync(destDir, { recursive: true });
          cpSync(src, join(destDir, "sig-infrastructure.pmtiles"));
          return;
        }
        // P30.3 (ADR-106): the national spine export renders ONE archive PER LICENCE
        // COMPARTMENT (`<compartment>-sites.pmtiles`, e.g. the ODbL osm_physical layer
        // apart from the CC-BY graph) — never a merged, mixed-licence archive. Each is
        // served as its own source with its own attribution (/map/style.json).
        // The SAME list `/map/style.json` is built from (data.ts getCompartmentTileSources):
        // the manifest's `web/tiles/<compartment>-sites.pmtiles` artifacts — so the style can
        // never name an archive that was not copied, and no unlisted file is served.
        const manifestPath = join(exportDir, "manifest.json");
        const listed = existsSync(manifestPath)
          ? (JSON.parse(readFileSync(manifestPath, "utf-8")).artifacts ?? [])
              .map((a) => String(a.path ?? ""))
              .filter((p) => /^web\/tiles\/[^/]+-sites\.pmtiles$/.test(p))
              .map((p) => p.slice("web/tiles/".length))
          : [];
        const perCompartment = listed.filter((f) => existsSync(join(tilesDir, f)));
        if (perCompartment.length !== listed.length) {
          throw new Error(
            `SIG_DATA_SOURCE=export: the manifest lists tile archives missing from ${tilesDir}.`,
          );
        }
        if (perCompartment.length === 0) {
          // Fail LOUD (like the dossier data layer): an export build that cannot find
          // its rendered tiles is a build error, never a silently tile-less map.
          throw new Error(
            `SIG_DATA_SOURCE=export but the rendered tiles are missing: ${src} ` +
              "(or per-compartment <compartment>-sites.pmtiles). Run `sig-exports build` first.",
          );
        }
        mkdirSync(destDir, { recursive: true });
        for (const f of perCompartment) cpSync(join(tilesDir, f), join(destDir, f));
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
  integrations: [react(), sigExportTiles()],
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
