// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.63 (K11 RQ-04 / SIG-RQ-007, SIG-RQ-010): `/research-queue/drafts/<place>.txt`
// — the per-place records-request draft bundle: every DRAFT the export
// persists for tasks scoped to the place and its slug-path children, as one
// downloadable text file. A bundle that would exceed 25 MB splits at draft
// boundaries into `…--part-<n>-of-<m>` files (SIG-RQ-010). DRAFT, NEVER SEND —
// a document, never a transmit path. A place with no drafts mints no file.
import type { APIRoute } from "astro";
import { getRecordsRequestDrafts, getResearchQueue } from "../../../lib/data";
import { placeFacets } from "../../../lib/queue-hub";
import {
  draftBundleFiles,
  placeDraftBundles,
  type DraftBundleFile,
} from "../../../lib/records-drafts";

/** The path separator — built, never a `"/"` literal site (SIG-REL-008). */
const PATH_SEP = String.fromCharCode(47);

interface Props {
  file: DraftBundleFile;
}

export function getStaticPaths() {
  const cards = getResearchQueue();
  const bundles = placeDraftBundles(cards, getRecordsRequestDrafts(), placeFacets(cards));
  return draftBundleFiles(bundles).map((file) => ({
    params: { slug: file.routeSlug },
    props: { file },
  }));
};

export const GET: APIRoute<Props> = ({ props }) => {
  return new Response(props.file.text, {
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "content-disposition": `attachment; filename="sig-records-request-DRAFTS-${props.file.routeSlug.split(PATH_SEP).join("-")}.txt"`,
    },
  });
};
