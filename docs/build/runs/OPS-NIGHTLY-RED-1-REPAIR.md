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

7. **`D-P34.2-1` → DONE** (verify genuinely met): the row asks for the
   `@lhci/cli` audit-runner chain's four `dev-only` advisories to retire —
   verify: `scripts/ci/npm_audit_gate.sh --full` green **with the entries
   REMOVED** ✓ and `npm --prefix web audit --json` shows the chain gone ✓
   (basic-ftp/extract-zip/tmp report no finding). `obligation_events`
   appended `D-P34.2-1:e1` (OPEN→DONE); the DEFERRALS status cell flips
   with the evidence recorded.

8. **Regression tests** (`docs/build/tools/test_memory_guard.py`, +8):
   the four documented failure cases + the `c2055d96` re-key against real
   history (skip on shallow clones), a whole-main-line earliest-carrier
   test, a synthetic side-branch/self/no-carrier map test, and an
   out-of-span oracle-row test (fails + reports). Suite: 163 passed
   (was 155).

## Deferred obligations

- **`D-P34.2-1` → DONE** — see §7 above.
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
| `scripts/ci/npm_audit_gate.sh --full` | `level=high candidates=0 blocked=0` |
| `pip-audit` (exported tree, py3.12) | No known vulnerabilities (was 26) |
| `memory_guard.py replay a33177c7..origin/main --oracle …` | **exit 1 — 167 missed / 91 unexpected / 1 clean-breached / 0 out-of-span** (§Local replay) |

## Heads / CI

Recorded at PR open + at verdict (`gh pr checks`), in §Heads of
`docs/build/pr/OPS-NIGHTLY-RED-1-REPAIR.md` and the post-closeout record.
`ci:` verdict lands at the next record entry. `Harness:
devin-desktop/swe-2-high/subagent` trailers throughout.
