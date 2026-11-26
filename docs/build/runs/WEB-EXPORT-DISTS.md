# WEB-EXPORT-DISTS — D-P37.65a-2 verify leg: both export-mode dists to completion

- **Deferral verified:** `D-P37.65a-2` (kind F) — the verify cell reads
  "`SIG_DATA_SOURCE=export SIG_EXPORT_DIR=<national export> npm --prefix web run
  build` completes over the real national export emitting every published entity
  route (both the `v/` and `s/<pub>` dists), with `npm --prefix web run check`
  green". This leg is the completion evidence the fix leg
  (`docs/build/runs/WEB-EXPORT-READERS.md`, `caae1a2f`, PR #567) left open.
- **Harness:** devin-desktop/swe-2-high/subagent
- **Branch / base:** `r11/ops-web-export-dists` forked at
  `origin/r11/ops-web-export-readers` tip `ea871d3c` — fix commit `caae1a2f`
  confirmed ancestor (`git merge-base --is-ancestor`).
- **Environment:** node `v24.21.0` (nvm, matches `web/.nvmrc`), npm 11.19.0;
  real national export at `/Users/stevenvitali/Eleutheria/exports/out/national`
  (4.2 GiB; `manifest.json` sha256
  `39e6549b4f54f63f867f35ba8017348e675f5130108b62c1b7824dac8168153c` — matches the
  fix leg's recorded manifest). Worktree `/tmp/sig-web-dists`; dists emitted to
  `/tmp/sig-web-dists-out/` via `astro build --outDir` (same pattern as the fix
  leg — an outDir outside the project root is **not** emptied by astro; noted
  below). Machine: 36 GiB RAM, single 460 GiB volume; a sibling agent
  (`r11/ops-release-stage-throughput`) was writing concurrently throughout —
  disk free fluctuated 2.6–21 GiB during the leg.

## `v/` latest-view dist — **COMPLETE**

Command (the verify cell's invocation; `--outDir` redirect only):

```
SIG_DATA_SOURCE=export SIG_EXPORT_DIR=/Users/stevenvitali/Eleutheria/exports/out/national \
  npm --prefix web run build -- --outDir /tmp/sig-web-dists-out/v
```

Three attempts; the first two died on *environment resource bounds*, not the
deferred reader bound:

| attempt | result | mechanism |
|---|---|---|
| 1 (21:00:32Z, default heap) | exit 134 at 16.5 min, ~264k HTML emitted | `FATAL ERROR: Ineffective mark-compacts near heap limit — JavaScript heap out of memory` during `/sources/` emit; live old-space ~3.73 GiB vs the ~4 GiB V8 default. The memoized corpus (~1.9 GiB parsed JSON held live, by design) + astro bookkeeping exceeds the default heap. |
| 2 (21:24:38Z, `--max-old-space-size=16384`) | exit 1 at 16.0 min | `ENOSPC: no space left on device` writing `/id/site/…/index.html` — the box's 19 GiB free was consumed by the dist (~6 GiB) plus concurrent sibling writes; heap was healthy (peak RSS 4.94 GiB, still climbing without GC distress). |
| 3 (21:43:56Z, `--max-old-space-size=12288`) | **exit 0** | completed. |

- **Wall-time:** 21:43:56Z → 22:09:28Z — astro reports
  **`287,679 page(s) built in 25m 26s`**; `sig-page-types: 287,681 route(s)
  classified, 69 T0 meta CSP(s) tightened`; `sig-redirects: 526,669 redirect
  rule(s)`; `[build] Complete!`
- **Peak RSS (build tree):** 8,400,368 KB ≈ **8.0 GiB** (12 GiB cap).
- **Dist size:** **12 GiB**, 304,138 files — 287,681 `*.html` + 16,457
  non-HTML (JSON twins, `.jsonl`/`.csv` twins, atom feeds, `_astro` assets).
- **Per-surface HTML tallies** (`find dist -name '*.html'` by first segment):
  `id/` 257,794 · `task/` 22,148 · `sources/` 3,571 · `research-queue/` 3,040 ·
  `evidence/` 518 · `dossier/` 253 · `watch/` 228 · `disagreements/` 59 ·
  `changes/` 17 · `entity/` 10 · `status/` 8 · `graphs/` 8 · `about/` 4 ·
  `data/` 3 · singletons (`index`, `map`, `search`, `explore`, `quality`,
  `methodology`, `glossary`, `terms`, `style-guide`, `editorial-standards`,
  `dispute`, `data-collection`, `coverage-metrics`, `corrections`, error pages).
- The `entity/` count is honestly small on this corpus: only **4** label rows
  resolve `pageState === "published"` (the four `org` twins shipped under
  `web/entity/org/`); the 257,823 `site` rows are `unpaged` (`site` is not a
  `PAGE_KINDS` kind) and the remaining `org` rows are `not_yet_reviewed` — they
  carry `/id/<type>/<uuid>` stubs (257,794) instead. No `ERR_STRING_TOO_LONG`,
  no corpus re-parse: emission ran at ~2–25 ms/route for stubs, ~0.3–4 s for
  dossier/sources/evidence pages.
- Spot-check: `entity/org/oklahoma-city-police-department--2thaz3s/index.html`
  renders the real entity page; root page carries the honest interim release
  sentence (no `release.json` bound for `v/`).
- **Post-measurement note:** the `v/` tree was deleted after measurement to
  guarantee the sibling-pressured disk could hold the snapshot dist; evidence is
  the meta/log/manifests archived under `/tmp/sig-web-dists-out/` (not committed
  — ephemeral measurement artifacts).

## `s/<pub>` snapshot dist — **COMPLETE**

Command — the pub is named by `SIG_BASE_PATH` (`astro.config.mjs`
`base: process.env.SIG_BASE_PATH || "/"`, the P36.66a seam; the fixtures check
`scripts/check-snapshot-mount.mjs` uses the same env). The candidate release
identity was bound via a **frozen copy** of the staged `sig.site-release/1`
(`SIG_RELEASE_JSON=/tmp/sig-web-dists-out/release/release.json`, copied from the
candidate staging tree `/tmp/sig-p3765a/work/release.json` — read-only copy so a
live staging rewrite could not make the input inconsistent):

```
SIG_DATA_SOURCE=export SIG_EXPORT_DIR=/Users/stevenvitali/Eleutheria/exports/out/national \
  SIG_BASE_PATH=/s/p-31371dfb4b2b26453f818fefd311ea07be50ef8413aa9185be1ede927a773a8b \
  SIG_RELEASE_JSON=/tmp/sig-web-dists-out/release/release.json \
  NODE_OPTIONS=--max-old-space-size=12288 \
  npm --prefix web run build -- --outDir /tmp/sig-web-dists-out/snapshot
```

- **Result:** **exit 0**, first attempt under the raised heap. astro reports
  **`287,679 page(s) built in 75m 42s`** (route generation 69m 56s + page-types
  classification) — `sig-page-types: 287,681 route(s) classified, 69 T0 meta
  CSP(s) tightened`; `sig-redirects: 526,669 rule(s)`; `[build] Complete!`
  at 18:33:34 local (22:17:49Z → 23:33:57Z). Slower than `v/`'s 25.5 min only
  from concurrent sibling disk/CPU load; emit pace per route was nominal.
- **Peak RSS:** 6,653,536 KB ≈ **6.3 GiB**.
- **Dist size:** **15 GiB**, 304,184 files, 287,681 `*.html` — per-surface
  tallies identical to `v/` (id 257,794 · task 22,148 · sources 3,571 ·
  research-queue 3,040 · evidence 518 · dossier 253 · watch 228 ·
  disagreements 59 · changes 17 · entity 10 · …).
- **Base containment:** in-site links carry the snapshot prefix
  (`href="/s/p-31371dfb…/_astro/…"`, `…/favicon.svg`, …) — the SIG-REL-008
  withBase() seam on real bytes. A sampled sweep reusing the gate's own
  `scanHtml` (`scripts/check-snapshot-mount.mjs`) with `base:
  /s/p-31371dfb…/` over **2,970 of the 287,681 emitted HTML files** (every
  97th file + every top-level page): **0 containment violations** — every
  same-origin link stays inside the base or a declared `/r/`/`/releases/`/
  `/v1/`/`/intake/` exception.
- **Release stamp:** `<meta name="sig-release" content="sig-2026-11-25.1
  p-31371dfb4b2b26453f818fefd311ea07be50ef8413aa9185be1ede927a773a8b">` — the
  bound candidate identity renders; `sig-2026-11-25.1` label present in the
  page. (The staged `release.json` is the sibling throughput leg's artifact —
  read, never modified.)

## `npm --prefix web run check` — e2e sweep flakes under ambient load

Run over the worktree after both dists completed (no concurrent work from this
leg): typecheck → test:unit → fixtures build → every `check:*` script →
test:e2e, all through the `check` chain.

- `astro check` typecheck: **0 errors** (pre-existing warnings only).
- `vitest run`: **109 files / 1407 tests green**.
- `SIG_BUILD_INTERNAL=1 astro build` (fixtures): **528 pages — PASS**.
- `check:lhci` / `check:map-styles` / `check:licenses` / `check:paths` /
  `check:snapshot` / `check:dom` / `check:figures` / `check:tokens` /
  `check:lexicon` / `check:copy` / `check:feeds` / `check:dsrc` /
  `check:runtime-deps`: **all PASS**.
- `npx playwright test` (fixtures dist): **6029 passed / 3 failed (18.0m)** —
  every failure a `Test timeout of 30000ms exceeded` inside a whole-route
  serial-fetch sweep, none an assertion:
  - `chrome.spec.ts:86` unique `<title>`/meta sweep (~500 routes serially);
  - `chrome.spec.ts:109` sitemap resolvable sweep;
  - `transparency-acceptance.spec.ts:86` cite-mode sweep.
  The box was at load-average 34–56 throughout (several sibling agents running
  their own playwright/astro/openssl workloads — fseventsd 83%, VM 63% at the
  peak); each sweep must serially fetch ~hundreds of routes through `astro
  preview` inside a 30 s cap, which cannot schedule under that contention.
- Re-runs: `typeahead.spec.ts` (the one non-sweep flake, a 15 s `toBeVisible`
  starvation) **4/4 green alone in 57.3 s**; `chrome.spec.ts` alone **9/11
  green** (favicon sweep 28.1 s, glued-words 27.3 s, ungrouped-number 59.5 s all
  passing under the cap). The three remaining sweeps timed out again on every
  contended attempt — identical failure class to the fix leg's six flakes,
  which cleared uncontended on the same bytes (this branch adds only this
  ledger file to `ea871d3c`'s code).
- A watcher (`/tmp/sig-web-dists-out/e2e-quiet-retry.sh`, not committed) keeps
  retrying the three specs whenever the 1-min load average drops below 12;
  outcome recorded if it lands before closeout.

## Verdict on `D-P37.65a-2`

- `v/` latest-view dist: **COMPLETE** — 287,679 pages in 25m 26s, exit 0.
- `s/<pub>` snapshot dist: **COMPLETE** — 287,679 pages in 75m 42s, exit 0,
  `/s/<pub>/` base on real bytes + real `sig.site-release/1` stamp.
- `npm --prefix web run check`: **green except 3 e2e whole-route sweep
  timeouts** — 6029/6032, all three the 30 s serial-fetch cap under ambient
  box load (34–56), none an assertion; every affected spec family has cleared
  uncontended on byte-identical code (fix leg + this leg's re-runs), and a
  quiet-window watcher remains armed. See the check section.
- Residual bound (not the deferred one): the default ~4 GiB V8 heap OOMs on
  this corpus (~3.7 GiB live memoized data + astro bookkeeping) — a
  `NODE_OPTIONS=--max-old-space-size` raise is required for the full-corpus
  build on this box. Whether that raise should be wired into docs/scripts is a
  decision for the parent/operator — recorded here as evidence, not acted on.

The deferral row itself is **not flipped here** — the canonical row lives on
`r11/P37.65a-live-2`; the parent flips it once both legs' evidence is in.
