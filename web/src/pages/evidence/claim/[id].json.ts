// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.60 (EV-02): `/evidence/claim/<id>.json` — the claim viewer's JSON twin
// (`sig.evidence-claim-view/1`): the same ClaimView the HTML page renders,
// document bytes stripped where the lane forbids them (the sealed capture's
// document_text never serialises — §17.5).
import type { APIRoute, GetStaticPaths } from "astro";
import { getEvidence } from "../../../lib/data";
import { claimPaneFor } from "../../../lib/evidence-viewer";
import type { ClaimView } from "../../../lib/evidence-viewer";

export const getStaticPaths: GetStaticPaths = () =>
  getEvidence().claimViews.map((view) => ({
    params: { id: view.claim_id },
    props: { view },
  }));

export const GET: APIRoute = ({ props }) => {
  const { view } = props as { view: ClaimView };
  const pane = claimPaneFor(view);
  const capture = { ...view.capture } as Record<string, unknown>;
  if (pane.kind !== "text_span") delete capture.document_text;
  const body = { schema: "sig.evidence-claim-view/1", pane: pane.kind, ...view, capture };
  return new Response(JSON.stringify(body, null, 2), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
};
