# ADR-250 — The current-state projection leaves the commit path: generated on demand, verified from a temp dir (P37.61c)

- Date: 2026-11-16
- Status: accepted (engineering; records/CI posture only — no control-state writes)
- Ticket: P37.61c (Round 11 / P37, sub-round 11D, manifest row 489c — on `r11/P37.61c-projection-out-of-commit-path`)
- Base: `r11/P37.61b-privacy-redaction-restore` (`62a1fd56`)
- Authority: operator **RULING E-2**, recorded verbatim in
  `docs/build/LEDGER.md` GATE DECISIONS (2026-11-15, channel interactive)
  and `docs/build/readouts/RULINGS-2026-11-15.md`
- Amends: ADR-126 (the committed-output half of `input-manifest/1` +
  `current-projection/1` only — the schemas, the input set, the bounded
  report and the advisory boundary are unchanged)

## Context

ADR-126 made the deterministic current-state projection a **committed**
artifact under `docs/build/reports/current/`, and P34.9 (B4 V9) wired
`current_projection.py verify` into the `docs` CI job as a freshness
gate. That coupling made every records commit — a PHASE LOG line, a
BUILD_INDEX row, a closeout — carry a projection regeneration in the same
change, because the committed output is a hash of its inputs and the
inputs are the records themselves. The failure mode arrived on schedule:
P33.1's gap analysis found the committed projection drifting on the
landed tip; P35.19's phase-log notes record docs-red pairs where a
closeout append invalidated a just-committed regeneration; and every
ticket's closeout paid a second "regenerate + re-verify" leg that proved
nothing — the check judged whether a generated file was committed fresh,
not whether the records were true.

The projection's value is the *verdicts*, not the committed bytes:
`generate` fails on unresolved inconsistencies and `verify` owns the
landing-ref check (an obligation landing naming no chain/BACKLOG row)
and the uncovered-new-input check. On a temp dir, "committed output
drifted" is tautologically absent — the gate keeps every semantic check
and drops only the bookkeeping one.

The operator's RULING E-2 (2026-11-15) settles the direction: stop
committing the generated projection and stop gating every records commit
on its freshness. This ADR records the amendment and the reader
dispositions the ruling required.

## Decision

1. **The projection output is no longer committed.** `docs/build/reports/current/`
   (14 files — `CURRENT.md`, `adrs.md`, `coverage-1..5.md`,
   `current.json`, `domains.md`, `funnel.md`, `manifest.json`,
   `obligations.md`, `receipt.json`, `return-pass.md`) is removed from
   the tree in one commit. The path is gitignored so a bare local
   `generate` writes scratch output that never dirties the index. All
   input files (`docs/build/reports/obligations/`, the ledgers, tickets,
   ADRs, readouts, run ledgers) are kept and stay committed.
2. **CI regenerates + verifies into a temp dir.** The `docs` job's
   projection step and `make docs-check-projection` run
   `current_projection.py generate --out <tmp> && current_projection.py
   verify --out <tmp>` — failing on generation failure, unresolved
   inconsistencies, landing-ref violations, uncovered new inputs and the
   CURRENT.md budget, never on "committed output drifted". The docs job
   uploads the generated output as a workflow artifact
   (`current-state-projection`, `actions/upload-artifact@v7`).
3. **Agents run `generate --out <tmp>` locally** when they need the view
   (`--out` defaults to `docs/build/reports/current/`, now gitignored
   scratch — the committed-orientation-view reading is retired).
4. **Every reader repointed**, per the ruling's sweep
   (`git grep -n "reports/current\|current\.json\|CURRENT\.md"` across
   tools, tests, workflows, AGENTS.md, OPERATING_MODE_R11.md and
   dispatch templates; `perf_reuse.py`; `memory_guard.py`'s policy):
   - `.github/workflows/ci.yml` — the `docs` job's
     `current_projection.py verify` step → `make docs-check-projection
     PROJ_OUT=${{ runner.temp }}/current-projection` + the artifact
     upload.
   - `Makefile` — `docs-check-projection` → temp-dir
     `generate && verify` (`PROJ_OUT` override; `mktemp -d` default).
   - `AGENTS.md` (root) — build-memory paragraph + `Do` item repointed
     to the on-demand view; `reports/current`/`CURRENT.md` tokens kept
     honest to the new posture.
   - `tests/AGENTS.md` — `reports/current/` dropped from the living-path
     enumeration.
   - `docs/build/README.md` — `reports/` description repointed
     (generated on demand, never committed).
   - `docs/build/reports/OPERATING_MODE_R11.md` — orient step O4 and the
     closeout regen instruction repointed to the temp-dir leg.
   - `docs/build/tools/record_policy/living_records.toml` — the
     `docs/build/reports/current/*` living glob removed (the path is no
     longer a committed record); the pinned example in
     `docs/build/tools/test_living_record_lint.py` repointed to
     `reports/obligations/*`.
   - `connectors/src/connectors/personal_id_rekey.py` — the dead
     `CURRENT_PROJECTION` constant naming the removed path deleted (the
     rekey is a one-time executed operation; a re-run regenerates via
     `generate --out <tmp>`).
   - `docs/build/tools/current_projection.py` — module docstring
     repointed (output is generated on demand, never committed; `verify`
     unchanged — it still owns stale-input, drift, budget,
     inconsistency, landing-ref and uncovered-input checks against the
     `--out` dir).
   - `scripts/ci/perf_reuse.py` — **verified, unchanged**: `docs/build/`
     minus `docs/build/tools/` is already records; no per-path rule
     needed.
   - `docs/build/tools/record_policy/history.policy` — the removal
     declared as a sanctioned deletion (`seed-commit <sha>` of the
     removal commit, the `427c5efb` precedent — a later commit in the
     same PR); the L798/L1236 comments left verbatim (they describe a
     historical mechanism correctly).
   - Historical records left verbatim (dated, never readers of the live
     path): `docs/build/COVERAGE_MATRIX.csv` evidence cells,
     `docs/governance/identifier-rekey-note.md`, `CAPSTONE_*`,
     `docs/build/planning/**`, `docs/build/reports/DOCS_REFRESH_REPORT_R10.md`,
     `docs/build/readouts/RULINGS-2026-11-15.md`, landed ADR bodies
     (ADR-126/146/148), run ledgers, PHASE LOG, BUILD_INDEX.
5. **`memory_guard`/`history.policy` treats the removal as a declared,
   sanctioned deletion** — `docs/build/reports/current/*` classifies to
   no protected record class (not a ledger/deferrals/readout/index/
   manifest/digest/jsonl/adr/contract/runpr/policy-ao path), so the
   deletion is clean under BM-HIST-01; the `seed-commit` declaration
   records the sanction explicitly per the ruling.

## Consequences

- A records-only change no longer requires a projection commit —
  `make docs-check` and the `docs` job stay green without one.
- The orientation view is still one command away and still bounded:
  `generate` fails nonzero on unresolved inconsistencies; `verify` still
  fails on stale recorded digests, missing/uncovered inputs, landing
  refs naming no chain row, and the CURRENT.md budget — all judged
  against the `--out` dir.
- The CI artifact makes the generated view reviewable per run without a
  checkout.
- `docs/build/reports/current/` is the only generated subtree removed;
  every other generated surface (ontology, spec, indexes, BACKLOG.md)
  stays committed.

## Alternatives considered

- **Keep the committed file, weaken `verify` to a warning.** Rejected:
  an advisory-in-name freshness gate still forces the regen commit to
  keep the artifact honest; the ruling removes the commit-path coupling
  itself, not the severity knob.
- **Commit only `CURRENT.md`.** Rejected: the same drift coupling
  survives — any input change still invalidates the committed bytes.
- **Move the output under `docs/build/logs/` only.** Rejected as the
  convention for local runs: `--out` already parameterises the
  destination; `docs/build/reports/current/` gitignored is the
  documented scratch default (a bare `generate` still lands somewhere
  sensible), while CI uses `runner.temp`.

## Revisit trigger

- **A control-authority cutover (`D-R10-MEMORY-1`):** if the projection
  ever becomes the authority rather than an advisory view, the
  single-writer cutover re-decides where its output is canonical —
  revisit this ADR in that ADR.
- **A second committed copy of the view:** any mechanism that re-commits
  generated projection bytes (a committed CURRENT.md mirror, a records
  file derived from the projection) recreates the drift-gate defect this
  ADR removes — reject it or record the change here first.
- **CI temp-dir leg weakens:** if the `docs` leg ever stops running
  `verify` (e.g. generate-only), the landing-ref and uncovered-input
  checks lose their gate — restore `generate && verify` or record the
  narrowing in a new ADR.
