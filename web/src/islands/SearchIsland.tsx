// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The client-side search / filter island (P27.9, DECISION-SPA = B, ADR-097;
 * P32.15 shared workspace state, SIG-FIND-004, ADR-134).
 *
 * PROGRESSIVE ENHANCEMENT, NOT REPLACEMENT (SIG-UI-050): this island hydrates ONLY
 * on `/search/`; the released-corpus GET forms and the static browse index
 * (SIG-FIND-003, ADR-133 — the verified per-compartment FTS5 index, never a
 * current-only Postgres fallback) are the no-JS / screen-reader path
 * (SIG-UI-037) and are never removed. This island filters the listed index in
 * the browser — a convenience, never the corpus (SIG-UI-040).
 *
 * Shared URL state (`sig.workspace-state/1`): `q`, the `kind` facet, `focus`,
 * `release`, `collection` and the view links all live in the query string, so a
 * deep link, a reload or Back/Forward restores the same investigation state and
 * the List/Map/Connections links carry it whole. Query/filter changes reset
 * pagination and keep the focused record ONLY while it remains in scope —
 * a cleared selection is announced, never silently lost.
 *
 * Accessibility (WCAG 2.2 AA): a labelled text input, an `aria-live` result
 * count + cleared-selection announcements, real checkboxes, and results as
 * native links (keyboard-operable, no custom widget). Typing refines the
 * current history entry (`replaceState`); selecting a record is a real
 * navigation (`pushState`) Back can undo.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactElement } from "react";
import {
  clearFocusOutOfScope,
  facetNoticeText,
  recordRoutes,
  viewHref,
  WORKSPACE_VIEWS,
} from "../lib/workspace-state";
import { useWorkspaceState } from "./workspace";

export type SearchKind = "dossier" | "site" | "source";

export interface SearchItem {
  kind: SearchKind;
  label: string;
  sublabel: string;
  href: string;
  /** The id this item puts in `focus=` when selected — a record_key where one
   *  exists (released sites), else the island's own node/asset id. */
  focusId?: string;
}

export interface SearchIslandProps {
  items: SearchItem[];
  /** The latest activated publication id for this build, or null (none). */
  release: string | null;
}

const GROUPS: { kind: SearchKind; heading: string }[] = [
  { kind: "dossier", heading: "Dossiers" },
  { kind: "site", heading: "Map sites" },
  { kind: "source", heading: "Sources" },
];

const VIEW_LABELS: Record<string, string> = {
  list: "List",
  map: "Map",
  network: "Connections",
};

export default function SearchIsland({ items, release }: SearchIslandProps): ReactElement {
  const { state, issues, ignored, update } = useWorkspaceState("list", { release });
  // The text field mirrors state.q (deep links, Back/Forward) but stays a
  // controlled local input while typing; committed to the URL on change via
  // `replace` so keystrokes do not flood history.
  const [draft, setDraft] = useState(state.q);
  useEffect(() => setDraft(state.q), [state.q]);
  const [notice, setNotice] = useState<string | null>(null);

  const activeKinds = useMemo(
    () => new Set(state.kind.length ? state.kind : GROUPS.map((g) => g.kind)),
    [state.kind],
  );

  const matches = useMemo(() => {
    const needle = draft.trim().toLowerCase();
    const byFacet = items.filter((it) => activeKinds.has(it.kind));
    if (needle === "") return byFacet;
    return byFacet.filter(
      (it) =>
        it.label.toLowerCase().includes(needle) || it.sublabel.toLowerCase().includes(needle),
    );
  }, [draft, items, activeKinds]);

  // The focus-scope rule (S4 §7): a selected record survives a query/filter
  // change only while it remains in scope; otherwise the selection clears and
  // the reader is TOLD (aria-live), it is never silently lost.
  const focusVisible = state.focus !== null && matches.some((m) => m.focusId === state.focus);
  useEffect(() => {
    if (state.focus === null || focusVisible) return;
    const { cleared } = clearFocusOutOfScope(state, (f) =>
      matches.some((m) => m.focusId === f),
    );
    if (cleared) {
      setNotice("Selection cleared — the focused record is outside the current query.");
      update({ focus: null }, "replace");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft, state.kind.join(","), state.focus]);

  const focusedItem = useMemo(
    () => (state.focus ? matches.find((m) => m.focusId === state.focus) : undefined),
    [matches, state.focus],
  );
  const focusedRoutes = useMemo(() => {
    const rel = state.release ?? release;
    return rel && state.focus ? recordRoutes(rel, state.focus) : null;
  }, [state.release, state.focus, release]);

  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const commitQuery = (value: string) => {
    if (debounce.current) clearTimeout(debounce.current);
    debounce.current = setTimeout(() => update({ q: value }, "replace"), 250);
  };

  const toggleKind = (kind: SearchKind) => {
    const next = new Set(activeKinds);
    if (next.has(kind)) next.delete(kind);
    else next.add(kind);
    // An empty selection reads as "all" — the canonical empty-facet default.
    update({ kind: next.size === GROUPS.length ? [] : [...next] });
  };

  return (
    <div className="sig-search-island" data-testid="search-island">
      <nav className="sig-view-links" aria-label="Investigation views" data-testid="island-view-links">
        {WORKSPACE_VIEWS.map((v) =>
          v === state.view ? (
            <strong key={v} aria-current="page">{VIEW_LABELS[v]}</strong>
          ) : (
            <a key={v} href={viewHref(state, v)} data-testid={`view-link-${v}`}>
              {VIEW_LABELS[v]}
            </a>
          ),
        )}
      </nav>
      {state.release && (
        <p className="sig-island__note" data-testid="workspace-release">
          Release <code>{state.release}</code>
        </p>
      )}
      {issues.length > 0 && (
        <p className="sig-island__note" role="status" data-testid="workspace-issues">
          {issues.join(" ")}
        </p>
      )}
      {ignored.length > 0 && (
        <p className="sig-island__note" role="status" data-testid="facet-not-applied">
          {facetNoticeText(ignored)}
        </p>
      )}

      <label htmlFor="sig-search-input">
        <strong>Filter the listed index</strong> — dossiers, listed sites and sources
      </label>
      <br />
      <input
        id="sig-search-input"
        className="sig-search-island__input"
        type="search"
        autoComplete="off"
        placeholder="Type to filter (e.g. a jurisdiction, an agency, a source)…"
        value={draft}
        data-testid="search-input"
        onChange={(e) => {
          setDraft(e.target.value);
          setNotice(null);
          commitQuery(e.target.value);
        }}
      />
      <fieldset className="sig-search-island__facets" data-testid="search-kind-facets">
        <legend>Record type</legend>
        {GROUPS.map((g) => (
          <label key={g.kind}>
            <input
              type="checkbox"
              checked={activeKinds.has(g.kind)}
              onChange={() => toggleKind(g.kind)}
            />{" "}
            {g.heading}
          </label>
        ))}
      </fieldset>
      <p className="sig-search-island__status" role="status" aria-live="polite" data-testid="search-status">
        {matches.length} result{matches.length === 1 ? "" : "s"}
        {draft.trim() !== "" ? ` for “${draft.trim()}”` : ""}.
        {notice ? ` ${notice}` : ""}
      </p>

      {state.focus && (
        <section className="sig-search-island__focus" data-testid="search-focus-pane" aria-label="Selected record">
          <h3>Selected record</h3>
          {focusedItem ? (
            <>
              <p>
                <strong>{focusedItem.label}</strong>{" "}
                <span className="sig-search-island__kind">{focusedItem.sublabel}</span>
              </p>
              <p>
                <a href={focusedItem.href} data-testid="focus-record-link">Open this record</a>
              </p>
            </>
          ) : (
            <p>
              <code>{state.focus}</code> — not in the filtered list.{" "}
              {focusedRoutes ? (
                <a href={focusedRoutes.pageHref} data-testid="focus-record-link">
                  Open the released record
                </a>
              ) : (
                "The released-record page is linked where a release pins it."
              )}
            </p>
          )}
          <p>
            <a href={viewHref({ ...state }, "map")} data-testid="focus-map-link">View on map</a>
            {" · "}
            <a href={viewHref({ ...state }, "network")} data-testid="focus-network-link">
              Connections
            </a>
            {" · "}
            <button type="button" onClick={() => update({ focus: null })}>
              Clear selection
            </button>
          </p>
        </section>
      )}

      {GROUPS.filter((g) => activeKinds.has(g.kind)).map((g) => {
        const groupMatches = matches.filter((m) => m.kind === g.kind);
        if (groupMatches.length === 0) return null;
        return (
          <section
            className="sig-search-island__group"
            key={g.kind}
            data-testid={`search-group-${g.kind}`}
          >
            <h3>
              {g.heading} <span className="sig-search-island__kind">({groupMatches.length})</span>
            </h3>
            <ul className="sig-search-island__results">
              {groupMatches.slice(0, 100).map((m) => (
                <li key={`${m.kind}:${m.href}:${m.label}`} data-testid="search-result">
                  <a href={m.href}>{m.label}</a>
                  <span className="sig-search-island__kind">{m.sublabel}</span>
                  {m.focusId && (
                    <button
                      type="button"
                      className="sig-search-island__focus-btn"
                      data-testid="search-focus-item"
                      aria-pressed={state.focus === m.focusId}
                      onClick={() =>
                        update({ focus: state.focus === m.focusId ? null : m.focusId! })
                      }
                    >
                      {state.focus === m.focusId ? "Selected" : "Select"}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </section>
        );
      })}

      {matches.length === 0 && (
        <p data-testid="search-empty">
          No match in this list. Nothing found here is not evidence of absence — try the
          released-corpus search above, the full browse index below, or the{" "}
          <a href="/research-queue/">research queue</a>.
        </p>
      )}
    </div>
  );
}
