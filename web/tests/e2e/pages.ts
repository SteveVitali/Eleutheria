// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The shell's pages, plus one representative task-intake page. Kept in one place so
// the a11y sweep and the no-JS checks cover the same surface.
import { absenceTaskHref } from "../../src/lib/task";

// The standard shell-layout pages: each carries the primary nav and the citation
// affordance (SIG-UI-035). The dossier page is one of these; its PRINT export is a
// standalone paginated document (no nav/citation by design) and is covered by the
// a11y sweep below, not here.
export const SHELL_PAGES = [
  "/",
  "/dossier/oklahoma-city/",
  "/visual-language/",
  "/reference-map/",
  "/reference-graph/",
] as const;

// The worked dossier's canonical slug + its derived surfaces (SIG-UI-010..015).
export const DOSSIER_SLUG = "oklahoma-city";
export const DOSSIER_PAGE = `/dossier/${DOSSIER_SLUG}/`;
export const DOSSIER_PRINT = `/dossier/${DOSSIER_SLUG}/print/`;
export const DOSSIER_JSON = `/dossier/${DOSSIER_SLUG}.json`;

// One pre-generated task-intake page (SIG-UI-007), built with the same href helper
// the hatches use, so it always matches a page `getStaticPaths` generated.
export const TASK_PAGE = absenceTaskHref({
  subject_id: "agency:okcpd",
  predicate_id: "sharing_partners",
  absence_kind: "NOT_RESEARCHED",
  predicate_label: "Data-sharing partners",
});

export const ALL_PAGES = [...SHELL_PAGES, TASK_PAGE] as const;

// The full a11y surface for the axe sweep: the shell-layout pages, a task-intake
// page, and the standalone dossier print export (WCAG 2.2 AA everywhere, SIG-UI-037).
export const A11Y_PAGES = [...ALL_PAGES, DOSSIER_PRINT] as const;
