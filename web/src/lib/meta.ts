// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * Page metadata helpers (P34.13 / QW-11, RI-51). Every built page carries a
 * unique `<title>` AND a unique meta description; the shared template below —
 * copy-batch row MD-01 (B-2) — derives the description from the page's unique
 * title so a page that forgets to supply one still emits a unique, honest
 * string rather than one generic site-wide sentence.
 */
export function defaultDescription(title: string): string {
  return `${title} — Surveillance Infrastructure Graph (SIG)`;
}
