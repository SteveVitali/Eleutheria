// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The dossier's API (JSON) form (SIG-UI-011). The shell is static-first
// (SIG-UI-036), so this is emitted as a committed static file at build time — one
// per jurisdiction — rather than served from a live API; the shape is the `/v1`
// dossier contract. It exists so that "what we don't know" appears in the API as
// well as the summary and the print export: `what_we_dont_know` is a top-level key.
import type { APIRoute, GetStaticPaths } from "astro";
import { renderDossierJson } from "../../lib/dossier";
import type { Dossier } from "../../lib/dossier";
import { DOSSIERS } from "../../lib/dossier-fixture";

export const getStaticPaths: GetStaticPaths = () =>
  DOSSIERS.map((d) => ({ params: { slug: d.slug }, props: { dossier: d } }));

export const GET: APIRoute = ({ props }) => {
  const { dossier } = props as { dossier: Dossier };
  const origin = new URL(import.meta.env.SITE ?? "https://sig.example").origin;
  const body = renderDossierJson(dossier, origin);
  return new Response(JSON.stringify(body, null, 2), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
};
