# PHANTOM-ARTIFACT-FIX — D-P37.65a-5: the emit-side phantom `/artifact/` routes serving synthesized payloads for absent export files

- **Finding:** `docs/build/reports/p37.65a-modes-triage/FINDINGS.md`
  finding 2 (verdict: defect, emit side, small) on
  `origin/r11/ops-modes-triage` / PR #571 — the real export carries ZERO
  `presentation/` paths (verified: `exports/out/national/manifest.json`
  0/1419), yet `getReleaseArtifactPayload`'s `[]` fallback via
  `readPresentation` masked the absence, minting a phantom
  `/artifact/web/presentation/jurisdiction_dossiers.json` route serving
  `[]` — against the route's own contract
  (`web/src/pages/artifact/[...path].json.ts`: "a path that is not a
  figure-addressable artifact emits no route (404), so the link set and
  the artifact set can never drift") and tripping the V3 `presentation/`
  by-name ban (`ops/src/ops/release_verify.py`, `publish.py`) in both
  dist trees. The ban stays unchanged — it caught a real demo-family
  residue.
- **Harness:** devin-desktop/swe-2-high/subagent
- **Branch / base:** `r11/ops-phantom-artifact-fix` off
  `origin/r11/P38.3c-round11-integration-plan-2` (worktree
  `/private/tmp/sig-phantom-fix`), PR base
  `r11/P38.3c-round11-integration-plan-2`.
- **Environment:** Node `v24.21.0` (nvm, `.nvmrc` pin, engine-strict);
  `npm ci` in the worktree; Playwright `chromium_headless_shell-1234`
  installed on demand (the cache carried only `-1248`; all 4361
  first-attempt e2e failures were `browserType.launch` executable-miss,
  never assertion failures).

## Fix shape

The absent-artifact contract the codebase already uses — `null` payload →
`getStaticPaths` emits no route — applied at the payload READ, never at
the route enumeration (the fixture allow-list stays the emission bound;
the payload decides whether bytes exist):

- `web/src/lib/data.ts` — `readPresentation` gained a nullable twin
  `readPresentationOrNull` (`null` when
  `<exportDir>/web/presentation/<name>.json` is absent). `readPresentation`
  now delegates (`OrNull ?? fallback`), so the `[]` fallback is unchanged
  for its only legitimate consumer, the dossier-LIST reader
  `jurisdictionDemos` (P30.3: demo dossiers render only when the bundle
  ships the file — same semantics, now routed through the nullable read).
- `web/src/lib/data.ts` `getReleaseArtifactPayload` case
  `"web/presentation/jurisdiction_dossiers.json"` — export mode reads
  `readPresentationOrNull<Dossier[]>`; fixtures/national modes keep
  serving `JURISDICTION_DOSSIERS`. Absent file → `null` → no route; a
  shipped file → its own bytes.
- `web/src/lib/data.ts` `getFreshnessRecords` — the same `[]`-fallback
  masking pattern on `transparency/freshness.jsonl` (`existsSync → []`).
  Now `unknown[] | null`, `null` when the file is absent. This was a live
  sibling instance of the same defect: the P27.5 fixture-export harness
  itself emits `transparency/` without `freshness.jsonl`, so export-mode
  builds were already minting `/artifact/transparency/freshness.json`
  serving a synthesized `[]`. The staleness cells derive from the same
  file via `exportFreshnessMap` (`web/src/lib/sources-table.ts`) — absent
  file → no staleness rows → no figures name it, so `null` creates no
  dangling link.

## Sibling audit — every `getReleaseArtifactPayload` case reviewed

- **Same `[]`-mask defect, fixed:** `transparency/freshness.jsonl`
  (above).
- **Already nullable/honest:** `status/quality/latest.json`,
  `status/lane.json`, `transparency/sources/<id>/{executions,captures,versions,entities}.*`,
  `web/dossier_sources/<slug>.json` (all `null` on absence).
- **Fail-loud (no mask):** `web/{dossiers,coverage,freshness,evaluation,
  mech_eval,quality}.json`, `transparency/{counts,sources}.json`,
  `web/analytics/{density_bins,provenance}.json`, `web/leverage.json`.
- **Deliberate documented compat shims — reviewed, NOT `[]` masks, left
  unchanged:** `web/terms_disclosure.json` (P34.17 policy-table fallback
  for pre-P34.17 exports carrying express-terms rows; page figures may
  name it and gating the route would break their `href`), `web/sources.json`
  (P35.37 sites.jsonl derivation for pre-P35.37 exports — same
  figure-link consideration), `web/dossier_index.json` (P35.45 v2-index
  supersession serving the index document the page renders). These serve
  real derived bytes at a name the page's figures can legitimately link
  when the fallback path is live; an export not listing them already
  fails `check-figures` on any figure naming them in export mode. They
  are a different class (named compat fallbacks feeding live figure
  links), not the absence-masking `[]` this defect is.

## Verification

- `npx vitest run tests/unit/data.test.ts` — 53/53 pass (5 new cases in
  the `D-P37.65a-5` describe: absent presentation file → `null`; shipped
  file → own bytes; fixtures → demo payload; absent `freshness.jsonl` →
  `null`; shipped rows → served).
- `npm --prefix web run check` — **green**: typecheck 0 errors,
  test:unit 1402/1402, fixtures build 513 pages, check:licenses 286 deps,
  test:e2e **6032/6032 passed** (~6.5m).
- Focused emit check over the P27.5 fixture-export harness bundle
  (`npm run export:fixtures -- /tmp/sig-export-nopres`,
  `SIG_DATA_SOURCE=export SIG_EXPORT_DIR=… npx astro build`):
  - **with** `web/presentation/` →
    `dist/artifact/web/presentation/jurisdiction_dossiers.json` emitted
    with the real bytes.
  - **without** `web/presentation/` → `dist/artifact/web/presentation/`
    absent (phantom route gone) AND `dist/artifact/transparency/`
    carries no `freshness.json` (the sibling phantom, also gone); the
    remaining 31 artifact payloads still emit.
  - Pre-existing bundle quirk recorded, not mine: `/watch/feeds/all.ics`
    renders `invalid ISO stamp for iCal: ""` on this harness bundle
    (bundle lacks `datapackage.json`; identical on the unmodified base —
    verified via `git stash` rebuild).

## Consequence (from the triage disposition)

The fix changes `s/`+`v/` tree bytes (two `artifact/` files leave the
emitted set) → the two dists rebuild and `sites`+`stage` re-run those
namespaces in the release-cut leg; `r/`+`releases/` and the pub id are
untouched (the descriptor binds no site-tree bytes). The V3
`presentation/` ban at `ops/src/ops/release_verify.py` and
`ops/src/ops/publish.py` is verbatim unchanged — it did its job.

No DEFERRALS rows written (task scope); `D-P37.65a-5` disposition was
already recorded by the triage leg.
