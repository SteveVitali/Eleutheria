// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.62 (K11 RQ-03b / SIG-RQ-002): `/task/<handle>.json` — the task page's
// JSON twin (`sig.task-page/1`): the same fields the HTML page renders —
// handle, title, type, status line, subject + place, the four spec fields,
// predicates, dispositions, trigger, history and the related handles.
import type { APIRoute, GetStaticPaths } from "astro";
import {
  getJurisdictionClaims,
  getQueueAsOf,
  getRecordsRequestDrafts,
  getResearchQueue,
} from "../../lib/data";
import { claimStatusFor, type ResearchTaskCard } from "../../lib/research-queue";
import { relatedTasks, taskPageTwin } from "../../lib/task-page";
import { draftForTask } from "../../lib/records-drafts";

export const getStaticPaths: GetStaticPaths = () => {
  return getResearchQueue()
    .filter((c) => c.handle)
    .map((card) => ({ params: { handle: card.handle! }, props: { card } }));
};

export const GET: APIRoute = ({ props }) => {
  const { card } = props as { card: ResearchTaskCard };
  const claim = claimStatusFor(card, getJurisdictionClaims(), getQueueAsOf());
  const related = relatedTasks(card, getResearchQueue());
  const body = taskPageTwin(card, {
    claimedBy: claim.claimed_by,
    related,
    draft: draftForTask(card, getRecordsRequestDrafts()),
  });
  return new Response(JSON.stringify(body, null, 2) + "\n", {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
};
