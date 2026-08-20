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
