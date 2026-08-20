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
