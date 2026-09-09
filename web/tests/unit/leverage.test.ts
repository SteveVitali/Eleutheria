// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { afterEach, describe, expect, it } from "vitest";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { getLeverageMetric } from "../../src/lib/data";
import { LEVERAGE_METRIC_FIXTURE } from "../../src/lib/leverage-fixture";

// data.ts reads env at CALL time (dataSource()/exportDir() are plain functions), so a
// static import is fine — just restore the env between cases so modes don't leak.
const saved = { source: process.env.SIG_DATA_SOURCE, dir: process.env.SIG_EXPORT_DIR };
afterEach(() => {
  if (saved.source === undefined) delete process.env.SIG_DATA_SOURCE;
  else process.env.SIG_DATA_SOURCE = saved.source;
  if (saved.dir === undefined) delete process.env.SIG_EXPORT_DIR;
  else process.env.SIG_EXPORT_DIR = saved.dir;
});

describe("§7 leverage metric (P21.7, SIG-CONTRIB-016e)", () => {
  it("fixtures mode returns the committed sample", () => {
    process.env.SIG_DATA_SOURCE = "fixtures";
    expect(getLeverageMetric()).toEqual(LEVERAGE_METRIC_FIXTURE);
  });

  it("the fixture carries a hashtag, an accepted count, and no user data", () => {
    expect(LEVERAGE_METRIC_FIXTURE.hashtag).toMatch(/^#sig_/);
    expect(LEVERAGE_METRIC_FIXTURE.accepted_operator_attributions).toBeGreaterThanOrEqual(0);
    for (const id of LEVERAGE_METRIC_FIXTURE.attributed_changeset_ids) {
      expect(id).toMatch(/^\d+$/); // changeset ids only — never a username
    }
    expect(JSON.stringify(LEVERAGE_METRIC_FIXTURE)).not.toMatch(/user|uid|mapper/i);
  });

  it("export mode reads <exportDir>/web/leverage.json", () => {
    const dir = mkdtempSync(join(tmpdir(), "sig-leverage-"));
    mkdirSync(join(dir, "web"), { recursive: true });
    const record = {
      hashtag: "#sig_operator_attribution",
      accepted_operator_attributions: 12,
      attributed_changeset_ids: ["1", "2", "3"],
    };
    writeFileSync(join(dir, "web", "leverage.json"), JSON.stringify(record));
    process.env.SIG_DATA_SOURCE = "export";
    process.env.SIG_EXPORT_DIR = dir;
    expect(getLeverageMetric().accepted_operator_attributions).toBe(12);
    rmSync(dir, { recursive: true, force: true });
  });

  it("export mode fails LOUD when the artifact is missing (never silent fixtures)", () => {
    process.env.SIG_DATA_SOURCE = "export";
    process.env.SIG_EXPORT_DIR = join(tmpdir(), "sig-does-not-exist-xyz");
    expect(() => getLeverageMetric()).toThrow(/leverage metric artifact is missing/);
  });
});
