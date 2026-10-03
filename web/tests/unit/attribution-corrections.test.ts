// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P34.21b (E2-12, ADR-194) — `getAttributionCorrections`: fixtures mode is
 * honest absence (null — the demo corpus carries no correction); export mode
 * reads `<exportDir>/web/attribution_corrections.json` — missing artifact is
 * honest absence, a malformed one fails loudly, and `corrected_on` is the
 * newest correction `decided_at` date the /sources/ note renders.
 */
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { getAttributionCorrections } from "../../src/lib/data";

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

function exportRoot(): string {
  const dir = mkdtempSync(join(tmpdir(), "sig-export-"));
  mkdirSync(join(dir, "web"));
  process.env.SIG_DATA_SOURCE = "export";
  process.env.SIG_EXPORT_DIR = dir;
  return dir;
}

const ARTIFACT = {
  schema: "sig.attribution-corrections/1",
  as_of: "2026-09-27",
  generated_at: "2026-10-02T00:00:00Z",
  note: "…",
  corrections: [
    {
      source_id: "src_alpha",
      decided_at: "2026-09-20T12:00:00+00:00",
      basis: "ADR-194 …",
      affected_rows: 42,
    },
    {
      source_id: "src_beta",
      decided_at: "2026-09-26T08:30:00+00:00",
      basis: "ADR-194 …",
      affected_rows: 7,
    },
  ],
};

describe("getAttributionCorrections", () => {
  const saved = saveEnv();
  afterEach(() => restoreEnv(saved));

  it("fixtures mode is honest absence", () => {
    delete process.env.SIG_DATA_SOURCE;
    expect(getAttributionCorrections()).toBeNull();
  });

  it("export mode with no artifact is honest absence", () => {
    exportRoot();
    expect(getAttributionCorrections()).toBeNull();
  });

  it("export mode reads the artifact; corrected_on is the newest date", () => {
    const dir = exportRoot();
    writeFileSync(
      join(dir, "web", "attribution_corrections.json"),
      JSON.stringify(ARTIFACT),
    );
    const c = getAttributionCorrections();
    expect(c).not.toBeNull();
    expect(c!.schema).toBe("sig.attribution-corrections/1");
    expect(c!.corrections).toHaveLength(2);
    expect(c!.corrections[0]!.source_id).toBe("src_alpha");
    expect(c!.corrected_on).toBe("2026-09-26");
  });

  it("a malformed artifact fails loudly", () => {
    const dir = exportRoot();
    writeFileSync(
      join(dir, "web", "attribution_corrections.json"),
      JSON.stringify({ schema: "sig.other/1", corrections: [] }),
    );
    expect(() => getAttributionCorrections()).toThrow(
      /sig\.attribution-corrections\/1/,
    );
  });
});
