// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.47 (UX10-3a): the source-page model + derivations — the fixture
 * universe covers every section and every named-absence kind; conduct is
 * aggregated from observed executions only (SIG-TRANSP-039); the strip spec
 * is the figure-kit chart contract (FIG-01b); SIG-TRANSP-037's no-record
 * honesty holds for data-bearing sources without executions.
 */
import { describe, expect, it } from "vitest";

import {
  conductSummary,
  coverageClass,
  fixtureReleaseInfo,
  getSourcePage,
  getSourcePageIds,
  isExecutionRecord,
  isRegistryOnly,
  isSourcePageRow,
  observedCadenceDays,
  runRecordMissing,
  runsStripSpec,
  SOURCE_EXECUTIONS_FIXTURE,
  SOURCE_PAGE_EXTRAS_FIXTURE,
} from "../../src/lib/source-page";

describe("the fixture universe (getSourcePageIds/getSourcePage)", () => {
  it("emits a page id per fixture source row", () => {
    const ids = getSourcePageIds();
    expect(ids.length).toBeGreaterThanOrEqual(7);
    for (const id of ids) {
      const model = getSourcePage(id);
      expect(model, id).not.toBeNull();
      expect(model!.row.source_id).toBe(id);
    }
  });

  it("every fixture row validates and gated rows classify registry-only", () => {
    for (const id of getSourcePageIds()) {
      const model = getSourcePage(id)!;
      expect(isSourcePageRow(model.row), id).toBe(true);
    }
    expect(isRegistryOnly(getSourcePage("demo_gated_registry")!.row)).toBe(true);
    expect(isRegistryOnly(getSourcePage("demo_refused_source")!.row)).toBe(true);
    expect(isRegistryOnly(getSourcePage("okc_camera_registry")!.row)).toBe(false);
  });

  it("an unknown id resolves to null (never an untyped page)", () => {
    expect(getSourcePage("no_such_source")).toBeNull();
  });
});

describe("conductSummary (SIG-TRANSP-039 — observed records only)", () => {
  it("aggregates robots outcomes per host with the GL-GATE-08 decision ref", () => {
    const c = conductSummary(SOURCE_EXECUTIONS_FIXTURE.okc_camera_registry)!;
    const dataHost = c.robotsByHost.find((r) => r.host === "data.example.invalid")!;
    expect(dataHost.outcomes.disregarded).toBe(4);
    expect(dataHost.outcomes.unavailable).toBe(1);
    expect(dataHost.outcomes.disallowed).toBe(1);
    expect(dataHost.decisionRef).toBe("GL-GATE-08");
    // latest execution only
    const latest = c.latestRobots.find((r) => r.host === "data.example.invalid")!;
    expect(latest.outcomes.disallowed).toBe(1);
    expect(latest.outcomes.disregarded).toBeUndefined();
  });

  it("folds refusal classes, rate limits and never invents counts", () => {
    const c = conductSummary(SOURCE_EXECUTIONS_FIXTURE.okc_camera_registry)!;
    expect(c.refusals.malformed_row).toBe(2);
    expect(c.rateLimitEvents).toBe(1);
    expect(c.totalExecutions).toBe(3);
  });

  it("returns null when no executions are recorded (a named absence)", () => {
    expect(conductSummary(null)).toBeNull();
    expect(conductSummary([])).toBeNull();
  });
});

describe("cadence + the runs strip spec", () => {
  it("computes the median observed interval of successful executions", () => {
    // okc fixture: 2026-09-15 → 2026-10-01 (16d) → 2026-10-15 (14d) → median 15.
    expect(observedCadenceDays(SOURCE_EXECUTIONS_FIXTURE.okc_camera_registry)).toBe(15);
    // one success is not evaluable.
    expect(observedCadenceDays(SOURCE_EXECUTIONS_FIXTURE.okc_council_minutes)).toBeNull();
    expect(observedCadenceDays(null)).toBeNull();
  });

  it("composes a sig.figure-kit-chart/1 strip spec (one dated marker per execution)", () => {
    const model = getSourcePage("okc_camera_registry")!;
    const spec = runsStripSpec(model, fixtureReleaseInfo())!;
    expect(spec.schema).toBe("sig.figure-kit-chart/1");
    expect(spec.kind).toBe("strip");
    expect(spec.events).toHaveLength(3);
    expect(spec.events[0]!.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    // a source with no executions composes no strip — a typed state, never
    // an empty drawing (SIG-ENG-042).
    expect(runsStripSpec(getSourcePage("demo_permitted_portal")!, fixtureReleaseInfo())).toBeNull();
  });
});

describe("honesty states", () => {
  it("flags a data-bearing source with no execution record (SIG-TRANSP-037)", () => {
    // demo_ingested_feed is data-bearing (ingested_not_published) with no
    // executions feed → the no-record honesty line renders.
    const model = getSourcePage("demo_ingested_feed")!;
    expect(runRecordMissing(model)).toBe(true);
    expect(runRecordMissing(getSourcePage("okc_camera_registry")!)).toBe(false);
    expect(runRecordMissing(getSourcePage("demo_permitted_portal")!)).toBe(false);
  });

  it("derives the rights-record coverage class without re-deciding", () => {
    expect(coverageClass(getSourcePage("okc_camera_registry")!)).toBe("delegated_rule");
    expect(coverageClass(getSourcePage("demo_refused_source")!)).toBe("refused");
    expect(coverageClass(getSourcePage("demo_gated_registry")!)).toBe("gated");
    expect(coverageClass(getSourcePage("demo_ingested_feed")!)).toBe("registry_only");
    // no extras → the basis decides; a no_decision_recorded basis is registry-only.
    const bare = { ...getSourcePage("demo_permitted_portal")!, extras: { ...SOURCE_PAGE_EXTRAS_FIXTURE.demo_permitted_portal!, coverage_class: null } };
    expect(coverageClass(bare)).toBe("registry_only");
  });
});

describe("validators (fail closed, never coerce)", () => {
  it("rejects malformed execution records", () => {
    expect(isExecutionRecord({})).toBe(false);
    expect(
      isExecutionRecord({ schema: "sig.execution-record/1", source_id: "x", outcome: "ok", robots: [] }),
    ).toBe(true);
    expect(
      isExecutionRecord({ schema: "sig.run-record/1", source_id: "x", outcome: "ok", robots: [] }),
    ).toBe(false);
  });

  it("rejects malformed source rows", () => {
    expect(isSourcePageRow({})).toBe(false);
    expect(isSourcePageRow({ source_id: "x" })).toBe(false);
  });
});
