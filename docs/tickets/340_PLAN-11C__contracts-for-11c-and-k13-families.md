<!-- Full contract written 2026-10-06 by PLAN-11B context C12 (row 239, `decompose-spec mode=extend`, Round-11 plan row 340, `NEW (S4c)`); it replaces the T3 skeleton under the same name — the skeleton's provisional context table cited stale row ids; this contract's table follows the ratified `data/round11_plan.csv` rows 344–420 as written. Planning is not execution evidence. -->
# PLAN-11C — decompose-spec mode=extend — full 11C contracts + K13 UX requirement families

- **Sequence:** 340 of 510 · **Phase:** Round 11 / P35 (sub-round 11B) · **Kind:** plan
- **Row kind (manifest):** plan — a contract-authoring row run like a ticket; each of its contexts runs `decompose-spec mode=extend`
- **Tag:** round11-11B
- **Harness:** devin-desktop/swe-2-high/subagent
- **base_branch:** current checkout — the branch the previous row left checked out; this row works on `r11/PLAN-11C-contracts-for-11c-and-k13-families`, PR base = that branch (H2 PR-1)
- **Depends on:** PLAN-11B — the plan cell, verbatim (row 239's contracts, family append and C13 review landed; the 11B OM-20 list exists so the 11C list can follow its shape)
- **Run:** `implement-spec spec=docs/tickets/340_PLAN-11C__contracts-for-11c-and-k13-families.md live_verification=false` — dispatched as the twelve ≤ 1-run contexts below (C1…C12), one fresh sub-agent each, in order; each context invokes `decompose-spec mode=extend` (Phase 3 contracts; C12 Phase 4 review) on its scope only
- **Gate status:** `none (plan only, OM-03)` — the plan cell, verbatim; rows enter only from the ratified plan: `data/round11_plan.csv` as ratified at GATE-P (S5) and amended at S6/S6b/S6c
- **OM-20 status:** not an OM-20 row — it drafts the 11C list for GATE-G5, approves nothing
- **Live stage:** none — the plan cell, verbatim
- **Live window:** `while P35.63 waits for its HG-11 go` — the plan cell, verbatim: a scheduling preference, not a production window; the row must finish before GATE-G5 (row 343) so the G5 packet cites written 11C contracts (plan note verbatim: "written before GATE-G5 so G5's OM-20 list cites written contracts")
- **Production mutations:** none
- **Size budget:** 7.0 runs (the plan row's `est_runs`, verbatim; plan §8.1's table shows 6.0 — a plan-internal drift the C12 review records, not resolves) as twelve contexts of ≤ 8 rows each (seams below; the plan row's "~7 contexts" fan-out (S4c FEA-01) would not leave working-set headroom — the same SEED-13e sizing rule that moved 11B to ≤ 8-row batches); no context over 1.0 run or ~150k tokens loaded; contract files and the spec append are the output (generated `docs/2_canonical_design_spec.md` excluded)
- **Load (token-counted, per context):** ≈ 320,000 B → ≈ 106,700 tokens (bytes÷3) · ≈ 80,000 (bytes÷4) for the common set, one 8-row batch's allowance and every context-only entry (an upper bound: no context loads both the C1-only K13 family set and another context's batch); ≤ ~150k → no split (A-15, §8.5); C12's Phase-4 review re-measures

## Goal

Every 11C chain row (rows 344–420, P36 "the public face" — the OSM/ALPR origins, the rights batch, the three connectors, and the K13 web redesign through its acceptance rows, plus the nested PLAN-11D contract and the GATE-G6 marker) gets an execute-grade contract before GATE-G5 — written from the ratified plan rows, sized for Devin Desktop's 256k window and reviewed in a fresh context — and the K13 UX requirement families the 11C contracts cite are appended to the spec, so GATE-G5's OM-20 list for 11C names written contracts.

## Load (read these — do not re-read others)

Paths under `PD/` are under `docs/build/planning/2026-09-30-next-phase/`. Byte counts are UTF-8 bytes of exactly the named part; figures carried from the PLAN-11B contract where the same load applies. Every context loads the common set; each adds only its batch.

- `AGENTS.md` — root agent guide (precedence, gotchas, Do/Don't) — 15,220 B
- `docs/build/LEDGER.md` — orient region only (line 1 → before `## OPEN FINDINGS`; counted at its 12 KiB budget, SIG-MEM-010) + the last three PHASE LOG entries if the head points there — 12,288 B
- `docs/build/reports/current/CURRENT.md` § Obligations — the index of owed rows (orientation only — it never replaces DEFERRALS) — 8,191 B
- `docs/tickets/DEFERRALS.md` — DEFERRALS-first (AGENTS.md gotcha 8): read in full the owed rows the batch's rows own or close — not the whole file. Counted as a 16 KiB allowance (re-measure at dispatch) — 16,384 B
- `docs/tickets/00_MANIFEST.md` — § Operating rules (binding) + this row's chain line + the 11C banners and rows 344–420 — 30,720 B
- `docs/2_canonical_design_spec.md` § Part 0 · 3. First principles · Appendix E — always in scope — 24,696 B
- `~/.claude/skills/decompose-spec/SKILL.md` — `mode=extend`, Phase 3 contract rules, Phase 4 review — 24,720 B
- `docs/tickets/_TEMPLATE.md` + `~/.claude/skills/build-memory/templates/ticket.md` — the contract templates — 2,977 B + 2,773 B
- `docs/tickets/239_PLAN-11B__contracts-for-11b-and-transp-family.md` — the plan-contract shape this file follows — 22,925 B
- a landed 11B contract (e.g. `docs/tickets/338_P35.61__…` or `331_P35.53__…`) + `docs/tickets/343_GATE-G5__11b-check-in.md` — the ticket and gate-marker shapes — 40,960 B
- `PD/NEXT_PHASE_PLAN.md` § 3.3 operating clauses + § 8.1 Shape and counts · § 8.3 Gates · § 8.4 Live stages · § 8.5 Sizing — 21,333 B
- `docs/2_canonical_design_spec.md` § 0.3 Requirement identifiers + § 56.8 Families appended by later rows — 4,372 B
- **C1 only:** `PD/data/k13_requirements.csv` (the 51 UXR rows) + `PD/data/k13_tickets.csv` (the K13 ticket map) + `PD/design/K13-ux-synthesis.md` § 6 (the requirements the UXR rows carry) + the K-series design-note draft-requirement sections the UXR-A01…A13 adoption rows adopt (counted as a 60 KiB allowance, re-measured) — 25,895 B + 32,831 B + 40,960 B + 61,440 B
- **C2 and C12 only:** `PD/data/acquisition_plan.csv` + `docs/build/reports/later-register/LATER_REGISTER.md` + `docs/tickets/DEFERRALS.md` rows for the placements PLAN-11B's C13 hands here (`grep`; counted as an 8 KiB allowance) — 8,192 B
- **Per batch (allowance, re-measured by each context):** the batch's ≤ 8 current contract files, their `data/round11_plan.csv` and `ticket_catalog.csv` rows and `stageB/T3_contract_map.csv` rows, and only the design-note sections each row cites — counted as 8 KiB per row, 64 KiB for an 8-row batch — 65,536 B
- `docs/adr/ADR-171-outreach-timing-owed-later-phase-no-outside-contact.md` § Decision — the outreach-owed rule every connector/acquisition row applies (deliverable 7a) — 10,076 B
- `docs/build/reports/plan-11b/TRANSP_id_map.csv` + `docs/tickets/REQUIREMENT_INDEX_R11.md` — the landed family map and index the K13 append extends — 16,384 B
- `docs/tickets/340_PLAN-11C__contracts-for-11c-and-k13-families.md` — this contract — 20,480 B

**Token count (counter `utf8-bytes÷3 | ÷4`, the named proxy of S6R-27 — `swe-2-high`'s tokenizer is unknown):** ≈ 320,000 B → ≈ 106,700 (÷3) · ≈ 80,000 (÷4) per context (upper bound). A context whose batch needs more than its allowance shrinks its batch (the seam moves; the order does not) and records it.

## Contexts and seams (≤ 1 run each; plan row: "fan-out ~7 contexts + Phase-4 sizing review" — S4c FEA-01, before the ≤ 8-row sizing rule)

| ctx | scope | notes |
|---|---|---|
| C1 | **K13 UX requirement families** + rows 344–346 (3) | the families must exist before the K13 contracts (rows 356+) cite them; the family job is heavier than 11B's so the row batch is smaller; P35.2 (346) re-confirms SIG-OPS-007's owner; P37.2 (345) carries ING-GO-C verbatim |
| C2 | rows 347–354 (8) | rights/connector block: P36.2 carries the out-of-rule rights re-decision (T3 fold — sized at the Phase-4 review); P36.76/77/78 are connector rows — deliverable 7a (outreach-owed) applies; P36.13 OM-20 |
| C3 | rows 355–362 (8; into the K13 W1 wave) | P36.16 design tokens opens the UX block; the K13 families must already exist |
| C4 | rows 363–370 (8) | P36.79's restricted-bucket write is an OM-20 named mutation |
| C5 | rows 371–378 (8) | P36.79 held-out relevance set written by a separate agent context (B-28b) is in this batch; P36.33's host-create is OM-20; P36.38 is a never-pre-authorised API roll |
| C6 | rows 379–386 (8) | P36.75's hosted claim write is OM-20; P36.43's gated scheduler lines carried verbatim |
| C7 | rows 387–394 (8) | P36.44's scheduler job and P36.46's run-log writes are OM-20 candidates |
| C8 | rows 395–402 (8) | |
| C9 | rows 403–410 (8) | P36.66a/b are already T3 splits under the TX-13b banner — contracts, never re-splits |
| C10 | rows 411–418 (8; to PLAN-11D) | P36.68's mirror writes are OM-20; P36.72a/b are the acceptance pair (b carries the HG-11 Class S readout, never pre-authorised); **PLAN-11D (418) gets a plan-kind contract modelled on this file** — its own contexts dispatch under row 418 later ("written before GATE-G6") |
| C11 | rows 419–420 (2) | P36.73 capstone (live-read sweep + GATE-G6 packet) and the GATE-G6 gate marker (guard sentence; it collects ING-GO-D, the Wave-D flip list, the 11D OM-20 list, the standing-go renewal) |
| C12 | **fresh-context Phase-4 sizing review** of all 11C contracts | splits, the 11C re-split decision with counts, requirement index, the 11C OM-20 list draft for GATE-G5, the 11C outreach-owed list, the carried placements |

## In scope — deliverables

1. **K13 UX requirement families (C1; plan §6.2, spec §56.8):** an append-only `spec_src` change adding the K13 synthesis's requirements — the 51 `data/k13_requirements.csv` rows — as final ids. UXR-01…UXR-38 are new requirements; UXR-A01…UXR-A13 are adoption rows that promote the K-series draft families (SIG-UI-D*, SIG-UI-DM*, SIG-SRCH-D*, SIG-JUR-D*, SIG-DSRC-D*, SIG-UI-DV*, SIG-WATCH-D*, SIG-EVUI-D*, SIG-RQ-D*, K14 DR-K14-*, L3's SIG-CONF-D01/D05/D11-as-UX) to final ids with their recorded amendments. **The prefix decision is recorded, not guessed:** the SEED-12a carry reads "append the K13 UX families (or fold them into SIG-UI) and register any new prefix in §0.3" — C1 picks new-family prefixes vs SIG-UI folds per draft, records the mapping in a committed draft→final id map (`docs/build/reports/plan-11c/K13_id_map.csv`), and registers any new prefix in §0.3. UXR-A10's J3/K9 TRANSP drafts **map onto the SIG-TRANSP-nnn ids PLAN-11B already appended** — never re-added. De-duplicated against existing ids; `BUILD.sh` rebuilds the spec; `check_spec_src.py`'s id baselines and an Appendix G row updated the way the SIG-TRANSP append did; one coverage-matrix row per new id, verdict MISSING, routed to its owning 11C row through `coverage-assessment/1` events. No MUST elsewhere is weakened (a weakening is a waiver needing the operator's words, ADR-150).
2. **77 contracts (C1–C11):** each 11C row's file under the **same name** (the manifest row binds it) becomes a full contract in the landed 11B shape: header with `Harness: devin-desktop/swe-2-high/subagent`, kind, the literal `Run:` line with `live_verification` where the row runs (none for plan/gate kinds), `Gate status` with the operator's words verbatim and round times from the ratification log, OM-20 status, `Live window:` and the live-leg re-run prompt where windowed (OM-19), the `Production mutations` list (OM-14), `live:` edges, a token-counted Load list (bytes ÷3 and ÷4, both recorded), deliverables with requirement ids, out-of-scope owners, ACs stated at their layer (BM-STATUS-01), the universal ACs (README "rows 1-N as of"; new verdict words extend `check_coverage_matrix.VERDICTS`; source flips recorded `FLIPPED <date> (<gate|ADR>)`; transitions only with events), and the B5 §6.2 / H2 §7 operating-clause block. Each skeleton's "Carried in at T3" items are honoured. PLAN-11D (418) gets the plan-kind contract form modelled on this file; GATE-G6 (420) gets the gate-contract form with the guard sentence.
3. **Owner re-confirmed (SEED-12a carry):** SIG-OPS-007 → P35.2 (as the spec's §56 `Owner:` line reads at this contract's writing — P35.2 is row 346, in C1's batch); any change is an appended spec_src amendment, not a silent re-route.
4. **Phase-4 review (C12, fresh context):** fragmented decisions, overflow risk (every contract's Load ≤ ~150k tokens by the higher of ÷3 / ÷4, with working-set headroom in the 256k window), orphan seams, coverage (every §56 id with an 11C owner and every new K13-family id maps to exactly one row), ordering (no forward `depends`), over-factoring. The watch/flag set is decided — P36.64 (S6R-14 256k watch list), P36.2 (the out-of-rule rights re-decision fold — sized here), and any row whose own Load count exceeds — pre-split or recorded as fitting. A split lands as suffix-letter rows under the current banner with a `## Plan extensions` line (`mode=extend`; OM-03), never a renumber.
5. **Re-split rule (§8.1, S2 §3.2 as made precise at S4c):** a sub-round whose engineering rows exceed 85 or whose engineering runs exceed 75 becomes two phases with an extra GATE. 11C stood at **76 engineering rows / 66.5 engineering runs at S6c**. If C12's review adds splits that push 11C over, the rule fires and an extra-GATE marker is added by `mode=extend` at a recorded boundary with its Plan-extensions line; otherwise C12 records that the rule did not fire, with the counts.
6. **GATE-G5 packet input:** a draft 11C OM-20 list — row id, the contract's exact mutation, restore point, `expires: GATE-G6`, `voided-by:` — built only from the written `Production mutations` headers, for the operator to approve verbatim at GATE-G5 (nothing pre-authorised on silence; the §8.1 count is 10 11C OM-20 rows; the never-pre-authorised classes — P37.2's tier bump, P36.38's API roll, P36.72b's HG-11 readout, every HG-03 flip, and P36.70 if the Class R standing go has lapsed — are excluded by construction).
7. **Placements carried in (deliverable 8's successor; `PD/stageB/CARRY.md` and PLAN-11B's C13 hand-offs):**
   - **(a) Outreach-owed list for GATE-ANNOUNCE (ADR-171), 11C part.** Every 11C contract whose row writes, widens or activates a connector for a project in spec §6's compact table or an ecosystem project (§22.4–§22.5, §35.1) — the acquisition block (P37.1, P37.2, P36.75, P36.76, P36.77, P36.78) and any row a contract author identifies — lists the Stage-0 set (SIG-CHART-033, SIG-INGEST-029/030a, SIG-CONTRIB-012/012a/013, SIG-GOV-024) as *owed — unmet at launch (ADR-171)*, never as satisfied; no agent contacts anyone (ADR-171 Decision 3). C12 writes the 11C part into the run ledger and the requirement index and carries it to PLAN-11D for GATE-ANNOUNCE's "spec MUSTs unmet at launch" list (plan §13.5; row 510).
   - **(b) PLAN-11B hand-offs.** Whatever PLAN-11B's C13 hands here by appended `## Plan extensions` lines — e.g. the IND-TRIBAL members `AP-T2-201`/`AP-T2-210` if the S8 screened lane's wave lands in 11C, and any `D-R11-OSMUID-1` placement — each names a landing 11C row or is re-handed to PLAN-11D, never dropped.
   - **(c) P36.2's out-of-rule rights re-decision (T3 fold).** The skeleton carries "P36.2 now also carries the out-of-rule rights re-decision" — C2's contract carries it explicitly and C12 sizes it at the Phase-4 review (the SEED-12a carry's own instruction).
   - **(d) GATE-G5's collected decisions are carried as cells, never anticipated.** ING-GO-C is named verbatim in P37.2's gate cell; the Wave-C/vendor HG-03 flip list (OP-26) names 11C sources; the contracts quote the plan cells verbatim and the answers are the operator's at GATE-G5 — no contract asserts a decision that has not been recorded.
8. **Requirement → ticket index for 11C:** extend `docs/tickets/REQUIREMENT_INDEX_R11.md` by re-running its generator (`python3 PD/tools/s13e/req_index.py write`, then `check`) after C11, and append the decisions to the manifest's `## Decomposition decisions` (Round-11 block).

## Out of scope

- Executing any 11C row; dispatching PLAN-11D's own contexts (row 418's dispatch later); 11D/tail contracts beyond PLAN-11D's own file — **PLAN-11D**; changing a ratified row's scope, order or gate (only splits, via `mode=extend`); any production action.
- Re-deciding anything GATE-G5 decides (the 11C OM-20 list is a **draft**; ING-GO-C and the flip lists are the operator's).

## Production mutations (OM-14; BM-PROD-01)

- **None.**

## Acceptance criteria

Each criterion names the BM-STATUS-01 layer it must reach (engineered · fixture-verified · staging-verified · live-executed · public · human-completed); a lower layer reached is reported as that layer, never higher.

- [ ] Rows 344–420: every file is a full contract (no skeleton header remains; `bash scripts/docs/check-build-memory.sh .` raises no skeleton or manifest violation), titles and `Harness:` lines as the seed's T3 check requires. *(deterministic · layer: engineered)*
- [ ] Every 11C contract records its Load count (÷3 and ÷4) and none exceeds ~150k by the higher figure, or it was split. *(deterministic · layer: engineered)*
- [ ] The K13 UX families are in the built spec, their prefixes registered in §0.3, mapped draft→final in `K13_id_map.csv`, each new id has a MISSING matrix row routed to an unlanded 11C row, and no id duplicates the landed SIG-TRANSP set; `check_spec_src.py` and `check_coverage_matrix.py` are green. *(deterministic · layer: engineered)*
- [ ] The C12 review is recorded (findings, splits, the watch/flag set, the 11C re-split decision with counts) in the run ledger and the manifest's Decomposition decisions. *(agentic · layer: engineered)*
- [ ] Deliverable 7: the outreach-owed list (11C part) exists and no 11C contract stamps the ADR-171 Stage-0 set as satisfied; each PLAN-11B hand-off names a landing row; `REQUIREMENT_INDEX_R11.md` regenerated and `req_index.py check` green. *(deterministic · layer: engineered)*
- [ ] The draft 11C OM-20 list exists for the GATE-G5 packet, each entry traceable to a contract header. *(deterministic · layer: engineered)*
- [ ] Verification green: `make check` and `make docs-check`; anything not automatically verifiable is a `DEFERRALS.md` row with `owner:`/`trigger:`; an ADR for every deviation and owned decision. *(deterministic · layer: engineered)*
- [ ] PR head checks read head-bound after push (`docs/build/tools/ci_boundary.py`; python, docs, composed, security, web) and recorded as the `ci:` line; red, pending or missing → `blockedOn`, no close on red (OM-05, SIG-MEM-007). *(deterministic · layer: engineered)*
- [ ] Closeout is one commit after the PR exists (OM-02): run ledger `docs/build/runs/PLAN-11C.md` (header `Harness: devin-desktop/swe-2-high/subagent`, `Started:`/`Closed:` from `date -u`, one section per context C1–C12, gap table), `docs/build/pr/PLAN-11C.md`, a BUILD_INDEX row under `## Round 11` (12 columns incl. `harness`), the LEDGER advanced, and the `rows 1-N as of` line of `docs/build/README.md` updated. *(deterministic · layer: engineered)*
- [ ] Record rules: a new coverage verdict word extends `check_coverage_matrix.VERDICTS` in the same change; a source flip, if any record of one is touched, reads `FLIPPED <date> (<gate|ADR>)`; every DEFERRALS lead-token change carries a matching `obligation-event/1` transition with its evidence (D-P32.18-1…D-P32.21-1 close only that way); protected records only gain lines (`python3 docs/build/tools/memory_guard.py all --staged` green before the closeout commit). *(deterministic · layer: engineered)*

## Requirement IDs to satisfy and stamp in the PR

- **Written here (final ids assigned in C1):** the K13 UX requirement families (plan §6.2; spec §56.8)
- **Owner confirmed:** SIG-OPS-007 (P35.2)
- **Cited:** SIG-ENG-003 (spec changes through `spec_src` + `BUILD.sh`), SIG-ENG-041 (MISSING rows and routing; owner SEED-15)

## Cross-cutting invariants

- **Defining standard (§3.1):** no unexplained dots or edges, no silent overwrites, no synthetic certainty; every claim has evidence, every inference is labelled, every contradiction stays visible.
- **Part VIII binds (§0.7):** no plate, trip or per-person data; officer-naming default-deny; sensitivity tiers, coordinate rules, licence gate and ODbL separation hold.
- **Append-only (P1–P3, AGENTS.md gotcha 5):** no `UPDATE`/`DELETE` on the claim spine; corrections are new rows; protected build records only gain lines at their ends (OM-13); landed ADR bodies are never edited.
- **Fail-closed sources (gotcha 4):** this row flips no `ingestion_permitted` and ticks no `HG-nn` gate (HG-03 flips are the operator's, OP-26).
- **Round-11 truth rules:** no agent label counts as a human label and no agent signs ("no human check performed"); nobody outside the project is contacted (U-011); the operator's personal e-mail address is never added to a file; dates come from `date -u` or git/GitHub time (OM-04); `db/sqitch.plan` lines 44–52 are never edited or re-stamped (C-10, ADR-146).
- **Additive / back-compat:** prior wire names, ids and schema contracts keep working; new fields are optional with today's behaviour as the default.

## Operating clauses

Cited from `docs/tickets/00_MANIFEST.md` § Operating rules (the LEDGER's `OPERATING MODE — Round 11` holds the full OM-01…OM-20 text); the run ledger's gap table has one row per clause. B5 §6.2's block with H2 §7's lines, filled for this row:

```
Round-11 operating clauses (OM-01…OM-20)
- [ ] Harness/model recorded in the run-ledger header; commits trailered.            (OM-01)
- [ ] Every date written comes from `date -u` or git/GitHub time (source named).   (OM-04)
- [ ] After push: PR checks read and recorded (job, conclusion, run id); red → blockedOn.   (OM-05)
- [ ] Each AC states its layer: engineered | fixture | staging | live | public | human.     (OM-06)
- [ ] Production mutations permitted by this ticket: none. (OM-14)
- [ ] Protected records touched only by appending; corrections name the sha/line corrected.   (OM-13)
- [ ] No test asserts the current state of a living record.                                (OM-15)
- [ ] Gate items: operator words verbatim; agent-drafted text labelled and confirmed; no proxy signature. (OM-07/08/09)
- [ ] Size budget: 7.0 runs as twelve ≤ 1-run contexts of ≤ 8 rows; a context near ~200k shrinks its batch. (OM-16)
- [ ] Closeout is one commit after the PR exists.                                         (OM-02)
- [ ] Window / live legs: none (scheduled `while P35.63 waits for its HG-11 go`, finished before GATE-G5). (OM-19)
- [ ] Pre-authorisation: not an OM-20 row; drafts the 11C list for GATE-G5, approves nothing. (OM-20)
- [ ] Rows enter only from the ratified plan; splits by mode=extend with a Plan-extensions line. (OM-03)
- [ ] Branch r11/PLAN-11C-contracts-for-11c-and-k13-families from chainTip; PR base = previous branch; body = docs/build/pr/PLAN-11C.md. (PR-1)
- [ ] Pre-closeout head green on all 5 required checks (sha-bound), recorded as the `ci:` line; closeout pushed after. (CI-2/CI-6)
- [ ] Local: `make ci-local` (or the H2 §3.4 list) with Docker up, or `locally-green (… not run: reason)`. (P11)
- [ ] CI config changed: no. (CI-8)
```

## Notes

- Carried in at T3: SEED-12a — append the K13 UX families (or fold them into SIG-UI) and register any new prefix in §0.3; re-confirm SIG-OPS-007 → P35.2; P36.2 carries the out-of-rule rights re-decision (sized at the Phase-4 review).
- The skeleton's provisional context table named stale row ids (an earlier row numbering); this contract's table follows the ratified `data/round11_plan.csv` — rows 344–420 as plan §8.1's table counts them (74 tickets, PLAN-11D, acceptance P36.73, GATE-G6; 77 rows).
- **Plan-internal drift recorded, not resolved:** the plan row's `est_runs` reads 7.0 while §8.1's table shows 6.0 in the PLAN column; C12's review records the figure it used.
- **Output budget (inference; same rule as SEED-13e's 11B review):** at ≈ 14 KB per written contract an 8-row batch adds ≈ 37k tokens (÷3) of output to ≈ 107k loaded (upper bound); with the run's skill text, harness allowance, self-review re-read and tool output the modelled peak stays ≈ 215k of the 256k window — over-budget contexts stop at a row boundary, record the seam, and the next context resumes there (the order never changes).
- Each context records its own `Started:`/`Closed:` and token count in the run ledger; the orchestrator's isolation probe repeats at the sub-round GATE, not per context.
- AC rubric: ACCEPTED / UNMET / OUT-OF-SCOPE / DEFERRED.
- Do not renumber a manifest row; do not edit `docs/2_canonical_design_spec.md` directly; append-only history; the commit message carries the `Harness:` trailer (OM-01).
