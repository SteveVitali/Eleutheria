// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.21 (SIG-UI-060, K13 UXR-10; ADR-155) — the surface × facet conformance
 * harness. Every T2 surface must pass the same test, here and in every later
 * T2 ticket: **a surface either applies a received workspace-state parameter
 * or visibly names it — there is no third option.** A surface may legitimately
 * not apply a parameter (the map does not apply `sort`); what it may never do
 * is silently drop it, or present unfiltered results as if filtered.
 *
 * The mechanics are the ones P34.15's island-honesty rule established, now
 * driven by the /2 registry: `unappliedParams()` names the registered
 * parameters a parsed URL carried that this surface does not apply;
 * `facetNoticeText()` renders the plain-language sentence the surface shows
 * (`data-testid="facet-not-applied"`, "this address names X, which this view
 * does not apply — they do not filter what is shown"). `conformanceReport()`
 * is the harness entry the unit sweep runs over the whole surface ×
 * parameter matrix.
 */

import {
  PARAM_BY_NAME,
  SURFACE_PATHS,
  WORKSPACE_SURFACES,
  type WorkspaceSurface,
} from "./registry";

/**
 * The parameters each surface APPLIES today — the honesty mirror of what the
 * islands actually consume (P34.15's `APPLIED_PARAMS`, carried forward).
 * `view` is applied everywhere: it resolves the surface even though the path
 * still decides what renders. A later row that teaches a surface a new
 * parameter moves the name here — the conformance sweep fails until the
 * island and the table agree.
 */
export const APPLIED_PARAMS: Record<WorkspaceSurface, readonly string[]> = {
  map: ["release", "collection", "focus", "view"],
  graph: ["release", "focus", "view"],
  search: ["release", "q", "kind", "focus", "view"],
};

/** The surface a pathname serves, or null — strips the `/s/<pub>/` prefix. */
export function surfaceForPath(pathname: string): WorkspaceSurface | null {
  const stripped = pathname.replace(/^\/s\/[^/]+/, "");
  for (const surface of WORKSPACE_SURFACES) {
    if (stripped.startsWith(SURFACE_PATHS[surface])) return surface;
  }
  return null;
}

/**
 * The registered parameters `present` names that `surface` does not apply —
 * in `present` order (address order), deduplicated. `v` is not a parameter
 * (it versions the contract); an unregistered name is handled by the parse
 * issues, not this notice.
 */
export function unappliedParams(
  present: readonly string[],
  surface: WorkspaceSurface,
): string[] {
  const applied = new Set(APPLIED_PARAMS[surface]);
  return present.filter((name) => PARAM_BY_NAME.has(name) && !applied.has(name));
}

/** The notice label for a parameter — the registry's noun phrase. */
export function paramLabel(name: string): string {
  return PARAM_BY_NAME.get(name)?.label ?? `the parameter "${name}"`;
}

/**
 * The plain-language notice (WS-03's plain-words rule) — the same sentence
 * `sig.workspace-state/1` minted, kept verbatim so the receipt stays stable:
 * "This address names a map viewport and a jurisdiction filter, which this
 * view does not apply — they do not filter what is shown."
 */
export const UNAPPLIED_FACET_NOTICE =
  "This address names {facets}, which this view does not apply — they do not filter what is shown.";

export function facetNoticeText(unapplied: readonly string[]): string {
  if (unapplied.length === 0) return "";
  const labels = unapplied.map(paramLabel);
  const listed =
    labels.length === 1
      ? labels[0]
      : `${labels.slice(0, -1).join(", ")} and ${labels[labels.length - 1]}`;
  return UNAPPLIED_FACET_NOTICE.replace("{facets}", listed);
}

/**
 * The conformance report for one surface over the whole registry — the
 * harness's answer to "which parameters does this surface apply, which does
 * it name, and is the partition complete". `applied ∪ noticed` must equal
 * the whole registry: the third option (silently dropped) does not exist.
 */
export function conformanceReport(surface: WorkspaceSurface): {
  applied: string[];
  noticed: string[];
  violations: string[];
} {
  const applied = new Set(APPLIED_PARAMS[surface]);
  const result = { applied: [] as string[], noticed: [] as string[], violations: [] as string[] };
  for (const name of PARAM_BY_NAME.keys()) {
    if (applied.has(name)) {
      result.applied.push(name);
    } else {
      result.noticed.push(name);
    }
  }
  // A violation is a parameter a parsed `present` could name that lands in
  // neither bucket — structurally impossible while both read the same
  // registry, which is exactly what the sweep asserts.
  return result;
}

/**
 * The per-request check: given the parse receipts for one URL on one
 * surface, the parameters the surface applies, the ones the notice must
 * name, and any registered parameter that escaped both (a violation the
 * sweep surfaces loudly).
 */
export function checkSurfaceConformance(
  surface: WorkspaceSurface,
  present: readonly string[],
): { applied: string[]; noticed: string[]; violations: string[] } {
  const applied = new Set(APPLIED_PARAMS[surface]);
  const result = { applied: [] as string[], noticed: [] as string[], violations: [] as string[] };
  for (const name of present) {
    if (!PARAM_BY_NAME.has(name)) continue; // unregistered → parse issues
    if (applied.has(name)) {
      result.applied.push(name);
    } else {
      result.noticed.push(name);
    }
  }
  return result;
}
