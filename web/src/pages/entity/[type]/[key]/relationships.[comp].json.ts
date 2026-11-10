// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.23 (K2 GX-06b §4.2 row 12): the entity's relationships JSON download —
// `/entity/<type>/<key>/relationships.<comp>.json`, the
// `sig.entity-relationships/1` slice the twin's downloads row names (K13
// R-6: a named download is never a dead link). Export mode serves the
// emitted artifact verbatim; fixtures serve the derived fixture bytes.
import type { APIRoute, GetStaticPaths } from "astro";
import { getEntityDownloadBytes, getEntityLabelRows, getEntityPageTwins } from "../../../../lib/data";
import { entityIndex } from "../../../../lib/entity-page";

export const getStaticPaths: GetStaticPaths = () => {
  const index = entityIndex(getEntityLabelRows());
  const paths: { params: { type: string; key: string; comp: string } }[] = [];
  for (const row of index.rows) {
    const key = `${row.slug}--${row.hash}`;
    for (const twin of getEntityPageTwins(row.url_type!, key)) {
      paths.push({ params: { type: row.url_type!, key, comp: twin.compartment } });
    }
  }
  return paths;
};

export const GET: APIRoute = ({ params }) => {
  const file = `relationships.${params.comp}.json`;
  const bytes = getEntityDownloadBytes(params.type ?? "", params.key ?? "", file);
  if (bytes === null) return new Response("not found", { status: 404 });
  return new Response(bytes, {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
};
