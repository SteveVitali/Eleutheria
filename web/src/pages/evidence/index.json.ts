// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.60 (EV-02): `/evidence/index.json` — the hub's JSON twin
// (`sig.evidence-index/1`): the roll-up counts + the artifact index rows the
// browse table renders (handle, title, source, type, state, lane, captures).
import type { APIRoute } from "astro";
import {
  artifactHandles,
  artifactState,
  artifactTitle,
  byArtifactIndex,
  capturesOf,
  evidenceRollup,
} from "../../lib/evidence-hub";
import { getEvidence } from "../../lib/data";

export const GET: APIRoute = () => {
  const { artifacts, claimViews } = getEvidence();
  const handles = artifactHandles(artifacts);
  const roll = evidenceRollup(artifacts);
  const body = {
    schema: "sig.evidence-index/1",
    artifacts: [...artifacts].sort(byArtifactIndex).map((a) => ({
      handle: handles.get(a.artifact_id)!,
      artifact_id: a.artifact_id,
      title: artifactTitle(a),
      source: a.source,
      source_name: a.source_name ?? null,
      artifact_type: a.artifact_type,
      state: artifactState(a),
      lane: a.lane ?? null,
      capture_status: a.capture_status,
      captures: capturesOf(a).length,
      place_key: a.place_key ?? null,
    })),
    claim_views: claimViews.map((v) => v.claim_id),
    rollup: {
      artifacts: roll.artifacts,
      run_records: roll.runRecords,
      captures: roll.capturesRecorded,
      captures_with_bytes: roll.capturesWithBytes,
    },
  };
  return new Response(JSON.stringify(body, null, 2), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
};
