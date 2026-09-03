-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:seed_vocab to pg
-- The FIXED reference vocabularies the claim spine's foreign keys resolve against:
-- the epistemic scales (R/D/I, §10.4-§10.6), the object-type kinds (§10.3.5), the
-- six evidence roles (§10.3.6), and the entity-type catalog (§11). These are
-- stable by construction; the mutable, ontology-owned vocabularies (predicates,
-- resolution strategies, rationales, confidence) are versioned migrations seeded
-- by the tickets that own them (P01.1 / P08.1).

BEGIN;

-- Source reliability R1..R6 (§10.4) — a property of the publisher.
INSERT INTO vocab_source_reliability (code, definition) VALUES
  ('R1','Authoritative first-party record (executed contract, official filing).'),
  ('R2','Reliable institutional source (agency policy, council minutes).'),
  ('R3','Credible secondary source (reputable journalism).'),
  ('R4','Mixed-reliability or advocacy source; corroboration expected.'),
  ('R5','Unverified or self-published source.'),
  ('R6','Vendor marketing or default material; weakest reliability.')
ON CONFLICT (code) DO NOTHING;

-- Claim directness D1..D6 (§10.5) — the (genre x predicate) matrix codomain.
INSERT INTO vocab_claim_directness (code, definition) VALUES
  ('D1','Direct statement of the fact in an authoritative record.'),
  ('D2','Direct statement in a secondary record.'),
  ('D3','Indirect but strongly implied.'),
  ('D4','Inferred from adjacent facts.'),
  ('D5','Weak support; the genre rarely bears on this predicate.'),
  ('D6','Effectively no bearing on this predicate.')
ON CONFLICT (code) DO NOTHING;

-- Artifact integrity I1..I3 (§10.6).
INSERT INTO vocab_artifact_integrity (code, definition) VALUES
  ('I1','Intact original capture with verified digest.'),
  ('I2','Derived or reformatted but faithful.'),
  ('I3','Degraded, partial, or integrity-uncertain.')
ON CONFLICT (code) DO NOTHING;

-- Object-type kinds (§10.3.5): which value_* column a claim populates.
INSERT INTO vocab_object_type (object_type, definition) VALUES
  ('literal','A literal string/number value.'),
  ('entity_ref','A reference to another entity.'),
  ('vocab_term','A controlled-vocabulary term.'),
  ('quantity','A dimensioned quantity (requires unit).'),
  ('money','A monetary amount.'),
  ('geometry','A spatial geometry.'),
  ('duration','A duration.'),
  ('interval','A time interval.'),
  ('document_ref','A reference to a document/artifact.')
ON CONFLICT (object_type) DO NOTHING;

-- The six evidence roles (§10.3.6 / §13.3).
INSERT INTO vocab_evidence_role (role, definition) VALUES
  ('establishes','Primary evidence establishing the claim.'),
  ('corroborates','Independent evidence supporting the claim.'),
  ('contextualizes','Evidence providing context.'),
  ('contradicts','Evidence AGAINST the claim (no negative claim invented).'),
  ('supersedes_basis','Evidence that supersedes an earlier basis.'),
  ('attests_absence','Evidence attesting absence (§9.5).')
ON CONFLICT (role) DO NOTHING;

-- Entity-type catalog (§11), snake_case slugs matching the C.4 sub-tables.
INSERT INTO vocab_entity_type (entity_type, definition) VALUES
  ('jurisdiction','A first-class jurisdiction (§11.1).'),
  ('organization','An institutional actor (§11.2).'),
  ('person','A tightly-constrained named individual (§11.3).'),
  ('product','A product (§11.4).'),
  ('technology','A technology node (§11.5).'),
  ('capability','A verb.object.scope capability (§11.6).'),
  ('deployment','An organizational adoption bridge (§11.7).'),
  ('physical_asset','A field-observed device (§11.8).'),
  ('candidate_asset','An RF/heuristic lead (§11.9).'),
  ('data_system','A reference database as infrastructure (§11.10).'),
  ('contract','A contract (§11.11).'),
  ('funding_instrument','A grant or funding instrument (§11.12).'),
  ('policy','An institutional policy (§11.13).'),
  ('legal_instrument','A legal instrument (§11.14).'),
  ('configuration_state','A configuration state (§11.15).'),
  ('usage_aggregate','An aggregate usage record (§11.16).'),
  ('accountability_event','An accountability event (§11.17).'),
  ('legal_proceeding','A legal proceeding (§11.18).'),
  ('records_request','A records request (§11.19).')
ON CONFLICT (entity_type) DO NOTHING;

COMMIT;
