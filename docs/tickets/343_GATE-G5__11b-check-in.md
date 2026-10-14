<!-- Full contract written 2026-10-06 by PLAN-11B context C12 (row 239, `decompose-spec mode=extend`, Round-11 plan row 343, `NEW (S2)`); it replaces the T3 skeleton under the same name. Planning is not execution evidence. -->
# GATE-G5 — 11B check-in (budget, publication, rights; ING-GO-B; pre-authorises 11C named mutations)

- **Sequence:** 343 of 510 · **Phase:** Round 11 / P35 (sub-round 11B) · **Kind:** gate
- **Tag:** round11-11B
- **Harness:** devin-desktop/swe-2-high/subagent
- **base_branch:** none — a gate marker is not an `implement-spec` input and opens no branch; the orchestrator records the answer on the chain tip it holds (GATE DECISIONS row + `docs/build/readouts/GATE-G5.md`)
- **Depends on:** P35.64
- **Run:** none — a milestone gate is not an `implement-spec` input and is never guessed past; the orchestrator presents P35.64's packet and records the operator's answer
- **Gate status:** `operator check-in (S5-2 packet). `continue` answers batch lines only; own-words, publication, rights, Part VIII, identity, money and OM-20 lines need their own verbatim line; silence = pause (OM-18), never consent` — **the plan cell, verbatim.**
- **OM-20 status:** not an OM-20 row (gate marker) — it is where the 11C OM-20 list is approved or not
- **Live stage:** none — the plan cell, verbatim (an operator sitting; plan §11.2 budgets the check-ins)
- **Live window:** `none` — the plan cell, verbatim; presented only when no leg is *due* (OM-19) and P35.64 has passed; legs whose window extends past the GATE are listed and carried
- **Production mutations:** none — the gate approves or declines; every mutation it pre-authorises runs later inside its own row
- **Size budget:** 0.0 runs (gate marker); the orchestrator's sitting
- **Load (token-counted):** ≈ 78,000 B → ≈ 26,000 tokens (bytes÷3) · ≈ 19,500 (bytes÷4); ≤ ~150k → no split (A-15, §8.5) — the packet draft, the S5-2 rule, OM-19/OM-20, SIG-SEC-010/REL-012 and the PLAN-11C contracts' OM-20 lines (re-measured when the packet exists)

> Milestone gate — not an `implement-spec` input; never guessed past. An operator or authorized human record supplies the decision; an agent must not sign or assume silence is approval.

## Goal

The operator checks in at the end of 11B on budget, publication and rights, and decides — line by line, in their own words — what 11C may do without pausing: the Wave-C ingestion go, the Wave-C/vendor HG-03 flip list, the 11C OM-20 list, and whether the Class R standing go renews. Nothing is decided on silence; the 11B pre-authorisations expire here. This marker records no decision that has not happened — the packet is drafted by P35.64, presented by the orchestrator, and answered verbatim by the operator.

## The packet (drafted by P35.64; S2 §3.6, ADR-149 §6; defaults first)

Agent-drafted and labelled; its sha256 recorded before it is shown (ADR-147). Each line shows its default if unanswered — every default is non-action. Lines marked **batch** are the only ones `continue` answers.

**1. Budget** — infra month-to-date, forecast and the 11C projection against $300 (P34.5's billing export and spend ledger, incl. the 11B lines: ≈ $0.1/mo release storage, ≈ $0.04/mo candidate, the Wave-C ≈ $2.2/mo projection at the S1a upper end, Cloudflare/R2, registrar and domains); agent usage reported, not capped (A-2b); any line that would exceed the ceiling is a **money** line needing its own verbatim answer. Status lines are **batch**.

**2. Publication** — what 11B published (the first model release under its signed candidate-specific HG-11 readout — "single maintainer, no second reviewer"; "no human check performed" — quoted, not re-asked); what 11C plans: P36.72b's core-surfaces release under its own Class S readout (its cell names the same sitting as GATE-G6), and P36.70's second-release acceptance running under the Class R standing go if it is still valid. Publication lines are never pre-authorised.

**3. Rights** — **ING-GO-C** for Wave C (P37.2's legs: window 2026-11-16 → 11-20, earliest 10-26 if P37.1, PKG-07 and Q-23 are early; the tier-bump go is P37.2's own in-ticket pause, not this list's) with the **Wave-C/vendor HG-03 flip list** (OP-26) naming the sources whose rows land in 11C; the A-7 lines due in 11C. Each is a **rights** line with its own verbatim answer. Default: the wave's legs pause in-ticket; rows land with `ingestion_permitted = false` and activation skips them. Flips are executed by the operator — one commit signed with the OP-25 key, or a signed GATE DECISIONS row naming each source id (S6R-17; SIG-SEC-010; P34.28's check). **Title/note recorded, not resolved:** the plan row's title carries `ING-GO-B` while its S4c note reads `collects ING-GO-C for Wave C (P37.2 legs 11-16 -> 11-20), A-7 lines due in 11C` — the packet drafts the note's content and records the title token verbatim; ING-GO-B itself was GATE-G4's Wave-B line.

**4. The 11C OM-20 list** — exact row ids from the PLAN-11C contracts (row 340), each with its contract's mutation, restore point and rollback quoted, expiring at the next sub-round GATE (GATE-G6, or an inserted gate if the 11C re-split rule fires). Candidates as the ratified gate cells read (the §8.1 count is 10): P35.2, P35.23, P36.13, P36.33, P36.44, P36.46, P36.68, P36.75, P36.79 and any further row a written `Production mutations` header names. Never on any list: P37.2's tier bump, P36.38 (an API roll that changes a public route's response), P36.72b's HG-11 readout, every HG-03 flip, and P36.70 if the standing go has lapsed — the never-pre-authorised classes of plan §3.3. Plus any 11B leg whose pre-authorisation expires here unrun — re-listed by row id or left to an in-ticket go. An **OM-20** line: approved only by its own verbatim line, never by `continue`. Default: nothing pre-authorised — each named mutation pauses in-ticket.

**5. Class R standing-go renewal (B-9)** — the operator's adopted text, renewed verbatim or not (agent-drafted, adopted by the operator at 2026-10-01T04:35:53Z; sha256 `e4e24975b854…`): "Agents may promote a Class R release built from the same signed code whose diff stays within bounds (records −2%…+15%, no compartment <−5% or >+50%, no source loses >20%), with all checks green and no waivers; this go expires at the next sub-round gate or after 30 days, and is void on any ratchet regression, Part VIII screen change or new source." It expires at the next sub-round GATE or after 30 days, whichever is first; it is void on any ratchet regression, Part VIII screen change or new source (TS-13); it is never renewed by `continue`. Default: it lapses → every release is Class S, and P36.70's first Class R promotion becomes an in-ticket pause. Recorded as a GATE DECISIONS `kind: pre-authorization` row.

**6. Status (information only; batch)** — the per-row layered status from P35.64's acceptance note (the 11B exit items and every row's highest layer); the live-leg queue (any carried 11B leg — P35.61's apply leg if its go was never given; legs whose window extends past this GATE); CI incidents; anomalies; operator-side merges read from GitHub; the D-K2-1 top-50 organisation review (OP-14, ≈ 1–2 h — due by this sitting, its outcome reported or carried); whether PLAN-11C's Phase-4 review fired the 11C re-split rule (> 85 engineering rows or > 75 engineering runs; 11C stood at 76 / 66.5 at S6c); the isolation probe repeated at this GATE (plan §8.5) — nothing to answer here.

## Answers and recording

- **Answers (S2 §3.6):** `continue` (every **batch** line takes its default) · `continue with <lines>` · `pause`. Every other line needs its own verbatim line; an unanswered non-batch line takes its non-action default; silence on the whole packet = pause (OM-18), never consent.
- **Recorded by the orchestrator** verbatim with `date -u` in a GATE DECISIONS row (and a `kind: pre-authorization` row for the OM-20 list and for the Class R renewal) and in `docs/build/readouts/GATE-G5.md` under the packet; no proxy signature, no paraphrase (OM-07/08); hedged words get a yes/no question (OM-09). Flip lines and any Class S go are covered by an operator-signed commit or GATE DECISIONS record (SIG-SEC-010).
- **Effects:** the 11B S5-3/G4 pre-authorisations expire at the answer; the approved 11C list takes effect with its expiry (`expires: GATE-G6`); a PHASE LOG pause/resume entry records the sitting; the LEDGER advances to row 344 only after the answer is recorded.

## Load (read these — do not re-read others)

Paths under `PD/` are under `docs/build/planning/2026-09-30-next-phase/`.

- `docs/build/LEDGER.md` — orient region (CURRENT STATE, OPERATING MODE, RETURN PASS queue) — counted at its 12 KiB budget — 12,288 B
- `PD/NEXT_PHASE_PLAN.md` § 8.3 Gates, pauses and operator touchpoints — what the packet carries — 2,571 B
- `PD/NEXT_PHASE_PLAN.md` § 3.3 OM-19 · OM-20 (lines) — due legs; never-list; standing go — 3,166 B
- `PD/NEXT_PHASE_PLAN.md` § 8.1 (lines) — the 11C counts the re-split rule reads — 1,024 B
- `PD/design/S2-round-structure.md` § 3.6 · 4.2 · 7.3 — packet parts and answers; the 11B exit; defaults — 5,120 B
- `docs/adr/ADR-149-round-11-operating-model.md` § 5 · 6 — OM-20 classes; the S5-2 packet rule — 2,673 B
- `docs/2_canonical_design_spec.md` § SIG-SEC-010 · SIG-REL-012 (lines) — operator-signed gate records; the standing go — 2,061 B
- `docs/build/readouts/GATE-G5.md (P35.64's packet draft)` — the packet (estimate — drafted by P35.64) — 12,288 B
- `docs/tickets/ (the OM-20 lines of the PLAN-11C contracts)` — each candidate's mutation, restore point and rollback (estimate — written by row 340) — 16,384 B
- `data/round11_plan.csv` rows 343–345 (lines) — this row's cells and P37.2's Wave-C cells — 4,096 B
- `docs/tickets/343_GATE-G5__11b-check-in.md` — this contract — 10,240 B

**Token count (counter `utf8-bytes÷3 | ÷4`, the named proxy of S6R-27 — `swe-2-high`'s tokenizer is unknown):** ≈ 78,000 B → ≈ 26,000 (÷3) · ≈ 19,500 (÷4). Working set (inference): the operator's answer and the records the orchestrator appends — small.

## Acceptance criteria

Each criterion names the BM-STATUS-01 layer it must reach (engineered · fixture-verified · staging-verified · live-executed · public · human-completed); a lower layer reached is reported as that layer, never higher.

- [ ] The packet presented is P35.64's draft (sha256 matches) and every line shows its default; it was not presented while a leg was due. *(deterministic · layer: engineered)*
- [ ] The operator's answer is recorded verbatim with `date -u` in GATE DECISIONS and the readout; each OM-20, rights, money and own-words line has its own verbatim answer or is recorded as defaulted. *(agentic · layer: human-completed)*
- [ ] The 11C OM-20 list (if any) names exact row ids with `expires: GATE-G6`; the Class R renewal (if given) is quoted with its expiry; ING-GO-C and the Wave-C/vendor flip list are recorded as answered or defaulted. *(deterministic · layer: human-completed)*
- [ ] Records: GATE DECISIONS rows and the readout only gain lines (`python3 docs/build/tools/memory_guard.py all --staged` green before the record commit); the PHASE LOG pause/resume entry written; the LEDGER advanced to row 344 only after the answer. *(deterministic · layer: engineered)*

## Requirement IDs to satisfy and stamp in the PR

- **Owner (spec §56 `Owner:`):** none.
- **Cited (context; owned elsewhere):** SIG-SEC-010 (operator-signed gate records; P34.28), SIG-REL-012 (Class R and the standing go; P35.60).
- **Outreach-owed check (PLAN-11B deliverable 8a, ADR-171) — recorded why it does not apply:** a gate marker performs no connector work and contacts nobody; the flip-list lines it collects are the operator's own decisions recorded verbatim. The Stage-0 set stays owed — unmet at launch — under `D-R11-LATER-04` (recorded, never implied satisfied). No outside contact (ADR-171 Decision 3, U-011).

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

- Plan row notes (S4c, S6): G5 collects ING-GO-C for Wave C (P37.2 legs 11-16 → 11-20), the A-7 lines due in 11C, the Wave-C/vendor HG-03 flip list (OP-26), the 11C OM-20 list and the Class R standing-go renewal (B-9); Q-23 (a), A-10 (no review) and I8-Q5 (a) were answered at GATE-P — recorded, not re-asked.
- The title's `ING-GO-B` vs the note's `ING-GO-C` is recorded verbatim as plan-internal drift (§ Rights part); ING-GO-B was GATE-G4's Wave-B line — the packet drafts the note's content.
- The isolation probe repeats at each sub-round GATE and after any orchestrator restart (plan §8.5) — the orchestrator's work, reported in the packet's status part.
- AC rubric: the gate's own lines are the recording checks above — no implementation verdict applies.
- Do not renumber a manifest row; append-only history; a record commit carries the `Harness:` trailer (OM-01).
