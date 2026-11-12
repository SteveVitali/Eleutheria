// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.40 (R11-K13-CHG-01, SIG-UI-072) — the changes surface's unit leg:
// doc validation fails closed, the SIG-vs-world classification, feed
// scoping, Atom/OPML emission, the empty feed and the demo fixture.
import { describe, expect, it } from "vitest";
import {
  CHANGES_OPML_PATH,
  changeFeedScopes,
  changeRows,
  changesFeedPath,
  recordEventClass,
  rowsForClass,
  scopeRows,
  sourceChangeClass,
  validateChangesFeed,
  validateChangesIndex,
  validateSourceChanges,
} from "../../src/lib/changes";
import {
  atomStamp,
  entryId,
  toChangesAtom,
  toChangesOpml,
} from "../../src/lib/changes-feeds";
import { CHANGES_FIXTURE } from "../../src/lib/changes-fixture";

const PLACES = [
  { path: "usa/ok", name: "Oklahoma" },
  { path: "usa/ok/oklahoma-city-4064000", name: "Oklahoma City" },
  { path: "unplaced", name: "Not yet placed" },
];
const SOURCES = [
  { id: "okc_camera_registry", name: "OKC camera registry" },
  { id: "demo_gated_registry", name: "Demo gated registry" },
];

describe("validate*", () => {
  it("accepts the committed fixture docs", () => {
    expect(() => validateChangesIndex(CHANGES_FIXTURE.index, "x")).not.toThrow();
    expect(() => validateSourceChanges(CHANGES_FIXTURE.sources, "x")).not.toThrow();
    expect(() => validateChangesFeed(CHANGES_FIXTURE.feed, "x")).not.toThrow();
  });
  it("fails closed on a wrong schema or malformed event", () => {
    expect(() => validateChangesIndex({ schema: "nope" }, "x")).toThrow(/not a valid/);
    expect(() =>
      validateChangesFeed(
        { schema: "sig.release-changes-feed/1", release: { publication_id: "p-1" }, events: [{ change_type: "bogus" }] },
        "x",
      ),
    ).toThrow(/artifact_id/);
    expect(() => validateSourceChanges({ schema: "sig.release-source-changes/1", state: "weird" }, "x")).toThrow();
  });
});

describe("the two classes (SIG-UI-072)", () => {
  it("splits record events: source_withdrawn → world, everything else → sig records", () => {
    const mk = (change_type: "added" | "removed" | "changed", reason?: string) =>
      recordEventClass({
        artifact_id: "k",
        field: "record",
        change_type,
        old_value: null,
        new_value: null,
        old_date: null,
        new_date: null,
        reason,
      });
    expect(mk("added")).toBe("sig_records");
    expect(mk("changed")).toBe("sig_records");
    expect(mk("removed", "superseded")).toBe("sig_records");
    expect(mk("removed", "no_longer_published")).toBe("sig_records");
    expect(mk("removed", "withdrawn")).toBe("sig_records");
    expect(mk("removed", "source_withdrawn")).toBe("world_changed");
  });
  it("splits source rows: retired/newly_failing → world, added/lane_changed → sig records", () => {
    expect(sourceChangeClass("retired")).toBe("world_changed");
    expect(sourceChangeClass("newly_failing")).toBe("world_changed");
    expect(sourceChangeClass("added")).toBe("sig_records");
    expect(sourceChangeClass("lane_changed")).toBe("sig_records");
  });
  it("the fixture's rows classify both ways", () => {
    const rows = changeRows(CHANGES_FIXTURE);
    const world = rowsForClass(rows, "world_changed");
    const sig = rowsForClass(rows, "sig_records");
    expect(world.length).toBeGreaterThan(0);
    expect(sig.length).toBeGreaterThan(0);
    expect(world.every((r) => r.kind === "source" || (r.kind === "record" && r.change === "removed"))).toBe(true);
    // dates come from the diff (world dates), never a wall clock
    expect(world.every((r) => r.date === "2026-10-15")).toBe(true);
  });
});

describe("feed scopes", () => {
  const scopes = changeFeedScopes(PLACES, SOURCES);
  it("mints all + every place + every source", () => {
    expect(scopes.map((s) => s.path)).toEqual([
      "all",
      "place/usa/ok",
      "place/usa/ok/oklahoma-city-4064000",
      "place/unplaced",
      "source/okc_camera_registry",
      "source/demo_gated_registry",
    ]);
    expect(changesFeedPath("place/usa/ok")).toBe("changes/feeds/place/usa/ok.atom");
    expect(CHANGES_OPML_PATH).toBe("changes/feeds.opml");
  });
  it("a place feed covers the place AND its descendants", () => {
    const rows = scopeRows(changeRows(CHANGES_FIXTURE), scopes, "place/usa/ok")!;
    expect(rows.length).toBeGreaterThan(0);
    expect(rows.every((r) => r.jurisdiction === "usa/ok" || r.jurisdiction?.startsWith("usa/ok/"))).toBe(true);
    expect(rows.some((r) => r.jurisdiction === "usa/ok/oklahoma-city-4064000")).toBe(true);
    // a different branch contributes nothing
    expect(rows.every((r) => r.jurisdiction !== "usa/tx/harris-county-48201")).toBe(true);
  });
  it("a source feed carries the source's record + lifecycle rows", () => {
    const rows = scopeRows(changeRows(CHANGES_FIXTURE), scopes, "source/demo_gated_registry")!;
    expect(rows.some((r) => r.kind === "source" && r.change === "retired")).toBe(true);
    expect(rows.some((r) => r.kind === "record" && r.sourceIds.includes("demo_gated_registry"))).toBe(true);
  });
  it("an un-minted scope resolves null (never a 200 on nothing)", () => {
    expect(scopeRows(changeRows(CHANGES_FIXTURE), scopes, "place/usa/never")).toBeNull();
  });
});

describe("Atom + OPML emission", () => {
  const scopes = changeFeedScopes(PLACES, SOURCES);
  const rows = scopeRows(changeRows(CHANGES_FIXTURE), scopes, "all")!;
  const atom = toChangesAtom({
    title: "SIG changes — every change",
    selfUrl: "https://surveillancegraph.org/changes/feeds/all.atom",
    pageUrl: "https://surveillancegraph.org/changes/",
    updated: "2026-10-15T00:00:00.000Z",
    publicationId: "p-demo",
    rows,
    feedDescription: "d",
  });
  it("emits a valid feed doc — feed/id/title/updated/self/alternate, entries dated", () => {
    expect(atom).toContain('<feed xmlns="http://www.w3.org/2005/Atom">');
    expect(atom).toContain('<link rel="self" type="application/atom+xml" href="https://surveillancegraph.org/changes/feeds/all.atom"/>');
    const entries = atom.split("  <entry>").slice(1);
    expect(entries.length).toBe(rows.length);
    for (const e of entries) {
      expect(e).toContain("<id>urn:sig:change:p-demo:");
      expect(e).toContain("<updated>");
      expect(e).toContain("<published>");
      expect(e).toContain("<category ");
      expect(e).toContain("<content type=\"text\">");
    }
  });
  it("entry ids are stable + xml is escaped", () => {
    expect(entryId(rows[0]!, "p-1")).toBe(`urn:sig:change:p-1:${rows[0]!.key}:${rows[0]!.change}:${rows[0]!.field ?? rows[0]!.change}`);
    const esc = toChangesAtom({
      title: 'a "b" <c> & d',
      selfUrl: "https://x/f.atom",
      pageUrl: "https://x/",
      updated: "2026-01-01T00:00:00.000Z",
      publicationId: "p-1",
      rows: [],
      feedDescription: "d",
    });
    expect(esc).toContain("a &quot;b&quot; &lt;c&gt; &amp; d");
  });
  it("an empty scope still emits a valid feed", () => {
    const empty = toChangesAtom({
      title: "t",
      selfUrl: "https://x/f.atom",
      pageUrl: "https://x/",
      updated: "2026-01-01T00:00:00.000Z",
      publicationId: "p-1",
      rows: [],
      feedDescription: "d",
    });
    expect(empty).toContain("</feed>");
    expect(empty).not.toContain("<entry>");
  });
  it("atomStamp normalises date-only and rejects garbage", () => {
    expect(atomStamp("2026-10-15")).toBe("2026-10-15T00:00:00.000Z");
    expect(() => atomStamp("nope")).toThrow(/invalid ISO/);
  });
  it("the OPML bundle outlines every scope to an .atom feed", () => {
    const opml = toChangesOpml({
      scopes,
      title: "SIG change feeds",
      feedUrl: (s) => `https://x/changes/feeds/${s}.atom`,
      pageUrl: (p) => `https://x/${p}`,
      dateCreated: "Thu, 15 Oct 2026 00:00:00 GMT",
    });
    expect(opml).toContain('<opml version="2.0">');
    for (const s of scopes) {
      expect(opml).toContain(`xmlUrl="https://x/changes/feeds/${s.path}.atom"`);
    }
  });
});
