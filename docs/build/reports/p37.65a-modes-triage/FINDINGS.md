# P37.65a mode-S triage — the five verify findings from `D-P37.65a-1` leg 3

Investigation + documentation only — no fixes implemented. Source leg:
`docs/build/runs/P37.65a-live-3.md` (on `r11/P37.65a-live-3`, PR #570); probe
rows in `docs/build/logs/p37.65a-live-3/verify-results/` (gitignored, read in
the live-3 worktree). Candidate `p-31371dfb4b2b26453f818fefd311ea07be50ef8413aa9185be1ede927a773a8b`
(`sig-2026-11-25.1`, production). Deferred ids suggested below continue the
`D-P37.65a-N` series (–1…–3 exist in `docs/tickets/DEFERRALS.md`).

Verdict legend: **defect** (the code is wrong), **spec-gap** (two deliberate
contracts collide — needs an owner/spec decision, not just engineering),
**honest** (expected absence, nothing to fix), **residue** (a dead attempt's
leftover state — a recorded reconciliation, not a code bug).

---

## Finding 1 — V3 fail: `page_index.json/` top-level not allow-listed in `s/<pub>/`

**Verdict: spec-gap → legitimate new artifact family; the allow-list's
effective top-level set needs an additive entry. Not an emission defect.**

Deciding citations:

- `page_index.json` is emitted deliberately at `s/<pub>/page_index.json` by
  `ops/src/ops/site_trees.py:228-232` (`assemble_site_trees`), documented at
  `site_trees.py:17-21` as "the **withdrawal index** (J3 §8.1): route →
  embedded entity/claim/artifact ids" — consumed by
  `exports.release.apply_withdrawals` (`site_trees.py:54`). Its location under
  `s/<pub>/` is load-bearing: V10's contract reads "…`s/` and `v/` pages via
  J3 `page_index.json`" (G3 §5.5 V10 row,
  `docs/build/planning/2026-09-30-next-phase/design/G3-release-model.md:339`).
- The allow-list check computes *effective* top-level sets per namespace at
  `ops/src/ops/release_verify.py:861-870`: `allowed_v` gains
  `{"release.json","entity","compat_index.json"}`, `allowed_s` gains only
  `{"release.json"}` — `page_index.json` was never added (P36.66b's
  site-trees emit landed after the check).
- The spec's own rule, G3 §5.4 (`G3-release-model.md:316-319`): "`ops/public_routes.toml`
  applies to the top level of `v/<pub>/` and `s/<pub>/`. Added prefixes: `r/`,
  `s/`, `releases/`, `status/`, `release.json`" — the additions the release
  model names. `page_index.json` belongs in exactly this list (G3 line 633
  already records "J3 TX-13b keeps `/s/` build + `page_index` +
  `selectors.conf`"), it simply was never added to §5.4 or to the check's
  extras set.
- `ops/public_routes.toml` itself is the **wrong** place: its header contract
  is "the synced web tree" — the Astro dist's top level; `r/ entity/ conf/
  compat_index.json release.json` are deliberately NOT listed there as
  "release-pipeline namespaces — never web-build output". `page_index.json`
  is the same class (written by `assemble_site_trees`, not by the Astro
  build), so the toml edit would be a category error.

Recommended disposition — **deferral `D-P37.65a-4`** (small fix leg):
add `"page_index.json"` to the `allowed_s` extras at
`release_verify.py:866-870` (mirroring `release.json` — allow-listed, never
`required`, since it is pipeline-emitted), and record the addition in G3 §5.4's
"Added prefixes" line. Engineering-visible spec amendment; recommend the
operator confirm §5.4 may grow the entry (the allow-list edit is historically
the publish decision, SIG-OPS-003).

Blocks: V3 (one of the three V3 violations) on both origins; part of the
`blocked` suite verdict gating `D-P37.65a-1`'s live-crawl leg.

---

## Finding 2 — V3 fail: `artifact/web/presentation/jurisdiction_dossiers.json` trips the `presentation/` by-name ban in both trees

**Verdict: defect (emit side, small) — a phantom `/artifact/` route serving
`[]` for an artifact the export does not carry. The ban is working as
intended and should not change.**

Deciding citations:

- The ban: `ops/src/ops/release_verify.py:889-893` — "presentation/ is the
  fixture-export harness's demo data — banned anywhere in the publish set, by
  name"; spec'd by the G3 §5.5 V3 row (`G3-release-model.md:332`, "content
  assertions (curate banner, loopback form actions, `demo_*` slugs,
  `presentation/`)"). Its upstream twin is `ops/src/ops/publish.py:231-234`
  (`assert_export_present`): an export dir carrying `web/presentation/` is the
  "fixture-export harness's DEMO presentation data (P27.5), never national
  data" — refused as a public build input.
- The artifact's real lineage: `web/presentation/jurisdiction_dossiers.json`
  is the SIG-PUB-017 **demonstration** dossiers file the fixture harness
  writes (`web/scripts/build-fixture-export.ts:411-414`), "Deliberately demo
  content … absent → `[]`" (`web/src/lib/data.ts:2351-2357`). The real
  national export carries **no** `web/presentation/` subtree (verified:
  `exports/out/national/web/` has no `presentation/`; `manifest.json` lists 0
  `presentation` paths out of 1419 artifacts).
- Why the route still emits: `web/src/pages/artifact/[...path].json.ts:24-51`
  enumerates `fixtureArtifactPaths()` (the committed
  `web/src/lib/figure-artifacts.json`, which includes
  `web/presentation/jurisdiction_dossiers.json` at line 7) and emits a route
  for every path whose `getReleaseArtifactPayload` is non-null. The payload
  case at `web/src/lib/data.ts:3141-3144` calls
  `readPresentation<Dossier[]>("jurisdiction_dossiers", [])` — the `[]`
  fallback that exists for the dossier-LIST use (`jurisdictionDemos`,
  `data.ts:390-393`) — so an absent export file yields `[]`, non-null, and the
  route emits. This violates the route's own invariant (`[...path].json.ts:10-12`:
  "A path that is not a figure-addressable artifact emits no route (404), so
  the link set and the artifact set can never drift") and mints a `presentation/`
  path segment carrying `[]` — an orphan (no export-mode figure names it:
  `getDossierArtifactRef` returns `null` unless a demo slug matches,
  `data.ts:1065-1069`).

Recommended disposition — **deferral `D-P37.65a-5`** (small fix leg): in
`data.ts:3141-3144`, the export-mode payload read must be **nullable** —
return `null` when `<exportDir>/web/presentation/jurisdiction_dossiers.json`
is absent (the `[]` fallback is correct only for `jurisdictionDemos`); keep
the V3 ban verbatim — it caught a real demo-family residue. No spec decision
needed. Consequence worth recording: the fix changes `s/`+`v/` tree bytes →
the two dists re-build, `sites`+`stage` re-run for those namespaces (the `r/`
tree is untouched; the pub id does not change since the descriptor binds no
site-tree bytes — verify `routes_sha256` semantics in the fix leg).

Blocks: V3 (two of the three violations, both trees); part of the `blocked`
verdict gating `D-P37.65a-1`.

---

## Finding 3 — V13 fail: `API is live` line absent on 6 error pages + 4 dossier `/print/` pages (of 749,417 stamped)

**Verdict: spec-gap — two deliberate contracts collide; needs an owner/spec
decision, then a one-line change either way.**

Deciding citations:

- The check's predicate: `ops/src/ops/release_verify.py:1516-1529` — a page is
  "stamped" iff it carries `name="sig-release"` meta; every stamped page must
  render `LIVE_API_LINE` (`release_verify.py:121`,
  `'The public API also serves newer, unreleased records, labelled "live".'`;
  the docstring's contract at `1439-1444`: "the 'API is live' line is on every
  stamped page"). Spec: G3 §5.5 V13 row (`G3-release-model.md:342`, "the 'API
  is live' line") and §6.1 (`:354`, "**The stamp (every HTML page**…").
- Why the 10 pages miss it: the machine-readable stamp is unconditional —
  `web/src/layouts/BaseLayout.astro:316` emits `<meta name="sig-release">` on
  every page when a release is bound (chrome-independent), and the print
  routes emit it themselves (`dossier/[...path]/print.astro:217`,
  `entity/[type]/[key]/print.astro:101`). But the visible basis sentence lives
  in the **full-chrome footer** (`BaseLayout.astro:358-393`, gated
  `chrome === "full"`; the line itself at `:391`). The error pages are
  `chrome="minimal"` by deliberate design (`web/src/pages/{403,404,410,500}.astro`;
  prop contract `BaseLayout.astro:80-84`, P34.13/QW-11 "chrome-light"), and
  the print pages are `data-sig-chrome="print"` standalone documents whose
  running footer (`components/print/PrintChrome.astro:36-72` + the JD-08
  release sentence at `print.astro:316-325`) carries release identity but
  never the API-live basis sentence. G3 §6.1's own text is ambiguous: "The
  print stylesheet repeats it as a running footer (C2 NEW-6/NEW-23)"
  (`G3-release-model.md:361-362`) — "it" (the stamp) is repeated in shortened
  form; whether the basis sentence is part of the print form was never
  specified, and whether minimal-chrome error pages carry the footer contract
  collides with P34.13.
- Truncation nuance the ledger could not show: `live_missing[:10]` caps both
  the failures and the evidence (`release_verify.py:1527-1529`), and the
  shown misses are simply the first 10 in sorted order (`403/`…`500`, then
  `dossier/iso3166-1-{bd,be,de,gb}/print/`). The true missing count is larger:
  all 16 `iso3166-1-*` country dossiers mint print pages (`print.astro:51-57`,
  `PRINT_LEVELS`), and `entity/[type]/[key]/print.astro` is stamped with the
  same reduced `PrintChrome` footer (no slot child → no basis sentence at all)
  — the real count is likely ~22+ in `s/<pub>` alone.

Recommended disposition — **deferral `D-P37.65a-6` (owner/spec decision
first, not engineering)**: decide whether the §6.1 footer-sentence contract
binds `data-sig-chrome ∈ {minimal, print}` pages. Consistent resolutions:
(a) check-side — scope V13's live-line leg to `data-sig-chrome="full"` pages
(the attribute is already emitted: `BaseLayout.astro:265`,
`print.astro:182`); the `<meta>`/describedby pair continues to pin every page
to the release, which is the honesty half the check exists for; or
(b) emit-side — extend the basis sentence to the minimal-chrome footer and
the print running foot (a designed-surface change to P34.13 chrome and the
space-budgeted print footer — the heavier path). Adjacent spec questions for
the same decision: the s/-variant wording — G3 §6.1 (`:363-364`) says the
second sentence on `s/` pages becomes "This is the fixed copy of this page in
release sig-…; the latest view is here", but `BaseLayout.astro:388-392`
renders the latest-view basis on BOTH trees (no variant in
`web/src/lib/release-stamp.ts`); and the entire `v/` tree is **unstamped**
(the `v/` dist was built without `SIG_RELEASE_JSON` — recorded verbatim in
`docs/build/runs/WEB-EXPORT-DISTS.md` "no `release.json` bound for `v/`",
`web/src/lib/release-stamp.ts:19-26` — so V4's "every HTML page has exactly
one stamp" (`release_verify.py:985-989`) will flag all ~514k `v/` pages when
the V4 leg ever runs: the `v/` dist must be re-built bound, or the stamp
contract scoped to `r/`+`s/`+`releases/`). Both belong to this decision.

Blocks: V13 on both origins; part of the `blocked` verdict gating
`D-P37.65a-1`. The v/-stamp sub-question additionally pre-figures V4's leg.

---

## Finding 4 — stranded label `sig-2026-11-25.1` bound to `['None']`

**Verdict: defect (pipeline gap) manifesting as residue — `verb_build`
allocates the label but never binds it; `record_label_publication` is
unreachable on the ops path, so EVERY verb_build-allocated label strands at
`publication_id: null`. Attempt-2's leftover is just the first live
manifestation.**

Deciding citations:

- The registry contract: `exports/src/exports/release_identity.py:263-272` —
  `allocate_label` appends `{label, publication_id: null, state:"allocated"}`;
  `record_label_publication` (`release_identity.py:283-304`) is the documented
  "post-build fill-in" that binds `publication_id`.
- The gap: `ops/src/ops/release_pipeline.py:757-767` — `verb_build` allocates
  via `_allocate_label` (the bucket-mirror write, `:682-712`, pub=null), then
  calls `build_release(..., labels_registry=None, label=label)` (`:763`).
  `build_release` only binds when `labels_registry` is passed
  (`exports/src/exports/release.py:876-877`), so nothing binds — verified:
  `record_label_publication` has no other caller in `ops/`. `verb_promote`
  resolves the label from the staged `catalog_entry.json`
  (`release_conf.py:1198-1207`), not from `labels.json`, so it does not bind
  either.
- V2's leg: `release_verify.py:739-754` — `bound != {pub}` fails; the
  committed test fixture writes the bound shape
  (`tests/ops/test_release_verify.py:354-365`, `publication_id: pub`), i.e.
  binding IS the expected end state.
- Downstream impact beyond V2: `read_label_map` (`release_conf.py:157-172`)
  skips null-pub entries → `labels.conf` (`render_labels_conf`,
  `release_conf.py:413-420`, the label→pub 301 aliases of G3 line 170) will
  never carry `sig-2026-11-25.1 → p-31371dfb…` — the `/releases/<label>/`
  alias 404s post-promotion.
- The reconciliation is forced, not a choice: `publication_id =
  sha256(descriptor)` and the descriptor embeds `label` (SIG-REL-001,
  date-derived from `as_of_world`), so `sig-2026-11-25.1` is already
  cryptographically welded to `p-31371dfb…`. Tombstoning or allocating a new
  label contradicts the descriptor (a different label ⇒ different descriptor
  ⇒ different pub); **bind it** — a `labels.json` write under the registry
  lock. That is a registry mutation: the leg-3 ledger records "a re-bind or a
  new allocation is the registry owner's call" — the operator binds, the
  agent does not.

Recommended disposition — **deferral `D-P37.65a-7`**, two halves:
(i) machinery — `verb_build` gains the post-build bind (mirror →
`record_label_publication` → generation-matched write-back under the held
lock, the `_allocate_label` pattern at `release_pipeline.py:694-712`); plus a
test that a built label reads `publication_id == pub`.
(ii) residue — the operator binds `sig-2026-11-25.1 → p-31371dfb…` as a
recorded registry write (labels.json is in `REGISTRY_STATE_FILES`,
`release_pipeline.py:81-87` — the write shifts the state digest, so it lands
inside a window before the next verb reads it).

Blocks: V2 on both origins; part of the `blocked` verdict; and (latent) the
label-alias route post-promotion. Until the machinery half lands, every
future `verb_build` re-strands.

---

## Finding 5 — tree-mode suite OS-killed at ~576k pages (0-byte log)

**Verdict: defect (verifier memory bound) — `check_v5`'s link/referrer
accumulation is O(all link edges) although every consumer needs only ≤2
witnesses per route. Fix class: bounded-resident accumulation +
page-iteration streaming, all inside `ops/src/ops/release_verify.py`.**

Deciding citations:

- The accumulation: `release_verify.py:1055-1071` — `links: dict[str,
  set[str]]` maps every same-origin route → the set of **every** page route
  linking it (≈1.28 M pages × ~20 links → ~25 M string pairs); plus the
  parallel `containment_targets` map (`:1070-1071`) and a second full `s/`
  re-read (`:1077-1087`). Every consumer of the referrer sets takes at most a
  couple of witnesses: `sorted(from_pages)[0]` (`:1095`),
  `sorted(links[route])[:2]` (`:1114`) — the full sets are never needed.
- Secondary resident cost: `_html_files` (`release_verify.py:459-466`)
  materialises a sorted `Path` list per check across all four namespaces
  (~1.28 M entries); `check_v4`'s per-page loop (`:975-1026`) is fine on
  memory but is the recorded ~30–60 h serial-fetch wall-clock bound
  (separate, already ledger-recorded — `P37.65a-live-3.md` "Measured bounds").
- The kill signature is consistent: 0-byte stdout, no traceback, death at
  ~5.8 h in — a resident-set OS kill, not a Python exception (the driver
  records it verbatim, `verify-suite-driver.py:86-91`).

Recommended disposition — **deferral `D-P37.65a-8`** (verifier fix leg):
`check_v5` keeps ≤2 referrer witnesses per route (or one min-referrer for
`containment_targets`) — O(unique-routes) resident instead of O(edges);
`_html_files` becomes an iterator (drop the whole-corpus `sorted()`, or
sort per namespace chunk); optionally run each check in its own subprocess
for kill isolation. The serial-fetch wall-clock bound is unchanged by this —
it is the separately recorded leg bound, not this defect.

Blocks: nothing additional *immediately* — the probe legs already produced
the bounded check rows (`V2/V3/V12/V13/V14/V15`), and V1/V4/V5 are the
recorded multi-day bounds regardless. It blocks producing a **complete**
tree-mode suite result at release scale, so it gates the evidence that
`D-P37.65a-1`'s live-crawl leg is supposed to land.

---

## Summary — what gates `D-P37.65a-1` green

| # | finding | verdict | disposition | gates the leg? |
|---|---|---|---|---|
| 1 | `page_index.json/` top-level in `s/` | spec-gap → additive allow-list entry | `D-P37.65a-4` — small fix (release_verify.py:866-870 + G3 §5.4 line) | yes — V3 fail |
| 2 | `artifact/web/presentation/…` in both trees | **defect** (phantom artifact route serving `[]`) | `D-P37.65a-5` — nullable payload read (data.ts:3141-3144); re-emit dists | yes — V3 fail ×2 |
| 3 | `API is live` absent on error/print pages | **spec-gap** — owner decision needed | `D-P37.65a-6` — decide chrome scope; + adjacent s/-wording + v/-unstamped (~514k) questions | yes — V13 fail |
| 4 | label bound to `['None']` | **defect** (verb_build never binds) + residue | `D-P37.65a-7` — bind machinery + operator bind of `sig-2026-11-25.1` | yes — V2 fail |
| 5 | tree suite OS-killed ~576k pages | **defect** (V5 O(edges) accumulation) | `D-P37.65a-8` — bounded-resident check_v5 | partial — full-suite evidence leg |

- V12 pass and the V14/V15 skips are honest states, never findings.
- The second V2 refusal ("the working tree is dirty now") is the leg's own
  uncommitted ledger work — honest, self-resolving.
- Findings 1–4 all gate the `blocked` suite verdict → they gate the
  `live-crawl` leg's green. Finding 5 gates only the *complete-suite*
  evidence; the bounded probe rows stand either way.
- Re-emission consequence: fixes for findings 2, and 3(b)/the v/-stamp
  question if emit-side, change `s/`+`v/` bytes → both dists rebuild (~25–120
  min each), `sites` re-assembles, `stage` re-runs those namespaces (~800k
  objects at the measured ~99 obj/s ≈ 2.2 h); `r/`+`releases/` and the pub id
  are untouched.
