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
