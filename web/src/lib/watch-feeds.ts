// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.34 (K7 WX-04b / SIG-WATCH-005, SIG-WATCH-006) — the decision calendar's
 * feed set, emitted as T0-class static bytes under `/watch/feeds/`:
 *
 *   watch/feeds/all.ics|.xml|.json            — the whole calendar
 *   watch/feeds/place/<path>.ics|.xml|.json   — every emitted place page
 *                                               (D-K7-5: empty too — a group
 *                                               can subscribe before the
 *                                               first item appears)
 *   watch/feeds/kind/<k>.ics|.xml|.json       — the six §5.2 kinds
 *   watch/feeds/vendor/<id>.ics|.xml|.json    — the facet values present
 *   watch/feeds/technology/<id>.ics|.xml|.json
 *   watch/feeds/item/<handle>.ics             — "add to calendar" per item
 *   watch/feeds.opml                          — the OPML bundle of place feeds
 *
 * The wire rules the emitters honour (K7 §5.5 → SIG-WATCH-005/006):
 *
 *   - iCal (RFC 5545): `UID:<handle>@surveillancegraph.org` — stable across
 *     builds (the handle IS the stable key; the production domain, never a
 *     fixture host). `SEQUENCE` increments when the date moves — the wire's
 *     recorded move signal is `status: "superseded"` (the firing claim's
 *     recorded supersession), so it emits `SEQUENCE:1`; every other item
 *     emits `SEQUENCE:0`. `STATUS:CANCELLED` when an item is `withdrawn` or
 *     `superseded` (calendar clients then remove it) — the cancelled event
 *     carries no reason text (the J3 §9.2 pattern). `DTSTAMP` is the watch
 *     build's `generated_at` (SIG-WATCH-006 — never a fixture constant, never
 *     a wall clock). All-day `DTSTART;VALUE=DATE`; `URL` = the item page;
 *     `REFRESH-INTERVAL;VALUE=DURATION:P1D` + `X-PUBLISHED-TTL:P1D`; an empty
 *     calendar still carries one UTC VTIMEZONE component so it validates.
 *   - RSS 2.0: `<link>` = the item page, `<guid>` = the handle URL,
 *     `pubDate` = `first_seen` (never the future decision date — the date
 *     rides the title + description), `lastBuildDate` = the watch build,
 *     `<ttl>1440</ttl>`, `atom:link rel="self"`.
 *   - JSON Feed 1.1: `version`/`title`/`home_page_url`/`feed_url`/`items`
 *     with `id` (the handle URL), `url` (the item page), `date_published`
 *     (`first_seen`), `date_modified` (`last_checked`).
 *   - OPML 2.0: one `type="rss"` outline per emitted place page (plus `all`),
 *     `xmlUrl` the `.xml` feed, `htmlUrl` the place page — D-K7-5, an empty
 *     place is still a valid subscription.
 *
 * An `upper_bound` alert date is never labelled a deadline inside a feed
 * either (SIG-WATCH-002): the description names it "latest possible date —
 * the real deadline may be earlier".
 */

import { NOT_RECORDED } from "./provenance-panel";
import {
  CERTAINTY_LABELS,
  DATE_KIND_LABELS,
  isWatchKind,
  itemsForKind,
  itemsForPlace,
  itemsForTechnology,
  itemsForVendor,
  byWatchDate,
  facetValues,
  WATCH_KIND_LABELS,
  WATCH_KINDS,
} from "./watch-v2";
import type { WatchEnvelopeV2, WatchItemV2, WatchPlacePage } from "./watch-v2";
import { WATCH_UID_DOMAIN } from "./watch";

// --- Feed scopes ------------------------------------------------------------ //

export const WATCH_FEED_FORMATS = ["ics", "xml", "json"] as const;
export type WatchFeedFormat = (typeof WATCH_FEED_FORMATS)[number];

/** One multi-format feed scope (`all`, a place, a kind, a facet value). */
export interface WatchFeedScope {
  /** The scope's route segment — `all`, `place/usa/ok`, `kind/agenda_item`,
   *  `vendor/flock_safety`, `technology/alpr`. */
  path: string;
  /** The scope's kind — used by the pages to group the directory. */
  scope: "all" | "place" | "kind" | "vendor" | "technology";
  /** The feed's human title (used in CALNAME/channel/json/OPML text). */
  title: string;
  /** The page the feed's htmlUrl/home link names (root-relative `watch/…`). */
  pagePath: string;
}

/** The feed file path for a scope+format — root-relative, no leading slash
 *  (`watch/feeds/place/usa/ok.ics`); callers pass through withBase(). */
export function watchFeedPath(scopePath: string, format: WatchFeedFormat): string {
  return `watch/feeds/${scopePath}.${format}`;
}

/** The per-item "add to calendar" file (`watch/feeds/item/<handle>.ics`). */
export function watchItemFeedPath(handle: string): string {
  return `watch/feeds/item/${handle}.ics`;
}

/** The OPML bundle path (`watch/feeds.opml`). */
export const WATCH_OPML_PATH = "watch/feeds.opml";

/**
 * The emitted multi-format scope set. `all` always emits; every emitted
 * place page gets a feed (D-K7-5 — empty or not); every one of the six §5.2
 * kinds emits (a closed list — a subscriber can come early); the vendor and
 * technology facets mint only for a value that exists on an item (the same
 * rule the facet pages hold — a never-matched value is never a feed).
 */
export function feedScopes(
  envelope: WatchEnvelopeV2,
  pages: readonly WatchPlacePage[],
): WatchFeedScope[] {
  const scopes: WatchFeedScope[] = [
    {
      path: "all",
      scope: "all",
      title: "SIG watch — upcoming decisions",
      pagePath: "watch/",
    },
  ];
  for (const page of pages) {
    scopes.push({
      path: `place/${page.path}`,
      scope: "place",
      title: page.unplaced
        ? "SIG watch — items not yet placed"
        : `SIG watch — ${page.name}`,
      pagePath: `watch/place/${page.path}/`,
    });
  }
  for (const kind of WATCH_KINDS) {
    scopes.push({
      path: `kind/${kind}`,
      scope: "kind",
      title: `SIG watch — ${WATCH_KIND_LABELS[kind].toLowerCase()}`,
      pagePath: `watch/kind/${kind}/`,
    });
  }
  const items = envelope.items;
  for (const v of facetValues(items, "vendor")) {
    scopes.push({
      path: `vendor/${v.id}`,
      scope: "vendor",
      title: `SIG watch — vendor ${v.label}`,
      pagePath: `watch/vendor/${v.id}/`,
    });
  }
  for (const t of facetValues(items, "technology")) {
    scopes.push({
      path: `technology/${t.id}`,
      scope: "technology",
      title: `SIG watch — ${t.label}`,
      pagePath: `watch/technology/${t.id}/`,
    });
  }
  return scopes;
}

/**
 * Resolve a scope segment to its item set + title — the same rules the
 * minted scopes carry, so a feed and its page can never disagree. `null`
 * when the scope names nothing this build emits (never minted → never GET).
 */
export function scopeItems(
  envelope: WatchEnvelopeV2,
  pages: readonly WatchPlacePage[],
  scopePath: string,
): { items: WatchItemV2[]; title: string; pagePath: string } | null {
  if (scopePath === "all") {
    return {
      items: [...envelope.items].sort(byWatchDate),
      title: "SIG watch — upcoming decisions",
      pagePath: "watch/",
    };
  }
  const [head, ...rest] = scopePath.split("/");
  const tail = rest.join("/");
  if (!tail) return null;
  if (head === "place") {
    const page = pages.find((p) => p.path === tail);
    if (!page) return null;
    return {
      items: itemsForPlace(envelope.items, page.key),
      title: page.unplaced ? "SIG watch — items not yet placed" : `SIG watch — ${page.name}`,
      pagePath: `watch/place/${page.path}/`,
    };
  }
  if (head === "kind" && isWatchKind(tail)) {
    return {
      items: itemsForKind(envelope.items, tail),
      title: `SIG watch — ${WATCH_KIND_LABELS[tail].toLowerCase()}`,
      pagePath: `watch/kind/${tail}/`,
    };
  }
  if (head === "vendor") {
    const rows = itemsForVendor(envelope.items, tail);
    if (rows.length === 0) return null;
    const label = facetValues(envelope.items, "vendor").find((v) => v.id === tail)?.label ?? tail;
    return {
      items: rows,
      title: `SIG watch — vendor ${label}`,
      pagePath: `watch/vendor/${tail}/`,
    };
  }
  if (head === "technology") {
    const rows = itemsForTechnology(envelope.items, tail);
    if (rows.length === 0) return null;
    const label = facetValues(envelope.items, "technology").find((v) => v.id === tail)?.label ?? tail;
    return {
      items: rows,
      title: `SIG watch — ${label}`,
      pagePath: `watch/technology/${tail}/`,
    };
  }
  return null;
}

// --- Shared feed primitives ------------------------------------------------- //

/**
 * The item's feed UID — `<handle>@surveillancegraph.org`: the production
 * domain (SIG-WATCH-005), derived from the stable handle only, so two builds
 * mint the identical UID for the same item.
 */
export function feedUid(item: WatchItemV2): string {
  return `${item.handle}@${WATCH_UID_DOMAIN}`;
}

/**
 * `SEQUENCE` — increments when the alert date moves (K7 §5.5). The wire's
 * recorded move signal is `status: "superseded"` (the producer marks it when
 * the firing claim's date was superseded by a newer claim): it emits
 * `SEQUENCE:1`; every other item emits `SEQUENCE:0`. Deterministic — the
 * same wire always mints the same number.
 */
export function feedSequence(item: WatchItemV2): number {
  return item.status === "superseded" ? 1 : 0;
}

/** `STATUS:CANCELLED` when withdrawn or superseded (clients then remove it). */
export function feedStatus(item: WatchItemV2): "CONFIRMED" | "CANCELLED" {
  return item.status === "withdrawn" || item.status === "superseded"
    ? "CANCELLED"
    : "CONFIRMED";
}

/**
 * The watch build's stamp — SIG-WATCH-006: `DTSTAMP` and `lastBuildDate`
 * come from the payload's `generated_at` (falling back to `as_of`), never a
 * fixture constant and never a wall clock. The fixture envelope declares
 * its own build stamp, which IS the build time in fixtures mode.
 */
export function feedBuiltAt(envelope: WatchEnvelopeV2): string {
  return envelope.generated_at ?? envelope.as_of ?? "";
}

/** Compact an ISO date/datetime to the iCal UTC form (`YYYYMMDD[THHMMSSZ]`). */
export function icalStamp(iso: string): string {
  const ms = Date.parse(iso.length === 10 ? `${iso}T00:00:00Z` : iso);
  if (Number.isNaN(ms)) throw new Error(`invalid ISO stamp for iCal: "${iso}"`);
  return new Date(ms).toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
}

/** Compact an ISO `YYYY-MM-DD` to the iCal DATE form `YYYYMMDD` (DTSTART). */
export function icalDate(iso: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) {
    throw new Error(`invalid ISO date for iCal: "${iso}"`);
  }
  return iso.replace(/-/g, "");
}

/** RFC 822 form for RSS `pubDate`/`lastBuildDate` (`Date#toUTCString`). */
export function rssStamp(iso: string): string {
  const ms = Date.parse(iso.length === 10 ? `${iso}T00:00:00Z` : iso);
  if (Number.isNaN(ms)) throw new Error(`invalid ISO stamp for RSS: "${iso}"`);
  return new Date(ms).toUTCString();
}

/** Escape a text value per RFC 5545 §3.3.11. */
function icalEscape(text: string): string {
  return text
    .replace(/\\/g, "\\\\")
    .replace(/;/g, "\\;")
    .replace(/,/g, "\\,")
    .replace(/\r?\n/g, "\\n");
}

/** Escape XML text/attribute content. */
function xmlEscape(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

/** Fold a content line to ≤75 octets per RFC 5545 §3.1 (UTF-8 aware). */
function icalFold(line: string): string {
  const enc = new TextEncoder();
  if (enc.encode(line).length <= 75) return line;
  const out: string[] = [];
  let current = "";
  let currentBytes = 0;
  let first = true;
  for (const ch of line) {
    const chBytes = enc.encode(ch).length;
    const limit = first ? 75 : 74;
    if (currentBytes + chBytes > limit) {
      out.push(current);
      current = ch;
      currentBytes = chBytes;
      first = false;
    } else {
      current += ch;
      currentBytes += chBytes;
    }
  }
  out.push(current);
  return out.join("\r\n ");
}

// --- The item's feed text --------------------------------------------------- //

/** The one alert date's feed wording — kind + certainty; an `upper_bound`
 *  is "latest possible date — the real deadline may be earlier", never a
 *  deadline (SIG-WATCH-002 inside feed bytes too). */
export function feedDateLine(item: WatchItemV2): string {
  const certainty = item.date_certainty ?? "stated";
  const kindLabel =
    certainty === "upper_bound"
      ? "latest possible date — the real deadline may be earlier"
      : (DATE_KIND_LABELS[item.date_kind] ?? item.date_kind);
  return `${item.date} (${kindLabel}${certainty === "upper_bound" ? "" : ` · ${CERTAINTY_LABELS[certainty] ?? certainty}`})`;
}

/** The feed description — kind, certainty, body, the item page as the
 *  evidence link and the contested marker (W-P3/SIG-UI-008). Cancelled
 *  items carry the status sentence only (no reason text — J3 §9.2). */
export function feedDescription(item: WatchItemV2, itemUrl: string): string {
  if (feedStatus(item) === "CANCELLED") {
    return `This item was withdrawn or its date moved — the item page holds the record: ${itemUrl}`;
  }
  const parts = [
    `${WATCH_KIND_LABELS[item.kind]} — ${feedDateLine(item)}.`,
    item.body ? `Body: ${item.body}.` : null,
    item.contested
      ? "Contested — a published disagreement names a value on this item (see the item page)."
      : null,
    `Item page and supporting claims: ${itemUrl}`,
  ].filter((p): p is string => p !== null);
  return parts.join(" ");
}

// --- iCal (RFC 5545) -------------------------------------------------------- //

/** A UTC VTIMEZONE so an empty calendar still carries a component. */
const UTC_VTIMEZONE = [
  "BEGIN:VTIMEZONE",
  "TZID:UTC",
  "BEGIN:STANDARD",
  "DTSTART:19700101T000000",
  "TZOFFSETFROM:+0000",
  "TZOFFSETTO:+0000",
  "TZNAME:UTC",
  "END:STANDARD",
  "END:VTIMEZONE",
];

/**
 * The iCal (RFC 5545) subscription for a scope (or one item). `builtAt` is
 * the watch build's `generated_at` (SIG-WATCH-006); `itemUrl` resolves the
 * item's absolute page URL; `selfUrl`/`pageUrl` are the feed's own absolute
 * URL and its page link. Empty item sets still emit the UTC VTIMEZONE so
 * the calendar validates (SIG-WATCH-005).
 */
export function toWatchICal(opts: {
  title: string;
  selfUrl: string;
  pageUrl: string;
  items: readonly WatchItemV2[];
  builtAt: string;
  itemUrl: (handle: string) => string;
}): string {
  const dtstamp = icalStamp(opts.builtAt);
  const lines: string[] = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//SIG//Watch Decision Calendar//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    `X-WR-CALNAME:${icalEscape(opts.title)}`,
    `X-WR-CALDESC:${icalEscape("Upcoming public decisions about surveillance technology — the SIG decision calendar.")}`,
    `URL:${opts.selfUrl}`,
    "REFRESH-INTERVAL;VALUE=DURATION:P1D",
    "X-PUBLISHED-TTL:P1D",
  ];
  if (opts.items.length === 0) {
    lines.push(...UTC_VTIMEZONE);
  }
  for (const item of opts.items) {
    const url = opts.itemUrl(item.handle);
    lines.push(
      "BEGIN:VEVENT",
      `UID:${feedUid(item)}`,
      `DTSTAMP:${dtstamp}`,
      `DTSTART;VALUE=DATE:${icalDate(item.date.slice(0, 10))}`,
      `SEQUENCE:${feedSequence(item)}`,
      `STATUS:${feedStatus(item)}`,
      `SUMMARY:${icalEscape(item.title)}`,
      `DESCRIPTION:${icalEscape(feedDescription(item, url))}`,
      `URL:${url}`,
      "END:VEVENT",
    );
  }
  lines.push("END:VCALENDAR");
  return lines.map(icalFold).join("\r\n") + "\r\n";
}

// --- RSS 2.0 ---------------------------------------------------------------- //

/**
 * The RSS 2.0 subscription for a scope — `atom:link rel="self"`,
 * `lastBuildDate` (the watch build), `<ttl>1440</ttl>`, one `<item>` per
 * watch item whose `pubDate` is `first_seen` (the future decision date
 * rides the title + description — K7 §5.5).
 */
export function toWatchRss(opts: {
  title: string;
  selfUrl: string;
  pageUrl: string;
  items: readonly WatchItemV2[];
  builtAt: string;
  itemUrl: (handle: string) => string;
}): string {
  const pub = (item: WatchItemV2) => rssStamp(item.first_seen ?? item.date);
  const out: string[] = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
    "  <channel>",
    `    <title>${xmlEscape(opts.title)}</title>`,
    `    <link>${xmlEscape(opts.pageUrl)}</link>`,
    `    <atom:link href="${xmlEscape(opts.selfUrl)}" rel="self" type="application/rss+xml"/>`,
    `    <description>${xmlEscape(
      "Upcoming public decisions about surveillance technology — the SIG decision calendar.",
    )}</description>`,
    `    <lastBuildDate>${xmlEscape(rssStamp(opts.builtAt))}</lastBuildDate>`,
    "    <ttl>1440</ttl>",
  ];
  for (const item of opts.items) {
    const url = opts.itemUrl(item.handle);
    out.push(
      "    <item>",
      `      <title>${xmlEscape(`${feedDateLine(item)} — ${item.title}`)}</title>`,
      `      <link>${xmlEscape(url)}</link>`,
      `      <guid isPermaLink="true">${xmlEscape(url)}</guid>`,
      `      <pubDate>${xmlEscape(pub(item))}</pubDate>`,
      `      <description>${xmlEscape(feedDescription(item, url))}</description>`,
      "    </item>",
    );
  }
  out.push("  </channel>", "</rss>", "");
  return out.join("\n");
}

// --- JSON Feed 1.1 ---------------------------------------------------------- //

/** ISO-8601 for a possibly date-only stamp (`YYYY-MM-DD` → `…T00:00:00Z`). */
function jsonStamp(iso: string): string {
  const ms = Date.parse(iso.length === 10 ? `${iso}T00:00:00Z` : iso);
  if (Number.isNaN(ms)) throw new Error(`invalid ISO stamp for JSON Feed: "${iso}"`);
  return new Date(ms).toISOString();
}

/** The JSON Feed 1.1 subscription for a scope (`application/feed+json`). */
export function toWatchJsonFeed(opts: {
  title: string;
  selfUrl: string;
  pageUrl: string;
  items: readonly WatchItemV2[];
  builtAt: string;
  itemUrl: (handle: string) => string;
}): string {
  const body = {
    version: "https://jsonfeed.org/version/1.1",
    title: opts.title,
    home_page_url: opts.pageUrl,
    feed_url: opts.selfUrl,
    description:
      "Upcoming public decisions about surveillance technology — the SIG decision calendar.",
    items: opts.items.map((item) => {
      const url = opts.itemUrl(item.handle);
      return {
        id: url,
        url,
        title: `${feedDateLine(item)} — ${item.title}`,
        content_text: feedDescription(item, url),
        date_published: jsonStamp(item.first_seen ?? item.date),
        ...(item.last_checked ? { date_modified: jsonStamp(item.last_checked) } : {}),
        tags: [item.kind, item.date_certainty ?? "stated"],
        _sig: {
          handle: item.handle,
          kind: item.kind,
          status: item.status ?? "upcoming",
          alert_date: item.date,
          date_kind: item.date_kind,
          date_certainty: item.date_certainty ?? "stated",
          cancelled: feedStatus(item) === "CANCELLED",
          built_at: jsonStamp(opts.builtAt),
        },
      };
    }),
  };
  return `${JSON.stringify(body, null, 2)}\n`;
}

// --- OPML 2.0 --------------------------------------------------------------- //

/**
 * The OPML bundle — one `type="rss"` outline for `all` plus every emitted
 * place page (D-K7-5: an empty place is still a valid subscription), plus a
 * nested group per kind/facet so a reader can pick scopes. `xmlUrl` is the
 * `.xml` feed, `htmlUrl` the page.
 */
export function toWatchOpml(opts: {
  scopes: readonly WatchFeedScope[];
  builtAt: string;
  feedUrl: (path: string, format: WatchFeedFormat) => string;
  pageUrl: (pagePath: string) => string;
}): string {
  const outline = (s: WatchFeedScope, indent: string) =>
    `${indent}<outline text="${xmlEscape(s.title)}" title="${xmlEscape(s.title)}" type="rss" ` +
    `xmlUrl="${xmlEscape(opts.feedUrl(s.path, "xml"))}" htmlUrl="${xmlEscape(opts.pageUrl(s.pagePath))}"/>`;
  const groups: { label: string; scopes: WatchFeedScope[] }[] = [
    { label: "All upcoming decisions", scopes: opts.scopes.filter((s) => s.scope === "all") },
    { label: "By place", scopes: opts.scopes.filter((s) => s.scope === "place") },
    { label: "By kind", scopes: opts.scopes.filter((s) => s.scope === "kind") },
    { label: "By vendor", scopes: opts.scopes.filter((s) => s.scope === "vendor") },
    { label: "By technology", scopes: opts.scopes.filter((s) => s.scope === "technology") },
  ];
  const body: string[] = [];
  for (const group of groups) {
    if (group.scopes.length === 0) continue;
    body.push(`    <outline text="${xmlEscape(group.label)}" title="${xmlEscape(group.label)}">`);
    for (const s of group.scopes) body.push(outline(s, "      "));
    body.push("    </outline>");
  }
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<opml version="2.0">',
    "  <head>",
    "    <title>SIG watch — feed subscriptions</title>",
    `    <dateCreated>${xmlEscape(rssStamp(opts.builtAt))}</dateCreated>`,
    `    <ownerName>SIG</ownerName>`,
    "  </head>",
    "  <body>",
    ...body,
    "  </body>",
    "</opml>",
    "",
  ].join("\n");
}

/** The feed description when an upstream document URL exists — K7's
 *  "evidence link" inside DESCRIPTION (item page remains the canonical
 *  links surface; the upstream URL is appended when recorded). */
export function feedUpstreamNote(item: WatchItemV2): string | null {
  const up = (item.evidence ?? [])
    .map((e) => e.upstream)
    .find((u) => u?.status === "full_url" && u.url);
  return up?.url ? `Source document: ${up.url}` : null;
}

/** `not_recorded` re-export for the feed emitters' named absences. */
export { NOT_RECORDED };
