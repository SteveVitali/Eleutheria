// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The per-jurisdiction RSS 2.0 renewal-watch subscription (SIG-UI-027). Static-first
// (SIG-UI-036): one .xml feed per jurisdiction, emitted at build time, each <item>
// keyed on next_decision_date (SIG-UI-014b).
import type { APIRoute, GetStaticPaths } from "astro";
import { jurisdictionSlug, toRss, watchJurisdictions } from "../../lib/watch";
import { WATCH_ITEMS } from "../../lib/watch-evidence-fixture";

export const getStaticPaths: GetStaticPaths = () =>
  watchJurisdictions(WATCH_ITEMS).map((jurisdiction) => ({
    params: { jurisdiction: jurisdictionSlug(jurisdiction) },
    props: { jurisdiction },
  }));

export const GET: APIRoute = ({ props }) => {
  const { jurisdiction } = props as { jurisdiction: string };
  const origin = new URL(import.meta.env.SITE ?? "https://sig.example").origin;
  const body = toRss(WATCH_ITEMS, jurisdiction, origin);
  return new Response(body, {
    headers: { "content-type": "application/rss+xml; charset=utf-8" },
  });
};
