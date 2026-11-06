// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.69 (UX10-3b): `/sources/<id>/versions/index.json` — the versions
// page's machine twin: the `sig.source-versions/1` document verbatim.
import type { APIRoute, GetStaticPaths } from "astro";
import { resolveSourceId } from "../../../../lib/alias";
import { getPageBIds, getSourceVersions } from "../../../../lib/source-page-b";

export const getStaticPaths: GetStaticPaths = () =>
  getPageBIds().filter((id) => getSourceVersions(id) !== null).map((id) => ({ params: { id } }));

export const GET: APIRoute = ({ params }) => {
  const id = resolveSourceId(String(params.id ?? "")) ?? "";
  return new Response(JSON.stringify(getSourceVersions(id), null, 2) + "\n", {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
};
