# ADR-150: Coverage verdict vocabulary

- **Status:** Accepted
- **Date:** 2026-10-01T05:03:05Z (decided by the operator at GATE-P — the latest of this ADR's lines, C-13, log rounds 22–23)
- **Phase:** Round 11 / Stage B seed (T1)
- **Ticket:** SEED-11 (unit SEED-11a)
- **Implemented by:** SEED-14 (re-verdicts) and SEED-15 (checker) at T4, then P34.33 (two-sum headline) and P34.48
  (boilerplate re-verdicts)
- **Decided by:** the operator at GATE-P (`PD/feedback/RATIFICATION_LOG.md`; `PD` = `docs/build/planning/2026-09-30-next-phase/`):
  - **B-5** (in the BT batch B-5, B-17, B-22, B-23, B-26), round 11 (2026-10-01T04:33:54Z): **"Accept all five
    (Recommended)"** — the line as presented: *"Verdict vocabulary (MET · MET-DIFFERENTLY(ADR) · MET-ENGINEERED · PARTIAL
    · MISSING · AT-RISK-INTEGRATION · WAIVED(ADR) · N/A-RATIONALE), the +4 matrix columns, and re-verdicts of scoped and
    boilerplate rows"* (`PD/feedback/RATIFICATION_ANSWERS.md`); member Q-E2-17 = a ("adopt the vocabulary + re-verdict").
  - **C-13**, rounds 22–23 (2026-10-01T05:03:05Z): **"Superseded (Recommended)"** — OD-29: ACCEPT-R10's "34 MET" stands as
    history, superseded by the Round-11 re-verdicts; recorded with its own time, never as a 2026-09-27/28 statement.
- **Requirement ids:** **SIG-ENG-041** "verdict integrity" and
  **SIG-ENG-042** "validator gates" (§56.3; drafted in B4 §5; final ids per `PD/stageB/T1_id_map.csv`); the Round-11 amendment of SIG-ENG-031 (Appendix G.7 R11-A16) (the coverage matrix is the traceability matrix, reflected through
  assessment events); SIG-MEM-002 (requirement assessments derived from evidence-backed transitions); SIG-ENG-005 (the
  risk-register route for requirements that cannot be verified automatically).
- **Spec:** §0.6 (SIG-ENG-005), §51.3 (SIG-ENG-031, amended per Appendix G.7 R11-A16), §55.7 (SIG-MEM-002); Part XII
  §56.3 (SIG-ENG-041, SIG-ENG-042); `docs/build/COVERAGE_MATRIX.csv` (vocabulary and columns, SEED-14/15).
- **Supersedes:** none — no landed ADR (plan §7, row 150). It supersedes a record, not a decision: ACCEPT-R10's
  "34 MET" headline (C-13).
- **Amends / qualifies / extends:** extends the `coverage-assessment/1` use of ADR-126 — every verdict change becomes an
  event and the matrix becomes the projection of the event heads — *(agent interpretation, labelled; §7 names no status
  line for ADR-126 on this account)*.
- **Sources:** plan §2.1, §6.4, §6.5 (first paragraph), §6.6, §7 (row 150), §13.1–§13.2, Appendix A (T4); `PD/research/F2b-verdicts.md`
  §1, §2.1–§2.6; `PD/design/B4-verification.md` G7 and §5; `PD/reviews/S4-truth-safety.md` TS-05 and
  `PD/reviews/REVIEW_CLOSURE.md` (TS-05 closure); `PD/data/decision_catalog.csv` (Q-E2-17, OD-29);
  `docs/build/tools/check_coverage_matrix.py` (current enum, line 43); landed ADR-126 (`coverage-assessment/1`).
- **Recorded:** 2026-10-01T07:42:36Z by Claude Code (Opus 5.5), harness `claude-code/claude-opus-5-5/subagent` — an
  agent-drafted record of the operator's decisions; the operator's words are quoted verbatim from the log.

## Context

The coverage matrix (715 rows) answered "is it built?" and "is it done?" with one word. "Closed P32.25 … NO production
serve" was recorded `MET`; the Round-10 capstone headline "34 MET" (CAPSTONE_CLOSURE §(f1)), accepted at ACCEPT-R10,
counted fixture-verified machinery as requirement satisfaction (F-16; E1 NEW-8; A3 NEW-1: 17 MET rows cite an owed
deferral). `check_coverage_matrix.py` knows six verdicts (`MET`, `MET-DIFFERENTLY`, `PARTIAL`, `MISSING`,
`AT-RISK-INTEGRATION`, `N/A-RATIONALE`), checks structure only, and runs in no gate (F2b NEW-4). Seventy-five
`MET-DIFFERENTLY` rows rest on boilerplate rather than an ADR or risk row.

F2b re-examined the 55 gated or reduced-scope ids: of 19 MET rows only 2 survive as MET; 12 become MET-ENGINEERED, and the
rest split across PARTIAL, AT-RISK-INTEGRATION and WAIVED (F2b §1). The same review found that spec amendments which
weakened a MUST had been classed as "spec amendments", invisible to the waiver checks (S4 TS-05). At GATE-P and in log
rounds 24 and 26 the operator then waived a MUST or a named clause twelve times in adopted words (A-6; WV-01…WV-11),
which needs a verdict that is neither MET nor owed.

## Decision

1. **Eight verdicts** (F2b §2.2; plan §6.4). Each answers one question — *does the landed and operated system satisfy the
   requirement text as written, at the evidence domain the text demands, with no human or live leg still owed?*

   | verdict | meaning | entry (all required) |
   |---|---|---|
   | `MET` | every clause satisfied at its required domain | evidence per clause; `achieved_domain ≥ required_domain`; no OPEN/PARTIAL D-row is a leg; no surface contradicts it |
   | `MET-DIFFERENTLY(ADR-nnn \| RISK-id)` | the intent met by another mechanism | an accepted ADR naming the id and the evidenced alternative, or (only for a requirement that cannot be verified automatically) a SIG-ENG-005 risk row with its compensating control; never a prefix default, bulk signature or boilerplate |
   | **`MET-ENGINEERED(D-id…)`** (new) | all engineering built and verified at ≥ `implementation`; only live, operator or human acts remain | the owed acts named in ≥ 1 OPEN/PARTIAL DEFERRALS row; the shipped engineering can perform the leg without new code; no surface claims the leg happened |
   | `PARTIAL` | some clauses unbuilt, or a public surface or record contradicts the requirement | exactly one live home |
   | `MISSING` | no conforming implementation | exactly one live home |
   | `AT-RISK-INTEGRATION` | a conforming, tested component the operated path does not use | an integration ticket as home (plus the D-row if a human act is also needed) |
   | **`WAIVED(ADR-nnn)`** (new) | the operator decided the requirement, or a named clause, will not be met for a stated scope or period | an accepted ADR with the operator's words verbatim, the risk accepted, compensating controls and a `## Revisit trigger`; a `spec_src` waiver note; no surface claims the waived property; a WONTFIX D-row or a skipped gate alone is never a waiver |
   | `N/A-RATIONALE` | a rationale statement with no build obligation | unchanged |

   Exits follow F2b §2.2: MET-ENGINEERED rises to MET only when every cited D-row is DONE at the required domain and falls
   to PARTIAL if a surface claims the leg happened; WAIVED is re-verdicted when its revisit trigger fires.
2. **Four additive matrix columns:** `required_domain` (fixture · implementation · composed-db · hosted · public, plus a
   `+human` flag), `achieved_domain`, `owed_legs` (D-ids) and `accepted_scope` (`<readout>@<date>#<clause>`).
3. **Register mapping** (F2b §2.3): MET allows no OPEN/PARTIAL row naming the id as a leg; MET-ENGINEERED requires one,
   and that row names the SIG id back; WAIVED leaves any prior D-row WONTFIX citing the ADR plus one BACKLOG row for the
   revisit trigger; PARTIAL, MISSING and AT-RISK-INTEGRATION may home in DEFERRALS or BACKLOG, never on a landed ticket.
4. **The checker enforces it.** `check_coverage_matrix.py` (SEED-15, T4) parses the grammar and its parameters
   (MET-DIFFERENTLY's ADR or RISK row exists and names the id; WAIVED's ADR is accepted, contains the id and a revisit
   trigger; MET-ENGINEERED has non-empty `owed_legs`) and cross-checks the obligation register's event heads: no MET with
   an owed leg; MET-ENGINEERED only with an open leg; WAIVED only with an accepted ADR and no open leg; routing to a
   landed ticket is an error; cited evidence must exist; `achieved_domain < required_domain` under MET is an error;
   expected counts derive from the spec — no pinned 715. It runs in `make docs-check` and the CI `docs` job (G7;
   SEED-02 wiring).
5. **Every verdict change is a `coverage-assessment/1` event** with its domain (ADR-126's schema); the matrix verdict is
   the projection of the event heads, so the event layer and the CSV cannot disagree.
6. **A scoped operator acceptance is an authorization to act, never a verdict** (F2b §2.5). It is recorded in
   `accepted_scope`; every clause it scoped out stays an OPEN D-row; the verdict is at most MET-ENGINEERED. Turning a
   scoped-out clause into a waiver takes a WAIVED(ADR) in the operator's words.
7. **An amendment that weakens a MUST is a waiver.** A spec amendment that removes or weakens a MUST is recorded as
   WAIVED(ADR) — the operator's words, compensating controls, revisit trigger — or the obligation stays owed with a
   trigger; T4 adds the rule to the S1b checker (`tools/check_dispositions.py`) and to `check_coverage_matrix.py`
   (plan §6.5; S4 TS-05).
8. **Headlines report two sums per status layer, never "N MET" alone** (P34.33, the R11-MEM-10 contract; P38.1a/b):
   *engineering closed* = MET + MET-DIFFERENTLY + MET-ENGINEERED; *requirement satisfied* = MET + MET-DIFFERENTLY;
   WAIVED rows listed with their ADRs; no public page presents a MET-ENGINEERED or WAIVED property as achieved; a
   publication gate lists the MET-ENGINEERED rows it scopes out.
9. **ACCEPT-R10's "34 MET" is superseded** by the re-verdicts (C-13) and stands as history; ACCEPT-R10's acceptance of the
   honest scope state ("production exposure OPEN … the S3 spine deferred … intake non-operational") is exactly what
   MET-ENGINEERED now expresses (F2b §2.4).
10. **Re-verdicts** (plan §6.6; applied by SEED-14 at T4, each as an event): the F2b deltas (12 MET → MET-ENGINEERED, the
    14 MET-ENGINEERED needing their D-rows opened first), the F2a deltas, the L3 deltas (ADR-152…154), and WAIVED(ADR)
    for every MUST or clause waived at GATE-P and in rounds 24 and 26 (SIG-EVAL-004 for C0–C2 → ADR-153; WV-01…WV-11 →
    ADR-163…165, 179…182, 186…189, each with its `accepted_scope`). The 61 unsampled boilerplate MET-DIFFERENTLY rows are
    re-verdicted row by row in P34.48.

## Consequences

- Headline numbers fall: most MET rows in the gated half become MET-ENGINEERED or PARTIAL. The fall is in the record,
  not in the system; the two-sum headline shows both what is built and what is satisfied.
- Owed live and human legs become visible per requirement through `owed_legs`, and a public surface that claims an owed
  leg demotes the row automatically.
- Waivers become first-class and auditable: each WAIVED row resolves to an ADR with the operator's words and a revisit
  trigger, and `ADR_TRIGGERS.csv` (SEED-15) carries one row per waiver trigger.
- The matrix gains four columns (back-compatible) and a validator that can fail a PR; T4 must open the missing D-rows
  before it may write MET-ENGINEERED.
- ACCEPT-R10 is not overturned as a record of what was accepted; only its count is superseded.

## Alternatives considered

- **Redefine MET to include scoped acceptance** (Q-E2-17 b): rejected — it is the F-16 failure written into the
  vocabulary; a signature would raise a verdict.
- **Keep the six verdicts and annotate:** rejected — annotations do not reach the checker or the headline, and owed legs
  stay invisible to cross-checks.
- **Treat a WONTFIX D-row or a skipped gate as a waiver:** rejected — no operator words, no compensating controls, no
  trigger (F2b §2.2).
- **Leave weakening spec amendments as "spec amendments":** rejected (TS-05) — it hides waived MUSTs from the
  announce-gate list and the checker.

## Revisit trigger

- A verdict outside the eight is needed, or a WAIVED or MET-ENGINEERED row's entry rule cannot be checked mechanically.
- The checker reports 0 items evaluated on a non-empty matrix, or is removed from `make docs-check` or CI.
- Any public surface, readout or acceptance packet reports "N MET" without the two-sum headline, or presents a
  MET-ENGINEERED or WAIVED property as achieved.
- A waiver's revisit trigger fires (re-verdict that row), or the operator reverses a waiver (the row returns to PARTIAL
  or MISSING with a home).
- P34.48's re-verdict of the boilerplate rows finds a class of row the vocabulary does not fit.
