// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.27 (K2 GX-09b, `sig.entity-twins/1`): the per-entity twin manifest —
// `/entity/<type>/<key>/index.json`, the machine-readable index of the
// compartment `sig.entity-page/1` twin files this release emitted for the
// entity (`index.<comp>.json`). The explorer's expansion and search-to-node
// fetch it so an ego load never guesses a compartment filename and never
// follows a dead fetch — an entity with no emitted twin answers 404, which
// the island reports as the typed "no machine-readable twin" state.
import type { APIRoute, GetStaticPaths } from "astro";
import { getEntityLabelRows, getEntityPageTwins } from "../../../../lib/data";
import { entityIndex } from "../../../../lib/entity-page";

export const getStaticPaths: GetStaticPaths = () => {
  const index = entityIndex(getEntityLabelRows());
  const paths: { params: { type: string; key: string } }[] = [];
  for (const row of index.rows) {
    const key = `${row.slug}--${row.hash}`;
    if (getEntityPageTwins(row.url_type!, key).length > 0) {
      paths.push({ params: { type: row.url_type!, key } });
    }
  }
  return paths;
};

export const GET: APIRoute = ({ params }) => {
  const key = params.key ?? "";
  const twins = getEntityPageTwins(params.type ?? "", key);
  const doc = {
    schema: "sig.entity-twins/1",
    key,
    twins: twins.map((t) => ({
      compartment: t.compartment,
      path: `index.${t.compartment}.json`,
    })),
  };
  return new Response(`${JSON.stringify(doc, null, 2)}\n`, {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
};
