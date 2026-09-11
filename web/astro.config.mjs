// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { defineConfig } from "astro/config";

// The public SIG web shell (Phase 15). Astro is a zero-JS-by-default static-first
// framework: with no explicit `client:*` directive on a component, the built page
// ships no client JavaScript at all (SIG-UI-036). Archivability is therefore
// STRUCTURAL — re-enabling client JS requires an explicit, greppable `client:`
// directive in a `.astro` file, not silent erosion. `output: "static"` makes the
// whole build a set of plain HTML files that read from web archives years later
// (SIG-UI-037).
export default defineConfig({
  output: "static",
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
