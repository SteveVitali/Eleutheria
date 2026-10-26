<!-- Full contract written 2026-10-25 by PLAN-11C context C10 (row 340, `decompose-spec mode=extend`, Round-11 plan row 418, `NEW (S4c)` — the nested plan row); it replaces the T3 skeleton under the same name. Planning is not execution evidence. -->
# PLAN-11D — decompose-spec mode=extend — full 11D + tail contracts

- **Sequence:** 418 of 510 · **Phase:** Round 11 / P36 (sub-round 11C) · **Kind:** plan
- **Row kind (manifest):** plan — a contract-authoring row run like a ticket; each of its contexts runs `decompose-spec mode=extend`
- **Tag:** round11-11D
- **Harness:** devin-desktop/swe-2-high/subagent
- **base_branch:** current checkout — the branch the previous row left checked out; this row works on `r11/PLAN-11D-contracts-for-11d-and-tail`, PR base = that branch (H2 PR-1)
- **Depends on:** PLAN-11C — the plan cell, verbatim; it dispatches later, after PLAN-11C lands and while P36.72b waits for its HG-11 go (the Notes record why these contracts must exist before the next gate)
- **Run:** `implement-spec spec=docs/tickets/418_PLAN-11D__contracts-for-11d-and-tail.md live_verification=false` — dispatched as the contexts below (one fresh sub-agent each, in order; each context invokes `decompose-spec mode=extend` on its scope only)
- **Gate status:** `none (plan only, OM-03)` — the plan cell, verbatim; rows enter only from the ratified plan: `data/round11_plan.csv` as ratified at GATE-P (S5) and amended at S6/S6b/S6c
- **OM-20 status:** not an OM-20 row — it drafts the 11D OM-20 list for GATE-G6, approves nothing
- **Live stage:** none — the plan cell, verbatim
- **Live window:** `while P36.72b waits for its HG-11 go` — the plan cell, verbatim: a scheduling preference, not a production window; written **before GATE-G6** (S4c) so G6's packet can cite written 11D contracts
- **Production mutations:** none
- **Size budget:** 6.0 runs (the plan row's `est_runs`, verbatim) as ~6 contract contexts plus the Phase-4 sizing review (S4c FEA-01); ≤ 8 rows per context (the SEED-13e sizing rule — 90 rows means ~12 contexts; the "~6" fan-out is the pre-sizing figure, recorded, not silently exceeded); no context over 1.0 run or ~150k tokens loaded
- **Load (token-counted, per context):** the common set (~320 kB → ≈ 106,700 tokens ÷3 · ≈ 80,000 ÷4, carried from PLAN-11C's measured figure — the same files, the same shape) plus one 8-row batch's 64 KiB allowance; ≤ ~150k → no context split (A-15, §8.5); the Phase-4 review re-measures every contract

## Goal

Every 11D and tail chain row (rows **421–510** — P37 hardening and lifecycle, the keyed-API unblocks, the map/entity/graph tails, the coverage closeout, the UX capstone journeys A/O/J + U-003 per-ask checks, and the tail's capstone-lite, reconcile, docs, announce-readiness and GATE-ANNOUNCE rows) gets an execute-grade contract **before GATE-G6** — written from the ratified plan rows, sized for Devin Desktop's 256k window and reviewed in a fresh context — so GATE-G6's OM-20 list for 11D names written contracts.

## Load (read these — do not re-read others)

Paths under `PD/` are under `docs/build/planning/2026-09-30-next-phase/`. Byte counts are UTF-8 bytes of exactly the named part; the common set is PLAN-11C's, re-verified at dispatch.

- `AGENTS.md` — root agent guide — ~15 kB
- `docs/build/LEDGER.md` — orient region only + the last PHASE LOG entries — ~12 KiB
- `docs/build/reports/current/CURRENT.md` § Obligations — orientation only — ~8 KiB
- `docs/tickets/DEFERRALS.md` — DEFERRALS-first: the owed rows each batch's rows own or close — 16 KiB allowance, re-measured
- `docs/tickets/00_MANIFEST.md` — § Operating rules + this row's chain line + the 11D/tail banners and rows 421–510 — ~31 KiB
- `docs/2_canonical_design_spec.md` § Part 0 · 3. First principles · Appendix E + §56 (all sub-sections now in force, incl. §56.11) — ~30 KiB
- `~/.claude/skills/decompose-spec/SKILL.md` — `mode=extend`, Phase 3/4 rules — ~25 KiB
- `docs/tickets/340_PLAN-11C__contracts-for-11c-and-k13-families.md` — the plan-contract shape this file follows — ~24 kB
- a landed 11C contract + `docs/tickets/343_GATE-G5__…` + `docs/tickets/420_GATE-G6__…` — the ticket and gate-marker shapes — ~55 kB
- `PD/NEXT_PHASE_PLAN.md` § 3.3 + § 8.1/8.3/8.4/8.5 — ~21 kB
- `docs/adr/ADR-171-…` § Decision — the outreach-owed rule (deliverable 8a's successor) — ~10 kB
- `docs/tickets/REQUIREMENT_INDEX_R11.md` — the index this row extends — ~16 KiB
- **Per batch (allowance):** the batch's ≤ 8 skeletons + `round11_plan.csv`/`ticket_catalog.csv`/`T3_contract_map.csv` rows + only the design-note sections each row cites — 8 KiB per row, 64 KiB per batch
- this contract — ~20 kB

**Token count** (`utf8-bytes÷3 | ÷4`, the S6R-27 proxy): ≈ 130k (÷3 upper bound, batch inclusive) — under ~150k; a context whose batch exceeds its allowance shrinks the batch (the seam moves; the order does not) and records it.

## Contexts and seams (≤ 1 run each; plan row: "fan-out ~6 contexts + Phase-4 sizing review" — S4c FEA-01; 90 rows at ≤ 8/context lands ~12 contexts + the review — the Phase-4 review records the actual split)

| ctx | scope | notes |
|---|---|---|
| D1 | rows 421–428 (8) | hardening block: P37.3 evidence-store hardening + off-instance copies; P37.4a/b security baseline (split pair); P37.5a/b ingestion hardening (split pair); P37.6 rights-record hygiene; P37.7 editorial decision log; P37.8 legal-demand posture (SIG-SEC-003) |
| D2 | rows 429–436 (8) | P37.71 true-deletion path (WV-06 — operator-only purge, the most sensitive row of the sub-round; its contract carries the constitutional posture verbatim); P37.9 lifecycle→dossier timeline; P37.10 asset-promotion gate; P37.11 SAM.gov resume (D-FEDERAL.1-1); P37.12 511 wiring (D-SOURCES.7-2); P37.70 keyed AU APIs (D-SOURCES.8-2 a); P37.13 registry completeness; P37.14 statute-seeded leads |
| D3 | rows 437–444 (8) | P37.15 parser canary; P37.16a/b dossier live captures (the D-P32.18/19/20/21-1 rows — deferral-closing contracts); P37.17 tiles v2; P37.18 map filters; P37.72 'my location' (D-K1-7, SIG-GOV-017 analysis-first); P37.19 map place search; P37.20 release-pinned bbox API; P37.21 access closures |
| D4 | rows 445–452 (8) | entity/graph tail: P37.22 contract B, P37.23 pages B, P37.24/25 overview builders + /graphs/**, and the next three rows |
| D5 | rows 453–460 (8) | continue the 11D tail (Wave-D scope rows per GATE-G6's I8-Q5 answer — in scope per S6) |
| D6 | rows 461–468 (8) | … |
| D7 | rows 469–476 (8) | … |
| D8 | rows 477–484 (8) | … |
| D9 | rows 485–492 (8) | … |
| D10 | rows 493–500 (8) | coverage closeout + the P37.68a–d UX capstone set (per-journey splits already in the plan — contracts, never re-splits) |
| D11 | rows 501–510 (10; the tail) | capstone-lite P38.1a/b + P38.2 closure + GATE-ACCEPT-R11 marker + P38.3a–c reconcile + P38.4 docs + P38.5 announce-readiness + GATE-ANNOUNCE marker (U-009 — never auto-announced; collects the outreach-owed list's final form) |
| D12 | **fresh-context Phase-4 sizing review** | splits, coverage (every 11D-owned §56 id → exactly one row), ordering, over-factoring, the 11D re-split decision with counts, the draft 11D OM-20 list for GATE-G6, the 11D outreach-owed list, the final placements audit |

## In scope — deliverables

1. **90 contracts (D1–D11):** every 11D + tail row's file under the **same name** (the manifest row binds it) becomes a full contract in this family's landed shape — header with `Harness:`, kind, the literal `Run:` line, `Gate status` verbatim with round times, OM-20 status, `Live window:` + the leg re-run prompt (OM-19), `Production mutations` (OM-14), token-counted Load lists, deliverables with requirement ids, layered ACs (BM-STATUS-01), the universal ACs and the OM-01…OM-20 block. The two gate rows (GATE-ACCEPT-R11, GATE-ANNOUNCE) get gate-marker contracts with their guard sentences; the capstone/reconcile rows get capstone contracts.
2. **Phase-4 review (D12, fresh context):** fragmented decisions, overflow risk (every Load ≤ ~150k tokens by the higher of ÷3/÷4), orphan seams, coverage, ordering (no forward `depends`), over-factoring; the watch/flag set; splits land as suffix-letter rows with a `## Plan extensions` line (mode=extend; OM-03), never a renumber.
3. **Re-split rule (§8.1, S2 §3.2):** a sub-round whose engineering rows exceed 85 or whose engineering runs exceed 75 becomes two phases with an extra GATE; D12 records whether the rule fires for 11D, with counts.
4. **GATE-G6 packet input:** the draft 11D OM-20 list — row id, the contract's exact mutation, restore point, `expires:` the next GATE, `voided-by:` — built only from written `Production mutations` headers, for the operator to approve verbatim at GATE-G6.
5. **Placements carried:** (a) the outreach-owed list extended to every 11D acquisition/connector row (ADR-171; the Stage-0 set stays owed — never stamped satisfied); (b) any PLAN-11C hand-offs by appended `## Plan extensions` lines; (c) GATE-G6's collected decisions carried as cells (ING-GO-D, the Wave-D flip list, the 11D OM-20 list, the standing-go renewal), never anticipated; (d) the tail's own owed-work register (the U-003.* closures' final landing rows, the "spec MUSTs unmet at launch" list GATE-ANNOUNCE reads, plan §13.5).
6. **Requirement index:** re-run `req_index.py write` + `check` after the last contract lands; append decisions to the manifest's `## Decomposition decisions`.

## Out of scope

- Executing any 11D/tail row; changing a ratified row's scope, order or gate (only splits, via `mode=extend`); any production action.
- Re-deciding anything GATE-G6 decides (the 11D OM-20 list is a **draft**; ING-GO-D and the Wave-D flip list are the operator's).
- Contacting anyone outside the project (U-011; ADR-171) — GATE-ANNOUNCE's contract *describes* the announce decision; it never performs it.

## Production mutations (OM-14; BM-PROD-01)

- **None.**

## Acceptance criteria

Each criterion names the BM-STATUS-01 layer it must reach (engineered · fixture-verified · staging-verified · live-executed · public · human-completed); a lower layer reached is reported as that layer, never higher.

- [ ] Rows 421–510: every file is a full contract (no skeleton header remains; `bash scripts/docs/check-build-memory.sh .` raises no skeleton or manifest violation). *(deterministic · layer: engineered)*
- [ ] Every contract records its Load count (÷3 and ÷4); none exceeds ~150k by the higher figure, or it was split with the seam recorded. *(deterministic · layer: engineered)*
- [ ] The D12 review is recorded (findings, splits, the re-split decision with counts) in the run ledger and the manifest's Decomposition decisions. *(agentic · layer: engineered)*
- [ ] The draft 11D OM-20 list exists for the GATE-G6 packet, each entry traceable to a contract header; the 11D outreach-owed list names every acquisition/connector row. *(deterministic · layer: engineered)*
- [ ] `REQUIREMENT_INDEX_R11.md` regenerated; `req_index.py check` green. *(deterministic · layer: engineered)*
- [ ] Verification green: `make check` and `make docs-check`; anything not automatically verifiable is a `DEFERRALS.md` row with `owner:`/`trigger:`; an ADR for every deviation and owned decision. *(deterministic · layer: engineered)*
- [ ] PR head checks read head-bound after push and recorded as the `ci:` line; red, pending or missing → `blockedOn`, no close on red (OM-05, SIG-MEM-007). *(deterministic · layer: engineered)*
- [ ] Closeout is one commit after the PR exists (OM-02): run ledger `docs/build/runs/PLAN-11D.md`, `docs/build/pr/PLAN-11D.md`, a BUILD_INDEX row under `## Round 11`, the LEDGER advanced, README's `rows 1-N as of` line updated. *(deterministic · layer: engineered)*

## Requirement IDs to satisfy and stamp in the PR

- **Served:** the 11D-owned §56 ids (routed per the coverage matrix and §56.11's Owner lines) — each contract stamps its own.
- **Cited:** SIG-ENG-003 (spec changes through `spec_src` + `BUILD.sh` — none expected here), SIG-ENG-041 (MISSING-row routing), SIG-ENG-042 (no vacuous pass), OM-03/OM-20 (the plan-row rules), U-009/GATE-ANNOUNCE's posture (never auto-announced).

## Cross-cutting invariants

- **Defining standard (§3.1):** no unexplained dots or edges, no silent overwrites, no synthetic certainty; every claim has evidence, every inference is labelled, every contradiction stays visible.
- **Part VIII binds (§0.7):** no plate, trip or per-person data; officer-naming default-deny; the sensitivity tiers, coordinate rules, licence gate and ODbL separation hold — P37.71's true-deletion contract carries the heaviest posture of the sub-round and says so verbatim.
- **Append-only (P1–P3):** no `UPDATE`/`DELETE` on the claim spine; corrections are new rows; protected records only gain lines (OM-13); landed ADR bodies never edited.
- **Fail-closed sources:** this row flips no `ingestion_permitted` and ticks no `HG-nn` gate; the 11D contracts' flip lists name the operator's acts (OP-26), never agent ones.
- **Round-11 truth rules:** no agent label counts as human; nobody outside the project is contacted; dates come from `date -u` or git/GitHub time (OM-04); the operator's personal e-mail is never added to a file.
- **Additive / back-compat:** prior wire names, ids and schema contracts keep working.
- **Planning is not execution evidence** — every contract this row produces carries that banner.

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
- [ ] Size budget: 6.0 runs as ~12 ≤ 1-run contexts of ≤ 8 rows + the review; a context near ~150k shrinks its batch. (OM-16)
- [ ] Closeout is one commit after the PR exists.                                         (OM-02)
- [ ] Window / live legs: none (scheduled `while P36.72b waits for its HG-11 go`, finished before GATE-G6). (OM-19)
- [ ] Pre-authorisation: not an OM-20 row; drafts the 11D list for GATE-G6, approves nothing. (OM-20)
- [ ] Rows enter only from the ratified plan; splits by mode=extend with a Plan-extensions line. (OM-03)
- [ ] Branch r11/PLAN-11D-contracts-for-11d-and-tail from chainTip; PR base = previous branch; body = docs/build/pr/PLAN-11D.md. (PR-1)
- [ ] Pre-closeout head green on all 5 required checks (sha-bound), recorded as the `ci:` line; closeout pushed after. (CI-2/CI-6)
- [ ] Local: `make ci-local` (or the H2 §3.4 list) with Docker up, or `locally-green (… not run: reason)`. (P11)
- [ ] CI config changed: no. (CI-8)
```

## DEFERRALS item

Read `docs/tickets/DEFERRALS.md` first — the 11D rows carry the round's largest deferral-closing surface (the keyed-API unblocks D-SOURCES.7-2/8-2, the federal resume D-FEDERAL.1-1, the dossier live captures D-P32.18/19/20/21-1, plus any rows PLAN-11C hands forward by `## Plan extensions` lines). Each contract names the rows its ticket owns or closes; a deferral not in that file did not happen.

## Notes

- This row runs in **sub-round 11C** as a contract-authoring act — its own dispatch (the D1…D12 contexts) happens later, after PLAN-11C lands, before GATE-G6.
- The "~6 contexts" figure in the plan notes is the pre-sizing fan-out (S4c FEA-01); the SEED-13e ≤8-rows-per-context rule lands ~12 contexts + the review — recorded here, decided finally at D12.
- The tail's GATE-ANNOUNCE row (510) gets a gate-marker contract whose guard sentence states U-009 verbatim — never auto-announced.
- Evidence location: the run ledger `docs/build/runs/PLAN-11D.md` and the generated contract files.
- AC rubric: ACCEPTED / UNMET / OUT-OF-SCOPE / DEFERRED.
- Do not renumber a manifest row; do not edit `docs/2_canonical_design_spec.md` directly; append-only history; the commit message carries the `Harness:` trailer (OM-01).
