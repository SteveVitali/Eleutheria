# ADR-183: Express-terms acceptance — the ≈8,088 currently public rows stay public; new non-commercial sources are facts and pointers only

- **Status:** Accepted
- **Date:** 2026-10-01
- **Ticket:** SEED-11 (Round-11 Stage B, T1 — unit SEED-11d)
- **Requirement ids:** SIG-LIC-001, SIG-LIC-002, SIG-LIC-003, SIG-LIC-004, SIG-LIC-011 (applied; none waived); SIG-INGEST-046c (not waived — an open question, see Consequences)
- **Spec:** docs/2_canonical_design_spec.md §42.1 — SIG-LIC-001…004 at lines 6057–6073 (source `docs/research/_meta/spec_src/90_partVIII_s42to43_lic_pub.md`); §23.7 — SIG-INGEST-046c at lines 4285–4290 (source `docs/research/_meta/spec_src/52_partIV_s23to26_connectors_parse.md`); line numbers as built at `71e8bc83`
- **Decision:** the operator's answers to A-8 and A-9, 2026-10-01T04:07:45Z, and to the A-8 wording line, 2026-10-01T04:09:43Z — `docs/build/planning/2026-09-30-next-phase/feedback/RATIFICATION_LOG.md`, rounds 4 and 5
- **Plan:** `docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md` §4.2 (A-8, A-9), §4.6, §5.5 ("Express terms"), §6.5 ("not waived" list), §7 row 183, §13.5, §14 R-19
- **Related:** ADR-169 (rights basis with guardrails: GL-GATE-07 re-confirmed), ADR-182 (WV-07: counsel clauses waived), ADR-161 (release model v2: 15-minute withdrawal); J4 NEW-1, I7-C1, I7-C6
- **Recorded:** 2026-10-01T07:45:36Z (`date -u`) by Claude Code (Opus 5.5), Stage-B sub-agent SEED-11d. Everything in this record except the quoted operator words is agent-drafted.

## Context

J4 found 5,267 public rows whose own captured terms forbid redistribution, are non-commercial (NC) or no-derivatives
(ND), or call the data a "demo" (J4 NEW-1), plus ≈2,821 rows of `camreg_txdot_rep_tx`, a republish of TxDOT camera
points whose origin terms say "distribution to third parties without TxDOT's written consent is strictly prohibited"
(I7-C1). GL-GATE-07 had accepted database-right risk, not express prohibitions. Three of the live rows carry NC
licences (Keizer, TRPA CC BY-NC, Cal OES NC-ND; I7-C6). The packet recommended withdrawing all ≈8,088 rows (A-8) and
asked whether SIG's use is non-commercial (A-9).

## Decision

### The operator's words

- **A-8, verbatim:** "Keep all, accept risk" — round 4, 2026-10-01T04:07:45Z (chosen over the recommendation to
  withdraw all ≈8,088 rows).
- **A-8 wording line, verbatim:** "Keep everything as is" — round 5, 2026-10-01T04:09:43Z (chosen over "Keep; NC rows
  facts-only").
- **Adopted sentence — agent-drafted, adopted by the operator at 2026-10-01T04:09:43Z:**

  > I accept the express-terms risk for all ≈8,088 currently public rows, including the non-commercial ones; A-9 applies to new sources only.

  sha256 `cd76b74e872db8dcc118c0cda0355fa505524a7bc8730e5f21df23be171f2fb4` (`printf '%s' "<sentence>" | shasum -a 256`,
  recomputed by SEED-11d; equals S6's value, `design/S6-ratification-applied.md` §5).
- **A-9, verbatim (a selected option label, not an own-words sentence):** "May be commercial (Recommended)" — round 4,
  2026-10-01T04:07:45Z; sha256 of the label `9ea4affaed2e9fafcd14ac427b25a5151e2a9757d07986a5b27ff77743d295ed`
  (computed by SEED-11d).

### What is decided

1. **No withdrawal.** The ≈8,088 rows public on 2026-10-01 — the 5,267 J4 NEW-1 rows and ≈2,821 `camreg_txdot_rep_tx`
   rows, including the 3 live NC rows — stay public. There is no TxDOT restriction (I7-C1's option b is not adopted)
   and no facts-only re-shaping of the NC rows.
2. **SIG's use is or may be commercial (A-9).** Any **new** source whose terms carry a non-commercial clause contributes
   facts and pointers only — cited, never re-hosted (E4-R4d declined; I7-IT2/IT3/IT5/IT6 facts-only pointers).
3. **This is a recorded risk acceptance, not a waiver.** No spec MUST is weakened: the rights records, archived terms
   and computed export licences still apply (SIG-LIC-001…004, SIG-LIC-011). The counsel clause that would otherwise
   apply to these rights decisions is waived separately (WV-07, ADR-182).

### Disclosure and remedies (the controls that make the acceptance honest)

1. **Disclosure instead of withdrawal.** Row **P34.19** shows, for each affected source, the captured terms verbatim and
   the operator-accepted basis on its rights record, source page and list entry, and in the file-level rights records of
   the exports (copy via copy batch #1, B-2; publication rides P34.17 and P34.21b).
2. **Withdrawal on objection.** A rights-holder objection or takedown withdraws the source through the withdrawal
   barrier (P34.41; the 15-minute technical withdrawal, D-G3-9, ADR-161), by a new claim, never by an edit.
3. **The 046c check.** Row **P36.1a** classifies the captured licence metadata of these rows; any that is an affirmative
   machine-readable rights reservation under SIG-INGEST-046c (not waived) goes back to the operator (plan §14 R-19).
4. **Outside the acceptance.** The 9 leak-derived Atlas FR rows (F-337) are still withdrawn — they are not an A-8 row —
   and the `demo_*` task pages are still stripped (C-12).
5. **Announcement.** GATE-ANNOUNCE checks that the express-terms rows are disclosed with their captured terms and the
   operator-accepted basis (plan §13.5).

## Consequences

- The publishers' own terms say SIG may not do what it is doing for these rows; the exposure is breach-of-terms or
  database-right claims (plan §14 R-19). The operator accepted it in the words above.
- **Open, not decided here:** (a) whether any row's captured licence metadata is itself a machine-readable reservation
  under SIG-INGEST-046c — then 046c requires refusal regardless of this acceptance (P36.1a returns it to the operator;
  R-19); (b) the sentence names "currently public rows"; whether rows later re-ingested from these same sources are
  covered is not stated, and is put to the operator if a refresh would publish new rows from them.
- T4 records the risk row (R-19) and a BACKLOG revisit row; SEED-15's `ADR_TRIGGERS.csv` carries this trigger.

## Alternatives considered

- **Withdraw all ≈8,088 rows (the recommendation)**, or **withdraw the 5,267 and keep TxDOT**. Not chosen.
- **Keep the rows but make the NC rows facts-only (the A-8 wording recommendation).** Not chosen ("Keep everything as
  is").
- **A-9 "Non-commercial".** Would have allowed NC sources to flip into an NC compartment with download gating; not
  chosen.

## Revisit trigger

Revisit — by a new ADR — when any of these happens:

- a rights holder objects or sends a takedown for any of these sources (withdraw first, then revisit);
- a source's captured terms change, or P36.1a classifies a row's metadata as an affirmative reservation (SIG-INGEST-046c);
- a refresh would publish rows from these sources that were not public on 2026-10-01;
- a first legal demand arrives, or the operator obtains counsel (LATER-05).
