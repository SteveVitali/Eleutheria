// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * Display formatting for built page text (P34.13, K14 §3.6 / DR-K14-19).
 *
 * English digit grouping: every run of five or more digits is grouped with
 * commas (3,994 → unchanged at four; 2423200 → 2,423,200). Exact counts are
 * NEVER rounded — grouping changes separators only, never the value. Runs
 * shorter than five digits stay ungrouped by design (K14 §3.6), and a run of
 * four inside a longer run is part of that run ("1234567" → "1,234,567").
 */

/** Group every digit run of five or more inside `text` with commas. */
export function groupDigits(text: string): string {
  return text.replace(/\d{5,}/g, (run) => run.replace(/\B(?=(\d{3})+(?!\d))/g, ","));
}

/** Format an integer for display with English digit grouping. */
export function fmtInt(n: number): string {
  return groupDigits(String(n));
}
