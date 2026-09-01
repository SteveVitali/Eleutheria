# Surveillance Infrastructure Graph ontology

The canonical SIG ontology: entities (§11), relationships (§12), and the structural controlled vocabularies (§13). One LinkML source generates every downstream form (§20.1).

URI: https://ontology.sig-project.org/schema/sig

Name: sig



## Classes

| Class | Description |
| --- | --- |
| [AccessRelationship](classes/AccessRelationship.md) | A sharing/access relationship; direction, scope, automaticity, and kind are a... |
| [AccountabilityEvent](classes/AccountabilityEvent.md) | An accountability event; epistemic_status is REQUIRED and rendered everywhere... |
| [CandidateAsset](classes/CandidateAsset.md) | [NEW] RF/heuristic leads that MUST live in a separate entity type and MUST NO... |
| [Capability](classes/Capability.md) | A verb |
| [Claim](classes/Claim.md) | An append-only assertion (subject, predicate, value,  |
| [ConfigurationState](classes/ConfigurationState.md) | Promoted to a first-class, time-versioned, per-Deployment entity (§11 |
| [Contract](classes/Contract.md) | A contract; acquisition_channel and parent_cooperative_contract are REQUIRED ... |
| [Contradiction](classes/Contradiction.md) | A first-class, addressable contradiction object (§31) |
| [CoverageRecord](classes/CoverageRecord.md) | [NEW] Makes negative claims queryable (§11 |
| [DataSystem](classes/DataSystem.md) | Reference databases as infrastructure — representable even where SIG holds no... |
| [Deployment](classes/Deployment.md) | The bridge between organizational adoption and individual devices; creatable ... |
| [Edge](classes/Edge.md) | Universal edge requirements (§12 |
| [Entity](classes/Entity.md) | Abstract base — every entity has identity (§3 |
| [EvidenceArtifact](classes/EvidenceArtifact.md) | A specific artifact published by a Source (§10 |
| [EvidenceCapture](classes/EvidenceCapture.md) | A content-addressed capture of an artifact at a time (§10 |
| [Extraction](classes/Extraction.md) | A run that extracted claims from a capture (§10 |
| [FundingInstrument](classes/FundingInstrument.md) | [NEW] Purchaser != operator != funder (§11 |
| [IntegrationEdge](classes/IntegrationEdge.md) | A data-bearing integration edge (§12 |
| [Jurisdiction](classes/Jurisdiction.md) | [NEW] A first-class jurisdiction with a self-referential hierarchy, a pluggab... |
| [LegalInstrument](classes/LegalInstrument.md) | [NEW] Laws and regulations as a modelled entity (§11 |
| [LegalProceeding](classes/LegalProceeding.md) | Split from AccountabilityEvent — dockets, parties, filings, posture (§11 |
| [Organization](classes/Organization.md) | The single entity for ALL institutional actors; "vendor" is a role, not a sub... |
| [Person](classes/Person.md) | [NEW] Tightly constrained (§11 |
| [PhysicalAsset](classes/PhysicalAsset.md) | A field-observed device; geometry is OPTIONAL and operator absence is a first... |
| [Policy](classes/Policy.md) | An institutional policy; MUST NOT be merged with ConfigurationState (§11 |
| [Product](classes/Product.md) | A product; MUST NOT be equated with a Technology (§11 |
| [ProvenanceEdge](classes/ProvenanceEdge.md) | Provenance relationships among claims, captures, artifacts, and sources (§12 |
| [RecordsRequest](classes/RecordsRequest.md) | [NEW] A public-records request SIG both cites as provenance and generates as ... |
| [ResearchTask](classes/ResearchTask.md) | [NEW] A research task as an object (§11 |
| [Resolution](classes/Resolution.md) | A stored current-best decision record (§16 |
| [RoleAssignment](classes/RoleAssignment.md) | Assigns one of the fourteen roles (§12 |
| [Source](classes/Source.md) | A publisher of evidence (§10 |
| [StructuralEdge](classes/StructuralEdge.md) | Organizational/structural relationships (§12 |
| [Technology](classes/Technology.md) | A three-level technology (domain→family→technology, §11 |
| [UsageAggregate](classes/UsageAggregate.md) | Aggregated usage; direction is the point (§11 |



## Slots

| Slot | Description |
| --- | --- |
| [absence_kind](slots/absence_kind.md) |  |
| [access_kind](slots/access_kind.md) | Configured vs observed vs declared — never defaulted into one another (SIG-ON... |
| [acquisition_channel](slots/acquisition_channel.md) |  |
| [active_device_count](slots/active_device_count.md) |  |
| [active_from](slots/active_from.md) |  |
| [actually_provides_capability](slots/actually_provides_capability.md) | Evidentiary; never silently inferred from product default (SIG-ONTO-018) |
| [address](slots/address.md) |  |
| [adopting_body](slots/adopting_body.md) |  |
| [affected_party_class](slots/affected_party_class.md) | A class, never a named private individual (N4) |
| [alias](slots/alias.md) |  |
| [alias_type](slots/alias_type.md) |  |
| [amends_contract](slots/amends_contract.md) |  |
| [amount](slots/amount.md) |  |
| [applies_to](slots/applies_to.md) | Organization, Deployment, or Product — polymorphic and repeatable |
| [applies_to_cohort](slots/applies_to_cohort.md) | Partial termination cohort — all / new_customers_only / existing_customers_on... |
| [approved_at](slots/approved_at.md) |  |
| [artifact_type](slots/artifact_type.md) | The genre of the artifact (§10 |
| [asserted_by](slots/asserted_by.md) | Which party asserted it — perspectival (§12 |
| [asset_type](slots/asset_type.md) | A Technology reference, not a free string |
| [audit_case_code_required](slots/audit_case_code_required.md) |  |
| [audit_source_type](slots/audit_source_type.md) |  |
| [authorization_state](slots/authorization_state.md) |  |
| [automaticity](slots/automaticity.md) | Required; direction/scope/automaticity/kind are all required (SIG-ONTO-049) |
| [award_date](slots/award_date.md) |  |
| [boundary](slots/boundary.md) | MultiPolygon, 4326 |
| [boundary_source](slots/boundary_source.md) |  |
| [buyer](slots/buyer.md) |  |
| [can_offer_capability](slots/can_offer_capability.md) | Defeasible / marketing-level only (SIG-ONTO-018) |
| [canonical_name](slots/canonical_name.md) | A claim, not an authoritative column (§8 |
| [capability](slots/capability.md) |  |
| [captured_at](slots/captured_at.md) |  |
| [captures_artifact](slots/captures_artifact.md) |  |
| [case_name](slots/case_name.md) |  |
| [citation](slots/citation.md) |  |
| [closing_condition](slots/closing_condition.md) |  |
| [code](slots/code.md) |  |
| [code_system](slots/code_system.md) | Repeatable code-system identifiers (us |
| [conditions](slots/conditions.md) |  |
| [confidence](slots/confidence.md) |  |
| [confirmation_status](slots/confirmation_status.md) |  |
| [consent_gate](slots/consent_gate.md) |  |
| [constrains_capability](slots/constrains_capability.md) |  |
| [constrains_technology](slots/constrains_technology.md) |  |
| [content_digest](slots/content_digest.md) |  |
| [contracted_at](slots/contracted_at.md) |  |
| [contracted_device_count](slots/contracted_device_count.md) |  |
| [contradiction_state](slots/contradiction_state.md) |  |
| [count](slots/count.md) | Subject to small-cell suppression (§18 |
| [court](slots/court.md) |  |
| [courtlistener_id](slots/courtlistener_id.md) |  |
| [coverage_period](slots/coverage_period.md) | What span the underlying audit covered — distinct from period |
| [currency](slots/currency.md) |  |
| [data_comes_to_rest](slots/data_comes_to_rest.md) |  |
| [data_kind](slots/data_kind.md) | The kind of data that moves (part of the edge key, SIG-ONTO-046) |
| [data_types](slots/data_types.md) |  |
| [date](slots/date.md) |  |
| [denominator_published](slots/denominator_published.md) |  |
| [deploying_organization](slots/deploying_organization.md) |  |
| [deployment](slots/deployment.md) | May be absent — the orphaned-device case |
| [deployments](slots/deployments.md) |  |
| [detection_method](slots/detection_method.md) |  |
| [direction](slots/direction.md) | Required; never symmetric by default (SIG-ONTO-049) |
| [disposition_date](slots/disposition_date.md) |  |
| [docket_number](slots/docket_number.md) |  |
| [document](slots/document.md) |  |
| [domain](slots/domain.md) | The domain-level slug this rolls up to |
| [edge_type](slots/edge_type.md) | Typed from the closed catalog (§12 |
| [effective_from](slots/effective_from.md) |  |
| [effective_to](slots/effective_to.md) |  |
| [enacting_body](slots/enacting_body.md) |  |
| [end_date](slots/end_date.md) |  |
| [enforcement_mechanism](slots/enforcement_mechanism.md) |  |
| [epistemic_status](slots/epistemic_status.md) |  |
| [estimate_radius_m](slots/estimate_radius_m.md) |  |
| [event_type](slots/event_type.md) |  |
| [evidence_role](slots/evidence_role.md) |  |
| [external_id](slots/external_id.md) |  |
| [extraction_method](slots/extraction_method.md) |  |
| [family](slots/family.md) | The family-level slug this rolls up to |
| [federal_award_id](slots/federal_award_id.md) | USAspending award/sub-award id — the traceable link (SIG-ONTO-033) |
| [federal_sharing_enabled](slots/federal_sharing_enabled.md) |  |
| [filed_date](slots/filed_date.md) |  |
| [first_observed](slots/first_observed.md) |  |
| [from_capture](slots/from_capture.md) |  |
| [funder](slots/funder.md) |  |
| [geometry](slots/geometry.md) | Optional (SIG-GEO-004) |
| [government_domain](slots/government_domain.md) |  |
| [granularity](slots/granularity.md) |  |
| [holds_data_collected_by](slots/holds_data_collected_by.md) | Custody != collection |
| [human_review_completed](slots/human_review_completed.md) | Person creation MUST have been through human review (SIG-ONTO-016) |
| [id](slots/id.md) | The entity's stable minted identity (L2 identity only, §8 |
| [identifier](slots/identifier.md) | Repeatable (scheme,value) pairs, qualified by identifier_system (SIG-IDENT-00... |
| [identifier_prefix](slots/identifier_prefix.md) | OUI or similar; never a full MAC |
| [identifier_system](slots/identifier_system.md) |  |
| [implements_technology](slots/implements_technology.md) |  |
| [inactive_at](slots/inactive_at.md) |  |
| [initiator](slots/initiator.md) |  |
| [installed_device_count](slots/installed_device_count.md) |  |
| [instrument_type](slots/instrument_type.md) |  |
| [integrity](slots/integrity.md) |  |
| [jurisdiction](slots/jurisdiction.md) |  |
| [jurisdiction_type](slots/jurisdiction_type.md) |  |
| [last_observed](slots/last_observed.md) |  |
| [litigation_hold](slots/litigation_hold.md) | A flag, coexisting with any state combination (SIG-ONTO-061) |
| [live_stream_permitted_to](slots/live_stream_permitted_to.md) |  |
| [location_estimate](slots/location_estimate.md) | With estimate_radius_m — never a bare point |
| [manufacturer](slots/manufacturer.md) |  |
| [mechanism](slots/mechanism.md) |  |
| [mobility](slots/mobility.md) |  |
| [model](slots/model.md) |  |
| [name](slots/name.md) |  |
| [name_lang](slots/name_lang.md) |  |
| [national_lookup_enabled](slots/national_lookup_enabled.md) |  |
| [observation_count](slots/observation_count.md) |  |
| [observed_at](slots/observed_at.md) | When SIG observed the state (observation time, never collapsed with valid tim... |
| [observed_via](slots/observed_via.md) |  |
| [offense_category_filter](slots/offense_category_filter.md) |  |
| [operational_state](slots/operational_state.md) |  |
| [operator](slots/operator.md) |  |
| [organization_type](slots/organization_type.md) |  |
| [organizations](slots/organizations.md) |  |
| [osm_version](slots/osm_version.md) |  |
| [over](slots/over.md) | The PhysicalAsset / Deployment / DataSystem the role is held over |
| [parent_cooperative_contract](slots/parent_cooperative_contract.md) | The master award being ridden (SIG-ONTO-032) |
| [parent_jurisdiction](slots/parent_jurisdiction.md) | Multiple parents permitted; hierarchies overlap (SIG-ONTO-010) |
| [parent_organization](slots/parent_organization.md) |  |
| [parties](slots/parties.md) |  |
| [party](slots/party.md) | The Organization (or, rarely and reviewed, Person) holding the role |
| [party_role](slots/party_role.md) |  |
| [period](slots/period.md) |  |
| [physical_state](slots/physical_state.md) |  |
| [platform](slots/platform.md) |  |
| [policy_type](slots/policy_type.md) |  |
| [posture](slots/posture.md) |  |
| [predicate](slots/predicate.md) |  |
| [procurement_state](slots/procurement_state.md) |  |
| [product](slots/product.md) |  |
| [product_name](slots/product_name.md) | Time-bounded; products are renamed constantly |
| [product_status](slots/product_status.md) |  |
| [products](slots/products.md) |  |
| [program_name](slots/program_name.md) | e |
| [promotion_status](slots/promotion_status.md) |  |
| [proposed_at](slots/proposed_at.md) |  |
| [public_interest_basis](slots/public_interest_basis.md) | MUST pass the officer-naming test (§43 |
| [publication_review](slots/publication_review.md) | Routes surrogate-only orgs through §43 |
| [published_by](slots/published_by.md) |  |
| [publisher_name](slots/publisher_name.md) |  |
| [quantities](slots/quantities.md) |  |
| [rationale](slots/rationale.md) |  |
| [raw_value](slots/raw_value.md) |  |
| [reason_category](slots/reason_category.md) |  |
| [reason_raw_value](slots/reason_raw_value.md) | Normalized reason_category retains the raw value (P2) |
| [recap_id](slots/recap_id.md) |  |
| [recipient](slots/recipient.md) |  |
| [released_documents](slots/released_documents.md) |  |
| [reliability](slots/reliability.md) |  |
| [renewal_options](slots/renewal_options.md) |  |
| [request_text](slots/request_text.md) |  |
| [requesting_party](slots/requesting_party.md) |  |
| [requires_authorization_of](slots/requires_authorization_of.md) | CCOPS-style approval requirements |
| [residential_parcel_flag](slots/residential_parcel_flag.md) | A true value bars publication outright (§43 |
| [resolved](slots/resolved.md) |  |
| [resolved_value](slots/resolved_value.md) |  |
| [response_date](slots/response_date.md) |  |
| [response_status](slots/response_status.md) |  |
| [retention](slots/retention.md) | A ConfigurationState fact where it varies per deployment |
| [retention_bucket](slots/retention_bucket.md) | The ordinal bucket form; comparison operates on intervals, never a coerced po... |
| [retention_days](slots/retention_days.md) | Duration OR ordinal bucket; MUST accept both (SIG-ONTO-035a) |
| [role](slots/role.md) |  |
| [role_description](slots/role_description.md) | The public role justifying inclusion (e |
| [scope](slots/scope.md) |  |
| [search_scope](slots/search_scope.md) |  |
| [searching_org](slots/searching_org.md) |  |
| [seller](slots/seller.md) |  |
| [sensitivity_tier](slots/sensitivity_tier.md) |  |
| [sharing_partner](slots/sharing_partner.md) | Repeatable, directional |
| [signed_date](slots/signed_date.md) |  |
| [source](slots/source.md) | The asserting/originating node (directed — §12 |
| [source_classes](slots/source_classes.md) | The OL-2E-AL-03 class of each entry in `sources`, index-aligned (as `parties`... |
| [source_org](slots/source_org.md) |  |
| [sources](slots/sources.md) | Supporting evidence artifacts/sources; every fact is evidenced (SIG-CHART-013... |
| [start_date](slots/start_date.md) |  |
| [state](slots/state.md) |  |
| [state_lookup_enabled](slots/state_lookup_enabled.md) |  |
| [statutory_basis](slots/statutory_basis.md) |  |
| [subject](slots/subject.md) |  |
| [subscribed_hotlist_topic](slots/subscribed_hotlist_topic.md) |  |
| [succession](slots/succession.md) |  |
| [succession_kind](slots/succession_kind.md) |  |
| [successor_product](slots/successor_product.md) |  |
| [sunset_date](slots/sunset_date.md) |  |
| [supersedes](slots/supersedes.md) |  |
| [system_scope](slots/system_scope.md) |  |
| [target](slots/target.md) |  |
| [target_agency](slots/target_agency.md) |  |
| [task_type](slots/task_type.md) |  |
| [technologies](slots/technologies.md) |  |
| [technology](slots/technology.md) | The technology-level slug |
| [terminable_by](slots/terminable_by.md) |  |
| [termination_reason](slots/termination_reason.md) |  |
| [text](slots/text.md) |  |
| [third_party_integration](slots/third_party_integration.md) |  |
| [transport](slots/transport.md) |  |
| [upstream_id](slots/upstream_id.md) | Qualified by system (osm |
| [valid_from](slots/valid_from.md) | When the fact/relationship became true (valid time, §9 |
| [valid_from_kind](slots/valid_from_kind.md) | Whether valid_from is known, unknown, or ongoing (§9 |
| [valid_to](slots/valid_to.md) | When it ceased to be true; distinct from unknown vs ongoing (§9 |
| [valid_to_kind](slots/valid_to_kind.md) | Whether valid_to is known, unknown, or ongoing (§9 |
| [value](slots/value.md) |  |
| [value_kind](slots/value_kind.md) |  |
| [vendor](slots/vendor.md) |  |


## Enumerations

| Enumeration | Description |
| --- | --- |
| [AbsenceKind](enums/AbsenceKind.md) | How an absence is known — negative space is queryable (§9 |
| [AccessKind](enums/AccessKind.md) | The three edge types that MUST NEVER be merged (§12 |
| [AccountabilityEventType](enums/AccountabilityEventType.md) | Accountability event type (§11 |
| [AcquisitionChannel](enums/AcquisitionChannel.md) | Contract acquisition channel (§11 |
| [AcquisitionMethod](enums/AcquisitionMethod.md) | Acquisition method, internationalized (§13 |
| [AliasType](enums/AliasType.md) | Organization alias qualifier (§11 |
| [ArtifactIntegrity](enums/ArtifactIntegrity.md) | Integrity I of the artifact (§10 |
| [ArtifactType](enums/ArtifactType.md) | The genre of an evidence artifact (§10 |
| [AuditSourceType](enums/AuditSourceType.md) | Audit source type — these are NOT interchangeable (§11 |
| [AuthorizationState](enums/AuthorizationState.md) | Track 4 — authorization (§13 |
| [Automaticity](enums/Automaticity.md) | How access is triggered (§12 |
| [CapabilityScope](enums/CapabilityScope.md) | Capability scope values (§11 |
| [ClaimDirectness](enums/ClaimDirectness.md) | Directness D from the (genre × predicate) matrix (§10 |
| [CohortApplicability](enums/CohortApplicability.md) | Which cohort an integration termination applies to (§12 |
| [ConfirmationStatus](enums/ConfirmationStatus.md) | How a physical asset was confirmed (§11 |
| [ContradictionState](enums/ContradictionState.md) | State of a contradiction (§31) |
| [Currency](enums/Currency.md) | Currency C derived at query time from volatility half-life (§28 |
| [DetectionMethod](enums/DetectionMethod.md) | How a candidate asset was detected (§11 |
| [Direction](enums/Direction.md) | Explicit edge direction — never symmetric by default (§12 |
| [EdgeType](enums/EdgeType.md) | The closed catalog of relationship types (§12 |
| [EnforcementMechanism](enums/EnforcementMechanism.md) | Policy enforcement mechanism (§11 |
| [EpistemicStatus](enums/EpistemicStatus.md) | Required epistemic status of an accountability event (§11 |
| [EvidenceRole](enums/EvidenceRole.md) | The role a piece of evidence plays for a claim (§13 |
| [FundingInstrumentType](enums/FundingInstrumentType.md) | Funding instrument type (§11 |
| [GeometryPrecision](enums/GeometryPrecision.md) | How precisely a stored geometry locates its subject (§14 |
| [JurisdictionType](enums/JurisdictionType.md) | Jurisdiction type, namespaced per country (§11 |
| [LegalInstrumentType](enums/LegalInstrumentType.md) | Legal instrument type, internationalized (§11 |
| [Mobility](enums/Mobility.md) | Physical asset mobility (§11 |
| [ObservedVia](enums/ObservedVia.md) | How a configuration state was observed (§11 |
| [OperationalState](enums/OperationalState.md) | Track 3 — operational (§13 |
| [OrganizationRelationType](enums/OrganizationRelationType.md) | The seven-value vocabulary of the reified, bitemporal OrganizationRelation (§... |
| [OrganizationType](enums/OrganizationType.md) | Organization type, namespaced and extensible (§11 |
| [PhysicalState](enums/PhysicalState.md) | Track 2 — physical (§13 |
| [PolicyType](enums/PolicyType.md) | Policy type (§11 |
| [PredicateVolatility](enums/PredicateVolatility.md) | Volatility class governing currency decay (§28 |
| [ProceedingPosture](enums/ProceedingPosture.md) | Legal proceeding posture (§11 |
| [ProcurementState](enums/ProcurementState.md) | Track 1 — procurement (§13 |
| [ProductStatus](enums/ProductStatus.md) | Product lifecycle status (§11 |
| [PromotionStatus](enums/PromotionStatus.md) | Candidate-asset promotion lifecycle (§11 |
| [RecordsPlatform](enums/RecordsPlatform.md) | Records-request platform (§11 |
| [RecordsResponseStatus](enums/RecordsResponseStatus.md) | Records-request response status (§11 |
| [ResolutionStrategy](enums/ResolutionStrategy.md) | Per-predicate resolution strategy (§28 |
| [Role](enums/Role.md) | The fourteen separately-modelled roles (§12 |
| [Salience](enums/Salience.md) | Technology salience rating (§13 |
| [SkosMappingRelation](enums/SkosMappingRelation.md) | SKOS mapping relations for crosswalks (§20 |
| [SourceClass](enums/SourceClass.md) | The six evidence source classes of OL-2E-AL-03 (§11 |
| [SourceReliability](enums/SourceReliability.md) | Reliability R of the publisher, not the claim (§10 |
| [SuccessionKind](enums/SuccessionKind.md) | Temporal identity succession qualifier (§14 |
| [SystemScope](enums/SystemScope.md) | DataSystem scope (§11 |
| [TemporalBoundKind](enums/TemporalBoundKind.md) | How a temporal bound is known (§9 |
| [ValueKind](enums/ValueKind.md) | RDF-style value kind — known value, unknown value, or no value (§9 |
| [WeightClass](enums/WeightClass.md) | Composed weight class W (§10 |


## Types

| Type | Description |
| --- | --- |
| [Bcp47](types/Bcp47.md) | A BCP-47 language tag qualifying a label-bearing value (§9 |
| [Boolean](types/Boolean.md) | A binary (true or false) value |
| [CapabilityCode](types/CapabilityCode.md) | A `verb |
| [Curie](types/Curie.md) | a compact URI |
| [Date](types/Date.md) | a date (year, month and day) in an idealized calendar |
| [DateOrDatetime](types/DateOrDatetime.md) | Either a date or a datetime |
| [Datetime](types/Datetime.md) | The combination of a date and time |
| [Decimal](types/Decimal.md) | A real number with arbitrary precision that conforms to the xsd:decimal speci... |
| [Double](types/Double.md) | A real number that conforms to the xsd:double specification |
| [DurationIso](types/DurationIso.md) | An ISO-8601 duration (e |
| [Edtf](types/Edtf.md) | An Extended Date/Time Format (ISO 8601-2 / EDTF) string |
| [Float](types/Float.md) | A real number that conforms to the xsd:float specification |
| [GeometryWkt](types/GeometryWkt.md) | A geometry as WKT/EWKT, SRID 4326 unless otherwise stated (§19 |
| [Integer](types/Integer.md) | An integer |
| [Jsonpath](types/Jsonpath.md) | A string encoding a JSON Path |
| [Jsonpointer](types/Jsonpointer.md) | A string encoding a JSON Pointer |
| [Money](types/Money.md) | A monetary amount; always paired with a currency slot |
| [Ncname](types/Ncname.md) | Prefix part of CURIE |
| [Nodeidentifier](types/Nodeidentifier.md) | A URI, CURIE or BNODE that represents a node in a model |
| [Objectidentifier](types/Objectidentifier.md) | A URI or CURIE that represents an object in the model |
| [PredicateCode](types/PredicateCode.md) | A slug from the predicate registry (§13 |
| [Sparqlpath](types/Sparqlpath.md) | A string encoding a SPARQL Property Path |
| [String](types/String.md) | A character string |
| [TechnologyCode](types/TechnologyCode.md) | A slug from the versioned SKOS Technology concept scheme (§13 |
| [Time](types/Time.md) | A time object represents a (local) time of day, independent of any particular... |
| [Uri](types/Uri.md) | a complete URI |
| [Uriorcurie](types/Uriorcurie.md) | a URI or a CURIE |


## Subsets

| Subset | Description |
| --- | --- |
