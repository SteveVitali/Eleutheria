-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:vocab_geometry_defect to pg
-- P35.16 (R11-DATA-01, F-322 / SIG-GEO-008): register `geometry_defect` in the
-- hosted closed vocabulary BEFORE the first detector-flagged ingest or the
-- correction-claim write lands — P35.14a's closed sink quarantines an
-- unregistered predicate, and `claim.predicate_id` carries the FK. The row
-- projects the ontology registry verbatim (vocab_version 1.0.0) exactly as
-- `closed_vocabulary` seeded its cohort; the directness matrix gains the
-- predicate's 20-genre row at ruleset_version 1.0.0. INSERT-only,
-- ON CONFLICT-safe, no UPDATE/DELETE: a pre-existing row keeps its values
-- (append-only, P1–P3). Deployed on the hosted spine as part of the queued
-- P35.16 correction leg, never by an engineering run outside its window.

BEGIN;

INSERT INTO vocab_predicate
(predicate_id, vocab_version, value_datatype, object_type, cardinality,
 definition, skos_concept_iri, volatility_class, half_life_days,
 resolution_strategy) VALUES
  ('geometry_defect', '1.0.0', 'string', 'literal', 'multi', 'A recorded geometry-defect marking on a registry-observed subject: the defect class an ingest detector or the append-only correction pass found in the published coordinate pair — axis_swap (the pair sits outside the declared extent and the transposed pair sits inside it), null_island (the pair is at/near (0,0)), sign_flip (the pair sits outside the declared extent and negating exactly one axis lands it inside), or wrong_jurisdiction (the pair contradicts the declared extent and no transposition or sign flip rescues it). The observed pair, the declared extent it failed and the detector version ride the claim evidence; the claim only MARKS the defect — the original coordinate claims stand and any corrected coordinate is a new camera_latitude/camera_longitude claim citing the originals in derived_from_claim_ids (P35.16 / R11-DATA-01, F-322, SIG-GEO-008, SIG-IDENT-004, SIG-ONTO-011).', 'https://ontology.sig-project.org/vocab/predicate/1.0.0/geometry_defect', 'IMMUTABLE', NULL, 'never_resolve')
ON CONFLICT (predicate_id) DO NOTHING;

INSERT INTO directness_matrix (artifact_type, predicate_id, directness, ruleset_version) VALUES
  ('executed_contract', 'geometry_defect', 'D6', '1.0.0'),
  ('invoice', 'geometry_defect', 'D6', '1.0.0'),
  ('portal_snapshot', 'geometry_defect', 'D6', '1.0.0'),
  ('council_minutes', 'geometry_defect', 'D6', '1.0.0'),
  ('agency_policy', 'geometry_defect', 'D6', '1.0.0'),
  ('osm_node_set', 'geometry_defect', 'D6', '1.0.0'),
  ('audit_log', 'geometry_defect', 'D6', '1.0.0'),
  ('news_article', 'geometry_defect', 'D6', '1.0.0'),
  ('vendor_default_page', 'geometry_defect', 'D6', '1.0.0'),
  ('camera_registry', 'geometry_defect', 'D4', '1.0.0'),
  ('connector_run', 'geometry_defect', 'D3', '1.0.0'),
  ('agenda_document', 'geometry_defect', 'D6', '1.0.0'),
  ('bill_index', 'geometry_defect', 'D6', '1.0.0'),
  ('portal_document', 'geometry_defect', 'D6', '1.0.0'),
  ('community_map', 'geometry_defect', 'D6', '1.0.0'),
  ('contract', 'geometry_defect', 'D6', '1.0.0'),
  ('official_statement', 'geometry_defect', 'D6', '1.0.0'),
  ('template', 'geometry_defect', 'D6', '1.0.0'),
  ('subscription', 'geometry_defect', 'D6', '1.0.0'),
  ('recommendation', 'geometry_defect', 'D6', '1.0.0')
ON CONFLICT (artifact_type, predicate_id, ruleset_version) DO NOTHING;

COMMIT;
