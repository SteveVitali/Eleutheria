// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P35.65 (G3 NEW-6/GT-11; K13 R-8/UXR-25; spec §56.6 SIG-REL-008 `Also:`):
 * `withBase()` — the single seam every web link/href/path construction calls
 * so a snapshot release built under `/s/<pub>/` stays self-contained: a cited
 * snapshot page links to its own pinned copy, never out to the live root.
 *
 * The helper reads Astro's configured base (`import.meta.env.BASE_URL`; today
 * `astro.config.mjs` sets no `base`, so it is `/`) and joins it with the path
 * using exactly one separating slash — never string-concatenating a hardcoded
 * `/`. When the snapshot/deploy rows (P36.66a/b) set `base`, every call site
 * re-resolves under the snapshot prefix with no template edits.
 *
 * New templates MUST route root-absolute paths through `withBase()` — the CI
 * containment check (`web/scripts/check-root-absolute-paths.mjs`, wired into
 * `npm run check` as `check:paths`) fails when a template adds a root-absolute
 * path site, so the legacy count G3 NEW-6 recorded can only shrink, never
 * grow. The sweep of the grandfathered sites is P36.66a's row.
 */

/**
 * The configured Astro base verbatim (`/` when none is set, `/s/<pub>/`-shaped
 * when the snapshot/deploy rows configure one). Exported read-only for call
 * sites that must render the base itself (nav state, canonical joins) — path
 * construction still goes through `withBase()`.
 */
export const BASE: string = import.meta.env?.BASE_URL ?? "/";

/** Collapse a configured base to its join form: `/` → ``, `/s/<pub>/` → `/s/<pub>`. */
function normaliseBase(base: string): string {
  const trimmed = base.replace(/\/+$/, "");
  if (trimmed === "") return "";
  // A base without a leading slash is malformed config; root it rather than
  // emit a relative URL that would escape differently per page depth.
  return trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
}

/**
 * Join `base` and `path` with exactly one separating slash. Tolerates
 * leading/trailing slashes on either side, a root (`/` or empty) base, a
 * bare `/` or empty path, and multiple leading slashes on the path (a
 * `//host`-shaped input can never smuggle a protocol-relative URL out — it
 * collapses to one `/`). Exported so build scripts and tests can join against
 * an explicit base; templates call `withBase()`.
 */
export function joinBase(base: string, path: string): string {
  const b = normaliseBase(base);
  // Strip every leading slash then prepend exactly one: "" → "/", "/" → "/",
  // "dossier/" → "/dossier/", "//evil" → "/evil".
  const p = `/${path.replace(/^\/+/, "")}`;
  return `${b}${p}`;
}

/**
 * The path helper every link/href/path construction uses. Under the default
 * root base this returns the path unchanged (leading slash normalised); under
 * a configured `/s/<pub>/` base it returns the path inside the snapshot.
 */
export function withBase(path: string): string {
  return joinBase(BASE, path);
}
