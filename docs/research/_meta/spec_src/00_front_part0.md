# Surveillance Infrastructure Graph (SIG)
## Canonical Design and Implementation Specification

**Document:** `docs/2_canonical_design_spec.md`
**Version:** 1.0.0
**Status:** Canonical. This document is the authoritative contract for implementation.
**Supersedes as an implementation authority:** `docs/1_deep_research_overview.md` (which remains
the authoritative statement of *intent* and against which this document is proven a strict superset).
**Spec date:** 2026-08-20

---

# Part 0 — How to use this specification

## 0.1 What this document is

`docs/1_deep_research_overview.md` ("the outline") is a landscape synthesis and project
definition. It is deliberately not an implementation specification; its closing section
instructs a downstream agent to "convert its research thesis into an implementable
architecture."

This document is that conversion. It is written to be executed by a long-running coding agent
across sequential phases, with each phase small enough to be implemented in a single fresh
context and verifiable against explicit acceptance criteria.

Three properties are load-bearing and are asserted here so that they can be checked:

1. **Superset.** Every obligation in the outline is discharged here. The proof is
   Appendix A, a traceability matrix over 480 extracted obligations
   (`docs/research/_meta/OUTLINE_TRACE.md`), each mapped to the section that discharges it and
   labelled `VERBATIM-PRESERVED`, `DEEPENED`, `CORRECTED`, or `EXTENDED`.
2. **Independently corroborated.** The outline's factual claims were re-verified against primary
   sources rather than restated. Corrections are collected in Appendix G and applied in place
   throughout. Where a claim could not be verified, this document says so rather than repeating it.

   All thirteen research workstreams are complete: **26,818 lines, 501 evidence-formatted findings,
   667 emitted requirements** (§0.5). Seven workstreams were interrupted partway by an account spend
   limit and were subsequently finished; Appendix G.4 records what was outstanding and how each item
   closed, because a specification that conceals its own gaps is not credible about anyone else's.

   Where research corrected *this document's* earlier findings, those corrections are recorded in
   G.4.2 rather than silently applied. Four residual questions remain genuinely open and are carried
   in the risk register (§53), not presented as settled.

3. **Executable.** Every requirement is testable. Requirements that cannot be expressed as a
   test are demoted to design rationale and marked as such.

## 0.2 Normative language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**,
**SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** are to be interpreted as described in
RFC 2119 and RFC 8174, and only when they appear in capitals.

- **MUST** — an implementation that violates this is non-conformant. Phase gates fail.
- **SHOULD** — deviation is permitted but MUST be recorded as an Architecture Decision Record
  (ADR) with rationale, and MUST be surfaced in the phase's evidence report.
- **MAY** — genuinely optional; no justification required either way.

Prose without these keywords is explanatory. It informs judgment; it does not bind.

**Non-normative statements with identifiers.** A few statements carry an identifier but bind
nothing — they record a scoping decision, an intended outcome, or an honest limitation that later
readers must not mistake for an omission. These are marked `(RATIONALE)` in place of a modal verb.
They are traceable and citable but impose no obligation.

**Section references.** A bare `§N` refers to a section of **this** document. References to the
source outline are written `outline §N`, and references to an external instrument name it
explicitly (e.g. "ODbL clause 4.4(b)"). A CI link-check MUST verify that every bare `§N` resolves to
a heading in this document.

## 0.3 Requirement identifiers

Every normative requirement carries a stable identifier:

```
SIG-<AREA>-<nnn>
```

`<AREA>` is a three-to-six letter area code, `<nnn>` a zero-padded ordinal within that area.
Identifiers are **append-only and never reused**. A withdrawn requirement is marked
`WITHDRAWN` in place with the reason and the superseding id; it is not deleted, because
implementation branches and tickets reference ids by number.

**Reserved-but-unassigned ids.** `SIG-ENG-006`…`SIG-ENG-009` and `SIG-ENG-028`…`SIG-ENG-029` are
**RESERVED, not withdrawn**: they were allocated during drafting to requirements that were merged
into others before publication. They MUST NOT be assigned to new requirements, so that any external
reference to them fails loudly rather than resolving to unrelated text. A CI check MUST assert that
every `SIG-*` id referenced anywhere in this document is either defined or listed here as reserved.

| Area code | Domain |
|---|---|
| `CHART` | Charter, scope, goals, non-goals |
| `ONTO` | Ontology, entities, fields, vocabularies |
| `TIME` | Temporal semantics |
| `EPIS` | Epistemic model: evidence, claims, confidence |
| `IDENT` | Identity, identifiers, entity resolution |
| `STORE` | Storage, schema, persistence |
| `EVID` | Evidence store, capture, archival |
| `GEO` | Geospatial |
| `INGEST` | Connector architecture and connectors |
| `PARSE` | Document parsing and extraction |
| `LLM` | Model-assisted processing and its guardrails |
| `RECON` | Reconciliation, resolution, inference, contradiction |
| `METRIC` | Coverage, completeness, freshness, quality metrics |
| `TASK` | Research-task generation and lifecycle |
| `CONTRIB` | Contributor system and upstream contribution |
| `API` | Public API |
| `EXPORT` | Bulk exports and dataset publication |
| `UI` | User interface, information architecture, interaction |
| `A11Y` | Accessibility (requirements are prefixed `SIG-UI-*` where they are inseparable from a surface; standalone `SIG-A11Y-*` ids are reserved for future use) |
| `LIC` | Licensing and rights management |
| `PUB` | Publication policy, personal data, sensitivity |
| `SEC` | Security and threat model |
| `GOV` | Governance, takedown, continuity |
| `ENG` | Engineering practice, repo, testing, CI |
| `OPS` | Deployment, observability, cost (currently carried under `SIG-ENG-*` in Part IX; `SIG-OPS-*` is reserved for future use) |

## 0.4 The execution model

This specification is designed to be executed as follows.

```
docs/2_canonical_design_spec.md              (this document — the contract)
        │
        ├── Part X phase plan defines Phase 0 … Phase N
        │
        ▼
~/agent-skills/skills/decompose-spec         (optional; slices a phase into tickets)
        │
        ▼
~/agent-skills/skills/implement-spec         (one invocation per ticket)
        │   spec = the ticket + the sections of this document it cites
        │   → branch → plan + test matrix → implement → self-review
        │   → gap-analysis vs the cited sections → verify → PR + evidence
        ▼
~/agent-skills/skills/orchestrate-build      (optional; drives tickets to completion)
```

**SIG-ENG-001 (MUST).** Each phase in Part X MUST be executable without reading any section of
this document not explicitly cited by that phase, plus Part 0, Part I §3 (invariants), and the
glossary. Phases that violate this are mis-cut and MUST be re-cut before implementation.

**SIG-ENG-002 (MUST).** A phase is complete only when every acceptance criterion listed for it
passes, and the phase-gate checks in §51.3 pass. Partial completion is reported as partial; it
is never reported as done.

**SIG-ENG-003 (MUST).** When implementation reveals that this specification is wrong —
an upstream API changed, a license is more restrictive than recorded, a design does not work —
the implementing agent MUST stop, record the finding as an ADR under `docs/adr/`, propose the
amendment, and proceed under the amendment. It MUST NOT silently implement something different
from what this document says, and it MUST NOT implement something it knows to be wrong because
this document says it.

## 0.5 The research cache

This specification is grounded in a structured research cache. Sections cite it by workstream
id. The cache is evidence, not decoration: where this document asserts that a data source is
accessible, the cache records the exact request that succeeded and what it returned.

| File | Workstream |
|---|---|
| `docs/research/R1_osm_physical_layer_and_odbl.md` | OSM schema, extraction, history, DeFlock, ODbL analysis |
| `docs/research/R2_flock_ecosystem_data_access.md` | Flock portals, Eyes on Flock, HIBF, ALPR Watch, access matrix |
| `docs/research/R3_eff_atlas_and_accountability.md` | EFF Atlas, Data Library, Data Driven, Accountability Atlas, CCOPS |
| `docs/research/R4_records_procurement_evidence.md` | MuckRock, DocumentCloud, federal/state/local procurement, courts, archiving |
| `docs/research/R5_identity_and_entity_resolution.md` | ORI, Census, org identity, ER methodology, ID scheme |
| `docs/research/R6_storage_bitemporal_provenance.md` | Storage decision, bitemporality, PROV, content addressing |
| `docs/research/R7_vendors_technologies_taxonomy.md` | Vendor/product/technology reference data, integration topology, roles, lifecycle |
| `docs/research/R8_legal_ethics_safety_governance.md` | Collection legality, publication policy, takedown, threat model, licensing |
| `docs/research/R9_international.md` | Technopolice, EU/UK/global sources, jurisdiction generalization, i18n |
| `docs/research/R10_uiux_and_product_surfaces.md` | Personas, epistemic UI, seven surfaces, stack, accessibility |
| `docs/research/R11_pipeline_ops_engineering.md` | Connector architecture, orchestration, data quality, deployment, cost |
| `docs/research/R12_community_and_research_coordination.md` | Local ecosystem, Stage 0 outreach, task types, FOIA reference, contribution-back |
| `docs/research/R13_reconciliation_and_inference.md` | Source model, resolution algorithm, workflows, inference, coverage metrics |
| `docs/research/_meta/OUTLINE_TRACE.md` | The 480 traced outline obligations |
| `docs/research/_meta/LEAD_SPOTCHECKS.md` | Direct verifications by the synthesizing agent |
| `docs/research/_meta/CONVENTIONS.md` | Research cache format |

## 0.6 Definition of Done

**SIG-ENG-004 (MUST).** A requirement is Done when all of the following hold:

1. The behaviour exists in the codebase on the default branch.
2. An automated test asserts the behaviour and fails if it is removed.
3. Where the requirement concerns data, a data-quality check (§48) asserts it in the pipeline,
   not only in unit tests.
4. Where the requirement concerns a public surface, it is documented in the user-facing docs.
5. The requirement id appears in the commit or PR that implemented it.

**SIG-ENG-005 (MUST).** No requirement is Done on the strength of a manual check alone. If a
behaviour genuinely cannot be automatically verified, it MUST be recorded in the risk register
(§53) as an unverifiable requirement with the compensating control.

## 0.7 A note on the subject matter

This project documents institutions and infrastructure. It is a research and journalism tool.
Part VIII is not an appendix of good intentions: it contains binding constraints that
the rest of the specification is written to satisfy, and several architectural decisions
elsewhere in this document exist *because* of them. An implementation that ships Parts II–VII
without Part VIII is not an incomplete version of SIG. It is a different and worse project.

---
