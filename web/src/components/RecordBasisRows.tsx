// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.39 (R11-K13-QB-01, L3 §5.2, SIG-CONF-011) — the ONE quality-basis
 * block's row markup, shared by every `sig.provenance-panel/1` emitter
 * (`ProvenancePanel.tsx` and the /map/ island twin `claim-panels.tsx`) so
 * the states render identically on every surface (UXR-33). Zero-JS:
 * a `<dl>` of pp-field rows; entry displays are the export's verbatim L3
 * §5.2 sentences; the copy / possible-duplicate labels are the lexicon
 * `identity` states (SIG-UI-143 — one word, one meaning).
 */
/** @jsxImportSource preact */
import type { JSX } from "preact";
import { basisRows } from "../lib/record-basis";
import { lexiconState } from "../lib/lexicon";
import type { RecordBasis } from "../lib/record-basis";

/** The lexicon `identity` states the basis block names (QB-01's lexicon
 *  deliverable: the words come from `lexicon.json`, never literals). */
export const BASIS_STATE_WORDS = {
  copies: lexiconState("identity", "COPY").label,
  possibleDuplicates: lexiconState("identity", "POSSIBLE_DUPLICATE").label,
} as const;

export function RecordBasisRows({ basis }: { basis: RecordBasis }): JSX.Element {
  return (
    <section className="pp-basis" data-basis="record" aria-label="Quality basis">
      <h3 className="pp-basis-heading">Quality basis</h3>
      <dl>
        {basisRows(basis).map(([label, text, displays]) => (
          <div className="pp-field" data-basis-field={label.toLowerCase().replace(/\s+/g, "-")}>
            <dt>{label}</dt>
            <dd>
              {displays.length > 0
                ? displays.map((d, i) => (
                    <span className="pp-basis-entry">
                      {i > 0 ? " " : null}
                      {d}
                    </span>
                  ))
                : text}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
