// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The React-side adapter for `sig.workspace-state/1` (P32.15, SIG-FIND-004).
 * The pure contract lives in `../lib/workspace-state`; this hook is the ONLY
 * DOM/history aware piece — it parses `location.search` at mount (deep links
 * and reloads), mirrors committed state into `history` so back/forward restore
 * it, and surfaces the parse `issues` the contract requires to be visible.
 *
 * Islands are `client:only="react"`, so `window` is always present here.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import {
  parseWorkspaceState,
  workspaceHref,
} from "../lib/workspace-state";
import type { WorkspaceState, WorkspaceView } from "../lib/workspace-state";

export interface WorkspaceRuntime {
  state: WorkspaceState;
  /** Visible-failure notes from the last parse (unknown versions/values). */
  issues: string[];
  /** Merge a patch and record it: `push` for a navigation the Back button can
   *  undo, `replace` for refining the current entry (e.g. live query text). */
  update: (patch: Partial<WorkspaceState>, mode?: "push" | "replace") => void;
}

export function useWorkspaceState(
  view: WorkspaceView,
  defaults: { release?: string | null } = {},
): WorkspaceRuntime {
  const read = () => {
    const parsed = parseWorkspaceState(window.location.search, {
      release: defaults.release ?? null,
      view,
    });
    // The path decides the rendered view; a differing `view=` value is visible
    // via issues on first parse, then the page's own view stands.
    return { parsed, state: { ...parsed.state, view } };
  };

  const [{ state, issues }, setCurrent] = useState(() => {
    const r = read();
    return { state: r.state, issues: r.parsed.issues };
  });
  const defaultsRef = useRef(defaults);
  defaultsRef.current = defaults;

  useEffect(() => {
    const onPop = () => {
      const parsed = parseWorkspaceState(window.location.search, {
        release: defaultsRef.current.release ?? null,
        view,
      });
      setCurrent({ state: { ...parsed.state, view }, issues: parsed.issues });
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, [view]);

  const update = useCallback(
    (patch: Partial<WorkspaceState>, mode: "push" | "replace" = "push") => {
      setCurrent((current) => {
        const merged = { ...current.state, ...patch, view };
        const href = workspaceHref(window.location.pathname, merged);
        if (mode === "push") window.history.pushState(null, "", href);
        else window.history.replaceState(null, "", href);
        return { ...current, state: merged };
      });
    },
    [view],
  );

  return { state, issues, update };
}
