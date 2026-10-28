// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * `sig.workspace-state/2` (P36.21; SIG-UI-052/059/060/093; ADR-155) — the
 * public interface of the v2 workspace-state package:
 *
 * - `registry.ts` — the one parameter registry (`sig.workspace-state-registry/1`)
 *   and the T2 surface / view vocabulary;
 * - `state.ts` — the pure contract: parse (v=1-compatible, tolerant-with-
 *   receipts), canonicalise (`bbox`/`frame`/`kind=site`/legacy jkeys → the
 *   canonical forms, each rewrite named in `notes`), serialise (defaults
 *   omitted, registry order — byte-stable round-trips);
 * - `conformance.ts` — the surface × facet harness: every parameter a
 *   surface receives is either applied or visibly named;
 * - `cite.ts` — "cite this view" (`/s/<pub>/<surface>/?v=2&…`, J3 §8.1
 *   interim) and the T2 `noindex,follow` policy.
 *
 * The `v=1` contract module `web/src/lib/workspace-state.ts` remains for the
 * v1 tests and contract references; new code imports from this package.
 */

export * from "./registry";
export * from "./state";
export * from "./conformance";
export * from "./cite";

// The record-key helpers are publication-route functions, not versioned state —
// the v1 module's implementations remain the single source and are re-exported
// here so v2 call sites have one import path.
export {
  evidenceAnchorHref,
  recordRoutes,
  splitRecordKey,
} from "../workspace-state";
export type { LocationFilter } from "../workspace-state";
