// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.17 (K13 UXK14-4 / K14 §3.4–3.5, C-01…C-04) — the shared lexicon accessors.
 *
 * `lexicon.json` is the ONE machine-readable vocabulary every surface reads
 * (SIG-UI-143: one epistemic word, one meaning; SIG-UI-133: one symbol, one
 * meaning). This module gives it a typed, fail-closed API:
 *
 *   - `lexiconState(field, id)` / `stateLabel(field, id)` — display text for a
 *     stored enum value. The enum values are never rewritten; only their
 *     labels come from here (K14 §3.4: "the short labels change display text
 *     only").
 *   - `symbolIndex()` — every declared symbol grouped by its glyph/pattern
 *     string, so tests can prove one meaning per symbol.
 *   - `specGlossaryTerms()` — the canonical spec's Appendix E rows, parsed
 *     verbatim at build time (the spec is read, never copied by hand).
 *   - `glossaryEntries()` — the merged glossary model: Appendix E terms
 *     verbatim + site terms + the epistemic-state glosses.
 *   - `glossaryTerm(id)` — one entry or a build-time throw. A `<Term>` that
 *     names an undefined term fails the build; a term is never silently
 *     dropped (SIG-ENG-042).
 *
 * The Python figure kit (P36.27/28) and any non-TS consumer read
 * `lexicon.json` itself — plain JSON is the cross-language contract; this
 * module is only the TypeScript binding plus the spec-E merge.
 */

import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import lexicon from "./lexicon.json";

export const LEXICON_SCHEMA = "sig.lexicon/1";
export const LEXICON = lexicon;

if (lexicon.schema !== LEXICON_SCHEMA) {
  throw new Error(`lexicon.json schema drift: got ${lexicon.schema}, want ${LEXICON_SCHEMA}`);
}

// --- States ---------------------------------------------------------------

export type StateField = keyof typeof lexicon.states;

export interface LexiconState {
  label: string;
  plain: string;
  symbol?: string;
  symbolMeaning?: string;
  spec?: string;
  merged?: boolean;
  token?: string;
  colourMeaning?: string;
}

/** All enum ids declared under one state field. */
export function stateIds(field: StateField): string[] {
  return Object.keys(lexicon.states[field]);
}

/**
 * The display entry for one enum value. Fails closed: a stored enum the
 * lexicon does not cover is a build-time error, never a silent fallback —
 * an unlabelled state would otherwise leak a raw enum into prose (SIG-UI-143).
 */
export function lexiconState(field: StateField, id: string): LexiconState {
  const states = lexicon.states[field] as Record<string, LexiconState>;
  const state = states[id];
  if (!state) {
    throw new Error(`lexicon has no ${String(field)} state ${id}`);
  }
  return state;
}

/** The short display label for one enum value (≤ 2 words by K14 §3.4). */
export function stateLabel(field: StateField, id: string): string {
  return lexiconState(field, id).label;
}

// --- One meaning per symbol (SIG-UI-133) ----------------------------------

export interface SymbolUse {
  /** Where the symbol is declared, e.g. "agreement.CONTESTED" or "legend.fill.corroborated". */
  at: string;
  /** The declared meaning family this symbol may ONLY ever carry. */
  symbolMeaning: string;
}

/**
 * Every declared symbol string → the places it is used and the single meaning
 * family it carries. Two uses may share a glyph ONLY when they declare the
 * same `symbolMeaning` (e.g. CONTESTED and IRRECONCILABLE both mark "contested
 * or unresolved value" — the same meaning); a glyph reused across two meaning
 * families is the C-01 collision class and fails the lexicon checks.
 */
export function symbolIndex(): Map<string, SymbolUse[]> {
  const index = new Map<string, SymbolUse[]>();
  for (const [field, states] of Object.entries(lexicon.states)) {
    for (const [id, state] of Object.entries(states as Record<string, LexiconState>)) {
      if (state.symbol) {
        const uses = index.get(state.symbol) ?? [];
        uses.push({
          at: `${field}.${id}`,
          symbolMeaning: state.symbolMeaning ?? `${field}.${id}`,
        });
        index.set(state.symbol, uses);
      }
    }
  }
  for (const [channel, enc] of Object.entries(lexicon.legend)) {
    if (!enc || typeof enc !== "object" || !("encodings" in enc)) continue;
    for (const [name, e] of Object.entries(
      (enc as { encodings: Record<string, { symbol?: string; symbolMeaning?: string }> }).encodings,
    )) {
      if (e.symbol) {
        const uses = index.get(e.symbol) ?? [];
        uses.push({
          at: `legend.${channel}.${name}`,
          symbolMeaning: e.symbolMeaning ?? `legend ${channel}`,
        });
        index.set(e.symbol, uses);
      }
    }
  }
  return index;
}

/** Symbol uses that collide on meaning — the test asserts this is empty. */
export function symbolMeaningConflicts(): { symbol: string; uses: SymbolUse[] }[] {
  return [...symbolIndex().entries()]
    .map(([symbol, uses]) => ({ symbol, uses }))
    .filter(({ uses }) => new Set(uses.map((u) => u.symbolMeaning)).size > 1);
}

// --- The canonical spec's Appendix E (read verbatim, never copied) --------

// The spec is read at build time. `import.meta.url` inside the bundled
// prerender chunk no longer sits at `src/lib/`, so walk up to the repo root
// (the same `uv.lock` probe figures.ts uses) — works from source, the build
// bundle, and vitest alike.
function repoRoot(): string {
  let dir = fileURLToPath(new URL(".", import.meta.url));
  for (;;) {
    if (existsSync(join(dir, "uv.lock"))) return dir;
    const parent = dirname(dir);
    if (parent === dir) {
      throw new Error(`repoRoot: walked above ${dir} without finding uv.lock`);
    }
    dir = parent;
  }
}

const SPEC_PATH = join(repoRoot(), "docs", "2_canonical_design_spec.md");

export interface SpecGlossaryTerm {
  /** The term as Appendix E prints it, e.g. "Weight (`W`)". */
  term: string;
  /** The definition, verbatim. */
  definition: string;
}

let _specTerms: SpecGlossaryTerm[] | null = null;

/**
 * The Appendix E glossary rows of the canonical spec, parsed at build time.
 * The spec is the authority for precise definitions (K14 §2.5: "precise
 * definition — verbatim where the spec supplies one"); this reader exists so
 * the definitions can never drift from the spec by hand-copying. Reading the
 * spec is safe in every build mode — it is a committed repo file, the same
 * pattern `figures.ts` uses.
 */
export function specGlossaryTerms(): SpecGlossaryTerm[] {
  if (_specTerms) return _specTerms;
  const text = readFileSync(SPEC_PATH, "utf8");
  const start = text.indexOf("# Appendix E — Glossary");
  if (start < 0) {
    throw new Error("Appendix E heading not found in the canonical spec");
  }
  const section = text.slice(start);
  const end = section.indexOf("\n# Appendix F");
  const body = end > 0 ? section.slice(0, end) : section;
  const terms: SpecGlossaryTerm[] = [];
  for (const line of body.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed.startsWith("|") || trimmed.startsWith("|-") || trimmed.startsWith("| ---")) continue;
    const cells = trimmed.split("|").slice(1, -1).map((c) => c.trim());
    if (cells.length < 2) continue;
    const m = /^\*\*(.+)\*\*$/.exec(cells[0]!);
    if (!m || m[1] === "Term") continue;
    terms.push({ term: m[1]!, definition: cells[1]! });
  }
  if (terms.length < 20) {
    // Appendix E has ~30 rows; a small parse means the format drifted and the
    // glossary would silently lose spec terms — fail loud (SIG-ENG-042).
    throw new Error(`Appendix E parse found only ${terms.length} terms — spec format drift?`);
  }
  _specTerms = terms;
  return terms;
}

// --- The merged glossary ---------------------------------------------------

export interface GlossaryEntry {
  /** The kebab id — also the `/glossary/` fragment anchor. */
  id: string;
  anchor: string;
  /** The term as displayed. */
  term: string;
  /** Plain definition (K14: ≤ ~25 words, the reader-facing layer). */
  plain: string;
  /** The verbatim spec definition where Appendix E supplies one. */
  precise?: string;
  example?: string;
  /** Ids of other glossary entries. */
  seeAlso: string[];
  /** The spec section reference, shown only inside a Spec references disclosure. */
  spec?: string;
  /** "spec" = Appendix E row; "lexicon" = site term; "merged" = both. */
  source: "spec" | "lexicon" | "merged";
  /** The lexicon state this entry glosses, where one applies. */
  stateRef?: string;
}

function slugify(name: string): string {
  return name
    .replace(/[`*]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

/** Normalize a term name for collision detection (case + punctuation ignored). */
function normalizeTerm(name: string): string {
  return slugify(name);
}

let _glossary: Map<string, GlossaryEntry> | null = null;

/**
 * The merged glossary. Three sources per K14 §2.5: the canonical spec's
 * Appendix E (verbatim precise definitions), the lexicon's `terms` (site
 * terms + plain definitions), and the epistemic states they gloss.
 *
 * Merge rules (K14: the glossary "fails on collision rather than rewriting
 * the spec's term"):
 *   - a lexicon term may absorb one Appendix E row by naming it in `specTerm`;
 *     the absorbed definition is carried verbatim as `precise`;
 *   - an Appendix E term that normalizes onto a lexicon term WITHOUT a
 *     declared `specTerm` merge is a collision and throws — the spec's term is
 *     never silently shadowed;
 *   - duplicate ids, anchors and unresolved seeAlso/stateRef/specTerm
 *     references all throw at build time.
 */
export function glossaryEntries(): GlossaryEntry[] {
  if (_glossary) return [..._glossary.values()];
  const specTerms = specGlossaryTerms();
  const byNormalizedSpec = new Map(specTerms.map((t) => [normalizeTerm(t.term), t]));
  const absorbed = new Set<string>();
  const entries: GlossaryEntry[] = [];

  interface LexiconTerm {
    id: string;
    term: string;
    plain: string;
    specTerm?: string;
    stateRef?: string;
    example?: string;
    seeAlso?: string[];
    spec?: string;
  }
  for (const t of lexicon.terms as LexiconTerm[]) {
    const entry: GlossaryEntry = {
      id: t.id,
      anchor: t.id,
      term: t.term,
      plain: t.plain,
      example: t.example,
      seeAlso: [...(t.seeAlso ?? [])],
      spec: t.spec,
      source: "lexicon",
      stateRef: t.stateRef,
    };
    if (t.specTerm) {
      const spec = byNormalizedSpec.get(normalizeTerm(t.specTerm));
      if (!spec) {
        throw new Error(`lexicon term ${t.id}: specTerm "${t.specTerm}" is not in Appendix E`);
      }
      if (absorbed.has(spec.term)) {
        throw new Error(`Appendix E term "${spec.term}" absorbed twice`);
      }
      absorbed.add(spec.term);
      entry.precise = spec.definition;
      entry.source = "merged";
    }
    entries.push(entry);
  }

  // Spec terms no site term claimed stand alone — verbatim, flagged as spec.
  for (const spec of specTerms) {
    if (absorbed.has(spec.term)) continue;
    const id = slugify(spec.term);
    const normalized = normalizeTerm(spec.term);
    const claimed = entries.find((e) => normalizeTerm(e.term) === normalized || e.id === id);
    if (claimed) {
      throw new Error(
        `Appendix E term "${spec.term}" collides with lexicon term "${claimed.id}" — ` +
          `declare specTerm to merge it; the spec's term is never silently shadowed`,
      );
    }
    entries.push({
      id,
      anchor: id,
      term: spec.term,
      plain: spec.definition, // no plainer text exists yet; the spec row stands
      precise: spec.definition,
      seeAlso: [],
      spec: "Appendix E",
      source: "spec",
    });
  }

  const map = new Map<string, GlossaryEntry>();
  for (const e of entries) {
    if (map.has(e.id)) throw new Error(`duplicate glossary id ${e.id}`);
    map.set(e.id, e);
  }
  // Reference resolution: every seeAlso and stateRef must resolve (SIG-ENG-042).
  for (const e of entries) {
    for (const ref of e.seeAlso) {
      if (!map.has(ref)) {
        throw new Error(`glossary entry ${e.id}: seeAlso "${ref}" is not a glossary term`);
      }
    }
    if (e.stateRef) {
      const [field, id] = e.stateRef.split(".");
      lexiconState(field as StateField, id!); // throws on miss
    }
  }
  _glossary = map;
  return entries;
}

/**
 * One glossary entry by id — the lookup `<Term>` performs. A term used before
 * it is defined is a build-time error, never a silent no-render (SIG-ENG-042).
 */
export function glossaryTerm(id: string): GlossaryEntry {
  if (!_glossary) glossaryEntries();
  const entry = _glossary!.get(id);
  if (!entry) {
    throw new Error(`<Term term="${id}"> names no glossary entry — define it in lexicon.json terms[]`);
  }
  return entry;
}

// --- The legend (C-01…C-04) -------------------------------------------------

/**
 * A `state` reference inside the legend, e.g. "access.CONFIGURED_ACCESS" →
 * the resolved lexicon state. Used by the glossary's legend section so the
 * encodings print their labels from the same state table as everything else.
 */
export function legendState(ref: string): LexiconState {
  const [field, id] = ref.split(".");
  return lexiconState(field as StateField, id!);
}

// --- Controlled vocabulary (K14 §3.5 / CP-10: one word per concept) --------

export interface VocabularyRow {
  concept: string;
  use: string;
  also?: string;
  not?: string[];
}

export const CONTROLLED_VOCABULARY: VocabularyRow[] = lexicon.vocabulary;
