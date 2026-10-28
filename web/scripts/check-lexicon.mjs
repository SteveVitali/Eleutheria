// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.17 (K13 UXK14-4 / SIG-UI-061/062/064/133/143) — the lexicon single-source lint.
 *
 * Legs (each fails closed; a vacuous leg is a failure, never a silent green —
 * SIG-ENG-042):
 *
 *   1. schema       — lexicon.json parses, declares sig.lexicon/1, carries the
 *                     four sections (fields, states, legend, vocabulary+terms).
 *   2. enum cover   — every stored enum value declared in epistemic.ts exists
 *                     as a lexicon state, so a stored value can never render
 *                     as a raw enum (SIG-UI-143).
 *   3. symbol       — one meaning per symbol (SIG-UI-133, C-01): a glyph or
 *                     pattern string may carry exactly one meaning family.
 *   4. C-vs-P       — Candidate and Provisional differ in word, symbol and
 *                     filter value (SIG-UI-062).
 *   5. lineage      — the corroborated fill counts INDEPENDENT LINEAGES and
 *                     carries the interim legend line verbatim (SIG-UI-064);
 *                     currency is never a line pattern and never hollow.
 *   6. L3 states    — "copy" and "possible duplicate" exist with their merge
 *                     semantics (possible duplicates stay visible, unmerged).
 *   7. terms        — unique glossary ids/anchors; seeAlso/stateRef/specTerm
 *                     references resolve; an Appendix E term a site term
 *                     shadows without a declared specTerm merge is a
 *                     collision (the spec's term is never rewritten).
 *   8. usage        — every <Term term="…"> names a defined term, at most
 *                     once per file per term (K14's first-mention rule — the
 *                     popover id is the anchor).
 *   9. built html   — when dist/ exists: every sig-term link resolves to a
 *                     /glossary/ anchor; no raw enum token appears in visible
 *                     text outside code/pre/details; no word joined at an
 *                     element boundary (DR-K14-19 shape).
 *  10. chrome       — P36.18 (SIG-UI-145): the shared chrome's visible-by-
 *                     default strings live in lexicon.chrome and render at
 *                     most 40 words; the strip template names its data slots
 *                     ({sources}/{asOf}/{reviewStatus}) so a count or date
 *                     can never be hard-coded into chrome copy.
 *
 * Exit codes: 0 pass · 1 violation · 2 usage/input error · 3 vacuous.
 */

import { readdirSync, readFileSync, existsSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = fileURLToPath(new URL("..", import.meta.url));
const SRC = join(WEB, "src");
const DIST = join(WEB, "dist");
const SPEC = join(WEB, "..", "docs", "2_canonical_design_spec.md");

const failures = [];
const notes = [];
function fail(leg, msg) {
  failures.push(`[${leg}] ${msg}`);
}
function vacuous(leg, msg) {
  fail(leg, `VACUOUS — ${msg} (SIG-ENG-042)`);
}

const lexicon = JSON.parse(readFileSync(join(SRC, "lib", "lexicon.json"), "utf8"));

// --- 1. schema ---------------------------------------------------------------
{
  if (lexicon.schema !== "sig.lexicon/1") fail("schema", `schema ${lexicon.schema} != sig.lexicon/1`);
  for (const key of ["fields", "states", "legend", "vocabulary", "terms"]) {
    if (!lexicon[key]) fail("schema", `missing section ${key}`);
  }
}

// --- 2. enum coverage ---------------------------------------------------------
{
  const epi = readFileSync(join(SRC, "lib", "epistemic.ts"), "utf8");
  const arrays = [...epi.matchAll(/(?:STATUSES|LEVELS|KINDS)\s*=\s*\[([\s\S]*?)\]\s*as const/g)];
  if (arrays.length < 5) vacuous("enum", `found ${arrays.length} enum arrays in epistemic.ts, want >= 5`);
  const declared = new Set();
  for (const states of Object.values(lexicon.states)) {
    for (const id of Object.keys(states)) declared.add(id);
  }
  const values = new Set();
  for (const m of arrays) {
    for (const v of m[1].matchAll(/"([A-Z][A-Z0-9_]+)"/g)) values.add(v[1]);
  }
  for (const v of values) {
    if (!declared.has(v)) fail("enum", `epistemic enum ${v} has no lexicon state`);
  }
  if (values.size === 0) vacuous("enum", "no enum values extracted");
  else notes.push(`enum: ${values.size} stored values covered`);
}

// --- 3. one meaning per symbol -------------------------------------------------
{
  const bySymbol = new Map();
  const add = (symbol, at, meaning) => {
    const list = bySymbol.get(symbol) ?? [];
    list.push({ at, meaning });
    bySymbol.set(symbol, list);
  };
  for (const [field, states] of Object.entries(lexicon.states)) {
    for (const [id, s] of Object.entries(states)) {
      if (s.symbol) add(s.symbol, `${field}.${id}`, s.symbolMeaning ?? `${field}.${id}`);
    }
  }
  for (const [channel, enc] of Object.entries(lexicon.legend)) {
    if (!enc || typeof enc !== "object" || !enc.encodings) continue;
    for (const [name, e] of Object.entries(enc.encodings)) {
      if (e.symbol) add(e.symbol, `legend.${channel}.${name}`, e.symbolMeaning ?? `legend ${channel}`);
    }
  }
  if (bySymbol.size === 0) vacuous("symbol", "no symbols declared");
  for (const [symbol, uses] of bySymbol) {
    const meanings = new Set(uses.map((u) => u.meaning));
    if (meanings.size > 1) {
      fail("symbol", `symbol "${symbol}" carries ${meanings.size} meanings: ${uses.map((u) => u.at).join(", ")}`);
    }
  }
  notes.push(`symbol: ${bySymbol.size} declared symbols, one meaning each`);
}

// --- 4. Candidate vs Provisional ----------------------------------------------
{
  const rows = lexicon.legend?.candidateVsProvisional?.rows ?? [];
  if (rows.length !== 2) fail("C-vs-P", `candidateVsProvisional.rows has ${rows.length} rows, want 2`);
  else {
    const [a, b] = rows;
    for (const key of ["word", "symbol", "filter"]) {
      if (a[key] === b[key]) fail("C-vs-P", `Candidate and Provisional share ${key} "${a[key]}" — they must differ`);
    }
    if (!a.word || !b.word) vacuous("C-vs-P", "rows lack words");
  }
}

// --- 5. independent-lineage corroboration + currency bounds ---------------------
{
  const corr = lexicon.legend?.fill?.encodings?.corroborated;
  if (!corr) fail("lineage", "legend.fill.encodings.corroborated missing");
  else {
    if (corr.countsIndependentLineages !== true) fail("lineage", "corroborated fill does not declare countsIndependentLineages");
    if (corr.interimLegendLine !== "2+ source records; republications not yet collapsed") {
      fail("lineage", `interimLegendLine drifted: "${corr.interimLegendLine}"`);
    }
    if (!corr.plain?.includes("independent")) fail("lineage", "corroborated plain does not say independent lineages");
  }
  const never = lexicon.legend?.currency?.never ?? [];
  for (const want of ["a line pattern", "hollow"]) {
    if (!never.includes(want)) fail("lineage", `legend.currency.never lacks "${want}"`);
  }
}

// --- 6. L3 copy / possible duplicate -------------------------------------------
{
  const copy = lexicon.states?.identity?.COPY;
  const dup = lexicon.states?.identity?.POSSIBLE_DUPLICATE;
  if (!copy) fail("L3", "identity.COPY missing");
  if (!dup) fail("L3", "identity.POSSIBLE_DUPLICATE missing");
  else {
    if (dup.merged !== false) fail("L3", "POSSIBLE_DUPLICATE must declare merged: false — it stays visible, unmerged");
    if (!/not merged/i.test(dup.plain) || !/cannot prove/i.test(dup.plain)) {
      fail("L3", "POSSIBLE_DUPLICATE plain must say it is not merged and that SIG cannot prove identity");
    }
  }
}

// --- 7. glossary terms ----------------------------------------------------------
{
  const specText = readFileSync(SPEC, "utf8");
  const eStart = specText.indexOf("# Appendix E — Glossary");
  if (eStart < 0) fail("terms", "Appendix E not found in the spec");
  const eBody = specText.slice(eStart, specText.indexOf("\n# Appendix F") || undefined);
  const specTerms = new Map();
  for (const m of eBody.matchAll(/\| \*\*(.+?)\*\* \| (.+?) \|/g)) {
    if (m[1] !== "Term") specTerms.set(m[1], m[2]);
  }
  if (specTerms.size < 20) vacuous("terms", `Appendix E parse found ${specTerms.size} terms`);
  const norm = (s) => s.replace(/[`*]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  const normSpec = new Map([...specTerms.keys()].map((t) => [norm(t), t]));

  const ids = new Set();
  const anchors = new Set();
  const absorbed = new Set();
  for (const t of lexicon.terms) {
    if (ids.has(t.id)) fail("terms", `duplicate term id ${t.id}`);
    ids.add(t.id);
    if (!t.plain) fail("terms", `term ${t.id} lacks a plain definition`);
    if (t.specTerm) {
      const spec = normSpec.get(norm(t.specTerm));
      if (!spec) fail("terms", `term ${t.id}: specTerm "${t.specTerm}" not in Appendix E`);
      else if (absorbed.has(spec)) fail("terms", `Appendix E "${spec}" absorbed twice`);
      else absorbed.add(spec);
    }
  }
  for (const t of lexicon.terms) {
    for (const ref of t.seeAlso ?? []) {
      if (!ids.has(ref)) fail("terms", `term ${t.id}: seeAlso "${ref}" undefined`);
    }
    if (t.stateRef) {
      const [f, id] = t.stateRef.split(".");
      if (!lexicon.states?.[f]?.[id]) fail("terms", `term ${t.id}: stateRef ${t.stateRef} resolves to no state`);
    }
  }
  // Spec terms unclaimed by a merge stand alone — shadowing without a merge is the collision class.
  for (const [normalized, specName] of normSpec) {
    if (absorbed.has(specName)) continue;
    const shadower = lexicon.terms.find((t) => norm(t.term) === normalized || t.id === normalized);
    if (shadower) {
      fail("terms", `Appendix E "${specName}" collides with lexicon term "${shadower.id}" — declare specTerm or rename`);
    }
    anchors.add(normalized);
  }
  for (const t of lexicon.terms) anchors.add(t.id);
  if (anchors.size < 30) vacuous("terms", `only ${anchors.size} glossary anchors`);
  else notes.push(`terms: ${lexicon.terms.length} site terms + ${specTerms.size} spec rows → ${anchors.size} anchors`);
}

// --- 8. <Term> usage ------------------------------------------------------------
{
  const files = [];
  const walk = (dir) => {
    for (const e of readdirSync(dir)) {
      const p = join(dir, e);
      if (statSync(p).isDirectory()) walk(p);
      else if (/\.(astro|tsx)$/.test(e)) files.push(p);
    }
  };
  walk(SRC);
  const defined = new Set(lexicon.terms.map((t) => t.id));
  let uses = 0;
  for (const f of files) {
    const text = readFileSync(f, "utf8");
    const seen = new Set();
    for (const m of text.matchAll(/<Term\s+term="([^"]+)"/g)) {
      uses++;
      if (!defined.has(m[1])) fail("usage", `${relative(WEB, f)}: <Term term="${m[1]}"> undefined`);
      if (seen.has(m[1])) fail("usage", `${relative(WEB, f)}: term "${m[1]}" used twice — first-mention only (the popover id is the anchor)`);
      seen.add(m[1]);
    }
  }
  notes.push(`usage: ${uses} <Term> use(s) over ${files.length} sources`);
}

// --- 9. built html ----------------------------------------------------------------
{
  if (!existsSync(DIST)) {
    notes.push("built: dist absent — legs skipped (they run after astro build in npm run check)");
  } else {
    const htmlFiles = [];
    const walk = (dir) => {
      for (const e of readdirSync(dir)) {
        const p = join(dir, e);
        if (statSync(p).isDirectory()) walk(p);
        else if (e.endsWith(".html")) htmlFiles.push(p);
      }
    };
    walk(DIST);
    if (htmlFiles.length === 0) vacuous("built", "dist/ has no html");

    // 9a. every sig-term link resolves to a /glossary/ anchor id
    const glossaryPath = join(DIST, "glossary", "index.html");
    if (!existsSync(glossaryPath)) fail("built", "dist/glossary/index.html missing");
    else {
      const glossary = readFileSync(glossaryPath, "utf8");
      const glossaryIds = new Set([...glossary.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]));
      for (const f of htmlFiles) {
        const text = readFileSync(f, "utf8");
        for (const m of text.matchAll(/sig-term__link[^>]*href="[^"]*glossary\/#([^"]+)"/g)) {
          if (!glossaryIds.has(m[1])) {
            fail("built", `${relative(WEB, f)}: term link #${m[1]} resolves to no glossary anchor`);
          }
        }
        // popover ids must be unique on a page
        const pop = [...text.matchAll(/\sid="td-([^"]+)"/g)].map((m) => m[1]);
        if (new Set(pop).size !== pop.length) {
          fail("built", `${relative(WEB, f)}: duplicate term popover ids`);
        }
      }
    }

    // 9b. no raw enum token in visible text (outside code/pre/details — DR-K14-09)
    const enums = new Set();
    for (const states of Object.values(lexicon.states)) {
      for (const id of Object.keys(states)) enums.add(id);
    }
    for (const id of ["NOT_APPLICABLE", "possible_duplicate", "reviewed_by_person", "location_check"]) enums.add(id);
    const enumRe = new RegExp(`\\b(${[...enums].join("|")})\\b`);
    const joinedRe = /[a-z][.?!)][A-Z][a-z]/;
    let scanned = 0;
    for (const f of htmlFiles) {
      let text = readFileSync(f, "utf8");
      const main = text.match(/<main[\s\S]*?<\/main>/);
      if (!main) continue;
      text = main[0]
        .replace(/<(script|style|code|pre)[\s\S]*?<\/\1>/g, " ")
        .replace(/<details[\s\S]*?<\/details>/g, " ")
        .replace(/<[^>]+>/g, " ")
        .replace(/&[a-z]+;|&#\d+;/g, " ");
      scanned++;
      // /glossary/ IS the definitional surface — the spec's own term names
      // (e.g. UNRESOLVED) are legitimately visible there as index terms; the
      // enum rule binds running prose on every other page.
      if (f !== join(DIST, "glossary", "index.html")) {
        const em = text.match(enumRe);
        if (em) {
          fail("built", `${relative(WEB, f)}: raw enum "${em[1]}" in visible text — ` +
            `enums may appear only in code/Technical details (DR-K14-09, SIG-UI-143)`);
        }
      }
      const jm = text.match(joinedRe);
      if (jm) {
        fail("built", `${relative(WEB, f)}: joined words "${jm[0]}" at an element boundary (DR-K14-19)`);
      }
    }
    if (scanned === 0) vacuous("built", "no <main> found in dist html");
    else notes.push(`built: ${scanned} pages scanned for enum leaks + joined words`);
  }
}

// --- 10. chrome — the forty-word visible-by-default budget ----------------------
{
  const chrome = lexicon.chrome;
  if (!chrome || typeof chrome !== "object") {
    fail("chrome", "lexicon.chrome missing — the shared chrome strings must be declared");
  } else {
    const COUNTED = ["strip", "dispute", "howWeKnowThis", "tagline", "licences", "status", "cite"];
    for (const key of [...COUNTED, "stampRelease", "stampDevelopment"]) {
      if (typeof chrome[key] !== "string" || chrome[key].length === 0) {
        fail("chrome", `lexicon.chrome.${key} missing or empty`);
      }
    }
    // A data slot keeps the template honest — a rendered count or date is
    // never a literal in chrome copy.
    for (const slot of ["{sources}", "{asOf}", "{reviewStatus}"]) {
      if (typeof chrome.strip === "string" && !chrome.strip.includes(slot)) {
        fail("chrome", `strip template lost its ${slot} slot — a value must never be hard-coded`);
      }
    }
    const words = (s) =>
      (s ?? "")
        .split(/\s+/)
        .filter((w) => /[\p{L}\p{N}]/u.test(w)).length; // a {slot} or a value is one word; "·" is none
    let total = 0;
    for (const key of COUNTED) total += words(chrome[key]);
    // Exactly one stamp form renders per page — count the larger.
    total += Math.max(words(chrome.stampRelease), words(chrome.stampDevelopment));
    if (total > 40) {
      fail("chrome", `visible-by-default chrome words ${total} > 40 (SIG-UI-145)`);
    } else if (total === 0) {
      vacuous("chrome", "no chrome words counted");
    } else {
      notes.push(`chrome: ${total} visible-by-default chrome words ≤ 40 (SIG-UI-145)`);
    }
  }
}

// --- report -----------------------------------------------------------------------
for (const n of notes) console.log(`check-lexicon: ${n}`);
if (failures.length) {
  console.error(`check-lexicon: ${failures.length} violation(s)`);
  for (const f of failures) console.error(`  ${f}`);
  process.exit(1);
}
console.log("check-lexicon: PASS");
