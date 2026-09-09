# ADR-062: Spec reconciliation after the 46-ticket build

- **Status:** Accepted
- **Date:** 2026-09-09
- **Phase:** P20.2
- **Requirement ids:** SIG-ENG-003, SIG-ENG-001, SIG-ENG-002, SIG-ENG-031, SIG-ENG-039, SIG-UI-047, SIG-EVID-020

## Context

After the 46-ticket build (P00.1–P18.2) and the capstone passes (P19.1–P20.1) the canonical spec
(`docs/2_canonical_design_spec.md`) and the built system had drifted in a bounded, well-catalogued
set of places: the build recorded these as ledger deferrals (`LEDGER_DEFERRALS.md`), ADR
deviations, and `MET-DIFFERENTLY` rows in `COVERAGE_MATRIX.csv`. Two classes of drift existed. (1)
**Normative** drift — a requirement the build deliberately met differently (zero-JS static map vs
interactive MapLibre; compute-on-read vs materialized contradiction/coverage/task objects; CLI+JSONL
curation vs a web surface; deferred claim partitioning; `canonical_name` as a scalar; the `evidence/`
package). Each is backed by an ADR, so softening it in the spec is legitimate only as an
operator-approved amendment (defining standard §3.1: no requirement weakened silently). (2)
**Non-normative** drift — Appendix F listed only the eighteen "logical" §15.5/stack decisions under a
numbering that never matched the repository ADR files (LD-X04/LD-D03), the ADR index omitted
ADR-056/057, and §52 said "32 task types" where §33.2 enumerates 34 (ADR-040).

Gate **HG-13** put the seven normative amendments (A1–A7) plus any further `P20.2:spec`-routed item
(A8) to the operator. The operator ticked all eight (A8's enumerated set is empty — `SIG-UI-038` is
the only `P20.2:spec` routing and it is A1).

## Decision

1. **Apply the seven ticked amendments at the source** (`spec_src/*.md` → `BUILD.sh`), never to the
   assembled artifact: A1 zero-JS static map as the conforming default + optional MapLibre island
   (SIG-UI-038, new SIG-UI-047); A2 residency barrier recorded as `absence_kind = not_researched`
   with the absence vocabulary made explicit; A3 `canonical_name` scalar; A4 claim partitioning is
   MAY/deferred but MUST keep the `claim_id` PK/FK contract; A5 compute-on-read accepted as
   conforming for `Contradiction`/`CoverageRecord`/research tasks; A6 CLI+JSONL curation queue
   conforming for Phase 5, web surface deferred to Phase 21; A7 `evidence/` added to the §47 layout.
2. **Fold three approved ticket-added requirements back into the spec** with new appended ids
   (§0.3, never reused): SIG-UI-047 (MAY, the MapLibre island), SIG-EVID-020 (MUST, the `evidence/`
   package blob-vs-capture dedup contract, ADR-023), and SIG-ENG-039 (MUST, Appendix F ↔ `docs/adr/`
   equivalence enforced in CI).
3. **Rebuild Appendix F** to list every repository ADR (ADR-001…062) by number, title, and phase,
   with `docs/adr/README.md` as the single source of truth (SIG-ENG-039), and add the missing
   ADR-056/057 index rows. Record the retired logical numbering as an equivalence note.
4. **Record everything in Appendix G.5** (append-only; earlier G entries untouched) and in
   `docs/build/SPEC_RECONCILIATION_PLAN.md` (§(a) ADR-001…061 dispositions, §(b) A1–A8 with exact
   before/after, §(c) fold-back ids, §(d) order, §(e) residual proposals) and
   `docs/build/TICKET_VS_SPEC.md` (per-ticket in-spec/spec-implied/ticket-added tagging).
5. **Add a consistency checker** (`docs/build/tools/check_spec_src.py`) asserting byte-identical
   `BUILD.sh` reproduction, Appendix F ↔ ADR-file equality, the `668 + 3` id count, and no
   duplicate/malformed/reserved ids.

No package code or schema changed (only the new stdlib checker and its tests). `git diff --stat`
touches `docs/**` only. Part VIII protections were not touched (§0.7).

## Consequences

- The spec now tells the same story as the built system for the seven amended areas, each traceable
  to its ADR; nothing was weakened without a tick.
- The requirement-id space grows by three (671 = 668 + 3); the new ids append to their prefix
  sequences and are traced in `docs/traceability.md` and `COVERAGE_MATRIX.csv`.
- Appendix F is now authoritative and machine-checked; a future ADR that is not indexed fails
  `check_spec_src.py` (SIG-ENG-039).
- No amendment was left as an unapplied proposal (all eight ticked); the only residual is the
  deferred build work (the MapLibre island, Phase-21 persistence/curation surfaces) already tracked
  in `BACKLOG.csv` and the risk register (RISK-P20-02).

## Revisit trigger

Revisit at the next planning pass, or whenever a later ticket adds an ADR or a requirement id (its
Appendix F row and, if a requirement, its `spec_src` paragraph must land in the same PR — SIG-ENG-039),
or if an operator later ticks an amendment that this pass left unticked (there are none today).
