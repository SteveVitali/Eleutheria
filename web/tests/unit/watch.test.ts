// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The §39.5 procurement/renewal watch, tested on the pure logic (SIG-UI-026/027,
// SIG-UI-014b): the derived decision date the watch keys on, and the iCal + RSS
// subscriptions by jurisdiction.
import { describe, expect, it } from "vitest";
import {
  alertItemsForJurisdiction,
  itemsForJurisdiction,
  jurisdictionSlug,
  resolveWatchItem,
  toICal,
  toRss,
  watchEventUid,
  watchJurisdictions,
} from "../../src/lib/watch";
import type { ContractWatchItem } from "../../src/lib/watch";
import { WATCH_ITEMS } from "../../src/lib/watch-evidence-fixture";
import { CONTESTED_MARKER } from "../../src/lib/epistemic";

const okcAuto = WATCH_ITEMS.find((i) => i.contract_id === "contract:okcpd-alpr")!;
const okcNonAuto = WATCH_ITEMS.find((i) => i.contract_id === "contract:okcpd-rtcc")!;

describe("the watch keys on next_decision_date, not expiry (SIG-UI-026, SIG-UI-014b)", () => {
  it("derives the notice deadline = expiry − notice window for an auto-renewing contract", () => {
    const r = resolveWatchItem(okcAuto);
    // Appendix-D: 2027-04-02 minus a 90-day notice window is 2027-01-02.
    expect(r.next_decision_date).toBe("2027-01-02");
    expect(r.notice_deadline).toBe("2027-01-02");
    // The decision date is NOT the expiry date — that is the whole point.
    expect(r.expiry_date).toBe("2027-04-02");
    expect(r.next_decision_date).not.toBe(r.expiry_date);
  });

  it("uses the expiry itself when the contract does not auto-renew", () => {
    const r = resolveWatchItem(okcNonAuto);
    expect(r.next_decision_date).toBe("2026-11-30");
    expect(r.next_decision_date).toBe(r.expiry_date);
  });

  it("has no dated alert when there is no expiry", () => {
    const noExpiry: ContractWatchItem = {
      ...okcAuto,
      contract_id: "contract:none",
      termination: { auto_renews: false, notice_window_days: null, expiry_date: null },
    };
    expect(resolveWatchItem(noExpiry).next_decision_date).toBeNull();
  });
});

describe("subscriptions are offered by jurisdiction (SIG-UI-027)", () => {
  it("splits the watch by jurisdiction, each feed non-empty", () => {
    const js = watchJurisdictions(WATCH_ITEMS);
    expect(js).toContain("Oklahoma City");
    expect(js).toContain("Tulsa");
    for (const j of js) {
      expect(itemsForJurisdiction(WATCH_ITEMS, j).length).toBeGreaterThan(0);
      expect(alertItemsForJurisdiction(WATCH_ITEMS, j).length).toBeGreaterThan(0);
    }
  });

  it("sorts the alert items by decision date within a jurisdiction", () => {
    const alerts = alertItemsForJurisdiction(WATCH_ITEMS, "Oklahoma City");
    const dates = alerts.map((a) => a.next_decision_date);
    expect([...dates]).toEqual([...dates].sort());
  });

  it("slugs a jurisdiction name for the feed path", () => {
    expect(jurisdictionSlug("Oklahoma City")).toBe("oklahoma-city");
  });
});

describe("iCal subscription is valid and keyed on the decision date (SIG-UI-027)", () => {
  const ics = toICal(WATCH_ITEMS, "Oklahoma City", "2026-08-20");

  it("is a well-formed VCALENDAR with a VEVENT per dated alert", () => {
    expect(ics.startsWith("BEGIN:VCALENDAR\r\n")).toBe(true);
    expect(ics.trimEnd().endsWith("END:VCALENDAR")).toBe(true);
    expect(ics.includes("VERSION:2.0")).toBe(true);
    const events = ics.match(/BEGIN:VEVENT/g) ?? [];
    expect(events.length).toBe(alertItemsForJurisdiction(WATCH_ITEMS, "Oklahoma City").length);
    // CRLF line endings per RFC 5545.
    expect(ics.includes("\r\n")).toBe(true);
  });

  it("keys DTSTART on next_decision_date (2027-01-02), never the expiry (2027-04-02)", () => {
    expect(ics).toContain("DTSTART;VALUE=DATE:20270102");
    expect(ics).not.toContain("DTSTART;VALUE=DATE:20270402");
  });

  it("uses a deterministic, stable UID and DTSTAMP (no wall-clock)", () => {
    const uid = watchEventUid(resolveWatchItem(okcAuto) as never);
    expect(ics).toContain(`UID:${uid}`);
    expect(ics).toContain("DTSTAMP:20260820T000000Z");
    // Re-emitting is byte-identical.
    expect(toICal(WATCH_ITEMS, "Oklahoma City", "2026-08-20")).toBe(ics);
  });

  it("carries the contested marker for a contested contract (SIG-UI-008)", () => {
    expect(ics).toContain(CONTESTED_MARKER.glyph);
  });

  it("folds every content line to ≤75 octets (RFC 5545 §3.1)", () => {
    const enc = new TextEncoder();
    // A continuation line begins with a single space; content lines otherwise.
    for (const line of ics.split("\r\n")) {
      expect(enc.encode(line).length).toBeLessThanOrEqual(75);
    }
  });
});

describe("RSS subscription is valid and keyed on the decision date (SIG-UI-027)", () => {
  const rss = toRss(WATCH_ITEMS, "Oklahoma City", "https://sig.example");

  it("is a well-formed RSS 2.0 channel with an item per dated alert", () => {
    expect(rss).toContain('<rss version="2.0">');
    expect(rss).toContain("<channel>");
    const items = rss.match(/<item>/g) ?? [];
    expect(items.length).toBe(alertItemsForJurisdiction(WATCH_ITEMS, "Oklahoma City").length);
  });

  it("titles/keys each item on the decision date and carries a stable guid", () => {
    expect(rss).toContain("Decision deadline 2027-01-02");
    expect(rss).toContain('<guid isPermaLink="false">sig-watch-contract:okcpd-alpr-20270102@sig.example</guid>');
    expect(rss).toContain("<pubDate>");
  });

  it("escapes XML and carries the contested marker (SIG-UI-008)", () => {
    // The Tulsa feed has no contested item; the OKC feed does.
    expect(rss).toContain(CONTESTED_MARKER.glyph);
    expect(toRss(WATCH_ITEMS, "Tulsa", "https://sig.example")).not.toContain(CONTESTED_MARKER.glyph);
  });
});
