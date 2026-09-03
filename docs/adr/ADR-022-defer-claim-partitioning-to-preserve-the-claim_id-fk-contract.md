# ADR-022: Defer physical partitioning of `claim` to preserve the `claim_id` FK contract

- **Status:** Accepted
- **Date:** 2026-08-27
- **Phase:** P02.1
- **Requirement ids:** SIG-STORE-008, SIG-STORE-010, SIG-STORE-011
- **Spec:** docs/2_canonical_design_spec.md §16.2 (design point 6)

## Context

§16.2 gives the `claim` DDL with two properties that PostgreSQL cannot satisfy
simultaneously:

1. `claim_id uuid PRIMARY KEY` — a single-column primary key. `claim_id` MUST be a
   single-column key because it is the universal foreign-key target: `claim_evidence`,
   `resolution.winning_claim`, `claim.revises_claim`/`retraction_of` (self-references),
   `person.public_interest_basis_claim`, `entity_identifier.asserted_by_claim`,
   `relationship.evidence_claim`, and others all reference `claim(claim_id)`.
2. `PARTITION BY RANGE (observed_at)` (design point 6) — physical partitioning by
   observation time.

PostgreSQL requires the partition key to be a member of every unique constraint
(including the primary key) on a partitioned table. `observed_at` is deliberately
**nullable** (§16.2 design point 4 — forcing a timestamp would manufacture T2 out
of T3/T4, forbidden by SIG-TIME-002), so it cannot join a primary key. Therefore a
table partitioned by `observed_at` cannot carry `PRIMARY KEY (claim_id)`, and a
composite `PRIMARY KEY (claim_id, observed_at)` would (a) require `observed_at NOT
NULL` and (b) break every single-column FK reference above.

The two requirements are individually normative and jointly infeasible in vanilla
PostgreSQL 18.

## Decision

Retain the **foreign-key contract**: `claim_id uuid PRIMARY KEY DEFAULT uuidv7()`,
unpartitioned, in P02.1. Defer physical partitioning of `claim` to a later,
partition-compatible design (e.g. a composite-key scheme with no cross-partition
single-column FKs, or moving inbound references onto a routing table) introduced as
its own sqitch change when query-latency budgets require it.

The FK contract is what this ticket **owns** and what every downstream ticket
depends on; partitioning is a physical performance concern that carries **no
acceptance criterion** in P02.1. All the epistemic invariants the section cares
about — append-only enforcement, corrections, the resolution non-overlap exclusion
constraint, and RLS — are unaffected and are implemented and tested here.

## Consequences

`claim` starts as a single (large) table. Index locality is preserved by the
UUIDv7 primary key (time-ordered) and the `(subject_id, predicate_id, observed_at)`
index, so the absence of partitions is not a correctness problem and is unlikely to
bind before national scale. Introducing partitioning later is a schema migration
that must also settle the inbound-FK strategy, and will itself warrant an ADR
(SIG-STORE-042). Until then, very large-table maintenance operations (bulk vacuum,
retention drops) run table-wide rather than per-partition.

## Alternatives considered

- **Composite PK `(claim_id, observed_at)` + partitioning now.** Requires
  `observed_at NOT NULL` (violates §16.2 design point 4 / SIG-TIME-002) and breaks
  all single-column FKs to `claim`. Rejected.
- **Partition by `sys_period` lower bound instead.** §16.2 design point 6 explicitly
  argues against partitioning by transaction time; queries filter on observation
  time. Rejected as a silent redesign of a spec decision.
- **Drop the inbound FKs and enforce referential integrity in application code.**
  Discards exactly the database-enforced integrity the claim spine exists to
  provide. Rejected.

## Revisit trigger

`claim` growth or query-latency measurements show table-wide maintenance or
scan cost exceeding budget despite projection and indexing, at which point a
partition-compatible FK strategy is designed and this decision is superseded by a
new ADR plus a sqitch migration.
