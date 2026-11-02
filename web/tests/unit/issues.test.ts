// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { describe, expect, it } from "vitest";
import {
  getIssues,
  ISSUES_FIXTURE,
  isIssueRecord,
  issueClassLabel,
  issueLogPages,
  issuesBySource,
  issuesForSource,
  issueText,
  sourceNameMap,
} from "../../src/lib/issues";

describe("issues fixture", () => {
  it("validates as sig.source-issue/1", () => {
    for (const r of ISSUES_FIXTURE) expect(isIssueRecord(r)).toBe(true);
  });

  it("fixtures mode returns the committed rows", () => {
    expect(getIssues().length).toBe(ISSUES_FIXTURE.length);
  });

  it("open rows sort before closed rows per source (append-only)", () => {
    const rows = issuesForSource(ISSUES_FIXTURE, "okc_camera_registry");
    expect(rows.length).toBe(2);
    expect(rows[0]!.closed_at).toBeNull();
    expect(rows[1]!.closed_at).not.toBeNull();
  });

  it("curated pending rows never carry public text (D-J3-12)", () => {
    for (const r of ISSUES_FIXTURE) {
      if (r.text_state === "pending_review") {
        expect(r.text === null || r.text === undefined).toBe(true);
        expect(issueText(r)).toBe("known-issue text pending review");
      }
    }
  });

  it("confirmed curated rows render their text + correction ref", () => {
    const closed = ISSUES_FIXTURE.find((r) => r.issue_id.startsWith("ki:okc_council_minutes"));
    expect(closed?.closed_at).not.toBeNull();
    expect(issueText(closed!)).toContain("Demonstration entry");
    expect(closed?.correction_ref).toBeTruthy();
  });

  it("groups by source", () => {
    const map = issuesBySource(ISSUES_FIXTURE);
    expect(map.has("demo_ingested_feed")).toBe(true);
    expect([...map.keys()]).toEqual([...map.keys()].sort());
  });

  it("paginates the source groups (K9 §6.1 fallback)", () => {
    const pages = issueLogPages(ISSUES_FIXTURE);
    expect(pages.length).toBe(1);
    expect(pages[0]!.length).toBe(issuesBySource(ISSUES_FIXTURE).size);
    expect(issueLogPages([])).toEqual([[]]);
  });

  it("class labels cover the vocabularies", () => {
    expect(issueClassLabel("axis_swap")).toBe("axis-swapped coordinates");
    expect(issueClassLabel("never_run")).toBe("never run");
    expect(issueClassLabel("upstream_http_503")).toBe("upstream http 503");
  });

  it("the name map falls back to the id", () => {
    const names = sourceNameMap();
    expect(names.get("okc_camera_registry")).toBeTruthy();
    expect(names.get("missing_source")).toBeUndefined();
  });
});
