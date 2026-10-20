-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:vocab_enforcement_count to pg
-- P36.12 / P36.6 (R11-ACQ-10, I8 NEW-7): register `enforcement_count` in the
-- hosted closed vocabulary BEFORE the first ATE-family live emit — P35.14a's
-- closed sink quarantines an unregistered predicate. The row projects the
-- ontology registry verbatim (vocab_version 1.0.0) exactly as
-- `closed_vocabulary` seeded its cohort; the directness matrix gains the
-- predicate's 20-genre row at ruleset_version 1.0.0. INSERT-only,
-- ON CONFLICT-safe, no UPDATE/DELETE: a pre-existing row keeps its values
-- (append-only, P1–P3). The Wave-B L0 leg runs this as an operator step on
-- the hosted spine — the change is committed here, never executed by an
-- agent's engineering run.

BEGIN;

INSERT INTO vocab_predicate
(predicate_id, vocab_version, value_datatype, object_type, cardinality,
 definition, skos_concept_iri, volatility_class, half_life_days,
 resolution_strategy) VALUES
  ('enforcement_count', '1.0.0', 'integer', 'literal', 'multi', 'The operator-published aggregate count of automated-enforcement outcomes (warnings/violations) for a camera or programme subject over a declared period — a claim carries its `period` and `measure` fields beside the integer value, keyed camera × month or site × quarter as published. Aggregate rows only: never a per-violation, plate, person, trip or citation record (P36.6 / R11-ACQ-10, I8 NEW-7) — the aggregate admission is distinct from the connector-forbidden `camera_count` device-count genre, and Part VIII prohibits the row-level surfaces this predicate deliberately replaces.', 'https://ontology.sig-project.org/vocab/predicate/1.0.0/enforcement_count', 'VOLATILE', 183, 'interval_union')
ON CONFLICT (predicate_id) DO NOTHING;

INSERT INTO directness_matrix (artifact_type, predicate_id, directness, ruleset_version) VALUES
  ('executed_contract', 'enforcement_count', 'D5', '1.0.0'),
  ('invoice', 'enforcement_count', 'D5', '1.0.0'),
  ('portal_snapshot', 'enforcement_count', 'D3', '1.0.0'),
  ('council_minutes', 'enforcement_count', 'D4', '1.0.0'),
  ('agency_policy', 'enforcement_count', 'D4', '1.0.0'),
  ('osm_node_set', 'enforcement_count', 'D6', '1.0.0'),
  ('audit_log', 'enforcement_count', 'D5', '1.0.0'),
  ('news_article', 'enforcement_count', 'D4', '1.0.0'),
  ('vendor_default_page', 'enforcement_count', 'D5', '1.0.0'),
  ('camera_registry', 'enforcement_count', 'D2', '1.0.0'),
  ('connector_run', 'enforcement_count', 'D3', '1.0.0'),
  ('agenda_document', 'enforcement_count', 'D6', '1.0.0'),
  ('bill_index', 'enforcement_count', 'D6', '1.0.0'),
  ('portal_document', 'enforcement_count', 'D4', '1.0.0'),
  ('community_map', 'enforcement_count', 'D6', '1.0.0'),
  ('contract', 'enforcement_count', 'D5', '1.0.0'),
  ('official_statement', 'enforcement_count', 'D3', '1.0.0'),
  ('template', 'enforcement_count', 'D6', '1.0.0'),
  ('subscription', 'enforcement_count', 'D6', '1.0.0'),
  ('recommendation', 'enforcement_count', 'D6', '1.0.0')
ON CONFLICT (artifact_type, predicate_id, ruleset_version) DO NOTHING;

COMMIT;
