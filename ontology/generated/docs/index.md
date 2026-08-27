# Surveillance Infrastructure Graph ontology

The canonical SIG ontology: entities (§11), relationships (§12), and the structural controlled vocabularies (§13). One LinkML source generates every downstream form (§20.1).

URI: https://ontology.sig-project.org/schema/sig

Name: sig



## Classes

| Class | Description |
| --- | --- |
| [AccessRelationship](AccessRelationship.md) | A sharing/access relationship; direction, scope, automaticity, and kind are a... |
| [AccountabilityEvent](AccountabilityEvent.md) | An accountability event; epistemic_status is REQUIRED and rendered everywhere... |
| [CandidateAsset](CandidateAsset.md) | [NEW] RF/heuristic leads that MUST live in a separate entity type and MUST NO... |
| [Capability](Capability.md) | A verb |
| [Claim](Claim.md) | An append-only assertion (subject, predicate, value,  |
| [ConfigurationState](ConfigurationState.md) | Promoted to a first-class, time-versioned, per-Deployment entity (§11 |
| [Contract](Contract.md) | A contract; acquisition_channel and parent_cooperative_contract are REQUIRED ... |
| [Contradiction](Contradiction.md) | A first-class, addressable contradiction object (§31) |
| [CoverageRecord](CoverageRecord.md) | [NEW] Makes negative claims queryable (§11 |
| [DataSystem](DataSystem.md) | Reference databases as infrastructure — representable even where SIG holds no... |
| [Deployment](Deployment.md) | The bridge between organizational adoption and individual devices; creatable ... |
| [Edge](Edge.md) | Universal edge requirements (§12 |
| [Entity](Entity.md) | Abstract base — every entity has identity (§3 |
| [EvidenceArtifact](EvidenceArtifact.md) | A specific artifact published by a Source (§10 |
| [EvidenceCapture](EvidenceCapture.md) | A content-addressed capture of an artifact at a time (§10 |
| [Extraction](Extraction.md) | A run that extracted claims from a capture (§10 |
| [FundingInstrument](FundingInstrument.md) | [NEW] Purchaser != operator != funder (§11 |
| [IntegrationEdge](IntegrationEdge.md) | A data-bearing integration edge (§12 |
| [Jurisdiction](Jurisdiction.md) | [NEW] A first-class jurisdiction with a self-referential hierarchy, a pluggab... |
| [LegalInstrument](LegalInstrument.md) | [NEW] Laws and regulations as a modelled entity (§11 |
| [LegalProceeding](LegalProceeding.md) | Split from AccountabilityEvent — dockets, parties, filings, posture (§11 |
| [Organization](Organization.md) | The single entity for ALL institutional actors; "vendor" is a role, not a sub... |
| [Person](Person.md) | [NEW] Tightly constrained (§11 |
| [PhysicalAsset](PhysicalAsset.md) | A field-observed device; geometry is OPTIONAL and operator absence is a first... |
| [Policy](Policy.md) | An institutional policy; MUST NOT be merged with ConfigurationState (§11 |
| [Product](Product.md) | A product; MUST NOT be equated with a Technology (§11 |
| [ProvenanceEdge](ProvenanceEdge.md) | Provenance relationships among claims, captures, artifacts, and sources (§12 |
| [RecordsRequest](RecordsRequest.md) | [NEW] A public-records request SIG both cites as provenance and generates as ... |
| [ResearchTask](ResearchTask.md) | [NEW] A research task as an object (§11 |
| [Resolution](Resolution.md) | A stored current-best decision record (§16 |
| [RoleAssignment](RoleAssignment.md) | Assigns one of the fourteen roles (§12 |
| [Source](Source.md) | A publisher of evidence (§10 |
| [StructuralEdge](StructuralEdge.md) | Organizational/structural relationships (§12 |
| [Technology](Technology.md) | A three-level technology (domain→family→technology, §11 |
| [UsageAggregate](UsageAggregate.md) | Aggregated usage; direction is the point (§11 |



## Slots

| Slot | Description |
| --- | --- |
| [absence_kind](absence_kind.md) |  |
| [access_kind](access_kind.md) | Configured vs observed vs declared — never defaulted into one another (SIG-ON... |
| [acquisition_channel](acquisition_channel.md) |  |
| [active_device_count](active_device_count.md) |  |
| [active_from](active_from.md) |  |
| [actually_provides_capability](actually_provides_capability.md) | Evidentiary; never silently inferred from product default (SIG-ONTO-018) |
| [address](address.md) |  |
| [adopting_body](adopting_body.md) |  |
| [affected_party_class](affected_party_class.md) | A class, never a named private individual (N4) |
| [alias](alias.md) |  |
| [alias_type](alias_type.md) |  |
| [amends_contract](amends_contract.md) |  |
| [amount](amount.md) |  |
| [applies_to](applies_to.md) | Organization, Deployment, or Product — polymorphic and repeatable |
| [applies_to_cohort](applies_to_cohort.md) | Partial termination cohort — all / new_customers_only / existing_customers_on... |
| [approved_at](approved_at.md) |  |
| [asserted_by](asserted_by.md) | Which party asserted it — perspectival (§12 |
| [asset_type](asset_type.md) | A Technology reference, not a free string |
| [audit_case_code_required](audit_case_code_required.md) |  |
| [audit_source_type](audit_source_type.md) |  |
| [authorization_state](authorization_state.md) |  |
| [automaticity](automaticity.md) |  |
| [award_date](award_date.md) |  |
| [boundary](boundary.md) | MultiPolygon, 4326 |
| [boundary_source](boundary_source.md) |  |
| [buyer](buyer.md) |  |
| [can_offer_capability](can_offer_capability.md) | Defeasible / marketing-level only (SIG-ONTO-018) |
| [canonical_name](canonical_name.md) | A claim, not an authoritative column (§8 |
| [capability](capability.md) |  |
| [captured_at](captured_at.md) |  |
| [captures_artifact](captures_artifact.md) |  |
| [case_name](case_name.md) |  |
| [citation](citation.md) |  |
| [closing_condition](closing_condition.md) |  |
| [code](code.md) |  |
| [code_system](code_system.md) | Repeatable code-system identifiers (us |
| [conditions](conditions.md) |  |
| [confidence](confidence.md) |  |
| [confirmation_status](confirmation_status.md) |  |
| [consent_gate](consent_gate.md) |  |
| [constrains_capability](constrains_capability.md) |  |
| [constrains_technology](constrains_technology.md) |  |
| [content_digest](content_digest.md) |  |
| [contracted_at](contracted_at.md) |  |
| [contracted_device_count](contracted_device_count.md) |  |
| [contradiction_state](contradiction_state.md) |  |
| [count](count.md) | Subject to small-cell suppression (§18 |
| [court](court.md) |  |
| [courtlistener_id](courtlistener_id.md) |  |
| [coverage_period](coverage_period.md) | What span the underlying audit covered — distinct from period |
| [currency](currency.md) |  |
| [data_comes_to_rest](data_comes_to_rest.md) |  |
| [data_kind](data_kind.md) | The kind of data that moves (part of the edge key, SIG-ONTO-046) |
| [data_types](data_types.md) |  |
| [date](date.md) |  |
| [denominator_published](denominator_published.md) |  |
| [deploying_organization](deploying_organization.md) |  |
| [deployment](deployment.md) | May be absent — the orphaned-device case |
| [deployments](deployments.md) |  |
| [detection_method](detection_method.md) |  |
| [direction](direction.md) | Required; never symmetric by default (SIG-ONTO-049) |
| [disposition_date](disposition_date.md) |  |
| [docket_number](docket_number.md) |  |
| [document](document.md) |  |
| [domain](domain.md) | The domain-level slug this rolls up to |
| [edge_type](edge_type.md) | Typed from the closed catalog (§12 |
| [effective_from](effective_from.md) |  |
| [effective_to](effective_to.md) |  |
| [enacting_body](enacting_body.md) |  |
| [end_date](end_date.md) |  |
| [enforcement_mechanism](enforcement_mechanism.md) |  |
| [epistemic_status](epistemic_status.md) |  |
| [estimate_radius_m](estimate_radius_m.md) |  |
| [event_type](event_type.md) |  |
| [evidence_role](evidence_role.md) |  |
| [external_id](external_id.md) |  |
| [extraction_method](extraction_method.md) |  |
| [family](family.md) | The family-level slug this rolls up to |
| [federal_award_id](federal_award_id.md) | USAspending award/sub-award id — the traceable link (SIG-ONTO-033) |
| [federal_sharing_enabled](federal_sharing_enabled.md) |  |
| [filed_date](filed_date.md) |  |
| [first_observed](first_observed.md) |  |
| [from_capture](from_capture.md) |  |
| [funder](funder.md) |  |
| [geometry](geometry.md) | Optional (SIG-GEO-004) |
| [government_domain](government_domain.md) |  |
| [granularity](granularity.md) |  |
| [holds_data_collected_by](holds_data_collected_by.md) | Custody != collection |
| [human_review_completed](human_review_completed.md) | Person creation MUST have been through human review (SIG-ONTO-016) |
| [id](id.md) | The entity's stable minted identity (L2 identity only, §8 |
| [identifier](identifier.md) | Repeatable (scheme,value) pairs, qualified by identifier_system (SIG-IDENT-00... |
| [identifier_prefix](identifier_prefix.md) | OUI or similar; never a full MAC |
| [identifier_system](identifier_system.md) |  |
| [implements_technology](implements_technology.md) |  |
| [inactive_at](inactive_at.md) |  |
| [initiator](initiator.md) |  |
| [installed_device_count](installed_device_count.md) |  |
| [instrument_type](instrument_type.md) |  |
| [integrity](integrity.md) |  |
| [jurisdiction](jurisdiction.md) |  |
| [jurisdiction_type](jurisdiction_type.md) |  |
| [last_observed](last_observed.md) |  |
| [litigation_hold](litigation_hold.md) | A flag, coexisting with any state combination (SIG-ONTO-061) |
| [live_stream_permitted_to](live_stream_permitted_to.md) |  |
| [location_estimate](location_estimate.md) | With estimate_radius_m — never a bare point |
| [manufacturer](manufacturer.md) |  |
| [mechanism](mechanism.md) |  |
| [mobility](mobility.md) |  |
| [model](model.md) |  |
| [name](name.md) |  |
| [name_lang](name_lang.md) |  |
| [national_lookup_enabled](national_lookup_enabled.md) |  |
| [observation_count](observation_count.md) |  |
| [observed_at](observed_at.md) | When SIG observed the state (observation time, never collapsed with valid tim... |
| [observed_via](observed_via.md) |  |
| [offense_category_filter](offense_category_filter.md) |  |
| [operational_state](operational_state.md) |  |
| [operator](operator.md) |  |
| [organization_type](organization_type.md) |  |
| [organizations](organizations.md) |  |
| [osm_version](osm_version.md) |  |
| [over](over.md) | The PhysicalAsset / Deployment / DataSystem the role is held over |
| [parent_cooperative_contract](parent_cooperative_contract.md) | The master award being ridden (SIG-ONTO-032) |
| [parent_jurisdiction](parent_jurisdiction.md) | Multiple parents permitted; hierarchies overlap (SIG-ONTO-010) |
| [parent_organization](parent_organization.md) |  |
| [parties](parties.md) |  |
| [party](party.md) | The Organization (or, rarely and reviewed, Person) holding the role |
| [party_role](party_role.md) |  |
| [period](period.md) |  |
| [physical_state](physical_state.md) |  |
| [platform](platform.md) |  |
| [policy_type](policy_type.md) |  |
| [posture](posture.md) |  |
| [predicate](predicate.md) |  |
| [procurement_state](procurement_state.md) |  |
| [product](product.md) |  |
| [product_name](product_name.md) | Time-bounded; products are renamed constantly |
| [product_status](product_status.md) |  |
| [products](products.md) |  |
| [program_name](program_name.md) | e |
| [promotion_status](promotion_status.md) |  |
| [proposed_at](proposed_at.md) |  |
| [public_interest_basis](public_interest_basis.md) | MUST pass the officer-naming test (§43 |
| [publication_review](publication_review.md) | Routes surrogate-only orgs through §43 |
| [published_by](published_by.md) |  |
| [publisher_name](publisher_name.md) |  |
| [quantities](quantities.md) |  |
| [rationale](rationale.md) |  |
| [raw_value](raw_value.md) |  |
| [reason_category](reason_category.md) |  |
| [reason_raw_value](reason_raw_value.md) | Normalized reason_category retains the raw value (P2) |
| [recap_id](recap_id.md) |  |
| [recipient](recipient.md) |  |
| [released_documents](released_documents.md) |  |
| [reliability](reliability.md) |  |
| [renewal_options](renewal_options.md) |  |
| [request_text](request_text.md) |  |
| [requesting_party](requesting_party.md) |  |
| [requires_authorization_of](requires_authorization_of.md) | CCOPS-style approval requirements |
| [residential_parcel_flag](residential_parcel_flag.md) | A true value bars publication outright (§43 |
| [resolved](resolved.md) |  |
| [resolved_value](resolved_value.md) |  |
| [response_date](response_date.md) |  |
| [response_status](response_status.md) |  |
| [retention](retention.md) | A ConfigurationState fact where it varies per deployment |
| [retention_bucket](retention_bucket.md) | The ordinal bucket form; comparison operates on intervals, never a coerced po... |
| [retention_days](retention_days.md) | Duration OR ordinal bucket; MUST accept both (SIG-ONTO-035a) |
| [role](role.md) |  |
| [role_description](role_description.md) | The public role justifying inclusion (e |
| [scope](scope.md) |  |
| [search_scope](search_scope.md) |  |
| [searching_org](searching_org.md) |  |
| [seller](seller.md) |  |
| [sensitivity_tier](sensitivity_tier.md) |  |
| [sharing_partner](sharing_partner.md) | Repeatable, directional |
| [signed_date](signed_date.md) |  |
| [source](source.md) | The asserting/originating node (directed — §12 |
| [source_org](source_org.md) |  |
| [sources](sources.md) | Supporting evidence artifacts/sources; every fact is evidenced (SIG-CHART-013... |
| [start_date](start_date.md) |  |
| [state](state.md) |  |
| [state_lookup_enabled](state_lookup_enabled.md) |  |
| [statutory_basis](statutory_basis.md) |  |
| [subject](subject.md) |  |
| [subscribed_hotlist_topic](subscribed_hotlist_topic.md) |  |
| [succession](succession.md) |  |
| [succession_kind](succession_kind.md) |  |
| [successor_product](successor_product.md) |  |
| [sunset_date](sunset_date.md) |  |
| [supersedes](supersedes.md) |  |
| [system_scope](system_scope.md) |  |
| [target](target.md) |  |
| [target_agency](target_agency.md) |  |
| [task_type](task_type.md) |  |
| [technologies](technologies.md) |  |
| [technology](technology.md) | The technology-level slug |
| [terminable_by](terminable_by.md) |  |
| [termination_reason](termination_reason.md) |  |
| [text](text.md) |  |
| [third_party_integration](third_party_integration.md) |  |
| [transport](transport.md) |  |
| [upstream_id](upstream_id.md) | Qualified by system (osm |
| [valid_from](valid_from.md) | When the fact/relationship became true (valid time, §9 |
| [valid_from_kind](valid_from_kind.md) | Whether valid_from is known, unknown, or ongoing (§9 |
| [valid_to](valid_to.md) | When it ceased to be true; distinct from unknown vs ongoing (§9 |
| [valid_to_kind](valid_to_kind.md) | Whether valid_to is known, unknown, or ongoing (§9 |
| [value](value.md) |  |
| [value_kind](value_kind.md) |  |
| [vendor](vendor.md) |  |


## Enumerations

| Enumeration | Description |
| --- | --- |
| [AbsenceKind](AbsenceKind.md) | How an absence is known — negative space is queryable (§9 |
| [AccessKind](AccessKind.md) | The three edge types that MUST NEVER be merged (§12 |
| [AccountabilityEventType](AccountabilityEventType.md) | Accountability event type (§11 |
| [AcquisitionChannel](AcquisitionChannel.md) | Contract acquisition channel (§11 |
| [AcquisitionMethod](AcquisitionMethod.md) | Acquisition method, internationalized (§13 |
| [AliasType](AliasType.md) | Organization alias qualifier (§11 |
| [ArtifactIntegrity](ArtifactIntegrity.md) | Integrity I of the artifact (§10 |
| [AuditSourceType](AuditSourceType.md) | Audit source type — these are NOT interchangeable (§11 |
| [AuthorizationState](AuthorizationState.md) | Track 4 — authorization (§13 |
| [Automaticity](Automaticity.md) | How access is triggered (§12 |
| [CapabilityScope](CapabilityScope.md) | Capability scope values (§11 |
| [ClaimDirectness](ClaimDirectness.md) | Directness D from the (genre × predicate) matrix (§10 |
| [CohortApplicability](CohortApplicability.md) | Which cohort an integration termination applies to (§12 |
| [ConfirmationStatus](ConfirmationStatus.md) | How a physical asset was confirmed (§11 |
| [ContradictionState](ContradictionState.md) | State of a contradiction (§31) |
| [Currency](Currency.md) | Currency C derived at query time from volatility half-life (§28 |
| [DetectionMethod](DetectionMethod.md) | How a candidate asset was detected (§11 |
| [Direction](Direction.md) | Explicit edge direction — never symmetric by default (§12 |
| [EdgeType](EdgeType.md) | The closed catalog of relationship types (§12 |
| [EnforcementMechanism](EnforcementMechanism.md) | Policy enforcement mechanism (§11 |
| [EpistemicStatus](EpistemicStatus.md) | Required epistemic status of an accountability event (§11 |
| [EvidenceRole](EvidenceRole.md) | The role a piece of evidence plays for a claim (§13 |
| [FundingInstrumentType](FundingInstrumentType.md) | Funding instrument type (§11 |
| [JurisdictionType](JurisdictionType.md) | Jurisdiction type, namespaced per country (§11 |
| [LegalInstrumentType](LegalInstrumentType.md) | Legal instrument type, internationalized (§11 |
| [Mobility](Mobility.md) | Physical asset mobility (§11 |
| [ObservedVia](ObservedVia.md) | How a configuration state was observed (§11 |
| [OperationalState](OperationalState.md) | Track 3 — operational (§13 |
| [OrganizationType](OrganizationType.md) | Organization type, namespaced and extensible (§11 |
| [PhysicalState](PhysicalState.md) | Track 2 — physical (§13 |
| [PolicyType](PolicyType.md) | Policy type (§11 |
| [PredicateVolatility](PredicateVolatility.md) | Volatility class governing currency decay (§28 |
| [ProceedingPosture](ProceedingPosture.md) | Legal proceeding posture (§11 |
| [ProcurementState](ProcurementState.md) | Track 1 — procurement (§13 |
| [ProductStatus](ProductStatus.md) | Product lifecycle status (§11 |
| [PromotionStatus](PromotionStatus.md) | Candidate-asset promotion lifecycle (§11 |
| [RecordsPlatform](RecordsPlatform.md) | Records-request platform (§11 |
| [RecordsResponseStatus](RecordsResponseStatus.md) | Records-request response status (§11 |
| [ResolutionStrategy](ResolutionStrategy.md) | Per-predicate resolution strategy (§28 |
| [Role](Role.md) | The fourteen separately-modelled roles (§12 |
| [Salience](Salience.md) | Technology salience rating (§13 |
| [SkosMappingRelation](SkosMappingRelation.md) | SKOS mapping relations for crosswalks (§20 |
| [SourceReliability](SourceReliability.md) | Reliability R of the publisher, not the claim (§10 |
| [SuccessionKind](SuccessionKind.md) | Temporal identity succession qualifier (§14 |
| [SystemScope](SystemScope.md) | DataSystem scope (§11 |
| [TemporalBoundKind](TemporalBoundKind.md) | How a temporal bound is known (§9 |
| [ValueKind](ValueKind.md) | RDF-style value kind — known value, unknown value, or no value (§9 |
| [WeightClass](WeightClass.md) | Composed weight class W (§10 |


## Types

| Type | Description |
| --- | --- |
| [Bcp47](Bcp47.md) | A BCP-47 language tag qualifying a label-bearing value (§9 |
| [Boolean](Boolean.md) | A binary (true or false) value |
| [CapabilityCode](CapabilityCode.md) | A `verb |
| [Curie](Curie.md) | a compact URI |
| [Date](Date.md) | a date (year, month and day) in an idealized calendar |
| [DateOrDatetime](DateOrDatetime.md) | Either a date or a datetime |
| [Datetime](Datetime.md) | The combination of a date and time |
| [Decimal](Decimal.md) | A real number with arbitrary precision that conforms to the xsd:decimal speci... |
| [Double](Double.md) | A real number that conforms to the xsd:double specification |
| [DurationIso](DurationIso.md) | An ISO-8601 duration (e |
| [Edtf](Edtf.md) | An Extended Date/Time Format (ISO 8601-2 / EDTF) string |
| [Float](Float.md) | A real number that conforms to the xsd:float specification |
| [GeometryWkt](GeometryWkt.md) | A geometry as WKT/EWKT, SRID 4326 unless otherwise stated (§19 |
| [Integer](Integer.md) | An integer |
| [Jsonpath](Jsonpath.md) | A string encoding a JSON Path |
| [Jsonpointer](Jsonpointer.md) | A string encoding a JSON Pointer |
| [Money](Money.md) | A monetary amount; always paired with a currency slot |
| [Ncname](Ncname.md) | Prefix part of CURIE |
| [Nodeidentifier](Nodeidentifier.md) | A URI, CURIE or BNODE that represents a node in a model |
| [Objectidentifier](Objectidentifier.md) | A URI or CURIE that represents an object in the model |
| [PredicateCode](PredicateCode.md) | A slug from the predicate registry (§13 |
| [Sparqlpath](Sparqlpath.md) | A string encoding a SPARQL Property Path |
| [String](String.md) | A character string |
| [TechnologyCode](TechnologyCode.md) | A slug from the versioned SKOS Technology concept scheme (§13 |
| [Time](Time.md) | A time object represents a (local) time of day, independent of any particular... |
| [Uri](Uri.md) | a complete URI |
| [Uriorcurie](Uriorcurie.md) | a URI or a CURIE |


## Subsets

| Subset | Description |
| --- | --- |
