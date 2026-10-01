# ADR-120 — Evidence integrity, useful investigations and current build memory

- Date: 2026-09-25
- Status: accepted as an engineering specification/planning decision under the operator’s six-stream research-and-artifact request; runtime/source/publication/human gates remain unapproved by this record.
- Scope: canonical §55 and the Round-10 contract extension. Implementation has not started.
- Baseline: `0e57e6461d6a5db2e8e0042464750ce2ea65db5e`; integration must reconcile the actual P31 tip and allocate a collision-free ADR number before entering the active chain.

## Context

The live project has strong evidence/append-only architecture but several production seams do not yet realize the contract: actual capture binding and metadata preservation, publisher/operator role interpretation, temporal selection, public-review eligibility, corpus discovery and immutable citation. Human matching evaluation remains provisional. Build memory retains rich history but mixes old/current interpretations. Code observations, execution reports, live public reads and inferences are separated in `docs/build/planning/2026-09-25-six-streams/research/`. No finding here implies every old row is wrong or every evidence blob is lost.

## Decision

1. Treat exact evidence, typed semantic qualifiers, conservative organization identities, per-lineage temporal candidate sets and one public eligibility/disposition policy as prerequisites for expansion. Preserve independent disagreement; do not collapse it with a global latest-row selector. Repair historical data only with proven lineage and additive dispositions.
2. Use three deeply evidenced local dossiers (Oklahoma City, Tulsa, San Diego) as a fixed acceptance portfolio. Enforce the twelve-question rubric and independent semantic review; honest unknowns remain visible, and incomplete views cannot count as pilot completion.
3. Separate blinded human reference labels from operational accept/reject. Preregister frames, grouping, probabilities, split/seal and stopping rules. For the new activated policy, require a simultaneous lower confidence bound of at least 0.98 for authorized auto-write tiers with a method appropriate to the design. Ship it shadow-only before human evaluation; development labels precede candidate freeze and final frame construction, then a separate blinded confirmatory campaign; existing posture remains explicitly PROVISIONAL until an approved transition. This prospectively tightens ADR-099/105’s point-estimate implementation without rewriting them or claiming completed calibration.
4. Retain Astro and existing map/search/network islands (ADR-091/097), complete static record/browse access, and add release-specific read-only search using compartmented immutable SQLite FTS5 artifacts through the existing API package, including a no-JS HTML query route. Keep P31 tiles/compression and no-basemap. Do not create a second SPA, account system or search cluster. Benchmark before exposure; an alternative requires a measured ADR.
5. Derive release namespace before rendering from canonical ID-free inputs; separately hash the final artifact manifest. Enforce current withdrawal at serving/activation/rollback across all operator-controlled origins and artifact types. Immutable identity does not mean irrevocable public access.
6. Add a separately credentialed, durable, minimized anonymous correction receiver and restricted idempotent moderation→canonical-disposition application path. Public exposure, retention/logging and staffing require a concrete operator-approved packet; the loopback curation app remains private.
7. Prioritize acquisition by named missing relationships and independent evidence lineage. Use the researched 27-row inventory with per-row review depth, not assumed rights clearance. Bound the incremental pilot to two non-portfolio families beyond the three city families, at most ten approved documents/aggregate rows each and two new protocols.
8. Preserve build-memory v2 and the ledger as control authority. Introduce evidence-backed obligation/coverage transitions and compact projections in shadow mode first. Cut over every worker/orchestrator write entry point together; use a stable chain identity, authoritative-head preconditions and a validated memory commit as the transaction. No installed global skill is changed by this planning branch.

## Authority, compatibility and supersession

The user requested comprehensive research, canonical updates and agent-ready contracts. This authorizes this design and decomposition, not source-rights flips, human annotation, operational spending, publication or merge-main. Part VIII and existing human gates remain binding. Existing source/claim ids and prior ADR bodies remain intact. New schema changes are additive through LinkML generation/sqitch; old exports get explicit compatibility/legacy states. This decision extends ADR-073, ADR-097, ADR-105, ADR-111, ADR-112 and ADR-114 only in the narrowly stated future interfaces and activation behavior. P31.1–19 obligations retain their owners; P32.1 reconciles any work already closed before dispatch.

## Alternatives considered

- A separate feature-rich SPA: deferred because it would duplicate release, evidence and navigation interpretations before their contracts are reliable. Existing islands can serve the three priority journeys.
- More broad ingestion first: rejected for this round; raw volume does not close missing governance/relationship evidence and amplifies semantic errors.
- More model labels as ground truth: rejected; agreement and self-consistency cannot provide independent human verification.
- Re-fetch missing historical pages as old evidence: rejected; new acquisition is a new observation.
- Rewrite history into a short ledger: rejected; generate a bounded current view and retain explicit historical evidence.
- A new hosted workflow/search platform: not selected; use existing packages and bounded local artifacts before introducing new services/cost.

## Validation and traceability

New normative ids are in §55 and COVERAGE_MATRIX with MISSING verdicts, exactly one contract owner each. The planning package includes six research reports, primary-source inventory, independent reviews and closure, PLAN/REQUIREMENTS, actual ticket files, a full nine-row tail, and reproducible planning checks. Planning validation does not establish implementation or live-domain correctness. See `docs/build/planning/2026-09-25-six-streams/VALIDATION.md` and `HANDOFF.md`. Backlog home: BL-058.

## Consequences

This is a substantive multi-stage program: integrity work precedes public promises, independent human effort is a real external prerequisite, and a final post-evaluation materialization prevents publishing stale graph decisions. A full static record corpus, SQLite cache and intake store have costs to benchmark; no capacity change is presumed approved. Legal/documentary ambiguity and missing captures remain unresolved when evidence is unavailable. Historical/third-party downloads cannot be promised recall.

## Revisit trigger

Revisit when a selected source/predicate mapping cannot express a material document clause; field evidence invalidates role/count assumptions; a source/ruleset mix drifts beyond the evaluated population; the preregistered gate is inconclusive at the approved human budget; record/index build or serving budgets fail on approved infrastructure; withdrawal cannot be enforced at an operator-controlled origin; staffing/retention cannot support public intake; memory cutover cannot cover every actual writer; or a future user need justifies a separate app. Record a new ADR and scoped ticket; never silently weaken evidence, corpus coverage, licensing, sampling or uncertainty disclosures.

### Trigger evaluation — SEED-11 (Round 11 T1, 2026-10-01): FIRED

Evaluated at Round-11 Stage B, T1 (unit SEED-11d, 2026-10-01T07:49:22Z) from F3 §5.1
(`docs/build/planning/2026-09-30-next-phase/research/F3-backlog.md`) and the Round-11 plan
(`docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md`); an agent evaluation, not an operator
decision. **The trigger fired:** three clauses are true: staffing cannot support public intake (D-P32.16-1),
the preregistered gate is likely inconclusive at an affordable human budget (E3 NEW-8), and withdrawal cannot
yet be enforced at an operator-controlled origin (F3 §5.1). **Answer:** (i) intake stays e-mail-only and the
receiver dark for Round 11 (B-8; ADR-180, ADR-186; row P37.59 dark); (ii) no human check this round, disclosed
in every readout, with independent evaluation owed under T-EVAL-IND (B-31; ADR-152; LATER-01; rows 184–187
superseded); (iii) the serving-topology and release rows P34.40, P34.41, P35.53–P35.55 and P35.59 make nginx
honour withdrawals, with a 15-minute withdrawal (plan §5.8; ADR-161). The decision above stays in force until
that answer lands; this ADR's body is unchanged (SIG-ENG-003).
