<!-- Full contract written 2026-11-05 by PLAN-11D context D11 (row 418, `decompose-spec mode=extend`, Round-11 plan row 510, `NEW (S2)`); it replaces the T3 skeleton under the same name. Planning is not execution evidence. -->
# GATE-ANNOUNCE — operator decides whether SIG is ready to announce (U-009); never auto

- **Sequence:** 510 of 510 · **Phase:** Round 11 / P38 (sub-round 11D-tail) · **Kind:** gate
- **Tag:** round11-11D
- **Harness:** devin-desktop/swe-2-high/subagent
- **base_branch:** none — a gate marker is not an `implement-spec` input and opens no branch; the orchestrator records the answer on the chain tip it holds (GATE DECISIONS row + `docs/build/readouts/GATE-ANNOUNCE.md`)
- **Depends on:** P38.5; REVIEW-R11 — the plan cell, verbatim (REVIEW-R11 is a unit outside the chain, not a manifest row)
- **Run:** none — a milestone gate is not an `implement-spec` input and is never guessed past; the orchestrator presents P38.5's readiness packet and records the operator's answer
- **Gate status:** `U-009 operator decision on the D3 §5 checklist; never auto; agents contact no one; the announcement itself is LATER-22 · S6-F3 answered 'S0/S1 must be dispositioned' (2026-10-01T06:05:22Z): not answered until REVIEW-R11 has finished and each of its S0/S1 findings is fixed (plan-extension row under the chain's rules) or dispositioned by the operator; S2/S3 findings feed the next round's planning · waiver triggers at the announcement (S6R-18): a keep/lift answer for WV-01, WV-03 ('for Round-11 releases'), WV-04, WV-05 ('for Round 11') and WV-08, beside Q-29 · re-anchoring (S6R-19): if REVIEW-R11 S0/S1 fixes need rows, decompose-spec mode=extend appends them after this row and then a new GATE-ANNOUNCE row; this row gets the appended token superseded-by(row <n>) (as rows 184-187); no row is renumbered` — **the plan cell, verbatim.**
- **OM-20 status:** not an OM-20 row (gate marker)
- **Live stage:** none — the plan cell, verbatim
- **Live window:** `none` — the plan cell, verbatim; presented only when no leg is *due* (OM-19) and P38.5 has passed, and **never before REVIEW-R11's S0/S1 findings are fixed or dispositioned (S6-F3)**
- **Live legs:** none (leg runs: 0)
- **Production mutations:** none — the gate decides readiness; the announcement itself is LATER-22, human work outside this chain
- **Size budget:** 0.0 runs (gate marker); the orchestrator's sitting
- **Load (token-counted):** ≈ 78,000 B → ≈ 26,000 tokens (bytes÷3) · ≈ 19,500 (bytes÷4); ≤ ~150k → no split (A-15, §8.5) — P38.5's readiness packet, the D3 §5 checklist, the REVIEW-R11 findings register, the waiver keep/lift lines and the outreach-owed list's final form (re-measured when the packet exists)

> Milestone gate — not an `implement-spec` input; never guessed past. An operator or authorized human record supplies the decision; an agent must not sign or assume silence is approval. **U-009 binds: the project is never auto-announced — no agent, no automation and no chain row announces it; the announcement itself is LATER-22, the operator's act, outside this chain.**

## Goal

The operator decides whether SIG is ready to announce — the last decision of the round and the plan's U-009 posture made literal: **never auto**. The artifact is **P38.5's readiness packet**: the D3 §5 checklist state (D3-Q5 [A-17] = a — the checklist is the gate, no early preview), the 'spec MUSTs unmet at launch' register (TS-05), the REVIEW-R11 findings and their dispositions, the outreach-owed list's final form (ADR-171 — owed, never implied satisfied) and the waiver keep/lift lines. This marker records no readiness that has not happened; an unanswered line takes its non-action default — never consent (OM-18).

## Preconditions (the gate does not sit until all hold)

- **P38.5's packet exists** — agent-drafted and labelled; its sha256 recorded before it is shown (ADR-147).
- **REVIEW-R11 has finished** and each S0/S1 finding is **fixed** (a plan-extension row appended under the chain's rules) or **dispositioned by the operator** (S6-F3, 2026-10-01T06:05:22Z). S2/S3 findings feed the next round's planning — they do not gate.
- **No leg is due** (OM-19) and no OPEN deferral scopes itself to this gate unrecorded.

## The packet (drafted by P38.5; defaults first)

**1. The D3 §5 checklist** — each readiness line shown with its evidence and its default. Checklist lines are own-words lines: each needs its own verbatim answer.

**2. The 'spec MUSTs unmet at launch' register (TS-05)** — signed verbatim. Its content is bounded by the adopted waivers: all eleven waivers (WV-01..WV-11) adopted at S6c means the register lists only items owed for other reasons — it no longer names SIG-GOV-003, SIG-INGEST-036 rule 6, SIG-INGEST-035's no-direct-capture clause or SIG-STORE-011. The dispute text states no response time is promised (B-8) and publishes the handling priority (WV-08).

**3. The waiver keep/lift lines (S6R-18)** — a keep/lift answer for each of WV-01, WV-03 ('for Round-11 releases'), WV-04, WV-05 ('for Round 11') and WV-08, beside **Q-29** (keep the personal address or require the alias — TS-21). Each is its own verbatim line; `continue` answers nothing here.

**4. The REVIEW-R11 findings register** — each S0/S1 finding shown as fixed (its row named) or dispositioned (the operator's words); S2/S3 findings listed for the next round's planning. Information line for S2/S3; each S0/S1 must already be settled before the sitting.

**5. The outreach-owed list's final form (ADR-171)** — the Stage-0 set as it stands owed-unmet at launch, recorded for the operator's own acts later; the packet implies nothing satisfied and contacts nobody.

**6. Status (information only; batch)** — the tail's recorded results, legs still open with their windows, CI incidents, anomalies, operator-side merges read from GitHub.

## Answers and recording

- **Answers:** `ready` / `not ready` — plus, verbatim, each own-words line (the waiver keep/lifts, Q-29, the MUSTs-unmet signature). Silence = pause (OM-18), never consent; hedged words get a yes/no question (OM-09).
- **Recorded by the orchestrator** verbatim with `date -u` in a GATE DECISIONS row and in `docs/build/readouts/GATE-ANNOUNCE.md`; no proxy signature, no paraphrase (OM-07/08); the signature act is the operator's (SIG-SEC-010 posture).
- **Re-anchoring (S6R-19):** if a REVIEW-R11 S0/S1 fix needs a row, `decompose-spec mode=extend` appends it after this row under a new `### Round 11` banner, then a new GATE-ANNOUNCE row; this row receives the appended token `superseded-by(row <n>)` — the pattern rows 184–187 use. **No row is renumbered.**
- **Effects:** a `ready` answer authorises nothing by itself — the announcement is LATER-22, human work outside the chain; a `not ready` or pause is recorded with its reasons and the chain's tail rows dispositioned accordingly.

## Load (read these — do not re-read others)

- `docs/build/LEDGER.md` — orient region (CURRENT STATE, OPERATING MODE, RETURN PASS queue) — ~12 KiB
- `docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md` — §13.5 + the U-009/D3 §5 posture — ~8 KiB
- `docs/tickets/DEFERRALS.md` — the register the packet reads — ~16 KiB
- `docs/tickets/509_P38.5__announce-readiness-review.md` — the packet's author contract — ~9 KiB
- the REVIEW-R11 findings register (unit outside the chain) — estimate — ~12 KiB
- `docs/build/readouts/GATE-ANNOUNCE.md` (P38.5's packet draft) — estimate — ~12 KiB
- `docs/tickets/510_GATE-ANNOUNCE__announce-decision.md` — this contract — ~9 KiB

**Token count (counter `utf8-bytes÷3 | ÷4`, the named proxy of S6R-27):** ≈ 78,000 B → ≈ 26,000 (÷3) · ≈ 19,500 (÷4). Working set (inference): the operator's answer and the records the orchestrator appends — small.

## Acceptance criteria

Each criterion names the BM-STATUS-01 layer it must reach (engineered · fixture-verified · staging-verified · live-executed · public · human-completed); a lower layer reached is reported as that layer, never higher.

- [ ] The packet presented is P38.5's draft (sha256 matches), every line shows its default, and the sitting did not begin while a leg was due or while any REVIEW-R11 S0/S1 finding stood unfixed and undispositioned. *(deterministic · layer: engineered)*
- [ ] The operator's answer is recorded verbatim with `date -u` in GATE DECISIONS and the readout; each own-words line (waiver keep/lifts, Q-29, the MUSTs-unmet signature) has its own verbatim answer or is recorded as defaulted. *(agentic · layer: human-completed)*
- [ ] U-009 held: nothing in the record announces the project, contacts anyone, or reads an agent act as the announcement — LATER-22 stays human work outside the chain. *(deterministic · layer: human-completed)*
- [ ] Records: GATE DECISIONS rows and the readout only gain lines (`python3 docs/build/tools/memory_guard.py all --staged` green before the record commit); the PHASE LOG pause/resume entry written; the re-anchoring rule applied if a fix row was needed. *(deterministic · layer: engineered)*

## Requirement IDs to satisfy and stamp in the PR

- **Owner (spec §56 `Owner:`):** none.
- **Cited (context; owned elsewhere):** SIG-SEC-010 (operator-signed gate records), U-009 (never auto-announced), D3-Q5 [A-17] = a (the D3 §5 checklist is the gate), S6-F3 / S6R-18 / S6R-19 (carried verbatim).
- **Outreach-owed check (ADR-171):** a gate marker contacts nobody; the outreach-owed list's final form is *read out* here as owed-unmet — the Stage-0 set stays owed under `D-R11-LATER-04`, recorded, never implied satisfied. No outside contact (ADR-171 Decision 3, U-011).

## Cross-cutting invariants

- **Defining standard (§3.1):** the packet shows each line's default; nothing is decided on silence; a recorded default is non-action, never consent.
- **Append-only (P1–P3, AGENTS.md gotcha 5):** GATE DECISIONS and the readout only gain lines; corrections name the sha/line corrected.
- **Round-11 truth rules:** no agent label counts as a human label and no agent signs; nobody outside the project is contacted (U-011) — the readiness question is about the project, never an act on the outside; the operator's personal e-mail address is never added to a file; dates come from `date -u` or git/GitHub time (OM-04); `db/sqitch.plan` lines 44–52 are never edited or re-stamped (C-10, ADR-146).
- **Additive / back-compat:** prior wire names, ids and schema contracts keep working.

## Operating clauses

OM-07/08/09 (verbatim words, no proxy signature, hedged words get a yes/no question), OM-17 (operator digest with merges read from GitHub), OM-18 (stop and ask; silence is never consent), OM-19 (no GATE while a leg is due) bind the orchestrator here. No branch, PR or CI read belongs to the gate marker itself.

## Notes

- **U-009, verbatim posture:** never auto — agents contact no one and the announcement itself is LATER-22. This marker's entire purpose is to record the operator's decision; it performs none.
- Plan row notes (S4c/S6/S6b/S6c, carried verbatim): the MUSTs-unmet list is signed verbatim (TS-05); Q-29 is revisited (keep the personal address or require the alias — TS-21); all eleven waivers adopted so the list names only items owed for other reasons; REVIEW-R11 gates on S0/S1 (S6-F3 — superseding S6's 'cited if it has finished' reading); the dispute text states no response time is promised (B-8) and publishes the handling priority (WV-08); the waiver keep/lift answers and the re-anchoring rule stand as written (S6R-18, S6R-19).
- **Re-anchoring rule restated:** a REVIEW-R11 S0/S1 fix lands as appended rows after row 510, then a new GATE-ANNOUNCE row; this row gains `superseded-by(row <n>)`. No row is renumbered.
- AC rubric: the gate's own lines are the recording checks above — no implementation verdict applies.
- Do not renumber a manifest row; append-only history; a record commit carries the `Harness:` trailer (OM-01).
