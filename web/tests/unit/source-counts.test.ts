// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P35.40 (SIG-TRANSP-002/026/027, K9 §3.1–3.3) — the source-universe pair:
 * `transparency/sources.json` (sig.source-row/1, one source = one registry
 * row) and `transparency/counts.json` (sig.source-counts/1, every count a
 * named predicate). The tests assert the invariants the ticket names:
 * six-state partition in the published precedence order, the emitted
 * partition-sum check, anomalies listed never counted, recompute parity,
 * and the fixture/export data-layer seam (fixtures bytes ≡ export bytes).
 */
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import { getSourceCounts, getSourceRows } from "../../src/lib/data";
import {
  buildCountsDoc,
  isSourceCountsDoc,
  isSourceRowsDoc,
  LIFECYCLE_STATES,
  recomputeSourceCounts,
  SOURCE_ANOMALIES_FIXTURE,
  SOURCE_COUNTS_FIXTURE,
  SOURCE_ROWS_DOC_FIXTURE,
  SOURCE_ROWS_FIXTURE,
  STATE_LABELS,
  type SourceRow,
} from "../../src/lib/source-counts";

const ENV_KEYS = ["SIG_DATA_SOURCE", "SIG_EXPORT_DIR"] as const;

function saveEnv(): Record<string, string | undefined> {
  return Object.fromEntries(ENV_KEYS.map((k) => [k, process.env[k]]));
}
function restoreEnv(saved: Record<string, string | undefined>): void {
  for (const k of ENV_KEYS) {
    if (saved[k] === undefined) delete process.env[k];
    else process.env[k] = saved[k];
  }
}

describe("source-counts fixtures (P35.40)", () => {
  it("the precedence order is the published K9 §3.2 order", () => {
    expect([...LIFECYCLE_STATES]).toEqual([
      "withdrawn",
      "published",
      "ingested_not_published",
      "permitted_not_ingested",
      "gated",
      "refused",
    ]);
    // Every state has a display label — the vocabulary is total.
    for (const s of LIFECYCLE_STATES) expect(STATE_LABELS[s]).toBeTruthy();
  });

  it("the fixture counts doc validates against the emitted schema", () => {
    expect(isSourceCountsDoc(SOURCE_COUNTS_FIXTURE)).toBe(true);
    expect(isSourceRowsDoc(SOURCE_ROWS_DOC_FIXTURE)).toBe(true);
  });

  it("one registry row = one source; every row lands in exactly one state", () => {
    const ids = SOURCE_ROWS_FIXTURE.map((r) => r.source_id);
    expect(new Set(ids).size).toBe(ids.length);
    const partitioned = LIFECYCLE_STATES.flatMap(
      (s) => SOURCE_COUNTS_FIXTURE.lifecycle[s].ids,
    );
    expect(partitioned.length).toBe(ids.length);
    expect(new Set(partitioned).size).toBe(partitioned.length);
    for (const id of ids) expect(partitioned).toContain(id);
  });

  it("the emitted partition check holds and sums to the universe", () => {
    const ps = SOURCE_COUNTS_FIXTURE.partition_sum;
    expect(ps.holds).toBe(true);
    expect(ps.expected).toBe(SOURCE_COUNTS_FIXTURE.universe.count);
    expect(ps.observed).toBe(ps.expected);
    const sum = LIFECYCLE_STATES.reduce(
      (n, s) => n + SOURCE_COUNTS_FIXTURE.lifecycle[s].count,
      0,
    );
    expect(sum).toBe(SOURCE_COUNTS_FIXTURE.universe.count);
  });

  it("fixture rows exercise every lifecycle state except withdrawn (none recorded)", () => {
    const states = new Set(SOURCE_ROWS_FIXTURE.map((r) => r.lifecycle_state));
    for (const s of LIFECYCLE_STATES.filter((s) => s !== "withdrawn")) {
      expect(states.has(s)).toBe(true);
    }
    // `withdrawn` is a defined state that carries a named predicate even at
    // zero — never silently dropped from the vocabulary.
    expect(SOURCE_COUNTS_FIXTURE.lifecycle.withdrawn.count).toBe(0);
    expect(SOURCE_COUNTS_FIXTURE.lifecycle.withdrawn.definition).toMatch(/withdrawal/i);
  });

  it("anomalies are listed by id and never counted in the universe", () => {
    for (const id of SOURCE_ANOMALIES_FIXTURE) {
      expect(SOURCE_COUNTS_FIXTURE.anomalies.ids).toContain(id);
      const partitioned = LIFECYCLE_STATES.flatMap(
        (s) => SOURCE_COUNTS_FIXTURE.lifecycle[s].ids,
      );
      expect(partitioned).not.toContain(id);
    }
  });

  it("every named count re-derives from the rows alone (recompute parity)", () => {
    const rc = recomputeSourceCounts(SOURCE_ROWS_FIXTURE);
    const c = SOURCE_COUNTS_FIXTURE;
    expect(rc.registered).toBe(c.universe.count);
    for (const s of LIFECYCLE_STATES) {
      // The artifact emits sorted ids; the recompute keeps registry order —
      // compare as sets/sorted lists.
      expect([...rc.partition[s]].sort()).toEqual(c.lifecycle[s].ids);
      expect(rc.partition[s].length).toBe(c.lifecycle[s].count);
    }
    expect(rc.rights_permitted).toBe(c.attributes.rights_permitted.count);
    expect(rc.scheduled).toBe(c.attributes.scheduled.count);
    expect(rc.one_time_load).toBe(c.attributes.one_time_load.count);
    expect(rc.site_records).toBe(c.attributes.site_records.count);
    expect(rc.run_records_present).toBe(c.attributes.run_records_present.count);
    expect(rc.run_records_missing).toBe(c.attributes.run_records_missing.count);
    expect(rc.open_issues).toBe(c.attributes.open_issues.count);
    expect(rc.lanes).toEqual(c.attributes.lanes.by_lane);
  });

  it("scheduled and one_time_load are exclusive schedule facets", () => {
    const c = SOURCE_COUNTS_FIXTURE.attributes;
    expect(c.scheduled.count + c.one_time_load.count + c.not_scheduled.count).toBe(
      SOURCE_COUNTS_FIXTURE.universe.count,
    );
    // The one-time seed is never also "scheduled".
    const seed = SOURCE_ROWS_FIXTURE.find((r) => r.source_id === "demo_seed_load");
    expect(seed?.cadence?.one_time_load).toBe(true);
    expect(seed?.cadence?.scheduled).toBe(false);
  });

  it("isSourceCountsDoc rejects a doc whose partition does not sum", () => {
    const bad = JSON.parse(JSON.stringify(SOURCE_COUNTS_FIXTURE));
    bad.partition_sum.holds = false;
    expect(isSourceCountsDoc(bad)).toBe(false);
    const bad2 = JSON.parse(JSON.stringify(SOURCE_COUNTS_FIXTURE));
    bad2.precedence.order = [...LIFECYCLE_STATES].reverse();
    expect(isSourceCountsDoc(bad2)).toBe(false);
    const bad3 = JSON.parse(JSON.stringify(SOURCE_COUNTS_FIXTURE));
    bad3.partition_sum.expected = bad3.universe.count + 1;
    expect(isSourceCountsDoc(bad3)).toBe(false);
  });

  it("buildCountsDoc fails closed when a row escapes the partition", () => {
    const orphan: SourceRow = {
      source_id: "bad_state",
      lifecycle_state: "not_a_state" as SourceRow["lifecycle_state"],
    };
    expect(() => buildCountsDoc([orphan], [], "2026-01-01")).toThrow(
      /partition invariant/,
    );
  });

  it("an empty registry emits an empty universe, never a crash", () => {
    const doc = buildCountsDoc([], [], "2026-01-01");
    expect(isSourceCountsDoc(doc)).toBe(true);
    expect(doc.universe.count).toBe(0);
    for (const s of LIFECYCLE_STATES) expect(doc.lifecycle[s].count).toBe(0);
    expect(doc.partition_sum.holds).toBe(true);
  });
});

describe("source-counts data-layer seam (P35.40)", () => {
  const saved = saveEnv();
  afterEach(() => restoreEnv(saved));

  it("fixtures mode returns the committed pair", () => {
    delete process.env.SIG_DATA_SOURCE;
    expect(getSourceCounts()).toBe(SOURCE_COUNTS_FIXTURE);
    expect(getSourceRows()).toBe(SOURCE_ROWS_DOC_FIXTURE);
  });

  it("export mode reads <exportDir>/transparency/{counts,sources}.json", () => {
    const dir = mkdtempSync(join(tmpdir(), "sig-export-"));
    mkdirSync(join(dir, "transparency"), { recursive: true });
    writeFileSync(
      join(dir, "transparency", "counts.json"),
      JSON.stringify(SOURCE_COUNTS_FIXTURE),
    );
    writeFileSync(
      join(dir, "transparency", "sources.json"),
      JSON.stringify(SOURCE_ROWS_DOC_FIXTURE),
    );
    process.env.SIG_DATA_SOURCE = "export";
    process.env.SIG_EXPORT_DIR = dir;
    expect(getSourceCounts().universe.count).toBe(
      SOURCE_COUNTS_FIXTURE.universe.count,
    );
    expect(getSourceRows().sources.length).toBe(SOURCE_ROWS_FIXTURE.length);
  });

  it("export mode fails LOUD on a missing transparency artifact", () => {
    const dir = mkdtempSync(join(tmpdir(), "sig-export-missing-"));
    process.env.SIG_DATA_SOURCE = "export";
    process.env.SIG_EXPORT_DIR = dir;
    expect(() => getSourceCounts()).toThrow(/transparency artifact is missing/);
    expect(() => getSourceRows()).toThrow(/transparency artifact is missing/);
  });

  it("export mode fails LOUD on a malformed counts doc (broken partition)", () => {
    const dir = mkdtempSync(join(tmpdir(), "sig-export-bad-"));
    mkdirSync(join(dir, "transparency"), { recursive: true });
    const bad = JSON.parse(JSON.stringify(SOURCE_COUNTS_FIXTURE));
    bad.partition_sum.holds = false;
    writeFileSync(
      join(dir, "transparency", "counts.json"),
      JSON.stringify(bad),
    );
    process.env.SIG_DATA_SOURCE = "export";
    process.env.SIG_EXPORT_DIR = dir;
    expect(() => getSourceCounts()).toThrow(/not a valid sig\.source-counts/);
  });
});
