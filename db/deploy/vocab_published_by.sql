-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:vocab_published_by to pg
-- P35.26 (R11-L3-CP7 / SIG-TRUST-003): register `published_by` in the hosted
-- closed vocabulary BEFORE the role-aware EFF/OSM re-ingest legs emit it —
-- P35.14a's closed sink quarantines an unregistered predicate, and
-- `claim.predicate_id` carries the FK. The row projects the ontology registry
-- verbatim (vocab_version 1.0.0); the directness matrix gains the predicate's
-- 20-genre row at ruleset_version 1.0.0. INSERT-only, ON CONFLICT-safe, no
-- UPDATE/DELETE: a pre-existing row keeps its values (append-only, P1–P3).

BEGIN;

INSERT INTO vocab_predicate
(predicate_id, vocab_version, value_datatype, object_type, cardinality,
 definition, skos_concept_iri, volatility_class, half_life_days,
 resolution_strategy) VALUES
  ('published_by', '1.0.0', 'string', 'literal', 'single', 'The publisher of the source dataset this subject''s claims derive from — PUBLISHER provenance, never an operational role. P35.26 / SIG-TRUST-003: the publisher label is recorded as published_by (the generic sibling of camera_registry_publisher for non-registry sources — e.g. "OpenStreetMap contributors", "EFF & MuckRock — Data Driven (2018)"); it never evidences camera operation, ownership, vendor or access status, and — a provenance role — never mints an organisation entity-ref (ADR-112/ADR-122).', 'https://ontology.sig-project.org/vocab/predicate/1.0.0/published_by', 'GLACIAL', 3652, 'max_support')
ON CONFLICT (predicate_id) DO NOTHING;

INSERT INTO directness_matrix (artifact_type, predicate_id, directness, ruleset_version) VALUES
  ('executed_contract', 'published_by', 'D6', '1.0.0'),
  ('invoice', 'published_by', 'D6', '1.0.0'),
  ('portal_snapshot', 'published_by', 'D6', '1.0.0'),
  ('council_minutes', 'published_by', 'D6', '1.0.0'),
  ('agency_policy', 'published_by', 'D6', '1.0.0'),
  ('osm_node_set', 'published_by', 'D2', '1.0.0'),
  ('audit_log', 'published_by', 'D6', '1.0.0'),
  ('news_article', 'published_by', 'D6', '1.0.0'),
  ('vendor_default_page', 'published_by', 'D6', '1.0.0'),
  ('camera_registry', 'published_by', 'D2', '1.0.0'),
  ('connector_run', 'published_by', 'D3', '1.0.0'),
  ('agenda_document', 'published_by', 'D6', '1.0.0'),
  ('bill_index', 'published_by', 'D6', '1.0.0'),
  ('portal_document', 'published_by', 'D6', '1.0.0'),
  ('community_map', 'published_by', 'D2', '1.0.0'),
  ('contract', 'published_by', 'D6', '1.0.0'),
  ('official_statement', 'published_by', 'D3', '1.0.0'),
  ('template', 'published_by', 'D6', '1.0.0'),
  ('subscription', 'published_by', 'D6', '1.0.0'),
  ('recommendation', 'published_by', 'D6', '1.0.0')
ON CONFLICT (artifact_type, predicate_id, ruleset_version) DO NOTHING;

COMMIT;
