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

# Part I — Charter

## 1. Mission

### 1.1 The one-sentence specification

> **Build an open, vendor-agnostic, temporally versioned, claim-level-provenance knowledge graph
> of surveillance infrastructure that federates existing public-interest datasets and primary
> records to show what surveillance capabilities exist, where and by whom they are deployed, how
> they are connected and accessed, what rules and contracts govern them, how they are actually
> used when evidence exists, how they change over time, and exactly which sources support or
> contradict every material claim.**

*(Discharges OL-23-01, preserved verbatim.)*

### 1.2 The defining purpose

> **To make the structure of surveillance infrastructure legible: what exists, where it exists,
> who controls it, who can access it, how it is connected, what capabilities it provides, what
> rules govern it, how those facts changed over time, and exactly what evidence supports every
> claim.**

*(Discharges OL-ES-23, preserved verbatim.)*

### 1.3 What SIG is not building

**SIG-CHART-001 (MUST NOT).** SIG MUST NOT be built as another surveillance map.

The ecosystem already contains capable projects for physical camera mapping, agency-adoption
mapping, transparency-portal aggregation, Flock audit-log analysis, public-records acquisition,
incident indexing, policy advocacy, and avoidance routing. What is missing is a **general
reconciliation layer across them** (OL-6-00). SIG is that layer.

**SIG-CHART-002 (MUST).** SIG MUST be architected such that its distinctive output is
*joined evidence* — facts that no single upstream can produce because they require reconciling
independent sources that disagree. If a SIG feature can be provided by an existing project
equally well, SIG SHOULD link to that project rather than reimplement it, and the decision MUST
be recorded in the federation compact (§6).

### 1.4 The core intellectual shift

**SIG-CHART-003 (MUST).** The ontology MUST treat the fundamental unit of surveillance
infrastructure as a **relationship among organizations, technologies, capabilities, physical
assets, datasets, policies, and access rights** — not as a device.

A surveillance device is one manifestation among many. The model MUST represent all of the
following without special-casing (OL-ES-26):

| Manifestation | Why it breaks a device-centric model |
|---|---|
| A fixed Flock camera on a public road | The baseline case; a device with coordinates. |
| A patrol-car ALPR | A device with no fixed coordinate; mobility is a first-class property. |
| A Fusus integration exposing 5,000 private cameras to a real-time crime center | The surveillance capability is created by an *integration*, not by any device SIG owns a record of. |
| A Clearview AI license | A deployment with no roadside device at all. |
| A Fog Reveal subscription | Location histories with no locally owned sensor whatsoever. |
| A camera owned by a shopping center but searchable by a police department | Ownership and access are separate relationships held by different organizations. |
| A canceled Flock contract followed by an Axon replacement | Not the disappearance of surveillance; a change of implementation. |

**SIG-CHART-004 (MUST).** SIG MUST model surveillance power as a graph of capabilities and
access, not merely a geography of sensors (OL-1.1-04).

The rationale is empirical, not rhetorical. Two jurisdictions with twenty cameras each can have
radically different surveillance capability: one retains data seven days and does not share;
the other retains a year, participates in nationwide lookup, feeds an RTCC, receives
private-camera streams, uses federal hotlists, and permits broad search (OL-1.1-03). A count of
cameras does not distinguish them. SIG MUST.

**SIG-CHART-005 (MUST).** The model MUST be able to express the twelve properties through which
networked surveillance systems generate power (OL-1.1-02): sensor density; historical retention;
cross-jurisdictional sharing; centralized search; automated alerts; integration with other
databases; private-public access relationships; analytics; identity resolution; institutional
policy; legal permissibility; and operator behavior. §12.9 maps each to the entity and predicate
that carries it, and Part V §32 defines the derived metrics that summarize them.

---

## 2. The questions SIG exists to answer

### 2.1 The thirteen questions

**SIG-CHART-006 (MUST).** Each of the following MUST be answerable from the graph, for any
subject where evidence exists, with full provenance and an explicit statement of coverage where
it does not. Each is bound to an acceptance query in §2.3.

| # | Question | Primary carrier in the model |
|---|---|---|
| Q-1 | Where is a physical surveillance device? | `PhysicalAsset` + geometry (§11.8) |
| Q-2 | Which organization owns or operates it? | Role edges: `owns`, `operates` (§12.4) |
| Q-3 | Which surveillance technology has a given agency adopted? | `Deployment` → `Technology` (§11.5) |
| Q-4 | Which vendor and product are involved? | `Vendor`, `Product` (§11.2, §11.4) |
| Q-5 | What did the deployment cost, and under what contract? | `Contract` (§11.11) |
| Q-6 | How many devices were purchased or reported? | The distinct count predicates (§29.1) |
| Q-7 | What is the system configured to retain, search, or share? | `ConfigurationState` (§11.15) |
| Q-8 | Which other organizations can access the data? | `AccessRelationship`, configured (§12.5) |
| Q-9 | Which organizations actually searched the data? | `UsageAggregate` (§11.16) |
| Q-10 | For what stated reasons? | Reason-category aggregates (§11.16, §24.2) |
| Q-11 | What policies and legal restrictions govern the system? | `Policy`, `LegalInstrument` (§11.13, §11.14) |
| Q-12 | Has the deployment been suspended, canceled, replaced, challenged, or litigated? | Lifecycle state machine (§13.4) + `AccountabilityEvent` (§11.17) |
| Q-13 | How does one deployment connect to broader regional or national networks? | `IntegrationRelationship` + access-path closure (§30.2) |

**SIG-CHART-007 (MUST).** These thirteen questions are today answered by thirteen different
systems (OL-ES-03). The specification's central architectural burden is that answering them
*together*, about the *same* subject, requires entity resolution (Part V §27) and reconciliation
(Part V §28) to be correct first. No product surface may be built that presents a joined answer
without the joins being auditable.

### 2.2 The four canonical user journeys

**SIG-CHART-008 (MUST).** The following four journeys are acceptance criteria for the system as
a whole, not illustrations. Each MUST be executable end-to-end against real data before the
corresponding phase gate passes, and each MUST render with per-claim provenance.

#### J-1 — The journalist's traversal

```
city
  → police agency
    → Flock deployment
      → contract
        → 42 contracted cameras
        → 31 field-observed OSM devices
        → 38 currently reported portal cameras
      → sharing relationships
      → actual network searches
      → retention settings
      → policy
      → related litigation
      → replacement vendor
```

This traversal crosses seven independent source families and three disagreeing quantity claims.
It is the single most demanding integration test in the specification. §D (Appendix D) works it
end to end. *(Discharges OL-ES-29.)*

#### J-2 — The researcher's query

> Which U.S. agencies operate ALPRs, share data outside their state, have retention periods over
> 30 days, and have documented immigration-related searches?

Four predicates, four different source families, four different confidence profiles. The result
MUST carry a coverage statement: how many agencies were evaluable for each predicate, and how
many were excluded for lack of evidence rather than for failing the test. *(Discharges OL-ES-30.)*

#### J-3 — The advocate's query

> Which municipalities are considering renewal in the next six months, how many cameras are
> physically mapped, what the current sharing network looks like, and which source documents
> would be useful at the next public meeting?

This is forward-looking and therefore depends on the procurement/renewal layer (§11.11, §39.5)
and on the evidence recommender (§39.5a). *(Discharges OL-ES-31.)*

#### J-4 — The systems researcher's query

> Which vendors increasingly occupy the same integration layer as Flock, and where are cities
> replacing one vendor with another rather than reducing surveillance capability?

This requires the lifecycle model with `replaced_by` edges (§13.4) and integration-layer
classification (§12.3). It is the query that fails outright in every existing dataset.
*(Discharges OL-ES-32.)*

### 2.3 Acceptance queries

**SIG-CHART-009 (MUST).** Each of Q-1…Q-13 and J-1…J-4 MUST have a corresponding executable
acceptance query committed under `tests/acceptance/queries/`, versioned with the schema, and run
in CI against a fixture dataset. A schema change that breaks an acceptance query fails CI.

**SIG-CHART-010 (MUST).** Each acceptance query MUST assert not only that rows are returned but
that (a) every returned material fact carries at least one resolvable evidence reference, and
(b) a coverage statement accompanies the result set.

---

## 3. First principles and architectural invariants

These are the invariants. Every subsequent design decision in this document is downstream of
them, and any proposed change that violates one is rejected by default.

### 3.1 The defining standard

> **No unexplained dots. No unexplained edges. No silent overwrites. No synthetic certainty.**
>
> Every node has identity. Every edge has semantics. Every state has time. Every claim has
> evidence. Every inference says that it is an inference. Every contradiction remains visible
> until resolved.

*(Discharges OL-24-19, OL-24-20, preserved verbatim.)*

**SIG-CHART-011 (MUST).** These six sentences MUST be enforceable, not aspirational. §3.3 binds
each to a schema-level or check-level enforcement point.

### 3.2 The twelve data-quality principles

**SIG-CHART-012 (MUST).** The following twelve principles are architectural invariants. The
"Enforced by" column is normative: it names where a violation is *mechanically prevented or
detected*, not merely discouraged.

| # | Principle | Meaning | Enforced by |
|---|---|---|---|
| P1 | **Provenance over convenience** | Never store a "fact" if the evidence-backed claim that generated it can be stored. | No writable "current value" columns on entities; resolved values are a derived view over claims (§16.4). CI check `no_orphan_facts` (§48). |
| P2 | **Raw before normalized** | Preserve source form. | `raw_value` NOT NULL on every extracted claim; normalization stored beside, never over (§16.2). |
| P3 | **Time before overwrite** | Append state transitions. | Claim table is append-only; UPDATE revoked at the role level (§16.3). Corrections are new assertions with `supersedes` (§16.6). |
| P4 | **Uncertainty before false precision** | Unknown is legitimate. | `UNRESOLVED` is a first-class resolution outcome (§28.5); nullable-with-reason encoding (§9.5). |
| P5 | **Federation before duplication** | Improve upstream commons. | Federation compact (§6); upstream-id preservation is mandatory (§14.6); contribution-back is a funded phase, not a stretch goal (§35). |
| P6 | **Organization identity before graph analytics** | Bad entity resolution makes every network statistic misleading. | Phase ordering: no network analytics surface ships before ER quality gates pass (§14.7). Analytics UI carries an ER-quality disclosure (§39.4). |
| P7 | **Capability before vendor** | Vendors change; capabilities persist. | `Technology`/`Capability` are independent of `Product`/`Vendor` (§11.5, §11.6); no vendor name appears in a schema identifier. |
| P8 | **Ownership is not access** | Model owner, operator, controller, platform provider, accessor, and data recipient separately. | Six distinct role edge types, no default coercion (§12.4). |
| P9 | **Configured access is not actual use** | Model both. | `AccessRelationship` and `UsageAggregate` are separate entities that MUST NOT be merged (§12.5, §11.16, §29.3). |
| P10 | **Policy is not configuration** | Model both. | `Policy` and `ConfigurationState` are separate entities; their disagreement is a first-class finding (§29.6). |
| P11 | **Contracted is not installed** | Model lifecycle. | Distinct count predicates (§29.1) and the lifecycle state machine (§13.4). |
| P12 | **Installed is not active** | Preserve last observation. | Every asset carries `last_observed` and a staleness class; "active" is never inferred from "exists" (§13.4, §32.4). |

*(Discharges OL-19.1 … OL-19.12.)*

### 3.3 Enforcement bindings for the defining standard

**SIG-CHART-013 (MUST).**

| Standard | Enforcement point |
|---|---|
| No unexplained dots | Every `PhysicalAsset` MUST have ≥1 supporting claim with a resolvable `EvidenceArtifact`; assets failing this are `candidate` status and are excluded from public device layers (§11.8, §43.5). |
| No unexplained edges | Every relationship instance MUST carry an edge type from the closed catalog (§12) and ≥1 supporting claim. Untyped edges are a schema error. |
| No silent overwrites | Claim storage is append-only (P3). The API MUST NOT expose any endpoint that mutates a claim in place. |
| No synthetic certainty | Confidence is drawn from a closed vocabulary with a machine-readable derivation (§10.6). Free-form numeric confidence is prohibited unless calibrated against a labelled set with published calibration (§10.7). |
| Every node has identity | Every entity has a SIG persistent identifier plus a crosswalk row per upstream identifier (§14). |
| Every state has time | Every claim carries the required temporal dimensions (§9.2); missing time is encoded explicitly, never as "now". |
| Every inference says it is an inference | Derived facts are stored in a physically separate namespace, carry `derivation_rule` + `derived_at` + `inputs[]`, and are labelled in API, UI, and exports (§30.2). |
| Every contradiction remains visible | `Contradiction` is a materialized entity with a lifecycle; resolution does not delete it (§31). |

### 3.4 The federation principle

**SIG-CHART-014 (MUST).** SIG MUST be designed for federation rather than appropriation
(OL-1.2-01, OL-ES-24). Specifically, SIG MUST:

1. preserve upstream identifiers;
2. ingest or reference upstream datasets where legally and technically permissible;
3. contribute corrections upstream when possible;
4. attach SIG-derived reconciliation claims separately from upstream claims;
5. make provenance visible;
6. expose missing links and contradictions;
7. generate research tasks that improve upstream sources as well as the graph.

**SIG-CHART-015 (MUST NOT).** SIG MUST NOT:

1. fork DeFlock's camera database into an independent competing dataset;
2. ask users to report the same camera twice;
3. replicate EFF's volunteer research workflow;
4. re-host Have I Been Flocked's plate-level search tool;
5. scrape normalized data while discarding provenance;
6. present itself as the authoritative replacement for existing civil-society projects.

*(Discharges OL-1.2-02 … OL-1.2-08.)*

**SIG-CHART-016 (MUST).** SIG's role is a **coordination and reconciliation layer across a
pluralistic ecosystem** (OL-1.2-09). §6 makes this operational as a per-project compact with an
enforced `ingestion_permitted` flag.

### 3.5 The six defining characteristics

**SIG-CHART-017 (MUST).** The graph MUST be:

| Characteristic | Concretely means | Section |
|---|---|---|
| **Vendor-agnostic** | No vendor name in any schema identifier, enum, or required field. Adding a vendor is data, never migration. | §11.2, §13.1 |
| **Technology-agnostic** | The technology vocabulary is extensible and versioned; ALPR is one member, not the root. | §13.1 |
| **Source-preserving** | Raw source form and an immutable capture are retained for every extracted claim. | §17 |
| **Temporal** | Every assertion carries the temporal dimensions of §9.2; nothing is stored as timeless present. | §9 |
| **Explicit about uncertainty** | Confidence, coverage, and contradiction are modelled, queryable, and rendered. | §10, §31, §32 |
| **Designed for federation** | Upstream ids, contribution-back, and non-competition are architectural, not editorial. | §6, §35 |

*(Discharges OL-ES-24.)*

### 3.6 Authority claim

**SIG-CHART-018 (MUST).** SIG's public authority claim is bounded and MUST be stated in these
terms wherever the project describes itself:

> SIG does not claim to know every surveillance device. It claims that for every fact it
> publishes, it can show where the fact came from, when it was observed, how it was normalized,
> what contradicts it, and how confident it is.

*(Discharges OL-22.2-01.)*

**SIG-CHART-019 (MUST NOT).** SIG MUST NOT represent itself as exhaustive or authoritative
where evidence is incomplete (OL-7.2-10). Every aggregate figure published by SIG MUST be
accompanied by its coverage denominator (§32.2).

### 3.7 No single source of truth

**SIG-CHART-020 (MUST).** The architecture MUST NOT designate a single source of truth. The
problem is inherently multi-layered: different facts are generated by different systems
(OL-22.1-01) —

| Fact | Generated by |
|---|---|
| physical location | field observation |
| purchase | procurement |
| contractual quantity | contract |
| active quantity | operator / vendor |
| sharing | configuration |
| actual use | audit log |
| legality | statute / court |
| policy | agency documents |
| abuse | investigation / litigation |
| replacement | future procurement |

— and therefore the correct architecture is **source-auditable reconciliation** (OL-22.1-02),
specified in Part V.

---

## 4. Goals and non-goals

### 4.1 Goals

**SIG-CHART-021 (MUST).** The system MUST serve all eight goals. Each is bound to the phase that
first satisfies it and to the metric that measures it.

| # | Goal | Means | First satisfied | Measured by |
|---|---|---|---|---|
| G1 | **Discover** | Identify surveillance deployments and infrastructure from heterogeneous public sources. | Phase 3 | New-deployment discovery rate; source coverage (§32.1) |
| G2 | **Reconcile** | Resolve duplicate organizations, devices, deployments, vendors, and claims across datasets. | Phase 5 | ER precision/recall vs gold set (§14.7); contradiction resolution rate (§32.5) |
| G3 | **Preserve provenance** | Make every material fact traceable to source evidence. | Phase 2 | % of published claims with a resolvable evidence artifact — target 100% (§32.3) |
| G4 | **Preserve time** | Record when a claim was true, when it was observed, and when it changed. | Phase 2 | Temporal-completeness check (§48); as-of query conformance |
| G5 | **Expose relationships** | Represent ownership, operation, access, data sharing, integration, procurement, and replacement as edges. | Phase 6 | Edge-type coverage; J-1 traversal passing |
| G6 | **Quantify incompleteness** | Make coverage gaps visible rather than implying completeness. | Phase 4 | Every published aggregate carries a denominator (§32.2) |
| G7 | **Coordinate research** | Turn contradictions and missing evidence into structured research tasks. | Phase 8 | Tasks generated; tasks closed; upstream contributions accepted (§32.6) |
| G8 | **Serve downstream users** | Provide stable, open exports/API primitives. | Phase 9 | API/export availability; documented downstream reuse |

Goal 8's audience is explicit and MUST be served by design, not incidentally: journalists;
researchers; civil-liberties organizations; local communities; policy analysts; mapping
applications; watchdog projects. §37–§39 map each to a surface.

*(Discharges OL-7.1-01 … OL-7.1-08.)*

### 4.2 Non-goals

**SIG-CHART-022 (MUST NOT).** SIG MUST NOT:

| # | Non-goal | Enforcement |
|---|---|---|
| N1 | Create a searchable database of ordinary people's movements. | No plate-level or trip-level storage in any tier (§43.2); schema contains no plate column. |
| N2 | Re-publish plate-level audit data merely because it is public. | Ingestion of audit exports produces aggregates only (§24.2); raw retained under restricted tier if at all (§17.5). |
| N3 | Track individual law-enforcement officers unless necessary for a documented accountability claim and consistent with a carefully developed policy. | The officer-naming test (§43.4) gates every person-named claim through review. |
| N4 | Infer private individuals' identities from cameras or radio observations. | Prohibited inference list (§30.3, SIG-RECON-051). |
| N5 | Encourage trespass, vandalism, interference, or destruction of surveillance equipment. | Content policy (§46.5); contributor guidance explicitly excludes it (§34.3). |
| N6 | Publish speculative exact locations of sensitive private residences based only on weak RF observations. | RF promotion rule (§43.5, SIG-PUB-013): residential-parcel candidates are never published at any precision. |
| N7 | Replace OpenStreetMap as the physical-device editing system. | SIG has no device-editing UI that writes to SIG-canonical geometry (§35.2). |
| N8 | Replace EFF's Atlas as the primary broad crowdsourced adoption-research project. | Federation compact (§6); corrections flow to Atlas (§35.3). |
| N9 | Replace HIBF as the specialist audit-log analysis project. | SIG stores structural aggregates, not a search corpus (§11.16). |
| N10 | Represent itself as exhaustive or "authoritative" when the evidence is incomplete. | SIG-CHART-019. |

*(Discharges OL-7.2-01 … OL-7.2-10.)*

**SIG-CHART-023 (MUST).** SIG MUST explicitly support research, journalism, policy analysis,
lawful field observation, and public-records work (OL-13.5-01), and MUST NOT provide
instructions for damaging, disabling, tampering with, or evading lawful enforcement in the
commission of wrongdoing (OL-13.5-02). §46.5 states the operable rules and addresses the
inherent tension honestly rather than pretending it does not exist.

**SIG-CHART-024 (MUST).** The project itself MUST NOT become a surveillance system (OL-13-00).
The bright-line default: SIG tracks public or institutionally relevant surveillance
infrastructure and organizational behavior, not ordinary people's movements (OL-13.1-01).

---

## 5. Scope

### 5.1 The initial wedge

**SIG-CHART-025 (MUST).** The first release MUST be narrowly excellent at **U.S. ALPR
infrastructure, modeled completely enough that the ontology naturally generalizes to broader
surveillance technology** (OL-16-01, OL-24-13).

The wedge is chosen because twelve conditions hold simultaneously (OL-16-02): rich OSM device
data; a DeFlock contributor ecosystem; Flock portal data; Eyes on Flock; HIBF; ALPR Watch;
historical Vigilant/EFF data; an active public-records movement; current procurement activity;
multiple vendors; strong network-sharing semantics; and device + software + policy + access all
present in one domain. No other surveillance technology offers all twelve.

**SIG-CHART-026 (MUST).** Initial technology scope MUST include at least: Flock;
Motorola/Vigilant; Rekor; Axon ALPR where data exists; Genetec ALPR; and unknown/other ALPR
(OL-16-03).

### 5.2 The generalization requirement

**SIG-CHART-027 (MUST).** The schema MUST support the non-ALPR extensions from day one
(OL-16-04). This is a hard constraint on Phase 2 and Phase 4, not a Phase 5 concern.

Concretely, the following MUST be representable in the Phase-4 schema even though they are not
populated until later phases: acoustic gunshot sensors as physical assets that are not cameras
(OL-4.5-02); capabilities with no physical asset at all, such as cell-site simulation
(OL-4.6-01) and mobile-device extraction (OL-4.8-01); reference databases as infrastructure
(OL-4.7-02); commercial data-access relationships with no locally owned sensor (OL-4.9-01); and
integration hubs that consume other systems (OL-4.10-02).

**SIG-CHART-028 (MUST).** A conformance test suite (`tests/ontology/generalization/`) MUST
assert that each of those constructs can be expressed in the current schema. It runs from
Phase 4 onward and fails the phase gate if the schema regresses to ALPR-specific assumptions.

**Rationale.** Flock is the ideal starting laboratory but the wrong permanent boundary
(OL-22.3-01). Vendor substitution is already occurring; a Flock-specific system would become
obsolete precisely when it became successful (OL-A.3). The lasting ontology is:

```
surveillance capability
      ↓
deployment
      ↓
assets / data / access
```

not `Flock camera`.

### 5.3 International scope

**SIG-CHART-029 (MUST).** The data model MUST be international from the beginning (OL-5-02),
even though the U.S. is the initial focus (OL-5-01). §11.1 (jurisdiction model), §11.2
(organization types as a namespaced vocabulary), §9.7 (multilingual labels), and §43.8
(jurisdiction-conditional publication rules) carry this requirement. Part X Phase 18 executes
the first non-U.S. adapter.

**SIG-CHART-030 (MUST NOT).** SIG MUST NOT invent a U.S.-only device schema (OL-2A-SUS-02).
The physical-device layer inherits OSM's global schema.

### 5.4 Explicitly out of scope

**SIG-CHART-031 (RATIONALE).** The following are out of scope for the entire specification and are recorded
so that they are not silently re-added:

| Out of scope | Why | Where the need is met instead |
|---|---|---|
| A plate-level or trip-level search corpus | Non-goal N1/N2 | HIBF |
| A device-editing UI writing to SIG-canonical geometry | Non-goal N7 | OSM / DeFlock |
| Real-time device liveness ("is this camera on right now") | §46.5 anti-misuse | Not provided |
| Individual-officer tracking as a product surface | Non-goal N3 | Not provided |
| Routing / navigation applications | Federation; already served | Drivers Against Flock |
| Field-of-view rendering as a source fact | Derived-facts rule (P-derived, §30.2) | Provided only as an explicitly labelled derived layer |
| Hosting others' raw sensitive corpora | OL-A.8 | Specialist projects retain custody |

---

## 6. The federation compact

**SIG-CHART-032 (MUST).** For every external project in the ecosystem, SIG MUST maintain a
machine-readable compact record governing the relationship, and the ingestion pipeline MUST
refuse to run a connector whose compact says ingestion is not permitted (§22.4).

The initial compact, derived from the outline's relationship table (OL-18-01 … OL-18-17) and
corrected/extended by research workstreams R1, R2, R3, R9 and R12, is specified in §22.2. Its
governing dispositions:

| Project | Their strongest role | SIG's relationship | Binding constraint |
|---|---|---|---|
| OpenStreetMap | Global physical-device commons | Upstream canonical device geography | ODbL (§42); never the canonical editing DB (N7) |
| DeFlock | ALPR discovery/reporting UX | Direct contributors upstream to OSM; link and reconcile | Do not fork (SIG-CHART-015.1) |
| Eyes on Flock | Portal discovery, aggregation, archival history | Partner / ingest / reference the portal temporal layer | Do not build a competing crawler before exhausting collaboration (§22.5) |
| Have I Been Flocked | Audit-log corpus and behavioral analysis | Partner; reference structural aggregates and evidence | Do not re-host plate-level search (N4/N9) |
| ALPR Watch | Reproducible FOIA normalization | Reuse methods, code, and data where compatible | Preserve their reason-code mapping semantics (§24.2) |
| EFF Atlas of Surveillance | Agency surveillance-adoption taxonomy | Primary seed for the deployment layer | Preserve source attribution; allow supersession (§23.3) |
| EFF Data Driven | Vigilant ALPR sharing history | Vendor-neutral ALPR network source | Priority ingestion for the vendor-neutral model (§23.6) |
| ALPR Accountability Atlas | Incident/legal/accountability records | Link and integrate events, preserving evidence semantics | Adopt their epistemic labels (§10.4) |
| ALPR Abuse Library / Kansas Watch | Curated index of published reporting | Link; a curated source index is valuable unnormalized | Do not force premature normalization (§10.9) |
| MuckRock | Public-records workflow and source files | Primary evidence substrate | Link to the exact released document (§17.2) |
| DocumentCloud | Document hosting and text | Evidence store, not a citation URL | Capture metadata per §10.3.2 |
| Drivers Against Flock | Privacy routing over OSM | Downstream consumer; do not compete | Publish reusable higher-order data (§38) |
| Flock Finder | RF-derived candidate discovery | Lead generation only | Never promoted to confirmed without §43.5 |
| Flock-You | Local RF detection | Observation lead, never automatic confirmation | Same |
| FlockReporter | Local ecosystem directory/coordination | Discover collaborators and local evidence | Ingest the directory (§33.7) |
| Local DeFlock / Eyes Off groups | Field research and civic action | Contributors, validators, consumers | Geographic research queues (§33.6) |
| Technopolice | European surveillance mapping/research | International model and future data source | Stage 6 (§Phase 14) |
| Surveillance under Surveillance | Global OSM visualization | Downstream/peer visualization | No competition |
| PanoptiCity | Coverage / field-of-view analysis | Possible downstream analytical consumer | Derived-fact discipline (§30.2) |

**SIG-CHART-033 (MUST).** Before any connector is written for a project in this table, Stage 0
outreach (§Phase 0, §35.1) MUST have been attempted and its outcome recorded in the compact —
including the outcome "no response", which is itself a recorded state that determines the
permitted ingestion posture.

---

## 7. Success criteria

**SIG-CHART-034 (MUST).** SIG's success MUST be measured partly by whether it makes other
projects stronger (OL-22.6-01), not solely by its own traffic or record count. The following are
tracked and published on the project's public metrics page (§39.8):

| Leverage measure | Target signal |
|---|---|
| DeFlock / OSM receives better operator attribution | Count of SIG-originated operator-attribution suggestions accepted upstream |
| Atlas receives newly documented deployments | Count of deployment corrections submitted and accepted |
| HIBF receives more targeted records submissions | Count of SIG-generated records requests filed and fulfilled |
| Local groups learn exactly which records are missing | Research tasks claimed and closed by local groups |
| Journalists locate primary evidence faster | Documented citations of SIG in published reporting |
| Researchers reproduce national analyses without rebuilding entity resolution | Downstream reuse of the entity-crosswalk export |

**SIG-CHART-035 (RATIONALE).** The intended end state is that SIG becomes **connective infrastructure for a
movement of independent researchers** (OL-22.6-02). Design decisions that increase SIG's
centrality at the expense of the ecosystem's resilience are to be rejected; §46.5 specifies the
continuity and succession commitments that follow from this, including SIG's role as archival
insurance for single-maintainer upstream projects.

---

# Part II — Domain model

## 8. Conceptual architecture

### 8.1 The six-layer model

**SIG-ONTO-001 (MUST).** SIG MUST be structured as six strictly ordered layers. Data flows
upward only. No layer may write to a layer below it. Each layer is independently
reconstructible from the layer beneath it, except L0, which is the ground truth of what SIG
observed.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ L5  PRESENTATION      product surfaces, API responses, exports, dossiers │
│                       — never stores anything; always regenerable        │
├──────────────────────────────────────────────────────────────────────────┤
│ L4  INFERENCE         derived facts: attribution candidates, access-path │
│                       closure, FOV geometry, network centrality          │
│                       — physically separate; labelled; droppable         │
├──────────────────────────────────────────────────────────────────────────┤
│ L3  RESOLUTION        the current-best view: for each (subject,          │
│                       predicate, as-of) a resolved value + confidence    │
│                       + rationale + supporting + dissenting claims       │
│                       — derived from L1+L2 by a versioned ruleset        │
├──────────────────────────────────────────────────────────────────────────┤
│ L2  ENTITY            resolved identities: organizations, deployments,   │
│                       assets, vendors, products, jurisdictions           │
│                       — identity only; carries no factual attributes     │
├──────────────────────────────────────────────────────────────────────────┤
│ L1  CLAIM             append-only assertions: subject, predicate, value, │
│                       raw value, temporal dimensions, evidence, method   │
│                       — the substance of the graph                       │
├──────────────────────────────────────────────────────────────────────────┤
│ L0  EVIDENCE          immutable content-addressed captures + artifact    │
│                       metadata + rights + acquisition provenance         │
│                       — write-once; never edited; never deleted silently │
└──────────────────────────────────────────────────────────────────────────┘
       ↑ cross-cutting: IDENTITY · VOCABULARY · RIGHTS · COVERAGE · LINEAGE
```

**SIG-ONTO-002 (MUST).** The layer boundaries MUST be enforced mechanically:

| Boundary rule | Enforcement |
|---|---|
| L0 is write-once | Object storage with immutability; DB role lacks UPDATE/DELETE on artifact content columns (§17.3). |
| L1 is append-only | Table-level revocation of UPDATE/DELETE; corrections are new rows with `supersedes` (§16.3). |
| L2 carries no facts | Entity tables contain identity, type, and crosswalk columns only. A schema test asserts no attribute columns exist that duplicate a predicate (§16.2). |
| L3 is derived | L3 tables are `TRUNCATE`-and-rebuild-able from L1+L2+ruleset. A CI job rebuilds L3 from scratch and asserts byte-identical output (§28.8). |
| L4 is separate and labelled | Distinct schema namespace `inference.`; every row carries `derivation_rule`, `derived_at`, `input_claim_ids[]` (§30.2). |
| L5 stores nothing | No product surface writes to L0–L4 except through the contribution pipeline, which itself enters at L0 (§34.4). |

**Rationale.** This structure is what makes the outline's invariants enforceable rather than
aspirational. "No silent overwrites" is a property of L1's append-only-ness. "Every inference
says it is an inference" is a property of L4 being a different namespace. "Provenance over
convenience" is a property of L2 being forbidden from holding attributes — there is nowhere to
put a fact except as a claim with evidence.

### 8.2 The critical separation: L2 holds no facts

**SIG-ONTO-003 (MUST).** Entity tables at L2 MUST NOT contain columns that assert facts about
the world. An `organizations` row contains an id, a type, crosswalk identifiers, and lifecycle
bookkeeping. It does **not** contain `camera_count`, `retention_days`, `is_active`, or even
`canonical_name` as a directly-writable authoritative value.

The canonical name of an organization is itself a claim, with a source, and it can be disputed.
This is not pedantry: the outline's own motivating example (OL-6.1-01) is that
"Los Angeles Police Department", "LAPD", and "Los Angeles Police Dept" are competing names
for one entity, and which one is canonical is an editorial judgment that must carry provenance.

**SIG-ONTO-004 (MUST).** For query ergonomics, L3 MUST publish denormalized read models that
*look* like conventional entity rows with attributes. These are materialized views over the
resolution layer, are regenerable, and MUST carry, for every attribute, a companion column or
adjacent structure exposing the confidence and the resolving claim id. A read model that
presents a value with no path to its provenance is non-conformant.

### 8.3 The domain layers (what the sources look like)

The outline organizes the ecosystem into source layers A–G. SIG's connector portfolio (§22–23)
MUST cover all seven, because each generates a *different kind of fact* that no other layer
generates (OL-22.1-01).

| Layer | Question it answers | Fact type generated | SIG connectors |
|---|---|---|---|
| **A — Physical infrastructure** | Where is a device? | Field-observed geometry and hardware attributes | OSM/Overpass, DeFlock linkage, RF candidate leads |
| **B — Vendor/official deployment metadata** | What does the operator say it has configured? | First-party configuration and rolling usage statistics | Flock transparency portals, Axon Community Connect, vendor pages |
| **C — Usage and audit behavior** | What did people actually do with it? | Behavioral aggregates and sharing configuration snapshots | HIBF, ALPR Watch, agency audit exports |
| **D — Agency adoption** | Which agency has which technology? | Reviewed OSINT adoption claims | EFF Atlas, EFF Data Driven, CCOPS inventories |
| **E — Accountability** | What went wrong, and what did institutions do? | Epistemically-labelled events | ALPR Accountability Atlas, Abuse Library, courts |
| **F — Records and primary evidence** | What is contractually and legally documented? | Authoritative primary documents | MuckRock, DocumentCloud, procurement, agenda systems |
| **G — Lead generation / field detection** | Where might there be something we do not know about? | Low-confidence candidates requiring promotion | Flock Finder / WiGLE, Flock-You, contributor reports |

**SIG-ONTO-005 (MUST).** No layer may be treated as authoritative over another by default.
Precedence is per-predicate and is specified in the resolution ruleset (§28.4), because
authority is predicate-relative: a contract is authoritative for contracted quantity and weak
for current active count; a portal is the reverse.

**SIG-ONTO-006 (MUST).** Layer G output MUST NOT enter L1 as an observation of a device. It
enters as a `CandidateAsset` claim with `evidence_tier = F` and MUST pass the promotion rule in
§43.5 before appearing in any public device layer. The required flow (OL-2G-FF-03) is:

```
radio observation → candidate surveillance asset → field verification /
public record / imagery → confirmed physical device → OSM
```

Note the terminal step: confirmed devices flow to **OSM**, not to a SIG-canonical device table
(N7, OL-2A-OSM-05).

### 8.4 What SIG stores versus what SIG references

**SIG-ONTO-007 (MUST).** For every source, the compact (§22.2) MUST record one of four custody
postures, and the connector MUST implement the one recorded:

| Posture | SIG stores | Example |
|---|---|---|
| **MIRROR** | A full local copy of the source data plus captures | Atlas CSV (CC-licensed), portal snapshots |
| **DERIVE** | Only aggregates/structural conclusions; raw stays upstream | HIBF audit corpora (OL-10.1E-02, OL-A.8) |
| **REFERENCE** | Identifiers and metadata only; content fetched at read time | OSM element geometry under a separable-layer posture (§42.3) |
| **LINK** | A citation and a capture-status record only | Paywalled scholarship; documents SIG may not archive (§42.3) |

**Rationale.** This is the mechanism by which the outline's federation principle and its
licensing constraints become executable rather than editorial. A connector cannot accidentally
mirror a source that the compact says may only be referenced, because the loader checks the
posture before writing.

### 8.5 The reconciliation core

**SIG-ONTO-008 (MUST).** The system's distinctive output is a **reconciliation**, not an
aggregation (OL-6.2-02). A reconciliation is a first-class, addressable, citable object that
states, for a subject and a predicate:

- every claim that bears on it, with source and time;
- the resolved value, or the explicit fact that it is unresolved;
- the confidence label and the machine-readable evidence counts that produced it;
- a human-readable rationale;
- the dissenting claims, preserved and visible;
- the research tasks that would close the gap.

The worked target (OL-6.2-01) that Part V must be able to produce verbatim in substance:

> Contract executed 2025-03-14 specifies 30 Falcon cameras. Transparency Portal reported 28
> active cameras on 2026-07-01. OSM contains 24 field-observed Flock ALPR nodes assigned to this
> agency as of 2026-08-20. Three additional candidate devices are unmapped to an operator. One
> local news story reports two relocations in June. Therefore, the graph currently estimates 28
> active contracted devices, 24 physically mapped, with 4 unresolved.

**SIG-ONTO-009 (MUST).** Note what that statement does *not* do: it does not declare a single
"true count". §29.1 defines the distinct count predicates precisely so that this statement is
expressible without collapsing them (OL-11.1-03, P11, P12).

---

## 9. Temporal semantics

The outline's requirement is stated once and is absolute: *never collapse observation time and
validity time* (OL-9.2-01). That single requirement, taken seriously, forces a richer temporal
model than the outline itself sketches. This section specifies it.

### 9.1 Why two dimensions are not enough

Conventional bitemporal modeling has two axes: **valid time** (when the fact was true) and
**transaction time** (when the database recorded it). SIG needs more, because SIG is not the
observer. SIG records what *someone else* observed, published, and SIG then retrieved.

Consider the outline's own example. A Flock portal is captured on 2026-08-20 and says
"25 cameras". The portal page says it was last updated 2026-08-01. SIG's crawler fetched it at
14:03 UTC on 2026-08-20 and the extraction ran on 2026-08-22 after a parser fix.

Collapsing these produces false statements. The only fact directly established is:

> On 2026-08-01, the Flock portal for agency X asserted a camera count of 25; SIG retrieved
> that assertion on 2026-08-20 and recorded it on 2026-08-22.

Whether 25 cameras were physically installed on any date is a *separate, weaker, derived*
question. The model must make it impossible to state the strong version by accident.

### 9.2 The five temporal dimensions

**SIG-TIME-001 (MUST).** SIG MUST model five distinct temporal dimensions. Each lives at a
specific layer; none may be substituted for another.

| # | Dimension | Question it answers | Layer | Storage |
|---|---|---|---|---|
| T1 | **Valid time** | When was this true *in the world*? | L1 claim | `valid_from`, `valid_to`, `valid_from_kind`, `valid_to_kind` |
| T2 | **Observation time** | When did the source observe or assert it? | L1 claim | `observed_at`, `observed_at_precision` |
| T3 | **Publication time** | When did the source publish the artifact carrying it? | L0 evidence | `published_at` on `evidence_artifact` |
| T4 | **Retrieval time** | When did SIG obtain the artifact? | L0 evidence | `retrieved_at` on `evidence_capture` |
| T5 | **Assertion (transaction) time** | When did SIG record this claim, and when did SIG stop asserting it? | L1 claim | `recorded_at`, `superseded_at` |

**SIG-TIME-016 (MUST).** Only **two** of the five dimensions are queryable `AS OF` axes:
T1 (valid) and T5 (assertion). T2 (observation) is an **ordering scalar** used by the resolution
engine to rank competing claims — it is not an axis you travel along. T3 and T4 belong to the
evidence layer and MUST NOT be copied onto claim rows; a claim that carries its own
`retrieved_at` has confused the artifact with the assertion. In the standard vocabulary: SIG is
**bitemporal in the query sense and tri-temporal in the record sense**. *(Corroborated by R6-F17,
R6-F19.)*

**SIG-TIME-002 (MUST).** T2 (observation) MUST NOT default to T3 (publication) or T4
(retrieval). Where a source does not state when it observed something, `observed_at` MUST be
NULL with `observed_at_unknown_reason` populated, and the resolution engine MUST treat the claim
as having observation time bounded above by T3 and below by nothing — it MUST NOT silently
substitute a timestamp.

**SIG-TIME-003 (MUST).** T1 (valid time) MUST NOT be populated by inference at ingestion. A
portal's "25 cameras" claim has `observed_at = 2026-08-01` and `valid_from`/`valid_to` NULL with
`valid_from_kind = 'unknown'`. Converting an observation into a validity interval is a
**resolution-layer** operation (§28) governed by predicate volatility (§28.3), and it happens at
L3, never at L1.

This is the single most-violated rule in comparable systems and the most important one here.

### 9.3 Encoding uncertain and open-ended time

**SIG-TIME-004 (MUST).** `valid_from` and `valid_to` MUST each be accompanied by a *kind*
discriminator drawn from a closed vocabulary. A NULL bound is never self-explanatory.

| Kind | Meaning | Example |
|---|---|---|
| `exact` | The bound is known to the stated precision. | Contract signed 2025-03-14 |
| `ongoing` | Known to still hold as of the latest evidence; no end observed. | Sharing edge still listed on the most recent portal capture |
| `unknown` | It ended or began, but SIG does not know when. | A deployment that clearly predates the earliest evidence |
| `before` | Known to be no later than the stated instant. | "Cameras were installed by the June council meeting" |
| `after` | Known to be no earlier than the stated instant. | "Installation began after contract execution" |
| `never` | The bound does not apply; the fact is atemporal. | A contract's signing date is an event, not an interval |

**SIG-TIME-005 (MUST).** `valid_to_kind = 'ongoing'` MUST NOT be interpreted as "true now". It
means "true as of the last observation, with no observed end". Every consumer — API, UI, export
— MUST render it with the observation date attached. "Currently sharing with 147 organizations"
is a non-conformant rendering; "sharing with 147 organizations as observed 2026-07-14" is
conformant. This directly implements P12 (installed is not active).

**SIG-TIME-006 (MUST).** Date precision MUST be explicit. SIG MUST support and preserve
imprecise dates using **EDTF (Extended Date/Time Format, ISO 8601-2)** semantics: year-only
(`2025`), year-month (`2025-03`), approximate (`2025-03~`), uncertain (`2025-03?`), and
intervals with unspecified components. The storage encoding is specified in §16.7. A source
that says "in early 2025" MUST NOT be stored as `2025-01-01`.

**Rationale.** Public records routinely give imprecise dates ("the department began using ALPRs
in 2019"). Silently sharpening them creates false precision, violating P4, and corrupts
lifecycle reconciliation (§29.4), which orders events by date.

### 9.4 As-of query semantics

**SIG-TIME-007 (MUST).** Every read path — API endpoint, export, and UI view — MUST accept two
independent as-of parameters and MUST default them explicitly rather than implicitly:

| Parameter | Axis | Meaning | Default |
|---|---|---|---|
| `as_of_world` | T1 | "…about the state of the world on this date" | today |
| `as_of_belief` | T5 | "…according to what SIG knew on this date" | now (latest) |

This yields the four questions the system must answer:

| `as_of_world` | `as_of_belief` | Question |
|---|---|---|
| today | now | What do we currently believe is true now? |
| past date | now | What do we now believe was true then? |
| today | past date | What did we believe, on that date, was true then? |
| past date | past date | What did we believe on date B about the state on date W? |

**SIG-TIME-008 (MUST).** The fourth form MUST work. It is what makes a published SIG citation
defensible: a journalist who cited SIG on 2026-09-01 must be able to reproduce exactly what SIG
said on 2026-09-01, even after SIG has since corrected itself. Every public page MUST expose a
belief-pinned permalink (§39.9).

**SIG-TIME-009 (MUST).** Correcting a past error MUST NOT destroy the record of having made it.
A correction sets `superseded_at` on the prior claim and inserts a new claim with
`supersedes = <prior id>` and a `correction_reason`. Queries at `as_of_belief` before the
correction MUST still return the erroneous value. This is required by P3 and by the takedown and
corrections procedure (§45.4).

### 9.5 Absence and the encoding of "unknown"

**SIG-TIME-010 (MUST).** The model MUST distinguish four epistemic states that are commonly and
wrongly conflated into NULL:

| State | Meaning | Encoding |
|---|---|---|
| `NOT_RESEARCHED` | SIG has not looked. | No claim exists; coverage record marks the subject/predicate unattempted. |
| `NO_EVIDENCE_FOUND` | SIG looked and found nothing. | A negative-coverage record naming the sources searched and when. |
| `EVIDENCE_OF_ABSENCE` | A source affirmatively asserts the thing does not exist. | A claim with a negative value and normal provenance. |
| `UNRESOLVED` | Evidence exists and disagrees; no resolution is defensible. | An L3 resolution row with outcome `UNRESOLVED` and the dissenting claims. |

**SIG-TIME-011 (MUST).** `NO_EVIDENCE_FOUND` MUST record *which* sources were searched, because
"not in the Atlas" and "not in the Atlas, not in any portal, and not in three years of council
minutes" are very different statements. This is the mechanism by which the outline's negative-
claims doctrine (OL-9.4-01, OL-9.4-02) becomes queryable rather than editorial.

**SIG-TIME-012 (MUST).** The API and UI MUST both render these four states distinguishably
(OL-9.4-03). Rendering `NOT_RESEARCHED` identically to `NO_EVIDENCE_FOUND` is non-conformant.

### 9.6 Temporal invariants

**SIG-TIME-013 (MUST).** The following MUST be enforced as database constraints or as pipeline
data-quality checks that fail the run, not as application-level conventions:

| Invariant | Rule |
|---|---|
| TI-1 | `valid_from <= valid_to` when both are `exact`. |
| TI-2 | `recorded_at <= superseded_at` when superseded. |
| TI-3 | `observed_at <= published_at` when both known, allowing a configurable tolerance for clock skew and time-zone-free source dates. |
| TI-4 | `published_at <= retrieved_at` when both known, same tolerance. |
| TI-5 | A claim MUST NOT have `observed_at` in the future relative to `recorded_at`. |
| TI-6 | For predicates declared mutually exclusive (§13.4 lifecycle states), the resolved intervals for one subject MUST NOT overlap at L3. Overlap at L1 is legal and is a contradiction, not an error. |
| TI-7 | A `supersedes` chain MUST be acyclic and MUST terminate. |
| TI-8 | Every claim MUST have at least one of `observed_at`, `published_at`, or an explicit `temporally_unanchored` flag with a reason. A claim floating free of all time is a data-quality failure. |

**SIG-TIME-014 (MUST).** TI-6's distinction is essential and is easy to get backwards.
*Contradictory claims at L1 are expected and are the point of the system.* Only the **resolved**
view at L3 must be internally consistent, and where it cannot be, it resolves to `UNRESOLVED`
rather than picking arbitrarily (P4, OL-6.5-01).

### 9.7 Multilingual and locale-sensitive temporal data

**SIG-TIME-015 (MUST).** All timestamps MUST be stored in UTC with the original source
representation preserved alongside. Source documents state dates in local time and in local
formats (`14/03/2025` is ambiguous between March 14 and unparseable depending on locale). The
raw string MUST be preserved per P2, and the parsed value MUST record the assumed locale and
time zone so that a later correction is possible.

---

## 10. The epistemic model

The outline states (§9) that SIG must be designed around the difference between fact,
observation, claim, inference, derived metric, and unresolved contradiction. This section
defines those distinctions as concrete objects with concrete rules. §28 defines the algorithm
that operates on them.

### 10.1 The evidence → claim chain

**SIG-EPIS-001 (MUST).** Every published material fact MUST be reachable by this chain, and the
chain MUST be traversable in both directions through the API and the UI:

```
Source (an upstream dataset, publisher, or records channel)
   └─ EvidenceArtifact        the identified document/dataset/page/record
        └─ EvidenceCapture    an immutable, content-addressed snapshot of it at a moment
             └─ Extraction    a versioned parse of a capture by a named method
                  └─ Claim    subject · predicate · value, with raw value and time
                       └─ Resolution      the current-best answer for that subject+predicate
                            └─ Presentation  what a user or API consumer sees
```

**SIG-EPIS-002 (MUST).** No shortcut through this chain is permitted. Specifically:

- A Claim MUST reference an Extraction, or be a `human_assertion` with a named author and a
  rationale, or be an `inference` living at L4. There is no fourth kind.
- An Extraction MUST reference exactly one EvidenceCapture.
- An EvidenceCapture MUST reference exactly one EvidenceArtifact and MUST carry a content hash.
- An EvidenceArtifact MUST reference exactly one Source and MUST carry a rights record (§42.4).

**Rationale.** This is the mechanical implementation of OL-24-18: *make the system reproducible
enough that a journalist can defend a graph claim by tracing it back to evidence.* If any link
is optional, the guarantee collapses to a convention, and conventions decay.

### 10.2 Source, EvidenceArtifact, and EvidenceCapture are three different things

The outline's `EvidenceArtifact` (OL-8.15) conflates three objects that must be separated,
because they change at different rates and carry different rights.

| Object | Identity | Mutability | Example |
|---|---|---|---|
| **Source** | The publisher/dataset/channel | Long-lived; its terms and license attach here | "Flock Safety transparency portals"; "EFF Atlas of Surveillance"; "MuckRock request #12345" |
| **EvidenceArtifact** | A specific addressable thing within a source | Its *content* may change over time; its identity does not | "The transparency portal at slug `hagerstown-md-pd`"; "the Atlas CSV"; "contract PDF, 14 pp." |
| **EvidenceCapture** | The bytes SIG obtained at a specific instant | **Immutable, forever** | "SHA-256 `ab12…` retrieved 2026-08-20T14:03Z, 412 KB, `text/html`" |

**SIG-EPIS-003 (MUST).** A transparency portal that reports 25 cameras today and 28 next month
is **one artifact with two captures**, not two artifacts. This is what makes portal diffing
(§29.7) and the "what did the portal say on date T" question (OL-2B-IND-02) expressible.

**SIG-EPIS-004 (MUST).** An artifact that *disappears* MUST be recorded as an event on the
artifact, not as a deletion. A vanished Flock portal is data (OL-2B-FP-03): the artifact gains a
`disappeared_observed_at`, its last capture remains, and a research task is generated. The
outline's Q18 (how to preserve deleted portals and inactive organizations) is answered by this
rule plus §17.6.

### 10.3 Field specifications

#### 10.3.1 `Source`

| Field | Type | Req | Notes |
|---|---|---|---|
| `id` | SIG id | ✓ | |
| `name` | text | ✓ | |
| `source_kind` | vocab | ✓ | `upstream_project`, `vendor_site`, `government_portal`, `records_channel`, `news_publisher`, `court_system`, `academic`, `community`, `contributor`, `commercial` |
| `homepage_url` | url | | |
| `operator_org_id` | SIG id | | Who publishes it |
| `default_tier` | vocab | ✓ | Default evidence tier (§10.4); overridable per artifact |
| `rights_id` | SIG id | ✓ | The rights record (§42.4) |
| `custody_posture` | vocab | ✓ | `MIRROR` / `DERIVE` / `REFERENCE` / `LINK` (§8.4) |
| `compact_status` | vocab | ✓ | Outreach/permission state (§22.2) |
| `ingestion_permitted` | bool | ✓ | Hard gate; connectors refuse to run when false |
| `robots_policy` | vocab | ✓ | `honor` / `honor_with_exception` / `not_applicable` |
| `crawl_budget` | struct | | Per-host rate limits (§26) |

#### 10.3.2 `EvidenceArtifact`

Discharges OL-8.15-02 and OL-2F-DC-02, corrected and extended.

| Field | Type | Req | Notes |
|---|---|---|---|
| `id` | SIG id | ✓ | |
| `source_id` | SIG id | ✓ | |
| `url` | url | | May be absent for offline records |
| `stable_locator` | text | ✓ | The identity within the source (portal slug, DocumentCloud id, docket number, OSM element ref, MuckRock request id) |
| `artifact_type` | vocab | ✓ | `contract`, `invoice`, `council_minutes`, `agenda_packet`, `audit_export`, `configuration_export`, `portal_page`, `policy_document`, `court_filing`, `news_article`, `dataset`, `press_release`, `presentation`, `email`, `photograph`, `osm_element`, `radio_observation`, `budget`, `grant_award`, `statute`, `regulation`, `screenshot`, `other` |
| `title` | text | | |
| `publisher_org_id` | SIG id | | Issuing organization (OL-2F-DC-02) |
| `published_at` | edtf | | T3 |
| `document_date` | edtf | | The date *of* the document, distinct from publication |
| `acquisition_method` | vocab | ✓ | `public_web`, `api`, `bulk_download`, `foia_request`, `leak`, `field_observation`, `contributor_upload`, `partner_feed`, `court_records`, `purchase`, `unknown` — internationalized per §13.8 |
| `records_request_id` | SIG id | | Links to the request that produced it (OL-2F-MR-02) |
| `page_count` | int | | |
| `primary_or_secondary` | vocab | ✓ | `primary`, `secondary`, `tertiary` |
| `default_tier` | vocab | ✓ | Overrides the source default |
| `rights_id` | SIG id | ✓ | |
| `sensitivity_class` | vocab | ✓ | §43.3; drives storage tier and public exposure |
| `capture_status` | vocab | ✓ | `captured`, `access_restricted`, `paywalled`, `link_rotted`, `not_attempted`, `refused_by_policy` |
| `disappeared_observed_at` | timestamptz | | Set when the artifact is confirmed gone |
| `supersedes_artifact_id` | SIG id | | Amended contracts, revised policies |

**SIG-EPIS-005 (MUST).** `capture_status` MUST be populated for every artifact. An artifact SIG
cited but could not retrieve is a legitimate, recordable state (see spot-check SC-07); it MUST
NOT be silently omitted, and it MUST NOT be treated as evidence of the same weight as a captured
artifact.

#### 10.3.3 `EvidenceCapture`

| Field | Type | Req | Notes |
|---|---|---|---|
| `id` | SIG id | ✓ | |
| `artifact_id` | SIG id | ✓ | |
| `content_hash` | text | ✓ | Multihash; algorithm recorded, not assumed (§17.2) |
| `retrieved_at` | timestamptz | ✓ | T4 |
| `retrieved_by_run_id` | SIG id | ✓ | Pipeline lineage (§21.6) |
| `http_status` | int | | |
| `media_type` | text | ✓ | |
| `byte_size` | bigint | ✓ | |
| `storage_uri` | text | ✓ | Object-store location (§17.3) |
| `storage_tier` | vocab | ✓ | `public`, `restricted`, `sealed` (§17.5) |
| `capture_method` | vocab | ✓ | `http_get`, `api_call`, `headless_browser`, `warc`, `manual_upload`, `screenshot`, `pdf_print` |
| `capture_tool_version` | text | ✓ | |
| `request_fingerprint` | jsonb | | Headers/params sent, for reproducibility |
| `redaction_applied` | bool | ✓ | Whether SIG applied redaction before storing (§43.7) |
| `parent_capture_id` | SIG id | | For derived captures (a redacted copy of a sealed original) |

**SIG-EPIS-006 (MUST).** Captures are immutable. A redacted derivative is a **new capture**
with `parent_capture_id` set, not an edit. This preserves OL-13.4-01's requirement for raw
private archival storage alongside a redacted public derivative.

#### 10.3.4 `Extraction`

This object does not appear in the outline and is required. It is what makes re-parsing
possible without destroying history (P2, P3, and the backfill requirement of §21.7).

| Field | Type | Req | Notes |
|---|---|---|---|
| `id` | SIG id | ✓ | |
| `capture_id` | SIG id | ✓ | |
| `method` | vocab | ✓ | `structured_parse`, `html_selector`, `pdf_text`, `pdf_table`, `ocr`, `tabular_import`, `llm_assisted`, `human_transcription`, `api_field_map` |
| `extractor_name` | text | ✓ | Module path |
| `extractor_version` | text | ✓ | Semantic version, pinned |
| `model_id` | text | | Required when `method = llm_assisted` (§25.3) |
| `prompt_version` | text | | Required when `method = llm_assisted` |
| `parameters` | jsonb | ✓ | Deterministic settings actually used |
| `extracted_at` | timestamptz | ✓ | |
| `run_id` | SIG id | ✓ | |
| `review_status` | vocab | ✓ | `unreviewed`, `sampled_ok`, `human_verified`, `disputed`, `rejected` |
| `superseded_by_extraction_id` | SIG id | | Set when re-extracted with a better parser |

**SIG-EPIS-007 (MUST).** Re-extracting a capture with an improved parser MUST produce a **new**
Extraction and a new set of Claims. The prior Claims are superseded (§9.4), not deleted, so that
a citation made against the old extraction remains reproducible.

#### 10.3.5 `Claim`

Discharges OL-8.16-02, extended.

| Field | Type | Req | Notes |
|---|---|---|---|
| `id` | SIG id | ✓ | |
| `subject_type` / `subject_id` | vocab / SIG id | ✓ | The entity the claim is about |
| `predicate` | vocab | ✓ | From the versioned predicate registry (§13.6) |
| `object_type` | vocab | ✓ | `literal`, `entity_ref`, `vocab_term`, `quantity`, `money`, `geometry`, `duration`, `interval`, `document_ref` |
| `object_entity_id` | SIG id | | When `object_type = entity_ref` |
| `value_json` | jsonb | ✓ | The normalized value, typed per predicate |
| `raw_value` | text | ✓ | **NOT NULL.** The source's literal text (P2, OL-2C-AW-05) |
| `raw_context` | jsonb | | Surrounding text, cell coordinates, page/bbox — the citation anchor |
| `unit` | text | | For quantities |
| `normalization_method` | vocab | | How raw → value |
| `normalization_version` | text | | Versioned and inspectable (OL-2C-AW-05) |
| `valid_from` / `valid_to` | edtf | | T1 |
| `valid_from_kind` / `valid_to_kind` | vocab | ✓ | §9.3 |
| `observed_at` | edtf | | T2 |
| `observed_at_unknown_reason` | vocab | | Required when `observed_at` is NULL |
| `value_kind` | vocab | ✓ | `value`, `somevalue` (a value exists but is unknown), `novalue` (asserted to have no value). Wikibase-derived; NULL cannot carry this distinction (§9.5, R6-F31) |
| `rank` | vocab | ✓ | `preferred`, `normal`, `deprecated`. A source's own ranking of its statements; deprecation preserves a known-wrong claim without deleting it |
| `asserted_by_person_id` | SIG id | | For human assertions |
| `assertion_rationale` | text | | Required for human assertions |
| `evidence_tier` | vocab | ✓ | §10.4 |
| `claim_polarity` | vocab | ✓ | `affirms`, `denies` — enables `EVIDENCE_OF_ABSENCE` (§9.5) |
| `qualifiers` | jsonb | | Scope qualifiers (Wikidata-style), e.g. "as reported by the vendor" |
| `derived_from_claim_ids` | SIG id[] | | Source-dependence chain (§28.6) — critical for not double-counting copied sources |
| `recorded_at` | timestamptz | ✓ | T5 |
| `superseded_at` | timestamptz | | T5 close |
| `supersedes_claim_id` | SIG id | | |
| `correction_reason` | vocab | | Required when superseding |
| `review_status` | vocab | ✓ | `unreviewed`, `machine_accepted`, `human_verified`, `disputed`, `retracted` |
| `sensitivity_class` | vocab | ✓ | §43.3 |
| `rights_id` | SIG id | ✓ | Inherited from artifact; drives export licensing (§42.4) |

**SIG-EPIS-008 (MUST).** `raw_value` is NOT NULL with no exceptions. If a claim has no
corresponding literal source text — because it is an inference — it does not belong at L1. It
belongs at L4.

**SIG-EPIS-009 (MUST).** `derived_from_claim_ids` MUST be populated whenever SIG ingests a claim
from a source that itself derived it from another source SIG also ingests. Several ecosystem
projects reuse each other's data. Without this field, three sources that all copied one portal
would appear as three independent corroborations, and the reconciliation engine would report
false confidence. §28.6 specifies the discount rule.

---
#### 10.3.6 `ClaimEvidence` — a claim has an evidence *set*, not a source

**SIG-EPIS-010 (MUST).** A claim MUST NOT hold a single `source` foreign key. It MUST reference
an evidence **set** through a join table in which each row carries a **role**. The outline's
`Claim.source` (OL-8.16-02) is a simplification that cannot express the situations SIG exists to
handle. *(Corrects OL-8.16-02; corroborated by R6-F33.)*

| Field | Type | Req | Notes |
|---|---|---|---|
| `claim_id` | SIG id | ✓ | |
| `extraction_id` | SIG id | | The parse that produced or supports this claim |
| `capture_id` | SIG id | ✓ | Denormalized for traversal without a join through extraction |
| `role` | vocab | ✓ | See below |
| `locator` | jsonb | | Page, bbox, cell, line, byte range, DOM path, CSV row — the *exact* anchor |
| `excerpt` | text | | The quoted span, subject to §43.7 redaction |
| `weight_note` | text | | Why this artifact bears on this claim, when non-obvious |

**Evidence roles:**

| Role | Meaning |
|---|---|
| `establishes` | The artifact directly states the claim. |
| `corroborates` | An independent artifact stating the same thing. |
| `contextualizes` | Supports interpretation without stating the claim. |
| `contradicts` | The artifact bears on this claim and disagrees with it. |
| `supersedes_basis` | The artifact is why a prior claim was corrected. |
| `attests_absence` | The artifact was searched and did not contain the fact (§9.5). |

**SIG-EPIS-011 (MUST).** The `contradicts` role is required and is not decorative. It allows a
single claim to carry, in its own evidence set, the artifact that undermines it — which is what
makes contradiction visible at the point of use rather than only in an aggregate view
(OL-6.5-01, OL-24-11).

**SIG-EPIS-012 (MUST).** Every `establishes` row SHOULD carry a `locator`, and MUST carry one
for artifacts over one page. "The contract says 42 cameras" is not evidence; "page 7, table 2,
row 3 of capture `sha256:ab12…`" is. The evidence viewer (§39.6) renders from this field, and
the extraction-quality gate (§25.3) fails LLM extractions that omit it.

---

### 10.4 Source reliability `R` — a property of the publisher, not the claim

**SIG-EPIS-013 (MUST).** The outline's Tier A–F (OL-9.1) MUST be retained as shorthand but MUST be
**redefined as a genre scale, not a reliability scale**, and crossed with three further axes before
it drives any resolution.

**The correction, stated plainly.** OL-9.1-01 places "signed contracts" and "direct field
observation" together in Tier A. But a signed contract is authoritative about what was *purchased*
and says nothing about what is switched on today; a field observation is authoritative about what
was *on a pole last Tuesday* and says nothing about who owns it. These artifacts are not equally
reliable — they are **reliable about different things**. Tier A therefore splits across two very
different reliability values once directness is factored out. *(R13; this is the correction the
outline most needs.)*

**SIG-EPIS-014 (MUST).** `R` MUST be assigned **per source in the registry**, with a written
justification, reviewed on a schedule — never re-judged per claim.

| `R` | Definition | Admiralty | Outline tier | Examples |
|---|---|---|---|---|
| `R1` | Legally-operative or system-of-record artifact produced by the party with authority and consequences for error | A | A | Executed contract; court filing; invoice; official device inventory; government open-data release |
| `R2` | First-party statement by the operating or vendor organization under its own name | B | A/B | Transparency portal page; agency policy PDF; council agenda packet; vendor or agency press release |
| `R3` | Reviewed specialist dataset with a published, checkable methodology | C | C | EFF Atlas; HIBF processed exports; Accountability Atlas; Eyes on Flock aggregations |
| `R4` | Professional reporting or research with editorial accountability but no published record-level method | C/D | D | Investigative article; academic paper; NGO report |
| `R5` | Community/volunteer observation from a structured collection process, individually unreviewed | D/E | E | An individual OSM/DeFlock node; a community photo report |
| `R6` | Heuristic, automated, or model-generated candidate with unresolved entity matching | F | F | RF/OUI match; LLM extraction; fuzzy name match |

**SIG-EPIS-015 (MUST).** A separate boolean `reliability_provisional` MUST exist for genuinely
**novel** sources, defaulting them to `R5` with the flag set. Novelty is not unreliability, and
conflating them (as a naive reading of Admiralty "F" would) unfairly penalizes new civic projects.

**SIG-EPIS-016 (MUST NOT).** SIG MUST NOT score a claim's *plausibility* against a prior
expectation of how much surveillance an agency "should" have. That is an editorial position, not a
measurement, and it would make the system's output a function of its authors' assumptions.

### 10.5 Claim directness `D` — the (genre × predicate) matrix

**SIG-EPIS-017 (MUST).** `D` MUST be read from a **published, versioned matrix** with one row per
artifact genre and one column per predicate. This is where "a Tier A contract is weak evidence for
current camera count" is encoded mechanically rather than left to judgment.

| `D` | Meaning |
|---|---|
| `D1` | The artifact is the authoritative record **of the fact itself** |
| `D2` | A first-party report of the fact |
| `D3` | Secondhand report, or a close proxy |
| `D4` | Establishes a *related* fact from which the target is a short inference |
| `D5` | Bears on the target only through a modelling assumption |
| `D6` | **Non-probative for this predicate — excluded from the admissible set** |

Illustrative rows (the full matrix ships with the ruleset):

| Artifact genre | `contract_signed_date` | `contracted_device_count` | `active_device_count` | `retention_days` | `configured_sharing_partner` |
|---|---|---|---|---|---|
| Executed contract PDF | **D1** | **D1** | D5 | D4 / D6 | D6 |
| Invoice | D3 | D2 | D4 | D6 | D6 |
| Transparency portal snapshot | D6 | D5 | **D1** | **D1** | **D1** |
| Council minutes / agenda packet | D2 | D2 | D4 | D3 | D4 |
| Agency written policy | D6 | D6 | D6 | **D2** (policy value) | D3 (declared) |
| OSM node set (field observation) | D6 | D5 | D3 (lower bound only) | D6 | D6 |
| Audit-log export | D6 | D6 | D4 | D6 | D4 (proves use, not configuration) |
| News article | D3 | D3 | D3 | D3 | D3 |
| Vendor default-settings page | D6 | D6 | D6 | D5 | D6 |

**SIG-EPIS-018 (MUST).** Two consequences are normative:

1. **A Tier-A contract is `D5` for `active_device_count`** and therefore cannot beat a `D1` portal
   snapshot on that predicate, regardless of tier. This discharges OL-9.1's requirement
   mechanically instead of rhetorically.
2. **`D6` is an admissibility filter, not a weight.** A portal snapshot contributes *nothing* to
   `contract_signed_date` — it is not weak evidence, it is not evidence. Excluding it is what
   prevents the resolver from ever emitting "the contract was signed around July 2026 (portal)."

### 10.6 Integrity `I`, currency `C`, and the composed weight `W`

**SIG-EPIS-019 (MUST).** `I` is assigned **mechanically** by the pipeline:
`I1` content-addressed archive stored with checksum, fetch timestamp, and HTTP status;
`I2` live URL recorded and retrievable at ingest but no durable archive;
`I3` secondhand transcription, screenshot without provenance, or an artifact SIG cannot re-fetch.

**SIG-EPIS-020 (MUST).** `C` MUST be derived **at query time** from the predicate's volatility class
and the claim's `observed_at` (§28.3). It MUST NOT be stored on the claim: a claim's currency
changes without the claim changing, which is precisely why resolutions must be recomputed rather
than cached indefinitely (§28.7).

**SIG-EPIS-021 (MUST).** Axes MUST compose by a **published ordinal table**, never by arithmetic on
invented numbers:

```
base:        R1→W4   R2→W3   R3→W3   R4→W2   R5→W2   R6→W1
directness:  D1 0    D2 0    D3 −1   D4 −2   D5 −2 (cap W1)   D6 EXCLUDE
integrity:   I1 0    I2 −1   I3 −2
currency:    C1 0    C2 −1   C3 −2   C4 −2 (cap W1)

upgrade, at most +1 total, never above W4:
  +1  machine-readable structured export AND extraction_confidence = EXACT
  +1  independently field-verified by a SIG curator with a logged verification event

W = clamp(W0..W4)
```

`W4` dispositive · `W3` strong · `W2` moderate · `W1` weak · `W0` non-probative (retained for
display, never resolving).

**SIG-EPIS-022 (MUST).** Free-form numeric confidence is **prohibited** unless calibrated against a
labelled set with published calibration (OL-9.3-01). Weight classes are ordinal and explainable;
"87% confidence" is neither.

### 10.7 The confidence vocabulary: three orthogonal fields, not one

**SIG-EPIS-023 (MUST).** SIG MUST publish **three orthogonal fields plus a status**, never one
fused token:

```
resolution_status : RESOLVED | UNRESOLVED | SUPERSEDED | WITHDRAWN
support           : CONFIRMED | STRONGLY_SUPPORTED | PROBABLE | WEAKLY_SUPPORTED | UNSUPPORTED
agreement         : UNCONTESTED | MINOR_DISAGREEMENT | CONTESTED | IRRECONCILABLE
currency          : CURRENT | AGING | STALE | HISTORICAL
```

**Why this replaces the outline's list.** OL-9.3-02 proposes
`confirmed / strongly supported / probable / unverified / contradicted / historical`. Four of those
are *support* levels, one is an *agreement* level, and one is a *currency* level. A single flat
enum therefore cannot express **"strongly supported but contested"** or **"confirmed but
historical"** — and in this domain those are the common and interesting cases. The three-field
model is a strict superset: every outline label is recoverable from a `(support, agreement,
currency)` triple. *(Corrects OL-9.3-02 while preserving all six labels.)*

`support` is computed **only** from the winning value's evidence:

| `support` | Condition |
|---|---|
| `CONFIRMED` | Winner has a `W4` claim, **or** ≥2 independent, method-distinct classes each at `W3`+ |
| `STRONGLY_SUPPORTED` | A `W3` claim, or ≥2 independent classes at `W2`+ |
| `PROBABLE` | Exactly one class at `W2`+ |
| `WEAKLY_SUPPORTED` | Best claim is `W1` |
| `UNSUPPORTED` | No admissible claim above `W0` (always co-occurs with `UNRESOLVED`) |

`agreement` is computed **only** from the dissent structure:

| `agreement` | Condition |
|---|---|
| `UNCONTESTED` | All admissible claims map to the same canonical value |
| `MINOR_DISAGREEMENT` | Dissent exists but is all `W1`/`W0`, or (numeric) within the predicate's tolerance |
| `CONTESTED` | Dissent at `W2`+ from ≥1 independent class |
| `IRRECONCILABLE` | Dissent at `W3`+ from ≥2 independent classes, or an open BLOCKING contradiction |

**SIG-EPIS-024 (MUST).** The API MUST always return all four fields. A one-word presentation label
MAY be derived from a published lookup for UI density, but MUST NEVER be the primary
representation.

**SIG-EPIS-025 (MUST).** Generated rationale text MUST NOT place a support term and an agreement
term in the same sentence. Mixing them is what produces sentences like "probably contested", which
readers cannot parse into a defensible meaning.

### 10.8 Source dependence

**SIG-EPIS-026 (MUST).** SIG MUST **declare** copying rather than infer it. Every claim carries
`derived_from_claim_ids` / `derived_from_source`, populated at ingest.

**Why SIG can do what the truth-discovery literature cannot.** Published data-fusion methods must
*infer* source dependence from a snapshot, because they cannot see inside their sources. SIG builds
its own intake and therefore **knows** which upstream a claim came from. This is a strict advantage
and SIG must exploit it: declared dependence is exact where inferred dependence is statistical.

**SIG-EPIS-027 (MUST).** Claims sharing an upstream origin MUST be grouped into a single
**independence class**, and corroboration MUST be counted **per class, not per claim**. Three
projects that all scraped one portal are one piece of evidence, not three.

**SIG-EPIS-028 (MUST).** Claims produced by the **same collection method** across different sources
MUST receive only partial independence credit, because a shared method shares a failure mode.

**SIG-EPIS-029 (MUST).** An **undeclared-copying detector** MUST run: claims from nominally
independent sources that match implausibly closely — including matching each other's errors — MUST
raise a review flag. Matching errors are near-proof of copying and are the cheapest available
signal.

### 10.9 Curated indexes need not be normalized

**SIG-EPIS-030 (MUST).** SIG MUST be able to hold a curated source index *as an index*, without
normalizing its entries into claims (OL-2E-AL-02). A well-maintained bibliography of reporting is
valuable on its own terms, and forcing premature normalization would both destroy that value and
manufacture low-quality claims.

---

## 11. Entity catalog

Every entity in the outline's §8 is present here. Several are split, because research showed the
outline's single object was carrying two or three incompatible jobs; every split is flagged.
Entities absent from the outline but required are marked **[NEW]** with the reason.

Recall SIG-ONTO-003: these tables hold **identity only**. The "fields" below are the entity's
**predicate surface** — the claims that may be made about it — not columns.

### 11.0 Entity index

| § | Entity | Outline § | Status |
|---|---|---|---|
| 11.1 | `Jurisdiction` | implied | **[NEW]** — the outline uses "jurisdiction" as a field without defining the object |
| 11.2 | `Organization` | 8.1 | Extended |
| 11.3 | `Person` | implied | **[NEW]** — tightly constrained; see §43.4 |
| 11.4 | `Product` | 8.3 | Extended |
| 11.5 | `Technology` | 8.4 | **Split** from `Capability` and `ConfigurationState` |
| 11.6 | `Capability` | 8.4 | **Split** — verb-grammar vocabulary |
| 11.7 | `Deployment` | 8.5 | Extended (four-track lifecycle) |
| 11.8 | `PhysicalAsset` | 8.6 | Extended |
| 11.9 | `CandidateAsset` | 2 Layer G | **[NEW]** — RF/heuristic leads must not enter the asset table |
| 11.10 | `DataSystem` | 8.7 | Extended |
| 11.11 | `Contract` | 8.10 | Extended |
| 11.12 | `FundingInstrument` | implied | **[NEW]** — grants and third-party funding; purchaser ≠ operator |
| 11.13 | `Policy` | 8.11 | Extended |
| 11.14 | `LegalInstrument` | ES-27 "laws and regulations" | **[NEW]** — the outline lists it but never models it |
| 11.15 | `ConfigurationState` | 8.12 | Promoted |
| 11.16 | `UsageAggregate` | 8.13 | Extended |
| 11.17 | `AccountabilityEvent` | 8.14 | Extended |
| 11.18 | `LegalProceeding` | 8.14 | **Split** from `AccountabilityEvent` |
| 11.19 | `RecordsRequest` | 2 Layer F | **[NEW]** — the outline specifies its fields but not the object |
| 11.20 | `Source` / `EvidenceArtifact` / `EvidenceCapture` / `Extraction` | 8.15 | **Split** four ways (§10.2) |
| 11.21 | `Claim` / `Resolution` / `Contradiction` | 8.16, 6.5 | Extended (§10.3, §16.4, §31) |
| 11.22 | `ResearchTask` | 12 | **[NEW]** — the outline describes the behaviour, not the object |
| 11.23 | `CoverageRecord` | 9.4 | **[NEW]** — required to make negative claims queryable |

---

### 11.1 `Jurisdiction` **[NEW]**

**Why it exists.** The outline treats "jurisdiction" as a string field on Organization,
Deployment, and elsewhere. That fails immediately: a city, the city government, and the city
police department are three different things, and a device inside city limits may be operated by
the county sheriff, the state police, or a university. Without a jurisdiction object, the
device-attribution workflow (§29.2) has nothing to reason over, and the international
requirement (§5.3) has nowhere to hang a non-US code system.

**SIG-ONTO-010 (MUST).** `Jurisdiction` MUST be a first-class entity with a self-referential
hierarchy, a pluggable national code system, and geometry.

| Predicate | Type | Notes |
|---|---|---|
| `jurisdiction_type` | vocab | `country`, `state_province`, `county`, `municipality`, `township`, `special_district`, `school_district`, `tribal`, `federal_region`, `judicial_district`, `metropolitan_area`, `neighborhood`, `unincorporated_area` — namespaced per country (§13.7) |
| `parent_jurisdiction` | entity_ref | Multiple parents permitted; hierarchies overlap (a city may span two counties) |
| `code_system` / `code` | vocab / literal | `us.census.geoid`, `us.fips`, `us.gnis`, `iso.3166-2`, `fr.insee`, `uk.ons`, `de.ags`, `wikidata.qid` — repeatable |
| `boundary` | geometry | MultiPolygon, 4326 |
| `boundary_source` | entity_ref | Which artifact the boundary came from; boundaries change |
| `name` / `name_lang` | literal / BCP-47 | Repeatable for multilingual labels |
| `valid_from` / `valid_to` | edtf | Jurisdictions incorporate, merge, and dissolve |

**SIG-ONTO-011 (MUST).** Jurisdiction geometry MUST be temporally versioned. Annexations are
common and a device's containing jurisdiction on the date it was observed may differ from today's.

---

### 11.2 `Organization`

Discharges OL-8.1-01, OL-8.1-02, extended.

**SIG-ONTO-012 (MUST).** `Organization` MUST be the single entity for **all** institutional
actors. "Vendor" is a **role**, not a subtype (§12.4). This resolves the outline's §8.2 note that
"a vendor is an organization but should have domain-specific relationships": the relationships
are edges, and the entity is not specialized.

| Predicate | Type | Notes |
|---|---|---|
| `canonical_name` | literal | **A claim, not a column.** Competing names are competing claims (§8.2) |
| `alias` | literal | Repeatable, with `alias_type` qualifier: `abbreviation`, `former_name`, `slug`, `misspelling`, `local_usage`, `legal_name`, `dba` |
| `name_lang` | BCP-47 | Multilingual labels |
| `organization_type` | vocab | Namespaced and extensible: `us.le.municipal_police`, `us.le.sheriff`, `us.le.state_police`, `us.le.university_police`, `us.le.transit_police`, `us.le.school_district_police`, `us.le.tribal_police`, `us.le.federal`, `us.gov.municipality`, `us.gov.county`, `us.gov.special_district`, `us.fusion_center`, `private.company`, `private.hoa`, `private.security_firm`, `private.bid`, `nonprofit`, `hospital`, `university`, `school_district`, `utility`, `transit_agency`, `vendor`, `data_broker`, `fr.police_municipale`, `fr.gendarmerie`, … (§13.7) |
| `parent_organization` | entity_ref | Time-bounded |
| `jurisdiction` | entity_ref | The jurisdiction it serves; may differ from where it is located |
| `identifier` | literal | Repeatable, qualified by `identifier_system`: `us.fbi.ori`, `wikidata.qid`, `gleif.lei`, `sam.uei`, `sam.cage`, `nces.leaid`, `ipeds.unitid`, `ntd.id`, `cms.ccn`, `muckrock.agency_id`, `flock.portal_slug`, `atlas.agency_name`, `osm.operator_string` |
| `government_domain` | literal | A `.gov`/`.us` domain is a strong deterministic match signal (§14.6) |
| `address` | structured | Repeatable, typed |
| `valid_from` / `valid_to` | edtf | Formation and dissolution |
| `succession` | entity_ref | Qualified `merged_into`, `split_from`, `renamed_from`, `absorbed_by` (§14.5) |

**SIG-ONTO-013 (MUST).** Organizations that are only ever observed inside a vendor network
listing — an HOA, an apartment complex, a small business — MUST be representable with a minted
SIG identifier and no external identifier, and MUST carry a `publication_review` flag routing
them through §43.4 before any public exposure. A small HOA is arguably a set of private
individuals wearing an institutional name, and SIG must decide case by case rather than by
default.

---

### 11.3 `Person` **[NEW]**, and tightly constrained

**SIG-ONTO-014 (MUST).** A `Person` entity MUST exist, because accountability events sometimes
require a named public official, and because SIG's own curators must be attributable. It MUST be
subject to the hardest constraints in the schema.

**SIG-ONTO-015 (MUST NOT).** A `Person` row MUST NOT be created for: a member of the public
observed by a surveillance system; a plate owner; an officer named only in a routine audit log
row; a private individual named in a network membership list. *(Non-goals N1, N3, N4.)*

**SIG-ONTO-016 (MUST).** Every `Person` row MUST carry a `public_interest_basis` claim that
passes the officer-naming test (§43.4) and MUST have been through human review before creation.
Person creation MUST NOT be reachable from any automated extraction path.

---

### 11.4 `Product`

Discharges OL-8.3-01, OL-8.3-02.

| Predicate | Type | Notes |
|---|---|---|
| `product_name` | literal | Time-bounded; products are renamed constantly (ShotSpotter→SoundThinking; COPLINK→CrimeTracer). Worked examples the model MUST carry, per OL-8.3-01: a fixed ALPR product; a vendor ALPR platform; a legacy ALPR network (Vigilant LEARN); an integration platform (Fusus); a face-recognition service (Clearview AI); a commercial location product (Fog Reveal); **a mobile-forensics product (Cellebrite UFED)**; an acoustic product (ShotSpotter) |
| `vendor` | entity_ref | Time-bounded — products change owners through acquisition |
| `implements_technology` | entity_ref | Many-to-many. Flock Falcon implements `alpr-fixed` **and** `vehicle-fingerprint-reid` |
| `can_offer_capability` | entity_ref | **Defeasible / marketing-level.** See SIG-ONTO-018 |
| `product_status` | vocab | `announced`, `available`, `end_of_sale`, `end_of_life`, `renamed`, `discontinued` |
| `successor_product` | entity_ref | |

**SIG-ONTO-017 (MUST).** A Product MUST NOT be equated with a Technology (OL-8.3-02). One product
implements many technologies; one technology is implemented by many products.

**SIG-ONTO-018 (MUST).** `Product --can_offer--> Capability` is **defeasible and marketing-level**.
`Deployment --actually_provides--> Capability` requires its **own evidence claim** and MUST NEVER
be silently inferred from the product default. Where SIG does infer it, the inference MUST be
materialized as a claim with `derivation = 'product_default'` and correspondingly low confidence.
*(R7-F7.1; this is P9 — "configured access is not actual use" — applied one level up: marketed
capability is not configured capability.)*

---

### 11.5 `Technology`

**SIG-ONTO-019 (MUST).** `Technology` MUST be a **three-level** hierarchy —
`domain` → `family` → `technology` — not a flat list. *(R7-F7.3; corrects OL-8.4-01.)*

The canonical vocabulary is **104 technologies / 36 families / 14 domains** (§13.1). Rationale:
a flat list cannot serve both rollup queries ("how many agencies have any biometric
identification?") and the discrimination the evidence supports (a covert trailer-mounted ALPR is
a different procurement, legal posture, and detection signature from a pole-mounted fixed one).

**SIG-ONTO-020 (MUST).** Every family MUST contain an `-unspecified` leaf. Most real evidence is
coarse: a contract saying only "license plate reader system" resolves to `alpr-unspecified`,
which is `broader_than {alpr-fixed, alpr-mobile, alpr-covert, alpr-trailer, alpr-checkpoint}`.
This is how incompleteness gets **represented** rather than guessed away (OL-9.4-01).

**SIG-ONTO-021 (MUST NOT).** An external source MUST NOT be forced down to the `technology` level.
Record the coarsest level the evidence supports and let the graph express the hierarchy.

**SIG-ONTO-022 (MUST).** Technology slugs MUST encode `family-discriminator`, never a vendor.
`flock-falcon` is a Product; `alpr-fixed` is a Technology.

---

### 11.6 `Capability` — a verb grammar, not a noun list

**SIG-ONTO-023 (MUST).** Capability slugs MUST follow the grammar `verb.object.scope`.
*(R7-F7.2; corrects OL-8.4-01, whose examples are all nouns.)*

A noun list cannot express scope or direction — which OL-8.8-03 says is the whole point ("do not
reduce all Flock network relationships to 'shares_with'; direction matters"). Concretely, a noun
called "ALPR network sharing" cannot represent *"federal organizations removed from national
lookup but state lookup intact"* — a real, dated 2025–2026 configuration change.

**Scope values:** `own`, `partner`, `state`, `region`, `national`, `commercial`, `subject`.

Capability classes (full vocabulary at §13.2):

| Class | Examples |
|---|---|
| Query | `search.plate.own`, `search.plate.state`, `search.plate.national`, `search.plate.commercial`, `search.face.*`, `search.location_history.subject`, `search.location_history.commercial`, `search.records.region` |
| Alerting | `alert.hotlist.own`, `alert.hotlist.federal`, `alert.hotlist.custom`, `alert.gunshot`, `alert.push_to.partner` |
| Live operations | `view.livestream.private_camera`, **`view.livestream.officer`**, `control.ptz.private_camera`, `dispatch.uas.autonomous`, `view.cad.partner` |
| Acquisition | `extract.device.logical`, `extract.device.physical`, `extract.cloud.account`, `locate.handset.rf`, `intercept.content.subject` |
| **Export / onward disclosure** | `disclose.results.to_partner`, `disclose.bulk.to_vendor`, `disclose.audit.public`, `resell.derived.commercial` |
| Governance (negative) | `restrict.offense_category`, `restrict.federal_sharing`, `restrict.immigration_query`, `audit.case_code.required` |

**SIG-ONTO-024 (MUST).** The **export / onward-disclosure** class is systematically absent from
every public surveillance taxonomy and MUST be present in SIG's. It is where the harm the project
exists to document actually occurs: not that an agency has a camera, but that what the camera
produces leaves the agency.

**SIG-ONTO-025 (MUST).** Governance capabilities are **negative** capabilities describing
restrictions. They MUST be modelled as `ConfigurationState` attributes with the capability derived
by negation, so that *"no evidence of a restriction" never silently becomes "restriction absent"*
(OL-9.4-01). `control.ptz.private_camera` is singled out for emphasis: the difference between
*seeing* a private feed and *steering* a private camera is the sharpest ownership/control boundary
in the model.

---

### 11.7 `Deployment`

Discharges OL-8.5-01, OL-8.5-02, extended. The Deployment is the bridge between organizational
adoption and individual devices.

| Predicate | Type | Notes |
|---|---|---|
| `deploying_organization` | entity_ref | |
| `product` / `vendor` | entity_ref | Both optional — a deployment may be evidenced before the product is known |
| `technology` | entity_ref | Repeatable; the coarsest level the evidence supports |
| `actually_provides_capability` | entity_ref | Evidentiary; see SIG-ONTO-018 |
| `procurement_state` | vocab | §13.4 track 1 |
| `physical_state` | vocab | §13.4 track 2 |
| `operational_state` | vocab | §13.4 track 3 |
| `authorization_state` | vocab | §13.4 track 4 |
| `litigation_hold` | boolean | A **flag**, coexisting with any state combination |
| `jurisdiction` | entity_ref | Where it operates, which may exceed the operator's jurisdiction |
| `contracted_device_count` … | quantity | The **distinct** count predicates of §29.1 — never one `quantity` |
| `proposed_at` / `approved_at` / `contracted_at` / `active_from` / `inactive_at` | edtf | Retained from OL-8.5-02; now derived from the state tracks and cross-checked |

**SIG-ONTO-026 (MUST).** A Deployment MUST be creatable with **no** product, **no** vendor, and
**no** physical asset. A Clearview licence, a Fog Reveal subscription, and a cell-site simulator
are all deployments with no roadside device (OL-ES-26, OL-4.6-01, OL-4.9-01).

---

### 11.8 `PhysicalAsset`

Discharges OL-8.6-01, OL-8.6-02, OL-8.6-03.

| Predicate | Type | Notes |
|---|---|---|
| `asset_type` | entity_ref | A Technology reference, not a free string |
| `geometry` | geometry | **Optional** (SIG-GEO-004) |
| `mobility` | vocab | `fixed`, `redeployable`, `vehicle_mounted`, `airborne`, `handheld`, `unknown` |
| `manufacturer` / `model` | entity_ref / literal | |
| `owner` / `operator` / `host` / `installer` … | entity_ref | The fourteen roles of §12.4 — **not** two fields |
| `deployment` | entity_ref | May be absent; this is the orphaned-device case |
| `first_observed` / `last_observed` | timestamptz | Drives staleness (P12) |
| `upstream_id` | literal | Qualified by system: `osm.node`, `osm.way`, `osm.relation`, `deflock.id`, … |
| `osm_version` | integer | Preserved per OL-2A-DF-06 |
| `sensitivity_tier` | vocab | §19.4 |
| `confirmation_status` | vocab | `field_confirmed`, `imagery_confirmed`, `record_confirmed`, `reported_unverified`, `candidate` |

**SIG-ONTO-027 (MUST).** The asset model MUST accommodate ways and relations, not only nodes
(SIG-GEO-003), and MUST NOT force acoustic sensors, drones, or RTCC facilities into a "camera"
abstraction (OL-4.5-02).

**SIG-ONTO-028 (MUST).** `operator` MUST be optional and its absence MUST be a first-class,
countable state. Measurement: only **19.1%** of the world's 144,312 mapped ALPRs carry an
`operator` tag — roughly **116,800 devices with no operator attribution** (SC-08.1). This is not
an edge case; it is the largest single body of addressable work in the project and the clearest
statement of what SIG adds that upstreams do not.

---

### 11.9 `CandidateAsset` **[NEW]**

**Why it exists.** Layer G (RF/OUI matches, unverified reports, model-generated candidates)
generates leads at a scale volunteers cannot match, and OL-2G-FF-02 is emphatic that these MUST
NOT be conflated with verified hardware. If candidates live in the same table as assets, they
will eventually be rendered on the same map.

**SIG-ONTO-029 (MUST).** Candidates MUST live in a **separate entity type** and MUST NOT appear in
any public device layer until promoted under §43.5.

| Predicate | Type | Notes |
|---|---|---|
| `detection_method` | vocab | `rf_oui_match`, `wigle_observation`, `imagery_detection`, `contributor_report`, `model_inference`, `count_gap_inference` |
| `location_estimate` | geometry | With `estimate_radius_m` — never a bare point |
| `identifier_prefix` | literal | OUI or similar; never a full MAC |
| `observation_count` | integer | Independent corroborations |
| `promotion_status` | vocab | `unreviewed`, `corroborated`, `promoted`, `rejected`, `suppressed_by_policy` |
| `residential_parcel_flag` | boolean | Set at ingestion; a true value bars publication outright (§43.5) |

**SIG-ONTO-030 (MUST).** The observation protocol of OL-2G-FY-02 MUST be captured in full:
observation; observer/source type; timestamp; location estimate; identifier prefix; confidence;
verification status.

---

### 11.10 `DataSystem`

Discharges OL-8.7-01, OL-8.7-02.

| Predicate | Type | Notes |
|---|---|---|
| `operator` / `vendor` / `product` | entity_ref | |
| `data_types` | vocab | Repeatable |
| `retention` | duration | **A ConfigurationState fact** where it varies per deployment (§11.15) |
| `system_scope` | vocab | `agency_local`, `vendor_cloud_single_tenant`, `vendor_cloud_shared`, `state`, `regional`, `federal`, `commercial` |
| `holds_data_collected_by` | entity_ref | Custody ≠ collection |

**SIG-ONTO-031 (MUST).** Reference databases MUST be representable as DataSystems even where SIG
holds no record of a sensor: `agency --can_query--> facial recognition system --searches_against-->
image/reference database` (OL-4.7-02). A commercial location dataset, an image gallery, and a
plate corpus are all infrastructure.

---

### 11.11 `Contract`

Discharges OL-8.10-02, extended.

| Predicate | Type | Notes |
|---|---|---|
| `buyer` / `seller` | entity_ref | |
| `amount` / `currency` | money | |
| `signed_date` / `start_date` / `end_date` | edtf | |
| `renewal_options` | structured | Count, term, auto-renew flag, notice window — the renewal-watch surface (§39.4) depends on this |
| `products` / `quantities` | entity_ref / quantity | |
| `document` | entity_ref | The EvidenceArtifact |
| `acquisition_channel` | vocab | `direct_award`, `competitive_rfp`, `sole_source`, `cooperative_piggyback`, `bundle_inclusion`, `free_trial`, `donation`, `grant_funded` |
| `parent_cooperative_contract` | entity_ref | The master award being ridden |
| `amends_contract` | entity_ref | Amendments are contracts |

**SIG-ONTO-032 (MUST).** `acquisition_channel` and `parent_cooperative_contract` are REQUIRED
model elements, not conveniences. Cooperative purchasing vehicles (Sourcewell, OMNIA, NASPO
ValuePoint, BuyBoard, TIPS, HGACBuy, Equalis, GSA) are a dominant acquisition channel for this
vendor category, and an agency riding a master award often generates **no local RFP at all**
(R4-F, R7-F7.43). A model that assumes a local competitive procurement will conclude, wrongly,
that no procurement evidence exists.

---

### 11.12 `FundingInstrument` **[NEW]**

**Why it exists.** Purchaser ≠ operator ≠ funder. Business improvement districts, HOAs, private
foundations, and federal grant programs routinely buy surveillance for agencies to operate
(R7-F7.41). This pattern most often escapes CCOPS ordinances, because those ordinances regulate
*agency acquisition*. A model with no funder is blind to it.

| Predicate | Type | Notes |
|---|---|---|
| `funder` | entity_ref | BID, HOA, foundation, federal program, state grant |
| `recipient` | entity_ref | |
| `instrument_type` | vocab | `federal_grant`, `state_grant`, `private_donation`, `bid_assessment`, `hoa_assessment`, `foundation_grant`, `asset_forfeiture`, `vendor_provided_free` |
| `program_name` | literal | e.g. Byrne JAG, UASI, COPS, Operation Stonegarden, HIDTA |
| `amount` / `award_date` / `period` | money / edtf | |
| `conditions` | literal | Strings attached that constrain use |
| `federal_award_id` | literal | USAspending award/sub-award id — the traceable link |

**SIG-ONTO-033 (MUST).** Federal grant → local surveillance is programmatically traceable via
USAspending sub-award data, which names LPR purchases by sheriffs under Byrne JAG and UASI
(R4). This path MUST be implemented, because it identifies deployments that appear in no local
procurement record.

---

### 11.13 `Policy`

Discharges OL-8.11-01, OL-8.11-02.

| Predicate | Type | Notes |
|---|---|---|
| `policy_type` | vocab | `retention`, `acceptable_use`, `warrant_requirement`, `immigration_restriction`, `reproductive_health_restriction`, `audit_requirement`, `external_sharing`, `data_minimization`, `oversight_reporting`, `sunset` |
| `applies_to` | entity_ref | Organization, Deployment, **or** Product — polymorphic and repeatable |
| `effective_from` / `effective_to` | edtf | |
| `adopting_body` | entity_ref | Council, chief, board — who adopted it matters for enforceability |
| `text` / `document` | literal / entity_ref | |
| `enforcement_mechanism` | vocab | `none_stated`, `internal_discipline`, `audit`, `external_oversight`, `statutory_penalty`, `contractual` |

**SIG-ONTO-034 (MUST).** `Policy` MUST NOT be merged with `ConfigurationState` (P10). Their
disagreement is a first-class finding, not a data-quality error (OL-8.12-02).

---

### 11.14 `LegalInstrument` **[NEW]**

The outline lists "laws and regulations" among what the graph must represent (OL-ES-27) but never
models them. Without this entity, the answer to Q-11 is half-missing and the international
requirement has nowhere to put an *arrêté préfectoral*, a CNIL decision, or an EU AI Act
obligation.

| Predicate | Type | Notes |
|---|---|---|
| `instrument_type` | vocab | `statute`, `ordinance`, `regulation`, `executive_order`, `court_order`, `consent_decree`, `dpa_decision`, `code_of_practice`, `prefectoral_order`, `directive` |
| `enacting_body` | entity_ref | |
| `jurisdiction` | entity_ref | |
| `citation` | literal | |
| `effective_from` / `effective_to` / `sunset_date` | edtf | |
| `constrains_technology` / `constrains_capability` | entity_ref | |
| `requires_authorization_of` | entity_ref | CCOPS-style approval requirements |

---

### 11.15 `ConfigurationState`

Promoted from OL-8.12 to a first-class, time-versioned, per-Deployment entity.

**SIG-ONTO-035 (MUST).** The **configuration-cut rule** determines what belongs here: *if a fact
can differ between two deployments of the same product with no change to hardware or software
version, it is configuration.* Retention days, hotlist topic subscriptions, sharing lists, offense
filters, audit settings, MFA, and live-stream permissions all fail that test and are therefore
configuration, not technology or capability. *(R7-F7.1.)*

| Predicate | Type | Notes |
|---|---|---|
| `retention_days` | duration **or ordinal bucket** | See SIG-ONTO-035a — MUST accept both |
| `subscribed_hotlist_topic` | vocab | Repeatable; includes federal NCIC topics |
| `sharing_partner` | entity_ref | Repeatable, directional |
| `state_lookup_enabled` / `national_lookup_enabled` | boolean | |
| `federal_sharing_enabled` | boolean | |
| `offense_category_filter` | vocab | Repeatable |
| `live_stream_permitted_to` | entity_ref | |
| `third_party_integration` | entity_ref | |
| `audit_case_code_required` | boolean | |
| `observed_via` | vocab | `portal`, `config_screenshot`, `foia_export`, `vendor_statement`, `contract_term` |

**SIG-ONTO-035a (MUST).** Retention MUST be representable as **either a duration or an ordinal
bucket**, and SIG MUST NOT fabricate a midpoint, a bound, or a point value from a bucket.

Real sources report retention categorically, not numerically. A statewide survey of 381 agencies
recorded it as `Less than 1 day` (30 agencies), `6 months or less` (17), `Between 6 months and
1 year` (76), `Between 1 year and 2 years` (56), `Between 2 years and 5 years` (29), and
`Greater than 5 years` (19) — **with overlapping and inconsistent bucket boundaries** (`6 months or
less` vs `Between 6 months and 1 year`).

Coercing `Between 1 year and 2 years` to `547 days` would manufacture precision the source never
had (P4) and would make two agencies look identical when the evidence does not say they are.
Comparison and reconciliation across mixed representations MUST therefore operate on **intervals**,
and a bucket that overlaps another MUST be treated as genuinely ambiguous rather than resolved by
convention.

**SIG-ONTO-036 (MUST).** Configuration is observed, never assumed. A vendor default MUST NOT
populate a deployment's configuration; a default may only produce an explicitly-labelled
`product_default` inference (§30.3).

---

### 11.16 `UsageAggregate`

Discharges OL-8.13-01, OL-8.13-02, OL-8.13-03.

| Predicate | Type | Notes |
|---|---|---|
| `searching_org` / `source_org` | entity_ref | Both required; direction is the point |
| `period` | tstzrange | Minimum granularity **one month** for published data (§18.4) |
| `count` | integer | Subject to small-cell suppression (§18.4) |
| `search_scope` | vocab | The capability scope values |
| `reason_category` | vocab | Normalized; `raw_value` retained (P2) |
| `audit_source_type` | vocab | `organization_audit`, `network_audit`, `portal_public_audit`, `event_log` — these are **not interchangeable** (§23.7) |
| `coverage_period` | tstzrange | What span the underlying audit actually covered — distinct from `period` |

**SIG-ONTO-037 (MUST NOT).** No per-search, per-plate, or per-person row may exist in this entity
or anywhere else in SIG (§18.1).

---

### 11.17 `AccountabilityEvent` and 11.18 `LegalProceeding`

Discharges OL-8.14-01, OL-8.14-02. Split because a lawsuit has a docket, parties, filings, and a
procedural posture that a "public hearing" does not, and flattening them loses the epistemic
distinctions OL-2E-AA-04 requires.

**`AccountabilityEvent`**

| Predicate | Type | Notes |
|---|---|---|
| `event_type` | vocab | `false_stop`, `wrongful_arrest`, `alleged_stalking_misuse`, `immigration_search_controversy`, `policy_violation`, `data_breach`, `security_finding`, `moratorium`, `contract_cancellation`, `public_hearing`, `audit_finding`, `regulatory_action`, `vendor_statement`, `local_regulation` |
| **`epistemic_status`** | vocab | **`alleged`, `reported`, `confirmed`, `adjudicated`, `policy_action`, `vendor_statement`, `disputed`, `retracted`** |
| `date` | edtf | |
| `organizations` / `deployments` / `technologies` | entity_ref | Repeatable |
| `affected_party_class` | vocab | Never a named private individual (N4) |
| `sources` | entity_ref | Repeatable, typed per OL-2E-AL-03 |

**SIG-ONTO-038 (MUST).** `epistemic_status` MUST be REQUIRED and MUST be rendered in every
surface. The graph MUST NOT flatten "X happened" when the evidence says "a plaintiff alleged X in
a pending lawsuit" (OL-2E-AA-05). This vocabulary is adopted directly from the ALPR
Accountability Atlas's model per OL-2E-AA-04.

**SIG-ONTO-039 (MUST).** An incident MUST be linkable to all six source classes of OL-2E-AL-03:
primary record; court record; agency statement; vendor statement; investigative article; advocacy
analysis — with the class recorded, so a claim resting only on advocacy analysis is
distinguishable from one resting on a court record.

**`LegalProceeding`**

| Predicate | Type | Notes |
|---|---|---|
| `court` / `docket_number` / `case_name` | entity_ref / literal | |
| `parties` | entity_ref | With `party_role` qualifier |
| `filed_date` / `disposition_date` | edtf | |
| `posture` | vocab | `filed`, `pending`, `dismissed`, `settled`, `judgment_plaintiff`, `judgment_defendant`, `on_appeal`, `consent_decree`, `class_certified` |
| `courtlistener_id` / `recap_id` | literal | |

---

### 11.19 `RecordsRequest` **[NEW]**

OL-2F-MR-02 specifies the fields but not the object. It is required because SIG must both *cite*
records requests as provenance and *generate* them as research tasks (§36).

| Predicate | Type | Notes |
|---|---|---|
| `requesting_party` | entity_ref | |
| `target_agency` | entity_ref | |
| `request_text` | literal | |
| `filed_date` / `response_date` | edtf | |
| `response_status` | vocab | `draft`, `filed`, `acknowledged`, `partially_fulfilled`, `fulfilled`, `denied`, `appealed`, `abandoned`, `no_responsive_records`, `fee_demanded` |
| `statutory_basis` | entity_ref | The LegalInstrument (state FOIA statute) |
| `platform` | vocab | `muckrock`, `nextrequest`, `govqa`, `justfoia`, `direct_email`, `portal`, `paper` |
| `external_id` | literal | MuckRock request id, NextRequest id |
| `released_documents` | entity_ref | Repeatable |

**SIG-ONTO-040 (MUST).** `response_status = 'no_responsive_records'` is a **positive finding**
that MUST feed the `NO_EVIDENCE_FOUND` coverage model (§9.5), not a null result to be discarded.
An agency stating on the record that it holds no ALPR contracts is evidence.

---

### 11.20 `ResearchTask` and 11.23 `CoverageRecord`

Specified at §33.2 and §32.2 respectively, where their behaviour is defined.

---

## 12. Relationship catalog

The outline's §22.4 argues the edges may matter more than the nodes. This section makes the edge
semantics precise enough that a network analysis over them means something.

### 12.1 Universal edge requirements

**SIG-ONTO-041 (MUST).** Every relationship instance MUST be:

1. **Directed.** Undirected surveillance edges are almost always a modelling error.
2. **Typed** from the closed catalog below. Untyped edges are a schema error.
3. **Time-bounded** with `valid_from`, `valid_to`, `valid_*_kind`, and `observed_at` (§9).
4. **Evidenced** — at least one supporting claim (SIG-CHART-013).
5. **Perspectival** — carrying which party asserted it, because A's claim about sharing with B and
   B's claim about receiving from A are different observations that may disagree.

### 12.2 The three sharing edge types that MUST NEVER be merged

**SIG-ONTO-042 (MUST).** Configured access, actual use, and declared policy are three distinct
edge types. They MUST NOT be merged, collapsed, or defaulted into one another. *(P9, P10,
OL-11.3-02.)*

| Edge type | Means | Typical evidence | Never implies |
|---|---|---|---|
| `configured_access` | The system is set up to permit it | `SharedNetworks.csv`; portal sharing sections; config screenshots | That anyone used it |
| `observed_use` | Someone actually did it | Network audit logs; usage aggregates | That it is still configured |
| `declared_policy` | Someone said it is permitted or forbidden | Agency policy; MOU; council resolution; vendor statement | That configuration matches |

**SIG-ONTO-043 (MUST).** Their disagreement is a **finding**, not an error. A written policy
prohibiting immigration-related use alongside a configuration enabling an immigration hotlist is
the paradigm case the outline demands be representable without editorial collapse (OL-8.12-02).
The contradiction detector (§31) MUST emit it, and the UI MUST show both.

**SIG-ONTO-044 (MUST).** Sharing edges observed in a **single snapshot** carry `valid_from_kind =
'unknown'` and `valid_to_kind = 'ongoing'`. A snapshot proves the state at observation; it proves
nothing about when the sharing began. Inferring a start date from first observation is prohibited.

### 12.3 Integration edges

**SIG-ONTO-045 (MUST).** `integrates_with` MUST NOT be a stored edge. It is permitted only as a
query-time rollup. If the question "what moves, and who initiates it?" can be answered, a specific
edge type MUST be used. *(R7 Part 5.)*

| Edge | Semantics | Discriminator |
|---|---|---|
| `ingests_feed_from` | B pulls a continuous stream from A; data comes to rest in B | Puller-initiated, continuous |
| `pushes_alerts_to` | A pushes discrete events to B; only events, not the corpus | Pusher-initiated, event-granular |
| `federates_search_to` | B may run a query against A's data; results return to B; **the corpus stays with A** | Query moves, corpus does not |
| `is_queryable_by` | The inverse of the above, asserted from A's side | Perspective — observed from different sources (portal vs contract) |
| `hosts_data_for` | A stores/controls infrastructure holding B's data | Custody, not access |
| `resells_data_from` | A sells access to data collected by B, where B is not party to A's customer relationship | Money + third-party corpus |
| `provides_platform_to` | A supplies the software surface B operates on | Vendor→operator, not data |
| `subscribes_to` | B pays for standing access to A's data/service | Money + standing access |
| `enrolls_asset_into` | An asset owned by A is registered into platform B | The object is a *device*, not data |
| `requests_data_from` | A can issue per-incident, consent-gated requests to B's users | Per-incident + consent |
| `distributes_list_to` | A pushes a watchlist to B for local matching; **matches do not return to A** | One-way list, no feedback |
| `authorizes` | A grants B legal permission to operate a capability; no data moves | Authority, not data |
| `replaced_by` / `succeeds` | B's deployment supersedes A's for the same capability at the same org | Temporal substitution |

**Required attributes on the data-bearing edges:** `initiator`, `transport`, `granularity`,
`data_comes_to_rest`, `scope`, `consent_gate`, `mechanism`, `terminable_by`, `termination_reason`.

**SIG-ONTO-046 (MUST).** Three rules follow from observed reality and are normative:

1. **Edges are per (product-pair, data-kind, direction), never per product-pair.** Two products can
   hold two integration edges in *opposite* directions simultaneously.
2. **Integrations are unilaterally terminable, mid-contract, and possibly partially.** `valid_to`
   MUST support `applies_to_cohort ∈ {all, new_customers_only, existing_customers_only}`. This is
   not hypothetical: Axon severed API interoperability with Flock effective 2025-07-24, which makes
   the outline's own Appendix C example (`Fusus integrates Flock ALPR`) a description of a
   *terminated* relationship (R7-F7.17).
3. **`distributes_list_to` MUST NOT be modelled as `federates_search_to`.** The direction of the
   *match result* is the entire civil-liberties question. Where a federal file populates a hotlist
   that a local agency matches against locally, the originating agency is not notified. Modelling
   it as federated search would invent a surveillance channel the evidence does not support.

### 12.4 The role model: fourteen roles, not four

**SIG-ONTO-047 (MUST).** The outline's `camera owner != data controller != police accessor !=
platform provider` (OL-4.1-05) is correct and insufficient. Fourteen roles MUST be modelled
separately. *(Extends OL-19.8's six.)*

| Role | Discriminating test |
|---|---|
| `owner` | Who could lawfully remove it? |
| `purchaser` | Whose money bought it? |
| `funder` | Whose grant or appropriation supplied that money? |
| `installer` | Who physically mounted it? |
| `host` | Whose pole, wall, or right-of-way is it on? |
| `operator` | Who aims it, tunes it, and responds to it? |
| `data_controller` | Who can change the retention setting? |
| `data_processor` | Could they lawfully use it for their own purposes? |
| `platform_provider` | Who would the capability disappear with? |
| `accessor_read` | Can they view without initiating a search? |
| `searcher` | Can they execute queries against the corpus? |
| `alert_recipient` | Do they get notified? |
| `auditor` | Can they see the search log as of right? |
| `regulator` | Can they prohibit it? |

**SIG-ONTO-048 (MUST).** Seven separations are load-bearing and MUST be independently
representable:

1. **owner ≠ operator** — private cameras effectively operated by a police RTCC.
2. **purchaser ≠ operator** — BID/HOA-purchased ALPRs operated by police. This pattern most often
   escapes surveillance-oversight ordinances, because those regulate *agency acquisition*.
3. **operator ≠ data_controller** — under a national-lookup configuration the searching agency is
   not the controller of the data it searches.
4. **data_controller ≠ platform_provider** — and this is **contested**. Vendors assert customers
   control the data; investigations dispute it. SIG MUST store the assertion and the
   contradiction, and MUST NOT adjudicate.
5. **searcher ≠ accessor** — a federal agency's search access granted by one local agency, over
   data owned by hundreds of uninvolved agencies, is a four-party fact.
6. **host ≠ owner** — for a rooftop acoustic sensor, disclosure of coordinates endangers the
   *host*, not the operator. **Therefore §43.3 coordinate sensitivity MUST be evaluated at the
   role level, not the asset level.**
7. **regulator ≠ funder ≠ authorizer** — these are routinely three different bodies.

### 12.5 `AccessRelationship`

Discharges OL-8.8-01, OL-8.8-02, OL-8.8-03.

| Attribute | Notes |
|---|---|
| `scope` | `own`, `partner`, `state`, `region`, `national`, `commercial`, `subject` |
| `direction` | **Required.** Never symmetric by default |
| `automaticity` | `automatic`, `manual_approval`, `per_incident_consent`, `legal_process_required` |
| `access_kind` | Which of the three edge types of §12.2 |
| `asserted_by` | Which party's evidence this rests on — enables asymmetry detection (§29.3) |

**SIG-ONTO-049 (MUST).** SIG MUST NOT reduce vendor network relationships to `shares_with`.
Direction, scope, automaticity, and kind are all required (OL-8.8-03).

### 12.6 Organizational and structural edges

`parent_of` / `child_of` (time-bounded); `merged_into`, `split_from`, `renamed_from`,
`absorbed_by` (§14.5); `participates_in` (fusion centers, task forces, cooperative purchasing
bodies); `has_jurisdiction_over`; `operates_within` (a deployment operating outside the operator's
own jurisdiction — a first-class fact, not an anomaly); `member_of_network`.

### 12.7 Provenance edges

`derived_from_claim`, `supersedes_claim`, `contradicts_claim`, `corroborates_claim`,
`extracted_from_capture`, `captures_artifact`, `published_by_source`.

### 12.8 Prohibited edges

**SIG-ONTO-050 (MUST NOT).** The following MUST NOT exist in any schema version:

| Prohibited | Why |
|---|---|
| Any edge from a `PhysicalAsset` to a natural person | Non-goal N4 |
| Any edge representing an individual's movement, trip, or sighting | Non-goal N1 |
| `shares_with` as an undifferentiated symmetric edge | OL-8.8-03 |
| `integrates_with` as stored data | §12.3 |
| A `Person`→`AccountabilityEvent` edge created by automated extraction | SIG-ONTO-016 |

### 12.9 Mapping the twelve power properties

**SIG-ONTO-051 (MUST).** SIG-CHART-005 requires the twelve power-generating properties
(OL-1.1-02) to be expressible. Their carriers:

| Property | Carrier |
|---|---|
| Sensor density | `PhysicalAsset` count per jurisdiction area (§32) |
| Historical retention | `ConfigurationState.retention_days` |
| Cross-jurisdictional sharing | `configured_access` edges with scope |
| Centralized search | `federates_search_to` + `search.*.{state,national}` capabilities |
| Automated alerts | `alert.*` capabilities; `distributes_list_to` |
| Integration with other databases | Integration edges §12.3 |
| Private-public access relationships | `enrolls_asset_into`; role separations §12.4 |
| Analytics | `analytics-inference` technology domain |
| Identity resolution | `search.face.*`, `search.person_records.commercial` |
| Institutional policy | `Policy` |
| Legal permissibility | `LegalInstrument`; `authorization_state` |
| Operator behavior | `UsageAggregate`; `observed_use` edges |

---

## 13. Controlled vocabularies

All vocabularies here are published as versioned SKOS concept schemes (§20.2) and are immutable
once published. The full term lists live in `ontology/vocab/` as the generated source of truth;
this section specifies their **structure, governing rules, and the terms that are load-bearing**.

### 13.1 Technology (`domain` → `family` → `technology`)

**SIG-ONTO-052 (MUST).** **14 domains, 36 families, 104 technologies** at v1.

**SIG-ONTO-052a (MUST).** Phase 1 acceptance MUST assert these counts against the generated
vocabulary artifact, and MUST assert that every technology term carries its distinguishing
criterion, evidence signature, and salience rating (SIG-ONTO-056). Counts asserted in prose but not
checked against an artifact are unfalsifiable, and this requirement exists to prevent that.

| Domain | Covers |
|---|---|
| `surveillance-vehicle` | ALPR (fixed, mobile, covert, trailer, checkpoint, unspecified), vehicle-fingerprint re-identification, commercial plate-data purchase |
| `surveillance-video` | Fixed CCTV, PTZ, private-camera registry / integration / per-incident request, video analytics, camera trailers |
| `body-worn-video` | **Body-worn cameras (`bwc-recorded`, `bwc-livestream`, `bwc-unspecified`); in-car video; live BWC streaming into an integration platform** |
| `biometric-id` | Face (1:1, 1:N, retrospective, live), iris, DNA/rapid DNA, tattoo, gait, voice |
| `acoustic` | Gunshot detection, acoustic sensing |
| `robotics-aerial` | UAS, drone-as-first-responder, tethered aerostat, persistent aerial |
| `robotics-ground` | UGV, robot dogs |
| `comms-intercept` | Cell-site simulators, tower dumps, wiretap, metadata interception |
| `device-forensics` | Logical/physical extraction, cloud-account extraction, exploit services |
| `data-acquisition` | Ad-tech location purchase, location-data subscription platforms, person-records brokers, utility records |
| `analytics-inference` | Predictive policing (place/person), risk assessment, behavioral analytics, social-media monitoring, OSINT platforms |
| `integration-platform` | RTCC platform, CAD/RMS integration, camera federation hub, third-party investigative platforms |
| `person-monitoring` | Electronic monitoring, jail-communications monitoring |
| `facility-screening` | Weapon detection, school surveillance |

**Governing rules:**

- **SIG-ONTO-053 (MUST).** Slugs are lowercase-hyphenated, **stable forever, never reused**.
  Retirement is `status: retired` + `superseded_by`, never deletion.
- **SIG-ONTO-054 (MUST).** Every family MUST have an `-unspecified` leaf (SIG-ONTO-020).
- **SIG-ONTO-055 (MUST).** Slugs encode `family-discriminator`, never a vendor.
- **SIG-ONTO-056 (MUST).** Each technology carries a **distinguishing criterion** (the single test
  separating it from its nearest sibling — two terms sharing a criterion are the same technology),
  an **evidence signature** (the literal strings that indicate presence in real contracts, portals,
  and reporting), and a **salience** rating `L`/`M`/`H`/`C`, where `C` marks technologies
  implicating a constitutional or statutory special category: biometrics, content of
  communications, immigration status, reproductive or religious activity, or First-Amendment-
  protected association.
- **SIG-ONTO-057 (MUST).** Two terms that external taxonomies treat as technologies are **not**
  technologies in SIG: a *fusion center* is an Organization type; an *RTCC* is both a Technology
  (`rtcc-platform`, the software) and an Organization sub-type (the unit), and the two MUST be
  distinguished.

**SIG-ONTO-057a (SHOULD).** Where SIG's own taxonomy must align with an external one, it SHOULD be
shaped after the **civil-liberties-argument** taxonomy rather than the procurement-visible one, with
the latter's categories as **children**.

The measurement supports this: of the procurement-oriented taxonomy's 12 categories, only **6
exact-match** the civil-liberties one; **five of the latter's technologies have no equivalent at
all** in the former — community surveillance apps, electronic monitoring, forensic extraction tools,
police access to IoT devices, and real-time location tracking — and one of the former's entries has
no counterpart because it is an *organization type*, not a technology. The civil-liberties taxonomy
is the broader and more structurally sound of the two, and it already covers the
data-access-without-hardware categories that OL-4.9 identifies as the future of the domain. So
`surveillance_camera_network` parents `camera_registry`, `rtcc_platform`, and `video_analytics`,
rather than the three sitting as siblings of it.

**SIG-ONTO-058 (MUST).** External taxonomies partition this space on **incompatible axes** — the
EFF Atlas by procurement-visible technology, EFF Street-Level Surveillance by civil-liberties
argument, and municipal surveillance-ordinance inventories by legal trigger. Crosswalks MUST
therefore be many-to-many with explicit SKOS mapping relations and a `lossy` flag (§20.3). SIG
MUST NOT adopt any external vocabulary as its primary key.

**SIG-ONTO-059 (MUST).** External vocabularies **change, and their changes carry negative
semantics**. The EFF Atlas retired its Ring/Neighbors category in March 2024 and removed ~2,530
data points, while adding Third-Party Investigative Platforms. Therefore *absence of a Ring data
point after March 2024 means "category retired", not "program ended"*. Every ingested external
vocabulary MUST carry a version stamp, and the coverage model (§32) MUST record category
retirements so that a disappearance is never read as a world change. *(R7-F7.4; a concrete
instance of OL-9.4-01.)*

### 13.2 Capability (`verb.object.scope`)

**SIG-ONTO-060 (MUST).** ~45 terms at v1, following the grammar of §11.6 (Capability). Scopes: `own`,
`partner`, `state`, `region`, `national`, `commercial`, `subject`. Classes: query, alerting,
live-operations, acquisition/extraction, **export/onward-disclosure**, governance (negative).

### 13.3 Evidence and epistemics

| Vocabulary | Terms |
|---|---|
| `source_reliability` (R) | `R1`…`R6` (§10.4) |
| `claim_directness` (D) | `D1`…`D6` (§10.5) |
| `artifact_integrity` (I) | `I1`, `I2`, `I3` |
| `currency` (C) | `C1` CURRENT, `C2` AGING, `C3` STALE, `C4` HISTORICAL |
| `weight_class` (W) | `W0`…`W4` |
| `confidence` | §10.6 |
| `evidence_role` | `establishes`, `corroborates`, `contextualizes`, `contradicts`, `supersedes_basis`, `attests_absence` |
| `epistemic_status` (events) | `alleged`, `reported`, `confirmed`, `adjudicated`, `policy_action`, `vendor_statement`, `disputed`, `retracted` |
| `absence_kind` | `not_researched`, `searched_not_found`, `evidence_of_absence`, `not_applicable` |
| `contradiction_state` | `uncontested`, `resolved_conflict`, `unresolved_conflict`, `insufficient` |
| `value_kind` | `value`, `somevalue`, `novalue` |
| `predicate_volatility` | `IMMUTABLE`, `GLACIAL`, `SLOW`, `MODERATE`, `FAST`, `VOLATILE` |

### 13.4 Deployment lifecycle — four orthogonal tracks

**SIG-ONTO-061 (MUST).** Lifecycle MUST be modelled as **four orthogonal state variables plus a
flag**, not one enum. *(R7 Part 7; corrects OL-6.7-01, which is one dimension short.)*

The proof that one enum is insufficient: a jurisdiction can simultaneously have a *cancelled
contract*, *hardware still physically mounted*, and *service unplugged*. That is three
simultaneous states on three different axes. A single enum forces a choice among them, and every
available choice produces a false statement.

**All fourteen of the outline's states are retained**; each is assigned to a track; ten are added.

**Track 1 — `procurement_state` (14):** `proposed`*, `rfp_issued`, `awarded`, `contracted`*,
`cooperative_piggyback`, `bundle_included`, `free_trial`, `donated`, `third_party_funded`,
`grant_funded_pending`, `renewed`, `nonrenewed`*, `canceled`*, `rejected`.

**Track 2 — `physical_state` (7):** `not_installed`, `installation`*, `installed`,
`installed_inactive`, `decommissioning`*, `removed`*, `destroyed_or_lost`.

**Track 3 — `operational_state` (6):** `inactive`, `pilot`*, `active`*, `expanded`*,
`restricted`*, `suspended`*.

**Track 4 — `authorization_state` (6):** `unauthorized`, `approval_pending`, `authorized`,
`authorized_expired`, `moratorium`, `sunset_by_ordinance`.

**Flag:** `litigation_hold` — coexists with any combination.

*(\* = a state named in OL-6.7-01.)*

**SIG-ONTO-062 (MUST).** `replaced` is **NOT** a state. It is the `replaced_by` edge (§12.3).
Modelling replacement as a state is precisely the error that lets a vendor swap read as a
surveillance reduction — the failure OL-22.5-02 and OL-6.7-02 exist to prevent.

**SIG-ONTO-063 (MUST).** `unknown` MUST be an admissible value on **every** track and MUST be the
default. This puts OL-9.4 and OL-6.6 in the schema rather than in prose.

**SIG-ONTO-064 (MUST).** `free_trial → operational:active` with **no procurement transition** is a
legal path. It is the mechanism by which surveillance capability is acquired with no procurement
paper trail at all, and it is the single most important edge in the state machine for SIG's
discovery mission.

**SIG-ONTO-065 (MUST).** Forbidden combinations MUST be **soft** constraints — flagged, never
rejected — because the interesting cases are real:

| Combination | Disposition |
|---|---|
| `physical=removed` ∧ `operational=active` | Impossible; flag as data error |
| `procurement=canceled` ∧ `physical=installed` | **Legal and common.** MUST NOT be blocked |
| `procurement=canceled` ∧ `operational=active` | Legal during wind-down; flag for a research task |
| `authorization=authorized` ∧ `physical=not_installed` | Legal; a high-value research task (authorized but not deployed) |

### 13.5 Organization type, evidence type, acquisition method, roles

Specified inline at §11.2, §10.3.2, and §12.4. All are namespaced and extensible per §13.7.

### 13.6 Predicates

**SIG-ONTO-066 (MUST).** Every predicate MUST be registered in `vocab_predicate` with:
`predicate_id`, `vocab_version`, `value_datatype`, `cardinality`, `definition`,
`skos_concept_iri`, **`volatility_class` and half-life** (§28.3), **`resolution_strategy`**
(§28.4), and its **row in the directness matrix** (§10.5).

**SIG-ONTO-067 (MUST).** A predicate MUST NOT be added without all of those, because a predicate
with no volatility class and no resolution strategy cannot be resolved — it can only be guessed at.

### 13.7 Internationalization of vocabularies

**SIG-ONTO-068 (MUST).** `organization_type`, `jurisdiction_type`, `acquisition_method`, and
`legal_instrument_type` MUST be **namespaced by country** (`us.*`, `fr.*`, `uk.*`, `de.*`) with a
shared abstract parent per concept. A US-shaped enum is prohibited (§5.3).

**SIG-ONTO-069 (MUST).** Every label-bearing term and every entity name MUST support repeatable
values tagged with **BCP 47** language tags. Transliterations carry a `transliteration_scheme`
qualifier.

### 13.8 Acquisition method, internationalized

`foia_request` is a US-specific term. The vocabulary MUST carry the abstract parent
`records_request` with national children (`us.foia`, `us.state_public_records`, `fr.cada`,
`uk.foi`, `eu.access_to_documents`), plus `no_equivalent_available` for jurisdictions with no
access regime — which is itself a coverage fact worth recording.

---

## 14. Identity architecture

The outline is unambiguous: entity resolution is *foundational infrastructure*, not ancillary
(OL-6.1-03), and identity must be solved before impressive graph visualizations (OL-24-04),
because bad entity resolution makes every network statistic misleading (P6).

### 14.1 The identity problem, stated concretely

One organization appears as: `Los Angeles Police Department`, `LAPD`, `Los Angeles CA PD`,
`City of Los Angeles Police Dept.`, `Los Angeles Police Dept` (OL-6.1-01). Across sources, the
identifiers do not align: vendor portal organization names, EFF Atlas agency names, ORI codes, OSM
`operator` strings, procurement customer names, records-platform jurisdiction records, police
rosters, and court documents each use a different convention (OL-6.1-02).

### 14.2 Per-class canonical identifiers (Q9, Q10, Q11, Q12)

**SIG-IDENT-001 (MUST).** Every organization class MUST have a designated canonical identifier
scheme; where none exists, SIG mints a surrogate under §14.4.

| Organization class | Canonical identifier | Source | Coverage |
|---|---|---|---|
| US law-enforcement agency | **ORI9** | FBI CDE agency registry, per-state endpoints | Broad but not total; excludes non-LE |
| US law-enforcement (crosswalk to geography) | **LEAIC** (ORI ↔ FIPS ↔ census place) | ICPSR | **Manual acquisition** — not automatically fetchable |
| Municipality / county / state | **Census GEOID** | Census Gazetteer + TIGER/Line | Complete for US |
| Named place | **GNIS feature id** | Census `ANSICODE` | Complete |
| School district | **NCES LEAID** | NCES | Complete |
| University | **IPEDS UNITID** | IPEDS | Complete |
| Transit agency | **NTD ID** | FTA | Complete |
| Hospital facility | **CMS CCN** (preferred), NPI secondary | CMS | Good |
| Corporate entity | **GLEIF LEI** | GLEIF golden-copy (CC0) | Public companies and many private |
| Federal contractor | **SAM UEI** (+ legacy DUNS) | USAspending (keyless) | Complete for federal awardees |
| Any entity, cross-project | **Wikidata QID** | Wikidata | Excellent for vendors; **weak for US agencies** |
| Non-US jurisdiction | ISO 3166-2, INSEE, ONS, AGS + **GeoNames id** | national sources | Varies |
| Everything else | **SIG surrogate** | §14.4 | — |

**SIG-IDENT-002 (MUST).** ORI codes MUST be validated against `^[A-Z0-9]{9}$` and MUST NOT be
parsed on the assumption that positions 1–2 are a USPS state code. A `ucr_state_code ↔
usps_state_code` reference table is REQUIRED, containing at minimum `NB→NE` and `GM→GU`.

**SIG-IDENT-003 (MUST).** ORIs whose ninth character is alphabetic MUST be flagged as possible
civil/applicant ORIs and MUST NOT be auto-linked to a surveillance-operating organization without
a second corroborating source.

**SIG-IDENT-004 (MUST).** Agency-registry latitude/longitude MUST be stored with
`geometry_precision = 'organization_centroid_or_unknown'` and MUST NOT be used for point-in-polygon
jurisdiction assignment or as an organization address. Using an agency centroid as a device
location would be a fabrication.

**SIG-IDENT-005 (MUST).** GEOIDs MUST be stored as **fixed-width strings** with a length check,
and every jurisdiction row MUST carry an explicit `level`, because 7-character GEOIDs are ambiguous
across place, county-subdivision, elementary school district, and school-district-administrative
levels.

**SIG-IDENT-006 (MUST).** `Jurisdiction.identifiers` and `Organization.identifiers` MUST be sets
of `(scheme, value)` pairs, never single columns.

**SIG-IDENT-007 (MUST).** Wikidata QIDs MUST be recorded where available but MUST NOT be depended
on for coverage of US law-enforcement agencies. For **vendors**, by contrast, they are strong:
`manufacturer:wikidata` is present on 83.4% of the world's mapped ALPRs (SC-08.2).

**SIG-IDENT-008 (MUST).** Any ingest job returning **zero** records for a jurisdiction MUST fail
the run rather than persist a zero, and MUST distinguish `absent` from `not observed`. A silent
zero is how coverage metrics become lies.

### 14.3 Organization taxonomy and the municipality/department distinction

**SIG-IDENT-009 (MUST).** A municipality and its police department MUST be **distinct
organizations** joined by `parent_of`. They have different identifiers, different legal capacities,
and frequently different surveillance postures — the city signs the contract, the department
operates the system.

**SIG-IDENT-010 (MUST).** Organizations MUST be classified on **two independent axes**:
`organization_class` (what kind of body it is) and `operating_relationship` (how it relates to the
surveillance in question). A university is a class; "purchaser but not operator" is a relationship.

**SIG-IDENT-011 (MUST).** Agency names containing a colon MUST be parsed into a parent
organization plus a local unit, and the parent MUST be materialized as its own Organization.

### 14.4 Surrogate identity for organizations with no external identifier (Q12)

**SIG-IDENT-012 (MUST).** Organizations with no external canonical identifier — HOAs, apartment
complexes, small businesses, private security firms appearing only in a vendor network list — MUST
receive a SIG-minted surrogate with a stored, **immutable** `identity_basis`:
`{normalized_name, org_class, place_geoid, address_hash, first_seen_source_ref, first_seen_at}`.

**SIG-IDENT-013 (MUST).** Address disambiguation MUST emit tiered keys: K1 (TIGER line + side),
K2 (block GEOID), K3 (tract GEOID), K4 (place GEOID). **K1/K2 may support matching; K3/K4 are
blocking-only** and MUST NOT be used as evidence of identity.

**SIG-IDENT-014 (MUST).** An organization that fails the publicity tests of §43.4 MUST NOT be
published by name. It MUST be represented publicly by an **aggregate count within its
jurisdiction**, with the full record retained privately. Network edges to suppressed nodes MUST
remain publishable in aggregate, so that the *shape* of private participation stays visible even
where the participants are not named.

**Rationale.** This is the honest resolution of a real tension. "Forty-seven residential
associations in this county share camera access with the police department" is exactly the kind of
structural fact SIG exists to surface. Naming a specific twelve-household HOA is closer to naming
twelve families. The aggregate preserves the finding; the suppression preserves the people.

**SIG-IDENT-015 (MUST).** Vendor portal slugs MUST be parsed by a documented, versioned grammar
rather than by ad-hoc splitting, with vendor-internal test organizations excluded by an explicit
denylist. Slug parsing is a *hypothesis generator*, never an identity assertion.

### 14.5 Temporal identity: merges, splits, renames, dissolutions (Q29)

**SIG-IDENT-016 (MUST).** Organizational change MUST be modelled as **reified
`OrganizationRelation` records** carrying valid time and transaction time, using a seven-value
vocabulary: `same_as`, `succeeded_by`, `merged_into`, `split_into`, `absorbed`, `parent_of`,
`acquired`.

**SIG-IDENT-017 (MUST).** A pure **rename** MUST produce a new organization *version* and an alias
with a `valid_to`. It MUST NOT produce a succession relation and MUST NOT produce a new identifier.
Renaming is not succession, and conflating them fragments the entity's history.

**SIG-IDENT-018 (MUST).** `Organization.status` MUST use `active | inactive | withdrawn |
suppressed`, where `withdrawn` means the entity was created in error and `suppressed` means it
exists but is not publishable (§14.4).

**SIG-IDENT-019 (MUST).** Five worked cases MUST each exist as a test fixture: a police department
disbanded and absorbed by a county sheriff; two departments merging into a new one; a department
splitting; a pure rename; and a vendor acquisition transferring product ownership.

### 14.6 The resolution cascade (Q27, Q28)

**SIG-IDENT-020 (MUST).** Matching MUST proceed as a **six-tier cascade**, deterministic first.
Tiers 0–3 MAY auto-write. **Tiers 4 and 5 MUST create `PROPOSED` claims and enqueue human review.**
Tier 6 MUST NOT persist per-pair records.

| Tier | Rule | Disposition |
|---|---|---|
| 0 | Exact shared canonical identifier (ORI9, GEOID, LEI, UEI, QID) | Auto-write |
| 1 | Exact upstream-id crosswalk already established | Auto-write |
| 2 | `normalized_name + state + class`, with a **data-generated** collision exclusion list | Auto-write |
| 3a | Government-domain match, with a shared-hosting denylist, domain from a Tier-A/B source | Auto-write |
| 3b | Exact address key K1 + normalized name | Auto-write |
| 4 | Probabilistic match above the review threshold | **Review queue** |
| 5 | Model-assisted or weak-signal candidate | **Review queue** |
| 6 | Below threshold | Discard; no per-pair record |

**SIG-IDENT-021 (MUST).** The probabilistic matcher MUST be **Splink 4** (MIT) on a DuckDB
backend. AGPL-licensed and proprietary matchers are excluded by SIG-STORE-002.

**SIG-IDENT-022 (MUST).** `normalize_org_name()` MUST be a **pure, deterministic, versioned**
function with a committed test-vector suite that runs in CI. It MUST collapse "Sheriff's Office"
and "Sheriff's Department" to one canonical suffix. Acronyms (LAPD, NYPD, LASD, CHP…) MUST be
resolved by **exact lookup** against an `acronym_alias` table and MUST NEVER be fuzzy-matched —
fuzzy-matching acronyms is how two unrelated agencies with similar initials get merged.

**SIG-IDENT-023 (MUST).** Blocking rules MUST be sized before use and rejected above a documented
comparison ceiling. Blocking on suffix alone or state alone is prohibited.

**SIG-IDENT-024 (MUST).** Trigram similarity MAY power an online candidate-search path but MUST
NOT be used as a decision score.

**SIG-IDENT-025 (MUST).** Every match MUST record `match_tier` and `match_evidence`, and for
probabilistic matches the match weight **and its per-comparison decomposition**, surfaced in the UI
as the confidence explanation. An unexplainable merge is a violation of the defining standard.

**SIG-IDENT-026 (MUST).** LLMs MAY generate **review rationales** for the human queue but MUST NOT
write to the graph. Model id and prompt version MUST be logged with each human decision. *(Q28.)*

### 14.7 Quality gates

**SIG-IDENT-027 (MUST).** A **gold-standard label set** MUST be constructed by stratified
blocked-pair sampling across match-weight bands, with double adjudication reporting Cohen's κ, a
three-value label vocabulary, written adjudication rules, and a **frozen holdout**. It MUST be
versioned data with per-label provenance.

**SIG-IDENT-028 (MUST).** Every ER run MUST report pairwise precision/recall/F1 at each tier
boundary and B-cubed cluster precision/recall on the holdout. **Auto-write tiers MUST be
automatically demoted to review if holdout precision falls below the published threshold.**

**SIG-IDENT-029 (MUST).** Cluster-shape alerts MUST fire for implausible clusters — a municipal PD
or sheriff cluster above a size threshold, or a cluster joined by a single bridge into components
that are each substantial. These are the signatures of a bad merge.

**SIG-IDENT-030 (MUST).** No network-analytics surface may ship before these gates pass (P6,
§14.7). The UI MUST carry an ER-quality disclosure wherever centrality or hub statistics appear.

### 14.8 Public identifiers and stability (Q37)

**SIG-IDENT-031 (MUST).** SIG MUST mint persistent public identifiers of the form
`sig:<type>:<uuidv7>`, dereferenceable at `https://<host>/id/<type>/<uuid>` with content
negotiation (HTML, JSON-LD, RDF).

**SIG-IDENT-032 (MUST).** Public identifiers MUST be **stable across cluster changes**. When a
cluster splits or merges, the surviving identifiers MUST be preserved and the change recorded as an
explicit, dated **merge/split event** with `redirects_to` or `split_into` pointers and tombstones.
An identifier MUST NEVER be silently reassigned to a different real-world entity — that is the one
failure that would poison every downstream citation.

**SIG-IDENT-033 (MUST).** SIG MUST publish a **crosswalk export** mapping SIG identifiers to every
external identifier it holds, under the most permissive licence the constituent rights permit. This
is the single highest-leverage artifact SIG can give the ecosystem: it lets other projects
reproduce national analyses without rebuilding entity resolution (OL-22.6-01).

**SIG-IDENT-034 (MUST).** SIG MUST publish and maintain an `ORI9 → Census GEOID` crosswalk as a
public artifact, subject to the licensing gate.

---

# Part III — Data architecture

## 15. Storage architecture

### 15.1 The decision

**SIG-STORE-001 (MUST).** Canonical storage MUST be **PostgreSQL ≥ 18 with PostGIS ≥ 3.6.3**.
Every other store — graph, RDF, analytics, tiles, search — MUST be a **derived projection** that
can be dropped and rebuilt from canonical data plus the evidence store. *(R6-F1, R6-F3,
REQ-R6-01.)*

This answers OL-Q20 ("relational/PostGIS with graph projections, a property graph, RDF, or
hybrid?") decisively: **hybrid, with a relational core.** It answers OL-Q21 ("which model best
supports claim-level provenance and bitemporal history?") with a qualification that matters:
RDF-star and Wikibase model *provenance* best, and XTDB models *bitemporality* best, but neither
can carry SIG's geospatial, access-control, and constraint requirements. Postgres can carry all
of them and can *emit* the other two as projections. The reverse is not true.

### 15.2 The evaluation

Scored against a weighted scorecard (R6 Part 2). Summary:

| Option | Score | Verdict |
|---|---|---|
| **Hybrid: Postgres+PostGIS canonical + derived projections** | **214** | **Adopted** |
| Postgres-only, no projections | 190 | Rejected: no interoperable RDF/analytics story |
| RDF/triplestore canonical | 142 | Rejected: fails on geospatial and write throughput |
| XTDB v2 canonical | 125 | Rejected: best bitemporal semantics, but no geospatial story, thin ecosystem, single-vendor governance |
| Native labelled property graph | 93 | Rejected: reification bloat; licensing |

**SIG-STORE-002 (MUST).** No component MAY be adopted as canonical if its access control,
backup, or production use requires a commercial or source-available (non-OSI) licence.
*(REQ-R6-04.)* The concrete exclusions, verified rather than assumed:

| Candidate | Disqualifying fact (verified 2026-08) |
|---|---|
| Kuzu | Repository archived 2025-10-10. Not viable. |
| Neo4j Community | GPLv3; RBAC and online backup are Enterprise-only — precisely the features SIG's sensitivity tiers need. |
| Memgraph Community | BUSL-1.1: source-available, not open source. |
| TigerGraph Community | Terms could not be verified. Excluded by SIG-STORE-002's default-deny. |
| Citus | AGPL-3.0; and columnar-in-Postgres is an unstable field (pg_mooncake stalled). |

**SIG-STORE-003 (MUST).** The system MUST start, ingest, resolve, and serve with **zero
non-PostGIS extensions installed**. Apache AGE, `pgvector`, `pg_ivm`, and `h3-pg` are optional
accelerants, never load-bearing. *(REQ-R6-05.)* This is a deliberate hedge: extension
availability on managed Postgres is volatile, and a public-interest project must not be
one hosting-provider decision away from being unable to run.

### 15.3 Why the relational core is not a compromise

The reasoning is worth recording, because "knowledge graph" invites a graph database by reflex.

1. **SIG's write path is not graph-shaped.** It is a high-volume append of typed assertions with
   constraints, temporal ranges, and geometry. That is Postgres's home ground.
2. **Claim-level provenance in an LPG requires reification.** Attaching source, time, method,
   and confidence to an *edge* forces either edge properties (which cannot themselves carry
   provenance) or reifying every edge as a node — at which point the graph database is storing a
   relational model badly. *(R6-F18.)*
3. **Bitemporality in an LPG is application discipline, not a database feature.** *(R6-F19.)*
   SIG's whole thesis rests on temporal correctness; putting it in application code is
   unacceptable.
4. **PG 18 ships the temporal primitives natively**: SQL:2011-style `PERIOD` / `WITHOUT OVERLAPS`
   constraints and `uuidv7()`. *(R6-F2.)*
5. **Row-level security gives per-row sensitivity tiers** (§43.3) without a commercial licence.
   *(R6-F8.)*
6. **PostGIS has no rival.** A project whose physical layer is 558,645 OSM elements cannot treat
   geospatial as an afterthought.
7. **The interoperability need is a *file* problem, not a *server* problem.** Downstream users
   want Parquet, GeoJSON, PMTiles, JSON-LD, and a SQLite bundle. Those are exports, and exports
   are cheap from Postgres.

### 15.4 The projections

**SIG-STORE-004 (MUST).** The following projections MUST be rebuildable from canonical state by
a single documented command, and a CI job MUST rebuild each from scratch and verify it.

| Projection | Technology | Purpose | Rebuild trigger |
|---|---|---|---|
| **Resolution read models** | Postgres materialized tables | Fast entity-with-attributes reads for API/UI | Ruleset or claim change |
| **Analytics** | Hive-partitioned Parquet + DuckDB | High-volume usage aggregates, off the transactional store | Nightly |
| **RDF / JSON-LD** | Named-graph serialization (PROV-O + SIG terms) | Semantic-web interoperability, claim-level provenance interchange | Per release |
| **Map tiles** | PMTiles v3 via tippecanoe | Static public map | Per release |
| **Search index** | Postgres FTS by default; Typesense/Meilisearch optional | Entity and document search | Continuous |
| **Graph query** | Apache AGE (optional) or an exported edge list | Network analytics, Cypher exploration | On demand |
| **Datasette/SQLite bundle** | SQLite export | Offline exploration, archival, teaching | Per release |

**SIG-STORE-005 (MUST).** No projection may be the sole home of any fact. Losing every
projection simultaneously MUST cost only compute, never information.

### 15.5 Architecture Decision Records

**SIG-STORE-006 (MUST).** Each of the following decisions MUST be recorded as an ADR under
`docs/adr/` at Phase 1, using a consistent template (context, decision, status, consequences,
alternatives considered, revisit triggers):

| ADR | Decision |
|---|---|
| ADR-001 | PostgreSQL 18 + PostGIS as canonical store; everything else a projection |
| ADR-002 | Append-only claim table; entity tables hold identity only |
| ADR-003 | Two interval time dimensions + one ordering scalar |
| ADR-004 | EDTF for uncertain dates |
| ADR-005 | Resolution as a stored decision record, not a view |
| ADR-006 | OCFL 1.1 evidence store on object storage with governance-mode Object Lock |
| ADR-007 | LinkML as the single ontology source of truth |
| ADR-008 | SKOS for published controlled vocabularies |
| ADR-009 | SPDX expressions for per-source licensing, with a build-time compatibility gate |
| ADR-010 | DuckDB/Parquet analytics boundary; no raw audit rows anywhere |
| ADR-011 | The ODbL posture (§42.3) |
| ADR-012 | Sensitivity tiers enforced by RLS, applied at the view layer |

**SIG-STORE-007 (MUST).** Every ADR MUST name its **revisit trigger** — the observable condition
under which the decision should be reconsidered. An ADR with no revisit trigger is incomplete.

---

## 16. The canonical schema

This section specifies the physical schema of the claim spine. The domain entity tables follow
from Part II §11 and are consolidated in Appendix C. Everything here is normative DDL; where a
choice is defensible either way, the rationale is given so an implementer does not silently
"improve" it into incorrectness.

### 16.1 Identity: entities hold identity only

```sql
CREATE TABLE entity (
  entity_id    uuid PRIMARY KEY DEFAULT uuidv7(),
  entity_type  text NOT NULL REFERENCES vocab_entity_type(entity_type),
  created_at   timestamptz NOT NULL DEFAULT clock_timestamp(),
  merged_into  uuid REFERENCES entity(entity_id),   -- cached resolver output; the merge is itself a claim
  CHECK (merged_into IS NULL OR merged_into <> entity_id)
);
```

**SIG-STORE-008 (MUST).** Entity tables MUST contain identity only: `entity_id`, `entity_type`,
lifecycle bookkeeping, and cached resolver outputs. **Every attribute of every entity MUST be
expressed as a claim.** *(REQ-R6-03; implements SIG-ONTO-003.)*

**SIG-STORE-009 (MUST).** A schema test MUST enumerate all columns on all entity tables and fail
if any column name matches a registered predicate id. This is the mechanical guard against the
model degrading back into a conventional attribute table over time — which it will otherwise do,
because adding a column is always locally easier than adding a claim.

**SIG-STORE-010 (MUST).** Primary keys MUST be UUIDv7 generated by PG 18's `uuidv7()`.
*(REQ-R6-06.)* Rationale: time-ordered UUIDs give index locality without leaking a guessable
sequential count of how much SIG knows, and they are safe to mint in distributed workers.

### 16.2 The claim table

```sql
CREATE TYPE value_kind    AS ENUM ('value', 'somevalue', 'novalue');
CREATE TYPE claim_rank    AS ENUM ('preferred', 'normal', 'deprecated');
CREATE TYPE review_status AS ENUM ('unreviewed','machine_accepted','human_verified','disputed','retracted');

CREATE TABLE claim (
  claim_id          uuid PRIMARY KEY DEFAULT uuidv7(),

  -- Subject · predicate · object -------------------------------------------
  subject_id        uuid NOT NULL REFERENCES entity(entity_id),
  predicate_id      text NOT NULL REFERENCES vocab_predicate(predicate_id),
  object_entity     uuid REFERENCES entity(entity_id),
  object_type       text NOT NULL REFERENCES vocab_object_type(object_type),
      -- literal|entity_ref|vocab_term|quantity|money|geometry|duration|interval|document_ref
      -- REQUIRED: which value_* column is populated is ambiguous across
      -- quantity / money / duration, so the kind is declared, never inferred (§10.3.5)
  value_kind        value_kind NOT NULL DEFAULT 'value',
  value_text        text,        -- canonical string form; always present when kind='value'
  value_num         numeric,     -- typed shadow for indexed numeric comparison
  value_bool        boolean,
  value_geom        geometry(Geometry, 4326),
  value_json        jsonb,       -- structured values: bounds, intervals, composite money
  unit              text,        -- REQUIRED for object_type='quantity'; not recoverable from value_json

  -- P2: raw before normalized ----------------------------------------------
  raw_value         text NOT NULL,   -- the source's literal text. NO EXCEPTIONS.
  raw_context       jsonb,           -- the citation anchor within the artifact
  normalization_id  text REFERENCES vocab_normalization(normalization_id),
  normalization_version text,

  -- T1 valid time -----------------------------------------------------------
  valid_period      tstzrange NOT NULL DEFAULT tstzrange(NULL, NULL, '[)'),
  valid_edtf        text,
  valid_from_kind   text NOT NULL DEFAULT 'unknown',  -- exact|ongoing|unknown|before|after|never
  valid_to_kind     text NOT NULL DEFAULT 'unknown',

  -- T2 observation time (ordering scalar, not an AS OF axis) ----------------
  observed_at       timestamptz,
  observed_edtf     text,
  observed_at_kind  text NOT NULL DEFAULT 'exact',    -- exact|approximate|bounded_above|unknown
  observed_unknown_reason text,

  -- T5 transaction time (DB-controlled) -------------------------------------
  sys_period        tstzrange NOT NULL DEFAULT tstzrange(clock_timestamp(), NULL, '[)'),

  -- Epistemics: the four axes of §10.4-§10.6 -------------------------------
  -- NOTE: these are the R/D/I axes. C (currency) is DERIVED AT QUERY TIME and is
  -- deliberately NOT stored (SIG-EPIS-020). W is computed from all four.
  source_reliability text NOT NULL
      REFERENCES vocab_source_reliability(code),   -- R1..R6  (§10.4)
  reliability_provisional boolean NOT NULL DEFAULT false,  -- novel source (SIG-EPIS-015)
  claim_directness   text NOT NULL
      REFERENCES vocab_claim_directness(code),     -- D1..D6  (§10.5)
  artifact_integrity text NOT NULL
      REFERENCES vocab_artifact_integrity(code),   -- I1..I3  (§10.6)
  legacy_source_tier char(1)
      CHECK (legacy_source_tier IS NULL OR legacy_source_tier BETWEEN 'A' AND 'F'),
      -- OPTIONAL. Retained only to carry an upstream's own Tier A-F label where a
      -- source publishes one. It is NEVER used in resolution (§10.4).
  claim_polarity    text NOT NULL DEFAULT 'affirms',   -- affirms|denies
  rank              claim_rank NOT NULL DEFAULT 'normal',
  review_status     review_status NOT NULL DEFAULT 'unreviewed',

  -- Origin ------------------------------------------------------------------
  extraction_id     uuid REFERENCES extraction(extraction_id),
  asserted_by       uuid REFERENCES entity(entity_id),   -- a Person entity (§11.3), not free text
  assertion_rationale text,
  derived_from_claim_ids uuid[],      -- source-dependence chain (§28.6)

  -- Lineage & governance ----------------------------------------------------
  ingest_run_id     uuid NOT NULL REFERENCES ingest_run(run_id),
  revises_claim     uuid REFERENCES claim(claim_id),
  retraction_of     uuid REFERENCES claim(claim_id),
  correction_reason text,
  sensitivity_tier  smallint NOT NULL DEFAULT 0,
  rights_id         uuid NOT NULL REFERENCES rights_record(rights_id),

  CONSTRAINT claim_value_shape CHECK (
      (value_kind = 'value'
         AND (value_text IS NOT NULL OR object_entity IS NOT NULL
              OR value_geom IS NOT NULL OR value_json IS NOT NULL))
   OR (value_kind IN ('somevalue','novalue')
         AND value_text IS NULL AND object_entity IS NULL AND value_num IS NULL
         AND value_bool IS NULL AND value_geom IS NULL)
  ),
  CONSTRAINT claim_origin_present CHECK (
      extraction_id IS NOT NULL OR asserted_by IS NOT NULL
  ),
  CONSTRAINT claim_unit_required CHECK (
      object_type <> 'quantity' OR unit IS NOT NULL
  ),
  CONSTRAINT claim_human_needs_rationale CHECK (
      asserted_by IS NULL OR assertion_rationale IS NOT NULL
  ),
  CONSTRAINT claim_observed_unknown_reasoned CHECK (
      observed_at IS NOT NULL OR observed_unknown_reason IS NOT NULL
  ),
  CONSTRAINT claim_correction_reasoned CHECK (
      revises_claim IS NULL OR correction_reason IS NOT NULL
  ),
  CONSTRAINT claim_observed_not_future CHECK (
      observed_at IS NULL OR observed_at <= clock_timestamp() + interval '1 day'
  )
) PARTITION BY RANGE (observed_at);

CREATE INDEX ON claim (subject_id, predicate_id, observed_at DESC);
CREATE INDEX ON claim USING gist (valid_period);
CREATE INDEX ON claim USING gist (value_geom) WHERE value_geom IS NOT NULL;
CREATE INDEX ON claim (predicate_id, object_entity) WHERE object_entity IS NOT NULL;
CREATE INDEX ON claim (ingest_run_id);
CREATE INDEX ON claim (subject_id) WHERE upper_inf(sys_period);
```

**Design points that MUST NOT be "simplified" away:**

| # | Choice | Why |
|---|---|---|
| 1 | `sys_period` is a **range**, not a `recorded_at` instant | A claim is closed out only when **SIG corrects its own record**, never when the world changes. A world change is a *new claim with different valid time*, and both rows remain current in transaction time. Conflating these is the classic bitemporal bug. |
| 2 | `valid_period` **and** `valid_edtf` coexist | The range is what indexes; the EDTF string is what the source actually supported. Dropping EDTF violates P2. |
| 3 | `raw_value` is `NOT NULL` | P2. A claim with no literal source text is an inference and belongs at L4. |
| 4 | `observed_at` is **nullable with a mandatory reason** | *This is a deliberate divergence from R6's `NOT NULL` recommendation.* Forcing a timestamp on a source that never stated when it observed would manufacture T2 out of T3 or T4 — exactly what SIG-TIME-002 forbids. The constraint pair (`observed_at OR observed_unknown_reason`) keeps the field from silently going unfilled. |
| 5 | Four epistemic axes, not one `confidence` | Source reliability, claim directness, artifact integrity, and currency are independent (§10.4–§10.6). A first-rate contract is an `R1` source and `D5` — weak support — for *current* camera count. |
| 5b | `C` (currency) is **not a column** | A claim's currency changes with the passage of time without the claim changing. Storing it would guarantee it goes stale (SIG-EPIS-020). |
| 5c | `legacy_source_tier` is nullable and non-resolving | The outline's Tier A–F is a *genre* scale (§10.4). Where an upstream publishes its own tier label, SIG preserves it as source data (P2) but MUST NOT resolve on it. |
| 6 | Partitioned by `observed_at`, not by `sys_period` | Queries filter on observation time, and historical backfills of old observations should land in old partitions. |
| 7 | `derived_from_claim_ids` | Without it, three sources that all copied one portal look like three independent corroborations (§28.6). |

### 16.3 Append-only enforcement

**SIG-STORE-011 (MUST).** The claim table MUST be append-only, enforced in the database, not by
convention. *(REQ-R6-02.)*

```sql
CREATE OR REPLACE FUNCTION claim_append_only() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'claim rows are immutable: DELETE forbidden (claim_id=%)', OLD.claim_id;
  END IF;
  -- The ONLY permitted mutation is closing the transaction-time interval.
  IF ROW(NEW.*) IS DISTINCT FROM ROW(OLD.*) THEN
    IF NEW.sys_period <> OLD.sys_period
       AND ROW(NEW.*) = ROW(OLD.*) # ARRAY['sys_period']::text[] THEN
      -- permitted: sys_period upper bound being set
      IF lower(NEW.sys_period) <> lower(OLD.sys_period) THEN
        RAISE EXCEPTION 'sys_period lower bound is immutable (claim_id=%)', OLD.claim_id;
      END IF;
      IF NOT upper_inf(OLD.sys_period) THEN
        RAISE EXCEPTION 'claim already closed (claim_id=%)', OLD.claim_id;
      END IF;
    ELSE
      RAISE EXCEPTION 'claim rows are immutable: only sys_period may be closed (claim_id=%)', OLD.claim_id;
    END IF;
  END IF;
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER claim_append_only_trg
  BEFORE UPDATE OR DELETE ON claim
  FOR EACH ROW EXECUTE FUNCTION claim_append_only();
```

*(The `#` operator above is illustrative of "compare all columns except"; the implementation MUST
use an explicit column list generated from the schema so that adding a column cannot silently
widen what is mutable. A CI test MUST assert the generated list matches the live schema.)*

**SIG-STORE-012 (MUST).** Application roles MUST NOT hold `DELETE` on `claim`, `extraction`,
`evidence_artifact`, or `evidence_capture`. The trigger is defence in depth, not the only line.

**SIG-STORE-013 (MUST).** `sys_period`'s lower bound MUST be database-assigned and immutable;
its upper bound MUST be set **only** when SIG corrects its own record. *(REQ-R6-08.)*

### 16.4 The resolution table

**SIG-STORE-014 (MUST).** Resolution MUST be a **stored decision record**, not a view.
*(REQ-R6-15.)* This is a correction to the outline, which reads (outline §6.5) as though resolution is a
computed presentation concern. It is not: a resolution embodies an editorial policy, has an
author (possibly `auto`), has a rationale a journalist may quote, and must be reproducible and
diffable after the fact.

```sql
CREATE TABLE resolution (
  resolution_id       uuid PRIMARY KEY DEFAULT uuidv7(),
  subject_id          uuid NOT NULL REFERENCES entity(entity_id),
  predicate_id        text NOT NULL REFERENCES vocab_predicate(predicate_id),

  value_kind          value_kind NOT NULL,
  value_text          text,
  value_num           numeric,
  value_geom          geometry(Geometry, 4326),
  value_json          jsonb,
  object_entity       uuid REFERENCES entity(entity_id),

  valid_period        tstzrange NOT NULL,
  sys_period          tstzrange NOT NULL DEFAULT tstzrange(clock_timestamp(), NULL, '[)'),

  -- WHY: what makes this a decision record rather than a cache
  winning_claim       uuid REFERENCES claim(claim_id),
  considered_claims   uuid[] NOT NULL,
  dissenting_claims   uuid[] NOT NULL DEFAULT '{}',
  contradiction_state text NOT NULL,   -- uncontested|resolved_conflict|unresolved_conflict|insufficient
  strategy_id         text NOT NULL REFERENCES vocab_resolution_strategy(strategy_id),
  rationale_code      text NOT NULL REFERENCES vocab_rationale(rationale_code),
  rationale_text      text NOT NULL,   -- a quotable sentence
  confidence          text NOT NULL REFERENCES vocab_confidence(confidence),
  evidence_counts     jsonb NOT NULL,  -- machine-readable support/dissent counts by tier (§10.6)
  resolver_version    text NOT NULL,
  ruleset_version     text NOT NULL,
  decided_by          text NOT NULL DEFAULT 'auto',
  decided_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
  override_rationale  text,

  CONSTRAINT resolution_no_overlap
    EXCLUDE USING gist (subject_id WITH =, predicate_id WITH =, valid_period WITH &&)
    WHERE (upper_inf(sys_period)),
  CONSTRAINT resolution_override_reasoned CHECK (
    decided_by = 'auto' OR override_rationale IS NOT NULL
  )
);
```

**SIG-STORE-015 (MUST).** `contradiction_state = 'unresolved_conflict'` MUST be a **publishable
outcome**. The API MUST be able to return a disagreement with all competing claims attached,
rather than forcing a single value. *(REQ-R6-16; discharges OL-11.1-03, OL-6.5-01.)*

**SIG-STORE-016 (MUST).** At most one resolved value per `(subject, predicate)` MAY be current
for any instant of valid time, enforced by the GiST exclusion constraint above — **not by
application code**. *(REQ-R6-17.)*

**SIG-STORE-017 (MUST).** `resolver_version` (code) and `ruleset_version` (policy) MUST be
versioned independently. A policy change — "contract quantities now outrank portal counts for
`contracted_camera_count`" — is an attributable editorial act that must be re-runnable
independently of code changes. *(REQ-R6-19.)*

**SIG-STORE-018 (MUST).** A CI job MUST regenerate a sample of resolution rows from their stored
inputs and assert they match. A mismatch means either a bug or undocumented policy drift; both
warrant an alert.

**SIG-STORE-019 (MUST).** Human override MUST be first-class: a curator may pin a resolution, and
that override is recorded with `decided_by` and `override_rationale`, surfaced in the UI as an
editorial act. *(Discharges OL-6.5-01's "resolution" block with an accountable author.)*

### 16.5 Claim evidence and qualifiers

```sql
CREATE TABLE claim_evidence (
  claim_id     uuid NOT NULL REFERENCES claim(claim_id),
  capture_id   uuid NOT NULL REFERENCES evidence_capture(capture_id),
  extraction_id uuid REFERENCES extraction(extraction_id),
  role         text NOT NULL REFERENCES vocab_evidence_role(role),
  locator      jsonb,
  excerpt      text,
  weight_note  text,
  PRIMARY KEY (claim_id, capture_id, role)
);

CREATE TABLE claim_qualifier (
  claim_id     uuid NOT NULL REFERENCES claim(claim_id),
  qualifier_id text NOT NULL REFERENCES vocab_predicate(predicate_id),
  value_text   text,
  value_num    numeric,
  value_entity uuid REFERENCES entity(entity_id),
  PRIMARY KEY (claim_id, qualifier_id, COALESCE(value_text, ''))
);
```

Evidence roles are the six of §10.3.6. `contradicts` lets SIG record "this document is evidence
*against* claim X" without inventing a negative claim — a distinct epistemic act that OL-9.4
requires and that a single `source` foreign key cannot express.

### 16.6 Corrections without erasure

**SIG-STORE-020 (MUST).** Correcting an erroneous claim MUST close the original's `sys_period`
and insert a new claim with `revises_claim` set and a `correction_reason`. Deleting or
overwriting the original is prohibited. *(REQ-R6-12; discharges OL-19.3 and SIG-TIME-009.)*

Worked example — on 2026-05-01 the parser read a contract PDF as "25 cameras"; on 2026-08-20 a
human notices it says "225":

```sql
BEGIN;
  -- 1. Close SIG's prior belief. The world did not change; SIG was wrong.
  UPDATE claim
     SET sys_period = tstzrange(lower(sys_period), clock_timestamp(), '[)')
   WHERE claim_id = :bad_claim_id AND upper_inf(sys_period);

  -- 2. Assert the corrected reading, pointing back at what it revises.
  INSERT INTO claim (subject_id, predicate_id, value_kind, value_text, value_num,
                     raw_value, raw_context, valid_period, valid_from_kind, valid_to_kind,
                     observed_at, observed_at_kind, source_tier, support_strength,
                     extraction_id, ingest_run_id, revises_claim, correction_reason, rights_id)
  SELECT subject_id, predicate_id, 'value', '225', 225,
         '225', raw_context, valid_period, valid_from_kind, valid_to_kind,
         observed_at, observed_at_kind, source_tier, support_strength,
         :new_extraction_id, :run_id, claim_id, 'extraction_error', rights_id
    FROM claim WHERE claim_id = :bad_claim_id;
COMMIT;
```

A query at `as_of_belief = '2026-06-01'` still returns 25. A journalist who cited SIG in June can
reproduce exactly what SIG said in June, and can also see that SIG corrected it and why. **That
property is the difference between a database and a citable source.**

### 16.7 EDTF encoding

**SIG-STORE-021 (MUST).** Uncertain, approximate, and open-ended dates MUST be stored as **EDTF
Level 1** strings (`valid_edtf`, `observed_edtf`, `published_at`), with a machine-usable
`tstzrange` envelope derived by a **pinned, versioned, deterministic** function. The widening
rules MUST be recorded in `ruleset_version`. *(REQ-R6-10; R6-F33.)*

| Source text | EDTF | Derived envelope | Kinds |
|---|---|---|---|
| "signed March 14, 2025" | `2025-03-14` | `[2025-03-14, 2025-03-15)` | exact / exact |
| "in 2019" | `2019` | `[2019-01-01, 2020-01-01)` | exact(year) |
| "early 2025" | `2025-03~` | `[2025-01-01, 2025-06-01)` | approximate |
| "began sometime before the June meeting" | `../2025-06-10` | `(-inf, 2025-06-11)` | before |
| "still in place as of the last capture" | `2026-07-14/..` | `[2026-07-14, inf)` | ongoing |
| "the department has used ALPRs for years" | `..` + note | `(-inf, inf)` | unknown |

**SIG-STORE-022 (MUST NOT).** A source that says "in early 2025" MUST NOT be stored as
`2025-01-01`. False precision is a P4 violation and corrupts lifecycle ordering (§29.4).

### 16.8 Access control

**SIG-STORE-023 (MUST).** Sensitivity tiers MUST be enforced by PostgreSQL **restrictive** RLS
policies. The public API role MUST NOT hold `BYPASSRLS`. Export and dump roles MUST run with
`row_security = off` so that a would-be-filtered export **fails loudly** rather than silently
publishing an incomplete dataset. *(REQ-R6-43.)*

**SIG-STORE-024 (MUST).** RLS policy tests MUST be part of CI: for each role and each tier, a
test asserts both that permitted rows are visible and that forbidden rows are not. A permissions
regression is a privacy incident, not a bug.

---

## 17. The evidence store

The outline requires (OL-2B-IND-03) that raw source snapshots remain immutable, and (OL-13.4-01)
that SIG be able to hold a raw private archival copy alongside a redacted public derivative.
Q25 asks how snapshots should be content-addressed. This section answers all three.

### 17.1 Requirements

**SIG-EVID-001 (MUST).** The evidence store MUST satisfy, simultaneously:

| # | Requirement | Driven by |
|---|---|---|
| E1 | Bytes are write-once and verifiable by digest | OL-2B-IND-03, OL-8.15-02 |
| E2 | A capture remains **re-parseable**, not merely viewable, years later | OL-19.2, §21.7 backfill |
| E3 | Sensitive material can be sealed while its metadata stays public | OL-13.4-01, OL-Q31 |
| E4 | A takedown obligation is satisfiable through a permissioned, audited path | OL-Q32 |
| E5 | The store survives loss of the application entirely | §46.5 continuity |
| E6 | Storage cost is bounded and egress is not ruinous | §50 |

### 17.2 Content addressing

**SIG-EVID-002 (MUST).** Digests MUST be stored as **multihash** (base32-lowercase), not as bare
hex, so the algorithm is part of the value and can be migrated. *(REQ-R6-21; R6-F38.)*

**SIG-EVID-003 (MUST).** The interop digest MUST be **SHA-256 or SHA-512**; BLAKE3 MAY be stored
additionally in the fixity block for fast local verification. *(R6-F39.)* Rationale: BLAKE3 is
faster and actively maintained, but SHA-2 is what every archival and legal-verification
counterparty accepts. SIG carries both rather than choosing.

**SIG-EVID-004 (MUST).** Deduplication MUST be by digest. A portal page fetched daily that has
not changed produces one stored blob and N capture rows. `(content_digest, source_uri)` is
unique.

### 17.3 Layout: OCFL

**SIG-EVID-005 (MUST).** Evidence bytes MUST live in an **OCFL 1.1** storage root on
S3-compatible object storage: one OCFL object per source stream, one OCFL version per capture,
with `sha512` in the inventory manifest and BLAKE3 in the `fixity` block. *(REQ-R6-20; R6-F37.)*

Rationale for OCFL specifically, over a bespoke layout: it is designed for exactly this problem
(immutable, versioned, digest-verified objects with a human-readable on-disk structure), it is
**recoverable without SIG's software** — the inventory is JSON next to the files — and it is the
format digital-preservation institutions already accept. E5 is satisfied by construction.

```
evidence-root/
  0=ocfl_1.1
  ocfl_layout.json
  a1/b2/c3/  <urn:sig:source:flock-portal:hagerstown-md-pd>/
      inventory.json            # manifest: version → digest → path
      inventory.json.sha512
      v1/content/index.html
      v2/content/index.html     # only if bytes changed
      v3/content/capture.wacz
```

**SIG-EVID-006 (MUST).** Object storage holding evidence MUST have **versioning enabled** and
**Object Lock in *governance* mode** with a documented default retention. **Compliance mode MUST
NOT be used**, so that takedown obligations (§45) remain satisfiable through a permissioned,
audited path rather than being technically impossible. *(REQ-R6-23; R6-F41.)*

This is a genuine ethical trade-off recorded deliberately: compliance mode would make SIG's
archive unimpeachable against a hostile legal demand, and would also make SIG unable to honour a
legitimate privacy-harm removal. SIG chooses the latter capability, and compensates with
transparency reporting (§45.6).

### 17.4 Web captures

**SIG-EVID-007 (MUST).** Web captures MUST be stored as **WACZ 1.1.1** packages, not as
screenshots or rendered PDFs alone. *(REQ-R6-22; R6-F36.)*

Rationale: a Flock transparency portal is a JavaScript application. A screenshot proves what it
looked like; it does not let a future parser re-extract fields when SIG's extraction improves
(E2). A WACZ retains the network traffic — including the JSON the SPA fetched — so re-extraction
years later is possible. Screenshots and PDFs are ADDITIONALLY captured for human display and for
evidentiary presentation, as separate captures of the same artifact.

**SIG-EVID-008 (MUST).** For any artifact rendered by JavaScript, the capture set MUST include:
(a) the WACZ, (b) a full-page screenshot, (c) the extracted structured payload if one exists, and
(d) the raw HTML. Each is a separate `evidence_capture` row sharing one `evidence_artifact`.

### 17.5 Storage tiers

**SIG-EVID-009 (MUST).** Every capture MUST carry a `storage_tier`:

| Tier | Meaning | Bytes | Metadata | Excerpts |
|---|---|---|---|---|
| `public` | Freely redistributable, no sensitivity concern | Public URL | Public | Public |
| `restricted` | Lawfully held, redistribution limited by licence or sensitivity | Access-controlled | Public | Redacted |
| `sealed` | Contains material SIG must not expose (unredacted PII, sealed records, material under a takedown hold) | Access-controlled, audited | **Metadata-only public representation** | None |

**SIG-EVID-010 (MUST).** A `sealed` capture MUST still have a **public metadata representation**:
its existence, source, date, digest, and the claims it supports are public even when its bytes
are not. *(Discharges OL-13.4-01 and OL-Q31.)* This is what allows SIG to say "we hold the
contract, here is its hash, here is what it establishes" without publishing an unredacted PDF.

**SIG-EVID-011 (MUST).** Redaction MUST produce a **new capture** with `parent_capture_id` set,
never an edit of the original (SIG-EPIS-006). The redaction method and version MUST be recorded
so that a mis-redaction can be identified and re-done.

**SIG-EVID-012 (MUST).** Access to `restricted` and `sealed` bytes MUST be logged with
requester, purpose, and timestamp, and the access log MUST itself be subject to retention limits
so that it does not become a surveillance record of SIG's own researchers (§44.5).

### 17.6 Disappearance and link rot

**SIG-EVID-013 (MUST).** When an artifact ceases to be retrievable, SIG MUST record a
disappearance event on the artifact — `disappeared_observed_at` plus the failing status — and
MUST NOT delete the artifact, its captures, or its claims. *(Discharges OL-Q18.)*

**SIG-EVID-014 (MUST).** Disappearance MUST generate a research task (§33.2) and MUST be visible
in the UI as a distinct state: "this source no longer exists; SIG's capture of
YYYY-MM-DD is the record."

**SIG-EVID-015 (MUST).** A recurring link-rot sweep MUST re-check `capture_status` for all
artifacts on a cadence proportional to source volatility, and MUST attempt Wayback registration
for public artifacts SIG is permitted to submit.

**Rationale.** A vanished Flock portal is one of the most informationally valuable events SIG can
observe (OL-2B-FP-03, OL-3-04). Treating it as an error to be retried, rather than as a datum to
be recorded, would discard the single clearest signal that an agency changed its transparency
posture. *(R11 independently flags this as a top-5 operational risk the outline ignores.)*

### 17.7 Reproducibility and deposit

**SIG-EVID-016 (MUST).** Every claim MUST reference an `ingest_run` recording connector version,
code commit, ruleset version, vocabulary version, input evidence digests, parameters, and
environment. *(REQ-R6-25.)*

**SIG-EVID-017 (MUST).** Re-running a pinned connector over pinned evidence digests MUST produce
byte-identical claim tuples modulo `claim_id` and `sys_period`, enforced by a CI test.
*(REQ-R6-26.)*

**SIG-EVID-018 (MUST).** Ingestion MUST run with `LC_ALL=C` and `TZ=UTC`, and MUST NOT use
wall-clock time in any derived claim **value**. *(REQ-R6-27.)* Wall-clock time belongs in
`recorded_at`, nowhere else.

**SIG-EVID-019 (MUST).** Each quarterly release MUST be deposited to **Zenodo**, citing the
concept DOI for the dataset and the version DOI for the release. Evidence **bytes** MUST NOT be
deposited (size limits); the evidence **manifest of digests** MUST be. *(REQ-R6-30; R6-F42.)*
A Software Heritage deposit of the code MUST accompany it.

---

## 18. The analytics boundary

The outline (OL-Q22) asks how high-volume audit aggregates stay separate from the knowledge
graph. The answer has a hard privacy component, not only a performance one.

### 18.1 The bright line

**SIG-STORE-025 (MUST NOT).** Raw per-search or per-plate audit rows MUST NOT be stored in the
canonical store **or** in the published analytics store. *(REQ-R6-34; discharges non-goals N1 and
N2, OL-13.1-02, OL-A.8.)*

**SIG-STORE-026 (MUST).** The claim schema MUST contain **no column capable of holding a licence
plate**. This is not merely a policy; it is a schema property, and a schema test asserts it. A
predicate whose registered datatype could carry plate-like values MUST be rejected at vocabulary
review.

### 18.2 The substrate

**SIG-STORE-027 (MUST).** High-volume aggregates MUST live outside PostgreSQL as
**Hive-partitioned Parquet queried by DuckDB**. No columnar Postgres extension may be adopted as
canonical. *(REQ-R6-31; R6-F43, R6-F44, R6-F11.)* ClickHouse (Apache-2.0) remains the documented
escape hatch if interactive aggregate latency ever demands it. *(R6-F45.)*

### 18.3 The join

**SIG-STORE-028 (MUST).** Aggregate partitions MUST join to the graph **only** via `sig_entity_id`
UUIDs and period — **never via names** — and MUST carry `ingest_run_id` and
`agg_ruleset_version`. *(REQ-R6-32.)*

Joining on names would reintroduce, at the analytics layer, exactly the entity-resolution failure
that P6 exists to prevent — and it would do so invisibly, in a layer where nobody is looking.

**SIG-STORE-029 (MUST).** Aggregate partitions MUST be registered as **evidence artifacts** with
digests. A claim is created only when SIG asserts a *summary statement* about a partition — e.g.
"agency X performed 412 searches in the 30 days to 2026-07-15" — and that claim cites the
partition as its evidence. *(REQ-R6-33.)* This keeps the chain of §10.1 unbroken across the
boundary.

### 18.4 Disclosure control

**SIG-STORE-030 (MUST).** Published aggregate cells with counts **1–4** MUST be suppressed —
published as null with `suppressed_flag` and `k_threshold`, **never as zero** — complementary
suppression MUST be applied so that a single suppression is not invertible from published totals,
and the finest published time granularity MUST be one month. *(REQ-R6-35.)*

**SIG-STORE-031 (MUST).** Suppression MUST record **which rationale applied**. Institutional
small counts MUST NOT be suppressed merely because they are small. *(REQ-R6-36.)*

| Rationale | Applies when | Action |
|---|---|---|
| `protects_individual` | A small cell could identify a private person or their movements | Suppress |
| `institutional_conduct` | The cell describes an organization's conduct (e.g. "this agency ran 3 immigration-reason searches") | **Publish.** Suppressing it would defeat the project's purpose |
| `contractual` | The upstream licence forbids cell-level republication | Suppress, cite the rights record |

**SIG-STORE-032 (MUST).** The distinction in that table is load-bearing and is easy to get
backwards. "Three searches" by an *agency* is accountability information about an institution and
MUST be published. "Three searches" that would isolate one *individual's* vehicle movements MUST
be suppressed. The default when the two cannot be separated is to suppress and to raise a review
task, not to publish.

**SIG-STORE-033 (RATIONALE).** Authoritative external small-cell thresholds could not be verified from a
primary US federal source during research (R6-F46). The k = 5 threshold above is therefore
adopted as SIG's own documented policy, not as a claimed standard, and the methodology page MUST
present it as such. Where a partner's licence imposes a different threshold, the stricter applies.

---

## 19. Geospatial architecture

### 19.1 Storage and projection

**SIG-GEO-001 (MUST).** Geometry MUST be stored in **EPSG:4326** and reprojected only at serving
time. *(REQ-R6-37.)*

**SIG-GEO-002 (MUST).** Proximity queries MUST cast to `geography` (metres). Degree-based
`ST_DWithin` on 4326 geometry is **prohibited** — it silently produces distance errors that vary
by latitude, and device-attribution (§29.2) depends on distance being correct. A lint rule MUST
reject the pattern in code review.

**SIG-GEO-003 (MUST).** The physical-asset model MUST NOT assume point geometry. OSM's
`man_made=surveillance` population is 557,900 nodes, **716 ways, and 29 relations** (measured
2026-08-20, spot-check SC-01). A schema keyed on node id would silently drop the non-node
population and would break on any future remapping.

### 19.2 Assets without coordinates

**SIG-GEO-004 (MUST).** Coordinates MUST NOT be required for movable assets (OL-8.6-03).
Specifically: *(REQ-R6-38)*

| Case | Representation | Prohibited |
|---|---|---|
| Mobile asset (patrol-car ALPR, trailer, drone) | An **operating-area polygon** plus `mobility` class | Inventing a point at the agency's HQ |
| Asset of unknown location | A `somevalue` location claim (§16.2) | A NULL that is indistinguishable from "not yet researched" |
| Capability with no physical asset (cell-site simulator, Clearview licence, Fog subscription) | **No PhysicalAsset row at all**; the Deployment carries the fact | Creating a phantom asset to satisfy a map |
| Sensor with a service area but no published point (acoustic array) | Service-area polygon; point only if evidenced | Deriving a point from the polygon centroid |

**SIG-GEO-005 (MUST).** `camera:type=fixed` covers 92.0% of mapped ALPRs (SC-08), meaning ~8% —
on the order of 11,500 devices — are already non-fixed. The mobility model has an immediate
population and MUST be implemented in the first physical-layer phase, not deferred.

### 19.3 Derived geometry is physically separate

**SIG-GEO-006 (MUST).** Derived geometry — field-of-view cones, coverage estimates, road
snapping, jurisdiction assignment — MUST live in a separate `derived_geometry` table recording
`model_version`, `input_claims`, and `assumptions`; MUST be regenerable; and MUST be **visually
and structurally distinguishable from observed geometry in every surface**. *(REQ-R6-39;
discharges OL-2A-PC-02.)*

**SIG-GEO-007 (MUST).** This is urgent rather than theoretical: `direction=*` is present on
**93.6%** of mapped ALPRs (SC-08.3), so a derived FOV layer would be nearly as large as the
observed layer. A design that lets the two blur would put ~135,000 modelled cones in front of
users looking indistinguishable from ~144,000 observations. The visual language for this is
specified at §39.1.

### 19.4 Coordinate sensitivity

**SIG-GEO-008 (MUST).** Public coordinate precision MUST be governed by a per-asset
`sensitivity_tier` applied **at the view layer**, with full precision retained in canonical
storage under RLS. *(REQ-R6-40; implements OL-13.3-01.)*

| Tier | Transform | Applies to |
|---|---|---|
| 0 | Full precision | Publicly visible roadside hardware on public right-of-way |
| 1 | Coordinate truncation to a published number of decimal places | Hidden sensors on public infrastructure |
| 2 | H3 cell binning at a published resolution | Candidate/unconfirmed assets; assets near sensitive sites |
| 3 | Jurisdiction-only; no geometry published | Private-residence candidates; confidential facilities; assets under a takedown hold |

**SIG-GEO-009 (MUST NOT).** Random jitter MUST NOT be used unless the radius is published **and**
the offset is deterministic per asset. *(REQ-R6-40.)* Non-deterministic jitter is worse than
useless: repeated observation averages it away, so it provides the appearance of protection
without the substance.

**SIG-GEO-010 (MUST).** The tier transform MUST be applied **before** spatial aggregation, and the
assigned tier MUST itself be an attributed, reviewable claim. *(REQ-R6-41.)* Aggregating first
and blurring second leaks the precise value through the aggregate.

### 19.5 Binning and tiles

**SIG-GEO-011 (SHOULD).** H3 (via `h3-pg`, now maintained under the PostGIS organization,
PG 14–18) SHOULD be used for density binning and for tier-2 obfuscation. It remains optional per
SIG-STORE-003. *(R6-F47.)*

**SIG-GEO-012 (MUST).** The public map MUST be served as **static PMTiles v3** generated by
tippecanoe from the resolution projection. A dynamic tile server MUST NOT be a hard dependency of
the public map. *(REQ-R6-42; R6-F48.)*

Rationale: a static tile archive on object storage is cheap, CDN-friendly, archivable, mirrorable,
and survives SIG's application being offline — which §46.5 requires. `martin` or `pg_tileserv`
MAY be added for internal/curation use.

### 19.6 Basemap and attribution

**SIG-GEO-013 (MUST).** The basemap MUST carry correct OpenStreetMap attribution in every
rendering context, including static image exports and printed dossiers. Attribution is a licence
obligation (§42), not a courtesy.

---

## 20. Ontology, vocabulary, and schema versioning

The ontology *will* change. A surveillance-technology taxonomy written in 2026 will be wrong by
2029. The requirement is not stability; it is that change never invalidates or silently rewrites
history.

### 20.1 One source of truth

**SIG-STORE-034 (MUST).** The ontology MUST be authored in **LinkML** and MUST generate JSON
Schema, OWL/SHACL, Python dataclasses/Pydantic, SQL DDL scaffolding, and documentation from one
YAML source. CI MUST fail if committed generated artifacts differ from a fresh generation.
*(REQ-R6-44; R6-F50.)*

Rationale: SIG must publish its schema in at least five forms for five audiences (SQL for
implementers, JSON Schema for API consumers, OWL/SHACL for semantic-web reuse, Pydantic for its
own pipeline, prose for humans). Hand-maintaining five forms guarantees drift; drift in a schema
that carries epistemic semantics is a correctness bug, not a documentation bug.

### 20.2 Published vocabularies

**SIG-STORE-035 (MUST).** Controlled vocabularies MUST be published as **versioned SKOS concept
schemes** with stable per-version IRIs, and each published version MUST be archived in the
evidence store. *(REQ-R6-46; R6-F51.)*

**SIG-STORE-036 (MUST).** Vocabulary terms MUST be **immutable once published**. Corrections
deprecate and supersede; they never redefine. *(REQ-R6-47.)* Redefining `surveillance_type:alpr`
in 2029 would retroactively change the meaning of every claim made under it — the silent
overwrite the defining standard forbids, executed at maximum blast radius.

**SIG-STORE-037 (MUST).** Vocabulary changes MUST ship with crosswalk rows using SKOS mapping
relations (`exactMatch`, `closeMatch`, `broadMatch`, `narrowMatch`, `relatedMatch`) and an
explicit **`lossy` flag**. Queries traversing a lossy crosswalk MUST propagate that flag into
result metadata. *(REQ-R6-48.)*

**SIG-STORE-038 (MUST NOT).** Historical claims MUST NOT be rewritten to a newer vocabulary. Bulk
re-classification, where warranted, MUST be performed as **new claims** with
`extraction_method = 'vocabulary_migration'` and `revises_claim` links. *(REQ-R6-49.)*

### 20.3 Crosswalks to external taxonomies

**SIG-STORE-039 (MUST).** SIG MUST maintain published crosswalks from its own technology
vocabulary to every external taxonomy it ingests, at minimum: EFF Atlas categories, EFF
Street-Level Surveillance topics, ALPR Accountability Atlas issue categories, OSM
`surveillance:type` / `surveillance` / `camera:type` values, CCOPS inventory categories, and the
French Technopolice vocabulary. *(Discharges OL-10.1C-02 — "do not overwrite Atlas taxonomy
blindly; create mappings".)*

**SIG-STORE-040 (MUST).** Each crosswalk row MUST carry the mapping relation and the `lossy`
flag. Mapping Atlas's single "Automated License Plate Readers" category onto SIG's finer ALPR
family is `broadMatch` and lossy; asserting `exactMatch` would fabricate precision.

### 20.4 Physical migrations

**SIG-STORE-041 (MUST).** Physical schema migrations MUST be managed with **sqitch**, with
`deploy`, `revert`, and `verify` scripts for every change. Migrations touching `claim` MUST be
**additive**. *(REQ-R6-45; R6-F49.)*

**SIG-STORE-042 (MUST).** A migration that would drop or retype a `claim` column MUST instead add
a new column and a migration claim-set, and MUST be reviewed as an ADR. There is no in-place
rewrite path for the claim table, by design.

### 20.5 Outward identifiers

**SIG-STORE-043 (MUST).** SIG entities MUST carry outward-linkable identifiers **as claims with
provenance**, not as bare columns: Wikidata QIDs, ORI codes, GEOIDs, LEIs, UEIs, OSM element
refs, upstream project ids. *(REQ-R6-50; discharges OL-Q37, OL-24-08.)*

**SIG-STORE-044 (MUST).** Wikidata QIDs SHOULD be treated as a **first-class** crosswalk
identifier rather than an optional one. Measurement justifies this: `manufacturer:wikidata` is
present on **83.4%** of the world's mapped ALPRs and `operator:wikidata` on 12.3% (SC-08.2). The
OSM community has already performed vendor entity resolution and published it; inheriting it is
free precision, and it gives SIG an immediate, neutral join key to a general-purpose identifier
hub.

---

# Part IV — Acquisition

## 21. Connector architecture

### 21.1 The eight-stage pipeline

**SIG-INGEST-001 (MUST).** Every source adapter MUST implement the same eight-stage interface.
Stages are separately addressable, separately retryable, and each persists a content-addressed
artifact so that any downstream stage can be re-run without re-contacting the source.

```
discover()  → what exists at this source right now (identifiers, not content)
fetch()     → obtain bytes           [the ONLY stage permitted network egress]
capture()   → immutable, content-addressed storage + evidence_capture row
parse()     → structure from bytes   [pure function of a capture]
extract()   → raw claims with locators
normalize() → typed values beside preserved raw values
link()      → entity resolution against the identity layer
load()      → claims into L1
```

**SIG-INGEST-002 (MUST).** `fetch()` MUST be the **only** stage permitted network egress. Every
stage after `capture()` MUST be a pure function of stored artifacts. This is what makes replay
possible and is enforced by running replay in a network-isolated context — an attempted egress in
`parse()` or later MUST fail the run, not silently succeed.

**SIG-INGEST-003 (MUST).** Every stage MUST be idempotent. Re-running a stage over identical inputs
MUST produce identical outputs modulo generated ids and transaction timestamps.

### 21.2 Claim identity and re-extraction

**SIG-INGEST-004 (MUST).** The claim's logical identity MUST include `extractor_version` and
`normalizer_version`. A better parser therefore produces **genuinely new claim rows**, not
mutations of existing ones. *(R11; this is the operational reading of P2 and P3.)*

**SIG-INGEST-005 (MUST).** Re-extraction MUST preserve `observed_at` and `valid_*` from the source
and set `recorded_at = now()`. An `as_of_belief` query in the past therefore still returns the old
interpretation, and reproducibility survives every parser improvement.

**Why this matters more than it looks.** Treating re-extraction as a migration — updating rows in
place when the parser improves — silently destroys history and breaks every citation made against
the previous interpretation. Treating it as a *write path* costs storage and preserves the record.
R11 identifies this as the top operational risk the outline does not address.

### 21.3 Source classes and incrementality (Q23, Q24)

**SIG-INGEST-006 (MUST).** Every connector MUST declare its ingestion mode and its incrementality
strategy.

| Mode | Incrementality | Examples |
|---|---|---|
| Bulk file download | ETag / Last-Modified / content-hash diff, then row-level diff | Atlas CSV, GLEIF, Census Gazetteer, TIGER |
| REST API | Cursor or updated-since watermark | DocumentCloud, USAspending, CourtListener, Legistar, PrimeGov, CivicClerk, NextRequest, FBI CDE |
| Replication diff | Sequence number | OSM minutely/daily diffs |
| Bulk geodata | Regional extract + diff application | OSM PBF extracts |
| HTML scraping | Normalized-content hashing on **extracted structure**, not raw HTML | Agency sites, vendor pages |
| Headless-browser capture | Same, plus WACZ | SPA sources |
| Manual / human-in-the-loop | Upload event | FOIA responses, contributor photos, manually acquired research datasets |
| Partner feed | Partner-defined | Ecosystem collaborations |
| Alert stream | Message id | RSS, agenda notifications, news |

**SIG-INGEST-007 (MUST).** Change detection on scraped pages MUST diff the **extracted structured
payload**, not the HTML. Boilerplate churn, session tokens, and rotating asset hashes otherwise
produce a continuous stream of false changes that destroys the value of the change feed.

**SIG-INGEST-008 (MUST).** Some dependencies are **manual-acquisition** and MUST be modelled as
such, with a documented human procedure recording DOI, version, and checksum. The build MUST NOT
assume they are automatically fetchable. Pretending a manual dependency is automatable produces a
pipeline that silently runs on stale data.

### 21.4 Source disappearance is data

**SIG-INGEST-009 (MUST).** A 404, a removal, or a persistent challenge MUST be recorded as a
**first-class event row**, not handled as a retryable exception. *(§17.6; OL-2B-FP-03, OL-3-04.)*

**SIG-INGEST-010 (MUST).** Disappearance MUST generate a research task and MUST be queryable, so
that "which agencies quietly removed their transparency portal" is an answerable question. If
disappearance lives only in the exception path, that dataset never exists — and it is one of the
most informative datasets SIG can produce.

### 21.5 Politeness and access

**SIG-INGEST-011 (MUST).** A shared rate-limiter and robots layer MUST sit between every connector
and the network, with per-host budgets, a documented crawler UA carrying a contact URL, and
crawl-delay honoring. Connectors MUST NOT hold their own HTTP clients.

**SIG-INGEST-012 (MUST).** Where `robots.txt` cannot be retrieved, crawl permission MUST be treated
as **not granted** and the connector MUST refuse to run. *(REQ-R2-02; this case is real —
`transparency.flocksafety.com/robots.txt` returns 403, F2.1.)*

**SIG-INGEST-013 (MUST NOT).** SIG MUST NOT operate a crawler that defeats a bot-management
challenge on any source. *(REQ-R2-01; §26, §46.5.)*

**SIG-INGEST-014 (MUST).** The connector loader MUST check the source's `ingestion_permitted` flag
and `custody_posture` (§8.4) **before** any fetch, and MUST refuse to run when permission is absent
or unresolved. Licensing is enforced by the pipeline, not by good intentions.

### 21.6 Lineage

**SIG-INGEST-015 (MUST).** Every claim MUST be traceable to its `ingest_run`, recording: connector
name and version, code commit, ruleset version, vocabulary version, input evidence digests,
parameters, and environment (§17.7).

**SIG-INGEST-016 (MUST).** Lineage records MUST map onto **PROV-O** for interoperable export:
captures and claims are `prov:Entity`; runs and extractions are `prov:Activity`; connectors,
curators, and sources are `prov:Agent`; `revises_claim` is `prov:wasRevisionOf`.

### 21.7 Backfill and replay

**SIG-INGEST-017 (MUST).** SIG MUST be able to re-run extraction over archived captures with an
improved parser and produce a new claim set **without destroying the old one**.

**SIG-INGEST-018 (MUST).** Replay MUST run against archived snapshots only, in a network-isolated
context. The interface makes contacting the source impossible during replay, which both guarantees
reproducibility and prevents a replay from accidentally hammering an upstream.

**SIG-INGEST-019 (MUST).** A replay MUST be able to run in **shadow mode**: producing the new claim
set, diffing it against the current one, and reporting the delta for review *before* the new claims
are asserted. A parser change that silently alters 40,000 claims must be seen before it lands.

### 21.8 Orchestration

**SIG-INGEST-020 (SHOULD).** Orchestration SHOULD use **Dagster OSS** (Apache-2.0), self-hosted on
Postgres. Its asset model maps directly onto SIG's evidence→claim lineage, and its partitions make
per-source, per-day backfill a first-class operation rather than a bespoke script.

**SIG-INGEST-021 (MUST).** The orchestration choice MUST be **reversible**. Every stage MUST be
runnable as a plain CLI invocation, with the orchestrator import confined to a single
`orchestration/` package. Replacing Dagster with cron MUST cost a configuration file, not a
rewrite. Rationale: a public-interest project on a volunteer footing must not be captured by a tool
whose licence or hosting economics may change.

**SIG-INGEST-022 (MUST NOT).** Orchestrators under AGPL, BUSL, or Elastic-style licences MUST NOT
be adopted (SIG-STORE-002). Kubernetes MUST NOT be a hard dependency.

---

## 22. The source registry and the federation compact

### 22.1 Structure

**SIG-INGEST-023 (MUST).** Every source MUST have a registry row carrying, at minimum: identity;
`custody_posture`; rights record with an SPDX expression; a **separately reviewed** `redistributable`
boolean; `default_tier` and source reliability `R`; access method; auth model; rate limits; observed
cadence; `compact_status`; `ingestion_permitted`; contact channel; and last-verified date.

**SIG-INGEST-024 (MUST).** `redistributable` MUST be a separately reviewed field, **not** derived
from the licence string. A permissive site-wide licence may not cover incorporated third-party data
(SC-09), and an unreviewed inference in either direction is a legal error.

### 22.2 The access matrix, as verified

Status recorded 2026-08-20. `VERIFIED` means a request was actually made and its outcome observed.

#### Physical layer

| Source | Access | Auth | Format | Rights | Status |
|---|---|---|---|---|---|
| OSM taginfo API | `taginfo.openstreetmap.org/api/4/*` | none | JSON | ODbL | **VERIFIED** |
| OSM Overpass | Public instances | none | JSON/XML | ODbL | Not yet tested — read etiquette rules first |
| OSM replication diffs | `planet.openstreetmap.org/replication/` | none | OSC | ODbL | Not yet tested |
| DeFlock | `deflock.me` **403**; `deflock.org` 200 | — | HTML | Unknown | **VERIFIED** — Cloudflare-fronted |
| Surveillance under Surveillance | 200 | none | HTML | Unknown | **VERIFIED** live |
| PanoptiCity | 200 | none | HTML | Unknown | **VERIFIED** live |
| Drivers Against Flock | 200 | none | HTML | Unknown | **VERIFIED** live |

#### Vendor / portal layer

| Source | Access | Rights | Status |
|---|---|---|---|
| **Flock transparency portals** | **403 on every path, incl. `robots.txt`** — Cloudflare managed challenge | ToS forbids bulk extraction | **VERIFIED — NOT ACCESSIBLE** (F2.1) |
| Eyes on Flock | 200 but **JS SPA**, 4.5 KB shell | Unknown | **VERIFIED** live; internals unresolved |
| Axon Community Connect | Public location listing + unauthenticated per-org stats endpoints | Unknown | **VERIFIED** — 321 communities enumerated (R7-F7.15) |

#### Usage / audit layer

| Source | Access | Rights | Status |
|---|---|---|---|
| Have I Been Flocked | 200, server-rendered; full audit-log field documentation | Unknown | **VERIFIED** (F2.3) |
| ALPR Watch | 200; GitLab org; Superset dashboard; KMZ/offline packages | Unknown | **VERIFIED** (F1.10) |

#### Adoption / accountability layer

| Source | Access | Rights | Status |
|---|---|---|---|
| **EFF Atlas of Surveillance** | Bulk CSV; >15,000 datapoints in 6,000+ jurisdictions; updated 2026-08-12 | `CC-BY-4.0` **with a third-party caveat** (SC-09) | **VERIFIED** |
| ALPR Accountability Atlas | 200 | Unknown | **VERIFIED** live |
| ALPR Abuse Library | 200 | Unknown | **VERIFIED** live |

#### Records / procurement / courts

| Source | Access | Auth | Limits | Status |
|---|---|---|---|---|
| **DocumentCloud** | `api.www.documentcloud.org` search + S3 assets | none for public | — | **VERIFIED — called** |
| **USAspending** | `spending_by_award` incl. **sub-awards**, `recipient/duns` | none | — | **VERIFIED — called** |
| **Legistar** | `webapi.legistar.com/v1/<client>/…` matters, attachments, histories, events | none | — | **VERIFIED — called** |
| **PrimeGov** | `<tenant>.primegov.com/api/v2/PublicPortal/…` | none | — | **VERIFIED — called** |
| **CivicClerk** | `<tenant>.api.civicclerk.com/v1/Events` + plaintext file stream | none | — | **VERIFIED — called** |
| **NextRequest** | undocumented `/client/requests`, `/client/request_documents` | none | — | **VERIFIED — called** |
| **CourtListener** | `/search/` open; `/dockets/`, `/opinions/`, `/parties/` **401** | token for most | **5/min, 50/hr, 125/day** | **VERIFIED** — crawling is impossible |
| **MuckRock** | **api_v2** (not v1); **401 on every data endpoint** | 5-min JWT | 15 req/min | **VERIFIED** — outline's v1 reference is wrong |
| SAM.gov | API | key | **10 requests/day** on the free tier | **VERIFIED** |
| OpenStates | API | key | 403 without | **VERIFIED** |
| **Sourcewell** | Free, unauthenticated: full solicitation record, signed contracts, monthly SKU price lists | none | — | **VERIFIED — files downloaded** |
| Wayback CDX | Availability + CDX API | none | — | **VERIFIED** |
| **Wayback for `*.flocksafety.com`** | **Excluded** — 403 + empty CDX with controls passing | — | — | **VERIFIED** |
| FBI CDE agency registry | `api.usa.gov/crime/fbi/cde/agency/byStateAbbr/{ST}` | api.data.gov key | 429s | **VERIFIED** |
| LEAIC crosswalk | ICPSR | login | — | **Manual acquisition** |

**SIG-INGEST-025 (MUST).** Four verified findings are architecture-determining and MUST be
reflected in phase planning, not discovered during implementation:

1. **The Flock portal layer has no lawful automated access path** (F2.1). Partnership,
   records requests, or human-mediated capture only.
2. **Flock domains are excluded from the Wayback Machine** — independently confirmed with passing
   controls (SC-13): `eff.org` returns captures from 1996 and `deflock.me` from 2024, while
   `transparency.flocksafety.com` returns zero captures and `flocksafety.com` returns no response
   body at all, which is the signature of an exclusion rule rather than of an unarchived host. There
   is therefore **no third-party archive to fall back on**. If SIG does not capture portal state
   through a lawful channel, *nobody does* — and because portal statistics are rolling rather than
   immutable, that history is being lost continuously, not merely left uncollected. Two
   consequences: any historical portal snapshots Eyes on Flock holds may be **globally unique**,
   which materially raises what SIG should be willing to offer in the collaboration and gives Phase 0
   a concrete first question; and SIG's archival-insurance role (§46.5) is this layer's only
   insurance rather than a courtesy.
3. **Court and records APIs are rate-limited to the point where crawling is impossible.** These
   are targeted-lookup sources, and any design assuming bulk court ingestion is void.
4. **Cooperative purchasing vehicles publish the full competitive record for free**, including
   signed contracts and monthly SKU price lists — while the agencies riding those contracts
   generate no local RFP. This is a major evidence channel the outline does not mention.

### 22.3 Sources the outline does not name

**SIG-INGEST-025a (MUST).** State reporting mandates MUST be modelled as **records-acquisition
leads, not as data feeds.** A statutory duty to *do* something is not a duty to *publish* it, and
neither implies a machine-readable dataset exists.

This is a correction, and it is grounded in the strongest available counter-case (SC-16). California
is the most ALPR-regulated state in the country — its ALPR statute has been in force since 2016 —
and as of 2026-08-20 it produces: **no recurring dataset**; **no central registry of the agency
policies the statute requires** (they are held decentrally and the state DOJ does not collect them);
**zero** hits for "ALPR" or "license plate reader" on the state open-data portal; **zero** ALPR
references in the state justice-data programme, whose bulk host is login-gated; and exactly **one**
relevant artifact — a 2020 state-auditor report whose 381-row agency survey is published as an HTML
table with **no CSV, XLSX, or JSON export of any kind**. A bill that would have mandated recurring
audits was **vetoed on the cost of the audits**; its successor's audit clause is
appropriation-contingent and the bill never uses the word "publish".

**SIG-INGEST-025b (MUST).** Two consequences bind the design:

1. The connector for this class is a **records-request generator** (§36) seeded from the statute —
   "this jurisdiction is required to hold X, therefore X is requestable" — not a scraper waiting for
   a feed. Statutory mandates are among the **best** leads SIG has, precisely because they establish
   that a record exists.
2. Where a one-time artifact does exist, it MUST be captured and parsed as an artifact
   (`state_auditor_survey`, §23.6) with its own `capture_status`, and MUST NOT create an expectation
   of recurrence. The absence of a follow-up is itself a `CoverageRecord` fact.

**SIG-INGEST-025c (MUST).** Legislative citations MUST be verified against the bill text and session,
never by bill number alone. Bill numbers are reused across sessions and across unrelated subjects:
in the California case, two later bills sharing a number with the ALPR bill are **Budget Acts**, and
a bill frequently cited alongside it concerns **facial recognition, not ALPR**. A `LegalInstrument`
claim MUST cite session and text, and a citation that cannot be resolved to text MUST NOT be
published.

**SIG-INGEST-026 (MUST).** The registry MUST include, in addition to every source in OL-21:

| Source | Why it matters |
|---|---|
| Cooperative purchasing bodies (Sourcewell, OMNIA, NASPO ValuePoint, BuyBoard, TIPS, HGACBuy, Equalis, GSA) | The dominant acquisition channel; free full contract records |
| Legistar / PrimeGov / CivicClerk / CivicPlus / NovusAgenda / BoardDocs / IQM2 / eScribe | Real APIs, not "agenda systems". **No municipality→platform directory exists; SIG should build one** |
| NextRequest / GovQA / JustFOIA / FOIAXpress | Published request logs with released-document URLs |
| USAspending **sub-awards** | Traces federal grant → local surveillance purchase (Byrne JAG, UASI) |
| FAA drone waiver releases | A federal regulator's dated authorization records with native validity intervals — an unusually clean `authorization_state` source |
| DHS fusion-center list | An authoritative roster (54 primary + 26 recognized = 80) |
| Municipal surveillance-ordinance (CCOPS) inventories | Statutory equipment inventories and impact reports, published on a legal cycle |
| State ALPR statutes and audits (CA SB 34, state auditor surveys) | **Leads to records, not feeds** — see SIG-INGEST-025a |
| GLEIF / SAM / FBI CDE / Census / NCES / IPEDS / NTD / CMS | The identity substrate (§14.2) |
| Footnote4a | A portal-tracking project surfaced via HIBF |
| eyesoffcr.org | A confirmed live local group |
| CourtListener / RECAP | Litigation evidence |

### 22.4 The compact and its enforcement

**SIG-INGEST-027 (MUST).** Each source's `compact_status` MUST be one of: `not_contacted`,
`contacted_awaiting_response`, `no_response`, `permission_granted`, `permission_granted_conditional`,
`permission_declined`, `public_terms_only`, `partnership_active`. **`no_response` is a recorded
state**, not an absence of one.

**SIG-INGEST-028 (MUST).** The pipeline MUST refuse to run a connector whose compact says ingestion
is not permitted (SIG-CHART-032). This is a runtime gate with a test, not a policy note.

**SIG-INGEST-029 (MUST).** For every project in the federation compact (§6), Stage 0 outreach MUST
have been attempted and its outcome recorded **before** a connector is written for it
(SIG-CHART-033).

### 22.5 The Eyes on Flock dependency

**SIG-INGEST-030 (MUST). — RESOLVED 2026-08-20.** Eyes on Flock exposes a **public,
unauthenticated, key-free JSON API**, verified directly (SC-18.1): `GET /api/v1/data` returns
HTTP 200, 7.6 MB, `{summary, portals}` with **950 portals** carrying `data_retention`,
`total_cameras`, `total_searches`, `vehicles_captured`, `hotlist_hits`, `hotlist_hit_rate`,
`organizations_shared_with`, `organizations_received_from`, `prohibited_uses`, `public_search_audit`,
`portal_url`, `slug`, `state`, `county`, `population`, `type`, and `data_last_updated`, plus national
roll-ups. **This maps almost field-for-field onto the outline's portal inventory (OL-2B-FP-02).**

`robots.txt` grants `User-agent: * → Allow: /` with `use=reference`. Licence: **CC BY-SA 4.0**.
Contact: `contact@eyesonflock.com`.

**The portal layer is therefore obtainable lawfully, without scraping the vendor and without a
headless browser.** Phase 11 is unblocked and risk R-02 is closed.

**SIG-INGEST-030a (MUST).** Outreach remains a **Phase 0 deliverable** even though the data is
already accessible — for three reasons that do not depend on access: ShareAlike attribution must be
agreed and correctly rendered; SIG MUST NOT poll faster than the upstream's own refresh
(SIG-INGEST-030c); and the archival-succession offer (SIG-CONTRIB-013) matters *more* now, not less,
because this API is a single point of failure for the only lawful route to the portal layer.

**SIG-INGEST-030b (MUST).** Historical back-fill MUST use the Internet Archive's captures of the API
endpoint itself rather than re-deriving history. Because the vendor's own domains are excluded from
the archive (SC-13) while this aggregator's are not, the aggregator's archived API responses are the
**only** available longitudinal record of portal state.

**SIG-INGEST-030c (MUST).** Change detection MUST key on the upstream's own `data_last_updated` /
snapshot field, **not** on SIG's fetch time, and SIG MUST NOT poll faster than the upstream
refreshes. This answers outline Q17 for this route: cadence is set by the upstream's recrawl, and
polling faster adds load without adding information.

**SIG-INGEST-031 (MUST).** The fallbacks remain documented and MUST be retained, because the API is
a single dependency: (a) public-records acquisition of the underlying configuration from agencies,
which is lawful and yields *better* evidence than the portal; (b) contributor-submitted captures
made by humans browsing normally; (c) partner archives. **Building a challenge-defeating crawler is
not on the list and MUST NOT be added to it.**

**SIG-INGEST-032 (SHOULD).** SIG SHOULD offer Eyes on Flock, and every single-maintainer upstream,
a mirroring and succession arrangement (§46.5) — SIG holds an archival copy that survives the
project, on terms the project sets. Given that Flock domains are excluded from the Wayback Machine,
this is the ecosystem's only insurance against permanent loss.

---

### 22.6 The seeded source registry

**SIG-INGEST-038 (MUST).** Phase 0 MUST seed the source registry with **every row below**. Each row
MUST receive a rights record, a custody posture, a `compact_status`, and an `ingestion_permitted`
flag. `Verified` records whether the lead research pass actually reached the URL on 2026-08-20;
**unverified rows MUST be verified during Phase 0 before any connector targets them.**

This section exists because a registry described in prose is not executable (SIG-ENG-001). Every
URL named in OL-21 appears here, plus every source added by research (§22.3).

#### A. Physical infrastructure

| Source | URL | Role | Verified |
|---|---|---|---|
| OSM surveillance tagging | `https://wiki.openstreetmap.org/wiki/Tag:man_made%3Dsurveillance` | Schema authority | — |
| OSM copyright / licence | `https://www.openstreetmap.org/copyright` | **ODbL authority** (§42.3) | ✅ |
| OSMF Licence Community Guidelines | `https://wiki.osmfoundation.org/wiki/Licence/Community_Guidelines` | Collective Database, Horizontal Layers, Substantial, Produced Work | ✅ |
| OSM taginfo API | `https://taginfo.openstreetmap.org/api/4/` | Tag statistics; vocabulary discovery | ✅ |
| OSM Overpass API | `https://overpass-api.de/api/interpreter` (+ mirrors) | Element extraction | — |
| OSM replication diffs | `https://planet.openstreetmap.org/replication/` | Incremental updates | — |
| OSM element history | `https://api.openstreetmap.org/api/0.6/node/<id>/history.json` | Per-element history (Q19) | — |
| OSM Automated Edits CoC | `https://wiki.openstreetmap.org/wiki/Automated_Edits_code_of_conduct` | **Hard constraint on write-back** (R-14) | — |
| DeFlock | **`https://deflock.org/` — use this** (200, serves the app) · `https://deflock.me/` (403, Cloudflare challenge fires ahead of a 301 to `.org`) | Upstream field observation | ✅ |
| DeFlock — canonical repos | `https://github.com/FoggedLens/deflock` (MIT) · `https://github.com/FoggedLens/deflock-app` (AGPL-3.0) | The real code | ✅ |
| ~~`flockhopper3/deflock-data`~~ | Cited at OL-21-04. **Exists, but belongs to a different project** — it is not DeFlock's | Do not treat as DeFlock | ✅ |
| Surveillance under Surveillance | `https://sunders.uber.space/` | Peer OSM visualization; evidence of the international community | ✅ |
| PanoptiCity | `https://panopticity.fr/` | FOV/coverage analysis; downstream consumer of derived geometry | ✅ |
| Drivers Against Flock | `https://driversagainstflock.org/` | Downstream consumer; **do not compete** | ✅ |

#### B. Vendor / portal layer

| Source | URL | Role | Verified |
|---|---|---|---|
| Flock transparency portals | `https://transparency.flocksafety.com/` | First-party config/usage. **403 on all paths — no lawful automated access** | ✅ |
| Flock API & Integration Terms | `https://www.flocksafety.com/legal/api-integration-terms` | ToS constraint | — |
| Eyes on Flock | `https://eyesonflock.com/` | **Top Stage-0 dependency** (§22.5) | ✅ |
| Eyes on Flock description | `https://www.reddit.com/r/FlockSurveillance/comments/1ra26qw/` | Methodology context | — |
| Axon Community Connect | `https://axoncommunityconnect.com/communities/` | Private-camera federation scale | ✅ |
| Footnote4a | `https://footnote4a.org/news/transparency-portals` | Portal tracking; surfaced via HIBF | — |
| CA sharing visualization | `https://www.reddit.com/r/FlockSurveillance/comments/1slvs6a/` | Archival-design precedent | — |

#### C. Usage and audit layer

| Source | URL | Role | Verified |
|---|---|---|---|
| Have I Been Flocked | `https://haveibeenflocked.com/` | Specialist upstream for usage | ✅ |
| HIBF methodology hub | `https://haveibeenflocked.com/about` | Methodology | — |
| HIBF audit-log guide | `https://haveibeenflocked.com/about/audit-logs` | **Canonical audit field schemas** (F2.3) | ✅ |
| ALPR Watch | `https://alprwatch.org/` | FOIA normalization; routing; offline packages | ✅ |
| ALPR Watch Flock FOIA method | `https://alprwatch.org/news/2025-07-28_flock_foia/` | Pipeline reference | — |
| ALPR Watch code | `https://gitlab.com/alprwatch-org` | **GitLab, not GitHub** (C-02) | ✅ |
| ALPR Watch FOIA dashboard | `https://superset.alprwatch.org/superset/dashboard/columbia-river-gorge-foia/` | Worked analysis | ✅ |
| flock.ajith.fyi | `https://flock.ajith.fyi/` | Network-topology visualization precedent | ❌ |
| Monahan, "Grounding the Flock" (2026) | `https://journals.sagepub.com/doi/10.1177/20501579261453519` | Academic framing. **403 — `capture_status = paywalled`** (SC-07) | ✅ |

#### D. Adoption layer

| Source | URL | Role | Verified |
|---|---|---|---|
| EFF Atlas of Surveillance | `https://www.atlasofsurveillance.org/` | **Primary deployment seed**; `CC-BY-4.0` w/ third-party caveat | ✅ |
| Atlas methodology | `https://www.atlasofsurveillance.org/methodology` | Evidence standards; the "not a complete inventory" statement | — |
| Atlas about / scope boundary | `https://atlasofsurveillance.org/pages/about` | Delegates the device layer to DeFlock (SC-10) | ✅ |
| Atlas Data Library | `https://www.atlasofsurveillance.org/data-library` | **Index of specialist datasets** (§22.7) | — |
| EFF copyright | `https://www.eff.org/copyright` | Licence authority for Atlas | ✅ |
| EFF Street-Level Surveillance | `https://www.eff.org/issues/street-level-surveillance` | Second technology taxonomy for crosswalk (§20.3) | — |
| **EFF Data Driven (2018 release)** | `https://www.eff.org/deeplinks/2018/11/eff-and-muckrock-release-records-and-data-200-law-enforcement-agencies-automated` | **Vendor-neutral ALPR network source** (§23.10) | — |

#### E. Accountability layer

| Source | URL | Role | Verified |
|---|---|---|---|
| ALPR Accountability Atlas | `https://alpratlas.org/` | Incidents; **the epistemic-label model SIG adopts** | ✅ |
| ALPR Abuse Library | `https://library.kansas.watch/` | Curated source index; held **unnormalized** (SIG-EPIS-030) | ✅ |
| **ACLU Get the Flock Out toolkit** | `https://www.aclu.org/get-the-flock-out-toolkit` | **Defines the local-advocate requirements the dossier serves** (§39.0) | — |
| ACLU cell-site simulators | `https://www.aclu.org/issues/privacy-technology/surveillance-technologies/stingray-tracking-devices` | Agency possession dataset | — |
| WIRED ShotSpotter sensor leak | `https://www.wired.com/story/shotspotter-secret-sensor-locations-leak` | Acoustic sensors; **leak-provenance veto applies** (SIG-PUB-005) | — |
| Guardian, Flock cameras (2026-08-20) | `https://www.theguardian.com/us-news/2026/aug/20/flock-cameras-surveillance` | Vendor-replacement reporting | — |
| CourtListener / RECAP | `https://www.courtlistener.com/api/rest/v4/` | Litigation. **~5/min, 50/hr, 125/day — lookup only** | ✅ |

#### F. Records, procurement, evidence

| Source | URL | Notes | Verified |
|---|---|---|---|
| MuckRock | `https://www.muckrock.com/` | **api_v2**; 401 on all data endpoints; 5-min JWT; ~15/min | ✅ |
| DocumentCloud | `https://api.www.documentcloud.org/api/documents/search/` | Public search + full text | ✅ |
| USAspending | `https://api.usaspending.gov/` | Prime **and sub-awards** (grant→deployment tracing) | ✅ |
| SAM.gov | `https://api.sam.gov/` | Vendor identity. **Free key = 10 requests/day** | ✅ |
| GovSpend | `https://www.govspend.com/` | Commercial procurement aggregator cited by Atlas; **paywalled — LINK posture** | — |
| Sourcewell | `https://www.sourcewell-mn.gov/` | **Free full competitive record + monthly SKU price lists** | ✅ |
| OMNIA Partners | `https://www.omniapartners.com/` | Cooperative vehicle | — |
| NASPO ValuePoint | `https://www.naspovaluepoint.org/` | Cooperative vehicle | — |
| BuyBoard / TIPS / HGACBuy / Equalis | `https://www.buyboard.com/` · `https://www.tips-usa.com/` · `https://www.hgacbuy.org/` · `https://equalisgroup.org/` | Cooperative vehicles | — |
| Legistar InSite API | `https://webapi.legistar.com/v1/<client>/` | Matters, attachments, histories, events | ✅ |
| PrimeGov | `https://<tenant>.primegov.com/api/v2/PublicPortal/` | Meetings, agendas | ✅ |
| CivicClerk | `https://<tenant>.api.civicclerk.com/v1/Events` | Meetings + plaintext file stream | ✅ |
| NextRequest | `https://<tenant>.nextrequest.com/client/requests` | Published request logs + released docs | ✅ |
| GovQA / JustFOIA / FOIAXpress | vendor-hosted per agency | Records portals | — |
| OpenStates | `https://v3.openstates.org/` | State legislation. 403 without key | ✅ |
| FBI CDE agency registry | `https://api.usa.gov/crime/fbi/cde/agency/byStateAbbr/{ST}` | **ORI9 authority** | ✅ |
| LEAIC crosswalk | ICPSR study 35158 | ORI↔FIPS↔place. **Manual acquisition** | — |
| Census Gazetteer / TIGER | `https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html` · `https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html` | GEOID + boundaries | — |
| Census Geocoder | `https://geocoding.geo.census.gov/geocoder/` | Address→jurisdiction (keyless) | — |
| GLEIF | `https://www.gleif.org/en/lei-data/gleif-golden-copy` | LEI, CC0 | — |
| NCES / IPEDS / NTD / CMS | `https://nces.ed.gov/ccd/` · `https://nces.ed.gov/ipeds/` · `https://www.transit.dot.gov/ntd` · `https://data.cms.gov/` | Per-class identifiers (§14.2) | — |
| Wikidata SPARQL | `https://query.wikidata.org/sparql` | QID crosswalk; **83.4% of ALPR manufacturers** | — |
| Internet Archive Wayback | `https://archive.org/wayback/available` | Archival. **`*.flocksafety.com` is excluded** (C-12) | ✅ |
| DHS fusion centers | `https://www.dhs.gov/fusion-center-locations-and-contact-information` | 80 centers (54 primary + 26 recognized) | — |
| FAA drone waivers | `https://www.faa.gov/uas/` + EFF FOIA release | Dated `authorization_state` records | — |

#### G. Lead generation

| Source | URL | Role | Verified |
|---|---|---|---|
| Flock Finder | `https://github.com/simeononsecurity/flock-finder` | RF/OUI candidates. **`R6`, lead generation only** | — |
| Flock-You | `https://github.com/colonelpanichacks/flock-you` | Local RF detection. **Never auto-confirms** | — |
| WiGLE | `https://wigle.net/` | Underlying radio observations | — |

#### H. Community ecosystem

| Source | URL | Role | Verified |
|---|---|---|---|
| FlockReporter | `https://flockreporter.org/` | Local-group directory. **Did not respond** (C-03, R-12) | ✅ (failure) |
| Eyes Off Cedar Rapids | `https://eyesoffcr.org/` | Confirmed live local group | ✅ |
| r/FlockSurveillance | `https://www.reddit.com/r/FlockSurveillance/` | Ecosystem discovery. **Blanket `Disallow: /`** — manual reference only | — |

**SIG-INGEST-039 (MUST).** Phase 0 MUST seed the **local-group registry** (SIG-TASK-014) with the
following. These URLs were **recovered from the last surviving archive capture of the ecosystem
directory and then individually re-tested** on 2026-08-20 (SC-11); they are not the outline's bare
names. A `403` here means the site is alive behind bot protection, not that it is gone.

| Group | URL | Verified 2026-08-20 |
|---|---|---|
| ALPR Pictures | `https://alpr.pictures/` | alive (403) |
| DeFlock Atlanta | `https://deflockatlanta.org/` | **200** |
| DeFlock Birmingham | `https://deflockbhm.com/` | **200** |
| DeFlock Joplin | `https://deflockjoplin.today/` | alive (403) |
| DeFlock Lynnwood | `https://deflocklynnwood.com/` | **200** |
| DeFlock Olympia | `https://deflockoly.noblogs.org/` | **200** |
| DeFlock Redmond | `https://bsky.app/profile/deflock-redmond.bsky.social` | **200** (no own domain) |
| DeFlock Tucson | `https://deflocktucson.com/` | **200** |
| DeFlock Vegas | `https://www.deflock.vegas/` | **200** |
| Eyes Off Cedar Rapids | `https://eyesoffcr.org/` | alive (403) |
| Eyes Off Colorado | `https://www.eyesoffcolorado.org/` | **200** |
| Eyes Off Indiana | `https://eyesoffindiana.org/` | **200** |
| Live Free VA | `https://livefreeva.org/` | **200** |
| Community Discord | `https://discord.gg/m9VsbR6d5z` | listed in the directory |

**SIG-INGEST-039a (MUST).** Two groups the outline names — **DeFlock Idaho** and the **Monterey
Park organizers** — do **not** appear in the recovered directory and MUST be registered as
`status = unlocated`, not silently dropped. Their absence is itself a coverage fact.

**SIG-INGEST-039b (MUST).** **FlockReporter, the directory itself, is dead.** Its DNS ceased to
resolve between 2026-07-28 (its last and only archive capture) and 2026-08-20. It MUST be
registered with `disappeared_observed_at = 2026-08-20`, its recovered capture retained as evidence,
and a research task generated (§33.2 #8). Its community Matrix room was homeserver-bound to the
same domain and died with it.

**This is the worked justification for §46.5, not a hypothetical.** A single-maintainer ecosystem
project vanished *during the research window for this specification*, and the directory survived
only because a third party captured it **exactly once**. That one capture is the entire margin
between recovering the ecosystem's coordination layer and losing it. Every group it indexed is
still alive; only the index died. SIG's archival-succession offer (SIG-CONTRIB-013) exists for
precisely this failure mode, and the cost of not having made that offer is now measurable.

**SIG-INGEST-040 (MUST).** Phase 0 MUST also register the national partner organizations that are
consumers and contributors rather than data sources — at minimum EFF, ACLU and its state
affiliates, EPIC, the Brennan Center, STOP, Oakland Privacy, Lucy Parsons Labs, Stop LAPD Spying,
MediaJustice, and the Reporters Committee — with contact channels, so that outreach and
correction-routing have somewhere to go.

#### H2. Projects the outline does not name (discovered 2026-08-20)

**SIG-INGEST-048 (MUST).** These MUST be registered in Phase 0. Four were created after mid-2025,
which is why the outline does not have them — and which is itself evidence that this ecosystem's
membership turns over fast enough that the registry needs a **recurring discovery sweep**, not a
one-time census.

| Project | URL | Licence | Why it matters |
|---|---|---|---|
| `none-below/sm-alpr` | `https://github.com/none-below/sm-alpr` | **AGPL-3.0** | The most sophisticated portal archiver found: daily dated captures per slug, sharing-graph builder, records-audit importer, **rename detection**, scrape diffing. Prior art for §29.7 |
| `eyes-off/eugene-oregon` | `https://github.com/eyes-off/eugene-oregon` | **CC0-1.0** | Long-term archive of search-audit CSVs, built explicitly to defeat the 30-day rolling window |
| `resistanceisliberty/panopti.ca` | `https://panopti.ca/` | **MIT** | Canadian DeFlock fork; bilingual EN/FR; also maps government CCTV. **Extends the model beyond the US** — a live Stage-6 precedent |
| `mcclatchy-southeast/private_eyes` | `https://github.com/mcclatchy-southeast/private_eyes` | **MIT** | A newsroom dataset that **flags portal-vs-reality discrepancies** in a controlled column. Direct prior art for §29.1 |
| `simeononsecurity/flock-finder` | `https://github.com/simeononsecurity/flock-finder` | **MIT** | RF/OUI detection modality (already at OL-21-25); actively maintained |
| `flock.ajith.fyi` | `https://flock.ajith.fyi/` | **none stated** | **Do not ingest.** Publishes raw operator identifiers (§43.2a) |
| `Ringmast4r/FLOCK` | `https://ringmast4r.github.io/FLOCK` | **none** | Claims "336K+ cameras worldwide"; unmaintained since 2025-11 |

**SIG-INGEST-048a (RATIONALE).** The last row closes an open question. An uncorroborated
"336K ALPRs" figure circulates in secondary coverage; direct measurement finds **144,312**
`surveillance:type=ALPR` elements (SC-03). The likely origin is this project's own headline claim.
It is unmaintained, unlicensed, and its figure is not reproducible from OSM — so the figure MUST NOT
be repeated, and this row exists so that a future contributor who encounters it can see why.

**SIG-INGEST-048b (MUST).** Two of these are **licence hazards** and MUST be handled as such:
`none-below/sm-alpr` is **AGPL-3.0**, so its *code* MUST NOT be linked into SIG's Apache-2.0
codebase (its *methods* may be studied freely); and two projects state **no licence at all**, which
under SIG-LIC-004 means `UNDETERMINED` and a closed export gate, not implied permission.

#### H3. Government-mandated disclosure (CCOPS) — a source class of its own

**SIG-INGEST-049 (MUST).** Municipal surveillance-ordinance disclosures MUST be registered as their
own source class, `government_mandated_disclosure`, distinct from both `civil_society_dataset` and
`vendor_portal`: `licence: public record`, `format: pdf`, `extraction: document_pipeline`.

**SIG-INGEST-049a (MUST).** It MUST be scoped as **depth, not breadth** — and the honest numbers
must be carried with it, because the temptation to oversell this class is real. It covers roughly
**26 jurisdictions**: about **5% of the US population** and **0.14% of US law-enforcement agencies**.
It will never be a national picture. **Zero** jurisdictions publish machine-readable output; the
canonical national list of which cities have such ordinances is an image file on an advocacy page.
Vocabularies, cadences, and scopes differ per city; at least one city runs months past its statutory
deadline; at least one blocks automated access.

**SIG-INGEST-049b (MUST).** Against that, it supplies **exactly the dossier fields SIG cannot obtain
anywhere else**: named sharing partners, acquisition and operating cost *including vendor-provided
freebies*, retention, audit mechanisms, deployment locations, signage and visibility, effectiveness
claims, complaint counts, and **real usage counts**. Several regimes are genuinely current.

**SIG-INGEST-049c (SHOULD).** Implement **three** connectors that pay for themselves — the city with
quarterly reporting and the richest per-technology detail; the city publishing 42 policies on a
stable URL pattern; and the city with a biannual citywide inventory carrying a compliance metric —
and route the remainder through the legislative-platform scrapers already required for §39.5.

**SIG-INGEST-049d (MUST).** This class's **highest value is calibration, not coverage**, and the
spec should treat it that way. These jurisdictions are the only places where SIG can check its
inferred picture against a **legally compelled disclosure**, which makes them the natural evaluation
corpus for the reconciliation engine (§28) and for measuring device-attribution accuracy (§29.2).
Roughly 1% of the adoption layer's row count, with perhaps twenty times the fields per row.

**SIG-INGEST-049e (MUST).** These disclosures also surface a finding class available nowhere else:
**non-compliance**. One city's own biannual inventory recorded a substantial share of technologies
in use *without* the policy the ordinance requires. That is a first-class `AccountabilityEvent`, and
SIG MUST be able to represent "the operator's own mandated disclosure says it is out of compliance."

**SIG-INGEST-049f (MUST).** State ALPR statutes MUST be seeded from the one national inventory that
exists, and **labelled with its date**: it is HTML-only, covers 16 states, and has been **frozen
since 2022-02-03** — predating the entire recent expansion, and demonstrably missing at least one
state statute enacted since. It is a one-time seed, never a feed, and SIG must maintain it onward.

#### H4. Future recurring sources — mandated but not yet flowing

**SIG-INGEST-050 (MUST).** Statutory disclosure duties that have been **enacted but whose first
reports are not yet due** MUST be registered now, with their commencement date, rather than
discovered when they begin.

At least one state statute mandates public posting of **nine specified items whose fields map almost
exactly onto SIG's deployment schema**, with first reports due **2027-04-01**. That is a genuine
recurring, structured, statutorily-compelled source — the thing this domain almost never has (§22.3,
SIG-INGEST-025a) — and it arrives on a known date.

Registering it early costs nothing and buys three things: the connector can be specified against the
statute's field list before any data exists; SIG can record the *absence* of reports before the due
date as a lawful `not_applicable` coverage state rather than a gap; and non-compliance after the due
date becomes immediately detectable and is itself an `AccountabilityEvent` (SIG-INGEST-049e).

#### I. International

| Source | URL | Role | Verified |
|---|---|---|---|
| Technopolice | `https://technopolice.fr/` | FR/BE mapping; Stage 6 model | ✅ |
| Technopolice mapping discussion | `https://forum.technopolice.fr/topic/405/cartographier-la-surveillance` | The OSM-vs-own-database debate | — |
| Technocarte update | `https://technopolice.fr/blog/mise-a-jour-de-la-technocarte/` | Dataset state | — |
| La Quadrature du Net | `https://www.laquadrature.net/` | Publisher | — |
| `sous-surveillance.net` → OSM import | OSM import wiki | ~12,000 cameras; activist-DB→commons precedent | — |
| TED (EU tenders) | `https://ted.europa.eu/` | EU procurement | — |
| DECP (FR procurement) | `https://www.data.gouv.fr/` | National open procurement data | — |

### 22.7 The Data Library specialist-dataset backlog

**SIG-INGEST-041 (MUST).** The EFF Data Library index is the **Phase 17 ingestion backlog**, and its
entries MUST be registered in Phase 0 rather than discovered later. Each is `LINK` posture until its
rights are reviewed.

| Dataset | Technology it populates | Phase 17 priority |
|---|---|---|
| Vigilant / Data Driven ALPR data | ALPR (vendor-neutral, historical) | **1 — also Phase 12** |
| Who Has Your Face? | Face recognition; reference databases | 2 |
| Clearview AI usage table (BuzzFeed) | Face recognition | 2 |
| Cell-site simulator datasets (ACLU) | `comms-intercept` | 3 |
| Upturn *Mass Extraction* | `device-forensics` | 4 |
| Public-safety drone datasets | `robotics-aerial` | 6 |
| Ring / Neighbors historical partnerships | Private-camera request. **Category retired 2024 — absence ≠ program ended** (SIG-ONTO-059) | 1 |
| California ALPR survey data (CA DOJ / SB 34) | ALPR; state reporting mandates | 1 |
| Federally funded body cameras | **Body-worn video** (§13.1) | 5 |
| Wiretap reports | `comms-intercept` | 3 |
| Aaron Swartz Day Police Surveillance Project | Multi | 7 |
| Electronic monitoring (MediaJustice) | `person-monitoring` | 7 |
| Atlas Border Communities | ALPR (checkpoint/covert) | 1 |
| AI Global Surveillance Index (Carnegie) | Country-level; **coarse granularity** (OL-5.3-02) | 8 |
| Facial Recognition World Map | Country-level | 8 |
| Mapping China's Tech Giants (ASPI) | Vendor-level, international | 8 |

**SIG-INGEST-042 (MUST).** Country-level datasets MUST be ingested as claims with **explicit coarse
granularity**, never disaggregated to agency level by inference (OL-5.3-02).

---

## 23. Connector specifications

Each connector is specified as: purpose; access path; incrementality; the predicates it may write;
the predicates it MUST NOT write; and its known failure modes. Only the governing rules and the
non-obvious constraints appear here; per-connector detail lives with the connector code and its
fixture suite (§48).

### 23.1 Universal connector rules

**SIG-INGEST-033 (MUST).** A connector MUST declare a **predicate allowlist**. Writing outside it
is a schema error. This is what prevents a portal scraper from asserting a contract date, or a
contract parser from asserting a current camera count — the `D6` admissibility filter (§10.5)
enforced at ingestion rather than only at resolution.

**SIG-INGEST-034 (MUST).** A connector MUST NOT perform entity resolution itself. It emits
candidate identifiers; the identity layer (§14.6) resolves them.

### 23.2 `osm` — physical assets

Writes: geometry, asset type, manufacturer, mobility, direction, mount, upstream ids, OSM version.
MUST NOT write: deployment linkage, operator attribution derived from SIG inference (that is L4),
contract facts.
Constraints: REQ-R1-01…R1-06. Handles nodes, ways, relations. Semicolon multi-values as sets.
Cross-key normalization. Preserves OSM element id **and version**, so a later OSM edit is detectable.
Output lands in the **ODbL-licensed** asset table (§42.3).

**SIG-INGEST-045 (MUST).** The connector MUST consume at minimum the following keys, and MUST record
any surveillance-bearing key it encounters outside this list as an unmapped value with a research
task (REQ-R1-02). Measured coverage is against the 144,312 elements tagged
`surveillance:type=ALPR` as of 2026-08-20 (R1-F1.5).

| Key | Carries | ALPR coverage | Handling |
|---|---|---|---|
| `man_made=surveillance` | The primary feature | 99.7% | Selection predicate |
| `surveillance:type` | Device kind — **116 distinct values** | — | Split on `;` as an unordered set; normalize via versioned mapping |
| `surveillance` | Zone — **430 distinct values**, polluted with types and booleans | 88.3% | Never trusted alone (R1-F1.4) |
| `surveillance:zone` | Zone (`traffic` 83.4%) | 87.4% | Cross-checked against `surveillance` |
| `camera:type` | `fixed` 92.0% | 92.4% | Drives `mobility`; ~8% are non-fixed |
| `camera:mount` | `pole` 22.4%, `street_lamp` 2.5% | 30.6% | Sparse → field-research task |
| `direction` | Bearing | **93.6%** | Input to derived FOV (§19.3) |
| `camera:direction` | Bearing (alternate) | 3.7% | Reconciled with `direction` |
| `manufacturer` | Vendor string — **7,031 distinct values** DB-wide | 86.9% | Normalize; `Flock Safety` 73.3%, `Motorola Solutions` present |
| **`manufacturer:wikidata`** | Vendor QID | **83.4%** | **First-class crosswalk key** (SIG-STORE-044) |
| **`operator`** | Operating organization | **19.1%** | **Absence is the ~116,800-device backlog** (SIG-ONTO-028) |
| `operator:wikidata` | Operator QID | 12.3% | Crosswalk |
| `operator:type` | Operator class | 2.9% | Sparse → research task |
| `brand` / `brand:wikidata` | Brand | 3.8% / 3.5% | Reconciled with manufacturer |
| `ref` | Device reference/label | — | Preserved as an upstream identifier |
| `start_date` / `check_date` | Installation / last verification | — | `valid_from` / staleness input |
| `source` | Provenance of the mapping | 1.7% | Recorded as source-dependence input (§10.8) |
| `electricity` | Power arrangement | 2.6% | Descriptive |
| `description` | Free text | 1.5% | `raw_value` only; never parsed into claims |

Non-camera surveillance types are in scope from Phase 4, not deferred: `gunshot_detector` (3,250
elements) and `AFR` (67) exist in OSM today (R1-F1.3).

**SIG-INGEST-045a (MUST).** `first_observed` MUST be derived from the element version at which
surveillance tags **first appeared**, obtained by walking the element history. It MUST NOT be read
from the element's creation timestamp.

**This is not a refinement; it prevents a systematic corruption of the temporal layer** (SC-17.3).
Measured on four live ALPR nodes: all were created on the same day in **2009** as part of a freeway
import, and all were **repurposed** into surveillance nodes on **2024-12-15** by adding tags to the
existing node. A connector reading the creation timestamp would date these devices to 2009 — before
the vendor existed — and would do so plausibly enough to escape notice, because old dates on road
infrastructure look unremarkable. At national scale this would corrupt exactly the property the
project exists to provide (OL-22.5).

**SIG-INGEST-045b (RATIONALE).** A bare OSM element id is **not** a well-defined reference across time.
The same id denoted a freeway feature for fifteen years and a surveillance device thereafter. Only
`(element_type, id, version)` is unambiguous, which is why REQ-R1-01 requires the version and why
§23.2 preserves it.

**SIG-INGEST-045c (MUST).** The element history endpoint
(`/api/0.6/<type>/<id>/history.json`) returns the complete version history with per-version tag sets
and is **verified working**. SIG MUST fetch it for elements under active reconciliation and MUST NOT
replicate the OSM history planet. This is the operative answer to outline Q19.

**SIG-INGEST-045e (MUST).** SIG MUST **discard OSM `user` and `uid` at ingest** and MUST NOT store
or expose them. A queryable table of *which mapper recorded which police camera* is a targeting
surface, and building one would make SIG a hazard to the volunteers it depends on. The upstream
history services adopt the same posture. `changeset` id is retained — it is the provenance anchor
and is not person-identifying on its face.

**SIG-INGEST-045f (MUST).** Element keys MUST be `(osm_type, osm_id)`, never `osm_id` alone: node,
way and relation id spaces are independent and overlap.

**SIG-INGEST-045g (MUST).** **Deletions require snapshot diffing.** Overpass's `(changed:…)` filter
reports modifications but **never reports deletions**, so a purely incremental connector would never
observe a device being removed. SIG MUST diff successive snapshots to detect disappearance, and MUST
distinguish *deleted from OSM* (a mapping event) from *removed from the street* (a world event) —
they are different claims with different predicates, and conflating them would let a mapper's
cleanup read as a decommissioning.

**SIG-INGEST-045h (MUST).** Overpass quotas are published and MUST be respected: **≤10,000
requests/day and ≤1 GB/day**, default `[timeout:180]`, `[maxsize:512MiB]`. `429` means slot
exhaustion — **back off in time**; `504` means the query was too large — **shrink it**. Retrying a
504 unchanged is useless and rude. The connector MUST poll `/api/status` rather than model quota
locally, because one DNS name fronts independently rate-limited servers.

**SIG-INGEST-045i (MUST NOT).** The Overpass documentation explicitly names *"stitching bounding
boxes to scrape the full data of the complete world"* as prohibited use and directs bulk consumers
to a planet dump. SIG MUST therefore use **PBF + tag filtering for bulk** and reserve **tiled
Overpass for increments**. A worldwide unbounded query fails in practice regardless.

**SIG-INGEST-045j (MUST).** SIG MUST NOT use another project's self-hosted Overpass instance without
that project's explicit permission, even where it is publicly reachable.

**SIG-INGEST-045d (MUST).** The Overpass connector MUST send a **descriptive** User-Agent with a
contact address. A browser-spoofed agent returns **HTTP 406** from the public instance — the
politeness requirement of §26 is mechanically enforced here, not merely conventional. The connector
MUST also avoid spaces in Overpass tag-value filters, which trip a request filter; filter
client-side instead.

### 23.3 `atlas` — agency adoption

**Input shape.** The upstream's methodology combines nine components, each of which is a different
evidence genre and therefore a different `R`/`D` profile that SIG MUST preserve rather than flatten
into one tier: OSINT; news reporting; government documents; meeting minutes; press releases;
procurement leads (including commercial procurement aggregators); crowdsourcing; staff and intern
review; and imported specialist datasets (OL-2D-AT-02). Where the upstream records which component
produced a row, SIG MUST carry it; where it does not, SIG MUST record the granularity loss rather
than assign a tier by guess.

Writes: `deployment_exists` at family-level technology granularity, with Atlas's own source
attribution preserved.
MUST NOT write: device counts, coordinates, configuration, current status.
Constraints: key on the Atlas agency identifier, routing non-ORI-shaped values to the surrogate path.
Preserve Atlas source attribution and allow later evidence to supersede or temporally qualify
(OL-2D-AT-06). Record the Atlas vocabulary version, and record category retirements so a
disappearance is never read as a world change (SIG-ONTO-059).

### 23.4 `flock_portal` — via the aggregator API

**SIG-INGEST-035 (MUST).** This connector MUST source the portal layer from the **aggregator's
public CC BY-SA 4.0 API** (§22.5, SC-18), and MUST NOT attempt direct capture from the vendor, whose
every path returns a bot challenge (F2.1). Output MUST land in the **CC BY-SA 4.0 compartment**
(SIG-LIC-004a), never merged into the CC-BY graph.

**The discovery problem, stated because it sizes the fallback.** The vendor publishes **no directory
of portals**. Portal discovery has historically been performed by **brute-force enumeration over
candidate locality/agency URL slugs** — which is why Eyes on Flock's discovery work is
infrastructural rather than cosmetic (OL-2B-EOF-02, OL-A.1). Combined with F2.1 (every path returns
403 to a scripted client) this means SIG **cannot discover portals at all** by its own lawful means.
Discovery must come from a partner, from contributor reports of portals they have visited, or from
agency-side records confirming a portal exists. An implementer who does not understand this will
under-size the Phase 11 fallback.

**Writes when enabled:**

| Predicate | Volatility | Notes |
|---|---|---|
| `active_device_count` | FAST | `D1` for this predicate |
| `configured_retention_days` | MODERATE | Distinct from policy and vendor default (§29.5) |
| `configured_sharing_partner` | FAST | Directional; configured access only |
| `state_lookup_enabled`, `national_lookup_enabled`, `federal_sharing_enabled` | VOLATILE | |
| `subscribed_hotlist_topic` | VOLATILE | |
| **`vehicles_detected_windowed_count`** | VOLATILE, `h`=1 mo | **Windowed** (SIG-RECON-011) |
| **`hotlist_hit_windowed_count`** | VOLATILE, `h`=1 mo | **Windowed.** One of the two headline statistics the portal-aggregation ecosystem exists to collect |
| `usage_search_windowed_count` | VOLATILE, `h`=1 mo | **Windowed** |
| **`portal_stated_permitted_use`** | SLOW | `R2 · D2`. A **first-party portal statement**, distinct from an adopted `Policy` document (§11.13) |
| **`portal_stated_prohibited_use`** | SLOW | Same |
| `portal_exists` / portal disappearance | — | An event on the artifact (§17.6) |
| `portal_last_updated_declared` | — | The portal's own claim about its freshness; never trusted as `observed_at` |

MUST NOT write: contract facts, device geometry, or any per-search row.

### 23.5 `records` — MuckRock, NextRequest, DocumentCloud

Writes: `RecordsRequest` entities, `EvidenceArtifact` rows, released-document captures.
Constraints: MuckRock is **api_v2** with auth on all data endpoints and a short-lived JWT; the
outline's api_v1 reference is wrong. `no_responsive_records` is a positive finding feeding the
coverage model (SIG-ONTO-040).

### 23.6 `procurement` — cooperative vehicles, USAspending, agenda platforms

Writes: `Contract`, `FundingInstrument`, `acquisition_channel`, quantities, renewal terms,
lifecycle transitions with dates.
Constraints: cooperative piggyback contracts MUST set `parent_cooperative_contract`. USAspending
sub-awards MUST be pulled, not only prime awards. Agenda platforms are per-tenant APIs, so the
connector needs a tenant registry, which SIG must build and publish (§22.3).

**SIG-INGEST-047 (MUST).** The `artifact_type` vocabulary (§10.3.2) MUST additionally carry
`state_auditor_survey`, `warrant`, and `procurement_aggregator_record`, and the source registry MUST
carry the commercial procurement aggregator named by the upstream Atlas methodology as an origin of
its procurement leads — under a `LINK` custody posture, because it is paywalled. Several state
auditors periodically survey agencies on surveillance-technology holdings; those surveys are `R1`
government datasets and are among the highest-value under-exploited sources available (OL-2F-GOV-02).

### 23.7 `audit_structural` — HIBF / agency audit exports

Writes: `UsageAggregate`, configured sharing edges from `SharedNetworks.csv`, event-log lifecycle
transitions, and `Camera Count` observations.
MUST NOT write: any per-search or per-plate row (§18.1).
Constraints: REQ-R2-05…R2-09. `***` redaction ≠ empty. Portal audit schema is agency-configured
and must be discovered per capture. The four audit source types are **not interchangeable** and
MUST be recorded on every aggregate.

**SIG-INGEST-046a (MUST).** Where an upstream publishes **derived** rather than primary data, SIG
MUST NOT ingest it as though it were the underlying record.

The specialist audit project's bulk exports are derived artifacts: plate values are **hashed**,
person names are **inferred** with confidence scores, reasons are **redacted**, and editorial
annotations are **injected into the data fields themselves**. Ingesting those rows as agency records
would silently import another project's inferences into SIG's graph **as though they were
observations** — the exact confusion the whole epistemic model exists to prevent (§10.1).

Such data MUST be ingested, if at all, as `R3` claims **about the upstream's conclusions**, with the
upstream named as the asserting party and its inference method recorded — never as `R1`/`R2` claims
about the agency. Where SIG needs the primary record, it MUST obtain it by records request.

**SIG-INGEST-046b (MUST).** A `robots.txt` disallow MUST be honoured **even where the data behind it
is technically reachable**. That project's exports exist, but its `robots.txt` disallows the API
path serving them. Reachability is not permission (§26 rule 2). The correct action is to **ask** —
which is Stage-0 outreach, and which the succession offer (SIG-CONTRIB-013) makes worth answering.

**SIG-INGEST-046c (MUST).** An **affirmative machine-readable rights reservation** MUST be honoured
as a refusal and recorded on the rights record. One ecosystem project combines
`Content-Signal: ai-train=no`, explicit AI-crawler disallows, and an **EU DSM Article 4 reservation**
— a formal opt-out with legal effect in the EU. `UNDETERMINED` and *"affirmatively refused"* are
different states and MUST be stored differently: the first invites a Stage-0 conversation, the
second closes it.

**SIG-INGEST-046 (MUST).** The upstream specialist's six documented capabilities (OL-2C-HIBF-08) are
dispositioned as follows, explicitly, so that none is silently dropped:

| Capability | SIG's disposition |
|---|---|
| Officer / name resolution | **Deliberately not performed.** SIG does not ingest per-search rows, so no officer names enter (SIG-PUB-010, §18.1). This is discharge by exclusion, and it is intentional, not an omission |
| Police rosters | **Not ingested.** A roster is a list of natural persons; §11.3 forbids `Person` rows outside the officer test. SIG references the upstream's roster work rather than reproducing it |
| Duplicate handling | Applies at the **aggregate** level: overlapping audit exports covering the same period MUST be deduplicated by `(source_org, searching_org, window)` before aggregation, and the overlap recorded |
| Source-agency provenance | Preserved: every aggregate carries the audit export it came from and that export's requesting agency |
| Anomaly detection | SIG consumes the upstream's published anomaly findings as `R3` claims; it does **not** rebuild detection over data it does not hold |
| Records-request templates | Reused, with attribution, in the request generator (§36) |

### 23.8 `accountability` — Accountability Atlas, Abuse Library, CourtListener

**Input shape (Accountability Atlas).** The upstream publishes five artifacts, each of which MUST be
consumed rather than only the headline CSV: an **issue-record CSV**; a **source-index CSV**; a
**GeoJSON**; a **data dictionary**; and a **research archive** (OL-2E-AA-02). The data dictionary is
the authority for the crosswalk (§20.3), and the source index is what allows SIG to preserve the
distinction between an event and the reporting about it. Its record categories — local
regulation/action, litigation, wrongful stop / false alert, immigration / data sharing,
security / product issues, stakeholder / company context — MUST be crosswalked, not adopted
wholesale.

Writes: `AccountabilityEvent`, `LegalProceeding`, source-class-tagged evidence links.
Constraints: `epistemic_status` is REQUIRED and preserved verbatim from the upstream where the
upstream provides one. Court APIs are targeted-lookup only (§22.2). A curated source index MAY be
ingested as an index without normalizing entries into facts (OL-2E-AL-02).

### 23.9 `data_driven` — the vendor-neutral historical ALPR network

**SIG-INGEST-043 (MUST).** EFF/MuckRock's Data Driven releases MUST be ingested as a **first-class
connector**, not treated as background reading. The outline designates them a priority ingestion
source for the first vendor-neutral ALPR model (OL-4.2-01), and they are the only substantial public
evidence base for pre-Flock, non-Flock ALPR network behaviour.

Writes: historical `Organization` rows; historical `configured_access` edges across a vendor network;
`deployment_exists` claims for a non-Flock vendor; aggregate scan/hit-rate observations.
MUST NOT write: current-state claims of any kind — every claim from this source carries its
historical `observed_at` and is subject to normal currency decay (§28.3), which for
`configured_sharing_partner_set` (FAST, 4-month half-life) means these claims are `C4 HISTORICAL`
and cannot resolve present-tense questions.

**SIG-INGEST-043a (MUST).** The dataset is **retrievable and MUST be ingested with its measured
values**, not paraphrased. Verified figures: **200 agency rows × 20 columns** across 23 states plus
a federal row; **2,541,566,055 detections against 11,384,164 hits — 99.552% of scans matched no
hotlist**; a mean of **160.2 direct sharing partners** per agency (maximum **851**); and **130
agencies** feeding a vendor-operated pooled lookup service. A companion release covering 89 agencies
in one state independently gives **99.948%** non-hit.

The non-hit proportion is the most analytically important number in the corpus and the easiest to
lose in summary: it establishes that ALPR collection is **overwhelmingly of uninvolved vehicles**,
which is a structural property of the technology rather than of any one vendor.

**SIG-INGEST-043b (MUST).** The connector MUST target the **file artifacts directly**. The
article URL cited by the outline (OL-21-35) is a **dead end containing no data links**; the data
lives at separate file paths. Record both, and mark the article as context rather than as the source.

**SIG-INGEST-043c (MUST).** A hard limitation MUST be recorded with the ingest: all **463
source-document links resolve to a document host that blocks automated access**. SIG therefore
obtains **sharing degree** — how many partners each agency had — but **not the sharing edge list**.
The distinction matters: degree supports the claim "this agency shared with 851 others"; it does not
support drawing any specific edge. Rendering degree as if it were a known network would be exactly
the unexplained edge the defining standard forbids.

**SIG-INGEST-043d (MUST).** This corpus already contains **vendor-specific retention-window columns
in incommensurable units** — a 30-day-window column for one vendor alongside other vendors' figures.
This is direct, dated evidence for the incommensurable-counts problem (§29.1) appearing *five years
before* the current vendor landscape, and the connector MUST preserve the window definition per
column rather than normalizing the values together.

**SIG-INGEST-044 (RATIONALE).** This connector's value is **structural, not current**: it proves that
cross-agency ALPR networks predate and exceed any single vendor (OL-2D-DD-03), and it supplies the
historical baseline against which vendor-replacement analysis (§29.4) is measured. A Flock-only
graph would mis-model the problem, and this connector is the concrete guard against that.

---

### 23.10 `rf_candidates` — lead generation

Writes: `CandidateAsset` only, at `R6`.
MUST NOT write: `PhysicalAsset`, or anything with `residential_parcel_flag = true` (§43.5).

---

## 24. Document parsing and extraction

### 24.1 Layered strategy

**SIG-PARSE-001 (MUST).** Parsing MUST proceed by the cheapest sufficient method, with the method
recorded on the extraction:

| Layer | Method | Use when |
|---|---|---|
| 1 | Structured import (CSV/XLSX/JSON/GeoJSON) | The source is already structured |
| 2 | Deterministic selector/template extraction | Stable HTML or a known form layout |
| 3 | PDF text extraction | Digital-native PDF |
| 4 | PDF table extraction | Tabular content in a digital PDF |
| 5 | OCR | Scanned documents |
| 6 | LLM-assisted structured extraction | Unstructured prose where 1–5 fail (§25) |
| 7 | Human transcription | Everything else, and all adjudication |

**SIG-PARSE-002 (MUST).** File classification MUST run before parsing, and its verdict MUST be
recorded. Real records responses arrive as mixed-format ZIPs containing scanned faxes,
password-protected PDFs, XLSX with merged headers, and native exports with multiple sheets.

**SIG-PARSE-003 (MUST).** Every extraction MUST emit a **locator** (page, bbox, cell, row, byte
range, DOM path) for every claim. An extraction that cannot say where a value came from MUST be
rejected, because the evidence viewer (§39.6) and the defensibility guarantee (OL-24-18) both
depend on it.

**SIG-PARSE-004 (MUST).** Extraction MUST preserve the raw literal in `raw_value` before any
typing or normalization (P2), including for values that fail to parse. A value SIG could not parse
is data about the source, not an error to be dropped.

### 24.2 Reason-code normalization

**SIG-PARSE-005 (MUST).** Free-text reason fields MUST be normalized through a **versioned,
inspectable, reversible** mapping stored as data. The raw text MUST be retained; the mapping
version MUST be recorded on every claim; and changing the mapping MUST NOT rewrite history
(SIG-STORE-038). *(OL-2C-AW-04, OL-2C-AW-05.)*

**SIG-PARSE-006 (MUST).** Reason fields arrive in **two** forms — free text and constrained
dropdowns — depending on configuration. These are different normalization problems and MUST be
distinguished on the claim, because a dropdown value is a much stronger signal than a typed phrase.

### 24.3 Parser drift

**SIG-PARSE-007 (MUST).** Every parser MUST have committed fixtures (real captured inputs, expected
outputs) so that an upstream redesign fails a test rather than silently producing garbage (§48).

**SIG-PARSE-008 (MUST).** Fixtures alone are insufficient: they pin known inputs and keep passing
forever. A **nightly canary** MUST run each parser against live sources and alert on structural
change. *(R11 identifies silent parser drift as a top-5 operational risk.)*

---

## 25. LLM usage policy

### 25.1 Permitted uses

**SIG-LLM-001 (MAY).** Models MAY be used for: proposing candidate structured claims from
unstructured documents; suggesting reason-code categorizations; suggesting entity aliases;
drafting summaries **for human reviewers**; and generating review rationales.

### 25.2 Prohibited uses

**SIG-LLM-002 (MUST NOT).** Models MUST NOT:

1. be the **sole basis** for a published factual claim;
2. write directly to the graph without review at or above the threshold of §14.6 tier 4;
3. overwrite, paraphrase, or "clean" source text (P2);
4. produce confidence values (§10.6 — confidence is computed by rule, from evidence);
5. resolve contradictions;
6. create a `Person` row (SIG-ONTO-016);
7. promote a `CandidateAsset` (§43.5);
8. determine a sensitivity classification.

### 25.3 Required scaffolding

**SIG-LLM-003 (MUST).** Every model-assisted extraction MUST record `model_id`, `prompt_version`,
and the deterministic parameters actually used, and MUST validate output against a schema.

**SIG-LLM-004 (MUST).** Every model-extracted claim MUST carry a **source span** — the exact text it
came from — and an extraction that cannot cite its span MUST be rejected (SIG-PARSE-003). This is
the single most important guardrail: it makes hallucination detectable mechanically, because a span
that does not appear in the capture fails validation.

**SIG-LLM-005 (MUST).** Model-extracted claims MUST be `R6` (§10.4) and enter as `PROPOSED`.

**SIG-LLM-006 (MUST).** A sampling rate for human review MUST be defined per extraction type, and
accuracy MUST be measured against a gold set on a published cadence. If measured accuracy falls
below the published threshold, the extraction type MUST be demoted to human-only.

**SIG-LLM-007 (MUST).** The pipeline MUST degrade gracefully when the model is unavailable: work
queues, it does not fail, and no claim is emitted with a lower evidentiary standard to compensate.

---

## 26. Crawler conduct

**SIG-INGEST-036 (MUST).** SIG MUST adopt and publish a Crawler Conduct Policy binding on every
connector. Its operative rules:

1. **Identify.** A descriptive UA with a contact URL and an explanation page. No spoofing.
2. **Honor `robots.txt`**, including AI-crawler directives and content-signal headers. Where
   robots.txt is unretrievable, permission is **not granted** (SIG-INGEST-012).
3. **Rate-limit conservatively**, per host, with backoff. Never burden a small civic host.
4. **Never circumvent access controls** — no authentication bypass, no paywall evasion, no
   challenge-solving, no proxy rotation or human-mimicking to defeat bot management.
5. **Prefer the offered channel.** If a source publishes an API, a bulk download, or a partner
   feed, use it instead of scraping the HTML.
6. **Ask first** where the compact is unresolved and the source is a small civil-society project.
7. **Honor opt-out** immediately and record it in the compact.
8. **Cache aggressively; refetch rarely.** Conditional requests, content-hash short-circuits.

**SIG-INGEST-037 (MUST).** Rule 4 is not merely ethical. Circumvention techniques have been held
to support anti-circumvention claims independent of any computer-fraud theory, and vendor API terms
in this sector expressly prohibit bulk extraction (R8). The policy is also a **legal posture**, and
deviating from it is an ADR-level decision requiring counsel, not an engineering judgment.

---

# Part V — Resolution, reconciliation, and inference

## 27. Entity resolution pipeline

Specified at §14.6–14.8. The operational requirements that belong to the pipeline rather than the
model:

**SIG-RECON-001 (MUST).** ER MUST run as a distinct pipeline stage between `normalize()` and
`load()`, with its own run record, its own quality report, and its own rollback path.

**SIG-RECON-002 (MUST).** ER MUST be **re-runnable** over historical claims without destroying the
prior clustering. A re-clustering produces new `same_as` assertions with a new ruleset version; it
does not silently move claims between entities.

**SIG-RECON-003 (MUST).** No network-analytics surface may ship before the §14.7 quality gates
pass, and every centrality or hub statistic MUST carry an ER-quality disclosure in the UI (P6).

---

## 28. The reconciliation engine

This is the intellectual core of the project. The outline states the requirement (outline §6.2, §6.5, §22.1); this section makes it executable.

### 28.1 Rule-based and auditable, by requirement

**SIG-RECON-004 (MUST).** Resolution MUST be **deterministic, rule-based, and explainable**. It
MUST NOT use an unsupervised truth-discovery model, a learned scorer, or any procedure whose output
cannot be traced to a named rule.

**Rationale, stated because the alternative is tempting.** The truth-discovery literature offers
elegant iterative source-weighting methods. They are the wrong tool here for three reasons: their
weights are not explainable to a journalist defending a claim; they assume source independence that
this ecosystem violates (§10.8); and they optimize for accuracy against a hidden truth, whereas
SIG's obligation is to be *defensible about its reasoning*, which is a different objective. A rule
that is 3% less accurate and fully explainable is the better instrument for this project.

**SIG-RECON-005 (MUST).** The ruleset MUST be **data, not code** — versioned, diffable, testable,
and separately attributable from the resolver implementation (SIG-STORE-017).

### 28.2 The algorithm

**SIG-RECON-006 (MUST).** `RESOLVE(subject, predicate, as_of_world, as_of_belief, ruleset)` MUST
execute these phases in order:

```
Phase 0  GATHER
  0.1  claims := {c : c.subject = S, c.predicate = P, c.sys_period contains as_of_belief}

Phase 1  ADMISSIBILITY            (admissibility is prior to weight)
  1.1  drop if review_status ∈ {retracted, withdrawn}
  1.2  drop if valid_period does not intersect as_of_world
  1.3  drop if D(genre(c), P) = D6                    ← non-probative for THIS predicate
  1.4  drop if superseded by a later claim from the SAME source with the same valid_time
  1.5  if empty → UNRESOLVED(NO_EVIDENCE)

Phase 2  CANONICALIZE
  2.1  canonicalize units, enum casing, entity identity, date granularity
  2.2  if a claim cannot be canonicalized → emit Contradiction(VALUE_DOMAIN_MISMATCH), drop
  2.3  if P is a count predicate and claims disagree on count_basis
       (contracted vs installed vs active vs mapped vs reported):
         emit Contradiction(PREDICATE_CONFLATION); drop the mismatched claims
         ← the §29.1 guard: NEVER silently compare different things

Phase 3  WEIGHT
  3.1  W(c) := compose(R, D, I, C)                    ← §10.6
  3.2  W0 claims leave the resolving set but are retained for display

Phase 4  INDEPENDENCE
  4.1  group claims into independence classes          ← §10.8
  4.2  W(class) := max W within the class
  4.3  per candidate value: supporting classes, method breadth, best weight

Phase 5  STRATEGY
  5.1  apply the predicate's resolution strategy       ← §28.4
  5.2  produce a TOTAL order over candidates

Phase 6  AMBIGUITY TEST                                ← §28.5
  6.1  if AMBIGUOUS → UNRESOLVED(first triggering condition, candidates, rationale)

Phase 7  EMIT
  7.1  winner, support, agreement, currency            ← §10.7
  7.2  supporting / dissenting / excluded claim ids with exclusion reasons
  7.3  independence classes, rules fired, ruleset version
  7.4  input_digest = hash(sorted claim ids + content hashes)
  7.5  as_of_world, as_of_belief, computed_at
```

**SIG-RECON-007 (MUST).** The ranking MUST be a **total order**. The universal final tie-break,
applied after every strategy's own criteria are exhausted, is:

```
(weight desc, method_breadth desc, observed_at desc, source_registry_rank asc, claim_id asc)
```

Since `claim_id` is stable, the order is fixed forever. **There MUST be no random tie-break
anywhere in the system** — a resolution that could differ between two runs over identical inputs is
not reproducible and cannot be cited.

### 28.3 Predicate volatility and currency

**SIG-RECON-008 (MUST).** Every predicate MUST carry a volatility class and half-life `h`. Currency
is derived at query time:

```
age = as_of_world − observed_at
C1 CURRENT      age ≤ 0.5h
C2 AGING        0.5h < age ≤ 1.0h
C3 STALE        1.0h < age ≤ 3.0h
C4 HISTORICAL   age > 3.0h        (IMMUTABLE predicates: h = ∞, always C1)
```

**SIG-RECON-009 (MUST).** The volatility table is ruleset data and MUST be recalibrated once SIG
has observed enough change-rate data to measure it. Initial assignment:

| Predicate class | Volatility | `h` |
|---|---|---|
| Contract dates, contract value, contracted quantity | IMMUTABLE | ∞ |
| Organization legal name, jurisdiction, ORI | GLACIAL | 10 y |
| Vendor of product, product capabilities | GLACIAL | 5 y |
| `deployment_exists` | SLOW | 3 y |
| `asset_operator` attribution | SLOW | 3 y |
| Written policy values | SLOW | 2 y |
| Fixed asset location | SLOW | 2 y |
| `asset_exists_at_location`, procurement status | MODERATE | 12 mo |
| `configured_retention_days`, vendor default retention | MODERATE | 9 mo |
| `operational_state`, `active_device_count`, `installed_device_count` | FAST | 6 mo |
| `configured_sharing_partner_set` | FAST | 4 mo |
| National/state lookup toggles, hotlist configuration | VOLATILE | 2 mo |
| Windowed usage counts | VOLATILE | 1 mo |

**SIG-RECON-010 (MUST).** For IMMUTABLE and GLACIAL predicates, **recency MUST NOT break a tie**.
A newer claim about a 2019 signing date has no advantage from being newer.

**SIG-RECON-011 (MUST).** **Windowed predicates are indexed, not stale.** A 30-day search count for
July does not become "stale" in August — it becomes *a value for July*. Windowed predicates carry
explicit window bounds in `valid_period` and are **exempt from currency downgrade for the window
they describe**. What decays is the *current rate*, which is a different, derived predicate with its
own volatility. Conflating these produces "412 searches in the last 30 days" on a dossier whose
underlying data is nine months old — a specific, avoidable, and highly visible failure.

### 28.4 Per-predicate strategies

**SIG-RECON-012 (MUST).** Every predicate MUST be assigned a resolution strategy in the ruleset:

| Strategy | Applies to |
|---|---|
| `latest_observation_wins` | FAST/VOLATILE operational state, active counts, sharing sets |
| `authoritative_source_wins` | Legal facts: contract dates, values, statutory citations |
| `interval_union` | Coverage and validity spans where sources report partial periods |
| `interval_intersection` | Facts requiring simultaneous support |
| `max_support` | Categorical facts with no clear authority ordering |
| `never_resolve` | Predicates SIG records but deliberately does not adjudicate (e.g. a contested data-controller assertion, §12.4) |

**SIG-RECON-013 (MUST).** A predicate with no assigned strategy MUST NOT be resolvable
(SIG-ONTO-067). Silence in the ruleset produces `UNRESOLVED`, never a guess.

### 28.5 The ambiguity test — when SIG refuses to answer

**SIG-RECON-014 (MUST).** `UNRESOLVED` MUST be returned when any of the following holds, evaluated
**in order** so the reason is deterministic:

| id | Condition | Why |
|---|---|---|
| `U0` | No admissible claims after Phase 1 | No evidence — distinct from balanced evidence |
| `U1` | Best weight ≤ `W1` | Nothing above weak; a tip alone never resolves |
| `U2` | Top and second have equal weight, disjoint independence classes, and equal method breadth | A genuine standoff between equal independent evidence |
| `U3` | The winner has exactly one class, and a dissenting method-distinct class is at `W2`+ | One source versus one source is never resolvable by fiat |
| `U4` | Numeric predicate; relative spread exceeds the predicate's tolerance; nothing dispositive | Numbers too far apart to pick between |
| `U5` | Winner's currency is STALE/HISTORICAL and the predicate is MODERATE/FAST/VOLATILE | **The best answer is too old to assert about a changing quantity** |
| `U6` | Claims were dropped for `count_basis` mismatch and fewer than two survive | The remainder cannot be compared |
| `U7` | An open `Contradiction` on this pair has severity BLOCKING | A human flagged it as not-safe-to-publish |
| `U8` | Agreement would be IRRECONCILABLE and support below CONFIRMED | Strong unreconciled dissent beats a merely-strong winner |

**SIG-RECON-015 (MUST).** **`U5` is the rule the outline lacks entirely, and it is essential.** It
is what stops SIG from publishing "42 active cameras" in 2026 on the strength of a 2024 contract —
*even with no dissent at all, even from a Tier-A source*. Silence plus age is not a resolution. In
this domain, where deployments change quietly and constantly, an unchallenged stale number is the
most likely way for SIG to publish something false.

**SIG-RECON-016 (MUST).** On `U5`, SIG MUST publish the stale value as `last_known` **with its
date**, not suppress it. "38 as of 2026-07-01, not since verified" is useful; a blank is not.

**SIG-RECON-017 (MUST).** `UNRESOLVED` is **not an error and MUST NOT be hidden**. It renders as an
explicit finding with all candidate values, their evidence, and an automatically generated research
task (§33). Declining to grade is a standards-compliant output, not a failure.

### 28.6 Independence and dependence discounting

Specified at §10.8. The engine-side requirement:

**SIG-RECON-018 (MUST).** Corroboration MUST be counted per independence class and per distinct
collection method, never per claim. A candidate value supported by five claims from one class has
the support of **one** class.

### 28.7 Recomputation, versioning, immutability

**SIG-RECON-019 (MUST).** Resolutions MUST be recomputed when: a new claim lands on the pair; a
claim is superseded; the ruleset version changes; or **currency crosses a class boundary** — the
last of which happens with no data change at all, purely through the passage of time, and is the
reason resolutions cannot be cached indefinitely.

**SIG-RECON-020 (MUST).** A resolution MUST be reproducible from `(claims + ruleset_version +
resolver_version + as_of pair)`, verified by the stored `input_digest`. CI MUST regenerate a sample
and assert a match (SIG-STORE-018).

**SIG-RECON-021 (MUST).** Resolutions MUST NEVER be edited in place. A new resolution supersedes
the old one in transaction time.

### 28.8 Rationale generation

**SIG-RECON-022 (MUST).** Every resolution MUST carry a human-readable rationale generated from a
**versioned template** filled from the resolution's own structured fields. It MUST name which
sources mattered, and which corroborate or conflict.

Worked examples of conformant rationales:

> "38, as reported by the agency's transparency portal captured 2026-07-01. The portal is the most
> direct available source for currently active devices. The executed contract's figure of 42 is
> recorded separately as the contracted quantity; it is not evidence of the active count."

> "Unresolved. The contract specifies 30 devices and the portal reported 28 on 2026-07-01, but the
> two figures describe different quantities and no source establishes the active count directly.
> Both values are shown with their evidence."

> "Unresolved, stale. The most recent evidence for this deployment's operational state is 31 months
> old, and operational state typically changes within about six months. Last known: active, as of
> 2024-01-12."

> "Confirmed. Three independent sources using different collection methods — an executed contract,
> council minutes, and a vendor press release — agree on a signing date of 2025-03-14."

> "Contested. The agency's written policy prohibits immigration-related queries, while a
> configuration export dated 2026-05-02 shows an immigration hotlist enabled. Both are first-party
> evidence and neither supersedes the other; the disagreement is the finding."

**SIG-RECON-023 (MUST).** Every rationale template MUST pass a committed template test asserting
that its rendered output: (a) contains no unresolved placeholder; (b) names at least one source; (c)
attributes every value to a source or to a named rule; (d) contains no support term and agreement
term in the same sentence (SIG-EPIS-025); and (e) uses no evaluative adjective from the prohibited
list in the style guide (§41). Template changes MUST re-run this suite.

*Rationale (not itself testable).* The target is that a journalist can quote the rationale verbatim
without adding interpretation. Clauses (a)–(e) are the mechanical properties that make that
achievable.

### 28.9 Human override

**SIG-RECON-024 (MUST).** A curator MAY pin a resolution. The override is itself recorded with
`decided_by` and a mandatory `override_rationale`, is displayed in the UI **as an editorial act**,
and is subject to the same review and correction process as any other claim (SIG-STORE-019).

**SIG-RECON-025 (MUST).** An override MUST NOT delete or hide the algorithmic result. Both are
shown, so a reader can see that a human disagreed with the rule and why.

---

## 29. The reconciliation workflows

### 29.1 Camera-count reconciliation

Discharges OL-11.1-01, OL-11.1-02, OL-11.1-03.

**SIG-RECON-026 (MUST).** The count predicates MUST be **distinct and never conflated**. The
outline's §11.1 (OL-11.1) nearly collapses them; the collapse is the error the whole workflow exists to
prevent.

| Predicate | Means | `D1` source | Volatility |
|---|---|---|---|
| `contracted_device_count` | Quantity the contract obliges | Executed contract | IMMUTABLE per contract |
| `invoiced_device_count` | Quantity actually billed | Invoice | IMMUTABLE per invoice |
| `installed_device_count` | Physically mounted, working or not | Inventory; field survey | MODERATE |
| `active_device_count` | Producing data now | Portal; audit `Camera Count`; vendor statement | FAST |
| `mapped_device_count` | Independently field-observed and mapped | OSM/DeFlock | **A lower bound only** |
| `claimed_device_count` | What someone said in public | Press release; council presentation | FAST |

**SIG-RECON-027 (MUST).** `mapped_device_count` MUST be treated as a **lower bound**, never as an
estimate of the true count. Mapping coverage is opportunistic and incomplete by construction.

**SIG-RECON-028 (MUST).** Phase 2.3 MUST refuse to compare claims with different `count_basis`,
emitting `PREDICATE_CONFLATION` instead.

**The worked case, and why it dissolves.** The outline's own Appendix B presents "42 contracted vs
38 portal-reported vs 31 mapped" as a contradiction to be resolved. Under this model it is **not a
contradiction at all**. The contract's 42 is `contracted_device_count` at `W4` (R1 · D1 · I1 · C1,
since contract quantity is IMMUTABLE). The *same artifact* for `active_device_count` is R1 · **D5**
· I1 · C3 → **W1**. The portal's 38 is R2 · D1 · I1 · C1 → **W3**, and wins `active_device_count`
by two weight classes. The OSM 31 is a lower bound on a third predicate.

So there are three correct answers to three different questions — plus **one genuine finding**: an
unresolved delta of 4 between contracted and active, and a gap of at least 7 between active and
mapped. Those deltas are the research tasks. This is what the outline means by "reconciliation, not
aggregation," made mechanical.

**SIG-RECON-029 (MUST).** The output object MUST carry every count predicate with its own
resolution, plus `unresolved_delta` values with their interpretation, plus the evidence for each,
plus the generated research tasks. It MUST NOT emit a single "true count."

### 29.2 Device attribution

Discharges OL-11.2-01, OL-11.2-02. This is the workflow that addresses the ~116,800 mapped ALPRs
with no operator (SC-08.1).

**SIG-RECON-030 (MUST).** Candidate generation MUST consider: spatial containment in a
jurisdiction; distance to the nearest deployment of a matching technology; road-network context
(a device on a county road inside a city is ambiguous by construction); jurisdiction adjacency;
manufacturer/vendor match against the deployment's product; and unexplained count gaps in the
jurisdiction (a deployment with 8 unmapped devices makes nearby orphans more likely to be its).

**SIG-RECON-031 (MUST).** Output MUST be an **inference at L4**, labelled `probable`, never an
observation. It MUST NOT be written into the asset's `operator` as though observed, and MUST NOT be
pushed to OSM automatically (§35.2).

**SIG-RECON-032 (MUST).** The hard cases MUST be modelled rather than resolved by default:

| Case | Required handling |
|---|---|
| Device on a county road inside city limits | Multiple candidate operators; do not default to the containing jurisdiction |
| State-police device inside a city | Containment is not attribution |
| Device operated by A on behalf of B | Both roles recorded (§12.4); attribution names the *role* it attributes |
| Multi-agency shared deployment | Multiple operators is a valid answer, not a conflict |
| Device on a jurisdiction boundary | Ambiguous by construction; enqueue rather than pick |

**SIG-RECON-033 (MUST).** Promotion from `probable` to asserted requires human confirmation or a
`D1`/`D2` documentary source. A high inference score MUST NOT promote itself.

### 29.3 Sharing-edge reconciliation

Discharges OL-11.3-01, OL-11.3-02.

**SIG-RECON-034 (MUST).** The three edge types of §12.2 MUST be reconciled **separately**. There is
no operation that merges them.

**SIG-RECON-035 (MUST).** **Asymmetry is a finding, not an error.** Where A's configuration export
lists B, and B's export does not list A, SIG MUST record both observations, emit a
`SHARING_ASYMMETRY` contradiction, and generate a research task. Possible explanations — one export
is stale, one direction was disabled, the exports have different semantics, one organization is
misidentified — are all interesting, and picking one silently destroys the signal.

**SIG-RECON-036 (MUST).** A sharing edge from a single snapshot carries `valid_from_kind =
'unknown'` (SIG-ONTO-044). SIG MUST NOT infer a start date from first observation.

**SIG-RECON-037 (MUST).** An `observed_use` edge MUST NOT create or imply a `configured_access`
edge, and vice versa — even though use logically implies access existed at the time of use. The
inference is available at L4, clearly labelled; it is not permitted at L1.

### 29.4 Deployment lifecycle reconciliation

Discharges OL-11.4-01, and the §22.5 requirement to distinguish removal from replacement.

**SIG-RECON-038 (MUST).** Each of the four tracks (§13.4) MUST be resolved **independently** at each
point in time. A single-timeline reconciliation is impossible because the tracks are orthogonal.

**SIG-RECON-039 (MUST).** Event-log transitions, where available, are the highest-quality evidence
and MUST be preferred over inferred transitions (REQ-R2-09).

**SIG-RECON-040 (MUST).** Fuzzy-dated events MUST be ordered using EDTF envelopes, and where two
events' envelopes overlap such that their order is indeterminate, the timeline MUST record them as
**unordered-within-window** rather than picking an order.

**SIG-RECON-041 (MUST).** The vendor-replacement pattern MUST be detected and rendered explicitly:
where a deployment reaches `procurement:canceled|nonrenewed` and another deployment of the same
technology family begins at the same organization within a configured window, SIG MUST create a
`replaced_by` edge and MUST render the pair as **"vendor replaced"**, never as "surveillance
removed."

**SIG-RECON-042 (MUST).** Where `procurement:canceled` coexists with `physical:installed`, the UI
and API MUST state both plainly: *"contract canceled; hardware still present as of <date>."* This
is the single most politically consequential distinction the system makes (OL-22.5-02), and it MUST
NOT be smoothed into either summary.

### 29.5 Retention reconciliation

**SIG-RECON-043 (MUST).** `policy_written_retention_days`, `configured_retention_days`, and
`vendor_default_retention_days` are **three predicates**. Their disagreement is a finding (P10).
Vendor defaults MUST NOT populate configuration (SIG-ONTO-036), and a vendor's default change does
not retroactively change existing deployments — a distinction that has real-world instances.

### 29.6 Policy-versus-configuration reconciliation

**SIG-RECON-044 (MUST).** SIG MUST detect and surface policy/configuration divergence as a
first-class finding, with both sides' evidence, and MUST NOT editorially collapse it
(OL-8.12-02). The canonical instance — a written policy prohibiting immigration-related use
alongside an enabled immigration hotlist — MUST be expressible and renderable.

### 29.7 Snapshot-diff reconciliation

**SIG-RECON-045 (MUST).** Consecutive captures of the same artifact MUST be diffed at the
**extracted-field level**, producing per-field change events with both values and both dates. This
is what makes "what changed, and when" answerable, and it is the basis of the change feed and of
several research-task detectors.

### 29.8 Additional workflows

**SIG-RECON-046 (MUST).** The following MUST also be implemented: **cost/contract-value**
reconciliation (contract vs invoices vs budget line vs cooperative SKU pricing);
**organization-existence** reconciliation (an organization named in a network list that no registry
knows — §14.4); **capability** reconciliation (does org X have capability Y, across disagreeing
sources, respecting the marketed-vs-configured distinction of SIG-ONTO-018); and
**geographic-coverage** reconciliation.

---

## 30. The inference layer

**SIG-RECON-047 (MUST).** Inferences live at L4 in a separate namespace, carry `derivation_rule`,
`derived_at`, and `input_claim_ids`, are labelled in every surface, and are droppable and
recomputable (§8.1, SIG-GEO-006).

### 30.1 The inference catalog

| Inference | Inputs | Confidence treatment | Invalidation trigger |
|---|---|---|---|
| Device→deployment attribution | §29.2 | Never above `probable` without human confirmation | Any input claim changes |
| Field-of-view geometry | Asset point + direction + mount + assumed optics | Always labelled modelled; assumptions published | Asset geometry or direction changes |
| Jurisdiction assignment | Asset geometry + jurisdiction boundary | High, but boundary-temporal | Boundary or geometry changes |
| Org hierarchy transitivity | `parent_of` chains | High; bounded depth | Any edge changes |
| **Access-path closure** | Access + integration edges | See §30.4 | Any edge on the path changes |
| Network centrality | Resolved edges | Gated on ER quality (P6) | Any edge changes |
| Product-default capability | `Product.can_offer` | `product_default`, low (SIG-ONTO-018) | Configuration evidence arrives |
| Coverage estimates | §32 | Explicit method disclosure | Any input changes |

### 30.2 Access-path closure — SIG's most powerful and most dangerous inference

**SIG-RECON-048 (MUST).** "Can organization A reach organization B's data, through any chain?" is
the transitive-closure question that OL-22.4-01 identifies as central. It MUST be implemented,
and it MUST be bounded.

**SIG-RECON-049 (MUST).** Closure MUST obey these limits:

1. **Only `configured_access` and `federates_search_to` edges compose.** `observed_use` does not
   compose — that A searched B and B searched C does not mean A can search C.
2. **`distributes_list_to` does not compose in the query direction.** A hotlist flowing outward
   creates no inbound search path (§12.3 rule 3).
3. **Scope must be respected.** A partner-scoped edge does not chain into a national-scoped one.
4. **Every hop must be currently valid** at the as-of time; a path through an expired edge is a
   *historical* path and MUST be labelled as such.
5. **Path length MUST be capped and reported.** Every published path MUST show its full hop list
   with each hop's evidence. An unexplained "A can reach B" is exactly the "unexplained edge" the
   defining standard forbids.
6. **Confidence is the minimum over the path**, never the average — a chain is as strong as its
   weakest hop.

**SIG-RECON-050 (MUST).** Beyond a published hop count, closure output MUST be labelled
**speculative** and excluded from headline figures. The difference between "these two agencies
share data" and "a seven-hop theoretical path exists" is the difference between a finding and an
insinuation, and SIG must not blur it — including when the blurred version would be more striking.

### 30.3 Prohibited inferences

**SIG-RECON-051 (MUST NOT).** SIG MUST NOT infer: any natural person's identity, location, or
movements; that a device is active because it exists; that configuration matches policy; that a
vendor default applies to a specific deployment; that absence of evidence is evidence of absence;
that a candidate asset is real; or that an organization's surveillance posture resembles its
neighbours'.

### 30.4 Labelling

**SIG-RECON-052 (MUST).** Every inference MUST be visually and structurally distinguishable from
observation in the UI, the API, and every export — including derived map layers, where the
distinction must survive at a glance (§39.1).

---

## 31. Contradiction as a first-class object

Discharges OL-6.5-01, OL-6.5-02, OL-24-11.

**SIG-RECON-053 (MUST).** `Contradiction` MUST be a materialized entity with:

| Field | Notes |
|---|---|
| `subject_id`, `predicate_id` | What is disputed |
| `contradiction_type` | `value_disagreement`, `predicate_conflation`, `value_domain_mismatch`, `sharing_asymmetry`, `policy_configuration_divergence`, `temporal_impossibility`, `count_basis_mismatch`, `identity_ambiguity`, `undeclared_copying` |
| `claim_ids[]` | The disagreeing claims |
| `severity` | `informational`, `notable`, `blocking` |
| `status` | `open`, `under_research`, `resolved`, `accepted_unresolvable`, `superseded` |
| `resolution_note`, `resolved_by`, `resolved_at` | |
| `research_task_ids[]` | What was generated to close it |

**SIG-RECON-054 (MUST).** `severity = blocking` MUST force `UNRESOLVED` (`U7`). This is the manual
brake: a curator who believes a value is unsafe to publish can stop it without deleting anything.

**SIG-RECON-055 (MUST).** A resolved contradiction MUST remain **visible in history**. Resolution
sets status; it does not delete (OL-24-20).

**SIG-RECON-056 (MUST).** `accepted_unresolvable` MUST be a legitimate terminal state. Some
disagreements cannot be settled with available evidence, and saying so is more honest than an
indefinite open task.

**SIG-RECON-057 (MUST).** Every contradiction detector MUST emit a research task with a defined
closing condition (§33.3). The detector→task contract is what turns disagreement into work
(OL-6.5-02).

---

## 32. Coverage, completeness, and quality metrics

Discharges Goal 6 (OL-7.1-06) and the negative-claims doctrine (OL-9.4).

### 32.1 The coverage record

**SIG-METRIC-001 (MUST).** `CoverageRecord` MUST make negative claims **queryable**:

| Field | Notes |
|---|---|
| `subject_id` / `subject_class` | An entity, or a class within a jurisdiction |
| `predicate_id` | What was sought |
| `absence_kind` | `not_researched`, `searched_not_found`, `evidence_of_absence`, `not_applicable` |
| `sources_searched[]` | **Required for `searched_not_found`** |
| `searched_at`, `searched_by` | |
| `search_method` | |

**SIG-METRIC-002 (MUST).** "Not in the Atlas" and "not in the Atlas, not in any portal, and not in
three years of council minutes" are very different statements, and `sources_searched[]` is what
distinguishes them (§9.5). Without it, coverage is rhetoric.

**SIG-METRIC-002a (MUST).** Discovery probes MUST **retain their negatives**. Where SIG enumerates a
candidate identifier space — portal slugs, agency identifiers, tenant names — every probe that
returned "does not exist" MUST be stored as a `CoverageRecord` with `absence_kind =
searched_not_found`, not discarded.

This is not bookkeeping. An ecosystem project's published database demonstrates the value directly:
it retains **5,011 confirmed-absent slugs alongside 495 confirmed-present ones** (R2-F2.15). The
negatives are what convert "we found 495 portals" into "we tested 5,506 candidates and 495 exist" —
which is a denominator (SIG-METRIC-003), a measure of enumeration completeness, and a way to detect
a *new* portal appearing later without re-probing the entire space. Discarding negatives throws away
the more informative half of the result.

### 32.2 Published denominators

**SIG-METRIC-003 (MUST).** **Every** published aggregate MUST carry its denominator and the count
excluded for lack of evidence. "37 agencies share data outside their state" is non-conformant.
"37 of 214 evaluable agencies; 1,109 not evaluable for lack of evidence" is conformant.

**SIG-METRIC-004 (MUST).** Per-jurisdiction coverage MUST be computed and published: agencies
known; agencies with any deployment evidence; deployments with contract evidence; with portal
evidence; with mapped devices; mean evidence age; open contradiction count; and the claim
weight-class distribution.

### 32.3 Provenance completeness

**SIG-METRIC-005 (MUST).** The share of published claims with a resolvable evidence artifact MUST
be measured, published, and **targeted at 100%**. Any shortfall is a defect list, not a statistic.

### 32.4 Freshness

**SIG-METRIC-006 (MUST).** Freshness MUST be measured **relative to predicate volatility**, not in
absolute days. A two-year-old contract date is fresh; a two-year-old active count is historical.

**SIG-METRIC-007 (MUST).** A public data-freshness page MUST show, per source: last successful
run, last content change, current status, and the count of entities whose evidence is stale for
their predicate class. A freshness dashboard is itself a trust affordance.

### 32.5 Completeness estimation — and why capture–recapture is prohibited

**SIG-METRIC-008 (MUST NOT).** SIG MUST NOT publish a capture–recapture estimate of device
population from volunteer mapping and vendor portal reporting. **Not with a caveat, not with a wide
interval.** *(This supersedes an earlier permissive formulation; the correction is R13 §12.4.)*

The Lincoln–Petersen estimator `N̂ = n₁n₂/m₂` fails here on four counts, and the first is
dispositive on its own:

1. **Linkage is impossible, so `m₂` is undefined.** Recapture requires knowing *which* individuals
   appear in both samples. Transparency portals publish a **count, not an inventory** — no device
   identifier, no location, no matchable attribute. Estimating `m₂` from the two totals assumes the
   answer. No version of the analysis survives this.
2. **Closure fails.** `active_device_count` is FAST (six-month half-life). Any window wide enough to
   accumulate both lists exceeds the closure horizon, and the samples are not even contemporaneous:
   an OSM observation time is an *edit* time, a systematically optimistic upper bound on when a
   human actually looked.
3. **Independence fails, in the worst direction.** Portal publication is opt-in and self-selected;
   agencies that publish are disproportionately those under local scrutiny — which is also where
   volunteer mappers are. The capture probabilities are **positively correlated**, which inflates
   `m₂` and therefore **deflates `N̂`**. The estimator would not be noisy; it would be **biased low
   by an unknown amount**. A public-interest project must not publish a number whose known failure
   mode is *understating the thing it exists to document*.
4. **Capture heterogeneity is structured and shared.** Roadside survey misses rear-facing,
   obscured, and private-property devices; portal reporting misses whatever the vendor does not
   instrument. Both blind spots track the same urban/rural and salience gradients.

**SIG-METRIC-008a (MUST NOT).** Multi-list log-linear models MUST NOT be used as a rescue. They
require three or more lists **with individual-level linkage**, and they cannot identify the
highest-order interaction — which is precisely the one that matters here, since every available list
shares a single latent "public visibility" factor.

**SIG-METRIC-008b (MAY).** There is exactly one legitimate application. Where SIG holds a
**records-derived installation list with locations** for a specific jurisdiction — the only true
device-level inventory available in this domain — a two-sample estimate against a **blind** field
survey of that jurisdiction is defensible, because linkage is possible and the processes are
genuinely independent when the survey is conducted without sight of the list.

Even then it MUST be understood and labelled as measuring **the field survey's recall in that
jurisdiction**, not the device population. It MUST be pre-registered, conducted inside a window
shorter than the predicate's half-life, and published as a **measurement of SIG's method**. It MUST
NOT be extrapolated to any other jurisdiction. Validation exercises do not extrapolate.

**SIG-METRIC-009 (MUST).** What SIG publishes instead: counted quantities with **named
denominators**; records-derived **bounds** where an inventory exists; per-agency reconciliation
ratios; and measured survey recall on a named calibration subset. **Never a total.**

**SIG-METRIC-010 (MUST NOT).** SIG MUST NOT publish a completeness percentage that implies it knows
the denominator of reality. The defensible claim is coverage of *known* entities plus an explicit
statement that the true population is unknown (SIG-CHART-019).

### 32.6 Ecosystem leverage metrics

**SIG-METRIC-011 (MUST).** The leverage measures of §7 MUST be instrumented and published, because
the project's stated definition of success depends on them and an unmeasured goal is a slogan.

---

# Part VI — Research coordination

The outline calls automatic research-lead generation "one of the most distinctive project
features" (OL-12-00) and says it turns the graph into a research coordination system rather than a
passive database (OL-3-07). This part specifies that machinery.

## 33. Research-task generation

### 33.1 The detector specification language

**SIG-TASK-001 (MUST).** Every task type MUST be declared as data, with all of:

| Field | Meaning |
|---|---|
| `task_type` | Stable slug |
| `detector` | A versioned query over the graph |
| `priority_fn` | How urgency is computed |
| `closing_condition` | **What evidence would close it** — testable |
| `assignee_class` | `field_mapper`, `records_requester`, `document_reviewer`, `analyst`, `local_group`, `curator`, `developer` |
| `effort_estimate` | |
| `dispositions[]` | The permitted outcomes (§33.4) |
| `geographic_scope` | For queue assignment |

**SIG-TASK-002 (MUST).** A task type with no testable `closing_condition` MUST NOT be registered.
"Research this" is not a task; "obtain a document establishing X, or record that the agency states
no such document exists" is.

### 33.2 The task catalog

**SIG-TASK-003 (MUST).** At minimum the following MUST be implemented. The first seven are the
outline's (OL-12-01…07); the remainder are required additions.

| # | Task type | Detector | Assignee |
|---|---|---|---|
| 1 | Missing physical devices | `active_device_count` > `mapped_device_count` | field_mapper / local_group |
| 2 | Missing contract | Deployment evidenced, no procurement evidence | records_requester |
| 3 | Conflicting retention | Policy vs configuration divergence | records_requester |
| 4 | Stale evidence | Currency STALE/HISTORICAL for the predicate class | analyst |
| 5 | Orphaned device | Asset with manufacturer, no operator | field_mapper / records_requester |
| 6 | New sharing node | Organization in a network list, absent from the registry | analyst |
| 7 | Vendor replacement | Cancellation + new deployment in window | analyst |
| 8 | Portal disappeared | Artifact disappearance event | analyst |
| 9 | Portal appeared, no known deployment | New portal, no deployment record | analyst |
| 10 | Contract expiring | `end_date` within N days, no renewal evidence | local_group / analyst |
| 11 | **Sharing asymmetry** | Edge asserted by one side only | analyst |
| 12 | Device/jurisdiction mismatch | Asset in A attributed to B | field_mapper |
| 13 | Retention changed without policy change | Config change, no policy claim | records_requester |
| 14 | Network org without jurisdiction | Org resolved, no jurisdiction | analyst |
| 15 | Adoption without corroboration | Atlas row; no portal, contract, or device | records_requester |
| 16 | Grant with no deployment | Surveillance grant awarded, no follow-up evidence | analyst |
| 17 | Vendor acquisition relink | Acquisition event; products need re-linking | curator |
| 18 | Sole-source / Tier-F support | A claim's only support is `R5`/`R6` | analyst |
| 19 | Long-unverified claim | `unreviewed` beyond threshold | curator |
| 20 | **Link rot** | Artifact URL now 404s | developer / analyst |
| 21 | Re-extraction available | Better parser version exists for stored captures | developer |
| 22 | Candidate duplicate entities | ER tier 4/5 pair | curator |
| 23 | Litigation without docket | Proceeding with no court record link | analyst |
| 24 | Incident with only secondary sources | No `R1`/`R2` support | records_requester |
| 25 | Unmapped vocabulary value | Source value outside the vocabulary | curator |
| 26 | **Authorized but not deployed** | `authorization=authorized` ∧ `physical=not_installed` | analyst |
| 27 | Canceled but installed | `procurement=canceled` ∧ `physical=installed` | field_mapper |
| 28 | Free-trial capability | `operational=active` with no procurement transition | records_requester |
| 29 | Cooperative contract unexplored | Piggyback contract with no master record | document_reviewer |
| 30 | Coverage hole | Jurisdiction with population above threshold and zero evidence | local_group |
| 31 | Unresolved contradiction aging | Open contradiction beyond threshold | curator |
| 32 | Candidate asset awaiting verification | `CandidateAsset` corroborated, unpromoted | field_mapper |
| 33 | **Contract amendment chain incomplete** | A contract's terms are contradicted by a later source (extended `end_date`, changed quantity, exercised renewal) with no `amends_contract` child on file | records_requester |
| 34 | **Sharing snapshot stale** | The newest `configured_access` observation for a deployment exceeds the FAST volatility threshold | records_requester |

**SIG-TASK-004 (MUST).** Every contradiction detector (§31) MUST map to a task type. Detection
without a route to resolution is just an alarm.

### 33.3 Lifecycle

**SIG-TASK-005 (MUST).** `generated → triaged → claimed → in_progress → submitted → verified →
closed`, with `reopened` and `invalidated` transitions.

**SIG-TASK-006 (MUST).** Tasks MUST auto-invalidate when their detector no longer fires — evidence
arriving by another route MUST silently close the task rather than leaving stale work in the queue.

**SIG-TASK-007 (MUST).** Duplicate suppression MUST be by `(task_type, subject)`, and claiming MUST
have a timeout so an abandoned claim returns to the pool.

### 33.4 Dispositions — the queue must be able to shrink

**SIG-TASK-008 (MUST).** Every task MUST support a **disposition vocabulary** richer than "done":

| Disposition | Meaning |
|---|---|
| `resolved_evidence_found` | The evidence was obtained; claims landed |
| `resolved_no_evidence_exists` | Searched; the record does not exist. **Writes a `CoverageRecord`** |
| `blocked_access_denied` | Request denied; records the denial as evidence |
| `blocked_fee` | A fee demand blocks it; records the amount |
| `blocked_awaiting_response` | Filed, pending |
| `not_actionable` | The detector fired on a modelling artifact |
| `superseded` | Another task subsumes it |
| `deferred` | Valid but not now, with a review date |

**SIG-TASK-009 (MUST).** `resolved_no_evidence_exists` MUST write a `CoverageRecord` with
`absence_kind = searched_not_found` and the sources searched. **This is the mechanism by which
negative results become data instead of nothing** — and without it, the queue can only grow, which
is how contributor systems die.

### 33.5 Geographic queues (Q36)

**SIG-TASK-010 (MUST).** A local group MAY **claim a jurisdiction**, which grants visibility,
notification, and priority in queue ordering. It MUST NOT grant exclusivity.

**SIG-TASK-011 (MUST).** Claims MUST expire without renewal, and any contributor MUST remain able
to work any open task. Geographic claiming is a coordination affordance; if it hardens into
territorial gatekeeping it defeats the federation principle, and the expiry is the safeguard.

### 33.6 Anti-abuse

**SIG-TASK-012 (MUST).** Tasks MUST NOT be gamified with public leaderboards ranking contributors
by volume. Volume incentives in an evidence system produce low-quality submissions at scale.
Recognition SHOULD be qualitative and tied to verified contributions.

**SIG-TASK-013 (MUST).** Task generation MUST be rate-limited per subject so that one badly-modelled
entity cannot flood the queue.

### 33.7 The local-group registry

**SIG-TASK-014 (MUST).** SIG MUST maintain its **own** registry of local surveillance-accountability
groups — name, jurisdiction, URL, contact, activity status, claimed queues — and MUST NOT depend on
an external directory's availability. *(The external directory the outline names did not respond
when tested, F1.9.)*

---

## 34. Contributors

### 34.1 Tiers

**SIG-CONTRIB-001 (MUST).**

| Tier | May write | Review requirement |
|---|---|---|
| Anonymous | Submissions to a queue | All reviewed before landing |
| Registered | Claims at `R5`, task dispositions | Sampled review |
| Trusted reviewer | Verify others' submissions; promote candidates | Sampled audit |
| Curator | Human assertions, resolution overrides, sensitivity classification, `Person` creation | Peer review for §43.4 decisions |
| Maintainer | Ruleset, vocabulary, schema | ADR + review |

**SIG-CONTRIB-002 (MUST).** No tier may write a claim without provenance. Contributor submissions
enter at **L0** as evidence (a photo, a document, a report), never directly at L1.

### 34.2 Onboarding

**SIG-CONTRIB-003 (MUST).** Before the contributor system is declared complete, a **moderated
usability study** MUST be run with at least five participants who have no prior knowledge of the
ontology, measuring time from landing page to accepted first contribution. The **median MUST be at
or under ten minutes**, and the study protocol and results MUST be published. Re-run on any change
to the contribution flow.

The intended path is: pick a nearby open task, or submit an observation with a photo and a
location.

**SIG-CONTRIB-004 (MUST).** For **device observations specifically**, SIG MUST route contributors
to OSM/DeFlock rather than capturing the observation itself (non-goal N7, OL-1.2-03). SIG's own
capture is for the things OSM does not hold: operator evidence, signage, contracts, agenda items.

### 34.3 Safety

**SIG-CONTRIB-005 (MUST).** SIG MUST NOT collect or retain: precise contributor geolocation beyond
the submitted observation; contributor real names as a requirement; device identifiers; or IP logs
beyond a short operational window. **What is not stored cannot be subpoenaed**, and this is a
design requirement, not a preference.

**SIG-CONTRIB-006 (MUST).** Pseudonymous contribution MUST be fully supported, including for
trusted-reviewer tier.

**SIG-CONTRIB-007 (MUST).** SIG MUST publish know-your-rights guidance for lawful photography in
public, and MUST explicitly instruct contributors not to trespass, tamper, or interfere
(non-goal N5, OL-13.5-02). Guidance MUST be jurisdiction-aware.

**SIG-CONTRIB-008 (MUST).** SIG MUST have a published policy for what it does if a contributor is
detained, arrested, or harassed in connection with contributing — including who to contact and what
SIG will and will not disclose.

### 34.4 Vandalism and poisoning resistance

**SIG-CONTRIB-009 (MUST).** Every contribution MUST be revertible as a unit, with the revert
recorded as a new assertion (never a deletion).

**SIG-CONTRIB-010 (MUST).** Anomaly detection MUST run on contribution patterns — bursts, coordinated
similar submissions, submissions that conveniently resolve contested claims — and MUST route to
review rather than auto-reject.

**SIG-CONTRIB-011 (MUST).** A coordinated campaign asserting *false absence* (that a deployment
does not exist) is as damaging as one asserting false presence, and MUST be equally guarded. This
threat is easy to overlook because it looks like helpfulness.

**SIG-CONTRIB-011a (MUST).** The **vendor operating-territory check** is a first-class plausibility
rule: a claim that vendor V operates a device in country or region C, where SIG holds no independent
evidence that V operates in C at all, MUST be held at the lowest confidence and MUST generate a
verification task rather than entering the graph as an observation.

**This threat is observed, not hypothetical, and it is currently active** (R12-F12.28). As of
2026-08-17 the OSM community was dealing with fabricated ALPR nodes across Canada, Germany, Poland,
the UK and Northern Ireland — devices attributed to a vendor in countries where it does not operate,
in locations including inside a shopping mall, an apartment courtyard, and a church. The dominant
live failure mode in this domain is therefore **inflationary**: panic-driven or adversarial
*over*-reporting, not under-reporting. A data-quality model that assumes honest error will not catch
it.

**SIG-CONTRIB-011b (MUST).** SIG MUST NOT be the proximate cause of a mass revert. Community
members have publicly proposed bot-removal of implausible nodes; any SIG-fed suggestion later judged
implausible would risk a revert that damages SIG, the mapper who applied it, and the upstream
project that relayed it. This is the strongest operational argument for the
suggestion-not-write posture of SIG-CONTRIB-015, independent of the licensing and
code-of-conduct arguments.

**SIG-CONTRIB-011c (MUST).** SIG MUST NOT render an unverified community observation with the same
visual weight as a records-derived claim. The ecosystem has independently converged on this remedy —
affected projects responded to the incident by adding provenance disclaimers, restricting default
views to confirmed devices, and prompting for a source before submission. That convergence is
corroboration that §10.7's explainable-confidence model is the right one, arrived at from the
opposite direction.

---

## 35. Contribution back to the ecosystem

### 35.1 Stage 0 outreach

**SIG-CONTRIB-012 (MUST).** Before any connector is written for an ecosystem project, SIG MUST have
attempted contact and recorded the outcome (SIG-CHART-033, SIG-INGEST-029), using a published
template that states: what SIG is; what it wants; **what it will not do** (non-competition,
non-duplication, no re-hosting of their differentiator); what it offers (corrections upstream,
traffic, targeted research tasks, methodology co-authorship, mirroring); and an explicit opt-out.

**SIG-CONTRIB-012a (SHOULD).** Where an upstream project has **publicly asked for help with a
problem SIG is already solving**, that request SHOULD be the opening offer, ahead of any data ask.

A concrete, dated instance exists: during the fabricated-node incident of SIG-CONTRIB-011a, a
maintainer publicly stated they would *"love to have more eyeballs"* on their internal monitoring
tool for implausible submissions. That is precisely the plausibility detector SIG builds anyway
(§34.4). The correct first approach is therefore to **offer to run those checks at graph scale and
feed the results back, free, with no attribution required and no reciprocal data access requested**.

This is also the cheapest possible demonstration of the federation compact: it gives before it asks,
it improves the upstream commons (P5), and it costs SIG nothing it was not already building.

**SIG-CONTRIB-013 (MUST).** The offer MUST include **archival succession**: SIG will hold a mirror
that survives the project's disappearance, on terms the project sets. Several of these projects are
single-maintainer efforts, and the relevant vendor domains are excluded from the general web
archive (§22.2) — so if these projects vanish, the record vanishes with them. This is one of the
most valuable things SIG can offer, and it costs SIG almost nothing.

### 35.2 To OpenStreetMap (Q33)

**SIG-CONTRIB-014 (MUST NOT).** SIG MUST NOT perform direct automated writes to OSM
(REQ-R1-13).

**SIG-CONTRIB-015 (MUST).** Contribution back MUST go through a **human-mediated suggestion
workflow** — a task challenge that a human mapper reviews and applies, in their own account, with
their own judgment. SIG supplies the evidence (a contract naming the operator, a council document,
a signage photo); the mapper decides.

**SIG-CONTRIB-015a (SHOULD).** The verified mechanism is a **MapRoulette cooperative challenge**.
Its API is live and its object model fits SIG's requirements directly (SC-15):

| SIG requirement | MapRoulette field |
|---|---|
| The mandatory changeset hashtag (SIG-CONTRIB-016e) | **`checkinComment`** |
| Originating-tool attribution | `checkinSource` |
| Surfacing the evidence to the mapper | `instruction`, `description`, `blurb` |
| Task priority (§33.1) | `defaultPriority`, `highPriorityRule`, `highPriorityBounds` |
| Geographic queues (§33.5) | `highPriorityBounds`, `isGlobal` |
| The §7 leverage metric | `completionMetrics`, `completionPercentage` |
| Task retirement (§33.3) | `isArchived`, `deleted`, `enabled` |

**`cooperativeType` is the decisive capability.** A cooperative challenge proposes a *specific tag
change* the mapper accepts, rejects, or edits — rather than sending them to edit freehand. That is
exactly the operator-attribution case: *"this node has no `operator`; SIG's evidence suggests
`operator=X`; decide."* It preserves individual human review, which is what keeps SIG outside the
Automated Edits Code's scope (SIG-CONTRIB-016b), while reducing the mapper's cost to roughly one
decision per device — the objective SIG-CONTRIB-017a sets.

**SIG-CONTRIB-015b (MUST).** Phase 16 MUST locate the current MapRoulette API documentation (the
expected `swagger.json` and docs-site URLs both returned 404 when checked) and establish who holds
SIG's MapRoulette account, since challenge creation requires authentication and that account falls
under the Organised Editing disclosure (SIG-CONTRIB-016d).

**SIG-CONTRIB-016 (MUST).** The compliance analysis MUST be recorded as an ADR (ADR-017). The
Automated Edits Code of Conduct has now been **read and analysed** (SC-12); the analysis below is
normative and supersedes the earlier open item.

**The scope test is the whole answer.** The Code of Conduct covers *"all edits where changes are
made to objects in the database **without review individually by the person controlling the
edits**"* — and it explicitly names Overpass-driven bulk retagging and "manually changing tags
without adequate review". Ignoring it *"will be treated as vandalism"*.

**SIG-CONTRIB-016a (MUST).** Operator attribution is **not** covered by any of the Code's
exceptions. Those are limited to blatant typos, reverting vandalism, correcting one's own work, and
reverting unapproved automated edits; the Code states that disagreeing with a tagging schema *"does
not count as typo"*. Adding `operator=*` from contracts and public records is new information from
an external source, which additionally engages the OSM import guidelines. At ~116,800 candidate
nodes it is unambiguously in scope.

**SIG-CONTRIB-016b (MUST).** Therefore the human-mediated suggestion workflow of SIG-CONTRIB-015 is
**not a cautious alternative to compliance — it is what keeps SIG outside the policy's scope
entirely.** A mapper reviewing each proposed change individually, in their own account, exercising
their own judgment, is by definition not making an automated edit. SIG supplies evidence; a person
decides. That is the compliant architecture, and there is no version of a SIG bot account that is
simpler.

**SIG-CONTRIB-016c (MUST).** If SIG ever proposes a genuinely bulk contribution, it MUST first
satisfy every documented requirement: a proposal page under `Automated edits/<username>` naming a
contactable human, the motivation, **the exact selection algorithm**, the consultation record, the
cadence, and **an opt-out mechanism**; registration in the automated-edits log; and a **permanent
record of community discussion and decision on an OSMF-run forum or wiki** — chat-platform
consensus explicitly does not count. Approval is **never blanket**: any later extension of scope
requires fresh community approval.

**SIG-CONTRIB-017 (MUST).** Operator attribution — the ~116,800-device backlog — is the
highest-value contribution SIG can make upstream, and the ODbL posture (§42.3) obliges SIG to share
it anyway. The licence and the mission point the same way here.

**SIG-CONTRIB-016d (MUST).** Escaping the Automated Edits Code of Conduct does **not** escape the
**Organised Editing Guidelines**, which apply to *"any edits that involve more than one person and
can be grouped under one or more sizeable, substantial, coordinated editing initiatives"* (SC-14).
A SIG-run task challenge directing volunteers at the orphaned-device backlog is squarely in scope.
SIG MUST therefore publish an activity page under `Organised Editing/Activities/`, registered in the
activities list, disclosing: the coordinating organisation and a contact; **a unique changeset
hashtag**; the goal and why it is pursued; the timeframe; **every non-standard tool and data source
with its usage conditions**, and links to them; participating accounts that wish to be identified;
any performance metrics used; and any training material issued.

**SIG-CONTRIB-016e (MUST).** SIG MUST declare a **changeset hashtag** and require it on every edit
originating from a SIG task. This is not merely compliance — it is the measurement instrument for
the §7 leverage metric *"SIG-originated operator-attribution suggestions accepted upstream"*, which
is otherwise unmeasurable except by inferring SIG's own influence from tag-count deltas. A declared
hashtag makes SIG's contribution stream **publicly auditable by third parties, including by SIG's
critics**, which is precisely the property that makes the metric credible. The same mechanism is how
SIG identifies *other* projects' organised edits.

**SIG-CONTRIB-016f (MUST).** The disclosure obligation *"any non-standard tools and data sources
used, and their usage conditions"* imposes a **licence gate on the contribution path**, distinct
from the export gate of §42.4. A source whose terms do not permit deriving an OSM edit from it MUST
NOT be surfaced in a contribution task at all, and the task builder MUST check this before
rendering. Publishing a task that invites a mapper into a licence breach would make SIG the
proximate cause of it.

**SIG-CONTRIB-016g (MUST).** Where the guidelines require *"a description of the metrics used"* for
participant performance, SIG's disclosure MUST state that it measures **task outcomes, not
contributor rankings**, consistent with §33.6's prohibition on volume gamification.

**SIG-CONTRIB-017a (MUST).** The binding consequence, which MUST shape the roadmap rather than be
discovered later: **SIG cannot clear this backlog mechanically.** Throughput is bounded by mapper
attention, not by compute. The design objective is therefore to **minimize the human cost per
resolution** — presenting the device, the candidate operator, the supporting contract or record, and
the jurisdiction together in one reviewable unit — and MUST NOT be to maximize automated write
volume. A contribution surface that makes one device resolvable in fifteen seconds is worth more
than any bot SIG is permitted to run.

### 35.3 To other projects (Q34, Q35)

**SIG-CONTRIB-018 (MUST).** SIG MUST maintain per-project correction export formats, and MUST use
each project's own stated submission channel rather than inventing one.

**SIG-CONTRIB-019 (MUST).** Where a research task's closing evidence is a public record, SIG MUST
be able to emit a **ready-to-file records request** (§36) and to record the resulting request as a
`RecordsRequest` linked back to the task.

**SIG-CONTRIB-020 (MUST).** Attribution reciprocity MUST be structural: every claim's upstream is
named in the UI, in API responses, and in exports. Aggregate acknowledgement on an About page is
not sufficient (OL-1.2-08).

---

## 36. Records-request generation

**SIG-TASK-015 (MUST).** Given a research gap, SIG MUST be able to emit a ready-to-file request
with: the correct target agency and its records contact; the correct **statutory citation for that
jurisdiction**; proven request language for the record type; and the specific records sought.

**SIG-TASK-016 (MUST).** SIG MUST maintain a per-jurisdiction records-law reference table covering
all **51 US jurisdictions**: statute name and citation, initial response deadline, fee rules, appeal
path, and whether a **requester-residency requirement** applies.

**SIG-TASK-016a (MUST).** The residency field is **operationally binding, not informational.** Six
states restrict public-records requests to their own residents — **Alabama, Arkansas, Delaware,
Kentucky, Tennessee, and Virginia** — and at least one grants agencies an express right to demand
proof of residency (R12-F12.26). In those jurisdictions a non-resident's request is not merely
likely to fail; it is not a valid request.

Therefore the request generator MUST:

1. **Refuse to emit** a request naming a non-resident filer for a residency-restricted jurisdiction,
   rather than emitting one that will be rejected.
2. **Route the task to the geographic queue** for that jurisdiction (§33.5), where a local
   contributor or partner group can file it. This is the point at which the local-group registry
   (SIG-INGEST-039) stops being a directory and becomes **load-bearing infrastructure**: in six
   states, SIG's records-acquisition capability is *exactly* its local-contributor coverage.
3. **Record the constraint as a coverage fact**, so that thin evidence in a residency-restricted
   state is attributed to the legal barrier rather than read as an absence of surveillance
   (§9.5, §32.2).

**SIG-TASK-016b (MUST).** Where the residency position could not be determined it MUST be recorded
as unknown and MUST default to the restrictive behaviour — route to a local filer — rather than
assuming openness.

**SIG-TASK-017 (MUST).** Request templates MUST be versioned and their **success rates measured**.
Templates that produce denials should be revised, and knowing which language works is itself a
research finding worth publishing.

**SIG-TASK-018 (MUST).** SIG MUST NOT file requests on a contributor's behalf without explicit
consent, and MUST make clear that a filed request is a public act attributable to the filer in most
jurisdictions.

---

# Part VII — Delivery

## 37. The public API

### 37.1 Principles

**SIG-API-001 (MUST).** The API MUST be a **hand-written, versioned contract**, never a schema
reflection. A reflected API leaks internal schema changes to consumers and makes the storage layer
un-refactorable.

**SIG-API-002 (MUST).** Every response carrying a material fact MUST include its resolution
envelope: `value`, `resolution_status`, `support`, `agreement`, `currency`, `rationale`,
`supporting_claim_ids`, `dissenting_claim_ids`, `as_of_world`, `as_of_belief`, `ruleset_version`.
A bare value MUST NOT be returned.

**SIG-API-003 (MUST).** Every response MUST carry a **coverage statement** — what was evaluable,
what was not, and why (§32.2).

**SIG-API-004 (MUST).** Every collection response MUST carry a licence statement computed from the
constituent rights records (§42.4), and every entity response MUST carry upstream attribution
(SIG-CONTRIB-020).

### 37.2 As-of semantics

**SIG-API-005 (MUST).** Every read endpoint MUST accept `as_of_world` and `as_of_belief`, defaulted
explicitly (§9.4), and MUST echo the resolved values back in the response. Omitting them MUST NOT
mean "latest" implicitly — the response states what it used.

**SIG-API-006 (MUST).** Responses MUST be cacheable by the full as-of pair. A belief-pinned request
is immutable and MUST be served with a long cache lifetime; a `now`-pinned request MUST NOT be.

### 37.3 Shape

**SIG-API-007 (MUST).** REST with OpenAPI generation is the baseline. Resource families:
`/entity/{type}/{id}`, `/claim/{id}`, `/resolution/{subject}/{predicate}`,
`/evidence/{artifact}/{capture}`, `/dossier/{jurisdiction|org}`, `/search`, `/task`,
`/coverage/{scope}`, `/contradiction`, `/crosswalk`, `/export`, `/changes`.

**SIG-API-008 (MUST).** Every SIG identifier MUST be dereferenceable at `/id/{type}/{uuid}` with
content negotiation to HTML, JSON-LD, and RDF (SIG-IDENT-031).

**SIG-API-009 (MUST).** A `/changes` feed MUST exist, driven by the snapshot-diff layer (§29.7), so
downstream consumers can follow SIG incrementally rather than re-downloading.

**SIG-API-010 (SHOULD).** GraphQL MAY be offered as a secondary read surface. It MUST NOT be the
only surface, because it defeats caching and archivability.

### 37.4 Access tiers and anti-misuse

**SIG-API-011 (MUST).** Tiers: anonymous (rate-limited, public data), registered (higher limits),
partner (bulk, agreed terms). No tier grants access to `restricted` or `sealed` material through
the public API.

**SIG-API-012 (MUST).** The API MUST NOT expose: any real-time device-liveness signal; any endpoint
enabling per-person lookup; any endpoint returning `sealed` capture bytes; or coordinates at finer
precision than the asset's sensitivity tier permits (§19.4).

**SIG-API-013 (MUST).** Acceptable-use terms MUST prohibit re-identification attempts, and MUST
state the remedy for violation. Terms without a stated remedy are decorative.

---

## 38. Exports and dataset publication

### 38.1 Static-first

**SIG-EXPORT-001 (MUST).** SIG MUST publish **versioned bulk artifacts** to object storage with
checksums and a manifest: Parquet, CSV, JSONL, GeoJSON, PMTiles, JSON-LD/RDF, and a
SQLite/Datasette bundle.

**SIG-EXPORT-002 (MUST).** Tabular exports MUST ship as a **Frictionless Data Package**; evidence
bundles MUST ship as **RO-Crate**. Each quarterly release MUST be deposited to **Zenodo** with a
concept DOI for the dataset and a version DOI for the release; evidence **bytes** are excluded by
size, but the **manifest of digests** MUST be deposited.

**SIG-EXPORT-003 (MUST).** Exports MUST be reproducible from `(as_of pair + ruleset version +
resolver version)` via the same code path the API uses. A hand-built export is a different dataset
wearing the same name.

### 38.2 Licence computation

**SIG-EXPORT-004 (MUST).** An export bundle's licence MUST be **computed** from the SPDX
expressions of its constituent rights records, and the build MUST **fail** if a share-alike input
appears in an export whose declared licence does not satisfy it (§42.4).

**SIG-EXPORT-005 (MUST).** OSM-derived physical assets MUST ship as a **separate file** under
**ODbL-1.0**; SIG-original graph data ships separately under **CC-BY-4.0** (§42.3). A single merged
file would force the whole export share-alike.

**SIG-EXPORT-006 (MUST).** Every export MUST carry per-row rights provenance, so a downstream user
can determine the licence of any individual fact rather than being forced to assume the strictest.

### 38.3 The crosswalk export

**SIG-EXPORT-007 (MUST).** The identifier crosswalk (SIG-IDENT-033) MUST be published under the
most permissive licence its constituents allow, prominently, and separately from the main dataset.
It is the highest-leverage artifact SIG produces for the ecosystem.

### 38.4 Downstream application classes as design targets

**SIG-EXPORT-010 (MUST).** The export portfolio MUST be validated against **six named downstream
application classes** (OL-15.7-01). Each is a design target, not an aspiration: for each, SIG MUST
be able to name the specific artifact that serves it, and a class with no serving artifact is an
export-design defect.

| Class | Serving artifact | Requirement it imposes |
|---|---|---|
| Academic analysis | Parquet + the crosswalk export + Zenodo DOIs | Reproducibility; stable citation; coverage denominators |
| Newsroom tools | JSON API + per-claim evidence links + belief-pinned permalinks | Defensibility under editorial review |
| Local dashboards | Per-jurisdiction JSON/CSV slices | Small, cacheable, jurisdiction-scoped extracts |
| Route / privacy applications | PMTiles + GeoJSON of the **ODbL** asset layer | Correct licence separation; geometry without the graph |
| Policy trackers | The procurement/renewal feed + iCal/RSS | Forward-looking dates, not only history |
| Visualizations | The edge list + entity crosswalk | Typed edges with ER-quality metadata attached |

**SIG-EXPORT-011 (MUST).** Where a class's needs conflict with another's — for example, route
applications want the device layer alone while researchers want it joined — SIG MUST serve them as
**separate artifacts** rather than one compromise artifact. This is also what the licence separation
of §42.3 requires, so the two constraints agree.

### 38.5 Sustainability of distribution

**SIG-EXPORT-008 (MUST).** Bulk distribution MUST use zero-or-low-egress object storage. **Egress
pricing, not storage or compute, is the existential cost** for a project whose value is bulk data
downloads: a 2 GB export downloaded 5,000 times a month is 10 TB of egress, which is free on some
providers and a four-figure monthly bill on others. Success is the failure mode, and the storage
choice must be made with that in mind.

**SIG-EXPORT-009 (SHOULD).** Torrent and IPFS distribution SHOULD be offered for the largest
artifacts, both for cost and for takedown resilience (§46.5).

---

## 39. The product surfaces

### 39.0 Users

**SIG-UI-001 (MUST).** The surfaces MUST be designed against named personas with real tasks:

| Persona | Arrives with | "Done" looks like | Would distrust the site if |
|---|---|---|---|
| Investigative journalist, on deadline | "What can I say about this agency, and can I defend it?" | A quotable claim with a citable document and a permalink | A number appears with no source, or the page changes under a citation |
| Academic researcher | "Give me the national picture and the denominators" | A reproducible bulk export with documented methods | Coverage is implied to be complete |
| **Local advocate, council meeting in 6 days** | "What is deployed here, what does it cost, when does it renew?" | **A printed dossier they can hand to a council member** | It reads as advocacy rather than record |
| Civil-liberties attorney | "What is documented, and what is the provenance chain?" | Evidence with page anchors and acquisition history | Inference is presented as observation |
| Council staffer | "Is what the vendor told us consistent with the record?" | A neutral comparison with sources | The tone is hostile to their institution |
| Resident | "Is there surveillance near me, and who runs it?" | A plain answer with an honest gap statement | Absence looks like proof of absence |
| Downstream developer | "Can I build on this?" | Stable ids, documented API, clear licence | Identifiers move |
| SIG contributor | "What needs doing near me?" | A concrete task with a closing condition | Work disappears into a queue with no effect |

**SIG-UI-002 (MUST).** The local advocate is the **design center**. That choice drives the print
path, the six-day time horizon of the renewal watch, and the plain-language register.

### 39.1 The epistemic visual language

This is the project's defining UI problem: communicating uncertainty without either false
confidence or paralysing hedging.

**SIG-UI-003 (MUST).** Support MUST render as a **four-step glyph** (e.g. ⊕⊕⊕◯) with an accessible
text equivalent, always accompanied by a machine-readable evidence count and, where downgraded, a
**downgrade reason code**. A confidence mark that does not say *why* is decoration.

**SIG-UI-004 (MUST).** The four epistemic fields (§10.7) MUST be independently visible. A single
fused badge is prohibited, because "strongly supported but contested" and "confirmed but
historical" must both be expressible at a glance.

**SIG-UI-005 (MUST).** Encoding MUST NOT rely on colour alone (WCAG 1.4.1). Every epistemic state
MUST carry a redundant non-colour channel: glyph, texture, or text.

**SIG-UI-006 (MUST).** Saturated colour MUST be reserved for epistemic state and data, never for
decoration. **Green MUST NOT be used for epistemic state** — it reads as endorsement, and SIG does
not endorse; it reports.

**SIG-UI-007 (MUST).** **Absence MUST have exactly one visual texture** (a hatch), used for nothing
else and meaning exactly one thing: *we do not have this*. The four absence kinds (§9.5) MUST be
distinguishable within it, and each MUST be **clickable, generating a research task**. This turns
the gap from an admission into an invitation — and it is what stops a mostly-hatched map from
reading as "this site has nothing."

**SIG-UI-008 (MUST).** A contested value MUST carry a persistent marker at every appearance —
table cell, summary tile, map popup, API response, export — not only in a detail view. A user who
never opens the detail must still know the number is disputed.

**SIG-UI-009 (MUST).** Contradictions MUST render as a **value range with the competing claims
plotted**, each labelled with source, tier, date, and document link, plus an explicit note where
the values measure *different quantities* (§29.1). The user must be able to see at a glance that
"42 vs 38" is not necessarily a disagreement.

### 39.2 The local dossier

**SIG-UI-010 (MUST).** The dossier is the primary public artifact. Sections, in order: at-a-glance;
what is deployed; cost and expiry; who else can see the data; configuration and retention; usage;
where the hardware is; policy; accountability events; timeline; **what we don't know**; how we know
this.

**SIG-UI-011 (MUST).** **"What we don't know" is not an appendix.** It appears in the summary, in
the print export, and in the API. In a project whose standard is "no synthetic certainty," the gap
list is a headline feature.

**SIG-UI-012 (MUST).** Every dossier MUST carry an explicit incompleteness banner naming the number
of unresearched fields and stating that absence of a row is not evidence of absence
(OL-9.4-01, OL-9.4-02).

**SIG-UI-013 (MUST).** The dossier MUST have a **print/PDF path** producing a document suitable for
handing to a council member: paginated, with sources, with the as-of date and permalink on every
page. The outline's design center needs paper, not a URL.

**SIG-UI-014 (MUST).** Every material figure MUST be expandable to its reconciliation: the rule
that fired, the competing claims, each source's tier and date, and a link to the document at the
page or cell that supports it.

**SIG-UI-014a (MUST).** The dossier MUST carry three blocks the outline's §15.1 field list omits.
Each is what converts the dossier from a description into something a person can act on:

| Block | Fields | Why it is the difference between informing and enabling |
|---|---|---|
| **`authorization`** | Which body approved it; the vote; **whether it passed on a consent agenda**; whether public comment was taken; the date | *"Approved 7–0 after public comment"* and *"passed unopposed on the consent agenda with no discussion"* are politically opposite facts. The second is the single most actionable thing a local advocate can learn, and no existing dataset records it |
| **`termination_mechanics`** | Auto-renewal flag; notice window; the **`next_decision_date`** derived from them | An expiry date is the wrong figure to surface. A contract expiring 2027-04-02 with auto-renewal and a 90-day notice window has a real deadline of **2027-01-02** — and after that date the decision is made by default. The dossier MUST surface the *decision* date, not the *expiry* date |
| **`legal_regime`** | The applicable state statute; the local ordinance; the disclosure duties each imposes | This answers *"what lever exists here?"* — whether there is a statutory retention cap, a disclosure duty, or an ordinance requiring council approval. Without it a reader knows what is happening but not what can be done about it |

**SIG-UI-014b (MUST).** `next_decision_date` MUST be computed and displayed wherever an expiry is
displayed, and the renewal watch (§39.5) MUST key its alerts on it.

**SIG-UI-015 (MUST).** The dossier MUST render **the outline's** Appendix B content contract in full, including the
`unknown` values — a policy whose configuration evidence is unknown MUST display as "unknown," not
be omitted.

### 39.3 The infrastructure map

**SIG-UI-016 (MUST).** Layers: physical devices; deployments; RTCCs and integration hubs; sharing
edges; private-public networks; service areas; lifecycle status. Derived layers (FOV, coverage)
MUST be separately toggled and visually distinct (SIG-GEO-006).

**SIG-UI-017 (MUST).** The **coverage underlay MUST be bound to the point layer with a single
control**, so a user cannot look at points without seeing where SIG has not looked. Two independent
toggles would let the map lie by default.

**SIG-UI-018 (MUST).** Low-coverage areas MUST NOT be able to read as low-density. Desaturation or
value-suppressing encoding MUST be applied so that "we don't know" is visually distinct from
"there is little here."

**SIG-UI-019 (MUST).** At national zoom the map MUST switch to density binning; individual points
appear only where the zoom supports honest rendering of their precision.

**SIG-UI-020 (MUST).** Assets with no coordinates MUST be represented — as jurisdiction-level
indicators — never silently dropped. A map that shows only locatable assets systematically
understates capability, which is the outline's core critique of camera maps.

**SIG-UI-021 (MUST).** Sharing edges MUST NOT be drawn as a national hairball. Default to an
ego-network from a selected entity, with matrix and arc views as alternatives.

### 39.4 The network explorer

**SIG-UI-022 (MUST).** Default view is an **ego network with expansion**, not a global graph.

**SIG-UI-023 (MUST).** Every centrality or hub statistic MUST carry an **ER-quality disclosure**
inline (P6, SIG-IDENT-030). If entity resolution is imperfect, so is every network statistic, and
the UI must say so where the statistic appears, not in a footnote.

**SIG-UI-024 (MUST).** The three access edge types MUST be visually distinct and independently
filterable, and MUST NOT be shown merged by default (§12.2).

**SIG-UI-025 (MUST).** Access-path closure results MUST show the full hop list with per-hop
evidence and MUST label paths beyond the published hop threshold as speculative
(SIG-RECON-050).

### 39.5 Procurement and renewal watch

**SIG-UI-026 (MUST).** For every contract: expiry, renewal window, notice deadline, approving body,
next scheduled meeting, and replacement procurement if known.

**SIG-UI-027 (MUST).** Subscriptions MUST be offered by jurisdiction with iCal and RSS output, so a
local group can put a renewal deadline in their own calendar. This is what turns passive history
into "actionable civic timing" (OL-15.4-01).

#### 39.5a The evidence recommender

**SIG-UI-027a (MUST).** For a given upcoming decision point — a renewal, a council agenda item, a
hearing — SIG MUST be able to produce a ranked list of the evidence artifacts most useful to a
person preparing for it. This is the component that makes journey **J-3** executable
(SIG-CHART-008); without it J-3 cannot pass.

Ranking inputs, all already present in the model:

| Input | Contribution |
|---|---|
| Claim directness `D` for the predicates at issue | `D1`/`D2` artifacts rank above `D3`+ |
| Currency `C` relative to predicate volatility (§28.3) | Fresh artifacts on volatile predicates rank up |
| Open contradictions touching the subject | Artifacts on both sides of a live dispute rank up |
| Open research tasks for the subject | Named gaps rank up, as things to raise |
| Artifact type vs the decision type | A contract and its amendments rank first for a renewal |
| `capture_status` | Retrievable artifacts rank above paywalled or link-rotted ones |

**SIG-UI-027b (MUST).** The recommender MUST NOT rank by "persuasiveness", sentiment, or predicted
effect on a vote. It ranks by evidentiary directness, recency, and dispute status only. A tool that
optimized for persuasion would make SIG an advocacy instrument and forfeit the neutrality on which
its usefulness to every other persona depends.

**SIG-UI-027c (MUST).** Output MUST be exportable as a citation list with permalinks and as-of
dates, suitable for attaching to public comment.

### 39.6 The evidence viewer

**SIG-UI-028 (MUST).** MUST render the document with the supporting span highlighted at its
locator, and MUST show: the claim; the extraction method and version; review status; conflicting
claims; capture date and digest; acquisition method; and the full history of the claim.

**SIG-UI-029 (MUST).** MUST support **diffing two captures of the same artifact**, field by field,
so "what changed on the portal between June and August" is directly visible (§29.7).

**SIG-UI-030 (MUST).** For `sealed` captures, MUST show the metadata-only representation with an
explanation of why the bytes are withheld (§17.5).

### 39.7 The research queue

**SIG-UI-031 (MUST).** Task cards MUST state the closing condition, the evidence sought, the
assignee class, and the effort estimate. MUST support geographic filtering, claiming with expiry,
and the full disposition vocabulary including "searched, found nothing" (§33.2).

### 39.8 Corrections, methodology, and metrics

**SIG-UI-032 (MUST).** A **public corrections log** MUST exist as a first-class page, listing every
correction with what changed, when, why, and who reported it. *(The outline has seven surfaces and
none is a corrections surface — this is a required addition.)*

**SIG-UI-033 (MUST).** A public **dispute/correction submission** path MUST exist on every page,
one click from any claim (§45).

**SIG-UI-034 (MUST).** A methodology page, a data-freshness page (§32.4), and a coverage-metrics
page MUST be public and linked from every dossier.

### 39.9 Citation and permanence

**SIG-UI-035 (MUST).** Every page MUST expose a belief-pinned permalink and a "cite this page"
affordance including the as-of pair and the ruleset version. A citation of SIG made today MUST
remain reproducible after SIG corrects itself (SIG-TIME-008).

---

## 40. Implementation stack and design system

**SIG-UI-036 (SHOULD).** The frontend SHOULD be a **zero-JS-by-default static-first framework with
opt-in interactive islands**. Rationale: SIG pages will be archived, cited in filings, and read
from web archives years later. A framework whose *default* is no client JavaScript makes
archivability structural — breaking it requires an explicit, greppable directive — rather than a
discipline that erodes.

**SIG-UI-037 (MUST).** Core content MUST be usable **without JavaScript**. Every map MUST have a
tabular equivalent; every graph MUST have a list equivalent. This is simultaneously an
accessibility requirement and an archival one.

**SIG-UI-038 (MUST).** Maps MUST use an open-source renderer with self-hosted vector tiles
(§19.5). Third-party tile CDNs MUST NOT be a hard dependency, and basemap attribution MUST be
correct in every context (SIG-GEO-013).

**SIG-UI-039 (MUST).** Every dependency MUST be OSI-licensed. Non-commercial (CC-BY-NC),
source-available, and dual BUSL licences MUST be excluded — this rules out several popular graph
and search components, and the exclusion MUST be checked in CI, not by memory.

**SIG-UI-040 (SHOULD).** Search SHOULD start with Postgres full-text search and add a dedicated
engine only on demonstrated need, checking licensing at that time.

**SIG-UI-041 (MUST).** Performance budgets MUST be enforced in CI, with the build failing on
regression. A dense evidence page that takes eight seconds to load will not be used at a podium.

---

## 41. Editorial standards

**SIG-UI-042 (MUST).** Each dossier template version MUST receive a recorded **hostile-reader
review** before release: two reviewers independently read a real rendered dossier adopting the
stance of the documented organization's counsel, log every sentence they would challenge, and sign
off. The review, its findings, and their disposition MUST be committed alongside the template
version. Release is blocked until every finding is dispositioned.

*Rationale (not itself testable).* The standard being approximated is that a police chief or vendor
counsel reading their own dossier should find it accurate, neutral, and hard to attack. That is not
politeness — it is the property that makes the work usable as evidence. The recorded review above is
the testable proxy.

**SIG-UI-043 (MUST).** Register rules:

1. Report; do not characterize. "The portal reported 38 cameras on 2026-07-01," not "the department
   admitted to only 38 cameras."
2. Never state an allegation as a fact. `epistemic_status` governs the verb.
3. Attribute every evaluative statement to its source.
4. Prefer the specific and dated to the general and timeless.
5. Name uncertainty in the same sentence as the number.
6. Do not editorialize about motive. SIG documents what institutions do, not why.

**SIG-UI-044 (MUST).** Every page MUST carry a "How we know this" module: artifact counts, tier
distribution, source-independence count, date range, rules applied, and human-review status.

**SIG-UI-045 (MUST).** Example conformant copy for the three hardest cases:

> **A pending lawsuit.** "A complaint filed 2026-03-04 in [court] alleges that a plate misread led
> to a wrongful stop. The allegation has not been adjudicated. The department has not filed a
> public response as of 2026-08-20. [complaint, p. 4]"

> **A policy/configuration divergence.** "The department's written policy, adopted 2025-11-02,
> prohibits use of the system for immigration enforcement. A configuration export dated 2026-05-02,
> obtained by records request, shows an immigration-related hotlist enabled. SIG has not determined
> which reflects current practice; both documents are linked, and this is an open question."

> **A cancellation with hardware remaining.** "The city council voted on 2026-07-14 not to renew
> the contract, which expires 2026-09-30. As of the most recent field observation on 2026-08-11,
> 23 devices remain physically installed. SIG has no evidence about whether they are operational.
> This is not a record of surveillance being removed."

**SIG-UI-046 (MUST).** A public **style guide** MUST codify these rules, and editorial review MUST
apply them to generated rationale templates as well as to hand-written copy — generated text is
published text.

---

# Part VIII — Governance, safety, and law

This part is not an appendix of good intentions. It contains binding constraints that the rest of
this specification is written to satisfy. Several architectural decisions elsewhere exist *because*
of these requirements, and an implementation that ships Parts II–VII without Part VIII is a
different and worse project (§0.7).

**Nothing in this Part is legal advice.** It identifies the questions, the governing authorities,
and defensible default postures, and it marks explicitly where counsel is required.

## 42. Licensing and rights

### 42.1 Rights as first-class data

**SIG-LIC-001 (MUST).** Every source and every evidence artifact MUST carry a **rights record**:
SPDX licence expression (using `LicenseRef-SIG-<slug>` for bespoke terms); attribution string;
**`redistributable` as a separately reviewed boolean**; derivative permission; the terms URL; and
the retrieval date. *(Discharges OL-14.2-01.)*

**SIG-LIC-002 (MUST).** The referenced terms text MUST itself be **archived as evidence**. Terms
change, and a rights determination that cannot show what the terms said when it was made is
unverifiable.

**SIG-LIC-003 (MUST).** `redistributable` MUST NOT be derived from the licence string
(SIG-INGEST-024). A site-wide permissive licence may not cover incorporated third-party data, and
inferring in either direction is an error with legal consequences (SC-09).

**SIG-LIC-004 (MUST).** A source with unresolved rights MUST be `UNDETERMINED`, which MUST **fail
the export gate closed**. The connector may still run for internal research; the data may not be
published. *(Discharges OL-14.2-02 — "do not discover after launch that a key dataset cannot
legally be redistributed.")*

### 42.2 SIG's own licences

**SIG-LIC-004a (MUST).** The export architecture MUST be an **N-compartment model keyed on the
rights record**, not a fixed two-way split. Each mutually-incompatible licence regime present in the
corpus gets its own separable table and its own export file, and the set of compartments is **data,
not code** — adding a source under a new share-alike licence MUST NOT require a schema change.

**This is a correction.** An earlier framing treated the problem as "ODbL assets vs everything
else". SIG has at least **three** incompatible regimes, and the third was discovered only by
checking (SC-18.3):

| Compartment | Licence | Share-alike? | Source |
|---|---|---|---|
| OSM-derived physical assets | **ODbL-1.0** | Yes | OpenStreetMap |
| Portal layer | **CC BY-SA 4.0** | Yes | Eyes on Flock |
| SIG-original graph | **CC-BY-4.0** | No | SIG |

ODbL and CC BY-SA 4.0 are not mergeable with each other, and **neither may be folded into a
CC-BY-4.0 export.** A Phase-14 export that merged portal-derived camera counts into the main
CC-BY graph would be a licence violation that is **invisible in the data and obvious to the
licensor** — the worst combination. The compatibility gate of SIG-EXPORT-004 MUST therefore run
per compartment, and its test suite MUST include a deliberate cross-compartment merge that fails
the build.

**SIG-LIC-004b (MUST).** The rights record MUST carry **`ai_training_permitted`** as a first-class
boolean, separate from the licence expression. A permissive licence does not imply permission to use
the content as model training data: Eyes on Flock's `robots.txt` carries
`Content-Signal: search=yes, ai-train=no, use=reference` while simultaneously granting `Allow: /` to
general agents (SC-18.2). Access permission and training permission are **different grants**, and a
licence string alone cannot express the distinction.

**SIG-LIC-004c (MUST).** Content marked `ai-train=no` MUST NOT be routed through any model-training
pipeline, and the prohibition MUST be enforced at the data layer rather than by convention. Note
this does **not** restrict §25's model-*assisted extraction*, which is inference over a document,
not training on it — but the distinction MUST be documented so that a future contributor does not
collapse it.

**SIG-LIC-005 (MUST).**

| Artifact | Licence | Reasoning |
|---|---|---|
| **Code** | **Apache-2.0** | Patent grant and trademark reservation. AGPL is rejected: the valuable asset is the graph, not the crawler, and AGPL would deter adoption by exactly the newsrooms and institutions Goal 8 targets |
| **OSM-derived physical assets** | **ODbL-1.0**, separate table and file | §42.3 |
| **Portal layer (Eyes on Flock–derived)** | **CC BY-SA 4.0**, separate table and file | ShareAlike; SC-18.3 |
| **SIG-original graph data** | **CC-BY-4.0** | Attribution is what keeps the provenance chain alive downstream — SIG's entire thesis. CC0 is rejected for that reason |
| **Documentation** | **CC-BY-4.0** | |
| **Ontology and vocabularies** | **CC0-1.0** | A vocabulary succeeds only by adoption; every obligation is an adoption tax, and term lists are barely copyrightable in any case |

### 42.3 The ODbL posture (Q13, Q14)

**SIG-LIC-006 (MUST).** SIG MUST adopt **Strategy B** of OL-14.1: publish the OSM-derived
physical-asset layer under ODbL as a physically separate table and export file, and keep the
SIG-original evidence graph under CC-BY-4.0.

**The reasoning, from the actual guidelines** (R1-F1.11 … F1.16):

1. The **Collective Database Guideline** permits adding a *property* to a primary feature **by
   reference** without triggering share-alike — and it names `operator` explicitly as a *property*
   — but only if **no OSM data** is used for that property within a regional cut.
2. The **Horizontal Map Layers Guideline** states that *"if you improve data used in the
   OpenStreetMap layer, such as additions or factual corrections, then you need to share those
   improvements,"* and gives as a "must share" example adding non-OSM data *based on comparison
   with* OSM data. SIG's device attribution is defined by comparison with OSM: it targets exactly
   the nodes OSM lacks an operator for, and it uses OSM geometry for spatial reasoning.
3. The two guidelines therefore point in **opposite directions** for SIG's exact case, and the
   conservative reading governs.
4. **Strategy A is unsafe.** Storing "only identifiers" does not avoid share-alike: the guideline
   holds a join key *is* a reference, states that physical separation is **not** sufficient for
   independence, and requires factual improvements to be shared regardless.
5. **Strategy C is unnecessary** and would impose share-alike on contract, policy, and
   accountability data containing no OSM content, restricting the reuse Goal 8 depends on.
6. **Substantiality is not available as an escape.** The OSMF guideline sets "insubstantial" at
   roughly a village — under 100 features — and states explicitly that *"repeated small extractions
   [count as] one big extraction."* SIG extracts ~144,312 ALPR features systematically and
   repeatedly.

**SIG-LIC-007 (RATIONALE).** This constraint is **mission-aligned, not a cost.** ODbL share-alike on the device
layer requires SIG to give its operator attributions back in a form OSM contributors can use —
which is what P5 and OL-22.6-01 want anyway. The licence enforces the federation compact.

### 42.3a The contribution licence conflict, and its resolution

**SIG-LIC-007a (MUST).** The subset of SIG-authored data that is offered upstream to OSM MUST be
**dual-licensed under CC0-1.0** for that purpose, separately from SIG's CC-BY-4.0 graph licence.

**The conflict is real and would otherwise block the write-back programme.** OSM's import guidance
states: *"We must be able to release the data with our OpenStreetMap License… Your data must be
compatible with the ODbL"* and — decisively — *"**You must not claim an additional copyright for
yourself as the importer.**"* OSM's own compatibility assessment rates **CC-BY-4.0 as requiring an
additional waiver**. So SIG's operator attributions, offered under plain CC-BY-4.0, are **not**
directly contributable.

**Why CC0 for this subset is the right answer rather than a concession:**

1. It satisfies the no-additional-copyright rule directly, with no waiver negotiation.
2. The contributed payload is *facts about public infrastructure* — that an identified agency
   operates an identified device. Facts are thin copyright subject matter at best, and asserting
   rights over them would be both legally weak and contrary to the project's purpose.
3. SIG's goal for this data is **maximum dissemination** (P5, OL-22.6-01). Attribution on the
   contributed subset buys SIG nothing it needs and costs it the ability to give the data away.
4. It is narrowly scoped: **only the contributed subset**, not the graph. SIG's reconciliations,
   contradictions, resolutions, and evidence chains — the actual work — remain CC-BY-4.0.

**SIG-LIC-007b (MUST).** SIG's attribution expectations for the contributed subset MUST be limited
to what OSM offers: mention on the contributors wiki page, a note on the import or activity account,
and source information in changesets. The guidance is explicit that *"if none of these are
acceptable attribution for a data source, you cannot proceed"* — so SIG MUST decide in advance that
they are acceptable, and record that decision, rather than discovering the constraint at
contribution time.

**SIG-LIC-007c (MUST).** The Organised Editing activity page (SIG-CONTRIB-016d) MUST publish the
licence of SIG's operator evidence, because the guidelines require disclosing data sources *"and
their usage conditions"*. Where a piece of evidence's own licence does not permit deriving a
contributed fact from it, that evidence MUST NOT feed a contribution task — which is the
contribution-path licence gate of SIG-CONTRIB-016f, arrived at independently from the licensing side.

**SIG-LIC-008 (MUST).** Produced Works (rendered maps, PDF dossiers, static images) MAY carry SIG's
own licence, **provided the underlying database is also published** as **ODbL clause 4.6** requires. Vector
tiles, GeoJSON, and bulk downloads are **database distribution, not Produced Works**, because they
are intended for extraction.

**SIG-LIC-009 (MUST).** The following MUST be referred to counsel before launch and MUST appear in
the risk register: whether API responses returning device-linked claims constitute distribution of
a Derivative Database under **ODbL clause 4.4(b)**; whether jurisdiction geometry sourced from OSM boundary
relations contaminates the operator property under the Collective Database fourth bullet; the
correct regional-cut unit; and the EU sui generis database right for the international phase.

### 42.4 Export-time computation

**SIG-LIC-009a (MUST).** SIG MUST detect **silently travelling share-alike obligations**. An
obligation does not disappear because an intermediary failed to pass it on: at least one ecosystem
project republishes OSM-derived data **without ODbL attribution**, so a downstream consumer ingesting
from that project would inherit an ODbL obligation with nothing in the artifact to signal it.

Therefore the rights record MUST capture not only a source's own licence but the **provenance of its
data**, and the ingestion gate MUST flag any source whose content is plausibly derived from a
share-alike upstream even where the source itself declares a permissive licence or none. Where this
cannot be resolved, the compartment MUST default to the **stricter** regime, not the declared one.

**SIG-LIC-010 (MUST).** Export licence MUST be **computed** from constituent rights, and the build
MUST fail on incompatibility (SIG-EXPORT-004). This is a CI gate with a test that deliberately
introduces an incompatible source and asserts the build fails.

**SIG-LIC-011 (MUST).** SIG MUST pass downstream the attribution and provenance obligations it
received, per row, so a downstream user can comply without re-deriving the chain.

### 42.5 Reusability

**SIG-LIC-012 (MUST).** Per OL-14.3-01, open code is not enough. SIG MUST ship: open code; open
schemas; downloadable datasets where licensing permits; documented APIs; provenance; versioned
snapshots; and reproducible ingestion. A release missing any of these is incomplete.

---

## 43. Publication policy

### 43.1 The bright line

**SIG-PUB-001 (MUST).** SIG documents **institutions and infrastructure**, not people
(SIG-CHART-024, OL-13.1-01). Every rule below follows from that.

### 43.2 Categorically excluded data

**SIG-PUB-002 (MUST NOT).** SIG MUST NOT store, in any tier, at any sensitivity level:

| Excluded | Enforcement |
|---|---|
| Licence plate numbers, or reversible derivatives | No such column may exist (SIG-STORE-026); schema test |
| Individual travel histories or sightings | No such entity or edge (§12.8) |
| Home addresses of officers or private individuals | **Categorical. No balancing test applies** |
| Private-person names encountered incidentally | Extraction-time redaction |
| Residential association membership of individuals | §14.4 |
| Personal identifiers unrelated to institutional conduct | Extraction-time redaction |

**SIG-PUB-003 (MUST).** Home addresses are excluded **categorically, not by public-interest
balancing**. The outline's §13.2 applies a public-interest standard to officer data generally; that
standard is correct for *names in an accountability claim* and **wrong for addresses**, where the
foreseeable harm is severe, the informational value is near zero, and several jurisdictions impose
strict-liability regimes on publishing them. *(Corrects OL-13.2-01/02 by making one item categorical.)*

### 43.2a SIG must never become the de-pseudonymisation join

**SIG-PUB-003a (MUST).** Operator, user, or account identifiers appearing in third-party audit data
MUST be **hashed with a held-back salt at ingest**, and the raw values MUST NEVER be stored in a
publishable tier or republished — **regardless of the fact that a third party has already published
them.**

**The hazard is live, specific, and named** (R2-F2.15). One ecosystem project publishes, at a single
unauthenticated URL, a 65 MB SQLite database containing **350,043 search-audit rows with raw
operator UUIDs on every row — zero redaction — across 9,717 distinct operators**, joined to
timestamps, agencies, and free-text reasons. A *different* ecosystem project publishes police
rosters and name-resolution tooling.

Neither project individually publishes officer identities. **The join does.** Stable pseudonymous
identifiers plus timestamps plus agency, cross-referenced against rosters and shift schedules
obtainable by records request, re-identify individuals.

**SIG-PUB-003b (MUST).** SIG MUST NOT construct, publish, or enable that join. This is not a
consequence of a general rule; it is a specific prohibition, because SIG is uniquely positioned to
be the thing that makes it work — reconciling identities across projects is precisely what SIG is
for, and this is the one place that capability must be withheld.

Concretely, SIG MUST NOT: ingest per-search rows carrying operator identifiers (§18.1 already
forbids this, and this is the reason it matters most); publish any table joinable on an operator
identifier; or expose an API surface permitting per-operator aggregation.

**SIG-PUB-003c (MUST).** "It is already public" MUST NOT be accepted as a justification anywhere in
this system. The material's prior publication does not reduce the harm of SIG amplifying,
normalising, or making it joinable — and §43.6a establishes that the republisher absorbs the
consequence regardless of the original source's conduct.

**SIG-PUB-003d (SHOULD).** Where SIG becomes aware of an ecosystem project exposing personal data
in this way, it SHOULD raise it privately with that project as part of Stage-0 engagement rather
than publicise it. The objective is that the data stop being exposed, not that SIG be seen to have
noticed.

### 43.3 Coordinate sensitivity

**SIG-PUB-004 (MUST).** Every asset MUST carry a sensitivity class determining published precision
(§19.4). Classification is **role-aware**, not asset-aware (§12.4 separation 6).

| Class | Applies to | Published |
|---|---|---|
| **C1** | Publicly visible hardware on public right-of-way | **Exact** |
| **C2** | Hidden sensor on public infrastructure | **Reduced precision** (documented radius / tract level); exact only if the operator has already published it |
| **C3** | Private-residence candidate; private registrant in a camera-sharing program | **No location.** Program-level facts only |
| **C4** | Confidential facility (domestic-violence shelter, protective, undercover) | **Jurisdiction only; existence not resolvable** |
| **C5** | Mobile asset | **Jurisdiction only**, plus dated historical observations. **Never a current position** |

**SIG-PUB-005 (MUST).** Overrides: an operator-already-published upgrade; **automatic demotion to
C3 on residential-parcel intersection**; a freshness gate beyond which precision is reduced; and a
leak-provenance veto — material whose only provenance is a leak of sensor locations MUST go through
human review before any publication, regardless of its public circulation.

**SIG-PUB-006 (MUST).** C1 is the default for roadside ALPR hardware, consistent with existing
community practice in OSM and DeFlock. SIG does not invent a new norm for the ordinary case; it
adds discipline for the unusual ones.

### 43.4 The officer-naming test

**SIG-PUB-007 (MUST).** A named individual MAY be published **only** if **all five** prongs hold:

1. The claim concerns **official conduct**, not private life.
2. The name appears **on the face of an `R1`/`R2` record** — never inferred, never assembled.
3. The record is **public in the jurisdiction that produced it**.
4. The accountability claim **genuinely fails without the name** — a role designation would not
   serve.
5. Severity, currency, and safety are **proportionate**.

**SIG-PUB-008 (MUST).** **Two independent reviewers MUST concur in writing.** Disagreement defaults
to **no-publish**. The decision, its reasoning, and its reviewers MUST be recorded.

**SIG-PUB-009 (MUST).** Home addresses are outside the test entirely — never, under any prong
(SIG-PUB-003).

**SIG-PUB-010 (MUST).** Routine audit-log rows naming an officer MUST NOT trigger this test,
because they MUST NOT be ingested at all (§18.1).

### 43.5 Candidate assets and RF-derived leads

**SIG-PUB-011 (MUST).** A `CandidateAsset` MUST NOT appear in any public device layer.

**SIG-PUB-012 (MUST).** Promotion to a published `PhysicalAsset` requires **either** human field or
imagery confirmation, **or** a documentary record — never corroboration count alone.

**SIG-PUB-013 (MUST NOT).** A candidate whose location intersects a residential parcel MUST NOT be
published **at any precision, ever**, regardless of corroboration. *(Discharges OL-7.2-06,
OL-2G-FY-03.)*

**SIG-PUB-014 (MUST).** Public UI MUST NOT describe an RF-derived candidate in language implying a
device is known to exist. "A radio observation consistent with this hardware vendor was recorded
nearby" is conformant; "suspected camera location" is not.

### 43.6 Aggregate disclosure

Specified at §18.4. The rule that matters most: **institutional small counts are published;
individual-identifying small counts are suppressed**, and where the two cannot be separated, the
default is suppress-and-review, not publish.

### 43.6a The republisher absorbs the consequence — a worked precedent

**SIG-PUB-014a (MUST).** Any free-text field originating from a records request or a government
data release MUST pass a **pre-publication personal-data screen** before it appears on a public
surface, regardless of the fact that the source is an official record and was lawfully obtained.

**The precedent, verified directly (2026-08-20).** A civil-liberties organization obtained
state-level electronic search-warrant disclosure data that the state was statutorily obliged to
publish but had taken offline. It published the data. The state agency then contacted it to say
that *"staff had failed to properly redact potentially personal information from these fields"* —
specifically the free-text `nature of investigation` and `facts giving rise to the emergency`
columns. The publisher responded in three stages over ten weeks: it first replaced the published
files with **column-reduced versions**; then, once the agency supplied properly redacted data,
replaced them again; and finally **withdrew from hosting the dataset entirely**.

Four things follow, and each is already a requirement elsewhere in this document — this precedent is
why:

| Lesson | Requirement |
|---|---|
| A lawfully public government record can contain unredacted personal data, and **the republisher, not the originating agency, absorbs the consequence** | SIG-PUB-014a, above |
| SIG must be able to **replace a published artifact in place with a reduced version while preserving the claim** | §45.2 outcomes; §17.5 redacted derivative as a new capture |
| SIG must have a takedown path that can escalate all the way to un-hosting | §45.2, SIG-GOV-007 suppression |
| "Link, don't mirror" is the right default for high-risk record sets — **but** the upstream here had itself gone dark, which is why it was mirrored in the first place | §8.4 custody postures; the resolution is **mirror privately, publish metadata publicly** (§17.5 `sealed`) |

**SIG-PUB-014b (MUST).** The tension in the fourth row MUST NOT be resolved by refusing to mirror.
Upstream instability is real (SC-11), and refusing to mirror loses the record. The `sealed` tier
exists exactly so that SIG can hold what it must not publish, and SIG MUST prefer that over either
horn of the false choice between "publish it" and "lose it".

### 43.7 Redaction

**SIG-PUB-015 (MUST).** Redaction produces a **new capture** (SIG-EVID-011), records its method and
version, and is reviewable. Redaction MUST be applied to excerpts surfaced in the UI and API, not
only to stored bytes.

**SIG-PUB-016 (MUST).** Redaction MUST be **irreversible in the published artifact** — no
black-box overlays on extractable text, which is a recurring and embarrassing failure mode in this
field.

### 43.8 Jurisdiction-conditional publication

**SIG-PUB-017 (MUST).** Publication rules MUST be **jurisdiction-conditional**. A single global
rule is not available: data-protection regimes in some jurisdictions constrain publishing even
public-body employee names, while others treat the same records as presumptively public. The policy
engine MUST evaluate the jurisdiction of the data subject and of the record's origin.

---

## 44. Threat model and security

### 44.1 The premise

**SIG-SEC-001 (MUST).** The threat model of §44.2 MUST be a **maintained, versioned artifact**
reviewed at every phase gate, and every adversary row MUST name at least one mitigation that maps to
a defined requirement id. A row with no mapped mitigation fails the gate.

*Rationale (not itself testable).* SIG is adversarial by nature: vendors, agencies, and hostile
individuals have incentives to attack, discredit, subpoena, or poison it, and a design that assumes
goodwill is negligent here. The maintained threat model above is how that assumption is kept
operative rather than rhetorical.

### 44.2 The threat model

| Adversary | Objective | Primary mitigations |
|---|---|---|
| Vendor / agency counsel | Suppress or discredit | Rigorous provenance; a real corrections process (§45); conservative crawler conduct (§26); counsel relationships. **Not hypothetical:** an ecosystem project run by one developer on ~$80/month has already faced **two vendor takedown attempts, one still pending** |
| Legal process against SIG | Compel contributor identity | **Do not collect it** (SIG-CONTRIB-005); short log retention; transparency reporting |
| Doxxer using SIG | Locate or target an individual | Categorical exclusions (§43.2); the officer test (§43.4); no per-person query surface (SIG-API-012) |
| Data-poisoning contributor | Insert false presence *or false absence* | Provenance-required writes; review queues; anomaly detection; full revert (§34.4) |
| Entity-resolution attacker | Corrupt the graph by forcing bad merges | Deterministic-first cascade; auto-write demotion on precision loss (§14.7) |
| Scraper / re-host | Take the data without attribution | Open licences make this mostly legitimate; attribution obligations pass downstream (§42.4) |
| Infrastructure attacker | Take SIG offline | Static-first architecture; mirrors; offline distribution (§46.5) |
| Insider | Exfiltrate sealed material | RLS (§16.8); access logging (SIG-EVID-012); least privilege |
| State actor | Surveil SIG's researchers | Minimal retention; pseudonymity; the whole architecture assumes this |

### 44.3 Warrant-resistant architecture

**SIG-SEC-002 (MUST).** SIG's strongest protection for contributors is **not holding data about
them**. Retention minimization is a security control and MUST be implemented as one, not treated as
a privacy nicety.

**SIG-SEC-003 (MUST).** SIG MUST publish a transparency report covering legal demands received,
complied with, and refused, and SHOULD maintain a warrant canary. The response posture for demands
directed at SIG MUST be documented **before** the first demand arrives.

### 44.4 Access control

**SIG-SEC-004 (MUST).** Sensitivity tiers enforced by restrictive RLS; public API role without
`BYPASSRLS`; export roles running with row security **off** so a would-be-filtered export fails
loudly (SIG-STORE-023). RLS policy tests are CI-blocking (SIG-STORE-024).

**SIG-SEC-005 (MUST).** Access to `restricted`/`sealed` bytes MUST be logged with requester,
purpose, and time — and that log MUST itself have a retention limit, so it does not become a
surveillance record of SIG's own researchers (SIG-EVID-012).

### 44.5 Standard practice

**SIG-SEC-006 (MUST).** Secrets in a manager, never in the repository; dependency and container
scanning in CI; SBOM per release; signed releases; least-privilege service accounts; documented
incident response with a disclosure commitment.

---

## 45. Corrections, disputes, and takedown (Q32)

### 45.1 Intake

**SIG-GOV-001 (MUST).** A public intake channel MUST exist, reachable **in one click from any
claim** (SIG-UI-033), accepting: factual error; privacy harm; legal demand; security concern;
copyright claim.

**SIG-GOV-002 (MUST).** Intake MUST NOT require identifying the submitter, except where a legal
demand requires standing.

### 45.2 Handling

**SIG-GOV-003 (MUST).** Published SLAs by category, with **privacy-harm and safety claims
prioritized above all others**, including above factual corrections.

**SIG-GOV-004 (MUST).** Permitted outcomes: correct; annotate; **suppress from public view while
retaining internally**; delete entirely; or **refuse with published reasoning**. Refusal MUST be a
real, exercisable option — a process that cannot say no is a heckler's veto.

### 45.3 Corrections preserve history

**SIG-GOV-005 (MUST).** A correction is a **new assertion**, never a deletion (SIG-STORE-020,
SIG-TIME-009). A query at a prior `as_of_belief` MUST still return the erroneous value, so a
citation made before the correction remains reproducible and the correction remains visible.

**SIG-GOV-006 (MUST).** Every correction MUST appear in the **public corrections log**
(SIG-UI-032).

### 45.4 Suppression as a distinct primitive

**SIG-GOV-007 (MUST).** **Suppression MUST exist as a primitive distinct from deletion.** An
append-only store with no suppression path forces a destructive delete the first time a valid
privacy demand arrives — which would violate the append-only invariant under pressure, at the worst
possible moment, with no design behind it. *(Corrects an omission in OL-9.2's append-only model.)*

Suppression sets a flag that removes material from public surfaces and exports while retaining it
internally under `sealed` tier, with the decision, its author, and its rationale recorded.

**SIG-GOV-008 (MUST).** True deletion MUST be reserved for material SIG must not hold at all, MUST
require two-person authorization, and MUST leave a tombstone recording that a deletion occurred,
its category, and its date — never its content.

**SIG-GOV-009 (MUST).** This is why evidence-store Object Lock is **governance mode, not compliance
mode** (SIG-EVID-006): compliance mode would make SIG's archive unimpeachable *and* make legitimate
removal technically impossible. SIG chooses the capability to remove, and compensates with
transparency reporting.

### 45.5 Disputes without correction

**SIG-GOV-010 (MUST).** A subject who disputes an accurate claim MUST be able to attach a
**response**, published alongside it. Being able to answer is a real remedy, and it costs SIG
nothing but honesty.

### 45.6 Transparency reporting

**SIG-GOV-011 (MUST).** SIG MUST publish periodic counts of requests by category and outcome,
including refusals.

---

## 46. Governance, sustainability, and continuity

### 46.1 Legal entity

**SIG-GOV-012 (MUST).** Before public launch, SIG MUST establish a legal home — a fiscal sponsor or
its own nonprofit — and document what it implies for liability, donations, and legal defence.
Operating a project with this threat profile as an unincorporated individual effort exposes
contributors personally.

**SIG-GOV-013 (MUST).** SIG MUST identify legal-defence resources appropriate to public-interest
research and journalism **before** they are needed.

### 46.2 Decision-making

**SIG-GOV-014 (MUST).** A published governance document MUST define: who decides schema, ruleset,
and vocabulary changes; how contested claims are adjudicated; a code of conduct with enforcement;
and dispute resolution.

**SIG-GOV-015 (MUST).** An **editorial board** MUST exist for contested claims, officer-naming
decisions (§43.4), and sensitivity classifications, distinct from the technical maintainers. These
are editorial judgments and should not be made by whoever happens to hold commit access.

**SIG-GOV-016 (MUST).** SIG MUST document how it resists capture by any single funder, ideology, or
vendor interest, including a policy on funding sources it will not accept.

### 46.3 Anti-misuse, stated honestly

**SIG-GOV-017 (MUST).** SIG MUST NOT build: a real-time device-liveness feed; a per-person lookup;
an "is a camera watching me right now" surface; or individual-officer tracking as a product
(SIG-API-012, non-goals N1/N3).

**SIG-GOV-018 (MUST).** SIG MUST NOT publish instructions for damaging, disabling, tampering with,
or evading enforcement in the commission of wrongdoing (OL-13.5-02).

**SIG-GOV-019 (MUST).** SIG MUST address the underlying tension **explicitly and in public**,
rather than pretending it does not exist. Mapping surveillance infrastructure does inherently make
avoidance easier. SIG's position is that public knowledge of publicly deployed infrastructure is
legitimate and necessary for democratic oversight; that the same information is already available
to anyone who drives the road and looks; and that the alternative — infrastructure that watches the
public while remaining unknown to it — is the condition the project exists to remedy. The
methodology page MUST say this in SIG's own voice. A project that hides from its hardest question
is not credible on any of its easier ones.

### 46.4 Sustainability

**SIG-GOV-020 (MUST).** SIG MUST define a **degraded-but-alive mode** that runs at approximately
zero marginal cost: static exports, scheduled jobs on free infrastructure, and object storage,
serving the last-published dataset with an honest staleness banner.

**SIG-GOV-021 (MUST).** The degraded mode MUST be **tested**, and its known decay paths documented
— including that free CI schedulers commonly disable dormant scheduled workflows after a period of
repository inactivity, which will silently stop a zero-cost pipeline unless a keepalive is designed
in. A sustainability plan that fails silently is not a plan.

### 46.5 Continuity and succession

**SIG-GOV-022 (MUST).** SIG MUST maintain: geographic mirrors; deposits to Zenodo and Software
Heritage (SIG-EVID-019); an offline distribution path (SIG-EXPORT-009); and a documented plan for
the disappearance of the primary domain.

**SIG-GOV-023 (MUST).** SIG MUST publish a **succession commitment**: if the project ends, the data
and code are released in a form that lets others continue, and the evidence store's OCFL layout
(§17.3) means the archive remains readable **without SIG's software**.

**SIG-GOV-024 (MUST).** SIG MUST offer reciprocal **archival insurance** to single-maintainer
upstream projects (SIG-CONTRIB-013). The need is concrete: the ecosystem's principal audit-analysis
project is **one developer on roughly $80/month who has already faced two vendor takedown attempts,
one still pending**. The failure mode for that project is not indifference or drift — it is a
legal budget mismatch, and it can resolve suddenly. This is not altruism: several of the sources SIG depends on
are one-person efforts, and the relevant vendor domains are excluded from the general web archive
(§22.2). If those projects vanish unmirrored, the historical record vanishes — and SIG's own dataset
loses its provenance chain.

**This requirement is graded MUST rather than SHOULD on the strength of a case observed during this
specification's own research window.** The ecosystem directory the outline designates as SIG's
mechanism for discovering local collaborators (OL-3-02, OL-18-13) ceased to resolve at the DNS level
between 2026-07-28 and 2026-08-20. It had been captured by the general web archive **exactly
once** in its entire history. That single capture is the whole margin by which the directory of
thirteen still-active local research groups — and with it the ecosystem's coordination layer — was
recovered rather than lost. Its community chat room was bound to the same domain and died with it.

Three lessons are encoded elsewhere in this specification as a result: the local-group registry is
seeded from recovered, individually re-verified URLs rather than from names (SIG-INGEST-039);
disappearance is a recorded event rather than a retryable error (SIG-INGEST-009); and the archival
offer is made *before* it is needed, because after is too late. **The projects SIG depends on are
more fragile than the vendors SIG documents.**

---

# Part IX — Engineering practice

## 47. Stack and repository

**SIG-ENG-010 (MUST).** Primary language **Python** for the data platform; **TypeScript** confined
to the web package. SIG MUST NOT author Rust or Go components without an ADR — a small team cannot
maintain four toolchains.

**SIG-ENG-011 (MUST).** **Monorepo**, as a workspace, with a committed lockfile plus a
standards-based lock export and an SBOM per release.

**SIG-ENG-012 (MUST).** Repository layout:

```
ontology/        LinkML source of truth; vocabularies (SKOS); generated artifacts
db/              sqitch migrations; RLS policies; DDL
connectors/      one package per source; each with fixtures/
parsing/         format handlers; extraction; locators
resolution/      entity resolution; blocking; gold set; metrics
reconcile/       resolver; rulesets (data); strategies; contradiction detectors
inference/       L4 derivations
tasks/           detectors; lifecycle; records-request templates
api/             read API; OpenAPI; as-of handling
web/             the public site (TypeScript)
exports/         bulk artifact builders; licence computation
orchestration/   the ONLY package importing the orchestrator
policy/          publication rules; sensitivity classification; licence gates
ops/             deployment; observability; runbooks
docs/            spec, ADRs, methodology, governance
tests/           unit; integration; acceptance/queries; property; fixtures
```

**SIG-ENG-013 (MUST).** Every pipeline stage MUST be invocable as a plain CLI command, with the
orchestrator import confined to `orchestration/` (SIG-INGEST-021).

**SIG-ENG-014 (MUST).** `policy/` MUST be a real, tested code package — the publication rules,
sensitivity classification, and licence gates are executable logic, not prose in `docs/`.

---

## 48. Testing

**SIG-ENG-015 (MUST).** The test taxonomy MUST include all of:

| Class | Asserts |
|---|---|
| Schema | Entity tables hold no attribute columns (SIG-STORE-009); no plate-capable column (SIG-STORE-026); append-only trigger column list matches the live schema |
| **Temporal property tests** | Randomized: `valid_from ≤ valid_to`; supersession chains acyclic and terminating; `as_of` monotonicity; correction preserves prior belief |
| Referential integrity | No orphan claims; every claim has origin and rights |
| Vocabulary conformance | Every claim's predicate registered; every term in scheme; no retired term on a new claim |
| **Geospatial sanity** | Asset falls inside the jurisdiction it is attributed to, or the mismatch raises a task (§33.2 #12) |
| **Count plausibility** | A source reporting 0 after reporting 300 is an alert, never a silent overwrite |
| Resolution determinism | Rebuild L3 from scratch; assert identical output (SIG-STORE-018) |
| **Reproducibility** | Re-run a pinned connector over pinned digests; assert byte-identical claims modulo id and sys_period |
| ER regression | Precision/recall on the frozen holdout; auto-demote on breach (SIG-IDENT-028) |
| **Parser fixtures** | Committed real captures with expected outputs (SIG-PARSE-007) |
| **Upstream canary** | Nightly, against live sources; alerts on structural drift (SIG-PARSE-008) |
| RLS policy | Per role and tier, both visibility and non-visibility (SIG-STORE-024) |
| **Licence gate** | A deliberately incompatible source MUST fail the export build |
| **Policy engine** | Each sensitivity class produces the specified precision; a residential-parcel candidate is never published |
| Acceptance queries | Q-1…Q-13, J-1…J-4 against fixtures (SIG-CHART-009) |
| Accessibility | Automated WCAG checks; no-JS smoke test |
| Performance | Budgets enforced; build fails on regression |

**SIG-ENG-016 (MUST).** Per-PR: unit, schema, property, fixture, licence-gate, policy-engine,
acceptance. Nightly: canaries, ER regression, full L3 rebuild, reproducibility.

**SIG-ENG-017 (MUST).** Data-quality checks MUST run **in the pipeline**, not only in CI
(SIG-ENG-004.3). A check that only runs against fixtures does not protect production data.

**SIG-ENG-018 (MUST).** Data-quality tooling MUST be OSI-licensed; several widely-recommended
options in this category have moved to source-available licences and MUST be re-verified at
adoption time rather than assumed.

---

## 49. Observability

**SIG-ENG-019 (MUST).** Structured logging with run correlation; metrics on ingestion volume,
claim/contradiction/task counts, resolution latency, and per-source freshness; error tracking.

**SIG-ENG-020 (MUST).** A **public** data-freshness and status page (SIG-METRIC-007). Publishing
staleness is a trust affordance, and hiding it is the beginning of implying completeness.

**SIG-ENG-021 (MUST).** Alerting MUST cover: connector failure; parser drift; count-plausibility
breach; ER precision breach; licence-gate failure; policy-engine failure; and a **silent success**
condition — a connector that "succeeds" while returning zero records MUST alert, never pass
(SIG-IDENT-008).

**SIG-ENG-022 (MUST).** Runbooks MUST exist for: source disappearance; upstream schema change; a
bad-merge rollback; a takedown request; a suspected poisoning campaign; and evidence-store
restoration.

---

## 50. Deployment and cost

**SIG-ENG-023 (MUST).** Topology: managed Postgres+PostGIS; object storage with versioning and
governance-mode Object Lock; a small compute instance for crawlers and jobs; CDN for static
artifacts; static site hosting; error tracking.

**SIG-ENG-024 (MUST).** **Egress-friendly object storage is a hard requirement**, not an
optimization (SIG-EXPORT-008).

**SIG-ENG-025 (MUST).** Three cost scales MUST be maintained and reviewed quarterly:

| Scale | Character |
|---|---|
| **Bootstrap** | Free/low tiers, zero-egress storage, free CI on a public repository, a single small instance. **Order of tens of dollars per month.** |
| **Steady state** | Paid database tier, headless-browser capacity, LLM extraction budget, monitoring |
| **Ambitious** | Redundancy, mirrors, higher-frequency capture, staffed review |

**SIG-ENG-026 (MUST).** LLM extraction cost MUST be budgeted per document class and monitored
against the budget, with the pipeline degrading to human-queue rather than exceeding it
(SIG-LLM-007).

**SIG-ENG-027 (MUST).** The bootstrap scale MUST be **real and tested** — the project must be able
to survive on it (SIG-GOV-020), and a plan that only works when funded is not a plan for a
public-interest project.

---

# Part X — The implementation plan

## 51. Phasing

### 51.1 Philosophy

**SIG-ENG-030 (MUST).** Every phase in §51.2 MUST declare which risk-register entries (§53) it
retires or reduces, and each of the four critical risks R-01…R-04 MUST be named by at least one
phase at or before Phase 6. A phase plan in which a critical risk is unretired by Phase 6 fails
review.

*Rationale (not itself testable).* The ordering principle is risk retirement rather than visible
value; the declaration requirement above is how conformance to it is checked.

Four things can kill this project, and all four are resolved or materially de-risked by Phase 6:

1. An ODbL mistake that makes the dataset unpublishable.
2. Entity resolution that silently corrupts every network statistic.
3. A claim/temporal model that cannot express contradiction.
4. Upstream projects declining collaboration — which, given that the Flock portal layer has no
   lawful automated access path (F2.1), determines whether a core layer exists at all.

Five further principles:

- **The ontology is code before it is data.** Schema-as-source-of-truth generates DDL, JSON Schema,
  RDF, types, and docs; vocabulary changes are versioned migrations.
- **Nothing is populated before it can be proven.** No connector lands claims before the evidence
  store, lineage, and licence gate exist.
- **One vertical slice early.** After the first two connectors, a single jurisdiction is driven
  end-to-end through J-1 — to *falsify the design* before it is replicated twenty thousand times.
- **Internal surfaces precede public ones.** The curation UI is required by ER review long before
  the public site.
- **Every phase ends green.** Build, tests, data-quality checks, and the acceptance queries in
  scope all pass.

### 51.2 The phases

| Ph | Name | Outline stage | Retires |
|---|---|---|---|
| **0** | Foundations, governance, ecosystem coordination | Stage 0 | Risk 4 |
| **1** | Ontology as code + vocabularies | — | Ontology churn |
| **2** | Bitemporal claim + evidence spine | — | Risk 3 |
| **3** | Identity registry + deterministic ER | Stage 1A | Risk 2 (part 1) |
| **4** | Connector framework + OSM + Atlas | Stage 1B/1C | Risk 1 |
| **5** | Probabilistic ER + review queue + curation UI | Stage 1A | Risk 2 (part 2) |
| **6** | **Vertical slice: one jurisdiction end-to-end** | — | Design falsification |
| **7** | Records, procurement, document parsing | Stage 1F | — |
| **8** | Reconciliation engine + contradictions | Stage 2 | — |
| **9** | Coverage, completeness, negative space | — | — |
| **10** | Research-task generation | — | — |
| **11** | Flock portal layer **(UNBLOCKED — aggregator API verified)** | Stage 1D | — |

*(Every outline stage is mapped: Stage 0 → Phase 0; 1A → 3 and 5; 1B/1C → 4; 1D → 11; 1E → 12; 1F → 7; 1G → 13; Stage 2 → 8; Stage 3 → 12; Stage 4 → 13; Stage 5 → 17; Stage 6 → 18. Phases with no stage column are infrastructure the outline assumes but does not stage.)*
| **12** | Usage and network layer | **Stage 1E**, Stage 3 | — |
| **13** | Accountability, policy, legal instruments | **Stage 1G**, Stage 4 | — |
| **14** | Public API + exports + dataset publication | — | — |
| **15** | Public web surfaces | — | — |
| **16** | Contributor system + contribution-back | — | — |
| **17** | Broader surveillance technologies | Stage 5 | — |
| **18** | International adapter #1 | Stage 6 | — |

### 51.3 Universal phase gate

**SIG-ENG-031 (MUST).** No phase is complete until: every acceptance criterion passes; CI is green
including data-quality checks; new requirements have automated tests (SIG-ENG-004); ADRs are
written for every deviation; the traceability matrix is updated; and the phase's own risk-register
entries are updated.

---

## 52. Phase specifications

Each phase states its **goal**, **deliverables**, **acceptance criteria** (testable), **spec
sections to load**, and **dependencies**. Sections not cited need not be read (SIG-ENG-001).

---

### Phase 0 — Foundations, governance, ecosystem coordination

**Goal.** Make it possible to build lawfully and collaboratively. Write no ingestion code.

**Deliverables.**
1. Repository skeleton (§47), CI, dependency management, licence headers.
2. **Adopted policy documents**, as code where executable: Crawler Conduct (§26); Publication
   Policy incl. the coordinate matrix and officer test (§43); Takedown & Correction (§45); Threat
   Model (§44); Licensing Decision (§42); Contributor Safety (§34.3); Governance & Code of Conduct
   (§46.2); the anti-misuse statement (SIG-GOV-019).
3. **Source registry seeded** with every source in OL-21 plus §22.3, each with rights record, SPDX
   expression, reviewed `redistributable`, custody posture, `compact_status`, `ingestion_permitted`.
4. **Stage 0 outreach executed** to all nineteen federation-compact projects, with outcomes
   recorded — including `no_response`.
5. ADR-001…ADR-012 written (§15.5).
6. Legal home identified (SIG-GOV-012).

**Acceptance criteria.**
- [ ] `ingestion_permitted` defaults to false and a test proves a connector refuses to run without it.
- [ ] The rights record for every registered source is populated or explicitly `UNDETERMINED`.
- [ ] `UNDETERMINED` fails the export gate — proven by test.
- [ ] Every policy document is published and every executable rule has a test.
- [ ] **Eyes on Flock outreach outcome is recorded** (SIG-INGEST-030) — the Phase 11 blocker.
- [ ] Every ADR names a revisit trigger (SIG-STORE-007).
- [ ] The canonical DeFlock host is resolved (REQ-R1-14).
- [ ] The local-group registry exists and is seeded (SIG-TASK-014).

**Load:** §0, §1–§7, §22, §26, §42–§46, §47.

---

### Phase 1 — Ontology as code

**Goal.** One schema source generating all downstream forms.

**Deliverables.** LinkML ontology for every §11 entity and §12 edge; §13 vocabularies as SKOS;
the predicate registry with volatility, strategy, and directness rows; generators for SQL DDL,
JSON Schema, OWL/SHACL, Pydantic, docs; the generalization conformance suite (SIG-CHART-028).

**Acceptance criteria.**
- [ ] CI fails if committed generated artifacts differ from a fresh generation.
- [ ] The generalization suite passes: acoustic sensor; capability with no asset; reference
      database; commercial data-access relationship; integration hub — all expressible.
- [ ] Every predicate has volatility, strategy, and a directness row (SIG-ONTO-067).
- [ ] Every technology family has an `-unspecified` leaf.
- [ ] No vendor name appears in any schema identifier.
- [ ] Vocabularies publish at stable per-version IRIs.

**Load:** §8, §11, §12, §13, §20. **Depends:** 0.

---

### Phase 2 — The bitemporal claim and evidence spine

**Goal.** The layer that makes every invariant enforceable.

**Deliverables.** L0/L1/L2/L3 schema (§16); append-only enforcement; OCFL evidence store; capture
and extraction pipeline; EDTF encoding with pinned envelope derivation; as-of functions; PROV-O
export; ingest-run lineage.

**Acceptance criteria.**
- [ ] UPDATE/DELETE on `claim` rejected except closing `sys_period` — proven by test.
- [ ] Entity tables contain no attribute columns — schema test.
- [ ] The §16.6 correction scenario passes: `as_of_belief` before the correction returns the old value.
- [ ] Property tests over temporal invariants TI-1…TI-8 pass.
- [ ] `valid_to_kind` distinguishes `ongoing` from `unknown`; the API surfaces it.
- [ ] EDTF round-trips; "early 2025" does not become `2025-01-01`.
- [ ] Resolution overlap prevented by exclusion constraint, not application code.
- [ ] An OCFL object is readable without SIG's code.
- [ ] Sealed captures expose metadata-only public representations.
- [ ] RLS tests pass for every role × tier.

**Load:** §9, §10, §16, §17, §20. **Depends:** 1.

---

### Phase 3 — Identity registry and deterministic ER

**Goal.** Stable identity before anything is counted.

**Deliverables.** Jurisdiction registry with geometry and temporal versioning; organization
registry; identifier crosswalk; `normalize_org_name()` with test vectors; cascade tiers 0–3;
public ID minting with merge/split events and tombstones.

**Acceptance criteria.**
- [ ] `normalize_org_name()` passes all committed vectors; sheriff variants collapse; acronyms
      resolve by exact lookup only.
- [ ] GEOIDs fixed-width with explicit level.
- [ ] ORI validated by pattern, not by positional state assumption; the UCR↔USPS table exists.
- [ ] A zero-record ingest **fails the run**.
- [ ] Municipality and its police department are distinct, joined by `parent_of`.
- [ ] The five succession fixtures pass; a rename produces no succession relation.
- [ ] Public identifiers survive a simulated cluster split with redirects and tombstones.
- [ ] Agency centroids are rejected for point-in-polygon use.

**Load:** §11.1–11.3, §14, §16. **Depends:** 2.

---

### Phase 4 — Connector framework, OSM, Atlas

**Goal.** Two connectors of maximally different shape prove the framework, and the ODbL split is
real in the schema.

**Deliverables.** The eight-stage interface; rate-limiter/robots layer; the licence gate; replay in
network isolation; shadow-mode diffing; source-disappearance events; `osm` and `atlas` connectors;
the **separate ODbL asset table**.

**Acceptance criteria.**
- [ ] A network call after `capture()` **fails the run**.
- [ ] Replay over pinned digests produces byte-identical claims modulo id and sys_period.
- [ ] Shadow mode reports a diff without asserting.
- [ ] A source returning 404 produces an event row and a task, not an exception.
- [ ] Robots-unretrievable ⇒ connector refuses to run.
- [ ] OSM connector handles nodes, ways, relations; splits semicolon multi-values; normalizes across
      all four surveillance keys; preserves element id **and version**.
- [ ] OSM output lands in the ODbL table; a test asserts an export mixing it with CC-BY **fails**.
- [ ] Atlas rows preserve upstream attribution and vocabulary version; a retired category is
      recorded as retirement, not as a world change.
- [ ] Each connector has committed fixtures and a canary.

**Load:** §8.4, §17, §21, §22, §23.2–23.3, §42. **Depends:** 3.

---

### Phase 5 — Probabilistic ER, review queue, curation UI

**Goal.** Close risk 2. Nothing uncertain writes itself.

**Deliverables.** Splink-based matcher; blocking with sizing; gold set with double adjudication and
frozen holdout; tiers 4–5 to review; the internal curation UI; cluster-shape alerts.

**Acceptance criteria.**
- [ ] Tiers 4/5 produce `PROPOSED` claims only — proven by test.
- [ ] Every match records tier, evidence, weight, and per-comparison decomposition.
- [ ] Holdout precision/recall reported; auto-write demotes on breach.
- [ ] Cluster-shape alerts fire on seeded implausible clusters.
- [ ] Blocking rules sized; oversized rules rejected.
- [ ] LLM output reaches only the review queue; model and prompt version logged with each decision.

**Load:** §14.6–14.8, §25, §27. **Depends:** 4.

---

### Phase 6 — Vertical slice: one jurisdiction end-to-end

**Goal.** **Falsify the design on real data before scaling it.**

**Deliverables.** One jurisdiction with genuinely disagreeing sources, carried from evidence to
rendered dossier: assets, organizations, a deployment, a contract, a portal-derived or
records-derived configuration, and at least one real contradiction.

**Acceptance criteria.**
- [ ] **J-1 executes end to end** for the slice jurisdiction.
- [ ] Every material fact resolves to a document at a locator.
- [ ] At least one genuine contradiction is detected and rendered without collapse.
- [ ] The count predicates are distinct; `PREDICATE_CONFLATION` fires on a deliberate conflation.
- [ ] A written retrospective is committed, recording what the design got wrong.
- [ ] **The slice jurisdiction satisfies the hardness precondition**, declared *before* the slice
      begins: at least three independent source families; at least two claims on one predicate that
      disagree; at least one asset with no operator; and at least one lifecycle transition
      evidenced by a dated document. A jurisdiction failing any precondition MUST NOT be used.

*Rationale.* The precondition replaces the unfalsifiable formulation "a slice that surfaces no
design problems was too easy" with a checkable property of the chosen jurisdiction, declared in
advance so it cannot be rationalized afterwards.

**Load:** all prior + §29.1, §39.2. **Depends:** 5.

---

### Phase 7 — Records, procurement, and document parsing

**Deliverables.** Parsing stack with locators; file classification; records connectors; procurement
connectors including cooperative vehicles and federal sub-awards; the agenda-platform tenant
registry; `RecordsRequest`; `FundingInstrument`.

**Acceptance criteria.**
- [ ] Every extraction emits a locator; locator-less extractions are rejected.
- [ ] `raw_value` preserved for unparseable values.
- [ ] Mixed-format archives classified before parsing.
- [ ] Cooperative piggyback contracts set `parent_cooperative_contract`.
- [ ] Federal sub-awards traced to a local deployment for at least one real case.
- [ ] `no_responsive_records` writes a `CoverageRecord`.
- [ ] Rate-limited APIs used as targeted lookups; no crawl attempted.

**Load:** §11.11–11.12, §11.19, §22, §23.5–23.6, §24. **Depends:** 6.

---

### Phase 8 — Reconciliation engine and contradictions

**Deliverables.** The §28 resolver; the ruleset as versioned data; the four axes; the ambiguity
test; rationale templates; `Contradiction`; the workflows of §29.

**Acceptance criteria.**
- [ ] Resolution is deterministic; no random tie-break; total order proven by test.
- [ ] A Tier-A contract does **not** win `active_device_count` against a `D1` portal snapshot.
- [ ] `D6` claims are excluded, not down-weighted.
- [ ] **`U5` fires**: a stale unchallenged value returns `UNRESOLVED` with `last_known` and a date.
- [ ] `unresolved_conflict` is publishable via the API.
- [ ] Three sources copying one upstream count as **one** independence class.
- [ ] Rationales are quotable and never mix a support and an agreement term in one sentence.
- [ ] Full L3 rebuild is byte-identical.
- [ ] Human override records author and rationale, and does not hide the algorithmic result.
- [ ] Sharing asymmetry produces a finding, not a merge.
- [ ] Vendor replacement renders as replacement, never as removal.

**Load:** §10.4–10.9, §16.4, §28, §29, §31. **Depends:** 7.

---

### Phase 9 — Coverage and negative space

**Acceptance criteria.**
- [ ] `CoverageRecord` with `sources_searched[]` required for `searched_not_found`.
- [ ] **Every published aggregate carries a denominator** — enforced by test.
- [ ] The four absence kinds are distinguishable in API and UI.
- [ ] Freshness is computed relative to predicate volatility.
- [ ] Any completeness estimate publishes its violated assumptions, or is omitted.

**Load:** §9.5, §32. **Depends:** 8.

---

### Phase 10 — Research-task generation

**Acceptance criteria.**
- [ ] All 32 task types implemented, each with a testable closing condition.
- [ ] Every contradiction detector maps to a task.
- [ ] `resolved_no_evidence_exists` writes a `CoverageRecord`.
- [ ] Tasks auto-invalidate when their detector stops firing.
- [ ] Geographic claims expire and never grant exclusivity.
- [ ] Records-request generation emits the correct statute for the jurisdiction.

**Load:** §33, §36. **Depends:** 9.

---

### Phase 11 — Flock portal layer **(ungated 2026-08-20)**

**SIG-ENG-032 (MUST). — GATE LIFTED 2026-08-20.** A lawful access path exists: the aggregator's
public CC BY-SA 4.0 API (SC-18). The phase proceeds against that API. The fallbacks of
SIG-INGEST-031 MUST still be implemented, because the API is a single dependency and the vendor's
own domains are unarchivable — if it goes away, so does the only route to this layer.

**Acceptance criteria.**
- [ ] No challenge-defeating code exists in the repository — proven by review and by a test that
      the connector honours a challenge response as a refusal.
- [ ] Portal data is ingested from the aggregator API into a **separate CC BY-SA 4.0 compartment**;
      a test asserts an export merging it with the CC-BY graph **fails the build** (SIG-LIC-004a).
- [ ] Change detection keys on the upstream's snapshot field, not fetch time; a test asserts SIG
      does not poll faster than the upstream refresh (SIG-INGEST-030c).
- [ ] Historical back-fill is sourced from archived captures of the API endpoint (SIG-INGEST-030b).
- [ ] `ai_training_permitted = false` is recorded and enforced for this source (SIG-LIC-004b).
- [ ] Portal disappearance produces an event and a task.
- [ ] Snapshot diffing produces per-field change events.
- [ ] Sharing edges land as **configured access only**, directional, with blank cells as negatives.
- [ ] Audit `Camera Count` lands as an independent count claim.
- [ ] `***` redaction is distinguished from empty.

**Load:** §22.5, §23.4, §23.7, §26, §29.3, §29.7. **Depends:** 10.

---

### Phase 12 — Usage and network layer

**Acceptance criteria.**
- [ ] No per-search or per-plate row exists anywhere — schema test.
- [ ] The three access edge types are never merged.
- [ ] Small-cell suppression applies with the correct rationale; institutional small counts publish.
- [ ] Analytics joins to the graph by UUID and period only, never by name.
- [ ] Aggregate partitions are registered as evidence artifacts.
- [ ] Access-path closure respects hop limits, scope, and non-composition rules.

**Load:** §11.16, §12.2, §12.5, §18, §30.2. **Depends:** 11.

---

### Phase 13 — Accountability, policy, legal instruments

**Acceptance criteria.**
- [ ] `epistemic_status` required and preserved end to end.
- [ ] An allegation never renders with a factual verb.
- [ ] Incidents link to all six source classes with class recorded.
- [ ] Policy/configuration divergence is a rendered finding.
- [ ] A curated index can be held without normalization.

**Load:** §11.13–11.14, §11.17–11.18, §23.8, §29.6. **Depends:** 12.

---

### Phase 14 — API and exports

**Acceptance criteria.**
- [ ] No endpoint returns a bare value without its resolution envelope.
- [ ] Both as-of parameters accepted and echoed.
- [ ] A belief-pinned request is reproducible after a correction.
- [ ] Export licence computed; incompatible mix fails the build.
- [ ] ODbL assets ship as a separate file; per-row rights present.
- [ ] Crosswalk export published.
- [ ] Zenodo deposit with concept and version DOIs.
- [ ] No prohibited endpoint exists (SIG-API-012).

**Load:** §37, §38, §42.4. **Depends:** 13.

---

### Phase 15 — Public web surfaces

**Acceptance criteria.**
- [ ] All seven outline surfaces exist, **plus the corrections log**.
- [ ] Core content usable **without JavaScript**; every map has a tabular equivalent.
- [ ] WCAG 2.2 AA automated checks pass; no colour-only encoding.
- [ ] The four epistemic fields are independently visible; no fused badge.
- [ ] Absence renders as one texture, is clickable, and generates a task.
- [ ] Contested values are marked at every appearance.
- [ ] The dossier prints to a usable PDF with sources, as-of date, and permalink per page.
- [ ] "What we don't know" appears in summary, print, and API.
- [ ] Centrality statistics carry an ER-quality disclosure inline.
- [ ] Every page has a belief-pinned permalink and a citation affordance.
- [ ] The three example editorial cases render as specified.

**Load:** §39, §40, §41. **Depends:** 14.

---

### Phase 16 — Contributors and contribution-back

**Acceptance criteria.**
- [ ] Contributions enter at L0 as evidence, never directly at L1.
- [ ] No contributor PII is retained beyond the documented window.
- [ ] Pseudonymous contribution works at every tier.
- [ ] Every contribution is revertible as a unit; the revert is a new assertion.
- [ ] **No direct automated OSM writes exist**; contribution is human-mediated.
- [ ] The OSM automated-edits compliance ADR is written (SIG-CONTRIB-016).
- [ ] An **Organised Editing activity page** is published and registered, disclosing tools, data
      sources and their usage conditions (SIG-CONTRIB-016d).
- [ ] A **changeset hashtag** is declared, required on SIG-originated edits, and wired to the §7
      leverage metric (SIG-CONTRIB-016e).
- [ ] The **contribution-path licence gate** blocks a task built on a source whose terms forbid
      deriving an OSM edit — proven by a test with a deliberately incompatible source
      (SIG-CONTRIB-016f).
- [ ] Device observations route to OSM/DeFlock, not to SIG capture.
- [ ] Upstream attribution appears in UI, API, and exports.

**Load:** §34, §35. **Depends:** 15.

---

### Phase 17 — Broader surveillance technologies (Stage 5)

Priority order per OL-17.5-01: private-camera federation; facial recognition; cell-site simulators;
mobile-device forensics; gunshot detection; drones; commercial location data; RTCC integration.

**Acceptance criteria.**
- [ ] **Each is populated with no schema change.** Any required change is a Phase-1 defect and MUST
      be recorded as one.
- [ ] Non-camera physical sensors are represented without a camera abstraction.
- [ ] The commercial data-broker chain is representable with distinct aggregator and productizer
      roles.
- [ ] Federal authorization datasets populate `authorization_state` with native validity intervals.

**Load:** §5.2, §11, §13.1, §23. **Depends:** 16.

---

### Phase 18 — International adapter #1 (Stage 6)

**Why France/Belgium is the recommended first adapter.** The Technopolice ecosystem has already
documented and mapped, in a non-US jurisdiction, the same technology span SIG models: CCTV;
**intelligent/algorithmic video (VSA)**; facial-recognition experiments; drones; thermal cameras;
acoustic sensors; and "safe city" integration programs (OL-5.2-01). Two facts make it the highest-value
first adapter rather than merely an available one:

1. **The community explicitly debated using OSM rather than building an isolated
   surveillance-camera database** (OL-5.2-02) — the same architectural choice SIG has made, argued
   independently in another jurisdiction. That debate is a documented precedent for SIG's federation
   posture, and the discussion thread is in the source registry (§22.6 I).
2. **A historical activist database of roughly 12,000 French cameras was imported into OSM for
   verification** (OL-5.2-03). This is the concrete, already-executed path from *local activist
   database* → *common geographic substrate* that SIG's whole federation thesis depends on, and it
   is the strongest available evidence that the thesis works. Phase 18 MUST study this import — its
   conventions, its community consultation, and its outcome — before proposing any SIG-originated
   contribution at scale (SIG-CONTRIB-016).

The French evidence base is also structurally different in a way that stress-tests the model:
authorization is carried by **published prefectural orders** rather than by contracts, and
procurement is carried by a **national open-data procurement dataset** rather than by thousands of
municipal systems. Both map onto `LegalInstrument` and `Contract` respectively, and if they do not,
that is a §5.3 defect to be found here rather than in production.

**SIG-ENG-036 (MUST).** Coarser international datasets — country-level surveillance indices, global
facial-recognition maps, and vendor-level international datasets (OL-5.3-01) — MUST be ingested as
claims with **explicit coarse granularity** and MUST NOT be disaggregated to agency level by
inference (SIG-INGEST-042, OL-5.3-02).

**Acceptance criteria.**
- [ ] Jurisdiction adapter checklist satisfied with no US-shaped assumption.
- [ ] Organization and legal-instrument types added under a national namespace, not by widening a
      US enum.
- [ ] Multilingual labels with BCP 47 tags render correctly.
- [ ] Jurisdiction-conditional publication rules apply (§43.8).
- [ ] The non-US records-request vocabulary is used, including `no_equivalent_available`.

**Load:** §5.3, §13.7–13.8, §43.8. **Depends:** 17.

---

## 53. Risk register

| # | Risk | Severity | Mitigation | Phase |
|---|---|---|---|---|
| R-01 | ODbL misapplication makes the dataset unpublishable | Critical | §42.3; separate tables; licence gate; counsel on §42.3 residuals | 0, 4 |
| R-02 | ~~Flock portal layer has no lawful automated path~~ **CLOSED 2026-08-20** | — | A public CC BY-SA 4.0 aggregator API supplies the layer (SC-18). Residual: it is a **single point of failure**, so the fallbacks of SIG-INGEST-031 and the succession offer stay live | 0, 11 |
| R-03 | ER errors corrupt all network statistics | Critical | §14.7 gates; P6 ordering; UI disclosure | 3, 5 |
| R-04 | Upstream projects decline collaboration | High | Stage 0; recorded `no_response`; fallbacks | 0 |
| R-05 | Re-extraction treated as migration, destroying history | High | §21.2 claim identity | 2, 4 |
| R-06 | Silent parser drift after an upstream redesign | High | Fixtures + nightly canary | 4+ |
| R-07 | Egress cost becomes existential on success | High | §38.4 storage choice | 14 |
| R-08 | Publishing a name or coordinate that causes harm | Critical | §43; two-reviewer test; categorical address rule | 0 |
| R-09 | Legal demand against SIG | High | §44.3, §45, §46.1 | 0 |
| R-10 | Data-poisoning campaign | Medium | §34.4; false-absence guard | 16 |
| R-11 | Zero-cost mode fails silently | Medium | §46.4 keepalive; tested degraded mode | 0 |
| R-12 | **FlockReporter unreachable; ecosystem directory may not exist** | Medium | SIG-TASK-014 own registry | 0 |
| R-13 | An unverifiable requirement ships unchecked | Medium | SIG-ENG-005 register entry + compensating control | all |
| R-14 | ~~OSM automated-edits rules not yet read~~ **CLOSED 2026-08-20** | — | Read and analysed (SC-12); the human-mediated design keeps SIG outside the policy's scope entirely (SIG-CONTRIB-016b). Residual: the ADR must still be written | 16 |
| R-15 | Scholarly/paywalled evidence unretrievable | Low | `capture_status` models it (SC-07) | 2 |
| R-16 | Vendor integration facts go stale fast | Medium | Volatility classes; canaries | 8 |

**SIG-ENG-033 (MUST).** The risk register MUST be reviewed at every phase gate, and each research
file's **Open questions** section MUST be triaged into it rather than left in the cache.

---

## 54. Sequencing and parallelization

**SIG-ENG-034 (MUST).** The critical path is `0 → 1 → 2 → 3 → 4 → 5 → 6 → 8`. Phase 6 is a hard
synchronization point: **no phase after 6 may begin until its retrospective is written.**

Parallelizable once their dependencies land: Phase 7 with 8 (parsing is independent of resolution);
Phase 9 with 10; Phase 13 with 12; Phase 15 surfaces individually; Phase 17 technologies
individually.

**SIG-ENG-035 (MUST).** Phase 11 depends on an **external** source, not on internal work, and it
MUST NOT block phases 12–18, which MUST be able to proceed on other sources. A design in which one
uncooperative or unavailable upstream halts the project is a design failure, and the phase order
avoids it deliberately.

The dependency is now **satisfied** rather than merely mitigated — a public API supplies the layer
(SC-18) — but the ordering constraint stands, because that API is a **single point of failure** and
the vendor's own domains are unarchivable. If it disappears, phases 12–18 must still run.

---

# Appendix A — Requirement traceability matrix

This appendix is the **proof of the superset claim** made in §0.1. It walks all **480 atomic
obligations** extracted from `docs/1_deep_research_overview.md` into
`docs/research/_meta/OUTLINE_TRACE.md`, and records for each the section of this specification that
discharges it.

The matrix was produced by an **independent adversarial review** whose brief was to find gaps rather
than confirm coverage (`docs/research/_meta/GAP_ANALYSIS.md`), then updated twice as work completed.

## A.1 Summary

| Stage | COVERED | PARTIAL | GAP | CONTRADICTED |
|---|---|---|---|---|
| Adversarial review, first pass | 395 | 58 | 27 | 0 rows / 4 self-claims |
| After the gap-closure pass | 479 | 1 | 0 | 0 |
| **After the research-completion pass** | **480** | **0** | **0** | **0** |

Rows closed in each stage are marked *(closed in the gap-closure pass.)* or *(closed in the
completion pass.)* respectively.

**The final PARTIAL was `OL-2B-FP-04`** — temporal snapshotting of vendor transparency portals. It
was held open honestly for as long as no lawful access path existed, on the grounds that marking it
COVERED would be the synthetic certainty §3.1 forbids. The completion pass established that a public,
CC BY-SA 4.0 aggregator API supplies the layer (SC-18), so the obligation is now genuinely
dischargeable and Phase 11 is ungated.

## A.2 Reading the matrix

`Type` is the obligation class from the trace: `PURPOSE`, `REQ`, `ENTITY`, `FIELD`, `VOCAB`,
`PRINCIPLE`, `NONGOAL`, `Q`, `SOURCE`, `EXAMPLE`, `SURFACE`, `STAGE`.

`COVERED` means the obligation is discharged by the named section, and a coding agent executing that
section would produce what the outline requires — not merely that the words appear.

## A.3 The matrix


### 0. Executive summary

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-ES-01` | PURPOSE | COVERED | §1.3, §6 | SIG positioned as the missing reconciliation layer. |
| `OL-ES-02` | REQ | COVERED | §2.1 Q-1…Q-13 | All thirteen mapped to a carrier + acceptance query. |
| `OL-ES-03` | REQ | COVERED | SIG-CHART-007 | Joining burden stated as the central architectural obligation. |
| `OL-ES-04` | SOURCE | COVERED | §6, §22.2, §23.2 | OSM = upstream canonical device geography. |
| `OL-ES-05` | SOURCE | COVERED | §6, §22.2 | DeFlock role: contributors upstream to OSM; do not fork. |
| `OL-ES-06` | SOURCE | COVERED | §6, §22.5 | EoF = portal temporal layer; Phase 0 blocking dependency. |
| `OL-ES-07` | SOURCE | COVERED | §6, §23.7, N9 | HIBF = audit specialist; SIG holds structural aggregates only. |
| `OL-ES-08` | SOURCE | COVERED | §6, §22.2, G C-02 | Role preserved; scope corrected (now routing/offline, GitLab). |
| `OL-ES-09` | SOURCE | COVERED | §6, §23.3 | Atlas = primary deployment seed. |
| `OL-ES-10` | SOURCE | COVERED | §22.6 D, §23.9 | Registry row + dedicated connector + Phase 12. *(closed in the gap-closure pass.)* |
| `OL-ES-11` | SOURCE | COVERED | §6, §23.8, §10.4 R3 | Accountability Atlas epistemic labels adopted. |
| `OL-ES-12` | SOURCE | COVERED | §6, §23.9, §43.5 | Lead generation only; never confirmed device identification. |
| `OL-ES-13` | SOURCE | COVERED | §6, §22.2, §38 | Downstream consumer; publish reusable higher-order data. |
| `OL-ES-14` | SOURCE | COVERED | §6, §33.7, G C-03 | FlockReporter unreachable; SIG maintains its own registry. |
| `OL-ES-15` | SOURCE | COVERED | §6, §11.19, §23.5 | MuckRock modelled as RecordsRequest evidence substrate. |
| `OL-ES-16` | REQ | COVERED | §13.1 | `body-worn-video` domain added; 14 domains. *(closed in the gap-closure pass.)* |
| `OL-ES-17` | SOURCE | COVERED | §22.2, §12.3, G C-06/C-07 | Community Connect verified; Fusus/Flock link severed 2025. |
| `OL-ES-18` | SOURCE | COVERED | §11.4, §43.3, G C-08 | ShotSpotter→SoundThinking rename; 22,471 not 25,000; leak veto. |
| `OL-ES-19` | SOURCE | COVERED | §11.4, §22.7 | Named examples restored incl. Cellebrite UFED. *(closed in the gap-closure pass.)* |
| `OL-ES-20` | REQ | COVERED | §5.3, §13.7, §43.8, Phase 18 | Global physical layer; jurisdiction adapters. |
| `OL-ES-21` | PURPOSE | COVERED | SIG-CHART-001 (MUST NOT) | Explicit prohibition on being another surveillance map. |
| `OL-ES-22` | PURPOSE | COVERED | §1.1, §3.4, §3.5 | Six defining characteristics bound to sections. |
| `OL-ES-23` | PURPOSE | COVERED | §1.2 | Preserved verbatim. |
| `OL-ES-24` | PRINCIPLE | COVERED | §3.5 SIG-CHART-017 | Each characteristic bound to an enforcing section. |
| `OL-ES-25` | PRINCIPLE | COVERED | SIG-CHART-003 | Relationship, not device, as fundamental unit. |
| `OL-ES-26` | EXAMPLE | COVERED | §1.4 table | All seven manifestations enumerated with why each breaks device-centrism. |
| `OL-ES-27` | ENTITY | COVERED | §11.0 entity index | All 21 classes present; several split, four NEW. |
| `OL-ES-28` | PURPOSE | COVERED | SIG-CHART-002 | Joined evidence as the distinctive output. |
| `OL-ES-29` | EXAMPLE | COVERED | §2.2 J-1, Appendix D, Phase 6 | Full traversal is the Phase-6 gate. |
| `OL-ES-30` | EXAMPLE | COVERED | §2.2 J-2, §11.16, §32.2 | Coverage statement mandated on the result set. |
| `OL-ES-31` | EXAMPLE | COVERED | §39.5a | Evidence recommender specified with a Phase 15 criterion. *(closed in the gap-closure pass.)* |
| `OL-ES-32` | EXAMPLE | COVERED | §2.2 J-4, §13.4, §29.4 | replaced_by edge + integration classification. |

### 1. Project thesis

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-1.1-01` | PRINCIPLE | COVERED | SIG-CHART-004 | Point-only representation rejected. |
| `OL-1.1-02` | REQ | COVERED | SIG-CHART-005, §12.9 | All twelve mapped to carriers. |
| `OL-1.1-03` | EXAMPLE | COVERED | §1.4 rationale | Two-jurisdiction contrast stated verbatim. |
| `OL-1.1-04` | PRINCIPLE | COVERED | SIG-CHART-004 | Graph of capabilities and access. |
| `OL-1.2-01` | PRINCIPLE | COVERED | SIG-CHART-014 | Federation as MUST. |
| `OL-1.2-02` | NONGOAL | COVERED | SIG-CHART-015.1 | Do not fork DeFlock. |
| `OL-1.2-03` | NONGOAL | COVERED | SIG-CHART-015.2, SIG-CONTRIB-004 | Route device observations to OSM/DeFlock. |
| `OL-1.2-04` | NONGOAL | COVERED | SIG-CHART-015.3 |  |
| `OL-1.2-05` | NONGOAL | COVERED | SIG-CHART-015.4, N9 |  |
| `OL-1.2-06` | NONGOAL | COVERED | SIG-CHART-015.5, SIG-EPIS-008 |  |
| `OL-1.2-07` | NONGOAL | COVERED | SIG-CHART-015.6, SIG-CHART-019 |  |
| `OL-1.2-08` | REQ | COVERED | SIG-CHART-014.1–7 | All seven positive obligations enumerated. |
| `OL-1.2-09` | PURPOSE | COVERED | SIG-CHART-016, §6 | Compact with enforced ingestion_permitted flag. |

### 2. Ecosystem — Layer A (physical infrastructure)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-2A-OSM-01` | SOURCE | COVERED | §19.1, §23.2 | man_made=surveillance population measured (SC-01). |
| `OL-2A-OSM-02` | VOCAB | COVERED | §23.2 SIG-INGEST-045 | Full measured tag vocabulary table. *(closed in the gap-closure pass.)* |
| `OL-2A-OSM-03` | REQ | COVERED | §22.2, §19.3, Q19 | Overpass, replication diffs, element history. |
| `OL-2A-OSM-04` | PRINCIPLE | COVERED | §6, §42.3 | Neutral substrate; never the canonical editing DB. |
| `OL-2A-OSM-05` | PRINCIPLE | COVERED | SIG-ONTO-006, N7 | Confirmed devices flow to OSM, not a SIG device table. |
| `OL-2A-OSM-06` | REQ | COVERED | §42.3, Q13/Q14 | Derivative vs Collective analysed from the actual guidelines. |
| `OL-2A-OSM-07` | SOURCE | COVERED | §22.6 A | URLs seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-2A-DF-01` | SOURCE | COVERED | §6, §22.2 |  |
| `OL-2A-DF-02` | PRINCIPLE | COVERED | §6, §42.3 |  |
| `OL-2A-DF-03` | REQ | COVERED | §6, SIG-CONTRIB-004 |  |
| `OL-2A-DF-04` | PRINCIPLE | COVERED | §6 (do not fork) |  |
| `OL-2A-DF-05` | SOURCE | COVERED | §22.6 A | `deflock-data` registered, marked existence-unverified. *(closed in the gap-closure pass.)* |
| `OL-2A-DF-06` | FIELD | COVERED | §11.8 | osm_version, upstream_id, first/last_observed all present. |
| `OL-2A-DF-07` | REQ | COVERED | §29.1, §29.2, §11.8 | Attribution + count reconciliation + orphan state. |
| `OL-2A-SUS-01` | SOURCE | COVERED | §22.6 A | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-2A-SUS-02` | REQ | COVERED | SIG-CHART-030 | No US-only device schema. |
| `OL-2A-PC-01` | SOURCE | COVERED | §22.6 A | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-2A-PC-02` | PRINCIPLE | COVERED | §19.3 SIG-GEO-006 | Derived geometry physically separate and labelled. |
| `OL-2A-DAF-01` | SOURCE | COVERED | §22.6 A | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-2A-DAF-02` | REQ | COVERED | §38, §6 | Reusable higher-order exports; no re-scraping. |

### 2. Ecosystem — Layer B (official/vendor deployment + sharing metadata)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-2B-FP-01` | SOURCE | COVERED | §22.2, §8.3 Layer B |  |
| `OL-2B-FP-02` | FIELD | COVERED | §23.4 | All twelve portal fields now have predicates. *(closed in the gap-closure pass.)* |
| `OL-2B-FP-03` | PRINCIPLE | COVERED | §10.2, §17.6, G C-04 | Portals incomplete; disappearance is data. |
| `OL-2B-FP-04` | REQ | COVERED | §22.5, §17, §29.7 | Portal snapshotting now fully dischargeable via the aggregator API (SC-18). *(closed in the completion pass.)* |
| `OL-2B-FP-05` | REQ | COVERED | §11.2, §12.2, §11.15 | Org types cover federal/university/private; direction required. |
| `OL-2B-FP-06` | SOURCE | COVERED | §22.6 B | Portal host + example slugs registered. *(closed in the gap-closure pass.)* |
| `OL-2B-EOF-01` | SOURCE | COVERED | §6, §22.5, R-02 | Foundational, Phase-0 blocking. |
| `OL-2B-EOF-02` | REQ | COVERED | §23.4 | The no-directory / brute-force-enumeration fact now stated. *(closed in the gap-closure pass.)* |
| `OL-2B-EOF-03` | FIELD | COVERED | §23.4 | `hotlist_hit_windowed_count` added. *(closed in the gap-closure pass.)* |
| `OL-2B-EOF-04` | REQ | COVERED | §22.5, §6 | Discovery/archiving/normalization/aggregation/edge extraction. |
| `OL-2B-EOF-05` | REQ | COVERED | SIG-INGEST-030/031 | Ordered fallback; challenge-defeating crawler forbidden. |
| `OL-2B-IND-01` | SOURCE | COVERED | §17.4 SIG-EVID-008, §29.7 | WACZ + screenshot + structured payload + raw HTML. |
| `OL-2B-IND-02` | PRINCIPLE | COVERED | §9.1–9.2, §10.2 | Four-way distinction encoded in the temporal model. |
| `OL-2B-IND-03` | PRINCIPLE | COVERED | §16.3, §17.3, SIG-EVID-006 | Immutability enforced by OCFL + Object Lock + role revocation. |

### 2. Ecosystem — Layer C (usage and audit behavior)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-2C-HIBF-01` | SOURCE | COVERED | §6, §23.7 |  |
| `OL-2C-HIBF-02` | ENTITY | COVERED | §11.16 audit_source_type=organization_audit |  |
| `OL-2C-HIBF-03` | ENTITY | COVERED | §23.7 REQ-R2-07 | `Camera Count` ingested as an independent count claim. *(closed in the gap-closure pass.)* |
| `OL-2C-HIBF-04` | ENTITY | COVERED | §11.16 audit_source_type=portal_public_audit |  |
| `OL-2C-HIBF-05` | ENTITY | COVERED | §23.7, §12.2 configured_access | SharedNetworks.csv → directional configured-access edges. |
| `OL-2C-HIBF-06` | ENTITY | COVERED | §23.7, §29.4 SIG-RECON-039 | Event-log transitions preferred over inferred ones. |
| `OL-2C-HIBF-07` | ENTITY | COVERED | §11.15 observed_via=config_screenshot | All listed settings are ConfigurationState predicates. |
| `OL-2C-HIBF-08` | REQ | COVERED | §23.7 SIG-INGEST-046 | All six capabilities explicitly dispositioned. *(closed in the gap-closure pass.)* |
| `OL-2C-HIBF-09` | PRINCIPLE | COVERED | §11.16, §18.1, N9 |  |
| `OL-2C-AW-01` | SOURCE | COVERED | §6, G C-02 |  |
| `OL-2C-AW-02` | REQ | COVERED | §21.1 eight-stage pipeline | Connector architecture mirrors the ALPR Watch shape. |
| `OL-2C-AW-03` | REQ | COVERED | §23.5, §24, §17.7 | MuckRock corrected to api_v2; reproducibility enforced. |
| `OL-2C-AW-04` | PRINCIPLE | COVERED | §24.2 SIG-PARSE-005/006 | Versioned, inspectable, reversible; dropdown vs free text split. |
| `OL-2C-AW-05` | PRINCIPLE | COVERED | §10.3.5, §16.2 | raw_value NOT NULL; normalization_id/version; review_status. |
| `OL-2C-AJ-01` | SOURCE | COVERED | §22.6 C | Both registered; the academic citation carries `capture_status=paywalled`. *(closed in the gap-closure pass.)* |
| `OL-2C-AJ-02` | PRINCIPLE | COVERED | §39.4, §30.2, §12.9 | Topology as first-class surface. |

### 2. Ecosystem — Layer D (agency-level adoption)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-2D-AT-01` | SOURCE | COVERED | §6, §23.3 |  |
| `OL-2D-AT-02` | REQ | COVERED | §23.3 | Nine methodology components enumerated with R/D consequences. *(closed in the gap-closure pass.)* |
| `OL-2D-AT-03` | PRINCIPLE | COVERED | §9.5, §32, SIG-ONTO-059 | Absence encoded; category retirement ≠ world change. |
| `OL-2D-AT-04` | REQ | COVERED | §20.3 SIG-STORE-039/040 | Crosswalks with SKOS relations and lossy flags. |
| `OL-2D-AT-05` | SOURCE | COVERED | §22.7 | Full Data Library roster as the Phase 17 backlog. *(closed in the gap-closure pass.)* |
| `OL-2D-AT-06` | REQ | COVERED | §23.3 | Attribution preserved; supersession allowed. |
| `OL-2D-DD-01` | SOURCE | COVERED | §23.9 | Connector specified. *(closed in the gap-closure pass.)* |
| `OL-2D-DD-02` | REQ | COVERED | §23.9 SIG-INGEST-043a | Measured values carried: 2.54bn detections, 99.552% non-hit, mean 160.2 partners. *(deepened in the completion pass.)* |
| `OL-2D-DD-03` | PRINCIPLE | COVERED | SIG-CHART-026, §13.1 | Vendor-neutral ALPR family; six vendors in initial scope. |

### 2. Ecosystem — Layer E (accountability, incidents, litigation, policy)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-2E-AA-01` | SOURCE | COVERED | §6, §23.8 |  |
| `OL-2E-AA-02` | REQ | COVERED | §23.8 | Five published artifacts enumerated. *(closed in the gap-closure pass.)* |
| `OL-2E-AA-03` | VOCAB | COVERED | §11.17 event_type | All six categories map to event_type terms. |
| `OL-2E-AA-04` | PRINCIPLE | COVERED | SIG-ONTO-038 | epistemic_status vocabulary adopted directly. |
| `OL-2E-AA-05` | PRINCIPLE | COVERED | SIG-ONTO-038, SIG-UI-043/045 | Allegation never rendered with a factual verb. |
| `OL-2E-AL-01` | SOURCE | COVERED | §6, §23.8 |  |
| `OL-2E-AL-02` | PRINCIPLE | COVERED | SIG-EPIS-030 | Curated index held as an index. |
| `OL-2E-AL-03` | REQ | COVERED | SIG-ONTO-039 | All six source classes linkable with class recorded. |
| `OL-2E-AC-01` | SOURCE | COVERED | §22.6 E, §39.0 | Registered; and it defines the local-advocate persona. *(closed in the gap-closure pass.)* |
| `OL-2E-AC-02` | SURFACE | COVERED | §39.2, Appendix D | All twelve dossier elements present. |

### 2. Ecosystem — Layer F (records and primary evidence)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-2F-MR-01` | SOURCE | COVERED | §6, §11.19 |  |
| `OL-2F-MR-02` | FIELD | COVERED | §11.19 | All eight fields present plus statutory_basis and platform. |
| `OL-2F-MR-03` | PRINCIPLE | COVERED | §6, §10.1 | Link to the exact released document. |
| `OL-2F-DC-01` | SOURCE | COVERED | §6, §10.2 | Evidence store, not a citation URL. |
| `OL-2F-DC-02` | FIELD | COVERED | §10.3.2, §10.3.3 | All ten metadata fields present. |
| `OL-2F-DC-03` | REQ | COVERED | §10.3.2 artifact_type | 24-term vocabulary covers all listed genres. |
| `OL-2F-GOV-01` | SOURCE | COVERED | §23.6 SIG-INGEST-047 | Procurement aggregator registered under LINK posture. *(closed in the gap-closure pass.)* |
| `OL-2F-GOV-02` | SOURCE | COVERED | §23.6 SIG-INGEST-047 | `state_auditor_survey` and `warrant` artifact types added. *(closed in the gap-closure pass.)* |
| `OL-2F-GOV-03` | PRINCIPLE | COVERED | §22.3 A-01/A-02, SIG-ONTO-064 | Procurement precedes mapping; free_trial path. |

### 2. Ecosystem — Layer G (lead generation and field detection)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-2G-FF-01` | SOURCE | COVERED | §11.9, §23.9 |  |
| `OL-2G-FF-02` | PRINCIPLE | COVERED | §11.9, SIG-PUB-011/014 | Never conflated with verified hardware. |
| `OL-2G-FF-03` | REQ | COVERED | SIG-ONTO-006 | Required flow reproduced verbatim, terminating at OSM. |
| `OL-2G-FY-01` | SOURCE | COVERED | §6, §23.9 |  |
| `OL-2G-FY-02` | FIELD | COVERED | SIG-ONTO-030 | Full observation protocol required. |
| `OL-2G-FY-03` | REQ | COVERED | SIG-PUB-013 | Residential-parcel candidate never published at any precision. |

### 3. Decentralized local research ecosystem

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-3-01` | SOURCE | COVERED | SIG-INGEST-039 | All named groups seeded, `status=unverified`. *(closed in the gap-closure pass.)* |
| `OL-3-02` | SOURCE | COVERED | §33.7, G C-03, R-12 | Corrected: directory unreachable; SIG builds its own. |
| `OL-3-03` | REQ | COVERED | §34, §33.2 | Contributor tiers + task catalog. |
| `OL-3-04` | REQ | COVERED | §17.6, §21.4, §29.7, §33.2 #8 | Disappearance/diff/change-feed machinery. |
| `OL-3-05` | REQ | COVERED | §33.5, §33.6 | Geographic queues, non-exclusive, expiring. |
| `OL-3-06` | EXAMPLE | COVERED | Appendix D.3a | The research-gap object worked end to end. *(closed in the gap-closure pass.)* |
| `OL-3-07` | PURPOSE | COVERED | Part VI preamble |  |

### 4. Beyond Flock — the broader surveillance stack

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-4-00` | PRINCIPLE | COVERED | §5.2, SIG-CHART-027/028 | Generalization conformance suite. |
| `OL-4.1-01` | REQ | COVERED | §29.4 SIG-RECON-041 | Vendor replacement rendered as replacement. |
| `OL-4.1-02` | REQ | COVERED | §13.1 | Body-camera live streams now representable. *(closed in the gap-closure pass.)* |
| `OL-4.1-03` | SOURCE | COVERED | §22.2 | Community Connect enumerated and verified. |
| `OL-4.1-04` | REQ | COVERED | G C-06 | Corrected: 321 communities; 850k sums incommensurable counters. |
| `OL-4.1-05` | PRINCIPLE | COVERED | §12.4 | Extended from four roles to fourteen. |
| `OL-4.1-06` | SOURCE | COVERED | §22.6 B/E | Guardian, Community Connect and the enumeration thread registered. *(closed in the gap-closure pass.)* |
| `OL-4.2-01` | REQ | COVERED | §23.9 | Data Driven connector + historical findings. *(closed in the gap-closure pass.)* |
| `OL-4.3-01` | REQ | COVERED | §12.4, §11.10 system_scope, SIG-ONTO-018 | Vendor default never substitutes for deployment evidence. |
| `OL-4.4-01` | REQ | COVERED | §11.6, SIG-ONTO-024 | Capability is first-class; export/disclosure class added. |
| `OL-4.5-01` | SOURCE | COVERED | §22.6 E | WIRED source registered; figure corrected; veto applies. *(closed in the gap-closure pass.)* |
| `OL-4.5-02` | FIELD | COVERED | §19.2, SIG-ONTO-027 | No camera abstraction forced; service-area polygons. |
| `OL-4.6-01` | REQ | COVERED | SIG-ONTO-026, §19.2 | Deployment with no PhysicalAsset row. |
| `OL-4.7-01` | SOURCE | COVERED | §22.7 | All four FR datasets in the backlog. *(closed in the gap-closure pass.)* |
| `OL-4.7-02` | ENTITY | COVERED | SIG-ONTO-031 | Reference databases as DataSystems. |
| `OL-4.8-01` | REQ | COVERED | §13.1 device-forensics, §11.6 extract.* | Investigative extraction capabilities modelled. |
| `OL-4.9-01` | REQ | COVERED | Appendix D.5 pathway 3 | Extended to six layers (aggregator ≠ productizer). |
| `OL-4.9-02` | PRINCIPLE | COVERED | §1.4, §12.3, SIG-ONTO-026 | Access relationships without hardware. |
| `OL-4.10-01` | REQ | COVERED | §13.1 | All nine RTCC inputs representable. *(closed in the gap-closure pass.)* |
| `OL-4.10-02` | REQ | COVERED | §12.3, §12.9 | Thirteen typed integration edges replace integrates_with. |

### 5. International landscape

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-5-01` | REQ | COVERED | §5.1, §5.3 | US-first rationale; twelve wedge conditions. |
| `OL-5-02` | PRINCIPLE | COVERED | SIG-CHART-029 | International from the beginning. |
| `OL-5.1-01` | REQ | COVERED | SIG-CHART-030 |  |
| `OL-5.2-01` | SOURCE | COVERED | Phase 18 | Full technology coverage named. *(closed in the gap-closure pass.)* |
| `OL-5.2-02` | REQ | COVERED | Phase 18 | The OSM-vs-own-database debate recorded as federation precedent. *(closed in the gap-closure pass.)* |
| `OL-5.2-03` | REQ | COVERED | Phase 18 | The ~12,000-camera import is the studied precedent for contribution-back. *(closed in the gap-closure pass.)* |
| `OL-5.3-01` | SOURCE | COVERED | §22.7, SIG-ENG-036 | Registered; coarse granularity mandatory. *(closed in the gap-closure pass.)* |
| `OL-5.3-02` | REQ | COVERED | SIG-ONTO-021 | Record the coarsest level the evidence supports. |

### 6. What is missing from the ecosystem

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-6-00` | REQ | COVERED | §1.3 SIG-CHART-001 | General reconciliation layer. |
| `OL-6.1-01` | REQ | COVERED | §14.1 | LAPD example preserved verbatim. |
| `OL-6.1-02` | REQ | COVERED | §14.1, §14.2 | Per-class canonical identifier table. |
| `OL-6.1-03` | PRINCIPLE | COVERED | §14, P6, Phase 3/5 ordering | ER gates block analytics surfaces. |
| `OL-6.2-01` | EXAMPLE | COVERED | §8.5 SIG-ONTO-008 | Target statement reproduced verbatim in substance. |
| `OL-6.2-02` | PRINCIPLE | COVERED | SIG-ONTO-008 | Reconciliation as a first-class addressable object. |
| `OL-6.3-01` | REQ | COVERED | §9, §29.4 | Five temporal dimensions; lifecycle reconciliation. |
| `OL-6.3-02` | PRINCIPLE | COVERED | §9.2, §9.3, §12.1 | valid_*_kind corrects the NULL ambiguity. |
| `OL-6.4-01` | PRINCIPLE | COVERED | §10.1, §16.2 | Provenance attaches at claim level, not entity level. |
| `OL-6.5-01` | PRINCIPLE | COVERED | §31, §28.5, SIG-STORE-015 | UNRESOLVED publishable with all dissent attached. |
| `OL-6.5-02` | PRINCIPLE | COVERED | SIG-RECON-057 | Every detector emits a task with a closing condition. |
| `OL-6.6-01` | REQ | COVERED | §30.2, §12.3 | Access-path closure across vendors. |
| `OL-6.7-01` | VOCAB | COVERED | §13.4 | All fourteen states retained across four tracks; ten added. |
| `OL-6.7-02` | PRINCIPLE | COVERED | SIG-ONTO-062, SIG-RECON-041 | replaced is an edge, not a state. |

### 7. Project definition

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-7-01` | PURPOSE | COVERED | §1.1 |  |
| `OL-7-02` | PRINCIPLE | COVERED | §43.1 SIG-PUB-001 |  |
| `OL-7.1-01` | REQ | COVERED | §4.1 G1 | Bound to Phase 3 and a metric. |
| `OL-7.1-02` | REQ | COVERED | §4.1 G2 |  |
| `OL-7.1-03` | REQ | COVERED | §4.1 G3, §32.3 | Target 100% resolvable evidence. |
| `OL-7.1-04` | REQ | COVERED | §4.1 G4, §9 |  |
| `OL-7.1-05` | REQ | COVERED | §4.1 G5, §12 |  |
| `OL-7.1-06` | REQ | COVERED | §4.1 G6, §32.2 |  |
| `OL-7.1-07` | REQ | COVERED | §4.1 G7, §33 |  |
| `OL-7.1-08` | REQ | COVERED | §4.1 G8, §37–§39 | Seven audiences named. |
| `OL-7.2-01` | NONGOAL | COVERED | N1, SIG-STORE-026 | No plate-capable column; schema test. |
| `OL-7.2-02` | NONGOAL | COVERED | N2, §18.1, §24.2 |  |
| `OL-7.2-03` | NONGOAL | COVERED | N3, §43.4 | Five-prong test, two concurring reviewers. |
| `OL-7.2-04` | NONGOAL | COVERED | §30.3 | Pointer corrected. *(closed in the gap-closure pass.)* |
| `OL-7.2-05` | NONGOAL | COVERED | §46.3, SIG-CONTRIB-007 | Pointers corrected. *(closed in the gap-closure pass.)* |
| `OL-7.2-06` | NONGOAL | COVERED | §43.5 SIG-PUB-013 | Pointer corrected. *(closed in the gap-closure pass.)* |
| `OL-7.2-07` | NONGOAL | COVERED | N7, §35.2, SIG-CONTRIB-014 |  |
| `OL-7.2-08` | NONGOAL | COVERED | N8, §6, §35.3 |  |
| `OL-7.2-09` | NONGOAL | COVERED | N9, §11.16 |  |
| `OL-7.2-10` | NONGOAL | COVERED | N10, SIG-CHART-019, §32.2 |  |

### 8. Conceptual graph model (every entity and field is an obligation)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-8.1-01` | ENTITY | COVERED | §11.2 organization_type | All fourteen example classes present, namespaced. |
| `OL-8.1-02` | FIELD | COVERED | §11.2 | All listed fields present as predicates. |
| `OL-8.2-01` | ENTITY | COVERED | SIG-ONTO-012 | Corrected: vendor is a role, not a subtype. |
| `OL-8.2-02` | EXAMPLE | COVERED | §14.5 acquired, §11.4 | Axon→Fusus expressible with time bounds. |
| `OL-8.2-03` | PRINCIPLE | COVERED | §11.4 product_name/vendor time-bounded |  |
| `OL-8.3-01` | ENTITY | COVERED | §11.4 | Cellebrite UFED restored. *(closed in the gap-closure pass.)* |
| `OL-8.3-02` | PRINCIPLE | COVERED | SIG-ONTO-017 |  |
| `OL-8.4-01` | ENTITY | COVERED | §11.5, §11.6, §13.1 | All twelve examples present in the 13-domain taxonomy. |
| `OL-8.4-02` | PRINCIPLE | COVERED | P7, §11.5 |  |
| `OL-8.5-01` | ENTITY | COVERED | §11.7 |  |
| `OL-8.5-02` | FIELD | COVERED | §11.7 | All fields retained; counts split per §29.1. |
| `OL-8.6-01` | ENTITY | COVERED | §11.8, SIG-ONTO-027 | Including RTCC facility and camera trailer. |
| `OL-8.6-02` | FIELD | COVERED | §11.8 | All fields present; owner/operator expanded to 14 roles. |
| `OL-8.6-03` | PRINCIPLE | COVERED | SIG-GEO-004 | Coordinates optional; four cases specified. |
| `OL-8.7-01` | ENTITY | COVERED | §11.10 |  |
| `OL-8.7-02` | FIELD | COVERED | §11.10 | Plus system_scope and holds_data_collected_by. |
| `OL-8.8-01` | ENTITY | COVERED | §12.5 |  |
| `OL-8.8-02` | FIELD | COVERED | §12.5, §12.1 | All attributes present plus asserted_by. |
| `OL-8.8-03` | PRINCIPLE | COVERED | SIG-ONTO-049, §12.2 | Direction required; three edge types never merged. |
| `OL-8.9-01` | ENTITY | COVERED | §12.3 | Thirteen typed edges; integrates_with prohibited as stored. |
| `OL-8.10-01` | ENTITY | COVERED | §11.11 |  |
| `OL-8.10-02` | FIELD | COVERED | §11.11 | Plus acquisition_channel and parent_cooperative_contract. |
| `OL-8.10-03` | REQ | COVERED | §23.6, §13.4 track 1, amends_contract |  |
| `OL-8.11-01` | ENTITY | COVERED | §11.13 policy_type | All seven examples present. |
| `OL-8.11-02` | FIELD | COVERED | §11.13 applies_to polymorphic |  |
| `OL-8.12-01` | ENTITY | COVERED | §11.15 | Promoted to first-class time-versioned entity. |
| `OL-8.12-02` | EXAMPLE | COVERED | SIG-ONTO-043, §29.6, SIG-UI-045 | Canonical divergence case rendered without collapse. |
| `OL-8.13-01` | ENTITY | COVERED | §11.16 |  |
| `OL-8.13-02` | FIELD | COVERED | §11.16 | All SearchAggregate fields plus coverage_period. |
| `OL-8.13-03` | PRINCIPLE | COVERED | §18.1, N9 |  |
| `OL-8.14-01` | ENTITY | COVERED | §11.17 event_type | All ten examples present. |
| `OL-8.14-02` | FIELD | COVERED | §11.17 epistemic_status | Required and rendered everywhere. |
| `OL-8.15-01` | ENTITY | COVERED | §10.2 | Split four ways: Source/Artifact/Capture/Extraction. |
| `OL-8.15-02` | FIELD | COVERED | §10.3.2, §10.3.3 | All eleven fields present. |
| `OL-8.15-03` | REQ | COVERED | §10.3.2 artifact_type | All eight examples covered. |
| `OL-8.16-01` | ENTITY | COVERED | §10.3.5 |  |
| `OL-8.16-02` | FIELD | COVERED | §16.2 | `object_type` and `unit` added; `asserted_by` is now an FK. *(closed in the gap-closure pass.)* |
| `OL-8.16-03` | EXAMPLE | COVERED | Appendix D.4 | Worked provenance chain for exactly this shape. |

### 9. Epistemic architecture

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-9-01` | PRINCIPLE | COVERED | §10 | Six distinctions as concrete objects. |
| `OL-9.1-01` | VOCAB | COVERED | §10.4 R1/R2 | Tier A split by directness; mapping table retained. |
| `OL-9.1-02` | VOCAB | COVERED | §10.4 R2 |  |
| `OL-9.1-03` | VOCAB | COVERED | §10.4 R3 | Upturn restored to the R3 examples. *(closed in the gap-closure pass.)* |
| `OL-9.1-04` | VOCAB | COVERED | §10.4 R4 |  |
| `OL-9.1-05` | VOCAB | COVERED | §10.4 R5 |  |
| `OL-9.1-06` | VOCAB | COVERED | §10.4 R6, SIG-LLM-005 |  |
| `OL-9.1-07` | PRINCIPLE | COVERED | SIG-EPIS-015, §10.5 | Novelty ≠ unreliability; D6 is admissibility, not rank. |
| `OL-9.2-01` | PRINCIPLE | COVERED | §9.1, §9.2 SIG-TIME-002/003 | Portal example reproduced; T1 never inferred at ingest. |
| `OL-9.3-01` | PRINCIPLE | COVERED | SIG-EPIS-022 | Numeric confidence prohibited unless calibrated. |
| `OL-9.3-02` | VOCAB | COVERED | §10.7 | Three orthogonal fields; all six labels recoverable. |
| `OL-9.4-01` | PRINCIPLE | COVERED | §9.5, §32.1 | Four epistemic states; CoverageRecord. |
| `OL-9.4-02` | EXAMPLE | COVERED | §32.1, SIG-UI-012 | sources_searched[] required. |
| `OL-9.4-03` | REQ | COVERED | SIG-TIME-012, SIG-API-003, SIG-UI-007 |  |

### 10. Source ingestion strategy

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-10.1A-01` | STAGE | COVERED | Phase 3, §14 | Identity registry before anything is counted. |
| `OL-10.1A-02` | REQ | COVERED | §14.2 | All seven identity aids present. |
| `OL-10.1B-01` | STAGE | COVERED | §23.2, Phase 4 | ID, version, tags, coordinates, attribution preserved. |
| `OL-10.1B-02` | PRINCIPLE | COVERED | N7, SIG-CONTRIB-014 |  |
| `OL-10.1C-01` | STAGE | COVERED | §23.3, Phase 4 |  |
| `OL-10.1C-02` | REQ | COVERED | §20.3 SIG-STORE-039 | Explicit Atlas crosswalk with lossy flags. |
| `OL-10.1D-01` | STAGE | COVERED | §22.5, Phase 11 gate |  |
| `OL-10.1D-02` | REQ | COVERED | §23.4 | Hotlist hits and vehicles-detected added. *(closed in the gap-closure pass.)* |
| `OL-10.1E-01` | STAGE | COVERED | §18.1, §23.7 | No plate/search rows ingested. |
| `OL-10.1E-02` | REQ | COVERED | §23.7, §11.16 | Structural aggregates only; custody stays upstream. |
| `OL-10.1F-01` | STAGE | COVERED | §23.5, §23.6, Phase 7 |  |
| `OL-10.1G-01` | STAGE | COVERED | §23.8, Phase 13 |  |

### 11. Reconciliation workflows

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-11.1-01` | REQ | COVERED | §29.1 | All six input classes as distinct predicates. |
| `OL-11.1-02` | FIELD | COVERED | §29.1 SIG-RECON-029 | Every count predicate with its own resolution + deltas. |
| `OL-11.1-03` | PRINCIPLE | COVERED | SIG-RECON-028/029, SIG-STORE-015 | PREDICATE_CONFLATION; no single true count. |
| `OL-11.2-01` | REQ | COVERED | §29.2 | Candidate generation spec + probable label at L4. |
| `OL-11.2-02` | REQ | COVERED | §29.2 SIG-RECON-033, §33.2 #5 | Human/documentary promotion only. |
| `OL-11.3-01` | REQ | COVERED | §29.3, §12.2 | All five source types kept distinct. |
| `OL-11.3-02` | PRINCIPLE | COVERED | SIG-ONTO-042, SIG-RECON-034 | No operation merges the three edge types. |
| `OL-11.4-01` | EXAMPLE | COVERED | §29.4, §13.4 | Four-track timeline; unordered-within-window for fuzzy dates. |

### 12. Research task generation

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-12-00` | REQ | COVERED | Part VI preamble, §33 |  |
| `OL-12-01` | REQ | COVERED | §33.2 #1 |  |
| `OL-12-02` | REQ | COVERED | §33.2 #2 |  |
| `OL-12-03` | REQ | COVERED | §33.2 #3, §29.5 |  |
| `OL-12-04` | REQ | COVERED | §33.2 #4, §28.3 |  |
| `OL-12-05` | REQ | COVERED | §33.2 #5, SIG-ONTO-028 |  |
| `OL-12-06` | REQ | COVERED | §33.2 #6, §14.4 |  |
| `OL-12-07` | REQ | COVERED | §33.2 #7, SIG-RECON-041 |  |
| `OL-12-08` | PURPOSE | COVERED | Part VI, §7 leverage metrics |  |

### 13. Ethical and security constraints

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-13-00` | PRINCIPLE | COVERED | SIG-CHART-024, §44 |  |
| `OL-13.1-01` | PRINCIPLE | COVERED | SIG-CHART-024, §43.1 |  |
| `OL-13.1-02` | REQ | COVERED | §18.1, N9 |  |
| `OL-13.2-01` | REQ | COVERED | §43.2 | All six categories excluded; addresses made categorical. |
| `OL-13.2-02` | REQ | COVERED | §43.4 | Five prongs + two concurring reviewers. |
| `OL-13.3-01` | REQ | COVERED | §43.3, §19.4 | Five-class matrix covering all five listed cases. |
| `OL-13.4-01` | REQ | COVERED | §17.5, SIG-EVID-010/011 | Sealed tier + public metadata + redacted derivative. |
| `OL-13.5-01` | REQ | COVERED | SIG-CHART-023 |  |
| `OL-13.5-02` | NONGOAL | COVERED | SIG-CHART-023, SIG-GOV-018 |  |

### 14. Licensing and data governance

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-14.1-01` | REQ | COVERED | §42.3 |  |
| `OL-14.1-02` | REQ | COVERED | §42.3 point 4 | Strategy A analysed and rejected with the guideline text. |
| `OL-14.1-03` | REQ | COVERED | §42.3 SIG-LIC-006 | Strategy B adopted. |
| `OL-14.1-04` | REQ | COVERED | §42.3 point 5 | Strategy C analysed and rejected. |
| `OL-14.1-05` | REQ | COVERED | SIG-LIC-009 | Four residuals referred to counsel and in the risk register. |
| `OL-14.2-01` | FIELD | COVERED | §42.1 SIG-LIC-001 | All six fields; redistributable separately reviewed. |
| `OL-14.2-02` | PRINCIPLE | COVERED | SIG-LIC-004 | UNDETERMINED fails the export gate closed. |
| `OL-14.3-01` | PRINCIPLE | COVERED | SIG-LIC-012 |  |
| `OL-14.3-02` | REQ | COVERED | SIG-LIC-012, §38 | All seven deliverables required for a release. |

### 15. Product surfaces

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-15.1-01` | SURFACE | COVERED | §39.2 |  |
| `OL-15.1-02` | FIELD | COVERED | §39.2, Appendix D | All fifteen output elements present. |
| `OL-15.1-03` | PRINCIPLE | COVERED | SIG-UI-002/010 | Dossier is the design center and primary artifact. |
| `OL-15.2-01` | SURFACE | COVERED | §39.3 | All seven layers plus a bound coverage underlay. |
| `OL-15.3-01` | SURFACE | COVERED | §39.4, §30.2 | Ego network; all four questions answerable. |
| `OL-15.4-01` | SURFACE | COVERED | §39.5 | Plus iCal/RSS subscriptions. |
| `OL-15.5-01` | SURFACE | COVERED | §39.6 | All eight expansions present. |
| `OL-15.6-01` | SURFACE | COVERED | §39.7, §33 | Task cards with closing conditions. |
| `OL-15.7-01` | SURFACE | COVERED | §38.4 | Six downstream classes as validated design targets. *(closed in the gap-closure pass.)* |

### 16. Initial release boundaries

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-16-01` | REQ | COVERED | SIG-CHART-025 |  |
| `OL-16-02` | REQ | COVERED | §5.1 | All twelve conditions enumerated. |
| `OL-16-03` | VOCAB | COVERED | SIG-CHART-026 | All six vendors. |
| `OL-16-04` | REQ | COVERED | SIG-CHART-027/028 | Generalization conformance suite from Phase 4. |

### 17. Staged project plan

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-17.0-01` | STAGE | COVERED | Phase 0 deliverable 4 | Extended from seven to nineteen projects. |
| `OL-17.0-02` | STAGE | COVERED | Phase 0 deliverables 2–4, §22.1 |  |
| `OL-17.1-01` | STAGE | COVERED | Phases 1–4 |  |
| `OL-17.1-02` | STAGE | COVERED | Phase 4 / Phase 6 acceptance |  |
| `OL-17.2-01` | STAGE | COVERED | Phase 8, §29 |  |
| `OL-17.2-02` | STAGE | COVERED | Phase 8 acceptance |  |
| `OL-17.3-01` | STAGE | COVERED | Phase 12, §23.7 |  |
| `OL-17.3-02` | STAGE | COVERED | Phase 12, §30.2 |  |
| `OL-17.4-01` | STAGE | COVERED | Phase 13, §11.13/11.14/11.17 |  |
| `OL-17.4-02` | STAGE | COVERED | Phase 13 acceptance |  |
| `OL-17.5-01` | STAGE | COVERED | Phase 17 | Priority order preserved exactly. |
| `OL-17.6-01` | STAGE | COVERED | Phase 18 | (§5.3 mis-cites this as Phase 14 — see DEFECTS.) |

### 18. Relationship to existing projects (the whole table is an obligation)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-18-01` | REQ | COVERED | §6 row 1 |  |
| `OL-18-02` | REQ | COVERED | §6 row 2 |  |
| `OL-18-03` | REQ | COVERED | §6 row 3, §22.5 |  |
| `OL-18-04` | REQ | COVERED | §6 row 4, §23.7 |  |
| `OL-18-05` | REQ | COVERED | §6 row 5, §24.2 |  |
| `OL-18-06` | REQ | COVERED | §6 row 6, §23.3 |  |
| `OL-18-07` | REQ | COVERED | §23.9 | Connector + corrected pointer. *(closed in the gap-closure pass.)* |
| `OL-18-08` | REQ | COVERED | §6 row 8, §23.8 |  |
| `OL-18-09` | REQ | COVERED | §6 row 10, §11.19 |  |
| `OL-18-10` | REQ | COVERED | §6 row 12, §38 |  |
| `OL-18-11` | REQ | COVERED | §6 row 13, §23.9 |  |
| `OL-18-12` | REQ | COVERED | §6 row 14, §43.5 |  |
| `OL-18-13` | REQ | COVERED | §6 row 15, §33.7 | Corrected: SIG maintains its own registry. |
| `OL-18-14` | REQ | COVERED | §6 row 16, §33.5 |  |
| `OL-18-15` | REQ | COVERED | §6 row 17, Phase 18 |  |
| `OL-18-16` | REQ | COVERED | §6 row 18 |  |
| `OL-18-17` | REQ | COVERED | §6 row 19, §30 labelling |  |

### 19. Data-quality principles (each is an architectural invariant)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-19.1` | PRINCIPLE | COVERED | §3.2 P1 | No writable current-value columns; no_orphan_facts CI check. |
| `OL-19.2` | PRINCIPLE | COVERED | §3.2 P2 | raw_value NOT NULL. |
| `OL-19.3` | PRINCIPLE | COVERED | §3.2 P3 | UPDATE revoked at role level; §45.4 adds suppression. |
| `OL-19.4` | PRINCIPLE | COVERED | §3.2 P4 | UNRESOLVED first-class. |
| `OL-19.5` | PRINCIPLE | COVERED | §3.2 P5 | Contribution-back is a funded phase. |
| `OL-19.6` | PRINCIPLE | COVERED | §3.2 P6 | Phase ordering + ER quality gates + UI disclosure. |
| `OL-19.7` | PRINCIPLE | COVERED | §3.2 P7 | No vendor name in any schema identifier. |
| `OL-19.8` | PRINCIPLE | COVERED | §3.2 P8, §12.4 | Extended from six roles to fourteen. |
| `OL-19.9` | PRINCIPLE | COVERED | §3.2 P9, §12.2 |  |
| `OL-19.10` | PRINCIPLE | COVERED | §3.2 P10, §29.6 |  |
| `OL-19.11` | PRINCIPLE | COVERED | §3.2 P11, §29.1 |  |
| `OL-19.12` | PRINCIPLE | COVERED | §3.2 P12, §32.4, SIG-TIME-005 |  |

### 20. Mandatory research questions (all 37 must be answered in the spec)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-Q01` | Q | COVERED | Appendix B Q1 | **ANSWERED** — public unauthenticated JSON API verified (SC-18). Phase 11 ungated. *(closed in the completion pass.)* |
| `OL-Q02` | Q | COVERED | Appendix B Q2 | **ANSWERED** — ~9.5mo per-portal history + 29 archived API captures. *(closed in the completion pass.)* |
| `OL-Q03` | Q | COVERED | Appendix B Q3 | **ANSWERED: CC BY-SA 4.0.** ShareAlike forced the N-compartment licence model. *(closed in the completion pass.)* |
| `OL-Q04` | Q | COVERED | Appendix B Q4 | **ANSWERED** — record types + fields documented; licence: none stated. *(closed in the completion pass.)* |
| `OL-Q05` | Q | COVERED | Appendix B Q5 | **ANSWERED** — 15 GitLab repos, REST API, open bulk archive. *(closed in the completion pass.)* |
| `OL-Q06` | Q | COVERED | Appendix B Q6 | Bulk CSV; EFF device-layer delegation recorded. |
| `OL-Q07` | Q | COVERED | Appendix B Q7 | api_v2, 401, JWT, rate limit — outline corrected. |
| `OL-Q08` | Q | COVERED | Appendix B Q8 | Called successfully. |
| `OL-Q09` | Q | COVERED | Appendix B Q9, §14.2 | ORI9 + LEAIC. |
| `OL-Q10` | Q | COVERED | Appendix B Q10, §14.2/14.4 | Per-class identifiers + two ORI traps. |
| `OL-Q11` | Q | COVERED | Appendix B Q11 | GEOID/GNIS/GeoNames; fixed-width + level. |
| `OL-Q12` | Q | COVERED | Appendix B Q12, §14.4 | Surrogate + identity_basis + aggregate publication. |
| `OL-Q13` | Q | COVERED | Appendix B Q13, §42.3 | Guideline conflict analysed; conservative reading. |
| `OL-Q14` | Q | COVERED | Appendix B Q14 | Answered 'not by separation alone'; Strategy B. |
| `OL-Q15` | Q | COVERED | Appendix B Q15 | **ANSWERED** — 4 of 6 have no licence or an affirmative refusal; export gate closed against them. *(closed in the completion pass.)* |
| `OL-Q16` | Q | COVERED | Appendix B Q16, §8.4 | custody_posture enforced before fetch. |
| `OL-Q17` | Q | COVERED | Appendix B Q17 | **ANSWERED** — cadence set by the upstream refresh (~monthly), not by SIG. *(closed in the completion pass.)* |
| `OL-Q18` | Q | COVERED | Appendix B Q18, §17.6 |  |
| `OL-Q19` | Q | COVERED | Appendix B Q19 | **VERIFIED** — history API tested; surfaced the element-repurposing dating trap. *(closed in the completion pass.)* |
| `OL-Q20` | Q | COVERED | Appendix B Q20, §15.1 | Hybrid with relational core; scored. |
| `OL-Q21` | Q | COVERED | Appendix B Q21, §15.3 |  |
| `OL-Q22` | Q | COVERED | Appendix B Q22, §18 |  |
| `OL-Q23` | Q | COVERED | Appendix B Q23, §21.3 |  |
| `OL-Q24` | Q | COVERED | Appendix B Q24, §26 | Reframed as four legal tracks. |
| `OL-Q25` | Q | COVERED | Appendix B Q25, §17.2/17.3/17.4 |  |
| `OL-Q26` | Q | COVERED | Appendix B Q26, §24 | Seven-layer ladder. |
| `OL-Q27` | Q | COVERED | Appendix B Q27, §14.6 | Tiers 0–3. |
| `OL-Q28` | Q | COVERED | Appendix B Q28, §14.6 | Tiers 4–5 to review; LLMs may not write. |
| `OL-Q29` | Q | COVERED | Appendix B Q29, §14.5 | Rename ≠ succession; five fixtures. |
| `OL-Q30` | Q | COVERED | Appendix B Q30, §43 |  |
| `OL-Q31` | Q | COVERED | Appendix B Q31, SIG-EVID-010 |  |
| `OL-Q32` | Q | COVERED | Appendix B Q32, §45 | Includes suppression as a distinct primitive. |
| `OL-Q33` | Q | COVERED | Appendix B Q33 | **ANSWERED** — CoC read; human review is outside its scope; MapRoulette verified. *(closed in the completion pass.)* |
| `OL-Q34` | Q | COVERED | Appendix B Q34 | PARTIAL answer, honestly labelled; Stage-0 item. |
| `OL-Q35` | Q | COVERED | Appendix B Q35 | PARTIAL answer; task→RecordsRequest model specified regardless. |
| `OL-Q36` | Q | COVERED | Appendix B Q36, §33.5 |  |
| `OL-Q37` | Q | COVERED | Appendix B Q37, §14.8 |  |

### 21. Priority source registry (every URL must appear in the spec's source registry)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-21-01` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-02` | SOURCE | COVERED | §22.6 A | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-21-03` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-04` | SOURCE | COVERED | §22.6 A | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-21-05` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-06` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-07` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-08` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-09` | SOURCE | COVERED | §22.6 B | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-21-10` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-11` | SOURCE | COVERED | §22.6 C | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-21-12` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-13` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-14` | SOURCE | COVERED | §22.6 C | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-21-15` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-16` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-17` | SOURCE | COVERED | §22.6 D | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-21-18` | SOURCE | COVERED | §22.6 D, §22.7 | URL seeded + roster. *(closed in the gap-closure pass.)* |
| `OL-21-19` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-20` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-21` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-22` | SOURCE | COVERED | §22.6 E | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-21-23` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-24` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-25` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-26` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-27` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-28` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-29` | SOURCE | COVERED | §22.6 I | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-21-30` | SOURCE | COVERED | §22.7 | All ten classes enumerated. *(closed in the gap-closure pass.)* |
| `OL-21-31` | SOURCE | COVERED | §22.6 E | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-21-32` | SOURCE | COVERED | §22.6 E | URL seeded + leak-provenance veto. *(closed in the gap-closure pass.)* |
| `OL-21-33` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-34` | SOURCE | COVERED | §22.6 E | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-21-35` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-36` | SOURCE | COVERED | §22.6 C | URL seeded, paywalled. *(closed in the gap-closure pass.)* |
| `OL-21-37` | SOURCE | COVERED | §22.6 B/H | Both threads registered; Reddit is manual-reference only. *(closed in the gap-closure pass.)* |

### 22. Critical conclusions

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-22.1-01` | PRINCIPLE | COVERED | §3.7 SIG-CHART-020 | Full fact→generator table reproduced. |
| `OL-22.1-02` | PRINCIPLE | COVERED | §3.7, Part V |  |
| `OL-22.2-01` | PURPOSE | COVERED | §3.6 SIG-CHART-018 | Authority claim stated verbatim as a bounded claim. |
| `OL-22.3-01` | PRINCIPLE | COVERED | §5.2 rationale | capability→deployment→assets/data/access. |
| `OL-22.4-01` | PRINCIPLE | COVERED | §30.2, §12.9, §39.4 | All seven central questions answerable. |
| `OL-22.4-02` | REQ | COVERED | §39.4, §30.2, P6 | Central, but gated on ER quality. |
| `OL-22.5-01` | PRINCIPLE | COVERED | §13.4, §28.3, Appendix G | Current dynamics modelled as state + edge changes. |
| `OL-22.5-02` | REQ | COVERED | SIG-RECON-041/042 | Canceled+installed stated plainly in UI and API. |
| `OL-22.6-01` | PURPOSE | COVERED | §7, §32.6 | All six leverage measures instrumented. |
| `OL-22.6-02` | PURPOSE | COVERED | SIG-CHART-035, §46.5 |  |

### 23. One-sentence specification

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-23-01` | PURPOSE | COVERED | §1.1 | Preserved verbatim. |

### 24. Guidance to the downstream design agent (all 18 are binding)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-24-01` | REQ | COVERED | Appendix G, §22.2 | Ecosystem re-verified; 14 factual corrections. |
| `OL-24-02` | REQ | COVERED | §22.2 access matrix | VERIFIED = a request was made and observed. |
| `OL-24-03` | REQ | COVERED | §22.2, SIG-INGEST-024 | Access verified, not assumed. |
| `OL-24-04` | REQ | COVERED | §14, Phase 3/5 before Phase 12 | ER precedes analytics by phase order. |
| `OL-24-05` | REQ | COVERED | Phases 1–2 before Phase 4 |  |
| `OL-24-06` | REQ | COVERED | §42.3, R-01, Phase 0/4 |  |
| `OL-24-07` | REQ | COVERED | SIG-CHART-014, §8.4 custody postures |  |
| `OL-24-08` | REQ | COVERED | SIG-STORE-043, §14.2 |  |
| `OL-24-09` | REQ | COVERED | §8.1 six layers | L0/L1/L3/L4 physically separated. |
| `OL-24-10` | REQ | COVERED | §18.1, N2, OL-A.8 |  |
| `OL-24-11` | REQ | COVERED | §31, SIG-EPIS-011, SIG-UI-009 |  |
| `OL-24-12` | REQ | COVERED | §33.1/§33.2, §39.7 |  |
| `OL-24-13` | REQ | COVERED | SIG-CHART-025/027 |  |
| `OL-24-14` | REQ | COVERED | §12.4, §12.3 enrolls_asset_into, §14.4 |  |
| `OL-24-15` | REQ | COVERED | SIG-ONTO-026/031, §19.2 |  |
| `OL-24-16` | REQ | COVERED | SIG-ONTO-062, SIG-RECON-041 |  |
| `OL-24-17` | REQ | COVERED | §37, §38, SIG-LIC-004 |  |
| `OL-24-18` | REQ | COVERED | §10.1, SIG-PARSE-003, Appendix D.4 |  |
| `OL-24-19` | PRINCIPLE | COVERED | §3.1 | Preserved verbatim; §3.3 binds each clause. |
| `OL-24-20` | PRINCIPLE | COVERED | §3.1, §3.3 | Preserved verbatim with enforcement points. |

### Appendix A — findings that changed the conception

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-A.1` | REQ | COVERED | §22.5, R-02, Phase 0 gate |  |
| `OL-A.2` | REQ | COVERED | §33.5, §33.7, §34 |  |
| `OL-A.3` | REQ | COVERED | §5.2 rationale, §13.4 |  |
| `OL-A.4` | REQ | COVERED | §22.2, §12.4, §14.4 |  |
| `OL-A.5` | REQ | COVERED | §1.4, §12.5 |  |
| `OL-A.6` | REQ | COVERED | §13.4 |  |
| `OL-A.7` | REQ | COVERED | §10, §16.2 |  |
| `OL-A.8` | REQ | COVERED | §18.1, §8.4 DERIVE posture |  |

### Appendix B — illustrative local dossier (the spec must be able to emit this exact object)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-B-01` | FIELD | COVERED | Appendix D, §11.1 |  |
| `OL-B-02` | FIELD | COVERED | Appendix D, §11.2 |  |
| `OL-B-03` | FIELD | COVERED | Appendix D.2 | Split into three predicates with separate resolutions. |
| `OL-B-04` | FIELD | COVERED | §11.11, §39.5, SIG-UI-015 |  |
| `OL-B-05` | FIELD | COVERED | Appendix D.3, §29.5 | Split into three retention predicates. |
| `OL-B-06` | FIELD | COVERED | Appendix D.3, §12.2 | Split configured vs observed. |
| `OL-B-07` | FIELD | COVERED | Appendix D.3, §11.16, SIG-RECON-011 | Windowed predicate with explicit bounds. |
| `OL-B-08` | FIELD | COVERED | Appendix D.3, §29.2 |  |
| `OL-B-09` | FIELD | COVERED | Appendix D.3, §9.5, SIG-UI-015 | 'unknown' rendered, not omitted. |
| `OL-B-10` | FIELD | COVERED | §11.17, SIG-UI-010 |  |
| `OL-B-11` | FIELD | COVERED | Appendix D.2, §33.2 | Detectors 1,2,3,4,27 cover the five listed gaps. |
| `OL-B-12` | REQ | COVERED | §1.3, §39.2, SIG-CHART-002 |  |

### Appendix C — illustrative surveillance pathways (all three must be representable and traversable)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-C-01` | EXAMPLE | COVERED | Appendix D.5 pathway 1 | enrolls_asset_into sharpens 'streams_via'. |
| `OL-C-02` | EXAMPLE | COVERED | Appendix D.5 pathway 2 | Directional, scoped, dated, separately evidenced. |
| `OL-C-03` | EXAMPLE | COVERED | Appendix D.5 pathway 3 | Six layers, not five. |
| `OL-C-04` | PURPOSE | COVERED | Appendix D.5, §30.2 |  |
## A.4 Maintenance

**SIG-ENG-037 (MUST).** This matrix MUST be regenerated at every phase gate (SIG-ENG-031) from
`OUTLINE_TRACE.md` plus the current spec, and a CI check MUST fail if any row's disposition
regresses from `COVERED`. The superset property is not a one-time claim; it is an invariant a later
edit can break.

**SIG-ENG-038 (SHOULD).** The regeneration SHOULD first **split compound trace rows** whose members
are independently satisfiable. The adversarial review identified this as a real weakness: a row
folding seven technologies into one obligation can be six-sevenths discharged without turning red,
which is precisely how one missing technology escaped detection in the first pass.


# Appendix B — Answers to the 37 mandatory questions (outline §20)

The outline designates these as mandatory research tasks for the downstream agent. Each is answered
with its status: **ANSWERED** (resolved with evidence), **ANSWERED-DESIGN** (a design decision made
here), **PARTIAL** (partly resolved; residual in the risk register), or **BLOCKED** (could not be
resolved; the spec hedges and Stage 0 must close it).

## Data access

**Q1 — Does Eyes on Flock expose an API, downloadable database, or archival repository?**
**ANSWERED — YES, and verified independently** (SC-18, R2-F2.6). A public, unauthenticated,
key-free JSON API: `GET /api/v1/data` returns HTTP 200, 7.6 MB, `{summary, portals}` with **950
portals × 20 fields** plus national roll-ups; `GET /api/audit/{state}/{slug}` is paginated and
supports **`?download=true` for CSV bulk export**; `GET /api/v1/map/{slug}` returns imagery.
`robots.txt` grants `User-agent: * → Allow: /`. No headless browser is required.

**The portal field set maps almost one-for-one onto the outline's inventory (OL-2B-FP-02)**,
including `data_retention`, `total_cameras`, `total_searches`, `vehicles_captured`, `hotlist_hits`,
`organizations_shared_with`, `organizations_received_from`, and `prohibited_uses`. **Phase 11 is
unblocked and risk R-02 is closed.**

**Q2 — Can we obtain its historical portal snapshots directly?** **ANSWERED — yes, two ways.**
(a) The audit exports themselves carry roughly **9.5 months of accumulated history per portal**, far
exceeding the vendor's ~30-day public window. (b) The Internet Archive holds **29 captures of the
API endpoint itself** spanning about 13 months, giving SIG a back-fill at **zero cost to the
operator** (SIG-INGEST-030b).

This matters disproportionately because the vendor's own domains are excluded from the general web
archive (SC-13): these aggregator captures are plausibly the **only** longitudinal record of portal
state that exists anywhere.

**Q3 — What are its reuse/licence terms?** **ANSWERED: CC BY-SA 4.0**, stated in the site footer
and confirmed in the built JS bundle. Contact published: `contact@eyesonflock.com`.

**ShareAlike is architecturally consequential**, not merely an attribution note: it is a *third*
incompatible licence regime alongside ODbL and CC-BY-4.0, and it forced the export model from a
two-way split to the N-compartment design of SIG-LIC-004a. A residual question remains open —
whether the grant is intended to cover the **API payload** as well as site content — and it is a
Stage-0 question for the operator (G.4.3).

**Q4 — What exports does HIBF make available, under what licence and cadence?** **PARTIAL.** The
record *types* and their exact fields are documented in full and captured verbatim (F2.3):
Organization Audit, Network Audit, Portal/Public Audit, SharedNetworks.csv, Event Logs, and
Configuration Settings. Licence and cadence were **not** located; Stage 0 must resolve them.

**Q5 — What APIs/exports does ALPR Watch publish?** **PARTIAL.** Confirmed public artifacts: KMZ
avoidance packages, offline routing data packages, a Superset FOIA dashboard, and GitLab
repositories — **GitLab, not GitHub** (F1.10). No REST API observed. The project's scope has shifted
materially from the outline's description.

**Q6 — What machine-readable interfaces does EFF Atlas expose beyond CSV?** **PARTIAL.** Bulk CSV
confirmed; >15,000 datapoints across 6,000+ jurisdictions; last updated 2026-08-12. No additional
public API confirmed. Notably, EFF has publicly delegated the device layer to DeFlock (SC-10),
which defines the federation boundary.

**Q7 — MuckRock API constraints and redistribution terms?** **ANSWERED (constraints).** It is
**api_v2**, not the v1 the outline references; **every data endpoint returns 401**; auth is a
5-minute JWT; ~15 requests/minute. Redistribution terms remain a Stage 0 item.

**Q8 — What can be pulled from DocumentCloud programmatically?** **ANSWERED.** The search API and
S3 full-text assets were successfully called unauthenticated for public documents.

## Identity

**Q9 — Best public canonical US law-enforcement agency identifier?** **ANSWERED.** **ORI9**, via the
FBI CDE per-state agency endpoints (api.data.gov key required), with the **LEAIC crosswalk** as the
essential ORI↔FIPS↔place bridge — obtained **manually**, not automatically (§14.2).

**Q10 — How complete are ORI codes, and how should non-LE entities be represented?** **ANSWERED.**
Broad for law enforcement, absent for everything else. Non-LE entities use per-class identifiers
(GEOID, NCES LEAID, IPEDS UNITID, NTD ID, CMS CCN, GLEIF LEI, SAM UEI) or a SIG surrogate with an
immutable `identity_basis` (§14.4). Two ORI traps are specified: the 9-character pattern must not be
parsed positionally for state, and alphabetic-9th-character ORIs may be civil/applicant ORIs
(SIG-IDENT-002/003).

**Q11 — Which datasets provide canonical municipal/county/state identifiers?** **ANSWERED.** Census
GEOID via Gazetteer and TIGER/Line, with GNIS feature ids, plus GeoNames for international
generality. Fixed-width storage with an explicit level is mandatory because 7-character GEOIDs are
ambiguous (SIG-IDENT-005).

**Q12 — How should private organizations in vendor networks be disambiguated?** **ANSWERED-DESIGN.**
SIG surrogate + `identity_basis` + tiered address keys, with K3/K4 blocking-only; and the
publication rule that an entity failing the publicity tests is represented publicly **as an
aggregate count**, with network edges to suppressed nodes still publishable in aggregate (§14.4).

## Licensing

**Q13 — Precisely how does ODbL apply to a graph joining OSM records to non-OSM entities?**
**ANSWERED.** In depth at §42.3 / R1-F1.12–F1.16. The Collective Database Guideline's fourth bullet
would permit adding `operator` — explicitly named as a *property* — by reference, **if** no OSM data
is used for that property within a regional cut. But the Horizontal Layers Guideline requires
sharing "additions or factual corrections" to OSM-layer data and specifically names
adding-by-comparison-with-OSM as a must-share case, which describes SIG's workflow. The guidelines
conflict for SIG's case; the conservative reading governs.

**Q14 — Can an OSM physical-assets table remain logically/licensably separate?** **ANSWERED — and
the answer is "not by separation alone."** The guideline states a join key **is** a reference and
that physical separation is **not** sufficient for independence. So Strategy A fails. SIG adopts
**Strategy B**: the asset layer is separate *and* ODbL; the SIG-original graph is CC-BY-4.0. Note
also that substantiality offers no escape — the threshold is ~100 features and repeated small
extractions count as one large one (F1.14).

**Q15 — Licences governing Atlas, HIBF, Eyes on Flock, ALPR Watch, Accountability Atlas?**
**ANSWERED — and the answer is negative for most of them**, which is itself the finding.

| Source | Position |
|---|---|
| Atlas | `CC-BY-4.0` **with a third-party-content caveat** (SC-09) — an adjudication between two workstreams that disagreed |
| Eyes on Flock | **CC BY-SA 4.0** (SC-18.3) |
| HIBF | **No licence at all** — no copyright line, no reuse grant anywhere on the domain |
| ALPR Accountability Atlas | **No licence at all** |
| ALPR Watch | **Mixed** — copyleft on some repositories, nothing on the bulk data tree |
| ALPR Abuse Library | **None, plus an affirmative refusal** — `ai-train=no`, AI-crawler disallows, and an EU DSM Article 4 reservation |

Four of six therefore register as `UNDETERMINED` or `refused`, and the export gate is **closed**
against them (SIG-LIC-004). This is the outcome OL-14.2-02 exists to prevent discovering after
launch, and it is why `redistributable` is a separately reviewed field rather than a function of the
licence string.

**Q16 — What source documents may be archived vs merely linked?** **ANSWERED-DESIGN.** Governed by
`custody_posture` (MIRROR / DERIVE / REFERENCE / LINK, §8.4) and enforced before fetch
(SIG-INGEST-014), with `capture_status` recording artifacts that are cited but unretrievable
(SIG-EPIS-005) and storage tiers governing exposure (§17.5).

## Temporal data

**Q17 — What snapshot cadence is justified for transparency portals?** **ANSWERED, and the answer
is set by the upstream rather than by SIG.** The aggregator's own recrawl advances its snapshot
field roughly **monthly**. SIG MUST key change detection on that field rather than on fetch time,
and MUST NOT poll faster than the upstream refreshes — polling faster adds load without adding
information (SIG-INGEST-030c).

Direct capture from the vendor remains unavailable (F2.1), and the fallback channels' cadences are
derived from predicate volatility (§28.3) rather than from habit:

| Channel | Justified cadence | Derivation |
|---|---|---|
| Partner feed, if obtained | Follow the partner's own capture rate; **add no independent load** | Duplicating a partner's crawl is both wasteful and rude |
| Contributor-mediated capture | Opportunistic, prioritized by staleness | Driven by the "sharing snapshot stale" detector (§33.2 #34) |
| Records-based configuration acquisition | **Annual baseline**, plus event-triggered | `configured_retention_days` is MODERATE (h = 9 mo); an annual request keeps it inside `C2` |
| Event-triggered re-request | On any of: a contract renewal, a policy change, a reported incident, or a lifecycle transition | These are the events that change configuration, so they are the correct trigger |

The general rule the outline was reaching for: **snapshot cadence should be a function of the
predicate's half-life, not of what is technically convenient.** Capturing a VOLATILE predicate
annually is nearly worthless; capturing an IMMUTABLE one repeatedly is waste.

**Q18 — How should deleted portals and inactive organizations be preserved?** **ANSWERED-DESIGN.**
Disappearance is a **dated event on the artifact**, never a deletion; the last capture is retained;
a research task is generated; the state is distinctly rendered (§17.6, SIG-INGEST-009).

**Q19 — How to represent OSM edit history without replicating the whole history database?**
**ANSWERED — VERIFIED** (SC-17.2). Store element id **and version** on every asset claim
(REQ-R1-01, §23.2); fetch per-element history on demand for the small set of elements under active
reconciliation; never mirror the history planet.

The endpoint `/api/0.6/<type>/<id>/history.json` was **tested live** and returns the complete
version history with per-version tag sets, `changeset`, `user`, and `timestamp`.

The design also turned out to have a **mandatory** use rather than an optional one: `first_observed`
cannot be read from an element's creation date, because OSM elements are routinely *repurposed*.
Four measured ALPR nodes were created in 2009 as freeway imports and became surveillance nodes in
2024 — a fifteen-year gap that, if taken as the device date, would silently corrupt the temporal
layer (SIG-INGEST-045a).

## Graph storage

**Q20 — Relational/PostGIS, property graph, RDF, or hybrid?** **ANSWERED.** **Hybrid with a
relational core**: PostgreSQL ≥18 + PostGIS ≥3.6.3 canonical, everything else a rebuildable
projection (§15.1). Scored decisively against four alternatives; the disqualifications are concrete
(an archived repository, GPL/BUSL licensing on the features SIG needs, no geospatial story), not
aesthetic.

**Q21 — Which model best supports claim-level provenance and bitemporal history?** **ANSWERED, with
a qualification that matters.** RDF-star/Wikibase model provenance best; XTDB models bitemporality
best; **neither carries SIG's geospatial, access-control, and constraint requirements.** Postgres
carries all of them and can *emit* the other two as projections; the reverse is not true (§15.3).

**Q22 — How should high-volume audit aggregates remain separate?** **ANSWERED.** Hive-partitioned
Parquet queried by DuckDB, joined to the graph **by UUID and period only, never by name**, with
partitions registered as evidence artifacts (§18). The boundary is also a privacy boundary: no raw
audit rows exist on either side.

## Ingestion

**Q23 — Which connectors can be incremental?** **ANSWERED.** Per-class matrix at §21.3, with an
explicit strategy per mode and a `manual_acquisition` class for dependencies that cannot be
automated (SIG-INGEST-008).

**Q24 — Which sources require scraping?** **ANSWERED — and reframed.** Scraping is four separate
legal tracks, not one technical question (§26). Concretely: the highest-value scraping target is
**not lawfully scrapable** (F2.1), while several sources the outline treats as scraping targets
turn out to have **real APIs** — Legistar, PrimeGov, CivicClerk, NextRequest, DocumentCloud,
USAspending — all successfully called (§22.2).

**Q25 — How should source snapshots be content-addressed?** **ANSWERED.** Multihash (base32) so the
algorithm is part of the value; SHA-2 for interop with BLAKE3 in fixity; OCFL 1.1 storage root on
object storage with versioning and **governance-mode** Object Lock; WACZ for web captures so pages
stay **re-parseable**, not merely viewable (§17).

**Q26 — What parser architecture handles PDF/HTML/CSV/XLSX/ZIP/JSON/meeting systems/contracts?**
**ANSWERED.** The seven-layer cheapest-sufficient ladder with recorded method, mandatory locators,
file classification before parsing, and committed fixtures plus a live canary (§24).

## Entity resolution

**Q27 — Which matches can be deterministic?** **ANSWERED.** Cascade tiers 0–3: shared canonical
identifier; established crosswalk; normalized-name+state+class with a data-generated collision
exclusion list; government-domain match with a shared-hosting denylist; exact address key K1 +
normalized name (§14.6).

**Q28 — Where should fuzzy/model-assisted matching generate review queues rather than writes?**
**ANSWERED.** Tiers 4 and 5, always. LLMs may generate review rationales but **may not write to the
graph**, with model and prompt version logged against each human decision (SIG-IDENT-026,
SIG-LLM-002).

**Q29 — How should aliases and mergers be represented?** **ANSWERED.** Typed aliases with their own
validity intervals; reified `OrganizationRelation` records with valid and transaction time over a
seven-value vocabulary; and the rule that **a rename is not a succession** (SIG-IDENT-016/017), with
five worked cases as required fixtures.

## Safety and privacy

**Q30 — What publication policy governs plates, names, private-residence detections, sensitive
content?** **ANSWERED.** §43: categorical exclusions (plates never; **home addresses categorically,
not by balancing**); the five-class coordinate matrix; the five-prong officer test requiring two
concurring reviewers with no-publish as the default on disagreement; and the RF rule that a
residential-parcel candidate is never published at any precision.

**Q31 — Which raw records should be stored privately and represented publicly only by metadata?**
**ANSWERED.** The `sealed` storage tier, which **still carries a public metadata representation** —
existence, source, date, digest, and the claims it supports — so SIG can say "we hold this contract,
here is its hash, here is what it establishes" without publishing it (SIG-EVID-010).

**Q32 — How should takedown/correction requests work?** **ANSWERED.** §45: one-click intake from any
claim; categories with privacy-harm prioritized; five permitted outcomes **including published
refusal**; corrections as new assertions preserving prior belief; and **suppression as a primitive
distinct from deletion** — the omission in the outline's append-only model that would otherwise
force a destructive delete on the first valid privacy demand (SIG-GOV-007).

## Collaboration

**Q33 — How can corrections flow upstream to OSM/DeFlock?** **ANSWERED, and now verified against
both governing documents** (SC-12, SC-14). Risk R-14 is closed.

**No direct automated writes.** Contribution goes through a human-mediated suggestion workflow in
which SIG supplies evidence and a mapper decides, in their own account (SIG-CONTRIB-014/015).

The reason this is the right architecture is sharper than "caution". The **Automated Edits Code of
Conduct** governs edits made *"without review individually by the person controlling the edits"* —
so a workflow where a human reviews each change individually is **outside its scope entirely**,
rather than merely compliant with it. Operator attribution is covered by none of the Code's
exceptions (those are typos, vandalism reversion, correcting one's own work, and reverting
unapproved automated edits), and as external data it would additionally engage the import
guidelines — so a SIG bot account would face the full documentation, consultation, opt-out and
per-scope-change re-approval burden, with *"ignoring this policy will be treated as vandalism"* as
the enforcement posture.

The **Organised Editing Guidelines** *do* apply, because SIG coordinating volunteers is *"a sizeable,
substantial, coordinated editing initiative"*. SIG must publish an activity page disclosing its
organisation, contact, goal, timeframe, tools, data sources **and their usage conditions**, and
**a unique changeset hashtag** (SIG-CONTRIB-016d).

Two consequences worth stating in the answer itself:

- **The hashtag is an asset, not a cost.** It makes SIG's upstream contribution stream publicly
  auditable by third parties, which is what turns the §7 leverage metric from an assertion into a
  measurement SIG does not control (SIG-CONTRIB-016e).
- **The backlog cannot be cleared mechanically.** Throughput is bounded by mapper attention, so the
  design objective is minimizing human cost per resolution, not maximizing write volume
  (SIG-CONTRIB-017a). This is a roadmap constraint, not a footnote.

**Q34 — Could Atlas consume deployment corrections?** **PARTIAL.** A contact address is published
and EFF has stated its scope boundary (SC-10), but no correction-submission channel was confirmed.
Stage 0 item.

**Q35 — Can research tasks link directly to HIBF/MuckRock workflows?** **PARTIAL.** HIBF documents a
submission path and publishes report surfaces SIG should **link to rather than recompute**
(REQ-R2-10). MuckRock's API requires auth on all data endpoints, so programmatic filing is
unconfirmed. The task→`RecordsRequest` model is specified either way (SIG-CONTRIB-019).

**Q36 — Could local groups claim geographic research queues?** **ANSWERED-DESIGN.** Yes — claiming
grants visibility, notification, and queue priority, but **never exclusivity**, and claims expire.
The expiry is the safeguard against coordination hardening into gatekeeping (§33.4).

**Q37 — What stable IDs would allow other projects to link back?** **ANSWERED.**
`sig:<type>:<uuidv7>`, dereferenceable with content negotiation; **stability across cluster
splits/merges via explicit dated merge/split events, redirects, and tombstones**; and a published
crosswalk export — the single highest-leverage artifact SIG can give the ecosystem, because it lets
others reproduce national analyses without rebuilding entity resolution (§14.8).

---

# Appendix C — Consolidated DDL for the domain entities

§16 gives the DDL for the **claim spine** — the layer whose exact shape carries the epistemic
invariants. This appendix gives the domain-entity DDL that §16 refers to, so that Phase 2 has no
undefined foreign-key targets.

**SIG-STORE-045 (MUST).** This DDL is the **specification**; the shipped DDL is **generated from the
LinkML ontology** (§20.1). Where the two differ, the generated artifact is authoritative and the
divergence is a Phase-1 defect to be reconciled — not a licence to hand-edit the database.

**SIG-STORE-046 (MUST).** Recall SIG-ONTO-003: these tables carry **identity, typing, and
bookkeeping only**. Every *attribute* is a claim. Where a column below looks like an attribute, it is
either a cached resolver output (marked) or a governance field that cannot itself be a claim.

## C.1 Supporting vocabularies and registries

```sql
CREATE TABLE vocab_entity_type          (entity_type text PRIMARY KEY, definition text NOT NULL);
CREATE TABLE vocab_object_type          (object_type text PRIMARY KEY, definition text NOT NULL);
CREATE TABLE vocab_evidence_role        (role text PRIMARY KEY, definition text NOT NULL);
CREATE TABLE vocab_confidence           (confidence text PRIMARY KEY, definition text NOT NULL);
CREATE TABLE vocab_rationale            (rationale_code text PRIMARY KEY, template text NOT NULL);
CREATE TABLE vocab_resolution_strategy  (strategy_id text PRIMARY KEY, definition text NOT NULL);
CREATE TABLE vocab_normalization        (normalization_id text PRIMARY KEY, definition text NOT NULL);
CREATE TABLE vocab_source_reliability   (code text PRIMARY KEY, definition text NOT NULL);  -- R1..R6
CREATE TABLE vocab_claim_directness     (code text PRIMARY KEY, definition text NOT NULL);  -- D1..D6
CREATE TABLE vocab_artifact_integrity   (code text PRIMARY KEY, definition text NOT NULL);  -- I1..I3

-- The predicate registry. SIG-ONTO-066: a predicate without all of these is unresolvable.
CREATE TABLE vocab_predicate (
  predicate_id        text PRIMARY KEY,
  vocab_version       text NOT NULL,
  value_datatype      text NOT NULL,
  object_type         text NOT NULL REFERENCES vocab_object_type(object_type),
  cardinality         text NOT NULL DEFAULT 'single',
  definition          text NOT NULL,
  skos_concept_iri    text,
  volatility_class    text NOT NULL,            -- IMMUTABLE|GLACIAL|SLOW|MODERATE|FAST|VOLATILE
  half_life_days      integer,                  -- NULL only when IMMUTABLE
  is_windowed         boolean NOT NULL DEFAULT false,   -- SIG-RECON-011
  resolution_strategy text NOT NULL REFERENCES vocab_resolution_strategy(strategy_id),
  max_relative_spread numeric,                  -- numeric predicates: the U4 tolerance
  deprecated_at       timestamptz,
  superseded_by       text REFERENCES vocab_predicate(predicate_id),
  CHECK (volatility_class = 'IMMUTABLE' OR half_life_days IS NOT NULL)
);

-- The (genre x predicate) directness matrix. SIG-EPIS-017: published, versioned, not illustrative.
CREATE TABLE directness_matrix (
  artifact_type  text NOT NULL,
  predicate_id   text NOT NULL REFERENCES vocab_predicate(predicate_id),
  directness     text NOT NULL REFERENCES vocab_claim_directness(code),
  ruleset_version text NOT NULL,
  note           text,
  PRIMARY KEY (artifact_type, predicate_id, ruleset_version)
);
```

## C.2 Rights, sources, and lineage

```sql
CREATE TABLE rights_record (
  rights_id            uuid PRIMARY KEY DEFAULT uuidv7(),
  spdx_expression      text NOT NULL,            -- LicenseRef-SIG-<slug> for bespoke terms
  attribution_text     text,
  redistributable      text NOT NULL,            -- yes|no|review_required|UNDETERMINED
  derivative_permitted text NOT NULL,
  terms_url            text,
  terms_capture_id     uuid,                     -- the ARCHIVED terms (SIG-LIC-002); FK added later
  reviewed_by          text,
  reviewed_at          timestamptz,
  retrieval_date       date NOT NULL,
  CHECK (redistributable IN ('yes','no','review_required','UNDETERMINED'))
);

CREATE TABLE source_registry (
  source_id            text PRIMARY KEY,
  name                 text NOT NULL,
  source_kind          text NOT NULL,
  homepage_url         text,
  operator_org_id      uuid REFERENCES entity(entity_id),
  default_reliability  text NOT NULL REFERENCES vocab_source_reliability(code),
  reliability_provisional boolean NOT NULL DEFAULT false,
  reliability_justification text NOT NULL,       -- SIG-EPIS-014: written, reviewed on a schedule
  rights_id            uuid NOT NULL REFERENCES rights_record(rights_id),
  custody_posture      text NOT NULL,            -- MIRROR|DERIVE|REFERENCE|LINK
  compact_status       text NOT NULL,            -- SIG-INGEST-027, incl. 'no_response'
  ingestion_permitted  boolean NOT NULL DEFAULT false,   -- HARD GATE, default deny
  robots_policy        text NOT NULL,
  crawl_budget         jsonb,
  contact_channel      text,
  last_verified_at     timestamptz,
  CHECK (custody_posture IN ('MIRROR','DERIVE','REFERENCE','LINK'))
);

CREATE TABLE ingest_run (
  run_id             uuid PRIMARY KEY DEFAULT uuidv7(),
  connector_name     text NOT NULL,
  connector_version  text NOT NULL,
  code_commit        text NOT NULL,
  ruleset_version    text NOT NULL,
  vocab_version      text NOT NULL,
  parameters         jsonb NOT NULL,
  environment        jsonb NOT NULL,             -- must record LC_ALL=C, TZ=UTC (SIG-EVID-018)
  input_digests      text[] NOT NULL,
  started_at         timestamptz NOT NULL DEFAULT clock_timestamp(),
  finished_at        timestamptz,
  status             text NOT NULL DEFAULT 'running',
  is_replay          boolean NOT NULL DEFAULT false,
  shadow_mode        boolean NOT NULL DEFAULT false   -- SIG-INGEST-019
);
```

## C.3 Evidence

```sql
CREATE TABLE evidence_artifact (
  artifact_id        uuid PRIMARY KEY DEFAULT uuidv7(),
  source_id          text NOT NULL REFERENCES source_registry(source_id),
  url                text,
  stable_locator     text NOT NULL,
  artifact_type      text NOT NULL,
  title              text,
  publisher_org_id   uuid REFERENCES entity(entity_id),
  published_at_edtf  text,                       -- T3, EDTF (often imprecise)
  document_date_edtf text,
  acquisition_method text NOT NULL,
  records_request_id uuid,
  page_count         integer,
  primary_or_secondary text NOT NULL,
  default_reliability  text REFERENCES vocab_source_reliability(code),
  rights_id          uuid NOT NULL REFERENCES rights_record(rights_id),
  sensitivity_tier   smallint NOT NULL DEFAULT 0,
  capture_status     text NOT NULL,              -- captured|access_restricted|paywalled|
                                                 -- link_rotted|not_attempted|refused_by_policy
  disappeared_observed_at timestamptz,           -- §17.6: an EVENT, never a delete
  supersedes_artifact_id  uuid REFERENCES evidence_artifact(artifact_id),
  UNIQUE (source_id, stable_locator)
);

CREATE TABLE evidence_capture (
  capture_id         uuid PRIMARY KEY DEFAULT uuidv7(),
  artifact_id        uuid NOT NULL REFERENCES evidence_artifact(artifact_id),
  content_digest     text NOT NULL,              -- multihash, base32 (SIG-EVID-002)
  digest_blake3      text,
  byte_size          bigint NOT NULL,
  media_type         text NOT NULL,
  retrieved_at       timestamptz NOT NULL,       -- T4
  retrieved_by_run_id uuid NOT NULL REFERENCES ingest_run(run_id),
  http_status        integer,
  ocfl_object_id     text NOT NULL,
  ocfl_version       text NOT NULL,
  storage_tier       text NOT NULL DEFAULT 'public',   -- public|restricted|sealed
  capture_method     text NOT NULL,
  capture_tool_version text NOT NULL,
  request_fingerprint jsonb,
  redaction_applied  boolean NOT NULL DEFAULT false,
  redaction_method   text,
  parent_capture_id  uuid REFERENCES evidence_capture(capture_id),   -- redacted derivative
  UNIQUE (content_digest, artifact_id),
  CHECK (storage_tier IN ('public','restricted','sealed')),
  CHECK (NOT redaction_applied OR redaction_method IS NOT NULL)
);
ALTER TABLE rights_record
  ADD CONSTRAINT rights_terms_capture_fk
  FOREIGN KEY (terms_capture_id) REFERENCES evidence_capture(capture_id);

CREATE TABLE extraction (
  extraction_id      uuid PRIMARY KEY DEFAULT uuidv7(),
  capture_id         uuid NOT NULL REFERENCES evidence_capture(capture_id),
  method             text NOT NULL,
  extractor_name     text NOT NULL,
  extractor_version  text NOT NULL,
  normalizer_version text NOT NULL,
  model_id           text,                       -- REQUIRED when method='llm_assisted'
  prompt_version     text,
  parameters         jsonb NOT NULL,
  extracted_at       timestamptz NOT NULL DEFAULT clock_timestamp(),
  run_id             uuid NOT NULL REFERENCES ingest_run(run_id),
  review_status      text NOT NULL DEFAULT 'unreviewed',
  superseded_by_extraction_id uuid REFERENCES extraction(extraction_id),
  CHECK (method <> 'llm_assisted' OR (model_id IS NOT NULL AND prompt_version IS NOT NULL))
);
```

## C.4 Domain entities

All are **identity-only** projections over `entity`. Typed sub-tables exist to carry
foreign-key-able identity and cached resolver output, never facts.

```sql
CREATE TABLE jurisdiction (
  entity_id      uuid PRIMARY KEY REFERENCES entity(entity_id),
  jurisdiction_type text NOT NULL,
  boundary       geometry(MultiPolygon, 4326),   -- cached from the resolved boundary claim
  boundary_valid tstzrange,                      -- SIG-ONTO-011: boundaries are temporal
  boundary_source_claim uuid REFERENCES claim(claim_id),
  level          text NOT NULL                   -- SIG-IDENT-005: GEOIDs are ambiguous without it
);

CREATE TABLE organization (
  entity_id      uuid PRIMARY KEY REFERENCES entity(entity_id),
  organization_type text NOT NULL,               -- namespaced: us.le.municipal_police, fr.* ...
  status         text NOT NULL DEFAULT 'active', -- active|inactive|withdrawn|suppressed
  identity_basis jsonb,                          -- SIG-IDENT-012, immutable for surrogates
  cached_canonical_name text,                    -- CACHED resolver output; never written directly
  publication_review_required boolean NOT NULL DEFAULT false   -- SIG-ONTO-013
);

CREATE TABLE entity_identifier (
  entity_id      uuid NOT NULL REFERENCES entity(entity_id),
  scheme         text NOT NULL,                  -- us.fbi.ori | us.census.geoid | wikidata.qid ...
  value          text NOT NULL,
  asserted_by_claim uuid REFERENCES claim(claim_id),   -- SIG-STORE-043: identifiers are claims
  PRIMARY KEY (entity_id, scheme, value)
);

CREATE TABLE organization_relation (           -- SIG-IDENT-016: reified, bitemporal
  relation_id    uuid PRIMARY KEY DEFAULT uuidv7(),
  from_entity    uuid NOT NULL REFERENCES entity(entity_id),
  to_entity      uuid NOT NULL REFERENCES entity(entity_id),
  relation_type  text NOT NULL,   -- same_as|succeeded_by|merged_into|split_into|absorbed|
                                  -- parent_of|acquired
  valid_period   tstzrange NOT NULL,
  sys_period     tstzrange NOT NULL DEFAULT tstzrange(clock_timestamp(), NULL, '[)'),
  evidence_claim uuid REFERENCES claim(claim_id)
);

CREATE TABLE person (                          -- SIG-ONTO-014..016: the most constrained table
  entity_id      uuid PRIMARY KEY REFERENCES entity(entity_id),
  public_interest_basis_claim uuid NOT NULL REFERENCES claim(claim_id),
  review_decision_id uuid NOT NULL,            -- the two-reviewer record (SIG-PUB-008)
  created_by     text NOT NULL
  -- NO address column exists, at any sensitivity tier, by construction (SIG-PUB-003).
);

CREATE TABLE product (
  entity_id      uuid PRIMARY KEY REFERENCES entity(entity_id),
  product_status text NOT NULL DEFAULT 'available'
);

CREATE TABLE technology (
  technology_id  text PRIMARY KEY,
  family_id      text NOT NULL,
  domain_id      text NOT NULL,
  definition     text NOT NULL,
  distinguishing_criterion text NOT NULL,       -- SIG-ONTO-056
  evidence_signature       text NOT NULL,
  salience       char(1) NOT NULL CHECK (salience IN ('L','M','H','C')),
  status         text NOT NULL DEFAULT 'active',
  superseded_by  text REFERENCES technology(technology_id),
  skos_concept_iri text
);

CREATE TABLE capability (
  capability_id  text PRIMARY KEY,              -- verb.object.scope (SIG-ONTO-023)
  verb           text NOT NULL,
  object         text NOT NULL,
  scope          text NOT NULL,
  capability_class text NOT NULL,
  is_negative    boolean NOT NULL DEFAULT false, -- governance capabilities (SIG-ONTO-025)
  definition     text NOT NULL
);

CREATE TABLE deployment (
  entity_id      uuid PRIMARY KEY REFERENCES entity(entity_id),
  -- The FOUR orthogonal lifecycle tracks (SIG-ONTO-061). Cached resolver outputs.
  procurement_state    text NOT NULL DEFAULT 'unknown',
  physical_state       text NOT NULL DEFAULT 'unknown',
  operational_state    text NOT NULL DEFAULT 'unknown',
  authorization_state  text NOT NULL DEFAULT 'unknown',
  litigation_hold      boolean NOT NULL DEFAULT false   -- a FLAG, not a state
);

CREATE TABLE physical_asset (
  entity_id      uuid PRIMARY KEY REFERENCES entity(entity_id),
  asset_technology text REFERENCES technology(technology_id),
  geometry       geometry(Geometry, 4326),      -- NULLABLE (SIG-GEO-004)
  operating_area geometry(MultiPolygon, 4326),  -- for mobile assets
  mobility       text NOT NULL DEFAULT 'unknown',
  sensitivity_class text NOT NULL DEFAULT 'C1', -- C1..C5 (SIG-PUB-004)
  confirmation_status text NOT NULL DEFAULT 'reported_unverified',
  osm_element_type text,                        -- node|way|relation (SIG-GEO-003)
  osm_element_id bigint,
  osm_version    integer,                       -- REQ-R1-01: id AND version
  first_observed timestamptz,
  last_observed  timestamptz,                   -- P12: 'active' is never inferred from existence
  CHECK (sensitivity_class IN ('C1','C2','C3','C4','C5'))
);

CREATE TABLE candidate_asset (                  -- SIG-ONTO-029: SEPARATE from physical_asset
  entity_id        uuid PRIMARY KEY REFERENCES entity(entity_id),
  detection_method text NOT NULL,
  location_estimate geometry(Point, 4326),
  estimate_radius_m numeric NOT NULL,           -- never a bare point
  identifier_prefix text,                       -- OUI only; never a full hardware address
  observation_count integer NOT NULL DEFAULT 1,
  promotion_status  text NOT NULL DEFAULT 'unreviewed',
  residential_parcel_flag boolean NOT NULL DEFAULT false   -- true => NEVER published
);

CREATE TABLE data_system    (entity_id uuid PRIMARY KEY REFERENCES entity(entity_id),
                             system_scope text NOT NULL DEFAULT 'unknown');
CREATE TABLE contract       (entity_id uuid PRIMARY KEY REFERENCES entity(entity_id),
                             acquisition_channel text NOT NULL DEFAULT 'unknown',
                             parent_cooperative_contract uuid REFERENCES entity(entity_id),
                             amends_contract uuid REFERENCES entity(entity_id));
CREATE TABLE funding_instrument (entity_id uuid PRIMARY KEY REFERENCES entity(entity_id),
                             instrument_type text NOT NULL,
                             federal_award_id text);
CREATE TABLE policy         (entity_id uuid PRIMARY KEY REFERENCES entity(entity_id),
                             policy_type text NOT NULL);
CREATE TABLE legal_instrument (entity_id uuid PRIMARY KEY REFERENCES entity(entity_id),
                             instrument_type text NOT NULL, citation text);
CREATE TABLE configuration_state (entity_id uuid PRIMARY KEY REFERENCES entity(entity_id),
                             deployment_id uuid NOT NULL REFERENCES entity(entity_id),
                             observed_via text NOT NULL);
CREATE TABLE accountability_event (entity_id uuid PRIMARY KEY REFERENCES entity(entity_id),
                             event_type text NOT NULL,
                             epistemic_status text NOT NULL);   -- REQUIRED (SIG-ONTO-038)
CREATE TABLE legal_proceeding (entity_id uuid PRIMARY KEY REFERENCES entity(entity_id),
                             docket_number text, posture text NOT NULL DEFAULT 'unknown');
CREATE TABLE records_request  (entity_id uuid PRIMARY KEY REFERENCES entity(entity_id),
                             response_status text NOT NULL DEFAULT 'draft',
                             platform text, external_id text);
```

## C.5 Relationships

```sql
CREATE TABLE relationship (
  relationship_id uuid PRIMARY KEY DEFAULT uuidv7(),
  from_entity    uuid NOT NULL REFERENCES entity(entity_id),
  to_entity      uuid NOT NULL REFERENCES entity(entity_id),
  edge_type      text NOT NULL,                 -- the CLOSED catalog of §12; no 'integrates_with'
  -- Access-edge attributes (§12.5)
  access_kind    text,                          -- configured_access|observed_use|declared_policy
  scope          text,
  direction      text NOT NULL,
  automaticity   text,
  -- Integration-edge attributes (§12.3)
  initiator      text,
  transport      text,
  granularity    text,
  data_comes_to_rest boolean,
  consent_gate   text,
  mechanism      text,
  terminable_by  text,
  termination_reason text,
  applies_to_cohort text DEFAULT 'all',         -- SIG-ONTO-046.2
  -- Universal (SIG-ONTO-041)
  asserted_by    uuid REFERENCES entity(entity_id),   -- perspective; enables asymmetry detection
  valid_period   tstzrange NOT NULL,
  valid_from_kind text NOT NULL DEFAULT 'unknown',
  valid_to_kind   text NOT NULL DEFAULT 'unknown',
  observed_at    timestamptz,
  sys_period     tstzrange NOT NULL DEFAULT tstzrange(clock_timestamp(), NULL, '[)'),
  evidence_claim uuid NOT NULL REFERENCES claim(claim_id),   -- no unevidenced edges
  CHECK (edge_type <> 'integrates_with')        -- SIG-ONTO-045, enforced
);
CREATE INDEX ON relationship (from_entity, edge_type);
CREATE INDEX ON relationship (to_entity, edge_type);
CREATE INDEX ON relationship USING gist (valid_period);

CREATE TABLE entity_role (                      -- the FOURTEEN roles of §12.4
  entity_id      uuid NOT NULL REFERENCES entity(entity_id),   -- the asset/deployment/system
  actor_id       uuid NOT NULL REFERENCES entity(entity_id),   -- the organization
  role           text NOT NULL,
  valid_period   tstzrange NOT NULL,
  evidence_claim uuid NOT NULL REFERENCES claim(claim_id),
  PRIMARY KEY (entity_id, actor_id, role, valid_period)
);
```

## C.6 Contradiction, coverage, tasks, inference

```sql
CREATE TABLE contradiction (
  contradiction_id uuid PRIMARY KEY DEFAULT uuidv7(),
  subject_id     uuid NOT NULL REFERENCES entity(entity_id),
  predicate_id   text NOT NULL REFERENCES vocab_predicate(predicate_id),
  contradiction_type text NOT NULL,
  claim_ids      uuid[] NOT NULL,
  severity       text NOT NULL DEFAULT 'informational',  -- informational|notable|blocking
  status         text NOT NULL DEFAULT 'open',
  resolution_note text, resolved_by text, resolved_at timestamptz,
  research_task_ids uuid[]
);

CREATE TABLE coverage_record (                  -- makes NEGATIVE claims queryable (§32.1)
  coverage_id    uuid PRIMARY KEY DEFAULT uuidv7(),
  subject_id     uuid REFERENCES entity(entity_id),
  subject_class  text,
  jurisdiction_id uuid REFERENCES entity(entity_id),
  predicate_id   text REFERENCES vocab_predicate(predicate_id),
  absence_kind   text NOT NULL,   -- not_researched|searched_not_found|
                                  -- evidence_of_absence|not_applicable
  sources_searched text[],        -- REQUIRED for searched_not_found (SIG-METRIC-002)
  searched_at    timestamptz, searched_by text, search_method text,
  CHECK (absence_kind <> 'searched_not_found' OR sources_searched IS NOT NULL)
);

CREATE TABLE research_task (
  task_id        uuid PRIMARY KEY DEFAULT uuidv7(),
  task_type      text NOT NULL,
  subject_id     uuid REFERENCES entity(entity_id),
  jurisdiction_id uuid REFERENCES entity(entity_id),
  priority       numeric NOT NULL,
  status         text NOT NULL DEFAULT 'generated',
  disposition    text,                          -- the §33.4 vocabulary
  claimed_by     text, claimed_at timestamptz, claim_expires_at timestamptz,
  closing_condition text NOT NULL,              -- SIG-TASK-002: testable, or no registration
  detector_version text NOT NULL,
  generated_at   timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (task_type, subject_id)                -- duplicate suppression (SIG-TASK-007)
);

-- L4. A SEPARATE SCHEMA, so an inference can never be mistaken for an observation (§8.1).
CREATE SCHEMA inference;
CREATE TABLE inference.derived_fact (
  derived_id     uuid PRIMARY KEY DEFAULT uuidv7(),
  subject_id     uuid NOT NULL,
  predicate_id   text NOT NULL,
  value_json     jsonb NOT NULL,
  derivation_rule text NOT NULL,
  rule_version   text NOT NULL,
  input_claim_ids uuid[] NOT NULL,
  confidence     text NOT NULL,
  derived_at     timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE inference.derived_geometry (       -- SIG-GEO-006
  derived_id     uuid PRIMARY KEY DEFAULT uuidv7(),
  asset_id       uuid NOT NULL REFERENCES entity(entity_id),
  geometry       geometry(Geometry, 4326) NOT NULL,
  geometry_kind  text NOT NULL,                 -- fov_cone|coverage_estimate|road_snap
  model_version  text NOT NULL,
  assumptions    jsonb NOT NULL,
  input_claim_ids uuid[] NOT NULL,
  derived_at     timestamptz NOT NULL DEFAULT clock_timestamp()
);
```

## C.7 What is deliberately absent

**SIG-STORE-047 (MUST).** The following MUST NOT exist in any schema version, and a schema test MUST
assert their absence rather than relying on review:

| Absent | Rule |
|---|---|
| Any column capable of holding a licence plate | SIG-STORE-026, non-goal N1/N2 |
| Any per-search, per-sighting, or per-trip table | §18.1 |
| Any address column on `person` | SIG-PUB-003 — categorical |
| Any attribute column on an entity table duplicating a registered predicate | SIG-STORE-009 |
| An `integrates_with` edge value | SIG-ONTO-045, enforced by CHECK |
| A stored `currency` column on `claim` | SIG-EPIS-020 — it is derived at query time |

---

# Appendix D — Worked example: the Example City dossier, fully traced

This appendix demonstrates that the specification can produce the outline's Appendix B object
(OL-B-01…OL-B-12), and — more importantly — shows how the machinery changes what that object says.

## D.1 The outline's object

The outline presents a dossier in which `contracted_quantity: 42`, `portal_reported_quantity: 38`,
and `osm_mapped_quantity: 31`, with a research gap "reconcile 42 contract units vs 38 portal units."
It presents this as a contradiction awaiting resolution.

## D.2 What SIG actually produces

**These are not three answers to one question. They are three answers to three questions, plus one
genuine finding.**

| Predicate | Value | Source | R · D · I · C | W | Resolution |
|---|---|---|---|---|---|
| `contracted_device_count` | **42** | Executed contract, signed 2025-04-03 | R1 · D1 · I1 · C1 (IMMUTABLE) | **W4** | RESOLVED · CONFIRMED · UNCONTESTED · CURRENT |
| `active_device_count` | **38** | Portal capture 2026-07-15 | R2 · D1 · I1 · C1 | **W3** | RESOLVED · STRONGLY_SUPPORTED · MINOR_DISAGREEMENT · CURRENT |
| ↳ *same contract, for this predicate* | *42* | Executed contract | R1 · **D5** · I1 · C3 | **W1** | Dissenting, retained, not resolving |
| `mapped_device_count` | **31** | OSM, 2026-08-20 | R5 · D3 · I1 · C1 | W2 | RESOLVED — **lower bound only** |

The contract does not "lose" to the portal. It **wins its own predicate at W4** and is merely weak
evidence (D5, capped at W1) for a different predicate — current activity — that it was never
evidence for.

**The rationale SIG emits, quotable verbatim:**

> "38 active devices, as reported by the agency's transparency portal captured 2026-07-15. The
> portal is the most direct available source for currently active devices. The executed contract's
> figure of 42 is recorded separately as the contracted quantity; it is not evidence of the active
> count. 31 devices are independently mapped, which is a lower bound on the physical population."

**The genuine findings**, which become research tasks:

- `unresolved_delta(contracted=42, active=38) = 4` → task #1: were four never installed, or removed?
- `gap(active=38, mapped=31) ≥ 7` → task #2: locate and map at least seven devices.

## D.3 Where the outline's dossier understates the situation

| Outline field | SIG's rendering | Why |
|---|---|---|
| `status: active` | Four tracks: `procurement=contracted`, `physical=installed`, `operational=active`, `authorization=unknown` | §13.4 — one enum cannot carry this |
| `retention: 30 days` | `policy_written_retention_days` vs `configured_retention_days` vs `vendor_default_retention_days`, each with its own evidence | §29.5, P10 |
| `sharing.outgoing_configured: 147` | 147 **configured-access** edges as observed 2026-07-14 — never "currently shares with 147" | SIG-TIME-005, §12.2 |
| `national_search_observed: true` | Split: `configured_access` (national lookup enabled) vs `observed_use` (a national search occurred) | §12.2 |
| `usage.searches_last_30d: 412` | A **windowed** predicate with explicit bounds, exempt from currency decay for its window, and never rendered as a current rate | SIG-RECON-011 |
| `policies.immigration_enforcement.configuration_evidence: unknown` | Rendered as `not_researched` vs `searched_not_found` — with sources searched | §9.5, SIG-UI-012 |
| `physical_assets.unknown_operator_near_jurisdiction: 4` | Candidate attributions at L4, labelled `probable`, never written to the asset | §29.2, §30.4 |

## D.3a The second worked object: a local research-gap report

The outline's other worked example (OL-3-06) is a *research-gap* object for a jurisdiction, and it
is what a local group receives. It is produced by the detectors of §33.2, not hand-assembled:

| Outline gap statement | Producing detector | Disposition available |
|---|---|---|
| "Contract indicates 78 cameras" | — (a resolved `contracted_device_count`, W4) | — |
| "OSM currently has 61 probable ALPR devices" | — (a resolved `mapped_device_count`, lower bound) | — |
| "Portal reports 75" | — (a resolved `active_device_count`) | — |
| **"14 OSM devices have unknown operator"** | #5 orphaned device | `resolved_evidence_found` / `resolved_no_evidence_exists` |
| **"Latest contract amendment is missing"** | **#33 contract amendment chain incomplete** | `resolved_evidence_found` / `blocked_fee` / `blocked_access_denied` |
| **"Sharing snapshot is 94 days old"** | **#34 sharing snapshot stale** — 94 days exceeds the FAST 4-month half-life boundary at `C2`→`C3` | `resolved_evidence_found` |
| (implied) 75 reported vs 61 mapped | #1 missing physical devices | `resolved_evidence_found` |
| (implied) 78 contracted vs 75 active | Camera-count reconciliation delta (§29.1) | — |

Two things this demonstrates that the outline's version does not:

- **Every gap is a typed task with a defined closing condition and a disposition vocabulary**, so a
  local group can record "we searched and the record does not exist" and have that become a
  `CoverageRecord` rather than leaving the task open forever (§33.4, SIG-TASK-009).
- **The three counts are not in conflict.** 78 contracted, 75 active, 61 mapped are three
  predicates. The findings are the *deltas* — 3 unexplained between contracted and active, and at
  least 14 between active and mapped — not a disagreement to be adjudicated.

## D.4 The provenance chain for one fact

For "38 active devices", every link is traversable in both directions:

```
Source            transparency portal for this agency  [rights: UNDETERMINED → not redistributable]
 └─ Artifact      portal page, stable_locator = <slug>, capture_status = captured
     └─ Capture   sha2-256 multihash …, retrieved 2026-07-15T14:03Z, WACZ + screenshot + HTML
         └─ Extraction   html_selector v2.3.1, run_id …, review_status = sampled_ok
             └─ Claim    active_device_count = 38
                         raw_value = "38", locator = {selector: "...", text_span: [412,414]}
                         observed_at = 2026-07-15, valid_*_kind = unknown/ongoing
                         R2 · D1 · I1 · C1 → W3
                 └─ Resolution   value 38, STRONGLY_SUPPORTED / MINOR_DISAGREEMENT / CURRENT
                                 ruleset v2026.3, resolver v1.4.0, decided_by auto
                     └─ Dossier  §1 row, with the ⊕⊕⊕◯ glyph and a ≠ marker
```

A journalist clicking the 38 reaches the capture, the highlighted span, the extraction method, the
competing claims, and the rule that fired. That is OL-24-18 discharged.

## D.5 Appendix C pathways

All three of the outline's illustrative pathways (OL-C-01…OL-C-03) are expressible, with edge types
sharper than the outline's prose:

**Pathway 1 — private camera to fusion center.**
`Business —owner→ Camera` · `Camera —enrolls_asset_into→ Integration Platform` ·
`Platform —federates_search_to→ RTCC` · `RTCC —operated_by→ Police Department` ·
`Department —participates_in→ Fusion Center`.
Note `enrolls_asset_into` rather than "streams_via": the object is a *device*, and whether a live
feed follows is a separate, evidenced fact with its own consent gate.

**Pathway 2 — roadside ALPR to federal access.**
`ALPR —operated_by→ Department` · `Department —hosts_data_for→ Vendor network` ·
`Vendor network —is_queryable_by→ {Neighboring PD, State Police, Federal organization}`, each edge
directional, scoped, dated, and separately evidenced — and each distinguishing configured access
from observed use.

**Pathway 3 — commercial data.**
`Department —subscribes_to→ Investigative platform` · `Platform —resells_data_from→ Aggregating
broker` · `Broker —resells_data_from→ Ad-tech source`. The chain has **six layers, not five**: the
aggregating broker and the productizing platform are routinely different companies, which the
outline's five-step diagram collapses.

**And the question the pathways exist to answer** (OL-C-04) — *what chain of institutions turns an
observation into searchable power?* — is the access-path closure of §30.2, with its hop limits,
non-composition rules, minimum-over-path confidence, and speculative labelling.

---

# Appendix E — Glossary

Terms are defined as SIG uses them. Where SIG's usage differs from common usage, the difference is
stated, because several of these differences are load-bearing.

| Term | Definition |
|---|---|
| **Agreement** | One of the three epistemic fields (§10.7): how much the admissible evidence disagrees. Independent of *support*. |
| **Artifact** | An addressable thing within a source whose *content may change* but whose identity does not (§10.2). A portal page is one artifact with many captures. |
| **Capability** | What an operator can *do*, expressed `verb.object.scope` (§11.6). Distinct from Technology (what kind of machine) and ConfigurationState (how it is tuned). |
| **Capture** | The immutable bytes SIG obtained at one instant, content-addressed. Never edited; a redaction is a new capture (§10.2). |
| **Claim** | An assertion with a subject, predicate, value, preserved raw value, temporal dimensions, evidence set, and epistemic axes (§10.3.5). The substance of the graph. |
| **Configured access** | The system is *set up* to permit something. Says nothing about whether anyone used it (§12.2). |
| **Contradiction** | A materialized entity recording a disagreement, with a lifecycle and a severity (§31). Resolution never deletes it. |
| **Coverage record** | A queryable record of *absence*, distinguishing "not researched" from "searched and found nothing" and naming the sources searched (§32.1). |
| **Currency (`C`)** | How stale a claim is *relative to its predicate's volatility* (§28.3). Derived at query time, never stored. |
| **Declared policy** | Someone said something is permitted or forbidden. Distinct from configuration and from use (§12.2). |
| **Derivative Database** | An ODbL term. A database built on OSM content such that share-alike attaches (§42.3). |
| **Directness (`D`)** | How directly *this artifact genre* supports *this predicate* (§10.5). `D6` means non-probative — excluded, not down-weighted. |
| **Dossier** | The per-jurisdiction public artifact; the project's primary deliverable (§39.2). |
| **EDTF** | Extended Date/Time Format. How SIG stores uncertain and open-ended dates without inventing precision (§16.7). |
| **Evidence set** | The artifacts bearing on a claim, each with a role — including `contradicts` (§10.3.6). A claim does not have "a source". |
| **Independence class** | A group of claims sharing an upstream origin. Corroboration is counted per class, never per claim (§10.8). |
| **Inference** | A derived fact at L4, in a separate namespace, labelled everywhere, recomputable and droppable (§30). |
| **Observation time (T2)** | When the *source* observed the fact. Never defaulted from publication or retrieval time (§9.2). |
| **Observed use** | Someone actually did something. Distinct from configured access (§12.2). |
| **Produced Work** | An ODbL term: an image, PDF, or printed map — not intended for data extraction. Vector tiles are *not* Produced Works (§42.3). |
| **Reliability (`R`)** | A property of the *publisher and its method*, assigned once per source with written justification (§10.4). Not re-judged per claim. |
| **Resolution** | A stored decision record — value, confidence fields, rationale, supporting and dissenting claims, ruleset version, author (§16.4). Not a view. |
| **Sensitivity class** | `C1`–`C5`, governing published coordinate precision, assessed at the *role* level (§43.3). |
| **Support** | One of the three epistemic fields: how strongly the *winning value* is evidenced. Independent of agreement (§10.7). |
| **Suppression** | Removing material from public surfaces while retaining it internally. A distinct primitive from deletion (§45.4). |
| **Transaction time (T5)** | When SIG recorded a belief, and when it stopped. Closed only when SIG corrects *itself*, never when the world changes (§9.2). |
| **UNRESOLVED** | A legitimate, publishable outcome — not an error and never hidden (§28.5). |
| **Valid time (T1)** | When a fact was true in the world. Never populated by inference at ingestion (§9.2). |
| **Weight (`W`)** | `W0`–`W4`, composed from `R`, `D`, `I`, `C` by a published ordinal table (§10.6). |
| **Windowed predicate** | A measurement *of* a period. It becomes history, not staleness, when the period passes (§28.3). |

# Appendix F — Architecture Decision Record index

**SIG-STORE-006** requires each decision below to be written as an ADR under `docs/adr/` in Phase 1,
using a consistent template: context, decision, status, consequences, alternatives considered, and —
mandatory per SIG-STORE-007 — a **revisit trigger**.

| ADR | Decision | Spec | Revisit trigger |
|---|---|---|---|
| ADR-001 | PostgreSQL 18 + PostGIS canonical; everything else a projection | §15.1 | A projection becomes the sole home of any fact; or a managed-Postgres dependency becomes unavailable |
| ADR-002 | Append-only claims; entity tables hold identity only | §16.1–16.3 | Write throughput becomes a demonstrated bottleneck |
| ADR-003 | Two interval time dimensions + one ordering scalar | §9.2 | A use case requires `AS OF` travel along observation time |
| ADR-004 | EDTF for uncertain dates | §16.7 | EDTF tooling becomes unmaintained |
| ADR-005 | Resolution as a stored decision record | §16.4 | Storage cost of resolutions exceeds a defined share of the database |
| ADR-006 | OCFL 1.1 evidence store, governance-mode Object Lock | §17.3 | A legal regime makes governance mode untenable |
| ADR-007 | LinkML as the single ontology source of truth | §20.1 | Generated artifacts diverge from hand-written needs in more than one target |
| ADR-008 | SKOS for published vocabularies | §20.2 | A downstream consumer standard displaces SKOS |
| ADR-009 | SPDX expressions + a build-time licence gate | §42.1, §42.4 | A key source's terms are inexpressible in SPDX |
| ADR-010 | DuckDB/Parquet analytics boundary; no raw audit rows | §18 | Interactive aggregate latency misses its budget |
| ADR-011 | **Strategy B ODbL posture: separate ODbL asset layer, CC-BY-4.0 graph** | §42.3 | OSMF guidance changes; or counsel advises differently on the §42.3 residuals |
| ADR-012 | Sensitivity tiers via RLS, applied at the view layer | §16.8, §19.4 | A tier transform is shown to be invertible from published aggregates |
| ADR-013 | Apache-2.0 code; CC-BY-4.0 data; CC0 ontology | §42.2 | Proprietary re-hosting causes demonstrated harm to the commons |
| ADR-014 | Dagster OSS orchestration, kept reversible | §21.8 | Its licence changes; or ops burden exceeds the cron alternative |
| ADR-015 | Static-first, zero-JS-default frontend | §40 | Interactive requirements make progressive enhancement untenable |
| ADR-016 | Splink 4 for probabilistic ER | §14.6 | Holdout precision cannot reach the auto-write threshold |
| ADR-017 | No direct automated OSM writes | §35.2 | The OSM automated-edits review (R-14) concludes otherwise |
| ADR-018 | Rule-based, non-learned resolution | §28.1 | A learned resolver demonstrates both better accuracy *and* per-decision explainability |

# Appendix G — Corrections and material extensions to the source outline

The outline instructs the downstream agent to "re-verify the ecosystem yourself" and to "contact
assumptions with evidence" (OL-24-01, OL-24-03). This appendix records what that produced. **Nothing
here removes an outline obligation**; every item either corrects a fact, sharpens a model, or adds
something the outline did not have.

## G.1 Factual corrections

| # | Outline says | Verified reality | Consequence |
|---|---|---|---|
| C-01 | ~~DeFlock is at `deflock.org`~~ | **WITHDRAWN — the outline was right.** An intermediate finding claimed `deflock.me` was canonical; it is not. `deflock.me` 301-redirects to `deflock.org` behind a Cloudflare challenge that fires first, so a compliant client sees only the 403 (G.4.2 #1, SC-19) | **Use `deflock.org`.** Registry carries both hosts and both observed behaviours |
| C-02 | ALPR Watch is a FOIA→SQL→Superset pipeline (OL-2C-AW-01) | It is now substantially an ALPR-avoidance routing and offline-data project built on DeFlock; **code is on GitLab, not GitHub**; the Superset dashboard persists as one component | Connector and collaboration targets change |
| C-03 | FlockReporter is the local-group directory (OL-3-02, OL-18-13) | **Did not respond** when tested | SIG maintains its own registry (SIG-TASK-014); risk R-12 |
| C-04 | Flock portals demand "snapshotting and temporal preservation" (OL-2B-FP-04) | **403 on every path including `robots.txt`** — a managed challenge. No lawful path *to the vendor* | **Superseded in part:** the layer is obtainable from a public CC BY-SA 4.0 aggregator API (SC-18), so Phase 11 is ungated. Direct vendor capture remains impossible, and the fallbacks stand |
| C-05 | MuckRock API (OL-Q07) | It is **api_v2**, not v1; **401 on every data endpoint**; 5-minute JWT; ~15 req/min | Connector design and expectations change |
| C-06 | A crowdsourced figure of 850,000+ private cameras across 324 communities (OL-4.1-04) | Independent enumeration found **321 communities**, and the 850k figure sums two incommensurable counters (registered + "integrated"), where "integrated" counts what an org can *see* through federation, not distinct cameras | The outline's own instruction to verify before treating as canonical, vindicated |
| C-07 | `Fusus integrates Flock ALPR` as a canonical example (OL-C-01, OL-4.1-02) | Axon **severed** API interoperability with Flock in 2025 | The outline's flagship integration example describes a terminated relationship; `applies_to_cohort` is required on edge termination |
| C-08 | ShotSpotter leak of "more than 25,000" sensors (OL-4.5-01) | The downloadable derivative holds **22,471** points | Do not repeat the press figure |
| C-09 | Ring/Neighbors partnerships as a category (OL-ES-16, OL-2D-AT-05) | The model is **two policy reversals stale**; and the Atlas *retired* the Ring category in 2024, deleting ~2,530 datapoints | **Absence of Ring data after 2024 means "category retired", not "program ended"** — SIG-ONTO-059 |
| C-10 | A circulating figure of ~336K ALPRs on OSM | Measured `surveillance:type=ALPR` = **144,312** | Not corroborated; unusable without a primary source |
| C-11 | Atlas licence unclear across research | **`CC-BY-4.0` with an explicit third-party-content caveat**, attributed to EFF + Reynolds School of Journalism | `redistributable` must be separately reviewed, not derived (SC-09) |
| C-12 | Web archiving as a general fallback (OL-2B-IND-01) | **`*.flocksafety.com` is excluded from the Wayback Machine** | There is no third-party archive fallback; SIG's archival role becomes ecosystem-critical |
| C-13 | Court records as an ingestion source (OL-2E) | Open endpoints are rate-limited to ~5/min, 50/hr, 125/day | Targeted lookup only; bulk court ingestion is void |
| C-14 | Data-quality tooling assumptions | Several widely-recommended tools have moved to source-available licences | Licence must be re-verified at adoption (SIG-ENG-018) |

## G.2 Model corrections

| # | Outline model | Correction | Section |
|---|---|---|---|
| M-01 | `Claim.source` — one source per claim (OL-8.16-02) | A claim has an **evidence set with roles**, including `contradicts` and `attests_absence` | §10.3.6 |
| M-02 | Two implied time dimensions (OL-6.3-02, OL-9.2-01) | **Five** dimensions across two layers; only two are `AS OF` axes; observation time is an ordering scalar | §9.2 |
| M-03 | No transaction time at all | Without it SIG **cannot reproduce its own past publications** or honour a citation of itself | §9.4, §16.2 |
| M-04 | `valid_to = NULL` (OL-6.3-02) | Ambiguous between "ongoing" and "unknown" — **opposite research tasks**. `valid_to_kind` is required | §9.3 |
| M-05 | Resolution as a computed view (OL-6.5-01) | A **stored decision record** with rationale, author, and an independently versioned ruleset | §16.4 |
| M-06 | Tier A–F as a reliability scale (OL-9.1) | It is a **genre** scale. A contract and a field observation are not equally reliable; they are reliable about *different things*. Four axes replace it | §10.4–10.6 |
| M-07 | Six flat confidence labels (OL-9.3-02) | Three of the six are on different dimensions; the enum cannot express "strongly supported but contested". Replaced by three orthogonal fields — a strict superset | §10.7 |
| M-08 | One lifecycle enum, 14 states (OL-6.7-01) | **Four orthogonal tracks**; "cancelled + still installed + unplugged" is three simultaneous states. All 14 retained, 10 added. **`replaced` is an edge, not a state** | §13.4 |
| M-09 | "Technology / capability" as one entity (OL-8.4) | **Three** entities: Technology (three-level, 101 terms), Capability (verb.object.scope), and a promoted ConfigurationState | §11.5–11.6, §11.15 |
| M-10 | Four ownership roles (OL-4.1-05) | **Fourteen** roles, with seven load-bearing separations — including that coordinate sensitivity must be assessed at the **role** level, because a rooftop sensor's coordinates endanger the *host* | §12.4 |
| M-11 | NULL for "unknown" | NULL cannot distinguish four epistemic states; `value_kind` (`value`/`somevalue`/`novalue`) plus `CoverageRecord` are required | §9.5, §32.1 |
| M-12 | No model of evidence decay | **Predicate volatility** with half-lives; and the `U5` rule, which is what stops SIG publishing a stale unchallenged number | §28.3, §28.5 |
| M-13 | Corroboration by counting sources | Sources copy each other. Corroboration counts **independence classes**, and SIG *declares* dependence rather than inferring it | §10.8 |
| M-14 | Append-only with no suppression (OL-19.3) | The first valid privacy demand would force a destructive delete. **Suppression is a distinct primitive** | §45.4 |
| M-15 | Public-interest balancing for all officer data (OL-13.2) | Correct for names; **wrong for home addresses**, which must be categorical | §43.2 |
| M-16 | Seven product surfaces (OL-15) | An eighth is required: a **public corrections log** | §39.8 |
| M-17 | Tasks that only say "go find X" (OL-12) | Without a **disposition vocabulary**, "searched, found nothing" is unrecordable and the queue can only grow | §33.4 |
| M-18 | Strategy A as a viable ODbL posture (OL-14.1) | Separation alone does not avoid share-alike: a join key **is** a reference, and physical separation is expressly insufficient | §42.3 |

## G.3 Material additions

| # | Addition | Why it matters |
|---|---|---|
| A-01 | **Cooperative purchasing vehicles** | A dominant acquisition channel that publishes full competitive records for free — while the agencies riding them generate **no local RFP** |
| A-02 | **Federal grant sub-award tracing** | Identifies deployments that appear in no local procurement record |
| A-03 | **Civic agenda platforms are real APIs** | Legistar, PrimeGov, CivicClerk, NextRequest all called successfully; **no municipality→platform directory exists and SIG should build one** |
| A-04 | **Municipal surveillance-ordinance inventories** | Statutory equipment inventories published on a legal cycle |
| A-05 | **Federal drone-authorization releases** | A regulator's dated records with native validity intervals — an unusually clean `authorization_state` source |
| A-06 | **The orphaned-device backlog, quantified** | Only **19.1%** of 144,312 mapped ALPRs carry an `operator` — ~116,800 devices. This is SIG's largest single body of addressable work and the clearest statement of its distinct value |
| A-07 | **Wikidata as a first-class crosswalk key** | `manufacturer:wikidata` on **83.4%** of mapped ALPRs — OSM has already done vendor entity resolution |
| A-08 | **`FundingInstrument` and third-party-funded surveillance** | BID/HOA/foundation purchases escape ordinances that regulate *agency* acquisition |
| A-09 | **`LegalInstrument`** | The outline lists laws among what must be represented but never models them |
| A-10 | **`CandidateAsset` as a separate entity** | If candidates share a table with assets, they eventually share a map |
| A-11 | **The `free_trial → active` path** | Capability acquired with no procurement paper trail — the most important edge in the state machine for discovery |
| A-12 | **Export/onward-disclosure capabilities** | Systematically absent from every public taxonomy, and where the harm actually lives |
| A-13 | **OSM already holds non-camera surveillance** | 3,250 gunshot detectors and 67 AFR nodes — the non-ALPR physical layer is free at Stage 1 |
| A-14 | **Shadow-mode replay** | A parser change that silently alters 40,000 claims must be seen before it lands |
| A-15 | **Archival succession for single-maintainer upstreams** | Several dependencies are one-person projects and the key vendor domains are unarchived; if they vanish, the record vanishes |
| A-16 | **The anti-misuse tension, addressed openly** | A project that hides from its hardest question is not credible on the easier ones |

## G.4 Research completeness

**Status as of 2026-08-20 (completion pass): all thirteen research workstreams are complete.**

An earlier version of this section recorded six open items caused by seven workstreams being
terminated mid-run by an account spend limit. The limit was lifted and the work was finished. The
record of what was outstanding, and how each was closed, is retained below — deleting it would erase
the evidence that the specification once rested on gaps.

| # | Was outstanding | Disposition |
|---|---|---|
| 1 | OSM Automated Edits Code of Conduct and Organised Editing Guidelines not read | **CLOSED.** Both read (SC-12, SC-14, R1-F1.27/28). The human-mediated design falls *outside* the Code's scope; the Guidelines apply and supply the changeset hashtag. Risk R-14 closed |
| 2 | Overpass and OSM element-history endpoints not tested | **CLOSED.** Both tested live (SC-17, R1-F1.17–F1.26). Q19 verified, and testing surfaced the element-repurposing dating trap (SIG-INGEST-045a) |
| 3 | Eyes on Flock internals, licence, collaboration posture unresolved | **CLOSED.** Public unauthenticated JSON API verified (SC-18, R2-F2.6); **CC BY-SA 4.0**; contact published. Phase 11 unblocked, risk R-02 closed |
| 4 | HIBF, ALPR Watch, Accountability Atlas, Abuse Library licences unresolved | **CLOSED, negatively for three of four** (R2-F2.16/18/19/20). Two state **no licence at all**; one is **mixed** (copyleft on some repos, nothing on the data tree); one adds an **affirmative refusal** with an EU DSM Art. 4 reservation. All now `UNDETERMINED` or `refused`, and the export gate is closed against them |
| 5 | DeFlock repository, export, and changeset signature undetermined | **CLOSED.** Canonical repos identified; the outline's cited repo belongs to a **different project**; **DeFlock has no data API** — there is no connector to build, the data is OSM; changeset signature is `created_by = "DeFlock <semver>"`, on ~75% of sampled ALPR edits |
| 6 | Seven workstreams terminated; R1/R2 reduced, R3 partial | **CLOSED.** All thirteen files now carry findings, open questions, and emitted requirements. R1 437→1,908 · R2 250→1,708 · R3 546→1,760 · R12 1,546→2,385 · R13 1,904→2,791. Cache total **26,818 lines, 501 findings, 667 requirements** |

### G.4.1 What the completion pass changed in the specification

The finished research did not merely confirm the draft. It produced eight corrections, four of
which changed requirements rather than confidence:

| Correction | Effect |
|---|---|
| The portal layer **is** lawfully obtainable | Phase 11 ungated; risk R-02 closed; the fallback chain retained because the API is a single dependency |
| The licence architecture is **N-compartment**, not two-way | A third share-alike regime (CC BY-SA 4.0) exists; a merged export would have been an invisible violation (SIG-LIC-004a) |
| **CC-BY-4.0 blocks upstream contribution** | OSM forbids importers claiming additional copyright; the contributed subset is dual-licensed **CC0** (SIG-LIC-007a) |
| **Capture–recapture is impossible here**, not merely caveated | `m₂` is undefined and the bias runs *downward*; prohibited, with one validation-only exception (SIG-METRIC-008) |
| A live **de-pseudonymisation join** exists in the ecosystem | Specific prohibition added; "already public" rejected as justification (SIG-PUB-003a–d) |
| Share-alike obligations **travel silently** | Provenance-aware rights gate; defaults to the stricter regime (SIG-LIC-009a) |
| Retention is reported as an **ordinal bucket** | Schema accepts duration *or* bucket; midpoints must not be fabricated (SIG-ONTO-035a) |
| OSM elements are **repurposed** | `first_observed` must come from the history walk, not the creation date (SIG-INGEST-045a) |

### G.4.2 Corrections to this document's own earlier findings

Recorded because a specification that hides its own error rate is not credible about anyone else's:

1. **`deflock.me` is not canonical.** An earlier spot-check (SC-04) read a `403` as evidence of
   canonicality and "corrected" the outline's `deflock.org` citation. **The outline was right.** The
   403 is a Cloudflare challenge firing ahead of a 301 to `.org` (SC-19). Withdrawn.
2. **"HIBF publishes no bulk export"** was inferred from three 404s; the export is one path level
   deeper (R2-F2.18). The conclusion sharpened rather than reversed — exports exist, a licence does
   not, and `robots.txt` forbids the path.
3. **The circulating "336K ALPRs" figure** has a probable origin: an unmaintained, unlicensed project
   whose headline claims it. Direct measurement gives 144,312 (SC-03, SIG-INGEST-048a).

### G.4.3 Residual open questions

These remain genuinely open and are carried in the risk register (§53) rather than presented as
settled:

1. Whether the aggregator's CC BY-SA grant is intended to cover the **API payload** as well as site
   content — material to §42.3's compartment boundary. A Stage-0 question for the operator.
2. Whether SIG's dual-licensing of the contributed subset (SIG-LIC-007a) satisfies the OSM community
   in practice, which is a consultation outcome and cannot be determined unilaterally.
3. The residual ODbL questions of §42.3 requiring counsel — unchanged, and correctly so.
4. Per-source licence positions for several newly discovered projects, two of which state none.

