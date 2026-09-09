# ADR-060: The resolver (P08.1) — retro-fitted record

- **Status:** Accepted
- **Date:** 2026-09-09
- **Phase:** P08.1 (retro-fitted by P19.5)
- **Requirement ids:** SIG-RECON-004, SIG-RECON-005, SIG-RECON-006, SIG-RECON-007, SIG-RECON-008, SIG-RECON-010, SIG-RECON-011, SIG-RECON-012, SIG-RECON-013, SIG-RECON-014, SIG-RECON-015, SIG-RECON-016, SIG-RECON-017, SIG-RECON-018, SIG-RECON-020, SIG-RECON-021, SIG-RECON-022, SIG-RECON-023, SIG-RECON-024, SIG-RECON-025, SIG-EPIS-014, SIG-EPIS-017, SIG-EPIS-018, SIG-EPIS-019, SIG-EPIS-020, SIG-EPIS-023, SIG-EPIS-025, SIG-EPIS-026, SIG-EPIS-027, SIG-EPIS-028, SIG-STORE-014

## Context

P08.1 built the reconciliation resolver — the intellectual core of the project (§28): a
deterministic, rule-based `RESOLVE(subject, predicate, as_of_world, as_of_belief, ruleset)` running a
fixed Phase 0–7 pipeline over one subject/predicate pair (gather → admissibility → canonicalize →
weight → independence → strategy → ambiguity → emit). It shipped as a **purely additive** change
(seven new files under `reconcile/`, PR #20) and was verified end-to-end — 57 reconcile tests, the
repo-wide suite green — but it shipped with **no ADR and no §53 risk-register section** (recorded by
the capstone gap analysis as LD-X05 / orphaned seam O7). This ADR retro-fits the decision record so
the resolver's load-bearing choices are documented where every other phase's are, without changing a
line of the shipped code (append-only, P1–P3).

This is a **record**, not a new decision: it states the design P08.1 already implemented and P08.2/
P08.3/P12/P14 already consume. Its companion is the new `## Phase 8 — Resolver (P08.1)` risk-register
section (RISK-P8-00a ruleset-as-data drift; RISK-P8-00b rationale quotability), added by P19.5.

## Decision (as built in P08.1)

1. **Determinism with no random tie-break anywhere (SIG-RECON-007).** The candidate order is
   `(match_weight desc, method_breadth desc, observed_at desc, source_registry_rank asc, claim_id asc)`;
   `claim_id` makes the order **total**, so identical inputs are byte-reproducible (`decision_key()` /
   `input_digest` exclude `computed_at`). Recency is neutralised for IMMUTABLE/GLACIAL predicates
   (SIG-RECON-010) in both candidate ranking and representative selection.

2. **Contradictions stay visible; nothing collapses to a single number (§3.1).** A within-predicate
   disagreement is emitted `UNRESOLVED`/`CONTESTED` with every candidate retained and `last_known` +
   date carried; `U5` is load-bearing (SIG-RECON-015) — a stale winner on a MODERATE/FAST/VOLATILE
   predicate returns `UNRESOLVED` even with no dissent. A Tier-A contract does **not** win
   `active_device_count` against a fresher portal snapshot; `D6` claims are **excluded**, not
   down-weighted.

3. **The ruleset is data, not code (SIG-RECON-021, SIG-STORE-017).**
   `reconcile/src/reconcile/data/ruleset.toml` holds the numeric tolerances, the strategy vocabulary,
   the versioned rationale templates, and the style-guide word-lists — versioned, diffable, testable,
   separately attributable. `resolver_version` and `ruleset_version` are independent, so a policy
   change is an attributable, versioned event. Per-predicate epistemics (strategy/volatility/
   directness) stay in the ontology-owned predicate registry the resolver consumes.

4. **Rationales are generated from versioned templates; an LLM never resolves or produces confidence
   (§25.2).** `reconcile.rationale` renders a quotable rationale from the template set; the committed
   `check_template` (clauses a–e) forbids, among other things, mixing a support term and an agreement
   term in one sentence. A human override records author + rationale and keeps BOTH the algorithmic
   result and the override visible (SIG-EPIS-025/026).

## Consequences

- The resolver is the read-time contract every later surface reuses: P08.2's §29 workflows, P08.3's
  materialised `Contradiction`, P12's L4 inference, P14.1's API envelope, and P19.4's
  `reconcile resolve --dsn` / `PgReadStore._compute_on_read()` all call `RESOLVE` — this record makes
  its guarantees citable.
- Because the ruleset and templates are data, their drift risks are real; they are retired by
  RISK-P8-00a/00b (the `check_ruleset` and live-rationale tests).

## Alternatives considered

- **Leave P08.1 undocumented.** Rejected: the resolver is the most-consumed seam in the build; an
  undocumented core is exactly the gap the capstone step exists to close (LD-X05).
- **Amend an existing ADR (e.g. ADR-036, the §29 workflows) instead of a new one.** Rejected: ADR-036
  records P08.2's per-predicate workflows, a different ticket; the resolver deserves its own record,
  and appending to ADR-036 would blur the P08.1/P08.2 boundary.

## Revisit trigger

Revisit if the total-order tie-break, the `U0–U8` ambiguity contract, or the ruleset/registry split
changes; or when P08.3's materialised `Contradiction` and P21.2's persisted annotations change how the
resolver's output is stored (the compute-on-read seam of ADR-059).
