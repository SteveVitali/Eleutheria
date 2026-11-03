// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.59 (K7 WX-04a / SIG-WATCH-002/003/004/010) — the watch decision-calendar
// page model: the 90-day list window, the per-place coverage rule (place +
// children), the typed empty-cause classes, the facets and pagination, and the
// SIG-WATCH-002 guard — an `upper_bound` date is NEVER labelled a deadline.
import { describe, expect, it } from "vitest";
import {
  CERTAINTY_LABELS,
  coverageStatement,
  evidenceRows,
  facetValues,
  historyItems,
  itemDateLabel,
  itemPlaceHref,
  itemsForKind,
  itemsForPlace,
  itemsForTechnology,
  itemsForVendor,
  kindsPresent,
  listItems,
  pageCount,
  pageNumbers,
  pageSlice,
  parsePlacePath,
  placeEmptiness,
  upstreamDisplay,
  WATCH_KINDS,
  WATCH_PAGE_SIZE,
  type WatchItemV2,
} from "../../src/lib/watch-v2";
import { WATCH_V2_FIXTURE } from "../../src/lib/watch-v2-fixture";
import { watchContext } from "../../src/lib/watch-context";

const ENV = WATCH_V2_FIXTURE;
const CTX = watchContext();

describe("the fixture envelope (sig/watch/2)", () => {
  it("exercises all six §5.2 kinds", () => {
    expect(kindsPresent(ENV.items)).toEqual([...WATCH_KINDS]);
  });
  it("every item carries exactly one alert date with kind + certainty", () => {
    for (const item of ENV.items) {
      expect(item.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(item.date_kind.length).toBeGreaterThan(0);
      expect(["stated", "derived", "upper_bound"]).toContain(item.date_certainty);
    }
  });
});

describe("itemDateLabel — SIG-WATCH-002", () => {
  it("never renders 'deadline' wording for an upper_bound date", () => {
    const upper = ENV.items.find((i) => i.date_certainty === "upper_bound")!;
    const dl = itemDateLabel(upper);
    expect(dl.certaintyLabel).toBe("latest possible date");
    expect(dl.kindLabel).not.toContain("deadline");
    // The certainty label is the honest bound wording — never "deadline".
    expect(CERTAINTY_LABELS.upper_bound).toBe("latest possible date");
  });
  it("keeps the stated/derived kind wording for non-upper-bound items", () => {
    const renewal = ENV.items.find((i) => i.kind === "renewal_deadline")!;
    expect(itemDateLabel(renewal).kindLabel).toBe("notice deadline");
    expect(itemDateLabel(renewal).certaintyLabel).toBe("derived");
  });
});

describe("listItems — the declared 90-day window", () => {
  it("lists only items on/before as_of + list_days, sorted by date", () => {
    const items = listItems(ENV);
    // The renewal at 2027-01-02 is beyond the 90-day list window from
    // as_of 2026-09-22 (horizon 2026-12-21) — excluded; the rest list.
    expect(items.find((i) => i.kind === "renewal_deadline")).toBeUndefined();
    for (let i = 1; i < items.length; i++) {
      expect(items[i]!.date >= items[i - 1]!.date).toBe(true);
    }
  });
  it("honours the envelope's own window value, not a hard-coded one", () => {
    const env = { ...ENV, build: { windows: { list_days: 10 } }, items: ENV.items };
    const items = listItems(env);
    const horizon = "2026-10-02";
    for (const i of items) expect(i.date <= horizon).toBe(true);
  });
});

describe("placePages + itemsForPlace — the place+children rule", () => {
  it("emits a page for every coverage place plus the unplaced bucket", () => {
    const paths = CTX.pages.map((p) => p.path);
    expect(paths).toContain("usa");
    expect(paths).toContain("usa/ok/oklahoma-city-4064000");
    expect(paths).toContain("usa/tx/harris-county-48201");
    expect(paths).toContain("unplaced");
  });
  it("a place page covers its registry children (chain membership)", () => {
    const state = itemsForPlace(ENV.items, "iso3166-2:US-OK");
    // Oklahoma's page shows the OKC-city renewal, the county expiry and the
    // state bill — never the Texas agenda item or the federal grants.
    expect(state.length).toBe(3);
    expect(state.every((i) => (i.place?.chain ?? []).includes("iso3166-2:US-OK"))).toBe(true);
    expect(itemsForPlace(ENV.items, "us.census.geoid.place:4064000").length).toBe(1);
  });
  it("the unplaced bucket lists only items with no place key", () => {
    const unplaced = itemsForPlace(ENV.items, null);
    expect(unplaced.length).toBe(1);
    expect(unplaced[0]!.kind).toBe("grant_period_end");
  });
  it("itemPlaceHref resolves the item's own place page", () => {
    const renewal = ENV.items.find((i) => i.kind === "renewal_deadline")!;
    expect(itemPlaceHref(renewal, CTX.pages)).toBe("watch/place/usa/ok/oklahoma-city-4064000/");
    const unplaced = ENV.items.find((i) => !i.place?.key)!;
    expect(itemPlaceHref(unplaced, CTX.pages)).toBe("watch/place/unplaced/");
  });
});

describe("facets + pagination (K9 §6.1)", () => {
  it("vendor/technology facets mint only values that exist", () => {
    expect(facetValues(ENV.items, "vendor").map((v) => v.id)).toContain("flock_safety");
    const tech = facetValues(ENV.items, "technology");
    expect(tech.map((t) => t.id)).toContain("alpr");
    expect(itemsForVendor(ENV.items, "flock_safety").length).toBe(1);
    expect(itemsForTechnology(ENV.items, "alpr").length).toBe(2);
  });
  it("the generated grant corpus crosses the 50-row page bound", () => {
    const grants = itemsForKind(ENV.items, "grant_period_end");
    expect(grants.length).toBe(53);
    expect(pageCount(grants.length)).toBe(2);
    expect(pageSlice(grants, 2).length).toBe(3);
    expect(pageNumbers(grants.length)).toEqual([1, 2]);
    // Page 1 is capped at WATCH_PAGE_SIZE; no empty page/2.
    expect(pageSlice(grants, 1).length).toBe(WATCH_PAGE_SIZE);
  });
});

describe("historyItems — the past-window archive", () => {
  it("lists recently_decided/past items for a place, not upcoming ones", () => {
    const ok = historyItems(ENV.items, "iso3166-2:US-OK", "2026-09-22");
    expect(ok.map((i) => i.kind)).toEqual(["legislative_action"]);
  });
});

describe("parsePlacePath — the rest-param pagination form", () => {
  it("splits a bare path and a page suffix", () => {
    expect(parsePlacePath("usa/ok")).toEqual({ path: "usa/ok", page: 1 });
    expect(parsePlacePath("usa/ok/page/3")).toEqual({ path: "usa/ok", page: 3 });
    expect(parsePlacePath("")).toBeNull();
  });
});

describe("placeEmptiness — SIG-WATCH-010's typed cause classes", () => {
  const pages = CTX.pages;
  const find = (path: string) => pages.find((p) => p.path === path)!;

  it("a monitored place with zero items is 'none found', never a research gap", () => {
    const cleveland = find("usa/ok/cleveland-county-40131");
    expect(placeEmptiness(cleveland, ENV.coverage, pages, CTX.names)).toBe("none_found");
    // A state with a monitored county reads 'none found' too — the place
    // page covers its children.
    const ok = find("usa/ok");
    expect(placeEmptiness(ok, ENV.coverage, pages, CTX.names)).toBe("none_found");
  });
  it("a place SIG does not check is 'not monitored'", () => {
    const germany = find("deu");
    expect(placeEmptiness(germany, ENV.coverage, pages, CTX.names)).toBe("not_monitored");
    const norman = find("usa/ok/norman-city-4055000");
    expect(placeEmptiness(norman, ENV.coverage, pages, CTX.names)).toBe("not_monitored");
  });
  it("a missing coverage block is the pipeline cause 'not connected'", () => {
    const okc = find("usa/ok/oklahoma-city-4064000");
    expect(placeEmptiness(okc, undefined)).toBe("not_connected");
  });
  it("the coverage statement names monitored tenants + last checked", () => {
    const stmt = coverageStatement(find("usa"), ENV.coverage);
    expect(stmt.tenantsRegistered).toBe(3);
    expect(stmt.tenantJurisdictions).toContain("Oklahoma City");
    expect(stmt.lastChecked).toBe(ENV.coverage!.last_checked);
  });
});

describe("upstreamDisplay — the J3 §5.3 forms (SIG-WATCH-003)", () => {
  it("renders full_url as a link, host_only as host+hash, withheld as the named absence", () => {
    expect(upstreamDisplay({ status: "full_url", url: "https://x.gov/d" }).href).toBe("https://x.gov/d");
    const host = upstreamDisplay({ status: "host_only", host: "x.gov", path_sha256: "abc" });
    expect(host.href).toBe("https://x.gov/");
    expect(host.display).toContain("x.gov");
    expect(upstreamDisplay({ status: "withheld_by_policy" }).href).toBeNull();
    expect(upstreamDisplay({ status: "no_upstream_url_recorded" }).href).toBeNull();
    expect(upstreamDisplay(undefined).display).toBe("no_upstream_url_recorded");
  });
});

describe("evidenceRows — deterministic order", () => {
  it("sorts by predicate then claim id", () => {
    const item: WatchItemV2 = {
      handle: "h",
      title: "t",
      kind: "contract_expiry",
      date: "2026-01-01",
      date_kind: "expiry",
      date_certainty: "stated",
      evidence: [
        { claim_id: "b", predicate: "z" },
        { claim_id: "a", predicate: "y" },
      ],
    };
    expect(evidenceRows(item).map((e) => e.claim_id)).toEqual(["a", "b"]);
  });
});
