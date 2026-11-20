# PR — OPS-NIGHTLY-RED-1-REPAIR — repair the `replay` machinery defect + the advisory drift

## What & why

The `nightly.yml` `replay` stage has been red since its first run on main
(2026-10-08) — and the recorded diagnosis
(`docs/build/reports/nightly-red-1-diagnosis.md`, committed `f2d0effd`,
**the spec for this PR**) proves it is a **machinery defect, not a real
invariant violation**: the committed oracle
`tests/unit/fixtures/memory_guard/replay_expected.csv` was keyed to the
*stacked branch's* first-parent line it was generated on, while the
nightly replays *main's* first-parent line (PR merge commits only) — **304
of 304 distinct commit keys out-of-span**, so every expectation was
silently skipped and `missed=0` asserted nothing. Two further legs
(`depaudit`, `npm`) were real advisory drift.

This PR lands the diagnosis's recommended repair:

1. **`register_commit_map` fixed** (`docs/build/tools/memory_guard.py`):
   the old `rev-list --first-parent --merges --ancestry-path w..tip`
   carrier query returned ∅ for any wanted commit not reachable through
   first-parent edges (i.e. every side-branch commit carried by a merge's
   second parent or deeper). Replaced with the **earliest merge M on tip's
   first-parent line whose side set `rev-list M ^M^1` names `w`** — for
   `w` off the line, `w` ancestor of M ⟺ `w` ∈ side(M). Verified carriers
   on main's line: `065d8aa0`→`b79a05c6`, `03450cb8`→`f87fcbe4`,
   `04895cdc`→`7086d2a5`, `03ac3b06`→`f79f9d2a`, `c2055d96`→`d9fa3f5d`
   (the old oracle's `e2175c93` cell — `e2175c93` is not on main's fp
   line; it was the stacked line's carrier).
2. **`oracle_compare` hardened**: expectation rows keyed to commits
   outside the judged span are collected, printed
   (`oracle-out-of-span:`), counted, surfaced in the JSON
   `disagreements["out-of-span"]`, and **fail the comparison** —
   `missed=0` can never again be vacuous.
3. **`oracle-gen` re-keys `source=reviewed` rows** through the fixed map:
   adjudications re-anchor to their commits' carrier merges on the
   re-derived line — kind/path/check/rule/source/note **preserved
   verbatim**. The bulk re-key is a **recorded namespace correction** —
   recorded here and in `runs/OPS-NIGHTLY-RED-1-REPAIR.md`, never a
   silent re-baseline.
4. **Oracle re-derived**: `oracle-gen a33177c7..origin/main` → 788 rows
   (371 derived + 417 reviewed), 132 distinct commit keys, **all
   in-span** (was 304/304 out-of-span).
5. **Dependency bumps (real, not allow-listed):**
   - `urllib3 2.7.0 → 2.8.0`, `pypdf 6.18.1 → 7.1.1`,
     `certifi 2026.7.22 → 2026.10.23` (uv lock + PEP 751 `pylock.toml`
     export; pip-audit over the tree now reports **no known
     vulnerabilities** — was 26 in 3 packages).
   - `web`: the express-chain fixes stay (`body-parser→1.20.9`,
     `proxy-addr→2.0.8`, `compression→1.8.2` — resolves the **critical**
     `GHSA-jqcg-44mw-7w3h`, `GHSA-27r3-jxmh-p828`,
     `GHSA-vc2v-76pw-4v95`). The `@lhci/cli` runner **stays at 0.15.1**
     after the head-bound web job failed twice under lighthouse 13.6.0 —
     LH13's new measurement set reports nonzero TBT on routes
     `sig.page-budgets/1` budgets at `<=0` (attempt 1: `/explore` 239 vs
     ≤200; attempt 2: `/r/_fixture-record/` 8 vs ≤0). The ceilings are
     ADR-155-generated ground — recalibrating them for LH13 is the
     operator's ADR call, not a dep-repair workaround — so instead:
     npm `overrides` pins `basic-ftp` 6.2.6 + `tmp` 0.2.7 (two of the
     four re-surfaced advisories resolved by real bumps, require-smoke +
     real `lhci collect` verified); `extract-zip` (no fixed release —
     2.0.1 is both vulnerable ceiling and latest) and chromium-bidi's
     nested `zod@^3` (fix 4.6.6 is an unsupported major) return to two
     scoped `dev-only` allow entries expiring **2027-02-20**. npm gate
     `level=high candidates=3 allowed=3 blocked=0`. The two
     `ASTRO-CHAIN-*` prod entries stand under their own tracking.

## Deferral register

- **`D-P34.2-1` → OPEN** (e1 flipped DONE on the zero-finding state,
  then e2 reopened it the same day): e1's verify — gate green with the
  entries REMOVED — stopped holding once the LH13 runner the bump
  depended on proved incompatible with ADR-155's `<=0` TBT ceilings
  (run 44676844367 attempts 1–2). The residual `extract-zip`/`zod`
  advisories retire on an upstream release or the operator's LH13
  recalibration — expiry 2027-02-20 keeps the grant loud.
- **`D-P34.7-1` — stays OPEN.** Its verify condition is a *scheduled
  nightly* reporting `judged > 0` with 0 missed / 0 breached / 0
  unexpected — owed to the first nightly after this merges, not claimed
  here.
- **`D-P34.2-2` (nightly leg) — stays OPEN**, same reason.
- Diagnosis recommendation 3 (forward-maintenance: append oracle rows
  when a merge lands carrying findings) is a standing rule — the merge
  landing this PR is itself judged on the next nightly; the local replay
  verdict is recorded honestly in the run ledger.

## Test plan

- `uv run pytest docs/build/tools/test_memory_guard.py` — **163 passed**
  (was 155; +8: the four documented carrier pairs + `c2055d96` on real
  history, a whole-main-line earliest-carrier test, a synthetic
  side-branch/in-span/no-carrier map test, an out-of-span oracle-row
  test).
- `uv run pytest tests/parsing tests/connectors/test_dossier_documents.py`
  — **177 passed** (pypdf 6→7 compatibility).
- `scripts/ci/npm_audit_gate.sh --full` — blocked=0.
- `memory_guard.py replay a33177c7..origin/main --oracle
  tests/unit/fixtures/memory_guard/replay_expected.csv` — **honestly RED
  (exit 1)**: 492 judged, oracle compare 167 missed / 91 unexpected /
  1 clean-breached / **0 out-of-span**. The machinery now reports real
  adjudication drift on main's line (decomposed in the run ledger:
  ~62+73 re-anchoring cells, ~105 born-at-merge/intra-PR-transient cells,
  the rest unadjudicated findings) — green needs a re-adjudication pass
  that is `D-P34.7-1`'s remaining substance, not a silent re-baseline.
- Head-bound CI: `a589ed1c` run 44676844367 — security ✓ docs ✓
  composed ✓ python ✓ · **web FAIL×2** (LH-TBT-EXPLORE-1 — the LH13
  measurement-drift signature above; recorded in `flake_log.csv`,
  unlisted, disposition = toolchain revert not budget smoothing). The
  closeout head re-runs green-or-real under the LH12 runner.

## Records

- `docs/build/runs/OPS-NIGHTLY-RED-1-REPAIR.md` — run ledger.
- `docs/tickets/DEFERRALS.md` — `D-P34.2-1` OPEN↔DONE↔OPEN record (old
  cells preserved).
- `docs/build/reports/obligations/events.jsonl` — `D-P34.2-1:e1` + `:e2`.
- `docs/build/LEDGER.md` — NIGHTLY-RED-1 OPEN FINDINGS line extended
  (additive).
- `docs/build/tools/record_policy/npm_audit_allow.toml` — history note +
  `LHCI-CHAIN-EXTRACT-ZIP` restored / `LHCI-CHAIN-ZOD` added (scoped,
  expiring 2027-02-20); `LHCI-CHAIN-BASIC-FTP`/`LHCI-CHAIN-TMP` stay
  retired — their advisories are resolved by the `overrides` bumps.
- `docs/build/reports/ci/flake_log.csv` — `LH-TBT-EXPLORE-1` attempt
  rows + verdict (unlisted; disposition = revert, not ceiling).

Harness: devin-desktop/swe-2-high/subagent
