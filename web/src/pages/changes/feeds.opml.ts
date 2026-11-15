// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.40 (R11-K13-CHG-01, SIG-UI-072): `changes/feeds.opml` — the OPML 2.0
// bundle of every change feed this build emits (all + every place + every
// source), so a feed reader imports the whole set at once.
import type { APIRoute } from "astro";
import {
  getDossiers,
  getReleaseChanges,
  getSourceRows,
  getUnplacedReport,
  exportBundleStamp,
} from "../../lib/data";
import { getSourcePageIds } from "../../lib/source-page";
import { getReleaseStamp } from "../../lib/release-stamp";
import { changeFeedScopes } from "../../lib/changes";
import { toChangesOpml } from "../../lib/changes-feeds";
import { withBase } from "../../lib/paths";

const SITE = import.meta.env.SITE ?? "https://surveillancegraph.org";
const abs = (path: string): string => new URL(withBase(path), SITE).toString();

const places = [
  ...getDossiers().map((d) => ({ path: d.slug, name: d.subject_label ?? d.slug })),
  ...(getUnplacedReport() !== null && !getDossiers().some((d) => d.slug === "unplaced")
    ? [{ path: "unplaced", name: "Not yet placed" }]
    : []),
];
const sourceNames = new Map(
  getSourceRows().sources.map((s) => [s.source_id, s.name ?? s.source_id]),
);
const sources = getSourcePageIds().map((id) => ({ id, name: sourceNames.get(id) ?? id }));
const SCOPES = changeFeedScopes(places, sources);

const DOC = getReleaseChanges();
const STAMP = getReleaseStamp();
const created =
  STAMP?.builtAtInstant ??
  DOC?.index.release.as_of_belief ??
  DOC?.index.release.as_of_world ??
  exportBundleStamp() ??
  "1970-01-01";

export const GET: APIRoute = () =>
  new Response(
    toChangesOpml({
      scopes: SCOPES,
      title: "SIG change feeds",
      feedUrl: (scopePath) => abs(`changes/feeds/${scopePath}.atom`),
      pageUrl: (pagePath) => abs(pagePath),
      dateCreated: new Date(
        Date.parse(created.length === 10 ? `${created}T00:00:00Z` : created) || 0,
      ).toUTCString(),
    }),
    { headers: { "content-type": "text/x-opml; charset=utf-8" } },
  );
