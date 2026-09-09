## Summary

P19.1 makes the build's memory durable and its workspace coherent before any capstone work, so every
later ticket cites committed paths. It commits the ticket contracts and the non-regenerable planning
artifacts, unifies the agent scratch dirs, bootstraps an `AGENTS.md` hierarchy, and fixes three small
manifest/template defects. **No code or schema changed.**

Implements `docs/tickets/P19.1__build-memory-and-hygiene.md` (ledger T1/T3/T4/T15/T16, §4.1/§4.2/§4.7;
ADR-058). Stacked on `devin/p18-2-france-belgium` (does **not** merge, tag, or push `main`).

## What changed

- **Tickets committed (T4).** `docs/tickets/` removed from `.gitignore`; the 65 contracts committed
  (46 + `00_MANIFEST.md` + `_TEMPLATE.md` + 17 post-build P19.1–P21.9). Manifest "gitignored"
  paragraph replaced; row 25 `(32/34 detectors)` → `(all 34 detectors)` (**LD-X10**); `_TEMPLATE.md`
  `of 43` → `of N` (**LD-X11**); the two `docs/tickets/` lines removed from the **untracked**
  `.devinignore` (**LD-X09**); README pointer added to `docs/tickets/00_MANIFEST.md` + `docs/build/`.
- **Build memory under `docs/build/` (§4.7).** Promoted (copied, then scratch copies deleted):
  `PLANNING_LEDGER.md` (← `NEXT-PHASE_planning-ledger_20260908.md`), `BUILD_INDEX.md`,
  `LEDGER_DEFERRALS.md`, `SCOPING_NUMBERS.md`, `SCOPING_ID_LISTS.md`, `DECISION_MEMO.md`, plus a new
  `README.md`. `PLANNING_LEDGER.md` gets the prepended build-ledger-exception line. Personal-data scan
  clean (no emails / phone / handle patterns; artifacts quote only public officials + project ids).
- **Scratch unified (T3, §4.1).** Single gitignored `.agents/scratch/` with `ledgers/ pr/ tools/
  fixtures/ logs/ planning/` + `README.md`. 44 run ledgers **moved+renamed** to
  `implement-spec_<PXX.Y>.md` (contents untouched, invariant P1–P3; full mapping in the scratch
  README). PR/commit drafts → `pr/`, one-off scripts → `tools/`, fixtures/diffs → `fixtures/`, all 16
  `*.log` deleted; root `scratch/` removed. `planning/` keeps only the gitignored
  `sig-postbuild-build-ledger.md` (the §4.7 / §9.G-item-7 exception — never committed, never moved).
- **`AGENTS.md` hierarchy (T15).** `agent-docs` bootstrap: root `AGENTS.md` + `web/`, `db/`,
  `connectors/` + a `CLAUDE.md` `@AGENTS.md` bridge. Documents the `make check` gate, the
  `verify-gen` commit-state gotcha (**LD-X03**), RDF canonicalisation via
  `rdflib.compare.to_canonical_graph` (**LD-X07**), the frozen §47 layout, and the spec-amend path.
- **Housekeeping (T1, T16).** `git fetch` + `git branch -f main origin/main` (no checkout);
  `main == origin/main`.
- **ADR-058** + `docs/adr/README.md` index row; **risk register** Phase 19 section (`RISK-P19-01`
  personal-data scan, `RISK-P19-02` rename provenance); **traceability** build-memory section.

### `.agents/scratch/planning/` → `docs/build/` substitutions (deliverable 2)

- `docs/build/PLANNING_LEDGER.md`: `sed 's#\.agents/scratch/planning/#docs/build/#g'` — **23**
  occurrences on 21 lines rewritten; then the single deliberate build-ledger-exception line prepended.
- `docs/build/DECISION_MEMO.md`: **left unchanged** — its sole reference (§8, the `orchestrate-build`
  invocation path) is the second deliberate mention the AC allows.
- `BUILD_INDEX.md`, `LEDGER_DEFERRALS.md`, `SCOPING_NUMBERS.md`, `SCOPING_ID_LISTS.md`, `README.md`:
  **0** occurrences → no substitution.

Net: `grep -rc '.agents/scratch/planning/' docs/build/*.md` → `PLANNING_LEDGER.md:1`,
`DECISION_MEMO.md:1`, all others `0` (exactly the two deliberate mentions).

## Verification (acceptance criteria → evidence)

| AC | Result |
|---|---|
| `git ls-files docs/tickets \| wc -l` = 65 | **65** |
| `grep -c 'docs/tickets' .gitignore` = 0 | **0** |
| manifest L34–35 replaced; row 25 "all 34"; `_TEMPLATE.md` no "of 43" | all confirmed |
| `git ls-files docs/build` = the 7 named files | exactly those 7 |
| `grep -rc '.agents/scratch/planning/' docs/build/*.md` = 0 except 2 | `PLANNING_LEDGER:1`, `DECISION_MEMO:1`, rest 0 |
| root `scratch/` gone; 6 subdirs exist; `ledgers \| wc -l` = 44, all match `implement-spec_P[0-9][0-9]\.[0-9]\.md`; `planning` = build-ledger only; `*.log` = 0; no scratch in `git status` | all confirmed |
| root `AGENTS.md` contains `make check`, `verify-gen`, `BUILD.sh`, `docs/tickets/`, `docs/build/`, `.agents/scratch/` | all present |
| agentic: 5 AGENTS.md claims accurate vs `Makefile`/`README` | check target, `test=uv run pytest`, `test-db` image+`SIG_REQUIRE_DB_TESTS`, `verify-gen` diff, TS-confined-to-web — all verified |
| `git rev-parse main == origin/main`; branch still P19.1 | equal (`2f4e9e5`); on `devin/p19-1-build-memory-and-hygiene` |
| `ADR-058-*.md` with 4 header fields + `## Revisit trigger`; adr/README lists it | confirmed |
| **Phase gate:** `make check` green; `verify-gen` clean; RISK-P19-01/02; traceability section | `make check` **2365 passed**, exit 0 |

## Deviations

- **Test count is 2365, not the ticket's literal 2363 / the operator's 2364.** The delta is exactly
  the mandated **ADR-058**: `tests/unit/test_policy_adrs.py::test_every_adr_names_a_revisit_trigger`
  is parametrized over `docs/adr/ADR-*.md`, so a new ADR adds one case. No code changed and nothing
  regressed — the required deliverable and the "unchanged count" AC are simply not simultaneously
  satisfiable; the ADR is the non-negotiable deliverable. verify-gen byte-clean; all suites green.
- **`docs/adr/README.md` index** had no rows for ADR-056/057 (a pre-existing omission from P18.1/P18.2;
  Appendix-F reconciliation is P20.2's scope). Only ADR-058's row was added here.
- The `agent-docs` freshness detector reports 4 "critical" refs to `docs/build/*.md` as missing — a
  **false positive**: its `find … -not -path '*/build/*'` exclude matches our `docs/build/` dir. The
  files exist, are git-tracked, and the references are accurate.

Requirement ids stamped: **SIG-ENG-001, SIG-ENG-003, SIG-ENG-012, SIG-ENG-031**. Planning refs:
T1, T3, T4, T15, T16; LD-X03, LD-X07, LD-X09, LD-X10, LD-X11.
