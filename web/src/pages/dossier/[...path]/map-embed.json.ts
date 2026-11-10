// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.29 (K6 VIZ-04, SIG-UI-127): the per-dossier embed-props document —
// `/dossier/<slug>/map-embed.json` — fetched by `<sig-activate>` ONLY after
// the reader's explicit click (never a preload on a T1 page). One route per
// drawn-map dossier, the same island-prop contract `/map/` serialises.
import type { APIRoute, GetStaticPaths } from "astro";
import { buildMapEmbedDoc, embedDossierSlugs } from "../../../lib/map-embed";

export const getStaticPaths: GetStaticPaths = () =>
  embedDossierSlugs().map((slug) => ({ params: { path: slug } }));

export const GET: APIRoute = ({ params }) => {
  const doc = buildMapEmbedDoc(params.path as string);
  return new Response(JSON.stringify(doc), {
    headers: { "content-type": "application/json" },
  });
};
