# P36.72a — core-surfaces acceptance readout (Class S republish packet)

**Row:** 415 / ACC-PLACES a-half · **Branch:** `r11/P36.72a-core-surfaces-crawl-parity-number-truth` · **Harness:** devin-desktop/swe-2-high/subagent
**Produced:** 2026-11-05 · **Layer reached:** engineered + fixture-verified (`live_verification=false` — nothing in this packet asserts a served/hosted state; the promote is P36.72b's operator act under HG-11)
**Machine twin:** `readout.json` (`sig.core-surfaces-acceptance/1`)

This is the evidence packet the P36.72b operator decision consumes. Every check is read-only over the built fixture site (`SIG_BUILD_INTERNAL=1` so the internal surfaces are measurable too); every sweep derives its route set from `dist/page-types.json` + the emitted file tree — never a hand list — and a surface that cannot be verified is named, never silently skipped (SIG-ENG-042).

## What the battery measures (506 tests, all green, ~1.1 min incremental)

| leg | scope | result |
|---|---|---|
| Zero-404 crawl (SIG-JUR-D09) | every discovered route (477: T1 447 · T0 19 · T3 8 · T2 3) + every emitted non-HTML file (757 of 1,234 total emitted files) answers 200; a never-published route answers the branded 404 | PASS |
| Historical URLs (SIG-UI-058, SIG-JUR-D09) | all 38 `dist/redirects.conf` rules: every rule names a resolvable end-state — an emitted 3xx target (fixture-scope targets that the corpus does not publish are recorded, never failed), an emitted try_files file, or a declared status; every stub-emitted path serves its tombstone page | PASS |
| Bare ids (SIG-JUR-D08, SIG-DSRC-D02) | no dossier twin's page `<h1>` is a bare code/key/slug; no source id appears as visible prose outside `<code>`/`sig-mut`/figure-evidence link labels/URL-path locators across all emitted HTML | PASS |
| Parity (SIG-JUR-D06, SIG-DSRC-D08/D09) | every dossier `.json` twin ↔ its HTML page (h1, as-of, records figure); every sources explorer row ↔ its `sig.dossier-sources/1` twin cells (records, share, located/declared, claims, first/last seen, licence; withdrawn/upstream-disappeared/ingested rows carry the twin's honest state); source ↔ dossier contribution parity across surfaces; index rows ↔ twin rollups | PASS |
| Number truth (J3 §5.4, SIG-TRANSP-013) | all 5,150 `<Figure>` regions across emitted HTML: every `data-artifact` + `data-pointer` resolves under the key-aware pointer language (object keys, array indices, id-keyed row selection, row-document field descent, collection counts); every numeric-leaf binding equals the rendered `data-figure-value`; every `data-figure-link="source"` anchor resolves; every `#breakdown` anchor resolves in-page | PASS |
| ROUTES.csv (COV-04) | bijective disposition table over all 48 advertised 09-27 rows (R01–R36, X01–X12): `resolves` families emit, `retired` routes resolve through the one redirect generator, `internal` routes emit `internal:true` only (never public), `/task/` keeps its honest no-index answer, bucket/API/intake URLs are `external` — owned by the promoted-release legs | PASS |
| axe WCAG 2.2 AA, both JS states (SIG-UI-037) | `a11y.spec.ts` (JS on) + `a11y-scripts-off.spec.ts` (every script refused at the network layer — the DOM the no-JS reader gets; the `<noscript>` notices' presence is asserted and their rendered visibility is covered by the no-js project) over every discovered route | PASS |
| Agent walkthroughs (K13 §8) | A1 type→place ≤3 clicks · A2 `deployed`/approved/next-decision · A3 council print · A4 gap→task→draft · O1 county overview · O3 local list + CSV + licence · O4 gap→task→template · J1 figure→breakdown→recomputing rows | PASS — **agent-verified**, never represented as user research |
| Budgets (SIG-UI-092) | `budget.spec.ts` per-type wire budgets over every discovered route (the pre-existing gate this row stamps) | PASS |

## Findings the acceptance surfaced (fixed, not deferred)

1. **HWKT source figure bound a field the artifact does not carry.** On dossier pages the `hwkt-sources` figure named `web/dossier_sources/<slug>.json` + `/provenance_summary/source_independence_count` — a field the `sig.dossier-sources/1` doc does not emit (it carries `sources_with_published_claims`, the same count `dossierSourcesProvenance` maps in). The binding could never resolve. Fixed in `web/src/components/HowWeKnowThis.astro`: a dsrc-scoped module now names the field the artifact actually carries — the rendered value and the pointed value are identical by construction.

## Named limits (recorded, never silently skipped)

- **Fixture-scope redirect targets:** several `/id/**` 3xx successors name entities the fixture corpus does not publish; the rules' end-states are recorded, and the full-set edge probe rides the include-carry leg (`D-P36.35-1` lineage) with the promoted release.
- **Unserved figure artifacts:** artifacts with no page-served bytes are named by the sweep; their figures' evidence reachability is proven via the `data-figure-link="source"` route instead.
- **Subject-bound figures:** a pointer that names a row/object whose figure derives from it (gap ordinals, "rest" remainders ≤ the named count, rendered phrases) is binding-proven and counted; only numeric-leaf bindings are asserted equal.
- **External rows:** bucket/API/intake URLs (X07–X12, X01 tiles) are not site routes — the promoted-release legs own them (`D-P36.71-1`, `D-R10-PUBLISH-1`).
- **`/s/<pub>/` and `/v1/releases/…` parity legs** ride the promoted release — recorded, never claimed here.

## Verdict

**PASS (fixture-verified).** The core surfaces — places, sources, queue, watch, evidence — satisfy the acceptance contract over the fixture corpus: zero unexplained 404s, every advertised/historical route resolves or names its honest disposition, HTML = JSON twin parity holds, displayed numbers trace to served artifact bytes, budgets and axe hold in both script states, and the ROUTES.csv expectation table is bijective. The readout feeds the P36.72b promote decision; nothing here promotes, publishes or ticks HG-11.
