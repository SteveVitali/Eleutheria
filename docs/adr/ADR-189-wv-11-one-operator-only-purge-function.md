# ADR-189: WV-11 — one operator-only purge function, the sole exception to SIG-STORE-011

- **Status:** Accepted
- **Date:** 2026-10-01
- **Ticket:** SEED-11 (Round-11 Stage B, T1 — unit SEED-11d)
- **Requirement ids:** SIG-STORE-011 (WAIVED for one operator-only purge function only; every other role and path stays append-only); SIG-GOV-008 (its scope and tombstone clauses bind the function; its two-person clause is waived by ADR-181); SIG-GOV-007
- **Spec:** docs/2_canonical_design_spec.md §16.3 — SIG-STORE-011 at lines 2822–2823 and the `claim_append_only()` trigger sketch that follows (source `docs/research/_meta/spec_src/41_partIII_s16_schema.md`); §45.4 — SIG-GOV-008 at lines 6497–6499 (source `91_partVIII_s44to46_sec_gov.md`); line numbers as built at `71e8bc83`
- **Decision:** the operator's answer to S6R-03 (waiver WV-11), 2026-10-01T06:51:11Z — `docs/build/planning/2026-09-30-next-phase/feedback/RATIFICATION_LOG.md`, round 26
- **Plan:** `docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md` §4.9 (S6R-03), §5.10, §6.3 (SIG-STORE-011 row), §6.5 (WV-11 row), §7 row 189, §14 R-32
- **Related:** ADR-181 (WV-06: single-operator true deletion — this function is its only claim-row mechanism), ADR-002 (append-only claim table), ADR-164 (public decision log), ADR-185 (P34.49's sealed SIG-PUB-002 material); `db/deploy/claim_append_only.sql`; root `AGENTS.md` gotcha 5
- **Recorded:** 2026-10-01T07:45:36Z (`date -u`) by Claude Code (Opus 5.5), Stage-B sub-agent SEED-11d. Everything in this record except the quoted operator words is agent-drafted.

## Context

WV-06 (ADR-181) lets the operator alone authorise a true deletion. S6r found (S6R-03) that the planned deletion path
(P37.71) would be an exception to SIG-STORE-011 — the claim table is append-only, enforced in the database by the
`claim_append_only()` trigger, which raises on every DELETE — and that the plan had dropped SIG-GOV-008's scope clause.
A claim-row deletion therefore needed its own narrow, explicit waiver. The operator was offered a narrow purge exception
(recommended) or no spine deletion at all.

## Decision

### The operator's words

- **Answer to S6R-03, verbatim:** "Narrow purge exception (Recommended)" — round 26, 2026-10-01T06:51:11Z.
- **Adopted sentence — agent-drafted, adopted by the operator at 2026-10-01T06:51:11Z:**

  > I approve one operator-only purge function as the sole exception to SIG-STORE-011, limited to material SIG must not hold (GOV-008), leaving a tombstone and a public log entry.

  sha256 `04e7b77f8db7b2396dcca7241cf3597fe1a04e2f10ced3493c3b6d1accbe19b1` (`printf '%s' "<sentence>" | shasum -a 256`,
  recomputed by SEED-11d; equals the value S6c recorded in plan §4.9).

### The requirement and the clause waived

> **SIG-STORE-011 (MUST).** The claim table MUST be append-only, enforced in the database, not by
> convention. *(REQ-R6-02.)*

— `docs/2_canonical_design_spec.md:2822-2823`

- **Waived:** append-only, for exactly one database function — the purge function below — and for no other role, path
  or mechanism.
- **Stands for everything else:** the claim table stays append-only, enforced in the database, for every other role and
  path; corrections stay new claims (SIG-GOV-005); suppression (SIG-GOV-007, sealed tier) stays the primitive for all
  material outside SIG-GOV-008's scope.

### The purge function (built by row P37.71)

1. **One function, DB-enforced, operator-only.** A single database function, executable only by an operator-held role,
   added by a **new** sqitch change with deploy, revert and verify scripts; no landed sqitch change is edited (the
   append-only migration discipline).
2. **Every other path still raises.** The `claim_append_only()` trigger continues to raise for every other role and
   path, and a test proves that UPDATE/DELETE from any other role or path still fails.
3. **Scope = SIG-GOV-008.** Only material SIG must not hold at all (for example SIG-PUB-002 material that P34.49 sealed
   and listed for the operator's decision).
4. **Tombstone and public log.** Each use leaves a tombstone recording that a deletion occurred, its category and its
   date — never its content — and a public decision-log entry with its reason (P37.7, ADR-164).
5. **Never pre-authorised.** The function is never on an OM-20 list; each use needs the operator's in-ticket go naming
   the material; its hosted deploy is itself a never-pre-authorised go.
6. **Named in the agent guidance.** P37.71 updates root `AGENTS.md` gotcha 5 and its Forbidden line, and the `db/` docs,
   to name this function as the sole exception to the insert-only rule. Until P37.71 lands nothing changes: today no
   update/delete path to the claim table exists.

### Scope

The claim table, through this one function only. Coverage: `WAIVED(ADR-189)` for SIG-STORE-011, with `accepted_scope`
naming the function; every other path stays MET (T4, SEED-14).

## Consequences

- A delete path exists in the claim spine. Misuse or a defect could remove evidence the record needs; this is plan §14
  R-32, mitigated by the operator-only role, the scope, the tombstone, the public log and the per-use go.
- The design must settle how rows that reference a purged claim (`claim_id` foreign keys, derived and resolution rows)
  are handled without breaking the claim-spine contracts (agent note for P37.71's design; not decided here).
- ADR-002's decision (claims are append-only) now has one recorded exception. §7 of the plan assigns no status line to
  ADR-002, so none is appended to it by T1.
- T4 records the verdict and a BACKLOG revisit row; SEED-15's `ADR_TRIGGERS.csv` carries this trigger.

## Alternatives considered

- **No spine deletion (option b).** P37.71 would remove evidence bytes and derived artifacts only; claims would be
  withheld by disposition. Not chosen.
- **A general delete permission or a second purge path.** Not offered and not decided; any such request is a revisit
  trigger.

## Revisit trigger

Revisit — by a new ADR — when any of these happens:

- any use of the function (each use is reviewed against this ADR in its decision-log entry);
- a request to widen its scope or to add a second purge path;
- a second maintainer joins (two-person authorisation, WV-06's trigger);
- a deletion is contested.
