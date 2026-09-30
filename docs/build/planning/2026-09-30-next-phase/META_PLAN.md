# SIG next phase (Round 11) — META-PLAN: the plan for the plan

> **Status: APPROVED (GATE-M signed 2026-09-30T16:16Z) — the Stage-P planning ledger.** Authored
> 2026-09-30T16:05Z (`date -u`) by Claude Code (Opus 5.5) at chain tip `b051732c` / `origin/main` `b7c9e2e3`.
> Lives in the isolated planning worktree `/Users/stevenvitali/Eleutheria-next-phase` on branch
> `claude/next-phase-planning` (forked from `b051732c`). This document **does not** advance
> `docs/build/LEDGER.md`, sign or pre-answer any build gate, amend the spec, or open a PR. Its `CURRENT STATE`
> block and lettered rows are driven one row per fresh context, exactly as `orchestrate-build` drives tickets.
> Operator decisions are recorded verbatim in §7.1.

---

## CURRENT STATE

```
projectStatus:   IN_PROGRESS        # NOT_STARTED | IN_PROGRESS | BLOCKED | PAUSED | DONE
stage:           P                  # M (meta-plan) → P (plan) → B (build artifacts) → HANDOFF
nextUnit:        WAVE-2             # A2 A3 B1 B2 C1 E1 E3 E4 G1 H1 (parallel) + D1 interactive; see §9
lastCompleted:   A1                 # baseline frozen 2026-09-30T16:31:55Z (baseline/BASELINE.md)
blockedOn:       (nothing)
pauseRequested:  false
baseline:        baseline/baseline.json @ 2026-09-30T16:31:55Z   # delta procedure in BASELINE.md
planOut:         docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md
memoryRoot:      docs/build
round:           11                 # provisional; manifest phases continue at P34, rows at 201
updatedAt:       2026-09-30T16:05Z
```

**Vocabularies.** Row status: `open → in-progress → done | blocked-on-operator | dropped(reason)`;
every `done` row cites its output path. Owner: `R` research · `D` design · `P` product · `S`
synthesis · `O` operator · `J` joint (operator + agent). `⚑` = operator-fixed constraint (not
relitigated). **Nothing cited that was not read.**

---

## 1. Purpose and outcome

Rounds 1–10 produced a real, publicly live product (surveillancegraph.org, release
`sig-2026-09-27-ce480ab1`) and a large body of machinery. They also left: 36 owed obligations, 69
not-MET requirements, a deferred human-evaluation spine, Round-10 machinery that has never run on
hosted data, spec text that contradicts operator decisions, and build memory that is no longer a
trustworthy resume point (future-dated records, deleted append-only history, a 679 KB ledger). See
Appendix A.

The next phase must, **in this order of truth**:

1. **Repair the build's truth infrastructure** so the next orchestrator resumes from records that are
   true (dates, append-only history, ledger, validators, CI awareness).
2. **Process everything owed** — deferrals, not-MET requirements, backlog, return passes — so every
   item has exactly one honest disposition.
3. **Incorporate an agentic critical design review** of the live site (driven in a real browser) **and
   the operator's own feedback** into product requirements.
4. **Make the spec tell the truth** about operator decisions (amend with ADR-recorded waivers, or keep
   the obligation owed with a real plan).
5. **Close coverage blind spots** — an extremely careful, comprehensive web search for the data sources we are
   missing (Flock, Axon and other public-private surveillance networks; missing geographies; missing technology
   classes), reviewed, configured for ingestion and **ingested into production during the Round-11 build**
   (added at the operator's request, §7.1).
6. **Make the data radically transparent and exportable** — per-source exploration, links to ground truth, raw
   and derived downloads, and public ingestion logs, metrics and timestamps (added at the operator's request, §7.1).
7. **Emit a ratified canonical next-phase plan and the build artifacts** (spec amendments, ADRs,
   manifest rows 201+, ticket contracts, DEFERRALS/BACKLOG mapping, a repaired LEDGER seed) so a fresh
   `orchestrate-build` session can pick up exactly where we left off.

**Out of scope for planning (Stages M/P/B):** implementing fixes, production changes (except Track 0
items the operator separately approves), merging PRs, signing gates on the operator's behalf, doing or
simulating human review. **New-source ingestion into production is Round-11 build work**: Stage P discovers,
reviews and designs; the Round-11 tickets configure connectors and run the hosted ingests after the operator's
per-source rights decisions (HG-03).

---

## 2. Stage model and gates

| Stage | What happens | Primary output | Exit gate (signed by) |
|---|---|---|---|
| **M — meta-plan** | This document is reviewed and revised | `META_PLAN.md` (approved) | **GATE-M** — operator approves; Q-1…Q-6 answered |
| **P — plan** | Rows A–H run (research/design/review/feedback), one per fresh context; then S1–S5 synthesis, adversarial review, ratification | `NEXT_PHASE_PLAN.md` + notes/data under this directory | **GATE-P** — operator ratifies the plan verbatim; universe check green; ≥3 independent reviews closed |
| **B — build artifacts** | Rows T1–T6 translate the ratified plan into canonical build memory and spec | spec_src amendments + ADRs, manifest rows 201+, ticket contracts, DEFERRALS/BACKLOG/COVERAGE mapping, LEDGER seed, HANDOFF | **GATE-B** — validators + CI green on the seed PR; orient dry-run resolves the expected next ticket; operator approves |
| **Handoff** | A fresh `orchestrate-build` session resumes from the repaired LEDGER | — | (the build's own gates) |

A gate is a pause, never a block; no gate is pre-answered or guessed past. The operator's words are
recorded verbatim; any text the agent drafts for an operator readout is labelled *agent-drafted* and
the operator confirms that exact text.

---

## 3. Binding principles for every row (lessons from Rounds 1–10)

- **P1 — Evidence discipline.** Every finding cites file:line, commit, PR, URL, or command + output, and
  an evidence class: `code` · `recorded-execution` · `live-read` · `operator-statement` · `inference`.
  Inferences are labelled. Earlier claims (including Appendix A of this document) are re-verified, never
  carried forward on authority.
- **P2 — Clock discipline.** Every date comes from `date -u`, git, GitHub, or a tool timestamp. Dates are
  never inferred, extrapolated, or "next day after the last recorded one" (the Round-10 failure, F-21).
- **P3 — Production is read-only during planning.** No deploys, bucket writes, DB writes, gcloud
  mutations, scheduler changes, PR merges/pushes to chain branches, or form submissions on the live site.
  Exceptions only via Track 0 with an explicit per-action operator go.
- **P4 — Human work is never fabricated or simulated.** Model agreement is never ground truth; no agent
  labels count as human labels; no agent-authored legal opinion; no agent signs anything.
- **P5 — Status vocabulary separates layers.** `engineered` (code + tests) · `fixture-verified` ·
  `staging-verified` · `live-executed` · `public` · `human-completed`. No status statement collapses
  them (the "MET on reduced scope" failure, F-16).
- **P6 — Independence.** Fresh context per row; a reviewer never reviews its own output; adversarial
  reviews get only the artifacts, not the authoring history.
- **P7 — Append-only stays append-only.** Corrections are new dated entries that name what they correct.
- **P8 — Unanchored human input first.** The operator's own feedback (D1) is captured before the agent's
  review findings are shown (C6), so the agent's view does not anchor the operator's.
- **P9 — Exactly-one disposition.** Every owed/unmet/found item lands in exactly one disposition in the
  work universe; a mechanical check proves completeness and non-duplication (reconcile-build discipline).
- **P10 — Control ledger untouched until Stage B.** Planning never edits `LEDGER.md`, `DEFERRALS.md`,
  the manifest, the spec, ADRs, or the coverage matrix; it writes only under this directory.
- **P11 — CI truth.** "Green" means the PR's GitHub checks plus local gates; local-only green is
  `locally-green`, not green.
- **P12 — Sized for one fresh context.** A row that overflows is split (`A3a`/`A3b`) and recorded in the
  change log.
- **P13 — Never read the whole LEDGER.** It is ~170k tokens. Rows use `reports/current/CURRENT.md`,
  `OPERATIONAL_READINESS.md §(f3)`, and targeted slices (`sed -n`, `grep`) only.
- **P14 — No secrets.** Session transcripts and GCP reads may surface tokens; never copy a value into any
  artifact (`provided: yes/no` only).
- **P15 — Source research is reproducible and conservative.** Every search query is logged (engine, query, date,
  hits kept); every candidate is captured with its URL, publisher, retrieval time and terms/licence text verbatim;
  availability is never treated as rights clearance; every candidate passes a Part VIII preflight (no person- or
  plate-level data; officer names and search reasons in audit logs are flagged); mirrors and re-publications are
  linked to their origin, never counted as independent.

---

## 4. Working theses (tested by Stage P, not assumed)

- **T1 — The biggest value gap is the truthfulness and legibility of what is already public, not new
  machinery.** (C1–C3, C6, D1–D3)
- **T2 — The build memory is not currently a safe resume point; repairing it is a prerequisite to any
  further autonomous build.** (A2, B1–B4)
- **T3 — Most owed obligations are blocked on human or operator action, not engineering; the next
  phase's engineering must be sized to the human work that will actually happen.** (E3, F1, F4)
- **T4 — Several spec MUSTs no longer reflect operator intent; the spec should be made true either way
  (explicit waiver or real plan).** (E1, E2)
- **T5 — Round-10 machinery creates value only once activated on hosted data and shipped; activation,
  not more machinery, is the next frontier.** (C4, G2, G3)
- **T6 — Verification must include CI and live evidence; local green plus fixtures was insufficient.**
  (B4, B5, H1, H2)
- **T7 — The live site under-serves the spec's design center — the local advocate with a council meeting
  in days who needs a printable dossier** (`docs/2_canonical_design_spec.md:5721-5730`, SIG-UI-002).
  (C1–C3, D1, D3)
- **T8 — Coverage has material blind spots: whole geographies and whole technology classes are missing or thin,
  and some high-yield public sources (vendor transparency portals, statutory ALPR reports, grant and procurement
  records) are not yet ingested.** (I1–I7)
- **T9 — Radical provenance transparency (every source explorable to its ground truth, raw and derived data
  downloadable where licences allow, ingestion runs visible) is both SIG's clearest differentiator and the fastest
  way to earn trust in its numbers.** (J1–J4, C3)

---

## 5. Inputs — the evidence base

| Input | Path / command | Use |
|---|---|---|
| Canonical spec (generated) | `docs/2_canonical_design_spec.md` ← `docs/research/_meta/spec_src/` + `BUILD.sh` | requirements, design center, Part VIII, §55 |
| Go-live spec | `docs/3_sig_golive_spec.md` | GL-* ids, lanes, gate delegations |
| ADRs | `docs/adr/ADR-001…145` (144 files; 064 skipped) | decisions, revisit triggers |
| Plan + contracts | `docs/tickets/00_MANIFEST.md`, `docs/tickets/*.md` | chain rows 1–200, deferred 184–187 |
| Owed register | `docs/tickets/DEFERRALS.md` (97 rows, 36 owed); `docs/build/reports/obligations/` | F1, A3 |
| Readiness + return passes | `docs/build/OPERATIONAL_READINESS.md §(f)`, esp. **§(f3)** | F1, G2 |
| Coverage | `docs/build/COVERAGE_MATRIX.csv` (715 rows) | F2 |
| Backlog | `docs/build/BACKLOG.csv/.md` (58 BL rows, 32 open), `docs/risk_register.md` | F3 |
| Capstone packet | `docs/build/CAPSTONE_CLOSURE.md §(f)`, `CAPSTONE_GAP_ANALYSIS.md` | F1, F2 |
| Build history | `docs/build/LEDGER.md` (slices only), `BUILD_INDEX.md`, `runs/`, `pr/`, `readouts/`, `planning/`, git log | B1–B5 |
| Current projection | `docs/build/reports/current/CURRENT.md` | orientation (advisory) |
| Integration plan | `docs/build/reports/p33.6-integration-plan/INTEGRATION_PLAN.md` | H1 |
| Round-10 planning precedent | `docs/build/planning/2026-09-25-six-streams/` | format precedent; S-stream design |
| Live product | https://surveillancegraph.org, API `sig-api` on Cloud Run, public bucket `manifest.json` | A1, C2, C3 |
| GCP (read-only) | project `zeta-medley-508121-u7`: Cloud Run, Cloud SQL `sig-pg`, Scheduler, GCS | A1, G1 |
| GitHub | `gh pr list/checks/view`, Actions logs | A1, H1 |
| Skills (user-global, read-only here) | `~/agent-skills/skills/{orchestrate-build,implement-spec,decompose-spec,build-memory,reconcile-build,synthesize-spec}` | B5, B6, T3 |
| 2026-09-30 review (this session) | Appendix A of this document; ephemeral captures in the session scratchpad (`…/scratchpad/live/`, **not durable**) | A2 seeds from it; C2 recaptures |
| Operator memory notes | `~/.claude/projects/-Users-stevenvitali-Eleutheria/memory/*.md` | B5 context |
| Source registry + targets | `connectors/src/connectors/data/sources.toml`, `live_targets.toml`, `ops/cadence.toml`, `tasks/src/tasks/data/acquisition_queue.toml` | I1, I7, J4 |
| Prior source research | `docs/build/planning/2026-09-25-six-streams/research/S5-source-strategy.md` + `data/source-candidates.csv`; `docs/build/reports/{SOURCE_LIVE_OPS_MATRIX,ECOSYSTEM_CONNECTORS,STAGE5_CONNECTORS,RIGHTS_REVIEW_INDEX}.md`; `docs/build/reports/catalog_sweep_*.json`; `docs/build/reports/rights/`, `acquisition/` | I1, I7 |
| Existing exposure surfaces | `exports/`, `api/`, `web/src/pages/` (downloads, `/data-freshness/`, `/evidence/`), public `manifest.json`, `ingest_run` / `ingest_run_completion` tables, GCS run rows | J1 |
| The open web | web search + fetch (reproducible query logs, P15) | I2–I6, J2 |

---

## 6. Streams and work units

```
GATE-M ─┬─ Track 0 (operator-approved ops actions; independent of planning)
        └─ A1 baseline ─┬─ A2 findings ───────────────────────────────┐
                        ├─ A3 universe ─────────────────┐              │
                        ├─ B1…B6 truth/process ─────────┤              │
                        ├─ C1 protocol ─ C2,C3,C4,(C5) ─ C6 synthesis ─┤
                        ├─ D1 operator feedback (before C6 is shown) ──┤
                        ├─ E1 ─ E2 ; E3 ; E4 ───────────┤              │
                        ├─ G1 ; H1 ─────────────────────┤              │
                        ├─ I1 ─ I2 ─ I3,I4,I5,I6 ─ I7 ─ I8 ─────────────┤
                        ├─ J1 ; J2 ─ J4 ─ J3 (after C2) ────────────────┤
                        │                               ▼              ▼
                        └──────────────── F1…F5 · D2 · D3 · G2 · G3 · H2
                                                        │
                              S1 universe → S2 → S3 plan → S4 reviews → S5 GATE-P
                                                        │
                              T1 spec+ADRs · T2 memory seed · T3 tickets · T4 mapping · T5 LEDGER · T6 GATE-B
```

Each row block below gives: owner/mode · depends · inputs · method · output · done-when.

### Track 0 — Operator-approved actions outside planning (each needs its own explicit go; Q-2)

| id | action | why now | note |
|---|---|---|---|
| 0.1 | Enable automated backups + point-in-time recovery on Cloud SQL `sig-pg`; take one on-demand backup; confirm it lists | **F-01**: backups disabled, 0 backups, ~2.4M claims unprotected | small monthly cost; reversible |
| 0.2 | Remove `curate/` from the public web bucket; confirm `/curate/` → 404 on both origins | **F-02**: demo curation pages publicly served (republish regression) | the durable fix (publish exclusion + test) is planned in G1 |
| 0.3 | Confirm the MapRoulette key recorded as "appeared in the session transcript" was rotated | LEDGER GATE DECISIONS 2026-09-24 entry | operator-only; record `rotated: yes/no` |
| 0.4 | Continue or pause the bottom-up integration (#141→#190) | operator is mid-integration at the #140→#141 boundary | **answered at GATE-M:** operator merges later; Round 11 builds on the chain (§7.1) |

### A. Baseline freeze and evidence capture

**A1 — Freeze the planning baseline** · R, read-only · depends GATE-M
- *Inputs:* git (`origin/main`, chain tip, every open PR head), `gh pr list/checks`, `reports/current/CURRENT.md`,
  sha256 of LEDGER/DEFERRALS/manifest/COVERAGE/BACKLOG; GCP read-only (`gcloud run services describe sig-web/sig-api`,
  `gcloud sql instances describe sig-pg`, `gcloud scheduler jobs list`, `gcloud run jobs list`, bucket listings),
  public `manifest.json`, live response headers.
- *Method:* record every value with the exact command and `date -u`; define a `--delta` re-run used again before S1 and T6.
- *Output:* `baseline/BASELINE.md`, `baseline/baseline.json`.
- *Done when:* later rows cite baseline keys instead of re-deriving; the delta procedure is written down.

**A2 — Verify and register the 2026-09-30 findings** · R · depends A1
- *Inputs:* Appendix A; each finding's evidence pointer.
- *Method:* re-verify every F-id against primary evidence; mark `verified | amended | refuted`; set severity,
  evidence class, implicated spec ids, routed stream. New findings from later rows are appended by the
  planning orchestrator (single writer).
- *Output:* `findings/FINDINGS.csv` (schema §8.2) + rendered `findings/FINDINGS.md`.
- *Done when:* every Appendix A row is verified or refuted with evidence.

**A3 — Extract the obligation universe (mechanical)** · R/S · depends A1
- *Inputs:* DEFERRALS (+ `obligations/events.jsonl` for effective status), COVERAGE_MATRIX (non-MET, MET-DIFFERENTLY,
  and MET rows whose evidence shows reduced scope), BACKLOG (open), risk register (→ BL), LEDGER OPEN FINDINGS +
  RETURN PASS + `returnPass` (slices), ADR revisit triggers, PENDING readouts (HUMAN-H4/H5), manifest deferred or
  unused rows (158/159, 184–187), §55 open obligations, OPERATIONAL_READINESS §(f3).
- *Method:* a small read-only extractor with a test (`tools/extract_universe.py`) emitting one row per source item
  (stable `U-nnnn`, source pointer, source status); cross-source duplicates linked, not double-counted; a checker
  proves each source item appears exactly once.
- *Output:* `universe/UNIVERSE.csv`, `tools/extract_universe.py`, `tools/test_extract_universe.py`.
- *Done when:* per-source counts reconcile to known totals (97 deferrals / 36 owed; 715 coverage / 69 not-MET;
  58 BL / 32 open; …) or each difference is explained.

### B. Build-truth repair design and orchestration retrospective

**B1 — Date-drift forensics and correction design** · R/D · depends A1
- *Inputs:* git log + PR `createdAt`; every dated field in `docs/build/**`, `docs/tickets/**`, `docs/adr/**`,
  `spec_src` (§55, App. G), `ops/src/ops/*` constants, test fixtures, `db/sqitch.plan`, the P32.23a candidate
  identity, `obligations/*.jsonl`.
- *Method:* inventory every recorded date later than its commit; classify (a) legitimately future (e.g. the
  2026-10-10 replay cron) vs (b) wrong event date; give each (b) its true date and a fix mechanism:
  append-only correction entry · code constant fix + regression test · sqitch (confirm whether change ids hash
  planned timestamps and which changes are deployed on hosted Cloud SQL — read-only — and never edit deployed
  lines) · candidate identity (supersede vs re-issue + re-sign GATE-G3). State the cause hypothesis with evidence.
- *Output:* `research/B1-date-drift.md`, `data/date_drift.csv`, draft correction ADR text.
- *Done when:* every wrong date has a true date and a fix mechanism; nothing is fixed yet.

**B2 — Append-only integrity scan and restoration design** · R · depends A1
- *Inputs:* git history of every append-only/historical file: LEDGER GATE DECISIONS / PHASE LOG / OPEN FINDINGS,
  DEFERRALS, readouts, landed ADR bodies, manifest Plan extensions + Spec amendments, spec App. G, BUILD_INDEX,
  `runs/`, `obligations/events.jsonl`.
- *Method:* diff-scan history for removed or rewritten lines; classify benign (formatting/escaping) vs loss;
  design restoration as appended "restored from `<sha>^`" blocks. Known case: `c2055d96` removed 53 GATE DECISIONS rows.
- *Output:* `research/B2-append-only.md`, `data/append_only_violations.csv`.
- *Done when:* every loss has a restoration design; benign rewrites are listed and justified.

**B3 — Control-ledger and index redesign** · D · depends A1, B2
- *Inputs:* LEDGER slices, `build-memory/layout.md` (BM-LEDGER-01/02, BM-LAYOUT-01 allowed root entries),
  `reports/current/`, closeout protocol (ADR-126/127, `docs/build/tools/CLOSEOUT_WRITER_PROTOCOL.md`), BUILD_INDEX,
  OPERATIONAL_READINESS §(f3).
- *Method:* design the target LEDGER: a size budget; PRIOR chains moved to an archive under `reports/` (the
  layout forbids new root entries); a fresh OPERATING MODE resume prompt; superseding notes for stale amendments;
  RETURN PASS + `returnPass` regenerated from §(f3); an appended ordered PHASE LOG index instead of moving history;
  BUILD_INDEX gaps (GATE-G3/GATE-ACCEPT rows, "PR pending" rows, duplicate sequence 170, 17 tickets without PHASE LOG
  entries); the `IN_PROGRESS` enum; the fate of shadow mode (`D-R10-MEMORY-1` cutover vs retire).
- *Output:* `design/B3-ledger-redesign.md` with a step-by-step migration usable in T2/T5 or as a first ticket.
- *Done when:* a fresh `orchestrate-build` orient following the design would read ≤ the budget and resolve the
  correct next unit.

**B4 — Verification and validator gap design** · D · depends B1, B2, B3
- *Items:* date sanity (recorded ≤ commit/PR time); an append-only diff guard in CI; reading GitHub checks at every
  ticket boundary; readout authorship/verbatim rule; ledger size budget; stale-path check on resume prompts;
  "tests may assert invariants, not the current state of living records" (inventory the 11 files that pin build
  memory, e.g. `tests/unit/test_capstone_closure_round10.py`); `check_spec_src.py` + coverage checker wired into CI
  (SIG-ENG-039); ADR index completeness (79 rows with "—"); traceability/risk-register per-phase updates
  (SIG-ENG-031); verdict-vocabulary enforcement.
- *Output:* `design/B4-verification.md` with draft requirement text (SIG-MEM / SIG-ENG) and test designs.
- *Done when:* each Appendix A memory/process finding maps to a guard that would have caught it, or a recorded
  reason why none can.

**B5 — Orchestration retrospective (Rounds 1–10)** · R · depends A2, B1, B2
- *Questions:* which practices produced trustworthy results; where autonomy outran verification; gate-handling
  patterns (pre-answered, blanket, pre-authorized, delegated signatures) and their consequences; `blockedOn` never
  used; harness switches (Devin / Claude Code / Codex) and their observable effects; planning outside
  `decompose-spec`; tail cost vs value; the four-time deferral of human evaluation; operator merges during the chain;
  out-of-ticket production changes by the orchestrator.
- *Output:* `research/B5-orchestration-retro.md`, ending in **concrete operating rules for Round 11** (these become the
  new OPERATING MODE in T5).
- *Done when:* every rule traces to at least one evidenced incident.

**B6 — Skill-change proposals (outside this repo)** · D · depends B4, B5
- *Method:* propose, in prose and diff sketches, changes to `orchestrate-build`, `implement-spec`, `decompose-spec`,
  `build-memory`, `reconcile-build`: CI at boundary; clock discipline; the P5 status vocabulary; readout authorship;
  ledger size budget; append-only guard; lint against tests pinning living records. **Not applied** — user-global
  skills are never edited from this repo (Q-13).
- *Output:* `research/B6-skill-proposals.md`.

### C. Agentic critical design review of the live product

**C1 — Review protocol and rubric** · P/D · depends A1
- *Inputs:* spec UI parts incl. personas and design center (`docs/2_canonical_design_spec.md:5715-5790`,
  SIG-UI-001/002), §3.1 defining standard, Part VIII §42–§46, `PUBLIC_SURFACE_DATA_CONTRACTS.md`, the P32.24 kit
  (`reports/p32.24-investigation-journey-verification/USABILITY_TASK_PROTOCOL.md`, T1–T7), route inventory
  (`web/src/pages`).
- *Method:* define personas and concrete task scripts, each with an evidence-grounded expected answer (local
  advocate preparing for a council meeting; journalist verifying a number; researcher downloading data; OSM/DeFlock
  contributor; an agency or vendor seeking a correction; a skeptic checking provenance); a heuristic checklist —
  truthfulness of every number, epistemic legibility (provisional / unknown / contradiction), task success, IA and
  navigation, copy, WCAG 2.2 AA, performance and JS budgets, mobile, the printed dossier, citations and permalinks,
  licensing and attribution, Part VIII safety, provenance and trust, empty and error states, discoverability; a page
  sample (every route + dossier edge cases: `unresolved`, largest, smallest, non-US); the finding schema (§8.2);
  evidence capture rules (§8.4); the browser (Q-5).
- *Output:* `review/PROTOCOL.md`.

**C2 — Execute the journeys on production in a real browser** · R, read-only · depends C1
- *Method:* desktop and mobile viewports; keyboard and screen-reader spot checks; print preview of a dossier; no
  form submissions or load; every observation → a finding with evidence.
- *Output:* findings (appended via the orchestrator) + `review/JOURNEYS.md` (narrative per persona).

**C3 — Data-truth audit of displayed numbers** · R, read-only · depends C1
- *Method:* trace every number and claim on the sampled pages to the public manifest/export JSON, an API response, or
  a read-only spine query; mismatches become findings. Known leads: the site-wide "How we know this" block, a tier sum
  6 short, the "human-verified holdout" wording.
- *Output:* `review/DATA_TRUTH.md`, `data/number_trace.csv`.

**C4 — Pre-release review of the unreleased Round-10 surfaces** · R · depends C1
- *Method:* run web + API (`--release-registry` on the P32.25 staging registry) + the intake receiver locally; review
  `/releases/`, `/r/<pub>`, release search, the coordinated workspace islands, `/research-dossier/`, and the `/dispute`
  and `/intake` flows with the same protocol, so that activation (G2) is informed.
- *Output:* findings + `review/R10_PREVIEW.md`.

**C5 — Landscape and differentiation scan (optional, Q-18)** · R
- *Method:* compare how comparable public resources (e.g. DeFlock, EFF Atlas of Surveillance, sources named in the
  spec's research cache) serve the design-center tasks, and what SIG uniquely answers on the page vs in principle.
- *Output:* `research/C5-landscape.md`.

**C6 — Review synthesis** · P · depends C2, C3, C4 (+C5)
- *Method:* cluster findings into product themes; severity-rank; separate violations of existing spec ids from new
  needs; draft requirement statements.
- *Output:* `review/REVIEW_SYNTHESIS.md`. **Not shown to the operator until D1 is complete (P8).**

### D. Operator feedback and product direction

**D1 — Unanchored operator feedback** · O (+ agent scribe) · depends GATE-M; must finish before C6 is shared
- *Method:* the agent writes `feedback/QUESTIONNAIRE.md` (what the site is for and for whom; what feels wrong,
  missing or embarrassing; what you would hand a council member; priorities; appetite for time, cost and human work;
  red lines). The operator answers in writing or in a live session; the agent records answers verbatim with `U-nnn`
  ids and keeps its structured interpretation in a separate, labelled section.
- *Output:* `feedback/OPERATOR_FEEDBACK.md`.

**D2 — Operator reaction to the findings** · O/J · depends D1, C6, B5, E1
- *Method:* the operator marks every S0–S2 finding agree / disagree / priority and adds new `U-nnn` items.
- *Output:* appended to `OPERATOR_FEEDBACK.md`; priority column in `FINDINGS.csv`.

**D3 — Product direction memo** · P/J · depends D2
- *Method:* from D1/D2 + C6 + T7: reaffirm or change the design center; target users; geographic focus (national
  breadth vs local depth; which jurisdictions); which Round-10 features must ship; success metrics for the phase.
- *Output:* `design/D3-product-direction.md` (ratified at S5).

### E. Governance, rights and spec-contradiction resolution

**E1 — Contradiction register** · R · depends A1
- *Scope:* every spec MUST/SHOULD contradicted by an operator decision or landed behaviour. Known: SIG-PUB-008 two
  independent reviewers (sole-maintainer waiver, yet marked MET); SIG-GOV-012 legal home (an individual); counsel
  (R-01, RISK-P0-*; interim dispositions); SIG-INGEST-037 / §26 rule 7 / `policy/crawler.py` docstring vs GL-GATE-08
  "disregard robots"; SIG-CONTRIB-012 Stage-0 outreach marked WONTFIX without an ADR; SIG-SEC-003 transparency report;
  SIG-TRUST-009/010 scoped acceptance; human evaluation deferred four times.
- *Output:* `research/E1-contradictions.md` (spec text, decision text, evidence, current compensating control).

**E2 — Option memos per contradiction** · D · depends E1
- *Method:* for each: (a) amend the spec — an ADR-recorded waiver with rationale, compensating control and revisit
  trigger; (b) keep it owed with a feasible plan (who, cost, when); (c) a hybrid. State risk plainly; never present
  agent analysis as legal advice; flag where real counsel is required.
- *Output:* `design/E2-governance-options.md`; each decision becomes a Q row answered at S5.

**E3 — Human-work feasibility and sourcing** · R/J · depends A1
- *Method:* enumerate every human role the owed work needs (H4/H5 device-label reviewers, dossier semantic reviewer,
  second publication reviewer, counsel, usability participants, rights reviewer, intake moderator); estimate effort
  (reuse the P32.9 measured-time worksheet); list realistic sourcing options and costs; define the smallest *honest*
  version of each; state what stays blocked if none is sourced.
- *Output:* `research/E3-human-work.md`.

**E4 — Rights-decision packets** · R · depends A1
- *Scope:* the six rights rows (D-JURIS.2-1, D-SOURCES.2-2/7-1/8-1/9-1/9-4), the D-R10-SOURCES-1 per-target reviews,
  and status re-assessment of D-SOURCES.12-1 (reads "nothing actionable remains") and D-SOURCES.9-2 (robots blocker
  pre-dates GL-GATE-08).
- *Output:* `design/E4-rights-packets.md` — decision-ready; the operator decides (HG-03), never the agent.

### F. Owed-obligation and requirement processing

**F1 — Owed-register adjudication (36 rows)** · R/D · depends A3, E1
- *Method:* for each row: re-verified current truth; status corrections (proposed, as append-only annotations);
  blocker class; proposed disposition (ticket · live return pass · operator action · human marker · WONTFIX with
  reason · spec amendment). Use the §(f3) commands as the starting point.
- *Output:* `research/F1-owed-register.md`; dispositions written to the universe.

**F2 — Requirement verdict re-audit and verdict vocabulary** · R · depends A3
- *Method:* re-verify all 69 not-MET ids; re-audit every pre-Round-10 PARTIAL / AT-RISK / MISSING verdict (not
  refreshed since about P21; e.g. "web reads fixtures", "search not wired" are stale), every reduced-scope MET
  (SIG-TRUST-009/010, FIND-006, DOS-002…005, ACQ-004) and a sample of the 77 MET-DIFFERENTLY; fix routing that points
  at long-landed P21.x tickets; home the 55 not-MET ids that appear in no BACKLOG/DEFERRALS/manifest row. Propose the
  verdict vocabulary (§8.3).
- *Output:* `research/F2-verdicts.md`, `data/coverage_delta.csv` (**proposal only**; applied in T4).

**F3 — Backlog triage** · R · depends A3
- *Method:* each of the 32 open BL rows → closed-by-later-round (with evidence) · still open (re-homed) · superseded.
- *Output:* `research/F3-backlog.md`.

**F4 — Deferred human-evaluation spine and chain re-entry design** · D · depends E3, B3
- *Method:* decide the fate of rows 184–187 (keep and re-enter · re-scope as new rows with 184–187 marked superseded ·
  keep deferred with a trigger), given E3's feasibility; reconcile with LEDGER semantics (`nextTicket` currently
  `HUMAN-H4`) and the append-only manifest; state what stays PROVISIONAL publicly until it runs.
- *Output:* `design/F4-s3-spine.md`.

**F5 — Carried engineering debt** · R · depends A2, C4
- *Scope:* D-P32.10a-1 (`sqitch verify` division by zero), D-P32.16a-1 (`sqitch revert` fails on postgis), tests that
  pin living records, and anything B or C4 surfaces.
- *Output:* `research/F5-eng-debt.md`.

### G. Production activation and operations

**G1 — Ops risk register and hardening design** · R/D · depends A1
- *Scope:* backups/PITR plus a restore drill (Track 0 covers only the switch); a publish-exclusion regression test
  (`/curate/`); `sig-alerts` on `:latest` (vs ADR-111); scheduler drift (live SAM.gov cron vs `ops/cadence.toml`); cost
  truth vs `ops/gcp/README.md`; alert delivery and monitoring; API-vs-site freshness drift and republish cadence; the
  2026-10-10T03:35Z OSM replay watch (D-P31.4-1); secret hygiene.
- *Output:* `research/G1-ops.md` (ops requirements + runbook changes).

**G2 — Round-10 activation plan** · D · depends C4, E2, F1
- *Method:* sequence, preconditions, cost, rollback and approvals for the live return passes: D-R10-LIVE-1 → D-P32.23a-1
  → D-R10-PUBLISH-1; dossier captures D-P32.18/19/20/21-1 (+ D-R10-SOURCES-1); intake operation D-P32.16-1; memory
  cutover D-R10-MEMORY-1; which product fixes (from C4) must land first.
- *Output:* `design/G2-activation.md`.

**G3 — Release, deploy provenance and versioning model** · D · depends C2, G2, J3
- *Method:* immutable release namespaces (P32.13) vs today's bucket-sync deploy; a release id/commit stamp in every page;
  republish cadence; tags on `main`; rollback.
- *Output:* `design/G3-release-model.md`.

### H. Integration completion and CI truth

**H1 — Integration state record and merge-readiness notes** · D · depends A1 · *re-scoped at GATE-M (Q-11: the
operator merges later; Round 11 builds on the chain)*
- *Method:* record the integration state (`main` at #140 `b7c9e2e3`; #141–#190 open) and write the operator's
  merge-readiness notes for later: the lockfile fix for #141–#154 (`npm ci`: `@emnapi/runtime` missing); the three PRs
  red on their own heads (#165, #179, #185); how Round-11 PRs stacked on #190 extend the bottom-up order; whether
  date corrections should land before the operator merges #143+; verification (tree == final head). **No merge,
  retarget or push to chain branches.**
- *Output:* `design/H1-integration.md`.

**H2 — PR model and CI policy for Round 11** · D/J · depends H1, B5 · *base decided at GATE-M: Round 11 stacks on the
chain tip (`devin/p33-8-agent-docs-refresh`, PR #190)*
- *Method:* stacked-PR conventions on top of #190; which CI failures inherited from the unmerged chain are expected vs
  new; required checks; how the orchestrator treats red CI (proposed: `blockedOn`).
- *Output:* `design/H2-branch-ci.md`.

### I. Source discovery and acquisition (added 2026-09-30 at the operator's request, §7.1)

Goal: an extremely careful, rigorous and comprehensive search for the datasets SIG is missing — Flock, Axon and
other public-private surveillance networks; missing geographies; missing technology classes — ending in a reviewed,
prioritized acquisition backlog and an ingestion design that Round-11 tickets execute into production.

**I1 — Current source-coverage map** · R, read-only · depends A1
- *Inputs:* `sources.toml` (every row: ingestion_permitted, review status, licence), `live_targets.toml`,
  `ops/cadence.toml`, hosted per-source volumes (read-only: public manifest/export freshness, API coverage routes,
  GCS run rows), `acquisition_queue.toml` (27 Round-10 candidates), catalog sweeps, `SOURCE_LIVE_OPS_MATRIX.md`,
  six-streams S5 research, the ontology's technology vocabulary.
- *Method:* a matrix of source × technology class × geography (country / US state / county / city) × publisher
  type × status (`ingested-live` · `permitted-not-ingested` · `gated` · `candidate` · `refused`); coverage counts per
  class and geography against explicit denominators (all US states; the largest US cities and counties; agencies
  known to contract with Flock/Axon/Motorola where evidenced); a ranked blind-spot list.
- *Output:* `research/I1-source-coverage.md`, `data/source_coverage.csv`.

**I2 — Source-search protocol and taxonomies** · D · depends I1
- *Method:* define (a) the technology taxonomy (e.g. fixed and mobile ALPR and their sharing networks; RTCC and
  camera-integration platforms; private-camera registries and partnerships; drones / drone-as-first-responder; gunshot
  detection; face recognition; cell-site simulators; social-media monitoring; mobile forensics; video analytics;
  school surveillance; data brokers; body-worn cameras and evidence platforms; fusion centers) mapped to the ontology;
  (b) the discovery-channel taxonomy (vendor transparency portals; government open-data portals; statutory reporting
  such as state ALPR audits and policies; CCOPS / surveillance-ordinance annual reports; council agendas; procurement
  and cooperative contracts; federal and state grants; legislation; court records; records-request corpora; NGO,
  journalism and academic datasets; crowdsourced maps; international equivalents); (c) the geography frame; (d) the
  query matrix, snowballing rules, inclusion/exclusion criteria, a saturation stopping rule per cell, and the
  candidate schema (§8.6); (e) how the fan-out rows split the matrix without overlap.
- *Output:* `design/I2-source-search-protocol.md`.

**I3–I6 — Deep web research fan-out** · R, web research · each depends I2 · run in parallel, one fresh context each,
all following the I2 protocol and logging every query (P15)
- **I3 — ALPR and public-private camera networks:** Flock (per-agency transparency portals at scale, sharing
  networks, Raven/Aerodome/integration products, customer evidence from procurement and agendas, released audit
  logs), Motorola Solutions / Vigilant (LEARN sharing), Axon (Fleet in-car ALPR, Fusus RTCC camera registries),
  Genetec, Rekor, Leonardo/ELSAG and others; statutory ALPR reporting regimes by state.
- **I4 — Other technology classes:** drones/DFR, gunshot detection, face recognition, RTCC and fusion centers,
  cell-site simulators, social-media monitoring, forensics, video analytics, school surveillance, data brokers,
  body-worn cameras and evidence platforms.
- **I5 — Geography gaps:** the I1 blind spots (US states, counties and cities with zero or thin coverage; tribal and
  territorial; priority international regions) — find the best sources per gap.
- **I6 — Cross-cutting evidence channels:** procurement and cooperative contracts (city/state registers, Sourcewell,
  NASPO, GSA), federal and state grants (DOJ/BJA, COPS, DHS/FEMA beyond what is ingested), legislation and CCOPS
  reports, court records, records-request corpora (MuckRock, DocumentCloud), NGO/journalism/academic datasets.
- *Output per row:* `research/I<n>-<slug>.md`, `data/candidates_I<n>.csv` (§8.6), `data/query_log_I<n>.csv`.

**I7 — Candidate consolidation and review packets** · R/D · depends I3–I6
- *Method:* merge and de-duplicate candidates against the registry, the 27-row acquisition queue and each other
  (lineage: origin vs mirror); capture terms/licence verbatim; Part VIII preflight; acquisition feasibility (access
  mode, format, volume, cadence, connector reuse — ArcGIS/Socrata/CKAN/Legistar/document adapters); score with the
  existing `acq-score/1` model (extended if needed, with rationale); produce the prioritized acquisition backlog and
  operator-ready HG-03 decision packets (proposed registry rows are written as planning data, never into
  `sources.toml`).
- *Output:* `research/I7-candidates.md`, `data/candidates_consolidated.csv`, `design/I7-rights-packets.md`.

**I8 — Acquisition and ingestion design** · D · depends I7, G1
- *Method:* for the prioritized candidates: connector design (reuse vs new), registry/targets/cadence changes,
  hosted ingest plan (jobs, digest-pinned images, cadence, volume, Cloud SQL disk/tier headroom, cost), entity
  resolution impact (dedupe against OSM/DeFlock/existing sites; mirror non-independence), Part VIII enforcement,
  rematerialization and republish, verification (captures landed, claims > 0, `+0` re-run, coverage movement per
  blind spot), and the Round-11 ticket outline that configures and ingests them into production.
- *Output:* `design/I8-acquisition-design.md`.

### J. Data transparency and export surface (added 2026-09-30 at the operator's request, §7.1)

Goal: make the data itself easy to explore and export from the public site — every third-party source explorable,
linked to its ground truth, raw and derived data downloadable where licences allow, and ingestion logs, metrics and
timestamps public — for maximal transparency.

**J1 — Current exposure inventory** · R, read-only · depends A1
- *Method:* what is public today (licence-separated downloads, `manifest.json`, `/data-freshness/`, `/evidence/`, API
  routes incl. `/v1/export`, citation/as-of blocks) vs what exists only internally (`ingest_run` +
  `ingest_run_completion`, GCS run rows, OCFL captures and `evidence_capture`, claim provenance, rights records, robots
  verdicts, probe history); per item: where it lives, whether it could be exposed, and the constraint (licence,
  Part VIII, restricted compartment, withdrawal barrier, egress cost).
- *Output:* `research/J1-exposure-inventory.md`.

**J2 — Prior art and standards (web research)** · R · depends A1
- *Method:* how leading open-data and transparency projects expose sources, provenance, downloads, update logs and
  data quality (e.g. OpenSanctions dataset pages, OpenStreetMap, Wikidata references, Our World in Data, ProPublica
  Data Store, OpenCorporates, Atlas of Surveillance, DeFlock); standards (DCAT / DCAT-US, schema.org `Dataset`,
  Frictionless Data Package, W3C PROV, CSVW); versioned releases, checksums and signing; public status/ingestion
  pages. Logged queries (P15).
- *Output:* `research/J2-prior-art.md`.

**J4 — Redistribution and feasibility matrix** · R/D · depends J1, I1
- *Method:* per registry source: raw-bytes redistribution status (`raw-ok` · `derived-only` · `link-only` ·
  `restricted`) from recorded licences/terms; volume and egress/storage estimates for raw and derived downloads
  (§38.5 egress risk); what may be shown of ingestion logs (scrub secrets, internal paths, PII).
- *Output:* `research/J4-redistribution-matrix.md`, `data/redistribution.csv`.

**J3 — Transparency and export design** · D · depends J1, J2, J4, C2
- *Method:* the source explorer (index + per-source page: publisher, description, licence and redistribution status,
  upstream ground-truth links, capture history with timestamps and content hashes, ingestion run log with metrics —
  fetched, parsed, claims added/duplicate/rejected, errors — freshness and cadence, coverage by geography and
  technology, sample records, rights-review record, known issues); per-record provenance (claim → capture → upstream
  URL, retrieval time, hash, "view original"); bulk downloads (per compartment and per release, formats, checksums,
  data dictionary and schema docs; API parity); how the export pipeline generates all of it from read-only spine
  views and run records; zero-JS content-page constraints; licence gating; Part VIII and withdrawal; cost. Draft
  requirements (SIG-*) and the Round-11 ticket outline; interfaces with G3 (release model) and C findings.
- *Output:* `design/J3-transparency-design.md`.

### S. Synthesis → the canonical next-phase plan

**S1 — Universe consolidation and dispositions** · S · depends A2, A3, B*, C6, D2, E*, F*, G*, H*, I*, J*
- Merge the universe with every finding (F-ids) and feedback item (U-ids); exactly one disposition each (§8.1);
  re-run the A1 delta and fold in any baseline change. *Done when* the completeness/non-duplication check is green.

**S2 — Themes, priorities, sequencing, success criteria** · S/J · depends S1, D3
- Group into themes and waves; dependency DAG; gates and human prerequisites; what is in this phase vs explicitly
  later (with triggers); measurable success criteria; the round's closing-tail shape (lighter than Round 10's
  five-ticket tail unless justified).

**S3 — Draft `NEXT_PHASE_PLAN.md`** · S · depends S2. Required sections:
  1 brief and authority · 2 baseline · 3 principles/invariants · 4 ratified decisions · 5 themes (problem → evidence
  F/U ids → design → requirements → acceptance) · 6 requirement changes (new ids with draft spec text, amended ids,
  ADR-recorded waivers) · 7 ADR list (from ADR-146) · 8 ticket plan outline (rows 201+, sizing for the dispatch
  target, dependencies, gates, live stages, HUMAN/GATE markers, re-entry of 184–187 per F4) · 9 obligation mapping
  (every U-id → disposition) · 10 ops track · 11 human-work plan · 12 integration and branch policy · 13 round tail and
  acceptance · 14 risks · 15 explicitly deferred items with triggers.

**S4 — Adversarial reviews (fresh contexts) and closure** · S · depends S3
- At least three lenses: (i) coverage — every universe item dispositioned, nothing dropped or double-owned; (ii)
  feasibility — sizing, ordering, dependencies, cost, human work realistic; (iii) truth and safety — no fabricated
  human work, honest verdicts, governance and Part VIII, clock discipline. Findings closed in `reviews/REVIEW_CLOSURE.md`.

**S5 — Operator ratification (GATE-P)** · O
- Every open Q answered or explicitly deferred; the operator's words recorded verbatim; the plan frozen as canonical
  for the phase.

### T. Translation to build artifacts (Stage B, after GATE-P)

**T1 — Spec amendments and ADRs.** `spec_src` edits (a new Part/§ for Round 11 following §55's pattern, plus
amendments to existing sections) → `BUILD.sh`; new requirement ids append-only; Appendix F/G rows; one ADR per
decision or waiver (from ADR-146, each with `## Revisit trigger`); `check_spec_src.py` green.

**T2 — Build-memory repair seed.** Only what must be true before the orchestrator resumes (per Q-14 and B3): the
correction ADR for dates (append-only), restored GATE DECISIONS block, LEDGER restructure, stale prompts superseded.
Everything that needs code or tests becomes early Round-11 tickets instead.

**T3 — Tickets via `decompose-spec mode=extend`.** Manifest rows 201+ with Round-11 banner and Plan-extensions line;
contracts from the template with `Run:` lines and `live_verification` values; HUMAN/GATE markers; the tail rows;
requirement → ticket index; sizing re-checked by a fresh-context review (decompose-spec Phase 4).

**T4 — Mapping into the registers.** DEFERRALS: every OPEN/PARTIAL row annotated with its new landing (append-only),
new rows for new deferrals; BACKLOG: new BL rows from BL-059, closures with evidence; COVERAGE_MATRIX: the F2 deltas
and the adopted verdict vocabulary; `check_backlog.py` and the coverage checker green.

**T5 — LEDGER seed and resume prompt.** New OPERATING MODE (the B5 rules, incl. CI reading and clock discipline);
CURRENT STATE (round 11, `nextTicket`, `chainTip`/base per H2, `dispatchTarget`, harness per Q-16); GATE DECISIONS
entries for GATE-M and GATE-P (verbatim).

**T6 — Validation, dry-run and handoff (GATE-B).** All validators green (existing + any new ones landed in the seed);
CI green on the seed PR; a read-only `orchestrate-build` orient dry-run resolves the expected next ticket;
`HANDOFF.md` with the exact resume prompt; operator approval recorded.

---

## 7. Operator decision register

Recommendations are mine; decisions are yours. **Q-1…Q-6 block the start of Stage P.**

| id | question | recommendation | unblocks |
|---|---|---|---|
| **Q-1** | Approve this meta-plan (stages, streams, principles, outputs)? Changes? | — | GATE-M |
| **Q-2** | Track 0: authorize 0.1 (backups + PITR) and 0.2 (remove `/curate/`) now, each as a separate action? Confirm 0.3 (key rotated)? | Yes to 0.1 and 0.2 | Track 0 |
| **Q-3** | Where planning artifacts live and when they are committed | An isolated worktree (`~/Eleutheria-next-phase`) on branch `claude/next-phase-planning` from the current chain tip, so your integration in the main checkout is untouched; commit each row's output as it lands; nothing touches LEDGER until Stage B | A1 |
| **Q-4** | Stage-P driver and harness | Claude Code: one planning-orchestrator session dispatching a fresh subagent per row, this file as the ledger (`synthesize-spec` run-mode semantics) | all rows |
| **Q-5** | Browser for C2/C4 | Claude in Chrome in a clean profile (public pages only), or the built-in browser; plus headless checks for a11y/perf | C1 |
| **Q-6** | D1 format and timing | Written questionnaire first (unanchored), then a live walkthrough for D2 | D1 |
| Q-7 | Governance stance: any contradictions you want pre-decided (amend the spec vs keep owed), or decide all at S5 from E2's memos? | Decide at S5 | E2, S5 |
| Q-8 | Appetite for human work next phase (recruiting reviewers, counsel, participants; budget; time) | Answer after E3 shows effort and options | F4, S2 |
| Q-9 | Which Round-10 features should ship to production next phase? | Decide at D3/S5 after C4 | G2 |
| Q-10 | Cost ceilings: monthly infra ceiling; one-off spend ceiling | State a number | G1, G2 |
| Q-11 | Will you finish merging #141–#190 before Round 11 seeds? Does Round 11 fork from `main`? | Yes and yes (simplest honest base) | H2, T5 |
| Q-12 | Date-correction approach for the signed fixture candidate | Supersede it (it held 0 records and never shipped) rather than re-issue + re-sign | B1, T2 |
| Q-13 | Are skill changes (B6) in scope, as a separate out-of-repo effort? | Yes, after GATE-P | B6 |
| Q-14 | Memory repair placement: Stage-B seed vs first Round-11 tickets | Minimal LEDGER reset + correction records in the seed; code/test repairs as early tickets | T2, T3 |
| Q-15 | Size, timebox and autonomy for Round 11 (checkpoint cadence, pause points) | Decide at S2 | S2, T5 |
| Q-16 | Execution harness for Round 11 (Claude Code / Devin / Codex) | Decide after B5 reports | T5 |
| Q-17 | Naming: Round 11 = phases P34+ and manifest rows 201+? | Yes | T1, T3 |
| Q-18 | Include the optional landscape scan (C5)? | Yes, time-boxed | C5 |
| Q-19 | Rights stance for newly discovered sources: apply GL-GATE-07 ("err on the side of approving") by default, or decide per batch? | Per-batch HG-03 packets with GL-GATE-07 as the default; anything flagged by the Part VIII preflight decided individually | I7, I8 |
| Q-20 | Sources, geographies or vendors you already know are missing (captured via D1 Q-D1-13) | — | I2 |
| Q-21 | Budget for paid data sources or services (e.g. commercial procurement databases) | Assume zero unless stated | I7 |
| Q-22 | Transparency defaults: publish raw captured bytes where the licence permits? Publish ingestion run logs (scrubbed)? | Yes to both, licence-gated and scrubbed | J3 |
| Q-23 | Acceptable Cloud SQL growth/cost for new ingestion (disk 15 GB, `db-custom-1-3840` today) | State a ceiling (feeds Q-10) | I8 |
| Q-24 | (from E3) Confirmatory evaluation goal: try to certify the 0.98 auto-write gate, or measure precision only and keep auto-write provisional? Which tier(s)? (149 pairs/tier minimum; certification is unlikely to pass even at true 99% precision) | Decide at S5 with E3 numbers | F4 |
| Q-25 | (from E3) May the operator hold the custodian / method-reviewer / adjudicator seats with public disclosure? | Custodian + method reviewer yes (disclosed); adjudicator external | F4, E2 |
| Q-26 | (from E3) Who gave the counsel determinations recorded in ADR-086 and ADR-106, and would they write a dated opinion? | — | E2 |
| Q-27 | (from E3) Should the correction-intake receiver open next phase, and who is the backup moderator? | — | G2 |
| Q-28 | (from E3) Authorize recruiting volunteer reviewers from the DeFlock / EFF / MuckRock communities? (outward contact) | Decide at S5 | F4 |
| Q-29 | Public contact for corrections/disputes: publish the operator's personal address on the site, or a project alias (e.g. `corrections@surveillancegraph.org` forwarding to it)? | A project alias (safety, spam, succession) — **ANSWERED: operator's personal address for now** (§7.1) | G2, J3 |

### 7.1 Decisions recorded at GATE-M (2026-09-30T16:16Z)

Operator, verbatim: *"I approve the meta-plan. I approve backups and removing curate. I approve separate git worktree
branched off latest build chain tip for planning work. Claude Code can run stage P. Use Chrome browser. And don't merge
the PR chain, we'll just build off of it and I'll handle merging later. For my feedback, use your best judgement, just
make sure you prompt me for my input when you need it and keep me in the loop"*

| Q | decision | consequence |
|---|---|---|
| Q-1 | **Approved** | Stage P starts; GATE-M closed |
| Q-2 | **0.1 backups: approved. 0.2 remove `/curate/`: approved.** 0.3 key rotation: not yet answered | Track 0.1/0.2 executed by the planning orchestrator (§11); 0.3 asked at the next check-in |
| Q-3 | **Separate git worktree branched off the latest chain tip** | `/Users/stevenvitali/Eleutheria-next-phase`, branch `claude/next-phase-planning` from `b051732c` |
| Q-4 | **Claude Code runs Stage P** | this session is the planning orchestrator; fresh subagent per row |
| Q-5 | **Chrome** | C2/C4 use Claude in Chrome |
| Q-6 | **Agent's judgement; prompt the operator when input is needed; keep the operator in the loop** | D1 = written questionnaire sent early (unanchored by C-stream findings), D2 = walkthrough of findings; progress check-ins at wave boundaries |
| Q-11 | **Do not merge the PR chain; build on it; the operator merges later** (answers Q-11 and Track 0.4) | Round 11 stacks on the chain tip (PR #190); H1 re-scoped to a record + merge-readiness notes; no merge/retarget/push by any row |

Follow-up, operator verbatim (2026-09-30T16:27Z): *"I'll leave the point-in-time recovery question to you. MapRoulette key
can stay stale for now. Continue researching/planning. When it's needed, I want you to just interactively collect and log
my answers to the questionairre interactively in Claude one by one"*

| item | decision | consequence |
|---|---|---|
| PITR (Track 0.1 remainder) | **delegated to the agent** → enabled in a quiet window | done 16:28–16:31Z; one 503 during restart, self-recovered (`baseline/TRACK0_RECORD.md`) |
| Track 0.3 MapRoulette key | **stays unrotated for now** (operator-accepted) | recorded as an accepted risk; G1 carries it |
| D1 mode | **interactive, one question at a time in the chat, when needed** | the planning orchestrator asks Q-D1-01…25 in order and logs answers verbatim to `feedback/OPERATOR_FEEDBACK.md` |

Scope addition, operator verbatim (2026-09-30, during Wave 2): *"Please continue as you are. The
research/planning/synthesis/design/etc. process so far looks good and should proceed. I want to make on
adjustment/addition, which is that we should add research/synthesis/design stream(s) to do deep research on the web
into additional data sources that we might be missing for Flock, Axon, or other public-private surveillance networks.
We may find that we are missing entire geographies or classes of surveillance technology. I want as part of this next
pass for us to do an extremely careful, rigorous, and comprehensive search and review of additional datasets we might
be missing and to configure them for ingestion and ingest them into prod. Additionally, I want us to do some research
and design work into making the data itself easily exportable from the public website, including the ability to
explore each third party source, link to the ground truth, download the raw data, and see ingestion logs/metrics/timestamps
or whatever for maximal transparency. Please continue current work and fold these streams into your process"*

| item | decision | consequence |
|---|---|---|
| New Stream I (source discovery and acquisition) | **added** | rows I1–I8 (§6); the resulting sources are configured and ingested into production by Round-11 tickets after per-source HG-03 decisions; §1 item 5, T8, P15, Q-19…Q-21, Q-23 |
| New Stream J (data transparency and export) | **added** | rows J1–J4 (§6); feeds G3 and the Round-11 product tickets; §1 item 6, T9, Q-22 |

Production-fix decision, operator verbatim (2026-09-30T18:2xZ): *"I want to do all of what you are suggesting, but this work
should be planned/specified in the next round of tickets, not done now. As for what SIG is for, you can draft that yourself.
And email alerts and anything else can route to 14stevevitali@gmail.com (Steven Vitali). I will try to confirm /chrome now"*

| item | decision | consequence |
|---|---|---|
| S0 hotfixes (attribution takedown, `/editorial-standards/` fixture review, `/dispute/` notice) and G1 quick actions QA-1…QA-10 (deletion protection + retain backups, maintenance window, alert channel + policies, uptime/TLS checks, re-roll `sig-probe`, bucket versioning, `sig-web` bucket non-public, disable GitHub `reingest` schedule, restore drill, budget alert) + `/task/new/` demo pages | **all approved in principle, to be specified as Round-11 tickets — not executed now** | no further Track-0 production changes; S2 places them as the first Round-11 wave ("production safety and honesty"); each ticket carries its live stage |
| Alert / notification routing | **the operator's address (Steven Vitali)** | alert channel(s) and operator notifications route there; whether that address may be *published* on the public site (e.g. `/dispute/`) is Q-29 |
| Q-D1-01 | **delegated to the agent** | agent-drafted answer recorded as U-001, pending confirmation |
| `/chrome` | operator connecting Claude in Chrome | C2 starts once the tools are visible |

Operator, verbatim (2026-09-30T17:29:54Z): *"I confirm U-001. And Q-29 just use my personal email for now. And yes for Q-D1-02 but also think
investigative journalists and other organizers"*

| item | decision | consequence |
|---|---|---|
| U-001 | **confirmed** | the agent-drafted "what SIG is for" stands as the operator's answer |
| Q-29 | **publish the operator's personal address as the public corrections/dispute contact, for now** | Round-11 dispute/intake tickets use it; the agent's safety/spam/succession concern is recorded as an operator-accepted risk with a revisit trigger (alias when volume or exposure grows) |
| Q-D1-02 | **yes — plus investigative journalists and other organizers** (U-002) | C2 journeys weight the journalist and organizer personas; D3 sets priorities |

---

## 8. Schemas, vocabularies and conventions

### 8.1 Work-universe item (`universe/UNIVERSE.csv`)
`u_id, source_kind (deferral|requirement|backlog|risk|finding|feedback|adr_trigger|readout|manifest_row|section55),
source_ref, title, source_status, effective_status, blocker_class (engineering|live-execution|operator|human|rights|external|scheduled),
evidence, disposition, disposition_ref, rationale, stream, priority`.

**Disposition enum (exactly one):** `ticket(<row>)` · `live-return-pass(<ticket>)` · `spec-amendment(<id>)` ·
`adr-waiver(<ADR>)` · `operator-action(<owner>)` · `human-marker(<row>)` · `already-done(<evidence>)` ·
`wontfix(<reason>)` · `later-phase(<trigger>)` · `merged-into(<u_id>)`.

### 8.2 Finding (`findings/FINDINGS.csv`)
`f_id, title, stream, surface (url|path|resource), observed_at (date -u), evidence_class, evidence, severity, category,
spec_ids, status (proposed|verified|amended|refuted|merged), routed_to, operator_priority`.

**Severity.** `S0` active harm or risk in production now (data loss, exposure, false public claim) · `S1` breaks a core
user task or the truth of the record · `S2` degraded quality or debt · `S3` polish.

### 8.3 Proposed verdict vocabulary for the coverage matrix (decided at S5, applied in T4)
`MET` · `MET-DIFFERENTLY(ADR)` · **`MET-ENGINEERED`** (built and tested; a named live or human leg is owed, citing its
D-id) · `PARTIAL` · `MISSING` · `AT-RISK-INTEGRATION` · **`WAIVED(ADR)`** · `N/A-RATIONALE`.

### 8.4 Evidence storage
Text evidence (page text, JSON, command output) is committed under this directory. Screenshots, HAR files and large
captures go to `docs/build/logs/next-phase/` (gitignored), each referenced by sha256 from the finding. The validator
flags files over 1 MB in fixtures and over 5 MB anywhere under `docs/build/`. No secrets (P14).

### 8.5 Directory layout (this planning round)
```
docs/build/planning/2026-09-30-next-phase/
  META_PLAN.md              # this file — the Stage-P ledger
  baseline/                 # A1
  findings/                 # A2 + every later finding (single writer: the planning orchestrator)
  universe/                 # A3, S1
  research/  design/        # B, C5, E, F, G, H notes
  review/                   # C1–C4, C6
  feedback/                 # D1, D2
  reviews/                  # S4 adversarial reviews + REVIEW_CLOSURE.md
  data/  tools/             # CSV/JSON + extractors with tests
  NEXT_PHASE_PLAN.md        # S3 output (canonical once GATE-P signs)
  HANDOFF.md                # T6
```
Streams I and J write their notes under `research/` and `design/` and their tables under `data/`
(`source_coverage.csv`, `candidates_I<n>.csv`, `query_log_I<n>.csv`, `candidates_consolidated.csv`,
`redistribution.csv`).

### 8.6 Source candidate (`data/candidates_*.csv`)
`cand_id, name, url, publisher, publisher_type (vendor-portal|gov-open-data|statutory-report|ccops-report|agenda|procurement|grant|legislation|court|records-release|ngo|journalism|academic|crowdsourced|other),
technology_classes, geographies, coverage_estimate, format_access (api|bulk-file|html|pdf|arcgis|socrata|ckan|other),
update_cadence, volume_estimate, terms_url, terms_verbatim_excerpt, licence_guess, rights_lane, part_viii_flags,
lineage (origin|mirror-of:<id>|derived-from:<id>), registry_match (new|same-as:<source_id>|related:<source_id>),
connector_reuse, retrieved_at (date -u), found_by_query_id, evidence_class, notes`.

---

## 9. Execution protocol for Stage P

- **Dispatch.** One planning-orchestrator session reads this file, picks the next runnable row(s), and dispatches each
  to a **fresh subagent** with a prompt of this shape: *"Execute row `<id>` of `META_PLAN.md`. Read §3 (principles),
  the row block, and only its listed inputs. Write only the row's declared outputs. Get dates from `date -u`. Return
  ≤ 300 words: what you did, the output paths, new finding/universe ids, open questions."*
- **Clock (added 2026-09-30T17:56:21Z after a self-caught drift).** Every timestamp the orchestrator writes into this directory is produced by
  `date -u` in the same command that writes it — never typed or estimated.
- **Single writer.** Only the planning orchestrator edits `META_PLAN.md` (status flips, change log) and appends to
  `findings/FINDINGS.csv`; workers return rows and never write shared files (the Round-10 concurrency lesson).
- **Parallelism.** Read-only rows with disjoint outputs may run concurrently. Waves:
  - *Wave 1:* A1.
  - *Wave 2:* A2, A3, B1, B2, C1, D1 (operator), E1, E3, E4, G1, H1; **I1, J1, J2** (added).
  - *Wave 3:* B3, C2, C3, C4, (C5), E2, F2, F3; **I2, J4**.
  - *Wave 3b:* **I3, I4, I5, I6** (parallel, after I2).
  - *Wave 4:* B4, B5, C6, F1, F5, G2; **I7, J3** (J3 after C2).
  - *Wave 5:* B6, D2, F4, G3, H2, **I8**, then D3.
  - *Wave 6:* S1 → S2 → S3 → S4 → S5.
  - *Stage B:* T1 → T2 → T3 → T4 → T5 → T6.
- **Size.** 55 rows (43 + Streams I and J: 8 + 4), about 47 agent rows plus operator sessions D1, D2, D3, E and I
  rights decisions, S5, GATE-B.
- **Pauses.** The orchestrator stops at GATE-M, at D1 (waiting for the operator), at D2, at S5 and at GATE-B, and
  whenever a row is `blocked-on-operator`. `pauseRequested: true` in the CURRENT STATE block is honoured at the next
  row boundary.
- **Row completion.** A row flips to `done` only with its output path and a one-line evidence summary in the change
  log; a red or partial result stays `in-progress` or becomes `blocked-on-operator` with the reason.

---

## 10. Risks to the planning process

| risk | mitigation |
|---|---|
| Scope explosion (the universe is large) | exactly-one disposition incl. `later-phase(trigger)`; S2 time-boxes the phase |
| Operator anchored by agent findings | D1 before C6 is shared (P8) |
| Context overflow on the 679 KB LEDGER | P13; rows read the projection, §(f3) and slices |
| Baseline moves during planning (your integration) | A1 records it; the A1 delta runs before S1 and T6; isolated worktree (Q-3) |
| Repeating the date failure | P2; B4 adds a date-sanity guard before any new records are written |
| Over-optimism about human work | E3 states effort and sourcing honestly; F4 plans for "none sourced" too |
| Planning drifts into doing | P3/P10; Track 0 is the only execution path and needs a per-action go |
| Agent review mistaken for user research | P5 labels agent walkthroughs as such; D-R10-USERS-1 stays owed until real participants exist |
| Source search is shallow or unreproducible | I2 protocol with a query matrix, saturation stopping rule and logged queries (P15); I7 de-duplicates and checks lineage |
| New sources raise rights or Part VIII exposure | availability ≠ clearance; Part VIII preflight per candidate; per-batch HG-03 packets (Q-19); nothing enters `sources.toml` during planning |
| Transparency features leak restricted data or cost too much | J4 redistribution matrix + egress estimates; licence gating, scrubbing and withdrawal barrier in J3 |

---

## 11. Change log
- 2026-09-30T16:05Z — meta-plan drafted from the 2026-09-30 orientation review (four read-only research passes +
  direct verification). Awaiting GATE-M.
- 2026-09-30T16:16Z — **GATE-M signed** (§7.1). Planning worktree created (`claude/next-phase-planning` @ `b051732c`).
- 2026-09-30T16:22Z — **Track 0.1 + 0.2 done** (`baseline/TRACK0_RECORD.md`): on-demand backup `1790785111976` SUCCESSFUL; automated
  backups enabled (05:00 UTC, 7 retained, no restart); `/curate/` removed from the public web bucket, 404 on both origins.
  PITR held (enabling it restarts the instance) — operator question. 0.3 pending.
- 2026-09-30T16:32Z — PITR enabled (delegated to agent; one 503 during the restart, self-recovered); 0.3 key stays stale
  (operator); D1 to be collected interactively. D1 questionnaire committed (`a23fca8a`).
- 2026-09-30T16:36Z — **A1 done**: `baseline/BASELINE.md` + `baseline.json` (196 keys; delta re-run 0 changes). 4 new findings
  in `findings/incoming/A1.csv` (chain tip not descended from `origin/main` lockfile commit; scheduled `reingest` workflow
  failing on `main` 6/6; `sig-pg` deletion protection OFF; 9 Cloud Run jobs without triggers). F-12 narrowed: only the
  `sig-alerts` service uses `:latest`. Chrome tools not connected in this session — operator to run `/chrome` before C2.
- 2026-09-30T16:45Z — Wave 2 dispatched (A2, A3, B1, B2, C1, E1, E3, E4, G1, H1). **Scope addition by the operator
  (§7.1): Stream I (source discovery and acquisition, I1–I8) and Stream J (data transparency and export, J1–J4)**; §1
  items 5–6, T8–T9, P15, Q-19…Q-23, §8.6, waves and size updated (55 rows).
- 2026-09-30T16:58Z — **E3 done** (`research/E3-human-work.md`): minimal honest human program ≈145–375 person-hours / 3–5 months;
  $0–1k (volunteer/pro bono) to ~$6k–25k (all paid, web estimates); 0.98 gate needs ≥149 pairs/tier and is unlikely to
  certify. 8 incoming findings incl. S1: `/editorial-standards/` publicly shows a completed two-reviewer "hostile-reader
  review" by placeholder reviewers from a fixture. Q-24…Q-28 added.
- 2026-09-30T17:02Z — **E4 done** (`design/E4-rights-packets.md`): 22 operator decisions (11 rights rows, 6 dossier/pilot batches,
  5 proposed status corrections); 6 already covered by GL-GATE-07 precedent; documentcloud (no-mining terms), courtlistener,
  Part VIII screening and SRC-027 not covered; 11 incoming findings. Decisions deferred to S5 (batched with I7 packets).
- 2026-09-30T17:05Z — **H1 done** (`design/H1-integration.md`): simulated bottom-up merge `main`@#140→#190 is conflict-free and
  ends tree-identical to #190; the #141–#154 lockfile red does not affect `main` (`main` keeps its lockfile); transient red
  on `main` for one step after each of #165/#179/#185; B1 date fixes cannot precede #143 without rewriting history →
  merge #143–#190 + the correction PR in one sitting; Round 11 should pin the npm/node toolchain. 6 incoming findings.
- 2026-09-30T17:08Z — **A3 done** (`universe/UNIVERSE.csv`, 528 rows, `--check` green, 16 planning tests pass): 97 deferrals
  (36 owed), 161 requirement rows (incl. 7 N/A-RATIONALE), 36 backlog, 62 risk, 1 open ledger finding, 19 return passes,
  144 ADR triggers, 2 PENDING readouts, 6 manifest rows. Orchestrator ruling on NEW-4: ADR revisit triggers are adjudicated
  by **F3** through their BACKLOG home (each trigger already has exactly one BL row). 5 incoming findings.
- 2026-09-30T17:12Z — **J1 done** (`research/J1-exposure-inventory.md`): public bulk release (132 files / 1.05 GB, 12 compartments,
  sha256) is unlinked from the site; no source index or per-source pages; 0/255 public evidence items carry an upstream URL;
  350 real captures + 387 WORM run records + a 342-source registry exist internally. 13 incoming findings. **Orchestrator
  severity ruling: J1 NEW-2 (CC-BY `sig_graph` rows and EFF Atlas rows in the live API attributed to "DeFlock community
  map" — rights records de-duplicated by licence only) = S0 (false public attribution claim live now)**; reported to the
  operator; remediation needs a code fix + republish (Round-11 early ticket unless the operator wants a hotfix).
- 2026-09-30T17:20Z — **C1 done** (`review/PROTOCOL.md`, `review/ROUTES.csv`): 36 source route patterns vs 23 built live (208 HTML
  pages); 12 personas / 31 tasks with release-grounded expected answers; 18 heuristics; 8-dossier sample; C2/C3/C4
  procedures. Blocking for C2: Claude in Chrome must be connected (`/chrome`). Possible Part VIII issue to verify in C2
  (H12): some source names under `/dossier/unresolved/` look like personal account handles. Orchestrator note: C3's
  read-only spine queries are within the GATE-M-approved scope (P3 read-only); C3 prefers release files and uses a
  read-only DB path only if one exists without new grants.
- 2026-09-30T17:40Z — **J2 done** (`research/J2-prior-art.md`, `data/query_log_J2.csv`, 118 logged queries): exemplars —
  OpenSanctions dataset/entity/issues pages, Transitland content-hashed versions with licence-gated raw downloads,
  OpenAddresses job records, Overture release notes, OWID bundles; standards: sha256 manifests + Frictionless + SPDX
  (low), DCAT 3 (low–med), PROV-O (med), DOIs (operator gate); schema.org JSON-LD conflicts with the no-`<script>` rule
  (needs an ADR or linked metadata files); pitfall: raw audit-log republication (plates/search reasons) — Part VIII scrub.
- 2026-09-30T17:41Z — **A2 done** (`findings/FINDINGS.csv` + `.md`): F-01…F-43 re-verified (35 verified, 8 amended, 0
  refuted) + F-44 (S1: `/dossier/id/` merges Idaho+Indonesia, `/dossier/mn/` Minnesota+Mongolia). Severity: 3 × S0
  (F-01/F-02 remediated; **F-03 dispute channel promised on every page but absent → S0**), 15 × S1. Incoming findings
  from later rows are merged by the orchestrator (single writer) into FINDINGS.csv at S1 (J1 NEW-2 attribution = S0).
  **Orchestrator clarification of P3:** read-only `SELECT`s against the hosted database through an EXISTING role and
  credential path (no new roles/grants, no writes, statement timeouts, off-peak) are within the GATE-M read-only scope;
  rows that need them (B1 sqitch registry, C3) may use them and must log each query.
- 2026-09-30T17:48Z — **E1 done** (`research/E1-contradictions.md`): 21 spec↔decision/behaviour contradictions (process 8, legal 4,
  trust 4, licensing 3, safety 2). Top: E1-02 `/editorial-standards/` presents a fixture two-reviewer "hostile-reader
  review" as real (**S0**, same as E3 NEW-1); E1-05 publication rests on no counsel opinion and the promised "pending
  counsel" label is absent; E1-06/08 robots disregarded without the SIG-INGEST-037 counsel step, and the crawler contact
  URL uses the unregistered domain `sig-project.org`; E1-12 required upstream attribution missing in public downloads;
  E1-04 legal home is an individual. 15 incoming findings. E2 dispatched.
- 2026-09-30T18:00Z — **G1 done** (`research/G1-ops.md`): 17 ops risks, 14 incoming findings. Top: **G1-02 monitoring is silently
  broken** — `sig-probe` failing every sweep since 09-27 (stale baked-in config), 28 critical alerts went only to a log, no
  Monitoring policies/channels/uptime checks, `observability.yml` measures nothing; G1-01 every workload runs as the
  default compute SA with `roles/editor`; G1-03 deletion protection off + backups deleted with instance; G1-04 restore
  never drilled at scale; G1-05 buckets unversioned ("WORM" claim false); G1-06 non-public routes can ship (six demo
  `/task/new/` pages live; `sig-web` bucket publicly readable); G1-07 freshness drift (≤156k new claims since 09-27, no
  republish cadence); G1-08 33 schedules fire for the first time 10-01…10-21 (12 never-run jobs). Ten quick actions
  QA-1…QA-10 proposed (each needs an operator go); est. cost ≈$90–100/mo vs README's ≈$0/$9.
- 2026-09-30T18:12Z — **B1 done** (`research/B1-date-drift.md`, `data/date_drift.csv`): 2,891 dated occurrences scanned; 595 rows /
  2,283 occurrences are events recorded on dates they did not happen (memory 322, release-identity 75, code 70, fixture 56,
  ADR 33, sqitch 18, spec 15, jsonl 6). **Cause evidenced:** agents kept a "chain date" decoupled from the clock ("previous
  entry + 1 day") and the memory tooling accepts hand-typed dates. Sqitch planned timestamps are hashed into change ids →
  deployed lines 41–43 must never be edited (correction comments + ADR + new-line guard). Candidate `p-17b713…`: supersede,
  don't re-sign. Hazard: memory dated 10-21 makes the 10-10 replay look overdue. Draft correction ADR in §8; Q-B1-1…4 in §9.
  7 incoming findings.
- 2026-09-30T18:40Z — **B2 done** (`research/B2-append-only.md`, `data/append_only_violations.csv`): 539 rows over 501 commits;
  losses in DEFERRALS (14), LEDGER (6 incl. c2055d96's 53 GATE DECISIONS rows — 6 exist nowhere else; GL-GATE-06 orphaned),
  contracts (6, incl. P25.5 AC weakened+ticked), runs (5), readouts (5), BUILD_INDEX (3), events.jsonl (3; P33.1 flipped 8
  events in place). Restoration = appended, hash-checked "RESTORED from <sha>^" blocks; guard = `check-append-only` CI
  check with an `APPEND_ONLY.toml` region policy + a date ≤ commit-date rule. 9 incoming findings.
- 2026-09-30T18:41Z — **I1 done** (`research/I1-source-coverage.md`, `data/source_coverage.csv`, 369 rows): 218 ingested-live,
  19 permitted-not-ingested, 101 gated, 4 refused, 27 candidates. Blind spots: Flock only via one mirror (~23% of networks),
  Axon/Fusus/RTCC nothing, 22 states without a dossier (incl. OK), statutory ALPR/CCOPS reporting thin, 10 states without
  an official camera registry, procurement cooperatives all gated, zero channels for social-media monitoring/forensics/
  school surveillance, drones/gunshot/FR/CSS only via Atlas. 9 incoming findings (S1: country/state code collisions, axis-
  swapped/mislabelled coordinates, only camera registries reach dossiers, all registry cameras typed `traffic_camera`).
- 2026-09-30T18:42Z — **F2a done** (`research/F2a-verdicts.md`, `data/coverage_delta_F2a.csv`): 49 engineering ids → 7 become MET,
  35 PARTIAL, 2 MISSING, 2 AT-RISK (new reasons), 1 MET-DIFFERENTLY, 2 N/A; ticket groups proposed. 10 incoming findings.
- 2026-09-30T18:42Z — **F2b done** (`research/F2b-verdicts.md`, `data/coverage_delta_F2b.csv`): 55 gated/reduced-scope ids →
  11 MET, 14 MET-ENGINEERED, 14 PARTIAL, 6 MISSING, 4 AT-RISK, 5 WAIVED(ADR), 1 MET-DIFFERENTLY(RISK); verdict vocabulary
  finalized (+4 matrix columns: required_domain, achieved_domain, owed_legs, accepted_scope). S1: the 75 boilerplate
  MET-DIFFERENTLY rows are prefix defaults, 7/13 sampled not met. 8 incoming findings.
- 2026-09-30T18:43Z — **E2 done** (`design/E2-governance-options.md`): 23 memos (+1 side memo on the dispute channel); 8
  honesty fixes needing no policy decision; operator decisions on governance, legal home, counsel, robots, DB-right,
  human evaluation, outreach, design center. 3 incoming findings (robots disregarded on 122 hosts; no opt-out mechanism).
- 2026-09-30T19:05Z — Wave 3/4 dispatched: B3, B5, I2, J4, F1. Chrome tools still not visible (awaiting the next operator
  turn after `/chrome`).
- 2026-09-30T19:10Z — **F3 done** (`research/F3-backlog.md`, `data/backlog_triage.csv`): 36 BL rows → 10 closed-by-later-round,
  4 superseded, 2 accepted, 20 still open (BL-001 re-opened); 62 RISK rows → 21 closed, 4 superseded, 1 accepted, 36 re-homed;
  144 ADR triggers → **68 fired** (42 with no recorded response), 5 superseded, 71 quiet; 58–60 orphan not-MET ids homed.
  Proposed Round-11 themes: R11-TRUTH, -GOV, -HUMAN, -OPS, -RECORD, -SOURCES, -TRANSPARENCY, -DATAMODEL, -DEBT,
  OPERATOR-QUEUE, LATER-PHASE, ADR-TRIGGER-REGISTER. 11 incoming findings (incl. live API minting `https://sig.example/id/`
  placeholder IRIs).
- 2026-09-30T19:20Z — **C3 done** (`review/DATA_TRUTH.md`, `data/number_trace.csv`, 453 traced numbers: 378 match, 50 mismatch, 22
  ambiguous, 2 untraceable, 1 stale). Release files are internally consistent; the defects are page claims and the API.
  **S0:** C3 NEW-1 the public API `/v1/dossier/{scope}` returns the same placeholder subjects/sources for every scope;
  C3 NEW-2 personal ArcGIS account handles embedded in public source ids (Part VIII; redacted in the committed CSV).
  S1: site-wide provenance block on every dossier; "human-verified" holdout false; coverage "resolved" vs 5,290
  conflicted; points outside their jurisdiction (CA←FL 838, GB-ENG axis-swapped 562, TH←HK 155, ID←Indonesia/Idaho);
  "0 stale" when not evaluable; map attribution to "SIG contributors"; API coverage "complete" with 0 evaluated.
  Systemic causes recorded. 21 incoming findings.
- 2026-09-30T19:40Z — **C4 done** (`review/R10_PREVIEW.md`): all Round-10 surfaces run locally (web fixture mode; release trees;
  release search API ×3 registries; intake receiver on local PG18 via podman — non-operational 503 and an operational walk).
  Export-mode build fails (candidate lacks `leverage.json`/tiles). Readiness: 5 surfaces blocked, 6 needs-work, 1 ready
  (the intake 503 page). 11 × S1 incl. two S0-on-exposure (research dossiers present stand-in documents as real captures
  with real URLs; the G3-accepted candidate is a fixture with `example.test` evidence), broken release-archive relative
  links, "Reviewed" headline while review `not_run`, moderator view HTTP 500 on PG, no production routing for `/v1`
  release search or `/intake`, `rsync --delete` deploy would wipe the release tree. 32 incoming findings.
- 2026-09-30T19:41Z — C2 dispatched in **headless Chrome** (Claude-in-Chrome tools never became visible to this session;
  orchestrator judgement per Q-6 — an interactive real-Chrome pass may be added later). D1 continues (U-001 confirmed,
  U-002 recorded; Q-29 answered). F5 dispatched.
- 2026-09-30T19:55Z — **B5 done** (`research/B5-orchestration-retro.md`): five lessons (verification stopped at the repo boundary;
  gates became a throughput device — 35/76 gate records answered at a pause with evidence; status words collapsed layers;
  append-only unenforced; harness/planning switches untracked) and **18 operating rules OM-01…OM-18** (pasteable OPERATING
  MODE + ticket-template blocks) for Round 11 — to be placed by B3/T5. Operator questions (B5 §8): which harness ran the
  untrailered stretches; were the full GATE-G3/ACCEPT-R10 texts seen before approval; was the P31.5 pause a harness switch.
  8 incoming findings.
- 2026-09-30T20:05Z — **B3 done** (`design/B3-ledger-redesign.md`): LEDGER 679,109 B (PHASE LOG 72%; CURRENT STATE 122,978 B of
  which 114,735 B PRIOR chains; ~32k tokens to orient); target: head ≤ 12 KiB, orient ≤ 48 KiB, values-only CURRENT STATE
  (≤ 256 B/line), head archived byte-for-byte under `reports/memory-repair/` with sha256 pointer, fresh Round-11 OPERATING
  MODE skeleton (§3.6), appended restorations/corrections/RETURN PASS/PHASE LOG index. `nextTicket` → first Round-11 row
  with 184–187 marked deferred (alternatives for F4). Shadow mode: split D-R10-MEMORY-1 (repair + enforce obligation
  events; keep projection as CI-verified orient view; keep closeout journal shadow). Seed = 10 ordered commits C0–C10;
  early tickets M1–M6; validator requirements V1–V11 for B4. 8 incoming findings. B4 + F4 dispatched.
- 2026-09-30T20:15Z — **F1 done** (`research/F1-owed-register.md`, `data/owed_register_adjudication.csv`): 36 rows → 9 live-return-pass,
  8 ticket, 7 operator-action, 4 human-marker, 3 wontfix, 3 later-phase, 2 already-done; proposed corrections D-SOURCES.12-1
  →DONE, D-SOURCES.7-1→PARTIAL, D-P21.3-2→DONE (hosted jobs already use every credential); 2 of 13 future-dated closures
  do not hold live (D-P31.1-1 contradiction serve 13.6 s warm; D-P31.5-2 flagged org still named) because the hosted API
  still runs the 09-25 image; **32/36 reachable without recruiting**; dependency-ordered Round-11 path recorded. 8 incoming
  findings (SAM.gov sweep restarts at keyword 0; ADR-124 operator allows missing; MuckRock 0 hosted claims). G2 dispatched.
- 2026-09-30T20:25Z — **J4 done** (`research/J4-redistribution-matrix.md`, `data/redistribution.csv`, 342 sources): of 237 live/permitted,
  raw-ok 54, derived-only 172 (SIG's own public-record / operator-accepted-DB-right bases cover facts, not bytes), restricted 10,
  unknown 1; 5,110 public rows come from sources whose own terms forbid redistribution (S1); full release 1.05 GB ≈ $0.13
  per download from GCS; egress ≈ $13–600/mo (≈$2.8k worst case) vs ≈$0 via an R2 mirror; scrub and Part VIII rules
  defined; operator decisions feed Q-22. 7 incoming findings (terms-forbidden sources published; new OSM/"SIG project"
  misattributions; only 349 of 6,144 capture digests have stored bytes; seed fixture sources served live).
- 2026-09-30T17:56:21Z — **F4 done** (`design/F4-s3-spine.md`): recommends **Option B (staged supersession)** — rows 184–187 cannot be re-entered as
  written (their new prerequisites would be later rows; row 188 already consumed P32.23's output; HUMAN-H4 binds a
  fixture-only snapshot and couples two unrelated reviews). New non-blocking markers HUMAN-H6 (labelling pilot) and
  HUMAN-H7 (dossier semantic review); EV1 reviewer labelling surface on an isolated eval DB; EV2 honest auto-write posture +
  public evaluation report; remaining chain seeded when trigger T-EVAL-1 fires; `nextTicket` at seed = row 201. Effort B:
  86–197 h (operator 28–61 h), $0–~8k, 3–5 months from recruiting. Q-24: tier 1g, 149 pairs zero-error certifies only
  ~47% of the time at true 0.995 (~11% with 1% insufficient-evidence) → pilot decides certify vs ~100-pair measure-only.
  Q-25: operator may hold custodian, method reviewer, one hostile-reader seat (disclosed); labelers + dossier reviewer
  external. 10 incoming findings, incl. **this ledger's own change log was future-dated** (see correction below).
- 2026-09-30T17:56:21Z — **CORRECTION (append-only, P2/P7): change-log timestamps from 16:58Z onward were typed by estimate, not read from
  the clock, and drifted up to ~2.5 h into the future** — the same failure this plan exists to fix (F-21/B1). True times
  are the planning commits' UTC timestamps (`git log --date=iso-strict`, converted to UTC). Recorded → true:
  E3 16:58Z → 16:52:52Z (6266f393) · E4 17:02Z → 16:55:28Z (c7c773e8) · H1 17:05Z → 16:56:41Z (ce45d548) ·
  A3 17:08Z → 16:58:30Z (81050955) · J1 17:12Z → 16:58:41Z (15975da7) · C1 17:20Z → 16:59:25Z (4df1552f) ·
  J2+A2 17:40Z/17:41Z → 17:01:09Z (5a0015db) · E1 17:48Z → 17:01:53Z (fddfc1b4) · G1 18:00Z → 17:03:33Z (7642f8d1) ·
  B1 18:12Z → 17:09:11Z (c28756d9) · operator production-fix decision (§7.1) "18:2xZ" → received before 17:10:49Z
  (e5725b7b) · B2/I1/F2a/F2b/E2 18:40–18:43Z → 17:20:51Z (4aff9a48) · Wave-3/4 dispatch 19:05Z → ≈17:21Z ·
  F3 19:10Z → 17:28:08Z (dfe34ad9) · C3 19:20Z → 17:29:01Z (e8e6df25) · C4 19:40Z/C2 dispatch 19:41Z → 17:35:35Z
  (2cf03075) · B5 19:55Z → 17:38:19Z (63d6a404) · B3 20:05Z → 17:39:46Z (1b9b57b2) · F1 20:15Z → 17:42:08Z (41ab9521) ·
  J4 20:25Z → 17:55:17Z (56c53158). Entries before 16:58Z were clock-derived and stand. **Rule from here on:** every
  timestamp this orchestrator writes is produced by `date -u` inside the same command that writes it (§9); B4 adds the
  date ≤ commit-time guard that would have caught this.
- 2026-09-30T17:58:06Z — **I2 done** (`design/I2-source-search-protocol.md`, `data/search_matrix.csv`): 29 technology classes (+multi) mapped to all 36
  ontology families (new: commercial plate data, traffic enforcement, other biometrics, aerostats, robots, intercept, electronic
  monitoring, weapon detection); 16 channels (+international map); 14 geography groups (10 priority states; 36 thin top-100
  cities); **190 matrix cells** — I3 40 (budget 150 queries), I4 74 (170), I5 53 (150), I6 23 (130) — every class×channel×geo
  combination in exactly one cell (checked). Calibration leads: ArcGIS catalog 1,266 "flock" items (mostly agency layers);
  Atlas cites 26,294 links (507 Flock portals); MN legislative library ALPR audits; VA State Police ALPR report; 2025 NAMSDL
  ALPR-law survey; "Connect ‹Place›" Fusus registries; >1,000 DFR waivers. Guardrails: Flock origin portals refused (no
  scraping/archives); never download plate/audit/student rows; personal-account ArcGIS layers presumed DeFlock/OSM copies.
  §8.6 candidate schema extended per I2 §12. **I3–I6 dispatched** (parallel).

---

## Appendix A — Baseline findings register (preliminary, observed 2026-09-30; A2 re-verifies every row)

`V` = verified directly in the 2026-09-30 session; `R` = reported by a read-only research pass, not yet independently
re-checked.

**Production and operations**

| id | finding | evidence | sev | stream |
|---|---|---|---|---|
| F-01 | Cloud SQL `sig-pg` automated backups disabled; 0 backups; backup bucket holds two 146 KB dumps from 09-15 (5-claim seed); ADR-081 says managed backups replaced the drill | `gcloud sql instances describe sig-pg` (V) | S0 | 0.1, G1 |
| F-02 | `/curate/` publicly served (200): demo curation pages, form posting to `127.0.0.1`; P30.3 stripped it, the 09-27 republish re-uploaded it | `curl https://surveillancegraph.org/curate/` (V); `ops/src/ops/publish.py:176` (R) | S0 | 0.2, G1 |
| F-03 | Every page advertises "Dispute or correct this record — one click", but `/dispute/` has no channel and `/intake/` is 404 (docs claim 503) | live read (R); `README.md:27,190` | S1 | C, G2 |
| F-04 | No Oklahoma dossier (`/dossier/ok/` 404); `unresolved` counted among 55 jurisdictions and holds ~71% of observations; codes mix US states and countries (`ca` = California, `ca-on` = Ontario) | live read (R) | S1 | C |
| F-05 | "How we know this" block shows site-wide totals on every page (Alabama: "218 independent sources"); tier breakdown sums 6 short of 2,423,200 | live read (R) | S1 | C3 |
| F-06 | Methodology shows P/R/F1 1.000 on "the frozen, human-verified holdout" beside "LLM-bootstrapped gold set"; κ row malformed | live read (R) | S1 | C3, E1 |
| F-07 | As-of "permalinks" do not pin (static nginx ignores the query string) | `ops/web/nginx.conf` (R) | S2 | C, G3 |
| F-08 | Freshness shows 178 "ok" with every volatility class "unknown"; the site is frozen at 09-27 while the API reads a spine that ingests daily | live read (R) | S2 | C, G1 |
| F-09 | Raw UUID node labels on `/network/`; disclaimer repeated 126× on home; `/v1/export` advertises `entities.parquet` (404); no sitemap; `www` redirects with `:443`; `/map/` says "no client JavaScript" while shipping an island; contribution-back OE link points to `/methodology/` | live read (R) | S3 | C |
| F-10 | `REPUBLISH_LIVE_2026-09-27.md:77` claims `has_vendor` links render on `/dossier/al/`; live has 0 rows | live read (R) | S2 | B, C3 |
| F-11 | No release id or commit stamp in served HTML | live read (R) | S2 | G3 |
| F-12 | `sig-alerts` runs on `:latest` (vs ADR-111); live SAM.gov cron differs from `ops/cadence.toml:317`; `ops/gcp/README.md` cost figures stale | gcloud read-only (R) | S2 | G1 |
| F-13 | D-P31.4-1: the OSM monthly replay fires 2026-10-10T03:35Z (pinned image, 36 h timeout); verifiable only afterwards | scheduler read-only (R) | — | G1 |

**Round-10 reality**

| id | finding | evidence | sev | stream |
|---|---|---|---|---|
| F-14 | No Round-10 surface is deployed: `/releases/`, release search, `/research-dossier/`, `/intake/` all 404; API OpenAPI lists only pre-Round-10 routes; islands are the P27.9 versions | live read (V: 404s; R: rest) | S2 | G2 |
| F-15 | Release candidate `p-17b713…` holds 0 records (16-claim fixture DB); P32.25 "publish" went to a repo folder served locally | `reports/p32.25-accepted-release-verification/README.md` (V) | S2 | G2 |
| F-16 | OKC/Tulsa/San Diego dossiers are built from hand-authored stand-in documents (disclosed); several Round-10 ids marked MET on reduced scope (TRUST-009/010, FIND-006, DOS-002…005, ACQ-004) | `tests/connectors/fixtures/dossier/SOURCES.md` (V); spec `:7377,:7381` (R) | S1 | F2, E1 |

**Integration and CI**

| id | finding | evidence | sev | stream |
|---|---|---|---|---|
| F-17 | `main` == P31.4 tree (#140 merged 09-30 UTC); 49 PRs open (#141–#190), not the 77 reported; memory does not record operator merges | `git rev-parse origin/main^{tree}`; `gh pr list` (V) | S2 | H1, B |
| F-18 | #141–#154 CI red since 09-25 (`web`, `composed`): `npm ci` lockfile out of sync (`@emnapi/runtime`) | `gh pr checks`, Actions logs (V) | S1 | H1 |
| F-19 | #165, #179, #185 red on their own heads: tests pin living build-memory state and the orchestrator committed inserts, pauses or signatures after close; 11 test files read living records | Actions logs (V); grep of `tests/` (V) | S1 | B4, H1 |
| F-20 | The chain never consulted CI (by skill design); "green" was local | skill text; CI history (V) | S1 | B4, B6, H2 |

**Build-memory integrity**

| id | finding | evidence | sev | stream |
|---|---|---|---|---|
| F-21 | Future-dated records: ~25 Round-10 events recorded 10-01…10-21, committed 09-25…09-28 (e.g. the "2026-10-19" S3 deferral and GATE-G3 signature are `a33cd6ec` / `95c8a73f` on 09-27); earlier episodes in Round 3, P25, Round 9; leaked into 20 ADR `Date:` headers, §55 spec text, `ops/src/ops/release_candidate.py` constants, 11 `db/sqitch.plan` timestamps (some deployed to hosted DB), the G3-signed candidate identity digest, and `events.jsonl` `recorded_at` | git log vs content (V for key cases; R for inventory) | S1 | B1 |
| F-22 | `c2055d96` (09-18) deleted 53 append-only GATE DECISIONS rows (HG-14 signature, HG-13 A1–A8, GL-GATE-01…06, counsel/go-public dispositions); recoverable from `c2055d96^` | `git show c2055d96` (V) | S1 | B2 |
| F-23 | LEDGER 679 KB; CURRENT STATE ~123 KB of PRIOR chains; header says "gitignored, never commit"; OPERATING MODE points to retired `.agents/scratch` path and "17 tickets"; Round-10 amendment says "do not resume until Codex reports"; `IN-PROGRESS` vs enum `IN_PROGRESS` | `LEDGER.md:1-52` (V) | S1 | B3 |
| F-24 | PHASE LOG out of order; 17 landed tickets lack PHASE LOG entries; BUILD_INDEX gaps (no GATE-G3/GATE-ACCEPT rows, rows 76–81 "PR pending", duplicate seq 170) | LEDGER/BUILD_INDEX (R) | S2 | B3 |
| F-25 | `returnPass` key and RETURN PASS table stale; the accurate list is `OPERATIONAL_READINESS.md §(f3)` | (R) | S2 | B3 |
| F-26 | `obligations/events.jsonl` rewritten wholesale three times; 97 events, 0 transitions | (R) | S2 | B2, B3 |
| F-27 | All validators pass despite F-21…F-26 (structure checked, not truth); the "independent" P33.1 gap analysis missed the dates | validator runs (V: `check-build-memory` exit 0) | S1 | B4 |
| F-28 | Stale landings in the projection (P31.18 never recreated, etc.); D-SOURCES.12-1 likely mis-statused; D-SOURCES.9-2 blocker pre-dates GL-GATE-08; D-FEDERAL.1-1 cadence described three ways | (R) | S2 | F1, E4 |
| F-29 | GATE-G3 and ACCEPT-R10 readouts written by the agent from short approvals; the signing commit removed the template line "an agent must not sign…"; scope clauses (a)–(c) are agent text | readouts + commit diff (R) | S1 | B4, E1 |

**Spec, coverage and backlog**

| id | finding | evidence | sev | stream |
|---|---|---|---|---|
| F-30 | 69 not-MET ids (Appendix C); 55 appear in no BACKLOG/DEFERRALS/manifest row; 19 routed to long-landed P21.x tickets; pre-Round-10 verdicts not refreshed since ~P21 | `COVERAGE_MATRIX.csv` (R) | S1 | F2 |
| F-31 | Spec MUSTs contradicted by operator decisions: SIG-PUB-008, SIG-GOV-012, counsel (R-01), SIG-INGEST-037 / §26 rule 7 / robots, SIG-CONTRIB-012, SIG-SEC-003 | spec lines; LEDGER GATE DECISIONS (R) | S1 | E1 |
| F-32 | Process requirements unmet: `check_spec_src.py` not in CI (SIG-ENG-039); ADR index has 79 rows of "—"; `traceability.md` / `risk_register.md` untouched since 09-14 (SIG-ENG-031); Part X covers phases 0–18 only; `TICKET_VS_SPEC.md` covers P00–P18 only | (R) | S2 | B4 |
| F-33 | 32 open BACKLOG rows, several apparently satisfied by later rounds but never closed | `BACKLOG.csv` (V: counts) | S2 | F3 |
| F-34 | SIG-EXPORT-012 / SIG-RECON-058 still describe ADR-092 compute-on-read, superseded by ADR-099/101 | spec (R) | S3 | F2, T1 |
| F-35 | `docs/3_sig_golive_spec.md` is not built or validated; GL-GATE-06…08 exist only in the LEDGER | (R) | S3 | T1 |

**Orchestration process**

| id | finding | evidence | sev | stream |
|---|---|---|---|---|
| F-36 | Gates were mostly pre-answered, blanket, pre-authorized or delegated; `blockedOn` never set in 194 ledger commits; human evaluation deferred four times | LEDGER GATE DECISIONS; git (R) | S1 | B5, E |
| F-37 | Most rounds planned outside `decompose-spec`; harness switched mid-round twice; date drift clustered in Devin-run stretches | git trailers (R) | S2 | B5, Q-16 |
| F-38 | The orchestrator made production changes outside tickets (Cloud SQL scale-up, reconnect drill, `min-instances`) | memory notes; `91521187` (R) | S2 | B5 |
| F-39 | `orchestration/` (Dagster, ADR-016) is ~560 LOC of glue; real scheduling is shell + Cloud Run jobs + Cloud Scheduler | code (V) | S3 | F2 |

## Appendix B — Owed register snapshot (36 rows = 32 OPEN + 4 PARTIAL; source `OPERATIONAL_READINESS.md §(f3)`)

| blocker | rows |
|---|---|
| Operator credentials / accounts (5) | D-P21.3-2 · D-P21.5-1 (PARTIAL) · D-P21.7-1 · D-SOURCES.7-2 · D-SOURCES.8-2 |
| Rights / reviewer, HG-03/04 (6) | D-JURIS.2-1 (PARTIAL) · D-SOURCES.2-2 · D-SOURCES.7-1 · D-SOURCES.8-1 (PARTIAL) · D-SOURCES.9-1 · D-SOURCES.9-4 |
| Human decision or review (10) | D-R10-HUMAN-1 · D-R6.1-EVAL · D-P30.2b-1 · D-R10-USERS-1 · D-P32.3-1 · D-R10-PUBLISH-1 · D-R10-MEMORY-1 · D-P32.16-1 · D-R7.1-AUTH · D-R7.2-SEND |
| Live execution after approval (7) | D-R10-LIVE-1 · D-P32.23a-1 · D-R10-SOURCES-1 · D-P32.18-1 · D-P32.19-1 · D-P32.20-1 · D-P32.21-1 |
| Scheduled / external (4) | D-P31.4-1 (2026-10-10 cron) · D-FEDERAL.1-1 · D-SOURCES.9-2 · D-SOURCES.9-3 |
| Engineering / maintainer decision (4) | D-P32.10a-1 · D-P32.16a-1 · D-P30.2b-2 · D-SOURCES.12-1 (PARTIAL) |

Deferred manifest rows: 184 HUMAN-H4 → 185 P32.22a → 186 HUMAN-H5 → 187 P32.23 (LEDGER `nextTicket: HUMAN-H4`).
Unused rows: 158 (P31.17, dropped), 159 (P31.18, moved to Round 10; never recreated).

## Appendix C — Not-MET requirement snapshot (69 of 715; `COVERAGE_MATRIX.csv`)

Verdicts: 54 PARTIAL · 10 MISSING · 5 AT-RISK-INTEGRATION.

- **Human- or operator-gated (20):** CONTRIB-012, CONTRIB-012a, CONTRIB-013; GOV-012, 013, 015, 016, 021, 022, 023,
  024; EVID-019; SEC-003; UI-001; LIC-012; EVAL-001, 002, 005, 006, 007.
- **Engineering (15):** PUB-007, PUB-012, PUB-015, PUB-016; INGEST-046b, 046c; UI-010, UI-040; EPIS-018;
  RECON-039, 040; SEC-005, SEC-006; STORE-004, 005.
- **Claimed but no id-linked test (34):** ONTO-001, 028, 035, 051, 054, 055, 057, 057a, 060, 064, 065;
  INGEST-004, 005, 006, 007, 008, 010, 025a, 025b, 025c, 041, 048; GEO-002, 005, 007; STORE-013, 037, 044, 045;
  RECON-052; ENG-004, 034; EVID-001; CONTRIB-019.
- **MISSING (subset of the above):** CONTRIB-012, 012a; SEC-003; EVAL-005, 006, 007; PUB-015, 016; INGEST-046b, 046c.
- **AT-RISK-INTEGRATION:** PUB-007, UI-010, EPIS-018, RECON-039, RECON-040 (several likely stale — F2).
