-- # Abstract Class: Entity Description: Abstract base — every entity has identity (§3.1 defining standard).
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: Jurisdiction Description: [NEW] A first-class jurisdiction with a self-referential hierarchy, a pluggable national code system, and temporally-versioned geometry (§11.1, SIG-ONTO-010/011).
--     * Slot: jurisdiction_type
--     * Slot: boundary Description: MultiPolygon, 4326.
--     * Slot: boundary_source
--     * Slot: valid_from
--     * Slot: valid_to
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: Organization Description: The single entity for ALL institutional actors; "vendor" is a role, not a subtype (§11.2, SIG-ONTO-012). canonical_name is a claim, not a column (§8.2).
--     * Slot: canonical_name Description: A claim, not an authoritative column (§8.2, SIG-ONTO-003).
--     * Slot: organization_type
--     * Slot: parent_organization
--     * Slot: jurisdiction
--     * Slot: government_domain
--     * Slot: valid_from
--     * Slot: valid_to
--     * Slot: publication_review Description: Routes surrogate-only orgs through §43.4 before public exposure (SIG-ONTO-013).
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: Person Description: [NEW] Tightly constrained (§11.3, SIG-ONTO-014/015/016). A Person row carries NO surveillance attributes and MUST NOT be reachable from any automated extraction path. It exists only for named public officials and SIG's own attributable curators.
--     * Slot: public_interest_basis Description: MUST pass the officer-naming test (§43.4); required (SIG-ONTO-016).
--     * Slot: human_review_completed Description: Person creation MUST have been through human review (SIG-ONTO-016).
--     * Slot: role_description Description: The public role justifying inclusion (e.g. named official in an accountability event).
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: Product Description: A product; MUST NOT be equated with a Technology (§11.4, SIG-ONTO-017).
--     * Slot: product_name Description: Time-bounded; products are renamed constantly.
--     * Slot: vendor
--     * Slot: product_status
--     * Slot: successor_product
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: Technology Description: A three-level technology (domain→family→technology, §11.5, SIG-ONTO-019). The authoritative term hierarchy is the SKOS Technology scheme (§13.1); this class carries the code and its rollup levels for a specific referenced node.
--     * Slot: technology Description: The technology-level slug.
--     * Slot: family Description: The family-level slug this rolls up to.
--     * Slot: domain Description: The domain-level slug this rolls up to.
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: Capability Description: A verb.object.scope capability (§11.6, SIG-ONTO-023).
--     * Slot: capability
--     * Slot: scope
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: Deployment Description: The bridge between organizational adoption and individual devices; creatable with NO product, NO vendor, and NO physical asset (§11.7, SIG-ONTO-026).
--     * Slot: deploying_organization
--     * Slot: product
--     * Slot: vendor
--     * Slot: procurement_state
--     * Slot: physical_state
--     * Slot: operational_state
--     * Slot: authorization_state
--     * Slot: litigation_hold Description: A flag, coexisting with any state combination (SIG-ONTO-061).
--     * Slot: jurisdiction
--     * Slot: contracted_device_count
--     * Slot: installed_device_count
--     * Slot: active_device_count
--     * Slot: proposed_at
--     * Slot: approved_at
--     * Slot: contracted_at
--     * Slot: active_from
--     * Slot: inactive_at
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: PhysicalAsset Description: A field-observed device; geometry is OPTIONAL and operator absence is a first-class countable state (§11.8, SIG-ONTO-027/028). Accommodates ways and relations, not only nodes, and MUST NOT force sensors into a camera abstraction.
--     * Slot: asset_type Description: A Technology reference, not a free string.
--     * Slot: geometry Description: Optional (SIG-GEO-004).
--     * Slot: mobility
--     * Slot: manufacturer
--     * Slot: model
--     * Slot: deployment Description: May be absent — the orphaned-device case.
--     * Slot: first_observed
--     * Slot: last_observed
--     * Slot: osm_version
--     * Slot: sensitivity_tier
--     * Slot: confirmation_status
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: CandidateAsset Description: [NEW] RF/heuristic leads that MUST live in a separate entity type and MUST NOT appear in any public device layer until promoted under §43.5 (§11.9, SIG-ONTO-029/030).
--     * Slot: detection_method
--     * Slot: location_estimate Description: With estimate_radius_m — never a bare point.
--     * Slot: estimate_radius_m
--     * Slot: identifier_prefix Description: OUI or similar; never a full MAC.
--     * Slot: observation_count
--     * Slot: promotion_status
--     * Slot: residential_parcel_flag Description: A true value bars publication outright (§43.5).
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: DataSystem Description: Reference databases as infrastructure — representable even where SIG holds no sensor (§11.10, SIG-ONTO-031).
--     * Slot: operator
--     * Slot: vendor
--     * Slot: product
--     * Slot: retention Description: A ConfigurationState fact where it varies per deployment.
--     * Slot: system_scope
--     * Slot: holds_data_collected_by Description: Custody != collection.
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: Contract Description: A contract; acquisition_channel and parent_cooperative_contract are REQUIRED model elements (§11.11, SIG-ONTO-032).
--     * Slot: buyer
--     * Slot: seller
--     * Slot: amount
--     * Slot: currency
--     * Slot: signed_date
--     * Slot: start_date
--     * Slot: end_date
--     * Slot: renewal_options
--     * Slot: document
--     * Slot: acquisition_channel
--     * Slot: parent_cooperative_contract Description: The master award being ridden (SIG-ONTO-032).
--     * Slot: amends_contract
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: FundingInstrument Description: [NEW] Purchaser != operator != funder (§11.12, SIG-ONTO-033). Grants and third-party funding; federal grant → local surveillance is traceable.
--     * Slot: funder
--     * Slot: recipient
--     * Slot: instrument_type
--     * Slot: program_name Description: e.g. Byrne JAG, UASI, COPS, Operation Stonegarden, HIDTA.
--     * Slot: amount
--     * Slot: award_date
--     * Slot: period
--     * Slot: conditions
--     * Slot: federal_award_id Description: USAspending award/sub-award id — the traceable link (SIG-ONTO-033).
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: Policy Description: An institutional policy; MUST NOT be merged with ConfigurationState (§11.13, SIG-ONTO-034). Their disagreement is a first-class finding.
--     * Slot: policy_type
--     * Slot: effective_from
--     * Slot: effective_to
--     * Slot: adopting_body
--     * Slot: text
--     * Slot: document
--     * Slot: enforcement_mechanism
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: LegalInstrument Description: [NEW] Laws and regulations as a modelled entity (§11.14). Gives the international requirement somewhere to put an arrêté préfectoral, a CNIL decision, or an EU AI Act obligation.
--     * Slot: instrument_type
--     * Slot: enacting_body
--     * Slot: jurisdiction
--     * Slot: citation
--     * Slot: effective_from
--     * Slot: effective_to
--     * Slot: sunset_date
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: ConfigurationState Description: Promoted to a first-class, time-versioned, per-Deployment entity (§11.15). Configuration is observed, never assumed (SIG-ONTO-036). Retention is a duration OR an ordinal bucket; SIG never fabricates a midpoint (SIG-ONTO-035a).
--     * Slot: deployment
--     * Slot: retention_days Description: Duration OR ordinal bucket; MUST accept both (SIG-ONTO-035a).
--     * Slot: retention_bucket Description: The ordinal bucket form; comparison operates on intervals, never a coerced point.
--     * Slot: state_lookup_enabled
--     * Slot: national_lookup_enabled
--     * Slot: federal_sharing_enabled
--     * Slot: audit_case_code_required
--     * Slot: observed_via
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: UsageAggregate Description: Aggregated usage; direction is the point (§11.16). NO per-search, per-plate, or per-person row may exist here or anywhere in SIG (SIG-ONTO-037, §18.1).
--     * Slot: searching_org
--     * Slot: source_org
--     * Slot: period Description: Minimum granularity one month for published data (§18.4).
--     * Slot: count Description: Subject to small-cell suppression (§18.4).
--     * Slot: search_scope
--     * Slot: reason_category
--     * Slot: reason_raw_value Description: Normalized reason_category retains the raw value (P2).
--     * Slot: audit_source_type
--     * Slot: coverage_period Description: What span the underlying audit covered — distinct from period.
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: AccountabilityEvent Description: An accountability event; epistemic_status is REQUIRED and rendered everywhere (§11.17, SIG-ONTO-038/039).
--     * Slot: event_type
--     * Slot: epistemic_status
--     * Slot: date
--     * Slot: affected_party_class Description: A class, never a named private individual (N4).
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: LegalProceeding Description: Split from AccountabilityEvent — dockets, parties, filings, posture (§11.18).
--     * Slot: court
--     * Slot: docket_number
--     * Slot: case_name
--     * Slot: filed_date
--     * Slot: disposition_date
--     * Slot: posture
--     * Slot: courtlistener_id
--     * Slot: recap_id
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: RecordsRequest Description: [NEW] A public-records request SIG both cites as provenance and generates as a task (§11.19). no_responsive_records is a positive finding (SIG-ONTO-040).
--     * Slot: requesting_party
--     * Slot: target_agency
--     * Slot: request_text
--     * Slot: filed_date
--     * Slot: response_date
--     * Slot: response_status
--     * Slot: statutory_basis
--     * Slot: platform
--     * Slot: external_id
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: Source Description: A publisher of evidence (§10.2, §11.20). Distinct from artifact and capture.
--     * Slot: publisher_name
--     * Slot: reliability
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: EvidenceArtifact Description: A specific artifact published by a Source (§10.2).
--     * Slot: published_by
--     * Slot: artifact_type Description: The genre of the artifact (§10.3.2, SIG-INGEST-047).
--     * Slot: integrity
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: EvidenceCapture Description: A content-addressed capture of an artifact at a time (§10.2, L0).
--     * Slot: captures_artifact
--     * Slot: captured_at
--     * Slot: content_digest
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: Extraction Description: A run that extracted claims from a capture (§10.2).
--     * Slot: from_capture
--     * Slot: extraction_method
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: Claim Description: An append-only assertion (subject, predicate, value, ...) — the substance of the graph (§10.3, L1). Physical append-only table is P02.
--     * Slot: subject
--     * Slot: predicate
--     * Slot: value
--     * Slot: value_kind
--     * Slot: raw_value
--     * Slot: absence_kind
--     * Slot: evidence_role
--     * Slot: supersedes
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: Resolution Description: A stored current-best decision record (§16.4, L3), not a view.
--     * Slot: subject
--     * Slot: predicate
--     * Slot: resolved_value
--     * Slot: confidence
--     * Slot: contradiction_state
--     * Slot: rationale
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: Contradiction Description: A first-class, addressable contradiction object (§31).
--     * Slot: subject
--     * Slot: predicate
--     * Slot: state
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: ResearchTask Description: [NEW] A research task as an object (§11.22, behaviour at §33.2).
--     * Slot: task_type
--     * Slot: target
--     * Slot: closing_condition
--     * Slot: resolved
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Class: CoverageRecord Description: [NEW] Makes negative claims queryable (§11.23, §32.2).
--     * Slot: subject
--     * Slot: predicate
--     * Slot: absence_kind
--     * Slot: coverage_period
--     * Slot: denominator_published
--     * Slot: id Description: The entity's stable minted identity (L2 identity only, §8.2).
-- # Abstract Class: Edge Description: Universal edge requirements (§12.1): directed, typed, time-bounded, evidenced, and perspectival.
--     * Slot: id
--     * Slot: source Description: The asserting/originating node (directed — §12.1.1).
--     * Slot: target
--     * Slot: edge_type Description: Typed from the closed catalog (§12.1.2).
--     * Slot: valid_from
--     * Slot: valid_to
--     * Slot: valid_from_kind Description: Snapshot sharing carries unknown/ongoing (SIG-ONTO-044).
--     * Slot: valid_to_kind
--     * Slot: observed_at
--     * Slot: asserted_by Description: Which party asserted it — perspectival (§12.1.5).
-- # Class: AccessRelationship Description: A sharing/access relationship; direction, scope, automaticity, and kind are all required — never reduced to `shares_with` (§12.5, SIG-ONTO-049). The three access kinds (§12.2) are never merged (SIG-ONTO-042).
--     * Slot: scope
--     * Slot: direction Description: Required; never symmetric by default (SIG-ONTO-049).
--     * Slot: automaticity Description: Required; direction/scope/automaticity/kind are all required (SIG-ONTO-049).
--     * Slot: access_kind Description: Configured vs observed vs declared — never defaulted into one another (SIG-ONTO-042).
--     * Slot: id
--     * Slot: source Description: The asserting/originating node (directed — §12.1.1).
--     * Slot: target
--     * Slot: edge_type Description: Typed from the closed catalog (§12.1.2).
--     * Slot: valid_from
--     * Slot: valid_to
--     * Slot: valid_from_kind Description: Snapshot sharing carries unknown/ongoing (SIG-ONTO-044).
--     * Slot: valid_to_kind
--     * Slot: observed_at
--     * Slot: asserted_by Description: Which party asserted it — perspectival (§12.1.5).
-- # Class: IntegrationEdge Description: A data-bearing integration edge (§12.3). Edges are per (product-pair, data-kind, direction), never per product-pair (SIG-ONTO-046). Unilaterally terminable, mid-contract, possibly partially, via applies_to_cohort.
--     * Slot: data_kind Description: The kind of data that moves (part of the edge key, SIG-ONTO-046).
--     * Slot: initiator
--     * Slot: transport
--     * Slot: granularity
--     * Slot: data_comes_to_rest
--     * Slot: scope
--     * Slot: consent_gate
--     * Slot: mechanism
--     * Slot: terminable_by
--     * Slot: termination_reason
--     * Slot: applies_to_cohort Description: Partial termination cohort — all / new_customers_only / existing_customers_only (SIG-ONTO-046).
--     * Slot: id
--     * Slot: source Description: The asserting/originating node (directed — §12.1.1).
--     * Slot: target
--     * Slot: edge_type Description: Typed from the closed catalog (§12.1.2).
--     * Slot: valid_from
--     * Slot: valid_to
--     * Slot: valid_from_kind Description: Snapshot sharing carries unknown/ongoing (SIG-ONTO-044).
--     * Slot: valid_to_kind
--     * Slot: observed_at
--     * Slot: asserted_by Description: Which party asserted it — perspectival (§12.1.5).
-- # Class: RoleAssignment Description: Assigns one of the fourteen roles (§12.4, SIG-ONTO-047) from a party to an asset/deployment/system. Modelled separately so the seven load-bearing separations (SIG-ONTO-048) are each independently representable, and so §43.3 coordinate sensitivity can be evaluated at the ROLE level (host≠owner).
--     * Slot: role
--     * Slot: party Description: The Organization (or, rarely and reviewed, Person) holding the role.
--     * Slot: over Description: The PhysicalAsset / Deployment / DataSystem the role is held over.
--     * Slot: id
--     * Slot: source Description: The asserting/originating node (directed — §12.1.1).
--     * Slot: target
--     * Slot: edge_type Description: Typed from the closed catalog (§12.1.2).
--     * Slot: valid_from
--     * Slot: valid_to
--     * Slot: valid_from_kind Description: Snapshot sharing carries unknown/ongoing (SIG-ONTO-044).
--     * Slot: valid_to_kind
--     * Slot: observed_at
--     * Slot: asserted_by Description: Which party asserted it — perspectival (§12.1.5).
-- # Class: StructuralEdge Description: Organizational/structural relationships (§12.6).
--     * Slot: id
--     * Slot: source Description: The asserting/originating node (directed — §12.1.1).
--     * Slot: target
--     * Slot: edge_type Description: Typed from the closed catalog (§12.1.2).
--     * Slot: valid_from
--     * Slot: valid_to
--     * Slot: valid_from_kind Description: Snapshot sharing carries unknown/ongoing (SIG-ONTO-044).
--     * Slot: valid_to_kind
--     * Slot: observed_at
--     * Slot: asserted_by Description: Which party asserted it — perspectival (§12.1.5).
-- # Class: ProvenanceEdge Description: Provenance relationships among claims, captures, artifacts, and sources (§12.7).
--     * Slot: id
--     * Slot: source Description: The asserting/originating node (directed — §12.1.1).
--     * Slot: target
--     * Slot: edge_type Description: Typed from the closed catalog (§12.1.2).
--     * Slot: valid_from
--     * Slot: valid_to
--     * Slot: valid_from_kind Description: Snapshot sharing carries unknown/ongoing (SIG-ONTO-044).
--     * Slot: valid_to_kind
--     * Slot: observed_at
--     * Slot: asserted_by Description: Which party asserted it — perspectival (§12.1.5).
-- # Class: Jurisdiction_parent_jurisdiction
--     * Slot: Jurisdiction_id Description: Autocreated FK slot
--     * Slot: parent_jurisdiction_id Description: Multiple parents permitted; hierarchies overlap (SIG-ONTO-010).
-- # Class: Jurisdiction_code_system
--     * Slot: Jurisdiction_id Description: Autocreated FK slot
--     * Slot: code_system Description: Repeatable code-system identifiers (us.census.geoid, iso.3166-2, fr.insee, ...).
-- # Class: Jurisdiction_code
--     * Slot: Jurisdiction_id Description: Autocreated FK slot
--     * Slot: code
-- # Class: Jurisdiction_name
--     * Slot: Jurisdiction_id Description: Autocreated FK slot
--     * Slot: name
-- # Class: Jurisdiction_name_lang
--     * Slot: Jurisdiction_id Description: Autocreated FK slot
--     * Slot: name_lang
-- # Class: Organization_alias
--     * Slot: Organization_id Description: Autocreated FK slot
--     * Slot: alias
-- # Class: Organization_alias_type
--     * Slot: Organization_id Description: Autocreated FK slot
--     * Slot: alias_type
-- # Class: Organization_name_lang
--     * Slot: Organization_id Description: Autocreated FK slot
--     * Slot: name_lang
-- # Class: Organization_identifier
--     * Slot: Organization_id Description: Autocreated FK slot
--     * Slot: identifier Description: Repeatable (scheme,value) pairs, qualified by identifier_system (SIG-IDENT-006).
-- # Class: Organization_identifier_system
--     * Slot: Organization_id Description: Autocreated FK slot
--     * Slot: identifier_system
-- # Class: Organization_address
--     * Slot: Organization_id Description: Autocreated FK slot
--     * Slot: address
-- # Class: Organization_succession
--     * Slot: Organization_id Description: Autocreated FK slot
--     * Slot: succession_id
-- # Class: Organization_succession_kind
--     * Slot: Organization_id Description: Autocreated FK slot
--     * Slot: succession_kind
-- # Class: Product_implements_technology
--     * Slot: Product_id Description: Autocreated FK slot
--     * Slot: implements_technology
-- # Class: Product_can_offer_capability
--     * Slot: Product_id Description: Autocreated FK slot
--     * Slot: can_offer_capability Description: Defeasible / marketing-level only (SIG-ONTO-018).
-- # Class: Deployment_technology
--     * Slot: Deployment_id Description: Autocreated FK slot
--     * Slot: technology Description: Repeatable; the coarsest level the evidence supports.
-- # Class: Deployment_actually_provides_capability
--     * Slot: Deployment_id Description: Autocreated FK slot
--     * Slot: actually_provides_capability Description: Evidentiary; never silently inferred from product default (SIG-ONTO-018).
-- # Class: PhysicalAsset_upstream_id
--     * Slot: PhysicalAsset_id Description: Autocreated FK slot
--     * Slot: upstream_id Description: Qualified by system (osm.node, osm.way, osm.relation, deflock.id, ...).
-- # Class: DataSystem_data_types
--     * Slot: DataSystem_id Description: Autocreated FK slot
--     * Slot: data_types
-- # Class: Contract_products
--     * Slot: Contract_id Description: Autocreated FK slot
--     * Slot: products_id
-- # Class: Contract_quantities
--     * Slot: Contract_id Description: Autocreated FK slot
--     * Slot: quantities
-- # Class: Policy_applies_to
--     * Slot: Policy_id Description: Autocreated FK slot
--     * Slot: applies_to Description: Organization, Deployment, or Product — polymorphic and repeatable.
-- # Class: LegalInstrument_constrains_technology
--     * Slot: LegalInstrument_id Description: Autocreated FK slot
--     * Slot: constrains_technology
-- # Class: LegalInstrument_constrains_capability
--     * Slot: LegalInstrument_id Description: Autocreated FK slot
--     * Slot: constrains_capability
-- # Class: LegalInstrument_requires_authorization_of
--     * Slot: LegalInstrument_id Description: Autocreated FK slot
--     * Slot: requires_authorization_of Description: CCOPS-style approval requirements.
-- # Class: ConfigurationState_subscribed_hotlist_topic
--     * Slot: ConfigurationState_id Description: Autocreated FK slot
--     * Slot: subscribed_hotlist_topic
-- # Class: ConfigurationState_sharing_partner
--     * Slot: ConfigurationState_id Description: Autocreated FK slot
--     * Slot: sharing_partner_id Description: Repeatable, directional.
-- # Class: ConfigurationState_offense_category_filter
--     * Slot: ConfigurationState_id Description: Autocreated FK slot
--     * Slot: offense_category_filter
-- # Class: ConfigurationState_live_stream_permitted_to
--     * Slot: ConfigurationState_id Description: Autocreated FK slot
--     * Slot: live_stream_permitted_to
-- # Class: ConfigurationState_third_party_integration
--     * Slot: ConfigurationState_id Description: Autocreated FK slot
--     * Slot: third_party_integration
-- # Class: AccountabilityEvent_organizations
--     * Slot: AccountabilityEvent_id Description: Autocreated FK slot
--     * Slot: organizations_id
-- # Class: AccountabilityEvent_deployments
--     * Slot: AccountabilityEvent_id Description: Autocreated FK slot
--     * Slot: deployments_id
-- # Class: AccountabilityEvent_technologies
--     * Slot: AccountabilityEvent_id Description: Autocreated FK slot
--     * Slot: technologies
-- # Class: AccountabilityEvent_sources
--     * Slot: AccountabilityEvent_id Description: Autocreated FK slot
--     * Slot: sources Description: Linkable to all six source classes of OL-2E-AL-03 (SIG-ONTO-039).
-- # Class: LegalProceeding_parties
--     * Slot: LegalProceeding_id Description: Autocreated FK slot
--     * Slot: parties
-- # Class: LegalProceeding_party_role
--     * Slot: LegalProceeding_id Description: Autocreated FK slot
--     * Slot: party_role
-- # Class: RecordsRequest_released_documents
--     * Slot: RecordsRequest_id Description: Autocreated FK slot
--     * Slot: released_documents
-- # Class: Edge_sources
--     * Slot: Edge_id Description: Autocreated FK slot
--     * Slot: sources Description: At least one supporting claim (§12.1.4, SIG-CHART-013).
-- # Class: AccessRelationship_sources
--     * Slot: AccessRelationship_id Description: Autocreated FK slot
--     * Slot: sources Description: At least one supporting claim (§12.1.4, SIG-CHART-013).
-- # Class: IntegrationEdge_sources
--     * Slot: IntegrationEdge_id Description: Autocreated FK slot
--     * Slot: sources Description: At least one supporting claim (§12.1.4, SIG-CHART-013).
-- # Class: RoleAssignment_sources
--     * Slot: RoleAssignment_id Description: Autocreated FK slot
--     * Slot: sources Description: At least one supporting claim (§12.1.4, SIG-CHART-013).
-- # Class: StructuralEdge_sources
--     * Slot: StructuralEdge_id Description: Autocreated FK slot
--     * Slot: sources Description: At least one supporting claim (§12.1.4, SIG-CHART-013).
-- # Class: ProvenanceEdge_sources
--     * Slot: ProvenanceEdge_id Description: Autocreated FK slot
--     * Slot: sources Description: At least one supporting claim (§12.1.4, SIG-CHART-013).

CREATE TABLE "Entity" (
	id TEXT NOT NULL,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_Entity_id" ON "Entity" (id);

CREATE TABLE "Jurisdiction" (
	jurisdiction_type VARCHAR(19),
	boundary TEXT,
	boundary_source TEXT,
	valid_from TEXT,
	valid_to TEXT,
	id TEXT NOT NULL,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_Jurisdiction_id" ON "Jurisdiction" (id);

CREATE TABLE "Person" (
	public_interest_basis TEXT NOT NULL,
	human_review_completed BOOLEAN NOT NULL,
	role_description TEXT,
	id TEXT NOT NULL,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_Person_id" ON "Person" (id);

CREATE TABLE "Technology" (
	technology TEXT,
	family TEXT,
	domain TEXT,
	id TEXT NOT NULL,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_Technology_id" ON "Technology" (id);

CREATE TABLE "Capability" (
	capability TEXT,
	scope VARCHAR(10),
	id TEXT NOT NULL,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_Capability_id" ON "Capability" (id);

CREATE TABLE "CandidateAsset" (
	detection_method VARCHAR(19),
	location_estimate TEXT,
	estimate_radius_m FLOAT,
	identifier_prefix TEXT,
	observation_count INTEGER,
	promotion_status VARCHAR(20),
	residential_parcel_flag BOOLEAN,
	id TEXT NOT NULL,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_CandidateAsset_id" ON "CandidateAsset" (id);

CREATE TABLE "AccountabilityEvent" (
	event_type VARCHAR(30),
	epistemic_status VARCHAR(16) NOT NULL,
	date TEXT,
	affected_party_class TEXT,
	id TEXT NOT NULL,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_AccountabilityEvent_id" ON "AccountabilityEvent" (id);

CREATE TABLE "Source" (
	publisher_name TEXT,
	reliability VARCHAR(2),
	id TEXT NOT NULL,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_Source_id" ON "Source" (id);

CREATE TABLE "Claim" (
	subject TEXT,
	predicate TEXT,
	value TEXT,
	value_kind VARCHAR(9),
	raw_value TEXT,
	absence_kind VARCHAR(19),
	evidence_role VARCHAR(16),
	supersedes TEXT,
	id TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(supersedes) REFERENCES "Claim" (id)
);
CREATE INDEX "ix_Claim_id" ON "Claim" (id);

CREATE TABLE "Resolution" (
	subject TEXT,
	predicate TEXT,
	resolved_value TEXT,
	confidence VARCHAR(2),
	contradiction_state VARCHAR(19),
	rationale TEXT,
	id TEXT NOT NULL,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_Resolution_id" ON "Resolution" (id);

CREATE TABLE "Contradiction" (
	subject TEXT,
	predicate TEXT,
	state VARCHAR(19),
	id TEXT NOT NULL,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_Contradiction_id" ON "Contradiction" (id);

CREATE TABLE "ResearchTask" (
	task_type TEXT,
	target TEXT,
	closing_condition TEXT,
	resolved BOOLEAN,
	id TEXT NOT NULL,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_ResearchTask_id" ON "ResearchTask" (id);

CREATE TABLE "CoverageRecord" (
	subject TEXT,
	predicate TEXT,
	absence_kind VARCHAR(19),
	coverage_period TEXT,
	denominator_published BOOLEAN,
	id TEXT NOT NULL,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_CoverageRecord_id" ON "CoverageRecord" (id);

CREATE TABLE "Edge" (
	id TEXT NOT NULL,
	source TEXT NOT NULL,
	target TEXT NOT NULL,
	edge_type VARCHAR(22) NOT NULL,
	valid_from TEXT,
	valid_to TEXT,
	valid_from_kind VARCHAR(7),
	valid_to_kind VARCHAR(7),
	observed_at TEXT,
	asserted_by TEXT,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_Edge_id" ON "Edge" (id);

CREATE TABLE "AccessRelationship" (
	scope VARCHAR(10) NOT NULL,
	direction VARCHAR(6) NOT NULL,
	automaticity VARCHAR(22) NOT NULL,
	access_kind VARCHAR(17) NOT NULL,
	id TEXT NOT NULL,
	source TEXT NOT NULL,
	target TEXT NOT NULL,
	edge_type VARCHAR(22) NOT NULL,
	valid_from TEXT,
	valid_to TEXT,
	valid_from_kind VARCHAR(7),
	valid_to_kind VARCHAR(7),
	observed_at TEXT,
	asserted_by TEXT,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_AccessRelationship_id" ON "AccessRelationship" (id);

CREATE TABLE "IntegrationEdge" (
	data_kind TEXT NOT NULL,
	initiator TEXT,
	transport TEXT,
	granularity TEXT,
	data_comes_to_rest BOOLEAN,
	scope VARCHAR(10),
	consent_gate BOOLEAN,
	mechanism TEXT,
	terminable_by TEXT,
	termination_reason TEXT,
	applies_to_cohort VARCHAR(23),
	id TEXT NOT NULL,
	source TEXT NOT NULL,
	target TEXT NOT NULL,
	edge_type VARCHAR(22) NOT NULL,
	valid_from TEXT,
	valid_to TEXT,
	valid_from_kind VARCHAR(7),
	valid_to_kind VARCHAR(7),
	observed_at TEXT,
	asserted_by TEXT,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_IntegrationEdge_id" ON "IntegrationEdge" (id);

CREATE TABLE "RoleAssignment" (
	role VARCHAR(17) NOT NULL,
	party TEXT NOT NULL,
	over TEXT NOT NULL,
	id TEXT NOT NULL,
	source TEXT NOT NULL,
	target TEXT NOT NULL,
	edge_type VARCHAR(22) NOT NULL,
	valid_from TEXT,
	valid_to TEXT,
	valid_from_kind VARCHAR(7),
	valid_to_kind VARCHAR(7),
	observed_at TEXT,
	asserted_by TEXT,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_RoleAssignment_id" ON "RoleAssignment" (id);

CREATE TABLE "StructuralEdge" (
	id TEXT NOT NULL,
	source TEXT NOT NULL,
	target TEXT NOT NULL,
	edge_type VARCHAR(22) NOT NULL,
	valid_from TEXT,
	valid_to TEXT,
	valid_from_kind VARCHAR(7),
	valid_to_kind VARCHAR(7),
	observed_at TEXT,
	asserted_by TEXT,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_StructuralEdge_id" ON "StructuralEdge" (id);

CREATE TABLE "ProvenanceEdge" (
	id TEXT NOT NULL,
	source TEXT NOT NULL,
	target TEXT NOT NULL,
	edge_type VARCHAR(22) NOT NULL,
	valid_from TEXT,
	valid_to TEXT,
	valid_from_kind VARCHAR(7),
	valid_to_kind VARCHAR(7),
	observed_at TEXT,
	asserted_by TEXT,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_ProvenanceEdge_id" ON "ProvenanceEdge" (id);

CREATE TABLE "Organization" (
	canonical_name TEXT,
	organization_type VARCHAR(28),
	parent_organization TEXT,
	jurisdiction TEXT,
	government_domain TEXT,
	valid_from TEXT,
	valid_to TEXT,
	publication_review BOOLEAN,
	id TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(parent_organization) REFERENCES "Organization" (id),
	FOREIGN KEY(jurisdiction) REFERENCES "Jurisdiction" (id)
);
CREATE INDEX "ix_Organization_id" ON "Organization" (id);

CREATE TABLE "EvidenceArtifact" (
	published_by TEXT,
	artifact_type VARCHAR(29),
	integrity VARCHAR(2),
	id TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(published_by) REFERENCES "Source" (id)
);
CREATE INDEX "ix_EvidenceArtifact_id" ON "EvidenceArtifact" (id);

CREATE TABLE "Jurisdiction_parent_jurisdiction" (
	"Jurisdiction_id" TEXT,
	parent_jurisdiction_id TEXT,
	PRIMARY KEY ("Jurisdiction_id", parent_jurisdiction_id),
	FOREIGN KEY("Jurisdiction_id") REFERENCES "Jurisdiction" (id),
	FOREIGN KEY(parent_jurisdiction_id) REFERENCES "Jurisdiction" (id)
);
CREATE INDEX "ix_Jurisdiction_parent_jurisdiction_Jurisdiction_id" ON "Jurisdiction_parent_jurisdiction" ("Jurisdiction_id");
CREATE INDEX "ix_Jurisdiction_parent_jurisdiction_parent_jurisdiction_id" ON "Jurisdiction_parent_jurisdiction" (parent_jurisdiction_id);

CREATE TABLE "Jurisdiction_code_system" (
	"Jurisdiction_id" TEXT,
	code_system TEXT,
	PRIMARY KEY ("Jurisdiction_id", code_system),
	FOREIGN KEY("Jurisdiction_id") REFERENCES "Jurisdiction" (id)
);
CREATE INDEX "ix_Jurisdiction_code_system_Jurisdiction_id" ON "Jurisdiction_code_system" ("Jurisdiction_id");
CREATE INDEX "ix_Jurisdiction_code_system_code_system" ON "Jurisdiction_code_system" (code_system);

CREATE TABLE "Jurisdiction_code" (
	"Jurisdiction_id" TEXT,
	code TEXT,
	PRIMARY KEY ("Jurisdiction_id", code),
	FOREIGN KEY("Jurisdiction_id") REFERENCES "Jurisdiction" (id)
);
CREATE INDEX "ix_Jurisdiction_code_Jurisdiction_id" ON "Jurisdiction_code" ("Jurisdiction_id");
CREATE INDEX "ix_Jurisdiction_code_code" ON "Jurisdiction_code" (code);

CREATE TABLE "Jurisdiction_name" (
	"Jurisdiction_id" TEXT,
	name TEXT,
	PRIMARY KEY ("Jurisdiction_id", name),
	FOREIGN KEY("Jurisdiction_id") REFERENCES "Jurisdiction" (id)
);
CREATE INDEX "ix_Jurisdiction_name_Jurisdiction_id" ON "Jurisdiction_name" ("Jurisdiction_id");
CREATE INDEX "ix_Jurisdiction_name_name" ON "Jurisdiction_name" (name);

CREATE TABLE "Jurisdiction_name_lang" (
	"Jurisdiction_id" TEXT,
	name_lang TEXT,
	PRIMARY KEY ("Jurisdiction_id", name_lang),
	FOREIGN KEY("Jurisdiction_id") REFERENCES "Jurisdiction" (id)
);
CREATE INDEX "ix_Jurisdiction_name_lang_Jurisdiction_id" ON "Jurisdiction_name_lang" ("Jurisdiction_id");
CREATE INDEX "ix_Jurisdiction_name_lang_name_lang" ON "Jurisdiction_name_lang" (name_lang);

CREATE TABLE "AccountabilityEvent_technologies" (
	"AccountabilityEvent_id" TEXT,
	technologies TEXT,
	PRIMARY KEY ("AccountabilityEvent_id", technologies),
	FOREIGN KEY("AccountabilityEvent_id") REFERENCES "AccountabilityEvent" (id)
);
CREATE INDEX "ix_AccountabilityEvent_technologies_AccountabilityEvent_id" ON "AccountabilityEvent_technologies" ("AccountabilityEvent_id");
CREATE INDEX "ix_AccountabilityEvent_technologies_technologies" ON "AccountabilityEvent_technologies" (technologies);

CREATE TABLE "AccountabilityEvent_sources" (
	"AccountabilityEvent_id" TEXT,
	sources TEXT,
	PRIMARY KEY ("AccountabilityEvent_id", sources),
	FOREIGN KEY("AccountabilityEvent_id") REFERENCES "AccountabilityEvent" (id)
);
CREATE INDEX "ix_AccountabilityEvent_sources_AccountabilityEvent_id" ON "AccountabilityEvent_sources" ("AccountabilityEvent_id");
CREATE INDEX "ix_AccountabilityEvent_sources_sources" ON "AccountabilityEvent_sources" (sources);

CREATE TABLE "Edge_sources" (
	"Edge_id" TEXT,
	sources TEXT,
	PRIMARY KEY ("Edge_id", sources),
	FOREIGN KEY("Edge_id") REFERENCES "Edge" (id)
);
CREATE INDEX "ix_Edge_sources_Edge_id" ON "Edge_sources" ("Edge_id");
CREATE INDEX "ix_Edge_sources_sources" ON "Edge_sources" (sources);

CREATE TABLE "AccessRelationship_sources" (
	"AccessRelationship_id" TEXT,
	sources TEXT,
	PRIMARY KEY ("AccessRelationship_id", sources),
	FOREIGN KEY("AccessRelationship_id") REFERENCES "AccessRelationship" (id)
);
CREATE INDEX "ix_AccessRelationship_sources_AccessRelationship_id" ON "AccessRelationship_sources" ("AccessRelationship_id");
CREATE INDEX "ix_AccessRelationship_sources_sources" ON "AccessRelationship_sources" (sources);

CREATE TABLE "IntegrationEdge_sources" (
	"IntegrationEdge_id" TEXT,
	sources TEXT,
	PRIMARY KEY ("IntegrationEdge_id", sources),
	FOREIGN KEY("IntegrationEdge_id") REFERENCES "IntegrationEdge" (id)
);
CREATE INDEX "ix_IntegrationEdge_sources_IntegrationEdge_id" ON "IntegrationEdge_sources" ("IntegrationEdge_id");
CREATE INDEX "ix_IntegrationEdge_sources_sources" ON "IntegrationEdge_sources" (sources);

CREATE TABLE "RoleAssignment_sources" (
	"RoleAssignment_id" TEXT,
	sources TEXT,
	PRIMARY KEY ("RoleAssignment_id", sources),
	FOREIGN KEY("RoleAssignment_id") REFERENCES "RoleAssignment" (id)
);
CREATE INDEX "ix_RoleAssignment_sources_RoleAssignment_id" ON "RoleAssignment_sources" ("RoleAssignment_id");
CREATE INDEX "ix_RoleAssignment_sources_sources" ON "RoleAssignment_sources" (sources);

CREATE TABLE "StructuralEdge_sources" (
	"StructuralEdge_id" TEXT,
	sources TEXT,
	PRIMARY KEY ("StructuralEdge_id", sources),
	FOREIGN KEY("StructuralEdge_id") REFERENCES "StructuralEdge" (id)
);
CREATE INDEX "ix_StructuralEdge_sources_StructuralEdge_id" ON "StructuralEdge_sources" ("StructuralEdge_id");
CREATE INDEX "ix_StructuralEdge_sources_sources" ON "StructuralEdge_sources" (sources);

CREATE TABLE "ProvenanceEdge_sources" (
	"ProvenanceEdge_id" TEXT,
	sources TEXT,
	PRIMARY KEY ("ProvenanceEdge_id", sources),
	FOREIGN KEY("ProvenanceEdge_id") REFERENCES "ProvenanceEdge" (id)
);
CREATE INDEX "ix_ProvenanceEdge_sources_ProvenanceEdge_id" ON "ProvenanceEdge_sources" ("ProvenanceEdge_id");
CREATE INDEX "ix_ProvenanceEdge_sources_sources" ON "ProvenanceEdge_sources" (sources);

CREATE TABLE "Product" (
	product_name TEXT,
	vendor TEXT,
	product_status VARCHAR(12),
	successor_product TEXT,
	id TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(vendor) REFERENCES "Organization" (id),
	FOREIGN KEY(successor_product) REFERENCES "Product" (id)
);
CREATE INDEX "ix_Product_id" ON "Product" (id);

CREATE TABLE "Contract" (
	buyer TEXT,
	seller TEXT,
	amount NUMERIC,
	currency TEXT,
	signed_date TEXT,
	start_date TEXT,
	end_date TEXT,
	renewal_options TEXT,
	document TEXT,
	acquisition_channel VARCHAR(21),
	parent_cooperative_contract TEXT,
	amends_contract TEXT,
	id TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(buyer) REFERENCES "Organization" (id),
	FOREIGN KEY(seller) REFERENCES "Organization" (id),
	FOREIGN KEY(parent_cooperative_contract) REFERENCES "Contract" (id),
	FOREIGN KEY(amends_contract) REFERENCES "Contract" (id)
);
CREATE INDEX "ix_Contract_id" ON "Contract" (id);

CREATE TABLE "FundingInstrument" (
	funder TEXT,
	recipient TEXT,
	instrument_type VARCHAR(20),
	program_name TEXT,
	amount NUMERIC,
	award_date TEXT,
	period TEXT,
	conditions TEXT,
	federal_award_id TEXT,
	id TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(funder) REFERENCES "Organization" (id),
	FOREIGN KEY(recipient) REFERENCES "Organization" (id)
);
CREATE INDEX "ix_FundingInstrument_id" ON "FundingInstrument" (id);

CREATE TABLE "Policy" (
	policy_type VARCHAR(31),
	effective_from TEXT,
	effective_to TEXT,
	adopting_body TEXT,
	text TEXT,
	document TEXT,
	enforcement_mechanism VARCHAR(19),
	id TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(adopting_body) REFERENCES "Organization" (id)
);
CREATE INDEX "ix_Policy_id" ON "Policy" (id);

CREATE TABLE "LegalInstrument" (
	instrument_type VARCHAR(17),
	enacting_body TEXT,
	jurisdiction TEXT,
	citation TEXT,
	effective_from TEXT,
	effective_to TEXT,
	sunset_date TEXT,
	id TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(enacting_body) REFERENCES "Organization" (id),
	FOREIGN KEY(jurisdiction) REFERENCES "Jurisdiction" (id)
);
CREATE INDEX "ix_LegalInstrument_id" ON "LegalInstrument" (id);

CREATE TABLE "UsageAggregate" (
	searching_org TEXT NOT NULL,
	source_org TEXT NOT NULL,
	period TEXT,
	count INTEGER,
	search_scope VARCHAR(10),
	reason_category TEXT,
	reason_raw_value TEXT,
	audit_source_type VARCHAR(19),
	coverage_period TEXT,
	id TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(searching_org) REFERENCES "Organization" (id),
	FOREIGN KEY(source_org) REFERENCES "Organization" (id)
);
CREATE INDEX "ix_UsageAggregate_id" ON "UsageAggregate" (id);

CREATE TABLE "LegalProceeding" (
	court TEXT,
	docket_number TEXT,
	case_name TEXT,
	filed_date TEXT,
	disposition_date TEXT,
	posture VARCHAR(18),
	courtlistener_id TEXT,
	recap_id TEXT,
	id TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(court) REFERENCES "Organization" (id)
);
CREATE INDEX "ix_LegalProceeding_id" ON "LegalProceeding" (id);

CREATE TABLE "EvidenceCapture" (
	captures_artifact TEXT,
	captured_at DATETIME,
	content_digest TEXT,
	id TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(captures_artifact) REFERENCES "EvidenceArtifact" (id)
);
CREATE INDEX "ix_EvidenceCapture_id" ON "EvidenceCapture" (id);

CREATE TABLE "Organization_alias" (
	"Organization_id" TEXT,
	alias TEXT,
	PRIMARY KEY ("Organization_id", alias),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id)
);
CREATE INDEX "ix_Organization_alias_Organization_id" ON "Organization_alias" ("Organization_id");
CREATE INDEX "ix_Organization_alias_alias" ON "Organization_alias" (alias);

CREATE TABLE "Organization_alias_type" (
	"Organization_id" TEXT,
	alias_type VARCHAR(12),
	PRIMARY KEY ("Organization_id", alias_type),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id)
);
CREATE INDEX "ix_Organization_alias_type_Organization_id" ON "Organization_alias_type" ("Organization_id");
CREATE INDEX "ix_Organization_alias_type_alias_type" ON "Organization_alias_type" (alias_type);

CREATE TABLE "Organization_name_lang" (
	"Organization_id" TEXT,
	name_lang TEXT,
	PRIMARY KEY ("Organization_id", name_lang),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id)
);
CREATE INDEX "ix_Organization_name_lang_Organization_id" ON "Organization_name_lang" ("Organization_id");
CREATE INDEX "ix_Organization_name_lang_name_lang" ON "Organization_name_lang" (name_lang);

CREATE TABLE "Organization_identifier" (
	"Organization_id" TEXT,
	identifier TEXT,
	PRIMARY KEY ("Organization_id", identifier),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id)
);
CREATE INDEX "ix_Organization_identifier_Organization_id" ON "Organization_identifier" ("Organization_id");
CREATE INDEX "ix_Organization_identifier_identifier" ON "Organization_identifier" (identifier);

CREATE TABLE "Organization_identifier_system" (
	"Organization_id" TEXT,
	identifier_system TEXT,
	PRIMARY KEY ("Organization_id", identifier_system),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id)
);
CREATE INDEX "ix_Organization_identifier_system_Organization_id" ON "Organization_identifier_system" ("Organization_id");
CREATE INDEX "ix_Organization_identifier_system_identifier_system" ON "Organization_identifier_system" (identifier_system);

CREATE TABLE "Organization_address" (
	"Organization_id" TEXT,
	address TEXT,
	PRIMARY KEY ("Organization_id", address),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id)
);
CREATE INDEX "ix_Organization_address_Organization_id" ON "Organization_address" ("Organization_id");
CREATE INDEX "ix_Organization_address_address" ON "Organization_address" (address);

CREATE TABLE "Organization_succession" (
	"Organization_id" TEXT,
	succession_id TEXT,
	PRIMARY KEY ("Organization_id", succession_id),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id),
	FOREIGN KEY(succession_id) REFERENCES "Organization" (id)
);
CREATE INDEX "ix_Organization_succession_Organization_id" ON "Organization_succession" ("Organization_id");
CREATE INDEX "ix_Organization_succession_succession_id" ON "Organization_succession" (succession_id);

CREATE TABLE "Organization_succession_kind" (
	"Organization_id" TEXT,
	succession_kind VARCHAR(12),
	PRIMARY KEY ("Organization_id", succession_kind),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id)
);
CREATE INDEX "ix_Organization_succession_kind_Organization_id" ON "Organization_succession_kind" ("Organization_id");
CREATE INDEX "ix_Organization_succession_kind_succession_kind" ON "Organization_succession_kind" (succession_kind);

CREATE TABLE "AccountabilityEvent_organizations" (
	"AccountabilityEvent_id" TEXT,
	organizations_id TEXT,
	PRIMARY KEY ("AccountabilityEvent_id", organizations_id),
	FOREIGN KEY("AccountabilityEvent_id") REFERENCES "AccountabilityEvent" (id),
	FOREIGN KEY(organizations_id) REFERENCES "Organization" (id)
);
CREATE INDEX "ix_AccountabilityEvent_organizations_AccountabilityEvent_id" ON "AccountabilityEvent_organizations" ("AccountabilityEvent_id");
CREATE INDEX "ix_AccountabilityEvent_organizations_organizations_id" ON "AccountabilityEvent_organizations" (organizations_id);

CREATE TABLE "Deployment" (
	deploying_organization TEXT,
	product TEXT,
	vendor TEXT,
	procurement_state VARCHAR(21),
	physical_state VARCHAR(18),
	operational_state VARCHAR(10),
	authorization_state VARCHAR(19),
	litigation_hold BOOLEAN,
	jurisdiction TEXT,
	contracted_device_count INTEGER,
	installed_device_count INTEGER,
	active_device_count INTEGER,
	proposed_at TEXT,
	approved_at TEXT,
	contracted_at TEXT,
	active_from TEXT,
	inactive_at TEXT,
	id TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(deploying_organization) REFERENCES "Organization" (id),
	FOREIGN KEY(product) REFERENCES "Product" (id),
	FOREIGN KEY(vendor) REFERENCES "Organization" (id),
	FOREIGN KEY(jurisdiction) REFERENCES "Jurisdiction" (id)
);
CREATE INDEX "ix_Deployment_id" ON "Deployment" (id);

CREATE TABLE "DataSystem" (
	operator TEXT,
	vendor TEXT,
	product TEXT,
	retention TEXT,
	system_scope VARCHAR(26),
	holds_data_collected_by TEXT,
	id TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(operator) REFERENCES "Organization" (id),
	FOREIGN KEY(vendor) REFERENCES "Organization" (id),
	FOREIGN KEY(product) REFERENCES "Product" (id),
	FOREIGN KEY(holds_data_collected_by) REFERENCES "Organization" (id)
);
CREATE INDEX "ix_DataSystem_id" ON "DataSystem" (id);

CREATE TABLE "RecordsRequest" (
	requesting_party TEXT,
	target_agency TEXT,
	request_text TEXT,
	filed_date TEXT,
	response_date TEXT,
	response_status VARCHAR(21),
	statutory_basis TEXT,
	platform VARCHAR(12),
	external_id TEXT,
	id TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(requesting_party) REFERENCES "Organization" (id),
	FOREIGN KEY(target_agency) REFERENCES "Organization" (id),
	FOREIGN KEY(statutory_basis) REFERENCES "LegalInstrument" (id)
);
CREATE INDEX "ix_RecordsRequest_id" ON "RecordsRequest" (id);

CREATE TABLE "Extraction" (
	from_capture TEXT,
	extraction_method TEXT,
	id TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(from_capture) REFERENCES "EvidenceCapture" (id)
);
CREATE INDEX "ix_Extraction_id" ON "Extraction" (id);

CREATE TABLE "Product_implements_technology" (
	"Product_id" TEXT,
	implements_technology TEXT,
	PRIMARY KEY ("Product_id", implements_technology),
	FOREIGN KEY("Product_id") REFERENCES "Product" (id)
);
CREATE INDEX "ix_Product_implements_technology_Product_id" ON "Product_implements_technology" ("Product_id");
CREATE INDEX "ix_Product_implements_technology_implements_technology" ON "Product_implements_technology" (implements_technology);

CREATE TABLE "Product_can_offer_capability" (
	"Product_id" TEXT,
	can_offer_capability TEXT,
	PRIMARY KEY ("Product_id", can_offer_capability),
	FOREIGN KEY("Product_id") REFERENCES "Product" (id)
);
CREATE INDEX "ix_Product_can_offer_capability_Product_id" ON "Product_can_offer_capability" ("Product_id");
CREATE INDEX "ix_Product_can_offer_capability_can_offer_capability" ON "Product_can_offer_capability" (can_offer_capability);

CREATE TABLE "Contract_products" (
	"Contract_id" TEXT,
	products_id TEXT,
	PRIMARY KEY ("Contract_id", products_id),
	FOREIGN KEY("Contract_id") REFERENCES "Contract" (id),
	FOREIGN KEY(products_id) REFERENCES "Product" (id)
);
CREATE INDEX "ix_Contract_products_Contract_id" ON "Contract_products" ("Contract_id");
CREATE INDEX "ix_Contract_products_products_id" ON "Contract_products" (products_id);

CREATE TABLE "Contract_quantities" (
	"Contract_id" TEXT,
	quantities INTEGER,
	PRIMARY KEY ("Contract_id", quantities),
	FOREIGN KEY("Contract_id") REFERENCES "Contract" (id)
);
CREATE INDEX "ix_Contract_quantities_Contract_id" ON "Contract_quantities" ("Contract_id");
CREATE INDEX "ix_Contract_quantities_quantities" ON "Contract_quantities" (quantities);

CREATE TABLE "Policy_applies_to" (
	"Policy_id" TEXT,
	applies_to TEXT,
	PRIMARY KEY ("Policy_id", applies_to),
	FOREIGN KEY("Policy_id") REFERENCES "Policy" (id)
);
CREATE INDEX "ix_Policy_applies_to_Policy_id" ON "Policy_applies_to" ("Policy_id");
CREATE INDEX "ix_Policy_applies_to_applies_to" ON "Policy_applies_to" (applies_to);

CREATE TABLE "LegalInstrument_constrains_technology" (
	"LegalInstrument_id" TEXT,
	constrains_technology TEXT,
	PRIMARY KEY ("LegalInstrument_id", constrains_technology),
	FOREIGN KEY("LegalInstrument_id") REFERENCES "LegalInstrument" (id)
);
CREATE INDEX "ix_LegalInstrument_constrains_technology_LegalInstrument_id" ON "LegalInstrument_constrains_technology" ("LegalInstrument_id");
CREATE INDEX "ix_LegalInstrument_constrains_technology_constrains_technology" ON "LegalInstrument_constrains_technology" (constrains_technology);

CREATE TABLE "LegalInstrument_constrains_capability" (
	"LegalInstrument_id" TEXT,
	constrains_capability TEXT,
	PRIMARY KEY ("LegalInstrument_id", constrains_capability),
	FOREIGN KEY("LegalInstrument_id") REFERENCES "LegalInstrument" (id)
);
CREATE INDEX "ix_LegalInstrument_constrains_capability_LegalInstrument_id" ON "LegalInstrument_constrains_capability" ("LegalInstrument_id");
CREATE INDEX "ix_LegalInstrument_constrains_capability_constrains_capability" ON "LegalInstrument_constrains_capability" (constrains_capability);

CREATE TABLE "LegalInstrument_requires_authorization_of" (
	"LegalInstrument_id" TEXT,
	requires_authorization_of TEXT,
	PRIMARY KEY ("LegalInstrument_id", requires_authorization_of),
	FOREIGN KEY("LegalInstrument_id") REFERENCES "LegalInstrument" (id)
);
CREATE INDEX "ix_LegalInstrument_requires_authorization_of_LegalInstrument_id" ON "LegalInstrument_requires_authorization_of" ("LegalInstrument_id");
CREATE INDEX "ix_LegalInstrument_requires_authorization_of_requires_authorization_of" ON "LegalInstrument_requires_authorization_of" (requires_authorization_of);

CREATE TABLE "LegalProceeding_parties" (
	"LegalProceeding_id" TEXT,
	parties TEXT,
	PRIMARY KEY ("LegalProceeding_id", parties),
	FOREIGN KEY("LegalProceeding_id") REFERENCES "LegalProceeding" (id)
);
CREATE INDEX "ix_LegalProceeding_parties_LegalProceeding_id" ON "LegalProceeding_parties" ("LegalProceeding_id");
CREATE INDEX "ix_LegalProceeding_parties_parties" ON "LegalProceeding_parties" (parties);

CREATE TABLE "LegalProceeding_party_role" (
	"LegalProceeding_id" TEXT,
	party_role TEXT,
	PRIMARY KEY ("LegalProceeding_id", party_role),
	FOREIGN KEY("LegalProceeding_id") REFERENCES "LegalProceeding" (id)
);
CREATE INDEX "ix_LegalProceeding_party_role_LegalProceeding_id" ON "LegalProceeding_party_role" ("LegalProceeding_id");
CREATE INDEX "ix_LegalProceeding_party_role_party_role" ON "LegalProceeding_party_role" (party_role);

CREATE TABLE "PhysicalAsset" (
	asset_type TEXT,
	geometry TEXT,
	mobility VARCHAR(15),
	manufacturer TEXT,
	model TEXT,
	deployment TEXT,
	first_observed DATETIME,
	last_observed DATETIME,
	osm_version INTEGER,
	sensitivity_tier TEXT,
	confirmation_status VARCHAR(19),
	id TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(manufacturer) REFERENCES "Organization" (id),
	FOREIGN KEY(deployment) REFERENCES "Deployment" (id)
);
CREATE INDEX "ix_PhysicalAsset_id" ON "PhysicalAsset" (id);

CREATE TABLE "ConfigurationState" (
	deployment TEXT,
	retention_days TEXT,
	retention_bucket TEXT,
	state_lookup_enabled BOOLEAN,
	national_lookup_enabled BOOLEAN,
	federal_sharing_enabled BOOLEAN,
	audit_case_code_required BOOLEAN,
	observed_via VARCHAR(17),
	id TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(deployment) REFERENCES "Deployment" (id)
);
CREATE INDEX "ix_ConfigurationState_id" ON "ConfigurationState" (id);

CREATE TABLE "Deployment_technology" (
	"Deployment_id" TEXT,
	technology TEXT,
	PRIMARY KEY ("Deployment_id", technology),
	FOREIGN KEY("Deployment_id") REFERENCES "Deployment" (id)
);
CREATE INDEX "ix_Deployment_technology_Deployment_id" ON "Deployment_technology" ("Deployment_id");
CREATE INDEX "ix_Deployment_technology_technology" ON "Deployment_technology" (technology);

CREATE TABLE "Deployment_actually_provides_capability" (
	"Deployment_id" TEXT,
	actually_provides_capability TEXT,
	PRIMARY KEY ("Deployment_id", actually_provides_capability),
	FOREIGN KEY("Deployment_id") REFERENCES "Deployment" (id)
);
CREATE INDEX "ix_Deployment_actually_provides_capability_Deployment_id" ON "Deployment_actually_provides_capability" ("Deployment_id");
CREATE INDEX "ix_Deployment_actually_provides_capability_actually_provides_capability" ON "Deployment_actually_provides_capability" (actually_provides_capability);

CREATE TABLE "DataSystem_data_types" (
	"DataSystem_id" TEXT,
	data_types TEXT,
	PRIMARY KEY ("DataSystem_id", data_types),
	FOREIGN KEY("DataSystem_id") REFERENCES "DataSystem" (id)
);
CREATE INDEX "ix_DataSystem_data_types_DataSystem_id" ON "DataSystem_data_types" ("DataSystem_id");
CREATE INDEX "ix_DataSystem_data_types_data_types" ON "DataSystem_data_types" (data_types);

CREATE TABLE "AccountabilityEvent_deployments" (
	"AccountabilityEvent_id" TEXT,
	deployments_id TEXT,
	PRIMARY KEY ("AccountabilityEvent_id", deployments_id),
	FOREIGN KEY("AccountabilityEvent_id") REFERENCES "AccountabilityEvent" (id),
	FOREIGN KEY(deployments_id) REFERENCES "Deployment" (id)
);
CREATE INDEX "ix_AccountabilityEvent_deployments_AccountabilityEvent_id" ON "AccountabilityEvent_deployments" ("AccountabilityEvent_id");
CREATE INDEX "ix_AccountabilityEvent_deployments_deployments_id" ON "AccountabilityEvent_deployments" (deployments_id);

CREATE TABLE "RecordsRequest_released_documents" (
	"RecordsRequest_id" TEXT,
	released_documents TEXT,
	PRIMARY KEY ("RecordsRequest_id", released_documents),
	FOREIGN KEY("RecordsRequest_id") REFERENCES "RecordsRequest" (id)
);
CREATE INDEX "ix_RecordsRequest_released_documents_RecordsRequest_id" ON "RecordsRequest_released_documents" ("RecordsRequest_id");
CREATE INDEX "ix_RecordsRequest_released_documents_released_documents" ON "RecordsRequest_released_documents" (released_documents);

CREATE TABLE "PhysicalAsset_upstream_id" (
	"PhysicalAsset_id" TEXT,
	upstream_id TEXT,
	PRIMARY KEY ("PhysicalAsset_id", upstream_id),
	FOREIGN KEY("PhysicalAsset_id") REFERENCES "PhysicalAsset" (id)
);
CREATE INDEX "ix_PhysicalAsset_upstream_id_PhysicalAsset_id" ON "PhysicalAsset_upstream_id" ("PhysicalAsset_id");
CREATE INDEX "ix_PhysicalAsset_upstream_id_upstream_id" ON "PhysicalAsset_upstream_id" (upstream_id);

CREATE TABLE "ConfigurationState_subscribed_hotlist_topic" (
	"ConfigurationState_id" TEXT,
	subscribed_hotlist_topic TEXT,
	PRIMARY KEY ("ConfigurationState_id", subscribed_hotlist_topic),
	FOREIGN KEY("ConfigurationState_id") REFERENCES "ConfigurationState" (id)
);
CREATE INDEX "ix_ConfigurationState_subscribed_hotlist_topic_ConfigurationState_id" ON "ConfigurationState_subscribed_hotlist_topic" ("ConfigurationState_id");
CREATE INDEX "ix_ConfigurationState_subscribed_hotlist_topic_subscribed_hotlist_topic" ON "ConfigurationState_subscribed_hotlist_topic" (subscribed_hotlist_topic);

CREATE TABLE "ConfigurationState_sharing_partner" (
	"ConfigurationState_id" TEXT,
	sharing_partner_id TEXT,
	PRIMARY KEY ("ConfigurationState_id", sharing_partner_id),
	FOREIGN KEY("ConfigurationState_id") REFERENCES "ConfigurationState" (id),
	FOREIGN KEY(sharing_partner_id) REFERENCES "Organization" (id)
);
CREATE INDEX "ix_ConfigurationState_sharing_partner_ConfigurationState_id" ON "ConfigurationState_sharing_partner" ("ConfigurationState_id");
CREATE INDEX "ix_ConfigurationState_sharing_partner_sharing_partner_id" ON "ConfigurationState_sharing_partner" (sharing_partner_id);

CREATE TABLE "ConfigurationState_offense_category_filter" (
	"ConfigurationState_id" TEXT,
	offense_category_filter TEXT,
	PRIMARY KEY ("ConfigurationState_id", offense_category_filter),
	FOREIGN KEY("ConfigurationState_id") REFERENCES "ConfigurationState" (id)
);
CREATE INDEX "ix_ConfigurationState_offense_category_filter_ConfigurationState_id" ON "ConfigurationState_offense_category_filter" ("ConfigurationState_id");
CREATE INDEX "ix_ConfigurationState_offense_category_filter_offense_category_filter" ON "ConfigurationState_offense_category_filter" (offense_category_filter);

CREATE TABLE "ConfigurationState_live_stream_permitted_to" (
	"ConfigurationState_id" TEXT,
	live_stream_permitted_to TEXT,
	PRIMARY KEY ("ConfigurationState_id", live_stream_permitted_to),
	FOREIGN KEY("ConfigurationState_id") REFERENCES "ConfigurationState" (id)
);
CREATE INDEX "ix_ConfigurationState_live_stream_permitted_to_ConfigurationState_id" ON "ConfigurationState_live_stream_permitted_to" ("ConfigurationState_id");
CREATE INDEX "ix_ConfigurationState_live_stream_permitted_to_live_stream_permitted_to" ON "ConfigurationState_live_stream_permitted_to" (live_stream_permitted_to);

CREATE TABLE "ConfigurationState_third_party_integration" (
	"ConfigurationState_id" TEXT,
	third_party_integration TEXT,
	PRIMARY KEY ("ConfigurationState_id", third_party_integration),
	FOREIGN KEY("ConfigurationState_id") REFERENCES "ConfigurationState" (id)
);
CREATE INDEX "ix_ConfigurationState_third_party_integration_ConfigurationState_id" ON "ConfigurationState_third_party_integration" ("ConfigurationState_id");
CREATE INDEX "ix_ConfigurationState_third_party_integration_third_party_integration" ON "ConfigurationState_third_party_integration" (third_party_integration);
