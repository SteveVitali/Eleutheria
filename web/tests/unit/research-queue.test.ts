// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { describe, expect, it } from "vitest";
import {
  ASSIGNEE_CLASSES,
  canRecordNoEvidence,
  claimIsActive,
  claimStatusFor,
  dispositionsFor,
  orderQueue,
  queueJurisdictions,
  SEARCHED_FOUND_NOTHING,
  tasksForJurisdiction,
} from "../../src/lib/research-queue";
import type { JurisdictionClaim } from "../../src/lib/research-queue";
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
