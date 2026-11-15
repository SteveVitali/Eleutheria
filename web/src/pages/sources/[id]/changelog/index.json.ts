// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.41 (UX10-4, K10 §16.1): `/sources/<id>/changelog/index.json` — the
// changelog page's machine twin: the `sig.source-changelog/1` document
// verbatim (every event; the HTML paginates for display only).
import type { APIRoute, GetStaticPaths } from "astro";
import { resolveSourceId } from "../../../../lib/alias";
import { getSourceChangelog } from "../../../../lib/source-changelog";
import { getPageBIds } from "../../../../lib/source-page-b";

export const getStaticPaths: GetStaticPaths = () =>
  getPageBIds().map((id) => ({ params: { id } }));

export const GET: APIRoute = ({ params }) => {
  const id = resolveSourceId(String(params.id ?? "")) ?? "";
  const doc = getSourceChangelog(id);
  if (doc === null) return new Response("not found", { status: 404 });
  return new Response(JSON.stringify(doc, null, 2) + "\n", {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
};
