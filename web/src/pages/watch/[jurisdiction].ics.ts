// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The per-jurisdiction iCal (RFC 5545) renewal-watch subscription (SIG-UI-027). The
// shell is static-first (SIG-UI-036): one .ics file per jurisdiction is emitted at
// build time, each VEVENT keyed on next_decision_date (SIG-UI-014b), never a live
// calendar server. DTSTAMP is the deterministic as-of date (no wall-clock), so the
// feed is byte-reproducible.
import type { APIRoute, GetStaticPaths } from "astro";
import { jurisdictionSlug, toICal, watchJurisdictions } from "../../lib/watch";
import { WATCH_ITEMS } from "../../lib/watch-evidence-fixture";
import { AS_OF } from "../../lib/fixtures";

export const getStaticPaths: GetStaticPaths = () =>
  watchJurisdictions(WATCH_ITEMS).map((jurisdiction) => ({
    params: { jurisdiction: jurisdictionSlug(jurisdiction) },
    props: { jurisdiction },
  }));

export const GET: APIRoute = ({ props }) => {
  const { jurisdiction } = props as { jurisdiction: string };
  const body = toICal(WATCH_ITEMS, jurisdiction, AS_OF.as_of_world);
  return new Response(body, {
    headers: { "content-type": "text/calendar; charset=utf-8" },
  });
};
