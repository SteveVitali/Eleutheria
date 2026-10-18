-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:subject_rekey to pg
-- P35.24 / ADR-212 (R11-L3-CP2, CONF-03b; F-506/F-518, L2-M07 5,278 collisions):
-- the key-pin metadata mirror and the append-only re-key decision log the
-- `sig-db subject-rekey` run needs.
--
-- 1. `subject_key_pin` seeds the committed pin registry
--    (`db/src/db/data/subject_key_pins.toml` sig.subject-key-pins/1) so an
--    applied decision can name the registry version it was minted under; the
--    runtime registry stays the TOML (single source — the test suite asserts
--    the seeds mirror it). UPDATE/DELETE are forbidden (append-only record).
--
-- 2. `subject_rekey_decision` is the append-only identity-decision log: one
--    row per (old subject value -> constituent value) written in the same
--    transaction as the claim corrections it summarises. UNIQUE
--    (scheme, old_value, new_value, registry_version) is the +0 rerun
--    barrier; existing claim/entity rows are never UPDATEd/DELETEd — the
--    correction lands as new claim rows with revises_claim + correction_reason.
--
-- 3. claim_evidence(claim_id) index — the re-key plan joins every moved
--    claim's evidence bundle; the existing indexes cover (capture_id) only.
--
-- Locking: two CREATE TABLEs take SHARE ROW EXCLUSIVE on their parents
-- briefly; the index is a plain btree CREATE INDEX (share lock on
-- claim_evidence for seconds on the hosted spine). Deployed when no ingest
-- execution is running; nothing else is altered — additive + back-compatible.

BEGIN;

CREATE TABLE subject_key_pin (
  pin_id           text PRIMARY KEY,
  family           text NOT NULL,
  key_version      int  NOT NULL,
  fields           jsonb NOT NULL,            -- ordered declared field names
  scope            jsonb,                     -- {field, kind, scheme, absent} or NULL
  uniqueness       text,                      -- 'capture' | NULL
  distinguish      jsonb NOT NULL DEFAULT '[]', -- collision selectors (predicate:<id> | context:<key>)
  registry_version text NOT NULL,
  registered_at    timestamptz NOT NULL DEFAULT clock_timestamp()
);

COMMENT ON TABLE subject_key_pin IS
  'P35.24 (ADR-212): mirror of the committed sig.subject-key-pins registry '
  '(subject_key_pins.toml) so re-key decisions can name the grammar version '
  'they were minted under; runtime grammar stays the TOML — seeds are pinned '
  'by test parity, never hand-edited.';

INSERT INTO subject_key_pin
  (pin_id, family, key_version, fields, scope, uniqueness, distinguish, registry_version)
VALUES
  ('traffic_camera', 'traffic_camera:', 1,
   '["source_id","target_id","camera_ref"]'::jsonb, NULL, 'capture',
   '["predicate:camera_latitude"]'::jsonb, 'sig.subject-key-pins/1'),
  ('atlas_agency', 'atlas:', 2,
   '["state","agency"]'::jsonb,
   '{"field":"state","kind":"scheme_prefixed","scheme":"us.state_abbr","absent":"unscoped"}'::jsonb,
   NULL, '["context:State"]'::jsonb, 'sig.subject-key-pins/1'),
  ('data_driven_agency', 'data_driven:agency:', 2,
   '["state","agency_id"]'::jsonb,
   '{"field":"state","kind":"scheme_prefixed","scheme":"us.state_abbr","absent":"unscoped"}'::jsonb,
   NULL, '["context:state"]'::jsonb, 'sig.subject-key-pins/1'),
  ('contract', 'contract:', 2,
   '["source_id","tenant_id","external_id"]'::jsonb,
   '{"field":"tenant_id","kind":"scheme_prefixed","scheme":"tenant","absent":"omit"}'::jsonb,
   NULL, '["context:tenant_id"]'::jsonb, 'sig.subject-key-pins/1'),
  ('agenda_item', 'agenda_item:', 1,
   '["source_id","tenant_id","external_id"]'::jsonb, NULL, NULL,
   '[]'::jsonb, 'sig.subject-key-pins/1'),
  ('agenda_document', 'agenda_document:', 1,
   '["source_id","tenant_id","external_id"]'::jsonb, NULL, NULL,
   '[]'::jsonb, 'sig.subject-key-pins/1');

-- Append-only (P1-P3): a registered pin is a recorded declaration; a change
-- ships as a NEW sqitch change with new rows, never an edit.
CREATE FUNCTION subject_key_pin_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION
    'subject_key_pin rows are immutable (append-only, P1-P3); register a new pin version in a new change';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER subject_key_pin_immutable
  BEFORE UPDATE OR DELETE ON subject_key_pin
  FOR EACH ROW EXECUTE FUNCTION subject_key_pin_immutable();

CREATE TABLE subject_rekey_decision (
  decision_seq     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  scheme           text NOT NULL,
  old_value        text NOT NULL,
  new_value        text NOT NULL,
  discriminator    text,                 -- coordinate pair / scope value the split used
  claims_moved     int  NOT NULL,
  run_id           uuid REFERENCES ingest_run(run_id),
  registry_version text NOT NULL,        -- the pin-registry version minted under
  decided_by       text NOT NULL,        -- a writer identity/role, never a personal name
  basis            text NOT NULL,
  decided_at       timestamptz NOT NULL DEFAULT clock_timestamp(),
  -- The decision names an existing keyed identity and a NEW constituent
  -- value — the old key itself is never rewritten.
  FOREIGN KEY (scheme, old_value) REFERENCES entity_identity_key (scheme, value),
  -- Idempotency barrier: one decision per (old key, constituent, registry
  -- version); the writer's INSERT ... ON CONFLICT DO NOTHING makes a re-run +0.
  UNIQUE (scheme, old_value, new_value, registry_version),
  CHECK (old_value <> new_value)
);

COMMENT ON TABLE subject_rekey_decision IS
  'P35.24 (ADR-212): append-only subject re-key decisions — one row per '
  '(collided sig.connector.subject key -> truthful constituent) recorded in '
  'the same transaction as the claim corrections (revises_claim + '
  'correction_reason). Historical rows are preserved; the current view shows '
  'constituent subjects because the old claims closed (sys_period end) when '
  'their corrections landed.';

CREATE INDEX subject_rekey_decision_old_idx
  ON subject_rekey_decision (scheme, old_value, decision_seq);

CREATE FUNCTION subject_rekey_decision_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION
    'subject_rekey_decision rows are immutable (append-only, P1-P3); record a NEW decision row instead';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER subject_rekey_decision_immutable
  BEFORE UPDATE OR DELETE ON subject_rekey_decision
  FOR EACH ROW EXECUTE FUNCTION subject_rekey_decision_immutable();

-- The re-key plan reads each moved claim's evidence bundle (capture +
-- locator); claim_evidence had no claim_id-first index.
CREATE INDEX claim_evidence_claim_idx ON claim_evidence (claim_id);

GRANT SELECT, INSERT ON subject_key_pin TO sig_ingest;
GRANT SELECT, INSERT ON subject_rekey_decision TO sig_ingest;

COMMIT;
