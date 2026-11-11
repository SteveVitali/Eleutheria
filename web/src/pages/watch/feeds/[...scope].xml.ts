// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.34 (K7 WX-04b, SIG-WATCH-005/006): the RSS 2.0 feed files —
// `watch/feeds/<scope>.xml` for every emitted multi-format scope (all,
// every place page, the six kinds, the present facet values), served as
// `application/rss+xml` with `atom:link rel="self"`, `lastBuildDate` at the
// watch build stamp and `pubDate` = `first_seen` (never the decision date).
import type { APIRoute, GetStaticPaths } from "astro";
import { watchContext } from "../../../lib/watch-context";
import {
  feedBuiltAt,
  feedScopes,
  scopeItems,
  toWatchRss,
} from "../../../lib/watch-feeds";
import { withBase } from "../../../lib/paths";

const CTX = watchContext();
const SITE = import.meta.env.SITE ?? "https://surveillancegraph.org";

const abs = (path: string): string => new URL(withBase(path), SITE).toString();

const SCOPES = feedScopes(CTX.envelope, CTX.pages);

export const getStaticPaths: GetStaticPaths = () =>
  SCOPES.map((s) => ({ params: { scope: s.path } }));

export const GET: APIRoute = ({ params }) => {
  const scope = params.scope ?? "";
  const resolved = scopeItems(CTX.envelope, CTX.pages, scope);
  if (!resolved) return new Response("no such watch feed", { status: 404 });
  const body = toWatchRss({
    title: resolved.title,
    selfUrl: abs(`watch/feeds/${scope}.xml`),
    pageUrl: abs(resolved.pagePath),
    items: resolved.items,
    builtAt: feedBuiltAt(CTX.envelope),
    itemUrl: (handle) => abs(`watch/item/${handle}/`),
  });
  return new Response(body, {
    headers: { "content-type": "application/rss+xml; charset=utf-8" },
  });
};
