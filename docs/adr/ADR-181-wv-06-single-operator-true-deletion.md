# ADR-181: WV-06 — single-operator true deletion (SIG-GOV-008's two-person clause waived; its scope and tombstone clauses stand)

- **Status:** Accepted
- **Date:** 2026-10-01
- **Ticket:** SEED-11 (Round-11 Stage B, T1 — unit SEED-11d)
- **Requirement ids:** SIG-GOV-008 (two-person-authorization clause WAIVED; scope and tombstone clauses stand); related SIG-GOV-007, SIG-GOV-009, SIG-STORE-011 (ADR-189)
- **Spec:** docs/2_canonical_design_spec.md §45.4 — SIG-GOV-008 at lines 6497–6499 (as built at `71e8bc83`; source `docs/research/_meta/spec_src/91_partVIII_s44to46_sec_gov.md`)
- **Decision:** the operator's answer to A-23 part 2 (waiver candidate WV-06), 2026-10-01T04:28:49Z, and to S6R-03, 2026-10-01T06:51:11Z — `docs/build/planning/2026-09-30-next-phase/feedback/RATIFICATION_LOG.md`, rounds 9 and 26
- **Plan:** `docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md` §4.6, §4.9 (S6R-03), §5.10, §6.3 (SIG-GOV-008 row), §6.5 (WV-06 row), §7 row 181, §14 R-22/R-32
- **Related:** ADR-189 (WV-11: the one operator-only purge function — this ADR's only claim-row mechanism), ADR-164 (WV-02: public decision log), ADR-177 (evidence retention, 365 days unlocked), ADR-006 / ADR-023 (OCFL evidence store, governance-mode Object Lock), ADR-002 (append-only claim table)
- **Recorded:** 2026-10-01T07:45:36Z (`date -u`) by Claude Code (Opus 5.5), Stage-B sub-agent SEED-11d. Everything in this record except the quoted operator words is agent-drafted.

## Context

SIG-GOV-008 reserves true deletion for material SIG must not hold at all, requires two-person authorization, and
requires a tombstone. Round 11 has one human (Q-8), so the two-person clause cannot be met, and without a waiver no
true deletion could happen — only suppression (SIG-GOV-007) and withdrawal. The packet offered WV-06 with the
recommendation to keep it owed ("then no true deletion happens; withdrawal only"); the operator waived it instead.
S6r later found (S6R-03) that the plan had dropped GOV-008's scope clause and that a claim-row deletion would collide
with SIG-STORE-011; round 26 settled that with a narrow purge exception (WV-11, ADR-189).

## Decision

### The operator's words

- **Answer to A-23 part 2 (multi-select; a tick waives), verbatim:** "WV-04 hostile-reader block (Recommended), WV-05
  anonymous intake (Recommended), WV-06 two-person deletion" — round 9, 2026-10-01T04:28:49Z. WV-06 was chosen over the
  recommendation (keep owed).
- **Adopted sentence — agent-drafted, adopted by the operator at 2026-10-01T04:28:49Z:**

  > I waive two-person authorisation for true deletion (SIG-GOV-008): I alone may authorise a deletion, publicly logged with its reason.

  sha256 `dbf7a851e9d51312f2e8b53d43d30c85b0e3640a8e0ef67d8bc1519ed3e3966c` (`printf '%s' "<sentence>" | shasum -a 256`,
  recomputed by SEED-11d; equals S6's value, `design/S6-ratification-applied.md` §5).
- **Answer to S6R-03, verbatim:** "Narrow purge exception (Recommended)" — round 26, 2026-10-01T06:51:11Z; its adopted
  sentence is recorded in ADR-189.

### The requirement and the clause waived

> **SIG-GOV-008 (MUST).** True deletion MUST be reserved for material SIG must not hold at all, MUST
> require two-person authorization, and MUST leave a tombstone recording that a deletion occurred,
> its category, and its date — never its content.

— `docs/2_canonical_design_spec.md:6497-6499`

- **Waived:** "MUST require two-person authorization" (line 6498). The operator alone may authorise a true deletion.
- **Stand, unchanged:** the scope clause ("reserved for material SIG must not hold at all") and the tombstone clause
  ("a tombstone recording that a deletion occurred, its category, and its date — never its content"). Suppression
  (SIG-GOV-007, sealed tier) stays the primitive for everything outside that scope.

### Scope

Every true deletion while this ADR stands — of evidence bytes, derived artifacts or, through ADR-189's purge function
only, claim rows. No round limit was stated in the sentence. The coverage verdict is `WAIVED(ADR-181)` for the
two-person clause, with the scope and tombstone clauses recorded as standing in `accepted_scope` (T4, SEED-14).

### Compensating controls

1. **Design first, mechanism ticketed.** Row **P37.71** writes the design note and builds the deletion path; it executes
   no deletion itself. The design states how a governance-mode delete keeps the audit record, reconciling the 365-day
   unlocked evidence retention (B-14, ADR-177, P37.3) and the OCFL write-once store (ADR-023).
2. **Scope enforced.** A deletion is only for material SIG must not hold at all (e.g. SIG-PUB-002 material the Part VIII
   at-rest audit P34.49 seals and lists, counts only, for the operator's decision). Everything else is suppressed, not
   deleted.
3. **The operator's go, every time.** Each deletion needs the operator's in-ticket go naming the material. It is never
   on an OM-20 pre-authorisation list and never initiated or run by an agent without that go (log round 9 labelled
   interpretation; plan §5.10).
4. **Public log and tombstone.** Each deletion is logged publicly with its reason in the editorial decision log (P37.7,
   ADR-164) and leaves a tombstone of category and date, never content.
5. **Audit record kept.** The mechanism keeps an internal audit record of the authorisation and the act (log round 9
   interpretation; P37.71).
6. **Claim rows only through ADR-189.** A claim row can be removed only by the one DB-enforced, operator-only purge
   function of ADR-189; every other path to the claim table stays insert-only (SIG-STORE-011).

## Consequences

- One person can remove material permanently. Misuse or error is mitigated by the public log, the tombstone, the
  narrow scope and the per-use go, not by a second person. The risk is plan §14 R-22 and, for claim rows, R-32.
- The 365-day unlocked retention (ADR-177) keeps this deletion technically possible; Object Lock stays governance mode
  (SIG-GOV-009).
- T4 records the verdict and a BACKLOG revisit row; SEED-15's `ADR_TRIGGERS.csv` carries this trigger.

## Alternatives considered

- **Keep SIG-GOV-008 owed (the recommendation).** No true deletion this round; suppression and withdrawal only. Not
  chosen.
- **No spine deletion (S6R-03 option b).** P37.71 would remove evidence bytes and derived artifacts only, with claims
  withheld by disposition. Not chosen; the narrow purge exception was (ADR-189).

## Revisit trigger

Revisit — by a new ADR — when any of these happens:

- a second maintainer joins (restore two-person authorisation);
- a deletion is contested, publicly or by the subject or source;
- a deletion is requested for material outside GOV-008's scope (that is a scope change, never an expansion by use).
