// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { describe, expect, it } from "vitest";
import {
  ASSIGNEE_CLASSES,
  assertUniqueTaskAnchors,
  canRecordNoEvidence,
  claimIsActive,
  claimStatusFor,
  DISPOSITIONS,
  dispositionsFor,
  jurisdictionAnchors,
  NOT_YET_CLASSIFIED,
  orderQueue,
  queueJurisdictions,
  SEARCHED_FOUND_NOTHING,
  taskAnchor,
  tasksForJurisdiction,
} from "../../src/lib/research-queue";
import type { JurisdictionClaim, ResearchTaskCard } from "../../src/lib/research-queue";
import {
  JURISDICTION_CLAIMS,
  QUEUE_AS_OF,
  RESEARCH_QUEUE,
} from "../../src/lib/corrections-methodology-fixture";

describe("research queue task cards (SIG-UI-031, §33)", () => {
  it("every card states the four required fields", () => {
    for (const card of RESEARCH_QUEUE) {
      expect(card.closing_condition.length).toBeGreaterThan(0);
      expect(card.evidence_sought.length).toBeGreaterThan(0);
      expect(ASSIGNEE_CLASSES).toContain(card.assignee_class);
      expect(["quick", "moderate", "substantial"]).toContain(card.effort_estimate);
    }
  });

  it("search-work tasks carry the 'searched, found nothing' disposition (SIG-TASK-009)", () => {
    // A field_mapper / records_requester / analyst / local_group task can conclude
    // resolved_no_evidence_exists; a curator/developer clean-up task cannot.
    expect(dispositionsFor("field_mapper")).toContain(SEARCHED_FOUND_NOTHING);
    expect(dispositionsFor("records_requester")).toContain(SEARCHED_FOUND_NOTHING);
    expect(dispositionsFor("developer")).not.toContain(SEARCHED_FOUND_NOTHING);
    const searchCard = RESEARCH_QUEUE.find((c) => c.assignee_class === "field_mapper")!;
    expect(canRecordNoEvidence(searchCard)).toBe(true);
  });

  it("records/document work can be blocked by a fee or a denial (§33.4)", () => {
    expect(dispositionsFor("records_requester")).toContain("blocked_fee");
    expect(dispositionsFor("records_requester")).toContain("blocked_access_denied");
    expect(dispositionsFor("analyst")).not.toContain("blocked_fee");
  });
});

describe("geographic filtering (§33.5, SIG-TASK-010)", () => {
  it("lists the distinct jurisdictions sorted", () => {
    expect(queueJurisdictions(RESEARCH_QUEUE)).toEqual(
      [...new Set(RESEARCH_QUEUE.map((c) => c.jurisdiction))].sort(),
    );
  });

  it("a global-scope task is visible under every jurisdiction; place tasks only under their own", () => {
    const okc = tasksForJurisdiction(RESEARCH_QUEUE, "Oklahoma City");
    const tulsa = tasksForJurisdiction(RESEARCH_QUEUE, "Tulsa");
    // The global link-rot task appears in both.
    expect(okc.some((c) => c.geographic_scope === "global")).toBe(true);
    expect(tulsa.some((c) => c.geographic_scope === "global")).toBe(true);
    // The OKC-scoped tasks do not leak into Tulsa's view.
    expect(tulsa.some((c) => c.jurisdiction === "Oklahoma City")).toBe(false);
  });
});

describe("claiming with expiry — priority, never exclusivity (SIG-TASK-010/011)", () => {
  const claim: JurisdictionClaim = {
    jurisdiction: "Oklahoma City",
    claimed_by: "Group",
    claimed_at: "2026-07-01",
    expires_at: "2026-10-01",
  };

  it("a claim is active before expiry and expires without renewal", () => {
    expect(claimIsActive(claim, "2026-08-20")).toBe(true);
    expect(claimIsActive(claim, "2026-10-01")).toBe(false);
    expect(claimIsActive(claim, "2026-11-01")).toBe(false);
  });

  it("claim status always reports that any contributor may work the task", () => {
    const card = RESEARCH_QUEUE.find((c) => c.jurisdiction === "Oklahoma City")!;
    const status = claimStatusFor(card, JURISDICTION_CLAIMS, QUEUE_AS_OF);
    expect(status.claimed).toBe(true);
    expect(status.anyone_may_work).toBe(true);
  });

  it("an unclaimed jurisdiction reports no claimant, still workable by anyone", () => {
    const card = RESEARCH_QUEUE.find((c) => c.jurisdiction === "Tulsa")!;
    const status = claimStatusFor(card, JURISDICTION_CLAIMS, QUEUE_AS_OF);
    expect(status.claimed).toBe(false);
    expect(status.claimed_by).toBeNull();
    expect(status.anyone_may_work).toBe(true);
  });
});

describe("queue ordering (no volume leaderboard, SIG-TASK-012)", () => {
  it("puts a claimed jurisdiction's tasks first, then by priority", () => {
    const ordered = orderQueue(RESEARCH_QUEUE, JURISDICTION_CLAIMS, QUEUE_AS_OF);
    // The first card is in the claimed jurisdiction (Oklahoma City).
    expect(ordered[0]!.jurisdiction).toBe("Oklahoma City");
    // Ordering is a stable function of the tasks/claims only — it carries no
    // contributor identity or volume ranking.
    expect(ordered.length).toBe(RESEARCH_QUEUE.length);
  });
});

// P34.12 / K11 RQ-00 (C3 NEW-10, NEW-13): unique card ids, live anchors, the
// catalog disposition vocabulary, and "not yet classified" instead of invented
// contributor/unknown placeholders — asserted over fixture AND export-shaped
// cards (the export path is what produced the placeholders; see
// exports/src/exports/spine_export.py::_research_queue).
describe("queue truth fixes (P34.12 / K11 RQ-00)", () => {
  // A card shaped like an export row for a task type the catalog does not know —
  // the shape `_research_queue` now emits instead of contributor/unknown/[].
  const UNCLASSIFIED: ResearchTaskCard = {
    task_id: "7c9e2b54-0000-4000-8000-0000000000aa",
    task_type: "geolocate_devices", // not a §33.2 catalog slug
    subject_id: "subjX",
    subject_label: "subjX",
    closing_condition: "≥1 coordinate claim exists for subjX",
    evidence_sought: "geolocate_devices",
    assignee_class: NOT_YET_CLASSIFIED,
    effort_estimate: NOT_YET_CLASSIFIED,
    geographic_scope: NOT_YET_CLASSIFIED,
    jurisdiction: "",
    dispositions: [...DISPOSITIONS], // unclassified → the full legal vocabulary
    priority: 5.0,
  };

  it("every card anchor is unique — a shared jurisdiction never collides", () => {
    const ordered = orderQueue(RESEARCH_QUEUE, JURISDICTION_CLAIMS, QUEUE_AS_OF);
    expect(() => assertUniqueTaskAnchors(ordered)).not.toThrow();
    const anchors = ordered.map(taskAnchor);
    expect(new Set(anchors).size).toBe(anchors.length);
    // Two cards share the fixture's Oklahoma City jurisdiction — their ids differ.
    const okc = ordered.filter((c) => c.jurisdiction === "Oklahoma City");
    expect(okc.length).toBeGreaterThan(1);
    expect(new Set(okc.map(taskAnchor)).size).toBe(okc.length);
  });

  it("the anchor derives from the task identity, never the jurisdiction", () => {
    const card = RESEARCH_QUEUE[0]!;
    expect(taskAnchor(card)).toBe(`task-${card.task_id}`);
    // A card without a task_id (older export) falls back to the dedup key
    // (sanitized to an HTML-safe id).
    const { task_id: _id, ...noId } = card;
    const fallback = taskAnchor(noId);
    expect(fallback).not.toBe(taskAnchor(card));
    expect(fallback).toMatch(/^task-/);
    expect(fallback).toContain("missing-physical-devices"); // task_type
    expect(fallback).toContain("okcpd"); // subject_id
  });

  it("a colliding anchor fails the build — never a silent duplicate id", () => {
    const a = RESEARCH_QUEUE[0]!;
    const dupe = { ...a };
    expect(() => assertUniqueTaskAnchors([a, dupe])).toThrow(/share the anchor/);
  });

  it("every jurisdiction filter target is a live anchor on a rendered card", () => {
    const ordered = orderQueue(RESEARCH_QUEUE, JURISDICTION_CLAIMS, QUEUE_AS_OF);
    const rendered = new Set(ordered.map(taskAnchor));
    const anchors = jurisdictionAnchors(ordered);
    expect(new Set(anchors.keys())).toEqual(new Set(ordered.map((c) => c.jurisdiction)));
    for (const target of anchors.values()) expect(rendered.has(target)).toBe(true);
  });

  it("card dispositions always come from the §33.4 vocabulary — never []", () => {
    for (const card of [...RESEARCH_QUEUE, UNCLASSIFIED]) {
      expect(card.dispositions.length).toBeGreaterThan(0);
      for (const d of card.dispositions) expect(DISPOSITIONS).toContain(d);
    }
    // An unclassified task may reach ANY legal outcome — including
    // searched-found-nothing (SIG-TASK-009).
    expect(UNCLASSIFIED.dispositions).toEqual([...DISPOSITIONS]);
    expect(canRecordNoEvidence(UNCLASSIFIED)).toBe(true);
  });

  it("no card ever emits the contributor/unknown placeholders (NEW-10)", () => {
    for (const card of [...RESEARCH_QUEUE, UNCLASSIFIED]) {
      expect(card.assignee_class).not.toBe("contributor");
      expect(card.effort_estimate).not.toBe("unknown");
      // The honest fallback is the named label, not another invented value.
      for (const v of [card.assignee_class, card.effort_estimate, card.geographic_scope]) {
        expect(
          [...ASSIGNEE_CLASSES, "quick", "moderate", "substantial", "jurisdiction", "region", "global", NOT_YET_CLASSIFIED],
        ).toContain(v);
      }
    }
  });
});
