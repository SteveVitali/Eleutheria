# Research cache

Evidence base for `docs/2_canonical_design_spec.md`. Every material claim in the spec traces here.

**Status: all thirteen workstreams complete.** 26,862 lines · 541 evidence-formatted findings ·
667 emitted requirements. Seven workstreams were interrupted partway by an account spend limit and
were subsequently finished; spec §0.1 and Appendix G.4 record what was outstanding and how each item
closed.

## Workstreams

| File | Scope | Lines | Findings |
|---|---|---|---|
| `R1_osm_physical_layer_and_odbl.md` | OSM schema and extraction (measured), Overpass and history APIs (tested), DeFlock, **the ODbL analysis**, write-back compliance | 1,908 | 39 |
| `R2_flock_ecosystem_data_access.md` | Flock portals, **the Eyes on Flock API**, HIBF audit schemas, ALPR Watch, ecosystem licences | 1,708 | 20 |
| `R3_eff_atlas_and_accountability.md` | EFF Atlas, Data Library (42 entries), Data Driven, SLS taxonomy, **CCOPS**, state mandates | 1,760 | 54 |
| `R4_records_procurement_evidence.md` | MuckRock, DocumentCloud, procurement, cooperative purchasing, courts, archiving | 2,375 | 53 |
| `R5_identity_and_entity_resolution.md` | ORI, Census, org identity, ER methodology, ID scheme | 2,195 | 23 |
| `R6_storage_bitemporal_provenance.md` | Storage decision, bitemporality, PROV, content addressing | 2,200 | 50 |
| `R7_vendors_technologies_taxonomy.md` | Vendors, technologies, integration edges, roles, lifecycle | 1,949 | 43 |
| `R8_legal_ethics_safety_governance.md` | Collection legality, publication policy, takedown, threat model | 2,102 | 36 |
| `R9_international.md` | Technopolice, EU/UK/global, jurisdiction generalization | 1,745 | 45 |
| `R10_uiux_and_product_surfaces.md` | Personas, epistemic UI, the surfaces, stack, accessibility | 1,577 | 33 |
| `R11_pipeline_ops_engineering.md` | Connectors, orchestration, data quality, deployment, cost | 2,123 | 37 |
| `R12_community_and_research_coordination.md` | Local ecosystem, outreach, task types, **51-jurisdiction records-law table** | 2,385 | 34 |
| `R13_reconciliation_and_inference.md` | Source model, resolution algorithm, workflows, inference, coverage metrics | 2,791 | 34 |

## Meta

| File | Purpose |
|---|---|
| `_meta/OUTLINE_TRACE.md` | **480 atomic obligations** extracted from the outline with stable `OL-*` ids |
| `_meta/GAP_ANALYSIS.md` | Independent adversarial review of the spec against those 480, plus the closure record |
| `_meta/LEAD_SPOTCHECKS.md` | **19 direct verifications** by the lead agent — the OSM measurements, three adjudications between disagreeing sources, and two corrections to this project's own earlier findings |
| `_meta/CONVENTIONS.md` | The research file format |
| `_meta/SPEC_OUTLINE.md` | The spec's planned document architecture |
| `_meta/spec_src/` | Section sources; `BUILD.sh` assembles them into the canonical spec |

## Regenerating the spec

```sh
sh docs/research/_meta/spec_src/BUILD.sh
```

Edit the section files, never `docs/2_canonical_design_spec.md` directly — it is a build artifact.

## A note on method

Findings from delegated research were **not adopted on report alone** where they were load-bearing.
The Eyes on Flock API, the California state-mandate findings, the Wayback exclusion, and the OSM
element-repurposing trap were each re-verified first-hand before entering the spec. Two delegated
findings were **declined** after failing verification, and two of the lead agent's own earlier
findings were **withdrawn** the same way. `_meta/LEAD_SPOTCHECKS.md` records all of it, including
the errors — a specification that hides its own error rate is not credible about anyone else's.
