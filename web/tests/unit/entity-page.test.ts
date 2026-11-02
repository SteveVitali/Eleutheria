// SPDX-License-Identifier: Apache-2.0
/**
 * P36.41 — the `sig.entity-page/1` contract A mirror (K2 §6.2 / A-10).
 * Fixture-level: the committed fixtures exercise the answered decision
 * verbatim (D-K2-1 = b + c) — an auto-allowed organisation renders its
 * keyed twin; every other organisation is typed `not_yet_reviewed`,
 * never a silent absence and never a raw identifier as a label.
 */

import { describe, expect, it } from "vitest";

import {
  ENTITY_LABEL_FIXTURES,
  ENTITY_PAGE_FIXTURES,
  ENTITY_PAGE_SCHEMA,
  ENTITY_PAGE_TWIN_FIXTURE,
  ER_DISCLOSURE,
  ITEMS_PER_RELATION,
  PAGE_KINDS,
  WITHHELD_RELATIONSHIPS_NOTICE,
  entityIndex,
  isEntityPageTwin,
  isReviewRecord,
  pageState,
  reviewRecord,
} from "../../src/lib/entity-page";
import { getEntityLabelRows, getEntityPageTwins } from "../../src/lib/data";

const RAW_ID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

describe("pageState — the A-10 decision surface", () => {
  it("types a keyed contract-A entity published", () => {
    for (const kind of PAGE_KINDS) {
      expect(
        pageState({ kind, slug: "x", hash: "abc1234", url_type: kind, url: `/entity/${kind}/x--abc1234/` }),
      ).toBe("published");
    }
  });

  it("types an organisation outside the auto-allow registry not_yet_reviewed", () => {
    const review = ENTITY_LABEL_FIXTURES.find((r) => r.label_state === "not_yet_reviewed")!;
    expect(pageState(review)).toBe("not_yet_reviewed");
    const rec = reviewRecord(review);
    expect(rec.review_state).toBe("not_yet_reviewed");
    expect(rec.kind).toBe("org");
    expect(rec.er_disclosure).toBe(ER_DISCLOSURE);
    // no label, key, url or id — the state is the record (SIG-UI-053/108).
    expect(rec).not.toHaveProperty("label");
    expect(rec).not.toHaveProperty("entity_id");
    expect(rec).not.toHaveProperty("url");
  });

  it("types withheld and person rows withheld — nothing emits", () => {
    expect(pageState({ kind: "org", label_state: "withheld" })).toBe("withheld");
    expect(pageState({ kind: "person" })).toBe("withheld");
  });

  it("types allowed non-contract-A kinds unpaged", () => {
    expect(
      pageState({ kind: "site", slug: "s", hash: "h123456", url_type: "site", url: "/entity/site/s--h123456/" }),
    ).toBe("unpaged");
  });

  it("types an unkeyed organisation not_yet_reviewed, never a broken page", () => {
    expect(pageState({ kind: "org", slug: null, hash: null, url_type: "org", url: null })).toBe(
      "not_yet_reviewed",
    );
  });
});

describe("the twin contract", () => {
  it("accepts the committed fixture twin", () => {
    expect(isEntityPageTwin(ENTITY_PAGE_TWIN_FIXTURE)).toBe(true);
  });

  it("rejects a twin with a foreign schema or a review state", () => {
    expect(isEntityPageTwin({ schema: "sig.other/1" })).toBe(false);
    expect(isEntityPageTwin(reviewRecord({ kind: "org", descriptor: "x" }))).toBe(false);
    expect(isReviewRecord(reviewRecord({ kind: "org", descriptor: "x" }))).toBe(true);
  });

  it("carries the H-2 relationship fields, separately", () => {
    const item = ENTITY_PAGE_TWIN_FIXTURE.relations[0].items[0];
    for (const field of ["relation", "date", "date_kind", "currency", "status", "support", "agreement", "sources", "claim_ids"]) {
      expect(item).toHaveProperty(field);
    }
    expect(item.counterparty.label).toBe("Vigilant Solutions (LEARN)");
    // historical relationships are marked (SIG-UI-116) — never present-tense.
    expect(item.historical).toBe(true);
    expect(item.currency).toBe("HISTORICAL");
  });

  it("marks undated relationships (SIG-UI-088)", () => {
    const undated = ENTITY_PAGE_TWIN_FIXTURE.relations
      .flatMap((g) => g.items)
      .find((i) => i.date_kind === "undated")!;
    expect(undated.date).toBeNull();
    expect(undated.currency).toBe("UNDATED");
  });

  it("carries degree-only facts as node attributes, never relation items", () => {
    const degree = ENTITY_PAGE_TWIN_FIXTURE.access.degree_only[0];
    expect(degree.counts).toEqual([851]);
    for (const grp of ENTITY_PAGE_TWIN_FIXTURE.relations) {
      expect(grp.relation).not.toContain("degree");
    }
    expect(ENTITY_PAGE_TWIN_FIXTURE.access.closures).toEqual([]);
  });

  it("carries the four epistemic fields on every claim group", () => {
    for (const grp of ENTITY_PAGE_TWIN_FIXTURE.claims) {
      expect(grp.envelope).toHaveProperty("status");
      expect(grp.envelope).toHaveProperty("support");
      expect(grp.envelope).toHaveProperty("agreement");
      expect(grp.envelope).toHaveProperty("currency");
    }
  });

  it("keeps contract-B sections as typed empty values", () => {
    expect(ENTITY_PAGE_TWIN_FIXTURE.contradictions).toEqual([]);
    expect(ENTITY_PAGE_TWIN_FIXTURE.timeline).toEqual([]);
    expect(ENTITY_PAGE_TWIN_FIXTURE.related).toEqual({});
    expect(ENTITY_PAGE_TWIN_FIXTURE.downloads).toEqual([]);
  });

  it("carries SIG-UI-080's sentence verbatim where a counterparty withheld", () => {
    expect(ENTITY_PAGE_TWIN_FIXTURE.withheld_notice).toBe(WITHHELD_RELATIONSHIPS_NOTICE);
  });

  it("renders no raw identifier as a label anywhere in the fixture twins", () => {
    for (const twin of Object.values(ENTITY_PAGE_FIXTURES)) {
      expect(RAW_ID_RE.test(twin.label)).toBe(false);
      for (const grp of twin.relations) {
        for (const item of grp.items) {
          if (item.counterparty.label != null) {
            expect(RAW_ID_RE.test(item.counterparty.label)).toBe(false);
          }
        }
        expect(grp.items.length).toBeLessThanOrEqual(ITEMS_PER_RELATION);
      }
    }
  });
});

describe("entityIndex — the SIG-UI-070 hub data", () => {
  it("counts published kinds and carries the ER disclosure", () => {
    const idx = entityIndex(ENTITY_LABEL_FIXTURES);
    const kinds = Object.fromEntries(idx.kinds.map((k) => [k.kind, k.count]));
    expect(kinds.agency).toBe(1);
    expect(kinds.org).toBe(1);
    expect(kinds.portal).toBe(1);
    for (const k of idx.kinds) expect(k.er_disclosure).toBe(ER_DISCLOSURE);
    // every index row is keyed and linked (SIG-UI-053).
    for (const row of idx.rows) expect(row.url).toBeTruthy();
    // the review-state organisation renders typed, never silently.
    expect(idx.review_rows).toHaveLength(1);
    expect(idx.review_rows[0].review_state).toBe("not_yet_reviewed");
  });
});

describe("the data layer", () => {
  it("serves fixture label rows and the fixture twin", () => {
    const rows = getEntityLabelRows();
    expect(rows.length).toBeGreaterThanOrEqual(4);
    const twins = getEntityPageTwins("agency", "acworth-police-department--4g2wm8q");
    expect(twins).toHaveLength(1);
    expect(twins[0].schema).toBe(ENTITY_PAGE_SCHEMA);
    expect(twins[0].label).toBe("Acworth Police Department");
  });

  it("answers an empty twin set for an unissued key — the typed absence", () => {
    expect(getEntityPageTwins("org", "unissued-key--0000000")).toEqual([]);
  });
});
