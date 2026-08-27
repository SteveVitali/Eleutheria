from __future__ import annotations

import re
import sys
from datetime import (
    date,
    datetime,
    time
)
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Literal,
    Optional,
    Union
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer
)


metamodel_version = "1.11.0"
version = "1.0.0"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias = True,
        validate_by_name = True,
        validate_assignment = True,
        validate_default = True,
        extra = "forbid",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
    )





class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key:str):
        return getattr(self.root, key)

    def __getitem__(self, key:str):
        return self.root[key]

    def __setitem__(self, key:str, value):
        self.root[key] = value

    def __contains__(self, key:str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta({'default_prefix': 'sig',
     'default_range': 'string',
     'description': 'The canonical SIG ontology: entities (§11), relationships '
                    '(§12), and the structural controlled vocabularies (§13). One '
                    'LinkML source generates every downstream form (§20.1).',
     'id': 'https://ontology.sig-project.org/schema/sig',
     'imports': ['linkml:types', 'common', 'entities', 'edges'],
     'license': 'Apache-2.0',
     'name': 'sig',
     'prefixes': {'dcterms': {'prefix_prefix': 'dcterms',
                              'prefix_reference': 'http://purl.org/dc/terms/'},
                  'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'},
                  'sig': {'prefix_prefix': 'sig',
                          'prefix_reference': 'https://ontology.sig-project.org/schema/'},
                  'skos': {'prefix_prefix': 'skos',
                           'prefix_reference': 'http://www.w3.org/2004/02/skos/core#'},
                  'xsd': {'prefix_prefix': 'xsd',
                          'prefix_reference': 'http://www.w3.org/2001/XMLSchema#'}},
     'source_file': 'ontology/src/ontology/schema/sig.yaml',
     'title': 'Surveillance Infrastructure Graph ontology'} )

class TemporalBoundKind(str, Enum):
    """
    How a temporal bound is known (§9.5).
    """
    known = "known"
    """
    A specific known bound.
    """
    unknown = "unknown"
    """
    Bound exists but is not known.
    """
    ongoing = "ongoing"
    """
    The fact is still in force (open interval).
    """


class SourceReliability(str, Enum):
    """
    Reliability R of the publisher, not the claim (§10.4).
    """
    R1 = "R1"
    """
    Highest reliability.
    """
    R2 = "R2"
    R3 = "R3"
    R4 = "R4"
    R5 = "R5"
    R6 = "R6"
    """
    Lowest reliability.
    """


class ClaimDirectness(str, Enum):
    """
    Directness D from the (genre × predicate) matrix (§10.5).
    """
    D1 = "D1"
    """
    Authoritative record of the fact itself.
    """
    D2 = "D2"
    """
    First-party report of the fact.
    """
    D3 = "D3"
    """
    Secondhand report or close proxy.
    """
    D4 = "D4"
    """
    Establishes a related fact; short inference.
    """
    D5 = "D5"
    """
    Bears on target only through a modelling assumption.
    """
    D6 = "D6"
    """
    Non-probative for this predicate — excluded from the admissible set.
    """


class ArtifactIntegrity(str, Enum):
    """
    Integrity I of the artifact (§10.6).
    """
    I1 = "I1"
    I2 = "I2"
    I3 = "I3"


class Currency(str, Enum):
    """
    Currency C derived at query time from volatility half-life (§28.3).
    """
    C1 = "C1"
    """
    CURRENT.
    """
    C2 = "C2"
    """
    AGING.
    """
    C3 = "C3"
    """
    STALE.
    """
    C4 = "C4"
    """
    HISTORICAL.
    """


class WeightClass(str, Enum):
    """
    Composed weight class W (§10.6).
    """
    W0 = "W0"
    W1 = "W1"
    W2 = "W2"
    W3 = "W3"
    W4 = "W4"


class EvidenceRole(str, Enum):
    """
    The role a piece of evidence plays for a claim (§13.3).
    """
    establishes = "establishes"
    corroborates = "corroborates"
    contextualizes = "contextualizes"
    contradicts = "contradicts"
    supersedes_basis = "supersedes_basis"
    attests_absence = "attests_absence"


class EpistemicStatus(str, Enum):
    """
    Required epistemic status of an accountability event (§11.17, SIG-ONTO-038).
    """
    alleged = "alleged"
    reported = "reported"
    confirmed = "confirmed"
    adjudicated = "adjudicated"
    policy_action = "policy_action"
    vendor_statement = "vendor_statement"
    disputed = "disputed"
    retracted = "retracted"


class AbsenceKind(str, Enum):
    """
    How an absence is known — negative space is queryable (§9.5).
    """
    not_researched = "not_researched"
    searched_not_found = "searched_not_found"
    evidence_of_absence = "evidence_of_absence"
    not_applicable = "not_applicable"


class ContradictionState(str, Enum):
    """
    State of a contradiction (§31).
    """
    uncontested = "uncontested"
    resolved_conflict = "resolved_conflict"
    unresolved_conflict = "unresolved_conflict"
    insufficient = "insufficient"


class ValueKind(str, Enum):
    """
    RDF-style value kind — known value, unknown value, or no value (§9.5).
    """
    value = "value"
    somevalue = "somevalue"
    """
    A value exists but is unknown.
    """
    novalue = "novalue"
    """
    There is provably no value.
    """


class PredicateVolatility(str, Enum):
    """
    Volatility class governing currency decay (§28.3, SIG-RECON-008).
    """
    IMMUTABLE = "IMMUTABLE"
    """
    Never changes; half-life infinite; always C1.
    """
    GLACIAL = "GLACIAL"
    SLOW = "SLOW"
    MODERATE = "MODERATE"
    FAST = "FAST"
    VOLATILE = "VOLATILE"


class ResolutionStrategy(str, Enum):
    """
    Per-predicate resolution strategy (§28.4, SIG-RECON-012).
    """
    latest_observation_wins = "latest_observation_wins"
    authoritative_source_wins = "authoritative_source_wins"
    interval_union = "interval_union"
    interval_intersection = "interval_intersection"
    max_support = "max_support"
    never_resolve = "never_resolve"
    """
    Recorded but deliberately not adjudicated (§12.4 contested facts).
    """


class SkosMappingRelation(str, Enum):
    """
    SKOS mapping relations for crosswalks (§20.3).
    """
    exactMatch = "exactMatch"
    closeMatch = "closeMatch"
    broadMatch = "broadMatch"
    narrowMatch = "narrowMatch"
    relatedMatch = "relatedMatch"


class ProcurementState(str, Enum):
    """
    Track 1 — procurement (§13.4). `unknown` is admissible and default (SIG-ONTO-063).
    """
    unknown = "unknown"
    proposed = "proposed"
    rfp_issued = "rfp_issued"
    awarded = "awarded"
    contracted = "contracted"
    cooperative_piggyback = "cooperative_piggyback"
    bundle_included = "bundle_included"
    free_trial = "free_trial"
    donated = "donated"
    third_party_funded = "third_party_funded"
    grant_funded_pending = "grant_funded_pending"
    renewed = "renewed"
    nonrenewed = "nonrenewed"
    canceled = "canceled"
    rejected = "rejected"


class PhysicalState(str, Enum):
    """
    Track 2 — physical (§13.4). `replaced` is deliberately NOT here (SIG-ONTO-062).
    """
    unknown = "unknown"
    not_installed = "not_installed"
    installation = "installation"
    installed = "installed"
    installed_inactive = "installed_inactive"
    decommissioning = "decommissioning"
    removed = "removed"
    destroyed_or_lost = "destroyed_or_lost"


class OperationalState(str, Enum):
    """
    Track 3 — operational (§13.4).
    """
    unknown = "unknown"
    inactive = "inactive"
    pilot = "pilot"
    active = "active"
    expanded = "expanded"
    restricted = "restricted"
    suspended = "suspended"


class AuthorizationState(str, Enum):
    """
    Track 4 — authorization (§13.4).
    """
    unknown = "unknown"
    unauthorized = "unauthorized"
    approval_pending = "approval_pending"
    authorized = "authorized"
    authorized_expired = "authorized_expired"
    moratorium = "moratorium"
    sunset_by_ordinance = "sunset_by_ordinance"


class Role(str, Enum):
    """
    The fourteen separately-modelled roles (§12.4). Never collapsed to owner/operator.
    """
    owner = "owner"
    """
    Who could lawfully remove it?
    """
    purchaser = "purchaser"
    """
    Whose money bought it?
    """
    funder = "funder"
    """
    Whose grant/appropriation supplied that money?
    """
    installer = "installer"
    """
    Who physically mounted it?
    """
    host = "host"
    """
    Whose pole/wall/right-of-way is it on?
    """
    operator = "operator"
    """
    Who aims, tunes, and responds to it?
    """
    data_controller = "data_controller"
    """
    Who can change the retention setting?
    """
    data_processor = "data_processor"
    """
    Could they lawfully use it for their own purposes?
    """
    platform_provider = "platform_provider"
    """
    Who would the capability disappear with?
    """
    accessor_read = "accessor_read"
    """
    Can they view without initiating a search?
    """
    searcher = "searcher"
    """
    Can they execute queries against the corpus?
    """
    alert_recipient = "alert_recipient"
    """
    Do they get notified?
    """
    auditor = "auditor"
    """
    Can they see the search log as of right?
    """
    regulator = "regulator"
    """
    Can they prohibit it?
    """


class AccessKind(str, Enum):
    """
    The three edge types that MUST NEVER be merged (§12.2).
    """
    configured_access = "configured_access"
    """
    The system is set up to permit it.
    """
    observed_use = "observed_use"
    """
    Someone actually did it.
    """
    declared_policy = "declared_policy"
    """
    Someone said it is permitted or forbidden.
    """


class Automaticity(str, Enum):
    """
    How access is triggered (§12.5).
    """
    automatic = "automatic"
    manual_approval = "manual_approval"
    per_incident_consent = "per_incident_consent"
    legal_process_required = "legal_process_required"


class CapabilityScope(str, Enum):
    """
    Capability scope values (§11.6, §13.2).
    """
    own = "own"
    partner = "partner"
    state = "state"
    region = "region"
    national = "national"
    commercial = "commercial"
    subject = "subject"


class CohortApplicability(str, Enum):
    """
    Which cohort an integration termination applies to (§12.3, SIG-ONTO-046).
    """
    all = "all"
    new_customers_only = "new_customers_only"
    existing_customers_only = "existing_customers_only"


class Mobility(str, Enum):
    """
    Physical asset mobility (§11.8).
    """
    fixed = "fixed"
    redeployable = "redeployable"
    vehicle_mounted = "vehicle_mounted"
    airborne = "airborne"
    handheld = "handheld"
    unknown = "unknown"


class ConfirmationStatus(str, Enum):
    """
    How a physical asset was confirmed (§11.8).
    """
    field_confirmed = "field_confirmed"
    imagery_confirmed = "imagery_confirmed"
    record_confirmed = "record_confirmed"
    reported_unverified = "reported_unverified"
    candidate = "candidate"


class DetectionMethod(str, Enum):
    """
    How a candidate asset was detected (§11.9, SIG-ONTO-030).
    """
    rf_oui_match = "rf_oui_match"
    wigle_observation = "wigle_observation"
    imagery_detection = "imagery_detection"
    contributor_report = "contributor_report"
    model_inference = "model_inference"
    count_gap_inference = "count_gap_inference"


class PromotionStatus(str, Enum):
    """
    Candidate-asset promotion lifecycle (§11.9, §43.5).
    """
    unreviewed = "unreviewed"
    corroborated = "corroborated"
    promoted = "promoted"
    rejected = "rejected"
    suppressed_by_policy = "suppressed_by_policy"


class ProductStatus(str, Enum):
    """
    Product lifecycle status (§11.4).
    """
    announced = "announced"
    available = "available"
    end_of_sale = "end_of_sale"
    end_of_life = "end_of_life"
    renamed = "renamed"
    discontinued = "discontinued"


class SystemScope(str, Enum):
    """
    DataSystem scope (§11.10).
    """
    agency_local = "agency_local"
    vendor_cloud_single_tenant = "vendor_cloud_single_tenant"
    vendor_cloud_shared = "vendor_cloud_shared"
    state = "state"
    regional = "regional"
    federal = "federal"
    commercial = "commercial"


class AcquisitionChannel(str, Enum):
    """
    Contract acquisition channel (§11.11, SIG-ONTO-032).
    """
    direct_award = "direct_award"
    competitive_rfp = "competitive_rfp"
    sole_source = "sole_source"
    cooperative_piggyback = "cooperative_piggyback"
    bundle_inclusion = "bundle_inclusion"
    free_trial = "free_trial"
    donation = "donation"
    grant_funded = "grant_funded"


class FundingInstrumentType(str, Enum):
    """
    Funding instrument type (§11.12).
    """
    federal_grant = "federal_grant"
    state_grant = "state_grant"
    private_donation = "private_donation"
    bid_assessment = "bid_assessment"
    hoa_assessment = "hoa_assessment"
    foundation_grant = "foundation_grant"
    asset_forfeiture = "asset_forfeiture"
    vendor_provided_free = "vendor_provided_free"


class PolicyType(str, Enum):
    """
    Policy type (§11.13).
    """
    retention = "retention"
    acceptable_use = "acceptable_use"
    warrant_requirement = "warrant_requirement"
    immigration_restriction = "immigration_restriction"
    reproductive_health_restriction = "reproductive_health_restriction"
    audit_requirement = "audit_requirement"
    external_sharing = "external_sharing"
    data_minimization = "data_minimization"
    oversight_reporting = "oversight_reporting"
    sunset = "sunset"


class EnforcementMechanism(str, Enum):
    """
    Policy enforcement mechanism (§11.13).
    """
    none_stated = "none_stated"
    internal_discipline = "internal_discipline"
    audit = "audit"
    external_oversight = "external_oversight"
    statutory_penalty = "statutory_penalty"
    contractual = "contractual"


class ObservedVia(str, Enum):
    """
    How a configuration state was observed (§11.15, SIG-ONTO-036).
    """
    portal = "portal"
    config_screenshot = "config_screenshot"
    foia_export = "foia_export"
    vendor_statement = "vendor_statement"
    contract_term = "contract_term"


class LegalInstrumentType(str, Enum):
    """
    Legal instrument type, internationalized (§11.14, §13.7).
    """
    statute = "statute"
    ordinance = "ordinance"
    regulation = "regulation"
    executive_order = "executive_order"
    court_order = "court_order"
    consent_decree = "consent_decree"
    dpa_decision = "dpa_decision"
    code_of_practice = "code_of_practice"
    prefectoral_order = "prefectoral_order"
    """
    e.g. a French arrêté préfectoral.
    """
    directive = "directive"


class AccountabilityEventType(str, Enum):
    """
    Accountability event type (§11.17).
    """
    false_stop = "false_stop"
    wrongful_arrest = "wrongful_arrest"
    alleged_stalking_misuse = "alleged_stalking_misuse"
    immigration_search_controversy = "immigration_search_controversy"
    policy_violation = "policy_violation"
    data_breach = "data_breach"
    security_finding = "security_finding"
    moratorium = "moratorium"
    contract_cancellation = "contract_cancellation"
    public_hearing = "public_hearing"
    audit_finding = "audit_finding"
    regulatory_action = "regulatory_action"
    vendor_statement = "vendor_statement"
    local_regulation = "local_regulation"


class ProceedingPosture(str, Enum):
    """
    Legal proceeding posture (§11.18).
    """
    filed = "filed"
    pending = "pending"
    dismissed = "dismissed"
    settled = "settled"
    judgment_plaintiff = "judgment_plaintiff"
    judgment_defendant = "judgment_defendant"
    on_appeal = "on_appeal"
    consent_decree = "consent_decree"
    class_certified = "class_certified"


class AuditSourceType(str, Enum):
    """
    Audit source type — these are NOT interchangeable (§11.16, §23.7).
    """
    organization_audit = "organization_audit"
    network_audit = "network_audit"
    portal_public_audit = "portal_public_audit"
    event_log = "event_log"


class RecordsResponseStatus(str, Enum):
    """
    Records-request response status (§11.19). no_responsive_records is a positive finding (SIG-ONTO-040).
    """
    draft = "draft"
    filed = "filed"
    acknowledged = "acknowledged"
    partially_fulfilled = "partially_fulfilled"
    fulfilled = "fulfilled"
    denied = "denied"
    appealed = "appealed"
    abandoned = "abandoned"
    no_responsive_records = "no_responsive_records"
    fee_demanded = "fee_demanded"


class RecordsPlatform(str, Enum):
    """
    Records-request platform (§11.19).
    """
    muckrock = "muckrock"
    nextrequest = "nextrequest"
    govqa = "govqa"
    justfoia = "justfoia"
    direct_email = "direct_email"
    portal = "portal"
    paper = "paper"


class AliasType(str, Enum):
    """
    Organization alias qualifier (§11.2).
    """
    abbreviation = "abbreviation"
    former_name = "former_name"
    slug = "slug"
    misspelling = "misspelling"
    local_usage = "local_usage"
    legal_name = "legal_name"
    dba = "dba"


class SuccessionKind(str, Enum):
    """
    Temporal identity succession qualifier (§14.5).
    """
    merged_into = "merged_into"
    split_from = "split_from"
    renamed_from = "renamed_from"
    absorbed_by = "absorbed_by"


class JurisdictionType(str, Enum):
    """
    Jurisdiction type, namespaced per country (§11.1, §13.7).
    """
    country = "country"
    state_province = "state_province"
    county = "county"
    municipality = "municipality"
    township = "township"
    special_district = "special_district"
    school_district = "school_district"
    tribal = "tribal"
    federal_region = "federal_region"
    judicial_district = "judicial_district"
    metropolitan_area = "metropolitan_area"
    neighborhood = "neighborhood"
    unincorporated_area = "unincorporated_area"


class OrganizationType(str, Enum):
    """
    Organization type, namespaced and extensible (§11.2, §13.7). "vendor" is a ROLE, not a subtype (SIG-ONTO-012); it appears here only as an organization-classification convenience and never specializes the entity.
    """
    usFULL_STOPleFULL_STOPmunicipal_police = "us.le.municipal_police"
    usFULL_STOPleFULL_STOPsheriff = "us.le.sheriff"
    usFULL_STOPleFULL_STOPstate_police = "us.le.state_police"
    usFULL_STOPleFULL_STOPuniversity_police = "us.le.university_police"
    usFULL_STOPleFULL_STOPtransit_police = "us.le.transit_police"
    usFULL_STOPleFULL_STOPschool_district_police = "us.le.school_district_police"
    usFULL_STOPleFULL_STOPtribal_police = "us.le.tribal_police"
    usFULL_STOPleFULL_STOPfederal = "us.le.federal"
    usFULL_STOPgovFULL_STOPmunicipality = "us.gov.municipality"
    usFULL_STOPgovFULL_STOPcounty = "us.gov.county"
    usFULL_STOPgovFULL_STOPspecial_district = "us.gov.special_district"
    usFULL_STOPfusion_center = "us.fusion_center"
    privateFULL_STOPcompany = "private.company"
    privateFULL_STOPhoa = "private.hoa"
    privateFULL_STOPsecurity_firm = "private.security_firm"
    privateFULL_STOPbid = "private.bid"
    nonprofit = "nonprofit"
    hospital = "hospital"
    university = "university"
    school_district = "school_district"
    utility = "utility"
    transit_agency = "transit_agency"
    vendor = "vendor"
    data_broker = "data_broker"
    frFULL_STOPpolice_municipale = "fr.police_municipale"
    frFULL_STOPgendarmerie = "fr.gendarmerie"


class AcquisitionMethod(str, Enum):
    """
    Acquisition method, internationalized (§13.8). foia_request is US-specific; the abstract parent is records_request with national children, plus no_equivalent_available (itself a coverage fact).
    """
    records_request = "records_request"
    """
    Abstract parent of all public-records regimes.
    """
    usFULL_STOPfoia = "us.foia"
    usFULL_STOPstate_public_records = "us.state_public_records"
    frFULL_STOPcada = "fr.cada"
    ukFULL_STOPfoi = "uk.foi"
    euFULL_STOPaccess_to_documents = "eu.access_to_documents"
    no_equivalent_available = "no_equivalent_available"


class Salience(str, Enum):
    """
    Technology salience rating (§13.1, SIG-ONTO-056).
    """
    L = "L"
    """
    Low.
    """
    M = "M"
    """
    Medium.
    """
    H = "H"
    """
    High.
    """
    C = "C"
    """
    Constitutional/statutory special category.
    """


class Direction(str, Enum):
    """
    Explicit edge direction — never symmetric by default (§12.5, SIG-ONTO-049).
    """
    a_to_b = "a_to_b"
    b_to_a = "b_to_a"


class EdgeType(str, Enum):
    """
    The closed catalog of relationship types (§12.1, SIG-ONTO-041). Untyped edges are a schema error. Prohibited edges (§12.8) are intentionally absent.
    """
    ingests_feed_from = "ingests_feed_from"
    """
    B pulls a continuous stream from A; data comes to rest in B.
    """
    pushes_alerts_to = "pushes_alerts_to"
    """
    A pushes discrete events to B.
    """
    federates_search_to = "federates_search_to"
    """
    B may query A's data; the corpus stays with A.
    """
    is_queryable_by = "is_queryable_by"
    """
    Inverse asserted from A's side (perspectival).
    """
    hosts_data_for = "hosts_data_for"
    """
    A stores/controls infrastructure holding B's data (custody).
    """
    resells_data_from = "resells_data_from"
    """
    A sells access to data collected by B (money + third-party corpus).
    """
    provides_platform_to = "provides_platform_to"
    """
    A supplies the software surface B operates on.
    """
    subscribes_to = "subscribes_to"
    """
    B pays for standing access to A's data/service.
    """
    enrolls_asset_into = "enrolls_asset_into"
    """
    An asset owned by A is registered into platform B.
    """
    requests_data_from = "requests_data_from"
    """
    A can issue per-incident, consent-gated requests to B's users.
    """
    distributes_list_to = "distributes_list_to"
    """
    A pushes a watchlist to B; matches do NOT return to A (SIG-ONTO-046).
    """
    authorizes = "authorizes"
    """
    A grants B legal permission to operate a capability; no data moves.
    """
    replaced_by = "replaced_by"
    """
    B's deployment supersedes A's for the same capability at the same org.
    """
    succeeds = "succeeds"
    """
    Temporal substitution (§12.3).
    """
    parent_of = "parent_of"
    child_of = "child_of"
    merged_into = "merged_into"
    split_from = "split_from"
    renamed_from = "renamed_from"
    absorbed_by = "absorbed_by"
    participates_in = "participates_in"
    """
    Fusion centers, task forces, cooperative purchasing bodies.
    """
    has_jurisdiction_over = "has_jurisdiction_over"
    operates_within = "operates_within"
    """
    A deployment operating outside the operator's own jurisdiction — first-class, not an anomaly.
    """
    member_of_network = "member_of_network"
    derived_from_claim = "derived_from_claim"
    supersedes_claim = "supersedes_claim"
    contradicts_claim = "contradicts_claim"
    corroborates_claim = "corroborates_claim"
    extracted_from_capture = "extracted_from_capture"
    captures_artifact = "captures_artifact"
    published_by_source = "published_by_source"



class Entity(ConfiguredBaseModel):
    """
    Abstract base — every entity has identity (§3.1 defining standard).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True,
         'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class Jurisdiction(Entity):
    """
    [NEW] A first-class jurisdiction with a self-referential hierarchy, a pluggable national code system, and temporally-versioned geometry (§11.1, SIG-ONTO-010/011).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    jurisdiction_type: Optional[JurisdictionType] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction']} })
    parent_jurisdiction: Optional[list[str]] = Field(default=None, description="""Multiple parents permitted; hierarchies overlap (SIG-ONTO-010).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction']} })
    code_system: Optional[list[str]] = Field(default=None, description="""Repeatable code-system identifiers (us.census.geoid, iso.3166-2, fr.insee, ...).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction']} })
    code: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction']} })
    boundary: Optional[str] = Field(default=None, description="""MultiPolygon, 4326.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction']} })
    boundary_source: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction']} })
    name: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction']} })
    name_lang: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction', 'Organization']} })
    valid_from: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction', 'Organization', 'Edge']} })
    valid_to: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction', 'Organization', 'Edge']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class Organization(Entity):
    """
    The single entity for ALL institutional actors; \"vendor\" is a role, not a subtype (§11.2, SIG-ONTO-012). canonical_name is a claim, not a column (§8.2).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    canonical_name: Optional[str] = Field(default=None, description="""A claim, not an authoritative column (§8.2, SIG-ONTO-003).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Organization']} })
    alias: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Organization']} })
    alias_type: Optional[list[AliasType]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Organization']} })
    name_lang: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction', 'Organization']} })
    organization_type: Optional[OrganizationType] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Organization']} })
    parent_organization: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Organization']} })
    jurisdiction: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Organization', 'Deployment', 'LegalInstrument']} })
    identifier: Optional[list[str]] = Field(default=None, description="""Repeatable (scheme,value) pairs, qualified by identifier_system (SIG-IDENT-006).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Organization']} })
    identifier_system: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Organization']} })
    government_domain: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Organization']} })
    address: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Organization']} })
    valid_from: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction', 'Organization', 'Edge']} })
    valid_to: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction', 'Organization', 'Edge']} })
    succession: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Organization']} })
    succession_kind: Optional[list[SuccessionKind]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Organization']} })
    publication_review: Optional[bool] = Field(default=None, description="""Routes surrogate-only orgs through §43.4 before public exposure (SIG-ONTO-013).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Organization']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class Person(Entity):
    """
    [NEW] Tightly constrained (§11.3, SIG-ONTO-014/015/016). A Person row carries NO surveillance attributes and MUST NOT be reachable from any automated extraction path. It exists only for named public officials and SIG's own attributable curators.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    public_interest_basis: str = Field(default=..., description="""MUST pass the officer-naming test (§43.4); required (SIG-ONTO-016).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Person']} })
    human_review_completed: bool = Field(default=..., description="""Person creation MUST have been through human review (SIG-ONTO-016).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Person']} })
    role_description: Optional[str] = Field(default=None, description="""The public role justifying inclusion (e.g. named official in an accountability event).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Person']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class Product(Entity):
    """
    A product; MUST NOT be equated with a Technology (§11.4, SIG-ONTO-017).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    product_name: Optional[str] = Field(default=None, description="""Time-bounded; products are renamed constantly.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Product']} })
    vendor: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Product', 'Deployment', 'DataSystem']} })
    implements_technology: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Product']} })
    can_offer_capability: Optional[list[str]] = Field(default=None, description="""Defeasible / marketing-level only (SIG-ONTO-018).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Product']} })
    product_status: Optional[ProductStatus] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Product']} })
    successor_product: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Product']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class Technology(Entity):
    """
    A three-level technology (domain→family→technology, §11.5, SIG-ONTO-019). The authoritative term hierarchy is the SKOS Technology scheme (§13.1); this class carries the code and its rollup levels for a specific referenced node.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    technology: Optional[str] = Field(default=None, description="""The technology-level slug.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Technology', 'Deployment']} })
    family: Optional[str] = Field(default=None, description="""The family-level slug this rolls up to.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Technology']} })
    domain: Optional[str] = Field(default=None, description="""The domain-level slug this rolls up to.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Technology']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class Capability(Entity):
    """
    A verb.object.scope capability (§11.6, SIG-ONTO-023).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    capability: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Capability']} })
    scope: Optional[CapabilityScope] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Capability', 'AccessRelationship', 'IntegrationEdge']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class Deployment(Entity):
    """
    The bridge between organizational adoption and individual devices; creatable with NO product, NO vendor, and NO physical asset (§11.7, SIG-ONTO-026).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    deploying_organization: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Deployment']} })
    product: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Deployment', 'DataSystem']} })
    vendor: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Product', 'Deployment', 'DataSystem']} })
    technology: Optional[list[str]] = Field(default=None, description="""Repeatable; the coarsest level the evidence supports.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Technology', 'Deployment']} })
    actually_provides_capability: Optional[list[str]] = Field(default=None, description="""Evidentiary; never silently inferred from product default (SIG-ONTO-018).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Deployment']} })
    procurement_state: Optional[ProcurementState] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Deployment']} })
    physical_state: Optional[PhysicalState] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Deployment']} })
    operational_state: Optional[OperationalState] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Deployment']} })
    authorization_state: Optional[AuthorizationState] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Deployment']} })
    litigation_hold: Optional[bool] = Field(default=None, description="""A flag, coexisting with any state combination (SIG-ONTO-061).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Deployment']} })
    jurisdiction: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Organization', 'Deployment', 'LegalInstrument']} })
    contracted_device_count: Optional[int] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Deployment']} })
    installed_device_count: Optional[int] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Deployment']} })
    active_device_count: Optional[int] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Deployment']} })
    proposed_at: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Deployment']} })
    approved_at: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Deployment']} })
    contracted_at: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Deployment']} })
    active_from: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Deployment']} })
    inactive_at: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Deployment']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class PhysicalAsset(Entity):
    """
    A field-observed device; geometry is OPTIONAL and operator absence is a first-class countable state (§11.8, SIG-ONTO-027/028). Accommodates ways and relations, not only nodes, and MUST NOT force sensors into a camera abstraction.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    asset_type: Optional[str] = Field(default=None, description="""A Technology reference, not a free string.""", json_schema_extra = { "linkml_meta": {'domain_of': ['PhysicalAsset']} })
    geometry: Optional[str] = Field(default=None, description="""Optional (SIG-GEO-004).""", json_schema_extra = { "linkml_meta": {'domain_of': ['PhysicalAsset']} })
    mobility: Optional[Mobility] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['PhysicalAsset']} })
    manufacturer: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['PhysicalAsset']} })
    model: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['PhysicalAsset']} })
    deployment: Optional[str] = Field(default=None, description="""May be absent — the orphaned-device case.""", json_schema_extra = { "linkml_meta": {'domain_of': ['PhysicalAsset', 'ConfigurationState']} })
    first_observed: Optional[datetime ] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['PhysicalAsset']} })
    last_observed: Optional[datetime ] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['PhysicalAsset']} })
    upstream_id: Optional[list[str]] = Field(default=None, description="""Qualified by system (osm.node, osm.way, osm.relation, deflock.id, ...).""", json_schema_extra = { "linkml_meta": {'domain_of': ['PhysicalAsset']} })
    osm_version: Optional[int] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['PhysicalAsset']} })
    sensitivity_tier: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['PhysicalAsset']} })
    confirmation_status: Optional[ConfirmationStatus] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['PhysicalAsset']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class CandidateAsset(Entity):
    """
    [NEW] RF/heuristic leads that MUST live in a separate entity type and MUST NOT appear in any public device layer until promoted under §43.5 (§11.9, SIG-ONTO-029/030).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    detection_method: Optional[DetectionMethod] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['CandidateAsset']} })
    location_estimate: Optional[str] = Field(default=None, description="""With estimate_radius_m — never a bare point.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CandidateAsset']} })
    estimate_radius_m: Optional[float] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['CandidateAsset']} })
    identifier_prefix: Optional[str] = Field(default=None, description="""OUI or similar; never a full MAC.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CandidateAsset']} })
    observation_count: Optional[int] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['CandidateAsset']} })
    promotion_status: Optional[PromotionStatus] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['CandidateAsset']} })
    residential_parcel_flag: Optional[bool] = Field(default=None, description="""A true value bars publication outright (§43.5).""", json_schema_extra = { "linkml_meta": {'domain_of': ['CandidateAsset']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class DataSystem(Entity):
    """
    Reference databases as infrastructure — representable even where SIG holds no sensor (§11.10, SIG-ONTO-031).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    operator: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['DataSystem']} })
    vendor: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Product', 'Deployment', 'DataSystem']} })
    product: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Deployment', 'DataSystem']} })
    data_types: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['DataSystem']} })
    retention: Optional[str] = Field(default=None, description="""A ConfigurationState fact where it varies per deployment.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DataSystem']} })
    system_scope: Optional[SystemScope] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['DataSystem']} })
    holds_data_collected_by: Optional[str] = Field(default=None, description="""Custody != collection.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DataSystem']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class Contract(Entity):
    """
    A contract; acquisition_channel and parent_cooperative_contract are REQUIRED model elements (§11.11, SIG-ONTO-032).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    buyer: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Contract']} })
    seller: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Contract']} })
    amount: Optional[Decimal] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Contract', 'FundingInstrument']} })
    currency: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Contract']} })
    signed_date: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Contract']} })
    start_date: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Contract']} })
    end_date: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Contract']} })
    renewal_options: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Contract']} })
    products: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Contract']} })
    quantities: Optional[list[int]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Contract']} })
    document: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Contract', 'Policy']} })
    acquisition_channel: Optional[AcquisitionChannel] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Contract']} })
    parent_cooperative_contract: Optional[str] = Field(default=None, description="""The master award being ridden (SIG-ONTO-032).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Contract']} })
    amends_contract: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Contract']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class FundingInstrument(Entity):
    """
    [NEW] Purchaser != operator != funder (§11.12, SIG-ONTO-033). Grants and third-party funding; federal grant → local surveillance is traceable.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    funder: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['FundingInstrument']} })
    recipient: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['FundingInstrument']} })
    instrument_type: Optional[FundingInstrumentType] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['FundingInstrument', 'LegalInstrument']} })
    program_name: Optional[str] = Field(default=None, description="""e.g. Byrne JAG, UASI, COPS, Operation Stonegarden, HIDTA.""", json_schema_extra = { "linkml_meta": {'domain_of': ['FundingInstrument']} })
    amount: Optional[Decimal] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Contract', 'FundingInstrument']} })
    award_date: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['FundingInstrument']} })
    period: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['FundingInstrument', 'UsageAggregate']} })
    conditions: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['FundingInstrument']} })
    federal_award_id: Optional[str] = Field(default=None, description="""USAspending award/sub-award id — the traceable link (SIG-ONTO-033).""", json_schema_extra = { "linkml_meta": {'domain_of': ['FundingInstrument']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class Policy(Entity):
    """
    An institutional policy; MUST NOT be merged with ConfigurationState (§11.13, SIG-ONTO-034). Their disagreement is a first-class finding.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    policy_type: Optional[PolicyType] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Policy']} })
    applies_to: Optional[list[str]] = Field(default=None, description="""Organization, Deployment, or Product — polymorphic and repeatable.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Policy']} })
    effective_from: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Policy', 'LegalInstrument']} })
    effective_to: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Policy', 'LegalInstrument']} })
    adopting_body: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Policy']} })
    text: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Policy']} })
    document: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Contract', 'Policy']} })
    enforcement_mechanism: Optional[EnforcementMechanism] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Policy']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class LegalInstrument(Entity):
    """
    [NEW] Laws and regulations as a modelled entity (§11.14). Gives the international requirement somewhere to put an arrêté préfectoral, a CNIL decision, or an EU AI Act obligation.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    instrument_type: Optional[LegalInstrumentType] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['FundingInstrument', 'LegalInstrument']} })
    enacting_body: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['LegalInstrument']} })
    jurisdiction: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Organization', 'Deployment', 'LegalInstrument']} })
    citation: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['LegalInstrument']} })
    effective_from: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Policy', 'LegalInstrument']} })
    effective_to: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Policy', 'LegalInstrument']} })
    sunset_date: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['LegalInstrument']} })
    constrains_technology: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['LegalInstrument']} })
    constrains_capability: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['LegalInstrument']} })
    requires_authorization_of: Optional[list[str]] = Field(default=None, description="""CCOPS-style approval requirements.""", json_schema_extra = { "linkml_meta": {'domain_of': ['LegalInstrument']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class ConfigurationState(Entity):
    """
    Promoted to a first-class, time-versioned, per-Deployment entity (§11.15). Configuration is observed, never assumed (SIG-ONTO-036). Retention is a duration OR an ordinal bucket; SIG never fabricates a midpoint (SIG-ONTO-035a).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    deployment: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['PhysicalAsset', 'ConfigurationState']} })
    retention_days: Optional[str] = Field(default=None, description="""Duration OR ordinal bucket; MUST accept both (SIG-ONTO-035a).""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConfigurationState']} })
    retention_bucket: Optional[str] = Field(default=None, description="""The ordinal bucket form; comparison operates on intervals, never a coerced point.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConfigurationState']} })
    subscribed_hotlist_topic: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ConfigurationState']} })
    sharing_partner: Optional[list[str]] = Field(default=None, description="""Repeatable, directional.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConfigurationState']} })
    state_lookup_enabled: Optional[bool] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ConfigurationState']} })
    national_lookup_enabled: Optional[bool] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ConfigurationState']} })
    federal_sharing_enabled: Optional[bool] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ConfigurationState']} })
    offense_category_filter: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ConfigurationState']} })
    live_stream_permitted_to: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ConfigurationState']} })
    third_party_integration: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ConfigurationState']} })
    audit_case_code_required: Optional[bool] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ConfigurationState']} })
    observed_via: Optional[ObservedVia] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ConfigurationState']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class UsageAggregate(Entity):
    """
    Aggregated usage; direction is the point (§11.16). NO per-search, per-plate, or per-person row may exist here or anywhere in SIG (SIG-ONTO-037, §18.1).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    searching_org: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['UsageAggregate']} })
    source_org: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['UsageAggregate']} })
    period: Optional[str] = Field(default=None, description="""Minimum granularity one month for published data (§18.4).""", json_schema_extra = { "linkml_meta": {'domain_of': ['FundingInstrument', 'UsageAggregate']} })
    count: Optional[int] = Field(default=None, description="""Subject to small-cell suppression (§18.4).""", json_schema_extra = { "linkml_meta": {'domain_of': ['UsageAggregate']} })
    search_scope: Optional[CapabilityScope] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['UsageAggregate']} })
    reason_category: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['UsageAggregate']} })
    reason_raw_value: Optional[str] = Field(default=None, description="""Normalized reason_category retains the raw value (P2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['UsageAggregate']} })
    audit_source_type: Optional[AuditSourceType] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['UsageAggregate']} })
    coverage_period: Optional[str] = Field(default=None, description="""What span the underlying audit covered — distinct from period.""", json_schema_extra = { "linkml_meta": {'domain_of': ['UsageAggregate', 'CoverageRecord']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class AccountabilityEvent(Entity):
    """
    An accountability event; epistemic_status is REQUIRED and rendered everywhere (§11.17, SIG-ONTO-038/039).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    event_type: Optional[AccountabilityEventType] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AccountabilityEvent']} })
    epistemic_status: EpistemicStatus = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['AccountabilityEvent']} })
    date: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AccountabilityEvent']} })
    organizations: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AccountabilityEvent']} })
    deployments: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AccountabilityEvent']} })
    technologies: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AccountabilityEvent']} })
    affected_party_class: Optional[str] = Field(default=None, description="""A class, never a named private individual (N4).""", json_schema_extra = { "linkml_meta": {'domain_of': ['AccountabilityEvent']} })
    sources: Optional[list[str]] = Field(default=None, description="""Linkable to all six source classes of OL-2E-AL-03 (SIG-ONTO-039).""", json_schema_extra = { "linkml_meta": {'domain_of': ['AccountabilityEvent', 'Edge']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class LegalProceeding(Entity):
    """
    Split from AccountabilityEvent — dockets, parties, filings, posture (§11.18).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    court: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['LegalProceeding']} })
    docket_number: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['LegalProceeding']} })
    case_name: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['LegalProceeding']} })
    parties: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['LegalProceeding']} })
    party_role: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['LegalProceeding']} })
    filed_date: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['LegalProceeding', 'RecordsRequest']} })
    disposition_date: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['LegalProceeding']} })
    posture: Optional[ProceedingPosture] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['LegalProceeding']} })
    courtlistener_id: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['LegalProceeding']} })
    recap_id: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['LegalProceeding']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class RecordsRequest(Entity):
    """
    [NEW] A public-records request SIG both cites as provenance and generates as a task (§11.19). no_responsive_records is a positive finding (SIG-ONTO-040).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    requesting_party: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['RecordsRequest']} })
    target_agency: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['RecordsRequest']} })
    request_text: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['RecordsRequest']} })
    filed_date: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['LegalProceeding', 'RecordsRequest']} })
    response_date: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['RecordsRequest']} })
    response_status: Optional[RecordsResponseStatus] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['RecordsRequest']} })
    statutory_basis: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['RecordsRequest']} })
    platform: Optional[RecordsPlatform] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['RecordsRequest']} })
    external_id: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['RecordsRequest']} })
    released_documents: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['RecordsRequest']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class Source(Entity):
    """
    A publisher of evidence (§10.2, §11.20). Distinct from artifact and capture.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    publisher_name: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Source']} })
    reliability: Optional[SourceReliability] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Source']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class EvidenceArtifact(Entity):
    """
    A specific artifact published by a Source (§10.2).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    published_by: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['EvidenceArtifact']} })
    integrity: Optional[ArtifactIntegrity] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['EvidenceArtifact']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class EvidenceCapture(Entity):
    """
    A content-addressed capture of an artifact at a time (§10.2, L0).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    captures_artifact: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['EvidenceCapture']} })
    captured_at: Optional[datetime ] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['EvidenceCapture']} })
    content_digest: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['EvidenceCapture']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class Extraction(Entity):
    """
    A run that extracted claims from a capture (§10.2).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    from_capture: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Extraction']} })
    extraction_method: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Extraction']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class Claim(Entity):
    """
    An append-only assertion (subject, predicate, value, ...) — the substance of the graph (§10.3, L1). Physical append-only table is P02.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    subject: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Claim', 'Resolution', 'Contradiction', 'CoverageRecord']} })
    predicate: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Claim', 'Resolution', 'Contradiction', 'CoverageRecord']} })
    value: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Claim']} })
    value_kind: Optional[ValueKind] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Claim']} })
    raw_value: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Claim']} })
    absence_kind: Optional[AbsenceKind] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Claim', 'CoverageRecord']} })
    evidence_role: Optional[EvidenceRole] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Claim']} })
    supersedes: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Claim']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class Resolution(Entity):
    """
    A stored current-best decision record (§16.4, L3), not a view.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    subject: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Claim', 'Resolution', 'Contradiction', 'CoverageRecord']} })
    predicate: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Claim', 'Resolution', 'Contradiction', 'CoverageRecord']} })
    resolved_value: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Resolution']} })
    confidence: Optional[WeightClass] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Resolution']} })
    contradiction_state: Optional[ContradictionState] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Resolution']} })
    rationale: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Resolution']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class Contradiction(Entity):
    """
    A first-class, addressable contradiction object (§31).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    subject: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Claim', 'Resolution', 'Contradiction', 'CoverageRecord']} })
    predicate: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Claim', 'Resolution', 'Contradiction', 'CoverageRecord']} })
    state: Optional[ContradictionState] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Contradiction']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class ResearchTask(Entity):
    """
    [NEW] A research task as an object (§11.22, behaviour at §33.2).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    task_type: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchTask']} })
    target: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchTask', 'Edge']} })
    closing_condition: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchTask']} })
    resolved: Optional[bool] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchTask']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class CoverageRecord(Entity):
    """
    [NEW] Makes negative claims queryable (§11.23, §32.2).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/entities'})

    subject: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Claim', 'Resolution', 'Contradiction', 'CoverageRecord']} })
    predicate: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Claim', 'Resolution', 'Contradiction', 'CoverageRecord']} })
    absence_kind: Optional[AbsenceKind] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Claim', 'CoverageRecord']} })
    coverage_period: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['UsageAggregate', 'CoverageRecord']} })
    denominator_published: Optional[bool] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['CoverageRecord']} })
    id: str = Field(default=..., description="""The entity's stable minted identity (L2 identity only, §8.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })


class Edge(ConfiguredBaseModel):
    """
    Universal edge requirements (§12.1): directed, typed, time-bounded, evidenced, and perspectival.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True,
         'from_schema': 'https://ontology.sig-project.org/schema/edges'})

    id: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })
    source: str = Field(default=..., description="""The asserting/originating node (directed — §12.1.1).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    target: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchTask', 'Edge']} })
    edge_type: EdgeType = Field(default=..., description="""Typed from the closed catalog (§12.1.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    valid_from: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction', 'Organization', 'Edge']} })
    valid_to: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction', 'Organization', 'Edge']} })
    valid_from_kind: Optional[TemporalBoundKind] = Field(default=None, description="""Snapshot sharing carries unknown/ongoing (SIG-ONTO-044).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    valid_to_kind: Optional[TemporalBoundKind] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    observed_at: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    sources: Optional[list[str]] = Field(default=None, description="""At least one supporting claim (§12.1.4, SIG-CHART-013).""", json_schema_extra = { "linkml_meta": {'domain_of': ['AccountabilityEvent', 'Edge']} })
    asserted_by: Optional[str] = Field(default=None, description="""Which party asserted it — perspectival (§12.1.5).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })


class AccessRelationship(Edge):
    """
    A sharing/access relationship; direction, scope, automaticity, and kind are all required — never reduced to `shares_with` (§12.5, SIG-ONTO-049). The three access kinds (§12.2) are never merged (SIG-ONTO-042).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/edges'})

    scope: CapabilityScope = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Capability', 'AccessRelationship', 'IntegrationEdge']} })
    direction: Direction = Field(default=..., description="""Required; never symmetric by default (SIG-ONTO-049).""", json_schema_extra = { "linkml_meta": {'domain_of': ['AccessRelationship']} })
    automaticity: Optional[Automaticity] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AccessRelationship']} })
    access_kind: AccessKind = Field(default=..., description="""Configured vs observed vs declared — never defaulted into one another (SIG-ONTO-042).""", json_schema_extra = { "linkml_meta": {'domain_of': ['AccessRelationship']} })
    id: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })
    source: str = Field(default=..., description="""The asserting/originating node (directed — §12.1.1).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    target: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchTask', 'Edge']} })
    edge_type: EdgeType = Field(default=..., description="""Typed from the closed catalog (§12.1.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    valid_from: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction', 'Organization', 'Edge']} })
    valid_to: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction', 'Organization', 'Edge']} })
    valid_from_kind: Optional[TemporalBoundKind] = Field(default=None, description="""Snapshot sharing carries unknown/ongoing (SIG-ONTO-044).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    valid_to_kind: Optional[TemporalBoundKind] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    observed_at: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    sources: Optional[list[str]] = Field(default=None, description="""At least one supporting claim (§12.1.4, SIG-CHART-013).""", json_schema_extra = { "linkml_meta": {'domain_of': ['AccountabilityEvent', 'Edge']} })
    asserted_by: Optional[str] = Field(default=None, description="""Which party asserted it — perspectival (§12.1.5).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })


class IntegrationEdge(Edge):
    """
    A data-bearing integration edge (§12.3). Edges are per (product-pair, data-kind, direction), never per product-pair (SIG-ONTO-046). Unilaterally terminable, mid-contract, possibly partially, via applies_to_cohort.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/edges'})

    data_kind: str = Field(default=..., description="""The kind of data that moves (part of the edge key, SIG-ONTO-046).""", json_schema_extra = { "linkml_meta": {'domain_of': ['IntegrationEdge']} })
    initiator: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['IntegrationEdge']} })
    transport: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['IntegrationEdge']} })
    granularity: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['IntegrationEdge']} })
    data_comes_to_rest: Optional[bool] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['IntegrationEdge']} })
    scope: Optional[CapabilityScope] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Capability', 'AccessRelationship', 'IntegrationEdge']} })
    consent_gate: Optional[bool] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['IntegrationEdge']} })
    mechanism: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['IntegrationEdge']} })
    terminable_by: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['IntegrationEdge']} })
    termination_reason: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['IntegrationEdge']} })
    applies_to_cohort: Optional[CohortApplicability] = Field(default=None, description="""Partial termination cohort — all / new_customers_only / existing_customers_only (SIG-ONTO-046).""", json_schema_extra = { "linkml_meta": {'domain_of': ['IntegrationEdge']} })
    id: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })
    source: str = Field(default=..., description="""The asserting/originating node (directed — §12.1.1).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    target: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchTask', 'Edge']} })
    edge_type: EdgeType = Field(default=..., description="""Typed from the closed catalog (§12.1.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    valid_from: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction', 'Organization', 'Edge']} })
    valid_to: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction', 'Organization', 'Edge']} })
    valid_from_kind: Optional[TemporalBoundKind] = Field(default=None, description="""Snapshot sharing carries unknown/ongoing (SIG-ONTO-044).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    valid_to_kind: Optional[TemporalBoundKind] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    observed_at: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    sources: Optional[list[str]] = Field(default=None, description="""At least one supporting claim (§12.1.4, SIG-CHART-013).""", json_schema_extra = { "linkml_meta": {'domain_of': ['AccountabilityEvent', 'Edge']} })
    asserted_by: Optional[str] = Field(default=None, description="""Which party asserted it — perspectival (§12.1.5).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })


class RoleAssignment(Edge):
    """
    Assigns one of the fourteen roles (§12.4, SIG-ONTO-047) from a party to an asset/deployment/system. Modelled separately so the seven load-bearing separations (SIG-ONTO-048) are each independently representable, and so §43.3 coordinate sensitivity can be evaluated at the ROLE level (host≠owner).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/edges'})

    role: Role = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['RoleAssignment']} })
    party: str = Field(default=..., description="""The Organization (or, rarely and reviewed, Person) holding the role.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RoleAssignment']} })
    over: str = Field(default=..., description="""The PhysicalAsset / Deployment / DataSystem the role is held over.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RoleAssignment']} })
    id: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })
    source: str = Field(default=..., description="""The asserting/originating node (directed — §12.1.1).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    target: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchTask', 'Edge']} })
    edge_type: EdgeType = Field(default=..., description="""Typed from the closed catalog (§12.1.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    valid_from: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction', 'Organization', 'Edge']} })
    valid_to: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction', 'Organization', 'Edge']} })
    valid_from_kind: Optional[TemporalBoundKind] = Field(default=None, description="""Snapshot sharing carries unknown/ongoing (SIG-ONTO-044).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    valid_to_kind: Optional[TemporalBoundKind] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    observed_at: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    sources: Optional[list[str]] = Field(default=None, description="""At least one supporting claim (§12.1.4, SIG-CHART-013).""", json_schema_extra = { "linkml_meta": {'domain_of': ['AccountabilityEvent', 'Edge']} })
    asserted_by: Optional[str] = Field(default=None, description="""Which party asserted it — perspectival (§12.1.5).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })


class StructuralEdge(Edge):
    """
    Organizational/structural relationships (§12.6).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/edges'})

    id: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })
    source: str = Field(default=..., description="""The asserting/originating node (directed — §12.1.1).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    target: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchTask', 'Edge']} })
    edge_type: EdgeType = Field(default=..., description="""Typed from the closed catalog (§12.1.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    valid_from: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction', 'Organization', 'Edge']} })
    valid_to: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction', 'Organization', 'Edge']} })
    valid_from_kind: Optional[TemporalBoundKind] = Field(default=None, description="""Snapshot sharing carries unknown/ongoing (SIG-ONTO-044).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    valid_to_kind: Optional[TemporalBoundKind] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    observed_at: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    sources: Optional[list[str]] = Field(default=None, description="""At least one supporting claim (§12.1.4, SIG-CHART-013).""", json_schema_extra = { "linkml_meta": {'domain_of': ['AccountabilityEvent', 'Edge']} })
    asserted_by: Optional[str] = Field(default=None, description="""Which party asserted it — perspectival (§12.1.5).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })


class ProvenanceEdge(Edge):
    """
    Provenance relationships among claims, captures, artifacts, and sources (§12.7).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://ontology.sig-project.org/schema/edges'})

    id: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Edge']} })
    source: str = Field(default=..., description="""The asserting/originating node (directed — §12.1.1).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    target: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchTask', 'Edge']} })
    edge_type: EdgeType = Field(default=..., description="""Typed from the closed catalog (§12.1.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    valid_from: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction', 'Organization', 'Edge']} })
    valid_to: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Jurisdiction', 'Organization', 'Edge']} })
    valid_from_kind: Optional[TemporalBoundKind] = Field(default=None, description="""Snapshot sharing carries unknown/ongoing (SIG-ONTO-044).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    valid_to_kind: Optional[TemporalBoundKind] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    observed_at: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    sources: Optional[list[str]] = Field(default=None, description="""At least one supporting claim (§12.1.4, SIG-CHART-013).""", json_schema_extra = { "linkml_meta": {'domain_of': ['AccountabilityEvent', 'Edge']} })
    asserted_by: Optional[str] = Field(default=None, description="""Which party asserted it — perspectival (§12.1.5).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
Entity.model_rebuild()
Jurisdiction.model_rebuild()
Organization.model_rebuild()
Person.model_rebuild()
Product.model_rebuild()
Technology.model_rebuild()
Capability.model_rebuild()
Deployment.model_rebuild()
PhysicalAsset.model_rebuild()
CandidateAsset.model_rebuild()
DataSystem.model_rebuild()
Contract.model_rebuild()
FundingInstrument.model_rebuild()
Policy.model_rebuild()
LegalInstrument.model_rebuild()
ConfigurationState.model_rebuild()
UsageAggregate.model_rebuild()
AccountabilityEvent.model_rebuild()
LegalProceeding.model_rebuild()
RecordsRequest.model_rebuild()
Source.model_rebuild()
EvidenceArtifact.model_rebuild()
EvidenceCapture.model_rebuild()
Extraction.model_rebuild()
Claim.model_rebuild()
Resolution.model_rebuild()
Contradiction.model_rebuild()
ResearchTask.model_rebuild()
CoverageRecord.model_rebuild()
Edge.model_rebuild()
AccessRelationship.model_rebuild()
IntegrationEdge.model_rebuild()
RoleAssignment.model_rebuild()
StructuralEdge.model_rebuild()
ProvenanceEdge.model_rebuild()
