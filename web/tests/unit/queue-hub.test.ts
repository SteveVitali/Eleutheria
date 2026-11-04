// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { describe, expect, it } from "vitest";
import {
  PLACE_TYPE_THRESHOLD,
  QUEUE_PAGE_SIZE,
  QUEUE_SORTS,
  childFacets,
  evidenceDateOf,
  facetValues,
  nestedTypeFacets,
  pageCount,
  pageNumbers,
  pageSlice,
  parseQueuePlacePath,
  placeFacets,
  placeSlugOf,
  queuePlaceTypeHref,
  roleLabel,
  sortQueue,
  tasksForPlace,
  tasksForRole,
  tasksForType,
  typeLabel,
  UNPLACED_PLACE,
} from "../../src/lib/queue-hub";
import {
  JURISDICTION_CLAIMS,
  QUEUE_AS_OF,
  QUEUE_CAMPAIGNS,
  RESEARCH_QUEUE,
} from "../../src/lib/corrections-methodology-fixture";
import type { ResearchTaskCard } from "../../src/lib/research-queue";

describe("place facets (SIG-RQ-004)", () => {
  it("every card maps to exactly one place facet and totals reconcile", () => {
    const facets = placeFacets(RESEARCH_QUEUE);
    expect(facets.reduce((n, f) => n + f.tasks, 0)).toBe(RESEARCH_QUEUE.length);
    expect(facets.map((f) => f.slug)).toContain("usa/ok/oklahoma-city-4064000");
    expect(facets.map((f) => f.slug)).toContain(UNPLACED_PLACE);
  });

  it("a parent place covers its slug-path children (state → cities)", () => {
    const synthetic = RESEARCH_QUEUE.map((c) => ({
      ...c,
      place: { key: "x", slug: "usa/ok", name: "Oklahoma" },
    }));
    const covered = tasksForPlace(synthetic, "usa");
    expect(covered).toHaveLength(RESEARCH_QUEUE.length);
    expect(tasksForPlace(synthetic, "usa/ok")).toHaveLength(RESEARCH_QUEUE.length);
    expect(tasksForPlace(synthetic, "usa/tx")).toHaveLength(0);
  });

  it("children listing names direct children only", () => {
    const facets = [
      { slug: "usa", name: "United States", tasks: 1, unplaced: false },
      { slug: "usa/ok", name: "Oklahoma", tasks: 2, unplaced: false },
      { slug: "usa/ok/tulsa-4075000", name: "Tulsa", tasks: 1, unplaced: false },
    ];
    expect(childFacets(facets, "usa").map((f) => f.slug)).toEqual(["usa/ok"]);
    expect(childFacets(facets, "usa/ok").map((f) => f.slug)).toEqual(["usa/ok/tulsa-4075000"]);
  });

  it("a card with no place resolves the unplaced bucket, never a guessed path", () => {
    const card: ResearchTaskCard = {
      ...RESEARCH_QUEUE[0]!,
      place: undefined,
      jurisdiction: "",
    };
    expect(placeSlugOf(card)).toBe(UNPLACED_PLACE);
  });
});

describe("type + role facets — totals reconcile per dimension", () => {
  it("facet counts sum to the lane total on each dimension", () => {
    for (const dim of ["task_type", "assignee_class"] as const) {
      const values = facetValues(RESEARCH_QUEUE, dim);
      expect(values.reduce((n, f) => n + f.tasks, 0)).toBe(RESEARCH_QUEUE.length);
    }
  });

  it("the filtered task sets are disjoint-covering per dimension", () => {
    const byType = new Set(tasksForType(RESEARCH_QUEUE, "conflicting_retention"));
    expect(byType.size).toBe(1);
    expect(tasksForRole(RESEARCH_QUEUE, "field_mapper").length).toBe(1);
    expect(typeLabel("conflicting_retention")).toBe("Conflicting Retention");
    expect(roleLabel("records_requester")).toBe("File a records request");
  });

  it("nested type facets mint only above the >50-task threshold (K11 §5.2)", () => {
    expect(nestedTypeFacets(RESEARCH_QUEUE, "usa/ok/oklahoma-city-4064000")).toEqual([]);
    const big = Array.from({ length: PLACE_TYPE_THRESHOLD + 1 }, (_, i) => ({
      ...RESEARCH_QUEUE[i % RESEARCH_QUEUE.length]!,
      task_id: `t-${i}`,
      place: { key: "x", slug: "usa/ok", name: "Oklahoma" },
    }));
    const nested = nestedTypeFacets(big, "usa/ok");
    expect(nested.length).toBeGreaterThan(0);
    expect(nested.reduce((n, f) => n + f.tasks, 0)).toBe(PLACE_TYPE_THRESHOLD + 1);
  });
});

describe("sorts (K11 §4.2)", () => {
  it("priority is the queue order; newest is generated_at desc; oldest is stale-first", () => {
    const pri = sortQueue(RESEARCH_QUEUE, JURISDICTION_CLAIMS, QUEUE_AS_OF, "priority");
    expect(pri).toHaveLength(RESEARCH_QUEUE.length);
    const newest = sortQueue(RESEARCH_QUEUE, JURISDICTION_CLAIMS, QUEUE_AS_OF, "newest");
    const dates = newest.map((c) => c.generated_at ?? "");
    expect([...dates].sort().reverse()).toEqual(dates);
    const oldest = sortQueue(RESEARCH_QUEUE, JURISDICTION_CLAIMS, QUEUE_AS_OF, "oldest");
    const eds = oldest.map(evidenceDateOf);
    expect([...eds].sort()).toEqual(eds);
    for (const k of QUEUE_SORTS) {
      expect(sortQueue(RESEARCH_QUEUE, JURISDICTION_CLAIMS, QUEUE_AS_OF, k)).toHaveLength(
        RESEARCH_QUEUE.length,
      );
    }
  });

  it("an undated card never reads as the oldest evidence", () => {
    const undated: ResearchTaskCard = {
      ...RESEARCH_QUEUE[0]!,
      task_id: "undated",
      generated_at: undefined,
      trigger: undefined,
    };
    const sorted = sortQueue([undated, ...RESEARCH_QUEUE], [], "", "oldest");
    expect(sorted.at(-1)!.task_id).toBe("undated");
  });
});

describe("pagination (≤50 cards per page, K9 §6.1)", () => {
  it("slices at the 50-card page size and never mints an empty page", () => {
    expect(QUEUE_PAGE_SIZE).toBe(50);
    expect(pageCount(0)).toBe(1);
    expect(pageCount(50)).toBe(1);
    expect(pageCount(51)).toBe(2);
    expect(pageNumbers(120)).toEqual([1, 2, 3]);
    expect(pageSlice(RESEARCH_QUEUE, 1).length).toBe(RESEARCH_QUEUE.length);
    expect(pageSlice(RESEARCH_QUEUE, 2)).toEqual([]);
  });
});

describe("the place rest-path parser", () => {
  it("parses every minted trailer shape", () => {
    expect(parseQueuePlacePath("usa/ok")).toEqual({
      path: "usa/ok",
      type: undefined,
      sort: "priority",
      page: 1,
    });
    expect(parseQueuePlacePath("usa/ok/page/2")).toEqual({
      path: "usa/ok",
      type: undefined,
      sort: "priority",
      page: 2,
    });
    expect(parseQueuePlacePath("usa/ok/sort/newest")).toEqual({
      path: "usa/ok",
      type: undefined,
      sort: "newest",
      page: 1,
    });
    expect(parseQueuePlacePath("usa/ok/sort/oldest/page/3")).toEqual({
      path: "usa/ok",
      type: undefined,
      sort: "oldest",
      page: 3,
    });
    expect(parseQueuePlacePath("usa/ok/type/coverage_hole")).toEqual({
      path: "usa/ok",
      type: "coverage_hole",
      sort: "priority",
      page: 1,
    });
    expect(parseQueuePlacePath("usa/ok/type/coverage_hole/sort/newest/page/2")).toEqual({
      path: "usa/ok",
      type: "coverage_hole",
      sort: "newest",
      page: 2,
    });
  });

  it("fails closed on a shape the family never mints (SIG-ENG-042)", () => {
    expect(parseQueuePlacePath("")).toBeNull();
    expect(parseQueuePlacePath("usa/ok/sort/bogus")).toBeNull();
    expect(parseQueuePlacePath("usa/ok/type")).toBeNull();
  });
});

describe("campaigns (SIG-RQ-006 / D-K11-1)", () => {
  it("the fixture campaign carries the v1 contract fields", () => {
    expect(QUEUE_CAMPAIGNS.length).toBeGreaterThan(0);
    for (const c of QUEUE_CAMPAIGNS) {
      expect(c.schema).toBe("sig.queue-campaign/1");
      expect(c.handle).toMatch(/^M-/);
      expect(c.member_count).toBeGreaterThan(0);
      expect(c.predicate_id.length).toBeGreaterThan(0);
    }
  });
});

describe("route helpers", () => {
  it("build the family hrefs without a leading slash", () => {
    expect(queuePlaceTypeHref("usa/ok", "coverage_hole", "newest", 2)).toBe(
      "research-queue/place/usa/ok/type/coverage_hole/sort/newest/page/2/",
    );
  });
});
