# MODES-TRIAGE — the `D-P37.65a-1` leg-3 mode-S verify findings, classified

- **Scope:** investigation + documentation only — classify each verbatim
  finding from `docs/build/runs/P37.65a-live-3.md` (on
  `r11/P37.65a-live-3` / PR #570), cite the deciding code/spec lines,
  recommend a disposition. No fixes implemented.
- **Harness:** devin-desktop/swe-2-high/subagent
- **Branch / base:** `r11/ops-modes-triage` (worktree
  `/private/tmp/sig-modes-triage`), PR base
  `r11/P38.3c-round11-integration-plan-2`.
- **Report:** `docs/build/reports/p37.65a-modes-triage/FINDINGS.md`.
- **Evidence read:** the live-3 run ledger verbatim; probe result rows in
  `docs/build/logs/p37.65a-live-3/verify-results/` (gitignored, read in
  `/private/tmp/sig-65a-live3`); `ops/src/ops/release_verify.py`,
  `ops/src/ops/site_trees.py`, `ops/src/ops/publish.py`,
  `ops/src/ops/release_pipeline.py`, `ops/src/ops/release_conf.py`,
  `ops/public_routes.toml`, `exports/src/exports/release.py`,
  `exports/src/exports/release_identity.py`,
  `exports/src/exports/release_pages.py`, `web/src/lib/data.ts`,
  `web/src/pages/artifact/[...path].json.ts`,
  `web/src/layouts/BaseLayout.astro`, `web/src/pages/**/print.astro`,
  `web/src/components/print/PrintChrome.astro`,
  `web/src/lib/release-stamp.ts`, `web/src/lib/figure-artifacts.json`,
  `docs/build/planning/2026-09-30-next-phase/design/G3-release-model.md`
  (§5.4/§5.5/§6.1), the real export at `exports/out/national/` (no
  `web/presentation/` — verified), `docs/build/runs/WEB-EXPORT-DISTS.md`
  (the `v/` dist's unbound stamp — recorded verbatim).

## Verdicts (one line each)

1. **V3 `page_index.json/` top-level in `s/<pub>/` — spec-gap:** the J3 §8.1
   withdrawal index is a legitimate release-model artifact
   (`site_trees.py:17-21,228-232`); the fix is additive — `allowed_s` extras
   at `release_verify.py:866-870` + G3 §5.4's added-prefixes line
   (`G3-release-model.md:318`); NOT `public_routes.toml` (web-dist contract).
   → `D-P37.65a-4` · gates the leg (V3 fail).
2. **V3 `artifact/web/presentation/…` in both trees — defect:** the real
   export carries no `web/presentation/` (verified —
   `exports/out/national/manifest.json`, 0/1419), but
   `getReleaseArtifactPayload` masks the absence with the `[]` fallback
   (`data.ts:3141-3144` + `readPresentation` `data.ts:2356-2364`) → a phantom
   `/artifact/` route serving `[]` contrary to the route's own contract
   (`[...path].json.ts:10-12`); the ban (`release_verify.py:889-893`,
   `publish.py:231-234`) stays — it did its job. → `D-P37.65a-5` · gates
   (V3 fail ×2).
3. **V13 `API is live` missing on error/print pages — spec-gap:** the
   `sig-release` meta is unconditional (`BaseLayout.astro:316`,
   `print.astro:217`) but the basis sentence lives in full-chrome footer
   only (`BaseLayout.astro:358-393`); `chrome="minimal"` error pages
   (P34.13) and `data-sig-chrome="print"` footers (P36.26, `PrintChrome.astro`)
   deliberately omit it — G3 §6.1's "every HTML page" never scoped the
   chrome classes; needs an owner decision (scope V13 to `data-sig-chrome="full"`
   vs. extend the footer), not just engineering. Also recorded: misses are
   `[:10]`-truncated (~22+ true), `s/` pages carry latest-view wording vs.
   the §6.1 fixed-copy variant, and the whole `v/` tree is unstamped (~514k
   pages — `WEB-EXPORT-DISTS.md` bound no `SIG_RELEASE_JSON`) which
   pre-figures V4. → `D-P37.65a-6` · gates (V13 fail).
4. **Stranded label `sig-2026-11-25.1` → `['None']` — defect + residue:**
   `verb_build` allocates pub=null (`release_pipeline.py:757,682-712`) but
   passes `labels_registry=None` so `record_label_publication`
   (`release_identity.py:283-304`, called only at `release.py:876-877`) is
   unreachable — every ops-path label strands, not just attempt-2's;
   `read_label_map` (`release_conf.py:157-172`) skipping null pubs also
   kills the `labels.conf` 301 alias post-promotion. Reconciliation is
   forced: the label is cryptographically welded to the pub (label ⊂
   descriptor ⊂ pub sha) — the operator binds `sig-2026-11-25.1 →
   p-31371dfb…` under the lock; machinery gains the post-build bind.
   → `D-P37.65a-7` · gates (V2 fail).
5. **Tree suite OS-killed ~576k pages — defect:** `check_v5` accumulates
   full referrer sets (`release_verify.py:1055-1071`) though consumers take
   ≤2 witnesses (`:1095,:1114`) — O(edges) ≈ 25 M pairs, multi-GB resident;
   `_html_files` materialises ~1.28 M sorted Paths (`:459-466`). Fix class:
   bounded-resident accumulation + page-iteration streaming in
   `release_verify.py`; the serial-fetch wall-clock bound is separate and
   already recorded. → `D-P37.65a-8` · partial (full-suite evidence leg).

## Deferred

- New deferral ids suggested `D-P37.65a-4…-8` (–1…–3 exist); no DEFERRALS.md
  rows written — the report proposes, the fix legs record.
- Not findings: V12 pass (1,296,982 files, 0 hits) and the V14/V15 skips
  (first release — no baseline, no quality report) are honest states; V2's
  dirty-tree refusal is the leg's own uncommitted ledger work.
- Out of scope (recorded, not adjudicated): the staging origin serves no
  staged tree (no `/mnt/rel` mount on `sig-web-staging` — V11's axe leg has
  no serving surface; a service update is the deploys-side authority's).
