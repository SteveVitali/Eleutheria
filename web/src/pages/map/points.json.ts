// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The opt-in map island's points, emitted at build time as a static file at
// /map/points.json (P30.3, ADR-106). At national scale the located records would put
// tens of MB into the /map/ HTML as island props; the island instead fetches this file
// when (and only when) JavaScript runs. The data flows through the single data seam
// (ADR-066) — the same tier-reduced `locatable` set the page's tabular equivalent
// renders (§19.4, SIG-UI-050) — and carries the OpenStreetMap attribution (§42.3).
import type { APIRoute } from "astro";
import { getMapSites } from "../../lib/data";
import { encodeIslandPoints } from "../../lib/map";
import { MAP_ATTRIBUTION_LINE } from "../../lib/map-tiles";

export const GET: APIRoute = () => {
  const payload = encodeIslandPoints(getMapSites(), MAP_ATTRIBUTION_LINE);
  return new Response(JSON.stringify(payload), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
};
