# Eleutheria — Surveillance Infrastructure Graph (SIG)

Design and implementation specification for an open, vendor-agnostic, temporally versioned,
claim-level-provenance knowledge graph of surveillance infrastructure.

> **Build an open, vendor-agnostic, temporally versioned, claim-level-provenance knowledge graph of
> surveillance infrastructure that federates existing public-interest datasets and primary records
> to show what surveillance capabilities exist, where and by whom they are deployed, how they are
> connected and accessed, what rules and contracts govern them, how they are actually used when
> evidence exists, how they change over time, and exactly which sources support or contradict every
> material claim.**

This repository currently contains **specification and research only** — no implementation yet.

## Contents

| Path | What it is |
|---|---|
| `docs/1_deep_research_overview.md` | The source outline: landscape synthesis and project definition (3,314 lines) |
| `docs/2_canonical_design_spec.md` | **The canonical design and implementation specification** (8,888 lines, 668 numbered requirements) |
| `docs/research/` | The evidence base: 13 research workstreams, 26,818 lines, 501 evidence-formatted findings |
| `docs/research/_meta/` | Traceability index, adversarial gap analysis, lead-agent spot-checks, and the spec's section sources |

## The specification

`docs/2_canonical_design_spec.md` is written to be executed by a long-running coding agent across
19 sequential phases, each with testable acceptance criteria. It is organised as:

- **Part 0** — how to use it; requirement grammar; the execution model
- **Part I** — charter, goals, non-goals, the federation compact
- **Part II** — domain model: temporal semantics, epistemic model, entities, relationships, vocabularies, identity
- **Part III** — data architecture: storage, schema, evidence store, analytics boundary, geospatial
- **Part IV** — acquisition: connector architecture, source registry, parsing, LLM policy, crawler conduct
- **Part V** — resolution, reconciliation, inference, contradiction, coverage metrics
- **Part VI** — research coordination: task generation, contributors, contribution-back
- **Part VII** — delivery: API, exports, the product surfaces, editorial standards
- **Part VIII** — governance, safety, and law: licensing, publication policy, threat model, continuity
- **Part IX** — engineering practice
- **Part X** — the phased implementation plan
- **Appendices A–G** — traceability matrix, the 37 mandatory questions answered, consolidated DDL, a worked example, glossary, ADR index, corrections to the outline

### Three properties it asserts, and how they are checked

1. **Superset.** Every obligation in the outline is discharged. Proven by Appendix A, a matrix over
   **480 atomic obligations** extracted into `docs/research/_meta/OUTLINE_TRACE.md`. Current state:
   **480/480 COVERED**.
2. **Independently corroborated.** The outline's factual claims were re-verified against primary
   sources rather than restated. Corrections are in Appendix G.
3. **Executable.** Every requirement is testable; requirements that cannot be expressed as a test
   are marked `(RATIONALE)` and bind nothing.

## Regenerating the specification

The canonical spec is a **build artifact**. Edit the section sources, not the output:

```sh
sh docs/research/_meta/spec_src/BUILD.sh
```

## Method note

Load-bearing findings from delegated research were not adopted on report alone. Several were
re-verified first-hand before entering the spec; two delegated findings were **declined** after
failing verification, and two of the project's own earlier findings were **withdrawn** the same way.
`docs/research/_meta/LEAD_SPOTCHECKS.md` records all of it, including the errors.

The specification documents **institutions and infrastructure, not people**. Part VIII is binding,
not aspirational: several architectural decisions elsewhere exist because of it.
