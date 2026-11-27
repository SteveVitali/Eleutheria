// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * D-P37.65a-2 — the export-mode data layer at national scale.
 *
 *   (a) The whole-file `readFileSync(p, "utf-8")` readers threw
 *       `Error: Cannot create a string longer than 0x1fffffe8 characters`
 *       (the V8 string cap) on any compartment `statements.jsonl` >512 MiB —
 *       the 2026-11-25 national export's `osm_physical/statements.jsonl` is
 *       1,013,125,905 B. These tests index a synthetic >512 MiB stream
 *       through the same getters the pages call — under the old readers this
 *       suite dies with ERR_STRING_TOO_LONG.
 *
 *   (b) The readers were non-memoized — every entity/claim route re-parsed
 *       the full corpus. The memo pins are instance-identity assertions:
 *       a second call returns THE SAME map/array, never a re-parse.
 */
import { afterAll, afterEach, describe, expect, it } from "vitest";
import { closeSync, mkdirSync, mkdtempSync, openSync, rmSync, statSync, writeFileSync, writeSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  getEntityCompartments,
  getEntityLabelRows,
  getJurisdictionCompartments,
  getRecordBasisIndex,
  getStatementIndex,
  getSourceLicenceTable,
} from "../../src/lib/data";
import { getSourceEntities } from "../../src/lib/source-page-b";

// data.ts reads env at CALL time — restore between cases (data.test.ts idiom).
const saved = { source: process.env.SIG_DATA_SOURCE, dir: process.env.SIG_EXPORT_DIR };
afterEach(() => {
  if (saved.source === undefined) delete process.env.SIG_DATA_SOURCE;
  else process.env.SIG_DATA_SOURCE = saved.source;
  if (saved.dir === undefined) delete process.env.SIG_EXPORT_DIR;
  else process.env.SIG_EXPORT_DIR = saved.dir;
});

const V8_STRING_CAP = 0x1fffffe8; // 536,870,888 — the cap the defect hit.

/** A minimal export layout: one compartment's sites.jsonl + labels dir. */
function seedBundle(): string {
  const bundle = mkdtempSync(join(tmpdir(), "sig-export-big-"));
  mkdirSync(join(bundle, "comp_a"), { recursive: true });
  mkdirSync(join(bundle, "labels"), { recursive: true });
  writeFileSync(
    join(bundle, "comp_a", "sites.jsonl"),
    [
      JSON.stringify({
        entity_id: "e1",
        entity_type: "deployment",
        jurisdiction_key: "iso3166-2:US-OK",
        jurisdiction_slug_path: "usa/ok",
        _rights: { source_id: "src_a" },
      }),
      JSON.stringify({ entity_id: "e2", entity_type: "deployment", _rights: { source_id: "src_b" } }),
      "",
    ].join("\n"),
  );
  writeFileSync(
    join(bundle, "labels", "comp_a.jsonl"),
    JSON.stringify({ entity_id: "e1", url_type: null, slug: null, hash: null }) + "\n",
  );
  return bundle;
}

describe("D-P37.65a-2 (a) — a >512 MiB statements.jsonl indexes without the string cap", () => {
  it(
    "getStatementIndex streams a file past 0x1fffffe8 chars",
    { timeout: 120_000 },
    () => {
      const bundle = seedBundle();
      const p = join(bundle, "comp_a", "statements.jsonl");
      // Rows ~1 MiB each so the file crosses the cap in ~540 rows — big
      // enough to die under readFileSync, cheap enough to parse under vitest.
      const pad = "x".repeat(1024 * 1024);
      const fd = openSync(p, "w");
      try {
        for (let i = 0; i < 540; i += 1) {
          writeSync(fd, JSON.stringify({ claim_id: `claim-${i}`, pad }) + "\n");
        }
      } finally {
        closeSync(fd);
      }
      expect(statSync(p).size).toBeGreaterThan(V8_STRING_CAP);

      process.env.SIG_DATA_SOURCE = "export";
      process.env.SIG_EXPORT_DIR = bundle;

      const index = getStatementIndex();
      expect(index.size).toBe(540);
      expect(index.get("claim-0")?.claim_id).toBe("claim-0");
      expect(index.get("claim-539")?.claim_id).toBe("claim-539");

      rmSync(bundle, { recursive: true, force: true });
    },
  );
});

describe("D-P37.65a-2 (b) — the corpus indexes are built once per data root", () => {
  it("every corpus getter returns the SAME index instance on repeat calls", () => {
    const bundle = seedBundle();
    process.env.SIG_DATA_SOURCE = "export";
    process.env.SIG_EXPORT_DIR = bundle;

    expect(getStatementIndex()).toBe(getStatementIndex());
    expect(getRecordBasisIndex()).toBe(getRecordBasisIndex());
    expect(getEntityCompartments()).toBe(getEntityCompartments());
    expect(getJurisdictionCompartments()).toBe(getJurisdictionCompartments());
    expect(getEntityLabelRows()).toBe(getEntityLabelRows());
    expect(getSourceLicenceTable()).toBe(getSourceLicenceTable());
    // The per-source entity index is one corpus pass shared by every source —
    // two sources resolve out of the same single scan.
    expect(getSourceEntities("src_a").map((r) => r.entity_id)).toEqual(["e1"]);
    expect(getSourceEntities("src_b").map((r) => r.entity_id)).toEqual(["e2"]);

    rmSync(bundle, { recursive: true, force: true });
  });

  it("a flipped SIG_EXPORT_DIR re-reads honestly (never a stale memo)", () => {
    const a = seedBundle();
    const b = seedBundle();
    writeFileSync(
      join(b, "comp_a", "sites.jsonl"),
      JSON.stringify({ entity_id: "e9", entity_type: "deployment" }) + "\n",
    );
    process.env.SIG_DATA_SOURCE = "export";
    process.env.SIG_EXPORT_DIR = a;
    const first = getEntityCompartments();
    expect(first.has("e1")).toBe(true);
    process.env.SIG_EXPORT_DIR = b;
    const second = getEntityCompartments();
    expect(second).not.toBe(first);
    expect(second.has("e9")).toBe(true);
    expect(second.has("e1")).toBe(false);

    rmSync(a, { recursive: true, force: true });
    rmSync(b, { recursive: true, force: true });
  });
});

// The temp bundles are small except the big-file case (which removes its own).
afterAll(() => {
  // nothing — each case removes its bundle; tmpdir GC handles a crash-left dir.
});
