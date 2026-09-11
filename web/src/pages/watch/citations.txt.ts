// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The exportable evidence citation list (SIG-UI-027c): the recommender's ranked
// output as a plain-text list with belief-pinned permalinks and as-of dates, suitable
// for attaching to public comment. Static-first (SIG-UI-036): emitted at build time.
import type { APIRoute } from "astro";
import { citationListText, recommendEvidence } from "../../lib/recommender";
import { DECISION_POINT, EVIDENCE_ARTIFACTS } from "../../lib/watch-evidence-fixture";

export const GET: APIRoute = () => {
  const ranked = recommendEvidence(EVIDENCE_ARTIFACTS, DECISION_POINT);
  const body = citationListText(ranked, DECISION_POINT);
  return new Response(body, {
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
};
