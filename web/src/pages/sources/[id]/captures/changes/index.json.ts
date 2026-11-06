// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.69 (UX10-3b, K10 §3): `/sources/<id>/captures/changes/index.json` —
// the changes list's twin: the record-set-changed `sig.capture-record/1` rows.
import type { APIRoute, GetStaticPaths } from "astro";
import { resolveSourceId } from "../../../../../lib/alias";
import { getPageBIds, getSourceCaptures, changedCaptures } from "../../../../../lib/source-page-b";

export const getStaticPaths: GetStaticPaths = () =>
  getPageBIds().map((id) => ({ params: { id } }));

export const GET: APIRoute = ({ params }) => {
  const id = resolveSourceId(String(params.id ?? "")) ?? "";
  const rows = changedCaptures(getSourceCaptures(id) ?? []);
  return new Response(
    JSON.stringify(
      { schema: "sig.source-captures/1", source_id: id, view: "changes", capture_count: rows.length, captures: rows },
      null,
      2,
    ) + "\n",
    { headers: { "content-type": "application/json; charset=utf-8" } },
  );
};
