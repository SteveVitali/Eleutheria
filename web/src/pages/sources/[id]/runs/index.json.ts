// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.69 (UX10-3b, K10 §3): `/sources/<id>/runs/index.json` — the runs
// page's machine twin: the source's `sig.execution-record/1` rows (the
// same rows the release's per-source `executions.jsonl` carries).
import type { APIRoute, GetStaticPaths } from "astro";
import { getSourcePage, type SourcePageModel } from "../../../../lib/source-page";
import { resolveSourceId } from "../../../../lib/alias";
import { getPageBIds } from "../../../../lib/source-page-b";

export const getStaticPaths: GetStaticPaths = () =>
  getPageBIds().map((id) => ({ params: { id } }));

export const GET: APIRoute = ({ params }) => {
  const id = resolveSourceId(String(params.id ?? "")) ?? "";
  const model = getSourcePage(id) as SourcePageModel | null;
  const executions = [...(model?.executions ?? [])].sort((a, b) =>
    String(b.started_at ?? b.finished_at ?? "").localeCompare(String(a.started_at ?? a.finished_at ?? "")),
  );
  return new Response(
    JSON.stringify(
      {
        schema: "sig.source-runs/1",
        source_id: id,
        execution_count: executions.length,
        executions,
      },
      null,
      2,
    ) + "\n",
    { headers: { "content-type": "application/json; charset=utf-8" } },
  );
};
