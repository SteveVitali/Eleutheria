// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.34 (K7 WX-04b, SIG-WATCH-005/006): the iCal (RFC 5545) feed files —
// `watch/feeds/<scope>.ics` for every emitted scope (all, every place page,
// the six kinds, the present vendor/technology facet values) plus
// `watch/feeds/item/<handle>.ics` for each item's "add to calendar".
// Emitted as static bytes at build time — UID stable, DTSTAMP the watch
// build's generated_at, an empty scope still validates (UTC VTIMEZONE).
import type { APIRoute, GetStaticPaths } from "astro";
import { watchContext } from "../../../lib/watch-context";
import { exportBundleStamp } from "../../../lib/data";
import {
  feedBuiltAt,
  feedScopes,
  scopeItems,
  toWatchICal,
} from "../../../lib/watch-feeds";
import { withBase } from "../../../lib/paths";

const CTX = watchContext();
const SITE = import.meta.env.SITE ?? "https://surveillancegraph.org";

const abs = (path: string): string => new URL(withBase(path), SITE).toString();
// SIG-WATCH-006: the envelope's own stamp wins; a bare-array pre-P35.43
// watch.json (stripped envelope) falls back to the bundle's recorded
// datapackage `created` — a real artifact stamp, never a wall clock.
const feedBuiltAtOrBundle = (): string =>
  feedBuiltAt(CTX.envelope) || exportBundleStamp() || "";

const SCOPES = feedScopes(CTX.envelope, CTX.pages);
// The item scopes — `item/<handle>` mints a one-VEVENT calendar per item.
const ITEM_SCOPES = CTX.envelope.items.map((i) => `item/${i.handle}`);

export const getStaticPaths: GetStaticPaths = () =>
  [...SCOPES.map((s) => s.path), ...ITEM_SCOPES].map((scope) => ({
    params: { scope },
  }));

export const GET: APIRoute = ({ params }) => {
  const scope = params.scope ?? "";
  const builtAt = feedBuiltAtOrBundle();
  const itemUrl = (handle: string) => abs(`watch/item/${handle}/`);
  let items;
  let title;
  let pagePath;
  if (scope.startsWith("item/")) {
    const item = CTX.envelope.items.find((i) => i.handle === scope.slice(5));
    if (!item) return new Response("no such watch item feed", { status: 404 });
    items = [item];
    title = `SIG watch — ${item.title}`;
    pagePath = `watch/item/${item.handle}/`;
  } else {
    const resolved = scopeItems(CTX.envelope, CTX.pages, scope);
    if (!resolved) return new Response("no such watch feed", { status: 404 });
    ({ items, title, pagePath } = resolved);
  }
  const body = toWatchICal({
    title,
    selfUrl: abs(`watch/feeds/${scope}.ics`),
    pageUrl: abs(pagePath),
    items,
    builtAt,
    itemUrl,
  });
  return new Response(body, {
    headers: { "content-type": "text/calendar; charset=utf-8" },
  });
};
