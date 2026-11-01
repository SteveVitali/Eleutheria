// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.42a (K2 GX-06a §4.2 row 12): the entity page's JSON twin download —
// `/entity/<type>/<key>/index.<comp>.json`, the `sig.entity-page/1` document
// the page renders. One route per (type, key, compartment) the data layer
// emits; fixtures and export mode serve the same bytes the release carries
// (the export's `web/entity/…/index.<comp>.json` artifact).
import type { APIRoute, GetStaticPaths } from "astro";
import { getEntityLabelRows, getEntityPageTwins } from "../../../../lib/data";
import { entityIndex } from "../../../../lib/entity-page";

export const getStaticPaths: GetStaticPaths = () => {
  const index = entityIndex(getEntityLabelRows());
  const paths: { params: { type: string; key: string; comp: string } }[] = [];
  for (const row of index.rows) {
    const key = `${row.slug}--${row.hash}`;
    for (const twin of getEntityPageTwins(row.url_type!, key)) {
      paths.push({
        params: { type: row.url_type!, key, comp: twin.compartment },
      });
    }
  }
  return paths;
};

export const GET: APIRoute = ({ params }) => {
  const twins = getEntityPageTwins(params.type ?? "", params.key ?? "");
  const twin = twins.find((t) => t.compartment === params.comp);
  return new Response(`${JSON.stringify(twin ?? { schema: "sig.entity-page/1" }, null, 2)}\n`, {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
};
