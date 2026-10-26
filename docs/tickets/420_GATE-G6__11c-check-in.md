<!-- Full contract written 2026-10-25 by PLAN-11C context C11 (row 340, `decompose-spec mode=extend`, Round-11 plan row 420, `NEW (S2)`); it replaces the T3 skeleton under the same name. Planning is not execution evidence. -->
# GATE-G6 — 11C check-in (budget, publication, rights; ING-GO-C/D; Wave-D scope; pre-authorises 11D named mutations)

- **Sequence:** 420 of 510 · **Phase:** Round 11 / P36 (sub-round 11C) · **Kind:** gate
- **Tag:** round11-11C
- **Harness:** devin-desktop/swe-2-high/subagent
- **base_branch:** none — a gate marker is not an `implement-spec` input and opens no branch; the orchestrator records the answer on the chain tip it holds (GATE DECISIONS row + `docs/build/readouts/GATE-G6.md`)
- **Depends on:** P36.73 — the plan cell, verbatim
- **Run:** none — a milestone gate is not an `implement-spec` input and is never guessed past; the orchestrator presents P36.73's packet and records the operator's answer
- **Gate status:** `operator check-in (S5-2 packet). `continue` answers batch lines only; own-words, publication, rights, Part VIII, identity, money and OM-20 lines need their own verbatim line; silence = pause (OM-18), never consent` — **the plan cell, verbatim.**
- **OM-20 status:** not an OM-20 row (gate marker) — it is where the 11D OM-20 list is approved or not
- **Live stage:** none — the plan cell, verbatim (an operator sitting; plan §11.2 budgets the check-ins)
- **Live window:** `none` — the plan cell, verbatim; presented only when no leg is *due* (OM-19) and P36.73 has passed; legs whose window extends past the GATE are listed and carried
- **Production mutations:** none — the gate approves or declines; every mutation it pre-authorises runs later inside its own row
- **Size budget:** 0.0 runs (gate marker); the orchestrator's sitting
- **Load (token-counted):** ≈ 78,000 B → ≈ 26,000 tokens (bytes÷3) · ≈ 19,500 (bytes÷4); ≤ ~150k → no split (A-15, §8.5) — the packet draft, the S5-2 rule, OM-19/OM-20, SIG-SEC-010/REL-012 and the PLAN-11D contracts' OM-20 lines (re-measured when the packet exists)

> Milestone gate — not an `implement-spec` input; never guessed past. An operator or authorized human record supplies the decision; an agent must not sign or assume silence is approval.

## Goal

The operator checks in at the end of 11C on budget, publication and rights, and decides — line by line, in their own words — what 11D may do without pausing: **ING-GO-D** for Wave D, the **Wave-D HG-03 flip list** (OP-26), the **11D OM-20 list** (whose entries must name written PLAN-11D contracts), and whether the Class R standing go renews again. **I8-Q5 (Wave-D scope) was answered `a` at GATE-P — Wave D is in scope (S6); it is recorded, not re-asked.** The same sitting hosts P36.72b's HG-11 Class S readout for the core-surfaces release (its contract's plan cell, verbatim). Nothing is decided on silence; the 11C pre-authorisations expire here. This marker records no decision that has not happened — the packet is drafted by P36.73, presented by the orchestrator, and answered verbatim by the operator.

## The packet (drafted by P36.73; S2 §3.6, ADR-149 §6; defaults first)

Agent-drafted and labelled; its sha256 recorded before it is shown (ADR-147). Each line shows its default if unanswered — every default is non-action. Lines marked **batch** are the only ones `continue` answers.

**1. Budget** — infra month-to-date, forecast and the 11D projection against the $300 ceiling; agent usage reported, not capped (A-2b); any line that would exceed the ceiling is a **money** line needing its own verbatim answer. Status lines are **batch**.

**2. Publication** — what 11C published (the core-surfaces release under P36.72b's HG-11 Class S readout — **held in this same sitting**, P36.72b's plan cell verbatim; the second-release acceptance under P36.70, Class R if the standing go survived GATE-G5, else Class S); what 11D plans next. Publication lines are never pre-authorised.

**3. Rights** — **ING-GO-D** for Wave D (the next ingestion wave — the keyed-API unblocks D-SOURCES.7-2/8-2, the federal resume D-FEDERAL.1-1, the Wave-D sources the S6 list names) with the **Wave-D HG-03 flip list** (OP-26) naming: N1–N21, ACQ-23a/b, DocumentCloud, Sourcewell/OMNIA, Axon Connect, RB-06b, RB-08 — the plan cell's verbatim set. Each is a **rights** line with its own verbatim answer. Default: the wave's legs pause in-ticket; rows land with `ingestion_permitted = false` and activation skips them. Flips are executed by the operator — one commit signed with the OP-25 key, or a signed GATE DECISIONS row naming each source id (S6R-17; SIG-SEC-010; P34.28's check).

**4. The 11D OM-20 list** — exact row ids from the written PLAN-11D contracts (row 418 — the dependency P36.73 carries), each with its contract's mutation, restore point and rollback quoted, expiring at the next sub-round GATE (GATE-ACCEPT-R11, or an inserted gate if an 11D re-split rule fires). Candidates are whatever PLAN-11D's `Production mutations` headers name — **the packet lists only written contracts; a row without a contract cannot be listed**. The never-pre-authorised classes of plan §3.3 hold (every HG-03 flip; every HG-11 readout; any Class R promotion if the standing go has lapsed; an API roll that changes a public route's response). Plus any 11C leg whose pre-authorisation expires here unrun — re-listed by row id or left to an in-ticket go. An **OM-20** line: approved only by its own verbatim line, never by `continue`. Default: nothing pre-authorised — each named mutation pauses in-ticket.

**5. Class R standing-go renewal (B-9)** — the operator's adopted text, renewed verbatim or not (the text as GATE-G5 last recorded it — quoted verbatim in the packet, never re-drafted by the agent). It expires at the next sub-round GATE or after 30 days, whichever is first; it is void on any ratchet regression, Part VIII screen change or new source (TS-13); it is never renewed by `continue`. Default: it lapses → every 11D release is Class S. Recorded as a GATE DECISIONS `kind: pre-authorization` row.

**6. Status (information only; batch)** — the per-row layered status from P36.73's acceptance pass (the 11C exit items and every row's highest layer); the live-leg queue (any carried leg — P37.2's Wave-C legs if their window extends past this sitting; legs whose window extends past this GATE); CI incidents; anomalies; operator-side merges read from GitHub; whether PLAN-11D's Phase-4 review fired the 11D re-split rule, with its counts; the isolation probe repeated at this GATE (plan §8.5) — nothing to answer here.

## Answers and recording

- **Answers (S2 §3.6):** `continue` (every **batch** line takes its default) · `continue with <lines>` · `pause`. Every other line needs its own verbatim line; an unanswered non-batch line takes its non-action default; silence on the whole packet = pause (OM-18), never consent.
- **Recorded by the orchestrator** verbatim with `date -u` in a GATE DECISIONS row (and a `kind: pre-authorization` row for the 11D OM-20 list and for the Class R renewal) and in `docs/build/readouts/GATE-G6.md` under the packet; no proxy signature, no paraphrase (OM-07/08); hedged words get a yes/no question (OM-09). Flip lines and any Class S go are covered by an operator-signed commit or GATE DECISIONS record (SIG-SEC-010).
- **Effects:** the 11C pre-authorisations (GATE-G5's approved list, if any) expire at the answer; the approved 11D list takes effect with its expiry (`expires: GATE-ACCEPT-R11` — or the inserted gate if an 11D re-split fired); a PHASE LOG pause/resume entry records the sitting; the LEDGER advances to row 421 only after the answer is recorded.

## Load (read these — do not re-read others)

Paths under `PD/` are under `docs/build/planning/2026-09-30-next-phase/`.

- `docs/build/LEDGER.md` — orient region (CURRENT STATE, OPERATING MODE, RETURN PASS queue) — counted at its 12 KiB budget — 12,288 B
- `PD/NEXT_PHASE_PLAN.md` § 8.3 Gates, pauses and operator touchpoints — what the packet carries — 2,571 B
- `PD/NEXT_PHASE_PLAN.md` § 3.3 OM-19 · OM-20 (lines) — due legs; never-list; standing go — 3,166 B
- `PD/NEXT_PHASE_PLAN.md` § 8.1 (lines) — the sub-round counts the re-split rule reads — 1,024 B
- `PD/design/S2-round-structure.md` § 3.6 · 4.2 · 7.3 — packet parts and answers; the sub-round exit; defaults — 5,120 B
- `docs/adr/ADR-149-round-11-operating-model.md` § 5 · 6 — OM-20 classes; the S5-2 packet rule — 2,673 B
- `docs/2_canonical_design_spec.md` § SIG-SEC-010 · SIG-REL-012 (lines) — operator-signed gate records; the standing go — 2,061 B
- `docs/build/readouts/GATE-G6.md (P36.73's packet draft)` — the packet (estimate — drafted by P36.73) — 12,288 B
- `docs/tickets/ (the OM-20 lines of the PLAN-11D contracts)` — each candidate's mutation, restore point and rollback (estimate — written by row 418) — 16,384 B
- `data/round11_plan.csv` rows 418–421 (lines) — this row's cells and the 11D boundary — 4,096 B
- `docs/tickets/420_GATE-G6__11c-check-in.md` — this contract — 10,240 B

**Token count (counter `utf8-bytes÷3 | ÷4`, the named proxy of S6R-27 — `swe-2-high`'s tokenizer is unknown):** ≈ 78,000 B → ≈ 26,000 (÷3) · ≈ 19,500 (÷4). Working set (inference): the operator's answer and the records the orchestrator appends — small.

## Acceptance criteria

Each criterion names the BM-STATUS-01 layer it must reach (engineered · fixture-verified · staging-verified · live-executed · public · human-completed); a lower layer reached is reported as that layer, never higher.

- [ ] The packet presented is P36.73's draft (sha256 matches) and every line shows its default; it was not presented while a leg was due. *(deterministic · layer: engineered)*
- [ ] The operator's answer is recorded verbatim with `date -u` in GATE DECISIONS and the readout; each OM-20, rights, money and own-words line has its own verbatim answer or is recorded as defaulted. *(agentic · layer: human-completed)*
- [ ] The 11D OM-20 list (if any) names exact row ids traceable to written PLAN-11D contract headers with `expires:` set; the Class R renewal (if given) is quoted with its expiry; ING-GO-D and the Wave-D flip list are recorded as answered or defaulted. *(deterministic · layer: human-completed)*
- [ ] Records: GATE DECISIONS rows and the readout only gain lines (`python3 docs/build/tools/memory_guard.py all --staged` green before the record commit); the PHASE LOG pause/resume entry written; the LEDGER advanced to row 421 only after the answer. *(deterministic · layer: engineered)*

## Requirement IDs to satisfy and stamp in the PR

- **Owner (spec §56 `Owner:`):** none.
- **Cited (context; owned elsewhere):** SIG-SEC-010 (operator-signed gate records; P34.28), SIG-REL-012 (Class R and the standing go; P35.60).
- **Outreach-owed check (PLAN-11B deliverable 8a lineage, ADR-171) — recorded why it does not apply:** a gate marker performs no connector work and contacts nobody; the Wave-D flip-list lines it collects are the operator's own decisions recorded verbatim. The Stage-0 set stays owed — unmet at launch — under `D-R11-LATER-04` (recorded, never implied satisfied). No outside contact (ADR-171 Decision 3, U-011).

## Cross-cutting invariants

- **Defining standard (§3.1):** the packet shows each line's default; nothing is decided on silence; a recorded default is non-action, never consent.
- **Part VIII binds (§0.7):** Part VIII lines need their own verbatim answers — they are never batch lines.
- **Append-only (P1–P3, AGENTS.md gotcha 5):** GATE DECISIONS and the readout only gain lines; corrections name the sha/line corrected.
- **Fail-closed sources (gotcha 4):** this marker flips no `ingestion_permitted` and ticks no `HG-nn` gate itself — the operator's lines do, or nothing does.
- **Round-11 truth rules:** no agent label counts as a human label and no agent signs ("no human check performed"); nobody outside the project is contacted (U-011); the operator's personal e-mail address is never added to a file; dates come from `date -u` or git/GitHub time (OM-04); `db/sqitch.plan` lines 44–52 are never edited or re-stamped (C-10, ADR-146).
- **Additive / back-compat:** prior wire names, ids and schema contracts keep working.

## Operating clauses

OM-07/08/09 (verbatim words, no proxy signature, hedged words get a yes/no question), OM-17 (operator digest with merges read from GitHub), OM-18 (stop and ask; silence is never consent), OM-19 (no GATE while a leg is due) and OM-20 (the list is exact, bounded, expiring and never approved on silence) bind the orchestrator here. No branch, PR or CI read belongs to the gate marker itself.

## Notes

- Plan row notes (S4c, S6): G6 collects ING-GO-D, the Wave-D flip list (N1–N21, ACQ-23a/b, DocumentCloud, Sourcewell/OMNIA, Axon Connect, RB-06b, RB-08; OP-26), the 11D OM-20 list and the standing-go renewal; **I8-Q5 was answered `a` at GATE-P — Wave D in scope** — recorded, not re-asked.
- **Title/note drift, recorded not resolved:** the plan row's title carries `ING-GO-C/D` while its S4c note reads `collects ING-GO-D` — the packet drafts the note's content (ING-GO-C was GATE-G5's Wave-C line, already answered there or carried by GATE-G5's record; the packet reads the recorded answer, never re-asks it). The same drift shape GATE-G5's contract recorded for `ING-GO-B`.
- The same sitting hosts P36.72b's HG-11 Class S readout (P36.72b's plan cell, verbatim) — a decision line of its own, never batch.
- The isolation probe repeats at each sub-round GATE and after any orchestrator restart (plan §8.5) — the orchestrator's work, reported in the packet's status part.
- AC rubric: the gate's own lines are the recording checks above — no implementation verdict applies.
- Do not renumber a manifest row; append-only history; a record commit carries the `Harness:` trailer (OM-01).
