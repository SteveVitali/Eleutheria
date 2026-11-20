# NIGHTLY-RED-1 — root-cause diagnosis (read-only, 2026-11-20)

Commissioned by the orchestrator after the GATE-ACCEPT-R11 post-gate unblock; the
diagnostic context ran read-only and modified nothing. This file preserves its findings.

## TL;DR

The `replay` stage has been red since its first-ever run on main (2026-10-08, one day
after P34.7 merged): a **machinery defect, not a real invariant violation**. The committed
oracle `tests/unit/fixtures/memory_guard/replay_expected.csv` is keyed to the
*stacked-branch* first-parent line it was generated on, while the nightly replays *main's*
first-parent line (PR merge commits only). **0 of the oracle's 304 distinct commit keys
exist on main's first-parent line**, so every expectation is silently out-of-scope and
every real finding is `oracle-unexpected`. Two additional legs (`depaudit`, `npm`) are
separate, real advisory-drift failures needing dependency bumps.

## Mechanism (verified)

- `cmd_replay` enumerates `git rev-list --first-parent root..HEAD` (`memory_guard.py:4687`)
  — on main that's merge commits only (~492 judged).
- The oracle was generated on `r11/P34.7-…` (`5b41a3ae`, rows added `c83a4c1a`) where the
  fp chain is the whole stacked work chain — P34.7's own ledger records 651 judged 0/0/0.
- `oracle_compare` skips rows whose commit ∉ judged span (`memory_guard.py:4255-4256`) →
  all expectation cells inert; `missed=0`/`breached=0` vacuous; every finding → `unexpected`.
- `register_commit_map` (`memory_guard.py:4307-4324`) exists for carrier-remap but its
  `rev-list --first-parent --merges --ancestry-path` query is unreliable (returns ∅ where
  carriers exist unless w is the merge's direct second parent).
- Timeline: last green 2026-10-06; first red 2026-10-07 (depaudit/npm/recordedci, pre-replay);
  first replay red 2026-10-08 (315 unexpected); drifted to 335 by 11-20.
- Findings are real append-only/record-dates/record-shape/readouts violations on merge
  commits (e8dfcb76, 03d056e6, 0e043910, 2075f700, …) — correctly detected, wrongly keyed.

## Other legs (real, not machinery)

- `depaudit`: 26 vulns — urllib3 2.7.0 → 2.8.0 (PYSEC-2026-4175/76/77), pypdf 6.18.1 → ≥6.20.1
  (PYSEC-2026-4157/59/60), +1 pkg — pinned in pylock.toml, needs bumps.
- `npm`: 4 blocked advisories — proxy-addr GHSA-jqcg-44mw-7w3h (critical), body-parser
  GHSA-27r3-jxmh-p828, compression GHSA-vc2v-76pw-4v95, zod GHSA-mrhx-c7xc-m3w5 (all high).

## Blocking surface

Does not gate PR CI (the 5 head-bound jobs are separate). Holds `D-P34.7-1` OPEN (verify
condition unmet) and the nightly leg of `D-P34.2-2`. Named in `readouts/GATE-ACCEPT-R11.md` §3.

## Recommended repair (from the diagnostic, verbatim)

1. Fix `register_commit_map`: replace the fp+ancestry-path query with earliest merge M on
   tip's fp line satisfying `git merge-base --is-ancestor w M` (+ regression test).
2. Re-derive the oracle over main's fp line; the `source=reviewed` rows need the same
   carrier re-key (recorded bulk namespace correction — adjudications preserved).
3. Forward-maintenance rule: oracle rows keyed to carrier merges must be appended when a
   merge lands carrying findings (closeout-step or re-run).
4. Harden `oracle_compare` to report out-of-span rows (today's `missed=0` asserted nothing).
5. Bump urllib3→2.8.0, pypdf→≥6.20.1 (+1 pkg) in pylock.toml; bump or date-allow-list the
   4 npm advisories per `record_policy/npm_audit_allow.toml`.
6. Owner: a dedicated repair row (small tooling ticket — guard fix + oracle re-key + one
   observed green nightly), closing `D-P34.7-1` and the nightly leg of `D-P34.2-2`.
