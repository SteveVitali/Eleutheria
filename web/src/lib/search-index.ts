// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.34 repair (JUR-04 / ADR-155): the search island's DOSSIER rows ride a
// fetched endpoint (`/search/index.json`, `sig.search-index/1`), never the
// serialized island props — the dossier index is the one UNBOUNDED list the
// quick filter names (the grouped `sig.dossier-index/2` corpus landed here,
// and a real-scale keyed index is thousands of rows), and every serialized
// prop row lands in the T2 document the wire budget measures raw. The bounded
// lists — the ≤ 200 capped sites and the source rows — stay serialized with
// the island. This module is the one mapping `search.astro` and the endpoint
// share so the emitted rows and the props contract can never drift.

import { getDossierIndex } from "./data";
import { dossierPath } from "./dossier";
import { displayJurisdiction, dossierDisplayTitle } from "./jurisdictions";

/** The emitted document's schema id. */
export const SEARCH_INDEX_SCHEMA = "sig.search-index/1" as const;

/** One dossier row of the listed index — the SearchIsland `SearchItem` shape. */
export interface DossierSearchItem {
  kind: "dossier";
  label: string;
  sublabel: string;
  href: string;
}

/**
 * The dossier items the quick filter lists — identical rows whether the page
 * serializes them or the island fetches `/search/index.json`. P34.14 (QW-8,
 * F-105): labels lead with the place's NAME, the code stays secondary.
 */
export function dossierSearchItems(): DossierSearchItem[] {
  return getDossierIndex().map((d) => ({
    kind: "dossier",
    label: dossierDisplayTitle(d.subject_label, d.jurisdiction),
    sublabel: d.display_name ?? d.name ?? displayJurisdiction(d.jurisdiction).label,
    href: dossierPath(d.slug),
  }));
}
