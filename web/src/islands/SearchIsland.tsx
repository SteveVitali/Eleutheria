// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The client-side search / filter island (P27.9, DECISION-SPA = B, ADR-097).
 *
 * PROGRESSIVE ENHANCEMENT, NOT REPLACEMENT (SIG-UI-050): this island hydrates ONLY
 * on `/search/`; the released-corpus GET forms and the static browse index
 * (SIG-FIND-003, ADR-133 — the verified per-compartment FTS5 index, never a
 * current-only Postgres fallback) are the no-JS / screen-reader path
 * (SIG-UI-037) and are never removed. This island filters the listed index in
 * the browser — a convenience, never the corpus (SIG-UI-040).
 *
 * Accessibility (WCAG 2.2 AA): a labelled text input, an `aria-live` result count,
 * and results as native links (keyboard-operable, no custom widget).
 */

import { useMemo, useState } from "react";
import type { ReactElement } from "react";

export type SearchKind = "dossier" | "site" | "source";

export interface SearchItem {
  kind: SearchKind;
  label: string;
  sublabel: string;
  href: string;
}

export interface SearchIslandProps {
  items: SearchItem[];
}

const GROUPS: { kind: SearchKind; heading: string }[] = [
  { kind: "dossier", heading: "Dossiers" },
  { kind: "site", heading: "Map sites" },
  { kind: "source", heading: "Sources" },
];

export default function SearchIsland({ items }: SearchIslandProps): ReactElement {
  const [q, setQ] = useState("");

  const matches = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (needle === "") return items;
    return items.filter(
      (it) =>
        it.label.toLowerCase().includes(needle) || it.sublabel.toLowerCase().includes(needle),
    );
  }, [q, items]);

  return (
    <div className="sig-search-island" data-testid="search-island">
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
        value={q}
        data-testid="search-input"
        onChange={(e) => setQ(e.target.value)}
      />
      <p className="sig-search-island__status" role="status" aria-live="polite" data-testid="search-status">
        {matches.length} result{matches.length === 1 ? "" : "s"}
        {q.trim() !== "" ? ` for “${q.trim()}”` : ""}.
      </p>

      {GROUPS.map((g) => {
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
