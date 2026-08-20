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
