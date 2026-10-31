// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.40 (K3 SRCH-05 / SIG-SRCH-010): the emitted `sig.typeahead-shard/1`
// set — one static JSON document per word-start key under
// `/search/shards/<key>.json`, built at build time from the release-pinned
// data layer (export mode binds the release's own named things; fixtures
// mode the committed corpus). The ONE shard root every `<sig-typeahead>`
// consumer names is `TYPEAHEAD_SHARD_ROOT` in lib/typeahead-shards — the
// header element, home hero, this page's corpus form and the dossier-index
// place form read it today; the map place search (P37.19) and explorer
// search-to-node (P37.26) read the same set when their rows land (UXR-23).
import type { APIRoute, GetStaticPaths } from "astro";
import { buildTypeaheadShards } from "../../../lib/typeahead-shards";

export const getStaticPaths: GetStaticPaths = () =>
  [...buildTypeaheadShards().keys()].map((key) => ({ params: { key } }));

export const GET: APIRoute = ({ params }) => {
  const shard = buildTypeaheadShards().get(params.key ?? "");
  return new Response(`${JSON.stringify(shard ?? { schema: "sig.typeahead-shard/1", key: params.key ?? "", entries: [] }, null, 2)}\n`, {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
};
