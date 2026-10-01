<!-- Full contract written 2026-10-01 by Stage-B unit SEED-13d (Round-11 T3, plan Appendix A T3 second bullet) from docs/build/planning/2026-09-30-next-phase/data/round11_plan.csv row 260 and ticket_catalog `NEW (S2)`; it replaces the T3 first-context file under the same name. Planning is not execution evidence. -->
# GATE-G4 — 11A check-in (budget, publication, rights; pre-authorises 11B named mutations)

- **Sequence:** 260 of 510 · **Phase:** Round 11 / P34 (sub-round 11A) · **Kind:** gate
- **Tag:** round11-11A
- **Harness:** devin-desktop/swe-2-high/subagent
- **base_branch:** none — a gate marker is not an `implement-spec` input and opens no branch; the orchestrator records the answer on the chain tip it holds (GATE DECISIONS row + `docs/build/readouts/GATE-G4.md`)
- **Depends on:** P34.47
- **Run:** none — a milestone gate is not an `implement-spec` input and is never guessed past; the orchestrator presents P34.47's packet and records the operator's answer
- **Gate status:** operator check-in (S5-2 packet). S5-2 **"Ratify (Recommended)"** (round 19, 2026-10-01T04:54:19Z): `continue` answers batch lines only; own-words, publication, rights, Part VIII, identity, money and OM-20 lines need their own verbatim line; the OM-20 list is never approved by `continue`; silence = pause (OM-18), never consent
- **OM-20 status:** not an OM-20 row (gate marker) — it is where the 11B OM-20 list is approved or not
- **Live stage:** none (an operator sitting, ≈ 2026-10-15 → 10-17, 1–1.5 h; plan §11.2)
- **Live window:** presented only when no leg is *due* (OM-19) and P34.47 has passed; legs whose window extends past the GATE are listed and carried
- **Production mutations:** none — the gate approves or declines; every mutation it pre-authorises runs later inside its own row
- **Size budget:** 0.0 runs (gate marker); the orchestrator's sitting
- **Load (token-counted):** 71,154 B → ≈ 23,718 tokens (bytes÷3) · ≈ 17,788 (bytes÷4); ≤ ~150k → no split (A-15, §8.5)

## Goal

The operator checks in at the end of 11A on budget, publication and rights, and decides — line by line, in their own words — what 11B may do without pausing: the wave go-lines and flip lists, the 11B OM-20 list, the Class R standing-go renewal and the API-roll go. Nothing is decided on silence; the 11A pre-authorisations expire here.

## The packet (drafted by P34.47; S2 §3.6, ADR-149 §6; defaults first)

Agent-drafted and labelled; its sha256 recorded before it is shown (ADR-147). Each line shows its default if unanswered — every default is non-action. Lines marked **batch** are the only ones `continue` answers.

**1. Budget** — infra month-to-date, forecast and the 11B projection against $300 (P34.5's billing export and spend ledger, incl. Cloudflare/R2, registrar and domains); agent usage reported, not capped (A-2b); any line that would exceed the ceiling is a **money** line needing its own verbatim answer (none expected). Status lines are **batch**.

**2. Publication** — what 11A published (republish #1 and #2, each under its own verbatim in-ticket go — quoted, not re-asked); what 11B plans: P35.63, the first model release under a signed HG-11 readout ("single maintainer, no second reviewer"; "no human check performed"), with its date window and new route families. **The P35.57 API-roll go** — its own verbatim line (a roll that changes a public route's response is never pre-authorised). P35.57 is an improvement, not a gate: under A-20 = a ("Yes, with labels", 04:25:48Z) the 11B structural spine writes do not wait for it. Default if unanswered: P35.57 pauses in-ticket (non-action).

**3. Rights** — **ING-GO-A** (Wave A legs 2026-10-19 → 10-23, 14:00–20:00Z; P35.11) with the operator's Wave A HG-03 flip list (OP-26), and **ING-GO-B** (Wave B legs 10-26 → 11-05, one family a day; P36.12) with the Wave B flip list (FEA-02); the A-7/B-32 lines due in 11B (Part VIII screen lanes per family; B-42's agent clear is disclosed, not asked). Each is a **rights** line with its own verbatim answer. Default: the wave's legs pause in-ticket; rows land with `ingestion_permitted = false` and activation skips them. Flips are executed by the operator — one commit signed with the OP-25 key, or a signed GATE DECISIONS row naming each source id (S6R-17; SIG-SEC-010; P34.28's G4c check). Carried, not asked unless ready: E4-R6a BidNet (terms captured by P34.38; due at GATE-G6 at the latest, S6R-28).

**4. The 11B OM-20 list** — exact row ids from the PLAN-11B contracts (row 239), each with its contract's mutation, restore point and rollback quoted, expiring at the next sub-round GATE (GATE-G5, or GATE-G4b if the re-split rule fires). Candidates (the 19 OM-20 rows of 11B): P35.5, P35.1a, P35.14a, P35.15a, P35.15b, P35.1b, P35.16, P35.17, P35.22, P35.24, P35.25, P35.26, P35.27, P35.32, P35.41, P35.46, P35.53, P35.59, P35.62. Never on any list: P35.57, P35.11, P35.14b, P36.12, P35.61, P35.63 and every HG-03 flip (incl. P35.17's boundary flip). Plus any 11A leg whose pre-authorisation expires here unrun (e.g. P34.45's ER re-run, P34.43 L2, P34.46's post-deploy drill re-run of P34.6) — re-listed by row id or left to an in-ticket go. An **OM-20** line: approved only by its own verbatim line, never by `continue`. Default: nothing pre-authorised — each named mutation pauses in-ticket.

**5. Class R standing-go renewal (B-9)** — the operator's adopted text, renewed verbatim or not (agent-drafted, adopted by the operator at 2026-10-01T04:35:53Z; sha256 `e4e24975b854…`): "Agents may promote a Class R release built from the same signed code whose diff stays within bounds (records −2%…+15%, no compartment <−5% or >+50%, no source loses >20%), with all checks green and no waivers; this go expires at the next sub-round gate or after 30 days, and is void on any ratchet regression, Part VIII screen change or new source." It expires at the next sub-round GATE or after 30 days, whichever is first; it is void on any ratchet regression, Part VIII screen change or new source (TS-13); it is never renewed by `continue`. Default: it lapses → every release is Class S. Recorded as a GATE DECISIONS `kind: pre-authorization` row (CARRY: SEED-11b/SEED-17).

**6. Status (information only; batch)** — the per-row layered status from P34.47's acceptance note; the live-leg queue (P34.39b's legs carried; any other leg with its window and go); CI incidents; anomalies; operator-side merges read from GitHub; the managed-certificate status; RI-01; the isolation probe repeated at this GATE (plan §8.5); that B-2's notice allowance (N-1…N-7 by sha256) ends here, so every later sentence needs per-text confirmation; whether PLAN-11B's sizing review fired the 11B re-split rule (> 85 engineering rows or > 75 runs) and so added a **GATE-G4b** at the Wave-B activation boundary (S6R-15); and, for the record, the REVIEW-R11 → GATE-ANNOUNCE rule (GATE-ANNOUNCE waits for each REVIEW-R11 S0/S1 finding to be fixed or dispositioned; fix rows are appended after row 510 with a new GATE-ANNOUNCE row and row 510 `superseded-by(row <n>)`; S6-F3, S6R-19) — nothing to answer here.

**Carried question (only if not already answered at GATE-B):** does the approved OM-20 entry "P34.6 (drill clone)" also cover P34.6's first monthly logical export and the `sig-backups` lifecycle/relabel changes? SEED-13b read it as not covering them (in-ticket go). Also the P34.40 "dark" reading if the orchestrator raised it.

## Answers and recording

- **Answers (S2 §3.6):** `continue` (every **batch** line takes its default) · `continue with <lines>` · `pause`. Every other line needs its own verbatim line; an unanswered non-batch line takes its non-action default; silence on the whole packet = pause (OM-18).
- **Recorded by the orchestrator** verbatim with `date -u` in a GATE DECISIONS row (and a `kind: pre-authorization` row for the OM-20 list and for the Class R renewal) and in `docs/build/readouts/GATE-G4.md` under the packet; no proxy signature, no paraphrase (OM-07/08); hedged words get a yes/no question (OM-09). Flip lines and any Class S go are covered by an operator-signed commit or GATE DECISIONS record (SIG-SEC-010).
- **Effects:** the 11A S5-3 pre-authorisations expire at the answer; the approved 11B list takes effect with its expiry; a PHASE LOG pause/resume entry records the sitting; the LEDGER advances to row 261 only after the answer is recorded.

## Load (read these — do not re-read others)

Paths under `PD/` are under `docs/build/planning/2026-09-30-next-phase/`. Byte counts are UTF-8 bytes of exactly the named part, measured 2026-10-01 on the `r11/seed` working tree.

- `docs/build/LEDGER.md` — orient region (CURRENT STATE, OPERATING MODE, RETURN PASS queue) — counted at its 12 KiB budget — 12,288 B
- `PD/NEXT_PHASE_PLAN.md` § 8.3 Gates, pauses and operator touchpoints — what the packet carries — 2,571 B
- `PD/NEXT_PHASE_PLAN.md` § 3.3 OM-19 · OM-20 (lines) — due legs; never-list; standing go — 3,166 B
- `PD/NEXT_PHASE_PLAN.md` § 11.2 touchpoints (lines) — the GATE-G4 sitting and its neighbours — 3,063 B
- `PD/design/S2-round-structure.md` § 3.6 · 7.3 — packet parts and answers; defaults — 2,943 B
- `docs/adr/ADR-149-round-11-operating-model.md` § 5 · 6 — OM-20 classes; the S5-2 packet rule — 2,673 B
- `docs/2_canonical_design_spec.md` § SIG-SEC-010 · SIG-REL-012 (lines) — operator-signed gate records; the standing go — 2,061 B
- `docs/build/readouts/GATE-G4.md (P34.47's packet draft)` — the packet (estimate — drafted by P34.47) — 12,288 B
- `docs/tickets/ (the OM-20 lines of the PLAN-11B contracts)` — each candidate's mutation, restore point and rollback (estimate — written by row 239) — 16,384 B
- `docs/tickets/260_GATE-G4__11a-check-in.md` — this contract — 13,717 B

**Token count (counter `utf8-bytes÷3 | ÷4`, the named proxy of S6R-27 — `swe-2-high`'s tokenizer is unknown):** 71,154 B → ≈ 23,718 (÷3) · ≈ 17,788 (÷4). Working set (inference): the operator's answer and the records the orchestrator appends — small.

## Acceptance criteria

Each criterion names the BM-STATUS-01 layer it must reach (engineered · fixture-verified · staging-verified · live-executed · public · human-completed); a lower layer reached is reported as that layer, never higher.

- [ ] The packet presented is P34.47's draft (sha256 matches) and every line shows its default; it was not presented while a leg was due. *(deterministic · layer: engineered)*
- [ ] The operator's answer is recorded verbatim with `date -u` in GATE DECISIONS and the readout; each OM-20, rights, money and own-words line has its own verbatim answer or is recorded as defaulted. *(agentic · layer: human-completed)*
- [ ] The 11B OM-20 list (if any) names exact row ids with expiry; the Class R renewal (if given) is quoted with its expiry; ING-GO-A/B and the flip lists are recorded as answered or defaulted. *(deterministic · layer: human-completed)*
- [ ] Records: GATE DECISIONS rows and the readout only gain lines (`python3 docs/build/tools/memory_guard.py all --staged` green before the record commit); the PHASE LOG pause/resume entry written; the LEDGER advanced to row 261 only after the answer. *(deterministic · layer: engineered)*

## Requirement IDs to satisfy and stamp in the PR

- **Owner (spec §56 `Owner:`):** none.
- **Cited (context; owned elsewhere):** SIG-SEC-010 (operator-signed gate records; P34.28), SIG-REL-012 (Class R and the standing go; P35.60).

## Cross-cutting invariants

- **Defining standard (§3.1):** no unexplained dots or edges, no silent overwrites, no synthetic certainty; every claim has evidence, every inference is labelled, every contradiction stays visible.
- **Part VIII binds (§0.7):** no plate, trip or per-person data; officer-naming default-deny; sensitivity tiers, coordinate rules, licence gate and ODbL separation hold.
- **Append-only (P1–P3, AGENTS.md gotcha 5):** no `UPDATE`/`DELETE` on the claim spine; corrections are new rows; protected build records only gain lines at their ends (OM-13); landed ADR bodies are never edited.
- **Fail-closed sources (gotcha 4):** this row flips no `ingestion_permitted` and ticks no `HG-nn` gate (HG-03 flips are the operator's, OP-26).
- **Round-11 truth rules:** no agent label counts as a human label and no agent signs ("no human check performed"); nobody outside the project is contacted (U-011); the operator's personal e-mail address is never added to a file; dates come from `date -u` or git/GitHub time (OM-04); `db/sqitch.plan` lines 44–52 are never edited or re-stamped (C-10, ADR-146).
- **Additive / back-compat:** prior wire names, ids and schema contracts keep working; new fields are optional with today's behaviour as the default.

## Operating clauses

OM-07/08/09 (verbatim words, no proxy signature, hedged words get a yes/no question), OM-17 (operator digest with merges read from GitHub), OM-18 (stop and ask; silence is never consent), OM-19 (no GATE while a leg is due) and OM-20 (the list is exact, bounded, expiring and never approved on silence) bind the orchestrator here. No branch, PR or CI read belongs to the gate marker itself.

## Notes

- Plan row notes (S4c, S6): G4 collects ING-GO-A, ING-GO-B (Wave B legs 10-26 → 11-05), the P35.57 API-roll go, A-7/B-32 lines due in 11B, the Wave A/B HG-03 flip lists (OP-26), the 11B OM-20 list and the Class R standing-go renewal (B-9); every other S5 line was answered at GATE-P.
- The isolation probe repeats at each sub-round GATE and after any orchestrator restart (plan §8.5) — the orchestrator's work, reported in the packet's status part.
