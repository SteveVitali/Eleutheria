// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.59 (K7 WX-04a): the shared route context every watch page builds once —
 * the `sig/watch/2` envelope, the `jkey → slug_path` map (coverage rows +
 * the dossier index + the export's jurisdiction key map), the place display
 * names and the emitted place-page set.
 *
 * Lives in its own module so `watch-v2.ts` stays free of the data seam (and
 * the dossier index types) — `data.ts` already imports `watch-v2`.
 */

import { getDossierIndex, getJurisdictionSlugPaths, getWatchV2 } from "./data";
import { rowName } from "./dossier-index";
import { placePages } from "./watch-v2";
import type { WatchEnvelopeV2, WatchPlacePage } from "./watch-v2";

export interface WatchContext {
  envelope: WatchEnvelopeV2;
  /** Every emitted place page (coverage places + resolved item keys + the
   *  `unplaced` bucket). */
  pages: WatchPlacePage[];
  /** jkey → display name for the pages' headings. */
  names: ReadonlyMap<string, string>;
}

/** The build-time context (called inside `getStaticPaths` / the frontmatter —
 *  build only, never shipped to the client). */
export function watchContext(): WatchContext {
  const envelope = getWatchV2();
  const slugMap = new Map<string, string>();
  const names = new Map<string, string>();
  for (const row of getDossierIndex()) {
    const path = row.slug_path ?? row.slug;
    if (row.jkey && path) slugMap.set(row.jkey, path);
    if (row.jkey) names.set(row.jkey, rowName(row));
  }
  for (const [k, v] of getJurisdictionSlugPaths() ?? []) slugMap.set(k, v);
  for (const p of envelope.coverage?.places ?? []) {
    if (p.key && p.slug) slugMap.set(p.key, p.slug);
  }
  return { envelope, pages: placePages(envelope, slugMap, names), names };
}
