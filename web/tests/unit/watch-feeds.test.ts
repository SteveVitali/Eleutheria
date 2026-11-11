// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.34 (K7 WX-04b / SIG-WATCH-005, SIG-WATCH-006) — the feed emitters'
 * contract suite: UID stability + domain, SEQUENCE/STATUS, DTSTAMP from the
 * watch build (never a fixture constant), RFC 5545 shape incl. the empty
 * calendar, RSS 2.0 self-link/pubDate rules, JSON Feed 1.1, OPML coverage.
 */

import { describe, expect, it } from "vitest";
import {
  feedBuiltAt,
  feedScopes,
  feedSequence,
  feedStatus,
  feedUid,
  scopeItems,
  toWatchICal,
  toWatchJsonFeed,
  toWatchOpml,
  toWatchRss,
  watchFeedPath,
  watchItemFeedPath,
  WATCH_OPML_PATH,
} from "../../src/lib/watch-feeds";
import { WATCH_V2_FIXTURE } from "../../src/lib/watch-v2-fixture";
import { placePages, WATCH_KINDS } from "../../src/lib/watch-v2";
import type { WatchItemV2 } from "../../src/lib/watch-v2";

const ORIGIN = "https://surveillancegraph.org";
const abs = (p: string) => `${ORIGIN}/${p}`;
const itemUrl = (h: string) => abs(`watch/item/${h}/`);

const SLUG_MAP = new Map<string, string>();
const PAGES = placePages(WATCH_V2_FIXTURE, SLUG_MAP);
const ENVELOPE = WATCH_V2_FIXTURE;

const unfold = (ics: string) => ics.replace(/\r\n /g, "");

describe("feed scopes (SIG-WATCH-004 / D-K7-5)", () => {
  it("emits a feed for every place page, empty or not", () => {
    const scopes = feedScopes(ENVELOPE, PAGES);
    const placeScopePaths = new Set(
      scopes.filter((s) => s.scope === "place").map((s) => s.path),
    );
    for (const page of PAGES) {
      expect(placeScopePaths.has(`place/${page.path}`)).toBe(true);
    }
    // An empty place (Cleveland County / Germany) still mints a feed.
    expect(placeScopePaths.has("place/usa/ok/cleveland-county-40131")).toBe(true);
    expect(placeScopePaths.has("place/deu")).toBe(true);
    // The unplaced data-quality bucket feeds too.
    expect(placeScopePaths.has("place/unplaced")).toBe(true);
  });

  it("emits all six kinds + only the present facet values", () => {
    const scopes = feedScopes(ENVELOPE, PAGES);
    const kinds = scopes.filter((s) => s.scope === "kind").map((s) => s.path);
    expect(kinds.sort()).toEqual(WATCH_KINDS.map((k) => `kind/${k}`).sort());
    const vendors = scopes.filter((s) => s.scope === "vendor").map((s) => s.path);
    expect(vendors).toEqual(["vendor/flock_safety"]);
    const techs = scopes.filter((s) => s.scope === "technology").map((s) => s.path);
    expect(techs).toContain("technology/alpr");
    expect(techs).toContain("technology/surveillance_equipment");
  });

  it("scopeItems covers the place's children (K7 §5.4 chain rule)", () => {
    const ok = scopeItems(ENVELOPE, PAGES, "place/usa/ok")!;
    const handles = ok.items.map((i) => i.handle);
    expect(handles).toContain("W-us-ok-oklahoma-city-4064000-renewal-c100-ab12");
    expect(handles).toContain("W-us-ok-bill-hb-1400-55aa");
    expect(scopeItems(ENVELOPE, PAGES, "kind/no_such_kind")).toBeNull();
    expect(scopeItems(ENVELOPE, PAGES, "vendor/never_matched")).toBeNull();
  });
});

describe("iCal (RFC 5545 / SIG-WATCH-005)", () => {
  const ics = toWatchICal({
    title: "SIG watch — test",
    selfUrl: abs("watch/feeds/all.ics"),
    pageUrl: abs("watch/"),
    items: ENVELOPE.items,
    builtAt: feedBuiltAt(ENVELOPE),
    itemUrl,
  });
  const flat = unfold(ics);

  it("is CRLF-folded at ≤75 octets and opens/closes correctly", () => {
    expect(ics.startsWith("BEGIN:VCALENDAR")).toBe(true);
    expect(ics.endsWith("END:VCALENDAR\r\n")).toBe(true);
    for (const line of ics.split("\r\n")) {
      expect(Buffer.byteLength(line, "utf-8")).toBeLessThanOrEqual(75);
    }
    expect(flat).toContain("VERSION:2.0");
    expect(flat).toContain("REFRESH-INTERVAL;VALUE=DURATION:P1D");
    expect(flat).toContain("X-PUBLISHED-TTL:P1D");
  });

  it("mints stable production-domain UIDs — two builds identical", () => {
    const item = ENVELOPE.items[0]!;
    const uid = feedUid(item);
    expect(uid).toBe(`${item.handle}@surveillancegraph.org`);
    const second = toWatchICal({
      title: "SIG watch — test",
      selfUrl: abs("watch/feeds/all.ics"),
      pageUrl: abs("watch/"),
      items: [item],
      builtAt: feedBuiltAt(ENVELOPE),
      itemUrl,
    });
    expect(unfold(second)).toContain(`UID:${uid}`);
    expect(second).not.toContain("sig.example");
  });

  it("DTSTAMP comes from the watch build, never a fixture constant (SIG-WATCH-006)", () => {
    const stamp = ENVELOPE.generated_at!.replace(/[-:]/g, "").slice(0, 15) + "Z";
    expect(flat).toContain(`DTSTAMP:${stamp}`);
    const other = toWatchICal({
      title: "t",
      selfUrl: abs("watch/feeds/all.ics"),
      pageUrl: abs("watch/"),
      items: [ENVELOPE.items[0]!],
      builtAt: "2030-05-06T07:08:09Z",
      itemUrl,
    });
    expect(unfold(other)).toContain("DTSTAMP:20300506T070809Z");
  });

  it("SEQUENCE stays stable and increments on a recorded date move; STATUS cancels on withdraw/supersede", () => {
    const base = ENVELOPE.items[0]!;
    expect(feedSequence(base)).toBe(0);
    expect(feedStatus(base)).toBe("CONFIRMED");
    const moved: WatchItemV2 = { ...base, status: "superseded" };
    expect(feedSequence(moved)).toBe(1);
    expect(feedUid(moved)).toBe(feedUid(base));
    expect(feedStatus(moved)).toBe("CANCELLED");
    const gone: WatchItemV2 = { ...base, status: "withdrawn" };
    expect(feedStatus(gone)).toBe("CANCELLED");
    const cancelled = toWatchICal({
      title: "t",
      selfUrl: abs("watch/feeds/all.ics"),
      pageUrl: abs("watch/"),
      items: [moved],
      builtAt: feedBuiltAt(ENVELOPE),
      itemUrl,
    });
    expect(unfold(cancelled)).toContain("STATUS:CANCELLED");
    expect(unfold(cancelled)).toContain("SEQUENCE:1");
  });

  it("an empty calendar still carries a VTIMEZONE component", () => {
    const empty = toWatchICal({
      title: "t",
      selfUrl: abs("watch/feeds/place/deu.ics"),
      pageUrl: abs("watch/place/deu/"),
      items: [],
      builtAt: feedBuiltAt(ENVELOPE),
      itemUrl,
    });
    const flat2 = unfold(empty);
    expect(flat2).toContain("BEGIN:VTIMEZONE");
    expect(flat2).toContain("TZID:UTC");
    expect(flat2).not.toContain("BEGIN:VEVENT");
  });

  it("an upper_bound date is never labelled a deadline in feed bytes (SIG-WATCH-002)", () => {
    const upper = ENVELOPE.items.find((i) => i.date_certainty === "upper_bound")!;
    const feed = unfold(
      toWatchICal({
        title: "t",
        selfUrl: abs("x"),
        pageUrl: abs("x"),
        items: [upper],
        builtAt: feedBuiltAt(ENVELOPE),
        itemUrl,
      }),
    );
    expect(feed).toContain("latest possible date");
    const desc = feed.match(/^DESCRIPTION:(.+)$/m)![1]!;
    expect(desc).not.toContain("deadline — the real deadline may be earlier");
  });
});

describe("RSS 2.0 (SIG-WATCH-005)", () => {
  const rss = toWatchRss({
    title: "SIG watch — test",
    selfUrl: abs("watch/feeds/all.xml"),
    pageUrl: abs("watch/"),
    items: ENVELOPE.items,
    builtAt: feedBuiltAt(ENVELOPE),
    itemUrl,
  });

  it("carries atom:link self, lastBuildDate and ttl 1440", () => {
    expect(rss).toContain('<rss version="2.0"');
    expect(rss).toContain("xmlns:atom");
    expect(rss).toContain(`<atom:link href="${abs("watch/feeds/all.xml")}" rel="self"`);
    expect(rss).toContain("<lastBuildDate>");
    expect(rss).toContain("<ttl>1440</ttl>");
  });

  it("pubDate is first_seen, never the future decision date; guid is the item URL", () => {
    const item = ENVELOPE.items.find((i) => i.handle === "W-us-ok-oklahoma-city-4064000-renewal-c100-ab12")!;
    // The decision date 2027-01-02 is a FUTURE date — it must not be pubDate.
    const itemXml = rss.split("<item>").find((s) => s.includes(item.handle) || s.includes(encodeURIComponent(item.handle))) ?? "";
    const body = rss.split("<item>").find((s) => s.includes("C-100")) ?? "";
    const seg = itemXml.length > body.length ? itemXml : body;
    expect(seg).toContain(`<pubDate>${new Date(`${item.first_seen}T00:00:00Z`).toUTCString()}</pubDate>`);
    expect(seg).not.toContain("<pubDate>Sat, 02 Jan 2027");
    expect(seg).toContain(`<guid isPermaLink="true">${itemUrl(item.handle)}</guid>`);
    expect(seg).toContain(`<link>${itemUrl(item.handle)}</link>`);
  });
});

describe("JSON Feed 1.1 (SIG-WATCH-005)", () => {
  it("emits the 1.1 shape with per-item dates and the _sig block", () => {
    const doc = JSON.parse(
      toWatchJsonFeed({
        title: "SIG watch — test",
        selfUrl: abs("watch/feeds/all.json"),
        pageUrl: abs("watch/"),
        items: ENVELOPE.items,
        builtAt: feedBuiltAt(ENVELOPE),
        itemUrl,
      }),
    );
    expect(doc.version).toBe("https://jsonfeed.org/version/1.1");
    expect(doc.feed_url).toBe(abs("watch/feeds/all.json"));
    const first = doc.items.find((i: any) => i._sig.handle === ENVELOPE.items[0]!.handle);
    expect(first.url).toBe(itemUrl(ENVELOPE.items[0]!.handle));
    expect(first.date_published.startsWith(ENVELOPE.items[0]!.first_seen!)).toBe(true);
    expect(first._sig.built_at).toBe(new Date(ENVELOPE.generated_at!).toISOString());
  });
});

describe("OPML (D-K7-5)", () => {
  it("lists all + every place scope as rss outlines", () => {
    const scopes = feedScopes(ENVELOPE, PAGES);
    const opml = toWatchOpml({
      scopes,
      builtAt: feedBuiltAt(ENVELOPE),
      feedUrl: (p, f) => abs(`watch/feeds/${p}.${f}`),
      pageUrl: (p) => abs(p),
    });
    expect(opml).toContain('<opml version="2.0">');
    for (const page of PAGES) {
      expect(opml).toContain(`watch/feeds/place/${page.path}.xml`);
    }
    expect(opml).toContain('type="rss"');
  });
});

describe("feed paths", () => {
  it("mints the committed route shapes", () => {
    expect(watchFeedPath("place/usa/ok", "ics")).toBe("watch/feeds/place/usa/ok.ics");
    expect(watchFeedPath("all", "json")).toBe("watch/feeds/all.json");
    expect(watchItemFeedPath("W-x")).toBe("watch/feeds/item/W-x.ics");
    expect(WATCH_OPML_PATH).toBe("watch/feeds.opml");
  });
});
