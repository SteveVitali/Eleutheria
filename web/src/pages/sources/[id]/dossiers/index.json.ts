// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.69 (UX10-3b): `/sources/<id>/dossiers/index.json` — the contribution
// table's twin: the shared `sig.source-dossier-contribution/1` rows.
import type { APIRoute, GetStaticPaths } from "astro";
import { getSourcePage } from "../../../../lib/source-page";
import { resolveSourceId } from "../../../../lib/alias";
import { getPageBIds } from "../../../../lib/source-page-b";

export const getStaticPaths: GetStaticPaths = () =>
  getPageBIds()
    .filter((id) => ((getSourcePage(id)?.row.contributions ?? []).length > 0))
    .map((id) => ({ params: { id } }));

export const GET: APIRoute = ({ params }) => {
  const id = resolveSourceId(String(params.id ?? "")) ?? "";
  const contributions = getSourcePage(id)?.row.contributions ?? [];
  return new Response(
    JSON.stringify(
      { schema: "sig.source-dossier-contributions/1", source_id: id, contributions },
      null,
      2,
    ) + "\n",
    { headers: { "content-type": "application/json; charset=utf-8" } },
  );
};
