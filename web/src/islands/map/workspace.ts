// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.37 — the Preact-side adapter for `sig.workspace-state/2` on the `/map/`
 * surface (the React twin `islands/workspace.ts` keeps serving the not-yet-
 * migrated islands). Same contract: parse `location.search` at mount, mirror
 * committed state into `history` so Back/Forward restore it (SIG-UI-093),
 * and surface the parse receipts + unapplied-parameter names (SIG-UI-060).
 * SSR-safe: on the server it returns the seeded default so the `client:idle`
 * first paint renders the shell skeleton.
 */

import { useCallback, useEffect, useState } from "preact/hooks";
import {
  ISLAND_SURFACE,
  parseWorkspaceState2,
  SURFACE_VIEW,
  toIslandState,
  unappliedParams,
  VIEW_SURFACE,
  workspaceHref2,
} from "../../lib/workspace-state/index";
import type { IslandView, IslandWorkspaceState } from "../../lib/workspace-state/index";

export interface WorkspaceRuntime {
  state: IslandWorkspaceState;
  issues: string[];
  ignored: readonly string[];
  update: (patch: Partial<IslandWorkspaceState>, mode?: "push" | "replace") => void;
}

const isBrowser = typeof window !== "undefined";

export function useMapWorkspace(
  view: IslandView,
  defaults: { release?: string | null } = {},
): WorkspaceRuntime {
  const seed = () => ({
    release: defaults.release ?? null,
    view: SURFACE_VIEW[ISLAND_SURFACE[view]],
  });
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
    if (!isBrowser) {
      // SSR: parse an empty query — the full registered defaults, never a stub.
      const parsed = parseWorkspaceState2("?", seed());
      return {
        state: toIslandState(parsed.state, view),
        issues: [] as string[],
        ignored: [] as string[],
      };
    }
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
