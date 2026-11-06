<!-- Full contract written 2026-11-05 by PLAN-11D context D11 (row 418, `decompose-spec mode=extend`, Round-11 plan row 504, `NEW (S2)`); it replaces the T3 skeleton under the same name. Planning is not execution evidence. -->
# GATE-ACCEPT-R11 — operator accepts Round-11 closure and deviations

- **Sequence:** 504 of 510 · **Phase:** Round 11 / P38 (sub-round 11D-tail) · **Kind:** gate
- **Tag:** round11-11D
- **Harness:** devin-desktop/swe-2-high/subagent
- **base_branch:** none — a gate marker is not an `implement-spec` input and opens no branch; the orchestrator records the answer on the chain tip it holds (GATE DECISIONS row + `docs/build/readouts/GATE-ACCEPT-R11.md`)
- **Depends on:** P38.2 — the plan cell, verbatim
- **Run:** none — a milestone gate is not an `implement-spec` input and is never guessed past; the orchestrator presents P38.2's acceptance packet and records the operator's answer
- **Gate status:** `operator signs the accepted-deviations list verbatim (HG-14 domain); never guessed past` — **the plan cell, verbatim.**
- **OM-20 status:** not an OM-20 row (gate marker)
- **Live stage:** none — the plan cell, verbatim
- **Live window:** `none` — the plan cell, verbatim; presented only when no leg is *due* (OM-19) and P38.2 has passed; legs whose window extends past the GATE are listed and carried
- **Live legs:** none (leg runs: 0)
- **Production mutations:** none — the gate accepts or declines; every mutation it touches ran inside its own row
- **Size budget:** 0.0 runs (gate marker); the orchestrator's sitting
- **Load (token-counted):** ≈ 66,000 B → ≈ 22,000 tokens (bytes÷3) · ≈ 16,500 (bytes÷4); ≤ ~150k → no split (A-15, §8.5) — P38.2's acceptance packet, the accepted-deviations list, the layered status register and the deferral register (re-measured when the packet exists)

> Milestone gate — not an `implement-spec` input; never guessed past. An operator or authorized human record supplies the decision; an agent must not sign or assume silence is approval.

## Goal

The operator accepts Round-11 closure — or pauses it — at the end of the tail. The artifact is **P38.2's acceptance packet**: the gap-closure record, the two-sum headline per status layer (P38.1a/b), and the **accepted-deviations list**, which the operator signs **verbatim** (the HG-14 domain — the signature is a human act, never an agent's). This marker records no acceptance that has not happened: the packet is drafted by P38.2, presented by the orchestrator, and answered verbatim by the operator. A declined or unanswered line is a recorded default — never consent (OM-18).

## The packet (drafted by P38.2; defaults first)

Agent-drafted and labelled; its sha256 recorded before it is shown (ADR-147). Each line shows its default if unanswered — every default is non-action.

**1. The accepted-deviations list (HG-14 domain)** — every deviation the round accepted, named with its basis: deferred obligations carrying `owner:`/`trigger:`, recorded non-conformances the operator chose to keep, scope items re-homed or split. The operator signs the list **verbatim** — an unsigned or hedged acceptance is recorded as not accepted, never inferred.

**2. The two-sum headline per status layer** — the round's rows counted by their highest verified layer (engineered · fixture-verified · staging-verified · live-executed · public · human-completed), so acceptance rests on measured evidence, not assertions.

**3. Status (information only; batch)** — the deferral register at close (OPEN/PARTIAL rows the tail carries forward with owners and triggers), legs whose window extends past this sitting, CI incidents, anomalies, operator-side merges read from GitHub. Nothing to answer here.

## Answers and recording

- **Answers:** `accept` (the list is signed verbatim) · `accept with <lines>` (a line's wording amended in the operator's own words) · `pause`. Silence on the whole packet = pause (OM-18), never consent; hedged words get a yes/no question (OM-09).
- **Recorded by the orchestrator** verbatim with `date -u` in a GATE DECISIONS row and in `docs/build/readouts/GATE-ACCEPT-R11.md`; no proxy signature, no paraphrase (OM-07/08). The signature act is the operator's (HG-14 domain; SIG-SEC-010 posture — operator-signed records).
- **Effects:** the round is accepted as written or the pause is recorded; a PHASE LOG pause/resume entry records the sitting; the LEDGER advances to row 505 only after the answer is recorded; outstanding deferrals carry into the reconcile rows with their owners and triggers intact.

## Load (read these — do not re-read others)

- `docs/build/LEDGER.md` — orient region (CURRENT STATE, OPERATING MODE, RETURN PASS queue) — ~12 KiB
- `docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md` — §13.4 (the acceptance packet and the tail) — ~6 KiB
- `docs/tickets/DEFERRALS.md` — the register the packet reads — ~16 KiB
- `docs/tickets/503_P38.2__round11-gap-closure-and-acceptance-packet.md` — the packet's author contract — ~9 KiB
- `docs/build/readouts/GATE-ACCEPT-R11.md` (P38.2's packet draft) — estimate — ~12 KiB
- `docs/tickets/504_GATE-ACCEPT-R11__round11-acceptance.md` — this contract — ~9 KiB

**Token count (counter `utf8-bytes÷3 | ÷4`, the named proxy of S6R-27):** ≈ 66,000 B → ≈ 22,000 (÷3) · ≈ 16,500 (÷4). Working set (inference): the operator's answer and the records the orchestrator appends — small.

## Acceptance criteria

Each criterion names the BM-STATUS-01 layer it must reach (engineered · fixture-verified · staging-verified · live-executed · public · human-completed); a lower layer reached is reported as that layer, never higher.

- [ ] The packet presented is P38.2's draft (sha256 matches) and every line shows its default; it was not presented while a leg was due. *(deterministic · layer: engineered)*
- [ ] The operator's answer is recorded verbatim with `date -u` in GATE DECISIONS and the readout; the accepted-deviations signature is the operator's verbatim act or is recorded as not given. *(agentic · layer: human-completed)*
- [ ] Records: GATE DECISIONS rows and the readout only gain lines (`python3 docs/build/tools/memory_guard.py all --staged` green before the record commit); the PHASE LOG pause/resume entry written; the LEDGER advanced to row 505 only after the answer. *(deterministic · layer: engineered)*

## Requirement IDs to satisfy and stamp in the PR

- **Owner (spec §56 `Owner:`):** none.
- **Cited (context; owned elsewhere):** SIG-SEC-010 (operator-signed gate records), HG-14 (the acceptance-signature domain).
- **Outreach-owed check (ADR-171):** a gate marker contacts nobody and performs no connector work; the Stage-0 set stays owed — unmet at launch — under `D-R11-LATER-04` (recorded, never implied satisfied). No outside contact (U-011).

## Cross-cutting invariants

- **Defining standard (§3.1):** the packet shows each line's default; nothing is accepted on silence; a recorded default is non-action, never consent.
- **Append-only (P1–P3, AGENTS.md gotcha 5):** GATE DECISIONS and the readout only gain lines; corrections name the sha/line corrected.
- **Round-11 truth rules:** no agent label counts as a human label and no agent signs ("no human check performed"); nobody outside the project is contacted (U-011); the operator's personal e-mail address is never added to a file; dates come from `date -u` or git/GitHub time (OM-04); `db/sqitch.plan` lines 44–52 are never edited or re-stamped (C-10, ADR-146).
- **Additive / back-compat:** prior wire names, ids and schema contracts keep working.

## Operating clauses

OM-07/08/09 (verbatim words, no proxy signature, hedged words get a yes/no question), OM-17 (operator digest with merges read from GitHub), OM-18 (stop and ask; silence is never consent), OM-19 (no GATE while a leg is due) bind the orchestrator here. No branch, PR or CI read belongs to the gate marker itself.

## Notes

- Plan cell, verbatim: `operator signs the accepted-deviations list verbatim (HG-14 domain); never guessed past`.
- The packet this gate reads is authored by P38.2 (row 503) — this marker only records the answer.
- AC rubric: the gate's own lines are the recording checks above — no implementation verdict applies.
- Do not renumber a manifest row; append-only history; a record commit carries the `Harness:` trailer (OM-01).
