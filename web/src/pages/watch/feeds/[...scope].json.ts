// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.34 (K7 WX-04b, SIG-WATCH-005/006): the JSON Feed 1.1 files —
// `watch/feeds/<scope>.json` for every emitted multi-format scope, served
// as `application/feed+json` (nginx maps the extension under /watch/feeds/;
// the lane's own *.json documents outside this directory keep
// `application/json`).
import type { APIRoute, GetStaticPaths } from "astro";
import { watchContext } from "../../../lib/watch-context";
import { exportBundleStamp } from "../../../lib/data";
import {
  feedBuiltAt,
  feedScopes,
  scopeItems,
  toWatchJsonFeed,
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

export const getStaticPaths: GetStaticPaths = () =>
  SCOPES.map((s) => ({ params: { scope: s.path } }));

export const GET: APIRoute = ({ params }) => {
  const scope = params.scope ?? "";
  const resolved = scopeItems(CTX.envelope, CTX.pages, scope);
  if (!resolved) return new Response("no such watch feed", { status: 404 });
  const body = toWatchJsonFeed({
    title: resolved.title,
    selfUrl: abs(`watch/feeds/${scope}.json`),
    pageUrl: abs(resolved.pagePath),
    items: resolved.items,
    builtAt: feedBuiltAtOrBundle(),
    itemUrl: (handle) => abs(`watch/item/${handle}/`),
  });
  return new Response(body, {
    headers: { "content-type": "application/feed+json; charset=utf-8" },
  });
};
