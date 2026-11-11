// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.34 (K7 WX-04b / SIG-WATCH-005, SIG-WATCH-006) — the feed surface e2e:
// every emitted feed validates at the wire level (XML parse in-browser for
// RSS/OPML, RFC 5545 shape for iCal, JSON Feed 1.1 fields), served with its
// registered content type, timestamps from the watch build, OPML covering
// every place feed, and the directory + subscribe links emitting.
import { test, expect } from "@playwright/test";

const unfold = (s: string) => s.replace(/\r\n /g, "");

test.describe("watch feeds — scoped iCal (SIG-WATCH-005)", () => {
  test("the all feed is a valid VCALENDAR with build-time DTSTAMP and production UIDs", async ({
    request,
  }) => {
    const res = await request.get("/watch/feeds/all.ics");
    expect(res.ok()).toBeTruthy();
    expect(res.headers()["content-type"]).toContain("text/calendar");
    const body = unfold(await res.text());
    expect(body).toContain("BEGIN:VCALENDAR");
    expect(body).toContain("VERSION:2.0");
    expect(body).toContain("REFRESH-INTERVAL;VALUE=DURATION:P1D");
    expect(body).toContain("X-PUBLISHED-TTL:P1D");
    // UID shape: handle @ the production domain — never sig.example.
    expect(body).toMatch(/UID:W-[A-Za-z0-9-]+@surveillancegraph\.org/);
    expect(body).not.toContain("sig.example");
    // DTSTAMP = the watch build's generated_at (2026-09-22 fixture stamp —
    // SIG-WATCH-006: the wire's own stamp, never a code literal).
    expect(body).toMatch(/DTSTAMP:\d{8}T\d{6}Z/);
    expect(body).toMatch(/DTSTART;VALUE=DATE:\d{8}/);
    expect(body).toMatch(/SEQUENCE:\d+/);
    expect(body).toMatch(/STATUS:(CONFIRMED|CANCELLED)/);
    expect(body).toMatch(/URL:https:\/\/surveillancegraph\.org\/watch\/item\//);
  });

  test("an empty place feed still validates — one UTC VTIMEZONE (D-K7-5)", async ({ request }) => {
    const res = await request.get("/watch/feeds/place/deu.ics");
    expect(res.ok()).toBeTruthy();
    const body = unfold(await res.text());
    expect(body).toContain("BEGIN:VTIMEZONE");
    expect(body).toContain("TZID:UTC");
    expect(body).not.toContain("BEGIN:VEVENT");
  });

  test("a per-item .ics carries one VEVENT for its own item", async ({ request }) => {
    const res = await request.get(
      "/watch/feeds/item/W-us-ok-oklahoma-city-4064000-renewal-c100-ab12.ics",
    );
    expect(res.ok()).toBeTruthy();
    const body = unfold(await res.text());
    expect((body.match(/BEGIN:VEVENT/g) ?? []).length).toBe(1);
    expect(body).toContain("UID:W-us-ok-oklahoma-city-4064000-renewal-c100-ab12@surveillancegraph.org");
    expect(body).toContain("DTSTART;VALUE=DATE:20270102");
  });

  test("kind and facet feeds emit for their scopes", async ({ request }) => {
    for (const p of [
      "/watch/feeds/kind/agenda_item.ics",
      "/watch/feeds/vendor/flock_safety.ics",
      "/watch/feeds/technology/alpr.ics",
    ]) {
      const res = await request.get(p);
      expect(res.ok(), p).toBeTruthy();
      expect((await res.text()).startsWith("BEGIN:VCALENDAR")).toBeTruthy();
    }
  });
});

test.describe("watch feeds — RSS 2.0 + JSON Feed (SIG-WATCH-005)", () => {
  test("the all.xml feed parses as RSS 2.0 with atom self-link", async ({ page, request }) => {
    const res = await request.get("/watch/feeds/all.xml");
    expect(res.ok()).toBeTruthy();
    expect(res.headers()["content-type"]).toContain("application/rss+xml");
    const text = await res.text();
    // In-browser XML parse — a well-formed document, never a parser error.
    await page.setContent(`<meta charset="utf-8"><pre id="x"></pre>`);
    const shape = await page.evaluate(async (xml) => {
      const doc = new DOMParser().parseFromString(xml, "text/xml");
      const err = doc.querySelector("parsererror");
      if (err) return { ok: false, err: err.textContent };
      const rss = doc.querySelector("rss");
      const chan = doc.querySelector("channel");
      const self = chan?.querySelector('link[rel="self"], atom|link[rel="self"]');
      const items = [...doc.querySelectorAll("item")];
      return {
        ok: true,
        rssVersion: rss?.getAttribute("version"),
        ttl: chan?.querySelector("ttl")?.textContent,
        lastBuild: !!chan?.querySelector("lastBuildDate"),
        self: self?.getAttribute("href"),
        itemCount: items.length,
        guid: items[0]?.querySelector("guid")?.textContent,
        pubDate: items[0]?.querySelector("pubDate")?.textContent,
      };
    }, text);
    expect(shape.ok).toBeTruthy();
    expect(shape.rssVersion).toBe("2.0");
    expect(shape.ttl).toBe("1440");
    expect(shape.lastBuild).toBeTruthy();
    expect(shape.self).toContain("/watch/feeds/all.xml");
    expect(shape.itemCount).toBeGreaterThan(0);
    expect(shape.guid).toContain("/watch/item/");
    expect(shape.pubDate).toBeTruthy();
    // pubDate is first_seen — never the future decision date itself.
    expect(text).not.toContain("<pubDate>Sat, 02 Jan 2027");
  });

  test("the all.json feed is JSON Feed 1.1", async ({ request }) => {
    const res = await request.get("/watch/feeds/all.json");
    expect(res.ok()).toBeTruthy();
    expect(res.headers()["content-type"]).toContain("application/feed+json");
    const doc = await res.json();
    expect(doc.version).toBe("https://jsonfeed.org/version/1.1");
    expect(doc.feed_url).toContain("/watch/feeds/all.json");
    expect(doc.items.length).toBeGreaterThan(0);
    const item = doc.items[0];
    expect(item.id).toContain("/watch/item/");
    // The feed stamp is the envelope's own generated_at — the same stamp the
    // .ics emits as DTSTAMP (SIG-WATCH-006, never a code literal).
    const ics = unfold(await (await request.get("/watch/feeds/all.ics")).text());
    const dtstamp = ics.match(/DTSTAMP:(\d{8}T\d{6}Z)/)?.[1];
    expect(new Date(doc._sig?.built_at ?? doc.items[0]._sig.built_at).toISOString()).toBeTruthy();
    expect(
      doc.items[0]._sig.built_at.replace(/[-:]/g, "").replace(/\.\d{3}/, ""),
    ).toBe(dtstamp);
    expect(item.id).toContain("/watch/item/");
  });
});

test.describe("watch feeds — OPML + directory", () => {
  test("feeds.opml parses and names every place feed", async ({ page, request }) => {
    const res = await request.get("/watch/feeds.opml");
    expect(res.ok()).toBeTruthy();
    const text = await res.text();
    await page.setContent(`<meta charset="utf-8">`);
    const shape = await page.evaluate(async (xml) => {
      const doc = new DOMParser().parseFromString(xml, "text/xml");
      if (doc.querySelector("parsererror")) return { ok: false, outlines: [] as string[] };
      return {
        ok: doc.documentElement.tagName === "opml",
        outlines: [...doc.querySelectorAll('outline[type="rss"]')].map(
          (o) => o.getAttribute("xmlUrl") ?? "",
        ),
      };
    }, text);
    expect(shape.ok).toBeTruthy();
    expect(shape.outlines.length).toBeGreaterThan(10);
    expect(shape.outlines.some((u) => u.endsWith("/watch/feeds/place/usa/tx.xml"))).toBeTruthy();
    expect(shape.outlines.some((u) => u.endsWith("/watch/feeds/place/deu.xml"))).toBeTruthy();
  });

  test("the directory lists the scoped feeds, the OPML and the how-to", async ({ page }) => {
    await page.goto("/watch/feeds/");
    const rows = page.getByTestId("feed-row");
    // 1 all + 14 place + 6 kind + 1 vendor + 5 technology scopes.
    await expect(rows).toHaveCount(27);
    await expect(page.getByTestId("feed-opml")).toHaveAttribute("href", /\/watch\/feeds\.opml$/);
    const first = rows.first();
    await expect(first.getByTestId("feed-ics")).toHaveAttribute("href", /\.ics$/);
    await expect(first.getByTestId("feed-rss")).toHaveAttribute("href", /\.xml$/);
    await expect(first.getByTestId("feed-json")).toHaveAttribute("href", /\.json$/);
    await expect(page.locator("main")).toContainText(/no email list|no accounts/i);
    await expect(page.locator("main")).toContainText(/JSON Feed 1\.1/);
  });

  test("place and item pages link their feeds", async ({ page }) => {
    await page.goto("/watch/place/usa/ok/");
    await expect(page.getByTestId("watch-subscribe-ics")).toHaveAttribute(
      "href",
      /\/watch\/feeds\/place\/usa\/ok\.ics$/,
    );
    await page.goto("/watch/item/W-us-ok-expiry-rtcc-77cd/");
    await expect(page.getByTestId("item-ics")).toHaveAttribute(
      "href",
      /\/watch\/feeds\/item\/W-us-ok-expiry-rtcc-77cd\.ics$/,
    );
  });
});
