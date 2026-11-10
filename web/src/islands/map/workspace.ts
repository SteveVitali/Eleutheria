// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.37 — the Preact-side adapter for `sig.workspace-state/2` on the `/map/`
 * surface. P37.26 (ADR-242): the React twin `islands/workspace.ts` retired
 * with the /network/ island — this adapter now serves `/map/`, `/explore/`
 * and `/search/`. Same contract: parse `location.search` at mount, mirror
 * committed state into `history` so Back/Forward restore it (SIG-UI-093),
 * and surface the parse receipts + unapplied-parameter names (SIG-UI-060).
 * SSR-safe: on the server it returns the seeded default so the `client:idle`
 * first paint renders the shell skeleton.
 */

import { useCallback, useEffect, useState } from "preact/hooks";
import {
  canonicaliseWorkspaceState,
  ISLAND_SURFACE,
  parseWorkspaceState2,
  SURFACE_VIEW,
  toIslandState,
  unappliedParams,
  VIEW_SURFACE,
  workspaceHref2,
} from "../../lib/workspace-state/index";
import type { IslandView, IslandWorkspaceState, Viewport, WorkspaceState2 } from "../../lib/workspace-state/index";

export interface WorkspaceRuntime {
  state: IslandWorkspaceState;
  issues: string[];
  ignored: readonly string[];
  update: (patch: Partial<IslandWorkspaceState>, mode?: "push" | "replace") => void;
}

const isBrowser = typeof window !== "undefined";

export function useMapWorkspace(
  view: IslandView,
  defaults: { release?: string | null; seed?: Partial<WorkspaceState2> } = {},
  opts: {
    frameBounds?: (jkey: string) => Viewport | null;
    /**
     * P37.29 (VIZ-04, K6 V-10 / SIG-UI-127): `url: false` is the EMBEDDED
     * mode — the dossier mounts the app in place and the address bar belongs
     * to the dossier, so the adapter never reads `location.search` (a
     * dossier URL carries no workspace params), never writes history (no
     * pushState/replaceState, no popstate listener), and seeds the state
     * from `defaults.seed` (the dossier's jurisdiction) instead. "Open full
     * map" carries the state to `/map/`; the embed itself mints nothing.
     */
    url?: boolean;
  } = {},
): WorkspaceRuntime {
  const url = opts.url !== false;
  const seed = () => ({
    release: defaults.release ?? null,
    view: SURFACE_VIEW[ISLAND_SURFACE[view]],
    ...(defaults.seed ?? {}),
  });
  const viewMismatch = (named: string) =>
    `The address names the "${named}" view; this page is ${ISLAND_SURFACE[view]} — it does not apply here.`;
  // P37.19 (MAP-04): the `frame=<jkey>` fold — the map row owns the
  // jkey→bounds table `canonicaliseWorkspaceState` deferred to; a resolved
  // frame lands as `at=` with the receipt in `notes` (never re-emitted).
  const fold = (s: ReturnType<typeof parseWorkspaceState2>) => {
    const folded = canonicaliseWorkspaceState(s.state, { frameBounds: opts.frameBounds });
    return { ...s, state: folded.state, notes: [...s.notes, ...folded.notes] };
  };
  const read = () => {
    const parsed = fold(parseWorkspaceState2(window.location.search, seed()));
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
    if (!isBrowser || !url) {
      // SSR — or the embedded mount, which seeds entirely from props: no
      // location read, so a dossier URL's own parameters can never surface
      // as unapplied-workspace receipts.
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
    if (!url) return; // embedded: the dossier owns the address bar — no popstate
    const onPop = () => {
      const parsed = fold(parseWorkspaceState2(window.location.search, seed()));
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
  }, [view, url]);

  const update = useCallback(
    (patch: Partial<IslandWorkspaceState>, mode: "push" | "replace" = "push") => {
      setCurrent((current) => {
        const merged = { ...current.state, ...patch, view };
        if (url) {
          const href = workspaceHref2(merged, window.location.pathname);
          if (mode === "push") window.history.pushState(null, "", href);
          else window.history.replaceState(null, "", href);
        }
        return { ...current, state: merged };
      });
    },
    [view, url],
  );

  return { state, issues, ignored, update };
}
