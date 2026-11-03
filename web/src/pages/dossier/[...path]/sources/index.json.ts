// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.52 (SIG-DSRC-009): the explorer's JSON twin —
// `/dossier/<path>/sources/index.json` serves the `sig.dossier-sources/1`
// artifact verbatim (the release-backed API serves the same data).
import type { APIRoute, GetStaticPaths } from "astro";
import { getDossierSourcesMap } from "../../../../lib/data";
import type { DossierSourcesDoc } from "../../../../lib/dossier-sources";

export const getStaticPaths: GetStaticPaths = () =>
  [...getDossierSourcesMap().entries()].map(([slug, doc]) => ({
    params: { path: slug },
    props: { doc },
  }));

export const GET: APIRoute = ({ props }) => {
  const doc = (props as { doc: DossierSourcesDoc }).doc;
  return new Response(JSON.stringify(doc, null, 2), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
};
