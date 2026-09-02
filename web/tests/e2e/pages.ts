// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The shell's pages, plus one representative task-intake page. Kept in one place so
// the a11y sweep and the no-JS checks cover the same surface.
import { absenceTaskHref } from "../../src/lib/task";

export const SHELL_PAGES = [
  "/",
  "/visual-language/",
  "/reference-map/",
  "/reference-graph/",
] as const;

// One pre-generated task-intake page (SIG-UI-007), built with the same href helper
// the hatches use, so it always matches a page `getStaticPaths` generated.
export const TASK_PAGE = absenceTaskHref({
  subject_id: "agency:okcpd",
  predicate_id: "sharing_partners",
  absence_kind: "NOT_RESEARCHED",
  predicate_label: "Data-sharing partners",
});

export const ALL_PAGES = [...SHELL_PAGES, TASK_PAGE] as const;
