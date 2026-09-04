# ADR-031: A minimal count-reconciliation seed, and the three missing count predicates, for the P06.1 vertical slice

- **Status:** Accepted
- **Date:** 2026-09-01
- **Phase:** P06.1
- **Requirement ids:** SIG-RECON-026, SIG-RECON-027, SIG-RECON-028, SIG-RECON-029, SIG-EPIS-021, SIG-RECON-008, SIG-ONTO-067
- **Spec:** docs/2_canonical_design_spec.md §29.1, §10.6, §28.3 (implements the Phase-6 slice of §52)

## Context

Phase 6 (the vertical slice) is sequenced **before** Phase 8, the reconciliation
engine and contradictions. Yet the P06.1 ticket requires the slice to keep the
count predicates distinct, fire `PREDICATE_CONFLATION` on a deliberate
conflation, and emit unresolved deltas as research tasks (SIG-RECON-026/028/029)
— i.e. it needs real reconciliation logic that does not yet exist. Two things
were also discovered to be missing when the slice tried to run on real data
(Oklahoma City):

1. **No code computed the composed weight `W` (§10.6) or the derived currency `C`
   (§28.3).** They were spec tables only. Reconciliation cannot resolve competing
   claims without them.
2. **Three of the six §29.1 count predicates were absent from the predicate
   registry.** Only `contracted_`, `active_`, and `installed_device_count` were in
   `ontology/vocab/predicates.yaml`; `invoiced_`, `mapped_`, and
   `claimed_device_count` existed only in spec prose, so `C` could not be derived
   for them (see the retrospective, finding 1).

## Decision

1. Implement a **minimal, spec-faithful count-reconciliation seed** in the
   existing `reconcile/` package: `weight.py` (the §10.6 ordinal composition and
   §28.3 currency derivation), `model.py` (thin value objects aligned with
   `db/deploy/graph_annotations.sql`), and `counts.py` (§29.1: per-basis
   resolution, the `PREDICATE_CONFLATION` guard, and delta→task generation). It is
   scoped to what the slice needs and is anchored on the spec's own Appendix D.2
   worked example.

2. Add `invoiced_device_count`, `mapped_device_count`, and `claimed_device_count`
   to the predicate registry source (`ontology/vocab/predicates.yaml`), each with
   a volatility class, half-life, resolution strategy, and full directness row
   (SIG-ONTO-067), and regenerate the committed artifacts. This is **additive and
   back-compatible**: no existing predicate, wire name, or id changes.

3. `reconcile` gains a workspace dependency on `sig-ontology` to read the
   generated predicate registry at runtime (epistemics are ruleset data, not
   hard-coded — SIG-RECON-009).

## Consequences

The slice executes J-1 end to end with genuine reconciliation, and the epistemic
model is exercised (and shown correct against Appendix D.2) for the first time.
`mapped_device_count` is treated as a lower bound (SIG-RECON-027) and no single
"true count" is emitted (SIG-RECON-029). The seed is intentionally partial: it
handles count predicates only, one contradiction shape per group, and a fixed set
of delta pairs.

## Alternatives considered

Deferring all reconciliation to P08 and faking the slice's numbers (rejected: the
slice's whole purpose is to *falsify the design*, which requires real machinery);
hard-coding volatility/half-life in `reconcile` instead of adding registry rows
(rejected: violates SIG-RECON-009 and would let the registry stay silently
incomplete — the very gap the slice exists to surface).

## Revisit trigger

P08 lands the full reconciliation engine and contradiction model. At that point
`reconcile/{weight,counts,model}.py` is either promoted to the engine's core or
replaced by it, and this ADR is superseded by the P08 ADRs. Also revisit if the
count model gains a `scope`/population dimension (retrospective finding 3).
