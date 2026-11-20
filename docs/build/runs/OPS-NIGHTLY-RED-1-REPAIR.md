# Run ledger — OPS-NIGHTLY-RED-1-REPAIR — repair the `replay` machinery defect + the advisory drift

- **Harness:** devin-desktop/swe-2-high/subagent
- **Scope:** tooling repair + records — the `memory_guard.py replay` machinery
  defect diagnosed by `docs/build/reports/nightly-red-1-diagnosis.md`
  (committed `f2d0effd`), the committed oracle's re-derivation over main's
  first-parent line, and the two real advisory-drift legs (`depaudit`,
  `npm`). No gate-affecting record touched; nothing signed.
- **Spec:** `docs/build/reports/nightly-red-1-diagnosis.md` — the recorded
  diagnosis is the spec; its key claims were re-verified in-repo before
  building on them (see §Verification).
- **Base / branch:** `f2d0effd` (chain tip) → `r11/ops-nightly-red-1-repair`
  (PR base `r11/P38.3c-round11-integration-plan-2`).
- **Started:** 2026-11-20 (`date -u`)
- **Closed:** 2026-11-20 (`date -u` at closeout — see §Heads)

## What the diagnosis claimed vs what the repo shows (verified)

- `register_commit_map`'s carrier query
  `rev-list --first-parent --merges --ancestry-path w..tip` **does return ∅
  where carriers exist**: `065d8aa0` (carrier `b79a05c6`), `04895cdc`
  (`7086d2a5`) both returned empty while `merge-base --is-ancestor` confirms
  ancestry. It only surfaces a carrier when `w` is reachable through
  first-parent edges — `03ac3b06`→`f79f9d2a` (direct second parent) and
  `03450cb8`→`e2175c93` (on `e2175c93`'s own fp chain — the *stacked* line)
  worked, which is why the defect went unnoticed at oracle-gen time.
- `e2175c93` is **not** on main's first-parent line — it was the carrier on
  the stacked branch's line. On main's fp line the carriers are:
  `065d8aa0`→`b79a05c6` (PR #135), `03450cb8`→`f87fcbe4` (PR #148),
  `04895cdc`→`7086d2a5` (PR #178), `03ac3b06`→`f79f9d2a` (PR #159), and the
  old oracle's `e2175c93`-keyed cells (register commit `c2055d96`) →
  `d9fa3f5d` (PR #108).
- The old oracle's 304 distinct keys were all off main's fp line → every
  expectation silently out-of-span, `missed=0` vacuous, every real finding
  `oracle-unexpected`. Confirmed before regeneration.
- `depaudit`: the audit names **3** packages, 26 vulns — `urllib3 2.7.0`
  (PYSEC-2026-4175/76/77 → 2.8.0), `pypdf 6.18.1` (PYSEC-2026-4157/59/60 +
  CVE-2026-1137xx/1155xx/1192xx → ≥6.21.4 clears all), `certifi 2026.7.22`
  (PYSEC-2026-4320 → ≥2026.10.18 — the "+1 pkg").
- `npm`: 4 blocked advisories, all via the `@lhci/cli` dev toolchain.

## What this run lands

1. **`register_commit_map` rewrite** (`docs/build/tools/memory_guard.py`):
   the carrier is the earliest merge M on tip's first-parent line whose
   **side set** `rev-list M ^M^1` names `w` — for `w` not on the line,
   `w` ancestor of M ⟺ `w` ∈ side(M), so walking the fp merges oldest-first
   finds the earliest carrier with no per-pair `merge-base` probe and no
   `--ancestry-path` fragility. A wanted commit with no carrier in span
   stays keyed to itself and reports out-of-span loudly (below).

2. **`oracle_compare` hardened** (`memory_guard.py`): oracle rows keyed to
   commits outside the judged span are collected, printed as
   `oracle-out-of-span:` rows, counted in the summary, surfaced in the
   JSON `disagreements["out-of-span"]`, and **fail the comparison**
   (`EXIT_VIOLATIONS`) — `missed=0` can never again be vacuous. The oracle
   must name only cells the span judges; an unjudgeable expectation is
   drift, not a skip.

3. **`oracle-gen` re-keys `source=reviewed` rows** through the same
   `register_commit_map`: an adjudication re-anchors to its commit's
   carrier merge on the re-derived line — kind/path/check/rule/source/note
   preserved verbatim. The bulk re-key is a recorded namespace correction
   (this ledger + the PR body), never a silent re-baseline.

4. **Oracle re-derived** (`oracle-gen a33177c7..origin/main`): 788 rows
   (371 derived + 417 reviewed), 132 distinct commit keys, **all in-span**
   (0 out-of-span — was 304/304 out-of-span). Reviewed adjudications
   preserved verbatim; e.g. the `e2175c93` cell family re-keyed to
   `d9fa3f5d`, the `03450cb8` family to `f87fcbe4`.

5. **Dependency bumps (depaudit leg):** `uv lock --upgrade-package` →
   `urllib3 2.7.0→2.8.0`, `pypdf 6.18.1→7.1.1`, `certifi 2026.7.22→2026.10.23`;
   `pylock.toml` regenerated via `uv export` (PEP 751). pip-audit over the
   exported tree: **No known vulnerabilities found** (was 26).

6. **npm advisory leg — real bumps, no allow-list additions:**
   `@lhci/cli 0.15.1 → 0.16.1` (devDependency, exact pin): lighthouse
   12.6.1→13.6.0, puppeteer-core→25.18.1, compression→1.8.2 fixed
   `GHSA-vc2v-76pw-4v95` and `GHSA-mrhx-c7xc-m3w5` (zod via chromium-bidi);
   `npm audit fix --package-lock-only` resolved `body-parser→1.20.9` and
   `proxy-addr→2.0.8` inside express 4.22.3's own `~` ranges, fixing
   `GHSA-27r3-jxmh-p828` and `GHSA-jqcg-44mw-7w3h` (the critical one).
   Gate: `level=high candidates=0 blocked=0`. The three `LHCI-CHAIN-*`
   allow-list entries covered no current finding after the bump — removed
   (a dead grant is a permanent silencer; history note added to the file's
   header). The two `ASTRO-CHAIN-*` prod-scope entries were already dormant
   before this run — left standing under their own tracking rows.
   → **superseded at closeout** — see *Post-CI correction* below: head-bound
   web failed under LH13's measurement drift on ADR-155's `<=0` TBT
   ceilings, so the runner reverted to `@lhci/cli` 0.15.1; basic-ftp/tmp
   stayed resolved via npm `overrides` (6.2.6 / 0.2.7), and only the two
   genuinely unfixable advisories (extract-zip ×2 — no release exists;
   chromium-bidi's nested `zod@^3` — the 4.6.6 fix is an unsupported major)
   returned to scoped `dev-only` entries expiring 2027-02-20.

7. **`D-P34.2-1` → DONE** (verify genuinely met): the row asks for the
   `@lhci/cli` audit-runner chain's four `dev-only` advisories to retire —
   verify: `scripts/ci/npm_audit_gate.sh --full` green **with the entries
   REMOVED** ✓ and `npm --prefix web audit --json` shows the chain gone ✓
   (basic-ftp/extract-zip/tmp report no finding). `obligation_events`
   appended `D-P34.2-1:e1` (OPEN→DONE); the DEFERRALS status cell flips
   with the evidence recorded.
   → **superseded at closeout:** the flip was premature — e1's verify
   ("gate green with the entries REMOVED") stopped holding once the LH13
   toolchain proved incompatible with the generated budgets; `D-P34.2-1:e2`
   (DONE→OPEN) and the DEFERRALS cell now carry the reopened state and the
   residual's three retirement paths.

8. **Regression tests** (`docs/build/tools/test_memory_guard.py`, +8):
   the four documented failure cases + the `c2055d96` re-key against real
   history (skip on shallow clones), a whole-main-line earliest-carrier
   test, a synthetic side-branch/self/no-carrier map test, and an
   out-of-span oracle-row test (fails + reports). Suite: 163 passed
   (was 155).

## Deferred obligations

- **`D-P34.2-1` → OPEN** (e1 DONE → e2 reopened) — see §7 above and the
  Post-CI correction: the residual extract-zip/zod advisories sit under
  scoped `dev-only` entries expiring 2027-02-20 until an upstream release
  or the operator's ADR-155 LH13 recalibration retires them.
- **`D-P34.7-1` — left OPEN, honestly.** Its verify needs the first
  scheduled nightly carrying the `replay` stage to show `judged > 0` with
  0 missed / 0 breached / 0 unexpected — that run only exists after this
  PR merges and the cron fires; a local green replay is evidence *toward*
  it, never the observation itself.
- **`D-P34.2-2` (nightly leg) — left OPEN, honestly.** Same reason: the
  first nightly `--all` recorded-CI sweep needs a real scheduled run.

## Local replay leg (the honest verdict)

`python3 docs/build/tools/memory_guard.py replay a33177c7..origin/main
--oracle tests/unit/fixtures/memory_guard/replay_expected.csv
--json /tmp/memory-replay-main.json` — **RED, exit 1, honestly reported**:
492 commits judged, 110 with violations, 7 vacuous (commits touching no
guarded path — `all_vacuous` false); oracle compare: **167 missed,
91 unexpected, 1 clean-breached, 0 out-of-span**. The machinery now does
exactly its job — every expectation is in-span (the out-of-span hardening
reports `0`, where the old oracle had 304/304 inert), the comparison is
non-vacuous, and the residual is *real adjudication drift on main's line*,
decomposed:

- **Re-anchoring drift (~62+73 cells):** 62 of the 167 missed cells have
  their `(path,check)` flagged at a *different* merge, and 73 of the 91
  unexpected cells match a missed `(path,check)` elsewhere (+14 more under
  a `check=*` row). Per-commit findings judged on the stacked line surface
  at different cells when whole PRs collapse into single merge diffs —
  e.g. `P20.2__spec-reconciliation.md` append-only adjudicated at
  `c73ccc60` (PR #55's carrier) is flagged at `015e1b28` (PR #53's merge,
  where the `[append-position]`/`[frozen]` markers actually land on main).
- **Cells that cannot reproduce (~105 missed):** intra-branch transient
  violations on files **born whole at merges** — `runs/P31.19.md`,
  `runs/P32.7.md`, `pr/P32.7.md`, ADRs, `BUILD_INDEX.md` — a new file
  cannot violate append-only, and a violation introduced-then-fixed
  inside a PR leaves no trace in the merge's net diff (e.g. `e8dfcb76`'s
  `P24.5.md` — the nightly's old `oracle-unexpected` signature — is now
  expected-keyed and judged clean at the merge).
- **Unadjudicated main-line findings (the rest) + 1 clean-breach:**
  findings no register/reviewed row names (`f24313dd`'s derived `clean`
  cell on `tickets/P27.8` is breached — a register-vs-judge disagreement).

**Residual nightly risk, stated plainly:** the nightly stays red after
merge — the replay leg will report these named disagreements instead of
the old keyed-wrong noise. Green needs a *re-adjudication pass* over the
~258 cells (re-anchor drift cells to the merges where their cells are
flagged; recorded withdrawals for cells that cannot reproduce; review
rows for the genuinely unadjudicated findings) — that is `D-P34.7-1`'s
remaining substance and it stays OPEN. Silently dropping reviewed rows or
auto-covering findings was expressly out of scope (no re-baseline, no
benign-by-default). The merge landing this PR is itself judged on the
next nightly (forward-maintenance, diagnosis recommendation 3).

## Guards

| check | result |
|---|---|
| `memory_guard.py all --staged` | 0 violations (529 items evaluated) |
| `scripts/docs/check-build-memory.sh .` | clean — known legacy `~` warnings only |
| `obligation_events.py check` | green — 4 known stale-ref warnings (SIG-CHART-006/007, SIG-ENG-020, SIG-EPIS-001), 798 events, 515 assessments |
| `pytest docs/build/tools/test_memory_guard.py` | 163 passed (was 155; +8 regression tests) |
| `pytest tests/parsing tests/connectors/test_dossier_documents.py` | 177 passed (pypdf 6→7 compat) |
| `make verify-gen` | `pylock.toml` + `ontology/generated` regenerate byte-identical (staged) |
| `scripts/ci/npm_audit_gate.sh --full` | at-open `level=high candidates=0 blocked=0` (0.16.1 tree); **post-correction `candidates=3 evaluated=3 allowed=3 blocked=0`** — extract-zip ×2 + zod under scoped 2027-02-20 entries; basic-ftp/tmp cleared by override bumps |
| `pip-audit` (exported tree, py3.12) | No known vulnerabilities (was 26) |
| `memory_guard.py replay a33177c7..origin/main --oracle …` | **exit 1 — 167 missed / 91 unexpected / 1 clean-breached / 0 out-of-span** (§Local replay) |

## Heads / CI

- `a589ed1c` — **ci: run 44676844367** (`gh pr checks 543`): security 39s ✓
  · docs 2m25s ✓ · composed 4m23s ✓ · python 23m55s ✓ · **web attempt-1
  FAIL → attempt-2 FAIL** (both recorded as `LH-TBT-EXPLORE-1` in
  `flake_log.csv`, unlisted — see Post-CI correction).

## Post-CI correction (2026-11-20 — the npm leg's closeout)

Head-bound web run 44676844367 failed twice under lighthouse 13.6.0 —
attempt 1 on `/explore/index.html` TBT 239 vs ≤200 (all three runs over),
attempt 2 on `/r/_fixture-record/index.html` TBT **8 vs ≤0** (`/map` warn
only). Under LH 12.6.1 the `<=0`-budgeted routes measured exactly 0; the
8–28% nonzero readings are LH13's new measurement set (the
`uses-long-cache-ttl`→`cache-insight` rename surfaced in-log), systematic
on the runner, not noise — and **not** a flake to absorb. The ceilings
are `sig.page-budgets/1` (ADR-155) ground generated by `gen-lhci.mjs`;
raising them needs an ADR amendment — the operator's recalibration call,
outside this repair. Disposition taken: `@lhci/cli` back to the
LH12-calibrated 0.15.1 (`lighthouse` resolves 12.6.1 — verified by a real
`lhci collect` against a local page: Chrome launched, full audit pipeline
clean); `overrides` pins `basic-ftp` 6.2.6 / `tmp` 0.2.7 (require-smoke on
get-uri/tmp/external-editor clean) resolving two of the four re-surfaced
advisories by real bumps; `extract-zip` (no fixed release — 2.0.1 is both
ceiling and latest) and nested `zod@^3` under chromium-bidi (fix 4.6.6 is
an unsupported major) returned to scoped `dev-only` allow entries
expiring 2027-02-20 with `D-P34.2-1` reopened for the residual. In-range
express fixes (body-parser 1.20.9, proxy-addr 2.0.8, compression 1.8.2)
stand — the critical `GHSA-jqcg-44mw-7w3h` stays resolved. The
`LHCI-CHAIN-BASIC-FTP`/`LHCI-CHAIN-TMP` entries stay removed (dead
grants); `LHCI-CHAIN-EXTRACT-ZIP` restored + new `LHCI-CHAIN-ZOD`.

**Second correction (run 44692468552, head `1c658faa`):** the LH12
revert fixed the TBT `<=0` drift but exposed the *other* floor — the
check:perf leg failed `largest-contentful-paint` on five routes, both
attempts consistent: `/` 1661.2–1661.5 (over its D-P36.64-2 recorded
bound ≤1600), `/releases` 1510.4, `/research-dossier/okc-alpr` 1511.9,
`/entity` 1507.8, `/coverage-metrics` 1506.9 (over ratified ≤1500).
Diagnosis verified stepwise: (a) my regenerated lockfile had drifted
three measurement-path transitives vs f2d0effd's known-green tree —
`chrome-launcher` 1.2.3→**pinned 1.2.1**, `puppeteer-core/ws` 8.23.0→**8.21.3**,
`ws`→**7.5.13** via scoped `overrides` (the lhci subtree now resolves
~identically to f2d0effd's); (b) the emitted bytes are identical —
astro/vite/esbuild/preact all match f2d0effd's lock and `web/` is
untouched; (c) a local `lhci autorun` on the pinned tree reproduces the
floor (~1,656 on `/`, ~1,504–1,510 fleet) — the D-P36.48-1 "shared ~1.5 s
first-paint floor" (TTFB ≈452 + render-delay ≈1,055, LCP≡FCP) now holds
previously-unrecorded routes — Chrome/lab-floor drift on the runner
image, not content, not the LH-LCP-MARGINAL noise class (both attempts +
local agree). Disposition — the sanctioned **measured-gap accommodation**
(ADR-230, the same mechanism P36.48/P37.61 used): four unscoped `lcpMs`
rows bound at 1,600 under D-P36.48-1; `/` re-recorded 1,661→bound 1,750
under D-P36.64-2; ratified ceilings untouched (warn-level), stale-row
fails. `flake_log.csv` rows LH-LCP-FLOOR-1. Residual risk: the export +
national legs' distinct T0 routes (`/r/_fixture-record`, `/dossier/ok*`)
are unmeasured this round — if they read over, they record under the same
deferral next cycle, never absorbed.

The closeout head's CI is a fresh verdict; `Harness:
devin-desktop/swe-2-high/subagent` trailers throughout.

## Final head-bound verdict (run 44806837553 @ `0b5f8f4f`, completed 2026-11-20T20:54Z)

- `security` ✓ · `docs` ✓ · `composed` ✓ · **`web` ✓ (attempt-1, no
  rerun)** · `python` ✗ — run conclusion `failure` on the python leg
  alone.
- **web green end-to-end:** all three generated Lighthouse matrices
  passed on the first attempt — zero error assertions, warnings only.
  Main matrix: `/` LCP 1,507.5 (warn ≤1,500; inside the 1,750 recorded
  bound), `/search/` 1,507.7 (warn), `/map/` TBT 503 (warn ≤350 — the
  pre-existing warn-level class); the four recorded gap routes
  (`/releases/`, `/research-dossier/okc-alpr/`, `/entity/`,
  `/coverage-metrics/`) produced **no warnings** — under even the
  ratified 1,500 this run; all `<=0` TBT legs held. The export-mode leg
  (`/r/_fixture-record` `<=0` TBT held — the unmeasured-route residual
  named above cleared) and the national matrix both green. Both
  toolchain families are satisfied on identical
  bytes: the LH12.6.1-pinned measurement path (chrome-launcher 1.2.1 +
  puppeteer-core/ws 8.21.3 + ws 7.5.13 overrides) restored the `<=0` TBT
  semantics, and the ADR-230 measured-gap rows bound the D-P36.48-1/
  D-P36.64-2 first-paint floor — ratified 1,500 ceilings untouched
  (warn-law). `flake_log.csv` success rows recorded against
  `LH-TBT-EXPLORE-1` + `LH-LCP-FLOOR-1`.
- **`python` failed on a base-branch fixture wall-clock — external to
  this head.** `tests/ops/test_release_verify.py::test_verb_verify_tree_p_mode_gates_unpromoted_namespaces`
  asserts `non_pass == {"V5"}` but now also reports P1 freshness:
  `latest=p-8494c9860dff… · age=35.34d · gen=2`. The fixture's frozen
  `activated_at` (`T0 = 2026-10-16T12:00Z`, test line 45) crossed the
  spec's P1 "release age < 35 days" bound (`release_verify.py:111`) at
  **2026-11-20T12:00Z — today**. Corroborated on the base branch's own
  python job `136480253141` (run `44791503380` @ `943d428a`, age=35.27d
  ~97 min earlier — the delta is wall clock). Deterministic, monotonic,
  not runner noise, unrelated to this diff; no same-head rerun burned
  since it cannot clear. **Every tree is red on this leg until a
  freeze/advance lands on base** — recorded `PY-T0-FRESHNESS-1`
  (unlisted) in `flake_log.csv`; the fixture repair is its own row, out
  of this repair's scope.
- `D-P34.7-1` and the nightly leg of `D-P34.2-2` stay **OPEN** — this
  was PR CI, not a scheduled nightly. `D-P34.2-1` stays OPEN pending the
  LH13 recalibration / upstream advisory fixes.

**Records-head confirmation (run 44817840719 @ `b2ab92fa`, completed
2026-11-20T22:27Z):** the records-only head concluded exactly as
predicted — `security`/`docs`/`composed`/`web` ✓ (web green a **second
consecutive** head-bound run, attempt-1: J1–J10 journeys, visual grid,
national + export matrices all clean — the toolchain + measured-gap
shape is stable, not a one-run marginal) · `python` ✗
`PY-T0-FRESHNESS-1` at age=35.39d — the third point on the monotonic
wall-clock line (35.27 base → 35.34 → 35.39). No same-head rerun burned
on either head: the failure is deterministic and cannot clear until the
fixture's frozen `T0` is advanced/frozen-clock on base.

**Second records-head run 44829211043 @ `4bf2b5cf` (completed
2026-11-20T23:17Z):** identical shape — `security`/`docs`/`composed`/
`web` ✓ (**third consecutive** head-bound web green, attempt-1) ·
`python` ✗ `PY-T0-FRESHNESS-1` at age=35.44d (fourth monotonic point).
Tail-recording stops here: each further records commit spawns a run
with the same deterministic verdict — the next head's python-failure
row is owed to `flake_log.csv` by whatever lands next.
