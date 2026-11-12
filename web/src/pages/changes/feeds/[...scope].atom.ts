// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.40 (R11-K13-CHG-01, SIG-UI-072): the Atom (RFC 4287) feed files —
// `changes/feeds/<scope>.atom` for `all`, every emitted place page
// (`place/<slug-path>`) and every emitted source page (`source/<id>`),
// served as `application/atom+xml` static bytes. `updated` is the release's
// belief-side stamp (release activation — the stamp's built_at wins, then
// the diff's as_of_belief, then the bundle's datapackage stamp; never a
// wall clock, never a version-control date); entry dates are the events'
// world dates.
import type { APIRoute, GetStaticPaths } from "astro";
import {
  getDossiers,
  getReleaseChanges,
  getSourceRows,
  getUnplacedReport,
  exportBundleStamp,
} from "../../../lib/data";
import { getSourcePageIds } from "../../../lib/source-page";
import { getReleaseStamp } from "../../../lib/release-stamp";
import {
  changeFeedScopes,
  changeRows,
  scopeRows,
  type ReleaseChangesDoc,
} from "../../../lib/changes";
import { toChangesAtom } from "../../../lib/changes-feeds";
import { withBase } from "../../../lib/paths";

const DOC = getReleaseChanges();
const ROWS = DOC ? changeRows(DOC) : [];
const STAMP = getReleaseStamp();
const SITE = import.meta.env.SITE ?? "https://surveillancegraph.org";

const abs = (path: string): string => new URL(withBase(path), SITE).toString();

export function changeScopes() {
  const places = [
    ...getDossiers().map((d) => ({ path: d.slug, name: d.subject_label ?? d.slug })),
    ...(getUnplacedReport() !== null && !getDossiers().some((d) => d.slug === "unplaced")
      ? [{ path: "unplaced", name: "Not yet placed" }]
      : []),
  ];
  const sourceNames = new Map(
    getSourceRows().sources.map((s) => [s.source_id, s.name ?? s.source_id]),
  );
  const sources = getSourcePageIds().map((id) => ({
    id,
    name: sourceNames.get(id) ?? id,
  }));
  return changeFeedScopes(places, sources);
}

const SCOPES = changeScopes();

/** The feed's `updated` stamp — release activation (belief time): the
 *  stamp's built_at, else the diff's as_of_belief, else the bundle stamp. */
function feedUpdated(doc: ReleaseChangesDoc | null): string {
  const stamp =
    STAMP?.builtAtInstant ??
    doc?.index.release.as_of_belief ??
    doc?.index.release.as_of_world ??
    exportBundleStamp();
  const iso = stamp ?? "1970-01-01";
  const ms = Date.parse(iso.length === 10 ? `${iso}T00:00:00Z` : iso);
  return Number.isNaN(ms) ? new Date(0).toISOString() : new Date(ms).toISOString();
}

export const getStaticPaths: GetStaticPaths = () =>
  SCOPES.map((s) => ({ params: { scope: s.path } }));

export const GET: APIRoute = ({ params }) => {
  const scope = params.scope ?? "";
  const meta = SCOPES.find((s) => s.path === scope);
  const rows = scopeRows(ROWS, SCOPES, scope);
  if (!meta || rows === null) return new Response("no such change feed", { status: 404 });
  const pub = DOC?.index.release.publication_id ?? STAMP?.publicationId ?? "p-unbound";
  const body = toChangesAtom({
    title: meta.title,
    selfUrl: abs(`changes/feeds/${scope}.atom`),
    pageUrl: abs(meta.pagePath),
    updated: feedUpdated(DOC),
    publicationId: pub,
    rows,
    feedDescription:
      "What changed between the latest release and the previous activated release — " +
      "SIG's records changed kept apart from the source reporting a change in the world.",
  });
  return new Response(body, {
    headers: { "content-type": "application/atom+xml; charset=utf-8" },
  });
};
