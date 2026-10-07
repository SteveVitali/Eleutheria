// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The research dossier's API (JSON) form (P32.17, SIG-DOS-001/002) — emitted as
// a committed static file at build time, one per reviewed dossier; the shape is
// the `sig.research-dossier/1` contract (states, ledger, checklist, rubric).
import type { APIRoute, GetStaticPaths } from "astro";
import { getResearchDossierPortfolio } from "../../lib/data";
import { researchDossierSlug } from "../../lib/research-dossier";
import type { ResearchDossier } from "../../lib/research-dossier";

export const getStaticPaths: GetStaticPaths = () =>
  getResearchDossierPortfolio().dossiers.map((d) => ({
    params: { slug: researchDossierSlug(d) },
    props: { dossier: d },
  }));

export const GET: APIRoute = ({ props }) => {
  const { dossier } = props as { dossier: ResearchDossier };
  return new Response(JSON.stringify(dossier, null, 2), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
};
