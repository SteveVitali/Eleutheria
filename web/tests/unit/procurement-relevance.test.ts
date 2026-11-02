// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { afterEach, describe, expect, it } from "vitest";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  PROCUREMENT_RELEVANCE_FIXTURE,
  PROCUREMENT_RELEVANCE_SCHEMA,
  UNCLASSIFIED_PROCUREMENT_LABEL,
  buyerNoticeRows,
  isProcurementRelevanceDoc,
  isSurveillanceRelevant,
  noticeRowLabel,
  surveillanceNotices,
} from "../../src/lib/procurement-relevance";
import { getProcurementRelevance } from "../../src/lib/data";

const ROWS = PROCUREMENT_RELEVANCE_FIXTURE.rows;
const KEYWORD_HIT = ROWS.find((r) => r.bases.includes("matched_keyword"))!;
const CODE_HIT = ROWS.find((r) => r.bases.includes("product_code"))!;
const UNCLASSIFIED = ROWS.find((r) => r.relevance === "not_classified")!;

const saved = {
  source: process.env.SIG_DATA_SOURCE,
  dir: process.env.SIG_EXPORT_DIR,
};
afterEach(() => {
  if (saved.source === undefined) delete process.env.SIG_DATA_SOURCE;
  else process.env.SIG_DATA_SOURCE = saved.source;
  if (saved.dir === undefined) delete process.env.SIG_EXPORT_DIR;
  else process.env.SIG_EXPORT_DIR = saved.dir;
});

describe("P36.30 procurement relevance — classification both ways (K2 GX-04)", () => {
  it("a fixture notice with a keyword hit is surveillance-related", () => {
    expect(isSurveillanceRelevant(KEYWORD_HIT)).toBe(true);
    expect(KEYWORD_HIT.matched).toContain("surveillance_camera");
    expect(KEYWORD_HIT.buyer_label).toBeNull();
  });

  it("a fixture notice classified by a reviewed CPV code is relevant", () => {
    expect(isSurveillanceRelevant(CODE_HIT)).toBe(true);
    expect(CODE_HIT.matched).toContain("cpv:35120000");
  });

  it("an unclassified notice carries the H-13 label, never a guess", () => {
    expect(isSurveillanceRelevant(UNCLASSIFIED)).toBe(false);
    expect(UNCLASSIFIED.bases).toEqual(["none"]);
    expect(UNCLASSIFIED.buyer_label).toBe(UNCLASSIFIED_PROCUREMENT_LABEL);
    expect(UNCLASSIFIED.buyer_label).toBe(
      "not classified as surveillance-related",
    );
  });
});

describe("P36.30 procurement relevance — the D-K2-5 exclusion posture", () => {
  it("surveillance surfaces draw only relevant notices", () => {
    const drawn = surveillanceNotices(ROWS);
    expect(drawn).toHaveLength(2);
    expect(drawn.map((r) => r.subject_key)).not.toContain(
      UNCLASSIFIED.subject_key,
    );
  });

  it("the unclassified notice still surfaces — as a buyer-page row", () => {
    // D-K2-5: excluded from surveillance surfaces, never silently dropped.
    const buyerRows = buyerNoticeRows(ROWS);
    const row = buyerRows.find((r) => r.subject_key === UNCLASSIFIED.subject_key);
    expect(row).toBeDefined();
    expect(noticeRowLabel(row!)).toBe("not classified as surveillance-related");
  });

  it("a relevant notice's row label is its matched technology (H-13)", () => {
    expect(noticeRowLabel(KEYWORD_HIT)).toBe("surveillance_camera");
    expect(noticeRowLabel(CODE_HIT)).toBe("cpv:35120000");
  });

  it("buyer-scoped listing filters on the buyer join key", () => {
    const scoped = buyerNoticeRows(ROWS, "ent:buyer-none");
    expect(scoped).toHaveLength(0);
    expect(buyerNoticeRows(ROWS, null)).toHaveLength(ROWS.length);
  });
});

describe("P36.30 getProcurementRelevance — data-source-aware load", () => {
  it("fixtures mode serves the committed fixture document", () => {
    process.env.SIG_DATA_SOURCE = "fixtures";
    expect(getProcurementRelevance()).toEqual(ROWS);
  });

  it("export mode reads <exportDir>/web/procurement_relevance.json", () => {
    const dir = mkdtempSync(join(tmpdir(), "sig-export-"));
    mkdirSync(join(dir, "web"), { recursive: true });
    writeFileSync(
      join(dir, "web", "procurement_relevance.json"),
      JSON.stringify({ schema: PROCUREMENT_RELEVANCE_SCHEMA, rows: ROWS }),
    );
    process.env.SIG_DATA_SOURCE = "export";
    process.env.SIG_EXPORT_DIR = dir;
    expect(getProcurementRelevance()).toEqual(ROWS);
  });

  it("export mode with no artifact is the honest empty verdict set", () => {
    const dir = mkdtempSync(join(tmpdir(), "sig-export-empty-"));
    mkdirSync(join(dir, "web"), { recursive: true });
    process.env.SIG_DATA_SOURCE = "export";
    process.env.SIG_EXPORT_DIR = dir;
    expect(getProcurementRelevance()).toEqual([]);
  });

  it("export mode rejects a wrong-schema document — fail closed", () => {
    const dir = mkdtempSync(join(tmpdir(), "sig-export-bad-"));
    mkdirSync(join(dir, "web"), { recursive: true });
    writeFileSync(
      join(dir, "web", "procurement_relevance.json"),
      JSON.stringify({ schema: "sig.other/1", rows: [] }),
    );
    process.env.SIG_DATA_SOURCE = "export";
    process.env.SIG_EXPORT_DIR = dir;
    expect(() => getProcurementRelevance()).toThrow();
    expect(isProcurementRelevanceDoc({ schema: "sig.other/1" })).toBe(false);
  });
});
