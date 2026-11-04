// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.60 (EV-02): `/evidence/artifact/<handle>.json` — the artifact page's
// JSON twin (`sig.evidence-artifact-page/1`): the same fields the HTML page
// renders — handle, title, source, lane, upstream, captures (metadata only),
// claims supported and the contradiction ids.
import type { APIRoute, GetStaticPaths } from "astro";
import {
  artifactContradictions,
  artifactHandles,
  artifactState,
  artifactTitle,
  capturesOf,
  claimsForArtifact,
} from "../../../lib/evidence-hub";
import { getEvidence, getStatementIndex } from "../../../lib/data";
import type { EvidenceArtifact } from "../../../lib/recommender";

export const getStaticPaths: GetStaticPaths = () => {
  const { artifacts } = getEvidence();
  const handles = artifactHandles(artifacts);
  return artifacts.map((a) => ({
    params: { handle: handles.get(a.artifact_id)! },
    props: { artifact: a, handle: handles.get(a.artifact_id)! },
  }));
};

export const GET: APIRoute = ({ props }) => {
  const { artifact: a, handle } = props as { artifact: EvidenceArtifact; handle: string };
  const statements = getStatementIndex();
  const claims = claimsForArtifact(statements, a.artifact_id);
  const body = {
    schema: "sig.evidence-artifact-page/1",
    handle,
    artifact_id: a.artifact_id,
    title: artifactTitle(a),
    source: a.source,
    source_name: a.source_name ?? null,
    artifact_type: a.artifact_type,
    capture_status: a.capture_status,
    capture_classification: a.capture_classification ?? null,
    state: artifactState(a),
    lane: a.lane ?? null,
    lane_basis: a.lane_basis ?? null,
    place_key: a.place_key ?? null,
    upstream: a.upstream ?? (a.upstream_url ? { status: "full_url", url: a.upstream_url } : null),
    captures: capturesOf(a).map(({ fields: _fields, ...c }) => c),
    claims_supported: claims.map((s) => ({
      claim_id: s.claim_id,
      predicate_id: s.predicate_id ?? null,
    })),
    contradictions: artifactContradictions(statements, a.artifact_id),
    as_of: a.as_of,
  };
  return new Response(JSON.stringify(body, null, 2), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
};
