// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.41 (R11-K13-UX10-4, K10 §15/§19 AT-K10-08, §56.10 SIG-TRANSP-042) —
 * the per-source changelog generator: append-only events dated by their own
 * records' clocks (clock_basis names which), never by version-control
 * dates; the baseline sentence; the emitted sig.source-changelog/1 doc.
 */
import { describe, expect, it } from "vitest";
import {
  baselineSentence,
  buildSourceChangelog,
  eventSummary,
  getSourceChangelog,
  getSourceChangelogIds,
  isChangelogDoc,
  CLOCK_BASES,
  CHANGELOG_KINDS,
  type ChangelogInputs,
  type SourceChangelogEvent,
} from "../../src/lib/source-changelog";
import {
  SOURCE_EXECUTIONS_FIXTURE,
  SOURCE_PAGE_EXTRAS_FIXTURE,
  type SourcePageRow,
} from "../../src/lib/source-page";
import { SOURCE_VERSIONS_FIXTURE } from "../../src/lib/source-page-b";
import { SOURCE_ROWS_DOC_FIXTURE } from "../../src/lib/source-counts";
import { CHANGES_FIXTURE } from "../../src/lib/changes-fixture";
import { ISSUES_FIXTURE } from "../../src/lib/issues";

const row = (id: string): SourcePageRow => {
  const r = SOURCE_ROWS_DOC_FIXTURE.sources.find((s) => s.source_id === id);
  if (!r) throw new Error(`fixture universe: no source row ${id}`);
  return r as SourcePageRow;
};

const inputs = (id: string, over: Partial<ChangelogInputs> = {}): ChangelogInputs => ({
  row: row(id),
  executions: SOURCE_EXECUTIONS_FIXTURE[id] ?? null,
  versions: SOURCE_VERSIONS_FIXTURE[id] ?? null,
  changes: CHANGES_FIXTURE,
  issues: ISSUES_FIXTURE.filter((i) => i.source_id === id),
  corrections: [],
  attribution: [],
  withdrawals: [],
  ...over,
});

const byKind = (events: readonly SourceChangelogEvent[], kind: string) =>
  events.filter((e) => e.kind === kind);

describe("the event generator (K10 §15)", () => {
  it("every event carries a record-clock basis — never git-derived", () => {
    for (const id of getSourceChangelogIds()) {
      const doc = getSourceChangelog(id);
      expect(doc, `changelog for ${id}`).not.toBeNull();
      for (const ev of doc!.events) {
        expect(CLOCK_BASES).toContain(ev.clock_basis);
        expect(CHANGELOG_KINDS).toContain(ev.kind);
        expect(Number.isFinite(Date.parse(ev.at)), `${ev.event_id} at ${ev.at}`).toBe(true);
        expect(ev.summary_code).toMatch(/^[a-z._]+$/);
        expect(ev.event_id).toContain(id);
      }
    }
  });

  it("AT-K10-08: a lane change, a rights decision and an issue close carry the right clocks", () => {
    // demo_seed_load: lane_changed in the TX-14 sources doc (activation) +
    // a decided_at rights review + okc_council_minutes's closed issue.
    const lane = byKind(buildSourceChangelog(inputs("demo_seed_load")), "lane_changed");
    expect(lane).toHaveLength(1);
    expect(lane[0]!.clock_basis).toBe("activation");
    expect(eventSummary(lane[0]!)).toContain("raw-ok → raw-review");

    const rights = byKind(buildSourceChangelog(inputs("okc_camera_registry")), "rights_decision");
    expect(rights).toHaveLength(1);
    expect(rights[0]!.clock_basis).toBe("decided_at");
    expect(rights[0]!.at).toBe("2026-09-18T00:00:00Z");

    const closed = byKind(buildSourceChangelog(inputs("okc_camera_registry")), "issue_closed");
    expect(closed).toHaveLength(1);
    expect(closed[0]!.clock_basis).toBe("closed_at");
  });

  it("rights_decision, first_ingest, first_publication, connector_version all emit", () => {
    const events = buildSourceChangelog(inputs("okc_camera_registry"));
    const kinds = events.map((e) => e.kind);
    expect(kinds).toContain("rights_decision");
    expect(kinds).toContain("first_ingest");
    expect(kinds).toContain("first_publication");
    expect(kinds).toContain("connector_version");
    const ing = byKind(events, "first_ingest")[0]!;
    expect(ing.clock_basis).toBe("finished_at");
    expect(ing.at).toBe("2026-09-15T05:11:02Z");
    const cv = byKind(events, "connector_version")[0]!;
    expect(cv.detail?.previous).toBe("0.0.0-demo");
    expect(cv.detail?.current).toBe("0.1.0-demo");
  });

  it("the TX-14 slice emits per-kind record events dated by activation", () => {
    const events = buildSourceChangelog(inputs("okc_camera_registry"));
    const added = byKind(events, "records_added")[0]!;
    const removed = byKind(events, "records_removed")[0]!;
    const changed = byKind(events, "records_changed")[0]!;
    expect(added.detail?.count).toBe(2);
    expect(removed.detail?.count).toBe(1);
    expect(changed.detail?.count).toBe(2);
    for (const ev of [added, removed, changed]) {
      expect(ev.clock_basis).toBe("activation");
      expect(ev.at).toBe("2026-10-15");
    }
  });

  it("lifecycle rows emit on their sources", () => {
    expect(byKind(buildSourceChangelog(inputs("demo_permitted_portal")), "source_added")).toHaveLength(1);
    expect(byKind(buildSourceChangelog(inputs("okc_council_minutes")), "source_newly_failing")).toHaveLength(1);
  });

  it("a source:-keyed correction emits a correction event on corrected_at", () => {
    const events = buildSourceChangelog(
      inputs("demo_seed_load", {
        corrections: [
          {
            id: "corr-demo-1",
            subject_id: "source:demo_seed_load",
            subject_label: "Demo source row",
            what_changed: "demo",
            corrected_at: "2026-10-01",
            reason: "demo",
            reported_by: "reader",
            category: "factual_error",
            outcome: "corrected",
            previous_value: "a",
            corrected_value: "b",
            previous_belief_date: "2026-09-30",
            subject_path: "/sources/demo_seed_load/",
          },
        ],
      }),
    );
    const corr = byKind(events, "correction");
    expect(corr).toHaveLength(1);
    expect(corr[0]!.clock_basis).toBe("corrected_at");
    expect(corr[0]!.at).toBe("2026-10-01");
  });

  it("an attribution correction emits on decided_at; a withdrawal on recorded_at", () => {
    const events = buildSourceChangelog(
      inputs("okc_camera_registry", {
        attribution: [{ source_id: "okc_camera_registry", decided_at: "2026-10-05" }],
        withdrawals: [
          {
            upstream_id: "DEMO-1",
            source_id: "okc_camera_registry",
            entity_id: "ent-demo",
            claim_ids: [],
            reason: "leak-provenance",
            recorded_at: "2026-10-03",
          },
        ],
      }),
    );
    expect(byKind(events, "attribution_correction")[0]!.clock_basis).toBe("decided_at");
    const w = byKind(events, "record_withdrawn")[0]!;
    expect(w.clock_basis).toBe("recorded_at");
    expect(w.at).toBe("2026-10-03");
  });

  it("events sort ascending by record clock; ids are unique", () => {
    const events = buildSourceChangelog(inputs("okc_camera_registry"));
    const times = events.map((e) => Date.parse(e.at));
    expect([...times].sort((a, b) => a - b)).toEqual(times);
    expect(new Set(events.map((e) => e.event_id)).size).toBe(events.length);
  });
});

describe("the assembled document", () => {
  it("validates as sig.source-changelog/1 and names the baseline release", () => {
    const doc = getSourceChangelog("okc_camera_registry")!;
    expect(isChangelogDoc(doc)).toBe(true);
    expect(doc.schema).toBe("sig.source-changelog/1");
    expect(doc.baseline_label).toBe("demo-release-2026-08");
    expect(doc.event_count).toBe(doc.events.length);
  });

  it("registry-only sources emit no changelog (S-11)", () => {
    expect(getSourceChangelog("demo_gated_registry")).toBeNull();
    expect(getSourceChangelog("demo_refused_source")).toBeNull();
    expect(getSourceChangelogIds()).not.toContain("demo_gated_registry");
  });

  it("a source with no versions doc still gets the baseline sentence", () => {
    expect(baselineSentence("demo-release-2026-08")).toBe(
      "History before demo-release-2026-08: rights decisions and run records only.",
    );
    expect(baselineSentence(null)).toContain("first activated release");
    const doc = getSourceChangelog("demo_permitted_portal")!;
    expect(doc.baseline_label).toBe("sig-2026-10-15.1"); // added in this release
    const noVersions = getSourceChangelog("demo_ingested_feed")!;
    expect(noVersions.baseline_label).toBeNull();
  });

  it("an absent changes doc degrades seam-by-seam (no fabricated diff)", () => {
    const events = buildSourceChangelog(inputs("okc_camera_registry", { changes: null }));
    const kinds = events.map((e) => e.kind);
    expect(kinds).not.toContain("records_added");
    expect(kinds).not.toContain("lane_changed");
    expect(kinds).toContain("rights_decision");
    expect(kinds).toContain("first_ingest");
  });
});
