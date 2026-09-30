// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The exportable evidence citation list (SIG-UI-027c): the recommender's ranked
// output as a plain-text list with belief-pinned permalinks and as-of dates, suitable
// for attaching to public comment. Static-first (SIG-UI-036): emitted at build time.
import type { APIRoute } from "astro";
import { citationListText, recommendEvidence } from "../../lib/recommender";
import { getEvidence, getDecisionPoint } from "../../lib/data";

// The ranked evidence + decision point flow through the single data seam (ADR-066).
const EVIDENCE_ARTIFACTS = getEvidence().artifacts;
const DECISION_POINT = getDecisionPoint();

export const GET: APIRoute = () => {
  // No tracked decision in a real-data build yet (P30.3): an honest empty list, never a demo.
  const body = DECISION_POINT
    ? citationListText(recommendEvidence(EVIDENCE_ARTIFACTS, DECISION_POINT), DECISION_POINT)
    : "No upcoming decision is tracked yet, so no evidence is ranked (a gap, not an absence).\n";
  return new Response(body, {
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
};
