// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.69 (UX10-3b): `/sources/<id>/entities/index.json` — the entity
// browse's machine twin (`sig.source-entities/1` — total + cap + rows).
import type { APIRoute, GetStaticPaths } from "astro";
import { resolveSourceId } from "../../../../lib/alias";
import { getPageBIds, getSourceEntities, entityBrowse, ENTITY_BROWSE_CAP } from "../../../../lib/source-page-b";

export const getStaticPaths: GetStaticPaths = () =>
  getPageBIds().filter((id) => getSourceEntities(id).length > 0).map((id) => ({ params: { id } }));

export const GET: APIRoute = ({ params }) => {
  const id = resolveSourceId(String(params.id ?? "")) ?? "";
  const browse = entityBrowse(getSourceEntities(id));
  return new Response(
    JSON.stringify(
      {
        schema: "sig.source-entities/1",
        source_id: id,
        total: browse.total,
        shown: browse.rows.length,
        cap: ENTITY_BROWSE_CAP,
        capped: browse.capped,
        entities: browse.rows,
      },
      null,
      2,
    ) + "\n",
    { headers: { "content-type": "application/json; charset=utf-8" } },
  );
};
