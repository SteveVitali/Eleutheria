# Canonical Spec — document architecture (working plan)

Target file: `docs/2_canonical_design_spec.md`. Single canonical artifact; phase-sliceable.

## Part 0 — How to use this specification
0.1 Audience and execution model (long-running agent, sequential phases, implement-spec)
0.2 Requirement identifier conventions (SIG-<AREA>-<nnn>), normative language (MUST/SHOULD/MAY)
0.3 Traceability contract to docs/1_deep_research_overview.md
0.4 Research cache index (docs/research/R1..R13)
0.5 Definition of Done, per requirement and per phase
0.6 How to handle spec/reality conflicts discovered mid-build

## Part I — Charter
1. Mission, one-sentence specification, defining purpose
2. The thirteen questions and the four canonical user journeys (executable acceptance queries)
3. First principles and architectural invariants (the twelve data-quality principles + defining standard)
4. Goals (8) and non-goals (10+)
5. Scope: the initial wedge, the generalization requirement, explicit out-of-scope
6. The federation compact: relationship to every existing project
7. Success criteria and how the project measures leverage on the ecosystem

## Part II — Domain model
8. Conceptual model overview + the layer architecture
9. Temporal semantics (the time dimensions, EDTF, open/unknown intervals)
10. Epistemic model (evidence → claim → resolution → inference; tiers; confidence vocabulary)
11. Entity catalog (all entities, all fields, all constraints)
12. Relationship catalog (all edge types with precise semantics)
13. Controlled vocabularies (technology, lifecycle, org type, role, evidence type, ...)
14. Identity architecture (identifiers, ER, stability, crosswalks)

## Part III — Data architecture
15. Storage decision + ADRs
16. Logical → physical schema, full DDL
17. Evidence store (content addressing, capture, archival, tiered access)
18. Analytics substrate and the graph/analytics boundary
19. Geospatial architecture
20. Schema, ontology, and vocabulary versioning

## Part IV — Acquisition
21. Connector architecture and lifecycle
22. Source registry (per-source access facts, licenses, cadence, permission status)
23. Connector specifications (one per source)
24. Document parsing and extraction architecture
25. LLM usage policy and guardrails
26. Crawler conduct and politeness enforcement

## Part V — Resolution, reconciliation, inference
27. Entity resolution pipeline
28. Reconciliation engine and per-predicate strategies
29. The named reconciliation workflows
30. Inference catalog
31. Contradiction management
32. Coverage, completeness, freshness, and quality metrics

## Part VI — Research coordination
33. Research-task generation (detectors, lifecycle, assignment)
34. Contributor system, tiers, review
35. Contribution-back and upstream integration
36. Records-request generation

## Part VII — Delivery
37. Public API
38. Bulk exports and dataset publication
39. UI/UX specification (seven surfaces + IA + interaction)
40. Design system, epistemic visual language, accessibility
41. Editorial standards and voice

## Part VIII — Governance, safety, legal
42. Licensing architecture (inputs, internal, outputs, export-time computation)
43. Publication policy (personal data, coordinates, RF candidates, aggregates)
44. Threat model and security architecture
45. Takedown, correction, dispute, transparency reporting
46. Project governance, sustainability, continuity

## Part IX — Engineering practice
47. Stack, repo layout, tooling
48. Testing strategy
49. Observability, ops, runbooks
50. Deployment topology and cost model

## Part X — Implementation plan
51. Phasing philosophy and phase-gate criteria
52. Phase 0 … Phase N: deliverables, tickets, acceptance criteria, dependencies, verification
53. Risk register and mitigations
54. Sequencing constraints and parallelization map

## Appendices
A. Requirement traceability matrix (all 480 OL-* ids → spec sections)
B. Answers to all 37 mandatory questions (§20)
C. Consolidated DDL
D. Worked end-to-end example (Example City dossier, fully traced)
E. Glossary
F. Architecture Decision Record index
G. Corrections to the source outline
