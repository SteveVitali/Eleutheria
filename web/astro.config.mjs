// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { defineConfig } from "astro/config";
import { cpSync, existsSync, mkdirSync } from "node:fs";
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
        const src = join(exportDir, "web", "tiles", "sig-infrastructure.pmtiles");
        if (!existsSync(src)) {
          // Fail LOUD (like the dossier data layer): an export build that cannot find
          // its rendered tiles is a build error, never a silently tile-less map.
          throw new Error(
            `SIG_DATA_SOURCE=export but the rendered tiles are missing: ${src}. ` +
              "Run `sig-exports build --jurisdiction <j> --out <dir>` first.",
          );
        }
        const destDir = join(fileURLToPath(dir), "tiles");
        mkdirSync(destDir, { recursive: true });
        cpSync(src, join(destDir, "sig-infrastructure.pmtiles"));
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
  integrations: [sigExportTiles()],
  site: "https://sig.example",
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
