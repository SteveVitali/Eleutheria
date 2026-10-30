// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.34 repair (JUR-04 / ADR-155): `/search/index.json` — the quick-filter
// island's dossier rows, fetched on mount instead of riding the serialized
// island props. The dossier index is the filter's one unbounded list (the
// grouped `sig.dossier-index/2` corpus; thousands of rows at real scale) and
// serialized props land in the T2 document the wire budget measures raw —
// the bounded rows (≤ 200 capped sites, the sources) stay serialized. The
// mapping lives in lib/search-index so this document and the page's model
// can never drift; the no-JS path is unchanged — the release-pinned GET
// forms and the static browse index enumerate every dossier without it.
import type { APIRoute } from "astro";
import { dossierSearchItems, SEARCH_INDEX_SCHEMA } from "../../lib/search-index";

export const GET: APIRoute = () =>
  new Response(
    `${JSON.stringify({ schema: SEARCH_INDEX_SCHEMA, items: dossierSearchItems() }, null, 2)}\n`,
    { headers: { "content-type": "application/json; charset=utf-8" } },
  );
