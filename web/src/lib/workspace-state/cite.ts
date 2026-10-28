// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.21 (SIG-UI-059/093, J3 §8.1; K0 §4.5; ADR-155) — "cite this view":
 * the snapshot-pinned form `/s/<pub>/<surface>/?v=2&…` a durable link mints,
 * plus the indexing policy every parameterised T2 URL carries.
 *
 * Posture (recorded in ADR-225):
 *
 * - The minted form is a SNAPSHOT route. TX-13b has not landed — `/s/<pub>/`
 *   does not resolve on this build — so the affordance shows the minted form
 *   as copyable text with J3 §8.1's interim sentence, never a dead `<a>`.
 *   The link flips to an anchor when the snapshot rows land.
 * - A static page cannot emit different `<head>` markup per query string, so
 *   every T2 document carries `robots` `noindex,follow` and the canonical
 *   link to the base surface unconditionally. The sitemap (T0/T1 routes
 *   only, generated from the page-type registry) is the indexing surface —
 *   the T2 explore views were never canonical content for the index anyway.
 */

import {
  SURFACE_PATHS,
  SURFACE_VIEW,
  WORKSPACE_STATE2_VERSION,
  type WorkspaceSurface,
} from "./registry";
import {
  serializeWorkspaceState2,
  toWireState,
  type IslandWorkspaceState,
} from "./state";

/**
 * The robots directive every T2 surface emits — `noindex,follow` (K13 §2.5:
 * parameterised T2 URLs are never the canonical indexable copy; crawlers may
 * still follow the record links out). Emitted unconditionally on the static
 * T2 document — see the module header for why the split is at page type,
 * not per-query-string.
 */
export const T2_ROBOTS_CONTENT = "noindex,follow";

/**
 * Mint the snapshot-pinned cite-this-view form: `/s/<pub>/<surface>/?v=2&…`
 * with the caller's state serialised. `surface` resolves its route through
 * the registry (`/map/`, `/network/`, `/search/`), so a later route rename
 * (GX-09a's `/explore/`) lands here in one place. `state` may be null for
 * the static affordance, which mints the base form.
 */
export function citeViewHref(
  publicationId: string,
  surface: WorkspaceSurface,
  state: IslandWorkspaceState | null,
): string {
  const base = `/s/${publicationId}${SURFACE_PATHS[surface]}`;
  if (!state) {
    return `${base}?v=${WORKSPACE_STATE2_VERSION}`;
  }
  // The minted view names THIS surface — a cite never pretends the state
  // belongs to a different surface than the page it was minted on.
  const wire = { ...toWireState(state), view: SURFACE_VIEW[surface] };
  const serialised = serializeWorkspaceState2(wire);
  return serialised ? `${base}?${serialised}` : base;
}

/**
 * J3 §8.1's interim sentence for the cite affordance — the snapshot route
 * the minted form names is not published yet (TX-13b's row), so the
 * affordance says exactly that rather than pretend the link resolves.
 * Agent-drafted wording, labelled; when TX-13b lands, this is replaced by
 * the snapshot's own citation block. Deliberately names no publication id in
 * plain text — the id is a 64-hex identifier and public text never carries
 * an ungrouped digit run (K14 NEW-8); the minted form inside <code> shows it.
 */
export const INTERIM_CITE_VIEW_TEXT =
  "The pinned form resolves when the release publishes its site snapshot; " +
  "this page is the latest view — an immutable citable copy is not yet published.";

/** The affordance text when no release is bound to the build — honest, no dead link. */
export const CITE_VIEW_UNBOUND =
  "Cite this view is unavailable on this build — no release is bound, so no pinned form exists.";
