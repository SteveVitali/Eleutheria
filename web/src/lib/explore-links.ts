// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.57 (VIZ-03, SIG-UI-055/126; cites SIG-UI-059/060) — the explore-bar and
 * "Show on the map" link minter. Every sideways link off a dossier (or off a
 * dossier's source rows) is minted through `sig.workspace-state/2` here, so
 * the wire form is canonical by construction (registry order, `v=2`, the
 * registered `view=` value) and the target surface's facet-conformance
 * harness decides what it applies — a facet the target cannot apply earns
 * its visible unapplied-facet notice there (SIG-UI-060), never a silently
 * dropped scope.
 *
 * - `exploreLinks(jkey)` — the dossier explore bar's three links: the map,
 *   the graph explorer and the scoped search, each carrying the dossier's
 *   canonical jurisdiction key (SIG-UI-126's "for its jurisdiction"). An
 *   unkeyed dossier mints the same links without the facet — the link never
 *   invents a key.
 * - `showOnMapHref(jkey, sourceId)` / `sourceRecordsHref(...)` — K5 §5.5's
 *   per-source-row control on the sources explorer: the scoped map link
 *   plus the no-JS records list on the release-pinned federated route
 *   (`type=record&jurisdiction=<jkey>&source=<id>&format=html`, K3 SRCH-04).
 *   The in-place Figure-1 activation half is VIZ-04's — the links are the
 *   complete variant today.
 */

import {
  DEFAULT_WORKSPACE_STATE2,
  SURFACE_PATHS,
  serializeWorkspaceState2,
  type WorkspaceViewValue,
} from "./workspace-state/index";

export interface ExploreLinks {
  map: string;
  graph: string;
  search: string;
}

/** Serialise `v=2&view=<view>` plus the caller's facets against `surface`'s path. */
function surfaceHref(
  surface: keyof typeof SURFACE_PATHS,
  view: WorkspaceViewValue,
  facets: Partial<typeof DEFAULT_WORKSPACE_STATE2>,
): string {
  const qs = serializeWorkspaceState2({
    ...DEFAULT_WORKSPACE_STATE2,
    view,
    ...facets,
  });
  return `${SURFACE_PATHS[surface]}?${qs}`;
}

/**
 * The dossier explore bar (K13 §3 "Explore bar (map · graph · search within)";
 * K14 §4.6 "`jurisdiction=` / `focus=`"). `jurisdiction` is the one facet the
 * dossier owns — the registry's descendants-inclusive filter (SIG-UI-059).
 * Each target names what it cannot apply: the links are emitted on every
 * keyed dossier, and the notice is the target's, per SIG-UI-126.
 */
export function exploreLinks(jkey: string | null): ExploreLinks {
  const facets = jkey ? { jurisdiction: [jkey] } : {};
  return {
    map: surfaceHref("map", "map", facets),
    graph: surfaceHref("graph", "graph", facets),
    search: surfaceHref("search", "list", facets),
  };
}

/**
 * The scoped `/map/` half of K5 §5.5's "Show on the map" control — the map
 * surface receives `jurisdiction` + `source`; whichever it does not apply is
 * visibly named on arrival (the conformance harness), never silently dropped.
 */
export function showOnMapHref(jkey: string | null, sourceId: string): string {
  return surfaceHref("map", "map", {
    ...(jkey ? { jurisdiction: [jkey] } : {}),
    source: [sourceId],
  });
}

/**
 * The no-JS records list half of the same control — a plain GET on the
 * release-pinned federated search route (the same route the scoped-search
 * forms post to): `type=record` plus the scope facets plus `format=html`
 * (K3 SRCH-04's server-rendered results page). `federatedSearchHref` is the
 * build's release target — `null` only when no release is activated, and the
 * caller renders the named absence instead of minting a dead link.
 */
export function sourceRecordsHref(
  federatedSearchHref: string,
  jkey: string | null,
  sourceId: string,
): string {
  const params = new URLSearchParams({ type: "record", format: "html" });
  if (jkey) params.set("jurisdiction", jkey);
  params.set("source", sourceId);
  return `${federatedSearchHref}?${params.toString()}`;
}
