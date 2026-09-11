// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { describe, expect, it } from "vitest";
import {
  ABSENCE_TASK_TYPE,
  INITIAL_TASK_STATUS,
  absenceTaskHref,
  buildResearchTask,
  decodeTaskSlug,
  taskSlug,
} from "../../src/lib/task";
import { TASKABLE_ABSENCES } from "../../src/lib/fixtures";
import type { AbsenceTaskParams } from "../../src/lib/task";

const PARAMS: AbsenceTaskParams = {
  subject_id: "agency:okcpd",
  predicate_id: "sharing_partners",
  absence_kind: "NOT_RESEARCHED",
  predicate_label: "Data-sharing partners",
};

describe("absence → research task (SIG-UI-007)", () => {
  it("generates a well-formed task in the GENERATED state", () => {
    const task = buildResearchTask(PARAMS);
    expect(task.status).toBe(INITIAL_TASK_STATUS);
    expect(task.status).toBe("generated");
    expect(task.task_type).toBe(ABSENCE_TASK_TYPE);
    expect(task.subject_id).toBe("agency:okcpd");
    expect(task.predicate_id).toBe("sharing_partners");
    expect(task.absence_kind).toBe("NOT_RESEARCHED");
    expect(task.rationale).toContain("Data-sharing partners");
  });

  it("keys the task for de-duplication on (task_type, subject)", () => {
    const task = buildResearchTask(PARAMS);
    expect(task.dedup_key).toEqual([ABSENCE_TASK_TYPE, "agency:okcpd"]);
  });

  it("round-trips through the slug (encode → href → decode) losslessly", () => {
    const decoded = decodeTaskSlug(taskSlug(PARAMS));
    expect(decoded).toEqual(PARAMS);
  });

  it("rejects a malformed or unknown-kind slug rather than fabricating a task", () => {
    expect(decodeTaskSlug("only~two")).toBeNull();
    expect(decodeTaskSlug("agency:x~pred~NOT_A_KIND")).toBeNull();
  });

  it("builds a no-JS GET href whose segment is the URL-safe slug the route generates", () => {
    const href = absenceTaskHref(PARAMS);
    expect(href.startsWith("/task/new/")).toBe(true);
    expect(href.endsWith("/")).toBe(true);
    const segment = href.slice("/task/new/".length, -1);
    // base64url is URL- and filesystem-safe, so the href segment IS the slug.
    expect(segment).toBe(taskSlug(PARAMS));
    expect(segment).toMatch(/^[A-Za-z0-9_-]+$/);
  });

  it("every taskable absence in the registry decodes to a buildable task", () => {
    for (const params of TASKABLE_ABSENCES) {
      const decoded = decodeTaskSlug(taskSlug(params));
      expect(decoded).not.toBeNull();
      const task = buildResearchTask(decoded!);
      expect(task.status).toBe("generated");
    }
  });
});
