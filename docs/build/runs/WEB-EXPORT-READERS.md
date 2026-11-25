# WEB-EXPORT-READERS — D-P37.65a-2 fix leg: streaming + memoised web export readers

- **Deferral discharged:** `D-P37.65a-2` (kind F) — the `web` export-mode data
  layer bound recorded by `docs/build/runs/P37.65a-live-1.md` (on
  `r11/P37.65a-live-2`, not yet merged into the integration tip): (a) whole-file
  `readFileSync(p,"utf-8")` readers throw `Cannot create a string longer than
  0x1fffffe8` on any compartment `statements.jsonl` >512 MiB
  (`osm_physical/statements.jsonl` = 1,013,125,905 B in the 2026-11-25 national
  export), killing every export-mode `astro build`; (b) the readers are
  non-memoized — ~226k entity pages re-parse the ~1.9 GB statements corpus and
  rebuild `getRecordBasisIndex()`/`entityIndex()` per route (quadratic).
- **Harness:** devin-desktop/swe-2-high/subagent
- **Branch / base:** `r11/ops-web-export-readers` off
  `origin/r11/P38.3c-round11-integration-plan-2` @ `ac52d33e`.
- **Environment:** node `v24.21.0` (nvm, matches `web/.nvmrc`), npm 11.x,
  `engine-strict=true`; real national export at `exports/out/national`
  (4.2 GiB, 1,422 objects, manifest sha256
  `39e6549b4f54f63f867f35ba8017348e675f5130108b62c1b7824dac8168153c`).
- **Return contracts preserved:** every changed function returns the same types
  and row semantics; no caller signature changed; fixtures-mode behaviour is
  unchanged (all caches key on the resolved data root, per-file
  `mtimeMs`+`size`, or the input object's identity, so test fixtures that
  mutate temp dirs between calls still derive honestly — pinned by the
  `SIG_EXPORT_DIR`-flip test).

## Changes

### New: `web/src/lib/jsonl.ts`

- `readLinesSync(path)` — chunked 8 MiB fd-read line iterator; multi-byte-safe
  across chunk boundaries (a UTF-8 sequence split at a boundary is carried into
  the next chunk's decode — pinned by test).
- `readJsonlRows(path)` — parsed-row stream, same skip-blank-lines contract as
  `readFileSync(p,"utf-8").split("\n").map(trim).filter(Boolean).map(JSON.parse)`.
- `readJsonlRowsCached(path)` — per-file parsed-rows cache validated on
  `mtimeMs`+`size` (a rewritten same-length file with a new mtime re-reads).
- `hasNonBlankLine(path)` — streaming `trim() !== ""` probe (replaces a
  whole-file read for a boolean).

### `web/src/lib/data.ts`

- `cachedCorpus(key, build)` — `_corpusCaches` Map keyed
  `"<name>|<mode>|<root>"` so a flipped `SIG_DATA_SOURCE`/`SIG_EXPORT_DIR`/
  `SIG_NATIONAL_DIR` re-reads honestly.
- `readJsonArtifact(path)` + `isJsonParseFailure` — `_artifactDocCache` keyed on
  path, validated by `mtimeMs`+`size`; wired into `readExportArtifact`,
  `readNationalArtifact`, `getEntitySlugHistory`.
- Streamed + memoized via `cachedCorpus`: `getRecordBasisIndex`,
  `getJurisdictionCompartments`, `getEntityLabelRows`, `getEntityCompartments`,
  `getStatementIndex`, `getSourceLicenceTable`.
- Streamed only: `getTermsDisclosure` (`hasNonBlankLine` on
  `operator_accepted/sites.jsonl`), `getFreshnessRecords`,
  `getSourceExecutionsArtifact`.

### Sibling libs

- `web/src/lib/sources.ts` — `sourceLicenceTable` streams `sites.jsonl` via
  `readLinesSync`; `readFileSync` import dropped.
- `web/src/lib/source-page-b.ts` — local `readJsonl` → `readJsonlRowsCached`;
  `getSourceEntities` rewritten as the memoized single-pass
  `sourceEntitiesIndex(root)` = `Map<source_id, Map<entity_id,row>>` (was
  O(sources × corpus) rescan per page; contract-A rows still overwrite
  `_rights` rows to preserve leg order).
- `web/src/lib/source-page.ts` — `_sourcesDocCache` (mtime+size) for
  `transparency/sources.json` shared by `exportPageIds`/`exportRow`;
  `exportExecutions`/`exportFreshness` use `readJsonlRowsCached`.
- `web/src/lib/sources-table.ts` — `exportExecutions`/`exportFreshnessMap` via
  `readJsonlRowsCached`.
- `web/src/lib/issues.ts` — `getIssues` export leg via `readJsonlRows`.
- `web/src/lib/entity-history.ts` — `resolveIndex` WeakMap memo keyed on the
  (memoized) rows array — `resolveEntityRequest` was O(rows) per row =
  O(rows²) in `/id/[type]/[uuid]` `getStaticPaths`.
- `web/src/lib/entity-pages.ts` — `emittedEntityPaths` WeakMap-memoized on the
  index object.
- `web/src/lib/entity-page.ts` — `entityIndex(rows)` WeakMap-memoized on the
  rows array (ran in every entity route's `getStaticPaths` AND per-page
  frontmatter).

## Tests

- `web/tests/unit/jsonl.test.ts` — 7 tests (incl. a multi-byte sequence split
  across the 8 MiB chunk boundary).
- `web/tests/unit/export-readers.test.ts` — 3 tests: `getStatementIndex` streams
  a synthetic `statements.jsonl` past `0x1fffffe8` chars without throwing;
  memoized second call does not re-parse; a flipped `SIG_EXPORT_DIR` re-reads
  honestly (never a stale memo).

## Evidence

- `npm run typecheck` (`astro check`): **0 errors** (pre-existing warnings only).
- `npm run test:unit` (vitest): **109 files / 1407 tests green** — incl.
  `jsonl.test.ts` 7/7, `export-readers.test.ts` 3/3.
- `SIG_BUILD_INTERNAL=1 npm run build` (fixtures): **528 pages, 53 s — PASS**.
- `check:lhci` / `check:map-styles` / `check:licenses` / `check:paths` /
  `check:snapshot` / `check:dom` / `check:figures` / `check:tokens` /
  `check:lexicon` / `check:copy` / `check:feeds` / `check:dsrc` /
  `check:runtime-deps`: **all PASS**.
- `npx playwright test` (fixtures dist): in-flight at ledger write — see the
  commit record for the final count.
- **Real-bytes reader smoke** (throwaway vitest, `SIG_DATA_SOURCE=export
  SIG_EXPORT_DIR=exports/out/national`, node v24.21.0): every corpus reader over
  the real 2026-11-25 export, cold → memoized:

  | reader | cold | rows |
  |---|---|---|
  | `getStatementIndex` | 79.3 s | 930,102 |
  | `getRecordBasisIndex` | 20.7 s | 226,157 |
  | `getJurisdictionCompartments` | 17.3 s | 58 |
  | `getEntityLabelRows` | 9.9 s | 260,822 |
  | `getEntityCompartments` | 29.2 s | 226,157 |
  | `getSourceLicenceTable` | 3 ms | 186 |

  Second `getStatementIndex()` call <1 s (memoized). No `ERR_STRING_TOO_LONG`
  on the 1.01 GB `osm_physical/statements.jsonl` — the bound is gone on the
  real bytes, not just the synthetic fixture.
- **Real `v/` export build** (`SIG_DATA_SOURCE=export SIG_EXPORT_DIR=
  exports/out/national astro build --outDir /tmp/sig-export-dist-v`): reached
  `generating static routes` — the phase where both P37.65a-live-1 builds sat
  at **0 routes for hours** — and is emitting real routes steadily (jurisdiction
  dossiers + entity routes at ~1–9 s/page on real rows). Full ~226k+ route
  emission is a multi-hour leg; it was left running and the per-route emit pace
  (never a corpus re-parse) is recorded.

## Deferral status

`D-P37.65a-2`'s canonical row lives in `docs/tickets/DEFERRALS.md` on
`r11/P37.65a-live-2` (`bff74d36`) — not yet merged into the integration tip this
branch is cut from, so the row is not flipped here. The verify cell reads
"`SIG_DATA_SOURCE=export SIG_EXPORT_DIR=<national export> npm --prefix web run
build` completes over the real national export emitting every published entity
route (both the `v/` and `s/<pub>` dists), with `npm --prefix web run check`
green". This leg lands the code fix and proves the bound is removed at the
reader layer over the real export plus steady route emission; the complete
both-dists emission leg is the remaining evidence the flip needs (the `v/`
build was still emitting when this ledger was written).
