-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:domain_entities to pg
-- Appendix C.4 / SIG-STORE-046: identity-only projections over `entity`. Typed
-- sub-tables carry FK-able identity, cached resolver output (marked), and
-- governance fields that cannot themselves be claims — NEVER world-facts. A
-- schema test (SIG-STORE-009) asserts no column here duplicates a predicate id.

BEGIN;

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

COMMIT;
