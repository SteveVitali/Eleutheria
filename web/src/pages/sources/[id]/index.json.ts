// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.69 (UX10-3b, K10 §3/§16.1): `/sources/<id>/index.json` — the source
// page's machine twin (`sig.source-page/2`): the publish-scrubbed
// `sig.source-row/1` row verbatim plus section summaries and the sub-route
// links — the same model the HTML page renders.
import type { APIRoute, GetStaticPaths } from "astro";
import { getSourcePage, getSourcePageIds, type SourcePageModel } from "../../../lib/source-page";
import { resolveSourceId } from "../../../lib/alias";
import {
  getSourceCaptures,
  getSourceVersions,
  getSourceEntities,
  sortedCaptures,
} from "../../../lib/source-page-b";
import { issuesForSource, getIssues } from "../../../lib/issues";
import { getSourceChangelog } from "../../../lib/source-changelog";

export const getStaticPaths: GetStaticPaths = () =>
  getSourcePageIds().map((id) => ({ params: { id } }));

export const GET: APIRoute = ({ params }) => {
  const id = resolveSourceId(String(params.id ?? "")) ?? "";
  const model = getSourcePage(id) as SourcePageModel | null;
  if (model === null) {
    return new Response("not found", { status: 404 });
  }
  const executions = [...(model.executions ?? [])].sort((a, b) =>
    String(b.started_at ?? b.finished_at ?? "").localeCompare(String(a.started_at ?? a.finished_at ?? "")),
  );
  const captures = sortedCaptures(getSourceCaptures(id) ?? []);
  const versions = getSourceVersions(id);
  const entities = getSourceEntities(id);
  const openIssues = issuesForSource(getIssues(), id).filter((i) => i.closed_at === null);
  const links = model.registryOnly
    ? {}
    : {
        runs: `sources/${id}/runs/`,
        captures: captures.length > 0 ? `sources/${id}/captures/` : null,
        changes: captures.some((c) => c.changed_vs_prior === "changed") ? `sources/${id}/captures/changes/` : null,
        versions: versions !== null ? `sources/${id}/versions/` : null,
        entities: entities.length > 0 ? `sources/${id}/entities/` : null,
        dossiers: (model.row.contributions ?? []).length > 0 ? `sources/${id}/dossiers/` : null,
        changelog: `sources/${id}/changelog/`,
      };
  const changelog = model.registryOnly ? null : getSourceChangelog(id);
  return new Response(
    JSON.stringify(
      {
        schema: "sig.source-page/2",
        source_id: id,
        registry_only: model.registryOnly,
        row: model.row,
        latest_executions: executions.slice(0, 20),
        latest_captures: captures.slice(0, 20),
        versions: versions === null
          ? null
          : { entry_count: versions.entry_count, latest: versions.entries[versions.entries.length - 1] ?? null },
        contributions: model.row.contributions ?? [],
        open_issues: openIssues.length,
        changelog:
          changelog === null
            ? null
            : {
                event_count: changelog.event_count,
                baseline_label: changelog.baseline_label,
                latest: changelog.events.slice(-10),
              },
        links,
      },
      null,
      2,
    ) + "\n",
    { headers: { "content-type": "application/json; charset=utf-8" } },
  );
};
