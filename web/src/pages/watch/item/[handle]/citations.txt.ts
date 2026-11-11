// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.30 (K7 §5.7, SIG-UI-027c): the per-item exportable citation list — the
// subject-scoped recommender's ranked output as plain text with permalinks
// and as-of dates, suitable for attaching to public comment. Static-first:
// emitted at build time; a non-finite score fails the build, never a zero.
import type { APIRoute, GetStaticPaths } from "astro";
import { citationListText, recommendEvidence } from "../../../../lib/recommender";
import { getEvidence, getDecisionPoints, getWatchV2 } from "../../../../lib/data";
import { watchDecisionPoint } from "../../../../lib/watch-v2";
import type { WatchItemV2 } from "../../../../lib/watch-v2";

export const getStaticPaths: GetStaticPaths = () =>
  getWatchV2().items.map((item) => ({ params: { handle: item.handle }, props: { item } }));

const EVIDENCE = getEvidence();
const POINTS = getDecisionPoints();

export const GET: APIRoute = ({ props }) => {
  const item = props.item as WatchItemV2;
  const decision = POINTS.get(item.handle) ?? watchDecisionPoint(item);
  const ranked = recommendEvidence(EVIDENCE.artifacts, decision, EVIDENCE.subjectNeighbours);
  const body =
    ranked.length > 0
      ? citationListText(ranked, decision)
      : `Evidence for: ${item.title}\n` +
        "No published evidence artifact is scored for this item's subject in this release.\n";
  return new Response(body, {
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
};
