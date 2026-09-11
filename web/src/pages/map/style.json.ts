// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The public map's MapLibre GL style, served as a static file at /map/style.json
// (SIG-UI-038, SIG-GEO-012/013). The shell is static-first (SIG-UI-036): this is
// emitted at build time, not from a live tile server. Its sources are self-hosted
// static PMTiles v3 archives with OSM attribution and NO third-party tile CDN — the
// serving contract a MapLibre renderer consumes. `assertServingContract` runs at
// build so an edit that breaks the contract fails the build, not just the tests.
import type { APIRoute } from "astro";
import { PUBLIC_MAP_STYLE, assertServingContract } from "../../lib/map-tiles";

export const GET: APIRoute = () => {
  assertServingContract(PUBLIC_MAP_STYLE);
  return new Response(JSON.stringify(PUBLIC_MAP_STYLE, null, 2), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
};
