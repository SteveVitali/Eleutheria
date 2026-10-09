// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P34.19 (F-403, ADR-183) — the express-terms disclosure getter: fixtures
 * mode returns the demo record, export mode reads
 * `<exportDir>/web/terms_disclosure.json` (missing = honest empty sources,
 * malformed = loud failure).
 */
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { getTermsDisclosure } from "../../src/lib/data";
import {
  isTermsDisclosure,
  TERMS_DISCLOSURE_FIXTURE,
} from "../../src/lib/terms-disclosure";

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

describe("getTermsDisclosure", () => {
  const saved = saveEnv();
  afterEach(() => restoreEnv(saved));

  it("fixtures mode returns the marked demo record", () => {
    delete process.env.SIG_DATA_SOURCE;
    const d = getTermsDisclosure();
    expect(isTermsDisclosure(d)).toBe(true);
    expect(d).toBe(TERMS_DISCLOSURE_FIXTURE);
    expect(d.sources[0]!.source_id).toContain("demo");
    expect(d.basis.operator_words.map((w) => w.text)).toContain(
      "Keep all, accept risk",
    );
  });

  it("export mode with no artifact reads honest absence (empty sources)", () => {
    const dir = mkdtempSync(join(tmpdir(), "sig-export-"));
    mkdirSync(join(dir, "web"));
    process.env.SIG_DATA_SOURCE = "export";
    process.env.SIG_EXPORT_DIR = dir;
    const d = getTermsDisclosure();
    expect(d.schema).toBe("sig.terms-disclosure/1");
    expect(d.sources).toEqual([]);
  });

  it("export mode reads a real artifact and rejects a malformed one", () => {
    const dir = mkdtempSync(join(tmpdir(), "sig-export-"));
    mkdirSync(join(dir, "web"));
    process.env.SIG_DATA_SOURCE = "export";
    process.env.SIG_EXPORT_DIR = dir;
    const path = join(dir, "web", "terms_disclosure.json");
    writeFileSync(
      path,
      JSON.stringify({
        schema: "sig.terms-disclosure/1",
        basis: TERMS_DISCLOSURE_FIXTURE.basis,
        sources: [
          {
            source_id: "camreg_trpa_us",
            name: "TRPA",
            spdx_registry: "LicenseRef-PublicRecord-FactualCompilation",
            terms_url: "https://example/terms",
            captured_terms_verbatim: "CC BY-NC",
            captured_terms_evidence: "ref",
            publication_basis: "operator-accepted express terms (ADR-183)",
            export_row_count: 15,
          },
        ],
      }),
    );
    const d = getTermsDisclosure();
    expect(d.sources).toHaveLength(1);
    expect(d.sources[0]!.captured_terms_verbatim).toBe("CC BY-NC");
    expect(d.sources[0]!.publication_basis).toBe(
      "operator-accepted express terms (ADR-183)",
    );
    writeFileSync(path, JSON.stringify({ not: "a disclosure" }));
    expect(() => getTermsDisclosure()).toThrow(/sig\.terms-disclosure\/1/);
  });
});
