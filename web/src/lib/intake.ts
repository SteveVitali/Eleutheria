// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The dispute/correction intake channel's contact address (P34.17 / R1.2).
 *
 * Under B-8 ("Email, no time promises") + WV-05 (ADR-180) the intake channel is
 * plain e-mail — the operator's address until `contact@surveillancegraph.org`
 * exists (OP-10). The address is the operator's personal e-mail, which MUST
 * NEVER be written into a file (the Part VIII / OP-10 invariant), so it is
 * injected at build time via `SIG_DISPUTE_EMAIL` and stamped into the rendered
 * page — the operator sets it for the publish build (the L2 leg of P34.17), and
 * `sig-ops publish-web` refuses a tree whose /dispute/ page still carries the
 * unset marker, so the address can never be silently absent.
 */
export function disputeIntakeEmail(): string | null {
  const v = (process.env.SIG_DISPUTE_EMAIL ?? "").trim();
  return v === "" ? null : v;
}

/**
 * The marker `sig-ops publish-web` checks: `set` when the page renders a real
 * address, `unset` when the build ran without `SIG_DISPUTE_EMAIL` (fixtures/CI —
 * a publishable tree must never ship it).
 */
export const INTAKE_EMAIL_MARKER = "data-intake-email";
