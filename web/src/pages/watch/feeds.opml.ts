// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.34 (K7 WX-04b, SIG-WATCH-005): `/watch/feeds.opml` — the OPML 2.0
// bundle of every feed this release emits: the `all` feed plus every place
// (empty or not, D-K7-5), kind, vendor and technology scope, each outline
// pointing at the scope's `.xml` (RSS 2.0) form.
import type { APIRoute } from "astro";
import { watchContext } from "../../lib/watch-context";
import { feedBuiltAt, feedScopes, toWatchOpml } from "../../lib/watch-feeds";
import { withBase } from "../../lib/paths";

const CTX = watchContext();
const SITE = import.meta.env.SITE ?? "https://surveillancegraph.org";

const abs = (path: string): string => new URL(withBase(path), SITE).toString();

export const GET: APIRoute = () => {
  const body = toWatchOpml({
    scopes: feedScopes(CTX.envelope, CTX.pages),
    builtAt: feedBuiltAt(CTX.envelope),
    feedUrl: (scopePath, format) => abs(`watch/feeds/${scopePath}.${format}`),
    pageUrl: (pagePath) => abs(pagePath),
  });
  return new Response(body, {
    headers: { "content-type": "text/x-opml; charset=utf-8" },
  });
};
