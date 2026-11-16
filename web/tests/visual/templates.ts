// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.60 (UXK14-10, SIG-UI-152, DR-K14-18; K14 §9) — the visual-regression
 * template registry.
 *
 * SIG-UI-152 binds "every template": a TEMPLATE here is a page module
 * (`src/pages/**.astro`, `src/internal/**.astro`) — the unit the build's
 * `component` field records — and template FAMILIES are the rows below, where
 * pagination/sort/facet sibling modules that render one visual template share
 * a group. A group is the screenshot cell: one deterministic representative
 * route per group, shot at every {light, dark} × {1440, 390, 320} cell.
 *
 * The claim rule is fail-closed exactly like the page-type registry (K0 NEW-4):
 *   - every `.astro` file under `src/pages` + `src/internal` MUST be claimed by
 *     at least one group (unit guard scans the trees — a new template file
 *     lands unclaimed and the build goes red until a human assigns it);
 *   - every `component` value a built manifest records MUST be claimed;
 *   - a group whose components emit no route on the current build is recorded
 *     `unemitted`, never silently dropped — unless `optional`, a group with
 *     components present but no emitted route still shoots nothing and the
 *     spec reports it.
 *
 * `prefer` is a ranking hint, never a filter: matching paths sort first (then
 * lexicographic), so the representative is deterministic per build and a
 * changed pick surfaces as a baseline diff in the ticket PR (DR-K14-18).
 */

export interface VisualTemplateGroup {
  /** Template id — the snapshot stem (`<id>--<theme>-<viewport>.png`). */
  readonly id: string;
  /** `src/`-relative page modules this group claims (one visual template family). */
  readonly components: readonly string[];
  /** Representative-path preference: matches sort first (then lexicographic). */
  readonly prefer?: RegExp;
  /**
   * The family's routes are data-dependent — on a build thin enough to emit
   * none, the group is recorded `unemitted` instead of failing (e.g. a
   * paginated variant with no second page).
   */
  readonly optional?: boolean;
  /** Emitted only under SIG_BUILD_INTERNAL — never a public surface. */
  readonly internal?: boolean;
  readonly note?: string;
}

const WATCH_FACET_VARIANTS = [
  "pages/watch/kind/[k].astro",
  "pages/watch/kind/[k]/page/[n].astro",
  "pages/watch/technology/[c].astro",
  "pages/watch/technology/[c]/page/[n].astro",
  "pages/watch/vendor/[id].astro",
  "pages/watch/vendor/[id]/page/[n].astro",
] as const;

export const VISUAL_TEMPLATE_GROUPS: readonly VisualTemplateGroup[] = [
  // -------------------------------------------------------------- chrome ---
  { id: "home", components: ["pages/index.astro"], prefer: /^\/$/ },
  { id: "error-403", components: ["pages/403.astro"], prefer: /^\/403\/$/ },
  { id: "error-404", components: ["pages/404.astro"], prefer: /^\/404\.html$/ },
  { id: "error-410", components: ["pages/410.astro"], prefer: /^\/410\/$/ },
  { id: "error-500", components: ["pages/500.astro"], prefer: /^\/500\/$/ },
  { id: "dispute", components: ["pages/dispute.astro"], prefer: /^\/dispute\/$/ },
  { id: "terms", components: ["pages/terms.astro"], prefer: /^\/terms\/$/ },

  // --------------------------------------------------- about / reference ---
  {
    id: "about",
    components: ["pages/about.astro", "pages/about/how-to-read-a-dossier.astro"],
    prefer: /^\/about\/$/,
  },
  {
    id: "about-editorial-decisions",
    components: ["pages/about/editorial-decisions.astro"],
    prefer: /^\/about\/editorial-decisions\/$/,
  },
  {
    id: "about-legal-demands",
    components: ["pages/about/legal-demands.astro"],
    prefer: /^\/about\/legal-demands\/$/,
  },
  { id: "methodology", components: ["pages/methodology.astro"], prefer: /^\/methodology\/$/ },
  {
    id: "editorial-standards",
    components: ["pages/editorial-standards.astro"],
    prefer: /^\/editorial-standards\/$/,
  },
  {
    id: "coverage-metrics",
    components: ["pages/coverage-metrics.astro"],
    prefer: /^\/coverage-metrics\/$/,
  },
  { id: "corrections", components: ["pages/corrections.astro"], prefer: /^\/corrections\/$/ },
  { id: "quality", components: ["pages/quality/index.astro"], prefer: /^\/quality\/$/ },
  { id: "style-guide", components: ["pages/style-guide.astro"], prefer: /^\/style-guide\/$/ },
  { id: "glossary", components: ["pages/glossary.astro"], prefer: /^\/glossary\/$/ },
  {
    id: "data-collection",
    components: ["pages/data-collection.astro"],
    prefer: /^\/data-collection\/$/,
  },

  // -------------------------------------------------------------- dossier --
  {
    id: "dossier-index",
    components: ["pages/dossier/index.astro"],
    prefer: /^\/dossier\/$/,
  },
  {
    id: "dossier-sort",
    components: ["pages/dossier/sort/[key].astro"],
    prefer: /^\/dossier\/sort\//,
  },
  {
    id: "dossier-by",
    components: ["pages/dossier/by/[dim]/[value].astro"],
    prefer: /^\/dossier\/by\//,
  },
  {
    id: "dossier-az",
    components: ["pages/dossier/a-z/index.astro", "pages/dossier/a-z/[letter].astro"],
    prefer: /^\/dossier\/a-z\/[a-z]\/$/,
  },
  // The dossier page itself renders country / admin-1 / county / place levels
  // and the unplaced report — one module, three shots at three depths.
  {
    id: "dossier-country",
    components: ["pages/dossier/[...path].astro"],
    prefer: /^\/dossier\/[^/]+\/$/,
  },
  {
    id: "dossier-admin1",
    components: ["pages/dossier/[...path].astro"],
    prefer: /^\/dossier\/[^/]+\/[^/]+\/$/,
    optional: true,
  },
  {
    id: "dossier-locality",
    components: ["pages/dossier/[...path].astro"],
    prefer: /^\/dossier\/[^/]+\/[^/]+\/[^/]+\/$/,
    optional: true,
  },
  {
    id: "dossier-print",
    components: ["pages/dossier/[...path]/print.astro"],
    prefer: /^\/dossier\/[^/]+\/[^/]+\/print\/$/,
  },
  {
    id: "dossier-sites",
    components: [
      "pages/dossier/[...path]/sites/index.astro",
      "pages/dossier/[...path]/sites/page/[n].astro",
    ],
    prefer: /^\/dossier\/[^/]+\/[^/]+\/sites\/$/,
    // Data-dependent (K14 §9's "optional" cell): `emittedSiteLists` only emits
    // a /sites/ list for a dossier whose site model crosses the list
    // threshold — the national fixture emits none, so the grid records the
    // family `unemitted` rather than dropping it silently.
    optional: true,
  },
  {
    id: "dossier-sources",
    components: [
      "pages/dossier/[...path]/sources/index.astro",
      "pages/dossier/[...path]/sources/page/[n].astro",
      "pages/dossier/[...path]/sources/sort/[key]/index.astro",
      "pages/dossier/[...path]/sources/sort/[key]/page/[n].astro",
    ],
    prefer: /^\/dossier\/[^/]+\/[^/]+\/sources\/$/,
  },
  {
    id: "dossier-downloads",
    components: ["pages/dossier/[...path]/downloads/index.astro"],
    prefer: /^\/dossier\/[^/]+\/downloads\/$/,
  },
  { id: "id-stub", components: ["pages/id/[type]/[uuid].astro"], prefer: /^\/id\// },

  // ------------------------------------------------------------------ T2 ---
  { id: "map", components: ["pages/map.astro"], prefer: /^\/map\/$/ },
  { id: "explore", components: ["pages/explore/index.astro"], prefer: /^\/explore\/$/ },
  { id: "search", components: ["pages/search.astro"], prefer: /^\/search\/$/ },

  // ------------------------------------------------------------- entities --
  { id: "entity-index", components: ["pages/entity/index.astro"], prefer: /^\/entity\/$/ },
  {
    id: "entity-type",
    components: ["pages/entity/[type]/index.astro", "pages/entity/[type]/page/[n].astro"],
    prefer: /^\/entity\/[^/]+\/$/,
  },
  {
    id: "entity-detail",
    components: ["pages/entity/[type]/[key]/index.astro"],
    prefer: /^\/entity\/[^/]+\/[^/]+\/$/,
  },
  {
    id: "entity-print",
    components: ["pages/entity/[type]/[key]/print.astro"],
    prefer: /^\/entity\/[^/]+\/[^/]+\/print\/$/,
    optional: true,
  },
  {
    id: "graphs-index",
    components: ["pages/graphs/index.astro"],
    prefer: /^\/graphs\/$/,
  },
  {
    id: "graphs-overview",
    components: ["pages/graphs/[...parts].astro"],
    prefer: /^\/graphs\/[^/]+\/$/,
  },

  // ------------------------------------------------------------- evidence --
  {
    id: "evidence-index",
    components: ["pages/evidence/index.astro", "pages/evidence/page/[n].astro"],
    prefer: /^\/evidence\/$/,
  },
  {
    id: "evidence-facet",
    components: [
      "pages/evidence/lane/[...path].astro",
      "pages/evidence/place/[...path].astro",
      "pages/evidence/source/[...path].astro",
      "pages/evidence/state/[...path].astro",
      "pages/evidence/type/[...path].astro",
    ],
    prefer: /^\/evidence\/type\//,
  },
  {
    id: "evidence-artifact",
    components: ["pages/evidence/artifact/[handle].astro"],
    prefer: /^\/evidence\/artifact\//,
  },
  {
    id: "evidence-diff",
    components: ["pages/evidence/artifact/[handle]/diff/[pair].astro"],
    prefer: /^\/evidence\/artifact\/[^/]+\/diff\//,
    optional: true,
  },
  {
    id: "evidence-claim",
    components: ["pages/evidence/claim/[id].astro"],
    prefer: /^\/evidence\/claim\//,
  },
  {
    id: "evidence-stub",
    components: ["pages/evidence/[id].astro"],
    prefer: /^\/evidence\/[^/]+\/$/,
    optional: true,
  },

  // ------------------------------------------------------- research queue --
  {
    id: "research-queue-index",
    components: [
      "pages/research-queue/index.astro",
      "pages/research-queue/page/[n].astro",
      "pages/research-queue/sort/[k].astro",
      "pages/research-queue/sort/[k]/page/[n].astro",
    ],
    prefer: /^\/research-queue\/$/,
  },
  {
    id: "research-queue-place",
    components: ["pages/research-queue/place/[...path].astro"],
    prefer: /^\/research-queue\/place\/[^/]+\/[^/]+\/$/,
    optional: true,
  },
  {
    id: "research-queue-type",
    components: [
      "pages/research-queue/type/[t].astro",
      "pages/research-queue/type/[t]/page/[n].astro",
      "pages/research-queue/type/[t]/sort/[k].astro",
      "pages/research-queue/type/[t]/sort/[k]/page/[n].astro",
    ],
    prefer: /^\/research-queue\/type\/[^/]+\/$/,
  },
  {
    id: "research-queue-role",
    components: [
      "pages/research-queue/role/[r].astro",
      "pages/research-queue/role/[r]/page/[n].astro",
      "pages/research-queue/role/[r]/sort/[k].astro",
      "pages/research-queue/role/[r]/sort/[k]/page/[n].astro",
    ],
    prefer: /^\/research-queue\/role\/[^/]+\/$/,
  },
  {
    id: "research-queue-campaigns",
    components: [
      "pages/research-queue/campaigns/index.astro",
      "pages/research-queue/campaigns/page/[n].astro",
    ],
    prefer: /^\/research-queue\/campaigns\/$/,
    optional: true,
  },
  {
    id: "research-queue-campaign",
    components: ["pages/research-queue/campaign/[handle].astro"],
    prefer: /^\/research-queue\/campaign\//,
    optional: true,
  },
  { id: "task", components: ["pages/task/[slug].astro"], prefer: /^\/task\// },

  // -------------------------------------------------------------- sources --
  {
    id: "sources-index",
    components: [
      "pages/sources.astro",
      "pages/sources/page/[n].astro",
      "pages/sources/sort/[col]/[dir].astro",
      "pages/sources/sort/[col]/[dir]/page/[n].astro",
    ],
    prefer: /^\/sources\/$/,
  },
  {
    id: "sources-by",
    components: [
      "pages/sources/by/[dim]/[value].astro",
      "pages/sources/by/[dim]/[value]/page/[n].astro",
    ],
    prefer: /^\/sources\/by\//,
  },
  {
    id: "sources-runs",
    components: [
      "pages/sources/runs/index.astro",
      "pages/sources/runs/page/[n].astro",
      "pages/sources/runs/sort/[col]/[dir].astro",
      "pages/sources/runs/sort/[col]/[dir]/page/[n].astro",
    ],
    prefer: /^\/sources\/runs\/$/,
  },
  {
    id: "sources-rights",
    components: [
      "pages/sources/rights/index.astro",
      "pages/sources/rights/page/[n].astro",
      "pages/sources/rights/sort/[col]/[dir].astro",
      "pages/sources/rights/sort/[col]/[dir]/page/[n].astro",
    ],
    prefer: /^\/sources\/rights\/$/,
  },
  {
    id: "sources-identifier-changed",
    components: ["pages/sources/identifier-changed.astro"],
    prefer: /^\/sources\/identifier-changed\/$/,
    optional: true,
  },
  {
    id: "source-page",
    components: ["pages/sources/[id]/index.astro"],
    prefer: /^\/sources\/[^/]+\/$/,
  },
  {
    id: "source-runs",
    components: [
      "pages/sources/[id]/runs/index.astro",
      "pages/sources/[id]/runs/page/[n].astro",
    ],
    prefer: /^\/sources\/[^/]+\/runs\/$/,
    optional: true,
  },
  {
    id: "source-captures",
    components: [
      "pages/sources/[id]/captures/index.astro",
      "pages/sources/[id]/captures/page/[n].astro",
    ],
    prefer: /^\/sources\/[^/]+\/captures\/$/,
    optional: true,
  },
  {
    id: "source-capture-changes",
    components: [
      "pages/sources/[id]/captures/changes/index.astro",
      "pages/sources/[id]/captures/changes/page/[n].astro",
    ],
    prefer: /^\/sources\/[^/]+\/captures\/changes\/$/,
    optional: true,
  },
  {
    id: "source-versions",
    components: ["pages/sources/[id]/versions/index.astro"],
    prefer: /^\/sources\/[^/]+\/versions\/$/,
    optional: true,
  },
  {
    id: "source-entities",
    components: [
      "pages/sources/[id]/entities/index.astro",
      "pages/sources/[id]/entities/page/[n].astro",
    ],
    prefer: /^\/sources\/[^/]+\/entities\/$/,
    optional: true,
  },
  {
    id: "source-dossiers",
    components: ["pages/sources/[id]/dossiers/index.astro"],
    prefer: /^\/sources\/[^/]+\/dossiers\/$/,
    optional: true,
  },
  {
    id: "source-changelog",
    components: [
      "pages/sources/[id]/changelog/index.astro",
      "pages/sources/[id]/changelog/page/[n].astro",
    ],
    prefer: /^\/sources\/[^/]+\/changelog\/$/,
    optional: true,
  },

  // --------------------------------------------------------------- status --
  { id: "status", components: ["pages/status.astro"], prefer: /^\/status\/$/ },
  {
    id: "status-sources",
    components: ["pages/status/sources/index.astro"],
    prefer: /^\/status\/sources\/$/,
  },
  {
    id: "status-issues",
    components: ["pages/status/issues/index.astro", "pages/status/issues/page/[n].astro"],
    prefer: /^\/status\/issues\/$/,
  },

  // ---------------------------------------------------------------- watch --
  {
    id: "watch-index",
    components: ["pages/watch/index.astro", "pages/watch/page/[n].astro"],
    prefer: /^\/watch\/$/,
  },
  {
    id: "watch-place",
    components: ["pages/watch/place/[...path].astro"],
    prefer: /^\/watch\/place\//,
    optional: true,
  },
  {
    id: "watch-facet",
    components: WATCH_FACET_VARIANTS,
    prefer: /^\/watch\/kind\//,
  },
  {
    id: "watch-item",
    components: ["pages/watch/item/[handle].astro"],
    prefer: /^\/watch\/item\//,
    optional: true,
  },
  {
    id: "watch-history",
    components: ["pages/watch/history/[...path].astro"],
    prefer: /^\/watch\/history\//,
    optional: true,
  },
  {
    id: "watch-feeds",
    components: ["pages/watch/feeds/index.astro"],
    prefer: /^\/watch\/feeds\/$/,
    optional: true,
  },

  // -------------------------------------------------------------- changes --
  {
    id: "changes-index",
    components: ["pages/changes/index.astro"],
    prefer: /^\/changes\/$/,
  },
  {
    id: "changes-feeds",
    components: [
      "pages/changes/feeds/index.astro",
      "pages/changes/feeds/place/page/[n].astro",
      "pages/changes/feeds/source/page/[n].astro",
    ],
    prefer: /^\/changes\/feeds\/$/,
  },

  // -------------------------------------------------------- disagreements --
  {
    id: "disagreements-index",
    components: ["pages/disagreements/index.astro"],
    prefer: /^\/disagreements\/$/,
  },
  {
    id: "disagreements-place",
    components: ["pages/disagreements/place/[...path].astro"],
    prefer: /^\/disagreements\/place\//,
    optional: true,
  },

  // ------------------------------------------------------------------ data --
  { id: "data-index", components: ["pages/data/index.astro"], prefer: /^\/data\/$/ },
  {
    id: "data-dictionary",
    components: ["pages/data/dictionary.astro"],
    prefer: /^\/data\/dictionary\/$/,
  },
  { id: "data-api", components: ["pages/data/api.astro"], prefer: /^\/data\/api\/$/ },

  // ------------------------------------------------------- internal (T3) ---
  // Emitted only under SIG_BUILD_INTERNAL — shot like every other template so
  // the curation surface and the internal harnesses regress loudly too; the
  // gallery sections them apart from the public surface.
  {
    id: "curate-index",
    components: ["internal/curate/index.astro"],
    prefer: /^\/curate\/$/,
    internal: true,
    optional: true,
  },
  {
    id: "curate-tasks",
    components: ["internal/curate/tasks.astro"],
    prefer: /^\/curate\/tasks\/$/,
    internal: true,
    optional: true,
  },
  {
    id: "curate-contradictions",
    components: ["internal/curate/contradictions.astro"],
    prefer: /^\/curate\/contradictions\/$/,
    internal: true,
    optional: true,
  },
  {
    id: "curate-revert",
    components: ["internal/curate/revert.astro"],
    prefer: /^\/curate\/revert\/$/,
    internal: true,
    optional: true,
  },
  {
    id: "curate-submit",
    components: ["internal/curate/submit.astro"],
    prefer: /^\/curate\/submit\/$/,
    internal: true,
    optional: true,
  },
  {
    id: "curate-detail",
    components: ["internal/curate/[id].astro"],
    prefer: /^\/curate\/[^/]+\/$/,
    internal: true,
    optional: true,
  },
  {
    id: "releases",
    components: ["internal/releases/index.astro"],
    prefer: /^\/releases\/$/,
    internal: true,
    optional: true,
  },
  {
    id: "research-dossier-index",
    components: ["internal/research-dossier/index.astro"],
    prefer: /^\/research-dossier\/$/,
    internal: true,
    optional: true,
  },
  {
    id: "research-dossier",
    components: ["internal/research-dossier/[slug].astro"],
    prefer: /^\/research-dossier\/[^/]+\/$/,
    internal: true,
    optional: true,
  },
  {
    id: "contribution-back",
    components: ["internal/contribution-back.astro"],
    prefer: /^\/contribution-back\/$/,
    internal: true,
    optional: true,
  },
  {
    id: "visual-language",
    components: ["internal/visual-language.astro"],
    prefer: /^\/visual-language\/$/,
    internal: true,
    optional: true,
  },
  {
    id: "enhancement-kit",
    components: ["internal/enhancement-kit/index.astro"],
    prefer: /^\/enhancement-kit\/$/,
    internal: true,
    optional: true,
  },
  {
    id: "component-kit",
    components: ["internal/component-kit/index.astro"],
    prefer: /^\/component-kit\/$/,
    internal: true,
    optional: true,
  },
];

/** One manifest row — the field shape this module consumes (dist/page-types.json). */
export interface VisualManifestRoute {
  readonly path: string;
  readonly component: string;
}

export interface RepresentativePick {
  readonly group: VisualTemplateGroup;
  /** The route shot for this group, or null when the build emitted none. */
  readonly path: string | null;
}

/**
 * The deterministic representative for a group on a given manifest: the
 * group's emitted routes sorted, `prefer` matches ranked first (then
 * lexicographic). `null` when none of the group's components emitted a route —
 * the spec records the group `unemitted`, it never invents a page to shoot.
 */
export function selectRepresentative(
  group: VisualTemplateGroup,
  routes: readonly VisualManifestRoute[],
): RepresentativePick {
  const claimed = new Set(group.components);
  const candidates = routes
    .filter((r) => claimed.has(r.component))
    .map((r) => r.path)
    .sort();
  if (candidates.length === 0) return { group, path: null };
  if (group.prefer !== undefined) {
    const preferred = candidates.filter((p) => group.prefer!.test(p));
    if (preferred.length > 0) return { group, path: preferred[0]! };
  }
  return { group, path: candidates[0]! };
}

/** Every component the registry claims — the unit/e2e claim guards consume this. */
export function claimedComponents(
  groups: readonly VisualTemplateGroup[] = VISUAL_TEMPLATE_GROUPS,
): ReadonlyMap<string, string[]> {
  const out = new Map<string, string[]>();
  for (const g of groups) {
    for (const c of g.components) {
      const holders = out.get(c) ?? [];
      holders.push(g.id);
      out.set(c, holders);
    }
  }
  return out;
}
