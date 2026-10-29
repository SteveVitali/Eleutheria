// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The React-side adapter for `sig.workspace-state/2` (P36.21; P32.15's
 * `sig.workspace-state/1` role carried forward). The pure contract lives in
 * `../lib/workspace-state/` (registry + state + conformance); this hook is
 * the ONLY DOM/history aware piece — it parses `location.search` at mount
 * (deep links and reloads), mirrors committed state into `history` so
 * Back/Forward restore it (SIG-UI-093), and surfaces the parse receipts the
 * contract requires to be visible:
 *
 * - `issues` — every parse receipt a reader must see: failures
 *   (unrecognised version, unusable values, a `view=` naming a different
 *   surface, REFUSED unregistered parameters) AND the canonicalisation
 *   receipts (`bbox` → `at=`, `kind=site` → `type=record`, legacy `US-OK`
 *   jurisdiction codes, `view=network` → `graph`). No rewrite is ever
 *   silent — both kinds render in the same `workspace-issues` element.
 * - `ignored` — the registered parameters this surface parsed but does not
 *   apply (SIG-UI-060): the island MUST announce them visibly — an ignored
 *   facet never passes for a filter that held.
 *
 * `v=1` URLs keep resolving: the parser switches to the v1 value semantics
 * for the v1 parameter set, and links the island mints from here are `v=2`.
 * Islands are `client:only="react"`, so `window` is always present here.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ISLAND_SURFACE,
  parseWorkspaceState2,
  SURFACE_VIEW,
  toIslandState,
  unappliedParams,
  VIEW_SURFACE,
  workspaceHref2,
} from "../lib/workspace-state/index";
import type { IslandView, IslandWorkspaceState } from "../lib/workspace-state/index";

export interface WorkspaceRuntime {
  state: IslandWorkspaceState;
  /**
   * Every visible parse receipt — failures plus the canonicalisation
   * receipts (`notes`), folded together because both kinds must render.
   */
  issues: string[];
  /**
   * The registered parameters the address names but this surface does NOT
   * apply (SIG-UI-060; P34.15's island-honesty rule): the island MUST
   * announce them visibly — an ignored facet never passes for a filter
   * that held.
   */
  ignored: readonly string[];
  /** Merge a patch and record it: `push` for a navigation the Back button can
   *  undo, `replace` for refining the current entry (e.g. live query text). */
  update: (patch: Partial<IslandWorkspaceState>, mode?: "push" | "replace") => void;
}

export function useWorkspaceState(
  view: IslandView,
  defaults: { release?: string | null } = {},
): WorkspaceRuntime {
  const defaultsRef = useRef(defaults);
  defaultsRef.current = defaults;
  // An absent `view=` means "this surface" — the parse seeds the surface's
  // own canonical view value, so only an explicit view naming a DIFFERENT
  // surface produces the mismatch receipt.
  const seed = () => ({
    release: defaultsRef.current.release ?? null,
    view: SURFACE_VIEW[ISLAND_SURFACE[view]],
  });
  // The path decides the rendered view (SIG-UI-059); a `view=` that
  // resolves to a different surface is a visible receipt, then the page's
  // own view stands.
  const viewMismatch = (named: string) =>
    `The address names the "${named}" view; this page is ${ISLAND_SURFACE[view]} — it does not apply here.`;
  const read = () => {
    const parsed = parseWorkspaceState2(window.location.search, seed());
    const issues = [...parsed.issues, ...parsed.notes];
    if (VIEW_SURFACE[parsed.state.view] !== ISLAND_SURFACE[view]) {
      issues.push(viewMismatch(parsed.state.view));
    }
    return {
      parsed: { ...parsed, issues },
      state: toIslandState(parsed.state, view),
    };
  };

  const [{ state, issues, ignored }, setCurrent] = useState(() => {
    const r = read();
    return {
      state: r.state,
      issues: r.parsed.issues,
      ignored: unappliedParams(r.parsed.present, ISLAND_SURFACE[view]),
    };
  });

  useEffect(() => {
    const onPop = () => {
      const parsed = parseWorkspaceState2(window.location.search, seed());
      const issues = [...parsed.issues, ...parsed.notes];
      if (VIEW_SURFACE[parsed.state.view] !== ISLAND_SURFACE[view]) {
        issues.push(viewMismatch(parsed.state.view));
      }
      setCurrent({
        state: toIslandState(parsed.state, view),
        issues,
        ignored: unappliedParams(parsed.present, ISLAND_SURFACE[view]),
      });
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, [view]);

  const update = useCallback(
    (patch: Partial<IslandWorkspaceState>, mode: "push" | "replace" = "push") => {
      setCurrent((current) => {
        const merged = { ...current.state, ...patch, view };
        const href = workspaceHref2(merged, window.location.pathname);
        if (mode === "push") window.history.pushState(null, "", href);
        else window.history.replaceState(null, "", href);
        return { ...current, state: merged };
      });
    },
    [view],
  );

  return { state, issues, ignored, update };
}
