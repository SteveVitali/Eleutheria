// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.62 (K11 RQ-03b / SIG-RQ-002/008/009): the task-page model legs —
// §5.3 blocks each a value or named absence, the gap→task/campaign resolver,
// the id-alias derivation and the sig.task-page/1 twin.
import { describe, expect, it } from "vitest";
import { QUEUE_CAMPAIGNS, RESEARCH_QUEUE } from "../../src/lib/corrections-methodology-fixture";
import { dispositionsFor } from "../../src/lib/research-queue";
import type { ResearchTaskCard } from "../../src/lib/research-queue";
import {
  resolveGapLink,
  statusLine,
  taskHandleRows,
  taskIdAliases,
  taskPageTwin,
  triggerSentence,
  unknownNote,
  whyItMatters,
} from "../../src/lib/task-page";

const card: ResearchTaskCard = RESEARCH_QUEUE[1]!; // conflicting_retention w/ predicate+trigger

describe("taskIdAliases — SIG-RQ-009", () => {
  it("emits one /task/<task_id>/ → /task/<handle>/ alias per handled card", () => {
    const aliases = taskIdAliases(RESEARCH_QUEUE);
    expect(aliases.length).toBe(RESEARCH_QUEUE.length);
    for (const a of aliases) {
      expect(a.taskId).not.toBe(a.handle);
      expect(a.handle.startsWith("T-")).toBe(true);
    }
  });

  it("taskHandleRows merges artifact rows ahead of derived aliases, deduped on old", () => {
    const artifact = [
      { old: "/task/T-usa-ok-tulsa-coverage-first-m4p2/", target: "/task/T-usa-ok-tulsa-coverage-first-m9z9/", note: "renamed" },
    ];
    const rows = taskHandleRows(RESEARCH_QUEUE, artifact);
    const olds = rows.map((r) => r.old);
    expect(new Set(olds).size).toBe(olds.length);
    expect(rows.find((r) => r.old === artifact[0]!.old)!.target).toBe(artifact[0]!.target);
    for (const c of RESEARCH_QUEUE) {
      expect(rows.some((r) => r.old === `/task/${c.task_id}/` && r.target === `/task/${c.handle}/`)).toBe(true);
    }
  });
});

describe("resolveGapLink — SIG-RQ-008", () => {
  it("resolves a gap to the task naming the same subject + predicate", () => {
    const link = resolveGapLink(
      { subject_id: "agency:okcpd", predicate_id: "configured_retention_days" },
      RESEARCH_QUEUE,
      QUEUE_CAMPAIGNS,
    );
    expect(link.kind).toBe("task");
    if (link.kind === "task") {
      expect(link.href).toBe(`task/${card.handle}/`);
    }
  });

  it("resolves the unmapped-devices gap to the devices task", () => {
    const link = resolveGapLink(
      { subject_id: "agency:okcpd", predicate_id: "device_coordinates" },
      RESEARCH_QUEUE,
      QUEUE_CAMPAIGNS,
    );
    expect(link.kind).toBe("task");
    if (link.kind === "task") expect(link.handle).toBe(RESEARCH_QUEUE[0]!.handle);
  });

  it("resolves a member gap to its campaign page", () => {
    const link = resolveGapLink(
      { subject_id: "osm:node:101", predicate_id: "operator" },
      RESEARCH_QUEUE,
      QUEUE_CAMPAIGNS,
    );
    expect(link.kind).toBe("campaign");
    if (link.kind === "campaign") {
      expect(link.href).toBe(`research-queue/campaign/${QUEUE_CAMPAIGNS[0]!.handle}/`);
    }
  });

  it("returns the named absence for an unqueued gap — never a guessed link", () => {
    const link = resolveGapLink(
      { subject_id: "agency:okcpd", predicate_id: "sharing_partners" },
      RESEARCH_QUEUE,
      QUEUE_CAMPAIGNS,
    );
    expect(link.kind).toBe("none");
  });
});

describe("the §5.3 block model — SIG-RQ-002", () => {
  it("every card yields a status line and a closing path", () => {
    for (const c of RESEARCH_QUEUE) {
      expect(statusLine(c, null)).toContain("anyone may work this task");
      expect(whyItMatters(c).length).toBeGreaterThan(0);
      expect(triggerSentence(c).length).toBeGreaterThan(0);
      // What's unknown is a value or the recorded-absence fallback — never "".
      expect(unknownNote(c) ?? "named absence").not.toBe("");
    }
  });

  it("statusLine names the dispositions on a closed task", () => {
    const closed = { ...card, disposition: "resolved_evidence_found" };
    expect(statusLine(closed, null)).toBe("Closed · resolved_evidence_found");
  });
});

describe("taskPageTwin — sig.task-page/1", () => {
  it("carries the card fields verbatim, incl. the related handles", () => {
    const twin = taskPageTwin(card, { claimedBy: null, related: [RESEARCH_QUEUE[0]!] });
    expect(twin.schema).toBe("sig.task-page/1");
    expect(twin.handle).toBe(card.handle);
    expect(twin.task_id).toBe(card.task_id);
    expect(twin.closing_condition).toBe(card.closing_condition);
    expect(twin.predicate_ids).toEqual(card.predicate_ids);
    expect(twin.related_handles).toEqual([RESEARCH_QUEUE[0]!.handle]);
  });

  it("an unhandled card still twins with null handle/id (the honest absence)", () => {
    const bare: ResearchTaskCard = {
      task_type: "coverage_hole",
      subject_id: "x",
      subject_label: "Subject",
      closing_condition: "c",
      evidence_sought: "e",
      assignee_class: "analyst",
      effort_estimate: "quick",
      geographic_scope: "global",
      jurisdiction: "",
      dispositions: dispositionsFor("analyst"),
      priority: 0.1,
    };
    const twin = taskPageTwin(bare, { claimedBy: null, related: [] });
    expect(twin.handle).toBeNull();
    expect(twin.task_id).toBeNull();
  });
});
