// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * Page metadata helpers (P34.13 / QW-11, RI-51; extended P36.25 / UXK14-7 —
 * SIG-UI-154's "meta descriptions per page type"). Every built page carries a
 * unique `<title>` AND a unique meta description; the shared template below —
 * copy-batch row MD-01 (B-2) — derives the description from the page's unique
 * title so a page that forgets to supply one still emits a unique, honest
 * string rather than one generic site-wide sentence. The per-type forms come
 * from `brand.ts` (`sig.social-card/1`'s sibling contract): T0 names the
 * fixed, script-free page, T2 names the interactive surface, T1/T3 keep the
 * MD-01 form verbatim.
 */
import type { PageType } from "./page-types";

export function defaultDescription(title: string, type: PageType = "T1"): string {
  switch (type) {
    case "T0":
      return `${title} — a fixed, no-JavaScript page in the Surveillance Infrastructure Graph (SIG)`;
    case "T2":
      return `${title} — interactive views over the Surveillance Infrastructure Graph (SIG): map, graph and search`;
    default:
      return `${title} — Surveillance Infrastructure Graph (SIG)`;
  }
}
