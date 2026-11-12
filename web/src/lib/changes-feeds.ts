// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.40 (R11-K13-CHG-01, SIG-UI-072) — the change feed emitters: Atom
 * (RFC 4287) documents per place and per source built from TX-14's
 * (`sig.release-changes-feed/1` + `sig.release-source-changes/1`) diffs,
 * plus an OPML bundle of the whole set.
 *
 * Wire rules:
 *
 *   - `<feed>` carries `id` (the feed's own absolute URL), `title`,
 *     `updated` (the release's belief-side stamp — release activation,
 *     never a wall clock and never a version-control date, SIG-UI-072),
 *     `link rel="self"` + `link rel="alternate"` (the page the feed
 *     scopes to).
 *   - Every `<entry>` carries a stable `id`
 *     (`urn:sig:change:<pub>:<key>:<change>:<field>` — the record key IS
 *     the stable identity; two builds mint the identical id), `title`,
 *     `updated`/`published` (the event's world date — `new_date` from the
 *     diff; never a version-control stamp), `category` for the class and
 *     the change verb, and `content type="text"` naming the class, the
 *     verb, the reason/detail and the record's place and sources.
 *   - An empty scope still emits a valid feed — a subscriber can come
 *     early (D-K7-5's posture; the O2 journey's "feed exists even with 0
 *     items" analogue).
 *   - Entry order is the row order the caller supplies (deterministic —
 *     the readers sort key-then-field); newest world-date first is the
 *     reader's own sort.
 */

import type { ChangeFeedScope, ChangeRow } from "./changes";

/** The feed id domain — the production domain, never a fixture host. */
export const CHANGES_UID_DOMAIN = "surveillancegraph.org";

/** Escape XML text/attribute content. */
function xmlEscape(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

/** ISO-8601 for a possibly date-only stamp (`YYYY-MM-DD` → `…T00:00:00Z`). */
export function atomStamp(iso: string): string {
  const ms = Date.parse(iso.length === 10 ? `${iso}T00:00:00Z` : iso);
  if (Number.isNaN(ms)) throw new Error(`invalid ISO stamp for Atom: "${iso}"`);
  return new Date(ms).toISOString();
}

/** The class + verb phrase an entry title/content carries. */
export function changeVerb(row: ChangeRow): string {
  const verbs: Record<string, string> = {
    added: "added",
    removed: "removed",
    changed: "changed",
    retired: "retired",
    newly_failing: "newly failing",
    lane_changed: "lane changed",
  };
  return verbs[row.change] ?? row.change;
}

/** The class label — the two SIG-UI-072 separations in the feed's own words. */
export function classLabel(cls: ChangeRow["cls"]): string {
  return cls === "world_changed"
    ? "the source reports a change in the world"
    : "SIG's records changed";
}

/** The entry's stable id (record key + change + field under the release). */
export function entryId(row: ChangeRow, publicationId: string): string {
  const field = row.field ?? row.change;
  return `urn:sig:change:${publicationId}:${row.key}:${row.change}:${field}`;
}

/** The entry's content — class, verb, detail, place and source routing. */
export function entryContent(row: ChangeRow): string {
  const parts = [
    `${classLabel(row.cls)} — a ${row.kind === "record" ? "record" : "source"} was ${changeVerb(row)}.`,
    row.detail ? `${row.detail.charAt(0).toUpperCase()}${row.detail.slice(1)}.` : null,
    row.jurisdiction ? `Place: ${row.jurisdiction}.` : null,
    row.sourceIds.length ? `Sources: ${row.sourceIds.join(", ")}.` : null,
    row.compartment ? `Compartment: ${row.compartment}.` : null,
    row.date ? `World date: ${row.date}.` : null,
  ].filter((p): p is string => p !== null);
  return parts.join(" ");
}

/** The entry title — verb + label + field for field-level changes. */
export function entryTitle(row: ChangeRow): string {
  const field = row.field ? ` ${row.field}` : "";
  return `${changeVerb(row)}${field} — ${row.label}`;
}

/**
 * The Atom (RFC 4287) document for one scope. `updated` is the release's
 * belief-side stamp (release activation — the as_of_belief/built pair the
 * caller resolves); entry dates are world dates. An empty `rows` emits a
 * valid feed with no entries.
 */
export function toChangesAtom(opts: {
  title: string;
  selfUrl: string;
  pageUrl: string;
  updated: string;
  publicationId: string;
  rows: readonly ChangeRow[];
  feedDescription: string;
}): string {
  const out: string[] = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<feed xmlns="http://www.w3.org/2005/Atom">',
    `  <title>${xmlEscape(opts.title)}</title>`,
    `  <id>${xmlEscape(opts.selfUrl)}</id>`,
    `  <updated>${xmlEscape(opts.updated)}</updated>`,
    `  <link rel="self" type="application/atom+xml" href="${xmlEscape(opts.selfUrl)}"/>`,
    `  <link rel="alternate" type="text/html" href="${xmlEscape(opts.pageUrl)}"/>`,
    `  <subtitle>${xmlEscape(opts.feedDescription)}</subtitle>`,
  ];
  for (const row of opts.rows) {
    const stamp = row.date ? atomStamp(row.date) : opts.updated;
    out.push(
      "  <entry>",
      `    <title>${xmlEscape(entryTitle(row))}</title>`,
      `    <id>${xmlEscape(entryId(row, opts.publicationId))}</id>`,
      `    <updated>${xmlEscape(stamp)}</updated>`,
      `    <published>${xmlEscape(stamp)}</published>`,
      `    <category term="${xmlEscape(row.change)}" label="${xmlEscape(classLabel(row.cls))}"/>`,
      `    <content type="text">${xmlEscape(entryContent(row))}</content>`,
      `    <link rel="related" type="text/html" href="${xmlEscape(opts.pageUrl)}"/>`,
      "  </entry>",
    );
  }
  out.push("</feed>", "");
  return out.join("\n");
}

/**
 * The OPML 2.0 bundle — one `type="rss"` outline per scope (`xmlUrl` the
 * `.atom` feed, `htmlUrl` the page it scopes to), grouped by scope kind so
 * a reader can import the whole set or one lane.
 */
export function toChangesOpml(opts: {
  scopes: readonly ChangeFeedScope[];
  title: string;
  feedUrl: (scopePath: string) => string;
  pageUrl: (pagePath: string) => string;
  dateCreated: string;
}): string {
  const outline = (s: ChangeFeedScope, indent: string) =>
    `${indent}<outline text="${xmlEscape(s.title)}" title="${xmlEscape(s.title)}" type="rss" ` +
    `xmlUrl="${xmlEscape(opts.feedUrl(s.path))}" htmlUrl="${xmlEscape(opts.pageUrl(s.pagePath))}"/>`;
  const groups: { label: string; scopes: ChangeFeedScope[] }[] = [
    { label: "Every change", scopes: opts.scopes.filter((s) => s.scope === "all") },
    { label: "By place", scopes: opts.scopes.filter((s) => s.scope === "place") },
    { label: "By source", scopes: opts.scopes.filter((s) => s.scope === "source") },
  ];
  const out: string[] = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<opml version="2.0">',
    "  <head>",
    `    <title>${xmlEscape(opts.title)}</title>`,
    `    <dateCreated>${xmlEscape(opts.dateCreated)}</dateCreated>`,
    "  </head>",
    "  <body>",
  ];
  for (const g of groups) {
    if (g.scopes.length === 0) continue;
    out.push(`    <outline text="${xmlEscape(g.label)}" title="${xmlEscape(g.label)}">`);
    for (const s of g.scopes) out.push(outline(s, "      "));
    out.push("    </outline>");
  }
  out.push("  </body>", "</opml>", "");
  return out.join("\n");
}
