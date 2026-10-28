# ADR-224 — the T1 enhancement kit's emission, admission and element roster (P36.20)

- Date: 2026-10-28
- Status: accepted
- Ticket: P36.20 (UXK0-4, manifest row 360 — on `r11/P36.20-enhancement-kit-behaviour`)
- Base: `r11/P36.19-csp-hsts-permissions-policy`
- Requirement stamps: SIG-UI-085 (the T2 set stays closed), SIG-UI-089 (every
  route classified exactly once), SIG-UI-090 (T0 ships no `<script>`),
  SIG-UI-091 (T1 JS-on/JS-off `main` parity minus `[data-enhancement]`),
  SIG-UI-039 / SIG-UI-040 / SIG-ENG-042 (cited), UXK0-4, ADR-155, ADR-223
- Supersedes: nothing — this records the first owned decision on the T1
  enhancement mechanism; the governing page-type contract it implements is
  deliberately unchanged (same budgets, same T2 set, no runtime dependency).

## Context

K0's least-power ladder puts "framework-free custom elements" third — above
React islands, below HTML/CSS — and the contract names the roster:
`<sig-table>` (sort, filter, facet chips, column chooser, "download this
view" CSV), `<sig-typeahead>` (APG combobox over static shards), `<sig-cite>`
(format restatement), plus `<sig-copy>` and `<sig-details>` from the row's
owned list. P35.50 built the admission machinery (the page-type registry and
the empty `t1-module-entries.json` allow-list) and P36.19 built the strict
CSP (`script-src 'self'` + per-page hashes, `script-src-attr 'none'`). The
question this row owned: how five framework-free modules get emitted,
admitted and upgraded without disturbing the T0/T2 boundaries, the parity
rule, the budgets, or the dependency posture.

## Decision

1. **Emission is a build hook, not an Astro asset pipeline.** The
   `sigEnhancementKit` `astro:build:done` integration bundles each
   `src/elements/sig-*.ts` with esbuild (already a build-time dependency of
   the Vite/Astro toolchain — no new runtime or build dependency) into
   `dist/_kit/sig-<name>.js`, one ESM module per element, dependency-free
   and Apache-2.0-bannered. Names are **stable and content-unhashed**:
   `t1-module-entries.json` names every admitted entry verbatim
   (`/_kit/sig-cite.js`, `/_kit/sig-copy.js`, `/_kit/sig-details.js`,
   `/_kit/sig-table.js`, `/_kit/sig-typeahead.js`), so the allow-list is a
   reviewed record, not a moving fingerprint. `_kit` is registered on the
   publish allow-list beside `_astro`.
2. **Admission is registry-gated, never template-convenient.** `BaseLayout`
   classifies the page's own path against `page-types.ts` and emits the
   three chrome modules (`sig-details`, `sig-cite`, `sig-copy` — the shared
   cite disclosure's upgrades) only on a full-chrome T1 page. Page-local
   elements name their own module beside the markup they upgrade
   (`sources.astro` for `<sig-table>`, the internal harness for
   `<sig-typeahead>`). Re-typing a route removes its scripts with no
   template edit; a T0 route can never carry one. `script-src 'self'`
   admits the `/_kit/` entries — no CSP directive, hash or exception added.
3. **Upgrade means additive DOM over complete markup.** Every element wraps
   server-rendered content and injects only `[data-enhancement]` chrome —
   the parity sweep (SIG-UI-091) subtracts it, print hides it (K14 §3.7).
   `<sig-table>` hides rows/cells with the `hidden` attribute (never
   removes DOM), wraps each `th`'s text in a sort button whose indicator is
   a `data-enhancement` span (header text is unchanged), reports
   `aria-sort`, and round-trips the view through URL parameters validated
   against the rendered model — a fabricated parameter can never invent a
   view. `<sig-typeahead>` upgrades a plain GET form into the APG combobox
   (`role=combobox`, `aria-expanded`/`controls`/`activedescendant`,
   `role=listbox`/`option`, arrows/Enter/Escape) fed by
   `sig.typeahead-shard/1` static shards, one fetch per key, cached, never
   a live-spine read — an unanswered or malformed shard yields no options
   and the form still submits. `<sig-cite>` restates the block's rendered
   citation in plain/APA/Chicago/legal from the `data-cite-*` fields only.
   `<sig-copy>` copies its wrapped anchor/text beside a JS-only status.
   `<sig-details>` opens a disclosure for a naming fragment and for print,
   then restores.
4. **The CSV carries the licences of the view it exports.** "Download this
   view" writes the visible rows/columns as CSV prefixed by `#`-comment
   provenance lines — one per distinct licence the visible rows are filed
   under, compartment-named when a row declares `data-compartment` — so a
   downloaded view never travels without the rights lines its rows carry.
5. **`<sig-activate>` is not built here.** The contract's own roster is the
   five elements above; the K0/UXK0-4 planning notes' `sig-activate`
   (click-to-activate a T2 surface) is VIZ-04's surface-activation row —
   T1 may not hydrate islands, so no element in this kit does. Recorded so
   a later reader does not treat the omission as drift.
6. **Internal harness over fixture shards.** `/enhancement-kit/` is an
   injected `SIG_BUILD_INTERNAL` route (never published, never
   allow-listed) that mounts every element over honest fixture markup plus
   a committed `sig.typeahead-shard/1` endpoint; P36.40 owns the real
   export-mode shards. The e2e suite exercises the kit there and on the
   real `/sources/` mount, including the K0 failure leg — every `/_kit/`
   module blocked leaves the page complete.

## Consequences

- T1 enhancement is now real but still opt-in per page: new elements land
  as a new `src/elements/sig-*.ts`, a new allow-list row, and a markup
  mount — each step reviewed, none silent.
- The `/_kit/` surface is bounded: five modules ≈ 15 KiB uncompressed,
  ≈ 6.6 KiB gzip in the heaviest mount (sources: trio + table), far inside
  the T1 20 KiB initial / 40 KiB post-action budgets.
- `page-types.json` remains the only route authority; `/enhancement-kit/`
  joins the T1 sweeps by classification like every other route.
- Print and reduced-motion posture held without element code: injected
  chrome is `display:none` under print; the only transition is token-bound
  (`--sig-motion-1`, which the token layer zeroes under
  `prefers-reduced-motion`).

## Alternatives considered

- **Astro `<script>` processing into `/_astro/` content-hashed assets.**
  Rejected — the T1 allow-list is an exact-src match; a moving content hash
  cannot sit in a committed allow-list without re-recording every build,
  and the script-policy check deliberately expects named entries.
- **A single bundled `sig-kit.js` for all elements.** Rejected — page-local
  admission (sources gets the table, the harness gets the typeahead) is
  clearer and cheaper than loading the whole roster everywhere; the chrome
  trio already shares BaseLayout's T1 gate.
- **`client:*` islands for the same behaviour.** Rejected — the contract is
  framework-free elements over server markup; an island would pull React
  hydration onto T1, against both the budget posture and K0's ladder.
- **Removing filtered rows from the DOM.** Rejected — removal would hide
  facts from the JS-on `main` text the parity rule compares; `hidden`
  preserves identical text and restores cleanly.
- **A global `/_kit/` loader script that imports modules on demand.**
  Rejected — an extra script hop the allow-list would have to admit anyway,
  and dynamic `import()` would make admission data-driven instead of
  markup-visible.

## Revisit trigger

- A new element needs a capability the roster does not have (e.g. a worker,
  a third-party origin, or an `unsafe-*` CSP exception) — a new ADR amends
  this emission/admission posture and, where the CSP posture moves,
  ADR-223's.
- P36.40 lands the real `sig.typeahead-shard/1` export-mode shards — the
  harness endpoint is replaced by export bytes and this ADR's fixture
  posture is amended by that row's record.
- The T1 budget or the allow-list mechanism itself changes (an ADR-155
  amendment path) — `_kit` emission and `t1-module-entries.json` move with
  it.
- A sixth element roster lands (`sig-activate` under VIZ-04, or another
  row's element) — its own ADR records its admission; this roster stays
  the record for the five P36.20 elements.
