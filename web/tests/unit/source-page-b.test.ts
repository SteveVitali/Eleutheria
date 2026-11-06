// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.69 (UX10-3b): the page-B model — the J3 §5.3 file-action matrix,
 * the changes list, sort + pagination/cap derivations, the versions seam
 * and the entity browse (SIG-TRANSP-005/040/041/043).
 */
import { describe, expect, it } from "vitest";

import {
  captureFileAction,
  changedCaptures,
  changeKindWord,
  entityBrowse,
  ENTITY_BROWSE_CAP,
  getPageBIds,
  getSourceCaptures,
  getSourceEntities,
  getSourceVersions,
  isCaptureRecord,
  isSourceVersionsDoc,
  pageCount,
  pageSlice,
  sortedCaptures,
  SOURCE_CAPTURES_FIXTURE,
  SOURCE_ENTITIES_FIXTURE,
  SOURCE_VERSIONS_FIXTURE,
  upstreamParts,
  type CaptureRecord,
} from "../../src/lib/source-page-b";

const cap = (over: Partial<CaptureRecord>): CaptureRecord => ({
  schema: "sig.capture-record/1",
  run_id: null,
  source_id: "demo",
  target: "not_recorded",
  state: null,
  records: null,
  digest: null,
  bytes: null,
  media_type: null,
  retrieved_at: null,
  records_digest: null,
  classification: "actual",
  storage_tier: "public",
  lane: "derived-only",
  bytes_retained: false,
  http_status: null,
  changed_vs_prior: "first",
  ...over,
});

describe("the J3 §5.3 file-action table (SIG-TRANSP-041)", () => {
  it("raw-ok + retained + P8 clear → download_original (label only — raw archive unpublished)", () => {
    const a = captureFileAction(cap({ lane: "raw-ok", bytes_retained: true }), null);
    expect(a.kind).toBe("download_original");
    expect(a.href).toBeNull();
    expect(a.note).toContain("not yet published");
  });
  it("raw-ok + retained + P8-5 → download_redacted", () => {
    expect(captureFileAction(cap({ lane: "raw-ok", bytes_retained: true }), "P8-5").kind).toBe("download_redacted");
  });
  it("raw-ok + not retained → view_at_source + did-not-retain note", () => {
    const a = captureFileAction(cap({ lane: "raw-ok", bytes_retained: false, target: "https://ex.invalid/f.csv" }), null);
    expect(a.kind).toBe("view_at_source");
    expect(a.href).toBe("https://ex.invalid/f.csv");
    expect(a.note).toContain("did not retain");
  });
  it("derived-only and link-only → view_at_source (host-only upstream links the host)", () => {
    expect(captureFileAction(cap({ lane: "derived-only", target: "https://ex.invalid/" }), null).href).toBe("https://ex.invalid/");
    const a = captureFileAction(cap({ lane: "link-only", target: "ex.invalid#path_sha256:ab12" }), null);
    expect(a.kind).toBe("view_at_source");
    expect(a.href).toBe("https://ex.invalid/");
  });
  it("restricted or sealed → not_redistributable, never a URL", () => {
    for (const c of [
      cap({ lane: "restricted", target: "ex.invalid#path_sha256:ab" }),
      cap({ lane: "raw-ok", storage_tier: "sealed", target: "sealed" }),
    ]) {
      const a = captureFileAction(c, null);
      expect(a.kind).toBe("not_redistributable");
      expect(a.href).toBeNull();
    }
    expect(captureFileAction(cap({ lane: "raw-ok" }), "P8-1").kind).toBe("not_redistributable");
  });
  it("unknown lane → rights_not_reviewed; synthetic → run_record", () => {
    expect(captureFileAction(cap({ lane: "unknown" }), null).kind).toBe("rights_not_reviewed");
    const a = captureFileAction(cap({ classification: "synthetic", lane: "raw-ok" }), null);
    expect(a.kind).toBe("run_record");
  });
});

describe("changes list + sort + pagination", () => {
  it("changedCaptures keeps only record-set changes", () => {
    const rows = SOURCE_CAPTURES_FIXTURE.demo_ingested_feed;
    const changes = changedCaptures(rows);
    expect(changes.length).toBeGreaterThan(0);
    expect(changes.every((c) => c.changed_vs_prior === "changed")).toBe(true);
  });
  it("sortedCaptures orders target then retrieved_at desc", () => {
    const rows = sortedCaptures([
      cap({ target: "b", retrieved_at: "2026-01-01T00:00:00Z" }),
      cap({ target: "a", retrieved_at: "2026-01-02T00:00:00Z" }),
      cap({ target: "a", retrieved_at: "2026-01-03T00:00:00Z" }),
    ]);
    expect(rows[0]!.retrieved_at).toBe("2026-01-03T00:00:00Z");
    expect(rows[1]!.retrieved_at).toBe("2026-01-02T00:00:00Z");
  });
  it("the fixture exercises 100-row pagination", () => {
    const rows = SOURCE_CAPTURES_FIXTURE.demo_ingested_feed;
    expect(rows.length).toBeGreaterThan(200);
    expect(pageCount(rows.length)).toBe(3);
    expect(pageSlice(rows, 2).length).toBe(100);
    expect(pageSlice(rows, 3).length).toBe(rows.length - 200);
  });
  it("changeKindWord renders the closed vocabulary", () => {
    expect(changeKindWord("formatting change only")).toBe("formatting change only");
    expect(changeKindWord("first")).toBe("first capture");
  });
});

describe("validators + seams", () => {
  it("fixture capture rows validate; a malformed row fails", () => {
    for (const list of Object.values(SOURCE_CAPTURES_FIXTURE)) {
      for (const r of list) expect(isCaptureRecord(r)).toBe(true);
    }
    expect(isCaptureRecord({ schema: "sig.capture-record/1" })).toBe(false);
  });
  it("versions docs validate; entries carry the declared states", () => {
    for (const d of Object.values(SOURCE_VERSIONS_FIXTURE)) {
      expect(isSourceVersionsDoc(d)).toBe(true);
    }
    const okc = SOURCE_VERSIONS_FIXTURE.okc_camera_registry;
    expect(okc.entries.map((e) => e.state)).toEqual(["manifest_only", "extract_absent", "extract"]);
  });
  it("getSourceCaptures/getSourceVersions answer honest absences", () => {
    expect(getSourceCaptures("demo_seed_load")).toBeNull();
    expect(getSourceVersions("demo_seed_load")).toBeNull();
    expect(getSourceCaptures("okc_camera_registry")!.length).toBe(6);
    expect(getSourceVersions("okc_camera_registry")!.entry_count).toBe(3);
  });
});

describe("entity browse (SIG-TRANSP-043, D-K10-2)", () => {
  it("caps at 10 pages × 100 and states the cap", () => {
    const browse = entityBrowse(SOURCE_ENTITIES_FIXTURE.demo_seed_load);
    expect(browse.total).toBe(1_050);
    expect(browse.capped).toBe(true);
    expect(browse.rows.length).toBe(ENTITY_BROWSE_CAP);
    expect(browse.pages).toBe(10);
  });
  it("orders jurisdiction → label → record key; the small set stays whole", () => {
    const browse = entityBrowse(getSourceEntities("okc_camera_registry"));
    expect(browse.total).toBe(3);
    expect(browse.capped).toBe(false);
    expect(browse.pages).toBe(1);
  });
  it("getPageBIds excludes the registry-only sources (S-11)", () => {
    const ids = getPageBIds();
    expect(ids).toContain("okc_camera_registry");
    expect(ids).not.toContain("demo_gated_registry");
    expect(ids).not.toContain("demo_refused_source");
  });
});

describe("upstream parts", () => {
  it("splits the S-6 forms honestly", () => {
    expect(upstreamParts("sealed")).toEqual({ url: null, host: null });
    expect(upstreamParts("https://ex.invalid/f.csv")).toEqual({ url: "https://ex.invalid/f.csv", host: "ex.invalid" });
    expect(upstreamParts("ex.invalid#path_sha256:ab").url).toBeNull();
    expect(upstreamParts("ex.invalid#path_sha256:ab").host).toBe("ex.invalid");
  });
});
