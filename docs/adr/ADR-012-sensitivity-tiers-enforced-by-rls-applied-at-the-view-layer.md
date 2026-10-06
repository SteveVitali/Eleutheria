# ADR-012: Sensitivity tiers enforced by RLS, applied at the view layer

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** SIG-GEO-008, SIG-SEC-004, SIG-STORE-024
- **Spec:** docs/2_canonical_design_spec.md §19.4, §44.4

## Context

Coordinate precision and record visibility must degrade by sensitivity class without ever leaking full precision through an aggregate or a mis-scoped query.

## Decision

Enforce sensitivity tiers with restrictive row-level security, and apply coordinate-precision transforms at the view layer; full precision is retained only in canonical storage. Export roles run with row security off so a would-be-filtered export fails loudly.

## Consequences

Precision policy is enforced by the database, not by application discipline; RLS policy tests are CI-blocking. Requires careful role design.

## Alternatives considered

Application-layer filtering only (one missed query leaks); blurring after aggregation (leaks precise values through the aggregate, SIG-GEO-010).

## Revisit trigger

Postgres RLS proves inadequate for a required policy, or the view-layer transform cannot meet query-latency budgets.

### Trigger evaluation — SEED-11 (Round 11 T1, 2026-10-01): LIKELY FIRED

Evaluated at Round-11 Stage B, T1 (unit SEED-11d, 2026-10-01T07:49:22Z) from F3 §5.1
(`docs/build/planning/2026-09-30-next-phase/research/F3-backlog.md`) and the Round-11 plan
(`docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md`); an agent evaluation, not an operator
decision. **The trigger likely fired:** `sig_read_public` has blanket SELECT that reaches
`evidence_access_log` and `review_decision` (J1 NEW-9; F3 §5.1), so the view-layer policy is not what bounds
those reads. **Answer:** row P34.25 (API honesty code: grants) cuts the grants and checks RLS against them;
least-privilege runtime identities are rows P34.42a/b. RLS at the view layer stays the decision. The decision
above stays in force until that answer lands; this ADR's body is unchanged (SIG-ENG-003).
