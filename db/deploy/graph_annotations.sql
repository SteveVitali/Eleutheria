-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:graph_annotations to pg
-- Appendix C.6 (relational part): contradiction (a first-class, visible object —
-- the point of retiring Risk 3), coverage_record (makes NEGATIVE claims
-- queryable, §32.1), and research_task. The L4 inference schema is a separate
-- change (`inference_schema`).

BEGIN;

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

COMMIT;
