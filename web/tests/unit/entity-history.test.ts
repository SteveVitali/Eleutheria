// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { afterEach, describe, expect, it } from "vitest";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  ENTITY_SLUG_HISTORY_FIXTURE,
  resolveEntityRequest,
} from "../../src/lib/entity-history";
import { getEntitySlugHistory } from "../../src/lib/data";

const ROWS = ENTITY_SLUG_HISTORY_FIXTURE.rows;

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

describe("P36.29 entity-history resolver — /entity/ paths (hash authoritative)", () => {
  it("an exact canonical key serves (200)", () => {
    const d = resolveEntityRequest(
      ROWS,
      "/entity/agency/oklahoma-city-police-department--z8t9rv5/",
    );
    expect(d).not.toBeNull();
    expect(d?.status).toBe(200);
  });

  it("a missing trailing slash still serves", () => {
    const d = resolveEntityRequest(
      ROWS,
      "/entity/agency/oklahoma-city-police-department--z8t9rv5",
    );
    expect(d?.status).toBe(200);
  });

  it("a wrong slug with the right hash 301s to the canonical key", () => {
    const d = resolveEntityRequest(ROWS, "/entity/agency/anything--z8t9rv5/");
    expect(d?.status).toBe(301);
    expect(d?.target).toBe(
      "/entity/agency/oklahoma-city-police-department--z8t9rv5/",
    );
  });

  it("a renamed entity's OLD key 301s to the new canonical key", () => {
    const d = resolveEntityRequest(
      ROWS,
      "/entity/agency/okc-office-of-emergency-management--b9sdfah/",
    );
    expect(d?.status).toBe(301);
    expect(d?.target).toBe(
      "/entity/agency/oklahoma-city-emergency-management--b9sdfah/",
    );
  });

  it("a renamed entity's NEW key serves — never a self-redirect loop", () => {
    const d = resolveEntityRequest(
      ROWS,
      "/entity/agency/oklahoma-city-emergency-management--b9sdfah/",
    );
    expect(d?.status).toBe(200);
  });

  it("a merged entity's key 301s to the survivor", () => {
    const d = resolveEntityRequest(
      ROWS,
      "/entity/agency/oklahoma-city-fusion-center--yarw4yk/",
    );
    expect(d?.status).toBe(301);
    expect(d?.target).toBe(
      "/entity/agency/oklahoma-city-police-department--z8t9rv5/",
    );
  });

  it("a split entity's key answers 300 with the successor list", () => {
    const d = resolveEntityRequest(
      ROWS,
      "/entity/agency/okcpd-field-operations--257dn0h/",
    );
    expect(d?.status).toBe(300);
    expect(d?.targets).toEqual([
      "/entity/agency/okcpd-north-division--sezzp58/",
      "/entity/agency/okcpd-south-division--vsht0xe/",
    ]);
  });

  it("a withdrawn entity's key tombstones (410)", () => {
    const d = resolveEntityRequest(
      ROWS,
      "/entity/atlas/okc-fairgrounds-camera-feed--3gh1axe/",
    );
    expect(d?.status).toBe(410);
  });

  it("an unknown hash is the honest 404 — null, never a guess", () => {
    expect(resolveEntityRequest(ROWS, "/entity/agency/x--zzzzzzz/")).toBeNull();
  });

  it.each([
    "/entity/agency/no-hash-at-all/",
    "/entity/",
    "/dossier/oklahoma/",
    "/id/agency/",
    "",
  ])("a malformed path %s answers null", (bad) => {
    expect(resolveEntityRequest(ROWS, bad)).toBeNull();
  });
});

describe("P36.29 entity-history resolver — /id/ paths", () => {
  it("a live uuid 302s to its current key", () => {
    const d = resolveEntityRequest(ROWS, "/id/agency/agency:okcpd");
    expect(d?.status).toBe(302);
    expect(d?.target).toBe(
      "/entity/agency/oklahoma-city-police-department--z8t9rv5/",
    );
  });

  it("a renamed uuid 302s through its live successor key", () => {
    const d = resolveEntityRequest(ROWS, "/id/agency/agency:okc-emergency-mgmt");
    expect(d?.status).toBe(302);
    expect(d?.target).toBe(
      "/entity/agency/oklahoma-city-emergency-management--b9sdfah/",
    );
  });

  it("a merged uuid 301s to the survivor — the stale current row never wins", () => {
    const d = resolveEntityRequest(ROWS, "/id/agency/agency:okc-fusion-center");
    expect(d?.status).toBe(301);
    expect(d?.target).toBe(
      "/entity/agency/oklahoma-city-police-department--z8t9rv5/",
    );
  });

  it("a split uuid answers 300 with the successor list", () => {
    const d = resolveEntityRequest(ROWS, "/id/agency/agency:okcpd-field-operations");
    expect(d?.status).toBe(300);
    expect(d?.targets).toHaveLength(2);
  });

  it("a withdrawn uuid tombstones (410)", () => {
    const d = resolveEntityRequest(ROWS, "/id/atlas/atlas:okc-fairgrounds-cameras");
    expect(d?.status).toBe(410);
  });

  it("an unknown uuid answers null", () => {
    expect(resolveEntityRequest(ROWS, "/id/agency/agency:nobody")).toBeNull();
  });
});

describe("P36.29 getEntitySlugHistory — data-source-aware load", () => {
  it("fixtures mode serves the committed fixture document", () => {
    process.env.SIG_DATA_SOURCE = "fixtures";
    expect(getEntitySlugHistory()).toEqual(ROWS);
  });

  it("export mode reads <exportDir>/web/entity_slug_history.json", () => {
    const dir = mkdtempSync(join(tmpdir(), "sig-export-"));
    mkdirSync(join(dir, "web"), { recursive: true });
    writeFileSync(
      join(dir, "web", "entity_slug_history.json"),
      JSON.stringify({ schema: "sig.slug-history/1", rows: ROWS }),
    );
    process.env.SIG_DATA_SOURCE = "export";
    process.env.SIG_EXPORT_DIR = dir;
    expect(getEntitySlugHistory()).toEqual(ROWS);
  });

  it("export mode with no artifact is the honest empty history", () => {
    const dir = mkdtempSync(join(tmpdir(), "sig-export-empty-"));
    mkdirSync(join(dir, "web"), { recursive: true });
    process.env.SIG_DATA_SOURCE = "export";
    process.env.SIG_EXPORT_DIR = dir;
    expect(getEntitySlugHistory()).toEqual([]);
  });
});
