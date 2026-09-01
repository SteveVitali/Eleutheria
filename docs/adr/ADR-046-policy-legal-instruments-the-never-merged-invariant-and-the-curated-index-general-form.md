# ADR-046: Policy/LegalInstrument surfaces, the never-merged invariant, and the SIG-EPIS-030 general form

- **Status:** Accepted
- **Date:** 2026-09-01
- **Phase:** P13.2
- **Requirement ids:** SIG-ONTO-034, SIG-RECON-044, SIG-EPIS-030 (and §11.14 `LegalInstrument`)
- **Spec:** docs/2_canonical_design_spec.md §§11.13–11.14 (`Policy` / `LegalInstrument`), §11.15 (`ConfigurationState`), §29.6 (policy-vs-configuration reconciliation), §10.9 (curated indexes need not be normalized)

## Context

P13.2 owns "what governs the infrastructure and where it is disobeyed": the `Policy`
and `LegalInstrument` predicate surfaces, policy-versus-configuration divergence as a
first-class finding (SIG-RECON-044), the invariant that `Policy` is never merged with
`ConfigurationState` (SIG-ONTO-034), and the general capability to hold a curated
source index *as an index* without normalizing its entries into claims (SIG-EPIS-030).

Two of the three entity/finding surfaces were already **front-loaded by dependencies**:

- **P01.1** defined `Policy`, `LegalInstrument`, and `ConfigurationState` in the LinkML
  source (`ontology/schema/entities.yaml`) with their full §11.13–11.15 predicate
  surfaces and the `PolicyType` / `LegalInstrumentType` / `EnforcementMechanism` enums.
- **P08.2** implemented the §29.6 divergence reconciler (`reconcile.policy_config`) with
  both-sides-retained evidence and the `collapse()` guard (SIG-RECON-044).

What was **not** yet present: (a) executable proof of the `Policy`/`LegalInstrument`
predicate surfaces and the never-merged invariant as ticket-scoped acceptance tests, and
(b) the **general form** of SIG-EPIS-030 — P13.1's `accountability` connector held the
Abuse Library as an index inline, but there was no reusable "curated source index held
as an index" object that a connector relies on.

## Decision

1. **No re-implementation of front-loaded surfaces.** The entities and the §29.6
   reconciler are consumed as-is; P13.2 does not touch the schema (so the generated
   artifacts are unchanged and the generation gate is unaffected). Instead it adds the
   ticket's acceptance tests against those surfaces: the `Policy` / `LegalInstrument`
   predicate-surface tests and the `Policy` ≠ `ConfigurationState` never-merged test
   (schema-level, plus a resolution-layer assertion that the two are distinct types).

2. **SIG-EPIS-030 as a general module in `connectors/`.** The curated-source-index
   capability lands as `connectors.curated_index` (`CuratedSourceIndex` /
   `CuratedIndexEntry`): a bibliography held as index references whose `index_records()`
   are `index_only` and whose `as_claims()` raises `IndexNormalizationRefused`. Holding
   an index as an index is fundamentally a connector-stage behaviour — the `normalize()`
   stage is what would otherwise turn entries into claims — so the general form lives in
   the connector framework package, alongside the seven connectors that consume it. The
   P13.1 `accountability` connector's Abuse Library path is refactored to build a
   `CuratedIndexEntry`, making it the canonical consumer of the general form. The change
   is additive: the emitted `index_only` advocacy-analysis evidence-link row shape is
   byte-for-byte unchanged, so no prior wire contract breaks.

## Consequences

- The SIG-EPIS-030 invariant ("held as an index, not normalized into facts") is now a
  mechanical property (`as_claims()` raises) reusable by any future connector with a
  curated bibliography, not a per-connector convention.
- Because P13.2 adds no schema and no new persisted surface, the risk it carries is
  entirely "an index entry is silently promoted to a claim" and "the two governing
  objects are folded into one" — both retired by executable checks (see risk register
  Phase 13 / P13.2).
- Public API / export surfaces over `Policy` / `LegalInstrument` remain out of scope
  (P14.1 / P14.2), as does `ConfigurationState` population (owned upstream).

## Revisit trigger

Revisit when the read/export surfaces over `Policy` / `LegalInstrument` land (P14.1 /
P14.2) — if they need a persisted representation of a curated source index (rather than
the in-memory `CuratedSourceIndex` value object), promote `connectors.curated_index` to a
stored surface at that point. Also revisit if a second connector needs the general form
with a different row shape than the `accountability` Abuse Library path, or if
`ConfigurationState` population (upstream) changes the shape the §29.6 reconciler consumes.
