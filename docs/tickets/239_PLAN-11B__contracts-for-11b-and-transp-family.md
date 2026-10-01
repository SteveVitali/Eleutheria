<!-- Full contract written 2026-10-01 by Stage-B unit SEED-13c (Round-11 T3, plan Appendix A T3 second bullet) from docs/build/planning/2026-09-30-next-phase/data/round11_plan.csv row 239 (plan §8.5, §6.2); it replaces the T3 first-context file under the same name. Planning is not execution evidence. -->
# PLAN-11B — decompose-spec mode=extend — full 11B contracts from the ratified PLAN rows + SIG-TRANSP family append

- **Sequence:** 239 of 510 · **Phase:** Round 11 / P34 (sub-round 11A) · **Kind:** plan
- **Row kind (manifest):** plan — a contract-authoring row run like a ticket; each of its contexts runs `decompose-spec mode=extend`
- **Tag:** round11-11A
- **Harness:** devin-desktop/swe-2-high/subagent
- **base_branch:** current checkout — the branch the previous row left checked out; this row works on `r11/PLAN-11B-contracts-for-11b-and-transp-family`, PR base = that branch (H2 PR-1)
- **Depends on:** P34.33
- **Run:** `implement-spec spec=docs/tickets/239_PLAN-11B__contracts-for-11b-and-transp-family.md live_verification=false` — dispatched as the eight ≤ 1-run contexts below (C1…C8), one fresh sub-agent each, in order; each context invokes `decompose-spec mode=extend` (Phase 3 contracts; C8 Phase 4 review) on its scope only
- **Gate status:** none — plan only; rows enter only from the ratified plan (OM-03): `data/round11_plan.csv` as ratified at GATE-P (S5) and amended at S6/S6b/S6c
- **OM-20 status:** not an OM-20 row
- **Live stage:** none
- **Live window:** scheduling preference, not a production window — during the 2026-10-06 00:00Z → 10-13 12:00Z AR-3 freeze, when hosted legs are idle (plan §8.4); it must finish before GATE-G4 so the G4 packet cites written 11B contracts
- **Production mutations:** none
- **Size budget:** 7.0 runs as eight contexts (seams below); no context over 1.0 run or ~150k tokens loaded; contract files and the spec append are the output (generated `docs/2_canonical_design_spec.md` excluded)
- **Load (token-counted, per context):** 311,556 B → ≈ 103,852 tokens (bytes÷3) · ≈ 77,889 (bytes÷4) for the common set plus one batch's allowance; ≤ ~150k → no split (A-15, §8.5)

## Goal

Every 11B chain row (rows 261–343, P35/P36 "Correct and traceable") gets an execute-grade contract before GATE-G4 — written from the ratified plan rows, sized for Devin Desktop's 256k window and reviewed in a fresh context — and the SIG-TRANSP requirement family the 11B transparency rows cite is appended to the spec, so GATE-G4's OM-20 list for 11B names written contracts.

## Load (read these — do not re-read others)

Paths under `PD/` are under `docs/build/planning/2026-09-30-next-phase/`. Byte counts are UTF-8 bytes of exactly the named part, measured 2026-10-01 on the `r11/seed` working tree. Every context loads the common set; each adds only its batch.

- `AGENTS.md` — root agent guide (precedence, gotchas, Do/Don't) — 15,220 B
- `docs/build/LEDGER.md` — orient region only (line 1 → before `## OPEN FINDINGS`; counted at its 12 KiB budget, SIG-MEM-010) + the last three PHASE LOG entries if the head points there — 12,288 B
- `docs/build/reports/current/CURRENT.md` § Obligations — the index of owed rows (orientation only — it never replaces DEFERRALS) — 8,191 B
- `docs/tickets/DEFERRALS.md` — DEFERRALS-first (AGENTS.md gotcha 8): read in full the owed rows the batch's rows own or close — not the whole file. Counted as a 16 KiB allowance (re-measure at dispatch) — 16,384 B
- `docs/tickets/00_MANIFEST.md` — § Operating rules (binding) + this row's chain line + the 11B banners and rows 261–343 — 27,509 B
- `docs/2_canonical_design_spec.md` § Part 0 · 3. First principles · Appendix E — always in scope — 24,696 B
- `~/.claude/skills/decompose-spec/SKILL.md` — `mode=extend`, Phase 3 contract rules, Phase 4 review — 24,720 B
- `docs/tickets/_TEMPLATE.md` + `~/.claude/skills/build-memory/templates/ticket.md` — the contract templates — 2,977 B + 2,773 B
- `docs/tickets/201_P34.1__toolchain-pin-and-ci-hygiene.md` — the established Round-11 contract shape (header, Load token count, AC layers, operating-clause block) — 20,191 B
- `PD/NEXT_PHASE_PLAN.md` § 3.3 operating clauses + § 8.1 Shape and counts · § 8.3 Gates · § 8.4 Live stages · § 8.5 Sizing — 21,333 B
- `docs/2_canonical_design_spec.md` § 0.3 Requirement identifiers + § 56.8 Families appended by later rows — 4,372 B
- **C1 only:** `PD/design/J3-transparency-design.md` § 11 Draft requirements, `PD/design/K9-sources-table.md` § 10, `PD/design/K10-source-pages.md` § 18 — the SIG-TRANSP drafts D01–D43 — 8,311 B + 3,628 B + 3,078 B
- **Per batch (allowance, re-measured by each context):** the batch's ~12 current contract files (≈ 2.2 KB each), their `data/round11_plan.csv` and `ticket_catalog.csv` rows and `stageB/T3_contract_map.csv` rows, and only the design-note sections each row cites — counted as 96 KiB — 98,304 B
- `docs/tickets/239_PLAN-11B__contracts-for-11b-and-transp-family.md` — this contract — 17,581 B

**Token count (counter `utf8-bytes÷3 | ÷4`, the named proxy of S6R-27 — `swe-2-high`'s tokenizer is unknown):** 311,556 B → ≈ 103,852 (÷3) · ≈ 77,889 (÷4) per context. A context whose batch needs more than its allowance shrinks its batch (the seam moves; the order does not) and records it.

## Contexts and seams (≤ 1 run each; plan row: "seam = contiguous batches of ~12 contracts")

| ctx | scope | notes |
|---|---|---|
| C1 | **SIG-TRANSP family** + rows 261–271 (to the Wave A activation, P35.11) | the family must exist before any 11B contract cites it |
| C2 | rows 272–283 | P35.14a carries SIG-ONTO-060 (enum read + proposal) and P35.14b is a never-pre-authorised hosted change |
| C3 | rows 284–290 (to the Wave B activation, P36.12) | P36.12 is flagged oversized (ten family legs) |
| C4 | rows 291–302 | P35.1b flagged oversized; SIG-SEC-008 owner P35.1a/b; SIG-SEC-009 owner P35.4 |
| C5 | rows 303–314 | P35.34 keeps SIG-INGEST-004's MUST (binding versions) — carried |
| C6 | rows 315–326 | |
| C7 | rows 327–343 (to GATE-G5) | P35.61 and P35.63 flagged oversized; SIG-CONF-010 owner P35.60; the PLAN-11C row (340), the 11B acceptance row P35.64 and the GATE-G5 marker |
| C8 | **fresh-context Phase-4 sizing review** of all 11B contracts | splits, GATE-G4b decision, requirement index, the 11B OM-20 list draft |

## In scope — deliverables

1. **SIG-TRANSP family (C1; plan §6.2, spec §56.8):** an append-only `spec_src` change adding the transparency requirements from J3 §11 (D01–D25) and K9/K10 (D26–D43) as final `SIG-TRANSP-nnn` ids, de-duplicated against existing ids and against the K13 set (D26–D43 are written once, here; PLAN-11C cites them); the `TRANSP` prefix registered in §0.3; `BUILD.sh` rebuilds the spec; a committed draft→final id map (`docs/build/reports/plan-11b/TRANSP_id_map.csv`); `check_spec_src.py`'s id baselines and an Appendix G.7 row updated the way SEED-12 did for §56; one coverage-matrix row per new id, verdict MISSING, routed to its owning 11B row through `coverage-assessment/1` events. No MUST elsewhere is weakened (a weakening is a waiver needing the operator's words, ADR-150). ADR-162 (transparency and distribution) is cited, not edited.
2. **83 contracts (C1–C7):** each 11B row's file under the **same name** (the manifest row binds it) becomes a full contract in the shape of `201_P34.1…md`: header with `Harness: devin-desktop/swe-2-high/subagent`, kind, the literal `Run:` line with `live_verification`, `Gate status` with the operator's words verbatim and round times from the ratification log, OM-20 status, `Live window:` and the live-leg re-run prompt where windowed (OM-19), the `Production mutations` list (OM-14), `live:` edges, a token-counted Load list (bytes ÷3 and ÷4, both recorded), deliverables with requirement ids, out-of-scope owners, ACs stated at their layer (BM-STATUS-01), the universal ACs (README "rows 1-N as of"; new verdict words extend `check_coverage_matrix.VERDICTS`; source flips recorded `FLIPPED <date> (<gate|ADR>)`; transitions only with events), and the B5 §6.2 / H2 §7 operating-clause block. Each skeleton's "Carried in at T3" items are honoured. Gate rows (GATE-G5) get the gate-contract form with the guard sentence; PLAN-11C's contract follows this one's shape.
3. **Owners re-confirmed (SEED-12a carry):** SIG-SEC-008 → P35.1a/b, SIG-SEC-009 → P35.4, SIG-CONF-010 → P35.60 (as the spec's §56 `Owner:` lines read at this contract's writing); any change is an appended spec_src amendment, not a silent re-route.
4. **Phase-4 review (C8, fresh context):** fragmented decisions, overflow risk (every contract's Load ≤ ~150k tokens by the higher of ÷3 / ÷4, with working-set headroom in the 256k window), orphan seams, coverage (every §56 id with an 11B owner and every SIG-TRANSP id maps to exactly one row), ordering (no forward `depends`), over-factoring. The four flagged rows (P35.1b, P35.61, P35.63, P36.12) are decided — pre-split or recorded as fitting. A split lands as suffix-letter rows under the current banner with a `## Plan extensions` line (`mode=extend`; OM-03), never a renumber.
5. **Re-split rule (S6R-15; plan §8.1):** if after splits 11B exceeds 85 engineering rows or 75 runs, add the GATE-G4b marker at the Wave-B activation boundary (after row 290, where the manifest already has a banner boundary) by `mode=extend`, with its Plan-extensions line; otherwise record that the rule did not fire, with the counts.
6. **GATE-G4 packet input:** a draft 11B OM-20 list — row id, the contract's exact mutation, restore point, `expires: GATE-G5`, `voided-by:` — built only from the written `Production mutations` headers, for the operator to approve verbatim at GATE-G4 (nothing pre-authorised on silence; the never-pre-authorised classes of §3.3 excluded).
7. **Requirement → ticket index for 11B** and the decisions appended to the manifest's `## Decomposition decisions` (Round-11 block).

## Out of scope

- 11C/11D/tail contracts — **PLAN-11C** (row 340), **PLAN-11D**; the K13 UX families — **PLAN-11C**.
- Executing any 11B row; changing a ratified row's scope, order or gate (only splits, via `mode=extend`); any production action.

## Production mutations (OM-14; BM-PROD-01)

- **None.**

## Acceptance criteria

Each criterion names the BM-STATUS-01 layer it must reach (engineered · fixture-verified · staging-verified · live-executed · public · human-completed); a lower layer reached is reported as that layer, never higher.

- [ ] Rows 261–343: every file is a full contract (no skeleton header remains; `bash scripts/docs/check-build-memory.sh .` raises no skeleton or manifest violation), titles and `Harness:` lines as the seed's T3 check requires. *(deterministic · layer: engineered)*
- [ ] Every 11B contract records its Load count (÷3 and ÷4) and none exceeds ~150k by the higher figure, or it was split. *(deterministic · layer: engineered)*
- [ ] SIG-TRANSP ids are in the built spec, registered in §0.3, mapped draft→final, and each has a MISSING matrix row routed to an unlanded 11B row; `check_spec_src.py` and `check_coverage_matrix.py` are green. *(deterministic · layer: engineered)*
- [ ] The C8 review is recorded (findings, splits, the four flagged rows, the GATE-G4b decision with counts) in the run ledger and the manifest's Decomposition decisions. *(agentic · layer: engineered)*
- [ ] The draft 11B OM-20 list exists for the GATE-G4 packet, each entry traceable to a contract header. *(deterministic · layer: engineered)*
- [ ] Verification green: `make check` and `make docs-check`; anything not automatically verifiable is a `DEFERRALS.md` row with `owner:`/`trigger:`; an ADR for every deviation and owned decision. *(deterministic · layer: engineered)*
- [ ] PR head checks read head-bound after push (`docs/build/tools/ci_boundary.py`; python, docs, composed, security, web) and recorded as the `ci:` line; red, pending or missing → `blockedOn`, no close on red (OM-05, SIG-MEM-007). *(deterministic · layer: engineered)*
- [ ] Closeout is one commit after the PR exists (OM-02): run ledger `docs/build/runs/PLAN-11B.md` (header `Harness: devin-desktop/swe-2-high/subagent`, `Started:`/`Closed:` from `date -u`, one section per context C1–C8, gap table), `docs/build/pr/PLAN-11B.md`, a BUILD_INDEX row under `## Round 11` (12 columns incl. `harness`), the LEDGER advanced, and the `rows 1-N as of` line of `docs/build/README.md` updated. *(deterministic · layer: engineered)*
- [ ] Record rules: a new coverage verdict word extends `check_coverage_matrix.VERDICTS` in the same change; a source flip, if any record of one is touched, reads `FLIPPED <date> (<gate|ADR>)`; every DEFERRALS lead-token change carries a matching `obligation-event/1` transition with its evidence (D-P32.18-1…D-P32.21-1 close only that way); protected records only gain lines (`python3 docs/build/tools/memory_guard.py all --staged` green before the closeout commit). *(deterministic · layer: engineered)*

## Requirement IDs to satisfy and stamp in the PR

- **Written here (final ids assigned in C1):** the SIG-TRANSP family (plan §6.2; spec §56.8)
- **Owners confirmed:** SIG-SEC-008 (P35.1a/b), SIG-SEC-009 (P35.4), SIG-CONF-010 (P35.60)
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
- [ ] Size budget: 7.0 runs as eight ≤ 1-run contexts; a context over budget shrinks its batch. (OM-16)
- [ ] Closeout is one commit after the PR exists.                                         (OM-02)
- [ ] Window / live legs: none (scheduled into the 10-06 → 10-13 AR-3 freeze by preference). (OM-19)
- [ ] Pre-authorisation: not an OM-20 row; drafts the 11B list for GATE-G4, approves nothing. (OM-20)
- [ ] Rows enter only from the ratified plan; splits by mode=extend with a Plan-extensions line. (OM-03)
- [ ] Branch r11/PLAN-11B-contracts-for-11b-and-transp-family from chainTip; PR base = previous branch; body = docs/build/pr/PLAN-11B.md. (PR-1)
- [ ] Pre-closeout head green on all 5 required checks (sha-bound), recorded as the `ci:` line; closeout pushed after. (CI-2/CI-6)
- [ ] Local: `make ci-local` (or the H2 §3.4 list) with Docker up, or `locally-green (… not run: reason)`. (P11)
- [ ] CI config changed: no. (CI-8)
```

## Notes

- Carried in at T3: SEED-12a — append the SIG-TRANSP family and register its prefix in §0.3; re-confirm the three owners; plan §8.1's re-split rule (four 11B rows flagged; 11B stood at 82 rows / 73.5 runs at S6c, 1.5 runs of headroom).
- **Output budget (inference):** at ≈ 14 KB per written contract a 12-row batch adds ≈ 56k tokens (÷3) of output to the ≈ 103,852 loaded — inside the 256k window but with less headroom than a ticket; a context nearing the ceiling stops at a row boundary, records the seam, and the next context resumes there (the order never changes).
- Each context records its own `Started:`/`Closed:` and token count in the run ledger; the orchestrator's isolation probe repeats at the sub-round GATE, not per context.
