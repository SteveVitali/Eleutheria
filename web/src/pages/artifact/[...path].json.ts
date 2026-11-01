// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P35.37 (SIG-TRANSP-013, J3 §5.4): `/artifact/<export-path>.json` — the
// downloadable form of a figure-addressable release artifact. Every <Figure>'s
// "source" link resolves here: the route serves the SAME bytes the data layer
// surfaces (the "downloadable file that recomputes it" in the J3 §5.4 headline
// row) — fixtures mode serialises the data-layer payloads; export mode would
// serve the export's own bytes. A path that is not a figure-addressable
// artifact emits no route (404), so the link set and the artifact set can
// never drift.
import type { APIRoute, GetStaticPaths } from "astro";
import { fixtureArtifactPaths } from "../../lib/figures";
import { getReleaseArtifactPayload } from "../../lib/data";
import { getSourcePageIds } from "../../lib/source-page";

// One pre-rendered route per figure-addressable artifact. The committed list
// (figure-artifacts.json) is the fixture manifest; in export mode the same
// allow-list bounds what the route serves — compartment row streams stay
// bundle-download territory, not page-served JSON. P36.48: the per-source
// `transparency/sources/<id>/executions.jsonl` feeds the table's run-cell
// figures point at — enumerated per source like the slug-bound paths.
export const getStaticPaths: GetStaticPaths = () =>
  [
    ...fixtureArtifactPaths(),
    ...getSourcePageIds().map(
      (id) => `transparency/sources/${id}/executions.jsonl`,
    ),
  ]
    .filter((p) => getReleaseArtifactPayload(p) !== null)
    .map((p) => ({
      // Route is `artifact/[...path].json` → params.path drops the suffix:
      // `web/coverage.json` → `web/coverage`. A `.jsonl` stream serves at
      // the `.json` twin path (the emitted JSON array of its rows).
      params: { path: p.replace(/\.jsonl$/, "").replace(/\.json$/, "") },
      props: { artifactPath: p },
    }));

export const GET: APIRoute = ({ props }) => {
  const { artifactPath } = props as { artifactPath: string };
  const payload = getReleaseArtifactPayload(artifactPath);
  if (payload === null) {
    return new Response("not a figure-addressable artifact", { status: 404 });
  }
  return new Response(JSON.stringify(payload, null, 2) + "\n", {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
};
