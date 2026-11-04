// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.63 (K11 RQ-04 / SIG-RQ-007): `/task/<handle>.draft.txt` — the task's
// records-request draft as a downloadable plain-text document. DRAFT, NEVER
// SEND: the file is a document the filer may send by hand — this endpoint is
// a static file emit, never a transmit path (ADR-171). A task with no
// persisted draft mints no file (fail closed, SIG-ENG-042).
import type { APIRoute } from "astro";
import { getRecordsRequestDrafts, getResearchQueue } from "../../lib/data";
import type { ResearchTaskCard } from "../../lib/research-queue";
import { draftForTask, draftTxt } from "../../lib/records-drafts";

interface Props {
  card: ResearchTaskCard;
  body: string;
}

export function getStaticPaths() {
  const drafts = getRecordsRequestDrafts();
  const out: { params: { handle: string }; props: Props }[] = [];
  for (const card of getResearchQueue()) {
    if (!card.handle) continue;
    const draft = draftForTask(card, drafts);
    if (!draft) continue;
    out.push({
      params: { handle: card.handle },
      props: { card, body: draftTxt(card, draft) },
    });
  }
  return out;
};

export const GET: APIRoute<Props> = ({ props }) => {
  return new Response(props.body, {
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "content-disposition": `attachment; filename="sig-records-request-DRAFT-${props.card.handle}.txt"`,
    },
  });
};
