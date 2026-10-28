// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.20 (UXK0-4): the fixture `sig.typeahead-shard/1` endpoint the internal
// harness's `<sig-typeahead>` reads — static files keyed by the query's
// first-two-char prefix, so each keystroke fetches at most one small shard
// and nothing ever touches a live spine. P36.40 owns the real export-mode
// shards; these entries point only at routes the fixtures build emits.
import type { APIRoute, GetStaticPaths } from "astro";
import { withBase } from "../../../lib/paths";
import type { TypeaheadShard } from "../../../elements/typeahead-model";

const href = (route: string) => withBase(route);

const SHARDS: Record<string, TypeaheadShard["entries"]> = {
  co: [
    { label: "Corrections log", kind: "page", href: href("corrections/") },
    { label: "Coverage metrics", kind: "page", href: href("coverage-metrics/") },
  ],
  ed: [
    {
      label: "Editorial standards",
      kind: "page",
      href: href("editorial-standards/"),
    },
  ],
  gl: [{ label: "Glossary", kind: "page", href: href("glossary/") }],
  ma: [{ label: "Map of recorded sites", kind: "map", href: href("map/") }],
  me: [
    { label: "Methodology", kind: "page", href: href("methodology/") },
    {
      label: "Methodology — count definitions",
      kind: "section",
      href: href("methodology/"),
    },
  ],
  ok: [
    {
      label: "Oklahoma City",
      kind: "place",
      href: href("dossier/oklahoma-city/"),
    },
  ],
  se: [{ label: "Search", kind: "page", href: href("search/") }],
  so: [
    { label: "Sources and licences", kind: "page", href: href("sources/") },
    {
      label: "Source registry terms",
      kind: "section",
      href: href("sources/"),
    },
  ],
  st: [{ label: "Status", kind: "page", href: href("status/") }],
  wa: [{ label: "Watch — outlier review", kind: "page", href: href("watch/") }],
};

export const getStaticPaths: GetStaticPaths = () =>
  Object.keys(SHARDS).map((key) => ({ params: { key } }));

export const GET: APIRoute = ({ params }) => {
  const key = params.key ?? "";
  const entries = SHARDS[key] ?? [];
  const shard: TypeaheadShard = {
    schema: "sig.typeahead-shard/1",
    key,
    entries,
  };
  return new Response(JSON.stringify(shard, null, 2), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
};
