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
