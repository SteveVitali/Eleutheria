// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.18 (UXK14-2 + the K13 IA; SIG-UI-051/UXR-01) — the header navigation
 * model: at most six sections plus the search entry, each rendered only when
 * its target route exists in the release this build serves.
 *
 * Routes are written WITHOUT a leading slash (`dossier/`) so every rendered
 * href goes through `withBase()` — a snapshot build under `/s/<pub>/` keeps
 * its chrome inside the snapshot (SIG-REL-008 `Also:`).
 *
 * The section set is K13 §2.1's ceiling, not a floor: `navForRoutes` drops
 * every item whose route the release does not emit and drops a section that
 * resolves to nothing — the honest posture is "the chrome renders what
 * exists" (UXR-01), never a dead link (SIG-ENG-042). A release carrying an
 * entity hub renders the Organizations section; today's public surface does
 * not, so it is honestly absent.
 */

export interface NavItem {
  label: string;
  /** Route sans leading slash (`dossier/unplaced/`). */
  route: string;
}

export interface NavSection {
  /** Stable machine id (used for aria wiring and tests). */
  id: string;
  label: string;
  /**
   * The route the section LABEL links to. When the declared landing route is
   * absent, `navForRoutes` falls back to the first item that resolves; a
   * section with neither landing nor items is omitted entirely.
   */
  landing: string;
  /** Menu items — each renders only when its route exists (UXR-01). */
  items: NavItem[];
  /**
   * Path prefixes (sans leading slash) that mark this section current — the
   * union of routes the section stands for, whether or not every one is a
   * rendered item (e.g. `data-freshness/` marks Sources & data even though
   * the menu does not list it).
   */
  match: string[];
}

/**
 * The six K13 sections in order. Item order inside a section follows K13's
 * menu lists; routes that the public build does not emit are still DECLARED
 * here so a release that serves them lights the menu entry up without a code
 * change.
 */
export const NAV_SECTIONS: NavSection[] = [
  {
    id: "places",
    label: "Places",
    landing: "dossier/",
    items: [
      { label: "Dossier index", route: "dossier/" },
      { label: "Not yet placed", route: "dossier/unplaced/" },
    ],
    match: ["dossier/"],
  },
  {
    id: "explore",
    label: "Explore",
    landing: "map/",
    items: [
      { label: "Map", route: "map/" },
      { label: "Graph explorer", route: "network/" },
      { label: "Search", route: "search/" },
      { label: "Disagreements", route: "disagreements/" },
    ],
    match: ["map/", "network/", "explore/", "search/", "disagreements/"],
  },
  {
    id: "organizations",
    label: "Organizations",
    landing: "entity/",
    items: [
      { label: "Entity hub", route: "entity/" },
      { label: "Organizations", route: "entity/organization/" },
    ],
    match: ["entity/", "organization/"],
  },
  {
    id: "watch",
    label: "Watch",
    landing: "watch/",
    items: [
      { label: "Upcoming decisions", route: "watch/" },
      { label: "Feeds", route: "watch/feeds/" },
    ],
    match: ["watch/"],
  },
  {
    id: "sources-data",
    label: "Sources & data",
    landing: "sources/",
    items: [
      { label: "Sources", route: "sources/" },
      { label: "Evidence", route: "evidence/" },
      { label: "Downloads & API", route: "data/" },
      { label: "Releases & changes", route: "releases/" },
      { label: "Status", route: "status/" },
    ],
    match: [
      "sources/",
      "evidence/",
      "data/",
      "data-freshness/",
      "releases/",
      "changes/",
      "status/",
    ],
  },
  {
    id: "about",
    label: "About",
    landing: "methodology/",
    items: [
      { label: "About & how it works", route: "about/" },
      { label: "How to read SIG", route: "visual-language/" },
      { label: "Glossary", route: "glossary/" },
      // `methodology/` is the section's landing today — declared anyway so
      // the menu mirrors the canonical list; navForRoutes drops a landing's
      // own duplicate row.
      { label: "Methodology", route: "methodology/" },
      { label: "How sure is SIG?", route: "quality/" },
      { label: "Editorial standards", route: "editorial-standards/" },
      { label: "Corrections", route: "corrections/" },
      { label: "Open questions", route: "research-queue/" },
      { label: "Dispute", route: "dispute/" },
    ],
    match: [
      "about/",
      "visual-language/",
      "glossary/",
      "methodology/",
      "quality/",
      "editorial-standards/",
      "corrections/",
      "research-queue/",
      "dispute/",
      "style-guide/",
      "coverage-metrics/",
      "data-collection/",
      "terms/",
    ],
  },
];

/**
 * A rendered menu item — the declared item whose route the release serves.
 * `route` stays sans slash; the template wraps it in `withBase()`.
 */
export interface RenderedNavItem extends NavItem {
  /** `true` when this item's route IS the current page. */
  current: boolean;
}

export interface RenderedNavSection {
  id: string;
  label: string;
  /** Route the section label links to — always one the release serves. */
  landing: string;
  /** `true` when the current path sits inside this section (aria-current). */
  current: boolean;
  /**
   * The rendered menu: items whose routes exist, minus the item that merely
   * repeats the section's landing link (the label already lands there — a
   * duplicate anchor would double the same href in the nav).
   */
  items: RenderedNavItem[];
}

/**
 * Does `path` (a site path sans leading slash, e.g. `dossier/oklahoma-city/`)
 * sit inside `section`? Prefix match on declared `match` routes — longest
 * prefix wins so `dossier/unplaced/` can never also mark a hypothetical
 * `dossier/unplaced/deeper/` section.
 */
export function pathInSection(path: string, section: NavSection): boolean {
  return section.match.some((prefix) => path === prefix || path.startsWith(prefix));
}

/** The section `path` belongs to, or `undefined` for the home page and
 *  unclassified routes. */
export function sectionForPath(
  path: string,
  sections: NavSection[] = NAV_SECTIONS,
): NavSection | undefined {
  let best: NavSection | undefined;
  let bestLen = -1;
  for (const section of sections) {
    for (const prefix of section.match) {
      if ((path === prefix || path.startsWith(prefix)) && prefix.length > bestLen) {
        best = section;
        bestLen = prefix.length;
      }
    }
  }
  return best;
}

/**
 * The header's rendered model for one release route set: sections filtered to
 * what the release serves, each carrying its resolved landing link, its
 * visible items, and its current marker for `path`.
 */
export function navForRoutes(
  routes: ReadonlySet<string>,
  path: string,
  sections: NavSection[] = NAV_SECTIONS,
): RenderedNavSection[] {
  const current = sectionForPath(path, sections);
  const out: RenderedNavSection[] = [];
  for (const section of sections) {
    const landing = routes.has(section.landing)
      ? section.landing
      : (section.items.find((item) => routes.has(item.route))?.route ?? undefined);
    if (landing === undefined) continue; // nothing in the section resolves — omit (UXR-01)
    const items = section.items
      .filter((item) => routes.has(item.route))
      .filter((item) => item.route !== landing)
      .map((item) => ({ ...item, current: item.route === path }));
    out.push({
      id: section.id,
      label: section.label,
      landing,
      current: current === section,
      items,
    });
  }
  return out;
}

/** A breadcrumb row — `href` is pre-resolved (already `withBase()`-joined);
 *  the last row renders unlinked with aria-current="page". */
export interface Crumb {
  label: string;
  href?: string;
}

/** A page-header-band action link (Cite is rendered by the band itself). */
export interface PageAction {
  label: string;
  href: string;
  testId?: string;
}
