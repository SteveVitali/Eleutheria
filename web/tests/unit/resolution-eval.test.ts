// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { describe, expect, it } from "vitest";
import { RESOLUTION_EVAL } from "../../src/lib/resolution-eval";

describe("resolution eval — SIG measuring its own method (§32.5, P28.4)", () => {
  it("preserves the PROVISIONAL disclosure verbatim and cites its deferral", () => {
    expect(RESOLUTION_EVAL.provisional).toBe(true);
    expect(RESOLUTION_EVAL.disclosure).toContain("PROVISIONAL");
    expect(RESOLUTION_EVAL.disclosure).toContain("D-R6.1-EVAL");
    expect(RESOLUTION_EVAL.deferral).toBe("D-R6.1-EVAL");
  });

  it("surfaces the P28.1 holdout metrics (κ, floor, P/R/F1) each against a named denominator", () => {
    const labels = RESOLUTION_EVAL.metrics.map((m) => m.label.toLowerCase()).join(" | ");
    expect(labels).toContain("κ");
    expect(labels).toContain("precision floor");
    expect(labels).toContain("f1");
    // The κ value and the auto-write floor mirror the committed P28.1 report.
    const kappa = RESOLUTION_EVAL.metrics.find((m) => m.label.includes("κ"));
    expect(kappa?.value).toBe("0.714");
    const floor = RESOLUTION_EVAL.metrics.find((m) => m.label.includes("precision floor"));
    expect(floor?.value).toBe("0.980");
    // Every metric is measured against a NAMED denominator/population — never a total.
    for (const m of RESOLUTION_EVAL.metrics) {
      expect(m.against.trim().length).toBeGreaterThan(0);
      expect(m.against.toLowerCase()).not.toContain("device population");
      expect(m.against.toLowerCase()).not.toContain("total population");
    }
  });

  it("publishes the P30.2b camera-site measurements, including the missed κ bar", () => {
    const camera = RESOLUTION_EVAL.metrics.filter((m) => m.label.startsWith("camera sites:"));
    expect(camera.map((m) => m.value)).toEqual(["0.669", "1.000 (70 of 70)", "0.986 (69 of 70)"]);
    expect(camera[0].against).toContain("suggester only");
    for (const m of camera.slice(1)) {
      expect(m.against).toContain("95% lower bound");
    }
  });
});
